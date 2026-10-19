# Hypothesis: futuresbasis_001 — Commodity/Rate Futures Basis and Roll Yield

## Mechanism
Front-month futures trade at a basis to spot driven by storage, convenience yield, financing and
forced flows; rolling the front contract captures (or pays) the roll yield. A transparent long
front-month (or roll-carry) position earns the basis/roll compensation if it persists net of
roll transaction costs.

## Expected direction and magnitude
Positive excess return from holding the front-month contract and rolling, of order single-digit
percent per year, after financing; direction long the front contract.

## Holding horizon
Daily to monthly (front-month holding, rolled at expiry).

## Asset universe
Front-month futures: crude oil (CL), gold (GC), 10-yr Treasury (ZN), S&P 500 (ES) — intended.

## Features and data sources
Close prices of front-month futures. Intended source: Yahoo Finance (already supported via
src/data/yfinance_fetcher.py). No futures series is currently cached.

## Entry/exit rules
Hold front-month contract; roll to next contract at expiry under an explicit point-in-time roll
rule; no parameter search.

## Benchmark
Close-to-close buy-and-hold of the same front-month series (same-fold).

## Known confounders
Splicing bias: a backtest on a spliced front-month series silently embeds the roll at an
unobservable price, understating roll cost and misstating roll yield. Survivorship/look-ahead in
contract selection. Financing and margin. Regime dependence of contango/backwardation.

## Falsification condition
If the roll-adjusted baseline cannot cover the roll cost plus the repository's 3 bp/unit model
on its own window, the candidate is Rejected/Failed on cost.

## Cost-model assumptions
Repository flat 3 bp/unit of weight change (plus 5/10 bp rows), plus the roll transaction cost
that the construction actually pays. A point-in-time roll must be observable; if it cannot be
constructed, the candidate is Blocked by data/infrastructure, not back-tested on a spliced series.

## Status
Blocked by data/infrastructure: Yahoo Finance exposes only a continuous (spliced) front-month
series for `=F` tickers; individual contract months (e.g. CLZ20) are not retrievable, so an
explicit point-in-time roll cannot be constructed from the supported, free data source. No cache
was written and no spliced series was back-tested.
"""