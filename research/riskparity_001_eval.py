#!/usr/bin/env python3
"""Pre-registered evaluation of the hypothesis ``riskparity_001`` (Cycle 930).

This tool executes the evaluation plan *as pre-registered* in
``research/hypotheses/riskparity_001.md`` -- no parameter is chosen after the
fact, no configuration is added, removed or re-tuned, and the trial count
(9) is the declared one, so the Deflated Sharpe Ratio is computed at N = 9.

The candidate
-------------
Long-only, fully invested, monthly-rebalanced inverse-volatility ("risk
balancing") allocation over the incumbent's seven-ETF universe
(SPY, QQQ, IWM, TLT, GLD, EFA, EEM):

* ``vol_i(t)`` = standard deviation of the daily returns of member *i* over
  the trailing ``L`` sessions **ending at t-1** (the estimate is lagged, so the
  Cycle-926 same-session volatility defect cannot occur);
* ``raw_w_i`` = ``1 / max(vol_i, 1e-6)``, normalised to 1.0, then capped
  per asset at ``cap`` with an iterative renormalisation (at most 5
  iterations; the realised maximum weight and the iteration count are
  reported, not approximated);
* the book formed on the last session of a calendar month is **effective from
  the next session**;
* costs: 1.0 bp commission + 2.0 bp slippage = 3.0 bp per unit of weight
  change (``config/settings.yaml``), the convention every committed candidate
  is costed on.

The evaluation window
---------------------
``research/hypotheses/riskparity_001.md`` pre-registers the evaluation on the
**point-in-time-complete** window: it starts on the first session on which all
seven members carry a valid lagged 63-session volatility estimate
(2005-11-10). The seven members did not exist simultaneously at the start of
the incumbent's sample, and the Cycle-929 membership audit measured that the
incumbent's published 48-fold mean mixes seven folds measured on an
incomplete cross-section with 41 measured on the complete one. The
pre-registered start is therefore held fixed for **every** configuration in
the grid, so the nine configurations are measured on one homogeneous window
and are directly comparable.

The tool is **read-only**: the price panel is read from the committed parquet
cache (the fetcher is never called), nothing under ``data/`` or ``config/`` is
written, the SHA-256 of every file under those two trees is compared before
and after the run, and no committed artefact other than this tool's own
report and experiment record is touched. The published record, the published
gates, the published protocol and the committed shortlist are left untouched.

Reproduction
------------
```bash
python research/riskparity_001_eval.py
python -m pytest -q tests/test_riskparity_001_evaluation.py
```
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.csmomentum_common_inception_audit import (  # noqa: E402
    aligned_close_from_cache,
)
from research.data_cost_inventory_002 import (  # noqa: E402
    fingerprint,
    tracked_artifact_hashes,
)
from research.month_end_candidate_reaudit import (  # noqa: E402
    path_metrics,
    path_returns,
    walkforward,
)
from research.tsmomentum_walkforward_embargo_audit import (  # noqa: E402
    build_candidate_path,
)
from src.backtest.engine import get_cost_params, get_risk_free_rate  # noqa: E402
from src.backtest.rebalance import month_end_sessions  # noqa: E402
from src.evaluation.sharpe import sharpe_ratio  # noqa: E402
from src.evaluation.statistics import compute_dsr, compute_psr  # noqa: E402
from src.evaluation.walkforward import generate_walkforward_splits  # noqa: E402

HYPOTHESIS_ID = "riskparity_001"
CYCLE = "930"

UNIVERSE = ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"]

# Pre-registered evaluation window (hypothesis section "Pre-registered
# evaluation plan"). The start is the first session on which all seven
# members carry a valid *lagged* 63-session volatility estimate.
EVAL_START = "2005-11-10"
TRAIN_END = "2015-12-31"
VAL_END = "2020-12-31"

# Pre-registered grid: L in {21, 63, 126} x cap in {0.25, 0.30, 0.40}.
LOOKBACKS = (21, 63, 126)
CAPS = (0.25, 0.30, 0.40)
BASELINE = (63, 0.30)
N_CONFIGS = len(LOOKBACKS) * len(CAPS)

# Pre-registered promotion gates (hypothesis + config/promotion_gates.yaml).
GATE_WF_MEAN_MIN = 0.9
GATE_POSITIVE_FOLD_MIN = 0.5
GATE_POOLED_TRADES_MIN = 100

# Walk-forward design (pre-registered).
WF_TRAIN_YEARS = 10.0
WF_TEST_MONTHS = 12.0
WF_STEP_MONTHS = 6.0
WF_PURGE_DAYS = 21
WF_EMBARGO_DAYS = 21

BOOTSTRAP_SEED = 20240101
BOOTSTRAP_DRAWS = 1000
BLOCK_SIZE = 22

REPORTS_DIR = REPO_ROOT / "research" / "reports"
EXPERIMENTS_DIR = REPO_ROOT / "research" / "experiments"
OUT_REPORT = REPORTS_DIR / "riskparity_001_evaluation.md"
OUT_EXP = EXPERIMENTS_DIR / "riskparity_001_evaluation.md"

SELF_OUTPUTS = {
    str(OUT_REPORT.relative_to(REPO_ROOT)),
    str(OUT_EXP.relative_to(REPO_ROOT)),
}


class EvaluationError(RuntimeError):
    """Raised when a required input is missing or malformed (fails closed)."""


def fail(message: str) -> None:
    raise EvaluationError(message)


# ----------------------------------------------------------------------
# Weight construction
# ----------------------------------------------------------------------


def capped_normalise(
    raw: np.ndarray, cap: float, max_iter: int = 5
) -> tuple[np.ndarray, int, float]:
    """Normalise *raw* to sum 1.0 and cap every weight at *cap*.

    The cap is applied iteratively: the assets above the cap are pinned to it
    and the remaining mass is redistributed proportionally among the assets
    that are still below the cap, at most *max_iter* times. The realised
    maximum weight and the number of iterations are returned so the result is
    **stated**, not approximated.
    """
    w = np.asarray(raw, dtype=float).copy()
    if not np.isfinite(w).all():
        fail("non-finite weight input")
    total = w.sum()
    if total <= 0:
        fail("weight input sums to zero")
    w = w / total
    used = 0
    for used in range(1, max_iter + 1):
        over = w > cap + 1e-12
        if not over.any():
            break
        excess = float(w[over].sum() - cap * over.sum())
        w[over] = cap
        free = ~over
        free_sum = float(w[free].sum())
        if free_sum <= 0:
            fail("the cap leaves no free weight to redistribute")
        w[free] = w[free] + excess * w[free] / free_sum
    residual = float(np.max(w) - cap)
    return w, used, max(residual, 0.0)


def lagged_volatility(close: pd.DataFrame, lookback: int) -> pd.DataFrame:
    """Trailing standard deviation of the daily returns ending at t-1.

    ``ret.rolling(L).std(ddof=1)`` at index ``t-1`` is the standard
    deviation of the ``L`` returns ``ret[t-L .. t-1]``; the ``shift(1)`` moves
    it to ``t``, so the estimate used on session ``t`` never contains the
    return of session ``t`` (the Cycle-926 defect cannot occur).
    """
    returns = close.pct_change()
    return returns.rolling(lookback).std(ddof=1).shift(1)


def build_weights(
    close: pd.DataFrame, lookback: int, cap: float
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Month-end rebalanced, 1-session-lagged inverse-volatility weights."""
    vol = lagged_volatility(close, lookback)
    inv = 1.0 / vol.clip(lower=1e-6)

    weights = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    segments: list[dict[str, Any]] = []
    max_weight = 0.0
    max_iterations = 0
    max_residual = 0.0

    for signal_date in month_end_sessions(close.index):
        row = inv.loc[signal_date]
        if row.isna().any():
            continue
        w, iterations, residual = capped_normalise(row.to_numpy(dtype=float), cap)
        pos = int(close.index.searchsorted(signal_date, side="right"))
        if pos >= len(close.index):
            break
        segments.append(
            {
                "signal_date": signal_date,
                "effective_date": close.index[pos],
                "weights": w,
                "iterations": iterations,
                "residual": residual,
            }
        )
        max_weight = max(max_weight, float(w.max()))
        max_iterations = max(max_iterations, iterations)
        max_residual = max(max_residual, residual)

    if not segments:
        fail("no rebalance could be formed from the committed cache")
    for j, seg in enumerate(segments):
        start = int(close.index.searchsorted(seg["effective_date"], side="left"))
        end = (
            int(close.index.searchsorted(segments[j + 1]["effective_date"], side="left"))
            if j + 1 < len(segments)
            else len(close.index)
        )
        weights.iloc[start:end, :] = seg["weights"]

    if (weights < -1e-12).any().any():
        fail("the constructed book holds a negative weight")
    row_sums = weights.sum(axis=1)
    invested = row_sums > 0
    if not np.allclose(row_sums[invested], 1.0, atol=1e-9):
        fail("the invested book does not sum to 1.0")

    return weights, {
        "n_segments": len(segments),
        "max_weight": max_weight,
        "max_cap_iterations": max_iterations,
        "max_cap_residual": max_residual,
        "first_signal_date": str(segments[0]["signal_date"].date()),
        "first_effective_date": str(segments[0]["effective_date"].date()),
        "last_signal_date": str(segments[-1]["signal_date"].date()),
    }


# ----------------------------------------------------------------------
# Metrics helpers
# ----------------------------------------------------------------------


def backtest_sharpe(returns: pd.Series, rf_annual: float = 0.02) -> float:
    """The repository's backtest-scale Sharpe: (CAGR - rf) / annualised vol."""
    if len(returns) < 2:
        return float("nan")
    ann_return = (1 + returns).prod() ** (252 / len(returns)) - 1
    ann_vol = returns.std() * np.sqrt(252)
    if ann_vol <= 0:
        return 0.0
    return float((ann_return - rf_annual) / ann_vol)


def pooled_test_returns(
    net_ret: pd.Series, splits: list[dict[str, Any]]
) -> pd.Series:
    """Concatenate the out-of-sample test returns of every walk-forward fold."""
    parts = []
    for sp in splits:
        sel = (
            (net_ret.index >= pd.Timestamp(sp["test_start"], tz="UTC"))
            & (net_ret.index <= pd.Timestamp(sp["test_end"], tz="UTC"))
        )
        parts.append(net_ret[sel])
    if not parts:
        return pd.Series(dtype=float)
    return pd.concat(parts)


def correlation(a: pd.Series, b: pd.Series) -> float:
    joined = pd.concat([a, b], axis=1).dropna()
    if len(joined) < 3:
        return float("nan")
    return float(joined.iloc[:, 0].corr(joined.iloc[:, 1]))


# ----------------------------------------------------------------------
# Configuration evaluation
# ----------------------------------------------------------------------


def evaluate_config(
    close: pd.DataFrame,
    lookback: int,
    cap: float,
    splits: list[dict[str, Any]],
    cost: float,
) -> dict[str, Any]:
    """Evaluate one pre-registered configuration on the pre-registered window."""
    window = close.loc[close.index >= pd.Timestamp(EVAL_START, tz="UTC")]
    # The weights are formed on the **full** price panel: the trailing
    # volatility window of the first rebalance inside the evaluation window
    # reaches back before it, exactly as it would in production.
    weights_full, meta = build_weights(close, lookback, cap)
    weights = weights_full.loc[window.index]
    invested = weights.sum(axis=1) > 0
    if not invested.any():
        fail(f"no book could be formed for L={lookback}, cap={cap}")
    meta = dict(meta)
    meta["first_invested_session"] = str(window.index[invested][0].date())
    meta["invested_sessions"] = int(invested.sum())
    net_ret, weights_a, turnover = path_returns(window, weights, cost)

    summary, rows = walkforward(net_ret, weights_a, splits)
    oos = pooled_test_returns(net_ret, splits)

    train_end = pd.Timestamp(TRAIN_END, tz="UTC")
    val_end = pd.Timestamp(VAL_END, tz="UTC")
    samples = {
        "train": window.index[window.index <= train_end],
        "validation": window.index[
            (window.index > train_end) & (window.index <= val_end)
        ],
        "test": window.index[window.index > val_end],
    }
    split_metrics = {
        name: path_metrics(net_ret, weights_a, cost, sample)
        for name, sample in samples.items()
    }

    sharpes = [r["test_sharpe"] for r in rows]
    gates = {
        "wf_mean_oos_sharpe": {
            "value": float(summary["mean_test_sharpe"]),
            "threshold": GATE_WF_MEAN_MIN,
            "comparison": ">=",
            "passed": bool(summary["mean_test_sharpe"] >= GATE_WF_MEAN_MIN),
        },
        "positive_fold_rate": {
            "value": float(summary["pct_positive_sharpe"]),
            "threshold": GATE_POSITIVE_FOLD_MIN,
            "comparison": ">=",
            "passed": bool(summary["pct_positive_sharpe"] >= GATE_POSITIVE_FOLD_MIN),
        },
        "pooled_oos_trades": {
            "value": int(summary["total_test_trades"]),
            "threshold": GATE_POOLED_TRADES_MIN,
            "comparison": ">",
            "passed": bool(summary["total_test_trades"] > GATE_POOLED_TRADES_MIN),
        },
    }

    return {
        "lookback": lookback,
        "cap": cap,
        "is_baseline": (lookback, cap) == BASELINE,
        "weight_meta": meta,
        "folds": rows,
        "n_folds": int(summary["n_folds"]),
        "wf_mean_test_sharpe": float(summary["mean_test_sharpe"]),
        "wf_median_test_sharpe": float(summary["median_test_sharpe"]),
        "wf_mean_test_sharpe_canonical": float(summary["mean_test_sharpe_canonical"]),
        "pct_positive_sharpe": float(summary["pct_positive_sharpe"]),
        "total_test_trades": int(summary["total_test_trades"]),
        "min_test_sharpe": float(summary["min_test_sharpe"]),
        "gates": gates,
        "gates_passed": all(g["passed"] for g in gates.values()),
        "split_metrics": split_metrics,
        "oos_returns": oos,
        "net_ret": net_ret,
        "weights": weights_a,
        "turnover": turnover,
    }


def breakeven_cost(
    close: pd.DataFrame,
    lookback: int,
    cap: float,
    splits: list[dict[str, Any]],
) -> dict[str, Any]:
    """Gate-flip costs: the cost per unit at which each pre-registered gate flips.

    The cost grid is scanned on 0.5 bp steps from 0 to 100 bp per unit of
    weight change, exactly as the committed cost break-even audit does. For
    each gate the reported value is the **largest** cost on the grid at which
    the gate still holds; ``None`` means the gate already fails at zero cost
    and therefore never flips. The erosion cost -- the largest cost at which
    the walk-forward mean OOS Sharpe is still above zero -- is reported as the
    informative measure of how much friction the mechanism can absorb.
    """
    window = close.loc[close.index >= pd.Timestamp(EVAL_START, tz="UTC")]
    weights_full, _ = build_weights(close, lookback, cap)
    weights = weights_full.loc[window.index]
    daily_ret = window.pct_change().fillna(0.0)
    gross = (weights * daily_ret).sum(axis=1)
    turnover = weights.diff().abs().sum(axis=1).fillna(0.0)

    rf = get_risk_free_rate()
    grid = [i * 0.5 for i in range(0, 201)]
    curve = []
    for bps in grid:
        cost = bps / 10000.0
        sharpes = []
        for sp in splits:
            sel = (
                (gross.index >= pd.Timestamp(sp["test_start"], tz="UTC"))
                & (gross.index <= pd.Timestamp(sp["test_end"], tz="UTC"))
            )
            r = gross[sel] - turnover[sel] * cost
            if len(r) < 2:
                continue
            sharpes.append(backtest_sharpe(r, rf))
        if sharpes:
            positive = float(np.mean([s > 0 for s in sharpes]))
            curve.append(
                {
                    "bps": bps,
                    "mean_sharpe": float(np.mean(sharpes)),
                    "positive_fold_rate": positive,
                }
            )

    def flip(threshold: float, key: str) -> float | None:
        passing = [row["bps"] for row in curve if row[key] >= threshold]
        return max(passing) if passing else None

    gate1 = flip(GATE_WF_MEAN_MIN, "mean_sharpe")
    gate2 = flip(GATE_POSITIVE_FOLD_MIN, "positive_fold_rate")
    above_zero = [row["bps"] for row in curve if row["mean_sharpe"] > 0]

    def at(bps: float) -> float:
        for row in curve:
            if abs(row["bps"] - bps) < 1e-9:
                return float(row["mean_sharpe"])
        return float("nan")

    return {
        "grid_bps": [row["bps"] for row in curve],
        "grid_mean_sharpe": [row["mean_sharpe"] for row in curve],
        "gate1_flip_bps": gate1,
        "gate2_flip_bps": gate2,
        "gate3_flip_bps": None,
        "erosion_bps": max(above_zero) if above_zero else 0.0,
        "sharpe_at_0bps": at(0.0),
        "sharpe_at_3bps": at(3.0),
        "sharpe_at_10bps": at(10.0),
        "gate": GATE_WF_MEAN_MIN,
    }


# ----------------------------------------------------------------------
# The evaluation
# ----------------------------------------------------------------------


def run_evaluation() -> dict[str, Any]:
    data_before = fingerprint(REPO_ROOT / "data")
    config_before = fingerprint(REPO_ROOT / "config")
    artifacts_before = tracked_artifact_hashes()

    commission, slippage = get_cost_params()
    cost = commission + slippage
    rf = get_risk_free_rate()

    close = aligned_close_from_cache(UNIVERSE)
    if close.empty:
        fail("the committed cache produced an empty close panel")

    # --- pre-registration anchor -------------------------------------
    vol63 = lagged_volatility(close, 63)
    complete = vol63.notna().all(axis=1)
    if not complete.any():
        fail("no session carries a valid lagged 63-session estimate for all seven")
    first_complete = str(complete.idxmax().date())
    # The pre-registration states the rule ("the evaluation starts on the
    # first session on which all seven members carry a valid lagged
    # volatility estimate") and gives 2005-11-10 as the date. The measured
    # date of that rule is earlier -- 2005-11-10 is the incumbent's *momentum*
    # warm-up date for GLD, not a 63-session volatility date -- so the
    # pre-registered window is point-in-time complete strictly from its first
    # session. The pre-registered date is kept unchanged and the measurement
    # is reported.
    if first_complete > EVAL_START:
        fail(
            "the pre-registered evaluation window is not point-in-time complete: "
            f"the first session on which all seven members carry a valid lagged "
            f"63-session estimate is {first_complete}, after {EVAL_START}"
        )

    window = close.loc[close.index >= pd.Timestamp(EVAL_START, tz="UTC")]
    end_date = str(window.index[-1].date())
    splits = generate_walkforward_splits(
        EVAL_START,
        end_date,
        WF_TRAIN_YEARS,
        WF_TEST_MONTHS,
        WF_STEP_MONTHS,
        WF_PURGE_DAYS,
        WF_EMBARGO_DAYS,
    )
    if len(splits) < 5:
        fail(f"the pre-registered design produced only {len(splits)} folds")

    configs: list[dict[str, Any]] = []
    for lookback in LOOKBACKS:
        for cap in CAPS:
            configs.append(evaluate_config(close, lookback, cap, splits, cost))

    baseline = next(c for c in configs if c["is_baseline"])

    # --- benchmarks on the same window --------------------------------
    bench_weights = pd.DataFrame(
        0.0, index=window.index, columns=window.columns
    )
    bench_weights[:] = 1.0 / len(UNIVERSE)
    bench_net, bench_w, _ = path_returns(window, bench_weights, cost)
    train_end = pd.Timestamp(TRAIN_END, tz="UTC")
    val_end = pd.Timestamp(VAL_END, tz="UTC")
    test_sample = window.index[window.index > val_end]
    one_over_n = {
        "full": path_metrics(bench_net, bench_w, cost, window.index),
        "test": path_metrics(bench_net, bench_w, cost, test_sample),
    }
    # The benchmark on the *same* walk-forward folds: the candidate's excess
    # over 1/N is the mechanism's contribution (AGENTS.md, "Known confounders":
    # a long-only seven-asset book earns part of its Sharpe as equity beta).
    bench_summary, _ = walkforward(bench_net, bench_w, splits)
    one_over_n["wf_mean_test_sharpe"] = float(bench_summary["mean_test_sharpe"])
    one_over_n["wf_mean_test_sharpe_canonical"] = float(
        bench_summary["mean_test_sharpe_canonical"]
    )
    one_over_n["pct_positive_sharpe"] = float(bench_summary["pct_positive_sharpe"])
    one_over_n["total_test_trades"] = int(bench_summary["total_test_trades"])
    one_over_n["n_folds"] = int(bench_summary["n_folds"])

    spy_ret = window["SPY"].pct_change().fillna(0.0)
    spy_weights = pd.DataFrame(0.0, index=window.index, columns=window.columns)
    spy_weights["SPY"] = 1.0
    spy_net, spy_w, _ = path_returns(window, spy_weights, cost)
    spy = {
        "full": path_metrics(spy_net, spy_w, cost, window.index),
        "test": path_metrics(spy_net, spy_w, cost, test_sample),
    }

    oos = baseline["oos_returns"]
    corr_1n = correlation(oos, bench_net.loc[oos.index])
    corr_spy = correlation(oos, spy_net.loc[oos.index])

    # --- correlation with the incumbent (reference only) --------------
    incumbent_net, _ = build_candidate_path(close)
    corr_incumbent = correlation(oos, incumbent_net.loc[oos.index])

    # --- multiple-testing control (N = 9, the declared trial count) ---
    psr = compute_psr(oos, sr_target=0.0, n_bootstrap=BOOTSTRAP_DRAWS,
                      block_size=BLOCK_SIZE, seed=BOOTSTRAP_SEED)
    dsr = compute_dsr(oos, n_configs=N_CONFIGS, sr_target=0.0,
                      n_bootstrap=BOOTSTRAP_DRAWS, block_size=BLOCK_SIZE,
                      seed=BOOTSTRAP_SEED)

    # --- cost sensitivity ---------------------------------------------
    cost_curve = breakeven_cost(close, BASELINE[0], BASELINE[1], splits)

    # --- plateau (post-gate robustness; reported either way) ----------
    lookback_plateau = {
        str(L): {
            "mean_test_sharpe": float(
                np.mean([c["wf_mean_test_sharpe"] for c in configs if c["lookback"] == L])
            )
        }
        for L in LOOKBACKS
    }
    cap_plateau = {
        str(cap): {
            "mean_test_sharpe": float(
                np.mean([c["wf_mean_test_sharpe"] for c in configs if c["cap"] == cap])
            )
        }
        for cap in CAPS
    }

    decision = "PROMOTE" if baseline["gates_passed"] else "REJECT"
    label = (
        "Credible candidate (promotion gates passed)"
        if baseline["gates_passed"]
        else "Rejected / failed the pre-registered promotion gates"
    )

    payload = {
        "hypothesis_id": HYPOTHESIS_ID,
        "cycle": CYCLE,
        "universe": list(UNIVERSE),
        "evaluation_start": EVAL_START,
        "evaluation_end": end_date,
        "first_complete_breadth_session": first_complete,
        "train_end": TRAIN_END,
        "validation_end": VAL_END,
        "n_folds": len(splits),
        "first_fold": splits[0],
        "last_fold": splits[-1],
        "cost_per_unit": cost,
        "commission_bps": commission * 10000.0,
        "slippage_bps": slippage * 10000.0,
        "risk_free_annual": rf,
        "grid": [
            {
                "lookback": c["lookback"],
                "cap": c["cap"],
                "is_baseline": c["is_baseline"],
                "wf_mean_test_sharpe": c["wf_mean_test_sharpe"],
                "wf_median_test_sharpe": c["wf_median_test_sharpe"],
                "wf_mean_test_sharpe_canonical": c["wf_mean_test_sharpe_canonical"],
                "pct_positive_sharpe": c["pct_positive_sharpe"],
                "total_test_trades": c["total_test_trades"],
                "min_test_sharpe": c["min_test_sharpe"],
                "gates_passed": c["gates_passed"],
                "max_weight": c["weight_meta"]["max_weight"],
            }
            for c in configs
        ],
        "baseline": {
            "lookback": baseline["lookback"],
            "cap": baseline["cap"],
            "wf_mean_test_sharpe": baseline["wf_mean_test_sharpe"],
            "wf_median_test_sharpe": baseline["wf_median_test_sharpe"],
            "wf_mean_test_sharpe_canonical": baseline["wf_mean_test_sharpe_canonical"],
            "pct_positive_sharpe": baseline["pct_positive_sharpe"],
            "total_test_trades": baseline["total_test_trades"],
            "min_test_sharpe": baseline["min_test_sharpe"],
            "gates": baseline["gates"],
            "gates_passed": baseline["gates_passed"],
            "folds": baseline["folds"],
            "split_metrics": baseline["split_metrics"],
            "weight_meta": baseline["weight_meta"],
        },
        "benchmarks": {
            "one_over_n": one_over_n,
            "spy": spy,
            "excess_over_1n_wf_mean": float(
                baseline["wf_mean_test_sharpe"] - one_over_n["wf_mean_test_sharpe"]
            ),
            "corr_with_1n": corr_1n,
            "corr_with_spy": corr_spy,
            "corr_with_incumbent": corr_incumbent,
        },
        "psr": {
            "psr_normal": psr["psr_normal"],
            "psr_empirical": psr["psr_empirical"],
            "sharpe_observed": psr["sharpe_observed"],
            "sharpe_se": psr["sharpe_se"],
            "ci_lower": psr["ci_lower"],
            "ci_upper": psr["ci_upper"],
        },
        "dsr": {
            "dsr": dsr["dsr"],
            "dsr_probability": dsr["dsr_probability"],
            "n_configs": dsr["n_configs"],
            "sr_threshold": dsr["sr_threshold"],
            "e_max": dsr["e_max"],
        },
        "cost_sensitivity": cost_curve,
        "lookback_plateau": lookback_plateau,
        "cap_plateau": cap_plateau,
        "decision": decision,
        "label": label,
    }

    # --- read-only guarantees -----------------------------------------
    data_after = fingerprint(REPO_ROOT / "data")
    config_after = fingerprint(REPO_ROOT / "config")
    artifacts_after = tracked_artifact_hashes()
    if data_before != data_after:
        fail("data/ changed during the run")
    if config_before != config_after:
        fail("config/ changed during the run")
    changed = {
        key
        for key in set(artifacts_before) | set(artifacts_after)
        if artifacts_before.get(key) != artifacts_after.get(key)
    }
    changed -= SELF_OUTPUTS
    if changed:
        fail(f"committed artefacts changed during the run: {sorted(changed)}")

    payload["checks"] = [
        {"name": "data_unchanged", "pass": True},
        {"name": "config_unchanged", "pass": True},
        {"name": "committed_artifacts_unchanged", "pass": True},
        {
            "name": "evaluation_window_is_point_in_time_complete",
            "pass": first_complete <= EVAL_START,
        },
        {
            "name": "baseline_weight_cap_respected",
            "pass": baseline["weight_meta"]["max_weight"]
            <= BASELINE[1] + 1e-9,
        },
        {
            "name": "trial_count_is_preregistered",
            "pass": len(configs) == N_CONFIGS,
        },
    ]
    payload["structural_pass"] = all(c["pass"] for c in payload["checks"])
    return payload


# ----------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------


def fmt(value: float, digits: int = 6) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "n/a"
    return f"{value:.{digits}f}"


def render_report(payload: dict[str, Any]) -> str:
    base = payload["baseline"]
    bench = payload["benchmarks"]
    lines: list[str] = []
    A = lines.append

    A(f"# Risk-Balanced (Inverse-Volatility) Allocation — `riskparity_001`")
    A("")
    A(f"**Cycle {payload['cycle']} — pre-registered evaluation of "
      "`research/hypotheses/riskparity_001.md`.**")
    A("")
    A("## Status")
    A("")
    A(f"- **Decision: {payload['decision']}** — {payload['label']}.")
    A(f"- Pre-registered baseline (L = {base['lookback']}, cap = {base['cap']}): "
      f"walk-forward mean OOS Sharpe **{fmt(base['wf_mean_test_sharpe'])}** "
      f"(canonical {fmt(base['wf_mean_test_sharpe_canonical'])}).")
    for name, gate in base["gates"].items():
        A(f"- Gate `{name}`: {fmt(float(gate['value']))} "
          f"{gate['comparison']} {fmt(float(gate['threshold']))} -> "
          f"**{'PASS' if gate['passed'] else 'FAIL'}**.")
    A(f"- Trials evaluated: **{len(payload['grid'])}** (the pre-registered grid; "
      f"DSR computed at N = {payload['dsr']['n_configs']}).")
    A(f"- Evaluation window: {payload['evaluation_start']} .. "
      f"{payload['evaluation_end']} "
      f"({payload['n_folds']} walk-forward folds, "
      f"10y train / 12m test / 6m step, 21d purge and embargo).")
    A("")

    A("## 1. What was evaluated")
    A("")
    A("A long-only, fully invested, month-end rebalanced inverse-volatility book")
    A("over the incumbent's seven-ETF universe. The volatility estimate is")
    A("**lagged** (it uses the returns up to and including the session *before*")
    A("the rebalance), the book formed on the last session of a month is")
    A("effective from the next session, and the cost model is the repository's")
    A(f"committed one: {payload['commission_bps']:.1f} bp commission + "
      f"{payload['slippage_bps']:.1f} bp slippage = "
      f"{payload['cost_per_unit'] * 10000:.1f} bp per unit of weight change.")
    A("")
    A("**The evaluation window is the pre-registered point-in-time-complete one.**")
    A("The pre-registration states the rule -- the evaluation starts on the")
    A("first session on which all seven members carry a valid *lagged*")
    A("volatility estimate -- and gives 2005-11-10 as the date. The rule is")
    A(f"measured at **{payload['first_complete_breadth_session']}** from the")
    A("committed cache: 2005-11-10 is the incumbent's *momentum* warm-up date")
    A("for GLD (226-session lookback skipping 21), not a 63-session volatility")
    A("date. The pre-registered date is therefore **later** than the rule")
    A("requires, so the window is point-in-time complete strictly from its")
    A("first session and every configuration of the grid is measured on a")
    A("homogeneous cross-section. The pre-registration is used unchanged; the")
    A("discrepancy is measured and reported, not silently corrected.")
    A("")

    A("## 2. Pre-registered grid (9 configurations, no post-hoc change)")
    A("")
    A("| L | cap | WF mean OOS Sharpe | median | canonical mean | positive folds | pooled trades | min fold | gates |")
    A("|---|---|---|---|---|---|---|---|---|")
    for row in payload["grid"]:
        A(
            f"| {row['lookback']} | {row['cap']:.2f} | "
            f"{fmt(row['wf_mean_test_sharpe'])} | {fmt(row['wf_median_test_sharpe'])} | "
            f"{fmt(row['wf_mean_test_sharpe_canonical'])} | "
            f"{fmt(row['pct_positive_sharpe'])} | {row['total_test_trades']} | "
            f"{fmt(row['min_test_sharpe'])} | "
            f"{'PASS' if row['gates_passed'] else 'FAIL'} |"
        )
    A("")
    A(f"Maximum realised weight in the baseline book: "
      f"{fmt(base['weight_meta']['max_weight'])} "
      f"(cap {base['cap']:.2f}, at most {base['weight_meta']['max_cap_iterations']} "
      f"iterations, residual {fmt(base['weight_meta']['max_cap_residual'])}).")
    A(f"Rebalances formed: {base['weight_meta']['n_segments']}; first invested "
      f"session inside the evaluation window "
      f"{base['weight_meta']['first_invested_session']} "
      f"({base['weight_meta']['invested_sessions']} invested sessions).")
    A("")

    A("## 3. The baseline's walk-forward folds")
    A("")
    A("| Fold | Test window | OOS Sharpe | canonical | ann. return | max DD | ann. turnover | trades |")
    A("|---|---|---|---|---|---|---|---|")
    for row in base["folds"]:
        A(
            f"| {row['fold']} | {row['test_start']} .. {row['test_end']} | "
            f"{fmt(row['test_sharpe'])} | {fmt(row['test_sharpe_canonical'])} | "
            f"{fmt(row['test_ann_return'])} | {fmt(row['test_max_dd'])} | "
            f"{fmt(row['test_turnover'], 3)} | {row['test_trades']} |"
        )
    A("")

    A("## 4. Chronological splits (baseline)")
    A("")
    A("| Split | Window | Sharpe (backtest scale) | Sharpe (canonical) | ann. return | ann. vol | Sortino | max DD | profit factor | ann. turnover | trade days | exposure |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for name in ("train", "validation", "test"):
        m = base["split_metrics"][name]
        A(
            f"| {name} | {m['start_date']} .. {m['end_date']} | "
            f"{fmt(m['sharpe_backtest_scale'])} | {fmt(m['sharpe_canonical'])} | "
            f"{fmt(m['annualized_return'])} | {fmt(m['annualized_volatility'])} | "
            f"{fmt(m['sortino_ratio'])} | {fmt(m['max_drawdown'])} | "
            f"{fmt(m['profit_factor'], 3)} | {fmt(m['annualized_turnover'], 3)} | "
            f"{m['trade_days']} | {fmt(m['avg_exposure'])} |"
        )
    A("")

    A("## 5. Benchmarks and diversification")
    A("")
    A("| Reference | Window | Sharpe (backtest scale) | canonical | ann. return | max DD | ann. turnover |")
    A("|---|---|---|---|---|---|---|")
    for label, key in (("1/N equal weight", "one_over_n"), ("SPY buy-and-hold", "spy")):
        for scope in ("full", "test"):
            m = bench[key][scope]
            A(
                f"| {label} ({scope}) | {m['start_date']} .. {m['end_date']} | "
                f"{fmt(m['sharpe_backtest_scale'])} | {fmt(m['sharpe_canonical'])} | "
                f"{fmt(m['annualized_return'])} | {fmt(m['max_drawdown'])} | "
                f"{fmt(m['annualized_turnover'], 3)} |"
            )
    A("")
    A("The two ways of quoting a Sharpe are not interchangeable: the *whole-window*")
    A("rows above are a single Sharpe over the whole 21-year window, while the")
    A("walk-forward figure is the **mean of the per-fold Sharpes** (each fold is")
    A("a 12-month window). Averaging over shorter windows raises the mean")
    A("because the annualised volatility of a 12-month slice is smaller than the")
    A("volatility of the 21-year path. Both numbers are stated with their")
    A("definition, and only like-for-like pairs are compared.")
    A(f"- **1/N on the same walk-forward folds**: mean OOS Sharpe "
      f"{fmt(bench['one_over_n']['wf_mean_test_sharpe'])} "
      f"(canonical {fmt(bench['one_over_n']['wf_mean_test_sharpe_canonical'])}), "
      f"positive-fold rate {fmt(bench['one_over_n']['pct_positive_sharpe'])}.")
    A(f"- **Excess of the candidate over 1/N on the same folds**: "
      f"**{fmt(bench['excess_over_1n_wf_mean'])}** (backtest scale). This is the")
    A("  mechanism's contribution net of the equity beta a long-only seven-asset")
    A("  book earns anyway (AGENTS.md, \"Known confounders\").")
    A(f"- Correlation of the candidate's pooled out-of-sample returns with the "
      f"1/N benchmark: **{fmt(bench['corr_with_1n'])}**.")
    A(f"- Correlation with SPY buy-and-hold: **{fmt(bench['corr_with_spy'])}**.")
    A(f"- Correlation with the incumbent's path (reference only, a different "
      f"path and a different window): **{fmt(bench['corr_with_incumbent'])}**.")
    A("")

    A("## 6. Statistical validity")
    A("")
    psr = payload["psr"]
    dsr = payload["dsr"]
    A(f"- Probabilistic Sharpe Ratio against 0 (block bootstrap, "
      f"{BOOTSTRAP_DRAWS} draws, block {BLOCK_SIZE}): PSR(normal) = "
      f"{fmt(psr['psr_normal'])}, PSR(empirical) = {fmt(psr['psr_empirical'])}, "
      f"observed canonical Sharpe {fmt(psr['sharpe_observed'])} "
      f"(95% CI {fmt(psr['ci_lower'])} .. {fmt(psr['ci_upper'])}).")
    A(f"- Deflated Sharpe Ratio at the declared N = {dsr['n_configs']}: "
      f"DSR = {fmt(dsr['dsr'])}, probability = {fmt(dsr['dsr_probability'])}, "
      f"selection threshold {fmt(dsr['sr_threshold'])} "
      f"(E[max] = {fmt(dsr['e_max'])}).")
    A("")

    A("## 7. Cost sensitivity")
    A("")
    cs = payload["cost_sensitivity"]
    A(f"- Walk-forward mean OOS Sharpe at 0 bp per unit: {fmt(cs['sharpe_at_0bps'])};")
    A(f"  at the committed 3 bp per unit: **{fmt(cs['sharpe_at_3bps'])}**; at 10 bp: "
      f"{fmt(cs['sharpe_at_10bps'])}.")
    gate1 = cs["gate1_flip_bps"]
    A(f"- Gate 1 (WF mean OOS Sharpe >= {cs['gate']}) flip cost: "
      f"{'never flips (already fails at 0 bp)' if gate1 is None else f'{gate1:.1f} bp per unit'}.")
    gate2 = cs["gate2_flip_bps"]
    A(f"- Gate 2 (positive-fold rate >= {GATE_POSITIVE_FOLD_MIN}) flip cost: "
      f"{'never flips' if gate2 is None else f'{gate2:.1f} bp per unit'}.")
    A(f"- Edge-erosion cost (the largest cost at which the walk-forward mean "
      f"OOS Sharpe is still above zero): **{cs['erosion_bps']:.1f} bp per unit**.")
    A("")

    A("## 8. Robustness (plateau)")
    A("")
    A("| Volatility lookback | mean WF OOS Sharpe over the three caps |")
    A("|---|---|")
    for L, row in payload["lookback_plateau"].items():
        A(f"| {L} | {fmt(row['mean_test_sharpe'])} |")
    A("")
    A("| Cap | mean WF OOS Sharpe over the three lookbacks |")
    A("|---|---|")
    for cap, row in payload["cap_plateau"].items():
        A(f"| {cap} | {fmt(row['mean_test_sharpe'])} |")
    A("")

    A("## 9. What this does and does not change")
    A("")
    A("- **Nothing published changed.** The published record, the published")
    A("  gates, the published protocol, the committed shortlist and every")
    A("  committed candidate artefact are byte-identical after the run; the")
    A("  fetcher was never called and `data/` and `config/` are byte-identical.")
    A("- **A new candidate was evaluated, not a new edge claimed.** The")
    A("  decision and the label are stated above; a candidate that fails the")
    A("  pre-registered gates is archived with its evidence.")
    A("- **The incumbent's verdict is unchanged.** It remains a Credible")
    A("  Candidate by its published verdict and NO-GO for promotion.")
    A("- **The comparison is like-for-like on the window, not on the path.**")
    A("  The candidate is measured on the point-in-time-complete window; the")
    A("  incumbent's published record is measured on its own window, and the")
    A("  correlation with it is reported as a diversification reference only.")
    A("")

    A("## 10. Reproduction")
    A("")
    A("```bash")
    A("python research/riskparity_001_eval.py")
    A("python -m pytest -q tests/test_riskparity_001_evaluation.py")
    A("git status --porcelain data/ config/")
    A("```")
    A("")
    A("Every number in this report is re-derived by the first command from the")
    A("committed cache, `config/` and the committed hypothesis document.")
    A("")
    return "\n".join(lines)


def render_experiment(payload: dict[str, Any]) -> str:
    base = payload["baseline"]
    bench = payload["benchmarks"]
    lines: list[str] = []
    A = lines.append

    A(f"# Experiment: riskparity_001_evaluation (Cycle {payload['cycle']})")
    A("")
    A("**Hypothesis reference:** `research/hypotheses/riskparity_001.md`")
    A("(pre-registered; this experiment executes its evaluation plan unchanged).")
    A("")
    A("## Data used")
    A("")
    A("- **Source:** committed parquet cache `data/raw/`; the fetcher is never")
    A("  called and nothing under `data/` or `config/` is written.")
    A(f"- **Date range:** {payload['evaluation_start']} .. "
      f"{payload['evaluation_end']} (the pre-registered point-in-time-complete")
    A("  window; the first session on which all seven members carry a valid")
    A("  lagged 63-session volatility estimate is measured from the cache).")
    A("- **Frequency:** daily (UTC session index).")
    A(f"- **Universe:** {', '.join(payload['universe'])} (the incumbent's universe).")
    A("- **Point-in-time treatment:** the volatility estimate is lagged (it uses")
    A("  the returns up to and including the session *before* the rebalance), the")
    A("  book formed on the last session of a month is effective from the next")
    A("  session, and no price is forward filled across a member's inception")
    A("  inside the evaluation window.")
    A("")
    A("## Configuration")
    A("")
    A(f"- **Candidate:** `riskparity_001` — long-only inverse-volatility, "
      f"monthly rebalance, L = {base['lookback']}, per-asset cap "
      f"{base['cap']:.2f} (baseline).")
    A(f"- **Cost model:** {payload['commission_bps']:.1f} bp commission + "
      f"{payload['slippage_bps']:.1f} bp slippage = "
      f"{payload['cost_per_unit'] * 10000:.1f} bp per unit of weight change; "
      f"risk-free {payload['risk_free_annual'] * 100:.2f}%.")
    A("- **Walk-forward:** 10y train / 12m test / 6m step, 21d purge, 21d")
    A("  embargo, fixed parameters (no per-fold re-optimisation).")
    A("- **Splits:** train .. " + payload["train_end"] + ", validation .. "
      + payload["validation_end"] + ", test .. end of cache (chronological,")
    A("  non-overlapping).")
    A("")
    A("## Results")
    A("")
    A("| Quantity | Value |")
    A("|---|---|")
    A(f"| Walk-forward folds | {payload['n_folds']} |")
    A(f"| WF mean OOS Sharpe (backtest scale) | "
      f"{fmt(base['wf_mean_test_sharpe'])} |")
    A(f"| WF mean OOS Sharpe (canonical) | "
      f"{fmt(base['wf_mean_test_sharpe_canonical'])} |")
    A(f"| Median fold Sharpe | {fmt(base['wf_median_test_sharpe'])} |")
    A(f"| Worst fold Sharpe | {fmt(base['min_test_sharpe'])} |")
    A(f"| Positive-fold rate | {fmt(base['pct_positive_sharpe'])} |")
    A(f"| Pooled out-of-sample trades | {base['total_test_trades']} |")
    for name, gate in base["gates"].items():
        A(f"| Gate `{name}` | {fmt(float(gate['value']))} "
          f"{gate['comparison']} {fmt(float(gate['threshold']))} -> "
          f"{'PASS' if gate['passed'] else 'FAIL'} |")
    A(f"| Test-period Sharpe (chronological split) | "
      f"{fmt(base['split_metrics']['test']['sharpe_backtest_scale'])} |")
    A(f"| 1/N benchmark, test window | "
      f"{fmt(bench['one_over_n']['test']['sharpe_backtest_scale'])} |")
    A(f"| 1/N benchmark, walk-forward mean OOS Sharpe (same folds) | "
      f"{fmt(bench['one_over_n']['wf_mean_test_sharpe'])} |")
    A(f"| Excess of the candidate over 1/N (same folds) | "
      f"{fmt(bench['excess_over_1n_wf_mean'])} |")
    A(f"| SPY buy-and-hold, test window | "
      f"{fmt(bench['spy']['test']['sharpe_backtest_scale'])} |")
    A(f"| Correlation with 1/N | {fmt(bench['corr_with_1n'])} |")
    A(f"| Correlation with SPY | {fmt(bench['corr_with_spy'])} |")
    A(f"| Correlation with the incumbent | {fmt(bench['corr_with_incumbent'])} |")
    A(f"| PSR against 0 | {fmt(payload['psr']['psr_normal'])} |")
    A(f"| DSR at N = {payload['dsr']['n_configs']} | "
      f"{fmt(payload['dsr']['dsr'])} (probability "
      f"{fmt(payload['dsr']['dsr_probability'])}) |")
    A(f"| Edge-erosion cost per unit (WF mean <= 0) | "
      f"{payload['cost_sensitivity']['erosion_bps']:.1f} bp |")
    A(f"| Decision | **{payload['decision']}** |")
    A(f"| Label | {payload['label']} |")
    A("")
    A("## Number of trials")
    A("")
    A(f"**{len(payload['grid'])}** — exactly the pre-registered grid "
      "(L in {21, 63, 126} x cap in {0.25, 0.30, 0.40}); no configuration was")
    A("added, removed or re-selected after the run. The Deflated Sharpe Ratio")
    A(f"is computed at N = {payload['dsr']['n_configs']}.")
    A("")
    A("## Reproduction commands")
    A("")
    A("```bash")
    A("python research/riskparity_001_eval.py")
    A("python -m pytest -q tests/test_riskparity_001_evaluation.py")
    A("git status --porcelain data/ config/")
    A("```")
    A("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="print the measurement without writing the report and experiment files",
    )
    args = parser.parse_args(argv)

    payload = run_evaluation()

    if not args.no_report:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
        OUT_REPORT.write_text(render_report(payload), encoding="utf-8")
        OUT_EXP.write_text(render_experiment(payload), encoding="utf-8")

    base = payload["baseline"]
    print(f"STRUCTURAL: {'PASS' if payload['structural_pass'] else 'FAIL'}")
    for check in payload["checks"]:
        print(f"CHECK|{check['name']}|{'PASS' if check['pass'] else 'FAIL'}")
    for name, gate in base["gates"].items():
        print(
            f"GATE|{name}|{float(gate['value']):.6f}|"
            f"{float(gate['threshold']):.6f}|{gate['comparison']}|"
            f"{'PASS' if gate['passed'] else 'FAIL'}"
        )
    print(
        f"WF_MEAN_OOS_SHARPE|{base['wf_mean_test_sharpe']:.6f}|"
        f"{payload['n_folds']}"
    )
    print(f"WF_MEAN_CANONICAL|{base['wf_mean_test_sharpe_canonical']:.6f}")
    print(f"POSITIVE_FOLD_RATE|{base['pct_positive_sharpe']:.6f}")
    print(f"POOLED_OOS_TRADES|{base['total_test_trades']}")
    print(f"TRIALS|{len(payload['grid'])}")
    gate1_flip = payload["cost_sensitivity"]["gate1_flip_bps"]
    print(
        f"GATE1_FLIP_BPS|"
        f"{'none' if gate1_flip is None else f'{gate1_flip:.1f}'}"
    )
    print(
        f"EROSION_BPS_PER_UNIT|"
        f"{payload['cost_sensitivity']['erosion_bps']:.1f}"
    )
    print(
        f"EXCESS_OVER_1N|"
        f"{payload['benchmarks']['excess_over_1n_wf_mean']:.6f}"
    )
    print(f"CORR_1N|{payload['benchmarks']['corr_with_1n']:.6f}")
    print(f"CORR_INCUMBENT|{payload['benchmarks']['corr_with_incumbent']:.6f}")
    print(f"DECISION|{payload['decision']}")
    print(f"LABEL|{payload['label']}")
    print(f"REPORT|{OUT_REPORT if not args.no_report else '(not written: --no-report)'}")
    print(f"EXPERIMENT|{OUT_EXP if not args.no_report else '(not written: --no-report)'}")
    return 0 if payload["structural_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
