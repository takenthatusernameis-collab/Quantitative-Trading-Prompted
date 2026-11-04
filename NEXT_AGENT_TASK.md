# NEXT_AGENT_TASK — Paper-trading extension gate check (post-236 verification)

## Context
- Verified 2026-11-04T22:47Z (17:47 EST, Tuesday): gate NOT released; last processed session 2026-11-04, NAV 133995.4210085515, sessions_extended 0, 0 writes.
- Verified 2026-11-04T22:48Z (17:48 EST): re-confirmed gate NOT released; state unchanged; drift rolling 63d Sharpe -0.8724 at 2026-11-04.
- Verified 2026-11-04T23:28Z (18:28 EST, Tuesday, invocation 236): re-confirmed gate NOT released; state unchanged at 2026-11-04, NAV 133995.4210085515; drift rolling 63d Sharpe -0.8724 at 2026-11-04; git status --porcelain data/ config/ empty; full test suite 45 passed; tests/test_real_extension_path.py confirmed committed at HEAD (9aadb30), no working-tree test edits.
- Clock gate NOT released at run time; candidate session 2026-11-05 has not closed.
  - Reason: `next session 2026-11-05 has not closed yet (in the future (today is 2026-11-04)); no completed candidate bar exists to extend into`
- Gate releases at 17:00 ET / 22:00 UTC on 2026-11-05 (Wednesday) once local clock passes 17:00 ET on 2026-11-05 session date (or following local day start logic).
- drift_persistence_report: rolling 63d Sharpe -0.8724 at 2026-11-04, drift flags show low_rolling_sharpe persistence_days 6.
- Idempotency confirmed across invocations 22:47 / 22:48 / 23:28: 0 writes, NAV unchanged each time.
- `git status --porcelain data/ config/` -> empty (clean). Only non-data/config artifact: `research/reports/paper_trading_rolling.md` git_sha provenance line bumps when drift report runs — expected, self-generated report metadata.

## Objective
At/after 22:00 UTC on 2026-11-05, run real extension and persistence checks. Extend by at most one session to 2026-11-05 if a completed bar exists; otherwise sessions_extended==0 with explicit reason and state unchanged.

## Acceptance criteria
- Run `python3 research/extend_paper_trading_state.py`; record gate/candidate/sessions_extended/last_run_date/NAV and reason if 0.
- If completed 2026-11-05 session exists: sessions_extended==1, last_run_date advances to 2026-11-05, NAV changes, state write count 1, raw cache scratch.
- If not: sessions_extended==0 with explicit reason, NAV unchanged, 0 writes.
- Second invocation idempotent: sessions_extended==0, write count 0, NAV unchanged.
- `python3 research/drift_persistence_report.py` reports drift metrics updated.
- `git status --porcelain data/ config/` shows only expected state update (no unintended changes).
- Full test suite (`tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py`) passes.

## Scope boundaries
- Do not change thresholds/gates/cost model/universe/clock-gate logic.
- Do not commit unless asked.
- Do not modify data/raw/.
- Do not hand-edit canonical state.
- Do NOT run before 22:00 UTC on 2026-11-05 (gate not released; would be a premature no-op).

## Verification commands (exact, in order)
1. `date -u && TZ=America/New_York date`
2. `python3 research/extend_paper_trading_state.py 2>&1 | tail -25`
3. `python3 research/drift_persistence_report.py 2>&1 | tail -4`
4. `python3 research/extend_paper_trading_state.py 2>&1 | tail -6`
5. `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q`
6. `git status --porcelain data/ config/`

## Handoff notes (current cycle)
- **Time/context:** UTC 2026-11-04T23:28Z (18:28 EST, Tuesday). Dependencies installed. Verified state already at 2026-11-04; no extension needed today.
- **Durable verification performed (invocation 236):**
  1. `extend_paper_trading_state.py` (x2) -> gate NOT released, `sessions extended: 0`, NAV unchanged 133995.4210085515, 0 writes, idempotent.
  2. `drift_persistence_report.py` -> rolling Sharpe -0.8724 at 2026-11-04, drift flags present; report provenance line bumped to 48a2d18 (expected self-generated metadata).
  3. `pytest ... -q` -> 45 passed in 28.95s.
  4. `git status --porcelain data/ config/` -> empty (canonical state clean).
  5. Confirmed `tests/test_real_extension_path.py` committed at HEAD (9aadb30); no uncommitted test edits.
- **Blocker:** Clock gate not released; next session 2026-11-05 not closed. Wait for gate release at 17:00 ET / 22:00 UTC on 2026-11-05.