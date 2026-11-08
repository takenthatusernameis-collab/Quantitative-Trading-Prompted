# NEXT_AGENT_TASK — Real paper-trading extension gate check (at/after 22:00 UTC 2026-11-09)

## Context
- State: `data/processed/paper_trading_state.yaml`, SHA256 `a8bb945ca24fb79133f75de9ba4e31b0205cafb50e9d71d6aa1eb451f4cd35b4`, `last_run_date: 2026-11-06`, NAV `130874.77477663972`.
- Rolling 63d Sharpe at 2026-11-06: `-1.8144`.
- `git status --porcelain data/ config/`: clean as of 2026-11-08 14:08 UTC (this session).
- **No-op path already verified this session (2026-11-08 14:06–14:08 UTC):** `extend_paper_trading_state.py` reported `clock gate: released`, `next expected session: 2026-11-09 (Monday)`, `candidate available: no` (reason: next session 2026-11-09 has not closed yet — in the future, today is 2026-11-08), `sessions extended: 0`, NAV before/after `130874.77477663972`, `state write count: 0`, raw cache scratch. `drift_persistence_report.py` tail `2026-11-06 -1.8144` consistent.
- **Gate check 2026-11-08 14:12 UTC:** `date -u` = Sun Nov 8 14:12:49 UTC 2026; gate NOT released (need >= 2026-11-09 22:00 UTC). Extend NOT run per scope. pytest 64 pass; ruff clean.
- **Reproducibility gap (pre-existing, not a defect):** `paper_trading_cache_reproducibility_audit.py --strict` → state frontier `2026-11-06`, cache frontier `2026-11-05`, missing from cache: 1 (`2026-11-06`), `reproducible from committed cache: NO`. The trailing session was produced by a live scratch-dir fetch that never refreshed `data/raw`. The extension tool re-fetches live data, so this does not block the extension; `data/raw` remains untouched.
- Deps present in this environment (pandas 3.1.1, numpy 2.5.4, pytest 9.2.0). The gate for 2026-11-09 is **NOT released** until 17:00 ET / 22:00 UTC 2026-11-09, and the candidate session is only usable once it is itself complete. Do NOT extend before then.

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
2. `python3 research/extend_paper_trading_state.py 2>&1 | tail -25`
3. `python3 research/drift_persistence_report.py 2>&1 | tail -6`
4. `python3 research/extend_paper_trading_state.py 2>&1 | tail -8`
5. `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py tests/test_state_aggregate_audit.py tests/test_rolling_63d_gate_refresh.py -q`
6. `git status --porcelain data/ config/`
7. (only if state advanced) `python3 research/data_cost_inventory_001.py && python3 research/data_cost_inventory_002.py && python -m pytest tests/test_data_cost_inventory_001.py tests/test_data_cost_inventory_002.py -q`
8. `python -m ruff check research/drift_persistence_report.py research/extend_paper_trading_state.py research/verify_monday_extension_path.py`