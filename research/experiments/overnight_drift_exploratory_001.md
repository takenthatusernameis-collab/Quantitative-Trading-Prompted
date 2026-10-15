# Overnight Drift Exploratory Diagnostic

**Status: EXPLORATORY DIAGNOSTIC ONLY — NO ALPHA CLAIMS**

This report characterizes the overnight/intraday return decomposition across
the available ETF universe using daily OHLCV data. It does not claim a tradable
edge. All results are subject to the limitations disclosed at the end of this report.

---

## 1. Data Inventory

| Symbol | Asset Class | Rows | Date Range |
|--------|-------------|------|------------|
| SPY | ETF | 8484 | 1993-02-01 to 2026-10-14 |
| QQQ | ETF | 6942 | 1999-03-11 to 2026-10-14 |
| IWM | ETF | 6634 | 2000-05-30 to 2026-10-14 |
| TLT | ETF | 6091 | 2002-07-31 to 2026-10-14 |
| GLD | ETF | 5509 | 2004-11-19 to 2026-10-14 |
| DBC | ETF | 5200 | 2006-02-07 to 2026-10-08 |
| VNQ | ETF | 5541 | 2004-09-30 to 2026-10-08 |
| EFA | ETF | 6319 | 2001-08-28 to 2026-10-14 |
| EEM | ETF | 5913 | 2003-04-15 to 2026-10-14 |
| XLB | ETF | 6990 | 1998-12-23 to 2026-10-08 |
| XLE | ETF | 6990 | 1998-12-23 to 2026-10-08 |
| XLF | ETF | 6990 | 1998-12-23 to 2026-10-08 |
| XLI | ETF | 6990 | 1998-12-23 to 2026-10-08 |
| XLK | ETF | 6990 | 1998-12-23 to 2026-10-08 |
| XLP | ETF | 6990 | 1998-12-23 to 2026-10-08 |
| XLU | ETF | 6990 | 1998-12-23 to 2026-10-08 |
| XLV | ETF | 6990 | 1998-12-23 to 2026-10-08 |
| XLY | ETF | 6990 | 1998-12-23 to 2026-10-08 |
| ^VIX | Index (Non-tradeable) | 8505 | 1993-01-05 to 2026-10-14 |

## 2. Per-Symbol Session Return Decomposition (Full History)

### Annualized Statistics

| Symbol | Session | Ann. Mean | Ann. Std | Ann. Sharpe | t-stat | p-value | N |
|--------|---------|-----------|----------|-------------|--------|---------|---|
| SPY | Overnight | 8.37% | 10.59% | 0.790 | 4.59 | 0.0000 | 8484 |
| SPY | Intraday | 1.85% | 15.16% | 0.122 | 0.71 | 0.4792 | 8484 |
| SPY | Total | 10.23% | 18.56% | 0.551 | 3.20 | 0.0014 | 8484 |
| QQQ | Overnight | 13.40% | 14.27% | 0.939 | 4.93 | 0.0000 | 6942 |
| QQQ | Intraday | -0.09% | 23.01% | -0.004 | -0.02 | 0.9838 | 6942 |
| QQQ | Total | 13.26% | 26.88% | 0.493 | 2.59 | 0.0097 | 6942 |
| IWM | Overnight | 12.14% | 13.25% | 0.916 | 4.70 | 0.0000 | 6634 |
| IWM | Intraday | -2.48% | 20.07% | -0.123 | -0.63 | 0.5266 | 6634 |
| IWM | Total | 9.61% | 23.83% | 0.403 | 2.07 | 0.0385 | 6634 |
| TLT | Overnight | -2.65% | 9.84% | -0.269 | -1.32 | 0.1860 | 6091 |
| TLT | Intraday | 3.51% | 10.16% | 0.346 | 1.70 | 0.0894 | 6091 |
| TLT | Total | 0.89% | 14.29% | 0.062 | 0.30 | 0.7607 | 6091 |
| GLD | Overnight | 10.96% | 13.07% | 0.839 | 3.92 | 0.0001 | 5509 |
| GLD | Intraday | 0.41% | 12.15% | 0.033 | 0.16 | 0.8759 | 5509 |
| GLD | Total | 11.45% | 18.27% | 0.627 | 2.93 | 0.0034 | 5509 |
| DBC | Overnight | 4.17% | 13.64% | 0.305 | 1.39 | 0.1655 | 5200 |
| DBC | Intraday | -0.72% | 14.27% | -0.051 | -0.23 | 0.8181 | 5200 |
| DBC | Total | 3.38% | 19.42% | 0.174 | 0.79 | 0.4289 | 5200 |
| VNQ | Overnight | 10.81% | 12.73% | 0.849 | 3.98 | 0.0001 | 5541 |
| VNQ | Intraday | -4.35% | 24.49% | -0.177 | -0.83 | 0.4053 | 5541 |
| VNQ | Total | 6.67% | 28.31% | 0.236 | 1.11 | 0.2692 | 5541 |
| EFA | Overnight | -0.64% | 15.71% | -0.040 | -0.20 | 0.8396 | 6319 |
| EFA | Intraday | 6.25% | 13.29% | 0.470 | 2.36 | 0.0185 | 6319 |
| EFA | Total | 5.66% | 20.83% | 0.272 | 1.36 | 0.1736 | 6319 |
| EEM | Overnight | 10.35% | 18.63% | 0.555 | 2.69 | 0.0072 | 5913 |
| EEM | Intraday | 0.38% | 17.59% | 0.022 | 0.11 | 0.9160 | 5913 |
| EEM | Total | 11.11% | 27.11% | 0.410 | 1.99 | 0.0472 | 5913 |
| XLB | Overnight | 8.12% | 13.51% | 0.601 | 3.16 | 0.0016 | 6990 |
| XLB | Intraday | 0.29% | 19.38% | 0.015 | 0.08 | 0.9371 | 6990 |
| XLB | Total | 8.38% | 23.55% | 0.356 | 1.87 | 0.0610 | 6990 |
| XLE | Overnight | 10.82% | 16.26% | 0.665 | 3.50 | 0.0005 | 6990 |
| XLE | Intraday | -0.65% | 22.83% | -0.029 | -0.15 | 0.8803 | 6990 |
| XLE | Total | 10.33% | 28.59% | 0.361 | 1.90 | 0.0572 | 6990 |
| XLF | Overnight | 8.45% | 17.09% | 0.494 | 2.60 | 0.0093 | 6990 |
| XLF | Intraday | -0.54% | 23.08% | -0.023 | -0.12 | 0.9022 | 6990 |
| XLF | Total | 7.76% | 28.19% | 0.275 | 1.45 | 0.1471 | 6990 |
| XLI | Overnight | 10.59% | 12.96% | 0.817 | 4.30 | 0.0000 | 6990 |
| XLI | Intraday | -1.13% | 17.21% | -0.066 | -0.35 | 0.7295 | 6990 |
| XLI | Total | 9.36% | 21.07% | 0.444 | 2.34 | 0.0194 | 6990 |
| XLK | Overnight | 14.30% | 16.02% | 0.893 | 4.70 | 0.0000 | 6990 |
| XLK | Intraday | -1.65% | 21.45% | -0.077 | -0.41 | 0.6855 | 6990 |
| XLK | Total | 12.43% | 26.01% | 0.478 | 2.52 | 0.0118 | 6990 |
| XLP | Overnight | 3.40% | 9.44% | 0.360 | 1.90 | 0.0577 | 6990 |
| XLP | Intraday | 2.09% | 13.51% | 0.155 | 0.82 | 0.4146 | 6990 |
| XLP | Total | 5.30% | 15.27% | 0.347 | 1.83 | 0.0676 | 6990 |
| XLU | Overnight | 10.87% | 9.96% | 1.092 | 5.75 | 0.0000 | 6990 |
| XLU | Intraday | -5.22% | 17.34% | -0.301 | -1.58 | 0.1131 | 6990 |
| XLU | Total | 5.51% | 19.27% | 0.286 | 1.51 | 0.1323 | 6990 |
| XLV | Overnight | 7.26% | 10.64% | 0.682 | 3.59 | 0.0003 | 6990 |
| XLV | Intraday | 1.36% | 15.40% | 0.088 | 0.47 | 0.6412 | 6990 |
| XLV | Total | 8.46% | 17.86% | 0.474 | 2.50 | 0.0126 | 6990 |
| XLY | Overnight | 8.48% | 14.05% | 0.604 | 3.18 | 0.0015 | 6990 |
| XLY | Intraday | 2.16% | 19.08% | 0.113 | 0.60 | 0.5515 | 6990 |
| XLY | Total | 10.40% | 22.65% | 0.459 | 2.42 | 0.0156 | 6990 |
| ^VIX | Overnight | 155.17% | 66.94% | 2.318 | 13.47 | 0.0000 | 8505 |
| ^VIX | Intraday | -85.98% | 98.60% | -0.872 | -5.07 | 0.0000 | 8505 |
| ^VIX | Total | 61.77% | 114.17% | 0.541 | 3.14 | 0.0017 | 8505 |

### Cumulative Log Returns (Full History)

| Symbol | Cum. Overnight | Cum. Intraday | Cum. Total |
|--------|----------------|---------------|------------|
| SPY | 2.6275 | 0.2356 | 2.8631 |
| QQQ | 3.4103 | -0.7518 | 2.6586 |
| IWM | 2.9638 | -1.1828 | 1.7810 |
| TLT | -0.7564 | 0.7236 | -0.0328 |
| GLD | 2.2092 | -0.0725 | 2.1368 |
| DBC | 0.6670 | -0.3596 | 0.3074 |
| VNQ | 2.1986 | -1.6151 | 0.5835 |
| EFA | -0.4704 | 1.3454 | 0.8750 |
| EEM | 2.0198 | -0.2727 | 1.7471 |
| XLB | 1.9942 | -0.4400 | 1.5542 |
| XLE | 2.6297 | -0.9054 | 1.7242 |
| XLF | 1.9392 | -0.8871 | 1.0521 |
| XLI | 2.7035 | -0.7249 | 1.9787 |
| XLK | 3.6069 | -1.0938 | 2.5131 |
| XLP | 0.8197 | 0.3270 | 1.1467 |
| XLU | 2.8778 | -1.8648 | 1.0130 |
| XLV | 1.8559 | 0.0488 | 1.9048 |
| XLY | 2.0778 | 0.0938 | 2.1716 |
| ^VIX | 44.8895 | -44.6562 | 0.2333 |

### Overnight Share of Total Return

| Symbol | Mean Share | Median Share | Std Share |
|--------|------------|--------------|-----------|
| SPY | 33.89% | 29.29% | 575.39% |
| QQQ | 40.72% | 26.78% | 837.77% |
| IWM | 34.22% | 23.17% | 531.67% |
| TLT | 60.71% | 50.00% | 505.45% |
| GLD | 47.88% | 57.14% | 468.31% |
| DBC | 50.08% | 45.00% | 257.65% |
| VNQ | 10.44% | 18.18% | 447.02% |
| EFA | 58.37% | 60.79% | 451.51% |
| EEM | 51.18% | 54.35% | 358.07% |
| XLB | 31.83% | 27.59% | 332.29% |
| XLE | 26.49% | 27.96% | 493.35% |
| XLF | 31.69% | 29.63% | 303.02% |
| XLI | 29.54% | 30.43% | 486.90% |
| XLK | 37.52% | 30.00% | 566.67% |
| XLP | 25.23% | 22.73% | 323.40% |
| XLU | 22.21% | 16.67% | 337.45% |
| XLV | 29.21% | 24.85% | 389.40% |
| XLY | 29.58% | 28.81% | 455.71% |
| ^VIX | 33.10% | 23.90% | 660.08% |

### Statistical Tests: Overnight vs Intraday

| Symbol | Paired t-stat (Ov vs In) | p-value | Binomial: Ov > In % | p-value | Binomial: Ov > 0 % | p-value |
|--------|--------------------------|---------|---------------------|---------|--------------------|---------|
| SPY | 2.05 | 0.0403 | 51.40% | 0.0101 | 54.92% | 0.0000 |
| QQQ | 2.60 | 0.0094 | 51.25% | 0.0379 | 55.11% | 0.0000 |
| IWM | 3.09 | 0.0020 | 51.40% | 0.0231 | 54.60% | 0.0000 |
| TLT | -2.16 | 0.0306 | 47.32% | 0.0000 | 48.86% | 0.0770 |
| GLD | 2.84 | 0.0045 | 52.91% | 0.0000 | 53.59% | 0.0000 |
| DBC | 1.11 | 0.2681 | 51.38% | 0.0474 | 50.90% | 0.1972 |
| VNQ | 2.65 | 0.0081 | 51.31% | 0.0530 | 55.62% | 0.0000 |
| EFA | -1.69 | 0.0902 | 50.93% | 0.1445 | 51.69% | 0.0076 |
| EEM | 2.00 | 0.0453 | 52.95% | 0.0000 | 54.02% | 0.0000 |
| XLB | 1.74 | 0.0827 | 51.59% | 0.0082 | 52.72% | 0.0000 |
| XLE | 2.20 | 0.0278 | 51.53% | 0.0108 | 53.15% | 0.0000 |
| XLF | 1.62 | 0.1054 | 51.93% | 0.0013 | 51.75% | 0.0037 |
| XLI | 2.80 | 0.0051 | 52.13% | 0.0004 | 53.03% | 0.0000 |
| XLK | 3.05 | 0.0023 | 52.26% | 0.0002 | 53.72% | 0.0000 |
| XLP | 0.39 | 0.6951 | 50.86% | 0.1546 | 50.52% | 0.3958 |
| XLU | 4.09 | 0.0000 | 51.59% | 0.0082 | 53.32% | 0.0000 |
| XLV | 1.59 | 0.1121 | 51.50% | 0.0124 | 53.22% | 0.0000 |
| XLY | 1.35 | 0.1774 | 51.47% | 0.0142 | 53.08% | 0.0000 |
| ^VIX | 11.22 | 0.0000 | 59.32% | 0.0000 | 54.32% | 0.0000 |

## 3. Sub-Period Stability Analysis

### Pre-2008 (1993-01-01 to 2007-12-31)

| Symbol | Session | Ann. Mean | Ann. Sharpe | t-stat | p-value | N |
|--------|---------|-----------|-------------|--------|---------|---|
| SPY | Overnight | 11.23% | 1.323 | 5.11 | 0.0000 | 3758 |
| SPY | Intraday | -1.65% | -0.109 | -0.42 | 0.6738 | 3758 |
| SPY | Total | 9.50% | 0.561 | 2.17 | 0.0304 | 3758 |
| QQQ | Overnight | 19.32% | 1.179 | 3.50 | 0.0005 | 2216 |
| QQQ | Intraday | -13.13% | -0.423 | -1.25 | 0.2103 | 2216 |
| QQQ | Total | 5.98% | 0.173 | 0.51 | 0.6079 | 2216 |
| IWM | Overnight | 16.36% | 1.591 | 4.38 | 0.0000 | 1908 |
| IWM | Intraday | -7.24% | -0.372 | -1.02 | 0.3061 | 1908 |
| IWM | Total | 8.97% | 0.420 | 1.16 | 0.2476 | 1908 |
| TLT | Overnight | -1.10% | -0.169 | -0.39 | 0.6950 | 1365 |
| TLT | Intraday | 4.04% | 0.527 | 1.23 | 0.2205 | 1365 |
| TLT | Total | 2.97% | 0.289 | 0.67 | 0.5017 | 1365 |
| GLD | Overnight | 16.98% | 1.405 | 2.48 | 0.0135 | 783 |
| GLD | Intraday | 4.53% | 0.350 | 0.62 | 0.5371 | 783 |
| GLD | Total | 21.67% | 1.170 | 2.06 | 0.0396 | 783 |
| DBC | Overnight | 6.37% | 0.463 | 0.64 | 0.5240 | 478 |
| DBC | Intraday | 10.04% | 0.587 | 0.81 | 0.4194 | 478 |
| DBC | Total | 15.77% | 0.838 | 1.15 | 0.2491 | 478 |
| VNQ | Overnight | 26.95% | 3.092 | 5.57 | 0.0000 | 819 |
| VNQ | Intraday | -18.53% | -1.046 | -1.88 | 0.0598 | 819 |
| VNQ | Total | 8.44% | 0.423 | 0.76 | 0.4462 | 819 |
| EFA | Overnight | 9.24% | 0.689 | 1.73 | 0.0835 | 1593 |
| EFA | Intraday | 1.95% | 0.164 | 0.41 | 0.6797 | 1593 |
| EFA | Total | 11.12% | 0.635 | 1.60 | 0.1107 | 1593 |
| EEM | Overnight | 45.75% | 3.272 | 7.10 | 0.0000 | 1187 |
| EEM | Intraday | -11.29% | -0.617 | -1.34 | 0.1811 | 1187 |
| EEM | Total | 34.76% | 1.425 | 3.09 | 0.0020 | 1187 |
| XLB | Overnight | 13.22% | 1.176 | 3.53 | 0.0004 | 2268 |
| XLB | Intraday | -2.81% | -0.138 | -0.41 | 0.6784 | 2268 |
| XLB | Total | 10.37% | 0.449 | 1.35 | 0.1777 | 2268 |
| XLE | Overnight | 17.78% | 1.543 | 4.63 | 0.0000 | 2268 |
| XLE | Intraday | -1.14% | -0.053 | -0.16 | 0.8738 | 2268 |
| XLE | Total | 16.60% | 0.682 | 2.05 | 0.0409 | 2268 |
| XLF | Overnight | 9.86% | 0.698 | 2.09 | 0.0364 | 2268 |
| XLF | Intraday | -4.41% | -0.218 | -0.65 | 0.5138 | 2268 |
| XLF | Total | 5.10% | 0.219 | 0.66 | 0.5110 | 2268 |
| XLI | Overnight | 14.48% | 1.258 | 3.77 | 0.0002 | 2268 |
| XLI | Intraday | -6.47% | -0.366 | -1.10 | 0.2726 | 2268 |
| XLI | Total | 7.70% | 0.393 | 1.18 | 0.2386 | 2268 |
| XLK | Overnight | 21.53% | 1.181 | 3.54 | 0.0004 | 2268 |
| XLK | Intraday | -18.53% | -0.713 | -2.14 | 0.0325 | 2268 |
| XLK | Total | 2.51% | 0.083 | 0.25 | 0.8034 | 2268 |
| XLP | Overnight | 5.61% | 0.595 | 1.79 | 0.0742 | 2268 |
| XLP | Intraday | -3.15% | -0.213 | -0.64 | 0.5234 | 2268 |
| XLP | Total | 2.24% | 0.138 | 0.41 | 0.6789 | 2268 |
| XLU | Overnight | 26.06% | 2.408 | 7.22 | 0.0000 | 2268 |
| XLU | Intraday | -19.80% | -1.056 | -3.17 | 0.0015 | 2268 |
| XLU | Total | 5.78% | 0.297 | 0.89 | 0.3724 | 2268 |
| XLV | Overnight | 11.90% | 1.022 | 3.06 | 0.0022 | 2268 |
| XLV | Intraday | -5.99% | -0.357 | -1.07 | 0.2848 | 2268 |
| XLV | Total | 5.57% | 0.298 | 0.89 | 0.3720 | 2268 |
| XLY | Overnight | 4.27% | 0.326 | 0.98 | 0.3286 | 2268 |
| XLY | Intraday | 1.15% | 0.061 | 0.18 | 0.8554 | 2268 |
| XLY | Total | 5.22% | 0.236 | 0.71 | 0.4789 | 2268 |
| ^VIX | Overnight | 74.56% | 1.180 | 4.57 | 0.0000 | 3777 |
| ^VIX | Intraday | -19.54% | -0.242 | -0.94 | 0.3480 | 3777 |
| ^VIX | Total | 44.70% | 0.485 | 1.88 | 0.0604 | 3777 |

### 2008-2020 (2008-01-01 to 2019-12-31)

| Symbol | Session | Ann. Mean | Ann. Sharpe | t-stat | p-value | N |
|--------|---------|-----------|-------------|--------|---------|---|
| SPY | Overnight | 4.81% | 0.427 | 1.48 | 0.1390 | 3021 |
| SPY | Intraday | 3.59% | 0.233 | 0.81 | 0.4190 | 3021 |
| SPY | Total | 8.50% | 0.434 | 1.50 | 0.1330 | 3021 |
| QQQ | Overnight | 9.63% | 0.826 | 2.86 | 0.0043 | 3021 |
| QQQ | Intraday | 4.44% | 0.255 | 0.88 | 0.3768 | 3021 |
| QQQ | Total | 14.06% | 0.672 | 2.33 | 0.0200 | 3021 |
| IWM | Overnight | 7.34% | 0.580 | 2.01 | 0.0446 | 3021 |
| IWM | Intraday | 2.11% | 0.102 | 0.35 | 0.7239 | 3021 |
| IWM | Total | 9.44% | 0.391 | 1.35 | 0.1763 | 3021 |
| TLT | Overnight | -0.45% | -0.046 | -0.16 | 0.8724 | 3021 |
| TLT | Intraday | 4.58% | 0.442 | 1.53 | 0.1259 | 3021 |
| TLT | Total | 4.19% | 0.288 | 1.00 | 0.3185 | 3021 |
| GLD | Overnight | 6.08% | 0.479 | 1.66 | 0.0970 | 3021 |
| GLD | Intraday | 0.09% | 0.007 | 0.02 | 0.9802 | 3021 |
| GLD | Total | 6.22% | 0.344 | 1.19 | 0.2331 | 3021 |
| DBC | Overnight | 1.02% | 0.080 | 0.28 | 0.7814 | 3021 |
| DBC | Intraday | -4.85% | -0.335 | -1.16 | 0.2468 | 3021 |
| DBC | Total | -3.83% | -0.199 | -0.69 | 0.4907 | 3021 |
| VNQ | Overnight | 9.14% | 0.676 | 2.34 | 0.0192 | 3021 |
| VNQ | Intraday | -0.63% | -0.022 | -0.08 | 0.9397 | 3021 |
| VNQ | Total | 8.70% | 0.268 | 0.93 | 0.3533 | 3021 |
| EFA | Overnight | -6.63% | -0.397 | -1.38 | 0.1692 | 3021 |
| EFA | Intraday | 8.13% | 0.546 | 1.89 | 0.0590 | 3021 |
| EFA | Total | 1.65% | 0.071 | 0.25 | 0.8046 | 3021 |
| EEM | Overnight | 1.00% | 0.050 | 0.17 | 0.8614 | 3021 |
| EEM | Intraday | 1.99% | 0.101 | 0.35 | 0.7267 | 3021 |
| EEM | Total | 3.63% | 0.120 | 0.41 | 0.6783 | 3021 |
| XLB | Overnight | 6.46% | 0.472 | 1.63 | 0.1022 | 3021 |
| XLB | Intraday | -0.33% | -0.017 | -0.06 | 0.9539 | 3021 |
| XLB | Total | 6.18% | 0.255 | 0.88 | 0.3781 | 3021 |
| XLE | Overnight | 2.86% | 0.187 | 0.65 | 0.5165 | 3021 |
| XLE | Intraday | -1.43% | -0.063 | -0.22 | 0.8274 | 3021 |
| XLE | Total | 1.72% | 0.061 | 0.21 | 0.8337 | 3021 |
| XLF | Overnight | 8.50% | 0.447 | 1.55 | 0.1216 | 3021 |
| XLF | Intraday | -0.67% | -0.024 | -0.08 | 0.9329 | 3021 |
| XLF | Total | 7.73% | 0.233 | 0.81 | 0.4194 | 3021 |
| XLI | Overnight | 7.15% | 0.547 | 1.89 | 0.0582 | 3021 |
| XLI | Intraday | 1.36% | 0.077 | 0.27 | 0.7886 | 3021 |
| XLI | Total | 8.43% | 0.392 | 1.36 | 0.1752 | 3021 |
| XLK | Overnight | 9.80% | 0.774 | 2.68 | 0.0074 | 3021 |
| XLK | Intraday | 2.84% | 0.163 | 0.56 | 0.5734 | 3021 |
| XLK | Total | 12.50% | 0.596 | 2.06 | 0.0391 | 3021 |
| XLP | Overnight | 3.79% | 0.401 | 1.39 | 0.1655 | 3021 |
| XLP | Intraday | 3.98% | 0.317 | 1.10 | 0.2729 | 3021 |
| XLP | Total | 7.49% | 0.541 | 1.87 | 0.0612 | 3021 |
| XLU | Overnight | 0.73% | 0.083 | 0.29 | 0.7750 | 3021 |
| XLU | Intraday | 4.42% | 0.282 | 0.98 | 0.3294 | 3021 |
| XLU | Total | 5.08% | 0.288 | 1.00 | 0.3187 | 3021 |
| XLV | Overnight | 7.26% | 0.749 | 2.59 | 0.0096 | 3021 |
| XLV | Intraday | 3.16% | 0.212 | 0.73 | 0.4631 | 3021 |
| XLV | Total | 10.30% | 0.603 | 2.09 | 0.0370 | 3021 |
| XLY | Overnight | 11.43% | 0.870 | 3.01 | 0.0026 | 3021 |
| XLY | Intraday | 2.49% | 0.130 | 0.45 | 0.6531 | 3021 |
| XLY | Total | 13.54% | 0.629 | 2.18 | 0.0296 | 3021 |
| ^VIX | Overnight | 169.59% | 2.447 | 8.47 | 0.0000 | 3021 |
| ^VIX | Intraday | -97.21% | -0.919 | -3.18 | 0.0015 | 3021 |
| ^VIX | Total | 70.63% | 0.556 | 1.92 | 0.0544 | 3021 |

### 2020+ (2020-01-01 to 2026-12-31)

| Symbol | Session | Ann. Mean | Ann. Sharpe | t-stat | p-value | N |
|--------|---------|-----------|-------------|--------|---------|---|
| SPY | Overnight | 8.37% | 0.634 | 1.65 | 0.0995 | 1705 |
| SPY | Intraday | 6.48% | 0.439 | 1.14 | 0.2533 | 1705 |
| SPY | Total | 14.90% | 0.743 | 1.93 | 0.0534 | 1705 |
| QQQ | Overnight | 12.40% | 0.802 | 2.09 | 0.0372 | 1705 |
| QQQ | Intraday | 8.84% | 0.463 | 1.20 | 0.2289 | 1705 |
| QQQ | Total | 21.29% | 0.859 | 2.23 | 0.0256 | 1705 |
| IWM | Overnight | 15.91% | 0.950 | 2.47 | 0.0136 | 1705 |
| IWM | Intraday | -5.28% | -0.269 | -0.70 | 0.4845 | 1705 |
| IWM | Total | 10.65% | 0.412 | 1.07 | 0.2837 | 1705 |
| TLT | Overnight | -7.79% | -0.639 | -1.66 | 0.0965 | 1705 |
| TLT | Intraday | 1.20% | 0.104 | 0.27 | 0.7864 | 1705 |
| TLT | Total | -6.64% | -0.405 | -1.05 | 0.2928 | 1705 |
| GLD | Overnight | 16.84% | 1.194 | 3.10 | 0.0019 | 1705 |
| GLD | Intraday | -0.93% | -0.084 | -0.22 | 0.8267 | 1705 |
| GLD | Total | 16.03% | 0.865 | 2.25 | 0.0246 | 1705 |
| DBC | Overnight | 9.14% | 0.604 | 1.57 | 0.1169 | 1701 |
| DBC | Intraday | 3.58% | 0.277 | 0.72 | 0.4713 | 1701 |
| DBC | Total | 12.72% | 0.640 | 1.66 | 0.0963 | 1701 |
| VNQ | Overnight | 6.01% | 0.466 | 1.21 | 0.2264 | 1701 |
| VNQ | Intraday | -4.11% | -0.229 | -0.59 | 0.5528 | 1701 |
| VNQ | Total | 2.21% | 0.095 | 0.25 | 0.8060 | 1701 |
| EFA | Overnight | 0.77% | 0.048 | 0.13 | 0.8999 | 1705 |
| EFA | Intraday | 6.94% | 0.610 | 1.59 | 0.1130 | 1705 |
| EFA | Total | 7.67% | 0.397 | 1.03 | 0.3019 | 1705 |
| EEM | Overnight | 2.27% | 0.119 | 0.31 | 0.7576 | 1705 |
| EEM | Intraday | 5.65% | 0.464 | 1.21 | 0.2274 | 1705 |
| EEM | Total | 7.90% | 0.350 | 0.91 | 0.3627 | 1705 |
| XLB | Overnight | 4.25% | 0.269 | 0.70 | 0.4848 | 1701 |
| XLB | Intraday | 5.53% | 0.320 | 0.83 | 0.4056 | 1701 |
| XLB | Total | 9.63% | 0.421 | 1.09 | 0.2745 | 1701 |
| XLE | Overnight | 15.66% | 0.703 | 1.83 | 0.0678 | 1701 |
| XLE | Intraday | 1.38% | 0.056 | 0.15 | 0.8841 | 1701 |
| XLE | Total | 17.24% | 0.511 | 1.33 | 0.1841 | 1701 |
| XLF | Overnight | 6.48% | 0.378 | 0.98 | 0.3258 | 1701 |
| XLF | Intraday | 4.86% | 0.284 | 0.74 | 0.4601 | 1701 |
| XLF | Total | 11.37% | 0.467 | 1.21 | 0.2256 | 1701 |
| XLI | Overnight | 11.53% | 0.793 | 2.06 | 0.0395 | 1701 |
| XLI | Intraday | 1.58% | 0.098 | 0.26 | 0.7982 | 1701 |
| XLI | Total | 13.21% | 0.597 | 1.55 | 0.1210 | 1701 |
| XLK | Overnight | 12.66% | 0.701 | 1.82 | 0.0689 | 1701 |
| XLK | Intraday | 12.89% | 0.610 | 1.59 | 0.1130 | 1701 |
| XLK | Total | 25.55% | 0.917 | 2.38 | 0.0173 | 1701 |
| XLP | Overnight | -0.22% | -0.023 | -0.06 | 0.9527 | 1701 |
| XLP | Intraday | 5.72% | 0.429 | 1.12 | 0.2648 | 1701 |
| XLP | Total | 5.51% | 0.336 | 0.87 | 0.3824 | 1701 |
| XLU | Overnight | 8.65% | 0.818 | 2.13 | 0.0337 | 1701 |
| XLU | Intraday | -2.89% | -0.160 | -0.41 | 0.6784 | 1701 |
| XLU | Total | 5.91% | 0.272 | 0.71 | 0.4795 | 1701 |
| XLV | Overnight | 1.06% | 0.098 | 0.26 | 0.7987 | 1701 |
| XLV | Intraday | 7.97% | 0.560 | 1.45 | 0.1459 | 1701 |
| XLV | Total | 9.05% | 0.503 | 1.31 | 0.1916 | 1701 |
| XLY | Overnight | 8.87% | 0.534 | 1.39 | 0.1659 | 1701 |
| XLY | Intraday | 2.91% | 0.152 | 0.39 | 0.6929 | 1701 |
| XLY | Total | 11.72% | 0.467 | 1.21 | 0.2256 | 1701 |
| ^VIX | Overnight | 308.04% | 4.423 | 11.51 | 0.0000 | 1707 |
| ^VIX | Intraday | -213.13% | -1.790 | -4.66 | 0.0000 | 1707 |
| ^VIX | Total | 83.86% | 0.632 | 1.65 | 0.1001 | 1707 |

## 4. Cross-Asset Group Comparison (Full History)

| Group | Symbols | Session | Avg Ann. Mean | Avg Ann. Sharpe | Avg t-stat |
|-------|---------|---------|---------------|-----------------|------------|
| Equity (US Broad) | 3 | Overnight | 11.30% | 0.882 | 4.74 |
| Equity (US Broad) | 3 | Intraday | -0.24% | -0.002 | 0.02 |
| Equity (US Broad) | 3 | Total | 11.03% | 0.483 | 2.62 |
| Equity (Sectors) | 9 | Overnight | 9.14% | 0.690 | 3.63 |
| Equity (Sectors) | 9 | Intraday | -0.37% | -0.014 | -0.07 |
| Equity (Sectors) | 9 | Total | 8.66% | 0.387 | 2.04 |
| International | 2 | Overnight | 4.86% | 0.258 | 1.24 |
| International | 2 | Intraday | 3.32% | 0.246 | 1.23 |
| International | 2 | Total | 8.39% | 0.341 | 1.67 |
| Bonds | 1 | Overnight | -2.65% | -0.269 | -1.32 |
| Bonds | 1 | Intraday | 3.51% | 0.346 | 1.70 |
| Bonds | 1 | Total | 0.89% | 0.062 | 0.30 |
| Commodities | 2 | Overnight | 7.56% | 0.572 | 2.65 |
| Commodities | 2 | Intraday | -0.16% | -0.009 | -0.04 |
| Commodities | 2 | Total | 7.42% | 0.400 | 1.86 |
| REITs | 1 | Overnight | 10.81% | 0.849 | 3.98 |
| REITs | 1 | Intraday | -4.35% | -0.177 | -0.83 |
| REITs | 1 | Total | 6.67% | 0.236 | 1.11 |
| Volatility Index | 1 | Overnight | 155.17% | 2.318 | 13.47 |
| Volatility Index | 1 | Intraday | -85.98% | -0.872 | -5.07 |
| Volatility Index | 1 | Total | 61.77% | 0.541 | 3.14 |

## 5. Limitations and Bias Disclosures

**THIS IS AN EXPLORATORY DIAGNOSTIC ONLY. NO TRADABLE EDGE IS CLAIMED.**

The following limitations apply to all results above:

1. **Daily data only — no intraday execution prices**: We observe Open and Close but not the path between them. Actual execution prices for overnight positions (buying at prior close, selling at open) may differ from reported Open/Close due to bid-ask spreads, auction mechanics, and market-on-open orders.

2. **Bid-ask spreads not observed**: Yahoo Finance reports midpoint-like prices. Real overnight trading incurs spread costs (typically 1–10 bps for liquid ETFs, wider for sector/international ETFs).

3. **ETF survivorship bias**: The universe comprises currently-listed ETFs. Delisted or merged ETFs are not represented. This may overstate returns if failed funds had different session return profiles.

4. **No point-in-time universe membership**: The universe is fixed to currently available symbols. Historical universe composition (e.g., sector ETFs incepting in 1998) changes the cross-sectional properties over time.

5. **Dividend adjustments**: Yahoo Finance provides adjusted Close but Open/High/Low may not be consistently adjusted for dividends/splits, potentially biasing overnight returns on ex-dividend dates.

6. **^VIX is an index, not tradeable**: Included for reference only; VIX futures/ETFs have different session dynamics.

7. **Weekend/holiday effects**: Overnight return from Friday close to Monday open spans 3 calendar days; holiday periods span longer. Not separately modeled.

8. **Corporate actions**: Splits and dividends may create artifacts in the Open/Close relationship if not perfectly adjusted.

9. **Data source limitations**: yfinance data may have occasional errors, missing rows, or adjustments that differ from official exchange data.

10. **No cost model applied**: All returns are gross of any transaction costs, slippage, or financing. A realistic overnight capture strategy would need to overcome ~5–20 bps round-trip costs per cycle.

11. **Multiple testing not controlled**: This diagnostic examines 19 symbols × 3 sessions × 3 sub-periods = 171+ statistical tests without correction. Reported p-values are nominal.

---

## 6. Conclusion

This exploratory diagnostic provides a descriptive characterization of overnight vs. intraday
return decomposition across the available ETF universe. Any apparent statistical significance
should be interpreted with extreme caution given the limitations above, particularly the
absence of bid-ask spread data, the use of daily (not intraday) prices, and the lack of
multiple-testing correction.

**No investment decisions should be based on this analysis.** Further investigation would
require: (a) intraday tick/bar data with bid-ask spreads, (b) point-in-time universe
construction, (c) explicit cost modeling with realistic overnight execution assumptions,
and (d) out-of-sample validation on a disjoint dataset.
