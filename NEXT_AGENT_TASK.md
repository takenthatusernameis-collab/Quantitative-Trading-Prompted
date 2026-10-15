# Next Agent Task: Post-Close Data Acquisition & Track Record Extension — Cycle 93

## Context

Cycle 92 (session 2026-10-15T11:32:43Z) executed before post-close gate (2026-10-17T20:00:00Z). Timestamp gate enforced; no fetch attempted. Independent rolling-63-day Sharpe recomputed matched stored value (diff ~5e-16), regime flips = 6. Supervisor loop tests 10/10 passed. Validation report: `research/reports/paper_trading_validation_092.md`.

Track record remains at 447 days (2025-01-02 → 2026-10-14), NAV $135,043.35, Sharpe 1.9272, max DD -2.93%, rolling 63-day Sharpe 0.1133. Drift flag persists (3 consecutive days, not yet >20-day threshold). State unchanged.

## Objective

1. **Timestamp gate**: Record UTC session timestamp. Only attempt post-close fetch if `session_time >= 2026-10-17T20:00:00Z`. If before gate, do NOT fetch — document timing and hand off with same gate for next cycle.
2. **Post-close fetch (only if gate met)**: Re-run `fetch_universe(['SPY','QQQ','IWM','TLT','GLD','EFA','EEM','^VIX'], start_date='2025-01-01', end_date='2026-11-30', force=True, raw_dir='data/raw')`; verify per-symbol max dates. If new real trading day (nonzero volume, incumbent ETFs) exists beyond 2026-10-14, bump replay script's `end_date` to capture it (preserve yfinance exclusive-end semantics), run `research/run_paper_trading_replay.py`, record extended track record. If no new real trading day exists, document confirmed blocker.
3. **Independent rolling-63-day Sharpe verification**: Recompute from `data/processed/paper_trading_state.yaml` `cumulative_returns` (last 63) via `(mean*252)/(std(ddof=1)*sqrt(252))`. Must match `state.drift_flags.low_rolling_sharpe.value`.
4. **Regime flip verification**: Recompute regime flips from `run_history` `regime_exposure` transitions; must equal 6 (or the recomputed value if the replay extended the track record).
5. **Tests**: `python3 .github/scripts/test_kilo_supervisor_loop.py -v` must pass 10/10.
6. Write `research/reports/paper_trading_validation_093.md` with results.
7. Update `NEXT_AGENT_TASK.md` with one narrow, testable next task for following cycle.

## Validation Commands

```bash
TZ=UTC date -u +%Y-%m-%dT%H:%M:%SZ
python3 -c "
import yaml,math
d=yaml.safe_load(open('data/processed/paper_trading_state.yaml'))
ret=d['cumulative_returns'][-63:]
m=sum(ret)/len(ret); v=sum((r-m)**2 for r in ret)/(len(ret)-1); s=(m*252)/(math.sqrt(v)*math.sqrt(252)) if v>0 else 0
print('sharpe',s,d['drift_flags']['low_rolling_sharpe']['value'])
"
python3 -c "
import yaml
d=yaml.safe_load(open('data/processed/paper_trading_state.yaml'))
rh=d['run_history']; t=0; prev=rh[0]['regime_exposure']
for i in range(1,len(rh)):
  if rh[i]['regime_exposure']!=prev: t+=1; prev=rh[i]['regime_exposure']
print('flips',t)
"
python3 .github/scripts/test_kilo_supervisor_loop.py -v
```

## Scope Boundaries

- Do not place live trades, enable live trading, or access credentials.
- Do not fabricate data, market findings, or test output.
- Do not add new dependencies, services, paid data, scheduled jobs, agents, or workflows.
- Preserve yfinance exclusive-end semantics when bumping `end_date`.
- Do not commit changes unless explicitly requested; keep work in working tree.
- Keep work bounded and restart-safe.