# Experiment 001 - Cost-Admissibility Screen (`cost_admissibility_screen_001`)

## Hypothesis reference

Not a new hypothesis and not a new candidate. This experiment is the **measurement
infrastructure** that Cycle 880's rejection exposed as missing: the candidate shortlist
(`research/reports/opportunity_shortlist.md`) scores candidates on a structural "(c) net
return" basis and states no candidate's **annualized cost drag**, and Cycle 880 had to
reject the overnight-session candidate `overnight_capture_001` *on cost* after a full
back-test. The hypothesis this experiment tests is a **methodological** one:

> **H-COST-ADMISSIBILITY.** A candidate's cost admissibility — whether its gross signal is
> large enough to survive the turnover it actually incurs at the repository's own cost model
> — is (i) computable from the committed cache and the committed artifacts alone,
> (ii) reproducible, and (iii) checkable against any cost-drag figure the repository states.

Falsification condition: if the screen cannot reproduce a published cost figure or a published
walk-forward statistic from the committed artifacts, or if a stated cost-drag figure can
pass the guard while being inconsistent with the turnover the strategy incurs, the screen is
useless and the experiment is a failure.

The underlying candidate hypotheses are unchanged and are **not** re-decided here:
`research/hypotheses/overnight_capture_001.md`, `research/hypotheses/calendar_effects_001.md`.

## Data used

| Item | Value |
|---|---|
| Source | committed Yahoo Finance parquet cache in `data/raw/` (read directly, never fetched) |
| Symbols | SPY, QQQ, IWM (overnight + calendar candidates); SPY, QQQ, IWM, TLT, GLD, EFA, EEM (incumbent benchmark) |
| Frequency | daily, timezone-aware UTC index |
| `overnight_capture_001` | 2000-05-26 -> 2026-10-16, 6,637 sessions (common calendar of SPY/QQQ/IWM) |
| `calendar_effects_001` | 2000-05-26 -> 2026-10-09, 6,632 sessions (declared `history_start` onward) |
| `tsmomentum_spytrend_001` | 1993-01-29 -> 2026-10-09, 8,482 sessions (committed artifact span) |
| Committed artifacts read | `data/processed/weights_calendar_effects_001.parquet`, `data/processed/simulation_calendar_effects_001.parquet`, `data/processed/simulation_candidate_001.parquet`, `data/processed/weights_full_history.parquet` |
| Configuration read | `config/overnight_capture_001.yaml`, `config/calendar_effects_001.yaml`, `config/simulation_candidate_001.yaml` |

**Data-vintage disclosure.** The committed *processed* artifacts stop at 2026-10-09 while the
committed *raw* cache now runs to 2026-10-16. The screen therefore **clips** the price frame
to each candidate's committed artifact end date before rebuilding anything. Without that clip
the rebuilt turn-of-month weights no longer match the committed artifact (max abs weight
difference 0.3333) and the walk-forward would change silently. The clip is verified: the
rebuilt calendar weights, gross returns and turnover match the committed artifacts with max
abs difference **0.000e+00** over 8,482 sessions.

## Point-in-time treatment

Unchanged and inherited from the artifacts being reused: the turnover and gross-return series
are the committed ones; the screen introduces no new information about the future and no
parameter that is selected on data. The calendar mask is the committed exogenous
turn-of-month mask (last 1 trading day of the month + first 3 trading days of the next month,
no shift), the incumbent is the committed full-history simulation, and the overnight leg is the
committed overnight/open-to-close construction with a 1-session lag on the previous close.

The screen's own statistics are computed on **fixed, pre-registered windows** (the candidate's
own committed window) and on the candidate's **own committed walk-forward folds**. No
window, no fold and no parameter is chosen by looking at an outcome.

## Configuration

| Item | Value |
|---|---|
| Cost model | `get_cost_params()`: 1 bp commission + 2 bp slippage = **3.0 bp per unit of weight change** |
| Cost rows | 3 / 5 / 10 bp per unit; decision row 3 bp/unit |
| Annualization | 252 sessions/yr; gross signal geometric `(1+r).prod()**(252/n)-1`; cost drag arithmetic `mean(turnover)*252*bps/10000` |
| Sharpe scales | walk-forward fold statistic on the backtest-baseline scale (`compute_metrics`), as the published records use; full-window statistic on the canonical scale (`sharpe_ratio`) |
| Walk-forward geometry | 10y train / 12m test / 6m step, 21d purge, 21d embargo (each candidate's frozen configuration) |
| Benchmark | close-to-close equal-weight buy-and-hold of the candidate's own universe, one unit of turnover in the first session of the screen window, none afterwards |
| Guard tolerance | 1e-9 on `cost_drag == annual_turnover * cost_bps / 10000` |
| Break-even solver | bisection on a monotone-decreasing objective over [-100, 1000] bp/unit, tolerance 1e-9 |
| Hardware / network | CPU only, no network (a missing cache file is a hard error, never a fetch) |

## Splits

| Candidate | Folds | First test window | Last test window | Pooled OOS sessions (summed over overlapping folds) |
|---|---|---|---|---|
| `overnight_capture_001` | 33 | 2010-02-22 | 2026-07-23 | 8,016 |
| `calendar_effects_001` | 33 | 2010-02-22 | 2026-07-23 | 8,016 |
| `tsmomentum_spytrend_001` | 48 | 2002-10-28 | 2026-06-25 | 11,664 |

The fold test windows **overlap** (12-month test, 6-month step), so the pooled session count
exceeds the number of distinct sessions in the window. This is the repository's existing
walk-forward convention, unchanged by this cycle.

## Results (3 bp/unit decision configuration)

| Quantity | `overnight_capture_001` | `calendar_effects_001` | `tsmomentum_spytrend_001` |
|---|---|---|---|
| Annualized turnover (units/yr) | 504.0000 | 24.1285 | 12.1645 |
| Annualized gross signal (geometric) | +9.1558%/yr | +2.7326%/yr | +13.8825%/yr |
| Annualized cost drag @3 bp | +15.1200%/yr | +0.7239%/yr | +0.3649%/yr |
| Annualized cost drag @5 bp | +25.2000%/yr | +1.2064%/yr | +0.6082%/yr |
| Annualized cost drag @10 bp | +50.4000%/yr | +2.4128%/yr | +1.2165%/yr |
| Net annualized return @3 bp | -6.1612%/yr | +1.9913%/yr | +13.4685%/yr |
| Net canonical Sharpe @3 bp | -0.459013 | +0.257291 | +1.496044 |
| Net WF mean OOS Sharpe @3 bp | -0.599718 | -0.025432 | +0.928608 |
| Net WF mean OOS Sharpe @5 bp | -1.546936 | -0.091457 | +0.979485 |
| Net WF mean OOS Sharpe @10 bp | -3.537547 | -0.254506 | +1.001733 |
| Minimum gross signal needed @3 bp | +15.1200%/yr | +0.7239%/yr | +0.3649%/yr |
| Gross signal surplus | -5.9642%/yr | +2.0087%/yr | +13.5175%/yr |
| **Break-even cost (net annualized return = 0)** | **1.738464 bp/unit** | **11.163921 bp/unit** | **106.754027 bp/unit** |
| **Cost at which the net WF Sharpe equals the same-fold benchmark's** | **0.291155 bp/unit** | **-22.685161 bp/unit (a rebate)** | **32.305171 bp/unit** |
| Cost at which the net full-window canonical Sharpe equals the benchmark's | 0.780612 bp/unit | -4.988492 bp/unit (a rebate) | 72.144596 bp/unit |
| Benchmark WF mean OOS Sharpe (same folds) | +0.844696 | +0.844696 | +0.705721 |
| Positive fold rate | 15.1515% | 42.4242% | 95.8333% |
| Pooled OOS trades | 8,016 | 761 | 6,071 |
| **Admissibility verdict** | **INADMISSIBLE** | **ADMISSIBLE** | **ADMISSIBLE** |

### Reproduction of the committed records (self-checks, 22/22 PASS)

| Candidate | Quantity | Published | Re-derived | Diff | Tolerance |
|---|---|---|---|---|---|
| `overnight_capture_001` | Annualized cost drag @3 bp | 0.1512 | 0.151200 | 2.776e-17 | 1e-9 |
| `overnight_capture_001` | Net WF mean OOS Sharpe | -0.599718 | -0.599718 | 1.082e-07 | 1e-6 |
| `overnight_capture_001` | Benchmark WF mean OOS Sharpe | +0.844696 | +0.844696 | 3.486e-07 | 1e-6 |
| `overnight_capture_001` | Positive fold rate | 0.151515 | 0.151515 | 1.515e-07 | 1e-6 |
| `overnight_capture_001` | Pooled OOS trades | 8,016 | 8,016 | 0 | exact |
| `calendar_effects_001` | Net WF mean OOS Sharpe | -0.0254 | -0.025432 | 3.226e-05 | 1e-4 |
| `calendar_effects_001` | Positive fold rate | 0.424242 | 0.424242 | 4.242e-07 | 1e-4 |
| `calendar_effects_001` | Pooled OOS trades | 761 | 761 | 0 | exact |
| `tsmomentum_spytrend_001` | Net WF mean OOS Sharpe (48 folds) | 0.9473 | 0.928608 | 1.869e-02 | 0.02 (`research/run_cycle7.py:TOL_SHARPE`) |
| `tsmomentum_spytrend_001` | Test-period Sharpe (2018-2026) | 1.4178 | 1.407770 | 1.003e-02 | 0.02 (same) |

The two incumbent differences are **disclosed, not failures**: the published baseline is a
configuration *re-run* with `overlay_warmup: "slice"` (overlay state initialised at the
evaluation window start, `research/reports/simulation_verification_001.md`), while the
committed artifact is the *full-history* run that carries the overlay state from 1993. The
difference is inside the repository's own declared tolerance and the screen checks exactly
that tolerance rather than a tighter invented one.

### The mechanical guard

| Case | Stated drag | Annual turnover | Cost | Expected | Abs diff | Result |
|---|---|---|---|---|---|---|
| Published overnight drag | 0.1512 | 504.0 | 3 bp | 0.151200 | 2.776e-17 | CONSISTENT |
| **Cycle 880 erratum (negative control)** | 0.0151 | 504.0 | 3 bp | 0.151200 | 1.361e-01 | **REJECTED** |
| Cycle 880 erratum at 5 bp | 0.0252 | 504.0 | 5 bp | 0.252000 | 2.268e-01 | **REJECTED** |
| Cycle 880 erratum at 10 bp | 0.0504 | 504.0 | 10 bp | 0.504000 | 4.536e-01 | **REJECTED** |
| Screen's own three candidates @3 bp | see above | 504.0 / 24.1285 / 12.1645 | 3 bp | - | 0.0 | CONSISTENT |

The guard is `cost_drag == annual_turnover * cost_bps_per_unit / 10000` within 1e-9, and it is
applied to every figure the screen states, to the figures published in the committed records
and to the Cycle 880 erratum as a negative control. `require_cost_drag_consistency` raises
`ValueError`, so a screen that states an inconsistent drag cannot complete.

## Number of trials

**One.** The screen evaluates three candidates at three cost rows. It performs **no
parameter search, no configuration selection, no optimization and no re-optimization**; the
only root-finders are the two deterministic bisections, and both are reported with their
bracket. The number of *configurations examined* is 1 for every candidate, so no
multiple-testing correction is required for the screen itself. The re-derived walk-forward
statistics are a **validation** of the screen, not a selection over configurations.

## Reproduction commands

```bash
python research/cost_admissibility_screen.py     # -> OVERALL: PASS, exit 0, prints every number
python -m pytest tests/test_cost_admissibility_screen.py -q   # 22 passed
python -m pytest -q                               # 124 passed (102 pre-existing + 22 new)
python research/go_no_go_evaluation.py            # NO-GO, side_effect_free: True
git status --porcelain data/ config/              # empty (nothing written under data/ or config/)
```

Read-only proof: the tool takes a SHA-256 fingerprint of all 1,844 files under `data/` and
`config/` before and after the run and requires them to be identical.

## Decision label

**Measurement, not a candidate decision.** The screen is a **cost filter** that is necessary
and not sufficient for a candidate to be worth a walk-forward evaluation. It changes no
candidate's label:

| Candidate | Label before | Label after |
|---|---|---|
| `overnight_capture_001` | Rejected/failed (Cycle 880, on cost) | Rejected/failed (unchanged; the rejection is reproduced from the committed artifacts and its arithmetic is now mechanically checkable) |
| `calendar_effects_001` | Rejected/failed (Cycle 18, on the walk-forward gate) | Rejected/failed (unchanged; the cost screen clears it, which is **not** evidence of an edge) |
| `tsmomentum_spytrend_001` | Credible candidate (incumbent) | Credible candidate (unchanged; NO-GO on the live paper record is unchanged) |

**Incumbent decision unchanged: NO-GO** (failed gates `rolling_63d_sharpe`, `psr`), live
deployment unsupported.
