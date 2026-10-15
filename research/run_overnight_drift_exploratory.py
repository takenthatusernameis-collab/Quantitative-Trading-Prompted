#!/usr/bin/env python3
"""
Overnight Drift Exploratory Diagnostic
=======================================
Loads daily OHLCV for all 19 symbols from data/raw/, computes overnight/intraday/total
returns, and produces a summary report. This is an EXPLORATORY DIAGNOSTIC ONLY — no
alpha claims are made.
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Add src to path for any utility imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

RAW_DIR = Path('data/raw')
OUTPUT_PATH = Path('research/experiments/overnight_drift_exploratory_001.md')

# All 19 symbols in data/raw/
SYMBOLS = [
    'SPY', 'QQQ', 'IWM', 'TLT', 'GLD', 'DBC', 'VNQ', 'EFA', 'EEM',
    'XLB', 'XLE', 'XLF', 'XLI', 'XLK', 'XLP', 'XLU', 'XLV', 'XLY', '^VIX'
]

# Asset class grouping for cross-asset comparison
ASSET_GROUPS = {
    'Equity (US Broad)': ['SPY', 'QQQ', 'IWM'],
    'Equity (Sectors)': ['XLB', 'XLE', 'XLF', 'XLI', 'XLK', 'XLP', 'XLU', 'XLV', 'XLY'],
    'International': ['EFA', 'EEM'],
    'Bonds': ['TLT'],
    'Commodities': ['DBC', 'GLD'],
    'REITs': ['VNQ'],
    'Volatility Index': ['^VIX']
}

# Sub-period definitions
SUB_PERIODS = {
    'Pre-2008': ('1993-01-01', '2007-12-31'),
    '2008-2020': ('2008-01-01', '2019-12-31'),
    '2020+': ('2020-01-01', '2026-12-31'),
}


def load_symbol(symbol: str) -> pd.DataFrame:
    """Load a single symbol's parquet file."""
    path = RAW_DIR / f'{symbol}.parquet'
    if not path.exists():
        print(f'WARNING: {path} not found')
        return None
    df = pd.read_parquet(path)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    # Ensure we have required columns
    required = ['Open', 'High', 'Low', 'Close', 'Volume']
    if not all(c in df.columns for c in required):
        print(f'WARNING: {symbol} missing required columns')
        return None
    return df[required]


def compute_session_returns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute overnight, intraday, and total returns.

    Overnight: Open_t / Close_{t-1} - 1
    Intraday: Close_t / Open_t - 1
    Total: Close_t / Close_{t-1} - 1
    """
    out = pd.DataFrame(index=df.index)
    out['close'] = df['Close']
    out['open'] = df['Open']
    out['prev_close'] = df['Close'].shift(1)

    # Overnight return (close-to-open)
    out['r_overnight'] = out['open'] / out['prev_close'] - 1

    # Intraday return (open-to-close)
    out['r_intraday'] = out['close'] / out['open'] - 1

    # Total return (close-to-close)
    out['r_total'] = out['close'] / out['prev_close'] - 1

    # Log returns for cumulative sums
    out['log_overnight'] = np.log1p(out['r_overnight'])
    out['log_intraday'] = np.log1p(out['r_intraday'])
    out['log_total'] = np.log1p(out['r_total'])

    # Verify multiplicative decomposition
    out['decomp_check'] = (1 + out['r_overnight']) * (1 + out['r_intraday']) - (1 + out['r_total'])

    # Overnight share of total return
    out['overnight_share'] = np.where(
        out['r_total'] != 0,
        out['r_overnight'] / out['r_total'],
        np.nan
    )

    # Drop first row (no prev_close)
    out = out.iloc[1:].copy()

    return out


def annualize(mean_daily: float, std_daily: float) -> tuple:
    """Return (annualized_mean, annualized_std, annualized_sharpe)."""
    ann_mean = mean_daily * 252
    ann_std = std_daily * np.sqrt(252)
    ann_sharpe = ann_mean / ann_std if ann_std > 0 else np.nan
    return ann_mean, ann_std, ann_sharpe


def t_test_vs_zero(series: pd.Series) -> tuple:
    """One-sample t-test vs zero. Returns (t_stat, p_value, n_obs)."""
    clean = series.dropna()
    if len(clean) < 2:
        return np.nan, np.nan, len(clean)
    t_stat, p_val = stats.ttest_1samp(clean, 0)
    return t_stat, p_val, len(clean)


def paired_t_test(a: pd.Series, b: pd.Series) -> tuple:
    """Paired t-test. Returns (t_stat, p_value, n_obs)."""
    clean = pd.DataFrame({'a': a, 'b': b}).dropna()
    if len(clean) < 2:
        return np.nan, np.nan, len(clean)
    t_stat, p_val = stats.ttest_rel(clean['a'], clean['b'])
    return t_stat, p_val, len(clean)


def binomial_test_positive_share(series: pd.Series) -> tuple:
    """Binomial test: H0: proportion > 0 is 0.5. Returns (proportion, p_value, n_obs)."""
    clean = series.dropna()
    if len(clean) == 0:
        return np.nan, np.nan, 0
    n_pos = (clean > 0).sum()
    n_total = len(clean)
    prop = n_pos / n_total
    # Two-sided binomial test
    from scipy.stats import binomtest
    result = binomtest(n_pos, n_total, 0.5, alternative='two-sided')
    return prop, result.pvalue, n_total


def summarize_series(series: pd.Series, label: str) -> dict:
    """Compute summary statistics for a return series."""
    clean = series.dropna()
    if len(clean) == 0:
        return {f'{label}_n': 0}

    mean_d = clean.mean()
    std_d = clean.std()
    ann_mean, ann_std, ann_sharpe = annualize(mean_d, std_d)
    t_stat, p_val, n_obs = t_test_vs_zero(clean)

    return {
        f'{label}_n': n_obs,
        f'{label}_mean_daily': mean_d,
        f'{label}_std_daily': std_d,
        f'{label}_ann_mean': ann_mean,
        f'{label}_ann_std': ann_std,
        f'{label}_ann_sharpe': ann_sharpe,
        f'{label}_t_stat': t_stat,
        f'{label}_p_val': p_val,
        f'{label}_skew': clean.skew(),
        f'{label}_kurtosis': clean.kurtosis(),
        f'{label}_min': clean.min(),
        f'{label}_max': clean.max(),
    }


def summarize_symbol(symbol: str, df: pd.DataFrame) -> dict:
    """Compute all summary statistics for a symbol."""
    returns = compute_session_returns(df)

    result = {'symbol': symbol}

    # Basic stats for each session
    for session in ['r_overnight', 'r_intraday', 'r_total']:
        result.update(summarize_series(returns[session], session))

    # Overnight share stats
    share = returns['overnight_share'].dropna()
    if len(share) > 0:
        result['share_mean'] = share.mean()
        result['share_median'] = share.median()
        result['share_std'] = share.std()

    # Paired test: overnight vs intraday
    t_stat, p_val, n_obs = paired_t_test(returns['r_overnight'], returns['r_intraday'])
    result['paired_t_stat'] = t_stat
    result['paired_p_val'] = p_val
    result['paired_n'] = n_obs

    # Binomial: overnight > intraday
    diff = returns['r_overnight'] - returns['r_intraday']
    prop, p_val, n_obs = binomial_test_positive_share(diff)
    result['binomial_prop_overnight_gt_intraday'] = prop
    result['binomial_p_val'] = p_val
    result['binomial_n'] = n_obs

    # Binomial: overnight > 0
    prop, p_val, n_obs = binomial_test_positive_share(returns['r_overnight'])
    result['binomial_prop_overnight_gt_zero'] = prop
    result['binomial_p_val_overnight_gt_zero'] = p_val

    # Cumulative log returns (final values)
    result['cum_log_overnight'] = returns['log_overnight'].sum()
    result['cum_log_intraday'] = returns['log_intraday'].sum()
    result['cum_log_total'] = returns['log_total'].sum()

    return result


def summarize_subperiod(returns: pd.DataFrame, start: str, end: str) -> dict:
    """Summarize returns for a sub-period."""
    mask = (returns.index >= start) & (returns.index <= end)
    sub = returns.loc[mask]

    if len(sub) == 0:
        return {'n': 0}

    result = {'n': len(sub)}
    for session in ['r_overnight', 'r_intraday', 'r_total']:
        clean = sub[session].dropna()
        if len(clean) > 0:
            mean_d = clean.mean()
            std_d = clean.std()
            ann_mean, ann_std, ann_sharpe = annualize(mean_d, std_d)
            t_stat, p_val, _ = t_test_vs_zero(clean)
            result[f'{session}_ann_mean'] = ann_mean
            result[f'{session}_ann_sharpe'] = ann_sharpe
            result[f'{session}_t_stat'] = t_stat
            result[f'{session}_p_val'] = p_val

    return result


def format_pct(x):
    """Format as percentage with 2 decimal places."""
    if pd.isna(x):
        return 'N/A'
    return f'{x*100:.2f}%'


def format_num(x, decimals=4):
    """Format number with specified decimals."""
    if pd.isna(x):
        return 'N/A'
    return f'{x:.{decimals}f}'


def generate_report(all_results: dict, subperiod_results: dict, group_results: dict) -> str:
    """Generate the markdown report."""
    lines = []

    lines.append('# Overnight Drift Exploratory Diagnostic')
    lines.append('')
    lines.append('**Status: EXPLORATORY DIAGNOSTIC ONLY — NO ALPHA CLAIMS**')
    lines.append('')
    lines.append('This report characterizes the overnight/intraday return decomposition across')
    lines.append('the available ETF universe using daily OHLCV data. It does not claim a tradable')
    lines.append('edge. All results are subject to the limitations disclosed at the end of this report.')
    lines.append('')
    lines.append('---')
    lines.append('')

    # Data inventory
    lines.append('## 1. Data Inventory')
    lines.append('')
    lines.append('| Symbol | Asset Class | Rows | Date Range |')
    lines.append('|--------|-------------|------|------------|')
    for symbol in SYMBOLS:
        if symbol in all_results:
            r = all_results[symbol]
            asset_class = 'Index (Non-tradeable)' if symbol == '^VIX' else 'ETF'
            lines.append(f'| {symbol} | {asset_class} | {r["r_total_n"]} | {r.get("date_start", "N/A")} to {r.get("date_end", "N/A")} |')
    lines.append('')

    # Per-symbol session return decomposition
    lines.append('## 2. Per-Symbol Session Return Decomposition (Full History)')
    lines.append('')
    lines.append('### Annualized Statistics')
    lines.append('')
    lines.append('| Symbol | Session | Ann. Mean | Ann. Std | Ann. Sharpe | t-stat | p-value | N |')
    lines.append('|--------|---------|-----------|----------|-------------|--------|---------|---|')

    for symbol in SYMBOLS:
        if symbol not in all_results:
            continue
        r = all_results[symbol]
        for session, label in [('r_overnight', 'Overnight'), ('r_intraday', 'Intraday'), ('r_total', 'Total')]:
            ann_mean = r.get(f'{session}_ann_mean', np.nan)
            ann_std = r.get(f'{session}_ann_std', np.nan)
            ann_sharpe = r.get(f'{session}_ann_sharpe', np.nan)
            t_stat = r.get(f'{session}_t_stat', np.nan)
            p_val = r.get(f'{session}_p_val', np.nan)
            n = r.get(f'{session}_n', 0)
            lines.append(f'| {symbol} | {label} | {format_pct(ann_mean)} | {format_pct(ann_std)} | {format_num(ann_sharpe, 3)} | {format_num(t_stat, 2)} | {format_num(p_val, 4)} | {n} |')
    lines.append('')

    lines.append('### Cumulative Log Returns (Full History)')
    lines.append('')
    lines.append('| Symbol | Cum. Overnight | Cum. Intraday | Cum. Total |')
    lines.append('|--------|----------------|---------------|------------|')
    for symbol in SYMBOLS:
        if symbol not in all_results:
            continue
        r = all_results[symbol]
        lines.append(f'| {symbol} | {format_num(r.get("cum_log_overnight", np.nan), 4)} | {format_num(r.get("cum_log_intraday", np.nan), 4)} | {format_num(r.get("cum_log_total", np.nan), 4)} |')
    lines.append('')

    lines.append('### Overnight Share of Total Return')
    lines.append('')
    lines.append('| Symbol | Mean Share | Median Share | Std Share |')
    lines.append('|--------|------------|--------------|-----------|')
    for symbol in SYMBOLS:
        if symbol not in all_results:
            continue
        r = all_results[symbol]
        lines.append(f'| {symbol} | {format_pct(r.get("share_mean", np.nan))} | {format_pct(r.get("share_median", np.nan))} | {format_pct(r.get("share_std", np.nan))} |')
    lines.append('')

    lines.append('### Statistical Tests: Overnight vs Intraday')
    lines.append('')
    lines.append('| Symbol | Paired t-stat (Ov vs In) | p-value | Binomial: Ov > In % | p-value | Binomial: Ov > 0 % | p-value |')
    lines.append('|--------|--------------------------|---------|---------------------|---------|--------------------|---------|')
    for symbol in SYMBOLS:
        if symbol not in all_results:
            continue
        r = all_results[symbol]
        lines.append(f'| {symbol} | {format_num(r.get("paired_t_stat", np.nan), 2)} | {format_num(r.get("paired_p_val", np.nan), 4)} | {format_pct(r.get("binomial_prop_overnight_gt_intraday", np.nan))} | {format_num(r.get("binomial_p_val", np.nan), 4)} | {format_pct(r.get("binomial_prop_overnight_gt_zero", np.nan))} | {format_num(r.get("binomial_p_val_overnight_gt_zero", np.nan), 4)} |')
    lines.append('')

    # Sub-period analysis
    lines.append('## 3. Sub-Period Stability Analysis')
    lines.append('')

    for period_name, (start, end) in SUB_PERIODS.items():
        lines.append(f'### {period_name} ({start} to {end})')
        lines.append('')
        lines.append('| Symbol | Session | Ann. Mean | Ann. Sharpe | t-stat | p-value | N |')
        lines.append('|--------|---------|-----------|-------------|--------|---------|---|')

        for symbol in SYMBOLS:
            if symbol not in subperiod_results or period_name not in subperiod_results[symbol]:
                continue
            r = subperiod_results[symbol][period_name]
            if r.get('n', 0) == 0:
                continue
            for session, label in [('r_overnight', 'Overnight'), ('r_intraday', 'Intraday'), ('r_total', 'Total')]:
                ann_mean = r.get(f'{session}_ann_mean', np.nan)
                ann_sharpe = r.get(f'{session}_ann_sharpe', np.nan)
                t_stat = r.get(f'{session}_t_stat', np.nan)
                p_val = r.get(f'{session}_p_val', np.nan)
                n = r.get('n', 0)
                lines.append(f'| {symbol} | {label} | {format_pct(ann_mean)} | {format_num(ann_sharpe, 3)} | {format_num(t_stat, 2)} | {format_num(p_val, 4)} | {n} |')
        lines.append('')

    # Cross-asset group comparison
    lines.append('## 4. Cross-Asset Group Comparison (Full History)')
    lines.append('')
    lines.append('| Group | Symbols | Session | Avg Ann. Mean | Avg Ann. Sharpe | Avg t-stat |')
    lines.append('|-------|---------|---------|---------------|-----------------|------------|')

    for group_name, symbols in ASSET_GROUPS.items():
        valid_symbols = [s for s in symbols if s in all_results]
        if not valid_symbols:
            continue
        for session, label in [('r_overnight', 'Overnight'), ('r_intraday', 'Intraday'), ('r_total', 'Total')]:
            ann_means = [all_results[s].get(f'{session}_ann_mean', np.nan) for s in valid_symbols]
            ann_sharpes = [all_results[s].get(f'{session}_ann_sharpe', np.nan) for s in valid_symbols]
            t_stats = [all_results[s].get(f'{session}_t_stat', np.nan) for s in valid_symbols]

            avg_mean = np.nanmean(ann_means)
            avg_sharpe = np.nanmean(ann_sharpes)
            avg_t = np.nanmean(t_stats)

            lines.append(f'| {group_name} | {len(valid_symbols)} | {label} | {format_pct(avg_mean)} | {format_num(avg_sharpe, 3)} | {format_num(avg_t, 2)} |')
    lines.append('')

    # Limitations
    lines.append('## 5. Limitations and Bias Disclosures')
    lines.append('')
    lines.append('**THIS IS AN EXPLORATORY DIAGNOSTIC ONLY. NO TRADABLE EDGE IS CLAIMED.**')
    lines.append('')
    lines.append('The following limitations apply to all results above:')
    lines.append('')
    lines.append('1. **Daily data only — no intraday execution prices**: We observe Open and Close but not the path between them. Actual execution prices for overnight positions (buying at prior close, selling at open) may differ from reported Open/Close due to bid-ask spreads, auction mechanics, and market-on-open orders.')
    lines.append('')
    lines.append('2. **Bid-ask spreads not observed**: Yahoo Finance reports midpoint-like prices. Real overnight trading incurs spread costs (typically 1–10 bps for liquid ETFs, wider for sector/international ETFs).')
    lines.append('')
    lines.append('3. **ETF survivorship bias**: The universe comprises currently-listed ETFs. Delisted or merged ETFs are not represented. This may overstate returns if failed funds had different session return profiles.')
    lines.append('')
    lines.append('4. **No point-in-time universe membership**: The universe is fixed to currently available symbols. Historical universe composition (e.g., sector ETFs incepting in 1998) changes the cross-sectional properties over time.')
    lines.append('')
    lines.append('5. **Dividend adjustments**: Yahoo Finance provides adjusted Close but Open/High/Low may not be consistently adjusted for dividends/splits, potentially biasing overnight returns on ex-dividend dates.')
    lines.append('')
    lines.append('6. **^VIX is an index, not tradeable**: Included for reference only; VIX futures/ETFs have different session dynamics.')
    lines.append('')
    lines.append('7. **Weekend/holiday effects**: Overnight return from Friday close to Monday open spans 3 calendar days; holiday periods span longer. Not separately modeled.')
    lines.append('')
    lines.append('8. **Corporate actions**: Splits and dividends may create artifacts in the Open/Close relationship if not perfectly adjusted.')
    lines.append('')
    lines.append('9. **Data source limitations**: yfinance data may have occasional errors, missing rows, or adjustments that differ from official exchange data.')
    lines.append('')
    lines.append('10. **No cost model applied**: All returns are gross of any transaction costs, slippage, or financing. A realistic overnight capture strategy would need to overcome ~5–20 bps round-trip costs per cycle.')
    lines.append('')
    lines.append('11. **Multiple testing not controlled**: This diagnostic examines 19 symbols × 3 sessions × 3 sub-periods = 171+ statistical tests without correction. Reported p-values are nominal.')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('## 6. Conclusion')
    lines.append('')
    lines.append('This exploratory diagnostic provides a descriptive characterization of overnight vs. intraday')
    lines.append('return decomposition across the available ETF universe. Any apparent statistical significance')
    lines.append('should be interpreted with extreme caution given the limitations above, particularly the')
    lines.append('absence of bid-ask spread data, the use of daily (not intraday) prices, and the lack of')
    lines.append('multiple-testing correction.')
    lines.append('')
    lines.append('**No investment decisions should be based on this analysis.** Further investigation would')
    lines.append('require: (a) intraday tick/bar data with bid-ask spreads, (b) point-in-time universe')
    lines.append('construction, (c) explicit cost modeling with realistic overnight execution assumptions,')
    lines.append('and (d) out-of-sample validation on a disjoint dataset.')
    lines.append('')

    return '\n'.join(lines)


def main():
    print('=' * 60)
    print('Overnight Drift Exploratory Diagnostic')
    print('=' * 60)

    # Load all symbols
    print('\nLoading data...')
    all_data = {}
    for symbol in SYMBOLS:
        df = load_symbol(symbol)
        if df is not None:
            all_data[symbol] = df
            print(f'  {symbol}: {len(df)} rows, {df.index[0].date()} to {df.index[-1].date()}')
        else:
            print(f'  {symbol}: FAILED TO LOAD')

    # Compute per-symbol results
    print('\nComputing session returns...')
    all_results = {}
    for symbol, df in all_data.items():
        returns = compute_session_returns(df)
        result = summarize_symbol(symbol, df)
        result['date_start'] = returns.index[0].date()
        result['date_end'] = returns.index[-1].date()
        all_results[symbol] = result
        print(f'  {symbol}: done')

    # Sub-period analysis
    print('\nComputing sub-period analysis...')
    subperiod_results = {}
    for symbol, df in all_data.items():
        returns = compute_session_returns(df)
        subperiod_results[symbol] = {}
        for period_name, (start, end) in SUB_PERIODS.items():
            subperiod_results[symbol][period_name] = summarize_subperiod(returns, start, end)
        print(f'  {symbol}: done')

    # Group-level aggregation
    print('\nComputing group-level aggregation...')
    group_results = {}
    for group_name, symbols in ASSET_GROUPS.items():
        valid = [s for s in symbols if s in all_results]
        group_results[group_name] = valid

    # Generate report
    print('\nGenerating report...')
    report = generate_report(all_results, subperiod_results, group_results)

    # Write output
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, 'w') as f:
        f.write(report)

    print(f'\nReport written to: {OUTPUT_PATH}')
    print('\nDone.')

    return 0


if __name__ == '__main__':
    sys.exit(main())