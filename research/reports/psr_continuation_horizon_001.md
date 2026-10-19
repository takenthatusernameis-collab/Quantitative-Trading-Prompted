# PSR Continuation Horizon (Cycle 865)

Read-only, canonical convention (arithmetic annualized, rf=0).
Baseline n=449, mean=0.00066578, std=0.006045, sharpe=1.748401, psr=0.684041, se=0.690150.

| r_future | N | n_total | sharpe | se | psr |
|---|---|---|---|---|---|
| 0.00066578 | 0 | 449 | 1.748401 | 0.690150 | 0.684041 |
| 0.00066578 | 30 | 479 | 1.805993 | 0.695999 | 0.711492 |
| 0.00066578 | 63 | 512 | 1.867293 | 0.666988 | 0.749817 |
| 0.00066578 | 126 | 575 | 1.979055 | 0.666399 | 0.800168 |
| 0.00066578 | 252 | 701 | 2.185501 | 0.618842 | 0.892613 |
| 0.00066578 | 504 | 953 | 2.548709 | 0.567916 | 0.976778 |
| 0.00097217 | 0 | 449 | 1.748401 | 0.690150 | 0.684041 |
| 0.00097217 | 30 | 479 | 1.857896 | 0.695974 | 0.736419 |
| 0.00097217 | 63 | 512 | 1.972717 | 0.671497 | 0.795708 |
| 0.00097217 | 126 | 575 | 2.178015 | 0.685414 | 0.866314 |
| 0.00097217 | 252 | 701 | 2.545880 | 0.662672 | 0.955652 |
| 0.00097217 | 504 | 953 | 3.166854 | 0.653668 | 0.996272 |

- r_future=0.00066578: min N in grid with PSR>=0.95: 504
- r_future=0.00097217: min N in grid with PSR>=0.95: 252

SE decline alone cannot reach PSR>=0.95 at current observed Sharpe 1.748401 < target-scale 1.4178? Note: observed sharpe on canonical scale vs sr_target 1.4178; max PSR at SE floor is 0 if observed sharpe < sr_target, else 1. Here observed 1.748401 > 1.4178, so as SE->0 PSR->1; but SE floor not reachable at plausible N (see grid).

Gate interactions: rolling 63d sharpe and max DD remain separate promotion gates; continuation at record mean does not address trailing-63-session underperformance documented in Cycle 862.
