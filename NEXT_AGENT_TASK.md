# DELAY-ELIMINATION OVERRIDE — 2026-10-30

The full-suite green criterion is currently blocked by two different classes of issue:
1. The committed DBC/csmomentum cache inconsistency needs an explicit governance decision before any change under data/, config/, frozen simulation artifacts, or published records. Do not rerun the full suite expecting it to become green while this decision is pending.
2. Several provider/TSMomentum and incumbent-headroom tests have documented long-running or hanging behavior. Re-running the complete suite repeatedly does not identify the slow node and wastes time.

**Bounded execution plan:**
- Do not run python -m pytest -q again until the DBC/csmomentum governance decision is made and the documented leadlag freeze references are repaired through an auditable path.
- Use pytest --collect-only first; then run only the named hanging test nodes/files under an OS-level timeout with -vv to identify the last test reached. Limit each isolate to one attempt per unchanged code/input state.
- If a test file has no output or exceeds its time budget, capture the exact last node and process state; do not rerun the same unchanged isolate repeatedly.
- Work only on network-independent tests or code paths that do not read/write data/, config/, frozen artifacts, strategy thresholds, or research verdicts.
- Run focused tests after any permitted test/diagnostic change. Reserve full-suite execution for after the governance blocker is resolved and a concrete fix exists.
- If the next productive action is the governance choice between (a) restoring historical DBC to the frozen cut-off, (b) recreating the csmomentum artifacts from a separately frozen historical cache, or (c) amending the published results with an explicit supersession record, stop and ask the repository owner. Do not choose unilaterally.

Keep thresholds and checks strict. Never fabricate the missing freeze commit, alter published results, or weaken assertions to obtain a green suite. The task remains open; this override changes only the diagnostic order and repeated-run cadence.

---

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