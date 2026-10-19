"""Regression tests for the sectorrotation_001 long-sample feasibility backtest.

The tool (``research/sectorrotation_long_sample_feasibility.py``) publishes the
long-sample feasibility evidence for the frozen ``sectorrotation_001`` candidate
in the pattern of ``research/promotion_feasibility_backtest.py``.  These tests
pin the invariants that make that evidence trustworthy:

* the tool runs standalone from the repository root and never mutates the raw
  cache,
* the headline long-sample number is re-derivable from the cached data alone
  and is the value published in the committed report,
* the aligned price frame is still the one that was frozen in the
  pre-registration (content hash ``5e2d48e6579a53cd``),
* the config-faithful month-end rebalance is point-in-time (a position is only
  ever held from the session after the month-end that produced it), and
* the gate table and its decision mapping are applied as documented in
  ``config/promotion_gates.yaml``.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import research.sectorrotation_long_sample_feasibility as feas  # noqa: E402
from src.evaluation.sharpe import sharpe_ratio  # noqa: E402
from src.evaluation.utils import max_drawdown  # noqa: E402
from src.features.momentum import compute_momentum, select_top_decile  # noqa: E402

REPORT = ROOT / "research" / "reports" / "sectorrotation_long_sample_feasibility_001.md"
UNIVERSE = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]

# Published in the committed report (canonical convention, invested sample).
REFERENCE_SHARPE = 0.472367
REFERENCE_PSR_TARGET_09 = 0.006618


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _raw_hashes() -> dict[str, str]:
    return {s: _sha256(ROOT / "data" / "raw" / f"{s}.parquet") for s in UNIVERSE}


def _aligned_close() -> pd.DataFrame:
    data = feas.fetch_universe(UNIVERSE, "1998-12-22", "2026-10-08", force=False)
    close = data.xs("Close", level=0, axis=1)
    return close.ffill().dropna(how="all")


def test_tool_runs_standalone_and_is_read_only():
    before = _raw_hashes()
    proc = subprocess.run(
        [sys.executable, "research/sectorrotation_long_sample_feasibility.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "OVERALL: PASS" in proc.stdout
    assert "NO-GO" in proc.stdout
    assert _raw_hashes() == before


def test_aligned_frame_is_the_preregistered_one():
    close = _aligned_close()
    assert close.shape == (6991, 9)
    assert int(close.isna().sum().sum()) == 0
    assert feas.content_hash(close).startswith(feas.ALIGNED_FRAME_HASH_PREFIX)


def test_headline_metrics_are_reproducible_from_the_cached_data():
    close = _aligned_close()
    momentum = compute_momentum(close, lookback=252, skip=21)
    mask = select_top_decile(momentum, top_fraction=0.5)
    weights, segments = feas.build_monthly_weights(
        close, mask, feas.month_end_dates(close.index)
    )
    assert segments, "no rebalance was produced"
    cost_per_trade = feas.get_cost_params()[0] + feas.get_cost_params()[1]
    net_ret, turnover = feas.portfolio_returns(close, weights, cost_per_trade)
    invested = close.index[weights.sum(axis=1) > 0]
    stats = feas.compute_stats(net_ret, weights, turnover, invested, cost_per_trade)
    assert stats["sharpe_canonical"] == pytest.approx(REFERENCE_SHARPE, abs=5e-7)
    assert stats["sharpe_canonical"] == pytest.approx(
        sharpe_ratio(net_ret.loc[invested]), abs=1e-12
    )
    assert stats["max_drawdown"] == pytest.approx(max_drawdown(net_ret.loc[invested]), abs=1e-12)
    report_text = REPORT.read_text()
    assert f"{stats['sharpe_canonical']:.6f}" in report_text
    assert f"{REFERENCE_PSR_TARGET_09:.6f}" in report_text


def test_month_end_dates_are_the_last_trading_day_of_each_month():
    idx = pd.DatetimeIndex(
        ["2020-01-30", "2020-01-31", "2020-02-03", "2020-02-28"], tz="UTC"
    )
    got = feas.month_end_dates(idx)
    assert [d.date().isoformat() for d in got] == ["2020-01-31", "2020-02-28"]


def test_monthly_weights_are_point_in_time():
    idx = pd.DatetimeIndex(
        [
            "2020-01-02", "2020-01-03", "2020-01-31", "2020-02-03", "2020-02-04",
            "2020-02-28", "2020-03-02", "2020-03-31", "2020-04-01",
        ],
        tz="UTC",
    )
    close = pd.DataFrame(
        np.arange(len(idx) * 2, dtype=float).reshape(len(idx), 2) + 100.0,
        index=idx,
        columns=["A", "B"],
    )
    # A is always stronger than B -> the mask selects A only
    mask = pd.DataFrame(
        [[True, False]] * len(idx),
        index=idx,
        columns=["A", "B"],
    )
    weights, segments = feas.build_monthly_weights(close, mask, feas.month_end_dates(idx))
    assert len(segments) == 3  # January, February and March month-ends
    for seg in segments:
        # the position is only held from the session after the signal date
        assert seg["effective_date"] > seg["signal_date"]
        assert weights.loc[seg["effective_date"], "A"] == pytest.approx(1.0)
        assert weights.loc[seg["effective_date"], "B"] == pytest.approx(0.0)
    # a month-end with no signal (all-False mask) carries no position
    empty = pd.DataFrame(False, index=idx, columns=["A", "B"])
    w_empty, seg_empty = feas.build_monthly_weights(close, empty, feas.month_end_dates(idx))
    assert seg_empty == []
    assert float(w_empty.abs().sum(axis=1).max()) == 0.0


def test_gate_decision_mapping_matches_the_documented_policy():
    gates = feas.load_yaml(feas.CONFIG_GATES)
    base = {
        "track_record_length": 1000.0,
        "full_period_sharpe": 1.0,
        "rolling_63d_sharpe": 1.0,
        "max_drawdown": -0.05,
        "rolling_63d_max_dd": -0.05,
    }
    gates_res, failed, decision, zone = feas.evaluate_gates(
        gates, base, psr_value=0.99, regime_flips_applicable=False
    )
    assert failed == []
    assert decision == "GO"
    assert gates_res["regime_flips"]["status"] == "not_applicable"

    # only the PSR gate fails, inside the grey zone -> INCONCLUSIVE
    _, failed, decision, zone = feas.evaluate_gates(
        gates, base, psr_value=0.70, regime_flips_applicable=False
    )
    assert failed == ["psr"]
    assert zone == "grey_zone"
    assert decision == "INCONCLUSIVE"

    # only the PSR gate fails, below the grey zone -> NO-GO
    _, failed, decision, zone = feas.evaluate_gates(
        gates, base, psr_value=0.10, regime_flips_applicable=False
    )
    assert failed == ["psr"]
    assert zone == "below_grey"
    assert decision == "NO-GO"

    # another gate fails -> NO-GO regardless of the PSR
    bad = dict(base)
    bad["full_period_sharpe"] = 0.4
    _, failed, decision, _ = feas.evaluate_gates(
        gates, bad, psr_value=0.99, regime_flips_applicable=False
    )
    assert "full_period_sharpe" in failed
    assert decision == "NO-GO"

    # a short record is inconclusive
    short = dict(base)
    short["track_record_length"] = 10.0
    _, failed, decision, _ = feas.evaluate_gates(
        gates, short, psr_value=0.99, regime_flips_applicable=False
    )
    assert decision == "INCONCLUSIVE"


def test_frozen_candidate_config_is_unchanged():
    cfg = feas.load_yaml(feas.CONFIG_CAND)
    assert cfg["candidate_id"] == "sectorrotation_001"
    assert list(cfg["universe"]) == UNIVERSE
    assert cfg["signal"]["lookback"] == 252
    assert cfg["signal"]["skip"] == 21
    assert cfg["signal"]["top_fraction"] == 0.5
    assert cfg["signal"]["rebalance_freq"] == "monthly"
    assert cfg["cost_model"]["total_round_trip_bps"] == 3.0
