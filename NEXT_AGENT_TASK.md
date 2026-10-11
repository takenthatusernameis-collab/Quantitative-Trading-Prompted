# Next Agent Task: Cycle 7 - Simulation Framework & Paper-Trading Preparation

## Context

Cycle 6 validated the SPY Trend Filter candidate via two independent checks:

### Cycle 6 Key Findings

| Validation Check | Result | Threshold | Status |
|------------------|--------|-----------|--------|
| Walk-Forward Mean OOS Sharpe | 0.9473 | >= 0.9 | **PASS** |
| % Positive WF Folds | 91.7% | >= 50% | **PASS** |
| SMA Plateau (windows >= 0.9) | 6/6 | >= 2/6 | **PASS** |

**Final Classification: Credible Candidate** — The SPY trend-filter candidate is confirmed for advancement to simulation/paper-trading.

### Candidate Configuration (Validated)

- **Universe**: SPY, QQQ, IWM, TLT, GLD, EFA, EEM (7-asset baseline)
- **Signal**: 226-day TSMOM (lookback=226, skip=21, top_fraction=0.5)
- **Risk Overlay**: Combined vol-targeting (10%) + drawdown control (15%)
- **Regime Filter**: SPY 200-day SMA trend filter (0% exposure when SPY < SMA)
- **Cost Model**: 3 bps round-trip (1 bps commission + 2 bps slippage)
- **Rebalancing**: Monthly (weights shifted 1 day for point-in-time)

### Evidence Artifacts Produced

- `research/experiments/tsmomentum_regime_filter_wf_001.md` — Walk-forward + plateau validation
- `research/run_cycle6.py` — Cycle 6 pipeline script

---

## Objective

Build a **simulation framework** for the validated Credible Candidate and prepare for **paper-trading (prospective) validation**. The simulation must:

1. Reproduce the candidate strategy with exact same logic as backtest
2. Support walk-forward re-optimization (if desired) and fixed-parameter execution
3. Generate realistic position/time series for paper-trading tracking
4. Include operational constraints: transaction costs, slippage, position limits, rebalancing schedule
5. Produce daily P&L, positions, risk metrics, and trade logs suitable for prospective monitoring

---

## Acceptance Criteria

The Cycle 7 work must produce:

### 1. `src/simulation/engine.py` — Simulation Engine

A new module with:
- `SimulationConfig` dataclass: universe, signal params, risk overlay params, regime filter params, cost model, rebalancing schedule, position sizing
- `run_simulation(config, start_date, end_date)` → returns `SimulationResult` with:
  - Daily net returns, positions, weights, turnover, costs
  - Trade log (date, symbol, side, quantity, price, cost)
  - Risk metrics (daily vol, VaR, drawdown, exposure)
  - Rebalancing events
- Point-in-time execution: signal computed on T-1 close, executed T open (or T close for EOD)
- Deterministic: same inputs → same outputs (seedable)

### 2. `research/run_cycle7.py` — Simulation Pipeline

Script that:
- Instantiates the validated candidate config
- Runs simulation on **full history** (1993-2026) for verification against backtest
- Runs simulation on **OOS period only** (2018-2026) for paper-trading baseline
- Exports daily position/return series to `data/processed/simulation_candidate_001.parquet`
- Exports trade log to `data/processed/trades_candidate_001.parquet`
- Verifies simulation matches backtest within tolerance (Sharpe diff < 0.02, DD diff < 0.5%)

### 3. `research/reports/simulation_verification_001.md` — Verification Report

| Metric | Backtest (Cycle 5/6) | Simulation | Diff | Status |
|--------|---------------------|------------|------|--------|
| Test Sharpe (2018-2026) | 1.4178 | — | — | PASS/FAIL |
| Max DD (2018-2026) | -7.79% | — | — | PASS/FAIL |
| Trades (2018-2026) | 1,196 | — | — | PASS/FAIL |
| Ann. Return (2018-2026) | 14.46% | — | — | PASS/FAIL |
| WF Mean OOS Sharpe | 0.9473 | — | — | PASS/FAIL |

### 4. `config/simulation_candidate_001.yaml` — Frozen Candidate Config

YAML file capturing all parameters for reproducible simulation/paper-trading:
```yaml
candidate_id: "tsmomentum_spytrend_001"
universe: ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"]
signal:
  type: "tsmomentum"
  lookback: 226
  skip: 21
  top_fraction: 0.5
  rebalance_freq: "monthly"
risk_overlay:
  vol_target: 0.10
  vol_lookback: 63
  max_leverage: 1.0
  dd_control:
    threshold: 0.15
    reduction: 0.5
regime_filter:
  type: "spy_sma"
  window: 200
  exposure_below: 0.0
  exposure_above: 1.0
cost_model:
  commission_bps: 1.0
  slippage_bps: 2.0
  total_round_trip_bps: 3.0
execution:
  signal_lag_days: 1
  price_field: "Open"  # or "Close" for EOD
  timezone: "UTC"
```

---

## Implementation Notes

### Simulation vs Backtest Differences to Handle

| Aspect | Backtest (Current) | Simulation (New) |
|--------|-------------------|------------------|
| Execution price | Close-to-Close | Open-to-Close (or configurable) |
| Signal lag | 1 day (shift) | Explicit T-1 → T |
| Position sizing | Equal-weight top fraction | Equal-weight with vol/DD scaling |
| Rebalancing | Monthly (implicit) | Explicit calendar schedule |
| Costs | Weight-change * bps | Per-trade commission + slippage |
| Output | Aggregate metrics | Full time-series + trade log |

### Reuse Existing Infrastructure

- `src/features/momentum.build_weights` — signal generation
- `src/evaluation/utils.fetch_close_prices` — data loading
- `src/backtest.engine.compute_metrics` — metrics computation
- Cycle 5/6 `_apply_overlay` logic — risk overlay + regime filter

### New Files to Create

- `src/simulation/__init__.py`
- `src/simulation/engine.py`
- `config/simulation_candidate_001.yaml`
- `research/run_cycle7.py`

---

## Scope Boundaries

- **In scope**: Simulation engine, verification against backtest, paper-trading config export
- **Do NOT** place live trades or connect to broker APIs
- **Do NOT** add new data dependencies (Yahoo Finance only)
- **Do NOT** modify existing backtest/evaluation modules (only import from them)
- **Do** preserve all Cycle 1-6 artifacts

---

## Validation Commands

```bash
# Run Cycle 7 simulation pipeline
python3 research/run_cycle7.py

# Verify simulation matches backtest
python3 -c "
import pandas as pd
sim = pd.read_parquet('data/processed/simulation_candidate_001.parquet')
print('Simulation rows:', len(sim))
print('Date range:', sim.index.min(), 'to', sim.index.max())
"

# Verify prior cycles still run
python3 research/run_cycle3.py 2>&1 | tail -3
python3 research/run_cycle4.py 2>&1 | tail -3
python3 research/run_cycle5.py 2>&1 | tail -3
python3 research/run_cycle6.py 2>&1 | tail -5

# Lint
python3 -m ruff check research/run_cycle7.py src/simulation/

# Compile check
python3 -c "import ast; ast.parse(open('research/run_cycle7.py').read())"

# Artifact existence
test -f src/simulation/engine.py
test -f config/simulation_candidate_001.yaml
test -f data/processed/simulation_candidate_001.parquet
test -f data/processed/trades_candidate_001.parquet
test -f research/reports/simulation_verification_001.md

# Content checks
grep -q "PASS" research/reports/simulation_verification_001.md
grep -q "tsmomentum_spytrend_001" config/simulation_candidate_001.yaml
```

---

## Expected Outcome

- Simulation engine produces results **within tolerance** of backtest (Sharpe diff < 0.02)
- All artifacts created and verified
- Next cycle (Cycle 8) can begin **paper-trading prospective validation**:
  - Daily simulation runs with current market data
  - Position/return tracking vs live market
  - Drift monitoring (signal, risk, regime filter)
  - Go/No-go decision after 3-6 months paper track record

---

## Evidence Reference

- Cycle 6 walk-forward: mean OOS Sharpe 0.9473, 91.7% positive folds, 6013 trades
- Cycle 6 plateau: 6/6 SMA windows (150, 175, 200, 226, 250, 277) achieve Sharpe >= 0.9
- Cycle 5 promotion gate: SPY trend filter test Sharpe 1.4178, max DD -7.79%, 1196 trades
- Cycle 4 best combined overlay (corrected 3 bps): Sharpe 0.7458
- Cycle 3 walk-forward baseline: mean test Sharpe 0.679, 97.9% positive folds

---