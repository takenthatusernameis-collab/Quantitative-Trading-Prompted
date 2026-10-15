# Next Agent Task: Verify ETF OHLCV Data Pipeline

## Context
The microcap mom121 hypothesis remains blocked by lack of point-in-time microcap market cap and shares outstanding data (see `research/experiments/mom121_datagate_survey.md`). However, the repository maintains a functional ETF OHLCV data pipeline via yfinance, caching data to `data/raw/` as parquet files. This pipeline is used by existing strategies (e.g., paper trading, sector rotation, time-series momentum). Ensuring its reliability is a prerequisite for any research that depends on ETF data.

## Objective
Verify that the existing yfinance-based data ingestion pipeline for ETF OHLCV data functions correctly and produces cached parquet files with the expected schema. This task is narrow, testable, and does not require new dependencies or data sources.

## Acceptance Criteria
1. **Data fetch succeeds**: Running the YFinanceFetcher for the configured ETF symbols does not throw exceptions and returns a non-empty DataFrame.
2. **Cache files created**: Parquet files are written to `data/raw/` for each ETF symbol with correct naming.
3. **Schema validation**: Each cached parquet file contains columns ['Open', 'High', 'Low', 'Close', 'Volume'] and a timezone-aware UTC DatetimeIndex.
4. **Data integrity**: No missing values in the Open, High, Low, Close columns for traded days (missing values allowed only for non-trading days due to calendar alignment).
5. **Feature computation pipeline works**: The fetched data can be used to compute momentum and factor weights using existing functions.

## Validation Commands
```bash
# 1. Run the data fetcher for a small subset of ETFs and verify output
python3 -c "
from src.data.yfinance_fetcher import fetch_universe
symbols = ['SPY', 'QQQ', 'IWM']
df = fetch_universe(symbols, start_date='2024-01-01', end_date='2024-12-31')
print('Fetched DataFrame shape:', df.shape)
print('Columns:', df.columns.tolist())
print('Index timezone:', df.index.tz)
print('First 5 rows:\\n', df.head())
assert df.shape[0] > 0, 'Empty DataFrame'
assert set(['Open', 'High', 'Low', 'Close', 'Volume']) == set(df.columns.levels[0]), 'Missing OHLCV columns'
assert df.index.tz is not None, 'Index not timezone-aware'
print('Data fetch test PASSED')
"

# 2. Check cached parquet files exist and are readable
python3 -c "
import os
from src.data.yfinance_fetcher import YFinanceFetcher
import pandas as pd
symbols = ['SPY', 'QQQ', 'IWM']
fetcher = YFinanceFetcher(symbols=symbols, start_date='2024-01-01', end_date='2024-12-31')
for sym in symbols:
    path = fetcher._cache_path(sym)
    assert os.path.exists(path), f'Missing cache file for {sym}'
    df = pd.read_parquet(path)
    assert not df.empty, f'Empty cache for {sym}'
    assert set(df.columns) == {'Open', 'High', 'Low', 'Close', 'Volume'}, f'Wrong columns for {sym}'
    assert df.index.tz is not None, f'Index not timezone-aware for {sym}'
    print(f'Cache file for {sym} OK: {df.shape}'
)"