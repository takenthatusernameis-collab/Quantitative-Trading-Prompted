# NEXT_AGENT_TASK.md

## Cycle 931 — Like-for-like mechanism comparison on the point-in-time-complete window

### Context
Cycle 929 measured the incumbent's point-in-time universe membership (the
published 48-fold mean mixes 7 folds on an incomplete cross-section with 41
on the complete one) and produced the `riskparity_001` shortlist row. Cycle
930 executed the pre-registered `riskparity_001` evaluation
(`research/reports/riskparity_001_evaluation.md`): the baseline (L = 63,
cap = 0.30) reaches a walk-forward mean OOS Sharpe of **0.778089** on the
point-in-time-complete window and **fails** the pre-registered gate 1 (0.9);
its excess over 1/N on the *same* 22 folds is **+0.005** with a correlation
of **0.991** to 1/N, and all nine pre-registered configurations fail gate 1
(0.7778 - 0.7844). The candidate is labelled **rejected**; it adds no
diversification and no incremental value over equal weight.

Three numbers now sit on the same point-in-time-complete window and the same
walk-forward design, but have never been placed side by side:

| Path | Walk-forward mean OOS Sharpe (same window / same folds) |
|---|---|
| 1/N equal weight (7 ETFs) | 0.773084 (measured in Cycle 930 as the benchmark) |
| `riskparity_001` (rejected) | 0.778089 |
| Incumbent `tsmomentum_spytrend_001` | 0.787522 (Cycle 929, complete-cross-section subsample) |

The published incumbent headline (0.947307) and the published 1/N reference
(0.4716) are measured on the *membership-heterogeneous* window, so the
published pair cannot be compared with the complete-cross-section pair.
AGENTS.md lists "incremental value" and "net capture feasibility" as decision
criteria, and both require a like-for-like comparison of the mechanisms on
one homogeneous window.

### Objective
Measure the incumbent, `riskparity_001` and 1/N on **one** point-in-time-
complete window under **one** walk-forward design and **one** cost model,
and state each mechanism's incremental value over 1/N (net of the committed
3 bp per unit of weight change) with the statistical support the window
allows. No new candidate, no parameter search, no re-tuning.

### Acceptance criteria
- A new report under `research/reports/` with, for each of the three paths on
  the same folds: walk-forward mean OOS Sharpe (backtest scale and canonical),
  positive-fold rate, pooled out-of-sample trades, the 3 bp/unit gate
  outcomes, the excess over 1/N, and a moving-block bootstrap 95% CI on the
  excess (fold-level, same seed and draw count as Cycle 929/930).
- The incumbent's path must be **recomputed** on the point-in-time-complete
  window from the committed cache and must reproduce the Cycle-929
  complete-cross-section figure (0.787522) to within 1e-6; a mismatch fails
  the run and is reported as a failure, not silently adjusted.
- The report states explicitly which of the two published statistics (0.947307
  headline / 0.4716 1/N reference) survives the homogeneous window and what
  that implies for the incumbent's **published verdict** (which must not be
  changed by this cycle: it stays a Credible Candidate by its published
  verdict and NO-GO for promotion).
- The decision label follows AGENTS.md ("Credible candidate" / "Exploratory
  signal" / "Rejected" / "Blocked by data") and is stated in the report and
  in a new experiment record under `research/experiments/`.
- No committed record, config, gate, protocol or shortlist row is modified; no
  dependency is added; the fetcher is not called; `data/` and `config/` are
  byte-identical after the run.

### Validation commands
```bash
python research/mechanism_comparison_001.py
python -m pytest -q tests/test_mechanism_comparison_001.py
python -m pytest -q tests/test_riskparity_001_evaluation.py
git status --porcelain data/ config/
```

### Scope boundaries
- Read-only on `data/` and `config/`; new files only under `research/` and
  `tests/`.
- No modification of committed records, configs, gates or shortlist rows.
- The published walk-forward, the promotion gates and the pre-registered
  hypothesis documents are inputs, not outputs.
- Single bounded task; do not dispatch the workflow or start agent sessions.
- Known environment issue: `tests/test_tsmomentum_vol_estimate_consolidation.py`
  and `tests/test_tsmomentum_same_session_vol_correction.py` did not complete
  within 8.6 minutes of wall clock in the Cycle-930 session, so the full
  suite (`python -m pytest -q`) is **not** a usable validation gate here; use
  the narrow commands above and report the timing of each.
