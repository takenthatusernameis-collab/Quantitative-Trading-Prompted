# Sectorrotation Walk-Forward Embargo Audit (sectorrotation_walkforward_embargo_001, Cycle 909)

- Candidate: sectorrotation_001
- Published WF mean OOS Sharpe: 0.847243 (published 0.847243) anchor=MATCH
- Design A folds: 18, mean 0.770297, overlap 0.0, disjoint 18
- Design B folds: 2

## Delta (published vs Design A)
- Fold count: 36 -> 18 (delta -18)
- WF mean OOS Sharpe: 0.847243 -> 0.770297
- Gate-1 margin (>=0.9): 0.052757 -> 0.129703
- Gate outcome changes under Design A: NO

## Checks
- anchor_reproduces_published: PASS
- design_a_disjoint: PASS
- published_has_overlap: PASS

OVERALL: PASS
