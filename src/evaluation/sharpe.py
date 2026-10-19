"""The repository's Sharpe conventions.

Cycle 861 established a single, documented Sharpe convention for every
promotion-gate, drift-flag and PSR quantity in this repository. Before that
cycle three different estimators were in simultaneous use and they disagreed
on the *verdict* for the same data (see
``research/reports/monitoring_cycle_860.md``, "Estimator discrepancy").

Two scales exist in this repository, and they play different roles:

``sharpe_ratio`` -- the canonical convention
    ``mean(r) * 252 / (std(r, ddof=1) * sqrt(252))``: the arithmetic mean daily
    net-of-cost return, annualised, divided by the annualised sample standard
    deviation, with a zero risk-free rate. This is the convention used by the
    promotion gates, by the ``low_rolling_sharpe`` drift flag and by *both*
    sides of the Probabilistic Sharpe Ratio (the observed Sharpe that forms
    the numerator and the moving-block bootstrap distribution that forms the
    standard error). It is also the scale of every rolling Sharpe quoted in
    the validation artifacts.

``backtest_sharpe_ratio`` -- the backtest-baseline scale
    ``((1+r).prod() ** (252/n) - 1 - rf) / (std(r, ddof=1) * sqrt(252))``:
    the geometric annualised return minus the risk-free rate, over the
    annualised volatility. This is the scale of the recorded backtest baseline
    (Sharpe 1.4178) and of the published backtest research artifacts, so it
    is used for backtest research metrics only. It must never be used in a
    promotion gate, in the drift flag or in the PSR.

The convention is also declared, machine-readably, in
``config/promotion_gates.yaml`` (``sharpe_convention``); the promotion
evaluation refuses to run when the declaration and this module disagree.
"""

from __future__ import annotations

import math

import numpy as np

# ----------------------------------------------------------------------
# The canonical convention
# ----------------------------------------------------------------------
SHARPE_CONVENTION_ID = "arithmetic_annualized_rf0"
SHARPE_CONVENTION_FORMULA = "mean(r) * 252 / (std(r, ddof=1) * sqrt(252))"
SHARPE_CONVENTION_RF_ANNUAL = 0.0
SHARPE_PERIODS_PER_YEAR = 252

# ----------------------------------------------------------------------
# The backtest-baseline scale (backtest research metrics only)
# ----------------------------------------------------------------------
BACKTEST_SHARPE_SCALE_ID = "cagr_annualized_rf2"
BACKTEST_SHARPE_SCALE_FORMULA = (
    "((1+r).prod() ** (252/n) - 1 - 0.02) / (std(r, ddof=1) * sqrt(252))"
)
BACKTEST_SHARPE_RF_ANNUAL = 0.02


def _clean(returns) -> np.ndarray:
    """Return *returns* as a flat float array with missing values removed."""
    arr = np.asarray(returns, dtype=float).ravel()
    if arr.size == 0:
        return arr
    return arr[np.isfinite(arr)]


def sharpe_ratio(
    returns,
    rf_annual: float = SHARPE_CONVENTION_RF_ANNUAL,
    periods_per_year: int = SHARPE_PERIODS_PER_YEAR,
) -> float:
    """Canonical annualised Sharpe ratio of a return series.

    ``mean(r) * periods_per_year / (std(r, ddof=1) * sqrt(periods_per_year))``,
    minus the annualised risk-free rate. With the default ``rf_annual=0.0``
    this is exactly the formula of the live ``low_rolling_sharpe`` drift flag
    and of every rolling Sharpe quoted in the validation artifacts.

    Returns 0.0 for a series that is too short or has no dispersion, so the
    function is total: it never raises on degenerate input.
    """
    arr = _clean(returns)
    if arr.size < 2:
        return 0.0
    vol = float(np.std(arr, ddof=1)) * math.sqrt(periods_per_year)
    if vol <= 0.0 or not math.isfinite(vol):
        return 0.0
    ann_excess = float(np.mean(arr)) * periods_per_year - rf_annual
    value = ann_excess / vol
    if not math.isfinite(value):
        return 0.0
    return float(value)


def backtest_sharpe_ratio(
    returns,
    rf_annual: float = BACKTEST_SHARPE_RF_ANNUAL,
    periods_per_year: int = SHARPE_PERIODS_PER_YEAR,
) -> float:
    """Sharpe ratio on the backtest-baseline scale (CAGR-based).

    ``(CAGR - rf) / annualised volatility``. Kept because the recorded
    backtest baseline (Sharpe 1.4178) and every published backtest research
    artifact are expressed on this scale; changing it would silently
    invalidate those artifacts. Do not use it in a promotion gate, in the
    drift flag or in the PSR -- use :func:`sharpe_ratio` there.
    """
    arr = _clean(returns)
    if arr.size < 2:
        return 0.0
    growth = float(np.prod(1.0 + arr))
    if growth <= 0.0 or not math.isfinite(growth):
        return 0.0
    cagr = growth ** (periods_per_year / arr.size) - 1.0
    vol = float(np.std(arr, ddof=1)) * math.sqrt(periods_per_year)
    if vol <= 0.0 or not math.isfinite(vol):
        return 0.0
    value = (cagr - rf_annual) / vol
    if not math.isfinite(value):
        return 0.0
    return float(value)
