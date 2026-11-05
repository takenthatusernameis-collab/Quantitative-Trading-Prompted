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
  "label_end_date": "2026-11-04",
  "realized_start_date": "1993-01-29",
  "realized_end_date": "2026-11-04",
  "realized_session_count": 8500,
  "start_date": "1993-01-29",
  "end_date": "2026-11-04",
  "session_count": 8500,
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
    "SPY": "7e695da550ce958da253007735f0e973ef7afd44ccf8844dd831a5cbf057ad1a",
    "QQQ": "4bb3b6f2b8a6ae9cce37c8cc1c33cdc8bf51d78c05c14072808f4621ef15d93e",
    "IWM": "9f16d0f9b1a0379b907e7512a56d1406fd1b1e51474834d7335ba137718c3248",
    "TLT": "1ecb72283daee4cbad90f9f0f352ec1a3a6b258131e81111e1e82b4e531d83c8",
    "GLD": "03a498b72d0e539a9da1e2ebb4045456d050d5853408f761872860b14b9a6966",
    "EFA": "a1d87c46db15174d367512e585e2da97882426ee9c8582687c59e3f379ee2b73",
    "EEM": "57e1faec0e1cbd68b2a1a5b406734c138bbc73485a44ee52ed790042df0c49e9"
  },
  "per_symbol_stats": {
    "SPY": {
      "first_date": "1993-01-29",
      "last_date": "2026-11-04",
      "row_count": 8500
    },
    "QQQ": {
      "first_date": "1999-03-10",
      "last_date": "2026-11-04",
      "row_count": 6958
    },
    "IWM": {
      "first_date": "2000-05-26",
      "last_date": "2026-11-04",
      "row_count": 6650
    },
    "TLT": {
      "first_date": "2002-07-30",
      "last_date": "2026-11-04",
      "row_count": 6107
    },
    "GLD": {
      "first_date": "2004-11-18",
      "last_date": "2026-11-04",
      "row_count": 5525
    },
    "EFA": {
      "first_date": "2001-08-27",
      "last_date": "2026-11-04",
      "row_count": 6335
    },
    "EEM": {
      "first_date": "2003-04-14",
      "last_date": "2026-11-04",
      "row_count": 5929
    }
  },
  "union_index_fingerprint": {
    "first_date": "1993-01-29",
    "last_date": "2026-11-04",
    "count": 8500
  },
  "cache_fingerprint": {
    "per_symbol": {
      "SPY": {
        "rows": 8500,
        "first_date": "1993-01-29",
        "last_date": "2026-11-04",
        "sha256": "7e695da550ce958da253007735f0e973ef7afd44ccf8844dd831a5cbf057ad1a"
      },
      "QQQ": {
        "rows": 6958,
        "first_date": "1999-03-10",
        "last_date": "2026-11-04",
        "sha256": "4bb3b6f2b8a6ae9cce37c8cc1c33cdc8bf51d78c05c14072808f4621ef15d93e"
      },
      "IWM": {
        "rows": 6650,
        "first_date": "2000-05-26",
        "last_date": "2026-11-04",
        "sha256": "9f16d0f9b1a0379b907e7512a56d1406fd1b1e51474834d7335ba137718c3248"
      },
      "TLT": {
        "rows": 6107,
        "first_date": "2002-07-30",
        "last_date": "2026-11-04",
        "sha256": "1ecb72283daee4cbad90f9f0f352ec1a3a6b258131e81111e1e82b4e531d83c8"
      },
      "GLD": {
        "rows": 5525,
        "first_date": "2004-11-18",
        "last_date": "2026-11-04",
        "sha256": "03a498b72d0e539a9da1e2ebb4045456d050d5853408f761872860b14b9a6966"
      },
      "EFA": {
        "rows": 6335,
        "first_date": "2001-08-27",
        "last_date": "2026-11-04",
        "sha256": "a1d87c46db15174d367512e585e2da97882426ee9c8582687c59e3f379ee2b73"
      },
      "EEM": {
        "rows": 5929,
        "first_date": "2003-04-14",
        "last_date": "2026-11-04",
        "sha256": "57e1faec0e1cbd68b2a1a5b406734c138bbc73485a44ee52ed790042df0c49e9"
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
  "paper_sharpe": 0.5643356780383462,
  "paper_max_dd": -0.6224126346564325,
  "rolling_sharpe_63d": -0.6434535005954656,
  "rolling_63d_max_dd": -0.07335686381411866,
  "regime_flips": 6,
  "paper_days": 8500,
  "sharpe_observed_canonical": 0.5643356780383462,
  "sharpe_se": 0.15222637755638702
}
```

## Backtest-baseline scale (cagr_annualized_rf2)

```json
{
  "sharpe_backtest_scale": 0.38284217165710066,
  "psr_target_backtest_scale": 1.4178,
  "baseline_tieback": {
    "recorded_baseline": 1.4178,
    "tolerance": "window/warmup/costs explain deviation (must be quantified)",
    "within_tolerance": false,
    "delta": -1.0349578283428993
  }
}
```

## PSR vs backtest baseline 1.4178

```json
{
  "psr_normal": 1.0320154467313735e-08,
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
    "value": 8500.0,
    "threshold": 126.0,
    "comparison": "gte",
    "pass": true
  },
  "full_period_sharpe": {
    "value": 0.5643356780383462,
    "threshold": 0.9,
    "comparison": "gte",
    "pass": false
  },
  "rolling_63d_sharpe": {
    "value": -0.6434535005954656,
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
    "value": -0.07335686381411866,
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
    "value": 1.0320154467313735e-08,
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
  "required_observed_sharpe_for_psr095": 1.6681901092413074,
  "sharpe_se_at_this_sample": 0.15222637755638702,
  "sample_length": 8500,
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
