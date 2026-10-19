# NEXT AGENT TASK — Cycle 881

## Context

Cycle 880 pre-registered and evaluated the overnight-session capture candidate
`overnight_capture_001` (`research/hypotheses/overnight_capture_001.md`,
`research/reports/overnight_capture_backtest_001.md`,
`research/experiments/overnight_capture_backtest_001.md`).

Result: **Rejected/Failed**, and the reason is structural rather than noisy.

- The **gross** overnight premium is real: +9.16%/yr annualized for the 1/3
  SPY/QQQ/IWM basket over 6,637 sessions (the exploratory diagnostic's
  mechanism observation is confirmed).
- An overnight-only leg must be flat during the day, so it round-trips **twice
  per session** -> 504 units of annual turnover -> **15.12%/yr** of cost at the
  repository's flat 3 bp/unit model, which is **larger than the gross premium**.
- Net WF mean OOS Sharpe **-0.599718**; positive fold rate 15.15%;
  DSR (N=3) -2.446673; block-bootstrap 95% CI [-0.788295, 0.034214].
- It also **loses to passive close-to-close holding of the identical basket** on
  identical folds (WF mean OOS Sharpe +0.844696), so the negative Sharpe is a
  cost result, not a market-direction result.

Two general lessons follow, and neither has been quantified in this repository
yet:

1. **A candidate's gross signal size must be compared with its own annualized
   cost drag *before* it is short-listed.** The shortlist
   (`research/reports/opportunity_shortlist.md`,
   `research/reports/candidate_family_selection_001.md`) ranks candidates by
   gross effect size; no artifact states each candidate's annualized cost drag
   at the repository's own cost model, nor the cost per unit at which each
   candidate would clear the >= 0.9 gate.
2. The Cycle 880 erratum (disclosed in
   `research/hypotheses/overnight_capture_001.md`) is a live hazard: a stated
   cost figure of "1.51%/yr" was actually 15.12%/yr. Nothing in the repository
   mechanically checks a stated cost-drag figure against the turnover the
   strategy actually incurs.

## Objective

Build one **read-only, deterministic** cost-admissibility screen that is
reusable for every future candidate, and apply it to the repository's existing
shortlist. No new candidate, no new data, no walk-forward re-run.

## Method (fixed by this task; do not re-choose)

- New script `research/cost_admissibility_screen.py` that, for a given
  strategy definition, computes from the committed cache:
  - **annualized gross signal** (annualized return with **zero** cost),
  - **annualized cost drag** at the repository's cost model
    (`get_cost_params()` = 3 bp/unit) and at the 5 bp and 10 bp rows,
  - the **break-even cost per unit** at which the net annualized return is
    zero, and the cost per unit at which the net Sharpe equals the
    same-fold close-to-close benchmark's,
  - the **minimum gross annual signal** a candidate needs in order to be
    admissible at 3 bp/unit, i.e. `annualized_cost_drag`.
- Apply the screen to **at least** these three existing candidates, reusing
  their committed artifacts and their existing frozen configurations (do not
  re-derive or re-tune them):
  1. `overnight_capture_001` (Cycle 880; must reproduce 15.12%/yr drag and the
     -0.599718 WF mean OOS Sharpe),
  2. `calendar_effects_001` (turn-of-month; WF mean OOS Sharpe -0.0254),
  3. the incumbent `tsmomentum_spytrend_001` (or `csmomentum_001`/`sectorrotation_001`
     if the incumbent's turnover is not derivable from its committed artifacts -
     state which one you used and why).
- Add one **mechanical guard** for the Cycle 880 failure mode: a helper (or a
  test) that takes a stated cost-drag figure and a stated annual turnover and
  asserts `cost_drag == turnover * cost_per_unit` within 1e-9, so a factor-10
  error like the Cycle 880 erratum cannot pass unnoticed again.

## Acceptance criteria

1. `research/cost_admissibility_screen.py` exists, is read-only (writes nothing
   under `data/` or `config/`), prints every number in its report, and exits 0
   with `OVERALL: PASS`.
2. `research/reports/cost_admissibility_screen_001.md` publishes, per candidate:
   gross annualized signal, annualized cost drag at 3 / 5 / 10 bp per unit,
   break-even cost per unit, the minimum gross signal required for
   admissibility, and the resulting **admissibility verdict**; and it states
   the screen's limitations (it is a necessary, not sufficient, condition).
3. The screen reproduces Cycle 880's numbers for `overnight_capture_001`
   (15.12%/yr drag at 3 bp/unit; net WF mean OOS Sharpe -0.599718) from the
   committed artifacts, or **explains precisely** why a number cannot be
   reproduced.
4. The mechanical guard is implemented and unit-tested (a deliberate factor-10
   error must be rejected by it).
5. New offline tests in `tests/test_cost_admissibility_screen.py` (no network,
   no data mutation) and `python -m pytest -q` passes (102 existing + the new
   tests).
6. `git status --porcelain data/ config/` shows **no modification** to an
   existing file under `data/` or `config/`.
7. The incumbent's decision is unchanged: **NO-GO**, live deployment
   unsupported; `python research/go_no_go_evaluation.py` still prints NO-GO
   with `side_effect_free: True`.
8. `research/reports/opportunity_shortlist.md` is updated with the cost column
   for the candidates the screen covers (additive edit only; do not remove or
   re-rank existing rows without stating the reason in the report).

## Validation commands

- `python research/cost_admissibility_screen.py`
- `python research/go_no_go_evaluation.py`
- `python -m pytest -q`
- `git status --porcelain data/ config/`

## Scope boundaries

- Research only. No live trading, no credential access, no scheduled jobs, no
  new dependencies.
- Do not modify existing files under `config/` or `data/`, the paper-trading
  state, the promotion gates, the incumbent configuration or the deployment
  decision. Do not modify `src/` (put candidate-specific code in `research/`).
- Do **not** re-optimize any candidate and do not re-run a walk-forward
  evaluation to "rescue" a rejected candidate. This cycle measures costs; it
  does not re-judge candidates.
- Do not propose a variant of `overnight_capture_001` (for example a version
  that avoids the second daily round trip). That is a **different hypothesis**
  and would need its own pre-registration before any backtest.
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
