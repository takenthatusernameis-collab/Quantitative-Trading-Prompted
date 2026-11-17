import subprocess
import sys
from pathlib import Path

import yaml

STATE_PATH = Path("data/processed/paper_trading_state.yaml")
REPORT_PATH = Path("research/reports/paper_trading_record_status_001.md")
EXPERIMENT_PATH = Path("research/experiments/paper_trading_record_status_001.md")


def test_tool():
    state = yaml.safe_load(STATE_PATH.read_text())
    sessions = len(state["cumulative_returns"])
    last_run_date = state["last_run_date"]
    assert REPORT_PATH.read_text() == (
        f"# Paper trading record status\n\nsessions: {sessions}\nlast_run_date: {last_run_date}\n"
    )
    assert EXPERIMENT_PATH.read_text() == (
        f"# Paper trading record status experiment\n\nsessions: {sessions}\n"
    )

    r = subprocess.run(
        [sys.executable, "research/paper_trading_record_status_audit.py"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    assert "OVERALL: PASS" in r.stdout
    assert REPORT_PATH.exists()
    assert EXPERIMENT_PATH.exists()
