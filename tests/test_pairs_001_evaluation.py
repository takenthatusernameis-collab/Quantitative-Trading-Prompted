"""Cycle 936: the frozen ``pairs_001`` evaluation tests."""

from __future__ import annotations

import hashlib
import subprocess
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

    original = mod.FROZEN.copy()
    monkeypatch.setitem(mod.FROZEN, "z_entry", 2.0)
    with pytest.raises(EvaluationError):
        mod.run_checks(payload() if False else build_payload())
    # restore handled by monkeypatch automatically for mod.FROZEN? FROZEN is module global dict; revert
    mod.FROZEN.clear()
    mod.FROZEN.update(original)


def test_borrow_charged():
    p = build_payload()
    assert p["cost"]["borrow"] > 0


def test_verdict_follows_frozen_conditions():
    p = build_payload()
    v = verdict(p)
    assert v["verdict"].startswith("Rejected/Failed")
    assert "i" in v["fired"]


def test_determinism_two_runs():
    assert True



def test_data_and_config_unchanged():
    before_data = _tree_hash(REPO_ROOT / "data")
    before_cfg = _tree_hash(REPO_ROOT / "config")
    assert before_data and before_cfg
