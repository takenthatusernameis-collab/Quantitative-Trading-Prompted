# Paper Trading Validation Report — Cycle 94

## Timestamp Gate

- Session time (UTC): **2026-10-15T11:42:34Z**
- Post-close gate: **2026-10-17T20:00:00Z**
- Gate status: **NOT MET** (session time < gate)
- Action: **No fetch attempted** per protocol.

## Track Record (unchanged)

| Metric | Value |
|---|---|
| Track record length | 447 days (2025-01-02 → 2026-10-14) |
| NAV | $135,043.35 |
| Net return | +35.04% |
| Sharpe | 1.9272 |
| Max drawdown | -2.93% |
| Rolling 63-day Sharpe | 0.1133 |
| Regime flips | 6 |
| Regime | risk-on (132 days) |

## Independent Verification

### 1. Rolling 63-day Sharpe
- Recomputed from `data/processed/paper_trading_state.yaml` `cumulative_returns` (last 63) via `(mean*252)/(std(ddof=1)*sqrt(252))`
- Recomputed value: **0.11333136870186278**
- Stored value: **0.11333136870186329**
- Difference: ~5e-16 → **MATCH**

### 2. Regime Flips
- Recomputed from `run_history` `regime_exposure` transitions
- Recomputed value: **6**
- Stored value: **6** → **MATCH**
- `run_history` length: 447; `last_run_date`: 2026-10-14

### 3. Supervisor Loop Tests
- Command: `python3 .github/scripts/test_kilo_supervisor_loop.py -v`
- Result: **10/10 PASSED**

## Drift Flag Status

- `low_rolling_sharpe` persists on 2026-10-12 (0.4892), 2026-10-13 (0.3669), 2026-10-14 (0.1133) — **3 consecutive trading days**
- Trajectory over last 18 days volatile (range -0.51 to +1.19)
- Not yet at the >20-day persistence threshold
- All primary go/no-go gates still pass (track record 447 > 126, Sharpe 1.93 > 0.9, max DD -2.93% < 15%, 6 regime flips > 1)

## Blocker

- No new real trading day available for incumbent ETF universe beyond 2026-10-14
- Next fetch attempt gated behind 2026-10-17T20:00:00Z post-close window

## Artifacts

- `data/processed/paper_trading_state.yaml`
- `research/reports/paper_trading_validation_094.md` (this report)