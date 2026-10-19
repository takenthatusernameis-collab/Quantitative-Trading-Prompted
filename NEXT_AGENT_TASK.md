# NEXT AGENT TASK — Cycle 873

## Context

Cycle 872 closed the `macroregime_001` data-readiness gap that Cycle 871 left open:

* `data/raw/^VIX.parquet` was backfilled from 2025-01-02 to **2004-11-18** (5,514 rows, 2004-11-18 .. 2026-10-16) using the existing `yfinance` path (`auto_adjust=False`, EOD `Close`, UTC index, `Open High Low Close Volume` schema). The extension is append-only in time: the previously cached rows are **byte-identical** to the newly downloaded series over the overlap (max relative diff on `Close` = 0.0, sha256 `58da9ca2f088906a`).
* `research/month_end_candidate_reaudit.py` now runs on the **real VIX gate** (no ablation). `macroregime_001` legacy reproduces the published numbers exactly (test Sharpe 0.2950, max drawdown -0.1807, turnover 3.13x, 58 trades, WF mean OOS Sharpe 0.4331 over 24 folds, 75.0% positive, 137 pooled trades); config-faithful gives WF mean OOS Sharpe 0.2636, positive fold rate 66.7%, 193 pooled trades → all three gates fail → **verdict unchanged (Rejected/Failed)**.
* The Cycle 871 ablation numbers (legacy test Sharpe 0.3371 / WF 0.4628, faithful test Sharpe 0.1705 / WF 0.2838) are kept as a documented alternative in `research/experiments/month_end_candidate_reaudit_001.md` § "Cycle 871 ablation alternative", not deleted.

Verification this cycle: `python research/month_end_candidate_reaudit.py` → **OVERALL: PASS, 17/17**; `python research/rebalance_schedule_audit.py` → **OVERALL: PASS**; `python research/sectorrotation_long_sample_feasibility.py` → runs clean (decision NO-GO, unchanged); `python -m pytest -q` → **82 passed**; `git status --porcelain config/ data/processed/` → empty.

## Objective

**Refresh the repository's descriptive data inventory to match the backfilled `^VIX` cache, and record the Cycle 872 backfill as a durable evidence artifact.**

Two bounded steps, in this order:

1. **Correct `research/reports/data_inventory.md`.** The file still describes `^VIX` as 8,502 rows starting 1993-01-04 (a stale pre-backfill figure). The real cache is 5,514 rows, 2004-11-18 .. 2026-10-16. Update the `^VIX` row of the price-data table and the prose that references VIX history coverage, and recompute the overview total if it changes. Do **not** regenerate the whole file from scratch unless its generator is present and deterministic; prefer a surgical edit and note the revision.
2. **Write the backfill evidence artifact.** Create `research/reports/vix_backfill_001.md` (hypothesis/experiment record per the repository's documentation standards) recording:
   - the data-readiness gap it closes (priority 1 of the strategic objective),
   - provider, symbol, schema, date range, row count, UTC index, no duplicate dates, no NaN `Close`,
   - the integrity check result over the overlapping range (2025-01-02 .. 2026-10-16): max relative diff on `Close` = 0.0, byte-identical sha256,
   - the re-audit outcome with the numbers that decide it (WF mean OOS Sharpe 0.4331 → 0.2636, gate 0.9, verdict unchanged),
   - the reproduction command (`python research/month_end_candidate_reaudit.py`).

## Acceptance criteria

1. `research/reports/data_inventory.md` states the real `^VIX` coverage (5,514 rows, 2004-11-18 .. 2026-10-16) and no longer claims 8,502 rows from 1993.
2. `research/reports/vix_backfill_001.md` exists and contains: mechanism/gap, provider and schema, date range and row count, the overlap integrity check result, the re-audit verdict with deciding numbers, and the reproduction command.
3. `python research/month_end_candidate_reaudit.py` still prints `OVERALL: PASS` (17/17) and `git status --porcelain config/ data/processed/` is still empty — i.e. the inventory correction touches only `research/reports/` and the new artifact.
4. `python -m pytest -q` still passes (82 tests).
5. No candidate configuration, universe, parameter, gate threshold, cost model, Sharpe convention or committed artifact under `data/processed/` is changed.

## Validation commands

```bash
python research/month_end_candidate_reaudit.py      # OVERALL: PASS
python research/rebalance_schedule_audit.py         # OVERALL: PASS
python -m pytest -q
git status --porcelain config/ data/processed/      # empty
```

## Scope boundaries

- **Do not** re-optimise, re-tune or re-select anything; this is a documentation + evidence cycle.
- **Do not** modify `data/raw/*`, `data/processed/*`, `config/*`, or any experiment record other than the two deliverables.
- **Do not** create a new provider, dependency, service, scheduled job, agent or workflow.
- **Do not** dispatch this workflow or start additional agent sessions.
- If the inventory file cannot be safely corrected by surgical edit (e.g. its generator is the authoritative source and re-running it would overwrite other content), stop and report the precise blocker rather than hand-editing it.