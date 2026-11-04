# NEXT_AGENT_TASK — Paper-trading extension for 2026-11-04 (Wednesday)

## Context
- State verified 2026-11-04 03:31 UTC (Tue 22:31 EST): `last_run_date` **2026-11-03**, `current_nav` **132866.0435881768**, `sessions` 461, `sessions_extended == 0`, 0 writes, `data/` and `config/` clean, `stored == recomputed: True` (rolling 63d Sharpe -1.3997 at 2026-11-03).
- `extend_paper_trading_state.py` correctly reports gate NOT released; 2026-11-04 session not yet closed; idempotent on 2nd invocation.
- Focused test suite: **45 passed in 19.15s** (test_paper_trading_extend.py, test_drift_persistence.py, test_verify_monday_extension_path.py, test_real_extension_path.py).
- Active-path verifier `research/verify_monday_extension_path.py`: **RESULT PASS** (target 2026-10-19, sessions_extended 1, state_writes 1, nav 132866.04 -> 133442.57, canonical state hash unchanged True, canonical data/raw unchanged True). Machinery confirmed functional.
- Wakeup `wku_1a49ef396001eK0lcPXkH4Fv4N` scheduled for 2026-11-04T22:05:00Z (5 min after gate release at 22:00 UTC / 17:00 ET Wednesday).

## Objective
At/after 22:00 UTC on 2026-11-04, run the real extension and persistence checks. Extend by at most one session to 2026-11-04 if a completed bar exists; otherwise `sessions_extended == 0` with explicit reason and state unchanged.

## Acceptance criteria
- Run `python3 research/extend_paper_trading_state.py`; record gate/candidate/sessions_extended/last_run_date/NAV and reason if 0.
- If completed 2026-11-04 session exists: `sessions_extended == 1`, `last_run_date` advances to 2026-11-04, NAV changes, state write count 1, raw cache scratch.
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