# Experiment: SMA-175 candidate validation for `tsmomentum_spytrend_001` (tsmomentum_sma175_validation_001, Cycle 914)

## Hypothesis reference

- Candidate hypothesis: `research/hypotheses/tsmomentum_004.md` (Cycle 5 promoted candidate)
- Published walk-forward record: `research/experiments/tsmomentum_regime_filter_wf_001.md` (resolved by content)
- Frozen candidate definition: `research/run_cycle6.py` (the script that produced the published record; read, never changed)
- Prior evidence: `research/experiments/tsmomentum_phase_stability_fix_001.md` (Cycle 913, phase-instability diagnosis and the SMA-175 tweak), `research/experiments/tsmomentum_fold_phase_decision_001.md` (Cycle 912, downgrade to exploratory)
- Pre-registered promotion gates: `AGENTS.md` and the published record's gate table (read, never changed)

## Objective

Validate the SMA-175 mutation (SPY trend-filter SMA window 200 -> 175) as a candidate under the full published protocol: the 48-fold walk-forward gates (gate-1 mean OOS Sharpe, gate-2 positive fold rate, gate-3 pooled OOS trades), the phase decomposition that motivated the mutation, and the published SMA-plateau check, all with the published cost model and thresholds unchanged. Measurement only: no promotion, no change to `research/run_cycle6.py`, no writes under `data/` or `config/`.

## Data

- Source: committed parquet cache in data/raw/ (fetcher never called)
- Universe: SPY, QQQ, IWM, TLT, GLD, EFA, EEM
- Date range: 1993-01-01 to 2026-10-09 (panel capped at END_DATE; the committed cache extends to 2026-10-19, 6 sessions dropped)
- Point-in-time treatment: signals use only data available at formation (weights shifted one day), the SPY SMA is computed point-in-time, the overlay/cost model are applied on the same continuously computed path for every fold and phase, and the panel is capped at the published END_DATE
- Cost model: 1.0 bps commission + 2.0 bps slippage = 3.0 bps round-trip; risk-free 0.02 annual (unchanged)

## Configuration (consumed as-is, never inferred)

- Signal: TSMOM lookback 226, skip 21, top_fraction 0.5
- Risk overlay: vol-target 0.1 (lookback 63) + drawdown control 0.15
- Regime filter: SPY SMA 200d (incumbent) vs 175d (candidate); all other parameters unchanged
- Walk-forward (published design): train 10.0y / test 12.0m / step 6.0m, purge 21d, embargo 21d
- Gates (pre-registered): WF mean OOS Sharpe >= 0.9, positive fold rate >= 0.5, pooled OOS trades > 100, SMA plateau >= 2 of 6 pre-specified windows (150, 175, 200, 226, 250, 277) with Sharpe >= 0.9 including the candidate's own baseline window

## Splits

- Published design: 48 folds, mean consecutive test-window overlap 175.0 days, 24 disjoint test windows (unchanged by the mutation: the same splits are used for both designs)
- Phase A = odd folds, phase B = even folds of the published 48-fold design (the interleaving of two disjoint 24-fold sub-designs).

## Results

### Anchor

- Published design recomputed (SMA-200): 48 folds, WF mean OOS Sharpe 0.947307, median 1.2933, positive fold rate 0.9167, pooled OOS trades 6013 -- published anchor reproduced: **MATCH** (48 folds compared).
- Published SMA-plateau table reproduced from the committed cache: **MATCH** (6 windows).

### Gate table

| Design | WF mean OOS Sharpe | Positive fold rate | Pooled OOS trades | Decision |
|---|---|---|---|---|
| SMA-200 (incumbent) | PASS (0.947307 vs 0.9, margin +0.047307) | PASS (0.9167 vs 0.5, margin +0.4167) | PASS (6013 vs 100, margin +5913) | Passes preliminary gates |
| SMA-175 (candidate) | PASS (1.539964 vs 0.9, margin +0.639964) | PASS (0.9583 vs 0.5, margin +0.4583) | PASS (5946 vs 100, margin +5846) | Passes preliminary gates |

### Phase decomposition

| Design | Phase A mean (gate 1) | Phase B mean (gate 1) | Gate-1 outcome changes between phases |
|---|---|---|---|
| SMA-200 (incumbent) | 1.385035 (PASS, 2952 trades) | 0.509580 (FAIL, 3061 trades) | **YES** |
| SMA-175 (candidate) | 1.539145 (PASS, 2922 trades) | 1.540784 (PASS, 3024 trades) | **NO** |

### SMA-plateau check

- Windows with Sharpe >= 0.9: **6/6** (150, 175, 200, 226, 250, 277).
- Gate for SMA-175 (baseline window 175): **PASS**; for SMA-200 (baseline window 200): **PASS**.

### Fold influence

- SMA-200 (incumbent): mean 0.947307, median 1.293299, trimmed mean 1.378012; most influential fold 12 (Sharpe -21.8299, 2 trades, LOO mean 1.431928); thin-trade folds (<= 10 trades): [12, 13].
- SMA-175 (candidate): mean 1.539964, median 1.378702, trimmed mean 1.523690; most influential fold 36 (Sharpe 3.9121, 24 trades, LOO mean 1.489493); thin-trade folds (<= 10 trades): [12].

### Net-of-cost sensitivity (informational)

| Round-trip cost (bps) | WF mean OOS Sharpe | Positive fold rate | Pooled OOS trades | Gate 1 |
|---|---|---|---|---|
| 0.0 | 1.606190 | 0.9792 | 5946 | PASS |
| 3.0 | 1.539964 | 0.9583 | 5946 | PASS |
| 6.0 | 1.473676 | 0.9583 | 5946 | PASS |
| 10.0 | 1.385244 | 0.9583 | 5946 | PASS |

### Parameter perturbation around SMA-175 (informational)

| SMA window | WF mean OOS Sharpe | Positive fold rate | Pooled OOS trades | Gate 1 | Phase A mean | Phase B mean | Phase-stable gate-1 |
|---|---|---|---|---|---|---|---|
| 165 | 1.554672 | 0.9792 | 5843 | PASS | 1.563143 | 1.546201 | YES |
| 170 | 1.548405 | 0.9583 | 5890 | PASS | 1.553047 | 1.543763 | YES |
| 175 | 1.539964 | 0.9583 | 5946 | PASS | 1.539145 | 1.540784 | YES |
| 180 | 1.512241 | 0.9375 | 5957 | PASS | 1.550398 | 1.474084 | YES |
| 185 | 1.074627 | 0.9375 | 5961 | PASS | 1.528878 | 0.620377 | NO |

## Trial count

- Deterministic measurement: 1 incumbent path + 1 candidate path on the published 48-fold design, 2 phase decompositions, 6 published plateau windows, 4 informational cost levels, 5 informational perturbation windows. No per-fold re-optimisation, no candidate selection inside this tool.
- Prior trial count to be charged against this result (from Cycle 913): 5 SPY SMA windows were tried on the same 48 folds (175, 170, 180, 150, 190) and the first phase-stable one was kept.

## Decision

- **Credible candidate for further validation (not promoted)**
- SMA-175 passes the published protocol on the published 48-fold design (gate-1 1.539964 >= 0.9, gate-2 0.9583 >= 0.5, gate-3 5946 > 100), is phase-stable (phase A 1.539145 / phase B 1.540784, both PASS) and passes the published SMA-plateau rule (6/6 windows, candidate baseline included). The incumbent SMA-200 is not phase-stable (phase B 0.509580 FAIL). Promotion is not performed by this tool: the parameter choice is in-sample, so a selection-aware holdout is required first. The SMA window was selected on the same 48 folds that are used to evaluate it (Cycle 913 scanned 175/170/180/150/190 on the published design and kept the first phase-stable window). The SMA-175 numbers are therefore in-sample with respect to the parameter choice: they are not independent evidence, and the selection itself (the number of windows tried) must be charged against the multiple-testing budget before promotion.

## Reproduction

```bash
python research/tsmomentum_sma175_validation_audit.py
python -m pytest -q tests/test_tsmomentum_sma175_validation_audit.py
python -m pytest -q
git status --porcelain data/ config/
git diff --stat src/ config/ research/run_cycle6.py research/experiments/ research/reports/
```
