# Experiment: Combined Risk Overlay Analysis (tsmomentum_combined_risk_001)

## Hypothesis Reference

See `research/hypotheses/tsmomentum_002.md`.

**Objective**: Test whether combining volatility targeting and drawdown control
overlays, applied to both the baseline (252-day) and perturbed (226-day)
lookback parameters, can elevate the test-period net Sharpe ratio to >= 0.9,
promoting the strategy from "Exploratory Signal" to "Credible Candidate."

**Configurations tested**: 8 total (2 lookbacks × 2 vol targets × 2 DD thresholds)

---

## Data Used

- **Source**: Yahoo Finance via yfinance (cached parquet in `data/raw/`)
- **Date Range**: 1993-01-01 to 2026-10-09
- **Frequency**: Daily (end-of-day)
- **Universe**: SPY, QQQ, IWM, TLT, GLD, EFA, EEM
- **Point-in-Time**: Signals computed using only data available at signal
  formation; weights shifted by 1 day before application.
- **Cost Model**: 0.0 bps commission + 0.0 bps slippage = 0.0 bps round-trip
- **Test Period**: 2018-01-01 to 2026-10-09

---

## Methodology

**Combined Risk Overlay** (applied in sequence):
1. **Volatility Targeting**: Scale gross exposure to achieve target annualized
   volatility (10%, 15%). Uses trailing 63-day realized volatility.
   Exposure capped at 100% (no leverage when vol is low).
2. **Drawdown Control**: When cumulative drawdown exceeds threshold (15%, 20%),
   reduce exposure by 50% until drawdown recovers.

The combination is applied additively: vol targeting scales weights first,
then DD control further reduces them when drawdown exceeds threshold.

---

## Configurations Tested

| Lookback | Vol Target | DD Threshold | Label |
|----------|------------|--------------|-------|
| 252 | 0.10 | 0.15 | combined_vol_0.10_dd_0.15 |
| 252 | 0.10 | 0.20 | combined_vol_0.10_dd_0.20 |
| 252 | 0.15 | 0.15 | combined_vol_0.15_dd_0.15 |
| 252 | 0.15 | 0.20 | combined_vol_0.15_dd_0.20 |
| 226 | 0.10 | 0.15 | combined_vol_0.10_dd_0.15 |
| 226 | 0.10 | 0.20 | combined_vol_0.10_dd_0.20 |
| 226 | 0.15 | 0.15 | combined_vol_0.15_dd_0.15 |
| 226 | 0.15 | 0.20 | combined_vol_0.15_dd_0.20 |

---

## Results: Lookback = 252 (Baseline)

## Combined Risk Overlay Results (Lookback=252)

| Overlay | Sharpe | Ann. Return | Max DD | Sortino | Profit Factor | Trades | DD < -30%? |
|---------|--------|-------------|--------|---------|---------------|--------|------------|
| **Baseline** | 0.6445 | 0.1209 | -0.3041 | 0.8576 | 1.15 | 190 | No |
| combined_vol_0.1_dd_0.15 | 0.7458 | 0.0930 | -0.1649 | 0.9788 | 1.18 | 1857 | Yes |
| combined_vol_0.1_dd_0.2 | 0.7072 | 0.0903 | -0.1851 | 0.9411 | 1.17 | 1857 | Yes |
| combined_vol_0.15_dd_0.15 | 0.7223 | 0.1080 | -0.1979 | 0.9156 | 1.17 | 984 | Yes |
| combined_vol_0.15_dd_0.2 | 0.6692 | 0.1046 | -0.2202 | 0.8607 | 1.16 | 976 | Yes |

---

## Results: Lookback = 226 (Perturbed -10%)

## Combined Risk Overlay Results (Lookback=226)

| Overlay | Sharpe | Ann. Return | Max DD | Sortino | Profit Factor | Trades | DD < -30%? |
|---------|--------|-------------|--------|---------|---------------|--------|------------|
| **Baseline** | 0.7046 | 0.1293 | -0.2918 | 0.9320 | 1.16 | 206 | Yes |
| combined_vol_0.1_dd_0.15 | 0.7794 | 0.0962 | -0.1625 | 1.0242 | 1.19 | 1812 | Yes |
| combined_vol_0.1_dd_0.2 | 0.7578 | 0.0947 | -0.1807 | 1.0031 | 1.18 | 1812 | Yes |
| combined_vol_0.15_dd_0.15 | 0.7724 | 0.1143 | -0.1767 | 0.9758 | 1.18 | 982 | Yes |
| combined_vol_0.15_dd_0.2 | 0.7483 | 0.1150 | -0.2017 | 0.9579 | 1.18 | 978 | Yes |

---

## Best Configuration Summary

| Metric | Value |
|--------|-------|
| Best Configuration | combined_vol_0.1_dd_0.15 (lookback=226) |
| Test Sharpe | 0.7794 |
| Annualized Return | 0.0962 |
| Max Drawdown | -0.1625 |
| Sortino | 1.0242 |
| Profit Factor | 1.19 |
| Trade Count | 1812 |
| Meets Sharpe >= 0.9? | **NO** |
| Meets Max DD > -30%? | **YES** |
| Meets Trades > 100? | **YES** |

---

## Promotion Gate Assessment

| Gate | Threshold | Observed | Status |
|------|-----------|----------|--------|
| Net OOS Sharpe >= 0.9 | 0.90 | 0.7794 | FAIL |
| >100 pooled OOS trades | 100 | 1812 | PASS |
| Max DD > -30% | -30% | -0.1625 | PASS |

**Overall Promotion Gate**: NOT MET

---

## Interpretation

The best combined overlay configuration **combined_vol_0.1_dd_0.15** with lookback=226
achieves a test-period Sharpe of **0.7794**, which does NOT meet the 0.9
promotion gate (gap: 0.1206).

Individual risk overlays from Cycle 3:
- dd_control_0.15: Sharpe 0.818
- vol_target_0.10: Sharpe 0.707
- 226-day lookback perturbation: Sharpe 0.705

The combined overlay improves over the baseline (0.645) but does not reach 0.9.
The strategy remains an **Exploratory Signal**.

---

## Next Steps

1. If promotion gate met: advance to simulation/parameter optimization (Cycle 5+)
2. If promotion gate NOT met: explore regime-aware filters or alternative universe
   selection (NOT further risk overlay tuning)

---

*Report generated: 2026-10-11*
*Code revision: f7cbf05*
