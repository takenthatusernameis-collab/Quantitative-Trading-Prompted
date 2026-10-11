# Experiment: Benchmark Comparison (tsmomentum_benchmark_001)

## Hypothesis Reference

See `research/hypotheses/tsmomentum_001.md`.

**Benchmark**: Equal-weighted (1/N) portfolio of the same 7 assets, SPY buy-and-hold,
and risk-free rate (2% annual).

---

## Data Used

- **Source**: Yahoo Finance via yfinance (cached)
- **Date Range**: 1993-01-01 to 2026-10-09
- **Universe**: SPY, QQQ, IWM, TLT, GLD, EFA, EEM
- **Cost Model**: 0.0 bps commission + 0.0 bps slippage = 0.0 bps round-trip

---

## Performance Comparison

| Portfolio | Period | Sharpe | Ann. Return | Max Drawdown | N Days |
|-----------|--------|--------|-------------|--------------|--------|
| strategy | train | 0.2833 | 0.0769 | -0.6135 | 4264 |
| strategy | validation | 0.5551 | 0.0918 | -0.1625 | 2013 |
| strategy | test | 0.6445 | 0.1209 | -0.3041 | 2205 |
| ew_1n | train | 0.3707 | 0.0961 | -0.5868 | 4264 |
| ew_1n | validation | 0.5151 | 0.0806 | -0.1584 | 2013 |
| ew_1n | test | 0.4716 | 0.0889 | -0.2797 | 2205 |
| spy_buyhold | train | 0.1836 | 0.0565 | -0.5647 | 4264 |
| spy_buyhold | validation | 0.6504 | 0.1155 | -0.1942 | 2013 |
| spy_buyhold | test | 0.5788 | 0.1302 | -0.3410 | 2205 |
| rf | train | 0.0000 | 0.0202 | 0.0000 | 4264 |
| rf | validation | 465931142127601.1250 | 0.0202 | 0.0000 | 2013 |
| rf | test | 0.0000 | 0.0202 | 0.0000 | 2205 |


### Test Period Focus

Strategy (test): Sharpe = 0.6445,
Ann. Return = 0.1209,
Max DD = -0.3041

Equal-weight 1/N (test): Sharpe = 0.4716,
Ann. Return = 0.0889

SPY buy-and-hold (test): Sharpe = 0.5788,
Ann. Return = 0.1302

Risk-free (test): 2.0% annual

---

## Alpha/Beta Regression

OLS regression: strategy_excess = alpha + beta * benchmark_excess + eps
Alpha annualized; benchmark = SPY (risk-free adjusted).

| Regression | Alpha (annual) | Beta | R-squared | t-stat (alpha) | p-value (alpha) | N obs |
|-----------|----------------|------|-----------|----------------|-----------------|-------|
| alpha_spy_daily | 0.0214 | 0.7055 | 0.7353 | 0.7849 | 0.4326 | 2205 |
| alpha_spy_monthly | 0.0171 | 0.7401 | 0.7613 | 0.7442 | 0.4585 | 106 |
| alpha_ew_daily | 0.0302 | 1.0038 | 0.8778 | 1.6328 | 0.1027 | 2205 |
| alpha_ew_monthly | 0.0324 | 0.9718 | 0.8693 | 1.9242 | 0.0571 | 106 |


### Alpha Interpretation

- **Alpha vs SPY (daily)**: 0.0214 annualized with
  p-value = 0.4326. Not statistically significant (p < 0.05: False).
- **Alpha vs SPY (monthly)**: 0.0171 annualized with
  p-value = 0.4585.
- **Alpha vs 1/N (daily)**: 0.0302 annualized with
  p-value = 0.1027.
- **Alpha vs 1/N (monthly)**: 0.0324 annualized with
  p-value = 0.0571.
- **Beta vs SPY (daily)**: 0.7055 — high market exposure.

---

## Correlation Analysis

| Strategy | SPY Buy-Hold | 1/N Portfolio | Risk-Free |
|----------|-------------|---------------|-----------|
| strategy | 0.8569 | 0.9344 | N/A (constant) |
| spy_buyhold | 1.0000 | 0.9096 | N/A (constant) |
| ew_portfolio | 0.9096 | 1.0000 | N/A (constant) |


### Correlation Interpretation

The strategy's daily returns correlate 0.86 with SPY buy-and-hold
and 0.93 with the equal-weight portfolio. This indicates
the strategy is heavily exposed to overall equity market movements. The
high correlation with SPY (β = 0.71)
means the strategy captures significant market beta alongside its alpha.

### Information Ratio vs Benchmarks (Test Period)

| Benchmark | Strategy Sharpe | Benchmark Sharpe | IR (Sharpe ratio difference) |
|-----------|----------------|-------------------|------------------------------|
| 1/N Portfolio | 0.6445 | 0.4716 | 0.1729 |
| SPY Buy-Hold | 0.6445 | 0.5788 | 0.0657 |

---

*Report generated: 2026-10-11*
*Code revision: f7cbf05*
