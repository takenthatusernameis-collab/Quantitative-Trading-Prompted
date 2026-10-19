# Corrective Invocation 1 - Handoff (Cycle 880 recovery)

**Date:** 2026-10-19 | **Base revision:** 639188b | **Resulting HEAD:** see the
two Cycle 880 commits + the Cycle 881 task-spec commit.

## Why the previous invocation produced no durable changes

`/home/runner/work/_temp/kilo-session-24.log` shows the previous invocation
(Cycle 880) reach the point of drafting the pre-registration hypothesis and
then fail **every** `Write` tool call with
`Error: The write tool was called with invalid arguments: ["content"]: is
missing and is required` / `["filePath"]: is missing and is required` -
repeatedly, until the session expired. The document body was emitted as plain
assistant text instead of as a tool payload, so nothing reached the worktree:
`git status` stayed empty and no commit was made.

## What this corrective invocation did differently

1. **Different write path.** No `Write` tool call was used for the large
   documents; every artifact was produced with a quoted heredoc
   (`cat > file <<'EOF'`) or a small `python3` text-edit, which does not depend
   on the failing argument shape.
2. **Incremental commits.** The pre-registration was committed **before** any
   backtest was executed (commit `8b04295`), so the hypothesis-first ordering
   required by AGENTS.md is preserved and verifiable in git history. The
   evaluation artifacts were committed in a second commit (`d157f2d`), and the
   next-cycle task spec in a third (`b98cded`).
3. **One identified defect in the inherited draft** (a factor-10 error in the
   stated annual cost drag) was corrected by a *disclosed post-execution
   erratum*, not by silently editing the pre-registration.

## Artifacts produced (all committed)

| Path | Content |
|---|---|
| `research/hypotheses/overnight_capture_001.md` | pre-registration (299 lines) + version history + post-execution erratum |
| `config/overnight_capture_001.yaml` | frozen candidate config (NEW file; no existing config touched) |
| `research/overnight_capture_backtest.py` | read-only evaluation script (no writes to `data/` or `config/`) |
| `research/reports/overnight_capture_backtest_001.md` | full report (data-integrity pre-check, per-fold table, pooled stats, DSR, bootstrap CI, cost rows, benchmarks, gates) |
| `research/experiments/overnight_capture_backtest_001.md` | experiment record (repository format) |
| `tests/test_overnight_capture_backtest.py` | 7 offline tests (pure helpers + fold count + read-only cache check) |
| `NEXT_AGENT_TASK.md` | Cycle 881 spec |

## Findings (the research result itself)

The overnight-session capture candidate is **Rejected/Failed**:

| Gate | Observed | Verdict |
|---|---|---|
| WF mean OOS Sharpe >= 0.9 | -0.599718 | FAIL |
| positive fold rate >= 50% | 15.15% | FAIL |
| pooled OOS trades > 100 | 8016 | PASS |
| net WF Sharpe > same-fold close-to-close | -0.599718 vs +0.844696 | FAIL |
| survives the 10 bp/unit cost row | -3.537547 | FAIL |
| DSR (N=3) | -2.446673 | REJECTED |
| block-bootstrap 95% CI lower bound > 0 | -0.788295 | FAIL |

Mechanism: the **gross** overnight premium is real (+9.16%/yr for the 1/3
SPY/QQQ/IWM basket over 6,637 sessions) but an overnight-only leg must be flat
during the day, so it round-trips twice per session -> 504 units/yr -> 15.12%/yr
of cost at the repository's 3 bp/unit model, which exceeds the gross premium.
It also loses to passive close-to-close holding of the identical basket on
identical folds, so the negative Sharpe is a cost result, not a
market-direction result.

## Exact verification commands and observed outputs

```
$ python3 research/overnight_capture_backtest.py
... OVERALL: PASS            (exit 0; DECISION: Rejected/Failed)

$ python3 -m pytest -q
102 passed in 85.25s (0:01:25)          # 95 pre-existing + 7 new

$ python3 research/go_no_go_evaluation.py
decision (evaluate_go_no_go): NO-GO
rationale: 2 promotion gate(s) failed: rolling_63d_sharpe, psr. ...
side_effect_free: True                 (exit 0)

$ git status --porcelain data/ config/
(empty)                                  # after the new config was committed

$ git status --short
(empty)                                  # worktree clean
```

## Unresolved blockers / open items

1. **The factor-10 erratum is a live hazard.** Nothing in the repository
   mechanically checks a stated cost-drag figure against the turnover a
   strategy actually incurs; Cycle 881's mechanical guard addresses this.
2. **No candidate has yet been screened for cost admissibility.** The
   shortlist ranks gross effect size only; the required gross signal at 3
   bp/unit has never been stated per candidate. Cycle 881 addresses this.
3. **A "long-only, no second round trip" variant of the overnight family is
   untested.** It is a *different* hypothesis and was deliberately not tested
   or proposed here; it must not be inferred from this result.
4. **Pending paper-trading extension** (449 -> 450 sessions) remains
   deliberately unbundled; see `NEXT_AGENT_TASK.md`.
