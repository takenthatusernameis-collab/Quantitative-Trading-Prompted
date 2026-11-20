# Corrective Handoff — Invocation 250

## Correction applied
Removed trailing blank line at EOF from `research/reports/sectorrotation_long_sample_feasibility_001.md` (line 875). This was the sole cause of `git diff --check` failure ("new blank line at EOF"). The previous invocation (8/CORRECTIVE_HANDOFF_CORR_CURRENT.md) claimed this fix was applied and verified, but the blank line remained in the working tree — this invocation applies the fix durably.

## Verification
Command: `git diff --check`
Output: exit 0 (no whitespace/EOF errors)

Command: `git diff --cached --check`
Output: exit 0

## Remaining unstaged changes (not part of this fix)
- `research/reports/sectorrotation_long_sample_feasibility_001.md` — code revision `2ec0575` → `a188737` (auto-updated report field, no whitespace issue)
- `research/reports/tsmomentum_sma175_candidate_eval_001.md` — Git rev `2ec0575` → `a188737` (auto-updated report field, no whitespace issue)

## Unresolved blockers
None related to `git diff --check`. Per NEXT_AGENT_TASK.md, a separate DBC/csmomentum governance blocker requires an owner decision and is out of scope for this whitespace fix.

CORRECTIVE_VERIFICATION=PASS
