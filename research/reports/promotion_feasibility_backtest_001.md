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
  "label_end_date": "2026-10-19",
  "realized_start_date": "1993-01-29",
  "realized_end_date": "2026-10-19",
  "realized_session_count": 8488,
  "start_date": "1993-01-29",
  "end_date": "2026-10-19",
  "session_count": 8488,
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
    "SPY": "971d02284b9790dfd282438b98f5a0c08cc409e379d1598a41c02d96eb00f47e",
    "QQQ": "71215972c77f917d54da229ee445c16edc4f51fd997f878a2ae3888855fb08ad",
    "IWM": "5bd3985f67dd47ad1ae75d1c23b7effa4d3bc7abd730cf7ac8c5c99887d91593",
    "TLT": "f745d0921006c792dd1ad180cefea529bf049cda24e4dc9fc0a378208a8c36e7",
    "GLD": "5ca9683ee5f6af6e25febb0c1c698e5505f255771ee4d19b57f725f849015696",
    "EFA": "a77623de41bdf6d5c48810c54079dbaa15181a30113b1b317e67630851592f8b",
    "EEM": "922f0181be3ed98ca4ad1ab844ed87dbda9afa562b44bde20b4dbf730f6693c8"
  },
  "per_symbol_stats": {
    "SPY": {
      "first_date": "1993-01-29",
      "last_date": "2026-10-19",
      "row_count": 8488
    },
    "QQQ": {
      "first_date": "1999-03-10",
      "last_date": "2026-10-19",
      "row_count": 6946
    },
    "IWM": {
      "first_date": "2000-05-26",
      "last_date": "2026-10-19",
      "row_count": 6638
    },
    "TLT": {
      "first_date": "2002-07-30",
      "last_date": "2026-10-19",
      "row_count": 6095
    },
    "GLD": {
      "first_date": "2004-11-18",
      "last_date": "2026-10-19",
      "row_count": 5513
    },
    "EFA": {
      "first_date": "2001-08-27",
      "last_date": "2026-10-19",
      "row_count": 6323
    },
    "EEM": {
      "first_date": "2003-04-14",
      "last_date": "2026-10-19",
      "row_count": 5917
    }
  },
  "union_index_fingerprint": {
    "first_date": "1993-01-29",
    "last_date": "2026-10-19",
    "count": 8488
  },
  "cache_fingerprint": {
    "per_symbol": {
      "SPY": {
        "rows": 8488,
        "first_date": "1993-01-29",
        "last_date": "2026-10-19",
        "sha256": "971d02284b9790dfd282438b98f5a0c08cc409e379d1598a41c02d96eb00f47e"
      },
      "QQQ": {
        "rows": 6946,
        "first_date": "1999-03-10",
        "last_date": "2026-10-19",
        "sha256": "71215972c77f917d54da229ee445c16edc4f51fd997f878a2ae3888855fb08ad"
      },
      "IWM": {
        "rows": 6638,
        "first_date": "2000-05-26",
        "last_date": "2026-10-19",
        "sha256": "5bd3985f67dd47ad1ae75d1c23b7effa4d3bc7abd730cf7ac8c5c99887d91593"
      },
      "TLT": {
        "rows": 6095,
        "first_date": "2002-07-30",
        "last_date": "2026-10-19",
        "sha256": "f745d0921006c792dd1ad180cefea529bf049cda24e4dc9fc0a378208a8c36e7"
      },
      "GLD": {
        "rows": 5513,
        "first_date": "2004-11-18",
        "last_date": "2026-10-19",
        "sha256": "5ca9683ee5f6af6e25febb0c1c698e5505f255771ee4d19b57f725f849015696"
      },
      "EFA": {
        "rows": 6323,
        "first_date": "2001-08-27",
        "last_date": "2026-10-19",
        "sha256": "a77623de41bdf6d5c48810c54079dbaa15181a30113b1b317e67630851592f8b"
      },
      "EEM": {
        "rows": 5917,
        "first_date": "2003-04-14",
        "last_date": "2026-10-19",
        "sha256": "922f0181be3ed98ca4ad1ab844ed87dbda9afa562b44bde20b4dbf730f6693c8"
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
  "paper_sharpe": 0.5657179297830458,
  "paper_max_dd": -0.6224126346564325,
  "rolling_sharpe_63d": -0.03425220400791309,
  "rolling_63d_max_dd": -0.061360722514321675,
  "regime_flips": 6,
  "paper_days": 8488,
  "sharpe_observed_canonical": 0.5657179297830458,
  "sharpe_se": 0.15424519947175822
}
```

## Backtest-baseline scale (cagr_annualized_rf2)

```json
{
  "sharpe_backtest_scale": 0.38434756317328844,
  "psr_target_backtest_scale": 1.4178,
  "baseline_tieback": {
    "recorded_baseline": 1.4178,
    "tolerance": "window/warmup/costs explain deviation (must be quantified)",
    "within_tolerance": false,
    "delta": -1.0334524368267115
  }
}
```

## PSR vs backtest baseline 1.4178

```json
{
  "psr_normal": 1.6549061233035153e-08,
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
    "value": 8488.0,
    "threshold": 126.0,
    "comparison": "gte",
    "pass": true
  },
  "full_period_sharpe": {
    "value": 0.5657179297830458,
    "threshold": 0.9,
    "comparison": "gte",
    "pass": false
  },
  "rolling_63d_sharpe": {
    "value": -0.03425220400791309,
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
    "value": -0.061360722514321675,
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
    "value": 1.6549061233035153e-08,
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
  "required_observed_sharpe_for_psr095": 1.6715107757909746,
  "sharpe_se_at_this_sample": 0.15424519947175822,
  "sample_length": 8488,
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
