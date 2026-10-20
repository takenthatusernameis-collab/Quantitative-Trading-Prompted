# NEXT AGENT TASK — Cycle 886

## Context
futuresbasis_002 rejected on cost: all four ETFs (USO/BNO/UNG/GSG) show negative
annualized carry vs GLD over 2015-2026, CIs include zero. Rank 7 closed.

## Objective
Update opportunity_shortlist.md rank 7 row additively to mark both contract-leg and
ETF routes rejected; advance shortlist to next candidate (rank 8) and pre-register.

## Validation
python research/cost_admissibility_screen.py  # OVERALL: PASS
python -m pytest -q
