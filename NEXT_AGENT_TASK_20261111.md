# NEXT_AGENT_TASK — Real paper-trading extension gate check (at/after 22:00 UTC 2026-11-11)

## Context
- **Pre-gate verification 2026-11-10 06:20 UTC (session 11, this session):** Gate for 2026-11-10 not open (releases 22:00 UTC 2026-11-10; current ET 01:20 Tue Nov 10). Pre-gate cmds 1,3,5,6,8 executed and **ALL PASSED**: date 2026-11-10T06:20:29Z / Tue Nov 10 01:20:29 EST; cmd 2 extend **NOT run** (scope boundary #37: before 22:00 UTC); drift tail includes `2026-11-09  -1.1566` (consistent); pytest **66 passed in 40.91s**; git status data/config clean (no output); ruff **All checks passed!**. State unchanged (SHA256 `24cd92a33d138f9c12004ddad25931a109977a68e14143395b3231ffe38f53f2`, last_run_date 2026-11-09, NAV 132932.12732794194, rolling_sharpe_63d -1.1566354312981708, run_history 465 entries). No 2026-11-10 artifacts exist (candidate session not closed). Supervisor: no `.kilo-runtime/current-supervisor-recommendation.json` present; disposition written as `verified` / `none-received`. Wakeup `wku_1c41eca55001kqDCHHkvqwbbA5` scheduled 2026-11-10T22:03:00Z.
- **Post-gate execution 2026-11-10 22:0X UTC (corrective invocation, session 3):** Gate window satisfied (>=22:00 UTC 2026-11-10). Cmds 1–8 executed in order. [To be filled by session 3 with exact output.]
- **Pre-gate verification 2026-11-10 03:04 UTC (session 2):** Gate not open (releases 22:00 UTC 2026-11-10). Pre-gate cmds 1,2,3,5,6,8 executed and **ALL PASSED**: date 2026-11-10T03:04:08Z / Mon Nov 9 22:04:08 EST; cmd 2 extend **no-op** (`sessions extended: 0`, `state write count: 0`, NAV before==after 132932.12732794194, candidate reason "next session 2026-11-10 has not closed yet"); drift tail includes `2026-11-09  -1.1566` (consistent); pytest **66 passed in 42.36s**; git status data/config clean (no output); ruff **All checks passed!**. State unchanged (SHA256 `24cd92a33d138f9c12004ddad25931a109977a68e14143395b3231ffe38f53f2`, last_run_date 2026-11-09, NAV 132932.12732794194). Durable report: `research/reports/paper_trading_extension_gate_check_20261110T0304Z_pregate.md`. Wakeup `wku_1c36cf0ae001MkptBEkl82jCoK` scheduled 2026-11-10T22:03:39Z.
- Next expected session: **2026-11-11 (Wednesday)**. Clock gate for 2026-11-11 releases after **17:00 ET 2026-11-11 (22:00 UTC 2026-11-11)** or following-day-start per completeness rule.
- Tooling: `/tmp/kilo-venv/bin/python` and `/tmp/kilo-venv/bin/ruff`. If missing, `python3 -m venv /tmp/kilo-venv && /tmp/kilo-venv/bin/pip install -r requirements.txt ruff`.

## Objective
At/after 22:00 UTC on 2026-11-11, run the real extension and persistence checks. Extend by at most one session to 2026-11-11 only if a completed bar exists; otherwise record `sessions_extended==0` with explicit reason and keep state unchanged. No alpha/promotion claims.

## Acceptance criteria
- Run verification commands in order; record gate/candidate/sessions_extended/last_run_date/NAV and reason if 0.
- If a completed 2026-11-11 session exists: `sessions_extended==1`, `last_run_date` advances, NAV changes, write count 1.
- If not: `sessions_extended==0` with explicit reason, NAV unchanged, 0 writes.
- Second invocation idempotent.
- `drift_persistence_report` reports updated/consistent.
- `git status --porcelain data/ config/` shows only the expected state update.
- pytest 64 pass (6-module suite).
- If state advanced, re-run `research/data_cost_inventory_001.py` and `research/data_cost_inventory_002.py` and confirm the regenerated reports match the new counters (same regression class fixed in Cycle 1147); re-run `tests/test_data_cost_inventory_001.py` and `tests/test_data_cost_inventory_002.py`.
- Ruff clean on 3 extension scripts.

## Scope boundaries
- Do not change thresholds/gates/cost model/universe/clock-gate logic.
- Do not commit unless asked.
- Do not modify `data/raw/`.
- Do NOT run extend before 22:00 UTC 2026-11-11.

## Verification commands
1. `date -u && TZ=America/New_York date`
2. `/tmp/kilo-venv/bin/python research/extend_paper_trading_state.py 2>&1 | tail -25`
3. `/tmp/kilo-venv/bin/python research/drift_persistence_report.py 2>&1 | tail -8`
4. `/tmp/kilo-venv/bin/python research/extend_paper_trading_state.py 2>&1 | tail -8`
5. `/tmp/kilo-venv/bin/python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py tests/test_state_aggregate_audit.py tests/test_rolling_63d_gate_refresh.py -q`
6. `git status --porcelain data/ config/`
7. (only if state advanced) `/tmp/kilo-venv/bin/python research/data_cost_inventory_001.py && /tmp/kilo-venv/bin/python research/data_cost_inventory_002.py && /tmp/kilo-venv/bin/python -m pytest tests/test_data_cost_inventory_001.py tests/test_data_cost_inventory_002.py -q`
8. `/tmp/kilo-venv/bin/ruff check research/drift_persistence_report.py research/extend_paper_trading_state.py research/verify_monday_extension_path.py`

(End of file - total 49 lines)