# Paper Trading Validation Report — Cycle 456

## Time
- UTC: 2026-10-16T01:44:40Z

## Gate State
- Current time: 2026-10-16T01:44:40Z
- Gate: 2026-10-18T20:00:00Z
- Status: < gate; do NOT fetch or replay.

## State Snapshot
- Run history: 447 entries (2025-01-02 → 2026-10-14)
- Regime flips: 6
- Last run date: 2026-10-14
- Regime: risk-on (132 days)
- Track record: 447 > 126 ✓
- Sharpe: 1.93 > 0.9 ✓
- Max DD: -2.93% < 15% ✓
- Drift flag (low_rolling_sharpe): persists (2026-10-12: 0.4892, 2026-10-13: 0.3669, 2026-10-14: 0.1133); not yet at >20-day persistence threshold

## Verification
- Rolling 63d Sharpe recomputation vs stored: diff 5.13e-16 (within float precision) ✓
- Regime flips recomputed: 6 (matches) ✓

## Supervisor Tests
- `python3 .github/scripts/test_kilo_supervisor_loop.py -v`: 10/10 passed ✓

## Outcome
No data fetch/replay performed as gate not met. Monitoring/verification/reporting only. Drift flag remains active as observed; no new data available yet.
