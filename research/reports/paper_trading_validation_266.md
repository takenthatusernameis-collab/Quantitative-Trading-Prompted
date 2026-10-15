# Paper Trading Validation Report — Cycle 266

- **UTC time**: 2026-10-15T20:35:03Z
- **Post-close gate**: 2026-10-18T20:00:00Z — **NOT MET**
- **Action**: No fetch, no replay. Gate-mandated hold respected.

## State snapshot (unchanged)
- Track record: 447 days (2025-01-02 → 2026-10-14)
- NAV: $135,043.35 (+35.04%)
- Max drawdown: -2.93%
- Sharpe: 1.9272
- Rolling 63-day Sharpe: 0.1133
- Regime flips: 6 (risk-on, 132 days)

## Independent verification
| Check | Result |
|---|---|
| Rolling 63d Sharpe recomputed vs stored | 0.11333136870186278 vs 0.11333136870186329, diff 5.13e-16 < 1e-12 |
| Regime flips recomputed | 6 over 447 run_history entries |
| Supervisor loop tests | 10/10 passed (0.447s) |

## Drift flag
`low_rolling_sharpe` persists on 2026-10-12 (0.4892), 2026-10-13 (0.3669), 2026-10-14 (0.1133) — 3 consecutive days. Not at >20-day persistence threshold.

## Artifacts
- `data/processed/paper_trading_state.yaml`
- `research/reports/paper_trading_rolling.md`
- `research/reports/paper_trading_validation_266.md` (this file)

## Next cycle
Continue gate monitoring. Re-attempt fetch after 2026-10-18T20:00:00Z.