# NEXT_AGENT_TASK — Re-run paper-trading extension after 2026-11-03 session closes

## Context
Current time: 2026-11-02T04:15Z UTC (Sunday 2026-11-01 23:15 ET).
Most recent state: `data/processed/paper_trading_state.yaml` last_run_date `2026-10-30` (NAV ~133019.54).
Drift/persistence: `stored == recomputed: True`, rolling 63d Sharpe -0.7690 at 2026-10-30.
Tests: `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q` -> 39 passed.
Extension check (2026-11-02T04:15Z): `sessions extended: 0` because 2026-11-02 (Monday) has not closed yet (current ET 2026-11-01 23:15 EST, session usable after 17:00 ET on 2026-11-02). Next expected session is 2026-11-02.

## Objective
Re-run `python research/extend_paper_trading_state.py` after the 2026-11-02 (Monday) session closes (~17:00 ET / 22:00 UTC on 2026-11-02). If a completed bar now exists beyond last_run_date (2026-10-30), extend by at most one session to 2026-11-02; `sessions extended: 1` and `last_run_date` advances. If not yet closed, check again; if Monday's bar becomes available, extend it. Otherwise document reason.

## Acceptance criteria
- `python research/extend_paper_trading_state.py` exits 0
- If completed session exists beyond 2026-10-30: extend by at most one session; `sessions extended: 1` and `last_run_date` advances to the extended session date
- If no completed bar available: `sessions extended: 0`, state unchanged, NAV unchanged (document reason)
- `python research/drift_persistence_report.py` -> `stored == recomputed: True`
- `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q` passes
- `git status --porcelain data/ config/` empty

## Validation commands
```bash
python research/extend_paper_trading_state.py 2>&1 | tail -25
python research/drift_persistence_report.py 2>&1 | tail -10
python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q
git status --porcelain data/ config/
```

## Scope boundaries
- Do not change thresholds/gates, cost model, universe, or clock-gate logic
- Do not commit unless explicitly asked
- Do not modify `data/raw/`
