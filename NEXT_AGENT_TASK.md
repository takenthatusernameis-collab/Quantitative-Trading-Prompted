# Next Agent Task: Cycle 5 - Regime-Aware Filter Exploration

## Context

Cycle 4 completed the combined risk overlay promotion test for the US Equity
Time-Series Momentum strategy.

### Cycle 4 Key Findings

| Criterion | Result | Threshold | Status |
|-----------|--------|-----------|--------|
| Best Combined Sharpe (test) | 0.7794 | ≥ 0.9 | FAIL |
| Best Config | combined_vol_0.1_dd_0.15 (lookback=226) | — | — |
| Max DD (best) | -16.25% | > -30% | PASS |
| Trades (best) | 1,812 | > 100 | PASS |
| Gap to promotion | 0.1206 Sharpe points | — | — |

### Classification: Exploratory Signal (Retained)

The combined risk overlay **does not meet** the 0.9 Sharpe promotion gate.
The best configuration (`combined_vol_0.1_dd_0.15` with 226-day lookback)
achieves test Sharpe = 0.779, an improvement over baseline (0.645) and
single overlays (best single: dd_control_0.15 at 0.818), but falls short
of the promotion threshold.

**Risk overlay progression summary:**
- Baseline (252): Sharpe 0.645, DD -30.4%
- dd_control_0.15: Sharpe 0.818, DD -20.9%
- vol_target_0.10: Sharpe 0.707, DD -18.5%
- 226-day lookback: Sharpe 0.705
- Best combined (226, vol=0.10, dd=0.15): Sharpe 0.779, DD -16.3%

### Evidence Summary

All 3 Cycle 4 artifacts are complete and validated:
- `research/experiments/tsmomentum_combined_risk_001.md`
- `research/reports/tsmomentum_decision_002.md`
- `research/hypotheses/tsmomentum_003.md`

Cycle 3 artifacts remain reproducible (verified via `python3 research/run_cycle3.py`).

---

## Objective

Explore **regime-aware filters** or **alternative universe selection** to
improve the strategy's risk-adjusted returns, as risk overlay tuning has been
exhausted (pre-specified grid of 8 combinations tested).

The hypothesis: Time-series momentum performs differently across market regimes
(e.g., equity bull/bear, high/low volatility, inflation regimes). Filtering or
adapting to regimes may improve net Sharpe toward the 0.9 promotion gate.

---

## Acceptance Criteria

1. **Regime Analysis** at `research/experiments/tsmomentum_regime_001.md`:
   - Define 2-3 regime classification methods (e.g., SPY trend, VIX level,
     inflation proxy, moving average regimes)
   - Segment the test period (2018-2026) by regime
   - Report per-regime strategy performance (Sharpe, return, DD, trades)
   - Identify regimes where strategy underperforms/outperforms

2. **Regime Filter Test** at `research/experiments/tsmomentum_regime_filter_001.md`:
   - Test 1-2 regime filters (e.g., "go to cash when SPY < 200-day MA",
     "reduce exposure when VIX > 30")
   - Apply filters to the best Cycle 4 config (226-day, vol=0.10, dd=0.15)
   - Report test-period metrics for filtered vs unfiltered
   - Test if any filter achieves Sharpe >= 0.9

3. **Alternative Universe Test** at `research/experiments/tsmomentum_universe_001.md`:
   - Test 1-2 alternative universes (e.g., sector ETFs, factor ETFs,
     global asset classes)
   - Use same best config parameters (226-day, vol=0.10, dd=0.15)
   - Report test-period metrics
   - Compare to baseline 7-asset universe

4. **Updated Decision** at `research/reports/tsmomentum_decision_003.md`:
   - Incorporate regime/universe findings
   - If Sharpe >= 0.9 with any filter/universe: **Credible Candidate**
   - Otherwise: **Exploratory Signal** with updated rationale

5. **Updated Hypothesis** at `research/hypotheses/tsmomentum_004.md`:
   - Incorporate regime/universe findings
   - Document new conditional entry/exit rules if applicable

6. **Reproduce existing results**:
   - Verify `python3 research/run_cycle3.py` still runs without errors
   - Verify `python3 research/run_cycle4.py` still runs without errors

---

## Implementation Notes

### Pre-specified regime filters (no cherry-picking)

Test ONLY these regime filters (defined before seeing results):

1. **SPY Trend Filter**: Go to cash (0% exposure) when SPY < 200-day SMA.
   Re-enter when SPY > 200-day SMA.

2. **VIX Volatility Filter**: Reduce exposure to 50% when VIX > 30.
   Full exposure when VIX ≤ 30. (Use ^VIX from Yahoo Finance)

### Pre-specified alternative universes

Test ONLY these universes:

1. **Sector ETFs**: XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY (9 sectors)
2. **Global Asset Classes**: SPY, EFA, EEM, TLT, GLD, DBC, VNQ (7 assets,
   similar to baseline but adds commodities + REITs)

### Scope Boundaries

- **Do not** add new risk overlay parameters (pre-specified grid exhausted)
- **Do not** tune filter parameters beyond the pre-specified definitions above
- **Do** use existing pipeline infrastructure
- **Do** document all negative results honestly
- **Do** use chronological splits only (train/val/test unchanged)
- **Do** preserve all existing artifacts (do not overwrite or delete)

---

## Validation Commands

```bash
# Verify new artifacts exist
test -f research/experiments/tsmomentum_regime_001.md
test -f research/experiments/tsmomentum_regime_filter_001.md
test -f research/experiments/tsmomentum_universe_001.md
test -f research/reports/tsmomentum_decision_003.md
test -f research/hypotheses/tsmomentum_004.md

# Verify content
grep -c "Regime" research/experiments/tsmomentum_regime_001.md
grep -c "Filter" research/experiments/tsmomentum_regime_filter_001.md
grep -c "Universe" research/experiments/tsmomentum_universe_001.md
grep -c "Decision" research/reports/tsmomentum_decision_003.md

# Re-verify Cycle 3 & 4 scripts
python3 research/run_cycle3.py
python3 research/run_cycle4.py

# Lint check
python3 -m ruff check src/evaluation/ --fix
```

---

## Expected Outcome

If any regime filter or alternative universe achieves test Sharpe >= 0.9 with
max DD > -30% and >100 OOS trades, the strategy is promoted to **Credible
Candidate** and the next cycle advances to simulation/parameter optimization.

If not, the strategy remains **Exploratory Signal** and the next cycle should
explore different structural mechanisms (funding/carry, session effects,
rebalancing flows, cross-asset momentum) rather than further regime/universe
variations on time-series momentum.

---

## Evidence Reference

- Cycle 4 best combined Sharpe: 0.7794 (source: `tsmomentum_combined_risk_001.md`)
- Cycle 4 best config: lookback=226, vol_target=0.10, dd_control=0.15
- Cycle 3 baseline test Sharpe: 0.645
- Cycle 3 best single overlay: dd_control_0.15 → Sharpe 0.818
- Code base: `92893b9`