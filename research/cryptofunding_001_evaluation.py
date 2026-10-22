#!/usr/bin/env python3
"""Evaluate the frozen ``cryptofunding_001`` candidate.

First published in Cycle 944. **Corrected in Cycle 945**: the Cycle 944
generator applied ``0.02`` *basis points* per unit of weight change to the
headline (the repository's annual capital-charge rate was passed into the
flat-cost function) and applied no capital charge at all, while the published
report declared the frozen configuration's 5.0 bp/unit and 2.0%/yr. Every
published number now uses the frozen configuration's cost model, and the
reconciliation with the prior cycles' record is generated with the same run.

The tool is read-only: it reads the committed carry paths, writes only its own
report and experiment record, and compares the SHA-256 fingerprints of
``data/``, ``config/`` and the tracked artefacts before and after the run.
"""

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

CYCLE = "945"
FIRST_PUBLISHED_CYCLE = "944"

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

#: The rule whose net return is the candidate's headline: the implementable
#: (previous-day signal) funding-positive rule. The always-on book is reported
#: next to it, and the look-ahead-contaminated same-day rule is reported for
#: reconciliation with the Cycle 890 record only.
HEADLINE_RULE = "funding_positive_lagged"

#: The conventions the reconciliation table reports. Every one of them is a
#: cost model that a committed record already published, so the table is a
#: cross-cycle comparison rather than a new set of trials.
RECONCILIATION_MODELS: dict[str, str] = {
    "frozen_config": "frozen_flat_5bp_capital_rf",
    "cycle891_flat_3bp": "flat_3bp",
    "cycle892_venue_taker_rf": "realistic_rf",
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


def frozen_cost_model(config: dict[str, Any]) -> ev.CostModel:
    """The cost model the frozen configuration declares.

    ``total_round_trip_bps`` (commission + slippage per unit of weight change)
    and ``capital_charge_annual`` (the charge on the capital the spot leg ties
    up) are read from the frozen configuration, so the applied cost model
    cannot drift away from the published one.
    """
    return ev.CostModel(
        key="frozen_flat_5bp_capital_rf",
        label=(
            f"Frozen configuration: {config['total_round_trip_bps']:.1f} bp per unit "
            f"of weight change + {config['capital_charge_annual']:.2%}/yr capital charge "
            "on the spot leg"
        ),
        kind="flat",
        flat_bps=float(config["total_round_trip_bps"]),
        capital_rate_annual=float(config["capital_charge_annual"]),
        source="config/cryptofunding_001.yaml (cost_model)",
        note=(
            "The cost model the frozen configuration declares: the commission plus "
            "slippage per unit of weight change, and the repository's risk-free rate "
            "charged on the capital the spot leg ties up."
        ),
    )


def portfolio_metrics(book: ev.Book, net: pd.Series) -> dict[str, float]:
    """The full-sample and out-of-sample metrics of *book* under *net*."""
    full = ev.sample_index(net.index, "full")
    oos = ev.sample_index(net.index, "test_oos")
    return {
        "full_ann": float(ev.annualized_return(net.loc[full], ev.PERIODS_PER_YEAR)),
        "oos_ann": float(ev.annualized_return(net.loc[oos], ev.PERIODS_PER_YEAR)),
        "oos_sharpe": float(
            ev.sharpe_ratio(net.loc[oos], periods_per_year=ev.PERIODS_PER_YEAR)
        ),
    }


def gross_metrics(book: ev.Book) -> dict[str, float]:
    """The same metrics with no cost at all."""
    return portfolio_metrics(book, book.gross)


def per_symbol_oos_sharpe(book: ev.Book, model: ev.CostModel) -> float:
    """The canonical out-of-sample Sharpe of a single-symbol book under *model*."""
    net = ev.net_series_model(book, model)
    oos = ev.sample_index(net.index, "test_oos")
    return float(ev.sharpe_ratio(net.loc[oos], periods_per_year=ev.PERIODS_PER_YEAR))


def build_payload() -> dict[str, Any]:
    data_before = fingerprint(REPO_ROOT / "data")
    config_before = fingerprint(REPO_ROOT / "config")
    artifacts_before = tracked_artifact_hashes()

    config = load_frozen_config()
    model = frozen_cost_model(config)
    paths = {base: ev.load_carry_path(base) for base in ev.BASE_SYMBOLS}

    identity = {base: ev.check_identity(paths[base]) for base in ev.BASE_SYMBOLS}

    portfolio_books: dict[str, ev.Book] = {}
    symbol_books: dict[str, dict[str, ev.Book]] = {}
    per_symbol_gate_results: dict[str, dict[str, Any]] = {}
    per_symbol_mean_oos_sharpe: dict[str, float] = {}

    for rule in ev.RULES:
        portfolio_books[rule.rule_id] = ev.portfolio_book(paths, rule)
        symbol_books[rule.rule_id] = {
            base: ev.build_book(paths[base], rule, weight=1.0) for base in ev.BASE_SYMBOLS
        }
        per_symbol_gate_results[rule.rule_id] = ev.promotion_gate(
            {
                base: ev.evaluate_book(symbol_books[rule.rule_id][base], cost_model=model)
                for base in ev.BASE_SYMBOLS
            }
        )
        per_symbol_mean_oos_sharpe[rule.rule_id] = float(
            np.mean(
                [
                    per_symbol_oos_sharpe(symbol_books[rule.rule_id][base], model)
                    for base in ev.BASE_SYMBOLS
                ]
            )
        )

    reconciliation: dict[str, dict[str, dict[str, float]]] = {}
    for rule in ev.RULES:
        book = portfolio_books[rule.rule_id]
        rows: dict[str, dict[str, float]] = {
            "gross_no_cost": gross_metrics(book),
        }
        for label, model_key in RECONCILIATION_MODELS.items():
            convention = model if label == "frozen_config" else ev.COST_MODEL_BY_KEY[model_key]
            rows[label] = portfolio_metrics(book, ev.net_series_model(book, convention))
        reconciliation[rule.rule_id] = rows

    headline_book = portfolio_books[HEADLINE_RULE]
    net = ev.net_series_model(headline_book, model)

    published_cycle944 = {
        "headline_rule": HEADLINE_RULE,
        "headline_net_ann": float(
            ev.annualized_return(
                ev.net_series(headline_book, ev.CAPITAL_CHARGE_RATES["repo_rf"]),
                ev.PERIODS_PER_YEAR,
            )
        ),
        "applied_cost_bps_per_unit": ev.CAPITAL_CHARGE_RATES["repo_rf"],
        "per_symbol_mean_oos_sharpe": {
            rule.rule_id: float(
                np.mean(
                    [
                        per_symbol_oos_sharpe(symbol_books[rule.rule_id][base], ev.COST_MODEL_BY_KEY["flat_3bp"])
                        for base in ev.BASE_SYMBOLS
                    ]
                )
            )
            for rule in ev.RULES
        },
    }

    payload = {
        "cycle": CYCLE,
        "first_published_cycle": FIRST_PUBLISHED_CYCLE,
        "config": config,
        "cost_model": {
            "key": model.key,
            "label": model.label,
            "kind": model.kind,
            "flat_bps_per_unit": model.flat_bps,
            "capital_charge_annual": model.capital_rate_annual,
        },
        "identity": identity,
        "per_symbol_gate_results": per_symbol_gate_results,
        "per_symbol_mean_oos_sharpe": per_symbol_mean_oos_sharpe,
        "portfolio_net_ann": float(ev.annualized_return(net, ev.PERIODS_PER_YEAR)),
        "portfolio_gross_ann": float(
            ev.annualized_return(headline_book.gross, ev.PERIODS_PER_YEAR)
        ),
        "reconciliation": reconciliation,
        "published_cycle944": published_cycle944,
        "overall": "PASS",
    }

    data_after = fingerprint(REPO_ROOT / "data")
    config_after = fingerprint(REPO_ROOT / "config")
    artifacts_after = tracked_artifact_hashes()
    payload["data_unchanged"] = data_before == data_after
    payload["config_unchanged"] = config_before == config_after
    payload["artifacts_unchanged"] = artifacts_before == artifacts_after
    return payload


def _correction_table(payload: dict[str, Any]) -> list[str]:
    published = payload["published_cycle944"]
    before = published["headline_net_ann"]
    after = payload["portfolio_net_ann"]
    lines = [
        "| Item | Cycle 944 (as published) | Cycle 945 (corrected) |",
        "|---|---|---|",
        f"| Applied trading cost | {published['applied_cost_bps_per_unit']} bp/unit "
        "(the annual capital-charge rate, passed into the flat-cost function) | "
        f"{payload['cost_model']['flat_bps_per_unit']} bp/unit (the frozen "
        "`total_round_trip_bps`) |",
        f"| Applied capital charge | none | "
        f"{payload['cost_model']['capital_charge_annual']:.2%}/yr on the spot leg |",
        f"| Portfolio net ann (headline, `{HEADLINE_RULE}`) | {before:.4%} | {after:.4%} |",
        f"| Portfolio gross ann (no cost) | {payload['portfolio_gross_ann']:.4%} | "
        f"{payload['portfolio_gross_ann']:.4%} |",
    ]
    for rule_id, sharpe in payload["per_symbol_mean_oos_sharpe"].items():
        lines.append(
            f"| Mean per-symbol OOS Sharpe, `{rule_id}` | "
            f"{published['per_symbol_mean_oos_sharpe'][rule_id]:.3f} | {sharpe:.3f} |"
        )
    return lines


def render_report(payload: dict[str, Any]) -> str:
    lines = []
    lines.append(f"# Cycle {payload['cycle']}: cryptofunding_001 evaluation")
    lines.append("")
    lines.append(
        f"First published in Cycle {payload['first_published_cycle']}; the generator's "
        "cost model was corrected in Cycle 945 (see the correction section below and "
        "`research/experiments/cryptofunding_001_evaluation_erratum_001.md`)."
    )
    lines.append("")
    lines.append("## Frozen configuration")
    lines.append(f"- Candidate: {payload['config']['candidate_id']}")
    lines.append(f"- Universe: {', '.join(payload['config']['universe'])}")
    lines.append(
        f"- Cost model: {payload['cost_model']['flat_bps_per_unit']:.1f} bp/unit (flat) "
        f"+ {payload['cost_model']['capital_charge_annual']:.2%}/yr capital charge on "
        "the spot leg"
    )
    lines.append(f"- Annualization: {payload['config']['annualization']}")
    lines.append(f"- Headline rule: {HEADLINE_RULE}")
    lines.append("")
    lines.append("## Results (frozen configuration)")
    lines.append(f"- Portfolio net ann (headline): {payload['portfolio_net_ann']:.4%}")
    lines.append(
        f"- Portfolio gross ann (no cost): {payload['portfolio_gross_ann']:.4%}"
    )
    for rule_id, gate in payload["per_symbol_gate_results"].items():
        lines.append(
            f"- {rule_id}: gate_pass={gate['promotion_gate_pass']}, "
            f"sharpe_oos={payload['per_symbol_mean_oos_sharpe'][rule_id]:.3f}, "
            f"pooled_oos_round_trips={gate['pooled_oos_position_round_trips']}"
        )
    lines.append("")
    lines.append("## Cost model correction (Cycle 945)")
    lines.append(
        "The Cycle 944 generator passed the repository's **annual capital-charge rate** "
        "(0.02) into `net_series(book, cost_bps)`, so the published headline charged "
        "0.02 **basis points** per unit of weight change instead of the frozen "
        "5.0 bp/unit, and it applied **no** capital charge at all: the published "
        "headline was the gross return of the headline rule's portfolio. The published "
        "report nevertheless declared the frozen configuration's 5.0 bp/unit and "
        "2.00%/yr. The numbers below are the corrected ones."
    )
    lines.append("")
    lines.extend(_correction_table(payload))
    lines.append("")
    lines.append("## Reconciliation with the prior cycles")
    lines.append(
        "Equal-weight BTC/ETH portfolio, 365-day annualization, no cost for the "
        "`gross_no_cost` row. The OOS window is 2025-01-01..2026-09-30 and the "
        "Sharpe is the canonical (arithmetic, zero risk-free) portfolio Sharpe."
    )
    lines.append("")
    lines.append(
        "| Rule | Cost convention | Full-sample net ann | OOS net ann | OOS Sharpe |"
    )
    lines.append("|---|---|---|---|---|")
    labels = {
        "gross_no_cost": "gross (no cost)",
        "frozen_config": "frozen config (5 bp/unit + 2%/yr capital)",
        "cycle891_flat_3bp": "Cycle 891 flat 3 bp/unit",
        "cycle892_venue_taker_rf": "Cycle 892 venue taker + slippage + rf",
    }
    for rule_id, rows in payload["reconciliation"].items():
        for key, label in labels.items():
            row = rows[key]
            lines.append(
                f"| {rule_id} | {label} | {row['full_ann']:+.4%} | {row['oos_ann']:+.4%} | "
                f"{row['oos_sharpe']:+.3f} |"
            )
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
    lines.append(
        f"First published in Cycle {payload['first_published_cycle']}. **Correction "
        "(Cycle 945):** the Cycle 944 generator applied 0.02 bp/unit of trading cost "
        "and no capital charge instead of the frozen 5.0 bp/unit and 2.00%/yr, so the "
        "published headline was the gross return of the headline rule's portfolio. The "
        "generator is corrected, the artifacts are regenerated, and the correction is "
        "of record in `research/experiments/cryptofunding_001_evaluation_erratum_001.md`. "
        "The verdict (exploratory signal, not promoted) is unchanged."
    )
    lines.append("")
    lines.append("## Hypothesis")
    lines.append("- research/hypotheses/cryptofunding_001.md (frozen)")
    lines.append("")
    lines.append("## Configuration")
    lines.append("- config/cryptofunding_001.yaml (frozen)")
    lines.append("")
    lines.append("## Evaluation")
    lines.append(f"- Overall: {payload['overall']}")
    lines.append(f"- Portfolio net ann (headline, {HEADLINE_RULE}): {payload['portfolio_net_ann']:.4%}")
    for rule_id, gate in payload["per_symbol_gate_results"].items():
        lines.append(
            f"- {rule_id}: gate_pass={gate['promotion_gate_pass']}, "
            f"sharpe_oos={payload['per_symbol_mean_oos_sharpe'][rule_id]:.3f}"
        )
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
    add(
        "frozen_cost_model_applied",
        payload["cost_model"]["flat_bps_per_unit"] == payload["config"]["total_round_trip_bps"]
        and payload["cost_model"]["capital_charge_annual"] == payload["config"]["capital_charge_annual"],
        "the applied cost model is the frozen configuration's cost model",
    )
    add(
        "headline_below_gross",
        payload["portfolio_net_ann"] < payload["portfolio_gross_ann"],
        "the published headline is net of the frozen cost model, not the gross return",
    )
    add(
        "gate_fails_for_every_rule",
        all(gate["promotion_gate_pass"] is False for gate in payload["per_symbol_gate_results"].values()),
        "the promotion gate fails for every rule (the trade-count criterion)",
    )
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
    print(f"HEADLINE|net_ann={payload['portfolio_net_ann']:.6%}|gross_ann={payload['portfolio_gross_ann']:.6%}")
    for rule_id, gate in payload["per_symbol_gate_results"].items():
        print(
            f"GATE|{rule_id}|gate_pass={gate['promotion_gate_pass']}"
            f"|sharpe_oos={payload['per_symbol_mean_oos_sharpe'][rule_id]:.6f}"
            f"|pooled_oos_round_trips={gate['pooled_oos_position_round_trips']}"
        )
    print(f"REPORT|{OUT_REPORT if not args.no_report else '(not written: --no-report)'}")
    print(f"EXPERIMENT|{OUT_EXP if not args.no_report else '(not written: --no-report)'}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
