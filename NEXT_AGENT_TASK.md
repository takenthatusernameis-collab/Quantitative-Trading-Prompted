# NEXT_AGENT_TASK — attempt paper-trading extension after 2026-10-26

## Context
`data/processed/paper_trading_state.yaml` has `last_run_date: 2026-10-26` and 455 sessions. Status files reconciled. Next candidate session is 2026-10-27 (Tuesday), usable after 17:00 ET.

## Objective
Run `python research/extend_paper_trading_state.py` (no --dry-run), record output, run drift report and tests, and if a session is extended, update status files accordingly.

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
