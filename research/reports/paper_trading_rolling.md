# Paper-Trading Rolling Report

**Generated:** 2026-11-03 06:59:28 UTC
**Last Run Date:** 2026-11-02
**Days Tracked:** 460

## Current State

| Metric | Value |
|---|---|
| Current NAV | $132,606.80 |
| Peak NAV | $139,120.07 |
| Paper Drawdown | -4.99% |
| Total Return | 32.61% |
| Annualized Return | 16.72% |
| Volatility (ann.) | 9.62% |
| Sharpe Ratio (ann.) | 1.7374 |

## Positions Table

- SPY: 17.2515%
- QQQ: 17.2515%
- IWM: 17.2515%
- EEM: 17.2515%

## Drift Monitoring

- **low_rolling_sharpe**: {'value': -1.3784428809419644, 'threshold': 0.5, 'date': '2026-11-02', 'persistence_days': 4}

## Enhanced Drift Monitoring

- **Rolling 63-day Sharpe:** -1.3784
- **Rolling 63-day Max DD:** -4.99%
- **Regime Persistence:** 145 days in current regime
- **vol_scale range:** [0.437, 1.000]
- **dd_scale range:** [1.000, 1.000]
- **Turnover (median/p95):** 0.14% / 50.00%

## Performance Tracking

- Go/No-Go Status (after 63 days): READY TO EVALUATE
- Target Sharpe: >= 0.9
- Max DD Threshold: <= 15.00%

## Run History (Recent)

- 2026-10-27: NAV=$134,964.32, Ret=0.67%, Turnover=0.55%
- 2026-10-28: NAV=$135,651.64, Ret=0.51%, Turnover=3.76%
- 2026-10-29: NAV=$135,161.06, Ret=-0.36%, Turnover=0.12%
- 2026-10-30: NAV=$133,019.54, Ret=-1.58%, Turnover=3.05%
- 2026-11-02: NAV=$132,606.80, Ret=-0.31%, Turnover=2.84%

## Drift Persistence Provenance

- **git_sha:** 6ddc17850f40c1f9e27d55ce160b3f4641e97173
- **paper_trading_state_sha256:** 43074f0e02629cdc2929c83c536a89be1982e39eb95ebfcb6b39ea7e90bcf41e
- **paper_trading_config_sha256:** 37a2a654c7f6f41924aba13d986d5aa2dd4072770d1142485d76a92c5e92bd8d
