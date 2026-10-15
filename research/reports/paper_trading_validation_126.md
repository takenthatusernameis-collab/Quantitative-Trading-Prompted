# Paper Trading Validation - Cycle 126

**Session (UTC):** 2026-10-15T14:26:12Z
**Gate (UTC):** 2026-10-17T20:00:00Z
**Gate met:** false

## Timestamp gate
- session_time < gate → no fetch/replay performed.

## Track record (unchanged)
- run_history: 447 days (2025-01-02 → 2026-10-14)
- NAV: $135,043.35 (+35.04%)
- Sharpe: 1.9272
- Max drawdown: -2.93%
- Rolling 63d Sharpe: 0.11333136870186278 (matches drift_flags value)
- Drift: low_rolling_sharpe persists (3 consecutive days, not >20d threshold)
- Regime flips: 6 (from stored history)

## Independent verifications
- Rolling-63d Sharpe computed from cumulative_returns[-63:]: matches drift_flags.low_rolling_sharpe.value (diff 5.13e-16 < 1e-10)
- Regime flip count from run_history.regime_exposure: 6

## Supervisor loop tests
- python3 .github/scripts/test_kilo_supervisor_loop.py -v: 10/10 passed

## Decision
- Gate not met. No new data/replay. Task unchanged for next cycle.
