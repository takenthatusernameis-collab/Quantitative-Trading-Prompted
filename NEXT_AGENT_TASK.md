# NEXT_AGENT_TASK — Re-check paper-trading extension after 17:00 ET on 2026-11-02

## Context
Session UTC 2026-11-01T20:59:03Z ran `python research/extend_paper_trading_state.py` early: `sessions extended: 0` because candidate session 2026-11-02 has not closed yet. `last_run_date` remains 2026-10-30 (460 cumulative sessions), NAV 133019.54382525434, rolling 63d Sharpe -0.7689729823169228. Drift report `stored == recomputed: True`. Tests 39 passed. `git status --porcelain data/ config/` empty. Gate release time: 17:00 ET on 2026-11-02 = 21:00 UTC on 2026-11-02.

## Objective
Run `python research/extend_paper_trading_state.py` at or after 17:00 ET on 2026-11-02 to extend paper-trading state by one session if available. Record exact commands and outputs.

## Acceptance criteria
- `python research/extend_paper_trading_state.py` exits 0
- If completed 2026-11-02 bar exists: `sessions extended: 1`, `last_run_date` becomes `2026-11-02`, NAV updates, `python research/drift_persistence_report.py` shows `stored == recomputed: True`
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
