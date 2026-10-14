# Next Agent Task: Microcap mom121 — Resolve Data Gap for Point-in-Time Microcap Universe

## Context

The previous cycle completed the data/universe gate (Section A of `NEXT_AGENT_TASK.md` v1) and found:

- **Data gate FAILED.** `data/raw/` contains 19 parquet files, all ETFs/indices (DBC, EEM, EFA, GLD, IWM, QQQ, SPY, TLT, VNQ, XLB–XLY, ^VIX) with only OHLCV columns. **Zero individual stock data files exist.**
- **yfinance cannot provide historical market cap.** `yfinance.download()` and `Ticker.history()` return only OHLCV + Dividends + Stock Splits. `Ticker.info` provides `marketCap` as a current snapshot only; no `get_market_cap_history()` method exists. Delisted tickers (e.g., RAD) return 0 rows with no structured delisting event data.
- **Existing hypothesis** (`research/hypotheses/mom121_microcap_001.md` v0.2) and **experiment record** (`research/experiments/mom121_microcap_001.md`) are persisted with status: **Blocked by data/infrastructure**.

The full audit, verification commands, and observed outcomes are documented in `research/experiments/mom121_microcap_001.md` Section A.

## Objective

Resolve the precise data blocker identified by the data gate: the inability to construct a **point-in-time microcap stock universe** (with historical market cap, shares outstanding, and delisting coverage). The objective is to determine the lowest-friction credible path to obtain the required data, and to run a **clearly labelled exploratory diagnostic** that tests the momentum code logic on imperfect data without making any alpha claims.

## Acceptance criteria

### 1. Exhaustive free-data-source survey

Survey all free/public data sources available in the repository's infrastructure (yfinance, ccxt, FRED, SEC EDGAR via `sec-edgar-downloader` if already installed, etc.):

- [ ] Confirm whether any free source can provide **point-in-time** historical market cap for individual US stocks at month-end intervals.
- [ ] Confirm whether any free source provides **delisting/termination** event dates for US stocks.
- [ ] Confirm whether any free source provides **historical shares outstanding** (not just current `info` snapshot).
- [ ] Confirm whether any free source provides a **point-in-time stock universe** (not just current constituents).
- [ ] Document each source's limitations explicitly. If a source provides current-only data (like yfinance `info`), state why this violates point-in-time requirements.

### 2. Exploratory diagnostic (clearly labelled, NOT confirmatory)

If yfinance can fetch historical prices for a current-ticker basket of microcap ETFs or stocks (using today's microcap universe applied retrospectively), run a **clearly labelled exploratory diagnostic** that:

- [ ] Uses the current-ticker yfinance basket ONLY for testing code mechanics, with prominent labels: "EXPLORATORY — NOT CONFIRMATORY — SURVIVORSHIP BIASED — CURRENT TICKERS APPLIED RETROSPECTIVELY"
- [ ] Tests the `compute_momentum` / `build_weights` pipeline from `src/features/momentum.py` on the fetched data
- [ ] Explicitly verifies the daily-vs-monthly 12-1 discrepancy: runs BOTH the existing daily convention (lookback=252, skip=21) AND a monthly calendar-month-end 12-1 convention, and documents the difference
- [ ] Does NOT report any Sharpe, return, or performance metric as evidence of an edge — only as code-verification output
- [ ] Saves results to `research/experiments/mom121_microcap_001_exploratory.md` with full disclosure labels

### 3. Document the data acquisition path

- [ ] Produce a ranked shortlist of data sources that COULD resolve the blocker (e.g., CRSP monthly stock file, Compustat, Polygon.io, etc.) with cost/access estimates.
- [ ] Document the exact data fields required (columns, frequency, point-in-time behavior).
- [ ] State the lowest-friction credible path as a single recommendation, with effort estimate.

### 4. Minimal code change (only if justified by evidence)

- If the exploratory diagnostic reveals a material code defect (e.g., momentum calculation bug, weight normalization issue) that would affect a future confirmatory test, fix the **smallest** defect and add a regression test.
- If no defect is found, make no code changes.

### 5. Durable outputs and handoff

- [ ] Update `research/experiments/mom121_microcap_001.md` with the free-data survey results (Section A supplement) and exploratory diagnostic.
- [ ] Update `research/hypotheses/mom121_microcap_001.md` version history (v0.3) with findings.
- [ ] Update README.md "Current Status" section with the microcap data gate result (factual summary only).
- [ ] Prepare exactly one next-task handoff in `NEXT_AGENT_TASK.md`.

## Scope boundaries

- **Data survey only:** No paid data acquisition, no new paid dependencies, no credential entry. Only inspect free sources already accessible or documented in `config/settings.yaml`.
- **Exploratory diagnostic only:** Do not run a confirmatory backtest. Do not present any metric as evidence of an edge.
- **No live trading, no deployment claims.** Research/backtesting only.
- **Smallest sufficient change:** Only add code/tests if a concrete defect is identified. Do not rebuild the stack.

## Validation commands

```bash
# 1. Verify data inventory (confirm no stock data exists)
find data/raw -name "*.parquet" | sort

# 2. Confirm yfinance has no historical market cap
python3 -c "import yfinance as yf; t=yf.Ticker('AAPL'); print('has_mc_history:', hasattr(t,'get_market_cap_history')); i=t.info; print('info_mc:', type(i.get('marketCap')))"

# 3. Run exploratory diagnostic (to be written by this task)
python3 research/run_mom121_microcap_exploratory.py

# 4. Run existing test suite
python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v

# 5. Verify created artifacts exist
ls -la research/experiments/mom121_microcap_001.md research/experiments/mom121_microcap_001_exploratory.md
```

## Completion standard

Return a concise evidence-backed decision: blocked by data (with exact missing fields and credible path documented), exploratory diagnostic results (code verification only, with full bias disclosures), and whether any code defects were found and fixed.
