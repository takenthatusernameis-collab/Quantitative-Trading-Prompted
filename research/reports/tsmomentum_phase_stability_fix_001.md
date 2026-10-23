# TSMomentum SPY-Trend Walk-Forward Mean Stability Audit (tsmomentum_phase_stability_fix_001, Cycle 913)

## Summary

- Candidate: `tsmomentum_spytrend_001` (the incumbent)
- Published walk-forward record (resolved by content): `research/experiments/tsmomentum_regime_filter_wf_001.md`
- Published WF mean OOS Sharpe: 0.9473 (gate >= 0.9, margin +0.0473)
- Gate-1 outcome under phase A (odd folds): **PASS**; under phase B (even folds): **FAIL** -- outcome changes between phases: **YES**
- Gate-1 outcome when thin-trade folds [12, 13] are excluded: **PASS** (mean 1.468851) -- outcome changes: **NO**
- Published PASS stability: **NOT STABLE**
- Read-only: `data/` and `config/` byte-identical before and after the run (**yes**); no committed artifact modified (**yes**).
- Data source: committed parquet cache in `data/raw/` only; the fetcher is never called.

## 1. Reproduction anchor (published design, re-derived from the committed cache)

The published 48-fold design is re-derived from the committed cache with the committed candidate definition and compared with the published record, resolved by content (the record that carries the published aggregate table and fold table).

| Design | Folds | WF mean OOS Sharpe | Median | Positive fold rate | Pooled OOS trades | Decision |
|---|---|---|---|---|---|---|
| Published (recomputed) | 48 | 0.9473 | 1.2933 | 0.9167 | 6013 | Passes preliminary gates |

## 2. Phase decomposition (odd folds vs even folds)

The generator steps the folds by 6 months over a 12-month test window, so consecutive test windows overlap and the published folds are the interleaving of two disjoint 24-fold sub-designs: phase A (folds 1, 3, 5, ...) and phase B (folds 2, 4, 6, ...). Both are evaluated on the same continuously computed point-in-time path; only the fold windows change.

| Phase | Folds | Fold numbers | WF mean OOS Sharpe | Median | Positive fold rate | Pooled OOS trades | Gate 1 (>= 0.9) | Gate 2 (>= 0.5) | Gate 3 (> 100) | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| Published design (all 48 folds) | 48 | 1..48 | 0.9473 | 1.2933 | 0.9167 | 6013 | PASS (+0.0473) | PASS (+0.4167) | PASS (+5913) | Passes preliminary gates |
| Phase A (odd folds) | 24 | 1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35, 37, 39, 41, 43, 45, 47 | 1.3850 | 1.4204 | 0.9167 | 2952 | PASS (+0.4850) | PASS (+0.4167) | PASS (+2852) | Passes preliminary gates |
| Phase B (even folds) | 24 | 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48 | 0.5096 | 1.2483 | 0.9167 | 3061 | FAIL (-0.3904) | PASS (+0.4167) | PASS (+2961) | Rejected/Failed |

- Phase A mean 1.385035 and phase B mean 0.509580 average to the published recomputed mean 0.947307: **YES**.
- Both phases have zero consecutive test-window overlap and disjoint count equal to fold count: **YES**.
- Published mean position: published 0.947307 = (1.385035 + 0.509580) / 2.

### 2.1 Phase A (odd folds, folds 1, 3, 5, ...) -- gate table

- wf_mean_oos_sharpe: threshold 0.9, observed 1.385035, margin 0.485035, status PASS
- positive_fold_rate: threshold 0.5, observed 0.916667, margin 0.416667, status PASS
- pooled_oos_trades: threshold 100, observed 2952, margin 2852.000000, status PASS

### 2.2 Phase B (even folds, folds 2, 4, 6, ...) -- gate table

- wf_mean_oos_sharpe: threshold 0.9, observed 0.509580, margin -0.390420, status FAIL
- positive_fold_rate: threshold 0.5, observed 0.916667, margin 0.416667, status PASS
- pooled_oos_trades: threshold 100, observed 3061, margin 2961.000000, status PASS

## 3. Fold leave-one-out influence table (published 48 folds)

| Fold | Test Sharpe | Test Trades | Leave-One-Out Mean | Shift in Published Mean | Notes |
|---|---|---|---|---|---|
| 1 | 2.5550 | 94 | 0.913102 | -0.034205 |  |
| 2 | 2.5821 | 215 | 0.912526 | -0.034782 |  |
| 3 | 0.3027 | 211 | 0.961022 | +0.013714 |  |
| 4 | 1.2700 | 154 | 0.940442 | -0.006866 |  |
| 5 | 1.9494 | 146 | 0.925986 | -0.021321 |  |
| 6 | 2.1849 | 146 | 0.920976 | -0.026332 |  |
| 7 | 2.3382 | 163 | 0.917714 | -0.029594 |  |
| 8 | 1.8912 | 207 | 0.927225 | -0.020082 |  |
| 9 | 1.3166 | 230 | 0.939450 | -0.007858 |  |
| 10 | 2.0815 | 198 | 0.923176 | -0.024132 |  |
| 11 | 2.7409 | 78 | 0.909145 | -0.038162 |  |
| 12 | -21.8299 | 2 | 1.431928 | +0.484621 | thin-trade fold (<= 10 trades), most influential fold |
| 13 | -0.2665 | 8 | 0.973134 | +0.025826 | thin-trade fold (<= 10 trades) |
| 14 | 1.7670 | 114 | 0.929868 | -0.017439 |  |
| 15 | 1.5242 | 212 | 0.935032 | -0.012275 |  |
| 16 | 1.0671 | 150 | 0.944759 | -0.002548 |  |
| 17 | 1.0960 | 164 | 0.944144 | -0.003164 |  |
| 18 | 0.2426 | 162 | 0.962302 | +0.014994 |  |
| 19 | 0.9429 | 50 | 0.947401 | +0.000093 |  |
| 20 | 1.2267 | 24 | 0.941364 | -0.005944 |  |
| 21 | 2.2063 | 131 | 0.920520 | -0.026787 |  |
| 22 | 2.1734 | 238 | 0.921220 | -0.026088 |  |
| 23 | 0.8107 | 236 | 0.950213 | +0.002906 |  |
| 24 | 0.4830 | 184 | 0.957186 | +0.009879 |  |
| 25 | 1.1702 | 102 | 0.942566 | -0.004742 |  |
| 26 | 0.8976 | 35 | 0.948364 | +0.001057 |  |
| 27 | 0.2792 | 18 | 0.961523 | +0.014216 |  |
| 28 | 1.3453 | 28 | 0.938838 | -0.008469 |  |
| 29 | 0.2969 | 29 | 0.961147 | +0.013839 |  |
| 30 | 0.6332 | 60 | 0.953991 | +0.006684 |  |
| 31 | 1.6764 | 75 | 0.931795 | -0.015512 |  |
| 32 | 1.1373 | 148 | 0.943265 | -0.004043 |  |
| 33 | 0.2472 | 130 | 0.962204 | +0.014896 |  |
| 34 | 1.0883 | 28 | 0.944307 | -0.003001 |  |
| 35 | 3.2521 | 26 | 0.898270 | -0.049038 |  |
| 36 | 3.9121 | 24 | 0.884227 | -0.063081 |  |
| 37 | 2.3629 | 124 | 0.917188 | -0.030119 |  |
| 38 | 0.7952 | 233 | 0.950543 | +0.003235 |  |
| 39 | -0.0836 | 243 | 0.969241 | +0.021934 |  |
| 40 | -0.1073 | 148 | 0.969747 | +0.022439 |  |
| 41 | 0.8947 | 29 | 0.948427 | +0.001119 |  |
| 42 | 1.5584 | 32 | 0.934306 | -0.013001 |  |
| 43 | 1.8332 | 118 | 0.928458 | -0.018850 |  |
| 44 | 1.8186 | 185 | 0.928770 | -0.018537 |  |
| 45 | 1.8342 | 220 | 0.928437 | -0.018870 |  |
| 46 | 1.1148 | 186 | 0.943744 | -0.003564 |  |
| 47 | 1.9609 | 115 | 0.925741 | -0.021566 |  |
| 48 | 2.8969 | 160 | 0.905826 | -0.041481 |  |

- Published mean: 0.947307; published median: 1.293299; trimmed mean (min and max fold removed): 1.378012.
- Most influential fold: fold 12 (test Sharpe -21.8299, leave-one-out mean 1.431928, shift +0.484621).
- Thin-trade folds (<= 10 trades): 12, 13; leave-one-out means: fold 12: 1.431928, fold 13: 0.973134.
- Both thin-trade folds excluded: mean 1.468851, gate-1 status PASS.

## 4. Stability verdict (explicit)

(i) Gate-1 outcome under phase A: **PASS**; under phase B: **FAIL** -- the outcome changes between phases: **YES**.
(ii) Excluding the thin-trade folds 12, 13: gate-1 outcome stays **PASS** -- the outcome changes: **NO**.
(iii) The published PASS is **NOT STABLE** against the two documented weaknesses: phase B alone fails gate 1 (0.5096 < 0.9), so the published margin of +0.0473 is not phase-stable; the thin-trade folds do not by themselves change the gate-1 outcome.

## 5. Smallest reversible tweaks tested

1. **spy_sma_175**: Change SPY SMA window from 200 to 175
   - Phase A: mean 1.539145, gate1 PASS, trades 2922
   - Phase B: mean 1.540784, gate1 PASS, trades 3024
   - Result: **PHASE-STABLE PASS**

**Minimal fix achieving phase-stable gate-1:** Change SPY SMA window from 200 to 175
- Both phases pass gate-1 with pooled trades > 100. No promotion performed.

## 6. Checks


- [published_record_resolved_by_content]: PASS (observed: research/experiments/tsmomentum_regime_filter_wf_001.md, expected: exactly one published walk-forward record carrying the published anchor)
- [cache_only_path_built]: PASS (observed: 8490 sessions, 7 symbols, expected: non-empty path)
- [reproduces_published_walk_forward_aggregate]: PASS (observed: n_folds=48 (published 48); mean_test_sharpe=0.9473074720246092 (published 0.9473); std_test_sharpe=3.4797702418403893 (published 3.4798); median_test_sharpe=1.29329878363231 (published 1.2933); min_test_sharpe=-21.829879416796786 (published -21.8299); max_test_sharpe=3.9121052879675915 (published 3.9121); pct_positive_sharpe=0.9166666666666666 (published 91.7%); mean_test_ann_return=0.1471459015552229 (published 14.71%); mean_test_max_dd=-0.05407695492453209 (published -5.41%); mean_test_trades=125.27083333333333 (published 125.3); total_test_trades=6013 (published 6013), expected: published aggregate statistics)
- [reproduces_published_walk_forward_fold_table]: PASS (observed: 48 folds compared, expected: every published fold reproduced)
- [phase_a_test_windows_pairwise_disjoint]: PASS (observed: overlap=0.0, disjoint=24, folds=24, expected: overlap == 0 and disjoint == folds)
- [phase_b_test_windows_pairwise_disjoint]: PASS (observed: overlap=0.0, disjoint=24, folds=24, expected: overlap == 0 and disjoint == folds)
- [phase_union_covers_published_fold_set]: PASS (observed: phase A 24 folds, phase B 24 folds, union 48, expected: all 48 published folds, no overlap between phases)
- [phase_means_average_to_published_mean]: PASS (observed: (1.385035 + 0.509580) / 2 = 0.947307, published recomputed 0.947307, expected: published mean equals the average of the two phase means)
- [data_unchanged]: PASS
- [config_unchanged]: PASS
- [committed_artifacts_unchanged]: PASS

## 6. Reproduction commands

```bash
python research/tsmomentum_phase_stability_fix_audit.py
python -m pytest -q tests/test_tsmomentum_phase_stability_fix_audit.py
python -m pytest -q
git status --porcelain data/
git diff --stat src/ config/ research/experiments/ research/reports/
```

## 7. JSON payload

```json
{
  "anchor": {
    "matches": true,
    "per_fold": [
      {
        "fold": 1,
        "match": true,
        "test_sharpe_abs_diff": 4.265613805909396e-05,
        "test_sharpe_observed": 2.554957343861941,
        "test_sharpe_published": 2.555,
        "trades_match": true,
        "train_sharpe_abs_diff": 3.654815586640048e-05,
        "window_match": true
      },
      {
        "fold": 2,
        "match": true,
        "test_sharpe_abs_diff": 4.855943252390915e-05,
        "test_sharpe_observed": 2.582051440567476,
        "test_sharpe_published": 2.5821,
        "trades_match": true,
        "train_sharpe_abs_diff": 2.40196570517881e-05,
        "window_match": true
      },
      {
        "fold": 3,
        "match": true,
        "test_sharpe_abs_diff": 4.767243282660649e-05,
        "test_sharpe_observed": 0.30274767243282663,
        "test_sharpe_published": 0.3027,
        "trades_match": true,
        "train_sharpe_abs_diff": 5.26622607366356e-06,
        "window_match": true
      },
      {
        "fold": 4,
        "match": true,
        "test_sharpe_abs_diff": 1.3297982745630321e-05,
        "test_sharpe_observed": 1.2699867020172544,
        "test_sharpe_published": 1.27,
        "trades_match": true,
        "train_sharpe_abs_diff": 2.967422661059871e-05,
        "window_match": true
      },
      {
        "fold": 5,
        "match": true,
        "test_sharpe_abs_diff": 3.286285638504083e-06,
        "test_sharpe_observed": 1.9493967137143615,
        "test_sharpe_published": 1.9494,
        "trades_match": true,
        "train_sharpe_abs_diff": 1.3621653088602415e-05,
        "window_match": true
      },
      {
        "fold": 6,
        "match": true,
        "test_sharpe_abs_diff": 4.165185774063218e-06,
        "test_sharpe_observed": 2.184895834814226,
        "test_sharpe_published": 2.1849,
        "trades_match": true,
        "train_sharpe_abs_diff": 4.6444374997678395e-05,
        "window_match": true
      },
      {
        "fold": 7,
        "match": true,
        "test_sharpe_abs_diff": 2.349522283218164e-05,
        "test_sharpe_observed": 2.3382234952228322,
        "test_sharpe_published": 2.3382,
        "trades_match": true,
        "train_sharpe_abs_diff": 1.919757549440071e-05,
        "window_match": true
      },
      {
        "fold": 8,
        "match": true,
        "test_sharpe_abs_diff": 3.427114384924046e-05,
        "test_sharpe_observed": 1.8911657288561508,
        "test_sharpe_published": 1.8912,
        "trades_match": true,
        "train_sharpe_abs_diff": 6.744475736120137e-06,
        "window_match": true
      },
      {
        "fold": 9,
        "match": true,
        "test_sharpe_abs_diff": 1.0865247365599018e-05,
        "test_sharpe_observed": 1.3166108652473656,
        "test_sharpe_published": 1.3166,
        "trades_match": true,
        "train_sharpe_abs_diff": 4.89517755242197e-05,
        "window_match": true
      },
      {
        "fold": 10,
        "match": true,
        "test_sharpe_abs_diff": 2.248810079041874e-06,
        "test_sharpe_observed": 2.081502248810079,
        "test_sharpe_published": 2.0815,
        "trades_match": true,
        "train_sharpe_abs_diff": 2.2609946152662985e-05,
        "window_match": true
      },
      {
        "fold": 11,
        "match": true,
        "test_sharpe_abs_diff": 3.9311803282426894e-05,
        "test_sharpe_observed": 2.7409393118032823,
        "test_sharpe_published": 2.7409,
        "trades_match": true,
        "train_sharpe_abs_diff": 3.360209133207448e-05,
        "window_match": true
      },
      {
        "fold": 12,
        "match": true,
        "test_sharpe_abs_diff": 2.0583203212964918e-05,
        "test_sharpe_observed": -21.829879416796786,
        "test_sharpe_published": -21.8299,
        "trades_match": true,
        "train_sharpe_abs_diff": 4.903022064794982e-05,
        "window_match": true
      },
      {
        "fold": 13,
        "match": true,
        "test_sharpe_abs_diff": 2.6371784232093187e-05,
        "test_sharpe_observed": -0.2665263717842321,
        "test_sharpe_published": -0.2665,
        "trades_match": true,
        "train_sharpe_abs_diff": 3.8448174114469325e-05,
        "window_match": true
      },
      {
        "fold": 14,
        "match": true,
        "test_sharpe_abs_diff": 4.706038807400503e-05,
        "test_sharpe_observed": 1.766952939611926,
        "test_sharpe_published": 1.767,
        "trades_match": true,
        "train_sharpe_abs_diff": 2.4347947024327965e-05,
        "window_match": true
      },
      {
        "fold": 15,
        "match": true,
        "test_sharpe_abs_diff": 4.0869787848896166e-05,
        "test_sharpe_observed": 1.524240869787849,
        "test_sharpe_published": 1.5242,
        "trades_match": true,
        "train_sharpe_abs_diff": 7.791550787894508e-06,
        "window_match": true
      },
      {
        "fold": 16,
        "match": true,
        "test_sharpe_abs_diff": 2.0824915031525393e-05,
        "test_sharpe_observed": 1.0670791750849684,
        "test_sharpe_published": 1.0671,
        "trades_match": true,
        "train_sharpe_abs_diff": 3.753466101819036e-05,
        "window_match": true
      },
      {
        "fold": 17,
        "match": true,
        "test_sharpe_abs_diff": 2.0682230092994303e-06,
        "test_sharpe_observed": 1.0959979317769908,
        "test_sharpe_published": 1.096,
        "trades_match": true,
        "train_sharpe_abs_diff": 1.9583608546813736e-05,
        "window_match": true
      },
      {
        "fold": 18,
        "match": true,
        "test_sharpe_abs_diff": 2.0742954135427594e-05,
        "test_sharpe_observed": 0.24257925704586458,
        "test_sharpe_published": 0.2426,
        "trades_match": true,
        "train_sharpe_abs_diff": 2.4960075628577272e-05,
        "window_match": true
      },
      {
        "fold": 19,
        "match": true,
        "test_sharpe_abs_diff": 3.454863451746171e-05,
        "test_sharpe_observed": 0.9429345486345174,
        "test_sharpe_published": 0.9429,
        "trades_match": true,
        "train_sharpe_abs_diff": 3.884979096313579e-05,
        "window_match": true
      },
      {
        "fold": 20,
        "match": true,
        "test_sharpe_abs_diff": 4.358223706524278e-05,
        "test_sharpe_observed": 1.2266564177629347,
        "test_sharpe_published": 1.2267,
        "trades_match": true,
        "train_sharpe_abs_diff": 3.631366849998763e-05,
        "window_match": true
      },
      {
        "fold": 21,
        "match": true,
        "test_sharpe_abs_diff": 1.7379155768715293e-05,
        "test_sharpe_observed": 2.206317379155769,
        "test_sharpe_published": 2.2063,
        "trades_match": true,
        "train_sharpe_abs_diff": 1.923840019912859e-05,
        "window_match": true
      },
      {
        "fold": 22,
        "match": true,
        "test_sharpe_abs_diff": 3.2464850168612e-05,
        "test_sharpe_observed": 2.1734324648501686,
        "test_sharpe_published": 2.1734,
        "trades_match": true,
        "train_sharpe_abs_diff": 3.200425335414536e-05,
        "window_match": true
      },
      {
        "fold": 23,
        "match": true,
        "test_sharpe_abs_diff": 4.378578550190415e-05,
        "test_sharpe_observed": 0.8107437857855019,
        "test_sharpe_published": 0.8107,
        "trades_match": true,
        "train_sharpe_abs_diff": 1.4377020108202743e-05,
        "window_match": true
      },
      {
        "fold": 24,
        "match": true,
        "test_sharpe_abs_diff": 7.093994017715044e-06,
        "test_sharpe_observed": 0.4830070939940177,
        "test_sharpe_published": 0.483,
        "trades_match": true,
        "train_sharpe_abs_diff": 4.0681489555716155e-05,
        "window_match": true
      },
      {
        "fold": 25,
        "match": true,
        "test_sharpe_abs_diff": 2.3136530639567e-05,
        "test_sharpe_observed": 1.1701768634693603,
        "test_sharpe_published": 1.1702,
        "trades_match": true,
        "train_sharpe_abs_diff": 5.846795064323729e-06,
        "window_match": true
      },
      {
        "fold": 26,
        "match": true,
        "test_sharpe_abs_diff": 4.285955559646393e-05,
        "test_sharpe_observed": 0.8976428595555964,
        "test_sharpe_published": 0.8976,
        "trades_match": true,
        "train_sharpe_abs_diff": 2.2060615848307208e-05,
        "window_match": true
      },
      {
        "fold": 27,
        "match": true,
        "test_sharpe_abs_diff": 4.2458661252686714e-05,
        "test_sharpe_observed": 0.2791575413387473,
        "test_sharpe_published": 0.2792,
        "trades_match": true,
        "train_sharpe_abs_diff": 4.403672672914638e-05,
        "window_match": true
      },
      {
        "fold": 28,
        "match": true,
        "test_sharpe_abs_diff": 4.958202366700526e-05,
        "test_sharpe_observed": 1.345349582023667,
        "test_sharpe_published": 1.3453,
        "trades_match": true,
        "train_sharpe_abs_diff": 1.8146540654573329e-06,
        "window_match": true
      },
      {
        "fold": 29,
        "match": true,
        "test_sharpe_abs_diff": 4.4469445790062956e-05,
        "test_sharpe_observed": 0.29685553055420993,
        "test_sharpe_published": 0.2969,
        "trades_match": true,
        "train_sharpe_abs_diff": 4.076585112011699e-05,
        "window_match": true
      },
      {
        "fold": 30,
        "match": true,
        "test_sharpe_abs_diff": 2.5420691122546302e-05,
        "test_sharpe_observed": 0.6331745793088774,
        "test_sharpe_published": 0.6332,
        "trades_match": true,
        "train_sharpe_abs_diff": 1.0690260003443086e-05,
        "window_match": true
      },
      {
        "fold": 31,
        "match": true,
        "test_sharpe_abs_diff": 1.8323191349978174e-05,
        "test_sharpe_observed": 1.67638167680865,
        "test_sharpe_published": 1.6764,
        "trades_match": true,
        "train_sharpe_abs_diff": 2.8662742043383815e-05,
        "window_match": true
      },
      {
        "fold": 32,
        "match": true,
        "test_sharpe_abs_diff": 1.0395687427999789e-05,
        "test_sharpe_observed": 1.137310395687428,
        "test_sharpe_published": 1.1373,
        "trades_match": true,
        "train_sharpe_abs_diff": 1.4356255559899722e-05,
        "window_match": true
      },
      {
        "fold": 33,
        "match": true,
        "test_sharpe_abs_diff": 1.0528141673543656e-05,
        "test_sharpe_observed": 0.24718947185832646,
        "test_sharpe_published": 0.2472,
        "trades_match": true,
        "train_sharpe_abs_diff": 4.631463911497491e-06,
        "window_match": true
      },
      {
        "fold": 34,
        "match": true,
        "test_sharpe_abs_diff": 3.590675757170203e-05,
        "test_sharpe_observed": 1.0883359067575717,
        "test_sharpe_published": 1.0883,
        "trades_match": true,
        "train_sharpe_abs_diff": 1.1902783058737043e-05,
        "window_match": true
      },
      {
        "fold": 35,
        "match": true,
        "test_sharpe_abs_diff": 2.497364777598321e-05,
        "test_sharpe_observed": 3.252075026352224,
        "test_sharpe_published": 3.2521,
        "trades_match": true,
        "train_sharpe_abs_diff": 3.9330351641941874e-05,
        "window_match": true
      },
      {
        "fold": 36,
        "match": true,
        "test_sharpe_abs_diff": 5.287967591360854e-06,
        "test_sharpe_observed": 3.9121052879675915,
        "test_sharpe_published": 3.9121,
        "trades_match": true,
        "train_sharpe_abs_diff": 3.750973617300257e-05,
        "window_match": true
      },
      {
        "fold": 37,
        "match": true,
        "test_sharpe_abs_diff": 1.5833084691774246e-05,
        "test_sharpe_observed": 2.3629158330846916,
        "test_sharpe_published": 2.3629,
        "trades_match": true,
        "train_sharpe_abs_diff": 3.525090697076294e-05,
        "window_match": true
      },
      {
        "fold": 38,
        "match": true,
        "test_sharpe_abs_diff": 4.1196906271689926e-05,
        "test_sharpe_observed": 0.7952411969062717,
        "test_sharpe_published": 0.7952,
        "trades_match": true,
        "train_sharpe_abs_diff": 2.9693297585620115e-05,
        "window_match": true
      },
      {
        "fold": 39,
        "match": true,
        "test_sharpe_abs_diff": 1.728993523536504e-05,
        "test_sharpe_observed": -0.08358271006476463,
        "test_sharpe_published": -0.0836,
        "trades_match": true,
        "train_sharpe_abs_diff": 2.0053134221154068e-05,
        "window_match": true
      },
      {
        "fold": 40,
        "match": true,
        "test_sharpe_abs_diff": 2.9913212291760027e-05,
        "test_sharpe_observed": -0.10732991321229177,
        "test_sharpe_published": -0.1073,
        "trades_match": true,
        "train_sharpe_abs_diff": 2.731150382140335e-05,
        "window_match": true
      },
      {
        "fold": 41,
        "match": true,
        "test_sharpe_abs_diff": 7.2885778124032186e-06,
        "test_sharpe_observed": 0.8946927114221876,
        "test_sharpe_published": 0.8947,
        "trades_match": true,
        "train_sharpe_abs_diff": 4.62741904827535e-05,
        "window_match": true
      },
      {
        "fold": 42,
        "match": true,
        "test_sharpe_abs_diff": 3.325902169137862e-05,
        "test_sharpe_observed": 1.5583667409783086,
        "test_sharpe_published": 1.5584,
        "trades_match": true,
        "train_sharpe_abs_diff": 7.563256721354605e-06,
        "window_match": true
      },
      {
        "fold": 43,
        "match": true,
        "test_sharpe_abs_diff": 4.0927374764354596e-05,
        "test_sharpe_observed": 1.8332409273747643,
        "test_sharpe_published": 1.8332,
        "trades_match": true,
        "train_sharpe_abs_diff": 4.841849358094841e-05,
        "window_match": true
      },
      {
        "fold": 44,
        "match": true,
        "test_sharpe_abs_diff": 3.511052240989798e-05,
        "test_sharpe_observed": 1.81856488947759,
        "test_sharpe_published": 1.8186,
        "trades_match": true,
        "train_sharpe_abs_diff": 9.399009421207083e-06,
        "window_match": true
      },
      {
        "fold": 45,
        "match": true,
        "test_sharpe_abs_diff": 1.822000720563821e-05,
        "test_sharpe_observed": 1.8342182200072057,
        "test_sharpe_published": 1.8342,
        "trades_match": true,
        "train_sharpe_abs_diff": 2.124158369398721e-05,
        "window_match": true
      },
      {
        "fold": 46,
        "match": true,
        "test_sharpe_abs_diff": 9.921607668328392e-06,
        "test_sharpe_observed": 1.1148099216076683,
        "test_sharpe_published": 1.1148,
        "trades_match": true,
        "train_sharpe_abs_diff": 4.8775120640165426e-05,
        "window_match": true
      },
      {
        "fold": 47,
        "match": true,
        "test_sharpe_abs_diff": 2.7886974275137533e-05,
        "test_sharpe_observed": 1.9609278869742752,
        "test_sharpe_published": 1.9609,
        "trades_match": true,
        "train_sharpe_abs_diff": 2.1608851996646194e-06,
        "window_match": true
      },
      {
        "fold": 48,
        "match": true,
        "test_sharpe_abs_diff": 2.4798685801297182e-05,
        "test_sharpe_observed": 2.8969247986858013,
        "test_sharpe_published": 2.8969,
        "trades_match": true,
        "train_sharpe_abs_diff": 4.304235060703654e-05,
        "window_match": true
      }
    ],
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
    ]
  },
  "candidate": "tsmomentum_spytrend_001",
  "checks": [
    {
      "expected": "exactly one published walk-forward record carrying the published anchor",
      "name": "published_record_resolved_by_content",
      "observed": "research/experiments/tsmomentum_regime_filter_wf_001.md",
      "pass": true
    },
    {
      "expected": "non-empty path",
      "name": "cache_only_path_built",
      "observed": "8490 sessions, 7 symbols",
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
      "expected": "overlap == 0 and disjoint == folds",
      "name": "phase_a_test_windows_pairwise_disjoint",
      "observed": "overlap=0.0, disjoint=24, folds=24",
      "pass": true
    },
    {
      "expected": "overlap == 0 and disjoint == folds",
      "name": "phase_b_test_windows_pairwise_disjoint",
      "observed": "overlap=0.0, disjoint=24, folds=24",
      "pass": true
    },
    {
      "expected": "all 48 published folds, no overlap between phases",
      "name": "phase_union_covers_published_fold_set",
      "observed": "phase A 24 folds, phase B 24 folds, union 48",
      "pass": true
    },
    {
      "expected": "published mean equals the average of the two phase means",
      "name": "phase_means_average_to_published_mean",
      "observed": "(1.385035 + 0.509580) / 2 = 0.947307, published recomputed 0.947307",
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
  "commission_bps": 1.0,
  "cycle": "913",
  "data_source": "committed parquet cache in data/raw/ (fetcher never called)",
  "fold_influence": {
    "both_thin_trade_folds_excluded_mean": 1.4688514009948321,
    "gate1_outcome_changes_when_thin_trade_folds_excluded": false,
    "gate1_when_thin_trade_folds_excluded": "PASS",
    "influence": [
      {
        "abs_shift": 0.0342053164220707,
        "fold": 1,
        "is_thin": false,
        "loo_mean": 0.9131021556025385,
        "shift": -0.0342053164220707,
        "test_sharpe": 2.554957343861941,
        "test_trades": 94
      },
      {
        "abs_shift": 0.034781786564741624,
        "fold": 2,
        "is_thin": false,
        "loo_mean": 0.9125256854598676,
        "shift": -0.034781786564741624,
        "test_sharpe": 2.582051440567476,
        "test_trades": 215
      },
      {
        "abs_shift": 0.013714038289187158,
        "fold": 3,
        "is_thin": false,
        "loo_mean": 0.9610215103137963,
        "shift": 0.013714038289187158,
        "test_sharpe": 0.30274767243282663,
        "test_trades": 211
      },
      {
        "abs_shift": 0.006865515531758293,
        "fold": 4,
        "is_thin": false,
        "loo_mean": 0.9404419564928509,
        "shift": -0.006865515531758293,
        "test_sharpe": 1.2699867020172544,
        "test_trades": 154
      },
      {
        "abs_shift": 0.021321047695526563,
        "fold": 5,
        "is_thin": false,
        "loo_mean": 0.9259864243290826,
        "shift": -0.021321047695526563,
        "test_sharpe": 1.9493967137143615,
        "test_trades": 146
      },
      {
        "abs_shift": 0.026331667293396088,
        "fold": 6,
        "is_thin": false,
        "loo_mean": 0.9209758047312131,
        "shift": -0.026331667293396088,
        "test_sharpe": 2.184895834814226,
        "test_trades": 146
      },
      {
        "abs_shift": 0.02959395794038777,
        "fold": 7,
        "is_thin": false,
        "loo_mean": 0.9177135140842214,
        "shift": -0.02959395794038777,
        "test_sharpe": 2.3382234952228322,
        "test_trades": 163
      },
      {
        "abs_shift": 0.020082090570883726,
        "fold": 8,
        "is_thin": false,
        "loo_mean": 0.9272253814537255,
        "shift": -0.020082090570883726,
        "test_sharpe": 1.8911657288561508,
        "test_trades": 207
      },
      {
        "abs_shift": 0.00785751900473941,
        "fold": 9,
        "is_thin": false,
        "loo_mean": 0.9394499530198698,
        "shift": -0.00785751900473941,
        "test_sharpe": 1.3166108652473656,
        "test_trades": 230
      },
      {
        "abs_shift": 0.0241318037613929,
        "fold": 10,
        "is_thin": false,
        "loo_mean": 0.9231756682632163,
        "shift": -0.0241318037613929,
        "test_sharpe": 2.081502248810079,
        "test_trades": 198
      },
      {
        "abs_shift": 0.038162379569758986,
        "fold": 11,
        "is_thin": false,
        "loo_mean": 0.9091450924548502,
        "shift": -0.038162379569758986,
        "test_sharpe": 2.7409393118032823,
        "test_trades": 78
      },
      {
        "abs_shift": 0.48462099763449784,
        "fold": 12,
        "is_thin": true,
        "loo_mean": 1.431928469659107,
        "shift": 0.48462099763449784,
        "test_sharpe": -21.829879416796786,
        "test_trades": 2
      },
      {
        "abs_shift": 0.025826251995933136,
        "fold": 13,
        "is_thin": true,
        "loo_mean": 0.9731337240205423,
        "shift": 0.025826251995933136,
        "test_sharpe": -0.2665263717842321,
        "test_trades": 8
      },
      {
        "abs_shift": 0.01743926526781492,
        "fold": 14,
        "is_thin": false,
        "loo_mean": 0.9298682067567943,
        "shift": -0.01743926526781492,
        "test_sharpe": 1.766952939611926,
        "test_trades": 114
      },
      {
        "abs_shift": 0.012275178675813181,
        "fold": 15,
        "is_thin": false,
        "loo_mean": 0.935032293348796,
        "shift": -0.012275178675813181,
        "test_sharpe": 1.524240869787849,
        "test_trades": 212
      },
      {
        "abs_shift": 0.002548334107666861,
        "fold": 16,
        "is_thin": false,
        "loo_mean": 0.9447591379169423,
        "shift": -0.002548334107666861,
        "test_sharpe": 1.0670791750849684,
        "test_trades": 150
      },
      {
        "abs_shift": 0.0031636268032418924,
        "fold": 17,
        "is_thin": false,
        "loo_mean": 0.9441438452213673,
        "shift": -0.0031636268032418924,
        "test_sharpe": 1.0959979317769908,
        "test_trades": 164
      },
      {
        "abs_shift": 0.014994217339973748,
        "fold": 18,
        "is_thin": false,
        "loo_mean": 0.9623016893645829,
        "shift": 0.014994217339973748,
        "test_sharpe": 0.24257925704586458,
        "test_trades": 162
      },
      {
        "abs_shift": 9.304092319373236e-05,
        "fold": 19,
        "is_thin": false,
        "loo_mean": 0.9474005129478029,
        "shift": 9.304092319373236e-05,
        "test_sharpe": 0.9429345486345174,
        "test_trades": 50
      },
      {
        "abs_shift": 0.005943594590176793,
        "fold": 20,
        "is_thin": false,
        "loo_mean": 0.9413638774344324,
        "shift": -0.005943594590176793,
        "test_sharpe": 1.2266564177629347,
        "test_trades": 24
      },
      {
        "abs_shift": 0.026787444832577556,
        "fold": 21,
        "is_thin": false,
        "loo_mean": 0.9205200271920316,
        "shift": -0.026787444832577556,
        "test_sharpe": 2.206317379155769,
        "test_trades": 131
      },
      {
        "abs_shift": 0.02608776580479888,
        "fold": 22,
        "is_thin": false,
        "loo_mean": 0.9212197062198103,
        "shift": -0.02608776580479888,
        "test_sharpe": 2.1734324648501686,
        "test_trades": 238
      },
      {
        "abs_shift": 0.0029056103455133986,
        "fold": 23,
        "is_thin": false,
        "loo_mean": 0.9502130823701226,
        "shift": 0.0029056103455133986,
        "test_sharpe": 0.8107437857855019,
        "test_trades": 236
      },
      {
        "abs_shift": 0.009878731447459765,
        "fold": 24,
        "is_thin": false,
        "loo_mean": 0.957186203472069,
        "shift": 0.009878731447459765,
        "test_sharpe": 0.4830070939940177,
        "test_trades": 184
      },
      {
        "abs_shift": 0.004741901945632621,
        "fold": 25,
        "is_thin": false,
        "loo_mean": 0.9425655700789766,
        "shift": -0.004741901945632621,
        "test_sharpe": 1.1701768634693603,
        "test_trades": 102
      },
      {
        "abs_shift": 0.0010566938823197702,
        "fold": 26,
        "is_thin": false,
        "loo_mean": 0.948364165906929,
        "shift": 0.0010566938823197702,
        "test_sharpe": 0.8976428595555964,
        "test_trades": 35
      },
      {
        "abs_shift": 0.014215955972039951,
        "fold": 27,
        "is_thin": false,
        "loo_mean": 0.9615234279966491,
        "shift": 0.014215955972039951,
        "test_sharpe": 0.2791575413387473,
        "test_trades": 18
      },
      {
        "abs_shift": 0.008468981063809333,
        "fold": 28,
        "is_thin": false,
        "loo_mean": 0.9388384909607999,
        "shift": -0.008468981063809333,
        "test_sharpe": 1.345349582023667,
        "test_trades": 28
      },
      {
        "abs_shift": 0.013839403010008855,
        "fold": 29,
        "is_thin": false,
        "loo_mean": 0.961146875034618,
        "shift": 0.013839403010008855,
        "test_sharpe": 0.29685553055420993,
        "test_trades": 29
      },
      {
        "abs_shift": 0.006683678568420115,
        "fold": 30,
        "is_thin": false,
        "loo_mean": 0.9539911505930293,
        "shift": 0.006683678568420115,
        "test_sharpe": 0.6331745793088774,
        "test_trades": 60
      },
      {
        "abs_shift": 0.015512217123064387,
        "fold": 31,
        "is_thin": false,
        "loo_mean": 0.9317952549015448,
        "shift": -0.015512217123064387,
        "test_sharpe": 1.67638167680865,
        "test_trades": 75
      },
      {
        "abs_shift": 0.004042615397080951,
        "fold": 32,
        "is_thin": false,
        "loo_mean": 0.9432648566275282,
        "shift": -0.004042615397080951,
        "test_sharpe": 1.137310395687428,
        "test_trades": 148
      },
      {
        "abs_shift": 0.014896127663112546,
        "fold": 33,
        "is_thin": false,
        "loo_mean": 0.9622035996877217,
        "shift": 0.014896127663112546,
        "test_sharpe": 0.24718947185832646,
        "test_trades": 130
      },
      {
        "abs_shift": 0.003000604994318201,
        "fold": 34,
        "is_thin": false,
        "loo_mean": 0.944306867030291,
        "shift": -0.003000604994318201,
        "test_sharpe": 1.0883359067575717,
        "test_trades": 28
      },
      {
        "abs_shift": 0.0490376075388852,
        "fold": 35,
        "is_thin": false,
        "loo_mean": 0.898269864485724,
        "shift": -0.0490376075388852,
        "test_sharpe": 3.252075026352224,
        "test_trades": 26
      },
      {
        "abs_shift": 0.06308080459453147,
        "fold": 36,
        "is_thin": false,
        "loo_mean": 0.8842266674300777,
        "shift": -0.06308080459453147,
        "test_sharpe": 3.9121052879675915,
        "test_trades": 24
      },
      {
        "abs_shift": 0.03011932683106544,
        "fold": 37,
        "is_thin": false,
        "loo_mean": 0.9171881451935437,
        "shift": -0.03011932683106544,
        "test_sharpe": 2.3629158330846916,
        "test_trades": 124
      },
      {
        "abs_shift": 0.003235452662092575,
        "fold": 38,
        "is_thin": false,
        "loo_mean": 0.9505429246867018,
        "shift": 0.003235452662092575,
        "test_sharpe": 0.7952411969062717,
        "test_trades": 233
      },
      {
        "abs_shift": 0.021933833661476276,
        "fold": 39,
        "is_thin": false,
        "loo_mean": 0.9692413056860855,
        "shift": 0.021933833661476276,
        "test_sharpe": -0.08358271006476463,
        "test_trades": 243
      },
      {
        "abs_shift": 0.022439093302912938,
        "fold": 40,
        "is_thin": false,
        "loo_mean": 0.9697465653275221,
        "shift": 0.022439093302912938,
        "test_sharpe": -0.10732991321229177,
        "test_trades": 148
      },
      {
        "abs_shift": 0.001119462991541087,
        "fold": 41,
        "is_thin": false,
        "loo_mean": 0.9484269350161503,
        "shift": 0.001119462991541087,
        "test_sharpe": 0.8946927114221876,
        "test_trades": 29
      },
      {
        "abs_shift": 0.013001261041567846,
        "fold": 42,
        "is_thin": false,
        "loo_mean": 0.9343062109830413,
        "shift": -0.013001261041567846,
        "test_sharpe": 1.5583667409783086,
        "test_trades": 32
      },
      {
        "abs_shift": 0.01884964798617339,
        "fold": 43,
        "is_thin": false,
        "loo_mean": 0.9284578240384358,
        "shift": -0.01884964798617339,
        "test_sharpe": 1.8332409273747643,
        "test_trades": 118
      },
      {
        "abs_shift": 0.01853739186070158,
        "fold": 44,
        "is_thin": false,
        "loo_mean": 0.9287700801639076,
        "shift": -0.01853739186070158,
        "test_sharpe": 1.81856488947759,
        "test_trades": 185
      },
      {
        "abs_shift": 0.018870441446438124,
        "fold": 45,
        "is_thin": false,
        "loo_mean": 0.9284370305781711,
        "shift": -0.018870441446438124,
        "test_sharpe": 1.8342182200072057,
        "test_trades": 220
      },
      {
        "abs_shift": 0.0035638819060223037,
        "fold": 46,
        "is_thin": false,
        "loo_mean": 0.9437435901185869,
        "shift": -0.0035638819060223037,
        "test_sharpe": 1.1148099216076683,
        "test_trades": 186
      },
      {
        "abs_shift": 0.021566391807439467,
        "fold": 47,
        "is_thin": false,
        "loo_mean": 0.9257410802171697,
        "shift": -0.021566391807439467,
        "test_sharpe": 1.9609278869742752,
        "test_trades": 115
      },
      {
        "abs_shift": 0.04148121971619545,
        "fold": 48,
        "is_thin": false,
        "loo_mean": 0.9058262523084137,
        "shift": -0.04148121971619545,
        "test_sharpe": 2.8969247986858013,
        "test_trades": 160
      }
    ],
    "loo_mean_thin_trade_folds": {
      "12": 1.431928469659107,
      "13": 0.9731337240205423
    },
    "most_influential_fold": {
      "abs_shift": 0.48462099763449784,
      "fold": 12,
      "is_thin": true,
      "loo_mean": 1.431928469659107,
      "shift": 0.48462099763449784,
      "test_sharpe": -21.829879416796786,
      "test_trades": 2
    },
    "published_mean": 0.9473074720246092,
    "published_median": 1.29329878363231,
    "thin_trade_folds": [
      12,
      13
    ],
    "trimmed_mean_drop_min_max": 1.3780115823045747
  },
  "overall": "PASS",
  "phase_decomposition": {
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
    "phase_means_average_to_published_mean": true,
    "phases_are_pairwise_disjoint": true,
    "published_mean_position": "published 0.947307 = (1.385035 + 0.509580) / 2",
    "union_covers_published_folds": true
  },
  "phase_stable_fix_found": true,
  "point_in_time": "signals use only data available at formation (weights shifted one day), the SPY SMA is computed point-in-time, and the overlay/cost model are applied on the same continuously computed path for every fold and phase",
  "published_anchor_value": 0.9473,
  "published_design": {
    "decision": {
      "detail": "all evaluated gates pass (the SMA-plateau gate is not fold-dependent and is not re-evaluated)",
      "label": "Passes preliminary gates"
    },
    "folds": [
      {
        "fold": 1,
        "test_ann_return": 0.2376477486419304,
        "test_end": "2003-09-16",
        "test_max_dd": -0.030663328891376795,
        "test_sharpe": 2.554957343861941,
        "test_sharpe_canonical": 2.5462896555619716,
        "test_start": "2002-09-30",
        "test_trades": 94,
        "train_end": "2002-08-29",
        "train_sharpe": 1.2279634518441336,
        "train_start": "1993-01-01"
      },
      {
        "fold": 2,
        "test_ann_return": 0.30094714999850347,
        "test_end": "2004-03-10",
        "test_max_dd": -0.034646576000514906,
        "test_sharpe": 2.582051440567476,
        "test_sharpe_canonical": 2.473353898707039,
        "test_start": "2003-03-25",
        "test_trades": 215,
        "train_end": "2003-02-21",
        "train_sharpe": 1.2213240196570518,
        "train_start": "1993-06-28"
      },
      {
        "fold": 3,
        "test_ann_return": 0.04855931391588175,
        "test_end": "2004-09-02",
        "test_max_dd": -0.0796932859468743,
        "test_sharpe": 0.30274767243282663,
        "test_sharpe_canonical": 0.5496867064796653,
        "test_start": "2003-09-17",
        "test_trades": 211,
        "train_end": "2003-08-18",
        "train_sharpe": 1.3993052662260737,
        "train_start": "1993-12-21"
      },
      {
        "fold": 4,
        "test_ann_return": 0.14380394968973986,
        "test_end": "2005-02-25",
        "test_max_dd": -0.07607654608655523,
        "test_sharpe": 1.2699867020172544,
        "test_sharpe_canonical": 1.4271842215188322,
        "test_start": "2004-03-11",
        "test_trades": 154,
        "train_end": "2004-02-10",
        "train_sharpe": 1.5440703257733894,
        "train_start": "1994-06-15"
      },
      {
        "fold": 5,
        "test_ann_return": 0.2101684286299157,
        "test_end": "2005-08-22",
        "test_max_dd": -0.06013536651786566,
        "test_sharpe": 1.9493967137143615,
        "test_sharpe_canonical": 2.0047864502238606,
        "test_start": "2004-09-03",
        "test_trades": 146,
        "train_end": "2004-08-04",
        "train_sharpe": 1.4240136216530885,
        "train_start": "1994-12-08"
      },
      {
        "fold": 6,
        "test_ann_return": 0.24266149027572004,
        "test_end": "2006-02-14",
        "test_max_dd": -0.06013536651786566,
        "test_sharpe": 2.184895834814226,
        "test_sharpe_canonical": 2.1833935979536854,
        "test_start": "2005-02-28",
        "test_trades": 146,
        "train_end": "2005-01-27",
        "train_sharpe": 1.3278535556250024,
        "train_start": "1995-06-02"
      },
      {
        "fold": 7,
        "test_ann_return": 0.2625037213001782,
        "test_end": "2006-08-09",
        "test_max_dd": -0.06914882906909847,
        "test_sharpe": 2.3382234952228322,
        "test_sharpe_canonical": 2.300047269359534,
        "test_start": "2005-08-23",
        "test_trades": 163,
        "train_end": "2005-07-22",
        "train_sharpe": 1.2887808024245055,
        "train_start": "1995-11-27"
      },
      {
        "fold": 8,
        "test_ann_return": 0.20347048361261577,
        "test_end": "2007-02-01",
        "test_max_dd": -0.0691488290690988,
        "test_sharpe": 1.8911657288561508,
        "test_sharpe_canonical": 1.9581022491717013,
        "test_start": "2006-02-15",
        "test_trades": 207,
        "train_end": "2006-01-16",
        "train_sharpe": 1.3808067444757361,
        "train_start": "1996-05-21"
      },
      {
        "fold": 9,
        "test_ann_return": 0.15802025957072852,
        "test_end": "2007-07-27",
        "test_max_dd": -0.05115685317802399,
        "test_sharpe": 1.3166108652473656,
        "test_sharpe_canonical": 1.452316828617102,
        "test_start": "2006-08-10",
        "test_trades": 230,
        "train_end": "2006-07-11",
        "train_sharpe": 1.3005489517755242,
        "train_start": "1996-11-13"
      },
      {
        "fold": 10,
        "test_ann_return": 0.22751692328549655,
        "test_end": "2008-01-21",
        "test_max_dd": -0.05115685317802421,
        "test_sharpe": 2.081502248810079,
        "test_sharpe_canonical": 2.1068165950623907,
        "test_start": "2007-02-02",
        "test_trades": 198,
        "train_end": "2007-01-03",
        "train_sharpe": 1.3681773900538474,
        "train_start": "1997-05-08"
      },
      {
        "fold": 11,
        "test_ann_return": 0.18816098072809817,
        "test_end": "2008-07-15",
        "test_max_dd": -0.016672932819318587,
        "test_sharpe": 2.7409393118032823,
        "test_sharpe_canonical": 2.841582883589101,
        "test_start": "2007-07-30",
        "test_trades": 78,
        "train_end": "2007-06-28",
        "train_sharpe": 1.367133602091332,
        "train_start": "1997-10-31"
      },
      {
        "fold": 12,
        "test_ann_return": -0.0012503139197203028,
        "test_end": "2009-01-07",
        "test_max_dd": -0.001210645450968828,
        "test_sharpe": -21.829879416796786,
        "test_sharpe_canonical": -1.2847295005078068,
        "test_start": "2008-01-22",
        "test_trades": 2,
        "train_end": "2007-12-21",
        "train_sharpe": 1.408750969779352,
        "train_start": "1998-04-27"
      },
      {
        "fold": 13,
        "test_ann_return": 0.010358952184071457,
        "test_end": "2009-07-02",
        "test_max_dd": -0.028677407434000157,
        "test_sharpe": -0.2665263717842321,
        "test_sharpe_canonical": 0.30289212694810447,
        "test_start": "2008-07-16",
        "test_trades": 8,
        "train_end": "2008-06-16",
        "train_sharpe": 1.4459384481741144,
        "train_start": "1998-10-20"
      },
      {
        "fold": 14,
        "test_ann_return": 0.1798868045551152,
        "test_end": "2009-12-25",
        "test_max_dd": -0.04455892802721595,
        "test_sharpe": 1.766952939611926,
        "test_sharpe_canonical": 1.8737070090903962,
        "test_start": "2009-01-08",
        "test_trades": 114,
        "train_end": "2008-12-09",
        "train_sharpe": 1.2815756520529757,
        "train_start": "1999-04-14"
      },
      {
        "fold": 15,
        "test_ann_return": 0.1893496048056018,
        "test_end": "2010-06-21",
        "test_max_dd": -0.05845897354583074,
        "test_sharpe": 1.524240869787849,
        "test_sharpe_canonical": 1.6166032273462736,
        "test_start": "2009-07-03",
        "test_trades": 212,
        "train_end": "2009-06-03",
        "train_sharpe": 1.3579922084492122,
        "train_start": "1999-10-07"
      },
      {
        "fold": 16,
        "test_ann_return": 0.12399313128154388,
        "test_end": "2010-12-14",
        "test_max_dd": -0.058458973545830295,
        "test_sharpe": 1.0670791750849684,
        "test_sharpe_canonical": 1.2481738430690315,
        "test_start": "2009-12-28",
        "test_trades": 150,
        "train_end": "2009-11-26",
        "train_sharpe": 1.4469375346610183,
        "train_start": "2000-03-31"
      },
      {
        "fold": 17,
        "test_ann_return": 0.12550680619365795,
        "test_end": "2011-06-08",
        "test_max_dd": -0.04837369532033353,
        "test_sharpe": 1.0959979317769908,
        "test_sharpe_canonical": 1.2764605029462512,
        "test_start": "2010-06-22",
        "test_trades": 164,
        "train_end": "2010-05-21",
        "train_sharpe": 1.3349195836085468,
        "train_start": "2000-09-25"
      },
      {
        "fold": 18,
        "test_ann_return": 0.04000735359578855,
        "test_end": "2011-12-01",
        "test_max_dd": -0.056276047293041365,
        "test_sharpe": 0.24257925704586458,
        "test_sharpe_canonical": 0.516804291450329,
        "test_start": "2010-12-15",
        "test_trades": 162,
        "train_end": "2010-11-15",
        "train_sharpe": 1.4236750399243714,
        "train_start": "2001-03-20"
      },
      {
        "fold": 19,
        "test_ann_return": 0.08045949987028544,
        "test_end": "2012-05-25",
        "test_max_dd": -0.04259998747586713,
        "test_sharpe": 0.9429345486345174,
        "test_sharpe_canonical": 1.239066620433899,
        "test_start": "2011-06-09",
        "test_trades": 50,
        "train_end": "2011-05-10",
        "train_sharpe": 1.4900388497909631,
        "train_start": "2001-09-12"
      },
      {
        "fold": 20,
        "test_ann_return": 0.12251367328369644,
        "test_end": "2012-11-19",
        "test_max_dd": -0.047830962563369495,
        "test_sharpe": 1.2266564177629347,
        "test_sharpe_canonical": 1.424823745025369,
        "test_start": "2011-12-02",
        "test_trades": 24,
        "train_end": "2011-11-02",
        "train_sharpe": 1.3917363136685,
        "train_start": "2002-03-07"
      },
      {
        "fold": 21,
        "test_ann_return": 0.23686267965922148,
        "test_end": "2013-05-14",
        "test_max_dd": -0.04783096256337005,
        "test_sharpe": 2.206317379155769,
        "test_sharpe_canonical": 2.2125874707065027,
        "test_start": "2012-05-28",
        "test_trades": 131,
        "train_end": "2012-04-26",
        "train_sharpe": 1.5006807615998008,
        "train_start": "2002-08-30"
      },
      {
        "fold": 22,
        "test_ann_return": 0.23562742089650301,
        "test_end": "2013-11-06",
        "test_max_dd": -0.05738998583156685,
        "test_sharpe": 2.1734324648501686,
        "test_sharpe_canonical": 2.1829516096713686,
        "test_start": "2012-11-20",
        "test_trades": 238,
        "train_end": "2012-10-19",
        "train_sharpe": 1.4859679957466458,
        "train_start": "2003-02-24"
      },
      {
        "fold": 23,
        "test_ann_return": 0.10130056393265607,
        "test_end": "2014-05-01",
        "test_max_dd": -0.05738998583156685,
        "test_sharpe": 0.8107437857855019,
        "test_sharpe_canonical": 1.0124449391805923,
        "test_start": "2013-05-15",
        "test_trades": 236,
        "train_end": "2013-04-15",
        "train_sharpe": 1.4046143770201083,
        "train_start": "2003-08-19"
      },
      {
        "fold": 24,
        "test_ann_return": 0.06688119721467167,
        "test_end": "2014-10-24",
        "test_max_dd": -0.055822625043241425,
        "test_sharpe": 0.4830070939940177,
        "test_sharpe_canonical": 0.7155206545957572,
        "test_start": "2013-11-07",
        "test_trades": 184,
        "train_end": "2013-10-08",
        "train_sharpe": 1.3381406814895558,
        "train_start": "2004-02-11"
      },
      {
        "fold": 25,
        "test_ann_return": 0.12682151609439463,
        "test_end": "2015-04-20",
        "test_max_dd": -0.04136091095118488,
        "test_sharpe": 1.1701768634693603,
        "test_sharpe_canonical": 1.3537847973741637,
        "test_start": "2014-05-02",
        "test_trades": 102,
        "train_end": "2014-04-02",
        "train_sharpe": 1.5173941532049358,
        "train_start": "2004-08-05"
      },
      {
        "fold": 26,
        "test_ann_return": 0.09196473639188407,
        "test_end": "2015-10-13",
        "test_max_dd": -0.04205310246631744,
        "test_sharpe": 0.8976428595555964,
        "test_sharpe_canonical": 1.1375065786195537,
        "test_start": "2014-10-27",
        "test_trades": 35,
        "train_end": "2014-09-25",
        "train_sharpe": 1.4012779393841517,
        "train_start": "2005-01-28"
      },
      {
        "fold": 27,
        "test_ann_return": 0.0376710748586373,
        "test_end": "2016-04-06",
        "test_max_dd": -0.039912359506039774,
        "test_sharpe": 0.2791575413387473,
        "test_sharpe_canonical": 0.615665329311792,
        "test_start": "2015-04-21",
        "test_trades": 18,
        "train_end": "2015-03-20",
        "train_sharpe": 1.4038559632732708,
        "train_start": "2005-07-25"
      },
      {
        "fold": 28,
        "test_ann_return": 0.1099010890454648,
        "test_end": "2016-09-29",
        "test_max_dd": -0.034187786134353804,
        "test_sharpe": 1.345349582023667,
        "test_sharpe_canonical": 1.593934184105767,
        "test_start": "2015-10-14",
        "test_trades": 28,
        "train_end": "2015-09-14",
        "train_sharpe": 1.1924018146540654,
        "train_start": "2006-01-17"
      },
      {
        "fold": 29,
        "test_ann_return": 0.04416191764059829,
        "test_end": "2017-03-24",
        "test_max_dd": -0.09934896639748347,
        "test_sharpe": 0.29685553055420993,
        "test_sharpe_canonical": 0.5715565326724592,
        "test_start": "2016-04-07",
        "test_trades": 29,
        "train_end": "2016-03-08",
        "train_sharpe": 1.19454076585112,
        "train_start": "2006-07-12"
      },
      {
        "fold": 30,
        "test_ann_return": 0.07797678067254865,
        "test_end": "2017-09-18",
        "test_max_dd": -0.0865432040027524,
        "test_sharpe": 0.6331745793088774,
        "test_sharpe_canonical": 0.8658386856694635,
        "test_start": "2016-09-30",
        "test_trades": 60,
        "train_end": "2016-08-31",
        "train_sharpe": 1.1733893097399966,
        "train_start": "2007-01-04"
      },
      {
        "fold": 31,
        "test_ann_return": 0.19058612790369245,
        "test_end": "2018-03-13",
        "test_max_dd": -0.08666119876873024,
        "test_sharpe": 1.67638167680865,
        "test_sharpe_canonical": 1.7657714026375597,
        "test_start": "2017-03-27",
        "test_trades": 75,
        "train_end": "2017-02-23",
        "train_sharpe": 1.0888713372579566,
        "train_start": "2007-06-29"
      },
      {
        "fold": 32,
        "test_ann_return": 0.13034856000643624,
        "test_end": "2018-09-05",
        "test_max_dd": -0.08666119876873035,
        "test_sharpe": 1.137310395687428,
        "test_sharpe_canonical": 1.311592579711584,
        "test_start": "2017-09-19",
        "test_trades": 148,
        "train_end": "2017-08-18",
        "train_sharpe": 0.9463856437444401,
        "train_start": "2007-12-24"
      },
      {
        "fold": 33,
        "test_ann_return": 0.039472774857814974,
        "test_end": "2019-02-28",
        "test_max_dd": -0.06143247772982807,
        "test_sharpe": 0.24718947185832646,
        "test_sharpe_canonical": 0.5307313914254013,
        "test_start": "2018-03-14",
        "test_trades": 130,
        "train_end": "2018-02-12",
        "train_sharpe": 1.0242046314639115,
        "train_start": "2008-06-17"
      },
      {
        "fold": 34,
        "test_ann_return": 0.10550886044213681,
        "test_end": "2019-08-23",
        "test_max_dd": -0.05912876041784676,
        "test_sharpe": 1.0883359067575717,
        "test_sharpe_canonical": 1.3160590591907242,
        "test_start": "2018-09-06",
        "test_trades": 28,
        "train_end": "2018-08-07",
        "train_sharpe": 1.0865880972169413,
        "train_start": "2008-12-10"
      },
      {
        "fold": 35,
        "test_ann_return": 0.2507648494811565,
        "test_end": "2020-02-17",
        "test_max_dd": -0.03707907709313607,
        "test_sharpe": 3.252075026352224,
        "test_sharpe_canonical": 3.190023719554733,
        "test_start": "2019-03-01",
        "test_trades": 26,
        "train_end": "2019-01-30",
        "train_sharpe": 1.039860669648358,
        "train_start": "2009-06-04"
      },
      {
        "fold": 36,
        "test_ann_return": 0.3062388503284017,
        "test_end": "2020-08-11",
        "test_max_dd": -0.03916526988162272,
        "test_sharpe": 3.9121052879675915,
        "test_sharpe_canonical": 3.6896116995686974,
        "test_start": "2019-08-26",
        "test_trades": 24,
        "train_end": "2019-07-25",
        "train_sharpe": 0.980137509736173,
        "train_start": "2009-11-27"
      },
      {
        "fold": 37,
        "test_ann_return": 0.24455516266448196,
        "test_end": "2021-02-03",
        "test_max_dd": -0.05737581276154191,
        "test_sharpe": 2.3629158330846916,
        "test_sharpe_canonical": 2.3505046675433587,
        "test_start": "2020-02-18",
        "test_trades": 124,
        "train_end": "2020-01-17",
        "train_sharpe": 1.1592647490930292,
        "train_start": "2010-05-24"
      },
      {
        "fold": 38,
        "test_ann_return": 0.10230564579347545,
        "test_end": "2021-07-29",
        "test_max_dd": -0.057375812761542466,
        "test_sharpe": 0.7952411969062717,
        "test_sharpe_canonical": 0.9929171427171172,
        "test_start": "2020-08-12",
        "test_trades": 233,
        "train_end": "2020-07-13",
        "train_sharpe": 1.2404296932975856,
        "train_start": "2010-11-16"
      },
      {
        "fold": 39,
        "test_ann_return": 0.011215008818299843,
        "test_end": "2022-01-21",
        "test_max_dd": -0.06324205466798849,
        "test_sharpe": -0.08358271006476463,
        "test_sharpe_canonical": 0.15852684230016514,
        "test_start": "2021-02-04",
        "test_trades": 243,
        "train_end": "2021-01-05",
        "train_sharpe": 1.2415200531342212,
        "train_start": "2011-05-11"
      },
      {
        "fold": 40,
        "test_ann_return": 0.011128203969249295,
        "test_end": "2022-07-18",
        "test_max_dd": -0.06324205466798782,
        "test_sharpe": -0.10732991321229177,
        "test_sharpe_canonical": 0.1751153791361648,
        "test_start": "2021-07-30",
        "test_trades": 148,
        "train_end": "2021-06-30",
        "train_sharpe": 1.2987273115038214,
        "train_start": "2011-11-03"
      },
      {
        "fold": 41,
        "test_ann_return": 0.05558728826307191,
        "test_end": "2023-01-10",
        "test_max_dd": -0.014533910576322917,
        "test_sharpe": 0.8946927114221876,
        "test_sharpe_canonical": 1.3799207150944197,
        "test_start": "2022-01-24",
        "test_trades": 29,
        "train_end": "2021-12-23",
        "train_sharpe": 1.1736537258095172,
        "train_start": "2012-04-27"
      },
      {
        "fold": 42,
        "test_ann_return": 0.13407946859976905,
        "test_end": "2023-07-05",
        "test_max_dd": -0.049654709208544756,
        "test_sharpe": 1.5583667409783086,
        "test_sharpe_canonical": 1.7555942817851862,
        "test_start": "2022-07-19",
        "test_trades": 32,
        "train_end": "2022-06-17",
        "train_sharpe": 1.1516924367432786,
        "train_start": "2012-10-22"
      },
      {
        "fold": 43,
        "test_ann_return": 0.2002503938626765,
        "test_end": "2023-12-28",
        "test_max_dd": -0.07793990324215128,
        "test_sharpe": 1.8332409273747643,
        "test_sharpe_canonical": 1.9060465393026864,
        "test_start": "2023-01-11",
        "test_trades": 118,
        "train_end": "2022-12-12",
        "train_sharpe": 1.090448418493581,
        "train_start": "2013-04-16"
      },
      {
        "fold": 44,
        "test_ann_return": 0.2022204171983275,
        "test_end": "2024-06-21",
        "test_max_dd": -0.07793990324215094,
        "test_sharpe": 1.81856488947759,
        "test_sharpe_canonical": 1.888572580072733,
        "test_start": "2023-07-06",
        "test_trades": 185,
        "train_end": "2023-06-06",
        "train_sharpe": 1.1321906009905789,
        "train_start": "2013-10-09"
      },
      {
        "fold": 45,
        "test_ann_return": 0.20729793433723254,
        "test_end": "2024-12-16",
        "test_max_dd": -0.06462135007497705,
        "test_sharpe": 1.8342182200072057,
        "test_sharpe_canonical": 1.8964216181154532,
        "test_start": "2023-12-29",
        "test_trades": 220,
        "train_end": "2023-11-29",
        "train_sharpe": 1.073121241583694,
        "train_start": "2014-04-03"
      },
      {
        "fold": 46,
        "test_ann_return": 0.12490239669762193,
        "test_end": "2025-06-10",
        "test_max_dd": -0.06462135007497694,
        "test_sharpe": 1.1148099216076683,
        "test_sharpe_canonical": 1.2980143119148375,
        "test_start": "2024-06-24",
        "test_trades": 186,
        "train_end": "2024-05-23",
        "train_sharpe": 1.2036487751206402,
        "train_start": "2014-09-26"
      },
      {
        "fold": 47,
        "test_ann_return": 0.20334324434421824,
        "test_end": "2025-12-03",
        "test_max_dd": -0.049857401112320954,
        "test_sharpe": 1.9609278869742752,
        "test_sharpe_canonical": 2.02710364685011,
        "test_start": "2024-12-17",
        "test_trades": 115,
        "train_end": "2024-11-15",
        "train_sharpe": 1.1557021608851996,
        "train_start": "2015-03-23"
      },
      {
        "fold": 48,
        "test_ann_return": 0.3197431491772065,
        "test_end": "2026-05-28",
        "test_max_dd": -0.038241314668189696,
        "test_sharpe": 2.8969247986858013,
        "test_sharpe_canonical": 2.734388052684735,
        "test_start": "2025-06-11",
        "test_trades": 160,
        "train_end": "2025-05-12",
        "train_sharpe": 1.190343042350607,
        "train_start": "2015-09-15"
      }
    ],
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
      "mean_test_sharpe_canonical": 1.514293096532496,
      "mean_test_trades": 125.27083333333333,
      "median_test_sharpe": 1.29329878363231,
      "min_test_sharpe": -21.829879416796786,
      "n_folds": 48,
      "pct_positive_sharpe": 0.9166666666666666,
      "std_test_sharpe": 3.4797702418403893,
      "total_test_trades": 6013
    }
  },
  "published_gate1_status": "PASS",
  "published_mean_recomputed": 0.9473074720246092,
  "published_record_path": "research/experiments/tsmomentum_regime_filter_wf_001.md",
  "published_verdict": "Credible Candidate",
  "read_only": {
    "committed_artifacts_unchanged": true,
    "config_unchanged": true,
    "data_unchanged": true
  },
  "rf_annual": 0.02,
  "slippage_bps": 2.0,
  "stability": {
    "gate1_outcome_changes_between_phases": true,
    "gate1_outcome_changes_when_thin_trade_folds_excluded": false,
    "published_pass_stable": false
  },
  "tweaks_tested": [
    {
      "description": "Change SPY SMA window from 200 to 175",
      "name": "spy_sma_175",
      "phase_a_gate1": "PASS",
      "phase_a_mean": 1.5391446802629378,
      "phase_a_trades": 2922,
      "phase_b_gate1": "PASS",
      "phase_b_mean": 1.5407838193178032,
      "phase_b_trades": 3024,
      "phase_stable_pass": true,
      "spy_sma_window": 175
    }
  ]
}
```
