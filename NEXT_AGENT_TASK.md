# Next Agent Task: Post-Close Data Acquisition Re-Attempt & README Reconciliation — Cycle 73

## Context
The paper-trading track record (tsmomentum_spytrend_001) stands at **447 days** (2025-01-02 → 2026-10-14), NAV **$135,043.35**, Sharpe **1.9272**, max DD **-2.93%**, rolling 63-day Sharpe **0.1133**. All primary go/no-go gates pass. Regime: risk-on, 132 days.

**Drift flag persists**: `low_rolling_sharpe` on 2026-10-12 (0.4892), 2026-10-13 (0.3669), 2026-10-14 (0.1133) — **3 consecutive trading days**. Not yet at the >20-day persistence threshold.

**Cycle 72 outcome**: Re-ran `fetch_universe(..., end_date="2026-11-30", force=True)`. No new real trading day exists beyond 2026-10-14 for the 7 incumbent ETFs or ^VIX. This is a **timing condition, not a feed failure**: the US equity market closes at 20:00 UTC, and Cycle 72's fetch ran at 02:45 UTC on 2026-10-15 — well before the Oct 15 close. A direct `yfinance.download('SPY', start='2026-10-14', end='2026-10-16')` returned only the 2026-10-14 row (SPY Vol=55,376,100).

**Key decision gate**: Re-fetching *before* the Oct 15 US market close (20:00 UTC) will reproduce the identical "no data beyond 2026-10-14" result. The prior ~18 cycles (validation_026–043, all committed with empty/summary messages) each re-ran the same fetch before market close and found no new data. Per AGENTS.md bounded-work and change-approach rules, the next cycle must **gate on the post-close timestamp** and include a concrete pivot if data remains unavailable even after a full market day has closed.

**Staleness finding (evidence for pivot)**: The committed README `Current Status` "Cycle 52" snapshot reports NAV $135,057.00 / Sharpe 1.9302 / rolling 0.1185 / SPY Vol 35,185,126 (a pre-finalization intermediate value). The authoritative working-tree `data/processed/paper_trading_state.yaml` (current_nav 135043.35, rolling_sharpe_63d 0.113331, SPY Vol 55,376,100) reflects the finalized 2026-10-14 data. The README headline is one finalization step behind and was never re-synced.

## Objective
1. **If running at/after 20:00 UTC on 2026-10-15** (i.e., after the Oct 15 US market close): re-attempt data acquisition and extend the track record if real data for 2026-10-15 (or later) exists for the incumbent ETFs.
2. **If data is still unavailable beyond 2026-10-14 even after the Oct 15 close** (confirmed post-close re-fetch): document the confirmed post-close blocker in `research/reports/paper_trading_validation_045.md` **and** reconcile the stale README "Current Status" Cycle 52 snapshot with the actual working-tree state so the project headline is accurate.

If this session is running **before 20:00 UTC 2026-10-15**, do NOT perform a fruitless same-approach fetch. Instead, execute only the **README reconciliation pivot** (item 3) directly — it is verifiable in-session and improves documentation integrity regardless of data availability.

## Acceptance Criteria
1. **Timestamp gate**: Record the UTC session timestamp. Only attempt the post-close fetch if `session_time >= 2026-10-15T20:00:00Z`. If before that gate, skip the fetch and proceed to criterion 3.
2. **Post-close fetch (only if gate met)**: Re-run `fetch_universe(['SPY','QQQ','IWM','TLT','GLD','EFA','EEM','^VIX'], start_date='2025-01-01', end_date='2026-11-30', force=True)`; verify per-symbol max dates. If a new real trading day (nonzero volume, incumbent ETFs) exists beyond 2026-10-14, bump the replay script's `end_date` to capture it, run `research/run_paper_trading_replay.py`, and record the extended track record (NAV, Sharpe, max DD, rolling 63-day Sharpe, regime flips, regime state, drift flags).
3. **README reconciliation pivot (always do if fetch is skipped or blocked post-close)**: Update the README `Current Status` headline metrics so they match the authoritative working-tree state (447 days; NAV $135,043.35; Sharpe 1.9272; max DD -2.93%; rolling 63-day Sharpe 0.1133; regime risk-on 132 days; 6 flips; drift flag 3 consecutive days 2026-10-12→14). Keep the existing narrative structure; only correct stale numbers and the SPY volume figure (35,185,126 → 55,376,100) and the rolling-Sharpe value (0.1185 → 0.1133).
4. **Independent rolling-63-day Sharpe verification**: Recompute from `data/processed/paper_trading_state.yaml` `cumulative_returns` (447 entries) via `mean(last_63)/std(last_63, ddof=1)*sqrt(252)`. Result must equal 0.1133313687 (exact match to `state.drift_flags.low_rolling_sharpe.value`).
5. **Tests**: `python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v` — must pass 10/10.
6. If data was extended in step 2: write `research/reports/paper_trading_validation_045.md` with the extended track record. If blocked post-close: write `research/reports/paper_trading_validation_045.md` documenting the confirmed post-close blocker + the README reconciliation performed.
7. Update `NEXT_AGENT_TASK.md` with one narrow, testable next task following from the evidence above.

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

# 4) Independent rolling 63-day Sharpe from state YAML
python3 << 'PY'
import yaml, pandas as pd, numpy as np
state = yaml.safe_load(open('data/processed/paper_trading_state.yaml'))
cr = pd.Series(state['cumulative_returns']).tail(63)
print('rolling63 ddof=1:', cr.mean()/cr.std()*np.sqrt(252))
print('stored drift flag:', state['drift_flags']['low_rolling_sharpe']['value'])
PY

# 5) Tests
python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v

# 3) README reconciliation verification
git show HEAD:README.md | grep -c "135,057.00"   # expect >0 before edit
grep -c "135,043.35" README.md                     # expect >0 after edit
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
- State: `data/processed/paper_trading_state.yaml` (current_nav 135043.35, rolling_sharpe_63d 0.113331, last_run_date 2026-10-14, 447 run_history records)
- Replay: `research/run_paper_trading_replay.py`
- Fetcher: `src/data/yfinance_fetcher.py`
- Recent validations: `research/reports/paper_trading_validation_043.md` (Cycle 71), `paper_trading_validation_044.md` (Cycle 72)
- Rolling report: `research/reports/paper_trading_rolling.md`
- Drift root-cause: `research/reports/paper_trading_drift_analysis_001.md`
- Stale README snapshot: `README.md` "Current Status" Cycle 52 (NAV $135,057.00, rolling 0.1185, SPY Vol 35,185,126)
