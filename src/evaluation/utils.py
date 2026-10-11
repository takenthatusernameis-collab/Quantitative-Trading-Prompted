"""Shared utilities for evaluation modules.

Provides common helpers: data loading, cost parameters, metric computation,
and period splitting. All evaluation modules import from here to avoid
duplicated logic and ensure consistent cost assumptions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import yaml

from src.backtest.engine import (
    compute_metrics,
    get_cost_params,
    get_risk_free_rate,
)
from src.data.yfinance_fetcher import fetch_universe
from src.features.momentum import build_weights


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def load_settings() -> dict:
    path = _project_root() / "config" / "settings.yaml"
    with open(path, "r") as fh:
        return yaml.safe_load(fh) or {}


def fetch_close_prices(
    symbols: list[str],
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Return a clean Close-price DataFrame for the given universe."""
    data = fetch_universe(symbols, start_date, end_date, force=False)
    if data.empty:
        raise RuntimeError("No data fetched")
    close = data.xs("Close", level=0, axis=1)
    close = close.ffill().dropna(how="all")
    return close


def run_backtest_for_config(
    symbols: list[str],
    start_date: str,
    end_date: str,
    lookback: int,
    skip: int,
    top_fraction: float,
) -> tuple[pd.Series, pd.DataFrame, dict]:
    """Run the backtest for a given parameter configuration.

    Returns (net_returns, weights, metrics) where metrics is a single dict
    (not split by period).
    """
    close = fetch_close_prices(symbols, start_date, end_date)
    weights = build_weights(close, lookback=lookback, skip=skip, top_fraction=top_fraction)

    common_index = close.index.intersection(weights.index)
    close = close.loc[common_index]
    weights = weights.loc[common_index]

    daily_ret = close.pct_change().fillna(0.0)
    port_ret = (weights * daily_ret).sum(axis=1)

    commission_bps, slippage_bps = get_cost_params()
    weight_changes = weights.diff().abs().sum(axis=1)
    cost_per_trade = commission_bps + slippage_bps
    costs = weight_changes * cost_per_trade
    net_ret = port_ret - costs

    rf_annual = get_risk_free_rate()
    metrics = compute_metrics(net_ret, weights, commission_bps, slippage_bps, rf_annual)
    return net_ret, weights, metrics


def split_by_periods(
    returns: pd.Series,
    weights: pd.DataFrame,
    train_end: str = "2009-12-31",
    val_end: str = "2017-12-31",
) -> dict:
    """Split returns/weights into train/validation/test periods."""
    train_end_dt = pd.Timestamp(train_end, tz="UTC")
    val_end_dt = pd.Timestamp(val_end, tz="UTC")

    train_mask = returns.index <= train_end_dt
    val_mask = (returns.index > train_end_dt) & (returns.index <= val_end_dt)
    test_mask = returns.index > val_end_dt

    return {
        "train": {"returns": returns[train_mask], "weights": weights[train_mask]},
        "validation": {"returns": returns[val_mask], "weights": weights[val_mask]},
        "test": {"returns": returns[test_mask], "weights": weights[test_mask]},
    }


def period_metrics(
    returns: pd.Series,
    weights: pd.DataFrame,
) -> dict:
    """Compute metrics for a single period."""
    commission_bps, slippage_bps = get_cost_params()
    rf_annual = get_risk_free_rate()
    return compute_metrics(returns, weights, commission_bps, slippage_bps, rf_annual)


def annualize_return(returns: pd.Series, periods: int = 252) -> float:
    if len(returns) == 0:
        return 0.0
    return float((1 + returns).prod() ** (periods / len(returns)) - 1)


def sharpe_ratio(returns: pd.Series, rf_annual: float = 0.02) -> float:
    if len(returns) < 2:
        return 0.0
    ann_vol = returns.std() * np.sqrt(252)
    if ann_vol == 0:
        return 0.0
    ann_ret = annualize_return(returns)
    return float((ann_ret - rf_annual) / ann_vol)


def max_drawdown(returns: pd.Series) -> float:
    if len(returns) == 0:
        return 0.0
    cum = (1 + returns).cumprod()
    running_max = cum.expanding().max()
    dd = (cum / running_max) - 1
    return float(dd.min())