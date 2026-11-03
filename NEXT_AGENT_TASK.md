# NEXT_AGENT_TASK — Re-check extension after 22:00 UTC 2026-11-03 (Cycle 1107)

## Context
- Checked at 2026-11-03 18:36 UTC (13:36 ET): clock gate NOT released; `last_run_date` 2026-11-02, NAV 132606.795692673, sessions extended 0, write count 0.
- Gate releases at 17:00 ET / 22:00 UTC on 2026-11-03.
- Drift report: stored == recomputed: True (rolling 63d Sharpe -1.3784428809419644 at 2026-11-02).
- Tests: 45 passed.

## Objective
At/after 22:00 UTC on 2026-11-03, run real extension + persistence checks; extend by at most one session to 2026-11-03 if completed bar exists; else sessions_extended==0 with reason.

## Acceptance criteria
- Run `python3 research/extend_paper_trading_state.py`; record gate/candidate/sessions_extended/last_run_date/NAV/reason.
- If completed 2026-11-03 session: sessions_extended==1, last_run_date 2026-11-03, NAV changes, write count 1, state updated, raw cache scratch.
- Else: sessions_extended==0 with explicit reason, NAV unchanged, 0 writes.
- Second invocation idempotent.
- `python3 research/drift_persistence_report.py` reports stored == recomputed: True.
- Tests pass (45).
- `git status --porcelain data/ config/` empty.

## Scope boundaries
- Do not change gates/thresholds/cost model/universe/clock-gate logic.
- Do not commit unless asked.
- Do not modify data/raw/.
- Do not hand-edit canonical state.

## Verification commands (exact, in order)
1. `date -u && TZ=America/New_York date`
2. `python3 research/extend_paper_trading_state.py 2>&1 | tail -25`
3. `python3 research/drift_persistence_report.py 2>&1 | tail -4`
4. `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q`
5. `git status --porcelain data/ config/`
