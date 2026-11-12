# NEXT_AGENT_TASK — Real paper-trading extension gate check (at/after 22:00 UTC 2026-11-13)

## Context
- **Pre-gate verification 2026-11-12 00:41 UTC (session 3 inv 1, run 43128013060 attempt 1):** Gate for 2026-11-12 **NOT released** (releases 22:00 UTC 2026-11-12; current ET 19:41 Wed Nov 11). Pre-gate cmds 1,3,5,6,8 executed fresh and **ALL PASSED**: (1) `Thu Nov 12 00:41:26 UTC 2026 / Wed Nov 11 19:41:26 EST 2026`; (3) drift tail ends `2026-11-11  -1.1049` (consistent, stored == recomputed); (5) 6 modules **68 passed in 40.37s** (`test_paper_trading_extend`, `test_drift_persistence`, `test_verify_monday_extension_path`, `test_real_extension_path`, `test_state_aggregate_audit`, `test_rolling_63d_gate_refresh`); (6) `git status --porcelain -- data/ config/ src/ tests/ research/` clean (0 lines, full `git status --porcelain` also 0 lines); (8) ruff **All checks passed!** on `research/drift_persistence_report.py`, `research/extend_paper_trading_state.py`, `research/verify_monday_extension_path.py`, `research/verify_gate_time_forward_bar.py`. State unchanged (SHA256 `5fa67d6395eb9948695e89dfa0349bfe51b15c994b6107214cca1fe9a518e227`, `last_run_date 2026-11-11`, `current_nav 133688.64116621733`, run_history **467**, `rolling_sharpe_63d: None`). No `*20261112*` artifacts in `data/processed/paper_trading/`; `data/raw/` 28 files untouched. Cmds 2,4,7 **NOT run** (scope boundary: before 22:00 UTC 2026-11-12). Wakeup `wku_1cd352c55001kftq5vvC4dFw9V` scheduled 2026-11-12T22:04:56Z for the real gate check. No commits made; `data/raw/` untouched. The 2026-11-12 post-gate log line is appended to `NEXT_AGENT_TASK.md` Context by the intervening session before this task is promoted.
- **Pre-staged by session 1 inv 1 (2026-11-12T00:35Z).** Gate for 2026-11-13 releases after **17:00 ET 2026-11-13 (22:00 UTC 2026-11-13)** or following-day-start per completeness rule.
- Tooling: `/tmp/kilo-venv/bin/python` and `/tmp/kilo-venv/bin/ruff`. If missing, `python3 -m venv /tmp/kilo-venv && /tmp/kilo-venv/bin/pip install -r requirements.txt ruff`.

## Objective
At/after 22:00 UTC on 2026-11-13, run the real extension and persistence checks. Extend by at most one session to 2026-11-13 only if a completed bar exists; otherwise record `sessions_extended==0` with explicit reason and keep state unchanged. No alpha/promotion claims.

## Acceptance criteria
- Run verification commands in order; record gate/candidate/sessions_extended/last_run_date/NAV and reason if 0.
- If a completed 2026-11-13 session exists: `sessions_extended==1`, `last_run_date` advances, NAV changes, write count 1.
- If not: `sessions_extended==0` with explicit reason, NAV unchanged, 0 writes.
- Second invocation idempotent.
- `drift_persistence_report` reports updated/consistent.
- `git status --porcelain data/ config/` shows only the expected state update.
- pytest 6-module suite passes.
- If state advanced, re-run `research/data_cost_inventory_001.py` and `research/data_cost_inventory_002.py` and confirm the regenerated reports match the new counters (same regression class fixed in Cycle 1147); re-run `tests/test_data_cost_inventory_001.py` and `tests/test_data_cost_inventory_002.py`.
- Ruff clean on 3 extension scripts.

## Scope boundaries
- Do not change thresholds/gates/cost model/universe/clock-gate logic.
- Do not commit unless asked.
- Do not modify `data/raw/`.
- Do NOT run extend before 22:00 UTC 2026-11-13.

## Verification commands
1. `date -u && TZ=America/New_York date`
2. `/tmp/kilo-venv/bin/python research/extend_paper_trading_state.py 2>&1 | tail -25`
3. `/tmp/kilo-venv/bin/python research/drift_persistence_report.py 2>&1 | tail -8`
4. `/tmp/kilo-venv/bin/python research/extend_paper_trading_state.py 2>&1 | tail -8`
5. `/tmp/kilo-venv/bin/python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py tests/test_state_aggregate_audit.py tests/test_rolling_63d_gate_refresh.py -q`
6. `git status --porcelain data/ config/`
7. (only if state advanced) `/tmp/kilo-venv/bin/python research/data_cost_inventory_001.py && /tmp/kilo-venv/bin/python research/data_cost_inventory_002.py && /tmp/kilo-venv/bin/python -m pytest tests/test_data_cost_inventory_001.py tests/test_data_cost_inventory_002.py -q`
8. `/tmp/kilo-venv/bin/ruff check research/drift_persistence_report.py research/extend_paper_trading_state.py research/verify_monday_extension_path.py`

(End of file)