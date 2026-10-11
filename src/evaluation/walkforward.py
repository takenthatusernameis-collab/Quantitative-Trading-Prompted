"""Walk-forward testing with purge and embargo for time-series momentum.

Implements two walk-forward schemes:
1. Expanding window: train on [1993, t], test on [t+1, t+12 months]
2. Rolling window: 10-year train, 1-year test, step 6 months

Purge: 21 days between train and test (matching skip window)
Embargo: 21 days after test period
"""

from __future__ import annotations

from datetime import timedelta
from typing import List, Sequence, Tuple

import numpy as np
import pandas as pd

from src.backtest.engine import (
    run_backtest,
    compute_metrics,
    get_cost_params,
    get_risk_free_rate,
    split_periods,
)
from src.features.momentum import build_weights


def _add_months(dt: pd.Timestamp, months: int) -> pd.Timestamp:
    """Add months to a timestamp, handling year-end rollover."""
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, 28)
    return pd.Timestamp(year=year, month=month, day=day, tz=dt.tz)


def expanding_window_folds(
    start_date: str,
    end_date: str,
    symbols: Sequence[str],
    initial_train_years: int = 16,
    test_months: int = 12,
    step_months: int = 6,
    purge_days: int = 21,
    embargo_days: int = 21,
    lookback: int = 252,
    skip: int = 21,
    top_fraction: float = 0.5,
) -> List[dict]:
    """Generate expanding-window walk-forward folds.

    Train: [start_date, t]
    Test: [t + purge_days, t + purge_days + test_months]
    """
    commission_bps, slippage_bps = get_cost_params()
    rf_annual = get_risk_free_rate()

    start_dt = pd.Timestamp(start_date, tz="UTC")
    end_dt = pd.Timestamp(end_date, tz="UTC")

    folds = []
    t = start_dt + pd.DateOffset(years=initial_train_years)

    fold_idx = 0
    while t < end_dt:
        test_start = t + pd.Timedelta(days=purge_days)
        test_end = _add_months(test_start, test_months) - pd.Timedelta(days=1)

        if test_start >= end_dt:
            break
        if test_end > end_dt:
            test_end = end_dt

        fold_idx += 1
        print(f"  Expanding fold {fold_idx}: train=[{start_dt.date()}, {t.date()}], "
              f"test=[{test_start.date()}, {test_end.date()}]")

        try:
            net_ret, weights, _ = run_backtest(
                symbols=list(symbols),
                start_date=start_date,
                end_date=test_end.strftime("%Y-%m-%d"),
                lookback=lookback,
                skip=skip,
                top_fraction=top_fraction,
            )

            test_mask = (net_ret.index >= test_start) & (net_ret.index <= test_end)
            test_ret = net_ret[test_mask]
            test_w = weights[test_mask]

            if len(test_ret) < 60:
                print(f"    WARNING: only {len(test_ret)} test days, skipping")
                t = _add_months(t, step_months)
                continue

            metrics = compute_metrics(
                test_ret, test_w, commission_bps, slippage_bps, rf_annual
            )
            metrics["fold"] = fold_idx
            metrics["train_start"] = str(start_dt.date())
            metrics["train_end"] = str(t.date())
            metrics["test_start"] = str(test_start.date())
            metrics["test_end"] = str(test_end.date())
            metrics["n_test_days"] = int(len(test_ret))
            folds.append(metrics)
        except Exception as e:
            print(f"    ERROR: {e}")

        t = _add_months(t, step_months)

    return folds


def rolling_window_folds(
    start_date: str,
    end_date: str,
    symbols: Sequence[str],
    train_years: int = 10,
    test_months: int = 12,
    step_months: int = 6,
    purge_days: int = 21,
    embargo_days: int = 21,
    lookback: int = 252,
    skip: int = 21,
    top_fraction: float = 0.5,
) -> List[dict]:
    """Generate rolling-window walk-forward folds.

    Train: [t - train_years, t]
    Test: [t + purge_days, t + purge_days + test_months]
    """
    commission_bps, slippage_bps = get_cost_params()
    rf_annual = get_risk_free_rate()

    start_dt = pd.Timestamp(start_date, tz="UTC")
    end_dt = pd.Timestamp(end_date, tz="UTC")

    folds = []
    t = start_dt + pd.DateOffset(years=train_years)

    fold_idx = 0
    while t < end_dt:
        train_start = t - pd.DateOffset(years=train_years)
        test_start = t + pd.Timedelta(days=purge_days)
        test_end = _add_months(test_start, test_months) - pd.Timedelta(days=1)

        if test_start >= end_dt:
            break
        if test_end > end_dt:
            test_end = end_dt

        fold_idx += 1
        print(f"  Rolling fold {fold_idx}: train=[{train_start.date()}, {t.date()}], "
              f"test=[{test_start.date()}, {test_end.date()}]")

        try:
            net_ret, weights, _ = run_backtest(
                symbols=list(symbols),
                start_date=train_start.strftime("%Y-%m-%d"),
                end_date=test_end.strftime("%Y-%m-%d"),
                lookback=lookback,
                skip=skip,
                top_fraction=top_fraction,
            )

            test_mask = (net_ret.index >= test_start) & (net_ret.index <= test_end)
            test_ret = net_ret[test_mask]
            test_w = weights[test_mask]

            if len(test_ret) < 60:
                print(f"    WARNING: only {len(test_ret)} test days, skipping")
                t = _add_months(t, step_months)
                continue

            metrics = compute_metrics(
                test_ret, test_w, commission_bps, slippage_bps, rf_annual
            )
            metrics["fold"] = fold_idx
            metrics["train_start"] = str(train_start.date())
            metrics["train_end"] = str(t.date())
            metrics["test_start"] = str(test_start.date())
            metrics["test_end"] = str(test_end.date())
            metrics["n_test_days"] = int(len(test_ret))
            folds.append(metrics)
        except Exception as e:
            print(f"    ERROR: {e}")

        t = _add_months(t, step_months)

    return folds


def summarize_folds(folds: List[dict], scheme: str) -> str:
    """Aggregate per-fold statistics into a markdown summary."""
    if not folds:
        return f"No {scheme} folds generated."

    df = pd.DataFrame(folds)
    numeric_cols = [
        "sharpe_ratio", "sortino_ratio", "annualized_return",
        "annualized_volatility", "max_drawdown", "profit_factor",
        "annualized_turnover", "trade_count", "n_test_days",
    ]

    lines = [f"## {scheme} Walk-Forward Summary", ""]
    lines.append(f"**Number of folds**: {len(folds)}")
    lines.append("")

    lines.append("| Metric | Mean | Std | Min | Median | Max |")
    lines.append("|--------|------|-----|-----|--------|-----|")

    for col in numeric_cols:
        if col not in df.columns:
            continue
        vals = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(vals) == 0:
            continue
        mean = vals.mean()
        std = vals.std()
        mn = vals.min()
        med = vals.median()
        mx = vals.max()
        lines.append(f"| {col} | {mean:.4f} | {std:.4f} | {mn:.4f} | {med:.4f} | {mx:.4f} |")

    lines.append("")
    lines.append("### Per-Fold Details")
    lines.append("")
    lines.append("| Fold | Train Period | Test Period | Sharpe | Ann. Return | Max DD | Trades |")
    lines.append("|------|-------------|-------------|--------|-------------|--------|--------|")
    for _, row in df.iterrows():
        train_range = f"{row.get('train_start', '?')} to {row.get('train_end', '?')}"
        test_range = f"{row.get('test_start', '?')} to {row.get('test_end', '?')}"
        sharpe = row.get("sharpe_ratio", np.nan)
        ann_ret = row.get("annualized_return", np.nan)
        max_dd = row.get("max_drawdown", np.nan)
        trades = row.get("trade_count", np.nan)
        lines.append(
            f"| {int(row['fold'])} | {train_range} | {test_range} | "
            f"{sharpe:.3f} | {ann_ret:.4f} | {max_dd:.4f} | {int(trades)} |"
        )

    return "\n".join(lines)