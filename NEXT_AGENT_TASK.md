# Next Agent Task: Post-Close Evaluation Gate Execution — Cycle 155 (Pending Gate)

## Context

Current check performed at 2026-10-15T16:36:22Z UTC. Post-close gate is 2026-10-17T20:00:00Z UTC; gate not met. No fetch or replay performed.

State (from `data/processed/paper_trading_state.yaml` as of 2026-10-14):
- Track record: 447 days (2025-01-02 → 2026-10-14)
- NAV: $135,043.35
- Sharpe: 1.9272
- Max DD: -2.93%
- Rolling 63d Sharpe: 0.1133 (stored)
- Drift flag persists (3 consecutive days, not yet >20d threshold)
- Regime: risk-on (132 days)
- Regime flips: 6 (447 run_history entries)

Independent verifications (this session):
- Rolling 63d Sharpe recomputed from last 63 cumulative_returns matches stored value within float precision (0.11333136870186278 vs 0.11333136870186329, diff 5.13e-16)
- Regime flips computed from run_history transitions: 6 (expected 6)
- State YAML integrity: cumulative_returns=447, run_history=447, cumulative_dates=447, no duplicate dates, cumulative_returns == daily_return series exactly, product of (1+returns) == NAV/100000
- Supervisor loop tests: 10/10 passed

Validation report written: `research/reports/paper_trading_validation_155.md`

## Objective

1. **Timestamp gate enforcement**: Record UTC session time via `TZ=UTC date -u +%Y-%m-%dT%H:%M:%SZ`. If `session_time < 2026-10-17T20:00:00Z`, do **not** fetch or replay. Document timing, run verifications (3-4), supervisor tests (5), write/update validation report for cycle 155, and leave this same task unchanged (gate still pending). If `session_time >= 2026-10-17T20:00:00Z`, proceed to (2).
2. **Post-close fetch (gate met)**: Re-run `fetch_universe(['SPY','QQQ','IWM','TLT','GLD','EFA','EEM','^VIX'], start_date='2025-01-01', end_date='2026-11-30', force=True, raw_dir='data/raw')`. Verify per-symbol max dates. Determine if any new real trading day exists beyond 2026-10-14 (nonzero volume, incumbent ETFs).
    - If **no new real trading day exists**: Document confirmed blocker (max date == 2026-10-14), do not modify replay, run verifications (3-4), supervisor tests (5), write validation report, and prepare next narrow task (advance gate/monitor for next close).
    - If **new real trading day exists**: Bump `research/run_paper_trading_replay.py`'s `end_date` to capture it, preserving yfinance exclusive-end semantics. Run `research/run_paper_trading_replay.py`. Record extended track record (days, NAV, Sharpe, max DD, rolling 63d Sharpe). Recompute regime flips from extended history.
3. **Independent rolling-63-day Sharpe verification**: From `data/processed/paper_trading_state.yaml`, compute rolling 63d Sharpe from last 63 `cumulative_returns`: `(mean*252)/(std(ddof=1)*sqrt(252))`. Must match `state.drift_flags.low_rolling_sharpe.value` (within float precision).
4. **Regime flip verification**: Recompute regime flips from `run_history.regime_exposure` transitions. If replay extended track, use recomputed count; otherwise expect 6.
5. **Supervisor loop tests**: `python3 .github/scripts/test_kilo_supervisor_loop.py -v` must pass 10/10.
6. **Reporting**: Write/update `research/reports/paper_trading_validation_155.md` with UTC time, gate result, fetch results (if attempted), per-symbol max dates, track record changes (if any), verification numbers, and test results.
7. **Next task**: Update `NEXT_AGENT_TASK.md` with one narrow, testable next task following evidence (do not fabricate). Preserve restart-safety.

## Validation Commands (reference)
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
print('flips',t,len(rh))
"
python3 .github/scripts/test_kilo_supervisor_loop.py -v
```

## Scope Boundaries
- Research/backtesting only. No live trades, no live trading enablement, no credentials access.
- Do not fabricate data, market findings, or test outputs.
- Do not add dependencies, services, paid data, scheduled jobs, agents, or workflows.
- Preserve yfinance exclusive-end semantics when bumping `end_date`.
- Keep bounded, restart-safe. If blocked by real data absence, document precisely.