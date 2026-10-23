"""Paper-trading (prospective) validation framework.

Runs the simulation daily with current market data, tracks positions,
returns, and risk metrics, monitors for signal/regime/risk drift, and
produces daily artifacts for review. This is NOT live trading - it is a
prospective simulation using each day's market data as it becomes
available without lookahead bias.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from src.evaluation.drift import (
    DEFAULT_MIN_PERIODS,
    DEFAULT_SHARPE_THRESHOLD,
    sharpe_persistence,
)
from src.evaluation.sharpe import sharpe_ratio
from src.evaluation.utils import compute_running_drawdown
from src.simulation.engine import (
    SimulationConfig,
    _project_root,
    run_simulation,
)


def _ensure_path(path: str | Path) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _project_root() / p
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


@dataclass
class PaperTradingConfig(SimulationConfig):
    """Configuration for paper-trading with operational parameters."""

    # Paper-trading specific parameters
    simulation_config_path: str = "config/simulation_candidate_001.yaml"
    notional_capital: float = 100000.0

    # Data refresh
    data_refresh_schedule: str = "daily"
    data_refresh_timezone: str = "America/New_York"
    data_refresh_market_close_hour: int = 16

    # Alert thresholds
    alert_regime_flip: bool = True
    alert_vol_scale_max: float = 2.0
    alert_dd_scale_min: float = 0.25
    alert_signal_turnover_pct: float = 0.5
    alert_max_drawdown_pct: float = 0.10

    # Output paths
    output_dir: str = "data/processed/paper_trading"
    report_path: str = "research/reports/paper_trading_rolling.md"
    state_path: str = "data/processed/paper_trading_state.yaml"

    # Go/no-go criteria
    go_no_go_min_days: int = 63
    go_no_go_target_sharpe: float = 0.9
    go_no_go_max_dd_threshold: float = 0.15

    @classmethod
    def from_paper_config_yaml(cls, path: str | Path) -> PaperTradingConfig:
        """Load PaperTradingConfig from paper trading YAML file."""
        with open(path, "r") as fh:
            cfg = yaml.safe_load(fh) or {}

        sim_cfg_path = cfg.get("simulation_config", "config/simulation_candidate_001.yaml")
        # Load base simulation config
        sim_base = SimulationConfig.from_yaml(sim_cfg_path)

        data_refresh = cfg.get("data_refresh", {})
        alert_thresholds = cfg.get("alert_thresholds", {})
        go_no_go = cfg.get("go_no_go", {})

        return cls(
            # Base sim config fields
            candidate_id=sim_base.candidate_id,
            universe=sim_base.universe,
            signal_type=sim_base.signal_type,
            lookback=sim_base.lookback,
            skip=sim_base.skip,
            top_fraction=sim_base.top_fraction,
            vol_target=sim_base.vol_target,
            vol_lookback=sim_base.vol_lookback,
            max_leverage=sim_base.max_leverage,
            dd_threshold=sim_base.dd_threshold,
            dd_reduction=sim_base.dd_reduction,
            lag_vol_estimate=sim_base.lag_vol_estimate,
            regime_type=sim_base.regime_type,
            regime_window=sim_base.regime_window,
            exposure_below=sim_base.exposure_below,
            exposure_above=sim_base.exposure_above,
            commission_bps=sim_base.commission_bps,
            slippage_bps=sim_base.slippage_bps,
            signal_lag_days=sim_base.signal_lag_days,
            price_field=sim_base.price_field,
            timezone=sim_base.timezone,
            rebalance_freq=sim_base.rebalance_freq,
            history_start=sim_base.history_start,
            overlay_warmup=sim_base.overlay_warmup,
            seed=sim_base.seed,
            # Paper trading specific
            simulation_config_path=str(sim_cfg_path),
            notional_capital=float(cfg.get("notional_capital", 100000.0)),
            data_refresh_schedule=str(data_refresh.get("schedule", "daily")),
            data_refresh_timezone=str(data_refresh.get("timezone", "America/New_York")),
            data_refresh_market_close_hour=int(
                data_refresh.get("market_close_hour", 16)
            ),
            alert_regime_flip=bool(alert_thresholds.get("regime_flip", True)),
            alert_vol_scale_max=float(alert_thresholds.get("vol_scale_max", 2.0)),
            alert_dd_scale_min=float(alert_thresholds.get("dd_scale_min", 0.25)),
            alert_signal_turnover_pct=float(
                alert_thresholds.get("signal_turnover_pct", 0.5)
            ),
            alert_max_drawdown_pct=float(alert_thresholds.get("max_drawdown_pct", 0.10)),
            output_dir=str(cfg.get("output_dir", "data/processed/paper_trading")),
            report_path=str(cfg.get("report_path", "research/reports/paper_trading_rolling.md")),
            state_path=str(cfg.get("state_path", "data/processed/paper_trading_state.yaml")),
            go_no_go_min_days=int(go_no_go.get("min_days", 63)),
            go_no_go_target_sharpe=float(go_no_go.get("target_sharpe", 0.9)),
            go_no_go_max_dd_threshold=float(go_no_go.get("go_no_go_max_dd_threshold", 0.15)) if "go_no_go_max_dd_threshold" in go_no_go else float(go_no_go.get("max_dd_threshold", 0.15)),
        )


@dataclass
class PaperTradingState:
    """Persistent state for paper-trading."""

    last_run_date: str | None = None
    current_positions: dict[str, float] = field(default_factory=dict)
    cumulative_returns: list[float] = field(default_factory=list)
    cumulative_pnl: list[float] = field(default_factory=list)
    cumulative_dates: list[str] = field(default_factory=list)
    peak_nav: float = 100000.0
    current_nav: float = 100000.0
    max_drawdown: float = 0.0
    drift_flags: dict[str, Any] = field(default_factory=dict)
    run_history: list[dict[str, Any]] = field(default_factory=list)
    previous_regime_exposure: float | None = None

    # Enhanced drift monitoring fields
    rolling_sharpe_63d: float = 0.0
    rolling_max_dd_63d: float = 0.0
    regime_persistence_days: int = 0
    vol_scale_min: float = 1.0
    vol_scale_max: float = 1.0
    dd_scale_min: float = 1.0
    dd_scale_max: float = 1.0
    turnover_median: float = 0.0
    turnover_p95: float = 0.0

    @classmethod
    def from_yaml(cls, path: str | Path) -> PaperTradingState:
        p = _ensure_path(path)
        if not p.exists():
            return cls()
        with open(p, "r") as fh:
            data = yaml.safe_load(fh) or {}
        return cls(
            last_run_date=data.get("last_run_date"),
            current_positions={str(k): float(v) for k, v in (data.get("current_positions") or {}).items()},
            cumulative_returns=[float(x) for x in (data.get("cumulative_returns") or [])],
            cumulative_pnl=[float(x) for x in (data.get("cumulative_pnl") or [])],
            cumulative_dates=[str(x) for x in (data.get("cumulative_dates") or [])],
            peak_nav=float(data.get("peak_nav", 100000.0)),
            current_nav=float(data.get("current_nav", 100000.0)),
            max_drawdown=float(data.get("max_drawdown", 0.0)),
            drift_flags=dict(data.get("drift_flags") or {}),
            run_history=[dict(x) for x in (data.get("run_history") or [])],
            previous_regime_exposure=data.get("previous_regime_exposure"),
            rolling_sharpe_63d=float(data.get("rolling_sharpe_63d", 0.0)),
            rolling_max_dd_63d=float(data.get("rolling_max_dd_63d", 0.0)),
            regime_persistence_days=int(data.get("regime_persistence_days", 0)),
            vol_scale_min=float(data.get("vol_scale_min", 1.0)),
            vol_scale_max=float(data.get("vol_scale_max", 1.0)),
            dd_scale_min=float(data.get("dd_scale_min", 1.0)),
            dd_scale_max=float(data.get("dd_scale_max", 1.0)),
            turnover_median=float(data.get("turnover_median", 0.0)),
            turnover_p95=float(data.get("turnover_p95", 0.0)),
        )

    def to_yaml(self, path: str | Path) -> None:
        p = _ensure_path(path)

        def convert(obj):
            if isinstance(obj, (np.integer, np.floating)):
                return obj.item()
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert(v) for v in obj]
            return obj

        payload = yaml.safe_dump(convert(asdict(self)), sort_keys=False)
        # Atomic write: build the new file next to the target, fsync it, then
        # os.replace() it into place. A crash, OOM, or disk-full during the
        # write therefore leaves the previous state file byte-for-byte
        # intact instead of truncating it (Cycle 999 contract: the single
        # state write must never corrupt the canonical paper-trading state).
        fd, tmp_path = tempfile.mkstemp(
            prefix=p.name + ".", suffix=".tmp", dir=str(p.parent)
        )
        try:
            with os.fdopen(fd, "w") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_path, p)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise


def run_daily_paper_update(
    config: PaperTradingConfig,
    state: PaperTradingState,
    market_data: pd.DataFrame | None = None,
) -> tuple[PaperTradingState, dict[str, Any]]:
    """
    Run a daily paper-trading update.

    Returns (updated_state, daily_artifacts)
    """
    from src.data.yfinance_fetcher import fetch_universe

    # Determine end date (today's date or last available trading day)
    if market_data is not None and len(market_data) > 0:
        end_date = market_data.index.max().strftime("%Y-%m-%d")
    else:
        end_date = datetime.now().strftime("%Y-%m-%d")

    # Fetch market data
    if market_data is None:
        data = fetch_universe(config.universe, config.history_start, end_date)
    else:
        data = market_data

    # Run simulation to get current day's results
    # Use full overlay warmup to be consistent, slice to relevant range
    sim = run_simulation(config, config.history_start, end_date, data=data)

    daily = sim.daily
    if daily.empty:
        return state, {}

    # Get latest day's data
    latest = daily.iloc[-1]
    latest_date = daily.index[-1].strftime("%Y-%m-%d")

    # Idempotency: if already processed this date, return current state
    if state.last_run_date == latest_date:
        return state, {}

    # Extract latest values from simulation output
    turnover = float(latest["turnover"]) if pd.notna(latest["turnover"]) else 0.0
    vol_scale = float(latest["vol_scale"]) if pd.notna(latest["vol_scale"]) else 1.0
    dd_scale = float(latest["dd_scale"]) if pd.notna(latest["dd_scale"]) else 1.0
    regime_exp = float(latest["regime_exposure"]) if pd.notna(latest["regime_exposure"]) else 1.0

    # Build positions info for latest
    positions_dict = {}
    for symbol in config.universe:
        col = f"weight_{symbol}"
        if col in daily.columns:
            positions_dict[symbol] = float(daily.iloc[-1][col])

    # Calculate daily P&L (mark-to-market approximation)
    daily_pnl = 0.0
    if latest["net_return"] != latest["net_return"]:  # NaN check
        daily_pnl = 0.0
    else:
        daily_pnl = state.current_nav * float(latest["net_return"])

    # Update NAV
    new_nav = state.current_nav + daily_pnl

    # Update running-maximum drawdown. The drawdown is always measured
    # against the all-time peak NAV, so a recovery followed by a new decline
    # is correctly reported as a deeper drawdown from the new high (see
    # compute_running_drawdown in src/evaluation/utils.py).
    state.peak_nav, state.max_drawdown = compute_running_drawdown(
        state.peak_nav, new_nav, state.max_drawdown
    )
    new_dd = state.max_drawdown

    # Enhanced drift monitoring calculations
    # Rolling 63-day Sharpe and max DD
    returns_arr = np.array(state.cumulative_returns + [float(latest["net_return"]) if pd.notna(latest["net_return"]) else 0.0])
    if len(returns_arr) >= 63:
        recent_returns = returns_arr[-63:]
    else:
        recent_returns = returns_arr

    # Rolling 63-day Sharpe, computed with the repository's canonical Sharpe
    # convention (src/evaluation/sharpe.py). The live drift flag, the
    # offline recomputation (research/drift_persistence_report.py) and the
    # promotion gate therefore report exactly the same number.
    rolling_sharpe = sharpe_ratio(recent_returns)

    # Persistence of the low-Sharpe condition: the number of consecutive
    # sessions for which the rolling Sharpe stayed below the alert threshold.
    # Recomputed from the stored return series so the count is reproducible
    # offline (research/drift_persistence_report.py) and cannot drift away
    # from the data it describes.
    history_dates = list(state.cumulative_dates)
    if len(history_dates) != len(state.cumulative_returns):
        history_dates = (
            history_dates[-len(state.cumulative_returns) :]
            if state.cumulative_returns
            else []
        )
    sharpe_persistence_days = int(
        sharpe_persistence(
            history_dates + [latest_date],
            [float(x) for x in returns_arr],
        )["streak_days"]
    )

    # Rolling max DD
    cum = np.cumprod(1.0 + returns_arr)
    peak = np.maximum.accumulate(cum)
    rolling_max_dd = float((cum / peak - 1.0).min())

    # Regime persistence
    if state.previous_regime_exposure is not None and state.previous_regime_exposure != regime_exp:
        regime_persistence = 1  # Reset on flip
    else:
        regime_persistence = state.regime_persistence_days + 1

    # Risk parameter bounds
    vol_scale_min = min(state.vol_scale_min, vol_scale) if state.vol_scale_min > 0 else vol_scale
    vol_scale_max = max(state.vol_scale_max, vol_scale)
    dd_scale_min = min(state.dd_scale_min, dd_scale) if state.dd_scale_min > 0 else dd_scale
    dd_scale_max = max(state.dd_scale_max, dd_scale)

    # Turnover distribution (rolling median and p95 from run_history)
    all_turnovers = [r.get("turnover", 0.0) for r in state.run_history] + [turnover]
    if all_turnovers:
        turnover_median = float(np.median(all_turnovers))
        turnover_p95 = float(np.percentile(all_turnovers, 95))
    else:
        turnover_median = 0.0
        turnover_p95 = 0.0

    # Drift monitoring
    drift_flags = {}
    if turnover > config.alert_signal_turnover_pct:
        drift_flags["high_turnover"] = {
            "value": turnover,
            "threshold": config.alert_signal_turnover_pct,
            "date": latest_date,
        }

    if vol_scale > config.alert_vol_scale_max:
        drift_flags["high_vol_scale"] = {
            "value": vol_scale,
            "threshold": config.alert_vol_scale_max,
            "date": latest_date,
        }

    if dd_scale < config.alert_dd_scale_min:
        drift_flags["low_dd_scale"] = {
            "value": dd_scale,
            "threshold": config.alert_dd_scale_min,
            "date": latest_date,
        }

    current_dd_pct = abs(new_dd) * 100.0 if new_dd < 0 else 0.0
    if current_dd_pct > config.alert_max_drawdown_pct * 100.0:
        drift_flags["max_drawdown_exceeded"] = {
            "value": current_dd_pct,
            "threshold": config.alert_max_drawdown_pct * 100.0,
            "date": latest_date,
        }

    # Regime change detection
    if (
        state.previous_regime_exposure is not None
        and state.previous_regime_exposure != regime_exp
        and config.alert_regime_flip
    ):
        drift_flags["regime_flip"] = {
            "from": state.previous_regime_exposure,
            "to": regime_exp,
            "date": latest_date,
        }

    # Enhanced drift alerts
    if (
        rolling_sharpe < DEFAULT_SHARPE_THRESHOLD
        and len(returns_arr) >= DEFAULT_MIN_PERIODS
    ):
        drift_flags["low_rolling_sharpe"] = {
            "value": rolling_sharpe,
            "threshold": DEFAULT_SHARPE_THRESHOLD,
            "date": latest_date,
            "persistence_days": sharpe_persistence_days,
        }

    if regime_persistence < 5 and state.previous_regime_exposure is not None and state.previous_regime_exposure != regime_exp:
        drift_flags["regime_persistence_low"] = {
            "value": regime_persistence,
            "threshold": 5,
            "date": latest_date,
        }

    if vol_scale > 2.5:
        drift_flags["vol_scale_extreme"] = {
            "value": vol_scale,
            "threshold": 2.5,
            "date": latest_date,
        }

    if dd_scale < 0.2:
        drift_flags["dd_scale_extreme"] = {
            "value": dd_scale,
            "threshold": 0.2,
            "date": latest_date,
        }

    # Update state
    state.last_run_date = latest_date
    state.current_positions = positions_dict
    state.cumulative_returns.append(float(latest["net_return"]) if pd.notna(latest["net_return"]) else 0.0)
    state.cumulative_pnl.append(daily_pnl)
    state.cumulative_dates.append(latest_date)
    state.current_nav = new_nav
    state.max_drawdown = new_dd
    state.drift_flags = drift_flags
    state.previous_regime_exposure = regime_exp
    # Enhanced drift monitoring state
    state.rolling_sharpe_63d = rolling_sharpe
    state.rolling_max_dd_63d = rolling_max_dd
    state.regime_persistence_days = regime_persistence
    state.vol_scale_min = vol_scale_min
    state.vol_scale_max = vol_scale_max
    state.dd_scale_min = dd_scale_min
    state.dd_scale_max = dd_scale_max
    state.turnover_median = turnover_median
    state.turnover_p95 = turnover_p95
    state.run_history.append(
        {
            "date": latest_date,
            "nav": new_nav,
            "daily_return": float(latest["net_return"]) if pd.notna(latest["net_return"]) else 0.0,
            "daily_pnl": daily_pnl,
            "turnover": turnover,
            "vol_scale": vol_scale,
            "dd_scale": dd_scale,
            "regime_exposure": regime_exp,
            "n_positions": int(latest["n_positions"]) if pd.notna(latest["n_positions"]) else 0,
        }
    )

    # Build daily artifacts
    output_dir = _ensure_path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    date_str_clean = latest_date.replace("-", "")

    positions_df = pd.DataFrame(
        [{"symbol": k, "weight": v, "date": latest_date} for k, v in positions_dict.items()]
    )
    positions_df.to_parquet(output_dir / f"positions_{date_str_clean}.parquet", index=False)

    regime_df = pd.DataFrame(
        [
            {
                "date": latest_date,
                "spy_price": float(latest.get("price_SPY", np.nan)) if "price_SPY" in daily.columns else np.nan,
                "regime_exposure": regime_exp,
            }
        ]
    )
    # Add SPY SMA if available - approximate from engine logic; but just store what we have
    regime_df.to_parquet(output_dir / f"regime_{date_str_clean}.parquet", index=False)

    risk_df = pd.DataFrame(
        [
            {
                "date": latest_date,
                "vol_scale": vol_scale,
                "dd_scale": dd_scale,
                "drawdown": new_dd,
                "exposure": float(latest["exposure"]) if pd.notna(latest["exposure"]) else 0.0,
            }
        ]
    )
    risk_df.to_parquet(output_dir / f"risk_state_{date_str_clean}.parquet", index=False)

    pnl_df = pd.DataFrame(
        [
            {
                "date": latest_date,
                "daily_return": float(latest["net_return"]) if pd.notna(latest["net_return"]) else 0.0,
                "daily_pnl": daily_pnl,
                "nav": new_nav,
            }
        ]
    )
    pnl_df.to_parquet(output_dir / f"daily_pnl_{date_str_clean}.parquet", index=False)

    artifacts = {
        "latest_date": latest_date,
        "positions": positions_dict,
        "regime_exposure": regime_exp,
        "vol_scale": vol_scale,
        "dd_scale": dd_scale,
        "daily_return": float(latest["net_return"]) if pd.notna(latest["net_return"]) else 0.0,
        "daily_pnl": daily_pnl,
        "nav": new_nav,
        "max_drawdown": new_dd,
        "turnover": turnover,
        "drift_flags": drift_flags,
    }

    return state, artifacts


def generate_paper_report(state: PaperTradingState, config: PaperTradingConfig) -> str:
    """Generate markdown report for daily review."""
    report_path = _ensure_path(config.report_path)
    last_run = state.last_run_date or "Never"
    days_tracked = len(state.cumulative_dates)

    # Calculate performance metrics if we have history
    if len(state.cumulative_returns) > 0:
        returns = np.array(state.cumulative_returns)
        total_ret = state.current_nav / 100000.0 - 1.0
        ann_ret = (1.0 + total_ret) ** (252.0 / max(days_tracked, 1)) - 1.0 if days_tracked > 0 else 0.0
        if days_tracked > 1:
            vol = np.std(returns) * np.sqrt(252.0)
            sharpe = ann_ret / vol if vol > 0 else 0.0
        else:
            vol = 0.0
            sharpe = 0.0
    else:
        total_ret = 0.0
        ann_ret = 0.0
        vol = 0.0
        sharpe = 0.0

    drift_lines = []
    if state.drift_flags:
        for k, v in state.drift_flags.items():
            drift_lines.append(f"- **{k}**: {v}")
    else:
        drift_lines.append("- None detected")

    # Enhanced drift monitoring
    enhanced_lines = []
    enhanced_lines.append(f"- **Rolling 63-day Sharpe:** {state.rolling_sharpe_63d:.4f}")
    enhanced_lines.append(f"- **Rolling 63-day Max DD:** {state.rolling_max_dd_63d:.2%}")
    enhanced_lines.append(f"- **Regime Persistence:** {state.regime_persistence_days} days in current regime")
    enhanced_lines.append(f"- **vol_scale range:** [{state.vol_scale_min:.3f}, {state.vol_scale_max:.3f}]")
    enhanced_lines.append(f"- **dd_scale range:** [{state.dd_scale_min:.3f}, {state.dd_scale_max:.3f}]")
    enhanced_lines.append(f"- **Turnover (median/p95):** {state.turnover_median:.2%} / {state.turnover_p95:.2%}")

    positions_lines = []
    if state.current_positions:
        for sym, w in sorted(state.current_positions.items(), key=lambda x: abs(x[1]), reverse=True):
            if abs(w) > 1e-9:
                positions_lines.append(f"- {sym}: {w:.4%}")
    else:
        positions_lines.append("- No positions")

    report = f"""# Paper-Trading Rolling Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
**Last Run Date:** {last_run}
**Days Tracked:** {days_tracked}

## Current State

| Metric | Value |
|---|---|
| Current NAV | ${state.current_nav:,.2f} |
| Peak NAV | ${state.peak_nav:,.2f} |
| Paper Drawdown | {state.max_drawdown:.2%} |
| Total Return | {total_ret:.2%} |
| Annualized Return | {ann_ret:.2%} |
| Volatility (ann.) | {vol:.2%} |
| Sharpe Ratio (ann.) | {sharpe:.4f} |

## Positions Table

{chr(10).join(positions_lines)}

## Drift Monitoring

{chr(10).join(drift_lines)}

## Enhanced Drift Monitoring

{chr(10).join(enhanced_lines)}

## Performance Tracking

- Go/No-Go Status (after {config.go_no_go_min_days} days): {'PENDING' if days_tracked < config.go_no_go_min_days else ('READY TO EVALUATE' if days_tracked >= config.go_no_go_min_days else 'PENDING')}
- Target Sharpe: >= {config.go_no_go_target_sharpe}
- Max DD Threshold: <= {config.go_no_go_max_dd_threshold:.2%}

## Run History (Recent)

"""
    # Add last 5 runs
    for run in state.run_history[-5:]:
        report += f"- {run['date']}: NAV=${run['nav']:,.2f}, Ret={run['daily_return']:.2%}, Turnover={run['turnover']:.2%}\n"
    if len(state.run_history) == 0:
        report += "- No runs yet\n"

    with open(report_path, "w") as fh:
        fh.write(report)

    return report
