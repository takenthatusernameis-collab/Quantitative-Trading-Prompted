# Promotion Criteria Feasibility (Cycle 867)

`label_*` is the common inception of the universe (the max of the per-symbol first
dates); `realized_*` (and the historical `start_date` / `end_date` /
`session_count` keys) is the sample the backtest actually computed. The engine
does not slice the price frame to the common inception, so the realized sample
is the union calendar of the raw cache -- the two windows are published side by
side instead of one being labelled as the other.

## Sample definition

```json
{
  "label_start_date": "2004-11-18",
  "label_end_date": "2026-11-05",
  "realized_start_date": "1993-01-29",
  "realized_end_date": "2026-11-05",
  "realized_session_count": 8501,
  "start_date": "1993-01-29",
  "end_date": "2026-11-05",
  "session_count": 8501,
  "universe": [
    "SPY",
    "QQQ",
    "IWM",
    "TLT",
    "GLD",
    "EFA",
    "EEM"
  ],
  "lookback": 226,
  "skip": 21,
  "top_fraction": 0.5,
  "rebalance_freq": "monthly",
  "cost_model": {
    "commission_bps": 1.0,
    "slippage_bps": 2.0,
    "total_round_trip_bps": 3.0
  },
  "overlay_warmup": "slice",
  "data_source": "committed raw cache (data/raw/*.parquet)",
  "sha256_raw_files": {
    "SPY": "e23d1cb44f361354293187d1c514d69d4f8dc58bbabe6c9cc58096eecb52102b",
    "QQQ": "5b867704a6d2b87615c2d6867b6e068c1e50f3b59f0030d54ece7529208c90ba",
    "IWM": "c16dd9c4a3ea1a5815d37bec1c222e71f4af439378d1f10cc85210f75fa47201",
    "TLT": "ee9b2f84d5cf1b195d821499d3d54bbb143000c6b302ecf5f33fd74fc54177e1",
    "GLD": "ad0cc279eb77ad6622d16e147944d263893b7a5dd74bc596f425dd77cb056669",
    "EFA": "875eecce9ab7c80ec9ba954a76fd1eb06519b8c85bdea3664fea0d432689c218",
    "EEM": "0630300350fe56bc729e3104be12a6d0f2fcc58de0cc83703a3cc39793fdd980"
  },
  "per_symbol_stats": {
    "SPY": {
      "first_date": "1993-01-29",
      "last_date": "2026-11-05",
      "row_count": 8501
    },
    "QQQ": {
      "first_date": "1999-03-10",
      "last_date": "2026-11-05",
      "row_count": 6959
    },
    "IWM": {
      "first_date": "2000-05-26",
      "last_date": "2026-11-05",
      "row_count": 6651
    },
    "TLT": {
      "first_date": "2002-07-30",
      "last_date": "2026-11-05",
      "row_count": 6108
    },
    "GLD": {
      "first_date": "2004-11-18",
      "last_date": "2026-11-05",
      "row_count": 5526
    },
    "EFA": {
      "first_date": "2001-08-27",
      "last_date": "2026-11-05",
      "row_count": 6336
    },
    "EEM": {
      "first_date": "2003-04-14",
      "last_date": "2026-11-05",
      "row_count": 5930
    }
  },
  "union_index_fingerprint": {
    "first_date": "1993-01-29",
    "last_date": "2026-11-05",
    "count": 8501
  },
  "cache_fingerprint": {
    "per_symbol": {
      "SPY": {
        "rows": 8501,
        "first_date": "1993-01-29",
        "last_date": "2026-11-05",
        "sha256": "e23d1cb44f361354293187d1c514d69d4f8dc58bbabe6c9cc58096eecb52102b"
      },
      "QQQ": {
        "rows": 6959,
        "first_date": "1999-03-10",
        "last_date": "2026-11-05",
        "sha256": "5b867704a6d2b87615c2d6867b6e068c1e50f3b59f0030d54ece7529208c90ba"
      },
      "IWM": {
        "rows": 6651,
        "first_date": "2000-05-26",
        "last_date": "2026-11-05",
        "sha256": "c16dd9c4a3ea1a5815d37bec1c222e71f4af439378d1f10cc85210f75fa47201"
      },
      "TLT": {
        "rows": 6108,
        "first_date": "2002-07-30",
        "last_date": "2026-11-05",
        "sha256": "ee9b2f84d5cf1b195d821499d3d54bbb143000c6b302ecf5f33fd74fc54177e1"
      },
      "GLD": {
        "rows": 5526,
        "first_date": "2004-11-18",
        "last_date": "2026-11-05",
        "sha256": "ad0cc279eb77ad6622d16e147944d263893b7a5dd74bc596f425dd77cb056669"
      },
      "EFA": {
        "rows": 6336,
        "first_date": "2001-08-27",
        "last_date": "2026-11-05",
        "sha256": "875eecce9ab7c80ec9ba954a76fd1eb06519b8c85bdea3664fea0d432689c218"
      },
      "EEM": {
        "rows": 5930,
        "first_date": "2003-04-14",
        "last_date": "2026-11-05",
        "sha256": "0630300350fe56bc729e3104be12a6d0f2fcc58de0cc83703a3cc39793fdd980"
      }
    },
    "note": "derived from the raw cache at run time; a later append to the cache changes these values and is therefore visible as a fingerprint change"
  },
  "reference_sample_anchors": {
    "incumbent_reference_end": "2026-10-16",
    "incumbent_reference_sessions": 8487,
    "incumbent_reference_sharpe": 0.5646255767978904,
    "incumbent_reference_max_drawdown": -0.6224126346564325,
    "incumbent_reference_psr": 2.2219753177036448e-08,
    "paper_record_reference_sessions": 449,
    "paper_record_reference_sharpe": 1.748401
  },
  "reference_sample_checks": [
    {
      "name": "incumbent_reference_sample",
      "definition": "realized net returns truncated at 2026-10-16",
      "expected": {
        "sessions": 8487,
        "sharpe": 0.5646255767978904,
        "max_drawdown": -0.6224126346564325,
        "psr": 2.2219753177036448e-08
      },
      "observed": {
        "sessions": 8487,
        "sharpe": 0.5646255767978904,
        "max_drawdown": -0.6224126346564325,
        "psr": 2.2219753177036448e-08
      },
      "pass": true
    },
    {
      "name": "paper_record_reference_sample",
      "definition": "first 449 sessions of the committed paper record",
      "expected": {
        "sessions": 449,
        "sharpe": 1.748401
      },
      "observed": {
        "sessions": 449,
        "sharpe": 1.748401004742091
      },
      "pass": true
    }
  ]
}
```

## Canonical metrics (arithmetic_annualized_rf0)

```json
{
  "paper_sharpe": 0.5544866131202392,
  "paper_max_dd": -0.6224126346564325,
  "rolling_sharpe_63d": -2.0322030121783885,
  "rolling_63d_max_dd": -0.109209305725669,
  "regime_flips": 6,
  "paper_days": 8501,
  "sharpe_observed_canonical": 0.5544866131202392,
  "sharpe_se": 0.15353194440392845
}
```

## Backtest-baseline scale (cagr_annualized_rf2)

```json
{
  "sharpe_backtest_scale": 0.37219520221141195,
  "psr_target_backtest_scale": 1.4178,
  "baseline_tieback": {
    "recorded_baseline": 1.4178,
    "tolerance": "window/warmup/costs explain deviation (must be quantified)",
    "within_tolerance": false,
    "delta": -1.045604797788588
  }
}
```

## PSR vs backtest baseline 1.4178

```json
{
  "psr_normal": 9.382315085066624e-09,
  "psr_empirical": 0.0,
  "psr_zone": "below_grey",
  "sharpe_ci_lower": NaN,
  "sharpe_ci_upper": NaN
}
```

## Gate evaluation (same table as config/promotion_gates.yaml)

```json
{
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
}
```

## Reference-sample integrity (Cycle 901/902 anchors)

```json
[
  {
    "name": "incumbent_reference_sample",
    "definition": "realized net returns truncated at 2026-10-16",
    "expected": {
      "sessions": 8487,
      "sharpe": 0.5646255767978904,
      "max_drawdown": -0.6224126346564325,
      "psr": 2.2219753177036448e-08
    },
    "observed": {
      "sessions": 8487,
      "sharpe": 0.5646255767978904,
      "max_drawdown": -0.6224126346564325,
      "psr": 2.2219753177036448e-08
    },
    "pass": true
  },
  {
    "name": "paper_record_reference_sample",
    "definition": "first 449 sessions of the committed paper record",
    "expected": {
      "sessions": 449,
      "sharpe": 1.748401
    },
    "observed": {
      "sessions": 449,
      "sharpe": 1.748401004742091
    },
    "pass": true
  }
]
```

## Decision

- decision: NO-GO
- failed_gates: ['full_period_sharpe', 'rolling_63d_sharpe', 'max_drawdown', 'psr']
- psr_zone: below_grey

## Attainability (explicit answer)

```json
{
  "psr_reaches_095": false,
  "required_observed_sharpe_for_psr095": 1.6703375756057135,
  "sharpe_se_at_this_sample": 0.15353194440392845,
  "sample_length": 8501,
  "note": "PSR>=0.95 when (sr_obs - sr_t)/se >= 1.64485 at same SE."
}
```

## Consequence for research loop

not promotable in principle

## Falsification conditions

- backtest reads from network (cache bypass) -> false claim; must be read-only.
- long-sample uses different universe/window than stated -> reject.
- canonical vs backtest-baseline scales mixed -> reject.
- gate thresholds changed from config/promotion_gates.yaml -> reject.
- published realized window differs from the raw-cache union index -> reject.
- a reference-sample anchor no longer reproduces -> reject.

## Reproduction

```json
{
  "command": "python research/promotion_feasibility_backtest.py",
  "deterministic": true,
  "no_network": true,
  "read_only_data": true
}
```
