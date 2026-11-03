# NEXT_AGENT_TASK — Re-check post-gate-release extension (Cycle 1097)

## Context
- State: last_run_date 2026-11-02, NAV 132606.795692673, sha256 43074f0e02629cdc2929c83c536a89be1982e39eb95ebfcb6b39ea7e90bcf41e.
- Cycle 1095/1096: gate NOT released pre-close; no extension, no writes.
- Current check (2026-11-03T10:09 UTC / 05:09 ET): `extend_paper_trading_state.py` reports clock gate NOT released, session 2026-11-03 not complete; sessions_extended 0, NAV unchanged, state write count 0, `raw cache: scratch (canonical data/raw untouched)`.
- `drift_persistence_report.py`: stored == recomputed True (rolling 63d Sharpe -1.3784 at 2026-11-02, persistence 4 days 2026-10-28 -> 2026-11-02).
- Tests: `python3 -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q` -> 45 passed.
- `git status --porcelain data/ config/` empty.

## Objective
After 22:00 UTC on 2026-11-03, run the real extension and persistence checks. Extend by at most one session to 2026-11-03 if a completed bar exists; otherwise sessions_extended == 0 with explicit reason and state unchanged.

## Acceptance criteria
- Run `python3 research/extend_paper_trading_state.py`; record gate/candidate/sessions_extended/last_run_date/NAV.
- If completed 2026-11-03 session exists: sessions_extended == 1 and last_run_date advances; else 0 with explicit reason.
- Second invocation: sessions_extended == 0, write count 0, NAV unchanged.
- `python3 research/drift_persistence_report.py` reports stored == recomputed: True.
- `python3 -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q` passes.
- `git status --porcelain data/ config/` empty.

## Scope boundaries
- Do not change thresholds/gates/cost model/universe/clock-gate logic.
- Do not commit unless asked.
- Do not modify data/raw/.
- Do not hand-edit canonical state.
- If gate still not released, record sessions_extended == 0 with explicit reason and leave next task to re-check.
