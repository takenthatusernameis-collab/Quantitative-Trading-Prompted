# Consolidation: Cross-Sectional Momentum Family (C3 / C4)

**Cycle:** 16 (2026-10-13); updated Cycle 17 (2026-10-13)
**Code revision:** 1d540f8 (Cycle 16); bd18164 (Cycle 17 update)
**Purpose:** Consolidate the cross-sectional momentum family
(Candidate C3, broad 18-ETF universe; Candidate C4, 9 GICS sector
ETFs) after Cycles 13 and 15, per the Cycle 15 decision tree.
This report supersedes the family-level conclusion stated in the
Cycle 15 handoff, which treated both candidates as validly rejected.

---

## 1. Candidate C3 (csmomentum_001) — VALIDLY EVALUATED → Rejected/Failed

- **Record:** `research/experiments/csmomentum_baseline_wf_001.md`
  (Cycle 13, `research/run_cycle13.py`); hypothesis
  `research/hypotheses/csmomentum_001.md`; frozen config
  `config/csmomentum_candidate_001.yaml`.
- **Universe:** 18 ETFs (SPY, QQQ, IWM, TLT, GLD, DBC, VNQ, EFA,
  EEM, XLB–XLY); aligned history 1993-01-29 → 2026-10-09 (8,482
  days); point-in-time breadth growth 8 → 17 → 18 assets.
- **Baseline** (lookback=252, skip=21, top_fraction=0.5, monthly,
  3 bps round-trip, 1-day lag): test-period (2018-2026) net Sharpe
  **0.4101**, max DD -35.71%, 62 trades, 2.06x annualized turnover.
- **Walk-forward** (48 folds, 10y/12m/6m, 21d purge/embargo, fixed
  params): mean OOS Sharpe **0.6868**, 79.2% positive folds, 313
  pooled OOS trades.
- **Robustness** (18-config grid): baseline ranks **17/18**; plateau
  2/3 lookbacks within 10% (pass); DSR **-0.6484** at the
  pre-registered N=27 and **-0.4634** at the evaluated N=18
  (probabilities 0.2584 / 0.3215) — does not survive
  multiple-testing deflation.
- **Benchmarks:** dominated by both — 1/N equal-weight test Sharpe
  0.4617; incumbent TSMOM (tsmomentum_spytrend_001) test Sharpe
  1.4178, WF mean 0.9473 (both reproduced exactly, verifying the
  benchmark implementation).
- **Verdict:** pre-registered falsification condition met (WF mean
  OOS Sharpe 0.6868 < 0.9) → **Rejected/Failed**. This evaluation
  is internally consistent: the artifacts
  (`simulation_csmomentum_001.parquet` etc.), the fold table, and
  the aggregate statistics all correspond to the 18-ETF universe and
  the pre-registered design.

## 2. Candidate C4 (sectorrotation_001) — INVALID EXECUTION → re-execution required

The Cycle 15 record (`research/experiments/sectorrotation_baseline_wf_001.md`)
does **not** document a valid evaluation of the pre-registered C4
design. The execution script (`research/run_cycle15.py`) contains the
C3 configuration, not the C4 configuration:

| Item | C4 pre-registration (frozen, Cycle 14) | Cycle 15 execution (actual) |
|------|----------------------------------------|------------------------------|
| Universe | 9 sector ETFs (XLB–XLY) | **18 ETFs** (`run_cycle15.py:68-71`, `UNIVERSE` = C3 list) |
| History start | 1998-12-22 (sector inception) | **1993-01-01** (`run_cycle15.py:74`, `START_DATE`) |
| Config hash | `config/sectorrotation_candidate_001.yaml` | **`config/csmomentum_candidate_001.yaml`** (`run_cycle15.py:140-141`) |
| Folds | 36 (from 1998-12-22) | **48** (from 1993-01-01) |

Physical evidence that the C4 run evaluated the C3 universe:

1. **Artifacts contain 18 assets.** `data/processed/weights_sectorrotation_001.parquet`
   is 8,482 × **18** (columns SPY…XLY), index 1993-01-29 →
   2026-10-09. `simulation_sectorrotation_001.parquet` carries 18
   `weight_*` columns. `trades_sectorrotation_001.parquet` (581
   rows) trades all 18 symbols. A valid C4 run would produce 9
   weight columns over 1998-12-22 → 2026-10-08 (6,991 days).
2. **The C4 fold table is byte-identical to C3's** — all 48 rows,
   same train starts (1993-01-01), same Sharpe values to 4 decimal
   places. Two different universes cannot produce identical fold
   statistics; the C4 "results" are C3's results.
3. **Aggregate statistics are identical to C3's** (mean OOS Sharpe
   0.6868, 79.2% positive, 313 pooled trades, mean trades 6.5).
4. **The C4 record's "1/N Equal-Weight (9 sector ETFs)" benchmark
   (test Sharpe 0.4617) equals C3's 18-ETF 1/N benchmark** (README
   Cycle 13 record), not a 9-sector 1/N portfolio.
5. The record's own data section is internally inconsistent: the
   narrative says "9 GICS sector ETFs" but the integrity table lists
   all 18 ETFs with 8,482 rows each, and the aggregate table says
   48 folds while the benchmark table says 36.

The C4 pre-registration itself is sound and consistent:
`generate_walkforward_splits("1998-12-22", "2026-10-09", 10y/12m/6m,
21d/21d)` yields exactly **36 folds**, and the first/last fold dates
match the hypothesis (`sectorrotation_001.md`: fold 1 train
1998-12-22→2008-08-18, test 2008-09-17→2009-09-03; fold 36 train
2015-11-17→2025-07-14, test 2025-08-13→2026-07-30). Only the
execution was wrong.

**Label for C4: Blocked by execution defect — NOT Rejected/Failed.**
The pre-registered C4 test (9 sector ETFs, 36 folds, 18-config grid)
has never been run. The Cycle 15 claim that C4 "failed the 0.9 gate"
is unsupported; the numbers cited for C4 are C3's numbers.

## 3. Family verdict (corrected)

- **Broad-universe cross-sectional momentum (C3): rejected** on valid
  evidence. The 18-ETF rank signal does not produce a net-of-cost,
  walk-forward-valid edge at the pre-registered configuration, and
  the result survives multiple-testing disclosure (negative DSR).
- **Sector-restricted cross-sectional momentum (C4): tested in
  Cycle 17 (corrected re-execution) — Rejected/Failed.** See
  section 6 below.
- The family is therefore **not** "rejected twice"; it is rejected
  once (C3) with a second, lower-prior test (C4) subsequently
  executed in Cycle 17 (section 6), completing the family
  verdict.

## 4. Root cause and correction

**Root cause:** `research/run_cycle15.py` was derived from
`research/run_cycle13.py` with the report narrative edited for C4,
but the execution constants (`UNIVERSE`, `START_DATE`,
`_config_hash` target) were not updated. The script therefore
reproduced C3's evaluation exactly and archived it under C4's
artifact names.

**Correction (assigned as the primary Cycle 17 task — see
`NEXT_AGENT_TASK.md`):** create a corrected execution script with the
C4 constants, re-run the pre-registered C4 evaluation (9 sector ETFs,
1998-12-22 start, 36 folds, 18-config grid), regenerate the C4
experiment record with correct provenance, and verify the artifacts
contain exactly 9 weight columns over the 1998-12-22 → 2026-10-08
calendar with a 36-row fold table that is NOT identical to C3's.
The defective Cycle 15 artifacts remain preserved in git history
(commit 1d540f8) as the record of the defect.

## 5. Decision-tree consequence

The Cycle 15 handoff's premise ("both C3 and C4 failed → advance to
C6") is only half supported. The corrected decision tree:

1. **First**, re-execute C4 correctly (Cycle 17 primary task). If it
   fails the pre-registered gate → the cross-sectional momentum
   family is rejected on two valid tests and is archived; if it
   passes → a credible candidate exists and the promotion-gate
   process applies.
2. **In parallel (already done in Cycle 16)**, pre-register the next
   distinct mechanism, C6 calendar/rebalancing effects
   (`research/hypotheses/calendar_effects_001.md`,
   `config/calendar_effects_001.yaml`), so the mechanism pipeline
   continues regardless of the C4 outcome.
3. **Then** (Cycle 18), execute the C6 evaluation
   (`research/run_cycle18.py`).

## 6. Cycle 17 corrected C4 re-execution — outcome (2026-10-13)

The pre-registered C4 test was executed correctly for the first
time via `research/run_cycle15_c4_corrected.py` (9 sector ETFs,
1998-12-22 start, 36 folds, 18-config grid; config SHA-256[:12]
`4f186de79db3`; record `research/experiments/sectorrotation_baseline_wf_001.md`,
regenerated). Artifacts verified: 9 weight columns (XLB–XLY),
6,991 rows (1998-12-22 → 2026-10-08), 36-fold table with train
starts 1998-12-22 (fold 1 test 2008-09-17→2009-09-03; fold 36
test 2025-08-13→2026-07-30) — NOT identical to C3's 48-fold
table.

**Corrected C4 results** (net of 3 bps, monthly rebalance, 1-day
lag, fixed pre-registered parameters):

- Baseline (252, 21, 0.5) test-period (2018-2026) net Sharpe
  **0.4679**, max DD -35.25%, 39 trades, 2.24x turnover.
- Walk-forward (36 folds): mean OOS Sharpe **0.6944**, 83.3%
  positive folds, **158** pooled OOS trades.
- Robustness grid (18 configs): baseline rank **5/18**; plateau
  3/3 lookbacks within 10% (pass).
- Benchmarks: 1/N equal-weight (9 sectors) test Sharpe 0.4430
  (baseline excess IR +0.0665, corr 0.954); incumbent TSMOM
  1.4122 on the common index (its standalone evaluation
  reproduces the Cycle 6/7 value 1.4178 exactly — the small
  difference is the common-index alignment to the 2026-10-08
  sector calendar), WF mean 1.2799.
- Multiple testing: DSR **-0.2742** (p=0.3920) at the true
  N=18; PSR vs the 0.9 gate 0.1008; PBO degenerate (all 18
  configs have positive OOS Sharpe); IS-OOS rank correlation
  -0.323.

**Verdict: Rejected/Failed.** The pre-registered falsification
condition is met (WF mean OOS Sharpe 0.6944 < 0.9). The sector
restriction did not rescue the cross-sectional rank signal: the
WF mean is marginally above C3's 0.6868 but still far below the
0.9 gate, the 1/N benchmark beats the baseline in the
walk-forward (0.7817 vs 0.6944), and DSR does not survive
deflation. The cross-sectional momentum family is now **rejected
on two valid, pre-registered tests** (C3 broad universe, C4
sector universe) and is archived. The next mechanism on the
Cycle 11 shortlist is **C6 calendar/rebalancing effects**
(pre-registered; Cycle 18 executes the evaluation).

---

## Evidence References

- `research/experiments/csmomentum_baseline_wf_001.md` (Cycle 13 — valid C3 rejection)
- `research/experiments/sectorrotation_baseline_wf_001.md` (Cycle 15 — defective C4 record)
- `research/run_cycle15.py` (defective constants: lines 68-71, 74, 140-141)
- `research/run_cycle15_c4_corrected.py` (Cycle 17 corrected C4 execution)
- Corrected C4 record: `research/experiments/sectorrotation_baseline_wf_001.md` (regenerated; the defective Cycle 15 original is preserved in git history, commit 1d540f8)
- `research/hypotheses/sectorrotation_001.md`, `config/sectorrotation_candidate_001.yaml` (frozen C4 pre-registration — sound, unchanged)
- `research/reports/opportunity_shortlist.md` (C3 29/35, C4 28/35, C6 26/35)
- Git history: commit 1d540f8 (defective C4 artifacts)

---

*Report generated: 2026-10-13 (Cycle 16); updated 2026-10-13 (Cycle 17 corrected C4 re-execution)*
*Code revision: bd18164*
