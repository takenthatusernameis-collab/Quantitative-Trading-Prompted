# Paper Trading Validation Report 380

## Timestamp (UTC)
2026-10-15T23:25:43Z

## Gate State
- Post-close gate: 2026-10-18T20:00:00Z UTC
- Current time: 2026-10-15T23:25:43Z UTC (gate not met)
- Fetch/replay: Not performed (gate unmet)

## State Snapshot
- run_history entries: 447
- regime flips: 6
- Stored drift flag: low_rolling_sharpe value 0.11333136870186329, threshold 0.5, date 2026-10-14
- last_run_date: 2026-10-14
- current_nav: 135043.35187742324, peak_nav: 139120.07235486925, max_drawdown: -0.0293036109631043
- positions: SPY 0.16152619822739042, QQQ 0.16152619822739042, IWM 0.16152619822739042, TLT 0.0, GLD 0.0, EFA 0.0, EEM 0.16152619822739042

## Verification
- Rolling 63d Sharpe recomputed from last 63 cumulative returns: 0.11333136870186278
- Stored value: 0.11333136870186329
- |computed - stored| = 5.134781488891349e-16 < 1e-12 ✓
- Regime flips recomputed from run_history: 6 (matches) ✓ Flip dates: 2025-03-10, 2025-03-24, 2025-03-26, 2025-05-12, 2026-03-19, 2026-04-08

## Supervisor Loop Tests
- python3 .github/scripts/test_kilo_supervisor_loop.py -v: 10/10 passed ✓

## Summary
Gate remains unmet. Per instructions, no fetch/replay performed. Minimal verifications passed. State unchanged (447 run_history entries, 6 regime flips, rolling 63d Sharpe matches stored drift flag).
