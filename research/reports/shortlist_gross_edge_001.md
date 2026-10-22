# Cycle 941 Report — Shortlist gross edge re-verification

This report consolidates the gross/net decomposition and classification. See `research/experiments/shortlist_gross_edge_001.md` for full details.

## Summary table

| Candidate | Benchmark | Gross (cost=0) | Turnover (u/yr) | Cost drag | Net | Class |
|---|---|---|---|---|---|---|
| reversal_001 | 1/N of same nine ETFs | -6.921261% | 100.766 | 3.022991% | -9.944252% | no_gross_edge |
| pairs_001 | cash | 8.786166% | 68.692 | 2.136449% | -13.677386% | gross_edge_below_cost_hurdle |
| liquidity_001 | 1/N of same nine ETFs | -7.869716% | 24.000 | 0.720000% | -8.589716% | no_gross_edge |
| leadlag_001 | cash | 4.120849% | 25.512 | 0.765372% | 3.355477% | other |

- OVERALL: PASS (deterministic, read-only on data/config, no new candidate/variants opened)
