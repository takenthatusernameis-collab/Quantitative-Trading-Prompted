"""Tests for tsmomentum_phase_stability_fix_audit."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

TOOL = "research/tsmomentum_phase_stability_fix_audit.py"
REPORT = REPO / "research" / "reports" / "tsmomentum_phase_stability_fix_001.md"
EXPERIMENT = REPO / "research" / "experiments" / "tsmomentum_phase_stability_fix_001.md"


def _run_tool(*extra):
    return subprocess.run([sys.executable, TOOL, *extra], cwd=REPO, check=False, capture_output=True, text=True)


def test_tool_runs_and_passes():
    result = _run_tool()
    assert result.returncode == 0, result.stderr
    assert "OVERALL: PASS" in result.stdout


def test_artifacts_exist():
    assert REPORT.exists()
    assert EXPERIMENT.exists()
