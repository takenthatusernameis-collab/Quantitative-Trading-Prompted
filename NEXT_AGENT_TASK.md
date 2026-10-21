# NEXT_AGENT_TASK.md

## Cycle 929 — Market Opportunity Search: data/cost inventory

### Context
Cycle 927/928 work consolidated the same-session volatility estimate and published corrected record. Full test suite (`python -m pytest -q`) was initiated but the session environment hung during execution of heavy test modules before completion; targeted consolidation tests were reported green in prior handoff (24 + 17 passed). No code changes made this cycle.

### Objective
Inventory real data and costs actually available in repository first, per AGENTS.md Market Opportunity Search step 1. Produce an evidence-based shortlist of plausible candidates scored against (a) data quality/access, (b) structural mechanism, (c) net capture, (d) robustness/power, (e) liquidity/capacity, (f) automation, (g) diversification.

### Acceptance criteria
- A new report under `research/reports/` documenting data inventory (files, date ranges, frequency, asset classes) and cost assumptions actually present in `config/` and `src/`.
- At least one candidate hypothesis file under `research/hypotheses/` with full required fields (mechanism, direction, horizon, universe, features, entry/exit, benchmark, confounders, falsification, cost model).
- No new dependency, no live trading, no fetcher call, no committed record/config modified.

### Validation commands
```bash
python -m pytest -q tests/test_tsmomentum_vol_estimate_consolidation.py tests/test_tsmomentum_same_session_vol_correction.py
git status --porcelain
```

### Scope boundaries
- Read-only on `data/` and `config/` except where a new hypothesis/report is added.
- No modification of committed records or configs.
- Single bounded task; do not dispatch workflow or start agent sessions.
