"""Cycle 8: Paper-Trading Prospective Validation.

Builds and runs the paper-trading framework for the validated Credible
Candidate. Runs daily updates, tracks positions, monitors drift, and
produces artifacts for prospective validation.

Artifacts produced:
  - src/simulation/paper_trading.py (paper-trading engine)
  - data/processed/paper_trading_state.yaml (persistent state)
  - data/processed/paper_trading/*.parquet (daily artifacts)
  - research/reports/paper_trading_rolling.md (rolling report)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.simulation.paper_trading import (
    PaperTradingConfig,
    PaperTradingState,
    generate_paper_report,
    run_daily_paper_update,
)


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    config_path = repo_root / "config" / "paper_trading_config.yaml"
    state_path = repo_root / "data" / "processed" / "paper_trading_state.yaml"

    print("=== Cycle 8: Paper-Trading Prospective Validation ===")
    print(f"Config: {config_path}")
    print(f"State: {state_path}")
    print()

    # Load config and state
    config = PaperTradingConfig.from_paper_config_yaml(config_path)
    state = PaperTradingState.from_yaml(state_path)

    # Run daily update
    print("Running daily paper-trading update...")
    state, artifacts = run_daily_paper_update(config, state)

    if not artifacts:
        print("No new artifacts generated (no data available for latest date).")
    else:
        print(f"Latest date: {artifacts['latest_date']}")
        print(f"Nav: ${artifacts['nav']:,.2f}")
        print(f"Daily return: {artifacts['daily_return']:.2%}")
        print(f"Max drawdown: {artifacts['max_drawdown']:.2%}")
        print(f"Positions: {len([w for w in artifacts['positions'].values() if abs(w) > 1e-9])} active")
        if artifacts['drift_flags']:
            print(f"Drift flags: {', '.join(artifacts['drift_flags'].keys())}")
        else:
            print("Drift flags: None")

    # Save state
    state.to_yaml(state_path)
    print(f"\nState saved to {state_path}")

    # Generate report
    generate_paper_report(state, config)
    print(f"Report saved to {config.report_path}")

    print("\n=== Cycle 8 Complete ===")


if __name__ == "__main__":
    main()
