# NEXT_AGENT_TASK — Re-run paper-trading extension after 2026-11-02 session closes

## Context
Last check: 2026-11-02T06:55 UTC (2026-11-02 01:55 EST). State last_run_date 2026-10-30, NAV 133019.54382525434.
Session 2026-11-02 not yet closed; no completed bar. sessions extended: 0, state unchanged.
drift persistence: stored == recomputed True; 39 tests passed; git status data/config empty.
- `python research/extend_paper_trading_state.py` -> exit 0; `session already complete: False`; `candidate available: no` (reason: next session 2026-11-02 has not closed yet); `sessions extended: 0`; NAV unchanged; state write count: 0; canonical data/raw untouched.
- `python research/drift_persistence_report.py` -> `stored == recomputed: True`; stored flag -0.7689729823169228 (2026-10-30); provenance block present (`git_sha be459c7f2641d27f320df79b257abc6c211bda97`).
- `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q` -> 39 passed in 2.58s.
- `git status --porcelain data/ config/` -> empty.

## Objective
Re-run `python research/extend_paper_trading_state.py` after the 2026-11-02 (Monday) session closes (~17:00 ET / ~22:00 UTC on 2026-11-02). Extend by at most one session to 2026-11-02 if completed bar exists.

## Acceptance criteria
- `python research/extend_paper_trading_state.py` exits 0
- If completed session exists beyond 2026-10-30: sessions extended: 1 and last_run_date advances
- If no completed bar: sessions extended: 0, state unchanged (document reason)
- `python research/drift_persistence_report.py` -> stored == recomputed: True
- `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q` passes
- `git status --porcelain data/ config/` empty

## Validation commands
```bash
python research/extend_paper_trading_state.py 2>&1 | tail -25
python research/drift_persistence_report.py 2>&1 | tail -3
python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q
git status --porcelain data/ config/
```

## Scope boundaries
- Do not change thresholds/gates, cost model, universe, or clock-gate logic
- Do not commit unless explicitly asked
- Do not modify `data/raw/`