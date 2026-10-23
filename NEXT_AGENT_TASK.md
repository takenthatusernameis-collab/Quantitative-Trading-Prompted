# Cycle 954 — Sector rotation C4 matches closed line; advance to next distinct candidate

## Context
- Cycle 953 verified that C4 (sector rotation across 9 GICS sector ETFs) is already
  pre-registered and evaluated under `sectorrotation_001` and `sectorrotation_002`
  with an identical construction (same 9-ETF universe, same 18-config grid, same
  benchmarks, same gates). No new hypothesis ID is warranted.
- Remaining shortlist exploratory candidates are blocked by data (C7 futures basis,
  C9 vol risk premium) or already rejected (C3, C4, C6 macro overlay, C5, C10).
- Cached data inventory unchanged; no new data fetched.

## Objective
Document the closed-line determination and select the next evidence-based,
data-supported distinct candidate or improvement track. No backtest execution.

## Acceptance criteria
1. `research/experiments/sectorrotation_closed_line_953.md` records the determination
   with references to sectorrotation_001/002 and the matching construction.
2. NEXT_AGENT_TASK.md replaced with a Cycle 955 task that either (a) proposes a
   bounded improvement experiment on the credible incumbent, or (b) documents a
   data/infrastructure blocker task — with verification commands.
3. `python -c "import yaml; print('ok')"` and `python research/commoditytrend_001_evaluation.py`
   (OVERALL: PASS) still pass.
4. No new backtest executed.

## Scope boundaries
- No backtest execution, tuning, or re-tuning.
- No reopening rejected candidates.
- Use cached data only.

## Verification
- `python -c "import yaml; print('ok')"`
- `python research/commoditytrend_001_evaluation.py`
