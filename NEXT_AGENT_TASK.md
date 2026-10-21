# NEXT_AGENT_TASK.md

## Cycle 921 — Publish the SMA-175 candidate's promotion verdict and quantify the reachability of its two failed gates

### Context
Cycle 920 evaluated `tsmomentum_sma175_candidate` against the full promotion gate suite of `config/promotion_gates.yaml` with `research/tsmomentum_sma175_promotion_gate_eval.py` (read-only, deterministic) and published the complete gate table:

| Gate | Value | Threshold | Result |
|------|-------|-----------|--------|
| track_record_length | 8488 | >= 126 | PASS |
| full_period_sharpe | 1.607869 | >= 0.9 | PASS |
| rolling_63d_sharpe | **-0.448918** | >= 0.9 | **FAIL** |
| max_drawdown | -0.094633 | >= -0.15 | PASS |
| rolling_63d_max_dd | -0.038564 | >= -0.15 | PASS |
| regime_flips | 277 | >= 1 | PASS |
| psr | **0.896592** | >= 0.95 | **FAIL** |

**Decision: NO-GO** (`CANDIDATE_PROMOTABLE: NO`). Evidence: `research/reports/tsmomentum_sma175_promotion_gate_eval_001.md`, `research/experiments/tsmomentum_sma175_promotion_gate_eval_001.md`, regression tests in `tests/test_tsmomentum_sma175_promotion_gate_eval.py` (14 tests).

Two gaps remain in the research record:

1. **The candidate has a gate verdict but no research label.** AGENTS.md ("Decision discipline") requires every result to be labelled *credible candidate for further validation / exploratory signal / rejected/failed / blocked by data-infrastructure*. `research/reports/opportunity_shortlist.md` still describes the family only as "TSMOM parameter variants | 25/35 | Rejected | Tested worse than incumbent on identical data"; the SMA-175 variant's own measured verdict is recorded in no shortlist row, so a reader of the shortlist cannot tell that this variant was evaluated against the *full* gate suite and failed it.
2. **The verdict is not quantified for action.** The PSR misses by 0.053408 (0.896592 vs 0.95) at the published Sharpe standard error 0.150565, and the rolling-63-session Sharpe is -0.448918 against a 0.9 threshold. The record does not say whether the PSR is attainable at the observed mean (a track-record-length question, measured for the incumbent in Cycles 865/866) or whether the variant is far from the gate on both axes. Without that, "rejected" is a number, not a decision.

Semantics settled in Cycle 921 (do not re-open): the tool's `OVERALL` is the verdict on the **tool's own internal checks** (Cycle 920 acceptance criterion 2: "Tool prints `OVERALL: PASS` only if all internal structural checks pass; fails closed otherwise"), which is the repository-wide convention; the **candidate's promotion verdict** is the separate `Decision` (GO / NO-GO / INCONCLUSIVE). The two axes are independent and are reported separately. The PSR gate is computed against the fixed backtest-baseline Sharpe **1.4178** documented in `config/promotion_gates.yaml` (never against a candidate-specific value).

### Objective
Publish the SMA-175 candidate's **decision**, not just its numbers: label it explicitly under AGENTS.md's decision discipline, and quantify — with a read-only tool, from the published series — how far each failed gate is from being cleared and whether the PSR gate is reachable at the record's observed mean. No re-fit, no parameter search, no promotion.

### Acceptance criteria
1. The experiment record `research/experiments/tsmomentum_sma175_promotion_gate_eval_001.md` carries the explicit research label (**rejected/failed**), the complete gate table, both failed gates with their values, and the reachability numbers.
2. `research/reports/opportunity_shortlist.md` gains a **dated addendum** recording the SMA-175 variant's measured verdict (and the PSR target used) under the existing "TSMOM parameter variants" family. The incumbent's row, score and rank are **not** re-scored, re-ranked or re-weighted, and no existing shortlist row is removed.
3. The reachability statement is **computed, not asserted**, by a read-only tool that reuses the repository's own machinery (`src/evaluation/statistics.py:compute_psr`, `src/evaluation/sharpe.py`, the raw parquet cache) and reports at least: (a) the observed Sharpe and its standard error as published, (b) the observed Sharpe required for `psr` = 0.95 at that standard error, (c) the gap to the observed Sharpe, (d) the number of additional sessions at the record's observed mean return and dispersion that would be needed to reach it — or the explicit statement that it is not attainable within a stated horizon. Every quoted number must be reproducible by running the tool.
4. The promotion gates, their thresholds, the decision mapping, the universe, the cost model, the Sharpe convention and the committed Cycle 920 gate table are **unchanged**; no committed artifact is modified other than the records this cycle is allowed to write.
5. Read-only with respect to market data and configuration: `git status --porcelain data/ config/` -> empty; `git diff --stat -- research/run_cycle6.py` -> empty. No new dependency, no network access, no live trading, no secrets.

### Scope boundaries
- Do not change `config/promotion_gates.yaml`, any threshold, the decision mapping, or the published Cycle 920 gate values.
- Do not re-run the strategy on a different sample, search parameters, re-fit, re-rank candidates, promote or deploy anything.
- Do not modify the incumbent's artifacts (`research/reports/tsmomentum_sma175_candidate_eval_001.md`), the `sectorrotation_*` or `csmomentum_*` records, or any file under `data/` or `config/`.
- Do not re-open the `OVERALL` vs `Decision` semantics question (settled in the Context above) and do not edit the Cycle 920 pre-registration; it is preserved in git history at commit `c3a22b6`.
- The test suite's known side effect (re-stamping `research/reports/sectorrotation_long_sample_feasibility_001.md` and `research/reports/tsmomentum_sma175_candidate_eval_001.md` with the current commit hash) is documented repo behaviour; revert that one-line stamp after the suite, as every prior cycle did.

### Validation commands
```bash
python research/tsmomentum_sma175_promotion_gate_eval.py
python -m pytest -q tests/test_tsmomentum_sma175_promotion_gate_eval.py
git status --porcelain data/ config/
git diff --stat -- research/run_cycle6.py
```

### Evidence artifacts
- Updated experiment record `research/experiments/tsmomentum_sma175_promotion_gate_eval_001.md` (label + gate table + reachability).
- Dated addendum in `research/reports/opportunity_shortlist.md`.
- The read-only tool that computes the reachability numbers, plus its report/record.
- Reproduction commands and the observed outputs of the validation commands above.

### Handoff (for the cycle after)
- Changed: Cycle 920 tool corrected (PSR target 1.4178 instead of the candidate's own Sharpe; `OVERALL` restored to the tool-check verdict of acceptance criterion 2; `--no-report` added so the tool can run without writing artifacts), the Cycle 920 report and experiment record regenerated, new regression test file `tests/test_tsmomentum_sma175_promotion_gate_eval.py` (14 tests).
- Verified: `python research/tsmomentum_sma175_promotion_gate_eval.py` -> `STRUCTURAL: PASS`, `OVERALL: PASS`, `DECISION|NO-GO`, `CANDIDATE_PROMOTABLE|NO`, `PSR_TARGET|1.4178`, exit 0; `python -m pytest -q tests/test_tsmomentum_sma175_promotion_gate_eval.py` -> 14 passed; `git status --porcelain data/ config/` -> empty; `git diff --stat -- research/run_cycle6.py` -> empty.
- Unresolved: the SMA-175 candidate has no research label in the shortlist and no quantified gate reachability; the two failed gates are not yet decomposed into "how far" and "attainable at the observed mean or not".
- Failed approaches: (a) computing the `psr` gate against the candidate's own backtest-scale Sharpe (0.856637) — it is not comparable with any published PSR and has been replaced by the documented 1.4178 target (0.896592); (b) reading `OVERALL` as the candidate's promotion verdict — it is the tool-check verdict, and the two axes are now reported separately.
- Next task: Cycle 921 as specified above.
