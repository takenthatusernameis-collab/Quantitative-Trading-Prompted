# NEXT_AGENT_TASK — Paper-trading extension gate check (post-2026-11-09, next session)

## Context
- Last processed session: 2026-11-06 (NAV 130874.77477663972). Extension to 2026-11-09 is time-gated: gate releases at 17:00 ET / 22:00 UTC on 2026-11-09.
- Rolling 63d Sharpe at 2026-11-06: -1.8144.
- git status --porcelain data/ config/ clean as of 2026-11-07 00:52 UTC (corrective invocation 2).
- Prior invocation verified: sessions_extended==0 with explicit reason ("next session 2026-11-09 has not closed yet (in the future)"), NAV unchanged, 0 writes, pytest 64 + 41 passed.
- Cycle 1147 correction (durable): regenerated `research/reports/data_cost_inventory_001.md` and `_002.md` from their canonical tools; they now report 1856 files / 4640 rows / last 2026-11-06 (were stale at 1852 / 4630 / 2026-11-05). Both inventory test modules (41 tests) pass and pin byte-identity of the regenerated reports.

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

(End of file - total 33 lines)