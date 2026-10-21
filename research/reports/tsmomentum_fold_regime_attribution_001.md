# Fold Regime Attribution of the Incumbent Walk-Forward (tsmomentum_fold_regime_attribution_001, Cycle 923)

## Summary

- Candidate: `tsmomentum_spytrend_001` (the incumbent)
- Published walk-forward record (resolved by content): `research/experiments/tsmomentum_regime_filter_wf_001.md`
- Published WF mean OOS Sharpe: 0.947300 (gate >= 0.9)
- Recomputed WF mean OOS Sharpe: 0.947307 (48 folds, 6013 pooled OOS trades)
- Anchor reproduced: **YES**
- Incumbent's published verdict is **unchanged** by this attribution: **Credible Candidate (unchanged)** (this tool is descriptive only).
- Read-only: `data/` and `config/` byte-identical before and after the run (**yes**); no committed artifact modified (**yes**).
- Data source: committed parquet cache in `data/raw/` only; the fetcher is never called.

## 1. Reproduction anchor (fail closed)

The published 48-fold walk-forward is re-derived from the committed cache with the committed candidate definition and compared with the published record before any attribution is published. A mismatch fails the run.

| Metric | Published | Recomputed | Tolerance | Match |
|---|---|---|---|---|
| n_folds | 48 | 48 | 0.000000 | MATCH |
| mean_test_sharpe | 0.9473 | 0.9473 | 0.000100 | MATCH |
| std_test_sharpe | 3.4798 | 3.4798 | 0.000100 | MATCH |
| median_test_sharpe | 1.2933 | 1.2933 | 0.000100 | MATCH |
| min_test_sharpe | -21.8299 | -21.8299 | 0.000100 | MATCH |
| max_test_sharpe | 3.9121 | 3.9121 | 0.000100 | MATCH |
| pct_positive_sharpe | 91.7% | 0.9167 | 0.050000 | MATCH |
| total_test_trades | 6013 | 6013 | 0.000000 | MATCH |

- Aggregate anchor: **MATCH**
- Per-fold reproduction: **48 folds**, all windows/OOS Sharpe/trades reproduced: **YES**

## 2. Phase decomposition (F1 calendar phase, published finding)

- Phase A (folds 1, 3, 5, ...): 24 folds, mean OOS Sharpe 1.385035
- Phase B (folds 2, 4, 6, ...): 24 folds, mean OOS Sharpe 0.509580
- Overall phase gap (A - B): +0.875454. Under phase B alone gate 1 (0.9) would FAIL (0.509580 < 0.9).

## 3. Observable-state bucket attribution

Four pre-specified bucket families (no fifth family). Every bucket is published with its fold count ``n``; the phase-A / phase-B split is computed *inside* each bucket (the state-vs-calendar test).

### F1 calendar phase

*phase A = published folds 1, 3, 5, ...; phase B = folds 2, 4, 6, ... (published decomposition)*

| Bucket | n | Mean OOS Sharpe | Median OOS Sharpe | Phase A n | Phase A mean | Phase B n | Phase B mean |
|---|---|---|---|---|---|---|---|
| phase_A | 24 | 1.3850 | 1.4204 | 24 | 1.3850 | 0 | N/A |
| phase_B | 24 | 0.5096 | 1.2483 | 0 | N/A | 24 | 0.5096 |

- Dispersion share (eta^2): 0.016160; permutation p-value (10000 permutations, seed 923): **0.634937**

### F2 SPY trend state at test-window start

*risk-on if SPY Close >= its 200-day SMA at test-window start (point-in-time); risk-off otherwise*

| Bucket | n | Mean OOS Sharpe | Median OOS Sharpe | Phase A n | Phase A mean | Phase B n | Phase B mean |
|---|---|---|---|---|---|---|---|
| risk_on | 37 | 1.4246 | 1.2700 | 19 | 1.4278 | 18 | 1.4211 |
| risk_off | 11 | -0.6580 | 1.3453 | 5 | 1.2225 | 6 | -2.2251 |

- Dispersion share (eta^2): 0.064618; permutation p-value (10000 permutations, seed 923): **0.127087**

### F3 SPY trailing 12-month return sign at test-window start

*sign of SPY trailing ~12-month (252 trading-day) return at test-window start; up / down*

| Bucket | n | Mean OOS Sharpe | Median OOS Sharpe | Phase A n | Phase A mean | Phase B n | Phase B mean |
|---|---|---|---|---|---|---|---|
| up | 38 | 1.4012 | 1.1984 | 18 | 1.3940 | 20 | 1.4076 |
| down | 10 | -0.7773 | 1.6627 | 6 | 1.3582 | 4 | -3.9806 |

- Dispersion share (eta^2): 0.066018; permutation p-value (10000 permutations, seed 923): **0.141386**

### F4 training-window 63-day realised volatility tercile

*trailing 63-day realised vol of the strategy's own net returns at train_end, terciled within that fold's training window only; low / medium / high*

| Bucket | n | Mean OOS Sharpe | Median OOS Sharpe | Phase A n | Phase A mean | Phase B n | Phase B mean |
|---|---|---|---|---|---|---|---|
| low_vol | 17 | 1.5387 | 1.5584 | 7 | 1.7674 | 10 | 1.3786 |
| med_vol | 18 | 0.3170 | 1.7475 | 10 | 1.4899 | 8 | -1.1492 |
| high_vol | 13 | 1.0468 | 1.0960 | 7 | 0.8529 | 6 | 1.2730 |

- Dispersion share (eta^2): 0.023240; permutation p-value (10000 permutations, seed 923): **0.877812**

## 4. State-vs-calendar test

The phase gap (A minus B mean OOS Sharpe) computed *within* each state bucket of F2/F3/F4, compared with the overall phase gap (+0.875454). A bucket-internal gap that collapses toward zero means the observable state explains the weakness; a gap that persists means a calendar/protocol effect no observable state flags.

| Family | Bucket | Phase gap within bucket | Gap minus overall |
|---|---|---|---|
| F2_spy_trend_state | risk_on | 0.0067 | -0.8688 |
| F2_spy_trend_state | risk_off | 3.4476 | 2.5721 |
| F3_spy_12m_return_sign | up | -0.0136 | -0.8891 |
| F3_spy_12m_return_sign | down | 5.3388 | 4.4634 |
| F4_train_63d_realvol_tercile | low_vol | 0.3888 | -0.4866 |
| F4_train_63d_realvol_tercile | med_vol | 2.6391 | 1.7636 |
| F4_train_63d_realvol_tercile | high_vol | -0.4201 | -1.2955 |

### Conclusion

Mixed evidence: the phase gap shrinks inside some state buckets but persists inside others, so the weakness is only partially explained by the observable states tested here; treat the monitorable signal as tentative.

## 5. Monitoring statement

No observable state among F2/F3/F4 is wired into any gate or decision. If monitored on the live stance, the candidate input would be: watch the SPY trend state (F2), the trailing 12-month return sign (F3) and the training-window realised volatility tercile (F4). The phase-A / phase-B gap collapses to about zero in risk-on and up-trend buckets (both phases ~1.4, no calendar weakness), while it persists in risk-off and down-trend buckets (phase B far weaker than phase A) -- so the phase-B weakness concentrates in observable risk-off/down states, albeit with small fold counts (11 risk-off, 10 down) and no dispersion share reaching conventional significance. Treat the monitorable signal as tentative. This attribution does not select, re-rank or re-fit anything and does not change the incumbent's published verdict.

This is a *candidate monitoring input only*: it is not wired into any gate, drift flag, threshold or decision mapping, and it does not change the incumbent's published verdict.

## 6. Checks

- [published_record_resolved_by_content]: PASS (observed: research/experiments/tsmomentum_regime_filter_wf_001.md, expected: exactly one published walk-forward record)
- [cache_only_path_built]: PASS (observed: 8488 sessions, 7 symbols, expected: non-empty path)
- [published_48_folds_evaluated]: PASS (observed: 48 folds, expected: 48 folds)
- [recomputed_aggregate_present]: PASS (observed: n=48, mean=0.947307, expected: non-empty summary)
- [reproduces_published_walk_forward_aggregate]: PASS (observed: mean=0.947307 (published 0.9473), expected: published aggregate statistics)
- [reproduces_published_walk_forward_fold_table]: PASS (observed: 48 folds compared, expected: every published fold reproduced)
- [phase_decomposition_matches_published_finding]: PASS (observed: A=1.385035, B=0.509580, expected: A~1.385035, B~0.509580 (Cycle 910))
- [bucket_family_F1_calendar_phase_has_exact_pre_specified_buckets]: PASS (observed: ['phase_A', 'phase_B'], expected: pre-specified ['phase_A', 'phase_B'])
- [bucket_family_F1_calendar_phase_every_bucket_has_n]: PASS (observed: n=[24, 24], expected: n > 0 for every bucket)
- [bucket_family_F2_spy_trend_state_has_exact_pre_specified_buckets]: PASS (observed: ['risk_off', 'risk_on'], expected: pre-specified ['risk_off', 'risk_on'])
- [bucket_family_F2_spy_trend_state_every_bucket_has_n]: PASS (observed: n=[37, 11], expected: n > 0 for every bucket)
- [bucket_family_F3_spy_12m_return_sign_has_exact_pre_specified_buckets]: PASS (observed: ['down', 'up'], expected: pre-specified ['down', 'up'])
- [bucket_family_F3_spy_12m_return_sign_every_bucket_has_n]: PASS (observed: n=[38, 10], expected: n > 0 for every bucket)
- [bucket_family_F4_train_63d_realvol_tercile_has_exact_pre_specified_buckets]: PASS (observed: ['high_vol', 'low_vol', 'med_vol'], expected: pre-specified ['high_vol', 'low_vol', 'med_vol'])
- [bucket_family_F4_train_63d_realvol_tercile_every_bucket_has_n]: PASS (observed: n=[17, 18, 13], expected: n > 0 for every bucket)
- [exactly_four_bucket_families_no_fifth]: PASS (observed: F1_calendar_phase, F2_spy_trend_state, F3_spy_12m_return_sign, F4_train_63d_realvol_tercile, expected: F1_calendar_phase, F2_spy_trend_state, F3_spy_12m_return_sign, F4_train_63d_realvol_tercile)
- [data_unchanged]: PASS
- [config_unchanged]: PASS
- [committed_artifacts_unchanged]: PASS

## 7. Reproduction commands

```bash
python research/tsmomentum_fold_regime_attribution.py
python -m pytest -q tests/test_tsmomentum_fold_regime_attribution.py
python -m pytest -q
git status --porcelain data/ config/
git diff --name-only HEAD -- research/run_cycle6.py research/experiments/tsmomentum_regime_filter_wf_001.md
```

## 8. JSON payload

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
  "anchor_reproduced": true,
  "bucket_families_order": [
    "F1_calendar_phase",
    "F2_spy_trend_state",
    "F3_spy_12m_return_sign",
    "F4_train_63d_realvol_tercile"
  ],
  "candidate": "tsmomentum_spytrend_001",
  "checks": [
    {
      "expected": "exactly one published walk-forward record",
      "name": "published_record_resolved_by_content",
      "observed": "research/experiments/tsmomentum_regime_filter_wf_001.md",
      "pass": true
    },
    {
      "expected": "non-empty path",
      "name": "cache_only_path_built",
      "observed": "8488 sessions, 7 symbols",
      "pass": true
    },
    {
      "expected": "48 folds",
      "name": "published_48_folds_evaluated",
      "observed": "48 folds",
      "pass": true
    },
    {
      "expected": "non-empty summary",
      "name": "recomputed_aggregate_present",
      "observed": "n=48, mean=0.947307",
      "pass": true
    },
    {
      "expected": "published aggregate statistics",
      "name": "reproduces_published_walk_forward_aggregate",
      "observed": "mean=0.947307 (published 0.9473)",
      "pass": true
    },
    {
      "expected": "every published fold reproduced",
      "name": "reproduces_published_walk_forward_fold_table",
      "observed": "48 folds compared",
      "pass": true
    },
    {
      "expected": "A~1.385035, B~0.509580 (Cycle 910)",
      "name": "phase_decomposition_matches_published_finding",
      "observed": "A=1.385035, B=0.509580",
      "pass": true
    },
    {
      "expected": "pre-specified ['phase_A', 'phase_B']",
      "name": "bucket_family_F1_calendar_phase_has_exact_pre_specified_buckets",
      "observed": "['phase_A', 'phase_B']",
      "pass": true
    },
    {
      "expected": "n > 0 for every bucket",
      "name": "bucket_family_F1_calendar_phase_every_bucket_has_n",
      "observed": "n=[24, 24]",
      "pass": true
    },
    {
      "expected": "pre-specified ['risk_off', 'risk_on']",
      "name": "bucket_family_F2_spy_trend_state_has_exact_pre_specified_buckets",
      "observed": "['risk_off', 'risk_on']",
      "pass": true
    },
    {
      "expected": "n > 0 for every bucket",
      "name": "bucket_family_F2_spy_trend_state_every_bucket_has_n",
      "observed": "n=[37, 11]",
      "pass": true
    },
    {
      "expected": "pre-specified ['down', 'up']",
      "name": "bucket_family_F3_spy_12m_return_sign_has_exact_pre_specified_buckets",
      "observed": "['down', 'up']",
      "pass": true
    },
    {
      "expected": "n > 0 for every bucket",
      "name": "bucket_family_F3_spy_12m_return_sign_every_bucket_has_n",
      "observed": "n=[38, 10]",
      "pass": true
    },
    {
      "expected": "pre-specified ['high_vol', 'low_vol', 'med_vol']",
      "name": "bucket_family_F4_train_63d_realvol_tercile_has_exact_pre_specified_buckets",
      "observed": "['high_vol', 'low_vol', 'med_vol']",
      "pass": true
    },
    {
      "expected": "n > 0 for every bucket",
      "name": "bucket_family_F4_train_63d_realvol_tercile_every_bucket_has_n",
      "observed": "n=[17, 18, 13]",
      "pass": true
    },
    {
      "expected": "F1_calendar_phase, F2_spy_trend_state, F3_spy_12m_return_sign, F4_train_63d_realvol_tercile",
      "name": "exactly_four_bucket_families_no_fifth",
      "observed": "F1_calendar_phase, F2_spy_trend_state, F3_spy_12m_return_sign, F4_train_63d_realvol_tercile",
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
  "cycle": "923",
  "data_source": "committed parquet cache in data/raw/ (fetcher never called)",
  "families": {
    "F1_calendar_phase": {
      "buckets": [
        {
          "bucket": "phase_A",
          "family": "F1_calendar_phase",
          "gap_vs_overall": NaN,
          "in_bucket_phase_gap": NaN,
          "mean_test_sharpe": 1.3850346885341203,
          "median_test_sharpe": 1.4204258675176074,
          "n": 24,
          "phase_A_mean": 1.3850346885341203,
          "phase_A_n": 24,
          "phase_B_mean": NaN,
          "phase_B_n": 0
        },
        {
          "bucket": "phase_B",
          "family": "F1_calendar_phase",
          "gap_vs_overall": NaN,
          "in_bucket_phase_gap": NaN,
          "mean_test_sharpe": 0.5095802555150982,
          "median_test_sharpe": 1.2483215598900945,
          "n": 24,
          "phase_A_mean": NaN,
          "phase_A_n": 0,
          "phase_B_mean": 0.5095802555150982,
          "phase_B_n": 24
        }
      ],
      "definition": "phase A = published folds 1, 3, 5, ...; phase B = folds 2, 4, 6, ... (published decomposition)",
      "dispersion_share": 0.016160297101650137,
      "label": "F1 calendar phase",
      "permutation_count": 6349,
      "permutation_pvalue": 0.634936506349365
    },
    "F2_spy_trend_state": {
      "buckets": [
        {
          "bucket": "risk_on",
          "family": "F2_spy_trend_state",
          "gap_vs_overall": -0.8687751361098751,
          "in_bucket_phase_gap": 0.006679296909146926,
          "mean_test_sharpe": 1.424564821902218,
          "median_test_sharpe": 1.2699867020172544,
          "n": 37,
          "phase_A_mean": 1.427814209587749,
          "phase_A_n": 19,
          "phase_B_mean": 1.4211349126786021,
          "phase_B_n": 18
        },
        {
          "bucket": "risk_off",
          "family": "F2_spy_trend_state",
          "gap_vs_overall": 2.5721017914867206,
          "in_bucket_phase_gap": 3.4475562245057425,
          "mean_test_sharpe": -0.6580127048364379,
          "median_test_sharpe": 1.345349582023667,
          "n": 11,
          "phase_A_mean": 1.2224725085303303,
          "phase_A_n": 5,
          "phase_B_mean": -2.225083715975412,
          "phase_B_n": 6
        }
      ],
      "definition": "risk-on if SPY Close >= its 200-day SMA at test-window start (point-in-time); risk-off otherwise",
      "dispersion_share": 0.06461844896409409,
      "label": "F2 SPY trend state at test-window start",
      "permutation_count": 1270,
      "permutation_pvalue": 0.12708729127087293
    },
    "F3_spy_12m_return_sign": {
      "buckets": [
        {
          "bucket": "up",
          "family": "F3_spy_12m_return_sign",
          "gap_vs_overall": -0.8890902185375059,
          "in_bucket_phase_gap": -0.013635785518483878,
          "mean_test_sharpe": 1.4011626651018427,
          "median_test_sharpe": 1.1984166406161476,
          "n": 38,
          "phase_A_mean": 1.3939859358815878,
          "phase_A_n": 18,
          "phase_B_mean": 1.4076217214000717,
          "phase_B_n": 20
        },
        {
          "bucket": "down",
          "family": "F3_spy_12m_return_sign",
          "gap_vs_overall": 4.463353587382463,
          "in_bucket_phase_gap": 5.338808020401485,
          "mean_test_sharpe": -0.777342261668877,
          "median_test_sharpe": 1.6626598402951172,
          "n": 10,
          "phase_A_mean": 1.358180946491717,
          "phase_A_n": 6,
          "phase_B_mean": -3.9806270739097687,
          "phase_B_n": 4
        }
      ],
      "definition": "sign of SPY trailing ~12-month (252 trading-day) return at test-window start; up / down",
      "dispersion_share": 0.06601770984528582,
      "label": "F3 SPY trailing 12-month return sign at test-window start",
      "permutation_count": 1413,
      "permutation_pvalue": 0.14138586141385862
    },
    "F4_train_63d_realvol_tercile": {
      "buckets": [
        {
          "bucket": "low_vol",
          "family": "F4_train_63d_realvol_tercile",
          "gap_vs_overall": -0.4866351184343004,
          "in_bucket_phase_gap": 0.38881931458472163,
          "mean_test_sharpe": 1.5386744396504102,
          "median_test_sharpe": 1.5583667409783086,
          "n": 17,
          "phase_A_mean": 1.767391683523776,
          "phase_A_n": 7,
          "phase_B_mean": 1.3785723689390543,
          "phase_B_n": 10
        },
        {
          "bucket": "med_vol",
          "family": "F4_train_63d_realvol_tercile",
          "gap_vs_overall": 1.7636243682776263,
          "in_bucket_phase_gap": 2.639078801296648,
          "mean_test_sharpe": 0.31695015584368824,
          "median_test_sharpe": 1.74747328314312,
          "n": 18,
          "phase_A_mean": 1.4898740675310875,
          "phase_A_n": 10,
          "phase_B_mean": -1.1492047337655606,
          "phase_B_n": 8
        },
        {
          "bucket": "high_vol",
          "family": "F4_train_63d_realvol_tercile",
          "gap_vs_overall": -1.295520666414848,
          "in_bucket_phase_gap": -0.42006623339582594,
          "mean_test_sharpe": 1.0467838752259906,
          "median_test_sharpe": 1.0959979317769908,
          "n": 13,
          "phase_A_mean": 0.852907152120225,
          "phase_A_n": 7,
          "phase_B_mean": 1.272973385516051,
          "phase_B_n": 6
        }
      ],
      "definition": "trailing 63-day realised vol of the strategy's own net returns at train_end, terciled within that fold's training window only; low / medium / high",
      "dispersion_share": 0.023239825152428114,
      "label": "F4 training-window 63-day realised volatility tercile",
      "permutation_count": 8778,
      "permutation_pvalue": 0.8778122187781222
    }
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
      "observed": 6013.0,
      "status": "PASS",
      "threshold": 100
    }
  ],
  "incumbent_verdict": "Credible Candidate (unchanged)",
  "monitoring_statement": "No observable state among F2/F3/F4 is wired into any gate or decision. If monitored on the live stance, the candidate input would be: watch the SPY trend state (F2), the trailing 12-month return sign (F3) and the training-window realised volatility tercile (F4). The phase-A / phase-B gap collapses to about zero in risk-on and up-trend buckets (both phases ~1.4, no calendar weakness), while it persists in risk-off and down-trend buckets (phase B far weaker than phase A) -- so the phase-B weakness concentrates in observable risk-off/down states, albeit with small fold counts (11 risk-off, 10 down) and no dispersion share reaching conventional significance. Treat the monitorable signal as tentative. This attribution does not select, re-rank or re-fit anything and does not change the incumbent's published verdict.",
  "overall": "PASS",
  "permutation_seed": 923,
  "permutations": 10000,
  "phase_decomposition": {
    "phase_A_mean": 1.3850346885341203,
    "phase_A_n": 24,
    "phase_B_mean": 0.5095802555150982,
    "phase_B_n": 24,
    "phase_gap_overall": 0.875454433019022
  },
  "published_anchor_value": 0.9473,
  "published_record_path": "research/experiments/tsmomentum_regime_filter_wf_001.md",
  "read_only": {
    "committed_artifacts_unchanged": true,
    "config_unchanged": true,
    "data_unchanged": true
  },
  "recomputed_summary": {
    "max_test_sharpe": 3.9121052879675915,
    "mean_test_sharpe": 0.9473074720246092,
    "median_test_sharpe": 1.29329878363231,
    "min_test_sharpe": -21.829879416796786,
    "n_folds": 48,
    "pct_positive_sharpe": 0.9166666666666666,
    "std_test_sharpe": 3.4797702418403893,
    "total_test_trades": 6013
  },
  "state_vs_calendar_conclusion": "Mixed evidence: the phase gap shrinks inside some state buckets but persists inside others, so the weakness is only partially explained by the observable states tested here; treat the monitorable signal as tentative."
}
```
