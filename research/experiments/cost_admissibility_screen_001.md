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

---

# Cycle 882 extension - the shortlist's cost column completed, and the gate headroom

**Added 2026-10-19.** The tool was **extended, not duplicated**: `research/cost_admissibility_screen.py`
gained three candidate builders, one further decision number and the verification of three
committed records. **No number that Cycle 881 published has changed** (verified by a line-level
diff of the three Cycle 881 candidate blocks against the committed report: the only changed
lines are the cost-sensitivity table header and rows, which gained one appended column and
kept every previous value; everything else in those blocks is an addition).

## What was added, and why

| Addition | Reason |
|---|---|
| `csmomentum_001` (shortlist rank 2) | Cycle 881 left rank 2 without a cost basis; the shortlist's cost column must be completed for every row. |
| `sectorrotation_001` (shortlist rank 3) | Same. |
| `macroregime_001` (shortlist rank 6) | Same. |
| **Gate headroom**: the cost per unit at which the candidate's net walk-forward mean OOS Sharpe falls to the repository's own 0.9 promotion threshold | The screen stated a break-even cost but not the cost at which the candidate stops passing the **promotion gate**; the two are different questions and only the second one says whether a cost can be paid for. |
| Publication of the gate headroom for **every** candidate the screen covers | A decision number that exists for one candidate and not for another is not a decision number. |
| The shortlist's cost column completed for all ten rows, with the four non-derivable rows listed and their reasons stated | The Cycle 881 task required "a cost basis for every row". |

## The three new candidates: construction and provenance

All three are the **config-faithful month-end path** of the repository's already-validated
construction (`src/backtest/rebalance.py:build_month_end_weights`, Cycle 870), reached through the
existing research tools, never re-implemented:

| Candidate | Built by | Schedule | Universe | Screen window (invested sample) | Folds |
|---|---|---|---|---|---|
| `csmomentum_001` | `research/month_end_candidate_reaudit.py:build_csmomentum` -> `faithful_schedule` | `src/backtest/rebalance.py:build_month_end_weights` | 18 ETFs | 1994-03-01 -> 2026-10-09 (8,208 sessions) | 48 |
| `sectorrotation_001` | `research/sectorrotation_long_sample_feasibility.py:build_monthly_weights` | same | 9 GICS sector ETFs | 2000-02-01 -> 2026-10-08 (6,712 sessions) | 36 |
| `macroregime_001` | `research/month_end_candidate_reaudit.py:build_macroregime` -> `faithful_schedule` | same | 7 ETFs (+ ^VIX as an **input only**) | 2005-12-01 -> 2026-10-09 (5,246 sessions) | 24 |

The **defective calendar rule** and the **daily re-rank** path are not used anywhere. No
parameter, universe, cost model, gate, threshold or window is changed by this cycle, and no
candidate is re-optimized.

**Screen window = the invested sample.** A candidate that cannot be invested before its signal
warm-up is flat before it, and a flat period carries neither signal nor turnover, so the screen
measures it from the first session with a non-zero position to the end of the committed cache.
This is the sample the committed records already use ("invested sample" in
`research/reports/sectorrotation_long_sample_feasibility_001.md`). The walk-forward folds remain
the candidate's own pre-registered splits, generated from the candidate's own sample start, so
the fold count and the fold windows are unchanged.

**Benchmark.** The same close-to-close 1/N buy-and-hold convention, with the screen's documented
cash rule applied explicitly for the staggered-inception universes: without it a symbol without a
price yet contributes a NaN to the whole benchmark return and silently removes every fold that
overlaps the gap. The three Cycle 881 candidates keep their original benchmark, so their
published numbers do not move.

**Trade-count conventions differ between the two records and both are kept.** The Cycle 871
record counts a fold's trades from the sliced weight frame (the first session of a fold
contributes no trade); the Cycle 869 record counts them from the turnover series (the first
session of a fold does). The screen keeps each candidate's own convention so that its pooled
out-of-sample trade count is directly comparable with the number it is checked against. The
convention affects only the trade-count and per-fold turnover columns, never a Sharpe.

## Results of the three new candidates (3 bp/unit decision row)

| Quantity | `csmomentum_001` | `sectorrotation_001` | `macroregime_001` |
|---|---|---|---|
| Annualized turnover (units/yr) | 2.2270 | 2.9961 | 3.7011 |
| Annualized gross signal (geometric) | +9.4355%/yr | +7.2161%/yr | +6.9222%/yr |
| Annualized cost drag @3 bp | +0.0668%/yr | +0.0899%/yr | +0.1110%/yr |
| Net annualized return @3 bp | +9.3625%/yr | +7.1200%/yr | +6.8039%/yr |
| Net canonical Sharpe @3 bp | +0.615144 | +0.472367 | +0.721249 |
| Net WF mean OOS Sharpe @3 bp (backtest scale) | +0.697524 | +0.709767 | +0.263566 |
| Net WF mean OOS Sharpe @3 bp (canonical scale) | +0.840389 | +0.847243 | +0.460847 |
| WF mean OOS Sharpe at **zero** cost (canonical) | +0.845822 | +0.852863 | +0.473297 |
| **Break-even cost (net annualized return = 0)** | **402.320946 bp/unit** | **231.710245 bp/unit** | **180.265254 bp/unit** |
| **Cost at which the net WF Sharpe equals the same-fold benchmark's** | **-5.334684 bp/unit (a rebate)** | **-31.158677 bp/unit (a rebate)** | **-86.152115 bp/unit (a rebate)** |
| **Gate headroom (net WF mean OOS Sharpe = 0.90, canonical scale)** | **-30.096717 bp/unit (negative)** | **-25.313702 bp/unit (negative)** | **none (no cost level in [-100, 1000] bp/unit reaches the gate)** |
| Positive fold rate / pooled OOS trades | 79.1667% / 400 | 83.3333% / 213 | 66.6667% / 193 |
| **Admissibility verdict** | **ADMISSIBLE** | **ADMISSIBLE** | **ADMISSIBLE** |

The `sectorrotation_001` positive-fold rate above is the **backtest-scale** rate (the screen's
column); the Cycle 869 record quotes the **canonical** rate, 91.6667% (33/36), and the screen
verifies the record's own scale (section "Reproduction" below).

## Reproduction of the three committed records (all PASS)

**Tolerance rule:** the committed records quote their numbers as decimal strings, so the
tolerance of every comparison is the unit of that string's last decimal - the repository's own
rule (`research/month_end_candidate_reaudit.py:compare_published`). A 4-decimal number is
compared with 1e-4, a 2-decimal one with 1e-2, a 6-decimal one with 1e-6, and a **count** with
**0** (exact), because a count is an integer and no rounding is implied.

| Candidate | Quantity | Published | Re-derived | Tolerance | Result |
|---|---|---|---|---|---|
| `csmomentum_001` | Test-window Sharpe (backtest scale) | 0.4878 | 0.487833 | 1e-4 | PASS |
| `csmomentum_001` | Test-window Sharpe (canonical) | 0.6635 | 0.663540 | 1e-4 | PASS |
| `csmomentum_001` | Test-window max drawdown | -0.2940 | -0.294002 | 1e-4 | PASS |
| `csmomentum_001` | Test-window annualized turnover | 2.47 | 2.468571 | 1e-2 | PASS |
| `csmomentum_001` | Test-window trade days | 77 | 77 | exact | PASS |
| `csmomentum_001` | Walk-forward mean OOS Sharpe (backtest scale) | 0.6975 | 0.697524 | 1e-4 | PASS |
| `csmomentum_001` | Walk-forward positive fold rate | 0.792 | 0.791667 | 1e-3 | PASS |
| `csmomentum_001` | Walk-forward pooled OOS trades | 400 | 400 | exact | PASS |
| `csmomentum_001` | Walk-forward fold count | 48 | 48 | exact | PASS |
| `sectorrotation_001` | Canonical Sharpe (invested sample) | 0.472367 | 0.472367 | 1e-6 | PASS |
| `sectorrotation_001` | Annualized turnover (invested sample) | 2.9961 | 2.996067 | 1e-4 | PASS |
| `sectorrotation_001` | Trade days (invested sample) | 175 | 175 | exact | PASS |
| `sectorrotation_001` | Walk-forward mean OOS Sharpe (canonical) | 0.847243 | 0.847243 | 1e-6 | PASS |
| `sectorrotation_001` | Walk-forward positive fold rate | 0.9167 | 0.916667 | 1e-4 | PASS |
| `sectorrotation_001` | Walk-forward pooled OOS trades | 215 | 215 | exact | PASS |
| `sectorrotation_001` | Walk-forward fold count | 36 | 36 | exact | PASS |
| `macroregime_001` | Test-window Sharpe (backtest scale) | 0.1428 | 0.142777 | 1e-4 | PASS |
| `macroregime_001` | Test-window Sharpe (canonical) | 0.3823 | 0.382343 | 1e-4 | PASS |
| `macroregime_001` | Test-window max drawdown | -0.2240 | -0.223998 | 1e-4 | PASS |
| `macroregime_001` | Test-window annualized turnover | 4.22 | 4.217824 | 1e-2 | PASS |
| `macroregime_001` | Test-window trade days | 84 | 84 | exact | PASS |
| `macroregime_001` | Walk-forward mean OOS Sharpe (backtest scale) | 0.2636 | 0.263566 | 1e-4 | PASS |
| `macroregime_001` | Walk-forward positive fold rate | 0.667 | 0.666667 | 1e-3 | PASS |
| `macroregime_001` | Walk-forward pooled OOS trades | 193 | 193 | exact | PASS |
| `macroregime_001` | Walk-forward fold count | 24 | 24 | exact | PASS |

**One disclosed inconsistency inside a committed record.** The table of
`research/experiments/month_end_candidate_reaudit_001.md` states `macroregime_001`'s test-window
trade days as **84** and its prose states **83**. The screen compares against the table's 84 (and
derives 84), so the discrepancy inside the record is visible rather than silently resolved. The
screen does not re-decide which one is "right"; the record is the authority and the difference
is one session.

## Number of trials

**One per candidate, unchanged.** The screen evaluates six candidates at three cost rows. It
performs **no parameter search, no configuration selection, no optimization and no
re-optimization**; the only root-finders are the deterministic bisections (break-even cost,
benchmark parity, gate headroom), and each is reported with its bracket. The number of
*configurations examined* is 1 for every candidate, so no multiple-testing correction is
required for the screen itself. The re-derived walk-forward statistics are a **validation** of
the screen, not a selection over configurations.

## Reproduction commands (Cycle 882)

```bash
python research/cost_admissibility_screen.py     # -> OVERALL: PASS, exit 0, prints every number
python -m pytest tests/test_cost_admissibility_screen.py -q   # 30 passed
python -m pytest -q                               # 132 passed (102 pre-existing + 30 new)
python research/go_no_go_evaluation.py            # NO-GO, side_effect_free: True
git status --porcelain data/ config/              # empty (nothing written under data/ or config/)
```

Read-only proof: the tool takes a SHA-256 fingerprint of all files under `data/` and `config/`
before and after the run and requires them to be identical.

## Decision label (Cycle 882)

**No candidate's label changes.** The screen is a cost filter that is necessary and not
sufficient; adding three candidates and one decision number to it changes no label:

| Candidate | Label before | Label after |
|---|---|---|
| `overnight_capture_001` | Rejected/failed (Cycle 880, on cost) | Rejected/failed (unchanged) |
| `calendar_effects_001` | Rejected/failed (Cycle 18, on the walk-forward gate) | Rejected/failed (unchanged; its gate headroom is **negative**, so the cost screen cannot promote it either) |
| `tsmomentum_spytrend_001` | Credible candidate (incumbent) | Credible candidate (unchanged; NO-GO on the live paper record is unchanged) |
| `csmomentum_001` | Rejected/failed (Cycle 871, on the walk-forward gate) | Rejected/failed (unchanged; the cost screen clears it, which is **not** evidence of an edge) |
| `sectorrotation_001` | Rejected/failed (Cycle 869, NO-GO on the promotion gates) | Rejected/failed (unchanged; the cost screen clears it, which is **not** evidence of an edge) |
| `macroregime_001` | Rejected/failed (Cycle 871, on the walk-forward gate) | Rejected/failed (unchanged; the cost screen clears it, which is **not** evidence of an edge) |

**Answer to the cycle's objective question.** *Which remaining candidate, if any, has enough
cost headroom to be worth a promotion-gate test, and is that headroom an edge or only survival?*

**None of them, and the headroom they have is only survival.** `csmomentum_001`,
`sectorrotation_001` and `macroregime_001` all survive their own costs with a very large margin
(gross signal 62x to 141x what their turnover requires, break-even costs of 180 to 402 bp/unit
against the model's 3 bp/unit), but:

1. every one of them is **below** the repository's 0.9 walk-forward gate **before a single basis
   point is charged** (canonical walk-forward mean OOS Sharpe 0.8458 / 0.8529 / 0.4733);
2. every one of them has a **negative gate headroom** (-30.10 / -25.31 bp/unit, and no crossing at
   all for `macroregime_001`), i.e. it would have to be **paid** to trade to reach the gate, so no
   cost level and no rebate promotes it;
3. every one of them has a **negative benchmark-parity cost** (-5.33 / -31.16 / -86.15 bp/unit),
   i.e. at *zero* cost it still does not match passive close-to-close holding of the same basket
   on the same folds.

Their cost headroom is a statement about how little they trade, not about an edge. The shortlist's
remaining rows therefore support **no further candidate evaluation**: the three stay
**Rejected/Failed** on their own pre-registered gates, and the cost screen adds no candidate.
The incumbent is the only candidate with a positive gate headroom (+37.51 bp/unit, 12.5x the
model's cost) - and even that is *survival*; the incumbent's edge comes from its own walk-forward
record, not from this screen.
