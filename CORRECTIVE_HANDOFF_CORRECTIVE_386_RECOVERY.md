# Corrective Handoff — CORRECTIVE_386 recovery (2026-11-15T09:41Z)

## Materially different approach from prior failed invocations
Every prior corrective invocation in this cycle re-ran the same acceptance-verification
suite (extend script, drift report, pytest) and re-documented the deterministic clock
blocker, producing no durable project change. This invocation instead inspected the
committed guards themselves for an internal inconsistency and found one: the two
committed fingerprint/consistency guards disagreed on the NAV pattern.

## Defect found and fixed
- **Location:** `tests/test_post_gate_handoff_consistency.py:38` (`_STATE_LINE`).
- **Root cause:** `scripts/post_gate_orchestrator.sh:345` was loosened in inv-228 to
  accept a negative NAV (`nav=-?[0-9]+\.?[0-9]*`) because `current_nav` is a float and a
  paper account can legitimately fall below zero. The committed consistency guard was
  NOT loosened at the same time and still required `nav=[0-9]+(?:\.[0-9]+)?`.
- **Consequence:** once the paper NAV goes negative, the real post-gate cycle would write
  a handoff with `nav=-1234.56`, and the very next gate cycle's committed consistency
  guard would REJECT it (`test_state_line_present_and_matches_real_state_file` fails on
  the regex), failing the acceptance verification of a handoff the orchestrator itself
  produced. The two guards disagreed on the same field.
- **Fix (smallest sufficient):** loosen `_STATE_LINE`'s nav to `nav=-?[0-9]+(?:\.[0-9]+)?`,
  matching the orchestrator's pattern. Added 4 regression tests:
  `test_negative_float_nav_handoff_is_consistent`, `test_negative_integer_nav_handoff_is_consistent`,
  `test_double_minus_nav_handoff_is_rejected`, `test_non_numeric_nav_handoff_is_rejected`.
- **Mutation-checked:** reverting the nav pattern to the pre-fix `[0-9]+...` fails both
  "negative NAV must pass" tests (`assert None`); loosening nav to `.*` fails both
  "malformed must be rejected" tests. Both mutations are caught, so the new tests are
  genuine regression guards, not vacuity. Also fixed a `ruff` FURB167 (`re.M` ->
  `re.MULTILINE`) in the new helper.
- **Scope:** test-only. No production code, threshold, gate, cost model, universe,
  `data/raw`, or state file touched.

## Verification (fresh, this run)
- Pre-gate cheap path:
  `GATE_EPOCH=1794866400 STATE_SHA256=c438cd71785459e2612e2dda3425d670de920a62de532c0dff2da6fe332b6365 bash scripts/pre_gate_check.sh`
  → `PRE-GATE OK: now=1794735673 (2026-11-15T09:41:13Z) < gate 1794866400 (2026-11-16T22:00:00Z); T-130727s remaining. state sha256 matches (c438cd71…); data/raw clean. STOP` — **EXIT=0**.
- `ruff check tests/test_post_gate_orchestrator.py tests/test_pre_gate_check.py tests/test_post_gate_handoff_consistency.py` → **All checks passed!**
- `pytest -q tests/test_post_gate_orchestrator.py tests/test_pre_gate_check.py tests/test_post_gate_handoff_consistency.py` → **61 passed in 3.93s** (57 baseline + 4 new).
- `bash -n scripts/post_gate_orchestrator.sh` → **ORCH_BASH_OK**; `bash -n scripts/pre_gate_check.sh` → **PREGATE_BASH_OK**.
- `git status --porcelain -- data/raw` → 0 lines.
- `git status --porcelain` → only `M tests/test_post_gate_handoff_consistency.py`.
- `sha256sum data/processed/paper_trading_state.yaml` = `c438cd71…` (unchanged; `last_run=2026-11-13`, `nav=132654.46201168097`, `runs=469`).

## Unresolved blocker (unchanged, deterministic)
Clock gate releases at 2026-11-16T22:00:00Z (~T-130727s out). The global 355-minute cutoff
precedes it. No code change can release the gate early; the mutating extend (cmd2/cmd4 of
`scripts/post_gate_orchestrator.sh`) remains withheld until at/after the gate epoch, per
NEXT_AGENT_TASK.md Step 2. `extend_paper_trading_state.py` run this session correctly
returned `sessions extended: 0`, `NAV before == NAV after`, `state write count: 0`, with
the readiness diagnostic showing the next session (2026-11-16 Mon) is still in the future.

## Next distinct investigation
The negative-NAV guard divergence is closed. If the paper NAV stays positive through the
gate release, no further consistency-guard change is needed. The next bounded task is the
real post-gate cycle at/after 2026-11-16T22:00:00Z (NEXT_AGENT_TASK.md Step 2), which this
fix specifically de-risks for the negative-NAV branch.