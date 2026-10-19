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

    stored_flag = (state.get("drift_flags") or {}).get("low_rolling_sharpe")
    if stored_flag is not None:
        stored = stored_flag["value"]
        stored_date = stored_flag["date"]
        flag_present = True
    else:
        stored = None
        stored_date = None
        flag_present = False

    print("=== Rolling 63-day Sharpe verification ===")
    print(f"cumulative_returns total entries: {n_returns}")
    print(f"last-63 window used: {len(last)} entries")
    print(f"mean(returns): {mean_r}")
    print(f"std(returns, ddof=1): {std_r}")
    print(f"Sharpe (code formula  sqrt(252)): {sharpe_code}")
    print(f"Sharpe (task formula  sqrt(256/252)): {sharpe_task}")
    print(f"Stored drift_flags.low_rolling_sharpe.value: {stored}")
    print(f"Stored date: {stored_date}")
    if flag_present:
        print(f"Match (code formula, exact): {np.isclose(sharpe_code, stored)}")
        print(f"Match (task formula, exact): {np.isclose(sharpe_task, stored)}")
    else:
        # The flag is absent only when the rolling Sharpe is at or above the
        # 0.5 alert threshold (or before 20 returns exist).
        print(
            "Flag absent: consistent with the 0.5 threshold: "
            f"{sharpe_code >= 0.5 or n_returns < 20}"
        )

    # Drift-flag persistence: consecutive trading sessions below the 0.5
    # threshold, recomputed independently of src/evaluation/drift.py.
    cum_dates_all = state["cumulative_dates"]
    series = []
    for i in range(len(cum_returns)):
        if i + 1 < 20:
            series.append(None)
        else:
            w = np.array(cum_returns[max(0, i - 62) : i + 1], dtype=float)
            vol = np.std(w, ddof=1) * np.sqrt(252)
            series.append((float(np.mean(w)) * 252) / vol if vol > 0 else 0.0)
    streak = 0
    for value in reversed(series):
        if value is None or value >= 0.5:
            break
        streak += 1
    print()
    print("=== Drift-flag persistence verification ===")
    print(f"Consecutive trading days below 0.5: {streak}")
    if streak:
        print(
            "Streak window: "
            f"{cum_dates_all[-streak]} -> {cum_dates_all[-1]}"
        )
    print(f"Recomputed final rolling Sharpe equals stored flag: "
          f"{np.isclose(sharpe_code, stored) if flag_present else 'n/a (flag absent)'}")

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

    # Invariants
    cum_pnl = state["cumulative_pnl"]
    cum_dates = state["cumulative_dates"]
    ok_inv = (
        len(cum_returns) == len(cum_pnl) == len(run_history) == len(cum_dates)
        and cum_dates == [r["date"] for r in run_history]
        and len(set(cum_dates)) == len(cum_dates)
        and all(cum_dates[i] < cum_dates[i+1] for i in range(len(cum_dates)-1))
        and abs(100000 + sum(cum_pnl) - state["current_nav"]) < 1e-6
        and state["previous_regime_exposure"] == run_history[-1]["regime_exposure"]
    )
    ok_sharpe = (
        bool(np.isclose(sharpe_code, stored))
        if flag_present
        else bool(sharpe_code >= 0.5 or n_returns < 20)
    )
    ok = bool(ok_sharpe and ok_inv)
    print()
    print(f"OVERALL: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
