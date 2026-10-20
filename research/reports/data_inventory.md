# Data & Cost Inventory

**Generated:** 2026-10-12 07:52:57 UTC
**Code revision:** a5d5971
**Method:** Programmatic scan of `data/raw/` and `data/processed/` by `research/run_cycle11.py` (Cycle 11). No backtests run; all statistics are descriptive properties of cached artifacts.
**Revision (Cycle 873):** `^VIX` row corrected to real cache (5,514 rows, 2004-11-18 .. 2026-10-16); overview total recomputed (128,042 → 125,054).
**Revision (Cycle 889):** crypto spot/perp/funding rows updated — Binance public archive (SHA256-verified per file) added to data/raw/crypto/ and data/processed/crypto/; the OKX-only 'PARTIAL' verdicts above are superseded.

## Overview

The repository currently caches **19 raw price files** (125,054 total rows, 4.53 MB) covering **19 symbols** at daily frequency, plus **6 processed artifacts** from Cycles 2-10 (simulation, trades, weights, go/no-go history, paper-trading state).

Since Cycle 889 it also caches **8 crypto files** (25,242 rows, 1.05 MB) under `data/raw/crypto/`
and **2 processed carry-path files** (4,928 rows, 0.39 MB) under `data/processed/crypto/`: the
Binance public archive's funding rates and daily spot/perp klines, plus the OKX funding
cross-check. Total under `data/raw/`: 35 parquet files, 174,044 rows, 6.36 MB.

All raw data was sourced from Yahoo Finance via `yfinance` (see `src/data/yfinance_fetcher.py`) and cached as parquet in `data/raw/`. Point-in-time safety: the fetcher only downloads data up to the requested end date; signals in the simulation engine are shifted by one day.

## Price Data (data/raw/ cache)

| Symbol | Asset Class | Rows | Fields | Start | End | Years | Frequency | Close Complete | Ann. Vol | Duplicate Dates |
|--------|-------------|------|--------|-------|-----|-------|-----------|----------------|----------|-----------------|
| DBC | Broad commodity ETF | 5,201 | Open, High, Low, Close, Volume | 2006-02-06 | 2026-10-08 | 20.7 | Daily | 100.0% | 19.4% | 0 |
| EEM | Emerging markets equity ETF | 5,911 | Open, High, Low, Close, Volume | 2003-04-14 | 2026-10-09 | 23.5 | Daily | 100.0% | 27.1% | 0 |
| EFA | Developed international equity ETF | 6,317 | Open, High, Low, Close, Volume | 2001-08-27 | 2026-10-09 | 25.1 | Daily | 100.0% | 20.8% | 0 |
| GLD | Gold commodity ETF | 5,507 | Open, High, Low, Close, Volume | 2004-11-18 | 2026-10-09 | 21.9 | Daily | 100.0% | 18.3% | 0 |
| IWM | US small-cap equity ETF (Russell 2000) | 6,632 | Open, High, Low, Close, Volume | 2000-05-26 | 2026-10-09 | 26.4 | Daily | 100.0% | 23.8% | 0 |
| QQQ | Broad US equity ETF (Nasdaq-100) | 6,940 | Open, High, Low, Close, Volume | 1999-03-10 | 2026-10-09 | 27.6 | Daily | 100.0% | 26.9% | 0 |
| SPY | Broad US equity ETF (S&P 500) | 8,482 | Open, High, Low, Close, Volume | 1993-01-29 | 2026-10-09 | 33.7 | Daily | 100.0% | 18.6% | 0 |
| TLT | US long Treasury bond ETF (20+ year) | 6,089 | Open, High, Low, Close, Volume | 2002-07-30 | 2026-10-09 | 24.2 | Daily | 100.0% | 14.3% | 0 |
| VNQ | US REIT ETF | 5,542 | Open, High, Low, Close, Volume | 2004-09-29 | 2026-10-08 | 22.0 | Daily | 100.0% | 28.3% | 0 |
| XLB | Materials sector ETF | 6,991 | Open, High, Low, Close, Volume | 1998-12-22 | 2026-10-08 | 27.8 | Daily | 100.0% | 23.5% | 0 |
| XLE | Energy sector ETF | 6,991 | Open, High, Low, Close, Volume | 1998-12-22 | 2026-10-08 | 27.8 | Daily | 100.0% | 28.6% | 0 |
| XLF | Financials sector ETF | 6,991 | Open, High, Low, Close, Volume | 1998-12-22 | 2026-10-08 | 27.8 | Daily | 100.0% | 28.2% | 0 |
| XLI | Industrials sector ETF | 6,991 | Open, High, Low, Close, Volume | 1998-12-22 | 2026-10-08 | 27.8 | Daily | 100.0% | 21.1% | 0 |
| XLK | Technology sector ETF | 6,991 | Open, High, Low, Close, Volume | 1998-12-22 | 2026-10-08 | 27.8 | Daily | 100.0% | 26.0% | 0 |
| XLP | Consumer Staples sector ETF | 6,991 | Open, High, Low, Close, Volume | 1998-12-22 | 2026-10-08 | 27.8 | Daily | 100.0% | 15.3% | 0 |
| XLU | Utilities sector ETF | 6,991 | Open, High, Low, Close, Volume | 1998-12-22 | 2026-10-08 | 27.8 | Daily | 100.0% | 19.3% | 0 |
| XLV | Health Care sector ETF | 6,991 | Open, High, Low, Close, Volume | 1998-12-22 | 2026-10-08 | 27.8 | Daily | 100.0% | 17.9% | 0 |
| XLY | Consumer Discretionary sector ETF | 6,991 | Open, High, Low, Close, Volume | 1998-12-22 | 2026-10-08 | 27.8 | Daily | 100.0% | 22.6% | 0 |
| ^VIX | CBOE Volatility Index (NOT directly tradeable) | 5,514 | Open, High, Low, Close, Volume | 2004-11-18 | 2026-10-16 | 21.9 | Daily | 100.0% | 114.2% | 0 |

**Source:** Yahoo Finance (yfinance 1.7.0), daily OHLCV, timezone-normalized to UTC, cached as parquet.

**Data quality observations (computed from cache):**
- All 19 files are daily frequency (median inter-row gap >= 0.9 days); no intraday history is cached.
- Close-price completeness is 100% for all symbols after the fetcher's forward-fill alignment (each symbol is observed on every aligned date).
- No duplicate dates in any cached file.
- Longest history: SPY 8,482 rows (1993-01-29 to 2026-10-09).
- Core 7-asset candidate universe has 5,507 common trading days across all members (intersection of calendars).
- ^VIX is an **index**, not a directly tradeable instrument; no VIX futures, VIX ETNs (VXX/UVXY), or options history is cached.

## Crypto Data (data/raw/crypto/ cache)

Source: Binance **public data archive** (`data.binance.vision`), monthly ZIPs, every object
SHA256-verified against the published `.CHECKSUM` before parsing; the live Binance/Bybit APIs are
geo-blocked from this environment (HTTP 451 / 403). The OKX funding files are the independent
cross-check collected in Cycle 888.

| File | Market | Rows | Fields | Start | End | Frequency | Integrity |
|---|---|---|---|---|---|---|---|
| `BTC_USDT_USDT_funding_binance.parquet` | Binance BTCUSDT perp (funding) | 7,395 | timestamp, datetime, fundingRate, symbol, funding_interval_hours | 2020-01-01 00:00Z | 2026-09-30 16:00Z | 8h | 81/81 objects verified; 0 missing 8h periods; 0 duplicate timestamps |
| `ETH_USDT_USDT_funding_binance.parquet` | Binance ETHUSDT perp (funding) | 7,395 | timestamp, datetime, fundingRate, symbol, funding_interval_hours | 2020-01-01 00:00Z | 2026-09-30 16:00Z | 8h | 81/81 objects verified; 0 missing 8h periods; 0 duplicate timestamps |
| `BTCUSDT_spot_1d_binance.parquet` | Binance spot BTCUSDT | 2,465 | timestamp, datetime, OHLC, volume, quote_volume, trades, symbol, market | 2020-01-01 | 2026-09-30 | daily | 81/81 objects verified |
| `BTCUSDT_perp_1d_binance.parquet` | Binance BTCUSDT perp (price) | 2,465 | as above | 2020-01-01 | 2026-09-30 | daily | 81/81 objects verified |
| `ETHUSDT_spot_1d_binance.parquet` | Binance spot ETHUSDT | 2,465 | as above | 2020-01-01 | 2026-09-30 | daily | 81/81 objects verified |
| `ETHUSDT_perp_1d_binance.parquet` | Binance ETHUSDT perp (price) | 2,465 | as above | 2020-01-01 | 2026-09-30 | daily | 81/81 objects verified |
| `BTC_USDT_USDT_funding.parquet` | OKX BTC/USDT:USDT swap (funding) | 296 | timestamp, datetime, fundingRate, symbol | 2026-07-13 16:00Z | 2026-10-20 00:00Z | 8h | Cycle 888 collection |
| `ETH_USDT_USDT_funding.parquet` | OKX ETH/USDT:USDT swap (funding) | 296 | timestamp, datetime, fundingRate, symbol | 2026-07-13 16:00Z | 2026-10-20 00:00Z | 8h | Cycle 888 collection |

Processed: `data/processed/crypto/{BTCUSDT,ETHUSDT}_carry_path.parquet` — 2,464 daily rows per
symbol (2020-01-02..2026-09-30), the daily spot-long/perp-short path (funding cashflow, spot/perp
returns, basis convergence, basis level). Machine-readable provenance:
`research/reports/binance_crypto_manifest.json`; record: `research/experiments/cryptofunding_002_data.md`; net-of-cost evaluation `research/experiments/cryptofunding_002_evaluation.md` (Cycle 890), cost screen extended.

## Simulation & Paper-Trading Artifacts (data/processed/)

### simulation_candidate_001.parquet — daily simulation series
- Rows: 8,482 | Range: 1993-01-29 to 2026-10-09
- Fields: net_return, gross_return, cost, turnover, exposure, n_positions, regime_exposure, vol_scale, dd_scale, overlay_drawdown, drawdown, weight_SPY, weight_QQQ, weight_IWM, weight_TLT, weight_GLD, weight_EFA, weight_EEM
- Contains: net/gross returns, per-trade cost drag, turnover, exposure, position count, regime exposure, vol_scale, dd_scale, overlay drawdown, portfolio drawdown, per-asset weights.
- Mean daily net return: 0.0517% | Mean exposure: 58.9% | Cumulative turnover: 409.4x

### trades_candidate_001.parquet — trade log
- Trades: 13,631 (6,354 buys / 7,277 sells)
- Per-symbol counts: EEM: 1,656, EFA: 2,038, GLD: 1,439, IWM: 2,274, QQQ: 2,743, SPY: 3,065, TLT: 416
- Cumulative cost drag (weight-change x 3bps, summed): 0.1228

### weights_full_history.parquet — point-in-time weights
- Rows: 8,482 | Range: 1993-01-29 to 2026-10-09 | Assets: SPY, QQQ, IWM, TLT, GLD, EFA, EEM

### go_no_go_history.parquet — historical go/no-go replay (Cycle 10)
- Evaluations: 2,205 | Range: 2018-01-02 to 2026-10-09
- Decisions: INCONCLUSIVE: 807, NO-GO: 1,398

### paper_trading_state.yaml + paper_trading/ — prospective artifacts (Cycle 8/9)
- Paper track record: 5 days (minimum required for GO: 63 days)
- Last run: 2026-10-09 | NAV: $102,109.13 | Active positions: 4
- Daily artifacts: daily_pnl_20261009.parquet, positions_20261009.parquet, regime_20261009.parquet, risk_state_20261009.parquet (dates: 20261009)

## Cost Model

| Component | Value | Source |
|-----------|-------|--------|
| Commission | 1.0 bps/trade | config/settings.yaml:backtest.default_commission_bps |
| Slippage | 2.0 bps/trade | config/settings.yaml:backtest.default_slippage_bps |
| Round-trip (candidate) | 3.0 bps | config/simulation_candidate_001.yaml:cost_model |
| Funding rate | 0.0% annualized (placeholder) | config/settings.yaml:backtest.default_funding_rate_annual |
| Risk-free rate | 2.0% (flat) | config/settings.yaml:evaluation.risk_free_rate_annual |
| Minimum trade size | $10.00 | config/settings.yaml:backtest.min_trade_size_usd |

**Cost model gaps:** no bid-ask spread model, no borrow/short-sale cost model, no futures roll cost model, no market-impact model (flat slippage assumption), no latency model, flat (not historical) risk-free rate. OKX spot/swap fee tiers (0.02-0.10%) are documented in the Cycle 1 inventory; since Cycle 889 the crypto spot/perp price and funding series are cached (data/raw/crypto/, data/processed/crypto/), so a crypto cost model can be applied, but no fee/slippage/margin schedule has been applied to the carry path yet.

## Execution Assumptions

| Parameter | Value | Source |
|-----------|-------|--------|
| Signal lag | 1 day (signal on T-1 close) | config/simulation_candidate_001.yaml:execution |
| Price field | Close (EOD) | config/simulation_candidate_001.yaml:execution |
| Rebalance schedule (execution) | daily | config/simulation_candidate_001.yaml:execution |
| Signal horizon | monthly (~21 trading days) | config/simulation_candidate_001.yaml:signal |
| Timezone | UTC | config/simulation_candidate_001.yaml:execution |

Close-to-close execution with a 1-day signal lag is the validated convention (Cycle 5/6/7); `price_field: Open` is supported for prospective studies but was not used in any validated result.

## Universe Definitions

| Universe | Members | Used In |
|----------|---------|---------|
| Core candidate (tsmomentum_spytrend_001) | SPY, QQQ, IWM, TLT, GLD, EFA, EEM | Cycles 2-10 (config/simulation_candidate_001.yaml) |
| Sector rotation | XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY | Cached, untested |
| Full cached ETF universe | DBC, EEM, EFA, GLD, IWM, QQQ, SPY, TLT, VNQ, XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY | Available for cross-sectional tests |
| Volatility indicator | ^VIX (index only, not tradeable) | Available as regime input |
| Benchmarks | BTC-USD, ETH-USD, SPY | config/settings.yaml:evaluation |

## Gaps and Limitations

**Missing from the local cache** (per the Cycle 1 live-API verification, some of these are fetchable at runtime via yfinance/ccxt, but they are NOT point-in-time cached in this repository and cannot be used for reproducible offline backtests):

| Data Class | Cached? | Limitation |
|------------|---------|------------|
| Crypto spot/perpetual data (BTC-USD, ETH-USD, funding rates) | YES | Cycle 889: Binance public archive cached to data/raw/crypto/ — {BTC,ETH}_USDT_USDT_funding_binance.parquet (7,395 8h records per symbol, 2020-01-01..2026-09-30, 0 missing 8h periods, 0 duplicate timestamps, every archive file SHA256-verified) plus {BTC,ETH}USDT_{spot,perp}_1d_binance.parquet (2,465 daily rows each). OKX series (296x8h per symbol, 2026-07-13..2026-10-20) retained as an independent cross-check. Single venue for the price legs; archive publishes no October-2026 file yet. |
| Commodity/rate futures (CL=F, GC=F, ZB=F, ...) | NO | yfinance continuous futures have undocumented roll logic; no separate spot series for basis |
| Forex spot (EURUSD=X, ...) | NO | No interest-rate differentials or forward curves available |
| Intraday history (1m/5m) | NO | Only recent 1-day/7-day windows verified live; no multi-year intraday history |
| VIX futures / VIX ETNs (VX=F, VXX, UVXY) | NO | ^VIX index cached but is not tradeable; no tradeable volatility instrument |
| Historical options data (prices, IV series) | NO | Only near-term live chains verified; no historical options data |
| Funding rate history | YES | Cached in data/raw/crypto/ (Binance BTC/ETH USDT-margined perps, 7,395x8h each, 2,464.7 days; OKX 296x8h each as cross-check). Blocker resolved in Cycle 889; a daily spot-long/perp-short carry path is committed to data/processed/crypto/*_carry_path.parquet. |
| Spot-perp basis series | YES (Cycle 889) | Cached: data/raw/crypto/{BTC,ETH}USDT_{spot,perp}_1d_binance.parquet (daily closes, 2020-01-01..2026-09-30); basis and its daily convergence are computed in data/processed/crypto/*_carry_path.parquet |
| Securities lending / borrow rates | NO | No source configured; blocks credible short-side cost modeling |

**Other limitations:**
- Paper-trading track record is only 5 days (from test data); the go/no-go gate requires 63 days.
- Paper-trading daily artifacts exist for a single date (2026-10-09).
- Forward-filled alignment means non-trading days carry stale prices within each symbol's series (standard for daily ETF data).
- ETF-level survivorship bias is minimal (all cached ETFs are still listed), but constituent-level survivorship is not modeled.
- No order-book depth or tick data; intraday execution quality cannot be validated from cache.

---

*Report generated by `research/run_cycle11.py` (Cycle 11). Raw cache: 19 files, 128,042 rows. Processed artifacts: 6 entries.*
