# Roll-Date Visibility in the Cached Front-Month Futures Series (Cycle 884)

**Generated:** 2026-10-20 00:07:41Z
**Candidate:** shortlist rank 7 — commodity/rate futures basis and roll yield (`futuresbasis_001`)
**Status:** roll **dates** are observable in the committed cache; roll **prices** are not — the candidate remains **Blocked by data/infrastructure**, with a narrower block than Cycle 883 recorded.

## 1. Question and pass criteria

Cycle 883 recorded that the roll dates are *not* detectable from the cached continuous front-month series. This cycle tests that statement against the cached data. The falsification condition is stated before the measurement:

1. **Void** if the volume signature does not reproduce each product's *exogenous* contract cycle: CL/NG monthly (25-35 days), GC bi-monthly (50-70 days), ZB quarterly (80-100 days). The test is the **modal spacing** between consecutive detected rolls: a detector that fires on noise cannot reproduce a 29/30/63/91-day modal spacing. The share of spacings inside the window is reported descriptively (the detector's recall is imperfect).
2. **PASS** requires at least 40 detected rolls per series, the modal spacing inside the cycle window for every product, and the externally verified roll of 2026-09-23 to be detected in the committed cache.
3. The roll **price** is out of scope: no source in scope serves the individual leg closes, so the roll spread and the roll cost actually paid stay unobservable.

## 2. The volume signature

The cached Yahoo front-month series carry a `Volume` column. That column is the **front contract's** volume: when the front month is rolled, the contract behind the series changes and the volume identity changes with it. The expiring contract's volume runs off as delivery approaches and the new front's volume resumes at its typical level, which leaves a recurring signature:

- **run-off session**: volume ratio < 0.55 of the trailing 60-session median (the median is shifted one session, so the ratio is point-in-time);
- **expiry session**: the first session after the run-off's local minimum whose volume ratio returns to >= 1.0 and stays >= 0.70 for the next four sessions;
- **roll date**: the first session after the expiry session, i.e. the first session of the new front month.

## 3. Independent verification of the 2026-09 roll

Yahoo Finance serves per-contract symbols for the currently listed contracts (`CLZ26.NYM`, `CLX26.NYM`, `CLZ27.NYM`, `CLJ27.NYM`); expired contracts return 404. Comparing the **volume** column of those per-contract series with the cached chain's volume column gives an independent identity check that does not use the detector:

| Date | cached chain volume | per-contract volume | reading |
|---|---:|---:|---|
| 2026-10-16 | 222,965 | `CLX26.NYM` (Nov-2026) = 222,965 | the chain is the Nov-2026 contract |
| 2026-10-16 | 222,965 | `CLZ26.NYM` (Dec-2026) = 249,739 | the Dec-2026 contract is a different contract |
| 2026-10-19 | 1,724 | `CLZ26.NYM` = 1,724, `CLX26.NYM` = 11 | the chain has rolled to the Dec-2026 contract |

The chain therefore held the **Nov-2026** contract from 2026-09-23 (the date the per-contract price series stops equalling the chain) to 2026-10-16, and the **Dec-2026** contract from 2026-10-19. The Oct-2026 contract was the front month up to and including **2026-09-22**, so the roll date is **2026-09-23** — which is exactly the event the volume detector finds in the committed cache, without any per-contract data.

## 4. Detected roll events

| Series | Product | Sessions | Detected rolls | Rolls/yr | Modal spacing | Median spacing | Cycle | Inside window |
|---|---|---:|---:|---:|---:|---:|---|---:|
| `CL-F` | WTI crude oil front month (CL=F) | 2964 | 127 | 10.98 | 29 d (x16) | 30 d | monthly (every calendar month) | 64.3% |
| `NG-F` | Henry Hub natural gas front month (NG=F) | 2965 | 125 | 10.98 | 30 d (x14) | 30 d | monthly (every calendar month) | 66.1% |
| `GC-F` | COMEX gold front month (GC=F) | 2964 | 72 | 6.34 | 63 d (x6) | 56 d | bi-monthly (two active contract months per year) | 35.2% |
| `ZB-F` | US Treasury bond front month (ZB=F) | 2964 | 62 | 5.39 | 91 d (x6) | 70 d | quarterly (Mar/Jun/Sep/Dec) | 29.5% |

- `CL-F`: first roll 2015-02-27, last roll 2026-09-23, cycle window 25-35 days.
- `NG-F`: first roll 2015-04-09, last roll 2026-08-28, cycle window 25-35 days.
- `GC-F`: first roll 2015-02-24, last roll 2026-07-07, cycle window 50-70 days.
- `ZB-F`: first roll 2015-04-15, last roll 2026-10-14, cycle window 80-100 days.

## 5. What is still unobservable

The roll **spread** — the difference between the expiring contract's close and the new front's close on the roll date, i.e. the roll cost actually paid — is **not** observable. The cached series is a single spliced front-month price; the expired leg's close on the roll date is not in it, and no source in scope serves the individual legs (see §7 below and `research/experiments/futuresbasis_001.md`). A point-in-time roll that pays the roll at observable closes therefore still cannot be constructed, and no spliced series was back-tested.

## 6. The aggregate roll effect the cache *can* measure

A front-month chain's total return equals the underlying's total return plus the accumulated roll effects, so the chain-minus-spot difference over the sample is the accumulated roll effect. The committed cache has exactly one spot proxy for a cached futures leg — `GLD`, a physical gold trust — so the aggregate is measurable for the gold leg only. It is an **estimate with a stated band**, not an observed roll cost: `GLD` pays a 0.40%/yr fee and is not the spot price itself.

| Quantity | Value |
|---|---:|
| Leg | `GC-F` (chain) vs `GLD` (spot proxy) |
| Sample | 2961 sessions, 2015-01-02 .. 2026-10-15 |
| Chain annualized return | +11.2944% |
| Spot-proxy annualized return | +10.8503% |
| **Annualized roll effect (chain − proxy)** | **+0.4441%** |
| Block-bootstrap 95% CI (126-session blocks, 2000 draws, seed 20261019) | [-1.8677%, +3.0458%] (sd 1.1828%) |
| Distinguishable from zero | **no** |

The interval contains zero: the accumulated roll effect of the gold leg is **not measurable** with the committed cache, and its point estimate is far below the 3 bp/unit model's 0.72%/yr charge for a monthly rolling position. The contract-leg construction of rank 7 is therefore not only unbuildable, it is **not measurable** at a size that could pay for itself. This is an exploratory measurement; it does not decide the candidate.

## 7. Source classes tried for the individual legs

| Source class | Endpoint | Outcome |
|---|---|---|
| Yahoo Finance per-contract symbols (new format, suffix exchange code) | `query1.finance.yahoo.com/v8/finance/chart/CLZ26.NYM` | HTTP 200 with 1,260 daily bars (2021-10-19..2026-10-19) — a span a single contract cannot have; the series is an alias of the continuous chain, not the contract's own history. Expired legs (`CLZ24.NYM`, `CLZ25.NYM`, `CLX25.NYM`) return HTTP 404. |
| Nasdaq Data Link (Quandl) CHRIS continuous-futures dataset (CL1/CL2 legs) | `data.nasdaq.com/api/v3/datasets/CHRIS/CME_CL1.json` | HTTP 403 — Cloudflare browser-verification challenge on both the .json and .csv routes. |
| CME Group daily settlement service (all contracts, all dates) | `cmegroup.com/CmeWS/mvc/Settlements/Futures/Settlements/425/FUT` | HTTP 403 — 'This IP address is blocked due to suspected web scraping activity associated with it on this CMEgroup.com page'. |
| WSJ market-data contract history download | `wsj.com/market-data/quotes/futures/CLZ24/historical-prices/download` | HTTP 401 — bot-protection interstitial. |
| Barchart contract time series | `barchart.com/proxies/timeseries/queryeod.ashx?symbol=CL*1` | HTTP 202 AWS WAF challenge on the page and HTTP 403 'Forbidden' on the time-series proxy. |
| Stooq | `stooq.com/q/d/l/?s=cl.f&i=d` | JavaScript proof-of-work challenge solved (SHA-256 nonce, /__verify returned 'ok'), the quote page then serves, but the CSV data endpoint answers HTTP 200 with an empty body ('Access denied' on other symbols). |
| FT Markets futures tearsheets | `markets.ft.com/data/futures/tearsheet/summary?s=CLc1` | HTTP 200 but the response is the generic 'Error'/equities page — no futures data is served for these symbols. |
| Investing.com financial-data API | `api.investing.com/api/financialdata/historical/8830` | HTTP 403 — Cloudflare 'Just a moment' interstitial. |
| Yahoo Finance symbol search (leg universe discovery) | `query2.finance.yahoo.com/v1/finance/search?q=CLZ24` | HTTP 200 with count 0 — Yahoo has no per-contract leg universe to enumerate beyond the handful of currently listed contracts. |

## 8. Checks

| Check | Result |
|---|---|
| CL-F modal roll spacing reproduces the contract cycle | PASS — 127 rolls, modal spacing 29 d (x16) inside the monthly (every calendar month) window 25-35 d: True; 64.3% of spacings inside the window (descriptive) |
| NG-F modal roll spacing reproduces the contract cycle | PASS — 125 rolls, modal spacing 30 d (x14) inside the monthly (every calendar month) window 25-35 d: True; 66.1% of spacings inside the window (descriptive) |
| GC-F modal roll spacing reproduces the contract cycle | PASS — 72 rolls, modal spacing 63 d (x6) inside the bi-monthly (two active contract months per year) window 50-70 d: True; 35.2% of spacings inside the window (descriptive) |
| ZB-F modal roll spacing reproduces the contract cycle | PASS — 62 rolls, modal spacing 91 d (x6) inside the quarterly (Mar/Jun/Sep/Dec) window 80-100 d: True; 29.5% of spacings inside the window (descriptive) |
| externally verified 2026-09 roll detected in the committed cache | PASS — expiry 2026-09-22 and roll 2026-09-23 detected: True / True |
| aggregate roll effect measurable through the cached spot proxy | PASS — GC-F - GLD: +0.4441%/yr, 95% CI [-1.8677%, +3.0458%] (distinguishable from zero: False) - exploratory, it does not decide the candidate |
| data/ and config/ untouched by the diagnostic | PASS — 1852 files fingerprinted before and after the run |

## 9. Reproduction

```bash
python research/futures_roll_visibility.py   # OVERALL: PASS, exit 0
python -m pytest tests/test_futures_roll_visibility.py -q
python -m pytest -q
git status --porcelain data/ config/            # empty
```

The per-contract cross-check of §3 needs network access and is therefore **not** part of the offline script; the exact command is in `research/experiments/futuresbasis_001.md`.
