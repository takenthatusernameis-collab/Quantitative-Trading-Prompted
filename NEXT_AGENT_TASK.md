# Next Agent Task: Cycle 10 - Go/No-Go Framework Historical Validation

## Context

Cycle 9 successfully built and verified the go/no-go evaluation framework. All verification checks passed:

- `src/simulation/evaluation.py` — Go/No-Go evaluation module with `GoNoGoConfig`, `GoNoGoResult`, `evaluate_go_no_go`, `generate_evaluation_report`
- `research/run_cycle9.py` — Daily evaluation pipeline
- `research/reports/go_no_go_evaluation_001.md` — Evaluation report with all required sections (Backtest Baseline, Paper Performance, Statistical Comparison, Drift Assessment, Decision)
- Enhanced drift monitoring in `src/simulation/paper_trading.py`:
  - Rolling 63-day Sharpe calculation in state (`rolling_sharpe_63d`)
  - Rolling 63-day max DD in state (`rolling_max_dd_63d`)
  - Regime persistence counter (`regime_persistence_days`)
  - Signal turnover distribution tracking (`turnover_median`, `turnover_p95`)
  - Risk parameter bounds tracking (`vol_scale_min/max`, `dd_scale_min/max`)
  - Drift alerts for: rolling Sharpe < 0.5, regime persistence < 5 days after flip, vol_scale > 2.5, dd_scale < 0.2

**Current Status**: The paper-trading track record has only 5 days (all from 2026-10-09 due to test data). Go/no-go decision is INCONCLUSIVE as expected (minimum 63 days required).

---

## Objective

Build a **historical validation** of the go/no-go framework by simulating paper-trading day-by-day over the full backtest period (2018-2026), producing a time series of go/no-go evaluations. This validates that:

1. The framework correctly identifies GO decisions when paper performance matches backtest
2. The framework correctly identifies NO-GO when performance degrades
3. Drift monitoring detects regime flips and risk parameter excursions
4. The statistical comparison (PSR vs backtest Sharpe) behaves as expected

This is a **one-time historical validation** — not a new paper-trading run. It uses the verified simulation engine (Cycle 7) to replay daily paper updates and evaluate go/no-go at each step.

---

## Acceptance Criteria

The Cycle 10 work must produce:

### 1. `research/run_cycle10.py` — Historical Go/No-Go Validation Script

Script that:
- Loads the frozen candidate config from `config/simulation_candidate_001.yaml`
- Loads the verified simulation daily series from `data/processed/simulation_candidate_001.parquet` (8,482 days, 1993-2026)
- Simulates day-by-day paper-trading from 2018-01-01 to 2026-10-09 (OOS period matching Cycle 7)
- At each day, runs `evaluate_go_no_go` with accumulating track record
- Records: date, track record length, paper Sharpe, PSR, decision, drift flags
- Outputs time-series CSV: `data/processed/go_no_go_history.parquet`
- Outputs summary markdown: `research/reports/go_no_go_historical_validation.md`

### 2. `data/processed/go_no_go_history.parquet` — Time Series of Evaluations

Columns:
- `date`: evaluation date
- `track_record_days`: cumulative paper trading days
- `paper_sharpe`: rolling paper Sharpe
- `paper_max_dd`: rolling paper max DD
- `psr_normal`: probabilistic Sharpe ratio (normal)
- `psr_empirical`: probabilistic Sharpe ratio (empirical)
- `decision`: GO / NO-GO / INCONCLUSIVE
- `regime_stable`: boolean
- `regime_persistence_days`: integer
- `vol_scale_min`, `vol_scale_max`: bounds
- `dd_scale_min`, `dd_scale_max`: bounds
- `turnover_median`, `turnover_p95`: distribution
- `drift_flags_count`: integer

### 3. `research/reports/go_no_go_historical_validation.md` — Validation Report

Sections:
- **Overview**: methodology, data period, candidate
- **Decision Timeline**: table showing first GO date, any NO-GO dates, final decision
- **PSR Evolution**: chart/table of PSR over time, crossing thresholds
- **Drift Events**: all regime flips, risk parameter breaches, low Sharpe alerts
- **Statistical Properties**: fraction of days INCONCLUSIVE/GO/NO-GO, median days to GO
- **Comparison to Backtest**: does framework correctly validate the known-good candidate?
- **Conclusion**: framework validated / issues found

---

## Implementation Notes

### Reuse Existing Infrastructure

- `src/simulation/evaluation.evaluate_go_no_go` — core evaluation function
- `src/simulation/paper_trading.PaperTradingState` — state management (adapt for historical replay)
- `src/simulation/engine.run_simulation` — verified simulation engine (Cycle 7)
- `data/processed/simulation_candidate_001.parquet` — verified daily series (8,482 rows)
- Cycle 7 baseline metrics: test Sharpe 1.4178, max DD -7.79%, 1196 trades

### Historical Replay Approach

The simulation daily series already contains all daily net returns, weights, risk state, regime exposure.
Instead of re-running the engine daily (slow), extract the OOS period (2018-2026) from the parquet and feed daily returns into a lightweight PaperTradingState accumulator, then call `evaluate_go_no_go` at each step.

### Scope Boundaries

- **In scope**: Historical replay script, time-series output, validation report
- **Do NOT** modify `src/simulation/evaluation.py` or `src/simulation/paper_trading.py` unless bug found
- **Do NOT** add new data dependencies
- **Do** preserve all Cycle 1-9 artifacts

---

## Validation Commands

```bash
# Run Cycle 10 historical validation
python3 research/run_cycle10.py

# Verify outputs created
test -f data/processed/go_no_go_history.parquet
test -f research/reports/go_no_go_historical_validation.md

# Verify parquet has expected columns
python3 -c "
import pandas as pd
df = pd.read_parquet('data/processed/go_no_go_history.parquet')
print('Rows:', len(df))
print('Cols:', list(df.columns))
print('Date range:', df['date'].min(), 'to', df['date'].max())
print('Decisions:', df['decision'].value_counts().to_dict())
"

# Verify report has expected sections
grep -q "Decision Timeline" research/reports/go_no_go_historical_validation.md
grep -q "PSR Evolution" research/reports/go_no_go_historical_validation.md
grep -q "Drift Events" research/reports/go_no_go_historical_validation.md
grep -q "Comparison to Backtest" research/reports/go_no_go_historical_validation.md
grep -q "Conclusion" research/reports/go_no_go_historical_validation.md

# Lint
python3 -m ruff check research/run_cycle10.py

# Compile check
python3 -c "import ast; ast.parse(open('research/run_cycle10.py').read())"

# Verify prior cycles still run
python3 research/run_cycle7.py 2>&1 | tail -3
python3 research/run_cycle8.py 2>&1 | tail -3
python3 research/run_cycle9.py 2>&1 | tail -3
```

---

## Expected Outcome

- Historical validation runs without errors on full OOS period (2018-2026)
- Time-series parquet produced with ~2,200 daily evaluations
- Framework correctly transitions from INCONCLUSIVE to GO after ~63 days and stays GO
- Drift events match known regime flips (SPY SMA crosses) and risk overlay behavior
- PSR converges toward 1.0 as track record lengthens
- Validation report documents all findings
- All prior cycles (1-9) continue to pass

---

## Evidence Reference

- Cycle 7: Simulation verified, test Sharpe 1.4178, OOS period 2018-2026
- Cycle 8: Paper-trading engine operational, daily artifacts produced
- Cycle 9: Go/no-go evaluation framework built, INCONCLUSIVE with 5 days
- `data/processed/simulation_candidate_001.parquet`: 8,482 daily rows, 1993-2026
- Backtest baseline: Sharpe 1.4178, max DD -7.79%, 1196 trades, turnover 13.32

---