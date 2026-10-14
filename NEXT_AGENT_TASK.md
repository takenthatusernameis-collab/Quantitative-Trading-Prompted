# Next Agent Task: Continue Paper Trading Monitoring & Data Acquisition (Bounded)

## Context

Cycle 53 (this session) re-attempted data acquisition from Yahoo Finance with `force=True` and `end_date=2026-11-30`. All 7 incumbent ETFs (SPY, QQQ, IWM, TLT, GLD, EFA, EEM) and ^VIX end at 2026-10-14 with real (nonzero volume) data. No data for 2026-10-15 or later is available — the session date is 2026-10-14, so 2026-10-15 has not yet occurred.

The `low_rolling_sharpe` drift flag persists at 3 consecutive days (2026-10-12: 0.4892, 2026-10-13: 0.3669, 2026-10-14: 0.1133), still below the >20-day persistence threshold for strategy review. The returns distribution analysis (`research/reports/returns_distribution_analysis_001.md`) attributes this to an 18% volatility increase and slightly more negative mean returns — consistent with sampling variation, not a structural break.

All primary go/no-go gates pass: track record 447 days (>126), Sharpe 1.9293 (>0.9), max DD -2.93% (<15%), 6 regime flips (>1). Regime unchanged (risk-on, 132 days). Independent verification of rolling 63-day Sharpe confirmed exact match (0.11333136870186329). Tests: 10/10 passed.

**Key note**: The task references `research/fetch_market_data.py` but this file does not exist in the repository. Data fetching uses `src/data/yfinance_fetcher.py` via `fetch_universe()`. The replay script `research/run_paper_trading_replay.py` has `end_date = "2026-10-15"` (line 46) and replay upper bound `"2026-10-14"` (line 53) hardcoded.

The `run_paper_trading_replay.py` script does NOT accept `--end-date` as a CLI argument — it is hardcoded. If a CLI was expected, this is a discrepancy to note.

## Objective

Re-attempt data acquisition from Yahoo Finance and check whether 2026-10-15 (or later) real trading data has arrived for the incumbent ETF universe. If new data is available, extend the paper-trading track record by updating the replay script's `end_date` and upper bound, then re-run the replay and recompute all metrics. If no new data, document the status and continue drift flag monitoring.

## Acceptance Criteria

1. **Fetch updated data**: Run `fetch_universe()` from `src/data/yfinance_fetcher.py` with `force=True`, `end_date=2026-11-30` for universe (SPY, QQQ, IWM, TLT, GLD, EFA, EEM) + ^VIX
2. **Verify data freshness**: Per-symbol parquet end dates; confirm whether 2026-10-15+ data exists
3. **If new data available**:
   - Update `end_date` in `run_paper_trading_replay.py` to capture the new latest date (e.g., `"2026-10-16"` for data through 2026-10-15) and bump the replay upper bound accordingly
   - Re-run `research/run_paper_trading_replay.py`
   - Extend track record and recompute all metrics (NAV, Sharpe, max DD, rolling 63-day Sharpe, regime flips)
   - Update drift flag status
   - Save updated artifacts
4. **If no new data**: Document status in validation report (no replay needed; results are unchanged)
5. **Write validation report** to `research/reports/paper_trading_validation_027.md`
6. **Run tests**: `python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v`

## Validation Commands

```bash
# Fetch updated market data (uses existing yfinance_fetcher infrastructure)
python3 -c "
from src.data.yfinance_fetcher import fetch_universe
data = fetch_universe(['SPY','QQQ','IWM','TLT','GLD','EFA','EEM','^VIX'], '1993-01-01', '2026-11-30', force=True)
print(f'Max date: {data.index.max().date()}')
"

# Check data freshness per symbol
python3 -c "
import pandas as pd, os
for sym in ['SPY','QQQ','IWM','TLT','GLD','EFA','EEM','^VIX']:
    f = f'data/raw/{sym}.parquet'
    if os.path.exists(f):
        df = pd.read_parquet(f)
        print(f'{sym}: {len(df)} rows, max date={df.index.max()}, last vol={df[\"Volume\"].iloc[-1] if \"Volume\" in df.columns else \"N/A\"}')
    else:
        print(f'{sym}: FILE NOT FOUND')
"

# If new data, update replay script end_date and re-run
# (Edit research/run_paper_trading_replay.py: end_date and replay upper bound)
# python3 research/run_paper_trading_replay.py

# Run tests
python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v
```

## Scope Boundaries

- **Monitoring only**: Do not modify trading logic, parameters, or strategy
- **Data acquisition**: Use existing yfinance pipeline only; no new data sources
- **Drift monitoring**: Track rolling 63-day Sharpe trajectory; flag if >20 consecutive days below 0.5
- **No live trading**: Research/backtesting only
- Do not commit unless explicitly requested
- If no new data is available, do NOT fabricate a track record extension or invent metrics
