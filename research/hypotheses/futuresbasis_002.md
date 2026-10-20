# Hypothesis: futuresbasis_002 — Commodity futures roll-carry via futures ETFs (executable route)

Parent: shortlist rank 7 (`futuresbasis_001`, "Commodity/rate futures basis and roll yield"),
which remains Blocked by data/infrastructure on the contract-leg construction.

## Mechanism
Commodity futures ETFs (USO WTI, BNO Brent, UNG natural gas, GSG broad commodity)
hold the futures position and perform the roll; the roll yield is embedded in the ETF's
total return and is observable without any contract leg. Signal = aggregate ETF total
return minus the spot proxy's total return (GC-F chain / GLD gold tracker), net of costs.

## Expected direction
Positive carry from backwardation (positive roll yield) in contango/backwardation regimes;
magnitude unknown a priori; must exceed embedded fees + 3 bp/unit turnover.

## Holding horizon
Monthly roll cycle; aggregate measured over full 2015-01-02..2026-10-15 window.

## Universe
USO, BNO, UNG, GSG (ETFs); spot proxy GLD vs GC-F chain for the gold leg.

## Features / data sources
Yahoo Finance daily OHLCV, total-return construction (auto_adjust=True), cached under
data/raw/{USO,BNO,UNG,GSG}.parquet. Roll dates from cached futures volume signature
(research/futures_roll_visibility.py).

## Entry / exit
Long ETF position, held through roll; no timing overlay (baseline).

## Benchmark
Close-to-close underlying spot proxy total return.

## Known confounders
ETF expense ratios, tracking error, roll schedule differences, contango/backwardation
regime shifts, survivorship, distribution reinvestment assumptions.

## Falsification condition
Net carry does not cover embedded fee + 3 bp/unit model on its own window; or the
block-bootstrap CI includes zero. Also Blocked by data/infrastructure if ETF series unusable.

## Cost-model assumptions
3 bp per unit of weight change (config/settings.yaml); 5 bp and 10 bp sensitivity rows;
embedded ETF expense ratios are part of the observed total return (not added).

Pre-registered before measurement. Trials: 1 (no parameter grid).
