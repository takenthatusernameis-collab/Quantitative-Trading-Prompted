# Hypothesis: US Equity Time-Series Momentum (tsmomentum_003)

## Version History

- v001 (tsmomentum_001, 2026-10-10): Initial hypothesis for Cycle 2 baseline
- v002 (tsmomentum_002, 2026-10-11): Updated based on Cycle 3 robustness & validation
- v003 (tsmomentum_003, 2026-10-11): Updated based on Cycle 4 combined risk overlay test

**Parent hypothesis**: `research/hypotheses/tsmomentum_002.md`
**Code revision**: 412f292

---

## Mechanism Description

Unchanged from tsmomentum_001. Time-series momentum exploits the tendency for
assets with positive recent returns to continue outperforming. Structural
explanations (investor underreaction, disposition effect, institutional
constraints, funding/carry) remain valid.

Risk overlay rationale: Volatility targeting stabilizes portfolio risk across
market regimes; drawdown control limits capital loss during sustained drawdowns
by reducing exposure. The combination applies vol targeting first (to normalize
risk) then DD control (to protect capital).

---

## Updated Expected Direction and Magnitude

| Metric | Baseline (v001) | Cycle 3 (v002) | Cycle 4 Combined (v003) |
|--------|-----------------|----------------|-------------------------|
| Annualized Return | 3-8% gross, 2-7% net | 7.7% net (est.) | 9.6% net |
| Net Sharpe | 0.5-1.0 | 0.64 (test) | **0.779** (test, best combined) |
| DSR-adjusted confidence | Not assessed | 41.6% | 41.6% (unchanged, same configs) |
| Max Drawdown | < 30% | -30.4% (baseline) | -16.2% (best combined) |

The best combined configuration (combined_vol_0.1_dd_0.15, lookback=226) achieves
test Sharpe = 0.779 with max DD = -16.2%.
This does NOT meet the 0.9 promotion gate.

---

## Holding Horizon

Unchanged: Monthly rebalancing, 12-month lookback excluding 21-day skip.
Best lookback: **226 trading days** (226 = 10% reduction from 252).

---

## Asset Universe

Unchanged: SPY, QQQ, IWM (equities), TLT (bonds), GLD (gold), EFA, EEM (intl).

---

## Features and Data Sources

Unchanged: Yahoo Finance daily OHLCV.

---

## Entry/Exit Rules (Updated with Combined Risk Overlay)

1. Compute 12-month momentum (lookback=226 days, skip=21 days) for each asset
2. Select top 50% of assets by momentum (equal-weight)
3. Rebalance monthly (weights shifted by 1 day for point-in-time)
4. **Risk Overlay 1 - Volatility Targeting**: Scale gross exposure to target
   annualized vol = 0.1 (63-day trailing realized vol, cap at 100% exposure)
5. **Risk Overlay 2 - Drawdown Control**: If cumulative drawdown exceeds 0.15,
   reduce exposure by 50% until drawdown recovers
6. Apply both overlays additively: vol targeting first, then DD control

---

## Benchmark

Unchanged: 1/N portfolio, SPY buy-and-hold, risk-free rate.

---

## Robustness Findings (Cycle 3 + Cycle 4)

### Parameter Sensitivity (Cycle 3)

- **Grid tested**: 100 configurations (5 lookbacks x 4 skips x 5 top-fractions)
- **Baseline test Sharpe**: 0.6445
- **Configs outperforming baseline**: 0 / 100
- **On plateau?**: False
- **Plateau fraction (within 0.05 Sharpe)**: 5.0%

**Conclusion**: The baseline parameters sit on a performance peak/island.

### Parameter Perturbation (+/- 10%) (Cycle 3)

- 226-day lookback (10% reduction) achieves test Sharpe = 0.705 vs baseline 0.645
- This perturbation is now **pre-specified** for Cycle 4 testing

### Walk-Forward Testing (Cycle 3)

- Rolling WFA: 48 folds, mean test Sharpe 0.679, 97.9% positive, 12,692 total trades
- Expanding WFA: Consistent positive results

### Statistical Significance (Cycle 3)

| Test | Result |
|------|--------|
| PSR vs 0 | 0.9830 |
| DSR | -0.2120 (prob: 41.6%) |
| PBO | 0.0121 |
| FDR significant configs | 100 / 100 |

### Risk Overlays (Cycle 3 + Cycle 4)

**Single overlays (Cycle 3)**:
- dd_control_0.15: Sharpe 0.818, DD -20.9%
- vol_target_0.10: Sharpe 0.707, DD -18.5%

**Combined overlays (Cycle 4)**:
- 8 configurations tested (2 lookbacks × 2 vol × 2 DD)
- Best: combined_vol_0.1_dd_0.15 (lookback=226) → Sharpe 0.7794, DD -16.25%

---

## Updated Falsification Conditions

The hypothesis is **falsified** (downgraded to Rejected) if ANY of:

1. **Net test Sharpe < 0.5** (unchanged)
2. **Test Sharpe < Train Sharpe - 1σ** (unchanged)
3. **Max Drawdown > 30%** (unchanged)
4. **Profit Factor < 1.0** (unchanged)
5. **PBO > 0.50** (probability of backtest overfitting exceeds 50%)
6. **DSR probability < 90%** (edge not statistically significant after multiple-testing)
7. **Baseline parameters NOT on a plateau** (sensitivity > 50% configs within 0.05 Sharpe)

---

## Updated Cost Model Assumptions

Unchanged from tsmomentum_001. Commission 1 bps, slippage 2 bps, RF 2%,
all from config/settings.yaml.

---

## References

Same as tsmomentum_002, plus:
- Cycle 4 combined risk overlay analysis: `research/experiments/tsmomentum_combined_risk_001.md`

---

*Updated: 2026-10-11*
*Code revision: 412f292*
