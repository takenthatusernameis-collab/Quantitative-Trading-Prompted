# Hypothesis: US Equity Time-Series Momentum (tsmomentum_002)

## Version History

- v001 (tsmomentum_001, 2026-10-10): Initial hypothesis for Cycle 2 baseline
- v002 (tsmomentum_002, 2026-10-11): Updated based on Cycle 3 robustness & validation

**Parent hypothesis**: `research/hypotheses/tsmomentum_001.md`
**Code revision**: 8950948

---

## Mechanism Description

Unchanged from tsmomentum_001. Time-series momentum exploits the tendency for
assets with positive recent returns to continue outperforming. Structural
explanations (investor underreaction, disposition effect, institutional
constraints, funding/carry) remain valid.

---

## Updated Expected Direction and Magnitude

| Metric | Baseline Estimate (v001) | Updated (v002) |
|--------|--------------------------|----------------|
| Annualized Return | 3-8% gross, 2-7% net | 7.7% net (Sharpe-based estimate) |
| Net Sharpe | 0.5-1.0 | 0.64 (test period) |
| DSR-adjusted confidence | Not assessed | 41.6% |

The test-period Sharpe is 0.645.
After deflating for 100 configurations,
the DSR probability is 41.6%, indicating
questionable statistical significance.

---

## Holding Horizon

Unchanged: Monthly rebalancing, 12-month lookback excluding 21-day skip.

---

## Asset Universe

Unchanged: SPY, QQQ, IWM (equities), TLT (bonds), GLD (gold), EFA, EEM (intl).

---

## Features and Data Sources

Unchanged: Yahoo Finance daily OHLCV.

---

## Entry/Exit Rules

Unchanged: Monthly rebalancing, equal-weight long positions in top fraction
by 12-month momentum.

---

## Benchmark

Unchanged: 1/N portfolio, SPY buy-and-hold, risk-free rate.

---

## Robustness Findings (Cycle 3)

### Parameter Sensitivity

- **Grid tested**: 100 configurations
  (5 lookbacks x 4 skips x 5 top-fractions)
- **Baseline test Sharpe**: 0.6445
- **Configs outperforming baseline**: 0 / 100
- **On plateau?**: False
- **Plateau fraction (within 0.05 Sharpe)**: 5.0%

**Conclusion**: The baseline parameters sit on a performance peak/island, indicating sensitivity to parameter choice.

### Parameter Perturbation (+/- 10%)


Baseline not found in perturbation results.

### Walk-Forward Testing

- **Rolling WFA**: see walkforward_001.md
  (see walkforward_001.md for full details)
- **Expanding WFA**: Also documented in walkforward_001.md

### Statistical Significance

| Test | Result |
|------|--------|
| PSR vs 0 | 0.9830 |
| DSR | -0.2120 (prob: 41.6%) |
| PBO | 0.0121 |
| FDR significant configs | 100 / 100 |

### Risk Overlays

Risk overlays tested volatility targeting (10/15/20%) and drawdown control
(15%/20%). See risk_001.md for details.

---

## Updated Falsification Conditions

The hypothesis is **falsified** (downgraded to Rejected) if ANY of:

1. **Net test Sharpe < 0.5** (unchanged)
2. **Test Sharpe < Train Sharpe - 1σ** (unchanged)
3. **Max Drawdown > 30%** (unchanged)
4. **Profit Factor < 1.0** (unchanged)
5. **NEW**: PBO > 0.50 (probability of backtest overfitting exceeds 50%)
6. **NEW**: DSR probability < 90% (edge not statistically significant after multiple-testing)
7. **NEW**: Baseline parameters NOT on a plateau (sensitivity > 50% configs within 0.05 Sharpe)

---

## Updated Cost Model Assumptions

Unchanged from tsmomentum_001. Commission 1 bps, slippage 2 bps, RF 2%,
all from config/settings.yaml.

---

## References

Same as tsmomentum_001, plus:
- Bailey, Borwein, López de Prado (2017) "The Deflated Sharpe Ratio"
- Bailey, Borwein, López de Prado, Zhu (2017) "The Probability of Backtest Overfitting"
- Benjamini, Hochberg (1995) "Controlling the False Discovery Rate"
- Politis, Romano (1994) "The Stationary Bootstrap"

---

*Updated: 2026-10-11*
*Code revision: 8950948*
