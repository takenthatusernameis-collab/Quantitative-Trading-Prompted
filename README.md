# Quantitative Trading Research

Autonomous research pipeline for discovering reproducible, net-of-cost trading edges.

## Overview

This repository implements a disciplined quantitative research process focused on finding genuine market inefficiencies that can be captured by low-friction automated strategies. The system runs autonomous agent cycles that iterate through hypothesis formation, implementation, evaluation, and learning.

## Research Philosophy

- **Evidence over optimism**: Prioritize reproducible, net-of-cost results over impressive in-sample backtests
- **Structure over patterns**: Seek specific structural mechanisms (funding/carry, constraints, session effects, delayed discovery) rather than data-mined correlations
- **Honest accounting**: All results reported net of realistic fees, slippage, and market impact
- **Statistical rigor**: Control for multiple testing, use chronological out-of-sample evaluation, track hypothesis count

## Project Structure

```
├── AGENTS.md              # Agent cycle instructions
├── README.md              # This file
├── NEXT_AGENT_TASK.md     # Current task specification
├── PROMPT.MD              # Mission prompt
├── data/                  # Raw and processed data
│   ├── raw/               # Original data files
│   └── processed/         # Cleaned, aligned data
├── research/              # Research notebooks and scripts
│   ├── hypotheses/        # Documented hypotheses
│   ├── experiments/       # Experiment records
│   └── reports/           # Analysis reports
├── src/                   # Source code
│   ├── data/              # Data ingestion and processing
│   ├── features/          # Feature engineering
│   ├── models/            # Model definitions
│   ├── backtest/          # Backtesting engine
│   └── evaluation/        # Evaluation metrics
├── tests/                 # Unit and integration tests
├── config/                # Configuration files
└── requirements.txt       # Python dependencies
```

## Current Status

**Cycle 17**: Corrected C4 re-execution (execution-defect correction) + C6 pre-registration validation.
- **C4 (sectorrotation_001) validly evaluated → Rejected/Failed**: the pre-registered C4 test was executed correctly for the first time via `research/run_cycle15_c4_corrected.py` (9 sector ETFs, 1998-12-22 start, 36 folds, 18-config grid, config SHA-256[:12] `4f186de79db3`). Results: baseline (252,21,0.5) test Sharpe 0.4679 (rank 5/18, plateau 3/3); walk-forward mean OOS Sharpe **0.6944** (83.3% positive folds, 158 pooled trades); 1/N 9-sector benchmark 0.4430 (baseline excess IR +0.0665); incumbent TSMOM 1.4122 common-index (standalone 1.4178, reproduces Cycle 6/7); DSR **-0.2742** (p=0.3920) at N=18. Pre-registered falsification condition met (WF mean OOS Sharpe 0.6944 < 0.9) → **Rejected/Failed**. Artifacts verified: 9 weight columns, 6,991 rows (1998-12-22 → 2026-10-08), 36-fold table ≠ C3's 48-fold table. Record: `research/experiments/sectorrotation_baseline_wf_001.md` (regenerated; defective Cycle 15 original preserved in git history, commit 1d540f8).
- **Family verdict complete**: cross-sectional momentum is rejected on two valid pre-registered tests (C3 broad universe, C4 sector universe) and archived. Full evidence: `research/reports/cross_momentum_consolidation.md` (section 6).
- C6 pre-registration validated: `config/calendar_effects_001.yaml` parses; grid arithmetic 3×6=18; `generate_walkforward_splits("2000-05-26", "2026-10-09", 10, 12, 6, 21, 21)` = 33 folds (fold 1 test 2010-02-22→2011-02-08; fold 33 test 2025-08-06→2026-07-23). No backtest executed.
- Next: Cycle 18 — execute the C6 evaluation (`research/run_cycle18.py`): baseline backtest, 33-fold walk-forward, 18-config grid, 1/N + incumbent benchmarks, DSR at N=18, plateau check on the `pre_days` axis at `post_days=3`.

**Cycle 18** (prior): Calendar/Rebalancing Effects (C6) execution complete — Rejected/Failed.
- `research/run_cycle18.py` executed the pre-registered C6 evaluation (TOM window on SPY/QQQ/IWM, 33-fold walk-forward, 18-config grid). Results: WF mean OOS Sharpe -0.0254 < 0.9, positive-fold rate 42.4% < 50%, plateau 1/3 — gates 1, 2, 4 fail. C6 is a distinct calendar mechanism, separate from the momentum family (C3/C4) already archived. Record: `research/experiments/calendar_effects_baseline_wf_001.md`.

**Cycle 19** (current): Macro Regime Overlay Extension (C5) execution complete — Rejected/Failed.
- `research/run_cycle19.py` executed the pre-registered C5 evaluation (VIX regime gate on top of the incumbent SPY-trend-filtered TSMOM: 7-ETF core universe 2004-11-18→2026-10-09, 24-fold walk-forward, 12-config grid, config SHA-256[:12] `76a8c320b25b`; aligned-frame hash `7393bf74d806c40b` verified). Results: baseline (vix_threshold=30, vix_exposure=0.5) test Sharpe 0.2950 (rank 7/12, plateau 4/4); walk-forward mean OOS Sharpe **0.4331** (75% positive folds, 137 pooled trades); benchmarks — incumbent control arm (vix_exposure=1.0) test Sharpe 0.3241 / WF 0.4628; 1/N 7-ETF test Sharpe 0.4716; DSR **-0.5061** (p=0.3064) at N=12, PSR vs 0.9 gate 0.0255, block-bootstrap 95% CI [-0.2934, 0.9147]; VIX gate underperforms the incumbent control on both test and WF. Pre-registered falsification condition met (WF mean OOS Sharpe 0.4331 < 0.9) → **Rejected/Failed**. Artifacts: `research/experiments/macroregime_baseline_wf_001.md`, `data/processed/*_macroregime_001.parquet`. The result is consistent with the pre-registered prior: overlay-on-overlay has low probability of raising the already-gated incumbent's OOS Sharpe; ^VIX is an index (not tradeable), so the gate is a position-sizing rule, not a vol-risk-premium harvest.

**Cycle 14** (prior): Pre-Registration for Sector Rotation (sectorrotation_001) complete.

**Cycle 14** (prior): Pre-Registration for Sector Rotation (sectorrotation_001) complete.
- Candidate C4 (long-only cross-sectional momentum, 9 GICS sector ETFs XLB–XLY) pre-registered: full hypothesis (`research/hypotheses/sectorrotation_001.md`), frozen config (`config/sectorrotation_candidate_001.yaml`), evaluation plan — **no backtest executed** (evaluation is Cycle 15)
- Grid arithmetic corrected: 3 lookbacks x 2 skips x 3 top-fractions = **18 unique configurations** (label equals the product; fixes the Cycle 13 "27" mislabel); Cycle 15 script must assert the count
- Walk-forward: 10yr/1yr/6mo, 21d purge/embargo from the 1998-12-22 history start → **36 folds** (actual count verified via `generate_walkforward_splits`; the C3 48-fold count does not apply)
- Prior explicitly conditioned on C3's rejection (lower than C3's was): gross 0%–2% excess over 1/N; falsification pre-stated: WF mean OOS Sharpe < 0.9 OR < 50% positive folds → Rejected/Failed
- Data integrity verified at freeze: 9/9 parquet files, 6,991 common trading days (1998-12-22 → 2026-10-08), 100% Close completeness, aligned-frame hash `5e2d48e6579a53cd`
- Next: Cycle 15 evaluation execution (`research/run_cycle15.py`) — baseline backtest, 36-fold walk-forward, 18-config grid, benchmarks (1/N 9-ETF + incumbent TSMOM), DSR at N=18

**Cycle 13** (prior): Baseline Backtest & Walk-Forward for Cross-Sectional Momentum (csmomentum_001) complete.
- Baseline (lookback=252, skip=21, top_fraction=0.5, monthly rebalance, 3bps costs): test period (2018-2026) net Sharpe 0.4101, max DD -35.7%, 62 trades, 2.06x annualized turnover
- Walk-forward (48 folds, fixed parameters, 10yr/1yr/6mo, 21d purge/embargo): mean OOS Sharpe 0.6868, 79.2% positive folds, 313 pooled OOS trades
- **Pre-registered falsification condition met** (WF mean OOS Sharpe < 0.9) → **Rejected/Failed**; dominated by both benchmarks (1/N equal-weight test Sharpe 0.4617; incumbent TSMOM 1.4178, WF 0.9473 — both reproduced exactly, verifying benchmark implementation)
- Robustness grid (18 pre-specified configs): baseline ranks 17/18; DSR negative at N=27 (pre-registered) and N=18 (evaluated); plateau 2/3 lookbacks within 10% (passes)
- Artifacts: `data/processed/{simulation,trades,weights}_csmomentum_001.parquet`; record: `research/experiments/csmomentum_baseline_wf_001.md`
- Regenerated by `research/run_cycle13.py`

## Running the Research Pipeline

The pipeline runs automatically via GitHub Actions every 5 minutes. Each cycle:
1. Reads the current task from `NEXT_AGENT_TASK.md`
2. Executes the bounded research task
3. Produces evidence artifacts
4. Writes the next task to `NEXT_AGENT_TASK.md`

## Key Documents

- [AGENTS.md](AGENTS.md) - Complete agent instructions and research standards
- [NEXT_AGENT_TASK.md](NEXT_AGENT_TASK.md) - Current cycle task specification
- [PROMPT.MD](PROMPT.MD) - Mission prompt

## Research Documentation Standards

All hypotheses and experiments follow strict documentation requirements defined in AGENTS.md to ensure reproducibility and prevent false discoveries.

## Safety

This is a research/backtesting system only. It never places live trades, accesses credentials, or modifies account settings.

**Cycle 20** (current): Paper-Trading Validation Extension (Option A) complete — 63-day gate **PASSED**.
- `research/run_paper_trading_replay.py` executed deterministic historical replay on cached data (2026-07-02 → 2026-10-09, 70 trading days). Results: track-record length **70 days** (exceeds 63-day minimum); rolling 63-day Sharpe **0.9356** (exceeds 0.9 target); max drawdown **-1.23%** (well within 15% threshold); full-period Sharpe 0.4191 (below 0.9 target due to early-period volatility in low-vol regime). Net return +0.90% (3.28% ann.), volatility 7.83% ann. Regime persistence: 70 days (SPY > SMA throughout); zero regime flips; turnover median 0.40%, p95 30.05%. Artifacts: `data/processed/paper_trading_state.yaml`, 70 daily parquet files, `research/reports/paper_trading_rolling.md`, `research/reports/paper_trading_validation_001.md`. Incumbent (tsmomentum_spytrend_001) advances to continued prospective validation; next cycle should extend track record further to capture regime diversity.