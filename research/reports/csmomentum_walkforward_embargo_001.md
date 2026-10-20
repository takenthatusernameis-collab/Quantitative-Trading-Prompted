# CSMomentum Walk-Forward Embargo Audit (csmomentum_walkforward_embargo_001, Cycle 908)

## Summary

- Candidate: `csmomentum_001`
- Gate scale: `backtest_sharpe_ratio` (backtest scale only)
- Common inception (re-derived): `2006-02-06`
- Verdict (published): **Rejected/Failed**
- Verdict survives Design A: **YES**

## 1. Reproduction anchor (published design on union_sample)

| Metric | Published | Observed | Match |
|---|---|---|---|
| n_folds | 48 | 48 | MATCH |
| mean_test_sharpe | 0.6975 | 0.6975243375 | MATCH |
| mean_test_sharpe_canonical | 0.8404 | 0.8403888342 | MATCH |
| median_test_sharpe | 0.6179 | 0.6178806353 | MATCH |
| pct_positive_sharpe | 0.7917 | 0.7916666667 | MATCH |
| total_test_trades | 400 | 400 | MATCH |

**Anchor overall:** MATCH (tool OVERALL depends on this)

## 2. Three designs, three samples

### 2.1 Published design (as in Cycle 907)

| Sample | Folds | WF mean OOS Sharpe (backtest) | Median | Positive folds | Pooled OOS trades | Mean consecutive overlap (days) | Max disjoint test windows | Decision |
|---|---|---|---|---|---|---|---|---|
| union_sample | 48 | 0.697524 | 0.617881 | 79.17% | 400 | 175.0 | 24 | Rejected/Failed |
| common_inception_slice | 21 | 0.586081 | 0.631134 | 76.19% | 166 | 175.0 | 11 | Rejected/Failed |
| common_inception_window | 21 | 0.586081 | 0.631134 | 76.19% | 166 | 175.0 | 11 | Rejected/Failed |

### 2.2 Design A (non-overlapping test windows, primary sensitivity)

| Sample | Folds | WF mean OOS Sharpe (backtest) | Median | Positive folds | Pooled OOS trades | Mean consecutive overlap (days) | Max disjoint test windows | Decision |
|---|---|---|---|---|---|---|---|---|
| union_sample | 24 | 0.698298 | 0.635245 | 79.17% | 199 | 0.0 | 24 | Rejected/Failed |
| common_inception_slice | 11 | 0.601900 | 0.511066 | 81.82% | 87 | 0.0 | 11 | Rejected/Failed |
| common_inception_window | 11 | 0.601900 | 0.511066 | 81.82% | 87 | 0.0 | 11 | Rejected/Failed |

### 2.3 Design B (configuration's embargo applied literally, informational)

| Sample | Folds | WF mean OOS Sharpe (backtest) | Median | Positive folds | Pooled OOS trades | Mean consecutive overlap (days) | Max disjoint test windows | Decision |
|---|---|---|---|---|---|---|---|---|
| union_sample | 3 | 0.913346 | 1.112158 | 100.00% | 26 | 0.0 | 3 | Inconclusive |
| common_inception_slice | 1 | -0.129823 | -0.129823 | 0.00% | 6 | 0.0 | 1 | Rejected/Failed |
| common_inception_window | 1 | -0.129823 | -0.129823 | 0.00% | 6 | 0.0 | 1 | Rejected/Failed |

## 3. Delta (published vs Design A, union_sample)

- Fold count: published 48, Design A 24 (delta -24)
- WF mean OOS Sharpe (backtest): published 0.697524, Design A 0.698298
- Gate-1 margin (>=0.9): published 0.202476, Design A 0.201702
- Published verdict **Rejected/Failed** survives Design A: **YES**

## 4. Gate tables

### Published design (union_sample)
- wf_mean_oos_sharpe: threshold >= 0.9, observed 0.6975243375140185, status FAIL 
- positive_fold_rate: threshold >= 0.5, observed 0.7916666666666666, status PASS 
- pooled_oos_trades: threshold >> 100, observed 400, status PASS 
- plateau: threshold >= 0.667 (>= 2 of 3 lookbacks), observed None, status NOT EVALUATED (the 27-configuration robustness grid is out of scope for this cycle (it is a re-optimisation, not a measurement); the plateau gate is reported as NOT EVALUATED, as the published record already does)

### Design A (union_sample)
- wf_mean_oos_sharpe: threshold >= 0.9, observed 0.6982984362427751, status FAIL 
- positive_fold_rate: threshold >= 0.5, observed 0.7916666666666666, status PASS 
- pooled_oos_trades: threshold >> 100, observed 199, status PASS 
- plateau: threshold >= 0.667 (>= 2 of 3 lookbacks), observed None, status NOT EVALUATED (the 27-configuration robustness grid is out of scope for this cycle (it is a re-optimisation, not a measurement); the plateau gate is reported as NOT EVALUATED, as the published record already does)

## 5. Independence diagnostic (all designs)

| Design | union_sample (folds / overlap days / disjoint) | common_inception_slice (folds / overlap days / disjoint) | common_inception_window (folds / overlap days / disjoint) |
|---|---|---|---|
| Published | 48 / 175.0 / 24 | 21 / 175.0 / 11 | 21 / 175.0 / 11 |
| Design A | 24 / 0.0 / 24 | 11 / 0.0 / 11 | 11 / 0.0 / 11 |
| Design B | 3 / 0.0 / 3 | 1 / 0.0 / 1 | 1 / 0.0 / 1 |

## 6. Checks
- [policy_loaded]: PASS
- [policy_universe_matches]: PASS (observed: ['SPY', 'QQQ', 'IWM', 'TLT', 'GLD', 'DBC', 'VNQ', 'EFA', 'EEM', 'XLB', 'XLE', 'XLF', 'XLI', 'XLK', 'XLP', 'XLU', 'XLV', 'XLY'], expected: ['SPY', 'QQQ', 'IWM', 'TLT', 'GLD', 'DBC', 'VNQ', 'EFA', 'EEM', 'XLB', 'XLE', 'XLF', 'XLI', 'XLK', 'XLP', 'XLU', 'XLV', 'XLY'])
- [common_inception_derived]: PASS (observed: 2006-02-06, expected: )
- [reproduces_committed_config_faithful_record_union_sample]: PASS (observed: {'n_folds': '48', 'mean_test_sharpe': 0.6975243375140185, 'mean_test_sharpe_canonical': 0.8403888341999609, 'median_test_sharpe': 0.6178806353181572, 'pct_positive_sharpe': 0.7916666666666666, 'total_test_trades': 400}, expected: {'n_folds': '48', 'mean_test_sharpe': '0.6975', 'mean_test_sharpe_canonical': '0.8404', 'median_test_sharpe': '0.6179', 'pct_positive_sharpe': '0.7917', 'total_test_trades': '400'})
- [does_not_produce_legacy_or_daily_values]: PASS (observed: 0.6975243375140185, expected: !=0.6868 and !=0.6928)
- [design_a_test_windows_pairwise_disjoint]: PASS (observed: overlap=0.0, disjoint=24, folds=24, expected: overlap==0 and disjoint==folds)
- [published_design_has_overlap]: PASS
- [data_unchanged]: PASS
- [config_unchanged]: PASS
- [committed_artifacts_unchanged]: PASS

## 7. JSON payload
```json
{
  "cycle": "908",
  "candidate": "csmomentum_001",
  "policy_path": "/home/runner/work/Quantitative-Trading-Prompted/Quantitative-Trading-Prompted/config/sample_policy.yaml",
  "config_path": "/home/runner/work/Quantitative-Trading-Prompted/Quantitative-Trading-Prompted/config/csmomentum_candidate_001.yaml",
  "gate_scale": "backtest_sharpe_ratio",
  "overall": "PASS",
  "checks": [
    {
      "name": "policy_loaded",
      "pass": true,
      "observed": "",
      "expected": ""
    },
    {
      "name": "policy_universe_matches",
      "pass": true,
      "observed": "['SPY', 'QQQ', 'IWM', 'TLT', 'GLD', 'DBC', 'VNQ', 'EFA', 'EEM', 'XLB', 'XLE', 'XLF', 'XLI', 'XLK', 'XLP', 'XLU', 'XLV', 'XLY']",
      "expected": "['SPY', 'QQQ', 'IWM', 'TLT', 'GLD', 'DBC', 'VNQ', 'EFA', 'EEM', 'XLB', 'XLE', 'XLF', 'XLI', 'XLK', 'XLP', 'XLU', 'XLV', 'XLY']"
    },
    {
      "name": "common_inception_derived",
      "pass": true,
      "observed": "2006-02-06",
      "expected": ""
    },
    {
      "name": "reproduces_committed_config_faithful_record_union_sample",
      "pass": true,
      "observed": "{'n_folds': '48', 'mean_test_sharpe': 0.6975243375140185, 'mean_test_sharpe_canonical': 0.8403888341999609, 'median_test_sharpe': 0.6178806353181572, 'pct_positive_sharpe': 0.7916666666666666, 'total_test_trades': 400}",
      "expected": "{'n_folds': '48', 'mean_test_sharpe': '0.6975', 'mean_test_sharpe_canonical': '0.8404', 'median_test_sharpe': '0.6179', 'pct_positive_sharpe': '0.7917', 'total_test_trades': '400'}"
    },
    {
      "name": "does_not_produce_legacy_or_daily_values",
      "pass": true,
      "observed": 0.6975243375140185,
      "expected": "!=0.6868 and !=0.6928"
    },
    {
      "name": "design_a_test_windows_pairwise_disjoint",
      "pass": true,
      "observed": "overlap=0.0, disjoint=24, folds=24",
      "expected": "overlap==0 and disjoint==folds"
    },
    {
      "name": "published_design_has_overlap",
      "pass": true,
      "observed": "",
      "expected": ""
    },
    {
      "name": "data_unchanged",
      "pass": true,
      "observed": "",
      "expected": ""
    },
    {
      "name": "config_unchanged",
      "pass": true,
      "observed": "",
      "expected": ""
    },
    {
      "name": "committed_artifacts_unchanged",
      "pass": true,
      "observed": "",
      "expected": ""
    }
  ],
  "common_inception": "2006-02-06",
  "anchor": {
    "rows": [
      {
        "metric": "n_folds",
        "published": 48,
        "observed": 48,
        "match": true
      },
      {
        "metric": "mean_test_sharpe",
        "published": 0.6975,
        "published_text": "0.6975",
        "observed": 0.6975243375140185,
        "abs_diff": 2.4337514018535344e-05,
        "match": true
      },
      {
        "metric": "mean_test_sharpe_canonical",
        "published": 0.8404,
        "published_text": "0.8404",
        "observed": 0.8403888341999609,
        "abs_diff": 1.1165800039125706e-05,
        "match": true
      },
      {
        "metric": "median_test_sharpe",
        "published": 0.6179,
        "published_text": "0.6179",
        "observed": 0.6178806353181572,
        "abs_diff": 1.9364681842826137e-05,
        "match": true
      },
      {
        "metric": "pct_positive_sharpe",
        "published": 0.7917,
        "published_text": "0.7917",
        "observed": 0.7916666666666666,
        "abs_diff": 3.333333333332966e-05,
        "match": true
      },
      {
        "metric": "total_test_trades",
        "published": 400,
        "observed": 400,
        "match": true
      }
    ],
    "matches": true
  },
  "published_design": {
    "union_sample": {
      "wf": {
        "n_folds": 48,
        "mean_test_sharpe": 0.6975243375140185,
        "std_test_sharpe": 0.7783585033932666,
        "median_test_sharpe": 0.6178806353181572,
        "min_test_sharpe": -0.8567738850188672,
        "max_test_sharpe": 2.4473493123037615,
        "pct_positive_sharpe": 0.7916666666666666,
        "mean_test_ann_return": 0.10509556949469127,
        "mean_test_max_dd": -0.13178343849592733,
        "mean_test_trades": 8.333333333333334,
        "total_test_trades": 400,
        "mean_test_sharpe_canonical": 0.8403888341999609,
        "folds": [
          {
            "fold": 1,
            "test_start": "2002-09-30",
            "test_end": "2003-09-16",
            "test_sessions": 243,
            "test_sharpe": 1.1121582256222222,
            "test_sharpe_canonical": 1.1847608618398233,
            "test_ann_return": 0.24338207942578305,
            "test_max_dd": -0.14265741312216396,
            "test_turnover": 3.814814814814815,
            "test_trades": 10
          },
          {
            "fold": 2,
            "test_start": "2003-03-25",
            "test_end": "2004-03-10",
            "test_sessions": 243,
            "test_sharpe": 2.085581432919897,
            "test_sharpe_canonical": 2.002910891173504,
            "test_ann_return": 0.3198232707365849,
            "test_max_dd": -0.05694729742869731,
            "test_turnover": 4.407407407407407,
            "test_trades": 11
          },
          {
            "fold": 3,
            "test_start": "2003-09-17",
            "test_end": "2004-09-02",
            "test_sessions": 243,
            "test_sharpe": 0.5510622508974872,
            "test_sharpe_canonical": 0.7301566223532905,
            "test_ann_return": 0.09888742015760066,
            "test_max_dd": -0.08720505524401456,
            "test_turnover": 3.6296296296296298,
            "test_trades": 9
          },
          {
            "fold": 4,
            "test_start": "2004-03-11",
            "test_end": "2005-02-25",
            "test_sessions": 243,
            "test_sharpe": 1.350235632768709,
            "test_sharpe_canonical": 1.4365928202598603,
            "test_ann_return": 0.1979630448722669,
            "test_max_dd": -0.08709718873636396,
            "test_turnover": 2.333333333333333,
            "test_trades": 6
          },
          {
            "fold": 5,
            "test_start": "2004-09-03",
            "test_end": "2005-08-22",
            "test_sessions": 244,
            "test_sharpe": 1.499876469611883,
            "test_sharpe_canonical": 1.58702274390774,
            "test_ann_return": 0.19376625264210334,
            "test_max_dd": -0.08879207214055351,
            "test_turnover": 2.581967213114754,
            "test_trades": 8
          },
          {
            "fold": 6,
            "test_start": "2005-02-28",
            "test_end": "2006-02-14",
            "test_sessions": 244,
            "test_sharpe": 0.6361047282984064,
            "test_sharpe_canonical": 0.8199685961078376,
            "test_ann_return": 0.10045987404804468,
            "test_max_dd": -0.08879207214055373,
            "test_turnover": 3.7008196721311477,
            "test_trades": 12
          },
          {
            "fold": 7,
            "test_start": "2005-08-23",
            "test_end": "2006-08-09",
            "test_sessions": 243,
            "test_sharpe": 0.5914958760019136,
            "test_sharpe_canonical": 0.763170967335054,
            "test_ann_return": 0.1082883117402873,
            "test_max_dd": -0.14251903837549496,
            "test_turnover": 3.744855967078189,
            "test_trades": 11
          },
          {
            "fold": 8,
            "test_start": "2006-02-15",
            "test_end": "2007-02-01",
            "test_sessions": 242,
            "test_sharpe": 0.9469738574733044,
            "test_sharpe_canonical": 1.0886805883916855,
            "test_ann_return": 0.14789059712033148,
            "test_max_dd": -0.14251903837549484,
            "test_turnover": 4.1652892561983474,
            "test_trades": 11
          },
          {
            "fold": 9,
            "test_start": "2006-08-10",
            "test_end": "2007-07-27",
            "test_sessions": 242,
            "test_sharpe": 0.8262041017731879,
            "test_sharpe_canonical": 0.993593637597982,
            "test_ann_return": 0.12266702958293396,
            "test_max_dd": -0.07287049457391714,
            "test_turnover": 4.026446280991736,
            "test_trades": 11
          },
          {
            "fold": 10,
            "test_start": "2007-02-02",
            "test_end": "2008-01-21",
            "test_sessions": 243,
            "test_sharpe": -0.1382632816059941,
            "test_sharpe_canonical": 0.06227404562370095,
            "test_ann_return": -0.005517548421673402,
            "test_max_dd": -0.10882469056901956,
            "test_turnover": 2.9497942386831277,
            "test_trades": 10
          },
          {
            "fold": 11,
            "test_start": "2007-07-30",
            "test_end": "2008-07-15",
            "test_sessions": 243,
            "test_sharpe": 0.09743325025298999,
            "test_sharpe_canonical": 0.2937757413426074,
            "test_ann_return": 0.038331982502398,
            "test_max_dd": -0.11808354095384432,
            "test_turnover": 1.8666666666666667,
            "test_trades": 8
          },
          {
            "fold": 12,
            "test_start": "2008-01-22",
            "test_end": "2009-01-07",
            "test_sessions": 244,
            "test_sharpe": -0.8333487045609156,
            "test_sharpe_canonical": -0.7199962882076838,
            "test_ann_return": -0.22359959672553253,
            "test_max_dd": -0.4050070282925824,
            "test_turnover": 1.8590163934426231,
            "test_trades": 8
          },
          {
            "fold": 13,
            "test_start": "2008-07-16",
            "test_end": "2009-07-02",
            "test_sessions": 244,
            "test_sharpe": -0.8567738850188672,
            "test_sharpe_canonical": -0.7551626381571066,
            "test_ann_return": -0.24797671992759973,
            "test_max_dd": -0.3845015275385357,
            "test_turnover": 2.0655737704918034,
            "test_trades": 8
          },
          {
            "fold": 14,
            "test_start": "2009-01-08",
            "test_end": "2009-12-25",
            "test_sessions": 244,
            "test_sharpe": 1.335075112364023,
            "test_sharpe_canonical": 1.3716630621364254,
            "test_ann_return": 0.26733766129886605,
            "test_max_dd": -0.1818591462071023,
            "test_turnover": 1.859016393442623,
            "test_trades": 6
          },
          {
            "fold": 15,
            "test_start": "2009-07-03",
            "test_end": "2010-06-21",
            "test_sessions": 243,
            "test_sharpe": 1.2976065459789101,
            "test_sharpe_canonical": 1.3355871405185837,
            "test_ann_return": 0.27326825148885203,
            "test_max_dd": -0.15110728630414993,
            "test_turnover": 2.2814814814814817,
            "test_trades": 7
          },
          {
            "fold": 16,
            "test_start": "2009-12-28",
            "test_end": "2010-12-14",
            "test_sessions": 244,
            "test_sharpe": 0.43949271470004525,
            "test_sharpe_canonical": 0.6114800739261205,
            "test_ann_return": 0.11226976712302972,
            "test_max_dd": -0.17721510219504288,
            "test_turnover": 3.3049180327868855,
            "test_trades": 9
          },
          {
            "fold": 17,
            "test_start": "2010-06-22",
            "test_end": "2011-06-08",
            "test_sessions": 244,
            "test_sharpe": 0.885280636825139,
            "test_sharpe_canonical": 1.0188984605484885,
            "test_ann_return": 0.15819391348880774,
            "test_max_dd": -0.07820715353923557,
            "test_turnover": 3.5114754098360654,
            "test_trades": 11
          },
          {
            "fold": 18,
            "test_start": "2010-12-15",
            "test_end": "2011-12-01",
            "test_sessions": 244,
            "test_sharpe": -0.0984188449796709,
            "test_sharpe_canonical": 0.10293881519111601,
            "test_ann_return": -0.001811434489857322,
            "test_max_dd": -0.20897774296566973,
            "test_turnover": 3.098360655737705,
            "test_trades": 10
          },
          {
            "fold": 19,
            "test_start": "2011-06-09",
            "test_end": "2012-05-25",
            "test_sessions": 244,
            "test_sharpe": -0.11832601380435821,
            "test_sharpe_canonical": 0.08217590761651598,
            "test_ann_return": -0.004853001337003282,
            "test_max_dd": -0.1962932686347152,
            "test_turnover": 2.0655737704918034,
            "test_trades": 6
          },
          {
            "fold": 20,
            "test_start": "2011-12-02",
            "test_end": "2012-11-19",
            "test_sessions": 242,
            "test_sharpe": 0.706764596510995,
            "test_sharpe_canonical": 0.9269012967121042,
            "test_ann_return": 0.0871547073657637,
            "test_max_dd": -0.06912622799279988,
            "test_turnover": 1.2495867768595041,
            "test_trades": 5
          },
          {
            "fold": 21,
            "test_start": "2012-05-28",
            "test_end": "2013-05-14",
            "test_sessions": 241,
            "test_sharpe": 2.064773735904461,
            "test_sharpe_canonical": 2.0757926837083205,
            "test_ann_return": 0.2378224365020405,
            "test_max_dd": -0.06912622799280044,
            "test_turnover": 2.7186721991701246,
            "test_trades": 9
          },
          {
            "fold": 22,
            "test_start": "2012-11-20",
            "test_end": "2013-11-06",
            "test_sessions": 243,
            "test_sharpe": 2.251890496149962,
            "test_sharpe_canonical": 2.195906739548103,
            "test_ann_return": 0.2806296075987531,
            "test_max_dd": -0.07241130632306358,
            "test_turnover": 2.9037037037037035,
            "test_trades": 10
          },
          {
            "fold": 23,
            "test_start": "2013-05-15",
            "test_end": "2014-05-01",
            "test_sessions": 243,
            "test_sharpe": 0.8950327298125819,
            "test_sharpe_canonical": 1.055381317712991,
            "test_ann_return": 0.13051466278956458,
            "test_max_dd": -0.0724113063230637,
            "test_turnover": 1.8666666666666667,
            "test_trades": 7
          },
          {
            "fold": 24,
            "test_start": "2013-11-07",
            "test_end": "2014-10-24",
            "test_sessions": 243,
            "test_sharpe": 0.5729193086169263,
            "test_sharpe_canonical": 0.7710932455689501,
            "test_ann_return": 0.08739321237868225,
            "test_max_dd": -0.08364478241975726,
            "test_turnover": 1.8666666666666667,
            "test_trades": 7
          },
          {
            "fold": 25,
            "test_start": "2014-05-02",
            "test_end": "2015-04-20",
            "test_sessions": 243,
            "test_sharpe": 0.8670941479237154,
            "test_sharpe_canonical": 1.0504759867998104,
            "test_ann_return": 0.1137650110178221,
            "test_max_dd": -0.08364478241975704,
            "test_turnover": 2.2814814814814817,
            "test_trades": 8
          },
          {
            "fold": 26,
            "test_start": "2014-10-27",
            "test_end": "2015-10-13",
            "test_sessions": 243,
            "test_sharpe": 0.13520930035425033,
            "test_sharpe_canonical": 0.3514019467260984,
            "test_ann_return": 0.037055410711650305,
            "test_max_dd": -0.09860782856456363,
            "test_turnover": 1.866666666666667,
            "test_trades": 7
          },
          {
            "fold": 27,
            "test_start": "2015-04-21",
            "test_end": "2016-04-06",
            "test_sessions": 243,
            "test_sharpe": -0.23854812887090193,
            "test_sharpe_canonical": -0.02803236394743473,
            "test_ann_return": -0.014097384931297419,
            "test_max_dd": -0.124244048685489,
            "test_turnover": 1.866666666666667,
            "test_trades": 8
          },
          {
            "fold": 28,
            "test_start": "2015-10-14",
            "test_end": "2016-09-29",
            "test_sessions": 243,
            "test_sharpe": 0.4001074396984549,
            "test_sharpe_canonical": 0.6112323721865939,
            "test_ann_return": 0.06678735292752513,
            "test_max_dd": -0.11745861248135314,
            "test_turnover": 1.6592592592592594,
            "test_trades": 7
          },
          {
            "fold": 29,
            "test_start": "2016-04-07",
            "test_end": "2017-03-24",
            "test_sessions": 244,
            "test_sharpe": 0.599656542337908,
            "test_sharpe_canonical": 0.8500132891298856,
            "test_ann_return": 0.07075140460828355,
            "test_max_dd": -0.05628152353105287,
            "test_turnover": 2.6852459016393446,
            "test_trades": 7
          },
          {
            "fold": 30,
            "test_start": "2016-09-30",
            "test_end": "2017-09-18",
            "test_sessions": 243,
            "test_sharpe": 0.9705986539411733,
            "test_sharpe_canonical": 1.1905354961993893,
            "test_ann_return": 0.10251648972194838,
            "test_max_dd": -0.03978515480064193,
            "test_turnover": 2.696296296296296,
            "test_trades": 6
          },
          {
            "fold": 31,
            "test_start": "2017-03-27",
            "test_end": "2018-03-13",
            "test_sessions": 243,
            "test_sharpe": 1.5319626020480195,
            "test_sharpe_canonical": 1.6234425890716693,
            "test_ann_return": 0.1902354194901812,
            "test_max_dd": -0.1007211679280452,
            "test_turnover": 1.2444444444444447,
            "test_trades": 5
          },
          {
            "fold": 32,
            "test_start": "2017-09-19",
            "test_end": "2018-09-05",
            "test_sessions": 243,
            "test_sharpe": 0.7367458052629678,
            "test_sharpe_canonical": 0.9065540370946299,
            "test_ann_return": 0.11696499810793615,
            "test_max_dd": -0.10072116792804486,
            "test_turnover": 1.8666666666666667,
            "test_trades": 8
          },
          {
            "fold": 33,
            "test_start": "2018-03-14",
            "test_end": "2019-02-28",
            "test_sessions": 242,
            "test_sharpe": -0.5647770603202239,
            "test_sharpe_canonical": -0.3777698638595333,
            "test_ann_return": -0.072412123406984,
            "test_max_dd": -0.21977920561691922,
            "test_turnover": 2.2909090909090915,
            "test_trades": 7
          },
          {
            "fold": 34,
            "test_start": "2018-09-06",
            "test_end": "2019-08-23",
            "test_sessions": 243,
            "test_sharpe": -0.25122281434076066,
            "test_sharpe_canonical": -0.04506836693287933,
            "test_ann_return": -0.018228386732282886,
            "test_max_dd": -0.21977920561691933,
            "test_turnover": 2.2814814814814817,
            "test_trades": 8
          },
          {
            "fold": 35,
            "test_start": "2019-03-01",
            "test_end": "2020-02-17",
            "test_sessions": 243,
            "test_sharpe": 2.4473493123037615,
            "test_sharpe_canonical": 2.452559291305073,
            "test_ann_return": 0.23209969224624127,
            "test_max_dd": -0.04239774207595359,
            "test_turnover": 2.2814814814814817,
            "test_trades": 9
          },
          {
            "fold": 36,
            "test_start": "2019-08-26",
            "test_end": "2020-08-11",
            "test_sessions": 243,
            "test_sharpe": 0.47963092425028103,
            "test_sharpe_canonical": 0.6506891689535299,
            "test_ann_return": 0.1461782036854733,
            "test_max_dd": -0.2940018681631915,
            "test_turnover": 2.696296296296296,
            "test_trades": 9
          },
          {
            "fold": 37,
            "test_start": "2020-02-18",
            "test_end": "2021-02-03",
            "test_sessions": 244,
            "test_sharpe": 0.35813513179384626,
            "test_sharpe_canonical": 0.5453433247219177,
            "test_ann_return": 0.11887713254809196,
            "test_max_dd": -0.2939166402872937,
            "test_turnover": 1.6524590163934427,
            "test_trades": 6
          },
          {
            "fold": 38,
            "test_start": "2020-08-12",
            "test_end": "2021-07-29",
            "test_sessions": 243,
            "test_sharpe": 1.3708899565812795,
            "test_sharpe_canonical": 1.4448666431899573,
            "test_ann_return": 0.21019139308236046,
            "test_max_dd": -0.07346374391202803,
            "test_turnover": 1.866666666666667,
            "test_trades": 6
          },
          {
            "fold": 39,
            "test_start": "2021-02-04",
            "test_end": "2022-01-21",
            "test_sessions": 244,
            "test_sharpe": 0.42921977006247863,
            "test_sharpe_canonical": 0.6179399292697632,
            "test_ann_return": 0.08181944848173361,
            "test_max_dd": -0.06718525747642823,
            "test_turnover": 2.478688524590164,
            "test_trades": 8
          },
          {
            "fold": 40,
            "test_start": "2021-07-30",
            "test_end": "2022-07-18",
            "test_sessions": 243,
            "test_sharpe": -0.3989563977001138,
            "test_sharpe_canonical": -0.20498553868857933,
            "test_ann_return": -0.05059308578047628,
            "test_max_dd": -0.13706262688296433,
            "test_turnover": 2.4888888888888894,
            "test_trades": 8
          },
          {
            "fold": 41,
            "test_start": "2022-01-24",
            "test_end": "2023-01-10",
            "test_sessions": 243,
            "test_sharpe": -0.03469383928587136,
            "test_sharpe_canonical": 0.164746474272295,
            "test_ann_return": 0.013346987524904597,
            "test_max_dd": -0.17445383760806377,
            "test_turnover": 1.866666666666667,
            "test_trades": 6
          },
          {
            "fold": 42,
            "test_start": "2022-07-19",
            "test_end": "2023-07-05",
            "test_sessions": 242,
            "test_sharpe": 0.3974654863681204,
            "test_sharpe_canonical": 0.5848710587218225,
            "test_ann_return": 0.08007000090181826,
            "test_max_dd": -0.13210086230908846,
            "test_turnover": 2.290909090909091,
            "test_trades": 8
          },
          {
            "fold": 43,
            "test_start": "2023-01-11",
            "test_end": "2023-12-28",
            "test_sessions": 243,
            "test_sharpe": 0.2912235240848116,
            "test_sharpe_canonical": 0.5141090899061407,
            "test_ann_return": 0.05250991953186235,
            "test_max_dd": -0.09640008083550777,
            "test_turnover": 3.5259259259259266,
            "test_trades": 11
          },
          {
            "fold": 44,
            "test_start": "2023-07-06",
            "test_end": "2024-06-21",
            "test_sessions": 243,
            "test_sharpe": 1.0721932171160171,
            "test_sharpe_canonical": 1.2307974393185588,
            "test_ann_return": 0.13729512128623833,
            "test_max_dd": -0.09640008083550766,
            "test_turnover": 2.9037037037037035,
            "test_trades": 10
          },
          {
            "fold": 45,
            "test_start": "2023-12-29",
            "test_end": "2024-12-16",
            "test_sessions": 243,
            "test_sharpe": 1.5558825705692616,
            "test_sharpe_canonical": 1.634650761449344,
            "test_ann_return": 0.19963496409630221,
            "test_max_dd": -0.07762924672561688,
            "test_turnover": 3.111111111111111,
            "test_trades": 10
          },
          {
            "fold": 46,
            "test_start": "2024-06-24",
            "test_end": "2025-06-10",
            "test_sessions": 242,
            "test_sharpe": 0.5747526402202823,
            "test_sharpe_canonical": 0.738323710808345,
            "test_ann_return": 0.11885008374652983,
            "test_max_dd": -0.15797148979782438,
            "test_turnover": 3.123966942148761,
            "test_trades": 10
          },
          {
            "fold": 47,
            "test_start": "2024-12-17",
            "test_end": "2025-12-03",
            "test_sessions": 241,
            "test_sharpe": 0.6708339733222468,
            "test_sharpe_canonical": 0.825949200583089,
            "test_ann_return": 0.13122681878504405,
            "test_max_dd": -0.15797148979782405,
            "test_turnover": 2.091286307053942,
            "test_trades": 9
          },
          {
            "fold": 48,
            "test_start": "2025-06-11",
            "test_end": "2026-05-28",
            "test_sessions": 242,
            "test_sharpe": 1.9795844704386507,
            "test_sharpe_canonical": 1.970451032562623,
            "test_ann_return": 0.2574566821332469,
            "test_max_dd": -0.07743137513579668,
            "test_turnover": 2.4991735537190083,
            "test_trades": 9
          }
        ]
      },
      "gates": [
        {
          "gate": "wf_mean_oos_sharpe",
          "threshold": ">= 0.9",
          "observed": 0.6975243375140185,
          "status": "FAIL"
        },
        {
          "gate": "positive_fold_rate",
          "threshold": ">= 0.5",
          "observed": 0.7916666666666666,
          "status": "PASS"
        },
        {
          "gate": "pooled_oos_trades",
          "threshold": ">> 100",
          "observed": 400,
          "status": "PASS"
        },
        {
          "gate": "plateau",
          "threshold": ">= 0.667 (>= 2 of 3 lookbacks)",
          "observed": null,
          "status": "NOT EVALUATED",
          "reason": "the 27-configuration robustness grid is out of scope for this cycle (it is a re-optimisation, not a measurement); the plateau gate is reported as NOT EVALUATED, as the published record already does"
        }
      ],
      "decision": {
        "label": "Rejected/Failed",
        "detail": "falsified (gate 1 or gate 2 fails)"
      },
      "folds": 48,
      "independence": {
        "mean_consecutive_overlap_days": 175.0,
        "max_disjoint_test_windows": 24
      }
    },
    "common_inception_slice": {
      "wf": {
        "n_folds": 21,
        "mean_test_sharpe": 0.586080732009725,
        "std_test_sharpe": 0.554361059192409,
        "median_test_sharpe": 0.631133614003499,
        "min_test_sharpe": -0.20512815658822753,
        "max_test_sharpe": 1.5870895011043684,
        "pct_positive_sharpe": 0.7619047619047619,
        "mean_test_ann_return": 0.10103795950008797,
        "mean_test_max_dd": -0.1291854358585874,
        "mean_test_trades": 7.904761904761905,
        "total_test_trades": 166,
        "mean_test_sharpe_canonical": 0.757728611295589,
        "folds": [
          {
            "fold": 1,
            "test_start": "2015-11-03",
            "test_end": "2016-10-19",
            "test_sessions": 243,
            "test_sharpe": -0.129822701336185,
            "test_sharpe_canonical": 0.10086541879979755,
            "test_ann_return": 0.005012005137578601,
            "test_max_dd": -0.11745861248135336,
            "test_turnover": 1.4518518518518517,
            "test_trades": 6
          },
          {
            "fold": 2,
            "test_start": "2016-04-27",
            "test_end": "2017-04-13",
            "test_sessions": 244,
            "test_sharpe": 0.6759640583544898,
            "test_sharpe_canonical": 0.9205716053018872,
            "test_ann_return": 0.07735016798668104,
            "test_max_dd": -0.056281523531053645,
            "test_turnover": 2.6852459016393446,
            "test_trades": 7
          },
          {
            "fold": 3,
            "test_start": "2016-10-20",
            "test_end": "2017-10-06",
            "test_sessions": 243,
            "test_sharpe": 1.5339533404250725,
            "test_sharpe_canonical": 1.6957655725589382,
            "test_ann_return": 0.14813808561634256,
            "test_max_dd": -0.0319299042970872,
            "test_turnover": 2.903703703703704,
            "test_trades": 7
          },
          {
            "fold": 4,
            "test_start": "2017-04-14",
            "test_end": "2018-04-02",
            "test_sessions": 242,
            "test_sharpe": 0.7117773159981329,
            "test_sharpe_canonical": 0.8901304213669123,
            "test_ann_return": 0.10907503411639285,
            "test_max_dd": -0.1007211679280452,
            "test_turnover": 1.2495867768595041,
            "test_trades": 5
          },
          {
            "fold": 5,
            "test_start": "2017-10-09",
            "test_end": "2018-09-25",
            "test_sessions": 243,
            "test_sharpe": 0.631133614003499,
            "test_sharpe_canonical": 0.811105102410711,
            "test_ann_return": 0.1032664421134073,
            "test_max_dd": -0.10072116792804509,
            "test_turnover": 1.6592592592592594,
            "test_trades": 7
          },
          {
            "fold": 6,
            "test_start": "2018-04-03",
            "test_end": "2019-03-20",
            "test_sessions": 243,
            "test_sharpe": -0.05124303302635702,
            "test_sharpe_canonical": 0.1550775898976611,
            "test_ann_return": 0.012137264379967982,
            "test_max_dd": -0.21977920561691966,
            "test_turnover": 2.4888888888888894,
            "test_trades": 8
          },
          {
            "fold": 7,
            "test_start": "2018-09-26",
            "test_end": "2019-09-12",
            "test_sessions": 242,
            "test_sharpe": -0.11738315853351025,
            "test_sharpe_canonical": 0.08962718770103004,
            "test_ann_return": 0.0020624379978750884,
            "test_max_dd": -0.21977920561691933,
            "test_turnover": 2.4991735537190083,
            "test_trades": 9
          },
          {
            "fold": 8,
            "test_start": "2019-03-21",
            "test_end": "2020-03-06",
            "test_sessions": 243,
            "test_sharpe": 0.5276044423756984,
            "test_sharpe_canonical": 0.7245136731118775,
            "test_ann_return": 0.08463855767006012,
            "test_max_dd": -0.1253768922505898,
            "test_turnover": 2.696296296296296,
            "test_trades": 10
          },
          {
            "fold": 9,
            "test_start": "2019-09-13",
            "test_end": "2020-08-31",
            "test_sessions": 244,
            "test_sharpe": 0.5110655618517029,
            "test_sharpe_canonical": 0.6779910498653653,
            "test_ann_return": 0.15423801927772374,
            "test_max_dd": -0.2940018681631914,
            "test_turnover": 2.478688524590164,
            "test_trades": 8
          },
          {
            "fold": 10,
            "test_start": "2020-03-09",
            "test_end": "2021-02-23",
            "test_sessions": 243,
            "test_sharpe": 0.8813362025342762,
            "test_sharpe_canonical": 0.9861934814848404,
            "test_ann_return": 0.2516078998752891,
            "test_max_dd": -0.1902617222839591,
            "test_turnover": 1.2444444444444447,
            "test_trades": 5
          },
          {
            "fold": 11,
            "test_start": "2020-09-01",
            "test_end": "2021-08-18",
            "test_sessions": 243,
            "test_sharpe": 0.8615838470971496,
            "test_sharpe_canonical": 1.0098581885287328,
            "test_ann_return": 0.1406703437212049,
            "test_max_dd": -0.07346374391202781,
            "test_turnover": 1.8666666666666667,
            "test_trades": 6
          },
          {
            "fold": 12,
            "test_start": "2021-02-24",
            "test_end": "2022-02-10",
            "test_sessions": 245,
            "test_sharpe": 0.6851062582427301,
            "test_sharpe_canonical": 0.8479622260417375,
            "test_ann_return": 0.12156903362086391,
            "test_max_dd": -0.07569804909295141,
            "test_turnover": 2.468571428571429,
            "test_trades": 8
          },
          {
            "fold": 13,
            "test_start": "2021-08-19",
            "test_end": "2022-08-05",
            "test_sessions": 243,
            "test_sharpe": 0.017618105237637394,
            "test_sharpe_canonical": 0.21738930856341535,
            "test_ann_return": 0.02313986450586314,
            "test_max_dd": -0.1370626268829641,
            "test_turnover": 2.2814814814814817,
            "test_trades": 7
          },
          {
            "fold": 14,
            "test_start": "2022-02-11",
            "test_end": "2023-01-30",
            "test_sessions": 242,
            "test_sharpe": -0.20512815658822753,
            "test_sharpe_canonical": -0.00604942288630805,
            "test_ann_return": -0.018863593001848034,
            "test_max_dd": -0.17445383760806366,
            "test_turnover": 1.8743801652892564,
            "test_trades": 6
          },
          {
            "fold": 15,
            "test_start": "2022-08-08",
            "test_end": "2023-07-25",
            "test_sessions": 242,
            "test_sharpe": 0.2112621846322155,
            "test_sharpe_canonical": 0.4111415457332088,
            "test_ann_return": 0.05141687073840395,
            "test_max_dd": -0.13210086230908868,
            "test_turnover": 2.2909090909090915,
            "test_trades": 8
          },
          {
            "fold": 16,
            "test_start": "2023-01-31",
            "test_end": "2024-01-17",
            "test_sessions": 242,
            "test_sharpe": -0.005933969590584664,
            "test_sharpe_canonical": 0.22772372984851547,
            "test_ann_return": 0.019340516031839616,
            "test_max_dd": -0.09640008083550744,
            "test_turnover": 3.748760330578513,
            "test_trades": 12
          },
          {
            "fold": 17,
            "test_start": "2023-07-26",
            "test_end": "2024-07-11",
            "test_sessions": 242,
            "test_sharpe": 1.034872385698726,
            "test_sharpe_canonical": 1.1991940799521588,
            "test_ann_return": 0.13238460672547014,
            "test_max_dd": -0.09640008083550766,
            "test_turnover": 2.9157024793388433,
            "test_trades": 10
          },
          {
            "fold": 18,
            "test_start": "2024-01-18",
            "test_end": "2025-01-03",
            "test_sessions": 243,
            "test_sharpe": 1.4913727272569932,
            "test_sharpe_canonical": 1.571222077585103,
            "test_ann_return": 0.20017377778901024,
            "test_max_dd": -0.07762924672561644,
            "test_turnover": 2.903703703703704,
            "test_trades": 9
          },
          {
            "fold": 19,
            "test_start": "2024-07-12",
            "test_end": "2025-06-30",
            "test_sessions": 242,
            "test_sharpe": 0.47952706967978465,
            "test_sharpe_canonical": 0.6523534078015951,
            "test_ann_return": 0.1028224567448166,
            "test_max_dd": -0.1579714897978245,
            "test_turnover": 3.1239669421487606,
            "test_trades": 10
          },
          {
            "fold": 20,
            "test_start": "2025-01-06",
            "test_end": "2025-12-23",
            "test_sessions": 243,
            "test_sharpe": 0.9759397767866145,
            "test_sharpe_canonical": 1.0927269982085683,
            "test_ann_return": 0.17733107422109629,
            "test_max_dd": -0.15797148979782405,
            "test_turnover": 2.0740740740740744,
            "test_trades": 9
          },
          {
            "fold": 21,
            "test_start": "2025-07-01",
            "test_end": "2026-06-17",
            "test_sessions": 243,
            "test_sharpe": 1.5870895011043684,
            "test_sharpe_canonical": 1.6369375953316205,
            "test_ann_return": 0.22428628423380848,
            "test_max_dd": -0.07743137513579657,
            "test_turnover": 2.696296296296296,
            "test_trades": 9
          }
        ]
      },
      "gates": [
        {
          "gate": "wf_mean_oos_sharpe",
          "threshold": ">= 0.9",
          "observed": 0.586080732009725,
          "status": "FAIL"
        },
        {
          "gate": "positive_fold_rate",
          "threshold": ">= 0.5",
          "observed": 0.7619047619047619,
          "status": "PASS"
        },
        {
          "gate": "pooled_oos_trades",
          "threshold": ">> 100",
          "observed": 166,
          "status": "PASS"
        },
        {
          "gate": "plateau",
          "threshold": ">= 0.667 (>= 2 of 3 lookbacks)",
          "observed": null,
          "status": "NOT EVALUATED",
          "reason": "the 27-configuration robustness grid is out of scope for this cycle (it is a re-optimisation, not a measurement); the plateau gate is reported as NOT EVALUATED, as the published record already does"
        }
      ],
      "decision": {
        "label": "Rejected/Failed",
        "detail": "falsified (gate 1 or gate 2 fails)"
      },
      "folds": 21,
      "independence": {
        "mean_consecutive_overlap_days": 175.0,
        "max_disjoint_test_windows": 11
      }
    },
    "common_inception_window": {
      "wf": {
        "n_folds": 21,
        "mean_test_sharpe": 0.586080732009725,
        "std_test_sharpe": 0.554361059192409,
        "median_test_sharpe": 0.631133614003499,
        "min_test_sharpe": -0.20512815658822753,
        "max_test_sharpe": 1.5870895011043684,
        "pct_positive_sharpe": 0.7619047619047619,
        "mean_test_ann_return": 0.10103795950008797,
        "mean_test_max_dd": -0.1291854358585874,
        "mean_test_trades": 7.904761904761905,
        "total_test_trades": 166,
        "mean_test_sharpe_canonical": 0.757728611295589,
        "folds": [
          {
            "fold": 1,
            "test_start": "2015-11-03",
            "test_end": "2016-10-19",
            "test_sessions": 243,
            "test_sharpe": -0.129822701336185,
            "test_sharpe_canonical": 0.10086541879979755,
            "test_ann_return": 0.005012005137578601,
            "test_max_dd": -0.11745861248135336,
            "test_turnover": 1.4518518518518517,
            "test_trades": 6
          },
          {
            "fold": 2,
            "test_start": "2016-04-27",
            "test_end": "2017-04-13",
            "test_sessions": 244,
            "test_sharpe": 0.6759640583544898,
            "test_sharpe_canonical": 0.9205716053018872,
            "test_ann_return": 0.07735016798668104,
            "test_max_dd": -0.056281523531053645,
            "test_turnover": 2.6852459016393446,
            "test_trades": 7
          },
          {
            "fold": 3,
            "test_start": "2016-10-20",
            "test_end": "2017-10-06",
            "test_sessions": 243,
            "test_sharpe": 1.5339533404250725,
            "test_sharpe_canonical": 1.6957655725589382,
            "test_ann_return": 0.14813808561634256,
            "test_max_dd": -0.0319299042970872,
            "test_turnover": 2.903703703703704,
            "test_trades": 7
          },
          {
            "fold": 4,
            "test_start": "2017-04-14",
            "test_end": "2018-04-02",
            "test_sessions": 242,
            "test_sharpe": 0.7117773159981329,
            "test_sharpe_canonical": 0.8901304213669123,
            "test_ann_return": 0.10907503411639285,
            "test_max_dd": -0.1007211679280452,
            "test_turnover": 1.2495867768595041,
            "test_trades": 5
          },
          {
            "fold": 5,
            "test_start": "2017-10-09",
            "test_end": "2018-09-25",
            "test_sessions": 243,
            "test_sharpe": 0.631133614003499,
            "test_sharpe_canonical": 0.811105102410711,
            "test_ann_return": 0.1032664421134073,
            "test_max_dd": -0.10072116792804509,
            "test_turnover": 1.6592592592592594,
            "test_trades": 7
          },
          {
            "fold": 6,
            "test_start": "2018-04-03",
            "test_end": "2019-03-20",
            "test_sessions": 243,
            "test_sharpe": -0.05124303302635702,
            "test_sharpe_canonical": 0.1550775898976611,
            "test_ann_return": 0.012137264379967982,
            "test_max_dd": -0.21977920561691966,
            "test_turnover": 2.4888888888888894,
            "test_trades": 8
          },
          {
            "fold": 7,
            "test_start": "2018-09-26",
            "test_end": "2019-09-12",
            "test_sessions": 242,
            "test_sharpe": -0.11738315853351025,
            "test_sharpe_canonical": 0.08962718770103004,
            "test_ann_return": 0.0020624379978750884,
            "test_max_dd": -0.21977920561691933,
            "test_turnover": 2.4991735537190083,
            "test_trades": 9
          },
          {
            "fold": 8,
            "test_start": "2019-03-21",
            "test_end": "2020-03-06",
            "test_sessions": 243,
            "test_sharpe": 0.5276044423756984,
            "test_sharpe_canonical": 0.7245136731118775,
            "test_ann_return": 0.08463855767006012,
            "test_max_dd": -0.1253768922505898,
            "test_turnover": 2.696296296296296,
            "test_trades": 10
          },
          {
            "fold": 9,
            "test_start": "2019-09-13",
            "test_end": "2020-08-31",
            "test_sessions": 244,
            "test_sharpe": 0.5110655618517029,
            "test_sharpe_canonical": 0.6779910498653653,
            "test_ann_return": 0.15423801927772374,
            "test_max_dd": -0.2940018681631914,
            "test_turnover": 2.478688524590164,
            "test_trades": 8
          },
          {
            "fold": 10,
            "test_start": "2020-03-09",
            "test_end": "2021-02-23",
            "test_sessions": 243,
            "test_sharpe": 0.8813362025342762,
            "test_sharpe_canonical": 0.9861934814848404,
            "test_ann_return": 0.2516078998752891,
            "test_max_dd": -0.1902617222839591,
            "test_turnover": 1.2444444444444447,
            "test_trades": 5
          },
          {
            "fold": 11,
            "test_start": "2020-09-01",
            "test_end": "2021-08-18",
            "test_sessions": 243,
            "test_sharpe": 0.8615838470971496,
            "test_sharpe_canonical": 1.0098581885287328,
            "test_ann_return": 0.1406703437212049,
            "test_max_dd": -0.07346374391202781,
            "test_turnover": 1.8666666666666667,
            "test_trades": 6
          },
          {
            "fold": 12,
            "test_start": "2021-02-24",
            "test_end": "2022-02-10",
            "test_sessions": 245,
            "test_sharpe": 0.6851062582427301,
            "test_sharpe_canonical": 0.8479622260417375,
            "test_ann_return": 0.12156903362086391,
            "test_max_dd": -0.07569804909295141,
            "test_turnover": 2.468571428571429,
            "test_trades": 8
          },
          {
            "fold": 13,
            "test_start": "2021-08-19",
            "test_end": "2022-08-05",
            "test_sessions": 243,
            "test_sharpe": 0.017618105237637394,
            "test_sharpe_canonical": 0.21738930856341535,
            "test_ann_return": 0.02313986450586314,
            "test_max_dd": -0.1370626268829641,
            "test_turnover": 2.2814814814814817,
            "test_trades": 7
          },
          {
            "fold": 14,
            "test_start": "2022-02-11",
            "test_end": "2023-01-30",
            "test_sessions": 242,
            "test_sharpe": -0.20512815658822753,
            "test_sharpe_canonical": -0.00604942288630805,
            "test_ann_return": -0.018863593001848034,
            "test_max_dd": -0.17445383760806366,
            "test_turnover": 1.8743801652892564,
            "test_trades": 6
          },
          {
            "fold": 15,
            "test_start": "2022-08-08",
            "test_end": "2023-07-25",
            "test_sessions": 242,
            "test_sharpe": 0.2112621846322155,
            "test_sharpe_canonical": 0.4111415457332088,
            "test_ann_return": 0.05141687073840395,
            "test_max_dd": -0.13210086230908868,
            "test_turnover": 2.2909090909090915,
            "test_trades": 8
          },
          {
            "fold": 16,
            "test_start": "2023-01-31",
            "test_end": "2024-01-17",
            "test_sessions": 242,
            "test_sharpe": -0.005933969590584664,
            "test_sharpe_canonical": 0.22772372984851547,
            "test_ann_return": 0.019340516031839616,
            "test_max_dd": -0.09640008083550744,
            "test_turnover": 3.748760330578513,
            "test_trades": 12
          },
          {
            "fold": 17,
            "test_start": "2023-07-26",
            "test_end": "2024-07-11",
            "test_sessions": 242,
            "test_sharpe": 1.034872385698726,
            "test_sharpe_canonical": 1.1991940799521588,
            "test_ann_return": 0.13238460672547014,
            "test_max_dd": -0.09640008083550766,
            "test_turnover": 2.9157024793388433,
            "test_trades": 10
          },
          {
            "fold": 18,
            "test_start": "2024-01-18",
            "test_end": "2025-01-03",
            "test_sessions": 243,
            "test_sharpe": 1.4913727272569932,
            "test_sharpe_canonical": 1.571222077585103,
            "test_ann_return": 0.20017377778901024,
            "test_max_dd": -0.07762924672561644,
            "test_turnover": 2.903703703703704,
            "test_trades": 9
          },
          {
            "fold": 19,
            "test_start": "2024-07-12",
            "test_end": "2025-06-30",
            "test_sessions": 242,
            "test_sharpe": 0.47952706967978465,
            "test_sharpe_canonical": 0.6523534078015951,
            "test_ann_return": 0.1028224567448166,
            "test_max_dd": -0.1579714897978245,
            "test_turnover": 3.1239669421487606,
            "test_trades": 10
          },
          {
            "fold": 20,
            "test_start": "2025-01-06",
            "test_end": "2025-12-23",
            "test_sessions": 243,
            "test_sharpe": 0.9759397767866145,
            "test_sharpe_canonical": 1.0927269982085683,
            "test_ann_return": 0.17733107422109629,
            "test_max_dd": -0.15797148979782405,
            "test_turnover": 2.0740740740740744,
            "test_trades": 9
          },
          {
            "fold": 21,
            "test_start": "2025-07-01",
            "test_end": "2026-06-17",
            "test_sessions": 243,
            "test_sharpe": 1.5870895011043684,
            "test_sharpe_canonical": 1.6369375953316205,
            "test_ann_return": 0.22428628423380848,
            "test_max_dd": -0.07743137513579657,
            "test_turnover": 2.696296296296296,
            "test_trades": 9
          }
        ]
      },
      "gates": [
        {
          "gate": "wf_mean_oos_sharpe",
          "threshold": ">= 0.9",
          "observed": 0.586080732009725,
          "status": "FAIL"
        },
        {
          "gate": "positive_fold_rate",
          "threshold": ">= 0.5",
          "observed": 0.7619047619047619,
          "status": "PASS"
        },
        {
          "gate": "pooled_oos_trades",
          "threshold": ">> 100",
          "observed": 166,
          "status": "PASS"
        },
        {
          "gate": "plateau",
          "threshold": ">= 0.667 (>= 2 of 3 lookbacks)",
          "observed": null,
          "status": "NOT EVALUATED",
          "reason": "the 27-configuration robustness grid is out of scope for this cycle (it is a re-optimisation, not a measurement); the plateau gate is reported as NOT EVALUATED, as the published record already does"
        }
      ],
      "decision": {
        "label": "Rejected/Failed",
        "detail": "falsified (gate 1 or gate 2 fails)"
      },
      "folds": 21,
      "independence": {
        "mean_consecutive_overlap_days": 175.0,
        "max_disjoint_test_windows": 11
      }
    }
  },
  "design_a_nonoverlapping": {
    "union_sample": {
      "wf": {
        "n_folds": 24,
        "mean_test_sharpe": 0.6982984362427751,
        "std_test_sharpe": 0.7940609358229938,
        "median_test_sharpe": 0.6352452578300773,
        "min_test_sharpe": -0.8567738850188672,
        "max_test_sharpe": 2.4473493123037615,
        "pct_positive_sharpe": 0.7916666666666666,
        "mean_test_ann_return": 0.10291874621033141,
        "mean_test_max_dd": -0.12909997532210168,
        "mean_test_trades": 8.291666666666666,
        "total_test_trades": 199,
        "mean_test_sharpe_canonical": 0.8432742147927629,
        "folds": [
          {
            "fold": 1,
            "test_start": "2002-09-30",
            "test_end": "2003-09-16",
            "test_sessions": 243,
            "test_sharpe": 1.1121582256222222,
            "test_sharpe_canonical": 1.1847608618398233,
            "test_ann_return": 0.24338207942578305,
            "test_max_dd": -0.14265741312216396,
            "test_turnover": 3.814814814814815,
            "test_trades": 10
          },
          {
            "fold": 2,
            "test_start": "2003-09-17",
            "test_end": "2004-09-02",
            "test_sessions": 243,
            "test_sharpe": 0.5510622508974872,
            "test_sharpe_canonical": 0.7301566223532905,
            "test_ann_return": 0.09888742015760066,
            "test_max_dd": -0.08720505524401456,
            "test_turnover": 3.6296296296296298,
            "test_trades": 9
          },
          {
            "fold": 3,
            "test_start": "2004-09-03",
            "test_end": "2005-08-22",
            "test_sessions": 244,
            "test_sharpe": 1.499876469611883,
            "test_sharpe_canonical": 1.58702274390774,
            "test_ann_return": 0.19376625264210334,
            "test_max_dd": -0.08879207214055351,
            "test_turnover": 2.581967213114754,
            "test_trades": 8
          },
          {
            "fold": 4,
            "test_start": "2005-08-23",
            "test_end": "2006-08-09",
            "test_sessions": 243,
            "test_sharpe": 0.5914958760019136,
            "test_sharpe_canonical": 0.763170967335054,
            "test_ann_return": 0.1082883117402873,
            "test_max_dd": -0.14251903837549496,
            "test_turnover": 3.744855967078189,
            "test_trades": 11
          },
          {
            "fold": 5,
            "test_start": "2006-08-10",
            "test_end": "2007-07-27",
            "test_sessions": 242,
            "test_sharpe": 0.8262041017731879,
            "test_sharpe_canonical": 0.993593637597982,
            "test_ann_return": 0.12266702958293396,
            "test_max_dd": -0.07287049457391714,
            "test_turnover": 4.026446280991736,
            "test_trades": 11
          },
          {
            "fold": 6,
            "test_start": "2007-07-30",
            "test_end": "2008-07-15",
            "test_sessions": 243,
            "test_sharpe": 0.09743325025298999,
            "test_sharpe_canonical": 0.2937757413426074,
            "test_ann_return": 0.038331982502398,
            "test_max_dd": -0.11808354095384432,
            "test_turnover": 1.8666666666666667,
            "test_trades": 8
          },
          {
            "fold": 7,
            "test_start": "2008-07-16",
            "test_end": "2009-07-02",
            "test_sessions": 244,
            "test_sharpe": -0.8567738850188672,
            "test_sharpe_canonical": -0.7551626381571066,
            "test_ann_return": -0.24797671992759973,
            "test_max_dd": -0.3845015275385357,
            "test_turnover": 2.0655737704918034,
            "test_trades": 8
          },
          {
            "fold": 8,
            "test_start": "2009-07-03",
            "test_end": "2010-06-21",
            "test_sessions": 243,
            "test_sharpe": 1.2976065459789101,
            "test_sharpe_canonical": 1.3355871405185837,
            "test_ann_return": 0.27326825148885203,
            "test_max_dd": -0.15110728630414993,
            "test_turnover": 2.2814814814814817,
            "test_trades": 7
          },
          {
            "fold": 9,
            "test_start": "2010-06-22",
            "test_end": "2011-06-08",
            "test_sessions": 244,
            "test_sharpe": 0.885280636825139,
            "test_sharpe_canonical": 1.0188984605484885,
            "test_ann_return": 0.15819391348880774,
            "test_max_dd": -0.07820715353923557,
            "test_turnover": 3.5114754098360654,
            "test_trades": 11
          },
          {
            "fold": 10,
            "test_start": "2011-06-09",
            "test_end": "2012-05-25",
            "test_sessions": 244,
            "test_sharpe": -0.11832601380435821,
            "test_sharpe_canonical": 0.08217590761651598,
            "test_ann_return": -0.004853001337003282,
            "test_max_dd": -0.1962932686347152,
            "test_turnover": 2.0655737704918034,
            "test_trades": 6
          },
          {
            "fold": 11,
            "test_start": "2012-05-28",
            "test_end": "2013-05-14",
            "test_sessions": 241,
            "test_sharpe": 2.064773735904461,
            "test_sharpe_canonical": 2.0757926837083205,
            "test_ann_return": 0.2378224365020405,
            "test_max_dd": -0.06912622799280044,
            "test_turnover": 2.7186721991701246,
            "test_trades": 9
          },
          {
            "fold": 12,
            "test_start": "2013-05-15",
            "test_end": "2014-05-01",
            "test_sessions": 243,
            "test_sharpe": 0.8950327298125819,
            "test_sharpe_canonical": 1.055381317712991,
            "test_ann_return": 0.13051466278956458,
            "test_max_dd": -0.0724113063230637,
            "test_turnover": 1.8666666666666667,
            "test_trades": 7
          },
          {
            "fold": 13,
            "test_start": "2014-05-02",
            "test_end": "2015-04-20",
            "test_sessions": 243,
            "test_sharpe": 0.8670941479237154,
            "test_sharpe_canonical": 1.0504759867998104,
            "test_ann_return": 0.1137650110178221,
            "test_max_dd": -0.08364478241975704,
            "test_turnover": 2.2814814814814817,
            "test_trades": 8
          },
          {
            "fold": 14,
            "test_start": "2015-04-21",
            "test_end": "2016-04-06",
            "test_sessions": 243,
            "test_sharpe": -0.23854812887090193,
            "test_sharpe_canonical": -0.02803236394743473,
            "test_ann_return": -0.014097384931297419,
            "test_max_dd": -0.124244048685489,
            "test_turnover": 1.866666666666667,
            "test_trades": 8
          },
          {
            "fold": 15,
            "test_start": "2016-04-07",
            "test_end": "2017-03-24",
            "test_sessions": 244,
            "test_sharpe": 0.599656542337908,
            "test_sharpe_canonical": 0.8500132891298856,
            "test_ann_return": 0.07075140460828355,
            "test_max_dd": -0.05628152353105287,
            "test_turnover": 2.6852459016393446,
            "test_trades": 7
          },
          {
            "fold": 16,
            "test_start": "2017-03-27",
            "test_end": "2018-03-13",
            "test_sessions": 243,
            "test_sharpe": 1.5319626020480195,
            "test_sharpe_canonical": 1.6234425890716693,
            "test_ann_return": 0.1902354194901812,
            "test_max_dd": -0.1007211679280452,
            "test_turnover": 1.2444444444444447,
            "test_trades": 5
          },
          {
            "fold": 17,
            "test_start": "2018-03-14",
            "test_end": "2019-02-28",
            "test_sessions": 242,
            "test_sharpe": -0.5647770603202239,
            "test_sharpe_canonical": -0.3777698638595333,
            "test_ann_return": -0.072412123406984,
            "test_max_dd": -0.21977920561691922,
            "test_turnover": 2.2909090909090915,
            "test_trades": 7
          },
          {
            "fold": 18,
            "test_start": "2019-03-01",
            "test_end": "2020-02-17",
            "test_sessions": 243,
            "test_sharpe": 2.4473493123037615,
            "test_sharpe_canonical": 2.452559291305073,
            "test_ann_return": 0.23209969224624127,
            "test_max_dd": -0.04239774207595359,
            "test_turnover": 2.2814814814814817,
            "test_trades": 9
          },
          {
            "fold": 19,
            "test_start": "2020-02-18",
            "test_end": "2021-02-03",
            "test_sessions": 244,
            "test_sharpe": 0.35813513179384626,
            "test_sharpe_canonical": 0.5453433247219177,
            "test_ann_return": 0.11887713254809196,
            "test_max_dd": -0.2939166402872937,
            "test_turnover": 1.6524590163934427,
            "test_trades": 6
          },
          {
            "fold": 20,
            "test_start": "2021-02-04",
            "test_end": "2022-01-21",
            "test_sessions": 244,
            "test_sharpe": 0.42921977006247863,
            "test_sharpe_canonical": 0.6179399292697632,
            "test_ann_return": 0.08181944848173361,
            "test_max_dd": -0.06718525747642823,
            "test_turnover": 2.478688524590164,
            "test_trades": 8
          },
          {
            "fold": 21,
            "test_start": "2022-01-24",
            "test_end": "2023-01-10",
            "test_sessions": 243,
            "test_sharpe": -0.03469383928587136,
            "test_sharpe_canonical": 0.164746474272295,
            "test_ann_return": 0.013346987524904597,
            "test_max_dd": -0.17445383760806377,
            "test_turnover": 1.866666666666667,
            "test_trades": 6
          },
          {
            "fold": 22,
            "test_start": "2023-01-11",
            "test_end": "2023-12-28",
            "test_sessions": 243,
            "test_sharpe": 0.2912235240848116,
            "test_sharpe_canonical": 0.5141090899061407,
            "test_ann_return": 0.05250991953186235,
            "test_max_dd": -0.09640008083550777,
            "test_turnover": 3.5259259259259266,
            "test_trades": 11
          },
          {
            "fold": 23,
            "test_start": "2023-12-29",
            "test_end": "2024-12-16",
            "test_sessions": 243,
            "test_sharpe": 1.5558825705692616,
            "test_sharpe_canonical": 1.634650761449344,
            "test_ann_return": 0.19963496409630221,
            "test_max_dd": -0.07762924672561688,
            "test_turnover": 3.111111111111111,
            "test_trades": 10
          },
          {
            "fold": 24,
            "test_start": "2024-12-17",
            "test_end": "2025-12-03",
            "test_sessions": 241,
            "test_sharpe": 0.6708339733222468,
            "test_sharpe_canonical": 0.825949200583089,
            "test_ann_return": 0.13122681878504405,
            "test_max_dd": -0.15797148979782405,
            "test_turnover": 2.091286307053942,
            "test_trades": 9
          }
        ]
      },
      "gates": [
        {
          "gate": "wf_mean_oos_sharpe",
          "threshold": ">= 0.9",
          "observed": 0.6982984362427751,
          "status": "FAIL"
        },
        {
          "gate": "positive_fold_rate",
          "threshold": ">= 0.5",
          "observed": 0.7916666666666666,
          "status": "PASS"
        },
        {
          "gate": "pooled_oos_trades",
          "threshold": ">> 100",
          "observed": 199,
          "status": "PASS"
        },
        {
          "gate": "plateau",
          "threshold": ">= 0.667 (>= 2 of 3 lookbacks)",
          "observed": null,
          "status": "NOT EVALUATED",
          "reason": "the 27-configuration robustness grid is out of scope for this cycle (it is a re-optimisation, not a measurement); the plateau gate is reported as NOT EVALUATED, as the published record already does"
        }
      ],
      "decision": {
        "label": "Rejected/Failed",
        "detail": "falsified (gate 1 or gate 2 fails)"
      },
      "folds": 24,
      "independence": {
        "mean_consecutive_overlap_days": 0.0,
        "max_disjoint_test_windows": 24
      },
      "rows": [
        {
          "fold": 1,
          "test_start": "2002-09-30",
          "test_end": "2003-09-16",
          "test_sessions": 243,
          "test_sharpe": 1.1121582256222222,
          "test_sharpe_canonical": 1.1847608618398233,
          "test_ann_return": 0.24338207942578305,
          "test_max_dd": -0.14265741312216396,
          "test_turnover": 3.814814814814815,
          "test_trades": 10
        },
        {
          "fold": 2,
          "test_start": "2003-09-17",
          "test_end": "2004-09-02",
          "test_sessions": 243,
          "test_sharpe": 0.5510622508974872,
          "test_sharpe_canonical": 0.7301566223532905,
          "test_ann_return": 0.09888742015760066,
          "test_max_dd": -0.08720505524401456,
          "test_turnover": 3.6296296296296298,
          "test_trades": 9
        },
        {
          "fold": 3,
          "test_start": "2004-09-03",
          "test_end": "2005-08-22",
          "test_sessions": 244,
          "test_sharpe": 1.499876469611883,
          "test_sharpe_canonical": 1.58702274390774,
          "test_ann_return": 0.19376625264210334,
          "test_max_dd": -0.08879207214055351,
          "test_turnover": 2.581967213114754,
          "test_trades": 8
        },
        {
          "fold": 4,
          "test_start": "2005-08-23",
          "test_end": "2006-08-09",
          "test_sessions": 243,
          "test_sharpe": 0.5914958760019136,
          "test_sharpe_canonical": 0.763170967335054,
          "test_ann_return": 0.1082883117402873,
          "test_max_dd": -0.14251903837549496,
          "test_turnover": 3.744855967078189,
          "test_trades": 11
        },
        {
          "fold": 5,
          "test_start": "2006-08-10",
          "test_end": "2007-07-27",
          "test_sessions": 242,
          "test_sharpe": 0.8262041017731879,
          "test_sharpe_canonical": 0.993593637597982,
          "test_ann_return": 0.12266702958293396,
          "test_max_dd": -0.07287049457391714,
          "test_turnover": 4.026446280991736,
          "test_trades": 11
        },
        {
          "fold": 6,
          "test_start": "2007-07-30",
          "test_end": "2008-07-15",
          "test_sessions": 243,
          "test_sharpe": 0.09743325025298999,
          "test_sharpe_canonical": 0.2937757413426074,
          "test_ann_return": 0.038331982502398,
          "test_max_dd": -0.11808354095384432,
          "test_turnover": 1.8666666666666667,
          "test_trades": 8
        },
        {
          "fold": 7,
          "test_start": "2008-07-16",
          "test_end": "2009-07-02",
          "test_sessions": 244,
          "test_sharpe": -0.8567738850188672,
          "test_sharpe_canonical": -0.7551626381571066,
          "test_ann_return": -0.24797671992759973,
          "test_max_dd": -0.3845015275385357,
          "test_turnover": 2.0655737704918034,
          "test_trades": 8
        },
        {
          "fold": 8,
          "test_start": "2009-07-03",
          "test_end": "2010-06-21",
          "test_sessions": 243,
          "test_sharpe": 1.2976065459789101,
          "test_sharpe_canonical": 1.3355871405185837,
          "test_ann_return": 0.27326825148885203,
          "test_max_dd": -0.15110728630414993,
          "test_turnover": 2.2814814814814817,
          "test_trades": 7
        },
        {
          "fold": 9,
          "test_start": "2010-06-22",
          "test_end": "2011-06-08",
          "test_sessions": 244,
          "test_sharpe": 0.885280636825139,
          "test_sharpe_canonical": 1.0188984605484885,
          "test_ann_return": 0.15819391348880774,
          "test_max_dd": -0.07820715353923557,
          "test_turnover": 3.5114754098360654,
          "test_trades": 11
        },
        {
          "fold": 10,
          "test_start": "2011-06-09",
          "test_end": "2012-05-25",
          "test_sessions": 244,
          "test_sharpe": -0.11832601380435821,
          "test_sharpe_canonical": 0.08217590761651598,
          "test_ann_return": -0.004853001337003282,
          "test_max_dd": -0.1962932686347152,
          "test_turnover": 2.0655737704918034,
          "test_trades": 6
        },
        {
          "fold": 11,
          "test_start": "2012-05-28",
          "test_end": "2013-05-14",
          "test_sessions": 241,
          "test_sharpe": 2.064773735904461,
          "test_sharpe_canonical": 2.0757926837083205,
          "test_ann_return": 0.2378224365020405,
          "test_max_dd": -0.06912622799280044,
          "test_turnover": 2.7186721991701246,
          "test_trades": 9
        },
        {
          "fold": 12,
          "test_start": "2013-05-15",
          "test_end": "2014-05-01",
          "test_sessions": 243,
          "test_sharpe": 0.8950327298125819,
          "test_sharpe_canonical": 1.055381317712991,
          "test_ann_return": 0.13051466278956458,
          "test_max_dd": -0.0724113063230637,
          "test_turnover": 1.8666666666666667,
          "test_trades": 7
        },
        {
          "fold": 13,
          "test_start": "2014-05-02",
          "test_end": "2015-04-20",
          "test_sessions": 243,
          "test_sharpe": 0.8670941479237154,
          "test_sharpe_canonical": 1.0504759867998104,
          "test_ann_return": 0.1137650110178221,
          "test_max_dd": -0.08364478241975704,
          "test_turnover": 2.2814814814814817,
          "test_trades": 8
        },
        {
          "fold": 14,
          "test_start": "2015-04-21",
          "test_end": "2016-04-06",
          "test_sessions": 243,
          "test_sharpe": -0.23854812887090193,
          "test_sharpe_canonical": -0.02803236394743473,
          "test_ann_return": -0.014097384931297419,
          "test_max_dd": -0.124244048685489,
          "test_turnover": 1.866666666666667,
          "test_trades": 8
        },
        {
          "fold": 15,
          "test_start": "2016-04-07",
          "test_end": "2017-03-24",
          "test_sessions": 244,
          "test_sharpe": 0.599656542337908,
          "test_sharpe_canonical": 0.8500132891298856,
          "test_ann_return": 0.07075140460828355,
          "test_max_dd": -0.05628152353105287,
          "test_turnover": 2.6852459016393446,
          "test_trades": 7
        },
        {
          "fold": 16,
          "test_start": "2017-03-27",
          "test_end": "2018-03-13",
          "test_sessions": 243,
          "test_sharpe": 1.5319626020480195,
          "test_sharpe_canonical": 1.6234425890716693,
          "test_ann_return": 0.1902354194901812,
          "test_max_dd": -0.1007211679280452,
          "test_turnover": 1.2444444444444447,
          "test_trades": 5
        },
        {
          "fold": 17,
          "test_start": "2018-03-14",
          "test_end": "2019-02-28",
          "test_sessions": 242,
          "test_sharpe": -0.5647770603202239,
          "test_sharpe_canonical": -0.3777698638595333,
          "test_ann_return": -0.072412123406984,
          "test_max_dd": -0.21977920561691922,
          "test_turnover": 2.2909090909090915,
          "test_trades": 7
        },
        {
          "fold": 18,
          "test_start": "2019-03-01",
          "test_end": "2020-02-17",
          "test_sessions": 243,
          "test_sharpe": 2.4473493123037615,
          "test_sharpe_canonical": 2.452559291305073,
          "test_ann_return": 0.23209969224624127,
          "test_max_dd": -0.04239774207595359,
          "test_turnover": 2.2814814814814817,
          "test_trades": 9
        },
        {
          "fold": 19,
          "test_start": "2020-02-18",
          "test_end": "2021-02-03",
          "test_sessions": 244,
          "test_sharpe": 0.35813513179384626,
          "test_sharpe_canonical": 0.5453433247219177,
          "test_ann_return": 0.11887713254809196,
          "test_max_dd": -0.2939166402872937,
          "test_turnover": 1.6524590163934427,
          "test_trades": 6
        },
        {
          "fold": 20,
          "test_start": "2021-02-04",
          "test_end": "2022-01-21",
          "test_sessions": 244,
          "test_sharpe": 0.42921977006247863,
          "test_sharpe_canonical": 0.6179399292697632,
          "test_ann_return": 0.08181944848173361,
          "test_max_dd": -0.06718525747642823,
          "test_turnover": 2.478688524590164,
          "test_trades": 8
        },
        {
          "fold": 21,
          "test_start": "2022-01-24",
          "test_end": "2023-01-10",
          "test_sessions": 243,
          "test_sharpe": -0.03469383928587136,
          "test_sharpe_canonical": 0.164746474272295,
          "test_ann_return": 0.013346987524904597,
          "test_max_dd": -0.17445383760806377,
          "test_turnover": 1.866666666666667,
          "test_trades": 6
        },
        {
          "fold": 22,
          "test_start": "2023-01-11",
          "test_end": "2023-12-28",
          "test_sessions": 243,
          "test_sharpe": 0.2912235240848116,
          "test_sharpe_canonical": 0.5141090899061407,
          "test_ann_return": 0.05250991953186235,
          "test_max_dd": -0.09640008083550777,
          "test_turnover": 3.5259259259259266,
          "test_trades": 11
        },
        {
          "fold": 23,
          "test_start": "2023-12-29",
          "test_end": "2024-12-16",
          "test_sessions": 243,
          "test_sharpe": 1.5558825705692616,
          "test_sharpe_canonical": 1.634650761449344,
          "test_ann_return": 0.19963496409630221,
          "test_max_dd": -0.07762924672561688,
          "test_turnover": 3.111111111111111,
          "test_trades": 10
        },
        {
          "fold": 24,
          "test_start": "2024-12-17",
          "test_end": "2025-12-03",
          "test_sessions": 241,
          "test_sharpe": 0.6708339733222468,
          "test_sharpe_canonical": 0.825949200583089,
          "test_ann_return": 0.13122681878504405,
          "test_max_dd": -0.15797148979782405,
          "test_turnover": 2.091286307053942,
          "test_trades": 9
        }
      ]
    },
    "common_inception_slice": {
      "wf": {
        "n_folds": 11,
        "mean_test_sharpe": 0.601899977260042,
        "std_test_sharpe": 0.6053984483184842,
        "median_test_sharpe": 0.5110655618517029,
        "min_test_sharpe": -0.129822701336185,
        "max_test_sharpe": 1.5870895011043684,
        "pct_positive_sharpe": 0.8181818181818182,
        "mean_test_ann_return": 0.09885794698295404,
        "mean_test_max_dd": -0.1307564488508914,
        "mean_test_trades": 7.909090909090909,
        "total_test_trades": 87,
        "mean_test_sharpe_canonical": 0.7729298597496885,
        "folds": [
          {
            "fold": 1,
            "test_start": "2015-11-03",
            "test_end": "2016-10-19",
            "test_sessions": 243,
            "test_sharpe": -0.129822701336185,
            "test_sharpe_canonical": 0.10086541879979755,
            "test_ann_return": 0.005012005137578601,
            "test_max_dd": -0.11745861248135336,
            "test_turnover": 1.4518518518518517,
            "test_trades": 6
          },
          {
            "fold": 2,
            "test_start": "2016-10-20",
            "test_end": "2017-10-06",
            "test_sessions": 243,
            "test_sharpe": 1.5339533404250725,
            "test_sharpe_canonical": 1.6957655725589382,
            "test_ann_return": 0.14813808561634256,
            "test_max_dd": -0.0319299042970872,
            "test_turnover": 2.903703703703704,
            "test_trades": 7
          },
          {
            "fold": 3,
            "test_start": "2017-10-09",
            "test_end": "2018-09-25",
            "test_sessions": 243,
            "test_sharpe": 0.631133614003499,
            "test_sharpe_canonical": 0.811105102410711,
            "test_ann_return": 0.1032664421134073,
            "test_max_dd": -0.10072116792804509,
            "test_turnover": 1.6592592592592594,
            "test_trades": 7
          },
          {
            "fold": 4,
            "test_start": "2018-09-26",
            "test_end": "2019-09-12",
            "test_sessions": 242,
            "test_sharpe": -0.11738315853351025,
            "test_sharpe_canonical": 0.08962718770103004,
            "test_ann_return": 0.0020624379978750884,
            "test_max_dd": -0.21977920561691933,
            "test_turnover": 2.4991735537190083,
            "test_trades": 9
          },
          {
            "fold": 5,
            "test_start": "2019-09-13",
            "test_end": "2020-08-31",
            "test_sessions": 244,
            "test_sharpe": 0.5110655618517029,
            "test_sharpe_canonical": 0.6779910498653653,
            "test_ann_return": 0.15423801927772374,
            "test_max_dd": -0.2940018681631914,
            "test_turnover": 2.478688524590164,
            "test_trades": 8
          },
          {
            "fold": 6,
            "test_start": "2020-09-01",
            "test_end": "2021-08-18",
            "test_sessions": 243,
            "test_sharpe": 0.8615838470971496,
            "test_sharpe_canonical": 1.0098581885287328,
            "test_ann_return": 0.1406703437212049,
            "test_max_dd": -0.07346374391202781,
            "test_turnover": 1.8666666666666667,
            "test_trades": 6
          },
          {
            "fold": 7,
            "test_start": "2021-08-19",
            "test_end": "2022-08-05",
            "test_sessions": 243,
            "test_sharpe": 0.017618105237637394,
            "test_sharpe_canonical": 0.21738930856341535,
            "test_ann_return": 0.02313986450586314,
            "test_max_dd": -0.1370626268829641,
            "test_turnover": 2.2814814814814817,
            "test_trades": 7
          },
          {
            "fold": 8,
            "test_start": "2022-08-08",
            "test_end": "2023-07-25",
            "test_sessions": 242,
            "test_sharpe": 0.2112621846322155,
            "test_sharpe_canonical": 0.4111415457332088,
            "test_ann_return": 0.05141687073840395,
            "test_max_dd": -0.13210086230908868,
            "test_turnover": 2.2909090909090915,
            "test_trades": 8
          },
          {
            "fold": 9,
            "test_start": "2023-07-26",
            "test_end": "2024-07-11",
            "test_sessions": 242,
            "test_sharpe": 1.034872385698726,
            "test_sharpe_canonical": 1.1991940799521588,
            "test_ann_return": 0.13238460672547014,
            "test_max_dd": -0.09640008083550766,
            "test_turnover": 2.9157024793388433,
            "test_trades": 10
          },
          {
            "fold": 10,
            "test_start": "2024-07-12",
            "test_end": "2025-06-30",
            "test_sessions": 242,
            "test_sharpe": 0.47952706967978465,
            "test_sharpe_canonical": 0.6523534078015951,
            "test_ann_return": 0.1028224567448166,
            "test_max_dd": -0.1579714897978245,
            "test_turnover": 3.1239669421487606,
            "test_trades": 10
          },
          {
            "fold": 11,
            "test_start": "2025-07-01",
            "test_end": "2026-06-17",
            "test_sessions": 243,
            "test_sharpe": 1.5870895011043684,
            "test_sharpe_canonical": 1.6369375953316205,
            "test_ann_return": 0.22428628423380848,
            "test_max_dd": -0.07743137513579657,
            "test_turnover": 2.696296296296296,
            "test_trades": 9
          }
        ]
      },
      "gates": [
        {
          "gate": "wf_mean_oos_sharpe",
          "threshold": ">= 0.9",
          "observed": 0.601899977260042,
          "status": "FAIL"
        },
        {
          "gate": "positive_fold_rate",
          "threshold": ">= 0.5",
          "observed": 0.8181818181818182,
          "status": "PASS"
        },
        {
          "gate": "pooled_oos_trades",
          "threshold": ">> 100",
          "observed": 87,
          "status": "FAIL"
        },
        {
          "gate": "plateau",
          "threshold": ">= 0.667 (>= 2 of 3 lookbacks)",
          "observed": null,
          "status": "NOT EVALUATED",
          "reason": "the 27-configuration robustness grid is out of scope for this cycle (it is a re-optimisation, not a measurement); the plateau gate is reported as NOT EVALUATED, as the published record already does"
        }
      ],
      "decision": {
        "label": "Rejected/Failed",
        "detail": "falsified (gate 1 or gate 2 fails)"
      },
      "folds": 11,
      "independence": {
        "mean_consecutive_overlap_days": 0.0,
        "max_disjoint_test_windows": 11
      },
      "rows": [
        {
          "fold": 1,
          "test_start": "2015-11-03",
          "test_end": "2016-10-19",
          "test_sessions": 243,
          "test_sharpe": -0.129822701336185,
          "test_sharpe_canonical": 0.10086541879979755,
          "test_ann_return": 0.005012005137578601,
          "test_max_dd": -0.11745861248135336,
          "test_turnover": 1.4518518518518517,
          "test_trades": 6
        },
        {
          "fold": 2,
          "test_start": "2016-10-20",
          "test_end": "2017-10-06",
          "test_sessions": 243,
          "test_sharpe": 1.5339533404250725,
          "test_sharpe_canonical": 1.6957655725589382,
          "test_ann_return": 0.14813808561634256,
          "test_max_dd": -0.0319299042970872,
          "test_turnover": 2.903703703703704,
          "test_trades": 7
        },
        {
          "fold": 3,
          "test_start": "2017-10-09",
          "test_end": "2018-09-25",
          "test_sessions": 243,
          "test_sharpe": 0.631133614003499,
          "test_sharpe_canonical": 0.811105102410711,
          "test_ann_return": 0.1032664421134073,
          "test_max_dd": -0.10072116792804509,
          "test_turnover": 1.6592592592592594,
          "test_trades": 7
        },
        {
          "fold": 4,
          "test_start": "2018-09-26",
          "test_end": "2019-09-12",
          "test_sessions": 242,
          "test_sharpe": -0.11738315853351025,
          "test_sharpe_canonical": 0.08962718770103004,
          "test_ann_return": 0.0020624379978750884,
          "test_max_dd": -0.21977920561691933,
          "test_turnover": 2.4991735537190083,
          "test_trades": 9
        },
        {
          "fold": 5,
          "test_start": "2019-09-13",
          "test_end": "2020-08-31",
          "test_sessions": 244,
          "test_sharpe": 0.5110655618517029,
          "test_sharpe_canonical": 0.6779910498653653,
          "test_ann_return": 0.15423801927772374,
          "test_max_dd": -0.2940018681631914,
          "test_turnover": 2.478688524590164,
          "test_trades": 8
        },
        {
          "fold": 6,
          "test_start": "2020-09-01",
          "test_end": "2021-08-18",
          "test_sessions": 243,
          "test_sharpe": 0.8615838470971496,
          "test_sharpe_canonical": 1.0098581885287328,
          "test_ann_return": 0.1406703437212049,
          "test_max_dd": -0.07346374391202781,
          "test_turnover": 1.8666666666666667,
          "test_trades": 6
        },
        {
          "fold": 7,
          "test_start": "2021-08-19",
          "test_end": "2022-08-05",
          "test_sessions": 243,
          "test_sharpe": 0.017618105237637394,
          "test_sharpe_canonical": 0.21738930856341535,
          "test_ann_return": 0.02313986450586314,
          "test_max_dd": -0.1370626268829641,
          "test_turnover": 2.2814814814814817,
          "test_trades": 7
        },
        {
          "fold": 8,
          "test_start": "2022-08-08",
          "test_end": "2023-07-25",
          "test_sessions": 242,
          "test_sharpe": 0.2112621846322155,
          "test_sharpe_canonical": 0.4111415457332088,
          "test_ann_return": 0.05141687073840395,
          "test_max_dd": -0.13210086230908868,
          "test_turnover": 2.2909090909090915,
          "test_trades": 8
        },
        {
          "fold": 9,
          "test_start": "2023-07-26",
          "test_end": "2024-07-11",
          "test_sessions": 242,
          "test_sharpe": 1.034872385698726,
          "test_sharpe_canonical": 1.1991940799521588,
          "test_ann_return": 0.13238460672547014,
          "test_max_dd": -0.09640008083550766,
          "test_turnover": 2.9157024793388433,
          "test_trades": 10
        },
        {
          "fold": 10,
          "test_start": "2024-07-12",
          "test_end": "2025-06-30",
          "test_sessions": 242,
          "test_sharpe": 0.47952706967978465,
          "test_sharpe_canonical": 0.6523534078015951,
          "test_ann_return": 0.1028224567448166,
          "test_max_dd": -0.1579714897978245,
          "test_turnover": 3.1239669421487606,
          "test_trades": 10
        },
        {
          "fold": 11,
          "test_start": "2025-07-01",
          "test_end": "2026-06-17",
          "test_sessions": 243,
          "test_sharpe": 1.5870895011043684,
          "test_sharpe_canonical": 1.6369375953316205,
          "test_ann_return": 0.22428628423380848,
          "test_max_dd": -0.07743137513579657,
          "test_turnover": 2.696296296296296,
          "test_trades": 9
        }
      ]
    },
    "common_inception_window": {
      "wf": {
        "n_folds": 11,
        "mean_test_sharpe": 0.601899977260042,
        "std_test_sharpe": 0.6053984483184842,
        "median_test_sharpe": 0.5110655618517029,
        "min_test_sharpe": -0.129822701336185,
        "max_test_sharpe": 1.5870895011043684,
        "pct_positive_sharpe": 0.8181818181818182,
        "mean_test_ann_return": 0.09885794698295404,
        "mean_test_max_dd": -0.1307564488508914,
        "mean_test_trades": 7.909090909090909,
        "total_test_trades": 87,
        "mean_test_sharpe_canonical": 0.7729298597496885,
        "folds": [
          {
            "fold": 1,
            "test_start": "2015-11-03",
            "test_end": "2016-10-19",
            "test_sessions": 243,
            "test_sharpe": -0.129822701336185,
            "test_sharpe_canonical": 0.10086541879979755,
            "test_ann_return": 0.005012005137578601,
            "test_max_dd": -0.11745861248135336,
            "test_turnover": 1.4518518518518517,
            "test_trades": 6
          },
          {
            "fold": 2,
            "test_start": "2016-10-20",
            "test_end": "2017-10-06",
            "test_sessions": 243,
            "test_sharpe": 1.5339533404250725,
            "test_sharpe_canonical": 1.6957655725589382,
            "test_ann_return": 0.14813808561634256,
            "test_max_dd": -0.0319299042970872,
            "test_turnover": 2.903703703703704,
            "test_trades": 7
          },
          {
            "fold": 3,
            "test_start": "2017-10-09",
            "test_end": "2018-09-25",
            "test_sessions": 243,
            "test_sharpe": 0.631133614003499,
            "test_sharpe_canonical": 0.811105102410711,
            "test_ann_return": 0.1032664421134073,
            "test_max_dd": -0.10072116792804509,
            "test_turnover": 1.6592592592592594,
            "test_trades": 7
          },
          {
            "fold": 4,
            "test_start": "2018-09-26",
            "test_end": "2019-09-12",
            "test_sessions": 242,
            "test_sharpe": -0.11738315853351025,
            "test_sharpe_canonical": 0.08962718770103004,
            "test_ann_return": 0.0020624379978750884,
            "test_max_dd": -0.21977920561691933,
            "test_turnover": 2.4991735537190083,
            "test_trades": 9
          },
          {
            "fold": 5,
            "test_start": "2019-09-13",
            "test_end": "2020-08-31",
            "test_sessions": 244,
            "test_sharpe": 0.5110655618517029,
            "test_sharpe_canonical": 0.6779910498653653,
            "test_ann_return": 0.15423801927772374,
            "test_max_dd": -0.2940018681631914,
            "test_turnover": 2.478688524590164,
            "test_trades": 8
          },
          {
            "fold": 6,
            "test_start": "2020-09-01",
            "test_end": "2021-08-18",
            "test_sessions": 243,
            "test_sharpe": 0.8615838470971496,
            "test_sharpe_canonical": 1.0098581885287328,
            "test_ann_return": 0.1406703437212049,
            "test_max_dd": -0.07346374391202781,
            "test_turnover": 1.8666666666666667,
            "test_trades": 6
          },
          {
            "fold": 7,
            "test_start": "2021-08-19",
            "test_end": "2022-08-05",
            "test_sessions": 243,
            "test_sharpe": 0.017618105237637394,
            "test_sharpe_canonical": 0.21738930856341535,
            "test_ann_return": 0.02313986450586314,
            "test_max_dd": -0.1370626268829641,
            "test_turnover": 2.2814814814814817,
            "test_trades": 7
          },
          {
            "fold": 8,
            "test_start": "2022-08-08",
            "test_end": "2023-07-25",
            "test_sessions": 242,
            "test_sharpe": 0.2112621846322155,
            "test_sharpe_canonical": 0.4111415457332088,
            "test_ann_return": 0.05141687073840395,
            "test_max_dd": -0.13210086230908868,
            "test_turnover": 2.2909090909090915,
            "test_trades": 8
          },
          {
            "fold": 9,
            "test_start": "2023-07-26",
            "test_end": "2024-07-11",
            "test_sessions": 242,
            "test_sharpe": 1.034872385698726,
            "test_sharpe_canonical": 1.1991940799521588,
            "test_ann_return": 0.13238460672547014,
            "test_max_dd": -0.09640008083550766,
            "test_turnover": 2.9157024793388433,
            "test_trades": 10
          },
          {
            "fold": 10,
            "test_start": "2024-07-12",
            "test_end": "2025-06-30",
            "test_sessions": 242,
            "test_sharpe": 0.47952706967978465,
            "test_sharpe_canonical": 0.6523534078015951,
            "test_ann_return": 0.1028224567448166,
            "test_max_dd": -0.1579714897978245,
            "test_turnover": 3.1239669421487606,
            "test_trades": 10
          },
          {
            "fold": 11,
            "test_start": "2025-07-01",
            "test_end": "2026-06-17",
            "test_sessions": 243,
            "test_sharpe": 1.5870895011043684,
            "test_sharpe_canonical": 1.6369375953316205,
            "test_ann_return": 0.22428628423380848,
            "test_max_dd": -0.07743137513579657,
            "test_turnover": 2.696296296296296,
            "test_trades": 9
          }
        ]
      },
      "gates": [
        {
          "gate": "wf_mean_oos_sharpe",
          "threshold": ">= 0.9",
          "observed": 0.601899977260042,
          "status": "FAIL"
        },
        {
          "gate": "positive_fold_rate",
          "threshold": ">= 0.5",
          "observed": 0.8181818181818182,
          "status": "PASS"
        },
        {
          "gate": "pooled_oos_trades",
          "threshold": ">> 100",
          "observed": 87,
          "status": "FAIL"
        },
        {
          "gate": "plateau",
          "threshold": ">= 0.667 (>= 2 of 3 lookbacks)",
          "observed": null,
          "status": "NOT EVALUATED",
          "reason": "the 27-configuration robustness grid is out of scope for this cycle (it is a re-optimisation, not a measurement); the plateau gate is reported as NOT EVALUATED, as the published record already does"
        }
      ],
      "decision": {
        "label": "Rejected/Failed",
        "detail": "falsified (gate 1 or gate 2 fails)"
      },
      "folds": 11,
      "independence": {
        "mean_consecutive_overlap_days": 0.0,
        "max_disjoint_test_windows": 11
      },
      "rows": [
        {
          "fold": 1,
          "test_start": "2015-11-03",
          "test_end": "2016-10-19",
          "test_sessions": 243,
          "test_sharpe": -0.129822701336185,
          "test_sharpe_canonical": 0.10086541879979755,
          "test_ann_return": 0.005012005137578601,
          "test_max_dd": -0.11745861248135336,
          "test_turnover": 1.4518518518518517,
          "test_trades": 6
        },
        {
          "fold": 2,
          "test_start": "2016-10-20",
          "test_end": "2017-10-06",
          "test_sessions": 243,
          "test_sharpe": 1.5339533404250725,
          "test_sharpe_canonical": 1.6957655725589382,
          "test_ann_return": 0.14813808561634256,
          "test_max_dd": -0.0319299042970872,
          "test_turnover": 2.903703703703704,
          "test_trades": 7
        },
        {
          "fold": 3,
          "test_start": "2017-10-09",
          "test_end": "2018-09-25",
          "test_sessions": 243,
          "test_sharpe": 0.631133614003499,
          "test_sharpe_canonical": 0.811105102410711,
          "test_ann_return": 0.1032664421134073,
          "test_max_dd": -0.10072116792804509,
          "test_turnover": 1.6592592592592594,
          "test_trades": 7
        },
        {
          "fold": 4,
          "test_start": "2018-09-26",
          "test_end": "2019-09-12",
          "test_sessions": 242,
          "test_sharpe": -0.11738315853351025,
          "test_sharpe_canonical": 0.08962718770103004,
          "test_ann_return": 0.0020624379978750884,
          "test_max_dd": -0.21977920561691933,
          "test_turnover": 2.4991735537190083,
          "test_trades": 9
        },
        {
          "fold": 5,
          "test_start": "2019-09-13",
          "test_end": "2020-08-31",
          "test_sessions": 244,
          "test_sharpe": 0.5110655618517029,
          "test_sharpe_canonical": 0.6779910498653653,
          "test_ann_return": 0.15423801927772374,
          "test_max_dd": -0.2940018681631914,
          "test_turnover": 2.478688524590164,
          "test_trades": 8
        },
        {
          "fold": 6,
          "test_start": "2020-09-01",
          "test_end": "2021-08-18",
          "test_sessions": 243,
          "test_sharpe": 0.8615838470971496,
          "test_sharpe_canonical": 1.0098581885287328,
          "test_ann_return": 0.1406703437212049,
          "test_max_dd": -0.07346374391202781,
          "test_turnover": 1.8666666666666667,
          "test_trades": 6
        },
        {
          "fold": 7,
          "test_start": "2021-08-19",
          "test_end": "2022-08-05",
          "test_sessions": 243,
          "test_sharpe": 0.017618105237637394,
          "test_sharpe_canonical": 0.21738930856341535,
          "test_ann_return": 0.02313986450586314,
          "test_max_dd": -0.1370626268829641,
          "test_turnover": 2.2814814814814817,
          "test_trades": 7
        },
        {
          "fold": 8,
          "test_start": "2022-08-08",
          "test_end": "2023-07-25",
          "test_sessions": 242,
          "test_sharpe": 0.2112621846322155,
          "test_sharpe_canonical": 0.4111415457332088,
          "test_ann_return": 0.05141687073840395,
          "test_max_dd": -0.13210086230908868,
          "test_turnover": 2.2909090909090915,
          "test_trades": 8
        },
        {
          "fold": 9,
          "test_start": "2023-07-26",
          "test_end": "2024-07-11",
          "test_sessions": 242,
          "test_sharpe": 1.034872385698726,
          "test_sharpe_canonical": 1.1991940799521588,
          "test_ann_return": 0.13238460672547014,
          "test_max_dd": -0.09640008083550766,
          "test_turnover": 2.9157024793388433,
          "test_trades": 10
        },
        {
          "fold": 10,
          "test_start": "2024-07-12",
          "test_end": "2025-06-30",
          "test_sessions": 242,
          "test_sharpe": 0.47952706967978465,
          "test_sharpe_canonical": 0.6523534078015951,
          "test_ann_return": 0.1028224567448166,
          "test_max_dd": -0.1579714897978245,
          "test_turnover": 3.1239669421487606,
          "test_trades": 10
        },
        {
          "fold": 11,
          "test_start": "2025-07-01",
          "test_end": "2026-06-17",
          "test_sessions": 243,
          "test_sharpe": 1.5870895011043684,
          "test_sharpe_canonical": 1.6369375953316205,
          "test_ann_return": 0.22428628423380848,
          "test_max_dd": -0.07743137513579657,
          "test_turnover": 2.696296296296296,
          "test_trades": 9
        }
      ]
    }
  },
  "design_b_embargo_literal": {
    "union_sample": {
      "wf": {
        "n_folds": 3,
        "mean_test_sharpe": 0.9133458303583644,
        "std_test_sharpe": 0.6341506812781212,
        "median_test_sharpe": 1.1121582256222222,
        "min_test_sharpe": 0.20360995936736387,
        "max_test_sharpe": 1.4242693060855072,
        "pct_positive_sharpe": 1.0,
        "mean_test_ann_return": 0.15860128716486468,
        "mean_test_max_dd": -0.12042409708130104,
        "mean_test_trades": 8.666666666666666,
        "total_test_trades": 26,
        "mean_test_sharpe_canonical": 1.0381820475009262,
        "folds": [
          {
            "fold": 1,
            "test_start": "2002-09-30",
            "test_end": "2003-09-16",
            "test_sessions": 243,
            "test_sharpe": 1.1121582256222222,
            "test_sharpe_canonical": 1.1847608618398233,
            "test_ann_return": 0.24338207942578305,
            "test_max_dd": -0.14265741312216396,
            "test_turnover": 3.814814814814815,
            "test_trades": 10
          },
          {
            "fold": 2,
            "test_start": "2013-07-12",
            "test_end": "2014-06-30",
            "test_sessions": 244,
            "test_sharpe": 1.4242693060855072,
            "test_sharpe_canonical": 1.5325537716325721,
            "test_ann_return": 0.1779845162279008,
            "test_max_dd": -0.060643388323915026,
            "test_turnover": 1.4459016393442623,
            "test_trades": 6
          },
          {
            "fold": 3,
            "test_start": "2024-04-25",
            "test_end": "2025-04-11",
            "test_sessions": 242,
            "test_sharpe": 0.20360995936736387,
            "test_sharpe_canonical": 0.39723150903038346,
            "test_ann_return": 0.05443726584091024,
            "test_max_dd": -0.15797148979782416,
            "test_turnover": 3.332231404958678,
            "test_trades": 10
          }
        ]
      },
      "gates": [
        {
          "gate": "wf_mean_oos_sharpe",
          "threshold": ">= 0.9",
          "observed": 0.9133458303583644,
          "status": "PASS"
        },
        {
          "gate": "positive_fold_rate",
          "threshold": ">= 0.5",
          "observed": 1.0,
          "status": "PASS"
        },
        {
          "gate": "pooled_oos_trades",
          "threshold": ">> 100",
          "observed": 26,
          "status": "FAIL"
        },
        {
          "gate": "plateau",
          "threshold": ">= 0.667 (>= 2 of 3 lookbacks)",
          "observed": null,
          "status": "NOT EVALUATED",
          "reason": "the 27-configuration robustness grid is out of scope for this cycle (it is a re-optimisation, not a measurement); the plateau gate is reported as NOT EVALUATED, as the published record already does"
        }
      ],
      "decision": {
        "label": "Inconclusive",
        "detail": "some gates fail"
      },
      "folds": 3,
      "independence": {
        "mean_consecutive_overlap_days": 0.0,
        "max_disjoint_test_windows": 3
      },
      "rows": [
        {
          "fold": 1,
          "test_start": "2002-09-30",
          "test_end": "2003-09-16",
          "test_sessions": 243,
          "test_sharpe": 1.1121582256222222,
          "test_sharpe_canonical": 1.1847608618398233,
          "test_ann_return": 0.24338207942578305,
          "test_max_dd": -0.14265741312216396,
          "test_turnover": 3.814814814814815,
          "test_trades": 10
        },
        {
          "fold": 2,
          "test_start": "2013-07-12",
          "test_end": "2014-06-30",
          "test_sessions": 244,
          "test_sharpe": 1.4242693060855072,
          "test_sharpe_canonical": 1.5325537716325721,
          "test_ann_return": 0.1779845162279008,
          "test_max_dd": -0.060643388323915026,
          "test_turnover": 1.4459016393442623,
          "test_trades": 6
        },
        {
          "fold": 3,
          "test_start": "2024-04-25",
          "test_end": "2025-04-11",
          "test_sessions": 242,
          "test_sharpe": 0.20360995936736387,
          "test_sharpe_canonical": 0.39723150903038346,
          "test_ann_return": 0.05443726584091024,
          "test_max_dd": -0.15797148979782416,
          "test_turnover": 3.332231404958678,
          "test_trades": 10
        }
      ]
    },
    "common_inception_slice": {
      "wf": {
        "n_folds": 1,
        "mean_test_sharpe": -0.129822701336185,
        "std_test_sharpe": NaN,
        "median_test_sharpe": -0.129822701336185,
        "min_test_sharpe": -0.129822701336185,
        "max_test_sharpe": -0.129822701336185,
        "pct_positive_sharpe": 0.0,
        "mean_test_ann_return": 0.005012005137578601,
        "mean_test_max_dd": -0.11745861248135336,
        "mean_test_trades": 6.0,
        "total_test_trades": 6,
        "mean_test_sharpe_canonical": 0.10086541879979755,
        "folds": [
          {
            "fold": 1,
            "test_start": "2015-11-03",
            "test_end": "2016-10-19",
            "test_sessions": 243,
            "test_sharpe": -0.129822701336185,
            "test_sharpe_canonical": 0.10086541879979755,
            "test_ann_return": 0.005012005137578601,
            "test_max_dd": -0.11745861248135336,
            "test_turnover": 1.4518518518518517,
            "test_trades": 6
          }
        ]
      },
      "gates": [
        {
          "gate": "wf_mean_oos_sharpe",
          "threshold": ">= 0.9",
          "observed": -0.129822701336185,
          "status": "FAIL"
        },
        {
          "gate": "positive_fold_rate",
          "threshold": ">= 0.5",
          "observed": 0.0,
          "status": "FAIL"
        },
        {
          "gate": "pooled_oos_trades",
          "threshold": ">> 100",
          "observed": 6,
          "status": "FAIL"
        },
        {
          "gate": "plateau",
          "threshold": ">= 0.667 (>= 2 of 3 lookbacks)",
          "observed": null,
          "status": "NOT EVALUATED",
          "reason": "the 27-configuration robustness grid is out of scope for this cycle (it is a re-optimisation, not a measurement); the plateau gate is reported as NOT EVALUATED, as the published record already does"
        }
      ],
      "decision": {
        "label": "Rejected/Failed",
        "detail": "falsified (gate 1 or gate 2 fails)"
      },
      "folds": 1,
      "independence": {
        "mean_consecutive_overlap_days": 0.0,
        "max_disjoint_test_windows": 1
      },
      "rows": [
        {
          "fold": 1,
          "test_start": "2015-11-03",
          "test_end": "2016-10-19",
          "test_sessions": 243,
          "test_sharpe": -0.129822701336185,
          "test_sharpe_canonical": 0.10086541879979755,
          "test_ann_return": 0.005012005137578601,
          "test_max_dd": -0.11745861248135336,
          "test_turnover": 1.4518518518518517,
          "test_trades": 6
        }
      ]
    },
    "common_inception_window": {
      "wf": {
        "n_folds": 1,
        "mean_test_sharpe": -0.129822701336185,
        "std_test_sharpe": NaN,
        "median_test_sharpe": -0.129822701336185,
        "min_test_sharpe": -0.129822701336185,
        "max_test_sharpe": -0.129822701336185,
        "pct_positive_sharpe": 0.0,
        "mean_test_ann_return": 0.005012005137578601,
        "mean_test_max_dd": -0.11745861248135336,
        "mean_test_trades": 6.0,
        "total_test_trades": 6,
        "mean_test_sharpe_canonical": 0.10086541879979755,
        "folds": [
          {
            "fold": 1,
            "test_start": "2015-11-03",
            "test_end": "2016-10-19",
            "test_sessions": 243,
            "test_sharpe": -0.129822701336185,
            "test_sharpe_canonical": 0.10086541879979755,
            "test_ann_return": 0.005012005137578601,
            "test_max_dd": -0.11745861248135336,
            "test_turnover": 1.4518518518518517,
            "test_trades": 6
          }
        ]
      },
      "gates": [
        {
          "gate": "wf_mean_oos_sharpe",
          "threshold": ">= 0.9",
          "observed": -0.129822701336185,
          "status": "FAIL"
        },
        {
          "gate": "positive_fold_rate",
          "threshold": ">= 0.5",
          "observed": 0.0,
          "status": "FAIL"
        },
        {
          "gate": "pooled_oos_trades",
          "threshold": ">> 100",
          "observed": 6,
          "status": "FAIL"
        },
        {
          "gate": "plateau",
          "threshold": ">= 0.667 (>= 2 of 3 lookbacks)",
          "observed": null,
          "status": "NOT EVALUATED",
          "reason": "the 27-configuration robustness grid is out of scope for this cycle (it is a re-optimisation, not a measurement); the plateau gate is reported as NOT EVALUATED, as the published record already does"
        }
      ],
      "decision": {
        "label": "Rejected/Failed",
        "detail": "falsified (gate 1 or gate 2 fails)"
      },
      "folds": 1,
      "independence": {
        "mean_consecutive_overlap_days": 0.0,
        "max_disjoint_test_windows": 1
      },
      "rows": [
        {
          "fold": 1,
          "test_start": "2015-11-03",
          "test_end": "2016-10-19",
          "test_sessions": 243,
          "test_sharpe": -0.129822701336185,
          "test_sharpe_canonical": 0.10086541879979755,
          "test_ann_return": 0.005012005137578601,
          "test_max_dd": -0.11745861248135336,
          "test_turnover": 1.4518518518518517,
          "test_trades": 6
        }
      ]
    }
  },
  "delta_published_vs_design_a_union": {
    "fold_count_delta": -24,
    "mean_sharpe_published": 0.6975243375140185,
    "mean_sharpe_design_a": 0.6982984362427751,
    "gate1_margin_published": 0.20247566248598148,
    "gate1_margin_design_a": 0.20170156375722492,
    "verdict_survives": true
  }
}
```

