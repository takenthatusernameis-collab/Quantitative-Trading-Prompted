"""Parameter sensitivity analysis for time-series momentum strategy.

Tests a grid of (lookback, skip, top_fraction) configurations on the test
period and reports a heatmap of test-period Sharpe ratios. Determines
whether the baseline configuration sits on a plateau or an isolated peak.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

import numpy as np
import pandas as pd

from src.backtest.engine import run_backtest, split_periods, compute_metrics, get_cost_params, get_risk_free_rate
from src.features.momentum import build_weights


def run_grid_search(
    symbols: Sequence[str],
    start_date: str,
    end_date: str,
    lookbacks: Sequence[int],
    skips: Sequence[int],
    top_fractions: Sequence[float],
    test_start: str = "2018-01-01",
) -> pd.DataFrame:
    """Run backtest for every (lookback, skip, top_fraction) combination.

    Returns a DataFrame indexed by (lookback, skip) with columns for each
    top_fraction, containing test-period Sharpe ratios.
    """
    commission_bps, slippage_bps = get_cost_params()
    rf_annual = get_risk_free_rate()

    results: dict = {}
    total = len(lookbacks) * len(skips) * len(top_fractions)
    count = 0

    for lb in lookbacks:
        for sk in skips:
            for tf in top_fractions:
                count += 1
                print(f"  [{count}/{total}] lookback={lb}, skip={sk}, top_frac={tf}")
                try:
                    net_ret, weights, _ = run_backtest(
                        symbols=list(symbols),
                        start_date=start_date,
                        end_date=end_date,
                        lookback=lb,
                        skip=sk,
                        top_fraction=tf,
                    )
                    periods = split_periods(net_ret, weights)
                    test_metrics = compute_metrics(
                        periods["test"]["returns"],
                        periods["test"]["weights"],
                        commission_bps,
                        slippage_bps,
                        rf_annual,
                    )
                    key = (lb, sk)
                    if key not in results:
                        results[key] = {}
                    results[key][tf] = test_metrics.get("sharpe_ratio", np.nan)
                except Exception as e:
                    print(f"    ERROR: {e}")
                    key = (lb, sk)
                    if key not in results:
                        results[key] = {}
                    results[key][tf] = np.nan

    # Build pivot: rows=lookback, cols=skip, one DataFrame per top_fraction
    rows = []
    for (lb, sk), tf_map in results.items():
        row = {"lookback": lb, "skip": sk}
        for tf in top_fractions:
            row[f"tf_{tf}"] = tf_map.get(tf, np.nan)
        rows.append(row)

    df = pd.DataFrame(rows)
    df = df.set_index(["lookback", "skip"])
    return df


def plateau_analysis(
    grid_df: pd.DataFrame,
    baseline_lookback: int = 252,
    baseline_skip: int = 21,
    baseline_tf: float = 0.5,
    window: float = 0.10,
) -> dict:
    """Determine if baseline is on a plateau or an isolated peak.

    A plateau is defined as: the baseline Sharpe is within (1 - window) of
    the median Sharpe across all configurations, AND at least 20% of
    configurations have Sharpe within 10% of the baseline.

    Returns a dict with classification and supporting statistics.
    """
    col = f"tf_{baseline_tf}"
    if col not in grid_df.columns:
        return {"error": f"Column {col} not found"}

    baseline_val = grid_df.loc[(baseline_lookback, baseline_skip), col]
    all_vals = grid_df[col].dropna()

    if len(all_vals) == 0 or pd.isna(baseline_val):
        return {"error": "No valid Sharpe values"}

    median_val = all_vals.median()
    std_val = all_vals.std()
    max_val = all_vals.max()

    # Fraction of configs within 10% of baseline
    within_10pct = (all_vals >= baseline_val * (1 - window)) & (all_vals <= baseline_val * (1 + window))
    frac_near = within_10pct.mean()

    # Fraction of configs that beat baseline
    frac_beat = (all_vals > baseline_val).mean()

    # Is baseline within 10% of the max?
    near_max = baseline_val >= max_val * (1 - window)

    # Plateau test
    is_on_plateau = frac_near >= 0.20

    # Isolated peak test
    is_isolated_peak = near_max and frac_near < 0.20

    return {
        "baseline_sharpe": float(baseline_val),
        "median_sharpe": float(median_val),
        "std_sharpe": float(std_val),
        "max_sharpe": float(max_val),
        "fraction_within_10pct": float(frac_near),
        "fraction_beating": float(frac_beat),
        "near_max": bool(near_max),
        "is_on_plateau": bool(is_on_plateau),
        "is_isolated_peak": bool(is_isolated_peak),
        "classification": (
            "plateau" if is_on_plateau else ("isolated_peak" if is_isolated_peak else "sensitive")
        ),
    }


def format_heatmap_markdown(
    grid_df: pd.DataFrame,
    title: str,
) -> str:
    """Format a pivot table as a markdown heatmap (text-based)."""
    lines = [f"### {title}", ""]
    lines.append("| Lookback \\ Skip | " + " | ".join(f"{sk}" for sk in grid_df.index.get_level_values('skip').unique()) + " |")
    lines.append("|" + "---|" + "|".join("---|" for _ in range(len(grid_df.index.get_level_values('skip').unique()))) + "|")

    for lb in grid_df.index.get_level_values('lookback').unique():
        row_vals = []
        for sk in grid_df.index.get_level_values('skip').unique():
            try:
                val = grid_df.loc[(lb, sk)]
                if isinstance(val, pd.Series):
                    val = val.iloc[0]
                row_vals.append(f"{val:.3f}" if pd.notna(val) else "N/A")
            except KeyError:
                row_vals.append("N/A")
        lines.append(f"| {lb} | " + " | ".join(row_vals) + " |")

    return "\n".join(lines)