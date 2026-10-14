# Paper Trading Performance Drift Analysis

**Date:** 2026-07-16
**Strategy:** tsmomentum_spytrend_001 (frozen incumbent)
**State File:** `data/processed/paper_trading_state.yaml`
**Config:** `config/simulation_candidate_001.yaml`

---

## 1. Performance Decomposition

### Track Record Summary
- **Period:** 2025-01-02 → 2026-07-16 (384 trading days)
- **Peak NAV:** $139,120.07 (2026-06-02)
- **Current NAV:** $134,844.60 (2026-07-16)
- **Max Drawdown:** -3.07% (from peak)
- **Rolling 63-day Sharpe:** 0.3495 (threshold: 0.5) → **DRIFT FLAG TRIGGERED**

### Key Performance Phases

| Phase | Dates | Duration | Regime | Net Return | Notable Events |
|-------|-------|----------|--------|------------|----------------|
| Early ramp-up | 2025-01-02 → 2025-03-10 | ~50 days | Risk-on | +3.9% | Consistent positive returns |
| **Risk-off (cash)** | **2026-03-19 → 2026-04-06** | **14 days** | **Risk-off** | **0.0%** | SPY < 200-day SMA, zero positions |
| Re-entry & volatility | 2026-04-08 → 2026-06-02 | ~40 days | Risk-on | +6.2% | Peak NAV reached 2026-06-02 |
| **Drawdown cluster** | **2026-06-03 → 2026-07-16** | **~32 days** | **Risk-on** | **-3.1%** | Multiple large negative days |

### Largest Negative Days (Drawdown Cluster)
| Date | Daily Return | Daily PnL | Vol Scale | Regime |
|------|-------------|-----------|-----------|--------|
| 2026-06-05 | -2.43% | -$3,366 | 0.524 | Risk-on |
| 2026-06-10 | -1.14% | -$1,540 | 0.508 | Risk-on |
| 2026-06-23 | -1.37% | -$1,891 | 0.464 | Risk-on |
| 2026-07-13 | -1.01% | -$1,376 | 0.451 | Risk-on |
| 2026-07-16 | -0.65% | -$887 | 0.451 | Risk-on |

### Rolling Sharpe Trajectory
- Peak rolling 63-day Sharpe: ~0.94 (early 2026)
- Steady decline from ~0.8 (April) → 0.55 (late May) → 0.35 (mid-July)
- The 63-day window now primarily captures the Jun–Jul drawdown cluster

---

## 2. Market Context

### Regime Filter Behavior (SPY 200-day SMA)
- **Risk-on periods:** Strategy fully invested (regime_exposure = 1.0, n_positions = 4)
- **Risk-off period (2026-03-19 → 2026-04-06):** SPY fell below 200-day SMA; strategy correctly moved to cash (regime_exposure = 0.0, n_positions = 0)
- **Re-entry:** 2026-04-08 — SPY crossed back above SMA; full exposure restored

### Volatility Targeting Response
- Vol scale dropped from 1.0 → ~0.45–0.55 during Apr–Jul 2026
- This reflects rising realized 63-day volatility in the universe
- Position sizing was automatically reduced, but not enough to prevent the drawdown cluster

### Universe Composition (as of 2026-07-16)
- **Active positions (4):** QQQ, IWM, GLD, EEM (~11.3% each, equal-weight top 50%)
- **Excluded (3):** SPY, TLT, EFA (bottom 50% by 226-day momentum minus 21-day skip)

---

## 3. Strategy Mechanics Verification

### Config Compliance (`config/simulation_candidate_001.yaml`)
| Component | Spec | Verified in State |
|-----------|------|-------------------|
| Universe | 7 ETFs (SPY, QQQ, IWM, TLT, GLD, EFA, EEM) | ✅ All 7 tracked |
| Signal | TSMOM, lookback=226, skip=21, top_fraction=0.5 | ✅ 4/7 positions active |
| Rebalance | Monthly | ✅ Turnover spikes ~monthly (0.5 = full rotation) |
| Regime filter | SPY 200-day SMA, binary (0/1) | ✅ Cash 2026-03-19→04-06; invested otherwise |
| Vol target | 10% ann., 63-day lookback | ✅ Vol scale 0.45–1.0 range |
| DD control | 15% threshold, 50% reduction | ✅ Max DD -3.07% < 15%; dd_scale = 1.0 throughout |
| Costs | 3 bps round-trip | ✅ Embedded in PnL |
| Execution | T-1 close signal, daily rebalance | ✅ Consistent with replay |

### No Deviations Found
- All run_history entries match the frozen config specification
- Regime filter triggered exactly once (correctly)
- Volatility scaling operated within bounds
- Drawdown control never activated (max DD well below 15% threshold)
- Turnover median 0.089%, p95 50% (monthly rebalance spikes)

---

## 4. Drift Flag Root Cause

**Primary driver:** A cluster of 5 large negative days within a 32-day window (Jun 5 – Jul 16), all during risk-on regime, where the strategy was fully invested but volatility targeting had reduced gross exposure to ~45–55%.

**Contributing factors:**
1. **Momentum signal decay:** The 226-day lookback with 21-day skip captured the late-2025 rally but the Jun–Jul 2026 period saw mean-reversion / choppy returns in the top-4 assets
2. **Vol targeting lag:** 63-day realized vol window reacts slowly; vol_scale was still declining when the largest losses occurred
3. **No regime protection:** SPY remained above 200-day SMA throughout (risk-on), so no regime-based risk reduction

**Not a structural failure:** The strategy behaved exactly as specified. The drift flag reflects a genuine (but not yet statistically significant) deterioration in recent risk-adjusted returns, not a mechanics error.

---

## 5. Confirmation: No Strategy Modifications

- **No parameter changes** made to `config/simulation_candidate_001.yaml`
- **No logic changes** to any backtest/execution code
- **No new backtests** or candidate variants created
- **Analysis only** — read-only inspection of state and config

---

## 6. Test Verification

```bash
python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v
```
**Result:** 10/10 tests PASSED (0.46s)

---

## 7. Conclusion

The low rolling Sharpe (0.3495 vs 0.5 threshold) is driven by a concentrated drawdown cluster in June–July 2026 during a risk-on regime where the strategy was fully invested. The SPY 200-day SMA regime filter correctly kept the strategy in cash during the March–April 2026 risk-off period, but provided no protection during the subsequent choppy risk-on phase. Volatility targeting reduced exposure but with a lag.

**Recommendation:** Continue monitoring. The drift flag has persisted for 1 day (as of 2026-07-16); the >20-day persistence threshold for action has not been met. No strategy modification warranted at this time — the behavior is consistent with the validated specification.

---

**Files Inspected:**
- `data/processed/paper_trading_state.yaml` (full 384-day history)
- `config/simulation_candidate_001.yaml` (frozen incumbent config)
- `research/experiments/tsmomentum_regime_filter_wf_001.md` (original validation evidence)