# Next Agent Task: Cycle 13 - Baseline Backtest & Walk-Forward for Cross-Sectional Momentum (csmomentum_001)

## Context

Cycle 12 completed the pre-registration for Candidate C3 (Long-only cross-sectional momentum, broad 18-ETF universe):
- Hypothesis documented: `research/hypotheses/csmomentum_001.md` (all AGENTS.md fields, falsification condition pre-stated)
- Frozen configuration committed: `config/csmomentum_candidate_001.yaml` (27-config robustness grid, baseline = 252/21/0.5)
- Evaluation plan pre-registered: chronological splits (train ≤2009, val 2010-2017, test 2018-2026), walk-forward (10yr/1yr/6mo, 21d purge/embargo), promotion gates (WF mean OOS Sharpe ≥0.9, ≥50% positive folds, >100 pooled OOS trades, parameter plateau ≥2/3 lookbacks within 10%)

**No backtest has been executed.** Cycle 13 executes the pre-registered evaluation.

---

## Objective

Execute the **baseline backtest and walk-forward evaluation** for `csmomentum_001` using the frozen configuration. Produce evidence artifacts and a go/no-go decision per the pre-registered promotion gates.

---

## Acceptance Criteria

### 1. Baseline Backtest (Test Period: 2018-01-01 to 2026-10-09)

Run the baseline configuration (lookback=252, skip=21, top_fraction=0.5, no risk overlay, 3bps costs, 1-day lag, monthly rebalance) on the test period. Output:
- `data/processed/simulation_csmomentum_001.parquet` — daily net/gross returns, costs, turnover, exposure, positions, weights
- `data/processed/trades_csmomentum_001.parquet` — trade log
- `data/processed/weights_csmomentum_001.parquet` — point-in-time weights

Report: Net Sharpe, Sortino, CAGR, max DD, profit factor, annualized turnover, avg exposure, trade count, tail metrics (95% VaR, CVaR).

### 2. Walk-Forward Evaluation (48 Folds, Fixed Parameters)

Match Cycle 6 design exactly (`research/experiments/tsmomentum_regime_filter_wf_001.md`):
- 10-year train, 1-year test, 6-month step, 21-day purge, 21-day embargo
- Fixed parameters across all folds (NO re-optimization)
- Per-fold metrics: test Sharpe, ann. return, max DD, trades
- Aggregate: mean OOS Sharpe, std, median, % positive folds, total pooled OOS trades

### 3. Robustness Grid Evaluation (27 Pre-Specified Configs)

Evaluate all 27 combinations from the frozen config on the **test period** (2018-2026):
- lookback ∈ {189, 252, 315}
- skip ∈ {21, 42}
- top_fraction ∈ {0.3, 0.5, 0.7}

Output: heatmap table (test Sharpe per config), baseline rank, plateau check (≥2 of 3 lookbacks within 10% of baseline test Sharpe at skip=21, top_fraction=0.5).

### 4. Benchmark Comparison

Evaluate both benchmarks on the identical test period and walk-forward folds:
- **1/N Equal-Weight (18 ETFs)**: monthly rebalance, 1-day lag, 3bps costs
- **Incumbent TSMOM (tsmomentum_spytrend_001)**: core 7, vol-target 10%, DD control 15%, SPY 200d SMA, 3bps costs

Report: net excess Sharpe, excess return, correlation, benchmark-relative drawdowns.

### 5. Multiple-Testing Control

- Compute Deflated Sharpe Ratio via `src/evaluation/statistics.py:compute_dsr` (N=27 trials)
- Compute PBO/CSCV if available
- Document: no configuration selected on test-period results

### 6. Experiment Record

Create `research/experiments/csmomentum_baseline_wf_001.md` with:
- Hypothesis reference (`csmomentum_001`)
- Data used (source, range, universe, point-in-time)
- Configuration (baseline + full 27-grid)
- Train/val/test splits, walk-forward design
- All results (baseline, WF folds, grid, benchmarks, DSR)
- Promotion-gate verdict (PASS/FAIL per gate)
- Reproduction command: `python3 research/run_cycle13.py`
- Code revision

### 7. Decision & Next Task

Label result per AGENTS.md:
- **Credible candidate** → Cycle 14: risk overlay exploration (vol-target, DD control, regime filter)
- **Exploratory signal** → Cycle 14: limited follow-up (e.g., test alternative grid configs)
- **Rejected/Failed** → Document falsification, Cycle 14: next shortlist candidate (C4 Sector rotation)
- **Blocked** → Document blocker

Prepare `NEXT_AGENT_TASK.md` for Cycle 14.

---

## Validation Commands

```bash
# Baseline artifacts exist
test -f data/processed/simulation_csmomentum_001.parquet
test -f data/processed/trades_csmomentum_001.parquet
test -f data/processed/weights_csmomentum_001.parquet

# Experiment record exists with required sections
test -f research/experiments/csmomentum_baseline_wf_001.md
grep -q "Walk-Forward" research/experiments/csmomentum_baseline_wf_001.md
grep -q "Robustness Grid" research/experiments/csmomentum_baseline_wf_001.md
grep -q "Promotion" research/experiments/csmomentum_baseline_wf_001.md
grep -q "Deflated Sharpe" research/experiments/csmomentum_baseline_wf_001.md
grep -q "Benchmark" research/experiments/csmomentum_baseline_wf_001.md

# Reproduction command works
python3 research/run_cycle13.py 2>&1 | tail -5

# Prior cycles still run
python3 research/run_cycle7.py 2>&1 | tail -3
python3 research/run_cycle11.py 2>&1 | tail -3

# Lint
python3 -m ruff check research/ config/ 2>/dev/null || true
```

---

## Scope Boundaries

- **DO NOT** modify `config/csmomentum_candidate_001.yaml` or `research/hypotheses/csmomentum_001.md` (frozen pre-registration)
- **DO NOT** add risk overlays (vol-target, DD control, regime filter) — reserved for Cycle 14+ ONLY if baseline clears gates
- **DO NOT** test configurations outside the pre-specified 27-grid
- **DO NOT** select configurations based on test-period results
- **DO NOT** fetch new data or add dependencies
- Use existing infrastructure: `src/features/momentum.py` (rank_assets, select_top_decile, build_weights), `src/backtest/engine.py`, `src/evaluation/statistics.py`

---

## Evidence Reference

- Pre-registered hypothesis: `research/hypotheses/csmomentum_001.md`
- Frozen config: `config/csmomentum_candidate_001.yaml`
- Cycle 11 shortlist (C3=29/35): `research/reports/opportunity_shortlist.md`
- Cycle 6 WF design: `research/experiments/tsmomentum_regime_filter_wf_001.md`
- Cycle 3 robustness caveat: `research/experiments/tsmomentum_robustness_001.md`
- Ranking machinery: `src/features/momentum.py`
- Backtest engine: `src/backtest/engine.py`
- Evaluation stats: `src/evaluation/statistics.py`
- AGENTS.md: "Baseline before complexity", "Independent evaluation", "Honest accounting", "Promotion gate"

---

## Implementation Notes

The baseline signal is long-only cross-sectional momentum:
1. Load 18 ETF Close prices from `data/raw/*.parquet`
2. Compute momentum via `compute_momentum(prices, lookback=252, skip=21)`
3. Rank cross-sectionally via `rank_assets(momentum)`
4. Select top 50% via `select_top_decile(momentum, top_fraction=0.5)`
5. Build equal-weight weights via `build_weights(...)` (includes 1-day shift)
6. Run simulation via `src/backtest/engine.py` with 3bps costs, monthly rebalance
7. Evaluate via `src/evaluation/statistics.py`

Walk-forward: use the same engine with rolling windows, fixed params, purge/embargo.