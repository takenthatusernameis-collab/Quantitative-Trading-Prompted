# NEXT_AGENT_TASK.md

## Cycle 909 — Apply the non-overlapping (embargoed) fold sensitivity to `sectorrotation_001` and publish the delta against its published protocol

### Context

Cycle 908 implemented a read-only sensitivity tool `research/csmomentum_walkforward_embargo_audit.py` that evaluates three fold designs (published design, Design A with non-overlapping test windows, Design B with literal embargo) for `csmomentum_001`. The published **Rejected/Failed** verdict survived Design A (union sample: 48 folds → 24 folds; WF mean OOS Sharpe 0.6975 → 0.6983; gate-1 still fails), with Design A producing zero overlap and disjoint count equal to fold count.

The published protocol-level question noted in Cycle 908 is sharpest where the candidate sits close to a gate. `research/reports/sectorrotation_long_sample_feasibility_001.md` reports `sectorrotation_001` with walk-forward mean OOS Sharpe **0.847243** against its gate **>= 0.9**, a margin of **0.0528** (much smaller than `csmomentum_001`'s 0.2025). The published record shows 36 folds under its pre-registered design. This margin means removing fold overlap could plausibly shift the mean by a non-trivial amount relative to the threshold; measuring it is a protocol-level sensitivity (not a candidate re-optimization).

### Objective

Quantify how much of `sectorrotation_001`'s walk-forward evidence survives a non-overlapping (embargoed) fold design, publish the delta against its published protocol, and state whether the published gate outcome (on the same pre-registered scale) changes under Design A. Do this as a **read-only sensitivity** — do not change the published protocol, do not modify any committed artifact, do not change gates/thresholds/universe/cost model/parameters.

### Acceptance criteria

1. **New tool** `research/sectorrotation_walkforward_embargo_audit.py` (read-only w.r.t. `data/`, `config/`, committed artifacts) that:
- Reuses the same machinery patterns as `research/csmomentum_walkforward_embargo_audit.py` (config-faithful path reuse where applicable, policy/committed-cache consumption approach; must not call the fetcher, only committed parquet cache). If the candidate’s evaluation is defined in its own config/report, consume those definitions as-is (do not infer new ones).
- For `sectorrotation_001`, implement three designs over the same continuously computed point-in-time path used in its published walk-forward:
  - Published design (reference, as published)
  - Design A (non-overlapping test windows): step = test window length (so consecutive test windows share no session)
  - Design B (literal embargo, informational): next training window starts after previous test end + configured embargo days; if insufficient folds to form a stable gate table, publish fold count and state gate table not forced
- Publish per design: fold count, fold table (train/test windows, OOS Sharpe), WF mean/median OOS Sharpe, positive fold rate, pooled OOS trades, independence diagnostic (mean consecutive test-window overlap in days, max number of pairwise-disjoint test windows). Design A must show overlap 0.0 and disjoint count == fold count.
- Report the delta (published vs Design A): fold count, mean OOS Sharpe, gate-1 margin relative to its published threshold (>= 0.9). State explicitly whether the gate outcome changes under Design A.
- **Reproduction anchor**: must reproduce the published walk-forward numbers for `sectorrotation_001` on its published design within tolerance of the last published decimal (e.g. WF mean OOS Sharpe ~0.847243). If reproduction requires extracting published values from the committed report, do it deterministically.
- Fails closed if any required inputs missing/malformed; nothing under `data/` or `config/` written.

2. **Artifacts**:
- Write `research/reports/sectorrotation_walkforward_embargo_001.md` (deterministic)
- Write `research/experiments/sectorrotation_walkforward_embargo_001.md` (experiment record with hypothesis ref, data, config, splits, metrics, independence, reproduction commands)
- Do **not** modify any committed artifact.

3. **Tests** `tests/test_sectorrotation_walkforward_embargo_audit.py` with checks:
- Anchor reproduces published design (within published-decimal tolerance)
- Design A test windows pairwise disjoint and published design has overlap > 0
- `data/` and `config/` byte-identical before and after run
- Committed artifacts byte-identical before and after run (including those related to sectorrotation published record)
- Two consecutive runs produce identical report and experiment record (bit-for-bit deterministic)
- Fails closed on malformed/missing required config (where applicable)

4. **Verification commands** (must all pass):
```
python research/sectorrotation_walkforward_embargo_audit.py   # OVERALL: PASS, exit 0
python -m pytest -q tests/test_sectorrotation_walkforward_embargo_audit.py
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
- If Design A changes the gate outcome, report the difference and stop there (do not change the protocol/decision)
- Extend to other candidates only if this is complete and passing; this cycle focuses on `sectorrotation_001` as specified
- Keep deterministic, no timestamps in report/experiment files

### Notes
This directly tests the protocol-level independence question surfaced in Cycle 908, on the candidate with the smallest margin to its published threshold (0.847243 vs >= 0.9). The task requires building the new tool modeled after the csmomentum one but targeting `sectorrotation_001`'s published definitions.
