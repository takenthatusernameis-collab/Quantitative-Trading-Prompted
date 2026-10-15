# Paper Trading Validation Report — Cycle 154

## Session
- UTC time: 2026-10-15T16:27:27Z
- Gate: 2026-10-17T20:00:00Z
- Gate met: false
- Track record: 447 days (2025-01-02 → 2026-10-14)
- NAV: $135,043.35
- Sharpe: 1.9272
- Max drawdown: -2.93%
- Rolling 63d Sharpe (stored): 0.11333136870186329
- Regime: risk-on (132 days)
- Drift flag: persists (3 consecutive days, < 20d threshold)

## Post-Close Gate Enforcement
- session_time (UTC): 2026-10-15T16:27:27Z < gate 2026-10-17T20:00:00Z
- Action: No fetch_universe call. No replay modification/run.
- Blocker: Post-close gate not reached; wait for next session at/after 2026-10-17T20:00:00Z.

## Independent Verifications

### 1. Rolling 63-day Sharpe (independent recomputation)
From last 63 cumulative_returns in `data/processed/paper_trading_state.yaml`:
- Computed: 0.11333136870186278
- Stored: 0.11333136870186329
- Difference: 5.13e-16 (within float precision) ✓

### 2. Regime flips
- Computed from run_history.regime_exposure transitions: 6 flips over 447 entries ✓

### 3. State YAML integrity
- cumulative_returns: 447
- cumulative_dates: 447
- run_history: 447
- No duplicate dates (447 unique of 447) ✓
- cumulative_returns == daily_return series exactly (elementwise) ✓
- Product of (1+cumulative_returns) × 100000 = 135043.3518774236 ≈ current_nav 135043.35187742324 ✓

### 4. Supervisor loop tests
- Command: `python3 .github/scripts/test_kilo_supervisor_loop.py -v`
- Result: 10/10 passed ✓

## Fetch/Replay
- No fetch attempted (gate not met)
- No replay run (gate not met)

## Conclusion
Gate condition not satisfied (2026-10-15T16:27:27Z < 2026-10-17T20:00:00Z). No new data fetched or replay executed. All verifications passed: rolling-63d Sharpe matched within float precision, regime flips matched expected count of 6, state YAML integrity confirmed (447 records consistent, NAV consistent with returns product), supervisor loop tests passed 10/10. Task remains bounded and restart-safe. Next cycle must check gate at/after 2026-10-17T20:00:00Z.
