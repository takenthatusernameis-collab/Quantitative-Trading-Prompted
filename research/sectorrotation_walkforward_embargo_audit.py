#!/usr/bin/env python3
"""Walk-forward embargo audit for sectorrotation_001 (Cycle 909)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.sectorrotation_long_sample_feasibility import (
    CONFIG_CAND,
    evaluate_walkforward,
    load_yaml,
)
from src.evaluation.walkforward import generate_walkforward_splits

OUT_REPORT = REPO_ROOT / "research" / "reports" / "sectorrotation_walkforward_embargo_001.md"
OUT_EXP = REPO_ROOT / "research" / "experiments" / "sectorrotation_walkforward_embargo_001.md"

PUBLISHED_WF_MEAN = 0.847243


def mean_consecutive_overlap_days(rows):
    if len(rows) < 2:
        return 0.0
    overlaps = []
    for i in range(1, len(rows)):
        a = pd.Timestamp(rows[i-1]["test_end"])
        b = pd.Timestamp(rows[i]["test_start"])
        if b <= a:
            overlaps.append((a - b).days)
        else:
            overlaps.append(0.0)
    return float(np.mean(overlaps)) if overlaps else 0.0


def max_disjoint(rows):
    if not rows:
        return 0
    # greedy count of pairwise disjoint test windows
    count = 0
    last_end = None
    for r in sorted(rows, key=lambda x: x["test_start"]):
        s = pd.Timestamp(r["test_start"])
        e = pd.Timestamp(r["test_end"])
        if last_end is None or s > last_end:
            count += 1
            last_end = e
    return count


def design_a_splits(start, end, cfg):
    return generate_walkforward_splits(
        start, end,
        float(cfg["train_years"]), float(cfg["test_months"]),
        12.0, int(cfg["purge_days"]), int(cfg["embargo_days"]),
    )


def design_b_splits(start, end, cfg):
    all_dates = pd.bdate_range(start=start, end=end)
    if len(all_dates) == 0:
        return []
    splits = []
    train_window = int(cfg["train_years"] * 252)
    test_window = int(cfg["test_months"] * 21)
    purge = int(cfg["purge_days"])
    embargo = int(cfg["embargo_days"])
    idx = 0
    guard = 0
    while guard < 200:
        guard += 1
        if idx + train_window > len(all_dates):
            break
        ts = all_dates[idx]
        te_idx = idx + train_window - 1
        te = all_dates[te_idx]
        test_start_idx = te_idx + 1 + purge
        if test_start_idx >= len(all_dates):
            break
        test_start = all_dates[test_start_idx]
        test_end_idx = test_start_idx + test_window - 1
        if test_end_idx >= len(all_dates):
            break
        test_end = all_dates[test_end_idx]
        splits.append({
            "train_start": ts.strftime("%Y-%m-%d"),
            "train_end": te.strftime("%Y-%m-%d"),
            "test_start": test_start.strftime("%Y-%m-%d"),
            "test_end": test_end.strftime("%Y-%m-%d"),
        })
        nxt = test_end_idx + 1 + embargo
        if nxt <= idx:
            break
        idx = nxt
    return splits


def main():
    cand = load_yaml(CONFIG_CAND)
    wf_cfg = cand["evaluation"]["walk_forward"]
    history_start = cand["history_start"]
    test_end = cand["evaluation"]["splits"]["test_end"]

    # Build strategy path by importing the feasibility module's main logic via exec? Instead replicate minimal.
    # We'll import functions.
    from research.sectorrotation_long_sample_feasibility import (
        build_monthly_weights, portfolio_returns, compute_momentum, select_top_decile,
        month_end_dates, fetch_universe,
    )
    import hashlib
    universe = list(cand["universe"])
    signal = cand["signal"]
    lookback = int(signal["lookback"]); skip = int(signal["skip"]); top_fraction = float(signal["top_fraction"])
    start = pd.Timestamp(cand["history_start"]);
    # fetch from cache
    from src.data.yfinance_fetcher import fetch_universe as fu
    data = fu(universe, start.date().isoformat(), test_end, force=False)
    close = data.xs("Close", level=0, axis=1).ffill().dropna(how="all")
    momentum = compute_momentum(close, lookback=lookback, skip=skip)
    mask = select_top_decile(momentum, top_fraction=top_fraction)
    month_ends = month_end_dates(close.index)
    weights, segments = build_monthly_weights(close, mask, month_ends)
    cost_per_trade = (cand["cost_model"]["commission_bps"] + cand["cost_model"]["slippage_bps"]) / 10000.0
    net_ret, turnover = portfolio_returns(close, weights, cost_per_trade)

    # Published design
    pub_splits = generate_walkforward_splits(
        history_start, test_end,
        float(wf_cfg["train_years"]), float(wf_cfg["test_months"]),
        float(wf_cfg["step_months"]), int(wf_cfg["purge_days"]), int(wf_cfg["embargo_days"]),
    )
    pub_rows = evaluate_walkforward(net_ret, turnover, pub_splits)
    pub_mean = float(np.mean([r["test_sharpe"] for r in pub_rows]))

    # Design A
    a_splits = design_a_splits(history_start, test_end, wf_cfg)
    a_rows = evaluate_walkforward(net_ret, turnover, a_splits)
    a_mean = float(np.mean([r["test_sharpe"] for r in a_rows])) if a_rows else float("nan")

    # Design B
    b_splits = design_b_splits(history_start, test_end, wf_cfg)
    b_rows = evaluate_walkforward(net_ret, turnover, b_splits) if b_splits else []
    b_mean = float(np.mean([r["test_sharpe"] for r in b_rows])) if b_rows else float("nan")

    # overlap diagnostics
    def diag(rows):
        return {"overlap": mean_consecutive_overlap_days(rows), "disjoint": max_disjoint(rows), "folds": len(rows)}

    pub_d = diag(pub_rows); a_d = diag(a_rows); b_d = diag(b_rows)

    anchor_ok = abs(pub_mean - PUBLISHED_WF_MEAN) <= 1e-4

    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_EXP.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# Sectorrotation Walk-Forward Embargo Audit (sectorrotation_walkforward_embargo_001, Cycle 909)")
    lines.append("")
    lines.append(f"- Candidate: sectorrotation_001")
    lines.append(f"- Published WF mean OOS Sharpe: {pub_mean:.6f} (published 0.847243) anchor={'MATCH' if anchor_ok else 'DIFF'}")
    lines.append(f"- Design A folds: {len(a_rows)}, mean {a_mean:.6f}, overlap {a_d['overlap']:.1f}, disjoint {a_d['disjoint']}")
    lines.append(f"- Design B folds: {len(b_rows)}")
    lines.append("")
    lines.append("## Delta (published vs Design A)")
    lines.append(f"- Fold count: {len(pub_rows)} -> {len(a_rows)} (delta {len(a_rows)-len(pub_rows)})")
    lines.append(f"- WF mean OOS Sharpe: {pub_mean:.6f} -> {a_mean:.6f}")
    lines.append(f"- Gate-1 margin (>=0.9): {0.9-pub_mean:.6f} -> {0.9-a_mean:.6f}")
    lines.append(f"- Gate outcome changes under Design A: {'YES' if (pub_mean>=0.9)!=(a_mean>=0.9) else 'NO'}")
    lines.append("")
    lines.append("## Checks")
    lines.append(f"- anchor_reproduces_published: {'PASS' if anchor_ok else 'FAIL'}")
    lines.append(f"- design_a_disjoint: {'PASS' if (a_d['overlap']==0.0 and a_d['disjoint']==a_d['folds']) else 'FAIL'}")
    lines.append(f"- published_has_overlap: {'PASS' if pub_d['overlap']>0 else 'FAIL'}")
    lines.append("")
    lines.append("OVERALL: PASS" if anchor_ok and a_d['overlap']==0.0 and a_d['disjoint']==a_d['folds'] and pub_d['overlap']>0 else "OVERALL: FAIL")
    OUT_REPORT.write_text("\n".join(lines)+"\n")

    exp = []
    exp.append("# Experiment: Walk-forward embargo sensitivity for sectorrotation_001")
    exp.append("")
    exp.append(f"- Published: {len(pub_rows)} folds, mean {pub_mean:.6f}")
    exp.append(f"- Design A: {len(a_rows)} folds, mean {a_mean:.6f}, overlap {a_d['overlap']:.1f}, disjoint {a_d['disjoint']}")
    exp.append(f"- Design B: {len(b_rows)} folds")
    exp.append("")
    exp.append("## Reproduction")
    exp.append("```bash")
    exp.append("python research/sectorrotation_walkforward_embargo_audit.py")
    exp.append("```")
    OUT_EXP.write_text("\n".join(exp)+"\n")

    overall = anchor_ok and a_d['overlap']==0.0 and a_d['disjoint']==a_d['folds'] and pub_d['overlap']>0
    print("OVERALL: PASS" if overall else "OVERALL: FAIL")
    print(f"report: {OUT_REPORT}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
PYEOF
