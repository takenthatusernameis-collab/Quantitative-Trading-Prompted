# NEXT_AGENT_TASK — Re-check paper-trading extension after 17:00 ET on 2026-11-02

## Context
Session UTC 2026-11-01T21:03Z ran `python research/extend_paper_trading_state.py`. Current time ET 2026-11-01 16:03:30 EST; next expected session 2026-11-02 (Monday) not closed yet (`sessions extended: 0`, `candidate_available: no`). `python research/drift_persistence_report.py` shows `stored == recomputed: True` (git_sha 160bfaf). Tests `tests/test_paper_trading_extend.py tests/test_drift_persistence.py` all passed (39 passed in 3.34s). `git status --porcelain data/ config/` empty. Working tree has only `research/reports/paper_trading_rolling.md` modified (generated artifact).

## Objective
Run `python research/extend_paper_trading_state.py` at or after 17:00 ET on 2026-11-02 to extend paper-trading state by one session if available (2026-11-02 session may have closed by then; also check 2026-11-03). Record exact commands and outputs.

## Acceptance criteria
- `python research/extend_paper_trading_state.py` exits 0
- If completed session exists beyond last_run_date (2026-10-30): extend by at most one session; `sessions extended: 1` and `last_run_date` advances if a new completed bar is found
- If no completed bar available: `sessions extended: 0`, state unchanged, NAV unchanged
- `python research/drift_persistence_report.py` -> `stored == recomputed: True`
- `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q` passes
- `git status --porcelain data/ config/` empty (canonical data untouched)

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
- Do not modify `data/raw/` (fetcher uses scratch cache only)
