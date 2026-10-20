# PSR Continuation Horizon (Cycle 865)

Read-only, canonical convention (arithmetic annualized, rf=0).
Baseline n=450, mean=0.00067394, std=0.006041, sharpe=1.771084, psr=0.695606, se=0.690271.

| r_future | N | n_total | sharpe | se | psr |
|---|---|---|---|---|---|
| 0.00066578 | 0 | 450 | 1.771084 | 0.690271 | 0.695606 |
| 0.00066578 | 30 | 480 | 1.827910 | 0.694358 | 0.722616 |
| 0.00066578 | 63 | 513 | 1.888445 | 0.661582 | 0.761580 |
| 0.00066578 | 126 | 576 | 1.998929 | 0.669530 | 0.807294 |
| 0.00066578 | 252 | 702 | 2.203344 | 0.622480 | 0.896518 |
| 0.00066578 | 504 | 954 | 2.563740 | 0.569562 | 0.977888 |
| 0.00097217 | 0 | 450 | 1.771084 | 0.690271 | 0.695606 |
| 0.00097217 | 30 | 480 | 1.879744 | 0.696153 | 0.746516 |
| 0.00097217 | 63 | 513 | 1.993737 | 0.666945 | 0.806081 |
| 0.00097217 | 126 | 576 | 2.197662 | 0.689983 | 0.870817 |
| 0.00097217 | 252 | 702 | 2.563372 | 0.668075 | 0.956803 |
| 0.00097217 | 504 | 954 | 3.181409 | 0.656591 | 0.996384 |

- r_future=0.00066578: min N in grid with PSR>=0.95: 504
- r_future=0.00097217: min N in grid with PSR>=0.95: 252

SE decline alone cannot reach PSR>=0.95 at current observed Sharpe 1.771084 < target-scale 1.4178? Note: observed sharpe on canonical scale vs sr_target 1.4178; max PSR at SE floor is 0 if observed sharpe < sr_target, else 1. Here observed 1.771084 > 1.4178, so as SE->0 PSR->1; but SE floor not reachable at plausible N (see grid).

Gate interactions: rolling 63d sharpe and max DD remain separate promotion gates; continuation at record mean does not address trailing-63-session underperformance documented in Cycle 862.
