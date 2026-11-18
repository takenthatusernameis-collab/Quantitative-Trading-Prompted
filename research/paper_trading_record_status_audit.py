#!/usr/bin/env python3
"""Read-only audit of paper-trading record status."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = REPO_ROOT / "data" / "processed" / "paper_trading_state.yaml"
REPORT_PATH = REPO_ROOT / "research" / "reports" / "paper_trading_record_status_001.md"
EXPERIMENT_PATH = REPO_ROOT / "research" / "experiments" / "paper_trading_record_status_001.md"


def main():
    state = yaml.safe_load(STATE_PATH.read_text())
    n = len(state.get("cumulative_returns", []))
    assert n > 0
    assert state.get("last_run_date")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXPERIMENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(f"# Paper trading record status\n\nsessions: {n}\nlast_run_date: {state['last_run_date']}\n")
    EXPERIMENT_PATH.write_text(f"# Paper trading record status experiment\n\nsessions: {n}\n")
    print("OVERALL: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
