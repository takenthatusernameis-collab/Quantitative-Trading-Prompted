# Rolling 63d Gate Evidence Refresh (Cycle 866)

**Type:** read-only, verification-only. No strategy, universe, cost model, parameter, threshold, gate or data change; no re-fit; nothing written outside `research/` and `tests/`.

**Artifacts:** `research/rolling_63d_gate_refresh.py` (read-only tool, `OVERALL: PASS`, 11/11 internal checks) and `tests/test_rolling_63d_gate_refresh.py` (6 regression tests).

---

## 1. Context and why this cycle exists

| Cycle | Question | Answer |
|---|---|---|
| 862 | Why did the trailing 63 sessions underperform? | Vol-targeting overlay (level) + signal failure in the 5 entering sessions (deterioration); PSR shortfall is numerator-driven, not tail-driven |
| 863 | How does the window roll off mechanically? | Under flat continuation the gate never clears within 63 sessions; under record-average continuation it clears at +49 sessions (a mechanical effect, not a forecast) |
| 865 | How long until the PSR gate can clear? | 252–504 further sessions at the record mean — longer than a plausible research cadence |

What was still missing after Cycle 865, and is supplied here:

1. **The empirical base rate of the rolling 63d Sharpe gate on the committed record itself.** Every statement so far about the trailing window was forward-looking (a projection) or backward-looking only for a single window (the attribution). Nothing had asked: *on this record's own history, how often would this gate have passed, where does the current value sit in that distribution, and how long do failing runs usually last?*
2. **Any quantified evidence on the two drawdown gates.** The full-period max DD and the rolling 63d max DD had been reported as single numbers (-4.9857% / -3.8564%) with no history, no worst case, no headroom and no stress bound.
3. **The gap to every promotion threshold expressed in the units of the gate** (Sharpe units, bp/day, percentage points of drawdown, sessions), including a computed counterfactual for the decision that would follow.

## 2. Data, provenance and point-in-time treatment

| Item | Value |
|---|---|
| Record | `data/processed/paper_trading_state.yaml` (committed), `cumulative_returns` |
| Sessions | 449 daily sessions, 2025-01-02 → 2026-10-16 |
| Frequency / netting | daily, net of cost (commission + slippage), paper-trading replay of the frozen candidate |
| Universe | SPY, QQQ, IWM, TLT, GLD, EFA, EEM (`config/simulation_candidate_001.yaml`); regime input ^VIX |
| Sharpe convention | `arithmetic_annualized_rf0`: `mean(r)·252 / (std(r, ddof=1)·√252)`, rf = 0 (`src/evaluation/sharpe.py`, declared in `config/promotion_gates.yaml`) |
| Gate table | `config/promotion_gates.yaml` — 7 gates, thresholds unchanged (126 days, 0.9 Sharpe ×2, -15% DD ×2, 1 regime flip, PSR 0.5/0.95) |
| Point-in-time | No re-fit, no re-simulation, no data acquisition. The committed state is the only input. |
| Precondition | No completed US session beyond 2026-10-16: `python research/refresh_raw_cache.py --dry-run` → `no-op: no completed sessions to append` (all 8 symbols, max date 2026-10-16); `python research/extend_paper_trading_state.py --dry-run` → `no new completed session`, 0 sessions extended, 0 state writes, NAV unchanged at 133,729.224310211. The 2026-10-19 bar is an in-progress session and is excluded by `complete_session_view`. |
| Read-only proof | The tool SHA-256s the state file and all 19 `data/raw/*.parquet` files before and after the run: byte-identical. `git status --porcelain data/` empty. |
| Trials | 1 (deterministic; no parameter search, no tuning) |

## 3. Method

All estimators are the production formulas, re-implemented in the tool and cross-checked against `src/`:

* rolling 63d Sharpe: `sharpe_ratio` over each trailing 63-session window (canonical convention);
* rolling 63d max DD: `cum = cumprod(1+r)`, `peak = maximum.accumulate(cum)`, `dd = (cum/peak − 1).min()` — identical to `src.simulation.evaluation._compute_rolling_metrics`;
* full-period max DD: `src.evaluation.utils.max_drawdown` formula, on the full series;
* gate table and decision: `evaluate_go_no_go` on the committed state (read-only), plus a **counterfactual** evaluation of the record truncated at the last passing rolling window.

Every rolling window on the record is enumerated: 449 − 63 + 1 = **387 windows**, each ending on a committed session date.

## 4. Results

### 4.1 Canonical Sharpe re-derivation (acceptance criterion)

```
canonical full-period Sharpe (re-derived from the committed record): 1.748401
full_period_sharpe gate value                                    : 1.748401  (diff 0.000e+00)
```

### 4.2 Production gate table and independent recomputation

| Gate | Value | Threshold | Verdict | Independent recomputation | Diff |
|---|---|---|---|---|---|
| track_record_length | 449.000000 | 126 | PASS | — | — |
| full_period_sharpe | 1.748401 | 0.9 | PASS | 1.748401 | 0.000e+00 |
| **rolling_63d_sharpe** | **-0.211884** | **0.9** | **FAIL** | -0.211884 | 0.000e+00 |
| max_drawdown | -0.049857 | -0.15 | PASS | -0.049857 | 0.000e+00 |
| rolling_63d_max_dd | -0.038564 | -0.15 | PASS | -0.038564 | 0.000e+00 |
| regime_flips | 6.000000 | 1 | PASS | — | — |
| **psr** | **0.684041** | **0.95** | **FAIL** | — | — |

`decision: NO-GO`, `failed_gates: ['rolling_63d_sharpe', 'psr']`, `psr_zone: grey_zone`.
The stored `low_rolling_sharpe` drift flag (-0.21188351222842883) equals the recomputed rolling 63d Sharpe to 1e-12.

### 4.3 NEW — rolling 63d Sharpe: the empirical base rate of the gate on this record

| Quantity | Value |
|---|---|
| Rolling windows on the record | 387 |
| Windows passing the 0.9 gate | **287 (74.16%)** |
| Windows failing | 100 (25.84%) |
| Rolling Sharpe min / median / max | -1.809887 / 1.953929 / 6.144063 |
| p5 / p10 / p25 / p50 / p75 / p90 / p95 | -0.667970 / -0.083317 / 0.748837 / 1.953929 / 3.716081 / 4.610642 / 5.114382 |
| **Current value -0.211884 → percentile rank** | **8.53%** of the 387 windows |
| Failing runs on the record (lengths) | 36, 25, 11, 8, 7, **5**, 3, 2, 1, 1, 1 (11 runs in total) |
| Current failing run | **5 windows** (2026-10-12 → 2026-10-16) |
| Longest failing runs | 36 windows (2025-04-03 → 2025-05-23), 25 windows (2026-07-15 → 2026-08-18), 11 (2026-08-20 → 2026-09-03) |
| Last passing window ended | 2026-10-09 (5 windows ago; the preceding run was 2 windows, 2026-10-07 → 2026-10-08) |
| Recovery lag (failing window → next pass) | median 9 windows, mean 11.93, p90 26.6, max 36 |

Reading: the gate is a *frequent* pass, not an exotic one — 3 windows in 4 would have cleared it on this record's own history, and the median failing window recovered within 9 windows. The current state is nevertheless in the **worst 9% of the record's own distribution**, and the current 5-window failing run is the 6th longest of 11 runs on the record. The record has been in longer failing states before — twice (36 windows in April–May 2025, 25 windows in July–August 2026) — and each time it recovered, in 36 windows in the worst case. This is a *state* the record has been in before and it resolved itself each time, but there is no guarantee, and the record's own history is a sample of 387 windows from one strategy.

### 4.4 NEW — max-drawdown evidence

| Quantity | Value |
|---|---|
| Full-period max DD (gate value) | **-4.98574%** vs -15% → headroom **10.0143 pp** |
| Rolling 63d max DD (gate value, current window) | **-3.85644%** vs -15% → headroom **11.1436 pp** |
| Worst rolling 63d max DD over all 387 windows | **-4.98574%** (identical to the record maximum) |
| Rolling windows breaching -15% | **0 of 387** |
| Worst single session on the record | -2.560456% (2026-01-30) |
| Best single session on the record | +2.065427% (2025-10-13) |
| Running-peak NAV / current NAV | 139,120.07 / 133,729.22 (current drawdown -3.874961%) |
| NAV that would breach the -15% gate | 118,252.06 = **-11.5735% from the current NAV** |
| Consecutive worst-recorded sessions to breach the gate | **5** |

Reading: **the drawdown gates are not close to binding.** The deepest drawdown the strategy has ever produced on this record is 4.99%, one third of the 15% allowance; no rolling window has ever breached it; and breaching it would require a 10.01 pp deeper peak-to-trough decline than anything in the record, or five consecutive sessions of the worst loss the record has ever produced. The drawdown evidence therefore says: *the failing gates are the Sharpe gates, and the risk gates have large, empirically-grounded headroom.*

### 4.5 NEW — the gap to each promotion threshold

**Rolling 63d Sharpe gate: -0.211884 vs 0.9 → gap 1.111884 Sharpe units.**

| Expression of the gap | Value |
|---|---|
| Window mean (2026-07-21 → 2026-10-16) | -0.006914%/session (-0.6914 bp/day) |
| Window dispersion (std, ddof=1) | 0.518011%/session (8.2232% annualised) |
| Mean required for Sharpe 0.9 at that dispersion | +0.029368%/session (+2.9368 bp/day) |
| Mean shortfall | **+3.6283 bp/day (+9.1432 pp annualised)** |
| Window cumulative net return: actual vs required | -0.435589% vs +1.850214% → gap **+2.2858 pp** |
| Can lower dispersion fix it? | **No** — the window mean is negative, so no dispersion reaches the threshold |

**Counterfactual bounds on the window's composition** (bounds on the *window*, not forecasts of future returns):

| Replacement | Window Sharpe | Sessions replaced |
|---|---|---|
| 2 worst window sessions ← 2 best sessions of the record | 1.619932 | 2 |
| 2 worst window sessions ← 2 record-average sessions (+0.066578%) | 1.027611 | 2 |

Two of the 63 sessions decide this gate. That is a statement about the *fragility* of a 63-session Sharpe on a 5.18 bp/day dispersion, and it is the same mechanism Cycle 862 identified (the five entering sessions carry the deterioration).

**Max-DD gates:** headroom 10.0143 pp (full period) and 11.1436 pp (rolling window); 0 breaches in 387 windows; 5 worst-case sessions to a breach.

**PSR gate (for the decision interaction):** psr 0.684041 vs 0.95, se 0.690150 → an observed Sharpe of **2.552996** would be required at the current SE (Cycle 862/865).

### 4.6 NEW — what clearing the rolling gate would actually buy (computed, not inferred)

The record truncated at the end of the last passing rolling window (444 sessions, through 2026-10-09) evaluated with the production code:

| Gate | Value | Threshold | Verdict |
|---|---|---|---|
| track_record_length | 444.000000 | 126 | PASS |
| full_period_sharpe | 1.934100 | 0.9 | PASS |
| rolling_63d_sharpe | 0.935578 | 0.9 | PASS |
| max_drawdown | -0.049857 | -0.15 | PASS |
| rolling_63d_max_dd | -0.019998 | -0.15 | PASS |
| regime_flips | 6.000000 | 1 | PASS |
| psr | 0.762425 | 0.95 | **FAIL** (grey zone) |

`decision: INCONCLUSIVE`, `failed_gates: ['psr']`.

**Therefore: clearing the rolling 63d Sharpe gate alone cannot produce "GO" on this record — it produces "INCONCLUSIVE" at best.** The binding constraint for promotion is the PSR gate, which needs an observed Sharpe of 2.552996 at the current SE, and Cycle 865 showed that needs 252–504 further sessions at the record mean. The rolling 63d gate is the *visible* failure; the PSR gate is the *decisive* one. Any plan that targets only the rolling window is optimising the symptom.

## 5. What this cycle establishes and what it does not

**Establishes (from the committed record, deterministically, read-only):**

1. The canonical full-period Sharpe 1.748401 is re-derivable from the committed state alone, and the four numeric gates recompute to 0.000e+00 against the production values.
2. The rolling 63d Sharpe gate has a **74.16% historical pass rate on this record**; the current value sits at the **8.53 percentile**; the current failing run is **5 windows**, the 6th longest of 11 on the record; the historical recovery lag has median 9 windows (max 36).
3. The drawdown gates have **large empirically-grounded headroom**: worst rolling 63d max DD on record -4.98574%, **0 breaches in 387 windows**, breach requires a 10.01 pp deeper decline or 5 consecutive worst-case sessions.
4. The gap to the rolling Sharpe gate is **1.111884 Sharpe units = +3.6283 bp/day of window mean = +2.2858 pp of window cumulative return**, and it is decided by **2 of 63 sessions**.
5. Clearing the rolling gate alone yields **INCONCLUSIVE, not GO**: the PSR gate remains decisive (needs observed Sharpe 2.552996 at SE 0.690150).

**Does not establish:**

1. That the strategy will recover. The base rate is a description of 387 past windows of one strategy, not a prediction; the recovery lag is a historical distribution, not a schedule.
2. That the counterfactual composition bounds are forecasts: replacing the 2 worst sessions with the 2 best days of the record is an upper bound on what re-composition alone could do, and it says nothing about future returns.
3. Any change to the verdict. The decision on the committed record is **NO-GO** (`rolling_63d_sharpe`, `psr` failing) and live deployment remains unsupported.

## 6. Falsification conditions

The conclusions above are falsified by any of the following:

| Conclusion | Falsified if |
|---|---|
| Base rate 74.16%, current value at the 8.53 percentile | Recomputing the rolling series from the committed state with the canonical convention gives a different pass count or percentile rank (i.e. the enumeration is not reproducible) |
| The drawdown gates are not binding | The worst rolling 63d max DD over the 387 windows is worse than -15%, or the gate value differs from the production value (recomputed diff ≠ 0.000e+00) |
| Clearing the rolling gate yields INCONCLUSIVE, not GO | The truncated 444-session record evaluated with the production code yields a different failed-gate set or decision |
| The gap is 1.111884 Sharpe units | The window mean/dispersion or the required mean at that dispersion recomputes differently, or the stored drift flag no longer equals the recomputed rolling Sharpe (1e-12) |
| The evidence is read-only | Any SHA-256 of the state file or the raw cache changes during the run, or `git status --porcelain data/` is non-empty |

## 7. Reproduction

```bash
python research/rolling_63d_gate_refresh.py       # OVERALL: PASS (11/11), exit 0
python research/sharpe_convention_audit.py         # gate table + PSR reproduced for 449 and 444 sessions
python research/go_no_go_evaluation.py             # side_effect_free True, evaluation_deterministic True, NO-GO
python -m pytest tests/test_rolling_63d_gate_refresh.py -q
python -m pytest -q                                # full suite
```

## 8. Label

**Exploratory evidence on a rejected candidate** — the record remains NO-GO (failed gates `rolling_63d_sharpe`, `psr`). The base rate, the drawdown headroom and the computed decision interaction are decision-relevant *negative* evidence: they show that the drawdown gates are not the problem, that the rolling gate is a frequent pass with a measurable recovery distribution, and that the PSR gate — not the trailing window — is what stands between this record and a promotion decision.
