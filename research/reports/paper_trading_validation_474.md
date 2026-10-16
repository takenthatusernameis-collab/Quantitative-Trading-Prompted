# Paper Trading Validation - Cycle 474

**Generated:** 2026-10-16T02:13:58Z (UTC)

## Gate State
- Current time (UTC): 2026-10-16T02:13:58Z
- Post-close gate: 2026-10-18T20:00:00Z
- Gate met: **false** (< gate)
- Action: No fetch/replay performed. Monitoring/verification and reporting only.

## State Snapshot
- run_history entries: 447 (2025-01-02 → 2026-10-14)
- Last run date: 2026-10-14
- Regime flips: 6
- Regime exposure (current): risk-on (132 days)
- Track record > 126: true (447)
- Sharpe (stored): 1.93 > 0.9: true (from state)
- Max drawdown: -2.93% < 15%: true (from state)
- Regime flips > 1: true (6)
- Drift flag (low_rolling_sharpe): persists (last 3 trading days: 2026-10-12: 0.4892, 2026-10-13: 0.3669, 2026-10-14: 0.1133). Not yet at >20-day persistence threshold.

## Verification (independent)
- Rolling 63d Sharpe (recomputed from last 63 cumulative returns): 0.113331
- Stored drift flag low_rolling_sharpe value: 0.113331
- Diff: 5.135e-16 (matches within float precision) ✓
- Regime flips recomputed from run_history: 6/447 ✓

## Supervisor Loop Tests
```bash
python3 .github/scripts/test_kilo_supervisor_loop.py -v
```
Result: 10/10 passed (OK) ✓

## Fetch/Replay
- Yahoo Finance fetch: not attempted (gate not met)
- Replay: not attempted (gate not met)

## Conclusion
All verifications pass. Gate remains unmet. No data acquisition/replay performed. State remains consistent.
