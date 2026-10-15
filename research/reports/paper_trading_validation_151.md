# Paper Trading Validation Report — Cycle 151

## Session Timestamp
- Session time (UTC): **2026-10-15T15:51:33Z**
- Post-close gate: **2026-10-17T20:00:00Z**
- Gate result: **NOT MET** (session_time < gate)

## Gate Enforcement
Per protocol, because `session_time < 2026-10-17T20:00:00Z`, **no data fetch and no replay were performed**. The post-close gate is the first opportunity for a new trading day to have published and cleared post-market close on the US equity calendar. Fetching before the gate would risk ingesting incomplete/intraday rows.

## Track Record (unchanged, from Cycle 150)
- Days: **447** (2025-01-02 → 2026-10-14)
- NAV: **$135,043.35**
- Sharpe: **1.9272**
- Max drawdown: **-2.93%**
- Rolling 63-day Sharpe: **0.1133**
- Regime: risk-on (132 days)
- Drift flag: `low_rolling_sharpe` persists — 3 consecutive trading days (2026-10-12: 0.4892, 2026-10-13: 0.3669, 2026-10-14: 0.1133). Not yet at the >20-day persistence threshold.

## Verification 1 — Independent Rolling 63-Day Sharpe
Computed from `data/processed/paper_trading_state.yaml`, last 63 `cumulative_returns`:
`(mean*252)/(std(ddof=1)*sqrt(252))`

- Recomputed: **0.11333136870186278**
- Stored `drift_flags.low_rolling_sharpe.value`: **0.11333136870186329**
- Absolute difference: **5.13e-16** (float precision) — **MATCH**
- Number of cumulative_returns: **447**

## Verification 2 — Regime Flip Count
Recomputed from `run_history.regime_exposure` transitions:
- Regime flips: **6**
- run_history length: **447**
- Expected (no replay extension): **6** — **MATCH**

## Verification 3 — Supervisor Loop Tests
Command: `python3 .github/scripts/test_kilo_supervisor_loop.py -v`

- Tests run: **10**
- Tests passed: **10/10**
- Result: **OK**

## Data Status
- No fetch attempted (gate not met).
- Per-symbol max dates unchanged from Cycle 150: all 7 incumbent ETF parquet files (SPY, QQQ, IWM, TLT, GLD, EFA, EEM) end at **2026-10-14**; `^VIX.parquet` ends at 2026-10-14 with placeholder row (Volume=0).
- No new real trading day exists beyond 2026-10-14 in the cached raw data.

## Artifacts
- `data/processed/paper_trading_state.yaml` (447 run_history records)
- `research/reports/paper_trading_validation_151.md` (this report)
- `research/reports/paper_trading_rolling.md`

## Next Task
Post-close gate unchanged at **2026-10-17T20:00:00Z**. Next cycle re-evaluates the gate; if met, attempts the post-close fetch for the 8-symbol universe and extends the replay if a new real trading day exists.

## Decision Label
**Blocked by timing gate** — not a research failure. Track record, verifications, and tests all reproduced exactly.