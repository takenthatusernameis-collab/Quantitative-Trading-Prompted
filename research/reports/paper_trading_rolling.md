# Paper-Trading Rolling Report

**Generated:** 2026-11-19 22:00:36 UTC
**Last Run Date:** 2026-11-19
**Days Tracked:** 473

## Current State

| Metric | Value |
|---|---|
| Current NAV | $130,307.21 |
| Peak NAV | $139,120.07 |
| Paper Drawdown | -6.56% |
| Total Return | 30.31% |
| Annualized Return | 15.15% |
| Volatility (ann.) | 9.93% |
| Sharpe Ratio (ann.) | 1.5259 |

## Positions Table



## Drift Monitoring

- **low_rolling_sharpe**: {'value': -2.141568617178681, 'threshold': 0.5, 'date': '2026-11-19', 'persistence_days': 17}
- **regime_persistence_low**: {'value': 2, 'threshold': 5, 'date': '2026-11-19'}

## Enhanced Drift Monitoring

- **Rolling 63-day Sharpe:** -2.1416
- **Rolling 63-day Max DD:** -6.54%
- **Regime Persistence:** 2 days in current regime
- **vol_scale range:** [0.437, 1.000]
- **dd_scale range:** [1.000, 1.000]
- **Turnover (median/p95):** 0.15% / 50.00%

## Performance Tracking

- Go/No-Go Status (after 63 days): READY TO EVALUATE
- Target Sharpe: >= 0.9
- Max DD Threshold: <= 15.00%

## Run History (Recent)

- 2026-11-13: NAV=$132,654.46, Ret=-0.29%, Turnover=0.01%
- 2026-11-16: NAV=$131,036.61, Ret=-1.22%, Turnover=0.55%
- 2026-11-17: NAV=$130,327.28, Ret=-0.54%, Turnover=0.35%
- 2026-11-18: NAV=$130,307.21, Ret=-0.02%, Turnover=51.32%
- 2026-11-19: NAV=$130,307.21, Ret=0.00%, Turnover=0.00%

## Drift Persistence Provenance

- **git_sha:** c3abaa68a529d0ca7ac7d83c3c3ad4869cf6198a
- **paper_trading_state_sha256:** 743c6e419f1e28a05a76272c63909161679178be3bf805f8cbf289e11c6b33ab
- **paper_trading_config_sha256:** 37a2a654c7f6f41924aba13d986d5aa2dd4072770d1142485d76a92c5e92bd8d
