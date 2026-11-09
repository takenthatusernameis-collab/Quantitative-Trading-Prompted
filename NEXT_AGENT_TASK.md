# NEXT_AGENT_TASK — Real paper-trading extension gate check (at/after 22:00 UTC 2026-11-09)

## Context
- State: `data/processed/paper_trading_state.yaml`, SHA256 `a8bb945ca24fb79133f75de9ba4e31b0205cafb50e9d71d6aa1eb451f4cd35b4`, `last_run_date: 2026-11-06`, NAV `130874.77477663972`.
- Rolling 63d Sharpe at 2026-11-06: `-1.8144`.
- `git status --porcelain data/ config/`: clean as of 2026-11-09 04:07 UTC (this pre-gate verification).
- **Pre-gate verification 2026-11-09 04:07 UTC:** `date -u` = Mon Nov 9 04:07:12 UTC 2026 / Sun Nov 8 23:07:12 EST. `extend_paper_trading_state.py`: clock gate released, next expected session 2026-11-09 (Monday), candidate available **no** (2026-11-09 not closed yet — future, no completed candidate bar), `sessions extended: 0`, NAV `130874.77477663972` before/after, `state write count: 0`, idempotent on re-run; `drift_persistence_report.py` tail `2026-11-06 -1.8144` consistent; pytest 6 modules → **64 passed**; `git status --porcelain data/ config/` clean; `ruff check` on 3 extension modules → **All checks passed!**. Real extension deferred until >= 22:00 UTC 2026-11-09.
- **Tooling:** `/tmp/kilo-venv/bin/python` and `/tmp/kilo-venv/bin/ruff` verified working. If missing at gate time, re-create: `python3 -m venv /tmp/kilo-venv && /tmp/kilo-venv/bin/pip install -r requirements.txt ruff`.

## Objective
At/after 22:00 UTC on 2026-11-09, run the real extension and persistence checks. Extend by at most one session to 2026-11-09 only if a completed bar exists; otherwise record `sessions_extended==0` with explicit reason and keep state unchanged.

## Acceptance criteria
- Run verification commands in order; record gate/candidate/sessions_extended/last_run_date/NAV and reason if 0.
- If a completed 2026-11-09 session exists: `sessions_extended==1`, `last_run_date` advances, NAV changes, write count 1.
- If not: `sessions_extended==0` with explicit reason, NAV unchanged, 0 writes.
- Second invocation idempotent.
- `drift_persistence_report` reports updated/consistent.
- `git status --porcelain data/ config/` shows only the expected state update.
- pytest 64 pass.
- If state advanced, re-run `research/data_cost_inventory_001.py` and `research/data_cost_inventory_002.py` and confirm the regenerated reports match the new counters (same regression class fixed in Cycle 1147); re-run `tests/test_data_cost_inventory_001.py` and `tests/test_data_cost_inventory_002.py`.

## Scope boundaries
- Do not change thresholds/gates/cost model/universe/clock-gate logic.
- Do not commit unless asked.
- Do not modify `data/raw/`.
- Do NOT run extend before 22:00 UTC 2026-11-09.

## Verification commands
1. `date -u && TZ=America/New_York date`
2. `/tmp/kilo-venv/bin/python research/extend_paper_trading_state.py 2>&1 | tail -25`
3. `/tmp/kilo-venv/bin/python research/drift_persistence_report.py 2>&1 | tail -6`
4. `/tmp/kilo-venv/bin/python research/extend_paper_trading_state.py 2>&1 | tail -8`
5. `/tmp/kilo-venv/bin/python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py tests/test_state_aggregate_audit.py tests/test_rolling_63d_gate_refresh.py -q`
6. `git status --porcelain data/ config/`
7. (only if state advanced) `/tmp/kilo-venv/bin/python research/data_cost_inventory_001.py && /tmp/kilo-venv/bin/python research/data_cost_inventory_002.py && /tmp/kilo-venv/bin/python -m pytest tests/test_data_cost_inventory_001.py tests/test_data_cost_inventory_002.py -q`
8. `/tmp/kilo-venv/bin/ruff check research/drift_persistence_report.py research/extend_paper_trading_state.py research/verify_monday_extension_path.py`