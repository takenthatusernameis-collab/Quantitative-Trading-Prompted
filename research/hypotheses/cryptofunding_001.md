# Hypothesis: cryptofunding_001 — Crypto perpetual funding-rate carry (spot long + perp short)

## Mechanism
Perpetual swaps pay funding to anchor price to spot; persistently positive funding can be harvested via spot-long/perp-short. Mechanical feature of perpetual swaps driven by leveraged long demand.

## Expected direction and magnitude
Positive carry from funding payments. Measured gross carry over 2020-01-01..2026-09-30: +11.59%/yr (BTC) and +13.57%/yr (ETH), but strongly regime-dependent (+37.3%/yr ETH in 2021 vs +1.9%/yr in 2026 YTD) and **before** all costs. Net-of-cost magnitude remains unproven.

## Holding horizon
Continuous (funding every 8h); position held while funding positive.

## Asset universe
BTC/USDT, ETH/USDT USDT-margined perpetuals. Binance (primary: prices and funding) and OKX
(funding only, independent cross-check). BTC and ETH are perpetual contracts, so there is no
point-in-time membership set to reconstruct.

## Features and data sources
Binance public archive (data.binance.vision), every archive file SHA256-verified against the
published .CHECKSUM before parsing:
- 8h funding rates: data/raw/crypto/{BTC,ETH}_USDT_USDT_funding_binance.parquet — 7,395 records
  per symbol, 2020-01-01T00:00:00Z..2026-09-30T16:00:00Z (2,464.7 days), 0 missing 8h periods,
  0 duplicate timestamps.
- Daily spot and perp legs: data/raw/crypto/{BTC,ETH}USDT_{spot,perp}_1d_binance.parquet — 2,465
  daily rows each, 2020-01-01..2026-09-30.
- Coupled return path: data/processed/crypto/{BTC,ETH}USDT_carry_path.parquet (daily
  funding cashflow, spot/perp returns, basis convergence).
- OKX 8h funding (data/raw/crypto/{BTC,ETH}_USDT_USDT_funding.parquet, 296 records per symbol,
  2026-07-13..2026-10-20) retained as an independent cross-check: on the 238 overlapping 8h
  settlements the same funding sign occurs in 91.2% of periods, median absolute difference 0.213 bp.
Provenance: research/experiments/cryptofunding_002_data.md; machine-readable manifest:
research/reports/binance_crypto_manifest.json.

## Entry/exit rules
Enter spot-long/perp-short when funding positive; exit when funding turns negative or risk limits hit.

## Benchmark
Hold spot only / risk-free.

## Known confounders
Funding rates volatile and can turn negative (negative in ~14% of periods over the full span);
the 2020-2021 bull regime dominates the mean; single venue for the price legs; live Binance/Bybit
APIs are geo-blocked from this environment (the archive is reachable instead); funding settlement
timing is not observable inside the 8h window.

## Falsification condition
No durable positive net carry after fees over multi-year history; <100 independent funding periods;
gross carry concentrated in a single regime (2020-2021) with no carry in the post-2022 sample.

## Cost model assumptions
Fees, borrow, margin, slippage per exchange schedule; capacity limited by Binance spot/perp
liquidity. Not yet applied: the candidate has no cost model in the repository (next cycle).

## Status
Pre-registered (Cycle 886). **Data blocker resolved (Cycle 889):** 2,464.7 days of 8h funding
history per symbol plus coupled daily spot/perp legs are cached and checksum-verified, and a
reproducible spot-long/perp-short return path is committed
(data/processed/crypto/*_carry_path.parquet). The candidate is now an **exploratory signal**
(testable, untested): no cost model, walk-forward split, block-bootstrap CI or promotion-gate test
has been run, so no edge is claimed. Gross carry only: +11.59%/yr BTC, +13.57%/yr ETH before
costs. Evidence: research/experiments/cryptofunding_002_data.md; Cycle 888 data note:
research/experiments/cryptofunding_001_data.md.

## Pre-registration (Cycle 890 evaluation)

### Rule set (fixed, no post-hoc selection)
1. **Always-on**: spot-long + perp-short carry every day (hold constant notional, rebalance daily to maintain constant notional due to drift). Entry/exit: always in.
2. **Funding-positive only**: same construction but only when funding is positive (`funding_cashflow > 0`); zero position otherwise. This is the rule named in the hypothesis.

**Trial count:** 2 rules × 2 symbols = 4 configurations. Reported explicitly; no other variants tested in this cycle.

### Cost model (all numbers and sources)
All costs are applied per the repository's flat cost model used by `research/cost_admissibility_screen.py`: **3 bp per unit of weight change** (commission + slippage as per `get_cost_params()`; repository default 1 bp commission + 2 bp slippage = 3 bp/unit).

Sources and assumptions:
- **Binance spot taker fee** on long leg: included in the 3 bp/unit turnover model (repository convention).
- **Binance USDT-margined perp maker/taker fee** on short leg: included in the 3 bp/unit turnover model (repository convention).
- **Slippage per leg**: included in the 3 bp/unit turnover model (repository convention).
- **Margin/financing cost on perp**: included implicitly in funding mechanics; funding cashflow is already separated in the path (`funding_cashflow`); no separate margin interest modeled beyond what funding represents.
- **Funding rounding**: assumed negligible / captured in observed funding rates from exchange data.
- **Positioning**: held constant-notional (one entry + daily drift rebalance). **Annual turnover in weight-change units** computed as `mean(daily |Δw|) * 252` where daily turnover is sum of absolute weight changes across legs; for constant-notional spot-long/perp-short with daily drift, daily turnover ≈ |spot_return| + |perp_return| per day (two legs rebalancing), annualized as reported.

### Chronological splits
- **Full sample:** 2020-01-02 to 2026-09-30 (2,464 days) - all data, reported in full.
- **Train/validation/test split (chronological, no post-hoc window exclusion):**
  - Train: 2020-01-02 to 2022-12-31
  - Validation: 2023-01-01 to 2024-12-31
  - Test (out-of-sample): 2025-01-01 to 2026-09-30
- **Post-2022 sub-sample** (required by falsification condition): 2023-01-01 to 2026-09-30 (separately reported).

### Benchmarks
- **Primary:** hold spot only (buy-and-hold spot)
- **Secondary:** risk-free rate (from `get_risk_free_rate()`)

### Promotion gates (from AGENTS.md)
- Net out-of-sample Sharpe >= 0.9
- Pooled out-of-sample trades > 100 (or equivalently sufficient independent observations)

### Falsification condition
No durable positive net carry after fees over multi-year history; < 100 independent funding periods; gross carry concentrated in a single regime (2020-2021) with no carry in the post-2022 sample. As stated in hypothesis.


## Cycle 890 Verdict (net-of-cost)
- **Evaluation:** Pre-registered (2 rules × 2 symbols), cost model 3 bp/unit weight change (repo flat). Chronological splits (train/val/test/post-2022) reported; block-bootstrap CI (126-day blocks, 2000 draws, seed 20261019); trial count 4.
- **Full-sample net (always-on):** BTC +7.98%/yr (Sharpe ~6.87, max DD -2.43%), ETH +9.33%/yr (Sharpe ~5.99, max DD -1.91%); turnover ~10.6/14.5 units/yr.
- **Full-sample net (funding-positive):** BTC +8.81%/yr (Sharpe ~8.34, max DD -0.35%), ETH +10.31%/yr (Sharpe ~7.43, max DD -0.27%); turnover lower (~9.09/12.47 units/yr).
- **Post-2022 (2023-01-01+):** Still positive net across configs (e.g. ETH funding-positive post-2022 ann net ~+9.4%, Sharpe ~7.8; BTC funding-positive ~+8.1%, Sharpe ~8.4). No collapse to zero.
- **Out-of-sample (2025-01-01+):** Strong net Sharpe across configs (pooled OOS Sharpe ~9.75, pooled OOS trades ~2335). Promotion gate (net OOS Sharpe >= 0.9 and > 100 pooled OOS trades): **PASS**.
- **Cost screen:** Added row to `research/cost_admissibility_screen.py`; break-even ~69.2 bp/unit, gate headroom ~34.5 bp/unit, **ADMISSIBLE** at 3 bp/unit; screen still **OVERALL: PASS**.
- **Verdict:** **exploratory signal** — net-positive after documented costs across rules/symbols with good risk-adjusted metrics and post-2022 persistence; mechanism plausible (funding carry). However, regime-dependent, venue-specific (Binance), and promotion to a "credible candidate for further validation" requires more conservative walk-forward implementation matching repo conventions and live-fee verification. Do **not** promote without additional robustness checks; do not tune further in this cycle (trial count declared).
- **Evidence:** `research/experiments/cryptofunding_002_evaluation.md`, `research/reports/cost_admissibility_screen_001.md`, updated `research/reports/opportunity_shortlist.md`.
