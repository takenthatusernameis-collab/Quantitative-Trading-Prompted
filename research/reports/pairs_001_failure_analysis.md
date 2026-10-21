# Report: `pairs_001` failure analysis (pairs_001_failure_analysis)

**Cycle 937.** Read-only, deterministic post-mortem. No files under `data/` or `config/` were modified; frozen artifacts remain unchanged.

## 1) Per-pair attribution
| Pair | Net excess annualized | Sharpe | Trades |
|---|---|---|---|
| XLP/XLU | 0.009094 | 0.179750 | 226 |
| XLF/XLK | -0.026539 | -0.314578 | 205 |
| XLE/XLB | -0.032287 | -0.408004 | 211 |
| XLI/XLB | -0.019626 | -0.451870 | 228 |
| XLV/XLY | -0.028693 | -0.439405 | 201 |
| XLK/XLU | -0.038723 | -0.452537 | 194 |

## 2) Cointegration failure summary
| Pair | Train windows | Cointegrated | Fails? | Min p | Max p |
|---|---|---|---|---|---|
| XLP/XLU | 36 | 14 | True | 0.001032 | 0.990904 |
| XLF/XLK | 36 | 4 | True | 0.000193 | 1.000000 |
| XLE/XLB | 36 | 1 | True | 0.022739 | 0.992559 |
| XLI/XLB | 36 | 7 | True | 0.002240 | 0.871773 |
| XLV/XLY | 36 | 11 | True | 0.000992 | 0.555322 |
| XLK/XLU | 36 | 10 | True | 0.001517 | 0.813088 |

## 3) Cost breakdown
- Turnover: 68.6916 units/yr; turnover cost drag: 0.000600%/yr
- Borrow: 20.3271%/yr (pre-registered 25 bp per unit short notional per rebalance)
- Total drag: 20.3277%/yr
- Gross before borrow: 6.6497%/yr; Net after borrow: -13.6774%/yr

## 4) Fired pre-registered conditions
- (i) >= 0.9: observed -0.829067 → **FIRED**
- (iii) no pair fails: observed any pair failed → **FIRED**
- (iv) > 0: observed -0.136774 → **FIRED**
- (ii) excludes zero: observed [-1.219160, -0.467513] → not fired

## 5) Concrete hypothesis about failure mechanism
The strategy's gross edge is small relative to the pre-registered borrow assumption and the spread reversion assumption is not cointegrated reliably across training windows; both effects are necessary to explain the negative net out-of-sample performance. Specifically, borrow drag dominates (net turns negative despite modest gross), and cointegration failure on many windows violates condition (iii).

## 6) Reproduction
```bash
python research/pairs_001_failure_analysis.py
python -m pytest -q tests/test_pairs_001_failure_analysis.py
git status --porcelain data/ config/
```
