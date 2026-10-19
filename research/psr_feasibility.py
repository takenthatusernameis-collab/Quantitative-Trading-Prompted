#!/usr/bin/env python3
"""Read-only PSR feasibility analysis under canonical convention."""
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluation.sharpe import sharpe_ratio
from src.evaluation.statistics import compute_psr

STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "paper_trading_state.yaml"
ANNUAL = 252
TARGET_PSR = 0.95
TARGET_SHARPE_OBS_CYCLE862 = 2.552996  # from Cycle 862


def load_committed_rets_series() -> pd.Series:
    with open(STATE_PATH) as f:
        state = yaml.safe_load(f)
    return pd.Series(state.get("cumulative_returns", []), dtype=float)


def main():
    rets = load_committed_rets_series()
    rets_np = rets.values
    n = len(rets)
    mean_full = float(rets.mean()) if n > 0 else 0.0
    std_full = float(rets.std(ddof=1)) if n > 1 else 0.0
    sharpe_full = sharpe_ratio(rets_np)

    # Required mean for target observed Sharpe given current full-period std
    mean_req_for_target = TARGET_SHARPE_OBS_CYCLE862 * std_full / np.sqrt(ANNUAL)

    print("=== PSR Feasibility (read-only, canonical convention) ===")
    print(f"Committed: {n} sessions (ends 2026-10-16)")
    print(f"Full-period: mean={mean_full:.8f} (ann={mean_full*252:.6f}), std={std_full:.6f}, sharpe={sharpe_full:.6f}")
    if n >= 63:
        tr = rets_np[-63:]
        print(f"Trailing 63: mean={tr.mean():.8f}, std={tr.std(ddof=1):.6f}, sharpe={sharpe_ratio(tr):.6f}")
    print()
    print(f"Target observed Sharpe for PSR>=0.95 at current SE (0.690150): {TARGET_SHARPE_OBS_CYCLE862:.6f}")
    print(f"Required mean daily (at current full-period std={std_full:.6f}): {mean_req_for_target:.8f} (ann={mean_req_for_target*252:.6f})")
    print(f"Gap vs record mean: {mean_req_for_target - mean_full:+.8f} daily ({(mean_req_for_target-mean_full)*252:+.6f} ann)")
    print()
    try:
        psr_res = compute_psr(rets, sr_target=1.4178, seed=20240101)
        print(f"PSR (target 1.4178): psr_normal={psr_res['psr_normal']:.6f}, psr_emp={psr_res['psr_empirical']:.6f}")
        print(f"  observed_sharpe={psr_res['sharpe_observed']:.6f}, se={psr_res['sharpe_se']:.6f}")
    except Exception as e:
        print(f"PSR calc error: {e}")
    print("=== End ===")


if __name__ == "__main__":
    main()
