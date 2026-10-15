2026-10-15T22:57:36Z

# Paper Trading Validation Report - Cycle 365

## Timestamp
2026-10-15T22:57:01Z

## Gate State
Post-close gate: 2026-10-18T20:00:00Z UTC (NOT MET)
Current time: 2026-10-15T22:57:01Z UTC
Gate status: LOCKED - No fetch/replay performed

## Fetch/Replay Status
- fetch_performed: false
- replay_performed: false
- reason: gate not met

## State Snapshot
- run_history_entries: 447
- regime_flips: 6
- regime_exposure: risk-on (132 days)
- drift_flags.low_rolling_sharpe.value: 0.11333136870186329
- drift_flags.low_rolling_sharpe.triggered: true (3 consecutive days as of prior cycles)
- nav: 135043.35
- total_return_pct: 35.04%
- max_drawdown_pct: -2.93%
- sharpe: 1.9272
- last_date: 2026-10-14

## Rolling Sharpe Verification (last 63 cumulative returns)
- recomputed: 0.11333136870186278
- stored: 0.11333136870186329
- diff: 5.134781488891349e-16 (< 1e-12) ✓

## Regime Flips Verification
- recomputed: 6
- expected: 6 ✓
- run_history_len: 447 ✓

## Supervisor Loop Tests
- python3 .github/scripts/test_kilo_supervisor_loop.py -v: OK (10/10 passed)

## Conclusion
All verifications pass. Gate remains unmet; no data ingestion, backtests, strategy changes, or dependency modifications performed. Task remains bounded to monitoring/verification.
