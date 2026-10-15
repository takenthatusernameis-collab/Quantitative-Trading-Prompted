# Paper Trading Validation Report - Cycle 359

Generated: 2026-10-15T22:49:00Z (UTC)

## Gate Status
- Post-close gate: 2026-10-18T20:00:00Z UTC
- Current UTC: 2026-10-15T22:48:50Z
- Gate met: No

## Fetch/Replay Status
- fetch/replay performed: No (gate not met)

## State Snapshot
- run_history entries: 447
- regime flips: 6
- Stored rolling 63d Sharpe drift flag value: 0.11333136870186329
- Stored drift flag date: 2026-10-14
- last_run_date: 2026-10-14
- current_nav: 135043.35187742324
- max_drawdown: -0.0293036109631043

## Verification
- Rolling 63d Sharpe diff (recomputed vs stored): 5.134781488891349e-16 (within 1e-12 ✓)
- Regime flips recomputed: 6 ✓
- Recomputed rolling 63d Sharpe: 0.11333136870186278

## Supervisor Loop Tests
- `python3 .github/scripts/test_kilo_supervisor_loop.py -v`: 10/10 passed ✓

## Supervisor Disposition
- Disposition: verified
