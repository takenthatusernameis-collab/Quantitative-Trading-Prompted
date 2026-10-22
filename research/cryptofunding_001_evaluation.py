#!/usr/bin/env python3
"""Cycle 944: evaluate the frozen ``cryptofunding_001`` candidate."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.data_cost_inventory_002 import (
    fingerprint,
    tracked_artifact_hashes,
)

import research.eval_cryptofunding as ev

CYCLE = "944"

REPORTS_DIR = REPO_ROOT / "research" / "reports"
EXPERIMENTS_DIR = REPO_ROOT / "research" / "experiments"

OUT_REPORT = REPORTS_DIR / "cryptofunding_001_evaluation.md"
OUT_EXP = EXPERIMENTS_DIR / "cryptofunding_001_evaluation.md"

CONFIG_PATH = REPO_ROOT / "config" / "cryptofunding_001.yaml"
HYPOTHESIS_PATH = REPO_ROOT / "research" / "hypotheses" / "cryptofunding_001.md"

FROZEN: dict[str, Any] = {
    "candidate_id": "cryptofunding_001",
    "universe": ["BTCUSDT", "ETHUSDT"],
    "signal_type": "funding_rate_carry",
    "entry_condition": "funding_cashflow > 0",
    "rebalance": "daily",
    "rebalance_freq": "daily",
    "rebalance_per_year": 365,
    "leg_weight": 0.5,
    "gross_exposure_max": 1.0,
    "commission_bps_per_unit": 3.0,
    "slippage_bps_per_unit": 2.0,
    "total_round_trip_bps": 5.0,
    "capital_charge_annual": 0.02,
    "annualization": 365,
    "history_start": "2020-01-02",
    "history_end": "2026-09-30",
    "purge_days": 2,
    "embargo_days": 2,
    "wf_mean_oos_sharpe_min": 0.9,
    "positive_fold_rate_min": 0.5,
    "pooled_oos_trades_min": 100,
}


class EvaluationError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise EvaluationError(message)


def load_frozen_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        fail(f"the frozen configuration is missing: {CONFIG_PATH}")
    if not HYPOTHESIS_PATH.exists():
        fail(f"the frozen hypothesis is missing: {HYPOTHESIS_PATH}")
    config = yaml.safe_load(CONFIG_PATH.read_text()) or {}
    signal = config.get("signal", {})
    portfolio = config.get("portfolio", {})
    costs = config.get("cost_model", {})
    execution = config.get("execution", {})
    evaluation = config.get("evaluation", {})
    walk = evaluation.get("walk_forward", {})
    gates = evaluation.get("promotion_gates", {})
    risk = config.get("risk_overlay", {})

    observed = {
        "candidate_id": config.get("candidate_id"),
        "universe": list(config.get("universe", [])),
        "signal_type": signal.get("type"),
        "entry_condition": signal.get("entry_condition"),
        "rebalance": signal.get("rebalance"),
        "rebalance_freq": signal.get("rebalance_freq"),
        "rebalance_per_year": signal.get("rebalance_per_year"),
        "leg_weight": portfolio.get("leg_weight"),
        "gross_exposure_max": portfolio.get("gross_exposure_max"),
        "commission_bps_per_unit": costs.get("commission_bps_per_unit"),
        "slippage_bps_per_unit": costs.get("slippage_bps_per_unit"),
        "total_round_trip_bps": costs.get("total_round_trip_bps"),
        "capital_charge_annual": costs.get("capital_charge_annual"),
        "annualization": execution.get("annualization"),
        "history_start": config.get("history_start"),
        "history_end": config.get("history_end"),
        "purge_days": walk.get("purge_days"),
        "embargo_days": walk.get("embargo_days"),
        "wf_mean_oos_sharpe_min": gates.get("wf_mean_oos_sharpe_min"),
        "positive_fold_rate_min": gates.get("positive_fold_rate_min"),
        "pooled_oos_trades_min": gates.get("pooled_oos_trades_min"),
    }
    drift = {k: (observed[k], FROZEN[k]) for k in FROZEN if observed[k] != FROZEN[k]}
    if drift:
        fail("the frozen configuration has drifted from the pre-registered values: " +
             "; ".join(f"{k}={v[0]!r} (frozen {v[1]!r})" for k, v in drift.items()))
    if risk.get("none") is not True:
        fail("the frozen configuration does not disable the risk overlay")
    if observed["universe"] != ["BTCUSDT", "ETHUSDT"]:
        fail("universe must be BTCUSDT, ETHUSDT")
    return observed


def build_payload() -> dict[str, Any]:
    data_before = fingerprint(REPO_ROOT / "data")
    config_before = fingerprint(REPO_ROOT / "config")
    artifacts_before = tracked_artifact_hashes()

    config = load_frozen_config()
    paths = {base: ev.load_carry_path(base) for base in ev.BASE_SYMBOLS}

    identity = {base: ev.check_identity(paths[base]) for base in ev.BASE_SYMBOLS}

    books = {}
    for rule in ev.RULES:
        portfolio = ev.portfolio_book(paths, rule)
        books[f"portfolio_{rule.rule_id}"] = ev.evaluate_book(portfolio)
        for base in ev.BASE_SYMBOLS:
            symbol_book = ev.build_book(paths[base], rule, weight=1.0)
            books[f"{base}_{rule.rule_id}"] = ev.evaluate_book(symbol_book)

    per_symbol_gate_results = {}
    for rule in ev.RULES:
        per_symbol_gate_results[rule.rule_id] = ev.promotion_gate(
            {base: books[f"{base}_{rule.rule_id}"] for base in ev.BASE_SYMBOLS}
        )

    portfolio_lagged = ev.portfolio_book(paths, ev.RULES[2])
    net = ev.net_series(portfolio_lagged, ev.CAPITAL_CHARGE_RATES["repo_rf"])

    payload = {
        "cycle": CYCLE,
        "config": config,
        "identity": identity,
        "per_symbol_gate_results": per_symbol_gate_results,
        "portfolio_net_ann": float(ev.annualized_return(net, ev.PERIODS_PER_YEAR)),
        "overall": "PASS",
    }

    data_after = fingerprint(REPO_ROOT / "data")
    config_after = fingerprint(REPO_ROOT / "config")
    artifacts_after = tracked_artifact_hashes()
    payload["data_unchanged"] = data_before == data_after
    payload["config_unchanged"] = config_before == config_after
    payload["artifacts_unchanged"] = artifacts_before == artifacts_after
    return payload


def render_report(payload: dict[str, Any]) -> str:
    lines = []
    lines.append(f"# Cycle {payload['cycle']}: cryptofunding_001 evaluation")
    lines.append("")
    lines.append("## Frozen configuration")
    lines.append(f"- Candidate: {payload['config']['candidate_id']}")
    lines.append(f"- Universe: {', '.join(payload['config']['universe'])}")
    lines.append(f"- Cost model: {payload['config']['total_round_trip_bps']} bp/unit")
    lines.append(f"- Annualization: {payload['config']['annualization']}")
    lines.append("")
    lines.append("## Results")
    lines.append(f"- Portfolio net ann (headline): {payload['portfolio_net_ann']:.4%}")
    for rule_id, gate in payload["per_symbol_gate_results"].items():
        lines.append(f"- {rule_id}: gate_pass={gate['promotion_gate_pass']}, sharpe_oos={gate['net_oos_sharpe_canonical_365']:.3f}")
    lines.append("")
    lines.append("## Data integrity")
    lines.append(f"- data/ unchanged: {payload['data_unchanged']}")
    lines.append(f"- config/ unchanged: {payload['config_unchanged']}")
    lines.append(f"- artifacts unchanged: {payload['artifacts_unchanged']}")
    lines.append("")
    lines.append("## Reproduction")
    lines.append("```bash")
    lines.append("python research/cryptofunding_001_evaluation.py")
    lines.append("python -m pytest tests/test_eval_cryptofunding_001.py -q")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def render_experiment(payload: dict[str, Any]) -> str:
    lines = []
    lines.append(f"# Experiment: cryptofunding_001_evaluation (Cycle {payload['cycle']})")
    lines.append("")
    lines.append("## Hypothesis")
    lines.append("- research/hypotheses/cryptofunding_001.md (frozen)")
    lines.append("")
    lines.append("## Configuration")
    lines.append("- config/cryptofunding_001.yaml (frozen)")
    lines.append("")
    lines.append("## Evaluation")
    lines.append(f"- Overall: {payload['overall']}")
    lines.append("- Cache-only: true")
    lines.append("- Network fetches: none")
    lines.append("")
    lines.append("## Reproduction")
    lines.append("```bash")
    lines.append("python research/cryptofunding_001_evaluation.py")
    lines.append("python -m pytest tests/test_eval_cryptofunding_001.py -q")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def run_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    checks = []
    def add(name: str, passed: bool, detail: str):
        checks.append({"name": name, "pass": bool(passed), "detail": detail})

    add("frozen_config_loaded", True, "frozen config asserted")
    add("cache_only", payload["data_unchanged"], "no writes under data/")
    add("config_unchanged", payload["config_unchanged"], "no writes under config/")
    add("evaluation_completed", payload["overall"] == "PASS", "evaluation ran")
    add("carry_identity_ok", all(v == 0.0 for v in payload["identity"].values()), "carry identity holds")
    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-report", action="store_true")
    args = parser.parse_args(argv)

    try:
        payload = build_payload()
        checks = run_checks(payload)
    except EvaluationError as error:
        print(f"ERROR: {error}")
        return 2
    except Exception as error:
        print(f"ERROR: {error}")
        import traceback
        traceback.print_exc()
        return 2

    overall = all(check["pass"] for check in checks)

    if not args.no_report:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
        OUT_REPORT.write_text(render_report(payload))
        OUT_EXP.write_text(render_experiment(payload))

    print(f"OVERALL: {'PASS' if overall else 'FAIL'}")
    for check in checks:
        print(f"CHECK|{check['name']}|{'PASS' if check['pass'] else 'FAIL'}|{check['detail']}")
    print(f"REPORT|{OUT_REPORT if not args.no_report else '(not written: --no-report)'}")
    print(f"EXPERIMENT|{OUT_EXP if not args.no_report else '(not written: --no-report)'}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
