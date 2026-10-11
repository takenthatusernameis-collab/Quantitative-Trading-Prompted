# Next Agent Task: Cycle 8 - Paper-Trading Prospective Validation

## Context

Cycle 7 successfully built and verified the simulation framework for the validated Credible Candidate. All verification checks passed:

| Validation Check | Result | Threshold | Status |
|------------------|--------|-----------|--------|
| Test-Period Sharpe Diff | 0.000000 | < 0.02 | **PASS** |
| Test-Period Max DD Diff | 0.00% | < 0.5% | **PASS** |
| Test-Period Trade Count Diff | 0 | 0 | **PASS** |
| Walk-Forward Mean OOS Sharpe Diff | 0.000000 | < 0.02 | **PASS** |
| SMA Plateau (6/6 windows >= 0.9) | 6/6 match | 6/6 | **PASS** |
| Determinism | Identical | Identical | **PASS** |

**Final Classification: Simulation Verified** — The SPY trend-filter candidate is confirmed for advancement to paper-trading (prospective) validation.

### Candidate Configuration (Frozen)

- **Universe**: SPY, QQQ, IWM, TLT, GLD, EFA, EEM (7-asset baseline)
- **Signal**: 226-day TSMOM (lookback=226, skip=21, top_fraction=0.5)
- **Risk Overlay**: Combined vol-targeting (10%) + drawdown control (15%)
- **Regime Filter**: SPY 200-day SMA trend filter (0% exposure when SPY < SMA)
- **Cost Model**: 3 bps round-trip (1 bps commission + 2 bps slippage)
- **Execution**: Signal computed on T-1 close, executed at T close (EOD)
- **Rebalancing**: Daily (weights shifted 1 day for point-in-time)

### Evidence Artifacts Produced

- `src/simulation/engine.py` — Simulation engine with `SimulationConfig`, `SimulationResult`, `run_simulation`
- `config/simulation_candidate_001.yaml` — Frozen candidate config (sha256[:12]=3c8f5b899f1f)
- `data/processed/simulation_candidate_001.parquet` — Full-history (1993-2026) daily series
- `data/processed/trades_candidate_001.parquet` — Full-history trade log (13,631 trades)
- `research/reports/simulation_verification_001.md` — Verification report

---

## Objective

Build a **paper-trading (prospective) validation framework** that:
1. Runs the simulation daily with current market data
2. Tracks positions, returns, and risk metrics vs. live market
3. Monitors for signal/regime/risk drift
4. Produces daily artifacts for review
5. Enables a go/no-go decision after 3-6 months of paper track record

This is **NOT live trading** — it is a prospective simulation that uses each day's market data as it becomes available, mimicking real-time execution without lookahead bias.

---

## Acceptance Criteria

The Cycle 8 work must produce:

### 1. `src/simulation/paper_trading.py` — Paper-Trading Engine

A new module with:
- `PaperTradingConfig` dataclass: extends `SimulationConfig` with paper-trading specific params (data refresh schedule, alert thresholds, output directory)
- `PaperTradingState` dataclass: persistent state (last run date, current positions, cumulative metrics, drift flags)
- `run_daily_paper_update(config, state, market_data=None)` → returns updated `PaperTradingState` and daily artifacts:
  - Current target weights (for next execution)
  - Current regime exposure (SPY vs SMA)
  - Current risk overlay state (vol scale, DD scale, drawdown)
  - Daily P&L (mark-to-market on current positions)
  - Drift alerts (signal turnover, regime change, risk parameter drift)
- `generate_paper_report(state, config)` → Markdown report for daily review
- State persistence: JSON/YAML serialization for restart capability

### 2. `research/run_cycle8.py` — Paper-Trading Pipeline

Script that:
- Loads frozen candidate config from `config/simulation_candidate_001.yaml`
- Loads or initializes `PaperTradingState` from `data/processed/paper_trading_state.yaml`
- Fetches latest market data (Yahoo Finance) for universe
- Runs `run_daily_paper_update` to compute today's signals/positions
- Exports daily artifacts to `data/processed/paper_trading/`:
  - `positions_YYYYMMDD.parquet` — target weights for each symbol
  - `regime_YYYYMMDD.parquet` — SPY price, SMA, exposure
  - `risk_state_YYYYMMDD.parquet` — vol_scale, dd_scale, drawdown, exposure
  - `daily_pnl_YYYYMMDD.parquet` — mark-to-market P&L
  - `drift_report_YYYYMMDD.md` — drift alerts and summary
- Updates and persists `PaperTradingState`
- Generates rolling report `research/reports/paper_trading_rolling.md`

### 3. `research/reports/paper_trading_rolling.md` — Rolling Paper-Trading Report

Living document updated daily with:
- **Header**: candidate ID, config hash, start date, last update, days live
- **Current State**: regime (risk-on/risk-off), exposure, vol_scale, dd_scale, current drawdown
- **Positions Table**: symbol, target weight, current price, notional (for $100k notional)
- **Drift Monitoring**: signal turnover vs. history, regime stability, risk parameter stability
- **Performance Tracking**: cumulative paper P&L, Sharpe (rolling 63d), max DD vs. backtest
- **Alerts**: any threshold breaches (regime flip, vol scale > 2x, DD > threshold, etc.)

### 4. `config/paper_trading_config.yaml` — Paper-Trading Configuration

YAML file with operational parameters:
```yaml
candidate_id: "tsmomentum_spytrend_001"
simulation_config: "config/simulation_candidate_001.yaml"
notional_capital: 100000  # USD for position sizing display
data_refresh:
  schedule: "daily"  # or "weekdays"
  timezone: "America/New_York"
  market_close_hour: 16  # 4 PM ET
alert_thresholds:
  regime_flip: true
  vol_scale_max: 2.0
  dd_scale_min: 0.25
  signal_turnover_pct: 0.5  # alert if daily turnover > 50%
  max_drawdown_pct: 0.10  # alert if paper DD exceeds 10%
output_dir: "data/processed/paper_trading"
report_path: "research/reports/paper_trading_rolling.md"
state_path: "data/processed/paper_trading_state.yaml"
go_no_go:
  min_days: 63  # minimum paper track record (3 months)
  target_sharpe: 0.9
  max_dd_threshold: 0.15
```

---

## Implementation Notes

### Paper-Trading vs. Simulation Differences

| Aspect | Simulation (Cycle 7) | Paper-Trading (Cycle 8) |
|--------|---------------------|------------------------|
| Data | Full history, fixed end date | Incremental, expanding window |
| Execution | Historical backfill | Next-day target weights |
| Output | Full time series | Daily snapshots + rolling state |
| Purpose | Verification | Prospective monitoring |
| State | Stateless | Persistent (positions, risk state) |

### Reuse Existing Infrastructure

- `src/simulation.engine.run_simulation` — core logic (import and adapt)
- `src.features.momentum.build_weights` — signal generation
- `src.data.yfinance_fetcher.fetch_universe` — data loading
- `config/simulation_candidate_001.yaml` — frozen candidate params

### New Files to Create

- `src/simulation/paper_trading.py`
- `config/paper_trading_config.yaml`
- `research/run_cycle8.py`
- `data/processed/paper_trading_state.yaml` (created on first run)

---

## Scope Boundaries

- **In scope**: Paper-trading engine, daily update pipeline, drift monitoring, rolling report
- **Do NOT** place live trades or connect to broker APIs
- **Do NOT** add new data dependencies beyond Yahoo Finance
- **Do NOT** modify existing simulation/backtest modules
- **Do** preserve all Cycle 1-7 artifacts

---

## Validation Commands

```bash
# Run Cycle 8 paper-trading update (idempotent, safe to run daily)
python3 research/run_cycle8.py

# Verify artifacts created
test -f data/processed/paper_trading_state.yaml
test -d data/processed/paper_trading
ls data/processed/paper_trading/ | head -5
test -f research/reports/paper_trading_rolling.md

# Verify rolling report has expected sections
grep -q "Current State" research/reports/paper_trading_rolling.md
grep -q "Positions Table" research/reports/paper_trading_rolling.md
grep -q "Drift Monitoring" research/reports/paper_trading_rolling.md
grep -q "Performance Tracking" research/reports/paper_trading_rolling.md

# Lint
python3 -m ruff check research/run_cycle8.py src/simulation/paper_trading.py

# Compile check
python3 -c "import ast; ast.parse(open('research/run_cycle8.py').read())"
python3 -c "import ast; ast.parse(open('src/simulation/paper_trading.py').read())"

# Verify prior cycles still run
python3 research/run_cycle5.py 2>&1 | tail -1
python3 research/run_cycle6.py 2>&1 | tail -1
python3 research/run_cycle7.py 2>&1 | tail -3
```

---

## Expected Outcome

- Paper-trading engine runs daily without errors
- Daily artifacts produced in `data/processed/paper_trading/`
- Rolling report updated with current state, positions, drift alerts, performance
- State persisted for restart capability
- After 63+ days (3 months), go/no-go criteria can be evaluated:
  - Paper Sharpe >= 0.9 (rolling 63d)
  - Paper max DD <= 15%
  - No structural drift detected (regime filter stable, signal turnover normal)
  - Risk overlay parameters within historical ranges

---

## Evidence Reference

- Cycle 7 verification: all checks PASS, zero diff vs. backtest
- Cycle 6 walk-forward: mean OOS Sharpe 0.9473, 91.7% positive folds, 6013 trades
- Cycle 6 plateau: 6/6 SMA windows (150, 175, 200, 226, 250, 277) achieve Sharpe >= 0.9
- Cycle 5 promotion gate: SPY trend filter test Sharpe 1.4178, max DD -7.79%, 1196 trades

---