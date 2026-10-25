# Data and Cost Inventory 001 — Cycle 912

**Method:** read-only, cache-only inspection of the committed repository. `research/data_cost_inventory_001.py` measures every file under `data/raw/`, the cost parameters actually configured in `config/` and `src/backtest/engine.py`, and the candidate shortlist scored against AGENTS.md's criteria (a)–(g). No backtest was run, no candidate was promoted, no fetcher was called and nothing under `data/` or `config/` was written.

**Determinism:** this document contains no timestamp, no run id and no filesystem-order dependence; two consecutive generations are byte-identical.

## 1. Data inventory — `data/raw/`

**35 parquet files, 180192 rows** (27 equity/futures files, 8 crypto files). Measured across the whole cache: **0 missing prices**, **0 duplicate timestamps**, **4 sub-daily files** (all of them the 8-hourly crypto funding series; **0** equity/futures file is finer than daily), **2133 non-positive price observations**.

| # | Path | Provenance | Universe | Rows | First | Last | Frequency | Median gap (d) | Dup timestamps | Missing prices | Stale (repeat) prices | Non-positive prices | Zero-volume rows | SHA-256 (16) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `data/raw/BNO.parquet` | yfinance-cache | BNO | 4123 | 2010-06-02 | 2026-10-21 | daily | 1.0000 | 0 | 0 | 77 | 0 | 27 | `f9f85c5844ba3884` |
| 2 | `data/raw/CL-F.parquet` | yfinance-cache | CL-F | 2964 | 2015-01-02 | 2026-10-15 | daily | 1.0000 | 0 | 0 | 12 | 1 | 7 | `5d7ec126885110fc` |
| 3 | `data/raw/DBC.parquet` | yfinance-cache | DBC | 5210 | 2006-02-06 | 2026-10-21 | daily | 1.0000 | 0 | 0 | 85 | 0 | 0 | `a04e11a54bb3710f` |
| 4 | `data/raw/EEM.parquet` | yfinance-cache | EEM | 5921 | 2003-04-14 | 2026-10-23 | daily | 1.0000 | 0 | 0 | 40 | 0 | 0 | `82bbe68da28e67e6` |
| 5 | `data/raw/EFA.parquet` | yfinance-cache | EFA | 6327 | 2001-08-27 | 2026-10-23 | daily | 1.0000 | 0 | 0 | 49 | 0 | 0 | `9663723537ee2122` |
| 6 | `data/raw/GC-F.parquet` | yfinance-cache | GC-F | 2964 | 2015-01-02 | 2026-10-15 | daily | 1.0000 | 0 | 0 | 15 | 0 | 36 | `2dc89075a6bfe3a9` |
| 7 | `data/raw/GLD.parquet` | yfinance-cache | GLD | 5517 | 2004-11-18 | 2026-10-23 | daily | 1.0000 | 0 | 0 | 20 | 0 | 0 | `a0f88f7f8c15fecc` |
| 8 | `data/raw/GSG.parquet` | yfinance-cache | GSG | 2964 | 2015-01-02 | 2026-10-15 | daily | 1.0000 | 0 | 0 | 59 | 0 | 0 | `d38c0d9bed4894da` |
| 9 | `data/raw/IWM.parquet` | yfinance-cache | IWM | 6642 | 2000-05-26 | 2026-10-23 | daily | 1.0000 | 0 | 0 | 20 | 0 | 0 | `3c0e1a712f512ad2` |
| 10 | `data/raw/NG-F.parquet` | yfinance-cache | NG-F | 2965 | 2015-01-02 | 2026-10-15 | daily | 1.0000 | 0 | 0 | 11 | 0 | 7 | `6d480ef7769f42eb` |
| 11 | `data/raw/QQQ.parquet` | yfinance-cache | QQQ | 6950 | 1999-03-10 | 2026-10-23 | daily | 1.0000 | 0 | 0 | 38 | 0 | 0 | `9533c5c922c4787e` |
| 12 | `data/raw/SPY.parquet` | yfinance-cache | SPY | 8492 | 1993-01-29 | 2026-10-23 | daily | 1.0000 | 0 | 0 | 62 | 0 | 0 | `23a0fb14324c3220` |
| 13 | `data/raw/TLT.parquet` | yfinance-cache | TLT | 6099 | 2002-07-30 | 2026-10-23 | daily | 1.0000 | 0 | 0 | 31 | 0 | 0 | `54070c10163d86b0` |
| 14 | `data/raw/UNG.parquet` | yfinance-cache | UNG | 4910 | 2007-04-18 | 2026-10-21 | daily | 1.0000 | 0 | 0 | 63 | 0 | 0 | `0ce2a5b25a2e8e6b` |
| 15 | `data/raw/USO.parquet` | yfinance-cache | USO | 2964 | 2015-01-02 | 2026-10-15 | daily | 1.0000 | 0 | 0 | 23 | 0 | 0 | `fa22094f98b4e826` |
| 16 | `data/raw/VNQ.parquet` | yfinance-cache | VNQ | 5542 | 2004-09-29 | 2026-10-08 | daily | 1.0000 | 0 | 0 | 30 | 0 | 0 | `8714f6b1bf45d1b0` |
| 17 | `data/raw/XLB.parquet` | yfinance-cache | XLB | 6991 | 1998-12-22 | 2026-10-08 | daily | 1.0000 | 0 | 0 | 78 | 0 | 0 | `465b9a7b6c784869` |
| 18 | `data/raw/XLE.parquet` | yfinance-cache | XLE | 6991 | 1998-12-22 | 2026-10-08 | daily | 1.0000 | 0 | 0 | 50 | 0 | 0 | `408b2806f7dbde65` |
| 19 | `data/raw/XLF.parquet` | yfinance-cache | XLF | 6991 | 1998-12-22 | 2026-10-08 | daily | 1.0000 | 0 | 0 | 100 | 0 | 0 | `2f8eeb83b2024b69` |
| 20 | `data/raw/XLI.parquet` | yfinance-cache | XLI | 6991 | 1998-12-22 | 2026-10-08 | daily | 1.0000 | 0 | 0 | 70 | 0 | 1 | `176eaa15a62526ec` |
| 21 | `data/raw/XLK.parquet` | yfinance-cache | XLK | 6991 | 1998-12-22 | 2026-10-08 | daily | 1.0000 | 0 | 0 | 78 | 0 | 0 | `b66776c5c1c70885` |
| 22 | `data/raw/XLP.parquet` | yfinance-cache | XLP | 6991 | 1998-12-22 | 2026-10-08 | daily | 1.0000 | 0 | 0 | 130 | 0 | 0 | `d1ac5528a51c5470` |
| 23 | `data/raw/XLU.parquet` | yfinance-cache | XLU | 6991 | 1998-12-22 | 2026-10-08 | daily | 1.0000 | 0 | 0 | 88 | 0 | 0 | `c9550ef0e461368e` |
| 24 | `data/raw/XLV.parquet` | yfinance-cache | XLV | 6991 | 1998-12-22 | 2026-10-08 | daily | 1.0000 | 0 | 0 | 91 | 0 | 0 | `bcf7029ba61bac58` |
| 25 | `data/raw/XLY.parquet` | yfinance-cache | XLY | 6991 | 1998-12-22 | 2026-10-08 | daily | 1.0000 | 0 | 0 | 65 | 0 | 0 | `7a64cd50a03d5d70` |
| 26 | `data/raw/ZB-F.parquet` | yfinance-cache | ZB-F | 2964 | 2015-01-02 | 2026-10-15 | daily | 1.0000 | 0 | 0 | 37 | 0 | 9 | `26f740c341408310` |
| 27 | `data/raw/^VIX.parquet` | yfinance-cache | ^VIX | 8513 | 1993-01-04 | 2026-10-23 | daily | 1.0000 | 0 | 0 | 47 | 0 | 8513 | `0f37ea8e1e40197b` |
| 28 | `data/raw/crypto/BTCUSDT_perp_1d_binance.parquet` | binance-archive | crypto/BTCUSDT_perp_1d_binance | 2465 | 2020-01-01 | 2026-09-30 | daily | 1.0000 | 0 | 0 | 0 | 0 | 0 | `b512246ba875b0d6` |
| 29 | `data/raw/crypto/BTCUSDT_spot_1d_binance.parquet` | binance-archive | crypto/BTCUSDT_spot_1d_binance | 2465 | 2020-01-01 | 2026-09-30 | daily | 1.0000 | 0 | 0 | 0 | 0 | 0 | `0fd946222a284885` |
| 30 | `data/raw/crypto/BTC_USDT_USDT_funding.parquet` | okx-api | crypto/BTC_USDT_USDT_funding | 296 | 2026-07-13 | 2026-10-20 | 8-hourly | 0.3333 | 0 | 0 | 19 | 29 | - | `1c5ded033f01acc7` |
| 31 | `data/raw/crypto/BTC_USDT_USDT_funding_binance.parquet` | binance-archive | crypto/BTC_USDT_USDT_funding_binance | 7395 | 2020-01-01 | 2026-09-30 | 8-hourly | 0.3333 | 0 | 0 | 1902 | 1036 | - | `4d3b4d653eaf2b09` |
| 32 | `data/raw/crypto/ETHUSDT_perp_1d_binance.parquet` | binance-archive | crypto/ETHUSDT_perp_1d_binance | 2465 | 2020-01-01 | 2026-09-30 | daily | 1.0000 | 0 | 0 | 1 | 0 | 0 | `5f3ea46cac53e52c` |
| 33 | `data/raw/crypto/ETHUSDT_spot_1d_binance.parquet` | binance-archive | crypto/ETHUSDT_spot_1d_binance | 2465 | 2020-01-01 | 2026-09-30 | daily | 1.0000 | 0 | 0 | 0 | 0 | 0 | `fee74e1349095aca` |
| 34 | `data/raw/crypto/ETH_USDT_USDT_funding.parquet` | okx-api | crypto/ETH_USDT_USDT_funding | 296 | 2026-07-13 | 2026-10-20 | 8-hourly | 0.3333 | 0 | 0 | 14 | 48 | - | `9b86f26b4febd486` |
| 35 | `data/raw/crypto/ETH_USDT_USDT_funding_binance.parquet` | binance-archive | crypto/ETH_USDT_USDT_funding_binance | 7395 | 2020-01-01 | 2026-09-30 | 8-hourly | 0.3333 | 0 | 0 | 1924 | 1019 | - | `50c57313802809e3` |

*"Stale (repeat) prices" counts the observations whose price equals the previous observation exactly (a carried-forward or genuinely unchanged print); "Non-positive prices" counts observations with a price at or below zero; "Zero-volume rows" counts observations with a zero volume print.*

### 1.1 Provenance and independent verification

**yfinance-cache** (27 files) — Yahoo Finance via `yfinance` (`src/data/yfinance_fetcher.py`), cached as daily parquet; re-fetchable, no per-file digest committed with the repository.

**binance-archive** (6 files) — Binance public data archive (`data.binance.vision`); every archive object was SHA-256-verified against the published `.CHECKSUM` and every cached file is pinned by a committed digest in `research/reports/binance_crypto_manifest.json`.

**okx-api** (2 files) — OKX public swap-funding API (Cycle 888 collection); re-fetchable, no committed per-file digest.

The committed crypto manifest (`research/reports/binance_crypto_manifest.json`, source: Binance public data archive (data.binance.vision), endpoint: https://data.binance.vision) pins **8/8** cached crypto artefacts by SHA-256; the digests were re-verified against the cached bytes for this report and all of them match.

| Dataset | Committed path | Digest status |
|---|---|---|
| `carry_path_BTCUSDT` | `data/processed/crypto/BTCUSDT_carry_path.parquet` | **MATCH** |
| `carry_path_ETHUSDT` | `data/processed/crypto/ETHUSDT_carry_path.parquet` | **MATCH** |
| `funding_BTCUSDT` | `data/raw/crypto/BTC_USDT_USDT_funding_binance.parquet` | **MATCH** |
| `funding_ETHUSDT` | `data/raw/crypto/ETH_USDT_USDT_funding_binance.parquet` | **MATCH** |
| `perp_BTCUSDT` | `data/raw/crypto/BTCUSDT_perp_1d_binance.parquet` | **MATCH** |
| `perp_ETHUSDT` | `data/raw/crypto/ETHUSDT_perp_1d_binance.parquet` | **MATCH** |
| `spot_BTCUSDT` | `data/raw/crypto/BTCUSDT_spot_1d_binance.parquet` | **MATCH** |
| `spot_ETHUSDT` | `data/raw/crypto/ETHUSDT_spot_1d_binance.parquet` | **MATCH** |

### 1.2 Point-in-time treatment

| Provenance | Timestamp semantics | Look-ahead exposure | Execution treatment |
|---|---|---|---|
| yfinance-cache | Daily bar stamped at the session date, UTC-normalised by `src/data/yfinance_fetcher.py`; the index carries the session date, not the publish time | The fetcher downloads only up to the requested end date; every price used by a signal is shifted one session (signals are formed on T-1 and executed on T) | Close-to-close with a 1-session signal lag (`signal_lag_days: 1`); the fetcher forward-fills each symbol's own last close onto the union calendar, so a symbol missing a session carries a stale close |
| binance-archive | Funding rows carry the settlement timestamp; the daily klines carry the UTC day | Funding settled at 00:00/08:00/16:00 UTC is only known **after** its timestamp, so a same-day funding rule is a look-ahead; the repository's committed implementable rule decides on the **previous** day's funding | The carry path is a spot-long / perp-short pair; both legs are traded, so the entry and the exit are both charged |
| okx-api | 8h funding settlement timestamps, UTC | Same rule as above | Cross-check only (296 rows per symbol, 98 days); it is not the evidence base of any scored candidate |

## 2. Data integrity — coverage, gaps and stale prices

**Coverage tiers** (the cache is not updated uniformly; a candidate whose universe spans two tiers inherits the shorter one):

| Last observation | Files | Names |
|---|---|---|
| 2026-09-30 | 6 | crypto/BTCUSDT_perp_1d_binance, crypto/BTCUSDT_spot_1d_binance, crypto/BTC_USDT_USDT_funding_binance, crypto/ETHUSDT_perp_1d_binance, crypto/ETHUSDT_spot_1d_binance, crypto/ETH_USDT_USDT_funding_binance |
| 2026-10-08 | 10 | VNQ, XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY |
| 2026-10-15 | 6 | CL-F, GC-F, GSG, NG-F, USO, ZB-F |
| 2026-10-20 | 2 | crypto/BTC_USDT_USDT_funding, crypto/ETH_USDT_USDT_funding |
| 2026-10-21 | 3 | BNO, DBC, UNG |
| 2026-10-23 | 8 | EEM, EFA, GLD, IWM, QQQ, SPY, TLT, ^VIX |

Measured equity-session lag behind the newest equity bar (2026-10-23): 2026-10-08 → 11 sessions; 2026-10-15 → 6 sessions; 2026-10-21 → 2 sessions; 2026-10-23 → 0 sessions.

**Zero-volume observations** (a non-trading or non-tradable print): `BNO.parquet` 27 of 4123 rows; `CL-F.parquet` 7 of 2964 rows; `GC-F.parquet` 36 of 2964 rows; `NG-F.parquet` 7 of 2965 rows; `XLI.parquet` 1 of 6991 rows; `ZB-F.parquet` 9 of 2964 rows; `^VIX.parquet` 8513 of 8513 rows.

**Repeat (unchanged) prices** — the largest counts are `crypto/ETH_USDT_USDT_funding_binance.parquet` 1924/7395 (26.02%); `crypto/BTC_USDT_USDT_funding_binance.parquet` 1902/7395 (25.72%); `XLP.parquet` 130/6991 (1.86%); `XLF.parquet` 100/6991 (1.43%); `XLV.parquet` 91/6991 (1.30%); `XLU.parquet` 88/6991 (1.26%); `DBC.parquet` 85/5210 (1.63%); `XLB.parquet` 78/6991 (1.12%).

**Survivorship.** Every cached instrument is a still-listed ETF, a still-traded futures front month or a live crypto contract; the repository holds no delisted series and no constituent-level membership, so ETF-level survivorship is not observable and constituent-level survivorship is **not modelled** (a limitation, inherited, not measured away).

**Observed price anomalies** (non-positive *prices*, i.e. not funding prints): `CL-F.parquet` 2020-04-20 (-37.63). These are real market prints, not cache errors (the front-month WTI series carries the negative settlement of 2020-04-20), and they are a reminder that a continuous front-month series contains roll discontinuities that a spot series does not. Negative **funding** rates (1036 of 7395 observations in `crypto/BTC_USDT_USDT_funding_binance.parquet`, 14.0%) are ordinary and are not anomalies.

## 3. Processed artefacts in the repository

| Group | Files | Parquet files | Rows | First | Last |
|---|---|---|---|---|---|
| `data/processed/(top level)` | 19 | 16 | 101640 | 1993-01-29 | 2026-10-09 |
| `data/processed/crypto` | 2 | 2 | 4928 | 2020-01-02 | 2026-09-30 |
| `data/processed/paper_trading` | 1816 | 1816 | 4540 | 2025-01-02 | 2026-10-23 |

The processed tree is a research output, not an independent data source: it is derived from `data/raw/` plus the committed code. It is inventoried here for completeness and is not used as a scored candidate's evidence base.

## 4. The cost model actually available

All figures below are read from the repository, never assumed: the first three come from `src/backtest/engine.py:get_cost_params()` and `get_risk_free_rate()` (which read `config/settings.yaml`), the remainder from the configuration scan below.

| Component | Value | Source |
|---|---|---|
| Commission | 1.0 bps per trade | `src/backtest/engine.py:get_cost_params()` → `config/settings.yaml:backtest.default_commission_bps` = 1.0 |
| Slippage | 2.0 bps per trade | `src/backtest/engine.py:get_cost_params()` → `config/settings.yaml:backtest.default_slippage_bps` = 2.0 |
| Round trip (one unit of weight change) | 3.0 bps | sum of the two rows above; the convention every committed candidate is costed on |
| Risk-free rate | 2.00% annual | `src/backtest/engine.py:get_risk_free_rate()` → `config/settings.yaml:evaluation.risk_free_rate_annual` = 0.02 |
| Funding rate (placeholder) | 0.00% annual | `config/settings.yaml:backtest.default_funding_rate_annual` — a placeholder, **not** a perpetual-funding model |
| Minimum trade size | $10.00 | `config/settings.yaml:backtest.min_trade_size_usd` |

### 4.1 Cost keys found in the configuration (19 config files scanned)

| Component | Configured as | Files |
|---|---|---|
| commission | **yes** | `calendar_effects_001.yaml:cost_model.commission_bps` = 1.0, `commoditytrend_001.yaml:cost_model.commission_bps` = 1.0, `cryptofunding_001.yaml:cost_model.commission_bps_per_unit` = 3.0, `csmomentum_001.yaml:costs.commission_bps` = 1.0, `csmomentum_candidate_001.yaml:cost_model.commission_bps` = 1.0, `leadlag_candidate_001.yaml:cost_model.commission_bps` = 1.0, `liquidity_candidate_001.yaml:cost_model.commission_bps` = 1.0, `macroregime_candidate_001.yaml:cost_model.commission_bps` = 1.0, `pairs_candidate_001.yaml:cost_model.commission_bps` = 1.0, `reversal_candidate_001.yaml:cost_model.commission_bps` = 1.0, `sectorrotation_002.yaml:costs.commission_bps` = 1.0, `sectorrotation_candidate_001.yaml:cost_model.commission_bps` = 1.0, `settings.yaml:backtest.default_commission_bps` = 1.0, `simulation_candidate_001.yaml:cost_model.commission_bps` = 1.0, `simulation_candidate_001_corrected.yaml:cost_model.commission_bps` = 1.0 |
| slippage | **yes** | `calendar_effects_001.yaml:cost_model.slippage_bps` = 2.0, `commoditytrend_001.yaml:cost_model.slippage_bps` = 2.0, `cryptofunding_001.yaml:cost_model.slippage_bps_per_unit` = 2.0, `csmomentum_001.yaml:costs.slippage_bps` = 2.0, `csmomentum_candidate_001.yaml:cost_model.slippage_bps` = 2.0, `leadlag_candidate_001.yaml:cost_model.slippage_bps` = 2.0, `liquidity_candidate_001.yaml:cost_model.slippage_bps` = 2.0, `macroregime_candidate_001.yaml:cost_model.slippage_bps` = 2.0, `pairs_candidate_001.yaml:cost_model.slippage_bps` = 2.0, `reversal_candidate_001.yaml:cost_model.slippage_bps` = 2.0, `sectorrotation_002.yaml:costs.slippage_bps` = 2.0, `sectorrotation_candidate_001.yaml:cost_model.slippage_bps` = 2.0, `settings.yaml:backtest.default_slippage_bps` = 2.0, `simulation_candidate_001.yaml:cost_model.slippage_bps` = 2.0, `simulation_candidate_001_corrected.yaml:cost_model.slippage_bps` = 2.0 |
| round_trip | **yes** | `calendar_effects_001.yaml:cost_model.total_round_trip_bps` = 3.0, `commoditytrend_001.yaml:cost_model.total_round_trip_bps` = 3.0, `cryptofunding_001.yaml:cost_model.total_round_trip_bps` = 5.0, `csmomentum_001.yaml:costs.roundtrip_bps` = 3.0, `csmomentum_candidate_001.yaml:cost_model.total_round_trip_bps` = 3.0, `leadlag_candidate_001.yaml:cost_model.total_round_trip_bps` = 3.0, `liquidity_candidate_001.yaml:cost_model.total_round_trip_bps` = 3.0, `macroregime_candidate_001.yaml:cost_model.total_round_trip_bps` = 3.0, `pairs_candidate_001.yaml:cost_model.total_round_trip_bps` = 3.0, `reversal_candidate_001.yaml:cost_model.total_round_trip_bps` = 3.0, `sectorrotation_002.yaml:costs.roundtrip_bps` = 3.0, `sectorrotation_candidate_001.yaml:cost_model.total_round_trip_bps` = 3.0, `simulation_candidate_001.yaml:cost_model.total_round_trip_bps` = 3.0, `simulation_candidate_001_corrected.yaml:cost_model.total_round_trip_bps` = 3.0 |
| funding | **yes** | `cryptofunding_001.yaml:data.funding_frequency` = 8h, `cryptofunding_001.yaml:data.raw_funding` = ['data/raw/crypto/BTC_USDT_USDT_funding_binance.parquet', 'data/raw/crypto/ETH_USDT_USDT_funding_binance.parquet'], `cryptofunding_001.yaml:data.rows_per_symbol_funding_8h` = 7395, `settings.yaml:backtest.default_funding_rate_annual` = 0.0 |
| risk_free | **yes** | `commoditytrend_001.yaml:cost_model.risk_free_rate_annual` = 0.02, `leadlag_candidate_001.yaml:cost_model.risk_free_rate_annual` = 0.02, `pairs_candidate_001.yaml:cost_model.risk_free_rate_annual` = 0.02, `settings.yaml:evaluation.risk_free_rate_annual` = 0.02 |
| bid_ask_spread | **NOT CONFIGURED** | — |
| borrow | **yes** | `pairs_candidate_001.yaml:cost_model.borrow_bps_per_unit_short_notional_per_rebalance` = 25.0, `pairs_candidate_001.yaml:evaluation.borrow.bps_per_unit_short_notional_per_rebalance` = 25.0 |
| roll | **NOT CONFIGURED** | — |
| market_impact | **NOT CONFIGURED** | — |
| latency | **NOT CONFIGURED** | — |
| margin | **NOT CONFIGURED** | — |

**Measured cost gaps.** 5 components that a credible net-of-cost evaluation would need have **no configuration key at all**: bid-ask spread, futures roll cost, market impact, latency, margin.

Components priced **outside** the shared cost model (a candidate's own pre-registered assumption, not part of `config/settings.yaml` and not applied to any other candidate): **borrow** -> `pairs_candidate_001.yaml:cost_model.borrow_bps_per_unit_short_notional_per_rebalance` = 25.0, `pairs_candidate_001.yaml:evaluation.borrow.bps_per_unit_short_notional_per_rebalance` = 25.0. A key that only *names* a component (for example the module that detects a roll) describes a rule, not a price, and is not counted as one.

Consequences that bind today: (i) the flat 2 bps slippage is the *entire* execution-cost model, so any claim of an edge below roughly 3 bps per unit of turnover is inside the model's own uncertainty; (ii) a short-side or lending candidate is costed only by the candidate's own pre-registered assumption, never by the shared model; (iii) a futures roll candidate cannot be charged for the roll.

## 5. Scored candidate shortlist

### 5.1 Scoring method

Criteria (a)–(g) are AGENTS.md's: (a) data quality/access, (b) structural mechanism, (c) expected net return after costs, (d) robustness and statistical power, (e) liquidity/capacity, (f) automation/operating burden, (g) diversification from the existing research.

* **(a) is measured** by a rubric evaluated on the cached files of each candidate's universe: `1` base, `+2` for ≥20 years of history (`+1` for ≥10), `+2` for a checksum-pinned archive (`+1` for a provider cache, `0` for a plain API), `+1` for zero missing prices **and** zero duplicate timestamps, `+1` when the coverage lag is ≤1 session (`0` for ≤10, `−1` beyond), `−1` when the universe contains a non-tradable index; the result is clamped to 1–5 and then capped where the candidate's mechanism needs a series the repository does not hold.
* **(b)–(g) are carried** from the committed shortlist (`research/reports/opportunity_shortlist.md`) and are changed only where a later committed record supplies new evidence; every change is listed in section 5.4 with its citation.
* **A data-readiness score may be lowered by measured evidence, never raised**: the published (a) score is the more pessimistic of the committed score and the measured rubric.

### 5.2 Measured data-readiness rubric

| Candidate | Depth (y) | Weakest provenance | Missing prices | Duplicate timestamps | Max coverage lag (sessions) | Rubric score | Committed (a) | Published (a) |
|---|---|---|---|---|---|---|---|---|
| TSMOM incumbent | 21.93 | yfinance-cache | 0 | 0 | 0 | 5 | 5 | 5 |
| Long-only cross-sectional momentum, broad 18-ETF universe | 20.70 | yfinance-cache | 0 | 0 | 11 | 4 | 5 | 4 |
| Sector rotation | 27.79 | yfinance-cache | 0 | 0 | 11 | 4 | 5 | 4 |
| Calendar / rebalancing effects | 26.41 | yfinance-cache | 0 | 0 | 0 | 5 | 5 | 5 |
| TSMOM parameter variants | 21.93 | yfinance-cache | 0 | 0 | 0 | 5 | 5 | 5 |
| Macro regime overlay extension | 21.93 | yfinance-cache | 0 | 0 | 0 | 5 | 4 | 4 |
| Crypto perpetual funding-rate carry | 6.75 | binance-archive | 0 | 0 | 20 | 3 | 4 | 3 |
| Commodity/rate futures basis and roll yield | 11.78 | yfinance-cache | 0 | 0 | 6 | 2 | 2 | 2 |
| Volatility risk premium | 0.00 | none present in the cache | 0 | 0 | 0 | 2 | 2 | 2 |
| Intraday session / time-of-day effects | 0.00 | none present in the cache | 0 | 0 | 0 | 1 | 1 | 1 |

The rubric reproduces the committed (a) score for eight of the ten candidates; the two differences are: the crypto carry (measured lower — the Binance archive has not published October 2026, so its price legs lag the OKX cross-check by 20 days) and the macro-regime overlay (the committed table deducted a point for ^VIX's non-tradability; the measured rubric applies the same deduction and still lands one point higher, so the committed score is kept as the more pessimistic of the two).

### 5.3 The shortlist

| Measured rank | Candidate | (a) | (b) | (c) | (d) | (e) | (f) | (g) | Total | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | TSMOM incumbent (`tsmomentum_spytrend_001`) | 5 | 4 | 4 | 3 | 5 | 5 | 5 | **31/35** | Credible candidate -- published PASS survives the non-overlapping fold design (Cycle 910) but is NOT phase-stable (Cycle 911) |
| 2 | Long-only cross-sectional momentum, broad 18-ETF universe (`csmomentum_001`) | 4 | 5 | 2 | 2 | 5 | 4 | 4 | **26/35** | Rejected/Failed -- gate 1 fails on every pre-registered sample and under the non-overlapping fold design |
| 3 | Sector rotation (`sectorrotation_001`) | 4 | 4 | 2 | 2 | 5 | 4 | 4 | **25/35** | Rejected -- the candidate's own pre-registered falsification condition is met |
| 4 | Calendar / rebalancing effects (`calendar_effects_001`) | 5 | 3 | 2 | 2 | 5 | 4 | 4 | **25/35** | Rejected -- gate 1 fails (walk-forward mean OOS Sharpe -0.0254); cost-admissible but with no edge |
| 5 | TSMOM parameter variants (`tsmomentum_variants`) | 5 | 4 | 2 | 2 | 5 | 5 | 2 | **25/35** | Rejected -- 0 of 100 configurations beat the baseline on identical data; the committed parameters sit on a peak, not a plateau |
| 6 | Macro regime overlay extension (`macroregime_001`) | 4 | 4 | 2 | 2 | 3 | 4 | 3 | **22/35** | Rejected -- the pre-registered falsification condition is met |
| 7 | Crypto perpetual funding-rate carry (`cryptofunding`) | 3 | 4 | 3 | 3 | 5 | 3 | 1 | **22/35** | Exploratory signal -- the net-of-cost edge is real but thin out of sample and the promotion gate's trade-count criterion fails in all 24 cost-model rows |
| 8 | Commodity/rate futures basis and roll yield (`futuresbasis`) | 2 | 4 | 3 | 2 | 3 | 2 | 5 | **21/35** | Rejected -- both routes rejected (contract-leg route unbuildable; ETF route negative carry, research/experiments/futuresbasis_002.md) |
| 9 | Volatility risk premium (`vol_risk_premium`) | 2 | 4 | 2 | 2 | 2 | 2 | 4 | **18/35** | Blocked by data -- no tradeable volatility instrument in the repository |
| 10 | Intraday session / time-of-day effects (`overnight_capture_001`) | 1 | 3 | 2 | 1 | 4 | 2 | 4 | **17/35** | Rejected -- no intraday equity series in the cache (the only sub-daily series are the 8-hourly crypto funding files); the overnight variant is inadmissible on cost (break-even 1.74 bp/unit against the 3 bp/unit charged) |

The committed table ranked the futures-basis candidate 7 and the crypto carry 8 even though the crypto carry scored higher (23 vs 21); the ordering above is by the measured total, ties broken by the committed rank.

### 5.4 Changes against the committed shortlist

| Candidate | Criterion | Committed | Revised | Evidence | Reason |
|---|---|---|---|---|---|
| TSMOM incumbent | (D) | 4 | 3 | `research/experiments/tsmomentum_walkforward_mean_robustness_001.md (Cycle 911)` | the published walk-forward PASS is not phase-stable: phase A (odd folds) mean 1.3850 passes gate 1, phase B (even folds) mean 0.5096 fails it, and excluding the two thin-trade folds does not change that |
| Long-only cross-sectional momentum, broad 18-ETF universe | (C) | 3 | 2 | `research/experiments/csmomentum_common_inception_001.md (Cycle 907); research/experiments/csmomentum_walkforward_embargo_001.md (Cycle 908)` | gate 1 (walk-forward mean OOS Sharpe >= 0.9) fails on every pre-registered sample (union 0.6975 backtest scale / 0.8404 canonical; common-inception slice 0.5861 / 0.7577) and under the non-overlapping fold design (0.6983 / 0.8433) |
| Long-only cross-sectional momentum, broad 18-ETF universe | (D) | 3 | 2 | `research/experiments/csmomentum_common_inception_001.md (Cycle 907)` | the candidate's own pre-registered falsification condition (gate 1) is met on all three samples and the plateau gate is NOT EVALUATED, so the published gate table is incomplete by construction |
| Sector rotation | (C) | 3 | 2 | `research/experiments/sectorrotation_long_sample_feasibility_001.md (Cycle 869); research/experiments/sectorrotation_walkforward_embargo_001.md (Cycle 907)` | published walk-forward mean 0.847243 and non-overlapping 0.770297 both fail gate 1; the long-sample canonical Sharpe is 0.472367 with a -47.16% max drawdown |
| Sector rotation | (D) | 3 | 2 | `research/experiments/sectorrotation_long_sample_feasibility_001.md (Cycle 869)` | the candidate's own pre-registered falsification condition is met, and the excess over an equal-weight 1/N benchmark is +0.0035 Sharpe |
| Calendar / rebalancing effects | (D) | 3 | 2 | `research/experiments/calendar_effects_baseline_wf_001.md (Cycle 18)` | gate 1 fails: walk-forward mean OOS Sharpe -0.0254 over 33 folds |
| Macro regime overlay extension | (C) | 3 | 2 | `research/experiments/macroregime_baseline_wf_001.md (Cycle 19)` | gate 1 fails: walk-forward mean OOS Sharpe 0.4331 over 24 folds |
| Macro regime overlay extension | (D) | 3 | 2 | `research/experiments/macroregime_baseline_wf_001.md (Cycle 19)` | the pre-registered falsification condition (walk-forward mean < 0.9) is met |

Verdicts carried unchanged (with their committed citations):

* **TSMOM parameter variants** — Rejected -- 0 of 100 configurations beat the baseline on identical data; the committed parameters sit on a peak, not a plateau. (`research/experiments/tsmomentum_robustness_001.md`)
* **Crypto perpetual funding-rate carry** — Exploratory signal -- the net-of-cost edge is real but thin out of sample and the promotion gate's trade-count criterion fails in all 24 cost-model rows. (`research/experiments/cryptofunding_002_evaluation.md`)
* **Commodity/rate futures basis and roll yield** — Rejected -- both routes rejected (contract-leg route unbuildable; ETF route negative carry, research/experiments/futuresbasis_002.md). (`research/experiments/futuresbasis_002.md`)
* **Volatility risk premium** — Blocked by data -- no tradeable volatility instrument in the repository. (`research/reports/data_inventory.md`)
* **Intraday session / time-of-day effects** — Rejected -- no intraday equity series in the cache (the only sub-daily series are the 8-hourly crypto funding files); the overnight variant is inadmissible on cost (break-even 1.74 bp/unit against the 3 bp/unit charged). (`research/reports/cost_admissibility_screen_001.md`)

## 6. Explicit rejection reasons

| Segment | Ground | Reason | Citation |
|---|---|---|---|
| Intraday session / time-of-day effects (overnight capture) | no data (and infeasible execution) | The cache holds no intraday equity series (0 of the equity/futures files are finer than daily; the finest spacing in the whole cache is the 8-hourly crypto funding series), so no open/close decomposition and no session-effect test can be formed; the overnight variant is separately inadmissible on cost (504 units/yr of turnover, +15.12%/yr of drag against a +9.16%/yr gross signal, break-even 1.74 bp/unit against the 3 bp/unit the repository charges). | `research/reports/cost_admissibility_screen_001.md` |
| Volatility risk premium (short vol / variance premium) | no tradable instrument | Only the ^VIX index is cached and it is not a return series (Volume == 0 on every row); no VIX future, VIX E/TN or option history exists in the repository, so the candidate cannot be expressed, costed or tested. | `research/reports/data_inventory.md` |
| Commodity / rate futures basis and roll yield | unobservable roll prices; rejected ETF route | Four front-month continuous series are cached and the roll dates are observable from the volume signature, but the contract-leg closes that price a roll are not in the repository (nine source classes probed); the ETF route (USO/BNO/UNG/GSG) was rejected on cost -- all four show negative annualised carry against GLD over 2015-2026. | `research/reports/futures_roll_visibility_001.md; research/experiments/futuresbasis_002.md` |
| FX carry / cross-border rate differentials | no data | The cache contains no FX series and no interest-rate differential series, so neither the price leg nor the funding leg of a carry trade can be observed offline. | `research/reports/data_inventory.md` |
| Any short-side / securities-lending candidate | omitted costs (no borrow model) | No configuration in `config/` defines a borrow or short-sale cost, and no borrow-rate series is cached; a short-leg candidate therefore cannot be costed with the repository's own cost model. | `config/ (measured: no key matching 'borrow' in any config file)` |
| Calendar / rebalancing effects (month-end, quarter-end flows) | gate 1 fails | The candidate is testable and cost-admissible (break-even 11.16 bp/unit against the 3 bp/unit charged), but its walk-forward mean OOS Sharpe is -0.0254 over 33 folds: the effect is not present net of costs, so there is nothing to capture. | `research/experiments/calendar_effects_baseline_wf_001.md` |
| Cross-sectional momentum (18-ETF) and sector rotation | gate 1 fails on every pre-registered sample | Both candidates are fully testable with the cache, and both fail their own pre-registered gate: 0.6975/0.8404 (union), 0.5861/0.7577 (common-inception slice) for csmomentum_001, and 0.847243 published / 0.770297 non-overlapping for sectorrotation_001. | `research/experiments/csmomentum_common_inception_001.md; research/experiments/sectorrotation_walkforward_embargo_001.md` |
| Crypto perpetual funding carry -- any rule keyed on the same day's funding | look-ahead | The funding rate of a UTC day is settled at 00:00/08:00/16:00 UTC, so a rule that reads the same day's funding is a look-ahead; the implementable rule decides on the previous day's funding (the repository's committed rule). | `research/experiments/cryptofunding_002_evaluation.md (Cycle 891)` |

Rejected on the candidate's own pre-registered gate (the numeric evidence is in section 5.4): cross-sectional momentum over the broad 18-ETF universe, sector rotation, the macro-regime overlay extension and the calendar/rebalancing-effects candidate.

## 7. Price predictability vs executable net edge

Every candidate the cache can support has now been carried through the repository's own walk-forward protocol at its own cost model (the crypto carry additionally through a realistic fee, slippage and capital-charge model). Only the incumbent clears the 0.9 walk-forward gate; the crypto carry's promotion gate fails in all 24 of its cost-model rows; the other four candidates fail gate 1 outright. The inventory explains why the others cannot be rescued by better data: their universe, sample and cost assumptions are already the ones the repository's own protocol uses, and their gate failures are properties of the effect, not of the measurement.

The data-readiness picture that survives this cycle is: one 33-year daily ETF cache with zero missing prices and zero duplicate timestamps; one 6.75-year, checksum-pinned crypto archive (spot, perpetual and 8-hourly funding for BTC and ETH) whose newest observation is 23 days behind the equity cache (2026-10-23); and no intraday equity, options, FX, borrow or contract-leg data at all. The next candidate segment must therefore be built from what the cache actually holds, or the cache must be extended first — with the extension itself being the preregistered, costed step.

## 8. Reproduction

```bash
python research/data_cost_inventory_001.py
python -m pytest -q tests/test_data_cost_inventory_001.py
python -m pytest -q
git status --porcelain data/
git diff --stat src/ config/ research/experiments/ research/reports/
```

Every number in this report is re-derived by the first command from the committed cache, `config/` and `src/backtest/engine.py` alone.
