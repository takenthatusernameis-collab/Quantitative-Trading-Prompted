# NEXT_AGENT_TASK — Real paper-trading extension gate check (at/after 22:00 UTC 2026-11-10)

## Context
- **Post-gate execution 2026-11-09 22:01 UTC (corrective invocation 11 wakeup, session 2):** Gate window satisfied (>=22:00 UTC). Cmds 1–8 executed in order. State advanced **2026-11-06 → 2026-11-09** (effective +1 completed session). SHA256 now `24cd92a33d138f9c12004ddad25931a109977a68e14143395b3231ffe38f53f2`, `last_run_date: 2026-11-09`, `current_nav: 132932.12732794194`, `rolling_sharpe_63d: -1.1566354312981708`, run_history 465 entries (last 2026-11-09 return 0.015720008342428357, pnl 2057.3525513022087, turnover 0.030509531446162308). Artifacts created: `data/processed/paper_trading/{daily_pnl,positions,regime,risk_state}_20261109.parquet`. Cmd 3 drift tail includes 2026-11-09 -1.1566. Cmd 4 idempotent (0 writes). Cmd 5 **64 passed in 25.73s**. Cmd 6 only expected state + 20261109 artifacts (no `data/raw/`). Cmd 7 (state advanced): `data_cost_inventory_001.py` OVERALL PASS, `002.py` OVERALL PASS `DECISION|NO-GO|incumbent tsmomentum_spytrend_001 unchanged`; **41 passed in 67.51s**. Cmd 8 ruff **All checks passed**. Durable report: `research/reports/paper_trading_extension_gate_check_20261109T2201Z_postgate.md`.
- **Pre-gate verification 2026-11-10 00:14 UTC (prior session):** Gate not open (releases 22:00 UTC 2026-11-10). Pre-gate cmds 1,3,5,6,8 executed and **ALL PASSED**: date 2026-11-10T00:14:06Z / Mon Nov 9 19:14:06 EST; drift tail includes 2026-11-09 -1.1566; pytest 65 passed in 22.40s; git status data/config clean; ruff clean. State unchanged (SHA256 `24cd92a33d138f9c12004ddad25931a109977a68e14143395b3231ffe38f53f2`, last_run_date 2026-11-09, NAV 132932.12732794194). No 2026-11-10 artifacts exist (candidate session not closed).
- **Pre-gate verification 2026-11-10 01:08 UTC (this session):** Gate still not open (releases 22:00 UTC 2026-11-10; current ET 20:08 on Mon Nov 9). Pre-gate cmds 1,3,5,6,8 executed and **ALL PASSED**: date 2026-11-10T01:08:02Z / Mon Nov 9 20:08:02 EST; drift tail includes `2026-11-09  -1.1566` (consistent); pytest **66 passed in 24.20s**; git status data/config clean (no output); ruff **All checks passed!**. State unchanged (SHA256 `24cd92a33d138f9c12004ddad25931a109977a68e14143395b3231ffe38f53f2`, last_run_date 2026-11-09, NAV 132932.12732794194). No 2026-11-10 artifacts exist (candidate session not closed).
- Next expected session: **2026-11-10 (Tuesday)**. Clock gate for 2026-11-10 releases after **17:00 ET 2026-11-10 (22:00 UTC 2026-11-10)** or following-day-start per completeness rule.
- Tooling: `/tmp/kilo-venv/bin/python` and `/tmp/kilo-venv/bin/ruff`. If missing, `python3 -m venv /tmp/kilo-venv && /tmp/kilo-venv/bin/pip install -r requirements.txt ruff`.

## Objective
At/after 22:00 UTC on 2026-11-10, run the real extension and persistence checks. Extend by at most one session to 2026-11-10 only if a completed bar exists; otherwise record `sessions_extended==0` with explicit reason and keep state unchanged. No alpha/promotion claims.

## Acceptance criteria
- Run verification commands in order; record gate/candidate/sessions_extended/last_run_date/NAV and reason if 0.
- If a completed 2026-11-10 session exists: `sessions_extended==1`, `last_run_date` advances, NAV changes, write count 1.
- If not: `sessions_extended==0` with explicit reason, NAV unchanged, 0 writes.
- Second invocation idempotent.
- `drift_persistence_report` reports updated/consistent.
- `git status --porcelain data/ config/` shows only the expected state update.
- pytest 64 pass.
- If state advanced, re-run `research/data_cost_inventory_001.py` and `research/data_cost_inventory_002.py` and confirm the regenerated reports match the new counters (same regression class fixed in Cycle 1147); re-run `tests/test_data_cost_inventory_001.py` and `tests/test_data_cost_inventory_002.py`.
- Ruff clean on 3 extension scripts.

## Scope boundaries
- Do not change thresholds/gates/cost model/universe/clock-gate logic.
- Do not commit unless asked.
- Do not modify `data/raw/`.
- Do NOT run extend before 22:00 UTC 2026-11-10.

## Verification commands
1. `date -u && TZ=America/New_York date`
2. `/tmp/kilo-venv/bin/python research/extend_paper_trading_state.py 2>&1 | tail -25`
3. `/tmp/kilo-venv/bin/python research/drift_persistence_report.py 2>&1 | tail -8`
4. `/tmp/kilo-venv/bin/python research/extend_paper_trading_state.py 2>&1 | tail -8`
5. `/tmp/kilo-venv/bin/python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py tests/test_state_aggregate_audit.py tests/test_rolling_63d_gate_refresh.py -q`
6. `git status --porcelain data/ config/`
7. (only if state advanced) `/tmp/kilo-venv/bin/python research/data_cost_inventory_001.py && /tmp/kilo-venv/bin/python research/data_cost_inventory_002.py && /tmp/kilo-venv/bin/python -m pytest tests/test_data_cost_inventory_001.py tests/test_data_cost_inventory_002.py -q`
8. `/tmp/kilo-venv/bin/ruff check research/drift_persistence_report.py research/extend_paper_trading_state.py research/verify_monday_extension_path.py`