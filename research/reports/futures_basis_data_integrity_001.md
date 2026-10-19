# Futures Basis / Roll Yield — Data Integrity Record (Cycle 883)

**Generated:** 2026-10-19
**Candidate:** shortlist rank 7 — Commodity/rate futures basis and roll yield (`futuresbasis_001`)
**Status:** Blocked by data/infrastructure — front-month series cached; point-in-time roll NOT constructible from available data

## 1. Purpose

Cycle 883's first (hard) gate is data readiness and integrity for shortlist rank 7. This record documents:

* the front-month futures series that *are* available in the repository cache,
* their coverage, gaps, duplicate dates, and the aligned frame's content hash,
* whether a **point-in-time roll** can be constructed from what is available, and
* the roll transaction cost that the construction actually pays (or an explicit statement that it cannot be quantified).

The known trap addressed explicitly: a backtest on a *spliced* front-month (continuous) series silently embeds the roll at an unobservable price and therefore **understates the roll cost and misstates the roll yield**. The construction must either pay the roll at observable prices or state plainly that it cannot. This record states plainly that it **cannot**.

## 2. Data source and fetch

* **Source:** Yahoo Finance (`yfinance` 1.7.0), free, public, no credentials.
* **Fetcher reused:** `src/data/yfinance_fetcher.py` (`YFinanceFetcher`, `auto_adjust=False`).
* **Symbols (continuous front month):** `CL=F` (crude oil), `NG=F` (natural gas), `GC=F` (gold), `ZB=F` (US Treasury bond).
* **Cached as (safe filenames):** `data/raw/CL-F.parquet`, `data/raw/NG-F.parquet`, `data/raw/GC-F.parquet`, `data/raw/ZB-F.parquet`.
* **Requested range:** 2015-01-01 .. 2026-10-16 (inclusive).
* **No forward-looking calls:** yfinance only ever returns data up to the requested end date; the fetcher performs no look-ahead.

## 3. Coverage, gaps, duplicates

| Stored symbol | Yahoo symbol | Sessions | Start | End | Missing `Close` | Duplicate dates | First close | Last close |
|---|---|---:|---|---|---:|---:|---:|---:|
| `CL-F` | `CL=F` | 2,964 | 2015-01-02 | 2026-10-15 | 0 | 0 | 52.6900 | 97.9700 |
| `NG-F` | `NG=F` | 2,965 | 2015-01-02 | 2026-10-15 | 0 | 0 | 3.0030 | 3.2360 |
| `GC-F` | `GC=F` | 2,964 | 2015-01-02 | 2026-10-15 | 0 | 0 | 1186.0000 | 4170.1001 |
| `ZB-F` | `ZB=F` | 2,964 | 2015-01-02 | 2026-10-15 | 0 | 0 | 145.5000 | 105.4375 |

* Union calendar (trading days only, weekdays): 2,965 sessions, 2015-01-02 .. 2026-10-15.
* Every series has data on every session of the union calendar after forward-fill; **0 missing after forward-fill**, **0 duplicate dates** in every raw file.
* No gaps in any series over the full window.

## 4. Aligned frame and content hash

The four series were aligned onto the union trading-day calendar and forward-filled (no missing values remain after alignment). The aligned frame `data/processed`-free in-memory frame:

* Columns: `CL-F`, `NG-F`, `GC-F`, `ZB-F`
* Rows: 2,965 (2015-01-02 .. 2026-10-15)
* **Content hash (SHA-256 of the aligned frame's CSV):** `f898cd42f5e42a29b50363258863f563daadb220c0896ecbef133b9b26446f9c`
* Individual file SHA-256 prefixes: CL-F `5d7ec126`, NG-F `6d480ef7`, GC-F `2dc89075`, ZB-F `26f740c3`.

## 5. Roll dates detected in the data

**None detected, and none can be detected reliably.**

A point-in-time roll requires knowing, at each date, which contract is the front month and the observable close price of *both* the expiring contract and the next contract on the roll date. Yahoo Finance continuous front-month symbols (`CL=F`, ...) return a single spliced series. They do **not** expose:

* the individual contract leg prices,
* the roll date yfinance used,
* the roll spread (difference between expiring and next contract) at the roll.

I probed eleven individual crude contract legs (`CLZ24`, `CLF25`, `CLG25`, `CLH25`, `CLJ25`, `CLK25`, `CLN25`, `CLQ25`, `CLU25`, `CLX25`, `CLZ25`): **all returned 404 "Quote not found" / "possibly delisted"**. No individual contract leg is available through the repository's supported fetcher.

Consequently:
* **Roll dates:** not detectable from the continuous series (the series shows normal crude volatility, 39–96 moves > 2.5% per year, with no clean monthly roll signature distinguishable from price moves).
* **Roll prices / roll spread:** unobservable.
* **Roll transaction cost actually paid:** cannot be quantified.

## 6. Point-in-time roll constructible?

**No.**

A point-in-time front-month roll that pays the roll at observable prices requires individual contract legs with observable closes on both sides of the roll. Those legs are not available from Yahoo Finance (the repository's supported, free data source), and no alternative free source is configured or permitted by this cycle's scope boundaries (no new dependencies, services, or paid data).

Therefore a backtest on the cached continuous front-month series would be a **spliced series** that silently embeds the roll at an unobservable price — exactly the trap this gate is designed to catch. It **understates the roll cost and misstates the roll yield**, so it must not be used as a valid test of the basis/roll-yield mechanism.

## 7. Decision

| Question | Answer |
|---|---|
| Front-month series fetchable? | **Yes** — `CL=F`, `NG=F`, `GC=F`, `ZB=F` cached (2015-01-02 .. 2026-10-15, complete). |
| Individual contract legs available? | **No** — all probed legs 404 / delisted. |
| Roll dates and roll prices observable? | **No**. |
| Point-in-time roll constructible? | **No**. |
| Roll cost quantifiable? | **No**. |
| Valid roll-yield backtest possible this cycle? | **No** — **Blocked by data/infrastructure**. |

## 8. What would unblock the cycle

A source of individual futures contract legs (front month + at least the next contract) with observable daily closes and volume/open-interest sufficient to detect the front-month roll point-in-time — e.g. a vendor feed or exchange-published settlement data — together with a documented roll rule (roll date and roll price convention). With that, the cycle can:

1. construct the point-in-time front-month series,
2. detect roll dates and the roll cost actually paid at observable closes,
3. extend `research/cost_admissibility_screen.py` to measure the roll-yield baseline,
4. reach a cost admissibility / falsification decision for rank 7.

## 9. Reproduction

The four raw parquet files are committed under `data/raw/`. The aligned frame can be rebuilt from them with the union-calendar / forward-fill construction above; its content hash is `f898cd42f5e42a29b50363258863f563daadb220c0896ecbef133b9b26446f9c`. No file under `data/` or `config/` is modified by the cost screen (which is read-only); this record is the only change to the research record for this gate.

## 10. Addendum — Cycle 884: the roll *dates* are detectable after all

**This addendum corrects §5 of this record, which is left unchanged above as the
Cycle 883 statement.** Cycle 883 concluded that no roll date could be detected from the
continuous series ("the series shows normal crude volatility, 39-96 moves > 2.5% per year,
with no clean monthly roll signature distinguishable from price moves"). That conclusion
was **wrong about the dates**, and it is corrected here.

The cached series carry a `Volume` column, and that column is the **front contract's**
volume: at a roll the contract behind the series is replaced, so the volume identity
changes with it. The expiring contract's volume runs off as delivery approaches and the
new front's volume resumes at its typical level, which leaves a **deterministic,
point-in-time signature**:

| Series | Detected rolls | Rolls/yr | Modal spacing | Contract cycle |
|---|---:|---:|---:|---|
| `CL-F` | 127 | 10.98 | 29 d | monthly |
| `NG-F` | 125 | 10.98 | 30 d | monthly |
| `GC-F` | 72 | 6.34 | 63 d | bi-monthly |
| `ZB-F` | 62 | 5.39 | 91 d | quarterly |

The one roll that could be verified independently (Yahoo's per-contract volume and price
series for the currently listed Nov-2026/Dec-2026 contracts show that the cached chain
held the Nov-2026 contract from **2026-09-23** and the Dec-2026 contract from 2026-10-19)
is detected in the committed cache by the volume rule alone, with no per-contract data.

**What did not change:** the roll *prices* — the two leg closes at the roll — are still
unobservable, so the roll spread and the roll cost actually paid still cannot be
quantified, the candidate is still **Blocked by data/infrastructure**, and no spliced
series was back-tested. Nine further source classes were probed in Cycle 884 and none
serves individual contract legs.

Tool: `research/futures_roll_visibility.py` (read-only, offline, exit 0 with
`OVERALL: PASS`); report: `research/reports/futures_roll_visibility_001.md`; decision
record: `research/experiments/futuresbasis_001.md`.

---
*The shortlist row for rank 7 remains "Blocked by data" (unchanged verdict); see `research/reports/opportunity_shortlist.md` and the experiment record `research/experiments/futuresbasis_001.md`. No row is re-scored or re-ranked.*
