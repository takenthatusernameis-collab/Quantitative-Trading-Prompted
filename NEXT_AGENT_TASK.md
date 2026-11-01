# NEXT_AGENT_TASK — Extend paper-trading state after 17:00 ET 2026-11-02

## Context
UTC 2026-11-01T23:00:30Z / ET 2026-11-01 18:00:30 EST. Ran `python research/extend_paper_trading_state.py` now: clock gate released but `next expected session 2026-11-02 (Monday) not closed yet` → `sessions extended: 0`, NAV unchanged (133019.54382525434). `python research/drift_persistence_report.py` shows `stored == recomputed: True`. `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q` passed 39/39. `git status --porcelain data/ config/` clean. Dependencies installed (no import errors).

## Objective
Execute at or after 17:00 ET on 2026-11-02: run `python research/extend_paper_trading_state.py` to extend paper-trading state by at most one session if 2026-11-02 has closed. Also consider 2026-11-03 if needed. Record exact commands and outputs.

## Acceptance criteria
- `python research/extend_paper_trading_state.py` exits 0
- If a completed session exists beyond last_run_date (2026-10-30): extend by at most one session; `sessions extended: 1` and `last_run_date` advances if new completed bar found
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
