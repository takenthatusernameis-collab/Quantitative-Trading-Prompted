# NEXT_AGENT_TASK — Paper-trading extension gate check (post-2026-11-09, next session)

## Context
- Last processed session: 2026-11-06, NAV 130874.77477663972 (data/processed/paper_trading_state.yaml, SHA256 a8bb945ca24fb79133f75de9ba4e31b0205cafb50e9d71d6aa1eb451f4cd35b4).
- Rolling 63d Sharpe at 2026-11-06: -1.8144.
- git status --porcelain data/ config/ clean as of 2026-11-08 00:30 UTC (Cycle 1159, run 42422468592 attempt 1 session 6 inv 1).
- Cycle 1159 (2026-11-08 00:28–00:30 UTC, pre-gate): **NO-OP VERIFIED** per NEXT_AGENT_TASK commands 1–6. UTC 00:28:18Z / ET 19:28:18 Sat 2026-11-07. `extend_paper_trading_state.py` (x2): clock gate released for day-after check, but next expected session 2026-11-09 (Monday) candidate unavailable (future; usable after 17:00 ET 2026-11-09); `sessions extended 0`, NAV before/after `130874.77477663972`, `state write count 0`, idempotent. `drift_persistence_report.py` tail `2026-11-06 -1.8144` consistent. Core pytest (6 modules) → **64 passed, 1 warning (31.67s)**. `git status --porcelain data/ config/` empty. State SHA256 unchanged. Supervisor review 0006 disposition `verified`: `pytest tests/test_cost_admissibility_screen.py -q` → **40 passed, 4 warnings (80.91s)**; `git diff -- research/reports/cost_admissibility_screen_001.md` no changes.
- Deps present in this environment (pandas 3.1.1, numpy 2.5.4, pytest 9.2.0). Gate for 2026-11-09 **NOT released** until 17:00 ET / 22:00 UTC 2026-11-09. Do NOT extend before then.

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

(End of file - total 45 lines)