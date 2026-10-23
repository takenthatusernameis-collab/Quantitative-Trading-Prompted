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
  "label_end_date": "2026-10-22",
  "realized_start_date": "1993-01-29",
  "realized_end_date": "2026-10-22",
  "realized_session_count": 8491,
  "start_date": "1993-01-29",
  "end_date": "2026-10-22",
  "session_count": 8491,
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
    "SPY": "f307f910a62dc3e237afc7a4910f5b3508c75c3f83330735d55aead81e459375",
    "QQQ": "3de8a01c4f0d6f77ddebd98295f5da5adb19ac6feade90d747cb7876a9faa872",
    "IWM": "0e32b42393e5dad65ea810d099c88ed21eba890c1d0d5e521b473da92ad74cb4",
    "TLT": "851db269e1622eb6684c075ce94a0a38f2e72b3f4a6f2202ab72b7a712f5c6ce",
    "GLD": "6e681051e18253fa9487ca86aff096e6ea5f81dc1d44995eefa0380cef2166c7",
    "EFA": "f72c519b0974467167e2f822eece66da6dbe1329dbd2981a86a373c5e303b101",
    "EEM": "17ad1692de6eee0b4eb32862c9133eab4b851865c5c2a78f05a6cbf5dfeb9ed5"
  },
  "per_symbol_stats": {
    "SPY": {
      "first_date": "1993-01-29",
      "last_date": "2026-10-22",
      "row_count": 8491
    },
    "QQQ": {
      "first_date": "1999-03-10",
      "last_date": "2026-10-22",
      "row_count": 6949
    },
    "IWM": {
      "first_date": "2000-05-26",
      "last_date": "2026-10-22",
      "row_count": 6641
    },
    "TLT": {
      "first_date": "2002-07-30",
      "last_date": "2026-10-22",
      "row_count": 6098
    },
    "GLD": {
      "first_date": "2004-11-18",
      "last_date": "2026-10-22",
      "row_count": 5516
    },
    "EFA": {
      "first_date": "2001-08-27",
      "last_date": "2026-10-22",
      "row_count": 6326
    },
    "EEM": {
      "first_date": "2003-04-14",
      "last_date": "2026-10-22",
      "row_count": 5920
    }
  },
  "union_index_fingerprint": {
    "first_date": "1993-01-29",
    "last_date": "2026-10-22",
    "count": 8491
  },
  "cache_fingerprint": {
    "per_symbol": {
      "SPY": {
        "rows": 8491,
        "first_date": "1993-01-29",
        "last_date": "2026-10-22",
        "sha256": "f307f910a62dc3e237afc7a4910f5b3508c75c3f83330735d55aead81e459375"
      },
      "QQQ": {
        "rows": 6949,
        "first_date": "1999-03-10",
        "last_date": "2026-10-22",
        "sha256": "3de8a01c4f0d6f77ddebd98295f5da5adb19ac6feade90d747cb7876a9faa872"
      },
      "IWM": {
        "rows": 6641,
        "first_date": "2000-05-26",
        "last_date": "2026-10-22",
        "sha256": "0e32b42393e5dad65ea810d099c88ed21eba890c1d0d5e521b473da92ad74cb4"
      },
      "TLT": {
        "rows": 6098,
        "first_date": "2002-07-30",
        "last_date": "2026-10-22",
        "sha256": "851db269e1622eb6684c075ce94a0a38f2e72b3f4a6f2202ab72b7a712f5c6ce"
      },
      "GLD": {
        "rows": 5516,
        "first_date": "2004-11-18",
        "last_date": "2026-10-22",
        "sha256": "6e681051e18253fa9487ca86aff096e6ea5f81dc1d44995eefa0380cef2166c7"
      },
      "EFA": {
        "rows": 6326,
        "first_date": "2001-08-27",
        "last_date": "2026-10-22",
        "sha256": "f72c519b0974467167e2f822eece66da6dbe1329dbd2981a86a373c5e303b101"
      },
      "EEM": {
        "rows": 5920,
        "first_date": "2003-04-14",
        "last_date": "2026-10-22",
        "sha256": "17ad1692de6eee0b4eb32862c9133eab4b851865c5c2a78f05a6cbf5dfeb9ed5"
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
  "paper_sharpe": 0.5643531603402314,
  "paper_max_dd": -0.6224126346564325,
  "rolling_sharpe_63d": 0.3822172141588271,
  "rolling_63d_max_dd": -0.061716508955863225,
  "regime_flips": 6,
  "paper_days": 8491,
  "sharpe_observed_canonical": 0.5643531603402314,
  "sharpe_se": 0.15699397227536388
}
```

## Backtest-baseline scale (cagr_annualized_rf2)

```json
{
  "sharpe_backtest_scale": 0.3828642682684244,
  "psr_target_backtest_scale": 1.4178,
  "baseline_tieback": {
    "recorded_baseline": 1.4178,
    "tolerance": "window/warmup/costs explain deviation (must be quantified)",
    "within_tolerance": false,
    "delta": -1.0349357317315755
  }
}
```

## PSR vs backtest baseline 1.4178

```json
{
  "psr_normal": 2.7218117229036965e-08,
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
    "value": 8491.0,
    "threshold": 126.0,
    "comparison": "gte",
    "pass": true
  },
  "full_period_sharpe": {
    "value": 0.5643531603402314,
    "threshold": 0.9,
    "comparison": "gte",
    "pass": false
  },
  "rolling_63d_sharpe": {
    "value": 0.3822172141588271,
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
    "value": -0.061716508955863225,
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
    "value": 2.7218117229036965e-08,
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
  "required_observed_sharpe_for_psr095": 1.676032104706651,
  "sharpe_se_at_this_sample": 0.15699397227536388,
  "sample_length": 8491,
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
