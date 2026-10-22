# Cycle 951 — Publish the `commoditytrend_001` rejection and close the line

## Context
- Cycle 950 committed the extended four-instrument commodity panel (BNO 2010-06-02, UNG 2007-04-18, DBC/GLD byte-identical to cache) and ran the frozen evaluation: `VERDICT|Rejected/Failed`, `FROZEN_CONDITIONS_FIRED|wf_mean_oos_sharpe,benchmark_relative_excess_ci,fold_or_trade_gate,no_post_2010_excess`.
- The candidate is not promoted and no variant is opened.

## Objective
Record the verdict durably (README + hypothesis status + experiment record), update the candidate's status line, and leave the repository in a clean, verified state.

## Acceptance criteria
1. README.md gains a Cycle 950/951 entry stating the verdict and fired conditions.
2. `research/hypotheses/commoditytrend_001.md` status updated to Rejected/Failed with fired conditions.
3. `git status --porcelain data/ config/` empty.
4. `python research/commoditytrend_001_evaluation.py` -> OVERALL: PASS, exit 0.
5. `python -m pytest -q` passes.

## Scope boundaries
- No new candidates, no re-tuning, no promotion.
- Do not modify data/ or config/.
