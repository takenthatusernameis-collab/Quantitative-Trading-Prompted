# Next Agent Task: run the next calendar-session gate extension (gate-active)

## Context
The 2026-11-13 gate extension is COMPLETE and verified (corrective invocation 2, 2026-11-13T22:05Z):

- Gate released 2026-11-13T22:00:00Z (epoch 1794607200); orchestrator `scripts/post_gate_orchestrator.sh --wait-until-gate` ran cmds 1–8.
- Extend: `sessions extended: 1`, `state write count: 1`, NAV `133039.92504076837` → `132654.46201168097`, `data/raw` untouched.
- Idempotent re-run: `sessions extended: 0`, `state write count: 0`, `ORCH_RC=0`.
- Drift tail ends `2026-11-13 -1.4833`; 6-module pytest `68 passed`; inventory pytest `41 passed`; ruff clean; inventory 002 `DECISION NO-GO` (incumbent unchanged).
- State: `last_run_date 2026-11-13`, `current_nav 132654.46201168097`, runs 469, SHA `c438cd71…`.
- Durable handoff: `CORRECTIVE_HANDOFF_POSTGATE_20261113.md` (full evidence + appended corrective-invocation-2 section). Pre-gate evidence preserved in `CORRECTIVE_HANDOFF_POSTGATE_20261113_pregate_backup.md`.
- Changes are uncommitted on disk (no commit performed; do not commit unless explicitly asked).

Runtime note: the venv `/tmp/kilo-venv` was (re)provisioned this session on Python 3.14 with the full required set. It is ephemeral (`/tmp`); if a future session finds it absent, recreate it before running the cycle:
```bash
python3 -m venv /tmp/kilo-venv
/tmp/kilo-venv/bin/python -m pip install --no-cache-dir numpy pandas scipy statsmodels arch yfinance pyarrow pyyaml pytest ruff
```

## Objective (bounded)
At/after the next calendar-session gate, run the same idempotent cycle. The last processed session is 2026-11-13 (Friday); the next weekday session is Monday 2026-11-16. Determine the gate epoch for that session and run:
```bash
GATE_EPOCH=<next-session-gate-epoch> PYTHON=/tmp/kilo-venv/bin/python RUFF=/tmp/kilo-venv/bin/ruff \
  bash scripts/post_gate_orchestrator.sh --wait-until-gate
```
Because a single invocation is bounded by a 600s idle timeout, launch it detached so it survives teardown (this is the pattern that worked):
```bash
setsid env GATE_EPOCH=<epoch> PYTHON=/tmp/kilo-venv/bin/python RUFF=/tmp/kilo-venv/bin/ruff \
  bash scripts/post_gate_orchestrator.sh --wait-until-gate > /tmp/gate_waiter.log 2>&1 < /dev/null &
```
then stay alive with sub-600s heartbeats to verify the post-gate result. Default handoff filename derives from the gate date (`CORRECTIVE_HANDOFF_POSTGATE_<YYYYMMDD>.md`).

## Acceptance criteria
- [ ] Gate extension runs at/after the next session gate (or correctly exits 3 if invoked early without `--wait-until-gate`).
- [ ] Extends by <=1 session only if a completed bar exists; idempotent re-run extends 0 with 0 writes.
- [ ] `data/raw/` untouched; no threshold/gate/cost/universe/clock-gate changes.
- [ ] Working tree shows only intended state/report/artifact changes; handoff `Status: OK` agrees with exit 0.

## Scope boundaries
- Do not run a mutating extend before the target session gate.
- Do not change thresholds/gates/cost model/universe/clock-gate logic; do not touch `data/raw/`.
- Do not commit unless explicitly asked.
- Do not dispatch this workflow or start additional agent sessions.