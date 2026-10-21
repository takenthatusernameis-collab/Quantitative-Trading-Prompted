# TSMomentum SMA-175 Promotion Gate Eval (tsmomentum_sma175_candidate, Cycle 920)

## Summary

- Candidate: `tsmomentum_sma175_candidate` (SMA window 175)
- Incumbent SMA window (run_cycle6): 200 (unchanged)
- Git rev: c3a22b6
- Date: 2026-10-21

## Full gate table

| Gate | Metric | Value | Threshold | Comparison | Result | Source |
|------|--------|-------|-----------|------------|--------|--------|
| track_record_length | paper_days | 8488.000000 | 126.000000 | gte | PASS | research/reports/paper_trading_validation_002.md |
| full_period_sharpe | paper_sharpe | 1.607869 | 0.900000 | gte | PASS | research/reports/paper_trading_validation_002.md |
| rolling_63d_sharpe | rolling_sharpe_63d | -0.448918 | 0.900000 | gte | FAIL | research/reports/paper_trading_validation_002.md |
| max_drawdown | paper_max_dd | -0.094633 | -0.150000 | gte | PASS | research/reports/paper_trading_validation_002.md |
| rolling_63d_max_dd | rolling_max_dd_63d | -0.038564 | -0.150000 | gte | PASS | research/reports/paper_trading_validation_002.md |
| regime_flips | regime_flips | 277.000000 | 1.000000 | gte | PASS | research/reports/paper_trading_validation_002.md |
| psr | psr_normal | 0.856637 | 0.950000 | gte | FAIL | research/reports/go_no_go_evaluation_002.md |

- PSR zone: grey_zone
- Failed gates: rolling_63d_sharpe, psr

## Decision mapping

- Decision: **NO-GO**
- Rationale: 2 promotion gate(s) failed: rolling_63d_sharpe, psr. A failing gate can never yield GO, regardless of the PSR.
- Conditions for re-evaluation: Strategy fails go/no-go criteria. Do not promote to live trading without major revision.

## Structural checks

- [git_status_data_config_clean]: PASS (observed= expected=)
- [git_diff_run_cycle6_empty]: PASS (observed= expected=)

OVERALL: PASS
