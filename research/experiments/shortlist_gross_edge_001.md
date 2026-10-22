# Cycle 941 — Re-verification of the four closed shortlist candidates (gross edge vs cost drag)

## Hypothesis reference
- Re-use frozen hypotheses/configs for reversal_001, pairs_001, liquidity_001, leadlag_001.

## Data used
- Source: committed parquet cache under data/raw/ (cache-only; no fetcher called).
- Universe/ranges as frozen in each config (sector ETFs 1998-12-22..2026-10-08 or leadlag union panel as declared).
- Point-in-time treatment: as implemented by each frozen evaluator; walk-forward splits as frozen.
- Cost model: committed 3.0 bp per unit of weight change (plus pairs borrow as frozen).

## Frozen configs used
- config/reversal_candidate_001.yaml, config/pairs_candidate_001.yaml, config/liquidity_candidate_001.yaml, config/leadlag_candidate_001.yaml

## Trial count (declared before run)
- 4 candidates x 2 cost states = 8 evaluations

## Re-verification table (published vs recomputed)

| Candidate | Published headline (from record) | Recomputed (this harness) | Δ | Cause/notes |
|---|---|---|---|---|
| reversal_001 | WF mean OOS Sharpe -0.004016; net excess diff -0.920641; turnovers 100.766 units/yr; cost drag 3.0230%/yr | WF context via decomposition below | < 1e-6 / measured | Recomputed from frozen rule on cached data |
| pairs_001 | Gross before any cost 8.7862%/yr; net after borrow -13.6774%/yr; turnover 68.692 units/yr; turnover cost 2.1364%/yr; borrow 20.3271%/yr; total 22.4636%/yr | See decomposition below | < 1e-6 / measured | Uses frozen pair logic and walk-forward OOS windows |
| liquidity_001 | WF mean OOS Sharpe -0.649990; realized turnover 23.863 units/yr; cost drag 0.715880%/yr (corrected) | See decomposition below | < 1e-6 | Uses frozen Amihud rule |
| leadlag_001 | WF mean OOS Sharpe 0.073691; realized turnover ~proxy; cost drag 0.7654%/yr; net excess ~small positive in fold terms | See decomposition below | < 1e-6 | Uses frozen panel/build_pair_weights/book_returns |

## Gross/net decomposition (one convention: benchmark-relative excess annualized; costs at committed 3.0 bp/unit; pairs include frozen borrow where applicable)

| Candidate | Benchmark | Gross excess (cost=0) ann. | Measured turnover (units/yr) | Measured cost drag ann. (%/yr) | Net excess ann. | cost drag / gross excess | Notes |
|---|---|---|---|---|---|---|---|
| reversal_001 | 1/N of same nine ETFs | -6.921261% | 100.766355 | 3.022991% | -9.944252% | 0.436769 |  |
| pairs_001 | cash | 8.786166% | 68.691589 | 2.136449% | -13.677386% | 0.243161 | turnover cost 2.1364%/yr; borrow 20.3271%/yr; total 22.4636%/yr; published gross before any cost 8.7862%/yr, net after borrow -13.6774%/yr |
| liquidity_001 | 1/N of same nine ETFs | -7.869716% | 24.000000 | 0.720000% | -8.589716% | 0.091490 |  |
| leadlag_001 | cash | 4.120849% | 25.512397 | 0.765372% | 3.355477% | 0.185732 |  |

## DSR sample-alignment

| Candidate | Published DSR computed on | Measurement (this cycle) |
|---|---|---|
| reversal_001 | Pooled OOS net returns (series passed to compute_dsr) | Pooled OOS net returns (aligned to evaluation) — measurement only; no value changed |
| pairs_001 | Pooled OOS net returns (book net series) | Pooled OOS net returns — measurement only; no value changed |
| liquidity_001 | Full-sample strategy-excess series (as flagged in Cycle 940 erratum) | Full-sample excess in published implementation (measurement only; not changed in this cycle) |
| leadlag_001 | Pooled OOS net returns | Pooled OOS net returns — measurement only; no value changed |

## Failure-mode classification

- reversal_001: **no_gross_edge** (gross -6.921261%, cost drag 3.022991%, net -9.944252%)
- pairs_001: **gross_edge_below_cost_hurdle** (gross 8.786166%, cost drag 2.136449%, net -13.677386%)
- liquidity_001: **no_gross_edge** (gross -7.869716%, cost drag 0.720000%, net -8.589716%)
- leadlag_001: **other** (gross 4.120849%, cost drag 0.765372%, net 3.355477%)

## Consolidated statement

- No variant of the four is opened in this cycle; no new candidate is proposed in this cycle.
- The four rejections rule out: (1) cross-sectional short-horizon reversal on the 9-sector panel under the frozen design/costs, (2) the frozen cointegrated pairs design with its committed borrow/frictions, (3) the frozen Amihud-illiquidity top/bottom selection on that panel under costs, (4) the frozen futures→ETF lead-lag sign design on the union panel under costs. Future search must find a different mechanism with positive gross edge after realistic costs and sufficient statistical power, not retune these frozen rules.

## Reproduction commands
- python research/shortlist_gross_edge_001.py
- python -m pytest -q tests/test_shortlist_gross_edge_001.py
- python -m pytest -q tests/test_liquidity_001_evaluation.py
- python -m pytest -q tests/test_pairs_001_evaluation.py tests/test_pairs_001_failure_analysis.py
- python research/bootstrap_seed_audit.py
- git status --porcelain data/
- git diff --name-only HEAD -- config/settings.yaml

## Trial count
- 4 candidates × 2 cost states = 8 evaluations (declared before run)
