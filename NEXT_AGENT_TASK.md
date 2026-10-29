# NEXT_AGENT_TASK — restore full pytest green (2026-10-29)

## Context
Cycle 6 assigned task: regenerate scratch provenance report at `/tmp/scratchpad/commodity_fetch/commodity_fetch_report.json` so `python -m pytest -q` exits 0. **Completed**: the scratch report and all 4 parquet files exist; `tests/test_commodity_data_gate_001.py` → 15 passed; `git status --porcelain data/ config/` empty.

However, `python -m pytest -q` still does not exit 0 due to **pre-existing failures unrelated to the commodity data gate**:

1. `tests/test_leadlag_001_evaluation.py` — 8 failures:
   - `research/leadlag_001_evaluation.py:90` hardcodes `FREEZE_COMMIT = "ace2643"`, which is not a valid object in this repo (`git cat-file -t ace2643` → fatal). This breaks `test_the_freeze_commit_contains_exactly_the_two_pre_registration_files` and `test_the_pre_registration_files_are_byte_identical_to_the_freeze_commit`.
   - `test_the_panel_is_the_cycle_934_complete_cross_section` expects `union_sessions == 6098` but measures `6100` (off by 2 sessions).
   - `test_two_runs_byte_identical_output` fails because the tool returns OVERALL: FAIL due to the panel check above.

2. Three test files hang indefinitely (>120s each, no output):
   - `tests/test_tsmomentum_sma175_candidate_eval.py`
   - `tests/test_tsmomentum_same_session_vol_correction.py`
   - `tests/test_tsmomentum_vol_estimate_consolidation.py`

3. `tests/test_the_incumbent_is_the_only_candidate_with_a_positive_gate_headroom.py` referenced in README does not exist.

## Objective
Make `python -m pytest -q` exit 0 by resolving the pre-existing test failures above, without editing test thresholds or weakening checks, and without writing under `data/` or `config/`.

## Acceptance criteria
- `python -m pytest -q` exits 0
- `git status --porcelain data/ config/` empty

## Validation commands
python -m pytest -q
git status --porcelain data/ config/

## Scope boundaries
- Do not edit test thresholds or weaken checks.
- Do not write under `data/` or `config/`.
- Do not fabricate git history or commits.
- The leadlag freeze commit fix must use an actual commit that exists in the repo; if `ace2643` cannot be recovered, document why and propose a bounded alternative.
- Investigate hanging tests before attempting fixes; do not add timeouts or retries as a substitute for root-cause fixes.
- This task is about test-suite health, not research: no strategy/gate/threshold/config changes.