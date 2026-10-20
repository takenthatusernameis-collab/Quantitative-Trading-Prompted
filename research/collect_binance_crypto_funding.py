"""Collect crypto funding rates and daily prices from the Binance public archive.

The live Binance REST API is geo-blocked from this environment, but the public
data archive (``https://data.binance.vision``) is reachable and publishes a
monthly ZIP per symbol for perpetual funding rates and for klines, each with a
companion ``.CHECKSUM`` file holding the SHA256 of the ZIP.  Every archive
object is therefore verified against its published checksum before it is
parsed, which makes provenance independently checkable without trusting the
collection run.

Outputs (all under ``data/raw/crypto/``):

* ``<BASE>_USDT_USDT_funding_binance.parquet`` — 8h funding rates of the
  USDT-margined Binance perpetual.  Schema matches the previously collected
  OKX cache (``research/experiments/cryptofunding_001_data.md``):
  ``timestamp`` (epoch ms, int64), ``datetime`` (UTC), ``fundingRate``
  (float64), ``symbol`` (ccxt unified, e.g. ``BTC/USDT:USDT``).
* ``<BASE>USDT_perp_1d_binance.parquet`` — daily USDT-margined perpetual
  klines (the short leg).
* ``<BASE>USDT_spot_1d_binance.parquet`` — daily spot klines (the long leg).

The script is idempotent, caches downloaded ZIPs under
``data/raw/crypto/_cache/`` and can rebuild every output from that cache with
``--offline``.  It never writes partial data: each output file is written only
after every contributing archive object has been checksum-verified.

Usage::

    python research/collect_binance_crypto_funding.py
    python research/collect_binance_crypto_funding.py --offline
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import zipfile
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_CRYPTO_DIR = REPO_ROOT / "data" / "raw" / "crypto"
MANIFEST_PATH = REPO_ROOT / "research" / "reports" / "binance_crypto_manifest.json"

ARCHIVE_URL = "https://data.binance.vision"
LISTING_URL = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"

FUNDING_PREFIX = "data/futures/um/monthly/fundingRate/{symbol}/"
PERP_KLINE_PREFIX = "data/futures/um/monthly/klines/{symbol}/1d/"
SPOT_KLINE_PREFIX = "data/spot/monthly/klines/{symbol}/1d/"

DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT")
DEFAULT_START = "2020-01"
DEFAULT_END = "2026-09"
DOWNLOAD_WORKERS = 8
HTTP_TIMEOUT = 30
HTTP_RETRIES = 3
FUNDING_INTERVAL_HOURS = 8
GAP_TOLERANCE_SECONDS = 60
PROCESSED_CRYPTO_DIR = REPO_ROOT / "data" / "processed" / "crypto"


# ======================================================================
# HTTP helpers
# ======================================================================
def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "quant-research-collector/1.0"})
    return session


def _get(session: requests.Session, url: str, params: dict | None = None) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(HTTP_RETRIES):
        try:
            response = session.get(url, params=params, timeout=HTTP_TIMEOUT)
            if response.status_code == 200:
                return response
            last_error = RuntimeError(f"HTTP {response.status_code} for {url}")
        except requests.RequestException as exc:  # transient network failure
            last_error = exc
        if attempt + 1 < HTTP_RETRIES:
            import time

            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def list_objects(session: requests.Session, prefix: str) -> list[str]:
    """Return every object key under ``prefix`` from the archive listing API."""
    keys: list[str] = []
    marker = ""
    while True:
        params = {"prefix": prefix, "delimiter": "/"}
        if marker:
            params["marker"] = marker
        response = _get(session, LISTING_URL, params=params)
        body = response.text
        keys.extend(re.findall(r"<Key>(.*?)</Key>", body))
        match = re.search(r"<NextMarker>(.*?)</NextMarker>", body)
        if not match:
            break
        marker = match.group(1)
    return sorted(k for k in keys if not k.endswith(".CHECKSUM"))


def download_verified(
    session: requests.Session, key: str, cache_dir: Path, offline: bool
) -> tuple[bytes, str]:
    """Return ``(payload, sha256)`` for an archive object, verifying its checksum.

    The published ``.CHECKSUM`` file is authoritative.  Cached payloads are
    re-verified against that checksum, so a truncated or corrupted cache entry
    can never enter a dataset.
    """
    cache_path = cache_dir / key.replace("/", "__")
    checksum_url = f"{ARCHIVE_URL}/{key}.CHECKSUM"
    expected = _get(session, checksum_url).text.split()[0].strip().lower()

    if cache_path.exists():
        payload = cache_path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        if digest == expected:
            return payload, digest
        cache_path.unlink()

    if offline:
        raise RuntimeError(f"offline mode and {key} is not cached")

    payload = _get(session, f"{ARCHIVE_URL}/{key}").content
    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected:
        raise RuntimeError(
            f"checksum mismatch for {key}: expected {expected}, computed {digest}"
        )
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(payload)
    return payload, digest


# ======================================================================
# Parsing
# ======================================================================
def _zip_member(payload: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = [n for n in archive.namelist() if not n.endswith("/")]
        if len(names) != 1:
            raise RuntimeError(f"expected exactly one CSV member, found {names}")
        return names[0]


def _zip_text(payload: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        name = _zip_member(payload)
        return archive.read(name).decode("utf-8")


def _epoch_ms(values: pd.Series) -> pd.Series:
    """Convert an archive epoch column to milliseconds.

    Binance mixes units across vintages: most files are in milliseconds, but
    spot klines from 2025 onwards ship microseconds.  The unit is detected
    from the magnitude of the column rather than assumed.
    """
    numeric = pd.to_numeric(values).astype("int64")
    peak = int(numeric.abs().max()) if len(numeric) else 0
    if peak > 10**17:
        return numeric // 1_000_000
    if peak > 10**14:
        return numeric // 1_000
    if peak > 10**11:
        return numeric
    return numeric * 1_000


def parse_funding_csv(text: str, symbol: str) -> pd.DataFrame:
    """Parse one monthly funding CSV into the repository funding schema."""
    frame = pd.read_csv(io.StringIO(text))
    expected = {"calc_time", "funding_interval_hours", "last_funding_rate"}
    missing = expected - set(frame.columns)
    if missing:
        raise RuntimeError(f"funding CSV missing columns {sorted(missing)}")
    millis = _epoch_ms(frame["calc_time"])
    out = pd.DataFrame(
        {
            "timestamp": millis,
            "datetime": pd.to_datetime(millis, unit="ms", utc=True),
            "fundingRate": frame["last_funding_rate"].astype("float64"),
            "symbol": symbol,
        }
    )
    out["funding_interval_hours"] = frame["funding_interval_hours"].astype("int64")
    return out


def parse_klines_csv(text: str, symbol: str, market: str) -> pd.DataFrame:
    """Parse one monthly daily-klines CSV into a flat OHLCV frame."""
    raw = pd.read_csv(io.StringIO(text), header=None)
    if raw.shape[1] < 9:
        raise RuntimeError(f"klines CSV has {raw.shape[1]} columns, expected >= 9")
    if str(raw.iat[0, 0]).strip() == "open_time":
        # Newer monthly files ship a header row.
        raw = raw.iloc[1:].reset_index(drop=True)
    raw = raw.apply(pd.to_numeric)
    millis = _epoch_ms(raw[0])
    frame = pd.DataFrame(
        {
            "timestamp": millis,
            "datetime": pd.to_datetime(millis, unit="ms", utc=True),
            "open": raw[1].astype("float64"),
            "high": raw[2].astype("float64"),
            "low": raw[3].astype("float64"),
            "close": raw[4].astype("float64"),
            "volume": raw[5].astype("float64"),
            "quote_volume": raw[7].astype("float64"),
            "trades": raw[8].astype("int64"),
            "symbol": symbol,
            "market": market,
        }
    )
    return frame


def _month_keys(keys: Iterable[str], start: str, end: str) -> list[str]:
    """Keep only the monthly members inside the inclusive ``YYYY-MM`` window."""
    keep = []
    for key in keys:
        match = re.search(r"-(\d{4}-\d{2})\.zip$", key)
        if not match:
            continue
        month = match.group(1)
        if start <= month <= end:
            keep.append(key)
    return keep


# ======================================================================
# Validation
# ======================================================================
def validate_funding(frame: pd.DataFrame) -> dict:
    """Describe coverage, interval structure and gaps of a funding frame."""
    if frame.empty:
        return {"rows": 0}
    ts = frame["datetime"].sort_values().reset_index(drop=True)
    gap_seconds = ts.diff().dt.total_seconds()
    interval_counts = (gap_seconds / 3600.0).round(3).value_counts().sort_index()
    expected_periods = (
        round((ts.iloc[-1] - ts.iloc[0]).total_seconds() / (FUNDING_INTERVAL_HOURS * 3600))
    ) + 1
    gaps = []
    for position in range(1, len(ts)):
        seconds = float(gap_seconds.iloc[position])
        # Archive timestamps carry a few milliseconds of jitter; only a real
        # missing period counts as a gap.
        if seconds <= FUNDING_INTERVAL_HOURS * 3600 + GAP_TOLERANCE_SECONDS:
            continue
        prev = ts.iloc[position - 1]
        gaps.append(
            {
                "after": prev.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "before": ts.iloc[position].strftime("%Y-%m-%dT%H:%M:%SZ"),
                "hours": round(seconds / 3600.0, 6),
                "missing_periods": round(seconds / (FUNDING_INTERVAL_HOURS * 3600)) - 1,
            }
        )
    annualized = frame["fundingRate"].mean() * 3 * 365
    span_years = (ts.iloc[-1] - ts.iloc[0]).total_seconds() / (365.25 * 86400.0)
    span_annualized = float(frame["fundingRate"].sum() / span_years) if span_years > 0 else 0.0
    return {
        "rows": len(frame),
        "start_utc": ts.iloc[0].strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end_utc": ts.iloc[-1].strftime("%Y-%m-%dT%H:%M:%SZ"),
        "span_days": round((ts.iloc[-1] - ts.iloc[0]).total_seconds() / 86400.0, 3),
        "duplicate_timestamps": int(ts.duplicated().sum()),
        "monotonic_after_sort": bool(ts.is_monotonic_increasing),
        "interval_hours_counts": {str(k): v for k, v in interval_counts.items()},
        "expected_periods_at_8h": expected_periods,
        "missing_periods_at_8h": expected_periods - len(frame),
        "gap_count": len(gaps),
        "largest_gaps": sorted(gaps, key=lambda g: -g["hours"])[:5],
        "funding_rate_min": float(frame["fundingRate"].min()),
        "funding_rate_max": float(frame["fundingRate"].max()),
        "funding_rate_mean": float(frame["fundingRate"].mean()),
        "mean_annualized_simple": float(annualized),
        "sum_annualized_over_span": span_annualized,
        "positive_fraction": float((frame["fundingRate"] > 0).mean()),
        "distinct_funding_intervals_hours": sorted(
            {int(v) for v in frame["funding_interval_hours"].unique()}
        ),
    }


def validate_klines(frame: pd.DataFrame) -> dict:
    """Describe coverage and continuity of a daily klines frame."""
    if frame.empty:
        return {"rows": 0}
    ts = frame["datetime"].sort_values().reset_index(drop=True)
    day = ts.dt.floor("D")
    return {
        "rows": len(frame),
        "start_utc": ts.iloc[0].strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end_utc": ts.iloc[-1].strftime("%Y-%m-%dT%H:%M:%SZ"),
        "span_days": round((ts.iloc[-1] - ts.iloc[0]).total_seconds() / 86400.0, 3),
        "duplicate_timestamps": int(ts.duplicated().sum()),
        "monotonic_after_sort": bool(ts.is_monotonic_increasing),
        "distinct_calendar_days": int(day.nunique()),
        "non_positive_close_rows": int((frame["close"] <= 0).sum()),
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ======================================================================
# Spot-long / perp-short construction path
# ======================================================================
def _daily_close(frame: pd.DataFrame) -> pd.Series:
    """Last close of each UTC calendar day in a klines frame."""
    ordered = frame.sort_values("datetime").drop_duplicates("datetime", keep="last")
    series = ordered.set_index("datetime")["close"]
    return series.groupby(series.index.floor("D")).last()


def build_carry_path(
    funding: pd.DataFrame, spot: pd.DataFrame, perp: pd.DataFrame
) -> pd.DataFrame:
    """Build the reproducible daily spot-long / perp-short return path.

    Components, all in simple daily returns of a dollar-neutral pair
    (one spot long, one perp short):

    * ``funding_cashflow``  — sum of the 8h funding rates credited to the
      short perp leg on that UTC day (positive funding pays the short).
    * ``spot_return`` / ``perp_return`` — close-to-close returns of the two
      legs.
    * ``basis_convergence`` — ``spot_return - perp_return``: what the
      short-perp / long-spot pair earns when the perp converges to spot.
    * ``gross_carry`` — ``funding_cashflow + basis_convergence``, i.e. the
      gross daily return of the pair *before* fees, slippage, funding
      rounding and margin costs.
    * ``basis_close`` — ``perp_close / spot_close - 1``, the contemporaneous
      annualised-free basis level used for diagnostics.

    Funding is attributed to the UTC day of its settlement timestamp, which
    is the only convention the archive supports (it stores settlement times,
    not accrual windows).
    """
    fund = funding.copy()
    fund["day"] = fund["datetime"].dt.floor("D")
    daily_funding = fund.groupby("day")["fundingRate"].agg(["sum", "count"])
    daily_funding.columns = ["funding_cashflow", "funding_periods"]

    spot_close = _daily_close(spot)
    perp_close = _daily_close(perp)
    days = pd.DatetimeIndex(
        sorted(set(daily_funding.index) | set(spot_close.index) | set(perp_close.index)),
        name="date",
    )
    path = pd.DataFrame(index=days)
    path["funding_cashflow"] = daily_funding["funding_cashflow"].reindex(days)
    path["funding_periods"] = daily_funding["funding_periods"].reindex(days).fillna(0).astype(int)
    path["spot_close"] = spot_close.reindex(days)
    path["perp_close"] = perp_close.reindex(days)
    path["spot_return"] = path["spot_close"].pct_change()
    path["perp_return"] = path["perp_close"].pct_change()
    path["basis_convergence"] = path["spot_return"] - path["perp_return"]
    path["basis_close"] = path["perp_close"] / path["spot_close"] - 1.0
    path["gross_carry"] = path["funding_cashflow"] + path["basis_convergence"]
    return path.dropna(subset=["spot_return", "perp_return"])


def carry_path_stats(path: pd.DataFrame) -> dict:
    """Descriptive (cost-free) statistics of a constructed carry path."""
    if path.empty:
        return {"rows": 0}
    per_year = path.groupby(path.index.year).agg(
        days=("gross_carry", "size"),
        gross_carry_sum=("gross_carry", "sum"),
        funding_sum=("funding_cashflow", "sum"),
        basis_sum=("basis_convergence", "sum"),
        positive_days=("gross_carry", lambda s: float((s > 0).mean())),
    )
    per_year["gross_carry_annualized"] = per_year["gross_carry_sum"] * 365.0 / per_year["days"]
    per_year["funding_annualized"] = per_year["funding_sum"] * 365.0 / per_year["days"]
    per_year["basis_annualized"] = per_year["basis_sum"] * 365.0 / per_year["days"]
    span_days = int(per_year["days"].sum())
    total = float(path["gross_carry"].sum())
    return {
        "rows": len(path),
        "start": path.index[0].strftime("%Y-%m-%d"),
        "end": path.index[-1].strftime("%Y-%m-%d"),
        "gross_carry_total": total,
        "gross_carry_annualized": total * 365.0 / span_days if span_days else 0.0,
        "funding_annualized": float(path["funding_cashflow"].sum()) * 365.0 / span_days
        if span_days
        else 0.0,
        "basis_annualized": float(path["basis_convergence"].sum()) * 365.0 / span_days
        if span_days
        else 0.0,
        "positive_day_fraction": float((path["gross_carry"] > 0).mean()),
        "per_year": {
            str(int(year)): {k: float(v) for k, v in row.items()}
            for year, row in per_year.to_dict(orient="index").items()
        },
    }


# ======================================================================
# Collection
# ======================================================================
def _download_many(
    session: requests.Session, keys: list[str], cache_dir: Path, offline: bool
) -> dict[str, bytes]:
    payloads: dict[str, bytes] = {}

    def _one(key: str) -> tuple[str, bytes]:
        payload, _ = download_verified(session, key, cache_dir, offline)
        return key, payload

    with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as pool:
        for key, payload in pool.map(_one, keys):
            payloads[key] = payload
    return payloads


def collect_funding(
    session: requests.Session,
    symbol: str,
    start: str,
    end: str,
    cache_dir: Path,
    offline: bool,
) -> tuple[pd.DataFrame, dict]:
    keys = _month_keys(list_objects(session, FUNDING_PREFIX.format(symbol=symbol)), start, end)
    if not keys:
        raise RuntimeError(f"no funding archive objects for {symbol} in {start}..{end}")
    payloads = _download_many(session, keys, cache_dir, offline)
    frames = []
    for key in keys:
        text = _zip_text(payloads[key])
        if not text.strip():
            continue
        frames.append(parse_funding_csv(text, f"{symbol[:3]}/USDT:USDT"))
    frame = pd.concat(frames, ignore_index=True)
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    frame = frame[~frame["timestamp"].duplicated(keep="last")].reset_index(drop=True)
    stats = validate_funding(frame)
    stats["archive_objects"] = len(keys)
    stats["archive_checksums_verified"] = len(keys)
    return frame, stats


def collect_klines(
    session: requests.Session,
    symbol: str,
    prefix: str,
    market: str,
    start: str,
    end: str,
    cache_dir: Path,
    offline: bool,
) -> tuple[pd.DataFrame, dict]:
    keys = _month_keys(list_objects(session, prefix.format(symbol=symbol)), start, end)
    if not keys:
        raise RuntimeError(f"no klines archive objects for {symbol}/{market}")
    payloads = _download_many(session, keys, cache_dir, offline)
    frames = []
    for key in keys:
        text = _zip_text(payloads[key])
        if not text.strip():
            continue
        frames.append(parse_klines_csv(text, f"{symbol[:3]}/USDT", market))
    frame = pd.concat(frames, ignore_index=True)
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    frame = frame[~frame["timestamp"].duplicated(keep="last")].reset_index(drop=True)
    stats = validate_klines(frame)
    stats["archive_objects"] = len(keys)
    stats["archive_checksums_verified"] = len(keys)
    return frame, stats


def funding_path(raw_dir: Path, symbol: str) -> Path:
    return raw_dir / f"{symbol[:3]}_USDT_USDT_funding_binance.parquet"


def klines_path(raw_dir: Path, symbol: str, market: str) -> Path:
    return raw_dir / f"{symbol}_spot_1d_binance.parquet" if market == "spot" else raw_dir / f"{symbol}_perp_1d_binance.parquet"


def collect(
    symbols: tuple[str, ...] = DEFAULT_SYMBOLS,
    start: str = DEFAULT_START,
    end: str = DEFAULT_END,
    raw_dir: Path = RAW_CRYPTO_DIR,
    cache_dir: Path | None = None,
    offline: bool = False,
    manifest_path: Path | None = MANIFEST_PATH,
    construct_path: bool = False,
    processed_dir: Path = PROCESSED_CRYPTO_DIR,
) -> dict:
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = Path(cache_dir) if cache_dir else raw_dir / "_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    session = _session()

    manifest: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Binance public data archive (data.binance.vision)",
        "listing_endpoint": LISTING_URL,
        "download_endpoint": ARCHIVE_URL,
        "checksum_verified": True,
        "window": {"start_month": start, "end_month": end},
        "datasets": {},
    }

    for symbol in symbols:
        funding, funding_stats = collect_funding(
            session, symbol, start, end, cache_dir, offline
        )
        path = funding_path(raw_dir, symbol)
        funding.to_parquet(path, index=False)
        funding_stats["path"] = str(path.relative_to(REPO_ROOT))
        funding_stats["sha256"] = sha256_file(path)
        manifest["datasets"][f"funding_{symbol}"] = funding_stats

        perp, perp_stats = collect_klines(
            session,
            symbol,
            PERP_KLINE_PREFIX,
            "perp",
            start,
            end,
            cache_dir,
            offline,
        )
        perp_path = klines_path(raw_dir, symbol, "perp")
        perp.to_parquet(perp_path, index=False)
        perp_stats["path"] = str(perp_path.relative_to(REPO_ROOT))
        perp_stats["sha256"] = sha256_file(perp_path)
        manifest["datasets"][f"perp_{symbol}"] = perp_stats

        spot, spot_stats = collect_klines(
            session,
            symbol,
            SPOT_KLINE_PREFIX,
            "spot",
            start,
            end,
            cache_dir,
            offline,
        )
        spot_path = klines_path(raw_dir, symbol, "spot")
        spot.to_parquet(spot_path, index=False)
        spot_stats["path"] = str(spot_path.relative_to(REPO_ROOT))
        spot_stats["sha256"] = sha256_file(spot_path)
        manifest["datasets"][f"spot_{symbol}"] = spot_stats

        if construct_path:
            carry = build_carry_path(funding, spot, perp)
            processed_dir = Path(processed_dir)
            processed_dir.mkdir(parents=True, exist_ok=True)
            carry_path = processed_dir / f"{symbol}_carry_path.parquet"
            carry.to_parquet(carry_path)
            carry_stats = carry_path_stats(carry)
            carry_stats["path"] = str(carry_path.relative_to(REPO_ROOT))
            carry_stats["sha256"] = sha256_file(carry_path)
            carry_stats["note"] = "gross of all costs; descriptive statistics only"
            manifest["datasets"][f"carry_path_{symbol}"] = carry_stats

    if manifest_path is not None:
        manifest_path = Path(manifest_path)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def print_summary(manifest: dict) -> None:
    print(f"source: {manifest['source']}")
    print(f"window: {manifest['window']['start_month']}..{manifest['window']['end_month']}")
    for name, stats in manifest["datasets"].items():
        line = (
            f"{name:<22} rows={stats['rows']:>6} "
            f"{stats.get('start_utc', stats.get('start', '?'))} .. "
            f"{stats.get('end_utc', stats.get('end', '?'))}"
        )
        if "span_days" in stats:
            line += f" span_days={stats.get('span_days', 0):>8.1f}"
        if "gap_count" in stats:
            line += (
                f" gaps={stats['gap_count']}"
                f" missing_8h_periods={stats.get('missing_periods_at_8h', 0)}"
                f" mean_ann={stats.get('mean_annualized_simple', 0.0):.4%}"
            )
        print(line)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect Binance public-archive crypto funding rates and prices."
    )
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS))
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=DEFAULT_END)
    parser.add_argument("--raw-dir", default=str(RAW_CRYPTO_DIR))
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--construct-path", action="store_true")
    parser.add_argument("--manifest", default=str(MANIFEST_PATH))
    args = parser.parse_args()

    manifest = collect(
        symbols=tuple(args.symbols),
        start=args.start,
        end=args.end,
        raw_dir=Path(args.raw_dir),
        cache_dir=Path(args.cache_dir) if args.cache_dir else None,
        offline=args.offline,
        manifest_path=Path(args.manifest) if args.manifest else None,
        construct_path=args.construct_path,
    )
    print_summary(manifest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
