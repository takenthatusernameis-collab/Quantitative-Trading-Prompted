# NEXT_AGENT_TASK — Re-run paper-trading extension after Nov 3 session close (gate release)

## Context (Cycle 1086, 2026-11-03T05:05:00Z / Tue 2026-11-03 00:05 EST)
- Prior cycle: gate NOT released (00:03 ET Nov 3); sessions extended 0; NAV 132606.795692673; last_run_date 2026-11-02.
- drift report: stored == recomputed True (rolling 63d Sharpe -1.3784428809419644 at 2026-11-02, persistence 4 days, streak 2026-10-28 -> 2026-11-02).
- Tests: 45 passed, 140 warnings. git status data/ config/ empty.
- Gate releases at 17:00 ET on 2026-11-03 (~22:00 UTC Tue 2026-11-03).

## Objective
After 17:00 ET on 2026-11-03, re-run the extension and persistence checks, documenting outcomes precisely. Expect the "then" branch: sessions extended == 1 and last_run_date advances to 2026-11-03 if a completed 2026-11-03 bar exists; otherwise sessions extended == 0 with explicit reason.

## Acceptance criteria
- Run `python3 research/extend_paper_trading_state.py` and record observed gate/candidate/sessions_extended/last_run_date.
- If a completed session exists: sessions_extended == 1 and last_run_date advances to 2026-11-03; else sessions_extended == 0 with explicit reason.
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
