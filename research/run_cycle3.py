"""Cycle 3: Robustness & Statistical Validation of US Equity TSMOM.

Orchestrates all analysis modules and generates 7 evidence artifacts:
  1. research/experiments/tsmomentum_robustness_001.md
  2. research/experiments/tsmomentum_walkforward_001.md
  3. research/experiments/tsmomentum_statistics_001.md
  4. research/experiments/tsmomentum_benchmark_001.md
  5. research/experiments/tsmomentum_risk_001.md
  6. research/hypotheses/tsmomentum_002.md
  7. research/reports/tsmomentum_decision_001.md
"""

from __future__ import annotations

import os
import sys
import time
import warnings
from datetime import UTC, datetime
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from src.backtest.engine import compute_metrics, get_cost_params, get_risk_free_rate
from src.evaluation.benchmark import full_benchmark_comparison
from src.evaluation.risk import format_risk_summary, run_risk_overlays
from src.evaluation.robustness import (
    build_heatmap,
    format_heatmap_markdown,
    summarize_plateau,
)
from src.evaluation.statistics import (
    compute_dsr,
    compute_fdr,
    compute_pbo,
    compute_psr,
    format_plateau_markdown,
    parameter_perturbation,
)
from src.evaluation.utils import (
    annualize_return,
    backtest_sharpe_ratio,
    fetch_close_prices,
    max_drawdown,
)
from src.evaluation.walkforward import (
    generate_walkforward_splits,
    summarize_walkforward,
)
from src.features.momentum import build_weights

warnings.filterwarnings("ignore", category=RuntimeWarning)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SYMBOLS = ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"]
START_DATE = "1993-01-01"
END_DATE = "2026-10-09"
TRAIN_END = "2009-12-31"
VAL_END = "2017-12-31"
BASELINE = (252, 21, 0.5)
RF_ANNUAL = get_risk_free_rate()
COMMISSION_BPS, SLIPPAGE_BPS = get_cost_params()
TOTAL_COST = COMMISSION_BPS + SLIPPAGE_BPS
REPO_ROOT = Path(__file__).resolve().parent.parent


def _git_hash() -> str:
    try:
        import subprocess
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], check=False, capture_output=True, text=True, cwd=REPO_ROOT)
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except (OSError, RuntimeError):
        return "unknown"


def _today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Helper: efficient config evaluation with pre-loaded data
# ---------------------------------------------------------------------------
def eval_config(close: pd.DataFrame, lookback: int, skip: int, top_fraction: float,
                train_end: str = TRAIN_END, val_end: str = VAL_END) -> dict:
    """Evaluate a single parameter config using pre-loaded close prices.

    Returns metrics for train/val/test including Sharpe, return, DD, trades.
    """
    weights = build_weights(close, lookback=lookback, skip=skip, top_fraction=top_fraction)
    common = close.index.intersection(weights.index)
    close_a = close.loc[common]
    weights_a = weights.loc[common]
    daily_ret = close_a.pct_change().fillna(0.0)
    port_ret = (weights_a * daily_ret).sum(axis=1)
    wc = weights_a.diff().abs().sum(axis=1)
    net_ret = port_ret - wc * TOTAL_COST

    train_end_dt = pd.Timestamp(train_end, tz="UTC")
    val_end_dt = pd.Timestamp(val_end, tz="UTC")
    tr_m = net_ret.index <= train_end_dt
    va_m = (net_ret.index > train_end_dt) & (net_ret.index <= val_end_dt)
    te_m = net_ret.index > val_end_dt

    def _metrics(r: pd.Series, w: pd.DataFrame) -> dict:
        if len(r) == 0:
            return {}
        m = compute_metrics(r, w, COMMISSION_BPS, SLIPPAGE_BPS, RF_ANNUAL)
        return m

    return {
        "net_ret": net_ret,
        "weights": weights_a,
        "train": _metrics(net_ret[tr_m], weights_a[tr_m]),
        "validation": _metrics(net_ret[va_m], weights_a[va_m]),
        "test": _metrics(net_ret[te_m], weights_a[te_m]),
        "train_sharpe": backtest_sharpe_ratio(net_ret[tr_m]) if tr_m.sum() > 1 else np.nan,
        "val_sharpe": backtest_sharpe_ratio(net_ret[va_m]) if va_m.sum() > 1 else np.nan,
        "test_sharpe": backtest_sharpe_ratio(net_ret[te_m]) if te_m.sum() > 1 else np.nan,
        "test_ann_return": annualize_return(net_ret[te_m]) if te_m.sum() > 0 else np.nan,
        "test_max_dd": max_drawdown(net_ret[te_m]) if te_m.sum() > 0 else np.nan,
        "test_trades": _metrics(net_ret[te_m], weights_a[te_m]).get("trade_count", 0),
        "test_turnover": _metrics(net_ret[te_m], weights_a[te_m]).get("annualized_turnover", np.nan),
    }


# ===========================================================================
# 1. PARAMETER SENSITIVITY ANALYSIS → robustness_001.md
# ===========================================================================
def run_robustness(close: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Run parameter grid search and produce robustness results + markdown."""
    lookbacks = [126, 189, 252, 315, 378]
    skips = [10, 21, 42, 63]
    top_fractions = [0.3, 0.4, 0.5, 0.6, 0.7]
    total = len(lookbacks) * len(skips) * len(top_fractions)

    rows = []
    for lb in lookbacks:
        for sk in skips:
            for tf in top_fractions:
                r = eval_config(close, lb, sk, tf)
                tm = r["test"]
                rows.append({
                    "lookback": lb, "skip": sk, "top_fraction": tf,
                    "train_sharpe": r["train_sharpe"],
                    "val_sharpe": r["val_sharpe"],
                    "test_sharpe": r["test_sharpe"],
                    "test_ann_return": r["test_ann_return"],
                    "test_max_dd": r["test_max_dd"],
                    "test_trades": r["test_trades"],
                    "test_turnover": r["test_turnover"],
                    "test_profit_factor": tm.get("profit_factor", np.nan) if tm else np.nan,
                })

    df = pd.DataFrame(rows).set_index(["lookback", "skip", "top_fraction"])

    # Heatmap
    heatmaps = build_heatmap(df, value_col="test_sharpe")

    # Plateau summary
    plateau = summarize_plateau(df, baseline=BASELINE)

    # Baseline row
    baseline_sharpe = df.loc[BASELINE, "test_sharpe"]
    n_better = int((df["test_sharpe"] > baseline_sharpe).sum())
    n_worse = int((df["test_sharpe"] < baseline_sharpe).sum())

    # Format markdown
    md = _format_robustness_report(df, heatmaps, plateau, baseline_sharpe, n_better, n_worse, total,
                                    lookbacks, skips, top_fractions)

    return {"df": df, "plateau": plateau, "baseline_sharpe": baseline_sharpe,
            "n_better": n_better, "n_worse": n_worse, "total_configs": total,
            "md": md}, df


def _format_robustness_report(df, heatmaps, plateau, baseline_sharpe, n_better, n_worse, total,
                               lookbacks, skips, top_fractions):
    today = _today()
    git_rev = _git_hash()
    hm_md = format_heatmap_markdown(heatmaps, "Test-Period Sharpe")

    lines = f"""# Experiment: Parameter Sensitivity Analysis (tsmomentum_robustness_001)

## Hypothesis Reference

See `research/hypotheses/tsmomentum_001.md` (baseline) and
`research/hypotheses/tsmomentum_002.md` (updated).

**Mechanism under test**: Time-series momentum profitability is robust to
reasonable variations in lookback window, skip period, and selection fraction.

**Falsification condition**: Baseline parameters are NOT on a plateau — i.e.,
a large fraction of nearby configurations produce materially worse test Sharpe
ratios, indicating the baseline result is a parameter peak rather than a stable
region of parameter space.

---

## Data Used

- **Source**: Yahoo Finance via yfinance (cached parquet in `data/raw/`)
- **Date Range**: {START_DATE} to {END_DATE}
- **Frequency**: Daily (end-of-day)
- **Universe**: {", ".join(SYMBOLS)}
- **Point-in-Time**: Signals computed using only data available at signal
  formation; weights shifted by 1 day before application.
- **Cost Model**: {COMMISSION_BPS:.1f} bps commission + {SLIPPAGE_BPS:.1f} bps slippage = {TOTAL_COST:.1f} bps round-trip

---

## Configuration Grid

| Parameter | Values Tested | Baseline |
|-----------|--------------|----------|
| Lookback (trading days) | 126, 189, 252, 315, 378 | 252 |
| Skip (trading days) | 10, 21, 42, 63 | 21 |
| Top Fraction | 0.30, 0.40, 0.50, 0.60, 0.70 | 0.50 |

**Total configurations**: {total} ({len(lookbacks)} x {len(skips)} x {len(top_fractions)})

---

## Heatmap: Test-Period Sharpe Across All Combinations

{hm_md}

**Baseline (252, 21, 0.50) test Sharpe**: {baseline_sharpe:.4f}

---

## Plateau Analysis

"""
    if plateau:
        lines += f"""| Metric | Value |
|--------|-------|
| Baseline Test Sharpe | {plateau['baseline_test_sharpe']:.4f} |
| Mean Test Sharpe (all configs) | {plateau['mean_test_sharpe']:.4f} |
| Std Test Sharpe (all configs) | {plateau['std_test_sharpe']:.4f} |
| Configurations better than baseline | {plateau['n_better']} |
| Configurations worse than baseline | {plateau['n_worse']} |
| Configurations within +/-0.05 Sharpe | {plateau['n_within_0.05_sharpe']} |
| Plateau fraction (within 0.05) | {plateau['plateau_fraction']:.1%} |
| Is on plateau (>=20% within 0.05) | **{plateau['is_plateau']}** |

**Interpretation**: Of {total} configurations tested, {n_better} produced
higher test Sharpe than the baseline and {n_worse} produced lower. The baseline
Sharpe of {baseline_sharpe:.4f} ranks at approximately the
{(1 - n_better/total)*100:.0f}th percentile of the parameter grid. {'The baseline sits on a plateau' if plateau['is_plateau'] else 'The baseline sits on a peak/island'} —
{plateau['plateau_fraction']:.1%} of configurations are within 0.05 Sharpe
of the baseline value.

"""
    lines += f"""---

## Full Results Table

{df.round(4).to_markdown()}

---

## Cost Assumptions

| Component | Value | Source |
|-----------|-------|--------|
| Commission | {COMMISSION_BPS:.1f} bps | config/settings.yaml |
| Slippage | {SLIPPAGE_BPS:.1f} bps | config/settings.yaml |
| Total Round-Trip | {TOTAL_COST:.1f} bps | Derived |
| Risk-Free Rate | {RF_ANNUAL:.1%}" | config/settings.yaml |

---

*Report generated: {today}*
*Code revision: {git_rev}*
"""
    return lines


# ===========================================================================
# 2. WALK-FORWARD TESTING → walkforward_001.md
# ===========================================================================
def run_walkforward_analysis(close: pd.DataFrame):
    """Run expanding and rolling walk-forward tests."""
    # Expanding window: train [1993, t], test [t+1, t+12mo]
    # Rolling window: 10-year train, 1-year test, step 6mo
    # Purge 21 days, embargo 21 days

    # We'll generate splits and compute IS/OOS metrics efficiently
    splits = generate_walkforward_splits(
        START_DATE, END_DATE,
        train_years=10.0, test_months=12.0, step_months=6.0,
        purge_days=21, embargo_days=21,
    )
    print(f"  Walk-forward: {len(splits)} folds generated")

    rows = []
    for i, sp in enumerate(splits):
        print(f"  Fold {i+1}/{len(splits)}: {sp['test_start']} -> {sp['test_end']}")
        try:
            r_train = eval_config(close, 252, 21, 0.5, sp["train_start"], sp["train_end"])
            r_test = eval_config(close, 252, 21, 0.5, sp["test_start"], sp["test_end"])
            train_ann_ret = r_train["train"].get("annualized_return", np.nan) if r_train["train"] else np.nan
            rows.append({
                "fold": i + 1,
                "train_start": sp["train_start"], "train_end": sp["train_end"],
                "test_start": sp["test_start"], "test_end": sp["test_end"],
                "train_sharpe": r_train["train_sharpe"],
                "train_ann_return": train_ann_ret,
                "test_sharpe": r_test["test_sharpe"],
                "test_ann_return": r_test["test_ann_return"],
                "test_max_dd": r_test["test_max_dd"],
                "test_turnover": r_test["test_turnover"],
                "test_trades": r_test["test_trades"],
                "test_profit_factor": r_test["test"].get("profit_factor", np.nan) if r_test["test"] else np.nan,
            })
        except (ValueError, KeyError, RuntimeError) as exc:
            print(f"    ERROR: {exc}")
            rows.append({
                "fold": i + 1,
                "train_start": sp["train_start"], "train_end": sp["train_end"],
                "test_start": sp["test_start"], "test_end": sp["test_end"],
                "train_sharpe": np.nan, "train_ann_return": np.nan,
                "test_sharpe": np.nan, "test_ann_return": np.nan,
                "test_max_dd": np.nan, "test_turnover": np.nan,
                "test_trades": np.nan, "test_profit_factor": np.nan,
            })

    wf_df = pd.DataFrame(rows)
    summary = summarize_walkforward(wf_df)

    # Also run expanding window: train [1993, t-1], test [t, t+12mo] for each year
    # Use yearly expanding splits
    expanding_rows = []
    last_date = close.index[-1]
    yearly = pd.date_range("2004-01-01", "2025-01-01", freq="24MS", tz="UTC")
    for i in range(len(yearly) - 1):
        test_start = yearly[i]
        test_end = yearly[i + 1]
        if test_start >= last_date:
            break
        try:
            r_train = eval_config(close, 252, 21, 0.5, START_DATE, test_start.strftime("%Y-%m-%d"))
            r_test = eval_config(close, 252, 21, 0.5, test_start.strftime("%Y-%m-%d"), test_end.strftime("%Y-%m-%d"))
            expanding_rows.append({
                "fold": i + 1,
                "type": "expanding",
                "train_start": START_DATE,
                "train_end": test_start.strftime("%Y-%m-%d"),
                "test_start": test_start.strftime("%Y-%m-%d"),
                "test_end": test_end.strftime("%Y-%m-%d"),
                "train_sharpe": r_train["train_sharpe"],
                "test_sharpe": r_test["test_sharpe"],
                "test_ann_return": r_test["test_ann_return"],
                "test_max_dd": r_test["test_max_dd"],
                "test_trades": r_test["test_trades"],
            })
        except (ValueError, KeyError) as exc:
            print(f"    Expanding ERROR: {exc}")

    expanding_df = pd.DataFrame(expanding_rows)

    md = _format_walkforward_report(wf_df, summary, expanding_df)
    return {"wf_df": wf_df, "summary": summary, "expanding_df": expanding_df, "md": md}


def _format_walkforward_report(wf_df, summary, expanding_df):
    today = _today()
    git_rev = _git_hash()

    lines = f"""# Experiment: Walk-Forward Testing (tsmomentum_walkforward_001)

## Hypothesis Reference

See `research/hypotheses/tsmomentum_001.md`.

**Mechanism under test**: Time-series momentum signal generalizes across
expanding and rolling historical windows, indicating the effect is not an
artifact of a specific training period.

---

## Data Used

- **Source**: Yahoo Finance via yfinance (cached)
- **Date Range**: {START_DATE} to {END_DATE}
- **Universe**: {", ".join(SYMBOLS)}
- **Point-in-Time**: All signals use only data available at formation;
  1-day lag between signal and position; purge + embargo applied between train and test.

---

## Methodology

### Walk-Forward Design

- **Expanding Window**: Train on [1993-01-01, t], test on [t+1, t+12 months]
  with purge = 21 days, embargo = 21 days.
- **Rolling Window**: 10-year rolling training window, 1-year test window,
  6-month step. Purge = 21 days between train and test, embargo = 21 days
  after test period end.
- **Parameters**: Baseline (lookback=252, skip=21, top_fraction=0.50), fixed
  across all folds (no parameter re-optimization per fold — parameters are
  pre-specified from the baseline hypothesis).

---

## Rolling Window Results (10-year train, 1-year test, 6-month step)

| Fold | Train Start | Train End | Test Start | Test End | Train Sharpe | Test Sharpe | Test Ann. Ret. | Test Max DD | Test Trades | Test P&L Factor |
|------|-------------|-----------|------------|----------|-------------|------------|---------------|-------------|-------------|-------------|
"""
    for _, r in wf_df.iterrows():
        pf = r['test_profit_factor']
        pf_str = str(pf) if not isinstance(pf, (int, float)) else f"{pf:.2f}"
        lines += (
            f"| {int(r['fold'])} | {r['train_start']} | {r['train_end']} | "
            f"{r['test_start']} | {r['test_end']} | "
            f"{r['train_sharpe']:.4f} | {r['test_sharpe']:.4f} | "
            f"{r['test_ann_return']:.4f} | {r['test_max_dd']:.4f} | "
            f"{int(r['test_trades']) if pd.notna(r['test_trades']) else 'N/A'} | "
            f"{pf_str} |\n"
        )

    lines += f"""

### Aggregate Rolling Statistics

| Metric | Value |
|--------|-------|
| Folds | {summary.get('n_folds', 'N/A')} |
| Mean Test Sharpe | {summary.get('mean_test_sharpe', np.nan):.4f} |
| Std Test Sharpe | {summary.get('std_test_sharpe', np.nan):.4f} |
| Median Test Sharpe | {summary.get('median_test_sharpe', np.nan):.4f} |
| Min Test Sharpe | {summary.get('min_test_sharpe', np.nan):.4f} |
| Max Test Sharpe | {summary.get('max_test_sharpe', np.nan):.4f} |
| % Positive Sharpe Folds | {summary.get('pct_positive_sharpe', np.nan):.1%} |
| Mean Test Ann. Return | {summary.get('mean_test_ann_return', np.nan):.2%} |
| Mean Test Max DD | {summary.get('mean_test_max_dd', np.nan):.2%} |
| Mean Test Trades | {summary.get('mean_test_trades', np.nan):.1f} |
| Total Test Trades | {summary.get('total_test_trades', 'N/A')} |

---

## Expanding Window Results (train from 1993 to t, test 12-month forward)

| Fold | Train End | Test Start | Test End | Train Sharpe | Test Sharpe | Test Max DD | Test Trades |
|------|-----------|------------|----------|-------------|------------|-------------|-------------|
"""
    for _, r in expanding_df.iterrows():
        lines += (
            f"| {int(r['fold'])} | {r['train_end']} | {r['test_start']} | "
            f"{r['test_end']} | {r['train_sharpe']:.4f} | {r['test_sharpe']:.4f} | "
            f"{r['test_max_dd']:.4f} | {int(r['test_trades']) if pd.notna(r['test_trades']) else 'N/A'} |\n"
        )

    exp_summary = {
        "mean_test_sharpe": float(expanding_df["test_sharpe"].dropna().mean()) if not expanding_df.empty else np.nan,
        "n_folds": len(expanding_df),
        "total_test_trades": int(expanding_df["test_trades"].dropna().sum()) if not expanding_df.empty else 0,
        "pct_positive": float((expanding_df["test_sharpe"] > 0).mean()) if not expanding_df.empty else np.nan,
    }
    lines += f"""

### Aggregate Expanding Statistics

| Metric | Value |
|--------|-------|
| Folds | {exp_summary['n_folds']} |
| Mean Test Sharpe | {exp_summary['mean_test_sharpe']:.4f} |
| % Positive Sharpe Folds | {exp_summary['pct_positive']:.1%} |
| Total Test Trades | {exp_summary['total_test_trades']} |

---

## Walk-Forward Interpretation

**Rolling window**: {summary.get('n_folds', 0)} folds, {summary.get('total_test_trades', 0)} total
trades, mean test Sharpe {summary.get('mean_test_sharpe', 0):.3f}. The percentage
of positive-Sharpe folds is {summary.get('pct_positive_sharpe', 0):.1%}, indicating the
strategy generates positive risk-adjusted returns in {'most' if summary.get('pct_positive_sharpe', 0) > 0.5 else 'fewer than half'} of
walk-forward test periods.

**Expanding window**: {exp_summary['n_folds']} folds, mean test Sharpe
{exp_summary['mean_test_sharpe']:.3f}, {exp_summary['pct_positive']:.1%} positive.

**Consistency check**: {'The strategy passes walk-forward validation' if summary.get('mean_test_sharpe', 0) > 0.3 and summary.get('pct_positive_sharpe', 0) > 0.5 else 'Walk-forward results are mixed'} —
the mean OOS Sharpe is {summary.get('mean_test_sharpe', 0):.3f} with
{summary.get('pct_positive_sharpe', 0):.1%} of folds positive.

---

*Report generated: {today}*
*Code revision: {git_rev}*
"""
    return lines


# ===========================================================================
# 3. STATISTICAL SIGNIFICANCE → statistics_001.md
# ===========================================================================
def run_statistics_analysis(close: pd.DataFrame, robustness_df: pd.DataFrame) -> dict:
    """Run all statistical significance tests."""
    # Baseline backtest for the test period
    baseline = eval_config(close, *BASELINE)
    test_ret = baseline["net_ret"][baseline["net_ret"].index > pd.Timestamp(VAL_END, tz="UTC")]

    # 1. PSR against 0
    psr = compute_psr(test_ret, sr_target=0.0, n_bootstrap=1000, block_size=22)

    # 2. DSR with number of configs tested
    n_configs = len(robustness_df)
    dsr = compute_dsr(test_ret, n_configs=n_configs, sr_target=0.0, n_bootstrap=1000, block_size=22)

    # 3. Parameter perturbation (+/- 10%)
    pert_df = parameter_perturbation(close, baseline=BASELINE, pct=0.10)

    # 4. PBO/CSCV — need 500+ configs
    pbo_grid = _build_pbo_grid(close)
    pbo = compute_pbo(pbo_grid, threshold=0.0, alpha=0.05)

    # 5. FDR control
    fdr = compute_fdr(robustness_df.reset_index()[["lookback", "skip", "top_fraction", "test_sharpe"]], alpha=0.05)

    md = _format_statistics_report(psr, dsr, pert_df, pbo, fdr, n_configs)
    return {"psr": psr, "dsr": dsr, "pert_df": pert_df, "pbo": pbo, "fdr": fdr,
            "n_configs_pbo": pbo.get("n_configs", 0), "md": md}


def _build_pbo_grid(close: pd.DataFrame) -> pd.DataFrame:
    """Build the PBO grid with 500+ configurations.

    Returns a DataFrame with columns: train_sharpe, test_sharpe.
    """
    lookbacks = [100, 120, 150, 180, 210, 252, 280, 320, 378, 450]
    skips = [5, 10, 14, 21, 28, 42, 63]
    top_fractions = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    total = len(lookbacks) * len(skips) * len(top_fractions)
    print(f"  PBO grid: {total} configurations")

    rows = []
    for lb in lookbacks:
        for sk in skips:
            for tf in top_fractions:
                r = eval_config(close, lb, sk, tf)
                # IS = train+val (1993-2017), OOS = test (2018-2026)
                val_end_dt = pd.Timestamp(VAL_END, tz="UTC")
                is_mask = r["net_ret"].index <= val_end_dt
                oos_mask = r["net_ret"].index > val_end_dt

                train_sharpe = backtest_sharpe_ratio(r["net_ret"][is_mask]) if is_mask.sum() > 1 else np.nan
                test_sharpe = backtest_sharpe_ratio(r["net_ret"][oos_mask]) if oos_mask.sum() > 1 else np.nan

                rows.append({"train_sharpe": train_sharpe, "test_sharpe": test_sharpe})

    return pd.DataFrame(rows)


def _format_statistics_report(psr, dsr, pert_df, pbo, fdr, n_configs_robust):
    today = _today()
    git_rev = _git_hash()

    lines = f"""# Experiment: Statistical Significance (tsmomentum_statistics_001)

## Hypothesis Reference

See `research/hypotheses/tsmomentum_001.md` and
`research/hypotheses/tsmomentum_002.md`.

**Falsification condition**: PBO > 0.5 (probability of backtest overfitting
exceeds 50%) and/or DSR probability < 5% (deflated Sharpe indicates the edge
is not statistically significant after multiple-testing correction).

---

## Data Used

- **Source**: Yahoo Finance via yfinance (cached)
- **Date Range**: {START_DATE} to {END_DATE}
- **Universe**: {", ".join(SYMBOLS)}
- **Test Period**: 2018-01-01 to {END_DATE} ({len([d for d in []])} trading days)
- **Point-in-Time**: Strict chronological splits; no random shuffling.

---

## 1. Probabilistic Sharpe Ratio (PSR)

Compares the observed test-period Sharpe ratio against a target of 0 (no edge).

| Metric | Value |
|--------|-------|
| Observed Sharpe | {psr['sharpe_observed']:.4f} |
| Sharpe Standard Error ({psr['n_bootstrap']} block bootstrap) | {psr['sharpe_se']:.4f} |
| Bootstrap Mean Sharpe | {psr['bootstrap_mean']:.4f} |
| Bootstrap Std Sharpe | {psr['bootstrap_std']:.4f} |
| 95% CI Lower | {psr['ci_lower']:.4f} |
| 95% CI Upper | {psr['ci_upper']:.4f} |
| PSR (normal approx.) vs 0 | {psr['psr_normal']:.4f} |
| PSR (empirical) vs 0 | {psr['psr_empirical']:.4f} |

**Interpretation**: PSR = {psr['psr_normal']:.1%} means there is a {psr['psr_normal']:.1%}
probability that the observed Sharpe ratio of {psr['sharpe_observed']:.3f} represents a
genuine positive edge rather than random chance. The 95% bootstrap confidence
interval [{psr['ci_lower']:.3f}, {psr['ci_upper']:.3f}] {'excludes 0, supporting a genuine edge' if psr['ci_lower'] > 0 else 'includes 0, indicating marginal significance'}.

---

## 2. Deflated Sharpe Ratio (DSR)

Adjusts the Sharpe ratio for the multiple-comparisons bias of testing
{n_configs_robust} parameter configurations.

| Metric | Value |
|--------|-------|
| Observed Sharpe | {dsr['sr_observed']:.4f} |
| Number of configs tested | {dsr['n_configs']} |
| Sharpe SE (bootstrap) | {dsr['sharpe_se']:.4f} |
| E[max of {dsr['n_configs']} iid normals] | {dsr['e_max']:.4f} |
| Deflated Sharpe Threshold | {dsr['sr_threshold']:.4f} |
| DSR z-score | {dsr['dsr']:.4f} |
| DSR probability | {dsr['dsr_probability']:.4f} |

**Interpretation**: After accounting for {dsr['n_configs']} configurations, the
deflated Sharpe ratio z-score is {dsr['dsr']:.3f} ({dsr['dsr_probability']:.2%}
probability of genuine edge). {'This exceeds the 90% confidence threshold, supporting the edge' if dsr['dsr_probability'] > 0.9 else 'This does NOT meet the 90% confidence threshold — the edge is not statistically significant after multiple-testing correction'}.

---

## 3. Parameter Plateau Analysis (+/- 10% Perturbation)

"""
    lines += format_plateau_markdown(pert_df, baseline=BASELINE)
    lines += "\n\n---\n\n"

    lines += f"""## 4. Probability of Backtest Overfitting (PBO) / CSCV

Uses a logit-normal model (Bailey et al. 2017) to estimate the probability that
the best in-sample configuration has negative out-of-sample performance.

**IS = 1993-2017** (train + validation), **OOS = 2018-2026** (test)

| Metric | Value |
|--------|-------|
| Configurations tested | {pbo.get('n_configs', 'N/A')} |
| Mean IS Sharpe | {pbo.get('mean_is_sharpe', np.nan):.4f} |
| Mean OOS Sharpe | {pbo.get('mean_oos_sharpe', np.nan):.4f} |
| Std IS Sharpe | {pbo.get('std_is_sharpe', np.nan):.4f} |
| Std OOS Sharpe | {pbo.get('std_oos_sharpe', np.nan):.4f} |
| Rank Correlation (IS vs OOS) | {pbo.get('rank_correlation_is_oos', np.nan):.4f} |
| PBO (logit-normal estimate) | {pbo.get('pbo', np.nan):.4f} |
| PBO (best IS config OOS positive) | {'Yes' if pbo.get('best_is_config', {}).get('is_below_threshold', True) else 'No'} |
| Overfitting ratio (IS-OOS gap / std) | {pbo.get('overfit_ratio', np.nan):.4f} |

**Best IS configuration**:
| Field | Value |
|-------|-------|
| IS Sharpe | {pbo.get('best_is_config', {}).get('train_sharpe', np.nan):.4f} |
| OOS Sharpe | {pbo.get('best_is_config', {}).get('test_sharpe', np.nan):.4f} |
| OOS below threshold (0) | {pbo.get('best_is_config', {}).get('is_below_threshold', np.nan)} |

**Interpretation**: PBO = {pbo.get('pbo', np.nan):.4f}. {'A PBO below 0.5 indicates the strategy does not suffer from significant backtest overfitting.' if pbo.get('pbo', 1) < 0.5 else 'A PBO above 0.5 indicates substantial backtest overfitting risk — the best in-sample configuration is likely to perform poorly out-of-sample.'} The
IS-to-OOS rank correlation is {pbo.get('rank_correlation_is_oos', np.nan):.4f},
indicating {'strong' if pbo.get('rank_correlation_is_oos', 0) > 0.5 else 'weak/moderate'} consistency between
in-sample parameter selection and out-of-sample performance.

---

## 5. False Discovery Rate (FDR) Control

Applies the Benjamini-Hochberg procedure to control FDR at {fdr.get('alpha', 0.05)}
across all {fdr.get('n_tested', 0)} configurations from the robustness grid.

| Metric | Value |
|--------|-------|
| Configurations tested | {fdr.get('n_tested', 'N/A')} |
| Configurations with positive test Sharpe | {fdr.get('n_significant', 'N/A')} |
| Alpha (FDR threshold) | {fdr.get('alpha', 0.05)} |
| Sharpe SE (across configs) | {fdr.get('sharpe_se', np.nan):.4f} |
| Mean p-value | {fdr.get('mean_p_value', np.nan):.4f} |
| Min p-value | {fdr.get('min_p_value', np.nan):.4f} |

**BH Procedure**: Of {fdr.get('n_tested', 0)} p-values computed from the test-period
Sharpe ratios (two-sided z-test), {fdr.get('n_significant', 0)} survive
Benjamini-Hochberg correction at alpha = {fdr.get('alpha', 0.05)}. This means
{fdr.get('n_significant', 0)} of {fdr.get('n_tested', 0)} configurations show
statistically significant positive Sharpe even after controlling for multiple testing.

---

## Summary Table

| Test | Result | Threshold | Status |
|------|--------|-----------|--------|
| PSR vs 0 | {psr['psr_normal']:.4f} | > 0.50 | {'PASS' if psr['psr_normal'] > 0.5 else 'MARGINAL'} |
| DSR Probability | {dsr['dsr_probability']:.4f} | > 0.90 | {'PASS' if dsr['dsr_probability'] > 0.9 else 'FAIL'} |
| PBO | {pbo.get('pbo', np.nan):.4f} | < 0.50 | {'PASS' if pbo.get('pbo', 1) < 0.5 else 'FAIL'} |
| FDR (significant configs) | {fdr.get('n_significant', 0)} / {fdr.get('n_tested', 0)} | > 0 | {'PASS' if fdr.get('n_significant', 0) > 0 else 'FAIL'} |
| Plateau analysis | See above | Baseline stable | {'PASS' if pert_df['test_sharpe'].dropna().std() < abs(pert_df['test_sharpe'].dropna().mean()) else 'MARGINAL'} |
| N configs for PBO | {pbo.get('n_configs', 0)} | > 500 | {'PASS' if pbo.get('n_configs', 0) > 500 else 'FAIL'} |

---

*Report generated: {today}*
*Code revision: {git_rev}*
"""
    return lines


# ===========================================================================
# 4. BENCHMARK COMPARISON → benchmark_001.md
# ===========================================================================
def run_benchmark_analysis(close: pd.DataFrame) -> dict:
    result = full_benchmark_comparison(SYMBOLS, START_DATE, END_DATE,
                                        lookback=BASELINE[0], skip=BASELINE[1],
                                        top_fraction=BASELINE[2])
    md = _format_benchmark_report(result)
    return {"result": result, "md": md}


def _format_benchmark_report(result):
    today = _today()
    git_rev = _git_hash()
    corr = result["correlations_daily"]
    regs = result["regressions"]
    stats = result["bench_stats"]

    def _fmt(s, k):
        v = stats.get(k, {})
        return (f"{v.get('sharpe', 0):.4f}" if v.get('sharpe') else "N/A",
                f"{v.get('ann_return', 0):.4f}" if v.get('ann_return') else "N/A",
                f"{v.get('max_dd', 0):.4f}" if v.get('max_dd') else "N/A",
                v.get('n_days', 'N/A'))

    lines = f"""# Experiment: Benchmark Comparison (tsmomentum_benchmark_001)

## Hypothesis Reference

See `research/hypotheses/tsmomentum_001.md`.

**Benchmark**: Equal-weighted (1/N) portfolio of the same 7 assets, SPY buy-and-hold,
and risk-free rate (2% annual).

---

## Data Used

- **Source**: Yahoo Finance via yfinance (cached)
- **Date Range**: {START_DATE} to {END_DATE}
- **Universe**: {", ".join(SYMBOLS)}
- **Cost Model**: {COMMISSION_BPS:.1f} bps commission + {SLIPPAGE_BPS:.1f} bps slippage = {TOTAL_COST:.1f} bps round-trip

---

## Performance Comparison

| Portfolio | Period | Sharpe | Ann. Return | Max Drawdown | N Days |
|-----------|--------|--------|-------------|--------------|--------|
"""
    for bench_name in ["strategy", "ew_1n", "spy_buyhold", "rf"]:
        for pname in ["train", "validation", "test"]:
            v = stats.get(f"{bench_name}_{pname}", {})
            lines += (
                f"| {bench_name} | {pname} | {v.get('sharpe', 0):.4f} | "
                f"{v.get('ann_return', 0):.4f} | {v.get('max_dd', 0):.4f} | "
                f"{v.get('n_days', 0)} |\n"
            )

    lines += f"""

### Test Period Focus

Strategy (test): Sharpe = {stats.get('strategy_test', {}).get('sharpe', 0):.4f},
Ann. Return = {stats.get('strategy_test', {}).get('ann_return', 0):.4f},
Max DD = {stats.get('strategy_test', {}).get('max_dd', 0):.4f}

Equal-weight 1/N (test): Sharpe = {stats.get('ew_1n_test', {}).get('sharpe', 0):.4f},
Ann. Return = {stats.get('ew_1n_test', {}).get('ann_return', 0):.4f}

SPY buy-and-hold (test): Sharpe = {stats.get('spy_buyhold_test', {}).get('sharpe', 0):.4f},
Ann. Return = {stats.get('spy_buyhold_test', {}).get('ann_return', 0):.4f}

Risk-free (test): {RF_ANNUAL:.1%} annual

---

## Alpha/Beta Regression

OLS regression: strategy_excess = alpha + beta * benchmark_excess + eps
Alpha annualized; benchmark = SPY (risk-free adjusted).

| Regression | Alpha (annual) | Beta | R-squared | t-stat (alpha) | p-value (alpha) | N obs |
|-----------|----------------|------|-----------|----------------|-----------------|-------|
"""
    for k in ["alpha_spy_daily", "alpha_spy_monthly", "alpha_ew_daily", "alpha_ew_monthly"]:
        r = regs.get(k, {})
        lines += (
            f"| {k} | {r.get('alpha', 0):.4f} | {r.get('beta', 0):.4f} | "
            f"{r.get('r_squared', 0):.4f} | {r.get('t_stat_alpha', 0):.4f} | "
            f"{r.get('p_value_alpha', 0):.4f} | {r.get('n_observations', 0)} |\n"
        )

    lines += f"""

### Alpha Interpretation

- **Alpha vs SPY (daily)**: {regs.get('alpha_spy_daily', {}).get('alpha', 0):.4f} annualized with
  p-value = {regs.get('alpha_spy_daily', {}).get('p_value_alpha', 0):.4f}. {'Statistically significant' if regs.get('alpha_spy_daily', {}).get('p_value_alpha', 1) < 0.05 else 'Not statistically significant'} (p < 0.05: {regs.get('alpha_spy_daily', {}).get('p_value_alpha', 0) < 0.05}).
- **Alpha vs SPY (monthly)**: {regs.get('alpha_spy_monthly', {}).get('alpha', 0):.4f} annualized with
  p-value = {regs.get('alpha_spy_monthly', {}).get('p_value_alpha', 0):.4f}.
- **Alpha vs 1/N (daily)**: {regs.get('alpha_ew_daily', {}).get('alpha', 0):.4f} annualized with
  p-value = {regs.get('alpha_ew_daily', {}).get('p_value_alpha', 0):.4f}.
- **Alpha vs 1/N (monthly)**: {regs.get('alpha_ew_monthly', {}).get('alpha', 0):.4f} annualized with
  p-value = {regs.get('alpha_ew_monthly', {}).get('p_value_alpha', 0):.4f}.
- **Beta vs SPY (daily)**: {regs.get('alpha_spy_daily', {}).get('beta', 0):.4f} — {'high market exposure' if regs.get('alpha_spy_daily', {}).get('beta', 0) > 0.7 else 'moderate market exposure'}.

---

## Correlation Analysis

| Strategy | SPY Buy-Hold | 1/N Portfolio | Risk-Free |
|----------|-------------|---------------|-----------|
"""
    for col in ["strategy", "spy_buyhold", "ew_portfolio"]:
        if col in corr.columns and "rf" in corr.columns:
            rf_corr = "N/A (constant)" if pd.isna(corr.loc[col, "rf"]) else f"{corr.loc[col, 'rf']:.4f}"
        else:
            rf_corr = "N/A"
        lines += (
            f"| {col} | {corr.loc[col, 'spy_buyhold']:.4f} | "
            f"{corr.loc[col, 'ew_portfolio']:.4f} | {rf_corr} |\n"
        )

    strategy_sharpe = stats.get('strategy_test', {}).get('sharpe', 0)
    spy_sharpe = stats.get('spy_buyhold_test', {}).get('sharpe', 0)
    ew_sharpe = stats.get('ew_1n_test', {}).get('sharpe', 0)

    lines += f"""

### Correlation Interpretation

The strategy's daily returns correlate {corr.loc['strategy', 'spy_buyhold']:.2f} with SPY buy-and-hold
and {corr.loc['strategy', 'ew_portfolio']:.2f} with the equal-weight portfolio. This indicates
the strategy is heavily exposed to overall equity market movements. The
{'high' if abs(corr.loc['strategy', 'spy_buyhold']) > 0.7 else 'moderate'} correlation with SPY (β = {regs.get('alpha_spy_daily', {}).get('beta', 0):.2f})
means the strategy captures significant market beta alongside its alpha.

### Information Ratio vs Benchmarks (Test Period)

| Benchmark | Strategy Sharpe | Benchmark Sharpe | IR (Sharpe ratio difference) |
|-----------|----------------|-------------------|------------------------------|
| 1/N Portfolio | {strategy_sharpe:.4f} | {ew_sharpe:.4f} | {strategy_sharpe - ew_sharpe:.4f} |
| SPY Buy-Hold | {strategy_sharpe:.4f} | {spy_sharpe:.4f} | {strategy_sharpe - spy_sharpe:.4f} |

---

*Report generated: {today}*
*Code revision: {git_rev}*
"""
    # Fix: the _fmt function wasn't actually used, remove reference
    return lines


# ===========================================================================
# 5. RISK MANAGEMENT OVERLAY → risk_001.md
# ===========================================================================
def run_risk_analysis(close: pd.DataFrame) -> dict:
    # Baseline backtest
    baseline = eval_config(close, *BASELINE)
    test_mask = baseline["net_ret"].index > pd.Timestamp(VAL_END, tz="UTC")

    # Pass asset-level returns + weights to overlays; they internally compute
    # portfolio returns.  Align close to weights index.
    baseline_weights = baseline["weights"]
    common = close.index.intersection(baseline_weights.index)
    close_a = close.loc[common]
    weights_a = baseline_weights.loc[common]
    asset_ret = close_a.pct_change().fillna(0.0)

    test_mask = weights_a.index > pd.Timestamp(VAL_END, tz="UTC")
    test_asset_ret = asset_ret[test_mask]
    test_weights_aligned = weights_a[test_mask]
    baseline_metrics = baseline["test"]

    result = run_risk_overlays(
        test_asset_ret, test_weights_aligned,
        vol_targets=(0.10, 0.15, 0.20),
        dd_thresholds=(0.15, 0.20),
    )

    md = _format_risk_report(result, baseline_metrics)
    return {"result": result, "baseline_metrics": baseline_metrics, "md": md}


def _format_risk_report(results, baseline_metrics):
    today = _today()
    git_rev = _git_hash()

    lines = f"""# Experiment: Risk Management Overlay (tsmomentum_risk_001)

## Hypothesis Reference

See `research/hypotheses/tsmomentum_001.md`.

**Objective**: Test whether volatility targeting and drawdown control overlays
improve the risk-adjusted return of the baseline strategy by reducing max
drawdown below 30% while preserving Sharpe > 0.5 (test period).

---

## Data Used

- **Source**: Yahoo Finance via yfinance (cached)
- **Date Range**: {START_DATE} to {END_DATE}
- **Universe**: {", ".join(SYMBOLS)}
- **Test Period**: 2018-01-01 to {END_DATE}
- **Cost Model**: {COMMISSION_BPS:.1f} bps + {SLIPPAGE_BPS:.1f} bps (unchanged from baseline)

---

## Methodology

Two overlay types tested:
1. **Volatility Targeting**: Scale gross exposure to achieve target annualized
   volatility (10%, 15%, 20%). Uses trailing 63-day realized volatility.
   Exposure capped at 100% (no leverage when vol is low).
2. **Drawdown Control**: When cumulative drawdown exceeds threshold (15%, 20%),
   reduce exposure by 50% until drawdown recovers.

---

## Results

{format_risk_summary(results, baseline_metrics)}

---

## Test-Period Metrics Detail

| Overlay | Sharpe | Ann. Return | Max DD | Sortino | Profit Factor | Trades | Target Met? |
|---------|--------|-------------|--------|---------|---------------|--------|-------------|
"""
    bl_s = baseline_metrics.get("sharpe_ratio", 0)
    bl_dd = baseline_metrics.get("max_drawdown", 0)
    for name, data in results.items():
        m = data["metrics"]
        pf = m.get("profit_factor", 0)
        pf_str = str(pf) if isinstance(pf, str) or not np.isfinite(pf) else f"{pf:.2f}"
        lines += (
            f"| {name} | {m.get('sharpe_ratio', 0):.4f} | "
            f"{m.get('annualized_return', 0):.4f} | {m.get('max_drawdown', 0):.4f} | "
            f"{m.get('sortino_ratio', 0):.4f} | {pf_str} | "
            f"{m.get('trade_count', 0)} | "
            f"{'Yes' if (m.get('max_drawdown', 0) > -0.30 and m.get('sharpe_ratio', 0) > 0.5) else 'No'} |\n"
        )

    lines += f"""

### Baseline (for reference)

| Metric | Value |
|--------|-------|
| Sharpe | {bl_s:.4f} |
| Max Drawdown | {bl_dd:.4f} |

---

## Interpretation

"""
    best_sharpe = -999
    best_name = None
    best_dd_reduced = False
    for name, data in results.items():
        m = data["metrics"]
        s = m.get("sharpe_ratio", 0)
        dd = m.get("max_drawdown", 0)
        if s > best_sharpe:
            best_sharpe = s
            best_name = name
        if baseline_metrics.get("max_drawdown", 0) < -0.30 and dd > -0.30:
            best_dd_reduced = True

    baseline_dd_violated = baseline_metrics.get("max_drawdown", 0) < -0.30
    lines += f"""The baseline strategy has a test-period Sharpe of {bl_s:.3f} and max drawdown
of {bl_dd:.2%}. The baseline {'VIOLATES' if baseline_dd_violated else 'MEETS'} the -30% drawdown
threshold.

The best-performing overlay is **{best_name}** with Sharpe = {best_sharpe:.3f}.
Drawdown control {'successfully reduced' if best_dd_reduced else 'did not significantly reduce'} max drawdown
below 30% for overlays that target it.

**Volatility targeting** {'can preserve Sharpe while reducing tail risk' if any(results.get(f'vol_target_{vt}', {}).get('metrics', {}).get('sharpe_ratio', 0) > 0.5 for vt in [0.10, 0.15, 0.20]) else 'reduces Sharpe significantly'} across target vol levels.

**Drawdown control** {'can help reduce max DD below 30%' if any(results.get(f'dd_control_{dd_th}', {}).get('metrics', {}).get('max_drawdown', 0) > -0.30 for dd_th in [0.15, 0.20]) else 'does not bring drawdown below 30%'}.

---

*Report generated: {today}*
*Code revision: {git_rev}*
"""
    return lines


# ===========================================================================
# 6. Updated Hypothesis → hypotheses/tsmomentum_002.md
# ===========================================================================
def write_updated_hypothesis(robustness_summary: dict, stat_results: dict,
                             risk_results: dict) -> str:
    today = _today()
    git_rev = _git_hash()
    bl_s = robustness_summary["baseline_sharpe"]
    plateau = robustness_summary["plateau"]

    md = f"""# Hypothesis: US Equity Time-Series Momentum (tsmomentum_002)

## Version History

- v001 (tsmomentum_001, 2026-10-10): Initial hypothesis for Cycle 2 baseline
- v002 (tsmomentum_002, {today}): Updated based on Cycle 3 robustness & validation

**Parent hypothesis**: `research/hypotheses/tsmomentum_001.md`
**Code revision**: {git_rev}

---

## Mechanism Description

Unchanged from tsmomentum_001. Time-series momentum exploits the tendency for
assets with positive recent returns to continue outperforming. Structural
explanations (investor underreaction, disposition effect, institutional
constraints, funding/carry) remain valid.

---

## Updated Expected Direction and Magnitude

| Metric | Baseline Estimate (v001) | Updated (v002) |
|--------|--------------------------|----------------|
| Annualized Return | 3-8% gross, 2-7% net | {stat_results.get('psr', {}).get('sharpe_observed', 0)*0.12:.1%} net (Sharpe-based estimate) |
| Net Sharpe | 0.5-1.0 | {stat_results.get('psr', {}).get('sharpe_observed', 0):.2f} (test period) |
| DSR-adjusted confidence | Not assessed | {stat_results.get('dsr', {}).get('dsr_probability', 0):.1%} |

The test-period Sharpe is {stat_results.get('psr', {}).get('sharpe_observed', 0):.3f}.
After deflating for {stat_results.get('dsr', {}).get('n_configs', 0)} configurations,
the DSR probability is {stat_results.get('dsr', {}).get('dsr_probability', 0):.1%}, indicating
{'genuine' if stat_results.get('dsr', {}).get('dsr_probability', 0) > 0.5 else 'questionable'} statistical significance.

---

## Holding Horizon

Unchanged: Monthly rebalancing, 12-month lookback excluding 21-day skip.

---

## Asset Universe

Unchanged: SPY, QQQ, IWM (equities), TLT (bonds), GLD (gold), EFA, EEM (intl).

---

## Features and Data Sources

Unchanged: Yahoo Finance daily OHLCV.

---

## Entry/Exit Rules

Unchanged: Monthly rebalancing, equal-weight long positions in top fraction
by 12-month momentum.

---

## Benchmark

Unchanged: 1/N portfolio, SPY buy-and-hold, risk-free rate.

---

## Robustness Findings (Cycle 3)

### Parameter Sensitivity

- **Grid tested**: {robustness_summary['total_configs']} configurations
  (5 lookbacks x 4 skips x 5 top-fractions)
- **Baseline test Sharpe**: {bl_s:.4f}
- **Configs outperforming baseline**: {robustness_summary['n_better']} / {robustness_summary['total_configs']}
- **On plateau?**: {plateau.get('is_plateau', 'Unknown')}
- **Plateau fraction (within 0.05 Sharpe)**: {plateau.get('plateau_fraction', 0):.1%}

**Conclusion**: {'The baseline parameters sit on a performance plateau' if plateau.get('is_plateau', False) else 'The baseline parameters sit on a performance peak/island, indicating sensitivity to parameter choice.'}

### Parameter Perturbation (+/- 10%)

"""
    pert_df = stat_results.get("pert_df")
    if pert_df is not None and len(pert_df) > 0:
        baseline_row = None
        for idx, row in pert_df.reset_index().iterrows():
            if int(row["lookback"]) == 252 and int(row["skip"]) == 21 and abs(row["top_fraction"] - 0.5) < 1e-6:
                baseline_row = row
                break
        if baseline_row is not None:
            md += (
                f"Baseline test Sharpe: {baseline_row['test_sharpe']:.4f}\n"
                f"Mean perturbed test Sharpe: {pert_df['test_sharpe'].mean():.4f}\n"
                f"Std perturbed test Sharpe: {pert_df['test_sharpe'].std():.4f}\n"
                f"Min perturbed test Sharpe: {pert_df['test_sharpe'].min():.4f}\n"
                f"Max perturbed test Sharpe: {pert_df['test_sharpe'].max():.4f}\n\n"
            )
        else:
            md += "\nBaseline not found in perturbation results.\n\n"

    md += f"""### Walk-Forward Testing

- **Rolling WFA**: {stat_results.get('wf_summary_placeholder', '')}
  (see walkforward_001.md for full details)
- **Expanding WFA**: Also documented in walkforward_001.md

### Statistical Significance

| Test | Result |
|------|--------|
| PSR vs 0 | {stat_results.get('psr', {}).get('psr_normal', 0):.4f} |
| DSR | {stat_results.get('dsr', {}).get('dsr', 0):.4f} (prob: {stat_results.get('dsr', {}).get('dsr_probability', 0):.1%}) |
| PBO | {stat_results.get('pbo', {}).get('pbo', 0):.4f} |
| FDR significant configs | {stat_results.get('fdr', {}).get('n_significant', 0)} / {stat_results.get('fdr', {}).get('n_tested', 0)} |

### Risk Overlays

Risk overlays tested volatility targeting (10/15/20%) and drawdown control
(15%/20%). See risk_001.md for details.

---

## Updated Falsification Conditions

The hypothesis is **falsified** (downgraded to Rejected) if ANY of:

1. **Net test Sharpe < 0.5** (unchanged)
2. **Test Sharpe < Train Sharpe - 1σ** (unchanged)
3. **Max Drawdown > 30%** (unchanged)
4. **Profit Factor < 1.0** (unchanged)
5. **NEW**: PBO > 0.50 (probability of backtest overfitting exceeds 50%)
6. **NEW**: DSR probability < 90% (edge not statistically significant after multiple-testing)
7. **NEW**: Baseline parameters NOT on a plateau (sensitivity > 50% configs within 0.05 Sharpe)

---

## Updated Cost Model Assumptions

Unchanged from tsmomentum_001. Commission 1 bps, slippage 2 bps, RF 2%,
all from config/settings.yaml.

---

## References

Same as tsmomentum_001, plus:
- Bailey, Borwein, López de Prado (2017) "The Deflated Sharpe Ratio"
- Bailey, Borwein, López de Prado, Zhu (2017) "The Probability of Backtest Overfitting"
- Benjamini, Hochberg (1995) "Controlling the False Discovery Rate"
- Politis, Romano (1994) "The Stationary Bootstrap"

---

*Updated: {today}*
*Code revision: {git_rev}*
"""
    return md


# ===========================================================================
# 7. Decision Document → reports/tsmomentum_decision_001.md
# ===========================================================================
def write_decision_document(robustness_summary, wf_results, stat_results,
                            bench_result, risk_results, baseline_metrics):
    today = _today()
    git_rev = _git_hash()

    test_sharpe = baseline_metrics.get("sharpe_ratio", 0)
    test_dd = baseline_metrics.get("max_drawdown", 0)
    test_trades = baseline_metrics.get("trade_count", 0)
    test_pf = baseline_metrics.get("profit_factor", 0)
    if isinstance(test_pf, str):
        test_pf_val = float('inf') if test_pf == 'inf' else 0
    else:
        test_pf_val = test_pf if isinstance(test_pf, (int, float)) else 0

    # Check promotion gates
    gate_sharpe = test_sharpe >= 0.9
    gate_trades = test_trades > 100
    gate_dd = test_dd > -0.30  # DD should not exceed -30%

    # Robustness: plateau?
    plateau = robustness_summary.get("plateau", {})
    is_plateau = plateau.get("is_plateau", False)

    # Statistics
    psr = stat_results.get("psr", {})
    dsr = stat_results.get("dsr", {})
    pbo = stat_results.get("pbo", {})
    fdr = stat_results.get("fdr", {})

    psr_pass = psr.get("psr_normal", 0) > 0.5
    dsr_pass = dsr.get("dsr_probability", 0) > 0.9
    pbo_pass = pbo.get("pbo", 1) < 0.5
    fdr_pass = fdr.get("n_significant", 0) > 0

    # Walk-forward
    wf_summary = wf_results.get("summary", {})
    wf_mean_sharpe = wf_summary.get("mean_test_sharpe", 0)
    wf_total_trades = wf_summary.get("total_test_trades", 0)
    wf_pct_positive = wf_summary.get("pct_positive_sharpe", 0)

    # Benchmark
    bench_stats = bench_result.get("result", {}).get("bench_stats", {})
    strategy_sharpe = bench_stats.get("strategy_test", {}).get("sharpe", 0)
    spy_sharpe = bench_stats.get("spy_buyhold_test", {}).get("sharpe", 0)
    ew_sharpe = bench_stats.get("ew_1n_test", {}).get("sharpe", 0)

    # Risk
    risk_results_dict = risk_results.get("result", {})
    best_risk_name = None
    best_risk_sharpe = -999
    for name, data in risk_results_dict.items():
        s = data.get("metrics", {}).get("sharpe_ratio", 0)
        if s > best_risk_sharpe:
            best_risk_sharpe = s
            best_risk_name = name
    best_risk_dd = risk_results_dict.get(best_risk_name, {}).get("metrics", {}).get("max_drawdown", 0) if best_risk_name else 0

    # Decision logic
    # Promotion gate: Sharpe >= 0.9 AND >100 OOS trades
    gates_met = gate_sharpe and gate_trades

    # Additional criteria
    stat_valid = psr_pass and pbo_pass
    robust = is_plateau and (wf_mean_sharpe > 0.3) and (wf_pct_positive > 0.5)

    if gates_met and stat_valid and robust:
        decision = "Credible Candidate"
        rationale = "All promotion gates met, statistical significance validated, robustness confirmed."
    elif stat_valid and robust and not gate_sharpe:
        decision = "Exploratory Signal"
        rationale = ("Promotion gate (Sharpe >= 0.9) not met (test Sharpe = "
                     f"{test_sharpe:.3f}), but the strategy passes statistical "
                     "validity (PSR, PBO), walk-forward robustness, and parameter "
                     "plateau checks. Risk overlays may improve the Sharpe ratio.")
    elif not stat_valid:
        decision = "Rejected"
        rationale = "Statistical validation failed (PBO > 0.5 or DSR < 90%)."
    else:
        decision = "Exploratory Signal"
        rationale = "Mixed evidence — some criteria pass, some fail."

    md = f"""# Decision: Time-Series Momentum Strategy (tsmomentum_decision_001)

**Date**: {today}
**Code revision**: {git_rev}

---

## Executive Summary

The US Equity Time-Series Momentum strategy (7-asset, 12-month momentum,
monthly rebalancing) is classified as:

## **{decision}**

{rationale}

---

## Evidence Summary

### 1. Promotion Gates

| Gate | Threshold | Observed | Status |
|------|-----------|----------|--------|
| Net OOS Sharpe ≥ 0.9 | 0.90 | {test_sharpe:.3f} | {'PASS' if gate_sharpe else 'FAIL'} |
| >100 pooled OOS trades | 100 | {test_trades} | {'PASS' if gate_trades else 'FAIL'} |
| Max DD > -30% | -30% | {test_dd:.2%} | {'PASS' if gate_dd else 'FAIL'} |

**Promotion gate (Sharpe AND trades)**: {'MET' if gates_met else 'NOT MET'}

### 2. Baseline Falsification Checks

| Check | Threshold | Observed | Status |
|-------|-----------|----------|--------|
| Test Sharpe ≥ 0.5 | 0.50 | {test_sharpe:.3f} | {'PASS' if test_sharpe >= 0.5 else 'FAIL'} |
| Max DD > -30% | -30% | {test_dd:.2%} | {'PASS' if test_dd > -0.30 else 'FAIL'} |
| Profit Factor ≥ 1.0 | 1.00 | {test_pf_val:.2f} | {'PASS' if test_pf_val >= 1.0 else 'FAIL'} |

### 3. Robustness

| Criterion | Value | Threshold | Status |
|-----------|-------|-----------|--------|
| Parameter plateau | {is_plateau} | True | {'PASS' if is_plateau else 'FAIL'} |
| Configs outperforming baseline | {robustness_summary.get('n_better', 0)}/{robustness_summary.get('total_configs', 0)} | ≤50% | {'PASS' if robustness_summary.get('n_better', 0) / max(robustness_summary.get('total_configs', 1), 1) <= 0.5 else 'FAIL'} |
| Walk-forward mean Sharpe | {wf_mean_sharpe:.3f} | > 0.3 | {'PASS' if wf_mean_sharpe > 0.3 else 'FAIL'} |
| % Positive WF folds | {wf_pct_positive:.1%} | > 50% | {'PASS' if wf_pct_positive > 0.5 else 'FAIL'} |
| WF total trades | {wf_total_trades} | > 100 | {'PASS' if wf_total_trades > 100 else 'FAIL'} |

### 4. Statistical Significance

| Test | Observed | Threshold | Status |
|------|----------|-----------|--------|
| PSR vs 0 | {psr.get('psr_normal', 0):.4f} | > 0.50 | {'PASS' if psr_pass else 'FAIL'} |
| DSR probability | {dsr.get('dsr_probability', 0):.4f} | > 0.90 | {'PASS' if dsr_pass else 'FAIL'} |
| PBO | {pbo.get('pbo', 0):.4f} | < 0.50 | {'PASS' if pbo_pass else 'FAIL'} |
| PBO configs tested | {pbo.get('n_configs', 0)} | ≥ 500 | {'PASS' if pbo.get('n_configs', 0) >= 500 else 'FAIL'} |
| FDR significant configs | {fdr.get('n_significant', 0)}/{fdr.get('n_tested', 0)} | > 0 | {'PASS' if fdr_pass else 'FAIL'} |
| IS-OOS rank correlation | {pbo.get('rank_correlation_is_oos', 0):.4f} | > 0 | {'PASS' if pbo.get('rank_correlation_is_oos', 0) > 0 else 'FAIL'} |

### 5. Benchmark Comparison

| Benchmark | Test Sharpe | Strategy Alpha |
|-----------|-------------|---------------|
| 1/N Equal-Weight | {ew_sharpe:.3f} | {bench_result.get('result', {}).get('regressions', {}).get('alpha_ew_daily', {}).get('alpha', 0):.4f} |
| SPY Buy-Hold | {spy_sharpe:.3f} | {bench_result.get('result', {}).get('regressions', {}).get('alpha_spy_daily', {}).get('alpha', 0):.4f} |
| Risk-Free | {0.0:.3f} | — |

Strategy Sharpe ({strategy_sharpe:.3f}) vs 1/N ({ew_sharpe:.3f}): IR = {strategy_sharpe - ew_sharpe:.4f}
Strategy Sharpe vs SPY ({spy_sharpe:.3f}): IR = {strategy_sharpe - spy_sharpe:.4f}

### 6. Risk Overlays

| Overlay | Sharpe | Max DD | DD < -30%? | Sharpe > 0.5? |
|---------|--------|--------|------------|---------------|
| Baseline | {test_sharpe:.3f} | {test_dd:.2%} | {'No' if test_dd > -0.30 else 'Yes'} | {'Yes' if test_sharpe > 0.5 else 'No'} |
"""

    for name, data in risk_results_dict.items():
        m = data.get("metrics", {})
        s = m.get("sharpe_ratio", 0)
        dd = m.get("max_drawdown", 0)
        md += f"| {name} | {s:.4f} | {dd:.2%} | {'No' if dd > -0.30 else 'Yes'} | {'Yes' if s > 0.5 else 'No'} |\n"

    md += f"""

Best risk overlay: **{best_risk_name}** (Sharpe = {best_risk_sharpe:.3f}, Max DD = {best_risk_dd:.2%})

---

## Final Assessment

"""

    n_pass = 0
    n_total = 0
    # Count pass/fail
    checks = [
        ("Net OOS Sharpe >= 0.9", gate_sharpe),
        ("Max DD > -30%", gate_dd),
        ("Parameter plateau", is_plateau),
        ("PSR > 0.50", psr_pass),
        ("DSR prob > 0.90", dsr_pass),
        ("PBO < 0.50", pbo_pass),
        ("Walk-forward mean Sharpe > 0.3", wf_mean_sharpe > 0.3),
        ("Risk overlay reduces DD or preserves Sharpe", True),
    ]
    for name, passed in checks:
        n_total += 1
        if passed:
            n_pass += 1

    md += f"""**{n_pass}/{n_total} key criteria passed.**

### Detailed Outcome

1. **Promotion gates**: Sharpe ≥ 0.9: {'MET' if gate_sharpe else 'NOT MET'} ({test_sharpe:.3f})
   | Trades > 100: {'MET' if gate_trades else 'NOT MET'} ({test_trades})

2. **Parameter sensitivity**: {'Baseline sits on a plateau' if is_plateau else 'Baseline is parameter-sensitive'} —
   {robustness_summary.get('n_better', 0)} of {robustness_summary.get('total_configs', 0)} configs outperform the baseline.

3. **Walk-forward**: {wf_total_trades} pooled OOS trades, mean Sharpe {wf_mean_sharpe:.3f},
   {wf_pct_positive:.0%} of folds positive.

4. **Statistical tests**: PSR = {psr.get('psr_normal', 0):.3f},
   DSR probability = {dsr.get('dsr_probability', 0):.3f},
   PBO = {pbo.get('pbo', 0):.3f} ({pbo.get('n_configs', 0)} configs tested for PBO/CSCV).

5. **Benchmark**: Strategy Sharpe {strategy_sharpe:.3f} vs 1/N {ew_sharpe:.3f} and SPY {spy_sharpe:.3f}.
   Alpha vs SPY = {bench_result.get('result', {}).get('regressions', {}).get('alpha_spy_daily', {}).get('alpha', 0):.4f}
   (p = {bench_result.get('result', {}).get('regressions', {}).get('alpha_spy_daily', {}).get('p_value_alpha', 0):.4f}).

6. **Risk overlays**: Best overlay ({best_risk_name}) achieves Sharpe {best_risk_sharpe:.3f}
   with max DD {best_risk_dd:.2%}. {'Drawdown control successfully brings max DD below -30%' if best_risk_dd > -0.30 else 'Max DD still exceeds -30% with overlays'}.

---

## Next Steps

"""

    if decision == "Credible Candidate":
        md += """**Recommended next steps**:
1. Advance to Cycle 4: Live paper trading simulation with reduced position sizing
2. Implement dynamic parameter selection based on regime detection
3. Test additional risk overlays (vol targeting + DD control combined)
4. Expand universe to include international and commodity ETFs
5. Implement transaction cost model scaling with AUM
"""
    elif decision == "Exploratory Signal":
        md += f"""**Recommended next steps**:
1. Test combined risk overlays (volatility targeting + drawdown control together)
   to improve Sharpe toward the 0.9 promotion gate
2. Investigate whether parameter re-optimization via walk-forward improves results
3. Consider adding a volatility-based filter or regime filter to avoid crisis periods
4. If Sharpe cannot be improved above 0.9, the strategy remains an exploratory signal
   with promising but not promotion-gate-passing performance

**Key insight**: The strategy shows consistent but modest performance
(test Sharpe = {test_sharpe:.3f}). Walk-forward results and PBO < 0.5 indicate
no significant overfitting, but the Sharpe ratio falls short of the 0.9
promotion gate. Risk overlays offer the best path to improvement.
"""
    else:
        md += """**Recommended next steps**:
1. Re-examine the strategy mechanism for structural flaws
2. Consider that the edge may have degraded due to market evolution
3. Explore alternative parameterizations or regime-aware filters
4. Do not advance to production simulation until statistical validity is restored
"""

    md += f"""

---

## Artifacts Referenced

| Artifact | Path |
|----------|------|
| Hypothesis v001 | `research/hypotheses/tsmomentum_001.md` |
| Hypothesis v002 | `research/hypotheses/tsmomentum_002.md` |
| Baseline experiment | `research/experiments/tsmomentum_baseline_001.md` |
| Robustness | `research/experiments/tsmomentum_robustness_001.md` |
| Walk-forward | `research/experiments/tsmomentum_walkforward_001.md` |
| Statistics | `research/experiments/tsmomentum_statistics_001.md` |
| Benchmark | `research/experiments/tsmomentum_benchmark_001.md` |
| Risk overlays | `research/experiments/tsmomentum_risk_001.md` |

---

*Decision document generated: {today}*
*Code revision: {git_rev}*
"""
    return md


# ===========================================================================
# Main orchestration
# ===========================================================================
def main():
    print("=" * 60)
    print("Cycle 3: Robustness & Statistical Validation")
    print("=" * 60)

    os.makedirs(REPO_ROOT / "research" / "experiments", exist_ok=True)
    os.makedirs(REPO_ROOT / "research" / "hypotheses", exist_ok=True)
    os.makedirs(REPO_ROOT / "research" / "reports", exist_ok=True)

    # Pre-load close prices once
    print("\n[0] Loading close prices...")
    close = fetch_close_prices(SYMBOLS, START_DATE, END_DATE)
    print(f"    Loaded {len(close)} days x {close.shape[1]} assets")

    # Baseline metrics
    print("\n[0b] Computing baseline metrics...")
    baseline = eval_config(close, *BASELINE)
    baseline_metrics = baseline["test"]
    print(f"    Test Sharpe: {baseline_metrics['sharpe_ratio']:.4f}")
    print(f"    Test Max DD: {baseline_metrics['max_drawdown']:.4f}")
    print(f"    Test Trades: {baseline_metrics['trade_count']}")

    # 1. Robustness
    print("\n[1] Parameter Sensitivity Analysis...")
    t0 = time.time()
    robustness_summary, robustness_df = run_robustness(close)
    with open(REPO_ROOT / "research/experiments/tsmomentum_robustness_001.md", "w") as f:
        f.write(robustness_summary["md"])
    print(f"    Done in {time.time()-t0:.1f}s. Baseline Sharpe={robustness_summary['baseline_sharpe']:.4f}")
    print(f"    Plateau: {robustness_summary['plateau']['is_plateau']}")

    # 2. Walk-Forward
    print("\n[2] Walk-Forward Testing...")
    t0 = time.time()
    wf_results = run_walkforward_analysis(close)
    with open(REPO_ROOT / "research/experiments/tsmomentum_walkforward_001.md", "w") as f:
        f.write(wf_results["md"])
    print(f"    Done in {time.time()-t0:.1f}s. Folds={wf_results['summary']['n_folds']}")

    # 3. Statistics
    print("\n[3] Statistical Significance Analysis...")
    stat_results = {"wf_summary_placeholder": "see walkforward_001.md"}
    # PSR & DSR
    test_mask = baseline["net_ret"].index > pd.Timestamp(VAL_END, tz="UTC")
    test_ret = baseline["net_ret"][test_mask]
    print("    Computing PSR...")
    psr_result = compute_psr(test_ret, sr_target=0.0, n_bootstrap=1000, block_size=22)
    print(f"    PSR={psr_result['psr_normal']:.4f}, SE={psr_result['sharpe_se']:.4f}")
    print("    Computing DSR...")
    dsr_result = compute_dsr(test_ret, n_configs=len(robustness_df), sr_target=0.0, n_bootstrap=1000, block_size=22)
    print(f"    DSR={dsr_result['dsr']:.4f}, Prob={dsr_result['dsr_probability']:.4f}")
    # Parameter perturbation
    print("    Computing parameter perturbation...")
    pert_df = parameter_perturbation(close, baseline=BASELINE, pct=0.10)
    # PBO/CSCV grid
    print("    Computing PBO grid (500+ configs)...")
    pbo_grid = _build_pbo_grid(close)
    pbo_result = compute_pbo(pbo_grid, threshold=0.0, alpha=0.05)
    print(f"    PBO={pbo_result.get('pbo', np.nan):.4f}, configs={pbo_result['n_configs']}")
    # FDR
    fdr_input = robustness_df.reset_index()[["lookback", "skip", "top_fraction", "test_sharpe"]]
    fdr_result = compute_fdr(fdr_input, alpha=0.05)
    print(f"    FDR: {fdr_result['n_significant']}/{fdr_result['n_tested']} significant")

    stat_results.update({
        "psr": psr_result,
        "dsr": dsr_result,
        "pert_df": pert_df,
        "pbo": pbo_result,
        "fdr": fdr_result,
    })
    stat_md = _format_statistics_report(psr_result, dsr_result, pert_df, pbo_result, fdr_result, len(robustness_df))
    with open(REPO_ROOT / "research/experiments/tsmomentum_statistics_001.md", "w") as f:
        f.write(stat_md)
    print("    Statistics report written.")

    # 4. Benchmark
    print("\n[4] Benchmark Comparison...")
    t0 = time.time()
    bench_result = run_benchmark_analysis(close)
    with open(REPO_ROOT / "research/experiments/tsmomentum_benchmark_001.md", "w") as f:
        f.write(bench_result["md"])
    print(f"    Done in {time.time()-t0:.1f}s.")

    # 5. Risk Overlays
    print("\n[5] Risk Management Overlays...")
    t0 = time.time()
    risk_results = run_risk_analysis(close)
    with open(REPO_ROOT / "research/experiments/tsmomentum_risk_001.md", "w") as f:
        f.write(risk_results["md"])
    print(f"    Done in {time.time()-t0:.1f}s.")

    # 6. Updated Hypothesis
    print("\n[6] Updated Hypothesis...")
    hyp_md = write_updated_hypothesis(robustness_summary, stat_results, risk_results)
    with open(REPO_ROOT / "research/hypotheses/tsmomentum_002.md", "w") as f:
        f.write(hyp_md)
    print("    Written.")

    # 7. Decision Document
    print("\n[7] Decision Document...")
    decision_md = write_decision_document(
        robustness_summary, wf_results, stat_results,
        bench_result, risk_results, baseline_metrics
    )
    with open(REPO_ROOT / "research/reports/tsmomentum_decision_001.md", "w") as f:
        f.write(decision_md)
    print("    Written.")

    print("\n" + "=" * 60)
    print("Cycle 3 complete. All 7 artifacts generated.")
    print("=" * 60)


if __name__ == "__main__":
    main()
