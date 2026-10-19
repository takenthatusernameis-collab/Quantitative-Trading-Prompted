"""Offline tests for the Cycle 880 overnight-session capture candidate.

No network access, no writes to data/ or config/: the tests only exercise the
pure helpers of research/overnight_capture_backtest.py plus the shared
walk-forward generator and a read-only check of the committed price cache.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "research"))

from research.overnight_capture_backtest import (  # noqa: E402
    UNIVERSE,
    apply_costs,
    common_calendar,
    leg_metrics,
    load_cached_ohlc,
    session_returns,
    turnover_units,
)
from src.evaluation.walkforward import generate_walkforward_splits  # noqa: E402


def _frame(rows: int = 6) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A tiny synthetic OHLC frame with a known overnight/intraday split."""
    idx = pd.date_range("2020-01-01", periods=rows, freq="B", tz="UTC")
    close = pd.DataFrame(
        {s: np.linspace(100.0, 100.0 + rows, rows) for s in UNIVERSE}, index=idx
    )
    open_ = close * 1.01
    return open_, close


def test_session_returns_overnight_uses_previous_close() -> None:
    open_, close = _frame()
    legs = session_returns(open_, close)
    on = legs["overnight"].iloc[1]
    expected = open_.iloc[1] / close.iloc[0] - 1.0
    pd.testing.assert_series_equal(on, expected, check_names=False)
    assert legs["overnight"].iloc[0].eq(0.0).all()


def test_session_legs_decompose_exactly_into_close_to_close() -> None:
    open_, close = _frame()
    legs = session_returns(open_, close)
    recombined = (1.0 + legs["overnight"]) * (1.0 + legs["intraday"]) - 1.0
    assert float((recombined.iloc[1:] - legs["close_to_close"].iloc[1:]).abs().max().max()) < 1e-12


def test_turnover_units_per_session_and_one_off() -> None:
    per = turnover_units(4, 2.0)
    assert list(per) == [2.0, 2.0, 2.0, 2.0]
    one = turnover_units(4, 0.0, one_off=True)
    assert list(one) == [1.0, 0.0, 0.0, 0.0]


def test_apply_costs_subtracts_turnover_times_bps() -> None:
    gross = pd.Series([0.01, -0.02, 0.0], index=pd.RangeIndex(3))
    turn = pd.Series([2.0, 2.0, 2.0], index=pd.RangeIndex(3))
    net = apply_costs(gross, turn, 3.0)
    expected = gross - 2.0 * 3.0 / 10000.0
    pd.testing.assert_series_equal(net, expected, check_names=False)


def test_leg_metrics_reports_explicit_turnover_and_trade_count() -> None:
    idx = pd.date_range("2020-01-01", periods=5, freq="B", tz="UTC")
    ret = pd.Series(np.linspace(-0.01, 0.01, 5), index=idx)
    w = pd.DataFrame(1.0 / 3.0, index=idx, columns=UNIVERSE)
    turn = pd.Series(2.0, index=idx)
    m = leg_metrics(ret, w, turn)
    assert m["annualized_turnover"] == pytest.approx(2.0 * 252)
    assert m["trade_count"] == 5
    assert "canonical_sharpe" in m


def test_walkforward_fold_count_is_33() -> None:
    splits = generate_walkforward_splits(
        "2000-05-26", "2026-10-16", 10.0, 12.0, 6.0, 21, 21
    )
    assert len(splits) == 33
    assert splits[0]["test_start"] == "2010-02-22"
    assert splits[-1]["test_end"] == "2026-07-23"


def test_cached_ohlc_is_readable_and_clean() -> None:
    frames = {s: load_cached_ohlc(s) for s in UNIVERSE}
    for s, df in frames.items():
        assert df[["Open", "Close"]].notna().all().all(), s
        assert df.index.duplicated().sum() == 0, s
    cal = common_calendar(frames)
    assert str(cal.min().date()) == "2000-05-26"
    assert len(cal) == 6637
