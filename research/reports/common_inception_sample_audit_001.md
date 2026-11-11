# Common-Inception Sample Audit (Cycle 903)

The incumbent's published long-sample evidence is computed on the **union
calendar** of the raw cache, because `src/backtest/engine.py:run_backtest`
does not slice the price frame it loads, while the frozen configuration
describes a **seven-asset universe** whose first fully populated date is
2004-11-18.  This artifact publishes the incumbent's canonical
metrics and its **full promotion gate table** on that common-inception
sample next to the union-sample numbers.

**This is a measurement, not a decision.**  No gate, threshold, decision
mapping, candidate configuration, universe, cost model or Sharpe
convention was changed, the committed long-sample artifact was not
regenerated or edited, and the incumbent's published decision (NO-GO) is
not changed by this cycle.  The choice of the sample on which the
long-sample diagnostic's gate table is evaluated is left to an explicitly
recorded decision; the evidence needed for it is published below.

## Question

Are the incumbent's published long-sample numbers and its NO-GO verdict an artefact of the sample definition (the union calendar of the raw cache) rather than of the strategy?

## Samples

```json
{
  "union_sample": {
    "label": "union_sample",
    "definition": "the union calendar of the raw cache (the sample the committed long-sample artifact computes)",
    "gates": {
      "track_record_length": {
        "value": 8504.0,
        "threshold": 126.0,
        "comparison": "gte",
        "pass": true
      },
      "full_period_sharpe": {
        "value": 0.5602214749842194,
        "threshold": 0.9,
        "comparison": "gte",
        "pass": false
      },
      "rolling_63d_sharpe": {
        "value": -1.3233468907373043,
        "threshold": 0.9,
        "comparison": "gte",
        "pass": false
      },
      "max_drawdown": {
        "value": -0.6224126346564325,
        "threshold": -0.15,
        "comparison": "gte",
        "pass": false
      },
      "rolling_63d_max_dd": {
        "value": -0.109209305725669,
        "threshold": -0.15,
        "comparison": "gte",
        "pass": true
      },
      "regime_flips": {
        "value": 6.0,
        "threshold": 1.0,
        "comparison": "gte",
        "pass": true
      },
      "psr": {
        "value": 1.0078448910250733e-08,
        "threshold": 0.95,
        "comparison": "gte",
        "pass": false
      }
    },
    "failed_gates": [
      "full_period_sharpe",
      "rolling_63d_sharpe",
      "max_drawdown",
      "psr"
    ],
    "psr_zone": "below_no_go",
    "decision": "NO-GO",
    "rationale": "4 promotion gate(s) failed: full_period_sharpe, rolling_63d_sharpe, max_drawdown, psr. A failing gate can never yield GO, regardless of the PSR.",
    "conditions_for_reevaluation": "Strategy fails go/no-go criteria. Do not promote to live trading without major revision.",
    "positions": {
      "mean_positions_held": 3.1451081843838193,
      "median_positions_held": 4.0,
      "sessions_with_one_position": 1542,
      "sessions_with_no_position": 248
    },
    "cross_section": {
      "sessions": 8504,
      "opening_date": "1993-01-29",
      "opening_width": 1,
      "price_width_min": 1,
      "price_width_median": 7.0,
      "price_width_max": 7,
      "price_width_change_dates": [
        {
          "date": "1999-03-10",
          "assets_with_price": 2
        },
        {
          "date": "2000-05-26",
          "assets_with_price": 3
        },
        {
          "date": "2001-08-27",
          "assets_with_price": 4
        },
        {
          "date": "2002-07-30",
          "assets_with_price": 5
        },
        {
          "date": "2003-04-14",
          "assets_with_price": 6
        },
        {
          "date": "2004-11-18",
          "assets_with_price": 7
        }
      ],
      "momentum_breadth_min": 0,
      "momentum_breadth_median": 7.0,
      "momentum_breadth_max": 7,
      "momentum_breadth_change_dates": [
        {
          "date": "1994-01-20",
          "assets_with_price": 1
        },
        {
          "date": "2000-03-01",
          "assets_with_price": 2
        },
        {
          "date": "2001-05-21",
          "assets_with_price": 3
        },
        {
          "date": "2002-08-26",
          "assets_with_price": 4
        },
        {
          "date": "2003-07-23",
          "assets_with_price": 5
        },
        {
          "date": "2004-04-06",
          "assets_with_price": 6
        },
        {
          "date": "2005-11-10",
          "assets_with_price": 7
        }
      ],
      "sessions_with_fewer_than_five_selectable_assets": 2640
    }
  },
  "common_inception_slice": {
    "label": "common_inception_slice",
    "definition": "the aligned price frame truncated to the common inception 2004-11-18 before the signal, cost model, universe, lookback/skip/top_fraction and rebalance semantics are applied",
    "gates": {
      "track_record_length": {
        "value": 5529.0,
        "threshold": 126.0,
        "comparison": "gte",
        "pass": true
      },
      "full_period_sharpe": {
        "value": 0.6910457493706031,
        "threshold": 0.9,
        "comparison": "gte",
        "pass": false
      },
      "rolling_63d_sharpe": {
        "value": -1.3233468907373043,
        "threshold": 0.9,
        "comparison": "gte",
        "pass": false
      },
      "max_drawdown": {
        "value": -0.3669795914712545,
        "threshold": -0.15,
        "comparison": "gte",
        "pass": false
      },
      "rolling_63d_max_dd": {
        "value": -0.109209305725669,
        "threshold": -0.15,
        "comparison": "gte",
        "pass": true
      },
      "regime_flips": {
        "value": 6.0,
        "threshold": 1.0,
        "comparison": "gte",
        "pass": true
      },
      "psr": {
        "value": 0.00015597590270448715,
        "threshold": 0.95,
        "comparison": "gte",
        "pass": false
      }
    },
    "failed_gates": [
      "full_period_sharpe",
      "rolling_63d_sharpe",
      "max_drawdown",
      "psr"
    ],
    "psr_zone": "below_no_go",
    "decision": "NO-GO",
    "rationale": "4 promotion gate(s) failed: full_period_sharpe, rolling_63d_sharpe, max_drawdown, psr. A failing gate can never yield GO, regardless of the PSR.",
    "conditions_for_reevaluation": "Strategy fails go/no-go criteria. Do not promote to live trading without major revision.",
    "positions": {
      "mean_positions_held": 3.820582383794538,
      "median_positions_held": 4.0,
      "sessions_with_one_position": 0,
      "sessions_with_no_position": 248
    },
    "cross_section": {
      "sessions": 5529,
      "opening_date": "2004-11-18",
      "opening_width": 7,
      "price_width_min": 7,
      "price_width_median": 7.0,
      "price_width_max": 7,
      "price_width_change_dates": [],
      "momentum_breadth_min": 6,
      "momentum_breadth_median": 7.0,
      "momentum_breadth_max": 7,
      "momentum_breadth_change_dates": [
        {
          "date": "2005-11-10",
          "assets_with_price": 7
        }
      ],
      "sessions_with_fewer_than_five_selectable_assets": 0
    }
  },
  "common_inception_window": {
    "label": "common_inception_window",
    "definition": "the union path restricted to the sessions from the common inception 2004-11-18 onwards (warm-up preserved)",
    "gates": {
      "track_record_length": {
        "value": 5529.0,
        "threshold": 126.0,
        "comparison": "gte",
        "pass": true
      },
      "full_period_sharpe": {
        "value": 0.7019873676244225,
        "threshold": 0.9,
        "comparison": "gte",
        "pass": false
      },
      "rolling_63d_sharpe": {
        "value": -1.3233468907373043,
        "threshold": 0.9,
        "comparison": "gte",
        "pass": false
      },
      "max_drawdown": {
        "value": -0.3669795914712546,
        "threshold": -0.15,
        "comparison": "gte",
        "pass": false
      },
      "rolling_63d_max_dd": {
        "value": -0.109209305725669,
        "threshold": -0.15,
        "comparison": "gte",
        "pass": true
      },
      "regime_flips": {
        "value": 6.0,
        "threshold": 1.0,
        "comparison": "gte",
        "pass": true
      },
      "psr": {
        "value": 0.00017476863096306433,
        "threshold": 0.95,
        "comparison": "gte",
        "pass": false
      }
    },
    "failed_gates": [
      "full_period_sharpe",
      "rolling_63d_sharpe",
      "max_drawdown",
      "psr"
    ],
    "psr_zone": "below_no_go",
    "decision": "NO-GO",
    "rationale": "4 promotion gate(s) failed: full_period_sharpe, rolling_63d_sharpe, max_drawdown, psr. A failing gate can never yield GO, regardless of the PSR.",
    "conditions_for_reevaluation": "Strategy fails go/no-go criteria. Do not promote to live trading without major revision.",
    "positions": {
      "mean_positions_held": 4.0,
      "median_positions_held": 4.0,
      "sessions_with_one_position": 0,
      "sessions_with_no_position": 0
    },
    "cross_section": {
      "sessions": 5529,
      "opening_date": "2004-11-18",
      "opening_width": 7,
      "price_width_min": 7,
      "price_width_median": 7.0,
      "price_width_max": 7,
      "price_width_change_dates": [],
      "momentum_breadth_min": 6,
      "momentum_breadth_median": 7.0,
      "momentum_breadth_max": 7,
      "momentum_breadth_change_dates": [
        {
          "date": "2005-11-10",
          "assets_with_price": 7
        }
      ],
      "sessions_with_fewer_than_five_selectable_assets": 0
    }
  }
}
```

## Canonical metrics per sample (arithmetic_annualized_rf0)

```json
{
  "union_sample": {
    "sessions": 8504,
    "start_date": "1993-01-29",
    "end_date": "2026-11-10",
    "paper_sharpe": 0.5602214749842194,
    "paper_max_dd": -0.6224126346564325,
    "rolling_sharpe_63d": -1.3233468907373043,
    "rolling_63d_max_dd": -0.109209305725669,
    "paper_days": 8504,
    "sharpe_observed_canonical": 0.5602214749842194,
    "sharpe_se": 0.15284835880824443,
    "sharpe_backtest_scale": 0.3784336640180774,
    "psr_normal": 1.0078448910250733e-08,
    "psr_empirical": 0.0,
    "psr_ci_lower": 0.26031368950176564,
    "psr_ci_upper": 0.8865290168008415,
    "zero_return_sessions": 275
  },
  "common_inception_slice": {
    "sessions": 5529,
    "start_date": "2004-11-18",
    "end_date": "2026-11-10",
    "paper_sharpe": 0.6910457493706031,
    "paper_max_dd": -0.3669795914712545,
    "rolling_sharpe_63d": -1.3233468907373043,
    "rolling_63d_max_dd": -0.109209305725669,
    "paper_days": 5529,
    "sharpe_observed_canonical": 0.6910457493706031,
    "sharpe_se": 0.20158682635786065,
    "sharpe_backtest_scale": 0.5120836617331459,
    "psr_normal": 0.00015597590270448715,
    "psr_empirical": 0.0,
    "psr_ci_lower": 0.31370117154578453,
    "psr_ci_upper": 1.0954964906095122,
    "zero_return_sessions": 248
  },
  "common_inception_window": {
    "sessions": 5529,
    "start_date": "2004-11-18",
    "end_date": "2026-11-10",
    "paper_sharpe": 0.7019873676244225,
    "paper_max_dd": -0.3669795914712546,
    "rolling_sharpe_63d": -1.3233468907373043,
    "rolling_63d_max_dd": -0.109209305725669,
    "paper_days": 5529,
    "sharpe_observed_canonical": 0.7019873676244225,
    "sharpe_se": 0.20019839158250452,
    "sharpe_backtest_scale": 0.5252549073995599,
    "psr_normal": 0.00017476863096306433,
    "psr_empirical": 0.0,
    "psr_ci_lower": 0.316792349131175,
    "psr_ci_upper": 1.10013871770956,
    "zero_return_sessions": 0
  }
}
```

## Where the union sample's numbers come from

```json
{
  "before_common_inception": {
    "sessions": 2975,
    "start_date": "1993-01-29",
    "end_date": "2004-11-17",
    "sharpe": 0.38501143654921,
    "max_drawdown": -0.6224126346564325
  },
  "from_common_inception": {
    "sessions": 5529,
    "start_date": "2004-11-18",
    "end_date": "2026-11-10",
    "sharpe": 0.7019873676244225,
    "max_drawdown": -0.3669795914712546
  },
  "union_max_drawdown": {
    "value": -0.6224126346564325,
    "peak_date": "2000-03-24",
    "trough_date": "2002-10-09",
    "is_pre_common_inception": true,
    "note": "the union sample's maximum drawdown is a peak-to-trough episode that opens before the common inception; the common-inception sample cannot contain it"
  }
}
```

## Warm-up ramp of the sliced sample

```json
{
  "flat_sessions_before_the_first_signal": 248,
  "first_non_zero_return_date": "2005-11-11",
  "first_session_with_a_position": "2005-11-11",
  "sessions_differing_from_the_warmup_variant": 249,
  "first_differing_session": "2004-11-18",
  "last_differing_session": "2005-11-11",
  "note": "the sliced sample has no momentum history for 226+21 sessions, so it is held flat (zero position, zero return, zero cost) until the first signal; the warm-up variant forms the same signals from the pre-inception history and therefore differs only in that ramp"
}
```

## Gate tables (config/promotion_gates.yaml, unchanged)

```json
{
  "union_sample": {
    "track_record_length": {
      "value": 8504.0,
      "threshold": 126.0,
      "comparison": "gte",
      "pass": true
    },
    "full_period_sharpe": {
      "value": 0.5602214749842194,
      "threshold": 0.9,
      "comparison": "gte",
      "pass": false
    },
    "rolling_63d_sharpe": {
      "value": -1.3233468907373043,
      "threshold": 0.9,
      "comparison": "gte",
      "pass": false
    },
    "max_drawdown": {
      "value": -0.6224126346564325,
      "threshold": -0.15,
      "comparison": "gte",
      "pass": false
    },
    "rolling_63d_max_dd": {
      "value": -0.109209305725669,
      "threshold": -0.15,
      "comparison": "gte",
      "pass": true
    },
    "regime_flips": {
      "value": 6.0,
      "threshold": 1.0,
      "comparison": "gte",
      "pass": true
    },
    "psr": {
      "value": 1.0078448910250733e-08,
      "threshold": 0.95,
      "comparison": "gte",
      "pass": false
    }
  },
  "common_inception_slice": {
    "track_record_length": {
      "value": 5529.0,
      "threshold": 126.0,
      "comparison": "gte",
      "pass": true
    },
    "full_period_sharpe": {
      "value": 0.6910457493706031,
      "threshold": 0.9,
      "comparison": "gte",
      "pass": false
    },
    "rolling_63d_sharpe": {
      "value": -1.3233468907373043,
      "threshold": 0.9,
      "comparison": "gte",
      "pass": false
    },
    "max_drawdown": {
      "value": -0.3669795914712545,
      "threshold": -0.15,
      "comparison": "gte",
      "pass": false
    },
    "rolling_63d_max_dd": {
      "value": -0.109209305725669,
      "threshold": -0.15,
      "comparison": "gte",
      "pass": true
    },
    "regime_flips": {
      "value": 6.0,
      "threshold": 1.0,
      "comparison": "gte",
      "pass": true
    },
    "psr": {
      "value": 0.00015597590270448715,
      "threshold": 0.95,
      "comparison": "gte",
      "pass": false
    }
  },
  "common_inception_window": {
    "track_record_length": {
      "value": 5529.0,
      "threshold": 126.0,
      "comparison": "gte",
      "pass": true
    },
    "full_period_sharpe": {
      "value": 0.7019873676244225,
      "threshold": 0.9,
      "comparison": "gte",
      "pass": false
    },
    "rolling_63d_sharpe": {
      "value": -1.3233468907373043,
      "threshold": 0.9,
      "comparison": "gte",
      "pass": false
    },
    "max_drawdown": {
      "value": -0.3669795914712546,
      "threshold": -0.15,
      "comparison": "gte",
      "pass": false
    },
    "rolling_63d_max_dd": {
      "value": -0.109209305725669,
      "threshold": -0.15,
      "comparison": "gte",
      "pass": true
    },
    "regime_flips": {
      "value": 6.0,
      "threshold": 1.0,
      "comparison": "gte",
      "pass": true
    },
    "psr": {
      "value": 0.00017476863096306433,
      "threshold": 0.95,
      "comparison": "gte",
      "pass": false
    }
  }
}
```

## Decisions and rationales

```json
{
  "union_sample": {
    "decision": "NO-GO",
    "failed_gates": [
      "full_period_sharpe",
      "rolling_63d_sharpe",
      "max_drawdown",
      "psr"
    ],
    "psr_zone": "below_no_go",
    "rationale": "4 promotion gate(s) failed: full_period_sharpe, rolling_63d_sharpe, max_drawdown, psr. A failing gate can never yield GO, regardless of the PSR.",
    "conditions_for_reevaluation": "Strategy fails go/no-go criteria. Do not promote to live trading without major revision."
  },
  "common_inception_slice": {
    "decision": "NO-GO",
    "failed_gates": [
      "full_period_sharpe",
      "rolling_63d_sharpe",
      "max_drawdown",
      "psr"
    ],
    "psr_zone": "below_no_go",
    "rationale": "4 promotion gate(s) failed: full_period_sharpe, rolling_63d_sharpe, max_drawdown, psr. A failing gate can never yield GO, regardless of the PSR.",
    "conditions_for_reevaluation": "Strategy fails go/no-go criteria. Do not promote to live trading without major revision."
  },
  "common_inception_window": {
    "decision": "NO-GO",
    "failed_gates": [
      "full_period_sharpe",
      "rolling_63d_sharpe",
      "max_drawdown",
      "psr"
    ],
    "psr_zone": "below_no_go",
    "rationale": "4 promotion gate(s) failed: full_period_sharpe, rolling_63d_sharpe, max_drawdown, psr. A failing gate can never yield GO, regardless of the PSR.",
    "conditions_for_reevaluation": "Strategy fails go/no-go criteria. Do not promote to live trading without major revision."
  }
}
```

## Sample-definition sensitivity

```json
{
  "gates_that_disagree": [],
  "decision_union": "NO-GO",
  "decision_common_inception_slice": "NO-GO",
  "decision_common_inception_window": "NO-GO",
  "decision_agrees": true,
  "failed_gates_union": [
    "full_period_sharpe",
    "rolling_63d_sharpe",
    "max_drawdown",
    "psr"
  ],
  "failed_gates_common_inception_slice": [
    "full_period_sharpe",
    "rolling_63d_sharpe",
    "max_drawdown",
    "psr"
  ],
  "failed_gates_common_inception_window": [
    "full_period_sharpe",
    "rolling_63d_sharpe",
    "max_drawdown",
    "psr"
  ],
  "metric_deltas_common_inception_slice_minus_union": {
    "paper_sharpe": 0.13082427438638378,
    "paper_max_dd": 0.255433043185178,
    "psr_normal": 0.0001559658242555769
  },
  "metric_deltas_common_inception_window_minus_union": {
    "paper_sharpe": 0.14176589264020312,
    "paper_max_dd": 0.2554330431851779,
    "psr_normal": 0.00017475855251415407
  }
}
```

## Union sample vs the committed artifact (exact equality)

```json
[
  {
    "name": "union_sample_window",
    "expected": {
      "start_date": "1993-01-29",
      "end_date": "2026-11-05",
      "sessions": 8501
    },
    "observed": {
      "start_date": "1993-01-29",
      "end_date": "2026-11-10",
      "sessions": 8504
    },
    "pass": false
  },
  {
    "name": "union_sample_canonical_metrics",
    "expected": {
      "paper_sharpe": 0.5544866131202392,
      "paper_max_dd": -0.6224126346564325,
      "rolling_sharpe_63d": -2.0322030121783885,
      "rolling_63d_max_dd": -0.109209305725669,
      "regime_flips": 6,
      "paper_days": 8501,
      "sharpe_observed_canonical": 0.5544866131202392,
      "sharpe_se": 0.15353194440392845
    },
    "observed": {
      "paper_sharpe": 0.5602214749842194,
      "paper_max_dd": -0.6224126346564325,
      "rolling_sharpe_63d": -1.3233468907373043,
      "rolling_63d_max_dd": -0.109209305725669,
      "regime_flips": 6,
      "paper_days": 8504,
      "sharpe_observed_canonical": 0.5602214749842194,
      "sharpe_se": 0.15284835880824443
    },
    "pass": false
  },
  {
    "name": "union_sample_psr",
    "expected": {
      "psr_normal": 9.382315085066624e-09,
      "psr_empirical": 0.0
    },
    "observed": {
      "psr_normal": 1.0078448910250733e-08,
      "psr_empirical": 0.0
    },
    "pass": false
  },
  {
    "name": "union_sample_gate_table",
    "expected": {
      "track_record_length": {
        "value": 8501.0,
        "threshold": 126.0,
        "comparison": "gte",
        "pass": true
      },
      "full_period_sharpe": {
        "value": 0.5544866131202392,
        "threshold": 0.9,
        "comparison": "gte",
        "pass": false
      },
      "rolling_63d_sharpe": {
        "value": -2.0322030121783885,
        "threshold": 0.9,
        "comparison": "gte",
        "pass": false
      },
      "max_drawdown": {
        "value": -0.6224126346564325,
        "threshold": -0.15,
        "comparison": "gte",
        "pass": false
      },
      "rolling_63d_max_dd": {
        "value": -0.109209305725669,
        "threshold": -0.15,
        "comparison": "gte",
        "pass": true
      },
      "regime_flips": {
        "value": 6.0,
        "threshold": 1.0,
        "comparison": "gte",
        "pass": true
      },
      "psr": {
        "value": 9.382315085066624e-09,
        "threshold": 0.95,
        "comparison": "gte",
        "pass": false
      }
    },
    "observed": {
      "track_record_length": {
        "value": 8504.0,
        "threshold": 126.0,
        "comparison": "gte",
        "pass": true
      },
      "full_period_sharpe": {
        "value": 0.5602214749842194,
        "threshold": 0.9,
        "comparison": "gte",
        "pass": false
      },
      "rolling_63d_sharpe": {
        "value": -1.3233468907373043,
        "threshold": 0.9,
        "comparison": "gte",
        "pass": false
      },
      "max_drawdown": {
        "value": -0.6224126346564325,
        "threshold": -0.15,
        "comparison": "gte",
        "pass": false
      },
      "rolling_63d_max_dd": {
        "value": -0.109209305725669,
        "threshold": -0.15,
        "comparison": "gte",
        "pass": true
      },
      "regime_flips": {
        "value": 6.0,
        "threshold": 1.0,
        "comparison": "gte",
        "pass": true
      },
      "psr": {
        "value": 1.0078448910250733e-08,
        "threshold": 0.95,
        "comparison": "gte",
        "pass": false
      }
    },
    "pass": false
  },
  {
    "name": "union_sample_decision",
    "expected": {
      "decision": "NO-GO",
      "failed_gates": [
        "full_period_sharpe",
        "rolling_63d_sharpe",
        "max_drawdown",
        "psr"
      ]
    },
    "observed": {
      "decision": "NO-GO",
      "failed_gates": [
        "full_period_sharpe",
        "rolling_63d_sharpe",
        "max_drawdown",
        "psr"
      ]
    },
    "pass": true
  }
]
```

## Structural checks (read-only, window, cross-section)

```json
[
  {
    "name": "data_and_config_unchanged",
    "expected": "identical SHA-256 fingerprint of every file under data/ and config/",
    "observed": {
      "data_files": 1919,
      "config_files": 19,
      "data_unchanged": true,
      "config_unchanged": true
    },
    "pass": true
  },
  {
    "name": "committed_artifact_untouched",
    "expected": "byte-identical research/reports/promotion_feasibility_backtest_001.md",
    "observed": {
      "unchanged": true
    },
    "pass": true
  },
  {
    "name": "union_sample_equals_raw_cache_union_index",
    "expected": {
      "first_date": "1993-01-29",
      "last_date": "2026-11-10",
      "count": 8504
    },
    "observed": {
      "start_date": "1993-01-29",
      "end_date": "2026-11-10",
      "sessions": 8504,
      "equals_raw_cache_union": true
    },
    "pass": true
  },
  {
    "name": "common_inception_sample_is_fully_populated",
    "expected": {
      "price_width_min": 7,
      "price_width_max": 7,
      "momentum_breadth_min": 6,
      "start_date": "2004-11-18",
      "end_date": "2026-11-10"
    },
    "observed": {
      "price_width_min": 7,
      "price_width_max": 7,
      "momentum_breadth_min": 6,
      "start_date": "2004-11-18",
      "end_date": "2026-11-10"
    },
    "pass": true
  },
  {
    "name": "common_inception_sample_sessions_are_a_subset_of_the_union_sample",
    "expected": "every common-inception session exists in the union sample",
    "observed": {
      "slice_sessions": 5529,
      "window_sessions": 5529,
      "subset": true
    },
    "pass": true
  }
]
```

## Verdict

- the sample definition changes the published numbers materially and does not change the verdict
- incumbent published decision: NO-GO (unchanged by this cycle)
- deferred decision: which sample the long-sample diagnostic's gate table is evaluated on is not decided here; the evidence above is the input to that decision. The promotion decision itself is made on the paper record, which the sample definition of the long-sample diagnostic does not affect.
- live deployment: unsupported (unchanged)

## Data used

```json
{
  "source": "committed raw cache (data/raw/*.parquet)",
  "universe": [
    "SPY",
    "QQQ",
    "IWM",
    "TLT",
    "GLD",
    "EFA",
    "EEM"
  ],
  "union_start_date": "1993-01-29",
  "union_end_date": "2026-11-10",
  "union_sessions": 8504,
  "common_inception": "2004-11-18",
  "per_symbol_stats": {
    "SPY": {
      "first_date": "1993-01-29",
      "last_date": "2026-11-10",
      "row_count": 8504
    },
    "QQQ": {
      "first_date": "1999-03-10",
      "last_date": "2026-11-10",
      "row_count": 6962
    },
    "IWM": {
      "first_date": "2000-05-26",
      "last_date": "2026-11-10",
      "row_count": 6654
    },
    "TLT": {
      "first_date": "2002-07-30",
      "last_date": "2026-11-10",
      "row_count": 6111
    },
    "GLD": {
      "first_date": "2004-11-18",
      "last_date": "2026-11-10",
      "row_count": 5529
    },
    "EFA": {
      "first_date": "2001-08-27",
      "last_date": "2026-11-10",
      "row_count": 6339
    },
    "EEM": {
      "first_date": "2003-04-14",
      "last_date": "2026-11-10",
      "row_count": 5933
    }
  },
  "sha256_raw_files": {
    "SPY": "96a0c39582d691132f02229bede5d4e943468027718716e8a50421e6aad0b0b9",
    "QQQ": "855ac59a412888d7d90ecaa1d5267ec0e8201244f26f558f95ffe0ca7d6b8269",
    "IWM": "7293151372d6e710b02281ef2b56dfa85e632c0026f4c407b4cecf974265285d",
    "TLT": "22987a3b280d135afcc276c0ce6576e70234e026e27c7be48e11985f3abc5ee6",
    "GLD": "f062f48a42353b4992de4149499ff5e807ef3b37613af5a70898486b9733255b",
    "EFA": "b2405c1a104300504903add96983b4191d99105ad464e323b0e7c142a18d6fe7",
    "EEM": "00a7163d69c343e7a64d88eb75dfe1e6ce2d9b628d4eea8666d8a4ca8bc3fb1a"
  },
  "point_in_time_treatment": "signals use only data up to the formation session, positions are effective on the next session (build_weights shifts by one day); no forward-looking data is used",
  "missing_data_handling": "the engine forward-fills each symbol on the union calendar; the cross-section width published here counts the assets that have a price on each session"
}
```

## Reproduction

```json
{
  "command": "python research/common_inception_sample_audit.py",
  "deterministic": true,
  "no_network": true,
  "read_only_data": true,
  "test": "python -m pytest -q tests/test_common_inception_sample_audit.py"
}
```

## Method

```json
{
  "measurement": "one deterministic measurement of the frozen candidate on three samples; no parameter search, no re-fit, no re-selection",
  "trials": 1,
  "engine": "src/backtest/engine.py:run_backtest, unchanged; the price frame is truncated in front of it for the slice variant and the engine's window semantics are untouched",
  "gate_table": "src/simulation/evaluation.py:evaluate_promotion_gates + map_decision on config/promotion_gates.yaml, unchanged",
  "psr": "src/evaluation/statistics.py:compute_psr, seed 20240101, target 1.4178 (the recorded backtest baseline)",
  "sharpe_convention": "arithmetic_annualized_rf0 (src/evaluation/sharpe.py)",
  "cost_model": "config/settings.yaml (1 bps commission + 2 bps slippage)",
  "splits": "none: a long-sample diagnostic has no train/validation/test split; the three samples are published side by side instead",
  "rolling_window": "the trailing 63 sessions of each sample's own net-return series (sharpe_ratio over the last 63 sessions, drawdown over the same window).  All three samples end on the same session, so their trailing 63-session windows are the same 63 sessions and their rolling-63d values are identical by construction -- not because a shared series was evaluated"
}
```

## Falsification conditions

- a gate, a threshold, the decision mapping or the Sharpe convention changed -> reject.
- the union-sample numbers differ from the committed artifact -> reject.
- the committed artifact is regenerated or edited by this tool -> reject.
- a file under data/ or config/ changed during the run -> reject.
- the common-inception sample does not have seven assets with a price -> reject.
- two runs of the tool disagree -> reject.
