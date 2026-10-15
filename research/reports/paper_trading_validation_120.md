# Paper Trading Validation Report — Cycle 120

- **UTC session time**: 2026-10-15T14:15:02Z
- **Post-close gate**: 2026-10-17T20:00:00Z — **NOT MET**
- **Action taken**: No fetch, no replay. Gate enforcement per NEXT_AGENT_TASK.md item 1.

## Verification Results

### 1. Independent rolling-63-day Sharpe
- Computed from `data/processed/paper_trading_state.yaml` last 63 `cumulative_returns`: **0.11333136870186278**
- Stored `drift_flags.low_rolling_sharpe.value`: **0.11333136870186329**
- **Match: PASS** (diff 5.13e-16 < 1e-12)

### 2. Regime flip verification
- Recomputed from `run_history.regime_exposure` transitions: **6 flips** over 447 records
- **Match: PASS**

### 3. Supervisor loop tests
- `python3 .github/scripts/test_kilo_supervisor_loop.py -v` — **10/10 PASSED**

## Track Record (unchanged)

- **Length**: 447 days (2025-01-02 → 2026-10-14)
- **NAV**: $135,043.35 (+35.04%)
- **Max drawdown**: -2.93%
- **Sharpe**: 1.9272
- **Rolling 63d Sharpe**: 0.1133

## Drift Flag

- `low_rolling_sharpe` persists: 2026-10-12 (0.4892), 2026-10-13 (0.3669), 2026-10-14 (0.1133) — **3 consecutive days**
- Trajectory volatile over last 18 days (-0.51 to +1.19); not yet at >20-day persistence threshold
- All primary go/no-go gates still pass (track record 447 > 126, Sharpe 1.93 > 0.9, max DD -2.93% < 15%, 6 regime flips > 1)
- Regime: risk-on (132 days)

## Blocker

- No new real trading day available beyond 2026-10-14 for incumbent ETF universe (SPY, QQQ, IWM, TLT, GLD, EFA, EEM)
- Gate not met; strategy frozen pending post-close window

## Next Task

Preserve gate unchanged for Cycle 121; re-evaluate after 2026-10-17T20:00:00Z.