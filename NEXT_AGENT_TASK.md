# NEXT_AGENT_TASK — Re-check post-gate-release extension (Cycle 1103)

## Context
- State: last_run_date 2026-11-02, NAV 132606.795692673, sha256 43074f0e02629cdc2929c83c536a89be1982e39eb95ebfcb6b39ea7e90bcf41e.
- Cycle 1103 (2026-11-03T10:59 UTC / 05:59 ET): gate NOT released; 2026-11-03 session has not yet opened (market opens 09:30 ET / 14:30 UTC, closes 17:00 ET / 22:00 UTC). No extension, no writes. sessions_extended 0, NAV unchanged, state write count 0, raw cache scratch (canonical untouched). Reason: next session 2026-11-03 not closed yet (today and still in progress / not yet started).
- drift_persistence_report.py: stored == recomputed True (rolling 63d Sharpe -1.3784428809419644 at 2026-11-02, persistence 4 days 2026-10-28 -> 2026-11-02).
- Tests: 45 passed (tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py).
- Supervisor recommendation 41605030040-attempt-1-review-0005-cd85aaa1838f disposition `accepted`: wait for gate release at ~22:00 UTC, then retry extend_paper_trading_state.py. Wakeup scheduled for 2026-11-03T22:00:00Z.
- Verification at 2026-11-03T10:57-10:59 UTC: extend script exit 0, sessions extended 0 with explicit reason, NAV 132606.795692673 unchanged, 0 writes; second invocation idempotent (sessions extended 0, write count 0); drift stored == recomputed True; 45 tests passed; git status --porcelain data/ config/ empty.

## Objective
At/after ~22:00 UTC on 2026-11-03 (after US equity session close), run the real extension and persistence checks. Extend by at most one session to 2026-11-03 if a completed bar exists; otherwise sessions_extended == 0 with explicit reason and state unchanged.

## Acceptance criteria
- Run `python3 research/extend_paper_trading_state.py`; record gate/candidate/sessions_extended/last_run_date/NAV and reason if 0.
- If completed 2026-11-03 session exists: sessions_extended == 1 and last_run_date advances to 2026-11-03; else sessions_extended == 0 with explicit reason, NAV unchanged, 0 writes.
- Second invocation: sessions_extended == 0, write count 0, NAV unchanged.
- `python3 research/drift_persistence_report.py` reports stored == recomputed: True.
- `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q` passes.
- `git status --porcelain data/ config/` empty.

## Scope boundaries
- Do not change thresholds/gates/cost model/universe/clock-gate logic.
- Do not commit unless asked.
- Do not modify data/raw/.
- Do not hand-edit canonical state.
- If gate still not released or session not complete, record sessions_extended == 0 with explicit reason and leave next task to re-check.
