# Next Agent Task: Cycle 11 - Market Opportunity Inventory & Candidate Scoring

## Context

Cycle 10 successfully validated the go/no-go evaluation framework via historical replay
over the full OOS period (2018-2026). Key findings:

- Framework correctly initializes as INCONCLUSIVE (< 63 days track record)
- PSR converges to 0.5 when paper = backtest (theoretically correct)
- No false GO decisions (PSR never exceeds 0.95 when paper = backtest)
- NO-GO/INCONCLUSIVE oscillation at PSR ≈ 0.5 reflects estimation noise, not true underperformance
- All 59 regime flips correctly detected
- Risk parameters tracked within bounds (vol_scale ∈ [0.437, 1.000], dd_scale = 1.000)
- Decision stability improves with track record length (41 changes over 2,205 days)

**Current Status**: The paper-trading track record has only 5 days (from test data).
Go/no-go decision requires minimum 63 days of prospective paper trading.

---

## Objective

Execute **Phase 1 of Market Opportunity Search** per AGENTS.md: inventory all real data
and costs available in the repository, then build an evidence-based shortlist of
plausible candidates for further research. Score each against the 7 criteria.

This is a **research/discovery task** — not a new backtest. It uses existing
infrastructure to catalog what we can actually test with available data.

---

## Acceptance Criteria

The Cycle 11 work must produce:

### 1. `research/reports/data_inventory.md` — Data & Cost Inventory

Document every data source, frequency, date range, universe, and cost assumption
actually available in the repository:

- **Price data**: symbols, date ranges, OHLCV fields, source, cache location
- **Simulation artifacts**: what series exist (daily returns, weights, risk state, trades)
- **Cost model**: commission, slippage, round-trip bps, funding/borrow if any
- **Execution assumptions**: signal lag, price field (Close/Open), rebalance freq
- **Universe definitions**: all universes used in prior cycles
- **Gaps/limitations**: missing data, survivorship issues, lookahead risks

### 2. `research/reports/opportunity_shortlist.md` — Scored Candidate Shortlist

For each plausible candidate where data supports a valid test, score against
AGENTS.md criteria (a)-(g):

| Candidate | (a) Data Quality | (b) Structural Mech | (c) Net Return | (d) Robustness | (e) Liquidity | (f) Automation | (g) Diversification | Overall | Verdict |
|-----------|------------------|---------------------|----------------|----------------|---------------|----------------|---------------------|---------|---------|

**Candidate categories to evaluate** (non-exhaustive):
- TSMOM variants (different lookbacks, skip, top-fraction, universes)
- Cross-sectional momentum (vs time-series)
- Carry/funding strategies (if futures/perp data available)
- Basis/calendar spread (if futures term structure available)
- Session/time-of-day effects (if intraday data available)
- Rebalancing/calendar effects (month-end, quarter-end, index reconstitution)
- Volatility risk premium (if options data available)
- Macro regime strategies (using existing SPY SMA + other regime indicators)

**Must distinguish**: price predictability vs executable net edge
**Must reject**: candidates explained by bad data, stale prices, survivorship/lookahead bias,
omitted costs, extreme turnover, illiquidity, infeasible execution

### 3. `research/run_cycle11.py` — Inventory & Scoring Script

Script that:
- Programmatically inventories all data in `data/raw/`, `data/processed/`
- Loads cost assumptions from config files
- Generates the two markdown reports above
- Does NOT run new backtests (only catalogs what's testable)

---

## Implementation Notes

### Reuse Existing Infrastructure

- `src/data/yfinance_fetcher.py` — data access layer
- `config/simulation_candidate_001.yaml` — reference cost/execution assumptions
- `data/processed/simulation_candidate_001.parquet` — verified daily series
- `src/evaluation/statistics.py` — statistical test functions (for robustness scoring)
- `src/backtest/engine.py` — backtest engine (for reference, not execution)

### Scope Boundaries

- **In scope**: Data inventory, candidate scoring, documentation
- **Do NOT** run new backtests or simulations
- **Do NOT** add new data dependencies
- **Do** preserve all Cycle 1-10 artifacts
- **Do** follow AGENTS.md "Market Opportunity Search" process exactly

---

## Validation Commands

```bash
# Run Cycle 11 inventory & scoring
python3 research/run_cycle11.py

# Verify outputs created
test -f research/reports/data_inventory.md
test -f research/reports/opportunity_shortlist.md

# Verify reports have expected sections
grep -q "Price Data" research/reports/data_inventory.md
grep -q "Cost Model" research/reports/data_inventory.md
grep -q "Gaps" research/reports/data_inventory.md
grep -q "Candidate" research/reports/opportunity_shortlist.md
grep -q "Overall" research/reports/opportunity_shortlist.md
grep -q "Verdict" research/reports/opportunity_shortlist.md

# Lint
python3 -m ruff check research/run_cycle11.py

# Compile check
python3 -c "import ast; ast.parse(open('research/run_cycle11.py').read())"

# Verify prior cycles still run
python3 research/run_cycle7.py 2>&1 | tail -3
python3 research/run_cycle8.py 2>&1 | tail -3
python3 research/run_cycle9.py 2>&1 | tail -3
python3 research/run_cycle10.py 2>&1 | tail -3
```

---

## Expected Outcome

- Complete data inventory documenting all testable assets, frequencies, costs
- Scored shortlist with 5-10 candidates, each with evidence-based scores
- Clear verdicts: credible candidate / exploratory signal / rejected / blocked by data
- No fabricated metrics — only what existing data can support
- Foundation for Cycle 12 (hypothesis formation for top candidate)

---

## Evidence Reference

- Cycle 7: Simulation verified, test Sharpe 1.4178, OOS period 2018-2026
- Cycle 8: Paper-trading engine operational, daily artifacts produced
- Cycle 9: Go/no-go evaluation framework built, INCONCLUSIVE with 5 days
- Cycle 10: Go/no-go framework historically validated (2,205 daily evaluations)
- `data/processed/simulation_candidate_001.parquet`: 8,482 daily rows, 1993-2026
- `config/simulation_candidate_001.yaml`: frozen candidate with cost model
- AGENTS.md: Market Opportunity Search process (steps 1-6)