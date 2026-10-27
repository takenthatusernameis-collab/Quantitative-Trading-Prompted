# NEXT_AGENT_TASK — full-suite hang isolation (2026-10-27)

## Context
TSMomentum same-session vol correction tests pass (28 tests; anchor committed 450 sessions reproduced). Full `python -m pytest -q` hangs on `test_the_incumbent_is_the_only_candidate_with_a_positive_gate_headroom` (~55s in isolation, passes alone); documented in README Cycle 875.

## Objective
Determine whether the full-suite hang is an ordering/resource issue and make the suite complete within documented timeout, without weakening tests.

## Acceptance criteria
- python -m pytest -q completes with exit 0
- git status --porcelain data/ config/ empty

## Validation commands
python -m pytest -q
git status --porcelain data/ config/
