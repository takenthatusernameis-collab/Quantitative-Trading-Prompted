# NEXT AGENT TASK — Cycle 882

## Context

Cycle 881 built the cost-admissibility screen the repository was missing
(`research/cost_admissibility_screen.py`, `research/reports/cost_admissibility_screen_001.md`,
`research/experiments/cost_admissibility_screen_001.md`).

What it established:

- A candidate's cost admissibility — can its gross signal survive the turnover it
  actually incurs at the repository's flat 3 bp/unit model? — is computable from the
  committed cache and the committed artifacts alone, and is now a published column.
- `overnight_capture_001`: +9.1558%/yr gross against +15.1200%/yr required ->
  **INADMISSIBLE**; break-even cost 1.7385 bp/unit, i.e. 58% of the model cost.
- `calendar_effects_001`: **ADMISSIBLE** (break-even 11.1639 bp/unit, 3.72x the model
  cost) **but with a negative benchmark-parity cost (-22.6852 bp/unit)**: to merely match
  passive close-to-close holding of the same basket on the same folds it would have to be
  *paid* 22.69 bp/unit. **Cost-admissibility is necessary and not sufficient: a candidate
  can survive its costs and still have no edge.**
- The incumbent `tsmomentum_spytrend_001`: **ADMISSIBLE** with a very large margin
  (break-even 106.7540 bp/unit, benchmark parity at 32.3052 bp/unit).
- The mechanical guard for the Cycle 880 erratum now exists: a stated cost drag is checked
  against `annual_turnover * cost_bps_per_unit / 10000` within 1e-9, and the factor-10
  error is rejected at every cost row.

What is still missing: the screen covers **three** candidates. The repository's own
shortlist (`research/reports/opportunity_shortlist.md`) has **ten** rows, and the cost column
in that file now covers only shortlist ranks 1, 4 and 10. The three remaining rows with a
derivable cost basis — `csmomentum_001` (rank 2), `sectorrotation_001` (rank 3) and
`macroregime_001` (rank 6) — still carry only a structural "(c) net return" score. The
shortlist is the instrument that chooses the next candidate, and the cost screen's own
finding (the calendar candidate is admissible and still worthless) says a gross-effect
score is not a sufficient basis for choosing one.

The two *open* families among them are `csmomentum_001` and `macroregime_001`:
`sectorrotation_001` was already evaluated on the config-faithful month-end path and
rejected/failed in Cycle 869. So the open question is concrete:

> **After the cost screen, is there any remaining candidate family whose cost headroom is
> large enough to be worth a promotion-gate test — and is that headroom an *edge* or only
> survival?**

## Objective

Complete the shortlist's cost column for the three remaining derivable candidates and
answer that question with the screen's own numbers.

**No new candidate, no new data, no re-optimization, no re-judging of any candidate.**

## Method (fixed by this task; do not re-choose)

1. Extend `research/cost_admissibility_screen.py` (do **not** write a second, parallel
   tool) so that it also covers:
   - `csmomentum_001` — frozen config `config/csmomentum_candidate_001.yaml`,
   - `sectorrotation_001` — frozen config `config/sectorrotation_candidate_001.yaml`,
   - `macroregime_001` — frozen config `config/macroregime_candidate_001.yaml`.

   Reuse the repository's **already-validated config-faithful month-end construction**
   (`src/backtest/rebalance.py`, added in Cycle 870) and the existing research tools
   `research/month_end_candidate_reaudit.py` (Cycle 871) and
   `research/sectorrotation_long_sample_feasibility.py` (Cycle 869). Do **not** re-derive
   their signals, parameters or schedule from scratch, and do **not** use the defective
   daily re-rank path or the calendar `is_month_end` path that Cycle 870 found and fixed.

2. Every new candidate's daily gross-return and daily-turnover series must be **verified
   against the committed published record** before it is screened, and a mismatch is a
   **FAIL** to be reported, never a re-tune. The records to check against are:
   - `research/reports/sectorrotation_long_sample_feasibility_001.md` (Cycle 869):
     config-faithful long sample, canonical Sharpe 0.472367, annualized turnover 2.9961x,
     175 trade days, WF mean OOS Sharpe 0.847243 over 36 folds.
   - `research/experiments/month_end_candidate_reaudit_001.md` (Cycle 871): the
     config-faithful `csmomentum_001` and `macroregime_001` numbers (turnover, trade days,
     test Sharpe, WF mean OOS Sharpe) as published there.
   State the tolerance used for each comparison and why.

3. Add **one** further decision number to the screen, computed on the candidate's own
   folds with the same machinery: the **cost per unit at which the candidate's net
   walk-forward mean OOS Sharpe falls to 0.9** — the repository's own promotion threshold
   (`AGENTS.md`, `config/promotion_gates.yaml`) — i.e. the candidate's *gate headroom*.
   A candidate whose gate headroom is at or below the model's 3 bp/unit cannot be
   promoted at the model's cost no matter how good its Sharpe is.

4. Publish, per candidate, the same block the screen already publishes (annualized gross
   signal; drag at 3/5/10 bp per unit; net annualized return; break-even cost; cost at
   which the net WF Sharpe equals the same-fold close-to-close benchmark's; minimum gross
   signal required; admissibility verdict) **plus** the new gate headroom, and state the
   screen's limitations (necessary, not sufficient).

5. Complete the cost column in `research/reports/opportunity_shortlist.md` (additive edit
   only; do not remove, re-score or re-rank an existing row without stating the reason in
   the report) for **every** shortlist row, including the rows that cannot be costed:
   list them explicitly with the reason (no cached data, no derivable turnover, or
   already rejected), so that no row is left silently without a cost basis.

6. Answer the objective question explicitly, in the report and in the experiment record:
   **which remaining candidate, if any, has enough cost headroom to be worth a
   promotion-gate test, and is that headroom an edge or only survival?** If the answer is
   "none", say so and say what the shortlist's remaining rows then support.

## Acceptance criteria

1. `research/cost_admissibility_screen.py` is **extended**, not duplicated; it still writes
   nothing under `data/` or `config/`, still prints every number in its report, and still
   exits 0 with `OVERALL: PASS`.
2. The screen's published block for `overnight_capture_001`, `calendar_effects_001` and
   `tsmomentum_spytrend_001` is **unchanged** by this cycle (same numbers to the published
   precision), and the existing reproduction checks still pass. Any change to those numbers
   must be explained in the report.
3. Each of `csmomentum_001`, `sectorrotation_001` and `macroregime_001` has a published
   screen block, and each one's series is verified against the committed published record
   with a stated tolerance; a verified mismatch is reported as a FAIL, not re-tuned.
4. The new **gate headroom** is published for every candidate the screen covers, with the
   threshold (0.9) and the folds used named explicitly.
5. The mechanical guard is applied to every new figure, and the factor-10 negative control
   still passes at every cost row.
6. `research/reports/opportunity_shortlist.md` carries a cost basis for **every** row, with
   the non-derivable rows listed and the reason given. No existing row is removed,
   re-scored or re-ranked.
7. The report states the screen's limitations (necessary, not sufficient) and answers the
   objective question.
8. New offline tests in `tests/test_cost_admissibility_screen.py` (no network, no data
   mutation) and `python -m pytest -q` passes (124 existing + the new tests).
9. `git status --porcelain data/ config/` shows **no modification** to an existing file
   under `data/` or `config/`.
10. No candidate's published verdict is changed. `csmomentum_001`, `sectorrotation_001`
    and `macroregime_001` remain rejected/failed on their own pre-registered conditions.
11. The incumbent's decision is unchanged: **NO-GO**, live deployment unsupported;
    `python research/go_no_go_evaluation.py` still prints NO-GO with
    `side_effect_free: True`.

## Validation commands

- `python research/cost_admissibility_screen.py`
- `python research/go_no_go_evaluation.py`
- `python -m pytest -q`
- `git status --porcelain data/ config/`

## Scope boundaries

- Research only. No live trading, no credential access, no scheduled jobs, no new
  dependencies.
- Do not modify existing files under `config/` or `data/`, the paper-trading state, the
  promotion gates, the incumbent configuration or the deployment decision. Do not modify
  `src/` (put candidate-specific code in `research/`); if a shared helper is genuinely
  needed, it must be additive, backward compatible and provably leave the incumbent
  artifacts byte-identical.
- Do **not** re-optimize any candidate and do **not** re-run a walk-forward evaluation to
  "rescue" a rejected candidate. This cycle measures costs; it does not re-judge
  candidates. The re-derived walk-forward statistics are a **validation** of the screen,
  not a selection over configurations.
- Do not propose a variant of any candidate (for example an overnight leg that avoids the
  second daily round trip). That is a **different hypothesis** and would need its own
  pre-registration before any backtest.
- Do not add a candidate, a universe, a cost model change, a gate or a threshold. The cost
  model stays `get_cost_params()` = 3 bp per unit of weight change, with 5 bp and 10 bp
  sensitivity rows.
- Do not dispatch this workflow or start additional agent sessions.

## Known pending item (deliberately not bundled with this cycle)

The 2026-10-19 US session is published by the provider but only becomes
*eligible* under the repository's own completeness rule
(`research/extend_paper_trading_state.py:session_is_complete`, `close_hour + 1`
= 17:00 ET = 21:00 UTC). Once that time has passed, the paper-trading record
can be extended from 449 to 450 sessions with the existing session-safe tool
(`python research/extend_paper_trading_state.py`, then
`python research/go_no_go_evaluation.py` and
`python research/drift_persistence_report.py`). Keep it separate from
candidate-evaluation cycles so the measured samples stay fixed.
