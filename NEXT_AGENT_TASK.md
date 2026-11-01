# NEXT_AGENT_TASK — Extend paper-trading state for 2026-11-02 after close

## Context
Session UTC 2026-11-01T16:05Z (EST 11:05) verified current state. `last_run_date` is 2026-10-30 (460 cumulative sessions), NAV 133019.54382525434, rolling 63d Sharpe -0.7689729823169228. The clock gate is released but 2026-11-02 (Monday) US trading session has not closed yet. Extension will only produce a new session after 17:00 ET on 2026-11-02 when a completed bar is available.

Supervisor recommendation (review-0006) disposition is `verified`: `get_provenance` is defined at `research/drift_persistence_report.py:83` and called at line 126 inside `build_report`; premise false, no code change needed.

Verification completed (Cycle 879):
- `python research/extend_paper_trading_state.py` -> exit 0, `sessions extended: 0`, NAV unchanged (133019.54382525434), no state write
- `python research/drift_persistence_report.py` -> `stored == recomputed: True`, provenance block present (git_sha 7fd0135 matches HEAD)
- `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q` -> 39 passed
- `git status --porcelain data/ config/` -> empty

## Objective
Run `python research/extend_paper_trading_state.py` at or after 17:00 ET on 2026-11-02 (or next local day when complete) to extend paper-trading state by one session if a completed 2026-11-02 bar is available. Record exact commands and outputs.

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
- `research/reports/paper_trading_rolling.md` may show modified git_sha artifact; leave as-is if only generated metadata.
