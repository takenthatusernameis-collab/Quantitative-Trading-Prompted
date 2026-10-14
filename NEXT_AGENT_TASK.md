# Next Agent Task: Analyze recent paper trading performance drift (Bounded)

## Context

The paper trading strategy (TSMOM incumbent, simulation_candidate_001) has a drift flag for low rolling Sharpe. The paper trading state (data/processed/paper_trading_state.yaml) shows:
- last_run_date: 2026-07-16
- drift_flags.low_rolling_sharpe.value: 0.3495 (threshold 0.5)
- peak_nav: 139120.07, current_nav: 134844.60, max_dd: -0.03073
- cumulative_returns has 384 values

The microcap hypothesis remains blocked by data infrastructure; other opportunity shortlist hypotheses have been rejected/failed. Strategy is frozen (no logic/parameter changes).

## Objective

Analyze recent paper trading performance to understand the drift flag source without modifying strategy logic. Produce a concise, evidence-backed analysis.

## Acceptance criteria

1. **Performance decomposition:** Examine recent P&L/returns vs prior period; identify when rolling Sharpe declined and magnitude.
2. **Market context:** Brief context on conditions around the flagged period using available data/config.
3. **Strategy mechanics check:** Verify execution per documented specs (config/simulation_candidate_001.yaml) - universe, regime filter, costs, rebalance.
4. **No strategy modifications:** Do not change logic/parameters, do not backtest new variants.
5. **Document findings:** Record observations in research/reports/ with clear summary and evidence references.
6. **Minimal verification:** Run existing tests to ensure nothing is broken.

## Validation commands

```bash
# Inspect paper trading state
cat data/processed/paper_trading_state.yaml

# Inspect strategy config
cat config/simulation_candidate_001.yaml

# Run existing tests
python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v
```

## Scope boundaries

- **No strategy modifications.** Read-only analysis.
- **No new backtests constituting strategy changes.** Do not create new candidate configs.
- **Research/backtesting only.** No live trading.
- **Preserve evidence.** Be precise about what the data shows.
- **Do not fabricate market data.** Work with what exists.

## Completion standard

Concise evidence-backed analysis of recent performance drift including decomposition, market context, strategy mechanics verification, confirmation no modifications made, with references to files inspected and test results.
