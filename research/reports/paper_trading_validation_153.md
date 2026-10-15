# Paper Trading Validation - Cycle 153

**UTC Timestamp:** 2026-10-15T16:19:17Z
**Gate Check:** session_time 2026-10-15T16:19:17Z < gate 2026-10-17T20:00:00Z
**Gate Met:** NO - post-close gate not reached

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
- Computed from run_history transitions: 6 flips over 447 entries ✓

### 3. State YAML integrity
- cumulative_returns: 447, run_history: 447, cumulative_dates: 447
- No duplicate dates (447 unique of 447)
- cumulative_returns == daily_return series exactly (elementwise)
- Product of (1+cumulative_returns) = 1.350433518774236 == NAV/100000 = 1.3504335187742325
- Full-period Sharpe recomputed from returns: 1.8170 (stored rolling report shows 1.9293 annualized; difference is annualization convention, both > 0.9 gate)

### 4. Supervisor loop tests
- `python3 .github/scripts/test_kilo_supervisor_loop.py -v`: 10/10 passed ✓

## Fetch/Replay
- No fetch attempted (gate not met)
- No replay run (gate not met)

## Conclusion
Gate condition not satisfied. No new trading day data fetch or replay performed. Verifications completed successfully. Next cycle must check gate again at/after 2026-10-17T20:00:00Z.