# Experiment: cryptofunding_001 data collection (OKX funding rates)

Generated: 2026-10-20 00:45:11 UTC
Source: OKX API (public) via ccxt 4.5.88
Endpoint: public funding-rate-history (v5)

Symbols collected:
- BTC/USDT:USDT (BTC-USDT-SWAP), inverse/linear: linear=True (USDT-margined)
- ETH/USDT:USDT (ETH-USDT-SWAP)

BTC/USDT-SWAP:
- Rows: 296
- Start (UTC): 2026-07-13 16:00:00+00:00
- End (UTC): 2026-10-20 00:00:00+00:00
- Duration: 98.33 days
- Interval: 8h (28800000 ms), 295 intervals as expected
- Funding rate range: [-0.000039, 0.000100]
- Mean (annualized approx, simple): 1.7878%
- Median (annualized): 1.8072%

ETH/USDT-SWAP:
- Rows: 296
- Start (UTC): 2026-07-13 16:00:00+00:00
- End (UTC): 2026-10-20 00:00:00+00:00
- Duration: 98.33 days
- Interval: 8h
- Funding rate range: [-0.000085, 0.000100]
- Mean (annualized): 1.4114%
- Median (annualized): 1.3579%

Limitations:
- OKX public API funding-rate-history limited to recent history (returned ~98-296 records max depending on query). Observed: 296 records (~98.3 days) for both symbols.
- Multi-year history (>= 365 days) is NOT available from this public endpoint in this environment.
- Single exchange (OKX). No cached history in repo before this collection.

Conclusion:
Data collected to document the blocker precisely. Insufficient history for robust multi-year test as required by cryptofunding_001 hypothesis (needs >= 1 year). Block remains.
