# Cycle 932 — Independent-sample significance of riskparity_001 excess over 1/N

## Context

Cycle 931 placed 1/N, riskparity_001 and the incumbent on the same 41 point-in-time-complete folds.
riskparity_001's excess over 1/N is +0.039267 with a moving-block
bootstrap 95% CI [0.006458, 0.079121]
that excludes zero, while the incumbent's excess has a CI that includes zero. The 41 folds overlap
(12-month test on a 6-month step), so the CI is on a serially dependent fold set, not independent samples.

## Objective

Recompute the riskparity_001 vs 1/N excess on a non-overlapping annual subset of the same
point-in-time-complete window and report whether the significance survives; no parameter search,
no new candidate.

## Method

- **Window**: same point-in-time-complete window as Cycle 931 (2006-02-15 .. 2026-05-28)
- **Folds**: selected non-overlapping annual subset from the 41 complete folds (even folds 8,10,12,...,48)
- **Design**: same walk-forward design, same cost model (3.0 bp per unit), same 1/N benchmark
- **Bootstrap**: moving block bootstrap on paired fold differences, block = max(2, n_folds//8), seed = 20240101

## Results

- **Number of folds in annual subset**: 21
- **riskparity_001 excess over 1/N**: 0.038820
- **95% CI (2000 draws)**: [-0.001639, 0.082736]
- **95% CI (1000 draws)**: [-0.000496, 0.081935]
- **Excludes zero**: False
- **Block size**: 2

### Selected folds

| Fold | Test window | riskparity_001 Sharpe | 1/N Sharpe | Excess |
|---|---|---|---|---|
| 8 | 2006-02-15 .. 2007-02-01 | 0.897270 | 0.952281 | -0.055012 |
| 10 | 2007-02-02 .. 2008-01-21 | 0.285352 | 0.190607 | 0.094745 |
| 12 | 2008-01-22 .. 2009-01-07 | -0.684195 | -0.726202 | 0.042007 |
| 14 | 2009-01-08 .. 2009-12-25 | 1.314210 | 1.274604 | 0.039607 |
| 16 | 2009-12-28 .. 2010-12-14 | 1.108746 | 0.899242 | 0.209504 |
| 18 | 2010-12-15 .. 2011-12-01 | 0.336886 | 0.120351 | 0.216535 |
| 20 | 2011-12-02 .. 2012-11-19 | 0.445680 | 0.477550 | -0.031870 |
| 22 | 2012-11-20 .. 2013-11-06 | 0.816447 | 0.801045 | 0.015402 |
| 24 | 2013-11-07 .. 2014-10-24 | 0.443794 | 0.321712 | 0.122082 |
| 26 | 2014-10-27 .. 2015-10-13 | -0.144129 | -0.240017 | 0.095888 |
| 28 | 2015-10-14 .. 2016-09-29 | 0.675498 | 0.623616 | 0.051882 |
| 30 | 2016-09-30 .. 2017-09-18 | 1.543610 | 1.520896 | 0.022714 |
| 32 | 2017-09-19 .. 2018-09-05 | 0.260431 | 0.298686 | -0.038255 |
| 34 | 2018-09-06 .. 2019-08-23 | 0.157943 | 0.045145 | 0.112797 |
| 36 | 2019-08-26 .. 2020-08-11 | 0.844472 | 0.831146 | 0.013327 |
| 38 | 2020-08-12 .. 2021-07-29 | 1.360544 | 1.467381 | -0.106837 |
| 40 | 2021-07-30 .. 2022-07-18 | -1.522262 | -1.421259 | -0.101003 |
| 42 | 2022-07-19 .. 2023-07-05 | 0.573063 | 0.557607 | 0.015456 |
| 44 | 2023-07-06 .. 2024-06-21 | 1.189931 | 1.023244 | 0.166687 |
| 46 | 2024-06-24 .. 2025-06-10 | 0.722728 | 0.770649 | -0.047921 |
| 48 | 2025-06-11 .. 2026-05-28 | 2.076500 | 2.099011 | -0.022511 |

## Conclusion

**Significance does not survive.** On the non-overlapping annual subset (21 folds),
riskparity_001's excess over 1/N is 0.038820 with 95% CI [-0.001639, 0.082736]
including zero.

## Validation

```bash
python research/mechanism_comparison_001.py
python research/annual_subset_riskparity_vs_oneoverN_932.py
git status --porcelain data/ config/
```

## Notes

- `data/` and `config/` byte-identical (read-only).
- No parameter search, no new candidate.
- Bootstrap uses same seed 20240101 as Cycle 929/930.