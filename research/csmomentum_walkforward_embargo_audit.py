#!/usr/bin/env python3
"""Walk-forward embargo audit for ``csmomentum_001`` (Cycle 908)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.csmomentum_common_inception_audit import (  # noqa: E402
    aligned_close_from_cache,
    breadth_stats,
    fail,
    fingerprint,
    load_policy,
    scan_raw_cache,
)
from research.csmomentum_sample_gate_audit import (  # noqa: E402
    BREADTH_FALLBACK,
    COMMITTED_ARTIFACTS,
    EVALUATION_SAMPLE,
    SAMPLE_ORDER,
    UNION_SAMPLE,
    WINDOW_SAMPLE,
    build_gate_table,
    compare_published,
    decimals_of,
    diagnostic_counts,
    fold_diagnostics,
    max_disjoint_test_windows,
    mean_consecutive_overlap_days,
    path_summary,
    sha256_file,
)
from research.month_end_candidate_reaudit import (  # noqa: E402
    build_csmomentum,
    gates_for,
    walkforward,
)
from research.promotion_feasibility_backtest import load_yaml  # noqa: E402
from src.backtest.engine import get_cost_params, get_risk_free_rate  # noqa: E402
from src.evaluation.sharpe import sharpe_ratio  # noqa: E402
from src.evaluation.walkforward import generate_walkforward_splits  # noqa: E402
from src.features.momentum import compute_momentum  # noqa: E402

CONFIG_CAND = REPO_ROOT / "config" / "csmomentum_candidate_001.yaml"
POLICY_DEFAULT = REPO_ROOT / "config" / "sample_policy.yaml"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
EXPERIMENTS_DIR = REPO_ROOT / "research" / "experiments"
OUT_REPORT = REPORTS_DIR / "csmomentum_walkforward_embargo_001.md"
OUT_EXP = EXPERIMENTS_DIR / "csmomentum_walkforward_embargo_001.md"

CANDIDATE_ID = "csmomentum_001"
SAMPLES = (UNION_SAMPLE, EVALUATION_SAMPLE, WINDOW_SAMPLE)
SAMPLES = (UNION_SAMPLE, EVALUATION_SAMPLE, WINDOW_SAMPLE)

PUBLISHED_UNION_WF = {
    "n_folds": "48",
    "mean_test_sharpe": "0.6975",
    "mean_test_sharpe_canonical": "0.8404",
    "median_test_sharpe": "0.6179",
    "pct_positive_sharpe": "0.7917",
    "total_test_trades": "400",
}

FORBIDDEN_UNION_WF = {
    "legacy_calendar_path": "0.6868",
    "daily_rerank_path": "0.6928",
}


def compute_fold_independence(folds: list[dict[str, Any]]) -> dict[str, Any]:
    if not folds:
        return {"mean_consecutive_overlap_days": 0.0, "max_disjoint_test_windows": 0}
    overlap = mean_consecutive_overlap_days(folds)
    disjoint = max_disjoint_test_windows(folds)
    return {
        "mean_consecutive_overlap_days": float(overlap),
        "max_disjoint_test_windows": int(disjoint),
    }


def generate_design_a_splits(
    start_date: str,
    end_date: str,
    train_years: float = 10.0,
    test_months: float = 12.0,
    step_months: float = 12.0,
    purge_days: int = 21,
    embargo_days: int = 21,
) -> list[dict]:
    return generate_walkforward_splits(
        start_date, end_date, train_years, test_months, step_months,
        purge_days, embargo_days,
    )


def generate_design_b_splits(
    start_date: str,
    end_date: str,
    train_years: float = 10.0,
    test_months: float = 12.0,
    purge_days: int = 21,
    embargo_days: int = 21,
) -> list[dict]:
    all_dates = pd.bdate_range(start=start_date, end=end_date)
    if len(all_dates) == 0:
        return []

    splits = []
    train_window = int(train_years * 252)
    test_window = int(test_months * 21)

    idx = 0
    fold_count = 0
    while True:
        if idx + train_window > len(all_dates):
            break
        train_start = all_dates[idx]
        train_end_idx = idx + train_window - 1
        train_end = all_dates[train_end_idx]

        test_start_idx = train_end_idx + 1 + purge_days
        if test_start_idx >= len(all_dates):
            break
        test_start = all_dates[test_start_idx]

        test_end_idx = test_start_idx + test_window - 1
        if test_end_idx >= len(all_dates):
            break
        test_end = all_dates[test_end_idx]

        splits.append({
            "train_start": train_start.strftime("%Y-%m-%d"),
            "train_end": train_end.strftime("%Y-%m-%d"),
            "test_start": test_start.strftime("%Y-%m-%d"),
            "test_end": test_end.strftime("%Y-%m-%d"),
            "train_start_idx": idx,
            "train_end_idx": train_end_idx,
            "test_start_idx": test_start_idx,
            "test_end_idx": test_end_idx,
        })

        next_start = test_end_idx + 1 + embargo_days
        if next_start <= idx:
            break
        idx = next_start
        fold_count += 1
        if fold_count > 200:
            break

    return splits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, default=POLICY_DEFAULT)
    args = parser.parse_args(argv)

    policy, section = load_policy(args.policy)

    cand = load_yaml(CONFIG_CAND)
    universe = list(cand["universe"])
    if list(section["universe"]) != universe:
        fail("policy universe does not match config/csmomentum_candidate_001.yaml")

    signal_cfg = cand["signal"]
    lookback = int(signal_cfg["lookback"])
    skip = int(signal_cfg["skip"])
    top_fraction = float(signal_cfg["top_fraction"])
    evaluation = cand["evaluation"]
    wf_cfg = evaluation["walk_forward"]
    gate_cfg = evaluation["promotion_gates"]
    test_end = str(evaluation["splits"]["test_end"])
    history_start = str(cand["history_start"])

    commission, slippage = get_cost_params()
    cost_per_trade = commission + slippage

    data_before = fingerprint(REPO_ROOT / "data")
    config_before = fingerprint(REPO_ROOT / "config")
    artifacts_before = {rel: sha256_file(REPO_ROOT / rel) for rel in COMMITTED_ARTIFACTS}

    per_symbol_stats, raw_hashes, raw_union_index = scan_raw_cache(universe)
    common_inception = pd.Timestamp(
        max(s["first_date"] for s in per_symbol_stats.values()), tz="UTC"
    )
    ci_str = common_inception.date().isoformat()

    close_full = aligned_close_from_cache(universe)
    close_union = close_full.loc[
        (close_full.index >= pd.Timestamp(history_start, tz="UTC"))
        & (close_full.index <= pd.Timestamp(test_end, tz="UTC"))
    ]

    close_slice = close_full.loc[
        (close_full.index >= common_inception)
        & (close_full.index <= pd.Timestamp(test_end, tz="UTC"))
    ].copy()

    window_index = close_union.loc[
        (close_union.index >= common_inception)
        & (close_union.index <= pd.Timestamp(test_end, tz="UTC"))
    ].index

    union_path = build_csmomentum(close_union, cost_per_trade)
    slice_path = build_csmomentum(close_slice, cost_per_trade)
    window_path_full = build_csmomentum(close_union, cost_per_trade)

    checks = []

    def record_check(name, ok, observed="", expected=""):
        checks.append({"name": name, "pass": bool(ok), "observed": observed, "expected": expected})
        if not ok:
            fail(f"check failed: {name} (observed={observed}, expected={expected})")

    record_check("policy_loaded", True)
    record_check("policy_universe_matches", list(section["universe"]) == universe,
                 str(list(section["universe"])), str(universe))
    record_check("common_inception_derived", True, ci_str)

    # Published design (as in Cycle 907)
    def splits_for(anchor: str):
        return generate_walkforward_splits(
            anchor,
            test_end,
            float(wf_cfg["train_years"]),
            float(wf_cfg["test_months"]),
            float(wf_cfg["step_months"]),
            int(wf_cfg["purge_days"]),
            int(wf_cfg["embargo_days"]),
        )

    union_splits_pub = splits_for(history_start)
    inception_splits_pub = splits_for(ci_str)

    union_wf_pub, union_rows_pub = walkforward(
        union_path["faithful_net"], union_path["faithful_weights"], union_splits_pub
    )
    slice_wf_pub, slice_rows_pub = walkforward(
        slice_path["faithful_net"], slice_path["faithful_weights"], inception_splits_pub
    )
    window_wf_pub, window_rows_pub = walkforward(
        window_path_full["faithful_net"].loc[window_index],
        window_path_full["faithful_weights"].loc[window_index],
        inception_splits_pub,
    )

    # Design A: non-overlapping test windows (step = test window length = 12 months)
    union_splits_a = generate_design_a_splits(
        history_start, test_end,
        float(wf_cfg["train_years"]), float(wf_cfg["test_months"]),
        step_months=12.0,
        purge_days=int(wf_cfg["purge_days"]),
        embargo_days=int(wf_cfg["embargo_days"]),
    )
    inception_splits_a = generate_design_a_splits(
        ci_str, test_end,
        float(wf_cfg["train_years"]), float(wf_cfg["test_months"]),
        step_months=12.0,
        purge_days=int(wf_cfg["purge_days"]),
        embargo_days=int(wf_cfg["embargo_days"]),
    )

    union_wf_a, union_rows_a = walkforward(
        union_path["faithful_net"], union_path["faithful_weights"], union_splits_a
    )
    slice_wf_a, slice_rows_a = walkforward(
        slice_path["faithful_net"], slice_path["faithful_weights"], inception_splits_a
    )
    window_wf_a, window_rows_a = walkforward(
        window_path_full["faithful_net"].loc[window_index],
        window_path_full["faithful_weights"].loc[window_index],
        inception_splits_a,
    )

    # Design B: next training window starts after previous test end + embargo
    union_splits_b = generate_design_b_splits(
        history_start, test_end,
        float(wf_cfg["train_years"]), float(wf_cfg["test_months"]),
        purge_days=int(wf_cfg["purge_days"]),
        embargo_days=int(wf_cfg["embargo_days"]),
    )
    inception_splits_b = generate_design_b_splits(
        ci_str, test_end,
        float(wf_cfg["train_years"]), float(wf_cfg["test_months"]),
        purge_days=int(wf_cfg["purge_days"]),
        embargo_days=int(wf_cfg["embargo_days"]),
    )

    union_wf_b, union_rows_b = walkforward(
        union_path["faithful_net"], union_path["faithful_weights"], union_splits_b
    ) if union_splits_b else ({}, [])
    slice_wf_b, slice_rows_b = walkforward(
        slice_path["faithful_net"], slice_path["faithful_weights"], inception_splits_b
    ) if inception_splits_b else ({}, [])
    window_wf_b, window_rows_b = walkforward(
        window_path_full["faithful_net"].loc[window_index],
        window_path_full["faithful_weights"].loc[window_index],
        inception_splits_b,
    ) if inception_splits_b else ({}, [])

    # Compute independence diagnostics
    pub_indep = {
        UNION_SAMPLE: compute_fold_independence(union_rows_pub),
        EVALUATION_SAMPLE: compute_fold_independence(slice_rows_pub),
        WINDOW_SAMPLE: compute_fold_independence(window_rows_pub),
    }
    a_indep = {
        UNION_SAMPLE: compute_fold_independence(union_rows_a),
        EVALUATION_SAMPLE: compute_fold_independence(slice_rows_a),
        WINDOW_SAMPLE: compute_fold_independence(window_rows_a),
    }
    b_indep = {
        UNION_SAMPLE: compute_fold_independence(union_rows_b),
        EVALUATION_SAMPLE: compute_fold_independence(slice_rows_b),
        WINDOW_SAMPLE: compute_fold_independence(window_rows_b),
    }

    # Gates
    def make_result(wf, rows):
        gates = build_gate_table(wf, gate_cfg)
        # compute decision
        gate_map = {g["gate"]: g for g in gates}
        g1_ok = gate_map["wf_mean_oos_sharpe"]["status"] == "PASS"
        g2_ok = gate_map["positive_fold_rate"]["status"] == "PASS"
        g3_ok = gate_map["pooled_oos_trades"]["status"] == "PASS"
        if (not g1_ok) or (not g2_ok):
            decision_label = "Rejected/Failed"
            decision_detail = "falsified (gate 1 or gate 2 fails)"
        elif g3_ok and g1_ok and g2_ok:
            decision_label = "Passes preliminary gates"
            decision_detail = "all evaluated gates pass (plateau not evaluated)"
        else:
            decision_label = "Inconclusive"
            decision_detail = "some gates fail"
        return {
            "wf": wf,
            "rows": rows,
            "gates": gates,
            "decision": {"label": decision_label, "detail": decision_detail},
        }

    results_pub = {
        UNION_SAMPLE: make_result(union_wf_pub, union_rows_pub),
        EVALUATION_SAMPLE: make_result(slice_wf_pub, slice_rows_pub),
        WINDOW_SAMPLE: make_result(window_wf_pub, window_rows_pub),
    }
    results_a = {
        UNION_SAMPLE: make_result(union_wf_a, union_rows_a),
        EVALUATION_SAMPLE: make_result(slice_wf_a, slice_rows_a),
        WINDOW_SAMPLE: make_result(window_wf_a, window_rows_a),
    }
    results_b = {
        UNION_SAMPLE: make_result(union_wf_b, union_rows_b) if union_rows_b else {"wf": {}, "rows": [], "gates": [], "decision": {"label": "Insufficient folds", "detail": "too few folds to evaluate gate table"}},
        EVALUATION_SAMPLE: make_result(slice_wf_b, slice_rows_b) if slice_rows_b else {"wf": {}, "rows": [], "gates": [], "decision": {"label": "Insufficient folds", "detail": "too few folds to evaluate gate table"}},
        WINDOW_SAMPLE: make_result(window_wf_b, window_rows_b) if window_rows_b else {"wf": {}, "rows": [], "gates": [], "decision": {"label": "Insufficient folds", "detail": "too few folds to evaluate gate table"}},
    }

    # Check anchor
    anchor_rows = []
    observed_anchor = {
        "n_folds": str(int(union_wf_pub.get("n_folds", 0))),
        "mean_test_sharpe": float(union_wf_pub.get("mean_test_sharpe", float("nan"))),
        "mean_test_sharpe_canonical": float(union_wf_pub.get("mean_test_sharpe_canonical", float("nan"))),
        "median_test_sharpe": float(union_wf_pub.get("median_test_sharpe", float("nan"))),
        "pct_positive_sharpe": float(union_wf_pub.get("pct_positive_sharpe", float("nan"))),
        "total_test_trades": int(union_wf_pub.get("total_test_trades", 0)),
    }
    for k, pub_s in PUBLISHED_UNION_WF.items():
        if k == "n_folds":
            obs = int(observed_anchor[k]) if isinstance(observed_anchor[k], str) else observed_anchor[k]
            pub = int(pub_s)
            ok = (obs == pub)
            anchor_rows.append({"metric": k, "published": pub, "observed": obs, "match": ok})
        elif k == "total_test_trades":
            obs = int(observed_anchor[k])
            pub = int(pub_s)
            ok = (obs == pub)
            anchor_rows.append({"metric": k, "published": pub, "observed": obs, "match": ok})
        else:
            pub = float(pub_s)
            obs = float(observed_anchor[k])
            decimals = decimals_of(pub_s)
            tol = 10.0 ** (-decimals)
            ok = abs(obs - pub) <= tol
            anchor_rows.append({"metric": k, "published": pub, "published_text": pub_s, "observed": obs, "abs_diff": abs(obs-pub), "match": bool(ok)})
    anchor_ok = all(r["match"] for r in anchor_rows)
    record_check("reproduces_committed_config_faithful_record_union_sample", anchor_ok, str(observed_anchor), str(PUBLISHED_UNION_WF))

    # Check no forbidden values
    mean_union = float(union_wf_pub.get("mean_test_sharpe", float("nan")))
    forbidden_ok = (abs(mean_union - 0.6868) > 1e-4) and (abs(mean_union - 0.6928) > 1e-4)
    record_check("does_not_produce_legacy_or_daily_values", forbidden_ok, mean_union, "!=0.6868 and !=0.6928")

    # Check Design A independence
    a_union_disjoint = a_indep[UNION_SAMPLE]["max_disjoint_test_windows"]
    a_union_folds = len(union_rows_a)
    a_indep_ok = (a_indep[UNION_SAMPLE]["mean_consecutive_overlap_days"] == 0.0 and a_union_disjoint == a_union_folds)
    record_check("design_a_test_windows_pairwise_disjoint", a_indep_ok,
                 f"overlap={a_indep[UNION_SAMPLE]['mean_consecutive_overlap_days']}, disjoint={a_union_disjoint}, folds={a_union_folds}",
                 "overlap==0 and disjoint==folds")

    pub_indep_ok = (pub_indep[UNION_SAMPLE]["mean_consecutive_overlap_days"] > 0)  # published design has overlap
    record_check("published_design_has_overlap", pub_indep_ok)

    # Fingerprints
    data_after = fingerprint(REPO_ROOT / "data")
    config_after = fingerprint(REPO_ROOT / "config")
    artifacts_after = {rel: sha256_file(REPO_ROOT / rel) for rel in COMMITTED_ARTIFACTS}
    record_check("data_unchanged", data_before == data_after)
    record_check("config_unchanged", config_before == config_after)
    record_check("committed_artifacts_unchanged", artifacts_before == artifacts_after)

    # Ensure output dirs
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)

    # Build report
    payload = {
        "cycle": "908",
        "candidate": CANDIDATE_ID,
        "policy_path": str(POLICY_DEFAULT),
        "config_path": str(CONFIG_CAND),
        "gate_scale": "backtest_sharpe_ratio",
        "overall": "PASS" if all(c["pass"] for c in checks) else "FAIL",
        "checks": checks,
        "common_inception": ci_str,
        "anchor": {"rows": anchor_rows, "matches": anchor_ok},
        "published_design": {
            UNION_SAMPLE: {"wf": union_wf_pub, "gates": results_pub[UNION_SAMPLE]["gates"], "decision": results_pub[UNION_SAMPLE]["decision"], "folds": len(union_rows_pub), "independence": pub_indep[UNION_SAMPLE]},
            EVALUATION_SAMPLE: {"wf": slice_wf_pub, "gates": results_pub[EVALUATION_SAMPLE]["gates"], "decision": results_pub[EVALUATION_SAMPLE]["decision"], "folds": len(slice_rows_pub), "independence": pub_indep[EVALUATION_SAMPLE]},
            WINDOW_SAMPLE: {"wf": window_wf_pub, "gates": results_pub[WINDOW_SAMPLE]["gates"], "decision": results_pub[WINDOW_SAMPLE]["decision"], "folds": len(window_rows_pub), "independence": pub_indep[WINDOW_SAMPLE]},
        },
        "design_a_nonoverlapping": {
            UNION_SAMPLE: {"wf": union_wf_a, "gates": results_a[UNION_SAMPLE]["gates"], "decision": results_a[UNION_SAMPLE]["decision"], "folds": len(union_rows_a), "independence": a_indep[UNION_SAMPLE], "rows": union_rows_a},
            EVALUATION_SAMPLE: {"wf": slice_wf_a, "gates": results_a[EVALUATION_SAMPLE]["gates"], "decision": results_a[EVALUATION_SAMPLE]["decision"], "folds": len(slice_rows_a), "independence": a_indep[EVALUATION_SAMPLE], "rows": slice_rows_a},
            WINDOW_SAMPLE: {"wf": window_wf_a, "gates": results_a[WINDOW_SAMPLE]["gates"], "decision": results_a[WINDOW_SAMPLE]["decision"], "folds": len(window_rows_a), "independence": a_indep[WINDOW_SAMPLE], "rows": window_rows_a},
        },
        "design_b_embargo_literal": {
            UNION_SAMPLE: {"wf": union_wf_b, "gates": results_b[UNION_SAMPLE]["gates"], "decision": results_b[UNION_SAMPLE]["decision"], "folds": len(union_rows_b), "independence": b_indep[UNION_SAMPLE], "rows": union_rows_b},
            EVALUATION_SAMPLE: {"wf": slice_wf_b, "gates": results_b[EVALUATION_SAMPLE]["gates"], "decision": results_b[EVALUATION_SAMPLE]["decision"], "folds": len(slice_rows_b), "independence": b_indep[EVALUATION_SAMPLE], "rows": slice_rows_b},
            WINDOW_SAMPLE: {"wf": window_wf_b, "gates": results_b[WINDOW_SAMPLE]["gates"], "decision": results_b[WINDOW_SAMPLE]["decision"], "folds": len(window_rows_b), "independence": b_indep[WINDOW_SAMPLE], "rows": window_rows_b},
        },
        "delta_published_vs_design_a_union": {
            "fold_count_delta": len(union_rows_a) - len(union_rows_pub),
            "mean_sharpe_published": float(union_wf_pub.get("mean_test_sharpe", float("nan"))),
            "mean_sharpe_design_a": float(union_wf_a.get("mean_test_sharpe", float("nan"))),
            "gate1_margin_published": gate_cfg["wf_mean_oos_sharpe_min"] - float(union_wf_pub.get("mean_test_sharpe", float("nan"))),
            "gate1_margin_design_a": gate_cfg["wf_mean_oos_sharpe_min"] - float(union_wf_a.get("mean_test_sharpe", float("nan"))),
            "verdict_survives": results_a[UNION_SAMPLE]["decision"]["label"] == results_pub[UNION_SAMPLE]["decision"]["label"],
        },
    }

    # Write report
    report_lines = []
    report_lines.append("# CSMomentum Walk-Forward Embargo Audit (csmomentum_walkforward_embargo_001, Cycle 908)")
    report_lines.append("")
    report_lines.append("## Summary")
    report_lines.append("")
    report_lines.append(f"- Candidate: `{CANDIDATE_ID}`")
    report_lines.append(f"- Gate scale: `backtest_sharpe_ratio` (backtest scale only)")
    report_lines.append(f"- Common inception (re-derived): `{ci_str}`")
    report_lines.append(f"- Verdict (published): **{results_pub[UNION_SAMPLE]['decision']['label']}**")
    report_lines.append(f"- Verdict survives Design A: **{'YES' if payload['delta_published_vs_design_a_union']['verdict_survives'] else 'NO'}**")
    report_lines.append("")
    report_lines.append("## 1. Reproduction anchor (published design on union_sample)")
    report_lines.append("")
    report_lines.append("| Metric | Published | Observed | Match |")
    report_lines.append("|---|---|---|---|")
    for r in anchor_rows:
        if "published_text" in r:
            report_lines.append(f"| {r['metric']} | {r['published_text']} | {r['observed']:.10g} | {'MATCH' if r['match'] else 'DIFF'} |")
        else:
            report_lines.append(f"| {r['metric']} | {r['published']} | {r['observed']} | {'MATCH' if r['match'] else 'DIFF'} |")
    report_lines.append("")
    report_lines.append(f"**Anchor overall:** {'MATCH' if anchor_ok else 'DIFF'} (tool OVERALL depends on this)")
    report_lines.append("")
    report_lines.append("## 2. Three designs, three samples")
    report_lines.append("")
    report_lines.append("### 2.1 Published design (as in Cycle 907)")
    report_lines.append("")
    report_lines.append(f"| Sample | Folds | WF mean OOS Sharpe (backtest) | Median | Positive folds | Pooled OOS trades | Mean consecutive overlap (days) | Max disjoint test windows | Decision |")
    report_lines.append(f"|---|---|---|---|---|---|---|---|---|")
    for name in SAMPLES:
        wf = results_pub[name]["wf"]
        indep = pub_indep[name]
        report_lines.append(f"| {name} | {len(results_pub[name]['rows'])} | {wf.get('mean_test_sharpe', float('nan')):.6f} | {wf.get('median_test_sharpe', float('nan')):.6f} | {wf.get('pct_positive_sharpe', float('nan')):.2%} | {wf.get('total_test_trades', 0)} | {indep['mean_consecutive_overlap_days']:.1f} | {indep['max_disjoint_test_windows']} | {results_pub[name]['decision']['label']} |")
    report_lines.append("")
    report_lines.append("### 2.2 Design A (non-overlapping test windows, primary sensitivity)")
    report_lines.append("")
    report_lines.append(f"| Sample | Folds | WF mean OOS Sharpe (backtest) | Median | Positive folds | Pooled OOS trades | Mean consecutive overlap (days) | Max disjoint test windows | Decision |")
    report_lines.append(f"|---|---|---|---|---|---|---|---|---|")
    for name in SAMPLES:
        wf = results_a[name]["wf"]
        indep = a_indep[name]
        report_lines.append(f"| {name} | {len(results_a[name]['rows'])} | {wf.get('mean_test_sharpe', float('nan')):.6f} | {wf.get('median_test_sharpe', float('nan')):.6f} | {wf.get('pct_positive_sharpe', float('nan')):.2%} | {wf.get('total_test_trades', 0)} | {indep['mean_consecutive_overlap_days']:.1f} | {indep['max_disjoint_test_windows']} | {results_a[name]['decision']['label']} |")
    report_lines.append("")
    report_lines.append("### 2.3 Design B (configuration's embargo applied literally, informational)")
    report_lines.append("")
    report_lines.append(f"| Sample | Folds | WF mean OOS Sharpe (backtest) | Median | Positive folds | Pooled OOS trades | Mean consecutive overlap (days) | Max disjoint test windows | Decision |")
    report_lines.append(f"|---|---|---|---|---|---|---|---|---|")
    for name in SAMPLES:
        wf = results_b[name]["wf"]
        indep = b_indep[name]
        folds_b = len(results_b[name]['rows'])
        if folds_b == 0 or not wf:
            report_lines.append(f"| {name} | 0 | N/A | N/A | N/A | 0 | {indep['mean_consecutive_overlap_days']:.1f} | {indep['max_disjoint_test_windows']} | Insufficient folds (cannot form gate table) |")
        else:
            report_lines.append(f"| {name} | {folds_b} | {wf.get('mean_test_sharpe', float('nan')):.6f} | {wf.get('median_test_sharpe', float('nan')):.6f} | {wf.get('pct_positive_sharpe', float('nan')):.2%} | {wf.get('total_test_trades', 0)} | {indep['mean_consecutive_overlap_days']:.1f} | {indep['max_disjoint_test_windows']} | {results_b[name]['decision']['label']} |")
    report_lines.append("")
    report_lines.append("## 3. Delta (published vs Design A, union_sample)")
    report_lines.append("")
    report_lines.append(f"- Fold count: published {len(union_rows_pub)}, Design A {len(union_rows_a)} (delta {len(union_rows_a)-len(union_rows_pub)})")
    report_lines.append(f"- WF mean OOS Sharpe (backtest): published {union_wf_pub.get('mean_test_sharpe'):.6f}, Design A {union_wf_a.get('mean_test_sharpe'):.6f}")
    report_lines.append(f"- Gate-1 margin (>=0.9): published {gate_cfg['wf_mean_oos_sharpe_min'] - float(union_wf_pub.get('mean_test_sharpe')):.6f}, Design A {gate_cfg['wf_mean_oos_sharpe_min'] - float(union_wf_a.get('mean_test_sharpe')):.6f}")
    report_lines.append(f"- Published verdict **Rejected/Failed** survives Design A: **{'YES' if payload['delta_published_vs_design_a_union']['verdict_survives'] else 'NO'}**")
    report_lines.append("")
    report_lines.append("## 4. Gate tables")
    report_lines.append("")
    report_lines.append("### Published design (union_sample)")
    for g in results_pub[UNION_SAMPLE]["gates"]:
        report_lines.append(f"- {g['gate']}: threshold {g['threshold']}, observed {g['observed']}, status {g['status']} {'({})'.format(g.get('reason')) if g.get('reason') else ''}")
    report_lines.append("")
    report_lines.append("### Design A (union_sample)")
    for g in results_a[UNION_SAMPLE]["gates"]:
        report_lines.append(f"- {g['gate']}: threshold {g['threshold']}, observed {g['observed']}, status {g['status']} {'({})'.format(g.get('reason')) if g.get('reason') else ''}")
    report_lines.append("")
    report_lines.append("## 5. Independence diagnostic (all designs)")
    report_lines.append("")
    report_lines.append("| Design | union_sample (folds / overlap days / disjoint) | common_inception_slice (folds / overlap days / disjoint) | common_inception_window (folds / overlap days / disjoint) |")
    report_lines.append("|---|---|---|---|")
    report_lines.append(f"| Published | {len(union_rows_pub)} / {pub_indep[UNION_SAMPLE]['mean_consecutive_overlap_days']:.1f} / {pub_indep[UNION_SAMPLE]['max_disjoint_test_windows']} | {len(slice_rows_pub)} / {pub_indep[EVALUATION_SAMPLE]['mean_consecutive_overlap_days']:.1f} / {pub_indep[EVALUATION_SAMPLE]['max_disjoint_test_windows']} | {len(window_rows_pub)} / {pub_indep[WINDOW_SAMPLE]['mean_consecutive_overlap_days']:.1f} / {pub_indep[WINDOW_SAMPLE]['max_disjoint_test_windows']} |")
    report_lines.append(f"| Design A | {len(union_rows_a)} / {a_indep[UNION_SAMPLE]['mean_consecutive_overlap_days']:.1f} / {a_indep[UNION_SAMPLE]['max_disjoint_test_windows']} | {len(slice_rows_a)} / {a_indep[EVALUATION_SAMPLE]['mean_consecutive_overlap_days']:.1f} / {a_indep[EVALUATION_SAMPLE]['max_disjoint_test_windows']} | {len(window_rows_a)} / {a_indep[WINDOW_SAMPLE]['mean_consecutive_overlap_days']:.1f} / {a_indep[WINDOW_SAMPLE]['max_disjoint_test_windows']} |")
    report_lines.append(f"| Design B | {len(union_rows_b)} / {b_indep[UNION_SAMPLE]['mean_consecutive_overlap_days']:.1f} / {b_indep[UNION_SAMPLE]['max_disjoint_test_windows']} | {len(slice_rows_b)} / {b_indep[EVALUATION_SAMPLE]['mean_consecutive_overlap_days']:.1f} / {b_indep[EVALUATION_SAMPLE]['max_disjoint_test_windows']} | {len(window_rows_b)} / {b_indep[WINDOW_SAMPLE]['mean_consecutive_overlap_days']:.1f} / {b_indep[WINDOW_SAMPLE]['max_disjoint_test_windows']} |")
    report_lines.append("")
    report_lines.append("## 6. Checks")
    for c in checks:
        report_lines.append(f"- [{c['name']}]: {'PASS' if c['pass'] else 'FAIL'}" + (f" (observed: {c['observed']}, expected: {c['expected']})" if c.get('observed') or c.get('expected') else ""))
    report_lines.append("")
    report_lines.append("## 7. JSON payload")
    report_lines.append("```json")
    report_lines.append(json.dumps(payload, indent=2, default=str))
    report_lines.append("```")
    report_lines.append("")

    report_text = "\n".join(report_lines) + "\n"
    OUT_REPORT.write_text(report_text)

    # Write experiment record
    exp_lines = []
    exp_lines.append("# Experiment: Walk-forward embargo sensitivity for `csmomentum_001` (csmomentum_walkforward_embargo_001, Cycle 908)")
    exp_lines.append("")
    exp_lines.append("## Hypothesis reference")
    exp_lines.append("- Candidate hypothesis: `research/hypotheses/csmomentum_001.md`")
    exp_lines.append("- Frozen config: `config/csmomentum_candidate_001.yaml` (read, never changed)")
    exp_lines.append("- Sample policy: `config/sample_policy.yaml` (read, never changed)")
    exp_lines.append("")
    exp_lines.append("## Objective")
    exp_lines.append("Quantify how much of `csmomentum_001`'s walk-forward evidence survives a non-overlapping (embargoed) fold design, publish delta against published protocol, and state whether the published Rejected/Failed verdict survives (sensitivity only).")
    exp_lines.append("")
    exp_lines.append("## Data")
    exp_lines.append(f"- Source: committed raw cache `data/raw/*.parquet` (cache-only, fetcher never called)")
    exp_lines.append(f"- Universe: {universe}")
    exp_lines.append(f"- Common inception (re-derived): {ci_str}")
    exp_lines.append(f"- Test end: {test_end}")
    exp_lines.append("")
    exp_lines.append("## Configurations")
    exp_lines.append("Three fold designs over the same continuously computed point-in-time path, fixed parameters (no per-fold re-optimisation):")
    exp_lines.append("1. **Published design** (Cycle 907): 10y train / 12m test / 6m step, 21d purge, 21d embargo (generator as-is).")
    exp_lines.append("2. **Design A (non-overlapping test windows)**: step = test window length (12 months), all else unchanged.")
    exp_lines.append("3. **Design B (embargo applied literally)**: next training window starts after previous test window ends + 21d embargo (informational).")
    exp_lines.append("")
    exp_lines.append("## Splits")
    exp_lines.append(f"- Published (union): {len(union_rows_pub)} folds, overlap {pub_indep[UNION_SAMPLE]['mean_consecutive_overlap_days']:.1f} days, disjoint {pub_indep[UNION_SAMPLE]['max_disjoint_test_windows']}")
    exp_lines.append(f"- Design A (union): {len(union_rows_a)} folds, overlap {a_indep[UNION_SAMPLE]['mean_consecutive_overlap_days']:.1f} days, disjoint {a_indep[UNION_SAMPLE]['max_disjoint_test_windows']}")
    exp_lines.append(f"- Design B (union): {len(union_rows_b)} folds")
    exp_lines.append("")
    exp_lines.append("## Results (union_sample)")
    exp_lines.append(f"- Published: WF mean OOS Sharpe {union_wf_pub.get('mean_test_sharpe'):.6f} (canonical {union_wf_pub.get('mean_test_sharpe_canonical'):.6f}), median {union_wf_pub.get('median_test_sharpe'):.6f}, positive {union_wf_pub.get('pct_positive_sharpe'):.2%}, pooled trades {union_wf_pub.get('total_test_trades')}, decision {results_pub[UNION_SAMPLE]['decision']['label']}")
    exp_lines.append(f"- Design A: WF mean OOS Sharpe {union_wf_a.get('mean_test_sharpe'):.6f} (canonical {union_wf_a.get('mean_test_sharpe_canonical'):.6f}), median {union_wf_a.get('median_test_sharpe'):.6f}, positive {union_wf_a.get('pct_positive_sharpe'):.2%}, pooled trades {union_wf_a.get('total_test_trades')}, decision {results_a[UNION_SAMPLE]['decision']['label']}")
    exp_lines.append(f"- Design B: folds {len(union_rows_b)}, decision {results_b[UNION_SAMPLE]['decision']['label']}")
    exp_lines.append("")
    exp_lines.append("## Independence diagnostic")
    exp_lines.append("| Design | union | common_inception_slice | common_inception_window |")
    exp_lines.append("|---|---|---|---|")
    exp_lines.append(f"| Published | {pub_indep[UNION_SAMPLE]['max_disjoint_test_windows']} disjoint ({len(union_rows_pub)} folds, {pub_indep[UNION_SAMPLE]['mean_consecutive_overlap_days']:.1f}d overlap) | {pub_indep[EVALUATION_SAMPLE]['max_disjoint_test_windows']} disjoint | {pub_indep[WINDOW_SAMPLE]['max_disjoint_test_windows']} disjoint |")
    exp_lines.append(f"| Design A | {a_indep[UNION_SAMPLE]['max_disjoint_test_windows']} disjoint ({len(union_rows_a)} folds, {a_indep[UNION_SAMPLE]['mean_consecutive_overlap_days']:.1f}d overlap) | {a_indep[EVALUATION_SAMPLE]['max_disjoint_test_windows']} disjoint | {a_indep[WINDOW_SAMPLE]['max_disjoint_test_windows']} disjoint |")
    exp_lines.append(f"| Design B | {b_indep[UNION_SAMPLE]['max_disjoint_test_windows']} disjoint ({len(union_rows_b)} folds) | {b_indep[EVALUATION_SAMPLE]['max_disjoint_test_windows']} disjoint | {b_indep[WINDOW_SAMPLE]['max_disjoint_test_windows']} disjoint |")
    exp_lines.append("")
    exp_lines.append("## Trial count")
    exp_lines.append("- 1 measurement per (design × sample) = 9 runs; no re-optimisation, fixed parameters.")
    exp_lines.append("")
    exp_lines.append("## Reproduction")
    exp_lines.append("```bash")
    exp_lines.append("python research/csmomentum_walkforward_embargo_audit.py")
    exp_lines.append("python research/csmomentum_sample_gate_audit.py")
    exp_lines.append("python research/month_end_candidate_reaudit.py")
    exp_lines.append("python -m pytest -q tests/test_csmomentum_walkforward_embargo_audit.py")
    exp_lines.append("python -m pytest -q tests/test_csmomentum_sample_gate_audit.py")
    exp_lines.append("python -m pytest -q")
    exp_lines.append("git status --porcelain data/")
    exp_lines.append("```")
    exp_lines.append("")

    exp_text = "\n".join(exp_lines) + "\n"
    OUT_EXP.write_text(exp_text)

    print("OVERALL: PASS" if all(c["pass"] for c in checks) else "OVERALL: FAIL")
    print(f"report: {OUT_REPORT}")
    print(f"experiment: {OUT_EXP}")
    print(f"union_sample published: {len(union_rows_pub)} folds, WF mean OOS Sharpe {union_wf_pub.get('mean_test_sharpe'):.4f} (backtest)")
    print(f"union_sample Design A: {len(union_rows_a)} folds, WF mean OOS Sharpe {union_wf_a.get('mean_test_sharpe'):.4f} (backtest)")
    print(f"union_sample Design B: {len(union_rows_b)} folds")

    if not all(c["pass"] for c in checks):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
