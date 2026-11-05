# Sharpe 63d gross-vs-cost/turnover attribution (diagnostic, pre-gate corrective 350)

- **Date (UTC):** 2026-11-05T20:03Z (pre-gate; 22:00 UTC gate not released)
- **Purpose:** Address supervisor review-0006 advisory (decompose negative 63d Sharpe into gross vs cost/turnover drag) as a bounded diagnostic using existing repo data only. **Exploratory/diagnostic; not a promotion claim.**
- **Scope:** Read-only on `data/raw/` and canonical paper-trading state fields; no thresholds/gates/cost model/universe/clock-gate/config changes; no commit.

## Data sources (observed)
- `data/processed/paper_trading_state.yaml`: `cumulative_returns/dates` (462), `run_history` (462) includes per-day `turnover`, `daily_return`, `nav`; `turnover_median=0.0013997`, `turnover_p95=0.5`; `rolling_sharpe_63d=-0.872439579425076` (2026-11-04), persistence 6.
- `data/processed/paper_trading/daily_pnl_*.parquet` (461 files, 2025-01-02–2026-11-04): `date,daily_return,daily_pnl,nav` (net; no explicit gross/cost columns).
- Cost assumption reference (configs): e.g. `config/calendar_effects_001.yaml` / `config/commoditytrend_001.yaml` use `commission_bps=1.0, slippage_bps=2.0` (3 bps/unit of turnover). **The extender’s exact cost application is not re-derived here; this attribution uses an explicit 3 bps/unit assumption for sensitivity only.**

## 63-day window (ending 2026-11-04)
Computed from `daily_pnl_*.parquet` net `daily_return` (authoritative series for that store; n=63, 2026-08-06–2026-11-04):
- Net ann. return: **-7.12%**, net ann. vol: **8.57%**, net 63d Sharpe: **-0.831** (close to drift/state -0.872; small method/date-boundary differences possible).

Computed from state `cumulative_returns` (different scale/base) gives Sharpe **+0.405** over 2026-08-07–2026-11-04 — **material discrepancy** vs daily_pnl/drift. This diagnostic treats daily_pnl/drift as the operative negative-Sharpe signal and flags the cumulative_returns-vs-daily_pnl inconsistency as a **data/metric-integrity follow-up** (out of scope to change here).

## Approximate cost/turnover sensitivity (assumption-bound)
Using `run_history` daily turnover aligned to the 63d window and **assumed** cost = `turnover * 3 bps` (commission+slippage, per config convention): observed `mean_daily_turnover=0.04692`, estimated annualized cost drag `~0.00355` (~0.36%/yr) vs net annualized return `~-7.12%/yr`. Estimated cost drag is **small** relative to the negative net return, implying the recent 63d negative Sharpe is **not explained solely by transaction costs under this assumption** — performance drag dominates (directional). **Caveat:** without per-day gross returns and the extender’s exact cost path, “gross Sharpe” cannot be asserted.

## Conclusion (diagnostic)
- Negative 63d Sharpe persists (persistence 6) per drift/state/daily_pnl.
- Under a 3 bps/unit turnover cost assumption, turnover/cost drag appears insufficient to explain the full drawdown in the 63d window; **performance drag dominates** (directional).
- **Integrity flag:** state `cumulative_returns`-derived Sharpe differs materially from `daily_pnl`/drift — reconcile metric sources in a separate bounded task.
- No changes to strategy, gates, thresholds, cost model, or state.

## Reproduction (read-only)
```python
import glob, pandas as pd, numpy as np, yaml
files=sorted(glob.glob('data/processed/paper_trading/daily_pnl_*.parquet'))
allp=pd.concat([pd.read_parquet(f) for f in files]).sort_values('date').drop_duplicates('date')
w=allp.tail(63); r=w['daily_return']; print('net_sharpe', r.mean()/r.std(ddof=1)*np.sqrt(252))
with open('data/processed/paper_trading_state.yaml') as f: s=yaml.safe_load(f)
rh=pd.DataFrame(s['run_history']); rh['date']=pd.to_datetime(rh['date'])
m=rh.merge(allp[['date']].assign(date=pd.to_datetime(allp['date'])),on='date').tail(63)
cost_assumed_bps=3.0; m['cost_drag']=m['turnover']*cost_assumed_bps/10000
print('mean_daily_turnover', m['turnover'].mean(), 'ann_cost_drag_est', m['cost_drag'].mean()*252)
```

CORRECTIVE_VERIFICATION context: pre-gate; this artifact is the durable evidence-supported correction for invocation 350.
