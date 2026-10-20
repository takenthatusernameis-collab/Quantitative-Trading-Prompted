"""Regression tests for the shared month-end rebalance schedule (Cycle 870).

The frozen candidate configurations (``config/sectorrotation_candidate_001.yaml``,
``config/csmomentum_candidate_001.yaml``, ``config/macroregime_candidate_001.yaml``)
specify ``rebalance_schedule: monthly`` with ``signal_lag_days: 1``, but until
Cycle 870 no code path executed that schedule: ``src/backtest/engine.py`` ignored
its ``rebalance_freq`` argument (the universe was re-ranked every session) and
``src/simulation/engine.py``'s ``"M"`` branch used the *calendar*
``index.is_month_end`` on a *trading* calendar.

These tests pin the semantics of the single shared implementation
(``src/backtest/rebalance.py``) and the invariant that the fix is opt-in:

* a month whose last calendar day is a weekend rebalances on the Friday session;
* the signal formed on the month-end session is held from the **next** session;
* no position exists before the first valid signal (no back-fill);
* the engine's opt-in path reproduces the config-faithful research path;
* the **default** path and the incumbent's committed artifacts do not move.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import research.sectorrotation_long_sample_feasibility as feas  # noqa: E402
from src.backtest.engine import run_backtest  # noqa: E402
from src.backtest.rebalance import (  # noqa: E402
    build_month_end_weights,
    month_end_sessions,
    normalize_schedule,
)
from src.evaluation.sharpe import sharpe_ratio  # noqa: E402
from src.evaluation.statistics import compute_psr  # noqa: E402
from src.evaluation.utils import max_drawdown  # noqa: E402
from src.features.momentum import compute_momentum, select_top_decile  # noqa: E402

SECTOR_UNIVERSE = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
SECTOR_START = "1998-12-22"
SECTOR_END = "2026-10-08"

INCUMBENT_REPORT = ROOT / "research" / "reports" / "promotion_feasibility_backtest_001.md"
# The incumbent's universe and signal (config/simulation_candidate_001.yaml).
INCUMBENT_UNIVERSE = ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"]
INCUMBENT_LOOKBACK = 226
INCUMBENT_SKIP = 21
INCUMBENT_TOP_FRACTION = 0.5
INCUMBENT_REBALANCE_FREQ = "monthly"
# The incumbent's committed code-level numbers are the numbers of the
# **reference sample**: the committed raw cache truncated at
# INCUMBENT_REFERENCE_END, i.e. the 8487-session sample the incumbent was
# first published against.  The engine's path is point-in-time (the weights
# at t use data up to t only), so truncating the return series reproduces the
# published path exactly, and an append-only extension of the raw cache --
# which necessarily moves the full-sample Sharpe -- cannot invalidate the
# invariant.
INCUMBENT_REFERENCE_END = "2026-10-16"
INCUMBENT_REFERENCE_SESSIONS = 8487
INCUMBENT_SHARPE = 0.5646255767978904
INCUMBENT_MAX_DD = -0.6224126346564325
INCUMBENT_PSR = 2.2219753177036448e-08
INCUMBENT_FAILED_GATES = "['full_period_sharpe', 'rolling_63d_sharpe', 'max_drawdown', 'psr']"


def _incumbent_sample_window() -> tuple[str, str]:
    """The sample window the incumbent's backtest is run on."""
    frames = [
        pd.read_parquet(ROOT / "data" / "raw" / f"{symbol}.parquet")
        for symbol in INCUMBENT_UNIVERSE
    ]
    start = max(df.index.min() for df in frames).date().isoformat()
    end = min(df.index.max() for df in frames).date().isoformat()
    return start, end


def _synthetic_calendar() -> pd.DatetimeIndex:
    """A small session calendar with a weekend month end (February 2020)."""
    return pd.DatetimeIndex(
        [
            "2020-01-30",  # Thursday
            "2020-01-31",  # Friday, last calendar day of January
            "2020-02-03",  # Monday
            "2020-02-04",
            "2020-02-05",
            "2020-02-06",
            "2020-02-07",
            "2020-02-10",
            "2020-02-11",
            "2020-02-12",
            "2020-02-13",
            "2020-02-14",
            "2020-02-18",
            "2020-02-19",
            "2020-02-20",
            "2020-02-21",
            "2020-02-24",
            "2020-02-25",
            "2020-02-26",
            "2020-02-27",
            "2020-02-28",  # Friday, last session of February
            "2020-03-02",  # Monday
            "2020-03-31",  # Tuesday, last session of March
        ],
        tz="UTC",
    )


def _synthetic_mask(index: pd.DatetimeIndex) -> pd.DataFrame:
    """Selects A in January and B from February onwards."""
    mask = pd.DataFrame(False, index=index, columns=["A", "B"])
    mask.loc[index <= pd.Timestamp("2020-01-31", tz="UTC"), "A"] = True
    mask.loc[index >= pd.Timestamp("2020-02-03", tz="UTC"), "B"] = True
    return mask


def test_month_end_is_the_last_session_of_the_month():
    index = _synthetic_calendar()
    got = [d.date().isoformat() for d in month_end_sessions(index)]
    assert got == ["2020-01-31", "2020-02-28", "2020-03-31"]


def test_weekend_month_end_rebalances_on_the_friday_session():
    """February 2020 ends on Saturday 29 Feb -> the rebalance is Friday 28 Feb."""
    index = _synthetic_calendar()
    weights, segments = build_month_end_weights(_synthetic_mask(index))

    february = [s for s in segments if s["signal_date"].month == 2]
    assert len(february) == 1
    signal_date = february[0]["signal_date"]
    # The last calendar day of February 2020 is Saturday 2020-02-29.
    assert pd.Timestamp("2020-02-29").dayofweek == 5
    assert signal_date.date().isoformat() == "2020-02-28"
    assert signal_date.dayofweek == 4  # Friday
    # The calendar predicate the simulation engine uses does not fire here.
    assert not bool(pd.Timestamp("2020-02-28").is_month_end)
    # The February selection (B) becomes effective from the next session.
    effective = february[0]["effective_date"]
    assert effective.date().isoformat() == "2020-03-02"
    assert weights.loc[effective, "B"] == pytest.approx(1.0)
    assert weights.loc[effective, "A"] == pytest.approx(0.0)


def test_signal_is_held_from_the_next_session():
    index = _synthetic_calendar()
    weights, segments = build_month_end_weights(_synthetic_mask(index))
    assert len(segments) == 2
    for seg in segments:
        signal_pos = int(index.get_loc(seg["signal_date"]))
        effective_pos = int(index.get_loc(seg["effective_date"]))
        assert effective_pos == signal_pos + 1
    # nothing is held before the first effective date
    first_eff = segments[0]["effective_date"]
    assert float(weights.loc[weights.index < first_eff].abs().sum(axis=1).max()) == 0.0
    # the January selection is held from 2020-02-03 until 2020-03-02
    assert weights.loc[pd.Timestamp("2020-02-03", tz="UTC"), "A"] == pytest.approx(1.0)
    assert weights.loc[pd.Timestamp("2020-02-28", tz="UTC"), "A"] == pytest.approx(1.0)
    assert weights.loc[pd.Timestamp("2020-03-02", tz="UTC"), "A"] == pytest.approx(0.0)


def test_no_position_exists_before_the_first_valid_signal():
    """A mask without a valid cross-section opens no position (no back-fill)."""
    index = _synthetic_calendar()
    empty = pd.DataFrame(False, index=index, columns=["A", "B"])
    weights, segments = build_month_end_weights(empty)
    assert segments == []
    assert float(weights.abs().sum(axis=1).max()) == 0.0

    # A mask that only becomes valid at the February month end: nothing is
    # held before the first valid signal, and the first valid signal is not
    # back-filled to earlier sessions.
    late = pd.DataFrame(False, index=index, columns=["A", "B"])
    late.loc[index >= pd.Timestamp("2020-02-28", tz="UTC"), "A"] = True
    weights, segments = build_month_end_weights(late)
    assert len(segments) == 1
    assert segments[0]["signal_date"].date().isoformat() == "2020-02-28"
    assert segments[0]["effective_date"].date().isoformat() == "2020-03-02"
    assert float(weights.loc[weights.index < segments[0]["effective_date"]].abs().sum(axis=1).max()) == 0.0


def test_unknown_schedule_is_a_hard_error():
    assert normalize_schedule("monthly") == "month_end"
    assert normalize_schedule("M") == "month_end"
    assert normalize_schedule("daily") == "daily"
    with pytest.raises(ValueError):
        normalize_schedule("weekly")
    with pytest.raises(ValueError):
        normalize_schedule(None)


def test_engine_opt_in_reproduces_the_config_faithful_research_path():
    """Acceptance criterion 2: max |net_return difference| <= 1e-12."""
    data = feas.fetch_universe(SECTOR_UNIVERSE, SECTOR_START, SECTOR_END, force=False)
    close = data.xs("Close", level=0, axis=1).ffill().dropna(how="all")
    momentum = compute_momentum(close, lookback=252, skip=21)
    mask = select_top_decile(momentum, top_fraction=0.5)
    ref_weights, _segments = feas.build_monthly_weights(
        close, mask, feas.month_end_dates(close.index)
    )
    cost_per_trade = feas.get_cost_params()[0] + feas.get_cost_params()[1]
    ref_net, _turnover = feas.portfolio_returns(close, ref_weights, cost_per_trade)

    net, weights, _metrics = run_backtest(
        symbols=SECTOR_UNIVERSE,
        start_date=SECTOR_START,
        end_date=SECTOR_END,
        lookback=252,
        skip=21,
        top_fraction=0.5,
        rebalance_freq="monthly",
        rebalance_schedule="month_end",
    )
    assert net.index.equals(ref_net.index)
    assert float(np.max(np.abs((net - ref_net).to_numpy()))) <= 1e-12
    assert np.array_equal(weights.to_numpy(), ref_weights.to_numpy())
    # structural property of the schedule: the portfolio can only change on
    # the session that follows a month-end session.
    month_ends = set(month_end_sessions(weights.index))
    change_sessions = set(weights.index[weights.diff().abs().sum(axis=1) > 1e-10])
    for session in change_sessions:
        pos = int(weights.index.get_loc(session))
        assert pos > 0
        assert weights.index[pos - 1] in month_ends


def test_engine_default_path_is_unchanged():
    """The opt-in parameter must not change the default behaviour."""
    default_net, default_weights, _ = run_backtest(
        symbols=SECTOR_UNIVERSE,
        start_date=SECTOR_START,
        end_date=SECTOR_END,
        lookback=252,
        skip=21,
        top_fraction=0.5,
    )
    explicit_none_net, explicit_none_weights, _ = run_backtest(
        symbols=SECTOR_UNIVERSE,
        start_date=SECTOR_START,
        end_date=SECTOR_END,
        lookback=252,
        skip=21,
        top_fraction=0.5,
        rebalance_schedule=None,
    )
    daily_net, daily_weights, _ = run_backtest(
        symbols=SECTOR_UNIVERSE,
        start_date=SECTOR_START,
        end_date=SECTOR_END,
        lookback=252,
        skip=21,
        top_fraction=0.5,
        rebalance_schedule="daily",
    )
    _month_end_net, month_end_weights, _ = run_backtest(
        symbols=SECTOR_UNIVERSE,
        start_date=SECTOR_START,
        end_date=SECTOR_END,
        lookback=252,
        skip=21,
        top_fraction=0.5,
        rebalance_schedule="month_end",
    )
    assert np.array_equal(default_net.to_numpy(), explicit_none_net.to_numpy())
    assert np.array_equal(default_net.to_numpy(), daily_net.to_numpy())
    assert np.array_equal(default_weights.to_numpy(), explicit_none_weights.to_numpy())
    assert np.array_equal(default_weights.to_numpy(), daily_weights.to_numpy())
    # the default path re-ranks every session (the defect that is now opt-in)
    default_trade_days = int((default_weights.diff().abs().sum(axis=1) > 1e-10).sum())
    month_end_trade_days = int((month_end_weights.diff().abs().sum(axis=1) > 1e-10).sum())
    assert default_trade_days > 3 * month_end_trade_days


def test_incumbent_artifacts_are_unchanged():
    """Acceptance criterion 1: the incumbent's artifacts must not move."""
    before = INCUMBENT_REPORT.read_bytes()
    proc = subprocess.run(
        [sys.executable, "research/promotion_feasibility_backtest.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "OVERALL: PASS" in proc.stdout
    assert "decision=NO-GO" in proc.stdout
    assert INCUMBENT_FAILED_GATES in proc.stdout
    # The committed report is the snapshot of the current sample and must be
    # reproduced byte-identically.  It is also the data-change alarm: a
    # refreshed raw cache changes the numbers in the report, and the refreshed
    # report has to be committed together with the refreshed data.
    assert INCUMBENT_REPORT.read_bytes() == before, (
        "the promotion report is not reproduced byte-identically: either the "
        "code changed the numbers, or the raw cache changed and the report "
        "has to be re-committed with the refreshed data"
    )
    report_text = INCUMBENT_REPORT.read_text()
    assert "NO-GO" in report_text


def test_incumbent_numbers_match_the_committed_report():
    """The numbers the committed report publishes are the numbers the
    incumbent path produces on the current sample, and the published artifact
    is unchanged on the reference sample.

    The current-sample numbers are re-derived instead of pinned to a literal,
    so that an append-only extension of the raw cache cannot invalidate the
    test; the reference-sample numbers (the published artifact) are pinned
    exactly, so a rewrite of the history still fails it.
    """
    start, end = _incumbent_sample_window()
    net, _weights, _ = run_backtest(
        symbols=INCUMBENT_UNIVERSE,
        start_date=start,
        end_date=end,
        lookback=INCUMBENT_LOOKBACK,
        skip=INCUMBENT_SKIP,
        top_fraction=INCUMBENT_TOP_FRACTION,
        rebalance_freq=INCUMBENT_REBALANCE_FREQ,
    )
    full_sharpe = sharpe_ratio(net)
    full_dd = max_drawdown(net)
    full_psr = compute_psr(net, sr_target=1.4178, seed=20240101)["psr_normal"]
    report_text = INCUMBENT_REPORT.read_text()
    assert f'"paper_sharpe": {full_sharpe!r}' in report_text
    assert f'"paper_max_dd": {full_dd!r}' in report_text
    assert f'"psr_normal": {full_psr!r}' in report_text
    # the published artifact: the reference sample
    reference = net.loc[: INCUMBENT_REFERENCE_END]
    assert len(reference) == INCUMBENT_REFERENCE_SESSIONS
    assert sharpe_ratio(reference) == pytest.approx(INCUMBENT_SHARPE, abs=1e-12)
    assert max_drawdown(reference) == pytest.approx(INCUMBENT_MAX_DD, abs=1e-12)
    psr = compute_psr(reference, sr_target=1.4178, seed=20240101)["psr_normal"]
    assert psr == pytest.approx(INCUMBENT_PSR, abs=1e-15)
