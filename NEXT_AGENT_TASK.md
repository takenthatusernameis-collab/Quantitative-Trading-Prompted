# NEXT_AGENT_TASK.md

## Cycle 937 — Investigate and document pairs_001 failure modes (without re-tuning)

### Context
Cycle 936 pre-registered and evaluated `pairs_001` (cointegrated-pairs relative value) on the committed nine-sector panel. The frozen specification (hypothesis `research/hypotheses/pairs_001.md`, config `config/pairs_candidate_001.yaml`, pre-registration commit hash published in the records) was executed unchanged by `research/pairs_001_evaluation.py` (OVERALL: PASS, exit 0). Verdict: **Rejected/Failed** — walk-forward mean OOS Sharpe **-0.829067**, positive-fold rate **0.250000**, pooled OOS trades **1380**, net excess over cash **-0.829067** with moving-block bootstrap 95% CI **[-1.219160, -0.467513]** (block 4, seed 20240101), net excess after pre-registered 25 bp/unit-of-short-notional borrow cost **-0.136774** annualized, DSR **-3.341643** (prob **0.000416**). Falsification conditions **(i), (iii), (iv)** fired; condition (ii) fired as well (CI excludes zero on the negative side). Cointegration test failed for at least one pair in training windows (any pair failed: True). Records: `research/experiments/pairs_001_evaluation.md`, `research/reports/pairs_001_evaluation.md`; tests `tests/test_pairs_001_evaluation.py` (6 passed).

`pairs_001` is **closed as Rejected/Failed**: not promoted, configuration retired as written, no variant opened, not re-ranked. The incumbent stays a Credible Candidate / NO-GO. Fixed Cycle-934 shortlist order remains: `reversal_001` (Rejected/Failed), `pairs_001` (Rejected/Failed), `liquidity_001` (24/35, rank 3), `leadlag_001` (16/35, rank 4). No closed line is reopened.

### Objective
Produce a read-only, deterministic analysis of why `pairs_001` failed without changing frozen artifacts or re-tuning. Identify which of the pre-registered failure modes drove rejection (Sharpe < 0.9, CI includes zero / negative excess, cointegration failure out of sample, borrow erasing edge) and quantify per-pair contributions. Leave the codebase unchanged except adding new read-only analysis artifacts under `research/` and `tests/` as specified.

### Acceptance criteria
- New read-only deterministic tool `research/pairs_001_failure_analysis.py` reads the frozen hypothesis/config and the committed evaluation artifacts (`research/experiments/pairs_001_evaluation.md`, `research/reports/pairs_001_evaluation.md`) without calling the fetcher and without modifying `data/` or `config/`. It must print `OVERALL: PASS` and exit 0, and two runs must be byte-identical.
- New record `research/experiments/pairs_001_failure_analysis.md` and report `research/reports/pairs_001_failure_analysis.md` containing: per-pair attribution from the published evaluation (net excess, turnover cost, borrow drag, Sharpe, trades), cointegration failure summary (which pairs failed in which folds/training windows per the published results), cost breakdown (turnover drag vs borrow drag) showing borrow's impact, a breakdown of which pre-registered conditions fired and their measured values, and a concrete hypothesis about the failure mechanism consistent with the evidence (without speculating beyond what's measured).
- New tests `tests/test_pairs_001_failure_analysis.py` covering: reads only committed artifacts (no data/config modified), reports all six pairs with attribution, states fired conditions with values, is deterministic across two runs, and `git status --porcelain data/ config/` remains empty.
- Validation: `test -f research/pairs_001_failure_analysis.py`, `test -f research/experiments/pairs_001_failure_analysis.md`, `test -f research/reports/pairs_001_failure_analysis.md`, `python research/pairs_001_failure_analysis.py` prints `OVERALL: PASS` and exits 0, `python -m pytest -q tests/test_pairs_001_failure_analysis.py` passes, `git status --porcelain data/` is empty, `git diff --name-only HEAD -- config/settings.yaml` is empty.

### Scope boundaries
- Read-only on `data/`, `config/` (except no changes), `src/`. Only add files under `research/` and `tests/`.
- No re-tuning, no parameter changes, no new pairs, no reopening closed candidates. Do not modify `pairs_001_evaluation.py`, the frozen hypothesis/config, or the published evaluation records.
- Do not dispatch workflows or start agent sessions.
