# Experiment: Walk-forward embargo sensitivity for `csmomentum_001` (csmomentum_walkforward_embargo_001, Cycle 908)

## Hypothesis reference
- Candidate hypothesis: `research/hypotheses/csmomentum_001.md`
- Frozen config: `config/csmomentum_candidate_001.yaml` (read, never changed)
- Sample policy: `config/sample_policy.yaml` (read, never changed)

## Objective
Quantify how much of `csmomentum_001`'s walk-forward evidence survives a non-overlapping (embargoed) fold design, publish delta against published protocol, and state whether the published Rejected/Failed verdict survives (sensitivity only).

## Data
- Source: committed raw cache `data/raw/*.parquet` (cache-only, fetcher never called)
- Universe: ['SPY', 'QQQ', 'IWM', 'TLT', 'GLD', 'DBC', 'VNQ', 'EFA', 'EEM', 'XLB', 'XLE', 'XLF', 'XLI', 'XLK', 'XLP', 'XLU', 'XLV', 'XLY']
- Common inception (re-derived): 2006-02-06
- Test end: 2026-10-09

## Configurations
Three fold designs over the same continuously computed point-in-time path, fixed parameters (no per-fold re-optimisation):
1. **Published design** (Cycle 907): 10y train / 12m test / 6m step, 21d purge, 21d embargo (generator as-is).
2. **Design A (non-overlapping test windows)**: step = test window length (12 months), all else unchanged.
3. **Design B (embargo applied literally)**: next training window starts after previous test window ends + 21d embargo (informational).

## Splits
- Published (union): 48 folds, overlap 175.0 days, disjoint 24
- Design A (union): 24 folds, overlap 0.0 days, disjoint 24
- Design B (union): 3 folds

## Results (union_sample)
- Published: WF mean OOS Sharpe 0.697524 (canonical 0.840389), median 0.617881, positive 79.17%, pooled trades 400, decision Rejected/Failed
- Design A: WF mean OOS Sharpe 0.698298 (canonical 0.843274), median 0.635245, positive 79.17%, pooled trades 199, decision Rejected/Failed
- Design B: folds 3, decision Inconclusive

## Independence diagnostic
| Design | union | common_inception_slice | common_inception_window |
|---|---|---|---|
| Published | 24 disjoint (48 folds, 175.0d overlap) | 11 disjoint | 11 disjoint |
| Design A | 24 disjoint (24 folds, 0.0d overlap) | 11 disjoint | 11 disjoint |
| Design B | 3 disjoint (3 folds) | 1 disjoint | 1 disjoint |

## Trial count
- 1 measurement per (design × sample) = 9 runs; no re-optimisation, fixed parameters.

## Reproduction
```bash
python research/csmomentum_walkforward_embargo_audit.py
python research/csmomentum_sample_gate_audit.py
python research/month_end_candidate_reaudit.py
python -m pytest -q tests/test_csmomentum_walkforward_embargo_audit.py
python -m pytest -q tests/test_csmomentum_sample_gate_audit.py
python -m pytest -q
git status --porcelain data/
```

