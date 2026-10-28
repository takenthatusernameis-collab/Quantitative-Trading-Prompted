# Corrective handoff 4 (2026-10-28) — CORRECTIVE_VERIFICATION=BLOCKED

## Summary of changes made
1. Reverted `src/backtest/engine.py` to HEAD. The CORR3 numpy rewrite of `compute_metrics` introduced 2 NEW read-only-guarantee failures (`test_read_only_guarantee`, `test_writes_nothing_outside_research`) because those tests assert `engine.py` is unmodified. Reverting removes both regressions; no behavior needed from the rewrite.
2. Fixed stale hardcoded PSR value in `tests/test_tsmomentum_sma175_promotion_gate_eval.py:140`: `0.8996990715818167` -> `0.896591902163973`. The tool's actual output and the test's own independent `expected_psr` fixture and docstring (Cycle 921 corrected value = 0.896592) all agree on 0.896591902163973; only the hardcoded line was stale. Confirmed this test fails identically on clean HEAD via `git stash` — pre-existing, not caused by my changes.
3. Kept `research/cost_admissibility_screen.py` memoization (CORR3) — harmless, causes no test failures, speeds the cost-admissibility screen.
4. `src/backtest/engine.py` is now back to HEAD (reverted); `data/` and `config/` remain byte-identical (clean).

## Verification (ran and passed)
- `git restore --source=HEAD --staged --worktree src/backtest/engine.py` -> engine.py unmodified (`git status --porcelain src/backtest/engine.py` empty).
- `python -m pytest tests/test_tsmomentum_rolling63_weakness_diagnosis.py::test_read_only_guarantee tests/test_shortlist_gross_edge_001.py::test_writes_nothing_outside_research tests/test_tsmomentum_sma175_promotion_gate_eval.py::test_reported_psr_matches_the_documented_baseline_psr -q` -> 3 passed in 16.82s.
- Full suite earlier (engine.py+memoization+PSR fix): `10 failed, 742 passed, 1 skipped in 1714.19s` (753 total) — every failure enumerated: exactly 8 `test_leadlag_001_evaluation.py` + 2 engine.py read-only failures, nothing else.

## Unresolved blocker (exit 0 unattainable)
8 pre-existing `tests/test_leadlag_001_evaluation.py` failures, present on clean HEAD (`git stash` -> `8 failed, 22 passed`, exit 1), unrelated to the cost-admissibility task:
- `test_the_freeze_commit_contains_exactly_the_two_pre_registration_files`: `fatal: ambiguous argument 'ace2643': unknown revision`.
- `test_the_pre_registration_files_are_byte_identical_to_the_freeze_commit`: `fatal: invalid object name 'ace2643'`.
- `test_the_panel_is_the_cycle_934_complete_cross_section`: `assert 6100 == 6098`.
- `test_two_runs_byte_identical_output`, `test_two_runs_write_byte_identical_artifacts`, `test_data_and_config_unchanged_before_and_after`, `test_all_structural_checks_pass`, `test_the_artifacts_are_written_and_carry_the_freeze_commit`: all `OVERALL: FAIL` (cascade from the missing `ace2643` freeze commit).
Commit `ace2643` does not exist in this repo (`git cat-file -t ace2643` -> invalid object name). These cannot be resolved without fabricating history/data or weakening tests, both prohibited. Therefore `python -m pytest -q` cannot reach exit 0; best achievable is the 8 pre-existing leadlag failures.

## Next distinct investigation (not part of this cost-admissibility scope)
Resolve the 8 pre-existing leadlag failures: determine whether freeze commit `ace2643` should exist in history (clone/fetch gap) or whether the leadlag test data and expected panel count (6100 vs 6098) need correction. Only after that is resolved can `python -m pytest -q` reach exit 0.

## Working tree (data/ config/ clean)
```
 M research/cost_admissibility_screen.py
 M research/reports/common_inception_sample_audit_001.md      (pre-existing trailing newline)
 M research/reports/sectorrotation_long_sample_feasibility_001.md  (test-regenerated git rev)
 M research/reports/tsmomentum_sma175_candidate_eval_001.md   (test-regenerated git rev/date)
 M tests/test_tsmomentum_sma175_promotion_gate_eval.py        (PSR fix)
?? CORRECTIVE_HANDOFF_CORR3.md                               (prior invocation)
?? CORRECTIVE_HANDOFF_CORR4.md                               (this record)
```

CORRECTIVE_VERIFICATION=BLOCKED
