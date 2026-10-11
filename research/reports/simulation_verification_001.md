# Simulation Verification Report (simulation_verification_001)

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
| Test Sharpe (2018-2026) | 1.4178 | 1.3180 | 0.0998 | FAIL |
| Max DD (2018-2026) | -0.0779 | -0.0993 | 0.0214 | FAIL |
| Trades (2018-2026) | 1196 | 4345 | 3149 | FAIL |
| Ann. Return (2018-2026) | 0.1446 | 0.1347 | 0.0099 | FAIL |
| WF Mean OOS Sharpe | 0.9473 | nan | nan | FAIL |

---

## Full History Simulation (1993-2026)

| Metric | Simulation |
|--------|------------|
| Sharpe | 1.3180 |
| Annualized Return | 0.1347 |
| Max Drawdown | -0.0993 |
| Trades | 4345 |
| Annualized Vol | 0.0870 |
| Sortino | 1.6385 |
| Profit Factor | 1.34 |
| Avg Exposure | 0.5892 |

---

## Walk-Forward Simulation Results

| Metric | Value |
|--------|-------|
| Folds | N/A |
| Mean Test Sharpe | nan |
| Std Test Sharpe | nan |
| Median Test Sharpe | nan |
| Min Test Sharpe | nan |
| Max Test Sharpe | nan |
| % Positive Sharpe Folds | nan% |
| Mean Test Ann. Return | nan% |
| Mean Test Max DD | nan% |
| Mean Test Trades | nan |
| Total Pooled OOS Trades | 0 |

---

## Overall Verification Status

**All tolerance checks passed: NO**

The simulation engine does NOT fully reproduce the backtest results within specified tolerances.

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

*Report generated: 2026-10-11*
*Code revision: 297b41b*
