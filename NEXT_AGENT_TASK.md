# NEXT AGENT TASK — Cycle 874

## Context

Cycles 872–873 closed the `macroregime_001` data-readiness gap and recorded the evidence:
`data/raw/^VIX.parquet` now covers 2004-11-18 .. 2026-10-16 (5,514 rows), and
`research/reports/vix_backfill_001.md` plus the corrected `research/reports/data_inventory.md`
document the backfill and overlap integrity (max relative diff on Close = 0.0).

## Objective

Run a final integrity/verification pass over the VIX cache and confirm no committed artifact
under `data/processed/` or `config/` changed as a side effect of the documentation cycle.

## Acceptance criteria

1. `python research/month_end_candidate_reaudit.py` prints `OVERALL: PASS`.
2. `python research/rebalance_schedule_audit.py` prints `OVERALL: PASS`.
3. `python -m pytest -q` passes (82 tests).
4. `git status --porcelain config/ data/processed/` is empty.
5. `data/raw/^VIX.parquet` still has 5,514 rows, range 2004-11-18 .. 2026-10-16, 0 duplicate dates, 0 NaN Close.

## Validation commands

```bash
python research/month_end_candidate_reaudit.py
python research/rebalance_schedule_audit.py
python -m pytest -q
git status --porcelain config/ data/processed/
```

## Scope boundaries

- Documentation/verification only. Do not modify data, config, or candidate parameters.
- Do not dispatch this workflow or start additional agent sessions.
" filePath="/home/runner/work/Quantitative-Trading-Prompted/Quantitative-Trading-Prompted/NEXT_AGENT_TASK.md