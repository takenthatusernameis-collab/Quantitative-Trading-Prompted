# Paper Trading Validation Report — Cycle 470

## Timestamp (UTC)
2026-10-16T02:09:00Z

## Gate Status
- Current UTC: 2026-10-16T02:09:00Z
- Gate: 2026-10-18T20:00:00Z
- Gate met: false

## Data/Fetch/Replay Status
- Fetch/replay performed: no (gate not met)
- Action taken: monitoring/verification and reporting only per task

## State Snapshot
- Run history entries: 447 (2025-01-02 → 2026-10-14)
- Last run date: 2026-10-14
- Regime: risk-on, 132 days
- Regime flips: 6
- Max drawdown: -2.93%
- Track record: 447 > 126 (pass)
- Sharpe (overall as stored): 1.93 > 0.9 (pass)
- Regime flips: 6 > 1 (pass)
- Drift flag low_rolling_sharpe: persists (3 consecutive trading days: 2026-10-12: 0.4892, 2026-10-13: 0.3669, 2026-10-14: 0.1133); below >20-day persistence threshold

## Independent Verification
- Rolling 63d Sharpe recomputation vs stored drift flag: diff = 5.134781488891349e-16 (within float precision); recomputed 0.11333136870186278 vs stored 0.11333136870186329
- Regime flips recomputation: flips = 6 of 447 run_history entries (matches); last_date 2026-10-14

## Supervisor Loop Tests
- Command: python3 .github/scripts/test_kilo_supervisor_loop.py -v
- Result: 10/10 tests passed

## Notes
- Gate remains unmet; no data acquisition/replay performed.
- Disposition recorded in .kilo-runtime/worker-disposition.json using current recommendation_id per schema_version 1.
