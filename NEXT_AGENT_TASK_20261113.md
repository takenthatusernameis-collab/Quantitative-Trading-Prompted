# NEXT_AGENT_TASK — Real paper-trading extension gate check (at/after 22:00 UTC 2026-11-13)

## Context
- **Pre-gate verification 2026-11-12 18:41 UTC (Cycle 1242, session 5 inv 2, corrective 411):** Gate for 2026-11-12 **NOT released** (releases 22:00 UTC 2026-11-12; ~3.2h remaining). Verified this cycle, materially different from prior no-op loops:
  - **cmd7 (the documented waiter gap) now runs inside the cycle** via the new durable orchestrator `scripts/post_gate_orchestrator.sh`, which is gate-guarded (exit 3 before release), restart-safe, idempotent, and writes its handoff into the repository (`CORRECTIVE_HANDOFF_POSTGATE_20261112.md`) instead of `/tmp`.
  - **cmd7 determinism verified pre-gate:** `data_cost_inventory_001.py` and `data_cost_inventory_002.py` both ran clean and regenerated reports **byte-identical to committed** (SHA-256 diff empty) while state was unchanged — proving the inventory path is stable across the 2026-11-12 extension and will only change counters after a real advance.
  - **Pre-gate cmds 1,3,5,6,8 all pass:** (1) `2026-11-12 18:41 UTC / Thu Nov 12 13:41 EST`; (3) drift tail ends `2026-11-11 -1.1049`, `stored == recomputed True`; (5) 6 modules **68 passed in 26.96s**; (6) `git status --porcelain data/ config/ src/ tests/ research/` clean (only `research/reports/*.md` + new `scripts/post_gate_orchestrator.sh`); (8) ruff **All checks passed!** on the 4 extension scripts.
  - **State unchanged:** SHA256 `5fa67d6395eb9948695e89dfa0349bfe51b15c994b6107214cca1fe9a518e227` (== committed), `last_run_date 2026-11-11`, NAV `133688.64116621733`, run_history **467**, 0 `*20261112*` artifacts.
  - **Detached gate-waiter still ALIVE:** PID 6726 (PGID/SID 6725), target 1794520860 = 2026-11-12T22:01:00Z. It runs cmds 1,3,2,3,4,5,6,8. The orchestrator is the durable superset (adds cmd7 + repo handoff) and can be re-run safely at/after the gate regardless of whether the waiter fired.
- **Pre-staged by session 1 inv 1 (2026-11-12T00:35Z).** Gate for 2026-11-13 releases after **17:00 ET 2026-11-13 (22:00 UTC 2026-11-13)** or following-day-start per completeness rule. The 2026-11-12 post-gate result (NAV/drift/history after the 22:00 extension) is appended to `NEXT_AGENT_TASK.md` Context by the intervening 22:00+ session before this task is promoted.
- Tooling: `/tmp/kilo-venv/bin/python` and `/tmp/kilo-venv/bin/ruff`. If missing, `python3 -m venv /tmp/kilo-venv && /tmp/kilo-venv/bin/pip install -r requirements.txt ruff`.
- **Preferred execution path:** `bash scripts/post_gate_orchestrator.sh` (full cycle 1–8 incl. cmd7 + durable handoff). Manual cmd-by-cmd fallback is the verification list below.

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