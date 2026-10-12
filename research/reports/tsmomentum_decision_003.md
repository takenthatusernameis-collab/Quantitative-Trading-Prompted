# Decision: Time-Series Momentum Strategy (tsmomentum_decision_003)

**Date**: 2026-10-12
**Code revision**: 8d573a4

---

## Executive Summary

The US Equity Time-Series Momentum strategy (Cycle 4 best config: 7-asset
TSMOM with lookback=226, combined vol-targeting 10% + drawdown control 15%)
was extended with pre-specified regime filters and alternative universes in
Cycle 5. It is classified as:

## **Credible Candidate**

Best candidate 'SPY Trend Filter (cash when SPY<200d SMA)' achieves test Sharpe 1.418 with max DD above -30% and >100 OOS trades, meeting all promotion gates.

---

## Evidence Summary

### 1. Promotion Gates (Best Candidate)

| Gate | Threshold | Observed | Status |
|------|-----------|----------|--------|
| Net OOS Sharpe >= 0.9 | 0.90 | 1.4178 | PASS |
| >100 pooled OOS trades | 100 | 1196 | PASS |
| Max DD > -30% | -30% | -0.0779 | PASS |

**Best candidate**: SPY Trend Filter (cash when SPY<200d SMA)
**Promotion gate (ALL three)**: MET

---

### 2. Regime Analysis Summary (tsmomentum_regime_001)

Regime-conditional performance of the unfiltered best config (overall test
Sharpe 0.7458):

- **spy_trend**: Sharpe range -1.375 – 1.667 (gap 3.042)
- **vix**: Sharpe range -1.649 – 3.094 (gap 4.743)
- **spy_vol**: Sharpe range 0.605 – 0.904 (gap 0.299)

**Widest regime spread**: vix (Sharpe gap 4.743 between best
and worst regime bucket). This indicates meaningful
regime-conditional behavior, motivating the regime-filter test.

---

### 3. Regime Filter Test Summary (tsmomentum_regime_filter_001)

| Filter | Test Sharpe | Max DD | Trades | Meets 0.9? |
|--------|-------------|--------|--------|------------|
| Unfiltered (Cycle 4 best) | 0.7458 | -0.1660 | 1812 | No |
| SPY Trend Filter (cash when SPY<200d SMA) | 1.4178 | -0.0779 | 1196 | YES |
| VIX Filter (50% exposure when VIX>30) | 1.0463 | -0.1227 | 1768 | YES |

Best filter Sharpe: 1.4178
(unchanged baseline: 0.7458).

---

### 4. Alternative Universe Test Summary (tsmomentum_universe_001)

| Universe | Test Sharpe | Max DD | Trades | Meets 0.9? |
|----------|-------------|--------|--------|------------|
| Baseline (SPY,QQQ,IWM,TLT,GLD,EFA,EEM) | 0.7458 | -0.1660 | 1812 | No |
| Sector ETFs (XLB,XLE,XLF,XLI,XLK,XLP,XLU,XLV,XLY) | 0.4415 | -0.1510 | 1964 | No |
| Global Asset Classes (SPY,EFA,EEM,TLT,GLD,DBC,VNQ) | 0.5515 | -0.1516 | 1717 | No |

Best universe Sharpe: 0.7458
(vs baseline 0.7458).

---

### 5. Prior Evidence (Cycle 3 + 4)

| Criterion | Value | Threshold | Status |
|-----------|-------|-----------|--------|
| Walk-forward mean Sharpe | 0.679 | > 0.3 | PASS |
| % Positive WF folds | 97.9% | > 50% | PASS |
| PSR vs 0 | 0.9830 | > 0.50 | PASS |
| PBO | 0.0121 | < 0.50 | PASS |
| DSR probability | 0.4160 | > 0.90 | FAIL |
| Parameter plateau | False | True | FAIL |
| Baseline test Sharpe | 0.6445 | >= 0.9 | FAIL |

---

## Final Assessment

**PROMOTION GATE MET** — Best Sharpe across all Cycle 5
candidates = 1.4178 (target >= 0.90; gap = 0.0000).

**Risk overlay progression**:
- Baseline (252-day): Sharpe 0.645, DD -30.4%
- Best single overlay (dd_control_0.15): Sharpe 0.818, DD -20.9%
  - Best combined (Cycle 4, documented *under-costed* ~0 bps): Sharpe 0.779, DD -16.25%
  - Best combined (Cycle 4, corrected 3 bps): Sharpe 0.746, DD -16.60%
  - Best Cycle 5 candidate (SPY Trend Filter (cash when SPY<200d SMA)): Sharpe 1.4178, DD -7.79%

  **Conclusion**: The promotion gate is met; the strategy advances as a Credible Candidate (preliminary). Per AGENTS.md, a promotion gate is a *preliminary* screening gate only — prospective paper-trading validation, walk-forward re-testing of the regime filter, and confirmation that the cost-model defect in src/evaluation/risk.py does not affect the conclusion are required before any real-money deployment.

---

## Next Steps

1. **Promoted to Credible Candidate (preliminary)**: SPY Trend Filter (cash when SPY<200d SMA)
2. **Cycle 6 first**: validate the candidate via walk-forward testing + parameter-plateau check of the regime filter (not yet independently validated across time)
3. Then advance to simulation / parameter optimization
4. Paper-trading / prospective validation before any real-money exposure
5. **Recommended bounded correction (non-blocking)**: fix the overlay-path cost bug in `src/evaluation/risk.py` (see Cost-Model Note) so Cycle 4's documented combined-overlay Sharpe is recomputed under correct 3 bps costs

---

## Artifacts Referenced

| Artifact | Path |
|----------|------|
| Regime Analysis | `research/experiments/tsmomentum_regime_001.md` |
| Regime Filter Test | `research/experiments/tsmomentum_regime_filter_001.md` |
| Alternative Universe Test | `research/experiments/tsmomentum_universe_001.md` |
| Combined Risk Overlay (Cycle 4) | `research/experiments/tsmomentum_combined_risk_001.md` |
| Hypothesis v003 | `research/hypotheses/tsmomentum_003.md` |
| Cycle 3 Decision | `research/reports/tsmomentum_decision_001.md` |
| Cycle 3 Statistics | `research/experiments/tsmomentum_statistics_001.md` |
| Cycle 3 Walk-Forward | `research/experiments/tsmomentum_walkforward_001.md` |

---

*Decision document generated: 2026-10-12*
*Code revision: 8d573a4*
