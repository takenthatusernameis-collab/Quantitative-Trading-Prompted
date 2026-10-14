# Next Agent Task: Cycle 36 — Continue Paper Trading Monitoring & Data Acquisition

## Context

Cycle 35 re-attempted data acquisition from Yahoo Finance to extend the paper-trading track record for the incumbent TSMOM strategy (`tsmomentum_spytrend_001`) beyond the previous date of 2026-10-12.

**Key findings from Cycle 35:**
- Fetch with `force=True` and end_date 2026-11-30 was executed successfully; all 7 incumbent ETFs (SPY, QQQ, IWM, TLT, GLD, EFA, EEM) now end at **2026-10-13** (one new trading day beyond 2026-10-12), ^VIX also ends at 2026-10-13.
- **However**, the replay's `force=True` re-fetch overwrote the raw cache during the replay run, and the final cached parquet files end at **2026-10-12** (445 rows each). The replay therefore processed **445 trading days** (2025-01-02 → 2026-10-12), the maximum achievable with current data.
- Track record **reproduced exactly**: NAV **$136,905.02** (+36.91%), max DD **-1.59%**, Sharpe **2.0404**, rolling 63-day Sharpe **0.4892**.
- **DRIFT FLAG PERSISTS**: `low_rolling_sharpe` on 2026-10-12 (0.4892 < 0.5 threshold). Duration remains at 1 day since no net-new trading days were added to the replay.
- All primary go/no-go gates from Cycle 22 still pass: track record 445 days (≫126), Sharpe 2.0404 (≫0.9), max DD -1.59% (≪15%), 6 regime flips (>1).
- Current regime: Risk-on (SPY ≥ 200-day SMA) for 130 consecutive days.
- Data integrity verified: all 7 incumbent ETF parquet files end at 2026-10-12; ^VIX ends at 2026-10-13 (8,505 rows, 1993-01-04 → 2026-10-13).

## Objective

Re-attempt data acquisition from Yahoo Finance to extend the paper trading track record further. Monitor the rolling 63-day Sharpe trajectory — if it remains below 0.5 for an extended period (>20 trading days), assess whether the strategy's momentum signal is degrading in the current low-volatility risk-on regime.

## Acceptance Criteria

- [ ] Fetch updated YFinance data for the universe + SPY + ^VIX using `src/data/yfinance_fetcher.py` (force=True) to extend `data/raw/*.parquet` beyond 2026-10-12
- [ ] Update `research/run_paper_trading_replay.py` `end_date` to the latest available data date
- [ ] Re-run `research/run_paper_trading_replay.py` to extend the paper trading track record
- [ ] Verify track record extended (target: any additional trading days; document actual count)
- [ ] Update `research/reports/paper_trading_rolling.md` with latest state
- [ ] Create `research/reports/paper_trading_validation_009.md` with extended validation results
- [ ] Document drift flag status: if `low_rolling_sharpe` persists, analyze trajectory and duration
- [ ] Update README.md with Cycle 36 summary (track record length, last date, NAV, max DD, drift status)
- [ ] Prepare NEXT_AGENT_TASK.md for Cycle 37 (continue monitoring or reassess based on regime stability and drift flag persistence)

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
"
```