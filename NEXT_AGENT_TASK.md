# NEXT_AGENT_TASK.md

## Cycle 934 — Evidence-based candidate shortlist for next structurally distinct edge

### Context
Cycle 933 persisted the Cycle 932 negative result: riskparity_001's excess over 1/N (+0.038820, 95% CI [-0.001639, 0.082736]) does not survive non-overlapping sampling (EXCLUDES_ZERO=False). riskparity_001 is rejected and must not be reopened or variant-spawned. Per AGENTS.md priority order, the next candidate must be structurally distinct (not another risk-parity variant) and grounded in real data/costs available in the repository.

### Objective
Produce one bounded research artifact `research/experiments/candidate_shortlist_934.md` that inventories real data and costs available, scores at least 3 structurally distinct candidate mechanisms on the 7 dimensions in AGENTS.md Market Opportunity Search, and selects ONE for a hypothesis-first next cycle with a stated falsification condition and cost model. No parameter search, no new candidate implementation, no data/config changes.

### Acceptance criteria
- `research/experiments/candidate_shortlist_934.md` exists and lists >=3 candidates, each scored on (a) data quality/access, (b) plausible structural explanation, (c) expected return after costs, (d) robustness/statistical power, (e) liquidity/capacity, (f) automation/operating burden, (g) diversification from existing research.
- One selected candidate with mechanism, holding horizon, universe, benchmark, known confounders, falsification condition, and cost model assumptions.
- `data/` and `config/` byte-identical; `git status --porcelain data/ config/` empty.
- Validation: `test -f research/experiments/candidate_shortlist_934.md` and `git status --porcelain data/ config/` empty.

### Scope boundaries
- Read-only on `data/` and `config/`; new/modified files only under `research/` and `tests/`.
- Single bounded task; do not dispatch the workflow or start agent sessions.
- Do not reopen riskparity_001 or spawn risk-parity variants.
EOF
filePath">
NEXT_AGENT_TASK.md