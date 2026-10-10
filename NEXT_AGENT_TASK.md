# Next Agent Task: Cycle 3 - Robustness & Statistical Validation

## Context

Cycle 2 completed the baseline US Equity Time-Series Momentum backtest. The
end-to-end pipeline (data ingestion → feature engineering → backtest →
evaluation → documentation) is validated and working.

### Baseline Results Summary

| Period | Sharpe | Ann. Return | Max DD | Trades |
|--------|--------|-------------|--------|--------|
| Train (1993-2009) | 0.283 | 7.69% | -61.35% | 139 |
| Validation (2010-2017) | 0.555 | 9.18% | -16.25% | 194 |
| **Test (2018-2026)** | **0.645** | **12.09%** | **-30.41%** | **190** |

### Falsification Check

- Test Sharpe (0.645) ≥ 0.5 → **PASS**
- Test Max DD (-30.41%) > -30% → **FAIL** (exceeds by 0.41%)
- Test Profit Factor (1.15) ≥ 1.0 → **PASS**
- Test Sharpe > Train Sharpe - 1σ → **PASS**

### Promotion Gates

- Net OOS Sharpe ≥ 0.9 → **NOT MET** (0.645)
- >100 pooled OOS trades → **MET** (190)

### Classification

**Exploratory Signal** — Pipeline validated; promotion gates not met. One
falsification condition triggered (max drawdown slightly exceeds threshold).

---

## Objective

Conduct rigorous robustness and statistical validation of the baseline strategy
to determine if it warrants promotion to "credible candidate" or should be
rejected. This includes parameter sensitivity analysis, walk-forward testing,
multiple-testing corrections, and proper benchmark comparison.

---

## Acceptance Criteria

1. **Parameter Sensitivity Analysis** at `research/experiments/tsmomentum_robustness_001.md`:
   - Test lookback windows: [126, 189, 252, 315, 378] trading days (6-18 months)
   - Test skip windows: [10, 21, 42, 63] trading days (0.5-3 months)
   - Test top fractions: [0.3, 0.4, 0.5, 0.6, 0.7]
   - Report heatmap of test-period Sharpe across all combinations
   - Identify if baseline (252, 21, 0.5) is on a plateau or peak

2. **Walk-Forward Testing** at `research/experiments/tsmomentum_walkforward_001.md`:
   - Expanding window: train on [1993, t], test on [t+1, t+12 months]
   - Rolling window: 10-year train, 1-year test, step 6 months
   - Purge: 21 days between train and test (matching skip window)
   - Embargo: 21 days after test period
   - Report per-fold Sharpe, return, DD, turnover; aggregate statistics

3. **Statistical Significance** at `research/experiments/tsmomentum_statistics_001.md`:
   - Deflated Sharpe Ratio (DSR) with 1,000 block bootstrap samples
   - Probabilistic Sharpe Ratio (PSR) against 0 benchmark
   - Parameter Plateau Analysis: perturbation of ±10% on all params
   - False Discovery Rate control across all tested configurations
   - Minimum 500 configurations tested for PBO/CSCV

4. **Benchmark Comparison** at `research/experiments/tsmomentum_benchmark_001.md`:
   - Equal-weighted (1/N) portfolio of same 7 assets
   - SPY buy-and-hold
   - Risk-free rate (2%)
   - Risk-adjusted alpha/beta regression (daily, monthly)
   - Correlation analysis of returns

5. **Risk Management Overlay** at `research/experiments/tsmomentum_risk_001.md`:
   - Volatility targeting (10%, 15%, 20% annualized vol)
   - Max drawdown control (reduce exposure when DD > 15%, 20%)
   - Test if overlays reduce max DD below 30% while preserving Sharpe > 0.5

6. **Updated Hypothesis** at `research/hypotheses/tsmomentum_002.md`:
   - Incorporate robustness findings
   - Update falsification conditions based on evidence
   - Document parameter stability or sensitivity

7. **Decision Document** at `research/reports/tsmomentum_decision_001.md`:
   - Label: Credible Candidate / Exploratory Signal / Rejected / Blocked
   - Evidence summary for each criterion
   - Next steps if credible; rejection rationale if rejected

---

## Validation Commands

```bash
# Verify all output files exist
test -f research/experiments/tsmomentum_robustness_001.md
test -f research/experiments/tsmomentum_walkforward_001.md
test -f research/experiments/tsmomentum_statistics_001.md
test -f research/experiments/tsmomentum_benchmark_001.md
test -f research/experiments/tsmomentum_risk_001.md
test -f research/hypotheses/tsmomentum_002.md
test -f research/reports/tsmomentum_decision_001.md

# Check key sections
grep -c "Heatmap" research/experiments/tsmomentum_robustness_001.md
grep -c "Walk-Forward" research/experiments/tsmomentum_walkforward_001.md
grep -c "Deflated Sharpe" research/experiments/tsmomentum_statistics_001.md
grep -c "Alpha" research/experiments/tsmomentum_benchmark_001.md
grep -c "Volatility Target" research/experiments/tsmomentum_risk_001.md
grep -c "Decision" research/reports/tsmomentum_decision_001.md
```

---

## Scope Boundaries

- **Do not** add new data sources or asset classes
- **Do not** tune parameters to maximize test-period returns (all configurations
  must be pre-specified or systematically explored)
- **Do** use the existing pipeline infrastructure (yfinance_fetcher, momentum,
  backtest engine)
- **Do** implement new analysis modules in `src/evaluation/` if needed
- **Do** document all negative results honestly
- **Do** track number of hypotheses/configurations tested for multiple-testing
  correction
- **Do** use chronological splits only; no random shuffling of time series

---

## Implementation Notes

### Suggested Module Structure

```
src/evaluation/
├── __init__.py
├── robustness.py       # Parameter grid search, heatmaps
├── walkforward.py      # Walk-forward splits with purge/embargo
├── statistics.py       # DSR, PSR, PBO, bootstrap CIs
├── benchmark.py        # Alpha/beta, correlation, attribution
└── risk.py             # Vol targeting, DD control overlays
```

### Key Libraries

- `arch` for block bootstrap
- `statsmodels` for regression
- `scipy` for statistical tests
- Existing: `vectorbt` may be used for walk-forward if helpful

### Cost Model

Use existing settings.yaml values (1 bps commission, 2 bps slippage, 2% RF).
Do not modify cost assumptions between experiments.

---

## Expected Timeline

This is a bounded task. If any component is blocked (e.g., insufficient data
for statistical power), document the blocker precisely and make the next task
resolve it. Do not conceal failures or invent outputs.