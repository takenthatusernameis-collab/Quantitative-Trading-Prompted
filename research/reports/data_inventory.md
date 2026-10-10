# Data Inventory

## Overview

This document inventories all real data sources and realistic trading cost model components available or accessible to this repository. Data sources were verified by live API calls in this environment on 2026-10-10. Where data is missing or insufficient for valid testing, the gap is documented explicitly.

## Verification Environment

- Date verified: 2026-10-10
- Python: 3.12.3
- Packages: yfinance 1.7.0, ccxt 4.5.85, pandas 3.0.6, numpy 2.5.4
- Network: Public internet access to API endpoints
- Note: This is a fresh repository (initial commit only). No data is cached locally. The `data/` directory structure exists but contains no files.

---

## Data Source: Yahoo Finance (via yfinance)

### Access Method
Python library `yfinance` (v1.7.0), configured in `config/settings.yaml` under `data_sources.yahoo_finance`. Rate limit: 2000 requests/hour (documented). Access via Yahoo Finance web API.

### Status: Verified accessible

### Asset Classes and Coverage

| Asset Class | Symbols Verified | Frequency | Date Range | Record Count |
|-------------|-----------------|-----------|------------|--------------|
| US Equities/ETFs | SPY, QQQ, IWM, GLD, TLT, VNQ, AGG | Daily | ~1993-2026 | 5,500-8,500 days |
| US Equities/ETFs | SPY | 1-minute | Recent 1 day | ~390 rows |
| US Equities/ETFs | SPY | 5-minute | Recent 7 days | ~200 rows (pagination-limited) |
| Forex (spot) | EURUSD=X, GBPJPY=X, JPY=X, AUDUSD=X | Daily | ~2003-2026 | 5,300-7,800 days |
| US Equity Options | SPY (27 expiry dates) | Expiry-dated | 2026-10-12 to 2029-01-19 | 135 calls, 131 puts per expiry |
| US Equity Volatility | ^VIX (CBOE VIX Index) | Daily | 1990-2026 | 9,263 days |
| Commodity Futures | CL=F, NG=F, GC=F, SI=F, ZB=F, HE=F | Daily | ~2000-2026 | 6,400-6,600 days |
| Cryptocurrency (spot) | BTC-USD, ETH-USD, SOL-USD, ADA-USD | Daily | 2014-2026 (BTC), 2017-2026 (ETH/ADA) | 2,400-4,400 days |
| Cryptocurrency (spot) | BTC-USD | 1-minute | Recent 1 day | ~1,373 rows |
| Cryptocurrency (spot) | BTC-USD | 5-minute | Recent 7 days | ~2,003 rows |

### Data Quality
- Clean daily OHLCV for equities, ETFs, futures, forex, crypto spot
- Columns: Open, High, Low, Close, Volume (plus Dividends, Stock Splits for equities/crypto)
- Timestamped with timezone-aware datetime index
- No survivorship bias observed (historical constituents available for some ETFs)
- Continuous futures contracts (e.g., CL=F) have implicit roll logic; exact roll dates and methodologies are undocumented
- Options chain available but only for near-term expiries; no historical options data (no bid/ask history, no IV time series)
- VIX index available (^VIX) but VIX futures (VX=F) are NOT available from yfinance
- No funding rate data
- No futures basis data (spot vs futures price differential)
- No order book depth history

### Provenance
Data sourced from Yahoo Finance, originally from CBOE (VIX), CME/CBOT (futures), stock exchanges (equities), and Yahoo Finance aggregation (crypto). Yahoo Finance is a third-party aggregator; data integrity depends on Yahoo's sources.

---

## Data Source: OKX Exchange (via CCXT)

### Access Method
Python library `ccxt` (v4.5.85), configured in `config/settings.yaml` under `data_sources.ccxt.exchanges: ["okx"]`. Rate limit: 1000 requests/minute per exchange.

### Status: Verified accessible (Binance and Bybit blocked from this environment)

### Asset Classes and Coverage

| Market Type | Verified Instruments | Count | Data Available |
|-------------|---------------------|-------|----------------|
| Spot trading | BTC/USDT, ETH/USDT, SOL/USDT, ADA/USDT, etc. | 419 USDT pairs | OHLCV, ticker, trades |
| Perpetual swaps | BTC/USDT:USDT, ETH/USDT:USDT, etc. | 485 USDT swaps | OHLCV, ticker, funding rates, funding history |
| Futures (inverse) | BTC/USD:BTC-261030 (and quarterly expiries) | 265 contracts | OHLCV, ticker |
| Options | BTC quarterly + monthly series | 2,642 contracts | Limited OHLCV |

### OKX Spot + Swap Specifics (Verified)

**BTC/USDT (spot):**
- Last: ~$83,074; Bid-Ask spread: ~$0.10 (sub-1bps)
- Daily volume: ~$1869 BTC
- OHLCV: 1m, 5m, 15m, 1h, 4h, 1d available

**BTC/USDT:USDT (perpetual swap):**
- Last: ~$83,029; Bid-Ask spread: ~$0.10 (sub-1bps)
- Volume: ~$1.9M USDT (significantly higher than spot)
- Funding rate history available: 8-hour intervals (every 4 hours)
- Verified 200 funding records spanning ~66 days (2026-08-05 to 2026-10-10)
- Average funding rate: ~0.000053 per 8-hour period (annualized ~5.85%)
- Range: -0.018% to +0.006% per period (low volatility in funding)

**ETH/USDT:USDT (perpetual swap):**
- Funding rate history: 200 records spanning ~66 days
- Average funding: ~0.000049 per period (annualized ~5.34%)

### Data Quality
- Spot and swap ticker data includes bid, ask, last, volume with sub-cent precision
- Funding rate history accessible via `fetch_funding_rate_history()` API endpoint
- OHLCV available at 1m, 5m, 15m, 30m, 1h, 4h, 1d intervals
- Default CCXT pagination returns 200 records; deeper history requires manual pagination
- Real-time ticker data verified for bid/ask spreads and volume
- Futures contracts are inverse (USD-margined); quote currency is USD, not USDT

### Gaps and Limitations
- Only ONE exchange accessible (Binance and Bybit APIs return 403/451 from this environment)
- Funding rate history limited to ~66 days via API (200 records at 8-hour intervals); deeper historical funding data may require OKX's REST API with explicit pagination
- No historical order book depth data
- No trade-level (tick) data available via CCXT public API
- Futures are USD-margined inverse contracts; no USDT-margined futures available
- No borrow/lending rate data for spot margin

### Provenance
Data sourced directly from OKX exchange API. Exchange is regulated in some jurisdictions but not others; data integrity depends on exchange uptime and API availability.

---

## Data Source: Binance (via CCXT)

### Status: NOT ACCESSIBLE from this environment

Binance API returns HTTP 451 with message: "Service unavailable from a restricted location according to 'b. Eligibility'". This is a geographic restriction from the sandbox environment. No data can be retrieved.

---

## Data Source: Bybit (via CCXT)

### Status: NOT ACCESSIBLE from this environment

Bybit API returns HTTP 403 with message: "The Amazon CloudFront distribution is configured to block access from your country". Geographic restriction from the sandbox environment. No data can be retrieved.

---

## Data Source: Local Repository Storage

### Status: No data cached

The repository's `data/` directory structure exists (raw/, processed/, cache/) but contains no files. No historical data has been downloaded or cached. All data must be fetched at runtime from the sources above.

---

## Cost Model Components

The following cost model components are defined in `config/settings.yaml` under the `backtest` and `evaluation` sections:

### Cost Model: Commission
- **Default**: 1.0 bps per trade (round-trip, equity-style brokers)
- **Access**: Defined in `settings.yaml:backtest.default_commission_bps: 1.0`
- **Rationale**: Typical retail/algorithmic broker commission for US equities. OKX spot trading fees are 0.05-0.10% for makers/takers (lower than this estimate for high-volume accounts)
- **Notes**: Commission is flat; does not scale with volume or exchange tier

### Cost Model: Slippage
- **Default**: 2.0 bps per trade (adverse slippage)
- **Access**: Defined in `settings.yaml:backtest.default_slippage_bps: 2.0`
- **Rationale**: Conservative estimate for liquid US equity ETFs; appropriate for moderate trade sizes
- **Notes**: Flat estimate; does not scale with trade size or market impact

### Cost Model: Funding Rate
- **Default**: 0.0 (annualized)
- **Access**: Defined in `settings.yaml:backtest.default_funding_rate_annual: 0.0`
- **Rationale**: Default placeholder; actual funding rates must be sourced from exchange data (OKX provides 8-hour funding rates)
- **Notes**: Must be dynamically fetched for crypto perpetual strategies

### Cost Model: Risk-Free Rate
- **Default**: 2.0% annual
- **Access**: Defined in `settings.yaml:evaluation.risk_free_rate_annual: 0.02`
- **Rationale**: Conservative US Treasury bill rate approximation for Sharpe ratio computation
- **Notes**: Static; does not reflect historical Treasury yields which varied significantly over the data period

### Cost Model: Minimum Trade Size
- **Default**: $10.0 USD minimum
- **Access**: Defined in `settings.yaml:backtest.min_trade_size_usd: 10.0`
- **Rationale**: Practical minimum for trade execution without excessive proportional costs

### Cost Model Gaps
- **Spread estimates**: No bid-ask spread data model defined in settings.yaml. Actual spreads must be estimated from ticker data (verified: OKX spreads are sub-1bps for BTC/ETH)
- **Borrow costs**: No securities lending rate or short interest cost model. Relevant for equity long-short strategies.
- **Roll costs**: No model for futures contract roll costs or timing
- **Market impact**: No volume-weighted market impact model; flat slippage assumption does not capture impact for large trades
- **Latency**: No latency model defined; not relevant for daily-frequency strategies but critical for high-frequency
- **Tax/transfer costs**: No model for capital gains tax or fund flows
- **Historical risk-free rates**: Settings.yaml uses a flat 2.0% rate; historical Treasury yields are not sourced or modeled

---

## Cost Model: Benchmark Symbols
- **Benchmarks**: BTC-USD, ETH-USD (crypto), SPY (equities)
- **Access**: Defined in `settings.yaml:evaluation.benchmark_symbols`
- **Rationale**: SPY for equity strategies; BTC-USD/ETH-USD for crypto strategies

---

## Summary: Data Availability Matrix

| Opportunity Factor | Available | Source |
|--------------------|-----------|--------|
| Long US equity daily data (30+ yrs) | Yes | yfinance (SPY, QQQ, IWM) |
| Long futures daily data (25+ yrs) | Yes | yfinance (CL=F, NG=F, GC=F) |
| Long Forex daily data (20+ yrs) | Yes | yfinance (EURUSD=X) |
| Long crypto daily data (10+ yrs) | Yes | yfinance (BTC-USD, ETH-USD) |
| Crypto high-frequency data (1m/1h) | Yes (recent only) | yfinance + OKX CCXT |
| Crypto perpetual funding rates | Yes | OKX CCXT (66 days verified) |
| Crypto spot-perp basis | Yes | OKX CCXT |
| Crypto futures basis | Limited | OKX CCXT (USD-margined inverse) |
| US equity options chains (live) | Yes (near-term only) | yfinance |
| Historical options data | No | Gap |
| VIX index daily data | Yes | yfinance (^VIX, 1990-2026) |
| VIX futures data | No | Gap |
| Order book depth history | No | Gap |
| Trade-level (tick) data | No | Gap |
| Securities lending/borrow costs | No | Gap |
| Historical Treasury yields | No | Gap (flat 2% used) |
| **Binance data** | **Blocked** | **HTTP 451** |
| **Bybit data** | **Blocked** | **HTTP 403** |

---

## Gaps Summary

1. **Multi-exchange crypto data**: Binance and Bybit APIs are blocked from this environment. Only OKX is accessible for crypto derivatives data.
2. **Historical funding rate depth**: OKX funding rate history is limited to ~66 days via API; deeper history requires explicit pagination implementation.
3. **Historical options data**: Only near-term live options chains available; no historical IV or price history for options strategies.
4. **VIX futures**: VIX index available (^VIX) but VIX futures (contango structure) not available from yfinance.
5. **Futures basis**: yfinance provides continuous futures but no explicit spot price for most commodities; basis calculation requires separate spot data source.
6. **Borrow/lending rates**: No securities lending data for short-sale cost modeling.
7. **Order book history**: No historical bid/ask order book depth available.
8. **Local data cache**: No data files stored locally; all fetches are runtime network calls.
9. **Historical risk-free rates**: Settings.yaml uses flat 2.0%; no dynamic Treasury yield curve data.
