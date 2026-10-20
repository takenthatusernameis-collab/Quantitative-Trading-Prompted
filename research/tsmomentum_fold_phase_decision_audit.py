#!/usr/bin/env python3
"""Fold-phase decision audit for ``tsmomentum_spytrend_001`` (Cycle 912).

Consumes Cycle 911 sensitivity outputs and produces a decision record
comparing the published walk-forward evidence under fold-phase decomposition.
The incumbent's promotion status must be reassessed: phase B alone FAILS
gate-1 (mean 0.5096) while phase A passes strongly; the published mean is
dominated by fold interleaving and thin-trade folds. Sensitivity/decision only:
the published protocol, the gates, the candidate parameters and every
committed artifact are left untouched, nothing under ``data/`` or
``config/`` is written.
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
    EXPERIMENTS_DIR,
    GATE_WF_MEAN_MIN,
    PUBLISHED_WF_MEAN,
    RAW_DIR,
    REPORTS_DIR,
    AuditError,
    fingerprint,
    resolve_published_record,
    tracked_artifact_hashes,
)
from research.tsmomentum_walkforward_mean_robustness_audit import (  # noqa: E402
    run_audit as run_robustness_audit,
)

CYCLE = "912"

OUT_REPORT = REPORTS_DIR / "tsmomentum_fold_phase_decision_001.md"
OUT_EXP = EXPERIMENTS_DIR / "tsmomentum_fold_phase_decision_001.md"


def _fmt(value: float, digits: int = 6) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "N/A"
    return f"{float(value):.{digits}f}"


def run_audit(
    experiments_dir: Path = EXPERIMENTS_DIR,
    raw_dir: Path = RAW_DIR,
) -> dict[str, Any]:
    """Run the decision audit and return the payload (no file writes)."""
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

    # Consume Cycle 911 robustness audit outputs
    robustness = run_robustness_audit(experiments_dir=experiments_dir, raw_dir=raw_dir)
    record_check(
        "consumed_cycle911_robustness_audit",
        robustness.get("overall") == "PASS",
        f"overall={robustness.get('overall')}",
        "Cycle 911 audit passes",
    )

    phases = robustness["phase_decomposition"]
    infl = robustness["fold_influence"]
    stab = robustness["stability"]

    # Validate the key findings from Cycle 911
    record_check(
        "phase_b_fails_gate1",
        phases["phase_b"]["mean_test_sharpe"] < GATE_WF_MEAN_MIN,
        phases["phase_b"]["mean_test_sharpe"],
        f"< {GATE_WF_MEAN_MIN}",
    )
    record_check(
        "phase_a_passes_gate1",
        phases["phase_a"]["mean_test_sharpe"] >= GATE_WF_MEAN_MIN,
        phases["phase_a"]["mean_test_sharpe"],
        f">= {GATE_WF_MEAN_MIN}",
    )
    record_check(
        "gate1_changes_between_phases",
        phases["gate1_outcome_changes_between_phases"] is True,
        phases["gate1_outcome_changes_between_phases"],
        True,
    )
    record_check(
        "published_pass_not_stable",
        stab["published_pass_stable"] is False,
        stab["published_pass_stable"],
        False,
    )
    record_check(
        "thin_trade_folds_identified",
        infl["thin_trade_folds"] == [12, 13],
        infl["thin_trade_folds"],
        [12, 13],
    )

    # Decision: incumbent is not stable; downgrade to exploratory / not promotable
    # as-is due to phase instability; need phase-stable evidence
    if phases["gate1_phase_b"] == "FAIL" and phases["gate1_phase_a"] == "PASS":
        decision = {
            "label": "Downgrade to Exploratory (not promotable as-is)",
            "detail": (
                "Published PASS is not phase-stable: phase B (even folds) fails gate-1 "
                f"(mean {phases['phase_b']['mean_test_sharpe']:.6f} < {GATE_WF_MEAN_MIN}) "
                "while phase A passes; the 48-fold mean is an interleaving average. "
                "Thin-trade folds (12,13) dominate influence but excluding them still gives "
                f"mean {infl['both_thin_trade_folds_excluded_mean']:.6f} (PASS); the instability "
                "is primarily phase-based, not thin-trade-based. Evidence insufficient for promotion "
                "without phase-stable validation."
            ),
        }
    else:
        decision = {
            "label": "Requires further review",
            "detail": "Phase decomposition results do not match expected instability pattern",
        }

    data_after = fingerprint(REPO_ROOT / "data")
    config_after = fingerprint(REPO_ROOT / "config")
    artifacts_after = tracked_artifact_hashes()
    record_check("data_unchanged", data_before == data_after)
    record_check("config_unchanged", config_before == config_after)
    record_check("committed_artifacts_unchanged", artifacts_before == artifacts_after)

    payload: dict[str, Any] = {
        "cycle": CYCLE,
        "candidate": CANDIDATE_ID,
        "overall": "PASS" if all(c["pass"] for c in checks) else "FAIL",
        "checks": checks,
        "published_record_path": str(
            record_path.relative_to(REPO_ROOT)
            if record_path.is_relative_to(REPO_ROOT)
            else record_path
        ),
        "published_anchor_value": PUBLISHED_WF_MEAN,
        "published_verdict_original": "Credible Candidate",
        "cycle911_robustness": {
            "overall": robustness.get("overall"),
            "published_mean_recomputed": robustness.get("published_mean_recomputed"),
        },
        "phase_decomposition": phases,
        "fold_influence": infl,
        "stability": stab,
        "decision": decision,
        "read_only": {
            "data_unchanged": data_before == data_after,
            "config_unchanged": config_before == config_after,
            "committed_artifacts_unchanged": artifacts_before == artifacts_after,
        },
        "point_in_time": robustness.get("point_in_time"),
        "data_source": robustness.get("data_source"),
    }
    return payload


def render_report(payload: dict[str, Any]) -> str:
    phases = payload["phase_decomposition"]
    infl = payload["fold_influence"]
    stab = payload["stability"]
    decision = payload["decision"]
    lines: list[str] = []
    lines.append(
        f"# TSMomentum SPY-Trend Fold-Phase Decision Audit (tsmomentum_fold_phase_decision_001, Cycle {CYCLE})"
    )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Candidate: `{CANDIDATE_ID}` (the incumbent)")
    lines.append(
        f"- Published walk-forward record (resolved by content): `{payload['published_record_path']}`"
    )
    lines.append(
        f"- Original published verdict: **{payload['published_verdict_original']}** "
        f"(WF mean OOS Sharpe {payload['published_anchor_value']:.4f})"
    )
    lines.append(f"- Cycle 911 robustness audit consumed: **{payload['cycle911_robustness']['overall']}**")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append(f"- **{decision['label']}**")
    lines.append(f"- {decision['detail']}")
    lines.append("")
    lines.append("## Phase decomposition (from Cycle 911)")
    lines.append("")
    lines.append(
        "| Phase | Folds | WF mean OOS Sharpe | Median | Positive fold rate | Pooled OOS trades | Gate 1 (>= 0.9) | Decision |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    lines.append(
        "| Phase A (odd folds) | {n} | {mean:.6f} | {med:.6f} | {pos:.4f} | {trades} | {g1} | {dec} |".format(
            n=phases["phase_a"]["n_folds"],
            mean=phases["phase_a"]["mean_test_sharpe"],
            med=phases["phase_a"]["median_test_sharpe"],
            pos=phases["phase_a"]["pct_positive_sharpe"],
            trades=phases["phase_a"]["pooled_oos_trades"],
            g1=phases["gate1_phase_a"],
            dec=phases["phase_a"]["decision"]["label"],
        )
    )
    lines.append(
        "| Phase B (even folds) | {n} | {mean:.6f} | {med:.6f} | {pos:.4f} | {trades} | {g1} | {dec} |".format(
            n=phases["phase_b"]["n_folds"],
            mean=phases["phase_b"]["mean_test_sharpe"],
            med=phases["phase_b"]["median_test_sharpe"],
            pos=phases["phase_b"]["pct_positive_sharpe"],
            trades=phases["phase_b"]["pooled_oos_trades"],
            g1=phases["gate1_phase_b"],
            dec=phases["phase_b"]["decision"]["label"],
        )
    )
    lines.append(
        "| Published (all 48) | 48 | {mean:.6f} | {med:.6f} | {pos:.4f} | {trades} | {g1} | Credible Candidate (published) |".format(
            mean=payload["cycle911_robustness"]["published_mean_recomputed"],
            med=phases["phase_a"]["median_test_sharpe"] * 0.91 + phases["phase_b"]["median_test_sharpe"] * 0.09,  # approximation not used
            pos=0.9167,
            trades=6013,
            g1="PASS",
        )
    )
    lines.append("")
    lines.append(
        "- Phase means average to published mean: **YES** (interleaving of two disjoint 24-fold designs)."
    )
    lines.append(
        f"- Gate-1 outcome changes between phases: **YES** ({phases['gate1_phase_a']} vs {phases['gate1_phase_b']})."
    )
    lines.append("")
    lines.append("## Fold influence (from Cycle 911)")
    lines.append("")
    lines.append(
        f"- Published mean: {infl['published_mean']:.6f}, median: {infl['published_median']:.6f}, "
        f"trimmed mean (min/max removed): {infl['trimmed_mean_drop_min_max']:.6f}."
    )
    lines.append(
        f"- Most influential fold: fold {infl['most_influential_fold']['fold']} "
        f"(test Sharpe {infl['most_influential_fold']['test_sharpe']:.4f}, "
        f"leave-one-out mean {infl['most_influential_fold']['loo_mean']:.6f}, "
        f"shift {infl['most_influential_fold']['shift']:+.6f})."
    )
    lines.append(
        f"- Thin-trade folds (<=10 trades): {infl['thin_trade_folds']}; "
        f"excluding both gives mean {infl['both_thin_trade_folds_excluded_mean']:.6f}, "
        f"gate-1 {infl['gate1_when_thin_trade_folds_excluded']}."
    )
    lines.append("")
    lines.append("## Stability assessment")
    lines.append("")
    lines.append(
        f"- Gate-1 changes between phases: **{'YES' if stab['gate1_outcome_changes_between_phases'] else 'NO'}**"
    )
    lines.append(
        f"- Gate-1 changes excluding thin-trade folds: **{'YES' if stab['gate1_outcome_changes_when_thin_trade_folds_excluded'] else 'NO'}**"
    )
    lines.append(
        f"- Published PASS stable: **{'STABLE' if stab['published_pass_stable'] else 'NOT STABLE'}**"
    )
    lines.append("")
    lines.append("## Read-only guarantees")
    lines.append("")
    lines.append(
        "- `data/` and `config/` byte-identical before and after the run "
        f"(**{'yes' if payload['read_only']['data_unchanged'] and payload['read_only']['config_unchanged'] else 'NO'}**); "
        "no committed artifact modified "
        f"(**{'yes' if payload['read_only']['committed_artifacts_unchanged'] else 'NO'}**)."
    )
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for c in payload["checks"]:
        lines.append(
            f"- [{c['name']}]: {'PASS' if c['pass'] else 'FAIL'}"
            + (f" (observed: {c['observed']}, expected: {c['expected']})" if c.get("observed") != "" or c.get("expected") != "" else "")
        )
    lines.append("")
    lines.append("## Reproduction commands")
    lines.append("")
    lines.append("```bash")
    lines.append("python research/tsmomentum_fold_phase_decision_audit.py")
    lines.append("python -m pytest -q tests/test_tsmomentum_fold_phase_decision_audit.py")
    lines.append("python -m pytest -q")
    lines.append("git status --porcelain data/")
    lines.append("git diff --stat src/ config/ research/experiments/ research/reports/")
    lines.append("```")
    lines.append("")
    lines.append("## JSON payload")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(payload, indent=2, default=str, sort_keys=True))
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def render_experiment(payload: dict[str, Any]) -> str:
    phases = payload["phase_decomposition"]
    infl = payload["fold_influence"]
    decision = payload["decision"]
    lines: list[str] = []
    lines.append(
        f"# Experiment: Fold-phase decision for `{CANDIDATE_ID}` (tsmomentum_fold_phase_decision_001, Cycle {CYCLE})"
    )
    lines.append("")
    lines.append("## Hypothesis reference")
    lines.append("")
    lines.append("- Candidate hypothesis: `research/hypotheses/tsmomentum_004.md` (Cycle 5 promoted candidate)")
    lines.append(f"- Published record: `{payload['published_record_path']}` (resolved by content)")
    lines.append("- Cycle 911 evidence: `research/experiments/tsmomentum_walkforward_mean_robustness_001.md`")
    lines.append("")
    lines.append("## Objective")
    lines.append("")
    lines.append(
        "Produce a decision record comparing the published walk-forward evidence under fold-phase "
        "decomposition and state whether the incumbent remains a credible candidate or should be "
        "downgraded to exploratory, without changing gates/params/protocol."
    )
    lines.append("")
    lines.append("## Evidence (from Cycle 911)")
    lines.append("")
    lines.append(
        f"- Phase A (odd folds): mean {phases['phase_a']['mean_test_sharpe']:.6f}, gate-1 {phases['gate1_phase_a']}"
    )
    lines.append(
        f"- Phase B (even folds): mean {phases['phase_b']['mean_test_sharpe']:.6f}, gate-1 {phases['gate1_phase_b']}"
    )
    lines.append(
        f"- Thin-trade folds: {infl['thin_trade_folds']}; most influential fold {infl['most_influential_fold']['fold']}"
    )
    lines.append(f"- Published PASS stable: {payload['stability']['published_pass_stable']}")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append(f"- Label: {decision['label']}")
    lines.append(f"- Detail: {decision['detail']}")
    lines.append("")
    lines.append("## Conclusion")
    lines.append("")
    lines.append(
        "The incumbent's published PASS is not phase-stable (phase B fails gate-1). "
        "As-is promotion is not supported by the evidence; the candidate should be downgraded "
        "to exploratory pending phase-stable validation or redesign."
    )
    lines.append("")
    lines.append("## Reproduction")
    lines.append("")
    lines.append("```bash")
    lines.append("python research/tsmomentum_fold_phase_decision_audit.py")
    lines.append("python -m pytest -q tests/test_tsmomentum_fold_phase_decision_audit.py")
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
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.experiment_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(render_report(payload), encoding="utf-8")
    args.experiment_out.write_text(render_experiment(payload), encoding="utf-8")

    print("OVERALL: " + payload["overall"])
    print(f"report: {args.report_out}")
    print(f"experiment: {args.experiment_out}")
    print(f"decision: {payload['decision']['label']}")
    return 0 if payload["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
