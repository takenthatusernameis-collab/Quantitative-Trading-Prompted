# Paper Trading Validation Report — Cycle 387

## Timestamp Gate
- Recorded UTC time: `2026-10-15T23:38:43Z`
- Post-close gate: `2026-10-18T20:00:00Z`
- Gate state: **NOT MET** (2026-10-15T23:38:43Z < 2026-10-18T20:00:00Z)
- Action: **No fetch or replay performed** per protocol.

## State Snapshot (unchanged from Cycle 386)
- Track record: **447 days** (2025-01-02 → 2026-10-14)
- NAV: **$135,043.35** (+35.04%)
- Max drawdown: **-2.93%**
- Sharpe: **1.9272**
- Rolling 63-day Sharpe: **0.11333136870186329**
- Regime: risk-on (132 days)
- Run history entries: 447
- Regime flips: 6

## Independent Verification
1. **Rolling 63d Sharpe recomputation**: recomputed 0.11333136870186278 vs stored 0.11333136870186329; diff = 5.134781488891349e-16 < 1e-12 → **match**.
2. **Regime flips recomputation**: 6 flips of 447 run_history entries → **match**.
3. **Supervisor loop tests**: `python3 .github/scripts/test_kilo_supervisor_loop.py -v` → **Ran 10 tests, OK** (10/10 pass).

## Drift Flag Status
- `low_rolling_sharpe` persists: 2026-10-12 (0.4892), 2026-10-13 (0.3669), 2026-10-14 (0.1133) — **3 consecutive trading days**.
- Not yet at the >20-day persistence threshold.
- Trajectory over last 18 days volatile (range -0.51 to +1.19).

## Primary Go/No-Go Gates
- Track record length: 447 > 126 → **PASS**
- Net-of-cost Sharpe: 1.9272 > 0.9 → **PASS**
- Max drawdown: -2.93% < 15% → **PASS**
- Regime flips: 6 > 1 → **PASS**

## Data Freshness
- All 7 incumbent ETF parquet files (SPY, QQQ, IWM, TLT, GLD, EFA, EEM) end at 2026-10-14.
- ^VIX.parquet ends at 2026-10-14 (placeholder row, Volume=0).
- No new real trading day available beyond 2026-10-14 as of this session.

## Artifacts
- `data/processed/paper_trading_state.yaml`
- `research/reports/paper_trading_rolling.md`

## Next Cycle
Re-evaluate after post-close gate (2026-10-18T20:00:00Z). If gate met: re-attempt data acquisition from Yahoo Finance (force=True, end_date 2026-11-30) for the 7-ETF incumbent universe + SPY + ^VIX, verify per-symbol max dates, re-run `research/run_paper_trading_replay.py`, confirm track record extension/regime/drift state, write validation report with results.