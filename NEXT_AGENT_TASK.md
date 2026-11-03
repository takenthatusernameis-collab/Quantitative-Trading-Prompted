# NEXT_AGENT_TASK — Re-check post-gate-release extension (Cycle 1096)

## Context
- State: last_run_date 2026-11-02, NAV 132606.795692673, sha256 43074f0e02629cdc2929c83c536a89be1982e39eb95ebfcb6b39ea7e90bcf41e.
- Cycle 1095 ran at 2026-11-03T09:57 UTC: gate NOT released, sessions_extended 0, NAV unchanged, 0 writes, drift stored==recomputed True, tests 45 passed, data/config clean.
- Corrective invocation 1 ran at 2026-11-03T10:07 UTC: gate STILL NOT released (current ET 05:07). Pre-close verification now DURABLY recorded in .kilo-runtime/worker-disposition.json (verification field populated): extend_paper_trading_state.py exit 0, sessions_extended 0, NAV unchanged, 0 writes; drift stored==recomputed True; pytest 45 passed; git status data/ config/ empty. Second invocation idempotent.
- The 2026-11-03 (Tuesday) session is still in progress; market closes 17:00 ET (~22:00 UTC).

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
