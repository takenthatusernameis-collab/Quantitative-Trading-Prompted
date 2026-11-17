# Corrective Handoff — record-status staleness regression guard (2026-11-17T01:48Z)

## Status
CORRECTIVE_VERIFICATION=PASS (focused verification of this correction succeeded)
Gate extension itself remains time-blocked until 2026-11-17T22:00:00Z (see Unresolved blocker).

## Invocation context
- Previous invocation (session 14) failed at the runtime/model layer: `/home/runner/work/_temp/kilo-session-14.log` shows `Error: The stealth model could not complete the request` (non-transient invocation failure), so it produced no new durable project change. Controller state `kilo-progress-state-43952759940-1.txt` records `phase=corrective-attempt-start`, `failed=3`.
- HEAD at start of this invocation: `ef1479d` (controller checkpoint), which had already corrected `research/{reports,experiments}/paper_trading_record_status_001.md` from the stale `sessions: 469 / last_run_date: 2026-11-13` to the true `470 / 2026-11-16`.
- This invocation is materially different from prior corrective invocations (which only ran the pre-gate cheap path and re-ran tests). Instead it closed the durable-evidence gap that allowed the staleness to occur silently.

## Evidence / root cause
- Canonical state `data/processed/paper_trading_state.yaml` (sha256 `8a1d2996…65ee1`, matches HEAD) has `last_run_date: 2026-11-16` and `len(cumulative_returns) == 470`.
- `research/paper_trading_record_status_audit.py` regenerates the two record-status artifacts from that state; running it against the committed files produced a byte-identical result (no diff), confirming HEAD `ef1479d` is correct.
- BUT: (a) `scripts/post_gate_orchestrator.sh` never invokes this audit (grep: `NOT REFERENCED IN ORCHESTRATOR`), so the artifacts drift after each gate cycle unless regenerated manually; and (b) the audit's test `tests/test_paper_trading_record_status_audit.py` only asserted the files exist and that the tool prints `OVERALL: PASS` — it never checked the artifacts match the state. That is exactly why the 469/2026-11-13 staleness went uncaught until a manual commit.

## What changed (test-only; no production/gate/cost/universe/clock change)
- `tests/test_paper_trading_record_status_audit.py`:
  - Added a deterministic staleness guard that reads `data/processed/paper_trading_state.yaml`, computes `sessions = len(cumulative_returns)` and `last_run_date`, and asserts the committed report/experiment artifacts equal the generator's exact output **before** running the tool (so a regeneration inside the tool cannot mask committed drift).
  - Preserved the original tool-run assertions (`returncode == 0`, `OVERALL: PASS`, files exist).
  - Incidental lint fixes in the same file: split `import subprocess, sys` (I001) and added `check=False` to `subprocess.run` (PLW1510). File is now ruff-clean.

## Verification (exact commands and observed outputs, all run fresh this invocation)
1. `date -u` / clock: now `2026-11-17T01:48:31Z`; gate `1794952800` = `2026-11-17T22:00:00Z`; T-72689s remaining.
2. `sha256sum data/processed/paper_trading_state.yaml` → `8a1d29960142bca9aa4d9673e06f64775593d9402622612209bae66bf9965ee1` (== HEAD).
3. `GATE_EPOCH=1794952800 STATE_SHA256=8a1d2996…65ee1 bash scripts/pre_gate_check.sh` → `PRE-GATE OK: … < gate 1794952800 …; T-72689s remaining. state sha256 matches (…); data/raw clean. STOP` → `PREGATE_EXIT=0`.
4. `/tmp/kilo-venv/bin/python -m pytest -q tests/test_post_gate_orchestrator.py tests/test_pre_gate_check.py tests/test_post_gate_handoff_consistency.py tests/test_paper_trading_record_status_audit.py` → `65 passed, 1 skipped in 8.91s` (`PYTEST_EXIT=0`); the single skip is the legitimate pre-gate conditional (`gate released: the committed handoff is expected to be a full-cycle record`).
5. `/tmp/kilo-venv/bin/ruff check tests/test_post_gate_orchestrator.py tests/test_pre_gate_check.py tests/test_post_gate_handoff_consistency.py tests/test_paper_trading_record_status_audit.py` → `All checks passed!` (`RUFF_EXIT=0`).
6. Negative control (proves the new guard actually catches the defect class): wrote stale artifacts (`sessions: 469`, `last_run_date: 2026-11-13`) then ran `pytest -q tests/test_paper_trading_record_status_audit.py` → `1 failed` with assertion diff `sessions: 470 → 469`, `last_run_date: 2026-11-16 → 2026-11-13` (`NEG_EXIT=1`); restored via `git checkout -- research/{reports,experiments}/paper_trading_record_status_001.md` and confirmed restoration (`git status --porcelain` shows only the intended test file).
7. `git status --porcelain` → ` M tests/test_paper_trading_record_status_audit.py` (only intended change). `git status --porcelain -- data/raw` → empty (canonical data untouched).

## Unresolved blocker
- Time gate only: `2026-11-17T22:00:00Z` (epoch 1794952800) is ~20h away; this run's controller envelope (`remaining_seconds≈3204`, ~53 min) ends long before the gate, so the mutating gate extension (Step 2) cannot run here. This is expected per `NEXT_AGENT_TASK.md` scope boundaries, not a defect.

## Next distinct investigation (at/after 2026-11-17T22:00:00Z)
- Re-run pre-gate; expect EXIT=3 (gate reached). Then run the full cycle:
  `GATE_EPOCH=1794952800 STATE_SHA256=8a1d29960142bca9aa4d9673e06f64775593d9402622612209bae66bf9965ee1 PYTHON=/tmp/kilo-venv/bin/python RUFF=/tmp/kilo-venv/bin/ruff bash scripts/post_gate_orchestrator.sh`
  Expect exactly one session appended (2026-11-17) with a single state write if a completed bar exists; idempotency re-run extends 0 with 0 writes.
- After the extend, re-run `research/paper_trading_record_status_audit.py` (or rely on the new test) so the record-status artifacts track the new session count/date; the new guard will fail if they are not regenerated.
- If `/tmp/kilo-venv` is absent, recreate per the runtime note in `NEXT_AGENT_TASK.md`.

## Safety
- Research/backtesting only; no live trades. No deps/services/secrets/workflow/agent changes. No threshold/gate/cost-model/universe/clock-gate edits. `data/raw` untouched (verified empty). All pre-registrations and promotion gates preserved. No manual commit (controller checkpoints at session boundary).