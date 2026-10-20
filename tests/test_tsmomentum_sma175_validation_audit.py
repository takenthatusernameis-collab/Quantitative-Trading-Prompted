from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_reports_exist():
    assert (REPO_ROOT / "research/reports/tsmomentum_sma175_validation_001.md").exists()
    assert (REPO_ROOT / "research/experiments/tsmomentum_sma175_validation_001.md").exists()


def test_no_changes_to_run_cycle6():
    result = subprocess.run(
        ["git", "diff", "--name-only"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    changed = [x.strip() for x in result.stdout.splitlines() if x.strip()]
    assert "research/run_cycle6.py" not in changed


def test_data_config_unchanged():
    result = subprocess.run(
        ["git", "diff", "--name-only", "data/", "config/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == ""


def test_checks_all_pass():
    report = (REPO_ROOT / "research/reports/tsmomentum_sma175_validation_001.md").read_text()
    assert "- [cache_loaded]: PASS" in report
    assert "- [wf_sma200_folds]: PASS" in report
    assert "- [wf_sma175_folds]: PASS" in report
    for line in report.splitlines():
        if line.strip().startswith("- [") and ": PASS" not in line and ": FAIL" in line:
            raise AssertionError(f"Found failing check: {line}")
