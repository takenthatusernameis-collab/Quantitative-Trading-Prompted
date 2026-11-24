# Paper-Trading Rolling Report

**Generated:** 2026-11-24 00:08:09 UTC
**Last Run Date:** 2026-11-23
**Days Tracked:** 475

## Current State

| Metric | Value |
|---|---|
| Current NAV | $130,307.21 |
| Peak NAV | $139,120.07 |
| Paper Drawdown | -6.56% |
| Total Return | 30.31% |
| Annualized Return | 15.08% |
| Volatility (ann.) | 9.91% |
| Sharpe Ratio (ann.) | 1.5222 |

## Positions Table



## Drift Monitoring

- **low_rolling_sharpe**: {'value': -2.1805161107015505, 'threshold': 0.5, 'date': '2026-11-23', 'persistence_days': 19}
- **regime_persistence_low**: {'value': 4, 'threshold': 5, 'date': '2026-11-23'}

## Enhanced Drift Monitoring

- **Rolling 63-day Sharpe:** -2.1805
- **Rolling 63-day Max DD:** -6.54%
- **Regime Persistence:** 4 days in current regime
- **vol_scale range:** [0.437, 1.000]
- **dd_scale range:** [1.000, 1.000]
- **Turnover (median/p95):** 0.15% / 50.00%

## Performance Tracking

- Go/No-Go Status (after 63 days): READY TO EVALUATE
- Target Sharpe: >= 0.9
- Max DD Threshold: <= 15.00%

## Run History (Recent)

- 2026-11-17: NAV=$130,327.28, Ret=-0.54%, Turnover=0.35%
- 2026-11-18: NAV=$130,307.21, Ret=-0.02%, Turnover=51.32%
- 2026-11-19: NAV=$130,307.21, Ret=0.00%, Turnover=0.00%
- 2026-11-20: NAV=$130,307.21, Ret=0.00%, Turnover=0.00%
- 2026-11-23: NAV=$130,307.21, Ret=0.00%, Turnover=0.00%

## Drift Persistence Provenance

- **git_sha:** c0c90ebcce09040aa5053754291862e9713408a7
- **paper_trading_state_sha256:** f023abb1d1ad98b6df7dadd29f2055fca7bccdceb2c2d350009ae9ce8e74c275
- **paper_trading_config_sha256:** 37a2a654c7f6f41924aba13d986d5aa2dd4072770d1142485d76a92c5e92bd8d
