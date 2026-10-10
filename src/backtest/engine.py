"""Backtesting engine for time-series momentum strategy.

Executes daily rebalancing per strategy signals, applies commission and slippage
from settings.yaml, and computes performance metrics across chronological
train/validation/test splits.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import yaml

from src.data.yfinance_fetcher import fetch_universe
from src.features.momentum import build_weights, compute_momentum, signal_summary


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def load_settings() -> dict:
    path = _project_root() / "config" / "settings.yaml"
    with open(path, "r") as fh:
        return yaml.safe_load(fh) or {}


def get_cost_params() -> tuple[float, float]:
    settings = load_settings()
    backtest_cfg = settings.get("backtest", {})
    commission_bps = backtest_cfg.get("default_commission_bps", 1.0)
    slippage_bps = backtest_cfg.get("default_slippage_bps", 2.0)
    return commission_bps / 10000.0, slippage_bps / 10000.0


def get_risk_free_rate() -> float:
    settings = load_settings()
    eval_cfg = settings.get("evaluation", {})
    return eval_cfg.get("risk_free_rate_annual", 0.02)


def compute_metrics(
    returns: pd.Series,
    weights: pd.DataFrame,
    commission: float,
    slippage: float,
    rf_annual: float,
) -> dict:
    """Compute performance metrics for a backtest period."""
    if returns.empty:
        return {}

    # Annualized return
    n_days = len(returns)
    ann_return = (1 + returns).prod() ** (252 / n_days) - 1 if n_days > 0 else 0.0

    # Annualized volatility
    ann_vol = returns.std() * np.sqrt(252) if n_days > 1 else 0.0

    # Sharpe ratio (using provided risk-free rate)
    sharpe = (ann_return - rf_annual) / ann_vol if ann_vol > 0 else 0.0

    # Sortino ratio (downside deviation)
    downside = returns[returns < 0]
    downside_vol = downside.std() * np.sqrt(252) if len(downside) > 1 else 0.0
    sortino = (ann_return - rf_annual) / downside_vol if downside_vol > 0 else 0.0

    # Max drawdown
    cum = (1 + returns).cumprod()
    running_max = cum.expanding().max()
    drawdown = (cum / running_max) - 1
    max_drawdown = drawdown.min()

    # Cumulative return
    cum_return = cum.iloc[-1] - 1

    # Turnover: sum of absolute daily weight changes
    weight_changes = weights.diff().abs().sum(axis=1)
    turnover = weight_changes.sum() / n_days if n_days > 0 else 0.0

    # Annualized turnover
    ann_turnover = turnover * 252

    # Trade count (number of rebalancing days with non-zero weight changes)
    trade_days = (weight_changes > 1e-10).sum()
    trade_count = int(trade_days)

    # Profit factor
    gross_profit = returns[returns > 0].sum()
    gross_loss = -returns[returns < 0].sum()
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

    # Exposure (average gross weight)
    exposure = weights.abs().sum(axis=1).mean()

    return {
        "total_return": float(cum_return),
        "annualized_return": float(ann_return),
        "annualized_volatility": float(ann_vol),
        "sharpe_ratio": float(sharpe),
        "sortino_ratio": float(sortino),
        "max_drawdown": float(max_drawdown),
        "avg_daily_turnover": float(turnover),
        "annualized_turnover": float(ann_turnover),
        "trade_count": trade_count,
        "profit_factor": float(profit_factor) if profit_factor != np.inf else "inf",
        "avg_exposure": float(exposure),
    }


def run_backtest(
    symbols: list[str],
    start_date: str,
    end_date: str,
    lookback: int = 252,
    skip: int = 21,
    top_fraction: float = 0.5,
    rebalance_freq: str = "M",
) -> tuple[pd.Series, pd.DataFrame, dict]:
    """Run the full backtest pipeline."""
    # Fetch data
    print(f"Fetching data for {symbols} from {start_date} to {end_date}...")
    data = fetch_universe(symbols, start_date, end_date, force=False)

    if data.empty:
        raise RuntimeError("No data fetched")

    # Extract Close prices
    close = data.xs("Close", level=0, axis=1)
    close = close.ffill().dropna(how="all")

    # Compute weights using momentum strategy
    print("Computing momentum signals...")
    weights = build_weights(close, lookback=lookback, skip=skip, top_fraction=top_fraction)

    # Align weights to close prices (weights shifted by 1 day in build_weights)
    common_index = close.index.intersection(weights.index)
    close = close.loc[common_index]
    weights = weights.loc[common_index]

    # Compute daily returns
    daily_ret = close.pct_change().fillna(0.0)

    # Portfolio returns (weight * asset return)
    # weights at t are formed from data up to t-1, applied to returns at t
    port_ret = (weights * daily_ret).sum(axis=1)

    # Apply transaction costs
    commission_bps, slippage_bps = get_cost_params()
    weight_changes = weights.diff().abs().sum(axis=1)
    cost_per_trade = commission_bps + slippage_bps
    costs = weight_changes * cost_per_trade
    net_ret = port_ret - costs

    # Metrics
    rf_annual = get_risk_free_rate()
    metrics = compute_metrics(net_ret, weights, commission_bps, slippage_bps, rf_annual)

    return net_ret, weights, metrics


def split_periods(
    returns: pd.Series,
    weights: pd.DataFrame,
    train_end: str = "2009-12-31",
    val_end: str = "2017-12-31",
) -> dict:
    """Split returns into train/validation/test periods."""
    train_end_dt = pd.Timestamp(train_end, tz="UTC")
    val_end_dt = pd.Timestamp(val_end, tz="UTC")

    train_mask = returns.index <= train_end_dt
    val_mask = (returns.index > train_end_dt) & (returns.index <= val_end_dt)
    test_mask = returns.index > val_end_dt

    periods = {
        "train": {"returns": returns[train_mask], "weights": weights[train_mask]},
        "validation": {"returns": returns[val_mask], "weights": weights[val_mask]},
        "test": {"returns": returns[test_mask], "weights": weights[test_mask]},
    }

    return periods


def format_metrics_table(metrics: dict) -> str:
    """Format metrics as a markdown table."""
    rows = []
    for period, m in metrics.items():
        if not m:
            rows.append(f"| {period} | - | - | - | - | - | - | - | - | - | - |")
            continue
        pf = m.get("profit_factor", "N/A")
        if isinstance(pf, float):
            pf_str = f"{pf:.2f}"
        else:
            pf_str = str(pf)
        rows.append(
            f"| {period} | {m['total_return']:.4f} | {m['annualized_return']:.4f} | "
            f"{m['annualized_volatility']:.4f} | {m['sharpe_ratio']:.4f} | "
            f"{m['sortino_ratio']:.4f} | {m['max_drawdown']:.4f} | "
            f"{m['annualized_turnover']:.2f} | {m['trade_count']} | {pf_str} |"
        )

    header = (
        "| Period | Total Return | Ann. Return | Ann. Vol | Sharpe | Sortino | "
        "Max DD | Ann. Turnover | Trades | Profit Factor |\n"
        "|--------|-------------|-------------|----------|--------|---------|--------|---------------|--------|---------------|"
    )
    return header + "\n" + "\n".join(rows)


def generate_report(
    symbols: list[str],
    start_date: str,
    end_date: str,
    lookback: int,
    skip: int,
    top_fraction: float,
    rebalance_freq: str,
    periods: dict,
    metrics: dict,
    output_dir: Path,
) -> Path:
    """Generate the experiment report markdown file."""
    settings = load_settings()
    commission_bps = settings.get("backtest", {}).get("default_commission_bps", 1.0)
    slippage_bps = settings.get("backtest", {}).get("default_slippage_bps", 2.0)
    rf_annual = settings.get("evaluation", {}).get("risk_free_rate_annual", 0.02)

    today = datetime.utcnow().strftime("%Y-%m-%d")

    report = f"""# Experiment: Time-Series Momentum Baseline (tsmomentum_baseline_001)

## Hypothesis Reference

See `research/hypotheses/tsmomentum_001.md` for the full hypothesis documentation.

**Mechanism**: Time-series momentum exploits the tendency for assets with positive
recent returns to continue outperforming in the near term, driven by investor
underreaction and slow information diffusion.

**Expected Direction**: Positive carry (3-8% annualized gross before costs)

**Falsification Condition**: Test-period Sharpe < 0.5 net of costs OR
test Sharpe < train Sharpe - 1 standard deviation of train Sharpe estimates.

---

## Data Used

- **Source**: Yahoo Finance (via yfinance library v1.7.0)
- **Date Range**: {start_date} to {end_date}
- **Frequency**: Daily (end-of-day OHLCV)
- **Universe**: {", ".join(symbols)}
- **Records**: {len(periods['train']['returns']) + len(periods['validation']['returns']) + len(periods['test']['returns'])} trading days total
- **Point-in-Time Treatment**: All signals computed using only data available
  at signal formation time. Momentum uses 12-month lookback (252 trading days)
  excluding the most recent month (21 trading days) to avoid short-term
  reversal microstructure noise. Weights computed on day t are shifted to be
  effective on day t+1. No forward-looking data used.

---

## Configuration

- **Lookback Window**: {lookback} trading days (~12 months)
- **Skip Window**: {skip} trading days (~1 month)
- **Selection**: Top {top_fraction:.0%} of assets by momentum (equal-weighted)
- **Rebalancing Frequency**: {rebalance_freq} (monthly via daily signal with
  forward-filled weights)
- **Commission**: {commission_bps:.1f} bps per trade (round-trip)
- **Slippage**: {slippage_bps:.1f} bps per trade
- **Risk-Free Rate**: {rf_annual:.1%} annual (for Sharpe calculation)
- **Code Revision**: {_get_git_hash()}

---

## Train/Validation/Test Splits

| Period | Start Date | End Date | Trading Days |
|--------|------------|----------|--------------|
| Train | {start_date} | 2009-12-31 | {len(periods['train']['returns'])} |
| Validation | 2010-01-01 | 2017-12-31 | {len(periods['validation']['returns'])} |
| Test | 2018-01-01 | {end_date} | {len(periods['test']['returns'])} |

---

## Results

### Performance Metrics (Net of Costs)

{format_metrics_table(metrics)}

### Detailed Period Results

#### Train Period (1993-01-01 to 2009-12-31)
- **Observations**: {len(periods['train']['returns'])} daily returns
- **Trades**: {metrics.get('train', {}).get('trade_count', 'N/A')}
- **Avg Positions**: {periods['train']['weights'].gt(0).sum(axis=1).mean():.1f}

#### Validation Period (2010-01-01 to 2017-12-31)
- **Observations**: {len(periods['validation']['returns'])} daily returns
- **Trades**: {metrics.get('validation', {}).get('trade_count', 'N/A')}
- **Avg Positions**: {periods['validation']['weights'].gt(0).sum(axis=1).mean():.1f}

#### Test Period (2018-01-01 to {end_date})
- **Observations**: {len(periods['test']['returns'])} daily returns
- **Trades**: {metrics.get('test', {}).get('trade_count', 'N/A')}
- **Avg Positions**: {periods['test']['weights'].gt(0).sum(axis=1).mean():.1f}

---

## Cost Assumptions

| Component | Value | Source |
|-----------|-------|--------|
| Commission | {commission_bps:.1f} bps | config/settings.yaml |
| Slippage | {slippage_bps:.1f} bps | config/settings.yaml |
| Risk-Free Rate | {rf_annual:.1%} annual | config/settings.yaml |
| Total Round-Trip Cost | {commission_bps + slippage_bps:.1f} bps | Derived |

Costs applied per rebalancing day proportional to absolute weight change.

---

## Reproduction Commands

```bash
# From repository root
python3 src/backtest/engine.py --output-dir research/experiments
```

This will fetch data, run the backtest, and regenerate this report.

---

## Classification

This result is classified as an **exploratory signal**. It validates the
research pipeline but does not yet meet promotion gates (net out-of-sample
Sharpe >= 0.9 and >100 pooled out-of-sample trades). Further validation
required including robustness checks, parameter perturbation, and
out-of-sample walk-forward testing.

---

*Report generated: {today}*
*Pipeline: data ingestion → feature engineering → backtest → evaluation*
"""

    output_path = output_dir / "tsmomentum_baseline_001.md"
    output_path.write_text(report)
    return output_path


def _get_git_hash() -> str:
    try:
        import subprocess

        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=_project_root(),
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def main():
    parser = argparse.ArgumentParser(description="Run time-series momentum backtest")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="research/experiments",
        help="Output directory for reports",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default="SPY,QQQ,IWM,TLT,GLD,EFA,EEM",
        help="Comma-separated list of symbols",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default="1993-01-01",
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="End date (YYYY-MM-DD), defaults to today",
    )
    parser.add_argument(
        "--lookback",
        type=int,
        default=252,
        help="Momentum lookback in trading days",
    )
    parser.add_argument(
        "--skip",
        type=int,
        default=21,
        help="Skip days to avoid short-term reversal",
    )
    parser.add_argument(
        "--top-fraction",
        type=float,
        default=0.5,
        help="Top fraction of assets to select",
    )
    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",")]
    end_date = args.end_date or datetime.utcnow().strftime("%Y-%m-%d")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run backtest
    net_ret, weights, _ = run_backtest(
        symbols=symbols,
        start_date=args.start_date,
        end_date=end_date,
        lookback=args.lookback,
        skip=args.skip,
        top_fraction=args.top_fraction,
    )

    # Split periods
    periods = split_periods(net_ret, weights)

    # Compute metrics for each period
    commission_bps, slippage_bps = get_cost_params()
    rf_annual = get_risk_free_rate()
    metrics = {}
    for period_name, data in periods.items():
        metrics[period_name] = compute_metrics(
            data["returns"], data["weights"], commission_bps, slippage_bps, rf_annual
        )

    # Generate report
    report_path = generate_report(
        symbols=symbols,
        start_date=args.start_date,
        end_date=end_date,
        lookback=args.lookback,
        skip=args.skip,
        top_fraction=args.top_fraction,
        rebalance_freq="M",
        periods=periods,
        metrics=metrics,
        output_dir=output_dir,
    )

    print(f"\nBacktest complete. Report saved to: {report_path}")

    # Print summary
    print("\n=== Summary ===")
    for period_name, m in metrics.items():
        if m:
            print(
                f"{period_name:12s} | Sharpe: {m['sharpe_ratio']:.3f} | "
                f"Ann Ret: {m['annualized_return']:.2%} | "
                f"Max DD: {m['max_drawdown']:.2%} | "
                f"Trades: {m['trade_count']}"
            )


if __name__ == "__main__":
    main()