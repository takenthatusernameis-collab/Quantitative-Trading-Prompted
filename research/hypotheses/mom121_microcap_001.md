# Preregistered Hypothesis: Microcap Cross-Sectional Momentum 12–1 (mom121_microcap_001)

**Status:** Pending data-integrity audit and execution. No alpha claim has been established by this preregistration.

## Research question

Can a monthly, long-only, cross-sectional 12–1 momentum portfolio of US microcap common stocks produce a reproducible positive return in strictly chronological out-of-sample periods after trading costs, turnover, liquidity limits, and conservative execution assumptions?

## Mechanism and falsification

The candidate mechanism is gradual price discovery / investor underreaction in small, less-followed companies. This is a hypothesis, not an assumption that microcaps are inherently inefficient. The signal must add value beyond an eligible-universe benchmark and remain implementable after trading frictions.

Reject the confirmatory hypothesis if any material integrity condition fails; if net OOS excess return versus the eligible-universe equal-weight benchmark is not positive; if net OOS Sharpe fails the repository's preliminary 0.9 screen; if results depend on survivorship/look-ahead, a single fold/regime, or a small subset of extremely illiquid names; or if the apparent edge disappears under a credible stressed-cost case. Insufficient history, sample size, or reliable universe data means **Blocked / Provisional**, not proof that the economic hypothesis is false.

## Primary strategy specification (freeze before viewing OOS results)

- **Universe:** US-listed common stocks classified as microcaps using information that was actually available on each historical formation date. Prefer an explicit market-cap interval of approximately USD 50–300 million when contemporaneous shares outstanding and prices support it. State any source-specific differences in definition, nominal-dollar effects, or missing market-cap observations. Exclude ETFs, funds, preferred shares, warrants, units, and duplicate share classes unless explicitly justified and handled consistently.
- **Point-in-time membership:** Include historical listings and delisted securities where reliable data permit. Never construct the confirmatory universe from today's surviving tickers, present-day index constituents, or current market caps applied retrospectively.
- **Signal:** At month-end formation date t, calculate canonical 12–1 momentum from adjusted month-end price at t−1 month to adjusted month-end price at t−12 months: MOM12_1(t) = AdjClose(t−1 month) / AdjClose(t−12 months) − 1. This skips the most recent month. Record exact timestamps and ensure all inputs were available before the next session's execution. Do not silently substitute a 252-day window plus an additional 21-day skip (which reaches further back); if the repository's existing function implements that different convention, document it and treat it only as a separately labelled definition.
- **Portfolio:** Rank eligible stocks by signal, buy the top decile, equal-weight, long-only, no leverage; rebalance monthly using signal information available at formation. Execute no earlier than the next tradable session. Apply consistent rules for minimum price, stale/missing prices, trading halts, and insufficient liquidity before computing ranks.
- **Benchmarks:** At minimum, the eligible point-in-time microcap universe equal-weighted with matching dates/cost conventions, plus a relevant investable microcap benchmark only where reliable total-return data are available. Include a cash/risk-free comparison when supported.
- **Primary baseline:** Keep this specification fixed. Any additional signal definitions or portfolio fractions must be identified as predeclared sensitivity tests and counted as separate trials, never chosen using the final holdout.

## Required data and integrity gate

1. Inventory data files, source/provider, licensing/access limitations, frequencies, columns, historical coverage, corporate-action adjustment, identifier quality, point-in-time shares outstanding/market cap, exchange/security type, trading volume, delisting coverage, and availability of quoted spreads or defensible cost proxies.
2. Test date alignment, duplicate identifiers/dates, missing and stale observations, adjusted-price continuity around splits/dividends, halt/delist handling, and timestamp availability. Do not forward-fill individual stock prices across material gaps to manufacture returns or liquidity.
3. If the available data cannot establish a point-in-time microcap universe and credible delisting treatment, label the confirmatory experiment **Blocked by data**. A current-ticker Yahoo Finance basket may only be used as a clearly labelled exploratory diagnostic and must not be promoted as a valid microcap backtest.
4. Preserve raw data; record source version, date range, hashes/counts where feasible, universe size by month, exclusions, and reproducible acquisition steps. No secrets, paid services, or new dependencies without explicit necessity and authorization.

## Evaluation design and costs

- Use strictly chronological development/validation/OOS partitions appropriate to the data actually available. Freeze the final holdout before tuning; never inspect final-holdout results to select parameters. Report fold-level results and a pooled OOS series with each calendar date counted at most once; do not double-count overlapping test windows.
- Reset positions, cash, equity, open orders, and all portfolio state at every independent fold boundary. Each fold must start from the documented initial state. Zero-trade folds must have no strategy P&L and must not inherit any preceding fold's equity, positions, or returns.
- Validate signal timing, split/dividend handling, missing data, position sizing, weight normalization, turnover, transaction-cost application, and end-of-period liquidation. Add deterministic unit/regression tests, including synthetic edge cases, before interpreting results.
- Estimate costs from reliable spread, volume, and liquidity data where possible. Include commissions/fees, half-spread, slippage and market impact; scale cost or reject trades when participation/ADV constraints are breached. If granular quotes are absent, disclose the proxy and test predeclared round-trip cost stress scenarios (at least 50, 100, and 200 bps, unless robust source evidence supports a better calibration). Show gross results only as a diagnostic; net results are primary.
- Compare the strategy against the matching benchmark after the same eligible trading universe and economically comparable costs. Include concentration and capacity sensitivity, especially dependence on low-price / low-volume observations.

## Required reporting

Report, where sample size supports them: gross and net cumulative return, CAGR, annualized volatility, Sharpe and Sortino, max drawdown and duration, downside/tail losses, turnover, trade/position count, profit factor, average exposure, benchmark-relative return, fold/year/regime stability, liquidity/ADV participation, and estimated capacity. State annualization conventions and risk-free-rate treatment. Track the total number of hypotheses/configurations tried. Use block-bootstrap confidence intervals and multiple-testing-aware measures (e.g. Deflated Sharpe / PBO) where valid for the available sample; explicitly describe limitations instead of presenting any statistic as proof.

## Reproducibility artifacts

Persist the preregistration, data audit, source/config/code revision, universe counts and construction, cost scenarios, fold boundaries, trial count, complete result tables, limitations, exact commands, and tests. Keep a clear decision label: **credible candidate for further validation**, **exploratory signal**, **rejected/failed**, or **blocked by data/infrastructure**. No live trades or deployment claims.
