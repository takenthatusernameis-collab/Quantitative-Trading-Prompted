"""Refined cohort attribution for the trailing 63 sessions.

The coarse buckets show the decline is NOT a regime-filter story (all 63 sessions
are risk-on / full exposure, so the SPY 200d SMA filter has not been the cause)
and is NOT a turnover story in the aggregate. It is concentrated:

  * temporally: the second half of the window (Sharpe -2.40 vs +2.00)
  * by vol_scale: the highest-volatility quartile (Sharpe -3.77 vs +4.43)

This script isolates the single cohort that overlaps both, tests whether it
carries a disproportionate share of the window return, and falsifies the
"broad, unattributable decline" hypothesis.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluation.sharpe import sharpe_ratio  # noqa: E402
from src.simulation.paper_trading import PaperTradingState  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = REPO_ROOT / "data" / "processed" / "paper_trading_state.yaml"
WINDOW = 63


def _sharpe(returns: pd.Series) -> float:
    if len(returns) < 2 or returns.std(ddof=1) == 0:
        return float("nan")
    return float(sharpe_ratio(list(returns)))


def main() -> int:
    state = PaperTradingState.from_yaml(STATE_PATH)
    rh = pd.DataFrame(state.run_history)
    rh["date"] = pd.to_datetime(rh["date"])
    rh = rh.sort_values("date").reset_index(drop=True)

    window = rh.tail(WINDOW).copy()
    ret = window["daily_return"].astype(float)
    mid = len(window) // 2
    vol_q = pd.qcut(window["vol_scale"], 4, labels=["q1", "q2", "q3", "q4"], duplicates="drop")

    cohorts = {
        "high_vol_late": (vol_q == "q4") & (window.index >= mid),
        "high_vol_early": (vol_q == "q4") & (window.index < mid),
        "low_vol_late": (vol_q == "q1") & (window.index >= mid),
        "low_vol_early": (vol_q == "q1") & (window.index < mid),
        "high_vol_all": vol_q == "q4",
        "low_vol_all": vol_q == "q1",
        "late_all": window.index >= mid,
        "high_vol_and_turnover_spike": (vol_q == "q4") & (window["turnover"] > window["turnover"].median()),
    }

    win_ret = float(ret.sum())
    print("=== Cohort attribution (last 63 sessions, 2026-07-22 .. 2026-10-19) ===")
    print(f"window cumulative return: {win_ret:.6f}  window Sharpe: {_sharpe(ret):.4f}")
    print(f"regime_exposure unique values: {sorted(window['regime_exposure'].unique())}")
    print(f"n_positions unique values: {sorted(window['n_positions'].unique())}")
    print(f"vol_scale quartile boundaries: {sorted(window['vol_scale'].quantile([0.25,0.5,0.75]).round(4).tolist())}")
    print()
    print(f"{'cohort':<26}{'n':>5}{'share_n':>9}{'share_ret':>11}{'sharpe':>9}{'mean_ret':>11}")
    rows = []
    for name, mask in cohorts.items():
        sub = ret[mask]
        share_n = float(mask.mean())
        share_ret = float(sub.sum() / win_ret) if win_ret != 0 else float("nan")
        rows.append((name, int(mask.sum()), share_n, share_ret, _sharpe(sub), float(sub.mean()) if len(sub) else float("nan")))
        print(
            f"{name:<26}{int(mask.sum()):>5}{share_n:>9.3f}"
            f"{share_ret:>11.3f}{_sharpe(sub):>9.3f}{float(sub.mean()) if len(sub) else float('nan'):>11.6f}"
        )

    # Dominant cohort: the one carrying the largest |share of window return|
    best = max(rows, key=lambda r: abs(r[3]))
    print()
    print(f"dominant cohort: {best[0]} -> share of window return {best[3]:.3f}, sharpe {best[4]:.3f}")
    concentrated = abs(best[3]) > 0.5
    print(f"single cohort carries >50% of window return: {concentrated}")
    print(f"falsification condition (broad, unattributable decline): {not concentrated}")
    return 0


if __name__ == "__main__":
    sys.exit(main())