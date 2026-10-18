#!/usr/bin/env python3
"""Independent verification of Cycle 77 paper-trading state.

Computes:
  - Rolling 63-day Sharpe from the last 63 `cumulative_returns` entries in
    data/processed/paper_trading_state.yaml
  - Number of regime flips from `run_history` `regime_exposure` transitions
Compares against the stored drift flag and documented counts.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parent.parent
STATE_PATH = REPO / "data" / "processed" / "paper_trading_state.yaml"


def main() -> int:
    with open(STATE_PATH) as f:
        state = yaml.safe_load(f)

    cum_returns = state["cumulative_returns"]
    n_returns = len(cum_returns)
    last = cum_returns[-63:]
    arr = np.array(last, dtype=float)

    mean_r = float(np.mean(arr))
    std_r = float(np.std(arr, ddof=1))

    # Formula used by src/simulation/paper_trading.py:
    #   recent_ann_ret = np.mean(recent_returns) * 252
    #   recent_vol = np.std(recent_returns, ddof=1) * np.sqrt(252)
    #   rolling_sharpe = recent_ann_ret / recent_vol
    sharpe_code = (mean_r * 252.0) / (std_r * np.sqrt(252.0)) if std_r > 0 else 0.0

    # Formula quoted literally in NEXT_AGENT_TASK.md:
    #   (mean*252) / (std(ddof=1) * sqrt(256/252))
    sharpe_task = (mean_r * 252.0) / (std_r * np.sqrt(256.0 / 252.0)) if std_r > 0 else 0.0

    stored = state["drift_flags"]["low_rolling_sharpe"]["value"]
    stored_date = state["drift_flags"]["low_rolling_sharpe"]["date"]

    print("=== Rolling 63-day Sharpe verification ===")
    print(f"cumulative_returns total entries: {n_returns}")
    print(f"last-63 window used: {len(last)} entries")
    print(f"mean(returns): {mean_r}")
    print(f"std(returns, ddof=1): {std_r}")
    print(f"Sharpe (code formula  sqrt(252)): {sharpe_code}")
    print(f"Sharpe (task formula  sqrt(256/252)): {sharpe_task}")
    print(f"Stored drift_flags.low_rolling_sharpe.value: {stored}")
    print(f"Stored date: {stored_date}")
    print(f"Match (code formula, exact): {np.isclose(sharpe_code, stored)}")
    print(f"Match (task formula, exact): {np.isclose(sharpe_task, stored)}")

    # Regime-flip verification from run_history regime_exposure transitions.
    run_history = state["run_history"]
    regime_series = [r.get("regime_exposure") for r in run_history if "regime_exposure" in r]
    flips = 0
    for prev, cur in zip(regime_series, regime_series[1:]):
        if prev != cur:
            flips += 1
    print()
    print("=== Regime-flip verification ===")
    print(f"run_history entries: {len(run_history)}")
    print(f"regime_exposure entries scanned: {len(regime_series)}")
    print(f"Regime flips (transitions): {flips}")
    print(f"Documented count: 6")
    print(f"Match: {flips == 6}")

    print()
    print("=== Summary ===")
    print(f"last_run_date: {state['last_run_date']}")
    print(f"current_nav: ${state['current_nav']:.2f}")
    print(f"peak_nav: ${state['peak_nav']:.2f}")
    print(f"max_drawdown: {state['max_drawdown']:.6f}")

    ok = bool(
        np.isclose(sharpe_code, stored) and flips == 6 and len(run_history) == 449
    )
    print()
    print(f"OVERALL: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
