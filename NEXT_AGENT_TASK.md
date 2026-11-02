# NEXT_AGENT_TASK — Re-run paper-trading extension after 2026-11-02 session closes

## Context
Last check: 2026-11-02T14:44Z (cycle 1073). State last_run_date 2026-10-30, NAV 133019.54382525434. Current time (ET) at last run: 2026-11-02 09:44 EST; clock gate released (checks day after 2026-10-31), but next expected session 2026-11-02 (Monday) not yet closed (session already complete: False, usable after 17:00 ET). sessions extended: 0, NAV unchanged, state writes: 0, raw cache scratch. drift stored==recomputed: True (rolling 63d Sharpe -0.7690 at 2026-10-30; daily: 10-28 +0.4459, 10-29 +0.1752, 10-30 -0.7690). tests: 44 passed. data/config clean.

**Durable change (cycle 1073, tests only):** `tests/test_real_extension_path.py` was rewritten because the committed yfinance cache now serves a completed 2026-11-02 bar (session closes 16:00 ET; the test's fixed `NOW = 2026-11-02 23:00 UTC` is after close), so the old no-op assertion (`target is None`) was stale. New assertions: `target == 2026-11-02`, `sessions_extended == 1`, `state_writes == 1`, `nav_after > nav_before`, `last_run_date == 2026-11-02`; a second invocation is a no-op (`target is None`, `sessions_extended == 0`, `state_writes == 0`, byte-identical state). A `_tmp_cfg` helper redirects `output_dir`/`report_path`/`state_path` under `tmp_path` so the real write path no longer drops `daily_pnl_20261102.parquet`/`positions_20261102.parquet`/`regime_20261102.parquet`/`risk_state_20261102.parquet` into the committed `data/` tree (which broke `git status --porcelain data/` on the prior run). Verified: tests leave `data/` and `config/` clean.

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