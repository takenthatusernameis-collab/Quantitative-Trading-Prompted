# Paper Trading Validation Report — Cycle 158

## Session
- UTC time: 2026-10-15T17:02:49Z
- Gate Check: session_time 2026-10-15T17:02:49Z < gate 2026-10-18T20:00:00Z
- Gate Met: NO — post-close gate not reached (3 days early)
- Prior report from: 2026-10-15T17:00:02Z (Cycle 157)

## Current State
- Last run date: 2026-10-14
- Track record: 447 days (2025-01-02 → 2026-10-14)
- NAV: $135,043.35
- Sharpe: 1.9272
- Max DD: -2.93%
- Rolling 63d Sharpe: 0.1133 (stored)
- Drift flag: persists (3 consecutive days; not yet >20d threshold)
- Regime: risk-on (132 days)
- Regime flips: 6 (from 447 run_history entries)

## Verifications

### 1. Rolling 63-day Sharpe (independent recomputation)
From last 63 cumulative_returns in `data/processed/paper_trading_state.yaml`:
- Computed: 0.11333136870186278
- Stored: 0.11333136870186329
- Difference: 5.13e-16 (matches to float precision)

### 2. Regime flips
- Computed from run_history transitions: 6 flips over 447 entries

### 3. State YAML integrity
- cumulative_returns: 447, run_history: 447, cumulative_dates: 447
- No duplicate dates (447 unique of 447)
- Product of (1+cumulative_returns) = 1.350433518774236 == NAV/100000 = 1.3504335187742325
- NAV match: $135,043.35

### 4. Raw data per-symbol max dates (all 19 parquet files in data/raw/)
| Symbol | Max Date | Rows | Last Volume |
|--------|----------|------|-------------|
| SPY | 2026-10-14 | 447 | 55,376,100 |
| QQQ | 2026-10-14 | 447 | 51,067,700 |
| IWM | 2026-10-14 | 447 | 37,946,800 |
| TLT | 2026-10-14 | 447 | 50,909,600 |
| GLD | 2026-10-14 | 447 | 10,283,300 |
| EFA | 2026-10-14 | 447 | 10,653,000 |
| EEM | 2026-10-14 | 447 | 21,169,200 |
| ^VIX | 2026-10-14 | 449 | 0 (placeholder) |
| DBC | 2026-10-08 | 5,201 | 1,375,600 |
| VNQ | 2026-10-08 | 5,542 | 6,074,200 |
| XLB–XLY (8) | 2026-10-08 | 6,991 each | nonzero |

All 7 incumbent ETF parquet files end at 2026-10-14 with real (nonzero volume) data. No symbol has a 2026-10-15 row. ^VIX ends at 2026-10-14 with Volume=0 (flat placeholder, not used by incumbent). Confirmed: **no new real trading day exists** beyond 2026-10-14.

### 5. Replay script state
- `research/run_paper_trading_replay.py`: end_date = "2026-10-15", replay-date upper bound = "2026-10-14" (yfinance exclusive-end semantics preserved)

### 6. Supervisor loop tests
- `python3 .github/scripts/test_kilo_supervisor_loop.py -v`: 10/10 passed

## Fetch/Replay
- No fetch attempted (gate not met: 2026-10-15T17:02:49Z < 2026-10-18T20:00:00Z)
- No replay run (gate not met)

## Conclusion
Gate condition not satisfied (2026-10-15T17:02:49Z < 2026-10-18T20:00:00Z). No new trading day data fetch or replay performed. All verifications re-run in this session with identical results: rolling-63d Sharpe matched within float precision (diff 5.13e-16), regime flips matched expected count of 6, state YAML integrity confirmed (447 records consistent, NAV consistent with returns product), per-symbol raw data inspection confirms all incumbent ETFs end at 2026-10-14 with real data and no 2026-10-15 row exists for any symbol, supervisor loop tests passed 10/10. Next cycle must check gate again at/after 2026-10-18T20:00:00Z.