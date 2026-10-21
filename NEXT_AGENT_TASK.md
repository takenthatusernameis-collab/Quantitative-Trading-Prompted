# NEXT_AGENT_TASK.md

## Cycle 926 — Make the same-session volatility estimate correctable behind a default-off switch, and re-derive the incumbent's published record on the corrected path

### Context
Cycle 925 diagnosed the incumbent's `rolling_63d_sharpe` gate failure on the committed 450-session paper-trading record (`research/reports/tsmomentum_rolling63_weakness_diagnosis_001.md`):

- The trailing 63-session Sharpe is **-0.4489181511478863**, at the **6.44th percentile** of the record's own 388 rolling windows; the gate passes in **73.97%** of them (bootstrap 95% CI [59.54%, 92.78%]). The weakness is concentrated in **Apr–May 2025** and **Jul–Oct 2026** and does **not** cluster in any published observable-state bucket (F2/F3/F4 are one-sided inside the record period; the only two-sided families are a contiguous time split whose gap CI includes zero).
- **No permitted fix exists**: the strongest isolated overlay variant (no volatility target) lifts the failing window only to **-0.034252**, still far below the 0.9 gate; and per Cycle 866 the PSR gate is the binding constraint anyway. The incumbent's verdict (**Credible Candidate**) and its promotion decision (**NO-GO**) are unchanged, and no production code was touched.

Cycle 925 also **found and quantified a separate measurement defect**: the committed volatility target sets session *t*'s exposure from a realised-volatility estimate whose trailing 63-session window **includes session t itself** (same-session feedback). It is present in three places:

- `research/run_cycle6.py::_apply_overlay` (the published research path)
- `src/simulation/engine.py::_target_weights` (the shared simulation / live paper-trading path)
- `src/evaluation/risk.py` (both overlay helpers)

Measured effect (Cycle 925, isolated scratch paths): committed-record Sharpe **1.771084 → 1.635705**, full-path Sharpe **1.486941 → 1.413736**, trailing-63d Sharpe **-0.448918 → -0.515807** when the estimate is lagged one session. The same-session estimate therefore *flatters* the published Sharpe statistics of the only credible candidate in the repository. A related numerical artefact was documented: the published walk-forward's minimum fold OOS Sharpe (**-21.829879**) comes from a near-flat 242-session segment and alone moves the headline walk-forward mean (0.947307 with it, 1.431928 without it).

### Objective
Make the same-session volatility estimate **correctable behind a default-off, opt-in switch** and **re-derive the incumbent's published record on the corrected path in a NEW artifact**, so that remediation (adopt / do not adopt / adopt only for new live records) can be decided on evidence rather than on an unquantified defect. The default path must stay bit-identical; the published record must not be overwritten.

### Acceptance criteria
1. **Fail-closed reproduction anchor.** Before publishing anything, reproduce the incumbent's published artefacts on the **default** path exactly as they are committed (48-fold walk-forward mean OOS Sharpe **0.947307**, and the committed paper-trading record's 450 sessions bit-identically) and fail closed on any mismatch.
2. **Opt-in switch, default off.** The corrected estimate (volatility computed from data up to and including session *t-1*) is reachable only through an explicit opt-in parameter/switch whose default value reproduces today's behaviour exactly. The default path must be **bit-identical** (max |diff| = 0.0) to the pre-change path on net returns, combined weights, the published walk-forward fold table and the committed paper-trading record. No existing call site may change behaviour.
3. **Read-only with respect to `data/` and `config/`.** `config/promotion_gates.yaml`, `config/paper_trading_config.yaml`, `config/simulation_candidate_001.yaml` and everything under `data/` must remain byte-identical (SHA-256 before/after). The switch's default value must not be set through a config-file edit in this cycle.
4. **Re-derivation on the corrected path, in NEW artifacts only.** Re-derive the incumbent's published walk-forward record and the committed paper-trading record's key statistics on the corrected path and publish them side by side with the current published values: 48-fold walk-forward mean/median/std/min OOS Sharpe (with and without the numerical-artefact fold), the record's canonical Sharpe, the trailing 63-session Sharpe, the `rolling_63d_sharpe` gate value, and the PSR against the fixed backtest-baseline Sharpe **1.4178** (the repository's own bootstrap settings: `n_bootstrap=1000`, `block_size=22`, `seed=20240101`). The published record itself (`research/experiments/tsmomentum_regime_filter_wf_001.md`) and the committed paper-trading state must **not** be overwritten.
5. **Blast radius and decision.** Publish an explicit inventory of every code path and every committed artefact that depends on the same-session estimate, and a **decision recommendation** with its evidence: adopt the fix everywhere / adopt only for new live paper-trading records / do not adopt (with the reason). If the recommendation is "adopt", state precisely which artefacts would then need re-derivation and in which order — as a plan, not as an execution.
6. **Honest accounting of what the defect does and does not change.** State explicitly that the defect does **not** cause the `rolling_63d_sharpe` failure (the corrected failing window is *worse*), does not rescue the incumbent's promotion decision (the PSR gate still fails on the corrected path), and does not change the incumbent's published verdict in this cycle. Do not let the re-derivation be reported as an edge, a recovery or a promotion.
7. **Evidence artifacts and tests.** A new report under `research/reports/` and a new experiment record under `research/experiments/` documenting the anchor, the switch's semantics, the side-by-side re-derivation, the blast-radius inventory, the decision and the reproduction commands; plus tests that pin the default-path bit-identity, the opt-in behaviour, the anchor reproduction and the read-only guarantee.
8. **No scope creep.** No gate, threshold, universe, cost model, Sharpe convention, hypothesis or drift-flag change; no candidate selection, re-fit or re-ranking; no live trading, no scheduled job, no new dependency; the fetcher is never called.

### Scope boundaries
- `src/` may be touched **only** to add the default-off opt-in switch and its tests; the default behaviour of every existing call site must not change.
- `data/` and `config/` are read-only.
- New files under `research/reports/` and `research/experiments/` may be written; existing committed records may not be overwritten.
- Do not re-derive the paper-trading state, the published walk-forward record, the shortlist scores or the promotion decision in this cycle — the task is to make the correction *possible and measured*, not to adopt it.

### Validation commands
```bash
python research/tsmomentum_rolling63_weakness_diagnosis.py --no-report   # Cycle 925 anchor still reproduces
python -m pytest -q tests/test_tsmomentum_rolling63_weakness_diagnosis.py
python -m pytest -q tests/test_tsmomentum_same_session_vol_correction.py   # new test file for this cycle
python -m pytest -q
git status --porcelain data/ config/
git diff --stat src/
```

### Evidence artifacts
- New report under `research/reports/` and new experiment record under `research/experiments/` for Cycle 926.
- A side-by-side table: published (default path) vs corrected path, for the walk-forward fold table, the paper-trading record statistics, the `rolling_63d_sharpe` gate value and the PSR.
- The blast-radius inventory (code paths, committed artefacts, re-derivation order if adopted).
- The decision recommendation with the evidence behind it, and the reproduction commands with their observed outputs.
