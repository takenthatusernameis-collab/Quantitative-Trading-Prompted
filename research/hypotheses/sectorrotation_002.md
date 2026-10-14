# Hypothesis: Sector Rotation — Cross-Sectional Momentum Across 9 GICS Sector ETFs (sectorrotation_002)

## Version History

- v002 (sectorrotation_002, 2026-10-14): Re-registered for Cycle 26 following csmomentum_001 rejection (WF mean OOS Sharpe 0.6619 < 0.9). Parent: Cycle 25 experiment csmomentum_001_experiment_001.md. Based on C4 from opportunity shortlist (Overall 28/35, Exploratory). Code revision: current.

---

## Mechanism Description

Sector leadership persists with the business cycle: different GICS sectors lead at different points in the cycle, and leadership changes gradually. The structural explanation is staggered information diffusion across sectors, institutional reallocation constraints, and confirmation effects producing intermediate-term persistence in relative sector performance.

This is cross-sectional momentum (Asness et al. 2013) restricted to a homogeneous equity-sector universe. Restricting to 9 GICS sector ETFs isolates equity sector leadership from cross-asset rank noise. Long-only implementation (top fraction, equal-weight, no shorts) avoids borrow-cost gaps.

**Context:** C3 (18-ETF broad universe containing these sectors) failed promotion gate in Cycle 25 (WF mean OOS Sharpe 0.6619 < 0.9). The sector-restricted variant tests whether purer sector leadership yields stronger performance; reduced cross-sectional breadth (9 vs 18) is a known trade-off.

---

## Expected direction and magnitude (Pre-Specified Prior)

| Metric | Expected Range | Note |
|--------|----------------|------|
| Gross annualized excess return over 1/N | 0%–2% | Prior conditioned on C3 rejection |
| Net annualized excess return over 1/N (after 3bps round-trip) | 0%–1.5% | ~monthly turnover |
| Net out-of-sample Sharpe (walk-forward) | >= 0.9 (promotion gate) | Gate fixed by AGENTS.md |
| Max drawdown (test) | < 25% | 9-asset concentration risk |
| Annualized turnover | 1.0x–2.0x | Narrower universe |

Falsification: WF mean OOS Sharpe < 0.9 OR < 50% positive folds OR < 100 pooled OOS trades → hypothesis rejected/failed.

---

## Holding horizon

~21 trading days (monthly). Signal on T-1 close, positions effective T (1-day lag). Monthly rebalance.

---

## Asset Universe

9 GICS sector ETFs (cached in data/raw/, 1998-2026):
- XLB (Materials), XLE (Energy), XLF (Financials), XLI (Industrials), XLK (Technology), XLP (Consumer Staples), XLU (Utilities), XLV (Health Care), XLY (Consumer Discretionary)

Common start across all 9: 1998-12-22 (sector ETFs incept 1998-12-22).

---

## Features and Data Sources

- Prices: Daily Close from data/raw/{symbol}.parquet
- Momentum: 12m return skipping 1m (lookback=252, skip=21) via src/features/momentum.py:compute_momentum
- Ranking/selection: cross-sectional rank, top_fraction, equal-weight via rank_assets/select_top_decile/build_weights
- Point-in-time: weights shifted by 1 day

---

## Pre-Specified Configuration (Baseline)

- lookback=252, skip=21, top_fraction=0.5
- Long-only, equal-weight (sum 1.0), no leverage
- Costs: 3bps round-trip (1bps comm + 2bps slip)

## Robustness Grid (Pre-Specified, N=18)

| Parameter | Values | Count |
|-----------|--------|-------|
| lookback | {189, 252, 315} | 3 |
| skip | {21, 42} | 2 |
| top_fraction | {0.3, 0.5, 0.7} | 3 |
| Total | | 18 |

Baseline is center (252,21,0.5). Grid count N=18 for DSR.

---

## Entry/Exit Rules

1. Signal formation T-1: compute momentum = (Close_{t-skip}/Close_{t-skip-lookback})-1 for each sector ETF
2. Cross-sectionally rank by momentum (higher better)
3. Select top top_fraction, equal-weight long-only
4. Weights effective T (1-day lag)
5. Monthly rebalance (month-end)
6. Costs 3bps round-trip on weight changes

---

## Benchmarks

1. 1/N Equal-Weight of the 9-sector universe (monthly rebalance, 1-day lag, same costs)
2. Incumbent TSMOM (7-ETF) for context on same test period

---

## Known Confounders

- Reduced cross-sectional breadth (9 assets) vs 18-ETF C3
- Sector concentration risk (single sector can dominate top fraction)
- Business cycle sensitivity; no explicit regime filter in baseline
- Parameter fragility (pre-specify grid + plateau)
- Costs modeled as flat 3bps

---

## Cost Model

- Commission 1bps, slippage 2bps, round-trip 3bps (per settings/simulation conventions)
- No borrow/short, no market impact beyond slippage, flat RF 2% ann

---

## Evaluation Plan

### Splits
| Split | Period | Purpose |
|-------|--------|---------|
| Train | 1998-12-22 to 2009-12-31 | Baseline fixed (no opt) |
| Validation | 2010-01-01 to 2017-12-31 | Robustness grid/diagnostics |
| Test | 2018-01-01 to 2026-10-09 | Final holdout |

### Walk-Forward (10yr/1yr/6mo, purge 21d, embargo 21d, fixed params)
- Folds: ~36 (sector universe starts 1998-12-22; actual count to be reported)
- Evaluate mean OOS Sharpe, pos fold rate, pooled trades

### Gates (all must pass)
- WF mean OOS Sharpe >= 0.9
- >= 50% positive folds
- > 100 pooled OOS trades
- Plateau: >= 2 of 3 lookbacks within 10% of baseline test Sharpe (at baseline skip/top)

### Multiple-Testing Control
- DSR with n_configs=18
- Block-bootstrap Sharpe CIs, PSR as applicable
- No test peeking

## Reproduction Commands
```bash
# Verify data
python3 << 'PY'
import pandas as pd
syms=['XLB','XLE','XLF','XLI','XLK','XLP','XLU','XLV','XLY']
for s in syms:
    df=pd.read_parquet(f'data/raw/{s}.parquet')
    print(s, df.index.min(), df.index.max())
PY
```
