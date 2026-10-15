# Paper Trading Validation Report — Cycle 255

- **Session time (UTC)**: 2026-10-15T20:20:31Z
- **Post-close gate**: 2026-10-18T20:00:00Z — **NOT MET**
- **Fetch/replay performed**: NO (gate not met; protocol hold respected)
- **Supervisor disposition**: accepted (recommendation_id `38762216276-attempt-1-review-0005-6996e9659a28`)

## State snapshot (unchanged)

| Metric | Value |
|---|---|
| Track record length | 447 days (2025-01-02 → 2026-10-14) |
| Current NAV | $135,043.35 |
| Peak NAV | $139,120.07 |
| Max drawdown | -2.93% |
| Full-period Sharpe | 1.9272 |
| Rolling 63-day Sharpe | 0.11333136870186329 |
| Regime flips | 6 |
| Regime | risk-on (132 days) |

## Independent verification

1. **Rolling 63d Sharpe**: recomputed from last 63 cumulative returns = 0.11333136870186278; stored drift-flag value = 0.11333136870186329; **diff = 5.13e-16 < 1e-12** → match within float precision.
2. **Regime flips**: recomputed from run_history transitions = **6** over 447 entries; matches stored count.
3. **Supervisor loop tests**: `python3 .github/scripts/test_kilo_supervisor_loop.py -v` → **Ran 10 tests in 0.452s, OK** (10/10 passed).

## Drift flag

`low_rolling_sharpe` persists at 0.1133 on 2026-10-14 (3 consecutive trading days: 2026-10-12 0.4892, 2026-10-13 0.3669, 2026-10-14 0.1133). Trajectory over last 18 days volatile (range -0.51 to +1.19). Not yet at the >20-day persistence threshold. All primary go/no-go gates still pass (track record 447 > 126, Sharpe 1.93 > 0.9, max DD -2.93% < 15%, 6 regime flips > 1).

## Repository state

`git status --short` clean — no unstaged/staged diff, consistent with no fetch/replay having occurred this cycle.

## Next cycle

Advance to Cycle 256: repeat timestamp gate check, verifications, supervisor tests, reporting, and disposition. If gate is met (>= 2026-10-18T20:00:00Z), execute the established post-close fetch/replay protocol only if explicitly required and verifiably safe.
