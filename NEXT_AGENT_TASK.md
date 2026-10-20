# NEXT AGENT TASK — Cycle 887

## Context
futuresbasis_002 rejected on cost: all four ETFs (USO/BNO/UNG/GSG) show negative
annualized carry vs GLD over 2015-2026, CIs include zero. Rank 7 closed (both
contract-leg and ETF routes rejected). Shortlist advanced to rank 8 (crypto
perpetual funding-rate carry), pre-registered as cryptofunding_001.

## Objective
Resolve the data blocker for rank 8: obtain multi-year (>= 1 year) of 8h funding-rate
history for BTC/ETH perpetuals on OKX (the only accessible exchange) so a valid
chronological test becomes possible. Document provenance, date range, row counts,
and any gaps. If multi-year history cannot be retrieved, document the precise
limit and make the next task a different bounded data-readiness step.

## Validation
python research/cost_admissibility_screen.py  # OVERALL: PASS
python -m pytest -q
