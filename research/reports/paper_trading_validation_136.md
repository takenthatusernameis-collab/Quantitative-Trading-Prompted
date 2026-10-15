# Paper Trading Validation Report - Cycle 136

## UTC Session Time
2026-10-15T15:00:30Z

## Post-Close Gate Evaluation
**Gate Time:** 2026-10-17T20:00:00Z
**Session Time:** 2026-10-15T15:00:30Z
**Result:** GATE NOT MET (session_time < gate_time)

Session time is before the post-close gate. No fetch or replay performed.

## Verification Results

### 3. Independent Rolling-63-Day Sharpe Verification
- Computed from last 63 cumulative returns: 0.11333136870186278
- Stored value in state.drift_flags.low_rolling_sharpe.value: 0.11333136870186329
- **Status:** MATCH (within float precision)

### 4. Regime Flip Verification
- Regime flips from run_history.regime_exposure transitions: 6
- Number of run_history entries: 447
- Expected value (from context): 6
- **Status:** MATCH

### 5. Supervisor Loop Tests
- Command: `python3 .github/scripts/test_kilo_supervisor_loop.py -v`
- Results: 10/10 tests passed
- Output: `Ran 10 tests in 0.442s — OK`
- **Status:** ALL TESTS PASSED

## Track Record Status (Unchanged)
- **Track Record Days:** 447 days (2025-01-02 → 2026-10-14)
- **NAV:** $135,043.35
- **Sharpe Ratio:** 1.9272
- **Max Drawdown:** -2.93%
- **Rolling 63-Day Sharpe:** 0.1133
- **Drift Flag:** Persists (3 consecutive days, not yet >20d threshold)

## Notes
- No fetch or replay performed due to gate not being met.
- All independent verifications matched stored values.
- Same post-close gate preserved for next cycle: 2026-10-17T20:00:00Z.
- Validation completed at session time: 2026-10-15T15:00:30Z.