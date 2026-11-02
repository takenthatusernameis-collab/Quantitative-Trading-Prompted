# NEXT_AGENT_TASK — Re-run paper-trading extension after 2026-11-03 session closes

## Context
Last check: 2026-11-02T22:55 UTC (17:55 ET, cycle 1077). State last_run_date 2026-11-02, NAV 132606.795692673. Clock gate: NOT released (gate checks day after: 2026-11-03 — calendar day after last_run_date hasn't started). Next expected session: 2026-11-03 (Tuesday), usable after 17:00 ET on 2026-11-03 (~22:00 UTC). session already complete: False, candidate available: no. drift stored==recomputed: True, rolling 63d Sharpe -1.3784 at 2026-11-02. tests: 44 passed. Extension run this cycle: sessions extended: 0, state unchanged (gate not released), script exit 0.

## Objective
Re-run `python3 research/extend_paper_trading_state.py` after the 2026-11-03 (Tuesday) session closes (~17:00 ET / ~22:00 UTC). Extend by at most one session to 2026-11-03 if completed bar exists.

## Acceptance criteria
- `python3 research/extend_paper_trading_state.py` exits 0
- If completed session exists beyond 2026-11-02: sessions extended: 1 and last_run_date advances to 2026-11-03
- If no completed bar: sessions extended: 0, state unchanged (document reason)
- `python3 research/drift_persistence_report.py` -> stored == recomputed: True
- `python3 -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q` passes
- `git status --porcelain data/ config/` empty (note: data/processed/paper_trading_state.yaml is pre-existing modified from prior session's extension; not caused by this session)

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
