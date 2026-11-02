# NEXT_AGENT_TASK — Re-run paper-trading extension after 2026-11-03 session closes

## Context
Last check: 2026-11-02T23:56 UTC. State at 2026-11-02 (last_run_date: 2026-11-02, NAV 132606.795692673). Current run: clock gate NOT released (day after last_run_date 2026-11-03 has not started), candidate available: no (session not closed yet). All tests pass (44 passed). git status data/config empty. drift_persistence_report shows rolling 63d Sharpe -1.3784 at 2026-11-02 with persistence 4 days.

## Objective
Re-run `python3 research/extend_paper_trading_state.py` after the 2026-11-03 (Tuesday) session closes (~17:00 ET / ~22:00 UTC). Extend by at most one session to 2026-11-03 if completed bar exists.

## Acceptance criteria
- `python3 research/extend_paper_trading_state.py` exits 0
- If completed session exists beyond 2026-11-02: sessions extended: 1 and last_run_date advances to 2026-11-03
- If no completed bar: sessions extended: 0, state unchanged (document reason)
- `python3 research/drift_persistence_report.py` -> stored == recomputed: True
- `python3 -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q` passes
- `git status --porcelain data/ config/` empty

## Validation commands
```bash
python3 research/extend_paper_trading_state.py 2>&1 | tail -30
python3 research/drift_persistence_report.py 2>&1 | tail -3
python3 -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q
git status --porcelain data/ config/
```

## Scope boundaries
- Do not change thresholds/gates, cost model, universe, or clock-gate logic
- Do not commit unless explicitly asked
- Do not modify `data/raw/`
- Do not revert pre-existing `data/processed/paper_trading_state.yaml` modification (legitimate state progression from prior session)
