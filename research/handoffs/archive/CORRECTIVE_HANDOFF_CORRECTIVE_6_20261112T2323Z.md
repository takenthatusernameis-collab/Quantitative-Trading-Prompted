# CORRECTIVE_HANDOFF — Corrective invocation 6 (2026-11-12T23:23Z)

## Why this invocation differs from prior ones
- Corrective invocations 2–5 either wrote handoff prose, re-verified an already-clean
  baseline, or fixed the hardcoded gate-date label (`GATE_HUMAN`, committed at `d27c6e9`).
- Inv5 explicitly recorded one **unresolved real defect** as the next bounded follow-up:
  "`--force` is only honored as the first CLI arg … make `--force` position-independent
  in the orchestrator arg loop, with a regression check."
- This invocation fixes exactly that defect and adds the missing regression check. It is a
  concrete code change with a test, not prose and not invented activity.

## Defect (evidence)
`scripts/post_gate_orchestrator.sh` parsed `--force` positionally:
```bash
if [[ "${1:-}" != "--force" ]]; then   # only a LEADING --force bypassed the clock gate
```
So `bash scripts/post_gate_orchestrator.sh --read-only --force` still hit the clock gate and
exited 3 before the gate. Demonstrated pre-fix:
```
$ GATE_EPOCH=4102444800 … bash scripts/post_gate_orchestrator.sh --read-only --force
clock gate NOT released (now=… target=4102444800); refusing to run   exit=3
```

## Change made (smallest sufficient, in scope)
`scripts/post_gate_orchestrator.sh` (5-line diff): parse `--force` into a `FORCE` flag in
the same arg loop and gate the pre-check on `if (( ! FORCE ))`. Default (no `--force`)
behavior is byte-for-byte equivalent; gate/threshold/cost/universe logic unchanged.
```diff
 READ_ONLY=0
+FORCE=0
 for arg in "$@"; do
   case "$arg" in
     --read-only) READ_ONLY=1 ;;
-    --force) : ;;  # consumed below
+    --force) FORCE=1 ;;
   esac
 done
-if [[ "${1:-}" != "--force" ]]; then
+if (( ! FORCE )); then
```
New test: `tests/test_post_gate_orchestrator.py` (4 cases) — default guard blocks before gate
(exit 3, no handoff), `--force` in second position bypasses gate (exit 0, handoff written),
`--force` first still bypasses, released gate default proceeds read-only.

## Verification (exact commands & observed outputs)
1. `bash -n scripts/post_gate_orchestrator.sh` → `SYNTAX_OK`
2. Regression test on FIXED script:
   `/tmp/kilo-venv/bin/python -m pytest tests/test_post_gate_orchestrator.py -q`
   → `4 passed in 0.27s`
3. Negative control — temporarily reverted to pre-fix logic, same test:
   → `1 failed, 3 passed` — `FAILED … test_force_second_position_bypasses_gate`
     `assert 3 != 3` (confirms the test catches the original bug). Script then restored
     from `/tmp/orch_fixed.sh` and re-verified `4 passed in 0.27s`.
4. Manual end-to-end on FIXED script, far-future gate, `--read-only --force`:
   `exit=0`, handoff written (bug gone).
5. `git status --porcelain` → only ` M scripts/post_gate_orchestrator.sh` and
   `?? tests/test_post_gate_orchestrator.py` (intended).
6. State integrity: `data/processed/paper_trading_state.yaml` SHA256
   `2dace0e3e1accf00a749cde2baf6470b5e2abc61e542fe636854910361dec88a` UNCHANGED,
   `last_run=2026-11-12`, `nav=133039.92504076837`, `runs=468`. `data/` and `config/` untouched.

## Unresolved blockers
- **Primary (time gate, not a defect):** the 2026-11-13 extension gate
  (epoch 1794607200 = 2026-11-13T22:00:00Z) is not released (~22.6h out at 2026-11-12T23:23Z).
  Per scope: do NOT run the mutating extend (cmd2) before the gate; do NOT re-extend 2026-11-12.
- No other known code/config defect in the orchestrator.

## Next distinct action (evidence-supported)
- At/after 2026-11-13T22:00:00Z run:
  `GATE_EPOCH=1794607200 HANDOFF=CORRECTIVE_HANDOFF_POSTGATE_20261113.md bash scripts/post_gate_orchestrator.sh`
  (fallback: manual cmds 1–8 from `NEXT_AGENT_TASK.md`). Extend by ≤1 session to 2026-11-13
  only if a completed bar exists; else `sessions_extended==0`, 0 writes. Record results in the
  durable in-repo handoff.
- Optional separate bounded follow-up (do NOT bundle with the gate run): make the orchestrator
  capture per-command pass/fail and exit non-zero on any failed check, so the handoff is
  self-evidencing (currently it always exits 0 even if a sub-check fails). Distinct task.

## Safety
No alpha/promotion claims. No live trading, secrets, credentials, or account access.
Research pre-registrations, promotion gates, security controls, workflow boundaries, and user
data preserved. Gate/threshold/cost/universe logic unchanged. No commit made (awaiting user).