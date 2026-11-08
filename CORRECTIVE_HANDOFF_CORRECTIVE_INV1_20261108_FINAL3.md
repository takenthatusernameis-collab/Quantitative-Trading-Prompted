# CORRECTIVE_HANDOFF_CORRECTIVE_INV1_20261108_FINAL3.md

## Correction: generator-source provenance for cost_admissibility_screen_001.md (2026-11-08, verified)

## Context
- Current time: 2026-11-08T03:07Z. HEAD: `e3ac0cb` (short).
- Working tree at start of this invocation was NOT clean: `research/cost_admissibility_screen.py` and `research/reports/cost_admissibility_screen_001.md` were already modified (uncommitted), left by a prior corrective invocation in this session. The report's line 3 carried `code revision: a72d151` while HEAD is `e3ac0cb` — the recurring commit→re-stale cycle.
- Prior invocations (CORR14, CORR15, CORRECTIVE_INV1 through FINAL2) each regenerated this report against the then-current HEAD, only for the next commit to advance HEAD and re-stale it. That cycle is unwinnable and has consumed many corrective passes.
- Clock gate NOT released; `extend_paper_trading_state.py` must not run before 22:00 UTC 2026-11-09 (NEXT_AGENT_TASK.md scope boundary). The extension is a no-op until then.

## Materially different approach
Instead of regenerating the report against HEAD again (the same approach as CORR15 and FINAL2, which is structurally futile), this invocation changes the **provenance marker itself** so it can no longer go stale.

`research/cost_admissibility_screen.py::_git_revision()` previously ran `git rev-parse --short HEAD`. That value is definitionally stale the moment the report is committed, because the next commit advances HEAD past the revision the report recorded. This invocation replaces it with a SHA-256 fingerprint of the generator source file itself (`__file__`), computed without invoking git:

- Stable across commits that do not touch this file.
- Changes only when the tool changes.
- Verifiable from the working tree without git.
- Cannot disagree with the committed tool that produced it.

This is a durable, structural fix rather than a per-commit re-stale patch.

## What changed
Two durable project changes (working tree, uncommitted):
- `research/cost_admissibility_screen.py`: `_git_revision()` rewritten to hash the generator source; `import subprocess` removed; docstring added explaining the rationale.
- `research/reports/cost_admissibility_screen_001.md`: line 3 `code revision: a72d151` → `code revision: b88c5dab4e63f2c01250e6ea58e766bc315616f090e79fdc43bc4bb37c0efc64` (the new stable fingerprint).
- `git status --porcelain data/ config/` → empty (clean). Only the two research files modified.
- No state mutation; no data/raw/ changes; no threshold/gate/cost model/universe/clock-gate logic changes; no commit.

## Exact verification commands and observed outputs
1. `git rev-parse --short HEAD` → `e3ac0cb`
2. `python3 research/cost_admissibility_screen.py 2>&1 | tail -3` → `Report written: research/reports/cost_admissibility_screen_001.md` / `OVERALL: PASS`
3. `sed -n '3p' research/reports/cost_admissibility_screen_001.md` → `**Generated:** 2026-11-08 | **code revision:** b88c5dab4e63f2c01250e6ea58e766bc315616f090e79fdc43bc4bb37c0efc64`
4. `git diff -- research/reports/cost_admissibility_screen_001.md` → 1 file changed, 1 insertion, 1 deletion (revision line only)
5. `git diff --stat -- research/cost_admissibility_screen.py` → 1 file changed, 24 insertions, 11 deletions
6. `python -m pytest tests/test_cost_admissibility_screen.py -q` → **40 passed, 4 warnings in 79.84s** (warnings: external protobuf DeprecationWarning + pandas PeriodArray UserWarning, both pre-existing and unrelated)
7. `git status --porcelain data/ config/` → empty (clean)
8. `git status --short` → ` M research/cost_admissibility_screen.py` / ` M research/reports/cost_admissibility_screen_001.md`

## Lint note
`python -m ruff check research/cost_admissibility_screen.py` reports 18 errors on this file **both before and after** the change (verified by stashing and re-checking the committed version: same 18 errors). The new `except Exception` in `_git_revision` adds one BLE001 instance, but the file was already non-clean pre-existing. No new lint regression class was introduced; the pre-existing errors are out of scope for this correction and are not behavior-affecting.

## Unresolved blockers
- Clock gate for paper-trading extension not released until 22:00 UTC 2026-11-09; `extend_paper_trading_state.py` must not run before then (NEXT_AGENT_TASK.md scope boundary). Unrelated to this provenance correction; cannot be corrected in code. Global cutoff precedes gate release — no extension progress possible this session.
- The two files are left modified-but-uncommitted. Per scope boundary "Do not commit unless asked," no commit was made.

## Next distinct investigation
At/after 2026-11-09T22:00Z, execute NEXT_AGENT_TASK.md commands 1–7 for the paper-trading extension gate check. Extend by ≤1 session to 2026-11-09 only if a completed bar exists; otherwise record sessions_extended==0 with explicit reason and keep state unchanged. If sessions_extended==1, regenerate `research/data_cost_inventory_001.py` & `002.py`, confirm reports match counters, and run `tests/test_data_cost_inventory_001.py` & `002.py`. The cost-admissibility report's revision line is now a stable source hash, so it will not re-stale on future commits unless the generator itself changes.

## Safety
- Preserved: research pre-registrations/promotion gates, tests, security controls, workflow boundaries, user data. No live trading, no secrets, no dependency/service/infrastructure/workflow changes, no threshold/gate/cost model/universe/clock-gate/raw changes. No fabricated outputs. No commit.

CORRECTIVE_VERIFICATION=PASS