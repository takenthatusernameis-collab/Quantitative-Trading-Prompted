# Paper-Trading Rolling Report

**Generated:** 2026-11-11 22:00:07 UTC
**Last Run Date:** 2026-11-11
**Days Tracked:** 467

## Current State

| Metric | Value |
|---|---|
| Current NAV | $133,688.64 |
| Peak NAV | $139,120.07 |
| Paper Drawdown | -6.56% |
| Total Return | 33.69% |
| Annualized Return | 16.96% |
| Volatility (ann.) | 9.92% |
| Sharpe Ratio (ann.) | 1.7091 |

## Positions Table

- SPY: 12.9237%
- QQQ: 12.9237%
- IWM: 12.9237%
- EEM: 12.9237%

## Drift Monitoring

- **low_rolling_sharpe**: {'value': -1.1048756449232444, 'threshold': 0.5, 'date': '2026-11-11', 'persistence_days': 11}

## Enhanced Drift Monitoring

- **Rolling 63-day Sharpe:** -1.1049
- **Rolling 63-day Max DD:** -6.54%
- **Regime Persistence:** 152 days in current regime
- **vol_scale range:** [0.437, 1.000]
- **dd_scale range:** [1.000, 1.000]
- **Turnover (median/p95):** 0.15% / 50.00%

## Performance Tracking

- Go/No-Go Status (after 63 days): READY TO EVALUATE
- Target Sharpe: >= 0.9
- Max DD Threshold: <= 15.00%

## Run History (Recent)

- 2026-11-05: NAV=$129,990.36, Ret=-2.99%, Turnover=12.08%
- 2026-11-06: NAV=$130,874.77, Ret=0.68%, Turnover=0.65%
- 2026-11-09: NAV=$132,932.13, Ret=1.57%, Turnover=3.05%
- 2026-11-10: NAV=$132,498.03, Ret=-0.33%, Turnover=0.24%
- 2026-11-11: NAV=$133,688.64, Ret=0.90%, Turnover=0.95%

## Drift Persistence Provenance

- **git_sha:** a3ad45f8610f5de8baf99e35fb0a8ccf053ed520
- **paper_trading_state_sha256:** 5fa67d6395eb9948695e89dfa0349bfe51b15c994b6107214cca1fe9a518e227
- **paper_trading_config_sha256:** 37a2a654c7f6f41924aba13d986d5aa2dd4072770d1142485d76a92c5e92bd8d
