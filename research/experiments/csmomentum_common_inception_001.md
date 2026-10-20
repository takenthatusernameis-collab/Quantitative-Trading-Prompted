# Experiment: Common-Inception Gate Table for `csmomentum_001` (csmomentum_common_inception_001, Cycle 907)

## Hypothesis reference

* Candidate hypothesis (pre-registered, frozen): `research/hypotheses/csmomentum_001.md`
* Frozen configuration: `config/csmomentum_candidate_001.yaml` (universe, signal, cost model,
  execution semantics, walk-forward protocol, promotion gates) — **read, never changed**.
* Sample-definition policy (pre-registered in Cycle 905): `config/sample_policy.yaml`,
  section `candidates.csmomentum_001` — **read, never changed**.
* Decision record behind the policy: `research/reports/sample_policy_001.md` (Cycle 904).
* Sample audit that pre-registered the control: `research/reports/csmomentum_common_inception_audit_001.md`
  (Cycle 905, extended in Cycle 906).
* Committed config-faithful record this cycle re-derives: `research/reports/month_end_candidate_reaudit_001.md`
  (Cycle 871) and `research/experiments/csmomentum_001_experiment_001.md` (Cycle 13).

## Objective

Measure the candidate's **config-faithful** walk-forward evaluation on the three samples that the
sample policy pre-registers for it (`union_sample`, `common_inception_slice`,
`common_inception_window`), publish the three gate tables side by side, and state whether the
candidate's published **Rejected/Failed** verdict is an artefact of the sample definition.

This is a **measurement** cycle: no gate, threshold, decision mapping, universe, cost model,
parameter, candidate configuration or committed artifact is changed; nothing under `data/` or
`config/` is written; the 27-configuration robustness grid is **not** executed (the plateau gate
is reported as NOT EVALUATED).

## Data used

| Item | Value |
|---|---|
| Source | committed raw cache `data/raw/*.parquet` (Yahoo Finance via yfinance, cached by `src/data/yfinance_fetcher.py`). The tool reads the parquet files directly and **never calls the fetcher**, so nothing is downloaded and nothing is written. |
| Universe | SPY, QQQ, IWM, TLT, GLD, DBC, VNQ, EFA, EEM, XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY (18 assets) |
| Range | the union calendar 1993-01-29 .. 2026-10-19; the evaluation window is truncated at the frozen `evaluation.splits.test_end` = **2026-10-09** (8,482 sessions). The six cached sessions 2026-10-12 .. 2026-10-19 are outside the pre-registered window and are excluded. |
| Frequency | daily (UTC), trading sessions only |
| Common inception | **2006-02-06** — re-derived at run time from the raw cache (max of the per-symbol first dates; DBC's first date). No date in the policy is trusted. |
| Per-symbol cache fingerprint | published in the report (rows, first/last date, SHA-256), derived at run time |
| Point-in-time treatment | the momentum is formed on the **last session of the calendar month** and the positions become effective on the **next** session (`signal_lag_days: 1`), so every trade is decided on information available before it is placed. No forward-fill of prices across the sample boundary: the aligned frame forward-fills each symbol's own last observed close onto the union calendar, exactly as `YFinanceFetcher._align` does. |

## Configuration (parameters, hyperparameters)

All of it is read from the frozen `config/csmomentum_candidate_001.yaml`; nothing was re-tuned.

| Item | Value |
|---|---|
| Signal | cross-sectional momentum, lookback 252, skip 21, top fraction 0.5 |
| Rebalance schedule | **config-faithful month-end** (`src/backtest/rebalance.py:build_month_end_weights`) — *not* the legacy calendar rule (`weights.index.is_month_end`, published mean OOS Sharpe 0.6868) and *not* the daily re-rank path (0.6928) |
| Cost model | 1.0 bp commission + 2.0 bp slippage per unit of weight change (3 bp/unit round trip) |
| Risk overlay | none (the candidate's pre-registered baseline) |
| Walk-forward protocol | 10y train / 12m test / 6m step, 21d purge, 21d embargo, **fixed parameters** (no per-fold re-optimisation); the fold windows are slices of one continuously computed point-in-time path per sample |
| Promotion gates | WF mean OOS Sharpe >= 0.9; positive fold rate >= 0.5; pooled OOS trades > 100; plateau >= 0.667 (2 of 3 lookbacks) — **NOT EVALUATED** this cycle |
| Decision mapping | the published one (`research/month_end_candidate_reaudit.py:gates_for`): falsified when gate 1 **or** gate 2 fails → **Rejected/Failed** |
| Gate scale | **backtest scale** (`backtest_sharpe_ratio`), the scale on which the candidate's gate was originally evaluated. The canonical scale (`arithmetic_annualized_rf0`) is published beside it and is never used for a gate. |
| Trial count | **1** measurement per sample (3 samples + 1 matched-fold-window sensitivity). No configuration was tried, tuned or re-ranked; the 27-configuration grid is out of scope. |

## Splits

* The evaluation window ends at the frozen `evaluation.splits.test_end` (**2026-10-09**).
* Each sample's fold calendar is generated over that sample's own declared window: the union
  sample over the configuration's `history_start` (1993-01-01), the two common-inception
  samples over the re-derived common inception (2006-02-06). A fold can only be trained on data
  the sample actually contains, so the common-inception samples' first out-of-sample fold starts
  after a full 10-year training window **inside** the sample (2015-11-03).
* **What the repository's generator applies** (`src/evaluation/walkforward.py:generate_walkforward_splits`):
  the 21-day **purge** is applied as a gap between the end of the training window and the start
  of the test window; the 21-day **embargo** parameter is accepted but **not** applied to the
  fold construction, because the folds roll — the next fold's training window starts 6 months
  after the previous fold's and therefore contains the tail of the previous fold's test window
  (fold 1: train 1993-01-01..2002-08-29, test 2002-09-30..2003-09-16; fold 2: train
  1993-06-28..2003-02-21, test 2003-03-25..2004-03-10). This is the repository's own
  convention — it is the generator that produced the candidate's own published 48-fold record and
  the Cycle 871 config-faithful record — so all three samples are measured identically and the
  comparison is unaffected. It does mean the folds are **not independent** (section 4 below).
  Because the parameters are fixed, no information from a test window enters the trading path:
  the overlap is a statistical-independence limitation, not a look-ahead.

## Results

### 1. The reproduction anchor (the union sample)

The tool's OVERALL depends on reproducing the committed config-faithful record of
`research/reports/month_end_candidate_reaudit_001.md` (section 2.3) at the tolerance of the last
published decimal:

| Metric | Published | Observed | Abs. diff | Result |
|---|---|---|---|---|
| folds | 48 | 48 | 0 | MATCH |
| mean OOS Sharpe (backtest scale) | 0.6975 | 0.6975243375140185 | 2.434e-05 | MATCH |
| mean OOS Sharpe (canonical) | 0.8404 | 0.8403888341999609 | 1.117e-05 | MATCH |
| median OOS Sharpe | 0.6179 | 0.6178806353181572 | 1.936e-05 | MATCH |
| positive fold rate | 0.7917 | 0.7916666666666666 | 3.333e-05 | MATCH |
| pooled OOS trades | 400 | 400 | 0 | MATCH |

The two values the union-sample path must **not** produce are not produced: the legacy calendar
path (0.6868, abs. diff 1.072e-02) and the daily re-rank path (0.6928, abs. diff 4.724e-03).

### 2. The three gate tables

| Sample | Sessions | Window | Folds | WF mean OOS Sharpe | Median | Positive folds | Pooled OOS trades | Gate 1 | Gate 2 | Gate 3 | Gate 4 | Decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `union_sample` | 8,482 | 1993-01-29..2026-10-09 | 48 | 0.6975 | 0.6179 | 79.17% | 400 | FAIL | PASS | PASS | NOT EVALUATED | **Rejected/Failed** |
| `common_inception_slice` | 5,202 | 2006-02-06..2026-10-09 | 21 | 0.5861 | 0.6311 | 76.19% | 166 | FAIL | PASS | PASS | NOT EVALUATED | **Rejected/Failed** |
| `common_inception_window` | 5,202 | 2006-02-06..2026-10-09 | 21 | 0.5861 | 0.6311 | 76.19% | 166 | FAIL | PASS | PASS | NOT EVALUATED | **Rejected/Failed** |

Exact values: union mean 0.6975243375140185 (canonical 0.8403888341999609), median
0.6178806353181572, std 0.7783585033932666, positive 0.7916666666666666, pooled 400; the two
common-inception samples: mean 0.586080732009725 (canonical 0.757728611295589), median
0.631133614003499, std 0.554361059192409, positive 0.7619047619047619, pooled 166.

Full-sample path metrics (the same config-faithful path, over each sample's whole window):

| Sample | Sharpe (backtest) | Sharpe (canonical) | Ann. return | Ann. volatility | Max drawdown | Ann. turnover | Trade days | Mean positions |
|---|---|---|---|---|---|---|---|---|
| `union_sample` | 0.424692 | 0.605113 | 0.090468 | 0.165928 | -0.447353 | 2.155x | 232 | 7.56 |
| `common_inception_slice` | 0.366686 | 0.552958 | 0.079297 | 0.161710 | -0.427678 | 2.277x | 164 | 9.44 |
| `common_inception_window` | 0.397537 | 0.580443 | 0.085618 | 0.165062 | -0.427678 | 2.453x | 176 | 9.94 |

### 3. The degenerate-fold diagnostic

| Sample | Folds | Train-end breadth < 5 | Train window contains breadth < 5 | Test window contains breadth < 5 | Test window entirely breadth < 5 | Min valid momentum @ test start |
|---|---|---|---|---|---|---|
| `union_sample` | 48 | 0 | 15 | 0 | 0 | 12 |
| `common_inception_slice` | 21 | 0 | 3 | 0 | 0 | 18 |
| `common_inception_window` | 21 | 0 | 0 | 0 | 0 | 18 |

* The union sample's 1,763 sessions with fewer than 5 selectable assets run from 1993-01-29 to
  **2000-01-21** — all of them **before** the earliest fold's test window (2002-09-30), by which
  time 12 assets already have a valid momentum.
* The pre-registered diagnostic (breadth at the fold's **training-window end**) is **not**
  degenerate for any fold of any sample: a ten-year training window is longer than the ragged
  era, and the union sample's earliest fold ends its training window on 2002-08-29 with 12
  assets carrying a valid momentum.
* The 15 union folds whose *training window contains* a degenerate stretch are folds 1..15
  (the pre-2000 era); the 3 affected common-inception-slice folds contain only the warm-up ramp,
  and the warm-up-preserving window has none.

### 4. The matched-fold-window sensitivity

All three paths evaluated on the same 20 test windows (the union sample's folds whose test
window lies inside the common-inception window, 2016-04-07 .. 2026-05-28):

| Path | Folds | Mean OOS Sharpe | Median | Positive | Pooled trades |
|---|---|---|---|---|---|
| `union_sample` | 20 | 0.7108237234527068 | 0.5872045912790951 | 80.00% | 160 |
| `common_inception_slice` | 20 | 0.7108237234527068 | 0.5872045912790951 | 80.00% | 160 |
| `common_inception_window` | 20 | 0.7108237234527068 | 0.5872045912790951 | 80.00% | 160 |

The three paths are identical on these windows: from the first month-end signal both frames can
form, the truncated and the union frame produce the same path, so the only difference between the
samples is the pre-common-inception history, which these test windows do not touch. The residual
difference between the samples' own-calendar means (0.6975 vs 0.5861, i.e. 0.1114 Sharpe) is
therefore a **fold-calendar** effect of about one standard error of the fold mean (fold Sharpe
std 0.7784 over 48 folds → SE ≈ 0.112; ≈ 0.174 on the 20 matched folds) and is **not
resolvable** at this number of folds. The two fold calendars are offset by 14 sessions (the
common-inception samples' first test window starts 2015-11-03, the union sample's nearest fold
2015-10-14).

### 5. The independence of the folds

| Sample | Folds | Mean consecutive test-window overlap (days) | Maximum number of disjoint test windows |
|---|---|---|---|
| `union_sample` | 48 | 175 | 24 |
| `common_inception_slice` | 21 | 175 | 11 |
| `common_inception_window` | 21 | 175 | 11 |

The 6-month step over a 12-month test window makes consecutive test windows overlap, and the
repository's generator does not apply the embargo, so the honest count of independent test
windows is 24 (union sample) and 11 (common-inception samples) — not 48 and 21. This is a
property of the published protocol (the candidate's own 48-fold record has the same overlap) and
it applies to every sample equally, so it does not bias the comparison; it is, however, the
reason the difference between the samples' mean OOS Sharpe is not resolvable, and it is a fact
the promotion gate's "> 100 pooled OOS trades" screen does not see.

### 6. Conclusion

* **The published verdict is not an artefact of the sample definition.** On the pre-registered
  common-inception samples the walk-forward mean OOS Sharpe is 0.5861, *below* the union
  sample's 0.6975, and gate 1 (>= 0.9) fails on every sample — by 0.2025 on the union sample and
  by 0.3139 on the pre-registered samples. The candidate stays **Rejected/Failed**.
* The trade-count screen still passes on the pre-registered sample (166 pooled OOS trades > 100),
  so the rejection is a return-quality rejection, not a statistical-power one.
* The "earliest folds are trained on a single asset" reading of the ragged union calendar is
  correct about the *training* window only: no fold of any sample is traded on a cross-section
  narrower than 5 assets, and no fold is trained on one at its training-window end.
* The candidate is **not** promoted, re-fit, re-ranked or re-optimised; the plateau gate stays
  NOT EVALUATED; the four committed records are byte-identical before and after the run.

## Known confounders and limitations

1. **The fold calendar is anchored at the sample's declared start**, so the three samples have
   different fold sets (48 / 21 / 21 folds) and the common-inception calendars are offset by 14
   sessions from the union calendar. The matched-fold-window block removes that offset and shows
   the three paths coincide on the common windows; the residual difference in the own-calendar
   means is about one standard error of the fold mean and is not resolvable at 20-48 folds.
2. **The comparison is a paired one on the same path family**, not an independent replication:
   the three samples share the same 18 assets, the same prices and the same configuration. The
   measurement answers "does the sample definition change the verdict?", not "does the strategy
   have an edge?".
3. **The plateau gate is NOT EVALUATED** (the 27-configuration grid is out of scope), so the
   gate table is incomplete by construction — exactly as the published record already is.
4. **The common-inception samples' first out-of-sample fold starts in 2015-11**, so the
   pre-registered samples' evidence covers roughly the last 11 years, not the last 20. This is a
   consequence of the 10-year training window inside a 20-year sample, not of a choice made for
   the result.
5. **The market-data window is the cached one**; the six sessions appended after 2026-10-09 are
   outside the pre-registered window and are excluded (as the published window is 8,482 and not
   8,488 sessions).
6. The trade-day count of a fold is computed on the fold's **sliced** weight frame (the first
   session of a fold has no measurable weight change inside the fold), the repository's own
   published convention; the net returns of the path itself are computed on the full frame.
7. **The folds are not independent observations** (section 5): 48 folds carry at most 24
   disjoint test windows and 21 folds at most 11, and the repository's embargo parameter is not
   applied. Any inference that treats the fold count as the number of independent observations
   (including the promotion gate's pooled-trade screen) overstates the evidence. This is
   pre-existing and identical for every published walk-forward record; it is published here, not
   fixed, because fixing it would change the published protocol.

## Falsification condition

This cycle's conclusions are wrong if any of the following holds (each is an executable check in
`research/csmomentum_sample_gate_audit.py`, 16/16 pass):

1. the union sample does not reproduce the committed config-faithful record of
   `research/reports/month_end_candidate_reaudit_001.md` at the published decimals;
2. the union-sample path produces the legacy calendar value (0.6868) or the daily re-rank value
   (0.6928);
3. the common inception is not re-derived from the raw cache as the max of the per-symbol first
   dates;
4. the config-faithful path is not equal to `src/backtest/rebalance.py:build_month_end_weights`,
   or a segment is not the selection of its own signal date, or it is effective on or before its
   signal date;
5. the evaluation window does not end at the frozen `evaluation.splits.test_end`, or the six
   cached sessions after it are added;
6. the gate table is not evaluated on the backtest scale, or the plateau gate is reported as
   anything other than NOT EVALUATED, or a sample publishes no decision;
7. a file under `data/` or `config/`, or one of the four committed records, is modified by the
   run.

## Reproduction commands

```bash
python research/csmomentum_sample_gate_audit.py      # OVERALL: PASS, 16/16 checks
python research/csmomentum_common_inception_audit.py  # the Cycle 905/906 sample audit still passes
python research/month_end_candidate_reaudit.py        # the committed config-faithful record is unchanged
python -m pytest -q tests/test_csmomentum_sample_gate_audit.py
python -m pytest -q
git status --porcelain data/ config/                 # empty
```

## Artifacts

| Artifact | Path |
|---|---|
| Tool (new) | `research/csmomentum_sample_gate_audit.py` |
| Report (new) | `research/reports/csmomentum_common_inception_gate_001.md` |
| Tests (new) | `tests/test_csmomentum_sample_gate_audit.py` |
| Sample policy (read-only) | `config/sample_policy.yaml` |
| Frozen candidate configuration (read-only) | `config/csmomentum_candidate_001.yaml` |
| Committed records used as reference (read-only) | `research/experiments/csmomentum_001_experiment_001.md`, `research/experiments/csmomentum_baseline_wf_001.md`, `research/reports/month_end_candidate_reaudit_001.md`, `research/reports/promotion_feasibility_backtest_001.md` |
| Predecessor cycle | `research/reports/csmomentum_common_inception_audit_001.md` (Cycle 905/906, the sample audit that pre-registered the control) and `research/reports/sample_policy_001.md` (Cycle 904, the decision record behind the policy) |

---

*Record generated from `research/csmomentum_sample_gate_audit.py` (Cycle 907). Deterministic: no
random number generator, no timestamps.*
