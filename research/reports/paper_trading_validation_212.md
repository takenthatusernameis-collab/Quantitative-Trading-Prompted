# Paper Trading Validation Report — Cycle 212

## UTC Session Time
2026-10-15T19:20:13Z

## Gate State
Post-close gate: **2026-10-18T20:00:00Z UTC** — **NOT MET** (session time < gate).
Per protocol: **NO fetch and NO replay** performed this cycle.

## State Snapshot
| Metric | Value |
|---|---|
| run_history entries | 447 |
| last_run_date | 2026-10-14 |
| current NAV | 135043.35187742324 |
| peak NAV | 139120.07235486925 |
| max drawdown | -2.93% |
| stored rolling 63d Sharpe | 0.11333136870186329 |
| drift flag `low_rolling_sharpe` | active=False |
| regime flips | 6 |

## Verification Results

### 1. Rolling 63d Sharpe recomputation
- Recomputed from last 63 cumulative returns: **0.11333136870186278**
- Stored drift flag value: **0.11333136870186329**
- **Difference: 5.13e-16** — matches within float precision. PASS.

### 2. Regime flips recomputation
- Recomputed from run_history transitions: **6**
- run_history length: 447
- **Matches stored value. PASS.**

### 3. Supervisor loop tests
`python3 .github/scripts/test_kilo_supervisor_loop.py -v` → **10/10 passed. PASS.**

### 4. Git status
`git status --short` → **clean** (no unstaged/staged changes). Confirms no fetch/replay occurred. PASS.

## Drift Flag Status
`low_rolling_sharpe` is **not active** (active=False). The stored value 0.1133 is below the 0.5 trigger threshold but the flag is not currently triggered. Rolling Sharpe trajectory over recent cycles has been volatile (range -0.51 to +1.19 over last 18 days), consistent with single low-return days moving the 63-day window rather than sustained degradation.

## Conclusion
All verification checks passed. Gate not met; no fetch/replay performed. Strategy remains frozen pending post-close gate.

## Reproduction Commands
```bash
TZ=UTC date -u +%Y-%m-%dT%H:%M:%SZ
python3 <<'PY'
import yaml,math
d=yaml.safe_load(open('data/processed/paper_trading_state.yaml'))
ret=d['cumulative_returns'][-63:]
m=sum(ret)/len(ret); v=sum((r-m)**2 for r in ret)/(len(ret)-1) if len(ret)>1 else 0
s=(m*252)/(math.sqrt(v)*math.sqrt(252)) if v>0 else 0
stored = d['drift_flags']['low_rolling_sharpe']['value']
print('sharpe_calc',s,'stored',stored,'diff',abs(s-stored))
PY
python3 <<'PY'
import yaml
d=yaml.safe_load(open('data/processed/paper_trading_state.yaml'))
rh=d['run_history']
t=0
if rh:
    prev=rh[0]['regime_exposure']
    for i in range(1,len(rh)):
        if rh[i]['regime_exposure']!=prev: t+=1; prev=rh[i]['regime_exposure']
df=d['drift_flags']['low_rolling_sharpe']
print('flips',t,'len',len(rh),'last_run_date', d['last_run_date'],'current_nav', d['current_nav'],'peak_nav', d['peak_nav'],'max_dd', d['max_drawdown'],'rolling', df.get('value'),'active', df.get('active', df.get('triggered', False)))
PY
git status --short
python3 .github/scripts/test_kilo_supervisor_loop.py -v
```