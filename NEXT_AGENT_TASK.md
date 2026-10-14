# Next Agent Task: Continue Paper Trading Monitoring & Data Acquisition (Bounded)

## Context

The paper trading drift analysis (`research/reports/paper_trading_drift_analysis_001.md`) confirms:
- Low rolling Sharpe (0.3495 vs 0.5 threshold) triggered on 2026-07-16 — **1 day duration**
- Root cause: concentrated drawdown cluster in Jun–Jul 2026 during risk-on regime
- Strategy mechanics verified against frozen config (`config/simulation_candidate_001.yaml`) — **no deviations**
- No strategy modifications made or warranted
- >20-day persistence threshold for action **not met**

All primary go/no-go gates still pass (track record 384 > 126, full-period Sharpe > 0.9, max DD -3.07% < 15%, regime flips observed). Strategy remains frozen.

## Objective

Re-attempt data acquisition from Yahoo Finance to extend the paper trading track record beyond 2026-07-16. Re-run deterministic replay if new trading days are available. Continue monitoring rolling Sharpe trajectory.

## Acceptance Criteria

1. **Data fetch:** Run `research/run_paper_trading_replay.py` with `force=True` to refresh raw parquet cache from Yahoo Finance
2. **Replay execution:** If new trading days exist beyond 2026-07-16, extend the track record deterministically
3. **Drift monitoring:** Record rolling 63-day Sharpe and drift flag status (duration, value)
4. **Gate verification:** Confirm all primary go/no-go gates still pass
5. **Artifacts:** Update `data/processed/paper_trading_state.yaml`, `research/reports/paper_trading_rolling.md`, and create `research/reports/paper_trading_validation_XXX.md`
6. **No strategy changes:** Do not modify config, logic, or parameters

## Validation Commands

```bash
# Fetch new data and replay
python3 research/run_paper_trading_replay.py --force --end-date 2026-11-30

# Inspect updated state
cat data/processed/paper_trading_state.yaml

# Check rolling Sharpe report
cat research/reports/paper_trading_rolling.md
```

## Scope Boundaries

- **No strategy modifications.** Read-only analysis and replay only.
- **No new backtests constituting strategy changes.** Do not create new candidate configs.
- **Research/backtesting only.** No live trading.
- **Preserve evidence.** Be precise about what the data shows.
- **Do not fabricate market data.** Work with what Yahoo Finance provides.

## Completion Standard

Updated paper trading state with extended track record (if new data available) or confirmed current state (if no new data), including rolling Sharpe trajectory, drift flag status, gate verification, and evidence references.