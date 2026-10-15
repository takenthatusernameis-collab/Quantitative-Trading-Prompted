# Paper Trading Validation Report - Cycle 143

**Cycle:** 143
**UTC Session Time:** 2026-10-15T15:22:41Z
**Gate Time:** 2026-10-17T20:00:00Z
**Gate Status:** NOT MET (2026-10-15T15:22:41Z < 2026-10-17T20:00:00Z)
**Generated:** 2026-10-15T15:22:41Z

## Summary

The post-close gate (2026-10-17T20:00:00Z) was not met at session time 2026-10-15T15:22:41Z. No fetch or replay was performed. All independent verifications completed successfully.

## Timing
- Session UTC: 2026-10-15T15:22:41Z
- Post-close gate: 2026-10-17T20:00:00Z
- Time until gate: ~50 hours (gate not met)

## Fetch Results
- Fetch attempted: No (gate not met)
- New real trading day beyond 2026-10-14: N/A

## Track Record (current state, unchanged)
- Track record days: 447 (2025-01-02 → 2026-10-14)
- NAV: $135,043.35
- Sharpe: 1.9272
- Max Drawdown: -2.93%
- Rolling 63d Sharpe: 0.11333136870186278
- Drift flag: persists (3 consecutive days, not yet >20d threshold)
- Regime: risk-on (132 days)
- Regime flips: 6

## Independent Verifications

### Rolling-63-day Sharpe verification
- Computed from last 63 cumulative_returns: 0.11333136870186278
- Stored value (drift_flags.low_rolling_sharpe.value): 0.11333136870186329
- Difference: 5.13e-16
- Status: PASSED (within float precision)

### Regime flip verification
- Recomputed from run_history.regime_exposure transitions: 6 flips
- Run history entries: 447
- Expected (if unchanged): 6
- Status: PASSED

### Supervisor loop tests
- Command: `python3 .github/scripts/test_kilo_supervisor_loop.py -v`
- Result: 10/10 passed
- Status: PASSED

## Conclusion

Gate not met. State remains unchanged. Task prepared for next cycle with same gate (2026-10-17T20:00:00Z).
