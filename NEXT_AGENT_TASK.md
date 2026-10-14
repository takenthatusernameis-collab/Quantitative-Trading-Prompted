# Next Agent Task: Cycle 33 — Continue Paper Trading Monitoring & Data Acquisition

## Context

Cycle 32 re-attempted data acquisition from Yahoo Finance to extend the paper-trading track record for the incumbent TSMOM strategy (tsmomentum_spytrend_001) beyond the previous date of 2026-10-12. No additional trading days were available; the track record remains at **445 days**.

**Key findings from Cycle 32:**
- All primary go/no-go gates from Cycle 22 still pass: track record 445 days (≫126), Sharpe 2.0404 (≫0.9), max DD -1.59% (≪15%), 6 regime flips (>1)
- **DRIFT FLAG PERSISTS**: `low_rolling_sharpe` triggered on 2026-10-12 continues to be active (rolling 63-day Sharpe = 0.4892 < 0.5 threshold)
- Current regime: Risk-on (SPY ≥ 200-day SMA) for 130 consecutive days
- Data availability: No new trading days were available from Yahoo Finance at fetch time (2026-10-14)

## Objective

Re-attempt data acquisition from Yahoo Finance to extend the paper trading track record further. Monitor the rolling 63-day Sharpe trajectory — if it remains below 0.5 for an extended period (>20 trading days), assess whether the strategy's momentum signal is degrading in the current low-volatility risk-on regime.

## Acceptance Criteria

- [ ] Fetch updated YFinance data for the universe + SPY + ^VIX using `src/data/yfinance_fetcher.py` (force=True) to extend `data/raw/*.parquet` beyond 2026-10-12
- [ ] Update `research/run_paper_trading_replay.py` `end_date` to the latest available data date
- [ ] Re-run `research/run_paper_trading_replay.py` to extend the paper trading track record
- [ ] Verify track record extended (target: any additional trading days; document actual count)
- [ ] Update `research/reports/paper_trading_rolling.md` with latest state
- [ ] Create `research/reports/paper_trading_validation_006.md` with extended validation results
- [ ] Document drift flag status: if `low_rolling_sharpe` persists, analyze trajectory and duration
- [ ] Update README.md with Cycle 33 summary (track record length, last date, NAV, max DD, drift status)
- [ ] Prepare NEXT_AGENT_TASK.md for Cycle 34 (continue monitoring or reassess based on regime stability and drift flag persistence)

## Scope Boundaries

- Fetching new data via yfinance is permitted (existing dependency in requirements.txt); this is data ingestion for research/backtesting only, not live trading
- Do not modify incumbent strategy logic (`config/simulation_candidate_001.yaml` is frozen)
- Report findings honestly: if data fetch fails or new data is unavailable, document the blocker
- Follow AGENTS.md standards
- Research/backtesting only. No live trades, no credential access, no account modifications

## Validation Commands

```bash
# Fetch new data (updates data/raw/*.parquet cache)
python3 -c "
from src.data.yfinance_fetcher import fetch_universe
data = fetch_universe(['SPY','QQQ','IWM','TLT','GLD','EFA','EEM','^VIX'], '1993-01-01', '2026-11-30', force=True)
print('Loaded:', len(data), 'rows,', data.index.min().date(), 'to', data.index.max().date())
"

# Re-run replay
python3 research/run_paper_trading_replay.py 2>&1 | tail -30

# Verify extended state
python3 -c "
import yaml
with open('data/processed/paper_trading_state.yaml') as f:
    s=yaml.safe_load(f)
print('days', len(s['run_history']), 'last', s['last_run_date'], 'nav', s['current_nav'], 'dd', s['max_drawdown'])
print('drift_flags:', s.get('drift_flags', {}))
```