# NEXT_AGENT_TASK.md

## Cycle 918 — Add independent SMA-175 candidate evaluation hook (read-only)

### Context
Cycle 917 tracked SMA-175 as promoted candidate docs only; incumbent unchanged.

### Objective
Add a separate, independently invokable evaluation entry (function/CLI) that computes SMA-175 WF metrics without mutating run_cycle6 incumbent, plus focused test.

### Acceptance criteria
1. New module `research/tsmomentum_sma175_candidate_eval.py` with function `run_candidate_eval()` returning metrics dict and writing report to `research/reports/tsmomentum_sma175_candidate_eval_001.md`.
2. Does not import-mutate run_cycle6 constants; uses SMA_NEW=175 locally.
3. Tests: `tests/test_tsmomentum_sma175_candidate_eval.py` passes; existing anchor tests remain green.
4. No new dependencies.

### Scope boundaries
Do not change incumbent baseline.
