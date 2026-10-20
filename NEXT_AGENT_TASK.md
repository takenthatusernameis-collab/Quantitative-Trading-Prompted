# NEXT_AGENT_TASK.md

## Cycle 904 — Record the deferred sample-definition decision and make the measurement path enforce it

### Context

Cycle 903 (see `research/reports/common_inception_sample_audit_001.md`) measured
the incumbent's canonical metrics and its **full promotion gate table** on the
**common-inception sample** (2004-11-18..2026-10-19, seven assets with a price
throughout) next to the union-sample numbers that the committed long-sample
artifact publishes (1993-01-29..2026-10-19, 8,488 sessions, a **1-to-7-asset**
cross-section).

| sample | sessions | canonical Sharpe | max DD | rolling-63d Sharpe | PSR | failed gates | decision |
|---|---|---|---|---|---|---|---|
| union (the committed sample) | 8,488 | 0.5657179297830458 | -0.6224126346564325 | -0.03425220400791309 | 1.6549061233035153e-08 | `full_period_sharpe`, `rolling_63d_sharpe`, `max_drawdown`, `psr` | **NO-GO** |
| common-inception slice | 5,513 | 0.7020812007943042 | -0.3669795914712545 | -0.03425220400791309 | 1.9717579528449186e-04 | the same four | **NO-GO** |
| common-inception window | 5,513 | 0.7128971065113597 | -0.3669795914712546 | -0.03425220400791309 | 2.3747177705301723e-04 | the same four | **NO-GO** |

What Cycle 903 established:

* The **numbers move materially** with the sample (Sharpe +0.136 / +0.147, max
  drawdown -62.24% -> -36.70%, PSR 1.65e-08 -> 1.97e-04 / 2.37e-04) and the
  **verdict does not**: no gate disagrees and the decision is NO-GO on every
  sample, so the incumbent's published NO-GO is **not** an artefact of the
  sample definition.
* The union sample's **-62.24% maximum drawdown is a pre-inception episode**
  (peak 2000-03-24 -> trough 2002-10-09). The union path splits into 2,975
  pre-inception sessions (Sharpe 0.38501143654921, max DD -0.6224126346564325)
  and 5,513 post-inception sessions (Sharpe 0.7128971065113597, max DD
  -0.3669795914712546).
* The union sample is **ragged**: price width 1 -> 7 (six width changes),
  selectable momentum breadth 0 -> 7, **2,640 of 8,488 sessions with fewer than
  five selectable assets** (where `select_top_decile` holds the single best
  asset) and 1,542 sessions with exactly one position.
* Cycle 903 **deliberately did not decide** which sample the *long-sample
  diagnostic's* gate table is evaluated on; it published the evidence and left
  the choice to "an explicitly recorded decision". That decision is still open.

### Objective

Record that decision **explicitly and machine-readably**, and make the
measurement path **enforce** it, so that every future long-sample verdict in
this repository is measured on a declared, fully populated cross-section instead
of on whatever window the engine happens to load. The decision must be a
declaration the code consumes and fails closed on, not a promise in prose.

### Acceptance criteria

1. A new machine-readable policy file `config/sample_policy.yaml` declares the
   decision and its inputs:
   * the **rule**: the long-sample diagnostic's promotion gate table is evaluated
     on the **common-inception sample** (the first session on which every asset
     of the universe has a price), and the union-sample numbers stay published
     next to it for continuity with the committed artifact;
   * the **derivation** of the common inception (the maximum of the per-symbol
     first dates of the raw cache) — a rule, never a frozen date;
   * the **warm-up convention**: the price frame is truncated at the common
     inception before the signal is formed (`common_inception_slice`), and the
     warm-up-preserving variant (`common_inception_window`) is published beside
     it;
   * the decision date, the evidence artifact
     (`research/reports/common_inception_sample_audit_001.md`) and the conditions
     under which the decision must be revisited (a change of universe, a change
     of the engine's window semantics, a new asset in the universe).
   No existing file under `config/` is modified.
2. `research/common_inception_sample_audit.py` **consumes** the policy: it exits
   non-zero with an explicit error when the policy file is missing, malformed, or
   names a rule the tool does not implement, and it re-derives the common
   inception from the raw cache instead of trusting the policy's date. The tool
   accepts an optional `--policy PATH` argument so that the failure path is
   testable without touching `config/`.
3. A decision record `research/reports/sample_policy_001.md` states the decision,
   the evidence it rests on, **what it changes** (the incumbent's long-sample
   numbers: Sharpe 0.5657179297830458 -> 0.7020812007943042 /
   0.7128971065113597, max DD -0.6224126346564325 -> -0.3669795914712545 /
   -0.3669795914712546, PSR 1.6549061233035153e-08 -> 1.9717579528449186e-04 /
   2.3747177705301723e-04), **what it does not change** (the incumbent's NO-GO
   on every sample, the promotion decision on the paper record, every gate,
   threshold, decision mapping, universe, cost model and Sharpe convention) and
   the conditions for revisiting it.
4. The committed artifact `research/reports/promotion_feasibility_backtest_001.md`
   and every number in it are **not** modified; the audit's published numbers
   are unchanged; the tool remains read-only with respect to `data/` and
   `config/` (except that it now *reads* the new policy file).
5. Tests assert that the policy is consistent with the raw cache (the declared
   rule reproduces the derived common inception), that the tool **fails closed**
   on a missing, malformed or unknown-rule policy (via `--policy` pointing at a
   file in a temporary directory), that the committed artifact is byte-identical
   after a tool run, and that the audit's published samples still match the
   policy's declared samples.
6. `git status --porcelain data/` is empty, `config/` gains exactly one new
   file, and the whole test suite is green.

### Validation commands

```
python research/common_inception_sample_audit.py       # OVERALL: PASS, numbers unchanged
python -m pytest -q tests/test_common_inception_sample_audit.py
python research/promotion_feasibility_backtest.py      # OVERALL: PASS, decision=NO-GO
python research/rolling_63d_gate_refresh.py            # OVERALL: PASS, 12/12 checks
python research/rebalance_schedule_audit.py            # OVERALL: PASS, 12/12 checks
python research/go_no_go_evaluation.py                 # decision NO-GO, failed gates ['rolling_63d_sharpe', 'psr']
python -m pytest -q                                    # whole suite green
git status --porcelain data/                           # empty
```

### Scope boundaries

* Do **not** change a gate, a threshold, the decision mapping, a candidate
  configuration, a universe, the cost model or the Sharpe convention.
* Do **not** regenerate, edit or re-number the committed long-sample artifact;
  the policy is *not* applied to its generator in this cycle — the artifact
  keeps publishing the union-sample numbers it publishes today.
* Do **not** change `src/backtest/engine.py`: the window semantics stay as they
  are; the truncation happens in front of the engine, inside the audit tool.
* Do **not** start, re-fit or re-optimise any candidate in this cycle. The
  sample-definition control for `csmomentum_001` (the rank-2 shortlist
  candidate, whose 18-asset long sample is ragged in the same way) is
  explicitly **out of scope** here: the policy makes its sample well defined,
  and it must be pre-registered before it is executed.
* If a number of the committed artifact moves, stop and report it instead of
  regenerating the published artifacts around the new value.
