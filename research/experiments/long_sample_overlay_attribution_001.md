# Experiment: Long-Sample Mechanism Decomposition of the Incumbent's Risk Overlays (long_sample_overlay_attribution_001)

**Cycle**: 878
**Type**: read-only, pre-registered diagnostic of a fixed configuration. No strategy, universe, cost model, parameter, threshold, gate, state or candidate was changed, and nothing was fitted or selected.
**Hypothesis**: `research/hypotheses/overlay_mechanism_long_sample_001.md` (v001, pre-registered 2026-10-19, code revision 38d3c44, before execution)
**Report**: `research/reports/long_sample_overlay_attribution_001.md` (+ machine-readable `research/reports/long_sample_overlay_attribution_001.json`)
**Script**: `research/long_sample_overlay_attribution.py` (read-only; prints every number in the report; exits 0 with `OVERALL: PASS`)

---

## Hypothesis Reference

The incumbent `tsmomentum_spytrend_001` stacks a SPY-200d trend filter, a 10%/63d volatility target, a 15% drawdown cut and a gross-exposure cap on a 12-1 month momentum signal. Cycle 862 localised the trailing 63-session promotion-gate failure to the volatility overlay but explicitly declined to conclude anything about the long run. The committed long-sample artifact (`research/reports/promotion_feasibility_backtest_001.md`) is produced by an engine **without** overlays, so the overlays' long-run contribution had never been measured.

Pre-registered conditions (verbatim intent, full text in the hypothesis file):

- **F1** — the overlay is a structural drag: L2-net Sharpe is not greater than L0-net Sharpe **or** the full-sample vol-overlay contribution is negative.
- **F2** — the trailing window is an overlay anomaly: the trailing-63 vol-overlay contribution ranks below the 50th percentile of all rolling-63 vol-overlay contributions.
- **F3** — the signal decayed: the trailing-63 canonical Sharpe of L0-net (raw signal) is negative.

Decision rule (fixed in advance): F1+F2+notF3 -> "a different risk treatment is warranted"; F1+F3 -> "retire the incumbent, next candidate must be a structurally different family"; notF1 -> "do not re-optimize the incumbent"; F2 without F1 -> "diagnostic only". **No candidate, promotion, re-fit or deployment decision may be taken in this cycle.**

---

## Data Used

- **Source**: committed cache `data/raw/*.parquet` (Yahoo Finance via yfinance), read-only; no download, no write, no cache mutation.
- **Realized sample**: 1993-01-29 .. 2026-10-16, **8,487 sessions** (union calendar from SPY's inception). The committed artifact's `sample.start_date` field is the *common* (max of per-symbol inception) start, 2004-11-18, but `src/backtest/engine.py:run_backtest` does not slice the price frame to it; the published metrics reproduce bit-exactly on the realized sample, so this measurement uses the same realized sample.
- **Universe**: SPY, QQQ, IWM, TLT, GLD, EFA, EEM (frozen paper-trading universe). `^VIX` is cached but unused by this measurement.
- **Frequency**: daily, close-to-close.
- **Point-in-time treatment**: unchanged from the strategy under test — the momentum signal uses the T-1 close (1-day lag), the trend filter uses the same day's close, the volatility and drawdown overlays use trailing information only. The measurement introduces no forward-looking step and fits nothing.
- **Missing data**: the fetcher's union-calendar forward fill, unchanged.

---

## Configuration (unchanged, frozen)

| Item | Value | Source |
|---|---|---|
| Candidate | `tsmomentum_spytrend_001` | `config/simulation_candidate_001.yaml` |
| Signal | 12-1 month momentum (226 lookback, 21 skip), top 50% equal weight | same |
| Trend filter | SPY 200-day SMA, exposure 0.0 / 1.0 | same |
| Volatility overlay | 10% annualized target, 63d trailing realized vol, leverage cap 1.0 | same |
| Drawdown overlay | exposure x 0.5 below -15% | same |
| Cost model | 1 bp commission + 2 bp slippage = 3 bp per unit of weight change | same |
| Execution | close-to-close, 1-day signal lag, daily rebalance | same |
| Sharpe convention | `arithmetic_annualized_rf0` (canonical) | `src/evaluation/sharpe.py` |
| Engine | `src/simulation/engine.py:run_simulation` | same pipeline as the paper record |
| Layer construction | `research/trailing_window_attribution.py:build_layers` (imported, not re-implemented) | Cycle 862 |

**Number of trials: 1.** One measurement of one frozen configuration. No parameter, threshold, window length, universe or configuration was varied, fitted or selected. F1-F3 are three fixed readings of that single run.

---

## Splits

None (nothing was fitted). The only chronological structure is inside the record: the full sample (8,487 sessions), the 8,425 overlapping rolling-63-session windows, and the trailing 63 sessions (2026-07-21 .. 2026-10-16) that fail the promotion gate.

---

## Method

1. Run `run_simulation` with the frozen config over the full history and rebuild the counterfactual layer chain with the shared `build_layers` helper.
2. Cost **every** layer on **its own** turnover (3 bp x |dW|_1) so the layers are comparable; the executed path (L4) is the paper record's own path.
3. Telescope the chain: L0 (raw signal) -> L1 (+ trend filter) -> L2 (+ volatility overlay) -> L3 (+ drawdown overlay) -> L4 (+ gross-exposure cap, executed).
4. Decompose the full sample and every rolling-63 window; the telescoping residual must be <= 1e-12.
5. Evaluate F1-F3 with the pre-registered decision rule.

**Integrity checks performed (all inside the script):**

| Check | Result |
|---|---|
| Simulation engine reproduces the committed 449-session paper record | max abs diff **0.000e+00** for `net_return`, `turnover`, `vol_scale`, `dd_scale`, `regime_exposure`, `n_positions` |
| Cycle 862 trailing-window numbers reproduced | max abs diff **4.587e-07 pp** (published values are rounded to 6 decimals of a percent) |
| Committed backtest artifact reproduced | canonical Sharpe **0.5646255767978904** and max drawdown **-0.6224126346564325** bit-exactly, 8,487 sessions |
| The two engines agree on the raw signal | max abs diff **5.421e-20** per session over 8,487 sessions |
| Telescoping residual (full sample) | **1.421e-14** (tol 1e-12) |
| Read-only | SHA-256 of all 19 raw parquet files, all `config/*.yaml` and the paper-trading state unchanged before/after |

---

## Results

### 1. Full sample, each layer net of its own cost (8,487 sessions)

| Layer | Compounded | Canonical Sharpe | Max drawdown | Annualised turnover |
|---|---|---|---|---|
| L0 raw signal | +1552.881339% | +0.564626 | -62.2413% | 9.215x |
| L1 + SPY-trend filter | +20671.820853% | +1.336945 | -16.0189% | 13.510x |
| L2 + volatility overlay | +6744.582201% | +1.485591 | -9.9349% | 12.158x |
| L3 + drawdown overlay | +6744.582201% | +1.485591 | -9.9349% | 12.158x |
| L4 + gross-exposure cap (executed) | +6744.582201% | +1.485591 | -9.9349% | 12.158x |

The drawdown cut and the gross-exposure cap are **inert** on this sample (`dd_scale < 1` on 0 of 8,487 sessions, maximum gross exposure exactly 1.000000). The trend filter is flat (exposure 0) on 2,270 of 8,487 sessions (26.7%).

### 2. Trailing 63 sessions (2026-07-21 .. 2026-10-16)

| Layer | Compounded | Canonical Sharpe |
|---|---|---|
| L0 raw signal | +0.912221% | **+0.307230** |
| L1 + trend filter | +0.912221% | +0.307230 |
| L2 + volatility overlay | -0.517510% | **-0.211884** |
| L4 executed | -0.517510% | -0.211884 |

### 3. Rolling-63 distribution of each mechanism's contribution (8,425 windows)

| Mechanism | trailing | rank | mean | median | p05 | p95 | windows < 0 |
|---|---|---|---|---|---|---|---|
| filter_effect | +0.000000% | 51.96% | +1.800457% | +0.000000% | -2.752202% | +12.957302% | 30.22% |
| vol_overlay_effect | -1.429732% | **21.70%** | -0.914246% | -0.019133% | -4.743014% | +0.492769% | 56.97% |
| drawdown_overlay_effect | +0.000000% | 100.00% | +0.000000% | +0.000000% | +0.000000% | +0.000000% | 0.00% |
| gross_exposure_cap_effect | +0.000000% | 100.00% | +0.000000% | +0.000000% | +0.000000% | +0.000000% | 0.00% |

### 4. Falsification conditions

| Condition | Verdict | Numbers |
|---|---|---|
| F1 (overlay is a drag) | **PASS** (second clause only) | vol-overlay compounded contribution -13927.24% < 0; but L2-net Sharpe +1.485591 > L0-net +0.564626 (first clause fails) |
| F2 (trailing window is an overlay anomaly) | **PASS** | trailing contribution -1.429732%, 21.70th percentile of 8,425 windows |
| F3 (signal decayed) | **FAIL** | trailing L0-net Sharpe +0.307230 > 0 |

Pre-registered rule output (F1 + F2 + not F3 branch): *"The overlay is a drag and the trailing window is an overlay-timing anomaly: a different risk treatment is warranted, quantified by this measurement."*

### 5. Mandatory qualification of the literal verdicts

- **F1's wording is not supported by the risk-adjusted readings of the same run.** A telescoping *difference of compounded* returns is not scale-free: the trend filter's own compounded effect is of the order of 10^4 percentage points, so the vol-overlay clause is dominated by that number. The scale-free comparison the same run produces (L1 -> L2) shows the overlay **improving** the canonical Sharpe (+1.336945 -> +1.485591) and the max drawdown (-16.0189% -> -9.9349%) while costing compounded return. The literal verdict is reported as pre-registered; the "structural drag" wording is not.
- **F2 is true but modest**: the 21.7th percentile is worse than typical, but far from the p05 (-4.7430%), and the median window is approximately flat (-0.0191%).
- **F3 is false and is the most decision-relevant reading**: in the trailing 63 sessions the *raw signal* was profitable (+0.307230 Sharpe) while the executed path lost money (-0.211884). The trailing NO-GO is an **overlay-timing** outcome, not evidence of a decayed momentum edge.

### 6. What the measurement establishes

1. The committed long-sample artifact (canonical Sharpe 0.5646255767978904, max drawdown -0.6224126346564325) is the **raw signal net of costs, without any overlay**, over the union calendar from 1993-01-29.
2. On the same sample the full overlay stack lifts the canonical Sharpe from +0.564626 to +1.485591 and the max drawdown from -62.24% to -9.93%.
3. The trailing 63-session gate failure is an overlay-timing outcome; the signal itself did not decay in that window.

### 7. What it does not establish

1. No new candidate, parameter, universe or deployment decision; the incumbent stays **NO-GO** and no re-fit is proposed.
2. Whether the overlay is a drag in the risk-adjusted sense (the pre-registered statistic is not scale-free; the scale-free readings point the other way).
3. Whether the rolling-63-day promotion gate is statistically informative or noisy — the empirical distribution of that statistic over the long sample is not measured here.

---

## Reproduction

```bash
python research/long_sample_overlay_attribution.py   # OVERALL: PASS (exit 0)
python research/promotion_feasibility_backtest.py     # committed artifact reproduced
python research/go_no_go_evaluation.py                # decision unchanged (NO-GO)
python research/drift_persistence_report.py           # stored == recomputed
python -m pytest -q                                  # 89 tests (82 pre-existing + 7 new)
git status --porcelain data/ config/                 # must be empty
```

---

## Decision label

**Exploratory / diagnostic** — the measurement is clean and the three pre-registered conditions are evaluated, but the pre-registered F1 statistic turned out not to be scale-free, so the cycle's headline is the *F3* reading rather than the F1 reading. The promotion decision is unchanged: **NO-GO**, live deployment unsupported; `sectorrotation_001`, `csmomentum_001` and `macroregime_001` remain rejected/failed; the drift flag `low_rolling_sharpe` (-0.21188351222842883, 5 consecutive trading days below 0.5) is unchanged. The measurement produced **no** candidate and recommends **no** re-fit.
