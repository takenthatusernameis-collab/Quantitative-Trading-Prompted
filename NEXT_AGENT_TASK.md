# NEXT_AGENT_TASK — Ext paper-trading state after the 2026-11-03 close window

## Context (Cycle 1085, 2026-11-03T05:05:00Z / Tue 2026-11-03 00:05 EST)
- Current state: `last_run_date: 2026-11-02`, NAV `132606.795692673` (unchanged). `data/processed/paper_trading_state.yaml` not modified.
- `python3 research/extend_paper_trading_state.py`: exit 0, clock gate NOT released (releases at 17:00 ET on 2026-11-03). `next expected session: 2026-11-03 (Tuesday)`, `session already complete: False`, `candidate available: no` — reason "next session 2026-11-03 has not closed yet (today and still in progress); no completed candidate bar exists to extend into". `sessions extended: 0`, `state write count: 0`, raw cache untouched (scratch).
- Idempotency second invocation: `sessions extended: 0`, `state write count: 0`, NAV unchanged 132606.795692673.
- `python3 research/drift_persistence_report.py`: `stored == recomputed: True` (rolling 63d Sharpe `-1.3784428809419644` at 2026-11-02, persistence 4 days, streak 2026-10-28 -> 2026-11-02).
- `python3 -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q`: **45 passed, 140 warnings**.
- `git status --porcelain data/ config/`: empty (no unintended writes).
- Blocker: ET clock is 2026-11-03 00:05 EST; the Nov 3 US session has not opened (opens 09:30 ET) and has not closed (~16:00 ET / ~21:00 UTC). Gate releases at 17:00 ET on 2026-11-03. No state write possible until a completed 2026-11-03 bar exists.
- `.kilo-runtime/worker-disposition.json`: `rejected_with_reason` for supervisor recommendation `41562401354-attempt-1-review-0002-0f859b77e50d` (pytest already installed; install out of scope).

## Objective
After 2026-11-03 session closes (~17:00 ET / ~22:00 UTC on Tue 2026-11-03), re-run the extension and persistence checks, documenting outcomes precisely. Expect the "then" branch: `sessions extended == 1` and `last_run_date` advances to `2026-11-03` if a completed 2026-11-03 bar exists; otherwise `sessions extended == 0` with explicit reason.

## Acceptance criteria
- Run `python3 research/extend_paper_trading_state.py` and record observed gate/candidate/sessions_extended/last_run_date.
- If a completed session exists: `sessions_extended == 1` and `last_run_date` advances to `2026-11-03`; else `sessions_extended == 0` with explicit reason.
- Run a second invocation to confirm idempotency: `sessions_extended == 0`, `state write count == 0`, NAV unchanged.
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
