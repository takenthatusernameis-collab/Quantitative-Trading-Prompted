# Next Agent Task — Extend and verify paper trading state

## Context
- Last processed session: `2026-10-23` in `data/processed/paper_trading_state.yaml`
- Gate not yet released at check time (current ~2026-10-24 04:35 ET); next usable session is `2026-10-26` (Monday) after gate release at/after 17:00 ET (or when day-after rule holds).
- Validation report written: `research/reports/paper_trading_validation_post_extend_20261024.md`

## Objective
When `research/extend_paper_trading_state.py` indicates gate is released and a new completed session is available, extend the paper trading state by >=1 session. If still not released, wait for gate conditions or report readiness unchanged (do not fabricate sessions).

## Acceptance criteria
1. Check latest session: `python3 -c "import yaml; d=yaml.safe_load(open('data/processed/paper_trading_state.yaml')); print(d['run_history'][-1]['date'])"`
2. If latest > `2026-10-23`:
   - Run `python research/extend_paper_trading_state.py` (or ensure extension applied). State must show new sessions extended.
   - Run `python research/drift_persistence_report.py` -> must show `stored == recomputed: True`
   - Run `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q` -> all pass
   - `git status --porcelain data/` should be empty or only intentional committed changes
   - Write `research/reports/paper_trading_validation_post_extend_<YYYYMMDD>.md` with UTC timestamp, old/new latest dates, NAV change, rolling 63d Sharpe (if available), drift status, and verification commands/results
3. If latest == `2026-10-23` and gate still NOT released: report "not yet extended; awaiting gate" with readiness from `python research/extend_paper_trading_state.py`; no data changes.

## Validation commands
```bash
python3 -c "import yaml; d=yaml.safe_load(open('data/processed/paper_trading_state.yaml')); print(d['run_history'][-1]['date'])"
python research/extend_paper_trading_state.py
python research/drift_persistence_report.py | tail -5
python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q
git status --porcelain data/
```

## Scope boundaries
- No strategy/gate/threshold/config changes. Do not commit unless explicitly requested. Raw cache untouched. Research/backtesting only. Never fabricate sessions.
