# Paper-Trading Rolling Report

**Generated:** 2026-11-03 22:00:15 UTC
**Last Run Date:** 2026-11-03
**Days Tracked:** 461

## Current State

| Metric | Value |
|---|---|
| Current NAV | $132,866.04 |
| Peak NAV | $139,120.07 |
| Paper Drawdown | -4.99% |
| Total Return | 32.87% |
| Annualized Return | 16.81% |
| Volatility (ann.) | 9.61% |
| Sharpe Ratio (ann.) | 1.7480 |

## Positions Table

- SPY: 17.2925%
- QQQ: 17.2925%
- IWM: 17.2925%
- EEM: 17.2925%

## Drift Monitoring

- **low_rolling_sharpe**: {'value': -1.399698929897785, 'threshold': 0.5, 'date': '2026-11-03', 'persistence_days': 5}

## Enhanced Drift Monitoring

- **Rolling 63-day Sharpe:** -1.3997
- **Rolling 63-day Max DD:** -4.99%
- **Regime Persistence:** 146 days in current regime
- **vol_scale range:** [0.437, 1.000]
- **dd_scale range:** [1.000, 1.000]
- **Turnover (median/p95):** 0.14% / 50.00%

## Performance Tracking

- Go/No-Go Status (after 63 days): READY TO EVALUATE
- Target Sharpe: >= 0.9
- Max DD Threshold: <= 15.00%

## Run History (Recent)

- 2026-10-28: NAV=$135,651.64, Ret=0.51%, Turnover=3.76%
- 2026-10-29: NAV=$135,161.06, Ret=-0.36%, Turnover=0.12%
- 2026-10-30: NAV=$133,019.54, Ret=-1.58%, Turnover=3.05%
- 2026-11-02: NAV=$132,606.80, Ret=-0.31%, Turnover=2.84%
- 2026-11-03: NAV=$132,866.04, Ret=0.20%, Turnover=0.16%

## Drift Persistence Provenance

- **git_sha:** d665d4984a3c99e1b8aa51ead6536431bf47c974
- **paper_trading_state_sha256:** 6f7b94ba81c802ee605c1fea7f257a19e52cd5c07ae87b06961d880de63d2886
- **paper_trading_config_sha256:** 37a2a654c7f6f41924aba13d986d5aa2dd4072770d1142485d76a92c5e92bd8d
