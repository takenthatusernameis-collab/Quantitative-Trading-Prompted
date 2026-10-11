"""Parameter sensitivity analysis for the time-series momentum strategy.

Systematically explores the (lookback, skip, top_fraction) parameter grid and
reports test-period Sharpe, return, drawdown, turnover, and trade count for
each combination. Identifies whether the baseline configuration (252, 21, 0.5)
sits on a performance plateau or an isolated peak.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from src.evaluation.utils import (
    _project_root,
    fetch_close_prices,
    run_backtest_for_config,
    split_by_periods,
    period_metrics,
)


def run_parameter_sensitivity(
    symbols: list[str],
    start_date: str,
    end_date: str,
    lookbacks: list[int],
    skips: list[int],
    top_fractions: list[float],
    output_path: Optional[Path] = None,
) -> pd.DataFrame:
    """Run a grid search over momentum parameters.

    Returns a DataFrame indexed by (lookback, skip, top_fraction) with
    columns: test_sharpe, test_ann_return, test_max_dd, test_trades,
    test_turnover, val_sharpe, train_sharpe.
    """
    rows = []
    total = len(lookbacks) * len(skips) * len(top_fractions)
    count = 0
    for lb in lookbacks:
        for sk in skips:
            for tf in top_fractions:
                count += 1
                print(f"  [{count}/{total}] lookback={lb}, skip={sk}, top_frac={tf}")
                try:
                    net_ret, weights, _ = run_backtest_for_config(
                        symbols, start_date, end_date, lb, sk, tf
                    )
                    periods = split_by_periods(net_ret, weights)
                    train_m = period_metrics(periods["train"]["returns"], periods["train"]["weights"])
                    val_m = period_metrics(periods["validation"]["returns"], periods["validation"]["weights"])
                    test_m = period_metrics(periods["test"]["returns"], periods["test"]["weights"])
                    rows.append({
                        "lookback": lb,
                        "skip": sk,
                        "top_fraction": tf,
                        "train_sharpe": train_m.get("sharpe_ratio", np.nan),
                        "val_sharpe": val_m.get("sharpe_ratio", np.nan),
                        "test_sharpe": test_m.get("sharpe_ratio", np.nan),
                        "test_ann_return": test_m.get("annualized_return", np.nan),
                        "test_max_dd": test_m.get("max_drawdown", np.nan),
                        "test_trades": test_m.get("trade_count", np.nan),
                        "test_turnover": test_m.get("annualized_turnover", np.nan),
                        "test_profit_factor": test_m.get("profit_factor", np.nan),
                    })
                except Exception as exc:
                    print(f"    ERROR: {exc}")
                    rows.append({
                        "lookback": lb,
                        "skip": sk,
                        "top_fraction": tf,
                        "train_sharpe": np.nan,
                        "val_sharpe": np.nan,
                        "test_sharpe": np.nan,
                        "test_ann_return": np.nan,
                        "test_max_dd": np.nan,
                        "test_trades": np.nan,
                        "test_turnover": np.nan,
                        "test_profit_factor": np.nan,
                    })

    df = pd.DataFrame(rows)
    df = df.set_index(["lookback", "skip", "top_fraction"])
    if output_path is not None:
        df.to_csv(output_path)
    return df


def build_heatmap(df: pd.DataFrame, value_col: str = "test_sharpe") -> dict:
    """Pivot a results DataFrame into a {top_fraction: (lookback x skip) DataFrame} dict."""
    heatmaps = {}
    for tf in df.index.get_level_values("top_fraction").unique():
        sub = df.xs(tf, level="top_fraction")
        heatmaps[tf] = sub.pivot_table(
            values=value_col,
            index="lookback",
            columns="skip",
            aggfunc="first",
        )
    return heatmaps


def format_heatmap_markdown(heatmaps: dict, value_label: str) -> str:
    """Format heatmaps as markdown tables."""
    try:
        from tabulate import tabulate
        use_tabulate = True
    except ImportError:
        use_tabulate = False

    lines = []
    for tf, hm in heatmaps.items():
        lines.append(f"### Top Fraction = {tf:.0%} ({value_label})\n")
        if use_tabulate:
            lines.append(tabulate(hm.round(3), headers="keys", tablefmt="github"))
        else:
            lines.append(hm.round(3).to_markdown())
        lines.append("")
    return "\n".join(lines)


def summarize_plateau(df: pd.DataFrame, baseline: tuple = (252, 21, 0.5)) -> dict:
    """Assess whether the baseline sits on a plateau or an isolated peak.

    Returns a dict with: baseline_test_sharpe, mean_test_sharpe, std_test_sharpe,
    n_better, n_worse, is_plateau (bool), plateau_radius.
    """
    test_sharpes = df["test_sharpe"].dropna()
    if test_sharpes.empty:
        return {}

    baseline_sharpe = df.loc[baseline, "test_sharpe"] if baseline in df.index else np.nan
    mean_sharpe = test_sharpes.mean()
    std_sharpe = test_sharpes.std()
    n_better = int((test_sharpes > baseline_sharpe).sum())
    n_worse = int((test_sharpes < baseline_sharpe).sum())

    within_05 = (test_sharpes - baseline_sharpe).abs() <= 0.05
    plateau_fraction = float(within_05.mean())

    return {
        "baseline_test_sharpe": float(baseline_sharpe),
        "mean_test_sharpe": float(mean_sharpe),
        "std_test_sharpe": float(std_sharpe),
        "n_better": n_better,
        "n_worse": n_worse,
        "n_within_0.05_sharpe": int(within_05.sum()),
        "plateau_fraction": plateau_fraction,
        "is_plateau": bool(plateau_fraction >= 0.2),
    }