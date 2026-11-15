# Corrective Handoff — inv 325 (2026-11-15T12:08Z)

## Blocker (unchanged, deterministic)
Gate `GATE_EPOCH=1794866400` = 2026-11-16T22:00:00Z is T-130628s (~36.3h) out at
2026-11-15T12:08Z. The 355-minute cutoff (~5.9h) cannot reach it. Step 2 (mutating
extend + idempotency re-run in `scripts/post_gate_orchestrator.sh`) is withheld by
scope boundaries, not failed. No code change can release the clock gate early.

## Materially different correction this run
Prior corrective invocations (324 included) re-ran the pre-gate cheap path and the
focused test suite — a read-only re-verification that cannot produce durable project
progress while the gate is unreached. This run inspected the orchestrator's own
behavior against the committed test suite and found a **coverage gap, not a code
defect**: the `--wait-until-gate` happy path (block until the gate releases, then run
the cycle) had never been exercised by any test. Both committed tests used either a
FUTURE_GATE (never reached → exit 3) or a PAST_GATE (already released → no wait), so
the wait-then-release branch was unverified. A regression there (sleeping past the
deadline, or exiting before running) would pass the suite.

**Smallest sufficient change:** added one regression test,
`tests/test_post_gate_orchestrator.py::test_wait_until_gate_blocks_then_releases_and_runs_cycle`.
It derives the gate epoch at call time (3s ahead, so it cannot go stale as wall-clock
advances), pins the wait budget to the remaining span + 2s, and asserts the real
happy-path markers: `waiting up to`, `clock gate released after wait`, exit 0, the
handoff exists, `- **Gate state:** released (gate epoch reached)`, and the gate epoch
line. Verified green against the real script with real interpreters.

## Evidence produced this run
- `verify_gate_time_forward_bar.py` → **RESULT: PASS**, exit 0. Real extension path
  (fetch → run_simulation → single state write) against a synthetic 2026-11-16
  forward bar; `sessions_extended: 1`, `state_writes: 1`, `nav_after 132843.97`,
  canonical state hash unchanged, tracked report hash unchanged.
- `research/audit_state_aggregates.py` → **all_match: True**, exit 0 (469 sessions,
  11 aggregate fields recomputed from `run_history`).
- `research/drift_persistence_report.py` → exit 0; `stored == recomputed: True`;
  persistence 13 days (2026-10-28 → 2026-11-13), rolling 63d Sharpe -1.4833.
- `--wait-until-gate` happy path exercised end-to-end against real interpreters
  (`/tmp/kilo-venv/bin/python`, `/tmp/kilo-venv/bin/ruff`): blocked, released at the
  gate, ran the full read-only cycle (cmds 1,3,5,6,7,8,9), wrote the handoff with
  `Status: OK`, `Mode: read-only verification`, `Gate state: released`, exit 0.
- **Full test suite: 854 passed, 3 skipped, exit 0** in 3728.90s
  (`/tmp/kilo-venv/bin/python -m pytest -q -p no:cacheprovider`).
- `ruff check tests/test_post_gate_orchestrator.py` → **All checks passed!**
- `git status --porcelain -- data/raw` → empty; state sha256 unchanged
  `c438cd71…`; working tree shows only the intended test addition.

## Unresolved blocker
The mutating extend (Step 2) remains gated on the deterministic clock. Next distinct
action: run Step 2 at/after 2026-11-16T22:00:00Z, then the idempotency re-run.