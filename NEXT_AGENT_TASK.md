# Next Agent Task: Continue Paper Trading Monitoring & Data Acquisition (Bounded)

## Context

The returns distribution analysis (`research/reports/returns_distribution_analysis_001.md`) confirms the `low_rolling_sharpe` drift flag is driven by an 18% volatility increase and slightly more negative mean returns over the last 20 trading days (2026-09-17 to 2026-10-14). The rolling 63-day Sharpe is 0.1133 (below 0.5 threshold). The drift has persisted for 3 consecutive days but has not reached the >20-day persistence threshold for strategy review.

All primary go/no-go gates still pass:
- Track record: 447 days (>126 minimum)
- Net Sharpe: 1.9302 (>0.9 target)
- Max drawdown: -2.92% (<15% threshold)
- Regime flips: 6 (>1 minimum)
- Current regime: risk-on (132 days)

No new trading data is available beyond 2026-10-14 (yfinance returns 0 rows for 2026-10-15+).

## Objective

Re-attempt data acquisition from Yahoo Finance and continue monitoring the rolling Sharpe trajectory. If new data arrives, extend the paper trading track record and recompute all metrics. If no new data, document the status and persist the drift flag monitoring.

## Acceptance Criteria

1. **Fetch updated data**: Run `research/fetch_market_data.py` (or equivalent) with `force=True`, `end_date=2026-11-30` for 7-ETF universe (SPY, QQQ, IWM, TLT, GLD, EFA, EEM) + SPY + ^VIX
2. **Verify data freshness**: Check per-symbol parquet end dates; confirm whether 2026-10-15+ data exists
3. **If new data available**:
   - Re-run `research/run_paper_trading_replay.py` with updated `end_date`
   - Extend track record and recompute all metrics (NAV, Sharpe, max DD, rolling 63-day Sharpe, regime flips)
   - Update drift flag status
   - Save updated artifacts
4. **If no new data**: Document status in validation report
5. **Write validation report** to `research/reports/paper_trading_validation_XXX.md` (incrementing sequence)
6. **Run tests** to ensure no regressions

## Validation Commands

```bash
# Fetch updated market data
python3 research/fetch_market_data.py --force --end-date 2026-11-30

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

# If new data, run replay (adjust end_date as needed)
# python3 research/run_paper_trading_replay.py --end-date 2026-10-15

# Run tests
python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v
```

## Scope Boundaries

- **Monitoring only**: Do not modify trading logic, parameters, or strategy
- **Data acquisition**: Use existing yfinance pipeline only; no new data sources
- **Drift monitoring**: Track rolling 63-day Sharpe trajectory; flag if >20 consecutive days below 0.5
- **No live trading**: Research/backtesting only
- Do not commit unless explicitly requested

## Completion Standard

- Data fetch attempted and logged
- Per-symbol data freshness verified
- Track record extended if new data available, otherwise status documented
- Validation report written with all metrics and drift flag status
- Tests passing
- No unintended modifications to codebase