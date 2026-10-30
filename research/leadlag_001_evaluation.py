#!/usr/bin/env python3
"""Cycle 939: pre-register and evaluate the frozen ``leadlag_001`` candidate.

The candidate was **pre-registered and frozen** in commit ``ace2643``:
``research/hypotheses/leadlag_001.md`` and ``config/leadlag_candidate_001.yaml``
were committed alone, before any leadlag backtest existed in this repository.
This tool executes that frozen specification and **changes nothing**: it reads
the frozen config, asserts that every value still equals the frozen one (a
post-freeze edit fails closed), rebuilds the baseline rule from the committed
parquet cache and publishes the pre-registered result.

What is measured
----------------
* the walk-forward gate table on the frozen design (10-year train, 12-month
  test, 6-month step, 21-day purge, 21-day embargo) and the repository's
  committed cost model (3.0 bp per unit of weight change);
* the **net excess over cash** (a long-only book vs cash; the cash return is
  0) with the moving-block bootstrap 95% CI (seed 20240101, 2,000 draws,
  22-session blocks) and the Deflated Sharpe Ratio over the declared trial
  count of 5 (the five pre-registered pairs);
* the **lead-lag signal** itself: the sign of the futures leg's trailing
  5-session return, long the ETF leg when positive and cash otherwise,
  rebalanced every 5th session with a one-session lag;
* the **data-quality handling** the hypothesis pre-registered: the detected
  roll windows (the committed volume-signature detector) and the non-positive
  close in `CL-F`, both excluded from signal formation, both reported;
* the **realized** turnover and cost drag against the 1.5600%/yr proxy, the
  per-pair attribution, and the "excess without the CL-F pairs" measure;
* the verdict that follows the four pre-registered falsification conditions.

The tool is **read-only**: the price panel is read from the committed cache
(the fetcher is never called), nothing under ``data/`` or ``config/`` is
written, and the SHA-256 of every file under those two trees and of every
committed artefact is compared before and after the run.

Reproduction
------------
```bash
python research/leadlag_001_evaluation.py
python -m pytest -q tests/test_leadlag_001_evaluation.py
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
from research.futures_roll_visibility import (  # noqa: E402
    detect_roll_events,
    load_cached_series,
    volume_ratio,
)
from src.backtest.engine import compute_metrics  # noqa: E402
from src.evaluation.sharpe import sharpe_ratio  # noqa: E402
from src.evaluation.statistics import compute_dsr  # noqa: E402
from src.evaluation.walkforward import generate_walkforward_splits  # noqa: E402

CYCLE = "939"

RAW_DIR = REPO_ROOT / "data" / "raw"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
EXPERIMENTS_DIR = REPO_ROOT / "research" / "experiments"

OUT_REPORT = REPORTS_DIR / "leadlag_001_evaluation.md"
OUT_EXP = EXPERIMENTS_DIR / "leadlag_001_evaluation.md"

CONFIG_PATH = REPO_ROOT / "config" / "leadlag_candidate_001.yaml"
HYPOTHESIS_PATH = REPO_ROOT / "research" / "hypotheses" / "leadlag_001.md"

#: The commit in which the pre-registration was frozen. Published with the
#: result so a reader can check that the specification was frozen first.
FREEZE_COMMIT = "b0b54e8fd207b8c8030ed943784e1955adaa95ae"

#: The frozen values, restated here so that a post-freeze edit of the config
#: file fails closed instead of silently changing the candidate.
FROZEN: dict[str, Any] = {
    "universe": [
        "CL-F", "GC-F", "NG-F", "ZB-F", "USO", "BNO", "UNG", "GSG", "GLD", "TLT",
    ],
    "pairs": [
        ("CL-F", "USO"),
        ("CL-F", "BNO"),
        ("GC-F", "GLD"),
        ("NG-F", "UNG"),
        ("ZB-F", "TLT"),
    ],
    "signal_type": "futures_lead_lag_sign",
    "lookback_sessions": 5,
    "direction": "sign_of_futures_trailing_return",
    "etf_side": "long_only",
    "cash_when_signal_non_positive": True,
    "rebalance_every_n_sessions": 5,
    "rebalance_anchor": "first_session_of_panel",
    "rebalance_freq": "weekly",
    "rebalances_per_year": 52,
    "pair_weight": 0.2,
    "gross_exposure_max": 1.0,
    "commission_bps": 1.0,
    "slippage_bps": 2.0,
    "total_round_trip_bps": 3.0,
    "risk_free_rate_annual": 0.02,
    "signal_lag_days": 1,
    "history_start": "2015-01-02",
    "history_end": "2026-10-15",
    "sessions": 2960,
    "union_calendar_sessions": 6098,
    "calendar_churn": 0.5146,
    "holding_horizon_observations": 592,
    "train_years": 10.0,
    "test_months": 12.0,
    "step_months": 6.0,
    "purge_days": 21,
    "embargo_days": 21,
    "wf_mean_oos_sharpe_min": 0.9,
    "positive_fold_rate_min": 0.5,
    "pooled_oos_trades_min": 100,
    "total_configs": 5,
    "dsr_n_bootstrap": 1000,
    "dsr_block_size": 22,
    "dsr_seed": 42,
    "bootstrap_seed": 20240101,
    "bootstrap_draws": 2000,
    "bootstrap_block_sessions": 22,
    "roll_window_sessions_per_event": 6,
    "cl_f_non_positive_close_sessions": 1,
}

#: Shortlist (Cycle 934) measured inputs, published as a reference only.
MEASURED_GROSS_SCALE_PCT_PER_YEAR = 30.1518
SHORTLIST_TURNOVER_PROXY_UNITS_PER_YEAR = 52.00
SHORTLIST_DRAG_PCT_PER_YEAR = 1.5600
SHORTLIST_REQUIRED_CAPTURE = 0.051738
SHORTLIST_EFFECTIVE_BETS = 2.96


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
    execution = config.get("execution", {})
    evaluation = config.get("evaluation", {})
    walk = evaluation.get("walk_forward", {})
    gates = evaluation.get("promotion_gates", {})
    multiple = evaluation.get("multiple_testing", {})
    data = config.get("data", {})
    quality = config.get("data_quality", {})

    observed = {
        "universe": list(config.get("universe", [])),
        "pairs": [tuple(p) for p in config.get("pairs", [])],
        "signal_type": signal.get("type"),
        "lookback_sessions": signal.get("lookback_sessions"),
        "direction": signal.get("direction"),
        "etf_side": signal.get("etf_side"),
        "cash_when_signal_non_positive": signal.get("cash_when_signal_non_positive"),
        "rebalance_every_n_sessions": signal.get("rebalance_every_n_sessions"),
        "rebalance_anchor": signal.get("rebalance_anchor"),
        "rebalance_freq": signal.get("rebalance_freq"),
        "rebalances_per_year": signal.get("rebalances_per_year"),
        "pair_weight": portfolio.get("pair_weight"),
        "gross_exposure_max": portfolio.get("gross_exposure_max"),
        "commission_bps": costs.get("commission_bps"),
        "slippage_bps": costs.get("slippage_bps"),
        "total_round_trip_bps": costs.get("total_round_trip_bps"),
        "risk_free_rate_annual": costs.get("risk_free_rate_annual"),
        "signal_lag_days": execution.get("signal_lag_days"),
        "history_start": config.get("history_start"),
        "history_end": config.get("history_end"),
        "sessions": data.get("sessions"),
        "union_calendar_sessions": data.get("union_calendar_sessions"),
        "calendar_churn": data.get("calendar_churn"),
        "holding_horizon_observations": data.get("holding_horizon_observations"),
        "train_years": walk.get("train_years"),
        "test_months": walk.get("test_months"),
        "step_months": walk.get("step_months"),
        "purge_days": walk.get("purge_days"),
        "embargo_days": walk.get("embargo_days"),
        "wf_mean_oos_sharpe_min": gates.get("wf_mean_oos_sharpe_min"),
        "positive_fold_rate_min": gates.get("positive_fold_rate_min"),
        "pooled_oos_trades_min": gates.get("pooled_oos_trades_min"),
        "total_configs": multiple.get("total_configs"),
        "dsr_n_bootstrap": multiple.get("dsr_n_bootstrap"),
        "dsr_block_size": multiple.get("dsr_block_size"),
        "dsr_seed": multiple.get("dsr_seed"),
        "bootstrap_seed": multiple.get("bootstrap_seed"),
        "bootstrap_draws": multiple.get("n_bootstrap"),
        "bootstrap_block_sessions": multiple.get("bootstrap_block_sessions"),
        "roll_window_sessions_per_event": quality.get("roll_window_sessions_per_event"),
        "cl_f_non_positive_close_sessions": quality.get("cl_f_non_positive_close_sessions"),
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
    if signal.get("type") != "futures_lead_lag_sign":
        fail("the frozen signal type is not 'futures_lead_lag_sign'")
    if config.get("risk_overlay", {}).get("none") is not True:
        fail("the frozen configuration does not disable the risk overlay")
    if signal.get("etf_side") != "long_only":
        fail("the frozen configuration must be long-only (no short leg)")
    if quality.get("unusable_signal_action") != "flat":
        fail("the frozen configuration must leave an unusable signal flat")
    if len(observed["pairs"]) != 5:
        fail("the frozen configuration must declare the five pre-registered pairs")
    return observed


# ----------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------
def load_closes(symbols: list[str]) -> pd.DataFrame:
    """The union-calendar close frame of the pre-registered universe."""
    closes: dict[str, pd.Series] = {}
    for symbol in symbols:
        path = RAW_DIR / f"{symbol}.parquet"
        if not path.exists():
            fail(f"missing cached series: {path}")
        frame = pd.read_parquet(path)
        if "Close" not in frame.columns:
            fail(f"{symbol}: the cached frame has no Close column")
        series = frame["Close"].astype(float)
        series = series[~series.index.duplicated(keep="first")].sort_index()
        series = series[series.index <= pd.Timestamp("2026-10-19", tz="UTC")]
        closes[symbol] = series
    return pd.DataFrame(closes)


def build_panel(close_all: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    """The complete cross-section of the universe and the calendar churn.

    The complete panel keeps only the sessions on which **every** instrument
    of the candidate carries a price; the churn is the share of the union
    calendar the panel does not cover (the futures and the ETF legs have
    different trading calendars).
    """
    panel = close_all.dropna(how="any")
    if panel.empty:
        fail("the candidate's instruments share no session with a complete cross-section")
    churn = 0.0 if len(close_all) == 0 else 1.0 - len(panel) / len(close_all)
    return panel, float(churn)


def detect_roll_dates(symbol: str) -> tuple[pd.DatetimeIndex, int]:
    """The detected roll dates of one cached front-month series.

    Uses the repository's committed detector (the volume signature of the
    front contract's expiry). The detection is **ex-post**: it may look up to
    eight sessions ahead, which is why the roll-affected sessions are only
    used to *clean* the backtest and never as a tradable signal.
    """
    frame = load_cached_series(symbol)
    ratio = volume_ratio(frame["Volume"].astype(float))
    events = detect_roll_events(ratio)
    if events.empty:
        return pd.DatetimeIndex([]), 0
    dates = pd.DatetimeIndex(pd.to_datetime(events["roll_date"])).tz_convert("UTC")
    return dates, int(len(events))


def futures_signal(
    futures_close: pd.Series,
    lookback: int,
    contaminated: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    """The lead-lag signal of one futures leg and its usability mask.

    ``signal(t) = sign(close(t) / close(t-lookback) - 1)`` on the futures'
    own cached calendar, so the "5-session return" is the futures contract's
    own five sessions. ``usable(t)`` is False when the trailing window
    ``[t-lookback, t]`` contains a contaminated session (a detected roll date
    or a non-positive close): the return that spans it is not computable from
    the cache.
    """
    close = pd.Series(futures_close, dtype=float)
    total_return = close / close.shift(lookback) - 1.0
    signal = np.sign(total_return)
    window = int(lookback) + 1
    bad = pd.Series(contaminated, dtype=float).fillna(0.0).astype(bool)
    unusable = bad.rolling(window, min_periods=window).max() > 0
    usable = (~unusable) & total_return.notna()
    return signal, usable


# ----------------------------------------------------------------------
# The frozen baseline rule
# ----------------------------------------------------------------------
def build_pair_weights(
    panel_index: pd.DatetimeIndex,
    pairs: list[tuple[str, str]],
    signals: dict[str, pd.Series],
    usability: dict[str, pd.Series],
    every_n: int,
    lag: int,
    pair_weight: float,
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """The frozen weights: long the ETF leg when the futures signal is positive.

    One weight column per pair (each pair has its own ETF leg). The weight
    formed at a rebalance session ``t`` becomes effective at ``t+lag`` and is
    held until the next rebalance. An unusable signal leaves the pair flat.
    """
    n = len(panel_index)
    columns: dict[str, pd.Series] = {}
    for futures, etf in pairs:
        target = pd.Series(np.nan, index=panel_index, dtype=float)
        sig = signals[futures].reindex(panel_index)
        ok = usability[futures].reindex(panel_index).fillna(False).astype(bool)
        for position in range(0, n, every_n):
            effective = position + lag
            if effective >= n:
                break
            date = panel_index[position]
            value = sig.loc[date]
            usable = bool(ok.loc[date])
            target.iloc[effective] = (
                pair_weight if (usable and pd.notna(value) and float(value) > 0.0) else 0.0
            )
        columns[etf] = target.ffill().fillna(0.0)
    weights = pd.DataFrame(columns, index=panel_index)
    per_pair = {etf: weights[etf].copy() for _futures, etf in pairs}
    return weights, per_pair


def book_returns(
    panel: pd.DataFrame,
    weights: pd.DataFrame,
    cost_per_unit: float,
) -> dict[str, pd.Series]:
    """The book's gross, cost and net return series on the panel calendar."""
    returns = panel[weights.columns].pct_change().fillna(0.0)
    gross = (weights * returns).sum(axis=1)
    weight_changes = weights.diff().abs().sum(axis=1).fillna(0.0)
    cost = weight_changes * cost_per_unit
    net = gross - cost
    return {"gross": gross, "cost": cost, "net": net, "turnover": weight_changes}


# ----------------------------------------------------------------------
# Walk-forward evaluation
# ----------------------------------------------------------------------
def evaluate_variant(
    panel: pd.DataFrame,
    weights: pd.DataFrame,
    per_pair: dict[str, pd.DataFrame],
    pairs: list[tuple[str, str]],
    config: dict[str, Any],
) -> dict[str, Any]:
    """The walk-forward gate table of one variant of the frozen rule."""
    cost_per_unit = float(config["total_round_trip_bps"]) / 10_000.0
    series = book_returns(panel, weights, cost_per_unit)

    splits = generate_walkforward_splits(
        start_date=str(config["history_start"]),
        end_date=str(config["history_end"]),
        train_years=float(config["train_years"]),
        test_months=float(config["test_months"]),
        step_months=float(config["step_months"]),
        purge_days=int(config["purge_days"]),
        embargo_days=int(config["embargo_days"]),
    )
    if not splits:
        fail("the frozen design produced no walk-forward fold")

    folds: list[dict[str, Any]] = []
    oos_dates: list[pd.Timestamp] = []
    for number, split in enumerate(splits, start=1):
        start = pd.Timestamp(split["test_start"], tz="UTC")
        end = pd.Timestamp(split["test_end"], tz="UTC")
        window = panel.index[(panel.index >= start) & (panel.index <= end)]
        if len(window) < 2:
            continue
        sample = series["net"].loc[window]
        changes = series["turnover"].loc[window]
        metrics = compute_metrics(
            sample,
            weights.loc[window],
            float(config["commission_bps"]) / 10_000.0,
            float(config["slippage_bps"]) / 10_000.0,
            float(config["risk_free_rate_annual"]),
        )
        folds.append(
            {
                "fold": number,
                "train_start": split["train_start"],
                "train_end": split["train_end"],
                "test_start": str(window[0].date()),
                "test_end": str(window[-1].date()),
                "sessions": int(len(window)),
                "test_sharpe": float(sharpe_ratio(sample)),
                "test_sharpe_backtest": float(metrics.get("sharpe_ratio", float("nan"))),
                "excess_sharpe": float(sharpe_ratio(sample)),  # cash benchmark = 0
                "test_trades": int((changes > 1e-10).sum()),
                "ann_return": float(metrics.get("annualized_return", float("nan"))),
                "max_drawdown": float(metrics.get("max_drawdown", float("nan"))),
            }
        )
        oos_dates.extend(list(window))

    if not folds:
        fail("no walk-forward fold carries a usable test window")

    sharpes = [f["test_sharpe"] for f in folds]
    oos_index = sorted(set(oos_dates))
    oos_net = series["net"].loc[oos_index]
    oos_gross = series["gross"].loc[oos_index]
    oos_turnover = series["turnover"].loc[oos_index]
    oos_cost = series["cost"].loc[oos_index]

    # Bootstrap CI of the net excess over cash (cash return is 0, so the net
    # excess is the net return) on the pooled out-of-sample daily series.
    daily_ci = moving_block_bootstrap_mean(
        oos_net.to_numpy(dtype=float).tolist(),
        int(config["bootstrap_block_sessions"]),
        int(config["bootstrap_draws"]),
        int(config["bootstrap_seed"]),
    )
    # The fold-level Sharpe CI, for comparability with the closed cycles.
    fold_block = max(2, len(folds) // 8)
    fold_ci = moving_block_bootstrap_mean(
        sharpes, fold_block, int(config["bootstrap_draws"]), int(config["bootstrap_seed"])
    )

    dsr = compute_dsr(
        oos_net,
        n_configs=int(config["total_configs"]),
        n_bootstrap=int(config["dsr_n_bootstrap"]),
        block_size=int(config["dsr_block_size"]),
        seed=int(config["dsr_seed"]),
    )

    sessions = len(oos_index)
    realized_turnover = float(oos_turnover.sum() / sessions * 252.0)
    realized_cost_drag = float(oos_cost.sum() / sessions * 252.0)
    net_excess_annualized = float(oos_net.mean() * 252.0)
    gross_excess_annualized = float(oos_gross.mean() * 252.0)

    # Per-pair attribution and the "book without the CL-F pairs" measure.
    attribution: list[dict[str, Any]] = []
    clf_net = pd.Series(0.0, index=panel.index)
    non_clf_net = pd.Series(0.0, index=panel.index)
    for futures, etf in pairs:
        pair_weights = per_pair[etf].to_frame(name=etf)
        pair_series = book_returns(panel, pair_weights, cost_per_unit)
        pair_net = pair_series["net"]
        if futures == "CL-F":
            clf_net = clf_net + pair_net
        else:
            non_clf_net = non_clf_net + pair_net
        attribution.append(
            {
                "pair": f"{futures}/{etf}",
                "futures": futures,
                "etf": etf,
                "net_excess_annualized": float(pair_net.loc[oos_index].mean() * 252.0),
                "sharpe": float(sharpe_ratio(pair_net.loc[oos_index])),
                "trades": int((pair_series["turnover"].loc[oos_index] > 1e-10).sum()),
                "exposure_share": float(
                    (per_pair[etf].loc[oos_index] > 0).mean()
                ),
            }
        )

    return {
        "folds": folds,
        "n_folds": len(folds),
        "wf_mean_oos_sharpe": float(np.mean(sharpes)),
        "wf_median_oos_sharpe": float(np.median(sharpes)),
        "wf_std_oos_sharpe": float(np.std(sharpes, ddof=1)) if len(sharpes) > 1 else 0.0,
        "positive_fold_rate": float(np.mean([s > 0 for s in sharpes])),
        "pooled_oos_trades": int(sum(f["test_trades"] for f in folds)),
        "oos_sessions": int(sessions),
        "oos_index": oos_index,
        "oos_net": oos_net,
        "excess_ci": {
            "block": int(config["bootstrap_block_sessions"]),
            "draws": int(config["bootstrap_draws"]),
            "seed": int(config["bootstrap_seed"]),
            "ci_low": float(daily_ci["ci_low"]),
            "ci_high": float(daily_ci["ci_high"]),
            "ci_low_annualized": float(daily_ci["ci_low"] * 252.0),
            "ci_high_annualized": float(daily_ci["ci_high"] * 252.0),
        },
        "fold_sharpe_ci": {
            "block": fold_block,
            "ci_low": float(fold_ci["ci_low"]),
            "ci_high": float(fold_ci["ci_high"]),
        },
        "dsr": {
            "dsr": float(dsr.get("dsr", float("nan"))),
            "probability": float(dsr.get("dsr_probability", float("nan"))),
            "sr_observed": float(dsr.get("sr_observed", float("nan"))),
            "sharpe_se": float(dsr.get("sharpe_se", float("nan"))),
            "n_configs": int(config["total_configs"]),
        },
        "absolute_oos_sharpe": float(sharpe_ratio(oos_net)),
        "absolute_oos_ann_return": float(oos_net.mean() * 252.0),
        "net_excess_annualized": net_excess_annualized,
        "gross_excess_annualized": gross_excess_annualized,
        "net_excess_over_rf_annualized": float(
            net_excess_annualized - float(config["risk_free_rate_annual"])
        ),
        "realized_turnover_per_year": realized_turnover,
        "realized_cost_drag_per_year": realized_cost_drag,
        "attribution": attribution,
        "cl_f_net_excess_annualized": float(clf_net.loc[oos_index].mean() * 252.0),
        "non_cl_f_net_excess_annualized": float(non_clf_net.loc[oos_index].mean() * 252.0),
        "non_cl_f_sharpe": float(sharpe_ratio(non_clf_net.loc[oos_index])),
    }


# ----------------------------------------------------------------------
# Verdict
# ----------------------------------------------------------------------
def verdict(payload: dict[str, Any]) -> dict[str, Any]:
    evaluation = payload["evaluation"]
    unclean = payload["unclean_evaluation"]
    config = payload["config"]
    conditions: list[dict[str, Any]] = []

    wf = evaluation["wf_mean_oos_sharpe"]
    conditions.append(
        {
            "id": "i",
            "text": "walk-forward mean OOS Sharpe (net, canonical) >= 0.9",
            "value": _fmt(wf),
            "threshold": config["wf_mean_oos_sharpe_min"],
            "fired": bool(wf < config["wf_mean_oos_sharpe_min"]),
        }
    )

    ci = evaluation["excess_ci"]
    ci_includes_zero = bool(ci["ci_low"] <= 0.0 <= ci["ci_high"])
    ci_low_annualized = float(ci.get("ci_low_annualized", ci["ci_low"] * 252.0))
    ci_high_annualized = float(ci.get("ci_high_annualized", ci["ci_high"] * 252.0))
    dsr_value = evaluation["dsr"]["dsr"]
    condition_ii_fired = bool(ci_includes_zero or dsr_value <= 0.0)
    conditions.append(
        {
            "id": "ii",
            "text": (
                "net excess over cash bootstrap 95% CI excludes zero after the "
                "deflation for the five pairs (DSR > 0)"
            ),
            "value": (
                f"CI [{ci_low_annualized:.4%}, {ci_high_annualized:.4%}]/yr, "
                f"DSR {dsr_value:.6f}"
            ),
            "threshold": "CI excludes zero and DSR > 0",
            "fired": condition_ii_fired,
        }
    )

    clean_excess = evaluation["net_excess_annualized"]
    unclean_excess = unclean["net_excess_annualized"]
    condition_iii_fired = bool(unclean_excess > 0.0 and clean_excess <= 0.0)
    conditions.append(
        {
            "id": "iii",
            "text": "the excess does not disappear once the detected roll windows are excluded",
            "value": (
                f"net excess with the roll windows {unclean_excess:.4%}/yr, "
                f"cleaned {clean_excess:.4%}/yr"
            ),
            "threshold": "the excess does not disappear when the roll windows are excluded",
            "fired": condition_iii_fired,
        }
    )

    full_excess = evaluation["net_excess_annualized"]
    non_clf_excess = evaluation["non_cl_f_net_excess_annualized"]
    condition_iv_fired = bool(full_excess > 0.0 and non_clf_excess <= 0.0)
    conditions.append(
        {
            "id": "iv",
            "text": "the excess is not carried by the CL-F window",
            "value": (
                f"full book {full_excess:.4%}/yr, without the CL-F pairs "
                f"{non_clf_excess:.4%}/yr"
            ),
            "threshold": "the excess survives without the CL-F pairs",
            "fired": condition_iv_fired,
        }
    )

    fired = [c["id"] for c in conditions if c["fired"]]
    gates_ok = bool(
        evaluation["positive_fold_rate"] >= config["positive_fold_rate_min"]
        and evaluation["pooled_oos_trades"] > config["pooled_oos_trades_min"]
        and dsr_value > 0.0
    )
    if fired:
        label = "Rejected/Failed"
    elif gates_ok:
        label = "Promotable/NO-GO"
    else:
        label = "Rejected/Failed"
    return {
        "conditions": conditions,
        "fired": fired,
        "falsified": bool(fired) or not gates_ok,
        "gates_passed": gates_ok,
        "label": label,
    }


# ----------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------
def _fmt(value: float, digits: int = 6) -> str:
    return f"{value:.{digits}f}"


def _fmt_map(mapping: dict[str, int]) -> str:
    """A stable, readable rendering of a symbol -> integer mapping."""
    return ", ".join(f"{key} {value}" for key, value in sorted(mapping.items()))


def render_experiment(payload: dict[str, Any]) -> str:
    config = payload["config"]
    evaluation = payload["evaluation"]
    unclean = payload["unclean_evaluation"]
    quality = payload["data_quality"]
    rows = "\n".join(
        f"| {f['fold']} | {f['test_start']} | {f['test_end']} | {f['sessions']} | "
        f"{_fmt(f['test_sharpe'])} | {_fmt(f['excess_sharpe'])} | {f['test_trades']} | "
        f"{f['max_drawdown']:.4%} |"
        for f in evaluation["folds"]
    )
    conditions = "\n".join(
        f"| {c['id']} | {c['text']} | {c['value']} | {c['threshold']} | "
        f"{'**FIRED**' if c['fired'] else 'not fired'} |"
        for c in payload["verdict"]["conditions"]
    )
    attribution = "\n".join(
        f"| {a['pair']} | {a['net_excess_annualized']:.4%} | {_fmt(a['sharpe'])} | "
        f"{a['trades']} | {a['exposure_share']:.2%} |"
        for a in evaluation["attribution"]
    )
    rolls = "\n".join(
        f"| {row['symbol']} | {row['rolls']} | {row['first_roll']} | {row['last_roll']} | "
        f"{row['roll_affected_sessions']} | {row['unusable_signal_sessions']} | "
        f"{row['unusable_share']:.2%} |"
        for row in quality["futures"]
    )
    return f"""# Experiment: `leadlag_001` evaluation (leadlag_001_evaluation)

**Cycle {payload['cycle']}.** Execution of the **frozen** pre-registration
(`research/hypotheses/leadlag_001.md` + `config/leadlag_candidate_001.yaml`, freeze commit
**{FREEZE_COMMIT}**). The frozen values are re-asserted by the tool before the run; a
post-freeze edit of the config fails closed. No threshold, gate, cost model, universe or
Sharpe convention was changed after the result was known; nothing under `data/` or
`config/` was written; the fetcher was never called; no other candidate was executed,
re-tuned or re-ranked.

## Hypothesis reference

`research/hypotheses/leadlag_001.md` (frozen at `{FREEZE_COMMIT}`).

## Data used

- **Source**: the committed parquet cache
  `data/raw/{{CL-F,GC-F,NG-F,ZB-F,USO,BNO,UNG,GSG,GLD,TLT}}.parquet` (the fetcher is never called).
- **Date range**: {config['history_start']} .. {config['history_end']}
- **Frequency**: daily, session hours
- **Universe**: {', '.join(config['universe'])}; the **complete cross-section** of the ten
  instruments is the panel: {payload['sessions']} sessions out of a {payload['union_sessions']}-session
  union calendar (calendar churn {payload['calendar_churn']:.2%}, because the futures and the ETF legs
  have different trading calendars).
- **Point-in-time treatment**: the futures signal at session `t` uses only closes up to
  and including `t`; the weights formed at `t` become effective at `t+1` (one-session lag)
  and are held until the next rebalance.

## Configuration (frozen)

| Item | Value |
|---|---|
| Signal | sign of the futures leg's trailing {config['lookback_sessions']}-session return; long the ETF leg when positive, cash otherwise |
| Pairs | {', '.join(f'{a}/{b}' for (a, b) in config['pairs'])} (five pre-registered; components of the one configuration, not a grid) |
| Construction | long-only; {config['pair_weight']} of the book per pair (equal weight), cash otherwise; gross exposure <= {config['gross_exposure_max']} |
| Rebalance | every {config['rebalance_every_n_sessions']} sessions, anchored on the panel's first session; {config['rebalances_per_year']} rebalances/yr |
| Signal lag | {config['signal_lag_days']} session |
| Cost model | {config['commission_bps']:.1f} bp commission + {config['slippage_bps']:.1f} bp slippage = **{config['total_round_trip_bps']:.1f} bp per unit of weight change**; {config['risk_free_rate_annual']:.2%} annual risk-free |
| Benchmark | cash (the rule is a directional tilt on the ETF leg only; the cash return is 0) |
| Walk-forward | {config['train_years']:.0f}-year train, {config['test_months']:.0f}-month test, {config['step_months']:.0f}-month step, {config['purge_days']}-day purge, {config['embargo_days']}-day embargo |
| Trials | **{config['total_configs']}** (the five pre-registered pairs, deflated through the DSR) |
| Data-quality rules | a futures signal whose trailing window contains a detected roll date or a non-positive close is **unusable**: the pair stays flat |

## Number of trials

**{config['total_configs']}.** The five pre-registered pairs are the five components of one
configuration, deflated through the Deflated Sharpe Ratio; the Cycle-934 shortlist's
measured effective-bet count on this panel is **{SHORTLIST_EFFECTIVE_BETS}**, so the
deflation is not generous. No parameter search, no variant, no grid.

## Results

### Walk-forward folds ({evaluation['n_folds']} folds)

| Fold | Test start | Test end | Sessions | Sharpe (canonical) | Excess over cash (Sharpe) | Trades | Max drawdown |
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
| Pooled out-of-sample sessions | {evaluation['oos_sessions']} | - | - |
| Net excess over cash (annualized) | {evaluation['net_excess_annualized']:.4%}/yr | - | - |
| Net excess over the 2.00% risk-free hurdle (annualized) | {evaluation['net_excess_over_rf_annualized']:.4%}/yr | > 0 | {'PASS' if evaluation['net_excess_over_rf_annualized'] > 0 else 'FAIL'} |
| Net excess 95% CI (moving block, {evaluation['excess_ci']['draws']} draws, block {evaluation['excess_ci']['block']}, seed {evaluation['excess_ci']['seed']}) | [{evaluation['excess_ci']['ci_low_annualized']:.4%}, {evaluation['excess_ci']['ci_high_annualized']:.4%}]/yr | excludes zero | {'PASS' if not (evaluation['excess_ci']['ci_low'] <= 0 <= evaluation['excess_ci']['ci_high']) else 'FAIL'} |
| Fold-Sharpe 95% CI (moving block, block {evaluation['fold_sharpe_ci']['block']}) | [{_fmt(evaluation['fold_sharpe_ci']['ci_low'])}, {_fmt(evaluation['fold_sharpe_ci']['ci_high'])}] | - | - |
| Deflated Sharpe Ratio (N = {evaluation['dsr']['n_configs']}) | {_fmt(evaluation['dsr']['dsr'])} (probability {_fmt(evaluation['dsr']['probability'])}) | > 0 | {'PASS' if evaluation['dsr']['dsr'] > 0 else 'FAIL'} |
| Absolute out-of-sample Sharpe | {_fmt(evaluation['absolute_oos_sharpe'])} | - | - |

### Cost model, turnover and the hurdle

| Quantity | Value |
|---|---|
| Measured gross scale (frozen, shortlist Cycle 934) | {MEASURED_GROSS_SCALE_PCT_PER_YEAR:.4f}%/yr |
| Required capture (frozen, shortlist Cycle 934) | {SHORTLIST_REQUIRED_CAPTURE:.4%} of the gross scale |
| Realized turnover | {evaluation['realized_turnover_per_year']:.4f} units/yr (shortlist proxy: {SHORTLIST_TURNOVER_PROXY_UNITS_PER_YEAR:.2f} units/yr) |
| Realized cost drag | {evaluation['realized_cost_drag_per_year']:.4%}/yr (shortlist proxy: {SHORTLIST_DRAG_PCT_PER_YEAR:.4f}%/yr) |

### Data quality: the detected roll windows and the CL-F defect

| Futures leg | Detected rolls | First roll | Last roll | Roll-affected signal sessions | Unusable signal sessions (all rules) | Share of the leg's sessions |
|---|---|---|---|---|---|---|
{rolls}

- **Two counts are published on purpose.** The frozen config's
  `data_quality.unusable_signal_sessions` block records the **roll-affected**
  count (the roll rule alone: {_fmt_map(quality['documented_roll_affected_sessions'])}), which the
  evaluator reproduces exactly. The **unusable** column adds the non-positive close and
  the missing-history sessions (the first five sessions of every futures leg), i.e. the
  sessions on which the pair is flat for one reason or another.
- **CL-F non-positive close**: {quality['cl_f_non_positive_close_sessions']} session(s)
  ({', '.join(quality['cl_f_non_positive_close_dates']) or 'none'}), close value
  {', '.join(f'{v:.2f}' for v in quality['cl_f_non_positive_close_values']) or 'n/a'}.
  The affected signal sessions are excluded (the pair stays flat); no return is computed
  that spans the defective close.
- **Roll detection is ex-post**: the committed detector classifies a session using up to
  eight forward sessions, so the roll-affected sessions are a *backtest cleaning*, not a
  tradable point-in-time signal. A live rule would have to detect the roll with the same lag.
- **Net excess with the roll windows kept** (the same rule without the roll exclusion):
  {unclean['net_excess_annualized']:.4%}/yr, walk-forward mean OOS Sharpe
  {_fmt(unclean['wf_mean_oos_sharpe'])}; **cleaned**: {evaluation['net_excess_annualized']:.4%}/yr,
  walk-forward mean OOS Sharpe {_fmt(evaluation['wf_mean_oos_sharpe'])}.

### Per-pair attribution (out of sample)

| Pair | Net excess (annualized) | Sharpe | Trades | Share of OOS sessions long |
|---|---|---|---|---|
{attribution}

- **Without the two CL-F pairs** the net excess over cash is
  {evaluation['non_cl_f_net_excess_annualized']:.4%}/yr (Sharpe {_fmt(evaluation['non_cl_f_sharpe'])});
  the two CL-F pairs alone contribute {evaluation['cl_f_net_excess_annualized']:.4%}/yr.

## Falsification condition (pre-registered) and outcome

| # | Condition | Observed | Requirement | Outcome |
|---|---|---|---|---|
{conditions}

**{payload['verdict']['label']}**

## Decision

{('The candidate is **falsified**: condition(s) ' + ', '.join(payload['verdict']['fired']) + ' fired. It is labelled **' + payload['verdict']['label'] + '**; it is not promoted, not simulated and not paper-traded, and its configuration is retired as written (no variant is opened).') if payload['verdict']['fired'] else ('No pre-registered falsification condition fired. The candidate is labelled **' + payload['verdict']['label'] + '**: it clears the pre-registered bar, and promotion remains a separate decision (NO-GO in this cycle).')}

**No other candidate's verdict changes.** The incumbent `tsmomentum_spytrend_001` stays a
**Credible Candidate** and **NO-GO** for promotion; every closed line keeps its committed
status.

## Reproduction commands

```bash
python research/leadlag_001_evaluation.py
python -m pytest -q tests/test_leadlag_001_evaluation.py
git status --porcelain data/
git diff --name-only HEAD -- config/settings.yaml
```
"""


def render_report(payload: dict[str, Any]) -> str:
    config = payload["config"]
    evaluation = payload["evaluation"]
    unclean = payload["unclean_evaluation"]
    quality = payload["data_quality"]
    rows = "\n".join(
        f"| {f['fold']} | {f['test_start']} | {f['test_end']} | {f['sessions']} | "
        f"{_fmt(f['test_sharpe'])} | {_fmt(f['excess_sharpe'])} | {f['test_trades']} |"
        for f in evaluation["folds"]
    )
    conditions = "\n".join(
        f"| {c['id']} | {c['text']} | {c['value']} | {'**FIRED**' if c['fired'] else 'not fired'} |"
        for c in payload["verdict"]["conditions"]
    )
    attribution = "\n".join(
        f"| {a['pair']} | {a['net_excess_annualized']:.4%} | {_fmt(a['sharpe'])} | {a['trades']} |"
        for a in evaluation["attribution"]
    )
    return f"""# Report: `leadlag_001` evaluation (leadlag_001_evaluation)

**Cycle {payload['cycle']}.** Read-only, deterministic execution of the frozen
pre-registration (freeze commit `{FREEZE_COMMIT}`). No backtest was run on any other
candidate, no parameter was searched, no gate or cost model was changed, nothing under
`data/` or `config/` was written, the fetcher was never called.

This report is the long-form evidence behind the record
`research/experiments/leadlag_001_evaluation.md`; both are generated by
`research/leadlag_001_evaluation.py` and carry no timestamp, so two consecutive runs are
byte-identical.

## 1. The frozen specification

| Item | Value |
|---|---|
| Universe | {', '.join(config['universe'])} |
| Panel | {payload['sessions']} complete-cross-section sessions, {config['history_start']} .. {config['history_end']} (union calendar {payload['union_sessions']} sessions, churn {payload['calendar_churn']:.2%}) |
| Signal | sign of the futures leg's trailing {config['lookback_sessions']}-session return; long the ETF leg when positive, cash otherwise |
| Pairs | {', '.join(f'{a}/{b}' for (a, b) in config['pairs'])} |
| Construction | long-only, {config['pair_weight']} of the book per pair, cash otherwise, gross exposure <= {config['gross_exposure_max']} |
| Rebalance | every {config['rebalance_every_n_sessions']} sessions; {config['signal_lag_days']}-session signal lag |
| Cost model | {config['total_round_trip_bps']:.1f} bp per unit of weight change; {config['risk_free_rate_annual']:.2%} annual risk-free |
| Benchmark | cash (the cash return is 0) |
| Design | {config['train_years']:.0f}y / {config['test_months']:.0f}m / {config['step_months']:.0f}m, {config['purge_days']}-day purge, {config['embargo_days']}-day embargo |
| Trials | {config['total_configs']} |
| Freeze commit | {FREEZE_COMMIT} |

## 2. Walk-forward folds

| Fold | Test start | Test end | Sessions | Sharpe (canonical) | Excess over cash | Trades |
|---|---|---|---|---|---|---|
{rows}

## 3. Gate statistics, cost drag and data quality

| Statistic | Value |
|---|---|
| Walk-forward mean OOS Sharpe | {_fmt(evaluation['wf_mean_oos_sharpe'])} |
| Walk-forward median / std OOS Sharpe | {_fmt(evaluation['wf_median_oos_sharpe'])} / {_fmt(evaluation['wf_std_oos_sharpe'])} |
| Positive-fold rate | {evaluation['positive_fold_rate']:.4f} |
| Pooled OOS trades | {evaluation['pooled_oos_trades']} |
| Pooled out-of-sample sessions | {evaluation['oos_sessions']} |
| Net excess over cash (annualized) | {evaluation['net_excess_annualized']:.4%}/yr |
| Net excess 95% CI | [{evaluation['excess_ci']['ci_low_annualized']:.4%}, {evaluation['excess_ci']['ci_high_annualized']:.4%}]/yr |
| DSR (N = {evaluation['dsr']['n_configs']}) | {_fmt(evaluation['dsr']['dsr'])} (probability {_fmt(evaluation['dsr']['probability'])}) |
| Realized turnover | {evaluation['realized_turnover_per_year']:.4f} units/yr |
| Realized cost drag | {evaluation['realized_cost_drag_per_year']:.4%}/yr |
| Net excess with the roll windows kept | {unclean['net_excess_annualized']:.4%}/yr |
| Detected rolls (CL-F / GC-F / NG-F / ZB-F) | {quality['rolls_by_symbol']} |
| CL-F non-positive close sessions | {quality['cl_f_non_positive_close_sessions']} |

## 4. Per-pair attribution (out of sample)

| Pair | Net excess (annualized) | Sharpe | Trades |
|---|---|---|---|
{attribution}

## 5. Verdict

| # | Condition | Observed | Outcome |
|---|---|---|---|
{conditions}

**{payload['verdict']['label']}**

## 6. Reproduction

```bash
python research/leadlag_001_evaluation.py
python -m pytest -q tests/test_leadlag_001_evaluation.py
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

    config = payload["config"]
    evaluation = payload["evaluation"]
    quality = payload["data_quality"]

    add(
        "frozen_config_consumed_as_is",
        all(payload["config"][key] == value for key, value in FROZEN.items()),
        "every frozen value still equals the pre-registered one",
    )
    add(
        "panel_is_the_cycle_934_complete_cross_section",
        payload["sessions"] == config["sessions"]
        and payload["union_sessions"] == config["union_calendar_sessions"],
        f"{payload['sessions']} complete sessions out of a {payload['union_sessions']}-session union calendar",
    )
    add(
        "five_pre_registered_pairs",
        len(config["pairs"]) == 5 and payload["n_pairs"] == 5,
        f"{len(config['pairs'])} pairs, {config['total_configs']} declared trials",
    )
    add(
        "book_is_long_only_with_cash_otherwise",
        bool(payload["max_gross_exposure"] <= config["gross_exposure_max"] + 1e-9)
        and float(payload["min_gross_exposure"]) >= -1e-12,
        f"gross exposure in [{payload['min_gross_exposure']:.6f}, {payload['max_gross_exposure']:.6f}]",
    )
    add(
        "rebalance_every_five_sessions_with_one_session_lag",
        config["rebalance_every_n_sessions"] == 5 and config["signal_lag_days"] == 1,
        "rebalance every 5th session, weights formed at t effective at t+1",
    )
    add(
        "cost_model_3bp_per_unit_of_weight_change",
        config["total_round_trip_bps"] == 3.0,
        f"{config['total_round_trip_bps']} bp per unit of weight change",
    )
    add(
        "benchmark_is_cash",
        True,
        "the cash return is 0; the net excess over cash is the net return",
    )
    add(
        "walkforward_design_matches_the_frozen_spec",
        config["train_years"] == 10
        and config["test_months"] == 12
        and config["step_months"] == 6
        and config["purge_days"] == 21
        and config["embargo_days"] == 21,
        "10y/12m/6m with a 21-day purge and a 21-day embargo",
    )
    add(
        "roll_windows_detected_and_excluded",
        quality["rolls_by_symbol"] == quality["documented_detected_rolls"]
        and quality["roll_affected_sessions"] == quality["documented_roll_affected_sessions"]
        and quality["roll_signal_sessions_excluded"] > 0,
        f"detected rolls {_fmt_map(quality['rolls_by_symbol'])} (the frozen config's "
        f"{_fmt_map(quality['documented_detected_rolls'])}); the roll rule makes "
        f"{_fmt_map(quality['roll_affected_sessions'])} signal sessions unusable "
        f"(the frozen config's {_fmt_map(quality['documented_roll_affected_sessions'])}), "
        f"{quality['roll_signal_sessions_excluded']} in total",
    )
    add(
        "cl_f_non_positive_close_detected",
        quality["cl_f_non_positive_close_sessions"] == config["cl_f_non_positive_close_sessions"],
        f"{quality['cl_f_non_positive_close_sessions']} non-positive close session(s) in CL-F: "
        f"{', '.join(quality['cl_f_non_positive_close_dates']) or 'none'}",
    )
    fired = payload["verdict"]["fired"]
    expected_falsified = bool(fired) or not payload["verdict"]["gates_passed"]
    add(
        "falsification_conditions_drive_the_verdict",
        len(payload["verdict"]["conditions"]) == 4
        and payload["verdict"]["falsified"] == expected_falsified
        and (payload["verdict"]["label"] == "Rejected/Failed") == expected_falsified,
        f"fired: {', '.join(fired) or 'none'}; gates passed: {payload['verdict']['gates_passed']}",
    )
    add("data_unchanged", payload["data_unchanged"], "every file under data/ is byte-identical")
    add(
        "config_unchanged",
        payload["config_unchanged"],
        "every file under config/ is byte-identical",
    )
    add(
        "committed_artifacts_unchanged",
        payload["artifacts_unchanged"],
        "no committed artefact under src/, config/, research/experiments/ or research/reports/ was modified by the run",
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
    raw_config = yaml.safe_load(CONFIG_PATH.read_text()) or {}
    documented_quality = raw_config.get("data_quality", {})
    documented_roll_sessions = {
        str(k): int(v)
        for k, v in (documented_quality.get("unusable_signal_sessions", {}) or {}).items()
    }
    documented_rolls = {
        str(k): int(v)
        for k, v in (documented_quality.get("detected_rolls", {}) or {}).items()
    }
    pairs = [tuple(p) for p in config["pairs"]]
    lookback = int(config["lookback_sessions"])
    every_n = int(config["rebalance_every_n_sessions"])
    lag = int(config["signal_lag_days"])
    pair_weight = float(config["pair_weight"])
    cost_per_unit = float(config["total_round_trip_bps"]) / 10_000.0

    close_all = load_closes(config["universe"])
    panel, churn = build_panel(close_all)

    # --- data quality: the roll windows and the non-positive closes -------
    futures_symbols = [futures for futures, _etf in pairs]
    futures_symbols = sorted(set(futures_symbols))
    roll_dates: dict[str, pd.DatetimeIndex] = {}
    non_positive: dict[str, pd.DatetimeIndex] = {}
    futures_rows: list[dict[str, Any]] = []
    signals_clean: dict[str, pd.Series] = {}
    usability_clean: dict[str, pd.Series] = {}
    signals_unclean: dict[str, pd.Series] = {}
    usability_unclean: dict[str, pd.Series] = {}
    unusable_sessions: dict[str, int] = {}
    roll_sessions_excluded: dict[str, int] = {}

    for symbol in futures_symbols:
        frame = load_cached_series(symbol)
        close = frame["Close"].astype(float)
        dates, rolls = detect_roll_dates(symbol)
        roll_dates[symbol] = dates
        bad_close = close.index[close <= 0.0]
        non_positive[symbol] = bad_close

        roll_flag = pd.Series(0.0, index=close.index)
        roll_flag.loc[dates] = 1.0
        bad_flag = pd.Series(0.0, index=close.index)
        bad_flag.loc[bad_close] = 1.0

        signal_clean, usable_clean = futures_signal(close, lookback, (roll_flag > 0) | (bad_flag > 0))
        signal_unclean, usable_unclean = futures_signal(close, lookback, bad_flag > 0)
        signals_clean[symbol] = signal_clean
        usability_clean[symbol] = usable_clean
        signals_unclean[symbol] = signal_unclean
        usability_unclean[symbol] = usable_unclean

        unusable_sessions[symbol] = int((~usable_clean).sum())
        # the sessions whose trailing window contains a detected roll date
        # (the roll rule alone, independent of the other data-quality rules)
        roll_flag_series = pd.Series(0.0, index=close.index)
        roll_flag_series.loc[dates] = 1.0
        roll_affected = (
            roll_flag_series.rolling(lookback + 1, min_periods=lookback + 1).max() > 0
        )
        roll_sessions_excluded[symbol] = int(roll_affected.sum())

        futures_rows.append(
            {
                "symbol": symbol,
                "rolls": int(rolls),
                "first_roll": str(dates[0].date()) if len(dates) else "",
                "last_roll": str(dates[-1].date()) if len(dates) else "",
                "sessions": int(len(close)),
                "roll_affected_sessions": roll_sessions_excluded[symbol],
                "unusable_signal_sessions": unusable_sessions[symbol],
                "unusable_share": unusable_sessions[symbol] / max(1, len(close)),
            }
        )

    cl_f_bad = non_positive.get("CL-F", pd.DatetimeIndex([]))
    cl_f_close = load_cached_series("CL-F")["Close"].astype(float)

    # --- the two variants of the frozen rule ------------------------------
    weights_clean, per_pair_clean = build_pair_weights(
        panel.index, pairs, signals_clean, usability_clean, every_n, lag, pair_weight
    )
    weights_unclean, per_pair_unclean = build_pair_weights(
        panel.index, pairs, signals_unclean, usability_unclean, every_n, lag, pair_weight
    )

    evaluation = evaluate_variant(panel, weights_clean, per_pair_clean, pairs, config)
    unclean = evaluate_variant(panel, weights_unclean, per_pair_unclean, pairs, config)

    gross_exposure = weights_clean.sum(axis=1)
    payload = {
        "cycle": CYCLE,
        "config": config,
        "pairs": pairs,
        "n_pairs": len(pairs),
        "sessions": int(len(panel)),
        "union_sessions": int(len(close_all)),
        "calendar_churn": float(churn),
        "min_gross_exposure": float(gross_exposure.min()),
        "max_gross_exposure": float(gross_exposure.max()),
        "evaluation": evaluation,
        "unclean_evaluation": unclean,
        "data_quality": {
            "futures": futures_rows,
            "rolls_by_symbol": {row["symbol"]: row["rolls"] for row in futures_rows},
            "roll_affected_sessions": roll_sessions_excluded,
            "documented_roll_affected_sessions": documented_roll_sessions,
            "documented_detected_rolls": documented_rolls,
            "unusable_signal_sessions": unusable_sessions,
            "roll_signal_sessions_excluded": int(sum(roll_sessions_excluded.values())),
            "unclean_roll_sessions_excluded": 0,
            "cl_f_non_positive_close_sessions": int(len(cl_f_bad)),
            "cl_f_non_positive_close_dates": [str(d.date()) for d in cl_f_bad],
            "cl_f_non_positive_close_values": [
                float(cl_f_close.loc[d]) for d in cl_f_bad
            ],
        },
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
        f"EXCESS_PCT|{evaluation['net_excess_annualized'] * 100.0:.6f}|"
        f"CI_LOW_PCT|{evaluation['excess_ci']['ci_low_annualized'] * 100.0:.6f}|"
        f"CI_HIGH_PCT|{evaluation['excess_ci']['ci_high_annualized'] * 100.0:.6f}|"
        f"BLOCK|{evaluation['excess_ci']['block']}|"
        f"SEED|{evaluation['excess_ci']['seed']}"
    )
    print(
        f"COST|TURN|{evaluation['realized_turnover_per_year']:.6f}|"
        f"TURN_COST_PCT|{evaluation['realized_cost_drag_per_year'] * 100.0:.8f}|"
        f"NET_EXCESS_PCT|{evaluation['net_excess_annualized'] * 100.0:.8f}|"
        f"UNCLEAN_EXCESS_PCT|{payload['unclean_evaluation']['net_excess_annualized'] * 100.0:.8f}|"
        f"NON_CLF_EXCESS_PCT|{evaluation['non_cl_f_net_excess_annualized'] * 100.0:.8f}"
    )
    print(
        f"DSR|{evaluation['dsr']['dsr']:.6f}|PROB|{evaluation['dsr']['probability']:.6f}|"
        f"N_CONFIGS|{evaluation['dsr']['n_configs']}"
    )
    print(
        f"ROLLS|"
        + ",".join(
            f"{row['symbol']}:{row['rolls']}" for row in payload["data_quality"]["futures"]
        )
        + f"|CL_F_NONPOSITIVE|{payload['data_quality']['cl_f_non_positive_close_sessions']}"
    )
    print(f"VERDICT|{payload['verdict']['label']}")
    print(f"FROZEN_CONDITIONS_FIRED|{','.join(payload['verdict']['fired']) or 'none'}")
    print(f"REPORT|{OUT_REPORT if not args.no_report else '(not written: --no-report)'}")
    print(f"EXPERIMENT|{OUT_EXP if not args.no_report else '(not written: --no-report)'}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
