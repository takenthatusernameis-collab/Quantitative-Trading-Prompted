# Paper Trading Validation Report - Cycle 438

## UTC Timestamp
2026-10-16T01:09:22Z

## Gate State
Current UTC time: 2026-10-16T01:09:22Z
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
- Execution time: ~0.411s

## Notes
All verification checks pass. State remains unchanged as no data ingestion occurred due to gate condition. Drift flag `low_rolling_sharpe` persists: 3 consecutive trading days (2026-10-12: 0.4892, 2026-10-13: 0.3669, 2026-10-14: 0.1133); not yet at the >20-day persistence threshold. All primary go/no-go gates still pass (track record 447 > 126, Sharpe 1.93 > 0.9, max DD -2.93% < 15%, 6 regime flips > 1). Regime unchanged (risk-on, 132 days).
