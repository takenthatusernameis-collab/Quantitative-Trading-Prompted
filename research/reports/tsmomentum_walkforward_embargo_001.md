# TSMomentum SPY-Trend Walk-Forward Embargo Audit (tsmomentum_walkforward_embargo_001, Cycle 910)

## Summary

- Candidate: `tsmomentum_spytrend_001` (the incumbent)
- Published walk-forward record (resolved by content): `research/experiments/tsmomentum_regime_filter_wf_001.md`
- Published WF mean OOS Sharpe: 0.9473 (gate >= 0.9, margin +0.0473)
- Design A (non-overlapping test windows) WF mean OOS Sharpe: 1.3850 (24 folds)
- Gate-1 outcome: published **PASS**, Design A **PASS** -- outcome changes under Design A: **NO**
- Published verdict: **Credible Candidate**; Design A verdict: **Passes preliminary gates**; verdict survives Design A: **YES** (the published record's verdict also requires the SMA-plateau gate, which is not fold-dependent and is therefore not re-evaluated here)
- Read-only: `data/` and `config/` byte-identical before and after the run (**yes**); no committed artifact modified (**yes**).
- Data source: committed parquet cache in `data/raw/` only; the fetcher is never called.

## 1. Reproduction anchor (published design, re-derived from the committed cache)

The published design is re-derived from the committed cache with the committed candidate definition and compared with the published record, which is resolved by content (the record that carries the published aggregate table and fold table).

| Metric | Published | Recomputed | Tolerance | Match |
|---|---|---|---|---|
| n_folds | 48 | 48 | 0.000000 | MATCH |
| mean_test_sharpe | 0.9473 | 0.9473 | 0.000100 | MATCH |
| std_test_sharpe | 3.4798 | 3.4798 | 0.000100 | MATCH |
| median_test_sharpe | 1.2933 | 1.2933 | 0.000100 | MATCH |
| min_test_sharpe | -21.8299 | -21.8299 | 0.000100 | MATCH |
| max_test_sharpe | 3.9121 | 3.9121 | 0.000100 | MATCH |
| pct_positive_sharpe | 91.7% | 0.9167 | 0.050000 | MATCH |
| mean_test_ann_return | 14.71% | 0.1471 | 0.005000 | MATCH |
| mean_test_max_dd | -5.41% | -0.0541 | 0.005000 | MATCH |
| mean_test_trades | 125.3 | 125.2708 | 0.100000 | MATCH |
| total_test_trades | 6013 | 6013 | 0.000000 | MATCH |

- Aggregate anchor: **MATCH**
- Per-fold reproduction: **48 folds**, all windows/OOS Sharpe/trades reproduced: **YES**

## 2. The three designs

All three designs are evaluated on the **same continuously computed point-in-time path** (one pass over the committed cache, one overlay, one cost model); only the fold windows change.

| Design | Folds | WF mean OOS Sharpe | Median | Positive fold rate | Pooled OOS trades | Mean consecutive overlap (days) | Max disjoint test windows | Decision |
|---|---|---|---|---|---|---|---|---|
| Published design | 48 | 0.947307 | 1.293299 | 0.9167 | 6013 | 175.0 | 24 | Passes preliminary gates |
| Design A (non-overlapping) | 24 | 1.385035 | 1.420426 | 0.9167 | 2952 | 0.0 | 24 | Passes preliminary gates |
| Design B (literal embargo) | 3 | 1.634397 | 1.318150 | 1.0000 | 551 | 0.0 | 3 | Passes preliminary gates |

### 2.1 Published design -- fold table

| Fold | Train Start | Train End | Test Start | Test End | Train Sharpe | Test Sharpe | Test Ann. Ret. | Test Max DD | Test Trades |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1993-01-01 | 2002-08-29 | 2002-09-30 | 2003-09-16 | 1.2280 | 2.5550 | 0.2376 | -0.0307 | 94 |
| 2 | 1993-06-28 | 2003-02-21 | 2003-03-25 | 2004-03-10 | 1.2213 | 2.5821 | 0.3009 | -0.0346 | 215 |
| 3 | 1993-12-21 | 2003-08-18 | 2003-09-17 | 2004-09-02 | 1.3993 | 0.3027 | 0.0486 | -0.0797 | 211 |
| 4 | 1994-06-15 | 2004-02-10 | 2004-03-11 | 2005-02-25 | 1.5441 | 1.2700 | 0.1438 | -0.0761 | 154 |
| 5 | 1994-12-08 | 2004-08-04 | 2004-09-03 | 2005-08-22 | 1.4240 | 1.9494 | 0.2102 | -0.0601 | 146 |
| 6 | 1995-06-02 | 2005-01-27 | 2005-02-28 | 2006-02-14 | 1.3279 | 2.1849 | 0.2427 | -0.0601 | 146 |
| 7 | 1995-11-27 | 2005-07-22 | 2005-08-23 | 2006-08-09 | 1.2888 | 2.3382 | 0.2625 | -0.0691 | 163 |
| 8 | 1996-05-21 | 2006-01-16 | 2006-02-15 | 2007-02-01 | 1.3808 | 1.8912 | 0.2035 | -0.0691 | 207 |
| 9 | 1996-11-13 | 2006-07-11 | 2006-08-10 | 2007-07-27 | 1.3005 | 1.3166 | 0.1580 | -0.0512 | 230 |
| 10 | 1997-05-08 | 2007-01-03 | 2007-02-02 | 2008-01-21 | 1.3682 | 2.0815 | 0.2275 | -0.0512 | 198 |
| 11 | 1997-10-31 | 2007-06-28 | 2007-07-30 | 2008-07-15 | 1.3671 | 2.7409 | 0.1882 | -0.0167 | 78 |
| 12 | 1998-04-27 | 2007-12-21 | 2008-01-22 | 2009-01-07 | 1.4088 | -21.8299 | -0.0013 | -0.0012 | 2 |
| 13 | 1998-10-20 | 2008-06-16 | 2008-07-16 | 2009-07-02 | 1.4459 | -0.2665 | 0.0104 | -0.0287 | 8 |
| 14 | 1999-04-14 | 2008-12-09 | 2009-01-08 | 2009-12-25 | 1.2816 | 1.7670 | 0.1799 | -0.0446 | 114 |
| 15 | 1999-10-07 | 2009-06-03 | 2009-07-03 | 2010-06-21 | 1.3580 | 1.5242 | 0.1893 | -0.0585 | 212 |
| 16 | 2000-03-31 | 2009-11-26 | 2009-12-28 | 2010-12-14 | 1.4469 | 1.0671 | 0.1240 | -0.0585 | 150 |
| 17 | 2000-09-25 | 2010-05-21 | 2010-06-22 | 2011-06-08 | 1.3349 | 1.0960 | 0.1255 | -0.0484 | 164 |
| 18 | 2001-03-20 | 2010-11-15 | 2010-12-15 | 2011-12-01 | 1.4237 | 0.2426 | 0.0400 | -0.0563 | 162 |
| 19 | 2001-09-12 | 2011-05-10 | 2011-06-09 | 2012-05-25 | 1.4900 | 0.9429 | 0.0805 | -0.0426 | 50 |
| 20 | 2002-03-07 | 2011-11-02 | 2011-12-02 | 2012-11-19 | 1.3917 | 1.2267 | 0.1225 | -0.0478 | 24 |
| 21 | 2002-08-30 | 2012-04-26 | 2012-05-28 | 2013-05-14 | 1.5007 | 2.2063 | 0.2369 | -0.0478 | 131 |
| 22 | 2003-02-24 | 2012-10-19 | 2012-11-20 | 2013-11-06 | 1.4860 | 2.1734 | 0.2356 | -0.0574 | 238 |
| 23 | 2003-08-19 | 2013-04-15 | 2013-05-15 | 2014-05-01 | 1.4046 | 0.8107 | 0.1013 | -0.0574 | 236 |
| 24 | 2004-02-11 | 2013-10-08 | 2013-11-07 | 2014-10-24 | 1.3381 | 0.4830 | 0.0669 | -0.0558 | 184 |
| 25 | 2004-08-05 | 2014-04-02 | 2014-05-02 | 2015-04-20 | 1.5174 | 1.1702 | 0.1268 | -0.0414 | 102 |
| 26 | 2005-01-28 | 2014-09-25 | 2014-10-27 | 2015-10-13 | 1.4013 | 0.8976 | 0.0920 | -0.0421 | 35 |
| 27 | 2005-07-25 | 2015-03-20 | 2015-04-21 | 2016-04-06 | 1.4039 | 0.2792 | 0.0377 | -0.0399 | 18 |
| 28 | 2006-01-17 | 2015-09-14 | 2015-10-14 | 2016-09-29 | 1.1924 | 1.3453 | 0.1099 | -0.0342 | 28 |
| 29 | 2006-07-12 | 2016-03-08 | 2016-04-07 | 2017-03-24 | 1.1945 | 0.2969 | 0.0442 | -0.0993 | 29 |
| 30 | 2007-01-04 | 2016-08-31 | 2016-09-30 | 2017-09-18 | 1.1734 | 0.6332 | 0.0780 | -0.0865 | 60 |
| 31 | 2007-06-29 | 2017-02-23 | 2017-03-27 | 2018-03-13 | 1.0889 | 1.6764 | 0.1906 | -0.0867 | 75 |
| 32 | 2007-12-24 | 2017-08-18 | 2017-09-19 | 2018-09-05 | 0.9464 | 1.1373 | 0.1303 | -0.0867 | 148 |
| 33 | 2008-06-17 | 2018-02-12 | 2018-03-14 | 2019-02-28 | 1.0242 | 0.2472 | 0.0395 | -0.0614 | 130 |
| 34 | 2008-12-10 | 2018-08-07 | 2018-09-06 | 2019-08-23 | 1.0866 | 1.0883 | 0.1055 | -0.0591 | 28 |
| 35 | 2009-06-04 | 2019-01-30 | 2019-03-01 | 2020-02-17 | 1.0399 | 3.2521 | 0.2508 | -0.0371 | 26 |
| 36 | 2009-11-27 | 2019-07-25 | 2019-08-26 | 2020-08-11 | 0.9801 | 3.9121 | 0.3062 | -0.0392 | 24 |
| 37 | 2010-05-24 | 2020-01-17 | 2020-02-18 | 2021-02-03 | 1.1593 | 2.3629 | 0.2446 | -0.0574 | 124 |
| 38 | 2010-11-16 | 2020-07-13 | 2020-08-12 | 2021-07-29 | 1.2404 | 0.7952 | 0.1023 | -0.0574 | 233 |
| 39 | 2011-05-11 | 2021-01-05 | 2021-02-04 | 2022-01-21 | 1.2415 | -0.0836 | 0.0112 | -0.0632 | 243 |
| 40 | 2011-11-03 | 2021-06-30 | 2021-07-30 | 2022-07-18 | 1.2987 | -0.1073 | 0.0111 | -0.0632 | 148 |
| 41 | 2012-04-27 | 2021-12-23 | 2022-01-24 | 2023-01-10 | 1.1737 | 0.8947 | 0.0556 | -0.0145 | 29 |
| 42 | 2012-10-22 | 2022-06-17 | 2022-07-19 | 2023-07-05 | 1.1517 | 1.5584 | 0.1341 | -0.0497 | 32 |
| 43 | 2013-04-16 | 2022-12-12 | 2023-01-11 | 2023-12-28 | 1.0904 | 1.8332 | 0.2003 | -0.0779 | 118 |
| 44 | 2013-10-09 | 2023-06-06 | 2023-07-06 | 2024-06-21 | 1.1322 | 1.8186 | 0.2022 | -0.0779 | 185 |
| 45 | 2014-04-03 | 2023-11-29 | 2023-12-29 | 2024-12-16 | 1.0731 | 1.8342 | 0.2073 | -0.0646 | 220 |
| 46 | 2014-09-26 | 2024-05-23 | 2024-06-24 | 2025-06-10 | 1.2036 | 1.1148 | 0.1249 | -0.0646 | 186 |
| 47 | 2015-03-23 | 2024-11-15 | 2024-12-17 | 2025-12-03 | 1.1557 | 1.9609 | 0.2033 | -0.0499 | 115 |
| 48 | 2015-09-15 | 2025-05-12 | 2025-06-11 | 2026-05-28 | 1.1903 | 2.8969 | 0.3197 | -0.0382 | 160 |

### 2.2 Design A (non-overlapping test windows) -- fold table

| Fold | Train Start | Train End | Test Start | Test End | Train Sharpe | Test Sharpe | Test Ann. Ret. | Test Max DD | Test Trades |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1993-01-01 | 2002-08-29 | 2002-09-30 | 2003-09-16 | 1.2280 | 2.5550 | 0.2376 | -0.0307 | 94 |
| 2 | 1993-12-21 | 2003-08-18 | 2003-09-17 | 2004-09-02 | 1.3993 | 0.3027 | 0.0486 | -0.0797 | 211 |
| 3 | 1994-12-08 | 2004-08-04 | 2004-09-03 | 2005-08-22 | 1.4240 | 1.9494 | 0.2102 | -0.0601 | 146 |
| 4 | 1995-11-27 | 2005-07-22 | 2005-08-23 | 2006-08-09 | 1.2888 | 2.3382 | 0.2625 | -0.0691 | 163 |
| 5 | 1996-11-13 | 2006-07-11 | 2006-08-10 | 2007-07-27 | 1.3005 | 1.3166 | 0.1580 | -0.0512 | 230 |
| 6 | 1997-10-31 | 2007-06-28 | 2007-07-30 | 2008-07-15 | 1.3671 | 2.7409 | 0.1882 | -0.0167 | 78 |
| 7 | 1998-10-20 | 2008-06-16 | 2008-07-16 | 2009-07-02 | 1.4459 | -0.2665 | 0.0104 | -0.0287 | 8 |
| 8 | 1999-10-07 | 2009-06-03 | 2009-07-03 | 2010-06-21 | 1.3580 | 1.5242 | 0.1893 | -0.0585 | 212 |
| 9 | 2000-09-25 | 2010-05-21 | 2010-06-22 | 2011-06-08 | 1.3349 | 1.0960 | 0.1255 | -0.0484 | 164 |
| 10 | 2001-09-12 | 2011-05-10 | 2011-06-09 | 2012-05-25 | 1.4900 | 0.9429 | 0.0805 | -0.0426 | 50 |
| 11 | 2002-08-30 | 2012-04-26 | 2012-05-28 | 2013-05-14 | 1.5007 | 2.2063 | 0.2369 | -0.0478 | 131 |
| 12 | 2003-08-19 | 2013-04-15 | 2013-05-15 | 2014-05-01 | 1.4046 | 0.8107 | 0.1013 | -0.0574 | 236 |
| 13 | 2004-08-05 | 2014-04-02 | 2014-05-02 | 2015-04-20 | 1.5174 | 1.1702 | 0.1268 | -0.0414 | 102 |
| 14 | 2005-07-25 | 2015-03-20 | 2015-04-21 | 2016-04-06 | 1.4039 | 0.2792 | 0.0377 | -0.0399 | 18 |
| 15 | 2006-07-12 | 2016-03-08 | 2016-04-07 | 2017-03-24 | 1.1945 | 0.2969 | 0.0442 | -0.0993 | 29 |
| 16 | 2007-06-29 | 2017-02-23 | 2017-03-27 | 2018-03-13 | 1.0889 | 1.6764 | 0.1906 | -0.0867 | 75 |
| 17 | 2008-06-17 | 2018-02-12 | 2018-03-14 | 2019-02-28 | 1.0242 | 0.2472 | 0.0395 | -0.0614 | 130 |
| 18 | 2009-06-04 | 2019-01-30 | 2019-03-01 | 2020-02-17 | 1.0399 | 3.2521 | 0.2508 | -0.0371 | 26 |
| 19 | 2010-05-24 | 2020-01-17 | 2020-02-18 | 2021-02-03 | 1.1593 | 2.3629 | 0.2446 | -0.0574 | 124 |
| 20 | 2011-05-11 | 2021-01-05 | 2021-02-04 | 2022-01-21 | 1.2415 | -0.0836 | 0.0112 | -0.0632 | 243 |
| 21 | 2012-04-27 | 2021-12-23 | 2022-01-24 | 2023-01-10 | 1.1737 | 0.8947 | 0.0556 | -0.0145 | 29 |
| 22 | 2013-04-16 | 2022-12-12 | 2023-01-11 | 2023-12-28 | 1.0904 | 1.8332 | 0.2003 | -0.0779 | 118 |
| 23 | 2014-04-03 | 2023-11-29 | 2023-12-29 | 2024-12-16 | 1.0731 | 1.8342 | 0.2073 | -0.0646 | 220 |
| 24 | 2015-03-23 | 2024-11-15 | 2024-12-17 | 2025-12-03 | 1.1557 | 1.9609 | 0.2033 | -0.0499 | 115 |

### 2.3 Design B (literal embargo, informational) -- fold table

| Fold | Train Start | Train End | Test Start | Test End | Train Sharpe | Test Sharpe | Test Ann. Ret. | Test Max DD | Test Trades |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1993-01-01 | 2002-08-29 | 2002-09-30 | 2003-09-16 | 1.2280 | 2.5550 | 0.2376 | -0.0307 | 94 |
| 2 | 2003-10-16 | 2013-06-12 | 2013-07-12 | 2014-06-30 | 1.3726 | 1.3182 | 0.1431 | -0.0558 | 237 |
| 3 | 2014-07-30 | 2024-03-26 | 2024-04-25 | 2025-04-11 | 1.1815 | 1.0301 | 0.1215 | -0.0646 | 220 |

Design B is informational: with a 10-year training window and the configured embargo the fold count is 3, which is too few to form a stable gate table. The fold count is published and the gate table is not forced.

## 3. Delta (published design vs Design A)

- Fold count: published 48, Design A 24 (delta -24)
- WF mean OOS Sharpe: published 0.947307, Design A 1.385035 (delta 0.437727)
- Gate-1 margin (>= 0.9): published +0.047307, Design A +0.485035 (delta +0.437727)
- Gate-1 outcome changes under Design A: **NO**
- Published verdict survives Design A: **YES**

## 4. Gate tables

Thresholds are the pre-registered ones (published record gate table and the AGENTS.md promotion gate: WF mean OOS Sharpe >= 0.9, positive fold rate >= 50%, > 100 pooled OOS trades). The SMA-plateau gate of the published record is not fold-dependent and is not re-evaluated here.

### Published design
- wf_mean_oos_sharpe: threshold 0.9, observed 0.947307, margin 0.047307, status PASS
- positive_fold_rate: threshold 0.5, observed 0.916667, margin 0.416667, status PASS
- pooled_oos_trades: threshold 100, observed 6013, margin 5913.000000, status PASS

### Design A
- wf_mean_oos_sharpe: threshold 0.9, observed 1.385035, margin 0.485035, status PASS
- positive_fold_rate: threshold 0.5, observed 0.916667, margin 0.416667, status PASS
- pooled_oos_trades: threshold 100, observed 2952, margin 2852.000000, status PASS

### Design B
- wf_mean_oos_sharpe: threshold 0.9, observed 1.634397, margin 0.734397, status PASS
- positive_fold_rate: threshold 0.5, observed 1.000000, margin 0.500000, status PASS
- pooled_oos_trades: threshold 100, observed 551, margin 451.000000, status PASS

## 5. Independence diagnostic

| Design | Folds | Mean consecutive test-window overlap (days) | Max pairwise-disjoint test windows |
|---|---|---|---|
| Published design | 48 | 175.0 | 24 |
| Design A (non-overlapping) | 24 | 0.0 | 24 |
| Design B (literal embargo) | 3 | 0.0 | 3 |

The published design's test windows overlap, so its folds are not independent observations; Design A makes them pairwise disjoint, and its disjoint count equals its fold count.

## 6. Checks

- [published_record_resolved_by_content]: PASS (observed: research/experiments/tsmomentum_regime_filter_wf_001.md, expected: exactly one published walk-forward record)
- [cache_only_path_built]: PASS (observed: 8492 sessions, 7 symbols, expected: non-empty path)
- [reproduces_published_walk_forward_aggregate]: PASS (observed: n_folds=48 (published 48); mean_test_sharpe=0.9473074720246092 (published 0.9473); std_test_sharpe=3.4797702418403893 (published 3.4798); median_test_sharpe=1.29329878363231 (published 1.2933); min_test_sharpe=-21.829879416796786 (published -21.8299); max_test_sharpe=3.9121052879675915 (published 3.9121); pct_positive_sharpe=0.9166666666666666 (published 91.7%); mean_test_ann_return=0.1471459015552229 (published 14.71%); mean_test_max_dd=-0.05407695492453209 (published -5.41%); mean_test_trades=125.27083333333333 (published 125.3); total_test_trades=6013 (published 6013), expected: published aggregate statistics)
- [reproduces_published_walk_forward_fold_table]: PASS (observed: 48 folds compared, expected: every published fold reproduced)
- [published_design_has_test_window_overlap]: PASS (observed: 175.0, expected: > 0 days)
- [design_a_test_windows_pairwise_disjoint]: PASS (observed: overlap=0.0, disjoint=24, folds=24, expected: overlap == 0 and disjoint == folds)
- [published_gate_thresholds_consumed_from_record]: PASS (observed: {'wf_mean_oos_sharpe_min': 0.9, 'positive_fold_rate_min': 0.5}, expected: 0.9 / 0.5 as published)
- [data_unchanged]: PASS
- [config_unchanged]: PASS
- [committed_artifacts_unchanged]: PASS

## 7. Reproduction commands

```bash
python research/tsmomentum_walkforward_embargo_audit.py
python -m pytest -q tests/test_tsmomentum_walkforward_embargo_audit.py
python -m pytest -q
git status --porcelain data/
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
      "expected": "exactly one published walk-forward record",
      "name": "published_record_resolved_by_content",
      "observed": "research/experiments/tsmomentum_regime_filter_wf_001.md",
      "pass": true
    },
    {
      "expected": "non-empty path",
      "name": "cache_only_path_built",
      "observed": "8492 sessions, 7 symbols",
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
      "expected": "> 0 days",
      "name": "published_design_has_test_window_overlap",
      "observed": 175.0,
      "pass": true
    },
    {
      "expected": "overlap == 0 and disjoint == folds",
      "name": "design_a_test_windows_pairwise_disjoint",
      "observed": "overlap=0.0, disjoint=24, folds=24",
      "pass": true
    },
    {
      "expected": "0.9 / 0.5 as published",
      "name": "published_gate_thresholds_consumed_from_record",
      "observed": "{'wf_mean_oos_sharpe_min': 0.9, 'positive_fold_rate_min': 0.5}",
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
  "cycle": "910",
  "data_source": "committed parquet cache in data/raw/ (fetcher never called)",
  "delta_published_vs_design_a": {
    "fold_count_delta": -24,
    "fold_count_design_a": 24,
    "fold_count_published": 48,
    "gate1_margin_delta": 0.4377272165095111,
    "gate1_margin_design_a": 0.48503468853412024,
    "gate1_margin_published": 0.047307472024609165,
    "gate1_status_design_a": "PASS",
    "gate1_status_published": "PASS",
    "gate1_threshold": 0.9,
    "gate_outcome_changes": false,
    "mean_sharpe_delta": 0.4377272165095111,
    "mean_sharpe_design_a": 1.3850346885341203,
    "mean_sharpe_published": 0.9473074720246092,
    "verdict_survives": true
  },
  "design_a_gate1_status": "PASS",
  "design_a_nonoverlapping": {
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
        "fold": 3,
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
        "fold": 4,
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
        "fold": 5,
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
        "fold": 6,
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
        "fold": 7,
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
        "fold": 8,
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
        "fold": 9,
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
        "fold": 10,
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
        "fold": 11,
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
        "fold": 12,
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
        "fold": 13,
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
        "fold": 14,
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
        "fold": 15,
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
        "fold": 16,
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
        "fold": 17,
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
        "fold": 18,
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
        "fold": 19,
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
        "fold": 20,
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
        "fold": 21,
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
        "fold": 22,
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
        "fold": 23,
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
        "fold": 24,
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
      }
    ],
    "gates": [
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
    "summary": {
      "max_test_sharpe": 3.252075026352224,
      "mean_test_ann_return": 0.14419274385660427,
      "mean_test_max_dd": -0.05350695964480131,
      "mean_test_sharpe": 1.3850346885341203,
      "mean_test_sharpe_canonical": 1.5458675784822986,
      "mean_test_trades": 123.0,
      "median_test_sharpe": 1.4204258675176074,
      "min_test_sharpe": -0.2665263717842321,
      "n_folds": 24,
      "pct_positive_sharpe": 0.9166666666666666,
      "std_test_sharpe": 0.9566051183437652,
      "total_test_trades": 2952
    }
  },
  "design_b_embargo_literal": {
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
        "test_ann_return": 0.14305796109262658,
        "test_end": "2014-06-30",
        "test_max_dd": -0.0558226250432412,
        "test_sharpe": 1.3181503658555487,
        "test_sharpe_canonical": 1.4791497342839528,
        "test_start": "2013-07-12",
        "test_trades": 237,
        "train_end": "2013-06-12",
        "train_sharpe": 1.3725934520619143,
        "train_start": "2003-10-16"
      },
      {
        "fold": 3,
        "test_ann_return": 0.12153334017495587,
        "test_end": "2025-04-11",
        "test_max_dd": -0.06462135007497727,
        "test_sharpe": 1.0300822239244285,
        "test_sharpe_canonical": 1.2130752904503939,
        "test_start": "2024-04-25",
        "test_trades": 220,
        "train_end": "2024-03-26",
        "train_sharpe": 1.1814592066717158,
        "train_start": "2014-07-30"
      }
    ],
    "gates": [
      {
        "gate": "wf_mean_oos_sharpe",
        "margin": 0.7343966445473061,
        "observed": 1.6343966445473062,
        "status": "PASS",
        "threshold": 0.9
      },
      {
        "gate": "positive_fold_rate",
        "margin": 0.5,
        "observed": 1.0,
        "status": "PASS",
        "threshold": 0.5
      },
      {
        "gate": "pooled_oos_trades",
        "margin": 451.0,
        "observed": 551,
        "status": "PASS",
        "threshold": 100
      }
    ],
    "independence": {
      "max_disjoint_test_windows": 3,
      "mean_consecutive_overlap_days": 0.0
    },
    "summary": {
      "max_test_sharpe": 2.554957343861941,
      "mean_test_ann_return": 0.1674130166365043,
      "mean_test_max_dd": -0.05036910133653175,
      "mean_test_sharpe": 1.6343966445473062,
      "mean_test_sharpe_canonical": 1.746171560098773,
      "mean_test_trades": 183.66666666666666,
      "median_test_sharpe": 1.3181503658555487,
      "min_test_sharpe": 1.0300822239244285,
      "n_folds": 3,
      "pct_positive_sharpe": 1.0,
      "std_test_sharpe": 0.810135676563438,
      "total_test_trades": 551
    }
  },
  "overall": "PASS",
  "point_in_time": "signals use only data available at formation (weights shifted one day), the SPY SMA is computed point-in-time, and the overlay/cost model are applied on the same continuously computed path for every design",
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
  "published_record_path": "research/experiments/tsmomentum_regime_filter_wf_001.md",
  "published_verdict": "Credible Candidate",
  "read_only": {
    "committed_artifacts_unchanged": true,
    "config_unchanged": true,
    "data_unchanged": true
  },
  "rf_annual": 0.02,
  "slippage_bps": 2.0
}
```
