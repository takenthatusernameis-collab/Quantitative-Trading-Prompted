# Hypothesis: Sector Rotation — Cross-Sectional Momentum Across 9 GICS Sector ETFs (sectorrotation_001)

## Version History

- v001 (sectorrotation_001, 2026-10-12): Initial pre-registered hypothesis
  for Cycle 14. Parent cycle: Cycle 11 Opportunity Shortlist (C4, 28/35 —
  Explor signal, rank 3 of 10). Code revision: 47c531e
  Pre-registered BEFORE any backtest execution (evaluation is Cycle 15).

---

## Mechanism Description

Sector leadership persists with the business cycle: at any point in the
cycle, a subset of GICS sectors leads (e.g., cyclicals early in an
expansion, defensives late), and leadership changes gradually as economic
conditions and earnings expectations diffuse. The structural explanation is
staggered information diffusion across sectors: fundamental information about
the cycle reaches sector earnings and analyst estimates at different speeds,
institutional reallocation between sectors faces mandate and benchmark
constraints, and investors require confirmation before rotating — producing
intermediate-term persistence in relative sector performance.

This is the cross-sectional momentum mechanism (Asness et al. 2013, "Value
and Momentum Everywhere") restricted to a homogeneous equity-sector universe.
Restricting the universe to the 9 GICS sector ETFs removes cross-asset-class
rank noise (rates, gold, commodity, and REIT factors that drive the
broad-universe rank ordering in C3 but are not sector-leadership signals),
so the rank ordering reflects equity sector leadership specifically. The
long-only implementation (top fraction, equal-weight, no shorts) avoids the
borrow-cost gap that blocks short-side strategies.

**Explicit acknowledgment (per Cycle 14 implementation notes)**: C4 is a
lower-prior variant of the same mechanism evaluated and rejected in Cycle 13.
The C3 universe (18 ETFs) CONTAINS these 9 sectors, and the cross-sectional
rank signal on that superset failed the pre-registered walk-forward gate
(WF mean OOS Sharpe 0.6868 < 0.9; baseline ranked 17/18 on its own grid;
DSR negative at both N=27 and N=18). The theoretical case for the sector
restriction (purer business-cycle leadership signal without cross-asset-class
rank noise) is plausible but unproven, and the reduced cross-sectional
breadth (9 vs 18 assets) lowers the rank signal's information content.
The prior below is therefore explicitly conditioned on C3's rejection and
is LOWER than C3's prior was.

---

## Expected direction and magnitude (Pre-Specified Prior)

The prior is explicitly conditioned on Cycle 13's rejection of C3 (the
broad 18-ETF universe containing these 9 sectors) and is LOWER than C3's
prior in every return dimension:

| Metric | C3 prior (rejected) | C4 prior (this hypothesis) | Note |
|--------|---------------------|----------------------------|------|
| Gross annualized excess return over 1/N (equal-weight) | 1%–4% | **0%–2%** | Prior, not a result; lowered because the superset-universe signal failed |
| Net annualized excess return over 1/N (after 3bps round-trip) | 0.5%–3% | **0%–1.5%** | Prior; ~monthly turnover, 12–15 trades/year |
| Net out-of-sample Sharpe (walk-forward) | >= 0.9 (promotion gate) | >= 0.9 (promotion gate, unchanged) | Gate is fixed by AGENTS.md; the prior probability of clearing it is lower |
| Maximum drawdown (test) | < 20% | < 25% | 9-asset concentration raises idiosyncratic drawdown risk |
| Annualized turnover | 1.0x–1.5x | 1.0x–2.0x | Narrower universe can raise concentration-driven turnover |

Direction: positive (long-only top-momentum sectors are expected to
outperform the 1/N equal-weight sector portfolio), net of 3bps costs.

Falsification: If the net walk-forward mean OOS Sharpe < 0.9 OR < 50% of
walk-forward folds have positive test Sharpe, the hypothesis is
**rejected** (downgraded to Rejected/Failed). This condition is
pre-stated BEFORE any backtest execution.

---

## Holding horizon

~21 trading days (monthly signal horizon). Matches the repository
convention used for the incumbent (tsmomentum_spytrend_001) and C3.
Signal is computed on T-1 close, positions effective T (1-day signal
lag). Rebalance calendar: monthly (month-end).

---

## Asset Universe

The 9 cached GICS sector ETFs (a subset of C3's 18-ETF universe):

1. XLB — Materials Sector
2. XLE — Energy Sector
3. XLF — Financials Sector
4. XLI — Industrials Sector
5. XLK — Technology Sector
6. XLP — Consumer Staples Sector
7. XLU — Utilities Sector
8. XLV — Health Care Sector
9. XLY — Consumer Discretionary Sector

**Data integrity (verified 2026-10-12, pre-freeze)**: all 9 parquet files
in `data/raw/*.parquet` have 6,991 rows each, identical trading calendars,
**100% Close completeness** on the common calendar (0 NaN, 0 duplicate
dates), common range **1998-12-22 to 2026-10-08** (~28 years). Aligned
Close frame: 6,991 x 9, content hash `5e2d48e6579a53cd`. No new data is
fetched (cache-only).

Cross-sectional breadth is constant at 9 for the full history (all 9
incept together on 1998-12-22). Signal warmup: the first date on which
all 9 momentum values are valid is 2000-01-24 for the baseline (252, 21)
and 2000-05-23 for the longest grid config (315, 42); pre-warmup dates
carry no positions (point-in-time, no back-fill).

---

## Features and Data Sources

| Feature | Specification | Source |
|---------|---------------|--------|
| Prices | Daily Close (OHLCV) | `data/raw/{XLB..XLY}.parquet` (Yahoo Finance via yfinance, cached) |
| Momentum signal | 12-month return with 1-month skip: `lookback=252`, `skip=21` (default) | Computed via `src/features/momentum.py:compute_momentum` |
| Ranking | Cross-sectional rank each period (higher momentum = higher rank) | `src/features/momentum.py:rank_assets` |
| Selection | Top `top_fraction` by rank, equal-weight | `src/features/momentum.py:select_top_decile`, `build_weights` |
| Point-in-time | Weights shifted by 1 day (signal on T-1 -> position on T) | `src/features/momentum.py:build_weights` line 98 |

### Pre-Specified Default Configuration

- `lookback = 252` trading days (~12 months)
- `skip = 21` trading days (~1 month, avoids short-term reversal)
- `top_fraction = 0.5` (hold top 50%, equal-weight)

With 9 assets, `select_top_decile` holds 3 sectors at `top_fraction=0.3`,
5 sectors at `0.5`, and 7 sectors at `0.7` (rank threshold
`max_rank x (1 - top_fraction)`).

### Pre-Specified Robustness Grid (Fixed Count for Multiple-Testing Control)

The following grid is pre-registered. ALL 18 combinations will be evaluated
in Cycle 15. No additional configurations will be added post-hoc.

| Parameter | Values | Count |
|-----------|--------|-------|
| `lookback` | {189, 252, 315} | 3 |
| `skip` | {21, 42} | 2 |
| `top_fraction` | {0.3, 0.5, 0.7} | 3 |
| **Total** | | **18** |

**Grid arithmetic (corrected per Cycle 14)**: the grid label equals the
product of the parameter value counts: 3 x 2 x 3 = **18 unique
configurations**. This corrects the Cycle 13 pre-registration defect, in
which the identical parameter values were mislabeled "27 configurations".
The Cycle 15 evaluation script MUST contain an explicit assertion that
`len(lookbacks) * len(skips) * len(top_fractions) == 18` before any
evaluation runs, and the multiple-testing deflation (DSR) is computed at
the TRUE count N=18 (there is no separate "pre-registered" vs "evaluated"
count this cycle — the pre-registered count IS the product).

This fixed count (18) is the basis for multiple-testing control (Deflated
Sharpe Ratio, PBO/CSCV). The baseline is the center point: `(252, 21, 0.5)`.

---

## Entry/Exit Rules

1. **Signal formation (T-1 close)**: Compute 12-month momentum for each
   of the 9 sector ETFs using `lookback` and `skip` parameters. Momentum
   = `(Close_{t-skip} / Close_{t-skip-lookback}) - 1`.
2. **Ranking**: Cross-sectionally rank assets by momentum (highest = rank 1).
3. **Selection**: Select assets in the top `top_fraction` by rank.
   Equal-weight the selected assets (sum of weights = 1.0).
4. **Point-in-time execution**: Weights computed on T-1 are effective on
   T (1-day signal lag, enforced by `build_weights` shift).
5. **Rebalancing**: Monthly (month-end calendar). No intra-month trading.
6. **Long-only**: No short positions. Cash weight = 1 - sum(long weights)
   when fewer than all assets are selected (always 0 for any
   top_fraction > 0 with 9 assets).
7. **No leverage**: Gross exposure <= 100% (long-only equal-weight sums to 1.0).
8. **Costs applied**: 3 bps round-trip (1 bps commission + 2 bps slippage)
   on weight changes.

---

## Benchmark

Two benchmarks, both evaluated on the identical date range and cost model:

1. **1/N Equal-Weight Portfolio**: All 9 sector ETFs held at equal weight
   (1/9 each), rebalanced monthly, same 1-day lag, same 3bps round-trip
   cost model. This isolates the alpha from cross-sectional ranking vs.
   passive holding of the same universe. (Within the engine's
   exogenous-weights framework, constant 1/9 targets with the monthly
   calendar imply zero observed turnover and zero cost drag — a mild
   upward bias in the benchmark's net return, noted as a limitation,
   identical to the C3 benchmark convention.)
2. **Incumbent TSMOM (tsmomentum_spytrend_001)**: The Cycle 6 validated
   candidate on its core 7-asset universe (SPY, QQQ, IWM, TLT, GLD, EFA,
   EEM) with vol-target (10%), DD control (15%), SPY 200d SMA filter, 3bps
   costs. This benchmark tests whether sector rotation adds value beyond
   the existing credible candidate. Evaluated with its validated
   overlay-warmup conventions: "slice" (overlay state initializes at the
   period start) for the test period — reproducing the Cycle 7 record —
   and "full" (overlay state initializes at history_start, then sliced)
   for the walk-forward folds — reproducing the Cycle 6 fold record.

Both benchmarks are evaluated on the **test period** (2018-01-01 to
2026-10-09) and in the **identical walk-forward folds**.

---

## Known Confounders

1. **C3 rejection on the superset universe**: The broad 18-ETF universe
   (which CONTAINS these 9 sectors) failed the walk-forward gate
   (WF mean OOS Sharpe 0.6868 < 0.9, baseline rank 17/18, negative DSR).
   This is direct prior evidence against the cross-sectional rank signal
   in this dataset and the primary reason the C4 prior is lower than C3's.
2. **Narrow 9-asset universe limits cross-sectional breadth**: Rank
   signals derive information from cross-sectional dispersion; 9 members
   (vs 18 in C3) means a noisier rank ordering and fewer independent
   relative-strength observations. With top_fraction=0.3 the portfolio
   holds only 3 sectors — high idiosyncratic concentration.
3. **Sector-concentrated equity beta**: All 9 members are US equity
   sector ETFs; the strategy carries concentrated US equity factor
   exposure and partially overlaps the incumbent's equity beta
   (diversification score 4/5 on the Cycle 11 shortlist).
4. **ETF-level only, no constituent data**: Survivorship bias is minimal
   at the ETF level (all 9 are currently listed), but constituent-level
   turnover within ETFs is not modeled.
5. **Flat 3bps cost model**: Real-world costs vary by asset, time, and
   trade size. Sector ETFs may have wider spreads than SPY/QQQ. The flat
   model is a simplifying assumption.
6. **No risk overlay in baseline**: Per AGENTS.md "Baseline before
   complexity", the baseline has NO volatility targeting, NO drawdown
   control, NO regime filter. These are reserved for post-baseline cycles
   ONLY IF the baseline clears all promotion gates.
7. **Monthly rebalancing with 1-day lag**: The signal horizon is ~21 days
   but execution is monthly. This may miss intra-month momentum decay or
   reversal.
8. **Common-inception universe**: All 9 ETFs incept on 1998-12-22, so
   there is no point-in-time breadth growth (unlike C3); the effective
   history for signal formation is ~26.7 years after momentum warmup.

---

## Falsification Condition

The hypothesis is **falsified (Rejected/Failed)** if ANY of the following
hold on the pre-registered walk-forward evaluation (36 folds, fixed
parameters, 10yr train / 1yr test / 6mo step, 21-day purge & embargo):

1. **Walk-forward mean OOS Sharpe < 0.9** (primary promotion gate)
2. **< 50% of walk-forward folds have positive test Sharpe**
3. **< 100 pooled OOS trades across all folds**
4. **Parameter plateau check fails**: < 2 of the 3 `lookback` values
   (189, 252, 315) achieve test Sharpe within 10% of the baseline
   (252, 21, 0.5) test Sharpe, when evaluated at the baseline's
   `skip=21, top_fraction=0.5` (repository plateau convention:
   threshold = max(0.1, 10% x |baseline test Sharpe|)).

This condition is pre-stated BEFORE any backtest execution. If falsified,
the candidate is labeled "rejected/failed" and archived, and the next
cycle moves to the next candidate on the Cycle 11 shortlist (C6 Calendar
/ rebalancing effects, 26/35).

---

## Cost Model Assumptions

Identical to C3 (csmomentum_001), the incumbent (tsmomentum_spytrend_001)
and `config/simulation_candidate_001.yaml`:

| Component | Value | Source |
|-----------|-------|--------|
| Commission | 1.0 bps/trade | `config/settings.yaml:backtest.default_commission_bps` |
| Slippage | 2.0 bps/trade | `config/settings.yaml:backtest.default_slippage_bps` |
| Round-trip | 3.0 bps | `config/simulation_candidate_001.yaml:cost_model` |
| Funding rate | 0.0% annualized (placeholder) | `config/settings.yaml:backtest.default_funding_rate_annual` |
| Risk-free rate | 2.0% annualized (flat) | `config/settings.yaml:evaluation.risk_free_rate_annual` |
| Minimum trade size | $10.00 | `config/settings.yaml:backtest.min_trade_size_usd` |

**Cost model gaps acknowledged**: No bid-ask spread model, no borrow/short
cost (long-only avoids this), no market-impact model (flat slippage), no
latency model, flat risk-free rate. These are documented limitations per
`research/reports/data_inventory.md`.

---

## Pre-Registered Evaluation Plan

### Chronological Splits (Repo Convention)

| Split | Period | Purpose |
|-------|--------|---------|
| Train | 1998-12-22 to 2009-12-31 | Parameter selection (NOT used — baseline is pre-specified) |
| Validation | 2010-01-01 to 2017-12-31 | Robustness grid evaluation, configuration screening (diagnostic only) |
| Test | 2018-01-01 to 2026-10-09 | Final holdout, promotion-gate decision |

**Calendar note**: the repository convention END_DATE is 2026-10-09; the
9-sector union calendar's final trading day is 2026-10-08, so the
effective test window ends 2026-10-08 with this universe (the engine
aligns onto the universe's own calendar).

**Point-in-time treatment**: All signals use only data available at
formation. Weights shifted 1 day. No look-ahead in any split.

### Walk-Forward Design (Matches Cycle 6 / `tsmomentum_regime_filter_wf_001.md`)

- **Rolling window**: 10-year train, 12-month test, 6-month step
- **Purge**: 21 days between train end and test start
- **Embargo**: 21 days after test period end
- **Parameters**: Fixed across all folds (NO per-fold re-optimization)
- **Folds**: **36** (computed from the 1998-12-22 history start via
  `src/evaluation/walkforward.py:generate_walkforward_splits`; the C3
  48-fold count does NOT apply because the sector universe starts in
  1998, not 1993). Fold 1: train 1998-12-22 -> 2008-08-18, test
  2008-09-17 -> 2009-09-03. Fold 36: train 2015-11-17 -> 2025-07-14,
  test 2025-08-13 -> 2026-07-30. The Cycle 15 script MUST assert the
  generated fold count equals 36 (documenting the actual count, not
  forcing 48).
- **Evaluation**: Each fold produces test-period Sharpe, annual return,
  max DD, trade count.

### Promotion Gates (ALL Must Pass to Advance to Simulation/Paper-Trading)

| Gate | Threshold | Measured On |
|------|-----------|-------------|
| Walk-forward mean OOS Sharpe | >= 0.9 | All folds, net of 3bps costs |
| Positive fold rate | >= 50% | Count of folds with test Sharpe > 0 |
| Pooled OOS trades | > 100 | Sum of trades across all test folds |
| Parameter plateau | >= 2 of 3 lookbacks within 10% of baseline test Sharpe | Baseline `skip=21, top_fraction=0.5` |

### Multiple-Testing Control

- **Exact configuration count tracked**: 18 pre-specified combinations
  (3 x 2 x 3), with an explicit arithmetic assertion in the Cycle 15 script
  (the grid label equals the product of the parameter value counts).
- **Deflated Sharpe Ratio**: Computed via
  `src/evaluation/statistics.py:compute_dsr` using the true trial count
  N=18 (no pre-registered/evaluated count discrepancy this cycle).
- **No test-set peeking**: Configurations are NEVER selected based on
  test-period results. The baseline is pre-specified. The robustness grid
  is for diagnostic/plateau purposes only.
- **PSR** (vs SR=0 and vs the 0.9 gate), **block-bootstrap Sharpe 95%
  CI**, and **PBO/CSCV** via `src/evaluation/statistics.py:compute_pbo`
  over the 18-config grid (train=1998-2009 vs test=2018-2026).

### Reproduction Commands

```bash
# Cycle 15 (to be created) will execute the baseline backtest and walk-forward
python3 research/run_cycle15.py

# Verification that config parses
python3 -c "import yaml; yaml.safe_load(open('config/sectorrotation_candidate_001.yaml'))"
```

---

## Evidence Artifacts (To Be Persisted in Cycle 15)

Per AGENTS.md "Evidence artifacts", Cycle 15 will persist:

- Data-source details, date ranges, frequency, asset universe, point-in-time treatment
- Missing-data handling (pre-inception cells are NaN and excluded from ranking)
- Integrity hashes/counts (row counts per symbol, date-range coverage, aligned-frame content hash)
- Code revision (git SHA)
- Configurations tested (all 18, with parent/lineage to this hypothesis)
- Trial count (18)
- Cost assumptions (3bps round-trip, 1-day lag, Close field)
- Baseline metrics (Sharpe, Sortino, CAGR, max DD, profit factor, turnover, exposure, trade count, tail risk)
- Benchmark-relative results (vs 1/N and vs incumbent)
- Walk-forward folds (36), purge/embargo, parameter plateau results
- Deflated Sharpe Ratio (N=18), PBO/CSCV, probabilistic Sharpe, block-bootstrap CIs
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
- Cycle 11 Opportunity Shortlist: `research/reports/opportunity_shortlist.md` (C4 = 28/35, rank 3 of 10 — Exploratory signal)
- Cycle 13 experiment record (C3 rejection; direct prior evidence): `research/experiments/csmomentum_baseline_wf_001.md`
- Cycle 12 pre-registration (C3): `research/hypotheses/csmomentum_001.md`, `config/csmomentum_candidate_001.yaml`
- Cycle 6 Walk-Forward Design: `research/experiments/tsmomentum_regime_filter_wf_001.md`
- Ranking Machinery: `src/features/momentum.py` (`compute_momentum`, `rank_assets`, `select_top_decile`, `build_weights`)
- Backtest engine: `src/backtest/engine.py`
- Evaluation stats: `src/evaluation/statistics.py` (`compute_dsr`, `compute_psr`, `compute_pbo`; seeded bootstrap, seed=42 convention)
- AGENTS.md: Research Documentation Standards; "Baseline before complexity"; "Hypothesis first"; "Independent evaluation"; "Multiple-testing control"

---

*Created: 2026-10-12*
*Code revision: 47c531e*
*Status: PRE-REGISTERED — No backtest executed. Cycle 15 will execute evaluation.*
