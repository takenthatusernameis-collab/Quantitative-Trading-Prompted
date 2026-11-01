# NEXT_AGENT_TASK — extend paper-trading state to next completed session

## Context
`data/processed/paper_trading_state.yaml` now has `last_run_date: 2026-10-29`
(457+2=459 sessions). Two extensions ran successfully this session:
- 2026-10-28 (NAV 134964.32 -> 135651.64)
- 2026-10-29 (NAV 135651.64 -> 135161.06)

The clock gate is released and the next candidate session after 2026-10-29 is
2026-10-30 (Friday); it is closed as of current time (ET), so a candidate exists.

## Objective
Run `python research/extend_paper_trading_state.py` (no --dry-run), record output,
run drift report and tests, and if extended update status files as needed.

## Acceptance criteria
- `git status --porcelain data/ config/` empty unless a legitimate state extension occurred
- Extension output recorded (sessions extended count, NAV before/after)
- `python research/drift_persistence_report.py` passes (stored == recomputed)
- `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q` passes

## Validation commands
```bash
python research/extend_paper_trading_state.py
python research/drift_persistence_report.py
python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q
git status --porcelain
```

## Scope boundaries
- Do not modify data/, config/, tests/, src/ except via the extension tool's normal state write
- Do not change gates, thresholds, or strategy parameters

## Evidence from this session
- Supervisor claim of `union_sessions=6100 vs frozen 6098` (6 failures in
  `tests/test_leadlag_001_evaluation.py`) is **not reproducible**. Read-only
  diagnostic via `research.leadlag_001_evaluation.load_closes`/`FROZEN` printed
  current union_sessions=6098, panel=2960, delta +0. Baseline pytest (extension
  changes stashed) ran `28 passed, 2 skipped, 0 failures`. The only post-extension
  failure is `test_git_reports_no_change_under_data_or_config`, which fails solely
  because the extension legitimately modified `data/processed/paper_trading_state.yaml`
  (it is a git-cleanliness guard, not a data inconsistency). Disposition recorded as
  `rejected_with_reason` in `.kilo-runtime/worker-disposition.json`.
- Prior environment blocker: `pandas`/`yfinance` were not installed in the default
  `python`. Resolved with `pip install -r requirements.txt` (session-local, not committed).