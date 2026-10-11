# Decision: Time-Series Momentum Strategy (tsmomentum_decision_001)

**Date**: 2026-10-11
**Code revision**: 8950948

---

## Executive Summary

The US Equity Time-Series Momentum strategy (7-asset, 12-month momentum,
monthly rebalancing) is classified as:

## **Exploratory Signal**

Mixed evidence — some criteria pass, some fail.

---

## Evidence Summary

### 1. Promotion Gates

| Gate | Threshold | Observed | Status |
|------|-----------|----------|--------|
| Net OOS Sharpe ≥ 0.9 | 0.90 | 0.645 | FAIL |
| >100 pooled OOS trades | 100 | 190 | PASS |
| Max DD > -30% | -30% | -30.41% | FAIL |

**Promotion gate (Sharpe AND trades)**: NOT MET

### 2. Baseline Falsification Checks

| Check | Threshold | Observed | Status |
|-------|-----------|----------|--------|
| Test Sharpe ≥ 0.5 | 0.50 | 0.645 | PASS |
| Max DD > -30% | -30% | -30.41% | FAIL |
| Profit Factor ≥ 1.0 | 1.00 | 1.15 | PASS |

### 3. Robustness

| Criterion | Value | Threshold | Status |
|-----------|-------|-----------|--------|
| Parameter plateau | False | True | FAIL |
| Configs outperforming baseline | 0/100 | ≤50% | PASS |
| Walk-forward mean Sharpe | 0.679 | > 0.3 | PASS |
| % Positive WF folds | 97.9% | > 50% | PASS |
| WF total trades | 12692 | > 100 | PASS |

### 4. Statistical Significance

| Test | Observed | Threshold | Status |
|------|----------|-----------|--------|
| PSR vs 0 | 0.9830 | > 0.50 | PASS |
| DSR probability | 0.4160 | > 0.90 | FAIL |
| PBO | 0.0121 | < 0.50 | PASS |
| PBO configs tested | 560 | ≥ 500 | PASS |
| FDR significant configs | 100/100 | > 0 | PASS |
| IS-OOS rank correlation | -0.1411 | > 0 | FAIL |

### 5. Benchmark Comparison

| Benchmark | Test Sharpe | Strategy Alpha |
|-----------|-------------|---------------|
| 1/N Equal-Weight | 0.472 | 0.0302 |
| SPY Buy-Hold | 0.579 | 0.0214 |
| Risk-Free | 0.000 | — |

Strategy Sharpe (0.645) vs 1/N (0.472): IR = 0.1729
Strategy Sharpe vs SPY (0.579): IR = 0.0657

### 6. Risk Overlays

| Overlay | Sharpe | Max DD | DD < -30%? | Sharpe > 0.5? |
|---------|--------|--------|------------|---------------|
| Baseline | 0.645 | -30.41% | Yes | Yes |
| vol_target_0.1 | 0.7072 | -18.51% | No | Yes |
| vol_target_0.15 | 0.6273 | -25.95% | No | Yes |
| vol_target_0.2 | 0.6096 | -30.09% | Yes | Yes |
| dd_control_0.15 | 0.8184 | -20.89% | No | Yes |
| dd_control_0.2 | 0.7849 | -19.86% | No | Yes |


Best risk overlay: **dd_control_0.15** (Sharpe = 0.818, Max DD = -20.89%)

---

## Final Assessment

**4/8 key criteria passed.**

### Detailed Outcome

1. **Promotion gates**: Sharpe ≥ 0.9: NOT MET (0.645)
   | Trades > 100: MET (190)

2. **Parameter sensitivity**: Baseline is parameter-sensitive —
   0 of 100 configs outperform the baseline.

3. **Walk-forward**: 12692 pooled OOS trades, mean Sharpe 0.679,
   98% of folds positive.

4. **Statistical tests**: PSR = 0.983,
   DSR probability = 0.416,
   PBO = 0.012 (560 configs tested for PBO/CSCV).

5. **Benchmark**: Strategy Sharpe 0.645 vs 1/N 0.472 and SPY 0.579.
   Alpha vs SPY = 0.0214
   (p = 0.4326).

6. **Risk overlays**: Best overlay (dd_control_0.15) achieves Sharpe 0.818
   with max DD -20.89%. Drawdown control successfully brings max DD below -30%.

---

## Next Steps

**Recommended next steps**:
1. Test combined risk overlays (volatility targeting + drawdown control together)
   to improve Sharpe toward the 0.9 promotion gate
2. Investigate whether parameter re-optimization via walk-forward improves results
3. Consider adding a volatility-based filter or regime filter to avoid crisis periods
4. If Sharpe cannot be improved above 0.9, the strategy remains an exploratory signal
   with promising but not promotion-gate-passing performance

**Key insight**: The strategy shows consistent but modest performance
(test Sharpe = 0.645). Walk-forward results and PBO < 0.5 indicate
no significant overfitting, but the Sharpe ratio falls short of the 0.9
promotion gate. Risk overlays offer the best path to improvement.


---

## Artifacts Referenced

| Artifact | Path |
|----------|------|
| Hypothesis v001 | `research/hypotheses/tsmomentum_001.md` |
| Hypothesis v002 | `research/hypotheses/tsmomentum_002.md` |
| Baseline experiment | `research/experiments/tsmomentum_baseline_001.md` |
| Robustness | `research/experiments/tsmomentum_robustness_001.md` |
| Walk-forward | `research/experiments/tsmomentum_walkforward_001.md` |
| Statistics | `research/experiments/tsmomentum_statistics_001.md` |
| Benchmark | `research/experiments/tsmomentum_benchmark_001.md` |
| Risk overlays | `research/experiments/tsmomentum_risk_001.md` |

---

*Decision document generated: 2026-10-11*
*Code revision: 8950948*
