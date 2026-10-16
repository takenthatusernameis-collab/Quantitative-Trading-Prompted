# Paper Trading Validation Report — Cycle 413

## UTC Time
2026-10-16T00:29:18Z

## Gate State
Post-close gate: 2026-10-18T20:00:00Z. Current time < gate. **No fetch or replay performed.**

## State Snapshot
- Track record: 447 days (2025-01-02 → 2026-10-14)
- NAV: $135,043.35 (+35.04%)
- Max drawdown: -2.93%
- Sharpe: 1.9272
- Rolling 63-day Sharpe: 0.11333136870186329
- Regime flips: 6
- Regime: risk-on (132 days)
- Drift flag: `low_rolling_sharpe` persists on 2026-10-12 (0.4892), 2026-10-13 (0.3669), 2026-10-14 (0.1133) — 3 consecutive days

## Verification
- Rolling 63d Sharpe recomputed from last 63 cumulative returns: 0.11333136870186278
- Stored drift flag value: 0.11333136870186329
- Diff: 5.13e-16 (within float precision — MATCH)
- Regime flips recomputed from run_history: 6 of 447 entries — MATCH

## Supervisor Loop Tests
`python3 .github/scripts/test_kilo_supervisor_loop.py -v` — **10/10 PASSED**

## Supervisor Disposition
Recorded in `.kilo-runtime/worker-disposition.json` (schema_version 1, recommendation_id `38817660960-attempt-1-review-0003-2ac0cb7d6609`, disposition `in_progress`).

## Next Task
Post-gate data acquisition check (Cycle 414) with same gate 2026-10-18T20:00:00Z.