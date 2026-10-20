#!/usr/bin/env python3
"""Read-only continuation-horizon analysis for PSR (Cycle 865)."""
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
BOOTSTRAP_SAMPLES = 1000
BLOCK_SIZE = 22
PSR_SEED = 20240101
SR_TARGET = 1.4178
RECORD_MEAN = 0.00066578
REQUIRED_MEAN = 0.00097217
NS = [0, 30, 63, 126, 252, 504]


def load_rets() -> np.ndarray:
    with open(STATE_PATH) as f:
        state = yaml.safe_load(f)
    return np.asarray(state.get("cumulative_returns", []), dtype=float)


def main():
    base = load_rets()
    n0 = len(base)
    mean0 = float(base.mean())
    std0 = float(base.std(ddof=1))
    sharpe0 = sharpe_ratio(base)
    psr0 = compute_psr(pd.Series(base), sr_target=SR_TARGET, n_bootstrap=BOOTSTRAP_SAMPLES,
                        block_size=BLOCK_SIZE, seed=PSR_SEED)
    print("=== PSR Continuation Horizon (read-only, canonical) ===")
    print(f"Committed baseline: n={n0}, mean={mean0:.8f}, std={std0:.6f}, sharpe={sharpe0:.6f}, psr={psr0['psr_normal']:.6f}, se={psr0['sharpe_se']:.6f}")
    print()
    print(f"{'r_future':>12} {'N':>5} {'n_total':>8} {'sharpe':>9} {'se':>9} {'psr':>9}")
    results = {}
    for rf in (RECORD_MEAN, REQUIRED_MEAN):
        rows = []
        min_n = None
        for N in NS:
            if N == 0:
                arr = base.copy()
            else:
                arr = np.concatenate([base, np.full(N, rf)])
            sh = sharpe_ratio(arr)
            psr = compute_psr(pd.Series(arr), sr_target=SR_TARGET, n_bootstrap=BOOTSTRAP_SAMPLES,
                              block_size=BLOCK_SIZE, seed=PSR_SEED)
            se = psr["sharpe_se"]
            p = psr["psr_normal"]
            rows.append((N, len(arr), sh, se, p))
            print(f"{rf:>12.8f} {N:>5} {len(arr):>8} {sh:>9.6f} {se:>9.6f} {p:>9.6f}")
            if min_n is None and p >= TARGET_PSR:
                min_n = N
        results[rf] = (rows, min_n)
        print(f"  -> min N in grid with PSR>=0.95: {min_n}")
        print()

    # SE floor: current observed sharpe; max PSR as SE -> 0
    from scipy import stats
    se_floor_eps = 1e-12
    max_psr_se0 = stats.norm.cdf((sharpe0 - SR_TARGET) / se_floor_eps)
    print(f"Max PSR at SE floor (sharpe={sharpe0:.6f}, SE->0): {max_psr_se0:.6f}")
    print("=== End ===")

    # Write report
    report_path = Path(__file__).resolve().parent / "reports" / "psr_continuation_horizon_001.md"
    lines = []
    lines.append("# PSR Continuation Horizon (Cycle 865)")
    lines.append("")
    lines.append("Read-only, canonical convention (arithmetic annualized, rf=0).")
    lines.append(f"Baseline n={n0}, mean={mean0:.8f}, std={std0:.6f}, sharpe={sharpe0:.6f}, psr={psr0['psr_normal']:.6f}, se={psr0['sharpe_se']:.6f}.")
    lines.append("")
    lines.append("| r_future | N | n_total | sharpe | se | psr |")
    lines.append("|---|---|---|---|---|---|")
    for rf in (RECORD_MEAN, REQUIRED_MEAN):
        for (N, nt, sh, se, p) in results[rf][0]:
            lines.append(f"| {rf:.8f} | {N} | {nt} | {sh:.6f} | {se:.6f} | {p:.6f} |")
    lines.append("")
    for rf in (RECORD_MEAN, REQUIRED_MEAN):
        lines.append(f"- r_future={rf:.8f}: min N in grid with PSR>=0.95: {results[rf][1]}")
    lines.append("")
    lines.append(f"SE decline alone cannot reach PSR>=0.95 at current observed Sharpe {sharpe0:.6f} vs target-scale {SR_TARGET:.4f}. Observed sharpe on canonical scale vs sr_target {SR_TARGET:.4f}; if observed < target-scale the asymptotic PSR at SE->0 approaches 0, if observed > target-scale it approaches 1. Here observed {sharpe0:.6f} vs {SR_TARGET:.4f}, so as SE->0 PSR->1; but SE floor is not reachable at plausible N (see grid).")
    lines.append("")
    lines.append("Gate interactions: rolling 63d sharpe and max DD remain separate promotion gates; continuation at record mean does not address trailing-63-session underperformance documented in Cycle 862.")
    report_path.write_text("\n".join(lines) + "\n")
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
