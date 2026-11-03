# NEXT_AGENT_TASK — Execute post-gate-release extension run (Cycle 1088)

## Context (evidence from this session, 2026-11-03T06:04 UTC)
- Current canonical state (verified by reading data/processed/paper_trading_state.yaml): last_run_date 2026-11-02, NAV 132606.795692673. The state is ALREADY at 2026-11-02, so it cannot "advance to 2026-11-02" — that expectation in the prior task text is stale.
- Current time 2026-11-03 01:06 ET (06:06 UTC). The 2026-11-03 US session has not opened (market opens 09:30 ET) and has not closed.
- Clock gate: NOT released. Next expected session 2026-11-03 (Tuesday), usable after 17:00 ET on 2026-11-03.
- pytest 9.2.0 and pandas 3.1.0 are installed; the four target test files pass (45 passed).
- Supervisor recommendation review-0002 disposition `rejected_with_reason` (pytest-not-installed premise stale); recorded in .kilo-runtime/worker-disposition.json.

## Objective
After 17:00 ET on 2026-11-03 (~22:00 UTC), run the real extension and persistence checks. Expect the extension to target 2026-11-03 (the session after last_run_date 2026-11-02): sessions_extended == 1 and last_run_date advances to 2026-11-03 if a completed 2026-11-03 bar exists in live data; otherwise sessions_extended == 0 with explicit reason.

## Acceptance criteria
- Run `python3 research/extend_paper_trading_state.py` and record observed gate/candidate/sessions_extended/last_run_date/NAV.
- If a completed session exists: sessions_extended == 1 and last_run_date advances to that session; else sessions_extended == 0 with explicit reason.
- Run a second invocation to confirm idempotency: sessions_extended == 0, state write count == 0, NAV unchanged.
- `python3 research/drift_persistence_report.py` reports stored == recomputed: True.
- `python3 -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q` passes.
- `git status --porcelain data/ config/` empty (no unintended writes).

## Validation commands
```bash
python3 research/extend_paper_trading_state.py 2>&1 | tail -40
python3 research/extend_paper_trading_state.py 2>&1 | tail -8
python3 research/drift_persistence_report.py 2>&1 | grep -i "stored == recomputed"
python3 -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q
git status --porcelain data/ config/
```

## Scope boundaries
- Do not change thresholds/gates, cost model, universe, or clock-gate logic.
- Do not commit unless explicitly asked.
- Do not modify data/raw/.
- Do not revert pre-existing data/processed/paper_trading_state.yaml modifications.
- Do not hand-edit the canonical state to simulate the extension; the real script owns the write.
- Do not wait passively past 17:00 ET on 2026-11-03; if the gate is still not released at run time, record sessions_extended == 0 with explicit reason and leave the next task to re-check after the session closes.
