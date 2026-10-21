"""Tests for the SMA-175 phase stability audit (Cycle 916)."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import pytest

from research.tsmomentum_sma175_phase_stability_audit import (
    GATE_WF_MEAN_MIN,
    OUT_EXP,
    OUT_REPORT,
    run_audit,
)

TOOL = "research/tsmomentum_sma175_phase_stability_audit.py"


def _run_tool(*extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, TOOL, *extra],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="module")
def payload() -> dict:
    return run_audit()


def test_tool_runs_and_passes():
    result = _run_tool()
    assert result.returncode == 0, result.stderr
    assert "OVERALL: PASS" in result.stdout


def test_artifacts_exist():
    assert OUT_REPORT.exists()
    assert OUT_EXP.exists()


def test_read_only_guarantees(payload):
    ro = payload["read_only"]
    assert ro["data_unchanged"] is True
    assert ro["config_unchanged"] is True
    assert ro["committed_artifacts_unchanged"] is True


def test_phase_decomposition_is_exact(payload):
    phases = payload["phase_decomposition"]
    assert phases["phases_are_pairwise_disjoint"] is True
    assert phases["union_covers_published_folds"] is True
    assert len(phases["phase_a_fold_numbers"]) == 24
    assert len(phases["phase_b_fold_numbers"]) == 24
    assert set(phases["phase_a_fold_numbers"]) | set(phases["phase_b_fold_numbers"]) == set(range(1, 49))
    assert set(phases["phase_a_fold_numbers"]) & set(phases["phase_b_fold_numbers"]) == set()
    mean_a = phases["phase_a"]["mean_test_sharpe"]
    mean_b = phases["phase_b"]["mean_test_sharpe"]
    assert abs((mean_a + mean_b) / 2.0 - payload["published_mean_recomputed"]) <= 1e-9
    assert phases["phase_means_average_to_published_mean"] is True


def test_fold_influence_consistent(payload):
    infl = payload["fold_influence"]
    influence = infl["influence"]
    assert len(influence) == 48
    # recompute loo for most influential
    sharpes = [float(item["test_sharpe"]) for item in influence]
    folds = [int(item["fold"]) for item in influence]
    most = infl["most_influential_fold"]
    idx = folds.index(most["fold"])
    loo = sum(sharpes[:idx] + sharpes[idx + 1:]) / (len(sharpes) - 1)
    assert abs(loo - most["loo_mean"]) <= 1e-12


def test_stability_verdict(payload):
    stab = payload["stability"]
    # Both conditions for "pass_stable"
    assert stab["gate1_outcome_changes_between_phases"] is False
    assert stab["gate1_outcome_changes_when_thin_trade_folds_excluded"] is False
    assert stab["published_pass_stable"] is True


def test_sma175_higher_mean(payload):
    assert payload["published_mean_recomputed"] > 1.5  # higher than incumbent 0.9473
    assert payload["sma_window"] == 175
