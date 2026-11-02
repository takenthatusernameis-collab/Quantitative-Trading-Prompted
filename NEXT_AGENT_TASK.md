# NEXT_AGENT_TASK — Re-check paper-trading extension at/after 22:00 UTC 2026-11-02

## Context
UTC 2026-11-02T02:58Z / ET 2026-11-01 21:58 EST. Ran `python research/extend_paper_trading_state.py`: clock gate released but candidate session 2026-11-02 (Monday) not closed yet → `sessions extended: 0`, NAV unchanged (133019.54382525434), last_run_date 2026-10-30. `python research/drift_persistence_report.py` -> `stored == recomputed: True`. Tests 39/39 passed. `git status --porcelain data/ config/` empty. At/after 2026-11-02T22:00 UTC (17:00 ET) the candidate session may be complete.

## Objective
Execute at or after 2026-11-02T22:00 UTC: run `python research/extend_paper_trading_state.py` to extend paper-trading state by at most one session if 2026-11-02 has closed. Record exact commands and outputs. If still not closed, next candidate could be 2026-11-03.

## Acceptance criteria
- `python research/extend_paper_trading_state.py` exits 0
- If a completed session exists beyond last_run_date (2026-10-30): extend by at most one session; `sessions extended: 1` and `last_run_date` advances
- If no completed bar available: `sessions extended: 0`, state unchanged, NAV unchanged
- `python research/drift_persistence_report.py` -> `stored == recomputed: True`
- `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q` passes
- `git status --porcelain data/ config/` empty

## Validation commands
```bash
python research/extend_paper_trading_state.py
python research/drift_persistence_report.py
python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q
git status --porcelain data/ config/
```

## Scope boundaries
- Do not change thresholds/gates, cost model, universe, or clock-gate logic
- Do not commit unless explicitly asked
- Do not modify `data/raw/`
