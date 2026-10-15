import yfinance as yf
import pandas as pd
import numpy as np
import sys
sys.path.insert(0, '/home/runner/work/Quantitative-Trading-Prompted/Quantitative-Trading-Prompted/src')
from features.momentum import compute_momentum

# Parameters
tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NFLX', 'NVDA', 'INTC', 'CSCO', 'JPM', 'BAC', 'WMT', 'PG', 'JNJ']
end_date = pd.Timestamp.now(tz='UTC')
start_date = end_date - pd.DateOffset(years=2)
# Format for yfinance
start_str = start_date.strftime('%Y-%m-%d')
end_str = end_date.strftime('%Y-%m-%d')

print(f'Downloading price data for {len(tickers)} tickers from {start_str} to {end_str}')
# Download adjusted close
price_data = yf.download(tickers, start=start_str, end=end_str, progress=False)['Close']
if price_data.empty:
    raise ValueError('No price data downloaded')
print(f'Price data shape: {price_data.shape}')
print(f'Date range: {price_data.index.min()} to {price_data.index.max()}')

# Fetch shares outstanding for each ticker
shares_dict = {}
for tk in tickers:
    try:
        t = yf.Ticker(tk)
        shares = t.get_shares_full()
        if shares is not None and not shares.empty:
            # Ensure timezone naive UTC for merging
            shares.index = shares.index.tz_convert(None)
            # Remove duplicate dates, keep last
            shares = shares[~shares.index.duplicated(keep='last')]
            shares_dict[tk] = shares
        else:
            print(f'Warning: No shares data for {tk}')
    except Exception as e:
        print(f'Error fetching shares for {tk}: {e}')

print(f'Successfully fetched shares for {len(shares_dict)} tickers')

# Align shares and price: forward fill shares to price dates
market_cap = pd.DataFrame(index=price_data.index, columns=price_data.columns)
for tk in price_data.columns:
    if tk in shares_dict:
        shares_series = shares_dict[tk].reindex(price_data.index, method='ffill')
        market_cap[tk] = price_data[tk] * shares_series
    else:
        market_cap[tk] = np.nan

# Drop columns where all market cap is NaN
market_cap = market_cap.dropna(axis=1, how='all')
print(f'Market cap data shape after dropping empty columns: {market_cap.shape}')

# Compute 12-1 momentum using daily convention (lookback=252, skip=21)
# Use the existing compute_momentum function which expects a DataFrame of prices
# We'll pass market cap as the "price" for momentum calculation
momentum = compute_momentum(market_cap, lookback=252, skip=21)
print(f'Momentum shape: {momentum.shape}')
print(f'Momentum date range: {momentum.index.min()} to {momentum.index.max()}')
print(f'Number of non-NaN momentum entries: {momentum.notna().sum().sum()}')

# Show some statistics
print('\\n--- Summary Statistics ---')
print(f'Average number of tickers with valid market cap per day: {market_cap.notna().sum().mean():.1f}')
print(f'Average number of tickers with valid momentum per day: {momentum.notna().sum().mean():.1f}')

# Example: compute decile weights (top 30% by momentum) for the last date
if not momentum.empty:
    last_momentum = momentum.iloc[-1]
    ranked = last_momentum.dropna().rank(ascending=False, method='first')
    n_select = max(1, int(len(ranked) * 0.3))  # top 30%
    selected = ranked[ranked <= n_select].index.tolist()
    print(f'\\nExample for last date ({momentum.index[-1]}):')
    print(f'Number of tickers selected for top 30% momentum: {len(selected)}')
    print(f'Selected tickers: {selected}')
else:
    print('No momentum data computed.')
