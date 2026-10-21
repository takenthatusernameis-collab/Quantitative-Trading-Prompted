# Corrective Invocation Handoff — Cycle 930

**Date:** 2026-10-21 (corrective invocation 1 of the Cycle-930 session).
**Trigger:** the previous invocation exited 0 but left **no durable project
changes** (the supervisor recorded `project_changes=0` at head `4a379ab`).

## 1. What the previous invocation had and had not done

| Item | State at the start of this invocation |
|---|---|
| `research/data_cost_inventory_002.py`, `research/reports/data_cost_inventory_002.md`, `research/experiments/data_cost_inventory_002.md`, `research/hypotheses/riskparity_001.md`, `tests/test_data_cost_inventory_002.py` | **already committed** (`ca94bc6`, `4a379ab`) — the Cycle-929 deliverables were durable |
| `NEXT_AGENT_TASK.md` | **stale**: still described Cycle 929, which was already complete; no next cycle was prepared and no handoff record was written |
| Cycle-929 verification | `python -m pytest -q tests/test_data_cost_inventory_002.py` → **20 passed in 52.80s** (re-run here) |
| The worktree | clean (`git status --porcelain` empty) — hence "no durable project changes" |

So the durable gap was not the research itself but the **handoff**: the
Cycle-929 work was verified and committed, yet no cycle contract step 5
(`NEXT_AGENT_TASK.md` for the next cycle) and no durable handoff record
existed, and the shortlist row that Cycle 929 produced
(`research/hypotheses/riskparity_001.md`) had never been executed.

## 2. What changed in this invocation (all additive)

| File | Change |
|---|---|
| `research/riskparity_001_eval.py` | **new** — executes the pre-registered `riskparity_001` evaluation plan unchanged (9 configurations, DSR at N = 9, the repository's 3 bp/unit cost model, 1/N and SPY benchmarks, gate-flip cost curve) |
| `research/reports/riskparity_001_evaluation.md` | **new** — the published measurement |
| `research/experiments/riskparity_001_evaluation.md` | **new** — the experiment record (hypothesis reference, data, point-in-time treatment, configuration, splits, results, trial count, reproduction commands) |
| `tests/test_riskparity_001_evaluation.py` | **new** — 15 tests over the construction rules, the pre-registered constants, the end-to-end run and the published artefacts |
| `NEXT_AGENT_TASK.md` | **replaced** — Cycle 931 (the like-for-like mechanism comparison on the point-in-time-complete window) |

**Nothing committed was modified**: no record, config, gate, protocol or
shortlist row was touched; `data/` and `config/` are byte-identical (checked
by the tool itself on every run).

## 3. The result (honest negative)

The pre-registered baseline (L = 63, cap = 0.30) is **rejected**:

| Quantity | Value | Gate | Outcome |
|---|---|---|---|
| Walk-forward mean OOS Sharpe (backtest scale) | 0.778089 | >= 0.9 | **FAIL** |
| Positive-fold rate | 0.863636 | >= 0.5 | PASS |
| Pooled out-of-sample trades | 252 | > 100 | PASS |
| Excess over 1/N on the same 22 folds | +0.005005 | — | the mechanism adds ~nothing |
| Correlation with 1/N | 0.991382 | — | no diversification |
| Correlation with the incumbent's path | 0.658742 | — | — |
| Edge-erosion cost (WF mean <= 0) | 100.0 bp/unit | — | the edge is not cost-limited; it is small |

All nine pre-registered configurations fail gate 1 (0.777807 - 0.784390), so
the rejection is not a parameter accident. The canonical-scale mean is
0.914204, but the committed gate is stated on the repository's backtest
scale, which is the scale every published record uses. The label is
**"Rejected / failed the pre-registered promotion gates"**; the incumbent's
published verdict is untouched (Credible Candidate by its published verdict,
NO-GO for promotion).

## 4. A defect found in the pre-registration (measured, not silently fixed)

`research/hypotheses/riskparity_001.md` pre-registers the evaluation start as
"the first session on which all seven members carry a valid lagged volatility
estimate (GLD's first valid 63-session estimate ends 2005-11-10)". Measured
from the committed cache, the first session on which all seven carry a valid
lagged 63-session estimate is **2005-02-22**; 2005-11-10 is the incumbent's
*momentum* warm-up date for GLD (226-session lookback skipping 21), not a
63-session volatility date. The pre-registered date is therefore **later**
than the rule it states, so the window is point-in-time complete strictly
from its first session and the grid is measured on a homogeneous
cross-section. The pre-registration is used **unchanged**; the discrepancy is
measured and reported in the report and in the tool's structural check
(`evaluation_window_is_point_in_time_complete`). **No pre-registration was
edited.**

A second implementation detail was corrected before publication: the trailing
volatility window of the first rebalance inside the evaluation window reaches
back before it, so the weights are formed on the **full** price panel and
sliced to the window (forming them on the sliced panel would have left the
book uninvested for its first three months).

## 5. Verification (exact commands and observed output)

```bash
$ python3 -m pytest -q tests/test_data_cost_inventory_002.py
20 passed in 52.80s

$ python3 research/riskparity_001_eval.py --no-report
STRUCTURAL: PASS
CHECK|data_unchanged|PASS
CHECK|config_unchanged|PASS
CHECK|committed_artifacts_unchanged|PASS
CHECK|evaluation_window_is_point_in_time_complete|PASS
CHECK|baseline_weight_cap_respected|PASS
CHECK|trial_count_is_preregistered|PASS
GATE|wf_mean_oos_sharpe|0.778089|0.900000|>=|FAIL
GATE|positive_fold_rate|0.863636|0.500000|>=|PASS
GATE|pooled_oos_trades|252.000000|100.000000|>|PASS
WF_MEAN_OOS_SHARPE|0.778089|22
WF_MEAN_CANONICAL|0.914204
POSITIVE_FOLD_RATE|0.863636
POOLED_OOS_TRADES|252
TRIALS|9
GATE1_FLIP_BPS|none
EROSION_BPS_PER_UNIT|100.0
EXCESS_OVER_1N|0.005005
CORR_1N|0.991382
CORR_INCUMBENT|0.658742
DECISION|REJECT
LABEL|Rejected / failed the pre-registered promotion gates

$ python3 -m pytest -q tests/test_riskparity_001_evaluation.py
15 passed in 17.94s

$ git status --porcelain data/ config/
(empty)
```

The walk-forward numbers reproduce the previous session's throwaway prototype
(`/home/runner/work/_temp/kilo-tmp/kilo/proto_rp.py`, which was never
committed) exactly: WF mean 0.778089, canonical 0.914204, positive-fold rate
0.863636, 252 pooled trades.

## 6. Unresolved blockers

1. **The full test suite is not a usable gate.** `python -m pytest -q
   tests/test_tsmomentum_vol_estimate_consolidation.py
   tests/test_tsmomentum_same_session_vol_correction.py` had **not completed
   after 8.6 minutes** of wall clock in this session (process observed alive
   and running), and the Cycle-929 handoff recorded the same symptom for the
   full suite. The two files re-derive the 48-fold walk-forward repeatedly;
   the cost has not been profiled. **Next distinct investigation:** profile
   those two modules (per-test durations) and, if a single test dominates,
   cache the derived path at module scope; this is an infrastructure task, not
   a research one, and it must not change any published number.
2. **The 1/N reference number in the hypothesis is from a different window.**
   `riskparity_001.md` quotes the incumbent's published 1/N benchmark
   (0.4716, incumbent test window) as the comparison; the Cycle-930 run
   measured 1/N on the *point-in-time-complete* window instead
   (WF mean 0.773084 on the same 22 folds). Both numbers are correct on
   their own window; the comparison must always name its window. This is why
   Cycle 931 exists.

## 7. Next task

`NEXT_AGENT_TASK.md` (Cycle 931): measure the incumbent, `riskparity_001`
and 1/N on one point-in-time-complete window under one design and one cost
model, and report each mechanism's incremental value over 1/N with a
bootstrap CI on the excess. It is bounded, read-only, adds no candidate and
does not touch the published verdict.

## 8. Safety

Research and backtesting only. No live trading, no fetcher call, no
dependency, no scheduled job, no agent or workflow dispatch, no secrets
touched, no committed record/config/gate/protocol/shortlist modified, and the
pre-registration and promotion gates are preserved unchanged.
