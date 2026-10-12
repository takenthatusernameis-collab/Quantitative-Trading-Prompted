"""Cycle 9: Go/No-Go Evaluation & Drift Enhancement.

Evaluates the paper-trading track record against go/no-go criteria,
enhances drift monitoring, and produces a formal evaluation report.

Artifacts produced:
  - src/simulation/evaluation.py (go/no-go evaluation module)
  - research/reports/go_no_go_evaluation_001.md (evaluation report)
  - Enhanced drift monitoring in src/simulation/paper_trading.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.simulation.evaluation import (
    GoNoGoConfig,
    evaluate_go_no_go,
    save_evaluation_report,
)
from src.simulation.paper_trading import (
    PaperTradingConfig,
    PaperTradingState,
    run_daily_paper_update,
)


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    paper_config_path = repo_root / "config" / "paper_trading_config.yaml"
    state_path = repo_root / "data" / "processed" / "paper_trading_state.yaml"
    report_path = repo_root / "research" / "reports" / "go_no_go_evaluation_001.md"

    print("=== Cycle 9: Go/No-Go Evaluation & Drift Enhancement ===")
    print(f"Paper Config: {paper_config_path}")
    print(f"State: {state_path}")
    print(f"Report Output: {report_path}")
    print()

    # Load config and state
    config = PaperTradingConfig.from_paper_config_yaml(paper_config_path)
    state = PaperTradingState.from_yaml(state_path)

    print(f"Candidate: {config.candidate_id}")
    print(f"Paper track record: {len(state.cumulative_returns)} days")
    print(f"Last run: {state.last_run_date}")
    print(f"Current NAV: ${state.current_nav:,.2f}")
    print(f"Max Drawdown: {state.max_drawdown:.2%}")
    print()

    # Run go/no-go evaluation
    print("Running go/no-go evaluation...")
    go_no_go_config = GoNoGoConfig(
        min_days=config.go_no_go_min_days,
        target_sharpe=config.go_no_go_target_sharpe,
        max_dd_threshold=config.go_no_go_max_dd_threshold,
    )

    result = evaluate_go_no_go(state, config, go_no_go_config=go_no_go_config)

    # Print summary
    print(f"\nDecision: {result.decision}")
    print(f"Paper Sharpe: {result.paper_sharpe:.4f}")
    print(f"Paper Max DD: {result.paper_max_dd:.2%}")
    print(f"PSR (normal): {result.psr_normal:.4f}")
    print(f"PSR (empirical): {result.psr_empirical:.4f}")
    print(f"Regime Stable: {result.regime_stable} ({result.regime_persistence_days} days)")
    print(f"vol_scale range: [{result.vol_scale_min:.3f}, {result.vol_scale_max:.3f}]")
    print(f"dd_scale range: [{result.dd_scale_min:.3f}, {result.dd_scale_max:.3f}]")
    print(f"Turnover median/p95: {result.turnover_median:.2%} / {result.turnover_p95:.2%}")
    print(f"Drift flags: {result.drift_flags_count}")
    print()

    # Generate and save evaluation report
    save_evaluation_report(result, go_no_go_config, report_path)
    print(f"Evaluation report saved to {report_path}")

    # Also run the paper trading update to refresh drift monitoring
    print("\nRunning daily paper-trading update (for enhanced drift monitoring)...")
    state, artifacts = run_daily_paper_update(config, state)

    if artifacts:
        print(f"Updated: {artifacts['latest_date']}")
        print(f"Rolling 63d Sharpe: {state.rolling_sharpe_63d:.4f}")
        print(f"Rolling 63d Max DD: {state.rolling_max_dd_63d:.2%}")
        print(f"Regime Persistence: {state.regime_persistence_days} days")
        print(f"vol_scale range: [{state.vol_scale_min:.3f}, {state.vol_scale_max:.3f}]")
        print(f"dd_scale range: [{state.dd_scale_min:.3f}, {state.dd_scale_max:.3f}]")
        print(f"Turnover median/p95: {state.turnover_median:.2%} / {state.turnover_p95:.2%}")
        if state.drift_flags:
            print(f"Drift flags: {', '.join(state.drift_flags.keys())}")
        else:
            print("Drift flags: None")
    else:
        print("No new data available for update.")

    # Save updated state
    state.to_yaml(state_path)
    print(f"\nUpdated state saved to {state_path}")

    # Generate updated rolling report
    from src.simulation.paper_trading import generate_paper_report
    generate_paper_report(state, config)
    print(f"Rolling report updated at {config.report_path}")

    print("\n=== Cycle 9 Complete ===")


if __name__ == "__main__":
    main()