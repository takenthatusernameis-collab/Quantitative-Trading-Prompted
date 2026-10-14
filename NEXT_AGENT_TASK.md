# Next Agent Task: Cycle 21 — Extended Paper-Trading Validation & Regime Diversity Capture

## Context

Cycle 20 executed Option A (Extend incumbent paper-trading validation) via `research/run_paper_trading_replay.py`. The deterministic historical replay on cached data (2026-07-02 → 2026-10-09, 70 trading days) produced:

- **Track-record length:** 70 days (exceeds 63-day minimum gate) ✅
- **Rolling 63-day Sharpe:** 0.9356 (exceeds 0.9 target) ✅
- **Max drawdown:** -1.23% (well within 15% threshold) ✅
- **Full-period Sharpe:** 0.4191 (below 0.9 target; attributable to early-period volatility)
- **Regime behavior:** 70 days of SPY > SMA (regime_exposure = 1.0 constant), **zero regime flips**
- **Turnover:** median 0.40%, p95 30.05%, elevated on final days due to vol-targeting in low-vol regime
- **Net return:** +0.90% (3.28% ann.), volatility 7.83% ann.

Artifacts: `data/processed/paper_trading_state.yaml`, 70 daily parquet files, `research/reports/paper_trading_rolling.md`, `research/reports/paper_trading_validation_001.md`.

**Key finding:** The 70-day validation period captured only a single regime (persistent risk-on, SPY above 200-day SMA). The SPY-trend filter — a core component of the incumbent's risk management — was never tested in a risk-off regime. The rolling 63-day Sharpe meets the target, but this is based on a homogeneous market environment.

## Objective

Extend the paper-trading validation to capture **regime diversity**, specifically targeting at least one SPY SMA regime flip (risk-on → risk-off → risk-on). This requires running the simulation further back in history to include the 2025-2026 period where SPY crossed its 200-day SMA.

### Action Required

Run the paper-trading engine on an extended historical window that includes regime transitions. Target: **minimum 126 trading days (6 months)** of track record with at least **one observed regime flip**.

### Implementation Steps

1. **Identify regime flip dates** in cached SPY data (SPY crossing 200-day SMA).
2. **Extend replay start date** to capture at least one full regime cycle (e.g., start from 2025-01-01 or earlier).
3. **Run deterministic replay** from the extended start date to 2026-10-09 (or latest cached date).
4. **Verify** that at least one regime flip occurs in the simulation output.
5. **Document** regime-specific performance (returns, drawdown, turnover in each regime).
6. **Update** `paper_trading_state.yaml`, daily artifacts, rolling report, and validation report.

## Acceptance Criteria

- [ ] Identify SPY 200-day SMA crossover dates in cached data (2024-2026).
- [ ] Select replay start date that guarantees ≥ 1 regime flip in the simulation window.
- [ ] Run extended deterministic replay (Option A continuation) via `research/run_paper_trading_replay.py` (modified) or new script.
- [ ] Achieve **≥ 126 trading days** track record (6 months).
- [ ] Confirm **≥ 1 regime flip** observed in `run_history` (regime_exposure changes from 1.0 to 0.0 or vice versa).
- [ ] Produce updated validation report (`research/reports/paper_trading_validation_002.md`) with regime-segmented analysis.
- [ ] Update `README.md` Current Status with extended track-record length, regime flip count, and regime-specific metrics.
- [ ] If no regime flip exists in cached data: document this limitation and prepare Option B (new shortlist) as fallback.

## Scope Boundaries

- Research/backtesting only. No live trading, no credentials, no network access (`force=False`).
- Cache-only data access (`data/raw/*.parquet`).
- Do not modify C1–C6, C18–C19 artifacts (archived).
- Reuse existing paper-trading infrastructure (`src/simulation/paper_trading.py`, `src/simulation/engine.py`).
- The 63-day gate is already passed; this cycle extends for **regime diversity**, not gate compliance.
- Next task must be bounded and non-recursive.

## Validation Commands

```bash
# Check SPY 200-day SMA crossovers in cached data
python3 -c "
import pandas as pd
df = pd.read_parquet('data/raw/SPY.parquet')
close = df['Close']
sma200 = close.rolling(200).mean()
cross_down = (close.shift(1) > sma200.shift(1)) & (close < sma200)
cross_up = (close.shift(1) < sma200.shift(1)) & (close > sma200)
print('Cross DOWN (risk-on to risk-off):')
print(close[cross_down].index.strftime('%Y-%m-%d').tolist())
print('Cross UP (risk-off to risk-on):')
print(close[cross_up].index.strftime('%Y-%m-%d').tolist())
"

# Run extended replay (after modifying start date in script)
python3 research/run_paper_trading_replay.py

# Verify regime flips in state
python3 -c "
import yaml
with open('data/processed/paper_trading_state.yaml') as f:
    state = yaml.safe_load(f)
regimes = [r['regime_exposure'] for r in state['run_history']]
flips = sum(1 for i in range(1, len(regimes)) if regimes[i] != regimes[i-1])
print(f'Total days: {len(regimes)}')
print(f'Regime flips: {flips}')
print(f'Regime sequence: {regimes[:10]}...{regimes[-10:]}')
"

# Check report
cat research/reports/paper_trading_rolling.md
```

## Decision Protocol

1. **Primary path:** Extend replay to capture regime flip(s). If successful → Cycle 22 continues monitoring or evaluates go/no-go with regime-aware metrics.
2. **Fallback (if cached data lacks regime flips):** Document the data limitation. Fall back to Option B from Cycle 20 (new evidence-based shortlist) for Cycle 21.
3. **In either case:** Prepare `NEXT_AGENT_TASK.md` for the subsequent cycle based on outcome.