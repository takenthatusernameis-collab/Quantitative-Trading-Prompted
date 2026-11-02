# NEXT_AGENT_TASK — Re-run paper-trading extension after 2026-11-02 session closes

## Context
Current time: 2026-11-02T04:13Z UTC (Sunday 2026-11-01 23:13 ET).
Last processed: 2026-10-30, NAV: 133019.54382525434 (unchanged).
Re-ran `python research/extend_paper_trading_state.py` at 04:12Z: exit 0, `clock gate: released`, `gate checks day after: 2026-10-31`, but `session already complete: False`, `candidate available: no`, `sessions extended: 0`. Reason: next session 2026-11-02 has not closed yet (today is still 2026-11-01 in ET; market opens 09:30 ET / 14:30 UTC, closes 16:00 ET / 21:00 UTC Monday 2026-11-02); no completed candidate bar exists to extend into.
Drift/persistence: `python research/drift_persistence_report.py` -> `stored == recomputed: True` (rolling 63d Sharpe -0.7689729823169228 at 2026-10-30, persistence 3 days 2026-10-28 -> 2026-10-30).
Tests: `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q` -> 39 passed in 3.42s.
Working tree clean for `data/ config/` (`git status --porcelain data/ config/` empty).
Supervisor recommendation 0033 disposition `verified` (re-written with fresh evidence): wakeup at 2026-11-02T22:05:00Z scheduled instead of a blocking shell sleep (shell has 120s cap); gate release alone is not sufficient — a completed candidate bar is also required.

## Objective
Re-run `python research/extend_paper_trading_state.py` after the 2026-11-02 (Monday) session closes (~17:00 ET / 22:00 UTC; wakeup scheduled at 22:05 UTC). If a completed bar now exists beyond last_run_date (2026-10-30), extend by at most one session; `sessions extended: 1` and `last_run_date` advances to 2026-11-02. If still not closed, check again later or note next candidate is 2026-11-03.

## Acceptance criteria
- `python research/extend_paper_trading_state.py` exits 0
- If a completed session exists beyond last_run_date (2026-10-30): extend by at most one session; `sessions extended: 1` and `last_run_date` advances
- If no completed bar available: `sessions extended: 0`, state unchanged, NAV unchanged (document reason)
- `python research/drift_persistence_report.py` -> `stored == recomputed: True`
- `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q` passes
- `git status --porcelain data/ config/` empty

## Validation commands
```bash
python research/extend_paper_trading_state.py 2>/dev/null
python research/drift_persistence_report.py 2>/dev/null
python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q
git status --porcelain data/ config/
```

## Scope boundaries
- Do not change thresholds/gates, cost model, universe, or clock-gate logic
- Do not commit unless explicitly asked
- Do not modify `data/raw/`
