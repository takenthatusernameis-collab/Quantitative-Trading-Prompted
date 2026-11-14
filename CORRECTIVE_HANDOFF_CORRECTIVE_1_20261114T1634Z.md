# Corrective Invocation 1 — handoff (2026-11-14T16:34Z)

## What this invocation changed (durable, project code — not handoff churn)

`scripts/post_gate_orchestrator.sh` now validates `GATE_EPOCH` itself, immediately after it
is resolved and **before** any `date -u -d "@$GATE_EPOCH"` call or `(( now_epoch < GATE_EPOCH ))`
arithmetic can consume it:

```
if ! [[ "$GATE_EPOCH" =~ ^[0-9]+$ ]]; then
  echo "FATAL: GATE_EPOCH must be a non-negative integer epoch, got '$GATE_EPOCH'" >&2
  exit 2
fi
```

### Root cause (why this was the smallest justified correction)
The sibling checker `scripts/pre_gate_check.sh` already guards `GATE_EPOCH`
(`[[ "$GATE_EPOCH" =~ ^[0-9]+$ ]] || exit 2`). The orchestrator had **no** such guard.
The natural partial invocation is to override only `GATE_EPOCH` (the pattern
`NEXT_AGENT_TASK.md` documents and the tests exercise), so a malformed value
(`GATE_EPOCH=17948_66400`, `-1`, quoted blank, `17948 66400`) previously flowed into:
- `date -u -d "@$GATE_EPOCH"` → bogus/garbage `GATE_HUMAN` and `GATE_DATE`, which then
  derive the durable handoff filename `CORRECTIVE_HANDOFF_POSTGATE_${GATE_DATE}.md`; and
- `(( now_epoch < GATE_EPOCH ))` → a non-numeric string is treated as **0** by bash
  arithmetic, so the clock gate reads as permanently released.

Net effect: a typo could open the gate, run the mutating extend out of schedule, and write
that evidence into a mis-dated durable record — a clock-gate and evidence-integrity hazard,
i.e. exactly the class this script exists to prevent. This is not a threshold/gate-value
change: the accepted epoch values are unchanged, only malformed input is now rejected.

## Verification (exact commands and observed output)

1. `GATE_EPOCH=17948_66400 ... bash scripts/post_gate_orchestrator.sh --read-only`
   → `exit 2`, stderr `FATAL: GATE_EPOCH must be a non-negative integer epoch, got '17948_66400'`,
   no handoff written. (Pinned by `test_non_numeric_gate_epoch_is_usage_error`.)
2. Negative epoch → `exit 2`, same FATAL, no handoff
   (`test_negative_gate_epoch_is_usage_error`).
3. `/tmp/kilo-venv/bin/python -m pytest -q tests/test_post_gate_orchestrator.py tests/test_pre_gate_check.py`
   → **41 passed** (was 39; +2 new).
4. Mutation check: guard block deleted → **2 failed, 30 passed** (the malformed gate silently
   ran the cycle and exited 0 with `cycle complete`); guard restored → 41 passed.
5. `/tmp/kilo-venv/bin/ruff check tests/test_post_gate_orchestrator.py` → `All checks passed!`
   (`scripts/*.sh` are shell, not python; ruff on the `.sh` reports pre-existing shell lint,
   unrelated to this change.)
6. `GATE_EPOCH=1794866400 STATE_SHA256=c438cd71785459e2612e2dda3425d670de920a62de532c0dff2da6fe332b6365 bash scripts/pre_gate_check.sh`
   → `PRE-GATE OK ... EXIT=0` (now 2026-11-14T16:34:42Z < gate 2026-11-16T22:00:00Z,
   T-192318s; `data/raw` clean). Gate remains unreleased — **the full cycle was NOT run.**
7. `git status --porcelain -- data/raw` → 0 lines (raw data untouched).

## Unresolved blockers / next distinct step
- The Step-2 full gate cycle (cmds 1–9 incl. mutating extend + idempotency re-run) still
  cannot execute before the gate: `GATE_EPOCH=1794866400` = 2026-11-16T22:00:00Z, ~2.22 days
  out from this run. That is a deterministic clock blocker, not a failure loop.
- Next distinct action (at/after the gate, by the then-active run):
  `GATE_EPOCH=1794866400 PYTHON=/tmp/kilo-venv/bin/python RUFF=/tmp/kilo-venv/bin/ruff bash scripts/post_gate_orchestrator.sh`,
  then re-run once for idempotency (`sessions extended: 0`, no second state write).
- Preserved unchanged: thresholds, cost model, universe, clock-gate values, promotion gates,
  pre-registrations, `data/raw`, security controls, workflow boundaries (no dispatch, no
  background waiter). State unchanged: `last_run_date 2026-11-13`,
  `c438cd71…b6365`, nav `132654.46201168097`, `run_history` 469.

## Prior failed approaches (do not repeat)
Read-only pre-gate cycles that commit only a handoff timestamp; the refuted "piped-to-tail
masks failures" theory; the refuted hard-fail-on-empty-`STATE_SHA` over-reach; the Cycle-1260
`last_run=None` guard hole (already fixed). This invocation instead fixes a concrete,
previously-unguarded validation hole with a mutation-proven regression test.