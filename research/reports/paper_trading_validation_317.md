# Paper Trading Validation Report — Cycle 317

- **Generated (UTC)**: 2026-10-15T21:46:05Z
- **Post-close gate**: 2026-10-18T20:00:00Z — **NOT MET** (2026-10-15T21:46:05Z < gate)
- **Fetch/replay performed**: **NO** (gate not met; protocol hold respected)

## State Snapshot
- Track record: **447 days** (2025-01-02 → 2026-10-14)
- NAV: $135,043.35 (+35.04%)
- Max drawdown: -2.93%
- Sharpe: 1.9272
- Rolling 63-day Sharpe: 0.1133
- Regime: risk-on (132 days)
- Regime flips: 6

## Independent Verification
1. **Rolling 63d Sharpe recompute**: recomputed from last 63 cumulative returns; diff vs stored drift-flag value = **5.13e-16** (< 1e-12 float precision). Match confirmed.
2. **Regime flips recompute**: recomputed from run_history; **6 flips** over **447 entries**. Match confirmed.
3. **Supervisor loop tests**: `python3 .github/scripts/test_kilo_supervisor_loop.py -v` — **10/10 passed**.

## Drift Flag
`low_rolling_sharpe` persists: 2026-10-12 (0.4892), 2026-10-13 (0.3669), 2026-10-14 (0.1133) — **3 consecutive trading days**. Trajectory over last 18 days volatile (range -0.51 to +1.19). Not yet at the >20-day persistence threshold.

## Supervisor Disposition
Recorded in `.kilo-runtime/worker-disposition.json` (schema_version 1, recommendation_id `38762216276-attempt-1-review-0005-6996e9659a28`, disposition `accepted`). Supervisor advice to continue gate monitoring only was consistent with the task contract and observed state.

## Next Cycle
Advance to Cycle 318. Re-evaluate UTC time against 2026-10-18T20:00:00Z; if still unmet, repeat verifications and reporting only.