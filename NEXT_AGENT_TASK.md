# NEXT_AGENT_TASK.md

## Cycle 932 — Independent-sample significance of the riskparity_001 excess over 1/N

### Context
Cycle 931 placed 1/N (0.603562), riskparity_001 (0.642829) and the incumbent (0.787524) on the same 41 point-in-time-complete folds. riskparity_001's excess over 1/N is +0.039267 with a moving-block bootstrap 95% CI [0.006458, 0.079121] that excludes zero, while the incumbent's excess +0.183963 has a CI that includes zero. The 41 folds overlap (12-month test on a 6-month step), so the CI is on a serially dependent fold set, not independent samples.

### Objective
Recompute the riskparity_001 vs 1/N excess on a non-overlapping annual subset of the same point-in-time-complete window and report whether the significance survives; no parameter search, no new candidate.

### Acceptance criteria
- A new report under `research/reports/` with the annual (non-overlapping) fold subset, the excess over 1/N, and a bootstrap 95% CI (same seed 20240101).
- `data/` and `config/` byte-identical; no fetcher call.
- Validation: `python research/mechanism_comparison_001.py` still passes; `git status --porcelain data/ config/` empty.

### Scope boundaries
- Read-only on `data/` and `config/`; new files only under `research/` and `tests/`.
- Single bounded task; do not dispatch the workflow or start agent sessions.
