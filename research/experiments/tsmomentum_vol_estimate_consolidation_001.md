# Experiment: Consolidated same-session volatility estimate and corrected successor backtest record for `tsmomentum_spytrend_001` (tsmomentum_vol_estimate_consolidation_001, Cycle 927)

## Hypothesis reference

- Incumbent hypothesis: `research/hypotheses/tsmomentum_004.md`
- Prior cycles reused: Cycle 925 (the same-session measurement defect), Cycle 926 (the default-off opt-in correction)

## Objective

Consolidate the same-session volatility estimate onto one shared implementation behind one default-off switch in all seven research scripts that still inlined it, and publish the incumbent's corrected backtest as a new, labelled successor reference. Measurement only: no gate, threshold, universe, cost model, Sharpe convention, parameter, hypothesis or drift flag is changed, and no candidate is promoted, re-fit or re-ranked.

## Data

- Committed paper-trading record: 454 sessions (2025-01-02 .. 2026-10-19)
- Price panel: committed parquet cache `data/raw/*.parquet` (cache-only; the fetcher is never called)
- Universe: SPY, QQQ, IWM, TLT, GLD, EFA, EEM
- Cost model: 1.0 bps commission + 2.0 bps slippage = 3.0 bps round-trip
- Point-in-time treatment: momentum weights shifted one session; the SPY SMA filter and the trailing volatility window are computed on the cached panel; the published walk-forward design (10y train / 12m test / 6m step, 21d purge, 21d embargo) is reused unchanged

## Configuration

- Signal: TSMOM lookback 226, skip 21, top_fraction 0.5
- Overlay: vol-target 0.1 (lookback 63) + drawdown control 0.15 + SPY 200-day SMA filter
- Switch: `lag_vol_estimate`, default **off**; the corrected path sets it to True in the research path and the shared engine
- PSR: target 1.4178, `n_bootstrap=1000`, `block_size=22`, `seed=20240101` (the repository's own settings)
- Gates read from `config/promotion_gates.yaml`: `rolling_63d_sharpe` >= 0.9, `psr` >= 0.95

## Trial count

- 1 anchor reproduction (48 folds) + 7 per-script consolidation bit-identity checks + 2 paths (default, corrected) + 1 frozen-implementation comparison per script; no per-fold re-optimisation, no candidate selection, no configuration search.

## Results

### Consolidation

- All seven scripts consolidated: run_cycle5, run_cycle13, run_cycle15, run_cycle15_c4_corrected, run_cycle18, run_cycle19, month_end_candidate_reaudit
- Per-script default path: bit-identical to the frozen pre-change implementation (max |diff| = 0.0, all scripts).
- Remaining inline same-session exposure estimates: 0.

### Successor record (supersedes nothing)

- Corrected walk-forward mean OOS Sharpe: 1.318605 (all folds); excluding each path's own worst fold: 1.357135
- Corrected record canonical Sharpe: 1.591618
- Corrected trailing 63-session Sharpe (`rolling_63d_sharpe`): -0.333802
- Corrected PSR vs 1.4178: 0.599720
- Corrected 2018-2026 test-period Sharpe (own-path reference): 1.335983
- Promotion decision: NO-GO on both paths (failed gates: rolling_63d_sharpe, psr)

## Verdict

The consolidation is complete and verified bit-for-bit. The corrected successor record is published as a new artefact that supersedes nothing. The incumbent remains a **Credible Candidate** by its published verdict and **NO-GO** for promotion; the corrected path is worse on every record-level statistic and does not rescue anything.

## Reproduction

```bash
python research/tsmomentum_vol_estimate_consolidation.py
python -m pytest -q tests/test_tsmomentum_vol_estimate_consolidation.py
```
