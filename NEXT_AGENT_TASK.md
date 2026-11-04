# NEXT_AGENT_TASK — Paper-trading extension gate check (2026-11-04 post-close)

## Context
- Verified 2026-11-04 04:29 UTC: last_run_date 2026-11-03, NAV 132866.0435881768, sessions 461, sessions_extended 0, 0 writes.
- Clock gate NOT released at run time (23:29 EST Tuesday 2026-11-03); candidate session 2026-11-04 has not closed.
- Gate releases at 17:00 ET / 22:00 UTC on 2026-11-04 (Wednesday).
- drift_persistence_report: stored == recomputed True (rolling 63d Sharpe -1.3997).
- Idempotency confirmed (2nd invocation: 0 writes, NAV unchanged).
- Wakeup wku_1a4d2454a0011tEq7bKvw7FYoQ scheduled 2026-11-04T22:05:00Z.

## Objective
At/after 22:00 UTC on 2026-11-04, run real extension and persistence checks. Extend by at most one session to 2026-11-04 if a completed bar exists; otherwise sessions_extended==0 with explicit reason and state unchanged.

## Acceptance criteria
- Run `python3 research/extend_paper_trading_state.py`; record gate/candidate/sessions_extended/last_run_date/NAV and reason if 0.
- If completed 2026-11-04 session exists: sessions_extended==1, last_run_date advances to 2026-11-04, NAV changes, state write count 1, raw cache scratch.
- If not: sessions_extended==0 with explicit reason, NAV unchanged, 0 writes.
- Second invocation idempotent: sessions_extended==0, write count 0, NAV unchanged.
- `python3 research/drift_persistence_report.py` reports stored == recomputed: True.
- `git status --porcelain data/ config/` shows only expected state update (no unintended changes).

## Scope boundaries
- Do not change thresholds/gates/cost model/universe/clock-gate logic.
- Do not commit unless asked.
- Do not modify data/raw/.
- Do not hand-edit canonical state.

## Verification commands (exact, in order)
1. `date -u && TZ=America/New_York date`
2. `python3 research/extend_paper_trading_state.py 2>&1 | tail -25`
3. `python3 research/drift_persistence_report.py 2>&1 | tail -4`
4. `python3 research/extend_paper_trading_state.py 2>&1 | tail -6`
5. `git status --porcelain data/ config/`