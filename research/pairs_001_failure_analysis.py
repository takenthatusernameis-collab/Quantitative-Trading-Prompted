#!/usr/bin/env python3
"""Cycle 937: read-only analysis of ``pairs_001`` failure modes (no re-tuning).

This tool reads the frozen hypothesis and configuration and the committed
evaluation artifacts produced by ``research/pairs_001_evaluation.py``.
It does not call the fetcher, does not modify ``data/`` or ``config/``,
and does not change any frozen artifacts.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.data_cost_inventory_002 import fingerprint  # noqa: E402

CYCLE = "937"

REPORTS_DIR = REPO_ROOT / "research" / "reports"
EXPERIMENTS_DIR = REPO_ROOT / "research" / "experiments"

OUT_REPORT = REPORTS_DIR / "pairs_001_failure_analysis.md"
OUT_EXP = EXPERIMENTS_DIR / "pairs_001_failure_analysis.md"

CONFIG_PATH = REPO_ROOT / "config" / "pairs_candidate_001.yaml"
HYPOTHESIS_PATH = REPO_ROOT / "research" / "hypotheses" / "pairs_001.md"
EVAL_EXP = EXPERIMENTS_DIR / "pairs_001_evaluation.md"
EVAL_REPORT = REPORTS_DIR / "pairs_001_evaluation.md"


class AnalysisError(RuntimeError):
    """Raised when required inputs are missing."""


def fail(message: str) -> None:
    raise AnalysisError(message)


# Per-pair values copied from committed evaluation records (read-only source of truth)
PAIR_ATTRIBUTION = [
    {"pair": "XLP/XLU", "net_excess_annualized": 0.009094, "sharpe": 0.179750, "trades": 226},
    {"pair": "XLF/XLK", "net_excess_annualized": -0.026539, "sharpe": -0.314578, "trades": 205},
    {"pair": "XLE/XLB", "net_excess_annualized": -0.032287, "sharpe": -0.408004, "trades": 211},
    {"pair": "XLI/XLB", "net_excess_annualized": -0.019626, "sharpe": -0.451870, "trades": 228},
    {"pair": "XLV/XLY", "net_excess_annualized": -0.028693, "sharpe": -0.439405, "trades": 201},
    {"pair": "XLK/XLU", "net_excess_annualized": -0.038723, "sharpe": -0.452537, "trades": 194},
]

COINT_SUMMARY = {
    "XLP/XLU": {"train_windows": 36, "cointegrated": 14, "min_p": 0.001032, "max_p": 0.990904},
    "XLF/XLK": {"train_windows": 36, "cointegrated": 4, "min_p": 0.000193, "max_p": 1.000000},
    "XLE/XLB": {"train_windows": 36, "cointegrated": 1, "min_p": 0.022739, "max_p": 0.992559},
    "XLI/XLB": {"train_windows": 36, "cointegrated": 7, "min_p": 0.002240, "max_p": 0.871773},
    "XLV/XLY": {"train_windows": 36, "cointegrated": 11, "min_p": 0.000992, "max_p": 0.555322},
    "XLK/XLU": {"train_windows": 36, "cointegrated": 10, "min_p": 0.001517, "max_p": 0.813088},
}

FIRED_CONDITIONS = {
    "i": {"observed": -0.829067, "requirement": ">= 0.9", "outcome": "FIRED"},
    "ii": {"observed": "[-1.219160, -0.467513]", "requirement": "excludes zero", "outcome": "not fired"},
    "iii": {"observed": "any pair failed", "requirement": "no pair fails", "outcome": "FIRED"},
    "iv": {"observed": -0.136774, "requirement": "> 0", "outcome": "FIRED"},
}

COST_BREAKDOWN = {
    "realized_turnover_per_year": 68.6916,
    "realized_turnover_cost_drag": 0.021364,
    "realized_borrow_drag_per_year": 0.203271,
    "realized_cost_drag_per_year": 0.224636,
    "gross_excess_before_any_cost_annualized": 0.087862,
    "excess_net_of_turnover_cost_before_borrow_annualized": 0.066497,
    "net_excess_after_borrow_annualized": -0.136774,
}


def load_inputs() -> dict[str, Any]:
    for p in [CONFIG_PATH, HYPOTHESIS_PATH, EVAL_EXP, EVAL_REPORT]:
        if not p.exists():
            fail(f"required input missing: {p}")
    cfg = yaml.safe_load(CONFIG_PATH.read_text()) or {}
    return {
        "config": cfg,
        "hypothesis": HYPOTHESIS_PATH.read_text(),
        "eval_exp": EVAL_EXP.read_text(),
        "eval_report": EVAL_REPORT.read_text(),
    }


def build_payload() -> dict[str, Any]:
    data_before = fingerprint(REPO_ROOT / "data")
    config_before = fingerprint(REPO_ROOT / "config")
    inputs = load_inputs()
    payload = {
        "cycle": CYCLE,
        "inputs": inputs,
        "pair_attribution": PAIR_ATTRIBUTION,
        "cointegration": COINT_SUMMARY,
        "fired_conditions": FIRED_CONDITIONS,
        "cost_breakdown": COST_BREAKDOWN,
    }
    data_after = fingerprint(REPO_ROOT / "data")
    config_after = fingerprint(REPO_ROOT / "config")
    payload["data_unchanged"] = data_before == data_after
    payload["config_unchanged"] = config_before == config_after
    return payload


def render_experiment(payload: dict[str, Any]) -> str:
    lines = []
    lines.append("# Experiment: `pairs_001` failure analysis (pairs_001_failure_analysis)")
    lines.append("")
    lines.append(f"**Cycle {CYCLE}.** Read-only deterministic analysis of why `pairs_001` failed, "
                  "using only the frozen hypothesis/config and committed evaluation artifacts. "
                  "No re-tuning, no changes under `data/` or `config/`, no modifications to frozen artifacts.")
    lines.append("")
    lines.append("## Inputs (read-only)")
    lines.append(f"- Hypothesis: `{HYPOTHESIS_PATH.relative_to(REPO_ROOT)}`")
    lines.append(f"- Config: `{CONFIG_PATH.relative_to(REPO_ROOT)}`")
    lines.append(f"- Experiment: `{EVAL_EXP.relative_to(REPO_ROOT)}`")
    lines.append(f"- Report: `{EVAL_REPORT.relative_to(REPO_ROOT)}`")
    lines.append("")
    lines.append("## Per-pair attribution (out of sample)")
    lines.append("| Pair | Net excess annualized | Sharpe | Trades |")
    lines.append("|---|---|---|---|")
    for row in payload["pair_attribution"]:
        lines.append(f"| {row['pair']} | {row['net_excess_annualized']:.6f} | {row['sharpe']:.6f} | {row['trades']} |")
    lines.append("")
    lines.append("## Cointegration failure summary (training windows only)")
    lines.append("| Pair | Train windows | Cointegrated | Min p-value | Max p-value |")
    lines.append("|---|---|---|---|---|")
    for pair, info in payload["cointegration"].items():
        lines.append(f"| {pair} | {info['train_windows']} | {info['cointegrated']} | {info['min_p']:.6f} | {info['max_p']:.6f} |")
    lines.append("")
    lines.append("## Cost breakdown (turnover drag vs borrow drag)")
    cb = payload["cost_breakdown"]
    lines.append("| Item | Value |")
    lines.append("|---|---|")
    lines.append(f"| Realized turnover (per year) | {cb['realized_turnover_per_year']:.4f} units/yr |")
    lines.append(f"| Realized turnover cost drag | {cb['realized_turnover_cost_drag']:.6%}/yr |")
    lines.append(f"| Realized borrow drag (25 bp x short notional per rebalance) | {cb['realized_borrow_drag_per_year']:.4%}/yr |")
    lines.append(f"| Realized total cost drag | {cb['realized_cost_drag_per_year']:.4%}/yr |")
    lines.append(f"| Gross excess (before any cost) annualized | {cb['gross_excess_before_any_cost_annualized']:.4%} |")
    lines.append(f"| Excess net of the turnover cost, before borrow, annualized | {cb['excess_net_of_turnover_cost_before_borrow_annualized']:.4%} |")
    lines.append(f"| Net excess after borrow annualized | {cb['net_excess_after_borrow_annualized']:.4%} |")
    lines.append("")
    lines.append("## Pre-registered conditions fired")
    lines.append("| # | Observed | Requirement | Outcome |")
    lines.append("|---|---|---|---|")
    for k in ["i", "ii", "iii", "iv"]:
        c = payload["fired_conditions"][k]
        lines.append(f"| {k} | {c['observed']} | {c['requirement']} | **{c['outcome']}** |")
    lines.append("")
    lines.append("## Failure mechanism hypothesis (evidence-based, no speculation beyond measured)")
    lines.append("- **Structural instability**: cointegration fails in most training windows for nearly all pairs (only 1/36 for XLE/XLB, 4/36 for XLF/XLK) — the mean-reverting spread assumption is not stable out of sample in this regime set.")
    lines.append("- **Cost sensitivity**: the gross excess before any cost is modest (+8.79%/yr); the measured turnover drag is 2.14%/yr and the pre-registered borrow drag is 20.33%/yr, leaving net -13.68%/yr; the strategy is not robust to the assumed short-borrow cost.")
    lines.append("- **Broad underperformance**: all pairs except XLP/XLU have negative net excess/Sharpe; performance is consistently negative across folds with positive-fold rate 0.25 and mean OOS Sharpe -0.829.")
    lines.append("- **Conclusion**: rejection is driven by a combination of unstable cointegration (condition iii) and insufficient gross edge to survive pre-registered borrow costs (condition iv), producing mean OOS Sharpe below threshold (condition i).")
    lines.append("")
    lines.append("## Integrity")
    lines.append(f"- data/ unchanged: {payload['data_unchanged']}")
    lines.append(f"- config/ unchanged: {payload['config_unchanged']}")
    lines.append("")
    return "\n".join(lines) + "\n"


def render_report(payload: dict[str, Any]) -> str:
    lines = []
    lines.append("# Report: `pairs_001` failure analysis (pairs_001_failure_analysis)")
    lines.append("")
    lines.append(f"**Cycle {CYCLE}.** Read-only, deterministic post-mortem. No files under `data/` or `config/` were modified; frozen artifacts remain unchanged.")
    lines.append("")
    lines.append("## 1) Per-pair attribution")
    lines.append("| Pair | Net excess annualized | Sharpe | Trades |")
    lines.append("|---|---|---|---|")
    for row in payload["pair_attribution"]:
        lines.append(f"| {row['pair']} | {row['net_excess_annualized']:.6f} | {row['sharpe']:.6f} | {row['trades']} |")
    lines.append("")
    lines.append("## 2) Cointegration failure summary")
    lines.append("| Pair | Train windows | Cointegrated | Fails? | Min p | Max p |")
    lines.append("|---|---|---|---|---|---|")
    for pair, info in payload["cointegration"].items():
        fails = info["cointegrated"] < info["train_windows"]
        lines.append(f"| {pair} | {info['train_windows']} | {info['cointegrated']} | {fails} | {info['min_p']:.6f} | {info['max_p']:.6f} |")
    lines.append("")
    lines.append("## 3) Cost breakdown")
    cb = payload["cost_breakdown"]
    lines.append(f"- Turnover: {cb['realized_turnover_per_year']:.4f} units/yr; turnover cost drag: {cb['realized_turnover_cost_drag']:.6%}/yr")
    lines.append(f"- Borrow: {cb['realized_borrow_drag_per_year']:.4%}/yr (pre-registered 25 bp per unit short notional per rebalance)")
    lines.append(f"- Total drag: {cb['realized_cost_drag_per_year']:.4%}/yr")
    lines.append(f"- Gross before any cost: {cb['gross_excess_before_any_cost_annualized']:.4%}/yr; net of the turnover cost, before borrow: {cb['excess_net_of_turnover_cost_before_borrow_annualized']:.4%}/yr; Net after borrow: {cb['net_excess_after_borrow_annualized']:.4%}/yr")
    lines.append("")
    lines.append("## 4) Fired pre-registered conditions")
    for k in ["i", "iii", "iv", "ii"]:
        c = payload["fired_conditions"][k]
        if c["outcome"] == "FIRED":
            lines.append(f"- ({k}) {c['requirement']}: observed {c['observed']} → **FIRED**")
        else:
            lines.append(f"- ({k}) {c['requirement']}: observed {c['observed']} → {c['outcome']}")
    lines.append("")
    lines.append("## 5) Concrete hypothesis about failure mechanism")
    lines.append("The strategy's gross edge is small relative to the pre-registered borrow assumption and the spread reversion assumption is not cointegrated reliably across training windows; both effects are necessary to explain the negative net out-of-sample performance. Specifically, borrow drag dominates (net turns negative despite modest gross), and cointegration failure on many windows violates condition (iii).")
    lines.append("")
    lines.append("## 6) Reproduction")
    lines.append("```bash")
    lines.append("python research/pairs_001_failure_analysis.py")
    lines.append("python -m pytest -q tests/test_pairs_001_failure_analysis.py")
    lines.append("git status --porcelain data/ config/")
    lines.append("```")
    lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-report", action="store_true", help="do not write outputs")
    args = parser.parse_args(argv)

    try:
        payload = build_payload()
    except AnalysisError as error:
        print(f"ERROR: {error}")
        return 2

    if not args.no_report:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
        OUT_REPORT.write_text(render_report(payload))
        OUT_EXP.write_text(render_experiment(payload))

    print("OVERALL: PASS")
    print(f"PAIRS_ANALYZED|{len(payload['pair_attribution'])}")
    fired = [k for k, v in payload['fired_conditions'].items() if v['outcome'] == 'FIRED']
    print(f"FIRED|{','.join(sorted(fired))}")
    print(f"NET_EXCESS_AFTER_BORROW|{payload['cost_breakdown']['net_excess_after_borrow_annualized']:.6f}")
    print(f"REPORT|{OUT_REPORT if not args.no_report else '(not written)'}")
    print(f"EXPERIMENT|{OUT_EXP if not args.no_report else '(not written)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
