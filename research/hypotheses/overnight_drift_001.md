# Hypothesis: Overnight Drift Exploratory Diagnostic (overnight_drift_001)

## Version History

- v001 (overnight_drift_001, 2026-10-15): Initial exploratory hypothesis for overnight drift diagnostic.
  Parent cycle: NEXT_AGENT_TASK.md assignment.
  Code revision: (current HEAD)

---

## Mechanism Description

Overnight drift refers to the well-documented tendency for equity returns to accrue predominantly during the overnight session (close-to-open) rather than the intraday session (open-to-close). The structural explanations include:

1. **Information accumulation**: Public and private information accumulates while markets are closed; prices adjust at the open to reflect overnight news, earnings, macroeconomic releases, and global market moves.
2. **Market maker inventory management**: Market makers and liquidity providers accumulate inventory imbalances during the day and adjust prices at the open to manage risk, creating a systematic overnight premium.
3. **Institutional rebalancing flows**: Large institutional orders (index rebalancing, fund flows, hedging) often execute at or near the open, creating predictable pressure.
4. **Delayed price discovery**: Less liquid assets and international assets (e.g., EFA, EEM) incorporate global information with a delay, manifesting as overnight returns when US markets open.

This diagnostic uses daily OHLCV data (Open, High, Low, Close, Volume) to decompose total daily returns into:
- **Overnight return**: `Open_t / Close_{t-1} - 1` (close-to-open)
- **Intraday return**: `Close_t / Open_t - 1` (open-to-close)
- **Total return**: `Close_t / Close_{t-1} - 1` (close-to-close)

The hypothesis is purely exploratory — we do not claim a tradable edge exists. The goal is to characterize the session return decomposition across the available ETF universe and assess whether the effect is stable, statistically significant, and potentially exploitable after realistic costs.

---

## Expected Direction and Magnitude (Pre-Specified Prior)

| Metric | Expected Range | Note |
|--------|----------------|------|
| Overnight return (annualized, SPY) | Positive, ~5–10% | Prior from literature (e.g., Berkman et al. 2012, Cliff et al. 2008) |
| Intraday return (annualized, SPY) | Near zero or slightly negative | Prior from literature |
| Overnight share of total return | > 50% for equities | Prior |
| Cross-asset variation | Higher for international/emerging (EFA, EEM), lower for bonds (TLT), commodities (DBC, GLD) | Prior |

**Falsification (exploratory only)**: If overnight returns are not statistically distinguishable from zero across the majority of equity ETFs, or if the intraday session contributes the majority of returns, the overnight drift effect is not supported in this dataset.

---

## Holding Horizon

Daily session decomposition (overnight vs. intraday). No trading strategy is proposed; this is a return attribution diagnostic.

---

## Asset Universe

The 19 cached symbols in `data/raw/` with daily OHLCV:

1. SPY — S&P 500 (1993-01-29 → 2026-10-14)
2. QQQ — Nasdaq-100 (1999-03-10 → 2026-10-14)
3. IWM — Russell 2000 (2000-05-26 → 2026-10-14)
4. TLT — 20+ Year US Treasury (2002-07-30 → 2026-10-14)
5. GLD — Gold (2004-11-18 → 2026-10-14)
6. DBC — Broad Commodity (2006-02-06 → 2026-10-08)
7. VNQ — US REITs (2004-09-29 → 2026-10-08)
8. EFA — Developed International Equity (2001-08-27 → 2026-10-14)
9. EEM — Emerging Markets Equity (2003-04-14 → 2026-10-14)
10. XLB — Materials Sector (1998-12-22 → 2026-10-08)
11. XLE — Energy Sector (1998-12-22 → 2026-10-08)
12. XLF — Financials Sector (1998-12-22 → 2026-10-08)
13. XLI — Industrials Sector (1998-12-22 → 2026-10-08)
14. XLK — Technology Sector (1998-12-22 → 2026-10-08)
15. XLP — Consumer Staples Sector (1998-12-22 → 2026-10-08)
16. XLU — Utilities Sector (1998-12-22 → 2026-10-08)
17. XLV — Health Care Sector (1998-12-22 → 2026-10-08)
18. XLY — Consumer Discretionary Sector (1998-12-22 → 2026-10-08)
19. ^VIX — CBOE Volatility Index (1993-01-04 → 2026-10-14) — *index only, not tradeable*

All symbols have 100% Close completeness, no duplicate dates, daily frequency. Earliest common date across all 18 tradeable ETFs: 2006-02-06 (DBC inception).

---

## Features and Data Sources

| Feature | Specification | Source |
|---------|---------------|--------|
| Open | Daily Open price | `data/raw/{symbol}.parquet` |
| High | Daily High price | `data/raw/{symbol}.parquet` |
| Low | Daily Low price | `data/raw/{symbol}.parquet` |
| Close | Daily Close price | `data/raw/{symbol}.parquet` |
| Volume | Daily Volume | `data/raw/{symbol}.parquet` |
| Overnight return | `Open_t / Close_{t-1} - 1` | Computed |
| Intraday return | `Close_t / Open_t - 1` | Computed |
| Total return | `Close_t / Close_{t-1} - 1` | Computed |

### Point-in-Time Treatment

All returns computed using only data available at the time. Overnight return for day t uses `Close_{t-1}` (known at prior close) and `Open_t` (known at current open). Intraday return uses `Open_t` and `Close_t` (both known during day t). No look-ahead bias in the decomposition.

---

## Entry/Exit Rules

**Not applicable** — this is an exploratory diagnostic, not a trading strategy. No entry/exit rules are defined.

---

## Benchmark

1. **Zero-return null**: Overnight and intraday returns tested against zero (t-test).
2. **Equal split null**: Overnight share of total return tested against 50% (binomial test).
3. **Cross-asset comparison**: Session return profiles compared across asset classes (equity vs. bond vs. commodity vs. REIT vs. international).

---

## Known Confounders

1. **Daily data only — no intraday execution prices**: We observe Open and Close but not the path between them. Actual execution prices for overnight positions (buying at prior close, selling at open) may differ from reported Open/Close due to bid-ask spreads, auction mechanics, and market-on-open orders.
2. **Bid-ask spreads not observed**: Yahoo Finance reports midpoint-like prices. Real overnight trading incurs spread costs (typically 1–10 bps for liquid ETFs, wider for sector/international ETFs).
3. **ETF survivorship bias**: The universe comprises currently-listed ETFs. Delisted or merged ETFs are not represented. This may overstate returns if failed funds had different session return profiles.
4. **No point-in-time universe membership**: The universe is fixed to currently available symbols. Historical universe composition (e.g., sector ETFs incepting in 1998) changes the cross-sectional properties over time.
5. **Dividend adjustments**: Yahoo Finance provides adjusted Close but Open/High/Low may not be consistently adjusted for dividends/splits, potentially biasing overnight returns on ex-dividend dates.
6. **^VIX is an index, not tradeable**: Included for reference only; VIX futures/ETFs have different session dynamics.
7. **Weekend/holiday effects**: Overnight return from Friday close to Monday open spans 3 calendar days; holiday periods span longer. Not separately modeled.
8. **Corporate actions**: Splits and dividends may create artifacts in the Open/Close relationship if not perfectly adjusted.
9. **Data source limitations**: yfinance data may have occasional errors, missing rows, or adjustments that differ from official exchange data.

---

## Falsification Condition

This is an **exploratory diagnostic only** — no formal falsification condition for a trading strategy. The diagnostic will be considered "inconclusive" if:
- Overnight returns are not statistically > 0 for the majority of equity ETFs (p > 0.05)
- Sub-period analysis shows the effect is not stable (e.g., disappears post-2020)
- Intraday returns dominate total returns for most symbols

---

## Cost Model Assumptions

**Not applicable for alpha claims** — this diagnostic does not claim a net edge. For reference, realistic overnight execution costs would include:
- Commission: ~1 bps (modern brokerage)
- Bid-ask spread at open: 2–10 bps depending on ETF liquidity
- Market-on-open slippage: 1–5 bps
- Total round-trip for overnight capture: ~5–20 bps per cycle

These costs would need to be overcome by any strategy attempting to harvest overnight drift.

---

## Pre-Registered Evaluation Plan

### Computations

For each symbol and each trading day t (where t-1 and t both exist):
1. `r_overnight = Open_t / Close_{t-1} - 1`
2. `r_intraday = Close_t / Open_t - 1`
3. `r_total = Close_t / Close_{t-1} - 1`
4. Verify: `r_total ≈ r_overnight + r_intraday + r_overnight * r_intraday` (multiplicative decomposition)

### Aggregations

1. **Per-symbol**: Mean, std, annualized mean (×252), t-stat vs zero, Sharpe (mean/std × √252) for each session return.
2. **Cumulative**: Cumulative sum of log returns for each session.
3. **Overnight share**: `r_overnight / r_total` (where r_total ≠ 0).
4. **Sub-periods**: Pre-2008 (through 2007-12-31), 2008-2020 (2008-01-01 to 2019-12-31), 2020+ (2020-01-01 onward).
5. **Cross-asset grouping**: Equity (SPY, QQQ, IWM, XLB–XLY), International (EFA, EEM), Bonds (TLT), Commodities (DBC, GLD), REITs (VNQ).

### Statistical Tests

1. One-sample t-test: H0: mean overnight return = 0
2. One-sample t-test: H0: mean intraday return = 0
3. Paired t-test: H0: mean overnight return = mean intraday return
4. Binomial test: H0: overnight return > intraday return on 50% of days

### Outputs

All results written to `research/experiments/overnight_drift_exploratory_001.md` with explicit "exploratory diagnostic only" labeling.

---

## Evidence Artifacts (To Be Persisted)

Per AGENTS.md "Evidence artifacts", this diagnostic will persist:
- Data-source details, date ranges, frequency, asset universe, point-in-time treatment
- Missing-data handling (pairwise deletion for days with missing Open/Close)
- Integrity hashes/counts (row counts per symbol, date-range coverage)
- Code revision (git SHA)
- All per-symbol and aggregate statistics
- Sub-period stability results
- Explicit limitations and bias disclosures

---

## Decision Discipline (Pre-Committed)

Results will be labeled as exactly one of:
- **Exploratory signal** — Overnight drift is statistically significant and stable; warrants further investigation with intraday data and cost modeling
- **Inconclusive** — Effect not statistically significant or not stable; no further action without better data
- **Blocked by data/infrastructure** — Cannot form valid test with available data (not expected here)

---

## References

- Berkman, H., Koch, P. D., Tuttle, L., & Zhang, Y. J. (2012). "Paying attention: overnight returns and the hidden cost of buying at the open". *Journal of Financial and Quantitative Analysis*, 47(4), 715-741.
- Cliff, M. T., Cooper, M. J., & Gulen, H. (2008). "Return differences between trading and non-trading hours: Like night and day". *Working Paper*.
- Lou, D., Polk, C., & Skouras, S. (2019). "A tug of war: Overnight vs. intraday expected returns". *Journal of Financial Economics*, 134(1), 192-213.
- AGENTS.md: Research Documentation Standards; "Honest accounting"; "Evidence artifacts"

---

*Created: 2026-10-15*
*Code revision: (current HEAD)*
*Status: EXPLORATORY DIAGNOSTIC — No trading strategy proposed.*