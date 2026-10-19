# Deployment Dossier for tsmomentum_spytrend_001

**Candidate:** tsmomentum_spytrend_001 (TSMOM + SPY-trend-filter + risk overlays)
**Deployment Preparation Date:** 2026-10-14
**Based on:** Cycle 6 walk-forward validation, Cycles 8-21 paper trading validation, Cycle 22 go/no-go evaluation
**Decision:** GO for live deployment (subject to standard operational controls)

---

## 1. Final Validated Strategy Specification

### 1.1 Strategy Identity
- **Candidate ID:** tsmomentum_spytrend_001
- **Config SHA-256[:12]:** 76a8c320b25b (from `config/simulation_candidate_001.yaml`)
- **Strategy Type:** Time-series momentum with regime filter and risk overlays
- **Asset Universe:** 7 liquid ETFs (SPY, QQQ, IWM, TLT, GLD, EFA, EEM)

### 1.2 Signal Parameters (Frozen)
| Parameter | Value | Description |
|-----------|-------|-------------|
| Signal Type | tsmomentum | Time-series momentum |
| Lookback | 226 trading days | ~12-month momentum window |
| Skip | 21 trading days | ~1-month short-term reversal skip |
| Top Fraction | 0.5 | Equal-weight top 50% by momentum |
| Rebalance Frequency | monthly | Signal horizon (~21 trading days) |

### 1.3 Risk Overlays (Frozen)
| Parameter | Value | Description |
|-----------|-------|-------------|
| Volatility Target | 10% annual | Annualized volatility target |
| Volatility Lookback | 63 trading days | Trailing realized-vol window |
| Max Leverage | 1.0 | Gross exposure cap (no leverage) |
| DD Control Threshold | 15% | Drawdown threshold triggering reduction |
| DD Control Reduction | 50% | Exposure multiplier while in drawdown |

### 1.4 Regime Filter (Frozen)
| Parameter | Value | Description |
|-----------|-------|-------------|
| Filter Type | spy_sma | SPY 200-day SMA trend filter |
| Window | 200 trading days | Long-term trend determination |
| Exposure Below SMA | 0.0 | Move to cash when SPY < SMA |
| Exposure Above SMA | 1.0 | Full exposure when SPY ≥ SMA |

### 1.5 Cost Model (Frozen)
| Component | Value | Notes |
|-----------|-------|-------|
| Commission | 1.0 bps/trade | Conservative estimate for liquid ETFs |
| Slippage | 2.0 bps/trade | Includes market impact |
| Round-trip Total | 3.0 bps | Applied on weight changes |

### 1.6 Execution Parameters (Frozen)
| Parameter | Value | Description |
|-----------|-------|-------------|
| Signal Lag | 1 day | Signal computed on T-1 close |
| Price Field | Close | EOD pricing (validated convention) |
| Timezone | UTC | Execution timezone |
| Rebalance Schedule | daily | Daily weight adjustment (vol targeting) |

### 1.7 Paper Trading Configuration (Operational)
| Parameter | Value | Source |
|-----------|-------|--------|
| Notional Capital | $100,000 | Display/scaling reference |
| Data Refresh | Daily at 16:00 ET | Yahoo Finance cache |
| Alert: Regime Flip | Enabled | Detect SPY SMA crossovers |
| Alert: Vol Scale Max | 2.0 | Volatility targeting upper bound |
| Alert: DD Scale Min | 0.25 | Drawdown control lower bound |
| Alert: Turnover Pct | 50% | Daily turnover alert threshold |
| Alert: Max Drawdown | 10% | Paper drawdown alert |
| Go/No-Go Min Days | 63 | Minimum track record |
| Go/No-Go Target Sharpe | 0.9 | Rolling 63-day Sharpe |
| Go/No-Go Max DD | 15% | Maximum drawdown threshold |

---

## 2. Live Trading Infrastructure Requirements

### 2.1 Market Data Feed
| Requirement | Specification | Notes |
|-------------|---------------|-------|
| Data Source | Real-time ETF quotes (SPY, QQQ, IWM, TLT, GLD, EFA, EEM) | Primary: IBKR, Polygon.io, or similar |
| Frequency | Daily OHLCV (minimum) | Intraday not required for daily rebalancing |
| History | 1+ year for indicator warmup | 200-day SMA requires ~1 year |
| Point-in-Time | Critical: no lookahead bias | Signal must use only data available at T-1 close |
| Failover | Secondary provider required | Redundancy for production |
| SPY Price | Required for regime filter | Must be available before signal generation |

### 2.2 Brokerage / Execution
| Requirement | Specification | Notes |
|-------------|---------------|-------|
| Broker | IBKR, Alpaca, or similar API-enabled broker | Must support 7 ETFs |
| Account Type | Margin (for cash management) | No leverage used (max 1.0) |
| Order Types | Market on Open (MOO) or Market on Close (MOC) | Match Close-to-close or Open-to-close assumption |
| Execution Time | Next-day open (T) for T-1 close signal | 1-day signal lag per validated model |
| Commission | ≤ 1 bps (negotiated) | Must not exceed cost model assumption |
| Slippage | ≤ 2 bps typical | Validate with live fills |
| Settlement | T+2 (standard) | Cash management for daily rebalancing |

### 2.3 Risk Management Systems
| Component | Specification | Notes |
|-----------|---------------|-------|
| Pre-trade Checks | Gross exposure ≤ 1.0, per-symbol limits | Enforce max leverage |
| Volatility Targeting | Daily position scaling to 10% ann. vol | Use 63-day realized vol |
| Drawdown Control | Reduce exposure 50% if DD > 15% | From peak NAV |
| Regime Filter | SPY 200-day SMA (compute pre-market) | Move to cash if SPY < SMA |
| Real-time Monitoring | Rolling 63d Sharpe, DD, turnover, regime | Alert on threshold breaches |
| Kill Switch | Manual override to flatten all positions | Emergency stop |

### 2.4 Technology Stack
| Layer | Recommendation | Notes |
|-------|----------------|-------|
| Language | Python 3.10+ | Match research environment |
| Data Handling | pandas, numpy | Existing simulation engine |
| Scheduling | cron / systemd / Airflow | Daily at market close + pre-market |
| State Persistence | SQLite or PostgreSQL | Audit trail, replay capability |
| Logging | Structured JSON logs | ELK/Grafana integration |
| Alerting | PagerDuty, Slack, email | For drift flags and regime flips |
| CI/CD | GitHub Actions or similar | Reproducible deployment |

### 2.5 Operational Requirements
| Requirement | Specification |
|-------------|---------------|
| Uptime | 99.9% on trading days |
| Recovery Time Objective (RTO) | < 1 hour |
| Recovery Point Objective (RPO) | < 1 day (daily state snapshots) |
| Backup | Daily state + config + code versioned |
| Audit Trail | Immutable log of all signals, orders, fills |
| Version Control | Config SHA-256 tracked with each deployment |

---

## 3. Live Monitoring and Validation Protocol

### 3.1 Daily Monitoring Checklist (Pre-Market)
- [ ] Verify data feed health (all 7 ETFs + SPY)
- [ ] Compute SPY 200-day SMA and regime exposure
- [ ] Generate TSMOM signals for each asset (lookback=226, skip=21)
- [ ] Apply top-fraction filter (50%)
- [ ] Compute 63-day realized volatility per asset
- [ ] Calculate volatility-targeted weights (10% ann. vol target)
- [ ] Apply drawdown control (if DD > 15%, scale 50%)
- [ ] Apply regime filter (exposure = 0.0 if SPY < SMA)
- [ ] Check for drift flags (turnover, vol_scale, dd_scale, regime persistence)
- [ ] Generate target portfolio weights
- [ ] Submit orders for next-day open execution

### 3.2 Daily Monitoring Checklist (Post-Market)
- [ ] Record fills and actual execution prices
- [ ] Calculate realized daily P&L (mark-to-market)
- [ ] Update NAV, peak NAV, drawdown
- [ ] Update rolling 63-day Sharpe and max DD
- [ ] Update regime persistence counter
- [ ] Check all drift alert thresholds
- [ ] Save daily state (YAML + parquet artifacts)
- [ ] Generate daily rolling report
- [ ] Archive all artifacts with date stamp

### 3.3 Drift Alert Thresholds (Live)
| Alert | Threshold | Action |
|-------|-----------|--------|
| Regime Flip | SPY crosses 200-day SMA | Notify; verify signal logic |
| Vol Scale Max | > 2.0 | Notify; check vol estimation |
| DD Scale Min | < 0.25 | Notify; verify drawdown control |
| Signal Turnover | > 50% daily | Notify; check for data errors |
| Max Drawdown | > 10% paper DD | Notify; review risk controls |
| Rolling 63d Sharpe | < 0.5 (after 20 days) | Notify; potential degradation |
| Regime Persistence | < 5 days after flip | Notify; potential whipsaw |
| Vol Scale Extreme | > 2.5 | Escalate; halt if persistent |
| DD Scale Extreme | < 0.2 | Escalate; halt if persistent |

### 3.4 Periodic Validation (Monthly)
- Compare live performance vs. paper trading / backtest expectations
- Verify cost model assumptions (actual commissions, slippage)
- Review regime filter effectiveness (capture/avoidance rates)
- Check capacity/liquidity (fill quality, market impact)
- Update rolling statistics and regime-segmented analysis
- Document any structural changes in market behavior

### 3.5 Quarterly Review
- Full go/no-go re-evaluation using live track record
- Statistical significance testing (PSR, DSR, bootstrap CIs)
- Regime filter parameter stability check
- Cost model recalibration
- Capacity assessment at current AUM
- Decision: Continue / Modify / Halt

### 3.6 Continued Paper Trading Shadow
- Run paper trading framework in parallel with live
- Compare live vs. paper daily (signal, weights, P&L)
- Any divergence > threshold triggers investigation
- Paper trading serves as drift detection baseline

---

## 4. Evidence Base Compilation

### 4.1 Validation Artifacts Summary
| Artifact | Location | Description |
|----------|----------|-------------|
| Go/No-Go Evaluation | `research/reports/go_nogo_evaluation_001.md` | Final decision document |
| Walk-Forward Validation | `research/experiments/tsmomentum_regime_filter_wf_001.md` | Cycle 6: 48 folds, 1993-2026 |
| Paper Trading (70d) | `research/reports/paper_trading_validation_001.md` | Cycle 20: Initial validation |
| Paper Trading (444d) | `research/reports/paper_trading_validation_002.md` | Cycle 21: Extended validation |
| Strategy Config | `config/simulation_candidate_001.yaml` | Frozen parameters |
| Paper Trading Config | `config/paper_trading_config.yaml` | Operational parameters |
| Simulation Engine | `src/simulation/engine.py` | Backtest/paper trading core |
| Paper Trading Engine | `src/simulation/paper_trading.py` | Prospective validation framework |
| Data Inventory | `research/reports/data_inventory.md` | Data sources and quality |
| State History | `data/processed/paper_trading_state.yaml` | 444-day track record |
| Daily Artifacts | `data/processed/paper_trading/` | 444 daily parquet files |
| Rolling Report | `research/reports/paper_trading_rolling.md` | Latest daily status |

### 4.2 Key Performance Evidence
| Metric | Walk-Forward (Cycle 6) | Paper Trading (444d) | Gate | Status |
|--------|------------------------|----------------------|------|--------|
| Mean OOS Sharpe | 0.9473 | 2.0548 (full) / 0.9356 (rolling) | ≥ 0.9 | ✅ PASS |
| % Positive Folds | 91.7% | 50.7% positive days | ≥ 50% | ✅ PASS |
| Max Drawdown | -5.41% (mean) | -4.99% | ≤ 15% | ✅ PASS |
| Regime Flips | N/A (backtest) | 6 | ≥ 1 | ✅ PASS |
| Track Record | 33+ years | 444 days | ≥ 126 days | ✅ PASS |
| Pooled OOS Trades | 6,013 | ~6.8x ann. turnover | > 100 | ✅ PASS |

### 4.3 Regime Filter Validation Evidence
- **3 complete risk-on/risk-off cycles** captured in 444-day paper trading
- **Risk-off periods (55 days):** 0% return, 0% volatility, 0% drawdown — perfect capital preservation
- **Risk-on periods (389 days):** Generated all returns, Sharpe 3.18 (longest streak), 0.92 (final period)
- **6 regime flips observed:** 3 down (risk-on→off), 3 up (risk-off→on)
- **No whipsaw losses:** Brief 2-day risk-on period generated small positive return
- **Transition latency:** 1-day signal lag incorporated in all results

### 4.4 Cost Model Validation
- **Assumed:** 3 bps round-trip (1 bp commission + 2 bp slippage)
- **Paper Trading Cost Drag:** ~2.1% annually on notional
- **Cost as % of Gross P&L:** 15% (444-day period with higher returns)
- **Actual Brokerage Commissions:** Must verify ≤ 1 bps in live
- **Actual Slippage:** Must verify ≤ 2 bps in live (liquid ETFs)

---

## 5. Decision Audit Trail

### 5.1 Hypothesis Evolution
| Cycle | Hypothesis | Outcome |
|-------|------------|---------|
| 1-2 | Baseline TSMOM (7 ETFs) | Positive but high drawdown |
| 3-5 | TSMOM + Risk Overlays (vol target, DD control) | Improved risk-adjusted returns |
| 6 | TSMOM + SPY-trend-filter (200-day SMA) | **Promoted: Credible Candidate** |
| 7 | Reproduction / Robustness | Confirmed Cycle 6 results |
| 8-9 | Paper trading initiation (70 days) | Insufficient regime diversity |
| 10 | Historical go/no-go replay | Framework validated |
| 11 | Data inventory | Confirmed data readiness |
| 12-13 | Cross-sectional momentum (C3) | **Rejected/Failed** |
| 14 | Sector rotation pre-reg (C4) | Pre-registered |
| 15 | Sector rotation eval (C4) | **Rejected/Failed** |
| 16 | Calendar effects pre-reg (C6) | Pre-registered |
| 17 | Calendar effects eval (C6) | **Rejected/Failed** |
| 18 | Macro regime overlay (C5) | Pre-registered |
| 19 | Macro regime eval (C5) | **Rejected/Failed** |
| 20 | Paper trading extension (70d) | Gates passed, low regime diversity |
| 21 | Paper trading extension (444d) | **All gates passed with margin** |
| 22 | Go/No-Go evaluation | **GO (with conditions)** |
| 23 | Deployment preparation | **This document** |

### 5.2 Falsification Conditions Tested
| Condition | Test | Result |
|-----------|------|--------|
| WF Mean OOS Sharpe < 0.9 | Cycle 6 (48 folds) | **Not met** (0.9473) |
| Positive Fold Rate < 50% | Cycle 6 | **Not met** (91.7%) |
| SMA Window Plateau < 100% | Cycle 6 (6 windows) | **Not met** (6/6 ≥ 0.9) |
| Paper Track Record < 126 days | Cycles 20-21 | **Not met** (444 days) |
| Paper Regime Flips < 1 | Cycle 21 | **Not met** (6 flips) |
| Rolling 63d Sharpe < 0.9 | Cycle 21 | **Not met** (0.9356) |
| Max DD > 15% | Cycle 21 | **Not met** (4.99%) |

### 5.3 Independent Reproduction Verification
- All backtests use deterministic engine with fixed seed (42)
- Config SHA-256 tracked for every evaluation
- Paper trading replay is deterministic on cached data
- Walk-forward splits are chronologically ordered with purging/embargo
- No lookahead bias: signals shifted 1 day, regime computed point-in-time

---

## 6. Risk Assessment for Live Deployment

### 6.1 Identified Risks (from Go/No-Go Report)
| Risk | Severity | Mitigation |
|------|----------|------------|
| Regime Filter Lag | Medium | 1-day lag in execution model; validated across 6 flips |
| Turnover Costs | Low | Cost model conservative (3 bps); actual drag ~2.1%/yr |
| Capacity Constraints | Low | Liquid ETFs, ~6.8x annual turnover manageable |
| Model Decay | Low-Medium | 33-year walk-forward + 444-day paper validation |
| Vol Targeting Path Dependency | Low | 63-day lookback standard; DD control provides backup |

### 6.2 Additional Live Deployment Risks
| Risk | Severity | Mitigation |
|------|----------|------------|
| Data Feed Failure | High | Dual provider failover; cached fallback |
| Broker API Outage | High | Order management with retry/idempotency |
| Execution Slippage > Model | Medium | Monitor live fills vs. 2 bps assumption |
| Corporate Actions | Low | ETFs handle splits/dividends automatically |
| Regulatory Changes | Low | Monitor SEC/ETF rule changes |
| Key Person Risk | Medium | Documented processes; automated execution |

---

## 7. Deployment Checklist

### 7.1 Pre-Deployment (Infrastructure)
- [ ] Provision production server / cloud instance
- [ ] Configure market data feeds (primary + backup)
- [ ] Set up brokerage API credentials (encrypted vault)
- [ ] Deploy simulation engine + paper trading framework
- [ ] Configure daily scheduler (pre-market signal gen, post-market reconciliation)
- [ ] Set up logging, monitoring, alerting (Slack/PagerDuty)
- [ ] Configure state persistence (DB + daily parquet/YAML backups)
- [ ] Run end-to-end test on historical data (reproduce paper trading)
- [ ] Validate cost model with broker commission schedule
- [ ] Document runbooks (startup, shutdown, emergency flatten)

### 7.2 Pre-Deployment (Validation)
- [ ] Verify config SHA-256 matches `76a8c320b25b`
- [ ] Confirm all 7 ETFs tradeable at broker
- [ ] Validate SPY 200-day SMA computation matches research
- [ ] Test regime flip detection logic
- [ ] Verify volatility targeting math (annualized 63-day realized vol)
- [ ] Confirm drawdown control triggers at 15% threshold
- [ ] Run parallel paper trading for 5+ days before going live
- [ ] Compare paper vs. live signals/weights daily

### 7.3 Go-Live
- [ ] Start with reduced notional (e.g., 25% target) for 20 trading days
- [ ] Monitor all drift alerts daily
- [ ] Verify fill quality (slippage, commission)
- [ ] Gradually scale to full notional after validation period
- [ ] Activate all monitoring alerts
- [ ] Begin monthly/quarterly review cadence

### 7.4 Post-Deployment (Ongoing)
- [ ] Daily: Pre-market signal generation, post-market reconciliation
- [ ] Weekly: Review rolling metrics, drift flags, regime status
- [ ] Monthly: Performance vs. expectations, cost analysis, capacity check
- [ ] Quarterly: Full go/no-go re-evaluation, statistical testing
- [ ] Annual: Strategy review, parameter stability, infrastructure audit

---

## 8. Research Handoff Summary

### 8.1 What Has Been Validated
✅ **Walk-forward robustness:** 48 folds (1993-2026), mean OOS Sharpe 0.9473, 91.7% positive folds
✅ **Parameter stability:** All 6 SMA windows [150,175,200,226,250,277] achieved Sharpe ≥ 0.9
✅ **Regime filter effectiveness:** 3 full cycles in 444-day paper trading, perfect capital preservation in risk-off
✅ **Risk controls operational:** Vol targeting (10%), DD control (15%) functioning as designed
✅ **Cost model credible:** 3 bps round-trip validated; ~2.1% annual drag; 15% of gross P&L
✅ **Operational readiness:** 444 days uninterrupted paper trading; comprehensive monitoring

### 8.2 What Requires Live Validation
⚠️ **Actual execution costs:** Verify commissions ≤ 1 bps, slippage ≤ 2 bps
⚠️ **Fill quality at scale:** Market impact at target AUM
⚠️ **Operational reliability:** Data feeds, broker API, scheduling over extended period
⚠️ **Regime filter in novel regimes:** Future bear markets, flash crashes, prolonged sideways
⚠️ **Model decay detection:** Ongoing statistical monitoring for performance degradation

### 8.3 Recommendation
**PROCEED with live deployment** subject to:
1. Infrastructure readiness per Section 2
2. Monitoring protocol per Section 3
3. Phased capital deployment (25% → 50% → 100% over 60 days)
4. Continued paper trading shadow
5. Quarterly go/no-go re-evaluation

### 8.4 Next Research Cycle (if any)
Since this system is for research/backtesting only, the next cycle within this environment should either:
- **Option A:** Continue prospective paper trading monitoring (extend track record further)
- **Option B:** Begin a new research hypothesis cycle (e.g., test alternative regime filters, universes, or signals)
- **Option C:** Archive this candidate and document lessons learned for future research

The deployment preparation is complete. Any transition to actual live trading would occur **outside this research environment** with appropriate infrastructure, compliance, and operational controls.

---

## Appendix: Reproduction Commands

```bash
# Verify strategy configuration
cat config/simulation_candidate_001.yaml

# Verify paper trading configuration
cat config/paper_trading_config.yaml

# Verify go/no-go decision
grep -A 2 "Decision:" research/reports/go_nogo_evaluation_001.md

# Re-run extended paper trading replay (deterministic)
python3 research/run_paper_trading_replay.py

# Verify 444-day track record
python3 -c "
import yaml
with open('data/processed/paper_trading_state.yaml') as f:
    state = yaml.safe_load(f)
print(f'Track record: {len(state[\"run_history\"])} days')
regimes = [r['regime_exposure'] for r in state['run_history']]
flips = sum(1 for i in range(1, len(regimes)) if regimes[i] != regimes[i-1])
print(f'Regime flips: {flips}')
print(f'Current NAV: \${state[\"current_nav\"]:,.2f}')
print(f'Max DD: {state[\"max_drawdown\"]:.2%}')
"

# Verify deployment dossier exists
ls -la research/reports/deployment_dossier_001.md
```
---

**ADDENDUM (2026-10-19, Cycle 858):** This dossier's "GO for live deployment" / "PROCEED with live deployment" statements were based on the 444-day record through 2026-10-09. Re-evaluation against the current committed paper record (449 days through 2026-10-16) shows: report-level rolling 63d Sharpe = **-0.493** (fails ≥ 0.9 gate), code-level `evaluate_go_no_go` decision = **INCONCLUSIVE** (PSR normal 0.622 in grey zone 0.5–0.95), and `low_rolling_sharpe` drift persists (5 consecutive trading days below threshold as of 2026-10-16). The unqualified "GO for live deployment" claim is **no longer supported** by current data. Promotion requires satisfying the promotion gates on the record at evaluation time. See `research/reports/go_no_go_evaluation_002.md` (2026-10-19) for full reconciliation.

**ADDENDUM (2026-10-19, Cycle 860): the decision is now gate-complete and has changed from INCONCLUSIVE to NO-GO.** The code-level go/no-go decision previously evaluated only a day-count, the PSR, the full-period max drawdown and regime *persistence*; it ignored the rolling 63d Sharpe, the full-period net-of-cost Sharpe, the rolling 63d max DD and the regime-flip gates that this dossier and `research/reports/paper_trading_validation_002.md` document. `config/promotion_gates.yaml` is now the single source of truth for the gate table and `evaluate_go_no_go` enforces **every** gate: "GO" is returned only if all of them pass, and a failing gate can never yield "GO". The gate values for the current 449-session record are unchanged from Cycle 859, but the decision that follows from them is now:

| Gate | Value | Threshold | Result |
|---|---|---|---|
| `track_record_length` | 449 | ≥ 126 | PASS |
| `full_period_sharpe` | 1.638009 | ≥ 0.9 | PASS |
| `rolling_63d_sharpe` | **-0.493001** | ≥ 0.9 | **FAIL** |
| `max_drawdown` | -0.049857 | ≥ -0.15 | PASS |
| `rolling_63d_max_dd` | -0.038564 | ≥ -0.15 | PASS |
| `regime_flips` | 6 | ≥ 1 | PASS |
| `psr` | **0.625683** | ≥ 0.95 | **FAIL** |

**Decision: NO-GO** (`psr_zone: grey_zone`; failed gates: `rolling_63d_sharpe`, `psr`). **Live deployment remains unsupported, and is now explicitly rejected on the current record**: two documented promotion gates fail, and the failing rolling 63d Sharpe gate is the same criterion this dossier lists as "Rolling 63d Sharpe < 0.9 → Not met". The earlier "GO (with conditions)" row in the rollout checklist (line 260) and the "PROCEED with live deployment" recommendation (line 365) describe the 444-day record through 2026-10-09 and must not be read as a current authorization. No threshold was changed in Cycle 860 — the enforcement of the already-documented thresholds is what changed. Evidence: `research/reports/monitoring_cycle_860.md`; dated addendum in `research/reports/go_no_go_evaluation_002.md`.

**ADDENDUM (2026-10-19, Cycle 861): the gate values are now on one documented Sharpe convention; live deployment remains unsupported.** Cycle 861 replaced the three simultaneous Sharpe estimators with one documented convention (`arithmetic_annualized_rf0`: `mean(r) * 252 / (std(r, ddof=1) * sqrt(252))`, zero risk-free rate — the formula of the live `low_rolling_sharpe` drift flag and the scale of every rolling Sharpe quoted in this dossier's source artifacts). The decision on the current record does not change, but two gate values do, and the 444-day record's verdict does:

| Gate | Value (Cycle 861) | Threshold | Result |
|---|---|---|---|
| `track_record_length` | 449 | ≥ 126 | PASS |
| `full_period_sharpe` | 1.748401 | ≥ 0.9 | PASS |
| `rolling_63d_sharpe` | **-0.211884** | ≥ 0.9 | **FAIL** |
| `max_drawdown` | -0.049857 | ≥ -0.15 | PASS |
| `rolling_63d_max_dd` | -0.038564 | ≥ -0.15 | PASS |
| `regime_flips` | 6 | ≥ 1 | PASS |
| `psr` | **0.684041** | ≥ 0.95 | **FAIL** |

**Decision on the current 449-session record: NO-GO** (`psr_zone: grey_zone`; failed gates `rolling_63d_sharpe`, `psr`). **Live deployment remains unsupported.** The rolling 63d Sharpe gate value quoted in the Cycle 858/860 addenda (-0.493001) was computed with the backtest-baseline scale; the canonical value for the same window is -0.211884, which is identical to the stored drift flag — the gate still fails, and the discrepancy between the two numbers was a measurement-definition difference, not a data change.

The 444-day record through 2026-10-09 (the record behind this dossier's original "GO (with conditions)" and "PROCEED with live deployment" statements) now evaluates as: rolling 63d Sharpe **0.935578 → PASS** (it was recorded as 0.670178 on the old scale, a FAIL) but `psr` **0.762425 → FAIL** (grey zone), i.e. **INCONCLUSIVE**. It is still not promotable, and the "GO"/"PROCEED" statements in this dossier remain historical and unsupported. Evidence: `research/reports/monitoring_cycle_861.md`; dated addendum in `research/reports/go_no_go_evaluation_002.md`.
