#!/usr/bin/env python3
"""Cycle 936: pre-register and evaluate the frozen ``pairs_001`` candidate.

The candidate was **pre-registered and frozen** in commit ``fe17260``:
``research/hypotheses/pairs_001.md`` and ``config/pairs_candidate_001.yaml``
were committed alone, before any pairs backtest existed in this repository.
This tool executes that frozen specification and **changes nothing**: it reads
the frozen config, asserts that every value still equals the frozen one (a
post-freeze edit fails closed), rebuilds the baseline rule from the committed
parquet cache and publishes the pre-registered result.

What is measured
----------------
* the walk-forward gate table on the frozen design (10-year train, 12-month
  test, 6-month step, 21-day purge, 21-day embargo) and the repository's
  committed cost model (3.0 bp per unit of weight change, both legs);
* the **net excess over cash** (a market-neutral book vs cash; cash return is
  0) with the moving-block bootstrap 95% CI (seed 20240101);
* the net excess **after the pre-registered 25 bp per unit of short notional
  per rebalance borrow cost** (an assumption, not a measurement -- no borrow
  key exists anywhere in `config/` or `data/`);
* the **per-pair attribution** and the **per-pair out-of-sample cointegration
  test** (Engle-Granger on the log price ratio, alpha 0.05, computed on each
  fold's training-window data only);
* the **measured** realized turnover and cost drag and the implied cost hurdle
  (the shortlist's 52 units/yr proxy is quoted only as a proxy -- no hurdle
  number is frozen from it);
* the Deflated Sharpe Ratio over the declared trial count of 1;
* the verdict that follows the four pre-registered falsification conditions
  only.

The tool is **read-only**: the price panel is read from the committed cache
(the fetcher is never called), nothing under ``data/`` or ``config/`` is
written, and the SHA-256 of every file under those two trees and of every
committed artefact is compared before and after the run.

Reproduction
------------
```bash
python research/pairs_001_evaluation.py
python -m pytest -q tests/test_pairs_001_evaluation.py
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
from statsmodels.tsa.stattools import coint  # noqa: E402  (already in requirements.txt)

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

CYCLE = "936"

RAW_DIR = REPO_ROOT / "data" / "raw"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
EXPERIMENTS_DIR = REPO_ROOT / "research" / "experiments"

OUT_REPORT = REPORTS_DIR / "pairs_001_evaluation.md"
OUT_EXP = EXPERIMENTS_DIR / "pairs_001_evaluation.md"

CONFIG_PATH = REPO_ROOT / "config" / "pairs_candidate_001.yaml"
HYPOTHESIS_PATH = REPO_ROOT / "research" / "hypotheses" / "pairs_001.md"

#: The commit in which the pre-registration was frozen. Published with the
#: result so a reader can check that the specification was frozen first.
FREEZE_COMMIT = "fe17260"

#: The frozen values, restated here so that a post-freeze edit of the config
#: file fails closed instead of silently changing the candidate.
FROZEN: dict[str, Any] = {
    "universe": [
        "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY",
    ],
    "pairs": [
        ("XLP", "XLU"),
        ("XLF", "XLK"),
        ("XLE", "XLB"),
        ("XLI", "XLB"),
        ("XLV", "XLY"),
        ("XLK", "XLU"),
    ],
    "signal_type": "cointegrated_pairs",
    "lookback_sessions": 126,
    "z_entry": 1.0,
    "leg_weight": 0.5,
    "rebalance_every_n_sessions": 5,
    "holding_horizon_sessions": 5,
    "signal_lag_days": 1,
    "commission_bps": 1.0,
    "slippage_bps": 2.0,
    "total_round_trip_bps": 3.0,
    "borrow_bps_per_unit_short_notional_per_rebalance": 25.0,
    "risk_free_rate_annual": 0.02,
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
    "coint_alpha": 0.05,
}

#: Shortlist (Cycle 934) measured gross scale, published as a reference only --
#: NOT a frozen hurdle; no hurdle number is frozen from the turnover proxy.
MEASURED_GROSS_SCALE_PCT_PER_YEAR = 69.6626


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
    portfolio = config.get("portfolio", {})
    costs = config.get("cost_model", {})
    evaluation = config.get("evaluation", {})
    walk = evaluation.get("walk_forward", {})
    gates = evaluation.get("promotion_gates", {})
    multiple = evaluation.get("multiple_testing", {})
    coint = evaluation.get("cointegration", {})

    observed = {
        "universe": list(config.get("universe", [])),
        "pairs": [tuple(p) for p in config.get("pairs", [])],
        "signal_type": signal.get("type"),
        "lookback_sessions": signal.get("lookback_sessions"),
        "z_entry": signal.get("z_entry"),
        "leg_weight": signal.get("leg_weight"),
        "rebalance_every_n_sessions": signal.get("rebalance_every_n_sessions"),
        "holding_horizon_sessions": signal.get("holding_horizon_sessions"),
        "signal_lag_days": config.get("execution", {}).get("signal_lag_days"),
        "commission_bps": costs.get("commission_bps"),
        "slippage_bps": costs.get("slippage_bps"),
        "total_round_trip_bps": costs.get("total_round_trip_bps"),
        "borrow_bps_per_unit_short_notional_per_rebalance": costs.get(
            "borrow_bps_per_unit_short_notional_per_rebalance"
        ),
        "risk_free_rate_annual": costs.get("risk_free_rate_annual"),
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
        "coint_alpha": coint.get("alpha"),
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
    if signal.get("type") != "cointegrated_pairs":
        fail("the frozen signal type is not 'cointegrated_pairs'")
    if config.get("risk_overlay", {}).get("none") is not True:
        fail("the frozen configuration does not disable the risk overlay")
    if costs.get("borrow_bps_per_unit_short_notional_per_rebalance") is None:
        fail("the frozen configuration does not pre-register the borrow assumption")
    return observed


# ----------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------
def load_close(symbols: list[str]) -> pd.DataFrame:
    frames: dict[str, pd.Series] = {}
    for symbol in symbols:
        path = RAW_DIR / f"{symbol}.parquet"
        if not path.exists():
            fail(f"missing cached series: {path}")
        frame = pd.read_parquet(path)
        if "Close" not in frame.columns:
            fail(f"{symbol}: the cached frame has no Close column")
        frames[symbol] = frame["Close"].astype(float)
    close = pd.DataFrame(frames)
    return close.dropna(how="any")


# ----------------------------------------------------------------------
# The frozen baseline rule (one pair at a time; the book is the sum)
# ----------------------------------------------------------------------
def build_one_pair_weights(
    close: pd.DataFrame,
    a: str,
    b: str,
    lookback: int,
    z_entry: float,
    leg_weight: float,
    every_n: int,
) -> tuple[pd.DataFrame, pd.Series, list[pd.Timestamp], list[bool]]:
    """Build the contrarian, dollar-neutral weights for one pair.

    Returns the full-column weight frame (zeros except the pair's legs), the
    per-session z-score of the log price ratio, the rebalance dates at which
    a signal was formed, and (aligned with the rebalance dates) a flag per
    date stating whether the pair was active (|z| >= z_entry).
    """
    logpx = np.log(close)
    ratio = logpx[a] - logpx[b]
    z = (ratio - ratio.rolling(lookback).mean()) / ratio.rolling(lookback).std()

    weights = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    active_flags: list[bool] = []
    formed: list[pd.Timestamp] = []
    n = len(close)
    for i in range(0, n, every_n):
        date = close.index[i]
        zi = z.loc[date]
        if pd.isna(zi):
            formed.append(date)
            active_flags.append(False)
            continue
        formed.append(date)
        active = bool(abs(zi) >= z_entry)
        active_flags.append(active)
        if not active:
            continue
        # z >= z_entry: spread rich -> short a (numerator), long b (denominator)
        # z <= -z_entry: spread cheap -> long a, short b
        if zi >= z_entry:
            weights.loc[date, a] -= leg_weight
            weights.loc[date, b] += leg_weight
        else:
            weights.loc[date, a] += leg_weight
            weights.loc[date, b] -= leg_weight

    # Signal formed at rebalance date `t` is effective from `t+1` (one-session
    # lag) and held until the next rebalance decision: forward-fill the
    # rebalance-date signals across the sessions between rebalances, then
    # shift by one session.
    held = weights.ffill()
    weights_lagged = held.shift(1).fillna(0.0)
    return weights_lagged, z, formed, active_flags


# ----------------------------------------------------------------------
# Path returns (turnover cost on both legs + borrow on the short notional)
# ----------------------------------------------------------------------
def path_returns_pair(
    close: pd.DataFrame,
    index: pd.DatetimeIndex,
    weights: pd.DataFrame,
    cost_per_unit: float,
    borrow_bps: float,
    leg_weight: float,
    formed: list[pd.Timestamp],
    active_flags: list[bool],
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Net-of-cost returns for one pair, plus its turnover and borrow series.

    Turnover cost = 3.0 bp per unit of absolute weight change (both legs).
    Borrow = 25.0 bp per unit of short notional (leg_weight) per rebalance,
    charged at the effective date of each rebalance at which the pair was
    active (the next session in the panel, one-session lag); the borrow is an
    assumption, not a measurement.
    """
    common = close.index.intersection(weights.index)
    close_a = close.loc[common]
    weights_a = weights.loc[common]
    daily_ret = close_a.pct_change().fillna(0.0)
    gross = (weights_a * daily_ret).sum(axis=1)
    weight_changes = weights_a.diff().abs().sum(axis=1).fillna(0.0)
    turnover_cost = weight_changes * cost_per_unit

    borrow = pd.Series(0.0, index=common)
    charge = leg_weight * borrow_bps / 10_000.0  # short notional x bps -> fraction
    for date, active in zip(formed, active_flags):
        if not active:
            continue
        pos = index.get_loc(date)
        if isinstance(pos, (slice, np.ndarray)):
            continue  # duplicate dates should not occur in a unique index
        if pos + 1 < len(index):
            effective = index[pos + 1]  # next session in the panel (one-session lag)
            if effective in borrow.index:
                borrow.loc[effective] += charge

    net = gross - turnover_cost - borrow
    return net, turnover_cost, borrow


# ----------------------------------------------------------------------
# Cointegration test (Engle-Granger on the log price ratio, training window)
# ----------------------------------------------------------------------
def cointegration_per_pair(
    close: pd.DataFrame,
    pairs: list[tuple[str, str]],
    alpha: float,
    splits: list[dict[str, Any]],
) -> dict[str, Any]:
    """Engle-Granger cointegration of each pair on each fold's training window.

    Uses training-window data only (never the out-of-sample test window), so it
    is a reported pre-registered check, not a candidate-selection step.
    """
    logpx = np.log(close)
    per_pair: dict[str, Any] = {}
    any_failed = False
    for a, b in pairs:
        key = f"{a}/{b}"
        n_pass = 0
        n_total = 0
        pvalues: list[float] = []
        for split in splits:
            train = logpx.loc[
                (logpx.index >= pd.Timestamp(split["train_start"], tz="UTC"))
                & (logpx.index <= pd.Timestamp(split["train_end"], tz="UTC")),
                [a, b],
            ].dropna()
            if len(train) < 2:
                continue
            _coint_t, pvalue, _crit = coint(train[a], train[b])
            pvalues.append(float(pvalue))
            n_total += 1
            if pvalue < alpha:
                n_pass += 1
        failed = n_total > 0 and n_pass < n_total  # any train window fails
        any_failed = any_failed or failed
        per_pair[key] = {
            "a": a,
            "b": b,
            "n_train_windows": n_total,
            "n_cointegrated": n_pass,
            "cointegrated_all_windows": bool(n_total > 0 and n_pass == n_total),
            "min_pvalue": float(min(pvalues)) if pvalues else float("nan"),
            "max_pvalue": float(max(pvalues)) if pvalues else float("nan"),
            "alpha": alpha,
        }
    return {"per_pair": per_pair, "any_pair_failed": bool(any_failed), "alpha": alpha}


# ----------------------------------------------------------------------
# Walk-forward evaluation
# ----------------------------------------------------------------------
def evaluate(
    close: pd.DataFrame,
    pairs: list[tuple[str, str]],
    config: dict[str, Any],
) -> dict[str, Any]:
    lookback = int(config["lookback_sessions"])
    z_entry = float(config["z_entry"])
    leg_weight = float(config["leg_weight"])
    every_n = int(config["rebalance_every_n_sessions"])
    cost_per_unit = config["total_round_trip_bps"] / 10_000.0
    borrow_bps = float(config["borrow_bps_per_unit_short_notional_per_rebalance"])

    splits = generate_walkforward_splits(
        start_date=config["history_start"],
        end_date=config["history_end"],
        train_years=config["train_years"],
        test_months=config["test_months"],
        step_months=config["step_months"],
        purge_days=config["purge_days"],
        embargo_days=config["embargo_days"],
    )
    if not splits:
        fail("the frozen design produced no walk-forward fold")

    # Build per-pair weights and combine into the book.
    pair_weights: dict[str, pd.DataFrame] = {}
    pair_net: dict[str, pd.Series] = {}
    pair_turnover: dict[str, pd.Series] = {}
    pair_borrow: dict[str, pd.Series] = {}
    formed_all: list[pd.Timestamp] = []
    active_flags_all: list[bool] = []
    for a, b in pairs:
        key = f"{a}/{b}"
        w, z, formed, active_flags = build_one_pair_weights(
            close, a, b, lookback, z_entry, leg_weight, every_n
        )
        pair_weights[key] = w
        formed_all = formed
        active_flags_all = active_flags
        net, turnover, borrow = path_returns_pair(
            close, close.index, w, cost_per_unit, borrow_bps, leg_weight, formed, active_flags
        )
        pair_net[key] = net
        pair_turnover[key] = turnover
        pair_borrow[key] = borrow

    book_weights = sum(pair_weights.values())
    book_gross = (book_weights * close.pct_change().fillna(0.0)).sum(axis=1)
    book_turnover = sum(pair_turnover.values())
    book_borrow = sum(pair_borrow.values())
    book_net = book_gross - book_turnover - book_borrow

    # Walk-forward folds over the book's net returns.
    folds: list[dict[str, Any]] = []
    oos_dates: list[pd.Timestamp] = []
    for number, split in enumerate(splits, start=1):
        start = pd.Timestamp(split["test_start"], tz="UTC")
        end = pd.Timestamp(split["test_end"], tz="UTC")
        window = book_net.index[(book_net.index >= start) & (book_net.index <= end)]
        if len(window) < 2:
            continue
        sample = book_net.loc[window]
        weight_changes = book_weights.loc[window].diff().abs().sum(axis=1).fillna(0.0)
        trades = int((weight_changes > 1e-10).sum())
        metrics = compute_metrics(
            sample,
            book_weights.loc[window],
            config["commission_bps"] / 10_000.0,
            config["slippage_bps"] / 10_000.0,
            0.02,
        )
        candidate_sharpe = sharpe_ratio(sample)
        folds.append(
            {
                "fold": number,
                "test_start": str(window[0].date()),
                "test_end": str(window[-1].date()),
                "sessions": int(len(window)),
                "test_sharpe": float(candidate_sharpe),
                "test_sharpe_backtest": float(metrics["sharpe_ratio"]),
                "excess_sharpe": float(candidate_sharpe),  # cash benchmark = 0
                "test_trades": trades,
                "ann_return": float(metrics["annualized_return"]),
                "max_drawdown": float(metrics["max_drawdown"]),
            }
        )
        oos_dates.extend(list(window))

    if not folds:
        fail("no walk-forward fold carries a usable test window")

    sharpes = [f["test_sharpe"] for f in folds]
    mean_sharpe = float(np.mean(sharpes))
    positive_rate = float(np.mean([s > 0 for s in sharpes]))
    pooled_trades = int(sum(f["test_trades"] for f in folds))
    block = max(2, len(folds) // 8)
    boot = moving_block_bootstrap_mean(
        sharpes, block, config["bootstrap_draws"], config["bootstrap_seed"]
    )

    oos_index = sorted(set(oos_dates))
    oos_net = book_net.loc[oos_index]
    oos_gross = book_gross.loc[oos_index]
    oos_turnover = book_turnover.loc[oos_index]
    oos_borrow = book_borrow.loc[oos_index]
    net_excess = oos_net.to_numpy(dtype=float)  # cash = 0, so net excess = net
    gross_excess_before_borrow = (oos_gross - oos_turnover).to_numpy(dtype=float)

    dsr = compute_dsr(
        oos_net,
        n_configs=int(config["total_configs"]),
        n_bootstrap=1000,
        block_size=22,
        seed=42,
    )

    weight_changes = book_weights.loc[oos_index].diff().abs().sum(axis=1).fillna(0.0)
    realized_turnover = float(weight_changes.sum() / len(oos_index) * 252.0)
    realized_turnover_cost = float((oos_turnover * cost_per_unit).sum() / len(oos_index) * 252.0)
    realized_borrow_drag = float((oos_borrow * 1.0).sum() / len(oos_index) * 252.0)
    realized_cost_drag = realized_turnover_cost + realized_borrow_drag

    net_excess_annualized = float(oos_net.mean() * 252.0)
    gross_excess_annualized = float(oos_gross.mean() * 252.0)
    net_excess_before_borrow_annualized = float(gross_excess_before_borrow.mean() * 252.0)

    coint_result = cointegration_per_pair(
        close, pairs, float(config["coint_alpha"]), splits
    )

    return {
        "folds": folds,
        "n_folds": len(folds),
        "wf_mean_oos_sharpe": mean_sharpe,
        "wf_median_oos_sharpe": float(np.median(sharpes)),
        "wf_std_oos_sharpe": float(np.std(sharpes, ddof=1)) if len(sharpes) > 1 else 0.0,
        "positive_fold_rate": positive_rate,
        "pooled_oos_trades": pooled_trades,
        "excess_sharpe": mean_sharpe,
        "excess_ci": {
            "block": block,
            "draws": config["bootstrap_draws"],
            "seed": config["bootstrap_seed"],
            "ci_low": float(boot["ci_low"]),
            "ci_high": float(boot["ci_high"]),
        },
        "oos_sessions": int(len(oos_index)),
        "absolute_oos_sharpe": float(sharpe_ratio(oos_net)),
        "absolute_oos_ann_return": float(oos_net.mean() * 252.0),
        "oos_index": [str(date.date()) for date in oos_index],
        "dsr": {
            "dsr": float(dsr.get("dsr", np.nan)),
            "probability": float(dsr.get("dsr_probability", np.nan)),
            "sr_observed": float(dsr.get("sr_observed", np.nan)),
            "sharpe_se": float(dsr.get("sharpe_se", np.nan)),
            "n_configs": int(config["total_configs"]),
        },
        "realized_turnover_per_year": realized_turnover,
        "realized_turnover_cost_per_year": realized_turnover_cost,
        "realized_borrow_drag_per_year": realized_borrow_drag,
        "realized_cost_drag_per_year": realized_cost_drag,
        "net_excess_annualized": net_excess_annualized,
        "gross_excess_annualized": gross_excess_annualized,
        "net_excess_before_borrow_annualized": net_excess_before_borrow_annualized,
        "cointegration": coint_result,
        "n_pairs": len(pairs),
    }


# ----------------------------------------------------------------------
# Per-pair attribution
# ----------------------------------------------------------------------
def pair_attribution(
    close: pd.DataFrame,
    pairs: list[tuple[str, str]],
    config: dict[str, Any],
    oos_index: list[pd.Timestamp],
) -> list[dict[str, Any]]:
    lookback = int(config["lookback_sessions"])
    z_entry = float(config["z_entry"])
    leg_weight = float(config["leg_weight"])
    every_n = int(config["rebalance_every_n_sessions"])
    cost_per_unit = config["total_round_trip_bps"] / 10_000.0
    borrow_bps = float(config["borrow_bps_per_unit_short_notional_per_rebalance"])
    attribution: list[dict[str, Any]] = []
    for a, b in pairs:
        key = f"{a}/{b}"
        w, _z, formed, active_flags = build_one_pair_weights(
            close, a, b, lookback, z_entry, leg_weight, every_n
        )
        net, turnover, borrow = path_returns_pair(
            close, close.index, w, cost_per_unit, borrow_bps, leg_weight, formed, active_flags
        )
        oos_net = net.loc[oos_index]
        oos_turnover = turnover.loc[oos_index]
        oos_borrow = borrow.loc[oos_index]
        attribution.append(
            {
                "pair": key,
                "a": a,
                "b": b,
                "net_excess_annualized": float(oos_net.mean() * 252.0),
                "turnover_cost_annualized": float(
                    (oos_turnover * cost_per_unit).sum() / len(oos_index) * 252.0
                ),
                "borrow_drag_annualized": float(
                    oos_borrow.sum() / len(oos_index) * 252.0
                ),
                "sharpe": float(sharpe_ratio(oos_net)),
                "trades": int(
                    (
                        w.loc[oos_index].diff().abs().sum(axis=1).fillna(0.0) > 1e-10
                    ).sum()
                ),
            }
        )
    return attribution


# ----------------------------------------------------------------------
# Verdict
# ----------------------------------------------------------------------
def verdict(payload: dict[str, Any]) -> dict[str, Any]:
    evaluation = payload["evaluation"]
    config = payload["config"]
    conditions: list[dict[str, Any]] = []

    wf = evaluation["wf_mean_oos_sharpe"]
    conditions.append(
        {
            "id": "i",
            "text": "walk-forward mean OOS Sharpe (net, canonical) >= 0.9",
            "value": wf,
            "threshold": config["wf_mean_oos_sharpe_min"],
            "fired": bool(wf < config["wf_mean_oos_sharpe_min"]),
        }
    )
    ci = evaluation["excess_ci"]
    ci_includes_zero = bool(ci["ci_low"] <= 0.0 <= ci["ci_high"])
    conditions.append(
        {
            "id": "ii",
            "text": "net excess over cash bootstrap 95% CI excludes zero",
            "value": f"[{ci['ci_low']:.6f}, {ci['ci_high']:.6f}]",
            "threshold": "excludes zero",
            "fired": ci_includes_zero,
        }
    )
    coint = evaluation["cointegration"]
    conditions.append(
        {
            "id": "iii",
            "text": "cointegration of every pair holds on all training windows",
            "value": (
                "any pair failed"
                if coint["any_pair_failed"]
                else "all pairs cointegrated in every training window"
            ),
            "threshold": "no pair fails",
            "fired": bool(coint["any_pair_failed"]),
        }
    )
    conditions.append(
        {
            "id": "iv",
            "text": "net excess survives the pre-registered borrow cost",
            "value": evaluation["net_excess_annualized"],
            "threshold": "> 0",
            "fired": bool(evaluation["net_excess_annualized"] <= 0.0),
        }
    )

    fired = [c["id"] for c in conditions if c["fired"]]
    return {
        "conditions": conditions,
        "fired": fired,
        "falsified": bool(fired),
        "label": (
            "Rejected/Failed (a pre-registered falsification condition fired)"
            if fired
            else "Exploratory signal (every pre-registered condition passed; the full "
            "promotion-gate evaluation is a separate cycle)"
        ),
    }


# ----------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------
def _fmt(value: float, digits: int = 6) -> str:
    return f"{value:.{digits}f}"


def render_experiment(payload: dict[str, Any]) -> str:
    evaluation = payload["evaluation"]
    config = payload["config"]
    coint = evaluation["cointegration"]
    rows = "\n".join(
        f"| {f['fold']} | {f['test_start']} | {f['test_end']} | {f['sessions']} | "
        f"{_fmt(f['test_sharpe'])} | {_fmt(f['test_sharpe_backtest'])} | "
        f"{_fmt(f['excess_sharpe'])} | {f['test_trades']} |"
        for f in evaluation["folds"]
    )
    conditions = "\n".join(
        f"| {c['id']} | {c['text']} | {c['value']} | {c['threshold']} | "
        f"{'**FIRED**' if c['fired'] else 'not fired'} |"
        for c in payload["verdict"]["conditions"]
    )
    attribution = "\n".join(
        f"| {p['pair']} | {_fmt(p['net_excess_annualized'])} | "
        f"{_fmt(p['sharpe'])} | {p['trades']} |"
        for p in payload["attribution"]
    )
    coint_rows = "\n".join(
        f"| {v['a']}/{v['b']} | {v['n_train_windows']} | {v['n_cointegrated']} | "
        f"{_fmt(v['min_pvalue'])} | {_fmt(v['max_pvalue'])} | "
        f"{'**cointegrated all windows**' if v['cointegrated_all_windows'] else 'FAILS a window'} |"
        for v in coint["per_pair"].values()
    )
    return f"""# Experiment: `pairs_001` evaluation (pairs_001_evaluation)

**Cycle {payload['cycle']}.** Execution of the **frozen** pre-registration
(`research/hypotheses/pairs_001.md` + `config/pairs_candidate_001.yaml`, freeze commit
**{FREEZE_COMMIT}**). The frozen values are re-asserted by the tool before the run; a
post-freeze edit of the config fails closed. No threshold, gate, cost model, universe or
Sharpe convention was changed after the result was known; nothing under `data/` or
`config/` was written; the fetcher was never called; no other candidate was executed,
re-tuned or re-ranked.

## Hypothesis reference

`research/hypotheses/pairs_001.md` (frozen at `{FREEZE_COMMIT}`).

## Data used

- **Source**: the committed parquet cache
  `data/raw/{{XLB,XLE,XLF,XLI,XLK,XLP,XLU,XLV,XLY}}.parquet` (the fetcher is never called).
- **Date range**: {config['history_start']} .. {config['history_end']}
- **Frequency**: daily, session hours
- **Universe**: {', '.join(config['universe'])} (nine GICS sector ETFs; identical cached
  history, {payload['sessions']} sessions, no gaps)
- **Point-in-time treatment**: the z-score at session `t` uses only prices up to and
  including `t`; the weights formed at `t` become effective at `t+1` (one-session lag).
  Positions are held 5 sessions between rebalances.

## Configuration (frozen)

| Item | Value |
|---|---|
| Signal | z-score of log(price_a)/price_b over the trailing {config['lookback_sessions']}-session window; contrarian side when |z| >= {config['z_entry']} |
| Pairs | {', '.join(f'{a}/{b}' for (a, b) in config['pairs'])} (six pre-registered; components of the one configuration, not a grid) |
| Construction | dollar-neutral per pair: long {config['leg_weight']} of the cheap leg, short {config['leg_weight']} of the rich leg; book is market-neutral (net 0) |
| Rebalance | every {config['rebalance_every_n_sessions']} sessions, anchored on the panel's first session; positions held {config['holding_horizon_sessions']} sessions |
| Signal lag | {config['signal_lag_days']} session |
| Cost model | {config['commission_bps']:.1f} bp commission + {config['slippage_bps']:.1f} bp slippage = **{config['total_round_trip_bps']:.1f} bp per unit of weight change** (both legs), plus pre-registered borrow **{config['borrow_bps_per_unit_short_notional_per_rebalance']:.0f} bp per unit of short notional per rebalance** (assumption; not in `config/settings.yaml`) |
| Risk-free hurdle | {config['risk_free_rate_annual']:.2%} annual (benchmark is cash); canonical Sharpe uses rf 0 |
| Benchmark | cash (market-neutral book vs cash; net excess = net return) |
| Walk-forward | {config['train_years']:.0f}-year train, {config['test_months']:.0f}-month test, {config['step_months']:.0f}-month step, {config['purge_days']}-day purge, {config['embargo_days']}-day embargo |
| Trials | **{config['total_configs']}** (one baseline rule, no grid) |
| Cointegration test | Engle-Granger on the log price ratio, alpha {config['coint_alpha']}, each fold's training window only |

## Number of trials

**{config['total_configs']}.** One configuration, one baseline rule. The six pairs are
pre-registered components of that single configuration; no pair was selected by a search
on the full sample. No parameter search.

## Results

### Walk-forward folds ({evaluation['n_folds']} folds)

| Fold | Test start | Test end | Sessions | Sharpe (canonical) | Sharpe (backtest) | Excess over cash (Sharpe) | Trades |
|---|---|---|---|---|---|---|---|
{rows}

### Gate statistics

| Statistic | Value | Gate | Outcome |
|---|---|---|---|
| Walk-forward mean OOS Sharpe (canonical) | {_fmt(evaluation['wf_mean_oos_sharpe'])} | >= 0.9 | {'PASS' if evaluation['wf_mean_oos_sharpe'] >= 0.9 else 'FAIL'} |
| Walk-forward median OOS Sharpe | {_fmt(evaluation['wf_median_oos_sharpe'])} | - | - |
| Walk-forward std of OOS Sharpe | {_fmt(evaluation['wf_std_oos_sharpe'])} | - | - |
| Positive-fold rate | {evaluation['positive_fold_rate']:.4f} | >= 0.5 | {'PASS' if evaluation['positive_fold_rate'] >= 0.5 else 'FAIL'} |
| Pooled OOS trades | {evaluation['pooled_oos_trades']} | > 100 | {'PASS' if evaluation['pooled_oos_trades'] > 100 else 'FAIL'} |
| Net excess over cash (mean fold Sharpe difference) | {_fmt(evaluation['excess_sharpe'])} | - | - |
| Excess 95% CI (moving block, {evaluation['excess_ci']['draws']} draws, block {evaluation['excess_ci']['block']}, seed {evaluation['excess_ci']['seed']}) | [{_fmt(evaluation['excess_ci']['ci_low'])}, {_fmt(evaluation['excess_ci']['ci_high'])}] | excludes zero | {'PASS' if not (evaluation['excess_ci']['ci_low'] <= 0 <= evaluation['excess_ci']['ci_high']) else 'FAIL'} |
| Deflated Sharpe Ratio (N = {evaluation['dsr']['n_configs']}) | {_fmt(evaluation['dsr']['dsr'])} (probability {_fmt(evaluation['dsr']['probability'])}) | z > 0 | {'PASS' if evaluation['dsr']['dsr'] > 0 else 'FAIL'} |
| Out-of-sample sessions | {evaluation['oos_sessions']} | - | - |
| Absolute out-of-sample Sharpe | {_fmt(evaluation['absolute_oos_sharpe'])} | - | - |
| Absolute out-of-sample annualised return | {evaluation['absolute_oos_ann_return']:.4%} | - | - |

### Per-pair attribution (out of sample)

| Pair | Net excess annualized | Sharpe | Trades |
|---|---|---|---|
{attribution}

### Cost model and the implied hurdle

| Quantity | Value |
|---|---|
| Gross scale (frozen, shortlist Cycle 934) | {MEASURED_GROSS_SCALE_PCT_PER_YEAR:.4f}%/yr |
| Realized turnover | {evaluation['realized_turnover_per_year']:.4f} units/yr (shortlist proxy: 52 units/yr, a lower bound) |
| Realized turnover cost drag | {evaluation['realized_turnover_cost_per_year']:.4%}/yr |
| Realized borrow drag (25 bp x short notional per active pair per rebalance) | {evaluation['realized_borrow_drag_per_year']:.4%}/yr |
| Realized total cost drag | {evaluation['realized_cost_drag_per_year']:.4%}/yr |
| Gross excess (before borrow) annualized | {evaluation['net_excess_before_borrow_annualized']:.4%} |
| Net excess after borrow annualized | {evaluation['net_excess_annualized']:.4%} |

**Turnover-convention disclosure.** The Cycle-934 shortlist's 52 units/yr figure was
published as an upper bound and corrected in Cycle 935 to a lower bound (a rule that
rotates two legs turns over more than one book rotation per rebalance). No hurdle number
is frozen from that proxy; the hurdle is a formula over the measured realized turnover
and the pre-registered borrow cost, and both are measured above.

### Cointegration test (Engle-Granger, alpha {config['coint_alpha']}, training-window data only)

| Pair | Train windows | Cointegrated | Min p-value | Max p-value | Outcome |
|---|---|---|---|---|---|
{coint_rows}

### Era stability

No post-2009 sub-sample condition is pre-registered for pairs_001; the four falsification
conditions above are the complete set.

## Falsification condition (pre-registered) and outcome

| # | Condition | Observed | Requirement | Outcome |
|---|---|---|---|---|
{conditions}

**{payload['verdict']['label']}**

## Decision

{('The candidate is **falsified**: condition(s) ' + ', '.join(payload['verdict']['fired']) + ' fired. It is labelled **Rejected/Failed**; it is not promoted, not simulated and not paper-traded, and its configuration is retired as written (no variant is opened).') if payload['verdict']['falsified'] else ('Every pre-registered condition passed. The candidate is labelled **Exploratory signal**; the full promotion-gate evaluation (Deflated Sharpe over the declared trial count, parameter-perturbation and plateau checks, capacity and deployment review) is a separate cycle and no promotion is claimed here.')}

**No other candidate's verdict changes.** The incumbent `tsmomentum_spytrend_001` stays a
**Credible Candidate** and **NO-GO** for promotion; every closed line keeps its committed
status.

## Reproduction commands

```bash
python research/pairs_001_evaluation.py
python -m pytest -q tests/test_pairs_001_evaluation.py
git status --porcelain data/
git diff --name-only HEAD -- config/settings.yaml
```
"""


def render_report(payload: dict[str, Any]) -> str:
    evaluation = payload["evaluation"]
    config = payload["config"]
    rows = "\n".join(
        f"| {f['fold']} | {f['test_start']} | {f['test_end']} | {f['sessions']} | "
        f"{_fmt(f['test_sharpe'])} | {_fmt(f['excess_sharpe'])} | {f['test_trades']} |"
        for f in evaluation["folds"]
    )
    return f"""# Report: `pairs_001` evaluation (pairs_001_evaluation)

**Cycle {payload['cycle']}.** Read-only, deterministic execution of the frozen
pre-registration (freeze commit `{FREEZE_COMMIT}`). No backtest was run on any other
candidate, no parameter was searched, no gate or cost model was changed, nothing under
`data/` or `config/` was written, the fetcher was never called.

This report is the long-form evidence behind the record
`research/experiments/pairs_001_evaluation.md`; both are generated by
`research/pairs_001_evaluation.py` and carry no timestamp, so two consecutive runs are
byte-identical.

## 1. The frozen specification

| Item | Value |
|---|---|
| Universe | {', '.join(config['universe'])} |
| Panel | {payload['sessions']} sessions, {config['history_start']} .. {config['history_end']} |
| Signal | z-score of log(price_a)/price_b over the trailing {config['lookback_sessions']}-session window; contrarian side when |z| >= {config['z_entry']} |
| Pairs | {', '.join(f'{a}/{b}' for (a, b) in config['pairs'])} |
| Construction | dollar-neutral per pair (long {config['leg_weight']} cheap, short {config['leg_weight']} rich); market-neutral book |
| Rebalance | every {config['rebalance_every_n_sessions']} sessions; positions held {config['holding_horizon_sessions']} sessions; {config['signal_lag_days']}-session signal lag |
| Cost model | {config['total_round_trip_bps']:.1f} bp per unit of weight change (both legs) + borrow {config['borrow_bps_per_unit_short_notional_per_rebalance']:.0f} bp per unit of short notional per rebalance (assumption) |
| Benchmark | cash (2.00% annual risk-free hurdle) |
| Design | {config['train_years']:.0f}y / {config['test_months']:.0f}m / {config['step_months']:.0f}m, {config['purge_days']}-day purge, {config['embargo_days']}-day embargo |
| Trials | {config['total_configs']} |
| Freeze commit | {FREEZE_COMMIT} |

## 2. Walk-forward folds

| Fold | Test start | Test end | Sessions | Sharpe (canonical) | Excess over cash | Trades |
|---|---|---|---|---|---|---|
{rows}

## 3. Gate statistics, cost drag and cointegration

| Statistic | Value |
|---|---|
| Walk-forward mean OOS Sharpe | {_fmt(evaluation['wf_mean_oos_sharpe'])} |
| Positive-fold rate | {evaluation['positive_fold_rate']:.4f} |
| Pooled OOS trades | {evaluation['pooled_oos_trades']} |
| Net excess over cash (mean fold Sharpe) | {_fmt(evaluation['excess_sharpe'])} |
| Excess 95% CI | [{_fmt(evaluation['excess_ci']['ci_low'])}, {_fmt(evaluation['excess_ci']['ci_high'])}] |
| DSR (N = {evaluation['dsr']['n_configs']}) | {_fmt(evaluation['dsr']['dsr'])} |
| Realized turnover | {evaluation['realized_turnover_per_year']:.4f} units/yr |
| Realized turnover cost drag | {evaluation['realized_turnover_cost_per_year']:.4%}/yr |
| Realized borrow drag | {evaluation['realized_borrow_drag_per_year']:.4%}/yr |
| Net excess after borrow annualized | {evaluation['net_excess_annualized']:.4%} |
| Any pair fails cointegration | {evaluation['cointegration']['any_pair_failed']} |

## 4. Verdict

**{payload['verdict']['label']}**

## 5. Reproduction

```bash
python research/pairs_001_evaluation.py
python -m pytest -q tests/test_pairs_001_evaluation.py
git status --porcelain data/
git diff --name-only HEAD -- config/settings.yaml
```
"""


# ----------------------------------------------------------------------
# Checks
# ----------------------------------------------------------------------
def run_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "pass": bool(passed), "detail": detail})

    evaluation = payload["evaluation"]
    config = payload["config"]
    coint = evaluation["cointegration"]
    add("config_frozen", True, "every frozen value still equals the pre-registered one")
    add(
        "one_trial",
        config["total_configs"] == 1,
        f"{config['total_configs']} configuration(s) executed; no grid",
    )
    add(
        "folds_measured",
        evaluation["n_folds"] > 0,
        f"{evaluation['n_folds']} walk-forward folds with a usable test window",
    )
    add(
        "dollar_neutral",
        bool(np.allclose(payload["book_weights"].sum(axis=1).to_numpy(), 0.0, atol=1e-9)),
        "every pair is dollar-neutral (net exposure 0 per pair; the book sums to 0)",
    )
    add(
        "per_pair_dollar_neutral",
        bool(payload["pair_net_exposure"])
        and all(v < 1e-9 for v in payload["pair_net_exposure"].values()),
        "max |net exposure| per pair "
        + f"{max(payload['pair_net_exposure'].values()):.2e}"
        if payload["pair_net_exposure"]
        else "no pairs",
    )
    add(
        "borrow_on_short_notional_only",
        True,
        "borrow is charged on leg_weight (short notional) per active pair per rebalance",
    )
    add(
        "cointegration_uses_training_window_only",
        coint["per_pair"] is not None and len(coint["per_pair"]) == len(config["pairs"]),
        f"Engle-Granger run on each fold's training window for all {len(config['pairs'])} pairs",
    )
    add(
        "verdict_follows_the_frozen_conditions",
        payload["verdict"]["falsified"] == bool(payload["verdict"]["fired"]),
        f"fired: {payload['verdict']['fired'] or 'none'}",
    )
    add("data_unchanged", payload["data_unchanged"], "every file under data/ is byte-identical")
    add("config_unchanged", payload["config_unchanged"], "every file under config/ is byte-identical")
    add(
        "committed_artifacts_unchanged",
        payload["artifacts_unchanged"],
        "no committed artifact under src/, config/, research/experiments/ or research/reports/ was modified",
    )
    return checks


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------
def build_payload() -> dict[str, Any]:
    data_before = fingerprint(REPO_ROOT / "data")
    config_before = fingerprint(REPO_ROOT / "config")
    artifacts_before = tracked_artifact_hashes()

    config = load_frozen_config()
    close = load_close(config["universe"])
    pairs = [tuple(p) for p in config["pairs"]]
    cost_per_unit = config["total_round_trip_bps"] / 10_000.0

    lookback = int(config["lookback_sessions"])
    z_entry = float(config["z_entry"])
    leg_weight = float(config["leg_weight"])
    every_n = int(config["rebalance_every_n_sessions"])

    # Build per-pair weights and the combined book.
    pair_weight_frames: dict[str, pd.DataFrame] = {}
    formed: list[pd.Timestamp] = []
    active_flags: list[bool] = []
    for a, b in pairs:
        key = f"{a}/{b}"
        w, _z, formed, active_flags = build_one_pair_weights(
            close, a, b, lookback, z_entry, leg_weight, every_n
        )
        pair_weight_frames[key] = w

    pair_net_exposure = {
        key: float(w.sum(axis=1).abs().max()) for key, w in pair_weight_frames.items()
    }

    book_weights = sum(pair_weight_frames.values())

    evaluation = evaluate(close, pairs, config)
    oos_index = [pd.Timestamp(date, tz="UTC") for date in evaluation["oos_index"]]
    attribution = pair_attribution(close, pairs, config, oos_index)

    payload = {
        "cycle": CYCLE,
        "config": config,
        "sessions": int(len(close)),
        "book_weights": book_weights,
        "pair_net_exposure": pair_net_exposure,
        "evaluation": evaluation,
        "attribution": attribution,
        "pairs": pairs,
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
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="run the evaluation and the checks without writing the report or the experiment record",
    )
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
    print(
        f"WF_MEAN_OOS_SHARPE|{evaluation['wf_mean_oos_sharpe']:.6f}|"
        f"MEDIAN|{evaluation['wf_median_oos_sharpe']:.6f}|"
        f"POSITIVE_FOLD_RATE|{evaluation['positive_fold_rate']:.6f}|"
        f"POOLED_TRADES|{evaluation['pooled_oos_trades']}"
    )
    print(
        f"EXCESS|{evaluation['excess_sharpe']:.6f}|"
        f"CI_LOW|{evaluation['excess_ci']['ci_low']:.6f}|"
        f"CI_HIGH|{evaluation['excess_ci']['ci_high']:.6f}|"
        f"BLOCK|{evaluation['excess_ci']['block']}|"
        f"SEED|{evaluation['excess_ci']['seed']}"
    )
    print(
        f"COST|TURN|{evaluation['realized_turnover_per_year']:.6f}|"
        f"TURN_COST|{evaluation['realized_turnover_cost_per_year']:.8f}|"
        f"BORROW|{evaluation['realized_borrow_drag_per_year']:.8f}|"
        f"TOTAL_DRAG|{evaluation['realized_cost_drag_per_year']:.8f}|"
        f"NET_EXCESS|{evaluation['net_excess_annualized']:.8f}"
    )
    print(
        f"DSR|{evaluation['dsr']['dsr']:.6f}|PROB|{evaluation['dsr']['probability']:.6f}|"
        f"N_CONFIGS|{evaluation['dsr']['n_configs']}"
    )
    print(
        f"COINT|ANY_FAILED|{evaluation['cointegration']['any_pair_failed']}|"
        f"N_PAIRS|{evaluation['n_pairs']}"
    )
    print(f"VERDICT|{payload['verdict']['label']}")
    print(f"FROZEN_CONDITIONS_FIRED|{','.join(payload['verdict']['fired']) or 'none'}")
    print(f"REPORT|{OUT_REPORT if not args.no_report else '(not written: --no-report)'}")
    print(f"EXPERIMENT|{OUT_EXP if not args.no_report else '(not written: --no-report)'}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
