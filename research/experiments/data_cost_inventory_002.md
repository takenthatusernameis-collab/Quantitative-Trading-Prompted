# Experiment: data_cost_inventory_002 (Cycle 929)

**Hypothesis reference:** none (measurement cycle).

**Objective:** refresh the repository's data and cost inventory from the
committed tree, verify the published Cycle-912 digests, and measure the
point-in-time universe membership of the incumbent's published walk-forward,
which no committed record measures.

## Data used

- **Source:** committed parquet cache `data/raw/` (35 files, 174052 rows); the fetcher is never called.
- **Date range:** the cache spans 1993-01-29 .. 2026-10-20; the incumbent's published walk-forward spans 1993-01-01 .. 2026-10-09.
- **Frequency:** daily for every equity/futures file; 8-hourly for the crypto funding files.
- **Point-in-time treatment:** the price panel is read from the cache exactly as the committed fetcher aligns it (union calendar, each symbol forward filled); the momentum, the selection rule and the overlay are the committed ones (`src/features/momentum.py`, `research/run_cycle6.py`).
- **Cost model:** 1.0 bps commission + 2.0 bps slippage = 3.0 bps per unit of weight change; risk-free 2.00%.

## Configuration

- **Candidate:** `tsmomentum_spytrend_001` (universe: SPY, QQQ, IWM, TLT, GLD, EFA, EEM).
- **Signal:** 226-session momentum skipping the most recent 21 sessions, top_fraction 0.5.
- **Design:** the published 10y-train / 12m-test / 6m-step walk-forward with 21d purge and 21d embargo, on the continuously computed point-in-time path.
- **Published record:** `research/experiments/tsmomentum_regime_filter_wf_001.md` (resolved by content).

## Results

| Quantity | Value |
|---|---|
| Published inventory digests re-verified | 35/35 match, 0 changed, 0 removed, 0 added |
| Configuration files | 8 published vs 13 current (added: config/overnight_capture_001.yaml, config/paper_trading_config.yaml, config/promotion_gates.yaml, config/sample_policy.yaml, config/simulation_candidate_001_corrected.yaml) |
| Anchor (recomputed) | 48 folds, mean 0.947307, positive 91.67%, 6013 pooled trades |
| Folds on an incomplete cross-section | 7 of 48 (mean OOS Sharpe 1.883186) |
| Folds on the complete cross-section | 41 of 48 (mean OOS Sharpe 0.787522; 1.352958 without the fold-12 artefact) |

## Number of trials

1 (a measurement: no parameter search, no candidate generation, no re-tuning). The bootstrap uses 2000 moving-block draws with seed 20240101.

## Reproduction commands

```bash
python research/data_cost_inventory_002.py
python -m pytest -q tests/test_data_cost_inventory_002.py
git status --porcelain data/ config/
```
