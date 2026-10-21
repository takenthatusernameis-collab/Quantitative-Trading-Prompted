# Experiment: `pairs_001` failure analysis (pairs_001_failure_analysis)

**Cycle 937.** Read-only deterministic analysis of why `pairs_001` failed, using only the frozen hypothesis/config and committed evaluation artifacts. No re-tuning, no changes under `data/` or `config/`, no modifications to frozen artifacts.

## Inputs (read-only)
- Hypothesis: `research/hypotheses/pairs_001.md`
- Config: `config/pairs_candidate_001.yaml`
- Experiment: `research/experiments/pairs_001_evaluation.md`
- Report: `research/reports/pairs_001_evaluation.md`

## Per-pair attribution (out of sample)
| Pair | Net excess annualized | Sharpe | Trades |
|---|---|---|---|
| XLP/XLU | 0.009094 | 0.179750 | 226 |
| XLF/XLK | -0.026539 | -0.314578 | 205 |
| XLE/XLB | -0.032287 | -0.408004 | 211 |
| XLI/XLB | -0.019626 | -0.451870 | 228 |
| XLV/XLY | -0.028693 | -0.439405 | 201 |
| XLK/XLU | -0.038723 | -0.452537 | 194 |

## Cointegration failure summary (training windows only)
| Pair | Train windows | Cointegrated | Min p-value | Max p-value |
|---|---|---|---|---|
| XLP/XLU | 36 | 14 | 0.001032 | 0.990904 |
| XLF/XLK | 36 | 4 | 0.000193 | 1.000000 |
| XLE/XLB | 36 | 1 | 0.022739 | 0.992559 |
| XLI/XLB | 36 | 7 | 0.002240 | 0.871773 |
| XLV/XLY | 36 | 11 | 0.000992 | 0.555322 |
| XLK/XLU | 36 | 10 | 0.001517 | 0.813088 |

## Cost breakdown (turnover drag vs borrow drag)
| Item | Value |
|---|---|
| Realized turnover (per year) | 68.6916 units/yr |
| Realized turnover cost drag | 2.136400%/yr |
| Realized borrow drag (25 bp x short notional per rebalance) | 20.3271%/yr |
| Realized total cost drag | 22.4636%/yr |
| Gross excess (before any cost) annualized | 8.7862% |
| Excess net of the turnover cost, before borrow, annualized | 6.6497% |
| Net excess after borrow annualized | -13.6774% |

## Pre-registered conditions fired
| # | Observed | Requirement | Outcome |
|---|---|---|---|
| i | -0.829067 | >= 0.9 | **FIRED** |
| ii | [-1.219160, -0.467513] | excludes zero | **not fired** |
| iii | any pair failed | no pair fails | **FIRED** |
| iv | -0.136774 | > 0 | **FIRED** |

## Failure mechanism hypothesis (evidence-based, no speculation beyond measured)
- **Structural instability**: cointegration fails in most training windows for nearly all pairs (only 1/36 for XLE/XLB, 4/36 for XLF/XLK) — the mean-reverting spread assumption is not stable out of sample in this regime set.
- **Cost sensitivity**: the gross excess before any cost is modest (+8.79%/yr); the measured turnover drag is 2.14%/yr and the pre-registered borrow drag is 20.33%/yr, leaving net -13.68%/yr; the strategy is not robust to the assumed short-borrow cost.
- **Broad underperformance**: all pairs except XLP/XLU have negative net excess/Sharpe; performance is consistently negative across folds with positive-fold rate 0.25 and mean OOS Sharpe -0.829.
- **Conclusion**: rejection is driven by a combination of unstable cointegration (condition iii) and insufficient gross edge to survive pre-registered borrow costs (condition iv), producing mean OOS Sharpe below threshold (condition i).

## Integrity
- data/ unchanged: True
- config/ unchanged: True

