# Next Agent Task: Sync paper_trading_state.yaml with latest replay data (Bounded)

## Context

The drift flag analysis (research/reports/paper_trading_drift_analysis_001.md)
found the `low_rolling_sharpe` drift flag (value 0.3495 on 2026-07-16, threshold
0.5) is **not** a strategy malfunction — it is market-driven. GLD (-11.3%),
EEM (-8.4%), and QQQ (-5.0%) declined June-July 2026 while the SPY SMA200 regime
filter stayed risk-on. The strategy mechanics were verified correct per
config/simulation_candidate_001.yaml.

The full analysis report shows the state YAML is stale: it records 384 days
through 2026-07-16, but daily P&L parquet files extend to 2026-10-14 (447 days).
The first 384 daily returns match exactly, so the state was partially generated
by the same replay but not updated after the later runs described in README.md
(Cycle 48–52, 447 days through 2026-10-14, rolling Sharpe 0.1185).

## Objective

Synchronize `data/processed/paper_trading_state.yaml` with the latest replay
artifacts so the drift flag is evaluated against complete data, then re-assess
the drift flag status.

## Acceptance Criteria

1. **State sync**: Re-run `research/run_paper_trading_replay.py` (or rebuild
   state from existing daily P&L parquet files if yfinance unavailable) so that
   `last_run_date`, `cumulative_returns`, `run_history`, and summary metrics
   reflect all 447 days through 2026-10-14.
2. **Drift flag re-evaluation**: After sync, confirm `last_run_date` = 2026-10-14,
   `cumulative_returns` count = 447, and recompute rolling 63-day Sharpe at the
   final date.
3. **No strategy modifications**: Do not change `config/simulation_candidate_001.yaml`
   or any simulation logic. Only regenerate state metrics.
4. **Verify consistency**: State file's `peak_nav`, `current_nav`, and `rolling_sharpe_63d`
   must match the daily P&L parquet files (`data/processed/paper_trading/daily_pnl_*.parquet`).
5. **Document outcome**: Record sync results and any discrepancies in
   `research/reports/paper_trading_state_sync_001.md`.
6. **Run existing tests**: `python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v`

## Validation Commands

```bash
# Verify latest daily P&L date
ls data/processed/paper_trading/daily_pnl_*.parquet | wc -l
ls data/processed/paper_trading/daily_pnl_20261014.parquet

# Sync state by re-running replay
python3 research/run_paper_trading_replay.py

# Verify synced state
python3 -c "
import yaml
with open('data/processed/paper_trading_state.yaml') as f:
    s = yaml.safe_load(f)
print('last_run_date:', s['last_run_date'])
print('cum_returns:', len(s['cumulative_returns']))
print('peak_nav:', s.get('peak_nav'))
print('current_nav:', s.get('current_nav'))
print('rolling_sharpe_63d:', s.get('rolling_sharpe_63d'))
print('drift_flags:', s.get('drift_flags'))
"

# Run tests
python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v
```

## Scope Boundaries

- **No strategy modifications.** Only regenerate state metrics from existing data.
- **No new backtests.** Re-run the same replay with the same config.
- **Research/backtesting only.** No live trading.
- If yfinance network fetch fails, fall back to rebuilding state from existing
  daily P&L parquet files without re-fetching.
- Do not commit unless explicitly requested.

## Completion Standard

State file synchronized to 447 days through 2026-10-14, drift flag re-evaluated
with complete data, consistency verified against parquet files, test suite passing,
findings documented.
