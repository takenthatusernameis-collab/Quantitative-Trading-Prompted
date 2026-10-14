# Next Agent Task: Microcap 12–1 Momentum — Data Audit, Clean Walk-Forward, and Net OOS Test

## Prompt refinement record

- **Iteration 1 — Hypothesis:** Test whether a 12-month equity momentum signal that skips the latest month produces a real microcap edge.
- **Iteration 2 — Operational definition:** Freeze the point-in-time universe, the exact 12–1 formula, monthly formation/execution timing, long-only baseline, and comparable benchmarks before examining OOS outcomes.
- **Iteration 3 — Failure-mode controls from the Extreme Quant mom121 work:** Explicitly audit universe construction and fold boundaries; isolate cash/position/equity state across folds; prevent zero-trade folds from inheriting returns; verify signal implementation, realistic frictions, and reproducibility.
- **Iteration 4 — Decision discipline:** Require delisted-stock / point-in-time controls and net OOS evidence. Treat missing data as a blocker, not permission to use survivorship-biased proxies or invent results.

The final task below is the execution prompt; do not restart an endless prompt-rewriting loop.

## Context and priority

The user explicitly prioritizes this microcap study over the prior ETF paper-trading monitoring task. The previous NEXT_AGENT_TASK.md is preserved at research/tasks/archive/cycle52-paper-trading-monitoring-2026-10-14.md.

The Extreme Quant mom121 work identified fold-state contamination and universe-construction as material risks to resolve before judging an edge. Prior artifacts referenced in conversation include research_journal/signal-construct-mom121.json and research_journal/backtest-verification-mom121-iter1.json; that repository is not currently accessible through this connection, so do not invent or assume unobserved metrics or findings beyond those known failure modes.

This repository's visible historical-data inventory is ETF/sector-oriented. Its existing momentum module implements cross-sectional ranking on the cached investable universe, not a point-in-time microcap stock universe. Verify the checked-out working tree and every available data source before deciding that an executable confirmatory test is possible.

## Objective

Execute the deepest useful, evidence-led research cycle available in the current Kilo runtime: audit data and existing implementations, write/verify the preregistration, repair only material test/engine defects required for a trustworthy experiment, run the fixed baseline plus bounded predeclared cost and stability tests when valid data permit, independently red-team the result, and persist a reproducible decision.

Read AGENTS.md, PROMPT.MD, this task, the archived task only where useful, the existing cross-sectional momentum hypothesis/results, src/features/momentum.py, src/backtest/engine.py, relevant data code/configuration/tests, and available prior experiment artifacts. Reuse working infrastructure; do not rebuild the stack merely to create activity.

## Acceptance criteria

### A. Data/universe gate — do this first

1. Inventory all available historical stock/market data and candidate providers. Validate fields, dates, corporate actions, historical listings/delistings, identifier continuity, contemporaneous market cap, exchange/security type, volume, and quoted-spread availability.
2. Require point-in-time universe membership and adequate delisting treatment for a confirmatory microcap result. Do not use today's survivors, current index constituents, or current market caps applied retrospectively as the confirmatory universe.
3. If the data gate fails, classify the study Blocked by data/infrastructure; explain the exact missing fields/sources and the lowest-friction credible path to resolve it. You may run clearly labelled exploratory diagnostics on imperfect data to test code, but never present them as evidence of a true microcap edge.
4. Do not fetch or commit huge raw files blindly; keep data provenance, cache paths, observation counts, and hashes where feasible. No credentials/secrets, live trading, paid services, or new dependencies without explicit authorization.

### B. Strategy and preregistration

Use research/hypotheses/mom121_microcap_001.md as the frozen primary specification. Primary signal: monthly canonical 12–1 adjusted-close momentum, AdjClose(t−1 month) / AdjClose(t−12 months) − 1; long-only equal-weight top decile of point-in-time US microcap common stocks; monthly rebalance; next-session execution; no leverage. Clarify any repository implementation that instead computes a full 252-day return and then skips another 21 days. Primary benchmark is the matching eligible-universe equal-weight portfolio; use an investable microcap index only when data support a fair comparison.

Do not tune primary choices after looking at OOS performance. Bounded sensitivity testing may cover predeclared cost scenarios, liquidity/participation constraints, fold/regime stability, and a small set of clearly labelled signal/portfolio variants; log every trial and preserve null and negative results.

### C. Backtest correctness and Extreme mom121 regression lessons

1. Inspect the actual walk-forward implementation and data/universe construction. Confirm every fold uses a fresh initial portfolio state: cash, equity, holdings, orders, and P&L accounting cannot leak from train or prior test folds.
2. Add tests that fail if zero-trade folds inherit returns or prior positions; include empty/zero-return folds, fold starts after a profitable/loss-making prior fold, missing histories, delisted assets, and signal-date alignment.
3. Prove that each return uses only information available by the signal timestamp, execution occurs no earlier than the next tradable session, corporate actions are handled consistently, and each pooled OOS date is counted once even if fold windows overlap.
4. Validate missing data, duplicate security/date rows, survivorship, stale-price handling, weight normalization, turnover, and realistic cost deductions. Fix the smallest material defect, not unrelated infrastructure.
5. Run the relevant existing tests plus new targeted regression tests and a deterministic replay. Quote only commands that actually ran and their observed outcomes.

### D. Heavy but bounded empirical work, if the data gate passes

1. Run the frozen baseline first and preserve it before testing sensitivities.
2. Use chronological development/validation/final OOS partitions, then walk-forward folds with non-duplicated pooled OOS dates, fixed primary parameters, and appropriate boundary treatment. Do not tune on the final holdout.
3. Benchmark net returns versus the matching equal-weight microcap universe. Apply transparent commissions, spread, slippage, and impact/participation assumptions; where quote data are absent, disclose the proxy and test at least 50, 100, and 200 bps round-trip unless source evidence supports a better calibrated schedule.
4. Report cumulative return, CAGR, annualized volatility, Sharpe/Sortino, max drawdown and duration, profit factor, turnover, trade/position counts, exposure, tail risk, benchmark-relative performance, fold/year/regime stability, liquidity participation, and capacity where estimable. Track every configuration/hypothesis.
5. Use block-bootstrap confidence intervals and multiple-testing-aware metrics only when sample size and implementation support them; disclose uncertainty and limitations.

### E. Decision thresholds and stopping rules

The repository's net OOS Sharpe >= 0.9 and >100 pooled OOS trades are preliminary screening gates, not proof and not universal laws. A credible candidate must also have positive net benchmark-relative OOS performance, plausible execution, stable performance across independent periods, and no material data/control failure. Show whether results survive stressed costs. If adequate independent observations do not exist, classify as exploratory/provisional rather than stretching significance.

Stop confirmatory claims immediately if point-in-time microcap membership or delisted-stock handling cannot be verified. Do not burn sessions repeating the same broken backtest, restating the task, or expanding parameter search. Correct the root cause once, run independent verification, or document the blocker and make the next task resolve the specific missing evidence.

### F. Durable outputs and handoff

- Maintain research/hypotheses/mom121_microcap_001.md as the preregistered hypothesis; update it only to correct documented ambiguities, with version history.
- Create research/experiments/mom121_microcap_001.md containing data gate, methods, trial count, fold design, cost assumptions, results, red-team findings, limitations, classification, and exact reproduction commands.
- Add targeted tests and minimal code/config changes only as justified by evidence. Keep the baseline and all negative/null results.
- Update README research status with a factual summary only after verification.
- Prepare exactly one next-task handoff based on the strongest evidence or the precise blocker.
- Research/backtesting only. Do not place trades, enable live execution, expose credentials, alter workflow schedules/permissions/agent definitions, or create recursive task dispatch.

## Completion standard

Return a concise, evidence-backed decision: credible candidate for further validation, exploratory signal, rejected/failed, or blocked by data/infrastructure. Separate observed results from hypotheses; never fabricate data, metrics, tests, or successful execution.
