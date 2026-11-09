# Paper-Trading Rolling Report

**Generated:** 2026-11-06 22:01:17 UTC
**Last Run Date:** 2026-11-06
**Days Tracked:** 464

## Current State

| Metric | Value |
|---|---|
| Current NAV | $130,874.77 |
| Peak NAV | $139,120.07 |
| Paper Drawdown | -6.56% |
| Total Return | 30.87% |
| Annualized Return | 15.74% |
| Volatility (ann.) | 9.87% |
| Sharpe Ratio (ann.) | 1.5941 |

## Positions Table

- SPY: 13.8643%
- QQQ: 13.8643%
- IWM: 13.8643%
- EEM: 13.8643%

## Drift Monitoring

- **low_rolling_sharpe**: {'value': -1.8144217837687115, 'threshold': 0.5, 'date': '2026-11-06', 'persistence_days': 8}

## Enhanced Drift Monitoring

- **Rolling 63-day Sharpe:** -1.8144
- **Rolling 63-day Max DD:** -6.54%
- **Regime Persistence:** 149 days in current regime
- **vol_scale range:** [0.437, 1.000]
- **dd_scale range:** [1.000, 1.000]
- **Turnover (median/p95):** 0.14% / 50.00%

## Performance Tracking

- Go/No-Go Status (after 63 days): READY TO EVALUATE
- Target Sharpe: >= 0.9
- Max DD Threshold: <= 15.00%

## Run History (Recent)

- 2026-11-02: NAV=$132,606.80, Ret=-0.31%, Turnover=2.84%
- 2026-11-03: NAV=$132,866.04, Ret=0.20%, Turnover=0.16%
- 2026-11-04: NAV=$133,995.42, Ret=0.85%, Turnover=0.98%
- 2026-11-05: NAV=$129,990.36, Ret=-2.99%, Turnover=12.08%
- 2026-11-06: NAV=$130,874.77, Ret=0.68%, Turnover=0.65%

## Drift Persistence Provenance

- **git_sha:** 880e4a22816a3896218671aa539182ca945af828
- **paper_trading_state_sha256:** a8bb945ca24fb79133f75de9ba4e31b0205cafb50e9d71d6aa1eb451f4cd35b4
- **paper_trading_config_sha256:** 37a2a654c7f6f41924aba13d986d5aa2dd4072770d1142485d76a92c5e92bd8d
