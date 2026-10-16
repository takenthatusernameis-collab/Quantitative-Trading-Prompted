# Paper Trading Validation Report — Cycle 457

## UTC Time
2026-10-16T01:46:40Z

## Gate State
Post-close gate: 2026-10-18T20:00:00Z. Session time 2026-10-16T01:46:40Z < gate. **Gate NOT met.** No fetch or replay performed per protocol.

## State Snapshot
- Track record: 447 days (2025-01-02 → 2026-10-14)
- NAV: $135,043.35 (+35.04%)
- Sharpe: 1.9272
- Max drawdown: -2.93%
- Rolling 63-day Sharpe: 0.11333136870186329
- Regime: risk-on (132 days), 6 regime flips
- Drift flag: `low_rolling_sharpe` persists 3 consecutive trading days (2026-10-12: 0.4892, 2026-10-13: 0.3669, 2026-10-14: 0.1133)

## Verification

### Rolling 63d Sharpe Recomputation
- Recomputed from last 63 cumulative returns: 0.11333136870186278
- Stored drift flag value: 0.11333136870186329
- Difference: 5.13e-16 (within float precision)

### Regime Flips Recomputation
- Recomputed from run_history: 6 flips over 447 records

### Supervisor Loop Tests
```
Ran 10 tests in 0.408s
OK
```
All 10 tests passed.

## Action
No fetch or replay performed (gate not met). Strategy frozen. Next cycle: re-evaluate after post-close gate at 2026-10-18T20:00:00Z.