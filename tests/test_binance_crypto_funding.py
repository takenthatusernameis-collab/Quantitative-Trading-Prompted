"""Offline tests for the Cycle 889 Binance public-archive crypto data.

No network access and no writes to ``data/`` or ``config/``: the tests
exercise the pure helpers of ``research/collect_binance_crypto_funding.py``
and one integration path that reads the committed Binance caches and checks
that the multi-year funding history is internally consistent, matches the
independently collected OKX series on the overlap window, and reproduces the
documented spot-long / perp-short construction path.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import research.collect_binance_crypto_funding as cbf  # noqa: E402

RAW_CRYPTO = REPO_ROOT / "data" / "raw" / "crypto"
PROCESSED_CRYPTO = REPO_ROOT / "data" / "processed" / "crypto"
MANIFEST = REPO_ROOT / "research" / "reports" / "binance_crypto_manifest.json"

MIN_HISTORY_DAYS = 365


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ======================================================================
# Pure helpers
# ======================================================================
def test_epoch_ms_detects_millisecond_columns() -> None:
    values = pd.Series([1609459200000, 1609462800000])
    assert list(cbf._epoch_ms(values)) == [1609459200000, 1609462800000]


def test_epoch_ms_detects_microsecond_columns() -> None:
    """Spot klines from 2025 onwards ship microsecond timestamps."""
    values = pd.Series([1735689600000000, 1735776000000000])
    assert list(cbf._epoch_ms(values)) == [1735689600000000 // 1000, 1735776000000000 // 1000]


def test_parse_funding_csv_uses_repository_schema() -> None:
    text = "calc_time,funding_interval_hours,last_funding_rate\n1609459200002,8,0.00022753\n"
    frame = cbf.parse_funding_csv(text, "BTC/USDT:USDT")
    assert list(frame.columns) == [
        "timestamp",
        "datetime",
        "fundingRate",
        "symbol",
        "funding_interval_hours",
    ]
    assert frame["fundingRate"].iloc[0] == pytest.approx(0.00022753)
    assert frame["datetime"].iloc[0] == pd.Timestamp("2021-01-01 00:00:00.002+00:00")


def test_parse_klines_csv_handles_header_and_microseconds() -> None:
    header = "open_time,open,high,low,close,volume,close_time,quote_volume,count,x,y,z\n"
    row = "1735689600000000,93576.0,95151.15,92888.0,93000.0,123.4,0,1.0,7,0,0,0\n"
    frame = cbf.parse_klines_csv(header + row, "BTC/USDT", "spot")
    assert len(frame) == 1
    assert frame["datetime"].iloc[0] == pd.Timestamp("2025-01-01 00:00:00+00:00")
    assert frame["close"].iloc[0] == pytest.approx(93000.0)


def test_validate_funding_ignores_sub_second_jitter() -> None:
    stamps = pd.DatetimeIndex(
        [
            pd.Timestamp("2021-01-01 00:00:00", tz="UTC"),
            pd.Timestamp("2021-01-01 08:00:00.002", tz="UTC"),
            pd.Timestamp("2021-01-01 16:00:00.001", tz="UTC"),
        ]
    )
    frame = pd.DataFrame(
        {
            "datetime": stamps,
            "fundingRate": [0.0001, 0.0002, -0.0003],
            "funding_interval_hours": [8, 8, 8],
        }
    )
    stats = cbf.validate_funding(frame)
    assert stats["gap_count"] == 0
    assert stats["missing_periods_at_8h"] == 0
    assert stats["duplicate_timestamps"] == 0


def test_validate_funding_reports_real_gaps() -> None:
    stamps = pd.DatetimeIndex(
        [
            pd.Timestamp("2021-01-01 00:00:00", tz="UTC"),
            pd.Timestamp("2021-01-01 08:00:00", tz="UTC"),
            pd.Timestamp("2021-01-02 00:00:00", tz="UTC"),  # one 8h period missing
            pd.Timestamp("2021-01-02 08:00:00", tz="UTC"),
        ]
    )
    frame = pd.DataFrame(
        {
            "datetime": stamps,
            "fundingRate": [0.0001] * 4,
            "funding_interval_hours": [8] * 4,
        }
    )
    stats = cbf.validate_funding(frame)
    assert stats["gap_count"] == 1
    assert stats["largest_gaps"][0]["missing_periods"] == 1
    assert stats["missing_periods_at_8h"] == 1


def test_build_carry_path_components() -> None:
    """funding + (spot return - perp return) must equal the gross carry."""
    funding = pd.DataFrame(
        {
            "datetime": pd.to_datetime(
                [
                    "2021-01-01 00:00:00",
                    "2021-01-01 08:00:00",
                    "2021-01-01 16:00:00",
                    "2021-01-02 00:00:00",
                ],
                utc=True,
            ),
            "fundingRate": [0.0001, 0.0002, -0.0001, 0.0004],
            "funding_interval_hours": [8, 8, 8, 8],
        }
    )
    spot = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2021-01-01", "2021-01-02"], utc=True),
            "close": [100.0, 110.0],
        }
    )
    perp = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2021-01-01", "2021-01-02"], utc=True),
            "close": [100.0, 111.0],
        }
    )
    path = cbf.build_carry_path(funding, spot, perp)
    assert len(path) == 1
    row = path.iloc[0]
    assert row["funding_cashflow"] == pytest.approx(0.0004)  # 2021-01-02 settlement
    assert row["spot_return"] == pytest.approx(0.10)
    assert row["perp_return"] == pytest.approx(0.11)
    assert row["basis_convergence"] == pytest.approx(-0.01)
    assert row["gross_carry"] == pytest.approx(0.0004 - 0.01)
    assert row["basis_close"] == pytest.approx(111.0 / 110.0 - 1.0)


# ======================================================================
# Committed-cache integration
# ======================================================================
@pytest.mark.parametrize("symbol", ["BTCUSDT", "ETHUSDT"])
def test_committed_funding_history_is_multi_year_and_complete(symbol: str) -> None:
    path = RAW_CRYPTO / f"{symbol[:3]}_USDT_USDT_funding_binance.parquet"
    assert path.exists(), f"missing committed funding cache {path}"
    frame = pd.read_parquet(path)
    assert list(frame.columns[:4]) == ["timestamp", "datetime", "fundingRate", "symbol"]
    stats = cbf.validate_funding(frame)
    assert stats["span_days"] >= MIN_HISTORY_DAYS
    assert stats["missing_periods_at_8h"] == 0, "funding history must have no missing 8h period"
    assert stats["duplicate_timestamps"] == 0
    assert stats["distinct_funding_intervals_hours"] == [8]
    assert stats["gap_count"] == 0


@pytest.mark.parametrize("symbol", ["BTCUSDT", "ETHUSDT"])
def test_committed_price_legs_align(symbol: str) -> None:
    spot = pd.read_parquet(RAW_CRYPTO / f"{symbol}_spot_1d_binance.parquet")
    perp = pd.read_parquet(RAW_CRYPTO / f"{symbol}_perp_1d_binance.parquet")
    spot_stats = cbf.validate_klines(spot)
    perp_stats = cbf.validate_klines(perp)
    assert spot_stats["rows"] >= MIN_HISTORY_DAYS
    assert spot_stats["non_positive_close_rows"] == 0
    assert perp_stats["non_positive_close_rows"] == 0
    assert spot_stats["start_utc"] == perp_stats["start_utc"]
    assert spot_stats["end_utc"] == perp_stats["end_utc"]


@pytest.mark.parametrize("symbol", ["BTCUSDT", "ETHUSDT"])
def test_committed_carry_path_reconciles_with_funding(symbol: str) -> None:
    path = PROCESSED_CRYPTO / f"{symbol}_carry_path.parquet"
    assert path.exists(), f"missing committed carry path {path}"
    path_frame = pd.read_parquet(path)
    funding = pd.read_parquet(
        RAW_CRYPTO / f"{symbol[:3]}_USDT_USDT_funding_binance.parquet"
    )
    daily = (
        funding.assign(day=funding["datetime"].dt.floor("D"))
        .groupby("day")["fundingRate"]
        .sum()
    )
    # The first calendar day has no prior close, so the path starts one day later.
    aligned = path_frame["funding_cashflow"].reindex(daily.index)
    comparable = aligned.notna()
    assert comparable.sum() >= MIN_HISTORY_DAYS
    assert (aligned[comparable] - daily[comparable]).abs().max() == pytest.approx(0.0, abs=1e-12)


def test_manifest_hashes_match_committed_files() -> None:
    assert MANIFEST.exists(), "missing Binance archive manifest"
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["checksum_verified"] is True
    for name, stats in manifest["datasets"].items():
        path = REPO_ROOT / stats["path"]
        assert path.exists(), f"{name}: missing {path}"
        assert _sha256(path) == stats["sha256"], f"{name}: manifest hash mismatch"


def test_binance_matches_independent_okx_series_on_overlap() -> None:
    """The Binance archive series must agree with the independently sourced OKX one."""
    binance = pd.read_parquet(RAW_CRYPTO / "BTC_USDT_USDT_funding_binance.parquet")
    okx = pd.read_parquet(RAW_CRYPTO / "BTC_USDT_USDT_funding.parquet")
    def grid(series: pd.Series) -> pd.DatetimeIndex:
        # Settlements differ between venues by a few milliseconds.
        return series.dt.round("h")
    left = pd.Series(
        binance["fundingRate"].to_numpy(),
        index=grid(binance["datetime"]),
    )
    right = pd.Series(
        okx["fundingRate"].to_numpy(),
        index=grid(okx["datetime"]),
    )
    joined = pd.concat([left.rename("binance"), right.rename("okx")], axis=1, join="inner")
    assert len(joined) >= 100, "expected a substantial cross-exchange overlap"
    same_sign = float(((joined["binance"] > 0) == (joined["okx"] > 0)).mean())
    median_abs_diff_bp = float((joined["binance"] - joined["okx"]).abs().median() * 1e4)
    assert same_sign >= 0.75, f"cross-exchange sign agreement too low: {same_sign}"
    assert median_abs_diff_bp <= 2.0, f"cross-exchange gap too wide: {median_abs_diff_bp} bp"
