# Next Agent Task: run the 2026-11-13 gate extension (gate-active)

## Context
Pre-gate verification is COMPLETE and re-verified fresh this session (2026-11-13T14:45 UTC, HEAD `47b1ab2`, working tree contains only the intended cycle-1253 fix):

| Cmd | Result |
|-----|--------|
| 0 `post_gate_orchestrator.sh` (no wait) | `clock gate NOT released ...; refusing to run` → **EXIT=3** |
| 1 `date -u && TZ=America/New_York date` | `Fri Nov 13 14:45 UTC 2026 / 09:45 EST`; gate releases 22:00 UTC (epoch 1794607200), ~7.25h out |
| 3 `drift_persistence_report.py` | `stored == recomputed: True`; rolling 63d `-1.3137210439928235 (2026-11-12)`; tail ends `2026-11-12 -1.3137`; state sha `2dace0e3…dec88a` matches committed |
| 5 6-module pytest | **68 passed in 42.04s** |
| 6 `git status --porcelain data/ config/` | **0 lines** (clean) |
| 8 `ruff` on 4 extension scripts | **All checks passed!** |
| 9 `research/verify_monday_extension_path.py` | `RESULT: PASS` (committed 2026-11-10 NAV reproduced bit-for-bit) |
| 10 `research/verify_gate_time_forward_bar.py` | `RESULT: PASS` (target 2026-11-13, `sessions_extended 1`, `state_writes 1`, `fetch_error None`, canonical state + tracked report unchanged) |

Cycle 1253 fixed a durable-evidence defect in `scripts/post_gate_orchestrator.sh`: overriding only `GATE_EPOCH` used to write the 2026-11-12 handoff file with the new gate's content. The default handoff is now derived from `GATE_EPOCH`, and an explicit `HANDOFF` naming a different gate date fails closed (rc=2). Orchestrator suite **20 passed** (was 16). Those two files are **uncommitted** (no commit requested); `cmd6 git status` will list them until committed — expected, not a scope violation.

Durable handoff: `CORRECTIVE_HANDOFF_POSTGATE_20261113.md` (inv131 section has the full evidence).

## Objective (bounded)
At/after 22:00 UTC 2026-11-13 (epoch 1794607200), run the gate extension:
```bash
GATE_EPOCH=1794607200 bash scripts/post_gate_orchestrator.sh --wait-until-gate
```
This blocks (60s heartbeat) until release, then runs cmds 1–8. It writes `CORRECTIVE_HANDOFF_POSTGATE_20261113.md` by default. Extends by <=1 session only if a completed bar exists; idempotent (re-run extends 0). `HANDOFF=` may be set only to a filename whose embedded date matches the gate (20261113).

## Acceptance criteria
- [ ] Gate extension runs at/after 22:00 UTC 2026-11-13 (or correctly exits 3 if invoked before release without `--wait-until-gate`)
- [ ] Extends by <=1 session only if a completed bar exists; idempotent re-run extends 0 and writes no second state update
- [ ] `data/raw/` untouched; no threshold/gate/cost/universe/clock-gate changes
- [ ] Working tree shows only intended state/report changes plus the cycle-1253 fix (script + test); no other code/config changes
- [ ] Handoff `Status: OK` agrees with process exit code 0

## Validation commands
```bash
# Before gate: confirm guard (expect EXIT=3, "clock gate NOT released")
GATE_EPOCH=1794607200 bash scripts/post_gate_orchestrator.sh
# At/after 22:00 UTC 2026-11-13 (blocks until release, then runs cmds 1-8):
GATE_EPOCH=1794607200 bash scripts/post_gate_orchestrator.sh --wait-until-gate
# Idempotency re-check (expect "sessions extended: 0", state write count 0):
GATE_EPOCH=1794607200 bash scripts/post_gate_orchestrator.sh
git status --porcelain
sha256sum data/processed/paper_trading_state.yaml
```
After a real advance also re-run `python research/drift_persistence_report.py` (tail must end on the new session) and the 6-module pytest.

## Scope boundaries
- Do not run the mutating extend before 22:00 UTC 2026-11-13 (time-gated).
- Do not change thresholds/gates/cost model/universe/clock-gate logic; do not touch `data/raw/`.
- Extend by <=1 session only if a completed bar exists.
- Do not rewrite this cycle's history; append evidence only.