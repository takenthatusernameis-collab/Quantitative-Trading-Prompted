# NEXT_AGENT_TASK — Pre-close readiness check for 2026-11-06 (Cycle 1113)

## Context
- State verified this cycle (2026-11-04 02:39 UTC / 21:39 EST Tuesday): `last_run_date` **2026-11-03**, `current_nav` **132866.0435881768**, `sessions_extended == 0`, 0 writes, `data/` and `config/` clean, `stored == recomputed: True` (rolling 63d Sharpe -1.3997 at 2026-11-03).
- The real extension for 2026-11-04 (Wednesday) is executed by the wakeup at 22:00 UTC on 2026-11-04 (see README.md Cycle 1112). After that extension completes, state should advance to `last_run_date: 2026-11-04` if the 2026-11-04 session closed and a completed bar exists.
- The real extension for 2026-11-05 (Thursday) is executed by the wakeup at 22:00 UTC on 2026-11-05.
- Gate for 2026-11-06 (Friday) releases at 22:00 UTC on 2026-11-06 (17:00 ET). Do not alter gate.

## Objective
At/after 22:00 UTC on 2026-11-06, run the real extension and persistence checks. Extend by at most one session to 2026-11-06 if a completed bar exists; otherwise `sessions_extended == 0` with explicit reason and state unchanged.

## Acceptance criteria
- Run `python3 research/extend_paper_trading_state.py`; record gate/candidate/sessions_extended/last_run_date/NAV and reason if 0.
- If completed 2026-11-06 session exists: `sessions_extended == 1`, `last_run_date` advances to 2026-11-06, NAV changes, state write count 1, raw cache scratch.
- If not: `sessions_extended == 0` with explicit reason, NAV unchanged, 0 writes.
- Second invocation idempotent: `sessions_extended == 0`, write count 0, NAV unchanged.
- `python3 research/drift_persistence_report.py` reports `stored == recomputed: True`.
- `git status --porcelain data/ config/` shows only the expected state update (no unintended changes).

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