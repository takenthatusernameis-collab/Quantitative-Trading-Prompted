# Paper Trading Validation Report — Cycle 447

**Generated:** 2026-10-16T01:26:33Z (UTC)

## Context
Cycle 446 completed at 2026-10-16T01:24:34Z (verification only; gate not met). Gate is 2026-10-18T20:00:00Z; now is < gate. No fetch/replay performed. State: 447 run_history (2025-01-02 → 2026-10-14), 6 regime flips, last_run_date 2026-10-14. Report: research/reports/paper_trading_validation_446.md. Drift flag `low_rolling_sharpe` persists: 3 consecutive trading days (2026-10-12: 0.4892, 2026-10-13: 0.3669, 2026-10-14: 0.1133); not yet at the >20-day persistence threshold. All primary go/no-go gates still pass (track record 447 > 126, Sharpe 1.93 > 0.9, max DD -2.93% < 15%, 6 regime flips > 1). Regime unchanged (risk-on, 132 days).

## Objective
Executed the Cycle 447 Post-Gate Data Acquisition Check per NEXT_AGENT_TASK.md.

## Time & Gate State
- **Current UTC time (TZ=UTC date -u +%Y-%m-%dT%H:%M:%SZ):** 2026-10-16T01:26:33Z
- **Gate:** 2026-10-18T20:00:00Z
- **Gate met:** No (< gate)
- **Fetch/Replay performed:** No - per-gate protocol; monitoring/verification and reporting only.

## State Snapshot
- **State file:** data/processed/paper_trading_state.yaml
- **run_history length:** 447 (2025-01-02 → 2026-10-14)
- **last_run_date:** 2026-10-14
- **Regime exposure:** risk-on (132 days, from last run)
- **Regime flips (stored/reported):** 6
- **Rolling 63-day Sharpe (stored drift flag):** 0.11333136870186329
- **Primary gates:** track record 447>126, Sharpe 1.93>0.9, max DD -2.93% < 15%, 6 regime flips > 1 (all pass)

## Independent Verification
- **Rolling 63d Sharpe recomputation from cumulative_returns[-63:]:** 0.11333136870186278
- **Stored value:** 0.11333136870186329
- **Diff (|computed - stored|):** 5.13e-16 (within float precision)
- **Result:** PASS - matches within float precision
- **Regime flips recomputed from run_history:** 6 (len 447)
- **Result:** PASS - consistent

## Drift Analysis
- **low_rolling_sharpe consecutive days (from report history):** 2026-10-12 (0.4892), 2026-10-13 (0.3669), 2026-10-14 (0.1133) - **3 consecutive trading days**
- **Status:** persists; not yet at >20-day persistence threshold
- **Trajectory:** volatile over recent window; consistent with single low-return days moving 63-day window rather than sustained degradation

## Supervisor Loop Tests
- **Command:** `python3 .github/scripts/test_kilo_supervisor_loop.py -v`
- **Result:** Ran 10 tests in ~0.448s, OK (10/10 passed)
- **Result:** PASS

## Supervisor Disposition
- **Protocol:** .kilo-runtime/worker-disposition.json updated within next two tool calls following schema_version 1
- **recommendation_id:** 38817660960-attempt-1-review-0003-2ac0cb7d6609 (from current recommendation)
- **disposition:** verified
- **updated_at:** 2026-10-16T01:26:33Z

## Conclusion
Pre-gate verification completed successfully. Current UTC time 2026-10-16T01:26:33Z is before gate 2026-10-18T20:00:00Z; no fetch/replay performed. All validations pass (rolling Sharpe match within float precision, regime flips correct, supervisor tests all pass). Drift flag remains at 3 consecutive days. State unchanged - track record 447 days (2025-01-02 → 2026-10-14), Sharpe ~1.93, max DD -2.93%, regime risk-on with 6 flips.

## Artifacts
- research/reports/paper_trading_validation_447.md (this file)
