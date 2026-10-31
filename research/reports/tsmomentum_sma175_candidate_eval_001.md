# TSMomentum SMA-175 Candidate Eval (tsmomentum_sma175_candidate_eval, Cycle 918)

## Summary

- Candidate: `tsmomentum_sma175_candidate_eval`
- SMA window (candidate): 175
- Incumbent SMA window (run_cycle6): 200 (unchanged)
- Folds: 48
- Mean test Sharpe: 1.5400
- % Positive Sharpe: 95.8%
- Mean test max DD: -5.15%
- Total test trades: 5946

## Config

- symbols: ['SPY', 'QQQ', 'IWM', 'TLT', 'GLD', 'EFA', 'EEM']
- start: 1993-01-01
- end: 2026-10-09
- lookback: 226
- skip: 21
- top_fraction: 0.5
- vol_target: 0.1
- dd_threshold: 0.15
- vol_target_lookback: 63
- wf_train_years: 10.0
- wf_test_months: 12.0
- wf_step_months: 6.0
- wf_purge_days: 21
- wf_embargo_days: 21

## Costs

- commission_bps: 1.0
- slippage_bps: 2.0
- total_bps: 3.0000000000000004
- rf_annual: 0.02

Git rev: 3344d44
Date: 2026-10-31
