# Next Agent Task: execute the 2026-11-16 gate extension in the FOREGROUND (the detached waiter cannot survive)

## Context — verified baseline (2026-11-14T03:49Z, session 23 inv 1; run 43522470160 attempt 1)
The 2026-11-13 gate extension is COMPLETE and committed; HEAD `eedcb11` (the last three commits were pure handoff-timestamp churn — see "Change made this session").
- State: `last_run_date 2026-11-13`, `current_nav 132654.46201168097`, `run_history` 469, SHA256 `c438cd71785459e2612e2dda3425d670de920a62de532c0dff2da6fe332b6365` — re-verified unchanged at 03:49Z.
- `date -u +%s` = 1794634270 < gate 1794866400 (2026-11-16T22:00:00Z): **~64.5h (T-232130s) before the gate**. `data/raw` untouched. `/tmp/kilo-venv` absent — recreate per the runtime note before running Step 2. No background waiter running.
- This session (2026-11-14T05:31Z): `scripts/pre_gate_check.sh` → exit 0 (cheap path applies); STOP — no cycle re-run, no handoff churn, no commit.
- Pre-gate cheap verification this session (03:49Z): `scripts/pre_gate_check.sh` → exit 0 (hash matches, `data/raw` clean). Did NOT re-run the full read-only cycle.
- Validation: `pytest tests/test_pre_gate_check.py tests/test_post_gate_orchestrator.py` → 30 passed. `bash -n` on both orchestrator scripts → OK. All imports in `/tmp/kilo-venv` OK.

## Change made this session (only non-handoff change)
The pre-gate cheap path was **prose-only and unenforced**, so three consecutive sessions
(`5be09e6`, `b5403fc`, `6799001`) each ignored it, re-ran the full read-only cycle, and committed
nothing but a fresh `Context — verified baseline` timestamp — i.e. **zero project progress**.
Added `scripts/pre_gate_check.sh`: a deterministic, side-effect-free, read-only check that encodes the
cheap path (gate-epoch + state-sha256 + `data/raw`-clean). Exit 0 = cheap path applies → STOP; exit 3 =
a precondition failed → inspect, do not stop; exit 2 = usage error. It never writes a file, never touches
`data/raw`, never runs the extend. 8 regression tests in `tests/test_pre_gate_check.py`. No
threshold/gate/cost/universe/clock-gate logic touched.

## Pre-gate sessions (now < 2026-11-16T22:00:00Z) — cheap path, one call, then stop
```
GATE_EPOCH=1794866400 STATE_SHA256=c438cd71785459e2612e2dda3425d670de920a62de532c0dff2da6fe332b6365 \
  bash scripts/pre_gate_check.sh
```
- Exit 0 → cheap path applies: **STOP.** Do not re-run the full read-only cycle (it rewrites the handoff and burns ~2 min every 5 minutes); the durable pre-gate evidence already exists in `CORRECTIVE_HANDOFF_POSTGATE_20261116.md` (`Gate state: NOT released`). Do not launch a waiter, do not commit, do not start sessions.
- Exit 3 → a precondition failed (gate reached / hash drift / dirty `data/raw`): **inspect the message and act; do not blindly stop.** If the gate is released, fall through to Step 1/2 below.
- Exit 2 → usage error (missing env var, bad state file): fix and re-run.

## Step 1 — foreground idempotent check (first action at/after the gate)
Read `data/processed/paper_trading_state.yaml` → `last_run_date`, compare `date -u +%s` to the gate:
- Already `2026-11-16`: extension already ran → verify only (re-run Step 2's command once; expect `sessions extended: 0`, no state write).
- `2026-11-13` and now ≥ 2026-11-16T22:00:00Z: run Step 2.
- now < gate: run the one-call cheap path above and stop on exit 0.

## Step 2 — full gate cycle (only at/after the gate, state not yet advanced)
```
GATE_EPOCH=1794866400 PYTHON=/tmp/kilo-venv/bin/python RUFF=/tmp/kilo-venv/bin/ruff \
  bash scripts/post_gate_orchestrator.sh
```
Runs cmds 1–8 including the mutating extend (cmd2) and the idempotency re-run (cmd4), and rewrites
`CORRECTIVE_HANDOFF_POSTGATE_20261116.md` with `Mode: full cycle (extend included)` and
`Gate state: released (gate epoch reached)`. Then run the same command once more to confirm
idempotency (expect `sessions extended: 0`). The extend targets the next session after 2026-11-13,
i.e. **2026-11-16** (Mon); `session_is_complete` treats it as complete once local time ≥ 17:00 ET,
which is exactly 22:00 UTC (EST, UTC-5 — already covered by `tests/test_verify_monday_extension_path.py`).
Expect exactly one session appended and a single state write.

## Acceptance criteria
- [ ] Gate extension ran at/after 2026-11-16T22:00:00Z, in the foreground.
- [ ] Extends by <=1 session only if a completed bar exists; idempotent re-run extends 0 with 0 writes.
- [ ] `data/raw` untouched; no threshold/gate/cost/universe/clock-gate changes.
- [ ] Working tree shows only intended state/handoff/artifact changes; handoff `Status: OK`, `Mode: full cycle (extend included)`, `Gate state: released`, consistent with exit 0.

## Validation commands
- `GATE_EPOCH=1794866400 STATE_SHA256=c438cd71785459e2612e2dda3425d670de920a62de532c0dff2da6fe332b6365 bash scripts/pre_gate_check.sh` (pre-gate: exit 0; at/after gate: exit 3)
- `cat CORRECTIVE_HANDOFF_POSTGATE_20261116.md` (post-gate: `Status: OK`, `Mode: full cycle (extend included)`, `Gate state: released`, `Cmds run` includes `2 extend`)
- `git status --porcelain -- data/raw` (expect empty)
- `git status --porcelain` (only intended state/handoff changes)
- `python -m pytest -q tests/test_post_gate_orchestrator.py tests/test_pre_gate_check.py` (30 passed)

## Scope boundaries
- Do not run a mutating extend before the target session gate.
- Do not change thresholds/gates/cost model/universe/clock-gate logic; do not touch `data/raw/`.
- Do not commit manually; the controller checkpoints working-tree changes at session boundaries.
- Do not dispatch this workflow, start additional agent sessions, or launch a background waiter.
- Do not add another handoff per pre-gate session; the cheap path above exists precisely to stop that churn.

## Runtime note: `/tmp/kilo-venv` is ephemeral. If absent, recreate before running the cycle:
```
python3 -m venv /tmp/kilo-venv
/tmp/kilo-venv/bin/python -m pip install --no-cache-dir numpy pandas scipy statsmodels arch yfinance pyarrow pyyaml pytest ruff
```

## Session 23 verification summary (2026-11-14T03:49Z)
- Pre-gate check: **exit 0** (gate not released, state SHA256 matches, data/raw clean)
- Tests: **30 passed** (test_pre_gate_check.py + test_post_gate_orchestrator.py)
- `git status --porcelain -- data/raw`: **empty**
- `git status --porcelain`: **empty** (working tree clean)
- Current time: 1794628187 (2026-11-14T03:49:47Z) vs gate 1794866400 (2026-11-16T22:00:00Z) → **T-238213s (~66h)**
- State unchanged: `last_run_date 2026-11-13`, NAV `132654.46201168097`, run_history 469, SHA256 `c438cd71...`
- **Action taken**: STOP on pre-gate exit 0 (no full cycle re-run, no handoff churn)