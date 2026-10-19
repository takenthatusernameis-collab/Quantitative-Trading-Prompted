"""Shared utilities for evaluation modules.

Provides common helpers: data loading, cost parameters, metric computation,
and period splitting. All evaluation modules import from here to avoid
duplicated logic and ensure consistent cost assumptions.

The Sharpe ratio itself lives in :mod:`src.evaluation.sharpe`, which holds the
repository's single canonical convention (used by the promotion gates, the
drift flag and the PSR) and the separate backtest-baseline scale used by the
backtest research artifacts. It is re-exported here for convenience.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from src.backtest.engine import (
    compute_metrics,
    get_cost_params,
    get_risk_free_rate,
)
from src.data.yfinance_fetcher import fetch_universe
from src.evaluation.sharpe import (
    BACKTEST_SHARPE_SCALE_FORMULA,
    BACKTEST_SHARPE_SCALE_ID,
    SHARPE_CONVENTION_FORMULA,
    SHARPE_CONVENTION_ID,
    SHARPE_CONVENTION_RF_ANNUAL,
    backtest_sharpe_ratio,
    sharpe_ratio,
)
from src.features.momentum import build_weights

__all__ = [
    "BACKTEST_SHARPE_SCALE_FORMULA",
    "BACKTEST_SHARPE_SCALE_ID",
    "SHARPE_CONVENTION_FORMULA",
    "SHARPE_CONVENTION_ID",
    "SHARPE_CONVENTION_RF_ANNUAL",
    "annualize_return",
    "backtest_sharpe_ratio",
    "compute_running_drawdown",
    "fetch_close_prices",
    "load_settings",
    "max_drawdown",
    "period_metrics",
    "run_backtest_for_config",
    "sharpe_ratio",
    "split_by_periods",
]


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


def max_drawdown(returns: pd.Series) -> float:
    if len(returns) == 0:
        return 0.0
    cum = (1 + returns).cumprod()
    running_max = cum.expanding().max()
    dd = (cum / running_max) - 1
    return float(dd.min())


def compute_running_drawdown(
    peak_nav: float, current_nav: float, prev_max_drawdown: float
) -> tuple[float, float]:
    """Update the running-maximum drawdown for one new NAV observation.

    The drawdown is always measured against the *all-time* peak NAV seen so
    far, not a recent local peak. This is the standard running-maximum
    definition: a portfolio that recovers to a new high and then falls must
    measure the new trough against that new high. Anchoring the running max
    to the current NAV instead silently understates drawdown whenever the
    portfolio has ever been higher than the current window.

    Parameters
    ----------
    peak_nav:
        All-time peak NAV observed before this step.
    current_nav:
        The new NAV observation for this step.
    prev_max_drawdown:
        Most negative drawdown observed before this step (<= 0).

    Returns
    -------
    (new_peak_nav, new_max_drawdown)
        Updated running peak and running maximum drawdown.
    """
    if peak_nav <= 0.0:
        new_peak = current_nav
        new_dd = 0.0
    else:
        new_peak = max(peak_nav, current_nav)
        new_dd = min(prev_max_drawdown, current_nav / new_peak - 1.0)
    return float(new_peak), float(new_dd)