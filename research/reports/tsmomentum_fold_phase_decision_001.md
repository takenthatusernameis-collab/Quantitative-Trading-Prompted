# TSMomentum SPY-Trend Fold-Phase Decision Audit (tsmomentum_fold_phase_decision_001, Cycle 912)

## Summary

- Candidate: `tsmomentum_spytrend_001` (the incumbent)
- Published walk-forward record (resolved by content): `research/experiments/tsmomentum_regime_filter_wf_001.md`
- Original published verdict: **Credible Candidate** (WF mean OOS Sharpe 0.9473)
- Cycle 911 robustness audit consumed: **PASS**

## Decision

- **Downgrade to Exploratory (not promotable as-is)**
- Published PASS is not phase-stable: phase B (even folds) fails gate-1 (mean 0.509580 < 0.9) while phase A passes; the 48-fold mean is an interleaving average. Thin-trade folds (12,13) dominate influence but excluding them still gives mean 1.468851 (PASS); the instability is primarily phase-based, not thin-trade-based. Evidence insufficient for promotion without phase-stable validation.

## Phase decomposition (from Cycle 911)

| Phase | Folds | WF mean OOS Sharpe | Median | Positive fold rate | Pooled OOS trades | Gate 1 (>= 0.9) | Decision |
|---|---|---|---|---|---|---|---|
| Phase A (odd folds) | 24 | 1.385035 | 1.420426 | 0.9167 | 2952 | PASS | Passes preliminary gates |
| Phase B (even folds) | 24 | 0.509580 | 1.248322 | 0.9167 | 3061 | FAIL | Rejected/Failed |
| Published (all 48) | 48 | 0.947307 | 1.404936 | 0.9167 | 6013 | PASS | Credible Candidate (published) |

- Phase means average to published mean: **YES** (interleaving of two disjoint 24-fold designs).
- Gate-1 outcome changes between phases: **YES** (PASS vs FAIL).

## Fold influence (from Cycle 911)

- Published mean: 0.947307, median: 1.293299, trimmed mean (min/max removed): 1.378012.
- Most influential fold: fold 12 (test Sharpe -21.8299, leave-one-out mean 1.431928, shift +0.484621).
- Thin-trade folds (<=10 trades): [12, 13]; excluding both gives mean 1.468851, gate-1 PASS.

## Stability assessment

- Gate-1 changes between phases: **YES**
- Gate-1 changes excluding thin-trade folds: **NO**
- Published PASS stable: **NOT STABLE**

## Read-only guarantees

- `data/` and `config/` byte-identical before and after the run (**yes**); no committed artifact modified (**yes**).

## Checks

- [published_record_resolved_by_content]: PASS (observed: research/experiments/tsmomentum_regime_filter_wf_001.md, expected: exactly one published walk-forward record carrying the published anchor)
- [consumed_cycle911_robustness_audit]: PASS (observed: overall=PASS, expected: Cycle 911 audit passes)
- [phase_b_fails_gate1]: PASS (observed: 0.5095802555150982, expected: < 0.9)
- [phase_a_passes_gate1]: PASS (observed: 1.3850346885341203, expected: >= 0.9)
- [gate1_changes_between_phases]: PASS (observed: True, expected: True)
- [published_pass_not_stable]: PASS (observed: False, expected: False)
- [thin_trade_folds_identified]: PASS (observed: [12, 13], expected: [12, 13])
- [data_unchanged]: PASS
- [config_unchanged]: PASS
- [committed_artifacts_unchanged]: PASS

## Reproduction commands

```bash
python research/tsmomentum_fold_phase_decision_audit.py
python -m pytest -q tests/test_tsmomentum_fold_phase_decision_audit.py
python -m pytest -q
git status --porcelain data/
git diff --stat src/ config/ research/experiments/ research/reports/
```

## JSON payload

```json
{
  "candidate": "tsmomentum_spytrend_001",
  "checks": [
    {
      "expected": "exactly one published walk-forward record carrying the published anchor",
      "name": "published_record_resolved_by_content",
      "observed": "research/experiments/tsmomentum_regime_filter_wf_001.md",
      "pass": true
    },
    {
      "expected": "Cycle 911 audit passes",
      "name": "consumed_cycle911_robustness_audit",
      "observed": "overall=PASS",
      "pass": true
    },
    {
      "expected": "< 0.9",
      "name": "phase_b_fails_gate1",
      "observed": 0.5095802555150982,
      "pass": true
    },
    {
      "expected": ">= 0.9",
      "name": "phase_a_passes_gate1",
      "observed": 1.3850346885341203,
      "pass": true
    },
    {
      "expected": true,
      "name": "gate1_changes_between_phases",
      "observed": true,
      "pass": true
    },
    {
      "expected": false,
      "name": "published_pass_not_stable",
      "observed": false,
      "pass": true
    },
    {
      "expected": [
        12,
        13
      ],
      "name": "thin_trade_folds_identified",
      "observed": [
        12,
        13
      ],
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
  "cycle": "912",
  "cycle911_robustness": {
    "overall": "PASS",
    "published_mean_recomputed": 0.9473074720246092
  },
  "data_source": "committed parquet cache in data/raw/ (fetcher never called)",
  "decision": {
    "detail": "Published PASS is not phase-stable: phase B (even folds) fails gate-1 (mean 0.509580 < 0.9) while phase A passes; the 48-fold mean is an interleaving average. Thin-trade folds (12,13) dominate influence but excluding them still gives mean 1.468851 (PASS); the instability is primarily phase-based, not thin-trade-based. Evidence insufficient for promotion without phase-stable validation.",
    "label": "Downgrade to Exploratory (not promotable as-is)"
  },
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
  "point_in_time": "signals use only data available at formation (weights shifted one day), the SPY SMA is computed point-in-time, and the overlay/cost model are applied on the same continuously computed path for every fold and phase",
  "published_anchor_value": 0.9473,
  "published_record_path": "research/experiments/tsmomentum_regime_filter_wf_001.md",
  "published_verdict_original": "Credible Candidate",
  "read_only": {
    "committed_artifacts_unchanged": true,
    "config_unchanged": true,
    "data_unchanged": true
  },
  "stability": {
    "gate1_outcome_changes_between_phases": true,
    "gate1_outcome_changes_when_thin_trade_folds_excluded": false,
    "published_pass_stable": false
  }
}
```
