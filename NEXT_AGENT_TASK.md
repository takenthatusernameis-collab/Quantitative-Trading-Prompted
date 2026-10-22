# Cycle 946 — Backfill README.md with Cycles 936–945 (stale by ten cycles)

## Context

`README.md` ends at **Cycle 935** (`reversal_001` Rejected/Failed). Ten research
cycles have executed since then and are recorded only in
`research/experiments/*.md` / `research/reports/*.md` and in git history:

| Cycle | What happened | Verdict |
|---|---|---|
| 936 | `pairs_001` frozen pre-registration + evaluation (6 cointegrated sector pairs, short-side borrow 25 bp/unit) | **Rejected/Failed** (conditions i, iii, iv fired) |
| 937 | (task handoff commit; the `pairs_001` record carries the cycle) | — |
| 938 | `liquidity_001` frozen pre-registration + evaluation (Amihud illiquidity, top-2-of-9) | **Rejected/Failed** (conditions i, iv fired) |
| 939 | `leadlag_001` frozen pre-registration + evaluation (futures→ETF lead-lag, 5 pairs) | **Rejected/Failed** (conditions i, ii fired) |
| 940 | Seeded the `liquidity_001` DSR (unseeded bootstrap → non-reproducible) and corrected the cost-drag lines of `liquidity_001` and `pairs_001` | defect repair; verdicts unchanged |
| 941 | Re-verified all four closed shortlist candidates; decomposed each failure into gross edge vs cost drag | **no_gross_edge** / **gross_edge_below_cost_hurdle**; consolidated statement published |
| 942 | (task handoff commit; `common_inception_sample_audit_001.md` regenerated) | — |
| 943 | `cryptofunding_001` pre-registration frozen (`config/cryptofunding_001.yaml`) | — |
| 944 | `cryptofunding_001` evaluation implemented | exploratory signal (not promoted) |
| 945 | Corrected the Cycle 944 cost-model defect (0.02 bp/unit + no capital charge → frozen 5.0 bp/unit + 2.00%/yr) and reconciled every metric against Cycles 891–896 | verdict unchanged |

The strategic consequence is not recorded in `README.md`: **the Cycle-934
shortlist is now fully exhausted.** All four candidates (`reversal_001`,
`pairs_001`, `liquidity_001`, `leadlag_001`) are **Rejected/Failed**, and
`cryptofunding_001` (the older Cycle-11 shortlist's rank 7) remains an
**exploratory signal** that fails the trade-count gate under every cost model.
The incumbent `tsmomentum_spytrend_001` stays **Credible Candidate / NO-GO**.
No candidate line in the repository is open for promotion.

## Objective

Append one entry per cycle (936–945) to `README.md`, in the repository's
existing cycle-entry format (UTC timestamp, what was and was not changed, the
measured result, the artifacts, the tests, the verification commands, the
decision and the handoff). Every number quoted must be re-derived from the
committed artifact named in this task — never transcribed from this file.

## Acceptance criteria

- `README.md` carries one entry per cycle 936–945, in chronological order, each
  stating: what was changed (nothing, for measurement/defect cycles), the
  measured result with its verdict, the artifacts, the test count, the
  verification commands, the decision and the next task.
- Every figure quoted is re-derived from the committed record for that cycle
  (the tool, report and experiment record named in the cycle's handoff).
- The new entries state explicitly that the Cycle-934 shortlist is exhausted
  and that no candidate line is open for promotion.
- `git status --porcelain data/ config/` is empty after the work.
- No candidate, gate, threshold, cost model, universe, hypothesis or committed
  record is modified.

## Scope boundaries

- Documentation only. No backtest, no new candidate, no code change, no data
  write, no fetcher call.
- Do not re-open any closed candidate line and do not propose a new candidate
  here (that is a separate, later task once the record is current).

## Validation commands

- `git status --porcelain data/ config/`
- `git diff --stat README.md` (only `README.md` should appear)
- Spot-check: for each cycle entry, the quoted headline matches the committed
  `research/experiments/<cycle>_*.md` and `research/reports/<cycle>_*.md`.

## Handoff notes

- Follow the format of the existing Cycle 934/935 entries: a one-paragraph
  "what was measured / what did not change", an artifacts line, a tests line,
  a verification line and a handoff line.
- Measurement and defect-repair cycles state explicitly that no candidate was
  executed, re-tuned, re-ranked or promoted.
- The final entry (Cycle 945) should point at the consolidated consequence:
  the shortlist is exhausted and the next evidence-based step is a new
  market-opportunity search over the repository's actual data and cost model,
  not a re-score of the closed list.