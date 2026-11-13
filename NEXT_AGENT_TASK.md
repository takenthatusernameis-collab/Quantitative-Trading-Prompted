# NEXT_AGENT_TASK — Real paper-trading extension gate check (at/after 22:00 UTC 2026-11-13)

## Status at handoff (2026-11-13 01:16 UTC, corrective invocation 380)

- **2026-11-13 pre-gate cycle is COMPLETE and COMMITTED** (prior session Cycle 1246).
  `data/processed/paper_trading_state.yaml` at HEAD `15bcaac`:
  - `last_run_date == 2026-11-12`
  - `current_nav == 133039.92504076837`
  - `run_history` length **468**
  - state SHA256 `2dace0e3e1accf00a749cde2baf6470b5e2abc61e542fe636854910361dec88a`
  - `risk_metrics.rolling_sharpe_63d: None` in stored state (63d window not yet refilled); drift report recomputes `rolling 63d Sharpe -1.3137210439928235` for 2026-11-12 with `stored == recomputed True`.
- **Pre-gate verification re-run this session (corrective invocation 380) — ALL PASSED (read-only):**
  - cmd1: `Fri Nov 13 01:15:56 UTC 2026 / Thu Nov 12 20:15:56 EST 2026`.
  - cmd2 `extend_paper_trading_state.py`: clock gate **NOT released**, `candidate available: no`, `sessions extended: 0`, NAV unchanged `133039.92504076837`, `state write count: 0`.
  - cmd3 `drift_persistence_report.py`: tail `2026-11-12  -1.3137`, `stored == recomputed True`.
  - cmd5 6-module pytest: **68 passed in 28.16s**.
  - cmd6 `git status --porcelain data/ config/`: **clean** (0 lines).
  - cmd8 ruff: **All checks passed!** on the 4 extension scripts.
  - Orchestrator gate guard: `GATE_EPOCH=1794607200 HANDOFF=CORRECTIVE_HANDOFF_POSTGATE_20261113.md bash scripts/post_gate_orchestrator.sh` exits **3** before the gate (verified previously: `ORCHESTRATOR_EXIT_CODE=3`).
- **Gate reachability (deterministic time blocker, not a failure loop):** this run's
  controller cutoff is `remaining_seconds=10478` (~2.9h) from 01:15 UTC, i.e.
  ~04:09 UTC 2026-11-13 — BEFORE the 22:00 UTC gate (epoch 1794607200). A detached waiter
  spawned in this run cannot survive run teardown to 22:00 UTC, so the real extension is
  not executable in this run. The run active at 22:00 UTC 2026-11-13 must perform the gate
  check (see Note for the next session).
- **Working tree is clean and committed** (HEAD `9191b0c`):
  - HEAD `9191b0c` (2026-11-13T00:23:07Z): `CORRECTIVE_HANDOFF_SESSION8_20261113T0033Z.md`,
    `NEXT_AGENT_TASK.md`.
  - `git status --porcelain` is clean (0 lines). `data/raw/`, `data/`, `config/` untouched.
- **Tooling:** `/tmp/kilo-venv/bin/python` and `/tmp/kilo-venv/bin/ruff` present
  (imports OK: yaml/pandas/numpy/pyarrow/pytest).

## Working tree changes at handoff

All prior changes are committed and the tree is clean:

- HEAD `9191b0c` (2026-11-13T00:23:07Z): `CORRECTIVE_HANDOFF_SESSION8_20261113T0033Z.md`,
  `NEXT_AGENT_TASK.md`.
- `git status --porcelain` is clean (0 lines). `data/raw/`, `data/`, `config/` untouched.
- No re-apply needed: the orchestrator already accepts `GATE_EPOCH`/`HANDOFF` env
  overrides, `--force`/`--read-only` in any order, and `--wait-until-gate`
  `--max-wait-seconds N`.

## Objective

At/after **22:00 UTC 2026-11-13** (gate epoch **1794607200**), run the real
extension and persistence checks for the 2026-11-13 session. Extend by at most
one session to 2026-11-13 only if a completed bar exists; otherwise record
`sessions_extended==0` with the explicit reason and keep state unchanged. No
alpha/promotion claims.

## Acceptance criteria

- Run verification commands in order; record gate / candidate / `sessions_extended`
  / `last_run_date` / NAV, and the explicit reason if `sessions_extended==0`.
- If a completed 2026-11-13 session exists: `sessions_extended==1`,
  `last_run_date` advances to 2026-11-13, NAV changes, `state write count 1`.
- If not: `sessions_extended==0`, NAV unchanged, 0 writes.
- Second invocation idempotent (0 writes, NAV unchanged).
- `drift_persistence_report` updated/consistent (`stored == recomputed True`).
- `git status --porcelain data/ config/` shows only the expected state/report/artifact update.
- 6-module pytest suite passes.
- If state advanced: re-run `research/data_cost_inventory_001.py` and
  `research/data_cost_inventory_002.py` and confirm the regenerated reports match
  the new counters; re-run `tests/test_data_cost_inventory_001.py` and
  `tests/test_data_cost_inventory_002.py`.
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

**Preferred execution path** — the durable, restart-safe, gate-guarded orchestrator
now accepts per-gate overrides and an optional bounded wait (no file edit needed):
```
GATE_EPOCH=1794607200 HANDOFF=CORRECTIVE_HANDOFF_POSTGATE_20261113.md \
  bash scripts/post_gate_orchestrator.sh --wait-until-gate
```
It runs cmds 1–8 in order (incl. cmd7) and writes the durable handoff into the
repository. It exits 3 before the gate (verified this session) unless
`--wait-until-gate` is given, in which case it blocks (60s heartbeat, bounded by the
run's own 355-minute cutoff) until the gate releases and then runs. If you run the
orchestrator, the manual list above is the fallback / independent record.

## Scope boundaries

- Do not change thresholds/gates/cost model/universe/clock-gate logic.
- Do not commit unless explicitly asked.
- Do not modify `data/raw/`.
- Do NOT run `cmd2` (extend) before 22:00 UTC 2026-11-13.
- Do NOT re-extend to 2026-11-12: that session is already complete and committed
  (`last_run_date == 2026-11-12`, run_history 468). A bare `cmd2` run before the
  next gate is a verified no-op (clock gate returns 0 writes), but it is out of
  scope here.
- Full cycle-by-cycle audit history lives in `README.md` (Cycles 1223–1243) and
  the `CORRECTIVE_HANDOFF_*.md` files; it is intentionally not repeated here.

## Note for the next session

The previous ~15 pre-gate sessions ended before their gate and left the cycle
unfinished; the 2026-11-12 cycle was completed by **staying alive in-session
across the gate** and verifying the detached waiter's work. This run (corrective
invocation 380) is clock-blocked: its run cutoff (~04:09 UTC 2026-11-13,
`remaining_seconds=10478` at 01:15 UTC) is ~18h before the gate, so do NOT burn
the session on repeated pre-gate verification. Instead:
- If the current run will still be active at 22:00 UTC 2026-11-13 (check the
  controller `remaining_seconds` in `$RUNNER_TEMP/kilo-progress-state-*.txt`), run
  `GATE_EPOCH=1794607200 HANDOFF=CORRECTIVE_HANDOFF_POSTGATE_20261113.md bash
  scripts/post_gate_orchestrator.sh --wait-until-gate` so the extension fires
  exactly at the gate (the run's 355-minute cutoff bounds the wait).
- Otherwise hand off immediately with a fresh pre-gate verification and let the run
  that is active at the gate perform the check.
Prefer `scripts/post_gate_orchestrator.sh` because it writes a durable, in-repo
handoff instead of `/tmp`, and now exits non-zero + marks the handoff `FAILED` on any
failed sub-check (verified previously with negative/positive controls).