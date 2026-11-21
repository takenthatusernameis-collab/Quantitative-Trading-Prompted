# Paper-Trading Gate Unreachable: Structural Session/Gate Timing Mismatch

**Date:** 2026-11-21
**Status:** OPEN — blocked on a controller/human decision (not worker-fixable)
**Scope:** Diagnostic record only. No code, config, threshold, gate, cost, universe, or `data/raw` change.

## Summary

The daily paper-trading extension gate releases at **22:00 UTC** (e.g. 2026-11-21T22:00:00Z = epoch 1795298400). Worker sessions start ~**01:00–08:00 UTC** with ~**355-minute** (~5.9h) cutoffs. A session starting before ~16:05Z therefore always reaches its cutoff (~02:00–08:00Z next day) **before** the 22:00Z gate. As a result, the mutating post-gate cycle (`scripts/post_gate_orchestrator.sh`) is **structurally unreachable** from any session that starts before ~16:05Z, regardless of worker behavior.

This is a **deterministic workflow-level timing mismatch**, not a worker defect and not a failure loop.

## Evidence

- `scripts/pre_gate_check.sh` emits a machine-readable verdict from `SESSION_BUDGET_SECONDS`:
  - `GATE_REACHABLE=1` → gate within session budget (waitable).
  - `GATE_REACHABLE=0` → gate beyond budget (unreachable this session).
- Observed repeatedly (2026-11-16 → 2026-11-21, ~10 sessions): `GATE_REACHABLE=0`, pre-gate exit 0, state sha256 matches HEAD, `data/raw` clean. Verdicts recorded in `tmp_diag/gate-verdict_*.json`.
- 2026-11-21T00:15:31Z (epoch 1795220129) → gate 1795298400: T-78269s (~21.7h) remaining; `GATE_REACHABLE=0`; est. cutoff 2026-11-21T02:45:31Z < gate 2026-11-21T22:00:00Z.

## Approaches already tried (and why each is blocked/unsound)

1. **Foreground pre-gate-only run + handoff** — works (safe no-op), but never executes the real extension because no session overlaps 22:00Z. Produces doc/verdict churn without project progress.
2. **Detached `setsid` background waiter to bridge to 22:00Z** — proven UNSOUND (Cycle 1254): the CI job container is torn down at session end (~02:45Z); no detached process survives ~21.7h to the gate.
3. **Editing workflow scheduling** (session start times / gate time) to overlap — **FORBIDDEN** by scope boundaries (worker must not edit workflow scheduling; do not edit workflow scheduling or agent counts as a workaround for research tasks).

## Recommended resolution (controller/human decision)

One of the following resolves the blocker without weakening safety:

- **(A)** Schedule (or allow) a worker session whose start time is at/after **22:00 UTC** on a gate day, so the session budget covers the gate release and `GATE_REACHABLE=1` → the post-gate cycle runs once, then an idempotent re-run.
- **(B)** Redefine the gate time to fall within the existing session start/cutoff window.

Until then, the correct worker behavior is: run the cheap pre-gate path once, record the `GATE_REACHABLE=0` verdict, and hand off — **do not** run a mutating extend before the gate, and **do not** fabricate a partial cycle.

## Verification of this record

- Re-run in a session starting at/after ~16:05Z with `SESSION_BUDGET_SECONDS=<remaining>`:
  `GATE_EPOCH=<gate> STATE_SHA256=<baseline> SESSION_BUDGET_SECONDS=<budget> bash scripts/pre_gate_check.sh`
  - Expect `GATE_REACHABLE=1`; then `bash scripts/post_gate_orchestrator.sh` → `ORCH_EXIT=0`, and an idempotent re-run showing `sessions_extended: 0`.
- If `GATE_REACHABLE=0` persists even from a ≥16:05Z start, the timing model above is falsified and must be revised from fresh evidence.

## References

- `scripts/pre_gate_check.sh` (GATE_REACHABLE verdict logic)
- `scripts/post_gate_orchestrator.sh` (mutating cycle; must run only when released)
- `NEXT_AGENT_TASK.md` (durable findings: structural mismatch)
- `tmp_diag/gate-verdict_20261121.json` (latest pre-gate verdict)
- Cycle 1254 record (detached-waiter unsoundness)