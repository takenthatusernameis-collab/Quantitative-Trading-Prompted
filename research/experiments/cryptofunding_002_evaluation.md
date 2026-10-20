# Experiment: cryptofunding_002_evaluation — Net-of-cost evaluation (Cycle 890)

## Pre-registered evaluation (see hypothesis)

Trial count: 4 (2 rules × 2 symbols). Cost model: 3 bp per unit of weight change (repository flat model). Block bootstrap: 126-day blocks, 2000 draws, seed 20261019.

## Results (net of costs)

{
  "BTC_always_on": {
    "n_full": 2464,
    "ann_net_return_full": 0.07982111915517964,
    "sharpe_full": 6.867815988821421,
    "sortino_full": 8.837990226643292,
    "max_dd_full": -0.024283209961711516,
    "ann_turnover": 10.608759855503205,
    "rebalances_full": 2464,
    "block_bootstrap_ci_ann_net_95_full": [
      0.04581226855254312,
      0.12502816374575687
    ],
    "train": {
      "ann_net": 0.1204693328719626,
      "sharpe": 7.2928702704241815,
      "n": 1095
    },
    "val": {
      "ann_net": 0.06749518226935614,
      "sharpe": 11.448473298570391,
      "n": 731
    },
    "test_oos": {
      "ann_net": 0.026883148595841178,
      "sharpe": 9.290907318461606,
      "n": 638
    },
    "post2022": {
      "ann_net": 0.04837253729338764,
      "sharpe": 9.925241791355974,
      "n": 1369,
      "block_bootstrap_ci_ann_net_95": [
        0.02854866399029652,
        0.07287172598624393
      ]
    },
    "oos_trades_approx": 638
  },
  "BTC_funding_positive": {
    "n_full": 2464,
    "ann_net_return_full": 0.0881357320638505,
    "sharpe_full": 8.335974171311666,
    "sortino_full": 18.62546991044524,
    "max_dd_full": -0.003535706234704006,
    "ann_turnover": 9.088874127541212,
    "rebalances_full": 2165,
    "block_bootstrap_ci_ann_net_95_full": [
      0.05321180565190858,
      0.13279029649802518
    ],
    "train": {
      "ann_net": 0.13600854717425026,
      "sharpe": 9.208790721164231,
      "n": 1095
    },
    "val": {
      "ann_net": 0.06937693166336412,
      "sharpe": 12.028655497343415,
      "n": 731
    },
    "test_oos": {
      "ann_net": 0.030964973791552497,
      "sharpe": 12.174246206582533,
      "n": 638
    },
    "post2022": {
      "ann_net": 0.051300768427459786,
      "sharpe": 10.959075886748561,
      "n": 1369,
      "block_bootstrap_ci_ann_net_95": [
        0.03323360704406581,
        0.07470600846059162
      ]
    },
    "oos_trades_approx": 2165
  },
  "ETH_always_on": {
    "n_full": 2464,
    "ann_net_return_full": 0.09334799790919646,
    "sharpe_full": 5.994283795069187,
    "sortino_full": 7.011732386190083,
    "max_dd_full": -0.019107832580336548,
    "ann_turnover": 14.48215064926316,
    "rebalances_full": 2464,
    "block_bootstrap_ci_ann_net_95_full": [
      0.04458618451789868,
      0.15581534145625237
    ],
    "train": {
      "ann_net": 0.15252864030236601,
      "sharpe": 6.726372064563462,
      "n": 1095
    },
    "val": {
      "ann_net": 0.07221552572817358,
      "sharpe": 11.802282310411492,
      "n": 731
    },
    "test_oos": {
      "ann_net": 0.021359187140782776,
      "sharpe": 6.012020745808605,
      "n": 638
    },
    "post2022": {
      "ann_net": 0.04820712798767435,
      "sharpe": 9.109286360543836,
      "n": 1369,
      "block_bootstrap_ci_ann_net_95": [
        0.02618006915160075,
        0.07502873306356504
      ]
    },
    "oos_trades_approx": 638
  },
  "ETH_funding_positive": {
    "n_full": 2464,
    "ann_net_return_full": 0.10309672837924744,
    "sharpe_full": 7.43092584277679,
    "sortino_full": 21.840232520700805,
    "max_dd_full": -0.002730194092474547,
    "ann_turnover": 12.466503187038441,
    "rebalances_full": 2170,
    "block_bootstrap_ci_ann_net_95_full": [
      0.056260256167134655,
      0.16441531517084942
    ],
    "train": {
      "ann_net": 0.17019976801900594,
      "sharpe": 8.532924400577059,
      "n": 1095
    },
    "val": {
      "ann_net": 0.07371655076915729,
      "sharpe": 12.270489512660372,
      "n": 731
    },
    "test_oos": {
      "ann_net": 0.02808627850936185,
      "sharpe": 11.518257154028161,
      "n": 638
    },
    "post2022": {
      "ann_net": 0.05220464423510962,
      "sharpe": 10.730934786523367,
      "n": 1369,
      "block_bootstrap_ci_ann_net_95": [
        0.03307122419697002,
        0.07690205419412727
      ]
    },
    "oos_trades_approx": 2170
  },
  "_meta": {
    "trial_count": 4,
    "cost_model_bps_per_unit": 3.0,
    "pooled_oos_trades": 2335,
    "pooled_oos_sharpe_mean": 9.748857856220226,
    "promotion_gate_pass": true,
    "splits": {
      "train": "2020-01-02 to 2022-12-31",
      "val": "2023-01-01 to 2024-12-31",
      "test_oos": "2025-01-01 to 2026-09-30",
      "post2022": "2023-01-01 to 2026-09-30"
    }
  }
}
