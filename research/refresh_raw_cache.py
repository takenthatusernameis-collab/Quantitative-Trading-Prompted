"""Session-safe raw-cache refresh for the paper-trading universe.

Appends only *completed* trading sessions to the canonical ``data/raw`` cache,
is idempotent, and records an integrity manifest per run.

Contract (Cycle 855):
  * Market data is downloaded into a scratch directory. The canonical cache is
    only touched when a new complete session is appended; existing history is
    never rewritten or deleted.
  * Provider bars for the in-progress session are partial and are dropped
    before anything is written (``session_is_complete`` /
    ``complete_session_view`` reused from
    ``research.extend_paper_trading_state``).
  * Every row about to be written is asserted to belong to a completed
    session; otherwise the run fails with a clear message and writes nothing.
  * Re-running with no new complete session writes 0 rows and reports "no-op".
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from research.extend_paper_trading_state import (
    complete_session_view,
    session_is_complete,
)
from src.data.yfinance_fetcher import fetch_universe

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "simulation_candidate_001.yaml"
RAW_DIR = REPO_ROOT / "data" / "raw"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
VIX_SYMBOL = "^VIX"
DEFAULT_CLOSE_HOUR = 16
DEFAULT_TZ = "America/New_York"
FIELDS = ("Open", "High", "Low", "Close", "Volume")


def universe_symbols() -> list[str]:
    with open(CONFIG_PATH) as fh:
        cfg = yaml.safe_load(fh) or {}
    symbols = list(cfg.get("universe", []))
    if VIX_SYMBOL not in symbols:
        symbols.append(VIX_SYMBOL)
    return symbols


def cache_path(raw_dir: Path, symbol: str) -> Path:
    safe = symbol.replace("/", "-").replace("=", "-")
    return raw_dir / f"{safe}.parquet"


def load_cache(raw_dir: Path, symbol: str) -> pd.DataFrame | None:
    path = cache_path(raw_dir, symbol)
    if not path.exists():
        return None
    try:
        df = pd.read_parquet(path)
    except Exception:
        return None
    if df is None or df.empty:
        return None
    return df.sort_index()


def cached_max_date(raw_dir: Path, symbol: str):
    df = load_cache(raw_dir, symbol)
    if df is None:
        return None
    return pd.Timestamp(df.index.max())


def symbol_frame(universe_df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Extract one symbol's flat OHLCV frame from the aligned universe frame."""
    df = universe_df.xs(symbol, level=1, axis=1)
    df.index = pd.DatetimeIndex(df.index)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    return df[list(FIELDS)].sort_index()


def assert_complete_rows(
    rows: pd.DataFrame,
    now_et: datetime,
    close_hour: int,
    tz: ZoneInfo,
) -> None:
    """Fail loudly if any row belongs to an incomplete session."""
    if rows is None or len(rows) == 0:
        return
    for ts in rows.index:
        ds = pd.Timestamp(ts).strftime("%Y-%m-%d")
        if not session_is_complete(ds, now_et, close_hour=close_hour, tz=tz):
            raise RuntimeError(
                f"refusing to write incomplete bar for session {ds}: "
                "the session close has not passed yet"
            )


def rows_to_append(
    fetched: pd.DataFrame,
    cached_max,
    now_et: datetime,
    close_hour: int,
    tz: ZoneInfo,
) -> pd.DataFrame:
    """Complete-session rows strictly newer than ``cached_max``.

    Partial (in-progress) bars are dropped first; rows to be written are then
    asserted complete so no incomplete bar can ever enter ``data/raw``.
    """
    kept = complete_session_view(fetched, now_et, close_hour=close_hour, tz=tz)
    if kept is None or len(kept) == 0:
        return kept
    if cached_max is not None:
        kept = kept.loc[kept.index > cached_max]
    if kept is None or len(kept) == 0:
        return kept
    assert_complete_rows(kept, now_et, close_hour=close_hour, tz=tz)
    return kept


def append_to_cache(raw_dir: Path, symbol: str, new_rows: pd.DataFrame) -> dict:
    path = cache_path(raw_dir, symbol)
    before = load_cache(raw_dir, symbol)
    if before is None or len(before) == 0:
        combined = new_rows.sort_index()
    else:
        combined = pd.concat([before.sort_index(), new_rows.sort_index()])
        combined = combined[~combined.index.duplicated(keep="last")].sort_index()
    combined.to_parquet(path)
    after = pd.read_parquet(path)
    return {
        "path": str(path),
        "before_rows": 0 if before is None else len(before),
        "after_rows": len(after),
        "appended_rows": len(new_rows),
        "before_max": _max_date_str(before),
        "after_max": _max_date_str(after),
    }


def _max_date_str(df: pd.DataFrame | None) -> str | None:
    if df is None or len(df) == 0:
        return None
    return pd.Timestamp(df.index.max()).strftime("%Y-%m-%d")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(entries: dict, reports_dir: Path = REPORTS_DIR) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "raw_dir": str(RAW_DIR),
        "symbols": entries,
    }
    (reports_dir / "raw_cache_integrity_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )


def refresh(
    raw_dir: Path = RAW_DIR,
    symbols: list[str] | None = None,
    now_et: datetime | None = None,
    close_hour: int = DEFAULT_CLOSE_HOUR,
    tz_name: str = DEFAULT_TZ,
    dry_run: bool = False,
    reports_dir: Path = REPORTS_DIR,
    fetch_fn=fetch_universe,
) -> dict:
    tz = ZoneInfo(tz_name)
    now_et = now_et or datetime.now(timezone.utc)
    symbols = symbols or universe_symbols()

    end_fetch = (now_et.date() + timedelta(days=1)).strftime("%Y-%m-%d")
    starts = {}
    cached_dfs = {}
    for symbol in symbols:
        cached = load_cache(raw_dir, symbol)
        cached_dfs[symbol] = cached
        starts[symbol] = (
            pd.Timestamp(cached.index.max()).strftime("%Y-%m-%d")
            if cached is not None and len(cached) > 0
            else "1993-01-01"
        )
    start_fetch = min(starts.values())

    with tempfile.TemporaryDirectory(prefix="raw-cache-refresh-") as scratch:
        scratch_path = Path(scratch)
        universe_df = fetch_fn(
            symbols, start_fetch, end_fetch, raw_dir=str(scratch_path), force=True
        )

    summary = []
    manifest_entries = {}
    total_appended = 0
    for symbol in symbols:
        cached = cached_dfs[symbol]
        cached_max = (
            pd.Timestamp(cached.index.max()) if cached is not None and len(cached) > 0 else None
        )
        cached_rows = len(cached) if cached is not None else 0
        cached_max_str = _max_date_str(cached)

        frame = symbol_frame(universe_df, symbol)
        new_rows = rows_to_append(frame, cached_max, now_et, close_hour, tz)
        appended = len(new_rows) if new_rows is not None else 0

        entry = {
            "symbol": symbol,
            "cached_rows": cached_rows,
            "cached_max": cached_max_str,
            "appended_rows": appended,
            "status": "no-op" if appended == 0 else "appended",
        }

        if appended == 0:
            after_rows, after_max = cached_rows, cached_max_str
        elif dry_run:
            after_rows, after_max = cached_rows + appended, _max_date_str(new_rows)
            entry["would_append_dates"] = [
                pd.Timestamp(ts).strftime("%Y-%m-%d") for ts in new_rows.index
            ]
        else:
            result = append_to_cache(raw_dir, symbol, new_rows)
            after_rows, after_max = result["after_rows"], result["after_max"]
            total_appended += appended

        entry.update(after_rows=after_rows, after_max=after_max)
        entry["sha256"] = sha256_file(cache_path(raw_dir, symbol))
        manifest_entries[symbol] = entry
        summary.append(entry)

    if not dry_run:
        write_manifest(manifest_entries, reports_dir)

    return {
        "now_utc": now_et.astimezone(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "total_appended": total_appended,
        "symbols": summary,
    }


def print_summary(result: dict) -> None:
    print(f"raw-cache refresh ({'dry-run' if result['dry_run'] else 'run'})")
    print(f"as of: {result['now_utc']}")
    print(f"{'Symbol':<8} {'Before rows':>12} {'Before max':>12} {'Appended':>10} {'After rows':>12} {'After max':>12}  Status")
    for entry in result["symbols"]:
        print(
            f"{entry['symbol']:<8} {entry['cached_rows']:>12} "
            f"{str(entry['cached_max']):>12} {entry['appended_rows']:>10} "
            f"{entry['after_rows']:>12} {str(entry['after_max']):>12}  {entry['status']}"
        )
    if result["total_appended"] == 0:
        print("no-op: no completed sessions to append")
    else:
        print(f"appended {result['total_appended']} row(s) in total")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Session-safe refresh of the canonical data/raw cache."
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--raw-dir", default=str(RAW_DIR))
    args = parser.parse_args()

    result = refresh(
        raw_dir=Path(args.raw_dir),
        dry_run=args.dry_run,
    )
    print_summary(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
