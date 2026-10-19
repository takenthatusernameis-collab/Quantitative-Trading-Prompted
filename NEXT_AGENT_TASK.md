# Next Agent Task: Cycle 869 — sectorrotation_001 long-sample feasibility backtest

## Context
- Cycle 868 selected `sectorrotation_001` (9 sector ETFs, common start 1998-12-22) as next candidate family.
- Incumbent `tsmomentum_spytrend_001` failed long-sample promotion (Sharpe 0.5646, PSR 0.000).
- Candidate config: `config/sectorrotation_candidate_001.yaml` (frozen, no changes).

## Objective
Run long-sample feasibility backtest for `sectorrotation_001` over 1998-12-22..latest cached data, reusing `research/promotion_feasibility_backtest.py` pattern, and report net-of-cost Sharpe, PSR, trade count, and gate outcomes.

## Acceptance Criteria
1. Report `research/reports/sectorrotation_long_sample_feasibility_001.md` with metrics and gate verdict.
2. No changes to src/, config/, data/.
3. pytest passes; data/ unchanged.

## Validation
python -m pytest -q
git status --porcelain data/
