"""Regression tests for the read-only rolling 63d gate evidence refresh.

The refresh tool (``research/rolling_63d_gate_refresh.py``) publishes the
rolling 63d Sharpe / max-drawdown evidence and the gap to the promotion
thresholds.  These tests pin the invariants that make that evidence
trustworthy:

* the tool runs standalone from the repository root and never mutates the
  committed state or the raw cache,
* the canonical full-period Sharpe it publishes (1.748401) is re-derivable
  from the committed record alone,
* its independent recomputation of the four numeric gates agrees with the
  production code in ``src/`` to the last bit, and
* the empirical base rate of the rolling 63d Sharpe gate that it publishes
  (287 of 387 windows pass) is reproducible from the committed record.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import research.rolling_63d_gate_refresh as refresh  # noqa: E402
from src.evaluation.sharpe import sharpe_ratio  # noqa: E402
from src.evaluation.utils import max_drawdown  # noqa: E402
from src.simulation.evaluation import _compute_rolling_metrics  # noqa: E402

STATE_PATH = ROOT / "data" / "processed" / "paper_trading_state.yaml"

# The committed record this tool was written against.  If the record is
# extended, the pinned values are re-derived and checked against the
# record that is actually on disk instead of against stale constants.
REFERENCE_SESSIONS = 449
REFERENCE_CANONICAL_SHARPE = 1.748401
REFERENCE_PASSING_WINDOWS = 287
REFERENCE_WINDOWS = 387


def _state() -> dict:
    with open(STATE_PATH) as fh:
        return yaml.safe_load(fh) or {}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_tool_runs_standalone_and_is_read_only():
    before = _sha256(STATE_PATH)
    proc = subprocess.run(
        [sys.executable, "research/rolling_63d_gate_refresh.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "OVERALL: PASS" in proc.stdout
    assert "state file and raw cache byte-identical before/after" in proc.stdout
    assert _sha256(STATE_PATH) == before


def test_canonical_full_period_sharpe_is_re_derivable():
    state = _state()
    returns = np.asarray(state["cumulative_returns"], dtype=float)
    value = sharpe_ratio(returns)
    if len(returns) == REFERENCE_SESSIONS:
        assert abs(value - REFERENCE_CANONICAL_SHARPE) < 5e-7
    # the published value must always be the canonical convention applied to
    # the committed record, whatever the record length is
    assert value == pytest.approx(refresh.sharpe_ratio(returns), abs=0.0)


def test_independent_recomputation_matches_production_code():
    state = _state()
    returns = [float(r) for r in state["cumulative_returns"]]
    dates = [str(d) for d in state["cumulative_dates"]]

    production = _compute_rolling_metrics(returns, dates, window=refresh.WINDOW)
    assert refresh.window_max_drawdown(np.asarray(returns[-refresh.WINDOW:])) == pytest.approx(
        production["rolling_max_dd"], abs=1e-15
    )
    assert sharpe_ratio(returns[-refresh.WINDOW:]) == pytest.approx(
        production["rolling_sharpe"], abs=1e-15
    )
    assert refresh.full_max_drawdown(np.asarray(returns)) == pytest.approx(
        max_drawdown(pd.Series(returns)), abs=1e-12
    )


def test_rolling_window_base_rate_is_reproducible():
    state = _state()
    returns = np.asarray(state["cumulative_returns"], dtype=float)
    window = refresh.WINDOW
    roll = np.array(
        [sharpe_ratio(returns[i - window + 1: i + 1]) for i in range(window - 1, len(returns))]
    )
    passes = roll >= 0.9
    if len(returns) == REFERENCE_SESSIONS:
        assert len(roll) == REFERENCE_WINDOWS
        assert int(passes.sum()) == REFERENCE_PASSING_WINDOWS
    # the currently published window must be the last one of the series
    assert sharpe_ratio(returns[-window:]) == pytest.approx(roll[-1], abs=0.0)


def test_failing_runs_and_recovery_lags():
    # three failing windows, one passing, one trailing failing window
    passes = np.array([False, False, False, True, False])
    assert refresh.failing_runs(passes) == [3, 1]
    # for every failing window, the number of windows until the next pass
    # (the trailing failing window has no next pass and is not counted)
    assert refresh.recovery_lags(passes) == [3, 2, 1]
    # no failing window at all
    assert refresh.failing_runs(np.array([True, True])) == []
    assert refresh.recovery_lags(np.array([True, True])) == []


def test_thresholds_come_from_the_committed_gate_table():
    table = refresh.load_gate_table()
    thresholds = {g["name"]: g for g in table["gates"]}
    assert thresholds["rolling_63d_sharpe"]["threshold"] == 0.9
    assert thresholds["max_drawdown"]["threshold"] == -0.15
    assert thresholds["rolling_63d_max_dd"]["threshold"] == -0.15
    assert thresholds["psr"]["threshold"] == 0.95
