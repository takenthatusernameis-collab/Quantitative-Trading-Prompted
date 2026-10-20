# Hypothesis: cryptofunding_001 — Crypto perpetual funding-rate carry (spot long + perp short)

## Mechanism
Perpetual swaps pay funding to anchor price to spot; persistently positive funding can be harvested via spot-long/perp-short. Mechanical feature of perpetual swaps driven by leveraged long demand.

## Expected direction and magnitude
Positive carry from funding payments; magnitude unproven beyond ~66 days of OKX data (~5.85% annualized BTC).

## Holding horizon
Continuous (funding every 8h); position held while funding positive.

## Asset universe
BTC/USDT, ETH/USDT perpetuals on OKX (single accessible exchange).

## Features and data sources
OKX 8h funding-rate history (~66 days verified); no crypto data cached in repository.

## Entry/exit rules
Enter spot-long/perp-short when funding positive; exit when funding turns negative or risk limits hit.

## Benchmark
Hold spot only / risk-free.

## Known confounders
Funding rates volatile and can turn negative; single exchange; geo-blocked alternatives (Binance/Bybit).

## Falsification condition
No durable positive net carry after fees over multi-year history; <100 independent funding periods.

## Cost model assumptions
Fees, borrow, margin, slippage per exchange schedule; capacity limited by OKX liquidity.

## Status
Pre-registered (Cycle 886). Blocked by data: insufficient verified funding history (~66 days vs multi-year requirement), single exchange, zero diversification from existing crypto exposure. No backtest executed.
