# Experiment: Statistical Significance (tsmomentum_statistics_001)

## Hypothesis Reference

See `research/hypotheses/tsmomentum_001.md` and
`research/hypotheses/tsmomentum_002.md`.

**Falsification condition**: PBO > 0.5 (probability of backtest overfitting
exceeds 50%) and/or DSR probability < 5% (deflated Sharpe indicates the edge
is not statistically significant after multiple-testing correction).

---

## Data Used

- **Source**: Yahoo Finance via yfinance (cached)
- **Date Range**: 1993-01-01 to 2026-10-09
- **Universe**: SPY, QQQ, IWM, TLT, GLD, EFA, EEM
- **Test Period**: 2018-01-01 to 2026-10-09 (0 trading days)
- **Point-in-Time**: Strict chronological splits; no random shuffling.

---

## 1. Probabilistic Sharpe Ratio (PSR)

Compares the observed test-period Sharpe ratio against a target of 0 (no edge).

| Metric | Value |
|--------|-------|
| Observed Sharpe | 0.6445 |
| Sharpe Standard Error (1000 block bootstrap) | 0.3041 |
| Bootstrap Mean Sharpe | 0.6682 |
| Bootstrap Std Sharpe | 0.3041 |
| 95% CI Lower | 0.0835 |
| 95% CI Upper | 1.2934 |
| PSR (normal approx.) vs 0 | 0.9830 |
| PSR (empirical) vs 0 | 0.9840 |

**Interpretation**: PSR = 98.3% means there is a 98.3%
probability that the observed Sharpe ratio of 0.645 represents a
genuine positive edge rather than random chance. The 95% bootstrap confidence
interval [0.083, 1.293] excludes 0, supporting a genuine edge.

---

## 2. Deflated Sharpe Ratio (DSR)

Adjusts the Sharpe ratio for the multiple-comparisons bias of testing
100 parameter configurations.

| Metric | Value |
|--------|-------|
| Observed Sharpe | 0.6445 |
| Number of configs tested | 100 |
| Sharpe SE (bootstrap) | 0.2992 |
| E[max of 100 iid normals] | 2.3663 |
| Deflated Sharpe Threshold | 0.7079 |
| DSR z-score | -0.2120 |
| DSR probability | 0.4160 |

**Interpretation**: After accounting for 100 configurations, the
deflated Sharpe ratio z-score is -0.212 (41.60%
probability of genuine edge). This does NOT meet the 90% confidence threshold — the edge is not statistically significant after multiple-testing correction.

---

## 3. Parameter Plateau Analysis (+/- 10% Perturbation)

## Parameter Plateau Analysis

Baseline: lookback=252, skip=21, top_fraction=0.5

| Perturbation | Lookback | Skip | Top Fraction | Train Sharpe | Val Sharpe | Test Sharpe |
|-------------|----------|------|--------------|-------------|-----------|------------|
| lookback_low | 226 | 21 | 0.50 | 0.2480 | 0.4940 | 0.7046 |
| lookback_high | 277 | 21 | 0.50 | 0.2932 | 0.6176 | 0.4400 |
| skip_low | 252 | 18 | 0.50 | 0.2994 | 0.5610 | 0.5865 |
| skip_high | 252 | 23 | 0.50 | 0.3027 | 0.4518 | 0.5955 |
| topfrac_low | 252 | 21 | 0.45 | 0.2347 | 0.5551 | 0.6445 |
| topfrac_high | 252 | 21 | 0.55 | 0.2833 | 0.5551 | 0.6445 |
| joint | 226 | 18 | 0.45 | 0.2293 | 0.4966 | 0.6426 |
| joint | 226 | 18 | 0.55 | 0.2605 | 0.4966 | 0.6426 |
| joint | 226 | 23 | 0.45 | 0.2266 | 0.4612 | 0.6049 |
| joint | 226 | 23 | 0.55 | 0.2430 | 0.4612 | 0.6049 |
| joint | 277 | 18 | 0.45 | 0.2668 | 0.4690 | 0.4390 |
| joint | 277 | 18 | 0.55 | 0.2841 | 0.4690 | 0.4390 |
| joint | 277 | 23 | 0.45 | 0.3036 | 0.5218 | 0.4111 |
| joint | 277 | 23 | 0.55 | 0.2897 | 0.5218 | 0.4111 |

---

## 4. Probability of Backtest Overfitting (PBO) / CSCV

Uses a logit-normal model (Bailey et al. 2017) to estimate the probability that
the best in-sample configuration has negative out-of-sample performance.

**IS = 1993-2017** (train + validation), **OOS = 2018-2026** (test)

| Metric | Value |
|--------|-------|
| Configurations tested | 560 |
| Mean IS Sharpe | 0.3245 |
| Mean OOS Sharpe | 0.4547 |
| Std IS Sharpe | 0.0736 |
| Std OOS Sharpe | 0.1258 |
| Rank Correlation (IS vs OOS) | -0.1411 |
| PBO (logit-normal estimate) | 0.0121 |
| PBO (best IS config OOS positive) | No |
| Overfitting ratio (IS-OOS gap / std) | -1.7696 |

**Best IS configuration**:
| Field | Value |
|-------|-------|
| IS Sharpe | 0.5546 |
| OOS Sharpe | 0.5209 |
| OOS below threshold (0) | False |

**Interpretation**: PBO = 0.0121. A PBO below 0.5 indicates the strategy does not suffer from significant backtest overfitting. The
IS-to-OOS rank correlation is -0.1411,
indicating weak/moderate consistency between
in-sample parameter selection and out-of-sample performance.

---

## 5. False Discovery Rate (FDR) Control

Applies the Benjamini-Hochberg procedure to control FDR at 0.05
across all 100 configurations from the robustness grid.

| Metric | Value |
|--------|-------|
| Configurations tested | 100 |
| Configurations with positive test Sharpe | 100 |
| Alpha (FDR threshold) | 0.05 |
| Sharpe SE (across configs) | 0.0077 |
| Mean p-value | 0.0000 |
| Min p-value | 0.0000 |

**BH Procedure**: Of 100 p-values computed from the test-period
Sharpe ratios (two-sided z-test), 100 survive
Benjamini-Hochberg correction at alpha = 0.05. This means
100 of 100 configurations show
statistically significant positive Sharpe even after controlling for multiple testing.

---

## Summary Table

| Test | Result | Threshold | Status |
|------|--------|-----------|--------|
| PSR vs 0 | 0.9830 | > 0.50 | PASS |
| DSR Probability | 0.4160 | > 0.90 | FAIL |
| PBO | 0.0121 | < 0.50 | PASS |
| FDR (significant configs) | 100 / 100 | > 0 | PASS |
| Plateau analysis | See above | Baseline stable | PASS |
| N configs for PBO | 560 | > 500 | PASS |

---

*Report generated: 2026-10-11*
*Code revision: 8950948*
