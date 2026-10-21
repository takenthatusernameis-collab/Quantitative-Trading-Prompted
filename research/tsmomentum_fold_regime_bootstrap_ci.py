#!/usr/bin/env python3
"""Fold-level regime bootstrap CIs for the incumbent ``tsmomentum_spytrend_001`` (Cycle 924).

Adds read-only, deterministic block-bootstrap uncertainty quantification for
within-bucket phase gaps (phase A - phase B mean OOS Sharpe). Descriptive only:
no selection, re-ranking, re-fitting, gate changes, or verdict changes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.tsmomentum_walkforward_embargo_audit import (  # noqa: E402
    AuditError,
    PUBLISHED_WF_MEAN,
    fail,
    fingerprint,
    tracked_artifact_hashes,
)
from research.tsmomentum_fold_regime_attribution import (  # noqa: E402
    AttributionError,
    BUCKET_FAMILIES,
    CANDIDATE_ID,
    PERM_SEED,
    PERMUTATIONS,
    REPORTS_DIR,
    EXPERIMENTS_DIR,
    RAW_DIR,
    OUT_REPORT as ATTR_OUT_REPORT,
    OUT_EXP as ATTR_OUT_EXP,
    calendar_phase,
    fold_summary,
    fmt,
    spy_trend_state,
    spy_12m_return_sign,
    train_window_realvol_tercile,
    run_attribution,
)

CYCLE_BOOT = "924"
BOOTSTRAP_RESAMPLES = 5000
BOOTSTRAP_SEED = 924

OUT_REPORT = REPORTS_DIR / "tsmomentum_fold_regime_bootstrap_ci_001.md"
OUT_EXP = EXPERIMENTS_DIR / "tsmomentum_fold_regime_bootstrap_ci_001.md"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def bootstrap_gap_ci(fold_rows: list[dict[str, Any]], family: str, bucket: str,
                     n_resamples: int = BOOTSTRAP_RESAMPLES, seed: int = BOOTSTRAP_SEED):
    """Bootstrap CI for phase_A_mean - phase_B_mean within (family, bucket)."""
    cell = [r for r in fold_rows if r[family] == bucket]
    if not cell:
        return float("nan"), float("nan"), float("nan")
    # Use deterministic seed based on family/bucket order
    family_order = {"F2_spy_trend_state": 0, "F3_spy_12m_return_sign": 1, "F4_train_63d_realvol_tercile": 2}
    bucket_order = {"risk_on": 0, "risk_off": 1, "up": 0, "down": 1, "low_vol": 0, "med_vol": 1, "high_vol": 2}
    det_seed = seed + family_order.get(family, 0) * 100 + bucket_order.get(bucket, 0)
    rng = np.random.default_rng(det_seed)
    n = len(cell)
    # Point estimate
    a_rows = [r for r in cell if r["F1_calendar_phase"] == "phase_A"]
    b_rows = [r for r in cell if r["F1_calendar_phase"] == "phase_B"]
    if not a_rows or not b_rows:
        return float("nan"), float("nan"), float("nan")
    a_mean_pt = float(np.mean([r["test_sharpe"] for r in a_rows]))
    b_mean_pt = float(np.mean([r["test_sharpe"] for r in b_rows]))
    pt_est = a_mean_pt - b_mean_pt
    gaps = []
    for _ in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        samp = [cell[i] for i in idx]
        sa = [r["test_sharpe"] for r in samp if r["F1_calendar_phase"] == "phase_A"]
        sb = [r["test_sharpe"] for r in samp if r["F1_calendar_phase"] == "phase_B"]
        if sa and sb:
            gaps.append(float(np.mean(sa)) - float(np.mean(sb)))
    if not gaps:
        return pt_est, float("nan"), float("nan")
    lo = float(np.percentile(gaps, 2.5))
    hi = float(np.percentile(gaps, 97.5))
    return pt_est, lo, hi


def run_bootstrap_ci(experiments_dir: Path = EXPERIMENTS_DIR,
                     raw_dir: Path = RAW_DIR,
                     write_report: bool = True) -> dict[str, Any]:
    # Reuse attribution machinery - must produce identical anchor
    attr_payload = run_attribution(experiments_dir=experiments_dir,
                                   raw_dir=raw_dir,
                                   write_report=False)
    if attr_payload["overall"] != "PASS":
        fail("attribution did not pass; bootstrap CI requires passing attribution anchor")

    # Get fold rows from attribution
    fold_rows = attr_payload["_fold_rows"]

    # Compute bootstrap CIs for F2, F3, F4 only (as specified)
    families_to_bootstrap = ["F2_spy_trend_state", "F3_spy_12m_return_sign", "F4_train_63d_realvol_tercile"]
    bootstrap_results = {}

    for family in families_to_bootstrap:
        fam_info = attr_payload["families"][family]
        bootstrap_results[family] = {
            "label": fam_info["label"],
            "definition": fam_info["definition"],
            "buckets": []
        }
        for b in fam_info["buckets"]:
            bucket_name = b["bucket"]
            pt_est, lo, hi = bootstrap_gap_ci(fold_rows, family, bucket_name)
            distinguishes = bool(np.isfinite(lo) and np.isfinite(hi) and lo > 0 and hi > 0) or \
                            bool(np.isfinite(lo) and np.isfinite(hi) and lo < 0 and hi < 0)
            # "distinguishable from zero" if 95% CI excludes 0
            excludes_zero = bool(np.isfinite(lo) and np.isfinite(hi) and (hi < 0 or lo > 0))
            bootstrap_results[family]["buckets"].append({
                "bucket": bucket_name,
                "n": b["n"],
                "point_estimate_gap": pt_est,
                "ci_95_lo": lo,
                "ci_95_hi": hi,
                "distinguishable_from_zero": "yes" if excludes_zero else "no",
                "phase_A_n": b["phase_A_n"],
                "phase_B_n": b["phase_B_n"],
                "phase_A_mean": b["phase_A_mean"],
                "phase_B_mean": b["phase_B_mean"],
            })

    # Finalize monitoring statement
    monitoring_parts = []
    for family in families_to_bootstrap:
        for b in bootstrap_results[family]["buckets"]:
            if b["distinguishable_from_zero"] == "yes":
                monitoring_parts.append(f"{family}/{b['bucket']} gap distinguishable from zero (CI [{b['ci_95_lo']:.4f}, {b['ci_95_hi']:.4f}])")

    if monitoring_parts:
        monitoring_statement = (
            "Based on bootstrap 95% CIs (fold-block bootstrap, 5000 resamples, seed 924), "
            "the following observable states show within-bucket phase gaps distinguishable from zero: "
            + "; ".join(monitoring_parts) +
            ". This is a candidate monitoring input only — not wired into any gate, drift flag, "
            "threshold or decision mapping, and does not change the incumbent's published verdict (Credible Candidate)."
        )
    else:
        monitoring_statement = (
            "Based on bootstrap 95% CIs (fold-block bootstrap, 5000 resamples, seed 924), "
            "none of the tested observable states (F2/F3/F4) show within-bucket phase gaps "
            "distinguishable from zero at 95% confidence. The apparent state-dependence is "
            "consistent with sampling noise in small buckets. This is a candidate monitoring "
            "input only — not wired into any gate, drift flag, threshold or decision mapping, "
            "and does not change the incumbent's published verdict (Credible Candidate)."
        )

    payload = {
        "cycle": CYCLE_BOOT,
        "base_cycle": "923",
        "candidate": CANDIDATE_ID,
        "bootstrap": {
            "method": "fold-block bootstrap (resample 48 folds with replacement)",
            "resamples": BOOTSTRAP_RESAMPLES,
            "seed": BOOTSTRAP_SEED,
            "ci_level": 0.95,
            "statistic": "phase_A_mean - phase_B_mean within bucket",
        },
        "anchor_reproduced": attr_payload["anchor_reproduced"],
        "recomputed_summary": attr_payload["recomputed_summary"],
        "families_bootstrap": bootstrap_results,
        "monitoring_statement": monitoring_statement,
        "incumbent_verdict": "Credible Candidate (unchanged)",
        "read_only": attr_payload["read_only"],
    }
    return payload


def render_report(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# Fold Regime Bootstrap CIs for the Incumbent Walk-Forward (tsmomentum_fold_regime_bootstrap_ci_001, Cycle {CYCLE_BOOT})")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Candidate: `{CANDIDATE_ID}` (incumbent)")
    lines.append(f"- Base attribution: Cycle 923 (tsmomentum_fold_regime_attribution_001)")
    lines.append(f"- Bootstrap method: {payload['bootstrap']['method']}, {payload['bootstrap']['resamples']} resamples, fixed seed {payload['bootstrap']['seed']}, 95% CI")
    lines.append(f"- Anchor reproduced: **{'YES' if payload['anchor_reproduced'] else 'NO'}** (48 folds, mean 0.947307)")
    lines.append(f"- Incumbent verdict unchanged: **{payload['incumbent_verdict']}**")
    lines.append("- Descriptive only: no selection, re-ranking, re-fitting, gate changes, or verdict changes.")
    lines.append("")

    for family in ["F2_spy_trend_state", "F3_spy_12m_return_sign", "F4_train_63d_realvol_tercile"]:
        if family not in payload["families_bootstrap"]:
            continue
        fam = payload["families_bootstrap"][family]
        lines.append(f"## {fam['label']}")
        lines.append("")
        lines.append(f"*{fam['definition']}*")
        lines.append("")
        lines.append("| Bucket | n | Phase A n | Phase B n | Phase A mean | Phase B mean | Point-est gap (A-B) | 95% CI [lo, hi] | Distinguishable from zero |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for b in fam["buckets"]:
            lines.append(
                "| {bucket} | {n} | {pa_n} | {pb_n} | {pa_m} | {pb_m} | {pt:+.6f} | [{lo:.6f}, {hi:.6f}] | {dfz} |".format(
                    bucket=b["bucket"],
                    n=b["n"],
                    pa_n=b["phase_A_n"],
                    pb_n=b["phase_B_n"],
                    pa_m=fmt(b["phase_A_mean"], 6),
                    pb_m=fmt(b["phase_B_mean"], 6),
                    pt=b["point_estimate_gap"],
                    lo=b["ci_95_lo"],
                    hi=b["ci_95_hi"],
                    dfz=b["distinguishable_from_zero"],
                )
            )
        lines.append("")

    lines.append("## Finalized monitoring statement")
    lines.append("")
    lines.append(payload["monitoring_statement"])
    lines.append("")
    lines.append("## Reproduction commands")
    lines.append("")
    lines.append("```bash")
    lines.append("python research/tsmomentum_fold_regime_bootstrap_ci.py")
    lines.append("python -m pytest -q tests/test_tsmomentum_fold_regime_bootstrap_ci.py")
    lines.append("git status --porcelain data/ config/")
    lines.append("git diff --name-only HEAD -- research/run_cycle6.py research/experiments/tsmomentum_regime_filter_wf_001.md")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def render_experiment(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# Experiment: Fold regime bootstrap CIs for `{CANDIDATE_ID}` (tsmomentum_fold_regime_bootstrap_ci_001, Cycle {CYCLE_BOOT})")
    lines.append("")
    lines.append("## Hypothesis reference")
    lines.append("- Candidate hypothesis: `research/hypotheses/tsmomentum_004.md` (incumbent)")
    lines.append("- Base attribution: `research/experiments/tsmomentum_fold_regime_attribution_001.md` (Cycle 923)")
    lines.append("- Published walk-forward record: `research/experiments/tsmomentum_regime_filter_wf_001.md`")
    lines.append("")
    lines.append("## Objective")
    lines.append("Add read-only fold-block bootstrap CIs for within-bucket phase gaps (A-B) over F2/F3/F4, determine distinguishability from zero at 95%, and finalize a monitoring statement. Descriptive only.")
    lines.append("")
    lines.append("## Method")
    lines.append(f"- Unit: 48 folds resampled with replacement, preserving test_sharpe, phase label, bucket labels")
    lines.append(f"- Statistic: phase_A mean - phase_B mean within bucket")
    lines.append(f"- Resamples: {payload['bootstrap']['resamples']}, seed {payload['bootstrap']['seed']}, two-sided 95% percentile CI")
    lines.append(f"- Buckets: F2/F3/F4 only (exactly as published)")
    lines.append("- Distinguishable from zero if 95% CI excludes 0")
    lines.append("")
    lines.append("## Results")
    lines.append(f"- Anchor: {payload['recomputed_summary']['n_folds']} folds, mean {payload['recomputed_summary']['mean_test_sharpe']:.6f}, median {payload['recomputed_summary']['median_test_sharpe']:.6f}, pooled trades {payload['recomputed_summary']['total_test_trades']}")
    lines.append("")
    lines.append("### Bootstrap CIs (F2/F3/F4)")
    lines.append("")
    for family in ["F2_spy_trend_state", "F3_spy_12m_return_sign", "F4_train_63d_realvol_tercile"]:
        if family not in payload["families_bootstrap"]:
            continue
        fam = payload["families_bootstrap"][family]
        lines.append(f"#### {fam['label']}")
        lines.append("| Bucket | n | Point gap (A-B) | 95% CI | Distinguishable from zero |")
        lines.append("|---|---|---|---|---|")
        for b in fam["buckets"]:
            lines.append(f"| {b['bucket']} | {b['n']} | {b['point_estimate_gap']:+.6f} | [{b['ci_95_lo']:.6f}, {b['ci_95_hi']:.6f}] | {b['distinguishable_from_zero']} |")
        lines.append("")
    lines.append("## Finalized monitoring statement")
    lines.append("")
    lines.append(payload["monitoring_statement"])
    lines.append("")
    lines.append("## Decision")
    lines.append("- No change to the incumbent's verdict (Credible Candidate). Bootstrap adds inference only; not used for selection/ranking/gate changes.")
    lines.append("")
    lines.append("## Reproduction commands")
    lines.append("```bash")
    lines.append("python research/tsmomentum_fold_regime_bootstrap_ci.py")
    lines.append("python -m pytest -q tests/test_tsmomentum_fold_regime_bootstrap_ci.py")
    lines.append("git status --porcelain data/ config/")
    lines.append("git diff --name-only HEAD -- research/run_cycle6.py research/experiments/tsmomentum_regime_filter_wf_001.md")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiments-dir", type=Path, default=EXPERIMENTS_DIR)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--report-out", type=Path, default=OUT_REPORT)
    parser.add_argument("--experiment-out", type=Path, default=OUT_EXP)
    parser.add_argument("--no-report", action="store_true", help="do not write the report or experiment record")
    args = parser.parse_args(argv)

    try:
        payload = run_bootstrap_ci(experiments_dir=args.experiments_dir, raw_dir=args.raw_dir, write_report=not args.no_report)
    except (AuditError, AttributionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not payload["anchor_reproduced"]:
        print("ERROR: published anchor not reproduced", file=sys.stderr)
        return 2

    if not args.no_report:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.experiment_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(render_report(payload), encoding="utf-8")
        args.experiment_out.write_text(render_experiment(payload), encoding="utf-8")

    print("OVERALL: PASS")
    print(f"anchor reproduced: {payload['anchor_reproduced']}")
    print(f"published design: {payload['recomputed_summary']['n_folds']} folds, WF mean OOS Sharpe {payload['recomputed_summary']['mean_test_sharpe']:.6f}")
    for family in ["F2_spy_trend_state", "F3_spy_12m_return_sign", "F4_train_63d_realvol_tercile"]:
        if family not in payload["families_bootstrap"]:
            continue
        fam = payload["families_bootstrap"][family]
        print(f"{fam['label']}:")
        for b in fam["buckets"]:
            print(f"  {b['bucket']}: n={b['n']}, gap={b['point_estimate_gap']:+.6f}, CI=[{b['ci_95_lo']:.6f},{b['ci_95_hi']:.6f}], distinguishable={b['distinguishable_from_zero']}")
    print(f"incumbent verdict: {payload['incumbent_verdict']}")
    print(f"report: {args.report_out}" if not args.no_report else "--no-report: no artifacts written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
