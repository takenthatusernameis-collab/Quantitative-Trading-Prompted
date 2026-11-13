# Paper-Trading Rolling Report

**Generated:** 2026-11-13 22:00:07 UTC
**Last Run Date:** 2026-11-13
**Days Tracked:** 469

## Current State

| Metric | Value |
|---|---|
| Current NAV | $132,654.46 |
| Peak NAV | $139,120.07 |
| Paper Drawdown | -6.56% |
| Total Return | 32.65% |
| Annualized Return | 16.40% |
| Volatility (ann.) | 9.91% |
| Sharpe Ratio (ann.) | 1.6538 |

## Positions Table

- SPY: 12.8801%
- QQQ: 12.8801%
- IWM: 12.8801%
- EEM: 12.8801%

## Drift Monitoring

- **low_rolling_sharpe**: {'value': -1.4832687549946837, 'threshold': 0.5, 'date': '2026-11-13', 'persistence_days': 13}

## Enhanced Drift Monitoring

- **Rolling 63-day Sharpe:** -1.4833
- **Rolling 63-day Max DD:** -6.54%
- **Regime Persistence:** 154 days in current regime
- **vol_scale range:** [0.437, 1.000]
- **dd_scale range:** [1.000, 1.000]
- **Turnover (median/p95):** 0.15% / 50.00%

## Performance Tracking

- Go/No-Go Status (after 63 days): READY TO EVALUATE
- Target Sharpe: >= 0.9
- Max DD Threshold: <= 15.00%

## Run History (Recent)

- 2026-11-09: NAV=$132,932.13, Ret=1.57%, Turnover=3.05%
- 2026-11-10: NAV=$132,498.03, Ret=-0.33%, Turnover=0.24%
- 2026-11-11: NAV=$133,688.64, Ret=0.90%, Turnover=0.95%
- 2026-11-12: NAV=$133,039.93, Ret=-0.49%, Turnover=0.18%
- 2026-11-13: NAV=$132,654.46, Ret=-0.29%, Turnover=0.01%

## Drift Persistence Provenance

- **git_sha:** 99a822ee2ee073d84fdd5d81d1a48ed96b82e11a
- **paper_trading_state_sha256:** c438cd71785459e2612e2dda3425d670de920a62de532c0dff2da6fe332b6365
- **paper_trading_config_sha256:** 37a2a654c7f6f41924aba13d986d5aa2dd4072770d1142485d76a92c5e92bd8d
