# Experiment: futuresbasis_002 — Commodity futures roll-carry via futures ETFs

Hypothesis: research/hypotheses/futuresbasis_002.md
Trials: 1 (no parameter grid).

Data: data/raw/{USO,BNO,UNG,GSG,GLD}.parquet, 2964 sessions, 2015-01-02..2026-10-15.
Total-return construction: auto_adjust=True (yfinance), documented; UNG raw price 239.36->11.09 reflects NAV roll losses, not distributions.

Aggregate (ETF total return minus GLD total return), annualized, block-bootstrap (126-session blocks, 2000 draws, seed 20261019):
- USO: -10.94%/yr, CI not excluding zero
- BNO: -1.22%/yr
- UNG: -33.82%/yr
- GSG: -6.10%/yr

All negative vs gold; CI includes zero. Net carry does not cover embedded fees + 3bp/unit. Cost screen not extended with a new row (no positive carry to cost).

Verdict: Rejected/Failed on cost (and signal sign). No claim of trading edge.

Reproduction: python research/futures_roll_visibility.py (OVERALL: PASS)
