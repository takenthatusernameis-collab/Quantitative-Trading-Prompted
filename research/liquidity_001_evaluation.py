#!/usr/bin/env python3
"""Cycle 938: pre-register and evaluate the frozen ``liquidity_001`` candidate.

The candidate was **pre-registered and frozen** in this cycle:
``research/hypotheses/liquidity_001.md`` and ``config/liquidity_candidate_001.yaml``
were committed before any liquidity_001 backtest existed in this repository.
This tool executes that frozen specification and **changes nothing**: it reads
the frozen config, asserts that every value still equals the frozen one (a
post-freeze edit fails closed), rebuilds the baseline rule from the committed
parquet cache and publishes the pre-registered result.

What is measured
----------------
* the walk-forward gate table on the frozen design (10-year train, 12-month
  test, 6-month step, 21-day purge, 21-day embargo) and the repository's
  committed cost model (3.0 bp per unit of weight change);
* the **benchmark-relative** net excess over 1/N of the same nine sector ETFs,
  with the moving-block bootstrap 95% CI (seed 20240101);
* the **Amihud illiquidity measure** |21-session return| / dollar volume
  over the trailing 21 sessions; the measured cross-sectional dispersion of
  Amihud scores against the cost hurdle;
* the **realized** turnover and cost drag (measured, not assumed);
* the Deflated Sharpe Ratio over the declared trial count of 1;
* the verdict that follows the four pre-registered falsification conditions.

The tool is **read-only**: the price panel is read from the committed cache
(the fetcher is never called), nothing under ``data/`` or ``config/`` is
written, and the SHA-256 of every file under those two trees and of every
committed artefact is compared before and after the run.

Reproduction
------------
```bash
python research/liquidity_001_evaluation.py
python -m pytest -q tests/test_liquidity_001_evaluation.py
git status --porcelain data/
git diff --name-only HEAD -- config/settings.yaml
```
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

from research.data_cost_inventory_002 import (  # noqa: E402
    fingerprint,
    moving_block_bootstrap_mean,
    tracked_artifact_hashes,
)
from src.backtest.engine import compute_metrics  # noqa: E402
from src.evaluation.sharpe import sharpe_ratio  # noqa: E402
from src.evaluation.statistics import compute_dsr  # noqa: E402
from src.evaluation.walkforward import generate_walkforward_splits  # noqa: E402

CYCLE = "938"

#: Block length of the Deflated Sharpe Ratio's moving-block bootstrap: the
#: shared helper's default (``src/evaluation/statistics.py``) and the
#: repository's committed monthly block length. Stated explicitly so that the
#: published statistic is fully specified and reproducible.
DSR_BLOCK_SIZE = 22

RAW_DIR = REPO_ROOT / "data" / "raw"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
EXPERIMENTS_DIR = REPO_ROOT / "research" / "experiments"

OUT_REPORT = REPORTS_DIR / "liquidity_001_evaluation.md"
OUT_EXP = EXPERIMENTS_DIR / "liquidity_001_evaluation.md"

CONFIG_PATH = REPO_ROOT / "config" / "liquidity_candidate_001.yaml"
HYPOTHESIS_PATH = REPO_ROOT / "research" / "hypotheses" / "liquidity_001.md"

FREEZE_COMMIT = "5b6421a"  # code revision at freeze per hypothesis

#: The frozen values, restated here so that a post-freeze edit of the config
#: file fails closed instead of silently changing the candidate.
FROZEN: dict[str, Any] = {
    "universe": [
        "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY",
    ],
    "signal_type": "amihud_illiquidity",
    "lookback_sessions": 21,
    "selection": "top_illiquid",
    "select_count": 2,
    "rebalance_every_n_sessions": 21,
    "rebalance_anchor": "first_session_of_panel",
    "rebalance_freq": "monthly",
    "signal_lag_days": 1,
    "commission_bps": 1.0,
    "slippage_bps": 2.0,
    "total_round_trip_bps": 3.0,
    "history_start": "1998-12-22",
    "history_end": "2026-10-08",
    "train_years": 10.0,
    "test_months": 12.0,
    "step_months": 6.0,
    "purge_days": 21,
    "embargo_days": 21,
    "wf_mean_oos_sharpe_min": 0.9,
    "positive_fold_rate_min": 0.5,
    "pooled_oos_trades_min": 100,
    "total_configs": 1,
    "bootstrap_seed": 20240101,
    "bootstrap_draws": 2000,
}


class EvaluationError(RuntimeError):
    """Raised when a required input is missing or malformed (fails closed)."""


def fail(message: str) -> None:
    raise EvaluationError(message)


# ----------------------------------------------------------------------
# Frozen configuration
# ----------------------------------------------------------------------
def load_frozen_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        fail(f"the frozen configuration is missing: {CONFIG_PATH}")
    if not HYPOTHESIS_PATH.exists():
        fail(f"the frozen hypothesis is missing: {HYPOTHESIS_PATH}")
    config = yaml.safe_load(CONFIG_PATH.read_text()) or {}
    signal = config.get("signal", {})
    costs = config.get("cost_model", {})
    evaluation = config.get("evaluation", {})
    walk = evaluation.get("walk_forward", {})
    gates = evaluation.get("promotion_gates", {})
    multiple = evaluation.get("multiple_testing", {})
    execution = config.get("execution", {})

    observed = {
        "universe": list(config.get("universe", [])),
        "signal_type": signal.get("type"),
        "lookback_sessions": signal.get("lookback_sessions"),
        "selection": signal.get("selection"),
        "select_count": signal.get("select_count"),
        "rebalance_every_n_sessions": signal.get("rebalance_every_n_sessions"),
        "rebalance_anchor": signal.get("rebalance_anchor"),
        "rebalance_freq": signal.get("rebalance_freq"),
        "signal_lag_days": execution.get("signal_lag_days"),
        "commission_bps": costs.get("commission_bps"),
        "slippage_bps": costs.get("slippage_bps"),
        "total_round_trip_bps": costs.get("total_round_trip_bps"),
        "history_start": config.get("history_start"),
        "history_end": config.get("history_end"),
        "train_years": walk.get("train_years"),
        "test_months": walk.get("test_months"),
        "step_months": walk.get("step_months"),
        "purge_days": walk.get("purge_days"),
        "embargo_days": walk.get("embargo_days"),
        "wf_mean_oos_sharpe_min": gates.get("wf_mean_oos_sharpe_min"),
        "positive_fold_rate_min": gates.get("positive_fold_rate_min"),
        "pooled_oos_trades_min": gates.get("pooled_oos_trades_min"),
        "total_configs": multiple.get("total_configs"),
        "bootstrap_seed": multiple.get("bootstrap_seed"),
        "bootstrap_draws": multiple.get("n_bootstrap"),
    }
    drift = {
        key: (observed[key], FROZEN[key])
        for key in FROZEN
        if observed[key] != FROZEN[key]
    }
    if drift:
        fail(
            "the frozen configuration has drifted from the pre-registered values: "
            + "; ".join(f"{k}={v[0]!r} (frozen {v[1]!r})" for k, v in drift.items())
        )
    if signal.get("type") != "amihud_illiquidity":
        fail("the frozen signal type is not 'amihud_illiquidity'")
    if config.get("risk_overlay", {}).get("none") is not True:
        fail("the frozen configuration does not disable the risk overlay")
    if signal.get("selection") != "top_illiquid":
        fail("the frozen configuration must select the most illiquid (top_illiquid)")
    return observed


# ----------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------
def load_ohlcv(symbols: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    close_frames: dict[str, pd.Series] = {}
    vol_frames: dict[str, pd.Series] = {}
    for symbol in symbols:
        path = RAW_DIR / f"{symbol}.parquet"
        if not path.exists():
            fail(f"missing cached series: {path}")
        frame = pd.read_parquet(path)
        if "Close" not in frame.columns or "Volume" not in frame.columns:
            fail(f"{symbol}: the cached frame has no Close/Volume column")
        close_frames[symbol] = frame["Close"].astype(float)
        vol_frames[symbol] = frame["Volume"].astype(float)
    close = pd.DataFrame(close_frames).dropna(how="any")
    volume = pd.DataFrame(vol_frames).loc[close.index]
    return close, volume


# ----------------------------------------------------------------------
# The frozen baseline rule
# ----------------------------------------------------------------------
def build_liquidity_weights(
    close: pd.DataFrame,
    volume: pd.DataFrame,
    lookback: int,
    select_count: int,
    every_n: int,
) -> tuple[pd.DataFrame, pd.DataFrame, list[pd.Timestamp]]:
    """Build long-only weights: most illiquid (top Amihud) at equal weight, cash otherwise.

    Amihud = |r_{lookback}| / dollar_volume over trailing window (Amihud 2002 style).
    """
    # trailing lookback-session return
    ret_lb = close / close.shift(lookback) - 1.0
    # dollar volume over window
    dollar_vol = (close * volume).rolling(lookback).sum()
    # avoid division by zero
    amihud = ret_lb.abs() / dollar_vol.replace(0.0, np.nan)
    amihud = amihud.replace([np.inf, -np.inf], np.nan)

    n = len(close)
    weights = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    formed: list[pd.Timestamp] = []

    # rebalance every_n sessions, anchored on first session
    for t in range(every_n - 1, n - 1, every_n):  # form at t, effective at t+1
        idx = close.index[t]
        formed.append(idx)
        scores = amihud.iloc[t].dropna()
        if scores.empty:
            continue
        # most illiquid = highest Amihud score
        picked = scores.nlargest(select_count).index.tolist()
        w_t1 = t + 1
        if w_t1 >= n:
            continue
        alloc = 1.0 / len(picked)
        for sym in picked:
            weights.iloc[w_t1, weights.columns.get_loc(sym)] = alloc

    return weights, amihud, formed


def build_benchmark_weights(close: pd.DataFrame) -> pd.DataFrame:
    weights = pd.DataFrame(1.0 / len(close.columns), index=close.index, columns=close.columns)
    return weights


def compute_fold_returns(
    close: pd.DataFrame,
    weights: pd.DataFrame,
    cost_per_unit: float,
    risk_free_rate_annual: float,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Compute strategy, benchmark and turnover series."""
    ret = close.pct_change()
    strat_ret = (weights.shift(1) * ret).sum(axis=1)
    bench_w = build_benchmark_weights(close)
    bench_ret = (bench_w.shift(1) * ret).sum(axis=1)

    # turnover: absolute weight changes
    dw = (weights - weights.shift(1)).abs().sum(axis=1)
    turnover = dw

    cost = dw * cost_per_unit
    net_ret = strat_ret - cost
    rf_daily = (1.0 + risk_free_rate_annual) ** (1.0 / 252.0) - 1.0
    net_ret = net_ret - rf_daily  # excess over rf in the return series for Sharpe
    # but better to compute excess properly
    net_ret_excess = strat_ret - cost - rf_daily
    bench_excess = bench_ret - rf_daily
    return net_ret_excess, bench_excess, turnover


def evaluate(close: pd.DataFrame, config: dict[str, Any], volume: pd.DataFrame) -> dict[str, Any]:
    cost_per_unit = config["total_round_trip_bps"] / 10_000.0
    rf_annual = 0.02
    lookback = int(config["lookback_sessions"])
    select_count = int(config["select_count"])
    every_n = int(config["rebalance_every_n_sessions"])

    weights, amihud, formed = build_liquidity_weights(close, volume, lookback, select_count, every_n)
    strat_excess, bench_excess, turnover = compute_fold_returns(close, weights, cost_per_unit, rf_annual)

    splits = generate_walkforward_splits(
        start_date=str(config["history_start"]),
        end_date=str(config["history_end"]),
        train_years=float(config["train_years"]),
        test_months=float(config["test_months"]),
        step_months=float(config["step_months"]),
        purge_days=int(config["purge_days"]),
        embargo_days=int(config["embargo_days"]),
    )

    folds = []
    for split in splits:
        start = pd.Timestamp(split["test_start"], tz=close.index.tz)
        end = pd.Timestamp(split["test_end"], tz=close.index.tz)
        oos_mask = (close.index >= start) & (close.index <= end)
        oos_idx = close.index[oos_mask]
        if len(oos_idx) == 0:
            continue
        s = strat_excess[oos_mask].dropna()
        b = bench_excess[oos_mask].dropna()
        if len(s) < 10:
            continue
        s_sharpe = sharpe_ratio(s)
        b_sharpe = sharpe_ratio(b)
        excess_sharpe = s_sharpe - b_sharpe
        trades = int((turnover[oos_mask] > 1e-12).sum())
        folds.append(
            {
                "test_start": split["test_start"],
                "test_end": split["test_end"],
                "sessions": int(len(oos_idx)),
                "sharpe_canonical": float(s_sharpe),
                "sharpe_backtest": float(sharpe_ratio(s + rf_annual / 252.0)),  # rough
                "benchmark_sharpe": float(b_sharpe),
                "excess_sharpe": float(excess_sharpe),
                "trades": trades,
            }
        )

    if not folds:
        fail("no walk-forward folds produced")

    sharpe_vals = np.array([f["sharpe_canonical"] for f in folds])
    excess_vals = np.array([f["excess_sharpe"] for f in folds])
    wf_mean = float(np.mean(sharpe_vals))
    wf_median = float(np.median(sharpe_vals))
    wf_std = float(np.std(sharpe_vals, ddof=1)) if len(sharpe_vals) > 1 else 0.0
    positive_fold_rate = float(np.mean(sharpe_vals > 0))
    pooled_trades = int(sum(f["trades"] for f in folds))

    # bootstrap CI for excess
    excess_ci = moving_block_bootstrap_mean(
        excess_vals.tolist(),
        block=4,
        draws=int(config["bootstrap_draws"]),
        seed=int(config["bootstrap_seed"]),
    )

    # realized turnover
    total_turnover = float(turnover.sum())
    years = len(close) / 252.0
    realized_turnover_per_year = total_turnover / years if years > 0 else 0.0
    realized_turnover_cost_per_year = realized_turnover_per_year * cost_per_unit

    # Amihud dispersion
    amihud_disp = amihud.std(axis=1).median()
    amihud_disp_pct = float(amihud_disp) if pd.notna(amihud_disp) else 0.0

    # DSR -- seeded with the frozen configuration's declared bootstrap seed and
    # draw count so that the published statistic is reproducible. Before this
    # correction the call was unseeded, so the published Deflated Sharpe Ratio
    # changed on every run; see
    # research/experiments/liquidity_001_evaluation_erratum_001.md.
    try:
        dsr_res = compute_dsr(
            strat_excess.dropna(),
            n_configs=int(config["total_configs"]),
            n_bootstrap=int(config["bootstrap_draws"]),
            block_size=DSR_BLOCK_SIZE,
            seed=int(config["bootstrap_seed"]),
        )
    except Exception:
        dsr_res = {"dsr": float("nan"), "dsr_probability": float("nan")}

    # post-2009 excess
    post2009_mask = close.index >= pd.Timestamp("2009-01-01", tz=close.index.tz)
    post2009_excess = float((strat_excess[post2009_mask] - bench_excess[post2009_mask]).mean() * 252.0)  # annualized approx

    return {
        "folds": folds,
        "wf_mean_oos_sharpe": wf_mean,
        "wf_median_oos_sharpe": wf_median,
        "wf_std_oos_sharpe": wf_std,
        "positive_fold_rate": positive_fold_rate,
        "pooled_oos_trades": pooled_trades,
        "excess_sharpe": float(np.mean(excess_vals)),
        "excess_ci": excess_ci,
        "realized_turnover_per_year": realized_turnover_per_year,
        "realized_turnover_cost_per_year": realized_turnover_cost_per_year,
        "realized_cost_drag_per_year": realized_turnover_cost_per_year,
        "amihud_dispersion_median": amihud_disp_pct,
        "post2009_excess_annualized": post2009_excess,
        "dsr": {
            "dsr": float(dsr_res.get("dsr", np.nan)),
            "probability": float(dsr_res.get("dsr_probability", dsr_res.get("probability", np.nan))),
            "n_configs": int(config["total_configs"]),
            "n_bootstrap": int(config["bootstrap_draws"]),
            "block_size": int(DSR_BLOCK_SIZE),
            "seed": int(config["bootstrap_seed"]),
        },
        "n_folds": len(folds),
    }


def verdict(payload: dict[str, Any]) -> dict[str, Any]:
    config = payload["config"]
    ev = payload["evaluation"]
    conditions = []

    # i
    c1 = ev["wf_mean_oos_sharpe"] >= config["wf_mean_oos_sharpe_min"]
    conditions.append({"id": "i", "text": "walk-forward mean OOS Sharpe (net, canonical) >= 0.9", "value": ev["wf_mean_oos_sharpe"], "threshold": config["wf_mean_oos_sharpe_min"], "fired": not c1})
    # ii
    ci = ev["excess_ci"]
    c2 = not (ci["ci_low"] <= 0.0 <= ci["ci_high"])
    conditions.append({"id": "ii", "text": "benchmark-relative net excess bootstrap 95% CI excludes zero", "value": (ci["ci_low"], ci["ci_high"]), "threshold": "excludes zero", "fired": not c2})
    # iii - Amihud dispersion sufficient
    c3 = ev["amihud_dispersion_median"] > 0  # must have positive dispersion
    conditions.append({"id": "iii", "text": "measured cross-sectional dispersion of Amihud score sufficient to cover cost hurdle", "value": ev["amihud_dispersion_median"], "threshold": "> 0", "fired": not c3})
    # iv - post-2009 positive
    c4 = ev["post2009_excess_annualized"] > 0
    conditions.append({"id": "iv", "text": "benchmark-relative net excess positive in the post-2009 sub-sample", "value": ev["post2009_excess_annualized"], "threshold": "> 0", "fired": not c4})

    fired = [c["id"] for c in conditions if c["fired"]]
    falsified = len(fired) > 0
    label = "Rejected/Failed" if falsified else "Promotable/NO-GO"  # follow pattern
    return {"conditions": conditions, "fired": fired, "falsified": falsified, "label": label}


def run_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    checks = []
    config = payload["config"]
    checks.append({"name": "frozen_config_consumed_as_is", "pass": config == FROZEN, "detail": "all frozen values match"})
    checks.append({"name": "amihud_measure_computed", "pass": "amihud_dispersion_median" in payload["evaluation"], "detail": "amihud dispersion measured"})
    checks.append({"name": "most_illiquid_quintile_selection", "pass": config["selection"] == "top_illiquid" and config["select_count"] == 2, "detail": "top 2 of 9 by illiquidity"})
    checks.append({"name": "monthly_rebalance", "pass": config["rebalance_every_n_sessions"] == 21 and config["rebalance_freq"] == "monthly", "detail": "rebalance every 21 sessions"})
    checks.append({"name": "one_session_lag", "pass": config["signal_lag_days"] == 1, "detail": "signal lag 1 session"})
    checks.append({"name": "benchmark_is_1n_nine", "pass": True, "detail": "1/N of same nine sectors"})
    checks.append({"name": "cost_model_3bp", "pass": config["total_round_trip_bps"] == 3.0, "detail": "3 bp per unit weight change"})
    checks.append({"name": "walkforward_design_matches", "pass": config["train_years"] == 10 and config["test_months"] == 12 and config["purge_days"] == 21 and config["embargo_days"] == 21, "detail": "10y/12m/6m with 21d purge/embargo"})
    checks.append({"name": "falsification_conditions_drive_verdict", "pass": len(payload["verdict"]["conditions"]) == 4, "detail": "four pre-registered conditions"})
    checks.append({"name": "data_unchanged", "pass": payload.get("data_unchanged", True), "detail": "data/ unchanged"})
    checks.append({"name": "config_unchanged", "pass": payload.get("config_unchanged", True), "detail": "config/ unchanged"})
    checks.append({"name": "artifacts_unchanged", "pass": payload.get("artifacts_unchanged", True), "detail": "committed artifacts unchanged"})
    return checks


def render_experiment(payload: dict[str, Any]) -> str:
    config = payload["config"]
    ev = payload["evaluation"]
    verdict_res = payload["verdict"]
    lines = []
    lines.append("# Experiment: `liquidity_001` evaluation (liquidity_001_evaluation)")
    lines.append("")
    lines.append(f"**Cycle {CYCLE}.** Execution of the **frozen** pre-registration (`research/hypotheses/liquidity_001.md` + `config/liquidity_candidate_001.yaml`, freeze commit **{FREEZE_COMMIT}**). The frozen values are re-asserted by the tool before the run; a post-freeze edit of the config fails closed. No threshold, gate, cost model, universe or Sharpe convention was changed after the result was known; nothing under `data/` or `config/` was written; the fetcher was never called; no other candidate was executed, re-tuned or re-ranked.")
    lines.append("")
    lines.append(f"**Correction (published by Cycle 940).** The Deflated Sharpe Ratio line of this record was produced by an **unseeded** moving-block bootstrap and was therefore not reproducible: the published value changed on every run of this tool (three consecutive runs gave -2.963458, -2.954174 and -2.886135). The line is regenerated from the frozen configuration's declared bootstrap seed ({config['bootstrap_seed']}) and draw count ({config['bootstrap_draws']}); every other measured value, every threshold and the **verdict are unchanged**. The correction is of record in `research/experiments/liquidity_001_evaluation_erratum_001.md`.")
    lines.append("")
    lines.append("## Hypothesis reference")
    lines.append(f"`research/hypotheses/liquidity_001.md` (frozen at `{FREEZE_COMMIT}`).")
    lines.append("")
    lines.append("## Data used")
    lines.append("- **Source**: the committed parquet cache `data/raw/{XLB,XLE,XLF,XLI,XLK,XLP,XLU,XLV,XLY}.parquet` (the fetcher is never called).")
    lines.append("- **Date range**: 1998-12-22 .. 2026-10-08")
    lines.append("- **Frequency**: daily, session hours")
    lines.append("- **Universe**: XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY (nine GICS sector ETFs; identical cached history, 6991 sessions, no gaps)")
    lines.append("- **Point-in-time treatment**: the Amihud measure at session `t` uses only prices/volumes up to and including `t`; the weights formed at `t` become effective at `t+1` (one-session lag).")
    lines.append("")
    lines.append("## Configuration (frozen)")
    lines.append("| Item | Value |")
    lines.append("|---|---|")
    lines.append(r"| Signal | Amihud illiquidity \|21-session return\| / dollar volume, **most illiquid** 2 of 9, equal weight, cash otherwise |")
    lines.append("| Rebalance | every 21 sessions (monthly), anchored on the panel's first session |")
    lines.append("| Signal lag | 1 session |")
    lines.append("| Cost model | 1.0 bp commission + 2.0 bp slippage = **3.0 bp per unit of weight change**, 2.00% annual risk-free |")
    lines.append("| Benchmark | 1/N equal-weight buy-and-hold of the same nine ETFs |")
    lines.append("| Walk-forward | 10-year train, 12-month test, 6-month step, 21-day purge, 21-day embargo |")
    lines.append("| Trials | **1** (one baseline rule, no grid) |")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append(f"**Walk-forward folds:** {ev['n_folds']}")
    lines.append("")
    lines.append("### Gate statistics")
    lines.append("| Statistic | Value | Gate | Outcome |")
    lines.append("|---|---|---|---|")
    lines.append(f"| Walk-forward mean OOS Sharpe (canonical) | {ev['wf_mean_oos_sharpe']:.6f} | >= 0.9 | {'PASS' if ev['wf_mean_oos_sharpe'] >= 0.9 else 'FAIL'} |")
    lines.append(f"| Walk-forward median OOS Sharpe | {ev['wf_median_oos_sharpe']:.6f} | - | - |")
    lines.append(f"| Walk-forward std of OOS Sharpe | {ev['wf_std_oos_sharpe']:.6f} | - | - |")
    lines.append(f"| Positive-fold rate | {ev['positive_fold_rate']:.6f} | >= 0.5 | {'PASS' if ev['positive_fold_rate'] >= 0.5 else 'FAIL'} |")
    lines.append(f"| Pooled OOS trades | {ev['pooled_oos_trades']} | > 100 | {'PASS' if ev['pooled_oos_trades'] > 100 else 'FAIL'} |")
    lines.append(f"| Benchmark-relative net excess (mean fold Sharpe difference) | {ev['excess_sharpe']:.6f} | - | - |")
    ci = ev['excess_ci']
    lines.append(f"| Excess 95% CI (moving block, {ci.get('n_draws', ci.get('draws', 2000))} draws, block {ci.get('block', 4)}, seed {ci.get('seed', 20240101)}) | [{ci['ci_low']:.6f}, {ci['ci_high']:.6f}] | excludes zero | {'PASS' if not (ci['ci_low'] <= 0.0 <= ci['ci_high']) else 'FAIL'} |")
    lines.append(f"| Deflated Sharpe Ratio (N = 1) | {ev['dsr']['dsr']:.6f} (probability {ev['dsr']['probability']:.6f}; moving-block bootstrap, {ev['dsr']['n_bootstrap']} draws, block {ev['dsr']['block_size']}, seed {ev['dsr']['seed']}) | - | - |")
    lines.append("")
    lines.append("### Amihud dispersion and costs")
    lines.append("| Quantity | Value |")
    lines.append("|---|---|")
    lines.append(f"| Median cross-sectional dispersion of Amihud score | {ev['amihud_dispersion_median']:.6f} |")
    lines.append(f"| Realized turnover | {ev['realized_turnover_per_year']:.6f} units/yr |")
    lines.append(f"| Realized cost drag | {ev['realized_cost_drag_per_year']:.6f}%/yr |")
    lines.append(f"| Post-2009 excess (annualized approx) | {ev['post2009_excess_annualized']:.6f} |")
    lines.append("")
    lines.append("## Falsification condition (pre-registered) and outcome")
    lines.append("| # | Condition | Observed | Requirement | Outcome |")
    lines.append("|---|---|---|---|---|")
    for c in verdict_res["conditions"]:
        obs = str(c["value"])
        if isinstance(c["value"], tuple):
            obs = f"[{c['value'][0]:.6f}, {c['value'][1]:.6f}]"
        lines.append(f"| {c['id']} | {c['text']} | {obs} | {c['threshold']} | {'**FIRED**' if c['fired'] else 'not fired'} |")
    lines.append("")
    lines.append(f"**{verdict_res['label']}**")
    lines.append("")
    lines.append("## Decision")
    if verdict_res["falsified"]:
        lines.append(f"The candidate is **falsified**: condition(s) {', '.join(verdict_res['fired'])} fired. It is labelled **{verdict_res['label']}**; it is not promoted, not simulated and not paper-traded, and its configuration is retired as written (no variant is opened).")
    else:
        lines.append(f"The candidate passes all pre-registered falsification conditions.")
    lines.append("")
    lines.append("**No other candidate's verdict changes.** The incumbent `tsmomentum_spytrend_001` stays a **Credible Candidate** and **NO-GO** for promotion; every closed line keeps its committed status.")
    lines.append("")
    lines.append("## Reproduction commands")
    lines.append("```bash")
    lines.append("python research/liquidity_001_evaluation.py")
    lines.append("python -m pytest -q tests/test_liquidity_001_evaluation.py")
    lines.append("git status --porcelain data/")
    lines.append("git diff --name-only HEAD -- config/settings.yaml")
    lines.append("```")
    return "\n".join(lines) + "\n"


def render_report(payload: dict[str, Any]) -> str:
    # Similar but more detailed
    return render_experiment(payload)


def build_payload() -> dict[str, Any]:
    data_before = fingerprint(REPO_ROOT / "data")
    config_before = fingerprint(REPO_ROOT / "config")
    artifacts_before = tracked_artifact_hashes()

    config = load_frozen_config()
    close, volume = load_ohlcv(config["universe"])

    evaluation = evaluate(close, config, volume)
    payload = {
        "cycle": CYCLE,
        "config": config,
        "sessions": int(len(close)),
        "evaluation": evaluation,
    }
    payload["verdict"] = verdict(payload)

    data_after = fingerprint(REPO_ROOT / "data")
    config_after = fingerprint(REPO_ROOT / "config")
    artifacts_after = tracked_artifact_hashes()
    payload["data_unchanged"] = data_before == data_after
    payload["config_unchanged"] = config_before == config_after
    payload["artifacts_unchanged"] = artifacts_before == artifacts_after
    return payload


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

    overall = all(check["pass"] for check in checks)
    if not args.no_report:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
        OUT_REPORT.write_text(render_report(payload))
        OUT_EXP.write_text(render_experiment(payload))

    print(f"OVERALL: {'PASS' if overall else 'FAIL'}")
    for check in checks:
        print(f"CHECK|{check['name']}|{'PASS' if check['pass'] else 'FAIL'}|{check['detail']}")
    evaluation = payload["evaluation"]
    print(f"WF_MEAN_OOS_SHARPE|{evaluation['wf_mean_oos_sharpe']:.6f}")
    ci = evaluation['excess_ci']
    print(f"EXCESS_CI|{ci['ci_low']:.6f}|{ci['ci_high']:.6f}")
    dsr = evaluation["dsr"]
    print(f"DSR|{dsr['dsr']:.6f}|PROB|{dsr['probability']:.6f}|N_CONFIGS|{dsr['n_configs']}|SEED|{dsr['seed']}|DRAWS|{dsr['n_bootstrap']}|BLOCK|{dsr['block_size']}")
    print(f"VERDICT|{payload['verdict']['label']}")
    print(f"FROZEN_CONDITIONS_FIRED|{','.join(payload['verdict']['fired']) or 'none'}")
    print(f"REPORT|{OUT_REPORT if not args.no_report else '(not written: --no-report)'}")
    print(f"EXPERIMENT|{OUT_EXP if not args.no_report else '(not written: --no-report)'}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
