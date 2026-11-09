# NEXT_AGENT_TASK — Real paper-trading extension gate check (at/after 22:00 UTC 2026-11-09)

## Context
- State: `data/processed/paper_trading_state.yaml`, SHA256 `a8bb945ca24fb79133f75de9ba4e31b0205cafb50e9d71d6aa1eb451f4cd35b4`, `last_run_date: 2026-11-06`, NAV `130874.77477663972`.
- Rolling 63d Sharpe at 2026-11-06: `-1.8144`.
- `git status --porcelain data/ config/`: clean.
- **Pre-gate verification 2026-11-09 10:05 UTC (Cycle 1184, run 42552418103 attempt 1 session 23 inv 1):** `date -u` = Mon Nov 9 10:05:16 UTC 2026 / Mon Nov 9 05:05:16 EST 2026. Gate NOT released (candidate 2026-11-09 not closed — session still in progress). Per scope boundary #29, cmds 2/4/7 **NOT run**. `drift_persistence_report.py` tail `2026-11-06 -1.8144` consistent; pytest 6 modules → **64 passed in 26.63s**; `git status --porcelain data/ config/` clean; `ruff check` on 3 extension modules → **All checks passed!** (`/tmp/kilo-venv` present). Real extension deferred until >= 22:00 UTC 2026-11-09.
- **Forward-path verification 2026-11-09 07:59 UTC (Cycle 320):** `research/verify_gate_time_forward_bar.py` → `RESULT: PASS` (target `2026-11-09`, `sessions_extended: 1`, `state_writes: 1`, NAV changed, canonical state hash unchanged, tracked report hash unchanged). `pytest tests/test_verify_gate_time_forward_bar.py tests/test_live_extension_path.py -v` → **3 passed in 15.46s**. The production extension path is verified correct and side-effect-free at the real clock and against a synthetic forward bar. The only remaining blocker is the time gate.
- **Scheduling:** wakeup `wku_1bf7e2bcc001p02dsC1BL9RP1D` due 2026-11-09T22:07:59Z carries the gate-check prompt. If the session resumes before then (e.g. controller heartbeat), re-check `date -u` and only run cmds 2/4/7 if `>= 22:00 UTC`.
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

(End of file - total 41 lines)