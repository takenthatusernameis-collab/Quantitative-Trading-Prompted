# Next Agent Task: Microcap mom121 — Evaluate Polygon.io API for Point-in-Time Fundamental Data

## Context

The previous cycle completed an exhaustive free-data-source survey (yfinance, ccxt, FRED, SEC EDGAR) and confirmed that no free source provides point-in-time historical market cap, shares outstanding, delisting events, or point-in-time universe membership for US stocks. An exploratory diagnostic using a current-ticker microcap basket verified the code mechanics of the momentum pipeline but confirmed severe survivorship bias. The hypothesis file (`research/hypotheses/mom121_microcap_001.md`) was updated to v0.3, documenting the survey, exploratory diagnostic, and a ranked shortlist of paid data sources that could resolve the blocker. The lowest-friction credible path identified was Polygon.io, offering historical OHLCV, market cap, shares outstanding, and delisting flags via API with point-in-time accuracy at moderate cost.

## Objective

Evaluate the Polygon.io API as a potential data source for point-in-time fundamental data to resolve the data blocker for the microcap mom121 hypothesis. Determine whether the API (free or paid tiers) provides the required fields with point-in-time accuracy, and assess the effort and cost to integrate it into the research pipeline.

## Acceptance Criteria

### 1. API Access and Documentation

- [ ] Sign up for a free API key from Polygon.io (https://polygon.io) and document the registration process, rate limits, and data limitations of the free tier.
- [ ] If a free tier is not available or insufficient, document the minimum paid tier required to access historical fundamental data (market cap, shares outstanding, delisting events) for US stocks.
- [ ] Review the Polygon.io API documentation to confirm the availability of the following endpoints:
  - Aggregates (OHLCV) for stocks
  - Reference data for tickers (including market cap and shares outstanding)
  - Corporate actions or events data (for delisting events)
  - Note: Polygon.io does not provide a direct "historical market cap" endpoint; market cap must be derived from share price and shares outstanding, or obtained via reference data snapshots.

### 2. Data Fetching and Validation

- [ ] Write a Python script (`research/evaluate_polygon_io.py`) that uses the Polygon.io API to fetch data for a small set of US stocks (e.g., 5 tickers: AAPL, MSFT, FCEL, ACB, SNDL).
- [ ] For each ticker, fetch:
  - Daily OHLCV for the past 6 months (to verify alignment with existing yfinance data).
  - Current reference data (to verify market cap and shares outstanding fields).
  - Historical reference data or corporate actions to assess delisting event coverage.
- [ ] Verify that the data includes timestamps and that historical data is point-in-time (i.e., a request for data as of a past date does not include future information).
- [ ] Document any data gaps, such as missing fields, limited history, or lack of delisting events.

### 3. Point-in-Time Behavior Test

- [ ] Design and run a test to confirm point-in-time accuracy:
  - Select a historical date (e.g., 2023-01-01).
  - Fetch reference data (market cap, shares outstanding) for each ticker as of that date using the API's historical reference data endpoint (if available) or by inferring from available snapshots.
  - Compare the fetched historical values to the actual values known at that date (e.g., from a trusted source or from the API's own time-series if available).
  - Note: If the API does not support historical reference data, document this limitation and assess whether alternative approaches (e.g., using aggregates to infer market cap) can provide point-in-time accuracy.

### 4. Effort and Cost Estimation

- [ ] Estimate the effort required to integrate Polygon.io data into the existing `YFinanceFetcher` or a new data fetcher module (in `src/data/`).
- [ ] Document the estimated cost to scale data collection to a microcap universe of approximately 1,500–2,000 stocks, considering API rate limits and data usage.
- [ ] Provide a cost estimate based on Polygon.io's pricing tiers (https://polygon.io/pricing) for the required data (stock aggregates, reference data, corporate actions).

### 5. Results and Recommendation

- [ ] Save the evaluation results to `research/experiments/mom121_microcap_001_polygon_eval.md` with full disclosure of any limitations (e.g., free tier restrictions, data latency).
- [ ] Update `research/hypotheses/mom121_microcap_001.md` version history (v0.4) with the evaluation findings.
- [ ] Update `research/experiments/mom121_microcap_001.md` with the evaluation results in a new section (e.g., Section B: Paid Data Source Evaluation).
- [ ] State a clear recommendation: whether to pursue Polygon.io as a data source for the microcap mom121 hypothesis, or to consider an alternative paid data source (e.g., Compustat via WRDS, Tiingo, IEX Cloud) based on the evaluation.

### 6. Durable Outputs and Handoff

- [ ] Ensure all artifacts are committed and available for the next cycle.
- [ ] Prepare exactly one next-task handoff in `NEXT_AGENT_TASK.md` based on the evaluation outcome.

## Scope Boundaries

- **No paid data acquisition without authorization:** If the evaluation requires a paid API tier beyond the free tier, do not purchase it without explicit authorization. Instead, document the cost and features of the paid tier based on the public pricing page.
- **Evaluation only:** Do not run a confirmatory backtest for the microcap mom121 hypothesis using Polygon.io data unless the evaluation confirms the API provides the required point-in-time fundamental data and authorization is granted for paid data access.
- **Research/backtesting only:** No live trading or deployment claims.
- **Smallest sufficient change:** Only add code or tests if a concrete improvement to the data pipeline is identified and justified.

## Validation Commands

```bash
# 1. Verify the evaluation script exists and is executable
ls -la research/evaluate_polygon_io.py

# 2. Run the evaluation script (if a free API key is available; otherwise, it should exit gracefully and document the limitation)
python3 research/evaluate_polygon_io.py

# 3. Verify the created artifact exists
ls -la research/experiments/mom121_microcap_001_polygon_eval.md

# 4. Run existing test suite to ensure no regressions
python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v
```

## Completion Standard

Return a concise evidence-backed decision: whether Polygon.io (free or paid tier) provides point-in-time historical market cap, shares outstanding, and delisting events for US stocks; the estimated effort and cost to integrate it; and a clear recommendation on whether to pursue this data source for the microcap mom121 hypothesis.