# Paper Trading Validation Report — Cycle 364

UTC: 2026-10-15T22:54:11Z
Gate: 2026-10-18T20:00:00Z UTC (not met)
Fetch/replay performed: No

## State snapshot
- run_history entries: 447
- regime flips (recomputed): 6

## Rolling 63d Sharpe (recomputed from last 63 cumulative returns)
- Computed: 0.11333136870186278
- Stored (drift_flags.low_rolling_sharpe.value): 0.11333136870186329
- Absolute diff: 5.134781488891349e-16 (< 1e-12)

## Supervisor loop tests
- python3 .github/scripts/test_kilo_supervisor_loop.py -v: 10/10 passed

## Result
Gate remains unmet; no data ingestion or replay performed. Verification complete.
