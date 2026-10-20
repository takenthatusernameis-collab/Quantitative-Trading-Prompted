"""Tests for tsmomentum_sma175_validation_audit (Cycle 914).

The audit tool is executed once per test session (it re-derives the published
walk-forward and plateau anchors from the committed cache, which takes about a
minute) and the committed artifacts are then inspected.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

TOOL = "research/tsmomentum_sma175_validation_audit.py"
REPORT = REPO / "research" / "reports" / "tsmomentum_sma175_validation_001.md"
EXPERIMENT = REPO / "research" / "experiments" / "tsmomentum_sma175_validation_001.md"
CANDIDATE_DEFINITION = REPO / "research" / "run_cycle6.py"


@pytest.fixture(scope="module")
def tool_run() -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, TOOL],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )


def test_tool_runs_and_passes(tool_run: subprocess.CompletedProcess):
    assert tool_run.returncode == 0, tool_run.stderr
    assert "OVERALL: PASS" in tool_run.stdout


def test_tool_reports_candidate_gates_and_verdict(tool_run: subprocess.CompletedProcess):
    out = tool_run.stdout
    assert "candidate gates: wf_mean_oos_sharpe=PASS" in out
    assert "positive_fold_rate=PASS" in out
    assert "pooled_oos_trades=PASS" in out
    assert "phase A 1.5391 (PASS)" in out
    assert "phase B 1.5408 (PASS)" in out
    assert "gate SMA-175 PASS" in out
    assert "not promoted" in out


def test_artifacts_exist():
    assert REPORT.exists() and REPORT.stat().st_size > 0
    assert EXPERIMENT.exists() and EXPERIMENT.stat().st_size > 0


def test_report_documents_published_anchors():
    text = REPORT.read_text(encoding="utf-8")
    # Anchor A: the published 48-fold design is reproduced with the incumbent.
    assert "reproduces_published_walk_forward_aggregate]: PASS" in text
    assert "reproduces_published_walk_forward_fold_table]: PASS" in text
    assert "0.9473074720246092" in text
    assert "| total_test_trades | 6013 | 6013 | YES |" in text
    # Anchor B: the published SMA-plateau table is reproduced cell by cell.
    assert "reproduces_published_plateau_table]: PASS" in text
    assert "| 175 | 1.4933 | 1.4933 |" in text
    assert "| 200 | 1.4178 | 1.4178 |" in text


def test_report_documents_candidate_gate_table_and_phases():
    text = REPORT.read_text(encoding="utf-8")
    assert "sma175_gate1_walkforward_mean_oos_sharpe]: PASS" in text
    assert "sma175_gate2_positive_fold_rate]: PASS" in text
    assert "sma175_gate3_pooled_oos_trades]: PASS" in text
    assert "sma175_phase_stable_gate1]: PASS" in text
    assert "sma175_plateau_gate_passes]: PASS" in text
    assert "cost_model_unchanged]: PASS" in text
    assert "1.539964" in text  # candidate 48-fold mean OOS Sharpe
    assert "5946" in text  # candidate pooled OOS trades


def test_report_declares_read_only_and_no_promotion():
    text = REPORT.read_text(encoding="utf-8")
    assert "data_unchanged]: PASS" in text
    assert "config_unchanged]: PASS" in text
    assert "committed_artifacts_unchanged]: PASS" in text
    assert "promotion performed: no" in text
    assert "research/run_cycle6.py` is unchanged" in text


def test_experiment_record_has_required_sections():
    text = EXPERIMENT.read_text(encoding="utf-8")
    for heading in (
        "## Hypothesis reference",
        "## Objective",
        "## Data",
        "## Configuration",
        "## Splits",
        "## Results",
        "## Trial count",
        "## Decision",
        "## Reproduction",
    ):
        assert heading in text
    assert "tsmomentum_phase_stability_fix_001.md" in text  # prior-cycle evidence cited
    assert "in-sample" in text  # selection caveat carried into the record


def test_candidate_definition_not_promoted():
    source = CANDIDATE_DEFINITION.read_text(encoding="utf-8")
    assert "SPY_SMA_WINDOW = 200" in source
    diff = subprocess.run(
        ["git", "diff", "--exit-code", "--", "research/run_cycle6.py"],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    assert diff.returncode == 0, diff.stdout


def test_data_and_config_untouched():
    status = subprocess.run(
        ["git", "status", "--porcelain", "data/", "config/"],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    assert status.returncode == 0, status.stderr
    assert status.stdout.strip() == ""
