#!/usr/bin/env python3
"""Historical replay for paper-trading validation to build 63-day track record.

This script runs the paper-trading engine deterministically over the cached
historical data from a start date to the latest available date, building
a proper track record with unique trading days.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.simulation.paper_trading import (
    PaperTradingConfig,
    PaperTradingState,
    generate_paper_report,
    run_daily_paper_update,
)
from src.data.yfinance_fetcher import fetch_universe


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    config_path = repo_root / "config" / "paper_trading_config.yaml"
    state_path = repo_root / "data" / "processed" / "paper_trading_state.yaml"

    print("=== Paper-Trading Historical Replay ===")
    print(f"Config: {config_path}")
    print(f"State: {state_path}")
    print()

    # Load config
    config = PaperTradingConfig.from_paper_config_yaml(config_path)

    # Load ALL market data once (from history_start to latest available).
    # NOTE: yfinance treats ``end`` as EXCLUSIVE, so to capture trading day
    # 2026-10-13 we must request end_date = 2026-10-14. Requesting
    # end_date = 2026-10-13 silently truncates the cache to 2026-10-12.
    end_date = "2026-10-14"
    print(f"Fetching market data from {config.history_start} to {end_date}...")
    all_market_data = fetch_universe(config.universe, config.history_start, end_date, force=True)
    print(f"Loaded market data: {len(all_market_data)} rows, {all_market_data.index.min().date()} to {all_market_data.index.max().date()}")

    # Get trading days from 2025-01-01 to 2026-10-13 (captures 2025 regime flips)
    start_replay_date = "2025-01-01"
    replay_dates = all_market_data.index[(all_market_data.index >= start_replay_date) & (all_market_data.index <= "2026-10-13")]
    replay_dates = replay_dates[replay_dates.weekday < 5]  # Ensure weekdays only
    print(f"Replay period: {start_replay_date} to {end_date} ({len(replay_dates)} trading days)")

    # Create fresh state (reset for clean replay)
    state = PaperTradingState()
    print(f"Starting with fresh state (last_run_date: {state.last_run_date})")

    # Run simulation day by day
    for i, target_date in enumerate(replay_dates):
        target_date_str = target_date.strftime("%Y-%m-%d")

        # Slice market data up to this date
        market_data_slice = all_market_data.loc[:target_date]

        # Run daily update with sliced data
        state, artifacts = run_daily_paper_update(config, state, market_data=market_data_slice)

        if artifacts:
            print(f"  Day {i+1}/{len(replay_dates)}: {target_date_str} | NAV=${artifacts['nav']:,.2f} | Ret={artifacts['daily_return']:.4%} | DD={artifacts['max_drawdown']:.2%} | Positions={len([w for w in artifacts['positions'].values() if abs(w) > 1e-9])}")
        else:
            print(f"  Day {i+1}/{len(replay_dates)}: {target_date_str} | SKIPPED (idempotency or no data)")

        # Save state after each day (for crash recovery)
        state.to_yaml(state_path)

    # Final report
    generate_paper_report(state, config)
    print(f"\nReplay complete! Track record length: {len(state.cumulative_dates)} unique days")
    print(f"State saved to {state_path}")
    print(f"Report saved to {config.report_path}")

    # Print summary
    if len(state.cumulative_returns) > 0:
        returns = np.array(state.cumulative_returns)
        total_ret = state.current_nav / 100000.0 - 1.0
        days = len(state.cumulative_dates)
        ann_ret = (1.0 + total_ret) ** (252.0 / max(days, 1)) - 1.0 if days > 0 else 0.0
        if days > 1:
            vol = np.std(returns) * np.sqrt(252.0)
            sharpe = ann_ret / vol if vol > 0 else 0.0
        else:
            vol = 0.0
            sharpe = 0.0
        print(f"\n=== SUMMARY ===")
        print(f"Days tracked: {days}")
        print(f"Current NAV: ${state.current_nav:,.2f}")
        print(f"Total Return: {total_ret:.2%}")
        print(f"Annualized Return: {ann_ret:.2%}")
        print(f"Volatility (ann.): {vol:.2%}")
        print(f"Sharpe Ratio: {sharpe:.4f}")
        print(f"Max Drawdown: {state.max_drawdown:.2%}")
        print(f"Go/No-Go Gate (63 days): {'PASSED' if days >= 63 else 'NOT YET REACHED'}")


if __name__ == "__main__":
    main()