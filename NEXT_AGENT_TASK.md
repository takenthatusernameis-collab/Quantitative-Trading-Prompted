# NEXT_AGENT_TASK — Verify and report paper-trading state at next close window

## Context
Last check: 2026-11-03T01:55 UTC. State: last_run_date 2026-11-02, sessions=0 in processed state (NAV 132606.795692673). extend_paper_trading_state reports clock gate NOT released (current time 2026-11-02 20:55 ET; next session 2026-11-03 not closed) — no completed bar to extend. drift_persistence: stored == recomputed True. All related tests pass (44 passed). git status data/config empty.

## Objective
After 2026-11-03 session closes (~17:00 ET / ~22:00 UTC), re-run the extension and persistence checks, documenting outcomes precisely.

## Acceptance criteria
- Run `python3 research/extend_paper_trading_state.py` and record observed gate/candidate/sessions_extended.
- If a completed session exists: sessions extended == 1 and last_run_date advances to 2026-11-03; else sessions extended == 0 with explicit reason.
- `python3 research/drift_persistence_report.py` reports `stored == recomputed: True`.
- `python3 -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q` passes.
- `git status --porcelain data/ config/` empty (no unintended writes).

## Validation commands
```bash
python3 research/extend_paper_trading_state.py 2>&1 | tail -40
python3 research/drift_persistence_report.py 2>&1 | tail -3
python3 -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q
git status --porcelain data/ config/
```

## Scope boundaries
- Do not change thresholds/gates, cost model, universe, or clock-gate logic.
- Do not commit unless explicitly asked.
- Do not modify `data/raw/`.
- Do not revert pre-existing `data/processed/paper_trading_state.yaml` modifications.
