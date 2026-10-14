# Next Agent Task: Analyze Returns Distribution During Drift Period (Bounded)

## Context

The drift flag verification confirmed that the `low_rolling_sharpe` detection logic is working correctly, with a rolling 63-day Sharpe of 0.1133 (below the 0.5 threshold) as of 2026-10-14. The README shows this drift flag has persisted for 3 consecutive days (2026-10-12 to 2026-10-14). Understanding the return distribution during this period could provide insights into whether this is a temporary fluctuation or indicative of deeper issues.

## Objective

Analyze the daily returns during the drift period and preceding period to characterize the performance degradation. This will help determine if the low rolling Sharpe is due to:
1. Increased volatility
2. Negative returns
3. Changed return distribution

## Acceptance Criteria

1. **Extract returns data**: Load the daily returns for the paper trading system
2. **Define analysis periods**:
   - Drift period: Last 20 trading days (to capture the persistent drift)
   - Baseline period: Previous 60 trading days (for comparison)
3. **Calculate statistics** for each period:
   - Mean daily return
   - Standard deviation of daily returns
   - Skewness and kurtosis
   - Maximum drawdown within period
   - Percentage of positive/negative days
4. **Compare periods** and identify key differences
5. **Document findings** in `research/reports/returns_distribution_analysis_001.md`
6. **Run relevant tests** to ensure no regressions

## Validation Commands

```bash
# Extract and analyze returns
python3 -c "
import pandas as pd
import numpy as np
import os
from scipy import stats

# Load returns data
paper_trading_dir = 'data/processed/paper_trading'
daily_pnl_files = sorted([f for f in os.listdir(paper_trading_dir) if f.startswith('daily_pnl_') and f.endswith('.parquet')])

returns = []
dates = []
for filename in daily_pnl_files:
    filepath = os.path.join(paper_trading_dir, filename)
    df = pd.read_parquet(filepath)
    returns.append(df['daily_return'].iloc[0])
    dates.append(df['date'].iloc[0])

returns = np.array(returns)
dates = np.array(dates)

print(f'Total returns: {len(returns)} from {dates[0]} to {dates[-1]}')

# Define periods (20 days drift, 60 days baseline)
drift_returns = returns[-20:]
drift_dates = dates[-20:]
baseline_returns = returns[-80:-20:]  # 60 days before drift period
baseline_dates = dates[-80:-20:]

print(f'\\nDrift period: {drift_dates[0]} to {drift_dates[-1]} ({len(drift_returns)} days)')
print(f'Baseline period: {baseline_dates[0]} to {baseline_dates[-1]} ({len(baseline_returns)} days)')

# Calculate statistics
def calculate_stats(ret_arr, name):
    if len(ret_arr) == 0:
        return {}
    mean_ret = np.mean(ret_arr)
    std_ret = np.std(ret_arr, ddof=1)
    skew = stats.skew(ret_arr)
    kurt = stats.kurtosis(ret_arr)
    # Calculate drawdown within period
    cum_ret = np.cumprod(1 + ret_arr)
    running_max = np.maximum.accumulate(cum_ret)
    drawdown = (cum_ret / running_max - 1)
    max_dd = np.min(drawdown)
    pos_pct = np.sum(ret_arr > 0) / len(ret_arr) * 100

    return {
        'mean': mean_ret,
        'std': std_ret,
        'skew': skew,
        'kurt': kurt,
        'max_dd': max_dd,
        'pos_pct': pos_pct,
        'sharpe': mean_ret / std_ret * np.sqrt(252) if std_ret > 0 else 0
    }

drift_stats = calculate_stats(drift_returns, 'drift')
baseline_stats = calculate_stats(baseline_returns, 'baseline')

print('\\n=== DRIFT PERIOD STATISTICS ===')
for k, v in drift_stats.items():
    if k in ['mean', 'std', 'sharpe']:
        print(f'{k:>8}: {v:>8.4f}')
    elif k in ['max_dd']:
        print(f'{k:>8}: {v:>8.2%}')
    elif k in ['pos_pct']:
        print(f'{k:>8}: {v:>8.1f}%')
    else:
        print(f'{k:>8}: {v:>8.4f}')

print('\\n=== BASELINE PERIOD STATISTICS ===')
for k, v in baseline_stats.items():
    if k in ['mean', 'std', 'sharpe']:
        print(f'{k:>8}: {v:>8.4f}')
    elif k in ['max_dd']:
        print(f'{k:>8}: {v:>8.2%}')
    elif k in ['pos_pct']:
        print(f'{k:>8}: {v:>8.1f}%')
    else:
        print(f'{k:>8}: {v:>8.4f}')

print('\\n=== CHANGE (DRIFT - BASELINE) ===')
for k in drift_stats.keys():
    if k in baseline_stats:
        change = drift_stats[k] - baseline_stats[k]
        if k in ['mean', 'std', 'sharpe', 'skew', 'kurt']:
            print(f'{k:>8}: {change:>8.4f}')
        elif k in ['max_dd']:
            print(f'{k:>8}: {change:>8.2%}')
        elif k in ['pos_pct']:
            print(f'{k:>8}: {change:>8.1f}%')
"

# Run tests
python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v
```

## Scope Boundaries

- **Analysis only**: Do not modify trading logic or state
- **Focused scope**: Only analyze returns distribution during drift period
- **Evidence-based**: Use actual returns data from paper trading system
- Do not commit unless explicitly requested

## Completion Standard

- Returns data extracted and periods defined
- Statistics calculated for both periods
- Clear comparison identifying key performance changes
- Analysis report written with actionable insights
- Tests passing
- No unintended modifications to codebase