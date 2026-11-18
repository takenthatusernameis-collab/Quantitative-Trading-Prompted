# Next Agent Task: 2026-11-19 gate cycle (pre-gate first; extend only at/after 22:00Z)

## Cycle result — 2026-11-18 drift decision COMPLETE (verified 2026-11-18T22:11Z)
- **Answer to the previous task:** all four 2026-11-18 drift flags were re-derived from committed source and **all four are `observe`** (no mitigation). Decision record: `research/reports/drift_decision_20261118.md`.
- **Reproduced exactly:** `high_turnover 0.5132058911351663` (threshold `config/paper_trading_config.yaml:22`, code `src/simulation/paper_trading.py:374`) `=` `sum|w_prev| = sum|Δw|` of `positions_20261117.parquet`; `regime_flip 1.0→0.0` (`paper_trading.py:404-414`, `config/paper_trading_config.yaml:19`); `low_rolling_sharpe -1.9744867954469325`, persistence `16` (streak `2026-10-28`→`2026-11-18`; `src/evaluation/drift.py:38-39`, `paper_trading.py:416-427`); `regime_persistence_low 1` (hard-coded threshold 5, reset-to-1 on flip at `paper_trading.py:352-353,439`).
- **Mismatch hypothesis falsified:** `run_history[-1]` for 2026-11-18 has `regime_exposure 0.0`, `n_positions 0`; `regime_20261118.parquet` has `regime_exposure 0.0`; `positions_20261118.parquet` is all zeros. The `1.0` in the flag is the *previous* session (`run_history[-2]`, 2026-11-17). Flag, applied exposure and artifact all derive from the same `latest["regime_exposure"]` column (`paper_trading.py:278`, `:469`, `:505-510`). `spy_price` NaN in the regime artifact is by construction (`paper_trading.py:508`; `engine.py:500-513` emits no `price_SPY`).
- **Structural cause (evidence, 472 sessions):** every one of the 7 days with `turnover > 0.5` is a regime-transition day, and every one of the 7 regime transitions has `turnover > 0.5`; median turnover `0.00148`. The 2026-11-18 liquidation is the SPY<200dSMA filter (`engine.py:207-219`, `config/simulation_candidate_001.yaml:34-38`) de-risking to cash, not unintended churn.
- **Production verdict unchanged:** `research/go_no_go_evaluation.py` → `NO-GO`, `failed_gates=['rolling_63d_sharpe','psr']` (psr `0.5304`, grey zone). `regime_flips` gate now counts `7` (passes).
- **Verification run:** `research/drift_persistence_report.py` tail ends `2026-11-18 -1.9745`; `research/rolling_63d_gate_refresh.py` `OVERALL: PASS` (12/12, read-only proof incl. byte-identical state/raw); `pytest -q tests/test_drift_persistence.py tests/test_rolling_63d_gate_refresh.py` → **30 passed in 6.88s**; `ruff` on both scripts → **All checks passed!**; `git status --porcelain -- data/raw` empty; state sha `bed3b2363a50d51bf059a27b2ca369d4b5480ada8ad01fe0e89756035720b750` unchanged.

## Next task (bounded): the 2026-11-19 gate cycle
- **Gate:** **2026-11-19T22:00:00Z** (Thu 17:00 ET), epoch **1795125600**. Previous cycle (2026-11-18) is complete; do not re-run it.
- **Objective:** run the cheap pre-gate path; only if the gate is released, run the full post-gate cycle once, confirm idempotency, and report the new day's drift flags (likely `regime_persistence_low`/`high_turnover` again if exposure re-enters or exits; expected set depends on the SPY/SMA200 state, not on tuning).
- **Acceptance criteria:**
  - Pre-gate command run in the foreground and its exit code recorded (0 = stop, 3 = gate reached/precondition change).
  - If exit 3 and `data/raw` clean: one foreground full cycle (`ORCH_EXIT=0`), then one idempotent re-run showing `sessions extended: 0` and no second state write; handoff `Status: OK`.
  - Extends at most one session, only with a completed bar; `data/raw` untouched; no threshold/gate/cost/universe/clock-gate changes.
  - New drift flags re-derived from source and recorded; if a `turnover > 0.5` day occurs **without** a regime transition, treat that as the defect signal from `research/reports/drift_decision_20261118.md` §7 and document it (do not retune).
- **Validation commands:**
  - `GATE_EPOCH=1795125600 STATE_SHA256=bed3b2363a50d51bf059a27b2ca369d4b5480ada8ad01fe0e89756035720b750 bash scripts/pre_gate_check.sh`
  - `GATE_EPOCH=1795125600 PYTHON=/tmp/kilo-venv/bin/python RUFF=/tmp/kilo-venv/bin/ruff bash scripts/post_gate_orchestrator.sh` (only if released)
  - `/tmp/kilo-venv/bin/python research/drift_persistence_report.py` (tail)
  - `/tmp/kilo-venv/bin/python -m pytest -q tests/test_post_gate_orchestrator.py tests/test_pre_gate_check.py tests/test_post_gate_handoff_consistency.py tests/test_drift_persistence.py`
  - `git status --porcelain -- data/raw` (empty)
- **Scope boundaries:** do not run a mutating extend before the gate; do not tune thresholds or alter the regime filter; do not touch `data/raw/`; do not dispatch this workflow or start extra agent sessions; do not commit manually.

## Durable finding persisted this cycle (2026-11-18T23:23Z, corrective inv 382) — NEW MEASUREMENT DEFECT
- **What was found:** the SPY-200dSMA regime factor applies *session t's own close* to *session t's own return*. `src/simulation/engine.py::_regime_exposure` builds `sma = spy.rolling(200).mean()` including `t` and sets `exposure[spy < sma] = 0.0`; `engine.py:450-452` multiplies that into `base_weights` on the same index row and `_finalize` computes `gross_ret = (scheduled * asset_ret)` with `asset_ret = close.pct_change()`. Identical in `research/run_cycle6.py::_apply_overlay` (`weights.mul(ef, axis=0)`). The momentum signal is correctly lagged (`src/features/momentum.py:105 weights.shift(1)`), so the regime factor is the only same-session input on the execution path. `src/simulation/paper_trading.py:288-296` (`daily_pnl = nav * latest["net_return"]`) carries it into the live record. This is the same defect class as the already-corrected vol-estimate feedback (`lag_vol_estimate`, Cycle 926) but was never audited.
- **Evidence:** `research/reports/tsmomentum_regime_lookahead_audit_001.md` (tool `research/tsmomentum_regime_lookahead_audit_001.py`, tests `tests/test_tsmomentum_regime_lookahead_audit_001.py`). Committed path reproduces the published anchor exactly (48 folds, mean OOS Sharpe `0.947307`, 6013 trades); lagging the regime factor one session (`exposure.shift(1)`) gives **`0.153040`** (43/48 folds worse). Post-2017 period: Sharpe `1.333367 → 0.555815`, max DD `-7.7940% → -15.4646%`, trades `1218 → 1247`, turnover unchanged. Live record: 55 of 472 sessions at zero exposure, 25 of 55 with a negative base-portfolio return.
- **Not fixed, deliberately:** correcting it needs an opt-in switch in `src/simulation/engine.py` + `research/run_cycle6.py` (mirroring `lag_vol_estimate`), a default-path bit-identity proof and a re-derivation of every published statistic. Out of scope for a read-only corrective invocation; bounded below.
- **Also inaccurate until then:** `research/reports/deployment_dossier_001.md:279` ("regime computed point-in-time") and `research/reports/go_nogo_evaluation_001.md:75` ("SPY SMA computed point-in-time"). Promotion decision unchanged (`research/go_no_go_evaluation.py` → NO-GO).
- **Read-only proof:** `data/` and `config/` tree digests byte-identical before/after both runs; state sha `bed3b236…` unchanged; `git status --porcelain -- data/raw` empty; two consecutive runs produce byte-identical reports apart from the timestamp line.

### Deferred bounded task (do AFTER the 2026-11-19 gate cycle completes)
- **Objective:** add an opt-in `lag_regime_exposure` switch (default `False`) to `src/simulation/engine.py` and `research/run_cycle6.py`, applied exactly like `lag_vol_estimate` (`exposure.shift(1).fillna(0.0)`), with a default-path bit-identity proof against a frozen pre-change copy.
- **Acceptance criteria:** default path reproduces `0.947307` (48-fold) and the committed state's 472 sessions bit-for-bit; lagged path reproduces `0.153040` from the audit; no config file sets the switch; `data/` and `config/` byte-identical; NO-GO verdict recorded on both paths.
- **Validation:** `pytest -q tests/test_tsmomentum_regime_lookahead_audit_001.py tests/test_real_extension_path.py tests/test_paper_trading_extend.py`; `ruff check` on touched files.
- **Scope boundaries:** do not change defaults, thresholds, universe, cost model or the committed record; do not promote or re-rank the candidate.

## Prior verified fixes at HEAD (preserved, do not re-open)
- **inv-386-recovery:** handoff-consistency nav pattern accepts negative NAV.
- **inv-473:** shortlist gross-edge test write-scope check diffs harness-only changes.
- **inv-230:** go_no_go parser strips markdown bullets for rolling Sharpe (`src/simulation/paper_trading.py:590`).
- **inv-182:** orchestrator gates mutating extend on `PRE_GATE` (clock), not `--read-only`.
- **inv-228:** cmd9 state-fingerprint accepts optional leading minus.
- **inv-1:** orchestrator fails closed (rc=2) when `PYTHON`/`RUFF` missing.
- **2026-11-17T05:37Z:** handoff consistency guard is record-anchored/forward-compatible.
- **2026-11-17T01:56Z:** orchestrator cmd4b regenerates record-status artifacts after extend.
- **2026-11-17T01:48Z:** record-status audit test asserts committed artifacts equal generator output.
- **2026-11-18 corrective inv 222:** removed two dead lint defects in `research/eval_cryptofunding.py` (behaviour-preserving).
- **2026-11-18 corrective inv 216:** `research/data_cost_inventory_001.py` tolerates non-parquet files in `data/processed/`.

## Runtime note
`/tmp/kilo-venv` is ephemeral. If absent before a gate step:
```
python3 -m venv /tmp/kilo-venv
/tmp/kilo-venv/bin/python -m pip install --no-cache-dir numpy pandas scipy statsmodels arch yfinance pyarrow pyyaml pytest ruff
```

## Session log (non-redundant)
- **Corrective inv 383 (2026-11-18T23:24Z):** pre-gate cheap path `EXIT=0` (gate 2026-11-19T22:00:00Z, T-81339s) with state sha `bed3b236…` and `data/raw` clean — no cycle permitted. Verification: `drift_persistence_report.py` tail ends `2026-11-18 -1.9745` (stored==recomputed True); focused regression suite **97 passed, 1 skipped**; `ruff` clean on drift/gate scripts; `git status --porcelain -- data/raw` empty; state sha unchanged. No production code, threshold, config, state or committed artifact modified.
- **Corrective inv 382 (2026-11-18T23:05–23:23Z):** pre-gate cheap path `EXIT=0` (gate 2026-11-19T22:00:00Z, T-81426s) with state sha `bed3b236…` and `data/raw` clean — no cycle permitted. Instead of a no-op re-verification this invocation audited and **persisted a new measurement defect**: the SPY-SMA regime factor is same-session (see "Durable finding" above). New files only: `research/tsmomentum_regime_lookahead_audit_001.py`, `research/reports/tsmomentum_regime_lookahead_audit_001.md`, `tests/test_tsmomentum_regime_lookahead_audit_001.py`, `CORRECTIVE_HANDOFF_CORRECTIVE_382_20261118T2323Z.md`. Verification: anchor `0.947307` reproduced; lagged path `0.153040`; `pytest` focused suite **102 passed, 1 skipped** (incl. 5 new tests); `ruff` clean on both new files; two runs byte-identical apart from timestamp; state sha and `data/raw` unchanged. No production code, threshold, config, state or committed artifact modified.
- **Session 2 inv 1 (2026-11-18T22:08–22:11Z, run 44374955463):** completed the assigned drift evaluation (record: `research/reports/drift_decision_20261118.md`). All four flags reproduced; all four decided `observe`; the `regime_flip` vs `regime_exposure` mismatch claim was falsified against the committed state and artifacts; no code/state/threshold change. Verification: `rolling_63d_gate_refresh.py` `OVERALL: PASS` 12/12, `pytest` 30 passed, ruff clean, `data/raw` clean, state sha unchanged `bed3b236…`. Supervisor rec `…-review-0078` accepted and answered (disposition `verified`).
- **Corrective inv 7 (2026-11-18T22:04–22:08Z):** 2026-11-18 gate cycle verified complete. First handoff was `Status: FAILED` because `cmd7b` self-raced with the aborted invocation's `data_cost_inventory_001.md` write; a clean `run_audit(write=False)` gave `n_before 857 n_after 857`, `FAILED_CHECKS []`. Foreground idempotent re-run: `ORCH_EXIT=0`, `sessions extended: 0` (cmd2/cmd4), cmd4b `OVERALL: PASS`, cmd5 `69 passed`, cmd7a/b `OVERALL: PASS`, cmd7c `43 passed`, cmd8 clean; handoff rewritten `Status: OK`. Bar cross-check: `daily_pnl_20261118.parquet` == `run_history[-1]`. Post-gate focused suite `73 passed, 1 skipped` (skip expected), ruff clean, `data/raw` untouched. Detail: `CORRECTIVE_HANDOFF_CORRECTIVE_7_20261118T2208Z.md`.
- **Corrective inv 222 (2026-11-18T15:33Z):** removed two dead lint defects in `research/eval_cryptofunding.py`; targeted ruff clean, `py_compile` ok, `tests/test_eval_cryptofunding*.py` 68 passed, gate suite 74 passed, pre-gate EXIT=0. Detail: `CORRECTIVE_HANDOFF_CORRECTIVE_222_20261118T1533Z.md`.
- **Session 1 inv 1 (2026-11-18T10:23Z, run 44284895009):** pre-gate cheap path EXIT=0 before the 2026-11-18 gate; venv recreated; focused suite 74 passed; state HEAD `fb5143b`; no change.
- **Session 12 inv 1 (2026-11-18T05:37Z, run 44222711169):** pre-gate EXIT=0 (`05ca6c2f…`); focused suite 74 passed; ruff clean; no change.
- **Session 5 inv 1 (2026-11-18T04:26Z):** pre-gate EXIT=0; focused suite 74 passed; ruff clean; no change.
- **Corrective inv 216 (2026-11-18T04:25Z):** `data_cost_inventory_001.py` skips non-parquet files; artifacts byte-identical; focused suite 74 passed; pre-gate EXIT=0. Detail: `CORRECTIVE_HANDOFF_CORRECTIVE_216_20261118T0425Z.md`.
- **Session 4 inv 1 / Session 2 inv 1 / Session 1 inv 1 (2026-11-18T02:2x–02:4xZ, run 44222711169):** pre-gate EXIT=0 each time (`05ca6c2f…`), focused suite 74 passed, ruff clean, no change.
- **Compact history of earlier pre-gate re-verifications:** run 44165547375 (sessions 2/4; 2026-11-17 gate verified), run 44077834177 (sessions 6/7/10/13/14), run 44008498688 (sessions 4/6/7/13/15, incl. gate-1 FAIL on the point-in-time-complete subsample: 41 folds mean OOS Sharpe 0.787522 < 0.9; artefact-fold-12-removed 40 folds 1.352958; incumbent NO-GO unchanged), runs 43722618751 / 43754114833 / 43852775967 / 43952759940 (identical EXIT=0 verifications). 2026-11-16T22:03Z (run 43952759940): 2026-11-16 gate extended 469→470, NAV 131036.60557839136.
