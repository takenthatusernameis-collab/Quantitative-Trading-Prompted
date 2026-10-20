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
