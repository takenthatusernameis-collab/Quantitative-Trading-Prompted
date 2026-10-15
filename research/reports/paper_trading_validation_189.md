# Paper Trading Validation Report — Cycle 189

- **Session time (UTC)**: 2026-10-15T18:29:13Z
- **Post-close gate**: 2026-10-18T20:00:00Z UTC — **NOT MET** (session < gate)
- **Fetch/replay performed**: NONE (gate not met; protocol forbids fetch/replay before gate)

## State Snapshot

| Metric | Value |
|---|---|
| Track record length | 447 days (2025-01-02 → 2026-10-14) |
| Last run date | 2026-10-14 |
| Current NAV | $135,043.35 |
| Peak NAV | $137,376.42 |
| Max drawdown | -2.93% |
| Rolling 63d Sharpe | 0.11333 |
| Regime flips | 6 |
| Drift flag `low_rolling_sharpe` | **not active** (value 0.11333 < 0.5 threshold, but persistence threshold not met) |

## Verification

1. **Rolling 63d Sharpe recomputation**: recomputed from last 63 cumulative returns.
   - Calculated: 0.11333136870186278
   - Stored: 0.11333136870186329
   - **Diff: 5.13e-16** — matches within float precision.

2. **Regime flips recomputation**: counted transitions in `run_history` (447 entries).
   - **Observed: 6** — matches expected.

3. **Supervisor loop tests**: `python3 .github/scripts/test_kilo_supervisor_loop.py -v`
   - **Result: 10/10 passed** (Ran 10 tests in 0.530s, OK).

## Blocker

Post-close gate (2026-10-18T20:00:00Z) not yet reached. No fetch/replay possible until gate met. Strategy frozen pending gate.

## Next Task

Continue gate monitoring — Cycle 190 (see `NEXT_AGENT_TASK.md`).