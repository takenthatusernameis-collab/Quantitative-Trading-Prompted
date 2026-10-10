# Hypothesis: US Equity Time-Series Momentum (tsmomentum_001)

## Mechanism Description

Time-series momentum (TSMOM) exploits the tendency for assets with positive recent
returns to continue outperforming in the near term, and for assets with negative
recent returns to continue underperforming. This is a well-documented anomaly
with multiple structural explanations:

1. **Investor Underreaction**: Information diffuses slowly across market
   participants due to limited attention, cognitive biases, and institutional
   constraints. Prices adjust gradually rather than instantaneously, creating
   momentum.

2. **Disposition Effect**: Investors hold losing positions too long and sell
   winners too early, creating selling pressure on winners and buying pressure
   on losers that slows price adjustment.

3. **Institutional Constraints**: Portfolio rebalancing rules, benchmarking
   against indices, and career concerns cause institutional flows to trend-follow
   rather than mean-revert in the intermediate term.

4. **Funding/Carry Compensation**: Assets with persistent positive momentum often
   carry positive expected returns as compensation for crash risk, liquidity risk,
   or funding constraints.

The effect is distinct from cross-sectional momentum (which ranks assets against
each other) and instead evaluates each asset's own return history relative to a
risk-free or zero threshold.

## Expected Direction and Magnitude

- **Direction**: Positive (long momentum assets outperforms cash/benchmark)
- **Magnitude**: 3-8% annualized gross excess return before costs
- **Net Expectation**: 2-7% annualized after 3 bps round-trip costs
- **Risk-Adjusted**: Target net Sharpe ratio of 0.5-1.0

## Holding Horizon

- **Rebalancing Frequency**: Monthly (approximately 20 trading days)
- **Effective Holding Period**: 20 trading days per position (weights updated monthly)
- **Momentum Window**: 12 months (252 trading days) excluding most recent 1 month (21 trading days)

## Asset Universe

| Symbol | Name | Inception | Sector/Asset Class |
|--------|------|-----------|-------------------|
| SPY | SPDR S&P 500 ETF | 1993-01-29 | US Large Cap Equity |
| QQQ | Invesco QQQ Trust (Nasdaq 100) | 1999-03-10 | US Large Cap Growth Equity |
| IWM | iShares Russell 2000 ETF | 2000-05-22 | US Small Cap Equity |
| TLT | iShares 20+ Year Treasury Bond ETF | 2002-07-22 | US Long-Duration Treasuries |
| GLD | SPDR Gold Shares | 2004-11-18 | Gold/Commodities |
| EFA | iShares MSCI EAFE ETF | 2001-08-14 | Developed Intl Equity |
| EEM | iShares MSCI Emerging Markets ETF | 2003-04-08 | Emerging Markets Equity |

**Note**: The universe expands over time as ETFs launch. The backtest handles this
by only including assets with sufficient history (252 + 21 trading days) at each
signal date.

## Features and Data Sources

- **Primary Feature**: 12-month price momentum = (Price_{t-21} / Price_{t-273}) - 1
- **Data Source**: Yahoo Finance via `yfinance` Python library
- **Frequency**: Daily end-of-day OHLCV
- **Fields Used**: Close price (adjusted for splits, not dividends)
- **Point-in-Time**: Only data available up to signal date used; 1-day lag
  between signal computation and position implementation

## Entry/Exit Rules

1. **Signal Computation** (at close of day t):
   - For each asset with sufficient history, compute 12-month return
     excluding the most recent 21 trading days
   - Rank assets by momentum score (higher = better)
   - Select top 50% of assets by momentum (top decile replaced by top 50%
     for small universe of <5 assets)

2. **Position Formation** (effective day t+1):
   - Equal-weight long positions in selected assets
   - Cash weight = 1 - sum(long weights)
   - No short positions (long-only)

3. **Rebalancing**:
   - Monthly rebalancing (approximately every 20 trading days)
   - Weights held constant between rebalancing dates
   - Transaction costs applied on rebalancing days proportional to weight changes

## Benchmark

- **Primary**: Equal-weighted portfolio of all 7 assets (1/N benchmark)
- **Secondary**: Risk-free rate (2% annual) for Sharpe ratio computation
- **Tertiary**: SPY buy-and-hold (US equity market beta)

## Known Confounders

1. **Regime Changes**: Momentum performance varies significantly across market
   regimes (bull/bear, high/low volatility, crisis/calm). The 2008 financial
   crisis and 2020 COVID crash are known stress periods.

2. **Volatility Clustering**: High volatility periods increase turnover and
   transaction costs while reducing signal reliability.

3. **Transaction Costs**: Although ETF costs are low (1 bps commission + 2 bps
   slippage), monthly rebalancing on 7 assets creates ~84 trades/month, which
   compounds to ~1% annual drag.

4. **Survivorship/Selection Bias**: The universe consists of ETFs that survived
   to present. Failed ETFs are not in the data. However, major index ETFs
   (SPY, QQQ, IWM) have virtually zero failure risk.

5. **Lookback Window Sensitivity**: The 12-month/1-month skip configuration is
   standard but not optimal. Results may be sensitive to this choice.

6. **Correlation Regime Shifts**: During market stress, cross-asset correlations
   converge to 1, reducing diversification benefit of multi-asset momentum.

7. **Data Quality**: yfinance data is adjusted for splits but not dividends.
   Total return vs price return difference is ~1.5-2% annually for equity ETFs.

## Falsification Condition

The hypothesis is **falsified** if ANY of the following hold in the test period
(2018-01-01 to present):

1. **Net Sharpe < 0.5**: The out-of-sample net-of-costs Sharpe ratio is below 0.5
2. **Test Sharpe < Train Sharpe - 1σ**: The test-period Sharpe ratio is more than
   one standard deviation below the train-period Sharpe (using block bootstrap
   standard error estimates)
3. **Max Drawdown > 30%**: Peak-to-trough drawdown exceeds 30% in test period
4. **Profit Factor < 1.0**: Gross losses exceed gross profits in test period

## Cost Model Assumptions

| Component | Value | Basis |
|-----------|-------|-------|
| Commission | 1.0 bps per trade | config/settings.yaml (retail/algo broker estimate) |
| Slippage | 2.0 bps per trade | config/settings.yaml (conservative for liquid ETFs) |
| Total Round-Trip | 3.0 bps | Sum of commission + slippage |
| Risk-Free Rate | 2.0% annual | config/settings.yaml (conservative T-bill approximation) |
| Minimum Trade Size | $10 | config/settings.yaml (operational floor) |
| Borrow Costs | 0.0% | Not modeled (long-only strategy) |
| Funding Rate | 0.0% | Not modeled (no futures/swaps) |
| Market Impact | Not modeled | Flat slippage assumption |

**Cost Application**: Costs applied on each rebalancing day proportional to the
absolute change in portfolio weights: `cost = sum(|w_{t+1} - w_t|) * (commission + slippage)`.

## References

- Moskowitz, Ooi, Pedersen (2012) "Time Series Momentum" - JFE
- Asness, Moskowitz, Pedersen (2013) "Value and Momentum Everywhere" - JF
- Hurst, Ooi, Pedersen (2017) "A Century of Evidence on Trend-Following Investing" - JPM
- Clare, Seaton, Smith, Thomas (2014) "Trend Following with Equity ETFs" - JI

## Version History

- v001 (2026-10-10): Initial hypothesis document for Cycle 2 baseline test