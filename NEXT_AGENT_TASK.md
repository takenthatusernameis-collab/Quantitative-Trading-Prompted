# NEXT_AGENT_TASK.md

## Cycle 922 — Execute the pre-registered C3 csmomentum_001 baseline backtest + walk-forward (single config, no tuning) and label the result

### Context
Cycle 921 is complete and verified (committed as HEAD): the SMA-175 candidate (`tsmomentum_sma175_candidate`) was evaluated against the full promotion gate suite and is **rejected/failed** (NO-GO on `rolling_63d_sharpe` -0.448918 vs 0.9 and `psr` 0.896592 vs 0.95 at target 1.4178). The experiment record carries the explicit research label and quantified gate-reachability numbers (required Sharpe 1.665458, gap 0.057589, 5923 additional sessions, attainable YES), and `research/reports/opportunity_shortlist.md` carries the dated Cycle 921 addendum under the "TSMOM parameter variants" family. `research/tsmomentum_sma175_psr_reachability.py` reproduces every quoted number.

The opportunity shortlist (rank 2, 29/35, Exploratory signal) identifies **C3 long-only cross-sectional momentum (`csmomentum_001`, 18-ETF universe)** as the highest-ranked untested candidate and recommends documenting its hypothesis and pre-registering its evaluation plan BEFORE any backtest. That pre-registration already exists:

- `research/hypotheses/csmomentum_001.md` (v001, 2026-10-12, status PRE-REGISTERED): mechanism, expected direction/magnitude, holding horizon (~21d monthly), 18-asset universe, features/data sources, entry/exit rules, benchmarks (1/N equal-weight + incumbent TSMOM), confounders, falsification condition, cost model (3bps round-trip), evaluation plan, promotion gates, multiple-testing control (27-config grid fixed), reproduction commands, decision discipline.
- `config/csmomentum_candidate_001.yaml`: FROZEN baseline config (lookback 252, skip 21, top_fraction 0.5, monthly rebalance, signal lag 1 day, Close field, no risk overlay, chronological splits train 1993-01-01..2009-12-31 / validation 2010-01-01..2017-12-31 / test 2018-01-01..2026-10-09, walk-forward 10y train / 1y test / 6mo step / 21d purge & embargo, gates WF mean OOS Sharpe >= 0.9, positive fold rate >= 50%, pooled OOS trades > 100, plateau >= 2 of 3 lookbacks within 10%).

**No backtest has been executed for C3 yet.** Per AGENTS.md ("hypothesis first", "baseline before complexity") and the shortlist's recommendation, the next bounded step is to execute the **single pre-specified baseline configuration** (252/21/0.5) on the cached 18-ETF universe with chronological splits and walk-forward, evaluate the gates computable from a single configuration, label the result per AGENTS.md decision discipline, and publish a read-only experiment record. The 27-config robustness grid, DSR/PBO, plateau gate and any risk overlay are explicitly reserved for later cycles (per the hypothesis: baseline must clear gates first; no post-hoc configs).

### Objective
Run the C3 `csmomentum_001` baseline (one pre-specified configuration, no parameter search, no tuning) against the cached 18-ETF daily OHLCV, compute train/validation/test metrics and a walk-forward evaluation (10y train / 1y test / 6mo step, 21-day purge & embargo, fixed parameters across folds), evaluate the promotion gates computable from a single configuration (WF mean OOS Sharpe >= 0.9, positive fold rate >= 50%, pooled OOS trades > 100; plateau reported as NOT EVALUATED), label the result as one of credible candidate / exploratory signal / rejected/failed / blocked by data per AGENTS.md, and publish a read-only experiment record plus a regression test.

### Acceptance criteria
1. A new read-only tool (e.g. `research/csmomentum_baseline_eval.py`) executes the C3 baseline: reads prices **directly from `data/raw/*.parquet`** (never calls the fetcher, no network, no writes under `data/`), builds month-end cross-sectional momentum weights (lookback 252 / skip 21 / top_fraction 0.5 / equal-weight top 50% / 1-day signal lag), applies the 3 bps round-trip cost model from `config/settings.yaml`/`config/csmomentum_candidate_001.yaml`, runs train/validation/test splits and walk-forward exactly per `config/csmomentum_candidate_001.yaml`, and prints a machine-parseable summary (`SHARPE|...`, `GATE|...`, `DECISION|...`, etc.).
2. The tool reports: full-period Sharpe, max drawdown, rolling-63d Sharpe/DD, walk-forward mean OOS Sharpe, positive fold rate, pooled OOS trades, turnover, trade count, and each gate's PASS/FAIL; `plateau` reported as `NOT EVALUATED` (requires the 27-config grid, reserved); a final `Decision` (GO / NO-GO / INCONCLUSIVE) and a research label per AGENTS.md decision discipline.
3. A new regression test (e.g. `tests/test_csmomentum_baseline_eval.py`) asserts: the tool exits 0, prints its own structural checks as PASS, `data/` and `config/` are byte-identical before/after the run, the config is consumed as frozen (no modification), the baseline configuration matches `config/csmomentum_candidate_001.yaml` (252/21/0.5), results are bit-for-bit deterministic across two runs, and the walk-forward uses fixed parameters across folds (no per-fold re-optimization).
4. `config/promotion_gates.yaml`, `config/csmomentum_candidate_001.yaml`, `config/settings.yaml`, `research/hypotheses/csmomentum_001.md`, `research/run_cycle6.py` and all committed artifacts are **unchanged**; `git status --porcelain data/ config/` -> empty; `git diff --stat -- research/run_cycle6.py` -> empty.
5. Read-only w.r.t. market data and configuration: no new dependency, no network access, no live trading, no secrets; `fetch_universe` is never called.
6. The result is labeled per AGENTS.md decision discipline and the experiment record states the gate table, values, thresholds, failed gates, decision, and research label.

### Scope boundaries
- **Single configuration only**: lookback 252, skip 21, top_fraction 0.5 (the frozen baseline). Do NOT evaluate the 27-config robustness grid, do NOT search or tune parameters, do NOT add a risk overlay (vol-target / DD control / regime filter reserved for later cycles).
- Do not modify any gate, threshold, decision mapping, universe, cost model, Sharpe convention, hypothesis document, or config file.
- Do not modify `data/` or anything under `config/`. Do not call `fetch_universe`.
- Do not promote, deploy, or re-rank any candidate; do not re-score the shortlist.
- The plateau gate (>= 2 of 3 lookbacks within 10% of baseline) is NOT EVALUATED for the baseline and must be reported as such.
- The tool may write NEW files under `research/experiments/` / `research/reports/` / `tests/` only; it must not rewrite any tracked committed artifact (provide `--no-report` and a test asserting tracked artifacts are byte-identical if any existing artifact is touched).

### Validation commands
```bash
python research/csmomentum_baseline_eval.py
python -m pytest -q tests/test_csmomentum_baseline_eval.py
git status --porcelain data/ config/
git diff --stat -- research/run_cycle6.py
```

### Evidence artifacts
- New read-only tool `research/csmomentum_baseline_eval.py` (baseline backtest + walk-forward + gate evaluation + decision/label).
- New experiment record `research/experiments/csmomentum_baseline_eval_001.md` (gate table, values, thresholds, failed gates, decision, research label).
- New regression test `tests/test_csmomentum_baseline_eval.py`.
- Reproduction commands and observed outputs of the validation commands above.

### Handoff (for the cycle after)
- Changed: new read-only C3 baseline evaluation tool, its experiment record, and its regression test.
- Verified: tool runs exit 0 with structural checks PASS; target tests pass; `data/`/`config/` untouched; results deterministic across two runs; baseline config matches the frozen `config/csmomentum_candidate_001.yaml`.
- Unresolved: none for this cycle (the baseline result itself is the output; if gates fail the candidate is labeled rejected/failed and the next cycle moves to the next shortlist candidate or documents the failure).
- Failed approaches: none yet (this is the first C3 execution).
- Next task: Cycle 922 as specified above.
