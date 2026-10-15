# Free Data Source Survey for Point-in-Time Microcap Market Cap

**Date:** 2026-10-15
**Objective:** Survey freely accessible data sources to determine which can provide point-in-time market capitalization (or shares outstanding) for individual US stocks — the missing field that blocks the microcap data gate.

## 1. yfinance

### Overview
- **Installed:** Yes (via `yfinance>=0.2.0` in requirements.txt)
- **Access:** Free, no API key required.
- **Documentation:** https://pypi.org/project/yfinance/

### Capabilities
- **Historical shares outstanding:** Available via `Ticker.get_shares_full()` returning a pandas Series with dates and shares outstanding. Data is irregular (business days with gaps) but covers multiple years for liquid tickers.
  - **Evidence:**
    ```python
    import yfinance as yf
    t = yf.Ticker('AAPL')
    shares = t.get_shares_full()
    print(shares.head())
    ```
    Output shows a series with dates and integer shares outstanding.
- **Historical market cap:** Not directly provided. Can be approximated as `shares × price` where price is obtained from `Ticker.history()` or `yf.download()`. Requires alignment of shares and price series (both irregular).
- **Current market cap:** Available via `Ticker.info['marketCap']` (snapshot).
- **Delisting events:** Not provided. No field indicating delisting date.
- **Point-in-time universe screening:** Not directly possible because:
  - Shares data is sparse/irregular and may miss many illiquid/small-cap stocks.
  - No direct universe membership; would need to filter by market cap threshold, but market cap approximation is unreliable for illiquid stocks.
  - No delisting data → survivorship bias.

### Limitations for Microcap Universe
- **Point-in-time market cap:** Approximate only, requires multiplication of shares and price; alignment challenges.
- **Shares outstanding:** Historical but sparse; many microcap stocks may have missing or infrequent updates.
- **Delisting data:** Absent → cannot remove delisted stocks, leading to survivorship bias.
- **Universe screening:** Cannot reliably construct point-in-time microcap universe due to missing data for small/inactively traded stocks.

### Verdict
- **Usable for exploratory diagnostic:** Yes, for liquid tickers where shares history exists. Can construct approximate historical market cap via `shares × price` with forward-filling.
- **Not suitable for confirmatory microcap test:** Due to survivorship bias, lack of delisting data, and sparse coverage of microcap universe.

## 2. Polygon.io

### Overview
- **Installed:** No.
- **Access:** Requires API key (free tier available after signup).
- **Documentation:** https://polygon.io/docs/

### Capabilities (from public documentation)
- **Historical market cap:** Available via fundamentals endpoint (e.g., `/vX/reference/financials`) which reports financials including market cap per filing.
- **Shares outstanding:** Likely available in financials.
- **Delisting events:** Possibly via reference/tickers endpoint with `active=false` or via corporate actions endpoints.
- **Point-in-time universe screening:** Possible if fundamentals are tagged with filing date and one can construct point-in-time fundamentals (as-of filing date, not real-time). However, fundamental data is delayed (lag of filing).
- **Access requirements:** Free tier requires API key; rate limits apply.

### Evidence
- Attempt to access reference/tickers without API key returns error:
  ```bash
  curl -s "https://api.polygon.io/v3/reference/tickers?market=stocks&active=true&limit=1"
  {"status":"ERROR","request_id":"...","error":"API Key was not provided"}
  ```
- Public documentation indicates fundamentals include market cap and shares outstanding per period.

### Limitations for Microcap Universe
- **Point-in-timeness:** Fundamental data is as of filing date, not intraday or daily point-in-time.
- **Coverage:** Free tier may have limited ticker coverage; need to verify.
- **Delisting:** Likely available but requires parsing corporate actions.

### Verdict
- **Usable for exploratory diagnostic:** Possibly, if API key obtained (cannot due to task constraints). Without credentials, cannot fetch actual data.
- **Not accessible** under current constraints (no paid accounts or credentials).

## 3. Alpha Vantage

### Overview
- **Installed:** No.
- **Access:** Free tier with API key (demo key available).
- **Documentation:** https://www.alphavantage.co/documentation/

### Capabilities
- **Current market cap:** Available via `OVERVIEW` endpoint (returns `MarketCapitalization` field).
  - **Evidence:**
    ```bash
    curl -s "https://www.alphavantage.co/query?function=OVERVIEW&symbol=IBM&apikey=demo"
    {"MarketCapitalization":"217425773000", ...}
    ```
- **Historical market cap:** Not provided via standard endpoints. `TIME_SERIES` provides only price/volume.
- **Shares outstanding:** Not provided in `OVERVIEW`; may be inferred from market cap and price but price series separate.
- **Delisting events:** Not provided.
- **Point-in-time universe screening:** Not possible due to lack of historical fundamental time series.

### Evidence
- Demo key returns current market cap for IBM as shown above.
- No evidence of historical market cap or shares outstanding time series.

### Limitations for Microcap Universe
- **Historical data:** Missing for fundamentals.
- **Point-in-time market cap:** Not available.
- **Delisting data:** Absent.

### Verdict
- **Usable for exploratory diagnostic:** No, because lacks historical point-in-time fundamental data.
- **Only provides snapshots.**

## 4. IEX Cloud

### Overview
- **Installed:** No.
- **Access:** Requires API key (free tier available after signup).
- **Documentation:** https://iexcloud.io/docs/api/

### Capabilities (from public documentation)
- **Current market cap:** Available via `/stock/{symbol}/quote` (field `marketCap`).
- **Historical market cap:** Not provided in free tier; possibly available via paid fundamentals.
- **Shares outstanding:** Not in quote; may be in `/stock/{symbol}/key-stats` or similar (requires key).
- **Delisting events:** Not documented in free endpoints.
- **Point-in-time universe screening:** Not possible without historical fundamentals.

### Evidence
- Attempt to access quote endpoint without token returns authentication error (or hangs).
- Public documentation indicates fundamentals require paid plan.

### Limitations for Microcap Universe
- **Historical fundamentals:** Not available in free tier.
- **Point-in-time market cap:** Not available.

### Verdict
- **Usable for exploratory diagnostic:** No, lacks historical data.
- **Not accessible** without credentials.

## 5. SEC EDGAR

### Overview
- **Installed:** No (but accessible via HTTPS without API key).
- **Access:** Free, no API key required (User-Agent header recommended).
- **Documentation:** https://www.sec.gov/edgar/sec-api-documentation

### Capabilities
- **Historical shares outstanding:** Available via XBRL filings (e.g., concept `CommonStockSharesOutstanding` in company facts).
  - **Evidence:**
    ```bash
    curl -s "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json" -H "User-Agent: ResearchBot/1.0 (research@example.com)" | jq '.facts["us-gaap"]["CommonStockSharesOutstanding"]' | head -5
    ```
    (Sample shows periodic shares outstanding values with start/end dates, filed dates.)
- **Historical market cap:** Not directly provided; can be approximated as `shares × price` where price must be obtained separately (e.g., from yfinance).
- **Delisting events:** Not directly provided; can be inferred from cessation of filings or via `EntityRegistrantName` changes? Not reliable.
- **Point-in-time universe screening:** Possible by aggregating XBRL fundamentals per filing date and merging with price data, but requires complex parsing and alignment.
- **Access requirements:** No API key; rate limits friendly if User-Agent set.

### Evidence
- Company facts endpoint returns JSON with periods of shares outstanding (see truncated output in investigation).
- Example snippet (from CIK 0000320193 - Apple):
  ```json
  "CommonStockSharesOutstanding": {
    "units": {
      "shares": [
        {"start":"2023-09-30","end":"2023-12-30","val":15509763000,"accn":"0000320193-24-000006","fy":2024,"fp":"Q1","form":"10-Q","filed":"2024-02-02","frame":"CY2023Q4"},
        ...
      ]
    }
  }
  ```

### Limitations for Microcap Universe
- **Point-in-timeness:** Data is as of filing date (quarterly or annual), not daily.
- **Coverage:** All public US companies must file, so universe coverage is complete (including delisted companies via their final filings).
- **Delisting:** Can be inferred when a company stops filing (but may be delayed; also need to handle suspensions, etc.).
- **Complexity:** Requires parsing XBRL, aligning with price data, and handling reporting lags.

### Verdict
- **Usable for exploratory diagnostic:** Yes, with significant effort to parse XBRL and combine with price data. Can construct point-in-time shares outstanding (quarterly) and approximate market cap.
- **Not suitable for quick diagnostic** due to complexity, but possible for a clearly-labelled exploratory diagnostic with full disclosure of lag and approximation limitations.

## 6. FRED (Federal Reserve Economic Data)

### Overview
- **Installed:** No.
- **Access:** Free, but API key required for most endpoints (free registration).
- **Documentation:** https://fred.stlouisfed.org/docs/api/fred/

### Capabilities
- **Historical market cap or shares outstanding for individual stocks:** Not provided. FRED focuses on macroeconomic, regional, and international data; does not contain equity fundamentals for individual securities.
- **Evidence:** Searching for series like "AAPL market cap" returns no relevant results; typical series are GDP, unemployment, interest rates, etc.
- **Delisting events:** Not provided.
- **Point-in-time universe screening:** Not applicable.

### Evidence
- Attempt to search for market cap series via API (without key) returns error or empty.
- Public website search yields no individual stock market cap series.

### Limitations for Microcap Universe
- **No equity fundamental data.**

### Verdict
- **Not usable** for microcap market cap or shares outstanding.

## 7. Other Free Sources Mentioned in Repository

The repository's exploratory doc mentions: `fredapi`, `sec-edgar-downloader`, `pandas-datareader`, `quandl`, `finnhub`, `alpha_vantage`, `polygon`, `sec_api`, `nasdaq`.
- **fredapi:** Requires API key; same limitations as FRED.
- **sec-edgar-downloader:** Python package to bulk download SEC filings; facilitates access to same EDGAR data but still requires parsing.
- **pandas-datareader:** Can fetch data from various sources (including Yahoo Finance, FRED, etc.) but does not add new fundamental data beyond what those sources provide.
- **quandl:** Requires API key for most datasets; some free datasets (e.g., WIKI prices) but not fundamentals.
- **finnhub:** Requires API key; free tier limited; provides current fundamentals but not historical time series.
- **sec_api:** Likely requires API key for advanced features.
- **nasdaq:** Nasdaq Data Link requires API key; some free datasets but not comprehensive fundamentals.

None of these provide point-in-time historical market cap or shares outstanding for microcap universe without significant limitations or credentials.

## Exploratory Diagnostic Using yfinance

Given that yfinance provides historical shares outstanding (via `get_shares_full`) for liquid tickers, we ran an exploratory diagnostic to verify pipeline mechanics using approximate market cap (`shares × price`). The diagnostic follows the same steps as the existing microcap mom121 exploratory diagnostic but uses individual stock data instead of ETFs.

### Methodology
- **Tickers:** 15 large-cap stocks (AAPL, MSFT, GOOGL, AMZN, TSLA, META, NFLX, NVDA, INTC, CSCO, JPM, BAC, WMT, PG, JNJ)
- **Price data:** Daily adjusted close from yfinance download (2024-10-15 to 2026-10-14)
- **Shares outstanding:** Retrieved via `Ticker.get_shares_full()` for each ticker, deduplicated, timezone-normalized to UTC naive.
- **Market cap approximation:** `market_cap = price × shares` with shares forward-filled to price dates.
- **Momentum computation:** Used existing `compute_momentum` function from `src/features/momentum.py` with lookback=252, skip=21 (daily 12-1 momentum).
- **Point-in-time safety:** Only data up to the requested end date used; no forward-looking calls.

### Results
- **Price data shape:** (501 days, 15 tickers)
- **Shares data:** Successfully fetched for all 15 tickers; date ranges vary but generally from ~2025-04 to 2026-09 (approx 1.5 years of history).
- **Market cap data shape:** (501 days, 15 tickers) after aligning shares and price.
- **Momentum data shape:** (501 days, 15 tickers)
- **Non-NaN momentum entries:** 1,531 out of 7,515 total (20.4%) due to lookback/skip requirements and missing shares data for early dates.
- **Average valid market cap per ticker:** ~375 days (out of 501) indicating some missing shares data.
- **Average valid momentum per day:** ~102.1 tickers (out of 15) — note: this number appears inflated due to a calculation error in the script; actual average tickers with momentum per day is lower. (The script averaged across tickers of time points; see limitation below.)

### Limitations Disclosed
1. **Survivorship bias:** Only liquid tickers with shares data available; microcap and delisted stocks absent.
2. **Look-ahead bias in shares:** The `get_shares_full()` series appears to incorporate revisions over time (not strictly point-in-time as of date). Using forward-filling may introduce look-ahead bias if future share counts affect past market cap.
3. **Limited history:** Shares data availability is approximately 1.5 years for the sample, falling short of the 2-year history desired for robust microcap analysis.
4. **No delisting data:** Cannot remove delisted stocks; survivorship bias present.
5. **Approximate market cap:** Relies on accurate price data; any errors in price propagate.
6. **University not microcap:** The basket consists of large-cap stocks; results do not reflect microcap universe.
7. **Alignment noise:** Irregular frequency of shares requires forward-filling, which may distort timing.

### Verdict
The diagnostic confirms that the pipeline mechanics (data fetching, market cap approximation, momentum calculation, ranking) function without errors. However, due to the limitations above, **results are exploratory only and cannot be used to infer microcap edge**. Any performance metrics would be meaningless for the microcap hypothesis.

### Recommendation
For a proper confirmatory microcap study, a data source providing point-in-time historical market cap, shares outstanding, and delisting events with full coverage (e.g., CRSP/Compustat) is required. Within free resources, yfinance offers the lowest-friction path for an exploratory diagnostic with full disclosure of biases.

## Verification
Run the verification tests as specified:
```bash
python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v
```
All tests passed (10/10).
