# Corrective Handoff — CORR248 (invocation 248)

## Invocation context
- Invocation: 248 (corrective). Diagnostic log inspected: `/home/runner/work/_temp/kilo-session-11-recovery-247.log` — shows only the provider auth/signup gate ("Sign up for free to continue..."), an environmental blocker unrelated to this repo's code.
- Prior corrective invocations (recovery logs 10–247) were ~293-byte provider-noise aborts; none produced a durable project change. The inherited working tree already carried one dirty file (`research/reports/tsmomentum_sma175_candidate_eval_001.md`, `Date: 2026-11-15` → `2026-11-16`). This invocation performed a distinct, evidence-supported investigation rather than repeating a no-op pre-gate re-check.

## Root cause found (reproducible, evidence-supported)
- Running `tests/test_tsmomentum_sma175_candidate_eval.py` (~196 s) **dirties the tracked report** `research/reports/tsmomentum_sma175_candidate_eval_001.md`. `research/tsmomentum_sma175_candidate_eval.py::run_candidate_eval()` rewrites `OUT_REPORT` with `Date: {today}` (`_today()` → `datetime.now(UTC)`), and the test both (a) runs the tool as a subprocess (`test_tool_runs_and_passes`) and (b) calls `run_candidate_eval()` via the module-scoped `payload` fixture. Neither path restored the file.
- The suite already asserts read-only guarantees for `research/run_cycle6.py` (`test_read_only_no_mutation_of_run_cycle6`) and `data/`/`config/` (`test_data_config_unchanged`), but it failed to protect the very artifact it mutates. This is the source of the inherited dirty state and a latent reproducibility gap: any test run leaves a spurious tracked-file diff that can be mistaken for intended work.

## What changed (test-only, smallest sufficient)
- `tests/test_tsmomentum_sma175_candidate_eval.py`: added a module-scoped `autouse` fixture `_restore_report_after_module` that snapshots `OUT_REPORT` bytes before the module runs and restores them (or unlinks, if it did not pre-exist) on teardown.
- No production code, threshold, gate, cost model, universe, clock-gate logic, `data/raw`, or `config/` touched. No commits.

## Verification (exact commands and outputs, all run fresh this invocation)
1. Reproduce the defect on the inherited tree:
   - `git checkout -- research/reports/tsmomentum_sma175_candidate_eval_001.md` then `/tmp/kilo-venv/bin/python -m pytest -q tests/test_tsmomentum_sma175_candidate_eval.py` → `6 passed in 195.66s`; `git status --porcelain` afterwards → ` M research/reports/tsmomentum_sma175_candidate_eval_001.md` (date-bump diff reproduced).
2. After the fix:
   - `/tmp/kilo-venv/bin/python -m pytest -q tests/test_tsmomentum_sma175_candidate_eval.py` → `6 passed in 197.01s`; `git status --porcelain` afterwards → ` M tests/test_tsmomentum_sma175_candidate_eval.py` only; `git diff -- research/reports/tsmomentum_sma175_candidate_eval_001.md` → **empty** (tracked report stays byte-identical).
   - `/tmp/kilo-venv/bin/ruff check tests/test_post_gate_orchestrator.py tests/test_pre_gate_check.py tests/test_post_gate_handoff_consistency.py` → `All checks passed!` (RUFF_EXIT=0).
   - `/tmp/kilo-venv/bin/python -m pytest -q tests/test_post_gate_orchestrator.py tests/test_pre_gate_check.py tests/test_post_gate_handoff_consistency.py` → `65 passed in 7.79s`.
   - `bash -n scripts/post_gate_orchestrator.sh` → `ORCH_BASH_OK`; `bash -n scripts/pre_gate_check.sh` → `PREGATE_BASH_OK`.
   - `GATE_EPOCH=1794866400 STATE_SHA256=c438cd71785459e2612e2dda3425d670de920a62de532c0dff2da6fe332b6365 bash scripts/pre_gate_check.sh` → `PRE-GATE OK: now=1794795175 (2026-11-16T02:12:55Z) < gate 1794866400; T-71225s remaining. state sha256 matches; data/raw clean. STOP` (EXIT=0).
   - `git status --porcelain -- data/raw` → empty; `git status --porcelain` → ` M tests/test_tsmomentum_sma175_candidate_eval.py` only.

## Note on pre-existing ruff findings (not introduced here)
- `ruff check tests/test_tsmomentum_sma175_candidate_eval.py` reports 3 findings (F401 unused `hashlib`; two PLW1510 `subprocess.run` without `check`). These are **pre-existing** — the same 3 findings are present in `git show HEAD:tests/test_tsmomentum_sma175_candidate_eval.py`. They are outside the task's ruff gate (which covers only the three orchestrator test files, all clean). Left untouched to keep this change minimal and test-isolated.

## Unresolved blocker
- **Temporal gate (expected, not a defect):** the post-gate extend cannot run until `2026-11-16T22:00:00Z` (epoch 1794866400); at this invocation `T-71225s` (~19.8 h) remains. No code change can release it early. Step 2 stays withheld.
- **Provider noise:** corrective recovery logs show `Sign up for free...` aborts before any project command; not a project-layer defect.

## Next distinct investigation (if re-invoked before the gate clears)
- Do not repeat the no-op pre-gate re-check. The report-dirtying defect is fixed and verified. Remaining actionable work is gated on the clock: at/after `2026-11-16T22:00:00Z`, run Step 2 (`GATE_EPOCH=1794866400 PYTHON=/tmp/kilo-venv/bin/python RUFF=/tmp/kilo-venv/bin/ruff bash scripts/post_gate_orchestrator.sh`), confirm idempotency on a second run (`sessions extended: 0`, 0 writes), and verify `data/raw` stays clean with `Status: OK` / `Mode: full cycle (extend included)` / `Gate state: released`.
- If a future run finds the same report file dirty again, check whether a *different* tracked artifact is being regenerated by a test (same defect class) rather than reverting blindly.

## Safety
- Research/backtesting only; no live trades. No deps/services added, no secrets accessed, no workflow/agent changes, no threshold/gate/cost-model/universe edits, no `data/raw` writes, no commits. Clean-tree invariant for `data/` and `data/raw` respected (verified empty). Pre-registrations and promotion gates preserved.