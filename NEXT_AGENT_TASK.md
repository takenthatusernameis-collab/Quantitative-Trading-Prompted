# Next Agent Task: Post-Close Data Acquisition & Track Record Extension — Cycle 80

## Context

The paper-trading track record (tsmomentum_spytrend_001) stands at **447 days** (2025-01-02 → 2026-10-14), NAV **$135,043.35**, Sharpe **1.9272**, max DD **-2.93%**, rolling 63-day Sharpe **0.1133**. All primary go/no-go gates pass. Regime: risk-on, 132 days.

**Drift flag persists**: `low_rolling_sharpe` on 2026-10-12 (0.4892), 2026-10-13 (0.3669), 2026-10-14 (0.1133) — **3 consecutive trading days**. Not yet at the >20-day persistence threshold.

**Cycle 79 outcome**: Session ran at **2026-10-15T03:18:05Z** (UTC) — before the 20:00 UTC post-close gate. Fetch skipped per timestamp gate. Independent rolling Sharpe verification matched exactly (0.1133313687). Tests passed 10/10. Documented in `research/reports/paper_trading_validation_051.md`.

## Objective

1. **Timestamp gate**: Record the UTC session timestamp. Only attempt the post-close fetch if `session_time >= 2026-10-15T20:00:00Z`. If before that gate, do NOT fetch — document the timing and hand off with the same gate for the next cycle.
2. **Post-close fetch (only if gate met)**: Re-run `fetch_universe(['SPY','QQQ','IWM','TLT','GLD','EFA','EEM','^VIX'], start_date='2025-01-01', end_date='2026-11-30', force=True, raw_dir='data/raw')`; verify per-symbol max dates. If a new real trading day (nonzero volume, incumbent ETFs) exists beyond 2026-10-14, bump the replay script's `end_date` to capture it, run `research/run_paper_trading_replay.py`, and record the extended track record (NAV, Sharpe, max DD, rolling 63-day Sharpe, regime flips, regime state, drift flags).
3. **If blocked post-close**: Document the confirmed post-close blocker in `research/reports/paper_trading_validation_052.md`.

## Acceptance Criteria

1. **Timestamp gate**: Record the UTC session timestamp. Only proceed to fetch if `session_time >= 2026-10-15T20:00:00Z`. If before, skip fetch and proceed to criterion 3.
2. **Post-close fetch (only if gate met)**: Fetch with `force=True`; verify per-symbol max dates and nonzero volume for incumbent ETFs. If new trading day(s) found:
   - Update `research/run_paper_trading_replay.py` `end_date` (yfinance exclusive-end: new date + 1 day) and replay-date upper bound
   - Run replay script
   - Record extended track record metrics
3. **Independent rolling-63-day Sharpe verification**: Recompute from `data/processed/paper_trading_state.yaml` `cumulative_returns` (last 63 entries) via `mean/std(ddof=1)*sqrt(252)`. Must match `state.drift_flags.low_rolling_sharpe.value`.
4. **Tests**: `python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v` — must pass 10/10.
5. Write `research/reports/paper_trading_validation_052.md` with results (extended track record if data found; confirmed post-close blocker if not).
6. Update `NEXT_AGENT_TASK.md` with one narrow, testable next task following from the evidence.

## Validation Commands

```bash
# 1) Timestamp gate
TZ=UTC date -u +%Y-%m-%dT%H:%M:%SZ

# 2) Post-close fetch (ONLY if >= 2026-10-15T20:00:00Z) + per-symbol max dates
PYTHONPATH=<repo>/src python3 << 'PY'
from data.yfinance_fetcher import fetch_universe
import pandas as pd
symbols=['SPY','QQQ','IWM','TLT','GLD','EFA','EEM','^VIX']
df = fetch_universe(symbols, start_date='2025-01-01', end_date='2026-11-30', force=True, raw_dir='data/raw')
print('aligned max:', df.index.max())
for s in symbols:
    v = df[('Volume', s)]
    lv = v.index.max(); print(f"{s}: max_date={v.dropna().index.max().date()} last_vol={int(v.loc[lv])}")
PY

# 3) Independent rolling 63-day Sharpe from state YAML
python3 << 'PY'
import yaml, pandas as pd, numpy as np
state = yaml.safe_load(open('data/processed/paper_trading_state.yaml'))
cr = pd.Series(state['cumulative_returns']).tail(63)
print('rolling63 ddof=1:', cr.mean()/cr.std()*np.sqrt(252))
print('stored drift flag:', state['drift_flags']['low_rolling_sharpe']['value'])
PY

# 4) Tests
python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v
```

## Scope Boundaries

- Do not place live trades, enable live trading, or access credentials.
- Do not fabricate data, market findings, or test output.
- Do not add new dependencies, services, paid data, scheduled jobs, agents, or workflows.
- Do not modify workflow scheduling or agent counts.
- Preserve yfinance exclusive-end semantics; the replay script's hardcoded `end_date="2026-10-15"` / bound `"2026-10-14"` already encodes this — only bump if a new trading day is confirmed.
- Do not commit changes unless explicitly requested; keep work in the working tree for inspection.
- Keep work bounded and restart-safe.

## Evidence Base

- State: `data/processed/paper_trading_state.yaml` (current_nav 135043.35187742324, rolling_sharpe_63d 0.1133313687, last_run_date 2026-10-14, 447 cumulative_returns records)
- Replay: `research/run_paper_trading_replay.py`
- Fetcher: `src/data/yfinance_fetcher.py`
- Recent validations: `research/reports/paper_trading_validation_050.md` (Cycle 78), `paper_trading_validation_051.md` (Cycle 79)
- Rolling report: `research/reports/paper_trading_rolling.md`
- Drift root-cause: `research/reports/paper_trading_drift_analysis_001.md`