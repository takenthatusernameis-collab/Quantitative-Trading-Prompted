# NEXT_AGENT_TASK.md

## Cycle 908 — Measure `csmomentum_001`'s walk-forward under a **non-overlapping (embargoed) fold design** and publish the delta against the published protocol

### Context

Cycle 907 re-derived `csmomentum_001`'s **config-faithful** walk-forward on the three samples
that `config/sample_policy.yaml` pre-registers for it and published the three gate tables side
by side (`research/reports/csmomentum_common_inception_gate_001.md`,
`research/experiments/csmomentum_common_inception_001.md`):

| Sample | Sessions | Folds | WF mean OOS Sharpe (backtest scale) | Median | Positive folds | Pooled OOS trades | Gate 1 (>= 0.9) | Decision |
|---|---|---|---|---|---|---|---|---|
| `union_sample` | 8,482 | 48 | 0.6975 | 0.6179 | 79.17% | 400 | FAIL | Rejected/Failed |
| `common_inception_slice` | 5,202 | 21 | 0.5861 | 0.6311 | 76.19% | 166 | FAIL | Rejected/Failed |
| `common_inception_window` | 5,202 | 21 | 0.5861 | 0.6311 | 76.19% | 166 | FAIL | Rejected/Failed |

Two of Cycle 907's published findings are the reason for this cycle.

1. **The walk-forward's folds are not independent observations.** The pre-registered design
   steps the folds by 6 months over a 12-month test window, so consecutive test windows overlap
   by ~175 days, and the repository's generator
   (`src/evaluation/walkforward.py:generate_walkforward_splits`) **accepts but never applies** the
   configuration's 21-day `embargo_days`: the next fold's rolling training window contains the
   tail of the previous fold's test window (fold 1: train 1993-01-01..2002-08-29, test
   2002-09-30..2003-09-16; fold 2: train 1993-06-28..2003-02-21, test 2003-03-25..2004-03-10).
   The honest count of pairwise-disjoint test windows is **24** (union sample) and **11**
   (common-inception samples) — not the 48 and 21 that the gate table counts, and the promotion
   gate's "> 100 pooled OOS trades" screen counts trade days inside overlapping windows.
2. **The verdict is robust, but the protocol question is open.** The gate-1 margin
   (0.2025 on the union sample, 0.3139 on the common-inception samples) is larger than the
   fold-to-fold scatter (fold-Sharpe std 0.7784 over 48 folds), and a matched-fold-window
   sensitivity returned identical numbers for all three paths (0.7108 on 20 shared test windows).
   What has **not** been measured is how much of the walk-forward evidence survives a fold
   design whose test windows do **not** overlap — the design the configuration's own embargo
   parameter describes.

Every published walk-forward record in the repository (the candidate's own 48-fold record in
`research/experiments/csmomentum_001_experiment_001.md`, the Cycle 871 config-faithful record in
`research/reports/month_end_candidate_reaudit_001.md`, the baseline walk-forward records) was
produced by the same generator, so the answer is a property of the **published protocol**, not
of one candidate.

The protocol question is sharpest on a record that sits **close** to its gate:
`research/reports/sectorrotation_long_sample_feasibility_001.md` publishes **36** pre-registered
folds with a walk-forward mean OOS Sharpe of **0.847243** against its own gate of 0.9 — a
margin of **0.053**, five times smaller than `csmomentum_001`'s 0.2025 — and those 36 folds come
from the same generator with the same overlapping-fold property. (That candidate is NO-GO on
three other gates — `full_period_sharpe`, `max_drawdown`, `psr` — so its verdict would not flip;
the point is that a protocol-level change of this size is not negligible in general.)

### Objective

Quantify how much of `csmomentum_001`'s walk-forward evidence survives a **non-overlapping
(embargoed)** fold design, publish the delta against the published protocol next to the
published numbers, and state whether the published **Rejected/Failed** verdict survives — as a
**published sensitivity**, without changing the published protocol, the shared generator, any
committed record, or the verdict.

### Acceptance criteria

1. **New tool** `research/csmomentum_walkforward_embargo_audit.py` (read-only w.r.t. `data/`,
   `config/` and every committed artifact) that:
   * **reuses** the Cycle 907 machinery instead of re-implementing it — the config-faithful
     path (`src/backtest/rebalance.py:build_month_end_weights` as executed by
     `research/month_end_candidate_reaudit.py`), the policy consumption and the read-only cache
     loader (`research/csmomentum_common_inception_audit.py`) — and adds no new data path;
   * consumes `config/sample_policy.yaml` -> `candidates.csmomentum_001` and **fails closed**
     when the policy is missing/malformed or the candidate section is invalid;
   * builds, for each of the three pre-registered samples, **three** fold designs over the
     same continuously computed point-in-time path, each with its rule stated verbatim in the
     report:
     * the **published design** (as in Cycle 907: 10y train / 12m test / 6m step, 21d purge,
       the repository's generator) — the reference every delta is measured against;
     * **Design A (non-overlapping test windows, the primary sensitivity)**: the step is set to
       the generator's own test-window length (`int(test_months * 21)` = 252 sessions, i.e. the
       6-month step becomes a 12-month step) so that consecutive test windows are exactly
       adjacent and share **no** session. The training window (10y), the 21-day purge, the
       12-month test window and the fixed parameters are unchanged; the training windows still
       roll over earlier test windows (a 10-year training window cannot avoid that), which is
       exactly why the *test* windows are the observations that must be disjoint. Expected
       result: **24** folds on the union sample and **11** on the common-inception samples —
       the same numbers as the "maximum number of pairwise-disjoint test windows" published in
       Cycle 907, which is the executable cross-check;
     * **Design B (the configuration's embargo applied literally, informational)**: the next
       fold's **training** window starts after the previous fold's test window ends plus the
       configured 21-day embargo. Publish the resulting fold count and state plainly whether
       the design can support a gate table at all — the expected result is that it cannot
       (a 10-year rolling training window plus a 12-month test window plus a purge plus the
       embargo consumes ~2814 sessions per fold, so the union sample yields only a handful of
       folds). Publish Design B's numbers if they exist; do **not** force a gate table out of
       a design with too few folds;
   * evaluates the **pre-registered** gate table (`evaluation.promotion_gates`, backtest scale
     only) on the published design and on Design A, and publishes, per sample and per design:
     fold count, the fold table (train window, test window, OOS Sharpe), mean / median OOS
     Sharpe, positive fold rate, pooled OOS trades, every gate with its observed value and
     pass/fail, the decision, and the **plateau gate as NOT EVALUATED** with the reason;
   * publishes the **delta** between the published design and Design A (fold count, mean OOS
     Sharpe, the gate-1 margin) and states whether the published **Rejected/Failed** verdict
     survives Design A;
   * publishes the **independence diagnostic** for every design: the mean consecutive
     test-window overlap in days and the maximum number of pairwise-disjoint test windows
     (an executable check, not a claim) — Design A must show a zero overlap and a disjoint
     count equal to its fold count;
   * writes `research/reports/csmomentum_walkforward_embargo_001.md`, writes **nothing** under
     `data/` or `config/`, **does not modify** any committed artifact (verified by fingerprint
     before/after), and **exits non-zero** if any structural check fails.
2. **Reproduction anchor (the tool's own OVERALL depends on it):** the *published* design must
   again reproduce the Cycle 907 record on `union_sample` — **48 folds, WF mean OOS Sharpe
   0.6975** (backtest scale), median 0.6179, positive fold rate **79.17%**, **400 pooled OOS
   trades** — at the tolerance of the last published decimal. The legacy calendar-path value
   (0.6868) and the daily re-rank value (0.6928) must **not** be produced.
3. **Scope of the sensitivity:** the two new designs are *published sensitivities*, not new
   protocols. `src/evaluation/walkforward.py` must **not** be changed, no published record may be
   rewritten, and the published protocol's numbers must remain the ones the committed records
   state. If Design A changes any gate outcome, **report** the difference and stop there;
   changing the published protocol is a separate, explicitly decided cycle.
4. **Tests** `tests/test_csmomentum_walkforward_embargo_audit.py`: the policy fails closed on a
   missing/malformed/invalid candidate section; the anchor reproduces (criterion 2); **Design
   A's test windows are pairwise disjoint and the published design's are not** (an executable
   check on the published fold windows, not a claim in prose); `data/` and `config/` are
   byte-identical before and after; the committed artifacts
   (`research/experiments/csmomentum_001_experiment_001.md`,
   `research/experiments/csmomentum_baseline_wf_001.md`,
   `research/reports/month_end_candidate_reaudit_001.md`,
   `research/reports/promotion_feasibility_backtest_001.md`,
   `research/reports/csmomentum_common_inception_gate_001.md`) are byte-identical before and
   after; two consecutive runs produce an identical report and stdout.
5. **Experiment record** `research/experiments/csmomentum_walkforward_embargo_001.md`
   (hypothesis reference, data source/date range/frequency/universe, point-in-time treatment,
   configuration, splits — both designs stated exactly —, all metrics, trial count, the
   independence diagnostic, reproduction commands) and a **README cycle entry** (newest at the
   top, as the file is append-proof).
6. `git status --porcelain data/` empty; only the intended new/modified files changed; the full
   test suite green.

### Validation commands

```
python research/csmomentum_walkforward_embargo_audit.py   # OVERALL: PASS, exit 0
python research/csmomentum_sample_gate_audit.py            # the Cycle 907 tool still passes
python research/month_end_candidate_reaudit.py              # the committed record is unchanged
python -m pytest -q tests/test_csmomentum_walkforward_embargo_audit.py
python -m pytest -q tests/test_csmomentum_sample_gate_audit.py
python -m pytest -q
git status --porcelain data/
git diff --stat src/ config/ research/experiments/ research/reports/month_end_candidate_reaudit_001.md
```

### Scope boundaries

* Do **not** change `src/evaluation/walkforward.py` (the shared generator), the published
  protocol, or any published record: Designs A and B live in the new tool only and are published
  as sensitivities.
* Do **not** change gates, thresholds, decision mapping, universe, cost model, Sharpe
  convention, parameters, or `config/csmomentum_candidate_001.yaml` / `config/sample_policy.yaml`
  (read the policy, do not edit it).
* Do **not** modify any committed artifact: the experiment records, the Cycle 872 re-audit
  report, the promotion artifact, the Cycle 905/906 audit report or the Cycle 907 gate report.
  If Design A changes the verdict, **report** the difference and stop there.
* Do **not** execute the 27-configuration robustness grid or any re-optimisation; the plateau
  gate is reported as NOT EVALUATED (as the published record already does).
* Do **not** touch the paper-trading / simulation path or the live configuration.
* Do **not** promote, re-fit or re-rank anything: this cycle is a measurement.
* All three designs must remain fixed-parameter and point-in-time; no per-fold re-optimisation;
  the 21-day purge stays; the designs change **only** the fold calendar.
* The new tool must not call `fetch_universe`/the fetcher: every price comes from the committed
  parquet cache, read-only.
* Extending the measurement to `sectorrotation_001`'s published record (36 folds, mean OOS
  Sharpe 0.847243 against its 0.9 gate) is **out of scope for this cycle** — publish the
  protocol-level evidence for `csmomentum_001` first; a separate cycle may apply it to the
  other candidates.
