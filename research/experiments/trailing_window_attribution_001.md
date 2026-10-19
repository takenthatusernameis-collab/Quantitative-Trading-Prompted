# Experiment: Trailing-Window Attribution of the Paper Record (trailing_window_attribution_001)

**Cycle**: 862
**Type**: read-only diagnosis of an existing record. No strategy, universe, cost-model, parameter, threshold or gate value was changed, and no parameter was fitted or selected against this record.
**Report**: `research/reports/trailing_window_attribution_001.md`
**Script**: `research/trailing_window_attribution.py` (read-only; prints every number in the report; exits 0 with `OVERALL: PASS`)

---

## Hypothesis Reference

The promotion decision for the paper record is governed by
`config/promotion_gates.yaml`. After Cycle 861 settled on one Sharpe
convention (`arithmetic_annualized_rf0`, `src.evaluation.sharpe.sharpe_ratio`),
the record's gate table reads:

| Gate | Value | Threshold | Result |
|---|---|---|---|
| `track_record_length` | 449 | ≥ 126 | PASS |
| `full_period_sharpe` | 1.748401 | ≥ 0.9 | PASS |
| `rolling_63d_sharpe` | **-0.211884** | ≥ 0.9 | **FAIL** |
| `max_drawdown` | -0.049857 | ≥ -0.15 | PASS |
| `rolling_63d_max_dd` | -0.038564 | ≥ -0.15 | PASS |
| `regime_flips` | 6 | ≥ 1 | PASS |
| `psr` | **0.684041** | ≥ 0.95 | **FAIL** (grey zone 0.5–0.95) |

**Decision: NO-GO.** The full-period Sharpe passes comfortably while the
trailing 63 sessions fail badly, and that divergence had never been
investigated. Cycle 861 deliberately deferred the question until the
measurement convention was settled, so that it would not be answered on two
definitions of "rolling Sharpe".

**Question under test (diagnostic, not a trading hypothesis)**: *what made the
trailing 63 sessions of the committed record fail the promotion gate, and
which mechanism dominates?* The candidate mechanisms are signal decay,
filter timing, overlay scaling and cost drag.

**Falsification conditions** are stated per mechanism in §5 of the report
(each candidate explanation is paired with the observation that would refute
it, and with the observation that already refutes the alternatives).

---

## Data Used

- **Source**: Yahoo Finance via yfinance, committed cache in `data/raw/*.parquet` (read cache-only, `force=False`; no download, no write)
- **Date range**: raw cache 1993-01-01 → 2026-10-16; paper record 2025-01-02 → 2026-10-16 (449 sessions)
- **Universe**: SPY, QQQ, IWM, TLT, GLD, EFA, EEM
- **Frequency**: daily, close-to-close
- **Point-in-time treatment**: unchanged from the strategy under test — the momentum signal uses the T-1 close (1-day lag), the regime filter uses the same day's close, the volatility and drawdown overlays use only trailing information. The attribution reuses the engine's own per-session output; it introduces no forward-looking step.
- **Missing data**: the fetcher's union-calendar forward fill, unchanged. No new session was available: `refresh_raw_cache.py --dry-run` is a no-op for all 8 symbols, `extend_paper_trading_state.py --dry-run` reports "no new completed session", 0 sessions extended, 0 state writes.

---

## Configuration (unchanged, frozen)

| Item | Value | Source |
|---|---|---|
| Candidate | `tsmomentum_spytrend_001` | `config/simulation_candidate_001.yaml` |
| Signal | 12-1 month time-series momentum, top 50% equal weight | same |
| Universe | SPY, QQQ, IWM, TLT, GLD, EFA, EEM | same |
| Risk overlay | vol target 10% (63d), max leverage 1.0, drawdown cut to 0.5 below -15% | same |
| Regime filter | SPY 200-day SMA, exposure 0.0 below / 1.0 above | same |
| Cost model | 1 bp commission + 2 bp slippage = 3 bp round trip on turnover | same |
| Execution | close-to-close, 1-day signal lag, daily rebalance | same |
| Sharpe convention | `arithmetic_annualized_rf0` | `config/promotion_gates.yaml` (Cycle 861) |
| PSR | seeded moving-block bootstrap, 1000 samples, block 22, seed 20240101, target 1.4178 | `src/evaluation/statistics.py` |

**Number of trials**: 1. This is a deterministic measurement of a fixed record, not a search: no parameter, threshold or configuration was varied, and no candidate was selected.

---

## Splits

None. There is no train/validation/test split because nothing was fitted. The only
"split" is chronological inside the record: the trailing 63 sessions
(2026-07-21 → 2026-10-16), the previous 63 sessions (2026-07-14 → 2026-10-09),
the 5 sessions that entered the window (2026-10-12 → 2026-10-16) and the
5 sessions that left it (2026-07-14 → 2026-07-20). The 58 overlapping
sessions are identical in both windows, which isolates the change.

---

## Method

Six nested counterfactual portfolios are built from one engine run over the
committed cache: L0 raw signal → L1 + SPY-trend filter → L2 + volatility
overlay → L3 + drawdown overlay → L4 + gross-exposure cap (= gross portfolio)
→ L5 − costs (= the committed record). Each mechanism's effect is the
difference of two compounded window paths, so the effects telescope and sum
to the observed compounded return exactly. Per-asset attribution uses the same
chain per asset (session-summed, plus a telescoped compounded view), with
costs attributed per symbol from the engine's trade log.

**Integrity of the measurement** (all verified by the script):

| Check | Result |
|---|---|
| Engine reproduces the committed record | `max |net_return − committed| = 0.000e+00` over all 449 sessions; same for `turnover`, `vol_scale`, `dd_scale`, `regime_exposure`, `n_positions` |
| Scratch incremental replay (state copy outside `data/processed`) | per-session fields bit-identical (0.000e+00); NAV ≤ 4.948e-10, of which only -2.910e-11 is accumulated by the 63 replayed sessions (float association order) |
| SHA-256 of the state file and of all 19 raw parquet files, before/after | unchanged |
| Stored drift flag vs recomputed trailing Sharpe | -0.21188351222842883 == -0.211884 |

---

## Results

### 1. Window decomposition (compounded; residual 0.000e+00 in every window)

| Component | trailing 63 | previous 63 | tail 5 |
|---|---|---|---|
| gross signal return (L0) | **+1.078731%** | +4.393818% | **-4.120856%** |
| filter effect | +0.000000% | +0.000000% | +0.000000% |
| volatility overlay | -1.497444% | -2.546287% | +1.466867% |
| drawdown overlay | +0.000000% | +0.000000% | +0.000000% |
| gross-exposure cap | +0.000000% | +0.000000% | +0.000000% |
| cost drag | -0.098798% | -0.100635% | -0.000903% |
| **observed** | **-0.517510%** | +1.746896% | **-2.654892%** |

### 2. Window-to-window change

5 sessions left (-0.439137% compounded), 5 entered (-2.654892% compounded), 58 unchanged; swing -2.264407%. The deterioration is entirely the five entering sessions.

### 3. Sharpe level

| | trailing 63 | previous 63 |
|---|---|---|
| mean / std (daily) | -0.6914 bp / 51.8011 bp | +2.8656 bp / 48.6225 bp |
| canonical Sharpe | -0.211884 | +0.935578 |
| mean required for Sharpe 0.9 at this dispersion | +2.9368 bp/day | +2.7566 bp/day |
| gap | -9.1432 pp annualised | +0.2746 pp annualised |

### 4. Per-asset attribution (trailing 63, session-summed, bp)

| Asset | signal | vol overlay | cost | total |
|---|---|---|---|---|
| IWM | -188.08 | +70.98 | -0.30 | -117.40 |
| GLD | +265.73 | -163.57 | -2.90 | +99.26 |
| EEM | -12.36 | -26.43 | -0.30 | -39.09 |
| QQQ | +59.61 | -42.94 | -0.30 | +16.37 |
| SPY | +36.15 | -20.54 | -4.48 | +11.13 |
| EFA | -22.91 | +10.73 | -1.63 | -13.81 |
| TLT | 0.00 | 0.00 | -0.00 | -0.00 |
| **all** | +138.14 | -171.77 | -9.94 | **-43.56** (= window arithmetic sum) |

Tail 5 (bp): EEM -151.24 signal / +53.88 overlay; QQQ -140.59 / +50.51; IWM -76.26 / +27.57; SPY -49.37 / +17.89; cost -0.08 in total; sum -267.69 bp.

### 5. Overlay mechanics

| | trailing 63 | previous 63 | tail 5 |
|---|---|---|---|
| mean / median `vol_scale` | 0.5238 / 0.4661 | 0.5084 / 0.4642 | 0.6460 / 0.6484 |
| corr(`vol_scale`, signal return) | -0.2197 | -0.1007 | +0.6799 |
| signal sum, high-`vol_scale` half | -5.244338% | -0.323408% | -0.660779% |
| signal sum, low-`vol_scale` half | +6.625738% | +4.917680% | -3.513933% |
| implied realised vol of the raw signal portfolio | 19.50% ann. | 20.02% ann. | 15.48% ann. |

### 6. PSR attribution (449 vs 444 sessions)

| | 449 sessions | 444 sessions |
|---|---|---|
| observed Sharpe | 1.748401 | 1.934100 |
| bootstrap SE | 0.690150 | 0.722984 |
| PSR (normal) | 0.684041 | 0.762425 |
| PSR (empirical) | 0.741 | 0.763 |

Numerator effect -0.086162, standard-error effect +0.007778, interaction +0.002597, total -0.078384. The trailing window does **not** dominate the bootstrap (5/449 = 1.11% of the record; the SE fell). The PSR gate failed before the tail as well (0.762425 < 0.95). At SE 0.690150 the record would need an observed Sharpe of 2.552996 (or an SE of 0.200991 at the observed Sharpe) to reach PSR 0.95.

### 7. Dominant mechanism (as stated in the report)

- **Window level**: the volatility-targeting overlay (-1.497444% of a -0.517510% result, against a *positive* +1.078731% raw signal). It is pro-cyclical with a lag: it de-risked the sessions where the signal was making money.
- **Deterioration**: a signal failure in the five entering sessions (-4.120856% unscaled, cushioned to -2.654892% by the overlay). Two sessions (2026-10-14, 2026-10-16) carry 84.2% of it, and they are broad risk-off days in the four assets the momentum signal held (SPY, QQQ, IWM, EEM).
- **Excluded by the data**: the SPY-trend filter (0 of 63 sessions risk-off, effect 0.000000%), the drawdown overlay (`dd_scale` 1.0 throughout, effect 0.000000%), the gross-exposure cap (never bound, effect 0.000000%) and cost drag (-0.098798% over the window, -0.000903% over the tail).

---

## Reproduction

```bash
python -m pytest -q                                  # 61 passed
python research/trailing_window_attribution.py       # OVERALL: PASS (exit 0)
python research/sharpe_convention_audit.py           # gate table and Sharpe scales
python research/go_no_go_evaluation.py               # side_effect_free / evaluation_deterministic
python research/drift_persistence_report.py          # stored == recomputed
python research/_tmp_cycle77_verify.py               # OVERALL: PASS
python .github/scripts/test_kilo_supervisor_loop.py
git status --porcelain data/                         # must be empty
```

Environment note: the runner image ships without the Python dependencies;
install `requirements.txt` (unmodified) before running the commands above.

---

## Decision label

**Exploratory / diagnostic, not a fix.** The cycle produced no new alpha claim
and no change to the strategy, the gates or the record. The promotion decision
remains **NO-GO** (failed gates: `rolling_63d_sharpe`, `psr`); the drift flag
`low_rolling_sharpe` (-0.21188351222842883, 5 consecutive trading days below
0.5, 2026-10-12 → 2026-10-16) is unchanged. The attribution localises the
loss; it does not establish that the signal has decayed, and it recommends no
re-fit.
