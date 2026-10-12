# Hypothesis: Long-Only Cross-Sectional Momentum (csmomentum_001)

## Version History

- v001 (csmomentum_001, 2026-10-12): Initial pre-registered hypothesis for Cycle 12.
  Parent cycle: Cycle 11 Opportunity Shortlist (C3, 29/35 — Exploratory signal).
  Code revision: 8604ed1

---

## Mechanism Description

Cross-sectional momentum exploits the tendency for assets with higher intermediate-term returns (relative to peers) to continue outperforming in the subsequent period. The structural explanation is investor underreaction and slow information diffusion across asset classes and sectors: fundamental improvements in relative performance are only gradually reflected in prices as investors update beliefs sluggishly, face institutional constraints on reallocation, or require confirmation before committing capital. Unlike time-series momentum (which asks "has this asset gone up?"), cross-sectional momentum asks "has this asset gone up *relative to the universe*?" — this isolates the relative-strength signal from common market beta and is less sensitive to regime-dependent absolute trends.

The long-only implementation (holding the top-ranked fraction, equal-weight, no shorts) avoids the borrow-cost gap that blocks short-side strategies and is executable with the 18-ETF cache available in this repository. The mechanism is a first-order, globally documented anomaly (Asness et al. 2013, "Value and Momentum Everywhere") with persistent evidence across asset classes, geographies, and time periods.

---

## Expected direction and magnitude (Pre-Specified Prior)

| Metric | Expected Range | Note |
|--------|----------------|------|
| Gross annualized excess return over 1/N (equal-weight) | 1%–4% | Prior, not a result; based on academic literature for broad-asset-class cross-sectional momentum |
| Net annualized excess return over 1/N (after 3bps round-trip) | 0.5%–3% | Prior; assumes ~monthly turnover, 12–15 trades/year, ~36–45bps annual cost drag |
| Net out-of-sample Sharpe (walk-forward) | >= 0.9 (promotion gate) | Must clear gate to advance; prior is optimistic but falsifiable |
| Maximum drawdown (test) | < 20% | Prior |
| Annualized turnover | 1.0x–1.5x | Prior |

Falsification: If the net walk-forward mean OOS Sharpe < 0.9 OR < 50% of walk-forward folds have positive test Sharpe, the hypothesis is **rejected** (downgraded to Rejected/Failed). This condition is pre-stated BEFORE any backtest execution.

---

## Holding horizon

~21 trading days (monthly signal horizon). Matches the repository convention used for the incumbent (tsmomentum_spytrend_001). Signal is computed on T-1 close, positions effective T (1-day signal lag). Rebalance calendar: monthly (month-end).

---

## Asset Universe

The 18 cached ETFs with complete daily OHLCV history (1993/1998–2026):

1. SPY — S&P 500
2. QQQ — Nasdaq-100
3. IWM — Russell 2000 (small-cap)
4. TLT — 20+ Year US Treasury
5. GLD — Gold
6. DBC — Broad Commodity
7. VNQ — US REITs
8. EFA — Developed International Equity
9. EEM — Emerging Markets Equity
10. XLB — Materials Sector
11. XLE — Energy Sector
12. XLF — Financials Sector
13. XLI — Industrials Sector
14. XLK — Technology Sector
15. XLP — Consumer Staples Sector
16. XLU — Utilities Sector
17. XLV — Health Care Sector
18. XLY — Consumer Discretionary Sector

All 18 are cached in `data/raw/*.parquet` with 100% Close completeness, no duplicate dates, daily frequency. Earliest common date across all 18: 2006-02-06 (DBC inception). SPY history begins 1993-01-29; sector ETFs begin 1998-12-22.

---

## Features and Data Sources

| Feature | Specification | Source |
|---------|---------------|--------|
| Prices | Daily Close (OHLCV) | `data/raw/{symbol}.parquet` (Yahoo Finance via yfinance, cached) |
| Momentum signal | 12-month return with 1-month skip: `lookback=252`, `skip=21` (default) | Computed via `src/features/momentum.py:compute_momentum` |
| Ranking | Cross-sectional rank each period (higher momentum = higher rank) | `src/features/momentum.py:rank_assets` |
| Selection | Top `top_fraction` by rank, equal-weight | `src/features/momentum.py:select_top_decile`, `build_weights` |
| Point-in-time | Weights shifted by 1 day (signal on T-1 → position on T) | `src/features/momentum.py:build_weights` line 98 |

### Pre-Specified Default Configuration

- `lookback = 252` trading days (~12 months)
- `skip = 21` trading days (~1 month, avoids short-term reversal)
- `top_fraction = 0.5` (hold top 50%, equal-weight)

### Pre-Specified Robustness Grid (Fixed Count for Multiple-Testing Control)

The following grid is pre-registered. ALL 27 combinations will be evaluated in Cycle 13. No additional configurations will be added post-hoc.

| Parameter | Values | Count |
|-----------|--------|-------|
| `lookback` | {189, 252, 315} | 3 |
| `skip` | {21, 42} | 2 |
| `top_fraction` | {0.3, 0.5, 0.7} | 3 |
| **Total** | | **27** |

This fixed count (27) is the basis for multiple-testing control (Deflated Sharpe Ratio, PBO/CSCV). The baseline is the center point: `(252, 21, 0.5)`.

---

## Entry/Exit Rules

1. **Signal formation (T-1 close)**: Compute 12-month momentum for each of the 18 ETFs using `lookback` and `skip` parameters. Momentum = `(Close_{t-skip} / Close_{t-skip-lookback}) - 1`.
2. **Ranking**: Cross-sectionally rank assets by momentum (highest = rank 1).
3. **Selection**: Select assets in the top `top_fraction` by rank. Equal-weight the selected assets (sum of weights = 1.0).
4. **Point-in-time execution**: Weights computed on T-1 are effective on T (1-day signal lag, enforced by `build_weights` shift).
5. **Rebalancing**: Monthly (month-end calendar). No intra-month trading.
6. **Long-only**: No short positions. Cash weight = 1 - sum(long weights) when fewer than all assets are selected (always 0 for top_fraction > 0 with 18 assets).
7. **No leverage**: Gross exposure ≤ 100% (long-only equal-weight sums to 1.0).
8. **Costs applied**: 3 bps round-trip (1 bps commission + 2 bps slippage) on weight changes.

---

## Benchmark

Two benchmarks, both evaluated on the identical date range and cost model:

1. **1/N Equal-Weight Portfolio**: All 18 ETFs held at equal weight (1/18 each), rebalanced monthly, same 1-day lag, same 3bps round-trip cost model. This isolates the alpha from cross-sectional ranking vs. passive holding of the same universe.
2. **Incumbent TSMOM (tsmomentum_spytrend_001)**: The Cycle 6 validated candidate on its core 7-asset universe (SPY, QQQ, IWM, TLT, GLD, EFA, EEM) with vol-target (10%), DD control (15%), SPY 200d SMA filter, 3bps costs. This benchmark tests whether cross-sectional momentum adds value beyond the existing credible candidate.

Both benchmarks are evaluated on the **test period** (2018-01-01 to 2026-10-09) and in **walk-forward folds**.

---

## Known confounders

1. **Parameter-peak risk**: Cycle 3's 100-config grid for the incumbent showed the baseline parameters sit on a sharp peak (5% of configs within 0.05 Sharpe; 0/100 beat baseline). Cross-sectional rank signals may exhibit similar fragility — this is why the 27-config robustness grid is pre-specified and the plateau check is a promotion gate.
2. **Universe composition sensitivity**: Cross-sectional rank signals depend on the relative ordering within the universe. Adding/removing assets (e.g., sector ETFs incepting in 1998) changes the rank distribution. The 18-ETF universe is fixed but its effective cross-sectional breadth varies over time (only 8 assets pre-1998, 17 pre-2006, 18 post-2006).
3. **ETF-level only, no constituent data**: Survivorship bias is minimal at the ETF level (all 18 are currently listed), but constituent-level turnover within ETFs is not modeled.
4. **Flat 3bps cost model**: Real-world costs vary by asset, time, and trade size. Sector ETFs (XLB–XLY) may have wider spreads than SPY/QQQ. The flat model is a simplifying assumption.
5. **No risk overlay in baseline**: Per AGENTS.md "Baseline before complexity", the baseline has NO volatility targeting, NO drawdown control, NO regime filter. These are reserved for Cycle 14+ ONLY IF the baseline clears promotion gates.
6. **Monthly rebalancing with 1-day lag**: The signal horizon is ~21 days but execution is monthly. This may miss intra-month momentum decay/reversal.

---

## Falsification Condition

The hypothesis is **falsified (Rejected/Failed)** if ANY of the following hold on the pre-registered walk-forward evaluation (48 folds, fixed parameters, 10yr train / 1yr test / 6mo step, 21-day purge & embargo):

1. **Walk-forward mean OOS Sharpe < 0.9** (primary promotion gate)
2. **< 50% of walk-forward folds have positive test Sharpe**
3. **< 100 pooled OOS trades across all folds**
4. **Parameter plateau check fails**: < 2 of the 3 `lookback` values (189, 252, 315) achieve test Sharpe within 10% of the baseline (252, 21, 0.5) test Sharpe, when evaluated at the baseline's `skip=21, top_fraction=0.5`.

If falsified, the candidate is labeled "rejected/failed" and the next cycle will document the failure and either (a) test a pre-specified alternative from the robustness grid, or (b) move to the next candidate on the shortlist (C4 Sector rotation).

---

## Cost Model Assumptions

Identical to the incumbent (tsmomentum_spytrend_001) and `config/simulation_candidate_001.yaml`:

| Component | Value | Source |
|-----------|-------|--------|
| Commission | 1.0 bps/trade | `config/settings.yaml:backtest.default_commission_bps` |
| Slippage | 2.0 bps/trade | `config/settings.yaml:backtest.default_slippage_bps` |
| Round-trip | 3.0 bps | `config/simulation_candidate_001.yaml:cost_model` |
| Funding rate | 0.0% annualized (placeholder) | `config/settings.yaml:backtest.default_funding_rate_annual` |
| Risk-free rate | 2.0% annualized (flat) | `config/settings.yaml:evaluation.risk_free_rate_annual` |
| Minimum trade size | $10.00 | `config/settings.yaml:backtest.min_trade_size_usd` |

**Cost model gaps acknowledged**: No bid-ask spread model, no borrow/short cost (long-only avoids this), no market-impact model (flat slippage), no latency model, flat risk-free rate. These are documented limitations per `research/reports/data_inventory.md`.

---

## Pre-Registered Evaluation Plan

### Chronological Splits (Repo Convention)

| Split | Period | Purpose |
|-------|--------|---------|
| Train | 1993-01-01 to 2009-12-31 | Parameter selection (not used in baseline; baseline is pre-specified) |
| Validation | 2010-01-01 to 2017-12-31 | Robustness grid evaluation, configuration screening |
| Test | 2018-01-01 to 2026-10-09 | Final holdout, promotion-gate decision |

**Point-in-time treatment**: All signals use only data available at formation. Weights shifted 1 day. No look-ahead in any split.

### Walk-Forward Design (Matches Cycle 6 / `tsmomentum_regime_filter_wf_001.md`)

- **Rolling window**: 10-year training, 1-year test, 6-month step
- **Purge**: 21 days between train end and test start
- **Embargo**: 21 days after test period end (before next fold train)
- **Parameters**: Fixed across all folds (NO per-fold re-optimization)
- **Folds**: ~48 (matching Cycle 6 count for 1993–2026 span)
- **Evaluation**: Each fold produces test-period Sharpe, annual return, max DD, trade count

### Promotion Gates (ALL Must Pass to Advance to Simulation/Paper-Trading)

| Gate | Threshold | Measured On |
|------|-----------|-------------|
| Walk-forward mean OOS Sharpe | >= 0.9 | All folds, net of 3bps costs |
| Positive fold rate | >= 50% | Count of folds with test Sharpe > 0 |
| Pooled OOS trades | > 100 | Sum of trades across all test folds |
| Parameter plateau | >= 2 of 3 lookbacks within 10% of baseline test Sharpe | Baseline `skip=21, top_fraction=0.5` |

### Multiple-Testing Control

- **Exact configuration count tracked**: 27 pre-specified combinations (3 × 2 × 3)
- **Deflated Sharpe Ratio**: Computed via `src/evaluation/statistics.py:compute_dsr` using the 27-config trial count
- **No test-set peeking**: Configurations are NEVER selected based on test-period results. The baseline is pre-specified. The robustness grid is for diagnostic/plateau purposes only.
- **Permutation/placebo test**: Available via `src/evaluation/statistics.py` for additional validation.

### Reproduction Commands

```bash
# Cycle 13 (to be created) will execute the baseline backtest and walk-forward
python3 research/run_cycle13.py

# Verification that config parses
python3 -c "import yaml; yaml.safe_load(open('config/csmomentum_candidate_001.yaml'))"
```

---

## Evidence Artifacts (To Be Persisted in Cycle 13+)

Per AGENTS.md "Evidence artifacts", Cycle 13 will persist:

- Data-source details, date ranges, frequency, asset universe, point-in-time treatment
- Missing-data handling (forward-fill alignment, inception-date awareness)
- Integrity hashes/counts (row counts per symbol, date-range coverage)
- Code revision (git SHA)
- Configurations tested (all 27, with parent/lineage to this hypothesis)
- Trial count (27)
- Cost assumptions (3bps round-trip, 1-day lag, Close field)
- Baseline metrics (Sharpe, Sortino, CAGR, max DD, profit factor, turnover, exposure, trade count, tail risk)
- Benchmark-relative results (vs 1/N and vs incumbent)
- Walk-forward folds, purge/embargo, parameter plateau results
- Deflated Sharpe Ratio, PBO/CSCV, probabilistic Sharpe, block-bootstrap CIs
- Reproduction commands

---

## Decision Discipline (Pre-Committed)

Results will be labeled as exactly one of:

- **Credible candidate for further validation** — All promotion gates passed, robustness confirmed, net-of-cost performance credible
- **Exploratory signal** — Some promise but gates not fully cleared; warrants limited follow-up
- **Rejected/Failed** — Falsification condition met; documented and archived
- **Blocked by data/infrastructure** — Cannot form valid test with available data

---

## References

- Asness, C. S., Moskowitz, T. J., & Pedersen, L. H. (2013). "Value and Momentum Everywhere". *Journal of Finance*, 68(3), 929-985.
- Cycle 11 Opportunity Shortlist: `research/reports/opportunity_shortlist.md` (C3 = 29/35)
- Cycle 11 Data Inventory: `research/reports/data_inventory.md`
- Cycle 6 Walk-Forward Design: `research/experiments/tsmomentum_regime_filter_wf_001.md`
- Cycle 3 Robustness Grid (parameter-peak caveat): `research/experiments/tsmomentum_robustness_001.md`
- Ranking Machinery: `src/features/momentum.py` (`rank_assets`, `select_top_decile`, `build_weights`)
- AGENTS.md: Research Documentation Standards; "Baseline before complexity"; "Hypothesis first"

---

*Created: 2026-10-12*
*Code revision: 8604ed1*
*Status: PRE-REGISTERED — No backtest executed. Cycle 13 will execute evaluation.*