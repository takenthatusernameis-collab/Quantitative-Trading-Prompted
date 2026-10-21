"""Smoke tests for Cycle 931 mechanism comparison."""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "research" / "mechanism_comparison_001.py"


def test_script_runs_and_passes_structural():
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert "STRUCTURAL: PASS" in result.stdout
