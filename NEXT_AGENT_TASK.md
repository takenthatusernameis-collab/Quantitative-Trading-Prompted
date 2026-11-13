# Next Agent Task: finish stale-anchor repair verification, then resume the 2026-11-13 gate

## Context
Cycle 1252 (2026-11-13, run 43353707922 attempt 1 session 11 inv 1) ran the FULL 800-test
suite for the first time. Prior gate cycles only ever ran ~104 tests and never saw this.
Result at HEAD: **14 failed, 783 passed, 3 skipped in 55:45**.

Root cause: stale historical anchors not updated when the committed paper-trading record
advanced (2026-11-09 -> 2026-11-12). The committed state now has **468** sessions
(cache-overlap **466**), trailing 63d Sharpe **-1.4394 / -1.6214**, canonical Sharpe
**1.4102**, PSR **0.9028** — but the tools/tests still pinned 450/465 sessions and older
metric values. These are maintenance anchors, not gate/threshold/cost/universe logic.

## What changed this session (uncommitted working tree)
Repaired all 14 stale anchors (no gate/threshold/cost/universe/clock-gate/raw changes):
- `research/tsmomentum_same_session_vol_correction.py`: `COMMITTED_TRAILING_SHARPE`
  -1.1566354312981708 -> -1.4394168982987599; `committed_record_loaded` 465 -> 468.
- `tests/test_tsmomentum_same_session_vol_correction.py`: `committed_sessions` 450 -> 466.
- `research/tsmomentum_vol_estimate_consolidation.py`: `committed_record_loaded` 465 -> 468;
  `CORRECTED_RECORD_EXPECTED` -> canonical 1.4102271780414941, trailing -1.6213634935218275,
  PSR 0.4957133449958039, maxDD -0.07814098097117361.
- `tests/test_tsmomentum_vol_estimate_consolidation.py`: `committed_sessions` 450 -> 466.
- `tests/test_tsmomentum_sma175_promotion_gate_eval.py`: PSR anchor 0.8958075181188366 -> 0.9028798778337083.
- `README.md`: restored the reversal-erratum measured figures (0.752318, 4.2843%, erratum filename).
- Regenerated `same_session` + `vol_estimate` report/experiment artifacts.

Verified so far: `same_session` module **27 passed** (0 failed); `reversal_001_erratum_001` **4 passed, 1 skipped**; both tools pass standalone (`RC=0`). The `vol_estimate`/`sma175` module run was still in progress at session end (no failure observed through 29 tests).

## Objective (next task, bounded)
1. Finish the repair verification: run the 4 repaired modules and confirm 0 failures.
2. If green, run the FULL suite once (`pytest tests/ -q`, ~55 min) and confirm 0 failed; fix any residual.
3. Then resume the primary gate task: at/after 22:00 UTC 2026-11-13 (epoch 1794607200) run the gate extension (`scripts/post_gate_orchestrator.sh`), extending by <=1 session only if a completed bar exists.

## Acceptance criteria
- [ ] `tests/test_tsmomentum_same_session_vol_correction.py` all pass
- [ ] `tests/test_tsmomentum_vol_estimate_consolidation.py` all pass
- [ ] `tests/test_tsmomentum_sma175_promotion_gate_eval.py` all pass
- [ ] `tests/test_reversal_001_erratum_001.py` all pass
- [ ] Full `pytest tests/ -q` reports 0 failed
- [ ] `data/raw/` untouched; no threshold/gate/cost/universe/clock-gate changes

## Validation commands
```
/tmp/kilo-venv/bin/python -m pytest tests/test_tsmomentum_same_session_vol_correction.py tests/test_tsmomentum_vol_estimate_consolidation.py tests/test_tsmomentum_sma175_promotion_gate_eval.py tests/test_reversal_001_erratum_001.py -q
/tmp/kilo-venv/bin/python -m pytest tests/ -q
git status --porcelain
```

## Scope boundaries
- Do not change thresholds/gates/cost model/universe/clock-gate logic; do not touch `data/raw/`.
- The repaired anchors are tied to the current 468-session committed record. They will drift
  again on the next state/cache advance; re-derive values before re-pinning (do not guess).
- Gate remains time-gated: this run's envelope (started ~07:18 UTC, hard timeout 9983s) ends
  ~10:05 UTC, before the 22:00 UTC gate. Leave the gate extension to the gate-active run.