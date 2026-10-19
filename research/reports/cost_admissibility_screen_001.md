# Cost-Admissibility Screen (cost_admissibility_screen_001, Cycle 881; extended in Cycle 882)

**Generated:** 2026-10-19 | **code revision:** cfe92d6
**Tool:** `research/cost_admissibility_screen.py` (read-only, deterministic, exit 0 on `OVERALL: PASS`)
**Cost model:** the repository's flat model, `get_cost_params()` = 1 bp commission + 2 bp slippage
= **3.0 bp per unit of weight change**; sensitivity rows 3 / 5 / 10 bp per unit.

## What changed in Cycle 882

The tool was **extended, not duplicated**. Three candidates were added
(`csmomentum_001`, `sectorrotation_001`, `macroregime_001`), one decision number was added (the
**gate headroom**) and the shortlist's cost column was completed for every row.

* **No number that Cycle 881 published has changed.** The three Cycle 881 blocks carry the same
  values to the same precision; the only additions inside them are the new gate-headroom lines
  and the new canonical-scale column of the cost-sensitivity table, plus the two new
  "reproduction of the committed records" tables.
* The three new candidates are built on the repository's **already-validated config-faithful
  month-end construction** (`src/backtest/rebalance.py`, Cycle 870) through the existing research
  tools `research/month_end_candidate_reaudit.py` (Cycle 871) and
  `research/sectorrotation_long_sample_feasibility.py` (Cycle 869). The defective calendar rule
  and the daily re-rank path are not used, and no parameter, universe, cost model, gate or
  threshold is changed.

## Why this screen exists

Cycle 880 rejected the overnight-session capture candidate `overnight_capture_001` on **cost**:
its gross overnight premium is +9.16%/yr, but an overnight-only leg must be flat during the
day, so it round-trips **twice per session** -> 504 units of annual turnover -> **15.12%/yr** of
cost at 3 bp/unit, i.e. more than the gross premium. The shortlist
(`research/reports/opportunity_shortlist.md`) ranks candidates by *gross* effect size and states
no candidate's annualized cost drag, so the same failure mode can recur silently for the next
candidate. This screen is that missing column.

Cycle 880 also published an **erratum**: a stated cost drag of "1.51%/yr" that was really
15.12%/yr. Nothing in the repository checked a stated drag against the turnover the strategy
actually incurs. This cycle adds that check as a **mechanical guard** (section 5).

## Headline

| Candidate | Gross annualized signal | Annual turnover (units/yr) | Drag @3 bp | Drag @5 bp | Drag @10 bp | Break-even cost | Min gross signal needed @3 bp | Admissibility | Gate headroom (WF Sharpe = 0.9) |
|---|---|---|---|---|---|---|---|---|---|
| `overnight_capture_001` | +9.1558% | 504.00 | +15.1200% | +25.2000% | +50.4000% | 1.7385 bp/unit | +15.1200% | **INADMISSIBLE** | 0.4719 bp/unit |
| `calendar_effects_001` | +2.7326% | 24.13 | +0.7239% | +1.2064% | +2.4128% | 11.1639 bp/unit | +0.7239% | **ADMISSIBLE** | -16.7460 bp/unit (negative: the candidate would have to be **paid** to trade to reach the gate) |
| `tsmomentum_spytrend_001` | +13.8825% | 12.16 | +0.3649% | +0.6082% | +1.2165% | 106.7540 bp/unit | +0.3649% | **ADMISSIBLE** | 37.5114 bp/unit |
| `csmomentum_001` | +9.4355% | 2.23 | +0.0668% | +0.1114% | +0.2227% | 402.3209 bp/unit | +0.0668% | **ADMISSIBLE** | -30.0967 bp/unit (negative: the candidate would have to be **paid** to trade to reach the gate) |
| `sectorrotation_001` | +7.2161% | 3.00 | +0.0899% | +0.1498% | +0.2996% | 231.7102 bp/unit | +0.0899% | **ADMISSIBLE** | -25.3137 bp/unit (negative: the candidate would have to be **paid** to trade to reach the gate) |
| `macroregime_001` | +6.9222% | 3.70 | +0.1110% | +0.1851% | +0.3701% | 180.2653 bp/unit | +0.1110% | **ADMISSIBLE** | none (no cost level in [-100, 1000] bp/unit reaches the gate) |

Read the verdict column as a **necessary, not sufficient** condition (section 6).

## Findings

1. **`overnight_capture_001` is INADMISSIBLE at the repository's own cost model.** Its gross signal
   is +9.1558%/yr against a required minimum of
   +15.1200%/yr, i.e. only **0.606x** of what its
   own turnover requires. It stops covering its costs at **1.7385 bp/unit**, which is
   57.9% of the 3.0 bp/unit the model
   charges, and it needs a cost of only **0.2912 bp/unit** to match passive
   close-to-close holding of the identical basket on the identical folds. Cycle 880's rejection
   is reproduced from the committed artifacts and its arithmetic is now mechanically checkable.
2. **`calendar_effects_001` is ADMISSIBLE on cost but has no edge the cost can pay for.** Its
   break-even cost is 11.1639 bp/unit (3.72x the model
   cost) and its gross signal is 3.775x the minimum it needs, so the cost screen
   clears it. But the *parity* cost is **negative**: to merely match passive close-to-close
   holding of the same basket on the same folds it would have to be **paid
   22.6852 bp/unit** of turnover. Its gross signal is *worse* than the passive
   basket's, and no positive cost level closes that gap. Cost-admissibility is therefore **not**
   evidence of an edge, and the screen must never be read as one.
3. **The incumbent is ADMISSIBLE with a very large margin.** Its break-even cost is
   106.7540 bp/unit (35.6x the model cost) and it still
   beats the passive 1/7 basket on the same folds at **32.3052 bp/unit**
   (10.8x the model cost). Its gross signal is
   38.04x the minimum it needs. This is the quantitative sense in which the
   incumbent's ranking is not a close call.
4. **The shortlist's gross-effect ranking is not preserved by the cost screen.** Ranked by
   break-even cost the three candidates screened in Cycle 881 are
   `tsmomentum_spytrend_001` (106.7540 bp/unit) >
   `calendar_effects_001` (11.1639 bp/unit) >
   `overnight_capture_001` (1.7385 bp/unit), whereas the shortlist's ranking is by gross
   effect size and states no cost column at all. **The cost screen has to be applied before a
   candidate is short-listed, not after it has been back-tested.**
5. **The three remaining shortlist candidates are all ADMISSIBLE on cost, and the shortlist's
   cost column is now complete.** `csmomentum_001` (2.2270
   units of annual turnover, +0.0668%/yr of drag at 3 bp/unit,
   402.32 bp/unit break-even),
   `sectorrotation_001` (2.9961 units,
   +0.0899%/yr, 231.71 bp/unit) and
   `macroregime_001` (3.7011 units,
   +0.1110%/yr, 180.27 bp/unit)
   each carry a gross signal that is 141.2x, 80.3x and
   62.3x what their own turnover requires. All three re-derive their committed
   published records exactly (section 3.2), so the cost column is measured, not estimated.
6. **Their headroom is survival, not edge.** The **gate headroom** - the cost per unit at which
   the candidate's net walk-forward mean OOS Sharpe falls to the repository's own 0.9 promotion
   threshold - is **negative for all three**: `csmomentum_001` -30.0967 bp/unit,
   `sectorrotation_001` -25.3137 bp/unit and `macroregime_001` *no crossing at all*
   (its canonical walk-forward mean OOS Sharpe is only
   0.4733 before any cost is charged, against the 0.90 gate).
   A negative gate headroom means the candidate would have to be **paid** to trade to reach the
   gate; no cost level, and no rebate, promotes it. Their **benchmark-parity costs are negative
   as well** (-5.3347, -31.1587 and -86.1521 bp/unit): at *zero* cost
   they already fail to match passive close-to-close holding of the same basket on the same folds.
   The overnight candidate is the mirror image: its gate headroom is positive
   (0.4719 bp/unit) but far below the 3.0 bp/unit the model
   charges, so it cannot be promoted at the model's cost either. Only the incumbent has real
   headroom (37.5114 bp/unit, 12.5x the model cost).
7. **Answer to this cycle's objective question: none of the remaining candidates is worth a
   promotion-gate test, and the headroom they have is only survival.** `csmomentum_001`,
   `sectorrotation_001` and `macroregime_001` survive their own costs with a very large margin,
   but every one of them is *below* the repository's 0.9 walk-forward gate before a single basis
   point is charged, and every one of them is *behind* the passive basket on the same folds at
   zero cost. Their cost headroom is a statement about how little they trade, not about an
   edge. Consequently the shortlist's remaining rows support **no further candidate evaluation**:
   the three candidates stay **Rejected/Failed** on their own pre-registered gates
   (`research/experiments/month_end_candidate_reaudit_001.md` and
   `research/reports/sectorrotation_long_sample_feasibility_001.md`), and the cost screen adds no
   candidate. The incumbent's headroom is likewise only *survival*; its edge is established by its
   own walk-forward record, not by this screen.

## 1. Method

For each candidate the screen rebuilds, from the committed cache and the committed artifacts
only:

* the candidate's **daily gross return series** (zero cost), and
* the candidate's **daily turnover series** (units of weight change per session),

then computes, on the candidate's own committed window:

1. **annualized gross signal** = `(1 + gross).prod() ** (252/n) - 1` (geometric annualization
   of the zero-cost return series);
2. **annualized cost drag** at 3 / 5 / 10 bp per unit
   = `mean(daily turnover) * 252 * cost_bps / 10000` (the arithmetic annualization of the daily
   cost series; this is the definition the Cycle 880 report used);
3. **net annualized return** at each cost row, and the net canonical Sharpe;
4. **break-even cost per unit**: the cost at which the net annualized return is exactly zero
   (bisection on a monotone-decreasing objective);
5. **cost per unit at which the candidate's net walk-forward Sharpe equals the same-fold
   close-to-close benchmark's** (the candidate and the benchmark are evaluated on the *same*
   folds and at the *same* cost level, so the comparison is like-for-like);
6. **minimum gross signal required for admissibility** at 3 bp/unit, which is by definition the
   candidate's own annualized cost drag at 3 bp/unit;
7. the **admissibility verdict**: ADMISSIBLE when the net annualized return at 3 bp/unit is
   positive, INADMISSIBLE otherwise;
8. the **gate headroom**: the cost per unit at which the candidate's net walk-forward mean OOS
   Sharpe falls to the repository's own promotion threshold of
   0.90 (`AGENTS.md`, `config/promotion_gates.yaml`,
   `wf_mean_oos_sharpe_min` in every frozen candidate configuration). It is measured on the
   **canonical** scale (`arithmetic_annualized_rf0`), the single gate convention the repository
   declares, and the backtest-baseline scale is published next to it because the candidate
   records quote their walk-forward means on that scale. The screen also publishes the
   candidate's walk-forward mean OOS Sharpe **at zero cost**, because a candidate that is
   already below the gate before a basis point is charged has no headroom at all, and a
   **negative** headroom means the candidate would have to be *paid* to trade to reach the gate.

The **benchmark** is a close-to-close equal-weight buy-and-hold of the candidate's own universe
on the candidate's own folds, with one unit of turnover in the first session and none afterwards
(the repository's own `1/N Equal-Weight` convention; for `overnight_capture_001` this is exactly
the benchmark Cycle 880 published). A symbol without a price history yet contributes zero, i.e.
the remainder is held in cash. The three candidates with a staggered-inception universe
(`csmomentum_001`: 18 ETFs, `sectorrotation_001`: 9 sector ETFs, `macroregime_001`: 7 ETFs) use
that cash rule explicitly, because otherwise a symbol without a price yet contributes a NaN to
the whole benchmark return and silently removes every fold that overlaps the gap. The three
candidates of Cycle 881 keep their original benchmark, so their published numbers do not move.

**What this cycle does not do.** No candidate is re-optimized, no parameter is selected, no
threshold is changed, no gate is re-thresholded, and no candidate's published verdict is
re-decided. The walk-forward statistics are re-derived only to (a) validate that the screen
reproduces the committed records and (b) place the candidate and its benchmark on identical
folds. A re-derivation that does not match a committed record is reported as a **FAIL**, never
re-tuned.

## 2. Candidates screened

### Overnight-session capture (overnight leg, 1/3 SPY/QQQ/IWM)

* candidate id: `overnight_capture_001` (role: candidate)
* universe: SPY, QQQ, IWM
* screen window: 2000-05-26 -> 2026-10-16 (6637 sessions)
* walk-forward: 33 folds, research/overnight_capture_backtest.py (Cycle 880)

| Quantity | Value |
|---|---|
| Annualized turnover (units of weight change / yr) | 504.0000 |
| **Annualized gross signal (zero cost, geometric)** | **+9.1558%** |
| Annualized gross signal (arithmetic, zero cost) | +9.5116% |
| **Minimum gross signal required for admissibility at 3 bp/unit** | **+15.1200%** |
| Gross signal surplus vs the requirement | -5.9642% |
| **Break-even cost per unit (net annualized return = 0)** | **1.7385 bp/unit** |
| Cost per unit at which the net WF Sharpe equals the same-fold benchmark's | 0.2912 bp/unit |
| Cost per unit at which the net full-window canonical Sharpe equals the benchmark's | 0.7806 bp/unit |
| WF mean OOS Sharpe (3 bp/unit) | -0.599718 |
| WF mean OOS Sharpe, canonical scale (3 bp/unit) | -0.408532 |
| Benchmark WF mean OOS Sharpe (3 bp/unit, same folds) | 0.844696 |
| Positive fold rate / pooled OOS trades | 15.1515% / 8016 |
| **Admissibility verdict (3 bp/unit)** | **INADMISSIBLE** |
| WF mean OOS Sharpe at **zero** cost (canonical scale) | 1.144231 |
| Promotion threshold (walk-forward mean OOS Sharpe) | 0.90 |
| **Gate headroom: cost per unit at which the net WF mean OOS Sharpe falls to 0.90 (canonical scale, 33 folds)** | **0.4719 bp/unit** |
| Gate headroom, backtest-baseline scale (the scale of the candidate records) | 0.1944 bp/unit |

Cost sensitivity of the screen's own quantities:

| Cost (bp/unit) | Annualized cost drag | Net annualized return | Net canonical Sharpe | WF mean OOS Sharpe | WF mean OOS Sharpe (canonical) |
|---|---|---|---|---|---|
| 3 | +15.1200% | -6.1612% | -0.4590 | -0.5997 | -0.4085 |
| 5 | +25.2000% | -15.1631% | -1.2840 | -1.5469 | -1.4437 |
| 10 | +50.4000% | -34.0807% | -3.3465 | -3.5375 | -4.0316 |

Provenance: config = config/overnight_capture_001.yaml; config_sha256[:12] = bb44adfbc500; price_cache = data/raw/{SPY,QQQ,IWM}.parquet; evaluation_script = research/overnight_capture_backtest.py (Cycle 880); hypothesis = research/hypotheses/overnight_capture_001.md

Notes: none.

### Turn-of-month window exposure (1/3 SPY/QQQ/IWM, pre=1/post=3)

* candidate id: `calendar_effects_001` (role: candidate)
* universe: SPY, QQQ, IWM
* screen window: 2000-05-26 -> 2026-10-09 (6632 sessions)
* walk-forward: 33 folds, research/run_cycle18.py (Cycle 18)

| Quantity | Value |
|---|---|
| Annualized turnover (units of weight change / yr) | 24.1285 |
| **Annualized gross signal (zero cost, geometric)** | **+2.7326%** |
| Annualized gross signal (arithmetic, zero cost) | +3.1356% |
| **Minimum gross signal required for admissibility at 3 bp/unit** | **+0.7239%** |
| Gross signal surplus vs the requirement | +2.0087% |
| **Break-even cost per unit (net annualized return = 0)** | **11.1639 bp/unit** |
| Cost per unit at which the net WF Sharpe equals the same-fold benchmark's | -22.6852 bp/unit |
| Cost per unit at which the net full-window canonical Sharpe equals the benchmark's | -4.9885 bp/unit |
| WF mean OOS Sharpe (3 bp/unit) | -0.025432 |
| WF mean OOS Sharpe, canonical scale (3 bp/unit) | 0.260782 |
| Benchmark WF mean OOS Sharpe (3 bp/unit, same folds) | 0.844696 |
| Positive fold rate / pooled OOS trades | 42.4242% / 761 |
| **Admissibility verdict (3 bp/unit)** | **ADMISSIBLE** |
| WF mean OOS Sharpe at **zero** cost (canonical scale) | 0.358585 |
| Promotion threshold (walk-forward mean OOS Sharpe) | 0.90 |
| **Gate headroom: cost per unit at which the net WF mean OOS Sharpe falls to 0.90 (canonical scale, 33 folds)** | **-16.7460 bp/unit (negative: the candidate would have to be **paid** to trade to reach the gate)** |
| Gate headroom, backtest-baseline scale (the scale of the candidate records) | -24.3080 bp/unit (negative: the candidate would have to be **paid** to trade to reach the gate) |

Cost sensitivity of the screen's own quantities:

| Cost (bp/unit) | Annualized cost drag | Net annualized return | Net canonical Sharpe | WF mean OOS Sharpe | WF mean OOS Sharpe (canonical) |
|---|---|---|---|---|---|
| 3 | +0.7239% | +1.9913% | 0.2573 | -0.0254 | 0.2608 |
| 5 | +1.2064% | +1.5000% | 0.2057 | -0.0915 | 0.1956 |
| 10 | +2.4128% | +0.2816% | 0.0770 | -0.2545 | 0.0332 |

Provenance: config = config/calendar_effects_001.yaml; config_sha256[:12] = ea4e13ef7c34; price_cache = data/raw/{SPY,QQQ,IWM}.parquet; committed_weights = data/processed/weights_calendar_effects_001.parquet; committed_simulation = data/processed/simulation_calendar_effects_001.parquet; evaluation_script = research/run_cycle18.py (Cycle 18); hypothesis = research/hypotheses/calendar_effects_001.md

Notes: none.

### TSMOM incumbent (226d lookback, 21d skip, top-50%, vol 10%, DD 15%, SPY 200d SMA)

* candidate id: `tsmomentum_spytrend_001` (role: incumbent)
* universe: SPY, QQQ, IWM, TLT, GLD, EFA, EEM
* screen window: 1993-01-29 -> 2026-10-09 (8482 sessions)
* walk-forward: 48 folds, research/run_cycle7.py (Cycle 7) / committed artifact

| Quantity | Value |
|---|---|
| Annualized turnover (units of weight change / yr) | 12.1645 |
| **Annualized gross signal (zero cost, geometric)** | **+13.8825%** |
| Annualized gross signal (arithmetic, zero cost) | +13.3822% |
| **Minimum gross signal required for admissibility at 3 bp/unit** | **+0.3649%** |
| Gross signal surplus vs the requirement | +13.5175% |
| **Break-even cost per unit (net annualized return = 0)** | **106.7540 bp/unit** |
| Cost per unit at which the net WF Sharpe equals the same-fold benchmark's | 32.3052 bp/unit |
| Cost per unit at which the net full-window canonical Sharpe equals the benchmark's | 72.1446 bp/unit |
| WF mean OOS Sharpe (3 bp/unit) | 0.928608 |
| WF mean OOS Sharpe, canonical scale (3 bp/unit) | 1.499856 |
| Benchmark WF mean OOS Sharpe (3 bp/unit, same folds) | 0.705721 |
| Positive fold rate / pooled OOS trades | 95.8333% / 6071 |
| **Admissibility verdict (3 bp/unit)** | **ADMISSIBLE** |
| WF mean OOS Sharpe at **zero** cost (canonical scale) | 1.555847 |
| Promotion threshold (walk-forward mean OOS Sharpe) | 0.90 |
| **Gate headroom: cost per unit at which the net WF mean OOS Sharpe falls to 0.90 (canonical scale, 48 folds)** | **37.5114 bp/unit** |
| Gate headroom, backtest-baseline scale (the scale of the candidate records) | 19.9509 bp/unit |

Cost sensitivity of the screen's own quantities:

| Cost (bp/unit) | Annualized cost drag | Net annualized return | Net canonical Sharpe | WF mean OOS Sharpe | WF mean OOS Sharpe (canonical) |
|---|---|---|---|---|---|
| 3 | +0.3649% | +13.4685% | 1.4960 | 0.9286 | 1.4999 |
| 5 | +0.6082% | +13.1933% | 1.4688 | 0.9795 | 1.4648 |
| 10 | +1.2165% | +12.5081% | 1.4003 | 1.0017 | 1.3787 |

Provenance: config = config/simulation_candidate_001.yaml; config_sha256[:12] = 3c8f5b899f1f; committed_simulation = data/processed/simulation_candidate_001.parquet; committed_weights = data/processed/weights_full_history.parquet; price_cache = data/raw/{SPY,QQQ,IWM,TLT,GLD,EFA,EEM}.parquet; evaluation_script = research/run_cycle7.py (Cycle 7) / committed artifact; hypothesis = research/experiments/tsmomentum_regime_filter_wf_001.md

Notes: none.

### Long-only cross-sectional momentum, 18-ETF universe (month-end, top 50%)

* candidate id: `csmomentum_001` (role: candidate)
* universe: SPY, QQQ, IWM, TLT, GLD, DBC, VNQ, EFA, EEM, XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY
* screen window: 1994-03-01 -> 2026-10-09 (8208 sessions)
* walk-forward: 48 folds, research/month_end_candidate_reaudit.py (Cycle 871)

| Quantity | Value |
|---|---|
| Annualized turnover (units of weight change / yr) | 2.2270 |
| **Annualized gross signal (zero cost, geometric)** | **+9.4355%** |
| Annualized gross signal (arithmetic, zero cost) | +10.4425% |
| **Minimum gross signal required for admissibility at 3 bp/unit** | **+0.0668%** |
| Gross signal surplus vs the requirement | +9.3687% |
| **Break-even cost per unit (net annualized return = 0)** | **402.3209 bp/unit** |
| Cost per unit at which the net WF Sharpe equals the same-fold benchmark's | -5.3347 bp/unit |
| Cost per unit at which the net full-window canonical Sharpe equals the benchmark's | 112.2549 bp/unit |
| WF mean OOS Sharpe (3 bp/unit) | 0.697524 |
| WF mean OOS Sharpe, canonical scale (3 bp/unit) | 0.840389 |
| Benchmark WF mean OOS Sharpe (3 bp/unit, same folds) | 0.714520 |
| Positive fold rate / pooled OOS trades | 79.1667% / 400 |
| **Admissibility verdict (3 bp/unit)** | **ADMISSIBLE** |
| WF mean OOS Sharpe at **zero** cost (canonical scale) | 0.845822 |
| Promotion threshold (walk-forward mean OOS Sharpe) | 0.90 |
| **Gate headroom: cost per unit at which the net WF mean OOS Sharpe falls to 0.90 (canonical scale, 48 folds)** | **-30.0967 bp/unit (negative: the candidate would have to be **paid** to trade to reach the gate)** |
| Gate headroom, backtest-baseline scale (the scale of the candidate records) | -96.7205 bp/unit (negative: the candidate would have to be **paid** to trade to reach the gate) |

Cost sensitivity of the screen's own quantities:

| Cost (bp/unit) | Annualized cost drag | Net annualized return | Net canonical Sharpe | WF mean OOS Sharpe | WF mean OOS Sharpe (canonical) |
|---|---|---|---|---|---|
| 3 | +0.0668% | +9.3625% | 0.6151 | 0.6975 | 0.8404 |
| 5 | +0.1114% | +9.3139% | 0.6125 | 0.6934 | 0.8368 |
| 10 | +0.2227% | +9.1925% | 0.6059 | 0.6832 | 0.8277 |

Provenance: config = config/csmomentum_candidate_001.yaml; config_sha256[:12] = 296a619f7942; price_cache = data/raw/*.parquet (18 ETFs, cache only, no fetch); evaluation_script = research/month_end_candidate_reaudit.py (Cycle 871); schedule = src/backtest/rebalance.py:build_month_end_weights (Cycle 870); hypothesis = research/hypotheses/csmomentum_001.md; screen_window = invested sample (first non-zero position .. 2026-10-09)

Notes: The trade-count and per-fold turnover convention of the Cycle 871 record (the weight frame is sliced per fold) is preserved, so the screen's pooled out-of-sample trade count is directly comparable with the published 400.

### Sector rotation, 9 GICS sector ETFs (month-end, top 50%)

* candidate id: `sectorrotation_001` (role: candidate)
* universe: XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY
* screen window: 2000-02-01 -> 2026-10-08 (6712 sessions)
* walk-forward: 36 folds, research/sectorrotation_long_sample_feasibility.py (Cycle 869)

| Quantity | Value |
|---|---|
| Annualized turnover (units of weight change / yr) | 2.9961 |
| **Annualized gross signal (zero cost, geometric)** | **+7.2161%** |
| Annualized gross signal (arithmetic, zero cost) | +8.5908% |
| **Minimum gross signal required for admissibility at 3 bp/unit** | **+0.0899%** |
| Gross signal surplus vs the requirement | +7.1262% |
| **Break-even cost per unit (net annualized return = 0)** | **231.7102 bp/unit** |
| Cost per unit at which the net WF Sharpe equals the same-fold benchmark's | -31.1587 bp/unit |
| Cost per unit at which the net full-window canonical Sharpe equals the benchmark's | 5.2023 bp/unit |
| WF mean OOS Sharpe (3 bp/unit) | 0.709767 |
| WF mean OOS Sharpe, canonical scale (3 bp/unit) | 0.847243 |
| Benchmark WF mean OOS Sharpe (3 bp/unit, same folds) | 0.781687 |
| Positive fold rate / pooled OOS trades | 83.3333% / 215 |
| **Admissibility verdict (3 bp/unit)** | **ADMISSIBLE** |
| WF mean OOS Sharpe at **zero** cost (canonical scale) | 0.852863 |
| Promotion threshold (walk-forward mean OOS Sharpe) | 0.90 |
| **Gate headroom: cost per unit at which the net WF mean OOS Sharpe falls to 0.90 (canonical scale, 36 folds)** | **-25.3137 bp/unit (negative: the candidate would have to be **paid** to trade to reach the gate)** |
| Gate headroom, backtest-baseline scale (the scale of the candidate records) | -87.7239 bp/unit (negative: the candidate would have to be **paid** to trade to reach the gate) |

Cost sensitivity of the screen's own quantities:

| Cost (bp/unit) | Annualized cost drag | Net annualized return | Net canonical Sharpe | WF mean OOS Sharpe | WF mean OOS Sharpe (canonical) |
|---|---|---|---|---|---|
| 3 | +0.0899% | +7.1200% | 0.4724 | 0.7098 | 0.8472 |
| 5 | +0.1498% | +7.0559% | 0.4691 | 0.7056 | 0.8435 |
| 10 | +0.2996% | +6.8960% | 0.4608 | 0.6950 | 0.8341 |

Provenance: config = config/sectorrotation_candidate_001.yaml; config_sha256[:12] = 4f186de79db3; price_cache = data/raw/*.parquet (9 sector ETFs, cache only, no fetch); evaluation_script = research/sectorrotation_long_sample_feasibility.py (Cycle 869); schedule = src/backtest/rebalance.py:build_month_end_weights (Cycle 870); hypothesis = research/hypotheses/sectorrotation_001.md; screen_window = invested sample (2000-02-01 .. 2026-10-08), the record's own sample

Notes: The trade-count convention of the Cycle 869 record (counted from the turnover series) is preserved, so the screen's pooled out-of-sample trade count is directly comparable with the published 215.

### Macro regime overlay (TSMOM + SPY 200d SMA + VIX gate, month-end)

* candidate id: `macroregime_001` (role: candidate)
* universe: SPY, QQQ, IWM, TLT, GLD, EFA, EEM
* screen window: 2005-12-01 -> 2026-10-09 (5246 sessions)
* walk-forward: 24 folds, research/month_end_candidate_reaudit.py (Cycle 871)

| Quantity | Value |
|---|---|
| Annualized turnover (units of weight change / yr) | 3.7011 |
| **Annualized gross signal (zero cost, geometric)** | **+6.9222%** |
| Annualized gross signal (arithmetic, zero cost) | +7.1748% |
| **Minimum gross signal required for admissibility at 3 bp/unit** | **+0.1110%** |
| Gross signal surplus vs the requirement | +6.8112% |
| **Break-even cost per unit (net annualized return = 0)** | **180.2653 bp/unit** |
| Cost per unit at which the net WF Sharpe equals the same-fold benchmark's | -86.1521 bp/unit |
| Cost per unit at which the net full-window canonical Sharpe equals the benchmark's | 41.9769 bp/unit |
| WF mean OOS Sharpe (3 bp/unit) | 0.263566 |
| WF mean OOS Sharpe, canonical scale (3 bp/unit) | 0.460847 |
| Benchmark WF mean OOS Sharpe (3 bp/unit, same folds) | 0.644000 |
| Positive fold rate / pooled OOS trades | 66.6667% / 193 |
| **Admissibility verdict (3 bp/unit)** | **ADMISSIBLE** |
| WF mean OOS Sharpe at **zero** cost (canonical scale) | 0.473297 |
| Promotion threshold (walk-forward mean OOS Sharpe) | 0.90 |
| **Gate headroom: cost per unit at which the net WF mean OOS Sharpe falls to 0.90 (canonical scale, 24 folds)** | **none (no cost level in [-100, 1000] bp/unit reaches the gate)** |
| Gate headroom, backtest-baseline scale (the scale of the candidate records) | none (no cost level in [-100, 1000] bp/unit reaches the gate) |

Cost sensitivity of the screen's own quantities:

| Cost (bp/unit) | Annualized cost drag | Net annualized return | Net canonical Sharpe | WF mean OOS Sharpe | WF mean OOS Sharpe (canonical) |
|---|---|---|---|---|---|
| 3 | +0.1110% | +6.8039% | 0.7212 | 0.2636 | 0.4608 |
| 5 | +0.1851% | +6.7251% | 0.7138 | 0.2549 | 0.4525 |
| 10 | +0.3701% | +6.5282% | 0.6952 | 0.2334 | 0.4317 |

Provenance: config = config/macroregime_candidate_001.yaml; config_sha256[:12] = 76a8c320b25b; price_cache = data/raw/*.parquet (7 ETFs + ^VIX as an input only, cache only); evaluation_script = research/month_end_candidate_reaudit.py (Cycle 871); schedule = src/backtest/rebalance.py:build_month_end_weights (Cycle 870); hypothesis = research/hypotheses/macroregime_001.md; screen_window = invested sample (first non-zero position .. 2026-10-09)

Notes: The trade-count and per-fold turnover convention of the Cycle 871 record (the weight frame is sliced per fold) is preserved, so the screen's pooled out-of-sample trade count is directly comparable with the published 193. The record states the test-window trade days as 84 in its table and as 83 in its prose; the screen compares against the table's 84 and reports the value it derives.


## 3. Reproduction of the committed records

### 3.1 The three candidates screened in Cycle 881

| Candidate | Quantity | Published | Re-derived | Match |
|---|---|---|---|---|
| `overnight_capture_001` | Annualized cost drag at 3 bp/unit | 0.1512 | 0.151200 | yes |
| `overnight_capture_001` | Net WF mean OOS Sharpe | -0.599718 | -0.599718 | yes |
| `overnight_capture_001` | Benchmark WF mean OOS Sharpe | +0.844696 | 0.844696 | yes |
| `calendar_effects_001` | Net WF mean OOS Sharpe | -0.0254 | -0.025432 | yes |
| `calendar_effects_001` | Positive fold rate | 0.424242 | 0.424242 | yes |
| `calendar_effects_001` | Pooled OOS trades | 761 | 761 | yes |
| `tsmomentum_spytrend_001` | Net WF mean OOS Sharpe (48 folds) | 0.9473 | 0.928608 | within the repository's declared tolerance (section 4) |
| `tsmomentum_spytrend_001` | Test-period Sharpe (2018-2026) | 1.4178 | 1.407770 | within the repository's declared tolerance (section 4) |

### 3.2 The three month-end candidates added in Cycle 882

**Tolerance rule.** The committed records quote their numbers as decimal strings, so the
tolerance of every comparison is the unit of that string's last decimal - the repository's own
rule (`research/month_end_candidate_reaudit.py:compare_published`). A 4-decimal published
number is therefore compared with 1e-4, a 2-decimal one with 1e-2, a 6-decimal one with 1e-6,
and a **count** (folds, trade days, pooled trades) with **0** (exact match), because a count is
an integer and no rounding is implied.

| Candidate | Quantity | Published | Re-derived | Tolerance | Match |
|---|---|---|---|---|---|
| `csmomentum_001` | Test-window Sharpe (backtest scale) | 0.4878 | 0.487833 | 1e-04 | yes |
| `csmomentum_001` | Test-window Sharpe (canonical) | 0.6635 | 0.663540 | 1e-04 | yes |
| `csmomentum_001` | Test-window max drawdown | -0.2940 | -0.294002 | 1e-04 | yes |
| `csmomentum_001` | Test-window annualized turnover | 2.47 | 2.468571 | 1e-02 | yes |
| `csmomentum_001` | Test-window trade days | 77 | 77.000000 | 0e+00 | yes |
| `csmomentum_001` | Walk-forward mean OOS Sharpe (backtest scale) | 0.6975 | 0.697524 | 1e-04 | yes |
| `csmomentum_001` | Walk-forward positive fold rate | 0.792 | 0.791667 | 1e-03 | yes |
| `csmomentum_001` | Walk-forward pooled OOS trades | 400 | 400.000000 | 0e+00 | yes |
| `csmomentum_001` | Walk-forward fold count | 48 | 48.000000 | 0e+00 | yes |
| `sectorrotation_001` | Canonical Sharpe (invested sample) | 0.472367 | 0.472367 | 1e-06 | yes |
| `sectorrotation_001` | Annualized turnover (invested sample) | 2.9961 | 2.996067 | 1e-04 | yes |
| `sectorrotation_001` | Trade days (invested sample) | 175 | 175.000000 | 0e+00 | yes |
| `sectorrotation_001` | Walk-forward mean OOS Sharpe (canonical) | 0.847243 | 0.847243 | 1e-06 | yes |
| `sectorrotation_001` | Walk-forward positive fold rate | 0.9167 | 0.916667 | 1e-04 | yes |
| `sectorrotation_001` | Walk-forward pooled OOS trades | 215 | 215.000000 | 0e+00 | yes |
| `sectorrotation_001` | Walk-forward fold count | 36 | 36.000000 | 0e+00 | yes |
| `macroregime_001` | Test-window Sharpe (backtest scale) | 0.1428 | 0.142777 | 1e-04 | yes |
| `macroregime_001` | Test-window Sharpe (canonical) | 0.3823 | 0.382343 | 1e-04 | yes |
| `macroregime_001` | Test-window max drawdown | -0.2240 | -0.223998 | 1e-04 | yes |
| `macroregime_001` | Test-window annualized turnover | 4.22 | 4.217824 | 1e-02 | yes |
| `macroregime_001` | Test-window trade days | 84 | 84.000000 | 0e+00 | yes |
| `macroregime_001` | Walk-forward mean OOS Sharpe (backtest scale) | 0.2636 | 0.263566 | 1e-04 | yes |
| `macroregime_001` | Walk-forward positive fold rate | 0.667 | 0.666667 | 1e-03 | yes |
| `macroregime_001` | Walk-forward pooled OOS trades | 193 | 193.000000 | 0e+00 | yes |
| `macroregime_001` | Walk-forward fold count | 24 | 24.000000 | 0e+00 | yes |

A mismatch here would be a **FAIL** and would be reported, never re-tuned: the screen measures
costs, it does not re-judge a candidate.

## 4. Two disclosed differences (not screen failures)

* **`calendar_effects_001` and `tsmomentum_spytrend_001` artifacts are older than the raw cache.**
  The committed processed artifacts stop at **2026-10-09**; the committed price cache now runs
  to **2026-10-16**. The screen therefore **clips** the price frame to each candidate's
  committed artifact end date before rebuilding anything. Without that clip the rebuilt
  calendar weights would no longer match the committed artifact (max abs weight difference
  0.3333) and the walk-forward would silently change. This is a property of the committed
  artifacts, not a defect of the screen.
* **The incumbent's published baseline is a re-run, the committed artifact is a full-history
  run.** The published numbers (test Sharpe 1.4178, 48-fold WF mean 0.9473) come from a
  configuration re-run with `overlay_warmup: "slice"` (overlay state initialised at the
  evaluation window start, `research/reports/simulation_verification_001.md`). The committed
  full-history artifact carries the overlay state from 1993, so slicing it to 2018+ gives a
  slightly different number. The difference is inside the repository's own declared
  tolerance (`research/run_cycle7.py`: `TOL_SHARPE = 0.02`) and the screen checks exactly that
  tolerance, not a tighter invented one. The screen's incumbent numbers are the
  artifact-derived ones, because the screen is defined to reuse committed artifacts.
* **The screen window of the three month-end candidates is their *invested* sample.** A candidate
  that cannot be invested before its signal warm-up is flat before it, and a flat period carries
  neither signal nor turnover, so the screen measures it from the first session with a non-zero
  position to the end of the committed cache. This is the sample the committed records use
  ("invested sample" in `research/reports/sectorrotation_long_sample_feasibility_001.md`); the
  walk-forward folds are still the candidate's own pre-registered splits, generated from the
  candidate's own sample start, so the fold count and the fold windows are unchanged
  (48 / 36 / 24 folds for `csmomentum_001` / `sectorrotation_001` / `macroregime_001`).
* **The trade-count conventions of the two records differ and both are kept.** The Cycle 871
  record counts a fold's trades from the **sliced weight frame** (the first session of a fold
  contributes no trade), the Cycle 869 record counts them from the **turnover series** (the
  first session of a fold does). The screen keeps each candidate's own convention so that its
  pooled out-of-sample trade count is directly comparable with the number it is checked against
  (`csmomentum_001` 400, `macroregime_001` 193, `sectorrotation_001` 215). The convention only
  affects the trade-count and per-fold turnover columns, never a Sharpe.
* **`macroregime_001`'s record states its test-window trade days twice.** The table of
  `research/experiments/month_end_candidate_reaudit_001.md` says 84 and its prose says 83. The
  screen compares against the table's 84 and reports the value it derives (84), so the
  discrepancy inside the record is visible rather than silently resolved.

## 5. The mechanical guard (Cycle 880 erratum)

`check_cost_drag_consistency(stated_cost_drag, annual_turnover, cost_bps_per_unit, tolerance=1e-9)`
asserts

```
cost_drag == annual_turnover * cost_bps_per_unit / 10000      (within 1e-9)
```

The guard is applied to (a) every cost-drag figure the screen itself states, (b) the drag
figures published in the committed records, and (c) the Cycle 880 erratum value as a
**negative control** at every cost row: a drag understated by a factor of 10 must be
*rejected* (3 bp/unit: stated 0.0151 vs expected 0.151200, abs difference 0.1361; 5 bp/unit:
0.0252 vs 0.252000, 0.2268; 10 bp/unit: 0.0504 vs 0.504000, 0.4536) -- seven to eight orders
of magnitude above the tolerance in every case. `require_cost_drag_consistency` raises
`ValueError`, so a screen that states an inconsistent drag cannot complete. The guard is
unit-tested in `tests/test_cost_admissibility_screen.py`.

## 6. Limitations (necessary, not sufficient)

The screen is a **cost** filter. It is necessary for a candidate to be worth a walk-forward
evaluation and it is **not** sufficient for promotion. In particular it says nothing about:

* the **sign or the statistical significance** of the gross signal (a candidate with a large
  gross signal and a large drag can be "ADMISSIBLE" and still lose money);
* **robustness**, **multiple-testing control**, **out-of-sample stability** or **capacity**;
* costs **not** in the flat per-unit model: borrow, funding, market impact, spread crossing,
  partial fills, exchange fees, or the operational cost of a higher-turnover implementation;
* the difference between a **modelled** cost per unit and an **executed** one;
* the difference between a **backtest** cost model and a **paper-trading** one;
* the **statistical significance** of the walk-forward means the gate headroom is measured on.
  The gate headroom says at which cost the *point estimate* of the walk-forward mean OOS Sharpe
  reaches 0.9; it says nothing about the confidence interval of that estimate, about the
  positive-fold rate, about the pooled trade count (the second promotion gate, > 100 pooled
  out-of-sample trades) or about any other gate of `config/promotion_gates.yaml`;
* the **monotonicity** of the Sharpe in the cost. The break-evens and the gate headroom are
  bisections on a bracket that keeps its sign change, so a reported crossing is a genuine
  crossing; if the objective were not monotone in the cost, the reported value would be *a*
  crossing and not necessarily the outermost one.

A candidate that passes the screen can still be rejected by the promotion gates, and a
candidate that fails the screen is rejected on cost before any further work is justified. The
screen's verdict is **necessary, never sufficient**, and the Cycle 882 addition of the gate
headroom does not change that: it measures how much cost a candidate can afford, not whether it
has an edge.

## 7. Self-checks

| Check | Result | Detail |
|---|---|---|
| `repository_cost_model_is_3_bps_per_unit` | PASS | get_cost_params() -> commission 1.0 bps + slippage 2.0 bps = 3.0 bps per unit of weight change. |
| `overnight_session_leg_decomposition_is_exact` | PASS | (1+overnight)*(1+intraday)-1 == close-to-close to 2.220e-16 over 6637 sessions; 0 missing opens. |
| `calendar_candidate_rebuilds_its_committed_artifacts_exactly` | PASS | the rebuilt turn-of-month weights, gross returns and turnover match data/processed/weights_calendar_effects_001.parquet and data/processed/simulation_calendar_effects_001.parquet with max abs difference 0.000e+00 over 8482 sessions. |
| `incumbent_committed_artifact_is_internally_consistent` | PASS | cost == turnover * 3.0 bp/unit (0.000e+00), net == gross - cost (1.735e-18) and the weight_* columns of data/processed/simulation_candidate_001.parquet equal data/processed/weights_full_history.parquet (1.055e-15); all within the 1e-12 parquet round-trip tolerance. |
| `guard_accepts_the_published_overnight_cost_drag` | PASS | stated 0.1512 == 504.0 units/yr x 3 bp/unit = 0.151200 (abs diff 2.776e-17 <= 1e-09). |
| `guard_rejects_the_cycle_880_factor_10_erratum` | PASS | the stated 0.0151 with 504 units/yr at 3 bp/unit is rejected: expected 0.151200, abs diff 1.361e-01 > 1e-09. |
| `guard_rejects_the_factor_10_erratum_at_every_cost_row` | PASS | a factor-10 understated drag is rejected at 3 bp/unit (abs diff 1.361e-01), 5 bp/unit (abs diff 2.268e-01), 10 bp/unit (abs diff 4.536e-01), every one of them far above the 1e-09 tolerance. |
| `guard_raises_on_an_inconsistent_figure` | PASS | require_cost_drag_consistency raises ValueError on the factor-10 error, so a screen that states an inconsistent drag cannot complete. |
| `every_stated_cost_drag_passes_the_guard` | PASS | each candidate's own stated annualized cost drag equals its own stated annual turnover times the cost per unit to within 1e-9. |
| `overnight_capture_001_reproduces_net_WF_mean_OOS_Sharpe` | PASS | published -0.599718 vs re-derived -0.599718 (abs diff 1.082e-07 <= 1e-06). |
| `overnight_capture_001_reproduces_benchmark_WF_mean_OOS_Sharpe` | PASS | published +0.844696 vs re-derived +0.844696 (abs diff 3.486e-07 <= 1e-06). |
| `overnight_capture_001_reproduces_positive_fold_rate` | PASS | published +0.151515 vs re-derived +0.151515 (abs diff 1.515e-07 <= 1e-06). |
| `overnight_capture_001_reproduces_pooled_oos_trades` | PASS | published 8016 vs re-derived 8016 pooled out-of-sample trades. |
| `calendar_effects_001_reproduces_net_WF_mean_OOS_Sharpe` | PASS | published -0.025400 vs re-derived -0.025432 (abs diff 3.226e-05 <= 1e-04). |
| `calendar_effects_001_reproduces_positive_fold_rate` | PASS | published +0.424242 vs re-derived +0.424242 (abs diff 4.242e-07 <= 1e-04). |
| `calendar_effects_001_reproduces_pooled_oos_trades` | PASS | published 761 vs re-derived 761 pooled out-of-sample trades. |
| `incumbent_walk_forward_has_48_folds` | PASS | the 1993-2026 geometry of the frozen configuration yields 48 folds (the published Cycle 6 record also states 48 folds). |
| `tsmomentum_spytrend_001_reproduces_net_WF_mean_OOS_Sharpe` | PASS | published +0.947300 vs re-derived +0.928608 (abs diff 1.869e-02 <= 2e-02). |
| `csmomentum_001_reproduces_Test_window_Sharpe_(backtest_scale)` | PASS | published +0.487800 vs re-derived +0.487833 (abs diff 3.279e-05 <= 1e-04); source: research/experiments/month_end_candidate_reaudit_001.md (config-faithful column). |
| `csmomentum_001_reproduces_Test_window_Sharpe_(canonical)` | PASS | published +0.663500 vs re-derived +0.663540 (abs diff 4.029e-05 <= 1e-04); source: research/experiments/month_end_candidate_reaudit_001.md (config-faithful column). |
| `csmomentum_001_reproduces_Test_window_max_drawdown` | PASS | published -0.294000 vs re-derived -0.294002 (abs diff 1.868e-06 <= 1e-04); source: research/experiments/month_end_candidate_reaudit_001.md (config-faithful column). |
| `csmomentum_001_reproduces_Test_window_annualized_turnover` | PASS | published +2.470000 vs re-derived +2.468571 (abs diff 1.429e-03 <= 1e-02); source: research/experiments/month_end_candidate_reaudit_001.md (config-faithful column). |
| `csmomentum_001_reproduces_Test_window_trade_days` | PASS | published +77.000000 vs re-derived +77.000000 (abs diff 0.000e+00 <= 0e+00); source: research/experiments/month_end_candidate_reaudit_001.md (config-faithful column). |
| `csmomentum_001_reproduces_Walk_forward_mean_OOS_Sharpe_(backtest_scale)` | PASS | published +0.697500 vs re-derived +0.697524 (abs diff 2.434e-05 <= 1e-04); source: research/experiments/month_end_candidate_reaudit_001.md (config-faithful column). |
| `csmomentum_001_reproduces_Walk_forward_positive_fold_rate` | PASS | published +0.792000 vs re-derived +0.791667 (abs diff 3.333e-04 <= 1e-03); source: research/experiments/month_end_candidate_reaudit_001.md (config-faithful column). |
| `csmomentum_001_reproduces_Walk_forward_pooled_OOS_trades` | PASS | published +400.000000 vs re-derived +400.000000 (abs diff 0.000e+00 <= 0e+00); source: research/experiments/month_end_candidate_reaudit_001.md (config-faithful column). |
| `csmomentum_001_reproduces_Walk_forward_fold_count` | PASS | published +48.000000 vs re-derived +48.000000 (abs diff 0.000e+00 <= 0e+00); source: research/experiments/month_end_candidate_reaudit_001.md (config-faithful column). |
| `csmomentum_001_reproduces_its_committed_published_record` | PASS | all 9 published quantities of csmomentum_001 are reproduced from the committed cache within the tolerance of the record's own last decimal. |
| `sectorrotation_001_reproduces_Canonical_Sharpe_(invested_sample)` | PASS | published +0.472367 vs re-derived +0.472367 (abs diff 4.833e-07 <= 1e-06); source: research/reports/sectorrotation_long_sample_feasibility_001.md. |
| `sectorrotation_001_reproduces_Annualized_turnover_(invested_sample)` | PASS | published +2.996100 vs re-derived +2.996067 (abs diff 3.325e-05 <= 1e-04); source: research/reports/sectorrotation_long_sample_feasibility_001.md. |
| `sectorrotation_001_reproduces_Trade_days_(invested_sample)` | PASS | published +175.000000 vs re-derived +175.000000 (abs diff 0.000e+00 <= 0e+00); source: research/reports/sectorrotation_long_sample_feasibility_001.md. |
| `sectorrotation_001_reproduces_Walk_forward_mean_OOS_Sharpe_(canonical)` | PASS | published +0.847243 vs re-derived +0.847243 (abs diff 2.934e-07 <= 1e-06); source: research/reports/sectorrotation_long_sample_feasibility_001.md. |
| `sectorrotation_001_reproduces_Walk_forward_positive_fold_rate` | PASS | published +0.916700 vs re-derived +0.916667 (abs diff 3.333e-05 <= 1e-04); source: research/reports/sectorrotation_long_sample_feasibility_001.md. |
| `sectorrotation_001_reproduces_Walk_forward_pooled_OOS_trades` | PASS | published +215.000000 vs re-derived +215.000000 (abs diff 0.000e+00 <= 0e+00); source: research/reports/sectorrotation_long_sample_feasibility_001.md. |
| `sectorrotation_001_reproduces_Walk_forward_fold_count` | PASS | published +36.000000 vs re-derived +36.000000 (abs diff 0.000e+00 <= 0e+00); source: research/reports/sectorrotation_long_sample_feasibility_001.md. |
| `sectorrotation_001_reproduces_its_committed_published_record` | PASS | all 7 published quantities of sectorrotation_001 are reproduced from the committed cache within the tolerance of the record's own last decimal. |
| `macroregime_001_reproduces_Test_window_Sharpe_(backtest_scale)` | PASS | published +0.142800 vs re-derived +0.142777 (abs diff 2.306e-05 <= 1e-04); source: research/experiments/month_end_candidate_reaudit_001.md (config-faithful column). |
| `macroregime_001_reproduces_Test_window_Sharpe_(canonical)` | PASS | published +0.382300 vs re-derived +0.382343 (abs diff 4.292e-05 <= 1e-04); source: research/experiments/month_end_candidate_reaudit_001.md (config-faithful column). |
| `macroregime_001_reproduces_Test_window_max_drawdown` | PASS | published -0.224000 vs re-derived -0.223998 (abs diff 2.258e-06 <= 1e-04); source: research/experiments/month_end_candidate_reaudit_001.md (config-faithful column). |
| `macroregime_001_reproduces_Test_window_annualized_turnover` | PASS | published +4.220000 vs re-derived +4.217824 (abs diff 2.176e-03 <= 1e-02); source: research/experiments/month_end_candidate_reaudit_001.md (config-faithful column). |
| `macroregime_001_reproduces_Test_window_trade_days` | PASS | published +84.000000 vs re-derived +84.000000 (abs diff 0.000e+00 <= 0e+00); source: research/experiments/month_end_candidate_reaudit_001.md (config-faithful column). |
| `macroregime_001_reproduces_Walk_forward_mean_OOS_Sharpe_(backtest_scale)` | PASS | published +0.263600 vs re-derived +0.263566 (abs diff 3.388e-05 <= 1e-04); source: research/experiments/month_end_candidate_reaudit_001.md (config-faithful column). |
| `macroregime_001_reproduces_Walk_forward_positive_fold_rate` | PASS | published +0.667000 vs re-derived +0.666667 (abs diff 3.333e-04 <= 1e-03); source: research/experiments/month_end_candidate_reaudit_001.md (config-faithful column). |
| `macroregime_001_reproduces_Walk_forward_pooled_OOS_trades` | PASS | published +193.000000 vs re-derived +193.000000 (abs diff 0.000e+00 <= 0e+00); source: research/experiments/month_end_candidate_reaudit_001.md (config-faithful column). |
| `macroregime_001_reproduces_Walk_forward_fold_count` | PASS | published +24.000000 vs re-derived +24.000000 (abs diff 0.000e+00 <= 0e+00); source: research/experiments/month_end_candidate_reaudit_001.md (config-faithful column). |
| `macroregime_001_reproduces_its_committed_published_record` | PASS | all 9 published quantities of macroregime_001 are reproduced from the committed cache within the tolerance of the record's own last decimal. |
| `tsmomentum_spytrend_001_reproduces_test_period_Sharpe_2018-2026` | PASS | published +1.417800 vs re-derived +1.407770 (abs diff 1.003e-02 <= 2e-02). |
| `benchmark_walk_forward_sharpe_is_cost_invariant` | PASS | the close-to-close benchmark's walk-forward Sharpe is the same at 3 bp/unit and at 10 bp/unit for every candidate (its only turnover is the initial purchase, which sits before the first test window), so the benchmark-parity cost compares the candidate and the benchmark at the same cost level on the same folds. |
| `screen_is_deterministic` | PASS | re-running the screen on the same inputs reproduces the annual turnover, the gross annualized signal, the minimum required gross signal and the WF mean OOS Sharpe bit-for-bit. |
| `no_file_under_data_or_config_changed` | PASS | the SHA-256 fingerprint of all 1844 files under data/ and config/ is identical before and after the run. |

**OVERALL: PASS** (50/50 checks passed)
