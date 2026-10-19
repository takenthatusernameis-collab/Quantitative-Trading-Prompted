# Next Agent Task: Cycle 868 — candidate-family selection for long-sample feasibility

## Context
- Cycle 867 long-sample backtest of frozen candidate tsmomentum_spytrend_001 over 2004-11-18..2026-10-16 (8487 sessions): canonical Sharpe 0.564626, PSR 0.000, 4 gates failed -> NO-GO. Consequence: incumbent not promotable in principle.
- Baseline tie-back: long-sample backtest Sharpe 0.383162 vs recorded 1.4178 (delta -1.034638), quantified (longer window incl. 2008/2020 drawdowns, slice warm-up).

## Objective
Select the next candidate family to test for long-sample feasibility: inventory available candidate configs and raw data coverage, score by data readiness + structural mechanism, pick one, and prepare its long-sample feasibility script (reuse promotion_feasibility_backtest.py pattern).

## Acceptance Criteria
1. Report research/reports/candidate_family_selection_001.md with scoring table and chosen family.
2. No code changes to src/config/data.
3. pytest passes; data/ unchanged.

## Validation
python -m pytest -q
git status --porcelain data/
