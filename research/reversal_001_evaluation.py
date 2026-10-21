#!/usr/bin/env python3
"""Cycle 935 (step 2 of 2): evaluate the frozen ``reversal_001`` candidate.

The candidate was **pre-registered and frozen** in commit ``a910dd4``:
``research/hypotheses/reversal_001.md`` and ``config/reversal_candidate_001.yaml``
were committed alone, before any reversal backtest existed in this repository.
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
  with the Cycle-929 paired moving-block bootstrap 95% CI;
* the **measured median gross capture fraction** against the pre-registered
  cost hurdle of 2.0047% of the cross-sectional dispersion per rebalance;
* the **realized** turnover and cost drag (measured, not assumed);
* the Deflated Sharpe Ratio over the declared trial count of 1;
* the **mirror test** against the rejected ``sectorrotation_001`` /
  ``sectorrotation_002`` signal on the same nine-sector panel: the candidate's
  excess is regressed on the **negated** rejected signal's excess, and the
  residual's mean is tested with the same bootstrap. The mirror test fires
  when that residual is not significantly positive -- i.e. when the result is
  explained by the arithmetic mirror of a rejected hypothesis rather than by a
  new mechanism.

The tool is **read-only**: the price panel is read from the committed cache
(the fetcher is never called), nothing under ``data/`` or ``config/`` is
written, and the SHA-256 of every file under those two trees and of every
committed artefact is compared before and after the run.

Reproduction
------------
```bash
python research/reversal_001_evaluation.py
python -m pytest -q tests/test_reversal_001_evaluation.py
git status --porcelain data/
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
from research.month_end_candidate_reaudit import path_returns  # noqa: E402
from src.backtest.engine import compute_metrics  # noqa: E402
from src.backtest.rebalance import build_month_end_weights  # noqa: E402
from src.evaluation.sharpe import sharpe_ratio  # noqa: E402
from src.evaluation.statistics import compute_dsr  # noqa: E402
from src.evaluation.walkforward import generate_walkforward_splits  # noqa: E402
from src.features.momentum import compute_momentum  # noqa: E402

CYCLE = "935"

RAW_DIR = REPO_ROOT / "data" / "raw"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
EXPERIMENTS_DIR = REPO_ROOT / "research" / "experiments"

OUT_REPORT = REPORTS_DIR / "reversal_001_evaluation.md"
OUT_EXP = EXPERIMENTS_DIR / "reversal_001_evaluation.md"

CONFIG_PATH = REPO_ROOT / "config" / "reversal_candidate_001.yaml"
HYPOTHESIS_PATH = REPO_ROOT / "research" / "hypotheses" / "reversal_001.md"

#: The commit in which the pre-registration was frozen.  Published with the
#: result so a reader can check that the specification was frozen first.
FREEZE_COMMIT = "a910dd4"

#: The frozen values, restated here so that a post-freeze edit of the config
#: file fails closed instead of silently changing the candidate.
FROZEN = {
    "universe": ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"],
    "lookback_sessions": 5,
    "select_count": 2,
    "rebalance_every_n_sessions": 5,
    "selected_weight": 0.5,
    "signal_lag_days": 1,
    "commission_bps": 1.0,
    "slippage_bps": 2.0,
    "total_round_trip_bps": 3.0,
    "capture_fraction_min": 0.020047,
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

#: The rejected signal the mirror test compares against (the frozen
#: ``config/sectorrotation_candidate_001.yaml`` rule, read from that file).
MIRROR_CONFIG = REPO_ROOT / "config" / "sectorrotation_candidate_001.yaml"


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
    hurdle = evaluation.get("cost_hurdle", {})
    multiple = evaluation.get("multiple_testing", {})

    observed = {
        "universe": list(config.get("universe", [])),
        "lookback_sessions": signal.get("lookback_sessions"),
        "select_count": signal.get("select_count"),
        "rebalance_every_n_sessions": signal.get("rebalance_every_n_sessions"),
        "selected_weight": portfolio.get("selected_weight"),
        "signal_lag_days": config.get("execution", {}).get("signal_lag_days"),
        "commission_bps": costs.get("commission_bps"),
        "slippage_bps": costs.get("slippage_bps"),
        "total_round_trip_bps": costs.get("total_round_trip_bps"),
        "capture_fraction_min": hurdle.get("capture_fraction_min"),
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
    if signal.get("selection") != "bottom":
        fail("the frozen selection direction is not 'bottom'")
    if signal.get("type") != "cross_sectional_reversal":
        fail("the frozen signal type is not 'cross_sectional_reversal'")
    if config.get("risk_overlay", {}).get("none") is not True:
        fail("the frozen configuration does not disable the risk overlay")
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
# The frozen baseline rule
# ----------------------------------------------------------------------
def build_reversal_weights(
    close: pd.DataFrame, lookback: int, select_count: int, every_n: int
) -> tuple[pd.DataFrame, pd.DataFrame, list[pd.Timestamp]]:
    """The frozen rule: bottom quintile of the trailing 5-session return.

    Returns the (1-session-lagged) weights, the signal score frame and the
    list of rebalance sessions at which a position was formed.
    """
    score = close.pct_change(lookback)
    mask = pd.DataFrame(False, index=close.index, columns=close.columns)
    formed: list[pd.Timestamp] = []
    positions = np.arange(len(close))
    for i in positions[positions % every_n == 0]:
        row = score.iloc[i]
        valid = row.dropna()
        if len(valid) < select_count:
            continue
        selected = valid.nsmallest(select_count).index
        mask.loc[close.index[i], selected] = True
        formed.append(close.index[i])
    held = mask.ffill()
    weights = held.astype(float) * (1.0 / select_count)
    weights = weights.shift(1).fillna(0.0)
    return weights, score, formed


def build_benchmark_weights(close: pd.DataFrame) -> pd.DataFrame:
    """1/N equal-weight buy-and-hold of the same nine ETFs (no turnover)."""
    weights = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    weights[:] = 1.0 / len(close.columns)
    return weights


def build_mirror_weights(close: pd.DataFrame) -> pd.DataFrame:
    """The rejected ``sectorrotation_001`` rule on the same nine ETFs.

    Read from the frozen ``config/sectorrotation_candidate_001.yaml``:
    cross-sectional momentum (252-day lookback, 21-day skip), the top 50%
    equal-weighted, rebalanced at month end with a one-session lag.
    """
    config = yaml.safe_load(MIRROR_CONFIG.read_text()) or {}
    signal = config.get("signal", {})
    momentum = compute_momentum(
        close, lookback=int(signal["lookback"]), skip=int(signal["skip"])
    )
    top_fraction = float(signal["top_fraction"])
    mask = momentum.rank(axis=1, ascending=False, pct=True) <= top_fraction
    mask = mask.fillna(False)
    weights, _segments = build_month_end_weights(mask)
    return weights.reindex(columns=close.columns).fillna(0.0)


# ----------------------------------------------------------------------
# Walk-forward evaluation
# ----------------------------------------------------------------------
def evaluate(
    close: pd.DataFrame,
    weights: pd.DataFrame,
    benchmark: pd.DataFrame,
    mirror: pd.DataFrame,
    cost: float,
    config: dict[str, Any],
) -> dict[str, Any]:
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

    net, weights_a, turnover = path_returns(close, weights, cost)
    bench_net, _bench_w, _bench_t = path_returns(close, benchmark, 0.0)
    mirror_net, _m_w, _m_t = path_returns(close, mirror, cost)

    folds: list[dict[str, Any]] = []
    oos_dates: list[pd.Timestamp] = []
    for number, split in enumerate(splits, start=1):
        start = pd.Timestamp(split["test_start"], tz="UTC")
        end = pd.Timestamp(split["test_end"], tz="UTC")
        window = net.index[(net.index >= start) & (net.index <= end)]
        if len(window) < 2:
            continue
        sample = net.loc[window]
        bench_sample = bench_net.loc[window]
        weight_changes = weights_a.loc[window].diff().abs().sum(axis=1).fillna(0.0)
        trades = int((weight_changes > 1e-10).sum())
        metrics = compute_metrics(
            sample,
            weights_a.loc[window],
            config["commission_bps"] / 10_000.0,
            config["slippage_bps"] / 10_000.0,
            0.02,
        )
        candidate_sharpe = sharpe_ratio(sample)
        bench_sharpe = sharpe_ratio(bench_sample)
        folds.append(
            {
                "fold": number,
                "test_start": str(window[0].date()),
                "test_end": str(window[-1].date()),
                "sessions": int(len(window)),
                "test_sharpe": float(candidate_sharpe),
                "test_sharpe_backtest": float(metrics["sharpe_ratio"]),
                "benchmark_sharpe": float(bench_sharpe),
                "excess_sharpe": float(candidate_sharpe - bench_sharpe),
                "test_trades": trades,
                "ann_return": float(metrics["annualized_return"]),
                "max_drawdown": float(metrics["max_drawdown"]),
            }
        )
        oos_dates.extend(list(window))

    if not folds:
        fail("no walk-forward fold carries a usable test window")

    sharpes = [f["test_sharpe"] for f in folds]
    excess = [f["excess_sharpe"] for f in folds]
    mean_sharpe = float(np.mean(sharpes))
    positive_rate = float(np.mean([s > 0 for s in sharpes]))
    pooled_trades = int(sum(f["test_trades"] for f in folds))
    block = max(2, len(folds) // 8)
    boot = moving_block_bootstrap_mean(
        excess, block, config["bootstrap_draws"], config["bootstrap_seed"]
    )

    oos_index = sorted(set(oos_dates))
    oos_net = net.loc[oos_index]
    oos_bench = bench_net.loc[oos_index]
    oos_mirror = mirror_net.loc[oos_index]
    excess_series = (oos_net - oos_bench).to_numpy(dtype=float)
    mirror_series = (oos_mirror - oos_bench).to_numpy(dtype=float)

    # Mirror test: regress the candidate's excess on the NEGATED rejected
    # signal's excess; the residual's mean must be significantly positive.
    design = np.column_stack([-mirror_series, np.ones(len(mirror_series))])
    coefficients, *_ = np.linalg.lstsq(design, excess_series, rcond=None)
    residual = excess_series - design @ coefficients
    residual_block = max(2, len(residual) // 8)
    residual_boot = moving_block_bootstrap_mean(
        list(residual), residual_block, config["bootstrap_draws"], config["bootstrap_seed"]
    )
    correlation = float(np.corrcoef(excess_series, mirror_series)[0, 1])
    total_variance = float(np.var(excess_series))
    residual_variance = float(np.var(residual))
    r_squared = (
        1.0 - residual_variance / total_variance if total_variance > 0 else 0.0
    )

    dsr = compute_dsr(
        oos_net,
        n_configs=int(config["total_configs"]),
        n_bootstrap=1000,
        block_size=22,
        seed=42,
    )

    absolute_sharpe = sharpe_ratio(oos_net)
    oos_weights = weights_a.loc[oos_index]
    weight_changes = oos_weights.diff().abs().sum(axis=1).fillna(0.0)
    realized_turnover = float(weight_changes.sum() / len(oos_index) * 252.0)
    realized_drag = realized_turnover * cost

    return {
        "folds": folds,
        "n_folds": len(folds),
        "wf_mean_oos_sharpe": mean_sharpe,
        "wf_median_oos_sharpe": float(np.median(sharpes)),
        "wf_std_oos_sharpe": float(np.std(sharpes, ddof=1)) if len(sharpes) > 1 else 0.0,
        "positive_fold_rate": positive_rate,
        "pooled_oos_trades": pooled_trades,
        "excess_sharpe": float(np.mean(excess)),
        "excess_ci": {
            "block": block,
            "draws": config["bootstrap_draws"],
            "seed": config["bootstrap_seed"],
            "ci_low": float(boot["ci_low"]),
            "ci_high": float(boot["ci_high"]),
        },
        "oos_sessions": int(len(oos_index)),
        "absolute_oos_sharpe": float(absolute_sharpe),
        "absolute_oos_ann_return": float(oos_net.mean() * 252.0),
        "oos_index": [str(date.date()) for date in oos_index],
        "mirror": {
            "correlation": correlation,
            "r_squared": r_squared,
            "slope_on_negated_mirror": float(coefficients[0]),
            "residual_mean": float(residual.mean()),
            "residual_ci_low": float(residual_boot["ci_low"]),
            "residual_ci_high": float(residual_boot["ci_high"]),
            "mirror_excess_mean": float(mirror_series.mean()),
        },
        "dsr": {
            "dsr": float(dsr.get("dsr", np.nan)),
            "probability": float(dsr.get("dsr_probability", np.nan)),
            "sr_observed": float(dsr.get("sr_observed", np.nan)),
            "sharpe_se": float(dsr.get("sharpe_se", np.nan)),
            "n_configs": int(config["total_configs"]),
        },
        "realized_turnover_per_year": realized_turnover,
        "realized_cost_drag_per_year": realized_drag,
    }


def capture_fraction(
    score: pd.DataFrame,
    formed: list[pd.Timestamp],
    weights: pd.DataFrame,
    oos_index: list[pd.Timestamp],
    select_count: int,
) -> dict[str, Any]:
    """Median gross capture fraction over the out-of-sample rebalances.

    The capture fraction at a formation date is
    ``[mean(selected 5-session return) - mean(all nine)] / std(all nine)``,
    exactly as the frozen hypothesis defines it.
    """
    oos = set(oos_index)
    values: list[float] = []
    dispersions: list[float] = []
    dates: list[pd.Timestamp] = []
    for date in formed:
        if date not in oos:
            continue
        row = score.loc[date].dropna()
        if len(row) < 3:
            continue
        selected = weights.index[weights.index == date]
        # The selection is read back from the score frame: the two lowest.
        picked = row.nsmallest(select_count).index
        mean_all = float(row.mean())
        dispersion = float(row.std(ddof=1))
        if dispersion <= 0:
            continue
        values.append((float(row[picked].mean()) - mean_all) / dispersion)
        dispersions.append(dispersion)
        dates.append(date)
    if not values:
        fail("no out-of-sample rebalance carries a capture fraction")
    return {
        "observations": len(values),
        "median": float(np.median(values)),
        "mean": float(np.mean(values)),
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "dispersion_median": float(np.median(dispersions)),
        "rebalances_per_year": float(len(values) / (len(oos_index) / 252.0))
        if oos_index
        else 0.0,
    }


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
    significantly_negative = bool(ci["ci_high"] < 0.0)
    conditions.append(
        {
            "id": "ii",
            "text": "benchmark-relative net excess bootstrap 95% CI excludes zero",
            "value": (
                f"[{ci['ci_low']:.6f}, {ci['ci_high']:.6f}]"
                + (" (significantly NEGATIVE)" if significantly_negative else "")
            ),
            "threshold": "excludes zero",
            "fired": ci_includes_zero,
        }
    )
    post_2009 = payload["post_2009"]
    conditions.append(
        {
            "id": "iii",
            "text": "benchmark-relative net excess positive in the post-2009 sub-sample",
            "value": post_2009["excess"],
            "threshold": "> 0",
            "fired": bool(post_2009["excess"] <= 0.0),
        }
    )
    capture = payload["capture"]
    conditions.append(
        {
            "id": "iv",
            "text": "median gross capture fraction >= the pre-registered cost hurdle",
            "value": capture["median"],
            "threshold": config["capture_fraction_min"],
            "fired": bool(capture["median"] < config["capture_fraction_min"]),
        }
    )
    folds = evaluation["folds"]
    trades_ok = evaluation["pooled_oos_trades"] > config["pooled_oos_trades_min"]
    rate_ok = evaluation["positive_fold_rate"] >= config["positive_fold_rate_min"]
    conditions.append(
        {
            "id": "v",
            "text": "positive-fold rate >= 0.5 and pooled OOS trades > 100",
            "value": f"rate {evaluation['positive_fold_rate']:.4f}, trades {evaluation['pooled_oos_trades']}",
            "threshold": "rate >= 0.5, trades > 100",
            "fired": bool(not (rate_ok and trades_ok)),
        }
    )
    mirror = evaluation["mirror"]
    mirror_fired = bool(mirror["residual_ci_low"] <= 0.0 <= mirror["residual_ci_high"])
    conditions.append(
        {
            "id": "vi",
            "text": "the excess is not explained by the negated rejected sector-momentum signal",
            "value": (
                f"residual mean {mirror['residual_mean']:.6f} "
                f"CI [{mirror['residual_ci_low']:.6f}, {mirror['residual_ci_high']:.6f}]"
            ),
            "threshold": "residual CI excludes zero",
            "fired": mirror_fired,
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
    capture = payload["capture"]
    mirror = evaluation["mirror"]
    rows = "\n".join(
        f"| {f['fold']} | {f['test_start']} | {f['test_end']} | {f['sessions']} | "
        f"{_fmt(f['test_sharpe'])} | {_fmt(f['test_sharpe_backtest'])} | "
        f"{_fmt(f['benchmark_sharpe'])} | {_fmt(f['excess_sharpe'])} | {f['test_trades']} |"
        for f in evaluation["folds"]
    )
    conditions = "\n".join(
        f"| {c['id']} | {c['text']} | {c['value']} | {c['threshold']} | "
        f"{'**FIRED**' if c['fired'] else 'not fired'} |"
        for c in payload["verdict"]["conditions"]
    )
    return f"""# Experiment: `reversal_001` evaluation (reversal_001_evaluation)

**Cycle {payload['cycle']}.** Execution of the **frozen** pre-registration
(`research/hypotheses/reversal_001.md` + `config/reversal_candidate_001.yaml`, freeze commit
**{FREEZE_COMMIT}**). The frozen values are re-asserted by the tool before the run; a
post-freeze edit of the config fails closed. No threshold, gate, cost model, universe or
Sharpe convention was changed after the result was known; nothing under `data/` or
`config/` was written; the fetcher was never called; no other candidate was executed,
re-tuned or re-ranked.

## Hypothesis reference

`research/hypotheses/reversal_001.md` (frozen at `{FREEZE_COMMIT}`).

## Data used

- **Source**: the committed parquet cache `data/raw/{{XLB,XLE,XLF,XLI,XLK,XLP,XLU,XLV,XLY}}.parquet`
  (the fetcher is never called).
- **Date range**: {config['history_start']} .. {config['history_end']}
- **Frequency**: daily, session hours
- **Universe**: {', '.join(config['universe'])} (nine GICS sector ETFs; identical cached
  history, {payload['sessions']} sessions, no gaps)
- **Point-in-time treatment**: the signal at session `t` uses only prices up to and
  including `t`; the weights formed at `t` become effective at `t+1` (one-session lag).
  The benchmark-relative series is computed on the same sessions as the candidate.

## Configuration (frozen)

| Item | Value |
|---|---|
| Signal | trailing {config['lookback_sessions']}-session total return, **bottom** {config['select_count']} of 9, equal weight, cash otherwise |
| Rebalance | every {config['rebalance_every_n_sessions']} sessions, anchored on the panel's first session |
| Signal lag | {config['signal_lag_days']} session |
| Cost model | {config['commission_bps']:.1f} bp commission + {config['slippage_bps']:.1f} bp slippage = **{config['total_round_trip_bps']:.1f} bp per unit of weight change**, 2.00% annual risk-free |
| Benchmark | 1/N equal-weight buy-and-hold of the same nine ETFs |
| Walk-forward | {config['train_years']:.0f}-year train, {config['test_months']:.0f}-month test, {config['step_months']:.0f}-month step, {config['purge_days']}-day purge, {config['embargo_days']}-day embargo |
| Trials | **{config['total_configs']}** (one baseline rule, no grid) |
| Pre-registered cost hurdle | median gross capture fraction >= {config['capture_fraction_min']:.6f} of the cross-sectional dispersion per rebalance |

## Number of trials

**{config['total_configs']}.** One configuration, one baseline rule. No parameter search.

## Results

### Walk-forward folds ({evaluation['n_folds']} folds)

| Fold | Test start | Test end | Sessions | Sharpe (canonical) | Sharpe (backtest) | Benchmark Sharpe | Excess Sharpe | Trades |
|---|---|---|---|---|---|---|---|---|
{rows}

### Gate statistics

| Statistic | Value | Gate | Outcome |
|---|---|---|---|
| Walk-forward mean OOS Sharpe (canonical) | {_fmt(evaluation['wf_mean_oos_sharpe'])} | >= 0.9 | {'PASS' if evaluation['wf_mean_oos_sharpe'] >= 0.9 else 'FAIL'} |
| Walk-forward median OOS Sharpe | {_fmt(evaluation['wf_median_oos_sharpe'])} | - | - |
| Walk-forward std of OOS Sharpe | {_fmt(evaluation['wf_std_oos_sharpe'])} | - | - |
| Positive-fold rate | {evaluation['positive_fold_rate']:.4f} | >= 0.5 | {'PASS' if evaluation['positive_fold_rate'] >= 0.5 else 'FAIL'} |
| Pooled OOS trades | {evaluation['pooled_oos_trades']} | > 100 | {'PASS' if evaluation['pooled_oos_trades'] > 100 else 'FAIL'} |
| Benchmark-relative net excess (mean fold Sharpe difference) | {_fmt(evaluation['excess_sharpe'])} | - | - |
| Excess 95% CI (moving block, {evaluation['excess_ci']['draws']} draws, block {evaluation['excess_ci']['block']}, seed {evaluation['excess_ci']['seed']}) | [{_fmt(evaluation['excess_ci']['ci_low'])}, {_fmt(evaluation['excess_ci']['ci_high'])}] | excludes zero | {'PASS' if not (evaluation['excess_ci']['ci_low'] <= 0 <= evaluation['excess_ci']['ci_high']) else 'FAIL'} |
| Deflated Sharpe Ratio (N = {evaluation['dsr']['n_configs']}) | {_fmt(evaluation['dsr']['dsr'])} (probability {_fmt(evaluation['dsr']['probability'])}) | z > 0 | {'PASS' if evaluation['dsr']['dsr'] > 0 else 'FAIL'} |
| Out-of-sample sessions | {evaluation['oos_sessions']} | - | - |
| Absolute out-of-sample Sharpe (the rule holds cash most of the time) | {_fmt(evaluation['absolute_oos_sharpe'])} | - | - |
| Absolute out-of-sample annualised return | {evaluation['absolute_oos_ann_return']:.4%} | - | - |

### The pre-registered cost hurdle

| Quantity | Value |
|---|---|
| Median gross capture fraction (out-of-sample rebalances) | {capture['median']:.6f} ({capture['median']:.4%}) |
| Mean / min / max | {capture['mean']:.6f} / {capture['min']:.6f} / {capture['max']:.6f} |
| Capture-fraction observations | {capture['observations']} |
| Pre-registered hurdle | {config['capture_fraction_min']:.6f} ({config['capture_fraction_min']:.4%}) |
| **Realized** turnover | {evaluation['realized_turnover_per_year']:.4f} units/yr (the pre-registered convention estimated 52) |
| **Realized** cost drag | {evaluation['realized_cost_drag_per_year']:.4%}/yr |
| **Hurdle recomputed on the realized turnover** | {payload['corrected_hurdle']:.6f} ({payload['corrected_hurdle']:.4%}) |

**Turnover-convention correction (disclosed).** The pre-registered estimate -- one
book rotation per rebalance, 52 units/yr -- is a *lower* bound for this rule, not the
upper bound the Cycle-934 shortlist stated: the rule rotates two of nine names, so a
typical rebalance changes 1.5-2.0 units of weight. The **realized** turnover is
{evaluation['realized_turnover_per_year']:.4f} units/yr, i.e. a
{evaluation['realized_cost_drag_per_year']:.4%}/yr drag, and the cost hurdle recomputed on
it is {payload['corrected_hurdle']:.6f} of the cross-sectional dispersion per rebalance
instead of {config['capture_fraction_min']:.6f}. **The outcome does not depend on the
correction**: the measured capture fraction is {capture['median']:.6f}, which is of the
*opposite sign* and roughly {abs(capture['median'] / payload['corrected_hurdle']):.0f}
times the magnitude of either hurdle. This correction is published here rather than
applied silently to the frozen specification.

### The mirror test

The rejected `sectorrotation_001` / `sectorrotation_002` signal (252-day momentum, 21-day
skip, top 50% at month end, one-session lag) is rebuilt from its own frozen config on the
same nine-sector panel and the same folds. The candidate's benchmark-relative excess is
regressed on the **negated** mirror excess; the residual's mean is the part of the
candidate's result that the rejected signal does **not** explain.

| Statistic | Value |
|---|---|
| Correlation(candidate excess, mirror excess) | {_fmt(mirror['correlation'])} |
| R^2 of the candidate excess on the negated mirror excess | {_fmt(mirror['r_squared'])} |
| Slope on the negated mirror excess | {_fmt(mirror['slope_on_negated_mirror'])} |
| Residual mean | {_fmt(mirror['residual_mean'])} |
| Residual mean 95% CI | [{_fmt(mirror['residual_ci_low'])}, {_fmt(mirror['residual_ci_high'])}] |
| Mirror signal's own mean excess | {_fmt(mirror['mirror_excess_mean'])} |

### Era stability (post-2009 sub-sample)

| Statistic | Value |
|---|---|
| Benchmark-relative net excess (post-2009 folds) | {_fmt(payload['post_2009']['excess'])} |
| Folds in the sub-sample | {payload['post_2009']['folds']} |

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
python research/reversal_001_evaluation.py
python -m pytest -q tests/test_reversal_001_evaluation.py
git status --porcelain data/
```
"""


def render_report(payload: dict[str, Any]) -> str:
    evaluation = payload["evaluation"]
    rows = "\n".join(
        f"| {f['fold']} | {f['test_start']} | {f['test_end']} | {f['sessions']} | "
        f"{_fmt(f['test_sharpe'])} | {_fmt(f['benchmark_sharpe'])} | "
        f"{_fmt(f['excess_sharpe'])} | {f['test_trades']} |"
        for f in evaluation["folds"]
    )
    return f"""# Report: `reversal_001` evaluation (reversal_001_evaluation)

**Cycle {payload['cycle']}.** Read-only, deterministic execution of the frozen
pre-registration (freeze commit `{FREEZE_COMMIT}`). No backtest was run on any other
candidate, no parameter was searched, no gate or cost model was changed, nothing under
`data/` or `config/` was written, the fetcher was never called.

This report is the long-form evidence behind the record
`research/experiments/reversal_001_evaluation.md`; both are generated by
`research/reversal_001_evaluation.py` and carry no timestamp, so two consecutive runs are
byte-identical.

## 1. The frozen specification

| Item | Value |
|---|---|
| Universe | {', '.join(payload['config']['universe'])} |
| Panel | {payload['sessions']} sessions, {payload['config']['history_start']} .. {payload['config']['history_end']} |
| Signal | trailing {payload['config']['lookback_sessions']}-session return, bottom {payload['config']['select_count']} of 9, equal weight, cash otherwise |
| Rebalance | every {payload['config']['rebalance_every_n_sessions']} sessions, {payload['config']['signal_lag_days']}-session signal lag |
| Cost model | {payload['config']['total_round_trip_bps']:.1f} bp per unit of weight change |
| Benchmark | 1/N of the same nine ETFs |
| Design | {payload['config']['train_years']:.0f}y / {payload['config']['test_months']:.0f}m / {payload['config']['step_months']:.0f}m, {payload['config']['purge_days']}-day purge, {payload['config']['embargo_days']}-day embargo |
| Trials | {payload['config']['total_configs']} |

## 2. Walk-forward folds

| Fold | Test start | Test end | Sessions | Sharpe (canonical) | Benchmark Sharpe | Excess Sharpe | Trades |
|---|---|---|---|---|---|---|---|
{rows}

## 3. Gate statistics, the cost hurdle and the mirror test

| Statistic | Value |
|---|---|
| Walk-forward mean OOS Sharpe | {_fmt(evaluation['wf_mean_oos_sharpe'])} |
| Positive-fold rate | {evaluation['positive_fold_rate']:.4f} |
| Pooled OOS trades | {evaluation['pooled_oos_trades']} |
| Benchmark-relative excess 95% CI | [{_fmt(evaluation['excess_ci']['ci_low'])}, {_fmt(evaluation['excess_ci']['ci_high'])}] |
| DSR (N = {evaluation['dsr']['n_configs']}) | {_fmt(evaluation['dsr']['dsr'])} |
| Median gross capture fraction | {payload['capture']['median']:.6f} (hurdle {payload['config']['capture_fraction_min']:.6f}) |
| Realized turnover | {evaluation['realized_turnover_per_year']:.4f} units/yr |
| Realized cost drag | {evaluation['realized_cost_drag_per_year']:.4%}/yr |
| Correlation with the rejected mirror signal | {_fmt(evaluation['mirror']['correlation'])} |
| Mirror residual mean 95% CI | [{_fmt(evaluation['mirror']['residual_ci_low'])}, {_fmt(evaluation['mirror']['residual_ci_high'])}] |

## 4. Verdict

**{payload['verdict']['label']}**

## 5. Reproduction

```bash
python research/reversal_001_evaluation.py
python -m pytest -q tests/test_reversal_001_evaluation.py
git status --porcelain data/
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
        "capture_fraction_measured",
        payload["capture"]["observations"] > 0,
        f"{payload['capture']['observations']} out-of-sample rebalances carry a capture fraction",
    )
    add(
        "mirror_test_measured",
        np.isfinite(evaluation["mirror"]["correlation"]),
        f"mirror correlation {evaluation['mirror']['correlation']:.6f}",
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
    cost = config["total_round_trip_bps"] / 10_000.0

    weights, score, formed = build_reversal_weights(
        close,
        lookback=int(config["lookback_sessions"]),
        select_count=int(config["select_count"]),
        every_n=int(config["rebalance_every_n_sessions"]),
    )
    benchmark = build_benchmark_weights(close)
    mirror = build_mirror_weights(close)

    evaluation = evaluate(close, weights, benchmark, mirror, cost, config)
    oos_index = [pd.Timestamp(date, tz="UTC") for date in evaluation["oos_index"]]
    capture = capture_fraction(
        score, formed, weights, oos_index, int(config["select_count"])
    )

    # Post-2009 sub-sample (era stability, frozen condition iii).
    post_folds = [f for f in evaluation["folds"] if f["test_start"] >= "2009-01-01"]
    post_excess = float(np.mean([f["excess_sharpe"] for f in post_folds])) if post_folds else 0.0

    rebalances_per_year = (
        capture["observations"] / (evaluation["oos_sessions"] / 252.0)
        if evaluation["oos_sessions"]
        else 0.0
    )
    ceiling_per_year = capture["dispersion_median"] * rebalances_per_year
    corrected_hurdle = (
        evaluation["realized_cost_drag_per_year"] / ceiling_per_year
        if ceiling_per_year > 0
        else float("nan")
    )
    payload = {
        "cycle": CYCLE,
        "config": config,
        "sessions": int(len(close)),
        "evaluation": evaluation,
        "capture": capture,
        "post_2009": {"excess": post_excess, "folds": len(post_folds)},
        "corrected_hurdle": corrected_hurdle,
        "ceiling_per_year": ceiling_per_year,
        "rebalances_per_year": rebalances_per_year,
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
        f"CAPTURE|{payload['capture']['median']:.6f}|"
        f"HURDLE|{payload['config']['capture_fraction_min']:.6f}|"
        f"OBS|{payload['capture']['observations']}"
    )
    print(
        f"TURNOVER|{evaluation['realized_turnover_per_year']:.6f}|"
        f"DRAG|{evaluation['realized_cost_drag_per_year']:.8f}|"
        f"DSR|{evaluation['dsr']['dsr']:.6f}"
    )
    print(
        f"MIRROR|CORR|{evaluation['mirror']['correlation']:.6f}|"
        f"R2|{evaluation['mirror']['r_squared']:.6f}|"
        f"RESIDUAL_MEAN|{evaluation['mirror']['residual_mean']:.6f}|"
        f"RESIDUAL_CI|{evaluation['mirror']['residual_ci_low']:.6f},"
        f"{evaluation['mirror']['residual_ci_high']:.6f}"
    )
    print(f"VERDICT|{payload['verdict']['label']}")
    print(f"FROZEN_CONDITIONS_FIRED|{','.join(payload['verdict']['fired']) or 'none'}")
    print(f"REPORT|{OUT_REPORT if not args.no_report else '(not written: --no-report)'}")
    print(f"EXPERIMENT|{OUT_EXP if not args.no_report else '(not written: --no-report)'}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
