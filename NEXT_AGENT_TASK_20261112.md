# NEXT_AGENT_TASK — Real paper-trading extension gate check (at/after 22:00 UTC 2026-11-12)

## Context
- **Pre-gate verification 2026-11-11 16:27 UTC (session 17 inv 1, this session):** Gate for 2026-11-11 **NOT released** (releases 22:00 UTC 2026-11-11; current ET 11:27 Wed Nov 11). Pre-gate cmds 1,3,5,6,8 executed fresh and **ALL PASSED**: date `2026-11-11T16:27:17Z / Wed Nov 11 11:27:17 EST 2026`; drift tail ends `2026-11-10  -1.4394` (consistent); pytest 6 modules **67 passed in 27.20s**; `git status --porcelain data/ config/` clean (0 lines); `data/raw/` 28 files untouched; ruff **All checks passed!** (3 extension scripts). State unchanged (SHA256 `111b642c4ac5834460c83ac250a0a90ffb75eed308321ad1bb6309a2fc552517`, last_run_date 2026-11-10, NAV 132498.02732499802, run_history 466). No `*20261111*` artifacts in `data/processed/paper_trading/`. Supervisor rec `43005933811-attempt-1-review-0006-335b3d78d8d0` disposition `verified` in `.kilo-runtime/worker-disposition.json` (runtime). Wakeup `wku_1cb70e7c7001POiKkmRp4VszOY` scheduled 2026-11-11T22:03:00Z for the 2026-11-11 gate check. Cmds 2,4,7 withheld (before 22:00 UTC 2026-11-11). No commits made; `data/raw/` untouched.
- **Pre-gate verification 2026-11-11 05:43 UTC (session 32 inv 1, this session):** Gate for 2026-11-11 **NOT released** (releases 22:00 UTC 2026-11-11; current ET 00:43 Wed Nov 11). Pre-gate cmds 1,3,5,6,8 executed and **ALL PASSED**: date `2026-11-11T05:43:43Z / Wed Nov 11 00:43:43 EST 2026`; drift tail ends `2026-11-10  -1.4394` (consistent); pytest 6 modules **67 passed in 22.74s**; `git status --porcelain data/ config/` clean (0 lines); ruff **All checks passed!**. State unchanged (SHA256 `111b642c4ac5834460c83ac250a0a90ffb75eed308321ad1bb6309a2fc552517`, last_run_date 2026-11-10, NAV 132498.02732499802, run_history 466, rolling_sharpe_63d -1.4394168982987599). No `*20261111*` artifacts in `data/processed/paper_trading/`. Cmds 2,4,7 **NOT run** (scope boundary: before 22:00 UTC 2026-11-11). Supervisor rec `42925409021-attempt-1-review-0003-632fb1d76266` disposition `verified` in `.kilo-runtime/worker-disposition.json` (runtime). No commits made; `data/raw/` untouched.
- **Pre-staged by session 25 inv 1 (2026-11-10T22:39Z).** Gate for 2026-11-12 releases after **17:00 ET 2026-11-12 (22:00 UTC 2026-11-12)** or following-day-start per completeness rule. Prior gate check for 2026-11-11 to be executed by the intervening session; its post-gate log line is appended to this file's Context section by that session before this task is promoted to `NEXT_AGENT_TASK.md`.
- Tooling: `/tmp/kilo-venv/bin/python` and `/tmp/kilo-venv/bin/ruff`. If missing, `python3 -m venv /tmp/kilo-venv && /tmp/kilo-venv/bin/pip install -r requirements.txt ruff`.

## Objective
At/after 22:00 UTC on 2026-11-12, run the real extension and persistence checks. Extend by at most one session to 2026-11-12 only if a completed bar exists; otherwise record `sessions_extended==0` with explicit reason and keep state unchanged. No alpha/promotion claims.

## Acceptance criteria
- Run verification commands in order; record gate/candidate/sessions_extended/last_run_date/NAV and reason if 0.
- If a completed 2026-11-12 session exists: `sessions_extended==1`, `last_run_date` advances, NAV changes, write count 1.
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
- Do NOT run extend before 22:00 UTC 2026-11-12.

## Verification commands
1. `date -u && TZ=America/New_York date`
2. `/tmp/kilo-venv/bin/python research/extend_paper_trading_state.py 2>&1 | tail -25`
3. `/tmp/kilo-venv/bin/python research/drift_persistence_report.py 2>&1 | tail -8`
4. `/tmp/kilo-venv/bin/python research/extend_paper_trading_state.py 2>&1 | tail -8`
5. `/tmp/kilo-venv/bin/python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py tests/test_state_aggregate_audit.py tests/test_rolling_63d_gate_refresh.py -q`
6. `git status --porcelain data/ config/`
7. (only if state advanced) `/tmp/kilo-venv/bin/python research/data_cost_inventory_001.py && /tmp/kilo-venv/bin/python research/data_cost_inventory_002.py && /tmp/kilo-venv/bin/python -m pytest tests/test_data_cost_inventory_001.py tests/test_data_cost_inventory_002.py -q`
8. `/tmp/kilo-venv/bin/ruff check research/drift_persistence_report.py research/extend_paper_trading_state.py research/verify_monday_extension_path.py`

(End of file - total 47 lines)