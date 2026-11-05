# Sharpe 63d gross-vs-cost/turnover attribution (corrected — invocation 351)

- **Date (UTC):** 2026-11-05T20:42Z (pre-gate; 22:00 UTC gate NOT released)
- **Purpose:** Re-execute supervisor review-0006 advisory (decompose negative 63d
  Sharpe into gross vs cost/turnover drag) using the **canonical state as the
  authoritative source**, correcting the methodological error in the prior
  diagnostic (invocation 350). **Exploratory/diagnostic; not a promotion claim.**
- **Scope:** Read-only on `data/processed/paper_trading_state.yaml` and
  `data/processed/paper_trading/daily_pnl_*.parquet`. No thresholds/gates/cost
  model/universe/clock-gate/config changes. No commit. No `data/raw` access.

## Correction of the invocation-350 error

The prior report (`sharpe63d_gross_vs_cost_attribution_350.md`) treated
`state.cumulative_returns` as a cumulative NAV series and reported a
"material discrepancy" between a cumulative-derived Sharpe (+0.405) and the
daily_pnl-derived Sharpe (-0.831). **That discrepancy was a methodological
error, not a data-integrity fault.**

Empirical verification (this invocation):
- `state.cumulative_returns` is a **daily return series**, not a NAV series.
- Aligning it against `daily_pnl.daily_return` (461 matched rows):
  `max abs diff = 0.0` — the two series are **identical**.
- The prior report's +0.405 figure came from taking `pct_change()` of an
  already-daily-return series (double-differencing), which produced a
  nonsensical result (ann. ret ~1949%). **Retracted.**

**There is no cumulative_returns-vs-daily_pnl metric inconsistency.** The
field is merely misnamed relative to its content.

## Authoritative 63-day window (ending 2026-11-04)

Computed from `state.cumulative_returns` / `state.cumulative_dates` using the
repository's canonical convention (`sharpe_ratio`, arithmetic annualised rf=0),
which is the same estimator the live drift flag uses. Window = the trailing 63
sessions: **2026-08-07 → 2026-11-04, n = 63.**

- Net annualised return: **-7.49%**
- Net annualised vol: **8.58%**
- **Net 63d Sharpe: -0.8724** — matches `state.rolling_sharpe_63d`
  (-0.872439579425076) and the recomputed `drift.last_sharpe` exactly
  (`stored_matches_recomputed == True`).

## Cost / turnover decomposition

Turnover aligned from `state.run_history` over the same 63 sessions
(63/63 rows matched). Cost model: **3 bps per unit of turnover**
(commission 1.0 bps + slippage 2.0 bps, per `config/calendar_effects_001.yaml`
/ `config/commoditytrend_001.yaml` convention). Net returns in this model are
already net of cost, so gross = net + cost_backed_out.

| Metric | Value |
|---|---|
| Mean daily turnover (63d window) | 0.04721 |
| Mean daily cost drag | 1.416e-05 |
| **Annualised cost drag** | **0.00357 (0.357%/yr)** |
| Net annualised return | -7.49% |
| **Gross 63d Sharpe** | **-0.8308** |
| **Net 63d Sharpe** | **-0.8724** |
| Cost drag as % of \|net ann. ret\| | **4.8%** |

Turnover distribution over full history: median 0.00140, p95 0.50.

## Conclusion

- The negative 63d Sharpe (-0.8724, persistence 6) is **overwhelmingly driven by
  directional performance drag**, not by transaction costs. Backing out the
  3 bps/unit cost assumption raises the Sharpe only from -0.8724 to -0.8308;
  cost drag accounts for ~4.8% of the magnitude of the negative annualised
  return.
- Under this cost model, **turnover/cost is not a credible explanation for the
  drawdown**. The strategy is simply in a losing directional period.
- **Data-integrity note (minor, non-blocking):** the `daily_pnl_*.parquet` store
  (461 rows) is missing the 2026-11-02 session that the canonical state
  (`cumulative_dates`/`run_history`, 462 rows) contains. The state is the
  authoritative source for all metrics above; the parquet store gap does not
  affect any Sharpe or persistence figure. Flagged for a separate bounded
  storage-reconciliation task.
- No changes to strategy, gates, thresholds, cost model, or state.

## Reproduction (read-only)

```python
import yaml, pandas as pd, numpy as np, glob
from src.evaluation.sharpe import sharpe_ratio
with open('data/processed/paper_trading_state.yaml') as f: s=yaml.safe_load(f)
dates=[str(d) for d in s['cumulative_dates']]
returns=[float(r) for r in s['cumulative_returns']]
rh=pd.DataFrame(s['run_history']); rh['date']=pd.to_datetime(rh['date'])
ser=pd.Series(returns, index=pd.to_datetime(dates))
w=ser.tail(63); r=w.values
rhw=rh[rh['date'].isin(w.index)].sort_values('date')
cost=rhw['turnover']*3.0/10000
gross=r+cost.values
print('net_sharpe', sharpe_ratio(r), 'gross_sharpe', sharpe_ratio(gross))
print('ann_cost_drag', cost.mean()*252, 'mean_turnover', rhw['turnover'].mean())
```

CORRECTIVE_VERIFICATION context: pre-gate; this artifact is the durable
evidence-supported correction for invocation 351, materially different from
350 (which contained the double-differencing error).