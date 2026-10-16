# Paper Trading Validation Report - Cycle 436
## UTC Timestamp
2026-10-16T01:04:01Z

## Gate State
Current UTC time: 2026-10-16T01:04:01Z
Post-close gate: 2026-10-18T20:00:00Z
Status: BELOW GATE - no fetch/replay performed

## Fetch/Replay Status
- Data acquisition from Yahoo Finance: NOT performed (gate not met)
- Replay: NOT performed (gate not met)

## State Snapshot
- Run history entries: 447
- Date range: 2025-01-02 → 2026-10-14 (from state)
- Last run date: 2026-10-14
- Regime flips: 6

## Verification Results
Rolling 63-day Sharpe (recomputed from last 63 cumulative returns):
- Computed Sharpe: 0.11333136870186278
- Stored Sharpe (drift_flags.low_rolling_sharpe.value): 0.11333136870186329
- Absolute difference: 5.134781488891349e-16
- Match status: ✓ Matches within float precision

Regime flip recomputation:
- Flips counted: 6
- Total run history entries: 447
- Last run date: 2026-10-14
- Match status: ✓ Consistent

## Supervisor Loop Tests
- Command: python3 .github/scripts/test_kilo_supervisor_loop.py -v
- Result: 10/10 tests passed (OK)
- Execution time: ~0.417s

## Notes
All verification checks pass. State remains unchanged as no data ingestion occurred due to gate condition.
