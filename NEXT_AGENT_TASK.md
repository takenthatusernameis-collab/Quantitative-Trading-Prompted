# NEXT_AGENT_TASK — Paper-trading extension gate check (post-2026-11-09, next session)

## Context
- Last processed session: 2026-11-06, NAV 130874.77477663972 (data/processed/paper_trading_state.yaml, SHA256 a8bb945ca24fb79133f75de9ba4e31b0205cafb50e9d71d6aa1eb451f4cd35b4).
- Rolling 63d Sharpe at 2026-11-06: -1.8144.
- git status --porcelain data/ config/ clean as of 2026-11-07 05:23 UTC (invocation 1148).
- Invocation 1148 (2026-11-07 05:21–05:23 UTC): fixed a deterministic environment blocker (system Python 3.14.4 had only PyYAML; installed pandas 3.1.1, numpy 2.5.4, pytest 9.2.0, yfinance 1.8.0, arch 8.0.0, statsmodels 0.15.0, scipy 1.18.1, pyarrow 26.0.1, python-dotenv). Ran the full acceptance sequence: extend → gate NOT released (next session 2026-11-09, not closed), sessions_extended 0, NAV unchanged, 0 writes; drift report consistent (2026-11-06 -1.8144); idempotent second run; **pytest 64 passed in 28.69s**; git status data/ config/ clean. No code/data/config/gate/cost/universe/threshold/raw changes.
- Supervisor recommendation 42326826034-attempt-1-review-0002-bfbd92bab48e (cycle 0002): accepted and verified — missing optional deps were the root cause of the collection abort; now resolved environment-only.
- Extension to 2026-11-09 is time-gated: gate releases at 17:00 ET / 22:00 UTC on 2026-11-09.

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