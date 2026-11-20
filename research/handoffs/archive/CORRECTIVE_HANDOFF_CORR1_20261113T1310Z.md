# Corrective Handoff — Corrective Invocation 1 (2026-11-13T13:10Z) — Orchestrator CLI fail-closed hardening

## Context
- **UTC 2026-11-13T13:09:00Z (08:09 EST).** Gate for 2026-11-13 **NOT released** (releases 22:00 UTC 2026-11-13, epoch 1794607200; ~8.8h remaining). Cmds 2/4 (mutating extend) withheld (scope boundary); `extend_paper_trading_state.py` correctly returns `sessions extended: 0` / 0 writes pre-gate.
- **Why this invocation is materially different from prior failed/no-op sessions:** prior sessions re-verified the clean baseline or added mixed-regime/pass-fail tests. This invocation audited the gate-active orchestrator's **argument parser** for fail-closed defects and fixed three that silently corrupted the durable record on mis-invocation, each reproduced empirically against the pre-fix script first.

## Defects found (reproduced against `git show HEAD:scripts/post_gate_orchestrator.sh`)
| # | Defect | Old behavior (observed) | New behavior |
|---|--------|-------------------------|--------------|
| A | Unknown flags silently ignored (`*) shift ;;`) | `--bogus-flag` → **rc=0**, "cycle complete", handoff written as if a valid cycle ran | **rc=2**, `FATAL: unknown argument '--bogus-flag'`, no handoff |
| B | `--max-wait-seconds 0` accepted despite "positive integer" claim | `--max-wait-seconds 0` → **rc=3** "wait budget exhausted", indistinguishable from a mis-invocation | **rc=2**, `requires a positive integer, got '0'` |
| C | No `--help`/usage despite documented CLI | `--help` treated as unknown → **rc=3** "gate NOT released" | **rc=0**, prints usage line |

**Impact:** a typo'd `--wait-until-gate` (e.g. `--wait-untill-gate`) would have been silently ignored; the gate-active run would then exit 3 "clock gate NOT released" and the durable record would never reveal the mis-invocation. That is exactly the durable-evidence failure class the orchestrator exists to prevent.

## Smallest sufficient change
- `scripts/post_gate_orchestrator.sh` argument loop: `*)` now exits 2 with `FATAL: unknown argument`; added `-h|--help` usage path; `--max-wait-seconds` now rejects `0` (strictly positive). No change to the gate clock, extend logic, cost model, universe, or any cmd 1–8 behavior.
- `tests/test_post_gate_orchestrator.py`: 3 new regression tests (`test_unknown_flag_is_a_usage_error`, `test_max_wait_seconds_rejects_zero`, `test_help_exits_zero`).

## Verification (commands + observed results)
| Check | Command | Result |
|-------|---------|--------|
| Bash syntax | `bash -n scripts/post_gate_orchestrator.sh` | `BASH_OK` |
| Orchestrator suite | `/tmp/kilo-venv/bin/python -m pytest tests/test_post_gate_orchestrator.py -q` | **16 passed in 2.01s** (was 13) |
| Regression proof (old script) | in-place run of `git show HEAD:` script | `--bogus-flag`→rc=0, `max-wait 0`→rc=3, `--help`→rc=3 (all three defects reproduced) |
| Fix proof (new script) | same probes | rc=2 / rc=2 / rc=0 respectively; no handoff written on error paths |
| 6-module + orchestrator | `pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py tests/test_state_aggregate_audit.py tests/test_rolling_63d_gate_refresh.py tests/test_post_gate_orchestrator.py -q` | **84 passed in 43.88s** |
| Documented read-only cycle | `GATE_EPOCH=1794520800 HANDOFF=/tmp/cycle_check.md PYTHON=true RUFF=true bash scripts/post_gate_orchestrator.sh --read-only` | exit 0, `Status: OK`, `Cmds run: 1,3,5,6,7,8`, `Cmds skipped: 2,4` |
| Drift report | `python research/drift_persistence_report.py` | tail ends `2026-11-12 -1.3137`, rc=0 |
| Ruff (python) | `ruff check tests/test_post_gate_orchestrator.py` | `All checks passed!` |
| Pre-gate extend (no-op proof) | `python research/extend_paper_trading_state.py` | `sessions extended: 0`, `state write count: 0`, `raw cache: scratch (canonical data/raw untouched)`, rc=0 |

## State / integrity
- `data/processed/paper_trading_state.yaml` sha256 `2dace0e3e1accf00a749cde2baf6470b5e2abc61e542fe636854910361dec88a` (== HEAD); `last_run_date 2026-11-12`, NAV `133039.92504076837`, run_history **468**. Unchanged.
- Working tree: only the two intended files (`scripts/post_gate_orchestrator.sh`, `tests/test_post_gate_orchestrator.py`) modified. `data/`, `config/`, `data/raw/` untouched. No commits made.

## Unresolved blocker
- **Clock gate not released** for the 2026-11-13 session (releases 22:00 UTC 2026-11-13, epoch 1794607200). The real extension (cmds 2/4) and post-advance cmd 7 cannot execute until then. Deterministic blocker, not a failure loop.

## Next distinct investigation (for the gate-active run)
At/after 22:00 UTC 2026-11-13 run:
```bash
GATE_EPOCH=1794607200 HANDOFF=CORRECTIVE_HANDOFF_POSTGATE_20261113.md \
  bash scripts/post_gate_orchestrator.sh --wait-until-gate
```
If any argument is mistyped, the orchestrator now fails closed with rc=2 instead of silently exiting 3.