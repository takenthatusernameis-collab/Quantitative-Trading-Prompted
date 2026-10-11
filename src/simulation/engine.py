"""Simulation engine for paper-trading preparation.

Provides deterministic, point-in-time simulation of the validated TSMOM
+ risk-overlay + regime-filter candidate strategy. Designed to reproduce
backtest results exactly while adding trade logs, positions, and risk metrics
suitable for prospective paper-trading monitoring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import yaml

from src.backtest.engine import compute_metrics, get_cost_params, get_risk_free_rate
from src.data.yfinance_fetcher import fetch_universe
from src.features.momentum import build_weights


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def load_settings() -> dict:
    path = _project_root() / "config" / "settings.yaml"
    with open(path, "r") as fh:
        return yaml.safe_load(fh) or {}


@dataclass
class SignalConfig:
    type: str = "tsmomentum"
    lookback: int = 226
    skip: int = 21
    top_fraction: float = 0.5
    rebalance_freq: str = "monthly"


@dataclass
class RiskOverlayConfig:
    vol_target: float = 0.10
    vol_lookback: int = 63
    max_leverage: float = 1.0
    dd_control_threshold: float = 0.15
    dd_control_reduction: float = 0.5


@dataclass
class RegimeFilterConfig:
    type: str = "spy_sma"
    window: int = 200
    exposure_below: float = 0.0
    exposure_above: float = 1.0


@dataclass
class CostModelConfig:
    commission_bps: float = 1.0
    slippage_bps: float = 2.0
    total_round_trip_bps: float = 3.0


@dataclass
class ExecutionConfig:
    signal_lag_days: int = 1
    price_field: str = "Open"
    timezone: str = "UTC"


@dataclass
class SimulationConfig:
    candidate_id: str = "tsmomentum_spytrend_001"
    universe: list[str] = field(default_factory=lambda: ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"])
    signal: SignalConfig = field(default_factory=SignalConfig)
    risk_overlay: RiskOverlayConfig = field(default_factory=RiskOverlayConfig)
    regime_filter: RegimeFilterConfig = field(default_factory=RegimeFilterConfig)
    cost_model: CostModelConfig = field(default_factory=CostModelConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> SimulationConfig:
        with open(path, "r") as fh:
            data = yaml.safe_load(fh) or {}
        return cls(
            candidate_id=data.get("candidate_id", "tsmomentum_spytrend_001"),
            universe=data.get("universe", ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"]),
            signal=SignalConfig(**data.get("signal", {})),
            risk_overlay=RiskOverlayConfig(**data.get("risk_overlay", {})),
            regime_filter=RegimeFilterConfig(**data.get("regime_filter", {})),
            cost_model=CostModelConfig(**data.get("cost_model", {})),
            execution=ExecutionConfig(**data.get("execution", {})),
        )

    def to_yaml(self, path: str | Path) -> None:
        data = {
            "candidate_id": self.candidate_id,
            "universe": self.universe,
            "signal": {
                "type": self.signal.type,
                "lookback": self.signal.lookback,
                "skip": self.signal.skip,
                "top_fraction": self.signal.top_fraction,
                "rebalance_freq": self.signal.rebalance_freq,
            },
            "risk_overlay": {
                "vol_target": self.risk_overlay.vol_target,
                "vol_lookback": self.risk_overlay.vol_lookback,
                "max_leverage": self.risk_overlay.max_leverage,
                "dd_control": {
                    "threshold": self.risk_overlay.dd_control_threshold,
                    "reduction": self.risk_overlay.dd_control_reduction,
                },
            },
            "regime_filter": {
                "type": self.regime_filter.type,
                "window": self.regime_filter.window,
                "exposure_below": self.regime_filter.exposure_below,
                "exposure_above": self.regime_filter.exposure_above,
            },
            "cost_model": {
                "commission_bps": self.cost_model.commission_bps,
                "slippage_bps": self.cost_model.slippage_bps,
                "total_round_trip_bps": self.cost_model.total_round_trip_bps,
            },
            "execution": {
                "signal_lag_days": self.execution.signal_lag_days,
                "price_field": self.execution.price_field,
                "timezone": self.execution.timezone,
            },
        }
        with open(path, "w") as fh:
            yaml.safe_dump(data, fh, sort_keys=False)


@dataclass
class SimulationResult:
    config: SimulationConfig
    start_date: str
    end_date: str
    daily_returns: pd.Series
    daily_positions: pd.DataFrame
    daily_weights: pd.DataFrame
    turnover: pd.Series
    costs: pd.Series
    trade_log: pd.DataFrame
    risk_metrics: pd.DataFrame
    rebalancing_events: pd.DataFrame
    metrics: dict

    def to_parquet(self, base_path: str | Path) -> None:
        base = Path(base_path)
        base.parent.mkdir(parents=True, exist_ok=True)
        self.daily_returns.to_frame("net_return").to_parquet(base.with_suffix(".returns.parquet"))
        self.daily_positions.to_parquet(base.with_suffix(".positions.parquet"))
        self.daily_weights.to_parquet(base.with_suffix(".weights.parquet"))
        self.trade_log.to_parquet(base.with_suffix(".trades.parquet"))
        self.risk_metrics.to_parquet(base.with_suffix(".risk.parquet"))
        self.rebalancing_events.to_parquet(base.with_suffix(".rebalancing.parquet"))

    @classmethod
    def from_parquet(cls, base_path: str | Path, config: SimulationConfig) -> SimulationResult:
        base = Path(base_path)
        return cls(
            config=config,
            start_date="",
            end_date="",
            daily_returns=pd.read_parquet(base.with_suffix(".returns.parquet"))["net_return"],
            daily_positions=pd.read_parquet(base.with_suffix(".positions.parquet")),
            daily_weights=pd.read_parquet(base.with_suffix(".weights.parquet")),
            turnover=pd.Series(dtype=float),
            costs=pd.Series(dtype=float),
            trade_log=pd.read_parquet(base.with_suffix(".trades.parquet")),
            risk_metrics=pd.read_parquet(base.with_suffix(".risk.parquet")),
            rebalancing_events=pd.read_parquet(base.with_suffix(".rebalancing.parquet")),
            metrics={},
        )


def _utc(ts) -> pd.Timestamp:
    return pd.Timestamp(ts, tz="UTC")


def _load_close(symbols: list[str], start_date: str, end_date: str) -> pd.DataFrame:
    """Return a clean Close-price DataFrame (UTC) for the given symbols."""
    data = fetch_universe(symbols, start_date, end_date, force=False)
    if data.empty:
        raise RuntimeError(f"No data fetched for {symbols}")
    close = data.xs("Close", level=0, axis=1)
    close = close.ffill().dropna(how="all")
    return close


def _load_open(symbols: list[str], start_date: str, end_date: str) -> pd.DataFrame:
    """Return a clean Open-price DataFrame (UTC) for the given symbols."""
    data = fetch_universe(symbols, start_date, end_date, force=False)
    if data.empty:
        raise RuntimeError(f"No data fetched for {symbols}")
    open_prices = data.xs("Open", level=0, axis=1)
    open_prices = open_prices.ffill().dropna(how="all")
    return open_prices


def _compute_regime_exposure(
    close: pd.DataFrame,
    regime_filter: RegimeFilterConfig,
) -> pd.Series:
    """Compute regime exposure factor (0.0 or 1.0 for SPY trend filter)."""
    spy = close["SPY"]
    if regime_filter.type == "spy_sma":
        sma = spy.rolling(regime_filter.window).mean()
        exposure = pd.Series(regime_filter.exposure_above, index=close.index)
        exposure[spy < sma] = regime_filter.exposure_below
        exposure[spy.isna() | sma.isna()] = regime_filter.exposure_below
        return exposure
    else:
        return pd.Series(1.0, index=close.index)


def _apply_combined_overlay(
    daily_ret: pd.DataFrame,
    base_weights: pd.DataFrame,
    exposure_factor: pd.Series,
    vol_target: float,
    vol_lookback: int,
    dd_threshold: float,
    dd_reduction: float,
    commission_bps: float,
    slippage_bps: float,
    rf_annual: float,
) -> tuple[pd.DataFrame, pd.Series, dict, pd.Series, pd.Series]:
    """Apply combined volatility targeting + drawdown control overlay.

    Returns (combined_weights, net_returns, metrics, weight_changes, costs)
    """
    weights = base_weights.copy()
    ef = exposure_factor.reindex(weights.index).fillna(0.0)
    weights = weights.mul(ef, axis=0)

    # Step 1: Volatility targeting
    port_ret = (weights * daily_ret).sum(axis=1)
    realized_vol = port_ret.rolling(vol_lookback).std() * np.sqrt(252)
    realized_vol = realized_vol.replace(0, np.nan)
    vol_scale = (vol_target / realized_vol).clip(upper=1.0).fillna(0.0)
    vol_targeted_weights = weights.mul(vol_scale, axis=0)

    # Step 2: Drawdown control on vol-targeted portfolio
    vol_port_ret = (vol_targeted_weights * daily_ret).sum(axis=1)
    cum = (1 + vol_port_ret).cumprod()
    running_max = cum.expanding().max()
    drawdown = (cum / running_max) - 1

    in_drawdown = drawdown < -dd_threshold
    dd_scale = pd.Series(1.0, index=weights.index)
    dd_scale[in_drawdown] = dd_reduction

    combined_scale = vol_scale * dd_scale
    combined_weights = weights.mul(combined_scale, axis=0)

    # Transaction costs (correct 3 bps round-trip model)
    weight_changes = combined_weights.diff().abs().sum(axis=1)
    cost_per_trade = commission_bps + slippage_bps
    costs = weight_changes * cost_per_trade

    net_ret = (combined_weights * daily_ret).sum(axis=1) - costs
    metrics = compute_metrics(
        net_ret, combined_weights, commission_bps, slippage_bps, rf_annual,
    )

    return combined_weights, net_ret, metrics, weight_changes, costs


def _build_trade_log(
    combined_weights: pd.DataFrame,
    daily_ret: pd.DataFrame,
    weight_changes: pd.Series,
    costs: pd.Series,
    price_field: str = "Close",
) -> pd.DataFrame:
    """Build a trade log from weight changes."""
    trades = []
    for i, date in enumerate(combined_weights.index):
        if i == 0:
            prev_weights = pd.Series(0.0, index=combined_weights.columns)
        else:
            prev_weights = combined_weights.iloc[i - 1]

        curr_weights = combined_weights.iloc[i]
        diff = curr_weights - prev_weights
        active = diff[diff.abs() > 1e-10]

        for symbol, weight_change in active.items():
            if weight_change == 0:
                continue
            side = "BUY" if weight_change > 0 else "SELL"
            # Approximate quantity based on weight change and portfolio value
            # For simulation, we track notional weight change
            price_val = 1.0  # normalized; real implementation would use actual prices
            trades.append({
                "date": date,
                "symbol": symbol,
                "side": side,
                "weight_change": weight_change,
                "price": price_val,
                "cost": costs.loc[date] if date in costs.index else 0.0,
            })

    if trades:
        return pd.DataFrame(trades).set_index("date")
    return pd.DataFrame(columns=["symbol", "side", "weight_change", "price", "cost"])


def _build_risk_metrics(
    net_ret: pd.Series,
    combined_weights: pd.DataFrame,
    daily_ret: pd.DataFrame,
) -> pd.DataFrame:
    """Build daily risk metrics DataFrame."""
    port_ret = (combined_weights * daily_ret).sum(axis=1)
    cum = (1 + net_ret).cumprod()
    running_max = cum.expanding().max()
    drawdown = (cum / running_max) - 1

    rolling_vol = net_ret.rolling(63).std() * np.sqrt(252)
    exposure = combined_weights.abs().sum(axis=1)

    return pd.DataFrame({
        "net_return": net_ret,
        "portfolio_return": port_ret,
        "cumulative": cum,
        "drawdown": drawdown,
        "rolling_vol_63d": rolling_vol,
        "gross_exposure": exposure,
        "net_exposure": combined_weights.sum(axis=1),
        "n_positions": (combined_weights > 0).sum(axis=1),
    }, index=net_ret.index)


def _build_rebalancing_events(
    combined_weights: pd.DataFrame,
    weight_changes: pd.Series,
) -> pd.DataFrame:
    """Identify rebalancing events (days with weight changes)."""
    rebal_days = weight_changes[weight_changes > 1e-10]
    events = []
    for date, turnover in rebal_days.items():
        events.append({
            "date": date,
            "turnover": turnover,
            "n_changes": int((combined_weights.loc[date].diff().abs() > 1e-10).sum()),
        })
    if events:
        return pd.DataFrame(events).set_index("date")
    return pd.DataFrame(columns=["turnover", "n_changes"])


def run_simulation(
    config: SimulationConfig,
    start_date: str,
    end_date: str,
) -> SimulationResult:
    """Run the full simulation pipeline.

    Args:
        config: Simulation configuration
        start_date: Inclusive start date (YYYY-MM-DD)
        end_date: Inclusive end date (YYYY-MM-DD)

    Returns:
        SimulationResult with all time series and metrics
    """
    # Load data
    close = _load_close(config.universe, start_date, end_date)
    open_prices = _load_open(config.universe, start_date, end_date)

    # Compute base momentum weights (point-in-time: signal at t-1, execute at t)
    base_weights = build_weights(
        close,
        lookback=config.signal.lookback,
        skip=config.signal.skip,
        top_fraction=config.signal.top_fraction,
    )

    # Align
    common = close.index.intersection(base_weights.index)
    close = close.loc[common]
    open_prices = open_prices.loc[common]
    base_weights = base_weights.loc[common]

    # Daily returns (using close-to-close for consistency with backtest)
    daily_ret = close.pct_change().fillna(0.0)

    # Compute regime exposure factor
    exposure_factor = _compute_regime_exposure(close, config.regime_filter)

    # Get cost params
    commission_bps = config.cost_model.commission_bps / 10000.0
    slippage_bps = config.cost_model.slippage_bps / 10000.0
    rf_annual = get_risk_free_rate()

    # Apply combined overlay
    combined_weights, net_ret, metrics, weight_changes, costs = _apply_combined_overlay(
        daily_ret=daily_ret,
        base_weights=base_weights,
        exposure_factor=exposure_factor,
        vol_target=config.risk_overlay.vol_target,
        vol_lookback=config.risk_overlay.vol_lookback,
        dd_threshold=config.risk_overlay.dd_control_threshold,
        dd_reduction=config.risk_overlay.dd_control_reduction,
        commission_bps=commission_bps,
        slippage_bps=slippage_bps,
        rf_annual=rf_annual,
    )

    # Build trade log
    trade_log = _build_trade_log(
        combined_weights, daily_ret, weight_changes, costs,
        price_field=config.execution.price_field,
    )

    # Build risk metrics
    risk_metrics = _build_risk_metrics(net_ret, combined_weights, daily_ret)

    # Build rebalancing events
    rebalancing_events = _build_rebalancing_events(combined_weights, weight_changes)

    # Positions (same as weights for this strategy)
    daily_positions = combined_weights.copy()

    return SimulationResult(
        config=config,
        start_date=start_date,
        end_date=end_date,
        daily_returns=net_ret,
        daily_positions=daily_positions,
        daily_weights=combined_weights,
        turnover=weight_changes,
        costs=costs,
        trade_log=trade_log,
        risk_metrics=risk_metrics,
        rebalancing_events=rebalancing_events,
        metrics=metrics,
    )


def run_simulation_fixed_params(
    symbols: list[str],
    start_date: str,
    end_date: str,
    lookback: int = 226,
    skip: int = 21,
    top_fraction: float = 0.5,
    vol_target: float = 0.10,
    vol_lookback: int = 63,
    dd_threshold: float = 0.15,
    dd_reduction: float = 0.5,
    spy_sma_window: int = 200,
    commission_bps: float = 1.0,
    slippage_bps: float = 2.0,
) -> tuple[pd.Series, pd.DataFrame, dict]:
    """Run simulation with fixed parameters (for walk-forward compatibility).

    Returns (net_returns, combined_weights, metrics).
    """
    config = SimulationConfig(
        universe=symbols,
        signal=SignalConfig(lookback=lookback, skip=skip, top_fraction=top_fraction),
        risk_overlay=RiskOverlayConfig(
            vol_target=vol_target,
            vol_lookback=vol_lookback,
            dd_control_threshold=dd_threshold,
            dd_control_reduction=dd_reduction,
        ),
        regime_filter=RegimeFilterConfig(window=spy_sma_window),
        cost_model=CostModelConfig(commission_bps=commission_bps, slippage_bps=slippage_bps),
    )
    result = run_simulation(config, start_date, end_date)
    return result.daily_returns, result.daily_weights, result.metrics


if __name__ == "__main__":
    # Quick test
    config = SimulationConfig()
    result = run_simulation(config, "2018-01-01", "2026-10-09")
    print(f"Test Sharpe: {result.metrics['sharpe_ratio']:.4f}")
    print(f"Test Max DD: {result.metrics['max_drawdown']:.4f}")
    print(f"Trades: {result.metrics['trade_count']}")
    print(f"Ann Return: {result.metrics['annualized_return']:.4f}")