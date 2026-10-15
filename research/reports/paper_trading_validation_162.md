# Paper Trading Validation — Cycle 162

**Generated:** 2026-10-15T17:20:22Z UTC
**Session time:** 2026-10-15T17:20:22Z UTC
**Post-close gate:** 2026-10-18T20:00:00Z UTC
**Gate met:** No (session_time < gate)

## Task status (from NEXT_AGENT_TASK.md)
Post-Close Evaluation Gate Execution — Cycle 162 (Pending Gate). Objective 1 applies.

## Timing
- Recorded UTC: `TZ=UTC date -u +%Y-%m-%dT%H:%M:%SZ` → 2026-10-15T17:20:22Z
- Gate: 2026-10-18T20:00:00Z
- Decision: Do not fetch or replay (gate not met).

## Data/state (from data/processed/paper_trading_state.yaml, as of 2026-10-14)
- Track record: 447 days (2025-01-02 → 2026-10-14)
- NAV: $135,043.35
- Peak: $139,120.07
- Max DD: -2.93%
- Sharpe: 1.9272
- Rolling 63d Sharpe (stored): 0.11333136870186329
- Cumulative returns count: 447
- run_history count: 447
- cumulative_dates count: 447
- Last run date: 2026-10-14
- Drift flag: persists (3 consecutive days, not yet >20d threshold)
- Regime: risk-on (132 days)
- Regime flips: 6

## Independent verifications (3-4)
1. Rolling 63d Sharpe recomputed from last 63 cumulative_returns
- Computed: (mean*252)/(std(ddof=1)*sqrt(252)) over last 63
- Computed value: 0.11333136870186278
- Stored value: 0.11333136870186329
- Match: Yes, within float precision (diff 5.13e-16)

2. Regime flip verification from run_history transitions
- Computed: 6 (transitions where regime_exposure changed)
- Expected (no replay extension): 6
- Match: Yes

3. State integrity (counts consistent)
- cumulative_returns == run_history == cumulative_dates (447)
- last_run_date == 2026-10-14
- NAV/peak/max DD match recorded values

## Supervisor loop tests (5)
- Command: `python3 .github/scripts/test_kilo_supervisor_loop.py -v`
- Result: 10/10 passed (OK)
- Evidence captured in test output.

## Fetch/replay attempt
- Not attempted (gate not met). No new data fetched; no replay run.

## Changes
- None to code, state, or data (read-only verification).

## Conclusion
Gate not met. State remains consistent with Cycle 161. Verifications pass. Supervisor tests pass. No data changes.
