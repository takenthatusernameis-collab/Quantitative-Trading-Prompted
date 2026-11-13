# CORRECTIVE_HANDOFF — Corrective invocation 393 (2026-11-13T00:17Z)

## Why this invocation differs from prior ones
Prior corrective invocations: 2–5 wrote prose or re-verified a clean baseline; inv6 fixed
`--force` position-independence (committed `d304bfd`). The most recent session-6 attempt
added an optional `--wait-until-gate` mode to the orchestrator but exited status 1 at the
API level before verifying or recording anything durable.

This invocation (a) verified the on-disk wait-mode work with the full relevant suite, and
(b) makes a **materially different, evidence-backed correction**: the orchestrator previously
**always exited 0 and wrote "cycle complete" even when a sub-check failed**. It now captures
each step's exit status and exits non-zero + marks the handoff FAILED on any failure. This was
flagged as the next distinct follow-up in `CORRECTIVE_HANDOFF_CORRECTIVE_6_20261112T2323Z.md`
("make the orchestrator capture per-command pass/fail and exit non-zero on any failed check …
currently it always exits 0 even if a sub-check fails").

## Changes made (smallest sufficient, in scope)
1. `scripts/post_gate_orchestrator.sh`:
   - Added `FAILED=0` + `record_rc <rc> <label>` helper (sets `FAILED=1`, logs
     `STEP FAILED (rc=…)` on non-zero).
   - Wrapped every step (cmd1, cmd3, cmd5, cmd6, cmd7a/b/c, cmd8, and cmd2/cmd4 when not
     read-only) with `record_rc $?` so failures are captured. Gate/threshold/cost/universe/
     clock logic is unchanged.
   - Handoff now carries a `Status:` line (`OK …` or `FAILED …`) and the script exits `1`
     when `FAILED=1` (previously always `exit 0`).
   - (Pre-existing on-disk, now verified:) `--wait-until-gate` / `--max-wait-seconds N`
     bounded wait mode, gated by the run cutoff.
2. `tests/test_post_gate_orchestrator.py`:
   - `_run` gained an optional `env_extra` override and `check=False` (ruff PLW1510).
   - Added `test_failed_subcheck_exits_nonzero_and_marks_handoff` (PYTHON/RUFF=false →
     exit 1, handoff `FAILED`, `STEP FAILED` in log) and
     `test_successful_cycle_marks_handoff_ok` (exit 0, handoff `OK`).
3. `README.md` / `NEXT_AGENT_TASK.md`: Cycle 1246 status (wait-mode) already on disk from the
   prior attempt; left as-is except this handoff records the new pass/fail-capture change.
   (No prose rewrite beyond this handoff, to avoid inventing activity.)

## Verification (exact commands & observed outputs)
1. `bash -n scripts/post_gate_orchestrator.sh` → `BASH_OK`.
2. `/tmp/kilo-venv/bin/python -m pytest tests/test_post_gate_orchestrator.py -q`
   → **9 passed in 1.58s** (4 original + 3 wait-mode + 2 new pass/fail-capture cases).
3. Negative control (failing sub-checks):
   `PYTHON=false RUFF=false GATE_EPOCH=1794520800 HANDOFF=/tmp/h_fail.md bash scripts/post_gate_orchestrator.sh --read-only`
   → `ORCHESTRATOR_EXIT=1`; log lines `STEP FAILED (rc=1): cmd3 drift / cmd5 6-module pytest
   / cmd7a / cmd7b / cmd7c / cmd8 ruff`; handoff `Status: FAILED — one or more verification
   steps failed …`. Confirms the mask defect is fixed (previously would have been exit 0).
4. Positive control (all checks pass):
   `PYTHON=true RUFF=true … --read-only` → `EXIT=0`; handoff `Status: OK — all verification
   steps passed`; log `cycle complete`.
5. 6-module suite:
   `/tmp/kilo-venv/bin/python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py tests/test_state_aggregate_audit.py tests/test_rolling_63d_gate_refresh.py -q`
   → **68 passed in 28.24s**.
6. `/tmp/kilo-venv/bin/ruff check research/drift_persistence_report.py research/extend_paper_trading_state.py research/verify_monday_extension_path.py research/verify_gate_time_forward_bar.py`
   → `All checks passed!`
7. `/tmp/kilo-venv/bin/ruff check tests/test_post_gate_orchestrator.py` → `All checks passed!`
8. Gate guard (unchanged): `GATE_EPOCH=1794607200 … --wait-until-gate --max-wait-seconds 1`
   → waits 1s, `wait budget exhausted`, `EXIT=3`.
9. State integrity: `data/processed/paper_trading_state.yaml` SHA256
   `2dace0e3e1accf00a749cde2baf6470b5e2abc61e542fe636854910361dec88a` UNCHANGED,
   `last_run=2026-11-12`, `nav=133039.92504076837`, `runs=468`.
10. `git status --porcelain` → only ` M NEXT_AGENT_TASK.md`, ` M README.md`,
    ` M scripts/post_gate_orchestrator.sh`, ` M tests/test_post_gate_orchestrator.py`.
    `data/` and `config/` untouched.

## Unresolved blockers
- **Primary (time gate, not a defect):** the 2026-11-13 extension gate (epoch 1794607200 =
  2026-11-13T22:00:00Z) is NOT released. At 2026-11-13T00:16Z it is ~21.7h out. This run's
  controller cutoff is `remaining_seconds=14082` (~3.9h) — BEFORE the gate. Per scope: do
  NOT run the mutating extend (cmd2) before the gate; do NOT re-extend 2026-11-12 (already
  complete and committed).
- No other known code/config defect in the orchestrator. The pass/fail-capture defect is now
  fixed and tested.

## Next distinct action (evidence-supported)
- At/after 2026-11-13T22:00:00Z, from the run active across the gate:
  `GATE_EPOCH=1794607200 HANDOFF=CORRECTIVE_HANDOFF_POSTGATE_20261113.md bash scripts/post_gate_orchestrator.sh --wait-until-gate`
  (the new failure capture makes the resulting handoff self-evidencing: `Status: OK/FAILED`).
  Extend by ≤1 session to 2026-11-13 only if a completed bar exists; else `sessions_extended==0`,
  0 writes. Fallback: manual cmds 1–8 from `NEXT_AGENT_TASK.md`.
- Optional distinct follow-up (do NOT bundle with the gate run): add a regression that asserts
  the handoff `Status:` line matches the exit code across mixed pass/fail (currently covered
  only by the two single-mode controls).

## Safety
No alpha/promotion claims. No live trading, secrets, credentials, or account access.
Research pre-registrations, promotion gates, security controls, workflow boundaries, and user
data preserved. Gate/threshold/cost/universe/clock logic unchanged. No commit made (user
instruction); working-tree changes are the intended deliverable.