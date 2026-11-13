# CORRECTIVE HANDOFF — corrective invocation 2 (2026-11-13T03:35Z)

## Why this invocation differs from invocation 1
Invocation 1 added a mixed pass/fail regression test (durable, still present) but emitted
`CORRECTIVE_VERIFICATION=BLOCKED` because it treated the *time-gated gate check* as the
verification target. That conflated two things and produced a no-success run.

This invocation instead audited the orchestrator itself for **durable-evidence defects** —
the class of bug that would silently corrupt the record the gate-active run leaves behind.
Three defects were reproduced empirically before fixing (see probes), and each now has a
regression test that fails against the pre-fix script and passes after.

## Defects found (reproduced before fixing)
1. **Handoff write failure still exited 0.** `HANDOFF=/nonexistent-dir-xyz/h.md` →
   `RC=0`, log printed `cycle complete`, error only on stderr. The script exists to leave
   durable evidence in the repo (not `/tmp`, lost on teardown); a failed write reported as
   success means a teardown kill can erase the only record of the gate check.
2. **Handoff misreported the cycle in read-only mode.** The `Cmds run` line was a static
   string listing `2 extend, 4 idempotent re-extend` even though `--read-only` skips both.
   A pre-gate read-only run would therefore record that the mutating extend had run.
3. **`--max-wait-seconds abc` crashed with `unbound variable` (rc=1)** instead of a usage
   error (rc=2). The gate-active run is instructed to pass this flag.

## Changes (smallest sufficient, in scope)
- `scripts/post_gate_orchestrator.sh`
  - `--max-wait-seconds` now validated as a positive integer → rc=2 + `requires a positive integer`.
  - Added `CMDS_RUN` / `CMDS_SKIPPED` tracking (`mark_run` / `mark_skipped`); the handoff now
    records what actually ran and what was skipped.
  - Handoff write is fatal: `if ! cat > "$HANDOFF" <<EOF ... then log FATAL; exit 1`.
  - `cycle complete` is now logged only *after* a successful write (no more misleading
    "cycle complete" preceding a FATAL).
- `tests/test_post_gate_orchestrator.py` — 3 new regression tests:
  `test_read_only_handoff_reports_skipped_extend`,
  `test_handoff_write_failure_exits_nonzero`,
  `test_max_wait_seconds_rejects_non_integer`.
- `README.md`, `NEXT_AGENT_TASK.md` — status refreshed. Objective, acceptance criteria,
  verification commands, scope boundaries unchanged.

No changes to thresholds, gates, cost model, universe, clock-gate epoch logic, or `data/`.

## Verification (exact commands and observed outputs)
| command | result |
|---|---|
| `bash -n scripts/post_gate_orchestrator.sh` | `BASH_OK` |
| `pytest tests/test_post_gate_orchestrator.py -q` (after) | **13 passed in 1.79s** |
| same, against `git show HEAD:scripts/post_gate_orchestrator.sh` (pre-fix) | **3 failed, 10 passed** — proves the new tests are real regressions, not tautologies |
| `pytest` 6-module suite (cmd5) | **68 passed in 27.54s** |
| `ruff check` 4 extension scripts + edited test | `All checks passed!` (`RUFF_RC=0`) |
| `pytest tests/test_tsmomentum_rolling63_weakness_diagnosis.py tests/test_go_no_go_evaluation.py` (cmd9) | **36 passed in 114.75s** |
| `sha256sum data/processed/paper_trading_state.yaml` | `2dace0e3e1accf00a749cde2baf6470b5e2abc61e542fe636854910361dec88a` (== HEAD, unchanged) |
| `git status --porcelain` | 5 modified files, all intended; `data/` and `config/` clean |
| `date -u` | `Fri Nov 13 03:35:17 UTC 2026` → gate epoch 1794607200 still **66283s (~18.4h) out** |

Behavioural probes after the fix:
- read-only handoff now: `Cmds run: 1 date, 3 drift, 5 6-module pytest, 6 git status,
  7 data-cost inventory + tests, 8 ruff` / `Cmds skipped: 2 extend (read-only),
  4 idempotent re-extend (read-only)`; `RC=0`.
- unwritable `HANDOFF` → `RC=1` + `FATAL: could not write durable handoff ...`.
- `--max-wait-seconds abc` → `RC=2` + usage message; `--max-wait-seconds 1` still → `RC=3`.

## Unresolved blocker (time gate, not a defect)
The 2026-11-13 extension gate (epoch 1794607200 = 2026-11-13T22:00:00Z) is still closed.
cmds 2/4/7 (mutating extend) remain withheld per scope. This run's envelope reaps far
before the gate; the run active at 22:00 UTC must perform it.

## Next distinct action (evidence-supported)
At/after 2026-11-13T22:00:00Z, from the run active across the gate:
```
GATE_EPOCH=1794607200 HANDOFF=CORRECTIVE_HANDOFF_POSTGATE_20261113.md \
  bash scripts/post_gate_orchestrator.sh --wait-until-gate
```
The orchestrator now fails loudly (rc=1) instead of silently if it cannot write that
handoff, and the handoff records exactly which cmds ran — so the resulting artifact is
trustworthy either way.

## Safety
No alpha/promotion claims. No live trading, secrets, credentials, or account access.
Research pre-registrations, promotion gates, cost model, security controls, workflow
boundaries, and user data preserved. No commit made (not requested). `data/raw/` untouched.