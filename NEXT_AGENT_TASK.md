# NEXT_AGENT_TASK — Extend paper-trading state after the 2026-11-03 close window

## Context
Cycle 1083 (2026-11-03T04:01:42Z, ET = Mon 2026-11-02 23:01) re-ran all checks; clock gate still NOT released because ET date is still 2026-11-02.
- `python3 research/extend_paper_trading_state.py`: clock gate NOT released, candidate available: no, sessions extended: 0, reason "next session 2026-11-03 has not closed yet (in the future (today is 2026-11-02)); no completed candidate bar exists to extend into"; state write count 0, NAV unchanged 132606.795692673, canonical data/raw untouched.
- Idempotency second invocation: sessions extended 0, state write count 0, NAV unchanged 132606.795692673.
- `python3 research/drift_persistence_report.py`: stored == recomputed: True (drift flag -1.3784428809419644 at 2026-11-02, persistence 4 days).
- `python3 -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q`: 45 passed, 140 warnings.
- `git status --porcelain data/ config/`: empty.

Blocker: ET clock still on 2026-11-02; gate releases once ET date advances to 2026-11-03 (or after 17:00 ET on 2026-11-03). No state write possible until then.

## Objective
After 2026-11-03 session closes (~17:00 ET / ~22:00 UTC), re-run the extension and persistence checks, documenting outcomes precisely. Expect the "then" branch: sessions extended == 1 and last_run_date advances to 2026-11-03 if a completed 2026-11-03 bar exists; otherwise sessions extended == 0 with explicit reason.

## Acceptance criteria
- Run `python3 research/extend_paper_trading_state.py` and record observed gate/candidate/sessions_extended/last_run_date.
- If a completed session exists: sessions extended == 1 and last_run_date advances to 2026-11-03; else sessions extended == 0 with explicit reason.
- Run a second invocation to confirm idempotency: sessions extended == 0, state write count == 0, NAV unchanged.
- `python3 research/drift_persistence_report.py` reports `stored == recomputed: True`.
- `python3 -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q` passes.
- `git status --porcelain data/ config/` empty (no unintended writes).

## Validation commands
```bash
python3 research/extend_paper_trading_state.py 2>&1 | tail -40
python3 research/extend_paper_trading_state.py 2>&1 | tail -8   # idempotency check
python3 research/drift_persistence_report.py 2>&1 | grep -i "stored == recomputed"
python3 -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q
git status --porcelain data/ config/
```

## Scope boundaries
- Do not change thresholds/gates, cost model, universe, or clock-gate logic.
- Do not commit unless explicitly asked.
- Do not modify `data/raw/`.
- Do not revert pre-existing `data/processed/paper_trading_state.yaml` modifications.
