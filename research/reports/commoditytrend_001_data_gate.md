# Commodity data gate -- `commoditytrend_001` (Cycle 949)

**Method:** a data-readiness measurement of the pre-registered data gate of `commoditytrend_001`. The upstream history of the frozen universe was fetched into a scratch directory only (`research/commodity_data_gate_fetch.py` refuses to write anywhere inside the repository); this tool measures it and writes nothing under `data/` or `config/`. **No trading verdict is published here** -- the candidate stays *Blocked by data/infrastructure* until the extended panel is committed and the frozen evaluation is run.

**Determinism:** the document carries no run time. Two consecutive generations from the same scratch fetch are byte-identical.

## 1. Provenance of the fetched panel

| Symbol | Source | Retrieved | Price field | Price convention | Rows | First | Last |
|---|---|---|---|---|---|---|---|
| `DBC` | yahoo_finance | 2026-10-22 | Close | raw (auto_adjust=False; the upstream close is split-adjusted but not dividend-adjusted -- the same convention as src/data/yfinance_fetcher.py) | 5210 | 2006-02-06 | 2026-10-21 |
| `BNO` | yahoo_finance | 2026-10-22 | Close | raw (auto_adjust=False; the upstream close is split-adjusted but not dividend-adjusted -- the same convention as src/data/yfinance_fetcher.py) | 4123 | 2010-06-02 | 2026-10-21 |
| `UNG` | yahoo_finance | 2026-10-22 | Close | raw (auto_adjust=False; the upstream close is split-adjusted but not dividend-adjusted -- the same convention as src/data/yfinance_fetcher.py) | 4910 | 2007-04-18 | 2026-10-21 |
| `GLD` | yahoo_finance | 2026-10-22 | Close | raw (auto_adjust=False; the upstream close is split-adjusted but not dividend-adjusted -- the same convention as src/data/yfinance_fetcher.py) | 5515 | 2004-11-18 | 2026-10-21 |

The request window was `2000-01-01 .. 2026-10-22`; the source is the same one the repository's own fetcher uses (`src/data/yfinance_fetcher.py`), with the same `auto_adjust=False` price convention, so the fetched panel is comparable with the committed cache.

## 2. Integrity counters

| Symbol | Rows | Close rows | Missing | Duplicate timestamps | Non-positive | Largest 1-day move | First close | Last close |
|---|---|---|---|---|---|---|---|---|
| `DBC` | 5210 | 5210 | 0 | 0 | 0 | 0.0794 (2022-03-09) | 24.2000 | 33.5000 |
| `BNO` | 4123 | 4123 | 0 | 0 | 0 | 0.2191 (2020-03-09) | 25.5900 | 67.0500 |
| `UNG` | 4910 | 4910 | 0 | 0 | 0 | 0.2485 (2026-02-02) | 6498.5601 | 9.9700 |
| `GLD` | 5515 | 5515 | 0 | 0 | 0 | 0.1129 (2008-09-17) | 44.3800 | 378.9500 |

No missing price, no duplicate timestamp and no non-positive close in any of the four files, and no one-day move above 25 % in any series: the upstream panel is **continuous** (a split discontinuity would appear as a ~90 % one-day move, and none is present).

## 3. Agreement with the committed cache

| Symbol | Cached range | Upstream range | Overlap sessions | Identical closes | Max abs. difference | Sessions before the cached start |
|---|---|---|---|---|---|---|
| `DBC` | 2006-02-06 .. 2026-10-08 | - .. - | 5201 | 5201 | 0.000000000 | 0 |
| `BNO` | 2015-01-02 .. 2026-10-15 | 2010-06-02 .. 2014-12-31 | 2964 | 2964 | 0.000000000 | 1155 |
| `UNG` | 2015-01-02 .. 2026-10-15 | 2007-04-18 .. 2014-12-31 | 2964 | 2964 | 0.000000000 | 1942 |
| `GLD` | 2004-11-18 .. 2026-10-19 | - .. - | 5513 | 5513 | 0.000000000 | 0 |

On every session the upstream history and the committed cache overlap, the closes are **identical** (maximum absolute difference 0). The upstream history therefore *extends* the committed cache rather than contradicting it, and the cached start of 2015-01-02 is confirmed to be a **fetch window** rather than instrument history: `BNO` incepts at 2010-06-02 and `UNG` at 2007-04-18 upstream, while `DBC` and `GLD` are already complete in the cache.

## 4. The data gate

The pre-registered gate (`config/commoditytrend_001.yaml`, section `data_gate`): the frozen **10y train / 12m test / 6m step** design with a 21-day purge must support at least **10 folds**, which needs `2520 + 252 + (folds-1)*126` = **3906 business days**, i.e. a common inception on or before **2011-10-20**.

| Quantity | Value |
|---|---|
| Common inception | **2010-06-02** |
| Common end | 2026-10-21 |
| Business days available | **4276** |
| Business days required for 10 folds | 3906 |
| Common-inception deadline | 2011-10-20 |
| Folds on the business-day calendar | **12** |
| Folds on the traded-session calendar | **11** |
| Folds required | 10 |
| **Gate verdict** | **PASS** (the candidate's block is lifted as far as *data readiness* is concerned) |

Both calendars are reported because the pre-registered gate is stated in business days while the panel is a set of trading sessions: the business-day count is the gate's own convention, the traded-session count is the stricter one, and the gate passes on both.

### 4.1 The folds the frozen design produces

| Fold | Train (business-day calendar) | Test | Train (session calendar) | Test |
|---|---|---|---|---|
| 1 | 2010-06-02 .. 2020-01-28 | 2020-02-27 .. 2021-02-12 | 2010-06-02 .. 2020-06-04 | 2020-07-07 .. 2021-07-06 |
| 2 | 2010-11-25 .. 2020-07-22 | 2020-08-21 .. 2021-08-09 | 2010-11-30 .. 2020-12-02 | 2021-01-05 .. 2022-01-03 |
| 3 | 2011-05-20 .. 2021-01-14 | 2021-02-15 .. 2022-02-01 | 2011-06-01 .. 2021-06-04 | 2021-07-07 .. 2022-07-06 |
| 4 | 2011-11-14 .. 2021-07-09 | 2021-08-10 .. 2022-07-27 | 2011-11-29 .. 2021-12-02 | 2022-01-04 .. 2023-01-04 |
| 5 | 2012-05-08 .. 2022-01-03 | 2022-02-02 .. 2023-01-19 | 2012-05-31 .. 2022-06-03 | 2022-07-07 .. 2023-07-07 |
| 6 | 2012-10-31 .. 2022-06-28 | 2022-07-28 .. 2023-07-14 | 2012-11-30 .. 2022-12-02 | 2023-01-05 .. 2024-01-05 |
| 7 | 2013-04-25 .. 2022-12-21 | 2023-01-20 .. 2024-01-08 | 2013-06-04 .. 2023-06-06 | 2023-07-10 .. 2024-07-09 |
| 8 | 2013-10-18 .. 2023-06-15 | 2023-07-17 .. 2024-07-02 | 2013-12-02 .. 2023-12-05 | 2024-01-08 .. 2025-01-07 |
| 9 | 2014-04-14 .. 2023-12-08 | 2024-01-09 .. 2024-12-25 | 2014-06-04 .. 2024-06-06 | 2024-07-10 .. 2025-07-11 |
| 10 | 2014-10-07 .. 2024-06-03 | 2024-07-03 .. 2025-06-19 | 2014-12-02 .. 2024-12-05 | 2025-01-08 .. 2026-01-09 |
| 11 | 2015-04-01 .. 2024-11-26 | 2024-12-26 .. 2025-12-12 | 2015-06-04 .. 2025-06-10 | 2025-07-14 .. 2026-07-14 |
| 12 | 2015-09-24 .. 2025-05-21 | 2025-06-20 .. 2026-06-08 | - | - |

The design yields **12 folds** on the business-day calendar and **11 folds** on the traded-session calendar, against the **10** the gate requires.

## 5. What this does and does not change

- **No trading verdict is published.** The gate is a *block*, not a verdict: the candidate's own falsification conditions (walk-forward Sharpe, benchmark-relative excess CI, cost hurdle, fold/trade gate, post-2010 sub-period, expense-ratio band) are untouched and unmeasured here.
- **The committed cache is untouched.** `data/` and `config/` are byte-identical before and after the run; the extended panel exists only in the scratch directory. Committing it is a separate, explicit step.
- **The candidate's published prior evidence is unchanged.** The two-asset screen on `{DBC, GLD}` (net benchmark-relative excess -0.5304 %/yr, net Sharpe 0.4041 against the benchmark's 0.4580) remains the prior the four-asset evaluation must publish its own numbers beside. A longer sample and a wider universe are *not* new evidence in the candidate's favour: they add two instruments whose individual decompositions were negative in the screen.
- **The next step is not the evaluation.** The evaluation needs the extended panel in the committed cache, under the repository's own fetcher, with the overlap verified byte-identical; only then does the frozen design run.

## 6. Internal checks

| Check | Result | Detail |
|---|---|---|
| `panel_complete` | PASS | 4/4 instruments measured |
| `no_missing_prices` | PASS | total missing prices: 0 |
| `no_duplicate_timestamps` | PASS | total duplicate timestamps: 0 |
| `no_non_positive_prices` | PASS | total non-positive prices: 0 |
| `price_series_continuous` | PASS | largest one-day move per instrument: DBC 0.0794 (2022-03-09), BNO 0.2191 (2020-03-09), UNG 0.2485 (2026-02-02), GLD 0.1129 (2008-09-17) |
| `overlap_identical_to_committed_cache` | PASS | DBC 5201/5201 identical; BNO 2964/2964 identical; UNG 2964/2964 identical; GLD 5513/5513 identical |
| `upstream_extends_the_committed_cache` | PASS | DBC +0 sessions (-..-); BNO +1155 sessions (2010-06-02..2014-12-31); UNG +1942 sessions (2007-04-18..2014-12-31); GLD +0 sessions (-..-) |
| `gate_folds_business_day_calendar` | PASS | 12 folds on the business-day calendar (required 10) |
| `gate_folds_session_calendar` | PASS | 11 folds on the traded-session calendar (required 10) |
| `gate_common_inception` | PASS | common inception 2010-06-02 (deadline 2011-10-20) |
| `gate_business_days` | PASS | 4276 business days available, 3906 required for 10 folds |
| `data_unchanged` | PASS | every file under data/ is byte-identical after the run |
| `config_unchanged` | PASS | every file under config/ is byte-identical after the run |

## 7. Reproduction

```bash
python research/commodity_data_gate_fetch.py
python research/commodity_data_gate_001.py
python -m pytest -q tests/test_commodity_data_gate_001.py
git status --porcelain data/ config/
```
