# NEXT_AGENT_TASK — Re-run paper-trading extension after 2026-11-02 session closes

## Context
Last check: 2026-11-02T12:52Z (cycle 895). State last_run_date 2026-10-30, NAV 133019.54382525434. Current time (ET): 2026-11-02 07:52 EST; clock gate released (checks day after 2026-10-31), next expected session 2026-11-02 (Monday) not yet closed (session already complete: False, candidate available: no, reason: today and still in progress). `python research/extend_paper_trading_state.py` -> exit 0, sessions extended: 0, NAV unchanged 133019.54382525434, state write count: 0, canonical data/raw untouched. `python research/drift_persistence_report.py` -> stored == recomputed: True, rolling 63d Sharpe -0.7689729823169228 at 2026-10-30 (streak 3 days: 10-28 -> 10-30). `python -m pytest ... -q` -> 44 passed. `git status --porcelain data/ config/` -> empty. Wakeup scheduled at 2026-11-02T21:53:18Z (wku_19c524154001ZNLjcDWaZM1M5g) for the post-close run.

**Prior durable change (still in effect):** the active extension write path is verified end-to-end against the committed cache. `python research/verify_monday_extension_path.py` -> RESULT: PASS, target derived from `data/raw/SPY.parquet` at run time, sessions_extended: 1, state_writes: 1, canonical state hash and data/raw byte-identical before/after. Regression coverage in `tests/test_verify_monday_extension_path.py`.

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
python research/extend_paper_trading_state.py 2>&1 | tail -25
python research/drift_persistence_report.py 2>&1 | tail -3
python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q
git status --porcelain data/ config/
```

## Scope boundaries
- Do not change thresholds/gates, cost model, universe, or clock-gate logic
- Do not commit unless explicitly asked
- Do not modify `data/raw/`