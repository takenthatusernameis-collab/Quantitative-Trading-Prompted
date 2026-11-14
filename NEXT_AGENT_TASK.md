# Next Agent Task: execute the 2026-11-16 gate extension in the FOREGROUND (the detached waiter cannot survive)

## Context — verified baseline (2026-11-14T02:46Z, session 19 inv 1; run 43522470160 attempt 1)
The 2026-11-13 gate extension is COMPLETE and committed; HEAD `b839070`.
- State: `last_run_date 2026-11-13`, `current_nav 132654.46201168097`, `run_history` 469, SHA256 `c438cd71785459e2612e2dda3425d670de920a62de532c0dff2da6fe332b6365` — re-verified unchanged at 02:46Z (this session).
- `date -u +%s` = 1794624403 < gate 1794866400 (2026-11-16T22:00:00Z): **~67h (T-241997s) before the gate**. `data/raw` untouched (`git status --porcelain -- data/raw` empty). `/tmp/kilo-venv` present. No background waiter running.
- Pre-gate cheap verification this session (02:46Z): state hash matches, `data/raw` clean — **stopped per cheap path** (did not re-run full read-only cycle).

## Change made this session (only non-handoff change)
`scripts/post_gate_orchestrator.sh` now writes a `- **Gate state:**` line into the durable handoff
(`NOT released — pre-gate verification run only (...); mutating extend withheld` before the gate,
`released (gate epoch reached)` at/after it), because a `--force --read-only` pre-gate run wrote a
handoff indistinguishable from post-gate evidence. Two regression tests added
(`tests/test_post_gate_orchestrator.py`, 22 passed). No threshold/gate/cost/universe/clock-gate
logic touched.

## Pre-gate sessions (now < 2026-11-16T22:00:00Z) — cheap path, do this and stop
1. `date -u +%s` and `sha256sum data/processed/paper_trading_state.yaml`.
2. If hash == `c438cd71785459e2612e2dda3425d670de920a62de532c0dff2da6fe332b6365` and `git status --porcelain -- data/raw` is empty: **stop.** Do not re-run the full read-only cycle (it rewrites the handoff and burns ~2 min every 5 minutes); the durable pre-gate evidence already exists in `CORRECTIVE_HANDOFF_POSTGATE_20261116.md` (`Gate state: NOT released`). Do not launch a waiter, do not commit, do not start sessions.

## Step 1 — foreground idempotent check (first action at/after the gate)
Read `data/processed/paper_trading_state.yaml` → `last_run_date`, compare `date -u +%s` to the gate:
- Already `2026-11-16`: extension already ran → verify only (re-run Step 2's command once; expect `sessions extended: 0`, no state write).
- `2026-11-13` and now ≥ 2026-11-16T22:00:00Z: run Step 2.
- now < gate: follow the cheap pre-gate path above.

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
- `cat CORRECTIVE_HANDOFF_POSTGATE_20261116.md` (post-gate: `Status: OK`, `Mode: full cycle (extend included)`, `Gate state: released`, `Cmds run` includes `2 extend`)
- `git status --porcelain -- data/raw` (expect empty)
- `git status --porcelain` (only intended state/handoff changes)
- `python -m pytest -q tests/test_post_gate_orchestrator.py` (22 passed)

## Scope boundaries
- Do not run a mutating extend before the target session gate.
- Do not change thresholds/gates/cost model/universe/clock-gate logic; do not touch `data/raw/`.
- Do not commit manually; the controller checkpoints working-tree changes at session boundaries.
- Do not dispatch this workflow, start additional agent sessions, or launch a background waiter.
- Do not add another handoff per pre-gate session; the cheap path above exists precisely to stop that churn.

Runtime note: `/tmp/kilo-venv` is ephemeral. If absent, recreate before running the cycle:
```
python3 -m venv /tmp/kilo-venv
/tmp/kilo-venv/bin/python -m pip install --no-cache-dir numpy pandas scipy statsmodels arch yfinance pyarrow pyyaml pytest ruff
```