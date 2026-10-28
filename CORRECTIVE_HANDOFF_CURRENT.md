# CORRECTIVE_HANDOFF_CURRENT.md

## Summary
Stale PSR hardcode in `tests/test_tsmomentum_sma175_promotion_gate_eval.py:140` corrected from
`0.8996990715818167` to `0.896591902163973` (matches the tool output, the test's own
`expected_psr` fixture and the Cycle-921 corrected value; verified pre-existing on clean HEAD).
`src/backtest/engine.py` left at HEAD (its CORR3 numpy rewrite reintroduced 2 read-only-guarantee
failures). Three `research/reports/*.md` files reverted (only metadata churn from earlier
full-suite runs). `data/` and `config/` byte-clean.

## Verification
- `git status --porcelain data/ config/` : empty
- `git status --porcelain src/backtest/engine.py` : empty (at HEAD)
- `python -m pytest tests/test_tsmomentum_sma175_promotion_gate_eval.py::test_reported_psr_matches_the_documented_baseline_psr tests/test_tsmomentum_rolling63_weakness_diagnosis.py::test_read_only_guarantee -q` -> 2 passed in 17.33s, EXIT=0

## Blockers
- 8 pre-existing `tests/test_leadlag_001_evaluation.py` failures on clean HEAD (`git stash` ->
  `8 failed, 22 passed`, exit 1). Two independent root causes, both hard-evidenced:
  1. Freeze commit `ace2643` does not exist (`git cat-file -t ace2643` -> invalid object name;
     `git fsck --full --unreachable` finds only stash/index commits; `git fetch origin ace2643`
     -> "couldn't find remote ref"; all 8 remote backup/fix branches fetched and searched, none
     contains the two pre-registration files). Unrecoverable from this repository.
  2. Union-calendar count mismatch: measured 6100 vs frozen 6098. Reproduced with the
     evaluator's own `load_closes`/`build_panel` and the shortlist's own
     `close_and_volume`/`complete_panel`: union = 6100, complete = 2960, churn = 0.514754
     (frozen asserts 6098 / 0.5146). The 2-session gap is not data drift: the union now includes
     4 sessions beyond the frozen `history_end` 2026-10-15 (2026-10-16, 19, 20, 21), present in
     every cached symbol (futures and ETFs now extend to 2026-10-21; GLD/TLT to 2026-10-19).
     `git status --porcelain data/` is empty, so the extension is committed history, not a
     working-tree edit.
- Therefore `python -m pytest -q` cannot reach exit 0.

## Next distinct investigation
Resolve the 8 pre-existing leadlag failures. Sub-question: is the intended fix to re-freeze the
pre-registration (a new commit containing exactly `config/leadlag_candidate_001.yaml` +
`research/hypotheses/leadlag_001.md`, union count corrected to the measured 6100 and churn to
0.514754) and update the test's hardcoded `6098`/`0.5146` literals to the measured values — the
smallest evidence-supported correction that does not touch market data — or should the cache be
restored to its freeze-era end date so the union returns to 6098? See
`CORRECTIVE_HANDOFF_CORR5.md` for the full evidence.

CORRECTIVE_VERIFICATION=BLOCKED