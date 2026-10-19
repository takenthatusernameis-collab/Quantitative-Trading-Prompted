# Cost-Admissibility Screen (cost_admissibility_screen_001, Cycle 881)

**Generated:** 2026-10-19 | **code revision:** 04ff5e7
**Tool:** `research/cost_admissibility_screen.py` (read-only, deterministic, exit 0 on `OVERALL: PASS`)
**Cost model:** the repository's flat model, `get_cost_params()` = 1 bp commission + 2 bp slippage
= **3.0 bp per unit of weight change**; sensitivity rows 3 / 5 / 10 bp per unit.

## Why this screen exists

Cycle 880 rejected the overnight-session capture candidate `overnight_capture_001` on **cost**:
its gross overnight premium is +9.16%/yr, but an overnight-only leg must be flat during the
day, so it round-trips **twice per session** -> 504 units of annual turnover -> **15.12%/yr** of
cost at 3 bp/unit, i.e. more than the gross premium. The shortlist
(`research/reports/opportunity_shortlist.md`) ranks candidates by *gross* effect size and states
no candidate's annualized cost drag, so the same failure mode can recur silently for the next
candidate. This screen is that missing column.

Cycle 880 also published an **erratum**: a stated cost drag of "1.51%/yr" that was really
15.12%/yr. Nothing in the repository checked a stated drag against the turnover the strategy
actually incurs. This cycle adds that check as a **mechanical guard** (section 5).

## Headline

| Candidate | Gross annualized signal | Annual turnover (units/yr) | Drag @3 bp | Drag @5 bp | Drag @10 bp | Break-even cost | Min gross signal needed @3 bp | Admissibility |
|---|---|---|---|---|---|---|---|---|
| `overnight_capture_001` | +9.1558% | 504.00 | +15.1200% | +25.2000% | +50.4000% | 1.7385 bp/unit | +15.1200% | **INADMISSIBLE** |
| `calendar_effects_001` | +2.7326% | 24.13 | +0.7239% | +1.2064% | +2.4128% | 11.1639 bp/unit | +0.7239% | **ADMISSIBLE** |
| `tsmomentum_spytrend_001` | +13.8825% | 12.16 | +0.3649% | +0.6082% | +1.2165% | 106.7540 bp/unit | +0.3649% | **ADMISSIBLE** |

Read the verdict column as a **necessary, not sufficient** condition (section 6).

## Findings

1. **`overnight_capture_001` is INADMISSIBLE at the repository's own cost model.** Its gross signal
   is +9.1558%/yr against a required minimum of
   +15.1200%/yr, i.e. only **0.606x** of what its
   own turnover requires. It stops covering its costs at **1.7385 bp/unit**, which is
   57.9% of the 3.0 bp/unit the model
   charges, and it needs a cost of only **0.2912 bp/unit** to match passive
   close-to-close holding of the identical basket on the identical folds. Cycle 880's rejection
   is reproduced from the committed artifacts and its arithmetic is now mechanically checkable.
2. **`calendar_effects_001` is ADMISSIBLE on cost but has no edge the cost can pay for.** Its
   break-even cost is 11.1639 bp/unit (3.72x the model
   cost) and its gross signal is 3.775x the minimum it needs, so the cost screen
   clears it. But the *parity* cost is **negative**: to merely match passive close-to-close
   holding of the same basket on the same folds it would have to be **paid
   22.6852 bp/unit** of turnover. Its gross signal is *worse* than the passive
   basket's, and no positive cost level closes that gap. Cost-admissibility is therefore **not**
   evidence of an edge, and the screen must never be read as one.
3. **The incumbent is ADMISSIBLE with a very large margin.** Its break-even cost is
   106.7540 bp/unit (35.6x the model cost) and it still
   beats the passive 1/7 basket on the same folds at **32.3052 bp/unit**
   (10.8x the model cost). Its gross signal is
   38.04x the minimum it needs. This is the quantitative sense in which the
   incumbent's ranking is not a close call.
4. **The shortlist's gross-effect ranking is not preserved by the cost screen.** Ranked by
   break-even cost the three candidates are
   `tsmomentum_spytrend_001` (106.7540 bp/unit) >
   `calendar_effects_001` (11.1639 bp/unit) >
   `overnight_capture_001` (1.7385 bp/unit), whereas the shortlist's ranking is by gross
   effect size and states no cost column at all. **The cost screen has to be applied before a
   candidate is short-listed, not after it has been back-tested.**

## 1. Method

For each candidate the screen rebuilds, from the committed cache and the committed artifacts
only:

* the candidate's **daily gross return series** (zero cost), and
* the candidate's **daily turnover series** (units of weight change per session),

then computes, on the candidate's own committed window:

1. **annualized gross signal** = `(1 + gross).prod() ** (252/n) - 1` (geometric annualization
   of the zero-cost return series);
2. **annualized cost drag** at 3 / 5 / 10 bp per unit
   = `mean(daily turnover) * 252 * cost_bps / 10000` (the arithmetic annualization of the daily
   cost series; this is the definition the Cycle 880 report used);
3. **net annualized return** at each cost row, and the net canonical Sharpe;
4. **break-even cost per unit**: the cost at which the net annualized return is exactly zero
   (bisection on a monotone-decreasing objective);
5. **cost per unit at which the candidate's net walk-forward Sharpe equals the same-fold
   close-to-close benchmark's** (the candidate and the benchmark are evaluated on the *same*
   folds and at the *same* cost level, so the comparison is like-for-like);
6. **minimum gross signal required for admissibility** at 3 bp/unit, which is by definition the
   candidate's own annualized cost drag at 3 bp/unit;
7. the **admissibility verdict**: ADMISSIBLE when the net annualized return at 3 bp/unit is
   positive, INADMISSIBLE otherwise.

The **benchmark** is a close-to-close equal-weight buy-and-hold of the candidate's own universe
on the candidate's own folds, with one unit of turnover in the first session and none afterwards
(the repository's own `1/N Equal-Weight` convention; for `overnight_capture_001` this is exactly
the benchmark Cycle 880 published). A symbol without a price history yet contributes zero, i.e.
the remainder is held in cash.

**What this cycle does not do.** No candidate is re-optimized, no parameter is selected, no
threshold is changed, no gate is re-thresholded, and no candidate's published verdict is
re-decided. The walk-forward statistics are re-derived only to (a) validate that the screen
reproduces the committed records and (b) place the candidate and its benchmark on identical
folds. A re-derivation that does not match a committed record is reported as a **FAIL**, never
re-tuned.

## 2. Candidates screened

### Overnight-session capture (overnight leg, 1/3 SPY/QQQ/IWM)

* candidate id: `overnight_capture_001` (role: candidate)
* universe: SPY, QQQ, IWM
* screen window: 2000-05-26 -> 2026-10-16 (6637 sessions)
* walk-forward: 33 folds, research/overnight_capture_backtest.py (Cycle 880)

| Quantity | Value |
|---|---|
| Annualized turnover (units of weight change / yr) | 504.0000 |
| **Annualized gross signal (zero cost, geometric)** | **+9.1558%** |
| Annualized gross signal (arithmetic, zero cost) | +9.5116% |
| **Minimum gross signal required for admissibility at 3 bp/unit** | **+15.1200%** |
| Gross signal surplus vs the requirement | -5.9642% |
| **Break-even cost per unit (net annualized return = 0)** | **1.7385 bp/unit** |
| Cost per unit at which the net WF Sharpe equals the same-fold benchmark's | 0.2912 bp/unit |
| Cost per unit at which the net full-window canonical Sharpe equals the benchmark's | 0.7806 bp/unit |
| WF mean OOS Sharpe (3 bp/unit) | -0.599718 |
| Benchmark WF mean OOS Sharpe (3 bp/unit, same folds) | 0.844696 |
| Positive fold rate / pooled OOS trades | 15.1515% / 8016 |
| **Admissibility verdict (3 bp/unit)** | **INADMISSIBLE** |

Cost sensitivity of the screen's own quantities:

| Cost (bp/unit) | Annualized cost drag | Net annualized return | Net canonical Sharpe | WF mean OOS Sharpe |
|---|---|---|---|---|
| 3 | +15.1200% | -6.1612% | -0.4590 | -0.5997 |
| 5 | +25.2000% | -15.1631% | -1.2840 | -1.5469 |
| 10 | +50.4000% | -34.0807% | -3.3465 | -3.5375 |

Provenance: config = config/overnight_capture_001.yaml; config_sha256[:12] = bb44adfbc500; price_cache = data/raw/{SPY,QQQ,IWM}.parquet; evaluation_script = research/overnight_capture_backtest.py (Cycle 880); hypothesis = research/hypotheses/overnight_capture_001.md

### Turn-of-month window exposure (1/3 SPY/QQQ/IWM, pre=1/post=3)

* candidate id: `calendar_effects_001` (role: candidate)
* universe: SPY, QQQ, IWM
* screen window: 2000-05-26 -> 2026-10-09 (6632 sessions)
* walk-forward: 33 folds, research/run_cycle18.py (Cycle 18)

| Quantity | Value |
|---|---|
| Annualized turnover (units of weight change / yr) | 24.1285 |
| **Annualized gross signal (zero cost, geometric)** | **+2.7326%** |
| Annualized gross signal (arithmetic, zero cost) | +3.1356% |
| **Minimum gross signal required for admissibility at 3 bp/unit** | **+0.7239%** |
| Gross signal surplus vs the requirement | +2.0087% |
| **Break-even cost per unit (net annualized return = 0)** | **11.1639 bp/unit** |
| Cost per unit at which the net WF Sharpe equals the same-fold benchmark's | -22.6852 bp/unit |
| Cost per unit at which the net full-window canonical Sharpe equals the benchmark's | -4.9885 bp/unit |
| WF mean OOS Sharpe (3 bp/unit) | -0.025432 |
| Benchmark WF mean OOS Sharpe (3 bp/unit, same folds) | 0.844696 |
| Positive fold rate / pooled OOS trades | 42.4242% / 761 |
| **Admissibility verdict (3 bp/unit)** | **ADMISSIBLE** |

Cost sensitivity of the screen's own quantities:

| Cost (bp/unit) | Annualized cost drag | Net annualized return | Net canonical Sharpe | WF mean OOS Sharpe |
|---|---|---|---|---|
| 3 | +0.7239% | +1.9913% | 0.2573 | -0.0254 |
| 5 | +1.2064% | +1.5000% | 0.2057 | -0.0915 |
| 10 | +2.4128% | +0.2816% | 0.0770 | -0.2545 |

Provenance: config = config/calendar_effects_001.yaml; config_sha256[:12] = ea4e13ef7c34; price_cache = data/raw/{SPY,QQQ,IWM}.parquet; committed_weights = data/processed/weights_calendar_effects_001.parquet; committed_simulation = data/processed/simulation_calendar_effects_001.parquet; evaluation_script = research/run_cycle18.py (Cycle 18); hypothesis = research/hypotheses/calendar_effects_001.md

### TSMOM incumbent (226d lookback, 21d skip, top-50%, vol 10%, DD 15%, SPY 200d SMA)

* candidate id: `tsmomentum_spytrend_001` (role: incumbent)
* universe: SPY, QQQ, IWM, TLT, GLD, EFA, EEM
* screen window: 1993-01-29 -> 2026-10-09 (8482 sessions)
* walk-forward: 48 folds, research/run_cycle7.py (Cycle 7) / committed artifact

| Quantity | Value |
|---|---|
| Annualized turnover (units of weight change / yr) | 12.1645 |
| **Annualized gross signal (zero cost, geometric)** | **+13.8825%** |
| Annualized gross signal (arithmetic, zero cost) | +13.3822% |
| **Minimum gross signal required for admissibility at 3 bp/unit** | **+0.3649%** |
| Gross signal surplus vs the requirement | +13.5175% |
| **Break-even cost per unit (net annualized return = 0)** | **106.7540 bp/unit** |
| Cost per unit at which the net WF Sharpe equals the same-fold benchmark's | 32.3052 bp/unit |
| Cost per unit at which the net full-window canonical Sharpe equals the benchmark's | 72.1446 bp/unit |
| WF mean OOS Sharpe (3 bp/unit) | 0.928608 |
| Benchmark WF mean OOS Sharpe (3 bp/unit, same folds) | 0.705721 |
| Positive fold rate / pooled OOS trades | 95.8333% / 6071 |
| **Admissibility verdict (3 bp/unit)** | **ADMISSIBLE** |

Cost sensitivity of the screen's own quantities:

| Cost (bp/unit) | Annualized cost drag | Net annualized return | Net canonical Sharpe | WF mean OOS Sharpe |
|---|---|---|---|---|
| 3 | +0.3649% | +13.4685% | 1.4960 | 0.9286 |
| 5 | +0.6082% | +13.1933% | 1.4688 | 0.9795 |
| 10 | +1.2165% | +12.5081% | 1.4003 | 1.0017 |

Provenance: config = config/simulation_candidate_001.yaml; config_sha256[:12] = 3c8f5b899f1f; committed_simulation = data/processed/simulation_candidate_001.parquet; committed_weights = data/processed/weights_full_history.parquet; price_cache = data/raw/{SPY,QQQ,IWM,TLT,GLD,EFA,EEM}.parquet; evaluation_script = research/run_cycle7.py (Cycle 7) / committed artifact; hypothesis = research/experiments/tsmomentum_regime_filter_wf_001.md


## 3. Reproduction of the committed records

| Candidate | Quantity | Published | Re-derived | Match |
|---|---|---|---|---|
| `overnight_capture_001` | Annualized cost drag at 3 bp/unit | 0.1512 | 0.151200 | yes |
| `overnight_capture_001` | Net WF mean OOS Sharpe | -0.599718 | -0.599718 | yes |
| `overnight_capture_001` | Benchmark WF mean OOS Sharpe | +0.844696 | 0.844696 | yes |
| `calendar_effects_001` | Net WF mean OOS Sharpe | -0.0254 | -0.025432 | yes |
| `calendar_effects_001` | Positive fold rate | 0.424242 | 0.424242 | yes |
| `calendar_effects_001` | Pooled OOS trades | 761 | 761 | yes |
| `tsmomentum_spytrend_001` | Net WF mean OOS Sharpe (48 folds) | 0.9473 | 0.928608 | within the repository's declared tolerance (section 4) |
| `tsmomentum_spytrend_001` | Test-period Sharpe (2018-2026) | 1.4178 | 1.407770 | within the repository's declared tolerance (section 4) |

## 4. Two disclosed differences (not screen failures)

* **`calendar_effects_001` and `tsmomentum_spytrend_001` artifacts are older than the raw cache.**
  The committed processed artifacts stop at **2026-10-09**; the committed price cache now runs
  to **2026-10-16**. The screen therefore **clips** the price frame to each candidate's
  committed artifact end date before rebuilding anything. Without that clip the rebuilt
  calendar weights would no longer match the committed artifact (max abs weight difference
  0.3333) and the walk-forward would silently change. This is a property of the committed
  artifacts, not a defect of the screen.
* **The incumbent's published baseline is a re-run, the committed artifact is a full-history
  run.** The published numbers (test Sharpe 1.4178, 48-fold WF mean 0.9473) come from a
  configuration re-run with `overlay_warmup: "slice"` (overlay state initialised at the
  evaluation window start, `research/reports/simulation_verification_001.md`). The committed
  full-history artifact carries the overlay state from 1993, so slicing it to 2018+ gives a
  slightly different number. The difference is inside the repository's own declared
  tolerance (`research/run_cycle7.py`: `TOL_SHARPE = 0.02`) and the screen checks exactly that
  tolerance, not a tighter invented one. The screen's incumbent numbers are the
  artifact-derived ones, because the screen is defined to reuse committed artifacts.

## 5. The mechanical guard (Cycle 880 erratum)

`check_cost_drag_consistency(stated_cost_drag, annual_turnover, cost_bps_per_unit, tolerance=1e-9)`
asserts

```
cost_drag == annual_turnover * cost_bps_per_unit / 10000      (within 1e-9)
```

The guard is applied to (a) every cost-drag figure the screen itself states, (b) the drag
figures published in the committed records, and (c) the Cycle 880 erratum value as a
**negative control** at every cost row: a drag understated by a factor of 10 must be
*rejected* (3 bp/unit: stated 0.0151 vs expected 0.151200, abs difference 0.1361; 5 bp/unit:
0.0252 vs 0.252000, 0.2268; 10 bp/unit: 0.0504 vs 0.504000, 0.4536) -- seven to eight orders
of magnitude above the tolerance in every case. `require_cost_drag_consistency` raises
`ValueError`, so a screen that states an inconsistent drag cannot complete. The guard is
unit-tested in `tests/test_cost_admissibility_screen.py`.

## 6. Limitations (necessary, not sufficient)

The screen is a **cost** filter. It is necessary for a candidate to be worth a walk-forward
evaluation and it is **not** sufficient for promotion. In particular it says nothing about:

* the **sign or the statistical significance** of the gross signal (a candidate with a large
  gross signal and a large drag can be "ADMISSIBLE" and still lose money);
* **robustness**, **multiple-testing control**, **out-of-sample stability** or **capacity**;
* costs **not** in the flat per-unit model: borrow, funding, market impact, spread crossing,
  partial fills, exchange fees, or the operational cost of a higher-turnover implementation;
* the difference between a **modelled** cost per unit and an **executed** one;
* the difference between a **backtest** cost model and a **paper-trading** one.

A candidate that passes the screen can still be rejected by the promotion gates, and a
candidate that fails the screen is rejected on cost before any further work is justified.

## 7. Self-checks

| Check | Result | Detail |
|---|---|---|
| `repository_cost_model_is_3_bps_per_unit` | PASS | get_cost_params() -> commission 1.0 bps + slippage 2.0 bps = 3.0 bps per unit of weight change. |
| `overnight_session_leg_decomposition_is_exact` | PASS | (1+overnight)*(1+intraday)-1 == close-to-close to 2.220e-16 over 6637 sessions; 0 missing opens. |
| `calendar_candidate_rebuilds_its_committed_artifacts_exactly` | PASS | the rebuilt turn-of-month weights, gross returns and turnover match data/processed/weights_calendar_effects_001.parquet and data/processed/simulation_calendar_effects_001.parquet with max abs difference 0.000e+00 over 8482 sessions. |
| `incumbent_committed_artifact_is_internally_consistent` | PASS | cost == turnover * 3.0 bp/unit (0.000e+00), net == gross - cost (1.735e-18) and the weight_* columns of data/processed/simulation_candidate_001.parquet equal data/processed/weights_full_history.parquet (1.055e-15); all within the 1e-12 parquet round-trip tolerance. |
| `guard_accepts_the_published_overnight_cost_drag` | PASS | stated 0.1512 == 504.0 units/yr x 3 bp/unit = 0.151200 (abs diff 2.776e-17 <= 1e-09). |
| `guard_rejects_the_cycle_880_factor_10_erratum` | PASS | the stated 0.0151 with 504 units/yr at 3 bp/unit is rejected: expected 0.151200, abs diff 1.361e-01 > 1e-09. |
| `guard_rejects_the_factor_10_erratum_at_every_cost_row` | PASS | a factor-10 understated drag is rejected at 3 bp/unit (abs diff 1.361e-01), 5 bp/unit (abs diff 2.268e-01), 10 bp/unit (abs diff 4.536e-01), every one of them far above the 1e-09 tolerance. |
| `guard_raises_on_an_inconsistent_figure` | PASS | require_cost_drag_consistency raises ValueError on the factor-10 error, so a screen that states an inconsistent drag cannot complete. |
| `every_stated_cost_drag_passes_the_guard` | PASS | each candidate's own stated annualized cost drag equals its own stated annual turnover times the cost per unit to within 1e-9. |
| `overnight_capture_001_reproduces_net_WF_mean_OOS_Sharpe` | PASS | published -0.599718 vs re-derived -0.599718 (abs diff 1.082e-07 <= 1e-06). |
| `overnight_capture_001_reproduces_benchmark_WF_mean_OOS_Sharpe` | PASS | published +0.844696 vs re-derived +0.844696 (abs diff 3.486e-07 <= 1e-06). |
| `overnight_capture_001_reproduces_positive_fold_rate` | PASS | published +0.151515 vs re-derived +0.151515 (abs diff 1.515e-07 <= 1e-06). |
| `overnight_capture_001_reproduces_pooled_oos_trades` | PASS | published 8016 vs re-derived 8016 pooled out-of-sample trades. |
| `calendar_effects_001_reproduces_net_WF_mean_OOS_Sharpe` | PASS | published -0.025400 vs re-derived -0.025432 (abs diff 3.226e-05 <= 1e-04). |
| `calendar_effects_001_reproduces_positive_fold_rate` | PASS | published +0.424242 vs re-derived +0.424242 (abs diff 4.242e-07 <= 1e-04). |
| `calendar_effects_001_reproduces_pooled_oos_trades` | PASS | published 761 vs re-derived 761 pooled out-of-sample trades. |
| `incumbent_walk_forward_has_48_folds` | PASS | the 1993-2026 geometry of the frozen configuration yields 48 folds (the published Cycle 6 record also states 48 folds). |
| `tsmomentum_spytrend_001_reproduces_net_WF_mean_OOS_Sharpe` | PASS | published +0.947300 vs re-derived +0.928608 (abs diff 1.869e-02 <= 2e-02). |
| `tsmomentum_spytrend_001_reproduces_test_period_Sharpe_2018-2026` | PASS | published +1.417800 vs re-derived +1.407770 (abs diff 1.003e-02 <= 2e-02). |
| `benchmark_walk_forward_sharpe_is_cost_invariant` | PASS | the close-to-close benchmark's walk-forward Sharpe is the same at 3 bp/unit and at 10 bp/unit for every candidate (its only turnover is the initial purchase, which sits before the first test window), so the benchmark-parity cost compares the candidate and the benchmark at the same cost level on the same folds. |
| `screen_is_deterministic` | PASS | re-running the screen on the same inputs reproduces the annual turnover, the gross annualized signal, the minimum required gross signal and the WF mean OOS Sharpe bit-for-bit. |
| `no_file_under_data_or_config_changed` | PASS | the SHA-256 fingerprint of all 1844 files under data/ and config/ is identical before and after the run. |

**OVERALL: PASS** (22/22 checks passed)
