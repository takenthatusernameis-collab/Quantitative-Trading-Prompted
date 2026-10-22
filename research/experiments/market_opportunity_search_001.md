# Experiment: Evidence-based market-opportunity search (market_opportunity_search_001)

**Cycle 947.** Search, measurement and documentation cycle. **No candidate was executed, pre-registered, promoted or re-ranked.** The Cycle-934 shortlist is exhausted and every remaining candidate line carries a committed verdict, so this cycle searched the *market segments* the committed cache can host and published an explicit rejection reason for each of them.

## Hypothesis reference

No candidate hypothesis is created by this cycle. The conditional candidate `commoditytrend_001` is specified in section 7 of the report but **not** pre-registered: its data gate is not satisfied and its only measurable instantiation fails the pre-declared feasibility screen.

## Data used

- Source: the committed parquet cache under `data/raw/` only. No network call, no fetcher invocation, no download, nothing written under `data/`.
- Inventory: 35 files, all read-only. Daily OHLCV: 27; crypto daily: 4; crypto 8h funding: 4.
- Frequency: every equity/ETF/index/futures series is daily; the only sub-daily series is the 8-hourly crypto funding rate.
- Date ranges, gaps, duplicate timestamps, non-positive closes, zero-volume rows and median dollar volume are tabulated in section 3 of the report and are re-derived by the tool on every run.

## Point-in-time treatment

The one backtest-like computation in this cycle is the pre-declared feasibility screen. Its signal is formed on the month-end session from data up to and including that session (`close.shift(21) / close.shift(252) - 1`), and the target weights are made effective on the **next** session, so no weight uses information that was not available when it was set. The cost is charged on the realised absolute weight change exactly as `src/backtest/engine.py` does it. No parameter is selected by the screen's result and the screen is in-sample and full-sample by construction.

## Configuration

- Cost model: 1.0 bp commission + 2.0 bp slippage = **3.0 bp per unit of weight change**, risk-free 2.00%/yr, read from `src/backtest/engine.py` at run time.
- Frictions absent from that model: borrow, impact, spread, latency, margin.
- Walk-forward design used for the fold counts: 10y train / 12m test / 6m step with a 21-day purge and a 21-day embargo (`src/evaluation/walkforward.py`).
- Minimum folds a panel must support: 15 (4,536 business days).

## Splits

No train/validation/test split was executed. The screen is full-sample and in-sample; the walk-forward fold counts published for each segment are the *counts* the frozen design would produce on that segment's panel, computed with the repository's own `generate_walkforward_splits`.

## Results

### Scored shortlist

| Rank | Segment | (a) | (b) | (c) | (d) | (e) | (f) | (g) | Total | Open for candidacy |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `equity_broad_index` | 5 | 2 | 2 | 3 | 5 | 5 | 3 | **25/35** | closed |
| 2 | `session_timing` | 5 | 4 | 1 | 3 | 5 | 4 | 3 | **25/35** | closed |
| 3 | `real_assets_reit` | 5 | 2 | 1 | 3 | 4 | 5 | 4 | **24/35** | closed |
| 4 | `vol_scaled_overlays` | 5 | 2 | 1 | 3 | 5 | 5 | 3 | **24/35** | closed |
| 5 | `short_leg_relative_value` | 5 | 3 | 2 | 3 | 4 | 2 | 3 | **22/35** | closed |
| 6 | `equity_gics_sectors` | 5 | 1 | 1 | 3 | 4 | 5 | 3 | **22/35** | closed |
| 7 | `equity_volatility` | 5 | 3 | 2 | 3 | 1 | 2 | 5 | **21/35** | blocked |
| 8 | `commodity_complex` | 2 | 4 | 3 | 2 | 2 | 4 | 3 | **20/35** | open |
| 9 | `crypto_funding` | 1 | 3 | 3 | 1 | 5 | 2 | 5 | **20/35** | closed |
| 10 | `rates_duration` | 2 | 2 | 2 | 2 | 4 | 3 | 3 | **18/35** | closed |
| 11 | `single_name_equities` | 1 | 3 | 1 | 1 | 1 | 2 | 3 | **12/35** | blocked |

### The pre-declared feasibility screen

- Screen candidate: `commoditytrend_001`, universe DBC, GLD, rule: absolute time-series momentum: hold every asset whose trailing 252-session total return, skipping the most recent 21 sessions, is positive; equal weight 1/N over the held assets; 100% cash when none is held
- Panel: 2006-02-06 .. 2026-10-08, 5201 sessions, 249 month-end rebalances
- Gross 6.6859%/yr (Sharpe 0.4083); net 6.6176%/yr (Sharpe 0.4041); drag 0.0683%/yr; turnover 2.2773 units/yr
- Benchmark net 7.1480%/yr (Sharpe 0.4580)
- **Benchmark-relative excess: gross -0.4620%/yr, net -0.5304%/yr**
- Sessions with a weight change: 45; rebalances where the held set changed: 58 of 249

## Number of trials

**1** -- one pre-declared screen, one rule, one universe, one benchmark, no grid, no sweep, no parameter search. The screen is a feasibility check and is not a candidate evaluation, so it carries no Deflated Sharpe Ratio and no trial-count accounting; it is published in full so that a reader can judge it.

## Reproduction commands

```bash
python research/market_opportunity_search_001.py
python -m pytest -q tests/test_market_opportunity_search_001.py
git status --porcelain data/ config/
git diff --stat
```

## Decision

**No candidate is pre-registered.** The incumbent `tsmomentum_spytrend_001` stays a Credible Candidate / NO-GO for promotion; every closed line keeps its committed status; no gate, threshold, cost model, universe or committed record was changed. The one segment the scoring leaves open, the commodity complex, is published with its measured data gate and the negative result of its only evaluable instantiation.
