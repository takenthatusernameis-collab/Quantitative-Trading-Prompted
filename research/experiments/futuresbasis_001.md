# Experiment 001 - Futures Basis / Roll Yield Data Gate (`futuresbasis_001`)

## Hypothesis reference

`research/hypotheses/futuresbasis_001.md` (v001 pre-registered 2026-10-19 for Cycle 883;
v002 data block 2026-10-19; v003 Cycle 884 data-fact correction). Parent: shortlist rank 7
in `research/reports/opportunity_shortlist.md` ("Commodity/rate futures basis and roll yield",
overall 21/35, verdict Blocked by data).

This experiment is **not a backtest** and **not a candidate measurement**. It is the data
gate for shortlist rank 7, run twice:

* **Cycle 883** asked whether the front-month series can be cached and whether a
  point-in-time roll can be constructed from what is available.
* **Cycle 884** asked the same question against a *materially different* set of sources,
  and re-tested Cycle 883's own claim that the roll dates are undetectable.

## Decision label

**Blocked by data/infrastructure** — shortlist rank 7 (`futuresbasis_001`), with a
**narrower** block than Cycle 883 recorded:

| Component | Cycle 883 | Cycle 884 |
|---|---|---|
| Front-month series cached | Yes | Yes (unchanged) |
| **Roll dates** observable in the cache | **No** (claimed) | **Yes** — the volume signature of the front contract's run-off and recovery; 127/125/72/62 events for CL/NG/GC/ZB, modal spacing 29/30/63/91 days, matching each product's contract cycle; the one externally verified roll (2026-09-23) is detected in the committed cache |
| **Roll prices** (the two leg closes at the roll) observable | No | **No** — nine source classes probed, none serves individual contract legs |
| **Roll cost actually paid** observable | No | **No** — it is the roll spread, which needs the leg closes |
| Valid roll-yield backtest possible | No | **No** |

The candidate is therefore **still blocked**, but the block is now a *price* block, not a
*date* block, and the false claim "the roll dates are not detectable" is corrected.

## Data used

| Item | Value |
|---|---|
| Source | Yahoo Finance (`yfinance` 1.7.0 / the Yahoo chart API), free/public, `auto_adjust=False` |
| Fetcher reused | `src/data/yfinance_fetcher.py` (`YFinanceFetcher`); no new dependencies, no paid data |
| Symbols (continuous front month) | `CL=F` (crude), `NG=F` (natural gas), `GC=F` (gold), `ZB=F` (US Treasury bond) |
| Cached as | `data/raw/CL-F.parquet`, `data/raw/NG-F.parquet`, `data/raw/GC-F.parquet`, `data/raw/ZB-F.parquet` |
| Frequency | daily, timezone-aware UTC index, trading days only |
| Requested range | 2015-01-01 .. 2026-10-16 (inclusive) |
| Actual range | 2015-01-02 .. 2026-10-15 (2,964-2,965 sessions each) |
| Forward-looking calls | none (yfinance only ever returns up to the requested end date) |
| Additional symbol classes probed (not cached) | Yahoo per-contract symbols `CLZ26.NYM`, `CLX26.NYM`, `CLZ27.NYM`, `CLJ27.NYM`, `MCLZ26.NYM`, `MCLX26.NYM` |

## Point-in-time treatment

* The committed caches are read-only and unchanged by this cycle (`git status --porcelain
  data/ config/` empty; the diagnostic fingerprints all 1,848 files under `data/` and
  `config/` before and after its run and compares them).
* The volume-signature detector is **point-in-time by construction**: the trailing median
  volume is shifted by one session, so a session's ratio never depends on the session
  itself, and the rule never looks further ahead than the session being classified.
* The per-contract cross-check (§"What was tried" item 2) uses only *currently listed*
  contracts and only to identify **which contract the cached chain was holding on a past
  date** — a composition question, not a price question. No value of the cross-check enters
  the detector or the reported numbers.

## What was tried

1. **Cycle 883 (retained).** Downloaded the four continuous front-month series and probed
   eleven individual crude legs (`CLZ24` .. `CLZ25`) through yfinance: **all returned 404
   "Quote not found" / "possibly delisted"**. Attempted to detect roll dates from the
   continuous series: no signature was found, and the record stated "no clean, detectable
   monthly roll signature".
2. **Cycle 884, new: the cached `Volume` column.** The cached series carry a `Volume`
   column that is the **front contract's** volume. At a roll the front contract is replaced,
   so the volume identity changes with it: the expiring contract's volume runs off and the
   new front's volume resumes. That signature **is** detectable, and the detector's modal
   spacing reproduces each product's contract cycle exactly (CL 29 d, NG 30 d, GC 63 d,
   ZB 91 d). **The Cycle 883 claim is falsified and corrected.**
3. **Cycle 884, new: independent verification of the most recent roll.** Yahoo serves
   per-contract symbols for the *currently listed* contracts. Comparing their volume
   columns with the cached chain's volume column gives a contract-identity check that does
   not use the detector:

   | Date | cached chain volume | per-contract volume | reading |
   |---|---:|---:|---|
   | 2026-10-16 | 222,965 | `CLX26.NYM` (Nov-2026) = 222,965; `CLZ26.NYM` (Dec-2026) = 249,739 | the chain is the Nov-2026 contract |
   | 2026-10-19 | 1,724 | `CLZ26.NYM` = 1,724; `CLX26.NYM` = 11 | the chain has rolled to the Dec-2026 contract |

   The per-contract *price* series additionally equals the chain exactly over
   2026-09-23 .. 2026-10-16, so the chain held the **Nov-2026** contract from 2026-09-23
   and the **Oct-2026** contract up to 2026-09-22. The roll date is therefore
   **2026-09-23** — the event the detector finds in the committed cache, from the cache
   alone.
4. **Cycle 884, new: nine source classes for the individual legs** (all different from
   the yfinance route of item 1), each with its verbatim outcome:

   | Source class | Endpoint | Outcome |
   |---|---|---|
   | Yahoo per-contract symbols, suffix format | `query1.finance.yahoo.com/v8/finance/chart/CLZ26.NYM` | HTTP 200 with 1,260 daily bars over five years — a span a single contract cannot have; the series is an alias of the continuous chain, not the contract's own history. Expired legs (`CLZ24.NYM`, `CLZ25.NYM`, `CLX25.NYM`) → HTTP 404 |
   | Nasdaq Data Link (Quandl) CHRIS `CL1`/`CL2` | `data.nasdaq.com/api/v3/datasets/CHRIS/CME_CL1.json` | HTTP 403 — Cloudflare browser-verification challenge (.json and .csv) |
   | CME Group daily settlement service | `cmegroup.com/CmeWS/mvc/Settlements/Futures/Settlements/425/FUT` | HTTP 403 — "This IP address is blocked due to suspected web scraping activity associated with it on this CMEgroup.com page" |
   | WSJ market-data contract history | `wsj.com/market-data/quotes/futures/CLZ24/historical-prices/download` | HTTP 401 — bot-protection interstitial |
   | Barchart contract time series | `barchart.com/proxies/timeseries/queryeod.ashx?symbol=CL*1` | HTTP 202 AWS WAF challenge on the page, HTTP 403 "Forbidden" on the proxy |
   | Stooq | `stooq.com/q/d/l/?s=cl.f&i=d` | JS proof-of-work challenge **solved** (SHA-256 nonce, `/__verify` → "ok"), the quote page then serves, but the CSV data endpoint answers HTTP 200 with an empty body ("Access denied" on other symbols) |
   | FT Markets futures tearsheets | `markets.ft.com/data/futures/tearsheet/summary?s=CLc1` | HTTP 200 but the response is the generic "Error"/equities page |
   | Investing.com financial-data API | `api.investing.com/api/financialdata/historical/8830` | HTTP 403 — Cloudflare "Just a moment" |
   | Yahoo symbol search (leg-universe discovery) | `query2.finance.yahoo.com/v1/finance/search?q=CLZ24` | HTTP 200, `count: 0` — no per-contract leg universe to enumerate |

5. **Cycle 884: no backtest was executed.** No spliced series was written to the
   repository, no candidate weights were built, and the cost-admissibility screen was
   **not** extended to this candidate, because an honest gross-return + turnover pair for
   a *roll* still cannot be built without the leg prices.
6. **Cycle 884: the aggregate roll effect that the cache *can* measure.** A front-month
   chain's total return equals the underlying's total return plus the accumulated roll
   effects, so the chain-minus-spot difference over the sample is the accumulated roll
   effect. The committed cache has exactly one spot proxy for a cached futures leg — `GLD`,
   a physical gold trust — so this is measurable for the **gold leg only**:
   chain (GC-F) annualized **+11.29%** vs proxy (GLD) **+10.85%**, i.e. an annualized roll
   effect of **+0.44%/yr** (fee-adjusted +0.84%/yr), with a 126-day block-bootstrap 95% CI
   of **[-1.87%, +3.05%]** (2,000 draws, seed 20261019). The interval contains zero: the
   accumulated roll effect of the gold leg is **not measurable** with the committed cache,
   and its point estimate is far below the 3 bp/unit model's 0.72%/yr charge for a monthly
   rolling position. **This is an exploratory measurement with a stated band, not an observed
   roll cost, and it does not decide the candidate** — it is recorded because it bounds how
   much the mechanism could possibly be worth.

## Configuration

| Parameter | Value | Where |
|---|---|---|
| Volume-ratio window | 60 sessions (median, shifted one session) | `research/futures_roll_visibility.py: VOLUME_RATIO_WINDOW` |
| Volume-ratio minimum periods | 20 | `VOLUME_RATIO_MIN_PERIODS` |
| Run-off threshold | ratio < 0.55 | `TROUGH_RATIO` |
| Expiry threshold | ratio >= 1.00 and >= 0.70 for the next 4 sessions | `RECOVERY_RATIO`, `HOLD_RATIO`, `HOLD_SESSIONS` |
| Maximum look-ahead | 8 sessions | `MAX_LOOKAHEAD_SESSIONS` |
| Cycle windows (exogenous) | CL/NG 25-35 d, GC 50-70 d, ZB 80-100 d | `CYCLE_WINDOW_DAYS` |
| Pass criteria | >= 40 events per series, modal spacing inside the cycle window, the verified 2026-09 roll detected, `data/`+`config/` untouched | `MIN_EVENTS_PER_SERIES`, §1 of the report |
| Walk-forward splits | **not applicable** — no backtest | — |
| Number of trials | **1** (one detector rule, one threshold set; no parameter search) | — |

## Result / numbers

| Series | Product | Sessions | Detected rolls | Rolls/yr | Modal spacing | Median spacing | Cycle | Spacings inside window |
|---|---|---:|---:|---:|---:|---:|---|---:|
| `CL-F` | WTI crude (CL=F) | 2,964 | 127 | 10.98 | 29 d (x16) | 30 d | monthly | 64.3% |
| `NG-F` | Henry Hub gas (NG=F) | 2,965 | 125 | 10.98 | 30 d (x14) | 30 d | monthly | 66.1% |
| `GC-F` | COMEX gold (GC=F) | 2,964 | 72 | 6.34 | 63 d (x6) | 56 d | bi-monthly | 35.2% |
| `ZB-F` | UST bond (ZB=F) | 2,964 | 62 | 5.39 | 91 d (x6) | 70 d | quarterly | 29.5% |

* Ground truth check: the cached `CL-F` series yields **expiry 2026-09-22, roll
  2026-09-23** — the event verified independently against Yahoo's per-contract volume and
  price series (item 3).
* The detector's recall is **imperfect**: it also fires on some off-cycle contract months
  and misses others, which is why the "spacings inside window" share is reported as a
  descriptive statistic and the *modal spacing* is the falsification test. The detector is
  a **visibility diagnostic**, not an exhaustive roll calendar.

| Question | Answer |
|---|---|
| Front-month series fetchable? | **Yes** — four series cached, complete |
| **Roll dates observable in the cache?** | **Yes** — the front contract's volume signature; 386 detected rolls across the four series; the verified 2026-09 roll is among them |
| Individual contract legs available? | **No** — nine source classes probed; expired legs 404, currently listed legs are chain aliases |
| Roll prices / roll spread observable? | **No** |
| Roll cost quantifiable? | **No** |
| Aggregate roll effect measurable (gold leg, via `GLD`)? | **Measured but not significant** — +0.44%/yr, 95% CI [-1.87%, +3.05%] (exploratory) |
| Honest roll-yield backtest possible this cycle? | **No** |
| Decision label | **Blocked by data/infrastructure** (roll-price block) |

## What would unblock the cycle

A source of individual futures contract legs (front month **and** next contract) with
observable daily closes for the contract months of the *past* — i.e. a source that keeps
expired contracts, or a licensed exchange feed. With that, Cycle 885 can:

1. take the roll dates that are now observable in the committed cache,
2. price the roll at the two observable leg closes,
3. extend `research/cost_admissibility_screen.py` (not a parallel tool) with the
   roll-yield baseline, the roll turnover and the gate headroom, without moving any of
   the six existing candidates' published numbers, and
4. reach the cost-admissibility / falsification decision for rank 7.

A second, weaker unblock is possible **without** new data: estimate the roll spread from
the observable chain plus an observable spot proxy (the cached `GLD` series is a physical
gold tracker, so the gold *spot* move is observable), state the estimator's assumption
explicitly, and make the decision only if it is robust across the estimation band. That
route is *not* "the roll cost actually paid at observable closes", so it would have to be
labelled as an estimate, and it is the fallback if no leg source is found.

## Reproduction

```bash
python research/futures_roll_visibility.py                    # OVERALL: PASS, exit 0
python -m pytest tests/test_futures_roll_visibility.py -q       # 16 passed
python research/cost_admissibility_screen.py                   # OVERALL: PASS (six candidates unchanged)
python -m pytest -q                                            # full offline suite
python research/go_no_go_evaluation.py                         # NO-GO, side_effect_free: True
git status --porcelain data/ config/                           # empty
```

The per-contract cross-check of item 3 needs network access and is therefore **not** part
of the offline script. It is reproduced with:

```bash
python - <<'PY'
import json, urllib.parse, urllib.request
H = {"User-Agent": "Mozilla/5.0"}
def series(sym):
    u = ("https://query1.finance.yahoo.com/v8/finance/chart/"
         + urllib.parse.quote(sym) + "?range=5y&interval=1d")
    j = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=30))
    r = j["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    return list(zip(r["timestamp"], q["close"], q["volume"]))
for sym in ["CL=F", "CLX26.NYM", "CLZ26.NYM"]:
    rows = series(sym)
    print(sym, rows[-3:])
PY
```

## Risk of misreading

* The volume signature identifies **when** the front month changed, not **what** was paid.
  The roll spread and the roll cost actually paid remain unobservable, so no roll-yield
  return series was constructed and no backtest was run.
* The detector's recall is imperfect (see above). It must not be used as an exhaustive
  roll calendar for cost accounting; the next cycle must verify each roll it uses.
* The per-contract Yahoo series are chain aliases, not leg histories. Using them as legs
  would silently substitute the continuous series for the leg and reproduce exactly the
  trap this gate exists to catch.
