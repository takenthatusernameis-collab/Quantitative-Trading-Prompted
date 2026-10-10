# Agent Instructions for Quantitative Trading Research

## Mission
Improve the probability of discovering a genuine, reproducible, net-of-cost trading edge by improving the research process—not by maximizing the number of agents, lines of code, indicators, backtests, or optimistic results.

## Current Cycle Contract

### 1. Preparation
- Read AGENTS.md, README.md, NEXT_AGENT_TASK.md, relevant source/tests, and recent experiment records before acting.

### 2. Task Validation
- Compare NEXT_AGENT_TASK.md's acceptance criteria with current code, tests, and documented outputs.
- If already complete: run verification and advance to evidence-based next task.
- Otherwise: execute current task as immediate bounded task; do not ignore for broader idea.
- Respect acceptance criteria unless user explicitly changes them.

### 3. Implementation
- Make smallest sufficient change.
- Reuse existing infrastructure.
- Preserve backward compatibility unless documented defect requires otherwise.

### 4. Verification
- Run relevant tests, lint, type checks, and reproducibility checks documented in repository.
- Report exact commands and observed results.
- Never say a check passed unless it ran and passed.

### 5. Completion
- Persist findings.
- Prepare ONE narrow, testable NEXT_AGENT_TASK.md for next cycle.
- Next task should follow from evidence, not arbitrary extension.
- Include: context, objective, acceptance criteria, validation commands, scope boundaries.

### 6. Bounded Work
- Keep work bounded and restart-safe.
- If blocked: document precise blocker and make next task resolve it.
- Do not conceal failures or invent outputs.

## Strategic Research Objective

Focus on financial-market segments where a plausible, persistent inefficiency may be discovered AND captured by a low-friction automated strategy.

### Priority Order
1. **Data readiness and integrity**: real historical observations, timestamps, point-in-time universe membership, sufficient history, independently checkable provenance
2. **Specific structural mechanism**: funding/carry or basis compensation, constraints and forced flows, market-session effects, delayed price discovery, documented rebalancing effects, robust time-series/cross-sectional behavior
3. **Net capture feasibility**: credible fees, bid-ask spread, slippage, market impact, funding, borrow, roll, latency, turnover, capacity, venue rules, operational constraints
4. **Automation practicality**: reproducible research using reliable, accessible data and simple execution assumptions
5. **Incremental value**: genuinely different from prior experiments and existing large-cap-crypto exposure
6. **Statistical testability**: enough independent observations, defensible benchmark, chronological out-of-sample design

## Market Opportunity Search

Build evidence-based shortlist rather than hard-coding claims about market inefficiency.

### Process
1. Inventory real data and costs actually available in repository first
2. Compare plausible candidates only where data supports valid test
3. Score each opportunity against:
   - (a) Data quality/access
   - (b) Plausible structural explanation
   - (c) Expected return after costs
   - (d) Robustness and statistical power
   - (e) Liquidity/capacity
   - (f) Automation and operating burden
   - (g) Diversification from existing research
4. Distinguish price predictability from executable net edge
5. Reject opportunities explained by: bad data, stale prices, survivorship/lookahead bias, omitted costs, extreme turnover, illiquidity, infeasible execution
6. Prefer modest, stable, understandable effect over spectacular isolated backtest

## State-of-the-Art Research Loop

### Principles
- **Hypothesis first**: record mechanism, expected direction, holding horizon, universe, features, entry/exit rules, benchmark, known confounders, falsification condition before tuning
- **Baseline before complexity**: test transparent baseline and cost model before adding ML, meta-labeling, ensembles, HMMs, or higher-order features
- **Controlled evolution**: once deterministic evaluation is trustworthy, propose bounded, diverse candidate mutations; record parent/lineage, configuration, search budget, results; preserve diversity and negative results
- **Independent evaluation**: separate candidate generation/tuning from final holdout; never feed final-holdout outcomes back into candidate selection; use chronological train/validation/test splits and/or walk-forward testing with purging/embargo
- **Multiple-testing control**: track hypotheses/configurations tried; use Deflated Sharpe Ratio, PBO/CSCV, probabilistic Sharpe, block-bootstrap CIs, placebo/permutation tests, parameter-plateau/perturbation checks, regime/time-period stability
- **Honest accounting**: report net returns after realistic fees and all material frictions; include Sharpe/Sortino, CAGR, max drawdown, profit factor, turnover, exposure, trade count, tail risk, benchmark-relative results, capacity limitations
- **Promotion gate**: net out-of-sample Sharpe >= 0.9 and >100 pooled out-of-sample trades as preliminary screening gates; robustness, statistical validity, net-of-cost performance, reproducibility, and plausible mechanism also required
- **Evidence artifacts**: persist data-source details, date ranges, frequency, asset universe, point-in-time treatment, missing-data handling, integrity hashes/counts, code revision, configurations, trial count, cost assumptions, baselines, metrics, folds, reproduction commands
- **Decision discipline**: label results as: credible candidate for further validation; exploratory signal; rejected/failed; or blocked by data/infrastructure

## Safety and Scope

- Research/backtesting only. Never place live trades, enable live trading, access or print secrets, or modify account credentials.
- Do not add dependencies, services, paid data, scheduled jobs, agents, workflows, permissions, or infrastructure unless current task requires it and benefit is documented.
- Do not edit workflow scheduling or agent counts as workaround for research task.
- Keep loop non-recursive at workflow level; future task must not dispatch this workflow or start additional agent sessions.
- Never fabricate data, market findings, financial metrics, test output, or sources. If real data unavailable, stop short of alpha claims and make missing evidence the next bounded task.
- Preserve working behavior. Avoid unrelated refactors and broad architecture expansion. Prefer deterministic checks over prose-only promises.
- Any residual failure must be reported accurately and converted into one bounded, non-recursive correction task with verification criterion.

## File Structure

```
/ (repository root)
├── AGENTS.md              # This file
├── README.md              # Project overview
├── NEXT_AGENT_TASK.md     # Current task specification
├── PROMPT.MD              # Mission prompt
├── data/                  # Raw and processed data
│   ├── raw/               # Original data files
│   └── processed/         # Cleaned, aligned data
├── research/              # Research notebooks and scripts
│   ├── hypotheses/        # Documented hypotheses
│   ├── experiments/       # Experiment records
│   └── reports/           # Analysis reports
├── src/                   # Source code
│   ├── data/              # Data ingestion and processing
│   ├── features/          # Feature engineering
│   ├── models/            # Model definitions
│   ├── backtest/          # Backtesting engine
│   └── evaluation/        # Evaluation metrics
├── tests/                 # Unit and integration tests
├── config/                # Configuration files
└── requirements.txt       # Python dependencies
```

## Research Documentation Standards

Each hypothesis must include:
- Mechanism description
- Expected direction and magnitude
- Holding horizon
- Asset universe
- Features and data sources
- Entry/exit rules
- Benchmark
- Known confounders
- Falsification condition
- Cost model assumptions

Each experiment must record:
- Hypothesis reference
- Data used (source, date range, frequency, universe)
- Point-in-time treatment
- Configuration (parameters, hyperparameters)
- Train/validation/test splits
- Results (all metrics)
- Number of trials
- Reproduction commands