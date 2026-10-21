"""Cycle 936: the frozen ``pairs_001`` evaluation tests."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.pairs_001_evaluation import (
    FROZEN,
    EvaluationError,
    build_payload,
    load_frozen_config,
    run_checks,
    verdict,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_hash(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(REPO_ROOT)): _sha256(p)
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


@pytest.fixture(scope="module")
def payload() -> dict:
    return build_payload()


def test_frozen_config_reasserted():
    cfg = load_frozen_config()
    assert cfg["lookback_sessions"] == 126
    assert cfg["z_entry"] == 1.0
    assert tuple(tuple(p) for p in cfg["pairs"]) == tuple(tuple(p) for p in FROZEN["pairs"])
    assert cfg["total_round_trip_bps"] == 3.0
    assert cfg["borrow_bps_per_unit_short_notional_per_rebalance"] == 25.0


def test_post_freeze_drift_fails_closed(monkeypatch):
    import research.pairs_001_evaluation as mod

    original = dict(mod.FROZEN)
    monkeypatch.setitem(mod.FROZEN, "z_entry", 2.0)
    try:
        with pytest.raises(EvaluationError):
            build_payload()
    finally:
        mod.FROZEN.clear()
        mod.FROZEN.update(original)


def test_borrow_charged(payload):
    # Borrow charged on short notional only per pre-registered assumption
    assert payload["evaluation"]["realized_borrow_drag_per_year"] > 0


def test_verdict_follows_frozen_conditions(payload):
    v = verdict(payload)
    assert v["label"].startswith("Rejected/Failed")
    assert "i" in v["fired"]


def test_determinism_two_runs(payload):
    p2 = build_payload()
    assert payload["evaluation"]["wf_mean_oos_sharpe"] == p2["evaluation"]["wf_mean_oos_sharpe"]
    assert payload["verdict"]["label"] == p2["verdict"]["label"]
    assert payload["verdict"]["fired"] == p2["verdict"]["fired"]


def test_data_and_config_unchanged(payload):
    assert payload["data_unchanged"] is True
    assert payload["config_unchanged"] is True


def test_the_reported_turnover_drag_applies_the_cost_rate_once(payload):
    """The reported drag must equal turnover x the committed 3.0 bp rate.

    The Cycle-940 erratum found that the published drag applied the cost rate a
    second time to a series that already carried it (0.0006%/yr published against
    the 2.0607%/yr implied by the record's own turnover figure). See
    ``research/experiments/pairs_001_evaluation_erratum_001.md``.
    """
    ev = payload["evaluation"]
    cost_per_unit = 3.0 / 10_000.0
    implied = ev["realized_turnover_per_year"] * cost_per_unit
    drag = ev["realized_turnover_cost_per_year"]
    assert implied > 0
    assert abs(drag / implied - 1.0) < 0.10
    # the defective value was three orders of magnitude too small
    assert drag > 100.0 * implied * cost_per_unit


def test_the_cost_series_already_carries_the_cost_rate():
    """``path_returns_pair`` returns a cost series, not a turnover series."""
    import numpy as np
    import pandas as pd

    from research.pairs_001_evaluation import path_returns_pair

    index = pd.date_range("2020-01-01", periods=6, freq="B", tz="UTC")
    close = pd.DataFrame({"A": 100.0 + np.arange(6), "B": 50.0 + np.arange(6)}, index=index)
    weights = pd.DataFrame(
        {"A": [0.0, 0.5, 0.5, 0.0, 0.0, 0.5], "B": [-0.0, -0.5, -0.5, 0.0, 0.0, -0.5]},
        index=index,
    )
    cost_per_unit = 3.0 / 10_000.0
    _net, turnover, _borrow = path_returns_pair(
        close, index, weights, cost_per_unit, 25.0, 0.5, [], []
    )
    weight_changes = weights.diff().abs().sum(axis=1).fillna(0.0)
    assert turnover.sum() == pytest.approx(weight_changes.sum() * cost_per_unit)


def test_the_gross_excess_before_any_cost_is_published(payload):
    ev = payload["evaluation"]
    assert ev["gross_excess_annualized"] > ev["net_excess_before_borrow_annualized"]
    assert ev["gross_excess_annualized"] - ev["realized_turnover_cost_per_year"] == pytest.approx(
        ev["net_excess_before_borrow_annualized"], abs=1e-9
    )
    record = (REPO_ROOT / "research" / "experiments" / "pairs_001_evaluation.md").read_text()
    assert "Gross excess (before any cost) annualized" in record
    assert "Excess net of the turnover cost, before borrow, annualized" in record


def test_the_net_excess_and_the_verdict_are_unchanged_by_the_correction(payload):
    """The correction touched the reported drag only."""
    ev = payload["evaluation"]
    assert ev["wf_mean_oos_sharpe"] == pytest.approx(-0.829066502937328, abs=1e-9)
    assert ev["net_excess_annualized"] == pytest.approx(-0.13677385668139808, abs=1e-9)
    assert ev["excess_ci"]["ci_low"] == pytest.approx(-1.219160, abs=1e-6)
    assert ev["excess_ci"]["ci_high"] == pytest.approx(-0.467513, abs=1e-6)
    assert payload["verdict"]["label"].startswith("Rejected/Failed")
    assert sorted(payload["verdict"]["fired"]) == ["i", "iii", "iv"]
