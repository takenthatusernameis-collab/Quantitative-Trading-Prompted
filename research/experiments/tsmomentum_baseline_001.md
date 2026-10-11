# Experiment: Time-Series Momentum Baseline (tsmomentum_baseline_001)

## Hypothesis Reference

See `research/hypotheses/tsmomentum_001.md` for the full hypothesis documentation.

**Mechanism**: Time-series momentum exploits the tendency for assets with positive
recent returns to continue outperforming in the near term, driven by investor
underreaction and slow information diffusion.

**Expected Direction**: Positive carry (3-8% annualized gross before costs)

**Falsification Condition**: Test-period Sharpe < 0.5 net of costs OR
test Sharpe < train Sharpe - 1 standard deviation of train Sharpe estimates.

---

## Data Used

- **Source**: Yahoo Finance (via yfinance library v1.7.0)
- **Date Range**: 1993-01-01 to 2026-10-11
- **Frequency**: Daily (end-of-day OHLCV)
- **Universe**: SPY, QQQ, IWM, TLT, GLD, EFA, EEM
- **Records**: 8482 trading days total
- **Point-in-Time Treatment**: All signals computed using only data available
  at signal formation time. Momentum uses 12-month lookback (252 trading days)
  excluding the most recent month (21 trading days) to avoid short-term
  reversal microstructure noise. Weights computed on day t are shifted to be
  effective on day t+1. No forward-looking data used.

---

## Configuration

- **Lookback Window**: 252 trading days (~12 months)
- **Skip Window**: 21 trading days (~1 month)
- **Selection**: Top 50% of assets by momentum (equal-weighted)
- **Rebalancing Frequency**: M (monthly via daily signal with
  forward-filled weights)
- **Commission**: 1.0 bps per trade (round-trip)
- **Slippage**: 2.0 bps per trade
- **Risk-Free Rate**: 2.0% annual (for Sharpe calculation)
- **Code Revision**: 6c74024

---

## Train/Validation/Test Splits

| Period | Start Date | End Date | Trading Days |
|--------|------------|----------|--------------|
| Train | 1993-01-01 | 2009-12-31 | 4264 |
| Validation | 2010-01-01 | 2017-12-31 | 2013 |
| Test | 2018-01-01 | 2026-10-11 | 2205 |

---

## Results

### Performance Metrics (Net of Costs)

| Period | Total Return | Ann. Return | Ann. Vol | Sharpe | Sortino | Max DD | Ann. Turnover | Trades | Profit Factor |
|--------|-------------|-------------|----------|--------|---------|--------|---------------|--------|---------------|
| train | 2.5020 | 0.0769 | 0.2008 | 0.2833 | 0.3844 | -0.6135 | 4.32 | 139 | 1.09 |
| validation | 1.0169 | 0.0918 | 0.1293 | 0.5551 | 0.7250 | -0.1625 | 12.27 | 194 | 1.14 |
| test | 1.7154 | 0.1209 | 0.1566 | 0.6445 | 0.8576 | -0.3041 | 10.86 | 190 | 1.15 |

### Detailed Period Results

#### Train Period (1993-01-01 to 2009-12-31)
- **Observations**: 4264 daily returns
- **Trades**: 139
- **Avg Positions**: 2.3

#### Validation Period (2010-01-01 to 2017-12-31)
- **Observations**: 2013 daily returns
- **Trades**: 194
- **Avg Positions**: 4.0

#### Test Period (2018-01-01 to 2026-10-11)
- **Observations**: 2205 daily returns
- **Trades**: 190
- **Avg Positions**: 4.0

---

## Cost Assumptions

| Component | Value | Source |
|-----------|-------|--------|
| Commission | 1.0 bps | config/settings.yaml |
| Slippage | 2.0 bps | config/settings.yaml |
| Risk-Free Rate | 2.0% annual | config/settings.yaml |
| Total Round-Trip Cost | 3.0 bps | Derived |

Costs applied per rebalancing day proportional to absolute weight change.

---

## Reproduction Commands

```bash
# From repository root
python3 src/backtest/engine.py --output-dir research/experiments
```

This will fetch data, run the backtest, and regenerate this report.

---

## Classification

This result is classified as an **exploratory signal**. It validates the
research pipeline but does not yet meet promotion gates (net out-of-sample
Sharpe >= 0.9 and >100 pooled out-of-sample trades). Further validation
required including robustness checks, parameter perturbation, and
out-of-sample walk-forward testing.

---

*Report generated: 2026-10-11*
*Pipeline: data ingestion → feature engineering → backtest → evaluation*
