# NEXT_AGENT_TASK — Verify and report paper-trading state at next close window

## Context
This cycle (2026-11-03T02:09Z, ET = Mon 2026-11-02 ~21:09): ran the full acceptance suite before the 2026-11-03 session close.
- `python3 research/extend_paper_trading_state.py`: clock gate NOT released, candidate available: no, sessions extended: 0, reason "next session 2026-11-03 has not closed yet (in the future (today is 2026-11-02)); no completed candidate bar exists to extend into"; no state write, NAV unchanged 132606.795692673, canonical data/raw untouched.
- `python3 research/drift_persistence_report.py`: stored == recomputed: True (drift flag -1.3784428809419644 at 2026-11-02, persistence 4 days).
- `python3 -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q`: 44 passed in 13.91s.
- `git status --porcelain data/ config/`: empty.
Committed state last_run_date remains 2026-11-02 (no advance, as expected pre-close).

## Objective
After 2026-11-03 session closes (~17:00 ET / ~22:00 UTC), re-run the extension and persistence checks, documenting outcomes precisely. Expect the "then" branch: sessions extended == 1 and last_run_date advances to 2026-11-03 if a completed 2026-11-03 bar exists; otherwise sessions extended == 0 with explicit reason.

## Acceptance criteria
- Run `python3 research/extend_paper_trading_state.py` and record observed gate/candidate/sessions_extended/last_run_date.
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
