# Cycle 948 — Commodity momentum on DBC/GLD with frozen walk-forward design (power-limited)

## Context
- Cycle 947 completed an evidence-based market-opportunity search over all data in `data/raw/`. 
- The only segment left open was `commodity_complex` (20/35). 
- Pre-declared feasibility screen of absolute time-series momentum on `{DBC, GLD}` (2006-02-06 .. 2026-10-08) gave **benchmark-relative excess net -0.5304%/yr** (Sharpe -0.0617) with 3.0 bp/unit costs; the rule also failed the trade-count/power bar. 
- Diversified commodity sets cannot satisfy the frozen 10y/12m/6m walk-forward design (most commodity futures/ETFs share a common start only from 2015-01-02, yielding only ~3 folds). 
- All other segments are closed/blocked with explicit evidence; no candidate was pre-registered this cycle.

## Objective
Test a **narrow, power-limited** commodity momentum hypothesis on the only commodity pair with sufficient history (`DBC`, `GLD`) under the repository's frozen walk-forward design and actual cost model, with full transparency about reduced statistical power. Do not expand to other commodities.

## Hypothesis (pre-register before evaluation)
Create `research/hypotheses/commoditytrend_001.md` with:
- Mechanism: time-series momentum in liquid commodity/real-asset ETFs with documented slow adjustment
- Universe: `{DBC, GLD}` only (justification from data gate)
- Signal: trailing 252-session return skipping most recent 21 sessions (as in screen), formed at month-end
- Entry/exit: long when positive, equal weight 1/N among held, else cash; no short leg
- Benchmark: 1/N buy-and-hold of `{DBC, GLD}` over common sessions
- Holding/rebalance: month-end with 1-session lag
- Cost model: 1.0 bp commission + 2.0 bp slippage = 3.0 bp per unit weight change (from `src/backtest/engine.py`)
- Known confounders: limited history (short sample), common factor exposure (risk-on/off), regime dependence
- Falsification: WF mean OOS Sharpe < 0.9 OR positive-fold rate < 0.5 OR pooled OOS trades <= 100 OR benchmark-relative excess CI includes zero OR net return worse than benchmark after costs

## Acceptance criteria
- Pre-register hypothesis in `research/hypotheses/commoditytrend_001.md` and minimal config in `config/commoditytrend_001.yaml` (freeze before evaluation). 
- Use only `data/raw/` (DBC.parquet, GLD.parquet). No external data/fetch.
- Run walk-forward evaluation with frozen design: 10y train / 12m test / 6m step, purge 21d, embargo 21d. Explicitly report number of folds and note power is limited.
- Apply actual costs (3.0 bp/unit). Report turnover, trade count, gross/net returns, benchmark-relative excess with bootstrap CI if feasible, Sharpe/Sortino, max DD.
- Do **not** add other commodities. Do **not** change promotion gates/thresholds.
- Produce `research/experiments/commoditytrend_001_evaluation.md` and `research/reports/commoditytrend_001_evaluation.md`.
- `git status --porcelain data/ config/` empty. Only new reports/experiments/hypotheses/config changed.
- `python -m pytest -q` passes or only pre-existing failures unchanged; report count.

## Scope boundaries
- **Narrow**: only DBC, GLD. Reject diversification to 2015-common-start set as underpowered.
- **Cost-realistic**: use engine cost model.
- **No re-opening** closed candidates.
- **Honest about power**: if folds < 5 or trades < 100, treat as insufficient power and do not promote; document clearly.

## Validation commands
- `python -m pytest -q`
- `git status --porcelain data/ config/`
- `git diff --stat`
