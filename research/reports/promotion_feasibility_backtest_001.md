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
  "label_end_date": "2026-10-23",
  "realized_start_date": "1993-01-29",
  "realized_end_date": "2026-10-23",
  "realized_session_count": 8492,
  "start_date": "1993-01-29",
  "end_date": "2026-10-23",
  "session_count": 8492,
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
    "SPY": "23a0fb14324c3220ed7d296da09fd417867bf9c6072dd97fce3465303653c641",
    "QQQ": "9533c5c922c4787eb9b83ad8ac56ef358259e0c7e67384dbd29c20b3e1085321",
    "IWM": "3c0e1a712f512ad22d4407ed7b40b987aa8952d4222aa3262dd13410a5663263",
    "TLT": "54070c10163d86b0333e6a815a126c4255b3e1bcb0a6f8dbbc97d632ed65abfa",
    "GLD": "a0f88f7f8c15fecc3931264695bb83bf4a5ebde9f533e123a6a4982339340631",
    "EFA": "9663723537ee21222b67c93dd9c97445e1272f527b47602831aa12117202319d",
    "EEM": "82bbe68da28e67e6c64eceada45df6f573d660d6bc1d81369dafdcdd3c65456b"
  },
  "per_symbol_stats": {
    "SPY": {
      "first_date": "1993-01-29",
      "last_date": "2026-10-23",
      "row_count": 8492
    },
    "QQQ": {
      "first_date": "1999-03-10",
      "last_date": "2026-10-23",
      "row_count": 6950
    },
    "IWM": {
      "first_date": "2000-05-26",
      "last_date": "2026-10-23",
      "row_count": 6642
    },
    "TLT": {
      "first_date": "2002-07-30",
      "last_date": "2026-10-23",
      "row_count": 6099
    },
    "GLD": {
      "first_date": "2004-11-18",
      "last_date": "2026-10-23",
      "row_count": 5517
    },
    "EFA": {
      "first_date": "2001-08-27",
      "last_date": "2026-10-23",
      "row_count": 6327
    },
    "EEM": {
      "first_date": "2003-04-14",
      "last_date": "2026-10-23",
      "row_count": 5921
    }
  },
  "union_index_fingerprint": {
    "first_date": "1993-01-29",
    "last_date": "2026-10-23",
    "count": 8492
  },
  "cache_fingerprint": {
    "per_symbol": {
      "SPY": {
        "rows": 8492,
        "first_date": "1993-01-29",
        "last_date": "2026-10-23",
        "sha256": "23a0fb14324c3220ed7d296da09fd417867bf9c6072dd97fce3465303653c641"
      },
      "QQQ": {
        "rows": 6950,
        "first_date": "1999-03-10",
        "last_date": "2026-10-23",
        "sha256": "9533c5c922c4787eb9b83ad8ac56ef358259e0c7e67384dbd29c20b3e1085321"
      },
      "IWM": {
        "rows": 6642,
        "first_date": "2000-05-26",
        "last_date": "2026-10-23",
        "sha256": "3c0e1a712f512ad22d4407ed7b40b987aa8952d4222aa3262dd13410a5663263"
      },
      "TLT": {
        "rows": 6099,
        "first_date": "2002-07-30",
        "last_date": "2026-10-23",
        "sha256": "54070c10163d86b0333e6a815a126c4255b3e1bcb0a6f8dbbc97d632ed65abfa"
      },
      "GLD": {
        "rows": 5517,
        "first_date": "2004-11-18",
        "last_date": "2026-10-23",
        "sha256": "a0f88f7f8c15fecc3931264695bb83bf4a5ebde9f533e123a6a4982339340631"
      },
      "EFA": {
        "rows": 6327,
        "first_date": "2001-08-27",
        "last_date": "2026-10-23",
        "sha256": "9663723537ee21222b67c93dd9c97445e1272f527b47602831aa12117202319d"
      },
      "EEM": {
        "rows": 5921,
        "first_date": "2003-04-14",
        "last_date": "2026-10-23",
        "sha256": "82bbe68da28e67e6c64eceada45df6f573d660d6bc1d81369dafdcdd3c65456b"
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
  "paper_sharpe": 0.5641515015894989,
  "paper_max_dd": -0.6224126346564325,
  "rolling_sharpe_63d": 0.26155357888397773,
  "rolling_63d_max_dd": -0.0626427965626718,
  "regime_flips": 6,
  "paper_days": 8492,
  "sharpe_observed_canonical": 0.5641515015894989,
  "sharpe_se": 0.15797030655961125
}
```

## Backtest-baseline scale (cagr_annualized_rf2)

```json
{
  "sharpe_backtest_scale": 0.38264283088927753,
  "psr_target_backtest_scale": 1.4178,
  "baseline_tieback": {
    "recorded_baseline": 1.4178,
    "tolerance": "window/warmup/costs explain deviation (must be quantified)",
    "within_tolerance": false,
    "delta": -1.0351571691107224
  }
}
```

## PSR vs backtest baseline 1.4178

```json
{
  "psr_normal": 3.261199104428894e-08,
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
    "value": 8492.0,
    "threshold": 126.0,
    "comparison": "gte",
    "pass": true
  },
  "full_period_sharpe": {
    "value": 0.5641515015894989,
    "threshold": 0.9,
    "comparison": "gte",
    "pass": false
  },
  "rolling_63d_sharpe": {
    "value": 0.26155357888397773,
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
    "value": -0.0626427965626718,
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
    "value": 3.261199104428894e-08,
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
  "required_observed_sharpe_for_psr095": 1.6776380316952124,
  "sharpe_se_at_this_sample": 0.15797030655961125,
  "sample_length": 8492,
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
