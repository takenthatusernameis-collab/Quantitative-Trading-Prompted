# NEXT_AGENT_TASK.md

## Cycle 933 — Record Cycle 932 negative result for riskparity_001 vs 1/N

### Context
Cycle 932 recomputed riskparity_001's excess over 1/N on a non-overlapping annual subset (21 folds, even folds 8..48): excess +0.038820, 95% CI [-0.001639, 0.082736], EXCLUDES_ZERO=False. The Cycle 931 significance on 41 overlapping folds did not survive non-overlapping sampling. riskparity_001 remains a rejected candidate; its edge over 1/N is not robust.

### Objective
Persist the negative result durably: append a Cycle 932 section to the riskparity_001 evaluation experiment record (or create `research/experiments/riskparity_001_annual_subset_932.md`) documenting the annual subset, excess, CI, and conclusion that significance does not survive. No parameter search, no new candidate, no data/config changes.

### Acceptance criteria
- A new or updated experiment record under `research/experiments/` citing `research/reports/annual_subset_riskparity_vs_oneoverN_932.md` with N_FOLDS=21, EXCESS=0.038820, CI=[-0.001639,0.082736], EXCLUDES_ZERO=False.
- `data/` and `config/` byte-identical; no fetcher call.
- Validation: `python research/annual_subset_riskparity_vs_oneoverN_932.py` still passes; `git status --porcelain data/ config/` empty.

### Scope boundaries
- Read-only on `data/` and `config/`; new/modified files only under `research/` and `tests/`.
- Single bounded task; do not dispatch the workflow or start agent sessions.
- Do not run further parameter searches or new candidates on this evidence.
EOF