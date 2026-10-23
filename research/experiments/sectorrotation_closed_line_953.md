# Sector Rotation C4 — Closed Line Determination (Cycle 953)

## Determination
C4 (sector rotation across 9 GICS sector ETFs) matches the already closed
`sectorrotation_001` / `sectorrotation_002` hypothesis line. Both pre-register
the identical construction: 9-ETF universe (XLB,XLE,XLF,XLI,XLK,XLP,XLU,XLV,XLY),
12m/1m momentum, 18-config robustness grid (3 lookbacks x 2 skips x 3 top
fractions), 1/N + incumbent benchmarks, 3bps round-trip, monthly rebalance,
36 walk-forward folds, identical promotion gates. No new hypothesis ID warranted.

## References
- research/hypotheses/sectorrotation_001.md
- research/hypotheses/sectorrotation_002.md
- research/experiments/sectorrotation_002_experiment_001.md

## Next
Remaining shortlist exploratory candidates are data-blocked or already rejected.
Next cycle to choose between a bounded incumbent improvement experiment or a
documented data/infrastructure task.
