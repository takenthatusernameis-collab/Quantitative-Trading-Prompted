# Next Agent Task: run the 2026-11-13 gate extension

## Context
Verification of the repaired stale anchors is COMPLETE (all acceptance criteria met):
- `tests/test_tsmomentum_same_session_vol_correction.py`: 28 passed, exit 0
- `tests/test_tsmomentum_vol_estimate_consolidation.py`: 26 passed, exit 0
- `tests/test_tsmomentum_sma175_promotion_gate_eval.py`: 14 passed, exit 0
- `tests/test_reversal_001_erratum_001.py`: 4 passed, 1 skipped, exit 0
- Full `pytest tests/ -q`: 797 passed, 3 skipped, **0 failed**, exit 0 (3724.45s)
- Working tree clean at HEAD `499dfcc`; `data/raw/` untouched; no threshold/gate/cost/universe/clock-gate changes.

The next step is the time-gated gate extension.

## Objective (next task, bounded)
At/after 22:00 UTC 2026-11-13 (epoch 1794607200), run the gate extension:
`GATE_EPOCH=1794607200 HANDOFF=CORRECTIVE_HANDOFF_POSTGATE_20261113.md bash scripts/post_gate_orchestrator.sh`
Extending by <=1 session only if a completed bar exists. The script is gate-guarded (exits 3 before release) and idempotent (re-run extends 0).

## Acceptance criteria
- [ ] Gate extension runs at/after 22:00 UTC 2026-11-13 (or correctly exits 3 if invoked before release)
- [ ] Extends by <=1 session only if a completed bar exists; idempotent re-run extends 0
- [ ] `data/raw/` untouched; no threshold/gate/cost/universe/clock-gate changes
- [ ] Working tree shows only intended state/report changes (no code/config changes)

## Validation commands
```
# Before gate: confirm guard (expect EXIT=3, "clock gate NOT released")
GATE_EPOCH=1794607200 bash scripts/post_gate_orchestrator.sh
# At/after 22:00 UTC 2026-11-13:
GATE_EPOCH=1794607200 HANDOFF=CORRECTIVE_HANDOFF_POSTGATE_20261113.md bash scripts/post_gate_orchestrator.sh
git status --porcelain
```

## Scope boundaries
- Do not run before 22:00 UTC 2026-11-13 (time-gated).
- Do not change thresholds/gates/cost model/universe/clock-gate logic; do not touch `data/raw/`.
- Extend by <=1 session only if a completed bar exists.
