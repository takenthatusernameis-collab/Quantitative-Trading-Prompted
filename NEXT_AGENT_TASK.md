# Next Agent Task: Cycle 871 — re-derive the two remaining frozen month-end candidates on the config-faithful path

## Context
- Cycle 869 measured the long-sample feasibility of the frozen `sectorrotation_001` candidate and
  **rejected** it on its own pre-registered falsification condition (walk-forward mean OOS Sharpe
  0.847243 < 0.9; long-sample canonical Sharpe 0.472367; repository gate table NO-GO).
  Evidence: `research/reports/sectorrotation_long_sample_feasibility_001.md`.
- Cycle 870 implemented **one** correct month-end rebalance schedule in shared code
  (`src/backtest/rebalance.py`), exposed it through the opt-in engine parameter
  `run_backtest(..., rebalance_schedule="month_end")`, and measured the remaining calendar-based
  defect in `src/simulation/engine.py` ("M" branch: no rebalance at all in 100 of the 335 months).
  Evidence: `research/reports/rebalance_schedule_001.md`,
  `research/experiments/rebalance_schedule_001.md`.
- **New finding that motivates this cycle:** the two *other* frozen candidates that specify the same
  month-end schedule were evaluated with a **calendar-based** `is_month_end` schedule of exactly the
  same defective kind:
  - `config/csmomentum_candidate_001.yaml` (`execution.rebalance_schedule: "monthly"`) was run by
    `research/run_cycle13.py:160-168` (`_apply_monthly_schedule`: `weights.where(is_month_end).ffill()`);
  - `config/macroregime_candidate_001.yaml` (`execution.rebalance_schedule: "monthly"`) was run by
    `research/run_cycle19.py:148-151` (the same calendar rule).
  Both therefore (a) rebalance one session earlier than the frozen configuration specifies
  (signal formed on the month's last session, effective from the next one) and (b) never rebalance in
  the ~30% of months whose last calendar day was a weekend or a market holiday, carrying the
  previous month's weights through the whole month. **Their published numbers have never been
  re-derived on a correct schedule.**

## Objective
Quantify, read-only, how much the defective calendar schedule changed the published results of
`csmomentum_001` and `macroregime_001`, using the now-executable config-faithful path, and label
whether each candidate's pre-registered verdict changes. **Measurement, not re-optimisation**: no
parameter, universe, cost model, gate threshold or configuration may change.

## Acceptance Criteria
1. A new read-only tool (e.g. `research/month_end_candidate_reaudit.py`) computes, for **each** of
   `csmomentum_001` and `macroregime_001`, on the same cached data, universe and 3 bps cost model:
   - the **legacy** path, reproducing the calendar `is_month_end` rule exactly as
     `research/run_cycle13.py` / `research/run_cycle19.py` implemented it;
   - the **config-faithful** path, via `src/backtest/rebalance.py`
     (`build_month_end_weights`) or `run_backtest(..., rebalance_schedule="month_end")`;
   and reports the deviation in canonical Sharpe, max drawdown, annualized turnover, trade days and
   the candidate's pre-registered walk-forward mean OOS Sharpe (36 folds, 10y/12m/6m, 21d purge,
   21d embargo) where the published record contains it.
2. The legacy path **reproduces the committed published numbers** of
   `research/experiments/csmomentum_001_experiment_001.md` and
   `research/experiments/macroregime_001_experiment_002.md` (state the tolerance and the exact
   numbers; if a published number cannot be reproduced from the committed cache, say so explicitly
   and quantify the difference instead of hiding it).
3. Each candidate gets an explicit **verdict label** (`verdict unchanged` / `verdict changed` /
   `indeterminate`), stating whether the schedule defect moves the candidate across its own
   pre-registered gates (`config/csmomentum_candidate_001.yaml`,
   `config/macroregime_candidate_001.yaml`), with the numbers that decide it.
4. `research/reports/month_end_candidate_reaudit_001.md` and
   `research/experiments/month_end_candidate_reaudit_001.md` document the method, the deviation
   table, the verdicts, the falsification conditions and the reproduction commands.
5. `python -m pytest -q` passes, `git status --porcelain data/` is empty, `config/` is unchanged, the
   committed experiment records and `data/processed/*.parquet` are unchanged, and the incumbent's
   code-level decision stays **NO-GO**.

## Validation
```
python -m pytest -q
python research/month_end_candidate_reaudit.py       # new tool; must print OVERALL: PASS
python research/rebalance_schedule_audit.py           # Cycle 870 tool must still print OVERALL: PASS
python research/sectorrotation_long_sample_feasibility.py
python research/promotion_feasibility_backtest.py     # incumbent artifacts unchanged (NO-GO)
git status --porcelain data/                          # empty
```

## Scope boundaries
- **No re-run and no rewrite** of `research/run_cycle13.py`, `research/run_cycle19.py` or
  `src/simulation/engine.py`: this cycle *measures*; adopting the shared schedule in those code
  paths is a separate, explicitly scoped change (and would move committed artifacts).
- No change to any candidate configuration, gate threshold, cost model, universe or Sharpe
  convention; no write to `data/` (the new tool must not create `data/processed/*.parquet`).
- Do not re-open the `sectorrotation_001` verdict (rejected on its pre-registered condition in
  Cycle 869); do not re-open the incumbent's NO-GO decision.
- Known limitation to state in the report: the 9 sector ETFs (and DBC, VNQ) are not covered by
  `research/refresh_raw_cache.py` and end 2026-10-08, six sessions behind the core cache
  (2026-10-16); the `csmomentum_001` universe therefore has an 18-asset common calendar that starts
  at the youngest asset's inception.
