# NEXT_AGENT_TASK.md

## Cycle 905 — Pre-register sample-definition control for csmomentum_001 (common inception)

### Context
Cycle 904 recorded a machine-readable sample policy for the incumbent long-sample diagnostic and made `research/common_inception_sample_audit.py` enforce it. The policy explicitly notes: *"Applies to the incumbent long-sample diagnostic universe as measured; csmomentum_001 long-sample sample-definition control is out of scope for this cycle."* The policy also states the control must be pre-registered before csmomentum_001 is executed.

`config/csmomentum_candidate_001.yaml` freezes a 18-asset universe. Scanning the raw cache shows the common inception (max of per-symbol first dates) is **2006-02-06** — so the csmomentum_001 long sample is ragged in the same way the incumbent was, and its evaluation sample must be well-defined before any execution/evaluation uses it as a promotion gate.

### Objective
Pre-register a sample-definition control for `csmomentum_001` in a machine-readable form, without changing gates/thresholds/decision mapping/universe/cost model or regenerating existing artifacts.

### Acceptance criteria
1. Extend `config/sample_policy.yaml` to add a `candidates.csmomentum_001` section (do **not** remove or change existing keys). It must declare:
   * `universe` (from config/csmomentum_candidate_001.yaml),
   * `rule_id: "common_inception_fully_populated"`,
   * `derivation.rule`: "common_inception = max of per-symbol first dates in the raw cache (re-derived from data/raw at measurement time; never a frozen date)",
   * `long_sample_diagnostic.evaluation_sample: "common_inception_slice"`,
   * `long_sample_diagnostic.publish_alongside` including `common_inception_window` and (for continuity) `union_sample` (or equivalent names),
   * `warm_up_convention` matching the incumbent pattern,
   * `evidence_note` pointing to the raggedness and that it must be pre-registered before execution,
   * `conditions_for_revisit` including universe/engine window semantics/new asset.
2. Create `research/csmomentum_common_inception_audit.py` (read-only w.r.t. data/ and config/ except reading the policy and raw cache) that:
   * accepts `--policy PATH` and fails closed if policy missing/malformed or candidate section missing/invalid,
   * re-derives common inception from raw cache for the candidate universe (never trusts a frozen date),
   * reports union vs common-inception slice/window (sessions, start/end, raggedness: price width changes / sessions with < N selectable assets as appropriate),
   * writes `research/reports/csmomentum_common_inception_audit_001.md` with the measurement,
   * exits non-zero on any structural check failure.
3. Add `tests/test_csmomentum_common_inception_audit.py` asserting: policy has candidate section consistent with raw cache; tool fails closed on bad policy; data/ and config/ untouched (except reading policy); artifact is written deterministically.
4. Run the new tool to produce the report; do not modify `research/experiments/*`, `research/reports/month_end_candidate_reaudit_001.md`, or any committed artifacts.
5. `git status --porcelain data/` empty; only intended new/modified files committed; full test suite green (or at least the new tests + existing audit tests pass).

### Validation commands
```
python -m pytest -q tests/test_common_inception_sample_audit.py
python research/csmomentum_common_inception_audit.py  # OVERALL/PASS as implemented
python -m pytest -q tests/test_csmomentum_common_inception_audit.py
python -m pytest -q
git status --porcelain data/
```

### Scope boundaries
* Do **not** execute csmomentum_001 backtests/walk-forward or change its numbers.
* Do **not** change gates/thresholds/decision mapping/universe/cost model/Sharpe convention.
* Do **not** regenerate existing experiment records.
* Truncation logic should mirror the incumbent pattern (slice before signal formation) conceptually; implement read-only measurement.
