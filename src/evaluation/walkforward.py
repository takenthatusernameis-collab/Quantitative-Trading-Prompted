"""Walk-forward testing module."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.evaluation.utils import (
    period_metrics,
    run_backtest_for_config,
)


def generate_walkforward_splits(
    start_date: str,
    end_date: str,
    train_years: float = 10.0,
    test_months: float = 12.0,
    step_months: float = 6.0,
    purge_days: int = 21,
    embargo_days: int = 21,
) -> list[dict]:
    """Generate chronological walk-forward train/test splits.

    Returns a list of dicts with keys: train_start, train_end, test_start, test_end.
    """
    all_dates = pd.bdate_range(start=start_date, end=end_date)
    if len(all_dates) == 0:
        return []

    splits = []
    train_window = int(train_years * 252)
    test_window = int(test_months * 21)
    step = int(step_months * 21)

    idx = 0
    while idx + train_window + test_window <= len(all_dates):
        train_start = all_dates[idx]
        train_end_idx = idx + train_window - 1
        train_end = all_dates[train_end_idx]

        # Purge gap between train and test
        test_start_idx = train_end_idx + 1 + purge_days
        if test_start_idx >= len(all_dates):
            break
        test_start = all_dates[test_start_idx]

        test_end_idx = test_start_idx + test_window - 1
        if test_end_idx >= len(all_dates):
            test_end = all_dates[-1]
        else:
            test_end = all_dates[test_end_idx]

        splits.append({
            "train_start": train_start.strftime("%Y-%m-%d"),
            "train_end": train_end.strftime("%Y-%m-%d"),
            "test_start": test_start.strftime("%Y-%m-%d"),
            "test_end": test_end.strftime("%Y-%m-%d"),
            "train_start_idx": idx,
            "train_end_idx": train_end_idx,
            "test_start_idx": test_start_idx,
            "test_end_idx": test_end_idx,
        })

        idx += step

    return splits


def run_walkforward(
    symbols: list[str],
    start_date: str,
    end_date: str,
    lookback: int = 252,
    skip: int = 21,
    top_fraction: float = 0.5,
    train_years: float = 10.0,
    test_months: float = 12.0,
    step_months: float = 6.0,
    purge_days: int = 21,
    embargo_days: int = 21,
) -> pd.DataFrame:
    """Run walk-forward testing with expanding or rolling window.

    Returns a DataFrame with one row per fold containing metrics.
    """
    splits = generate_walkforward_splits(
        start_date, end_date, train_years, test_months, step_months,
        purge_days, embargo_days,
    )

    rows = []
    for i, sp in enumerate(splits):
        print(f"  Fold {i+1}/{len(splits)}: train {sp['train_start']}->{sp['train_end']}, "
              f"test {sp['test_start']}->{sp['test_end']}")
        try:
            # Train on train period
            train_ret, train_w, _ = run_backtest_for_config(
                symbols, sp["train_start"], sp["train_end"],
                lookback, skip, top_fraction,
            )
            train_m = period_metrics(train_ret, train_w)

            # Test on test period (re-fetch data for test range, but use same params)
            test_ret, test_w, _ = run_backtest_for_config(
                symbols, sp["test_start"], sp["test_end"],
                lookback, skip, top_fraction,
            )
            test_m = period_metrics(test_ret, test_w)

            rows.append({
                "fold": i + 1,
                "train_start": sp["train_start"],
                "train_end": sp["train_end"],
                "test_start": sp["test_start"],
                "test_end": sp["test_end"],
                "train_sharpe": train_m.get("sharpe_ratio", np.nan),
                "train_ann_return": train_m.get("annualized_return", np.nan),
                "test_sharpe": test_m.get("sharpe_ratio", np.nan),
                "test_ann_return": test_m.get("annualized_return", np.nan),
                "test_max_dd": test_m.get("max_drawdown", np.nan),
                "test_turnover": test_m.get("annualized_turnover", np.nan),
                "test_trades": test_m.get("trade_count", np.nan),
                "test_profit_factor": test_m.get("profit_factor", np.nan),
            })
        except Exception as exc:  # noqa: BLE001  # intentional: walk-forward continues past any per-fold failure
            print(f"    ERROR: {exc}")
            rows.append({
                "fold": i + 1,
                "train_start": sp["train_start"],
                "train_end": sp["train_end"],
                "test_start": sp["test_start"],
                "test_end": sp["test_end"],
                "train_sharpe": np.nan,
                "train_ann_return": np.nan,
                "test_sharpe": np.nan,
                "test_ann_return": np.nan,
                "test_max_dd": np.nan,
                "test_turnover": np.nan,
                "test_trades": np.nan,
                "test_profit_factor": np.nan,
            })

    return pd.DataFrame(rows)


def summarize_walkforward(wf_df: pd.DataFrame) -> dict:
    """Compute aggregate statistics from walk-forward results."""
    test_sharpes = wf_df["test_sharpe"].dropna()
    if test_sharpes.empty:
        return {}

    return {
        "n_folds": len(wf_df),
        "mean_test_sharpe": float(test_sharpes.mean()),
        "std_test_sharpe": float(test_sharpes.std()),
        "median_test_sharpe": float(test_sharpes.median()),
        "min_test_sharpe": float(test_sharpes.min()),
        "max_test_sharpe": float(test_sharpes.max()),
        "pct_positive_sharpe": float((test_sharpes > 0).mean()),
        "mean_test_ann_return": float(wf_df["test_ann_return"].dropna().mean()),
        "mean_test_max_dd": float(wf_df["test_max_dd"].dropna().mean()),
        "mean_test_trades": float(wf_df["test_trades"].dropna().mean()),
        "total_test_trades": int(wf_df["test_trades"].dropna().sum()),
    }