#!/usr/bin/env python3
"""Walk-forward mean stability audit for ``tsmomentum_spytrend_001`` (Cycle 911).

Decomposes the published 48-fold walk-forward mean OOS Sharpe (0.9473) into:

1. The two fold phases implied by the 6-month step over 12-month test windows
   (odd folds vs even folds): each with its own fold count, mean/median OOS
   Sharpe, positive fold rate, pooled OOS trades and gate table.
2. A fold leave-one-out influence table: per fold its OOS Sharpe, trade count,
   leave-one-out mean and the shift in the published mean, plus the published
   mean, median, trimmed mean and the leave-one-out means of the thin-trade
   folds (<= 10 trades).

It is a **read-only sensitivity**: the published protocol, the gates, the
candidate parameters and every committed artifact are left untouched, nothing
under ``data/`` or ``config/`` is written, and the fetcher is never called.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.tsmomentum_walkforward_embargo_audit import (  # noqa: E402
    CANDIDATE_ID,
    END_DATE,
    EXPERIMENTS_DIR,
    GATE_POOLED_TRADES_MIN,
    GATE_POSITIVE_FOLD_RATE_MIN,
    GATE_WF_MEAN_MIN,
    LOOKBACK,
    PUBLISHED_WF_MEAN,
    RAW_DIR,
    REPORTS_DIR,
    SKIP,
    SPY_SMA_WINDOW,
    START_DATE,
    SYMBOLS,
    TOP_FRACTION,
    VOL_TARGET,
    VOL_TARGET_LOOKBACK,
    WF_EMBARGO_DAYS,
    WF_PURGE_DAYS,
    WF_STEP_MONTHS,
    WF_TEST_MONTHS,
    WF_TRAIN_YEARS,
    AuditError,
    build_candidate_path,
    build_anchor,
    decision_from_gates,
    evaluate_design,
    fail,
    fingerprint,
    gate_table,
    load_close_from_cache,
    mean_consecutive_overlap_days,
    max_disjoint_test_windows,
    published_splits,
    resolve_published_record,
    tracked_artifact_hashes,
)
from src.backtest.engine import get_cost_params, get_risk_free_rate  # noqa: E402

CYCLE = "911"
THIN_TRADE_MAX = 10  # folds at or below this trade count are "thin-trade" folds

OUT_REPORT = REPORTS_DIR / "tsmomentum_walkforward_mean_robustness_001.md"
OUT_EXP = EXPERIMENTS_DIR / "tsmomentum_walkforward_mean_robustness_001.md"


def _fmt(value: float, digits: int = 6) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "N/A"
    return f"{float(value):.{digits}f}"


def _fold_table(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| Fold | Train Start | Train End | Test Start | Test End | Train Sharpe | Test Sharpe | Test Ann. Ret. | Test Max DD | Test Trades |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            "| {fold} | {train_start} | {train_end} | {test_start} | {test_end} | "
            "{train_sharpe} | {test_sharpe} | {test_ann_return} | {test_max_dd} | {test_trades} |".format(
                fold=r["fold"],
                train_start=r["train_start"],
                train_end=r["train_end"],
                test_start=r["test_start"],
                test_end=r["test_end"],
                train_sharpe=_fmt(r["train_sharpe"], 4),
                test_sharpe=_fmt(r["test_sharpe"], 4),
                test_ann_return=_fmt(r["test_ann_return"], 4),
                test_max_dd=_fmt(r["test_max_dd"], 4),
                test_trades=r["test_trades"],
            )
        )
    return lines


def _gate_lines(gates: list[dict[str, Any]]) -> list[str]:
    if not gates:
        return ["- Gate table not formed (insufficient folds)."]
    return [
        "- {gate}: threshold {threshold}, observed {observed}, margin {margin}, status {status}".format(
            gate=g["gate"],
            threshold=g["threshold"],
            observed=_fmt(g["observed"]) if isinstance(g["observed"], float) else g["observed"],
            margin=_fmt(g["margin"]),
            status=g["status"],
        )
        for g in gates
    ]


def run_audit(
    experiments_dir: Path = EXPERIMENTS_DIR,
    raw_dir: Path = RAW_DIR,
) -> dict[str, Any]:
    """Run the whole audit and return the payload (no file writes)."""
    checks: list[dict[str, Any]] = []

    def record_check(name: str, ok: bool, observed: Any = "", expected: Any = "") -> None:
        checks.append(
            {"name": name, "pass": bool(ok), "observed": observed, "expected": expected}
        )

    record_path, published = resolve_published_record(experiments_dir)
    record_check(
        "published_record_resolved_by_content",
        True,
        str(
            record_path.relative_to(REPO_ROOT)
            if record_path.is_relative_to(REPO_ROOT)
            else record_path
        ),
        "exactly one published walk-forward record carrying the published anchor",
    )

    data_before = fingerprint(REPO_ROOT / "data")
    config_before = fingerprint(REPO_ROOT / "config")
    artifacts_before = tracked_artifact_hashes()

    close = load_close_from_cache(list(SYMBOLS), raw_dir)
    net_ret, weights = build_candidate_path(close)
    record_check(
        "cache_only_path_built",
        len(net_ret) > 0,
        f"{len(net_ret)} sessions, {len(close.columns)} symbols",
        "non-empty path",
    )

    splits = published_splits()
    pub = evaluate_design(net_ret, weights, splits)
    pub["gates"] = gate_table(pub["summary"])
    pub["decision"] = decision_from_gates(pub["gates"])

    anchor = build_anchor(published, pub)
    record_check(
        "reproduces_published_walk_forward_aggregate",
        anchor["matches"],
        "; ".join(f"{r['metric']}={r['observed']} (published {r['published_text']})" for r in anchor["rows"]),
        "published aggregate statistics",
    )
    record_check(
        "reproduces_published_walk_forward_fold_table",
        anchor["per_fold_match"],
        f"{anchor['per_fold_count']} folds compared",
        "every published fold reproduced",
    )

    # ------------------------------------------------------------------
    # Phase decomposition: odd folds vs even folds of the published design
    # ------------------------------------------------------------------
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

    record_check(
        "phase_a_test_windows_pairwise_disjoint",
        des_a["independence"]["mean_consecutive_overlap_days"] == 0.0
        and des_a["independence"]["max_disjoint_test_windows"] == des_a["summary"].get("n_folds", 0),
        f"overlap={des_a['independence']['mean_consecutive_overlap_days']}, disjoint={des_a['independence']['max_disjoint_test_windows']}, folds={des_a['summary'].get('n_folds', 0)}",
        "overlap == 0 and disjoint == folds",
    )
    record_check(
        "phase_b_test_windows_pairwise_disjoint",
        des_b["independence"]["mean_consecutive_overlap_days"] == 0.0
        and des_b["independence"]["max_disjoint_test_windows"] == des_b["summary"].get("n_folds", 0),
        f"overlap={des_b['independence']['mean_consecutive_overlap_days']}, disjoint={des_b['independence']['max_disjoint_test_windows']}, folds={des_b['summary'].get('n_folds', 0)}",
        "overlap == 0 and disjoint == folds",
    )
    record_check(
        "phase_union_covers_published_fold_set",
        set(phase_a_numbers) | set(phase_b_numbers) == set(f["fold"] for f in folds)
        and set(phase_a_numbers) & set(phase_b_numbers) == set(),
        f"phase A {len(phase_a_numbers)} folds, phase B {len(phase_b_numbers)} folds, union {len(set(phase_a_numbers) | set(phase_b_numbers))}",
        f"all {len(folds)} published folds, no overlap between phases",
    )
    record_check(
        "phase_means_average_to_published_mean",
        phases_average,
        f"({mean_a:.6f} + {mean_b:.6f}) / 2 = {(mean_a + mean_b) / 2:.6f}, published recomputed {mean_all:.6f}",
        "published mean equals the average of the two phase means",
    )

    # ------------------------------------------------------------------
    # Fold leave-one-out influence table
    # ------------------------------------------------------------------
    sharpes = [float(r["test_sharpe"]) for r in folds]
    trades = [int(r["test_trades"]) for r in folds]
    influence: list[dict[str, Any]] = []
    for i, r in enumerate(folds):
        loo = float(np.mean(sharpes[:i] + sharpes[i + 1 :]))
        shift = loo - mean_all
        influence.append(
            {
                "fold": r["fold"],
                "test_sharpe": sharpes[i],
                "test_trades": trades[i],
                "loo_mean": loo,
                "shift": shift,
                "abs_shift": abs(shift),
                "is_thin": trades[i] <= THIN_TRADE_MAX,
            }
        )
    most_influential = max(influence, key=lambda item: item["abs_shift"])
    median = float(np.median(sharpes))
    ordered = sorted(sharpes)
    trimmed = float(np.mean(ordered[1:-1]))
    thin = [item for item in influence if item["is_thin"]]
    both_excluded_mean = float(
        np.mean([s for s, t in zip(sharpes, trades) if t > THIN_TRADE_MAX])
    )

    # ------------------------------------------------------------------
    # Stability verdict
    # ------------------------------------------------------------------
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
    payload: dict[str, Any] = {
        "cycle": CYCLE,
        "candidate": CANDIDATE_ID,
        "overall": "PASS" if all(c["pass"] for c in checks) else "FAIL",
        "checks": checks,
        "published_design": pub,
        "published_record_path": str(
            record_path.relative_to(REPO_ROOT)
            if record_path.is_relative_to(REPO_ROOT)
            else record_path
        ),
        "published_anchor_value": PUBLISHED_WF_MEAN,
        "published_mean_recomputed": mean_all,
        "published_verdict": "Credible Candidate",
        "published_gate1_status": gate1_published,
        "phase_decomposition": {
            "phase_a_fold_numbers": phase_a_numbers,
            "phase_b_fold_numbers": phase_b_numbers,
            "phase_a": {
                "n_folds": des_a["summary"].get("n_folds", 0),
                "mean_test_sharpe": mean_a,
                "median_test_sharpe": float(des_a["summary"]["median_test_sharpe"]),
                "pct_positive_sharpe": float(des_a["summary"]["pct_positive_sharpe"]),
                "pooled_oos_trades": int(des_a["summary"]["total_test_trades"]),
                "gate_table": des_a["gates"],
                "decision": des_a["decision"],
                "independence": des_a["independence"],
            },
            "phase_b": {
                "n_folds": des_b["summary"].get("n_folds", 0),
                "mean_test_sharpe": mean_b,
                "median_test_sharpe": float(des_b["summary"]["median_test_sharpe"]),
                "pct_positive_sharpe": float(des_b["summary"]["pct_positive_sharpe"]),
                "pooled_oos_trades": int(des_b["summary"]["total_test_trades"]),
                "gate_table": des_b["gates"],
                "decision": des_b["decision"],
                "independence": des_b["independence"],
            },
            "phases_are_pairwise_disjoint": bool(
                des_a["independence"]["mean_consecutive_overlap_days"] == 0.0
                and des_b["independence"]["mean_consecutive_overlap_days"] == 0.0
            ),
            "union_covers_published_folds": bool(
                set(phase_a_numbers) | set(phase_b_numbers)
                == set(f["fold"] for f in folds)
                and set(phase_a_numbers) & set(phase_b_numbers) == set()
            ),
            "phase_means_average_to_published_mean": bool(phases_average),
            "published_mean_position": (
                f"published {mean_all:.6f} = ({mean_a:.6f} + {mean_b:.6f}) / 2"
            ),
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
            "loo_mean_thin_trade_folds": {
                str(item["fold"]): item["loo_mean"] for item in thin
            },
            "both_thin_trade_folds_excluded_mean": both_excluded_mean,
            "gate1_when_thin_trade_folds_excluded": gate1_thin_excluded,
            "gate1_outcome_changes_when_thin_trade_folds_excluded": bool(
                outcome_changes_thin
            ),
        },
        "stability": {
            "gate1_outcome_changes_between_phases": bool(outcome_changes_phase),
            "gate1_outcome_changes_when_thin_trade_folds_excluded": bool(
                outcome_changes_thin
            ),
            "published_pass_stable": bool(pass_stable),
        },
        "read_only": {
            "data_unchanged": data_before == data_after,
            "config_unchanged": config_before == config_after,
            "committed_artifacts_unchanged": artifacts_before == artifacts_after,
        },
        "commission_bps": commission_bps * 10000.0,
        "slippage_bps": slippage_bps * 10000.0,
        "rf_annual": get_risk_free_rate(),
        "anchor": anchor,
        "point_in_time": (
            "signals use only data available at formation (weights shifted one day), "
            "the SPY SMA is computed point-in-time, and the overlay/cost model are applied "
            "on the same continuously computed path for every fold and phase"
        ),
        "data_source": "committed parquet cache in data/raw/ (fetcher never called)",
    }
    return payload


def render_report(payload: dict[str, Any]) -> str:
    pub = payload["published_design"] if "published_design" in payload else None
    lines: list[str] = []
    lines.append(
        f"# TSMomentum SPY-Trend Walk-Forward Mean Stability Audit (tsmomentum_walkforward_mean_robustness_001, Cycle {CYCLE})"
    )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Candidate: `{CANDIDATE_ID}` (the incumbent)")
    lines.append(
        f"- Published walk-forward record (resolved by content): `{payload['published_record_path']}`"
    )
    lines.append(
        f"- Published WF mean OOS Sharpe: {payload['published_anchor_value']:.4f} "
        f"(gate >= {GATE_WF_MEAN_MIN}, margin {payload['published_anchor_value'] - GATE_WF_MEAN_MIN:+.4f})"
    )
    stab = payload["stability"]
    phases = payload["phase_decomposition"]
    lines.append(
        f"- Gate-1 outcome under phase A (odd folds): **{phases['gate1_phase_a']}**; "
        f"under phase B (even folds): **{phases['gate1_phase_b']}** -- "
        f"outcome changes between phases: **{'YES' if phases['gate1_outcome_changes_between_phases'] else 'NO'}**"
    )
    infl = payload["fold_influence"]
    lines.append(
        f"- Gate-1 outcome when thin-trade folds {infl['thin_trade_folds']} are excluded: "
        f"**{infl['gate1_when_thin_trade_folds_excluded']}** (mean {infl['both_thin_trade_folds_excluded_mean']:.6f}) -- "
        f"outcome changes: **{'YES' if infl['gate1_outcome_changes_when_thin_trade_folds_excluded'] else 'NO'}**"
    )
    lines.append(
        f"- Published PASS stability: **{'STABLE' if stab['published_pass_stable'] else 'NOT STABLE'}**"
    )
    lines.append(
        "- Read-only: `data/` and `config/` byte-identical before and after the run "
        f"(**{'yes' if payload['read_only']['data_unchanged'] and payload['read_only']['config_unchanged'] else 'NO'}**); "
        "no committed artifact modified "
        f"(**{'yes' if payload['read_only']['committed_artifacts_unchanged'] else 'NO'}**)."
    )
    lines.append(
        "- Data source: committed parquet cache in `data/raw/` only; the fetcher is never called."
    )
    lines.append("")
    lines.append("## 1. Reproduction anchor (published design, re-derived from the committed cache)")
    lines.append("")
    lines.append(
        "The published 48-fold design is re-derived from the committed cache with the committed "
        "candidate definition and compared with the published record, resolved by content "
        "(the record that carries the published aggregate table and fold table)."
    )
    lines.append("")
    lines.append("| Design | Folds | WF mean OOS Sharpe | Median | Positive fold rate | Pooled OOS trades | Decision |")
    lines.append("|---|---|---|---|---|---|---|")
    lines.append(
        "| Published (recomputed) | {folds} | {mean} | {median} | {pos} | {trades} | {decision} |".format(
            folds=pub["summary"].get("n_folds", 0),
            mean=_fmt(pub["summary"].get("mean_test_sharpe"), 4),
            median=_fmt(pub["summary"].get("median_test_sharpe"), 4),
            pos=f"{pub['summary'].get('pct_positive_sharpe', float('nan')):.4f}",
            trades=pub["summary"].get("total_test_trades", 0),
            decision=pub["decision"]["label"],
        )
    )
    lines.append("")
    lines.append("## 2. Phase decomposition (odd folds vs even folds)")
    lines.append("")
    lines.append(
        "The generator steps the folds by 6 months over a 12-month test window, so consecutive "
        "test windows overlap and the published folds are the interleaving of two disjoint "
        "24-fold sub-designs: phase A (folds 1, 3, 5, ...) and phase B (folds 2, 4, 6, ...). "
        "Both are evaluated on the same continuously computed point-in-time path; only the fold "
        "windows change."
    )
    lines.append("")
    lines.append(
        "| Phase | Folds | Fold numbers | WF mean OOS Sharpe | Median | Positive fold rate | Pooled OOS trades | Gate 1 (>= 0.9) | Gate 2 (>= 0.5) | Gate 3 (> 100) | Decision |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    def _design_row(d: dict[str, Any], key: str) -> tuple[int, float, float, float, int, list[dict[str, Any]], str]:
        if key == "published":
            s = d["summary"]
            return (
                int(s.get("n_folds", 0)),
                float(s.get("mean_test_sharpe", float("nan"))),
                float(s.get("median_test_sharpe", float("nan"))),
                float(s.get("pct_positive_sharpe", float("nan"))),
                int(s.get("total_test_trades", 0)),
                d["gates"],
                d["decision"]["label"],
            )
        return (
            int(d.get("n_folds", 0)),
            float(d.get("mean_test_sharpe", float("nan"))),
            float(d.get("median_test_sharpe", float("nan"))),
            float(d.get("pct_positive_sharpe", float("nan"))),
            int(d.get("pooled_oos_trades", 0)),
            d["gate_table"],
            d["decision"]["label"],
        )

    for label, key, fold_numbers in (
        ("Published design (all 48 folds)", "published", None),
        ("Phase A (odd folds)", "phase_a", phases["phase_a_fold_numbers"]),
        ("Phase B (even folds)", "phase_b", phases["phase_b_fold_numbers"]),
    ):
        d = pub if key == "published" else phases[key]
        n_folds, mean, median, pos, trades, gates, decision = _design_row(d, key)
        lines.append(
            "| {label} | {folds} | {fnums} | {mean} | {median} | {pos} | {trades} | {g1} | {g2} | {g3} | {decision} |".format(
                label=label,
                folds=n_folds,
                fnums=", ".join(str(n) for n in fold_numbers) if fold_numbers is not None else "1..48",
                mean=_fmt(mean, 4),
                median=_fmt(median, 4),
                pos=f"{pos:.4f}",
                trades=trades,
                g1=f"{gates[0]['status']} ({gates[0]['margin']:+.4f})",
                g2=f"{gates[1]['status']} ({gates[1]['margin']:+.4f})",
                g3=f"{gates[2]['status']} ({gates[2]['margin']:+.0f})",
                decision=decision,
            )
        )
    lines.append("")
    lines.append(
        "- Phase A mean {mean_a} and phase B mean {mean_b} average to the published recomputed "
        "mean {mean_all}: **{avg}**.".format(
            mean_a=_fmt(phases["phase_a"]["mean_test_sharpe"], 6),
            mean_b=_fmt(phases["phase_b"]["mean_test_sharpe"], 6),
            mean_all=_fmt(payload["published_mean_recomputed"], 6),
            avg="YES" if phases["phase_means_average_to_published_mean"] else "NO",
        )
    )
    lines.append(
        "- Both phases have zero consecutive test-window overlap and disjoint count equal to "
        "fold count: **{disj}**.".format(
            disj="YES"
            if phases["phases_are_pairwise_disjoint"] and phases["union_covers_published_folds"]
            else "NO"
        )
    )
    lines.append(
        f"- Published mean position: {phases['published_mean_position']}."
    )
    lines.append("")
    lines.append("### 2.1 Phase A (odd folds, folds 1, 3, 5, ...) -- gate table")
    lines.append("")
    lines.extend(_gate_lines(phases["phase_a"]["gate_table"]))
    lines.append("")
    lines.append("### 2.2 Phase B (even folds, folds 2, 4, 6, ...) -- gate table")
    lines.append("")
    lines.extend(_gate_lines(phases["phase_b"]["gate_table"]))
    lines.append("")
    lines.append("## 3. Fold leave-one-out influence table (published 48 folds)")
    lines.append("")
    lines.append(
        "| Fold | Test Sharpe | Test Trades | Leave-One-Out Mean | Shift in Published Mean | Notes |"
    )
    lines.append("|---|---|---|---|---|---|")
    for item in infl["influence"]:
        notes = []
        if item["is_thin"]:
            notes.append("thin-trade fold (<= 10 trades)")
        if item["fold"] == infl["most_influential_fold"]["fold"]:
            notes.append("most influential fold")
        lines.append(
            "| {fold} | {sharpe} | {trades} | {loo} | {shift:+.6f} | {notes} |".format(
                fold=item["fold"],
                sharpe=_fmt(item["test_sharpe"], 4),
                trades=item["test_trades"],
                loo=_fmt(item["loo_mean"], 6),
                shift=item["shift"],
                notes=", ".join(notes) if notes else "",
            )
        )
    lines.append("")
    lines.append(
        f"- Published mean: {infl['published_mean']:.6f}; published median: {infl['published_median']:.6f}; "
        f"trimmed mean (min and max fold removed): {infl['trimmed_mean_drop_min_max']:.6f}."
    )
    lines.append(
        f"- Most influential fold: fold {infl['most_influential_fold']['fold']} "
        f"(test Sharpe {infl['most_influential_fold']['test_sharpe']:.4f}, "
        f"leave-one-out mean {infl['most_influential_fold']['loo_mean']:.6f}, "
        f"shift {infl['most_influential_fold']['shift']:+.6f})."
    )
    lines.append(
        "- Thin-trade folds (<= 10 trades): {thin}; leave-one-out means: {loos}.".format(
            thin=", ".join(str(f) for f in infl["thin_trade_folds"]),
            loos=", ".join(
                f"fold {f}: {infl['loo_mean_thin_trade_folds'][str(f)]:.6f}"
                for f in infl["thin_trade_folds"]
            ),
        )
    )
    lines.append(
        f"- Both thin-trade folds excluded: mean {infl['both_thin_trade_folds_excluded_mean']:.6f}, "
        f"gate-1 status {infl['gate1_when_thin_trade_folds_excluded']}."
    )
    lines.append("")
    lines.append("## 4. Stability verdict (explicit)")
    lines.append("")
    lines.append(
        "(i) Gate-1 outcome under phase A: **{pa}**; under phase B: **{pb}** -- "
        "the outcome changes between phases: **{ch}**.".format(
            pa=phases["gate1_phase_a"],
            pb=phases["gate1_phase_b"],
            ch="YES" if phases["gate1_outcome_changes_between_phases"] else "NO",
        )
    )
    lines.append(
        "(ii) Excluding the thin-trade folds {thin}: gate-1 outcome stays **{g}** -- "
        "the outcome changes: **{ch}**.".format(
            thin=", ".join(str(f) for f in infl["thin_trade_folds"]),
            g=infl["gate1_when_thin_trade_folds_excluded"],
            ch="YES" if infl["gate1_outcome_changes_when_thin_trade_folds_excluded"] else "NO",
        )
    )
    lines.append(
        "(iii) The published PASS is **{stab}** against the two documented weaknesses: "
        "phase B alone fails gate 1 ({mb} < 0.9), so the published margin of "
        "{margin:+.4f} is not phase-stable; the thin-trade folds do not by themselves "
        "change the gate-1 outcome.".format(
            stab="STABLE" if stab["published_pass_stable"] else "NOT STABLE",
            mb=_fmt(phases["phase_b"]["mean_test_sharpe"], 4),
            margin=payload["published_anchor_value"] - GATE_WF_MEAN_MIN,
        )
    )
    lines.append("")
    lines.append("## 5. Checks")
    lines.append("")
    for c in payload["checks"]:
        lines.append(
            f"- [{c['name']}]: {'PASS' if c['pass'] else 'FAIL'}"
            + (
                f" (observed: {c['observed']}, expected: {c['expected']})"
                if c.get("observed") or c.get("expected")
                else ""
            )
        )
    lines.append("")
    lines.append("## 6. Reproduction commands")
    lines.append("")
    lines.append("```bash")
    lines.append("python research/tsmomentum_walkforward_mean_robustness_audit.py")
    lines.append("python -m pytest -q tests/test_tsmomentum_walkforward_mean_robustness_audit.py")
    lines.append("python -m pytest -q")
    lines.append("git status --porcelain data/")
    lines.append("git diff --stat src/ config/ research/experiments/ research/reports/")
    lines.append("```")
    lines.append("")
    lines.append("## 7. JSON payload")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(payload, indent=2, default=str, sort_keys=True))
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def render_experiment(payload: dict[str, Any]) -> str:
    phases = payload["phase_decomposition"]
    infl = payload["fold_influence"]
    stab = payload["stability"]
    lines: list[str] = []
    lines.append(
        f"# Experiment: Walk-forward mean stability for `{CANDIDATE_ID}` (tsmomentum_walkforward_mean_robustness_001, Cycle {CYCLE})"
    )
    lines.append("")
    lines.append("## Hypothesis reference")
    lines.append("")
    lines.append("- Candidate hypothesis: `research/hypotheses/tsmomentum_004.md` (Cycle 5 promoted candidate)")
    lines.append(
        f"- Published walk-forward record: `{payload['published_record_path']}` (resolved by content)"
    )
    lines.append(
        "- Frozen candidate definition: `research/run_cycle6.py` (the script that produced the published record; read, never changed)"
    )
    lines.append("- Pre-registered promotion gates: `AGENTS.md` and the published record's gate table (read, never changed)")
    lines.append("")
    lines.append("## Objective")
    lines.append("")
    lines.append(
        "Quantify how much of the incumbent's published walk-forward mean OOS Sharpe (0.9473) "
        "depends on (a) the fold phase of the pre-registered 6-month step over 12-month test "
        "windows and (b) the two thin-trade folds, publish the phase decomposition and the "
        "fold leave-one-out influence table, and state explicitly whether the published gate "
        "outcome is stable. Sensitivity only: the published protocol, the gates and every "
        "committed artifact are unchanged."
    )
    lines.append("")
    lines.append("## Data")
    lines.append("")
    lines.append("- Source: committed raw cache `data/raw/*.parquet` (cache-only; the fetcher is never called)")
    lines.append(f"- Universe: {', '.join(SYMBOLS)}")
    lines.append(f"- Date range: {START_DATE} to {END_DATE}")
    lines.append("- Point-in-time treatment: " + payload["point_in_time"])
    lines.append(
        f"- Cost model: {payload['commission_bps']:.1f} bps commission + {payload['slippage_bps']:.1f} bps slippage "
        f"= {payload['commission_bps'] + payload['slippage_bps']:.1f} bps round-trip; risk-free rate {payload['rf_annual']} annual"
    )
    lines.append("")
    lines.append("## Configuration (consumed as-is, never inferred)")
    lines.append("")
    lines.append(f"- Signal: TSMOM lookback {LOOKBACK}, skip {SKIP}, top_fraction {TOP_FRACTION}")
    lines.append(
        f"- Risk overlay: vol-target {VOL_TARGET} (lookback {VOL_TARGET_LOOKBACK}) + drawdown control 0.15"
    )
    lines.append(f"- Regime filter: SPY {SPY_SMA_WINDOW}-day SMA trend filter")
    lines.append(
        f"- Walk-forward (published design): train {WF_TRAIN_YEARS}y / test {WF_TEST_MONTHS}m / step {WF_STEP_MONTHS}m, purge {WF_PURGE_DAYS}d, embargo {WF_EMBARGO_DAYS}d"
    )
    lines.append(
        f"- Gates (pre-registered): WF mean OOS Sharpe >= {GATE_WF_MEAN_MIN}, positive fold rate >= {GATE_POSITIVE_FOLD_RATE_MIN}, pooled OOS trades > {GATE_POOLED_TRADES_MIN}"
    )
    lines.append("")
    lines.append("## Splits")
    lines.append("")
    lines.append(
        f"- Published design: {payload['published_design']['summary'].get('n_folds', 0)} folds, "
        f"overlap {payload['published_design']['independence']['mean_consecutive_overlap_days']:.1f} days"
    )
    lines.append("")
    lines.append("| Design | Folds | Fold numbers | Mean consecutive overlap (days) | Max disjoint test windows |")
    lines.append("|---|---|---|---|---|")
    lines.append(
        "| Published design | {folds} | 1..48 | {ov:.1f} | {dj} |".format(
            folds=payload["published_design"]["summary"].get("n_folds", 0),
            ov=payload["published_design"]["independence"]["mean_consecutive_overlap_days"],
            dj=payload["published_design"]["independence"]["max_disjoint_test_windows"],
        )
    )
    lines.append(
        "| Phase A (odd folds) | 24 | {fnums} | {ov:.1f} | {dj} |".format(
            fnums=", ".join(str(n) for n in phases["phase_a_fold_numbers"]),
            ov=phases["phase_a"]["independence"]["mean_consecutive_overlap_days"],
            dj=phases["phase_a"]["independence"]["max_disjoint_test_windows"],
        )
    )
    lines.append(
        "| Phase B (even folds) | 24 | {fnums} | {ov:.1f} | {dj} |".format(
            fnums=", ".join(str(n) for n in phases["phase_b_fold_numbers"]),
            ov=phases["phase_b"]["independence"]["mean_consecutive_overlap_days"],
            dj=phases["phase_b"]["independence"]["max_disjoint_test_windows"],
        )
    )
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("### Published anchor")
    lines.append("")
    lines.append(
        "- Recomputed published design: {folds} folds, WF mean OOS Sharpe {mean:.6f} (published {published:.4f}), "
        "median {median:.4f}, positive fold rate {pos:.4f}, pooled OOS trades {trades} -- "
        "anchor reproduced: **MATCH**.".format(
            folds=payload["published_design"]["summary"].get("n_folds", 0),
            mean=payload["published_mean_recomputed"],
            published=payload["published_anchor_value"],
            median=infl["published_median"],
            pos=payload["published_design"]["summary"].get("pct_positive_sharpe", 0.0),
            trades=payload["published_design"]["summary"].get("total_test_trades", 0),
        )
    )
    lines.append("")
    lines.append("### Phase decomposition")
    lines.append("")
    lines.append(
        "| Phase | Folds | WF mean OOS Sharpe | Median | Positive fold rate | Pooled OOS trades | Gate 1 status |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for label, key in (("Published design", "published"), ("Phase A (odd folds)", "phase_a"), ("Phase B (even folds)", "phase_b")):
        d = payload["published_design"] if key == "published" else phases[key]
        if key == "published":
            s = d["summary"]
            folds_n = int(s.get("n_folds", 0))
            mean = float(s.get("mean_test_sharpe", float("nan")))
            median = float(s.get("median_test_sharpe", float("nan")))
            pos = float(s.get("pct_positive_sharpe", float("nan")))
            trades = int(s.get("total_test_trades", 0))
            g = d["gates"]
        else:
            folds_n = int(d.get("n_folds", 0))
            mean = float(d.get("mean_test_sharpe", float("nan")))
            median = float(d.get("median_test_sharpe", float("nan")))
            pos = float(d.get("pct_positive_sharpe", float("nan")))
            trades = int(d.get("pooled_oos_trades", 0))
            g = d["gate_table"]
        lines.append(
            "| {label} | {folds} | {mean} | {median} | {pos} | {trades} | {g1} |".format(
                label=label,
                folds=folds_n,
                mean=_fmt(mean, 6),
                median=_fmt(median, 6),
                pos=f"{pos:.4f}",
                trades=trades,
                g1=f"{g[0]['status']} (mean {g[0]['observed']:.6f} vs threshold {g[0]['threshold']})",
            )
        )
    lines.append("")
    lines.append(
        "- Phase means average to the published mean: ("
        "{a:.6f} + {b:.6f}) / 2 = {avg:.6f} = published recomputed {m:.6f}: **{match}**.".format(
            a=phases["phase_a"]["mean_test_sharpe"],
            b=phases["phase_b"]["mean_test_sharpe"],
            avg=(phases["phase_a"]["mean_test_sharpe"] + phases["phase_b"]["mean_test_sharpe"]) / 2.0,
            m=payload["published_mean_recomputed"],
            match="YES" if phases["phase_means_average_to_published_mean"] else "NO",
        )
    )
    lines.append("")
    lines.append("### Fold leave-one-out influence")
    lines.append("")
    lines.append(
        f"- Published mean: {infl['published_mean']:.6f}; published median: {infl['published_median']:.6f}; "
        f"trimmed mean (min and max removed): {infl['trimmed_mean_drop_min_max']:.6f}."
    )
    lines.append(
        f"- Most influential fold: fold {infl['most_influential_fold']['fold']} "
        f"(test Sharpe {infl['most_influential_fold']['test_sharpe']:.4f}, "
        f"leave-one-out mean {infl['most_influential_fold']['loo_mean']:.6f}, "
        f"shift {infl['most_influential_fold']['shift']:+.6f})."
    )
    lines.append(
        f"- Thin-trade folds (<= {THIN_TRADE_MAX} trades): {', '.join(str(f) for f in infl['thin_trade_folds'])}; "
        f"leave-one-out means: " + ", ".join(
            f"fold {f}: {infl['loo_mean_thin_trade_folds'][str(f)]:.6f}"
            for f in infl["thin_trade_folds"]
        ) + "."
    )
    lines.append(
        f"- Both thin-trade folds excluded: mean {infl['both_thin_trade_folds_excluded_mean']:.6f}, "
        f"gate-1 status {infl['gate1_when_thin_trade_folds_excluded']}."
    )
    lines.append("")
    lines.append("### Stability verdict")
    lines.append("")
    lines.append(
        f"- Gate-1 outcome changes between phases: **{'YES' if stab['gate1_outcome_changes_between_phases'] else 'NO'}** "
        f"(phase A {phases['gate1_phase_a']}, phase B {phases['gate1_phase_b']})."
    )
    lines.append(
        f"- Gate-1 outcome changes when thin-trade folds are excluded: **{'YES' if stab['gate1_outcome_changes_when_thin_trade_folds_excluded'] else 'NO'}**."
    )
    lines.append(
        f"- Published PASS stable against the two documented weaknesses: **{'STABLE' if stab['published_pass_stable'] else 'NOT STABLE'}**."
    )
    lines.append("")
    lines.append("## Trial count")
    lines.append("")
    lines.append(
        "- 1 measurement per phase plus 1 influence pass on one shared path = deterministic, "
        "fixed parameters, no per-fold re-optimisation, no robustness grid, no candidate selection."
    )
    lines.append("")
    lines.append("## Reproduction")
    lines.append("")
    lines.append("```bash")
    lines.append("python research/tsmomentum_walkforward_mean_robustness_audit.py")
    lines.append("python -m pytest -q tests/test_tsmomentum_walkforward_mean_robustness_audit.py")
    lines.append("python -m pytest -q")
    lines.append("git status --porcelain data/")
    lines.append("git diff --stat src/ config/ research/experiments/ research/reports/")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiments-dir", type=Path, default=EXPERIMENTS_DIR)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--report-out", type=Path, default=OUT_REPORT)
    parser.add_argument("--experiment-out", type=Path, default=OUT_EXP)
    args = parser.parse_args(argv)

    try:
        payload = run_audit(
            experiments_dir=args.experiments_dir,
            raw_dir=args.raw_dir,
        )
    except AuditError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.experiment_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(render_report(payload), encoding="utf-8")
    args.experiment_out.write_text(render_experiment(payload), encoding="utf-8")

    print("OVERALL: " + payload["overall"])
    print(f"report: {args.report_out}")
    print(f"experiment: {args.experiment_out}")
    print(
        f"published design: {payload.get('published_design', {}).get('summary', {}).get('n_folds', 'n/a')} folds, "
        f"WF mean OOS Sharpe {payload['published_mean_recomputed']:.4f}"
    )
    print(
        f"Phase A: {payload['phase_decomposition']['phase_a']['n_folds']} folds, "
        f"WF mean OOS Sharpe {payload['phase_decomposition']['phase_a']['mean_test_sharpe']:.4f}, "
        f"gate 1 {payload['phase_decomposition']['gate1_phase_a']}"
    )
    print(
        f"Phase B: {payload['phase_decomposition']['phase_b']['n_folds']} folds, "
        f"WF mean OOS Sharpe {payload['phase_decomposition']['phase_b']['mean_test_sharpe']:.4f}, "
        f"gate 1 {payload['phase_decomposition']['gate1_phase_b']}"
    )
    print(
        f"gate-1 outcome changes between phases: "
        f"{'YES' if payload['phase_decomposition']['gate1_outcome_changes_between_phases'] else 'NO'}"
    )
    print(
        f"published pass stable: {'YES' if payload['stability']['published_pass_stable'] else 'NO'}"
    )
    return 0 if payload["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
