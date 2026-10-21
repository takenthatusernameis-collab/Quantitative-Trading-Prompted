"""Tests for the SMA-175 candidate evaluation hook (Cycle 918)."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import pytest

from research.tsmomentum_sma175_candidate_eval import (
    OUT_REPORT,
    run_candidate_eval,
)

TOOL = "research/tsmomentum_sma175_candidate_eval.py"


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
    return run_candidate_eval()


def test_tool_runs_and_passes():
    result = _run_tool()
    assert result.returncode == 0, result.stderr
    assert "OVERALL: PASS" in result.stdout


def test_artifacts_exist():
    assert OUT_REPORT.exists()


def test_report_contains_metrics():
    content = OUT_REPORT.read_text()
    assert "Mean test Sharpe" in content
    assert "Folds" in content
    assert "tsmomentum_sma175_candidate_eval" in content


def test_read_only_no_mutation_of_run_cycle6():
    result = subprocess.run(
        ["git", "diff", "--name-only"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    changed = [x.strip() for x in result.stdout.splitlines() if x.strip()]
    assert "research/run_cycle6.py" not in changed


def test_data_config_unchanged():
    result = subprocess.run(
        ["git", "diff", "--name-only", "data/", "config/"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == ""


def test_returns_metrics_dict(payload):
    assert isinstance(payload, dict)
    assert "summary" in payload
    assert "walkforward_sma175" in payload
    summary = payload["summary"]
    assert "n_folds" in summary
    assert summary["n_folds"] == 48
    assert "mean_test_sharpe" in summary
