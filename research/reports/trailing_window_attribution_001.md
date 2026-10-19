# Trailing-Window Attribution — Why the Trailing 63 Sessions Failed the Promotion Gate (Cycle 862)

**Record**: 449 paper sessions, 2025-01-02 → 2026-10-16 (`data/processed/paper_trading_state.yaml`, NAV $133,729.22, max drawdown -4.9857%).
**Convention**: canonical `arithmetic_annualized_rf0` (`src.evaluation.sharpe.sharpe_ratio`), the single convention adopted in Cycle 861 for every gate, drift-flag and PSR quantity.
**Status of this document**: read-only diagnosis. No strategy, universe, cost-model, parameter, threshold or gate value was changed; no parameter was fitted or selected against this record.
**Reproduction**: `python research/trailing_window_attribution.py` (every number below is printed by that script; it exits 0 with `OVERALL: PASS`).

---

## 0. Preconditions and the integrity of the numbers

| Check | Result |
|---|---|
| Completed US session beyond 2026-10-16 available? | **No** — `research/refresh_raw_cache.py --dry-run` is a no-op for all 8 symbols (SPY 8487, QQQ 6945, IWM 6637, TLT 6094, GLD 5512, EFA 6322, EEM 5916 rows, ^VIX 451, all max 2026-10-16) |
| `research/extend_paper_trading_state.py --dry-run` | "no new completed session", 0 sessions extended, 0 state writes |
| Engine reproduces the committed record? | **Yes, exactly** — one simulation run over the committed raw cache reproduces all 449 committed sessions with `max |net_return − committed| = 0.000e+00`, and likewise `0.000e+00` for `turnover`, `vol_scale`, `dd_scale`, `regime_exposure`, `n_positions` |
| SHA-256 of the state file and of all 19 `data/raw/*.parquet` files before/after the cycle | **unchanged** |
| Canonical trailing 63d Sharpe vs. the stored drift flag | -0.211884 == -0.21188351222842883 (identical) |

**Correction to a Cycle 861 handoff label.** The handoff quoted the trailing window as
"2026-08-21 → 2026-10-16". The committed state shows that date range contains only **40** sessions;
the trailing 63 sessions are **2026-07-21 → 2026-10-16** (the previous 63 are 2026-07-14 →
2026-10-09). The compounded return the handoff quoted (-0.5175%) is the 63-session figure and is
unchanged; only the start-date label was wrong. Every window in this report is the actual
63-session slice of `cumulative_dates`.

The attribution below is therefore computed on the *committed* numbers, not on a re-derived series: the decomposition reuses the engine's own per-session gross return, cost, turnover and overlay scales.

---

## 1. The decomposition that reconciles

### 1.1 Construction

Six nested counterfactual portfolios are built from the same simulation output, each differing from the previous one by exactly one mechanism:

| Level | Definition |
|---|---|
| L0 | raw momentum signal: equal-weight top-50% by 12-1 month momentum, no filter, no overlay, no cost |
| L1 | L0 × SPY-trend regime filter (`regime_exposure` ∈ {0, 1}) |
| L2 | L1 × volatility-targeting scale (`vol_scale` = min(1, 10% / trailing 63d realised vol of the gated portfolio)) |
| L3 | L2 × drawdown scale (`dd_scale` = 0.5 while the overlay drawdown < -15%) |
| L4 | L3 × gross-exposure cap (`max_leverage` = 1.0) = the **gross** portfolio |
| L5 | L4 − cost (`turnover × 3 bp`) = the **committed** record |

Each level is compounded over the window as `C(L) = Π(1 + r_L,t) − 1`, and each mechanism's effect is the difference of two compounded paths. Because the levels form a chain, the effects telescope: **the components sum to the observed compounded return exactly**. The residual is not an unexplained leftover — it is identically `0.000e+00` by construction, and the script prints it for every window (tolerance 1e-6).

### 1.2 Result (compounded returns of the window)

| Component | trailing 63 (2026-07-21 → 2026-10-16) | previous 63 (2026-07-14 → 2026-10-09) | tail 5 (2026-10-12 → 2026-10-16) |
|---|---|---|---|
| **gross signal return (L0)** | **+1.078731%** | +4.393818% | **-4.120856%** |
| filter effect (SPY 200d SMA) | +0.000000% | +0.000000% | +0.000000% |
| overlay effect (vol + drawdown + cap) | **-1.497444%** | -2.546287% | **+1.466867%** |
| — of which volatility overlay | -1.497444% | -2.546287% | +1.466867% |
| — of which drawdown overlay | +0.000000% | +0.000000% | +0.000000% |
| — of which gross-exposure cap | +0.000000% | +0.000000% | +0.000000% |
| **cost drag** (turnover × 3 bp) | **-0.098798%** | -0.100635% | **-0.000903%** |
| **residual** | **+0.000e+00** | +0.000e+00 | +0.000e+00 |
| **observed compounded net return** | **-0.517510%** | +1.746896% | **-2.654892%** |
| arithmetic sum of the daily net returns | -0.435589% | +1.805336% | -2.677129% |
| regime-off sessions / min `dd_scale` | 0 / 1.0000 | 0 / 1.0000 | 0 / 1.0000 |
| mean `vol_scale` / cumulative turnover | 0.5238 / 3.3102 | 0.5084 / 3.2969 | 0.6460 / 0.0307 |

**Reconciliation.** trailing 63: `+1.078731 + 0.000000 - 1.497444 - 0.098798 = -0.517510%` = observed (-0.517510%), residual `0.000e+00`. The same identity holds for the previous window and the tail.

**Reading of the residual.** The residual is zero because the decomposition is a telescoping sequence of paths of the *same* data: every session's net return is reproduced by L5, and each level differs from the previous one by one mechanism. Nothing is left over. (The same identity does not hold in *arithmetic* return space — the window's arithmetic sum is -0.435589% while the compounded return is -0.517510%; the difference is ordinary compounding and is reported separately, not folded into any component.)

### 1.3 Why the window failed the *Sharpe* gate

The gate is `rolling_63d_sharpe ≥ 0.9` on the canonical convention, i.e. `mean(r)·√252 / std(r, ddof=1)`.

| | trailing 63 | previous 63 |
|---|---|---|
| mean daily net return | -0.6914 bp/day (-1.7424% annualised) | +2.8656 bp/day (+7.2213% annualised) |
| daily std (ddof=1) | 51.8011 bp/day (8.2232% annualised) | 48.6225 bp/day (7.7186% annualised) |
| canonical Sharpe | **-0.211884** (FAIL) | +0.935578 (PASS) |
| mean required for Sharpe 0.9 at this dispersion | +2.9368 bp/day (+7.4009% annualised) | +2.7566 bp/day (+6.9467% annualised) |
| gap to the requirement | **-9.1432 pp annualised** | +0.2746 pp annualised |

The window is not unusually volatile (8.22% annualised daily dispersion, only 0.5 pp above the previous window). The gate fails because the **mean** is -9.14 pp annualised short of what the same dispersion would require. The mean is a near-zero number built from a strong positive stretch that a five-session loss wiped out.

---

## 2. Where the deterioration came from (window-to-window)

The two windows overlap in 58 sessions; only 5 sessions left and 5 entered.

| | compounded | arithmetic |
|---|---|---|
| 5 sessions that **left** the window (2026-07-14 → 2026-07-20) | -0.439137% | -0.436205% |
| 5 sessions that **entered** the window (2026-10-12 → 2026-10-16) | **-2.654892%** | -2.677129% |
| swing in the window's compounded return | **-2.264407%** | -2.240924% |

The 58 overlapping sessions are unchanged, so the entire deterioration (+1.746896% → -0.517510%) is the five sessions that entered. Within those five sessions:

| Date | signal (unscaled) | vol-scaled | net | `vol_scale` | `dd_scale` | `regime` | turnover (bp) |
|---|---|---|---|---|---|---|---|
| 2026-10-12 | -52.561 bp | -34.300 bp | -34.315 bp | 0.652581 | 1.0 | 1.0 | 48.795 |
| 2026-10-13 | -34.856 bp | -22.717 bp | -22.719 bp | 0.651720 | 1.0 | 1.0 | 8.607 |
| 2026-10-14 | **-175.674 bp** | -113.504 bp | -113.521 bp | 0.646105 | 1.0 | 1.0 | 56.152 |
| 2026-10-15 | +21.339 bp | +13.836 bp | +13.829 bp | 0.648366 | 1.0 | 1.0 | 22.613 |
| 2026-10-16 | **-175.719 bp** | -110.936 bp | -110.987 bp | 0.631325 | 1.0 | 1.0 | 170.411 |

Two sessions (2026-10-14 and 2026-10-16) carry -351.39 bp of the -417.47 bp unscaled signal loss (84.2%).

---

## 3. Per-asset attribution

### 3.1 Trailing 63 sessions — session-summed contribution (bp), by asset and mechanism

| Asset | signal | filter | vol overlay | drawdown overlay | cap | cost | total |
|---|---|---|---|---|---|---|---|
| IWM | -188.08 | 0.00 | +70.98 | 0.00 | 0.00 | -0.30 | -117.40 |
| GLD | +265.73 | 0.00 | -163.57 | 0.00 | 0.00 | -2.90 | +99.26 |
| EEM | -12.36 | 0.00 | -26.43 | 0.00 | 0.00 | -0.30 | -39.09 |
| QQQ | +59.61 | 0.00 | -42.94 | 0.00 | 0.00 | -0.30 | +16.37 |
| SPY | +36.15 | 0.00 | -20.54 | 0.00 | 0.00 | -4.48 | +11.13 |
| EFA | -22.91 | 0.00 | +10.73 | 0.00 | 0.00 | -1.63 | -13.81 |
| TLT | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | -0.00 | -0.00 |
| **all** | **+138.14** | **0.00** | **-171.77** | **0.00** | **0.00** | **-9.94** | **-43.56** |

The sum of all cells (-43.5589 bp) equals the window's arithmetic sum of daily net returns exactly. Compounded (telescoped over assets on the no-cost paths): IWM -1.168484%, GLD +1.004121%, EEM -0.413881%, QQQ +0.132296%, SPY +0.149031%, EFA -0.121796%, TLT 0.000000%, cost drag -0.098798% → sum -0.517510451% vs. observed -0.517510% (exact).

### 3.2 The five sessions that entered the window

| Asset | signal | vol overlay | cost | total (bp) | compounded contribution |
|---|---|---|---|---|---|
| EEM | -151.24 | +53.88 | -0.02 | -97.38 | -0.970019% |
| QQQ | -140.59 | +50.51 | -0.02 | -90.10 | -0.891772% |
| IWM | -76.26 | +27.57 | -0.02 | -48.71 | -0.481561% |
| SPY | -49.37 | +17.89 | -0.02 | -31.50 | -0.310637% |
| TLT / GLD / EFA | 0.00 | 0.00 | 0.00 | 0.00 | 0.000000% |
| **all** | **-417.46** | **+149.85** | **-0.08** | **-267.69** | **-2.654892%** (sum check) |

Assets held in every one of the five sessions: **SPY, QQQ, IWM, EEM** (equal-weighted at ~16% each before the vol scale, 4 positions). Underlying returns in the two decisive sessions:

| Date | SPY | QQQ | IWM | TLT | GLD | EFA | EEM |
|---|---|---|---|---|---|---|---|
| 2026-10-14 | -108.1 | -196.6 | -192.6 | +66.4 | -148.8 | -69.6 | -205.4 |
| 2026-10-16 | -110.7 | -250.0 | -168.7 | +10.0 | -18.3 | -11.6 | -173.5 |

(bp). The two losing sessions are broad risk-off days: every held asset fell, and the momentum selection happened to hold exactly the four assets that fell hardest (EEM, QQQ, IWM). TLT and GLD, which rose on 2026-10-14, were not held.

---

## 4. The dominant mechanism

### 4.1 For the 63-session window: the volatility-targeting overlay, not the signal

The unscaled momentum signal compounded **+1.078731%** over the trailing 63 sessions. The net record compounded **-0.517510%**. The difference is made of the volatility overlay (**-1.497444%**) and trading costs (**-0.098798%**); the filter, the drawdown overlay and the exposure cap contributed exactly **0.000000%** each.

The mechanism is visible in the overlay's own state:

| | trailing 63 | previous 63 | tail 5 |
|---|---|---|---|
| mean `vol_scale` | 0.5238 | 0.5084 | 0.6460 |
| median `vol_scale` | 0.4661 | 0.4642 | 0.6484 |
| corr(`vol_scale`, signal return) | **-0.2197** | -0.1007 | +0.6799 |
| signal sum on the high-`vol_scale` half | **-5.244338%** | -0.323408% | -0.660779% |
| signal sum on the low-`vol_scale` half | **+6.625738%** | +4.917680% | -3.513933% |
| implied trailing realised vol of the raw signal portfolio (10% / `vol_scale`) | 19.50% annualised | 20.02% annualised | 15.48% annualised |

The volatility scaler is *pro-cyclical with a lag*: it sizes exposure from the trailing 63-day realised volatility of the signal portfolio, so it holds the most exposure when realised vol has been low. In this window the raw signal portfolio ran at ~19.5% annualised volatility (roughly twice its 10% target), so the scaler spent the window de-risked (mean `vol_scale` 0.52) — and it de-risked into the sessions where the signal was making money: the signal's gross return was **+6.63%** on the low-`vol_scale` half of the window and **-5.24%** on the high-`vol_scale` half. The same flip appears in the arithmetic sums (signal +1.381399% → vol-scaled -0.336284%), so it is not a compounding artefact.

### 4.2 For the deterioration (the five sessions that entered): signal failure, cushioned by the overlay

In the five entering sessions the **signal itself** lost -4.120856% unscaled; the volatility overlay *added* +1.466867% (it was scaling ~0.65 of a losing book), and costs took -0.000903%. The filter and the drawdown overlay were inert (0.000000% each).

### 4.3 Stated conclusion

> **The trailing-63-session failure is dominated by the volatility-targeting overlay in the level of the window (-1.497444% of a -0.517510% result, against a *positive* +1.078731% raw signal), and the window-to-window deterioration is dominated by a signal failure in the five entering sessions (-4.120856% unscaled, cushioned to -2.654892% by the overlay). Neither the SPY-trend filter (0.000000%), nor the drawdown overlay (0.000000%), nor trading costs (-0.098798% over the window, -0.000903% over the tail) can account for it.**

The two statements are not in conflict: the overlay was a *drag* over the 58-session stretch (it de-risked the winners) and a *cushion* over the five-session tail (it scaled a losing book down). The window is negative because the two effects net out against a small positive signal.

### 4.4 Falsification conditions

**What would refute "the volatility overlay dominates the window-level shortfall":**

1. The unscaled signal path over the same 63 sessions being negative — it is **+1.078731%**, so this is already excluded by the data.
2. The overlay effect being an artefact of the order in which mechanisms are substituted — the arithmetic-sum version tells the same story (signal +1.381399% → vol-scaled -0.336284%), and the filter/drawdown/cap layers are identically zero, so they cannot absorb or create the effect.
3. The `vol_scale` values being wrong — the engine reproduces every committed `vol_scale` bit-identically (0.000e+00) and the scratch replay reproduces them again bit-identically, so the state is not corrupted.
4. A different ordering (cost applied before the overlay) changing the sign of the conclusion — the cost effect is an additive subtraction in the daily return and is three orders of magnitude smaller; it cannot reverse the ranking.

**What would refute "the deterioration is a signal failure in the five entering sessions":**

1. The unscaled signal path over those five sessions being non-negative — it is **-4.120856%**.
2. The loss being a data artefact (stale or mis-adjusted prices) rather than real moves — the raw cache's 2026-10-14 and 2026-10-16 bars show a *broad* cross-asset selloff with normal volumes (SPY -108.1 bp / -110.7 bp, QQQ -196.6 bp / -250.0 bp, TLT +66.4 bp / +10.0 bp), which is the signature of a real session, not of a corrupted series.
3. The momentum selection being contaminated by look-ahead — the engine computes the signal on the T-1 close and shifts the weights by one day; the replayed positions are the committed ones.

**What would refute the alternatives (i.e. the evidence that rules them out):**

- *"Filter timing failure"*: refuted by the data — 0 of 63 sessions had `regime_exposure = 0.0`; the filter effect is exactly 0.000000%, and SPY was above its 200-day SMA throughout. A filter-timing explanation would require at least one risk-off session in the window.
- *"Drawdown-overlay failure"*: refuted — `dd_scale` = 1.0 on all 63 sessions (the overlay drawdown never reached -15%); effect exactly 0.000000%.
- *"Cost drag"*: refuted as a dominant cause — 3.3102 cumulative turnover → -0.098798% over the window (19.1% of the net shortfall, a real but second-order effect) and -0.000903% over the five entering sessions (0.03% of that loss).
- *"Exposure-cap failure"*: refuted — the pre-cap gross exposure never exceeded 1.0, so the cap never bound (effect exactly 0.000000%).

**Caveat on statistical strength.** Five sessions and two decisive days are a very small sample. The attribution says *where* the loss came from (the momentum selection, in a broad risk-off move, in a risk-on SPY regime); it does not establish that the signal has decayed. With 63 sessions of evidence the trailing window is a *measurement*, not a verdict on the strategy.

---

## 5. The connection to the PSR shortfall

| | 449-session record (ends 2026-10-16) | 444-session record (ends 2026-10-09) |
|---|---|---|
| observed canonical Sharpe (PSR numerator) | 1.748401 | 1.934100 |
| bootstrap standard error (denominator) | 0.690150 | 0.722984 |
| **PSR (normal)** | **0.684041** | 0.762425 |
| PSR (empirical) | 0.741 | 0.763 |
| PSR gate (≥ 0.95) | FAIL | FAIL |

Split of the change (`PSR = Φ((observed − 1.4178) / SE)`):

| Effect | Value |
|---|---|
| numerator effect (observed Sharpe 1.934100 → 1.748401) | **-0.086162** |
| standard-error effect (SE 0.722984 → 0.690150) | +0.007778 |
| interaction | +0.002597 |
| **total** | **-0.078384** |

**The PSR is not 0.684041 because the trailing window dominates the bootstrap.** The five new sessions are 5/449 = 1.11% of the record; the bootstrap SE moved by -0.032834 (-4.5%) and *downwards*, which slightly *helped* the PSR. The movement is 110% numerator-driven: appending the five losing sessions lowered the observed full-period Sharpe by 0.185699 (1.934100 → 1.748401), and that is what moved the PSR.

The PSR shortfall itself has a different, structural cause: the observed Sharpe (1.748401) is *above* the 1.4178 target, but the record is too short for that gap to be resolved. At SE = 0.690150 the record would need an observed Sharpe of **2.552996** to reach PSR 0.95, or an SE of **0.200991** at the observed Sharpe. The 449-session record is nowhere near either. The PSR gate was therefore already failing before the five sessions entered (0.762425 < 0.95, decision INCONCLUSIVE at 444 sessions); the tail moved the value inside the grey zone without changing any verdict.

**Relationship between the two failures.** They are different gates measuring different things: `rolling_63d_sharpe` measures the trailing 63 sessions' *mean* return (now -1.74% annualised against the +7.40% the same dispersion would require), while the PSR measures the *whole record's* Sharpe against the backtest baseline with a standard error that is large because 449 sessions is a short record. The five entering sessions are the common cause of the *deterioration* in both numbers, but the PSR gate would have failed regardless.

---

## 6. Read-only compliance

| Requirement | Status |
|---|---|
| No change to strategy, universe, cost model, parameters, thresholds or the gate table | None — `config/` untouched |
| No change to the committed state, the raw cache or any committed artifact | SHA-256 set unchanged; `git status --porcelain data/` empty |
| Per-asset attribution uses a **scratch** copy of the state | The replay runs on a state copy in a temporary directory outside `data/processed` (removed after the run); the canonical file is opened read-only |
| New read-only script reproduces every number in this report | `python research/trailing_window_attribution.py` → `OVERALL: PASS` |
| Test suite still passes | `python -m pytest -q` → 61 passed (unchanged) |
| No re-fit, no parameter search against this record | This cycle measures and explains only |

**Documented replay tolerance.** The scratch replay reproduces every per-session field bit-identically (`daily_return`, `turnover`, `vol_scale`, `dd_scale`, `regime_exposure` all `0.000e+00`). The NAV differs by at most **4.948e-10**, and the script measures where that comes from: the scratch state is seeded with a vectorised `cumprod` reference path while the committed NAV was accumulated session by session, so the seed already differs by **+4.657e-10** and the last replayed session by **+4.366e-10** — i.e. the 63 replayed sessions accumulated only **-2.910e-11**, pure floating-point association order. The committed record's own NAV path differs from its own compounded path by 4.947651e-10, the same magnitude. The tolerance used is 1e-6 on NAV and 1e-12 on every other field.

---

## 7. What this cycle does *not* claim

- It does not claim the strategy has decayed. It locates the loss: a five-session, two-day risk-off move in the assets the momentum signal happened to hold, plus a volatility overlay that de-risked the winners earlier in the window.
- It does not recommend, and this cycle did not perform, any re-fit, re-selection or threshold change. Any follow-up experiment must be pre-specified and evaluated on data that is not this record.
- It does not claim the PSR gate is reachable. On this record's dispersion it is not; that is a statement about the length of the track record, not about a threshold that should move.
