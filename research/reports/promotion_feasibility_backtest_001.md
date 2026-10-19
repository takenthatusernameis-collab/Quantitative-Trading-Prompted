# Promotion Criteria Feasibility (Cycle 867)

## Sample definition

```json
{
  "start_date": "2004-11-18",
  "end_date": "2026-10-16",
  "session_count": 8487,
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
    "SPY": "545fc8df7a832f95f7d9631bb1978dfee748f2b1be49c1788baebfa44ecf0188",
    "QQQ": "e0a49f97534e56772ccc063c78cf184abce8a4f6419a953994f60187bd6e6072",
    "IWM": "19943ed1c0601ae126422ae6b16b3f961764155bbb4f2a0ab0f03c8fe13d47d4",
    "TLT": "e2e7888c28c684c2387fc04ebcfb7d910a588a258860cf98e29b98f11a7cad8a",
    "GLD": "55599371df45d59e1d82fcba36fc6995d7eceabf9bda8c73ca3a9723c0b2a080",
    "EFA": "49ccdf05ba7ead3f71ff0f49ad9273513e431fbe7ee36bd7b92547049d5801d6",
    "EEM": "c8839887bcaf3336f8e276e05895dbe3626b4a0c0b69a9e47d385fb1728a476f"
  }
}
```

## Canonical metrics (arithmetic_annualized_rf0)

```json
{
  "paper_sharpe": 0.5646255767978904,
  "paper_max_dd": -0.6224126346564325,
  "rolling_sharpe_63d": 0.30723025922509417,
  "rolling_63d_max_dd": -0.06136072251432145,
  "regime_flips": 6,
  "paper_days": 8487,
  "sharpe_observed_canonical": 0.5646255767978904,
  "sharpe_se": 0.1559096836433908
}
```

## Backtest-baseline scale (cagr_annualized_rf2)

```json
{
  "sharpe_backtest_scale": 0.3831622875894151,
  "psr_target_backtest_scale": 1.4178,
  "baseline_tieback": {
    "recorded_baseline": 1.4178,
    "tolerance": "window/warmup/costs explain deviation (must be quantified)",
    "within_tolerance": false,
    "delta": -1.0346377124105848
  }
}
```

## PSR vs backtest baseline 1.4178

```json
{
  "psr_normal": 2.2219753177036448e-08,
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
    "value": 8487.0,
    "threshold": 126.0,
    "comparison": "gte",
    "pass": true
  },
  "full_period_sharpe": {
    "value": 0.5646255767978904,
    "threshold": 0.9,
    "comparison": "gte",
    "pass": false
  },
  "rolling_63d_sharpe": {
    "value": 0.30723025922509417,
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
    "value": -0.06136072251432145,
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
    "value": 2.2219753177036448e-08,
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
  "required_observed_sharpe_for_psr095": 1.674248608617688,
  "sharpe_se_at_this_sample": 0.1559096836433908,
  "sample_length": 8487,
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
