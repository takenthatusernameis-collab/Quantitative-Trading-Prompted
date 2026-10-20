# Promotion Criteria Feasibility (Cycle 867)

## Sample definition

```json
{
  "start_date": "2004-11-18",
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
  }
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

## Reproduction

```json
{
  "command": "python research/promotion_feasibility_backtest.py",
  "deterministic": true,
  "no_network": true,
  "read_only_data": true
}
```
