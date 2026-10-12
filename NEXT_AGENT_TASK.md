# Next Agent Task: Cycle 14 - Pre-Registration for Sector Rotation (sectorrotation_001)

## Context

Cycle 13 executed the pre-registered evaluation of Candidate C3
(`csmomentum_001`, long-only cross-sectional momentum, broad 18-ETF
universe). The **pre-registered falsification condition was met**:
walk-forward mean OOS Sharpe 0.6868 < 0.9 gate (79.2% positive folds,
313 pooled OOS trades, plateau 2/3 all passed, but gate 1 failed).
Verdict: **Rejected/Failed** (`research/experiments/csmomentum_baseline_wf_001.md`).

Key evidence from Cycle 13 that Cycle 14 must respect:
- Baseline (252/21/0.5, monthly rebalance) test Sharpe 0.4101, rank 17/18
  on the pre-specified grid; DSR negative at both N=27 (pre-registered)
  and N=18 (evaluated).
- CS momentum was dominated by both benchmarks: 1/N equal-weight
  (test Sharpe 0.4617) and the incumbent TSMOM (test Sharpe 1.4178,
  WF mean 0.9473 — both reproduced exactly, verifying the Cycle 13
  benchmark implementation against the Cycle 6/7 records).
- The broad 18-ETF universe (which CONTAINS the 9 sector ETFs) failed
  the walk-forward gate. This is direct prior evidence against the
  cross-sectional rank signal in this dataset and must lower the C4 prior.

**No new backtest is executed in Cycle 14.** Cycle 14 pre-registers the
next shortlist candidate (C4 Sector rotation) following the Cycle 12
pre-registration structure.

---

## Objective

Pre-register Candidate C4 (sector rotation: cross-sectional momentum
across the 9 GICS sector ETFs) with a complete hypothesis document,
frozen configuration, and pre-registered evaluation plan. Mirror the
Cycle 12 → Cycle 13 structure: Cycle 14 = pre-registration, Cycle 15 =
evaluation.

---

## Acceptance Criteria

### 1. Hypothesis Document

Create `research/hypotheses/sectorrotation_001.md` with ALL AGENTS.md
fields:
- Mechanism description (sector leadership persistence with the business
  cycle; staggered information diffusion across sectors)
- Expected direction and magnitude (pre-specified prior, explicitly
  conditioned on C3's rejection — the prior must be LOWER than C3's
  was, since the broad universe containing these sectors failed)
- Holding horizon (~21 trading days, monthly)
- Asset universe: XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY
  (all cached in `data/raw/*.parquet`, inception 1998-12-22, ~28
  years common history)
- Features and data sources (Close prices, `compute_momentum`,
  `rank_assets`, `select_top_decile`, `build_weights`)
- Entry/exit rules (long-only top fraction, equal-weight, 1-day lag,
  monthly month-end rebalance, 3bps round-trip costs)
- Benchmark (1/N equal-weight over the 9 sector ETFs; incumbent
  TSMOM `tsmomentum_spytrend_001` on its core 7)
- Known confounders (narrow 9-asset universe limits cross-sectional
  breadth; C3 rejection on the superset universe; ETF-level only;
  flat cost model; no risk overlay in baseline)
- **Falsification condition pre-stated BEFORE any backtest**:
  WF mean OOS Sharpe < 0.9 OR < 50% positive folds → Rejected/Failed
  (same gate structure as C3)
- Cost model assumptions (identical to C3: 1bps commission + 2bps
  slippage, rf 2%)
- Pre-registered evaluation plan (chronological splits, walk-forward
  design, promotion gates, multiple-testing control)

### 2. Frozen Configuration

Create `config/sectorrotation_candidate_001.yaml` mirroring
`config/csmomentum_candidate_001.yaml`:
- candidate_id, universe (9 sector ETFs), signal defaults, cost model,
  execution (signal_lag_days: 1, price_field: Close,
  rebalance_schedule: monthly), history_start: "1998-12-22",
  evaluation metadata (splits, walk-forward, promotion gates,
  multiple-testing)

### 3. Robustness Grid — Correct Arithmetic (MANDATORY)

The grid label MUST equal the actual product of the parameter values.
Cycle 13 disclosed a pre-registration defect: C3's documents labeled
the grid "27 configurations" while the specified values
(3 x 2 x 3) yield **18** unique combinations. For C4, state the
grid as "lookback {189, 252, 315} x skip {21, 42} x top_fraction
{0.3, 0.5, 0.7} = **18 unique configurations**" (or choose a grid
whose label equals its product) and verify the count with an explicit
assertion in the Cycle 15 evaluation script.

### 4. Evaluation Plan (pre-registered, executed in Cycle 15)

- Chronological splits: train ≤2009 (1998-2009), validation
  2010-2017, test 2018-01-01 to 2026-10-09
- Walk-forward: 10-year train / 1-year test / 6-month step / 21-day
  purge / 21-day embargo, fixed parameters, no re-optimization
  (note: the 1998 start yields ~35 folds, not 48 — document the
  actual fold count; do NOT force 48)
- Promotion gates: WF mean OOS Sharpe >= 0.9; >= 50% positive folds;
  > 100 pooled OOS trades; plateau >= 2 of 3 lookbacks within 10% of
  baseline test Sharpe at skip=21, top_fraction=0.5
- Multiple-testing control: DSR via `src/evaluation/statistics.py:compute_dsr`
  at the grid's true count; PSR; PBO via `compute_pbo`
- Benchmarks on identical periods/folds: 1/N (9 ETFs) and incumbent
  TSMOM (validated overlay-warmup conventions: "slice" for test
  period, "full" for WF folds — see Cycle 13's verified implementation)

### 5. Next Task

Write `NEXT_AGENT_TASK.md` for Cycle 15 (evaluation execution,
mirroring the Cycle 13 task structure).

---

## Validation Commands

```bash
# Hypothesis document exists with all required sections
test -f research/hypotheses/sectorrotation_001.md
grep -q "Falsification Condition" research/hypotheses/sectorrotation_001.md
grep -q "Promotion Gates" research/hypotheses/sectorrotation_001.md
grep -q "Known Confounders" research/hypotheses/sectorrotation_001.md

# Frozen config parses
python3 -c "import yaml; yaml.safe_load(open('config/sectorrotation_candidate_001.yaml'))"

# Grid arithmetic: label equals product of parameter values
python3 - <<'PY'
import yaml
cfg = yaml.safe_load(open('config/sectorrotation_candidate_001.yaml'))
# extract grid values and assert the stated count equals the product
print("config OK")
PY

# Prior cycles still run
python3 research/run_cycle13.py 2>&1 | tail -3
python3 research/run_cycle7.py 2>&1 | tail -3
```

---

## Scope Boundaries

- **DO NOT** run any backtest or simulation in Cycle 14 (evaluation is
  Cycle 15's job; pre-registration must precede execution)
- **DO NOT** modify `config/csmomentum_candidate_001.yaml`,
  `research/hypotheses/csmomentum_001.md`, or
  `research/experiments/csmomentum_baseline_wf_001.md` (frozen
  pre-registration and completed experiment record)
- **DO NOT** add risk overlays, fetch new data, or add dependencies
- **DO NOT** invent grid counts: the grid label must equal the product
  of the parameter value counts
- **DO NOT** weaken the promotion gates (WF mean OOS Sharpe >= 0.9
  stays; it is the AGENTS.md screening gate)

---

## Evidence Reference

- Cycle 13 experiment record (C3 rejection):
  `research/experiments/csmomentum_baseline_wf_001.md`
- Cycle 12 pre-registration template (C3):
  `research/hypotheses/csmomentum_001.md`,
  `config/csmomentum_candidate_001.yaml`
- Cycle 11 shortlist (C4 = 25/35, Exploratory signal):
  `research/reports/opportunity_shortlist.md`
- Cycle 6 WF design: `research/experiments/tsmomentum_regime_filter_wf_001.md`
- Ranking machinery: `src/features/momentum.py`
- Backtest engine: `src/backtest/engine.py`
- Evaluation stats: `src/evaluation/statistics.py` (seeded bootstrap,
  see Cycle 13's `seed=42` convention)
- AGENTS.md: "Hypothesis first", "Baseline before complexity",
  "Independent evaluation", "Multiple-testing control"

---

## Implementation Notes

- The C4 universe (9 sector ETFs) is a subset of C3's 18-ETF universe.
  The hypothesis document must explicitly address why a sector-restricted
  cross-sectional signal can succeed where the broad-universe signal
  failed (e.g., purer business-cycle leadership signal without
  cross-asset-class rank noise), or acknowledge that C4 is a
  lower-prior variant of the same mechanism.
- Data integrity: verify all 9 sector parquet files have 100% Close
  completeness over the common 1998-12-22 to 2026-10-09 range before
  freezing the config.
- Uncertainty discipline: the falsification condition and promotion
  gates are fixed; no post-hoc gate adjustments are permitted.
