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
