# Paper Trading Validation Report — Cycle 270

- **Generated (UTC)**: 2026-10-15T20:44:13Z
- **Post-close gate**: 2026-10-18T20:00:00Z UTC
- **Gate state**: NOT MET (session time < gate). No fetch or replay performed.

## Verification Results

| Check | Command / Method | Result |
|---|---|---|
| Rolling 63d Sharpe | Recompute from last 63 cumulative returns | calc 0.11333136870186278, stored 0.11333136870186329, diff 5.13e-16 (< 1e-12) |
| Regime flips | Recompute from run_history | 6 flips over 447 entries |
| Supervisor loop tests | `python3 .github/scripts/test_kilo_supervisor_loop.py -v` | 10/10 passed |
| Git status | `git status --short` | Clean (no unstaged/staged changes) |

## State Snapshot (unchanged)

- **Track record**: 447 days (2025-01-02 → 2026-10-14)
- **NAV**: $135,043.35 (+35.04%)
- **Peak NAV**: $139,120.07
- **Max drawdown**: -2.93%
- **Sharpe**: 1.9272
- **Rolling 63-day Sharpe**: 0.1133 (drift flag `low_rolling_sharpe`, active=False)
- **Regime**: risk-on (132 days)
- **Drift flag persistence**: 3 consecutive trading days (2026-10-12: 0.4892, 2026-10-13: 0.3669, 2026-10-14: 0.1133). Not yet at >20-day persistence threshold.

## Fetch / Replay Status

- **Fetch**: NOT ATTEMPTED (gate not met).
- **Replay**: NOT RUN (gate not met).
- State unchanged from Cycle 269.

## Supervisor Disposition

- Recorded in `.kilo-runtime/worker-disposition.json` (schema_version 1, recommendation_id `38762216276-attempt-1-review-0005-6996e9659a28`, disposition `accepted`).

## Next Task

Advance to Cycle 271: repeat gate check, verifications, and reporting per the same protocol.