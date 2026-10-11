# Experiment: Risk Management Overlay (tsmomentum_risk_001)

## Hypothesis Reference

See `research/hypotheses/tsmomentum_001.md`.

**Objective**: Test whether volatility targeting and drawdown control overlays
improve the risk-adjusted return of the baseline strategy by reducing max
drawdown below 30% while preserving Sharpe > 0.5 (test period).

---

## Data Used

- **Source**: Yahoo Finance via yfinance (cached)
- **Date Range**: 1993-01-01 to 2026-10-09
- **Universe**: SPY, QQQ, IWM, TLT, GLD, EFA, EEM
- **Test Period**: 2018-01-01 to 2026-10-09
- **Cost Model**: 0.0 bps + 0.0 bps (unchanged from baseline)

---

## Methodology

Two overlay types tested:
1. **Volatility Targeting**: Scale gross exposure to achieve target annualized
   volatility (10%, 15%, 20%). Uses trailing 63-day realized volatility.
   Exposure capped at 100% (no leverage when vol is low).
2. **Drawdown Control**: When cumulative drawdown exceeds threshold (15%, 20%),
   reduce exposure by 50% until drawdown recovers.

---

## Results

## Risk Overlay Results

| Overlay | Sharpe | Ann. Return | Max DD | Sortino | Profit Factor | Trades |
|---------|--------|-------------|--------|---------|---------------|--------|
| **Baseline** | 0.6445 | 0.1209 | -0.3041 | 0.8576 | 1.15 | 190 |
| vol_target_0.1 | 0.7072 | 0.0903 | -0.1851 | 0.9411 | 1.17 | 1857 |
| vol_target_0.15 | 0.6273 | 0.1014 | -0.2595 | 0.8170 | 1.15 | 972 |
| vol_target_0.2 | 0.6096 | 0.1090 | -0.3009 | 0.7895 | 1.15 | 572 |
| dd_control_0.15 | 0.8184 | 0.1376 | -0.2089 | 1.0696 | 1.19 | 211 |
| dd_control_0.2 | 0.7849 | 0.1367 | -0.1986 | 1.0346 | 1.18 | 215 |

---

## Test-Period Metrics Detail

| Overlay | Sharpe | Ann. Return | Max DD | Sortino | Profit Factor | Trades | Target Met? |
|---------|--------|-------------|--------|---------|---------------|--------|-------------|
| vol_target_0.1 | 0.7072 | 0.0903 | -0.1851 | 0.9411 | 1.17 | 1857 | Yes |
| vol_target_0.15 | 0.6273 | 0.1014 | -0.2595 | 0.8170 | 1.15 | 972 | Yes |
| vol_target_0.2 | 0.6096 | 0.1090 | -0.3009 | 0.7895 | 1.15 | 572 | No |
| dd_control_0.15 | 0.8184 | 0.1376 | -0.2089 | 1.0696 | 1.19 | 211 | Yes |
| dd_control_0.2 | 0.7849 | 0.1367 | -0.1986 | 1.0346 | 1.18 | 215 | Yes |


### Baseline (for reference)

| Metric | Value |
|--------|-------|
| Sharpe | 0.6445 |
| Max Drawdown | -0.3041 |

---

## Interpretation

The baseline strategy has a test-period Sharpe of 0.645 and max drawdown
of -30.41%. The baseline VIOLATES the -30% drawdown
threshold.

The best-performing overlay is **dd_control_0.15** with Sharpe = 0.818.
Drawdown control successfully reduced max drawdown
below 30% for overlays that target it.

**Volatility targeting** can preserve Sharpe while reducing tail risk across target vol levels.

**Drawdown control** can help reduce max DD below 30%.

---

*Report generated: 2026-10-11*
*Code revision: 8950948*
