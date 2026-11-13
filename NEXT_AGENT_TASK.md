# Next Agent Task: run the 2026-11-13 gate extension (gate-active)

## Context
Pre-gate verification for the 2026-11-13 gate (epoch 1794607200 = 22:00 UTC 2026-11-13) is COMPLETE and re-verified fresh this session (2026-11-13T14:25 UTC, HEAD `bb2632e`, working tree clean):

| Cmd | Result |
|-----|--------|
| 0 `post_gate_orchestrator.sh` (no wait) | `clock gate NOT released ...; refusing to run` → **EXIT=3** |
| 1 `date -u && TZ=America/New_York date` | `Fri Nov 13 14:25:38 UTC 2026 / Fri Nov 13 09:25:38 EST 2026` |
| 3 `drift_persistence_report.py` | `stored == recomputed: True`; rolling 63d `-1.3137210439928235 (2026-11-12)`; tail ends `2026-11-12 -1.3137`; state sha `2dace0e3…dec88a` matches committed |
| 5 6-module pytest | **68 passed in 42.05s** |
| 6 `git status --porcelain data/ config/` | **0 lines** (clean) |
| 8 `ruff` on 4 extension scripts | **All checks passed!** |

Fail-closed CLI fixes from corrective invocation 1 (HEAD `9921f26`) re-verified this session: unknown flag → rc=2; `--max-wait-seconds 0` → rc=2; `-h|--help` → rc=0. `tests/test_post_gate_orchestrator.py` 16 passed.

Durable handoff `CORRECTIVE_HANDOFF_POSTGATE_20261113.md` updated with the fresh evidence above.

## Objective (next task, bounded)
At/after 22:00 UTC 2026-11-13 (epoch 1794607200), run the gate extension:
```bash
GATE_EPOCH=1794607200 HANDOFF=CORRECTIVE_HANDOFF_POSTGATE_20261113.md \
  bash scripts/post_gate_orchestrator.sh --wait-until-gate
```
Extends by <=1 session only if a completed bar exists. The script is gate-guarded (exits 3 before release) and idempotent (re-run extends 0). Use `--wait-until-gate` so the gate-active run blocks until release rather than exiting 3.

## Acceptance criteria
- [ ] Gate extension runs at/after 22:00 UTC 2026-11-13 (or correctly exits 3 if invoked before release)
- [ ] Extends by <=1 session only if a completed bar exists; idempotent re-run extends 0
- [ ] `data/raw/` untouched; no threshold/gate/cost/universe/clock-gate changes
- [ ] Working tree shows only intended state/report changes (no code/config changes)

## Validation commands
```bash
# Before gate: confirm guard (expect EXIT=3, "clock gate NOT released")
GATE_EPOCH=1794607200 bash scripts/post_gate_orchestrator.sh
# At/after 22:00 UTC 2026-11-13:
GATE_EPOCH=1794607200 HANDOFF=CORRECTIVE_HANDOFF_POSTGATE_20261113.md bash scripts/post_gate_orchestrator.sh --wait-until-gate
git status --porcelain
```

## Scope boundaries
- Do not run before 22:00 UTC 2026-11-13 (time-gated).
- Do not change thresholds/gates/cost model/universe/clock-gate logic; do not touch `data/raw/`.
- Extend by <=1 session only if a completed bar exists.