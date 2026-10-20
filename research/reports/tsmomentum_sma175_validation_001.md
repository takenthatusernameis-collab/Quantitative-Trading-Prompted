# TSMomentum SPY-Trend SMA-175 Candidate Validation (tsmomentum_sma175_validation_001, Cycle 914)

## Summary

- Candidate: `tsmomentum_spytrend_001` (the incumbent)
- Mutation under validation: change the SPY trend-filter SMA window from 200 to 175 days (all other candidate parameters unchanged)
- Published walk-forward record (resolved by content): `research/experiments/tsmomentum_regime_filter_wf_001.md`
- Published (SMA-200) 48-fold WF mean OOS Sharpe: 0.947307 (gate-1 PASS, margin +0.047307)
- Candidate (SMA-175) 48-fold WF mean OOS Sharpe: 1.539964 (gate-1 PASS, margin +0.639964)
- Phase stability -- SMA-200: phase A 1.385035 (PASS), phase B 0.509580 (FAIL); SMA-175: phase A 1.539145 (PASS), phase B 1.540784 (PASS)
- SMA-plateau rule: 6/6 windows reach Sharpe >= 0.9; gate for SMA-175: **PASS**, for SMA-200: **PASS**
- Verdict: **Credible candidate for further validation (not promoted)** (promotion performed: no)
- Read-only: `data/` and `config/` byte-identical before and after the run (**yes**); no committed artifact modified (**yes**).
- Data source: committed parquet cache in data/raw/ (fetcher never called).

## 1. Data, protocol and the END_DATE cap

| Item | Value |
|---|---|
| Source | committed parquet cache in data/raw/ (fetcher never called) |
| Universe | SPY, QQQ, IWM, TLT, GLD, EFA, EEM |
| Protocol date range | 1993-01-01 to 2026-10-09 |
| Cached panel | 1993-01-29 to 2026-10-19 (8488 sessions) |
| Panel used | 2026-10-09 (8482 sessions) |
| Sessions dropped after END_DATE | 6 |
| Signal | TSMOM lookback 226, skip 21, top_fraction 0.5 |
| Risk overlay | vol-target 0.1 (lookback 63) + drawdown control 0.15 |
| Regime filter | SPY 200-day SMA (incumbent) vs 175-day SMA (candidate) |
| Walk-forward | train 10.0y / test 12.0m / step 6.0m, purge 21d, embargo 21d |
| Cost model | 1.0 bps commission + 2.0 bps slippage = 3.0 bps round-trip (unchanged); risk-free 0.02 annual |
| Gates (pre-registered) | WF mean OOS Sharpe >= 0.9, positive fold rate >= 0.5, pooled OOS trades > 100, SMA plateau >= 2/6 windows |

- the committed cache extends past the published protocol END_DATE; the panel is capped at END_DATE so the published data range (and the published plateau table) is reproduced exactly.
- Point-in-time treatment: signals use only data available at formation (weights shifted one day), the SPY SMA is computed point-in-time, the overlay/cost model are applied on the same continuously computed path for every fold and phase, and the panel is capped at the published END_DATE.
- The committed cache now carries sessions past the published protocol's END_DATE, which shifts the (unbounded) plateau test period; capping the panel at END_DATE reproduces the published plateau table exactly, and leaves the walk-forward design unchanged (its fold windows are already bounded by END_DATE).

## 2. Anchor A -- the published 48-fold design (SMA-200, incumbent)

| Metric | Recomputed | Published | Match |
|---|---|---|---|
| n_folds | 48 | 48 | YES |
| mean_test_sharpe | 0.9473074720246092 | 0.9473 | YES |
| std_test_sharpe | 3.4797702418403893 | 3.4798 | YES |
| median_test_sharpe | 1.29329878363231 | 1.2933 | YES |
| min_test_sharpe | -21.829879416796786 | -21.8299 | YES |
| max_test_sharpe | 3.9121052879675915 | 3.9121 | YES |
| pct_positive_sharpe | 0.9166666666666666 | 91.7% | YES |
| mean_test_ann_return | 0.1471459015552229 | 14.71% | YES |
| mean_test_max_dd | -0.05407695492453209 | -5.41% | YES |
| mean_test_trades | 125.27083333333333 | 125.3 | YES |
| total_test_trades | 6013 | 6013 | YES |

- Per-fold reproduction: 48 folds compared, all match: **YES**.

## 3. Anchor B -- the published SMA-plateau table

| SMA Window | Test Sharpe (recomputed) | Published | Ann. Return | Published | Max DD | Published | Trades | Published | Match |
|---|---|---|---|---|---|---|---|---|---|
| 150 | 1.5504 | 1.5504 | 0.1570 | 0.1570 | -0.0682 | -0.0682 | 1170 | 1170 | YES |
| 175 | 1.4933 | 1.4933 | 0.1517 | 0.1517 | -0.0682 | -0.0682 | 1204 | 1204 | YES |
| 200 | 1.4178 | 1.4178 | 0.1446 | 0.1446 | -0.0779 | -0.0779 | 1196 | 1196 | YES |
| 226 | 1.3178 | 1.3178 | 0.1359 | 0.1359 | -0.0779 | -0.0779 | 1233 | 1233 | YES |
| 250 | 1.2781 | 1.2781 | 0.1324 | 0.1324 | -0.0820 | -0.0820 | 1279 | 1279 | YES |
| 277 | 1.2270 | 1.2270 | 0.1282 | 0.1282 | -0.0876 | -0.0876 | 1303 | 1303 | YES |

- Plateau period: 2017-12-31 -> 2026-10-09 (post-VAL_END test period).
- Rule: >= 2 of 6 pre-specified windows reach Sharpe >= 0.9, and the candidate's own baseline window is one of them. Windows at or above Sharpe 0.9: **6/6** (150, 175, 200, 226, 250, 277).
- Gate for the incumbent (baseline window 200): **PASS**; for the candidate (baseline window 175): **PASS**.

## 4. The candidate (SMA-175) on the published 48-fold walk-forward

| Design | Folds | WF mean OOS Sharpe | Median | Positive fold rate | Pooled OOS trades | Gate 1 | Gate 2 | Gate 3 | Decision |
|---|---|---|---|---|---|---|---|---|---|
| SMA-200 (incumbent) | 48 | 0.947307 | 1.2933 | 0.9167 | 6013 | PASS (+0.0473) | PASS (+0.4167) | PASS (+5913) | Passes preliminary gates |
| SMA-175 (candidate) | 48 | 1.539964 | 1.3787 | 0.9583 | 5946 | PASS (+0.6400) | PASS (+0.4583) | PASS (+5846) | Passes preliminary gates |

### 4.1 Candidate gate table (SMA-175)

- wf_mean_oos_sharpe: threshold 0.9, observed 1.539964, margin 0.639964, status PASS
- positive_fold_rate: threshold 0.5, observed 0.958333, margin 0.458333, status PASS
- pooled_oos_trades: threshold 100, observed 5946, margin 5846.000000, status PASS

### 4.2 Per-fold comparison

| Fold | Test Start | Test End | SMA-200 Test Sharpe | SMA-175 Test Sharpe | SMA-200 Trades | SMA-175 Trades |
|---|---|---|---|---|---|---|
| 1 | 2002-09-30 | 2003-09-16 | 2.5550 | 2.8243 | 94 | 99 |
| 2 | 2003-03-25 | 2004-03-10 | 2.5821 | 2.5835 | 215 | 216 |
| 3 | 2003-09-17 | 2004-09-02 | 0.3027 | 0.6399 | 211 | 206 |
| 4 | 2004-03-11 | 2005-02-25 | 1.2700 | 1.7595 | 154 | 147 |
| 5 | 2004-09-03 | 2005-08-22 | 1.9494 | 2.0850 | 146 | 110 |
| 6 | 2005-02-28 | 2006-02-14 | 2.1849 | 2.1029 | 146 | 110 |
| 7 | 2005-08-23 | 2006-08-09 | 2.3382 | 2.9127 | 163 | 152 |
| 8 | 2006-02-15 | 2007-02-01 | 1.8912 | 2.5660 | 207 | 196 |
| 9 | 2006-08-10 | 2007-07-27 | 1.3166 | 1.4642 | 230 | 229 |
| 10 | 2007-02-02 | 2008-01-21 | 2.0815 | 2.5262 | 198 | 186 |
| 11 | 2007-07-30 | 2008-07-15 | 2.7409 | 3.6312 | 78 | 66 |
| 12 | 2008-01-22 | 2009-01-07 | -21.8299 | 0.2791 | 2 | 2 |
| 13 | 2008-07-16 | 2009-07-02 | -0.2665 | 0.3553 | 8 | 14 |
| 14 | 2009-01-08 | 2009-12-25 | 1.7670 | 1.7316 | 114 | 136 |
| 15 | 2009-07-03 | 2010-06-21 | 1.5242 | 1.0678 | 212 | 223 |
| 16 | 2009-12-28 | 2010-12-14 | 1.0671 | 0.8092 | 150 | 143 |
| 17 | 2010-06-22 | 2011-06-08 | 1.0960 | 1.0966 | 164 | 163 |
| 18 | 2010-12-15 | 2011-12-01 | 0.2426 | 0.4856 | 162 | 156 |
| 19 | 2011-06-09 | 2012-05-25 | 0.9429 | 1.3835 | 50 | 44 |
| 20 | 2011-12-02 | 2012-11-19 | 1.2267 | 1.3437 | 24 | 26 |
| 21 | 2012-05-28 | 2013-05-14 | 2.2063 | 2.2547 | 131 | 133 |
| 22 | 2012-11-20 | 2013-11-06 | 2.1734 | 2.1734 | 238 | 238 |
| 23 | 2013-05-15 | 2014-05-01 | 0.8107 | 0.8107 | 236 | 236 |
| 24 | 2013-11-07 | 2014-10-24 | 0.4830 | 0.4830 | 184 | 184 |
| 25 | 2014-05-02 | 2015-04-20 | 1.1702 | 1.1702 | 102 | 102 |
| 26 | 2014-10-27 | 2015-10-13 | 0.8976 | 1.0229 | 35 | 43 |
| 27 | 2015-04-21 | 2016-04-06 | 0.2792 | 0.4714 | 18 | 28 |
| 28 | 2015-10-14 | 2016-09-29 | 1.3453 | 1.3739 | 28 | 30 |
| 29 | 2016-04-07 | 2017-03-24 | 0.2969 | 0.3672 | 29 | 29 |
| 30 | 2016-09-30 | 2017-09-18 | 0.6332 | 0.6986 | 60 | 60 |
| 31 | 2017-03-27 | 2018-03-13 | 1.6764 | 1.6764 | 75 | 75 |
| 32 | 2017-09-19 | 2018-09-05 | 1.1373 | 1.3533 | 148 | 144 |
| 33 | 2018-03-14 | 2019-02-28 | 0.2472 | 0.3550 | 130 | 128 |
| 34 | 2018-09-06 | 2019-08-23 | 1.0883 | 0.9474 | 28 | 30 |
| 35 | 2019-03-01 | 2020-02-17 | 3.2521 | 3.2521 | 26 | 26 |
| 36 | 2019-08-26 | 2020-08-11 | 3.9121 | 3.9121 | 24 | 24 |
| 37 | 2020-02-18 | 2021-02-03 | 2.3629 | 2.3629 | 124 | 124 |
| 38 | 2020-08-12 | 2021-07-29 | 0.7952 | 0.7952 | 233 | 233 |
| 39 | 2021-02-04 | 2022-01-21 | -0.0836 | -0.0836 | 243 | 243 |
| 40 | 2021-07-30 | 2022-07-18 | -0.1073 | -0.0206 | 148 | 143 |
| 41 | 2022-01-24 | 2023-01-10 | 0.8947 | 0.9691 | 29 | 32 |
| 42 | 2022-07-19 | 2023-07-05 | 1.5584 | 1.7177 | 32 | 61 |
| 43 | 2023-01-11 | 2023-12-28 | 1.8332 | 2.1372 | 118 | 128 |
| 44 | 2023-07-06 | 2024-06-21 | 1.8186 | 1.9209 | 185 | 175 |
| 45 | 2023-12-29 | 2024-12-16 | 1.8342 | 1.8342 | 220 | 220 |
| 46 | 2024-06-24 | 2025-06-10 | 1.1148 | 1.0502 | 186 | 183 |
| 47 | 2024-12-17 | 2025-12-03 | 1.9609 | 1.9015 | 115 | 112 |
| 48 | 2025-06-11 | 2026-05-28 | 2.8969 | 3.3635 | 160 | 158 |

### 4.3 Fold influence (leave-one-out)

- **SMA-200 (incumbent)**: mean 0.947307, median 1.293299, trimmed mean (min/max removed) 1.378012; most influential fold 12 (Sharpe -21.8299, 2 trades, LOO mean 1.431928, shift +0.484621); thin-trade folds (<= 10 trades): [12, 13].
- **SMA-175 (candidate)**: mean 1.539964, median 1.378702, trimmed mean (min/max removed) 1.523690; most influential fold 36 (Sharpe 3.9121, 24 trades, LOO mean 1.489493, shift -0.050471); thin-trade folds (<= 10 trades): [12].

## 5. Phase decomposition (odd folds vs even folds)

| Phase | Design | Folds | WF mean OOS Sharpe | Median | Positive fold rate | Pooled OOS trades | Gate 1 | Decision |
|---|---|---|---|---|---|---|---|---|
| Phase A (odd folds) | SMA-200 (incumbent) | 24 | 1.385035 | 1.4204 | 0.9167 | 2952 | PASS (+0.4850) | Passes preliminary gates |
| Phase B (even folds) | SMA-200 (incumbent) | 24 | 0.509580 | 1.2483 | 0.9167 | 3061 | FAIL (-0.3904) | Rejected/Failed |
| Phase A (odd folds) | SMA-175 (candidate) | 24 | 1.539145 | 1.4238 | 0.9583 | 2922 | PASS (+0.6391) | Passes preliminary gates |
| Phase B (even folds) | SMA-175 (candidate) | 24 | 1.540784 | 1.3636 | 0.9583 | 3024 | PASS (+0.6408) | Passes preliminary gates |

- Phase A fold numbers: 1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35, 37, 39, 41, 43, 45, 47; phase B fold numbers: 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48.
- Gate-1 outcome changes between phases -- SMA-200: **YES**; SMA-175: **NO**.
- Phase means average to the published mean -- SMA-175: **YES** (1.539964 vs 1.539964).

## 6. Cost model and net-of-cost sensitivity (informational)

- The published cost model is used unchanged: 1.0 bps commission + 2.0 bps slippage = 3.0 bps round-trip. Every metric in this report is net of that cost.

| Round-trip cost (bps) | WF mean OOS Sharpe | Positive fold rate | Pooled OOS trades | Gate 1 |
|---|---|---|---|---|
| 0.0 | 1.606190 | 0.9792 | 5946 | PASS |
| 3.0 | 1.539964 | 0.9583 | 5946 | PASS |
| 6.0 | 1.473676 | 0.9583 | 5946 | PASS |
| 10.0 | 1.385244 | 0.9583 | 5946 | PASS |

- Informational only: the cost model itself is not changed and no gate depends on this table.

## 7. Parameter perturbation around SMA-175 (informational)

| SMA window | WF mean OOS Sharpe | Positive fold rate | Pooled OOS trades | Gate 1 | Phase A mean | Phase B mean | Phase-stable gate-1 |
|---|---|---|---|---|---|---|---|
| 165 | 1.554672 | 0.9792 | 5843 | PASS | 1.563143 | 1.546201 | YES |
| 170 | 1.548405 | 0.9583 | 5890 | PASS | 1.553047 | 1.543763 | YES |
| 175 | 1.539964 | 0.9583 | 5946 | PASS | 1.539145 | 1.540784 | YES |
| 180 | 1.512241 | 0.9375 | 5957 | PASS | 1.550398 | 1.474084 | YES |
| 185 | 1.074627 | 0.9375 | 5961 | PASS | 1.528878 | 0.620377 | NO |

- Informational only: this is a neighbourhood check around the candidate window, not a gate, and it is measured on the same folds that selected the window.

## 8. Verdict and caveats

- **Credible candidate for further validation (not promoted)**
- SMA-175 passes the published protocol on the published 48-fold design (gate-1 1.539964 >= 0.9, gate-2 0.9583 >= 0.5, gate-3 5946 > 100), is phase-stable (phase A 1.539145 / phase B 1.540784, both PASS) and passes the published SMA-plateau rule (6/6 windows, candidate baseline included). The incumbent SMA-200 is not phase-stable (phase B 0.509580 FAIL). Promotion is not performed by this tool: the parameter choice is in-sample, so a selection-aware holdout is required first. The SMA window was selected on the same 48 folds that are used to evaluate it (Cycle 913 scanned 175/170/180/150/190 on the published design and kept the first phase-stable window). The SMA-175 numbers are therefore in-sample with respect to the parameter choice: they are not independent evidence, and the selection itself (the number of windows tried) must be charged against the multiple-testing budget before promotion.
- Selection caveat: The SMA window was selected on the same 48 folds that are used to evaluate it (Cycle 913 scanned 175/170/180/150/190 on the published design and kept the first phase-stable window). The SMA-175 numbers are therefore in-sample with respect to the parameter choice: they are not independent evidence, and the selection itself (the number of windows tried) must be charged against the multiple-testing budget before promotion.
- No promotion was performed: `research/run_cycle6.py` is unchanged and the committed candidate definition still uses SMA 200.

## 9. Checks

- [cache_only_path_built]: PASS (observed: 8482 sessions (8488 cached), 7 symbols, last 2026-10-09, expected: non-empty cache-only panel capped at the published END_DATE)
- [published_record_resolved_by_content]: PASS (observed: research/experiments/tsmomentum_regime_filter_wf_001.md, expected: exactly one published walk-forward record carrying the published anchor)
- [reproduces_published_walk_forward_aggregate]: PASS (observed: n_folds=48 (published 48); mean_test_sharpe=0.9473074720246092 (published 0.9473); std_test_sharpe=3.4797702418403893 (published 3.4798); median_test_sharpe=1.29329878363231 (published 1.2933); min_test_sharpe=-21.829879416796786 (published -21.8299); max_test_sharpe=3.9121052879675915 (published 3.9121); pct_positive_sharpe=0.9166666666666666 (published 91.7%); mean_test_ann_return=0.1471459015552229 (published 14.71%); mean_test_max_dd=-0.05407695492453209 (published -5.41%); mean_test_trades=125.27083333333333 (published 125.3); total_test_trades=6013 (published 6013), expected: published aggregate statistics)
- [reproduces_published_walk_forward_fold_table]: PASS (observed: 48 folds compared, expected: every published fold reproduced)
- [reproduces_published_plateau_table]: PASS (observed: 150: sharpe 1.5504 vs published 1.5504, trades 1170 vs 1170; 175: sharpe 1.4933 vs published 1.4933, trades 1204 vs 1204; 200: sharpe 1.4178 vs published 1.4178, trades 1196 vs 1196; 226: sharpe 1.3178 vs published 1.3178, trades 1233 vs 1233; 250: sharpe 1.2781 vs published 1.2781, trades 1279 vs 1279; 277: sharpe 1.2270 vs published 1.2270, trades 1303 vs 1303, expected: every published plateau row reproduced (sharpe/return/dd/sortino/profit-factor/trades))
- [harness_matches_committed_path_builders]: PASS (observed: SMA-200 max|diff| ret=0.0 weights=0.0; SMA-175 max|diff| ret=0.0 weights=0.0, expected: local path builder is bit-identical to the committed path builders)
- [sma175_gate1_walkforward_mean_oos_sharpe]: PASS (observed: 1.539964 (margin +0.639964), expected: >= 0.9)
- [sma175_gate2_positive_fold_rate]: PASS (observed: 0.958333 (margin +0.458333), expected: >= 0.5)
- [sma175_gate3_pooled_oos_trades]: PASS (observed: 5946 (margin +5846), expected: > 100)
- [sma175_phase_stable_gate1]: PASS (observed: phase A 1.539145 (PASS, 2922 trades), phase B 1.540784 (PASS, 3024 trades), expected: both phases pass gate-1 (phase-stable outcome))
- [phase_means_average_to_published_mean]: PASS (observed: (1.539145 + 1.540784) / 2 = 1.539964, published recomputed 1.539964, expected: published mean equals the average of the two phase means)
- [sma175_plateau_gate_passes]: PASS (observed: 6/6 windows >= 0.9 (150, 175, 200, 226, 250, 277); candidate baseline window 175 passes: True, expected: >= 2 of 6 windows including the candidate baseline)
- [cost_model_unchanged]: PASS (observed: 1.0 bps commission + 2.0 bps slippage = 3.0 bps round-trip, expected: the committed published cost model is used unchanged)
- [data_unchanged]: PASS
- [config_unchanged]: PASS
- [committed_artifacts_unchanged]: PASS

## 10. Reproduction commands

```bash
python research/tsmomentum_sma175_validation_audit.py
python -m pytest -q tests/test_tsmomentum_sma175_validation_audit.py
python -m pytest -q
git status --porcelain data/ config/
git diff --stat src/ config/ research/run_cycle6.py research/experiments/ research/reports/
```

## 11. JSON payload

```json
{
  "baseline_design_sma200": {
    "decision": {
      "detail": "all evaluated gates pass (the SMA-plateau gate is not fold-dependent and is not re-evaluated)",
      "label": "Passes preliminary gates"
    },
    "gates": [
      {
        "gate": "wf_mean_oos_sharpe",
        "margin": 0.047307472024609165,
        "observed": 0.9473074720246092,
        "status": "PASS",
        "threshold": 0.9
      },
      {
        "gate": "positive_fold_rate",
        "margin": 0.41666666666666663,
        "observed": 0.9166666666666666,
        "status": "PASS",
        "threshold": 0.5
      },
      {
        "gate": "pooled_oos_trades",
        "margin": 5913.0,
        "observed": 6013,
        "status": "PASS",
        "threshold": 100
      }
    ],
    "independence": {
      "max_disjoint_test_windows": 24,
      "mean_consecutive_overlap_days": 175.0
    },
    "summary": {
      "max_test_sharpe": 3.9121052879675915,
      "mean_test_ann_return": 0.1471459015552229,
      "mean_test_max_dd": -0.05407695492453209,
      "mean_test_sharpe": 0.9473074720246092,
      "mean_test_trades": 125.27083333333333,
      "median_test_sharpe": 1.29329878363231,
      "min_test_sharpe": -21.829879416796786,
      "n_folds": 48,
      "pct_positive_sharpe": 0.9166666666666666,
      "std_test_sharpe": 3.4797702418403893,
      "total_test_trades": 6013
    }
  },
  "candidate": "tsmomentum_spytrend_001",
  "candidate_design_sma175": {
    "decision": {
      "detail": "all evaluated gates pass (the SMA-plateau gate is not fold-dependent and is not re-evaluated)",
      "label": "Passes preliminary gates"
    },
    "gates": [
      {
        "gate": "wf_mean_oos_sharpe",
        "margin": 0.6399642497903707,
        "observed": 1.5399642497903707,
        "status": "PASS",
        "threshold": 0.9
      },
      {
        "gate": "positive_fold_rate",
        "margin": 0.45833333333333337,
        "observed": 0.9583333333333334,
        "status": "PASS",
        "threshold": 0.5
      },
      {
        "gate": "pooled_oos_trades",
        "margin": 5846.0,
        "observed": 5946,
        "status": "PASS",
        "threshold": 100
      }
    ],
    "independence": {
      "max_disjoint_test_windows": 24,
      "mean_consecutive_overlap_days": 175.0
    },
    "summary": {
      "max_test_sharpe": 3.9121052879675915,
      "mean_test_ann_return": 0.15793403339737985,
      "mean_test_max_dd": -0.05149349120559104,
      "mean_test_sharpe": 1.5399642497903707,
      "mean_test_trades": 123.875,
      "median_test_sharpe": 1.3787016850990557,
      "min_test_sharpe": -0.08358271006476245,
      "n_folds": 48,
      "pct_positive_sharpe": 0.9583333333333334,
      "std_test_sharpe": 0.9805245918062045,
      "total_test_trades": 5946
    }
  },
  "checks": [
    {
      "expected": "non-empty cache-only panel capped at the published END_DATE",
      "name": "cache_only_path_built",
      "observed": "8482 sessions (8488 cached), 7 symbols, last 2026-10-09",
      "pass": true
    },
    {
      "expected": "exactly one published walk-forward record carrying the published anchor",
      "name": "published_record_resolved_by_content",
      "observed": "research/experiments/tsmomentum_regime_filter_wf_001.md",
      "pass": true
    },
    {
      "expected": "published aggregate statistics",
      "name": "reproduces_published_walk_forward_aggregate",
      "observed": "n_folds=48 (published 48); mean_test_sharpe=0.9473074720246092 (published 0.9473); std_test_sharpe=3.4797702418403893 (published 3.4798); median_test_sharpe=1.29329878363231 (published 1.2933); min_test_sharpe=-21.829879416796786 (published -21.8299); max_test_sharpe=3.9121052879675915 (published 3.9121); pct_positive_sharpe=0.9166666666666666 (published 91.7%); mean_test_ann_return=0.1471459015552229 (published 14.71%); mean_test_max_dd=-0.05407695492453209 (published -5.41%); mean_test_trades=125.27083333333333 (published 125.3); total_test_trades=6013 (published 6013)",
      "pass": true
    },
    {
      "expected": "every published fold reproduced",
      "name": "reproduces_published_walk_forward_fold_table",
      "observed": "48 folds compared",
      "pass": true
    },
    {
      "expected": "every published plateau row reproduced (sharpe/return/dd/sortino/profit-factor/trades)",
      "name": "reproduces_published_plateau_table",
      "observed": "150: sharpe 1.5504 vs published 1.5504, trades 1170 vs 1170; 175: sharpe 1.4933 vs published 1.4933, trades 1204 vs 1204; 200: sharpe 1.4178 vs published 1.4178, trades 1196 vs 1196; 226: sharpe 1.3178 vs published 1.3178, trades 1233 vs 1233; 250: sharpe 1.2781 vs published 1.2781, trades 1279 vs 1279; 277: sharpe 1.2270 vs published 1.2270, trades 1303 vs 1303",
      "pass": true
    },
    {
      "expected": "local path builder is bit-identical to the committed path builders",
      "name": "harness_matches_committed_path_builders",
      "observed": "SMA-200 max|diff| ret=0.0 weights=0.0; SMA-175 max|diff| ret=0.0 weights=0.0",
      "pass": true
    },
    {
      "expected": ">= 0.9",
      "name": "sma175_gate1_walkforward_mean_oos_sharpe",
      "observed": "1.539964 (margin +0.639964)",
      "pass": true
    },
    {
      "expected": ">= 0.5",
      "name": "sma175_gate2_positive_fold_rate",
      "observed": "0.958333 (margin +0.458333)",
      "pass": true
    },
    {
      "expected": "> 100",
      "name": "sma175_gate3_pooled_oos_trades",
      "observed": "5946 (margin +5846)",
      "pass": true
    },
    {
      "expected": "both phases pass gate-1 (phase-stable outcome)",
      "name": "sma175_phase_stable_gate1",
      "observed": "phase A 1.539145 (PASS, 2922 trades), phase B 1.540784 (PASS, 3024 trades)",
      "pass": true
    },
    {
      "expected": "published mean equals the average of the two phase means",
      "name": "phase_means_average_to_published_mean",
      "observed": "(1.539145 + 1.540784) / 2 = 1.539964, published recomputed 1.539964",
      "pass": true
    },
    {
      "expected": ">= 2 of 6 windows including the candidate baseline",
      "name": "sma175_plateau_gate_passes",
      "observed": "6/6 windows >= 0.9 (150, 175, 200, 226, 250, 277); candidate baseline window 175 passes: True",
      "pass": true
    },
    {
      "expected": "the committed published cost model is used unchanged",
      "name": "cost_model_unchanged",
      "observed": "1.0 bps commission + 2.0 bps slippage = 3.0 bps round-trip",
      "pass": true
    },
    {
      "expected": "",
      "name": "data_unchanged",
      "observed": "",
      "pass": true
    },
    {
      "expected": "",
      "name": "config_unchanged",
      "observed": "",
      "pass": true
    },
    {
      "expected": "",
      "name": "committed_artifacts_unchanged",
      "observed": "",
      "pass": true
    }
  ],
  "cost_model": {
    "commission_bps": 1.0,
    "note": "all reported metrics are net of the published round-trip cost",
    "published_commission_bps": 1.0,
    "published_slippage_bps": 2.0,
    "rf_annual": 0.02,
    "round_trip_bps": 3.0000000000000004,
    "slippage_bps": 2.0,
    "source": "config/settings.yaml via src.backtest.engine.get_cost_params (unchanged)"
  },
  "cost_sensitivity": [
    {
      "gate1": "PASS",
      "mean_test_sharpe": 1.6061904312558735,
      "pct_positive_sharpe": 0.9791666666666666,
      "round_trip_bps": 0.0,
      "total_test_trades": 5946
    },
    {
      "gate1": "PASS",
      "mean_test_sharpe": 1.5399642497903707,
      "pct_positive_sharpe": 0.9583333333333334,
      "round_trip_bps": 3.0,
      "total_test_trades": 5946
    },
    {
      "gate1": "PASS",
      "mean_test_sharpe": 1.473676495966101,
      "pct_positive_sharpe": 0.9583333333333334,
      "round_trip_bps": 6.0,
      "total_test_trades": 5946
    },
    {
      "gate1": "PASS",
      "mean_test_sharpe": 1.3852443287206844,
      "pct_positive_sharpe": 0.9583333333333334,
      "round_trip_bps": 10.0,
      "total_test_trades": 5946
    }
  ],
  "cycle": "914",
  "data": {
    "end_date": "2026-10-09",
    "end_date_cap_applied": true,
    "note": "the committed cache extends past the published protocol END_DATE; the panel is capped at END_DATE so the published data range (and the published plateau table) is reproduced exactly",
    "protocol_capped_last_date": "2026-10-09",
    "raw_cache_first_date": "1993-01-29",
    "raw_cache_last_date": "2026-10-19",
    "sessions_dropped_after_end_date": 6,
    "sessions_raw": 8488,
    "sessions_used": 8482,
    "source": "committed parquet cache in data/raw/ (fetcher never called)",
    "start_date": "1993-01-01",
    "symbols": [
      "SPY",
      "QQQ",
      "IWM",
      "TLT",
      "GLD",
      "EFA",
      "EEM"
    ]
  },
  "fold_comparison": [
    {
      "fold": 1,
      "sharpe_sma175": 2.824253035140459,
      "sharpe_sma200": 2.554957343861941,
      "test_end": "2003-09-16",
      "test_start": "2002-09-30",
      "trades_sma175": 99,
      "trades_sma200": 94
    },
    {
      "fold": 2,
      "sharpe_sma175": 2.583463106453757,
      "sharpe_sma200": 2.582051440567476,
      "test_end": "2004-03-10",
      "test_start": "2003-03-25",
      "trades_sma175": 216,
      "trades_sma200": 215
    },
    {
      "fold": 3,
      "sharpe_sma175": 0.6398909707019417,
      "sharpe_sma200": 0.30274767243282663,
      "test_end": "2004-09-02",
      "test_start": "2003-09-17",
      "trades_sma175": 206,
      "trades_sma200": 211
    },
    {
      "fold": 4,
      "sharpe_sma175": 1.7595109543539205,
      "sharpe_sma200": 1.2699867020172544,
      "test_end": "2005-02-25",
      "test_start": "2004-03-11",
      "trades_sma175": 147,
      "trades_sma200": 154
    },
    {
      "fold": 5,
      "sharpe_sma175": 2.085021508033203,
      "sharpe_sma200": 1.9493967137143615,
      "test_end": "2005-08-22",
      "test_start": "2004-09-03",
      "trades_sma175": 110,
      "trades_sma200": 146
    },
    {
      "fold": 6,
      "sharpe_sma175": 2.1029033783456907,
      "sharpe_sma200": 2.184895834814226,
      "test_end": "2006-02-14",
      "test_start": "2005-02-28",
      "trades_sma175": 110,
      "trades_sma200": 146
    },
    {
      "fold": 7,
      "sharpe_sma175": 2.9127080261079454,
      "sharpe_sma200": 2.3382234952228322,
      "test_end": "2006-08-09",
      "test_start": "2005-08-23",
      "trades_sma175": 152,
      "trades_sma200": 163
    },
    {
      "fold": 8,
      "sharpe_sma175": 2.5659720457066277,
      "sharpe_sma200": 1.8911657288561508,
      "test_end": "2007-02-01",
      "test_start": "2006-02-15",
      "trades_sma175": 196,
      "trades_sma200": 207
    },
    {
      "fold": 9,
      "sharpe_sma175": 1.4641969877813676,
      "sharpe_sma200": 1.3166108652473656,
      "test_end": "2007-07-27",
      "test_start": "2006-08-10",
      "trades_sma175": 229,
      "trades_sma200": 230
    },
    {
      "fold": 10,
      "sharpe_sma175": 2.526156497755748,
      "sharpe_sma200": 2.081502248810079,
      "test_end": "2008-01-21",
      "test_start": "2007-02-02",
      "trades_sma175": 186,
      "trades_sma200": 198
    },
    {
      "fold": 11,
      "sharpe_sma175": 3.631157760363165,
      "sharpe_sma200": 2.7409393118032823,
      "test_end": "2008-07-15",
      "test_start": "2007-07-30",
      "trades_sma175": 66,
      "trades_sma200": 78
    },
    {
      "fold": 12,
      "sharpe_sma175": 0.2790526045840107,
      "sharpe_sma200": -21.829879416796786,
      "test_end": "2009-01-07",
      "test_start": "2008-01-22",
      "trades_sma175": 2,
      "trades_sma200": 2
    },
    {
      "fold": 13,
      "sharpe_sma175": 0.355345266333087,
      "sharpe_sma200": -0.2665263717842321,
      "test_end": "2009-07-02",
      "test_start": "2008-07-16",
      "trades_sma175": 14,
      "trades_sma200": 8
    },
    {
      "fold": 14,
      "sharpe_sma175": 1.7316178641362698,
      "sharpe_sma200": 1.766952939611926,
      "test_end": "2009-12-25",
      "test_start": "2009-01-08",
      "trades_sma175": 136,
      "trades_sma200": 114
    },
    {
      "fold": 15,
      "sharpe_sma175": 1.0678441740809985,
      "sharpe_sma200": 1.524240869787849,
      "test_end": "2010-06-21",
      "test_start": "2009-07-03",
      "trades_sma175": 223,
      "trades_sma200": 212
    },
    {
      "fold": 16,
      "sharpe_sma175": 0.8092246892498306,
      "sharpe_sma200": 1.0670791750849684,
      "test_end": "2010-12-14",
      "test_start": "2009-12-28",
      "trades_sma175": 143,
      "trades_sma200": 150
    },
    {
      "fold": 17,
      "sharpe_sma175": 1.0966239700441356,
      "sharpe_sma200": 1.0959979317769908,
      "test_end": "2011-06-08",
      "test_start": "2010-06-22",
      "trades_sma175": 163,
      "trades_sma200": 164
    },
    {
      "fold": 18,
      "sharpe_sma175": 0.48558432919825706,
      "sharpe_sma200": 0.24257925704586458,
      "test_end": "2011-12-01",
      "test_start": "2010-12-15",
      "trades_sma175": 156,
      "trades_sma200": 162
    },
    {
      "fold": 19,
      "sharpe_sma175": 1.3834689525368111,
      "sharpe_sma200": 0.9429345486345174,
      "test_end": "2012-05-25",
      "test_start": "2011-06-09",
      "trades_sma175": 44,
      "trades_sma200": 50
    },
    {
      "fold": 20,
      "sharpe_sma175": 1.3436703909662417,
      "sharpe_sma200": 1.2266564177629347,
      "test_end": "2012-11-19",
      "test_start": "2011-12-02",
      "trades_sma175": 26,
      "trades_sma200": 24
    },
    {
      "fold": 21,
      "sharpe_sma175": 2.2547079473254508,
      "sharpe_sma200": 2.206317379155769,
      "test_end": "2013-05-14",
      "test_start": "2012-05-28",
      "trades_sma175": 133,
      "trades_sma200": 131
    },
    {
      "fold": 22,
      "sharpe_sma175": 2.1734324648501646,
      "sharpe_sma200": 2.1734324648501686,
      "test_end": "2013-11-06",
      "test_start": "2012-11-20",
      "trades_sma175": 238,
      "trades_sma200": 238
    },
    {
      "fold": 23,
      "sharpe_sma175": 0.8107437857854995,
      "sharpe_sma200": 0.8107437857855019,
      "test_end": "2014-05-01",
      "test_start": "2013-05-15",
      "trades_sma175": 236,
      "trades_sma200": 236
    },
    {
      "fold": 24,
      "sharpe_sma175": 0.48300709399401764,
      "sharpe_sma200": 0.4830070939940177,
      "test_end": "2014-10-24",
      "test_start": "2013-11-07",
      "trades_sma175": 184,
      "trades_sma200": 184
    },
    {
      "fold": 25,
      "sharpe_sma175": 1.1701768634693603,
      "sharpe_sma200": 1.1701768634693603,
      "test_end": "2015-04-20",
      "test_start": "2014-05-02",
      "trades_sma175": 102,
      "trades_sma200": 102
    },
    {
      "fold": 26,
      "sharpe_sma175": 1.0228516206881326,
      "sharpe_sma200": 0.8976428595555964,
      "test_end": "2015-10-13",
      "test_start": "2014-10-27",
      "trades_sma175": 43,
      "trades_sma200": 35
    },
    {
      "fold": 27,
      "sharpe_sma175": 0.47139728369432843,
      "sharpe_sma200": 0.2791575413387473,
      "test_end": "2016-04-06",
      "test_start": "2015-04-21",
      "trades_sma175": 28,
      "trades_sma200": 18
    },
    {
      "fold": 28,
      "sharpe_sma175": 1.3739344176613004,
      "sharpe_sma200": 1.345349582023667,
      "test_end": "2016-09-29",
      "test_start": "2015-10-14",
      "trades_sma175": 30,
      "trades_sma200": 28
    },
    {
      "fold": 29,
      "sharpe_sma175": 0.3672020215273593,
      "sharpe_sma200": 0.29685553055420993,
      "test_end": "2017-03-24",
      "test_start": "2016-04-07",
      "trades_sma175": 29,
      "trades_sma200": 29
    },
    {
      "fold": 30,
      "sharpe_sma175": 0.6986199746201786,
      "sharpe_sma200": 0.6331745793088774,
      "test_end": "2017-09-18",
      "test_start": "2016-09-30",
      "trades_sma175": 60,
      "trades_sma200": 60
    },
    {
      "fold": 31,
      "sharpe_sma175": 1.6763816768086506,
      "sharpe_sma200": 1.67638167680865,
      "test_end": "2018-03-13",
      "test_start": "2017-03-27",
      "trades_sma175": 75,
      "trades_sma200": 75
    },
    {
      "fold": 32,
      "sharpe_sma175": 1.3532836649589943,
      "sharpe_sma200": 1.137310395687428,
      "test_end": "2018-09-05",
      "test_start": "2017-09-19",
      "trades_sma175": 144,
      "trades_sma200": 148
    },
    {
      "fold": 33,
      "sharpe_sma175": 0.35497239259755986,
      "sharpe_sma200": 0.24718947185832646,
      "test_end": "2019-02-28",
      "test_start": "2018-03-14",
      "trades_sma175": 128,
      "trades_sma200": 130
    },
    {
      "fold": 34,
      "sharpe_sma175": 0.9473779856524394,
      "sharpe_sma200": 1.0883359067575717,
      "test_end": "2019-08-23",
      "test_start": "2018-09-06",
      "trades_sma175": 30,
      "trades_sma200": 28
    },
    {
      "fold": 35,
      "sharpe_sma175": 3.252075026352224,
      "sharpe_sma200": 3.252075026352224,
      "test_end": "2020-02-17",
      "test_start": "2019-03-01",
      "trades_sma175": 26,
      "trades_sma200": 26
    },
    {
      "fold": 36,
      "sharpe_sma175": 3.9121052879675915,
      "sharpe_sma200": 3.9121052879675915,
      "test_end": "2020-08-11",
      "test_start": "2019-08-26",
      "trades_sma175": 24,
      "trades_sma200": 24
    },
    {
      "fold": 37,
      "sharpe_sma175": 2.3629158330846907,
      "sharpe_sma200": 2.3629158330846916,
      "test_end": "2021-02-03",
      "test_start": "2020-02-18",
      "trades_sma175": 124,
      "trades_sma200": 124
    },
    {
      "fold": 38,
      "sharpe_sma175": 0.7952411969062841,
      "sharpe_sma200": 0.7952411969062717,
      "test_end": "2021-07-29",
      "test_start": "2020-08-12",
      "trades_sma175": 233,
      "trades_sma200": 233
    },
    {
      "fold": 39,
      "sharpe_sma175": -0.08358271006476245,
      "sharpe_sma200": -0.08358271006476463,
      "test_end": "2022-01-21",
      "test_start": "2021-02-04",
      "trades_sma175": 243,
      "trades_sma200": 243
    },
    {
      "fold": 40,
      "sharpe_sma175": -0.02058417578521229,
      "sharpe_sma200": -0.10732991321229177,
      "test_end": "2022-07-18",
      "test_start": "2021-07-30",
      "trades_sma175": 143,
      "trades_sma200": 148
    },
    {
      "fold": 41,
      "sharpe_sma175": 0.9691186126171883,
      "sharpe_sma200": 0.8946927114221876,
      "test_end": "2023-01-10",
      "test_start": "2022-01-24",
      "trades_sma175": 32,
      "trades_sma200": 29
    },
    {
      "fold": 42,
      "sharpe_sma175": 1.7176865578318712,
      "sharpe_sma200": 1.5583667409783086,
      "test_end": "2023-07-05",
      "test_start": "2022-07-19",
      "trades_sma175": 61,
      "trades_sma200": 32
    },
    {
      "fold": 43,
      "sharpe_sma175": 2.1371559267078553,
      "sharpe_sma200": 1.8332409273747643,
      "test_end": "2023-12-28",
      "test_start": "2023-01-11",
      "trades_sma175": 128,
      "trades_sma200": 118
    },
    {
      "fold": 44,
      "sharpe_sma175": 1.9209195735803848,
      "sharpe_sma200": 1.81856488947759,
      "test_end": "2024-06-21",
      "test_start": "2023-07-06",
      "trades_sma175": 175,
      "trades_sma200": 185
    },
    {
      "fold": 45,
      "sharpe_sma175": 1.8342182200072057,
      "sharpe_sma200": 1.8342182200072057,
      "test_end": "2024-12-16",
      "test_start": "2023-12-29",
      "trades_sma175": 220,
      "trades_sma200": 220
    },
    {
      "fold": 46,
      "sharpe_sma175": 1.0502365662266004,
      "sharpe_sma200": 1.1148099216076683,
      "test_end": "2025-06-10",
      "test_start": "2024-06-24",
      "trades_sma175": 183,
      "trades_sma200": 186
    },
    {
      "fold": 47,
      "sharpe_sma175": 1.901478795274787,
      "sharpe_sma200": 1.9609278869742752,
      "test_end": "2025-12-03",
      "test_start": "2024-12-17",
      "trades_sma175": 112,
      "trades_sma200": 115
    },
    {
      "fold": 48,
      "sharpe_sma175": 3.3635435737241766,
      "sharpe_sma200": 2.8969247986858013,
      "test_end": "2026-05-28",
      "test_start": "2025-06-11",
      "trades_sma175": 158,
      "trades_sma200": 160
    }
  ],
  "influence": {
    "sma175": {
      "both_thin_trade_folds_excluded_mean": 1.5667921571351866,
      "mean": 1.5399642497903707,
      "median": 1.3787016850990557,
      "most_influential_fold": {
        "fold": 36,
        "is_thin": false,
        "loo_mean": 1.4894931638717062,
        "shift": -0.05047108591866456,
        "test_sharpe": 3.9121052879675915,
        "test_trades": 24
      },
      "rows": [
        {
          "fold": 1,
          "is_thin": false,
          "loo_mean": 1.5126389564850493,
          "shift": -0.027325293305321408,
          "test_sharpe": 2.824253035140459,
          "test_trades": 99
        },
        {
          "fold": 2,
          "is_thin": false,
          "loo_mean": 1.5177621464571067,
          "shift": -0.022202103333264,
          "test_sharpe": 2.583463106453757,
          "test_trades": 216
        },
        {
          "fold": 3,
          "is_thin": false,
          "loo_mean": 1.5591147450901242,
          "shift": 0.019150495299753434,
          "test_sharpe": 0.6398909707019417,
          "test_trades": 206
        },
        {
          "fold": 4,
          "is_thin": false,
          "loo_mean": 1.5352930433102947,
          "shift": -0.004671206480076018,
          "test_sharpe": 1.7595109543539205,
          "test_trades": 147
        },
        {
          "fold": 5,
          "is_thin": false,
          "loo_mean": 1.5283672868490334,
          "shift": -0.011596962941337274,
          "test_sharpe": 2.085021508033203,
          "test_trades": 110
        },
        {
          "fold": 6,
          "is_thin": false,
          "loo_mean": 1.527986821523236,
          "shift": -0.011977428267134771,
          "test_sharpe": 2.1029033783456907,
          "test_trades": 110
        },
        {
          "fold": 7,
          "is_thin": false,
          "loo_mean": 1.5107569354006347,
          "shift": -0.029207314389736005,
          "test_sharpe": 2.9127080261079454,
          "test_trades": 152
        },
        {
          "fold": 8,
          "is_thin": false,
          "loo_mean": 1.5181342966857692,
          "shift": -0.021829953104601563,
          "test_sharpe": 2.5659720457066277,
          "test_trades": 196
        },
        {
          "fold": 9,
          "is_thin": false,
          "loo_mean": 1.5415763191948173,
          "shift": 0.001612069404446581,
          "test_sharpe": 1.4641969877813676,
          "test_trades": 229
        },
        {
          "fold": 10,
          "is_thin": false,
          "loo_mean": 1.518981436003873,
          "shift": -0.0209828137864978,
          "test_sharpe": 2.526156497755748,
          "test_trades": 186
        },
        {
          "fold": 11,
          "is_thin": false,
          "loo_mean": 1.495470770842013,
          "shift": -0.044493478948357756,
          "test_sharpe": 3.631157760363165,
          "test_trades": 66
        },
        {
          "fold": 12,
          "is_thin": true,
          "loo_mean": 1.5667921571351866,
          "shift": 0.026827907344815882,
          "test_sharpe": 0.2790526045840107,
          "test_trades": 2
        },
        {
          "fold": 13,
          "is_thin": false,
          "loo_mean": 1.5651689090128658,
          "shift": 0.02520465922249504,
          "test_sharpe": 0.355345266333087,
          "test_trades": 14
        },
        {
          "fold": 14,
          "is_thin": false,
          "loo_mean": 1.5358865133149258,
          "shift": -0.00407773647544496,
          "test_sharpe": 1.7316178641362698,
          "test_trades": 136
        },
        {
          "fold": 15,
          "is_thin": false,
          "loo_mean": 1.5500093577841867,
          "shift": 0.010045107993815972,
          "test_sharpe": 1.0678441740809985,
          "test_trades": 223
        },
        {
          "fold": 16,
          "is_thin": false,
          "loo_mean": 1.5555119000146371,
          "shift": 0.015547650224266407,
          "test_sharpe": 0.8092246892498306,
          "test_trades": 143
        },
        {
          "fold": 17,
          "is_thin": false,
          "loo_mean": 1.5493970216998647,
          "shift": 0.009432771909493987,
          "test_sharpe": 1.0966239700441356,
          "test_trades": 163
        },
        {
          "fold": 18,
          "is_thin": false,
          "loo_mean": 1.5623978651221178,
          "shift": 0.022433615331747037,
          "test_sharpe": 0.48558432919825706,
          "test_trades": 156
        },
        {
          "fold": 19,
          "is_thin": false,
          "loo_mean": 1.5432939369659782,
          "shift": 0.003329687175607443,
          "test_sharpe": 1.3834689525368111,
          "test_trades": 44
        },
        {
          "fold": 20,
          "is_thin": false,
          "loo_mean": 1.5441407148717348,
          "shift": 0.004176465081364045,
          "test_sharpe": 1.3436703909662417,
          "test_trades": 26
        },
        {
          "fold": 21,
          "is_thin": false,
          "loo_mean": 1.524756937076858,
          "shift": -0.01520731271351261,
          "test_sharpe": 2.2547079473254508,
          "test_trades": 133
        },
        {
          "fold": 22,
          "is_thin": false,
          "loo_mean": 1.5264862026614385,
          "shift": -0.013478047128932191,
          "test_sharpe": 2.1734324648501646,
          "test_trades": 238
        },
        {
          "fold": 23,
          "is_thin": false,
          "loo_mean": 1.5554795788117508,
          "shift": 0.015515329021380087,
          "test_sharpe": 0.8107437857854995,
          "test_trades": 236
        },
        {
          "fold": 24,
          "is_thin": false,
          "loo_mean": 1.562452699913697,
          "shift": 0.02248845012332623,
          "test_sharpe": 0.48300709399401764,
          "test_trades": 184
        },
        {
          "fold": 25,
          "is_thin": false,
          "loo_mean": 1.547832066520605,
          "shift": 0.007867816730234178,
          "test_sharpe": 1.1701768634693603,
          "test_trades": 102
        },
        {
          "fold": 26,
          "is_thin": false,
          "loo_mean": 1.5509666461542477,
          "shift": 0.01100239636387701,
          "test_sharpe": 1.0228516206881326,
          "test_trades": 43
        },
        {
          "fold": 27,
          "is_thin": false,
          "loo_mean": 1.5626997171541162,
          "shift": 0.022735467363745432,
          "test_sharpe": 0.47139728369432843,
          "test_trades": 28
        },
        {
          "fold": 28,
          "is_thin": false,
          "loo_mean": 1.543496799410138,
          "shift": 0.0035325496197673445,
          "test_sharpe": 1.3739344176613004,
          "test_trades": 30
        },
        {
          "fold": 29,
          "is_thin": false,
          "loo_mean": 1.5649166376257537,
          "shift": 0.024952387835383005,
          "test_sharpe": 0.3672020215273593,
          "test_trades": 29
        },
        {
          "fold": 30,
          "is_thin": false,
          "loo_mean": 1.5578651918152682,
          "shift": 0.017900942024897448,
          "test_sharpe": 0.6986199746201786,
          "test_trades": 60
        },
        {
          "fold": 31,
          "is_thin": false,
          "loo_mean": 1.537061751343173,
          "shift": -0.002902498447197699,
          "test_sharpe": 1.6763816768086506,
          "test_trades": 75
        },
        {
          "fold": 32,
          "is_thin": false,
          "loo_mean": 1.5439361771272082,
          "shift": 0.0039719273368374886,
          "test_sharpe": 1.3532836649589943,
          "test_trades": 144
        },
        {
          "fold": 33,
          "is_thin": false,
          "loo_mean": 1.5651768424966004,
          "shift": 0.025212592706229664,
          "test_sharpe": 0.35497239259755986,
          "test_trades": 128
        },
        {
          "fold": 34,
          "is_thin": false,
          "loo_mean": 1.5525724681762838,
          "shift": 0.012608218385913084,
          "test_sharpe": 0.9473779856524394,
          "test_trades": 30
        },
        {
          "fold": 35,
          "is_thin": false,
          "loo_mean": 1.503536360927352,
          "shift": -0.03642788886301873,
          "test_sharpe": 3.252075026352224,
          "test_trades": 26
        },
        {
          "fold": 36,
          "is_thin": false,
          "loo_mean": 1.4894931638717062,
          "shift": -0.05047108591866456,
          "test_sharpe": 3.9121052879675915,
          "test_trades": 24
        },
        {
          "fold": 37,
          "is_thin": false,
          "loo_mean": 1.5224546416351719,
          "shift": -0.017509608155198864,
          "test_sharpe": 2.3629158330846907,
          "test_trades": 124
        },
        {
          "fold": 38,
          "is_thin": false,
          "loo_mean": 1.5558094211283295,
          "shift": 0.01584517133795882,
          "test_sharpe": 0.7952411969062841,
          "test_trades": 233
        },
        {
          "fold": 39,
          "is_thin": false,
          "loo_mean": 1.5745078021277135,
          "shift": 0.03454355233734274,
          "test_sharpe": -0.08358271006476245,
          "test_trades": 243
        },
        {
          "fold": 40,
          "is_thin": false,
          "loo_mean": 1.57316740778134,
          "shift": 0.03320315799096929,
          "test_sharpe": -0.02058417578521229,
          "test_trades": 143
        },
        {
          "fold": 41,
          "is_thin": false,
          "loo_mean": 1.5521099016451188,
          "shift": 0.01214565185474803,
          "test_sharpe": 0.9691186126171883,
          "test_trades": 32
        },
        {
          "fold": 42,
          "is_thin": false,
          "loo_mean": 1.5361829240873597,
          "shift": -0.0037813257030110403,
          "test_sharpe": 1.7176865578318712,
          "test_trades": 61
        },
        {
          "fold": 43,
          "is_thin": false,
          "loo_mean": 1.5272580438985088,
          "shift": -0.012706205891861888,
          "test_sharpe": 2.1371559267078553,
          "test_trades": 128
        },
        {
          "fold": 44,
          "is_thin": false,
          "loo_mean": 1.531858817369306,
          "shift": -0.008105432421064762,
          "test_sharpe": 1.9209195735803848,
          "test_trades": 175
        },
        {
          "fold": 45,
          "is_thin": false,
          "loo_mean": 1.5337035270197994,
          "shift": -0.006260722770571325,
          "test_sharpe": 1.8342182200072057,
          "test_trades": 220
        },
        {
          "fold": 46,
          "is_thin": false,
          "loo_mean": 1.5503839877385357,
          "shift": 0.010419737948164975,
          "test_sharpe": 1.0502365662266004,
          "test_trades": 183
        },
        {
          "fold": 47,
          "is_thin": false,
          "loo_mean": 1.5322724509502765,
          "shift": -0.007691798840094188,
          "test_sharpe": 1.901478795274787,
          "test_trades": 112
        },
        {
          "fold": 48,
          "is_thin": false,
          "loo_mean": 1.5011646897066724,
          "shift": -0.03879956008369834,
          "test_sharpe": 3.3635435737241766,
          "test_trades": 158
        }
      ],
      "thin_trade_fold_details": [
        {
          "fold": 12,
          "loo_mean": 1.5667921571351866,
          "test_sharpe": 0.2790526045840107,
          "test_trades": 2
        }
      ],
      "thin_trade_folds": [
        12
      ],
      "trimmed_mean_drop_min_max": 1.5236904654790209
    },
    "sma200": {
      "both_thin_trade_folds_excluded_mean": 1.4688514009948321,
      "mean": 0.9473074720246092,
      "median": 1.29329878363231,
      "most_influential_fold": {
        "fold": 12,
        "is_thin": true,
        "loo_mean": 1.431928469659107,
        "shift": 0.48462099763449784,
        "test_sharpe": -21.829879416796786,
        "test_trades": 2
      },
      "rows": [
        {
          "fold": 1,
          "is_thin": false,
          "loo_mean": 0.9131021556025385,
          "shift": -0.0342053164220707,
          "test_sharpe": 2.554957343861941,
          "test_trades": 94
        },
        {
          "fold": 2,
          "is_thin": false,
          "loo_mean": 0.9125256854598676,
          "shift": -0.034781786564741624,
          "test_sharpe": 2.582051440567476,
          "test_trades": 215
        },
        {
          "fold": 3,
          "is_thin": false,
          "loo_mean": 0.9610215103137963,
          "shift": 0.013714038289187158,
          "test_sharpe": 0.30274767243282663,
          "test_trades": 211
        },
        {
          "fold": 4,
          "is_thin": false,
          "loo_mean": 0.9404419564928509,
          "shift": -0.006865515531758293,
          "test_sharpe": 1.2699867020172544,
          "test_trades": 154
        },
        {
          "fold": 5,
          "is_thin": false,
          "loo_mean": 0.9259864243290826,
          "shift": -0.021321047695526563,
          "test_sharpe": 1.9493967137143615,
          "test_trades": 146
        },
        {
          "fold": 6,
          "is_thin": false,
          "loo_mean": 0.9209758047312131,
          "shift": -0.026331667293396088,
          "test_sharpe": 2.184895834814226,
          "test_trades": 146
        },
        {
          "fold": 7,
          "is_thin": false,
          "loo_mean": 0.9177135140842214,
          "shift": -0.02959395794038777,
          "test_sharpe": 2.3382234952228322,
          "test_trades": 163
        },
        {
          "fold": 8,
          "is_thin": false,
          "loo_mean": 0.9272253814537255,
          "shift": -0.020082090570883726,
          "test_sharpe": 1.8911657288561508,
          "test_trades": 207
        },
        {
          "fold": 9,
          "is_thin": false,
          "loo_mean": 0.9394499530198698,
          "shift": -0.00785751900473941,
          "test_sharpe": 1.3166108652473656,
          "test_trades": 230
        },
        {
          "fold": 10,
          "is_thin": false,
          "loo_mean": 0.9231756682632163,
          "shift": -0.0241318037613929,
          "test_sharpe": 2.081502248810079,
          "test_trades": 198
        },
        {
          "fold": 11,
          "is_thin": false,
          "loo_mean": 0.9091450924548502,
          "shift": -0.038162379569758986,
          "test_sharpe": 2.7409393118032823,
          "test_trades": 78
        },
        {
          "fold": 12,
          "is_thin": true,
          "loo_mean": 1.431928469659107,
          "shift": 0.48462099763449784,
          "test_sharpe": -21.829879416796786,
          "test_trades": 2
        },
        {
          "fold": 13,
          "is_thin": true,
          "loo_mean": 0.9731337240205423,
          "shift": 0.025826251995933136,
          "test_sharpe": -0.2665263717842321,
          "test_trades": 8
        },
        {
          "fold": 14,
          "is_thin": false,
          "loo_mean": 0.9298682067567943,
          "shift": -0.01743926526781492,
          "test_sharpe": 1.766952939611926,
          "test_trades": 114
        },
        {
          "fold": 15,
          "is_thin": false,
          "loo_mean": 0.935032293348796,
          "shift": -0.012275178675813181,
          "test_sharpe": 1.524240869787849,
          "test_trades": 212
        },
        {
          "fold": 16,
          "is_thin": false,
          "loo_mean": 0.9447591379169423,
          "shift": -0.002548334107666861,
          "test_sharpe": 1.0670791750849684,
          "test_trades": 150
        },
        {
          "fold": 17,
          "is_thin": false,
          "loo_mean": 0.9441438452213673,
          "shift": -0.0031636268032418924,
          "test_sharpe": 1.0959979317769908,
          "test_trades": 164
        },
        {
          "fold": 18,
          "is_thin": false,
          "loo_mean": 0.9623016893645829,
          "shift": 0.014994217339973748,
          "test_sharpe": 0.24257925704586458,
          "test_trades": 162
        },
        {
          "fold": 19,
          "is_thin": false,
          "loo_mean": 0.9474005129478029,
          "shift": 9.304092319373236e-05,
          "test_sharpe": 0.9429345486345174,
          "test_trades": 50
        },
        {
          "fold": 20,
          "is_thin": false,
          "loo_mean": 0.9413638774344324,
          "shift": -0.005943594590176793,
          "test_sharpe": 1.2266564177629347,
          "test_trades": 24
        },
        {
          "fold": 21,
          "is_thin": false,
          "loo_mean": 0.9205200271920316,
          "shift": -0.026787444832577556,
          "test_sharpe": 2.206317379155769,
          "test_trades": 131
        },
        {
          "fold": 22,
          "is_thin": false,
          "loo_mean": 0.9212197062198103,
          "shift": -0.02608776580479888,
          "test_sharpe": 2.1734324648501686,
          "test_trades": 238
        },
        {
          "fold": 23,
          "is_thin": false,
          "loo_mean": 0.9502130823701226,
          "shift": 0.0029056103455133986,
          "test_sharpe": 0.8107437857855019,
          "test_trades": 236
        },
        {
          "fold": 24,
          "is_thin": false,
          "loo_mean": 0.957186203472069,
          "shift": 0.009878731447459765,
          "test_sharpe": 0.4830070939940177,
          "test_trades": 184
        },
        {
          "fold": 25,
          "is_thin": false,
          "loo_mean": 0.9425655700789766,
          "shift": -0.004741901945632621,
          "test_sharpe": 1.1701768634693603,
          "test_trades": 102
        },
        {
          "fold": 26,
          "is_thin": false,
          "loo_mean": 0.948364165906929,
          "shift": 0.0010566938823197702,
          "test_sharpe": 0.8976428595555964,
          "test_trades": 35
        },
        {
          "fold": 27,
          "is_thin": false,
          "loo_mean": 0.9615234279966491,
          "shift": 0.014215955972039951,
          "test_sharpe": 0.2791575413387473,
          "test_trades": 18
        },
        {
          "fold": 28,
          "is_thin": false,
          "loo_mean": 0.9388384909607999,
          "shift": -0.008468981063809333,
          "test_sharpe": 1.345349582023667,
          "test_trades": 28
        },
        {
          "fold": 29,
          "is_thin": false,
          "loo_mean": 0.961146875034618,
          "shift": 0.013839403010008855,
          "test_sharpe": 0.29685553055420993,
          "test_trades": 29
        },
        {
          "fold": 30,
          "is_thin": false,
          "loo_mean": 0.9539911505930293,
          "shift": 0.006683678568420115,
          "test_sharpe": 0.6331745793088774,
          "test_trades": 60
        },
        {
          "fold": 31,
          "is_thin": false,
          "loo_mean": 0.9317952549015448,
          "shift": -0.015512217123064387,
          "test_sharpe": 1.67638167680865,
          "test_trades": 75
        },
        {
          "fold": 32,
          "is_thin": false,
          "loo_mean": 0.9432648566275282,
          "shift": -0.004042615397080951,
          "test_sharpe": 1.137310395687428,
          "test_trades": 148
        },
        {
          "fold": 33,
          "is_thin": false,
          "loo_mean": 0.9622035996877217,
          "shift": 0.014896127663112546,
          "test_sharpe": 0.24718947185832646,
          "test_trades": 130
        },
        {
          "fold": 34,
          "is_thin": false,
          "loo_mean": 0.944306867030291,
          "shift": -0.003000604994318201,
          "test_sharpe": 1.0883359067575717,
          "test_trades": 28
        },
        {
          "fold": 35,
          "is_thin": false,
          "loo_mean": 0.898269864485724,
          "shift": -0.0490376075388852,
          "test_sharpe": 3.252075026352224,
          "test_trades": 26
        },
        {
          "fold": 36,
          "is_thin": false,
          "loo_mean": 0.8842266674300777,
          "shift": -0.06308080459453147,
          "test_sharpe": 3.9121052879675915,
          "test_trades": 24
        },
        {
          "fold": 37,
          "is_thin": false,
          "loo_mean": 0.9171881451935437,
          "shift": -0.03011932683106544,
          "test_sharpe": 2.3629158330846916,
          "test_trades": 124
        },
        {
          "fold": 38,
          "is_thin": false,
          "loo_mean": 0.9505429246867018,
          "shift": 0.003235452662092575,
          "test_sharpe": 0.7952411969062717,
          "test_trades": 233
        },
        {
          "fold": 39,
          "is_thin": false,
          "loo_mean": 0.9692413056860855,
          "shift": 0.021933833661476276,
          "test_sharpe": -0.08358271006476463,
          "test_trades": 243
        },
        {
          "fold": 40,
          "is_thin": false,
          "loo_mean": 0.9697465653275221,
          "shift": 0.022439093302912938,
          "test_sharpe": -0.10732991321229177,
          "test_trades": 148
        },
        {
          "fold": 41,
          "is_thin": false,
          "loo_mean": 0.9484269350161503,
          "shift": 0.001119462991541087,
          "test_sharpe": 0.8946927114221876,
          "test_trades": 29
        },
        {
          "fold": 42,
          "is_thin": false,
          "loo_mean": 0.9343062109830413,
          "shift": -0.013001261041567846,
          "test_sharpe": 1.5583667409783086,
          "test_trades": 32
        },
        {
          "fold": 43,
          "is_thin": false,
          "loo_mean": 0.9284578240384358,
          "shift": -0.01884964798617339,
          "test_sharpe": 1.8332409273747643,
          "test_trades": 118
        },
        {
          "fold": 44,
          "is_thin": false,
          "loo_mean": 0.9287700801639076,
          "shift": -0.01853739186070158,
          "test_sharpe": 1.81856488947759,
          "test_trades": 185
        },
        {
          "fold": 45,
          "is_thin": false,
          "loo_mean": 0.9284370305781711,
          "shift": -0.018870441446438124,
          "test_sharpe": 1.8342182200072057,
          "test_trades": 220
        },
        {
          "fold": 46,
          "is_thin": false,
          "loo_mean": 0.9437435901185869,
          "shift": -0.0035638819060223037,
          "test_sharpe": 1.1148099216076683,
          "test_trades": 186
        },
        {
          "fold": 47,
          "is_thin": false,
          "loo_mean": 0.9257410802171697,
          "shift": -0.021566391807439467,
          "test_sharpe": 1.9609278869742752,
          "test_trades": 115
        },
        {
          "fold": 48,
          "is_thin": false,
          "loo_mean": 0.9058262523084137,
          "shift": -0.04148121971619545,
          "test_sharpe": 2.8969247986858013,
          "test_trades": 160
        }
      ],
      "thin_trade_fold_details": [
        {
          "fold": 12,
          "loo_mean": 1.431928469659107,
          "test_sharpe": -21.829879416796786,
          "test_trades": 2
        },
        {
          "fold": 13,
          "loo_mean": 0.9731337240205423,
          "test_sharpe": -0.2665263717842321,
          "test_trades": 8
        }
      ],
      "thin_trade_folds": [
        12,
        13
      ],
      "trimmed_mean_drop_min_max": 1.3780115823045747
    }
  },
  "mutation": {
    "baseline_value": 200,
    "candidate_value": 175,
    "description": "change the SPY trend-filter SMA window from 200 to 175 days (all other candidate parameters unchanged)",
    "name": "spy_sma_175",
    "parameter": "SPY_SMA_WINDOW"
  },
  "overall": "PASS",
  "perturbation": [
    {
      "gate1": "PASS",
      "mean_test_sharpe": 1.5546723625503833,
      "pct_positive_sharpe": 0.9791666666666666,
      "phase_a_mean": 1.5631432992261762,
      "phase_b_mean": 1.5462014258745906,
      "phase_stable_gate1": true,
      "sma_window": 165,
      "total_test_trades": 5843
    },
    {
      "gate1": "PASS",
      "mean_test_sharpe": 1.5484050391992046,
      "pct_positive_sharpe": 0.9583333333333334,
      "phase_a_mean": 1.5530470258425797,
      "phase_b_mean": 1.543763052555829,
      "phase_stable_gate1": true,
      "sma_window": 170,
      "total_test_trades": 5890
    },
    {
      "gate1": "PASS",
      "mean_test_sharpe": 1.5399642497903707,
      "pct_positive_sharpe": 0.9583333333333334,
      "phase_a_mean": 1.5391446802629378,
      "phase_b_mean": 1.5407838193178032,
      "phase_stable_gate1": true,
      "sma_window": 175,
      "total_test_trades": 5946
    },
    {
      "gate1": "PASS",
      "mean_test_sharpe": 1.5122410696484418,
      "pct_positive_sharpe": 0.9375,
      "phase_a_mean": 1.5503979186136967,
      "phase_b_mean": 1.4740842206831875,
      "phase_stable_gate1": true,
      "sma_window": 180,
      "total_test_trades": 5957
    },
    {
      "gate1": "PASS",
      "mean_test_sharpe": 1.07462739731188,
      "pct_positive_sharpe": 0.9375,
      "phase_a_mean": 1.528877687240314,
      "phase_b_mean": 0.6203771073834461,
      "phase_stable_gate1": false,
      "sma_window": 185,
      "total_test_trades": 5961
    }
  ],
  "phases": {
    "phase_a_fold_numbers": [
      1,
      3,
      5,
      7,
      9,
      11,
      13,
      15,
      17,
      19,
      21,
      23,
      25,
      27,
      29,
      31,
      33,
      35,
      37,
      39,
      41,
      43,
      45,
      47
    ],
    "phase_b_fold_numbers": [
      2,
      4,
      6,
      8,
      10,
      12,
      14,
      16,
      18,
      20,
      22,
      24,
      26,
      28,
      30,
      32,
      34,
      36,
      38,
      40,
      42,
      44,
      46,
      48
    ],
    "sma175": {
      "gate1_outcome_changes_between_phases": false,
      "gate1_phase_a": "PASS",
      "gate1_phase_b": "PASS",
      "phase_a": {
        "decision": {
          "detail": "all evaluated gates pass (the SMA-plateau gate is not fold-dependent and is not re-evaluated)",
          "label": "Passes preliminary gates"
        },
        "gate_table": [
          {
            "gate": "wf_mean_oos_sharpe",
            "margin": 0.6391446802629378,
            "observed": 1.5391446802629378,
            "status": "PASS",
            "threshold": 0.9
          },
          {
            "gate": "positive_fold_rate",
            "margin": 0.45833333333333337,
            "observed": 0.9583333333333334,
            "status": "PASS",
            "threshold": 0.5
          },
          {
            "gate": "pooled_oos_trades",
            "margin": 2822.0,
            "observed": 2922,
            "status": "PASS",
            "threshold": 100
          }
        ],
        "independence": {
          "max_disjoint_test_windows": 24,
          "mean_consecutive_overlap_days": 0.0
        },
        "mean_test_sharpe": 1.5391446802629378,
        "median_test_sharpe": 1.4238329701590895,
        "n_folds": 24,
        "pct_positive_sharpe": 0.9583333333333334,
        "pooled_oos_trades": 2922
      },
      "phase_b": {
        "decision": {
          "detail": "all evaluated gates pass (the SMA-plateau gate is not fold-dependent and is not re-evaluated)",
          "label": "Passes preliminary gates"
        },
        "gate_table": [
          {
            "gate": "wf_mean_oos_sharpe",
            "margin": 0.6407838193178031,
            "observed": 1.5407838193178032,
            "status": "PASS",
            "threshold": 0.9
          },
          {
            "gate": "positive_fold_rate",
            "margin": 0.45833333333333337,
            "observed": 0.9583333333333334,
            "status": "PASS",
            "threshold": 0.5
          },
          {
            "gate": "pooled_oos_trades",
            "margin": 2924.0,
            "observed": 3024,
            "status": "PASS",
            "threshold": 100
          }
        ],
        "independence": {
          "max_disjoint_test_windows": 24,
          "mean_consecutive_overlap_days": 0.0
        },
        "mean_test_sharpe": 1.5407838193178032,
        "median_test_sharpe": 1.3636090413101474,
        "n_folds": 24,
        "pct_positive_sharpe": 0.9583333333333334,
        "pooled_oos_trades": 3024
      },
      "phase_mean_average": 1.5399642497903705,
      "phase_means_average_to_published_mean": true
    },
    "sma200": {
      "gate1_outcome_changes_between_phases": true,
      "gate1_phase_a": "PASS",
      "gate1_phase_b": "FAIL",
      "phase_a": {
        "decision": {
          "detail": "all evaluated gates pass (the SMA-plateau gate is not fold-dependent and is not re-evaluated)",
          "label": "Passes preliminary gates"
        },
        "gate_table": [
          {
            "gate": "wf_mean_oos_sharpe",
            "margin": 0.48503468853412024,
            "observed": 1.3850346885341203,
            "status": "PASS",
            "threshold": 0.9
          },
          {
            "gate": "positive_fold_rate",
            "margin": 0.41666666666666663,
            "observed": 0.9166666666666666,
            "status": "PASS",
            "threshold": 0.5
          },
          {
            "gate": "pooled_oos_trades",
            "margin": 2852.0,
            "observed": 2952,
            "status": "PASS",
            "threshold": 100
          }
        ],
        "independence": {
          "max_disjoint_test_windows": 24,
          "mean_consecutive_overlap_days": 0.0
        },
        "mean_test_sharpe": 1.3850346885341203,
        "median_test_sharpe": 1.4204258675176074,
        "n_folds": 24,
        "pct_positive_sharpe": 0.9166666666666666,
        "pooled_oos_trades": 2952
      },
      "phase_b": {
        "decision": {
          "detail": "gate(s) not met: wf_mean_oos_sharpe",
          "label": "Rejected/Failed"
        },
        "gate_table": [
          {
            "gate": "wf_mean_oos_sharpe",
            "margin": -0.3904197444849018,
            "observed": 0.5095802555150982,
            "status": "FAIL",
            "threshold": 0.9
          },
          {
            "gate": "positive_fold_rate",
            "margin": 0.41666666666666663,
            "observed": 0.9166666666666666,
            "status": "PASS",
            "threshold": 0.5
          },
          {
            "gate": "pooled_oos_trades",
            "margin": 2961.0,
            "observed": 3061,
            "status": "PASS",
            "threshold": 100
          }
        ],
        "independence": {
          "max_disjoint_test_windows": 24,
          "mean_consecutive_overlap_days": 0.0
        },
        "mean_test_sharpe": 0.5095802555150982,
        "median_test_sharpe": 1.2483215598900945,
        "n_folds": 24,
        "pct_positive_sharpe": 0.9166666666666666,
        "pooled_oos_trades": 3061
      },
      "phase_mean_average": 0.9473074720246093,
      "phase_means_average_to_published_mean": true
    }
  },
  "plateau": {
    "gate": {
      "n_pass": 6,
      "passing_windows": [
        150,
        175,
        200,
        226,
        250,
        277
      ],
      "rule": ">= 2 of 6 pre-specified windows reach Sharpe >= 0.9, and the candidate's own baseline window is one of them",
      "sma175": {
        "baseline_window": 175,
        "baseline_window_passes": true,
        "gate": "PASS"
      },
      "sma200": {
        "baseline_window": 200,
        "baseline_window_passes": true,
        "gate": "PASS"
      },
      "windows": [
        150,
        175,
        200,
        226,
        250,
        277
      ]
    },
    "published_period": "2017-12-31 -> 2026-10-09 (post-VAL_END test period)",
    "rows": [
      {
        "abs_diffs": {
          "test_ann_return": 1.7080992140455775e-05,
          "test_max_dd": 1.4462005627671748e-05,
          "test_profit_factor": 0.0014625626151534288,
          "test_sharpe": 2.172176260972769e-05,
          "test_sortino": 4.948136283577931e-05
        },
        "match": true,
        "published": {
          "sma_window": 150,
          "test_ann_return": 0.157,
          "test_max_dd": -0.0682,
          "test_profit_factor": 1.38,
          "test_sharpe": 1.5504,
          "test_sortino": 1.9052,
          "test_trades": 1170
        },
        "sma_window": 150,
        "test_ann_return": 0.15698291900785954,
        "test_max_dd": -0.06818553799437232,
        "test_profit_factor": 1.3785374373848465,
        "test_sharpe": 1.5504217217626097,
        "test_sortino": 1.9051505186371642,
        "test_trades": 1170
      },
      {
        "abs_diffs": {
          "test_ann_return": 1.6224133865538892e-05,
          "test_max_dd": 1.4462005628115837e-05,
          "test_profit_factor": 0.00484210012514219,
          "test_sharpe": 6.803603827210125e-06,
          "test_sortino": 2.352807114913702e-05
        },
        "match": true,
        "published": {
          "sma_window": 175,
          "test_ann_return": 0.1517,
          "test_max_dd": -0.0682,
          "test_profit_factor": 1.37,
          "test_sharpe": 1.4933,
          "test_sortino": 1.8386,
          "test_trades": 1204
        },
        "sma_window": 175,
        "test_ann_return": 0.15168377586613446,
        "test_max_dd": -0.06818553799437188,
        "test_profit_factor": 1.365157899874858,
        "test_sharpe": 1.4932931963961729,
        "test_sortino": 1.8386235280711491,
        "test_trades": 1204
      },
      {
        "abs_diffs": {
          "test_ann_return": 4.7984834857850434e-05,
          "test_max_dd": 3.990324215139007e-05,
          "test_profit_factor": 0.0028239071345723676,
          "test_sharpe": 4.80324459315451e-05,
          "test_sortino": 2.500530609039764e-05
        },
        "match": true,
        "published": {
          "sma_window": 200,
          "test_ann_return": 0.1446,
          "test_max_dd": -0.0779,
          "test_profit_factor": 1.35,
          "test_sharpe": 1.4178,
          "test_sortino": 1.7477,
          "test_trades": 1196
        },
        "sma_window": 200,
        "test_ann_return": 0.14464798483485786,
        "test_max_dd": -0.07793990324215139,
        "test_profit_factor": 1.3471760928654277,
        "test_sharpe": 1.4177519675540684,
        "test_sortino": 1.7476749946939096,
        "test_trades": 1196
      },
      {
        "abs_diffs": {
          "test_ann_return": 3.627447112788951e-05,
          "test_max_dd": 3.9903242151057006e-05,
          "test_profit_factor": 0.002658365090878023,
          "test_sharpe": 4.231391313580524e-05,
          "test_sortino": 1.3413147970098294e-05
        },
        "match": true,
        "published": {
          "sma_window": 226,
          "test_ann_return": 0.1359,
          "test_max_dd": -0.0779,
          "test_profit_factor": 1.32,
          "test_sharpe": 1.3178,
          "test_sortino": 1.6205,
          "test_trades": 1233
        },
        "sma_window": 226,
        "test_ann_return": 0.13593627447112788,
        "test_max_dd": -0.07793990324215105,
        "test_profit_factor": 1.322658365090878,
        "test_sharpe": 1.3178423139131359,
        "test_sortino": 1.6205134131479701,
        "test_trades": 1233
      },
      {
        "abs_diffs": {
          "test_ann_return": 3.9123676392055495e-05,
          "test_max_dd": 4.5565998217436676e-05,
          "test_profit_factor": 0.002365478170679225,
          "test_sharpe": 4.051146450345655e-05,
          "test_sortino": 1.3114179523432412e-05
        },
        "match": true,
        "published": {
          "sma_window": 250,
          "test_ann_return": 0.1324,
          "test_max_dd": -0.082,
          "test_profit_factor": 1.31,
          "test_sharpe": 1.2781,
          "test_sortino": 1.5826,
          "test_trades": 1279
        },
        "sma_window": 250,
        "test_ann_return": 0.13236087632360793,
        "test_max_dd": -0.08204556599821744,
        "test_profit_factor": 1.3123654781706793,
        "test_sharpe": 1.2780594885354966,
        "test_sortino": 1.5826131141795234,
        "test_trades": 1279
      },
      {
        "abs_diffs": {
          "test_ann_return": 1.6237477103719922e-06,
          "test_max_dd": 3.505145858674619e-05,
          "test_profit_factor": 0.00041413416133440073,
          "test_sharpe": 4.297349966986275e-05,
          "test_sortino": 1.2414926932935444e-05
        },
        "match": true,
        "published": {
          "sma_window": 277,
          "test_ann_return": 0.1282,
          "test_max_dd": -0.0876,
          "test_profit_factor": 1.3,
          "test_sharpe": 1.227,
          "test_sortino": 1.5266,
          "test_trades": 1303
        },
        "sma_window": 277,
        "test_ann_return": 0.12820162374771038,
        "test_max_dd": -0.08763505145858674,
        "test_profit_factor": 1.2995858658386656,
        "test_sharpe": 1.2269570265003302,
        "test_sortino": 1.526612414926933,
        "test_trades": 1303
      }
    ]
  },
  "point_in_time": "signals use only data available at formation (weights shifted one day), the SPY SMA is computed point-in-time, the overlay/cost model are applied on the same continuously computed path for every fold and phase, and the panel is capped at the published END_DATE",
  "published_anchor": {
    "matches": true,
    "per_fold_count": 48,
    "per_fold_match": true,
    "rows": [
      {
        "abs_diff": 0,
        "match": true,
        "metric": "n_folds",
        "observed": 48,
        "published": 48,
        "published_text": "48",
        "tolerance": 0
      },
      {
        "abs_diff": 7.4720246091564135e-06,
        "match": true,
        "metric": "mean_test_sharpe",
        "observed": 0.9473074720246092,
        "published": 0.9473,
        "published_text": "0.9473",
        "scaled_observed": 0.9473074720246092,
        "tolerance": 0.0001
      },
      {
        "abs_diff": 2.9758159610704382e-05,
        "match": true,
        "metric": "std_test_sharpe",
        "observed": 3.4797702418403893,
        "published": 3.4798,
        "published_text": "3.4798",
        "scaled_observed": 3.4797702418403893,
        "tolerance": 0.0001
      },
      {
        "abs_diff": 1.2163676899046294e-06,
        "match": true,
        "metric": "median_test_sharpe",
        "observed": 1.29329878363231,
        "published": 1.2933,
        "published_text": "1.2933",
        "scaled_observed": 1.29329878363231,
        "tolerance": 0.0001
      },
      {
        "abs_diff": 2.0583203212964918e-05,
        "match": true,
        "metric": "min_test_sharpe",
        "observed": -21.829879416796786,
        "published": -21.8299,
        "published_text": "-21.8299",
        "scaled_observed": -21.829879416796786,
        "tolerance": 0.0001
      },
      {
        "abs_diff": 5.287967591360854e-06,
        "match": true,
        "metric": "max_test_sharpe",
        "observed": 3.9121052879675915,
        "published": 3.9121,
        "published_text": "3.9121",
        "scaled_observed": 3.9121052879675915,
        "tolerance": 0.0001
      },
      {
        "abs_diff": 0.03333333333334565,
        "match": true,
        "metric": "pct_positive_sharpe",
        "observed": 0.9166666666666666,
        "published": 91.7,
        "published_text": "91.7%",
        "scaled_observed": 91.66666666666666,
        "tolerance": 0.05
      },
      {
        "abs_diff": 0.004590155522288697,
        "match": true,
        "metric": "mean_test_ann_return",
        "observed": 0.1471459015552229,
        "published": 14.71,
        "published_text": "14.71%",
        "scaled_observed": 14.71459015552229,
        "tolerance": 0.005
      },
      {
        "abs_diff": 0.0023045075467909015,
        "match": true,
        "metric": "mean_test_max_dd",
        "observed": -0.05407695492453209,
        "published": -5.41,
        "published_text": "-5.41%",
        "scaled_observed": -5.407695492453209,
        "tolerance": 0.005
      },
      {
        "abs_diff": 0.02916666666666856,
        "match": true,
        "metric": "mean_test_trades",
        "observed": 125.27083333333333,
        "published": 125.3,
        "published_text": "125.3",
        "scaled_observed": 125.27083333333333,
        "tolerance": 0.1
      },
      {
        "abs_diff": 0,
        "match": true,
        "metric": "total_test_trades",
        "observed": 6013,
        "published": 6013,
        "published_text": "6013",
        "tolerance": 0
      }
    ],
    "value": 0.9473
  },
  "published_record_path": "research/experiments/tsmomentum_regime_filter_wf_001.md",
  "read_only": {
    "committed_artifacts_unchanged": true,
    "config_unchanged": true,
    "data_unchanged": true
  },
  "verdict": {
    "baseline_phase_stable": false,
    "detail": "SMA-175 passes the published protocol on the published 48-fold design (gate-1 1.539964 >= 0.9, gate-2 0.9583 >= 0.5, gate-3 5946 > 100), is phase-stable (phase A 1.539145 / phase B 1.540784, both PASS) and passes the published SMA-plateau rule (6/6 windows, candidate baseline included). The incumbent SMA-200 is not phase-stable (phase B 0.509580 FAIL). Promotion is not performed by this tool: the parameter choice is in-sample, so a selection-aware holdout is required first. The SMA window was selected on the same 48 folds that are used to evaluate it (Cycle 913 scanned 175/170/180/150/190 on the published design and kept the first phase-stable window). The SMA-175 numbers are therefore in-sample with respect to the parameter choice: they are not independent evidence, and the selection itself (the number of windows tried) must be charged against the multiple-testing budget before promotion.",
    "label": "Credible candidate for further validation (not promoted)",
    "phase_stable": true,
    "plateau_ok": true,
    "promotion_performed": false,
    "protocol_gates_met": true,
    "selection_caveat": "The SMA window was selected on the same 48 folds that are used to evaluate it (Cycle 913 scanned 175/170/180/150/190 on the published design and kept the first phase-stable window). The SMA-175 numbers are therefore in-sample with respect to the parameter choice: they are not independent evidence, and the selection itself (the number of windows tried) must be charged against the multiple-testing budget before promotion."
  }
}
```
