# Cycle 953 — Prepare `sectorrotation_001` (C4) hypothesis and evaluation plan

## Context
- Cycle 950/951 committed `commoditytrend_001` rejection. Cycle 952 reconciled `csmomentum_001` (C3): experiment `research/experiments/csmomentum_001_experiment_001.md` shows WF mean OOS Sharpe 0.6619 < 0.9 with DSR prob 0.4460 → Rejected/Failed per pre-registered gates; hypothesis updated.
- Opportunity shortlist ranks C4 (sector rotation across 9 GICS sector ETFs) at 28/35 as next untested candidate after C3. C4 is subsumed by C3 only if C3 validates; since C3 is rejected, C4 remains a distinct, testable candidate with cached data (XLB,XLE,XLF,XLI,XLK,XLP,XLU,XLV,XLY, 1998-2026).
- Existing `sectorrotation_001`/`sectorrotation_002` hypotheses exist and are rejected (different constructions) — do not reopen them; if C4 is a different specification, create a new hypothesis ID only if necessary, else document why it differs.

## Objective
Pre-register C4 as a testable hypothesis (or confirm no new hypothesis needed) with a frozen evaluation plan. Do not execute backtest/tuning.

## Acceptance criteria
1. Check existing `research/hypotheses/sectorrotation_*.md` — confirm status and construction; if C4 matches closed line, document and pick next untested candidate instead.
2. If distinct and untested: create `research/hypotheses/sectorrotation_003.md` (or next available ID) pre-registered with mechanism, universe (9 sector ETFs), lookback/skip/top-fraction, benchmark (1/N), cost model (3bps round-trip), monthly rebalance, chronological splits, walk-forward with purge/embargo, promotion gates (WF mean OOS Sharpe >= 0.9, >=50% folds positive, >100 pooled OOS trades), multiple-testing controls, falsification conditions.
3. Create `research/experiments/sectorrotation_00X_evaluation_plan_953.md` documenting frozen plan and reproduction command skeleton (no execution).
4. Verify cached data exists for all 9 sector ETFs in `data/processed/` or `data/raw/` used by repo convention.
5. `python -c "import yaml; print('ok')"` and relevant tests still pass; `python research/commoditytrend_001_evaluation.py` -> OVERALL: PASS.
6. Replace NEXT_AGENT_TASK.md with Cycle 954 task: run frozen evaluation for the selected candidate with full verification and record verdict.

## Scope boundaries
- No backtest execution, tuning, or re-tuning.
- No reopening commoditytrend_001 or csmomentum_001.
- Use cached data only.
- Follow hypothesis-first discipline.
