# NEXT_AGENT_TASK — Complete the 2026-11-12 post-gate paper-trading extension

## Status at handoff (2026-11-12 17:27 UTC, run 43256335825 attempt 1 session 5 inv 1)

- **Gate for 2026-11-12 is NOT released yet.** It releases at **22:00 UTC 2026-11-12**
  (17:00 ET, per `session_is_complete` close_hour 16 + 1). At handoff the local clock is
  12:27 ET, i.e. ~4.5 h before the gate. `cmd2` (extend) MUST NOT run before 22:00 UTC.
- **Readiness diagnosis (read-only, real state, this session):** `last_run_date 2026-11-11`,
  `clock_gate_released False`, `next_calendar_day 2026-11-12`,
  `next_expected_session 2026-11-12`, `next_session_already_complete False`,
  `candidate_available False`, reason
  *"next session 2026-11-12 has not closed yet (today and still in progress); no completed
  candidate bar exists to extend into"*. **The sole blocker is the clock — there is no code,
  data, or provider problem.**
- **Baseline verified unchanged:** state SHA256
  `5fa67d6395eb9948695e89dfa0349bfe51b15c994b6107214cca1fe9a518e227` (== committed),
  `last_run_date 2026-11-11`, `current_nav 133688.64116621733`, `run_history 467`,
  drift `rolling 63d -1.1048756449232449` with `stored == recomputed True`,
  `git status --porcelain -- data/ config/ src/ tests/ research/` = 0 lines,
  `0` `*20261112*` artifacts in `data/processed/paper_trading/`.
- **Pre-gate cmds 1,3,5,6,8 all PASS:** (1) date; (3) drift consistent, unchanged/not
  worsened; (5) 6 modules **68 passed**; (6) git clean; (8) ruff **All checks passed!**.
- **Detached gate-waiter is ALIVE and will fire:** PID **6726**, PGID/SID **6725** (its own
  session leader, so the per-session idle-watchdog `killpg` cannot signal it), target epoch
  **1794520860 = 2026-11-12T22:01:00Z**, log
  `/home/runner/work/_temp/kilo-tmp/kilo/gate_run.log`. It runs cmds **1,3,2,3,4,5,6,8**.
  **Known gap:** it does **NOT** run `cmd7` (data-cost inventory) and does **NOT** write a
  handoff; its log lives in `/tmp` and is lost on runner teardown. The next session must close
  that gap (see Case A).

## Objective

Complete the 2026-11-12 post-gate cycle. Handle both cases.

**Case A — state already advanced (waiter fired): `last_run_date == 2026-11-12`.**
1. Verify the advance: NAV changed vs `133688.64116621733`, `state_writes 1`, new
   `*20261112*.parquet` artifacts present, drift report consistent.
2. **Close the waiter gap:** run `cmd7` — `research/data_cost_inventory_001.py` and
   `research/data_cost_inventory_002.py` — then `tests/test_data_cost_inventory_001.py` and
   `tests/test_data_cost_inventory_002.py`; confirm the regenerated reports match the new
   counters.
3. Run the 6-module pytest suite; confirm ruff clean.
4. Rewrite this file (and add a README cycle line) with the **actual** post-gate NAV, drift,
   and run_history. Do not carry forward the synthetic `133879.62…` figure from
   `verify_gate_time_forward_bar.py` — it is a synthetic-bar value, not the real NAV.

**Case B — state NOT advanced (still `2026-11-11` at/after 22:00 UTC; waiter failed).**
Run `cmd2` now, then `cmd3`, `cmd4`, `cmd5`, `cmd6`, `cmd8`, and `cmd7` only if the state
advanced. Never run `cmd2` before 22:00 UTC 2026-11-12.

## Acceptance criteria

- gate/candidate/`sessions_extended`/`last_run_date`/NAV recorded; if `sessions_extended==0`
  record the explicit reason and keep state unchanged (0 writes).
- If advanced: `last_run_date == 2026-11-12`, NAV changed, write count 1, new
  `*20261112*.parquet` artifacts present.
- Second invocation idempotent (`sessions_extended==0`, NAV unchanged, 0 writes).
- `drift_persistence_report` updated/consistent (`stored == recomputed True`).
- `git status --porcelain data/ config/` shows only the expected state/report/artifact update.
- 6-module pytest suite passes.
- If advanced: re-run cmd7 inventory + its tests and confirm the reports match the new counters.
- Ruff clean on the 4 extension scripts.

## Verification commands

1. `date -u && TZ=America/New_York date`
2. `/tmp/kilo-venv/bin/python research/extend_paper_trading_state.py 2>&1 | tail -25`
3. `/tmp/kilo-venv/bin/python research/drift_persistence_report.py 2>&1 | tail -8`
4. `/tmp/kilo-venv/bin/python research/extend_paper_trading_state.py 2>&1 | tail -8`
5. `/tmp/kilo-venv/bin/python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py tests/test_state_aggregate_audit.py tests/test_rolling_63d_gate_refresh.py -q`
6. `git status --porcelain data/ config/`
7. (only if state advanced) `/tmp/kilo-venv/bin/python research/data_cost_inventory_001.py && /tmp/kilo-venv/bin/python research/data_cost_inventory_002.py && /tmp/kilo-venv/bin/python -m pytest tests/test_data_cost_inventory_001.py tests/test_data_cost_inventory_002.py -q`
8. `/tmp/kilo-venv/bin/ruff check research/drift_persistence_report.py research/extend_paper_trading_state.py research/verify_monday_extension_path.py research/verify_gate_time_forward_bar.py`

Tooling: `/tmp/kilo-venv/bin/python` and `/tmp/kilo-venv/bin/ruff`. If missing:
`python3 -m venv /tmp/kilo-venv && /tmp/kilo-venv/bin/pip install -q -r requirements.txt ruff`.

## Scope boundaries

- Do not change thresholds/gates/cost model/universe/clock-gate logic.
- Do not commit unless explicitly asked.
- Do not modify `data/raw/`.
- Do NOT run `cmd2` (extend) before 22:00 UTC 2026-11-12.
- Full cycle-by-cycle audit history for this task lives in `README.md` (Cycles 1223–1241)
  and the `CORRECTIVE_HANDOFF_*.md` files; it is intentionally not repeated here.
- Pre-staged `NEXT_AGENT_TASK_20261113.md` exists but its Context references an older
  (2026-11-12T00:35Z) session; refresh its Context from the actual 2026-11-12 post-gate
  result before promoting it.