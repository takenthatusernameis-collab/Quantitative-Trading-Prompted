# NEXT_AGENT_TASK — extend paper-trading state to next completed session

## Context
`data/processed/paper_trading_state.yaml` now has `last_run_date: 2026-10-27` (455+1=456 sessions). The extension tool ran successfully and updated state/report. Next trading session after 2026-10-27 is 2026-10-28 (Wed); it's closed as of current time (ET), so a candidate exists.

## Objective
Run `python research/extend_paper_trading_state.py` (no --dry-run), record output, run drift report and tests, and if extended update status files as needed.

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
