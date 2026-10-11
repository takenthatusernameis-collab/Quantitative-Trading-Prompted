# Simulation Verification Report (simulation_verification_001)

## Hypothesis Reference

See `research/hypotheses/tsmomentum_004.md` and
`research/experiments/tsmomentum_regime_filter_wf_001.md` (Cycle 6
validation of the promoted candidate).

**Candidate**: `tsmomentum_spytrend_001` — 226-day TSMOM (lookback=226,
skip=21, top_fraction=0.5) with combined volatility-targeting (10%,
63-day lookback) + drawdown control (15% threshold, 50% reduction) and
SPY 200-day SMA trend filter (0% exposure below SMA). Cost model:
3 bps round-trip (1 bps commission + 2 bps slippage) applied to
absolute weight changes.

**Objective**: verify that the new simulation engine
(`src/simulation/engine.py`) reproduces the validated backtest within
tolerance, and produce the daily position/return series and trade log
required for Cycle 8 paper-trading (prospective) validation.

---

## Data Used

- **Source**: Yahoo Finance via yfinance (cached parquet in `data/raw/`)
- **Date Range**: 1993-01-01 to 2026-10-09 (8482 trading days)
- **Universe**: SPY, QQQ, IWM, TLT, GLD, EFA, EEM
- **Execution convention**: signal computed on T-1 close (1-day lag),
  executed at T close (EOD) — identical to the backtest convention.
  The engine also supports `"Open"` execution for prospective
  next-open studies.
- **Cost Model**: 1.0 bps commission +
  2.0 bps slippage =
  3.0 bps round-trip
- **Point-in-time**: overlay state conventions replicate the validated
  code paths — `slice` mode (Cycle 5 test-period evaluation) and
  `full` mode (Cycle 6 walk-forward fold evaluation).

---

## Methodology

The simulation engine re-implements the candidate as a deterministic,
point-in-time pipeline:

1. **Signal**: `src.features.momentum.build_weights` (226-day TSMOM,
   21-day skip, top-50% equal weight, 1-day lag).
2. **Regime filter**: SPY 200-day SMA exposure gate (0% below SMA),
   computed point-in-time on the full price history.
3. **Risk overlay**: volatility targeting (63-day realized vol,
   10% annualized target, capped at 1.0) and drawdown control
   (15% threshold, 0.5 exposure multiplier), followed by a gross
   leverage cap of 1.0.
4. **Execution**: weights changes executed daily (backtest-exact);
   an explicit month-end calendar (`rebalance_schedule: "M"`) is
   supported for paper-trading studies.
5. **Costs**: absolute weight change x 3 bps round-trip, identical
   to the backtest cost model.

Verification compares the simulation against the **original
Cycle 5/6 code paths** (`research/run_cycle5.py::_eval_candidate`
and `research/run_cycle6.py::_eval_candidate_period`), imported
directly — i.e. two independent implementations of the same
validated logic.

---

## 1. Backtest Replication (Test Period 2018-2026)

Simulation uses `overlay_warmup="slice"` (overlay state initializes
at the simulation start date), exactly matching the Cycle 5
test-period evaluation.

| Metric | Backtest (Cycle 5/6) | Simulation | Diff | Tolerance | Status |
|--------|---------------------|------------|------|-----------|--------|
| Test Sharpe | 1.4178 | 1.4178 | 0.000000 | 0.02 | PASS |
| Max Drawdown | -7.79% | -7.79% | 0.00% | 0.5% | PASS |
| Ann. Return | 14.46% | 14.46% | 0.00% | 0.5% | PASS |
| Trades | 1,196 | 1,196 | 0 | 0 | PASS |

**Documented Cycle 5/6 values for cross-check**: test Sharpe
1.4178, max DD -7.79%,
1,196 trades, annualized return
14.46%.

---

## 2. Walk-Forward Replication

Simulation uses `overlay_warmup="full"` (overlay state initializes
at `history_start`, then sliced to each fold), exactly matching the
Cycle 6 walk-forward fold evaluation. Walk-forward design: 10-year
train, 12-month test, 6-month step, 21-day purge, 21-day embargo;
parameters fixed across folds.

| Fold | Test Start | Test End | Backtest Sharpe | Simulation Sharpe | Diff |
|------|------------|----------|-----------------|-------------------|------|
| 1 | 2002-09-30 | 2003-09-16 | 2.5550 | 2.5550 | 0.000000 |
| 2 | 2003-03-25 | 2004-03-10 | 2.5821 | 2.5821 | 0.000000 |
| 3 | 2003-09-17 | 2004-09-02 | 0.3027 | 0.3027 | 0.000000 |
| 4 | 2004-03-11 | 2005-02-25 | 1.2700 | 1.2700 | 0.000000 |
| 5 | 2004-09-03 | 2005-08-22 | 1.9494 | 1.9494 | 0.000000 |
| 6 | 2005-02-28 | 2006-02-14 | 2.1849 | 2.1849 | 0.000000 |
| 7 | 2005-08-23 | 2006-08-09 | 2.3382 | 2.3382 | 0.000000 |
| 8 | 2006-02-15 | 2007-02-01 | 1.8912 | 1.8912 | 0.000000 |
| 9 | 2006-08-10 | 2007-07-27 | 1.3166 | 1.3166 | 0.000000 |
| 10 | 2007-02-02 | 2008-01-21 | 2.0815 | 2.0815 | 0.000000 |
| 11 | 2007-07-30 | 2008-07-15 | 2.7409 | 2.7409 | 0.000000 |
| 12 | 2008-01-22 | 2009-01-07 | -21.8299 | -21.8299 | 0.000000 |
| 13 | 2008-07-16 | 2009-07-02 | -0.2665 | -0.2665 | 0.000000 |
| 14 | 2009-01-08 | 2009-12-25 | 1.7670 | 1.7670 | 0.000000 |
| 15 | 2009-07-03 | 2010-06-21 | 1.5242 | 1.5242 | 0.000000 |
| 16 | 2009-12-28 | 2010-12-14 | 1.0671 | 1.0671 | 0.000000 |
| 17 | 2010-06-22 | 2011-06-08 | 1.0960 | 1.0960 | 0.000000 |
| 18 | 2010-12-15 | 2011-12-01 | 0.2426 | 0.2426 | 0.000000 |
| 19 | 2011-06-09 | 2012-05-25 | 0.9429 | 0.9429 | 0.000000 |
| 20 | 2011-12-02 | 2012-11-19 | 1.2267 | 1.2267 | 0.000000 |
| 21 | 2012-05-28 | 2013-05-14 | 2.2063 | 2.2063 | 0.000000 |
| 22 | 2012-11-20 | 2013-11-06 | 2.1734 | 2.1734 | 0.000000 |
| 23 | 2013-05-15 | 2014-05-01 | 0.8107 | 0.8107 | 0.000000 |
| 24 | 2013-11-07 | 2014-10-24 | 0.4830 | 0.4830 | 0.000000 |
| 25 | 2014-05-02 | 2015-04-20 | 1.1702 | 1.1702 | 0.000000 |
| 26 | 2014-10-27 | 2015-10-13 | 0.8976 | 0.8976 | 0.000000 |
| 27 | 2015-04-21 | 2016-04-06 | 0.2792 | 0.2792 | 0.000000 |
| 28 | 2015-10-14 | 2016-09-29 | 1.3453 | 1.3453 | 0.000000 |
| 29 | 2016-04-07 | 2017-03-24 | 0.2969 | 0.2969 | 0.000000 |
| 30 | 2016-09-30 | 2017-09-18 | 0.6332 | 0.6332 | 0.000000 |
| 31 | 2017-03-27 | 2018-03-13 | 1.6764 | 1.6764 | 0.000000 |
| 32 | 2017-09-19 | 2018-09-05 | 1.1373 | 1.1373 | 0.000000 |
| 33 | 2018-03-14 | 2019-02-28 | 0.2472 | 0.2472 | 0.000000 |
| 34 | 2018-09-06 | 2019-08-23 | 1.0883 | 1.0883 | 0.000000 |
| 35 | 2019-03-01 | 2020-02-17 | 3.2521 | 3.2521 | 0.000000 |
| 36 | 2019-08-26 | 2020-08-11 | 3.9121 | 3.9121 | 0.000000 |
| 37 | 2020-02-18 | 2021-02-03 | 2.3629 | 2.3629 | 0.000000 |
| 38 | 2020-08-12 | 2021-07-29 | 0.7952 | 0.7952 | 0.000000 |
| 39 | 2021-02-04 | 2022-01-21 | -0.0836 | -0.0836 | 0.000000 |
| 40 | 2021-07-30 | 2022-07-18 | -0.1073 | -0.1073 | 0.000000 |
| 41 | 2022-01-24 | 2023-01-10 | 0.8947 | 0.8947 | 0.000000 |
| 42 | 2022-07-19 | 2023-07-05 | 1.5584 | 1.5584 | 0.000000 |
| 43 | 2023-01-11 | 2023-12-28 | 1.8332 | 1.8332 | 0.000000 |
| 44 | 2023-07-06 | 2024-06-21 | 1.8186 | 1.8186 | 0.000000 |
| 45 | 2023-12-29 | 2024-12-16 | 1.8342 | 1.8342 | 0.000000 |
| 46 | 2024-06-24 | 2025-06-10 | 1.1148 | 1.1148 | 0.000000 |
| 47 | 2024-12-17 | 2025-12-03 | 1.9609 | 1.9609 | 0.000000 |
| 48 | 2025-06-11 | 2026-05-28 | 2.8969 | 2.8969 | 0.000000 |

**Mean OOS Sharpe**: backtest 0.9473,
simulation 0.9473,
diff 0.000000 (tolerance 0.02) —
**PASS**

Documented Cycle 6 walk-forward mean OOS Sharpe for cross-check:
0.9473.

---

## 3. SMA Window Plateau Replication

| SMA Window | Backtest Sharpe | Simulation Sharpe | Diff | Trades (sim) | Sharpe >= 0.9 |
|------------|-----------------|-------------------|------|--------------|---------------|
| 150 | 1.5504 | 1.5504 | 0.000000 | 1170 | YES |
| 175 | 1.4933 | 1.4933 | 0.000000 | 1204 | YES |
| 200 | 1.4178 | 1.4178 | 0.000000 | 1196 | YES |
| 226 | 1.3178 | 1.3178 | 0.000000 | 1233 | YES |
| 250 | 1.2781 | 1.2781 | 0.000000 | 1279 | YES |
| 277 | 1.2270 | 1.2270 | 0.000000 | 1303 | YES |

**Windows with Sharpe >= 0.9**: backtest 6/6,
simulation 6/6; max per-window diff
0.000000 (tolerance 0.02) —
**PASS**

---

## 4. Determinism Check

The OOS simulation was executed twice from the same configuration:

- Daily series identical: True
- Trade log identical: True
- Weights identical: True

**Result**: **PASS** (the engine uses no
random number generator; the `seed` field is reserved for API
compatibility).

---

## 5. Paper-Trading Baseline (OOS 2018-2026)

Key metrics from the verified simulation, for prospective tracking:

| Metric | Value |
|--------|-------|
| Sharpe | 1.4178 |
| Sortino | 1.7477 |
| Annualized return | 14.46% |
| Annualized volatility | 8.79% |
| Max drawdown | -7.79% |
| Total return | 226.12% |
| Trades | 1,196 |
| Annualized turnover | 13.32 |
| Avg exposure | 0.6506 |
| Profit factor | 1.35 |
| Daily VaR (95%) | 0.90% |
| Daily CVaR (95%) | 0.02% |
| Max exposure | 100.00% |
| Current exposure | 64.77% |
| Total transaction costs | 0.034967 (of unit capital) |
| Avg daily cost | 0.00001586 |

---

## Artifacts

| Artifact | Path | Contents |
|----------|------|----------|
| Simulation engine | `src/simulation/engine.py` | `SimulationConfig`, `SimulationResult`, `run_simulation` |
| Frozen config | `config/simulation_candidate_001.yaml` | Candidate parameters (sha256[:12]=3c8f5b899f1f) |
| Daily series | `data/processed/simulation_candidate_001.parquet` | Full-history (1993-2026) daily returns, positions, risk state |
| Trade log | `data/processed/trades_candidate_001.parquet` | Full-history per-trade log (date, symbol, side, weight, price, cost) |

Daily series: 8,482 rows,
1993-01-29 to 2026-10-09.
Trade log: 13,631 trades.
Rebalancing events: 4,345 days with nonzero turnover.

---

## Reproducibility

```bash
python3 research/run_cycle7.py
```

Configuration: `config/simulation_candidate_001.yaml`
(sha256[:12]=3c8f5b899f1f). Code revision: 412f292.

---

## Classification

**PASS — simulation verified**

The simulation engine reproduces the Cycle 5/6 backtest within
tolerance (test-period Sharpe diff 0.000000
< 0.02; max-DD diff 0.00% < 0.5%;
identical trade count; walk-forward mean OOS Sharpe diff
0.000000; plateau 6/6 windows
>= 0.9). The candidate is ready for **Cycle 8: paper-trading
(prospective) validation** — daily simulation runs with current
market data, position/return tracking, drift monitoring, and a
go/no-go decision after a 3-6 month paper track record.

---

*Report generated: 2026-10-11*
*Code revision: 412f292*
*Config hash: 3c8f5b899f1f*
