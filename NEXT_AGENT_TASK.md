# NEXT_AGENT_TASK — Paper-trading extension gate check (post-2026-11-09, next session)

## Context
- Last processed session: 2026-11-06, NAV 130874.77477663972 (data/processed/paper_trading_state.yaml, SHA256 a8bb945ca24fb79133f75de9ba4e31b0205cafb50e9d71d6aa1eb451f4cd35b4).
- Rolling 63d Sharpe at 2026-11-06: -1.8144.
- git status --porcelain data/ config/ clean as of 2026-11-07 06:30 UTC (corrective invocation 1152) and re-verified clean at 2026-11-07 09:27 UTC (session 17, invocation 1).
- Corrective invocation 1152 (2026-11-07 06:30 UTC, Sat 01:30 EST): gate for 2026-11-09 **NOT released** (releases 17:00 ET / 22:00 UTC 2026-11-09). `python3 research/extend_paper_trading_state.py` → gate NOT released, next expected session 2026-11-09 (Monday), candidate unavailable (future), `sessions_extended 0`, NAV unchanged `130874.77477663972`, `state write count 0`, raw cache scratch. State SHA256 unchanged `a8bb945ca24fb79133f75de9ba4e31b0205cafb50e9d71d6aa1eb451f4cd35b4`. `pytest` core 6 modules → **64 passed, 1 warning in 28.11s**. No writes to `data/` or `config/`; `data/raw/` untouched; no code/threshold/gate/cost/universe/clock-gate changes. Durable evidence: `CORRECTIVE_HANDOFF_INVOCATION_1152.md`.
- Fresh pre-gate verification (2026-11-07 09:27 UTC, Sat 04:27 EST, session 17 invocation 1): gate NOT released (22:00 UTC 2026-11-09), `sessions_extended 0` with explicit reason ("next session 2026-11-09 has not closed yet (in the future)"), NAV unchanged `130874.77477663972`, `state write count 0`, second invocation idempotent, drift report tail `2026-11-06 -1.8144` consistent, `git status --porcelain data/ config/` clean, state SHA256 `a8bb945ca24fb79133f75de9ba4e31b0205cafb50e9d71d6aa1eb451f4cd35b4` unchanged. `pytest` core 6 modules → **64 passed, 1 warning in 28.33s**. Durable evidence: `.kilo-runtime/worker-disposition.json` (disposition `verified` for supervisor review 0003), `CORRECTIVE_HANDOFF_INVOCATION_1152.md`.
- Session 8 invocation 1 (2026-11-07 13:17 UTC): gate NOT released; `sessions_extended 0`; NAV unchanged `130874.77477663972`; state write count 0; idempotent second invocation; drift report tail `2026-11-06 -1.8144`; `git status --porcelain data/ config/` clean; pytest 64 passed, 1 warning in 19.60s.
- Session 10 invocation 1 (2026-11-07 13:37 UTC, Sat 08:37 EST): gate NOT released (releases 22:00 UTC 2026-11-09); `extend_paper_trading_state.py` (x2) → `sessions_extended 0`, candidate unavailable (future), NAV unchanged `130874.77477663972`, `state write count 0`, idempotent. Drift tail `2026-11-06 -1.8144` consistent. State SHA256 `a8bb945ca24fb79133f75de9ba4e31b0205cafb50e9d71d6aa1eb451f4cd35b4` unchanged. `git status --porcelain data/ config/` clean. Core pytest 6 modules → **64 passed, 1 warning in 20.13s**. Supervisor review 0009 disposition `verified` (`.kilo-runtime/worker-disposition.json`). No writes to `data/`/`config/`; `data/raw/` untouched; no threshold/gate/cost/universe/clock-gate changes.
- Session 12 invocation 1 (2026-11-07 13:40 UTC, Sat 08:40 EST): gate NOT released (releases 22:00 UTC 2026-11-09). Verified state SHA256 `a8bb945ca24fb79133f75de9ba4e31b0205cafb50e9d71d6aa1eb451f4cd35b4`, `last_run_date 2026-11-06`, NAV `130874.77477663972`; `git status --porcelain data/ config/` clean. Did **not** run `extend_paper_trading_state.py` (pre-gate; scope prohibits). Supervisor review 0009 disposition `verified`. No writes to `data/`/`config/`; `data/raw/` untouched.
- Prior invocations 1145–1151 also verified pre-gate no-op; deps present in this environment.

## Objective
At/after 22:00 UTC on 2026-11-09, run the real extension and persistence checks. Extend by at most one session to 2026-11-09 only if a completed bar exists; otherwise record sessions_extended==0 with explicit reason and keep state unchanged.

## Acceptance criteria
- Run verification commands in order; record gate/candidate/sessions_extended/last_run_date/NAV and reason if 0.
- If completed 2026-11-09 session exists: sessions_extended==1, last_run_date advances, NAV changes, write count 1.
- If not: sessions_extended==0 with explicit reason, NAV unchanged, 0 writes.
- Second invocation idempotent.
- drift_persistence_report reports updated/consistent.
- git status --porcelain data/ config/ shows only expected state update.
- pytest 64 pass.
- If state advanced, re-run `research/data_cost_inventory_001.py` and `research/data_cost_inventory_002.py` and confirm the regenerated reports match the new counters (same regression class fixed in Cycle 1147); re-run `tests/test_data_cost_inventory_001.py` and `tests/test_data_cost_inventory_002.py`.

## Scope boundaries
- Do not change thresholds/gates/cost model/universe/clock-gate logic.
- Do not commit unless asked.
- Do not modify data/raw/.
- Do NOT run extend before 22:00 UTC 2026-11-09.

## Verification commands
1. date -u && TZ=America/New_York date
2. python3 research/extend_paper_trading_state.py 2>&1 | tail -25
3. python3 research/drift_persistence_report.py 2>&1 | tail -6
4. python3 research/extend_paper_trading_state.py 2>&1 | tail -8
5. python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py tests/test_state_aggregate_audit.py tests/test_rolling_63d_gate_refresh.py -q
6. git status --porcelain data/ config/
7. (only if state advanced) python3 research/data_cost_inventory_001.py && python3 research/data_cost_inventory_002.py && python -m pytest tests/test_data_cost_inventory_001.py tests/test_data_cost_inventory_002.py -q

(End of file - total 38 lines)