#!/usr/bin/env python3
"""Cycle 932: riskparity_001 vs 1/N on non-overlapping annual subset.

Recompute the riskparity_001 vs 1/N excess on a non-overlapping annual subset
of the same point-in-time-complete window and report whether the significance
survives. No parameter search, no new candidate.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.data_cost_inventory_002 import fingerprint, moving_block_bootstrap_mean, tracked_artifact_hashes
from research.mechanism_comparison_001 import run_comparison

REPORTS_DIR = REPO_ROOT / "research" / "reports"
OUT_REPORT = REPORTS_DIR / "annual_subset_riskparity_vs_oneoverN_932.md"

BOOTSTRAP_SEED = 20240101
BOOTSTRAP_DRAWS = (2000, 1000)


def main() -> int:
    data_before = fingerprint(REPO_ROOT / "data")
    config_before = fingerprint(REPO_ROOT / "config")
    artifacts_before = tracked_artifact_hashes()
    self_outputs = {str(OUT_REPORT.relative_to(REPO_ROOT))}

    payload = run_comparison()
    # Get fold rows for riskparity and 1/N
    rp_rows = payload["fold_rows"]["riskparity_001"]
    bench_rows = payload["fold_rows"]["one_over_n"]

    # Build mapping
    bench_by_fold = {r["fold"]: r for r in bench_rows}

    # Select non-overlapping annual subset
    # Folds are 12-month test windows on 6-month steps starting from fold 8
    # Non-overlapping annual subset means pick folds that don't overlap
    # e.g. every other fold or pick starting points 12 months apart
    # Looking at the pattern: fold 8 starts 2006-02-15, fold 9 starts 2006-08-10 (6 months later),
    # fold 10 starts 2007-02-02 etc. So to get non-overlapping annual, pick folds with start dates
    # 12 months apart - e.g. fold 8, fold 10, fold 12,... (every other fold gives 12 month spacing)
    selected_folds = []
    for r in rp_rows:
        f = r["fold"]
        if f % 2 == 0:  # even folds give 12-month spacing from fold 8
            selected_folds.append(r)

    selected_bench = [bench_by_fold[r["fold"]] for r in selected_folds]

    rp_sharpes = [float(r["test_sharpe"]) for r in selected_folds]
    bench_sharpes = [float(r["test_sharpe"]) for r in selected_bench]
    diffs = [a - b for a, b in zip(rp_sharpes, bench_sharpes)]
    excess = float(np.mean(diffs))

    n_folds = len(selected_folds)
    block = max(2, n_folds // 8) if n_folds > 0 else 2
    ci_results = {}
    for draws in BOOTSTRAP_DRAWS:
        boot = moving_block_bootstrap_mean(diffs, block, draws, BOOTSTRAP_SEED)
        ci_results[draws] = boot

    primary = ci_results[BOOTSTRAP_DRAWS[0]]
    excludes_zero = bool(primary["ci_low"] > 0.0 or primary["ci_high"] < 0.0)
    positive = bool(primary["ci_low"] > 0.0)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    lines = []
    A = lines.append
    A("# Cycle 932 — Independent-sample significance of riskparity_001 excess over 1/N")
    A("")
    A("## Context")
    A("")
    A("Cycle 931 placed 1/N, riskparity_001 and the incumbent on the same 41 point-in-time-complete folds.")
    A(f"riskparity_001's excess over 1/N is +{payload['excess']['riskparity_001']['excess']:.6f} with a moving-block")
    A(f"bootstrap 95% CI [{payload['excess']['riskparity_001']['ci']['2000']['ci_low']:.6f}, {payload['excess']['riskparity_001']['ci']['2000']['ci_high']:.6f}]")
    A("that excludes zero, while the incumbent's excess has a CI that includes zero. The 41 folds overlap")
    A("(12-month test on a 6-month step), so the CI is on a serially dependent fold set, not independent samples.")
    A("")
    A("## Objective")
    A("")
    A("Recompute the riskparity_001 vs 1/N excess on a non-overlapping annual subset of the same")
    A("point-in-time-complete window and report whether the significance survives; no parameter search,")
    A("no new candidate.")
    A("")
    A("## Method")
    A("")
    A("- **Window**: same point-in-time-complete window as Cycle 931 (2006-02-15 .. 2026-05-28)")
    A("- **Folds**: selected non-overlapping annual subset from the 41 complete folds (even folds 8,10,12,...,48)")
    A("- **Design**: same walk-forward design, same cost model (3.0 bp per unit), same 1/N benchmark")
    A("- **Bootstrap**: moving block bootstrap on paired fold differences, block = max(2, n_folds//8), seed = 20240101")
    A("")
    A("## Results")
    A("")
    A(f"- **Number of folds in annual subset**: {n_folds}")
    A(f"- **riskparity_001 excess over 1/N**: {excess:.6f}")
    A(f"- **95% CI (2000 draws)**: [{primary['ci_low']:.6f}, {primary['ci_high']:.6f}]")
    A(f"- **95% CI (1000 draws)**: [{ci_results[1000]['ci_low']:.6f}, {ci_results[1000]['ci_high']:.6f}]")
    A(f"- **Excludes zero**: {excludes_zero}")
    A(f"- **Block size**: {block}")
    A("")
    A("### Selected folds")
    A("")
    A("| Fold | Test window | riskparity_001 Sharpe | 1/N Sharpe | Excess |")
    A("|---|---|---|---|---|")
    for r_rp, r_b in zip(selected_folds, selected_bench):
        diff_fold = float(r_rp["test_sharpe"]) - float(r_b["test_sharpe"])
        A(f"| {r_rp['fold']} | {r_rp['test_start']} .. {r_rp['test_end']} | {r_rp['test_sharpe']:.6f} | {r_b['test_sharpe']:.6f} | {diff_fold:.6f} |")
    A("")
    A("## Conclusion")
    A("")
    if excludes_zero and positive:
        A(f"**Significance survives.** On the non-overlapping annual subset ({n_folds} folds),")
        A(f"riskparity_001's excess over 1/N remains positive with 95% CI [{primary['ci_low']:.6f}, {primary['ci_high']:.6f}]")
        A("excluding zero (same seed 20240101).")
    elif excludes_zero:
        A(f"**Significance survives in the sense that CI excludes zero, but direction is negative.**")
        A(f"Excess is {excess:.6f} with 95% CI [{primary['ci_low']:.6f}, {primary['ci_high']:.6f}].")
    else:
        A(f"**Significance does not survive.** On the non-overlapping annual subset ({n_folds} folds),")
        A(f"riskparity_001's excess over 1/N is {excess:.6f} with 95% CI [{primary['ci_low']:.6f}, {primary['ci_high']:.6f}]")
        A("including zero.")
    A("")
    A("## Validation")
    A("")
    A("```bash")
    A("python research/mechanism_comparison_001.py")
    A("python research/annual_subset_riskparity_vs_oneoverN_932.py")
    A("git status --porcelain data/ config/")
    A("```")
    A("")
    A("## Notes")
    A("")
    A("- `data/` and `config/` byte-identical (read-only).")
    A("- No parameter search, no new candidate.")
    A("- Bootstrap uses same seed 20240101 as Cycle 929/930.")

    report_text = "\n".join(lines)
    OUT_REPORT.write_text(report_text, encoding="utf-8")

    # Verify read-only guarantees
    data_after = fingerprint(REPO_ROOT / "data")
    config_after = fingerprint(REPO_ROOT / "config")
    artifacts_after = tracked_artifact_hashes()
    if data_before != data_after:
        raise RuntimeError("data/ changed during the run")
    if config_before != config_after:
        raise RuntimeError("config/ changed during the run")
    changed = {k for k in set(artifacts_before) | set(artifacts_after)
               if artifacts_before.get(k) != artifacts_after.get(k)}
    changed -= self_outputs
    if changed:
        raise RuntimeError(f"committed artefacts changed: {sorted(changed)}")

    print(f"REPORT|{OUT_REPORT}")
    print(f"N_FOLDS|{n_folds}")
    print(f"EXCESS|{excess:.6f}")
    print(f"CI2000|{primary['ci_low']:.6f}|{primary['ci_high']:.6f}")
    print(f"EXCLUDES_ZERO|{excludes_zero}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
