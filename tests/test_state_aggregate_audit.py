"""Offline integrity audit of the stored aggregate fields in the canonical
paper-trading state.

Prior cycles verified the ``low_rolling_sharpe`` drift flag and the extension
clock gate, but never independently recomputed the *other* stored aggregates
(``rolling_sharpe_63d``, ``rolling_max_dd_63d``, ``regime_persistence_days``,
``vol_scale_min/max``, ``dd_scale_min/max``, ``turnover_median/p95``,
``peak_nav``, ``max_drawdown``) from the per-session record. This test closes
that gap using the exact update formulas in
``src/simulation/paper_trading.run_daily_paper_update``.

It is read-only: it opens the committed state, recomputes, and asserts
equality. It writes nothing and never touches the network or the raw cache.
"""

import hashlib
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import research.audit_state_aggregates as audit  # noqa: E402
from src.evaluation.sharpe import sharpe_ratio  # noqa: E402

STATE_PATH = ROOT / "data" / "processed" / "paper_trading_state.yaml"


def _state_snapshot() -> str:
    return hashlib.sha256(STATE_PATH.read_bytes()).hexdigest()


def test_state_file_exists_and_is_committed():
    assert STATE_PATH.exists()
    assert STATE_PATH.parent.exists()


def test_audit_is_read_only():
    before = _state_snapshot()
    result = audit.audit()
    assert _state_snapshot() == before
    assert "recomputed" in result and "stored" in result


def test_audit_recomputes_all_stored_aggregates_from_run_history():
    result = audit.audit()
    assert result["all_match"] is True, result["mismatches"]
    # every stored aggregate must have a recomputed counterpart
    assert set(result["recomputed"]) == set(result["stored"])
    assert len(result["recomputed"]) == 11


def test_audit_sessions_span_a_real_history():
    result = audit.audit()
    assert result["sessions"] > 63
    start, end = result["date_range"].split(" -> ")
    assert start < end
    assert end == "2026-10-23"


def test_running_sharpe_matches_canonical_sharpe_function():
    """The 63d rolling Sharpe must use the repo's sharpe_ratio convention."""
    with open(STATE_PATH) as fh:
        state = yaml.safe_load(fh) or {}
    rh = state["run_history"]
    nav = np.array([float(r["nav"]) for r in rh], dtype=float)
    rets = np.empty_like(nav)
    rets[0] = nav[0] / 100000.0 - 1.0
    rets[1:] = nav[1:] / nav[:-1] - 1.0
    recomputed = float(sharpe_ratio(rets[-63:]))
    assert recomputed == pytest.approx(state["rolling_sharpe_63d"])


def test_audit_main_exits_zero_when_consistent():
    assert audit.main() == 0


def test_audit_flags_injected_mismatch():
    """The audit must not silently pass on a corrupted state."""
    bad = {
        "run_history": [
            {"date": "2026-10-22", "nav": 100000.0, "daily_return": 0.0,
             "daily_pnl": 0.0, "turnover": 0.0, "vol_scale": 1.0,
             "dd_scale": 1.0, "regime_exposure": 1.0, "n_positions": 1},
            {"date": "2026-10-23", "nav": 100100.0, "daily_return": 0.001,
             "daily_pnl": 100.0, "turnover": 0.0, "vol_scale": 1.0,
             "dd_scale": 1.0, "regime_exposure": 1.0, "n_positions": 1},
        ],
        "rolling_sharpe_63d": 999.0,  # impossible value
        "rolling_max_dd_63d": 0.0,
        "regime_persistence_days": 1,
        "vol_scale_min": 1.0,
        "vol_scale_max": 1.0,
        "dd_scale_min": 1.0,
        "dd_scale_max": 1.0,
        "turnover_median": 0.0,
        "turnover_p95": 0.0,
        "peak_nav": 100100.0,
        "max_drawdown": 0.0,
    }
    result = audit.audit(state=bad)
    assert result["all_match"] is False
    assert "rolling_sharpe_63d" in result["mismatches"]