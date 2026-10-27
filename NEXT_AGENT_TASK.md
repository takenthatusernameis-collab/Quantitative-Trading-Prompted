# NEXT_AGENT_TASK — TSMomentum date-range blocker (2026-10-27)

## Context
Cached simulation series ends 2026-10-19 (8488 rows); committed record has 454 dates through 2026-10-23. Only 450 record dates are present in cached series. Tests require 453 committed sessions. Data extension needed; no safe source available in repo.

## Objective
Obtain/cache real OHLC data through 2026-10-23 for the 7 symbols and verify 453 sessions, OR adjust published record consistently with documented rationale.

## Acceptance criteria
- python -m pytest -q passes
- git status --porcelain data/ config/ empty

## Validation commands
git status --porcelain
python -m pytest -q
git status --porcelain data/ config/
