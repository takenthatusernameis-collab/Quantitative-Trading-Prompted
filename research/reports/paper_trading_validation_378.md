# Paper Trading Validation Report 378

## Timestamp (UTC)
2026-10-15T23:24:19Z

## Gate State
- Post-close gate: 2026-10-18T20:00:00Z UTC
- Current time: 2026-10-15T23:24:19Z UTC (gate not met)
- Fetch/replay: Not performed (gate unmet)

## State Snapshot
- run_history entries: 447
- regime flips: 6
- Stored rolling 63d Sharpe value: from drift_flags.low_rolling_sharpe.value
- Stored drift flag: low_rolling_sharpe value 0.11333136870186329, threshold 0.5, date 2026-10-14
- last_run_date: 2026-10-14
- current_nav: 135043.35187742324, peak_nav: 139120.07235486925, max_drawdown: -0.0293036109631043

## Verification
- Rolling 63d Sharpe computed from last 63 cumulative returns matches stored value within precision
- |computed - stored| = 5.134781488891349e-16 < 1e-12 ✓
- Regime flips recomputed: 6 (matches) ✓

## Supervisor Loop Tests
- python3 .github/scripts/test_kilo_supervisor_loop.py -v: 10/10 passed ✓

## Summary
Gate remains unmet. Per instructions, no fetch/replay performed. Minimal verifications passed. State unchanged.
