# Sample-definition hygiene of the long-sample promotion artifact (Cycle 902)

## Context

Cycle 902 was a **verification-hygiene** cycle. No candidate, universe, cost
model, gate, threshold, configuration, state, metric or deployment decision
was changed; nothing was written under `data/` or `config/`.

Its handoff (`NEXT_AGENT_TASK.md` at `7fd1363`) named two open defects in
`research/promotion_feasibility_backtest.py`:

1. **The published sample definition did not describe the sample.** The
   artifact published `sample.start_date: 2004-11-18` (the *common* inception,
   the max of the per-symbol first dates) together with
   `session_count: 8488` — the length of the **union calendar** from
   1993-01-29 — and printed
   `SAMPLE: 2004-11-18..2026-10-19 (8488 sessions)`: a label and a count that
   describe two different samples.
2. **Two frozen Sharpe literals** in `research/psr_continuation_horizon.py`
   and `research/rolling_63d_rolloff_projection.py`.

### Defect 2 was already closed before this cycle started

`git log -S"1.748401" -- research/psr_continuation_horizon.py
research/rolling_63d_rolloff_projection.py` shows the two literals were
replaced by live interpolation in commit **`a50c89c`** (the Cycle 902 handoff
commit itself):

```diff
-    lines.append("SE decline alone cannot reach PSR>=0.95 at current observed Sharpe 1.748401 < target-scale 1.4178? ...")
+    lines.append(f"SE decline alone cannot reach PSR>=0.95 at current observed Sharpe {sharpe0:.6f} < target-scale 1.4178? ...")
-    print("  Current observed Sharpe (full period): 1.748401; gap is numerator-driven")
+    print(f"  Current observed Sharpe (full period): {sharpe_ratio(rets):.6f}; gap is numerator-driven")
```

Both scripts print the live value **1.771084** today (the canonical Sharpe of
the 450-session paper record) and neither contains the literal any more. The
`449`-session anchor `1.748401` survives only where it belongs: as a
*reference sample* anchor (`research/rolling_63d_gate_refresh.py`,
`tests/test_rolling_63d_gate_refresh.py`) and in dated reports that quote the
449-session record. `research/rolling_63d_rolloff_projection.py` writes no
report file, so the "regenerated report" part of the handoff has no second
file; `research/reports/psr_continuation_horizon_001.md` was regenerated.

**Consequence for this cycle:** the remaining work was defect 1 (plus the
acceptance criteria that came with it), not a second literal.

## 1. What changed

### 1.1 `research/promotion_feasibility_backtest.py`

| Change | Why |
|---|---|
| The `sample` block now publishes the **label** (`label_start_date`, `label_end_date` — the common inception) **and** the **realized** window (`realized_start_date`, `realized_end_date`, `realized_session_count`); the historical `start_date` / `end_date` / `session_count` keys now carry the realized window, so no key describes a sample that was not computed. | Defect 1: a label and a count that described two different samples. |
| The console line became `SAMPLE: realized 1993-01-29..2026-10-19 (8488 sessions), label 2004-11-18..2026-10-19, universe=[...]`. | The printed line was the most-read form of the same defect. |
| The realized window is **derived independently** from the `data/raw/*.parquet` union index (`scan_raw_cache()` reads every parquet once and builds the sorted union of the per-symbol indices), and the tool now checks that the backtest's own return index **equals** that union index (`realized window equals raw-cache union index: True`). | The criterion requires an independent derivation, not the engine's loader. |
| `per_symbol_stats` (first date, last date, row count per symbol) and `cache_fingerprint` (rows, first/last date and the **SHA-256 of the file** per symbol) are published. | The ragged edge of the union calendar has to be visible in the artifact, and a later append has to show up as a *fingerprint change* rather than as an unexplained number change. |
| The cache fingerprint is **derived at run time** from the files on disk. The first draft of this cycle hard-coded `SPY 8488 rows / 2026-10-19 / sha256 971d02284b9790df…` as a constant — that would have gone stale on the next append, i.e. exactly the failure mode the fingerprint exists to prevent. It was replaced by the computed value. | A frozen fingerprint is a stale literal. |
| The **reference-sample anchors** are published *and re-derived on every run*: the incumbent path truncated at 2026-10-16 (8,487 sessions) must reproduce Sharpe 0.5646255767978904 / max DD -0.6224126346564325 / PSR 2.2219753177036448e-08, and the first 449 sessions of the paper record must reproduce the canonical Sharpe 1.748401. Both are checked (`reference check [...]: PASS`) and the tool's `OVERALL` is now `PASS` only if **both** the reference checks and the realized-window check hold. | The handoff asked for the live-sample expectations to be expressed as reference-sample anchors plus a cache fingerprint; an anchor that is not re-derived is a frozen constant. |
| `research/reports/promotion_feasibility_backtest_001.md` gained the "Reference-sample integrity" section and two new falsification conditions. | The artifact has to carry its own evidence. |

**Nothing else moved:** the gate table, the thresholds, the decision mapping,
the universe, the cost model, the Sharpe convention, the candidate
configuration and every published metric are untouched. The canonical numbers
on the full sample are bit-identical to Cycle 901's:
`sharpe_canon=0.565718`, `sharpe_backtest=0.384348`, `rolling63=-0.034252`,
`psr=0.000000` (1.6549061233035153e-08), `failed=['full_period_sharpe',
'rolling_63d_sharpe', 'max_drawdown', 'psr']`, `decision=NO-GO`.

### 1.2 `research/psr_continuation_horizon.py` (narrative only, no number)

The generated report contained a self-contradictory sentence — "at current
observed Sharpe 1.771084 **<** target-scale 1.4178**?**" with a stray "?" —
and a dead `z_floor` variable whose value was never used while the printed
expression used a different epsilon (`1e-12` vs `1e-9`). The sentence now
interpolates `SR_TARGET` and states the comparison correctly; the dead
variable is gone and the printed expression is the one that is used. The
printed value is unchanged: `Max PSR at SE floor (sharpe=1.771084, SE->0):
1.000000` before and after. **No metric, gate or threshold was touched.**

### 1.3 `research/long_sample_overlay_attribution.py` (wording only)

Its report stated that "the committed artifact's `sample.start_date` is the
**common** (max of per-symbol) inception" — true before this cycle, false
after it. The wording now describes the two published windows; no number in
the report changed (only that paragraph is in the diff).

### 1.4 `tests/test_promotion_feasibility_sample_window.py` (new, 6 tests)

The handoff required "a test [that] asserts that the published realized window
equals the independently computed union index of the raw cache (no new stale
literal; the test must survive the next data append)". The module:

* recomputes the union calendar from `data/raw/*.parquet` itself and compares
  it with the published `realized_*` fields and with the historical
  `start_date` / `end_date` / `session_count` keys;
* checks that the published label is the common inception (max of the
  per-symbol first dates) and is published *next to* the realized window;
* checks that the published cache fingerprint equals the SHA-256, row count
  and dates of the files on disk (so a fingerprint that is frozen rather than
  derived fails the test);
* checks that the published reference-sample checks are present and pass;
* runs the tool as a subprocess, asserts that it publishes the realized window
  and that it reproduces the committed report **byte-identically**.

No window date, session count or hash is pinned in the test: both sides of
every comparison are recomputed, so the invariants survive the next append
(the committed report then has to be regenerated and committed with the data,
which is the repository's existing data-change alarm).

## 2. Reconciliation: why 1.771084 and 0.5657 are both "current"

The two Sharpe numbers come from **two different samples of the same frozen
candidate** (`tsmomentum_spytrend_001`, `config/simulation_candidate_001.yaml`),
evaluated by two different tools. They are not in conflict.

| Tool | Sample it evaluates | Sessions | Canonical full-period Sharpe | Rolling 63d | PSR | Failed gates | Decision |
|---|---|---|---|---|---|---|---|
| `research/go_no_go_evaluation.py`, `research/rolling_63d_gate_refresh.py`, `research/psr_continuation_horizon.py`, `research/rolling_63d_rolloff_projection.py` | the **prospective paper-trading record** (`data/processed/paper_trading_state.yaml`) | 450 (2025-01-02..2026-10-19) | **1.771084** | -0.448918 | 0.695606 | `['rolling_63d_sharpe', 'psr']` | **NO-GO** |
| `research/promotion_feasibility_backtest.py`, `research/rebalance_schedule_audit.py` | the **long-sample backtest** of the same configuration on the raw cache | 8,488 (1993-01-29..2026-10-19) | **0.565718** | -0.034252 | 1.6549061233035153e-08 | `['full_period_sharpe', 'rolling_63d_sharpe', 'max_drawdown', 'psr']` | **NO-GO** |

The four-gate versus two-gate difference is the **sample**, not a
disagreement: the long sample additionally fails `full_period_sharpe`
(0.5657 < 0.9) and `max_drawdown` (-62.24% vs the -15% limit), because it
contains the 2000-2002 and 2008 drawdowns that the two-year paper record
does not.

**The cross-section of the long sample is ragged** — this is the fact the
cycle's publication makes visible for the first time.
`src/backtest/engine.py:run_backtest` does not slice the price frame
(`src/data/yfinance_fetcher.py` returns the whole parquet; the engine only
does `close.ffill().dropna(how="all")`), and
`src/features/momentum.py:select_top_decile` selects the single best asset
when fewer than five assets have a momentum value and otherwise ranks the
*available* assets. The realized sample therefore carries

| from | cross-section |
|---|---|
| 1993-01-29 | SPY (1 asset) |
| 1999-03-10 | + QQQ (2) |
| 2000-05-26 | + IWM (3) |
| 2001-08-27 | + EFA (4) |
| 2002-07-30 | + TLT (5) |
| 2003-04-14 | + EEM (6) |
| 2004-11-18 | + GLD (7) |

so the published long-sample metrics are the numbers of a **1-to-7-asset**
strategy, while the frozen configuration describes a 7-asset universe whose
first fully populated date is 2004-11-18 (the label that was published until
this cycle). The incumbent's long-sample evidence has never been measured on
a window in which all seven assets exist. That is the open question the next
cycle takes up.

## 3. Verification (exact commands and observed results)

```
$ python research/promotion_feasibility_backtest.py
OVERALL: PASS
SAMPLE: realized 1993-01-29..2026-10-19 (8488 sessions), label 2004-11-18..2026-10-19, universe=['SPY', 'QQQ', 'IWM', 'TLT', 'GLD', 'EFA', 'EEM']
sharpe_canon=0.565718 sharpe_backtest=0.384348 delta=-1.033452
rolling63=-0.034252 psr=0.000000 failed=['full_period_sharpe', 'rolling_63d_sharpe', 'max_drawdown', 'psr'] decision=NO-GO
attainable_psr095=False req_sr_obs=1.671511 se=0.154245
realized window equals raw-cache union index: True (1993-01-29..2026-10-19, 8488 sessions)
reference check [incumbent_reference_sample]: PASS
reference check [paper_record_reference_sample]: PASS

$ python research/rolling_63d_gate_refresh.py      -> checks passed: 12/12, OVERALL: PASS (decision NO-GO)
$ python research/rebalance_schedule_audit.py      -> OVERALL: PASS
   incumbent default path on the 8487-session reference sample (through 2026-10-16): sharpe=0.5646255767978904 max_dd=-0.6224126346564325 psr=2.2219753177036448e-08
   incumbent default path on the full sample (8488 sessions, through 2026-10-19): sharpe=0.5657179297830458 max_dd=-0.6224126346564325 psr=1.6549061233035153e-08 decision=NO-GO failed=['full_period_sharpe', 'rolling_63d_sharpe', 'max_drawdown', 'psr']
$ python research/long_sample_overlay_attribution.py -> OVERALL: PASS
$ python research/psr_continuation_horizon.py        -> Baseline n=450 ... sharpe=1.771084, psr=0.695606, se=0.690271; "Max PSR at SE floor (sharpe=1.771084, SE->0): 1.000000"
$ python research/rolling_63d_rolloff_projection.py  -> "Current observed Sharpe (full period): 1.771084; gap is numerator-driven"
$ python research/go_no_go_evaluation.py             -> failed_gates: ['rolling_63d_sharpe', 'psr']; decision (evaluate_go_no_go): NO-GO; side_effect_free: True
$ python -m pytest tests/test_promotion_feasibility_sample_window.py -q -> 6 passed in 7.68s
$ python -m pytest -q                                -> 240 passed, 3 warnings in 326.39s (0:05:26)   (234 pre-existing + 6 new)
$ git status --porcelain data/ config/               -> empty
```

## 4. Decision and handoff

* **Unchanged:** the incumbent's decision is **NO-GO** (long sample: failed
  gates `['full_period_sharpe', 'rolling_63d_sharpe', 'max_drawdown',
  'psr']`; paper record: failed gates `['rolling_63d_sharpe', 'psr']`).
  Live deployment remains unsupported. No gate, threshold, decision mapping,
  universe, cost model, candidate configuration or Sharpe convention was
  changed, and no file under `data/` or `config/` was written.
* **No candidate work was started.** This cycle changed no candidate and
  opened no new candidate family. For the avoidance of doubt: the
  shortlist's rank-2 candidate (`csmomentum_001`, long-only cross-sectional
  momentum over the 18-ETF cache) is **not** new work — it was pre-registered
  in `research/hypotheses/csmomentum_001.md` (v001, Cycle 12) and evaluated
  on the config-faithful month-end path in Cycle 871
  (`research/month_end_candidate_reaudit.py`), where it failed its
  pre-registered gate (walk-forward mean OOS Sharpe 0.847243 < 0.9); the
  cost screen then measured it as needing to be *paid* 30.0967 bp/unit to
  reach the gate. The file read in this cycle was that pre-existing
  hypothesis, not a new pre-registration.
* **Consumer audit of the changed key semantics.** The promotion artifact's
  `sample` block is written by `research/promotion_feasibility_backtest.py`
  and read by exactly two Python modules: `tests/test_rebalance_schedule.py`
  (which asserts byte-identity and the `paper_sharpe` / `paper_max_dd` /
  `psr_normal` strings — none of them in the `sample` block) and the new
  `tests/test_promotion_feasibility_sample_window.py`. No reader anywhere
  still treats `start_date` as the common inception; the one prose reference
  to the old semantics (`research/long_sample_overlay_attribution.py`) was
  corrected in this cycle.
* **Handoff:** `NEXT_AGENT_TASK.md` is replaced with **Cycle 903** — measure
  the incumbent's promotion-gate table on the **common-inception sample**
  (2004-11-18..2026-10-19, seven assets throughout) next to the union-sample
  numbers, read-only, with the engine's window semantics untouched, so that
  the NO-GO verdict is known to be (or not to be) an artefact of the sample
  definition.
