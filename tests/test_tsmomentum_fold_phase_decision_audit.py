"""Tests for the ``tsmomentum_spytrend_001`` fold-phase decision audit (Cycle 912).

The audit consumes Cycle 911 sensitivity outputs and produces a decision record
showing the incumbent is not phase-stable (phase B fails gate-1) and should be
downgraded to exploratory.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import pytest  # noqa: E402

from research.tsmomentum_fold_phase_decision_audit import (  # noqa: E402
    GATE_WF_MEAN_MIN,
    PUBLISHED_WF_MEAN,
    run_audit,
)

TOOL = "research/tsmomentum_fold_phase_decision_audit.py"
REPORT = REPO / "research" / "reports" / "tsmomentum_fold_phase_decision_001.md"
EXPERIMENT = REPO / "research" / "experiments" / "tsmomentum_fold_phase_decision_001.md"
PUBLISHED_RECORD = REPO / "research" / "experiments" / "tsmomentum_regime_filter_wf_001.md"
ROBUSTNESS_REPORT = REPO / "research" / "reports" / "tsmomentum_walkforward_mean_robustness_001.md"


def _run_tool(*extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, TOOL, *extra],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _committed_artifact_hashes() -> dict[str, str]:
    res = subprocess.run(
        ["git", "ls-files", "src", "config", "research/experiments", "research/reports"],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    out: dict[str, str] = {}
    for rel in res.stdout.splitlines():
        rel = rel.strip()
        if not rel:
            continue
        path = REPO / rel
        if path.is_file():
            out[rel] = _sha256(path)
    return out


@pytest.fixture(scope="module")
def payload() -> dict:
    return run_audit()


def test_tool_runs_and_passes():
    result = _run_tool()
    assert result.returncode == 0, result.stderr
    assert "OVERALL: PASS" in result.stdout


def test_artifacts_exist():
    assert REPORT.exists()
    assert EXPERIMENT.exists()


def test_consumes_cycle911_evidence(payload):
    assert payload["cycle911_robustness"]["overall"] == "PASS"
    assert ROBUSTNESS_REPORT.exists()


def test_phase_b_fails_gate1(payload):
    phases = payload["phase_decomposition"]
    assert phases["phase_b"]["mean_test_sharpe"] < GATE_WF_MEAN_MIN
    assert phases["gate1_phase_b"] == "FAIL"
    assert phases["phase_a"]["mean_test_sharpe"] >= GATE_WF_MEAN_MIN
    assert phases["gate1_phase_a"] == "PASS"
    assert phases["gate1_outcome_changes_between_phases"] is True


def test_published_pass_not_stable(payload):
    assert payload["stability"]["published_pass_stable"] is False
    assert payload["stability"]["gate1_outcome_changes_between_phases"] is True


def test_thin_trade_folds_identified(payload):
    infl = payload["fold_influence"]
    assert infl["thin_trade_folds"] == [12, 13]


def test_decision_downgrades_incumbent(payload):
    decision = payload["decision"]
    assert "Exploratory" in decision["label"] or "downgrade" in decision["label"].lower()
    assert "phase" in decision["detail"].lower()


def test_read_only_guarantees(payload):
    assert payload["read_only"]["data_unchanged"] is True
    assert payload["read_only"]["config_unchanged"] is True
    assert payload["read_only"]["committed_artifacts_unchanged"] is True


def test_committed_artifacts_are_byte_identical_before_and_after():
    before = _committed_artifact_hashes()
    published_key = str(PUBLISHED_RECORD.relative_to(REPO))
    assert published_key in before
    result = _run_tool()
    assert result.returncode == 0, result.stderr
    after = _committed_artifact_hashes()
    assert after == before
    assert _sha256(PUBLISHED_RECORD) == before[published_key]


def test_two_consecutive_runs_are_bit_for_bit_deterministic():
    first = _run_tool()
    assert first.returncode == 0, first.stderr
    report_1 = REPORT.read_bytes()
    experiment_1 = EXPERIMENT.read_bytes()
    second = _run_tool()
    assert second.returncode == 0, second.stderr
    assert REPORT.read_bytes() == report_1
    assert EXPERIMENT.read_bytes() == experiment_1
    assert first.stdout == second.stdout


def test_fails_closed_on_missing_experiments_dir(tmp_path):
    result = _run_tool(
        "--experiments-dir",
        str(tmp_path / "does-not-exist"),
        "--report-out",
        str(tmp_path / "report.md"),
        "--experiment-out",
        str(tmp_path / "experiment.md"),
    )
    assert result.returncode != 0
    assert "ERROR" in result.stderr
