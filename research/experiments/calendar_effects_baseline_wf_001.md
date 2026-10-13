# Cycle 18: Calendar/Rebalancing Effects Evaluation (calendar_effects_001)

**Generated:** 2026-10-13  |  **Code revision:** a95433b
**Config SHA-256[:12]:** ea4e13ef7c34
**History:** 2000-05-26 → 2026-10-09 (8,482 trading days)
**Universe:** SPY, QQQ, IWM (n=3)

## Data Integrity (pre-registered)
| Symbol | Rows | Start | End |
|---|---|---|---|
| SPY | 8482 | 1993-01-29 | 2026-10-09 |
| QQQ | 6940 | 1999-03-10 | 2026-10-09 |
| IWM | 6632 | 2000-05-26 | 2026-10-09 |
| Common calendar | 8,482 | 1993-01-29 | 2026-10-09 |
| Aligned frame hash | e6742a181cf525e5 | | |
| Config hash | ea4e13ef7c34 | | |

## Grid (pre-registered)
pre_days in [1, 2, 3], post_days in [1, 2, 3, 5, 7, 10] → 18 configs (baseline (1,3))

## Walk-forward folds (33)
Fold 1: train 2000-05-26→2010-01-21, test 2010-02-22→2011-02-08, OOS Sharpe=1.5504
Fold 2: train 2000-11-20→2010-07-16, test 2010-08-17→2011-08-03, OOS Sharpe=1.2893
Fold 3: train 2001-05-15→2011-01-10, test 2011-02-09→2012-01-26, OOS Sharpe=-0.4505
Fold 4: train 2001-11-07→2011-07-05, test 2011-08-04→2012-07-20, OOS Sharpe=-0.0112
Fold 5: train 2002-05-02→2011-12-28, test 2012-01-27→2013-01-14, OOS Sharpe=1.0195
Fold 6: train 2002-10-25→2012-06-21, test 2012-07-23→2013-07-09, OOS Sharpe=0.9832
Fold 7: train 2003-04-21→2012-12-14, test 2013-01-15→2014-01-01, OOS Sharpe=0.0192
Fold 8: train 2003-10-14→2013-06-10, test 2013-07-10→2014-06-26, OOS Sharpe=-0.3359
Fold 9: train 2004-04-07→2013-12-03, test 2014-01-02→2014-12-19, OOS Sharpe=-0.7054
Fold 10: train 2004-09-30→2014-05-28, test 2014-06-27→2015-06-15, OOS Sharpe=-1.5240
Fold 11: train 2005-03-25→2014-11-20, test 2014-12-22→2015-12-08, OOS Sharpe=-0.7259
Fold 12: train 2005-09-19→2015-05-15, test 2015-06-16→2016-06-01, OOS Sharpe=-0.3296
Fold 13: train 2006-03-14→2015-11-09, test 2015-12-09→2016-11-24, OOS Sharpe=-0.8644
Fold 14: train 2006-09-06→2016-05-03, test 2016-06-02→2017-05-19, OOS Sharpe=-0.5073
Fold 15: train 2007-03-01→2016-10-26, test 2016-11-25→2017-11-13, OOS Sharpe=-0.0635
Fold 16: train 2007-08-24→2017-04-20, test 2017-05-22→2018-05-08, OOS Sharpe=-0.8228
Fold 17: train 2008-02-18→2017-10-13, test 2017-11-14→2018-10-31, OOS Sharpe=-0.5441
Fold 18: train 2008-08-12→2018-04-09, test 2018-05-09→2019-04-25, OOS Sharpe=1.1516
Fold 19: train 2009-02-04→2018-10-02, test 2018-11-01→2019-10-18, OOS Sharpe=0.0959
Fold 20: train 2009-07-30→2019-03-27, test 2019-04-26→2020-04-13, OOS Sharpe=-0.4263
Fold 21: train 2010-01-22→2019-09-19, test 2019-10-21→2020-10-06, OOS Sharpe=0.5735
Fold 22: train 2010-07-19→2020-03-13, test 2020-04-14→2021-03-31, OOS Sharpe=1.5428
Fold 23: train 2011-01-11→2020-09-07, test 2020-10-07→2021-09-23, OOS Sharpe=0.8165
Fold 24: train 2011-07-06→2021-03-02, test 2021-04-01→2022-03-18, OOS Sharpe=-0.7493
Fold 25: train 2011-12-29→2021-08-25, test 2021-09-24→2022-09-12, OOS Sharpe=-0.6710
Fold 26: train 2012-06-22→2022-02-17, test 2022-03-21→2023-03-07, OOS Sharpe=0.1705
Fold 27: train 2012-12-17→2022-08-12, test 2022-09-13→2023-08-30, OOS Sharpe=0.1737
Fold 28: train 2013-06-11→2023-02-06, test 2023-03-08→2024-02-22, OOS Sharpe=-0.5938
Fold 29: train 2013-12-04→2023-08-01, test 2023-08-31→2024-08-16, OOS Sharpe=-0.8170
Fold 30: train 2014-05-29→2024-01-24, test 2024-02-23→2025-02-10, OOS Sharpe=-0.8092
Fold 31: train 2014-11-21→2024-07-18, test 2024-08-19→2025-08-05, OOS Sharpe=-0.3708
Fold 32: train 2015-05-18→2025-01-10, test 2025-02-11→2026-01-28, OOS Sharpe=0.0172
Fold 33: train 2015-11-10→2025-07-07, test 2025-08-06→2026-07-23, OOS Sharpe=1.0793

## Promotion gates
1. WF mean OOS Sharpe >= 0.9: -0.0254 (FAIL)
2. Positive fold rate >= 50%: 42.4% (FAIL)
3. Pooled OOS trades > 100: 761 (PASS)
4. Plateau (>=2 of 3 pre_days at post_days=3): 1/3 (FAIL)

**FINAL VERDICT:** Rejected/Failed

## Artifacts
| Artifact | Path |
|---|---|
| Weights | `data/processed/weights_calendar_effects_001.parquet` |
| Simulation | `data/processed/simulation_calendar_effects_001.parquet` |
| Trades | `data/processed/trades_calendar_effects_001.parquet` |
| Report | `research/experiments/calendar_effects_baseline_wf_001.md` |
