# NEXT_AGENT_TASK — 2026-11-13 gate check (post-advance test anchors repaired)

## Status at handoff (2026-11-13 02:25 UTC, corrective invocation 2 — pre-gate re-verification)

- **Recovery log inspected:** `/home/runner/work/_temp/kilo-session-14-recovery-1.log` (prior invocation ran pre-gate verification but produced no durable project changes).
- **Pre-gate verification completed this corrective session (bounded, evidence-based):**
  - **Cmd 1 (time):** `2026-11-13 02:21:44 UTC / Thu Nov 12 21:21:44 EST 2026` (clock gate for 2026-11-13 session NOT released; target 22:00 UTC 2026-11-13, epoch 1794607200).
  - **Cmd 3 (drift):** tail ends `2026-11-12  -1.3137` (`stored == recomputed True`).
  - **Cmd 5 (6-module pytest):** `tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py tests/test_state_aggregate_audit.py tests/test_rolling_63d_gate_refresh.py` → **68 passed in 28.07s**.
  - **Cmd 6 (git status data/config):** **0 lines** (clean; state SHA256 `2dace0e3e1accf00a749cde2baf6470b5e2abc61e542fe636854910361dec88a` matches HEAD).
  - **Cmd 8 (ruff on 4 extension scripts):** **All checks passed!** (`research/drift_persistence_report.py research/extend_paper_trading_state.py research/verify_monday_extension_path.py research/verify_gate_time_forward_bar.py`).
  - **Cmd 9 (two repaired test modules):** `tests/test_tsmomentum_rolling63_weakness_diagnosis.py tests/test_go_no_go_evaluation.py` → **36 passed in 113.80s**.
- **State (unchanged, verified):** 468 sessions, `last_run_date 2026-11-12`, `current_nav 133039.92504076837`, run_history 468, state SHA256 `2dace0e3e1accf00a749cde2baf6470b5e2abc61e542fe636854910361dec88a`.
- **Gate reachability (deterministic time blocker, not a failure loop):** this run's controller cutoff is ~04:10 UTC 2026-11-13 — **before** the 22:00 UTC 2026-11-13 gate (epoch **1794607200**). The real extension is not executable in this run. The run active at 22:00 UTC must perform the gate check below.
- **Working tree:** only this `NEXT_AGENT_TASK.md` status refresh is modified by this corrective session (durable handoff update); `data/` and `config/` remain clean. `CORRECTIVE_HANDOFF_POSTGATE_20261113.md` is present as an untracked artifact from prior work.

## Objective

At/after **22:00 UTC 2026-11-13** (gate epoch **1794607200**), run the real extension and persistence checks for the 2026-11-13 session. Extend by at most one session to 2026-11-13 only if a completed bar exists; otherwise record `sessions_extended==0` with the explicit reason and keep state unchanged. No alpha/promotion claims.

## Acceptance criteria

- Run verification commands in order; record gate / candidate / `sessions_extended` / `last_run_date` / NAV, and the explicit reason if `sessions_extended==0`.
- If a completed 2026-11-13 session exists: `sessions_extended==1`, `last_run_date` advances to 2026-11-13, NAV changes, `state write count 1`.
- If not: `sessions_extended==0`, NAV unchanged, 0 writes.
- Second invocation idempotent (0 writes, NAV unchanged).
- `drift_persistence_report` updated/consistent (`stored == recomputed True`).
- `git status --porcelain data/ config/` shows only the expected state/report/artifact update.
- 6-module pytest suite passes.
- **New (post-advance):** the two repaired modules (`tests/test_tsmomentum_rolling63_weakness_diagnosis.py`, `tests/test_go_no_go_evaluation.py`) still pass, and the regenerated rolling63 report/experiment match the committed record (468 sessions, trailing `-1.3137210439928235`, 406 windows). If the state advances to 2026-11-13, update those record anchors again from the new committed state before re-running.
- If state advanced: re-run `research/data_cost_inventory_001.py` and `research/data_cost_inventory_002.py` and confirm the regenerated reports match the new counters; re-run `tests/test_data_cost_inventory_001.py` and `tests/test_data_cost_inventory_002.py`.
- Ruff clean on the 4 extension scripts (and no new findings on the two test modules).

## Verification commands

1. `date -u && TZ=America/New_York date`
2. `/tmp/kilo-venv/bin/python research/extend_paper_trading_state.py 2>&1 | tail -25`
3. `/tmp/kilo-venv/bin/python research/drift_persistence_report.py 2>&1 | tail -8`
4. `/tmp/kilo-venv/bin/python research/extend_paper_trading_state.py 2>&1 | tail -8`
5. `/tmp/kilo-venv/bin/python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py tests/test_state_aggregate_audit.py tests/test_rolling_63d_gate_refresh.py -q`
6. `git status --porcelain data/ config/`
7. (only if state advanced) `/tmp/kilo-venv/bin/python research/data_cost_inventory_001.py && /tmp/kilo-venv/bin/python research/data_cost_inventory_002.py && /tmp/kilo-venv/bin/python -m pytest tests/test_data_cost_inventory_001.py tests/test_data_cost_inventory_002.py -q`
8. `/tmp/kilo-venv/bin/ruff check research/drift_persistence_report.py research/extend_paper_trading_state.py research/verify_monday_extension_path.py research/verify_gate_time_forward_bar.py`
9. `/tmp/kilo-venv/bin/python -m pytest tests/test_tsmomentum_rolling63_weakness_diagnosis.py tests/test_go_no_go_evaluation.py -q`

Tooling: `/tmp/kilo-venv/bin/python` and `/tmp/kilo-venv/bin/ruff`. If missing:
`python3 -m venv /tmp/kilo-venv && /tmp/kilo-venv/bin/pip install -q -r requirements.txt ruff`.

**Preferred execution path** — the durable, restart-safe, gate-guarded orchestrator accepts per-gate overrides and an optional bounded wait (no file edit needed):
```
GATE_EPOCH=1794607200 HANDOFF=CORRECTIVE_HANDOFF_POSTGATE_20261113.md \
  bash scripts/post_gate_orchestrator.sh --wait-until-gate
```
It runs cmds 1–8 in order (incl. cmd7) and writes the durable handoff into the repository. It exits 3 before the gate unless `--wait-until-gate` is given, in which case it blocks (60s heartbeat, bounded by the run's own cutoff) until the gate releases and then runs. The manual list above is the fallback / independent record.

## Scope boundaries

- Do not change thresholds/gates/cost model/universe/clock-gate logic.
- Do not commit unless explicitly asked.
- Do not modify `data/raw/`.
- Do NOT run `cmd2` (extend) before 22:00 UTC 2026-11-13.
- Do NOT re-extend to 2026-11-12: that session is complete and committed.
- Do not "fix" the pre-existing `RUF100`/`PLW1510` lint findings in the two test modules; they predate this task and are outside its scope.
- Full cycle-by-cycle audit history lives in `README.md` and the `CORRECTIVE_HANDOFF_*.md` files; it is intentionally not repeated here.

## Note for the next session

The 2026-11-12 cycle is complete and committed. The only open item for 2026-11-13 is the gate check above. **If the run is active at 22:00 UTC 2026-11-13, run the orchestrator with `--wait-until-gate`; otherwise hand off immediately with a fresh pre-gate verification and let the gate-active run perform the check. Do not burn the session on repeated pre-gate verification: this run is clock-blocked (cutoff ~04:10 UTC), and the previous ~15 pre-gate sessions that did so left the cycle unfinished.**