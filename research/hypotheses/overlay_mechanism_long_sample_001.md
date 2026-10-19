# Hypothesis: Long-Sample Mechanism Decomposition of the Incumbent's Risk Overlays (overlay_mechanism_long_sample_001)

## Version History

- v001 (overlay_mechanism_long_sample_001, 2026-10-19): Initial pre-registered
  hypothesis for Cycle 878. Parent cycle: Cycle 877 (post-go/no-go monitoring,
  NO-GO stable on the 449-session record through 2026-10-16). Code revision:
  38d3c44. Pre-registered **BEFORE** any long-sample measurement was executed.

---

## Mechanism Description

The incumbent `tsmomentum_spytrend_001` (frozen in
`config/simulation_candidate_001.yaml`) is a 12-1 month time-series momentum
signal on 7 liquid ETFs, with three risk treatments stacked on top of it:

1. **SPY 200-day SMA trend filter** (exposure 0.0 below the SMA, 1.0 above),
2. **volatility targeting** (10% annualized target on 63-day trailing realized
   volatility, capped at 1.0 gross leverage),
3. **drawdown control** (exposure cut to 0.5 while the volatility-scaled
   portfolio is more than 15% below its running peak) plus a gross-exposure cap.

The **structural claim** behind the overlays is the standard one: a momentum
signal's returns arrive unevenly, and scaling exposure down when realized
volatility is high (or when the strategy is in drawdown) should improve the
*risk-adjusted* and *drawdown* profile of an otherwise volatile signal.

The **counter-claim** is equally structural: a lagged volatility scaler is
pro-cyclical. It reduces exposure *after* volatility has risen, which is
exactly when momentum signals tend to be losing money, and it restores
exposure after volatility has fallen, when the signal is usually working. If
the signal's own return distribution is negatively related to its own realized
volatility — the well-documented momentum/crash covariance — then the scaler
is not risk management but a systematic loss-maker, and the strategy's net
return is lower with the overlay than without it.

Neither claim has been tested on long-sample evidence. Cycle 862
(`research/reports/trailing_window_attribution_001.md`) decomposed only the
trailing 63 sessions and the preceding 63 sessions of the **paper record** and
found the volatility overlay to be the dominant trailing-window mechanism
(-1.497444% of a -0.517510% window result, against a +1.078731% raw signal),
while explicitly declining to conclude anything about the long run ("it
localises the loss; it does not establish that the signal has decayed, and it
recommends no re-fit").

The measurement gap is structural: the repository's committed **long-sample**
artifact (`research/reports/promotion_feasibility_backtest_001.md`, 8,487
sessions 2004-11-18..2026-10-16) is produced by `src/backtest/engine.py`, which
contains **no** overlays, while the **paper record** is produced by
`src/simulation/engine.py`, which contains all three. The two artifacts have
never been reconciled, and the overlays' long-run contribution has never been
measured.

**This hypothesis is a diagnostic, not a trading hypothesis.** It proposes no
new candidate, no parameter, no universe and no deployment.

---

## Expected direction and magnitude (Pre-Specified Prior)

The prior is deliberately non-binding: it states a direction, not a number,
because the quantity has never been measured.

| Quantity | Prior (weak, non-binding) |
|---|---|
| Long-sample contribution of the vol overlay to net return | **negative or indistinguishable from zero** (the overlay scales down exactly when the signal is losing) |
| Long-sample contribution of the vol overlay to *max drawdown* | **strongly positive** (this is what the overlay was added for) |
| Long-sample contribution of the trend filter and the drawdown cut | small (the filter is 0 in most windows; the drawdown cut is rarely active) |
| Trailing-63 Sharpe of the **raw signal** (no overlays) | **uncertain**; the Cycle 862 attribution shows the raw signal itself lost 4.12% in the five entering sessions, so signal-level weakness is at least as plausible as overlay mechanics |

The prior explicitly permits the opposite outcome for every row: the overlay
may improve net Sharpe, and the trailing window may be unremarkable for the
raw signal.

---

## Holding horizon

Measurement horizons inside the existing daily record:

- **Full sample**: 2004-11-18 .. 2026-10-16 (8,487 sessions) — the published
  long-sample window.
- **Rolling windows**: every trailing 63-session window of the full sample
  (8,425 windows) — the same window length as the promotion gate.
- **Trailing window**: 2026-07-21 .. 2026-10-16 — the 63 sessions of the paper
  record that fail the gate.

---

## Asset Universe

The frozen paper-trading universe, unchanged:
SPY, QQQ, IWM, TLT, GLD, EFA, EEM (7 ETFs), plus `^VIX` only as a cached
non-traded reference (not used by this measurement).

Common history: **2004-11-18** (GLD inception) .. **2026-10-16** (last
completed session), 8,487 sessions.

---

## Features and Data Sources

| Item | Value | Source |
|---|---|---|
| Prices | Daily OHLCV, close execution | committed cache `data/raw/*.parquet` (read-only, no download, no write) |
| Signal | 12-1 month momentum (226 lookback, 21 skip), top 50% equal weight | `src/features/momentum.py:build_weights` (via the frozen config) |
| Signal lag | 1 session (signal on T-1 close) | frozen config `execution.signal_lag_days: 1` |
| Trend filter | SPY 200-day SMA, 0.0/1.0 exposure | frozen config `regime_filter` |
| Vol overlay | 10% target, 63-day trailing realized vol, cap 1.0 | frozen config `risk_overlay` |
| Drawdown overlay | cut to 0.5 below -15% | frozen config `risk_overlay.dd_control` |
| Engine | `src/simulation/engine.py:run_simulation` (the pipeline that produced the paper record) | — |
| Layer construction | `research/trailing_window_attribution.py:build_layers` / `decompose_window`, **imported, not re-implemented** | — |
| Cost | 3 bp per unit of weight change (1 bp commission + 2 bp slippage) | frozen config `cost_model` |
| Sharpe convention | `arithmetic_annualized_rf0` (canonical, Cycle 861) | `src/evaluation/sharpe.py` |

**Point-in-time treatment**: unchanged from the strategy under test — the
signal uses the T-1 close, the filter uses the same day's close, the overlays
use trailing information only. This measurement introduces no forward-looking
step and fits nothing.

**Missing data**: the fetcher's union-calendar forward fill, unchanged. The
measurement reads only the committed cache.

---

## Measurement Rules (fixed by this hypothesis; not re-chosen at run time)

1. **Layers.** L0 = base signal weights; L1 = L0 x trend exposure; L2 = L1 x
   `vol_scale`; L3 = L2 x `dd_scale`; L4 = L3 x gross-exposure cap; L5 = L4 net
   of the executed cost (the executed strategy).
2. **Own-cost variants.** Every layer additionally gets its **own** net path:
   that layer's gross path minus 3 bp x the layer's own |ΔW|_1 turnover. This
   is the fair comparison: Cycle 862's counterfactuals were gross, which
   overstates the cost of the lower-turnover counterfactual layers.
3. **Decomposition.** Telescoping decomposition (compounded paths, exactly as
   in Cycle 862) over the full sample and over every rolling 63-session
   window; the residual must be <= 1e-12.
4. **Statistics per mechanism**: full-sample contribution, mean/median/p05/p95/
   min/max of the rolling-63 contributions, and the percentile rank of the
   trailing-63 window among all rolling-63 windows.
5. **Signal-vs-overlay split of the trailing window**: canonical 63-day Sharpe
   of L0-net (raw signal) and of L5-net (fully overlaid), plus the
   corresponding full-sample values.
6. **Reconciliation** (integrity, not a result):
   a. `src/backtest/engine.py:run_backtest` over the same window must
      reproduce the committed long-sample artifact exactly — canonical Sharpe
      0.5646255767978904 and max drawdown -0.6224126346564325 (proof that
      data and configuration are unchanged);
   b. the difference between that backtest path and the simulation engine's
      L0-net-of-base-costs path must be **measured and explained** (the two
      engines differ by construction in warm-up window and cost base);
   c. the simulation engine over the 449-session paper window must still
      reproduce the committed paper record exactly (max |net_return -
      committed| = 0).
7. **Trials: 1.** No parameter, threshold, window length, universe or
   configuration is varied, fitted or selected. There is no search.

---

## Falsification Conditions (pre-registered; evaluated exactly as stated)

Each condition is evaluated on the full sample unless stated. "Contribution"
means the telescoped compounded contribution of that mechanism.

- **F1 — "the overlay is a structural drag"**: the full-sample canonical Sharpe
  of **L2-net is not greater than L0-net**, OR the full-sample vol-overlay
  contribution is **negative**. If F1 holds, the overlay must be dropped in
  any future candidate; the incumbent must not be re-tuned around it.
  *Falsified if*: L2-net Sharpe > L0-net Sharpe AND the vol-overlay
  contribution is positive.
- **F2 — "the trailing window is an overlay anomaly"**: the trailing-63
  vol-overlay contribution ranks **below the 50th percentile** of all
  rolling-63 vol-overlay contributions. If F2 holds, overlay timing explains
  a material part of the trailing failure and the benefit of a different risk
  treatment is pre-quantified by this measurement. *Falsified if* the trailing
  contribution is at or above the 50th percentile.
- **F3 — "the signal itself decayed"**: the trailing-63 canonical Sharpe of
  **L0-net** (raw signal, no overlays) is **negative**. If F3 holds, the
  trailing failure is a property of the signal, not of the overlay, and the
  next candidate must be a structurally different family rather than a variant
  of this one. *Falsified if* L0-net's trailing-63 Sharpe is >= 0.

**Decision rule (fixed in advance)**: report F1/F2/F3 as PASS/FAIL each with
its numbers, and state which of the three pre-registered conclusions the
evidence supports:

- F1 PASS + F2 FAIL + F3 FAIL -> the overlay is a drag and the trailing
  window is an overlay-timing anomaly: a different risk treatment is
  warranted, quantified by this measurement.
- F1 PASS + F3 PASS -> the overlay is a drag and the raw signal also failed in
  the trailing window: retire the incumbent; the next candidate must be a
  structurally different family, not a variant of this one.
- F1 FAIL -> the overlay is not the problem on long-sample evidence: do not
  re-optimize the incumbent (the drift policy stands); the trailing failure
  is a signal-level or noise event.
- Any F2 PASS without F1 PASS -> the trailing window is an overlay-timing
  anomaly but the overlay is net-positive over the long run: report as a
  diagnostic only, no candidate change.

**No candidate, promotion, re-fit or deployment decision may be taken in this
cycle** on the basis of this measurement. The incumbent's promotion decision
(**NO-GO**) is unchanged by construction.

---

## Benchmark

- **The committed long-sample artifact** (`research/reports/promotion_feasibility_backtest_001.md`):
  canonical Sharpe 0.5646255767978904, max drawdown -0.6224126346564325,
  PSR (target 1.4178) 2.2219753177036448e-08, decision NO-GO over 8,487
  sessions. Used as the reconciliation reference (rule 6a).
- **The committed paper record** (`data/processed/paper_trading_state.yaml`):
  449 sessions through 2026-10-16, canonical Sharpe 1.748401, rolling 63d
  Sharpe -0.211884, PSR 0.684041, decision NO-GO. Used as the reproduction
  reference (rule 6c) and as the source of the trailing-window location.

---

## Known Confounders

1. **Engine difference (warm-up, cost base)**: the backtest engine starts with
   no signal history at 2004-11-18 (226-day warm-up in cash) and costs the
   *base* weights; the simulation engine starts with live positions and costs
   the *executed* (overlaid) weights. The two paths are therefore not expected
   to be identical, and the deviation is measured, not assumed (rule 6b).
2. **Overlay warm-up convention**: the frozen config uses `overlay_warmup:
   slice`, i.e. the volatility and drawdown state initializes at the sample
   start. The long-sample run therefore has a fresh overlay state at
   2004-11-18, while the paper record's overlay state is continuous over its
   own window. This is the incumbent's own convention and is not changed here.
3. **Survivorship / present-day universe**: the 7 ETFs are all live today; the
   1993-2004 part of the cache is not used because the common sample starts
   2004-11-18 (GLD inception).
4. **Regime concentration**: the sample contains one dominant volatility regime
   (2008, 2020, 2022) and the trailing window is a single risk-off episode.
   A 63-session statistic is a small-sample statistic; the percentile rank in
   the rolling-63 distribution is reported so the reader can see the
   distribution rather than one window.
5. **Multiple-testing**: none. One measurement of one frozen configuration,
   no parameters selected. The F1/F2/F3 conditions are three fixed readings of
   the same single run and are stated before it.
6. **Costs**: flat 3 bp per unit of weight change; no spread, impact, borrow or
   latency model. Volatility-targeting strategies trade more when volatility
   is high, exactly when spreads are widest, so the measured cost drag is
   likely **understated** for the overlaid layers.
7. **No cash return**: the engine does not accrue interest on de-risked
   capital; the canonical Sharpe subtracts no risk-free rate
   (`arithmetic_annualized_rf0`), so the overlay is not charged for the
   opportunity cost of holding cash. This biases the overlay **upward**.
8. **Single-path counterfactuals**: the counterfactual layers re-use one
   realised path; they are not a re-optimised portfolio and carry no
   rebalancing-feedback effects.

---

## Cost Model Assumptions

Identical to the incumbent and to every other candidate in the repository:
1.0 bp commission + 2.0 bp slippage = **3.0 bp per unit of weight change**,
flat, applied to |ΔW|_1 of the layer being costed. Risk-free rate 0% in the
canonical Sharpe convention. Documented gaps: no bid-ask spread model, no
market-impact model, no borrow/short cost (long-only), no latency model.

---

## Reproduction

```bash
python research/long_sample_overlay_attribution.py   # the measurement (exit 0, OVERALL: PASS)
python research/promotion_feasibility_backtest.py     # reconciliation reference
python research/go_no_go_evaluation.py                # decision unchanged (NO-GO)
python -m pytest -q                                   # full suite
git status --porcelain data/ config/                  # must be empty
```

---

## Decision Discipline (Pre-Commitment)

This cycle produces a **diagnostic** label, not a candidate label:
- *Exploratory / diagnostic* if the measurement is clean and the three
  conditions are evaluated.
- *Blocked by data/infrastructure* if the reconciliation (rule 6a/6c) fails.

The incumbent's promotion decision is **NO-GO** before and after this cycle,
and no candidate, configuration or deployment change may be justified by this
measurement alone.

---

## References

- `research/reports/trailing_window_attribution_001.md` (Cycle 862) — trailing
  window decomposition; the question this hypothesis answers.
- `research/experiments/trailing_window_attribution_001.md` — the method
  (nested counterfactual chain) reused here.
- `research/reports/promotion_feasibility_backtest_001.md` (Cycle 867) — the
  committed long-sample artifact used as the reconciliation reference.
- `research/reports/monitoring_cycle_877.md` (Cycle 877) — current NO-GO
  decision and drift-flag status.
- `src/simulation/engine.py`, `src/backtest/engine.py`,
  `src/features/momentum.py`, `src/evaluation/sharpe.py`.
- AGENTS.md: "Hypothesis first", "Baseline before complexity", "Honest
  accounting", "Multiple-testing control".

---

*Created: 2026-10-19*
*Code revision: 38d3c44*
*Status: PRE-REGISTERED — no long-sample measurement executed yet. Cycle 878 executes it.*
