# Cycle 942 — Evidence-based search for a new candidate using the Cycle 941 decomposition

## Context

Cycle 941 re-verified all four closed shortlist candidates from the committed parquet cache using a new read-only deterministic harness (`research/shortlist_gross_edge_001.py`, `research/experiments/shortlist_gross_edge_001.md`, `research/reports/shortlist_gross_edge_001.md`). Key findings (one convention stated):

| Candidate | Benchmark | Gross excess (cost=0) ann. | Measured turnover (u/yr) | Measured cost drag ann. | Net excess ann. | Class |
|---|---|---|---|---|---|---|
| reversal_001 | 1/N of same nine ETFs | -6.921261% | 100.766 | 3.023000% | -9.944252% | no_gross_edge |
| pairs_001 | cash | 8.786166% | 68.692 | 2.136449% (turnover) + 20.327103% (borrow) = 22.463552% total | -13.677386% | gross_edge_below_cost_hurdle |
| liquidity_001 | 1/N of same nine ETFs | -7.869716% | 24.000 | 0.720000% | -8.589716% | no_gross_edge |
| leadlag_001 | cash | 4.120849% | 25.512 | 0.765372% | 3.355477% | other (net positive but WF gates fail: mean OOS Sharpe 0.0737 < 0.9, positive fold rate 0.333 < 0.5, DSR negative) |

Cycle 934's four-way shortlist is exhausted. No variant of those four is opened; no candidate is proposed in Cycle 941. The harness enforces read-only on `data/` and `config/`, deterministic runs, and writes only under `research/`.

## Objective

Search for **one** new, structurally distinct candidate from the **committed parquet cache only** (no new fetches/services/dependencies/workflows/agents). Follow AGENTS.md: data readiness first, hypothesis-first (mechanism, direction, horizon, universe, features, entry/exit, benchmark, confounders, falsification), baseline before complexity, realistic costs, walk-forward with purging/embargo, honest accounting. The new candidate must be genuinely different from reversal_001, pairs_001, liquidity_001, leadlag_001 and must not be a re-tune of them.

## Acceptance criteria

- Document hypothesis in `research/hypotheses/<new_candidate_id>.md` with all required elements.
- Add frozen pre-registered config `config/<new_candidate_id>.yaml` (frozen before backtest). Include explicit cost model (use committed convention: 3.0 bp per unit of weight change unless there is a documented, measurable reason different; any deviation must be justified and applied consistently).
- Inventory real data in `data/raw/` actually usable for this candidate (point-in-time, coverage, calendar alignment). If insufficient real data exists to test the mechanism credibly, stop and produce a **narrow, bounded** next task that creates only the missing evidence (do not fabricate data).
- Implement a minimal, read-only evaluation script `research/<new_candidate_id>_evaluation.py` following patterns of existing evaluators (frozen-config assertion, cache-only, SHA checks on data/config, walk-forward with purge/embargo, realized turnover/cost drag, benchmark-relative accounting).
- Add tests `tests/test_<new_candidate_id>_evaluation.py` covering frozen-config stability, cache-only/read-only behavior, and basic sanity checks.
- Run evaluation; record in `research/experiments/<new_candidate_id>_evaluation.md` and `research/reports/<new_candidate_id>_evaluation.md` with all metrics, cost decomposition, trials count, reproduction commands.
- Respect promotion gates (net OOS Sharpe >= 0.9, >100 pooled OOS trades as preliminary screening) but do not relax for weak results; label as credible/exploratory/rejected/blocked with evidence.
- Validation commands all pass (including any new tests). `git status --porcelain data/ config/` unchanged by the evaluation (and no unplanned writes outside allowed locations).
- Prepare **ONE** narrow next task in `NEXT_AGENT_TASK.md` based on evidence from this cycle.

## Scope boundaries

- No re-tuning/reopening of the four closed candidates. No variants of them.
- No new data downloads, services, dependencies, scheduled jobs, agents, workflows, permissions, or infrastructure changes unless strictly necessary to test the new hypothesis and benefit is documented.
- Research/backtest only. No live trading.
- Use only committed parquet cache. Do not fabricate data/metrics.

## Handoff notes

- Cycle 941 shows gross edges exist in places (pairs had gross ~8.79% but consumed by borrow+turnover; leadlag had small positive net in decomposition but failed WF/gates). Any new candidate needs positive gross edge after realistic costs and statistical robustness.
- DSR sample alignment remains noted (liquidity computed on full-sample in published form) - be consistent and explicit about samples used.
- Two turnover conventions existed for pairs; be precise about definitions.
