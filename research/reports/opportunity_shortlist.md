# Opportunity Shortlist

## Overview

This document presents an evidence-based shortlist of candidate trading opportunities, scored against the seven criteria defined in AGENTS.md. Each opportunity is evaluated based on verified data availability and realistic cost assumptions from `research/reports/data_inventory.md`. Scores use a 1-5 scale where 1 = poor/infeasible and 5 = excellent/feasible.

**Scoring Legend:**
- (a) Data quality/access
- (b) Plausible structural explanation
- (c) Expected return after costs
- (d) Robustness and statistical power
- (e) Liquidity/capacity
- (f) Automation and operating burden
- (g) Diversification from existing research (existing exposure is large-cap crypto)

---

## Opportunity 1: US Equity Time-Series Momentum

**Mechanism:** Time-series momentum exploits the tendency for recently strong-performing assets to continue outperforming in the short-to-medium term. This is driven by behavioral underreaction, investor herding, and slow information diffusion. A simple strategy buys assets with positive recent returns and sells (or stays flat on) assets with negative recent returns.

**Asset Universe:** Liquid US equity ETFs (SPY, QQQ, IWM, VXX for volatility, TLT for bonds, GLD for gold)

**Holding Horizon:** 20-120 trading days (monthly rebalancing typical)

**Entry/Exit:** Rank assets by 3-12 month momentum; go long top decile, rebalance monthly.

**Benchmark:** Equal-weighted portfolio of same ETFs or risk-free rate.

**Cost Model:** 1.0 bps commission + 2.0 bps slippage per trade (from settings.yaml).

### Scores

| Criterion | Score | Rationale |
|-----------|-------|-----------|
| (a) Data quality/access | 5 | yfinance provides 25-30+ years of clean daily data for SPY (1993), QQQ (1999), IWM (2000), GLD (2004), TLF (2002). Data is survivorship-bias-controlled at the ETF level. |
| (b) Structural explanation | 4 | Well-documented anomaly with behavioral and institutional explanations. Persistence is debated due to competition, but structural mechanism is sound. |
| (c) Expected return after costs | 4 | Gross momentum premia are typically 3-8% annualized; net of 3bps round-trip costs, still 3-7% for liquid ETFs. Modest but real. |
| (d) Robustness/statistical power | 5 | Decades of data provide thousands of independent monthly observations. Extensive academic literature confirms robustness across markets and time periods. |
| (e) Liquidity/capacity | 5 | SPY and QQQ have daily volumes of $20-50B; strategy capacity easily exceeds $100M with negligible market impact. |
| (f) Automation burden | 5 | Daily data, monthly rebalancing. Simple ranking algorithm. No special infrastructure required. |
| (g) Diversification | 5 | Equity-based strategy; substantially different from existing large-cap crypto exposure. |

**Total: 28/35**

**Assessment:** Strong candidate for Cycle 2 baseline test. Longest data history, lowest costs, simplest implementation, and diversifies existing crypto exposure. Not an alpha claim; a baseline to validate the research pipeline.

---

## Opportunity 2: Multi-Asset Cross-Sectional Momentum

**Mechanism:** Cross-sectional momentum ranks assets by recent performance and goes long winners while shorting losers within a universe. Exploits underreaction to firm-specific information and slow price adjustment.

**Asset Universe:** Broad set of liquid ETFs across equities (SPY, QQQ, IWM), sectors (XLK, XLF, XLE), commodities (GLD, SLV), bonds (TLT, IEF), and international (EFA, EEM).

**Holding Horizon:** 60-90 trading days (monthly rebalancing).

**Entry/Exit:** Rank all assets by 12-month return (excluding most recent month); go long top 30%, short bottom 30%; equal-weight.

**Benchmark:** Market-neutral zero-investment portfolio; compare Sharpe to 1/N benchmark.

**Cost Model:** 1.0 bps commission + 2.0 bps slippage per leg. Short interest borrow costs not modeled (gap).

### Scores

| Criterion | Score | Rationale |
|-----------|-------|-----------|
| (a) Data quality/access | 5 | yfinance provides daily data for 20+ ETFs spanning 1993-2026. |
| (b) Structural explanation | 5 | Well-established in academic literature (Asness et al. 2013). Clear behavioral and institutional mechanism. |
| (c) Expected return after costs | 3 | Gross Sharpe typically 0.4-0.6; net of costs, bid-ask on shorts, and borrow fees, may drop to 0.3-0.5. Competitive space with many providers. |
| (d) Robustness/statistical power | 4 | Strong historical evidence, but cross-sectional signal is weaker than time-series. Multiple decades of data available. |
| (e) Liquidity/capacity | 4 | Very liquid ETFs; capacity moderate due to short-side constraints and borrow costs. |
| (f) Automation burden | 4 | Requires both long and short execution; more complex than time-series momentum. |
| (g) Diversification | 4 | Equity-focused multi-asset; different from large-cap crypto exposure. |

**Total: 25/35**

**Assessment:** Solid candidate, but less attractive than pure time-series momentum due to short-side complexity, borrow costs, and increased commission burden. Consider for later cycle if baseline TSMOM proves viable.

---

## Opportunity 3: Crypto Perpetual Funding Rate Carry

**Mechanism:** Perpetual swap futures include a periodic funding rate paid by shorts to longs (or vice versa) to anchor the swap price to the spot index. When funding rates are persistently positive (contango), a strategy of buying spot and shorting perpetual swaps captures the funding rate as yield.

**Asset Universe:** BTC/USDT, ETH/USDT perpetual swaps on OKX.

**Holding Horizon:** 8-hour funding intervals; strategy holds positions through funding payments.

**Entry/Exit:** Go long spot, short perpetual swap, hold for funding rate collection. Exit when rate turns negative or basis becomes excessive.

**Benchmark:** Spot buy-and-hold return.

**Cost Model:** 0.10% OKX spot taker fee + 0.02% swap taker fee + 2.0 bps slippage per entry/exit + basis risk.

### Scores

| Criterion | Score | Rationale |
|-----------|-------|-----------|
| (a) Data quality/access | 4 | OKX CCXT verified accessible. Funding rate history available (8-hour intervals) but only 66 days verified (200 records). Spot and swap OHLCV available at 1m-1d. Binance and Bybit are blocked. |
| (b) Structural explanation | 4 | Funding rate is a mechanical feature of perpetual swaps. Positive funding is driven by market structure (long demand from leverage traders). Mechanism is structural, not data-mined. |
| (c) Expected return after costs | 3 | Verified average annualized funding rate: ~5.85% for BTC, ~5.34% for ETH. Net of fees (~0.12%) and basis risk, still positive. But rates are volatile and can turn negative. |
| (d) Robustness/statistical power | 3 | Only 66 days of verified funding data available; insufficient for statistical significance. Requires implementation of deeper pagination to access longer history. |
| (e) Liquidity/capacity | 5 | BTC and ETH have deep liquidity on OKX. Verified sub-1bps spreads and high volumes. Capacity well above $100M. |
| (f) Automation burden | 3 | Requires real-time API connection, margin management, position sizing across spot and swap accounts. More infrastructure than daily strategies. |
| (g) Diversification | 2 | This is crypto exposure; existing research already covers large-cap crypto. Low diversification value. |

**Total: 19/35**

**Assessment:** Interesting opportunity with a clear structural mechanism, but constrained by: (1) only one exchange accessible (Binance/Bybit blocked), (2) insufficient verified funding rate history for statistical confidence, (3) low diversification from existing crypto exposure. Deprioritize until multi-exchange data or deeper history is available.

---

## Opportunity 4: Crypto Spot-Perpetual Basis Mean Reversion

**Mechanism:** The basis between spot price and perpetual swap price should converge to fair value determined by the funding rate. Temporary deviations from fair basis can be exploited by taking positions that profit from convergence. This is a high-frequency version of funding rate arbitrage.

**Asset Universe:** BTC, ETH, SOL, ADA spot vs perpetual swaps on OKX.

**Holding Horizon:** Minutes to hours (intraday).

**Entry/Exit:** Enter when basis deviates 2+ standard deviations from historical mean; exit at convergence.

**Benchmark:** Buy-and-hold spot return.

**Cost Model:** Spot taker fee 0.10% + swap taker fee 0.02% + slippage per entry/exit. Basis is typically <0.1%, requiring high precision.

### Scores

| Criterion | Score | Rationale |
|-----------|-------|-----------|
| (a) Data quality/access | 3 | OKX spot and swap data available at 1m resolution. Only recent data verified; no long historical basis series confirmed. |
| (b) Structural explanation | 4 | Basis should converge due to arbitrage; mechanism is sound. Requires fast execution to capture small differentials. |
| (c) Expected return after costs | 2 | Basis deviations are small (typically <0.1%); after fees (0.12%) and slippage, net returns may be negative. Requires high frequency and low-latency execution. |
| (d) Robustness/statistical power | 3 | Need long 1-minute basis series for statistical analysis; not yet verified. Convergence can be slow during stressed markets. |
| (e) Liquidity/capacity | 4 | BTC/ETH highly liquid on OKX. But high turnover erodes capacity due to fee accumulation. |
| (f) Automation burden | 2 | Requires real-time monitoring, fast execution, latency optimization, and risk management. High operational complexity. |
| (g) Diversification | 2 | Crypto exposure; no diversification from existing research. |

**Total: 16/35**

**Assessment:** Mechanism is sound but the profit opportunity is very small relative to transaction costs. Not viable without sub-bps fee tiers and low-latency infrastructure. Relegate to later research stage after baseline strategies are validated.

---

## Opportunity 5: Commodity Futures Roll Yield (Contango/Backwardation)

**Mechanism:** Futures contracts in contango (future price > expected spot) create negative roll yield for long positions, while backwardation creates positive roll yield. A strategy can exploit structural contango or backwardation patterns in specific commodity sectors to capture roll returns.

**Asset Universe:** Energy (CL=F crude oil, NG=F natural gas), metals (GC=F gold, SI=F silver), agriculture (HE=F lean hogs), bonds (ZB=F 10-year note).

**Holding Horizon:** Varies by contract maturity; roll occurs at contract expiration.

**Entry/Exit:** Long front-month futures; roll to next month at expiry. Profit from positive roll yield in backwardation markets.

**Benchmark:** Spot commodity return (where available) or buy-and-hold futures return.

**Cost Model:** 1.0 bps commission + 2.0 bps slippage per roll. Roll timing and execution costs not explicitly modeled.

### Scores

| Criterion | Score | Rationale |
|-----------|-------|-----------|
| (a) Data quality/access | 4 | yfinance provides continuous futures contracts (CL=F, NG=F, GC=F, etc.) with ~25 years of daily data. Continuous contracts have implicit roll logic but exact methodology is undocumented. No separate spot price series for most commodities. |
| (b) Structural explanation | 5 | Roll yield is a structural feature driven by storage costs, convenience yields, and supply-demand fundamentals. Well-documented in academic and practitioner literature. |
| (c) Expected return after costs | 3 | Roll yield varies by commodity and market regime. Oil and gas can have significant negative carry (contango) making long positions unprofitable. Positive roll opportunities (backwardation) are intermittent. High volatility. |
| (d) Robustness/statistical power | 3 | 25+ years of data available, but roll yield is regime-dependent and can persist in losing states for years. Need careful implementation of roll timing. |
| (e) Liquidity/capacity | 3 | Varies significantly. Crude oil and gold have excellent liquidity; agriculture and livestock futures can be illiquid. No spot-futures arbitrage possible without separate spot data. |
| (f) Automation burden | 2 | Requires futures account, margin management, and careful roll timing. Continuous contracts from yfinance mask real execution costs and roll timing decisions. |
| (g) Diversification | 5 | Commodity futures are structurally different from large-cap crypto exposure. Strong diversification value. |

**Total: 20/35**

**Assessment:** Structural mechanism is strong and well-documented. Data is available but quality is degraded by continuous-futures roll methodology. Requires futures account infrastructure and careful cost modeling. Medium priority for later cycles.

---

## Opportunity 6: VIX Index Time-Series Momentum

**Mechanism:** VIX (CBOE Volatility Index) exhibits mean-reverting behavior over intermediate horizons and trending behavior during regime shifts. Time-series momentum or mean-reversion strategies on VIX-related instruments can capture volatility risk premium.

**Asset Universe:** ^VIX (CBOE VIX Index), VXX (volatility ETN), UVXY (ultra VIX ETN).

**Holding Horizon:** 5-60 trading days.

**Entry/Exit:** Buy volatility exposure during low-volatility regimes; sell during high-volatility spikes. Or trend-follow volatility during regime shifts.

**Benchmark:** S&P 500 (SPY) total return.

**Cost Model:** 1.0 bps commission + 2.0 bps slippage per trade. ETN-specific risks (credit risk, tracking error) not modeled.

### Scores

| Criterion | Score | Rationale |
|-----------|-------|-----------|
| (a) Data quality/access | 3 | ^VIX index data available 1990-2026 (9,263 days). But VIX futures (VX=F) are NOT available from yfinance. VXX/UVXY data available but these are ETNs with complex dynamics. No reliable futures curve data. |
| (b) Structural explanation | 4 | Volatility risk premium is well-documented (variance risk premium). VIX mean-reversion is structural due to options pricing mechanics. |
| (c) Expected return after costs | 2 | VIX strategies have high turnover and compounding decay (especially for leveraged ETNs like UVXY). Volatility clustering reduces edge. Risk premium exists but timing is difficult. |
| (d) Robustness/statistical power | 2 | VIX is non-stationary and regime-dependent. Mean-reversion can fail for extended periods during crises. Limited independent observations in calm vs. crisis regimes. |
| (e) Liquidity/capacity | 3 | VIX itself is not directly tradeable; must use VXX/UVXY which have significant tracking error and decay. Options on VIX available but not modeled. |
| (f) Automation burden | 3 | Daily data, moderate complexity. But ETN-specific risks (decay, credit) add operational burden. |
| (g) Diversification | 4 | Volatility strategies are largely uncorrelated with equity directions; different from crypto exposure. |

**Total: 19/35**

**Assessment:** Structural mechanism exists but implementation is severely constrained by lack of VIX futures data and complex ETN dynamics. Not viable without futures curve data. Low priority.

---

## Opportunity 7: US Equity Open/Close Session Effect

**Mechanism:** Stocks and ETFs exhibit systematic price patterns around market open and close. The closing auction attracts liquidity and institutional order flow. Strategies can exploit predictable patterns in opening-to-closing or closing-to-opening returns.

**Asset Universe:** SPY, QQQ, IWM, and constituent stocks.

**Holding Horizon:** Intraday (minutes to hours) or hold cash overnight to capture next-day open effect.

**Entry/Exit:** Enter at/near close; exit at/near open. Or reverse.

**Benchmark:** SPY total return.

**Cost Model:** 1.0 bps commission + 2.0 bps slippage per trade. No intraday spread model.

### Scores

| Criterion | Score | Rationale |
|-----------|-------|-----------|
| (a) Data quality/access | 2 | yfinance provides intraday data only for recent periods (1-day at 1m, 7-day at 5m). No multi-year intraday history available. End-of-day data available for 25-30 years. |
| (b) Structural explanation | 3 | Closing auction liquidity and overnight gaps have some structural basis, but the effect is debated and often arbitraged away by institutional algorithms. |
| (c) Expected return after costs | 2 | Overnight gap effects are typically <2% annualized; intraday patterns are weak and easily arbitraged. Costs (commission + slippage + spread) eat most of the edge. |
| (d) Robustness/statistical power | 1 | Insufficient intraday data for statistical analysis. Daily proxies available but may not capture true intraday effect. |
| (e) Liquidity/capacity | 4 | SPY/QQQ extremely liquid. No capacity constraints for moderate trade sizes. |
| (f) Automation burden | 2 | Requires intraday data and precise timing. But no intraday data available for meaningful backtesting period. |
| (g) Diversification | 4 | Equity-based, different from large-cap crypto exposure. |

**Total: 16/35**

**Assessment:** Insufficient data for valid testing. Intraday data only available for very recent periods. No multi-year history. Rejected for now.

---

## Considered-But-Excluded Opportunities

### Excluded: Binance Funding Rate Arbitrage
**Reason:** Binance API returns HTTP 451 ("Service unavailable from a restricted location") from this environment. No data can be accessed. Even if accessible, geographic restrictions may make it unreliable. Binance has historically provided rich funding rate data spanning years, which would be ideal for this strategy. Blocked by infrastructure limitation.

**Score if accessible:** (a)=5, (b)=4, (c)=4, (d)=4, (e)=5, (f)=3, (g)=2 — Total 27/35

### Excluded: Bybit Funding Rate Arbitrage
**Reason:** Bybit API returns HTTP 403 ("block access from your country") from this environment. No data accessible. Same structural opportunity as Binance funding rates but blocked.

### Excluded: Historical Options Trading Strategies
**Reason:** yfinance provides live options chains (SPY: 27 expiries, call/put bids/asks/IV) but no historical options price or IV data. Cannot backtest volatility strategies (straddles, condors, IV crushing) without years of historical options data. The available data is only for near-term expiries (next 27 dates through 2029-01-19), but bid/ask values are NaN for unstarted expiries. No historical IV time series.

### Excluded: Forex Carry Trade (Interest Rate Differentials)
**Reason:** yfinance provides spot Forex rates (EURUSD=X, GBPJPY=X, etc.) with 20+ years of daily data, but does NOT provide interest rate differentials or forward rates needed for carry trade implementation. No deposit rates, no forward curves. Spot Forex data alone cannot support a carry trade strategy.

### Excluded: High-Frequency Statistical Arbitrage
**Reason:** Only 1-minute resolution data available for recent periods (1-day window for crypto, 1-day for equities). No tick-level or order-book data. Insufficient for HFT strategies. Transaction costs would dominate any signal.

### Excluded: News-Based or Sentiment Strategies
**Reason:** No news data feed, social media data, or sentiment data source configured in the repository. yfinance does not provide news sentiment. No alternative data source available.

### Excluded: Cross-Exchange Crypto Arbitrage
**Reason:** Only one exchange (OKX) is accessible. Binance and Bybit are blocked. Cross-exchange arbitrage requires multiple venues simultaneously. Per AGENTS.md: avoid cross-venue arbitrage unless explicitly authorized and operationally justified.

---

## Ranking and Recommendation for Cycle 2

| Rank | Opportunity | Total Score | Key Strength | Key Constraint |
|------|-------------|-------------|--------------|----------------|
| 1 | US Equity Time-Series Momentum | 28/35 | Decades of clean data, lowest costs, simplest implementation, best diversification from crypto | Competitive space, modest returns |
| 2 | Multi-Asset Cross-Sectional Momentum | 25/35 | Strong academic backing, diversified | Short-side borrow costs, complexity |
| 3 | Commodity Futures Roll Yield | 20/35 | Strong structural mechanism, good diversification | Continuous contract quality, futures account needed |
| 4 | Crypto Perpetual Funding Rate Carry | 19/35 | Clear structural mechanism, verified data | Only 1 exchange, limited funding history, low diversification |
| 5 | VIX Index Time-Series | 19/35 | Volatility risk premium is structural | No VIX futures data, ETN complexity |
| 6 | Spot-Perpetual Basis MR | 16/35 | Strong mechanism | High costs, low-frequency data |
| 7 | Open/Close Session Effect | 16/35 | Equity-based | No intraday history |

### Recommendation

**Cycle 2 should implement a baseline US Equity Time-Series Momentum strategy** using yfinance daily data for SPY, QQQ, and IWM. This opportunity was selected because:

1. **Longest verified data history** (SPY: 1993-2026, 8,482 days)
2. **Lowest implementation complexity** — single asset class, daily rebalancing
3. **Realistic cost model** — commission and slippage from settings.yaml are reasonable for ETF trading
4. **Best diversification** from existing large-cap crypto exposure
5. **Well-documented structural mechanism** — time-series momentum is a first-order market anomaly

The strategy should be implemented as a transparent baseline before testing more complex or crypto-based opportunities. Results will validate the research pipeline (data → features → backtest → evaluation) and inform Cycle 3.
