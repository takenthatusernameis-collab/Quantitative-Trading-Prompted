# Next Agent Task: Cycle 31 — Extend Paper Trading Track Record with New Data

## Context

Cycle 30 ran a reproducibility check of the incumbent TSMOM strategy (tsmomentum_spytrend_001). The replay script (`research/run_paper_trading_replay.py`) was executed on cached data only (no new fetching), reproducing the 444-day track record exactly (2025-01-02 to 2026-10-09, NAV $137,376.42, Sharpe 2.0686, max DD -1.25%, 6 regime flips, no drift flags). All go/no-go gates from Cycle 22 remain passing.

**Key blocker identified in Cycle 30:** Cached raw data (`data/raw/*.parquet` for SPY, QQQ, IWM, TLT, GLD, EFA, EEM, ^VIX`) is exhausted at **2026-10-09**. The track record already covers all available cached trading days. The objective of extending by 20 additional trading days could not be met with cached data only. The incumbent remains in "ready" state pending new data acquisition.

## Objective

Acquire new market data for the 7-ETF universe + SPY beyond 2026-10-09, update the replay script's end_date to the latest available data, and re-run the replay to extend the paper trading track record by at least 20 additional trading days (target: >= 464 total days).

## Acceptance Criteria

- [ ] Fetch updated YFinance data for the universe + SPY using the existing `src/data/yfinance_fetcher.py` (force=True) to extend `data/raw/*.parquet` beyond 2026-10-09
- [ ] Update `research/run_paper_trading_replay.py` `end_date` to the latest available data date
- [ ] Re-run `research/run_paper_trading_replay.py` to extend the paper trading track record
- [ ] Verify track record extended by at least 20 trading days (target: >= 464 days)
- [ ] Update `research/reports/paper_trading_rolling.md` with latest state
- [ ] Create `research/reports/paper_trading_validation_004.md` with extended validation results
- [ ] Verify no drift flags triggered; document any flags with analysis if triggered
- [ ] Update README.md with Cycle 31 summary (track record length, last date, NAV, max DD)
- [ ] Prepare NEXT_AGENT_TASK.md for Cycle 32 (continue monitoring or reassess based on regime stability)

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
data = fetch_universe(['SPY','QQQ','IWM','TLT','GLD','EFA','EEM','^VIX'], '1993-01-01', '2026-10-20', force=True)
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
"
```
