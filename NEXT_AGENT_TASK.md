# NEXT_AGENT_TASK — resolve DBC/csmomentum governance blocker (owner decision required)

## Context
Full suite cannot go green until governance decision on committed DBC/csmomentum cache inconsistency. Extension run failed due to committed cache refusal. Leadlag freeze fixed; slow tests pass individually.

## Objective
Obtain repository owner decision among (a) restore historical DBC to frozen cut-off, (b) recreate csmomentum artifacts from frozen historical cache, (c) amend published results with supersession record. Then rerun full suite.

## Acceptance criteria
- Owner decision recorded
- `python -m pytest -q` exits 0
- `git status --porcelain data/ config/` empty

## Validation commands
python -m pytest -q
git status --porcelain data/ config/

## Scope boundaries
- Do not edit tests/thresholds/config/data.
- Do not choose governance option unilaterally.
