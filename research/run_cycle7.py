"""Cycle 7: Simulation Framework & Paper-Trading Preparation.

Builds a simulation engine for the validated Credible Candidate and prepares
for paper-trading (prospective) validation. The simulation must:
1. Reproduce the candidate strategy with exact same logic as backtest
2. Support walk-forward re-optimization and fixed-parameter execution
3. Generate realistic position/time series for paper-trading tracking
4. Include operational constraints: transaction costs, slippage, position limits, rebalancing schedule
5. Produce daily P&L, positions, risk metrics, and trade logs suitable for prospective monitoring
"""

from __future__ import annotations

import sys
import warnings
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.backtest.engine import get_cost_params, get_risk_free_rate
from src.data.yfinance_fetcher import fetch_universe
from src.simulation.engine import (
    CostModelConfig,
    ExecutionConfig,
    RegimeFilterConfig,
    RiskOverlayConfig,
    SignalConfig,
    SimulationConfig,
    run_simulation,
    run_simulation_fixed_params,
)

warnings.filterwarnings("ignore", category=RuntimeWarning)

# ---------------------------------------------------------------------------
# Configuration (frozen from Cycle 5/6 validated candidate)
# ---------------------------------------------------------------------------
SYMBOLS = ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"]
START_DATE = "1993-01-01"
END_DATE = "2026-10-09"
TRAIN_END = "2009-12-31"
VAL_END = "2017-12-31"
TEST_START = "2018-01-01"

# Validated candidate config
LOOKBACK, SKIP, TOP_FRACTION = 226, 21, 0.5
VOL_TARGET, VOL_LOOKBACK = 0.10, 63
DD_THRESHOLD, DD_REDUCTION = 0.15, 0.5
SPY_SMA_WINDOW = 200

COMMISSION_BPS, SLIPPAGE_BPS = get_cost_params()  # fractions (1bps -> 0.0001)
COMMISSION_BPS_RAW = COMMISSION_BPS * 10000.0  # 1.0
SLIPPAGE_BPS_RAW = SLIPPAGE_BPS * 10000.0  # 2.0
TOTAL_COST_BPS_RAW = COMMISSION_BPS_RAW + SLIPPAGE_BPS_RAW  # 3.0

RF_ANNUAL = get_risk_free_rate()
REPO_ROOT = Path(__file__).resolve().parent.parent

# Reference metrics from Cycle 5/6 (backtest) for verification
# These are the "correct 3 bps" numbers from Cycle 5 regime filter test
BACKTEST_METRICS = {
    "test_sharpe": 1.4178,
    "max_dd": -0.0779,
    "trades": 1196,
    "ann_return": 0.1446,
    "wf_mean_oos_sharpe": 0.9473,
}


def _git_hash() -> str:
    try:
        import subprocess
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=False, capture_output=True, text=True, cwd=REPO_ROOT,
        )
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except (OSError, RuntimeError):
        return "unknown"


def _today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def _utc(ts) -> pd.Timestamp:
    return pd.Timestamp(ts, tz="UTC")


def _load_close(symbols: list[str], start_date: str, end_date: str) -> pd.DataFrame:
    data = fetch_universe(symbols, start_date, end_date, force=False)
    if data.empty:
        raise RuntimeError(f"No data fetched for {symbols}")
    close = data.xs("Close", level=0, axis=1)
    close = close.ffill().dropna(how="all")
    return close


def run_simulation_full_history() -> tuple[pd.Series, pd.DataFrame, dict]:
    """Run simulation on full history (1993-2026) for verification against backtest."""
    print("\n=== [1] Full History Simulation (1993-2026) ===")

    config = SimulationConfig(
        universe=SYMBOLS,
        signal=SignalConfig(type="tsmomentum", lookback=LOOKBACK, skip=SKIP, top_fraction=TOP_FRACTION, rebalance_freq="monthly"),
        risk_overlay=RiskOverlayConfig(vol_target=VOL_TARGET, vol_lookback=VOL_LOOKBACK, dd_control_threshold=DD_THRESHOLD, dd_control_reduction=DD_REDUCTION),
        regime_filter=RegimeFilterConfig(type="spy_sma", window=SPY_SMA_WINDOW, exposure_below=0.0, exposure_above=1.0),
        cost_model=CostModelConfig(commission_bps=COMMISSION_BPS_RAW, slippage_bps=SLIPPAGE_BPS_RAW),
        execution=ExecutionConfig(signal_lag_days=1, price_field="Open", timezone="UTC"),
    )

    result = run_simulation(config, START_DATE, END_DATE)
    print(f"  Full history Sharpe: {result.metrics['sharpe_ratio']:.4f}")
    print(f"  Full history Max DD: {result.metrics['max_drawdown']:.4f}")
    print(f"  Full history Trades: {result.metrics['trade_count']}")
    print(f"  Full history Ann Return: {result.metrics['annualized_return']:.4f}")

    return result.daily_returns, result.daily_weights, result.metrics


def run_simulation_oos_only() -> tuple[pd.Series, pd.DataFrame, dict]:
    """Run simulation on OOS period only (2018-2026) for paper-trading baseline."""
    print("\n=== [2] OOS Period Simulation (2018-2026) ===")

    config = SimulationConfig(
        universe=SYMBOLS,
        signal=SignalConfig(type="tsmomentum", lookback=LOOKBACK, skip=SKIP, top_fraction=TOP_FRACTION, rebalance_freq="monthly"),
        risk_overlay=RiskOverlayConfig(vol_target=VOL_TARGET, vol_lookback=VOL_LOOKBACK, dd_control_threshold=DD_THRESHOLD, dd_control_reduction=DD_REDUCTION),
        regime_filter=RegimeFilterConfig(type="spy_sma", window=SPY_SMA_WINDOW, exposure_below=0.0, exposure_above=1.0),
        cost_model=CostModelConfig(commission_bps=COMMISSION_BPS_RAW, slippage_bps=SLIPPAGE_BPS_RAW),
        execution=ExecutionConfig(signal_lag_days=1, price_field="Open", timezone="UTC"),
    )

    result = run_simulation(config, TEST_START, END_DATE)
    print(f"  OOS Sharpe: {result.metrics['sharpe_ratio']:.4f}")
    print(f"  OOS Max DD: {result.metrics['max_drawdown']:.4f}")
    print(f"  OOS Trades: {result.metrics['trade_count']}")
    print(f"  OOS Ann Return: {result.metrics['annualized_return']:.4f}")

    return result.daily_returns, result.daily_weights, result.metrics, result


def run_walkforward_simulation() -> dict:
    """Run walk-forward evaluation using the simulation engine."""
    print("\n=== [3] Walk-Forward Simulation ===")

    from src.evaluation.walkforward import (
        evaluate_walkforward,
        summarize_walkforward,
    )

    def config_fn(symbols: list[str], start: str, end: str) -> tuple[pd.Series, pd.DataFrame]:
        return run_simulation_fixed_params(
            symbols, start, end,
            lookback=LOOKBACK, skip=SKIP, top_fraction=TOP_FRACTION,
            vol_target=VOL_TARGET, vol_lookback=VOL_LOOKBACK,
            dd_threshold=DD_THRESHOLD, dd_reduction=DD_REDUCTION,
            spy_sma_window=SPY_SMA_WINDOW,
            commission_bps=COMMISSION_BPS_RAW, slippage_bps=SLIPPAGE_BPS_RAW,
        )

    wf_df = evaluate_walkforward(
        SYMBOLS, START_DATE, END_DATE, config_fn,
        train_years=10.0, test_months=12.0, step_months=6.0,
        purge_days=21, embargo_days=21,
    )

    summary = summarize_walkforward(wf_df)
    print(f"  WF Folds: {summary.get('n_folds', 0)}")
    print(f"  Mean test Sharpe: {summary.get('mean_test_sharpe', np.nan):.4f}")
    print(f"  % Positive Sharpe: {summary.get('pct_positive_sharpe', np.nan):.1%}")
    print(f"  Mean test max DD: {summary.get('mean_test_max_dd', np.nan):.2%}")
    print(f"  Total test trades: {summary.get('total_test_trades', 0)}")

    return {"wf_df": wf_df, "summary": summary}


def write_verification_report(
    full_metrics: dict,
    oos_metrics: dict,
    wf_summary: dict,
    oos_result: object,
) -> Path:
    """Generate the simulation verification report."""
    today = _today()
    git_rev = _git_hash()

    # Compute differences from backtest
    sim_test_sharpe = oos_metrics["sharpe_ratio"]
    sim_max_dd = oos_metrics["max_drawdown"]
    sim_trades = oos_metrics["trade_count"]
    sim_ann_return = oos_metrics["annualized_return"]

    sharpe_diff = abs(sim_test_sharpe - BACKTEST_METRICS["test_sharpe"])
    dd_diff = abs(sim_max_dd - BACKTEST_METRICS["max_dd"])
    trades_diff = abs(sim_trades - BACKTEST_METRICS["trades"])
    ann_return_diff = abs(sim_ann_return - BACKTEST_METRICS["ann_return"])

    wf_mean_sharpe = wf_summary.get("mean_test_sharpe", np.nan)
    wf_sharpe_diff = abs(wf_mean_sharpe - BACKTEST_METRICS["wf_mean_oos_sharpe"]) if not np.isnan(wf_mean_sharpe) else np.nan

    # Tolerance checks
    sharpe_pass = sharpe_diff < 0.02
    dd_pass = dd_diff < 0.005
    trades_pass = trades_diff <= 50  # allow some variance
    ann_return_pass = ann_return_diff < 0.005
    wf_pass = wf_sharpe_diff < 0.02 if not np.isnan(wf_sharpe_diff) else False

    md = f"""# Simulation Verification Report (simulation_verification_001)

## Objective

Verify that the new simulation engine reproduces the Cycle 5/6 backtest results
for the validated Credible Candidate (SPY trend filter on 226-day TSMOM with
combined vol-targeting 10% + drawdown control 15%) within acceptable tolerances.

**Tolerance Criteria**:
- Sharpe difference < 0.02
- Max DD difference < 0.5% (0.005)
- Trade count difference <= 50
- Annual return difference < 0.5%
- WF mean OOS Sharpe difference < 0.02

---

## Candidate Configuration

| Parameter | Value |
|-----------|-------|
| Candidate ID | tsmomentum_spytrend_001 |
| Universe | SPY, QQQ, IWM, TLT, GLD, EFA, EEM |
| Signal | 226-day TSMOM (lookback=226, skip=21, top_fraction=0.5) |
| Risk Overlay | Vol targeting 10% (63d lookback) + DD control 15% (50% reduction) |
| Regime Filter | SPY 200-day SMA (0% exposure below, 100% above) |
| Cost Model | 1 bps commission + 2 bps slippage = 3 bps round-trip |
| Execution | Signal lag 1 day, Open price, UTC |

---

## Verification Results: OOS Period (2018-2026)

| Metric | Backtest (Cycle 5/6) | Simulation | Diff | Status |
|--------|---------------------|------------|------|--------|
| Test Sharpe (2018-2026) | {BACKTEST_METRICS['test_sharpe']:.4f} | {sim_test_sharpe:.4f} | {sharpe_diff:.4f} | {'PASS' if sharpe_pass else 'FAIL'} |
| Max DD (2018-2026) | {BACKTEST_METRICS['max_dd']:.4f} | {sim_max_dd:.4f} | {dd_diff:.4f} | {'PASS' if dd_pass else 'FAIL'} |
| Trades (2018-2026) | {BACKTEST_METRICS['trades']} | {sim_trades} | {trades_diff} | {'PASS' if trades_pass else 'FAIL'} |
| Ann. Return (2018-2026) | {BACKTEST_METRICS['ann_return']:.4f} | {sim_ann_return:.4f} | {ann_return_diff:.4f} | {'PASS' if ann_return_pass else 'FAIL'} |
| WF Mean OOS Sharpe | {BACKTEST_METRICS['wf_mean_oos_sharpe']:.4f} | {wf_mean_sharpe:.4f} | {wf_sharpe_diff:.4f} | {'PASS' if wf_pass else 'FAIL'} |

---

## Full History Simulation (1993-2026)

| Metric | Simulation |
|--------|------------|
| Sharpe | {full_metrics['sharpe_ratio']:.4f} |
| Annualized Return | {full_metrics['annualized_return']:.4f} |
| Max Drawdown | {full_metrics['max_drawdown']:.4f} |
| Trades | {full_metrics['trade_count']} |
| Annualized Vol | {full_metrics['annualized_volatility']:.4f} |
| Sortino | {full_metrics['sortino_ratio']:.4f} |
| Profit Factor | {full_metrics['profit_factor']:.2f} |
| Avg Exposure | {full_metrics['avg_exposure']:.4f} |

---

## Walk-Forward Simulation Results

| Metric | Value |
|--------|-------|
| Folds | {wf_summary.get('n_folds', 'N/A')} |
| Mean Test Sharpe | {wf_mean_sharpe:.4f} |
| Std Test Sharpe | {wf_summary.get('std_test_sharpe', np.nan):.4f} |
| Median Test Sharpe | {wf_summary.get('median_test_sharpe', np.nan):.4f} |
| Min Test Sharpe | {wf_summary.get('min_test_sharpe', np.nan):.4f} |
| Max Test Sharpe | {wf_summary.get('max_test_sharpe', np.nan):.4f} |
| % Positive Sharpe Folds | {wf_summary.get('pct_positive_sharpe', np.nan):.1%} |
| Mean Test Ann. Return | {wf_summary.get('mean_test_ann_return', np.nan):.2%} |
| Mean Test Max DD | {wf_summary.get('mean_test_max_dd', np.nan):.2%} |
| Mean Test Trades | {wf_summary.get('mean_test_trades', np.nan):.1f} |
| Total Pooled OOS Trades | {wf_summary.get('total_test_trades', 0)} |

---

## Overall Verification Status

**All tolerance checks passed: {'YES' if all([sharpe_pass, dd_pass, trades_pass, ann_return_pass, wf_pass]) else 'NO'}**

The simulation engine {'successfully reproduces' if all([sharpe_pass, dd_pass, trades_pass, ann_return_pass, wf_pass]) else 'does NOT fully reproduce'} the backtest results within specified tolerances.

---

## Reproduction Commands

```bash
# Run Cycle 7 simulation pipeline
python3 research/run_cycle7.py

# Verify artifacts
python3 -c "
import pandas as pd
sim = pd.read_parquet('data/processed/simulation_candidate_001.parquet')
print('Simulation rows:', len(sim))
print('Date range:', sim.index.min(), 'to', sim.index.max())
"
```

---

## Artifacts Produced

| Artifact | Path |
|----------|------|
| Simulation daily series | `data/processed/simulation_candidate_001.parquet` |
| Trade log | `data/processed/trades_candidate_001.parquet` |
| Frozen config | `config/simulation_candidate_001.yaml` |
| Verification report | `research/reports/simulation_verification_001.md` |

---

*Report generated: {today}*
*Code revision: {git_rev}*
"""
    out = REPO_ROOT / "research" / "reports" / "simulation_verification_001.md"
    out.write_text(md)
    print(f"  Verification report -> {out}")
    return out


def export_artifacts(
    oos_result: object,
    full_returns: pd.Series,
    full_weights: pd.DataFrame,
) -> None:
    """Export simulation artifacts to parquet."""
    processed_dir = REPO_ROOT / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    # Export daily simulation series (OOS period for paper-trading baseline)
    sim_df = pd.DataFrame({
        "net_return": oos_result.daily_returns,
        "cumulative": (1 + oos_result.daily_returns).cumprod(),
        "drawdown": oos_result.risk_metrics["drawdown"],
        "rolling_vol_63d": oos_result.risk_metrics["rolling_vol_63d"],
        "gross_exposure": oos_result.risk_metrics["gross_exposure"],
        "net_exposure": oos_result.risk_metrics["net_exposure"],
        "n_positions": oos_result.risk_metrics["n_positions"],
    })
    sim_df.index.name = "date"
    sim_path = processed_dir / "simulation_candidate_001.parquet"
    sim_df.to_parquet(sim_path)
    print(f"  Simulation series -> {sim_path}")

    # Export trade log
    trade_log = oos_result.trade_log.copy()
    if not trade_log.empty:
        trade_log.index.name = "date"
    trade_path = processed_dir / "trades_candidate_001.parquet"
    trade_log.to_parquet(trade_path)
    print(f"  Trade log -> {trade_path}")

    # Also export full history weights for reference
    full_weights_path = processed_dir / "weights_full_history.parquet"
    full_weights.to_parquet(full_weights_path)
    print(f"  Full history weights -> {full_weights_path}")


def main():
    print("=" * 60)
    print("CYCLE 7: Simulation Framework & Paper-Trading Preparation")
    print("=" * 60)

    # 1. Full history simulation (verification against backtest)
    full_returns, full_weights, full_metrics = run_simulation_full_history()

    # 2. OOS period simulation (paper-trading baseline)
    _, _, oos_metrics, oos_result = run_simulation_oos_only()

    # 3. Walk-forward simulation
    wf_results = run_walkforward_simulation()

    # 4. Export artifacts
    print("\n=== [4] Exporting Artifacts ===")
    export_artifacts(oos_result, full_returns, full_weights)

    # 5. Write verification report
    print("\n=== [5] Writing Verification Report ===")
    write_verification_report(full_metrics, oos_metrics, wf_results["summary"], oos_result)

    # Final summary
    print("\n" + "=" * 60)
    print("CYCLE 7 COMPLETE")
    print("=" * 60)
    print(f"OOS Sharpe: {oos_metrics['sharpe_ratio']:.4f} (backtest: {BACKTEST_METRICS['test_sharpe']:.4f})")
    print(f"OOS Max DD: {oos_metrics['max_drawdown']:.4f} (backtest: {BACKTEST_METRICS['max_dd']:.4f})")
    print(f"OOS Trades: {oos_metrics['trade_count']} (backtest: {BACKTEST_METRICS['trades']})")
    print(f"WF Mean Sharpe: {wf_results['summary'].get('mean_test_sharpe', np.nan):.4f} (backtest: {BACKTEST_METRICS['wf_mean_oos_sharpe']:.4f})")


if __name__ == "__main__":
    main()