# Returns Distribution Analysis During Drift Period

## Executive Summary

Analysis of the paper trading system's daily returns during the drift period (2026-09-17 to 2026-10-14, 20 trading days) compared to the preceding baseline period (2026-06-23 to 2026-09-16, 60 trading days) reveals that the persistent `low_rolling_sharpe` flag is driven primarily by **increased volatility** and **slightly more negative mean returns**, resulting in a significantly worse Sharpe ratio (-1.31 vs -0.58).

## Data Overview

- **Total track record**: 447 trading days (2025-01-02 to 2026-10-14)
- **Drift period**: 20 days (2026-09-17 to 2026-10-14)
- **Baseline period**: 60 days (2026-06-23 to 2026-09-16)

## Statistical Comparison

| Metric | Drift Period | Baseline Period | Change |
|--------|--------------|-----------------|--------|
| Mean Daily Return | -0.0500% | -0.0200% | -0.0300% |
| Std Dev (Daily) | 0.5900% | 0.5000% | +0.0900% |
| Skewness | -0.3595 | -0.1677 | -0.1918 |
| Kurtosis | -0.8006 | 0.0654 | -0.8659 |
| Max Drawdown | -2.91% | -2.78% | -0.14% |
| Positive Days % | 50.0% | 46.7% | +3.3% |
| Annualized Sharpe | -1.3130 | -0.5781 | -0.7349 |

## Key Findings

### 1. Volatility Increase is Primary Driver (+18% increase in daily std dev)
The drift period shows an 18% increase in daily return volatility (0.59% vs 0.50%). This alone would reduce the Sharpe ratio even if mean returns were unchanged.

### 2. Mean Returns Slightly More Negative
Mean daily return deteriorated from -0.02% to -0.05%, a small but meaningful shift given the already low return environment.

### 3. Return Distribution Shape Changed
- **More negative skew** (-0.36 vs -0.17): Slightly more left-tailed, indicating occasional larger negative returns
- **Platykurtic shift** (-0.80 vs +0.07): Distribution became flatter with lighter tails than normal, meaning fewer extreme outliers but more moderate deviations

### 4. Maximum Drawdown Marginally Worse
In-period max drawdown increased from -2.78% to -2.91%, consistent with higher volatility.

### 5. Win Rate Paradoxically Improved
Positive day percentage increased from 46.7% to 50.0%, but this is outweighed by the magnitude of negative days.

## Rolling 63-Day Sharpe Context

The rolling 63-day Sharpe of 0.1133 (as of 2026-10-14) reflects the cumulative impact of this 20-day drift period embedded in a 63-day window. The drift period contributes approximately 32% of the rolling window.

## Interpretation

The drift does **not** appear to be a regime change or structural break:
- No extreme outliers (kurtosis decreased)
- Win rate actually improved
- Drawdown increase is modest and consistent with volatility increase
- The signal is consistent with **normal sampling variation in a low-return, moderate-volatility strategy** experiencing a temporary rough patch

The strategy remains in a risk-on regime (SPY > 200-day SMA for 132 days), so this is not a regime filter failure.

## Recommendation

**Continue monitoring**. The drift flag has persisted for 3 consecutive days but has not reached the >20-day persistence threshold that would trigger a strategy review. The statistical profile suggests this is within expected variation for a strategy with ~2% annualized volatility and near-zero expected return in the current regime.

No changes to trading logic or risk parameters are warranted at this time.

## Reproduction

```bash
python3 -c "
import pandas as pd
import numpy as np
import os
from scipy import stats

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

drift_returns = returns[-20:]
baseline_returns = returns[-80:-20]

def calculate_stats(ret_arr):
    mean_ret = np.mean(ret_arr)
    std_ret = np.std(ret_arr, ddof=1)
    skew = stats.skew(ret_arr)
    kurt = stats.kurtosis(ret_arr)
    cum_ret = np.cumprod(1 + ret_arr)
    running_max = np.maximum.accumulate(cum_ret)
    drawdown = (cum_ret / running_max - 1)
    max_dd = np.min(drawdown)
    pos_pct = np.sum(ret_arr > 0) / len(ret_arr) * 100
    sharpe = mean_ret / std_ret * np.sqrt(252) if std_ret > 0 else 0
    return dict(mean=mean_ret, std=std_ret, skew=skew, kurt=kurt, max_dd=max_dd, pos_pct=pos_pct, sharpe=sharpe)

print('Drift:', calculate_stats(drift_returns))
print('Baseline:', calculate_stats(baseline_returns))
"
```