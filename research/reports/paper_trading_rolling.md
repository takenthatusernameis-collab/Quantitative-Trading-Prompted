# Paper-Trading Rolling Report

**Generated:** 2026-11-10 22:01:55 UTC
**Last Run Date:** 2026-11-10
**Days Tracked:** 466

## Current State

| Metric | Value |
|---|---|
| Current NAV | $132,498.03 |
| Peak NAV | $139,120.07 |
| Paper Drawdown | -6.56% |
| Total Return | 32.50% |
| Annualized Return | 16.44% |
| Volatility (ann.) | 9.92% |
| Sharpe Ratio (ann.) | 1.6576 |

## Positions Table

- SPY: 13.1618%
- QQQ: 13.1618%
- IWM: 13.1618%
- EEM: 13.1618%

## Drift Monitoring

- **low_rolling_sharpe**: {'value': -1.4394168982987599, 'threshold': 0.5, 'date': '2026-11-10', 'persistence_days': 10}

## Enhanced Drift Monitoring

- **Rolling 63-day Sharpe:** -1.4394
- **Rolling 63-day Max DD:** -6.54%
- **Regime Persistence:** 151 days in current regime
- **vol_scale range:** [0.437, 1.000]
- **dd_scale range:** [1.000, 1.000]
- **Turnover (median/p95):** 0.14% / 50.00%

## Performance Tracking

- Go/No-Go Status (after 63 days): READY TO EVALUATE
- Target Sharpe: >= 0.9
- Max DD Threshold: <= 15.00%

## Run History (Recent)

- 2026-11-04: NAV=$133,995.42, Ret=0.85%, Turnover=0.98%
- 2026-11-05: NAV=$129,990.36, Ret=-2.99%, Turnover=12.08%
- 2026-11-06: NAV=$130,874.77, Ret=0.68%, Turnover=0.65%
- 2026-11-09: NAV=$132,932.13, Ret=1.57%, Turnover=3.05%
- 2026-11-10: NAV=$132,498.03, Ret=-0.33%, Turnover=0.24%

## Drift Persistence Provenance

- **git_sha:** 7b59a7ab20754d10b7d42eae88e74f3058813712
- **paper_trading_state_sha256:** 111b642c4ac5834460c83ac250a0a90ffb75eed308321ad1bb6309a2fc552517
- **paper_trading_config_sha256:** 37a2a654c7f6f41924aba13d986d5aa2dd4072770d1142485d76a92c5e92bd8d
