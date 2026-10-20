# NEXT_AGENT_TASK.md

## Cycle 906 — Re-derive `csmomentum_001`'s walk-forward evaluation on the pre-registered common-inception sample

### Context

Cycle 905 pre-registered the sample-definition control for `csmomentum_001` in
`config/sample_policy.yaml` (`candidates.csmomentum_001`): the candidate's long-sample
diagnostic gate table is evaluated on `common_inception_slice`
(**2006-02-06** = max of the per-symbol first dates of the 18-asset universe, re-derived
from `data/raw`, never a frozen date), with `common_inception_window` (warm-up preserved)
and `union_sample` published alongside. The policy states the control must exist
**before `csmomentum_001` is executed**.

The candidate's own published records were executed **before** that control existed and
on the **union calendar**:

* `research/experiments/csmomentum_001_experiment_001.md` — "Full Sample
  (1993-01-29 to 2026-10-09)", walk-forward **46 folds**, mean OOS Sharpe **0.6619**
  (daily re-rank path; its walk-forward block is *not* reproducible, see the Cycle 872
  report), verdict **Rejected/Failed** (gate: WF mean OOS Sharpe >= 0.9).
* `research/reports/month_end_candidate_reaudit_001.md` — the **config-faithful**
  path (`src/backtest/rebalance.py:build_month_end_weights`), window
  **1993-01-29..2026-10-09 (8,482 sessions)**, **48 folds**, WF mean OOS Sharpe
  **0.6975** (backtest scale; canonical 0.8404), median 0.6179, positive fold rate
  **79.17%**, **400 pooled OOS trades** — verdict unchanged (Rejected/Failed).

On that union sample the cross-section is **ragged**: price width 1 -> 18 (the 18-asset
universe is only fully populated from **2006-02-06**), and the walk-forward's earliest
folds are therefore trained on a cross-section that is a **single asset** — a
time-series bet, not a cross-sectional one. Cycle 905's measurement
(`research/reports/csmomentum_common_inception_audit_001.md`) quantifies this on the
**union** sample: **273** sessions with **zero** selectable assets and **1,763 of 8,488
sessions (20.8%) with fewer than five** — i.e. inside the `select_top_decile`
single-asset fallback — while the common-inception slice has 273 such sessions (the
warm-up ramp: lookback 252 + skip 21) and the warm-up-preserving window has none
(opening selectable breadth 0 vs 17).

So the candidate's published gate table was measured on a sample the policy now
forbids for gate-table evaluation. This cycle closes that gap: it measures the
candidate's **config-faithful** walk-forward on the three pre-registered samples and
states whether the **Rejected/Failed** verdict is an artefact of the sample definition
(the same question Cycle 903 asked, and answered "no", for the incumbent).

### Objective

Measure `csmomentum_001`'s walk-forward evaluation on the pre-registered samples and
publish the three gate tables side by side, without changing any gate, threshold,
decision mapping, universe, cost model, parameter, committed artifact or verdict.

### Acceptance criteria

1. **New tool** `research/csmomentum_sample_gate_audit.py` (read-only w.r.t. `data/`,
   `config/` and every committed artifact) that:
   * consumes `config/sample_policy.yaml` -> `candidates.csmomentum_001` and **fails
     closed** when the policy is missing/malformed or the candidate section is invalid;
   * **re-derives** the common inception from `data/raw` at run time (never a frozen
     date) and publishes the per-symbol cache fingerprint;
   * builds **three** paths with the **config-faithful month-end schedule**
     (`src/backtest/rebalance.py:build_month_end_weights` — *not* the daily re-rank and
     *not* the legacy calendar rule): `union_sample`, `common_inception_slice`
     (price frame truncated at the common inception, so the signal has no warm-up) and
     `common_inception_window` (union frame kept, evaluation window truncated);
   * evaluates the **pre-registered** walk-forward protocol of
     `config/csmomentum_candidate_001.yaml` (`evaluation.walk_forward`: 10y train / 12m
     test / 6m step, 21d purge, 21d embargo, fixed parameters; fold windows are slices
     of one continuously computed point-in-time path) and the **pre-registered** gate
     table (`evaluation.promotion_gates`: WF mean OOS Sharpe >= 0.9, positive fold rate
     >= 0.5, pooled OOS trades > 100, plateau >= 2/3 lookbacks), on the **backtest
     scale** (`backtest_sharpe_ratio`) on which the candidates' gate was originally
     evaluated — the canonical scale may be published beside it but the gate table uses
     one scale only and states which;
   * publishes, per sample: fold count, the fold table (test window, OOS Sharpe), mean
     / median OOS Sharpe, positive fold rate, pooled OOS trades, every gate with its
     observed value and pass/fail, the decision, and the **plateau gate as NOT
     EVALUATED** with the reason (the 27-config grid is out of scope this cycle);
   * publishes the **degenerate-fold diagnostic**: for every fold, the number of assets
     with a price and the number with a valid momentum at the fold's training-window
     end (the mechanism by which the union sample differs from the common-inception
     sample), plus the count of folds trained on a cross-section narrower than the
     selection fallback threshold (5 assets, `src/features/momentum.py`) — on the union
     sample **1,763 of 8,488 sessions** are inside that single-asset fallback regime;
   * writes `research/reports/csmomentum_common_inception_gate_001.md`, writes **nothing**
     under `data/` or `config/`, **does not modify** any committed artifact (verified by
     fingerprint before/after), and **exits non-zero** if any structural check fails.
2. **Reproduction anchor (the tool's own OVERALL depends on it):** on `union_sample`,
   with the config-faithful path and the published window **1993-01-29..2026-10-09**,
   the tool must reproduce the committed config-faithful numbers of
   `research/reports/month_end_candidate_reaudit_001.md` — **48 folds, WF mean OOS
   Sharpe 0.6975** (backtest scale), median 0.6179, positive fold rate **79.17%**,
   **400 pooled OOS trades** — at the tolerance of the last published decimal. The
   legacy calendar-path value (0.6868) and the daily re-rank value (0.6928) must
   **not** be produced.
3. **Sample scope:** the evaluation window ends at the frozen
   `evaluation.splits.test_end` (**2026-10-09**); the six cached sessions
   2026-10-12..2026-10-19 are outside the pre-registered window and must not be added
   (they are the reason the published window is 8,482 sessions and not 8,488).
4. **Tests** `tests/test_csmomentum_sample_gate_audit.py`: the policy fails closed on a
   missing/malformed/invalid candidate section; the common inception is re-derived from
   the raw cache and equals the max of the per-symbol first dates; the tool reproduces
   the committed config-faithful union-sample record (criterion 2); `data/` and
   `config/` are byte-identical before and after; the committed artifacts
   (`research/experiments/csmomentum_001_experiment_001.md`,
   `research/experiments/csmomentum_baseline_wf_001.md`,
   `research/reports/month_end_candidate_reaudit_001.md`,
   `research/reports/promotion_feasibility_backtest_001.md`) are byte-identical before
   and after; two consecutive runs produce an identical report and stdout.
5. **Experiment record** `research/experiments/csmomentum_common_inception_001.md`
   (hypothesis reference, data source/date range/frequency/universe, point-in-time
   treatment, configuration, splits, all metrics, trial count, reproduction commands)
   and a **README cycle entry** (newest at the top, as the file is append-proof).
6. `git status --porcelain data/` empty; only the intended new/modified files changed;
   the full test suite green.

### Validation commands

```
python research/csmomentum_sample_gate_audit.py          # OVERALL: PASS, exit 0
python -m pytest -q tests/test_csmomentum_sample_gate_audit.py
python -m pytest -q tests/test_csmomentum_common_inception_audit.py
python -m pytest -q
git status --porcelain data/
git diff --stat research/experiments/ research/reports/month_end_candidate_reaudit_001.md
```

### Scope boundaries

* Do **not** execute the 27-configuration robustness grid or any re-optimisation; the
  plateau gate is reported as NOT EVALUATED (as the published record already does).
* Do **not** change gates, thresholds, decision mapping, universe, cost model, Sharpe
  convention, parameters, or `config/csmomentum_candidate_001.yaml` /
  `config/sample_policy.yaml` (read the policy, do not edit it).
* Do **not** modify any committed artifact: the experiment records, the Cycle 872
  re-audit report, the promotion artifact, or the Cycle 905 audit report. If the
  common-inception decision differs from the published one, **report** the difference
  and stop there; updating the published record is a separate cycle.
* Do **not** touch the paper-trading / simulation path or the live configuration.
* Do **not** promote, re-fit or re-rank anything: this cycle is a measurement.
* The walk-forward must remain fixed-parameter and point-in-time; no per-fold
  re-optimisation, and the purge/embargo must be honoured on the new sample.
