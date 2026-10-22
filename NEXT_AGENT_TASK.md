# Cycle 949 — Commodity data gate measurement (scratch fetch; no committed cache rewrite)

## Context
- Cycle 948 found `commoditytrend_001` blocked by data gate: cached common inception 2015-01-02 supports only 3 folds vs required 10.
- Hypothesis/config remain frozen and blocked; no trading verdict published.

## Objective
Measure whether upstream history can satisfy the data gate (common inception <= 2011-10-20) by fetching into a scratch directory only. Do not modify committed cache.

## Acceptance criteria
- Fetch DBC/BNO/UNG/GLD upstream history into `/tmp/scratchpad/commodity_fetch/` only.
- Report common inception and fold count.
- `git status --porcelain data/ config/` empty.
- `python -m pytest -q` unchanged.

## Scope boundaries
- No committed cache changes. No evaluation until gate passes.
- No new commodities.

## Validation commands
- `git status --porcelain data/ config/`
- `python -m pytest -q`
