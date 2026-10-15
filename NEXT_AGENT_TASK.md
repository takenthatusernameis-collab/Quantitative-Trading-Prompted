# Next Agent Task: Paper Trading Monitoring & Data Acquisition — Cycle 69

## Context
The paper-trading track record (tsmomentum_spytrend_001) stands at **447 days** (2025-01-02 → 2026-10-14), NAV **$135,043.35**, Sharpe **1.9272**, max DD **-2.93%**, rolling 63-day Sharpe **0.1133**. All primary go/no-go gates pass. Regime: risk-on, 132 days.

**Drift flag persists**: `low_rolling_sharpe` on 2026-10-12 (0.4892), 2026-10-13 (0.3669), 2026-10-14 (0.1133) — **3 consecutive trading days**. Trajectory over last 18 days volatile (range -0.51 to +1.19). Not yet at the >20-day persistence threshold.

Cycle 68 validation: data acquisition re-attempted with force=True, end_date 2026-11-30. All 7 incumbent ETFs end at 2026-10-14 with real nonzero volume (SPY 55,376,100; QQQ 51,067,700; IWM 37,946,800; TLT 50,909,600; GLD 10,283,300; EFA 10,653,000; EEM 21,169,200). ^VIX ends at 2026-10-14 with Volume=0 (placeholder). Direct yfinance query for 2026-10-14→2026-10-21 returns 1 row for all 8 symbols dated 2026-10-14 — no 2026-10-15 data published. Rolling 63-day Sharpe independently verified (0.114242 via ddof=0; 0.113331 via ddof=1, exact match with state YAML drift flag). Tests: 10/10 passed. Report: `research/reports/paper_trading_validation_040.md`.

Microcap exploratory work remains blocked by data/infrastructure (quarterly EDGAR lag, no delistings, survivorship bias) — see `research/hypotheses/mom121_microcap_001.md` v0.4.

## Objective
Re-attempt data acquisition from Yahoo Finance to extend the paper-trading track record. If new data arrives, run the deterministic replay and update the track record. If no new data, report the blocker in a new validation report. Continue monitoring rolling 63-day Sharpe.

## Acceptance Criteria
1. Re-run fetch path with `force=True` and `end_date="2026-11-30"`. Verify per-symbol max dates for SPY, QQQ, IWM, TLT, GLD, EFA, EEM and ^VIX.
2. If a new real trading day (nonzero volume for incumbent ETFs) exists beyond 2026-10-14, run `research/run_paper_trading_replay.py` with matching `end_date` and record extended track record (NAV, Sharpe, max DD, rolling 63-day Sharpe, regime flips, regime state, drift flags).
3. If no new data, write `research/reports/paper_trading_validation_041.md` documenting the blocker precisely (max dates, per-symbol volume, yfinance exclusive-end semantics).
4. Independently verify rolling 63-day Sharpe by recomputing from `data/processed/paper_trading_state.yaml` cumulative returns.
5. Run `python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v` — must pass 10/10.
6. Update `NEXT_AGENT_TASK.md` with next bounded task.

## Validation Commands
```bash
# Fetch and verify
PYTHONPATH=/home/runner/work/Quantitative-Trading-Prompted/Quantitative-Trading-Prompted/src python3 << 'PY'
from data.yfinance_fetcher import fetch_universe
symbols=['SPY','QQQ','IWM','TLT','GLD','EFA','EEM']
df = fetch_universe(symbols, start_date='2025-01-01', end_date='2026-11-30', force=True, raw_dir='data/raw')
print('max:', df.index.max())
PY

# Independent rolling Sharpe
python3 << 'PY'
import yaml, pandas as pd, numpy as np
with open('data/processed/paper_trading_state.yaml') as f:
    state = yaml.safe_load(f)
cr = pd.Series(state['cumulative_returns'])
roll = cr.rolling(63).apply(lambda x: x.mean()/x.std()*np.sqrt(252) if x.std()>0 else np.nan, raw=True)
print('roll63:', roll.iloc[-1])
PY

# Tests
python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v
```

## Scope Boundaries
- Do not place live trades, enable live trading, or access credentials.
- Do not fabricate data, market findings, or test output.
- Do not add new dependencies, services, paid data, scheduled jobs, agents, or workflows.
- Do not modify workflow scheduling or agent counts.
- Preserve yfinance exclusive-end semantics; make smallest reversible change if needed and document it.
- Keep work bounded and restart-safe.

## Evidence Base
- State: `data/processed/paper_trading_state.yaml`
- Replay: `research/run_paper_trading_replay.py`
- Fetcher: `src/data/yfinance_fetcher.py`
- Recent validations: `research/reports/paper_trading_validation_040.md` (Cycle 68)
- Rolling report: `research/reports/paper_trading_rolling.md`