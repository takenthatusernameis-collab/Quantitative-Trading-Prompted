# Paper Trading Validation Report - Cycle 140

## UTC Session Time
2026-10-15T15:08:21Z

## Post-Close Gate Evaluation
- **Gate Time:** 2026-10-17T20:00:00Z
- **Session Time:** 2026-10-15T15:08:21Z
- **Result:** GATE NOT MET (session_time < gate_time)

Session time is before the post-close gate. No fetch or replay performed per protocol.

## Fetch Results
Not attempted — gate not met. Data state unchanged: `last_run_date` = 2026-10-14 in `data/processed/paper_trading_state.yaml`; raw parquet max dates remain 2026-10-14 for the 7 incumbent ETFs (per prior cycles' per-symbol verification).

## Track Record Status (Unchanged)
- **Track Record Days:** 447 days (2025-01-02 → 2026-10-14)
- **NAV:** $135,043.35
- **Peak NAV:** $139,120.07
- **Sharpe Ratio:** 1.9272
- **Max Drawdown:** -2.93%
- **Rolling 63-Day Sharpe:** 0.1133
- **Drift Flag:** Persists — `low_rolling_sharpe` value 0.11333136870186329 (threshold 0.5) at date 2026-10-14; 3 consecutive days flagged (2026-10-12, 2026-10-13, 2026-10-14), not yet at >20-day persistence threshold
- **Regime:** Risk-on (132 consecutive days at session end)
- **Regime flips:** 6 (over 447 run_history entries)

## Verification Results

### 3. Independent Rolling-63-Day Sharpe Verification
Command:
```bash
python3 -c "
import yaml,math
d=yaml.safe_load(open('data/processed/paper_trading_state.yaml'))
ret=d['cumulative_returns'][-63:]
m=sum(ret)/len(ret); v=sum((r-m)**2 for r in ret)/(len(ret)-1); s=(m*252)/(math.sqrt(v)*math.sqrt(252)) if v>0 else 0
print('sharpe',s,d['drift_flags']['low_rolling_sharpe']['value'])
"
```
- Computed from last 63 cumulative returns: 0.11333136870186278
- Stored value in state.drift_flags.low_rolling_sharpe.value: 0.11333136870186329
- Difference: 5.13e-16 (within float precision)
- **Status:** MATCH (within float precision)

### 4. Regime Flip Verification
Command:
```bash
python3 -c "
import yaml
d=yaml.safe_load(open('data/processed/paper_trading_state.yaml'))
rh=d['run_history']; t=0; prev=rh[0]['regime_exposure']
for i in range(1,len(rh)):
  if rh[i]['regime_exposure']!=prev: t+=1; prev=rh[i]['regime_exposure']
print('flips',t,len(rh))
"
```
- Regime flips from run_history.regime_exposure transitions: 6
- Number of run_history entries: 447
- Expected value (from context): 6
- **Status:** MATCH

### 5. Supervisor Loop Tests
- Command: `python3 .github/scripts/test_kilo_supervisor_loop.py -v`
- Result: `Ran 10 tests in 0.417s — OK`
- Tests passed: 10/10
- **Status:** ALL TESTS PASSED

## Notes
- No fetch or replay performed; gate not met (session 2026-10-15T15:08:21Z precedes gate 2026-10-17T20:00:00Z).
- All independent verifications matched stored values (rolling 63-day Sharpe diff 5.13e-16; regime flips 6/447).
- Supervisor loop tests passed 10/10.
- Track record unchanged from Cycle 139.
- Same post-close gate preserved for next cycle: 2026-10-17T20:00:00Z.
- Validation completed at session time: 2026-10-15T15:08:21Z.
