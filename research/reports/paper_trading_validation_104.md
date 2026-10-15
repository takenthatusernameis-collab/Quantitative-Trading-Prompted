# Paper Trading Validation Report - Cycle 104

## UTC Session Time
2026-10-15T13:05:34Z

## Gate Time
2026-10-17T20:00:00Z

## Gate Result
**NOT MET** (session_time < gate_time)

## Verifications (Run Despite Gate Not Met)

### 3. Independent Rolling-63-Day Sharpe Verification
- Computed rolling 63-day Sharpe: 0.11333136870186278
- Stored low_rolling_sharpe.value: 0.11333136870186329
- **MATCH** (difference ~5e-16, within floating-point precision)

### 4. Regime Flip Verification
- Computed regime flips from run_history: 6
- Stored regime flips (from context): 6
- **MATCH**

## Actions Taken
- No fetch or replay performed (gate not met).
- No changes to paper trading state or history.

## Next Steps
Leave the same task (Cycle 104) for the next agent session; the gate remains unchanged.

## Validation Commands Reference
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
```