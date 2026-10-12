# Go/No-Go Evaluation Report

**Candidate:** tsmomentum_spytrend_001
**Evaluation Date:** 2026-10-12
**Paper Track Record Length:** 5 days
**Config Hash:** {'min_days': 63, 'target_sharpe': 0.9, 'max_dd_threshold': 0.15, 'psr_go_threshold': 0.95, 'psr_no_go_threshold': 0.5, 'bootstrap_samples': 1000, 'block_size': 22, 'backtest_sharpe': 1.4178, 'backtest_max_dd': -0.0779, 'backtest_trades': 1196, 'backtest_annualized_turnover': 13.32, 'backtest_annualized_return': 0.1446, 'backtest_volatility': 0.0879, 'backtest_sortino': 1.7477, 'backtest_profit_factor': 1.35}

---

## Decision: ⏳ INCONCLUSIVE

**Rationale:**
Insufficient track record: 5 days < 63 minimum required.

**Conditions for Re-evaluation:**
Re-evaluate after 58 more trading days of paper track record.

---

## Backtest Baseline (Cycle 5/6 Verified)

| Metric | Value |
|--------|-------|
| Test Sharpe | 1.4178 |
| Sortino | 1.7477 |
| Annualized Return | 14.46% |
| Annualized Volatility | 8.79% |
| Max Drawdown | -7.79% |
| Total Return | -7.79% |
| Trades | 1196 |
| Annualized Turnover | 13.32 |
| Profit Factor | 1.35 |

*Source: simulation_verification_001.md (Cycle 7 verification)*

---

## Paper Performance (5 days)

| Metric | Paper | Backtest | Difference |
|--------|-------|----------|------------|
| Sharpe Ratio | 0.0000 | 1.4178 | -1.4178 |
| Sortino | 0.0000 | 1.7477 | -1.7477 |
| Annualized Return | 186.32% | 14.46% | +171.86% |
| Annualized Volatility | 0.00% | 8.79% | -8.79% |
| Max Drawdown | 0.00% | -7.79% | +7.79% |
| Total Return | 2.11% | -7.79% | N/A |
| Trade Count (approx) | 5 | 1196 | N/A |
| Annualized Turnover | 84.80 | 13.32 | +71.48 |
| Profit Factor | inf | 1.35 | +inf |

---

## Statistical Comparison

| Metric | Value |
|--------|-------|
| Probabilistic Sharpe Ratio (normal) | 0.0000 |
| Probabilistic Sharpe Ratio (empirical) | 0.0000 |
| Sharpe Standard Error | 0.0000 |
| 95% CI Lower | 0.0000 |
| 95% CI Upper | 0.0000 |
| Target PSR (GO) | > 0.95 |
| Target PSR (NO-GO) | < 0.5 |

**Interpretation:** PSR measures the probability that the true Sharpe ratio exceeds the backtest Sharpe (1.4178).
- PSR > 0.95: Strong evidence paper performance matches backtest
- PSR < 0.5: Strong evidence paper performance is worse than backtest
- Otherwise: Inconclusive, need more data

---

## Drift Assessment

### Regime Stability
- **Current Regime Exposure:** Full (1.0)
- **Days in Current Regime:** 5
- **Regime Stable (≥5 days):** Yes

### Risk Parameter Bounds
| Parameter | Min | Max | Alert Threshold | Status |
|-----------|-----|-----|-----------------|--------|
| vol_scale | 0.648 | 0.648 | > 2.0 | ✅ OK |
| dd_scale | 1.000 | 1.000 | < 0.25 | ✅ OK |

### Turnover Distribution
| Statistic | Value | Backtest Avg | Status |
|-----------|-------|--------------|--------|
| Median Daily Turnover | 33.65% | ~0.012 (est.) | ✅ OK |
| 95th Percentile Turnover | 33.65% | ~0.05 (est.) | ✅ OK |

### Drift Flags
- **Active Drift Flags:** 0
- **Details:** See paper_trading_rolling.md for current flags

---

## Go/No-Go Criteria Summary

| Criterion | Threshold | Actual | Status |
|-----------|-----------|--------|--------|
| Minimum Track Record | ≥ 63 days | 5 days | ❌ FAIL |
| Probabilistic Sharpe Ratio | > 0.95 | 0.000 | ❌ FAIL |
| Max Drawdown | ≤ 15% | 0.00% | ✅ PASS |
| Regime Stability | Stable | Stable | ✅ PASS |
| Risk Parameters | In Bounds | vol_scale∈[0.65,0.65], dd_scale∈[1.00,1.00] | ✅ PASS |

---

*Report generated: 2026-10-12 04:21:16 UTC*
*Code revision: c92f30a*
