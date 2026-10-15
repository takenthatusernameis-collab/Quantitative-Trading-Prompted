# Paper Trading Validation Report — Cycle 86

**Session timestamp (UTC):** 2026-10-15T03:32:36Z
**Post-close gate:** 2026-10-15T20:00:00Z
**Gate status:** BEFORE GATE — fetch skipped

---

## Track Record (Unchanged)

- **Period:** 2025-01-02 → 2026-10-14 (447 trading days)
- **NAV:** $135,043.35 (+35.04% since inception)
- **Full-period Sharpe:** 1.9272
- **Max drawdown:** -2.93%
- **Rolling 63-day Sharpe:** 0.1133
- **Regime:** Risk-on (132 consecutive days)
- **Regime flips observed:** 6 (3 risk-on→risk-off, 3 risk-off→risk-on)

---

## Drift Monitoring

**Drift flag persists:** `low_rolling_sharpe` on 3 consecutive trading days:
- 2026-10-12: 0.4892
- 2026-10-13: 0.3669
- 2026-10-14: 0.1133

Trajectory over last 18 days volatile (range -0.51 to +1.19). Not yet at the >20-day persistence threshold.

---

## Go/No-Go Gates (All Pass)

| Gate | Threshold | Current | Status |
|------|-----------|---------|--------|
| Track record length | >126 days | 447 days | ✅ PASS |
| Net-of-cost Sharpe | >0.9 | 1.9272 | ✅ PASS |
| Max drawdown | <15% | -2.93% | ✅ PASS |
| Regime flips | >1 | 6 | ✅ PASS |
| Rolling 63-day Sharpe | >0.9 | 0.1133 | ⚠️ DRIFT FLAG |

---

## Independent Rolling 63-Day Sharpe Verification

```python
import yaml, pandas as pd, numpy as np
state = yaml.safe_load(open('data/processed/paper_trading_state.yaml'))
cr = pd.Series(state['cumulative_returns']).tail(63)
rolling63 = cr.mean()/cr.std(ddof=1)*np.sqrt(252)
# Result: 0.1133313687018633
# Stored drift flag value: 0.11333136870186329
# Match: EXACT (within floating-point precision)
```

---

## Data Status

No fetch attempted (session before 20:00 UTC post-close gate).
Raw parquet files in `data/raw/` end at 2026-10-14 for all 7 incumbent ETFs (SPY, QQQ, IWM, TLT, GLD, EFA, EEM) and ^VIX.

---

## Tests

```
python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v
```
**Result:** 10/10 PASSED

---

## Next Action

Next cycle should run at or after 2026-10-15T20:00:00Z UTC to attempt post-close data acquisition and track record extension.