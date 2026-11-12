# NEXT_AGENT_TASK — Verify/complete the 2026-11-12 paper-trading gate extension

## Status at handoff (2026-11-12 17:24 UTC, run 43256335825 attempt 1 session 4)

- **Gate releases 22:00 UTC 2026-11-12.** A detached gate-waiter is already running and
  will fire automatically at **22:01 UTC**: PID 6726, script
  `/home/runner/work/_temp/kilo-tmp/kilo/gate_wait_and_run.sh`, target epoch 1794520860,
  log `/home/runner/work/_temp/kilo-tmp/kilo/gate_run.log`.
  - Robustness verified: the waiter is its **own session leader** (PGID/SID 6725), so the
    per-session idle-watchdog `killpg` (which kills only each worker's own process group,
    e.g. node SID 54025) cannot terminate it. It has already survived 1 h+ across multiple
    session transitions. It is expected to still be alive at 22:01.
  - The waiter runs cmds 1,3,2,3,4,5,6,8. It does **NOT** run cmd7
    (`data_cost_inventory_001/002.py`) and does not write a post-gate handoff.
- **Pre-gate state (verified fresh this session, unchanged):**
  SHA256 `5fa67d6395eb9948695e89dfa0349bfe51b15c994b6107214cca1fe9a518e227`,
  `last_run_date 2026-11-11`, `current_nav 133688.64116621733`, `run_history 467`,
  drift tail `2026-11-11 -1.1049` (stored == recomputed), git tree clean.
- **Forward-path code-path verifier PASSES** (`research/verify_gate_time_forward_bar.py`):
  target 2026-11-12, `sessions_extended 1`, `state_writes 1`, `fetch_error None`,
  canonical state/report hashes unchanged. **Caveat:** its `nav_after 133879.62493931194`
  is computed from a **synthetic flat-extended 2026-11-12 bar** (`synthetic shape … max date
  2026-11-12`), so it is **not** the real expected NAV. The live 22:01 fetch will produce a
  different NAV. (Earlier cycles wrongly called 133879.62… "deterministic expected NAV".)
- **Orchestration (context for why sessions run before the gate):** `main.yml` runs on a
  `*/5 * * * *` cron and spawns sequential worker sessions until a global 355-min wall-clock
  cutoff (~22:08 UTC for this run). Pre-22:00 sessions therefore correctly do pre-gate
  verification only (cmds 1,3,5,6,8); they are not project no-ops by choice, they are
  blocked by the clock gate.

## Objective

Determine whether the 2026-11-12 gate extension ran, then verify and complete it.

- If `last_run_date` is already `2026-11-12` (waiter fired): verify the advance, then run
  cmd7 (inventory) and confirm the regenerated reports match the new counters. Write the
  post-gate result.
- If `last_run_date` is still `2026-11-11` at/after 22:00 UTC (waiter did not fire): run the
  real extension (cmd2) and the rest of cmds 1–8 in order.
- Never run cmd2 before 22:00 UTC 2026-11-12.

## Acceptance criteria

- Gate/candidate/sessions_extended/last_run_date/NAV recorded; if `sessions_extended==0`
  record the explicit reason and keep state unchanged (0 writes).
- If advanced: `last_run_date == 2026-11-12`, NAV changed, write count 1, new
  `*20261112*.parquet` artifacts present.
- Second invocation idempotent (`sessions_extended==0`, NAV unchanged, 0 writes).
- `drift_persistence_report` updated/consistent.
- `git status --porcelain data/ config/` shows only the expected state/report/artifact update.
- 6-module pytest suite passes.
- If state advanced: re-run `research/data_cost_inventory_001.py` and
  `research/data_cost_inventory_002.py` and confirm the reports match new counters; re-run
  `tests/test_data_cost_inventory_001.py` and `tests/test_data_cost_inventory_002.py`.
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
- Do NOT run cmd2 (extend) before 22:00 UTC 2026-11-12.
- Full cycle-by-cycle audit history for this task lives in `README.md` (Cycles 1223–1240)
  and the `CORRECTIVE_HANDOFF_*.md` files; it is intentionally not repeated here.