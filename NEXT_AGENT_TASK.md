# NEXT_AGENT_TASK.md

## Cycle 911 — Measure how much of `tsmomentum_spytrend_001`'s published walk-forward **mean** depends on the fold calendar and on thin-trade folds (read-only robustness of the published statistic)

### Context

Cycle 910 applied the non-overlapping (embargoed) fold sensitivity to the incumbent
`tsmomentum_spytrend_001` (the only candidate in the repository whose published walk-forward
**passes** its gate). The published record
`research/experiments/tsmomentum_regime_filter_wf_001.md` reports 48 folds, WF mean OOS Sharpe
**0.9473** (gate >= 0.9, margin **+0.0473**), 91.7% positive folds, 6013 pooled trades.

Cycle 910 reproduced that record exactly from the committed cache (48/48 folds, aggregate MATCH)
and added three measurements that are new evidence and that this cycle's task follows from:

1. **Design A (24 pairwise-disjoint folds, step = test window length) gives a *higher* mean:
   1.3850** (median 1.4204, 91.67% positive, 2952 pooled trades) against the published 0.9473.
   The gate-1 outcome does **not** change (PASS -> PASS) and the margin *grows* from +0.0473 to
   +0.4850, so the incumbent's published PASS is **not** an artefact of fold overlap.
2. **The published 48-fold mean is a 50/50 mixture of two disjoint 24-fold sub-designs that
   differ by 0.88 Sharpe.** The generator (`src/evaluation/walkforward.py:generate_walkforward_splits`)
   steps the folds by 6 months over a 12-month test window, so the published folds are
   `phase A` (folds 1, 3, 5, ...; mean **1.3850**, this is Design A) and `phase B`
   (folds 2, 4, 6, ...; mean **0.509580**). The published mean is their average, 0.9473.
   **Under phase B alone the gate-1 outcome would be FAIL (0.5096 < 0.9)**, so the published
   margin of +0.0473 is not a phase-stable property of the protocol.
3. **The published mean is dominated by two thin-trade folds.** The published fold table contains
   fold 12 (test 2008-01-22..2009-01-07, **2 trades**, OOS Sharpe **-21.8299**) and fold 13
   (**8 trades**, OOS Sharpe -0.2665). Leave-one-out on the published 48 folds: removing fold 12
   moves the mean from 0.947307 to **1.431928** (+0.4846); removing fold 13 moves it to 0.973441
   (+0.0261). The trimmed mean (drop min and max) is 1.378012; the published median is 1.293299.
   The published 0.9473 therefore sits **0.44 below** the median of the same fold set.

The incumbent's published PASS rests on a statistic that is sensitive to the fold phase and to
folds with a handful of trades. That is a **protocol-level** question (it is a property of how the
repository computes and gates a walk-forward mean), not a candidate-specific one, and it is the
question this cycle must answer. It must be answered as a **read-only sensitivity**: the published
protocol, the gates and the published record stay untouched.

### Objective

Quantify, for the incumbent `tsmomentum_spytrend_001`, how much of the published walk-forward
**mean OOS Sharpe** (0.9473) depends on (a) the fold phase of the pre-registered 6-month step and
(b) the two thin-trade folds, publish the decomposition and the influence table, and state
explicitly whether the published gate outcome is stable under those two documented weaknesses.
Do not change the published protocol, the gates, the thresholds, the universe, the cost model, the
parameters, the candidate configuration or any committed artifact.

### Acceptance criteria

1. **New tool** `research/tsmomentum_walkforward_embargo_audit.py`'s successor (new file, e.g.
   `research/tsmomentum_walkforward_mean_robustness_audit.py`) that is read-only with respect to
   `data/`, `config/` and every committed artifact, and that:
   - Reuses the Cycle 910 machinery (cache-only close panel from the committed parquet cache, the
     committed candidate definition from `research/run_cycle6.py`, the committed overlay
     `_apply_overlay`, `src/evaluation/walkforward.py:generate_walkforward_splits`); **the fetcher
     must never be called**.
   - **Reproduction anchor (mandatory):** the published design must reproduce the published
     record's 48 folds, mean OOS Sharpe **0.9473**, 91.7% positive folds and 6013 pooled trades
     within the last published decimal, and the published record must again be resolved **by
     content** (the file that carries the published aggregate table and fold table), not by a
     hard-coded filename. The tool fails closed if the anchor does not reproduce.
   - Publishes the **phase decomposition**: the two disjoint 24-fold sub-designs of the published
     48 folds (phase A = folds 1, 3, 5, ...; phase B = folds 2, 4, 6, ...), each with fold count,
     mean/median OOS Sharpe, positive fold rate, pooled OOS trades and its own gate table
     (gate 1 >= 0.9, gate 2 positive fold rate >= 0.5, gate 3 pooled OOS trades > 100 -- the
     pre-registered thresholds of the published record and `AGENTS.md`), plus the published mean's
     position between them.
   - Publishes the **fold-influence table** for the published 48 folds: per fold its OOS Sharpe,
     trade count, leave-one-out mean, and the shift in the published mean; and publishes the
     published mean, the published median, the trimmed mean (min and max removed) and the
     leave-one-out mean of the two thin-trade folds (<= 10 trades) explicitly.
   - States, in one explicit line each: (i) whether the published gate-1 outcome changes under
     phase A and under phase B, (ii) whether it changes when the thin-trade folds are excluded,
     and (iii) whether the published PASS is therefore **stable** or **not stable** against the two
     documented weaknesses. It must not change the published protocol or the published verdict.
   - Fails closed if any required input is missing or malformed; nothing under `data/` or `config/`
     is written.
2. **Artifacts**:
   - Write `research/reports/tsmomentum_walkforward_mean_robustness_001.md` (deterministic)
   - Write `research/experiments/tsmomentum_walkforward_mean_robustness_001.md` (experiment record:
     hypothesis reference, data, configuration, splits, metrics, influence table, trial count,
     reproduction commands)
   - Do **not** modify any committed artifact (in particular not
     `research/experiments/tsmomentum_regime_filter_wf_001.md`).
3. **Tests** `tests/test_tsmomentum_walkforward_mean_robustness_audit.py` with checks:
   - the anchor reproduces the published design (48 folds, 0.9473, 6013 pooled trades) within the
     published-decimal tolerance, and the published record is resolved by content
   - the phase decomposition is exact: the two sub-designs are pairwise disjoint, their union is the
     published fold set, and their means average to the published mean
   - the leave-one-out table is internally consistent (recomputing the leave-one-out mean of the
     most influential fold from the published fold Sharpes reproduces the published value)
   - `data/` and `config/` byte-identical before and after the run
   - committed artifacts byte-identical before and after the run (including
     `research/experiments/tsmomentum_regime_filter_wf_001.md`)
   - two consecutive runs produce identical report and experiment record (bit-for-bit deterministic)
   - fails closed on a malformed/missing published record and on a missing cached price file
4. **Verification commands** (must all pass):
   ```
   python research/tsmomentum_walkforward_mean_robustness_audit.py   # OVERALL: PASS, exit 0
   python -m pytest -q tests/test_tsmomentum_walkforward_mean_robustness_audit.py
   python -m pytest -q
   git status --porcelain data/
   git diff --stat src/ config/ research/experiments/ research/reports/
   ```

### Scope boundaries
- Sensitivity/measurement only; do not change the published protocol, the gates, the thresholds, the
  universe, the cost model, the parameters or the candidate configuration
- Do not change `src/evaluation/walkforward.py` and do not "fix" the generator's unapplied
  `embargo_days`; the weakness is published, not fixed
- Do not re-open, re-rate or re-decide the incumbent's published verdict; the cycle publishes the
  stability evidence and stops there
- No per-fold re-optimization, no robustness grid, no new candidate, no execution of the SMA-plateau
  check
- Cache-only reads (no fetcher/network); read-only
- Keep deterministic: no timestamps in the report or the experiment record

### Notes
- The embargo-fold sensitivity triad is now complete: `csmomentum_001` (rejected -> survives),
  `sectorrotation_001` (rejected -> survives) and the incumbent (passes -> survives, and its
  margin *grows* from +0.0473 to +0.4850 on the non-overlapping design).
- The remaining protocol weakness is in the **statistic**, not in the fold calendar: the published
  walk-forward mean is an unweighted average of 48 overlapping fold Sharpes of which two have
  fewer than ten trades, and it is the average of two disjoint 24-fold sub-designs whose means are
  1.3850 and 0.5096.
- Operational note for the next cycle (it cost three worker invocations): the worker image ships
  **without the repository's Python dependencies** -- `pandas`, `pyarrow`, `pyyaml`, `pytest`,
  `yfinance`, `scipy`, `arch`, `statsmodels` must be installed from `requirements.txt` before any
  tool or test can run (`python3 -m pip install -r requirements.txt`). The full suite takes about
  10 minutes, and the invocation watchdog terminates a worker whose child is silent for 600
  seconds, so run the long suite **in the background** and poll it instead of blocking on it.
  Running the suite also re-stamps `research/reports/sectorrotation_long_sample_feasibility_001.md`
  with the current commit hash (a pre-existing side effect of that report's generator, not of this
  cycle's tool); revert that one-line stamp so that
  `git diff --stat src/ config/ research/experiments/ research/reports/` stays empty and is not
  mistaken for a modified committed artifact.
