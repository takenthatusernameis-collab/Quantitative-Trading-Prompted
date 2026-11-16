# Experiment: fold_sharpe_degeneracy_audit (Cycle 930)

**Hypothesis reference:** none (measurement cycle).

**Objective:** decide whether the point-in-time-complete gate-1 FAIL reported by
the Cycle-929 inventory is a broad performance gap or the effect of a single
degenerate fold, by measuring each fold's exposure and volatility.

## Data used

- **Source:** committed parquet cache `data/raw/` (universe SPY, QQQ, IWM, TLT, GLD, EFA, EEM); the fetcher is never called.
- **Range:** the incumbent's published walk-forward (48 folds) on the continuously computed point-in-time path.
- **Point-in-time treatment:** momentum (226-session lookback, skip 21) and the SPY 200-session SMA overlay are the committed ones (`src/features/momentum.py`, `research/run_cycle6.py`).
- **Cost model:** 1.0 bps commission + 2.0 bps slippage = 3.0 bps per unit of weight change; risk-free 2.00% annual (unchanged, from `src/backtest/engine.py`).

## Configuration

- **Candidate:** `tsmomentum_spytrend_001`.
- **Degeneracy rule (pre-registered):** `ann_vol < 0.01` or `active_days <= 2`.
- **Promotion gate 1:** mean OOS Sharpe >= 0.9.
- **Rule robustness (separation-based, not floor-distance):** fold 12 sits ~10x below the volatility floor (`ann_vol` 0.000973) while the next-lowest non-degenerate fold is ~3.6x above it (`ann_vol` 0.036173), a ~37x separation, so the measured outcome is insensitive to the exact threshold anywhere inside that gap.

## Results

| Quantity | Value |
|---|---|
| Degenerate folds | 12 |
| Fold 12 sessions / cash / active / non-zero | 244 / 243 / 1 / 2 |
| Fold 12 annualized volatility | 0.000973 |
| Fold 12 recomputed Sharpe | -21.829879 |
| Complete-subsample gate 1 (41 folds) | 0.787522 -> FAIL |
| Complete-subsample gate 1 without degenerate folds (40 folds) | 1.352958 -> PASS |

## Number of trials

1 (a measurement: no parameter search, no candidate generation, no re-tuning). The bootstrap uses the same 2000 moving-block draws and seed as the Cycle-929 inventory.

## Reproduction commands

```bash
python research/fold_sharpe_degeneracy_audit.py
python -m pytest -q tests/test_fold_sharpe_degeneracy_audit.py
git status --porcelain data/ config/
```
