# Sector Rotation Long-Sample Feasibility (Cycle 869)

Candidate `sectorrotation_001` (frozen config `config/sectorrotation_candidate_001.yaml`) evaluated on its own long sample, in the pattern of `research/promotion_feasibility_backtest.py`.

- code revision: `828f9f0`
- report generator: `research/sectorrotation_long_sample_feasibility.py`
- raw cache SHA-256 identical before/after: True

## Verdict

- long-sample net-of-cost Sharpe (canonical `arithmetic_annualized_rf0`, config-faithful month-end rebalance, invested sample): **0.472367** (backtest-baseline scale 0.284499)
- PSR vs the candidate's own promotion threshold 0.9: **0.006618** (PSR vs the incumbent baseline 1.4178: 0.000000)
- trade days (invested sample): **175** across 321 month-end rebalances; pooled out-of-sample trades over the 36 pre-registered folds: **215** (110 unique sessions)
- repository promotion-gate table on the long sample: **NO-GO** (failed: ['full_period_sharpe', 'max_drawdown', 'psr']; PSR zone below_grey)
- candidate's own pre-registered gates: walk-forward mean OOS Sharpe 0.847243 (>= 0.9 required), positive fold rate 0.9167 (>= 0.5), pooled OOS trades 215 (> 100), plateau 2/3 lookbacks within 10% -> failed gates ['wf_mean_oos_sharpe']
- excess over the 1/N equal-weight benchmark on the invested sample: +0.003544 Sharpe, +0.0156 pp annualized, at 2.9961x annualized turnover
- the 36 pre-registered fold windows cover 2008-09-17..2026-07-30 and exclude the 2448 sessions before 2008-09-16 (max drawdown there -0.363222); the fold windows and the long sample therefore measure different periods
- label: **rejected/failed (pre-registered falsification condition met)**

## 1. Sample definition and data integrity

```json
{
  "candidate_id": "sectorrotation_001",
  "start_date": "1998-12-22",
  "end_date": "2026-10-08",
  "session_count": 6991,
  "universe": [
    "XLB",
    "XLE",
    "XLF",
    "XLI",
    "XLK",
    "XLP",
    "XLU",
    "XLV",
    "XLY"
  ],
  "lookback": 252,
  "skip": 21,
  "top_fraction": 0.5,
  "rebalance_freq": "monthly",
  "signal_lag_days": 1,
  "cost_model": {
    "commission_bps": 1.0,
    "slippage_bps": 2.0,
    "total_round_trip_bps": 3.0
  },
  "data_source": "committed raw cache (data/raw/*.parquet), no network",
  "aligned_frame_rows": 6991,
  "aligned_frame_hash": "5e2d48e6579a53cd4ed43412f1a95119e8f32ad5633c38f7dec3d1259e909ee1",
  "pre_registered_aligned_frame_hash": "5e2d48e6579a53cd",
  "sha256_raw_files": {
    "XLB": "465b9a7b6c7848690c347eb3a9229e133b01ebf638642e12c6c75070e14cee12",
    "XLE": "408b2806f7dbde65bdf3a8e0cd5673406945a791f77b5e44683cf855e08d2ff6",
    "XLF": "2f8eeb83b2024b693fc55c1dba57f23e02932af7c4bc2216ad714fc2539d8891",
    "XLI": "176eaa15a62526ec729dbcb5a8ceac50510b0566e87f7ac1b155cfa39f06c480",
    "XLK": "b66776c5c1c70885794c0c912bad0bff8cebe775d978b113af9bc5c2561ca6ad",
    "XLP": "d1ac5528a51c54708fc60feff3c9553d60c863dbdab7d177519bb000e38d7211",
    "XLU": "c9550ef0e461368e96c4321b320926d397f066281210d8cd4f60b08a56a0cd76",
    "XLV": "bcf7029ba61bac58eb747d8edc6fef907a35e31f91ab246a6c845433ccf86bab",
    "XLY": "7a64cd50a03d5d70d29418908a1271a9df47bfda1e50da9def5d868908ff4ab6"
  },
  "per_symbol": {
    "XLB": {
      "rows": 6991,
      "first": "1998-12-22",
      "last": "2026-10-08",
      "close_nan": 0,
      "duplicate_dates": 0
    },
    "XLE": {
      "rows": 6991,
      "first": "1998-12-22",
      "last": "2026-10-08",
      "close_nan": 0,
      "duplicate_dates": 0
    },
    "XLF": {
      "rows": 6991,
      "first": "1998-12-22",
      "last": "2026-10-08",
      "close_nan": 0,
      "duplicate_dates": 0
    },
    "XLI": {
      "rows": 6991,
      "first": "1998-12-22",
      "last": "2026-10-08",
      "close_nan": 0,
      "duplicate_dates": 0
    },
    "XLK": {
      "rows": 6991,
      "first": "1998-12-22",
      "last": "2026-10-08",
      "close_nan": 0,
      "duplicate_dates": 0
    },
    "XLP": {
      "rows": 6991,
      "first": "1998-12-22",
      "last": "2026-10-08",
      "close_nan": 0,
      "duplicate_dates": 0
    },
    "XLU": {
      "rows": 6991,
      "first": "1998-12-22",
      "last": "2026-10-08",
      "close_nan": 0,
      "duplicate_dates": 0
    },
    "XLV": {
      "rows": 6991,
      "first": "1998-12-22",
      "last": "2026-10-08",
      "close_nan": 0,
      "duplicate_dates": 0
    },
    "XLY": {
      "rows": 6991,
      "first": "1998-12-22",
      "last": "2026-10-08",
      "close_nan": 0,
      "duplicate_dates": 0
    }
  }
}
```

- The aligned Close frame reproduces the pre-registered content hash `5e2d48e6579a53cd` recorded in `research/hypotheses/sectorrotation_001.md` (freeze time 2026-10-12): the cached data has not changed since pre-registration.
- The cache ends 2026-10-08 for the 9 sector ETFs, i.e. 6991 sessions of the 9-sector union calendar. The core cache (SPY/QQQ/.../EEM) reaches 2026-10-16; the sector universe is 6 sessions behind. No data was fetched or written (`data/` is byte-identical, see the checks).
- The first date with a valid 9-asset momentum cross-section is 2000-01-24 (pre-registered 2000-01-24); the first session with positions is 2000-02-01. The invested sample therefore has 6712 sessions and the full aligned sample 6991.

## 2. Execution path: the engine does not implement the frozen rebalance schedule

`src/backtest/engine.py:run_backtest` accepts a `rebalance_freq` argument and never uses it: `build_weights` re-ranks the universe **every session**, so positions can change between month-ends. The frozen configuration specifies month-end rebalancing with a 1-day signal lag, so the config-faithful path is implemented in this script (`build_monthly_weights`) and the engine path is reported next to it as a deviation measurement, using exactly the code path of `research/promotion_feasibility_backtest.py`.

- config-faithful (month-end rebalance): 321 rebalances, 175 trade days, annualized turnover 2.9961
- engine default (daily re-rank): 1088 trade days, annualized turnover 16.4849, Sharpe 0.471379

## 3. Long-sample results (primary: config-faithful month-end rebalance)

```json
{
  "sessions": 6712,
  "start_date": "2000-02-01",
  "end_date": "2026-10-08",
  "sharpe_canonical": 0.4723674832996954,
  "sharpe_backtest_scale": 0.2844989916183757,
  "cagr": 0.07119975301191817,
  "annualized_vol": 0.17996462033368832,
  "total_return": 5.2459346280633605,
  "max_drawdown": -0.4715783445216646,
  "rolling_63d_sharpe": 1.7651632775694415,
  "rolling_63d_max_dd": -0.0334805595055111,
  "trade_days": 175,
  "turnover_total": 79.8,
  "annualized_turnover": 2.9960667461263406,
  "avg_exposure": 1.0,
  "profit_factor": 1.0921660501827901,
  "best_day": 0.11864193190428868,
  "worst_day": -0.11193548012032087,
  "cost_drag_total": 0.023940000000000003
}
```

### Variant comparison

```json
{
  "monthly_rebalance_invested_sample": {
    "sessions": 6712,
    "start_date": "2000-02-01",
    "end_date": "2026-10-08",
    "sharpe_canonical": 0.4723674832996954,
    "sharpe_backtest_scale": 0.2844989916183757,
    "cagr": 0.07119975301191817,
    "annualized_vol": 0.17996462033368832,
    "total_return": 5.2459346280633605,
    "max_drawdown": -0.4715783445216646,
    "rolling_63d_sharpe": 1.7651632775694415,
    "rolling_63d_max_dd": -0.0334805595055111,
    "trade_days": 175,
    "turnover_total": 79.8,
    "annualized_turnover": 2.9960667461263406,
    "avg_exposure": 1.0,
    "profit_factor": 1.0921660501827901,
    "best_day": 0.11864193190428868,
    "worst_day": -0.11193548012032087,
    "cost_drag_total": 0.023940000000000003
  },
  "monthly_rebalance_full_sample": {
    "sessions": 6991,
    "start_date": "1998-12-22",
    "end_date": "2026-10-08",
    "sharpe_canonical": 0.4628389866272501,
    "sharpe_backtest_scale": 0.27369618971815296,
    "cagr": 0.06826347539183986,
    "annualized_vol": 0.17633959552575668,
    "total_return": 5.2459346280633605,
    "max_drawdown": -0.4715783445216646,
    "rolling_63d_sharpe": 1.7651632775694415,
    "rolling_63d_max_dd": -0.0334805595055111,
    "trade_days": 175,
    "turnover_total": 79.80000000000001,
    "annualized_turnover": 2.8764983550278935,
    "avg_exposure": 0.9600915462737806,
    "profit_factor": 1.0921660501827901,
    "best_day": 0.11864193190428868,
    "worst_day": -0.11193548012032087,
    "cost_drag_total": 0.023940000000000003
  },
  "engine_daily_rerank_invested_sample": {
    "sessions": 6717,
    "start_date": "2000-01-25",
    "end_date": "2026-10-08",
    "sharpe_canonical": 0.4713788457490444,
    "sharpe_backtest_scale": 0.28327836441435106,
    "cagr": 0.07070308446427842,
    "annualized_vol": 0.17898678767473766,
    "total_return": 5.177625324089563,
    "max_drawdown": -0.4846834162724222,
    "rolling_63d_sharpe": 1.856416829543253,
    "rolling_63d_max_dd": -0.0334805595055111,
    "trade_days": 1088,
    "turnover_total": 439.4,
    "annualized_turnover": 16.484859312192942,
    "avg_exposure": 1.0,
    "profit_factor": 1.0967061749149056,
    "best_day": 0.11864193190428868,
    "worst_day": -0.11666586169874746,
    "cost_drag_total": 0.13182000000000002
  },
  "engine_daily_rerank_full_sample": {
    "sessions": 6991,
    "start_date": "1998-12-22",
    "end_date": "2026-10-08",
    "sharpe_canonical": 0.46204244540209743,
    "sharpe_backtest_scale": 0.27267597736950505,
    "cagr": 0.06784010379631011,
    "annualized_vol": 0.175446712460048,
    "total_return": 5.177625324089563,
    "max_drawdown": -0.4846834162724222,
    "rolling_63d_sharpe": 1.856416829543253,
    "rolling_63d_max_dd": -0.0334805595055111,
    "trade_days": 1088,
    "turnover_total": 439.4,
    "annualized_turnover": 15.83876412530396,
    "avg_exposure": 0.9608067515376914,
    "profit_factor": 1.0967061749149056,
    "best_day": 0.11864193190428868,
    "worst_day": -0.11666586169874746,
    "cost_drag_total": 0.13182000000000002
  },
  "benchmark_1_over_9_equal_weight": {
    "sessions": 6712,
    "start_date": "2000-02-01",
    "end_date": "2026-10-08",
    "sharpe_canonical": 0.4688235700892847,
    "sharpe_backtest_scale": 0.2809274003752089,
    "cagr": 0.07104385616636,
    "annualized_vol": 0.1816976774005861,
    "total_return": 5.221768571324176,
    "max_drawdown": -0.5392223772740949,
    "rolling_63d_sharpe": 0.10347212669832259,
    "rolling_63d_max_dd": -0.05442402347190911,
    "trade_days": 0,
    "turnover_total": 0.0,
    "annualized_turnover": 0.0,
    "avg_exposure": 1.0,
    "profit_factor": 1.0937343726249082,
    "best_day": 0.11194064216345244,
    "worst_day": -0.1157257560155213,
    "cost_drag_total": 0.0
  }
}
```

The full-sample rows keep the pre-warmup sessions (zero exposure, zero return); the invested-sample rows start at the first session with a position. The gate evaluation uses the invested sample of the config-faithful path.

## 4. Pre-registered chronological splits

```json
{
  "train": {
    "sessions": 2774,
    "start_date": "1998-12-22",
    "end_date": "2009-12-31",
    "sharpe_canonical": 0.14753167829883593,
    "sharpe_backtest_scale": -0.05247981046318692,
    "cagr": 0.010079456892739813,
    "annualized_vol": 0.1890354218070045,
    "total_return": 0.1167230770656098,
    "max_drawdown": -0.4715783445216646,
    "rolling_63d_sharpe": 2.849745748392941,
    "rolling_63d_max_dd": -0.045922836344069906,
    "trade_days": 70,
    "turnover_total": 31.0,
    "annualized_turnover": 2.8161499639509735,
    "avg_exposure": 0.8994232155731795,
    "profit_factor": 1.0294164255407658,
    "best_day": 0.11864193190428868,
    "worst_day": -0.09502517655253238,
    "cost_drag_total": 0.009300000000000003
  },
  "validation": {
    "sessions": 2013,
    "start_date": "2010-01-04",
    "end_date": "2017-12-29",
    "sharpe_canonical": 0.7204303177287158,
    "sharpe_backtest_scale": 0.5449530022365507,
    "cagr": 0.10264480282524646,
    "annualized_vol": 0.15165491792147678,
    "total_return": 1.1826288550750967,
    "max_drawdown": -0.2263713251565581,
    "rolling_63d_sharpe": 4.354669827684103,
    "rolling_63d_max_dd": -0.017420980783282136,
    "trade_days": 45,
    "turnover_total": 21.6,
    "annualized_turnover": 2.704023845007452,
    "avg_exposure": 1.0,
    "profit_factor": 1.141460831147449,
    "best_day": 0.05173360228797952,
    "worst_day": -0.06854122928205193,
    "cost_drag_total": 0.0064800000000000005
  },
  "test": {
    "sessions": 2204,
    "start_date": "2018-01-02",
    "end_date": "2026-10-08",
    "sharpe_canonical": 0.6861681662906355,
    "sharpe_backtest_scale": 0.5179274065272281,
    "cagr": 0.11359319523325007,
    "annualized_vol": 0.18070716871463674,
    "total_return": 1.5625482481020767,
    "max_drawdown": -0.34132006501598744,
    "rolling_63d_sharpe": 1.7651632775694415,
    "rolling_63d_max_dd": -0.0334805595055111,
    "trade_days": 60,
    "turnover_total": 27.200000000000003,
    "annualized_turnover": 3.1099818511796737,
    "avg_exposure": 1.0,
    "profit_factor": 1.1390342093360575,
    "best_day": 0.09624423003235447,
    "worst_day": -0.11193548012032087,
    "cost_drag_total": 0.00816
  }
}
```

## 5. Pre-registered walk-forward (36 folds, fixed parameters)

Splits are generated with `src/evaluation/walkforward.py:generate_walkforward_splits` (10y train / 12m test / 6m step, purge 21d, embargo 21d) from 1998-12-22; 36 folds were generated (pre-registered: 36). Parameters are fixed across folds, so the fold test windows are slices of one continuously computed point-in-time strategy path rather than re-fitted per fold.

```json
{
  "n_folds": 36,
  "mean_test_sharpe": 0.8472432934255264,
  "median_test_sharpe": 0.7396059140520563,
  "min_test_sharpe": -0.2517527273410225,
  "max_test_sharpe": 2.3267979679635586,
  "positive_fold_rate": 0.9166666666666666,
  "pooled_oos_trades_sum_over_folds": 215,
  "unique_traded_sessions_across_folds": 110,
  "mean_test_cagr": 0.11692128470589583,
  "worst_test_max_dd": -0.3811307207365453
}
```

### Candidate's own pre-registered gates

```json
{
  "wf_mean_oos_sharpe": {
    "value": 0.8472432934255264,
    "threshold": 0.9,
    "comparison": "gte",
    "pass": false,
    "status": "evaluated"
  },
  "positive_fold_rate": {
    "value": 0.9166666666666666,
    "threshold": 0.5,
    "comparison": "gte",
    "pass": true,
    "status": "evaluated"
  },
  "pooled_oos_trades": {
    "value": 215.0,
    "threshold": 100.0,
    "comparison": "gt",
    "pass": true,
    "status": "evaluated"
  }
}
```

Falsification condition (pre-registered): WF mean OOS Sharpe < 0.9 OR positive fold rate < 50% OR pooled OOS trades < 100 OR the parameter plateau check fails.

### What the walk-forward windows cover (and what they exclude)

The pre-registered design burns in 10 years before the first fold test window, so the 36 fold test windows cover **2008-09-17 .. 2026-07-30** and **exclude** the first 2448 invested sessions (1998-12-22 .. 2008-09-16). That is why the walk-forward mean OOS Sharpe (0.847243) is far above the full-sample Sharpe (0.472367): the two numbers measure different windows, and the excluded window is where the strategy lost money.

Two further properties of the pre-registered design must be kept in mind when reading the gate value. (1) The gate statistic is the **mean of 36 overlapping 12-month Sharpes**; it is not the Sharpe of the concatenated covered window, which is 0.590049 over the same 4494 sessions -- equal-weighting the folds gives every year the same weight and therefore a higher value than the compounded path. (2) The folds overlap by 6 months, so they are not independent observations: the pooled trade count is 215 summed over folds but only 110 distinct traded sessions.

```json
{
  "walkforward_covered_window": {
    "sessions": 4494,
    "start_date": "2008-09-17",
    "end_date": "2026-07-30",
    "sharpe_canonical": 0.5900492386571634,
    "sharpe_backtest_scale": 0.4127827196557262,
    "cagr": 0.0964290805518504,
    "annualized_vol": 0.18515571731199082,
    "total_return": 4.164001979471469,
    "max_drawdown": -0.3811307207365453,
    "rolling_63d_sharpe": 1.0524198800926148,
    "rolling_63d_max_dd": -0.04057108277648058,
    "trade_days": 110,
    "turnover_total": 50.800000000000004,
    "annualized_turnover": 2.8485981308411215,
    "avg_exposure": 1.0,
    "profit_factor": 1.1212304737997991,
    "best_day": 0.11864193190428868,
    "worst_day": -0.11193548012032087,
    "cost_drag_total": 0.015240000000000002
  },
  "pre_walkforward_window_excluded_from_the_folds": {
    "sessions": 2448,
    "start_date": "1998-12-22",
    "end_date": "2008-09-16",
    "sharpe_canonical": 0.18237947633510096,
    "sharpe_backtest_scale": -0.021716131819164725,
    "cagr": 0.016517220099706575,
    "annualized_vol": 0.16037754464263443,
    "total_return": 0.17250477010647947,
    "max_drawdown": -0.36322196588884226,
    "rolling_63d_sharpe": -2.7097773479317966,
    "rolling_63d_max_dd": -0.12904510465752084,
    "trade_days": 65,
    "turnover_total": 29.000000000000004,
    "annualized_turnover": 2.9852941176470593,
    "avg_exposure": 0.8860294117647058,
    "profit_factor": 1.034294658066439,
    "best_day": 0.05897837456400793,
    "worst_day": -0.0625204959079542,
    "cost_drag_total": 0.008700000000000003
  },
  "benchmark_1_over_9_same_window": {
    "sessions": 4494,
    "start_date": "2008-09-17",
    "end_date": "2026-07-30",
    "sharpe_canonical": 0.5685118870066325,
    "sharpe_backtest_scale": 0.38975608264428013,
    "cagr": 0.09383391134942021,
    "annualized_vol": 0.18943620032431008,
    "total_return": 3.950316919770268,
    "max_drawdown": -0.45218228528630044,
    "rolling_63d_sharpe": 2.016139583743356,
    "rolling_63d_max_dd": -0.017049088894717124,
    "trade_days": 0,
    "turnover_total": 0.0,
    "annualized_turnover": 0.0,
    "avg_exposure": 1.0,
    "profit_factor": 1.1198912314045728,
    "best_day": 0.11194064216345244,
    "worst_day": -0.1157257560155213,
    "cost_drag_total": 0.0
  }
}
```

### Parameter plateau (lookback 189 / 252 / 315 at skip 21, top_fraction 0.5, test window)

```json
{
  "rows": [
    {
      "lookback": 189,
      "skip": 21,
      "top_fraction": 0.5,
      "test_sessions": 2204,
      "test_sharpe_canonical": 0.6561806421908947,
      "test_sharpe_backtest_scale": 0.4848637306112509,
      "test_cagr": 0.10786149478319595,
      "test_max_dd": -0.32839849319132464
    },
    {
      "lookback": 252,
      "skip": 21,
      "top_fraction": 0.5,
      "test_sessions": 2204,
      "test_sharpe_canonical": 0.6861681662906355,
      "test_sharpe_backtest_scale": 0.5179274065272281,
      "test_cagr": 0.11359319523325007,
      "test_max_dd": -0.34132006501598744
    },
    {
      "lookback": 315,
      "skip": 21,
      "top_fraction": 0.5,
      "test_sessions": 2204,
      "test_sharpe_canonical": 0.5488995775739868,
      "test_sharpe_backtest_scale": 0.3679395821738396,
      "test_cagr": 0.08885537543121602,
      "test_max_dd": -0.3667863423963248
    }
  ],
  "gate": {
    "value": 2.0,
    "threshold": 2.0,
    "comparison": "gte",
    "pass": true,
    "status": "evaluated",
    "lookbacks_within_threshold": [
      189,
      252
    ],
    "threshold_used": 0.1
  }
}
```

## 6. PSR and multiple-testing control

```json
{
  "target_0.0": {
    "sr_target": 0.0,
    "psr_normal": 0.9968950201132478,
    "psr_empirical": 0.999,
    "sharpe_observed": 0.4723674832996954,
    "sharpe_se": 0.17261839196973408
  },
  "target_0.9_candidate_gate": {
    "sr_target": 0.9,
    "psr_normal": 0.006618494482442546,
    "psr_empirical": 0.008,
    "sharpe_observed": 0.4723674832996954,
    "sharpe_se": 0.17261839196973408,
    "sharpe_ci_lower": 0.15353081206095023,
    "sharpe_ci_upper": 0.8272277103917911
  },
  "target_1.4178_incumbent_baseline": {
    "sr_target": 1.4178,
    "psr_normal": 2.1628739762327463e-08,
    "psr_empirical": 0.0,
    "sharpe_observed": 0.4723674832996954,
    "sharpe_se": 0.17261839196973408
  }
}
```

```json
{
  "dsr": -4.182755196700947,
  "dsr_probability": 1.4399872686190892e-05,
  "n_configs": 18,
  "sr_observed": 0.4723674832996954,
  "sharpe_se": 0.16932506993201432,
  "sr_threshold": 1.1806127994895796,
  "e_max": 1.6572430745326043,
  "sr_target": 0.9,
  "seed": 42
}
```

The PSR seed is 20240101 (as in `config/promotion_gates.yaml`), the DSR seed is 42 (as in the frozen candidate config); N=18 is the pre-registered configuration count. Three PSR targets are reported because the candidate has no recorded backtest baseline of its own: 0.0 (is the edge positive at all), 0.9 (the candidate's own promotion threshold -- the decision-relevant reading) and 1.4178 (the incumbent's recorded baseline -- kept for like-for-like comparison with `research/reports/promotion_feasibility_backtest_001.md`).

## 7. Repository promotion-gate table applied to the long sample

```json
{
  "track_record_length": {
    "value": 6712.0,
    "threshold": 126.0,
    "comparison": "gte",
    "pass": true,
    "status": "evaluated"
  },
  "full_period_sharpe": {
    "value": 0.4723674832996954,
    "threshold": 0.9,
    "comparison": "gte",
    "pass": false,
    "status": "evaluated"
  },
  "rolling_63d_sharpe": {
    "value": 1.7651632775694415,
    "threshold": 0.9,
    "comparison": "gte",
    "pass": true,
    "status": "evaluated"
  },
  "max_drawdown": {
    "value": -0.4715783445216646,
    "threshold": -0.15,
    "comparison": "gte",
    "pass": false,
    "status": "evaluated"
  },
  "rolling_63d_max_dd": {
    "value": -0.0334805595055111,
    "threshold": -0.15,
    "comparison": "gte",
    "pass": true,
    "status": "evaluated"
  },
  "regime_flips": {
    "value": null,
    "threshold": 1.0,
    "comparison": "gte",
    "pass": null,
    "status": "not_applicable",
    "note": "The candidate has no paper-trading record and no regime filter (frozen config: risk_overlay.none = true), so this gate cannot be satisfied or violated by a long-sample backtest."
  },
  "psr": {
    "value": 0.006618494482442546,
    "threshold": 0.95,
    "comparison": "gte",
    "pass": false,
    "status": "evaluated"
  }
}
```

`regime_flips` is reported as NOT APPLICABLE: it counts risk-on/risk-off transitions in a paper-trading state, and this candidate has no paper-trading record and no regime filter (frozen config: `risk_overlay.none = true`). The decision is therefore given under three explicit readings.

```json
{
  "primary_candidate_target_0.9": {
    "decision": "NO-GO",
    "failed_gates": [
      "full_period_sharpe",
      "max_drawdown",
      "psr"
    ],
    "psr_zone": "below_grey",
    "regime_flips_treatment": "not_applicable_excluded",
    "psr_target": 0.9
  },
  "comparable_incumbent_target_1.4178": {
    "decision": "NO-GO",
    "failed_gates": [
      "full_period_sharpe",
      "max_drawdown",
      "psr"
    ],
    "psr_zone": "below_grey",
    "regime_flips_treatment": "not_applicable_excluded",
    "psr_target": 1.4178
  },
  "conservative_regime_flips_counted_as_failed": {
    "decision": "NO-GO",
    "failed_gates": [
      "full_period_sharpe",
      "max_drawdown",
      "psr",
      "regime_flips"
    ],
    "psr_zone": "below_grey",
    "regime_flips_treatment": "not_applicable_counted_as_failed",
    "psr_target": 0.9
  }
}
```

### Same table with the incumbent's PSR target (1.4178)

```json
{
  "track_record_length": {
    "value": 6712.0,
    "threshold": 126.0,
    "comparison": "gte",
    "pass": true,
    "status": "evaluated"
  },
  "full_period_sharpe": {
    "value": 0.4723674832996954,
    "threshold": 0.9,
    "comparison": "gte",
    "pass": false,
    "status": "evaluated"
  },
  "rolling_63d_sharpe": {
    "value": 1.7651632775694415,
    "threshold": 0.9,
    "comparison": "gte",
    "pass": true,
    "status": "evaluated"
  },
  "max_drawdown": {
    "value": -0.4715783445216646,
    "threshold": -0.15,
    "comparison": "gte",
    "pass": false,
    "status": "evaluated"
  },
  "rolling_63d_max_dd": {
    "value": -0.0334805595055111,
    "threshold": -0.15,
    "comparison": "gte",
    "pass": true,
    "status": "evaluated"
  },
  "regime_flips": {
    "value": null,
    "threshold": 1.0,
    "comparison": "gte",
    "pass": null,
    "status": "not_applicable",
    "note": "The candidate has no paper-trading record and no regime filter (frozen config: risk_overlay.none = true), so this gate cannot be satisfied or violated by a long-sample backtest."
  },
  "psr": {
    "value": 2.1628739762327463e-08,
    "threshold": 0.95,
    "comparison": "gte",
    "pass": false,
    "status": "evaluated"
  }
}
```

## 8. Benchmark: 1/N equal weight over the same 9 sectors

```json
{
  "invested_sample": {
    "sessions": 6712,
    "start_date": "2000-02-01",
    "end_date": "2026-10-08",
    "sharpe_canonical": 0.4688235700892847,
    "sharpe_backtest_scale": 0.2809274003752089,
    "cagr": 0.07104385616636,
    "annualized_vol": 0.1816976774005861,
    "total_return": 5.221768571324176,
    "max_drawdown": -0.5392223772740949,
    "rolling_63d_sharpe": 0.10347212669832259,
    "rolling_63d_max_dd": -0.05442402347190911,
    "trade_days": 0,
    "turnover_total": 0.0,
    "annualized_turnover": 0.0,
    "avg_exposure": 1.0,
    "profit_factor": 1.0937343726249082,
    "best_day": 0.11194064216345244,
    "worst_day": -0.1157257560155213,
    "cost_drag_total": 0.0
  },
  "test_window": {
    "sessions": 2204,
    "start_date": "2018-01-02",
    "end_date": "2026-10-08",
    "sharpe_canonical": 0.618722527092796,
    "sharpe_backtest_scale": 0.44299324631156295,
    "cagr": 0.09961591436176875,
    "annualized_vol": 0.17972263691301027,
    "total_return": 1.294537926290603,
    "max_drawdown": -0.37428653185914385,
    "rolling_63d_sharpe": 0.10347212669832259,
    "rolling_63d_max_dd": -0.05442402347190911,
    "trade_days": 0,
    "turnover_total": 0.0,
    "annualized_turnover": 0.0,
    "avg_exposure": 1.0,
    "profit_factor": 1.12959665884203,
    "best_day": 0.1066957576099959,
    "worst_day": -0.1157257560155213,
    "cost_drag_total": 0.0
  }
}
```

The benchmark is evaluated in the engine's exogenous-weight convention (constant 1/9 weights, zero observed turnover, zero cost drag), which is the convention documented in the hypothesis.

- invested sample: strategy CAGR +0.071200 vs benchmark +0.071044 (excess +0.000156), Sharpe 0.472367 vs 0.468824 (excess +0.003544)
- test window (2018-01-01 .. 2026-10-08): strategy CAGR +0.113593 vs benchmark +0.099616 (excess +0.013977), Sharpe 0.686168 vs 0.618723 (excess +0.067446)
- max drawdown: strategy -0.471578 vs benchmark -0.539222
- the strategy buys its long-sample Sharpe with turnover (2.9961x annualized) and 175 trade days; the benchmark needs none.

## 9. Falsification conditions for this report

- the raw cache is modified, or the aligned-frame hash stops matching `5e2d48e6579a53cd` -> the data is not the pre-registered data -> reject.
- the sample window differs from 1998-12-22..2026-10-08 -> reject.
- canonical and backtest-baseline Sharpe conventions are mixed in one statement -> reject.
- the walk-forward fold count is not 36 -> reject.
- the month-end weights are not derived from the mask at the preceding month-end -> the path is not point-in-time -> reject.
- a gate threshold is changed from `config/promotion_gates.yaml` or from the frozen candidate config -> reject.

## 10. Limitations and caveats

1. The long sample is a single path of one pre-registered configuration; it is a feasibility screen, not an independent out-of-sample record.
2. The engine's `rebalance_freq` argument is inert, so the repository's own backtest path for this candidate does not implement the frozen month-end schedule; the config-faithful path lives in this research script, not in `src/`.
3. The PSR target 1.4178 belongs to the incumbent's backtest baseline and is not the candidate's own baseline; it is reported for comparability only.
4. The `regime_flips` gate cannot be evaluated without a paper-trading record, so the gate table is reported under three explicit readings instead of one.
5. Costs are the repository's flat 3 bps round-trip model (1 bps commission + 2 bps slippage) with no bid-ask spread, market-impact, borrow or latency model; sector ETFs can be wider than SPY.
6. The sector-ETF cache ends 2026-10-08 while the core cache reaches 2026-10-16, so the candidate is evaluated 6 sessions behind the rest of the repository.
7. The 18-configuration robustness grid is not evaluated here (only the 3-lookback plateau check required by the pre-registered falsification condition).

## 11. Reproduction

```json
{
  "command": "python research/sectorrotation_long_sample_feasibility.py",
  "deterministic": true,
  "no_network": true,
  "read_only_data": true,
  "psr_seed": 20240101,
  "dsr_seed": 42,
  "n_bootstrap": 1000,
  "block_size": 22
}
```

## Appendix A: walk-forward folds

| Fold | Test start | Test end | Sessions | Test Sharpe | Test CAGR | Test max DD | Trades | Positive |
|---|---|---|---|---|---|---|---|---|
| 1 | 2008-09-17 | 2009-09-03 | 244 | -0.251753 | -0.153203 | -0.381131 | 3 | False |
| 2 | 2009-03-12 | 2010-02-26 | 243 | 2.326798 | 0.482562 | -0.084130 | 5 | True |
| 3 | 2009-09-04 | 2010-08-23 | 243 | 0.534212 | 0.091517 | -0.182286 | 6 | True |
| 4 | 2010-03-01 | 2011-02-15 | 245 | 1.105686 | 0.216599 | -0.182286 | 8 | True |
| 5 | 2010-08-24 | 2011-08-10 | 244 | 0.222370 | 0.024318 | -0.205645 | 8 | True |
| 6 | 2011-02-16 | 2012-02-02 | 243 | -0.151350 | -0.062920 | -0.226371 | 5 | False |
| 7 | 2011-08-11 | 2012-07-27 | 243 | 1.224398 | 0.242492 | -0.118092 | 4 | True |
| 8 | 2012-02-03 | 2013-01-21 | 241 | 1.276151 | 0.143699 | -0.070982 | 4 | True |
| 9 | 2012-07-30 | 2013-07-16 | 241 | 1.475458 | 0.182960 | -0.070982 | 7 | True |
| 10 | 2013-01-22 | 2014-01-08 | 244 | 2.014894 | 0.257427 | -0.063384 | 6 | True |
| 11 | 2013-07-17 | 2014-07-03 | 244 | 1.632968 | 0.197835 | -0.060335 | 5 | True |
| 12 | 2014-01-09 | 2014-12-26 | 244 | 0.843277 | 0.103140 | -0.096505 | 5 | True |
| 13 | 2014-07-04 | 2015-06-22 | 243 | 0.435778 | 0.047781 | -0.096505 | 5 | True |
| 14 | 2014-12-29 | 2015-12-15 | 244 | 0.041292 | -0.005234 | -0.113779 | 5 | True |
| 15 | 2015-06-23 | 2016-06-08 | 243 | 0.030937 | -0.008245 | -0.141787 | 4 | True |
| 16 | 2015-12-16 | 2016-12-01 | 243 | 0.415316 | 0.046177 | -0.125193 | 5 | True |
| 17 | 2016-06-09 | 2017-05-26 | 244 | 0.936460 | 0.094910 | -0.047121 | 5 | True |
| 18 | 2016-12-02 | 2017-11-20 | 244 | 1.617971 | 0.144983 | -0.047121 | 5 | True |
| 19 | 2017-05-29 | 2018-05-15 | 243 | 1.052497 | 0.141742 | -0.104484 | 7 | True |
| 20 | 2017-11-21 | 2018-11-07 | 243 | 0.521526 | 0.072208 | -0.111798 | 9 | True |
| 21 | 2018-05-16 | 2019-05-02 | 242 | 0.280416 | 0.032086 | -0.211827 | 8 | True |
| 22 | 2018-11-08 | 2019-10-25 | 242 | 0.574884 | 0.077289 | -0.171063 | 3 | True |
| 23 | 2019-05-03 | 2020-04-20 | 243 | 0.109172 | -0.015857 | -0.341320 | 6 | True |
| 24 | 2019-10-28 | 2020-10-13 | 243 | 0.587677 | 0.150493 | -0.341320 | 8 | True |
| 25 | 2020-04-21 | 2021-04-07 | 243 | 2.141875 | 0.422882 | -0.082640 | 4 | True |
| 26 | 2020-10-14 | 2021-09-30 | 243 | 1.337338 | 0.206471 | -0.063475 | 5 | True |
| 27 | 2021-04-08 | 2022-03-25 | 245 | 1.096551 | 0.176596 | -0.075208 | 6 | True |
| 28 | 2021-10-01 | 2022-09-19 | 243 | 0.349912 | 0.049626 | -0.130601 | 9 | True |
| 29 | 2022-03-28 | 2023-03-14 | 242 | -0.188398 | -0.053271 | -0.142241 | 10 | False |
| 30 | 2022-09-20 | 2023-09-06 | 242 | 0.608990 | 0.085622 | -0.105982 | 9 | True |
| 31 | 2023-03-15 | 2024-02-29 | 242 | 1.452585 | 0.188093 | -0.096770 | 8 | True |
| 32 | 2023-09-07 | 2024-08-23 | 243 | 1.318585 | 0.170817 | -0.087476 | 7 | True |
| 33 | 2024-03-01 | 2025-02-17 | 241 | 1.096893 | 0.134608 | -0.071076 | 7 | True |
| 34 | 2024-08-26 | 2025-08-12 | 241 | 0.635935 | 0.095824 | -0.166460 | 5 | True |
| 35 | 2025-02-18 | 2026-02-04 | 243 | 0.582934 | 0.084391 | -0.166460 | 4 | True |
| 36 | 2025-08-13 | 2026-07-30 | 242 | 1.210524 | 0.142750 | -0.060668 | 5 | True |

## Appendix B: internal checks

| Check | Pass | Detail |
|---|---|---|
| raw_cache_present | True | 9/9 sector parquet files present in data/raw (no network fetch possible). |
| aligned_frame_shape | True | aligned Close frame is 6991 x 9 (expected 6991 x 9). |
| aligned_frame_no_missing | True | aligned Close frame has 0 missing values. |
| aligned_frame_matches_preregistered_hash | True | aligned-frame content hash 5e2d48e6579a53cd (pre-registered 5e2d48e6579a53cd). |
| sample_matches_preregistered_window | True | sample 1998-12-22..2026-10-08 matches the frozen history_start 1998-12-22 and the cached last session. |
| cost_model_matches_frozen_config | True | engine cost model 1.0+2.0 bps = 3.0 bps round-trip equals the frozen config. |
| warmup_matches_preregistered_signal_date | True | first date with a valid momentum cross-section is 2000-01-24 (pre-registered 2000-01-24). |
| no_positions_before_warmup | True | no position is held before 2000-02-01 (279 pre-warmup sessions carry zero exposure). |
| monthly_weights_point_in_time | True | 321 rebalances; each segment equals the equal-weight of the mask at its own signal date and becomes effective strictly after it |
| benchmark_exposure_is_unit | True | 1/N benchmark gross exposure is 1.000000 on the invested sample. |
| walkforward_fold_count | True | generated 36 walk-forward folds (pre-registered 36). |
| raw_cache_unchanged | True | all 9 sector parquet files are SHA-256 byte-identical before and after the run. |
