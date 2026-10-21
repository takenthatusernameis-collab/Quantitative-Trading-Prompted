# NEXT_AGENT_TASK.md

## Cycle 935 — Pre-register and evaluate `reversal_001` (cross-sectional short-horizon reversal)

### Context
Cycle 934 produced an evidence-based candidate shortlist (`research/experiments/candidate_shortlist_934.md`, tool `research/candidate_shortlist_934.py`, OVERALL: PASS, 16 structural checks). The committed Cycle-11 shortlist is exhausted (every row carries a committed outcome record), so Cycle 934 built a new shortlist from what `data/` actually holds, quoted the committed status line of every closed line, scored four structurally distinct mechanisms on the seven AGENTS.md dimensions, and selected **one** under a rule fixed before the scores were read: `reversal_001` (28/35; next best `pairs_001` 25/35, `liquidity_001` 24/35, `leadlag_001` 16/35).

`reversal_001`: rank the nine GICS sector ETFs (XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY — the repository's only membership-stable cross-section: identical cached history, 6991 sessions, 1998-12-22 .. 2026-10-08, no gaps) by the trailing 5-session return; hold the bottom quintile (2 of 9) at equal weight and cash otherwise; rebalance every 5th session; the signal formed at t is effective at t+1. Benchmark: 1/N equal-weight of the same nine sectors. Cost model: 3.0 bp per unit of weight change (1.0 bp commission + 2.0 bp slippage, `config/settings.yaml`), no borrow (long-only), turnover 52 units/yr = 1.5600%/yr drag under the committed one-book-rotation-per-rebalance convention. The pre-registered **cost hurdle**: the rule must capture at least **2.0047%** of the measured cross-sectional dispersion (77.8181%/yr of scale) per rebalance to break even.

No candidate's verdict changes in Cycle 934; the incumbent stays a Credible Candidate / NO-GO. `riskparity_001` remains rejected and is not reopened; no closed line is reopened and no variant of one is proposed.

### Objective
Pre-register `reversal_001` (hypothesis + frozen config, committed **before** any backtest is executed) and then evaluate it config-faithfully on the nine-sector panel, reporting the benchmark-relative net excess, its moving-block bootstrap 95% CI, the walk-forward gate table, the mirror test against the rejected sector-momentum signal on the same panel, and the measured gross capture fraction against the 2.0047% cost hurdle.

### Acceptance criteria
- `research/hypotheses/reversal_001.md` and `config/reversal_candidate_001.yaml` exist and contain: mechanism, expected direction and magnitude (declared prior, marked as such), holding horizon (5 sessions, weekly rebalance, 1-session lag), asset universe (the nine sector ETFs), features and data sources, entry/exit rules, benchmark (1/N of the same nine), known confounders (the six published in `research/experiments/candidate_shortlist_934.md`), falsification condition (the five published parts), cost model assumptions, and the pre-registered trial count. The pre-registration must be **frozen before the backtest runs** (the commit hash of the pre-registration is published with the result).
- A read-only, deterministic tool evaluates the frozen configuration on the committed parquet cache (the fetcher is never called) under the 10y/12m/6m walk-forward design with 21-day purge and 21-day embargo, and publishes: the walk-forward mean OOS Sharpe (backtest and canonical scales), the positive-fold rate, the pooled OOS trades, the three gate outcomes, the benchmark-relative net excess with its moving-block bootstrap 95% CI, the **mirror test** against the rejected sector-momentum signal on the same panel, and the measured gross capture fraction against the 2.0047% cost hurdle.
- The verdict follows the pre-registered falsification condition only; no threshold, gate or cost model is changed after the result is known.
- `data/` and `config/` are byte-identical before and after the run except for the one new pre-registration config file; `git status --porcelain data/` is empty and `git diff --name-only HEAD -- config/` shows only the new pre-registration file.
- Validation: `test -f research/hypotheses/reversal_001.md`, `test -f config/reversal_candidate_001.yaml`, `test -f research/experiments/reversal_001_evaluation.md`, the new tool prints `OVERALL: PASS` and exits 0, `python -m pytest -q tests/test_reversal_001_evaluation.py` passes, and `git status --porcelain data/` is empty.

### Scope boundaries
- Hypothesis-first: the hypothesis and the config are written and frozen before any backtest is executed; a result obtained before the freeze does not count.
- One baseline rule, one pre-registered trial count; no parameter search and no variant grid.
- The nine-sector panel is the candidate's universe; the incumbent's seven-asset universe and every closed candidate line are read-only references.
- Read-only on `data/`; new/modified files only under `research/`, `tests/` and the one new `config/reversal_candidate_001.yaml`.
- Single bounded task; do not dispatch the workflow or start agent sessions.
- Do not reopen `riskparity_001` or any other closed line, and do not spawn variants of them.

### Bounded follow-up left open by Cycle 934 (not part of this task, do not start here)
`research/futures_roll_visibility.py` (Cycle 884) still describes an ex-post roll classifier as "without looking ahead", and its ground-truth constant is a manual external observation with no committed, reproducible provenance. Cycle 934 disclosed both limits where it used the detector and left the module untouched. Closing that documentation/provenance line is a separate bounded task.
