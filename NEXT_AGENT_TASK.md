# Next Agent Task: Cycle 20 — Evidence-Based Shortlist Refresh & Incumbent Paper-Trading Validation Extension

## Context

Cycle 19 executed the pre-registered C5 evaluation (macroregime_001, VIX regime overlay
on the SPY-trend-filtered TSMOM incumbent). Results:

- Baseline test Sharpe 0.2950 (rank 7/12); VIX-gate plateau 4/4 PASS
- Walk-forward mean OOS Sharpe **0.4331** (75% positive folds, 137 pooled trades)
- Benchmark (incumbent control arm, vix_exposure=1.0): test Sharpe 0.3241, WF 0.4628
- 1/N 7-ETF: test Sharpe 0.4716
- DSR -0.5061 (p=0.3064) at N=12; PSR vs 0.9 gate 0.0255
- **Rejected/Failed** — pre-registered falsification condition met (WF mean OOS Sharpe
  0.4331 < 0.9). The VIX gate underperformed the incumbent control arm on both test
  and walk-forward periods, consistent with the pre-registered prior that an
  overlay-on-overlay of an already-gated candidate has low probability of raising
  the OOS Sharpe.

Per the pre-registered post-gate guidance in `research/hypotheses/macroregime_001.md`
(section "Decision Discipline"):

> If C5 is rejected, the next cycle moves to the next untested shortlist candidate;
> per the Cycle 11 shortlist, all remaining candidates C7–C10 are blocked by data
> and C2 is rejected, so the shortlist is exhausted and the next cycle should
> either (a) extend the incumbent's prospective paper-trading validation (gate:
> 63 days of track record), or (b) document a new evidence-based shortlist per
> AGENTS.md Market Opportunity Search.

## Shortlist Status (Post-Cycle 19)

| Candidate | Score | Verdict | Status |
|-----------|-------|---------|--------|
| C1 TSMOM incumbent | 32/35 | Credible candidate | In paper-trading validation (gate: 63 days) |
| C2 TSMOM parameter variants | 25/35 | Rejected | Tested worse; archived |
| C3 Cross-sectional momentum (18-ETF) | 29/35 | Rejected/Failed | Valid test, archived |
| C4 Sector rotation (9 sector ETFs) | 28/35 | Rejected/Failed | Valid test, archived |
| C5 Macro regime overlay | 24/35 | Rejected/Failed | Valid test, archived |
| C6 Calendar/rebalancing effects | 26/35 | Rejected/Failed | Valid test, archived |
| C7 Volatility risk premium | 18/35 | Blocked by data | ^VIX index only, no tradeable instrument |
| C8 Crypto perpetual funding carry | 20/35 | Blocked by data | ~66 days history, single exchange, no diversification |
| C9 Futures basis & roll yield | 21/35 | Blocked by data | No futures/spot data cached |
| C10 Intraday session effects | 17/35 | Rejected | No intraday history |

**All 10 shortlist candidates are resolved**: 1 credible (C1, in validation),
4 rejected/failed (C2–C6), 4 blocked by data (C7–C10), 1 rejected (C10).

## Objective

Choose ONE bounded, evidence-based action from the two pre-registered options:

### Option A (recommended): Extend incumbent paper-trading validation

The incumbent (tsmomentum_spytrend_001) is the only **Credible candidate** remaining.
It was promoted through the full validation funnel (Cycle 6 walk-forward: mean OOS
Sharpe 0.9473, 48 folds; Cycle 7 test: Sharpe 1.4178). The next step per AGENTS.md
is prospective paper-trading to verify live-execution fidelity (slippage, latency,
real-time regime behavior).

**Action**: Inspect the paper-trading engine state, compute the current track-record
length, and extend the paper-trading validation period if the 63-day minimum gate
has not yet been reached. Document the prospective track record with daily P&L,
position turnover, and realized vs. backtested slippage.

**Evidence artifacts to inspect**:
- `data/processed/paper_trading/` (daily state snapshots)
- `data/processed/paper_trading_state.yaml` (engine state)
- `research/reports/paper_trading_rolling.md` (rolling validation report)
- `src/paper_trading/` (engine source, if present)

### Option B (alternative): Document a new evidence-based shortlist

If the paper-trading engine is unavailable or the track-record gate cannot be
meaningfully extended in this session, conduct a new evidence-based Market
Opportunity Search per AGENTS.md:

1. Inventory all cached data files (`data/raw/*.parquet`) with row counts, date
   ranges, and Close completeness.
2. For each cached instrument, compute available trading-day overlap and
   identify unexplored structural mechanisms (e.g., cross-asset carry,
   volatility-term-structure proxies using ^VIX level/trend as a regime
   input on the cached ETF universe, multi-horizon momentum combining
   time-series and cross-sectional signals).
3. Score up to 5 new candidate mechanisms against the seven criteria
   ((a)–(g)) from AGENTS.md.
4. Select the top candidate and pre-register a hypothesis + frozen config
   BEFORE any backtest execution.

## Acceptance Criteria

### If choosing Option A:
- [ ] Locate and inspect the paper-trading engine source and state files.
- [ ] Compute the current paper-trading track-record length (days of daily P&L).
- [ ] If < 63 days: extend the paper-trading validation by running the engine's
      simulation forward on the cached data (deterministic replay), producing
      daily P&L snapshots until the 63-day minimum gate is reached.
- [ ] Produce a track-record report (`research/reports/paper_trading_validation_001.md`)
      documenting: daily P&L, cumulative return, volatility, Sharpe, turnover,
      realized vs. backtested slippage, max drawdown, and position statistics.
- [ ] Update `README.md` Current Status with the paper-trading track-record
      length and gate status.
- [ ] If the 63-day gate is reached: confirm the incumbent advances to the
      next validation phase (or remains in validation if performance is below
      expectations). Report the net-of-cost track-record Sharpe honestly.

### If choosing Option B:
- [ ] Inventory all cached data files with row counts, date ranges, completeness.
- [ ] Identify and score up to 5 new candidate mechanisms.
- [ ] Select the top candidate and write:
  - `research/hypotheses/<candidate_id>.md` (full hypothesis with mechanism,
    expected direction, holding horizon, universe, features, entry/exit,
    benchmark, confounders, falsification condition, cost model)
  - `config/<candidate_id>_candidate_001.yaml` (frozen pre-registered config)
- [ ] Write a shortlist report (`research/reports/opportunity_shortlist_cycle20.md`)
      documenting the scoring and selection rationale.
- [ ] Update `README.md` Current Status with the new shortlist.
- [ ] Pre-register the evaluation plan (splits, gates, multiple-testing) in the
      hypothesis file — **no backtest execution**.

## Scope Boundaries

- Research/backtesting only. No live trading, no credentials, no network access
  unless a paper-trading engine requires it for deterministic replay.
- Cache-only data access (`force=False`); do not fetch new data from Yahoo Finance
  or any external source.
- Do not modify C1–C6 artifacts, hypotheses, configs, or scripts (they are archived).
- If extending paper-trading: reuse existing infrastructure; do not introduce new
  dependencies, scheduled jobs, or workflows.
- The 63-day paper-trading gate is the sole gating criterion for advancement;
  do not weaken it.
- Next task must be bounded and non-recursive (must not start additional agent
  sessions).

## Validation Commands

```bash
# Check for paper-trading engine and state
ls -la data/processed/paper_trading/ 2>/dev/null
ls -la data/processed/paper_trading_state.yaml 2>/dev/null
find src/ -name "*paper*" -o -name "*trading*" 2>/dev/null

# If extending paper-trading: run the engine's deterministic replay
python3 research/run_paper_trading_validation.py 2>/dev/null || echo "Engine not yet present"

# Verify cached data inventory
python3 -c "
import pandas as pd, glob, os
for f in sorted(glob.glob('data/raw/*.parquet')):
    df = pd.read_parquet(f)
    sym = os.path.basename(f).replace('.parquet','')
    print(f'{sym}: {len(df)} rows, {df.index.min().date()} -> {df.index.max().date()}, Close NaN={df[\"Close\"].isna().sum()}')
"
```

## Decision Protocol

1. First, attempt **Option A**: inspect the paper-trading engine. If it exists
   and the track-record is < 63 days, extend it to 63 days via deterministic
   replay on cached data and document the results.
2. If the paper-trading engine does not exist, is broken, or cannot be extended
   without live network access, fall back to **Option B**: document a new
   evidence-based shortlist and pre-register the top candidate (NO backtest).
3. In either case, prepare the NEXT_AGENT_TASK.md for the subsequent cycle
   based on the outcome (e.g., if 63-day gate reached → begin paper-trading
   performance review; if new shortlist created → Cycle 21 executes the
   top candidate's pre-registered evaluation).
