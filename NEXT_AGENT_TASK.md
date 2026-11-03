# NEXT_AGENT_TASK — Post-close extension for 2026-11-03 (Cycle 1106)

## Context
- State at last verified run (2026-11-03 17:43 UTC): `last_run_date` **2026-11-02**, `current_nav` **132606.795692673**, 461 sessions in `run_history` (last three: 2026-10-29, 2026-10-30, 2026-11-02).
- `extend_paper_trading_state.py` at 17:43 UTC: exit 0; clock gate **NOT released** (checks day after last_run_date = 2026-11-03); next expected session 2026-11-03 (Tuesday); `candidate available: no` — "next session 2026-11-03 has not closed yet (today and still in progress)"; `sessions extended: 0`; NAV before == NAV after 132606.795692673; state write count 0; raw cache scratch (canonical data/raw untouched).
- Gate release time: **17:00 ET on 2026-11-03 = 22:00 UTC** (or the start of the following local day, 2026-11-04 00:00 ET). This is a deliberate, documented safety control in `session_is_complete()` (research/extend_paper_trading_state.py:45) — it guarantees the provider bar is final before it enters state. Scope forbids altering the gate.
- Drift report: `stored == recomputed: True` (rolling 63d Sharpe -1.3784428809419644 at 2026-11-02, persistence 4 days).
- Tests: `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q` → **45 passed** in 15.71s.
- `git status --porcelain data/ config/` → empty [exit 0].

## Objective
At/after 22:00 UTC on 2026-11-03 (after the US equity session close), run the real extension and persistence checks. Extend by at most one session to 2026-11-03 if a completed bar exists; otherwise `sessions_extended == 0` with explicit reason and state unchanged.

## Acceptance criteria
- Run `python3 research/extend_paper_trading_state.py`; record gate/candidate/sessions_extended/last_run_date/NAV and reason if 0.
- If completed 2026-11-03 session exists: `sessions_extended == 1`, `last_run_date` advances to 2026-11-03, NAV changes, state write count 1, `data/processed/paper_trading_state.yaml` updated, raw cache scratch (canonical data/raw untouched).
- If not: `sessions_extended == 0` with explicit reason, NAV unchanged, 0 writes.
- Second invocation idempotent: `sessions_extended == 0`, write count 0, NAV unchanged.
- `python3 research/drift_persistence_report.py` reports `stored == recomputed: True`.
- `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q` passes.
- `git status --porcelain data/ config/` empty.

## Scope boundaries
- Do not change thresholds/gates/cost model/universe/clock-gate logic.
- Do not commit unless asked.
- Do not modify data/raw/.
- Do not hand-edit canonical state.
- If gate still not released or session not complete, record `sessions_extended == 0` with explicit reason and leave next task to re-check.

## Current status (updated)
- Last checked: 2026-11-03 17:45 UTC (12:45 PM EST). Gate releases at 22:00 UTC (17:00 ET) on 2026-11-03; NOT released. `python3 research/extend_paper_trading_state.py` -> exit 0, `last processed session: 2026-11-02`, `clock gate: NOT released`, `candidate available: no` (2026-11-03 still in progress), `sessions extended: 0`, NAV before == NAV after 132606.795692673, state write count 0, raw cache scratch (canonical data/raw untouched). `python3 research/drift_persistence_report.py` -> `stored == recomputed: True` (rolling 63d Sharpe -1.3784 at 2026-11-02). `python -m pytest ... -q` -> **45 passed, 136 warnings in 18.25s**. `git status --porcelain data/ config/` -> empty.

## Verification commands (exact, in order)
1. `date -u && TZ=America/New_York date`
2. `python3 research/extend_paper_trading_state.py 2>&1 | tail -25`
3. `python3 research/drift_persistence_report.py 2>&1 | tail -4`
4. `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q`
5. `git status --porcelain data/ config/`
