# NEXT_AGENT_TASK.md

## Cycle 923 — Attribute the incumbent's published 48-fold walk-forward outcome to pre-specified observable regime state, and state whether the phase-A/phase-B weakness is a monitorable regime risk

### Context
Cycle 922 is complete and verified: the C3 candidate `csmomentum_001` is **rejected/failed** and its **last open pre-registered gate — the parameter-plateau gate (gate 4) — is now EVALUATED** on the config-faithful month-end path (3 of 3 lookbacks within the 0.1 tolerance -> PASS), while gate 1 (walk-forward mean OOS Sharpe 0.697524 < 0.9) still fails on every pre-registered sample, and **0 of the 18 pre-registered grid configurations clear gate 1** — the rejection is not an artefact of the pre-registered baseline. The C3 family is closed; the shortlist is unchanged.

That leaves the **incumbent** `tsmomentum_spytrend_001` as the only candidate whose published record is a *credible candidate* and the only one with a live stance (currently INCONCLUSIVE at the code level, with the report-level `rolling_63d_sharpe` gate failing on the committed 450-session record). Its published walk-forward PASS rests on a **+0.0473** margin over the 0.9 gate (48 folds, mean OOS Sharpe 0.947307, median 1.293299, 91.7% positive folds, 6013 pooled trades), and that margin is **not phase-stable**: the published 48 folds are two interleaved 24-fold sub-designs whose means differ by 0.88 Sharpe (phase A = folds 1,3,5,... mean **1.385035**; phase B = folds 2,4,6,... mean **0.509580**), and under phase B alone gate 1 would be a **FAIL** (0.5096 < 0.9). That is the published finding of Cycle 910/911 and it is still **unexplained**: it is not a fold-overlap artefact (removing the overlap *raises* the mean to 1.3850) and not a thin-trade artefact (only 2 of 48 folds have fewer than ten trades, and dropping them moves the mean up).

**The open question this cycle must answer:** the phase A/B split is a *calendar interleaving* (12-month test windows stepped by 6 months, so phase A's windows start in January and phase B's in July). Is the phase-B weakness therefore (a) an **observable state** effect — the phase-B windows happen to sit in a specific, identifiable market state that could be *monitored* on the live stance — or (b) a **calendar/protocol** effect that no observable state can flag? The distinction is decision-relevant: (a) yields a monitorable risk input for the only live candidate, (b) means the published margin is structurally fragile and the live stance should be treated accordingly. It has never been measured.

### Objective
Build a read-only, deterministic attribution of the incumbent's **48 published walk-forward folds** to **pre-specified observable state buckets**, using the published record (resolved by content) and the committed candidate definition, and publish: the per-bucket OOS Sharpe statistics; the phase-A/phase-B split *inside* each state bucket (the state-vs-calendar test); the dispersion each bucket family explains, with a permutation p-value; and an explicit statement of whether the phase-B weakness is an observable, monitorable regime risk or a protocol artefact. The published record, the published verdict and every gate stay unchanged; the attribution is descriptive and may not select, re-rank or re-fit anything.

### Pre-specified buckets (fixed here so that nothing can be fished)
The bucket families, their definitions and their counts are fixed by this task. No other bucket, split or grouping may be added, and every statistic must be published with its fold count `n`.
- **F1 calendar phase** (the published decomposition): phase A = published folds 1, 3, 5, ...; phase B = published folds 2, 4, 6, ...
- **F2 SPY trend state** at the fold's test-window start: risk-on if SPY Close >= its 200-day SMA, risk-off otherwise (both computed point-in-time from the cached prices; 2 buckets).
- **F3 SPY trailing 12-month return sign** at the fold's test-window start: up / down (2 buckets).
- **F4 trailing 63-day realized volatility** of the strategy's own net returns over the fold's **training** window, split into terciles whose boundaries are computed **from that training window only** (point-in-time; 3 buckets).

### Acceptance criteria
1. A new read-only tool (e.g. `research/tsmomentum_fold_regime_attribution.py`) reads prices **directly from `data/raw/*.parquet`** (never calls the fetcher, no network, no writes under `data/`), consumes the committed candidate definition and overlay **as-is** from `research/run_cycle6.py` (reuse `research/tsmomentum_walkforward_embargo_audit.py`: `resolve_published_record`, `load_close_from_cache`, `build_candidate_path`, `published_splits`), and evaluates the **48 published folds** with the published protocol (fixed parameters, no per-fold re-optimisation).
2. **Reproduction anchor, fail closed**: the tool reproduces the published aggregate (48 folds, mean OOS Sharpe **0.947307**, median **1.293299**, positive folds **91.7%**, pooled trades **6013**) and the published per-fold table before it publishes any attribution; if the anchor does not match, the tool exits non-zero and the attribution is not published.
3. The tool publishes, for each pre-specified family and bucket: `n` folds, mean/median OOS Sharpe, the phase-A/phase-B counts and means **inside** the bucket, and the family-level share of the between-fold dispersion with a **permutation p-value** (10,000 permutations, fixed seed, published).
4. The tool publishes the **state-vs-calendar test** explicitly: the phase-A minus phase-B mean OOS Sharpe difference computed *within* each state bucket of F2/F3/F4, with a statement of whether the phase gap is explained by the observable state (gap shrinks inside the buckets) or persists (calendar/protocol effect).
5. The tool publishes a **monitoring statement**: which observable state (if any) flags the incumbent's weakness, expressed as a *candidate* monitoring input only — it is **not** wired into any gate, drift flag, threshold or decision mapping, and it does not change the published verdict.
6. A new regression test (e.g. `tests/test_tsmomentum_fold_regime_attribution.py`) asserts: the tool exits 0 and prints its own structural checks as PASS; `data/` and `config/` are byte-identical before/after; the committed artifacts are byte-identical before/after; the tool supports `--no-report` and writes no tracked artifact under test; the anchor (48 folds / 0.947307 / 6013 pooled trades) and the per-fold reproduction hold; the four bucket families are exactly the pre-specified ones and no fifth family appears; the results are bit-for-bit deterministic across two runs; the published verdict is unchanged by the attribution.
7. A new experiment record states the data used, the pre-specified buckets, the per-bucket statistics, the permutation p-values, the state-vs-calendar conclusion, the monitoring statement, the decision (no change to the incumbent's verdict) and the reproduction commands.

### Scope boundaries
- **Descriptive only.** The attribution may not select a configuration, re-rank candidates, re-fit parameters, change the incumbent's published verdict, or alter any promotion/drift gate. The published 48-fold record and the incumbent's *Credible Candidate* label are unchanged by this cycle.
- The four bucket families above are **pre-specified**: do not add, drop, split or merge buckets, and do not try alternative windows or lookbacks. Publish every bucket with its `n`.
- Do not modify any gate, threshold, decision mapping, universe, cost model, Sharpe convention, parameter, hypothesis document or config file; do not modify `data/`; do not call `fetch_universe`; no new dependency, no network, no live trading, no secrets.
- The tool may write NEW files under `research/experiments/` / `research/reports/` / `tests/` only and must not rewrite any tracked committed artifact (support `--no-report`; the test asserts tracked artifacts are byte-identical).
- The permutation test is the multiple-testing control for the four families; the analysis is not a selection and must not be used as one.

### Validation commands
```bash
python research/tsmomentum_fold_regime_attribution.py
python -m pytest -q tests/test_tsmomentum_fold_regime_attribution.py
git status --porcelain data/ config/
git diff --name-only HEAD -- research/run_cycle6.py research/experiments/tsmomentum_regime_filter_wf_001.md
```

### Evidence artifacts
- New read-only tool `research/tsmomentum_fold_regime_attribution.py` (anchor reproduction + pre-specified attribution + permutation control + monitoring statement).
- New report `research/reports/tsmomentum_fold_regime_attribution_001.md` and new experiment record `research/experiments/tsmomentum_fold_regime_attribution_001.md`.
- New regression test `tests/test_tsmomentum_fold_regime_attribution.py`.
- Reproduction commands and observed outputs of the validation commands above.

### Handoff (for the cycle after)
- Changed: new read-only fold-attribution tool, its report, its experiment record and its regression test. (Cycle 922 changed: `research/csmomentum_plateau_gate_eval.py`, `research/reports/csmomentum_plateau_gate_eval_001.md`, `research/experiments/csmomentum_plateau_gate_eval_001.md`, `tests/test_csmomentum_plateau_gate_eval.py`; the C3 label stays *Rejected/Failed*.)
- Verified (Cycle 922): the tool reproduces the published config-faithful C3 record (union sample: 48 folds, mean OOS Sharpe 0.697524, median 0.617881, 79.17% positive, 400 pooled trades; common-inception slice: 21 folds, 0.586081, 166 pooled trades) and the published path (Sharpe 0.4247 backtest-scale / 0.6051 canonical, max DD -0.4474, turnover 2.16, 232 trade days, 7.56 mean positions); the plateau gate is EVALUATED (3 of 3, PASS); 0 of 18 grid configurations clear gate 1; the DSR is published on the current canonical convention (0.1248 at N=27, 0.3098 at N=18) together with the Cycle 13 record's own estimator (-0.3961 at N=27) and the scale disclosure; `data/` and `config/` are byte-identical before/after; the tool is deterministic across two runs.
- Unresolved: whether the incumbent's phase-B weakness is an observable, monitorable regime state or a calendar/protocol artefact (the object of this cycle); the incumbent's live stance remains INCONCLUSIVE at the code level with the report-level `rolling_63d_sharpe` gate failing on the committed 450-session record.
- Failed approaches (Cycle 922): the Cycle 922 hand-off's premise that "no backtest has been executed for C3 yet" was false — the baseline was executed in Cycle 13 and the config-faithful gate table in Cycle 907 — so the cycle did **not** re-execute it, and instead closed the last open pre-registered gate (plateau) on the config-faithful path. An intermediate draft of this cycle's report mis-described the shared selection module (`select_top_decile`) as a momentum-*value* threshold; it is rank-based (rank >= max_rank x (1 - top_fraction)) and the report was corrected before publication, with a regression test pinning the correct rule.
- Next task: Cycle 923 as specified above.
