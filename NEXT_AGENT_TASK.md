# NEXT_AGENT_TASK — Re-run paper-trading extension after 2026-11-02 session closes

## Context
Last check: 2026-11-02T20:49 UTC (15:49 ET). State last_run_date 2026-10-30, NAV 133019.54382525434. Session 2026-11-02 is in progress (not closed yet; closes ~17:00 ET). `python3 research/extend_paper_trading_state.py` exited 0 with no extension (sessions extended: 0) because candidate not available. `python3 research/drift_persistence_report.py` would need to be checked; tests for extension path all passed previously (44 passed). Git status clean.

Blocker: 2026-11-02 session not closed yet. Re-run required after ~17:00 ET / ~22:00 UTC on 2026-11-02.

## Objective
Re-run `python research/extend_paper_trading_state.py` after the 2026-11-02 (Monday) session closes (~17:00 ET / ~22:00 UTC). Extend by at most one session to 2026-11-02 if completed bar exists.

## Acceptance criteria
- `python research/extend_paper_trading_state.py` exits 0
- If completed session exists beyond 2026-10-30: sessions extended: 1 and last_run_date advances to 2026-11-02
- If no completed bar: sessions extended: 0, state unchanged (document reason)
- `python research/drift_persistence_report.py` -> stored == recomputed: True
- `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q` passes
- `git status --porcelain data/ config/` empty

## Validation commands
```bash
python research/extend_paper_trading_state.py 2>&1 | tail -30
python research/drift_persistence_report.py 2>&1 | tail -3
python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q
git status --porcelain data/ config/
```

## Scope boundaries
- Do not change thresholds/gates, cost model, universe, or clock-gate logic
- Do not commit unless explicitly asked
- Do not modify `data/raw/`
