# Experiment 001 - Futures Basis / Roll Yield Data Gate (`futuresbasis_001`)

## Hypothesis reference

`research/hypotheses/futuresbasis_001.md` (v001 pre-registered 2026-10-19 for Cycle 883;
v002 data block 2026-10-19). Parent: shortlist rank 7 in
`research/reports/opportunity_shortlist.md` ("Commodity/rate futures basis and roll yield",
overall 21/35, verdict Blocked by data).

This experiment is **not a backtest** and **not a candidate measurement**. It is the
Cycle 883 data-readiness gate: can the front-month futures series be cached with an
explicit, documented, point-in-time roll rule, and can the roll cost actually paid be
quantified? If not, the cycle records a "Blocked by data/infrastructure" decision and
does not back-test a spliced series (the explicit trap the gate is designed to catch).

## Decision label

**Blocked by data/infrastructure** — shortlist rank 7 (`futuresbasis_001`).

The front-month series *is* fetchable and cached, but no point-in-time roll can be
constructed from the available data, so the roll cost cannot be quantified and no valid
roll-yield backtest or cost-admissibility measurement exists this cycle.

## Data used

| Item | Value |
|---|---|
| Source | Yahoo Finance (`yfinance` 1.7.0), free/public, `auto_adjust=False`, `group_by='ticker'` |
| Fetcher reused | `src/data/yfinance_fetcher.py` (`YFinanceFetcher`); no new dependencies, no paid data |
| Symbols (continuous front month) | `CL=F` (crude), `NG=F` (natural gas), `GC=F` (gold), `ZB=F` (US Treasury bond) |
| Cached as | `data/raw/CL-F.parquet`, `data/raw/NG-F.parquet`, `data/raw/GC-F.parquet`, `data/raw/ZB-F.parquet` |
| Frequency | daily, timezone-aware UTC index, trading days only |
| Requested range | 2015-01-01 .. 2026-10-16 (inclusive) |
| Actual range | 2015-01-02 .. 2026-10-15 |
| Forward-looking calls | none (yfinance only ever returns up to the requested end date) |

## Point-in-time treatment

**No point-in-time information is used or claimed.** The continuous front-month series
is the only data available. The candidate's pre-registered entry/exit rules require
observable closes of *both* the expiring contract and the next contract on the roll date,
plus a detectable roll date. None of these is available:

* **Individual contract legs**: I probed eleven individual crude legs
  (`CLZ24`, `CLF25`, `CLG25`, `CLH25`, `CLJ25`, `CLK25`, `CLN25`, `CLQ25`, `CLU25`,
  `CLX25`, `CLZ25`) through yfinance; **all returned 404 "Quote not found" /
  "possibly delisted"**. No individual contract leg is available through the repository's
  supported fetcher, and no alternative free source is in scope.
* **Roll dates**: not detectable from the continuous series (normal crude volatility,
  39–96 moves > 2.5% per year, with no clean monthly roll signature distinguishable from
  price moves); yfinance does not expose the roll date it uses.
* **Roll prices / roll spread**: unobservable — the continuous series is a single spliced
  price and yfinance exposes neither the leg prices nor the roll spread.

## Data integrity record

| Measure | Value |
|---|---|
| Sessions per series | 2,964 (CL, GC, ZB) / 2,965 (NG) |
| Union calendar (trading days) | 2,965 sessions, 2015-01-02 .. 2026-10-15 |
| Missing `Close` per series | 0 (all four) |
| Duplicate dates per series | 0 (all four) |
| Missing after forward-fill on union | 0 |
| Aligned-frame content hash (SHA-256) | `f898cd42f5e42a29b50363258863f563daadb220c0896ecbef133b9b26446f9c` |
| File SHA-256 prefixes | CL-F `5d7ec126`, NG-F `6d480ef7`, GC-F `2dc89075`, ZB-F `26f740c3` |
| Integrity report | `research/reports/futures_basis_data_integrity_001.md` |

## What was tried

1. Downloaded all four continuous front-month series (`CL=F`, `NG=F`, `GC=F`, `ZB=F`)
   over 2015-01-01 .. 2026-10-16 — **succeeded**, all four cached complete.
2. Probed eleven individual crude contract legs for roll-leg prices — **all failed** (404 /
   delisted).
3. Attempted to detect roll dates from the continuous series — **no reliable signature**;
   roll dates and roll prices remain unobservable.

## Result / numbers

| Question | Answer |
|---|---|
| Front-month series fetchable? | **Yes** — four series cached, complete (0 missing closes, 0 duplicates) |
| Individual contract legs available? | **No** — all probed legs 404 / delisted |
| Roll dates and roll prices observable? | **No** |
| Point-in-time roll constructible? | **No** |
| Roll cost quantifiable? | **No** |
| Honest roll-yield backtest possible this cycle? | **No** |
| Decision label | **Blocked by data/infrastructure** |

## What would unblock the cycle

A source of individual futures contract legs (front month + next contract) with observable
daily closes and volume/open-interest sufficient to detect the front-month roll
point-in-time, plus a documented roll rule (roll date and roll price convention). With
that, Cycle 884 can:

1. construct the point-in-time front-month series,
2. detect roll dates and the roll cost actually paid at observable closes,
3. extend `research/cost_admissibility_screen.py` (not a parallel tool) to measure the
   roll-yield baseline,
4. reach a cost admissibility / falsification decision for rank 7.

## Reproduction

The four raw parquet files are committed under `data/raw/`. The aligned frame can be rebuilt
from them (union trading-day calendar, forward-fill); its content hash is
`f898cd42f5e42a29b50363258863f563daadb220c0896ecbef133b9b26446f9c`. The cost-admissibility
screen is **not** extended to this candidate this cycle: no honest gross-return + turnover
pair can be built without an observable point-in-time roll, and extending it to a spliced
series would violate the data gate. The screen's existing published numbers for the six
candidates it already covers are unchanged.

## Risk of misreading

A backtest on the cached continuous front-month series would silently embed the roll at an
unobservable price and therefore **understate the roll cost and misstate the roll yield**.
This experiment explicitly refuses that construction. "Blocked by data/infrastructure" is
the honest decision; recording it with the evidence above is a successful cycle, not a
failure.
