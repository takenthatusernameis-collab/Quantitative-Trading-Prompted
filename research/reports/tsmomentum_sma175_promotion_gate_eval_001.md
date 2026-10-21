# TSMomentum SMA-175 Promotion Gate Eval (tsmomentum_sma175_candidate, Cycle 920)

## Summary

- Candidate: `tsmomentum_sma175_candidate` (SMA window 175)
- Incumbent SMA window (run_cycle6): 200 (unchanged)
- Git rev: 5932ce0
- Date: 2026-10-21
- Sharpe convention: `arithmetic_annualized_rf0`
- PSR target: 1.4178 (config/promotion_gates.yaml gate 'psr' (backtest Sharpe baseline 1.4178); src.simulation.evaluation.GoNoGoConfig.backtest_sharpe)
- PSR bootstrap: n=1000, block_size=22, seed=20240101

## Full gate table

| Gate | Metric | Value | Threshold | Comparison | Result | Source |
|------|--------|-------|-----------|------------|--------|--------|
| track_record_length | paper_days | 8488.000000 | 126.000000 | gte | PASS | research/reports/paper_trading_validation_002.md |
| full_period_sharpe | paper_sharpe | 1.607869 | 0.900000 | gte | PASS | research/reports/paper_trading_validation_002.md |
| rolling_63d_sharpe | rolling_sharpe_63d | -0.448918 | 0.900000 | gte | FAIL | research/reports/paper_trading_validation_002.md |
| max_drawdown | paper_max_dd | -0.094633 | -0.150000 | gte | PASS | research/reports/paper_trading_validation_002.md |
| rolling_63d_max_dd | rolling_max_dd_63d | -0.038564 | -0.150000 | gte | PASS | research/reports/paper_trading_validation_002.md |
| regime_flips | regime_flips | 277.000000 | 1.000000 | gte | PASS | research/reports/paper_trading_validation_002.md |
| psr | psr_normal | 0.896592 | 0.950000 | gte | FAIL | research/reports/go_no_go_evaluation_002.md |

- PSR zone: grey_zone
- Sharpe standard error: 0.150565
- Sharpe on backtest-baseline scale (diagnostic): 1.447467
- Failed gates: rolling_63d_sharpe, psr

## Decision mapping

- Decision: **NO-GO**
- Candidate promotable (every promotion gate passes): NO
- Rationale: 2 promotion gate(s) failed: rolling_63d_sharpe, psr. A failing gate can never yield GO, regardless of the PSR.
- Conditions for re-evaluation: Strategy fails go/no-go criteria. Do not promote to live trading without major revision.

## Structural checks

- [git_status_data_config_clean]: PASS (observed= expected=)
- [git_diff_run_cycle6_empty]: PASS (observed= expected=)
- [sharpe_convention_matches_implementation]: PASS (observed=arithmetic_annualized_rf0 expected=arithmetic_annualized_rf0)
- [psr_target_is_documented_backtest_baseline]: PASS (observed=1.4178 expected=src.evaluation.statistics.compute_psr (seeded moving-block bootstrap, seed 20240101) of the paper return series against the backtest Sharpe baseline 1.4178. The observed Sharpe (numerator) and the bootstrap distribution (standard error) use the same estimator, the canonical convention (see sharpe_convention); the target 1.4178 is an external reference on the backtest-baseline scale (see sharpe_convention.backtest_baseline_scale).)

STRUCTURAL: PASS

OVERALL is the verdict on this tool's own internal checks: it is PASS
only when every internal check above passes. It is *not* the
candidate's promotion verdict: that is the Decision above
(GO / NO-GO / INCONCLUSIVE), which is reported independently.

OVERALL: PASS
