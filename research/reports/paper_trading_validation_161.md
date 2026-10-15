# Paper Trading Validation — Cycle 161

**UTC session time:** 2026-10-15T17:18:42Z
**Post-close gate:** 2026-10-18T20:00:00Z UTC
**Gate result:** NOT MET (17:18:42Z < 20:00:00Z on 2026-10-18) — no fetch/replay performed

## State (from data/processed/paper_trading_state.yaml, as of 2026-10-14)
- Track record: 447 days (2025-01-02 → 2026-10-14)
- NAV: $135,043.35
- Sharpe: 1.9272
- Max DD: -2.93%
- Rolling 63d Sharpe (stored): 0.1133
- Drift flag: persists (3 consecutive days; not yet >20d threshold)
- Regime: risk-on (132 days)
- Regime flips: 6 (447 run_history entries)

## Gate enforcement
- Recorded UTC time via `TZ=UTC date -u +%Y-%m-%dT%H:%M:%SZ`: 2026-10-15T17:18:42Z
- Condition: session_time < 2026-10-18T20:00:00Z is true → did **not** fetch or replay.
- No modifications to `research/run_paper_trading_replay.py` or processed state.

## Independent verifications (3–4)
1. **Rolling 63d Sharpe verification**
   - Computed from last 63 `cumulative_returns`: (mean*252)/(std(ddof=1)*sqrt(252))
   - Computed: 0.11333136870186278; stored: 0.11333136870186329; diff = 5.13e-16 (< 1e-10) ✓

2. **Regime flip verification**
   - Recomputed from `run_history.regime_exposure` transitions: 6 flips across 447 records ✓ (expected 6)

3. **State integrity**
   - `cumulative_returns` = 447, `run_history` = 447, `cumulative_dates` = 447; first date 2025-01-02, last date 2026-10-14; `last_run_date` = 2026-10-14 ✓
   - `current_nav` = 135043.35187742324, `peak_nav` = 139120.07235486925, `max_drawdown` = -0.0293036109631043 ✓

## Supervisor loop tests (5)
- `python3 .github/scripts/test_kilo_supervisor_loop.py -v`: **10/10 passed** ✓

## Outcome
Gate not met. No new data available beyond 2026-10-14. State unchanged. Drift flag persists (3 consecutive days). Next action: re-check at/after 2026-10-18T20:00:00Z UTC.

## Artifacts
- This report: `research/reports/paper_trading_validation_161.md`
- State: `data/processed/paper_trading_state.yaml` (unchanged)