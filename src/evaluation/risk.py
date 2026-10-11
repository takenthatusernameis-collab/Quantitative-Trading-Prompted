"""Risk management overlays: volatility targeting and drawdown control."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from src.backtest.engine import compute_metrics, get_cost_params, get_risk_free_rate


def volatility_target_overlay(
    returns: pd.Series,
    weights: pd.DataFrame,
    target_vol: float = 0.15,
    vol_lookback: int = 63,
    commission_bps: float = 1.0,
    slippage_bps: float = 2.0,
    rf_annual: float = 0.02,
) -> tuple[pd.Series, dict]:
    """Apply volatility targeting: scale gross exposure to hit target annualized vol.

    Uses rolling realized vol over `vol_lookback` days.  If realized vol is zero
    or NaN, exposure is set to zero (no positions).
    """
    daily_ret = returns.copy()
    port_ret = (weights * daily_ret).sum(axis=1)
    realized_vol = port_ret.rolling(vol_lookback).std() * np.sqrt(252)
    realized_vol = realized_vol.replace(0, np.nan)

    scale = target_vol / realized_vol
    scale = scale.clip(upper=1.0).fillna(0.0)

    scaled_weights = weights.mul(scale, axis=0)

    weight_changes = scaled_weights.diff().abs().sum(axis=1)
    cost_per_trade = commission_bps / 10000.0 + slippage_bps / 10000.0
    costs = weight_changes * cost_per_trade

    net_ret = (scaled_weights * daily_ret).sum(axis=1) - costs
    metrics = compute_metrics(net_ret, scaled_weights, commission_bps / 10000.0, slippage_bps / 10000.0, rf_annual)
    return net_ret, metrics


def drawdown_control_overlay(
    returns: pd.Series,
    weights: pd.DataFrame,
    dd_threshold: float = 0.15,
    reduction_factor: float = 0.5,
    commission_bps: float = 1.0,
    slippage_bps: float = 2.0,
    rf_annual: float = 0.02,
) -> tuple[pd.Series, dict]:
    """Reduce exposure when drawdown exceeds threshold.

    When the cumulative drawdown exceeds `dd_threshold`, gross exposure is
    scaled by `reduction_factor` until the drawdown recovers.
    """
    daily_ret = returns.copy()
    port_ret = (weights * daily_ret).sum(axis=1)
    cum = (1 + port_ret).cumprod()
    running_max = cum.expanding().max()
    drawdown = (cum / running_max) - 1

    in_drawdown = drawdown < -dd_threshold
    scale = pd.Series(1.0, index=weights.index)
    scale[in_drawdown] = reduction_factor

    scaled_weights = weights.mul(scale, axis=0)

    weight_changes = scaled_weights.diff().abs().sum(axis=1)
    cost_per_trade = commission_bps / 10000.0 + slippage_bps / 10000.0
    costs = weight_changes * cost_per_trade

    net_ret = (scaled_weights * daily_ret).sum(axis=1) - costs
    metrics = compute_metrics(net_ret, scaled_weights, commission_bps / 10000.0, slippage_bps / 10000.0, rf_annual)
    return net_ret, metrics


def combined_risk_overlay(
    returns: pd.Series,
    weights: pd.DataFrame,
    target_vol: float = 0.15,
    vol_lookback: int = 63,
    dd_threshold: float = 0.15,
    reduction_factor: float = 0.5,
    commission_bps: float = 1.0,
    slippage_bps: float = 2.0,
    rf_annual: float = 0.02,
) -> tuple[pd.Series, dict]:
    """Apply combined risk overlay: volatility targeting first, then drawdown control.

    1. Scale weights to target annualized volatility (capped at 1.0x gross exposure)
    2. When drawdown exceeds threshold, further reduce exposure by reduction_factor

    This is an additive combination: vol targeting scales the weights, then DD
    control further reduces them when drawdown exceeds threshold.
    """
    daily_ret = returns.copy()

    # Step 1: Volatility targeting
    port_ret = (weights * daily_ret).sum(axis=1)
    realized_vol = port_ret.rolling(vol_lookback).std() * np.sqrt(252)
    realized_vol = realized_vol.replace(0, np.nan)

    vol_scale = target_vol / realized_vol
    vol_scale = vol_scale.clip(upper=1.0).fillna(0.0)

    vol_targeted_weights = weights.mul(vol_scale, axis=0)

    # Step 2: Drawdown control on vol-targeted portfolio
    vol_port_ret = (vol_targeted_weights * daily_ret).sum(axis=1)
    cum = (1 + vol_port_ret).cumprod()
    running_max = cum.expanding().max()
    drawdown = (cum / running_max) - 1

    in_drawdown = drawdown < -dd_threshold
    dd_scale = pd.Series(1.0, index=weights.index)
    dd_scale[in_drawdown] = reduction_factor

    # Combined scale: vol targeting first, then DD control
    combined_scale = vol_scale * dd_scale
    combined_weights = weights.mul(combined_scale, axis=0)

    # Costs on combined weights
    weight_changes = combined_weights.diff().abs().sum(axis=1)
    cost_per_trade = commission_bps / 10000.0 + slippage_bps / 10000.0
    costs = weight_changes * cost_per_trade

    net_ret = (combined_weights * daily_ret).sum(axis=1) - costs
    metrics = compute_metrics(net_ret, combined_weights, commission_bps / 10000.0, slippage_bps / 10000.0, rf_annual)
    return net_ret, metrics


def run_risk_overlays(
    returns: pd.Series,
    weights: pd.DataFrame,
    vol_targets: Sequence[float] = (0.10, 0.15, 0.20),
    dd_thresholds: Sequence[float] = (0.15, 0.20),
) -> dict:
    """Run all risk overlay combinations and return results keyed by name."""
    commission_bps, slippage_bps = get_cost_params()
    rf_annual = get_risk_free_rate()

    results = {}

    for tv in vol_targets:
        net_ret, metrics = volatility_target_overlay(
            returns, weights, target_vol=tv,
            commission_bps=commission_bps, slippage_bps=slippage_bps, rf_annual=rf_annual,
        )
        results[f"vol_target_{tv}"] = {"net_ret": net_ret, "metrics": metrics}

    for dd in dd_thresholds:
        net_ret, metrics = drawdown_control_overlay(
            returns, weights, dd_threshold=dd,
            commission_bps=commission_bps, slippage_bps=slippage_bps, rf_annual=rf_annual,
        )
        results[f"dd_control_{dd}"] = {"net_ret": net_ret, "metrics": metrics}

    return results


def run_combined_risk_overlays(
    returns: pd.Series,
    weights: pd.DataFrame,
    vol_targets: Sequence[float] = (0.10, 0.15),
    dd_thresholds: Sequence[float] = (0.15, 0.20),
) -> dict:
    """Run combined risk overlay configurations and return results keyed by name.

    Tests all combinations of vol_targets x dd_thresholds.
    """
    commission_bps, slippage_bps = get_cost_params()
    rf_annual = get_risk_free_rate()

    results = {}

    for tv in vol_targets:
        for dd in dd_thresholds:
            net_ret, metrics = combined_risk_overlay(
                returns, weights,
                target_vol=tv,
                dd_threshold=dd,
                commission_bps=commission_bps,
                slippage_bps=slippage_bps,
                rf_annual=rf_annual,
            )
            results[f"combined_vol_{tv}_dd_{dd}"] = {"net_ret": net_ret, "metrics": metrics}

    return results


def format_risk_summary(results: dict, baseline_metrics: dict) -> str:
    """Format risk overlay results as markdown."""
    lines = ["## Risk Overlay Results", ""]
    lines.append("| Overlay | Sharpe | Ann. Return | Max DD | Sortino | Profit Factor | Trades |")
    lines.append("|---------|--------|-------------|--------|---------|---------------|--------|")

    # Baseline
    lines.append(
        f"| **Baseline** | {baseline_metrics.get('sharpe_ratio', 0):.4f} | "
        f"{baseline_metrics.get('annualized_return', 0):.4f} | "
        f"{baseline_metrics.get('max_drawdown', 0):.4f} | "
        f"{baseline_metrics.get('sortino_ratio', 0):.4f} | "
        f"{baseline_metrics.get('profit_factor', 0):.2f} | "
        f"{baseline_metrics.get('trade_count', 0)} |"
    )

    for name, data in results.items():
        m = data["metrics"]
        pf = m.get("profit_factor", 0)
        if isinstance(pf, str) or not np.isfinite(pf):
            pf_str = str(pf)
        else:
            pf_str = f"{pf:.2f}"
        lines.append(
            f"| {name} | {m.get('sharpe_ratio', 0):.4f} | "
            f"{m.get('annualized_return', 0):.4f} | "
            f"{m.get('max_drawdown', 0):.4f} | "
            f"{m.get('sortino_ratio', 0):.4f} | "
            f"{pf_str} | "
            f"{m.get('trade_count', 0)} |"
        )

    return "\n".join(lines)


def format_combined_risk_summary(results: dict, baseline_metrics: dict, lookback: int) -> str:
    """Format combined risk overlay results as markdown."""
    lines = [f"## Combined Risk Overlay Results (Lookback={lookback})", ""]
    lines.append("| Overlay | Sharpe | Ann. Return | Max DD | Sortino | Profit Factor | Trades | DD < -30%? |")
    lines.append("|---------|--------|-------------|--------|---------|---------------|--------|------------|")

    # Baseline
    bl_sharpe = baseline_metrics.get('sharpe_ratio', 0)
    bl_dd = baseline_metrics.get('max_drawdown', 0)
    lines.append(
        f"| **Baseline** | {bl_sharpe:.4f} | "
        f"{baseline_metrics.get('annualized_return', 0):.4f} | "
        f"{bl_dd:.4f} | "
        f"{baseline_metrics.get('sortino_ratio', 0):.4f} | "
        f"{baseline_metrics.get('profit_factor', 0):.2f} | "
        f"{baseline_metrics.get('trade_count', 0)} | "
        f"{'Yes' if bl_dd > -0.30 else 'No'} |"
    )

    for name, data in results.items():
        m = data["metrics"]
        pf = m.get("profit_factor", 0)
        if isinstance(pf, str) or not np.isfinite(pf):
            pf_str = str(pf)
        else:
            pf_str = f"{pf:.2f}"
        dd = m.get('max_drawdown', 0)
        lines.append(
            f"| {name} | {m.get('sharpe_ratio', 0):.4f} | "
            f"{m.get('annualized_return', 0):.4f} | "
            f"{dd:.4f} | "
            f"{m.get('sortino_ratio', 0):.4f} | "
            f"{pf_str} | "
            f"{m.get('trade_count', 0)} | "
            f"{'Yes' if dd > -0.30 else 'No'} |"
        )

    return "\n".join(lines)