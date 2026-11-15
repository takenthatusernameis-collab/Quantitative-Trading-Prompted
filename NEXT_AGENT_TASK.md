# Next Agent Task: execute the 2026-11-16 gate extension in the FOREGROUND

## Current status (verified 2026-11-15T07:24Z, run 43656693214, session 16 inv 1)
- **Pre-gate cheap path exit 0 (STOP):** `GATE_EPOCH=1794866400 STATE_SHA256=c438cd71785459e2612e2dda3425d670de920a62de532c0dff2da6fe332b6365 bash scripts/pre_gate_check.sh` → `PRE-GATE OK: now=1794727410 (2026-11-15T07:23:30Z) < gate 1794866400 (2026-11-16T22:00:00Z); T-138990s remaining. state sha256 matches (c438cd71…); data/raw clean. STOP` **EXIT=0**.
- **Gate reachability (deterministic):** now epoch 1794727410 vs gate 1794866400 → **~38.6h / T-138990s out**. No code change can release the gate early. The run active at/after 2026-11-16T22:00:00Z must run Step 2.
- **Focused verification this run:** `/tmp/kilo-venv/bin/python -m pytest -q tests/test_post_gate_orchestrator.py tests/test_pre_gate_check.py tests/test_post_gate_handoff_consistency.py` → **57 passed in 3.86s**; `/tmp/kilo-venv/bin/ruff check tests/test_post_gate_orchestrator.py tests/test_pre_gate_check.py tests/test_post_gate_handoff_consistency.py` → **All checks passed!**; `bash -n scripts/post_gate_orchestrator.sh` → **ORCH_BASH_OK**; `bash -n scripts/pre_gate_check.sh` → **PREGATE_BASH_OK**.
- **Working tree:** `git status --porcelain` → empty (before this doc refresh); `git ls-files --others --exclude-standard` → empty; `git status --porcelain -- data/raw` → empty. HEAD `29503eb`. `/tmp/kilo-venv` present. No production code, threshold, gate, cost model, universe, or `data/raw` touched.
- **State fingerprint (unchanged):** `last_run_date 2026-11-13`; `current_nav 132654.46201168097`; `run_history 469`; sha256 `c438cd71785459e2612e2dda3425d670de920a62de532c0dff2da6fe332b6365`.
- **Provider-noise note:** corrective inv 392 (2026-11-15T07:12Z) recovery logs 389–391 showed model-provider `Sign up for free…` aborts before any project command (623 occurrences over 392 recovery logs in `/home/runner/work/_temp/kilo-session-13-recovery-*.log`). This is **not** a project-layer defect; do not treat provider exit-1 as a code/test/gate failure.

## Prior verified fixes at HEAD (preserved, do not re-open)
- **inv-473:** `tests/test_shortlist_gross_edge_001.py` write-scope check diffs harness-only changes; `research/reports/tsmomentum_same_session_vol_correction_001.md` refreshed.
- **inv-230:** go_no_go parser strips markdown bullets (`.strip(" *")`) for rolling Sharpe in `src/simulation/paper_trading.py:590`.
- **inv-182:** `scripts/post_gate_orchestrator.sh` gates mutating extend on `PRE_GATE` (clock), not `--read-only`; `Mode` derived from what actually ran.
- **inv-228:** cmd9 state-fingerprint accepts optional leading minus (`nav=-?[0-9]+\.?[0-9]*`); 4 regression tests.
- **inv-1:** orchestrator fails closed (rc=2) with actionable "recreate /tmp/kilo-venv" when `PYTHON`/`RUFF` missing; 3 regression tests.
- **session 12:** `tests/test_post_gate_handoff_consistency.py` pins committed `CORRECTIVE_HANDOFF_POSTGATE_20261116.md` State/Mode/Gate/Cmds against real state and gate.

## Step 1 — pre-gate cheap path (now < 2026-11-16T22:00:00Z)
```
GATE_EPOCH=1794866400 STATE_SHA256=c438cd71785459e2612e2dda3425d670de920a62de532c0dff2da6fe332b6365 \
  bash scripts/pre_gate_check.sh
```
- Exit 0 → **STOP.** (cheap path; no per-session record needed if state unchanged)
- Exit 3 → precondition failed (gate reached / hash drift / dirty `data/raw`): inspect; if gate released go to Step 2.
- Exit 2 → usage error: fix and re-run.

## Step 2 — full gate cycle (only at/after gate, state still `2026-11-13`)
```
GATE_EPOCH=1794866400 PYTHON=/tmp/kilo-venv/bin/python RUFF=/tmp/kilo-venv/bin/ruff \
  bash scripts/post_gate_orchestrator.sh
```
Runs cmds 1–8 including mutating extend (cmd2) and idempotency re-run (cmd4), plus cmd9 fingerprint; rewrites `CORRECTIVE_HANDOFF_POSTGATE_20261116.md` with `Mode: full cycle (extend included)` and `Gate state: released (gate epoch reached)`. Run once more to confirm idempotency (expect `sessions extended: 0`, no second state write). Extend targets next session after 2026-11-13 (**2026-11-16 Mon**); complete once local time ≥ 17:00 ET = 22:00 UTC (EST). Expect exactly one session appended and a single state write.

## Acceptance criteria
- [ ] Gate extension ran at/after 2026-11-16T22:00:00Z, in the foreground.
- [ ] Extends by <=1 session only if a completed bar exists; idempotent re-run extends 0 with 0 writes.
- [ ] `data/raw` untouched; no threshold/gate/cost/universe/clock-gate changes.
- [ ] Working tree shows only intended state/handoff/artifact changes; handoff `Status: OK`, `Mode: full cycle (extend included)`, `Gate state: released`, exit 0, and a **non-empty** `- **State:**` line.

## Validation commands
- `GATE_EPOCH=1794866400 STATE_SHA256=c438cd71785459e2612e2dda3425d670de920a62de532c0dff2da6fe332b6365 bash scripts/pre_gate_check.sh` (pre-gate: exit 0; at/after gate: exit 3)
- `cat CORRECTIVE_HANDOFF_POSTGATE_20261116.md` (pre-gate: `Status: OK`, `Mode: pre-gate verification (extend withheld — gate not released)`, `Gate state: NOT released`, `Cmds skipped` includes `2 extend (gate not released)` and `4 idempotent re-extend (gate not released)`; post-gate: `Status: OK`, `Mode: full cycle (extend included)`, `Gate state: released`)
- `git status --porcelain -- data/raw` (expect empty)
- `git status --porcelain` (only intended state/handoff changes)
- `/tmp/kilo-venv/bin/python -m pytest -q tests/test_post_gate_orchestrator.py tests/test_pre_gate_check.py tests/test_post_gate_handoff_consistency.py` (>=57 passed)
- `/tmp/kilo-venv/bin/ruff check tests/test_post_gate_orchestrator.py tests/test_pre_gate_check.py tests/test_post_gate_handoff_consistency.py` (All checks passed!)

## Scope boundaries
- Do not run a mutating extend before the target session gate.
- Do not change thresholds/gates/cost model/universe/clock-gate logic; do not touch `data/raw/`.
- Do not commit manually; controller checkpoints at session boundaries.
- Do not dispatch this workflow, start additional agent sessions, or launch a background waiter.
- Do not append redundant per-session re-verification notes to this file on clean pre-gate exit 0 with unchanged state.

## Runtime note
`/tmp/kilo-venv` is ephemeral. If absent before Step 2:
```
python3 -m venv /tmp/kilo-venv
/tmp/kilo-venv/bin/python -m pip install --no-cache-dir numpy pandas scipy statsmodels arch yfinance pyarrow pyyaml pytest ruff
```

## Session log (non-redundant)
- **Corrective inv 396, session 16 inv 1 (2026-11-15T07:24Z, HEAD 29503eb):** pre-gate cheap path EXIT=0 (T-138990s); 57 tests passed; ruff clean; bash -n OK on both scripts; state/hash/data-raw/working-tree clean. Gate unreached; Step 2 withheld. `NEXT_AGENT_TASK.md` consolidated (removed duplicated per-session re-verification blocks inv 393–396 and tail duplicate Step 1/2 text) to preserve a single authoritative handoff without losing task/procedure/criteria/traceability.
