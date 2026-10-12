"""Simulation engine for paper-trading preparation.

Deterministic, point-in-time simulation of the validated TSMOM +
combined-risk-overlay + SPY-trend-filter candidate. The engine reproduces
the Cycle 5/6 backtest logic exactly (close-to-close execution, 1-day
signal lag, volatility targeting + drawdown control, SPY SMA regime
filter, 3 bps round-trip cost model) while adding trade logs, position
series, rebalancing events, and risk metrics suitable for prospective
paper-trading monitoring.

Two overlay-state conventions are supported so the engine can replicate
both validated code paths:

* ``overlay_warmup="slice"``: overlay state (rolling realized vol,
  cumulative drawdown) initializes at ``start_date``. This replicates
  the Cycle 5 test-period evaluation exactly.
* ``overlay_warmup="full"``: overlay state initializes at
  ``history_start`` and results are sliced to ``[start_date, end_date]``.
  This replicates the Cycle 6 walk-forward fold evaluation exactly.

The engine is fully deterministic: no random number generator is used.
The ``seed`` field is accepted for API compatibility only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from src.backtest.engine import compute_metrics, get_risk_free_rate
from src.data.yfinance_fetcher import fetch_universe
from src.features.momentum import (
    build_weights,
    compute_momentum,
    select_top_decile,
)


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


@dataclass
class SimulationConfig:
    """Frozen configuration for one candidate simulation.

    All parameters mirror the validated candidate configuration from
    Cycles 4-6 (see research/experiments/tsmomentum_regime_filter_001.md
    and tsmomentum_regime_filter_wf_001.md).
    """

    candidate_id: str = "tsmomentum_spytrend_001"
    universe: list[str] = field(
        default_factory=lambda: ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"]
    )

    signal_type: str = "tsmomentum"
    lookback: int = 226
    skip: int = 21
    top_fraction: float = 0.5

    vol_target: float = 0.10
    vol_lookback: int = 63
    max_leverage: float = 1.0
    dd_threshold: float = 0.15
    dd_reduction: float = 0.5

    regime_type: str = "spy_sma"
    regime_window: int = 200
    exposure_below: float = 0.0
    exposure_above: float = 1.0

    commission_bps: float = 1.0
    slippage_bps: float = 2.0

    signal_lag_days: int = 1
    price_field: str = "Close"
    timezone: str = "UTC"
    rebalance_freq: str = "daily"

    history_start: str = "1993-01-01"
    overlay_warmup: str = "slice"
    seed: int | None = None

    @classmethod
    def from_yaml(cls, path: str | Path) -> SimulationConfig:
        """Load a SimulationConfig from a YAML file."""
        with open(path, "r") as fh:
            cfg = yaml.safe_load(fh) or {}
        signal = cfg.get("signal", {})
        overlay = cfg.get("risk_overlay", {})
        dd_control = overlay.get("dd_control", {})
        regime = cfg.get("regime_filter", {})
        costs = cfg.get("cost_model", {})
        execution = cfg.get("execution", {})
        return cls(
            candidate_id=str(cfg.get("candidate_id", "tsmomentum_spytrend_001")),
            universe=[str(s) for s in cfg.get("universe", [])]
            or ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"],
            signal_type=str(signal.get("type", "tsmomentum")),
            lookback=int(signal.get("lookback", 226)),
            skip=int(signal.get("skip", 21)),
            top_fraction=float(signal.get("top_fraction", 0.5)),
            vol_target=float(overlay.get("vol_target", 0.10)),
            vol_lookback=int(overlay.get("vol_lookback", 63)),
            max_leverage=float(overlay.get("max_leverage", 1.0)),
            dd_threshold=float(dd_control.get("threshold", 0.15)),
            dd_reduction=float(dd_control.get("reduction", 0.5)),
            regime_type=str(regime.get("type", "spy_sma")),
            regime_window=int(regime.get("window", 200)),
            exposure_below=float(regime.get("exposure_below", 0.0)),
            exposure_above=float(regime.get("exposure_above", 1.0)),
            commission_bps=float(costs.get("commission_bps", 1.0)),
            slippage_bps=float(costs.get("slippage_bps", 2.0)),
            signal_lag_days=int(execution.get("signal_lag_days", 1)),
            price_field=str(execution.get("price_field", "Close")),
            timezone=str(execution.get("timezone", "UTC")),
            rebalance_freq=str(execution.get("rebalance_schedule", "daily")),
            history_start=str(cfg.get("history_start", "1993-01-01")),
            overlay_warmup=str(cfg.get("overlay_warmup", "slice")),
            seed=cfg.get("seed"),
        )


@dataclass
class SimulationResult:
    """Container for a completed simulation run."""

    config: SimulationConfig
    start_date: str
    end_date: str
    daily: pd.DataFrame
    weights: pd.DataFrame
    base_weights: pd.DataFrame
    trade_log: pd.DataFrame
    rebalance_events: pd.DataFrame
    metrics: dict
    risk_metrics: dict
    data_info: dict

    def summary(self) -> str:
        """Return a one-line human-readable summary of the run."""
        m = self.metrics
        return (
            f"{self.config.candidate_id} [{self.start_date}..{self.end_date}] "
            f"Sharpe={m.get('sharpe_ratio', float('nan')):.4f} "
            f"AnnRet={m.get('annualized_return', float('nan')):.4f} "
            f"MaxDD={m.get('max_drawdown', float('nan')):.4f} "
            f"Trades={m.get('trade_count', 0)}"
        )


def _load_market_data(
    symbols: list[str],
    history_start: str,
    end_date: str,
    data: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (close, open) price frames for the universe."""
    if data is None:
        data = fetch_universe(symbols, history_start, end_date, force=False)
    if data.empty:
        raise RuntimeError(f"No data fetched for {symbols}")
    close = data.xs("Close", level=0, axis=1).ffill().dropna(how="all")
    open_px = data.xs("Open", level=0, axis=1).ffill()
    return close, open_px


def _signal_weights(close: pd.DataFrame, config: SimulationConfig) -> pd.DataFrame:
    """Compute point-in-time strategy weights (signal on T-1 close)."""
    if config.signal_lag_days == 1:
        return build_weights(
            close,
            lookback=config.lookback,
            skip=config.skip,
            top_fraction=config.top_fraction,
        )
    momentum = compute_momentum(close, lookback=config.lookback, skip=config.skip)
    mask = select_top_decile(momentum, top_fraction=config.top_fraction)
    n_selected = mask.sum(axis=1).replace(0, np.nan)
    return mask.astype(float).div(n_selected, axis=0).fillna(0.0)


def _regime_exposure(close: pd.DataFrame, config: SimulationConfig) -> pd.Series:
    """Return the point-in-time regime exposure factor."""
    if config.regime_type != "spy_sma":
        raise ValueError(
            f"Unsupported regime filter type: {config.regime_type!r}"
        )
    spy = close["SPY"]
    sma = spy.rolling(config.regime_window).mean()
    exposure = pd.Series(config.exposure_above, index=close.index)
    exposure[spy < sma] = config.exposure_below
    exposure[spy.isna() | sma.isna()] = config.exposure_below
    return exposure


def _target_weights(
    weights: pd.DataFrame,
    asset_ret: pd.DataFrame,
    config: SimulationConfig,
) -> dict:
    """Apply volatility targeting + drawdown control + leverage cap."""
    port_ret = (weights * asset_ret).sum(axis=1)
    realized_vol = port_ret.rolling(config.vol_lookback).std() * np.sqrt(252)
    realized_vol = realized_vol.replace(0, np.nan)
    vol_scale = (config.vol_target / realized_vol).clip(upper=1.0).fillna(0.0)

    vol_targeted = weights.mul(vol_scale, axis=0)
    vol_port_ret = (vol_targeted * asset_ret).sum(axis=1)
    cum = (1 + vol_port_ret).cumprod()
    running_max = cum.expanding().max()
    drawdown = (cum / running_max) - 1.0
    in_drawdown = drawdown < -config.dd_threshold
    dd_scale = pd.Series(1.0, index=weights.index)
    dd_scale[in_drawdown] = config.dd_reduction

    combined = weights.mul(vol_scale * dd_scale, axis=0)

    gross = combined.abs().sum(axis=1)
    leverage_scale = (config.max_leverage / gross).clip(upper=1.0)
    combined = combined.mul(leverage_scale, axis=0)

    return {
        "combined_weights": combined,
        "vol_scale": vol_scale,
        "dd_scale": dd_scale,
        "overlay_drawdown": drawdown,
    }


def _apply_rebalance_schedule(
    combined: pd.DataFrame,
    config: SimulationConfig,
) -> pd.DataFrame:
    """Apply the rebalancing calendar to target weights."""
    if config.rebalance_freq == "M":
        is_month_end = combined.index.is_month_end
        return combined.where(
            pd.Series(is_month_end, index=combined.index), axis=0
        ).ffill().fillna(0.0)
    if config.rebalance_freq != "daily":
        raise ValueError(
            f"Unsupported rebalance_freq: {config.rebalance_freq!r}"
        )
    return combined


def _finalize(
    scheduled: pd.DataFrame,
    asset_ret: pd.DataFrame,
    config: SimulationConfig,
) -> dict:
    """Compute costs, gross/net returns from executed weights."""
    cost_per_unit = (config.commission_bps + config.slippage_bps) / 10000.0
    weight_changes = scheduled.diff().abs().sum(axis=1)
    costs = weight_changes * cost_per_unit
    gross_ret = (scheduled * asset_ret).sum(axis=1)
    net_ret = gross_ret - costs
    return {
        "weight_changes": weight_changes,
        "costs": costs,
        "gross_return": gross_ret,
        "net_return": net_ret,
        "cost_per_unit": cost_per_unit,
    }


def _build_trade_log(
    scheduled: pd.DataFrame,
    exec_price: pd.DataFrame,
    cost_per_unit: float,
) -> pd.DataFrame:
    """Build a long-format trade log from executed weight changes."""
    columns = [
        "trade_id",
        "date",
        "symbol",
        "side",
        "weight_before",
        "weight_after",
        "weight_change",
        "price",
        "cost",
    ]
    changes = scheduled.diff()
    stacked = changes.stack()
    nonzero = stacked[stacked.abs() > 0]
    if nonzero.empty:
        return pd.DataFrame(columns=columns)

    before = scheduled.shift(1).stack().reindex(nonzero.index)
    after = scheduled.stack().reindex(nonzero.index)
    prices = exec_price.stack().reindex(nonzero.index)

    trade_log = pd.DataFrame(
        {
            "weight_before": before.to_numpy(),
            "weight_after": after.to_numpy(),
            "weight_change": nonzero.to_numpy(),
            "price": prices.to_numpy(),
        },
        index=nonzero.index,
    )
    trade_log["side"] = np.where(
        trade_log["weight_change"] > 0, "buy", "sell"
    )
    trade_log["cost"] = trade_log["weight_change"].abs() * cost_per_unit
    trade_log = trade_log.reset_index()
    # Ensure index levels are named correctly
    trade_log.columns = ["date", "symbol"] + list(trade_log.columns[2:])
    trade_log.insert(0, "trade_id", np.arange(1, len(trade_log) + 1))
    return trade_log[columns]


def _build_rebalance_events(
    trade_log: pd.DataFrame,
    regime_exposure: pd.Series,
) -> pd.DataFrame:
    """Aggregate the trade log into per-date rebalancing events."""
    columns = [
        "date",
        "n_trades",
        "turnover",
        "cost",
        "cumulative_cost",
        "regime_exposure",
    ]
    if trade_log.empty:
        return pd.DataFrame(columns=columns)
    events = trade_log.groupby("date").agg(
        n_trades=("trade_id", "count"),
        turnover=("weight_change", lambda s: float(s.abs().sum())),
        cost=("cost", "sum"),
    )
    events["cumulative_cost"] = events["cost"].cumsum()
    events["regime_exposure"] = regime_exposure.reindex(events.index)
    return events.reset_index()[columns]


def _risk_metrics(
    net_ret: pd.Series,
    scheduled: pd.DataFrame,
    costs: pd.Series,
) -> dict:
    """Compute risk statistics for the simulation window."""
    clean = net_ret.dropna()
    if clean.empty:
        return {
            "n_days": 0,
            "ann_vol": 0.0,
            "var_95_daily": 0.0,
            "cvar_95_daily": 0.0,
            "avg_exposure": 0.0,
            "max_exposure": 0.0,
            "min_exposure": 0.0,
            "current_exposure": 0.0,
            "total_cost": 0.0,
            "avg_daily_cost": 0.0,
        }
    var_95 = float(np.percentile(clean, 5))
    tail = clean[clean <= -var_95]
    cvar_95 = float(-tail.mean()) if len(tail) > 0 else 0.0
    exposure = scheduled.abs().sum(axis=1)
    return {
        "n_days": len(clean),
        "ann_vol": float(clean.std() * np.sqrt(252)),
        "var_95_daily": float(-var_95),
        "cvar_95_daily": cvar_95,
        "avg_exposure": float(exposure.mean()),
        "max_exposure": float(exposure.max()),
        "min_exposure": float(exposure.min()),
        "current_exposure": float(exposure.iloc[-1]),
        "total_cost": float(costs.sum()),
        "avg_daily_cost": float(costs.mean()),
    }


def run_simulation(
    config: SimulationConfig,
    start_date: str,
    end_date: str,
    data: pd.DataFrame | None = None,
) -> SimulationResult:
    """Run a deterministic point-in-time simulation of the candidate.

    Parameters
    ----------
    config:
        Simulation configuration (see :class:`SimulationConfig`).
    start_date, end_date:
        Simulation window (YYYY-MM-DD). Signal data is always loaded
        from ``config.history_start`` so signals are point-in-time.
    data:
        Optional pre-fetched OHLCV frame (MultiIndex columns as returned
        by :func:`src.data.yfinance_fetcher.fetch_universe`). When
        omitted, data is loaded from the Yahoo Finance cache.

    Returns
    -------
    SimulationResult
        Daily series, weights, trade log, rebalancing events, metrics,
        and risk statistics for the simulation window.
    """
    symbols = list(config.universe)
    close, open_px = _load_market_data(
        symbols, config.history_start, end_date, data=data
    )
    base_weights = _signal_weights(close, config)
    common = close.index.intersection(base_weights.index)
    close = close.loc[common]
    open_px = open_px.loc[common]
    base_weights = base_weights.loc[common]

    if config.price_field == "Close":
        exec_price = close
        asset_ret = close.pct_change()
    elif config.price_field == "Open":
        exec_price = open_px
        asset_ret = (close / open_px) - 1.0
    else:
        raise ValueError(f"Unsupported price_field: {config.price_field!r}")

    regime = _regime_exposure(close, config)
    gated = base_weights.mul(regime.reindex(base_weights.index).fillna(0.0), axis=0)

    start_ts = pd.Timestamp(start_date, tz=config.timezone)
    end_ts = pd.Timestamp(end_date, tz=config.timezone)
    mask = (base_weights.index >= start_ts) & (base_weights.index <= end_ts)
    if not mask.any():
        raise ValueError(
            f"No simulation dates between {start_date} and {end_date}"
        )

    if config.overlay_warmup == "full":
        targets = _target_weights(gated, asset_ret, config)
        scheduled_full = _apply_rebalance_schedule(
            targets["combined_weights"], config
        )
        finalized = _finalize(scheduled_full, asset_ret, config)
        scheduled = scheduled_full.loc[mask]
        net_ret = finalized["net_return"].loc[mask]
        gross_ret = finalized["gross_return"].loc[mask]
        costs = finalized["costs"].loc[mask]
        weight_changes = finalized["weight_changes"].loc[mask]
        vol_scale = targets["vol_scale"].loc[mask]
        dd_scale = targets["dd_scale"].loc[mask]
        overlay_drawdown = targets["overlay_drawdown"].loc[mask]
    elif config.overlay_warmup == "slice":
        sim_ret = asset_ret.loc[mask]
        sim_gated = gated.loc[mask]
        targets = _target_weights(sim_gated, sim_ret, config)
        scheduled = _apply_rebalance_schedule(
            targets["combined_weights"], config
        )
        finalized = _finalize(scheduled, sim_ret, config)
        net_ret = finalized["net_return"]
        gross_ret = finalized["gross_return"]
        costs = finalized["costs"]
        weight_changes = finalized["weight_changes"]
        vol_scale = targets["vol_scale"]
        dd_scale = targets["dd_scale"]
        overlay_drawdown = targets["overlay_drawdown"]
    else:
        raise ValueError(
            f"Unsupported overlay_warmup: {config.overlay_warmup!r}"
        )

    cost_per_unit = finalized["cost_per_unit"]

    cum_net = (1 + net_ret).cumprod()
    net_drawdown = (cum_net / cum_net.expanding().max()) - 1.0

    daily = pd.DataFrame(index=scheduled.index)
    daily["net_return"] = net_ret
    daily["gross_return"] = gross_ret
    daily["cost"] = costs
    daily["turnover"] = weight_changes
    daily["exposure"] = scheduled.abs().sum(axis=1)
    daily["n_positions"] = (scheduled > 0).sum(axis=1)
    daily["regime_exposure"] = regime.reindex(scheduled.index)
    daily["vol_scale"] = vol_scale
    daily["dd_scale"] = dd_scale
    daily["overlay_drawdown"] = overlay_drawdown
    daily["drawdown"] = net_drawdown
    for symbol in symbols:
        daily[f"weight_{symbol}"] = scheduled[symbol].to_numpy()

    trade_log = _build_trade_log(scheduled, exec_price, cost_per_unit)
    rebalance_events = _build_rebalance_events(trade_log, regime)

    commission = config.commission_bps / 10000.0
    slippage = config.slippage_bps / 10000.0
    metrics = compute_metrics(
        net_ret, scheduled, commission, slippage, get_risk_free_rate()
    )
    risk = _risk_metrics(net_ret, scheduled, costs)

    data_info = {
        "source": "yahoo_finance",
        "cache_dir": str(_project_root() / "data" / "raw"),
        "history_start": config.history_start,
        "data_start": str(close.index.min()),
        "data_end": str(close.index.max()),
        "n_price_rows": len(close),
        "price_field": config.price_field,
        "cost_model_round_trip_bps": config.commission_bps + config.slippage_bps,
        "overlay_warmup": config.overlay_warmup,
        "rebalance_freq": config.rebalance_freq,
    }

    return SimulationResult(
        config=config,
        start_date=start_date,
        end_date=end_date,
        daily=daily,
        weights=scheduled,
        base_weights=base_weights.loc[scheduled.index],
        trade_log=trade_log,
        rebalance_events=rebalance_events,
        metrics=metrics,
        risk_metrics=risk,
        data_info=data_info,
    )
