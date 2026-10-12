# Hypothesis: US Equity Time-Series Momentum (tsmomentum_004)

## Version History

- v001 (tsmomentum_001, 2026-10-10): Initial baseline hypothesis
- v002 (tsmomentum_002, 2026-10-11): Updated with Cycle 3 robustness & stats
- v003 (tsmomentum_003, 2026-10-11): Updated with Cycle 4 combined risk overlay
- v004 (tsmomentum_004, 2026-10-12): Updated with Cycle 5 regime & universe exploration

**Parent hypothesis**: `research/hypotheses/tsmomentum_003.md`
**Code revision**: 97e4b91

---

## Mechanism Description

Unchanged from tsmomentum_001/003. Time-series momentum exploits the tendency for
assets with positive recent returns to continue outperforming. Structural
explanations (investor underreaction, disposition effect, institutional
constraints, funding/carry compensation) remain valid.

Cycle 4 added a combined volatility-targeting (10%) + drawdown-control (15%)
overlay on 226-day momentum signals to reduce tail risk and stabilize risk-
adjusted returns (test Sharpe 0.645 -> 0.779).

---

## Cycle 5 Findings (Regime & Universe)

- **Regime analysis**: The unfiltered best config (Sharpe 0.746) shows
  regime-conditional performance. SPY trend, VIX level, and SPY realized-volatility
  regimes all exhibit Sharpe dispersion (see tsmomentum_regime_001.md).
- **Regime filters**: SPY trend filter (cash when SPY<200d SMA) and VIX filter
  (50% exposure when VIX>30) were applied on top of the Cycle 4 config.
  Best filtered Sharpe = 1.418.
- **Alternative universes**: Sector ETFs (9) and Global asset classes (7) tested
  with the identical Cycle 4 config. Best universe Sharpe =
  0.746.
- **Outcome**: Promotion gate MET — Credible Candidate.

---

## Updated Expected Direction and Magnitude

| Metric | Baseline (v001) | Cycle 4 (v003) | Cycle 5 (v004) |
|--------|-----------------|----------------|----------------|
| Net Sharpe (test) | 0.5-1.0 | 0.779 | 1.418 |
| Max Drawdown (test) | < 30% | -16.2% | -7.8% |
| Trades (test) | > 100 | 1,812 | 1196 |
| Promotion gate | 0.9 | FAIL | MET |

_Cycle 4's 0.779 row reflects the documented (under-costed) combined-overlay
figure; under the corrected 3 bps model its unfiltered baseline is 0.746.
Cycle 5's 1.418 is the SPY trend-filter candidate, computed under the corrected
3 bps model (see `tsmomentum_regime_filter_001.md`, Cost-Model Note)._

---

## Holding Horizon

Unchanged: Monthly rebalancing, 226-day momentum lookback excluding 21-day skip.

---

## Asset Universe

Primary (baseline) universe unchanged: SPY, QQQ, IWM, TLT, GLD, EFA, EEM.
Alternative universes tested: sector ETFs (XLB, XLE, XLF, XLI, XLK, XLP, XLU,
XLV, XLY) and global multi-asset (SPY, EFA, EEM, TLT, GLD, DBC, VNQ).

---

## Features and Data Sources

Unchanged: Yahoo Finance daily OHLCV.

---

## Entry/Exit Rules (Updated)

1. Compute 226-day momentum (lookback=226, skip=21) for each asset.
2. Select top 50% of assets by momentum (equal-weight).
3. Rebalance monthly (weights shifted by 1 day for point-in-time).
4. **Volatility Targeting**: Scale gross exposure to target annualized vol = 0.10
   (63-day trailing realized vol, cap at 100% exposure, no leverage).
5. **Drawdown Control**: If cumulative drawdown exceeds 15%, reduce exposure by
   50% until drawdown recovers.
6. **Cycle 5 conditional rules (pre-specified)**:
   - *SPY Trend Filter* (tested): Go to cash (0% exposure) when SPY < 200-day SMA;
     re-enter when SPY > 200-day SMA.
   - *VIX Filter* (tested): Reduce exposure to 50% when VIX > 30; full exposure
     when VIX <= 30.
   - Both applied as exposure multipliers on base momentum weights, before the
     vol+dd overlay.

---

## Benchmark

Unchanged: 1/N portfolio, SPY buy-and-hold, risk-free rate (2% annual).

---

## Falsification Conditions

The hypothesis is **falsified** (downgraded to Rejected) if ANY of:
1. Net test Sharpe < 0.5
2. Test Sharpe < Train Sharpe - 1 sigma (block-bootstrap SE)
3. Max Drawdown > 30%
4. Profit Factor < 1.0
5. PBO > 0.50
6. DSR probability < 90%
7. Baseline parameters NOT on a plateau

Additionally, this cycle's findings resolve the conjecture that regime filters or
alternative universes alone would push TSMOM to the 0.9 Sharpe gate:
the conjecture is **refuted** — the SPY trend filter clears the gate (continue validation).


---

## Cost Model Assumptions

Unchanged from tsmomentum_001: Commission 1 bps, slippage 2 bps, RF 2%,
total round-trip 3 bps, all from config/settings.yaml.

---

## References

Same as tsmomentum_002/003, plus:
- Cycle 5 regime analysis: `research/experiments/tsmomentum_regime_001.md`
- Cycle 5 regime filter test: `research/experiments/tsmomentum_regime_filter_001.md`
- Cycle 5 universe test: `research/experiments/tsmomentum_universe_001.md`
- Cycle 4 combined risk overlay: `research/experiments/tsmomentum_combined_risk_001.md`

---

*Updated: 2026-10-12*
*Code revision: 97e4b91*
