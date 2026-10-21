# Experiment: Like-for-like mechanism comparison (mechanism_comparison_001)

**Cycle 931.**

## Hypothesis reference

This is a **measurement cycle**, not a candidate cycle. It has no new
hypothesis of its own: it re-measures the incumbent
`tsmomentum_spytrend_001`, the rejected `riskparity_001` candidate and
the 1/N benchmark on **one** point-in-time-complete window under **one**
walk-forward design and **one** cost model, and states each mechanism's
incremental value over 1/N. The inputs are the committed records:

- `research/experiments/tsmomentum_regime_filter_wf_001.md` (the published 48-fold walk-forward record and the 0.947307 headline);
- `research/hypotheses/riskparity_001.md` and `research/experiments/riskparity_001_evaluation.md` (the pre-registered candidate and its Cycle-930 rejection);
- `research/experiments/tsmomentum_benchmark_001.md` (the 0.4716 1/N reference);
- `research/reports/data_cost_inventory_002.md` (the Cycle-929 point-in-time membership audit and the 0.787522 complete-cross-section figure).

## Data used

- **Source**: the committed parquet cache `data/raw/` (the fetcher is never called).
- **Universe**: SPY, QQQ, IWM, TLT, GLD, EFA, EEM.
- **Window**: 2006-02-15 .. 2026-05-28 (41 folds; the panel itself starts 1993-01-29 and ends 2026-10-19).
- **Frequency**: daily, weekdays, forward-filled onto the union calendar.

## Point-in-time treatment

- The incumbent's momentum selection uses only data available at formation (226-session lookback skipping the most recent 21 sessions); the SPY trend overlay uses a 200-session moving average.
- The `riskparity_001` weights use a **lagged** volatility estimate (the trailing window ends at t-1), so no same-session feedback is possible.
- A fold is *point-in-time complete* only when all seven members carry a valid momentum on **every** session of its test window; the 7 folds that fail this test are excluded and the remaining folds are the measurement window for all three paths.
- No constituent-level membership exists in the repository and none is modelled; the asset-level membership is measured, as in Cycle 929.

## Configuration

| Item | Value |
|---|---|
| Walk-forward design | 10-year rolling train, 12-month test, 6-month step, 21-day purge, 21-day embargo (the published design) |
| Folds | 41 |
| Cost model | 1.0 bp commission + 2.0 bp slippage = 3.0 bp per unit of weight change |
| Risk-free rate | 0.02 annual |
| Incumbent | momentum selection (lookback 226, skip 21, top fraction 0.5) + SPY 200-session trend overlay |
| `riskparity_001` | pre-registered baseline: lagged 63-session inverse volatility, cap 0.3 |
| 1/N benchmark | equal weight over the seven ETFs, constant weights |
| Bootstrap | moving block, block 5, seed 20240101, draws 2000, 1000 |

## Number of trials

**1** — this cycle searches nothing. The `riskparity_001` path is the pre-registered baseline of the Cycle-930 grid (9 configurations, declared N = 9, already evaluated and rejected); the incumbent is the published path; the benchmark is the benchmark.

## Results

| Path | WF mean OOS Sharpe (backtest) | WF mean OOS Sharpe (canonical) | Positive folds | Pooled OOS trades | Gate 1 | Gate 2 | Gate 3 | Excess over 1/N | 95% CI (2000 draws) |
|---|---|---|---|---|---|---|---|---|---|
| Incumbent `tsmomentum_spytrend_001` | 0.787524 | 1.443935 | 0.902439 | 4884 | 0.787524 >= 0.900000 -> FAIL | 0.902439 >= 0.500000 -> PASS | 4884.000000 > 100.000000 -> PASS | 0.183963 | [-0.906068, 0.839629] |
| `riskparity_001` baseline (L = 63, cap = 0.30) | 0.642829 | 0.813226 | 0.780488 | 474 | 0.642829 >= 0.900000 -> FAIL | 0.780488 >= 0.500000 -> PASS | 474.000000 > 100.000000 -> PASS | 0.039267 | [0.006458, 0.079121] |
| 1/N equal weight (7 ETFs) | 0.603562 | 0.764690 | 0.756098 | 0 | 0.603562 >= 0.900000 -> FAIL | 0.756098 >= 0.500000 -> PASS | 0.000000 > 100.000000 -> FAIL | - | - |

## Decision

**Exploratory signal** — at least one mechanism's excess over 1/N is statistically supported, but no mechanism clears the 0.9 walk-forward gate on the point-in-time-complete window.

The label applies to the incremental-value comparison only. The incumbent's published verdict is unchanged (a Credible Candidate by its published verdict and NO-GO for promotion) and `riskparity_001` remains rejected.

## Reproduction commands

```bash
python research/mechanism_comparison_001.py
python -m pytest -q tests/test_mechanism_comparison_001.py
git status --porcelain data/ config/
```
