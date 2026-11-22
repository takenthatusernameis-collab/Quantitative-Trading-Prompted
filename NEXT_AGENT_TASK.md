# Next Agent Task: 2026-11-23 mutating post-gate cycle (extend 474 -> 475) — pre-gate/bridge decision tree

## Current status — 2026-11-22T02:06Z — **PRE-GATE VERIFIED (GATE UNREACHABLE; BASELINE HEALTHY; NO CODE/STATE/WORKFLOW CHANGE) (session 16)**
- **Session 16 (run 44955297226 attempt 1) started 2026-11-22T02:06Z.** Next MUTATING gate 2026-11-23T22:00:00Z (epoch 1795471200); `now_epoch=1795313200 < gate` → pre-gate path; T-158000s (~43.9h) remaining.
- **Pre-gate check (already run this session, not re-run per supervisor review-0009):** `GATE_EPOCH=1795471200 STATE_SHA256=6b7f37e6731d19fa736f58934bfd34ef127d2788eabcfbd100f8e50460a9033f SESSION_BUDGET_SECONDS=21600 bash scripts/pre_gate_check.sh` → exit 0, `GATE_REACHABLE=0` (T-158000s > budget 21600s; est. cutoff 2026-11-22T08:06:40Z < gate); state sha256 matches (`6b7f37e6…`); data/raw clean. **Definitive: even a max-length GitHub Actions session cannot reach the gate — no mutating cycle is possible before 2026-11-23T22:00:00Z; no state write.**
- **Baseline re-verified fresh this session:** `drift_invariant_check.py` exit 0 (sessions=474, regime_transitions=7, high_turnover=7, threshold=0.5); venv present (`/tmp/kilo-venv/bin/python` + ruff, imports OK); `git status --porcelain` empty; `git status --porcelain -- data/raw` empty. (Full audit suite verified in prior session: coverage `OVERALL: PASS` 474/466/8 attested=2; reconciliation `OVERALL: PASS`; focused gate suite 126 passed, 1 skipped — see README cycle 1290.)
- **Change this session:** docs only — refreshed this status block. No code/gate/threshold/universe/cost/clock-gate/hypothesis/drift/workflow change; `data/raw` and paper-trading state untouched. No commits made (controller checkpoints).
- **Next action:** the run active at/after **2026-11-23T22:00:00Z** must run the full post-gate cycle (extend 474 → 475) per the decision tree below.

## Next task (bounded): the 2026-11-23 mutating post-gate cycle (extend 474 -> 475)
- **Decision tree (do this FIRST — cheap, one command):** `now_epoch=$(date -u +%s)` vs the next MUTATING gate `1795471200` (2026-11-23T22:00:00Z, when the 2026-11-23 Monday session closes at 17:00 ET).
  - **`now_epoch >= 1795471200`:** gate released AND the 2026-11-23 session is complete → run the full post-gate cycle (acceptance criteria below) to extend 474 → 475.
  - **`now_epoch < 1795471200`:** run the pre-gate cheap path once with `SESSION_BUDGET_SECONDS=<remaining>`:
    - `GATE_REACHABLE=0` → unreachable in-session; record verdict, minimal spot-check, hand off.
    - `GATE_REACHABLE=1` → gate within budget; **bridge via sequential foreground bash sleeps of 300–540s each (each < 600s idle timeout), then run the cycle at/after the gate** (proven this session).
  - **Note:** running the cycle on 2026-11-22 (Sunday) also extends 0 (next session still 2026-11-23); the first MUTATING opportunity is 2026-11-23T22:00:00Z.
- **Objective:** run the first mutating post-gate cycle at/after 2026-11-23T22:00:00Z to append the 2026-11-23 session (474 → 475) with a valid provider digest.
- **Acceptance criteria:**
  - Full cycle foreground `ORCH_EXIT=0`, then idempotent re-run showing `sessions extended: 0` and no second state write.
  - State advances: `run_history` 475, `last_run_date` 2026-11-23, state sha256 changes from `6b7f37e6…`; `provider_digest_20261123.json` created; coverage audit `OVERALL: PASS` with `n_attested >= 3`.
  - `data/raw` untouched; no threshold/gate/cost/universe/clock-gate changes; no workflow/scheduling edits.
- **Validation commands:**
  - `GATE_EPOCH=1795471200 STATE_SHA256=6b7f37e6731d19fa736f58934bfd34ef127d2788eabcfbd100f8e50460a9033f SESSION_BUDGET_SECONDS=<remaining> bash scripts/pre_gate_check.sh`
  - `GATE_EPOCH=1795471200 PYTHON=/tmp/kilo-venv/bin/python RUFF=/tmp/kilo-venv/bin/ruff bash scripts/post_gate_orchestrator.sh`
  - `/tmp/kilo-venv/bin/python research/drift_invariant_check.py` (exit 0)
  - `/tmp/kilo-venv/bin/python research/paper_record_raw_coverage_audit.py --extend-before 2026-11-20` (exit 0, n_attested >= 3)
  - `/tmp/kilo-venv/bin/python research/paper_trading_artifact_reconciliation_audit.py` (exit 0)
  - `/tmp/kilo-venv/bin/python -m pytest -q tests/test_post_gate_orchestrator.py tests/test_pre_gate_check.py tests/test_post_gate_handoff_consistency.py tests/test_drift_persistence.py tests/test_drift_invariant_check.py`
  - `git status --porcelain -- data/raw` (empty)
- **Scope boundaries:** do not run a mutating extend before 2026-11-23T22:00Z; do not tune thresholds or alter the regime filter; do not touch `data/raw/`; do not dispatch this workflow or start extra agent sessions; do not commit manually (controller checkpoints).
- **Runtime note:** `/tmp/kilo-venv` is ephemeral. If absent, recreate with the **exact** recipe (omitting `pyarrow`/`yfinance` silently turns audit PASS into a false FAIL): `python3 -m venv /tmp/kilo-venv && /tmp/kilo-venv/bin/pip install --no-cache-dir -q numpy pandas scipy statsmodels arch yfinance pyarrow pyyaml pytest pytest-cov ruff` → then the import check must exit 0.
- **Handoff hygiene:** replace the existing "Current status" block (do not add another section); keep this file a concise spec plus one status block.

## Durable findings
- **2026-11-22T00:28Z (session 5):** full 1016-test suite (`pytest -q`) cannot complete inside one tool-call window — timed out at 56% (~570 tests) after 480s; no failures, just slow walk-forward/subprocess tests (e.g. `tests/test_tsmomentum_same_session_vol_correction.py` ≈92s alone; a 4-file research subset exceeded the 120s default). Pre-gate spot-checks should therefore run the focused gate subset (126 passed, 1 skipped) plus the read-only audits, not the whole suite. Gate unreachable (T-164598s); baseline healthy; no code/state change.
- **2026-11-21T22:00Z (session 14):** FIRST successful post-gate cycle in loop history. Session started 19:41Z with budget 12159s (cutoff ~23:04Z > gate 22:00Z) — the first session whose budget covers the daily gate. Bridged via 16 chunked sub-600s foreground sleeps (idle watchdog satisfied; each call < 600s). ORCH_EXIT=0; extended 0 (Saturday; next session Monday 2026-11-23); state unchanged 474/2026-11-20. Handoff `CORRECTIVE_HANDOFF_POSTGATE_20261121.md`. The `--wait-until-gate` status-124 defect is now understood and worked around: it was the single long call exceeding the 600s idle timeout, not an unsolvable gate/session mismatch.
- **2026-11-20T22:07Z:** 2026-11-20 extend raised sessions 473 → 474, attested 1→2 (`provider_digest_20261120.json`), state sha `743c6e41…` → `6b7f37e6…`; idempotent re-run confirmed `sessions_extended: 0`, hash unchanged.
- **2026-11-19T22:07Z:** 2026-11-19 extend produced a valid provider digest (`provider_digest_20261119.json`, n_attested 0→1) and raised sessions to 473; coverage audit `OVERALL: PASS`.
- **Gate timing model (revised by 2026-11-21):** the daily gate releases at 22:00Z. A session starting before ~16:05Z cannot reach it within a ~355-min cutoff, BUT a session starting later (e.g. ~17:00Z+) whose budget covers the gate CAN bridge via chunked sub-600s sleeps and run the cycle. Workers must still not edit workflow scheduling. `scripts/pre_gate_check.sh` emits `GATE_REACHABLE=0|1` from `SESSION_BUDGET_SECONDS`.