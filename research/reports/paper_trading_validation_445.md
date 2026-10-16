# Paper Trading Validation Report - Cycle 445

**Validation Date (UTC):** 2026-10-16T01:21:39Z
**Previous Report:** research/reports/paper_trading_validation_444.md
**State File:** data/processed/paper_trading_state.yaml
**Run:** GitHub Actions run ID 38817660960, attempt 1, session 74, invocation 1

## Cycle Status
- **Cycle:** 445 (Post-Gate Data Acquisition Check)
- **Gate:** 2026-10-18T20:00:00Z
- **Current UTC Time:** 2026-10-16T01:21:39Z
- **Gate Met:** No (pre-gate)
- **Fetch/Replay Performed:** No - per-gate protocol; only verification and reporting.

## State Snapshot
- **run_history length:** 447 (2025-01-02 → 2026-10-14)
- **last_run_date:** 2026-10-14
- **Regime exposure:** risk-on (132 days)
- **Regime flips:** 6
- **Rolling 63-day Sharpe (stored drift flag):** 0.1133
- **Primary gates:** track record 447>126, Sharpe 1.93>0.9, max DD -2.93% < 15%, 6 regime flips > 1 (all pass)

## Independent Verification
- **Rolling 63d Sharpe recomputation from cumulative_returns[-63:]:** matches stored `drift_flags.low_rolling_sharpe.value`
- **Diff (|computed - stored|):** 5.13e-16 (within float precision - PASS)
- **Regime flips recomputed from run_history:** 6 (PASS) - consistent with stored count
- **Last 63 cumulative returns window:** validated (length 63)

## Drift Analysis
- **low_rolling_sharpe consecutive days:** 2026-10-12 (0.4892), 2026-10-13 (0.3669), 2026-10-14 (0.1133) - **3 consecutive trading days**
- **Status:** persists; not yet at >20-day persistence threshold
- **Trajectory:** volatile over recent window; consistent with single low-return days moving 63-day window

## Supervisor Loop Tests
- **Command:** `python3 .github/scripts/test_kilo_supervisor_loop.py -v`
- **Result:** Ran 10 tests in 0.407s, OK (10/10 passed - PASS)

## Conclusion
Pre-gate verification completed successfully. No data fetch/replay performed as gate not yet met. All validations pass (rolling Sharpe match, regime flips correct, supervisor tests all pass). Drift flag remains at 3 consecutive days. Ready for next cycle.

## Artifacts
- research/reports/paper_trading_validation_445.md (this file)
