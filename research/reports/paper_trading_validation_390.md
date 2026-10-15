# Paper Trading Validation Report - Cycle 390

## Timestamp
UTC: 2026-10-15T23:42:13Z

## Post-Close Gate
Gate: 2026-10-18T20:00:00Z UTC
Status: NOT MET (current < gate)
Action: No fetch or replay performed

## State Snapshot
- run_history entries: 447
- regime flips: 6
- cumulative_returns last 63: computed from stored state
- drift_flags.low_rolling_sharpe.value: stored in state
- rolling 63d Sharpe recomputed matches stored drift flag within float precision

## Verification Results
- Rolling 63d Sharpe diff: 5.13e-16 (matches stored drift flag)
- Regime flips recomputed: 6 of 447 (matches stored state)
- Supervisor loop tests: 10/10 passed (0.407s)

## Fetch/Replay Status
- Data acquisition: Not performed (gate not met)
- Replay: Not performed (gate not met)

## Conclusion
Post-close gate not met; monitoring/verification and reporting only as specified. All verifications pass. Supervisor loop tests pass.
