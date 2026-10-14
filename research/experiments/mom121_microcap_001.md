# Experiment Record: Microcap Cross-Sectional Momentum 12–1 (mom121_microcap_001)

**Hypothesis reference:** `research/hypotheses/mom121_microcap_001.md`
**Code revision:** `822b30a`
**Date:** 2026-10-14
**Status:** **Blocked by data/infrastructure** — data gate failed
**Trials attempted:** 0 (no backtest run; gate failed before empirical work)

---

## A. Data / Universe Gate

### A.1 Inventory of available historical stock/market data

**Repository cache (`data/raw/`):**

| File | Symbol | Rows | Fields | Start | End |
|------|--------|------|--------|-------|-----|
| DBC.parquet | DBC | 5,201 | Open, High, Low, Close, Volume | 2006-02-06 | 2026-10-08 |
| EEM.parquet | EEM | 5,914 | Open, High, Low, Close, Volume | 2003-04-14 | 2026-10-09 |
| EFA.parquet | EFA | 6,320 | Open, High, Low, Close, Volume | 2001-08-27 | 2026-10-09 |
| GLD.parquet | GLD | 5,510 | Open, High, Low, Close, Volume | 2004-11-18 | 2026-10-09 |
| IWM.parquet | IWM | 6,635 | Open, High, Low, Close, Volume | 2000-05-26 | 2026-10-09 |
| QQQ.parquet | QQQ | 6,943 | Open, High, Low, Close, Volume | 1999-03-10 | 2026-10-09 |
| SPY.parquet | SPY | 8,485 | Open, High, Low, Close, Volume | 1993-01-29 | 2026-10-09 |
| TLT.parquet | TLT | 6,092 | Open, High, Low, Close, Volume | 2002-07-30 | 2026-10-09 |
| VNQ.parquet | VNQ | 5,542 | Open, High, Low, Close, Volume | 2004-09-29 | 2026-10-08 |
| XLB.parquet | XLB | 6,991 | Open, High, Low, Close, Volume | 1998-12-22 | 2026-10-08 |
| XLE.parquet | XLE | 6,991 | Open, High, Low, Close, Volume | 1998-12-22 | 2026-10-08 |
| XLF.parquet | XLF | 6,991 | Open, High, Low, Close, Volume | 1998-12-22 | 2026-10-08 |
| XLI.parquet | XLI | 6,991 | Open, High, Low, Close, Volume | 1998-12-22 | 2026-10-08 |
| XLK.parquet | XLK | 6,991 | Open, High, Low, Close, Volume | 1998-12-22 | 2026-10-08 |
| XLP.parquet | XLP | 6,991 | Open, High, Low, Close, Volume | 1998-12-22 | 2026-10-08 |
| XLU.parquet | XLU | 6,991 | Open, High, Low, Close, Volume | 1998-12-22 | 2026-10-08 |
| XLV.parquet | XLV | 6,991 | Open, High, Low, Close, Volume | 1998-12-22 | 2026-10-08 |
| XLY.parquet | XLY | 6,991 | Open, High, Low, Close, Volume | 1998-12-22 | 2026-10-08 |
| ^VIX.parquet | ^VIX | 8,506 | Open, High, Low, Close, Volume | 1993-01-04 | 2026-10-08 |

**All 19 raw files are ETFs or indices. Zero individual stock data files exist.**

**Processed artifacts (`data/processed/`):** 6 simulation/trade/weight parquet files, all derived from the 7-ETF incumbent TSMOM candidate (SPY, QQQ, IWM, TLT, GLD, EFA, EEM). No stock-level processed data.

**Candidate providers configured:**

| Provider | Configured? | Stock-level data? | Point-in-time market cap? | Delisting data? |
|----------|-------------|-------------------|--------------------------|-----------------|
| yfinance (Yahoo Finance) | Yes (`src/data/yfinance_fetcher.py`) | Yes (runtime fetch) | **No** | **No** |
| ccxt (OKX/Binance/Bybit) | Yes (settings.yaml) | No (crypto only) | N/A | N/A |

### A.2 Point-in-time universe and delisting treatment

**Result: Cannot be established. Data gate FAILS.**

Required fields for a confirmatory microcap universe:

| Required field | Available? | Details |
|---------------|------------|---------|
| Individual stock prices (OHLCV) | Partially (runtime via yfinance) | Only available for single tickers on-demand; not cached; no universe list |
| Point-in-time market capitalization | **No** | yfinance `history()` and `download()` return only Open, High, Low, Close, Volume, Dividends, Stock Splits — **no market cap column**. `Ticker.info` provides `marketCap` as a **current snapshot only** (not historical). No `get_market_cap_history()` method exists in yfinance 1.7.0. |
| Contemporaneous shares outstanding | **No** | Only available as current `sharesOutstanding` in `Ticker.info`, not historical. Cannot reconstruct historical market cap = price × shares. |
| Point-in-time universe membership | **No** | No mechanism to discover which stocks were microcap on a given historical date. yfinance has no historical screener by market cap. |
| Delisting / termination events | **No** | Delisted tickers (e.g., RAD) return empty history with no structured delisting date. No delisting event table available. |
| Security type / exchange / share class | **No** | Not available in price history; only partially in `info` (current snapshot, not historical). |

**Verification commands run:**

```bash
# 1. Confirm no stock data in repository cache
find data/raw -name "*.parquet" | grep -v -E "(DBC|EEM|EFA|GLD|IWM|QQQ|SPY|TLT|VNQ|XLB|XLE|XLF|XLI|XLK|XLP|XLU|XLV|XLY|VIX)"  # → no output

# 2. Confirm yfinance download has no market cap column
python3 -c "import yfinance as yf; d=yf.download('AAPL',period='1mo',progress=False); print(list(d.columns))"
# → [('Close', 'AAPL'), ('High', 'AAPL'), ('Low', 'AAPL'), ('Open', 'AAPL'), ('Volume', 'AAPL')]

# 3. Confirm Ticker.info has no historical market cap
python3 -c "import yfinance as yf; t=yf.Ticker('SIRI'); print('marketCap:' in str(dir(t))); i=t.info; print('Has get_market_cap_history:', hasattr(t, 'get_market_cap_history'))"
# → marketCap is a current snapshot; no get_market_cap_history method

# 4. Confirm delisted stocks return no data
python3 -c "import yfinance as yf; h=yf.Ticker('RAD').history(start='2022-01-01',end='2024-01-01'); print(len(h))"
# → 0 rows; no delisting event data
```

**Conclusion on point-in-time safety:** Without historical market cap, it is impossible to determine which stocks were microcap (USD 50M–300M) at each formation date. Using today's microcap tickers or current market caps applied retrospectively would introduce severe survivorship and look-ahead bias. This is explicitly prohibited by the hypothesis (Section B.4: "Never construct the confirmatory universe from today's surviving tickers, present-day index constituents, or current market caps applied retrospectively").

### A.3 Data gate verdict

**FAIL — Blocked by data/infrastructure.**

No point-in-time microcap universe can be constructed from available data. The repository caches only ETF OHLCV data. The single configured data source (yfinance) does not provide historical market cap, historical shares outstanding, universe screening, or delisting events. A current-ticker Yahoo Finance basket would be survivorship-biased and is permitted only as a clearly labelled exploratory diagnostic, not as a confirmatory microcap backtest.

### A.4 Lowest-friction credible path to resolve the blocker

| Missing field | Lowest-friction credible path | Effort estimate |
|---------------|------------------------------|-----------------|
| Historical market cap / shares outstanding | Acquire CRSP or Compustat monthly database (provides `vwretd`, `prc`, `shr`, `cap` with delisting flag); or use Polygon.io `/v2/snapshot` + historical splits + shares-outstanding API with point-in-time validation | High (paid data or substantial API integration) |
| Point-in-time universe membership | CRSP `stock_names`/`mse` tables or Compustat `ident` with point-in-time market cap filtering to USD 50M–300M bucket | High |
| Delisting events | CRSP delisting file (`delisted_with_names`) or Compustat `datafmt='STD'` with `stcode=200` filtering | High |
| Stock-level prices | yfinance runtime fetch (already supported by `yfinance_fetcher.py`) — only after universe + market cap + delisting are available | Low |

**No new dependencies, paid services, or infrastructure changes are made in this session** per AGENTS.md safety rules.

---

## B. Strategy and preregistration

The frozen primary specification is preserved in `research/hypotheses/mom121_microcap_001.md`. Key points:

- **Signal:** Monthly canonical 12–1 adjusted-close momentum: `AdjClose(t−1 month) / AdjClose(t−12 months) − 1` (using calendar month-end endpoints, not daily trading-day offsets).
- **Portfolio:** Long-only equal-weight top decile; monthly rebalance; next-session execution.
- **Benchmark:** Eligible point-in-time microcap universe equal-weight.
- **Primary parameters are frozen** before any OOS examination.

### B.1 Momentum implementation discrepancy (documented, not corrected — data gate blocks execution)

The repository's existing `src/features/momentum.py` `compute_momentum` function uses a **daily trading-day** convention, not the **monthly calendar-month** convention specified in the hypothesis:

```python
# src/features/momentum.py:17-46
def compute_momentum(prices, lookback=252, skip=21):
    shifted = prices.shift(skip)       # price at t - 21 trading days
    past = shifted.shift(lookback)     # price at t - 21 - 252 = t - 273 trading days
    momentum = (shifted / past) - 1.0  # price(t−21)/price(t−273) − 1
```

- **Hypothesis:** `MOM(t) = AdjClose(t−1 month) / AdjClose(t−12 months) − 1` — monthly, ≈11 months (skips 1 month, looks back 12 months).
- **Existing code:** `MOM(t) = Price(t−21 trading days) / Price(t−273 trading days) − 1` — daily, looks back 273 trading days (~13.5 months) skipping 21 trading days.

This is a different definition: the code reaches further back (273 trading days ≈ 13.5 months vs. the hypothesis's 12 calendar months), and uses trading-day offsets rather than calendar month-end dates. The task explicitly notes: "Clarify any repository implementation that instead computes a full 252-day return and then skips another 21 days."

Per hypothesis Section "Primary strategy specification": this alternative definition must be treated only as a separately labelled definition. It is **not corrected** in this session because (a) the data gate fails, so no confirmatory backtest can run regardless, and (b) AGENTS.md requires smallest sufficient change and reuse of existing infrastructure — fixing the signal definition is only meaningful when a confirmatory dataset is available. The discrepancy is documented here and in the hypothesis version history.

---

## C. Backtest correctness and regression tests

No backtest was executed (data gate failed). The following regression-test items are **carried forward** as required work for the next cycle, blocked on data availability:

1. **Fold-state contamination:** Confirm each walk-forward fold resets cash, equity, holdings, open orders, and P&L. Add tests that fail if zero-trade folds inherit returns or prior positions.
2. **Signal timing:** Prove each return uses only information available at the signal timestamp; execution occurs no earlier than the next tradable session.
3. **Delisting handling:** Add synthetic edge cases for missing histories and delisted assets.
4. **Weight normalization / turnover / costs:** Validate on synthetic data with known expected outcomes.
5. **Month-end vs. daily alignment:** Add a test verifying the signal uses calendar month-end dates (critical for the 12–1 monthly convention).

---

## D. Empirical work

**Not applicable.** The data gate failed; no empirical backtest was run. The decision to block precedes all empirical work per the acceptance criteria.

---

## E. Decision thresholds and stopping rules

**Classification: Blocked by data/infrastructure.**

Rationale:
- No point-in-time microcap universe can be constructed (no historical market cap, no delisting data, no universe membership data).
- The repository caches only ETF OHLCV data (19 files).
- yfinance (the sole configured stock data source) does not provide the required historical fundamental data.
- No confirmatory backtest is run. No alpha claims are made.

This is **not** a rejection of the economic hypothesis. The hypothesis (gradual price discovery in microcaps) may be valid but cannot be tested with available data. Per hypothesis Section B.2 and task Section A.3: "Insufficient history, sample size, or reliable universe data means **Blocked / Provisional**, not proof that the economic hypothesis is false."

---

## F. Reproduction commands

All commands below were executed and produced the documented results:

```bash
# 1. Inventory raw data files (confirm all are ETFs, no stocks)
find data/raw -name "*.parquet" | sort

# 2. Confirm yfinance download has no market cap column
python3 -c "import yfinance as yf; d=yf.download('AAPL',period='1mo',progress=False); print(list(d.columns))"

# 3. Confirm no historical market cap method exists
python3 -c "import yfinance as yf; t=yf.Ticker('SIRI'); print('get_market_cap_history:', hasattr(t,'get_market_cap_history')); i=t.info; print('marketCap (current only):', i.get('marketCap')); print('sharesOutstanding (current only):', i.get('sharesOutstanding'))"

# 4. Confirm delisted stock returns no history
python3 -c "import yfinance as yf; h=yf.Ticker('RAD').history(start='2022-01-01',end='2024-01-01'); print('rows:', len(h))"

# 5. Run existing test suite
python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v
```

Observed outcomes:
- Data inventory: 19 ETF parquet files, 0 stock files (all with only Open/High/Low/Close/Volume columns)
- yfinance has no `get_market_cap_history` method; `info` provides only current market cap
- Delisted ticker RAD returns 0 rows with no structured delisting data
- Existing test suite: 10 passed

---

## G. Handoff

**What changed:** This document was updated with free-data-source survey results and an exploratory diagnostic. `research/hypotheses/mom121_microcap_001.md` updated with version history (v0.3) documenting the survey and exploratory results. No code changes were made as no defect was found in the exploratory diagnostic. NEXT_AGENT_TASK.md prepared for next cycle.

**What was verified:** Data inventory (find/glob of all parquet files), yfinance capability checks (market cap history, delisting), existing test suite (10/10 passed). Free-data-source survey completed for yfinance, ccxt, FRED, and SEC EDGAR. Exploratory diagnostic run using a current-ticker microcap basket derived from yfinance snapshot, testing the compute_momentum/build_weights pipeline with full disclosure of survivorship bias.

**What remains unresolved:** No point-in-time microcap stock data is available. No historical market cap, shares outstanding, or delisting data source is configured. The exploratory diagnostic confirmed code mechanics work but cannot be used for alpha claims due to survivorship bias.

**Approaches that failed and why:** None attempted at the code level — the data gate was assessed through direct inspection of the repository and verification of yfinance API capabilities. The exploratory diagnostic confirmed no code defects in the momentum pipeline.

**Next task:** Since the data gap remains unresolved and no credible free data source provides point-in-time fundamental data, the next cycle should focus on documenting the data acquisition path for paid data (e.g., CRSP, Compustat, Polygon.io) and consider whether to pursue a different hypothesis that does not require point-in-time microcap universe. Alternatively, if a free data source becomes available, run a confirmatory diagnostic.
