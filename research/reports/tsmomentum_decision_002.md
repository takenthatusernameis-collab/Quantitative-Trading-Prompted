# Decision: Time-Series Momentum Strategy (tsmomentum_decision_002)

**Date**: 2026-10-11
**Code revision**: 92893b9

---

## Executive Summary

The US Equity Time-Series Momentum strategy (7-asset, 12-month momentum,
monthly rebalancing) with combined risk overlays is classified as:

## **Exploratory Signal**

Mixed evidence — some criteria pass, some fail.

---

## Evidence Summary

### 1. Promotion Gates (Best Combined Configuration)

| Gate | Threshold | Observed | Status |
|------|-----------|----------|--------|
| Net OOS Sharpe >= 0.9 | 0.90 | 0.7794 | FAIL |
| >100 pooled OOS trades | 100 | 1812 | PASS |
| Max DD > -30% | -30% | -0.1625 | PASS |

**Best Config**: combined_vol_0.1_dd_0.15 (lookback=226)
**Promotion gate (ALL three)**: NOT MET

### 2. All 8 Configurations Tested

#### Lookback = 252 (Baseline)

| Configuration | Sharpe | Ann. Return | Max DD | Sortino | Profit Factor | Trades | DD < -30%? |
|---------------|--------|-------------|--------|---------|---------------|--------|------------|
| combined_vol_0.1_dd_0.15 | 0.7458 | 0.0930 | -0.1649 | 0.9788 | 1.18 | 1857 | Yes |
| combined_vol_0.1_dd_0.2 | 0.7072 | 0.0903 | -0.1851 | 0.9411 | 1.17 | 1857 | Yes |
| combined_vol_0.15_dd_0.15 | 0.7223 | 0.1080 | -0.1979 | 0.9156 | 1.17 | 984 | Yes |
| combined_vol_0.15_dd_0.2 | 0.6692 | 0.1046 | -0.2202 | 0.8607 | 1.16 | 976 | Yes |

#### Lookback = 226 (Perturbed)

| Configuration | Sharpe | Ann. Return | Max DD | Sortino | Profit Factor | Trades | DD < -30%? |
|---------------|--------|-------------|--------|---------|---------------|--------|------------|
| combined_vol_0.1_dd_0.15 | 0.7794 | 0.0962 | -0.1625 | 1.0242 | 1.19 | 1812 | Yes |
| combined_vol_0.1_dd_0.2 | 0.7578 | 0.0947 | -0.1807 | 1.0031 | 1.18 | 1812 | Yes |
| combined_vol_0.15_dd_0.15 | 0.7724 | 0.1143 | -0.1767 | 0.9758 | 1.18 | 982 | Yes |
| combined_vol_0.15_dd_0.2 | 0.7483 | 0.1150 | -0.2017 | 0.9579 | 1.18 | 978 | Yes |


### 3. Baseline Falsification Checks (Original Baseline, Lookback=252)

| Check | Threshold | Observed | Status |
|-------|-----------|----------|--------|
| Test Sharpe >= 0.5 | 0.50 | 0.6445 | PASS |
| Max DD > -30% | -30% | -0.3041 | FAIL |
| Profit Factor >= 1.0 | 1.00 | 1.15 | PASS |

### 4. Robustness (from Cycle 3)

| Criterion | Value | Threshold | Status |
|-----------|-------|-----------|--------|
| Parameter plateau | False | True | FAIL |
| Walk-forward mean Sharpe | 0.679 | > 0.3 | PASS |
| % Positive WF folds | 97.9% | > 50% | PASS |

### 5. Statistical Significance (from Cycle 3)

| Test | Observed | Threshold | Status |
|------|----------|-----------|--------|
| PSR vs 0 | 0.9830 | > 0.50 | PASS |
| DSR probability | 0.4160 | > 0.90 | FAIL |
| PBO | 0.0121 | < 0.50 | PASS |
| IS-OOS rank correlation | -0.1411 | > 0 | FAIL |

### 6. Benchmark Comparison (from Cycle 3)

| Benchmark | Test Sharpe | Strategy Alpha |
|-----------|-------------|---------------|
| 1/N Equal-Weight | 0.472 | 0.0302 |
| SPY Buy-Hold | 0.579 | 0.0214 |

---

## Final Assessment

**PROMOTION GATES NOT MET** — Best combined Sharpe = 0.779 (target >= 0.90).

**Key Evidence**:
- Walk-forward: 48 folds, mean OOS Sharpe 0.679, 98% positive
- PBO: 0.012 (low overfitting risk across 560 configs)
- PSR: 0.983 (high probability of genuine edge)
- DSR: 0.416 (not significant after multiple-testing correction)
- Parameter plateau: FAILED (baseline on a peak, not plateau)
- IS-OOS rank correlation: -0.141 (weak consistency)

**Risk overlay progression**:
- Baseline: Sharpe 0.645, DD -30.4%
- Best single overlay (dd_control_0.15): Sharpe 0.818, DD -20.9%
- 226-day lookback: Sharpe 0.705
- Best combined (combined_vol_0.1_dd_0.15): Sharpe 0.7794, DD -16.25%

**Gap to promotion**: 0.1206 Sharpe points

---

## Next Steps

1. Strategy remains **Exploratory Signal** — consistent but below promotion threshold
2. **Do NOT** further tune risk overlay parameters (pre-specified grid exhausted)
3. Next cycle should explore: regime-aware filters, alternative universe selection, or
   different structural mechanisms (funding/carry, session effects, rebalancing flows)
4. Consider whether the 0.9 Sharpe gate is appropriate for this strategy class

---

## Artifacts Referenced

| Artifact | Path |
|----------|------|
| Combined Risk Overlay | `research/experiments/tsmomentum_combined_risk_001.md` |
| Hypothesis v003 | `research/hypotheses/tsmomentum_003.md` |
| Cycle 3 Decision | `research/reports/tsmomentum_decision_001.md` |
| Cycle 3 Statistics | `research/experiments/tsmomentum_statistics_001.md` |
| Cycle 3 Risk Overlays | `research/experiments/tsmomentum_risk_001.md` |

---

*Decision document generated: 2026-10-11*
*Code revision: 92893b9*
