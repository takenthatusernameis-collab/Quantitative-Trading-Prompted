# Experiment: Walk-forward embargo sensitivity for `tsmomentum_spytrend_001` (tsmomentum_walkforward_embargo_001, Cycle 910)

## Hypothesis reference

- Candidate hypothesis: `research/hypotheses/tsmomentum_004.md` (Cycle 5 promoted candidate)
- Published walk-forward record: `research/experiments/tsmomentum_regime_filter_wf_001.md` (resolved by content)
- Frozen candidate definition: `research/run_cycle6.py` (the script that produced the published record; read, never changed)
- Pre-registered promotion gates: `AGENTS.md` and the published record's gate table (read, never changed)

## Objective

Quantify how much of the incumbent's published walk-forward evidence survives a non-overlapping (embargoed) fold design, publish the delta against the published protocol, and state whether the published gate outcome changes under Design A. Sensitivity only: the published protocol, the gates and every committed artifact are unchanged.

## Data

- Source: committed raw cache `data/raw/*.parquet` (cache-only; the fetcher is never called)
- Universe: SPY, QQQ, IWM, TLT, GLD, EFA, EEM
- Date range: 1993-01-01 to 2026-10-09
- Point-in-time treatment: signals use only data available at formation (weights shifted one day), the SPY SMA is computed point-in-time, and the overlay/cost model are applied on the same continuously computed path for every design
- Cost model: 1.0 bps commission + 2.0 bps slippage = 3.0 bps round-trip; risk-free rate 0.02 annual

## Configuration (consumed as-is, never inferred)

- Signal: TSMOM lookback 226, skip 21, top_fraction 0.5
- Risk overlay: vol-target 0.1 (lookback 63) + drawdown control 0.15
- Regime filter: SPY 200-day SMA trend filter
- Walk-forward (published design): train 10.0y / test 12.0m / step 6.0m, purge 21d, embargo 21d
- Gates (pre-registered): WF mean OOS Sharpe >= 0.9, positive fold rate >= 0.5, pooled OOS trades > 100

## Splits

- Published design: 48 folds, overlap 175.0 days, disjoint 24
- Design A (non-overlapping): 24 folds, overlap 0.0 days, disjoint 24
- Design B (literal embargo): 3 folds, overlap 0.0 days, disjoint 3

## Results

| Design | Folds | WF mean OOS Sharpe | Median | Std | Positive fold rate | Pooled OOS trades | Decision |
|---|---|---|---|---|---|---|---|
| Published | 48 | 0.947307 | 1.293299 | 3.479770 | 0.9167 | 6013 | Passes preliminary gates |
| Design A | 24 | 1.385035 | 1.420426 | 0.956605 | 0.9167 | 2952 | Passes preliminary gates |
| Design B | 3 | 1.634397 | 1.318150 | 0.810136 | 1.0000 | 551 | Passes preliminary gates |

- Published anchor reproduced: **YES** (published WF mean OOS Sharpe 0.9473, recomputed 0.9473)
- Delta (published -> Design A): folds 48 -> 24, mean OOS Sharpe 0.947307 -> 1.385035 (+0.437727), gate-1 margin +0.047307 -> +0.485035
- Gate-1 outcome changes under Design A: **NO**; published verdict (Credible Candidate) survives: **YES**
- Informational (canonical arithmetic scale, not a gate): published 1.514293, Design A 1.545868

## Independence diagnostic

| Design | Folds | Mean consecutive test-window overlap (days) | Max pairwise-disjoint test windows |
|---|---|---|---|
| Published | 48 | 175.0 | 24 |
| Design A | 24 | 0.0 | 24 |
| Design B | 3 | 0.0 | 3 |

## Trial count

- 1 measurement per design = 3 measurements on one shared path; fixed parameters, no per-fold re-optimisation, no robustness grid, no candidate selection.

## Reproduction

```bash
python research/tsmomentum_walkforward_embargo_audit.py
python -m pytest -q tests/test_tsmomentum_walkforward_embargo_audit.py
python -m pytest -q
git status --porcelain data/
git diff --stat src/ config/ research/experiments/ research/reports/
```
