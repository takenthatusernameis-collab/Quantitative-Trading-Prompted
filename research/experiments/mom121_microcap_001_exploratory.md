# Exploratory Diagnostic: Microcap mom121 Momentum Code Mechanics

**Labels:** EXPLORATORY — NOT CONFIRMATORY — SURVIVORSHIP BIASED — CURRENT TICKERS APPLIED RETROSPECTIVELY

## Purpose
This diagnostic tests the code mechanics of the momentum and weight-building pipeline
using a current-ticker microcap basket derived from yfinance snapshot.
It does not constitute evidence of an edge due to severe survivorship and look-ahead bias.

## Data
- Tickers: ['SNDL', 'ACB']
- Date range: 2024-10-14 to 2026-10-14
- Number of observations: 501
- Price type: Close (not adjusted for splits/dividends) — limitation noted.

## Methodology
1. Fetched historical OHLCV data via `YFinanceFetcher` (aligned calendar).
2. Extracted Close prices as a proxy for adjusted close (limitation: splits/dividends not accounted for).
3. Computed momentum using two conventions:
   - Daily trading-day convention: `lookback=252, skip=21` (as in `src/features/momentum.py`)
   - Approximate monthly calendar-month-end convention:
     * Resampled to month-end close, computed `Close(t-1)/Close(t-12)-1`, forward-filled to daily frequency.
4. Built weights using top decile long-only equal-weight portfolio.

## Results (Code Mechanics Only)
- The momentum and weight-building pipeline runs without errors.
- Weights are generated and sum to approximately 1.0 each day (indicating proper normalization).
- No code defects were detected in the exploratory run.

## Limitations and Biases
**Survivorship Bias:** The ticker list is based on current market cap snapshot;
  delisted or formerly microcap stocks that have grown or shrunk are omitted.

**Look-ahead Bias:** Using today's microcap universe to select tickers for historical analysis
  assumes that the same tickers were microcap in the past, which is not true.

**Price Adjustment:** Used Close prices instead of split- and dividend-adjusted prices.
  This may distort returns, especially around corporate actions.

**Monthly Approximation:** The monthly momentum is approximated by resampling to month-end
  and forward-filling; exact month-end dates may not align with trading days.

## Conclusion
The exploratory diagnostic confirms that the code mechanics of the momentum
and weight-building pipeline are functional. No defects were found.
However, due to the biases listed above, the results cannot be used
as evidence of a trading edge.

## Next Steps
If point-in-time fundamental data becomes available, a confirmatory diagnostic
should be run with proper point-in-time microcap universe and adjusted prices.