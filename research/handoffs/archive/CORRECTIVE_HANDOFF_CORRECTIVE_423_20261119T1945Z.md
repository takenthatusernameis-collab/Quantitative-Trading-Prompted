# Corrective invocation 423 — record/artifact reconciliation audit (2026-11-19)

## Trigger
Recovery message: the previous invocation "produced no durable project changes".
The previous invocation had only re-run the pre-gate cheap path and correctly
stopped (gate **2026-11-19T22:00:00Z**, epoch `1795125600`). The gate was still
closed (~2.2h out), so no mutating cycle work was permitted. This invocation did
not repeat the no-op verification; it closed a genuine evidence gap and found a
real committed-artifact defect.

## Finding
Nothing in the repository compared the state's `run_history` rows with the
committed per-session parquet artifacts across the whole record:

* `research/audit_state_aggregates.py` re-derives state-level fields from
  `run_history` only (never reads artifacts);
* `research/drift_invariant_check.py` checks the **latest** session's regime
  exposure only;
* `research/paper_record_raw_coverage_audit.py` compares against `data/raw`.

Artifact writes have silently dropped before
(`research/repair_missing_paper_trading_artifacts_868.py`), and a repair can
write a value the live path would never have written — undetectable by any
existing check.

## Change
New `research/paper_trading_artifact_reconciliation_audit.py` (read-only) plus
`tests/test_paper_trading_artifact_reconciliation_audit.py` (26 hermetic tests).
For every session it re-derives, and compares with the committed artifacts:

| artifact | checks |
|---|---|
| `daily_pnl` | single row, dated to session; `daily_return`, `daily_pnl`, `nav` equal the row; `daily_pnl == nav - previous nav` (first session: notional 100000) |
| `risk_state` | single row, dated; `vol_scale`, `dd_scale` equal the row; `exposure == vol_scale * regime_exposure`; `drawdown` equals the running maximum drawdown of the record NAV series up to that session |
| `regime` | single row, dated; `regime_exposure` equals the row |
| `positions` | exactly the configured universe, dated; nonzero-weight count equals `n_positions`; gross `sum|w| <= 1`; `sum|w_t - w_{t-1}|` equals the row's `turnover` (from session 2) |

A mismatch is exempted only when both `(session, field)` **and** the exact
observed value match a pinned `KNOWN_DEFECTS` entry; anything else exits 1.
Exit 2 for missing state/artifact-dir/config.

Also wired into `scripts/post_gate_orchestrator.sh` as read-only **cmd8d**
(with `RUFF4` membership and 3 new orchestrator regression tests) so the
cycle's exit code and durable handoff can no longer stay "OK" while this audit
fails. The audit writes only its own report; it never writes the state,
artifacts, `data/raw`, or config.

## Defect found (attested, not repaired)
`risk_state_20261102.parquet` stores `drawdown = -0.06562469374042057` — the
**all-time** maximum drawdown at repair time — instead of the **2026-11-02
session's running maximum drawdown**, `-0.049857401112321176` (the value stored
for both neighbouring sessions 2026-10-30 and 2026-11-03). Root cause is the
reconstruction in `research/repair_missing_paper_trading_artifacts_868.py`,
whose docstring states `drawdown = state.max_drawdown`. The other 471 sessions
reconcile exactly, including the 2026-11-02 `positions`, `regime`,
`daily_pnl`, `vol_scale`, `dd_scale` and `exposure` fields.

The value is **not** rewritten: a committed historical artifact must not be
hand-edited to make a check pass. It is pinned by exact observed value in
`KNOWN_DEFECTS` and reported as `ATTESTED` in every run and in
`research/reports/paper_trading_artifact_reconciliation_001.md`.

## Verification (all commands run in this invocation)
| command | result |
|---|---|
| `GATE_EPOCH=1795125600 STATE_SHA256=bed3b236… bash scripts/pre_gate_check.sh` | `EXIT=0`, `T-8100s remaining`, state sha matches, `data/raw` clean — STOP, no cycle |
| `/tmp/kilo-venv/bin/python research/paper_trading_artifact_reconciliation_audit.py` | `ATTESTED 2026-11-02 drawdown …`; `SUMMARY sessions=472 attested=1 unattested=0 window=2025-01-02..2026-11-18`; `OVERALL: PASS`; `EXIT=0` |
| rerun of the audit (report determinism) | report sha256 `cba45b22f9de4345d505647abd6e15a76190e5dc1edd9a3a3c5d8d2a5a39c1d6` both times |
| `pytest -q tests/test_post_gate_orchestrator.py tests/test_pre_gate_check.py tests/test_post_gate_handoff_consistency.py tests/test_drift_persistence.py tests/test_drift_invariant_check.py tests/test_paper_record_raw_coverage_audit.py tests/test_paper_trading_artifact_reconciliation_audit.py tests/test_provider_digest.py` | **185 passed, 1 skipped in 15.72s** |
| `pytest -q tests/test_post_gate_orchestrator.py` | **58 passed in 10.22s** |
| same 3 new orchestrator tests against `git show HEAD:scripts/post_gate_orchestrator.sh` | **3 failed** (regression proof: they detect the missing cmd8d/wiring) |
| `ruff check` on all touched files and the whole `RUFF4` list | **All checks passed!** |
| `bash -n scripts/post_gate_orchestrator.sh` | exit 0 |
| `git status --porcelain -- data/raw` | empty |
| state sha256 | unchanged `bed3b2363a50d51bf059a27b2ca369d4b5480ada8ad01fe0e89756035720b750` |

No production model/backtest code, threshold, gate, cost model, universe,
config or the paper-trading record/state was modified. No live trading.

## Files
- `research/paper_trading_artifact_reconciliation_audit.py` (new)
- `research/reports/paper_trading_artifact_reconciliation_001.md` (new, regenerated deterministically)
- `tests/test_paper_trading_artifact_reconciliation_audit.py` (new)
- `scripts/post_gate_orchestrator.sh` (cmd8d step + RUFF4 entry)
- `tests/test_post_gate_orchestrator.py` (3 tests)
- `NEXT_AGENT_TASK.md` (session log + validation command)

## Unresolved blocker / next distinct investigation
Gate clock not released (~2.2h). The next agent whose run is active at/after
2026-11-19T22:00:00Z must run the full post-gate cycle once and then an
idempotent re-run, and must confirm cmd8d reports `OVERALL: PASS` with
`attested=1 unattested=0` (any new mismatch means a real regression in the new
session's artifacts — record it, do not retune or hand-edit).

Next bounded task (post-gate, not started): decide whether to repair
`risk_state_20261102.parquet`'s drawdown via a guarded, tested reconstruction
script (mirroring `repair_missing_paper_trading_artifacts_868.py`'s
reconstructability guards) or keep it permanently attested. Do not edit the
parquet by hand.
