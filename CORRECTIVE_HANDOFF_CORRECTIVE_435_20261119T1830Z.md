# Corrective handoff — invocation 435 (2026-11-19T18:30Z)

- **Status:** OK — one production wiring defect fixed and pinned by tests; no research
  threshold, gate, cost model, universe, config, state or committed data change.
- **Prior failure (434):** the corrective invocation aborted with an upstream provider
  error (`Sign up for free to continue…`, exit 1) before any tool ran. Nothing in the
  repository was corrupted; `git status --porcelain` was 0 lines at start of this
  invocation and HEAD was `c99009f`.
- **Gate state at work time:** pre-gate. `scripts/pre_gate_check.sh` →
  `PRE-GATE OK … T-12037s` (gate `2026-11-19T22:00:00Z`, epoch `1795125600`),
  state sha `bed3b2363a50d51bf059a27b2ca369d4b5480ada8ad01fe0e89756035720b750`,
  `data/raw` clean. Per the acceptance criteria exit 0 = STOP: **no extend was run**.

## Defect found and fixed

`research/paper_record_raw_coverage_audit.py` documents (checks §6, `--extend-before`)
that an extension completed in the cycle MUST carry a valid
`provider_digest_YYYYMMDD.json` and otherwise fails closed. That guard was **dead** in
the real cycle: `scripts/post_gate_orchestrator.sh` invoked cmd8c with **no argument**,
so `require_digest_for` stayed `None` and a silently failed digest write would have
left the handoff reading `Status: OK` — the exact regression the 2026-11-19 digest
acceptance criterion names ("a missing digest on a real extend is a regression").

**Change (smallest sufficient):**
- `scripts/post_gate_orchestrator.sh`: new read-only step 1b captures the pre-extend
  `last_run_date` from `data/processed/paper_trading_state.yaml` (plain `sed` text read,
  so it is not an extra interpreter step and the cycle's ordering contract is unchanged),
  validates it against `^20[0-9]{2}-[0-9]{2}-[0-9]{2}$`, and passes
  `--extend-before "$EXTEND_BEFORE"` to cmd8c only when armed. Missing/malformed state
  → flag omitted with an explicit log line (`digest requirement not armed`), so an
  ad-hoc or stubbed run cannot be failed for the wrong reason.
- `tests/test_post_gate_orchestrator.py`: 3 new tests
  (`test_cmd8c_receives_pre_extend_last_run_anchor`,
  `test_cmd8c_anchor_omitted_when_state_is_absent`,
  `test_cmd8c_anchor_omitted_when_last_run_is_not_a_session_date`) plus helpers
  (`_argv_logging_stub`, `_init_git`, `_write_state`, `_coverage_audit_argv`).

**Regression proof:** the same harness run against `git show HEAD:scripts/post_gate_orchestrator.sh`
records the audit argv as exactly `['research/paper_record_raw_coverage_audit.py']`
(no flag) → `OLD_SCRIPT_PINS_DEFECT: True`. Against the patched script the audit argv is
`[… '--extend-before', '2026-11-19']`.

## Verification (exact commands and results)

| command | result |
|---|---|
| `/tmp/kilo-venv/bin/python -m pytest -q tests/test_post_gate_orchestrator.py` | **55 passed in 9.41s** |
| `/tmp/kilo-venv/bin/python -m pytest -q tests/test_post_gate_orchestrator.py tests/test_pre_gate_check.py tests/test_post_gate_handoff_consistency.py tests/test_drift_persistence.py tests/test_drift_invariant_check.py tests/test_paper_record_raw_coverage_audit.py tests/test_paper_trading_record_status_audit.py` | **131 passed, 1 skipped in 13.55s** |
| `/tmp/kilo-venv/bin/ruff check tests/test_post_gate_orchestrator.py research/paper_record_raw_coverage_audit.py` | `All checks passed!` |
| `bash -n scripts/post_gate_orchestrator.sh` | exit 0 (syntax) |
| `/tmp/kilo-venv/bin/python research/paper_record_raw_coverage_audit.py --extend-before 2026-11-18` | `OVERALL: PASS`, exit 0, record not advanced → `no session extended (digest requirement not triggered)` |
| `/tmp/kilo-venv/bin/python research/paper_record_raw_coverage_audit.py` | `OVERALL: PASS`; `SUMMARY sessions=472 covered=466 unverified=6 attested=0 coverage_end=2026-11-10`; report byte-identical to HEAD (0 diff) |
| `/tmp/kilo-venv/bin/python research/drift_invariant_check.py` | `OK` ×3, `SUMMARY sessions=472 regime_transitions=7 high_turnover_sessions=7 threshold=0.5`, exit 0 |
| `GATE_EPOCH=1795125600 STATE_SHA256=bed3b236… bash scripts/pre_gate_check.sh` | `PRE-GATE OK … T-12037s`, exit 0 |
| `git status --porcelain -- data/raw` | 0 lines |
| state sha256 | `bed3b2363a50d51bf059a27b2ca369d4b5480ada8ad01fe0e89756035720b750` (unchanged) |
| `git status --porcelain` | only `scripts/post_gate_orchestrator.sh`, `tests/test_post_gate_orchestrator.py`, `NEXT_AGENT_TASK.md`, this handoff |

## Residual blocker / next distinct investigation

The only blocker is the clock: the 2026-11-19 gate (`22:00:00Z`) has not been released and
no mutating extend may run before it. The gate-active run must, after the extend:

1. confirm `provider_digest_20261119.json` exists next to the paper-trading artifacts,
2. confirm cmd8c now reports the extended session as attested (`n_attested >= 1`) and
   `OVERALL: PASS` **without** hand-editing the digest,
3. if the digest is missing, treat the cycle's `Status: FAILED` as the correct signal
   (do not retry the write manually, do not relax the guard).

No research pre-registration, promotion gate, cost assumption or committed data was
altered by this invocation.
