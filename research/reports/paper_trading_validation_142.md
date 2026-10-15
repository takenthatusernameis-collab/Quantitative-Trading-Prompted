# Paper Trading Validation Report — Cycle 142

**Cycle**: 142
**Timestamp (UTC)**: 2026-10-15T15:19:53Z
**Gate**: Post-close evaluation gate at 2026-10-17T20:00:00Z

## Gate Status

**NOT MET** — Session time 2026-10-15T15:19:53Z < 2026-10-17T20:00:00Z. No fetch or replay attempted per protocol.

## Track Record (Unchanged)

- **Length**: 447 days (2025-01-02 → 2026-10-14)
- **NAV**: $135,043.35 (+35.04%)
- **Full-period Sharpe**: 1.9272
- **Max Drawdown**: -2.93%
- **Rolling 63-day Sharpe**: 0.1133
- **Regime**: Risk-on (132 days)
- **Regime Flips**: 6 (3 risk-on→risk-off, 3 risk-off→risk-on)

## Drift Monitoring

- `low_rolling_sharpe` flag persists: triggered on 2026-10-12 (0.4892), 2026-10-13 (0.3669), 2026-10-14 (0.1133) — **3 consecutive trading days**
- Trajectory over last 18 days volatile (range -0.51 to +1.19)
- Not yet at >20-day persistence threshold
- All primary go/no-go gates still pass (track record 447 > 126, Sharpe 1.93 > 0.9, max DD -2.93% < 15%, 6 regime flips > 1)

## Independent Verifications

### Rolling 63-day Sharpe Recomputation
- Computed from `data/processed/paper_trading_state.yaml` `cumulative_returns`[-63:]: **0.11333136870186278**
- Stored drift flag value: **0.11333136870186329**
- Difference: **5.13e-16** (within float precision) ✓

### Regime Flip Recomputation
- Recomputed from `run_history.regime_exposure` transitions: **6 flips**
- Run history entries: **447** ✓

## Supervisor Loop Tests

```
python3 .github/scripts/test_kilo_supervisor_loop.py -v
```
**Result**: 10/10 tests passed ✓

## Next Steps

The post-close gate (2026-10-17T20:00:00Z) remains the next opportunity for a new trading day to have published and cleared post-market close. Next cycle (143) will re-evaluate the gate at its session time.

## Artifacts

- `data/processed/paper_trading_state.yaml` (unchanged)
- 447 daily parquet files in `data/processed/`
- `research/reports/paper_trading_rolling.md` (unchanged)