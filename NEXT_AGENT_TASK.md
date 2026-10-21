# NEXT_AGENT_TASK.md

## Cycle 924 — Bootstrap confidence intervals for the within-bucket phase gaps; finalize the monitorable-regime statement

### Context
Cycle 923 is complete and verified: `research/tsmomentum_fold_regime_attribution.py` (read-only) attributes the incumbent `tsmomentum_spytrend_001`'s published 48-fold walk-forward to the four pre-specified observable-state buckets. Anchor reproduced (48 folds, mean OOS Sharpe 0.947307, median 1.293299, 91.7% positive, 6013 pooled trades; per-fold table reproduced). Phase decomposition confirmed: phase A mean 1.385035 vs phase B mean 0.509580 (gap +0.875454), matching Cycle 910.

Cycle 923's state-vs-calendar result is **tentative / mixed**:
- The phase gap collapses to ~0 in risk-on (gap +0.0067, n=37) and up-trend (gap -0.014, n=38) buckets — both phases perform alike (~1.4), no calendar weakness there.
- The phase gap persists (and widens) in risk_off (gap +3.45, n=11), down (gap +5.34, n=10) and med_vol (gap +2.64, n=18) buckets.
- But no dispersion share reaches conventional significance (F2 p=0.127, F3 p=0.141, F4 p=0.878), and the risk-off/down buckets are small (11 and 10 folds), so the weakness is not yet cleanly separable into a single monitorable regime.

The incumbent's `Credible Candidate` verdict is unchanged; nothing was wired into any gate. The open issue is purely statistical: **are the within-bucket phase gaps distinguishable from zero, or is the apparent state-dependence noise from small samples?**

### Objective
Add a read-only, deterministic block-bootstrap uncertainty quantification to the attribution: for each F2/F3/F4 bucket, compute a bootstrap confidence interval for the phase-A-minus-phase-B mean OOS Sharpe gap, state whether each gap's CI excludes zero, and finalize the monitoring statement on that basis. Descriptive only: no selection, re-ranking, re-fitting, gate changes, or verdict changes.

### Pre-specified method (fixed here; no fishing)
- Bootstrap unit: the 48 folds (resample folds with replacement), preserving each fold's test_sharpe, phase label, and bucket label.
- Statistic: phase_A mean test_sharpe minus phase_B mean test_sharpe within the bucket.
- Resamples: 5,000, fixed seed (published), two-sided 95% percentile CI (2.5th / 97.5th percentiles).
- Buckets: exactly the F2/F3/F4 buckets already published (risk_on, risk_off, up, down, low_vol, med_vol, high_vol) — no new buckets, no merged buckets.
- A bucket's gap is "distinguishable from zero" if its 95% CI excludes 0.

### Acceptance criteria
1. New read-only tool (e.g. `research/tsmomentum_fold_regime_bootstrap_ci.py`) reuses the committed candidate definition from `research/run_cycle6.py` and the attribution path machinery (cache-only prices from `data/raw/*.parquet`, fetcher never called), recomputes the 48 folds, and attaches bootstrap CIs to each F2/F3/F4 bucket.
2. Reproduction anchor, fail closed: reproduces the published aggregate (48 folds, mean 0.947307, median 1.293299, pooled 6013) and per-fold table; exits non-zero on mismatch and publishes nothing.
3. Publishes per bucket: n, point-estimate gap, bootstrap 95% CI [lo, hi], and "distinguishable from zero" yes/no; publishes the number of resamples and the seed.
4. Publishes a finalized monitoring statement: which observable state (if any) flags the incumbent's weakness, expressed as a candidate monitoring input only — not wired into any gate, drift flag, threshold or decision mapping, and not changing the published verdict.
5. All existing Cycle 923 behavior preserved: anchor, per-fold reproduction, four pre-specified families only, `--no-report` support, data/`config` byte-identical, committed artifacts byte-identical, bit-for-bit deterministic across two runs.
6. New regression test asserts: tool exits 0 with structural checks PASS; `data/` and `config/` byte-identical; committed artifacts byte-identical; `--no-report` writes no tracked artifact; anchor and per-fold reproduction hold; exactly the four bucket families; bootstrap CIs deterministic across two runs with the fixed seed; the monitoring statement is stated.
7. New experiment record states the bootstrap method, seed, resample count, per-bucket CIs, the finalized monitoring statement, the decision (no change to the incumbent's verdict), and reproduction commands.

### Scope boundaries
- Descriptive only; may not select, re-rank, re-fit, change any gate/threshold/universe/cost model/Sharpe convention/parameter, modify `data/`, call the fetcher, access secrets, or place trades.
- Bootstrap adds inference only; it must not be used to select a bucket or to change the verdict.
- The tool may write NEW files under `research/experiments/` / `research/reports/` / `tests/` only and must not rewrite any tracked committed artifact.
- Read-only guarantee enforced by SHA-256 fingerprinting `data/`, `config/` and committed artifacts before/after.

### Validation commands
```bash
python research/tsmomentum_fold_regime_bootstrap_ci.py
python -m pytest -q tests/test_tsmomentum_fold_regime_bootstrap_ci.py
git status --porcelain data/ config/
git diff --name-only HEAD -- research/run_cycle6.py research/experiments/tsmomentum_regime_filter_wf_001.md
```

### Evidence artifacts
- New read-only tool (bootstrap CI on within-bucket phase gaps).
- New report + new experiment record.
- New regression test.
- Reproduction commands and observed outputs of the validation commands above.

### Handoff (Cycle 923, this session)
- Changed: `research/tsmomentum_fold_regime_attribution.py`, `research/reports/tsmomentum_fold_regime_attribution_001.md`, `research/experiments/tsmomentum_fold_regime_attribution_001.md`, `tests/test_tsmomentum_fold_regime_attribution.py`.
- Verified: tool OVERALL: PASS; anchor MATCH; per-fold reproduction YES; 17/17 structural checks PASS; `data/`+`config/` byte-identical; committed artifacts unchanged; incumbent verdict unchanged; regression test 14 passed; full suite 465 passed, exit 0.
- Key result: phase gap collapses in risk_on/up (gap ≈ 0) but persists in risk_off/down/med_vol; dispersion shares not significant (p 0.127/0.141/0.878); conclusion tentative. Next step (Cycle 924) is bootstrap CIs to decide whether the state-dependence is distinguishable from noise.
- Incumbent's live stance remains INCONCLUSIVE at the code level (report-level `rolling_63d_sharpe` gate failing on the committed 450-session record); verdict unchanged.
