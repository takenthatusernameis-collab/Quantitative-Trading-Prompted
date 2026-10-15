# Paper Trading Validation Report — Cycle 370

- **Session time (UTC)**: 2026-10-15T23:09:29Z
- **Post-close gate**: 2026-10-18T20:00:00Z — **NOT MET**
- **Fetch/replay status**: None performed (gate-mandated hold)
- **Worker disposition**: `.kilo-runtime/worker-disposition.json` — accepted (recommendation 38762216276-attempt-1-review-0005-6996e9659a28)

## State snapshot (unchanged)
- Track record: **447 days** (2025-01-02 → 2026-10-14)
- NAV: **$135,043.35** (+35.04%)
- Max drawdown: **-2.93%**
- Sharpe: **1.9272**
- Rolling 63-day Sharpe: **0.11333136870186329**
- Regime flips: **6**
- Regime: risk-on (132 days)

## Verification results
| Check | Result |
|---|---|
| Rolling 63d Sharpe recomputed | 0.11333136870186278 vs stored 0.11333136870186329 — diff **5.134781488891349e-16** (< 1e-12) — **PASS** |
| Regime flips recomputed | **6** over 447 run_history entries — **PASS** |
| Supervisor loop tests | **10/10 PASS** |

## Drift flag
`low_rolling_sharpe` persists on 2026-10-12 (0.4892), 2026-10-13 (0.3669), 2026-10-14 (0.1133) — **3 consecutive trading days**. Trajectory over last 18 days volatile (range -0.51 to +1.19). Not yet at the >20-day persistence threshold. All primary go/no-go gates still pass (track record 447 > 126, Sharpe 1.93 > 0.9, max DD -2.93% < 15%, 6 regime flips > 1).

## Next cycle
Advance to Cycle 371: repeat timestamp-gate check, verifications, supervisor tests, and report; only proceed to fetch/replay if session time >= 2026-10-18T20:00:00Z.