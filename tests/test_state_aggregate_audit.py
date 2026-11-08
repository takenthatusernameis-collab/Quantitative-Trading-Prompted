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

import research.audit_state_aggregates as audit
from src.evaluation.sharpe import sharpe_ratio

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
    # The trailing date is the last session in the committed state; it advances
    # as the paper-trading record is extended, so assert the invariant
    # (start < end, more than 63 sessions) rather than a frozen date.
    with open(STATE_PATH) as fh:
        state = yaml.safe_load(fh) or {}
    assert end == str(state["run_history"][-1]["date"])


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


def test_rolling_max_dd_is_trailing_63d_not_full_history():
    """``rolling_max_dd_63d`` must be measured on the trailing 63 sessions.

    The field name and the promotion gate (config/promotion_gates.yaml
    "rolling_63d_max_dd") both describe a trailing-63-session drawdown. A
    synthetic record longer than 63 sessions where the worst drawdown sits
    outside the trailing window distinguishes the two definitions: the
    full-history value would be the early drawdown, the trailing-63 value the
    recent one (Cycle 1140).
    """
    # 80 flat sessions, then a deep drawdown, then a mild recent window.
    # The record is 86 sessions long, so the trailing-63 window (the last 63)
    # excludes the deep drawdown entirely.
    flat = [0.0] * 80
    deep = [-0.05, -0.05, -0.05]  # worst drawdown, early, OUTSIDE trailing-63
    mild = [0.01, -0.01, 0.005] * 20  # recent, milder
    daily_returns = flat + deep + mild
    nav = [100000.0]
    for r in daily_returns:
        nav.append(nav[-1] * (1.0 + r))
    run_history = []
    for i, v in enumerate(nav[1:]):
        # Unique sequential dates so the record is a valid trading history.
        month = 1 + (i // 28)
        day = 1 + (i % 28)
        run_history.append(
            {
                "date": f"2026-{month:02d}-{day:02d}",
                "nav": v,
                "daily_return": daily_returns[i],
                "daily_pnl": 0.0,
                "turnover": 0.0,
                "vol_scale": 1.0,
                "dd_scale": 1.0,
                "regime_exposure": 1.0,
                "n_positions": 1,
            }
        )
    assert len(run_history) > 63, "record must exceed the rolling window"
    assert len({r["date"] for r in run_history}) == len(run_history), (
        "dates must be unique"
    )

    rets = audit._returns_from_nav(np.array(nav))
    recent = rets[-63:]
    cum = np.cumprod(1.0 + recent)
    peak = np.maximum.accumulate(cum)
    expected_trailing = float((cum / peak - 1.0).min())

    full_cum = np.cumprod(1.0 + rets)
    full_peak = np.maximum.accumulate(full_cum)
    expected_full = float((full_cum / full_peak - 1.0).min())

    assert expected_trailing != pytest.approx(expected_full), (
        "synthetic record does not distinguish trailing-63 from full-history; "
        "test is not discriminating"
    )
    # The audit recomputes the trailing-63 value, not the full-history one.
    # regime_persistence_days is recomputed as the trailing run of identical
    # regime_exposure values, which for an all-1.0 record equals its length.
    regime_persistence = len(run_history)
    turnovers = [0.0] * len(run_history)
    turnover_median = float(np.median(turnovers))
    turnover_p95 = float(np.percentile(turnovers, 95))
    rolling_sharpe = float(sharpe_ratio(rets[-63:]))
    state = {
        "run_history": run_history,
        "rolling_sharpe_63d": rolling_sharpe,
        "rolling_max_dd_63d": expected_trailing,
        "regime_persistence_days": regime_persistence,
        "vol_scale_min": 1.0,
        "vol_scale_max": 1.0,
        "dd_scale_min": 1.0,
        "dd_scale_max": 1.0,
        "turnover_median": turnover_median,
        "turnover_p95": turnover_p95,
        "peak_nav": float(np.max(nav)),
        "max_drawdown": expected_full,
    }
    assert audit.audit(state=state)["all_match"] is True
    # A state storing the full-history value under the rolling-63d name must fail.
    state["rolling_max_dd_63d"] = expected_full
    result = audit.audit(state=state)
    assert result["all_match"] is False
    assert "rolling_max_dd_63d" in result["mismatches"]