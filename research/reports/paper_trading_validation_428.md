# Paper Trading Validation Report — Cycle 428

- **UTC time**: 2026-10-16T00:53:02Z
- **Gate state**: UNMET (2026-10-16T00:53:02Z < 2026-10-18T20:00:00Z). No fetch or replay performed per protocol.
- **Fetch/replay status**: SKIPPED (pre-gate).

## State Snapshot
- Track record: **447 days** (2025-01-02 → 2026-10-14)
- NAV: **$135,043.35** (+35.04%)
- Max drawdown: **-2.93%**
- Sharpe: **1.9272**
- Rolling 63-day Sharpe: **0.1133**
- Regime flips: **6** (risk-on, 132 days)
- Drift flag: `low_rolling_sharpe` persists on 2026-10-12 (0.4892), 2026-10-13 (0.3669), 2026-10-14 (0.1133) — **3 consecutive trading days**. Trajectory over last 18 days volatile (range -0.51 to +1.19). Not yet at the >20-day persistence threshold.

## Verification
- Rolling 63d Sharpe recomputed from last 63 cumulative returns: **0.11333136870186278** vs stored **0.11333136870186329** → diff **5.13e-16** (matches within float precision).
- Regime flips recomputed from run_history: **6** flips over **447** records (matches).
- Supervisor loop tests: `python3 .github/scripts/test_kilo_supervisor_loop.py -v` → **10/10 passed**.

## Artifacts
- `data/processed/paper_trading_state.yaml`
- `research/reports/paper_trading_rolling.md`
- `research/reports/paper_trading_validation_427.md` (prior cycle)

## Next Task
Prepare Cycle 429 with the same post-close gate (2026-10-18T20:00:00Z). If gate met: re-attempt data acquisition (force=True, end_date 2026-11-30) for the 7-ETF incumbent universe + SPY + ^VIX, verify per-symbol max dates, re-run `research/run_paper_trading_replay.py`, confirm track record extension/regime/drift state, write validation report 428.
