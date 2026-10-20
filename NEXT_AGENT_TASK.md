# NEXT_AGENT_TASK.md

## Cycle 910 — Apply the non-overlapping (embargoed) fold sensitivity to `tsmomentum_spytrend_001` (the incumbent) and publish the delta against its published protocol

### Context

Cycle 909 applied the read-only embargo-fold sensitivity to `sectorrotation_001` (published WF mean OOS Sharpe 0.847243 vs gate >= 0.9, rejected). Design A (non-overlapping test windows) dropped the mean to 0.770297 and the verdict survived (Rejected/Failed). The same sensitivity was applied to `csmomentum_001` in Cycle 908 (0.6975 -> 0.6983; verdict survived).

Both tested candidates were already rejected, so fold overlap never flipped a verdict. The decision-relevant case is the incumbent `tsmomentum_spytrend_001`, whose published walk-forward **passes** gate 1: `research/experiments/tsmomentum_regime_filter_wf_001.md` reports walk-forward Mean OOS Sharpe **0.9473** (>= 0.9 required), positive fold rate 91.7% (>= 0.5), 6013 pooled trades (> 100), all three validation gates met, "All three validation gates are met." Because the published mean sits only 0.0473 above the gate, removing fold overlap could plausibly shift it below 0.9 and flip the verdict from PASS to FAIL. Measuring this is a protocol-level sensitivity (not a candidate re-optimization).

### Objective

Quantify how much of `tsmomentum_spytrend_001`'s walk-forward evidence survives a non-overlapping (embargoed) fold design, publish the delta against its published protocol, and state whether the published gate outcome (on the same pre-registered scale) changes under Design A. Do this as a **read-only sensitivity** — do not change the published protocol, do not modify any committed artifact, do not change gates/thresholds/universe/cost model/parameters.

### Acceptance criteria

1. **New tool** `research/tsmomentum_walkforward_embargo_audit.py` (read-only w.r.t. `data/`, `config/`, committed artifacts) that:
   - Reuses the same machinery patterns as `research/sectorrotation_walkforward_embargo_audit.py` (config-faithful path reuse where applicable, policy/committed-cache consumption approach; must not call the fetcher, only committed parquet cache). If the candidate's evaluation is defined in its own config/report, consume those definitions as-is (do not infer new ones).
   - For `tsmomentum_spytrend_001`, implement three designs over the same continuously computed point-in-time path used in its published walk-forward:
     - Published design (reference, as published)
     - Design A (non-overlapping test windows): step = test window length (so consecutive test windows share no session)
     - Design B (literal embargo, informational): next training window starts after previous test end + configured embargo days; if insufficient folds to form a stable gate table, publish fold count and state gate table not forced
   - Publish per design: fold count, fold table (train/test windows, OOS Sharpe), WF mean/median OOS Sharpe, positive fold rate, pooled OOS trades, independence diagnostic (mean consecutive test-window overlap in days, max number of pairwise-disjoint test windows). Design A must show overlap 0.0 and disjoint count == fold count.
   - Report the delta (published vs Design A): fold count, mean OOS Sharpe, gate-1 margin relative to its published threshold (>= 0.9). State explicitly whether the gate outcome changes under Design A.
   - **Reproduction anchor**: must reproduce the published walk-forward mean OOS Sharpe for `tsmomentum_spytrend_001` on its published design within tolerance of the last published decimal (published WF mean OOS Sharpe ~0.9473). If reproduction requires extracting published values from the committed experiment record, do it deterministically.
   - Fails closed if any required inputs missing/malformed; nothing under `data/` or `config/` written.

2. **Artifacts**:
   - Write `research/reports/tsmomentum_walkforward_embargo_001.md` (deterministic)
   - Write `research/experiments/tsmomentum_walkforward_embargo_001.md` (experiment record with hypothesis ref, data, config, splits, metrics, independence, reproduction commands)
   - Do **not** modify any committed artifact.

3. **Tests** `tests/test_tsmomentum_walkforward_embargo_audit.py` with checks:
   - Anchor reproduces published design (within published-decimal tolerance)
   - Design A test windows pairwise disjoint and published design has overlap > 0
   - `data/` and `config/` byte-identical before and after run
   - Committed artifacts byte-identical before and after run (including those related to the incumbent published record)
   - Two consecutive runs produce identical report and experiment record (bit-for-bit deterministic)
   - Fails closed on malformed/missing required config (where applicable)

4. **Verification commands** (must all pass):
   ```
   python research/tsmomentum_walkforward_embargo_audit.py   # OVERALL: PASS, exit 0
   python -m pytest -q tests/test_tsmomentum_walkforward_embargo_audit.py
   python -m pytest -q
   git status --porcelain data/
   git diff --stat src/ config/ research/experiments/ research/reports/
   ```

### Scope boundaries
- Sensitivity only; do not change the published protocol or any committed record
- Do not change `src/evaluation/walkforward.py`
- Do not change gates/thresholds/universe/cost model/parameters/candidate configs
- No per-fold re-optimization, no execution of robustness grid
- Cache-only reads (no fetcher/network); read-only
- If Design A changes the gate outcome (PASS -> FAIL or FAIL -> PASS), report the difference and stop there (do not change the protocol/decision)
- Keep deterministic, no timestamps in report/experiment files

### Notes
This completes the embargo-fold sensitivity triad (csmomentum rejected -> survived; sectorrotation rejected -> survived; incumbent passes -> test whether overlap inflates the mean enough to flip the verdict). Published anchor: 0.9473 vs gate >= 0.9, margin 0.0473.
