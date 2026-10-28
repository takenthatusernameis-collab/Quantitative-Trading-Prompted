# CORRECTIVE_HANDOFF_CORR6.md

## Correction applied (invocation 376)

1. **Fixed the commodity data-gate blocker.** `tests/test_commodity_data_gate_001.py` was failing 3 + erroring 5 because `research/commodity_data_gate_001.py --no-report` requires the scratch provenance report `/tmp/scratchpad/commodity_fetch/commodity_fetch_report.json` (produced by `research/commodity_data_gate_fetch.py`, network, scratch-only). Ran the documented reproduction step:
   `python research/commodity_data_gate_fetch.py` -> fetched DBC/BNO/UNG/GLD (BNO incepts 2010-06-02), wrote the provenance report, EXIT=0.
   Then `python research/commodity_data_gate_001.py` -> OVERALL: PASS, union 6100 sessions, 12/11 folds, all 13 checks PASS, data/ config/ byte-identical.
   Then `python -m pytest -q tests/test_commodity_data_gate_001.py` -> 15 passed in 3.76s, EXIT=0.
   (Scratch report lives in /tmp/scratchpad, outside the repo; no repo files written by the fetch.)

2. **Ran the full suite to completion (materially different from prior attempts that hung/timed out).**
   `python -m pytest -q` ran in the background (pid 105211) and completed: `8 failed, 744 passed, 1 skipped, 110 warnings in 3943.45s (1:05:43)`. It does NOT hang; it completes. All 8 failures are confined to `tests/test_leadlag_001_evaluation.py`.

## Verification commands and outputs

- `python research/commodity_data_gate_fetch.py` -> EXIT=0; provenance report at /tmp/scratchpad/commodity_fetch/commodity_fetch_report.json
- `python research/commodity_data_gate_001.py` -> OVERALL: PASS, EXIT=0
- `python -m pytest -q tests/test_commodity_data_gate_001.py` -> 15 passed in 3.76s, EXIT=0
- `python -m pytest -q` -> `8 failed, 744 passed, 1 skipped ... in 3943.45s (1:05:43)`; all 8 failures in test_leadlag_001_evaluation.py
- `git status --porcelain data/ config/` -> empty (clean)

## The 8 remaining failures (test_leadlag_001_evaluation.py), hard-evidenced

All 8 pre-exist on clean HEAD (`git stash` -> 8 failed). Two independent root causes, neither fixable within AGENTS.md safety constraints (no fabricating git objects, no truncating/replacing committed market data, no weakening pre-registration integrity tests, no committing without explicit request):

1. **Freeze commit `ace2643` does not exist.** `git cat-file -t ace2643` -> "Not a valid object name". `git log --all` contains only `8a0bfe9`, `f64c456`. `git fetch origin ace2643` -> "couldn't find remote ref". `FREEZE_COMMIT = "ace2643"` is hardcoded in `research/leadlag_001_evaluation.py:90` and the tests call `git show ace2643 ...`. Tests `test_the_freeze_commit_contains_exactly_the_two_pre_registration_files` and `test_the_pre_registration_files_are_byte_identical_to_the_freeze_commit` cannot pass without the object. Unrecoverable from this repository.

2. **Union-calendar count mismatch: 6100 measured vs 6098 frozen.** `research/leadlag_001_evaluation.py` `build_payload` sets `union_sessions = len(close_all)` = 6100 (full union of all cached symbol dates, incl. out-of-range sessions); `FROZEN["union_calendar_sessions"]` and `config/leadlag_candidate_001.yaml` record 6098, and the test hardcodes `payload["union_sessions"] == 6098` (`test_the_panel_is_the_cycle_934_complete_cross_section`) and `calendar_churn == 0.5146` (1 - 2960/6098 = 0.514595; measured churn = 0.514754). The cache has since been appended (sessions beyond frozen history_end 2026-10-15); `git status --porcelain data/` is empty, so it is committed history, not a working-tree edit. No principled computation of the current cache yields 6098, so the test literal cannot be satisfied without modifying the frozen values/test/data (prohibited).

Cascading failures (tool returns OVERALL: FAIL because check `panel_is_the_cycle_934_complete_cross_section` fails): `test_two_runs_byte_identical_output`, `test_two_runs_write_byte_identical_artifacts`, `test_data_and_config_unchanged_before_and_after`, `test_all_structural_checks_pass`, `test_the_artifacts_are_written_and_carry_the_freeze_commit`.

## Why exit 0 is unreachable

`python -m pytest -q` cannot reach exit 0 while `ace2643` is absent (tests 1–2 permanently fail) and union = 6100 ≠ frozen 6098 (tests 3–8 permanently fail). Both are pre-existing infrastructure/data gaps, independent of the cost-admissibility task, and both were already concluded unfixable in CORRECTIVE_HANDOFF_CORR4.md / CORR5.md / CURRENT.md.

## Next distinct investigation

Resolve the 8 pre-existing `test_leadlag_001_evaluation.py` failures. Per CORR5's sub-question (a): re-freeze the pre-registration (a new git commit containing exactly `config/leadlag_candidate_001.yaml` + `research/hypotheses/leadlag_001.md`, union count corrected to the measured 6100 and churn to 0.514754), re-point `FREEZE_COMMIT`/tests at the new commit, and update the test's hardcoded `6098`/`0.5146` literals to the measured values. This is the smallest evidence-supported correction that does not touch market data. Note: creating the commit requires explicit user request (per "NEVER commit changes unless the user explicitly asks"), and updating `FREEZE_COMMIT` away from `ace2643` requires care because the tool and tests hardcode it. Only after this is resolved can `python -m pytest -q` reach exit 0.

CORRECTIVE_VERIFICATION=BLOCKED
