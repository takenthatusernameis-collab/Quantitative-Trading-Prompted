# Paper Trading Validation Report - Cycle 146

**UTC Session Time:** 2026-10-15T15:36:35Z
**Post-Close Gate:** 2026-10-17T20:00:00Z
**Gate Status:** NOT MET (session time < gate time)

## Actions Performed
- Timestamp gate enforcement: Confirmed gate not met.
- Independent rolling-63-day Sharpe verification: Computed 0.11333136870186278, stored value 0.11333136870186329 (difference ~5.13e-16).
- Regime flip verification: Counted 6 flips from 447 run_history entries.
- Supervisor loop tests: All 10 tests passed.

## Fetch and Replay
- **Not attempted** due to gate not being met.
- No fetch or replay performed.

## Track Record
- **Unchanged** (no new data fetched or replayed).
- Prior track record: 447 days (2025-01-02 → 2026-10-14), NAV $135,043.35, Sharpe 1.9272, max DD -2.93%, rolling 63d Sharpe 0.1133.
- Drift flag persists (3 consecutive days, not yet >20d threshold).
- Regime: risk-on (132 days).

## Verification Details
- Rolling 63-day Sharpe: 0.11333136870186278 (matches stored value within float precision).
- Regime flips: 6 (matches expected count).
- Supervisor loop tests: 10/10 passed.

## Next Steps
- Leave the post-close gate unchanged for the next cycle.
- The next session will re-evaluate the gate at or after 2026-10-17T20:00:00Z.
