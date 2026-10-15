# Paper Trading Validation Report - Cycle 383

## Timestamp
UTC: 2026-10-15T23:30:44Z

## Gate State
Post-close gate: 2026-10-18T20:00:00Z UTC
Gate met: false (< gate time)
Action: No fetch/replay performed.

## Fetch/Replay Status
- fetch: not performed (gate not met)
- replay: not performed (gate not met)

## State Snapshot
- run_history entries: 447
- regime flips: 6
- last_run_date: 2026-10-14
- current_nav: 135043.35187742324
- peak_nav: 139120.07235486925
- max_drawdown: -0.0293036109631043
- low_rolling_sharpe stored: 0.11333136870186329
- low_rolling_sharpe threshold: 0.5

## Verification (independent recomputation)
- Rolling 63d Sharpe (from last 63 cumulative returns):
  - recomputed: 0.11333136870186278
  - stored: 0.11333136870186329
  - diff: 5.134781e-16 (< 1e-12) ✓
- Regime flips (transitions in regime_exposure across run_history):
  - computed: 6
  - expected (stored state): 6 ✓

## Supervisor Loop Tests
- Command: `python3 .github/scripts/test_kilo_supervisor_loop.py -v`
- Result: OK (10/10 passed)

## Conclusion
Gate not met; monitoring/verification only. All validations passed.
