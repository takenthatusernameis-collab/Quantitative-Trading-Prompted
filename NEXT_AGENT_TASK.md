# Cycle 941 — Re-verify the four closed shortlist candidates and decompose their failure (gross edge vs cost drag)

## Context

Cycle 934 shortlisted four structurally distinct candidates on committed data. All four
are now evaluated and **rejected**:

| Candidate | Cycle | Verdict | Fired conditions | Published WF mean OOS Sharpe | Published excess 95% CI | Pooled OOS trades |
|---|---|---|---|---|---|---|
| `reversal_001` | 935/936 | Rejected/Failed | i, iii, iv, vi | -0.004016 | [-1.186788, -0.740217] | 3485 |
| `pairs_001` | 936 | Rejected/Failed | i, iii, iv | -0.829067 | [-1.219160, -0.467513] | 1380 |
| `liquidity_001` | 938 | Rejected/Failed | i, iv | -0.649990 | [-2.113215, -0.859968] | 832 |
| `leadlag_001` | 939 | Rejected/Failed | i, ii | 0.073691 | [-13.5760%, 21.6097%]/yr | 132 |

The incumbent `tsmomentum_spytrend_001` stays **Credible Candidate / NO-GO**. The Cycle-934
shortlist is therefore **exhausted**: four mechanisms are ruled out and no new candidate has
been selected yet.

Cycle 940 audited the published statistics of the closed shortlist and found **three
reporting defects** in two of the four records, all now corrected with errata of record
(`research/experiments/liquidity_001_evaluation_erratum_001.md`,
`research/experiments/pairs_001_evaluation_erratum_001.md`):

1. `liquidity_001`'s published Deflated Sharpe Ratio was produced by an **unseeded**
   bootstrap, so it changed on every run (-2.919035 as published; -2.963458 / -2.954174 /
   -2.886135 on three consecutive audit runs). It is now seeded with the frozen
   configuration's declared seed (20240101) and draw count (2000) and is reproducible
   (-2.968111, probability 0.001498).
2. `liquidity_001` published its **Realized cost drag** as the fraction of return under a
   percent label (0.007159%/yr) while its own turnover figure (23.862681 units/yr at
   3.0 bp per unit) implies **0.715880%/yr**.
3. `pairs_001` published a **Realized turnover cost drag of 0.0006%/yr** because the
   evaluator applied the 3.0 bp cost rate to a series that already carried it; the
   measured drag is **2.1364%/yr** (total drag 22.4636%/yr, not 20.3277%/yr). Its
   "Gross excess (before borrow) annualized" (6.6497%) was in fact **net of the turnover
   cost**; the true gross before any cost (8.7862%/yr) was computed but never published.
   Its correction notice also pointed at an erratum file that **did not exist** in the
   repository; that file now exists.

No verdict changed: in all three cases the affected figures are reported statistics, not
pre-registered falsification conditions, and the strategy return series, fold Sharpes,
bootstrap CIs and Deflated Sharpe Ratios are unchanged.

Two gaps remain open and are the subject of this cycle:

- **No re-verification harness exists for the closed shortlist.** A published number in
  any of the four records could drift from its generator without anything detecting it
  (the DSR defect was detected only by accident, when a concurrent run rewrote the
  committed file).
- **The Deflated Sharpe Ratio is computed on different samples by different evaluators.**
  `liquidity_001` computes it on the **full-sample** strategy-excess series
  (1998-12-22 .. 2026-10-08, i.e. including the in-sample train period); `reversal_001`,
  `pairs_001` and `leadlag_001` compute it on the **pooled out-of-sample** net returns.
  A full-sample DSR is optimistic. The Cycle-940 erratum flagged this as open; it is
  still open.

## Objective

Build **one** read-only, deterministic re-verification harness that re-runs each of the
four *closed* candidates' **frozen** specifications from the committed parquet cache and
publishes, per candidate: (a) the cross-check of the published headline numbers against the
recomputed ones, (b) the **gross** (zero-cost) benchmark-relative excess, the **measured**
turnover and cost drag under the committed 3.0 bp/unit model, and the **net** excess, and
(c) the classification of the failure mode: **"no gross edge"** (gross excess <= 0) versus
**"gross edge below the measured cost hurdle"** (gross excess > 0 but net excess <= 0).
Publish the consolidated record that states, per mechanism, what its rejection rules out
for future cycles. Follow AGENTS.md: hypothesis-first, no re-tuning, no variant creation,
no new candidate, honest accounting, and no number that is not either recomputed from the
committed cache or transcribed from a frozen configuration.

## Acceptance criteria

- New read-only deterministic tool `research/shortlist_gross_edge_001.py` that:
  - consumes the four **frozen** configurations (`config/reversal_candidate_001.yaml`,
    `config/pairs_candidate_001.yaml`, `config/liquidity_candidate_001.yaml`,
    `config/leadlag_candidate_001.yaml`) and the construction functions of the four
    committed evaluators (`research/reversal_001_evaluation.py`,
    `research/pairs_001_evaluation.py`, `research/liquidity_001_evaluation.py`,
    `research/leadlag_001_evaluation.py`) **as they are** — no edit to any of them;
  - reads only the committed parquet cache under `data/raw/`, never calls the fetcher,
    writes nothing under `data/` or `config/`, and asserts that the SHA-256 of every file
    under `data/` and `config/` is unchanged before and after the run;
  - prints `OVERALL: PASS` and exits 0; two consecutive runs are byte-identical.
- Re-verification table, one row per candidate and one row per published statistic: the
  published value (transcribed from `research/experiments/<candidate>_evaluation.md`) and
  the recomputed value; every difference is either < 1e-6 or is listed explicitly with its
  cause (for example a unit convention, or the `leadlag_001` roll-window rule).
- Gross/net decomposition per candidate, in **one** unit convention stated in the record:
  gross benchmark-relative excess (cost = 0), measured turnover (units/yr), measured cost
  drag (%/yr at the committed 3.0 bp per unit of weight change), net excess, and the ratio
  `cost drag / gross excess`; the benchmark-relative measure is the candidate's own
  published benchmark (1/N of the same universe for `liquidity_001`, cash for
  `leadlag_001`, and whatever each frozen configuration declares for the other two).
  Note explicitly where two turnover measures of the same strategy disagree (the
  `pairs_001` record publishes 68.6916 units/yr from the netted book, while its
  pair-level cost series implies about 71.2 units/yr) and which one the decomposition
  uses.
- DSR sample-alignment column per candidate: the sample the published Deflated Sharpe
  Ratio is computed on (full-sample excess vs pooled out-of-sample net returns), stated as
  a measurement; **no published DSR value is changed**.
- Failure-mode classification per candidate: `no_gross_edge` or
  `gross_edge_below_cost_hurdle`, with the numbers it follows from, and an explicit
  statement that **no variant of the four is opened** and that no new candidate is
  proposed in this cycle.
- New records `research/experiments/shortlist_gross_edge_001.md` and
  `research/reports/shortlist_gross_edge_001.md`, with the hypothesis reference, the data
  used (source, range, frequency, universe, point-in-time treatment), the frozen configs
  used, the two tables above, the classification, the consolidated statement of what the
  four rejections rule out, the reproduction commands, and the trial count (4 candidates
  x 2 cost states = 8 evaluations, declared before the run).
- New tests `tests/test_shortlist_gross_edge_001.py` covering: the published-versus-
  recomputed cross-check for all four candidates; the gross/net decomposition identity
  (`gross excess - cost drag = net excess`); determinism (two runs byte-identical);
  `git status --porcelain data/ config/` unchanged; and that the tool writes nothing
  outside `research/`.
- Validation commands all pass:
  - `python research/shortlist_gross_edge_001.py` -> `OVERALL: PASS`, exit 0
  - `python -m pytest -q tests/test_shortlist_gross_edge_001.py` -> all passed
  - `python -m pytest -q tests/test_liquidity_001_evaluation.py` -> 18 passed (no regression)
  - `python -m pytest -q tests/test_pairs_001_evaluation.py tests/test_pairs_001_failure_analysis.py` -> 19 passed (no regression)
  - `python research/bootstrap_seed_audit.py` -> `OVERALL: PASS`, exit 0 (no new unseeded
    bootstrap call introduced)
  - `git status --porcelain data/` -> empty
  - `git diff --name-only HEAD -- config/settings.yaml` -> empty

## Scope boundaries

- **Read-only** on `data/` and `config/`. Only add files under `research/` and `tests/`.
- Do **not** modify the four candidate evaluators, their records, their frozen
  configurations, the Cycle-940 errata, `config/settings.yaml`, or the committed cost
  model (3.0 bp per unit of weight change). The decomposition *measures* the drag; it does
  not assume a different cost model.
- No re-tuning, no parameter search, no grid, no variant creation after seeing results,
  no reopening of `reversal_001`, `pairs_001`, `liquidity_001` or `leadlag_001`, and **no
  new candidate** in this cycle.
- Do not dispatch workflows or start agent sessions. Use only the committed parquet cache.

## Handoff for next cycle

- **Changed (Cycle 940)**:
  - `research/liquidity_001_evaluation.py`: the DSR call is seeded with the frozen
    configuration's declared seed (20240101) and draw count (2000), block 22; the
    probability is read from the key `compute_dsr` actually returns (0.001498 instead of
    `nan`); the DSR is printed to stdout so the "two runs are byte-identical" test covers
    it; the "Realized cost drag" line is published as 0.715880%/yr (percent convention);
    the record carries a correction note. The published record and report were
    regenerated.
  - `research/experiments/liquidity_001_evaluation_erratum_001.md`: the correction of
    record for the two `liquidity_001` defects; the verdict is unchanged (Rejected/Failed,
    conditions i and iv fired; the DSR is not one of the four pre-registered conditions).
  - `research/pairs_001_evaluation.py`: the reported turnover cost drag applies the cost
    rate once (2.1364%/yr instead of 0.0006%/yr); the gross excess before any cost
    (8.7862%/yr) is published next to the excess net of the turnover cost and before
    borrow (6.6497%/yr); the correction notice now states that the superseded Cycle-936
    figures were never published and points at the erratum that now exists.
  - `research/pairs_001_failure_analysis.py`: the hard-coded cost breakdown and the
    narrative sentence that quoted it are corrected; both failure-analysis artifacts are
    regenerated.
  - `research/experiments/pairs_001_evaluation_erratum_001.md`: the correction of record
    for the `pairs_001` defects (drag, label, broken reference); the verdict is unchanged
    (Rejected/Failed, conditions i, iii and iv fired).
  - `research/bootstrap_seed_audit.py` plus `research/experiments/bootstrap_seed_audit_001.md`
    and `research/reports/bootstrap_seed_audit_001.md`: a deterministic AST audit of every
    bootstrap call site in `research/` and `src/` (55 sites; the only unseeded ones left
    are the four historical calls in `research/run_cycle3.py`, which are reported, not
    repaired); it fails closed when a candidate evaluator holds an unseeded call.
  - Tests: DSR reproducibility across processes, the frozen-seed wiring, the published
    DSR/probability, the liquidity percent convention, the `pairs_001` drag identity and
    the cost-series unit test, plus seven audit tests.
- **Verified (Cycle 940)**:
  - `python research/liquidity_001_evaluation.py` -> `OVERALL: PASS`, exit 0,
    `DSR|-2.968111|PROB|0.001498|N_CONFIGS|1|SEED|20240101|DRAWS|2000|BLOCK|22`,
    `VERDICT|Rejected/Failed`, `FROZEN_CONDITIONS_FIRED|i,iv`, identical across three runs.
  - `python -m pytest -q tests/test_liquidity_001_evaluation.py` -> 18 passed.
  - `python research/pairs_001_evaluation.py` -> `OVERALL: PASS`, exit 0,
    `COST|TURN|68.691589|TURN_COST|0.02136449|BORROW|0.20327103|TOTAL_DRAG|0.22463551|NET_EXCESS|-0.13677386`,
    `VERDICT|Rejected/Failed`, `FROZEN_CONDITIONS_FIRED|i,iii,iv` (the net excess, the fold
    Sharpes, the CI and the DSR are unchanged by the correction).
  - `python research/pairs_001_failure_analysis.py` -> exit 0, `FIRED|i,iii,iv`,
    `NET_EXCESS_AFTER_BORROW|-0.136774`.
  - `python -m pytest -q tests/test_pairs_001_evaluation.py tests/test_pairs_001_failure_analysis.py` -> 19 passed.
  - `python research/bootstrap_seed_audit.py` -> `OVERALL: PASS`, exit 0, 55 call sites, 4 unseeded (all historical).
  - `python -m pytest -q tests/test_bootstrap_seed_audit.py` -> 7 passed;
    `python -m pytest -q tests/test_leadlag_001_evaluation.py` -> 30 passed.
  - `git status --porcelain data/ config/` -> empty;
    `git diff --name-only HEAD -- config/settings.yaml` -> empty.
  - Cycle 939 (the task assigned by the previous agent) was re-verified first:
    `python research/leadlag_001_evaluation.py` -> `OVERALL: PASS`, exit 0,
    `VERDICT|Rejected/Failed`, `FROZEN_CONDITIONS_FIRED|i,ii`, and 30 tests passed.
- **Unresolved**: the two gaps above (no re-verification harness for the closed shortlist;
  DSR sample alignment between `liquidity_001` and the other three evaluators). The four
  unseeded historical calls in `research/run_cycle3.py` (which wrote the Cycle-3 incumbent
  statistics and decision records) are documented in the seed audit, not repaired. The
  `pairs_001` record's two turnover measures (68.6916 units/yr from the netted book vs
  about 71.2 units/yr from the pair-level cost series) are not yet reconciled.
- **Failed approaches**: `reversal_001`, `pairs_001`, `liquidity_001` and `leadlag_001` are
  all Rejected/Failed; do not re-propose them or open variants of them without new
  evidence. Cycle 934's four-way shortlist is exhausted, so the next candidate must come
  from a fresh, evidence-based search over the committed cache once Cycle 941 has measured
  what the four rejections rule out.
- **Operational note for the next session**: at the start of Cycle 940 an **orphaned**
  full-suite `python3 -m pytest -q` from the previous session (PPID 1) was still running
  and was concurrently rewriting committed artifacts (it rewrote
  `research/reports/sectorrotation_long_sample_feasibility_001.md` at 23:17:14 UTC, and it
  explains the unexplained working-tree diffs present at session start). It was terminated.
  Before running anything long, check for stray `pytest`/`research/` processes
  (`ps -eo pid,ppid,etime,cmd | grep -E 'pytest|research/'`), and confirm
  `git status --porcelain` is clean before and after a run.
- **Next task**: execute Cycle 941 as specified above; then prepare Cycle 942, which should
  use the Cycle-941 gross-edge decomposition to design the **new** candidate search
  (data readiness first, per AGENTS.md) rather than re-scoring the exhausted shortlist.
