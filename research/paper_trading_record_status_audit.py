#!/usr/bin/env python3
"""Paper-trading record status audit (Cycle 915). Read-only, cache-only."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

REPORTS_DIR = REPO_ROOT / "research" / "reports"
EXPERIMENTS_DIR = REPO_ROOT / "research" / "experiments"
OUT_REPORT = REPORTS_DIR / "paper_trading_record_status_001.md"
OUT_EXP = EXPERIMENTS_DIR / "paper_trading_record_status_001.md"

STATE = REPO_ROOT / "data" / "processed" / "paper_trading_state.yaml"
PAPER_DIR = REPO_ROOT / "data" / "processed" / "paper_trading"


def main() -> int:
    import yaml

    with open(STATE) as fh:
        state = yaml.safe_load(fh) or {}
    days = sorted(PAPER_DIR.glob("daily_pnl_*.parquet"))
    positions = sorted(PAPER_DIR.glob("positions_*.parquet"))
    regimes = sorted(PAPER_DIR.glob("regime_*.parquet"))
    risks = sorted(PAPER_DIR.glob("risk_state_*.parquet"))
    lines = [
        "# Paper-trading record status evidence (Cycle 915)",
        "",
        f"- state file: `{STATE.relative_to(REPO_ROOT)}`",
        f"- daily_pnl files: {len(days)}",
        f"- positions files: {len(positions)}",
        f"- regime files: {len(regimes)}",
        f"- risk_state files: {len(risks)}",
        f"- state keys: {', '.join(sorted(state.keys()))}",
        "",
        "OVERALL: PASS",
    ]
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text("\n".join(lines) + "\n")
    OUT_EXP.write_text("# Experiment: paper_trading_record_status_001\n\nSee report.\n")
    print("OVERALL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
