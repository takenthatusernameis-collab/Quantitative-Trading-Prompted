# CSMomentum Common-Inception Audit (Cycle 905)

Read-only sample measurement for `csmomentum_001`. The common inception is
re-derived from the raw cache on every run; no date in the policy is trusted.
No backtest is executed here and no gate, threshold, universe, cost model or
Sharpe convention is changed.

- common inception: **2006-02-06** (re-derived; max of per-symbol first dates)
- union sample: 1993-01-29 .. 2026-10-21, 8490 sessions, price width 1..18 of 18
- common-inception slice: 2006-02-06 .. 2026-10-21, 5210 sessions, price width 18..18 of 18
- slice warm-up ramp: 273 flat sessions before the first selectable asset (2007-03-09), first selectable asset in the warm-up-preserving window: 2006-02-06

```json
{
  "candidate": "csmomentum_001",
  "artifact": "common-inception sample-definition audit (measurement only, no backtest)",
  "policy": {
    "path": "config/sample_policy.yaml",
    "rule_id": "common_inception_fully_populated",
    "evaluation_sample": "common_inception_slice",
    "publish_alongside": [
      "common_inception_window",
      "union_sample"
    ],
    "derivation_rule": "common_inception = max of per-symbol first dates in the raw cache (re-derived from data/raw at measurement time; never a frozen date)",
    "evidence_note": "The csmomentum_001 long sample is ragged (common inception 2006-02-06); sample-definition control must be pre-registered before execution.",
    "conditions_for_revisit": [
      "change of universe",
      "change of the engine's window semantics",
      "a new asset in the universe"
    ]
  },
  "candidate_configuration": {
    "signal_type": "csmomentum",
    "lookback": 252,
    "skip": 21,
    "top_fraction": 0.5,
    "rebalance_freq": "monthly",
    "cost_model": {
      "commission_bps": 1.0,
      "slippage_bps": 2.0,
      "total_round_trip_bps": 3.0
    },
    "execution": {
      "signal_lag_days": 1,
      "price_field": "Close",
      "timezone": "UTC",
      "rebalance_schedule": "monthly"
    },
    "universe_size": 18
  },
  "common_inception": "2006-02-06",
  "samples": {
    "union_sample": {
      "start": "1993-01-29",
      "end": "2026-10-21",
      "sessions": 8490,
      "price_width_min": 1,
      "price_width_median": 18.0,
      "price_width_max": 18,
      "price_width_changes": [
        {
          "date": "1998-12-22",
          "assets_with_price": 10
        },
        {
          "date": "1999-03-10",
          "assets_with_price": 11
        },
        {
          "date": "2000-05-26",
          "assets_with_price": 12
        },
        {
          "date": "2001-08-27",
          "assets_with_price": 13
        },
        {
          "date": "2002-07-30",
          "assets_with_price": 14
        },
        {
          "date": "2003-04-14",
          "assets_with_price": 15
        },
        {
          "date": "2004-09-29",
          "assets_with_price": 16
        },
        {
          "date": "2004-11-18",
          "assets_with_price": 17
        },
        {
          "date": "2006-02-06",
          "assets_with_price": 18
        }
      ],
      "momentum_breadth": {
        "sessions": 8490,
        "opening_breadth": 0,
        "breadth_min": 0,
        "breadth_median": 18.0,
        "breadth_max": 18,
        "sessions_with_zero_selectable_assets": 273,
        "sessions_with_fewer_than_five_selectable_assets": 1763,
        "first_session_with_a_selectable_asset": "1994-02-28",
        "flat_sessions_before_the_first_signal": 273
      }
    },
    "common_inception_slice": {
      "start": "2006-02-06",
      "end": "2026-10-21",
      "sessions": 5210,
      "price_width_min": 18,
      "price_width_median": 18.0,
      "price_width_max": 18,
      "price_width_changes": [],
      "fully_populated": true,
      "momentum_breadth": {
        "sessions": 5210,
        "opening_breadth": 0,
        "breadth_min": 0,
        "breadth_median": 18.0,
        "breadth_max": 18,
        "sessions_with_zero_selectable_assets": 273,
        "sessions_with_fewer_than_five_selectable_assets": 273,
        "first_session_with_a_selectable_asset": "2007-03-09",
        "flat_sessions_before_the_first_signal": 273
      }
    },
    "common_inception_window": {
      "start": "2006-02-06",
      "end": "2026-10-21",
      "sessions": 5210,
      "note": "warm-up preserved: the union price frame is kept, only the evaluation window is truncated",
      "price_width_min": 18,
      "price_width_max": 18,
      "momentum_breadth": {
        "sessions": 5210,
        "opening_breadth": 17,
        "breadth_min": 17,
        "breadth_median": 18.0,
        "breadth_max": 18,
        "sessions_with_zero_selectable_assets": 0,
        "sessions_with_fewer_than_five_selectable_assets": 0,
        "first_session_with_a_selectable_asset": "2006-02-06",
        "flat_sessions_before_the_first_signal": 0
      }
    }
  },
  "raggedness": {
    "union_price_width_changes": [
      {
        "date": "1998-12-22",
        "assets_with_price": 10
      },
      {
        "date": "1999-03-10",
        "assets_with_price": 11
      },
      {
        "date": "2000-05-26",
        "assets_with_price": 12
      },
      {
        "date": "2001-08-27",
        "assets_with_price": 13
      },
      {
        "date": "2002-07-30",
        "assets_with_price": 14
      },
      {
        "date": "2003-04-14",
        "assets_with_price": 15
      },
      {
        "date": "2004-09-29",
        "assets_with_price": 16
      },
      {
        "date": "2004-11-18",
        "assets_with_price": 17
      },
      {
        "date": "2006-02-06",
        "assets_with_price": 18
      }
    ],
    "sessions_with_fewer_than_N_assets_union": 3280,
    "sessions_with_fewer_than_N_assets_common_inception": 0,
    "selectable_breadth_threshold": 5
  },
  "raw_cache_fingerprint": {
    "per_symbol": {
      "SPY": {
        "first_date": "1993-01-29",
        "last_date": "2026-10-19",
        "row_count": 8488,
        "sha256": "971d02284b9790dfd282438b98f5a0c08cc409e379d1598a41c02d96eb00f47e"
      },
      "QQQ": {
        "first_date": "1999-03-10",
        "last_date": "2026-10-19",
        "row_count": 6946,
        "sha256": "71215972c77f917d54da229ee445c16edc4f51fd997f878a2ae3888855fb08ad"
      },
      "IWM": {
        "first_date": "2000-05-26",
        "last_date": "2026-10-19",
        "row_count": 6638,
        "sha256": "5bd3985f67dd47ad1ae75d1c23b7effa4d3bc7abd730cf7ac8c5c99887d91593"
      },
      "TLT": {
        "first_date": "2002-07-30",
        "last_date": "2026-10-19",
        "row_count": 6095,
        "sha256": "f745d0921006c792dd1ad180cefea529bf049cda24e4dc9fc0a378208a8c36e7"
      },
      "GLD": {
        "first_date": "2004-11-18",
        "last_date": "2026-10-21",
        "row_count": 5515,
        "sha256": "a50a33932759e90a5fb105cce54d02ecc387de198a33c6f7783c50d59d883057"
      },
      "DBC": {
        "first_date": "2006-02-06",
        "last_date": "2026-10-21",
        "row_count": 5210,
        "sha256": "a04e11a54bb3710f2e97600d093fc7f647ed6d448399e8a4412b3c8837aeeaf4"
      },
      "VNQ": {
        "first_date": "2004-09-29",
        "last_date": "2026-10-08",
        "row_count": 5542,
        "sha256": "8714f6b1bf45d1b01f6c83f635b689d54b37c5cb38a6e6e8a316117e4f9169ec"
      },
      "EFA": {
        "first_date": "2001-08-27",
        "last_date": "2026-10-19",
        "row_count": 6323,
        "sha256": "a77623de41bdf6d5c48810c54079dbaa15181a30113b1b317e67630851592f8b"
      },
      "EEM": {
        "first_date": "2003-04-14",
        "last_date": "2026-10-19",
        "row_count": 5917,
        "sha256": "922f0181be3ed98ca4ad1ab844ed87dbda9afa562b44bde20b4dbf730f6693c8"
      },
      "XLB": {
        "first_date": "1998-12-22",
        "last_date": "2026-10-08",
        "row_count": 6991,
        "sha256": "465b9a7b6c7848690c347eb3a9229e133b01ebf638642e12c6c75070e14cee12"
      },
      "XLE": {
        "first_date": "1998-12-22",
        "last_date": "2026-10-08",
        "row_count": 6991,
        "sha256": "408b2806f7dbde65bdf3a8e0cd5673406945a791f77b5e44683cf855e08d2ff6"
      },
      "XLF": {
        "first_date": "1998-12-22",
        "last_date": "2026-10-08",
        "row_count": 6991,
        "sha256": "2f8eeb83b2024b693fc55c1dba57f23e02932af7c4bc2216ad714fc2539d8891"
      },
      "XLI": {
        "first_date": "1998-12-22",
        "last_date": "2026-10-08",
        "row_count": 6991,
        "sha256": "176eaa15a62526ec729dbcb5a8ceac50510b0566e87f7ac1b155cfa39f06c480"
      },
      "XLK": {
        "first_date": "1998-12-22",
        "last_date": "2026-10-08",
        "row_count": 6991,
        "sha256": "b66776c5c1c70885794c0c912bad0bff8cebe775d978b113af9bc5c2561ca6ad"
      },
      "XLP": {
        "first_date": "1998-12-22",
        "last_date": "2026-10-08",
        "row_count": 6991,
        "sha256": "d1ac5528a51c54708fc60feff3c9553d60c863dbdab7d177519bb000e38d7211"
      },
      "XLU": {
        "first_date": "1998-12-22",
        "last_date": "2026-10-08",
        "row_count": 6991,
        "sha256": "c9550ef0e461368e96c4321b320926d397f066281210d8cd4f60b08a56a0cd76"
      },
      "XLV": {
        "first_date": "1998-12-22",
        "last_date": "2026-10-08",
        "row_count": 6991,
        "sha256": "bcf7029ba61bac58eb747d8edc6fef907a35e31f91ab246a6c845433ccf86bab"
      },
      "XLY": {
        "first_date": "1998-12-22",
        "last_date": "2026-10-08",
        "row_count": 6991,
        "sha256": "7a64cd50a03d5d70d29418908a1271a9df47bfda1e50da9def5d868908ff4ab6"
      }
    }
  },
  "checks": [
    {
      "name": "policy_universe_matches_candidate_config",
      "expected": 18,
      "observed": 18,
      "pass": true
    },
    {
      "name": "common_inception_rederived_from_raw_cache",
      "expected": "max of per-symbol first dates in data/raw",
      "observed": "2006-02-06",
      "pass": true
    },
    {
      "name": "union_sample_is_ragged",
      "expected": "< 18",
      "observed": 1,
      "pass": true
    },
    {
      "name": "common_inception_after_union_start",
      "expected": ">= 1993-01-29",
      "observed": "2006-02-06",
      "pass": true
    },
    {
      "name": "common_inception_sample_is_nonempty",
      "expected": "> 0 sessions",
      "observed": 5210,
      "pass": true
    },
    {
      "name": "common_inception_fully_populated",
      "expected": 18,
      "observed": 18,
      "pass": true
    },
    {
      "name": "aligned_index_matches_raw_cache_union",
      "expected": 8490,
      "observed": 8490,
      "pass": true
    },
    {
      "name": "slice_warmup_ramp_matches_lookback_plus_skip",
      "expected": 273,
      "observed": 273,
      "pass": true
    },
    {
      "name": "window_variant_preserves_warmup",
      "expected": "window opening breadth > slice opening breadth (warm-up preserved)",
      "observed": {
        "slice_opening_breadth": 0,
        "window_opening_breadth": 17
      },
      "pass": true
    },
    {
      "name": "common_inception_sample_is_a_subset_of_the_union_sample",
      "expected": "subset of 8490 union sessions",
      "observed": 5210,
      "pass": true
    },
    {
      "name": "common_inception_sample_ends_with_the_union_sample",
      "expected": "2026-10-21",
      "observed": "2026-10-21",
      "pass": true
    },
    {
      "name": "data_and_config_unchanged",
      "expected": {
        "data": true,
        "config": true
      },
      "observed": {
        "data": true,
        "config": true
      },
      "pass": true
    }
  ],
  "overall": "PASS"
}
```
