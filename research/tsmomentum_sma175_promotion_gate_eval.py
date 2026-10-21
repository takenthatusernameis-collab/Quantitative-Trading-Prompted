#!/usr/bin/env python3
"""Evaluate SMA-175 candidate against full promotion gate suite (Cycle 920)."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.run_cycle6 import (
    DD_THRESHOLD,
    END_DATE,
    LOOKBACK,
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
    _apply_overlay,
)
from src.evaluation.sharpe import (
    SHARPE_CONVENTION_ID,
    backtest_sharpe_ratio,
    sharpe_ratio,
)
from src.evaluation.statistics import compute_psr
from src.evaluation.utils import max_drawdown
from src.features.momentum import build_weights
from src.simulation.evaluation import (
    GoNoGoConfig,
    classify_psr,
    evaluate_promotion_gates,
    map_decision,
)

RAW_DIR = REPO_ROOT / "data" / "raw"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
EXPERIMENTS_DIR = REPO_ROOT / "research" / "experiments"
CONFIG_GATES = REPO_ROOT / "config" / "promotion_gates.yaml"

OUT_REPORT = REPORTS_DIR / "tsmomentum_sma175_promotion_gate_eval_001.md"
OUT_EXP = EXPERIMENTS_DIR / "tsmomentum_sma175_promotion_gate_eval_001.md"

SMA_NEW = 175
CANDIDATE_ID = "tsmomentum_sma175_candidate"
CYCLE = 920
PSR_SEED = 20240101

# The PSR gate is defined in config/promotion_gates.yaml against the *fixed*
# backtest Sharpe baseline (1.4178), not against a candidate-specific value:
#   "compute_psr ... of the paper return series against the backtest Sharpe
#    baseline 1.4178" (config/promotion_gates.yaml, gate "psr")
# The same constant and the same bootstrap settings are used by the canonical
# promotion evaluation (src/simulation/evaluation.py) and by every other PSR
# call in the repository (research/promotion_feasibility_backtest.py,
# research/rolling_63d_gate_refresh.py, research/psr_feasibility.py).
# A candidate-specific target would make the gate value incomparable with
# every published PSR and would silently substitute a self-comparison.
GO_NO_GO = GoNoGoConfig()
PSR_TARGET_BACKTEST_SCALE = float(GO_NO_GO.backtest_sharpe)
PSR_N_BOOTSTRAP = int(GO_NO_GO.bootstrap_samples)
PSR_BLOCK_SIZE = int(GO_NO_GO.block_size)
PSR_TARGET_SOURCE = (
    "config/promotion_gates.yaml gate 'psr' (backtest Sharpe baseline "
    f"{PSR_TARGET_BACKTEST_SCALE}); src.simulation.evaluation.GoNoGoConfig.backtest_sharpe"
)


def _git_hash() -> str:
    try:
        import subprocess

        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def load_close_from_cache(symbols: list[str]) -> pd.DataFrame:
    frames: dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        path = RAW_DIR / f"{symbol}.parquet"
        if not path.exists():
            raise FileNotFoundError(f"missing cached price: {path}")
        df = pd.read_parquet(path)
        idx = pd.to_datetime(df.index)
        if idx.tz is None:
            idx = idx.tz_localize("UTC", ambiguous="infer", nonexistent="shift_forward")
        else:
            idx = idx.tz_convert("UTC")
        df = df.copy()
        df.index = idx
        frames[symbol] = df.sort_index()

    all_index = pd.DatetimeIndex(sorted(set().union(*[f.index for f in frames.values()])))
    all_index = all_index[all_index.weekday < 5]
    out = pd.DataFrame(index=all_index)
    for symbol, df in frames.items():
        if "Close" not in df.columns:
            raise RuntimeError(f"missing Close for {symbol}")
        out[symbol] = df["Close"].reindex(all_index).ffill()
    out = out.ffill().dropna(how="all")
    return out


def _eval_full_period(close: pd.DataFrame, spy_sma_window: int) -> tuple[pd.Series, pd.DataFrame]:
    weights = build_weights(close, lookback=LOOKBACK, skip=SKIP, top_fraction=TOP_FRACTION)
    common = close.index.intersection(weights.index)
    close_a = close.loc[common]
    weights_a = weights.loc[common]
    daily_ret = close_a.pct_change().fillna(0.0)

    spy = close_a["SPY"]
    spy_sma = spy.rolling(spy_sma_window).mean()
    exposure = pd.Series(1.0, index=close_a.index)
    exposure[spy < spy_sma] = 0.0
    exposure[spy.isna() | spy_sma.isna()] = 0.0

    cw, net_ret, _ = _apply_overlay(daily_ret, weights_a, exposure_factor=exposure)
    return net_ret, cw


def count_regime_flips_from_exposure(close: pd.DataFrame, spy_sma_window: int) -> int:
    spy = close["SPY"]
    spy_sma = spy.rolling(spy_sma_window).mean()
    exposure = pd.Series(1.0, index=spy.index)
    exposure[spy < spy_sma] = 0.0
    exposure[spy.isna() | spy_sma.isna()] = 0.0
    # count transitions
    flips = 0
    prev = None
    for e in exposure.values:
        if prev is not None and e != prev:
            flips += 1
        prev = e
    return flips


def load_gates() -> dict:
    import yaml

    with open(CONFIG_GATES, "r") as fh:
        return yaml.safe_load(fh) or {}


def fmt(v: float, d: int = 6) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "N/A"
    return f"{float(v):.{d}f}"


def evaluate() -> dict[str, Any]:
    # checks for immutability
    import subprocess

    checks = []

    def record(name: str, ok: bool, obs: Any = "", exp: Any = ""):
        checks.append({"name": name, "pass": bool(ok), "observed": obs, "expected": exp})

    close = load_close_from_cache(list(SYMBOLS))
    net_ret, cw = _eval_full_period(close, spy_sma_window=SMA_NEW)

    # metrics
    full_period_sharpe = sharpe_ratio(net_ret)
    max_dd = max_drawdown(net_ret)
    rolling63 = net_ret.iloc[-63:] if len(net_ret) >= 63 else net_ret
    rolling_63d_sharpe = sharpe_ratio(rolling63)
    cum63 = (1.0 + rolling63).cumprod()
    rolling_63d_max_dd = float((cum63 / cum63.expanding().max() - 1.0).min()) if len(cum63) > 0 else 0.0
    regime_flips = count_regime_flips_from_exposure(close, spy_sma_window=SMA_NEW)
    track_record_length = int(len(net_ret))
    psr_res = (
        compute_psr(
            net_ret,
            sr_target=PSR_TARGET_BACKTEST_SCALE,
            n_bootstrap=PSR_N_BOOTSTRAP,
            block_size=PSR_BLOCK_SIZE,
            seed=PSR_SEED,
        )
        if len(net_ret) >= 20
        else {"psr_normal": 0.0, "sharpe_se": 0.0}
    )
    psr_normal = float(psr_res.get("psr_normal", 0.0))
    sharpe_se = float(psr_res.get("sharpe_se", 0.0))
    sharpe_backtest_scale = float(backtest_sharpe_ratio(net_ret))

    gates_doc = load_gates()
    metric_values = {
        "paper_days": float(track_record_length),
        "paper_sharpe": float(full_period_sharpe),
        "rolling_sharpe_63d": float(rolling_63d_sharpe),
        "paper_max_dd": float(max_dd),
        "rolling_max_dd_63d": float(rolling_63d_max_dd),
        "regime_flips": float(regime_flips),
        "psr_normal": float(psr_normal),
    }
    gate_evals = evaluate_promotion_gates(metric_values, gates_doc.get("gates", []))
    grey_zone = gates_doc.get("psr_grey_zone") or {}
    decision_mapping = gates_doc.get("decision_mapping") or {}
    psr_zone = classify_psr(psr_normal, grey_zone)
    decision, rationale, conditions = map_decision(gate_evals, psr_normal, grey_zone, decision_mapping)

    # structural checks
    # 3. git status --porcelain data/ config/ empty
    res_dc = subprocess.run(["git", "status", "--porcelain", "data/", "config/"], cwd=REPO_ROOT, capture_output=True, text=True)
    record("git_status_data_config_clean", res_dc.stdout.strip() == "", res_dc.stdout.strip(), "")
    # 4. git diff --stat -- research/run_cycle6.py empty
    res_rc = subprocess.run(["git", "diff", "--stat", "--", "research/run_cycle6.py"], cwd=REPO_ROOT, capture_output=True, text=True)
    record("git_diff_run_cycle6_empty", res_rc.stdout.strip() == "", res_rc.stdout.strip(), "")
    # 5. the declared Sharpe convention must match the implementation, exactly
    #    as src/simulation/evaluation.py refuses to evaluate when they differ.
    declared_convention = gates_doc.get("sharpe_convention") or {}
    declared_id = str(declared_convention.get("id", ""))
    record(
        "sharpe_convention_matches_implementation",
        declared_id == SHARPE_CONVENTION_ID,
        declared_id,
        SHARPE_CONVENTION_ID,
    )
    # 6. the PSR target must be the fixed backtest baseline that the gate
    #    definition itself documents (it names the baseline number in prose).
    psr_gate_doc = next(
        (g for g in gates_doc.get("gates", []) if g.get("name") == "psr"),
        {},
    )
    psr_gate_definition = str(psr_gate_doc.get("metric_definition", ""))
    record(
        "psr_target_is_documented_backtest_baseline",
        f"{PSR_TARGET_BACKTEST_SCALE:.4f}" in psr_gate_definition,
        f"{PSR_TARGET_BACKTEST_SCALE:.4f}",
        psr_gate_definition,
    )
    structural_pass = all(c["pass"] for c in checks)
    gates_pass = all(g["passed"] for g in gate_evals)
    # OVERALL is the verdict on this tool's *own* internal checks, exactly as
    # in every other read-only evaluation tool in this repository
    # (research/rolling_63d_gate_refresh.py, research/promotion_feasibility_
    # backtest.py, research/sectorrotation_long_sample_feasibility.py, ...)
    # and as required by the Cycle 920 acceptance criterion 2 ("OVERALL: PASS
    # only if all internal structural checks pass"). The candidate's
    # promotion verdict is the separate Decision (GO / NO-GO / INCONCLUSIVE)
    # reported below; the two are independent axes and are never conflated.
    overall_pass = structural_pass

    payload = {
        "candidate_id": CANDIDATE_ID,
        "cycle": CYCLE,
        "sma_new": SMA_NEW,
        "sma_baseline_incumbent": SPY_SMA_WINDOW,
        "git_rev": _git_hash(),
        "date": _today(),
        "psr_target": PSR_TARGET_BACKTEST_SCALE,
        "psr_target_source": PSR_TARGET_SOURCE,
        "psr_n_bootstrap": PSR_N_BOOTSTRAP,
        "psr_block_size": PSR_BLOCK_SIZE,
        "psr_seed": PSR_SEED,
        "sharpe_convention": SHARPE_CONVENTION_ID,
        "metrics": {
            "full_period_sharpe": float(full_period_sharpe),
            "rolling_63d_sharpe": float(rolling_63d_sharpe),
            "max_drawdown": float(max_dd),
            "rolling_63d_max_dd": float(rolling_63d_max_dd),
            "psr_normal": float(psr_normal),
            "psr_zone": psr_zone,
            "sharpe_se": sharpe_se,
            "sharpe_backtest_scale": sharpe_backtest_scale,
            "regime_flips": int(regime_flips),
            "track_record_length": int(track_record_length),
        },
        "gates": [
            {
                "name": g.name,
                "metric": g.metric,
                "value": g.value,
                "threshold": g.threshold,
                "comparison": g.comparison,
                "passed": g.passed,
                "source": g.source,
            }
            for g in gate_evals
        ],
        "decision": decision,
        "rationale": rationale,
        "conditions_for_reevaluation": conditions,
        "checks": checks,
        "structural_pass": structural_pass,
        "gates_pass": gates_pass,
        "candidate_promotable": bool(gates_pass),
        "failed_gates": [g.name for g in gate_evals if not g.passed],
        "overall_pass": overall_pass,
    }
    return payload


def render_report(payload: dict[str, Any]) -> str:
    lines = []
    lines.append(f"# TSMomentum SMA-175 Promotion Gate Eval ({payload['candidate_id']}, Cycle {payload['cycle']})")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Candidate: `{payload['candidate_id']}` (SMA window {payload['sma_new']})")
    lines.append(f"- Incumbent SMA window (run_cycle6): {payload['sma_baseline_incumbent']} (unchanged)")
    lines.append(f"- Git rev: {payload['git_rev']}")
    lines.append(f"- Date: {payload['date']}")
    lines.append(f"- Sharpe convention: `{payload['sharpe_convention']}`")
    lines.append(f"- PSR target: {payload['psr_target']:.4f} ({payload['psr_target_source']})")
    lines.append(
        f"- PSR bootstrap: n={payload['psr_n_bootstrap']}, block_size={payload['psr_block_size']}, seed={payload['psr_seed']}"
    )
    lines.append("")
    lines.append("## Full gate table")
    lines.append("")
    lines.append("| Gate | Metric | Value | Threshold | Comparison | Result | Source |")
    lines.append("|------|--------|-------|-----------|------------|--------|--------|")
    for g in payload["gates"]:
        res = "PASS" if g["passed"] else "FAIL"
        lines.append(f"| {g['name']} | {g['metric']} | {g['value']:.6f} | {g['threshold']:.6f} | {g['comparison']} | {res} | {g['source']} |")
    lines.append("")
    lines.append(f"- PSR zone: {payload['metrics']['psr_zone']}")
    lines.append(f"- Sharpe standard error: {payload['metrics']['sharpe_se']:.6f}")
    lines.append(f"- Sharpe on backtest-baseline scale (diagnostic): {payload['metrics']['sharpe_backtest_scale']:.6f}")
    lines.append(f"- Failed gates: {', '.join(payload['failed_gates']) or 'none'}")
    lines.append("")
    lines.append("## Decision mapping")
    lines.append("")
    lines.append(f"- Decision: **{payload['decision']}**")
    lines.append(
        f"- Candidate promotable (every promotion gate passes): {'YES' if payload['candidate_promotable'] else 'NO'}"
    )
    lines.append(f"- Rationale: {payload['rationale']}")
    lines.append(f"- Conditions for re-evaluation: {payload['conditions_for_reevaluation']}")
    lines.append("")
    lines.append("## Structural checks")
    lines.append("")
    for c in payload["checks"]:
        lines.append(f"- [{c['name']}]: {'PASS' if c['pass'] else 'FAIL'} (observed={c['observed']} expected={c['expected']})")
    lines.append("")
    lines.append(f"STRUCTURAL: {'PASS' if payload['structural_pass'] else 'FAIL'}")
    lines.append("")
    lines.append(
        "OVERALL is the verdict on this tool's own internal checks: it is PASS"
    )
    lines.append(
        "only when every internal check above passes. It is *not* the"
    )
    lines.append(
        "candidate's promotion verdict: that is the Decision above"
    )
    lines.append(
        "(GO / NO-GO / INCONCLUSIVE), which is reported independently."
    )
    lines.append("")
    lines.append(f"OVERALL: {'PASS' if payload['overall_pass'] else 'FAIL'}")
    lines.append("")
    return "\n".join(lines)


def render_experiment(payload: dict[str, Any]) -> str:
    lines = []
    lines.append(f"# Experiment: SMA-175 full promotion gate eval ({payload['candidate_id']}, Cycle {payload['cycle']})")
    lines.append("")
    lines.append("Read-only evaluation of SMA-175 candidate against full promotion gate suite from config/promotion_gates.yaml.")
    lines.append("")
    lines.append(f"- Decision: {payload['decision']}")
    lines.append(f"- full_period_sharpe: {payload['metrics']['full_period_sharpe']:.6f}")
    lines.append(f"- rolling_63d_sharpe: {payload['metrics']['rolling_63d_sharpe']:.6f}")
    lines.append(f"- max_drawdown: {payload['metrics']['max_drawdown']:.6f}")
    lines.append(f"- rolling_63d_max_dd: {payload['metrics']['rolling_63d_max_dd']:.6f}")
    lines.append(f"- psr_normal: {payload['metrics']['psr_normal']:.6f}")
    lines.append(f"- psr_target: {payload['psr_target']:.4f}")
    lines.append(f"- psr_target_source: {payload['psr_target_source']}")
    lines.append(f"- sharpe_se: {payload['metrics']['sharpe_se']:.6f}")
    lines.append(f"- sharpe_backtest_scale: {payload['metrics']['sharpe_backtest_scale']:.6f}")
    lines.append(f"- psr_zone: {payload['metrics']['psr_zone']}")
    lines.append(f"- regime_flips: {payload['metrics']['regime_flips']}")
    lines.append(f"- track_record_length: {payload['metrics']['track_record_length']}")
    lines.append(f"- failed_gates: {', '.join(payload['failed_gates']) or 'none'}")
    lines.append(f"- structural_pass: {payload['structural_pass']}")
    lines.append(
        f"- candidate_promotable (every promotion gate passes): {payload['candidate_promotable']}"
    )
    lines.append(
        f"- OVERALL: {'PASS' if payload['overall_pass'] else 'FAIL'} (verdict on the tool's own internal checks)"
    )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="print the measurement without writing the report and experiment files",
    )
    args = parser.parse_args(argv)
    payload = evaluate()
    report = render_report(payload)
    exp = render_experiment(payload)
    if not args.no_report:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
        OUT_REPORT.write_text(report, encoding="utf-8")
        OUT_EXP.write_text(exp, encoding="utf-8")
    print(f"STRUCTURAL: {'PASS' if payload['structural_pass'] else 'FAIL'}")
    print(f"OVERALL: {'PASS' if payload['overall_pass'] else 'FAIL'}")
    print(f"REPORT: {OUT_REPORT if not args.no_report else '(not written: --no-report)'}")
    print(f"EXPERIMENT: {OUT_EXP if not args.no_report else '(not written: --no-report)'}")
    # print full gate table summary
    for g in payload["gates"]:
        print(f"GATE|{g['name']}|{g['metric']}|{g['value']}|{g['threshold']}|{g['comparison']}|{'PASS' if g['passed'] else 'FAIL'}")
    print(f"PSR_TARGET|{payload['psr_target']}")
    print(f"DECISION|{payload['decision']}")
    print(f"CANDIDATE_PROMOTABLE|{'YES' if payload['candidate_promotable'] else 'NO'}")
    return 0 if payload["overall_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
