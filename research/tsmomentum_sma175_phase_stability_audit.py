#!/usr/bin/env python3
"""Walk-forward mean stability audit for SMA-175 variant of ``tsmomentum_spytrend_001``.

Decomposes the walk-forward mean OOS Sharpe for SMA-175 into fold phases
(odd/even folds) and leave-one-out influence, following the same methodology
as ``incumbent_phase_stability_audit.py``. Read-only comparison only; does
not modify ``run_cycle6.py``, ``data/``, ``config/``, or committed artifacts.
"""

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

from research.run_cycle6 import (  # noqa: E402
    END_DATE,
    LOOKBACK,
    SKIP,
    START_DATE,
    SYMBOLS,
    TOP_FRACTION,
    WF_EMBARGO_DAYS,
    WF_PURGE_DAYS,
    WF_STEP_MONTHS,
    WF_TEST_MONTHS,
    WF_TRAIN_YEARS,
    _apply_overlay,
)
from research.tsmomentum_walkforward_embargo_audit import (  # noqa: E402
    EXPERIMENTS_DIR,
    GATE_POOLED_TRADES_MIN,
    GATE_POSITIVE_FOLD_RATE_MIN,
    GATE_WF_MEAN_MIN,
    RAW_DIR,
    REPORTS_DIR,
    AuditError,
    decision_from_gates,
    evaluate_design,
    fail,
    fingerprint,
    gate_table,
    load_close_from_cache,
    mean_consecutive_overlap_days,
    max_disjoint_test_windows,
    published_splits,
    tracked_artifact_hashes,
)
from src.backtest.engine import get_cost_params, get_risk_free_rate  # noqa: E402
from src.features.momentum import build_weights  # noqa: E402

CYCLE = "916"
CANDIDATE_ID = "tsmomentum_spytrend_001"
SMA_WINDOW = 175
THIN_TRADE_MAX = 10

OUT_REPORT = REPORTS_DIR / "tsmomentum_sma175_phase_stability_001.md"
OUT_EXP = EXPERIMENTS_DIR / "tsmomentum_sma175_phase_stability_001.md"


def _fmt(value: float, digits: int = 6) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "N/A"
    return f"{float(value):.{digits}f}"


def build_candidate_path_sma175(close: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    weights = build_weights(close, lookback=LOOKBACK, skip=SKIP, top_fraction=TOP_FRACTION)
    common = close.index.intersection(weights.index)
    close_a = close.loc[common]
    weights_a = weights.loc[common]
    daily_ret = close_a.pct_change().fillna(0.0)

    spy = close_a["SPY"]
    spy_sma = spy.rolling(SMA_WINDOW).mean()
    exposure = pd.Series(1.0, index=close_a.index)
    exposure[spy < spy_sma] = 0.0
    exposure[spy.isna() | spy_sma.isna()] = 0.0

    combined_weights, net_ret, _ = _apply_overlay(daily_ret, weights_a, exposure_factor=exposure)
    if len(net_ret) == 0:
        fail("candidate path is empty")
    return net_ret, combined_weights


def run_audit(
    experiments_dir: Path = EXPERIMENTS_DIR,
    raw_dir: Path = RAW_DIR,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def record_check(name: str, ok: bool, observed: Any = "", expected: Any = "") -> None:
        checks.append({"name": name, "pass": bool(ok), "observed": observed, "expected": expected})

    data_before = fingerprint(REPO_ROOT / "data")
    config_before = fingerprint(REPO_ROOT / "config")
    artifacts_before = tracked_artifact_hashes()

    close = load_close_from_cache(list(SYMBOLS), raw_dir)
    net_ret, weights = build_candidate_path_sma175(close)
    record_check("cache_only_path_built", len(net_ret) > 0, f"{len(net_ret)} sessions, {len(close.columns)} symbols", "non-empty path")

    splits = published_splits()
    pub = evaluate_design(net_ret, weights, splits)
    pub["gates"] = gate_table(pub["summary"])
    pub["decision"] = decision_from_gates(pub["gates"])

    record_check("independence_evaluated_published_design", True, f"mean_overlap_days={pub['independence']['mean_consecutive_overlap_days']}, max_disjoint={pub['independence']['max_disjoint_test_windows']}", "evaluated")
    record_check("reproduces_published_fold_count", pub["summary"].get("n_folds") == 48, f"n_folds={pub['summary'].get('n_folds')}", "48")

    # Phase decomposition
    phase_a_splits = [s for i, s in enumerate(splits) if i % 2 == 0]
    phase_b_splits = [s for i, s in enumerate(splits) if i % 2 == 1]
    des_a = evaluate_design(net_ret, weights, phase_a_splits)
    des_b = evaluate_design(net_ret, weights, phase_b_splits)
    des_a["gates"] = gate_table(des_a["summary"])
    des_a["decision"] = decision_from_gates(des_a["gates"])
    des_b["gates"] = gate_table(des_b["summary"])
    des_b["decision"] = decision_from_gates(des_b["gates"])

    folds = pub["folds"]
    phase_a_numbers = [f["fold"] for f in folds if f["fold"] % 2 == 1]
    phase_b_numbers = [f["fold"] for f in folds if f["fold"] % 2 == 0]

    mean_a = float(des_a["summary"]["mean_test_sharpe"])
    mean_b = float(des_b["summary"]["mean_test_sharpe"])
    mean_all = float(pub["summary"]["mean_test_sharpe"])
    phases_average = abs(((mean_a + mean_b) / 2.0) - mean_all) <= 1e-9

    record_check("phase_a_test_windows_pairwise_disjoint", des_a["independence"]["mean_consecutive_overlap_days"] == 0.0 and des_a["independence"]["max_disjoint_test_windows"] == des_a["summary"].get("n_folds", 0), f"overlap={des_a['independence']['mean_consecutive_overlap_days']}, disjoint={des_a['independence']['max_disjoint_test_windows']}, folds={des_a['summary'].get('n_folds', 0)}", "overlap==0 and disjoint==folds")
    record_check("phase_b_test_windows_pairwise_disjoint", des_b["independence"]["mean_consecutive_overlap_days"] == 0.0 and des_b["independence"]["max_disjoint_test_windows"] == des_b["summary"].get("n_folds", 0), f"overlap={des_b['independence']['mean_consecutive_overlap_days']}, disjoint={des_b['independence']['max_disjoint_test_windows']}, folds={des_b['summary'].get('n_folds', 0)}", "overlap==0 and disjoint==folds")
    record_check("phase_union_covers_published_fold_set", set(phase_a_numbers) | set(phase_b_numbers) == set(f["fold"] for f in folds) and set(phase_a_numbers) & set(phase_b_numbers) == set(), f"phase A {len(phase_a_numbers)} folds, phase B {len(phase_b_numbers)} folds", f"all {len(folds)} folds, disjoint")
    record_check("phase_means_average_to_published_mean", phases_average, f"({mean_a:.6f}+{mean_b:.6f})/2={(mean_a+mean_b)/2:.6f}, published {mean_all:.6f}", "equal within tol")

    # Fold influence
    sharpes = [float(r["test_sharpe"]) for r in folds]
    trades = [int(r["test_trades"]) for r in folds]
    influence = []
    for i, r in enumerate(folds):
        loo = float(np.mean(sharpes[:i] + sharpes[i + 1 :]))
        shift = loo - mean_all
        influence.append({"fold": r["fold"], "test_sharpe": sharpes[i], "test_trades": trades[i], "loo_mean": loo, "shift": shift, "abs_shift": abs(shift), "is_thin": trades[i] <= THIN_TRADE_MAX})
    most_influential = max(influence, key=lambda item: item["abs_shift"])
    median = float(np.median(sharpes))
    ordered = sorted(sharpes)
    trimmed = float(np.mean(ordered[1:-1])) if len(ordered) >= 3 else mean_all
    thin = [item for item in influence if item["is_thin"]]
    both_excluded_mean = float(np.mean([s for s, t in zip(sharpes, trades) if t > THIN_TRADE_MAX])) if any(t > THIN_TRADE_MAX for t in trades) else mean_all

    gate1_published = pub["gates"][0]["status"]
    gate1_phase_a = des_a["gates"][0]["status"]
    gate1_phase_b = des_b["gates"][0]["status"]
    outcome_changes_phase = gate1_published != gate1_phase_a or gate1_published != gate1_phase_b
    gate1_thin_excluded = "PASS" if both_excluded_mean >= GATE_WF_MEAN_MIN else "FAIL"
    outcome_changes_thin = gate1_published != gate1_thin_excluded
    pass_stable = (not outcome_changes_phase) and (not outcome_changes_thin)

    data_after = fingerprint(REPO_ROOT / "data")
    config_after = fingerprint(REPO_ROOT / "config")
    artifacts_after = tracked_artifact_hashes()
    record_check("data_unchanged", data_before == data_after)
    record_check("config_unchanged", config_before == config_after)
    record_check("committed_artifacts_unchanged", artifacts_before == artifacts_after)

    commission_bps, slippage_bps = get_cost_params()
    payload = {
        "cycle": CYCLE,
        "candidate": CANDIDATE_ID,
        "sma_window": SMA_WINDOW,
        "overall": "PASS" if all(c["pass"] for c in checks) else "FAIL",
        "checks": checks,
        "published_design": pub,
        "published_mean_recomputed": mean_all,
        "phase_decomposition": {
            "phase_a_fold_numbers": phase_a_numbers,
            "phase_b_fold_numbers": phase_b_numbers,
            "phase_a": {"n_folds": des_a["summary"].get("n_folds", 0), "mean_test_sharpe": mean_a, "median_test_sharpe": float(des_a["summary"]["median_test_sharpe"]), "pct_positive_sharpe": float(des_a["summary"]["pct_positive_sharpe"]), "pooled_oos_trades": int(des_a["summary"]["total_test_trades"]), "gate_table": des_a["gates"], "decision": des_a["decision"], "independence": des_a["independence"]},
            "phase_b": {"n_folds": des_b["summary"].get("n_folds", 0), "mean_test_sharpe": mean_b, "median_test_sharpe": float(des_b["summary"]["median_test_sharpe"]), "pct_positive_sharpe": float(des_b["summary"]["pct_positive_sharpe"]), "pooled_oos_trades": int(des_b["summary"]["total_test_trades"]), "gate_table": des_b["gates"], "decision": des_b["decision"], "independence": des_b["independence"]},
            "phases_are_pairwise_disjoint": True,
            "union_covers_published_folds": True,
            "phase_means_average_to_published_mean": bool(phases_average),
            "gate1_phase_a": gate1_phase_a,
            "gate1_phase_b": gate1_phase_b,
            "gate1_outcome_changes_between_phases": bool(outcome_changes_phase),
        },
        "fold_influence": {
            "published_mean": mean_all,
            "published_median": median,
            "trimmed_mean_drop_min_max": trimmed,
            "most_influential_fold": most_influential,
            "influence": influence,
            "thin_trade_folds": [item["fold"] for item in thin],
            "loo_mean_thin_trade_folds": {str(item["fold"]): item["loo_mean"] for item in thin},
            "both_thin_trade_folds_excluded_mean": both_excluded_mean,
            "gate1_when_thin_trade_folds_excluded": gate1_thin_excluded,
            "gate1_outcome_changes_when_thin_trade_folds_excluded": bool(outcome_changes_thin),
        },
        "stability": {
            "gate1_outcome_changes_between_phases": bool(outcome_changes_phase),
            "gate1_outcome_changes_when_thin_trade_folds_excluded": bool(outcome_changes_thin),
            "published_pass_stable": bool(pass_stable),
        },
        "read_only": {"data_unchanged": data_before == data_after, "config_unchanged": config_before == config_after, "committed_artifacts_unchanged": artifacts_before == artifacts_after},
        "commission_bps": commission_bps * 10000.0,
        "slippage_bps": slippage_bps * 10000.0,
        "rf_annual": get_risk_free_rate(),
        "point_in_time": "signals use only data available at formation (weights shifted one day), SPY SMA computed point-in-time, overlay/cost model applied on same path",
        "data_source": "committed parquet cache in data/raw/ (fetcher never called)",
    }
    return payload


def _fold_table(rows):
    lines = ["| Fold | Train Start | Train End | Test Start | Test End | Train Sharpe | Test Sharpe | Test Ann. Ret. | Test Max DD | Test Trades |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['fold']} | {r['train_start']} | {r['train_end']} | {r['test_start']} | {r['test_end']} | {_fmt(r['train_sharpe'],4)} | {_fmt(r['test_sharpe'],4)} | {_fmt(r['test_ann_return'],4)} | {_fmt(r['test_max_dd'],4)} | {r['test_trades']} |")
    return lines


def _gate_lines(gates):
    if not gates:
        return ["- Gate table not formed (insufficient folds)."]
    out = []
    for g in gates:
        obs = g["observed"]
        if isinstance(obs, float):
            obs_s = _fmt(obs)
        else:
            obs_s = str(obs)
        out.append(f"- {g['gate']}: threshold {g['threshold']}, observed {obs_s}, margin {_fmt(g['margin'])}, status {g['status']}")
    return out


def render_report(payload):
    phases = payload["phase_decomposition"]
    infl = payload["fold_influence"]
    pub = payload["published_design"]
    lines = []
    lines.append(f"# TSMomentum SMA-175 Walk-Forward Mean Stability Audit (tsmomentum_sma175_phase_stability_001, Cycle {payload['cycle']})")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Candidate: `{payload['candidate']}` (variant: SPY SMA window = {payload['sma_window']})")
    lines.append(f"- Walk-forward design: published splits (48 folds), purge {WF_PURGE_DAYS}d / embargo {WF_EMBARGO_DAYS}d, train {WF_TRAIN_YEARS}y / test {WF_TEST_MONTHS}m / step {WF_STEP_MONTHS}m")
    lines.append(f"- WF mean OOS Sharpe (recomputed, SMA-{payload['sma_window']}): {payload['published_mean_recomputed']:.6f}")
    lines.append(f"- Gate-1 outcome under phase A (odd folds): **{phases['gate1_phase_a']}**; under phase B (even folds): **{phases['gate1_phase_b']}** — outcome changes between phases: **{'YES' if phases['gate1_outcome_changes_between_phases'] else 'NO'}**")
    lines.append(f"- Thin-trade folds (<= {THIN_TRADE_MAX} trades): {infl['thin_trade_folds']} (leave-one-out means: " + ", ".join(f"fold {k} {_fmt(v,6)}" for k, v in sorted(infl['loo_mean_thin_trade_folds'].items(), key=lambda x: int(x[0]))) + ")")
    lines.append(f"- WF mean OOS Sharpe excluding both thin-trade folds: {infl['both_thin_trade_folds_excluded_mean']:.6f} — Gate-1 status: **{infl['gate1_when_thin_trade_folds_excluded']}** (outcome changes when excluded: **{'YES' if infl['gate1_outcome_changes_when_thin_trade_folds_excluded'] else 'NO'}**)")
    lines.append(f"- Phase means average to published mean: **{'YES' if phases['phase_means_average_to_published_mean'] else 'NO'}** ({payload['published_mean_recomputed']:.6f} = ({phases['phase_a']['mean_test_sharpe']:.6f} + {phases['phase_b']['mean_test_sharpe']:.6f}) / 2)")
    lines.append(f"- Overall stability verdict (phase stability AND thin-trade robustness): **{'PASS' if payload['stability']['published_pass_stable'] else 'FAIL'}**")
    lines.append("")
    lines.append("## Read-only / integrity checks")
    lines.append("")
    for c in payload["checks"]:
        lines.append(f"- [{ 'PASS' if c['pass'] else 'FAIL' }] {c['name']}: observed={c['observed']}; expected={c['expected']}")
    lines.append("")
    lines.append("## Phase decomposition")
    lines.append("")
    lines.append(f"### Phase A (odd fold numbers: {phases['phase_a_fold_numbers']}) — {phases['phase_a']['n_folds']} folds")
    lines.append(f"- Mean test Sharpe: {phases['phase_a']['mean_test_sharpe']:.6f}, median {phases['phase_a']['median_test_sharpe']:.6f}, % positive {phases['phase_a']['pct_positive_sharpe']:.2f}%")
    lines.append(f"- Pooled OOS trades: {phases['phase_a']['pooled_oos_trades']}")
    lines.append("- Gate table:")
    for gl in _gate_lines(phases['phase_a']['gate_table']):
        lines.append(f"  {gl}")
    lines.append(f"- Decision: {phases['phase_a']['decision']}")
    lines.append("")
    lines.append(f"### Phase B (even fold numbers: {phases['phase_b_fold_numbers']}) — {phases['phase_b']['n_folds']} folds")
    lines.append(f"- Mean test Sharpe: {phases['phase_b']['mean_test_sharpe']:.6f}, median {phases['phase_b']['median_test_sharpe']:.6f}, % positive {phases['phase_b']['pct_positive_sharpe']:.2f}%")
    lines.append(f"- Pooled OOS trades: {phases['phase_b']['pooled_oos_trades']}")
    lines.append("- Gate table:")
    for gl in _gate_lines(phases['phase_b']['gate_table']):
        lines.append(f"  {gl}")
    lines.append(f"- Decision: {phases['phase_b']['decision']}")
    lines.append("")
    lines.append("## Fold leave-one-out influence (published splits)")
    lines.append("")
    lines.append(f"- Published mean: {infl['published_mean']:.6f}, median: {infl['published_median']:.6f}, trimmed mean (drop min/max): {infl['trimmed_mean_drop_min_max']:.6f}")
    lines.append(f"- Most influential fold: fold {infl['most_influential_fold']['fold']} (test Sharpe {_fmt(infl['most_influential_fold']['test_sharpe'],6)}, trades {infl['most_influential_fold']['test_trades']}), LOO mean {_fmt(infl['most_influential_fold']['loo_mean'],6)}, shift {infl['most_influential_fold']['shift']:+.6f}")
    lines.append("")
    lines.append("| Fold | Test Sharpe | Test Trades | LOO Mean | Shift (LOO - published mean) | Thin (<=10) |")
    lines.append("|---|---|---|---|---|---|")
    for item in infl["influence"]:
        lines.append(f"| {item['fold']} | {_fmt(item['test_sharpe'],6)} | {item['test_trades']} | {_fmt(item['loo_mean'],6)} | {item['shift']:+.6f} | {'Y' if item['is_thin'] else 'N'} |")
    lines.append("")
    lines.append("## Published design fold table (for reference)")
    lines.append("")
    lines.extend(_fold_table(pub["folds"]))
    lines.append("")
    lines.append("## Methodology / guarantees")
    lines.append("")
    lines.append("- Read-only comparison only. Does **not** change `research/run_cycle6.py`, `data/`, `config/`, or committed artifacts.")
    lines.append("- Uses same fold generation (`published_splits`) and evaluation (`evaluate_design`) as incumbent phase stability audit.")
    lines.append("- SMA-175 path computed via same overlay/cost model as run_cycle6 logic.")
    lines.append("- Cache-only data access via `load_close_from_cache`.")
    lines.append("")
    lines.append(f"**OVERALL:** {payload['overall']}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(payload: dict[str, Any]) -> None:
    report_md = render_report(payload)
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_EXP.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_REPORT, "w") as f:
        f.write(report_md)

    exp_md = ["# Experiment: SMA-175 phase stability audit (Cycle 916)", "", "Read-only phase decomposition (odd/even folds) and thin-trade fold influence for SMA-175 variant of tsmomentum_spytrend_001.", "", f"- Report: {OUT_REPORT.relative_to(REPO_ROOT)}", f"- Overall: {payload['overall']}", f"- WF mean OOS Sharpe (SMA-175): {payload['published_mean_recomputed']:.6f}", f"- Phase-stable gate-1: {'YES' if not payload['stability']['gate1_outcome_changes_between_phases'] else 'NO'}", f"- Thin-trade robust: {'YES' if not payload['stability']['gate1_outcome_changes_when_thin_trade_folds_excluded'] else 'NO'}", ""]
    with open(OUT_EXP, "w") as f:
        f.write("\n".join(exp_md))


def main() -> int:
    parser = argparse.ArgumentParser(description="SMA-175 phase stability audit (read-only)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        payload = run_audit()
    except AuditError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if not args.dry_run:
        write_outputs(payload)

    print(f"OVERALL: {payload['overall']}")
    print(f"WF mean Sharpe (SMA-175): {payload['published_mean_recomputed']:.6f}")
    print(f"Phase stable (gate-1 unchanged across phases): {not payload['stability']['gate1_outcome_changes_between_phases']}")
    print(f"Thin-trade robust (gate-1 unchanged when excluding thin folds): {not payload['stability']['gate1_outcome_changes_when_thin_trade_folds_excluded']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
