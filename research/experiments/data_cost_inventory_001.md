# Experiment: Data and cost inventory (data_cost_inventory_001, Cycle 912)

## Hypothesis reference

None — this is a **measurement** cycle, not a strategy hypothesis. It executes the first step of AGENTS.md's Market Opportunity Search: *"Inventory real data and costs actually available in the repository first"*, followed by a scored shortlist against criteria (a)–(g).

## Objective

Produce a bounded, evidence-based inventory of the real data and the real cost model available in this repository, score the plausible candidate segments against AGENTS.md's (a)–(g), and state the rejection reason for every segment the data does not support. No backtest is executed, no candidate is promoted, no gate is changed.

## Data used

* Source: the committed cache `data/raw/` — 35 parquet files, 180155 rows (27 equity/futures files from the Yahoo Finance cache, 8 crypto files from the Binance public archive and the OKX funding cross-check). The fetcher is never called; nothing is downloaded.
* Point-in-time treatment: the Yahoo Finance cache carries session-dated UTC bars and is consumed with a 1-session signal lag; the Binance funding series carries settlement timestamps (a same-day funding rule is a look-ahead — the committed rule decides on the previous day's funding); the OKX series is a cross-check only.
* Provenance verification: the committed digests in `research/reports/binance_crypto_manifest.json` were re-verified against the cached bytes — **8/8 match**.
* Frequency: every file's frequency is derived from its own median inter-observation spacing; measured sub-daily files in the cache: **4**.
* Universe: the whole repository (`data/raw/`, `data/processed/`, `config/`, `src/`, `research/`), read-only.

## Configuration

* Cost model read from the repository: commission **1.0 bps**, slippage **2.0 bps** (round trip **3.0 bps** per unit of weight change), risk-free rate **2.00%** annual — the first three from `src/backtest/engine.py:get_cost_params()`/`get_risk_free_rate()`, the risk-free rate likewise from `get_risk_free_rate()`.
* Cost-key scan: every leaf key of every file in `config/` was matched against the components (commission, slippage, round trip, funding, risk-free, spread, borrow, roll, market impact, latency, margin). The **absent** components are reported as measured gaps, not as assumptions.
* Scoring: criterion (a) is measured from the cache by the documented rubric; criteria (b)–(g) are carried from `research/reports/opportunity_shortlist.md` and changed only with a cited committed record.
* The shortlist, the carried scores and the citation for every change are listed in `research/reports/data_cost_inventory_001.md` sections 5.2–5.4.

## Results

| Item | Value |
|---|---|
| Raw files inventoried | 35 |
| Raw rows inventoried | 180155 |
| Missing prices (whole cache) | 0 |
| Duplicate timestamps (whole cache) | 0 |
| Repeat (unchanged) prices (whole cache) | 5329 |
| Sub-daily files (whole cache) | 4 |
| Cost components with no configuration key | 5 of 11 |
| Candidates scored | 10 |
| Segments explicitly rejected or blocked | 8 |

| Measured rank | Candidate | (a) | (b) | (c) | (d) | (e) | (f) | (g) | Total | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | TSMOM incumbent | 5 | 4 | 4 | 3 | 5 | 5 | 5 | **31/35** | Credible candidate -- published PASS survives the non-overlapping fold design (Cycle 910) but is NOT phase-stable (Cycle 911) |
| 2 | Long-only cross-sectional momentum, broad 18-ETF universe | 4 | 5 | 2 | 2 | 5 | 4 | 4 | **26/35** | Rejected/Failed -- gate 1 fails on every pre-registered sample and under the non-overlapping fold design |
| 3 | Sector rotation | 4 | 4 | 2 | 2 | 5 | 4 | 4 | **25/35** | Rejected -- the candidate's own pre-registered falsification condition is met |
| 4 | Calendar / rebalancing effects | 5 | 3 | 2 | 2 | 5 | 4 | 4 | **25/35** | Rejected -- gate 1 fails (walk-forward mean OOS Sharpe -0.0254); cost-admissible but with no edge |
| 5 | TSMOM parameter variants | 5 | 4 | 2 | 2 | 5 | 5 | 2 | **25/35** | Rejected -- 0 of 100 configurations beat the baseline on identical data; the committed parameters sit on a peak, not a plateau |
| 6 | Macro regime overlay extension | 4 | 4 | 2 | 2 | 3 | 4 | 3 | **22/35** | Rejected -- the pre-registered falsification condition is met |
| 7 | Crypto perpetual funding-rate carry | 3 | 4 | 3 | 3 | 5 | 3 | 1 | **22/35** | Exploratory signal -- the net-of-cost edge is real but thin out of sample and the promotion gate's trade-count criterion fails in all 24 cost-model rows |
| 8 | Commodity/rate futures basis and roll yield | 2 | 4 | 3 | 2 | 3 | 2 | 5 | **21/35** | Rejected -- both routes rejected (contract-leg route unbuildable; ETF route negative carry, research/experiments/futuresbasis_002.md) |
| 9 | Volatility risk premium | 2 | 4 | 2 | 2 | 2 | 2 | 4 | **18/35** | Blocked by data -- no tradeable volatility instrument in the repository |
| 10 | Intraday session / time-of-day effects | 1 | 3 | 2 | 1 | 4 | 2 | 4 | **17/35** | Rejected -- no intraday equity series in the cache (the only sub-daily series are the 8-hourly crypto funding files); the overnight variant is inadmissible on cost (break-even 1.74 bp/unit against the 3 bp/unit charged) |

**Decision of this cycle: none.** No candidate is promoted and none is demoted by the inventory itself; the inventory records what the data supports, the cost model that exists, and the rejection reasons for the segments that the data cannot support.

## Trial count

- 1 deterministic measurement pass over the committed cache, the committed configuration and the committed shortlist table. No parameter search, no robustness grid, no candidate selection, no backtest: the cycle consumes **0** new strategy trials.

## Reproduction

```bash
python research/data_cost_inventory_001.py
python -m pytest -q tests/test_data_cost_inventory_001.py
python -m pytest -q
git status --porcelain data/
git diff --stat src/ config/ research/experiments/ research/reports/
```

## Boundaries

* Read-only: no fetcher or network call for new data; the existing committed cache is the only data source inspected.
* Nothing under `data/` or `config/` is written, and no committed artifact other than the two new files of this cycle is modified.
* No backtest, no promotion, no gate change, no candidate execution.
* Deterministic: no timestamps in the report or in this record.

## Artifacts

| Artifact | Path |
|---|---|
| Tool | `research/data_cost_inventory_001.py` |
| Report | `research/reports/data_cost_inventory_001.md` |
| Experiment record | `research/experiments/data_cost_inventory_001.md` |
| Tests | `tests/test_data_cost_inventory_001.py` |
