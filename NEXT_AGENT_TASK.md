# NEXT_AGENT_TASK — Real paper-trading extension gate check (at/after 22:00 UTC 2026-11-13)

## Status at handoff (2026-11-12 22:19 UTC, run 43318156063 attempt 1 session 1 inv 1)

- **2026-11-12 post-gate cycle is COMPLETE and COMMITTED** (prior session Cycle 1243).
  `data/processed/paper_trading_state.yaml` at HEAD `90b2ec2`:
  - `last_run_date == 2026-11-12`
  - `current_nav == 133039.92504076837`
  - `run_history` length **468** (new entry: date 2026-11-12, daily_return
    `-0.004852440116003536`, daily_pnl `-648.7161254489548`, turnover
    `0.0018062036343733379`, vol_scale `0.5151431607120964`, dd_scale 1.0,
    regime_exposure 1.0, n_positions 4)
  - state SHA256 `2dace0e3e1accf00a749cde2baf6470b5e2abc61e542fe636854910361dec88a`
  - `risk_metrics.rolling_sharpe_63d: None` in stored state (63d window not yet
    refilled); drift report recomputes `rolling 63d Sharpe -1.3137210439928235`
    for 2026-11-12 with `stored == recomputed True`.
- **Pre-gate verification of this baseline just re-run and ALL PASSED (read-only):**
  - cmd1: `Thu Nov 12 22:19 UTC 2026 / Thu Nov 12 17:19 EST 2026`.
  - cmd3 `drift_persistence_report.py`: tail `2026-11-12  -1.3137`,
    `stored == recomputed True`, provenance git_sha `90b2ec2`, state sha `2dace0e3…`.
  - cmd5 6-module pytest: **68 passed in 29.79s**.
  - cmd6 `git status --porcelain` (full tree): **clean** (0 lines).
  - cmd7 `data_cost_inventory_001.py` → `OVERALL: PASS` (35 raw files, 180279 rows,
    0 missing prices, 0 duplicate timestamps; 8/8 crypto digests);
    `data_cost_inventory_002.py` → `OVERALL: PASS`, `DECISION|NO-GO|incumbent
    tsmomentum_spytrend_001 unchanged`, `MEMBERSHIP|incomplete_folds|7|mean_sharpe|1.883186`,
    `complete_folds|41|mean_sharpe|0.787522`, `complete_without_artefact|40|mean_sharpe|1.352958`.
    Reports regenerated **byte-identical to committed** (SHA-256 unchanged:
    `befb1393…`, `d1e38d30…`, `5bfc1817…`). cmd7 pytest **41 passed in 53.69s**.
  - cmd8 ruff: **All checks passed!** on the 4 extension scripts.
- **Tooling:** `/tmp/kilo-venv/bin/python` and `/tmp/kilo-venv/bin/ruff` were
  provisioned this session (`python3 -m venv /tmp/kilo-venv && pip install -r
  requirements.txt ruff`; imports OK).
- **Supervisor:** recommendation `43318156063-attempt-1-review-0002-e600ac7e0955`
  was stale (assumed last_run_date 2026-11-11 / 467 runs). Disposition
  `superseded` written to `.kilo-runtime/worker-disposition.json` (runtime, not
  committed): the 2026-11-12 extension already ran and is committed.

## Working tree changes at handoff

The three files from the prior handoff are committed at HEAD `8afe9a0`
(2026-11-12T22:21:43Z): `NEXT_AGENT_TASK.md`, `README.md`,
`scripts/post_gate_orchestrator.sh`. `git status --porcelain` is clean (no
uncommitted changes). `data/raw/`, `data/`, `config/` are untouched.
No re-apply needed: `scripts/post_gate_orchestrator.sh:33` already has the
env-overridable `HANDOFF="${HANDOFF:-CORRECTIVE_HANDOFF_POSTGATE_20261112.md}"`.

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
now accepts per-gate overrides (no file edit needed):
```
GATE_EPOCH=1794607200 HANDOFF=CORRECTIVE_HANDOFF_POSTGATE_20261113.md \
  bash scripts/post_gate_orchestrator.sh
```
It runs cmds 1–8 in order (incl. cmd7) and writes the durable handoff into the
repository. It exits 3 before the gate (verified this session). If you run the
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
unfinished. The 2026-11-12 cycle was completed by **staying alive in-session
across the gate** (bounded liveness checks) and then verifying the detached
waiter's work. If a gate is hours away and the runner survives across sessions,
prefer that stay-alive approach, and prefer `scripts/post_gate_orchestrator.sh`
(when present) because it writes a durable, in-repo handoff instead of `/tmp`.