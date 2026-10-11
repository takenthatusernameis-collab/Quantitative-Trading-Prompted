# Next Agent Task: Cycle 4 - Risk-Adjusted Promotion Test

## Context

Cycle 3 completed rigorous robustness and statistical validation of the US Equity
Time-Series Momentum baseline strategy.

### Cycle 3 Key Findings

| Criterion | Result | Threshold | Status |
|-----------|--------|-----------|--------|
| Net OOS Sharpe (test) | 0.645 | ≥ 0.9 | FAIL |
| PSR vs 0 | 0.983 | > 0.50 | PASS |
| DSR probability | 0.416 | > 0.90 | FAIL |
| PBO | 0.012 | < 0.50 | PASS |
| Walk-forward mean Sharpe (48 folds) | 0.679 | > 0.3 | PASS |
| % Positive WF folds | 97.9% | > 50% | PASS |
| Parameter plateau | No | Yes | FAIL |
| IS-OOS rank correlation | -0.14 | > 0 | FAIL |

### Classification: Exploratory Signal

The baseline does not meet the 0.9 Sharpe promotion gate. However, risk overlays
show promise for closing the gap:

| Overlay | Test Sharpe | Max DD | Below -30%? |
|---------|-------------|--------|-------------|
| Baseline | 0.645 | -30.41% | No (fails) |
| dd_control_0.15 | 0.818 | -20.89% | Yes |
| dd_control_0.20 | 0.785 | -19.86% | Yes |
| vol_target_0.10 | 0.707 | -18.51% | Yes |
| vol_target_0.15 | 0.627 | -25.95% | Yes |

Additionally, the ±10% parameter perturbation found that a **226-day lookback**
(10% less than baseline 252) achieves test Sharpe = 0.705 vs baseline 0.645.

### Evidence Summary

All 7 Cycle 3 artifacts are complete and validated:
- `research/experiments/tsmomentum_robustness_001.md`
- `research/experiments/tsmomentum_walkforward_001.md`
- `research/experiments/tsmomentum_statistics_001.md`
- `research/experiments/tsmomentum_benchmark_001.md`
- `research/experiments/tsmomentum_risk_001.md`
- `research/hypotheses/tsmomentum_002.md`
- `research/reports/tsmomentum_decision_001.md`

---

## Objective

Determine whether **combining risk overlays** (volatility targeting + drawdown
control) and the **perturbed 226-day lookback** can elevate the strategy's test-
period net Sharpe ratio to >= 0.9, promoting it from "Exploratory Signal" to
"Credible Candidate."

The hypothesis is evidence-based: individual risk overlays and the 226-day
perturbation each independently improve Sharpe, suggesting a combination may be
sufficient to cross the 0.9 threshold.

---

## Acceptance Criteria

1. **Combined Risk Overlay Analysis** at
   `research/experiments/tsmomentum_combined_risk_001.md`:
   - Test all 4 combinations of {vol_target: 0.10, 0.15} × {dd_control: 0.15, 0.20}
   - Apply each combination to both baseline (252-day) and perturbed (226-day)
     lookback parameters
   - Report per-combination: test Sharpe, annualized return, max DD, sortino,
     profit factor, trade count
   - Identify the best combination by Sharpe, and test if it achieves Sharpe >= 0.9

2. **Updated Decision** at `research/reports/tsmomentum_decision_002.md`:
   - Recalculate promotion gates with the best combined overlay
   - If Sharpe >= 0.9 AND > 100 OOS trades AND max DD > -30%: label as
     **Credible Candidate**
   - Otherwise: retain **Exploratory Signal** with updated rationale

3. **Updated Hypothesis** at `research/hypotheses/tsmomentum_003.md`:
   - Incorporate the combined overlay finding
   - Update expected Sharpe range to include the risk-adjusted estimate
   - Document the new parameter + overlay combination

4. **Reproduce existing results** (unchanged from Cycle 3):
   - Verify all 7 Cycle 3 artifacts still pass their validation checks
   - Verify `research/run_cycle3.py` still runs end-to-end without errors

---

## Implementation Notes

### Pre-specified configurations (no cherry-picking)

The 226-day lookback is NOT a new parameter selection — it was discovered via
the ±10% perturbation analysis in Cycle 3 and is now pre-specified based on
that evidence. The combinations to test:

- (lookback=252, skip=21, top_frac=0.5) + {vol=0.10, dd=0.15}
- (lookback=252, skip=21, top_frac=0.5) + {vol=0.10, dd=0.20}
- (lookback=252, skip=21, top_frac=0.5) + {vol=0.15, dd=0.15}
- (lookback=252, skip=21, top_frac=0.5) + {vol=0.15, dd=0.20}
- (lookback=226, skip=21, top_frac=0.5) + {vol=0.10, dd=0.15}
- (lookback=226, skip=21, top_frac=0.5) + {vol=0.10, dd=0.20}
- (lookback=226, skip=21, top_frac=0.5) + {vol=0.15, dd=0.15}
- (lookback=226, skip=21, top_frac=0.5) + {vol=0.15, dd=0.20}

**Total: 8 configurations** (2 lookbacks × 4 overlay combos).

### Suggested implementation

Extend `src/evaluation/risk.py` with a `combined_risk_overlay()` function that
applies volatility targeting first, then drawdown control on the already-
vol-targeted weights. The combination should be additive: vol targeting scales
the weights, then DD control further reduces them when drawdown exceeds threshold.

---

## Validation Commands

```bash
# Verify new artifact exists
test -f research/experiments/tsmomentum_combined_risk_001.md
test -f research/reports/tsmomentum_decision_002.md
test -f research/hypotheses/tsmomentum_003.md

# Verify combined overlay section
grep -c "Combined" research/experiments/tsmomentum_combined_risk_001.md

# Verify decision
grep -c "Decision" research/reports/tsmomentum_decision_002.md

# Re-verify Cycle 3 artifacts still pass
grep -c "Heatmap" research/experiments/tsmomentum_robustness_001.md
grep -c "Deflated Sharpe" research/experiments/tsmomentum_statistics_001.md
grep -c "Probability of Backtest" research/experiments/tsmomentum_walkforward_001.md
grep -c "Alpha" research/experiments/tsmomentum_benchmark_001.md
grep -c "Volatility Target" research/experiments/tsmomentum_risk_001.md

# Run Cycle 3 script (reproducibility check)
python3 research/run_cycle3.py

# Lint check
python3 -m ruff check src/evaluation/ --fix
```

---

## Scope Boundaries

- **Do not** add new asset classes or data sources
- **Do not** tune parameters beyond the pre-specified 226-day lookback and
  the 8 configurations listed above
- **Do** use existing pipeline infrastructure (yfinance_fetcher, momentum,
  backtest engine, evaluation modules)
- **Do** document all negative results honestly
- **Do** use chronological splits only
- **Do** preserve all existing Cycle 3 artifacts (do not overwrite or delete)

---

## Expected Outcome

If the best combined overlay achieves Sharpe >= 0.9 with max DD > -30% and
> 100 OOS trades, the strategy is promoted to **Credible Candidate** and the
next cycle advances to simulation/parameter optimization. If not, the strategy
remains **Exploratory Signal** and the next cycle should explore regime-
aware filters or alternative universe selection, not further risk overlay
tuning.

---

## Evidence Reference

- Cycle 3 baseline test Sharpe: 0.645 (source: `tsmomentum_baseline_001.md`)
- Cycle 3 best single overlay Sharpe: 0.818 (dd_control_0.15, source: `tsmomentum_risk_001.md`)
- Cycle 3 perturbation finding: 226-day lookback → Sharpe 0.705 (source: `tsmomentum_statistics_001.md`)
- Code base: `8950948`
