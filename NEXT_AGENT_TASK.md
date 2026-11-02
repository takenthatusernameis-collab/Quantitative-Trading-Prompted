# NEXT_AGENT_TASK — Re-check paper-trading extension at/after 17:00 ET 2026-11-02

## Context
UTC 2026-11-02T00:57Z / ET 2026-11-01 19:57 EST. Ran `python research/extend_paper_trading_state.py`: clock gate released but `next expected session 2026-11-02 (Monday) not closed yet` → `sessions extended: 0`, NAV unchanged (133019.54382525434), last_run_date 2026-10-30. `python research/drift_persistence_report.py` shows `stored == recomputed: True` (rolling 63d Sharpe -0.7689729823169228 at 2026-10-30, provenance git_sha 6a53815e6d1771939db4ae5bab958433df7e7f45). `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q` passed 39/39 in 3.49s. `git status --porcelain data/ config/` empty.

Supervisor recommendation 0002 (`41360230625-attempt-1-review-0002-747242e74448`) disposition `verified` — pandas 3.1.0 already installed; premise (ModuleNotFoundError) stale/incorrect; steady state awaiting next completed session.

## Objective
Execute at or after 17:00 ET on 2026-11-02 (2026-11-02T22:00 UTC): run `python research/extend_paper_trading_state.py` to extend paper-trading state by at most one session if 2026-11-02 has closed. Record exact commands and outputs. If still not closed, wait until after 17:00 ET and re-check (next candidate could be 2026-11-03).

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
