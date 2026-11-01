# NEXT_AGENT_TASK — Extend paper-trading state when 2026-11-02 (or later) session completes

## Context
Session UTC 2026-11-01T19:12Z verified current state. `last_run_date` is 2026-10-30 (460 cumulative sessions), NAV 133019.54382525434, rolling 63d Sharpe -0.7689729823169228. `python research/extend_paper_trading_state.py` exits 0 with `sessions extended: 0` because 2026-11-02 bar not yet complete (clock-gated). Drift report `stored == recomputed: True`. Tests 39 passed for paper trading/drift tests. Working tree clean. Supervisor recommendation 0005 verified; no code action required.

Gate release time: 17:00 ET on 2026-11-02 = 21:00 UTC on 2026-11-02. Current time is 2026-11-01 14:10 ET — the gate is released but the next candidate session has not closed yet.

## Objective
Run `python research/extend_paper_trading_state.py` at or after 17:00 ET on 2026-11-02 (or next local trading day when a completed session bar exists) to extend paper-trading state by one session if available. Record exact commands and outputs.

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

## Notes
- Time-gated blocker, not a code defect. Do not force extension before session complete.
- `research/reports/paper_trading_rolling.md` has unstaged git_sha update; leave as-is if only generated metadata.