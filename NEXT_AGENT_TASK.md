# Next Agent Task: Cycle 15 - Baseline Backtest & Walk-Forward for Sector Rotation (sectorrotation_001)

## Context

Cycle 14 pre-registered Candidate C4 (`sectorrotation_001`,
long-only cross-sectional momentum across the 9 GICS sector
ETFs XLB–XLY) following the Cycle 12 → Cycle 13 structure:
hypothesis document (`research/hypotheses/sectorrotation_001.md`)
and frozen configuration (`config/sectorrotation_candidate_001.yaml`)
are complete. **No backtest has been executed for C4.**

Cycle 14 corrected the Cycle 13 pre-registration defect: the
robustness grid is labeled by its true product,
**3 lookbacks x 2 skips x 3 top-fractions = 18 unique
configurations** (not the mislabeled "27"), and the walk-forward
fold count for the 1998-12-22 history start is **36 folds**
(verified via `generate_walkforward_splits`; the C3 48-fold count
does not apply to this universe).

Key evidence Cycle 15 must respect:
- C3 (broad 18-ETF universe CONTAINING these 9 sectors) was
  **Rejected/Failed** in Cycle 13: WF mean OOS Sharpe 0.6868 < 0.9
  gate, baseline ranked 17/18 on its grid, DSR negative at N=27
  and N=18. This is direct prior evidence against the cross-sectional
  rank signal in this dataset and lowers the C4 prior.
- The incumbent TSMOM (`tsmomentum_spytrend_001`) remains the
  credible benchmark: test Sharpe 1.4178, WF mean 0.9473.
- The C4 prior (gross 0%–2% excess over 1/N) is explicitly lower
  than C3's was (1%–4%).

---

## Objective

Execute the pre-registered evaluation of Candidate C4 exactly as
frozen in `config/sectorrotation_candidate_001.yaml` and
`research/hypotheses/sectorrotation_001.md`, mirroring the
Cycle 13 execution (`research/run_cycle13.py` →
`research/experiments/csmomentum_baseline_wf_001.md`):

1. Baseline backtest on the test period (2018-01-01 to 2026-10-09)
2. Walk-forward evaluation (36 folds, fixed parameters, 10yr/1yr/6mo,
   21-day purge/embargo)
3. Robustness grid: all **18** pre-specified configurations on the
   test period
4. Benchmark comparison: 1/N equal-weight (9 sector ETFs) and the
   incumbent TSMOM on identical periods/folds
5. Multiple-testing control: DSR at the true count N=18, PSR, PBO/CSCV
6. Promotion-gate verdict and pre-registered classification

---

## Acceptance Criteria

### 1. Evaluation Script

Create `research/run_cycle15.py` mirroring `research/run_cycle13.py`
(reuse its helpers: `_apply_monthly_schedule`, `_net_returns`,
`eval_config`, `eval_config_period`, `eval_equal_weight` over the
9-sector universe, `eval_incumbent` with both warmup conventions,
`_benchmark_comparison`, `_tail_metrics`, `_build_trade_log`,
report generation). Mandatory pre-execution assertions:

```python
assert len(LOOKBACKS) * len(SKIPS) * len(TOP_FRACTIONS) == 18  # grid label = product
assert len(generate_walkforward_splits("1998-12-22", "2026-10-09",
                                       10.0, 12.0, 6.0, 21, 21)) == 36  # actual folds
```

### 2. Execution Conventions (frozen, pre-registered)

- Universe: XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY
  (cache-only, `fetch_universe(..., force=False)`; no new data)
- Baseline: lookback=252, skip=21, top_fraction=0.5, monthly
  month-end rebalance, 1-day signal lag, Close prices, 3bps
  round-trip costs (1bps commission + 2bps slippage), rf 2%
- NO risk overlays (baseline before complexity)
- NO configuration selected on test-period results; grid is
  diagnostic (plateau + multiple-testing control) only
- Data integrity re-verified at runtime: 9/9 files, 6,991 rows,
  100% Close completeness, content hash `5e2d48e6579a53cd`

### 3. Walk-Forward

- 36 folds (assert the generated count equals 36 — document the
  actual count; do NOT force 48)
- Fixed parameters across folds (no per-fold re-optimization)
- Fold 1: train 1998-12-22 → 2008-08-18, test 2008-09-17 → 2009-09-03
- Fold 36: train 2015-11-17 → 2025-07-14, test 2025-08-13 → 2026-07-30

### 4. Benchmarks (identical periods/folds, identical cost model)

- 1/N equal-weight over the 9 sector ETFs (note the zero-turnover
  convention caveat, identical to C3's)
- Incumbent TSMOM with validated overlay-warmup conventions:
  "slice" for the test period (reproduces the Cycle 7 record:
  test Sharpe 1.4178), "full" for the WF folds (reproduces the
  Cycle 6 fold record: WF mean 0.9473). Verify both reproduce the
  prior records; report any deviation.

### 5. Multiple-Testing Control

- DSR via `src/evaluation/statistics.py:compute_dsr` at **N=18**
  (the true count; there is no pre-registered/evaluated count
  discrepancy this cycle — do not invent one)
- PSR vs SR=0 and vs the 0.9 gate; block-bootstrap 95% CI
  (1000 samples, block=22d, seed=42)
- PBO via `compute_pbo` over the 18-config grid (train=1998-2009
  vs test=2018-2026); report degenerate-case handling as in Cycle 13
  if all configs have positive test Sharpe

### 6. Promotion Gates & Classification

| Gate | Threshold |
|------|-----------|
| WF mean OOS Sharpe >= 0.9 | primary |
| Positive fold rate >= 50% | |
| Pooled OOS trades > 100 | |
| Plateau: >= 2 of 3 lookbacks within max(0.1, 10%×\|baseline\|) of baseline test Sharpe (skip=21, tf=0.5) | |

Pre-registered falsification: WF mean OOS Sharpe < 0.9 OR < 50%
positive folds → **Rejected/Failed**. Apply the pre-registered
decision discipline labels exactly (credible candidate / exploratory
signal / rejected-failed / blocked).

### 7. Artifacts

- `data/processed/simulation_sectorrotation_001.parquet`
- `data/processed/trades_sectorrotation_001.parquet`
- `data/processed/weights_sectorrotation_001.parquet`
- Experiment record `research/experiments/sectorrotation_baseline_wf_001.md`
  (mirror `csmomentum_baseline_wf_001.md` structure: hypothesis
  reference, data used with integrity table, configuration with the
  grid-arithmetic disclosure, splits/WF design, baseline backtest,
  per-fold WF table, grid heatmap + full results + plateau check,
  benchmark comparison, multiple-testing control, promotion-gate
  verdict, reproducibility, code revision)
- Update `README.md` Current Status to Cycle 15

### 8. Next Task

Write `NEXT_AGENT_TASK.md` for Cycle 16 following the
pre-registered decision tree:
- If Rejected/Failed → pre-register the next shortlist candidate
  (C6 Calendar/rebalancing effects, 26/35) OR document the
  cross-sectional-momentum mechanism as rejected in this dataset
  (C3 and C4 both failed) and move to the next distinct mechanism
  family on the shortlist.
- If gates pass → risk-overlay exploration on the validated baseline
  (vol-target/DD control), pre-registered first.

---

## Validation Commands

```bash
# Experiment record exists with required sections
test -f research/experiments/sectorrotation_baseline_wf_001.md
grep -q "Promotion-Gate Verdict" research/experiments/sectorrotation_baseline_wf_001.md
grep -q "18" research/experiments/sectorrotation_baseline_wf_001.md

# Frozen pre-registration still parses and is unmodified
python3 -c "import yaml; yaml.safe_load(open('config/sectorrotation_candidate_001.yaml'))"

# Full Cycle 15 evaluation (regenerates all artifacts and the record)
python3 research/run_cycle15.py 2>&1 | tail -5

# Artifacts exist
test -f data/processed/simulation_sectorrotation_001.parquet
test -f data/processed/trades_sectorrotation_001.parquet
test -f data/processed/weights_sectorrotation_001.parquet

# Prior cycles still run
python3 research/run_cycle13.py 2>&1 | tail -3
python3 research/run_cycle7.py 2>&1 | tail -3
```

---

## Scope Boundaries

- **DO NOT** modify `research/hypotheses/sectorrotation_001.md` or
  `config/sectorrotation_candidate_001.yaml` (frozen pre-registration)
  — execute them as specified
- **DO NOT** modify `config/csmomentum_candidate_001.yaml`,
  `research/hypotheses/csmomentum_001.md`, or
  `research/experiments/csmomentum_baseline_wf_001.md` (frozen C3
  pre-registration and completed experiment record)
- **DO NOT** add post-hoc configurations, weaken promotion gates,
  or select configurations on test-period results
- **DO NOT** add risk overlays, fetch new data, or add dependencies
- **DO NOT** force the fold count to 48 — the 1998-12-22 start
  yields 36 folds; assert and document the actual count
- **DO NOT** invent grid counts — the grid label must equal the
  product (18 = 3 x 2 x 3); assert it
- **DO NOT** run live trading or access credentials (research only)

---

## Evidence Reference

- Cycle 14 pre-registration (C4):
  `research/hypotheses/sectorrotation_001.md`,
  `config/sectorrotation_candidate_001.yaml`
- Cycle 13 execution template (C3 evaluation):
  `research/run_cycle13.py`,
  `research/experiments/csmomentum_baseline_wf_001.md`
- Cycle 11 shortlist (C4 = 28/35, rank 3 — Exploratory signal):
  `research/reports/opportunity_shortlist.md`
- Cycle 6 WF design: `research/experiments/tsmomentum_regime_filter_wf_001.md`
- Cycle 7 incumbent test-period record (benchmark reproduction target:
  test Sharpe 1.4178)
- Ranking machinery: `src/features/momentum.py`
- Backtest engine: `src/backtest/engine.py`
- Evaluation stats: `src/evaluation/statistics.py` (seeded bootstrap,
  seed=42 convention)
- Walk-forward: `src/evaluation/walkforward.py:generate_walkforward_splits`
- AGENTS.md: "Hypothesis first", "Baseline before complexity",
  "Independent evaluation", "Multiple-testing control", "Honest accounting"

---

## Implementation Notes

- The C4 universe (9 sector ETFs) is a subset of C3's 18-ETF
  universe. The experiment record must explicitly compare the C4
  result against C3's rejection evidence (same mechanism, narrower
  universe) and state whether the sector restriction changed the
  outcome.
- The 9-sector union calendar ends 2026-10-08 (repo convention
  END_DATE is 2026-10-09); the engine aligns onto the universe's
  own calendar. Document the effective test window.
- Momentum warmup: first fully-valid signal date is 2000-01-24 for
  the baseline (252, 21) and 2000-05-23 for (315, 42); pre-warmup
  dates carry no positions (point-in-time, no back-fill).
- With 9 assets, `select_top_decile` holds 3/5/7 sectors at
  top_fraction 0.3/0.5/0.7 — document concentration.
- The 1/N benchmark over 9 ETFs, represented as constant 1/9 target
  weights with 1-day lag and the monthly calendar, implies zero
  observed turnover and zero cost drag within the engine's
  exogenous-weights framework (mild upward bias; noted as a
  limitation, identical to the C3 convention).
- Determinism: backtest, walk-forward, grid, and benchmark
  computations are deterministic (no RNG); bootstrap statistics use
  seed=42.
- Report ALL metrics honestly, including negative results. If the
  falsification condition is met, label Rejected/Failed — do not
  tune to clear the gate.

---

## Verification Checklist (pre-registration integrity)

Before executing the backtest, confirm:
- [ ] Grid assertion present: `3 x 2 x 3 == 18`
- [ ] Fold-count assertion present: `generate_walkforward_splits(...) == 36`
- [ ] DSR computed at N=18 (true count)
- [ ] Baseline parameters are the pre-registered (252, 21, 0.5)
- [ ] Benchmarks: 1/N (9 ETFs) + incumbent TSMOM (slice/full)
- [ ] Cache-only data load (no network fetch)
- [ ] Promotion gates unchanged from the frozen config
