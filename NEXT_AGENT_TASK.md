# NEXT AGENT TASK — Cycle 872

## Context

Cycle 871 (`research/experiments/month_end_candidate_reaudit_001.md`,
`research/reports/month_end_candidate_reaudit_001.md`) re-measured the two remaining frozen
month-end candidates on the config-faithful schedule and closed the defect question:

* `csmomentum_001` — legacy (calendar) path reproduces the committed
  `data/processed/weights_csmomentum_001.parquet` **bit-identically** and the published numbers of
  `research/experiments/csmomentum_baseline_wf_001.md`; the config-faithful path is bit-identical
  to `src/backtest/rebalance.py:build_month_end_weights`. Deviation: test Sharpe 0.4101 → 0.4878,
  WF mean OOS Sharpe 0.6868 → 0.6975, 48 folds. **Verdict unchanged** (Rejected/Failed; gate 1
  needs WF mean OOS Sharpe ≥ 0.9 in both paths).
* `macroregime_001` — the published path is reproduced exactly from the committed
  `data/processed/weights_macroregime_001.parquet` (test Sharpe 0.2950, WF mean OOS Sharpe 0.4331,
  24 folds, 137 pooled trades). **But the config-faithful path with the published VIX gate is not
  computable from the committed cache**, because the committed `data/raw/^VIX.parquet` covers only
  2025-01-02 .. 2026-10-16 (451 rows) while the candidate's sample is 2004-11-18 .. 2026-10-09
  (5,507 sessions). 5,063 of those sessions have no VIX observation, so the VIX regime gate is
  inactive before 2025 in every cache-reproducible path.

Consequence: the `macroregime_001` deviation was measured on a **VIX-gate ablation**
(cache-reproducible legacy 0.4628 vs config-faithful 0.2838 WF mean OOS Sharpe, still a
"verdict unchanged" rejection), and the published-VIX-gate counterpart of the config-faithful path
remains **indeterminate**. This is the one open corner left by Cycle 871 and it is a *data
readiness* gap, which is priority 1 of the repository's strategic objective.

The environment has network access to the provider (`yf.download` was verified to return `^VIX`
bars from 2004), so the gap is closable without any new dependency or paid data source.

## Objective

**Backfill the committed `^VIX` raw cache to cover the `macroregime_001` sample, then re-run the
`macroregime_001` leg of the Cycle 871 re-audit on the real VIX gate and close the remaining
indeterminacy.**

Two bounded steps, in this order:

1. **Data readiness.** Extend `data/raw/^VIX.parquet` backwards from 2025-01-02 to at least
   2004-11-18 using the same provider and the same schema as
   `research/refresh_raw_cache.py` (Yahoo Finance via yfinance, `auto_adjust=False`, EOD `Close`,
   UTC index, same column set). The extension must be **append-only in time**: every row that
   exists today must survive unchanged in content, and the overlapping range (2025-01-02 ..
   2026-10-16) must be byte-for-byte consistent with the newly downloaded series — otherwise the
   cache is not trustworthy and the cycle must stop and report that instead.
2. **Measurement.** Re-run `research/month_end_candidate_reaudit.py` so that the
   `macroregime_001` legacy path is computed **from the cache** (no ablation) and must reproduce the
   published numbers of `research/experiments/macroregime_baseline_wf_001.md` and
   `research/experiments/macroregime_001_experiment_002.md`; and so that the config-faithful path
   is computed with the **real** VIX gate. Then state, with the numbers that decide it, whether the
   schedule defect moves `macroregime_001` across its own pre-registered gates
   (`config/macroregime_candidate_001.yaml`: WF mean OOS Sharpe ≥ 0.9, positive fold rate ≥ 0.5,
   pooled OOS trades > 100), and label the outcome `verdict unchanged` / `verdict changed` /
   `indeterminate`.

## Acceptance criteria

1. `data/raw/^VIX.parquet` covers at least 2004-11-18 .. 2026-10-09 with the same schema as today
   (columns `Open High Low Close Volume`, UTC `DatetimeIndex`, no duplicate dates, no NaN `Close`),
   and the rows that existed before the cycle are unchanged in content.
2. An integrity check is executed and its output recorded: the newly downloaded series over the
   overlapping range (2025-01-02 .. 2026-10-16) agrees with the previously cached rows to within
   1e-6 relative on `Close` (or the discrepancy is reported and explained).
3. `python research/month_end_candidate_reaudit.py` prints `OVERALL: PASS`, and its
   `macroregime_001` section no longer uses the VIX-gate ablation: the legacy path computed from
   the cache reproduces the published test-window metrics and walk-forward block of
   `research/experiments/macroregime_baseline_wf_001.md` within the published precision
   (test Sharpe 0.2950, max drawdown -0.1807, turnover 3.13x, 58 trades, WF mean OOS Sharpe 0.4331
   over 24 folds, 75.0% positive, 137 pooled trades).
4. The `macroregime_001` verdict on the config-faithful path is stated with the numbers that decide
   it (WF mean OOS Sharpe, positive fold rate, pooled trades vs the three gates).
5. `research/reports/month_end_candidate_reaudit_001.md` and
   `research/experiments/month_end_candidate_reaudit_001.md` are updated to the non-ablation
   numbers; the Cycle 871 numbers that the ablation produced are kept as a documented alternative
   in the report, not silently deleted.
6. `python -m pytest -q` passes (82 tests at the time of writing), `python
   research/rebalance_schedule_audit.py` still prints `OVERALL: PASS`, and `git status --porcelain
   config/` is empty.
7. The candidate configurations, the gate thresholds, the cost model, the Sharpe conventions and
   every committed artifact under `data/processed/` are **unchanged**; only `data/raw/^VIX.parquet`
   and the Cycle 871 deliverables may change.

## Validation commands

```bash
python -c "import pandas as pd; d=pd.read_parquet('data/raw/^VIX.parquet'); print(len(d), d.index.min(), d.index.max())"
python research/month_end_candidate_reaudit.py      # OVERALL: PASS
python research/rebalance_schedule_audit.py         # OVERALL: PASS
python research/sectorrotation_long_sample_feasibility.py
python -m pytest -q
git status --porcelain config/ data/processed/      # empty
```

## Scope boundaries

- **Do not** change any candidate configuration, universe, parameter, gate threshold, cost model or
  Sharpe convention; this is a data + measurement cycle.
- **Do not** re-optimise, re-tune or re-select anything; the re-audit measures, it does not search.
- **Do not** create a new provider, a paid feed, a dependency, a service, a scheduled job, an
  agent or a workflow. Only the existing `yfinance` path is allowed, and only for `^VIX`.
- **Do not** modify `data/processed/*` or any committed experiment record other than the Cycle 871
  deliverables; the committed artifacts are the reproduction reference and must stay untouched.
- **Do not** dispatch this workflow or start additional agent sessions.
- If the backfill cannot be made trustworthy (the overlap check fails, or the provider does not
  serve the 2004-2025 `^VIX` history), **stop and report**: keep the Cycle 871 evidence, state the
  blocker precisely, and make the next bounded task the resolution of that blocker. Do not publish
  an ablation result as if it were the published-VIX-gate result.
