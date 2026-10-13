# Next Agent Task: Cycle 17 — Re-Execute C4 Correctly (execution-defect correction), Validate C6 Pre-Registration

## Context

Cycle 16 discovered a material execution defect in Cycle 15 (see
`research/reports/cross_momentum_consolidation.md`):
`research/run_cycle15.py` evaluated the **C3 18-ETF universe**
(`UNIVERSE` at run_cycle15.py:68-71), from **1993-01-01**
(`START_DATE` at line 74), hashing **`config/csmomentum_candidate_001.yaml`**
(`_config_hash` at lines 140-141) — not the pre-registered C4 design.
Consequently the C4 artifacts contain 18 weight columns over
1993-01-29→2026-10-09, the C4 fold table is byte-identical to C3's
(48 folds), and every C4 "result" (WF mean 0.6868, 79.2%, 313 trades,
"1/N 9-sector" benchmark 0.4617) is C3's result. The pre-registered C4
test (9 sector ETFs, 1998-12-22 start, 36 folds, 18-config grid) has
**never been executed**. The C4 hypothesis and config are sound and
frozen; only the execution was wrong.

Cycle 16 also completed the C6 (calendar/rebalancing effects)
pre-registration: `research/hypotheses/calendar_effects_001.md` and
`config/calendar_effects_001.yaml` (turn-of-month window exposure on
SPY/QQQ/IWM, 18-config grid, 33 verified folds from the 2000-05-26
common-calendar start).

## Objective

1. **PRIMARY — C4 re-execution correction**: re-run the pre-registered
   C4 evaluation with the correct constants, regenerate the C4 experiment
   record with correct provenance, and verify the corrected artifacts.
2. **SECONDARY — C6 pre-registration validation**: verify the frozen C6
   config and hypothesis are internally consistent (parses, grid
   arithmetic, fold count) so Cycle 18 can execute the C6 evaluation.

## Required Actions

### Part 1 (primary): C4 re-execution

1. Create `research/run_cycle15_c4_corrected.py` as a corrected copy of
   `research/run_cycle15.py` with these changes (nothing else changes):
   - `UNIVERSE` = the 9 GICS sector ETFs
     `["XLB","XLE","XLF","XLI","XLK","XLP","XLU","XLV","XLY"]`
   - `START_DATE = "1998-12-22"` (sector inception; repo-convention
     `END_DATE = "2026-10-09"` stays — the engine aligns to the
     universe calendar whose last trading day is 2026-10-08)
   - `_config_hash()` reads `config/sectorrotation_candidate_001.yaml`
   - Add a pre-execution assertion that
     `len(generate_walkforward_splits(START_DATE, END_DATE, 10, 12, 6, 21, 21)) == 36`
     and that fold 1 / fold 36 dates match the frozen hypothesis
     (fold 1: train 1998-12-22→2008-08-18, test 2008-09-17→2009-09-03;
     fold 36: train 2015-11-17→2025-07-14, test 2025-08-13→2026-07-30)
   - Keep the existing 18-config grid assertion
     (`len(LOOKBACKS) * len(SKIPS) * len(TOP_FRACTIONS) == 18`)
   - Keep all evaluation machinery, cost model, benchmark conventions
     (1/N monthly with 1-day lag; incumbent "slice" test-period /
     "full" fold warmup), multiple-testing (DSR N=18, PSR, PBO), and
     report generation identical to the pre-registered C4 plan.
   - Artifacts: overwrite `data/processed/{simulation,trades,weights}_sectorrotation_001.parquet`
     and regenerate `research/experiments/sectorrotation_baseline_wf_001.md`
     with correct provenance (the defective originals remain preserved in
     git history, commit 1d540f8).
2. Execute: `python3 research/run_cycle15_c4_corrected.py`
3. Verify (all must hold):
   - `weights_sectorrotation_001.parquet` has exactly **9 columns**
     (XLB..XLY) and **6,991 rows** (1998-12-22 → 2026-10-08)
   - The regenerated record's fold table has **36 rows** with train
     starts at 1998-12-22 and is **NOT identical** to C3's fold table
   - The record's data-integrity table lists exactly the 9 sector ETFs
     with 6,991 rows each, 100% Close completeness, and the config
     SHA-256[:12] equals `sha256sum config/sectorrotation_candidate_001.yaml`
   - Promotion-gate verdict is computed from the corrected results
     (report whatever it is — do not tune anything to change it)
4. Update the "Decision & Next Steps" section of the regenerated record
   with the honest label (Rejected/Failed, Exploratory signal, or
   Credible candidate) per the pre-registered gates.

### Part 2 (secondary): C6 pre-registration validation

Run and confirm (no backtest execution — that is Cycle 18):

```bash
python3 -c "import yaml; yaml.safe_load(open('config/calendar_effects_001.yaml'))"
python3 - <<'EOF'
import sys; sys.path.insert(0, '.')
from src.evaluation.walkforward import generate_walkforward_splits
pre_days, post_days = [1,2,3], [1,2,3,5,7,10]
assert len(pre_days) * len(post_days) == 18, "grid arithmetic"
splits = generate_walkforward_splits("2000-05-26", "2026-10-09", 10, 12, 6, 21, 21)
assert len(splits) == 33, f"expected 33 folds, got {len(splits)}"
assert splits[0]["train_start"] == "2000-05-26" and splits[0]["test_start"] == "2010-02-22"
assert splits[-1]["test_end"] == "2026-07-23"
print("C6 pre-registration checks: PASS (18 configs, 33 folds)")
EOF
```

## Acceptance Criteria

- `research/run_cycle15_c4_corrected.py` exists, runs to completion,
  and produces corrected C4 artifacts and record.
- Corrected C4 record: 36 folds, 9-ETF universe, correct config hash,
  honest promotion-gate verdict; fold table differs from C3's.
- C6 pre-registration validation commands pass (18 configs, 33 folds).
- No modification to frozen C3/C4 pre-registration artifacts
  (`research/hypotheses/sectorrotation_001.md`,
  `config/sectorrotation_candidate_001.yaml`) — only the experiment
  record and data artifacts are regenerated by the corrected execution.
- `research/reports/cross_momentum_consolidation.md` updated with the
  corrected C4 outcome (one short section; do not rewrite the defect
  documentation).
- `NEXT_AGENT_TASK.md` written for Cycle 18 (execute the C6 evaluation
  via `research/run_cycle18.py` per the frozen
  `config/calendar_effects_001.yaml`, mirroring the C3/C4 evaluation
  discipline: baseline backtest, 33-fold walk-forward, 18-config grid,
  1/N + incumbent benchmarks, DSR at N=18, plateau check on the
  `pre_days` axis at `post_days=3`).

## Scope Boundaries

- Do NOT modify `research/hypotheses/sectorrotation_001.md`,
  `config/sectorrotation_candidate_001.yaml`,
  `research/hypotheses/calendar_effects_001.md`, or
  `config/calendar_effects_001.yaml` (frozen pre-registrations).
- Do NOT modify `research/run_cycle13.py`, `research/run_cycle15.py`
  (frozen history of the defect), or any C3 artifacts
  (`*_csmomentum_001.parquet`,
  `research/experiments/csmomentum_baseline_wf_001.md`).
- Do NOT execute the C6 backtest in this cycle (that is Cycle 18).
- Do NOT add data fetching, new dependencies, overlays, or gate
  weakening. Research/backtesting only.

## Evidence References

- `research/reports/cross_momentum_consolidation.md` (Cycle 16 — defect
  documentation and corrected family verdict)
- `research/run_cycle15.py` (defective constants: lines 68-71, 74, 140-141)
- `research/hypotheses/sectorrotation_001.md` (frozen C4 design: 36-fold
  dates, 18-config grid, promotion gates)
- `config/sectorrotation_candidate_001.yaml` (frozen C4 config)
- `research/hypotheses/calendar_effects_001.md` +
  `config/calendar_effects_001.yaml` (frozen C6 pre-registration)
- `research/experiments/csmomentum_baseline_wf_001.md` (valid C3 rejection)
