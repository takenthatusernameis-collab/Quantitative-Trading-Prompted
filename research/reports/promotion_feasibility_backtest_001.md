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
  "label_end_date": "2026-11-10",
  "realized_start_date": "1993-01-29",
  "realized_end_date": "2026-11-10",
  "realized_session_count": 8504,
  "start_date": "1993-01-29",
  "end_date": "2026-11-10",
  "session_count": 8504,
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
    "SPY": "96a0c39582d691132f02229bede5d4e943468027718716e8a50421e6aad0b0b9",
    "QQQ": "855ac59a412888d7d90ecaa1d5267ec0e8201244f26f558f95ffe0ca7d6b8269",
    "IWM": "7293151372d6e710b02281ef2b56dfa85e632c0026f4c407b4cecf974265285d",
    "TLT": "22987a3b280d135afcc276c0ce6576e70234e026e27c7be48e11985f3abc5ee6",
    "GLD": "f062f48a42353b4992de4149499ff5e807ef3b37613af5a70898486b9733255b",
    "EFA": "b2405c1a104300504903add96983b4191d99105ad464e323b0e7c142a18d6fe7",
    "EEM": "00a7163d69c343e7a64d88eb75dfe1e6ce2d9b628d4eea8666d8a4ca8bc3fb1a"
  },
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
  "union_index_fingerprint": {
    "first_date": "1993-01-29",
    "last_date": "2026-11-10",
    "count": 8504
  },
  "cache_fingerprint": {
    "per_symbol": {
      "SPY": {
        "rows": 8504,
        "first_date": "1993-01-29",
        "last_date": "2026-11-10",
        "sha256": "96a0c39582d691132f02229bede5d4e943468027718716e8a50421e6aad0b0b9"
      },
      "QQQ": {
        "rows": 6962,
        "first_date": "1999-03-10",
        "last_date": "2026-11-10",
        "sha256": "855ac59a412888d7d90ecaa1d5267ec0e8201244f26f558f95ffe0ca7d6b8269"
      },
      "IWM": {
        "rows": 6654,
        "first_date": "2000-05-26",
        "last_date": "2026-11-10",
        "sha256": "7293151372d6e710b02281ef2b56dfa85e632c0026f4c407b4cecf974265285d"
      },
      "TLT": {
        "rows": 6111,
        "first_date": "2002-07-30",
        "last_date": "2026-11-10",
        "sha256": "22987a3b280d135afcc276c0ce6576e70234e026e27c7be48e11985f3abc5ee6"
      },
      "GLD": {
        "rows": 5529,
        "first_date": "2004-11-18",
        "last_date": "2026-11-10",
        "sha256": "f062f48a42353b4992de4149499ff5e807ef3b37613af5a70898486b9733255b"
      },
      "EFA": {
        "rows": 6339,
        "first_date": "2001-08-27",
        "last_date": "2026-11-10",
        "sha256": "b2405c1a104300504903add96983b4191d99105ad464e323b0e7c142a18d6fe7"
      },
      "EEM": {
        "rows": 5933,
        "first_date": "2003-04-14",
        "last_date": "2026-11-10",
        "sha256": "00a7163d69c343e7a64d88eb75dfe1e6ce2d9b628d4eea8666d8a4ca8bc3fb1a"
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
  "paper_sharpe": 0.5602214749842194,
  "paper_max_dd": -0.6224126346564325,
  "rolling_sharpe_63d": -1.3233468907373043,
  "rolling_63d_max_dd": -0.109209305725669,
  "regime_flips": 6,
  "paper_days": 8504,
  "sharpe_observed_canonical": 0.5602214749842194,
  "sharpe_se": 0.15284835880824443
}
```

## Backtest-baseline scale (cagr_annualized_rf2)

```json
{
  "sharpe_backtest_scale": 0.3784336640180774,
  "psr_target_backtest_scale": 1.4178,
  "baseline_tieback": {
    "recorded_baseline": 1.4178,
    "tolerance": "window/warmup/costs explain deviation (must be quantified)",
    "within_tolerance": false,
    "delta": -1.0393663359819225
  }
}
```

## PSR vs backtest baseline 1.4178

```json
{
  "psr_normal": 1.0078448910250733e-08,
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
  "required_observed_sharpe_for_psr095": 1.6692131773593208,
  "sharpe_se_at_this_sample": 0.15284835880824443,
  "sample_length": 8504,
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
