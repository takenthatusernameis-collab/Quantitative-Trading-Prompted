# Paper Trading Validation Report — Cycle 441

## UTC Time
2026-10-16T01:12:37Z

## Gate State
Gate: 2026-10-18T20:00:00Z — **NOT MET** (current time < gate).
Per task constraints: no fetch/replay performed.

## State Snapshot (from data/processed/paper_trading_state.yaml)
- last_run_date: 2026-10-14
- run_history length: 447 (2025-01-02 → 2026-10-14)
- peak_nav: 139120.07235486925
- current_nav: 135043.35187742324
- max_drawdown: -0.0293036109631043 (-2.93%)
- regime flips: 6
- regime unchanged (risk-on, 132 days)

## Drift Flag
- low_rolling_sharpe: value 0.11333136870186329, threshold 0.5, date 2026-10-14
- Persistence: 3 consecutive trading days (2026-10-12: 0.4892, 2026-10-13: 0.3669, 2026-10-14: 0.1133)
- Not yet at >20-day persistence threshold

## Verification Results

### Rolling 63d Sharpe Recomputation
- Recomputed from last 63 cumulative returns: 0.11333136870186278
- Stored drift flag value: 0.11333136870186329
- Difference: 5.134781488891349e-16 (within float precision) ✓

### Regime Flips Recomputation
- Recomputed from run_history: 6 flips over 447 entries ✓

### Supervisor Loop Tests
- Command: `python3 .github/scripts/test_kilo_supervisor_loop.py -v`
- Result: Ran 10 tests in 0.410s — OK (10/10) ✓

## Primary Go/No-Go Gates
| Gate | Value | Threshold | Status |
|------|-------|-----------|--------|
| Track record length | 447 | > 126 | PASS |
| Sharpe | 1.93 | > 0.9 | PASS |
| Max drawdown | -2.93% | < 15% | PASS |
| Regime flips | 6 | > 1 | PASS |

## Fetch/Replay Status
Not performed — post-close gate (2026-10-18T20:00:00Z) not yet reached.

## Supervisor Disposition
- recommendation_id: 38817660960-attempt-1-review-0003-2ac0cb7d6609
- disposition: verified
- Written to .kilo-runtime/worker-disposition.json

## Next Task
Post-gate data acquisition check — Cycle 442, same gate (2026-10-18T20:00:00Z).