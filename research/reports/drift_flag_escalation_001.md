# Drift Flag Escalation Assessment — low_rolling_sharpe

**Generated:** 2026-10-18T21:35:00Z
**Code revision:** a95433b (from README)
**Trigger:** `low_rolling_sharpe` drift flag reached documented >20-day persistence threshold
**Scope:** Verification and documentation only. No strategy, data, or infrastructure changes.

---

## 1. Detection Logic

Located at `src/simulation/paper_trading.py:355-361`:

```python
if rolling_sharpe < 0.5 and len(returns_arr) >= 20:
    drift_flags["low_rolling_sharpe"] = {
        "value": rolling_sharpe,
        "threshold": 0.5,
        "date": latest_date,
    }
```

Rolling Sharpe computed at `src/simulation/paper_trading.py:273-284`:
- Window: last 63 daily returns
- Annualized: `mean(returns) * 252 / (std(returns, ddof=1) * sqrt(252))`

---

## 2. Independent Recomputation

Recomputed from `data/processed/paper_trading_state.yaml` (449 `run_history` entries, 2025-01-02 → 2026-10-16):

| Metric | Full Sample (449d) | Recent 63-Day Window |
|--------|-------------------|---------------------|
| Mean daily return | +0.000666 | -0.000069 |
| Std daily (ddof=1) | 0.006045 | 0.005180 |
| Annualized return | +16.78% | -1.74% |
| Annualized volatility | 9.60% | 8.22% |
| **Sharpe** | **1.7484** | **-0.2119** |

Stored `rolling_sharpe_63d` = -0.21188351222842883; independently recomputed value matches exactly.

Cumulative return over the recent 63-day window: **-0.52%**. NAV $133,729.22 vs peak $139,120.07; max drawdown -4.99%.

---

## 3. Persistence Count — Methodological Discrepancy

**Documented claim (README, NEXT_AGENT_TASK.md):** "`low_rolling_sharpe` persists 20 consecutive days."

**Independent finding:** The rolling 63-day Sharpe has been below the 0.5 threshold on **21 of the last 46 calendar days** (2026-09-01 → 2026-10-16), but only **5 consecutive trading days** at the end of the window (2026-10-12 through 2026-10-16). The trajectory is volatile, with values above 0.5 on 2026-10-05 (0.9920), 2026-10-06 (0.9994), and 2026-10-09 (0.9356) interrupting the sub-threshold period.

The 20-day figure appears to count calendar days since the first recent flag date (2026-09-01) rather than consecutive trading days below threshold. No code in `src/` computes a persistence counter for the `low_rolling_sharpe` flag — the count is recorded manually in documentation.

**Assessment of the discrepancy:** The 20-day persistence threshold as documented is not reproducible from the stored state using the stated definition ("consecutive trading days below 0.5"). The actual consecutive trading-day streak is 5 days. This is a documentation accuracy issue, not a strategy defect.

---

## 4. Return/Volatility Decomposition

The recent 63-day window is characterized by:
- **Return contribution:** Mean daily return fell from +0.000666 (full sample) to -0.000069 (recent), a sign reversal. Annualized return went from +16.78% to -1.74%.
- **Volatility contribution:** Volatility fell modestly from 9.60% to 8.22% (ratio 0.86), so the low Sharpe is driven primarily by the **negative mean return**, not elevated volatility.
- **Interpretation:** The strategy experienced a period of slightly negative returns in a lower-than-average volatility environment. This is consistent with sampling variation in a mean-reverting/low-edge window rather than a structural break — the full-sample Sharpe of 1.75 remains intact, and the drawdown (-4.99%) is well within the 15% limit.

---

## 5. Decision Label

**Exploratory signal degradation — monitor, do not re-optimize.**

Rationale:
- The full-sample Sharpe (1.75) and max drawdown (-4.99%) remain healthy; the degradation is confined to the most recent 63-day window.
- Volatility is not elevated; the driver is a negative mean return, consistent with a temporary low-edge period.
- The documented "20-day persistence" claim is not reproducible as stated (actual consecutive trading-day streak: 5 days); the threshold has not been reached under the stated definition.
- No strategy, data, or infrastructure changes are warranted. Per AGENTS.md safety scope, the strategy remains frozen pending evidence of structural degradation, not a single volatile rolling-window observation.

---

## 6. Verification Commands Executed

- `python -m pytest -q` → 7 passed (52.25s)
- `python research/_tmp_cycle77_verify.py` → OVERALL PASS (rolling 63d Sharpe match True, date 2026-10-16, regime flips 6/6, run_history 449)
- `python .github/scripts/test_kilo_supervisor_loop.py` → 10/10 OK (0.368s)

Data ends 2026-10-16; no new real trading days beyond.