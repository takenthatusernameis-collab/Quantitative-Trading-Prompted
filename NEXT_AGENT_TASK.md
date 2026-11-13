# Next Agent Task: run the 2026-11-13 gate extension

## Context
Verification of the repaired stale anchors is COMPLETE (all acceptance criteria met):
- `tests/test_tsmomentum_same_session_vol_correction.py`: 28 passed, exit 0
- `tests/test_tsmomentum_vol_estimate_consolidation.py`: 26 passed, exit 0
- `tests/test_tsmomentum_sma175_promotion_gate_eval.py`: 14 passed, exit 0
- `tests/test_reversal_001_erratum_001.py`: 4 passed, 1 skipped, exit 0
- Full `pytest tests/ -q`: 797 passed, 3 skipped, **0 failed**, exit 0 (3724.45s)
- Working tree clean at HEAD `499dfcc`; `data/raw/` untouched; no threshold/gate/cost/universe/clock-gate changes.

This session (2026-11-13T13:02 UTC, HEAD `690c9a5`, working tree clean): pre-gate verification re-run fresh — cmd1 date OK; cmd3 drift `stored == recomputed: True`, rolling 63d `-1.3137210439928235 (2026-11-12)`, tail ends `2026-11-12 -1.3137`, state sha `2dace0e3…dec88a` matches committed; cmd5 **68 passed in 42.41s**; cmd6 git status clean (0 lines, `data/` and `config/` clean); cmd8 ruff **All checks passed!** on the 4 extension scripts. State: last_run_date 2026-11-12, current_nav 133039.92504076837, run_history 468, rolling_sharpe_63d None. Gate epoch 1794607200 (22:00 UTC 2026-11-13) is NOT yet released (now ~13:02 UTC, ~9.0h remaining) — deterministic clock blocker, not a failure loop.

Corrective invocation 1 (2026-11-13T13:10 UTC, HEAD `9921f26`, uncommitted = 2 intended files): audited the gate-active orchestrator CLI for fail-closed defects and fixed three, each reproduced against the pre-fix script first — (A) unknown flags were silently ignored (`*) shift ;;`) so a typo'd `--wait-until-gate` would exit 3 "gate NOT released" with no visible cause; (B) `--max-wait-seconds 0` was accepted despite the "positive integer" claim (degrades to no-wait); (C) no `--help`/usage. Now rc=2 `FATAL: unknown argument` on any unknown flag, `0` rejected, and `-h|--help` prints usage (rc=0). 3 regression tests added; `tests/test_post_gate_orchestrator.py` **16 passed** (was 13); 6-module + orchestrator **84 passed in 43.88s**; `bash -n` OK; ruff clean on the test file; documented read-only cycle still exit 0 `Status: OK`; pre-gate extend is an offline no-op (`sessions extended: 0`, 0 writes, `data/raw` untouched); state sha `2dace0e3…dec88a` unchanged. Details: `CORRECTIVE_HANDOFF_CORR1_20261113T1310Z.md`.

The next step is the time-gated gate extension.

## Objective (next task, bounded)
At/after 22:00 UTC 2026-11-13 (epoch 1794607200), run the gate extension:
`GATE_EPOCH=1794607200 HANDOFF=CORRECTIVE_HANDOFF_POSTGATE_20261113.md bash scripts/post_gate_orchestrator.sh --wait-until-gate`
Extending by <=1 session only if a completed bar exists. The script is gate-guarded (exits 3 before release) and idempotent (re-run extends 0). Use `--wait-until-gate` so the gate-active run blocks until release rather than exiting 3.

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
GATE_EPOCH=1794607200 HANDOFF=CORRECTIVE_HANDOFF_POSTGATE_20261113.md bash scripts/post_gate_orchestrator.sh --wait-until-gate
git status --porcelain
```

## Scope boundaries
- Do not run before 22:00 UTC 2026-11-13 (time-gated).
- Do not change thresholds/gates/cost model/universe/clock-gate logic; do not touch `data/raw/`.
- Extend by <=1 session only if a completed bar exists.
