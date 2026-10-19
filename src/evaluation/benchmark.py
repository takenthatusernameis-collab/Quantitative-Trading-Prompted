"""Benchmark comparison module for the time-series momentum strategy.

Compares the strategy against:
  - Equal-weighted (1/N) portfolio of the same 7 assets
  - SPY buy-and-hold
  - Risk-free rate (2% annual)

Computes alpha/beta regression, correlation analysis, and attribution.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from src.evaluation.sharpe import backtest_sharpe_ratio
from src.evaluation.utils import (
    annualize_return,
    fetch_close_prices,
    get_cost_params,
    get_risk_free_rate,
    max_drawdown,
)
from src.features.momentum import build_weights


def compute_equal_weight_returns(
    close: pd.DataFrame,
    start_idx: int,
    end_idx: int,
) -> pd.Series:
    """Equal-weighted (1/N) portfolio returns using the same 7 assets.

    Each day, weight is 1/N for each available asset (N = number of non-NaN
    assets that day). No transaction costs applied (proxy benchmark).
    """
    daily_ret = close.pct_change().fillna(0.0)
    n_assets = close.notna().sum(axis=1).replace(0, np.nan)
    ew_weights = close.notna().astype(float).div(n_assets, axis=0)
    port_ret = (ew_weights * daily_ret).sum(axis=1)
    return port_ret.iloc[start_idx:end_idx].dropna()


def compute_buy_hold_returns(
    close_spy: pd.Series,
    start_idx: int,
    end_idx: int,
) -> pd.Series:
    """SPY buy-and-hold daily total return (price return)."""
    daily_ret = close_spy.pct_change().fillna(0.0)
    return daily_ret.iloc[start_idx:end_idx].dropna()


def compute_rf_returns(dates: pd.DatetimeIndex, rf_annual: float = 0.02) -> pd.Series:
    """Daily risk-free returns from annual rate."""
    daily_rf = rf_annual / 252.0
    return pd.Series(daily_rf, index=dates)


def alpha_beta_regression(
    strategy_returns: pd.Series,
    benchmark_returns: pd.Series,
    frequency: str = "daily",
) -> dict:
    """Run OLS regression: strategy_returns = alpha + beta * benchmark_returns + eps.

    Parameters
    ----------
    strategy_returns, benchmark_returns:
        Series of excess returns (over risk-free rate).
    frequency:
        "daily" or "monthly" — affects annualization of alpha.
    """
    if frequency == "monthly":
        s = strategy_returns.resample("ME").sum()
        b = benchmark_returns.resample("ME").sum()
        periods = 12
    else:
        s = strategy_returns
        b = benchmark_returns
        periods = 252

    aligned = pd.concat([s, b], axis=1).dropna()
    if len(aligned) < 3:
        return {"alpha": np.nan, "beta": np.nan, "r_squared": np.nan, "t_stat_alpha": np.nan, "p_value_alpha": np.nan}

    s_vals = aligned.iloc[:, 0].values
    b_vals = aligned.iloc[:, 1].values

    X = sm.add_constant(b_vals)
    try:
        model = sm.OLS(s_vals, X).fit()
    except (np.linalg.LinAlgError, ValueError):
        return {"alpha": np.nan, "beta": np.nan, "r_squared": np.nan, "t_stat_alpha": np.nan, "p_value_alpha": np.nan}

    alpha_annual = float(model.params[0]) * periods
    beta = float(model.params[1])
    r_sq = float(model.rsquared)
    t_stat_alpha = float(model.tvalues[0])
    p_val_alpha = float(model.pvalues[0])

    return {
        "alpha": alpha_annual,
        "alpha_daily": float(model.params[0]),
        "beta": beta,
        "r_squared": r_sq,
        "t_stat_alpha": t_stat_alpha,
        "p_value_alpha": p_val_alpha,
        "n_observations": int(model.nobs),
        "freq": frequency,
    }


def correlation_analysis(
    strategy_returns: pd.Series,
    benchmarks: dict[str, pd.Series],
) -> pd.DataFrame:
    """Compute correlation matrix between strategy and benchmark returns."""
    data = {"strategy": strategy_returns}
    data.update(benchmarks)
    df = pd.DataFrame(data).dropna()
    return df.corr()


def full_benchmark_comparison(
    symbols: list[str],
    start_date: str,
    end_date: str,
    lookback: int = 252,
    skip: int = 21,
    top_fraction: float = 0.5,
    train_end: str = "2009-12-31",
    val_end: str = "2017-12-31",
) -> dict:
    """Run full benchmark comparison for the baseline strategy.

    Computes:
      - Strategy net returns (with costs)
      - Equal-weight portfolio returns
      - SPY buy-and-hold returns
      - Risk-free returns
      - Alpha/beta regressions (daily, monthly) vs SPY and vs 1/N
      - Correlation analysis
    """
    commission_bps, slippage_bps = get_cost_params()
    rf_annual = get_risk_free_rate()
    cost = commission_bps + slippage_bps

    close = fetch_close_prices(symbols, start_date, end_date)
    weights = build_weights(close, lookback=lookback, skip=skip, top_fraction=top_fraction)
    common = close.index.intersection(weights.index)
    close_a = close.loc[common]
    weights_a = weights.loc[common]

    daily_ret = close_a.pct_change().fillna(0.0)
    port_ret = (weights_a * daily_ret).sum(axis=1)
    wc = weights_a.diff().abs().sum(axis=1)
    strategy_ret = port_ret - wc * cost

    train_end_dt = pd.Timestamp(train_end, tz="UTC")
    val_end_dt = pd.Timestamp(val_end, tz="UTC")

    # Benchmarks
    ew_ret = compute_equal_weight_returns(close_a, 0, len(close_a))
    spy_ret = compute_buy_hold_returns(close_a["SPY"], 0, len(close_a))
    rf_daily = rf_annual / 252.0
    rf_ret = pd.Series(rf_daily, index=close_a.index)

    # Excess returns
    strategy_excess = strategy_ret - rf_ret

    # Split into train/val/test
    periods = {
        "train": (strategy_ret.index <= train_end_dt),
        "validation": (strategy_ret.index > train_end_dt) & (strategy_ret.index <= val_end_dt),
        "test": (strategy_ret.index > val_end_dt),
    }

    # Alpha/beta vs SPY and vs 1/N, daily and monthly
    regressions = {}
    for bench_name, bench_ret in [("spy", spy_ret), ("ew", ew_ret)]:
        for freq in ["daily", "monthly"]:
            s_ex = strategy_excess[periods["test"]]
            b_ex = (bench_ret - rf_ret.reindex(bench_ret.index))[periods["test"]]
            aligned_len = min(len(s_ex), len(b_ex))
            if aligned_len > 10:
                s_ex = s_ex.iloc[-aligned_len:]
                b_ex = b_ex.iloc[-aligned_len:]
                regressions[f"alpha_{bench_name}_{freq}"] = alpha_beta_regression(s_ex, b_ex, freq)

    # Correlations
    corr_daily = correlation_analysis(
        strategy_ret,
        {"spy_buyhold": spy_ret, "ew_portfolio": ew_ret, "rf": rf_ret},
    )

    # Benchmark period stats
    bench_stats = {}
    for name, ret in [("strategy", strategy_ret), ("ew_1n", ew_ret), ("spy_buyhold", spy_ret), ("rf", rf_ret)]:
        for pname, mask in periods.items():
            r = ret[mask]
            if len(r) > 0:
                bench_stats[f"{name}_{pname}"] = {
                    "sharpe": backtest_sharpe_ratio(r),
                    "ann_return": annualize_return(r),
                    "max_dd": max_drawdown(r),
                    "n_days": len(r),
                }

    return {
        "strategy_ret": strategy_ret,
        "ew_ret": ew_ret,
        "spy_ret": spy_ret,
        "rf_ret": rf_ret,
        "strategy_excess": strategy_excess,
        "correlations_daily": corr_daily,
        "regressions": regressions,
        "bench_stats": bench_stats,
        "commission_bps": commission_bps,
        "slippage_bps": slippage_bps,
        "rf_annual": rf_annual,
        "symbols": symbols,
        "lookback": lookback,
        "skip": skip,
        "top_fraction": top_fraction,
    }
