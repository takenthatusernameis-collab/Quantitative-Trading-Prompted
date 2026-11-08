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
  "label_end_date": "2026-11-06",
  "realized_start_date": "1993-01-29",
  "realized_end_date": "2026-11-06",
  "realized_session_count": 8502,
  "start_date": "1993-01-29",
  "end_date": "2026-11-06",
  "session_count": 8502,
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
    "SPY": "7649e6a42c1282f021870650c06c11044dceacb47d78a2cfa7e65d0d74eb0f38",
    "QQQ": "2592918f78c2e88e6cfedf32da7f9815e379a0dd341d58ecde2063cb2c8e0f2b",
    "IWM": "31d5093c17a884e0fdcea95f99d4639b821393b911fe8004642edca30d073eb6",
    "TLT": "809f3531285eb971178a2a272bc15ab9b9273180586bc0c8cb67d4cb7983562c",
    "GLD": "185f6120aa79dc017e445cd448d19029b9d5b124386671ccabd89ea9c81dbd0d",
    "EFA": "f90dcab2a54e77877b001c177cda62e22e9445a3e2a1063672f7f5aae760c6fd",
    "EEM": "0155ad5f13503c6a281dbe4e63d69c1f2470431325d2d8a758e83395c5ef0620"
  },
  "per_symbol_stats": {
    "SPY": {
      "first_date": "1993-01-29",
      "last_date": "2026-11-06",
      "row_count": 8502
    },
    "QQQ": {
      "first_date": "1999-03-10",
      "last_date": "2026-11-06",
      "row_count": 6960
    },
    "IWM": {
      "first_date": "2000-05-26",
      "last_date": "2026-11-06",
      "row_count": 6652
    },
    "TLT": {
      "first_date": "2002-07-30",
      "last_date": "2026-11-06",
      "row_count": 6109
    },
    "GLD": {
      "first_date": "2004-11-18",
      "last_date": "2026-11-06",
      "row_count": 5527
    },
    "EFA": {
      "first_date": "2001-08-27",
      "last_date": "2026-11-06",
      "row_count": 6337
    },
    "EEM": {
      "first_date": "2003-04-14",
      "last_date": "2026-11-06",
      "row_count": 5931
    }
  },
  "union_index_fingerprint": {
    "first_date": "1993-01-29",
    "last_date": "2026-11-06",
    "count": 8502
  },
  "cache_fingerprint": {
    "per_symbol": {
      "SPY": {
        "rows": 8502,
        "first_date": "1993-01-29",
        "last_date": "2026-11-06",
        "sha256": "7649e6a42c1282f021870650c06c11044dceacb47d78a2cfa7e65d0d74eb0f38"
      },
      "QQQ": {
        "rows": 6960,
        "first_date": "1999-03-10",
        "last_date": "2026-11-06",
        "sha256": "2592918f78c2e88e6cfedf32da7f9815e379a0dd341d58ecde2063cb2c8e0f2b"
      },
      "IWM": {
        "rows": 6652,
        "first_date": "2000-05-26",
        "last_date": "2026-11-06",
        "sha256": "31d5093c17a884e0fdcea95f99d4639b821393b911fe8004642edca30d073eb6"
      },
      "TLT": {
        "rows": 6109,
        "first_date": "2002-07-30",
        "last_date": "2026-11-06",
        "sha256": "809f3531285eb971178a2a272bc15ab9b9273180586bc0c8cb67d4cb7983562c"
      },
      "GLD": {
        "rows": 5527,
        "first_date": "2004-11-18",
        "last_date": "2026-11-06",
        "sha256": "185f6120aa79dc017e445cd448d19029b9d5b124386671ccabd89ea9c81dbd0d"
      },
      "EFA": {
        "rows": 6337,
        "first_date": "2001-08-27",
        "last_date": "2026-11-06",
        "sha256": "f90dcab2a54e77877b001c177cda62e22e9445a3e2a1063672f7f5aae760c6fd"
      },
      "EEM": {
        "rows": 5931,
        "first_date": "2003-04-14",
        "last_date": "2026-11-06",
        "sha256": "0155ad5f13503c6a281dbe4e63d69c1f2470431325d2d8a758e83395c5ef0620"
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
  "paper_sharpe": 0.5564979703883025,
  "paper_max_dd": -0.6224126346564325,
  "rolling_sharpe_63d": -1.7076117952763843,
  "rolling_63d_max_dd": -0.109209305725669,
  "regime_flips": 6,
  "paper_days": 8502,
  "sharpe_observed_canonical": 0.5564979703883025,
  "sharpe_se": 0.15264855348720863
}
```

## Backtest-baseline scale (cagr_annualized_rf2)

```json
{
  "sharpe_backtest_scale": 0.37437761124543095,
  "psr_target_backtest_scale": 1.4178,
  "baseline_tieback": {
    "recorded_baseline": 1.4178,
    "tolerance": "window/warmup/costs explain deviation (must be quantified)",
    "within_tolerance": false,
    "delta": -1.043422388754569
  }
}
```

## PSR vs backtest baseline 1.4178

```json
{
  "psr_normal": 8.385489043436886e-09,
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
    "value": 8502.0,
    "threshold": 126.0,
    "comparison": "gte",
    "pass": true
  },
  "full_period_sharpe": {
    "value": 0.5564979703883025,
    "threshold": 0.9,
    "comparison": "gte",
    "pass": false
  },
  "rolling_63d_sharpe": {
    "value": -1.7076117952763843,
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
    "value": 8.385489043436886e-09,
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
  "required_observed_sharpe_for_psr095": 1.668884526852331,
  "sharpe_se_at_this_sample": 0.15264855348720863,
  "sample_length": 8502,
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
