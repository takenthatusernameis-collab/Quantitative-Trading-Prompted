# Next Agent Task: Paper Trading Monitoring & Data Acquisition — Cycle 53

## Context
The microcap mom121 data source survey and exploratory diagnostic (Cycle 52) are complete:
- Survey: `research/reports/microcap_datasource_survey_001.md` — 8 free sources assessed; **SEC EDGAR XBRL** is the only viable source for point-in-time shares outstanding (verified: 33/38 tickers returned usable history).
- Diagnostic: `research/run_microcap_exploratory.py` + `research/experiments/mom121_microcap_exploratory_001.md` — clearly-labelled exploratory only, no tradable edge claimed. Universe: 31 tickers, 699 trading days (2024-01-02 → 2026-10-14), canonical 12-1 momentum computed, descriptive stats only.
- Hypothesis `research/hypotheses/mom121_microcap_001.md` updated to v0.4; verdict remains **Blocked by data/infrastructure** (quarterly lag, no delistings, survivorship bias, no cost model, retrospective ticker list).

The incumbent paper-trading track record (tsmomentum_spytrend_001) stands at **447 days** (2025-01-02 → 2026-10-14), NAV **$135,057.00** (+35.06%), Sharpe **1.9302**, max DD **-2.92%**, rolling 63-day Sharpe **0.1185**. All primary go/no-go gates pass. Regime: risk-on, 132 days.

**Drift flag persists**: `low_rolling_sharpe` on 2026-10-12 (0.4892), 2026-10-13 (0.3669), 2026-10-14 (0.1185) — **3 consecutive trading days**. Trajectory over last 18 days volatile (range -0.51 to +1.19). Not yet at the >20-day persistence threshold.

## Objective
Re-attempt data acquisition from Yahoo Finance to extend the paper-trading track record, and continue monitoring the rolling 63-day Sharpe trajectory. If new data arrives, run the deterministic replay and update the track record. If no new data, report the blocker in a new validation report.

## Acceptance Criteria
1. Re-run `src/data/yfinance_fetcher.py` (or the fetch path used by `research/run_paper_trading_replay.py`) with `force=True` and `end_date="2026-11-30"`.
2. Verify per-symbol max dates for the 7 incumbent ETFs (SPY, QQQ, IWM, TLT, GLD, EFA, EEM) and ^VIX.
3. If a new real trading day (nonzero volume) exists beyond 2026-10-14, run `research/run_paper_trading_replay.py` with the matching `end_date` and record the extended track record (NAV, Sharpe, max DD, rolling 63-day Sharpe, regime flips, regime state, drift flags).
4. If no new data, do NOT fabricate a replay; write `research/reports/paper_trading_validation_036.md` documenting the blocker precisely (max dates observed, per-symbol volume check, yfinance exclusive-end semantics).
5. Independently verify the rolling 63-day Sharpe by recomputing it from `data/processed/paper_trading_state.yaml` cumulative returns (do not trust the stored drift_flag value).
6. Run the test suite: `python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v` — must pass 10/10.
7. Update `NEXT_AGENT_TASK.md` with the next bounded task.

## Validation Commands
```bash
# 1. Fetch and verify data availability
python3 -c "
import sys; sys.path.insert(0, 'src')
from data.yfinance_fetcher import fetch_universe
df = fetch_universe(force=True, end_date='2026-11-30')
print('max date:', df.index.max())
"

# 2. If replay ran, verify state YAML integrity
python3 -c "
import yaml
with open('data/processed/paper_trading_state.yaml') as f:
    state = yaml.safe_load(f)
print('run_history records:', len(state.get('run_history', [])))
"

# 3. Independent rolling Sharpe recomputation
python3 -c "
import pandas as pd, numpy as np
state = yaml.safe_load(open('data/processed/paper_trading_state.yaml'))
cr = pd.Series(state['cumulative_returns'])
ret = cr.pct_change().dropna()
roll = ret.rolling(63).apply(lambda x: x.mean()/x.std()*np.sqrt(252), raw=True)
print('rolling 63d Sharpe (last):', roll.iloc[-1])
"

# 4. Test suite
python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v
```

## Scope Boundaries
- **Do not** place live trades, enable live trading, or access credentials.
- **Do not** fabricate data, market findings, or test output.
- **Do not** add new dependencies, services, scheduled jobs, agents, or workflows.
- **Do not** modify workflow scheduling or agent counts.
- **Do** preserve the existing replay script's yfinance exclusive-end semantics; if a fix is needed, make the smallest reversible change and document it.
- **Do** keep work bounded and restart-safe.

## Evidence Base
- Track record state: `data/processed/paper_trading_state.yaml`
- Replay script: `research/run_paper_trading_replay.py`
- Fetcher: `src/data/yfinance_fetcher.py`
- Prior validation reports: `research/reports/paper_trading_validation_026.md` through `_035.md`
- Rolling Sharpe trajectory: `research/reports/paper_trading_rolling.md`
- Microcap deliverables (this cycle): `research/reports/microcap_datasource_survey_001.md`, `research/run_microcap_exploratory.py`, `research/experiments/mom121_microcap_exploratory_001.md`, `research/hypotheses/mom121_microcap_001.md` (v0.4)
