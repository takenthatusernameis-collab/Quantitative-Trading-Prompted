# Next Agent Task: Cycle 18 — Execute the C6 Calendar/Rebalancing Effects Evaluation (calendar_effects_001)

## Context

Cycle 17 completed the primary correction: the pre-registered
C4 (sectorrotation_001) evaluation was executed correctly for
the first time via `research/run_cycle15_c4_corrected.py`
(9 sector ETFs, 1998-12-22 start, 36 folds, 18-config grid)
and was **Rejected/Failed** (WF mean OOS Sharpe 0.6944 < 0.9;
DSR -0.2742 at N=18). The cross-sectional momentum family
(C3 broad universe + C4 sector universe) is now rejected on
two valid pre-registered tests and archived. Evidence:
`research/reports/cross_momentum_consolidation.md` (section 6)
and `research/experiments/sectorrotation_baseline_wf_001.md`.

The C6 (calendar/rebalancing effects) pre-registration is
frozen and validated (Cycle 17 Part 2):
`research/hypotheses/calendar_effects_001.md` and
`config/calendar_effects_001.yaml` parse; the grid arithmetic
(3 pre_days × 6 post_days = 18) holds; `generate_walkforward_splits("2000-05-26", "2026-10-09", 10, 12, 6, 21, 21)`
yields exactly 33 folds with the pre-registered fold 1 /
fold 33 dates. **No C6 backtest has been executed.** This
cycle executes it.

## Objective

Execute the pre-registered C6 evaluation — turn-of-month (TOM)
window exposure on SPY/QQQ/IWM — via a new
`research/run_cycle18.py`, mirroring the C3/C4 evaluation
discipline: baseline backtest, 33-fold walk-forward, 18-config
grid, always-invested 1/N + incumbent benchmarks, DSR at N=18,
plateau check on the `pre_days` axis at `post_days=3`, and an
honest promotion-gate verdict (report whatever it is — do not
tune anything to change it).

## Required Actions

1. Create `research/run_cycle18.py` implementing the frozen
   C6 design (nothing may be added post-hoc):
   - `UNIVERSE = ["SPY", "QQQ", "IWM"]`
   - `START_DATE = "2000-05-26"` (IWM inception bounds the
     common calendar; 6,632 trading days through 2026-10-09).
     Repo-convention `END_DATE = "2026-10-09"` stays.
     `TRAIN_END = "2009-12-31"`, `VAL_END = "2017-12-31"`,
     `TEST_START = "2018-01-01"`.
   - Baseline: `PRE_DAYS = 1`, `POST_DAYS = 3` (the classic
     TOM window). Grid: `PRE_DAYS_GRID = [1, 2, 3]`,
     `POST_DAYS_GRID = [1, 2, 3, 5, 7, 10]`; assert
     `len(PRE_DAYS_GRID) * len(POST_DAYS_GRID) == 18` and
     that the baseline (1, 3) is a grid member.
   - **Calendar mask (critical, pre-registered)**: month
     boundaries MUST be computed on TRADING days (the last
     `pre_days` trading days of each month and the first
     `post_days` trading days of the following month), NOT on
     calendar `is_month_end` / `is_month_start` flags (which
     are False whenever a month's boundary day is a non-trading
     day).
   - **No 1-day shift on the mask** (pre-registered): the
     calendar is exogenous public information known indefinitely
     in advance, so there is no price-signal lookahead channel;
     positions are established at the prior trading day's close
     (`port_ret[t] = weights[t] * ret[t]`). Document this
     deliberate difference from the momentum `build_weights`
     shift(1) convention in the record.
   - Exposure: equal-weight 1/3 per asset when the mask is
     True, cash (0 exposure) otherwise. Long-only, gross
     exposure ∈ {0.0, 1.0}. Trades occur only at window
     boundaries (~24.1 trade days/yr at baseline).
   - Costs: 3 bps per unit of weight change (1 bps commission
     + 2 bps slippage, `get_cost_params()`); cash return 0%;
     risk-free rate 2% flat (`get_risk_free_rate()`).
   - Strategy history starts at the common-calendar start
     2000-05-26 (pre-inception cells are NaN, not back-filled;
     the strategy holds no positions before 2000-05-26).
   - Walk-forward: `generate_walkforward_splits("2000-05-26",
     "2026-10-09", 10, 12, 6, 21, 21)` — assert
     `len(splits) == 33` and the pre-registered fold dates
     (fold 1: train 2000-05-26→2010-01-21, test
     2010-02-22→2011-02-08; fold 33: train 2015-11-10→
     2025-07-07, test 2025-08-06→2026-07-23). Fixed
     parameters across folds (no per-fold re-optimization).
   - Benchmarks (identical periods and folds, identical 3 bps
     cost model):
     (a) **Always-invested 1/N equal-weight basket**: constant
     1/3 target weights in SPY/QQQ/IWM with a 1-day lag
     (`shift(1)`) and the monthly month-end schedule (the
     C3/C4 1/N convention — zero observed turnover / zero cost
     drag within the engine's exogenous-weights framework; note
     the mild upward bias as a limitation).
     (b) **Incumbent TSMOM (tsmomentum_spytrend_001)** on its
     core-7 universe (fetch CORE7 separately via
     `fetch_close_prices`, cache-only), with its validated
     overlay-warmup conventions: "slice" for the test period,
     "full" for the walk-forward folds. It is a CONTEXT
     benchmark (its validated WF statistics are on the 1993-start
     48-fold design; not directly comparable to the 33-fold
     design) — report it, not a gate.
   - Multiple-testing control: DSR via `compute_dsr` at the
     true trial count N=18 (1000 block-bootstrap samples,
     22-day block, seed=42), PSR vs SR=0 and vs the 0.9 gate,
     block-bootstrap Sharpe 95% CI, PBO/CSCV via `compute_pbo`
     over the 18-config grid (train=2000-2009 vs test=2018-2026).
   - Plateau check (pre-registered gate 4): >= 2 of the 3
     `pre_days` values (1, 2, 3) achieve test Sharpe within 10%
     of the baseline (1, 3) test Sharpe, evaluated at
     `post_days=3` (threshold = max(0.1, 10% × |baseline test
     Sharpe|), the repository plateau convention).
   - Promotion gates: WF mean OOS Sharpe >= 0.9; positive-fold
     rate >= 50%; pooled OOS trades > 100 (expected ~790 at
     baseline); plateau >= 2 of 3. Pre-registered falsification:
     WF mean OOS Sharpe < 0.9 OR < 50% positive folds →
     Rejected/Failed.
   - Reuse the existing machinery (`src/features/momentum.py`,
     `src/backtest/engine.py:compute_metrics`,
     `src/evaluation/statistics.py`,
     `src/evaluation/walkforward.py`,
     `src/evaluation/utils.py:fetch_close_prices`); do NOT add
     dependencies, data fetching (`force=False`, cache-only),
     overlays, or gate weakening.
2. Execute: `python3 research/run_cycle18.py`
3. Artifacts: `data/processed/{simulation,trades,weights}_calendar_effects_001.parquet`
   and the experiment record
   `research/experiments/calendar_effects_baseline_wf_001.md`
   with full provenance (data-integrity table per symbol:
   SPY 8,482 rows 1993-01-29→2026-10-09; QQQ 6,940 rows
   1999-03-10→2026-10-09; IWM 6,632 rows 2000-05-26→2026-10-09;
   common calendar 6,632 days; aligned-frame content hash;
   config SHA-256[:12] equal to
   `sha256sum config/calendar_effects_001.yaml`; code revision;
   all 18 grid configs with train/val/test metrics; 33-fold
   table; benchmark comparison; multiple-testing results;
   promotion-gate verdict; honest final classification per the
   pre-committed decision discipline).
4. Verify (all must hold):
   - `weights_calendar_effects_001.parquet` covers the strategy
     history (2000-05-26 → 2026-10-09, 6,632 rows) with
     exactly 3 columns (SPY, QQQ, IWM); weights are either
     1/3-per-asset (in-window) or 0 (cash); trades occur only
     at window boundaries.
   - The record's fold table has 33 rows with train starts
     2000-05-26 and fold dates matching the frozen hypothesis.
   - The promotion-gate verdict is computed from the actual
     corrected results; the "Decision & Next Steps" section
     carries the honest label (Rejected/Failed, Exploratory
     signal, or Credible candidate).
5. Update `research/reports/cross_momentum_consolidation.md`
   only if the C6 outcome changes the family conclusion (it
   does not — C6 is a distinct mechanism; a one-line pointer
   suffices), and update `README.md`'s Current Status.

## Acceptance Criteria

- `research/run_cycle18.py` exists, runs to completion, and
  produces the C6 artifacts and record with correct provenance.
- C6 record: 33 folds, 3-ETF universe, correct config hash,
  18-config grid, honest promotion-gate verdict.
- Pre-execution assertions present and enforced: 18-config
  grid arithmetic, 33-fold count with fold 1/fold 33 dates.
- No modification to frozen pre-registrations
  (`research/hypotheses/calendar_effects_001.md`,
  `config/calendar_effects_001.yaml`) or to any C3/C4
  artifact, hypothesis, config, or evaluation script
  (`research/run_cycle13.py`, `research/run_cycle15.py`,
  `research/run_cycle15_c4_corrected.py`,
  `research/hypotheses/sectorrotation_001.md`,
  `config/sectorrotation_candidate_001.yaml`,
  `config/csmomentum_candidate_001.yaml`,
  `research/experiments/csmomentum_baseline_wf_001.md`,
  `research/experiments/sectorrotation_baseline_wf_001.md`).
- `NEXT_AGENT_TASK.md` written for Cycle 19 (per the
  pre-registered decision tree: if C6 is rejected, the next
  untested Cycle 11 shortlist candidate is C5 macro regime
  overlay extension, 24/35 — noting its overlay-only
  constraint; if C6 passes, risk-overlay exploration on the
  C6 baseline).

## Scope Boundaries

- Do NOT modify the frozen C6 pre-registration
  (`research/hypotheses/calendar_effects_001.md`,
  `config/calendar_effects_001.yaml`).
- Do NOT modify any C3/C4 artifact or the corrected C4 script
  (Cycle 17's work is complete and verified).
- Do NOT add data fetching (cache-only), new dependencies,
  overlays, post-hoc calendar variants (quarter-end /
  index-reconstitution refinements are explicitly reserved for
  post-gate cycles), or gate weakening. Research/backtesting
  only. No live trading, no credentials, no scheduled jobs.
- Do NOT select configurations on test-period results: the
  baseline is pre-specified; the grid is diagnostic
  (plateau + multiple-testing control) only.

## Evidence References

- `research/hypotheses/calendar_effects_001.md` (frozen C6
  design: mechanism, trading-day month boundaries, no-shift
  mask convention, 18-config grid, 33-fold dates, promotion
  gates, falsification condition)
- `config/calendar_effects_001.yaml` (frozen C6 config)
- `research/reports/cross_momentum_consolidation.md` (Cycle 17
  corrected C4 outcome; family archived)
- `research/experiments/sectorrotation_baseline_wf_001.md`
  (Cycle 17 corrected C4 record — the evaluation-record
  template to mirror)
- `research/run_cycle15_c4_corrected.py` (the corrected C4
  execution script — the structural template for
  `run_cycle18.py`)
- `research/experiments/tsmomentum_regime_filter_wf_001.md`
  (Cycle 6 walk-forward design; incumbent benchmark
  conventions)
- `research/reports/opportunity_shortlist.md` (C6 = 26/35,
  rank 4 of 10; C5 = 24/35)

## Environment Note

The Python environment used for Cycle 17 execution had these
packages installed into the user site-packages (system
`python3`, Python 3.12.3):
`pip install "numpy==1.26.4" "pandas==2.2.3" "scipy==1.13.1" "statsmodels==0.14.2" "arch==7.2.0" "pyarrow==16.1.0" pyyaml yfinance pytest`.
If modules are missing at session start, install exactly these
versions before running (the repo's code targets the pandas
2.x / numpy 1.x API era). All data is cached in `data/raw/`
(cache-only execution; no network fetch occurs with
`force=False`).
