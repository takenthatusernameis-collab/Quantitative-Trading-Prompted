# Data and Cost Inventory 002 — Cycle 929

**Method:** read-only, cache-only inspection of the committed repository. `research/data_cost_inventory_002.py` re-measures the cache, re-verifies the digests published by the Cycle-912 inventory, re-derives the configured cost model, and measures the **point-in-time universe membership** of the incumbent's published walk-forward. No backtest was re-tuned, no candidate was promoted, no fetcher was called and nothing under `data/` or `config/` was written.

**Determinism:** this document contains no timestamp and no run id; two consecutive generations are byte-identical.

## 1. Data inventory — `data/raw/`

**35 parquet files, 180184 rows** (22 ETF, 4 futures, 8 crypto, 1 index). **0 missing prices**, **0 duplicate timestamps**, **1 (n/a for the 4 funding-rate files) non-positive prices**, **8599 (n/a for the 4 funding-rate files) zero-volume rows**.

The counters marked *n/a* apply to the crypto funding-rate files: a funding rate is a signed rate (a negative value is ordinary, not an anomaly) and the series carries no volume column.

| # | Path | Asset class | Rows | First | Last | Freq | Missing | Dup | Repeat | Non-pos | Zero-vol | SHA-256 (16) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `data/raw/BNO.parquet` | etf | 4123 | 2010-06-02 | 2026-10-21 | daily | 0 | 0 | 77 | 0 | 27 | `f9f85c5844ba3884` |
| 2 | `data/raw/CL-F.parquet` | futures | 2964 | 2015-01-02 | 2026-10-15 | daily | 0 | 0 | 12 | 1 | 7 | `5d7ec126885110fc` |
| 3 | `data/raw/DBC.parquet` | etf | 5210 | 2006-02-06 | 2026-10-21 | daily | 0 | 0 | 85 | 0 | 0 | `a04e11a54bb3710f` |
| 4 | `data/raw/EEM.parquet` | etf | 5920 | 2003-04-14 | 2026-10-22 | daily | 0 | 0 | 40 | 0 | 0 | `17ad1692de6eee0b` |
| 5 | `data/raw/EFA.parquet` | etf | 6326 | 2001-08-27 | 2026-10-22 | daily | 0 | 0 | 49 | 0 | 0 | `f72c519b09744671` |
| 6 | `data/raw/GC-F.parquet` | futures | 2964 | 2015-01-02 | 2026-10-15 | daily | 0 | 0 | 15 | 0 | 36 | `2dc89075a6bfe3a9` |
| 7 | `data/raw/GLD.parquet` | etf | 5516 | 2004-11-18 | 2026-10-22 | daily | 0 | 0 | 20 | 0 | 0 | `6e681051e18253fa` |
| 8 | `data/raw/GSG.parquet` | etf | 2964 | 2015-01-02 | 2026-10-15 | daily | 0 | 0 | 59 | 0 | 0 | `d38c0d9bed4894da` |
| 9 | `data/raw/IWM.parquet` | etf | 6641 | 2000-05-26 | 2026-10-22 | daily | 0 | 0 | 20 | 0 | 0 | `0e32b42393e5dad6` |
| 10 | `data/raw/NG-F.parquet` | futures | 2965 | 2015-01-02 | 2026-10-15 | daily | 0 | 0 | 11 | 0 | 7 | `6d480ef7769f42eb` |
| 11 | `data/raw/QQQ.parquet` | etf | 6949 | 1999-03-10 | 2026-10-22 | daily | 0 | 0 | 38 | 0 | 0 | `3de8a01c4f0d6f77` |
| 12 | `data/raw/SPY.parquet` | etf | 8491 | 1993-01-29 | 2026-10-22 | daily | 0 | 0 | 62 | 0 | 0 | `f307f910a62dc3e2` |
| 13 | `data/raw/TLT.parquet` | etf | 6098 | 2002-07-30 | 2026-10-22 | daily | 0 | 0 | 31 | 0 | 0 | `851db269e1622eb6` |
| 14 | `data/raw/UNG.parquet` | etf | 4910 | 2007-04-18 | 2026-10-21 | daily | 0 | 0 | 63 | 0 | 0 | `0ce2a5b25a2e8e6b` |
| 15 | `data/raw/USO.parquet` | etf | 2964 | 2015-01-02 | 2026-10-15 | daily | 0 | 0 | 23 | 0 | 0 | `fa22094f98b4e826` |
| 16 | `data/raw/VNQ.parquet` | etf | 5542 | 2004-09-29 | 2026-10-08 | daily | 0 | 0 | 30 | 0 | 0 | `8714f6b1bf45d1b0` |
| 17 | `data/raw/XLB.parquet` | etf | 6991 | 1998-12-22 | 2026-10-08 | daily | 0 | 0 | 78 | 0 | 0 | `465b9a7b6c784869` |
| 18 | `data/raw/XLE.parquet` | etf | 6991 | 1998-12-22 | 2026-10-08 | daily | 0 | 0 | 50 | 0 | 0 | `408b2806f7dbde65` |
| 19 | `data/raw/XLF.parquet` | etf | 6991 | 1998-12-22 | 2026-10-08 | daily | 0 | 0 | 100 | 0 | 0 | `2f8eeb83b2024b69` |
| 20 | `data/raw/XLI.parquet` | etf | 6991 | 1998-12-22 | 2026-10-08 | daily | 0 | 0 | 70 | 0 | 1 | `176eaa15a62526ec` |
| 21 | `data/raw/XLK.parquet` | etf | 6991 | 1998-12-22 | 2026-10-08 | daily | 0 | 0 | 78 | 0 | 0 | `b66776c5c1c70885` |
| 22 | `data/raw/XLP.parquet` | etf | 6991 | 1998-12-22 | 2026-10-08 | daily | 0 | 0 | 130 | 0 | 0 | `d1ac5528a51c5470` |
| 23 | `data/raw/XLU.parquet` | etf | 6991 | 1998-12-22 | 2026-10-08 | daily | 0 | 0 | 88 | 0 | 0 | `c9550ef0e461368e` |
| 24 | `data/raw/XLV.parquet` | etf | 6991 | 1998-12-22 | 2026-10-08 | daily | 0 | 0 | 91 | 0 | 0 | `bcf7029ba61bac58` |
| 25 | `data/raw/XLY.parquet` | etf | 6991 | 1998-12-22 | 2026-10-08 | daily | 0 | 0 | 65 | 0 | 0 | `7a64cd50a03d5d70` |
| 26 | `data/raw/ZB-F.parquet` | futures | 2964 | 2015-01-02 | 2026-10-15 | daily | 0 | 0 | 37 | 0 | 9 | `26f740c341408310` |
| 27 | `data/raw/^VIX.parquet` | index (non-tradable) | 8512 | 1993-01-04 | 2026-10-22 | daily | 0 | 0 | 47 | 0 | 8512 | `15b03407de4f693e` |
| 28 | `data/raw/crypto/BTCUSDT_perp_1d_binance.parquet` | crypto | 2465 | 2020-01-01 | 2026-09-30 | daily | 0 | 0 | 0 | 0 | 0 | `b512246ba875b0d6` |
| 29 | `data/raw/crypto/BTCUSDT_spot_1d_binance.parquet` | crypto | 2465 | 2020-01-01 | 2026-09-30 | daily | 0 | 0 | 0 | 0 | 0 | `0fd946222a284885` |
| 30 | `data/raw/crypto/BTC_USDT_USDT_funding.parquet` | crypto | 296 | 2026-07-13 | 2026-10-20 | 8-hourly | 0 | 0 | 19 | - | - | `1c5ded033f01acc7` |
| 31 | `data/raw/crypto/BTC_USDT_USDT_funding_binance.parquet` | crypto | 7395 | 2020-01-01 | 2026-09-30 | 8-hourly | 0 | 0 | 1902 | - | - | `4d3b4d653eaf2b09` |
| 32 | `data/raw/crypto/ETHUSDT_perp_1d_binance.parquet` | crypto | 2465 | 2020-01-01 | 2026-09-30 | daily | 0 | 0 | 1 | 0 | 0 | `5f3ea46cac53e52c` |
| 33 | `data/raw/crypto/ETHUSDT_spot_1d_binance.parquet` | crypto | 2465 | 2020-01-01 | 2026-09-30 | daily | 0 | 0 | 0 | 0 | 0 | `fee74e1349095aca` |
| 34 | `data/raw/crypto/ETH_USDT_USDT_funding.parquet` | crypto | 296 | 2026-07-13 | 2026-10-20 | 8-hourly | 0 | 0 | 14 | - | - | `9b86f26b4febd486` |
| 35 | `data/raw/crypto/ETH_USDT_USDT_funding_binance.parquet` | crypto | 7395 | 2020-01-01 | 2026-09-30 | 8-hourly | 0 | 0 | 1924 | - | - | `50c57313802809e3` |

### 1.1 Processed artefacts

| Group | Files | Rows | First | Last |
|---|---|---|---|---|
| `data/processed/(top level)` | 16 | 101640 | 1993-01-29 | 2026-10-09 |
| `data/processed/crypto` | 2 | 4928 | 2020-01-02 | 2026-09-30 |
| `data/processed/paper_trading` | 1812 | 4530 | 2025-01-02 | 2026-10-22 |

## 2. Drift audit against the committed Cycle-912 inventory

The published inventory (`research/reports/data_cost_inventory_001.md`) pins a SHA-256 prefix for every cached price file. This tool re-computes them: **35 of 35 match**, **0 changed**, **0 removed**, **0 added**.

The configuration file set has changed: the published scan covered **15 files** (the report states "19 config files scanned"), the current tree holds **19**. Added: `config/overnight_capture_001.yaml`, `config/paper_trading_config.yaml`, `config/promotion_gates.yaml`, `config/sample_policy.yaml`. Removed: none.

## 3. The cost model actually available

| Component | Value | Source |
|---|---|---|
| Commission | 1.0 bps per trade | `src/backtest/engine.py:get_cost_params()` -> `config/settings.yaml` |
| Slippage | 2.0 bps per trade | `src/backtest/engine.py:get_cost_params()` -> `config/settings.yaml` |
| Round trip (one unit of weight change) | 3.0 bps | the convention every committed candidate is costed on |
| Risk-free rate | 2.00% annual | `src/backtest/engine.py:get_risk_free_rate()` |

**19 configuration files scanned.** Components with a configuration key:

| Component | Keys found |
|---|---|
| commission | `config/calendar_effects_001.yaml:54:commission_bps = 1.0`<br>`config/commoditytrend_001.yaml:69:commission_bps = 1.0`<br>`config/cryptofunding_001.yaml:49:commission_bps_per_unit = 3.0`<br>`config/csmomentum_001.yaml:47:commission_bps = 1.0`<br>`config/csmomentum_candidate_001.yaml:53:commission_bps = 1.0`<br>`config/leadlag_candidate_001.yaml:71:commission_bps = 1.0`<br>`config/liquidity_candidate_001.yaml:51:commission_bps = 1.0`<br>`config/macroregime_candidate_001.yaml:52:commission_bps = 1.0`<br>`config/pairs_candidate_001.yaml:66:commission_bps = 1.0`<br>`config/reversal_candidate_001.yaml:53:commission_bps = 1.0`<br>`config/sectorrotation_002.yaml:35:commission_bps = 1.0`<br>`config/sectorrotation_candidate_001.yaml:55:commission_bps = 1.0`<br>`config/settings.yaml:14:default_commission_bps = 1.0`<br>`config/simulation_candidate_001.yaml:41:commission_bps = 1.0`<br>`config/simulation_candidate_001_corrected.yaml:53:commission_bps = 1.0` |
| slippage | `config/calendar_effects_001.yaml:55:slippage_bps = 2.0`<br>`config/commoditytrend_001.yaml:70:slippage_bps = 2.0`<br>`config/cryptofunding_001.yaml:50:slippage_bps_per_unit = 2.0`<br>`config/csmomentum_001.yaml:48:slippage_bps = 2.0`<br>`config/csmomentum_candidate_001.yaml:54:slippage_bps = 2.0`<br>`config/leadlag_candidate_001.yaml:72:slippage_bps = 2.0`<br>`config/liquidity_candidate_001.yaml:52:slippage_bps = 2.0`<br>`config/macroregime_candidate_001.yaml:53:slippage_bps = 2.0`<br>`config/pairs_candidate_001.yaml:67:slippage_bps = 2.0`<br>`config/reversal_candidate_001.yaml:54:slippage_bps = 2.0`<br>`config/sectorrotation_002.yaml:36:slippage_bps = 2.0`<br>`config/sectorrotation_candidate_001.yaml:56:slippage_bps = 2.0`<br>`config/settings.yaml:15:default_slippage_bps = 2.0`<br>`config/simulation_candidate_001.yaml:42:slippage_bps = 2.0`<br>`config/simulation_candidate_001_corrected.yaml:54:slippage_bps = 2.0` |
| round_trip | `config/calendar_effects_001.yaml:56:total_round_trip_bps = 3.0`<br>`config/commoditytrend_001.yaml:71:total_round_trip_bps = 3.0`<br>`config/cryptofunding_001.yaml:51:total_round_trip_bps = 5.0`<br>`config/csmomentum_001.yaml:49:roundtrip_bps = 3.0`<br>`config/csmomentum_candidate_001.yaml:55:total_round_trip_bps = 3.0`<br>`config/leadlag_candidate_001.yaml:73:total_round_trip_bps = 3.0`<br>`config/liquidity_candidate_001.yaml:53:total_round_trip_bps = 3.0`<br>`config/macroregime_candidate_001.yaml:54:total_round_trip_bps = 3.0`<br>`config/pairs_candidate_001.yaml:68:total_round_trip_bps = 3.0`<br>`config/reversal_candidate_001.yaml:55:total_round_trip_bps = 3.0`<br>`config/sectorrotation_002.yaml:37:roundtrip_bps = 3.0`<br>`config/sectorrotation_candidate_001.yaml:57:total_round_trip_bps = 3.0`<br>`config/simulation_candidate_001.yaml:43:total_round_trip_bps = 3.0`<br>`config/simulation_candidate_001_corrected.yaml:55:total_round_trip_bps = 3.0` |
| funding | `config/cryptofunding_001.yaml:73:funding_frequency = "8h"`<br>`config/cryptofunding_001.yaml:78:raw_funding = `<br>`config/cryptofunding_001.yaml:89:rows_per_symbol_funding_8h = 7395`<br>`config/settings.yaml:16:default_funding_rate_annual = 0.0` |
| risk_free | `config/commoditytrend_001.yaml:72:risk_free_rate_annual = 0.02`<br>`config/leadlag_candidate_001.yaml:74:risk_free_rate_annual = 0.02`<br>`config/pairs_candidate_001.yaml:74:risk_free_rate_annual = 0.02`<br>`config/settings.yaml:20:risk_free_rate_annual = 0.02` |

Components with **no configuration key at all**: `bid_ask_spread`, `roll`, `market_impact`, `latency`, `margin`. The cost axis itself is closed by the committed Cycle-913 break-even audit (`research/reports/cost_gate_break_even_001.md`), which measures the bid-ask floor from the cache and the cost level at which each gate flips; this inventory re-states the gap and does not redo that measurement.

Components priced **outside** the shared cost model (a candidate's own pre-registered assumption, not part of `config/settings.yaml` and not applied to any other candidate): `borrow` -> `config/pairs_candidate_001.yaml:73:borrow_bps_per_unit_short_notional_per_rebalance = 25.0`. A key that only *names* a component (for example the module that detects a roll) describes a rule, not a price, and is not counted as one.

## 4. Point-in-time universe membership of the published walk-forward

AGENTS.md lists **point-in-time universe membership** first among the data-readiness criteria, and the committed inventories state that the repository holds "no constituent-level membership" and that this is "not modelled". That statement is about *constituent* membership (index members). The **asset-level** membership of the incumbent's universe is measurable from the cache, and it has never been measured: the seven universe ETFs did not all exist at the start of the published sample, so the *effective* cross-section of the published path grows over the sample.

### 4.1 When each universe member enters the path

A member can only be ranked once it has a valid 226-session momentum that skips the most recent 21 sessions, i.e. 247 sessions of price history.

| Symbol | First cached close | First valid momentum |
|---|---|---|
| SPY | 1993-01-29 | 1994-01-20 |
| QQQ | 1999-03-10 | 2000-03-01 |
| IWM | 2000-05-26 | 2001-05-21 |
| TLT | 2002-07-30 | 2003-07-23 |
| GLD | 2004-11-18 | 2005-11-10 |
| EFA | 2001-08-27 | 2002-08-26 |
| EEM | 2003-04-14 | 2004-04-06 |

### 4.2 The effective cross-section over the sample

| Assets with a valid momentum | Sessions | From | To |
|---|---|---|---|
| 0 | 247 | 1993-01-29 | 1994-01-19 |
| 1 | 1542 | 1994-01-20 | 2000-02-29 |
| 2 | 308 | 2000-03-01 | 2001-05-18 |
| 3 | 315 | 2001-05-21 | 2002-08-23 |
| 4 | 228 | 2002-08-26 | 2003-07-22 |
| 5 | 178 | 2003-07-23 | 2004-04-05 |
| 6 | 404 | 2004-04-06 | 2005-11-09 |
| 7 | 5269 | 2005-11-10 | 2026-10-22 |

**The selection rule degenerates as the cross-section shrinks.** The repository's shared rule (`src/features/momentum.py:select_top_decile`) selects every asset whose cross-sectional rank is at least `max_rank x (1 - 0.5)`, which is a *rank* rule, not a count rule: with `k` assets that carry a valid momentum it holds

| Assets with a valid momentum (`k`) | Held | Share of the cross-section |
|---|---|---|
| 1 | 1 | 100.0% |
| 2 | 2 | 100.0% |
| 3 | 2 | 66.7% |
| 4 | 3 | 75.0% |
| 5 | 3 | 60.0% |
| 6 | 4 | 66.7% |
| 7 | 4 | 57.1% |

so the pre-2006 part of the published path is not the same strategy as the post-2006 part: with 4 assets carrying a valid momentum it holds 3 of them (75%), with 5 it holds 3 (60%) and with 6 it holds 4 (66.7%), where the full 7-asset cross-section holds 4 (57.1%). With one or two assets the rule degenerates further: it holds the single best asset, then both of the two.

### 4.3 The published fold table with its effective cross-section

| Fold | Test window | Breadth at start | Breadth (min/mean) | Mean assets selected | Published OOS Sharpe | Recomputed | Trades | Phase |
|---|---|---|---|---|---|---|---|---|
| 1 | 2002-09-30 .. 2003-09-16 | 4 | 4 / 4.16 | 3.00 | 2.5550 | 2.5550 | 94 | A |
| 2 | 2003-03-25 .. 2004-03-10 | 4 | 4 / 4.66 | 3.00 | 2.5821 | 2.5821 | 215 | B |
| 3 | 2003-09-17 .. 2004-09-02 | 5 | 5 / 5.43 | 3.43 | 0.3027 | 0.3027 | 211 | A |
| 4 | 2004-03-11 .. 2005-02-25 | 5 | 5 / 5.93 | 3.93 | 1.2700 | 1.2700 | 154 | B |
| 5 | 2004-09-03 .. 2005-08-22 | 6 | 6 / 6.00 | 4.00 | 1.9494 | 1.9494 | 146 | A |
| 6 | 2005-02-28 .. 2006-02-14 | 6 | 6 / 6.27 | 4.00 | 2.1849 | 2.1849 | 146 | B |
| 7 | 2005-08-23 .. 2006-08-09 | 6 | 6 / 6.77 | 4.00 | 2.3382 | 2.3382 | 163 | A |
| 8 | 2006-02-15 .. 2007-02-01 | 7 | 7 / 7.00 | 4.00 | 1.8912 | 1.8912 | 207 | B |
| 9 | 2006-08-10 .. 2007-07-27 | 7 | 7 / 7.00 | 4.00 | 1.3166 | 1.3166 | 230 | A |
| 10 | 2007-02-02 .. 2008-01-21 | 7 | 7 / 7.00 | 4.00 | 2.0815 | 2.0815 | 198 | B |
| 11 | 2007-07-30 .. 2008-07-15 | 7 | 7 / 7.00 | 4.00 | 2.7409 | 2.7409 | 78 | A |
| 12 | 2008-01-22 .. 2009-01-07 | 7 | 7 / 7.00 | 4.00 | -21.8299 | -21.8299 | 2 | B |
| 13 | 2008-07-16 .. 2009-07-02 | 7 | 7 / 7.00 | 4.00 | -0.2665 | -0.2665 | 8 | A |
| 14 | 2009-01-08 .. 2009-12-25 | 7 | 7 / 7.00 | 4.00 | 1.7670 | 1.7670 | 114 | B |
| 15 | 2009-07-03 .. 2010-06-21 | 7 | 7 / 7.00 | 4.00 | 1.5242 | 1.5242 | 212 | A |
| 16 | 2009-12-28 .. 2010-12-14 | 7 | 7 / 7.00 | 4.00 | 1.0671 | 1.0671 | 150 | B |
| 17 | 2010-06-22 .. 2011-06-08 | 7 | 7 / 7.00 | 4.00 | 1.0960 | 1.0960 | 164 | A |
| 18 | 2010-12-15 .. 2011-12-01 | 7 | 7 / 7.00 | 4.00 | 0.2426 | 0.2426 | 162 | B |
| 19 | 2011-06-09 .. 2012-05-25 | 7 | 7 / 7.00 | 4.00 | 0.9429 | 0.9429 | 50 | A |
| 20 | 2011-12-02 .. 2012-11-19 | 7 | 7 / 7.00 | 4.00 | 1.2267 | 1.2267 | 24 | B |
| 21 | 2012-05-28 .. 2013-05-14 | 7 | 7 / 7.00 | 4.00 | 2.2063 | 2.2063 | 131 | A |
| 22 | 2012-11-20 .. 2013-11-06 | 7 | 7 / 7.00 | 4.00 | 2.1734 | 2.1734 | 238 | B |
| 23 | 2013-05-15 .. 2014-05-01 | 7 | 7 / 7.00 | 4.00 | 0.8107 | 0.8107 | 236 | A |
| 24 | 2013-11-07 .. 2014-10-24 | 7 | 7 / 7.00 | 4.00 | 0.4830 | 0.4830 | 184 | B |
| 25 | 2014-05-02 .. 2015-04-20 | 7 | 7 / 7.00 | 4.00 | 1.1702 | 1.1702 | 102 | A |
| 26 | 2014-10-27 .. 2015-10-13 | 7 | 7 / 7.00 | 4.00 | 0.8976 | 0.8976 | 35 | B |
| 27 | 2015-04-21 .. 2016-04-06 | 7 | 7 / 7.00 | 4.00 | 0.2792 | 0.2792 | 18 | A |
| 28 | 2015-10-14 .. 2016-09-29 | 7 | 7 / 7.00 | 4.00 | 1.3453 | 1.3453 | 28 | B |
| 29 | 2016-04-07 .. 2017-03-24 | 7 | 7 / 7.00 | 4.00 | 0.2969 | 0.2969 | 29 | A |
| 30 | 2016-09-30 .. 2017-09-18 | 7 | 7 / 7.00 | 4.00 | 0.6332 | 0.6332 | 60 | B |
| 31 | 2017-03-27 .. 2018-03-13 | 7 | 7 / 7.00 | 4.00 | 1.6764 | 1.6764 | 75 | A |
| 32 | 2017-09-19 .. 2018-09-05 | 7 | 7 / 7.00 | 4.00 | 1.1373 | 1.1373 | 148 | B |
| 33 | 2018-03-14 .. 2019-02-28 | 7 | 7 / 7.00 | 4.00 | 0.2472 | 0.2472 | 130 | A |
| 34 | 2018-09-06 .. 2019-08-23 | 7 | 7 / 7.00 | 4.00 | 1.0883 | 1.0883 | 28 | B |
| 35 | 2019-03-01 .. 2020-02-17 | 7 | 7 / 7.00 | 4.00 | 3.2521 | 3.2521 | 26 | A |
| 36 | 2019-08-26 .. 2020-08-11 | 7 | 7 / 7.00 | 4.00 | 3.9121 | 3.9121 | 24 | B |
| 37 | 2020-02-18 .. 2021-02-03 | 7 | 7 / 7.00 | 4.00 | 2.3629 | 2.3629 | 124 | A |
| 38 | 2020-08-12 .. 2021-07-29 | 7 | 7 / 7.00 | 4.00 | 0.7952 | 0.7952 | 233 | B |
| 39 | 2021-02-04 .. 2022-01-21 | 7 | 7 / 7.00 | 4.00 | -0.0836 | -0.0836 | 243 | A |
| 40 | 2021-07-30 .. 2022-07-18 | 7 | 7 / 7.00 | 4.00 | -0.1073 | -0.1073 | 148 | B |
| 41 | 2022-01-24 .. 2023-01-10 | 7 | 7 / 7.00 | 4.00 | 0.8947 | 0.8947 | 29 | A |
| 42 | 2022-07-19 .. 2023-07-05 | 7 | 7 / 7.00 | 4.00 | 1.5584 | 1.5584 | 32 | B |
| 43 | 2023-01-11 .. 2023-12-28 | 7 | 7 / 7.00 | 4.00 | 1.8332 | 1.8332 | 118 | A |
| 44 | 2023-07-06 .. 2024-06-21 | 7 | 7 / 7.00 | 4.00 | 1.8186 | 1.8186 | 185 | B |
| 45 | 2023-12-29 .. 2024-12-16 | 7 | 7 / 7.00 | 4.00 | 1.8342 | 1.8342 | 220 | A |
| 46 | 2024-06-24 .. 2025-06-10 | 7 | 7 / 7.00 | 4.00 | 1.1148 | 1.1148 | 186 | B |
| 47 | 2024-12-17 .. 2025-12-03 | 7 | 7 / 7.00 | 4.00 | 1.9609 | 1.9609 | 115 | A |
| 48 | 2025-06-11 .. 2026-05-28 | 7 | 7 / 7.00 | 4.00 | 2.8969 | 2.8969 | 160 | B |

### 4.4 The published statistic on each side of the membership boundary

| Subsample | Folds | Mean OOS Sharpe | 95% CI (moving block) | Positive folds | Pooled trades | Gate 1 (>= 0.9) |
|---|---|---|---|---|---|---|
| All published folds (48) | 48 | 0.947306 | [-0.1181, 1.6041] | 91.67% | 6013 | PASS |
| Point-in-time-complete folds (breadth 7/7) | 41 | 0.787522 | [-0.4244, 1.5431] | 90.24% | 4884 | FAIL |
| Point-in-time-complete folds, artefact fold 12 removed | 40 | 1.352958 | [1.0358, 1.6602] | 92.50% | 4882 | PASS |
| Point-in-time-incomplete folds (breadth < 7/7) | 7 | 1.883186 | [1.1877, 2.3925] | 100.00% | 1129 | PASS |

| Subsample | Gate 1 | Gate 2 (positive folds >= 0.5) | Gate 3 (pooled trades > 100) |
|---|---|---|---|
| All published folds (48) | PASS | PASS | PASS |
| Point-in-time-complete folds (breadth 7/7) | FAIL | PASS | PASS |
| Point-in-time-complete folds, artefact fold 12 removed | PASS | PASS | PASS |
| Point-in-time-incomplete folds (breadth < 7/7) | PASS | PASS | PASS |

### 4.5 The membership split is not the phase split

| Subsample | Phase | Folds | Mean OOS Sharpe | Median |
|---|---|---|---|---|
| all | A | 24 | 1.385029 | 1.4204 |
| all | B | 24 | 0.509583 | 1.2483 |
| complete | A | 20 | 1.304770 | 1.2434 |
| complete | B | 21 | 0.294905 | 1.1373 |
| incomplete | A | 4 | 1.786325 | 2.1438 |
| incomplete | B | 3 | 2.012333 | 2.1849 |

The `all` row is an independent reproduction of the committed Cycle-911 phase decomposition (phase A **1.385029** vs the published **1.385035**, phase B **0.509583** vs the published **0.509580**; the residual is the rounding of the per-fold Sharpes to the four decimals the published fold table carries). The membership split is therefore a **third** axis, not a relabelling of the phase split: the incomplete folds are high in *both* phases (A 1.786325, B 2.012333), so they are not a phase artefact.
## 5. What this does and does not change

- **Nothing published changed.** The published record, the published gates, the published protocol, the shortlist row and every committed candidate artefact are byte-identical after the run; the anchor (48 folds, mean 0.947307, positive rate 91.67%, 6013 pooled trades) is reproduced from the committed cache.
- **The incumbent's verdict is unchanged**: it stays a **Credible Candidate** by its published verdict and **NO-GO** for promotion (failed gates `rolling_63d_sharpe`, `psr`). This audit adds a third stability axis to a verdict that was already NO-GO.
- **The published walk-forward mean is not a homogeneous statistic.** It averages 7 folds measured on an incomplete cross-section (mean 1.883186) with 41 folds measured on the complete one (mean 0.787522; 1.352958 with the fold-12 numerical artefact removed). The gate-1 outcome on the complete subsample therefore depends on that artefact, and neither variant reproduces the published number.
- **The finding is an association, not a mechanism.** The incomplete folds are also the earliest folds, so "incomplete cross-section" and "a favourable 2002-2006 regime for this rule" are not separable in this design. The decision-relevant statement is the same either way: the published statistic does not survive either stability split taken alone.
- **The cost model is unchanged** and the cost axis remains closed by the committed Cycle-913 break-even audit.

## 6. Reproduction

```bash
python research/data_cost_inventory_002.py
python -m pytest -q tests/test_data_cost_inventory_002.py
git status --porcelain data/ config/
```

Every number in this report is re-derived by the first command from the committed cache, `config/`, `src/` and the committed published record.
