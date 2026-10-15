# Paper Trading Validation Report — Cycle 255
## Session Time (UTC)
2026-10-15T20:21:09Z

## Post-Close Gate State
Gate threshold: 2026-10-18T20:00:00Z UTC
Session time: 2026-10-15T20:21:09Z UTC
Gate met: false
Fetch attempted: no
Replay attempted: no
Fetch/replay status: no real trading data fetched/replayed (gate not met)

## State Snapshot
Last run date: 2026-10-14
Track record entries (run_history): 447
Current NAV: 135043.35187742324
Peak NAV: 139120.07235486925
Max drawdown: -0.0293036109631043
Regime flips (computed): 6

## Drift Flags
low_rolling_sharpe.value: 0.11333136870186329
low_rolling_sharpe.active/triggered: false
low_rolling_sharpe consecutive days: 3 (from prior cycles; not incremented in this validation cycle)

## Independent Verification
Rolling 63d Sharpe (recomputed from last 63 cumulative_returns):
- calc = 0.11333136870186278
- stored = 0.11333136870186329
- |diff| = 5.134781488891349e-16 (within float precision < 1e-12)

Regime flips recomputed from run_history transitions: 6 (matches expected)

## Supervisor Loop Tests
python3 .github/scripts/test_kilo_supervisor_loop.py -v: 10/10 OK (ran 0.422s)

## Conclusion
Gate not met; state unchanged. Verifications passed. Supervisor loop tests pass 10/10. Report written.
