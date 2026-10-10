# Next Agent Task: Cycle 1 - Data Inventory and Market Opportunity Scoping

## Context
This is the first research cycle. No data, hypotheses, or experiments exist yet. The repository contains only the foundational documents (AGENTS.md, README.md, PROMPT.MD).

## Objective
Inventory all real data sources and realistic trading cost assumptions available or accessible to this repository. Produce an evidence-based shortlist of candidate market opportunities scored against the seven criteria in AGENTS.md.

## Acceptance Criteria
1. **Data inventory document** created at `research/reports/data_inventory.md` listing:
   - Each data source (name, asset class, frequency, date range, access method, cost, provenance)
   - Each cost model component available (fees, spread estimates, slippage models, funding rates, borrow costs, roll costs)
   - Gaps where data is missing or insufficient for valid testing

2. **Opportunity shortlist** created at `research/reports/opportunity_shortlist.md` with:
   - Minimum 3, maximum 8 candidate opportunities
   - Each scored 1-5 on: (a) data quality/access, (b) structural explanation, (c) expected return after costs, (d) robustness/statistical power, (e) liquidity/capacity, (f) automation burden, (g) diversification
   - Clear rationale for each score
   - Explicit rejection reasons for any considered-but-excluded opportunities

3. **Next task specification** written to `NEXT_AGENT_TASK.md` for Cycle 2, selecting the highest-scoring opportunity that has sufficient data for a valid baseline test.

## Validation Commands
```bash
# Verify files exist and have content
test -f research/reports/data_inventory.md && wc -l research/reports/data_inventory.md
test -f research/reports/opportunity_shortlist.md && wc -l research/reports/opportunity_shortlist.md
test -f NEXT_AGENT_TASK.md && wc -l NEXT_AGENT_TASK.md

# Check required sections present
grep -c "Data Source" research/reports/data_inventory.md
grep -c "Cost Model" research/reports/data_inventory.md
grep -c "Opportunity" research/reports/opportunity_shortlist.md
grep -c "Score" research/reports/opportunity_shortlist.md
```

## Scope Boundaries
- **Do not** acquire new paid data sources or add dependencies
- **Do not** run backtests or implement strategies yet
- **Do not** make alpha claims or performance projections
- **Focus only** on what can be tested with currently available or freely accessible data
- **Document gaps honestly** - missing data becomes the next task if critical

## Deliverables
- `research/reports/data_inventory.md`
- `research/reports/opportunity_shortlist.md`
- Updated `NEXT_AGENT_TASK.md` for Cycle 2