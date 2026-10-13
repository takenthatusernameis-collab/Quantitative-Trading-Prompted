# Consolidation: Cross-Sectional Momentum Family (C3 / C4)

**Cycle:** 16 (2026-10-13)
**Code revision:** 1d540f8
**Purpose:** Preserve the Cycle 16 root-cause analysis for C3/C4 and record the corrected family conclusion after the valid Cycle 17 C4 re-execution. Sections 2–5 describe the Cycle 16 state before the corrected C4 run; the current disposition is in Section 6.

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

## 2. Candidate C4 (sectorrotation_001) — Cycle 16 historical diagnosis (superseded by Section 6)

*Historical status at the end of Cycle 16: the old Cycle 15 execution was invalid. The corrected Cycle 17 execution and its final rejection are recorded in Section 6 below.*


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

## 3. Family verdict (Cycle 16 snapshot; superseded by Section 6)

*This was the conclusion before the corrected C4 backtest. See Section 6 for the current result.*


- **Broad-universe cross-sectional momentum (C3): rejected** on valid
  evidence. The 18-ETF rank signal does not produce a net-of-cost,
  walk-forward-valid edge at the pre-registered configuration, and
  the result survives multiple-testing disclosure (negative DSR).
- **Sector-restricted cross-sectional momentum (C4): untested.** C3's
  rejection is strong prior evidence against the family — the 9
  sectors are a subset of the failed 18-asset rank, and restricting
  the universe reduces cross-sectional breadth — but the
  pre-registered sector test must be executed before the family can
  be declared fully rejected. The prior for C4 is explicitly lower
  than C3's was (per the frozen hypothesis).
- The family is therefore **not** "rejected twice"; it is rejected
  once (C3) with a second, lower-prior test (C4) outstanding.

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

## 5. Decision-tree consequence (Cycle 16 snapshot; superseded by Section 6)

*This decision tree was written before C4 was validly executed. The next step is now Cycle 18 C6 evaluation, as recorded in Section 6.*


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

---

## Evidence References

- `research/experiments/csmomentum_baseline_wf_001.md` (Cycle 13 — valid C3 rejection)
- `research/experiments/sectorrotation_baseline_wf_001.md` (Cycle 15 — defective C4 record)
- `research/run_cycle15.py` (defective constants: lines 68-71, 74, 140-141)
- `research/hypotheses/sectorrotation_001.md`, `config/sectorrotation_candidate_001.yaml` (frozen C4 pre-registration — sound, unchanged)
- `research/reports/opportunity_shortlist.md` (C3 29/35, C4 28/35, C6 26/35)
- Git history: commit 1d540f8 (defective C4 artifacts)

---

*Report generated: 2026-10-13 (Cycle 16)*
*Code revision: 1d540f8*


## 6. Cycle 17 result — corrected C4 evaluation completed

The corrected cache-only C4 run completed successfully on 2026-10-13. The exact corrected runner commit was `fa9cd1593a190fcfa2523dd02bd3697fa2ccd1af`; see [GitHub Actions run #38418474184](https://github.com/takenthatusernameis-collab/Quantitative-Trading-Prompted/actions/runs/38418474184).

- **Universe and dates:** the nine frozen GICS sector ETFs, 6,991 common daily observations from 1998-12-22 through 2026-10-08.
- **Cache-only preflight:** all 16 required tracked parquet inputs (the nine candidate ETFs plus CORE7 incumbent inputs) were present and readable; no market-data downloads were made.
- **Structural validation:** exactly 18 frozen grid configurations and 36 walk-forward folds; all required train/OOS metrics were finite; generated weights, simulation, trade log and report provenance passed the runner's persisted-output contract.
- **Baseline test-period Sharpe:** 0.4679; grid rank 5/18.
- **Mean OOS walk-forward Sharpe:** **0.6944**, below the frozen 0.90 threshold (**FAIL**).
- **Positive-fold rate:** 83.3% (PASS); pooled OOS trades: 158 (PASS); parameter plateau: 3/3 lookbacks (PASS).
- **Deflated Sharpe Ratio:** -0.2742; reported probability 0.3920.
- **Benchmark context:** test-period Sharpe 0.4430 for 1/N sector equal weight and 1.4122 for incumbent TSMOM; mean OOS walk-forward Sharpe 0.7817 and 1.2799 respectively.

**Current C4 verdict: Rejected/Failed.** The pre-registered falsification rule is conjunctive at the candidate level: the mean OOS Sharpe gate alone is enough to reject because it is below 0.9. No tuning or threshold changes were made after seeing the results. The full corrected report, 36-fold table and three generated parquet outputs are preserved in the [validated artifact bundle](https://github.com/takenthatusernameis-collab/Quantitative-Trading-Prompted/actions/runs/38418474184/artifacts/11825760496); [cache manifest and diagnostics](https://github.com/takenthatusernameis-collab/Quantitative-Trading-Prompted/actions/runs/38418474184/artifacts/11825481124).

### Current family and pipeline decision

- **C3:** Rejected/Failed on its valid 18-ETF, 48-fold evidence.
- **C4:** Rejected/Failed on the corrected 9-ETF, 36-fold evidence. The former report is preserved as `research/experiments/sectorrotation_baseline_wf_001_pre-correction.md`; the canonical C4 report has been corrected.
- **Cross-sectional momentum family:** two valid pre-registered variants have now failed their promotion gate. Archive these outcomes; do not reopen C3/C4 to tune against the holdout.
- **Next independent candidate:** proceed to **Cycle 18, C6 calendar/rebalancing effects**, using the already frozen `research/hypotheses/calendar_effects_001.md` and `config/calendar_effects_001.yaml`. The exact next-agent handoff is in `NEXT_AGENT_TASK.md`. C6 is a distinct, calendar-based mechanism, not a repair or extension of C4.
- **Scope:** frozen C3/C4/C6 hypotheses and configs remain unchanged. The corrected backtest workflow did not invoke Kilo or commit binary research outputs; the result bundle remains linked in GitHub Actions.
