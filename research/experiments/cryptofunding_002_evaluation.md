# Experiment: cryptofunding_002_evaluation — hardened net-of-cost evaluation (Cycle 891)

Hypothesis: `research/hypotheses/cryptofunding_001.md`

This record supersedes the Cycle 890 evaluation (`research/experiments/cryptofunding_002_evaluation.md`, previous revision), which annualized a 24/7 crypto series at 252 periods/year and never charged the entry or the exit of the funding-positive rule.

## Data used

| Item | Value |
|---|---|
| Source | Binance public archive (data.binance.vision), SHA256-verified |
| Universe | BTCUSDT perp, ETHUSDT perp |
| Range | 2020-01-02 .. 2026-09-30 (2464 daily rows per symbol) |
| Frequency | daily (UTC), 24/7 |
| Carry paths | `data/processed/crypto/{BTCUSDT,ETHUSDT}_carry_path.parquet` |
| Point-in-time treatment | Funding is attributed to the UTC day of its settlement timestamp and is never forward-filled; the funding-positive rule of this evaluation decides with the **previous** day's aggregate funding, the last information available before the trading day starts. |
| Identity check | `gross_carry == funding_cashflow + basis_convergence` holds row by row (max abs deviation 0.0e+00). |

The price legs come from a single venue (Binance). The OKX funding series collected in Cycle 888 is an independent cross-check of the funding *levels* (91.2% sign agreement on the overlap window), not an independent price path.

## Configuration

* **Annualization:** 365 periods/year (24/7 crypto). The cost screen's 252 is used only for the reconciliation below.
* **Cost model:** 3.0 bp per unit of weight change (repository flat model: 1.0 bp commission + 2.0 bp slippage); sensitivity rows at 1.5, 3.0, 4.5 bp.
* **Book:** one unit of equity running a delta-neutral carry pair, `+w` spot and `-w` perp (200% gross notional, zero net). Single-symbol books use `w = 1.0`; the BTC/ETH portfolio uses `w = 0.5` per symbol, the construction the cost screen screens.
* **Turnover:** the daily rebalance of the legs while the pair is held **plus** the position transitions: an entry (long spot + short perp) and an exit each change the leg weights by `2 * w` and are charged.
* **Metrics:** `src/backtest/engine.compute_metrics` (annualized return, volatility, Sharpe, Sortino, max drawdown, profit factor) and `src.evaluation.sharpe.sharpe_ratio` (the canonical `arithmetic_annualized_rf0` gate convention), both evaluated on the 365-day scale. Turnover and trade counts are supplied explicitly, because the engine's weight frame would net the two legs away.
* **Block bootstrap:** 2000 draws, 126-day blocks, seed 20261019 (pre-registered in Cycle 890).
* **Splits (pre-registered):**
  * `full`: 2020-01-02 .. 2026-09-30
  * `train`: 2020-01-02 .. 2022-12-31
  * `val`: 2023-01-01 .. 2024-12-31
  * `test_oos`: 2025-01-01 .. 2026-09-30
  * `post2022`: 2023-01-01 .. 2026-09-30
* **Trial count:** 6 candidate configurations (3 rules x 2 symbols); the BTC/ETH portfolio is an equal-weight combination of the two symbol books, not an additional configuration. The robustness rows are sensitivity analyses of the same configurations, not new trials.

## Rules evaluated

| Rule | Look-ahead | Note |
|---|---|---|
| `always_on` (Always-on carry) | no | Pre-registered rule 1. |
| `funding_positive_sameday` (Funding-positive only (same-day signal, pre-registered)) | yes | Pre-registered rule 2; the day's aggregate funding is only known after that day's settlements, so this variant is contaminated. Reported for reconciliation with Cycle 890 only. |
| `funding_positive_lagged` (Funding-positive only (previous-day signal, implementable)) | no | Pre-registered rule 2, defect-corrected: the decision uses the previous day's aggregate funding. |

## Results (net of costs, 365-day annualization)

### Portfolio (equal weight BTC/ETH)

| Rule | Sample | Sessions | Ann. net (geo) | Ann. net (arith) | Ann. vol | Sharpe (canonical) | Sharpe (backtest) | Sortino (canonical) | Sortino (backtest) | Max DD | Turnover/yr | Cost drag/yr | Entries | Rebalance days |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `always_on` | full | 2464 | +12.7694% | +12.0304% | +1.4788% | 8.135 | 7.282 | 9.296 | 8.321 | -1.7213% | 18.47 | +0.5540% | 2 | 2464 |
| `always_on` | train | 1095 | +20.3240% | +18.5281% | +2.0836% | 8.892 | 8.794 | 10.483 | 10.367 | -1.7213% | 23.50 | +0.7050% | 2 | 1095 |
| `always_on` | val | 731 | +10.2744% | +9.7836% | +0.6518% | 15.009 | 12.694 | 30.881 | 26.118 | -0.1039% | 14.04 | +0.4212% | 0 | 731 |
| `always_on` | test_oos | 638 | +3.5123% | +3.4527% | +0.3098% | 11.144 | 4.881 | 15.135 | 6.629 | -0.6535% | 14.90 | +0.4470% | 0 | 638 |
| `always_on` | post2022 | 1369 | +7.0697% | +6.8332% | +0.5466% | 12.501 | 9.275 | 25.534 | 18.945 | -0.6535% | 14.44 | +0.4332% | 0 | 1369 |
| `funding_positive_sameday` | full | 2464 | +11.3923% | +10.8002% | +1.4025% | 7.701 | 6.697 | 25.026 | 21.764 | -2.2058% | 96.79 | +2.9036% | 275 | 2414 |
| `funding_positive_sameday` | train | 1095 | +19.6502% | +17.9629% | +1.9144% | 9.383 | 9.220 | 35.355 | 34.740 | -1.3464% | 108.64 | +3.2593% | 135 | 1073 |
| `funding_positive_sameday` | val | 731 | +9.0468% | +8.6643% | +0.7170% | 12.084 | 9.828 | 22.604 | 18.384 | -0.6742% | 58.21 | +1.7463% | 45 | 728 |
| `funding_positive_sameday` | test_oos | 638 | +0.9577% | +0.9542% | +0.4478% | 2.131 | -2.327 | 3.020 | -3.299 | -2.2058% | 120.64 | +3.6193% | 95 | 613 |
| `funding_positive_sameday` | post2022 | 1369 | +5.1994% | +5.0711% | +0.6390% | 7.936 | 5.007 | 14.669 | 9.255 | -2.2058% | 87.31 | +2.6192% | 140 | 1341 |
| `funding_positive_lagged` | full | 2464 | +10.5340% | +10.0282% | +1.5202% | 6.597 | 5.614 | 9.302 | 7.916 | -2.6594% | 96.96 | +2.9088% | 275 | 2413 |
| `funding_positive_lagged` | train | 1095 | +18.0646% | +16.6322% | +2.1103% | 7.881 | 7.612 | 11.042 | 10.666 | -2.6050% | 108.93 | +3.2679% | 135 | 1072 |
| `funding_positive_lagged` | val | 731 | +8.7877% | +8.4264% | +0.7273% | 11.586 | 9.333 | 22.795 | 18.362 | -0.8010% | 58.21 | +1.7463% | 45 | 728 |
| `funding_positive_lagged` | test_oos | 638 | +0.5295% | +0.5292% | +0.4691% | 1.128 | -3.135 | 1.467 | -4.078 | -2.6594% | 120.81 | +3.6244% | 95 | 613 |
| `funding_positive_lagged` | post2022 | 1369 | +4.8579% | +4.7460% | +0.6537% | 7.261 | 4.372 | 13.039 | 7.851 | -2.6594% | 87.39 | +2.6216% | 140 | 1341 |

**The two metric scales are the same daily series under two conventions, and they are never compared silently.** The *canonical* Sharpe/Sortino are the repository's gate convention (`arithmetic_annualized_rf0`: the arithmetic mean daily return, annualized, with a zero risk-free rate). The *backtest* Sharpe/Sortino are the engine's published backtest baseline (`src/backtest/engine.py:compute_metrics`): the **geometric** annualized return minus the 2% risk-free rate, over the annualized volatility / downside deviation. A rule whose net return is below the 2% risk-free rate is therefore negative on the backtest scale while positive on the canonical scale - that is the convention, not a series mismatch, and it is why the promotion gate consumes the canonical scale only.

### Per symbol (leg weight 1.0)

| Book | Sample | Sessions | Ann. net (geo) | Sharpe (canonical) | Max DD | Turnover/yr | Entries | Exits |
|---|---|---|---|---|---|---|---|---|
| `BTCUSDT_always_on` | full | 2464 | +11.7554% | 8.257 | -2.4283% | 15.66 | 1 | 0 |
| `BTCUSDT_always_on` | test_oos | 638 | +3.9171% | 11.182 | -0.5262% | 11.62 | 0 | 0 |
| `BTCUSDT_always_on` | post2022 | 1369 | +7.0817% | 11.945 | -0.5262% | 12.35 | 0 | 0 |
| `ETHUSDT_always_on` | full | 2464 | +13.7888% | 7.207 | -1.9108% | 21.27 | 1 | 0 |
| `ETHUSDT_always_on` | test_oos | 638 | +3.1084% | 7.235 | -0.7927% | 18.18 | 0 | 0 |
| `ETHUSDT_always_on` | post2022 | 1369 | +7.0572% | 10.963 | -0.7927% | 16.53 | 0 | 0 |
| `BTCUSDT_funding_positive_sameday` | full | 2464 | +10.3042% | 7.414 | -2.2839% | 94.05 | 137 | 136 |
| `BTCUSDT_funding_positive_sameday` | test_oos | 638 | +1.6841% | 3.106 | -2.2839% | 101.14 | 40 | 40 |
| `BTCUSDT_funding_positive_sameday` | post2022 | 1369 | +5.2344% | 7.299 | -2.2839% | 82.40 | 67 | 67 |
| `ETHUSDT_funding_positive_sameday` | full | 2464 | +12.4876% | 7.014 | -2.6404% | 99.53 | 138 | 137 |
| `ETHUSDT_funding_positive_sameday` | test_oos | 638 | +0.2354% | 0.418 | -2.2407% | 140.15 | 55 | 55 |
| `ETHUSDT_funding_positive_sameday` | post2022 | 1369 | +5.1633% | 6.961 | -2.2407% | 92.22 | 73 | 73 |
| `BTCUSDT_funding_positive_lagged` | full | 2464 | +9.4966% | 6.452 | -2.5663% | 94.26 | 137 | 136 |
| `BTCUSDT_funding_positive_lagged` | test_oos | 638 | +1.3302% | 2.394 | -2.5663% | 101.33 | 40 | 40 |
| `BTCUSDT_funding_positive_lagged` | post2022 | 1369 | +4.9010% | 6.709 | -2.5663% | 82.47 | 67 | 67 |
| `ETHUSDT_funding_positive_lagged` | full | 2464 | +11.5775% | 6.019 | -4.1945% | 99.66 | 138 | 137 |
| `ETHUSDT_funding_positive_lagged` | test_oos | 638 | -0.2661% | -0.441 | -2.8554% | 140.30 | 55 | 55 |
| `ETHUSDT_funding_positive_lagged` | post2022 | 1369 | +4.8137% | 6.328 | -2.8554% | 92.30 | 73 | 73 |

### Benchmark (equal-weight BTC/ETH spot buy-and-hold)

| Sample | Sessions | Ann. return | Sharpe (canonical) | Max DD |
|---|---|---|---|---|
| full | 2464 | +53.9463% | 0.985 | -76.2537% |
| train | 1095 | +72.5240% | 1.089 | -76.2537% |
| val | 731 | +101.8785% | 1.653 | -35.4756% |
| test_oos | 638 | -7.1962% | 0.135 | -59.9292% |
| post2022 | 1369 | +40.5376% | 0.911 | -59.9292% |

## Block-bootstrap intervals (moving block, 126-day blocks, 2000 draws)

| Book | Sample | Sharpe 95% CI | Ann. net (geometric) 95% CI | Ann. net (arithmetic) 95% CI |
|---|---|---|---|---|
| `BTCUSDT_always_on` | full | [6.379, 10.895] | [+6.5785%, +18.5386%] | [+6.3789%, +17.0255%] |
| `BTCUSDT_always_on` | post2022 | [9.507, 14.064] | [+4.3850%, +10.5185%] | [+4.2926%, +10.0051%] |
| `BTCUSDT_always_on` | test_oos | [5.509, 14.723] | [+1.9156%, +5.0888%] | [+1.8980%, +4.9645%] |
| `ETHUSDT_always_on` | full | [5.197, 9.978] | [+6.7083%, +22.9116%] | [+6.4972%, +20.6601%] |
| `ETHUSDT_always_on` | post2022 | [7.646, 13.814] | [+4.0208%, +10.8729%] | [+3.9434%, +10.3258%] |
| `ETHUSDT_always_on` | test_oos | [2.706, 11.157] | [+1.2207%, +4.2087%] | [+1.2141%, +4.1234%] |
| `BTCUSDT_funding_positive_sameday` | full | [5.048, 9.629] | [+4.6935%, +17.1672%] | [+4.5898%, +15.8609%] |
| `BTCUSDT_funding_positive_sameday` | post2022 | [2.700, 11.044] | [+1.7558%, +9.1970%] | [+1.7425%, +8.8025%] |
| `BTCUSDT_funding_positive_sameday` | test_oos | [-2.949, 8.118] | [-1.7512%, +3.8850%] | [-1.7648%, +3.8126%] |
| `ETHUSDT_funding_positive_sameday` | full | [4.594, 9.349] | [+4.9199%, +21.8029%] | [+4.8078%, +19.7515%] |
| `ETHUSDT_funding_positive_sameday` | post2022 | [2.145, 11.233] | [+1.3702%, +9.5519%] | [+1.3627%, +9.1270%] |
| `ETHUSDT_funding_positive_sameday` | test_oos | [-4.469, 3.982] | [-2.6920%, +2.0485%] | [-2.7269%, +2.0291%] |
| `BTCUSDT_funding_positive_lagged` | full | [3.767, 9.094] | [+3.8741%, +16.4612%] | [+3.8057%, +15.2573%] |
| `BTCUSDT_funding_positive_lagged` | post2022 | [1.974, 10.690] | [+1.3138%, +8.9626%] | [+1.3074%, +8.5876%] |
| `BTCUSDT_funding_positive_lagged` | test_oos | [-3.881, 7.540] | [-2.3744%, +3.7047%] | [-2.4012%, +3.6390%] |
| `ETHUSDT_funding_positive_lagged` | full | [3.301, 8.852] | [+4.1845%, +20.7105%] | [+4.1040%, +18.8543%] |
| `ETHUSDT_funding_positive_lagged` | post2022 | [1.229, 10.882] | [+0.8025%, +9.3520%] | [+0.8013%, +8.9446%] |
| `ETHUSDT_funding_positive_lagged` | test_oos | [-5.681, 3.399] | [-3.5852%, +1.8378%] | [-3.6488%, +1.8225%] |

## Reconciliation with the cost screen

The screen (`research/cost_admissibility_screen.py`, row `cryptofunding_001`) screens the **same** series at the repository-wide 252 convention and without the position transitions. The screen's series and this evaluation's series are identical (gross identical: True, turnover identical: True), so the two rows describe the same candidate under two annualization conventions.

| Quantity | Screen (252) | This evaluation (365) |
|---|---|---|
| Annualized gross signal | +9.0672% | +13.3957% |
| Annual turnover (units/yr) | 12.55 | 18.17 |
| Cost drag at 3 bp/unit | +0.3764% | +0.5451% |
| Net annualized return at 3 bp/unit | +8.6576% | +12.7794% |
| Break-even cost per unit | 69.1853 bp | (invariant to the annualization convention) |

The screen's cost drag understates the crypto drag by the factor 365/252 = 1.452 and its gross signal understates the crypto gross signal by the same factor, so the **admissibility verdict is unaffected** (the break-even cost per unit is invariant).

## Robustness

### Cost sensitivity (portfolio)

| Rule | Cost/unit | Ann. net | Sharpe | Turnover/yr | Cost drag/yr |
|---|---|---|---|---|---|
| `always_on` | 1.5 bp | +13.0821% | 8.321 | 18.47 | +0.2770% |
| `always_on` | 3.0 bp | +12.7694% | 8.135 | 18.47 | +0.5540% |
| `always_on` | 4.5 bp | +12.4576% | 7.948 | 18.47 | +0.8310% |
| `funding_positive_sameday` | 1.5 bp | +13.0215% | 9.016 | 96.79 | +1.4518% |
| `funding_positive_sameday` | 3.0 bp | +11.3923% | 7.701 | 96.79 | +2.9036% |
| `funding_positive_sameday` | 4.5 bp | +9.7863% | 6.411 | 96.79 | +4.3554% |
| `funding_positive_lagged` | 1.5 bp | +12.1536% | 7.769 | 96.96 | +1.4544% |
| `funding_positive_lagged` | 3.0 bp | +10.5340% | 6.597 | 96.96 | +2.9088% |
| `funding_positive_lagged` | 4.5 bp | +8.9376% | 5.448 | 96.96 | +4.3632% |

### Turnover-convention sensitivity (portfolio, 3 bp/unit)

| Rule | Convention | Ann. net | Sharpe | Turnover/yr | Cost drag/yr |
|---|---|---|---|---|---|
| `always_on` | drift | +12.7694% | 8.135 | 18.47 | +0.5540% |
| `always_on` | parity | +13.3829% | 8.496 | 0.38 | +0.0113% |
| `always_on` | fixed_quantity | +13.3856% | 8.498 | 0.30 | +0.0089% |
| `funding_positive_sameday` | drift | +11.3923% | 7.701 | 96.79 | +2.9036% |
| `funding_positive_sameday` | parity | +11.9125% | 7.997 | 81.25 | +2.4375% |
| `funding_positive_sameday` | fixed_quantity | +11.9149% | 7.999 | 81.18 | +2.4353% |
| `funding_positive_lagged` | drift | +10.5340% | 6.597 | 96.96 | +2.9088% |
| `funding_positive_lagged` | parity | +11.0560% | 6.889 | 81.25 | +2.4375% |
| `funding_positive_lagged` | fixed_quantity | +11.0584% | 6.891 | 81.18 | +2.4353% |

* `drift`: Constant-notional rebalance of both legs every day (the cost screen's convention): w*(|spot_return| + |perp_return|) while the pair is held.
* `parity`: Equal-notional maintenance: only the basis drift is traded, w*|spot_return - perp_return| while the pair is held.
* `fixed_quantity`: Fixed coin quantity on both legs (no daily rebalancing at all): the pair is entered and exited only.

### Funding precision, rounding and settlement timing

* The archived 8h funding rates carry 8 decimals, so rounding them to the published precision is a no-op on the committed data.
* Worst-case per-settlement payment rounding: 5.475e-06 per year (0.054750 bp) - immaterial.
* Late entry (only the 08:00 and 16:00 UTC settlements captured): ann. net +8.2127%, Sharpe 6.845.

### Post-2022 and per-year stability (portfolio, 3 bp/unit)

| Rule | Year | Sessions | Ann. net | Sharpe | Max DD | Turnover/yr | Invested |
|---|---|---|---|---|---|---|---|
| `always_on` | 2020 | 365 | +22.8697% | 8.680 | -1.7213% | 23.60 | 1.000 |
| `always_on` | 2021 | 365 | +39.2556% | 14.095 | -0.2001% | 26.79 | 1.000 |
| `always_on` | 2022 | 365 | +1.8120% | 2.552 | -0.8699% | 20.11 | 1.000 |
| `always_on` | 2023 | 365 | +7.8445% | 14.583 | -0.0855% | 11.91 | 1.000 |
| `always_on` | 2024 | 366 | +12.7522% | 16.118 | -0.1039% | 16.16 | 1.000 |
| `always_on` | 2025 | 365 | +4.6366% | 15.150 | -0.1210% | 15.66 | 1.000 |
| `always_on` | 2026 | 273 | +2.0280% | 6.517 | -0.6535% | 13.89 | 1.000 |
| `funding_positive_sameday` | 2020 | 365 | +24.2622% | 11.524 | -0.3769% | 69.50 | 0.992 |
| `funding_positive_sameday` | 2021 | 365 | +38.6532% | 13.885 | -0.4476% | 66.63 | 0.975 |
| `funding_positive_sameday` | 2022 | 365 | -0.5805% | -1.032 | -1.3464% | 189.79 | 0.858 |
| `funding_positive_sameday` | 2023 | 365 | +6.2412% | 10.027 | -0.6742% | 69.21 | 0.981 |
| `funding_positive_sameday` | 2024 | 366 | +11.9185% | 14.225 | -0.6657% | 47.24 | 0.986 |
| `funding_positive_sameday` | 2025 | 365 | +2.3471% | 5.582 | -1.0415% | 98.09 | 0.981 |
| `funding_positive_sameday` | 2026 | 273 | -0.8704% | -1.852 | -2.2058% | 150.80 | 0.821 |
| `funding_positive_lagged` | 2020 | 365 | +21.9923% | 8.348 | -1.5888% | 69.78 | 0.989 |
| `funding_positive_lagged` | 2021 | 365 | +37.8163% | 13.469 | -0.6299% | 67.01 | 0.975 |
| `funding_positive_lagged` | 2022 | 365 | -2.1127% | -3.587 | -2.6050% | 190.00 | 0.858 |
| `funding_positive_lagged` | 2023 | 365 | +5.9098% | 9.296 | -0.7668% | 69.24 | 0.981 |
| `funding_positive_lagged` | 2024 | 366 | +11.7356% | 13.901 | -0.8010% | 47.21 | 0.986 |
| `funding_positive_lagged` | 2025 | 365 | +2.0986% | 4.851 | -1.2314% | 97.96 | 0.981 |
| `funding_positive_lagged` | 2026 | 273 | -1.5309% | -3.089 | -2.6594% | 151.37 | 0.821 |

### Capacity and liquidity

Daily quote volume of the traded legs (from the committed Binance klines) bounds the notional that can be rebalanced without moving the market:

| Symbol | Leg | Min daily quote volume | Median daily quote volume |
|---|---|---|---|
| BTCUSDT | spot | $121,214,452 | $1,711,652,906 |
| BTCUSDT | perp | $409,678,761 | $12,196,490,218 |
| ETHUSDT | spot | $18,952,319 | $927,024,812 |
| ETHUSDT | perp | $45,339,862 | $6,548,059,757 |

Indicative capacity (notional whose daily rebalance trade stays inside 1% of the leg's daily quote volume):

| Symbol | Convention | Median-day capacity | Worst-day capacity |
|---|---|---|---|
| BTCUSDT | drift | $406,585,254 | $28,793,226 |
| BTCUSDT | parity | $86,864,548,724 | $6,151,503,406 |
| ETHUSDT | drift | $161,309,089 | $3,297,842 |
| ETHUSDT | parity | $37,925,796,836 | $775,364,125 |

The **one-time entry** is the binding constraint for an always-on book (it never trades again except for the daily rebalance):

| Symbol | Leg | Entry capacity (median day) | Entry capacity (worst day) |
|---|---|---|---|
| BTCUSDT | spot | $17,116,529 | $1,212,145 |
| BTCUSDT | perp | $121,964,902 | $4,096,788 |
| ETHUSDT | spot | $9,270,248 | $189,523 |
| ETHUSDT | perp | $65,480,598 | $453,399 |

(1% of the daily quote volume of the traded leg; the capacity is the notional whose daily rebalance trade stays inside that budget. The one-time entry is bounded by the same 1% budget. The spot leg is the binding constraint for both symbols; the perp leg is deeper. The estimate ignores market impact beyond the participation budget, so it is an upper bound.)

**The capacity of this candidate is small**: at a 1% participation budget the one-time entry of an always-on BTC+ETH book is bounded by the spot leg at roughly $17,116,529 / $9,270,248 (median day) and by $1,212,145 / $189,523 (worst day) per symbol. A book larger than that either exceeds the participation budget or pays the market impact that the flat cost model does not capture.

### Return decomposition (funding vs basis)

| Symbol | Funding/yr | Funding vol/yr | Basis/yr | Basis vol/yr | Gross/yr | Gross vol/yr | Positive-funding days |
|---|---|---|---|---|---|---|---|
| BTCUSDT | +11.7310% | +1.1051% | -0.1361% | +0.6567% | +11.5949% | +1.3481% | 0.879 |
| ETHUSDT | +13.8421% | +1.4256% | -0.2682% | +0.9472% | +13.5740% | +1.7950% | 0.881 |

The edge is the **funding payment**: the basis convergence is a near zero-sum change of the price difference and contributes nothing to the annualized return, but it is the reason the daily volatility is small and the Sharpe is large. A strategy that harvests the funding is therefore exposed to the funding regime itself, not to a diversifiable spread.

### Sensitivity to the convergence assumption

| Rule | Gross with convergence/yr | Gross funding-only/yr | Funding-only Sharpe | Funding-only max DD |
|---|---|---|---|---|
| `always_on` | +12.7694% | +13.0014% | 10.003 | -0.8569% |
| `funding_positive_sameday` | +11.3923% | +10.9032% | 8.129 | -2.4275% |
| `funding_positive_lagged` | +10.5340% | +10.4471% | 7.692 | -3.0387% |

The basis-convergence term is a near zero-sum change of the price difference between the two legs; crediting it or not moves the annualized net return by well under one percentage point, so the result does not depend on that accounting.

## Promotion gates

| Rule | Net OOS Sharpe (canonical, 365) | Sharpe criterion | Pooled OOS round trips | Repo rebalance-day count | Settlement observations | Trade-count criterion | Gate |
|---|---|---|---|---|---|---|---|
| `always_on` | 9.209 | PASS | 0 | 1276 | 3828 | FAIL | **FAIL** |
| `funding_positive_sameday` | 1.762 | PASS | 95 | 1154 | 3828 | FAIL | **FAIL** |
| `funding_positive_lagged` | 0.977 | PASS | 95 | 1154 | 3828 | FAIL | **FAIL** |

The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.

## Verdict

**Exploratory signal — not promoted.** The carry is real and large net of the repository's cost model on every rule, symbol and sample, and it survives the post-2022 falsification condition, but the candidate is **not** promoted, for three measured reasons:

1. The pre-registered funding-positive rule is contaminated by a look-ahead (the same day's aggregate funding). The implementable variant, which also pays for its entries and exits, is materially weaker than the Cycle 890 record reported.
2. The Cycle 890 record reported `promotion_gate_pass: true` on a trade count that counted daily rebalances of a single position rather than independent round trips. On the honest count the trade criterion is not met.
3. The edge is venue-specific (Binance only), regime-dependent (2021 is the best year by a wide margin) and structurally exposed to the funding-positive regime that produced it: a long period of negative funding removes the return *and* adds trading costs.

The Sharpe criterion is met with a very large margin, so the candidate deserves one more validation cycle (independent venue, live-fee schedule, borrow/financing costs on the spot leg) before it is either promoted or rejected.

## Reproduction

```bash
python research/eval_cryptofunding.py
python -m pytest -q tests/test_eval_cryptofunding.py
python research/cost_admissibility_screen.py   # ends with OVERALL: PASS
python -m pytest -q
```

## Machine-readable summary

```json
{
  "benchmark_spot_buy_and_hold": {
    "full": {
      "ann_return_geometric": 0.5394633700231566,
      "max_drawdown": -0.7625369100009561,
      "sessions": 2464,
      "sharpe_canonical": 0.9851702128212253
    },
    "post2022": {
      "ann_return_geometric": 0.4053756919568816,
      "max_drawdown": -0.5992916086611823,
      "sessions": 1369,
      "sharpe_canonical": 0.9112844185488596
    },
    "test_oos": {
      "ann_return_geometric": -0.0719616606835457,
      "max_drawdown": -0.5992916086611817,
      "sessions": 638,
      "sharpe_canonical": 0.1349854549336388
    },
    "train": {
      "ann_return_geometric": 0.7252401177019854,
      "max_drawdown": -0.7625369100009561,
      "sessions": 1095,
      "sharpe_canonical": 1.0892522732919097
    },
    "val": {
      "ann_return_geometric": 1.0187846854157798,
      "max_drawdown": -0.35475567639624983,
      "sessions": 731,
      "sharpe_canonical": 1.6529042070382414
    }
  },
  "meta": {
    "bootstrap": {
      "block_days": 126,
      "draws": 2000,
      "seed": 20261019
    },
    "cost_model": {
      "commission_bps": 1.0,
      "decision_bps_per_unit": 3.0,
      "sensitivity_rows_bps": [
        1.5,
        3.0,
        4.5
      ],
      "slippage_bps": 2.0,
      "source": "src/backtest/engine.py:get_cost_params (config/settings.yaml)"
    },
    "data": {
      "carry_paths": "data/processed/crypto/{BTCUSDT,ETHUSDT}_carry_path.parquet",
      "end": "2026-09-30",
      "frequency": "daily (UTC), 24/7",
      "identity_max_deviation": {
        "BTCUSDT": 0.0,
        "ETHUSDT": 0.0
      },
      "rows": 2464,
      "source": "Binance public archive (data.binance.vision), SHA256-verified",
      "start": "2020-01-02",
      "universe": [
        "BTCUSDT perp",
        "ETHUSDT perp"
      ]
    },
    "generated_at": "2026-10-20T04:42:37.217803+00:00",
    "periods_per_year": 365,
    "promotion_gates": {
      "min_pooled_oos_trades": 100,
      "net_oos_sharpe_min": 0.9
    },
    "risk_free_rate_annual": 0.02,
    "screen_periods_per_year": 252,
    "splits": {
      "full": {
        "end": "2026-09-30",
        "start": "2020-01-02"
      },
      "post2022": {
        "end": "2026-09-30",
        "start": "2023-01-01"
      },
      "test_oos": {
        "end": "2026-09-30",
        "start": "2025-01-01"
      },
      "train": {
        "end": "2022-12-31",
        "start": "2020-01-02"
      },
      "val": {
        "end": "2024-12-31",
        "start": "2023-01-01"
      }
    },
    "trial_count": "6 candidate configurations (3 rules x 2 symbols); the BTC/ETH portfolio is an equal-weight combination of the two symbol books, not an additional configuration. The robustness rows are sensitivity analyses of the same configurations, not new trials."
  },
  "per_symbol": {
    "BTCUSDT_always_on": {
      "book": "BTCUSDT_always_on",
      "bootstrap": {
        "full": {
          "ann_return_arithmetic_ci_95": [
            0.0637889417779346,
            0.1702552220476289
          ],
          "ann_return_geometric_ci_95": [
            0.06578473192169848,
            0.1853861159606018
          ],
          "block_days": 126,
          "n_bootstrap": 2000,
          "seed": 20261019,
          "sharpe_ci_95": [
            6.379246317860291,
            10.8946615684123
          ]
        },
        "post2022": {
          "ann_return_arithmetic_ci_95": [
            0.04292640141897022,
            0.10005141464818959
          ],
          "ann_return_geometric_ci_95": [
            0.04384971830345279,
            0.10518531339718454
          ],
          "block_days": 126,
          "n_bootstrap": 2000,
          "seed": 20261019,
          "sharpe_ci_95": [
            9.50712864435186,
            14.064057081301321
          ]
        },
        "test_oos": {
          "ann_return_arithmetic_ci_95": [
            0.018980315580013372,
            0.04964526947320611
          ],
          "ann_return_geometric_ci_95": [
            0.019155631881375458,
            0.05088769307492557
          ],
          "block_days": 63,
          "n_bootstrap": 2000,
          "seed": 20261019,
          "sharpe_ci_95": [
            5.509349133169268,
            14.722798663033934
          ]
        }
      },
      "cost_bps_per_unit": 3.0,
      "cost_sensitivity": {
        "1.5bp": {
          "ann_return_arithmetic": 0.1135994491703378,
          "ann_return_geometric": 0.12018192247151727,
          "annualized_cost_drag": 0.0023493193084331908,
          "annualized_turnover_units": 15.66212872288794,
          "cost_bps_per_unit": 1.5,
          "max_drawdown": -0.02380446334331443,
          "sharpe_canonical": 8.42991181881716
        },
        "3.0bp": {
          "ann_return_arithmetic": 0.11125012986190459,
          "ann_return_geometric": 0.11755418977192233,
          "annualized_cost_drag": 0.0046986386168663815,
          "annualized_turnover_units": 15.66212872288794,
          "cost_bps_per_unit": 3.0,
          "max_drawdown": -0.024283209961711516,
          "sharpe_canonical": 8.257129360070175
        },
        "4.5bp": {
          "ann_return_arithmetic": 0.1089008105534714,
          "ann_return_geometric": 0.11493256881892,
          "annualized_cost_drag": 0.007047957925299573,
          "annualized_turnover_units": 15.66212872288794,
          "cost_bps_per_unit": 4.5,
          "max_drawdown": -0.024761732564029693,
          "sharpe_canonical": 8.082860405502338
        }
      },
      "entries_full_sample": 1,
      "exits_full_sample": 0,
      "leg_weight": 1.0,
      "look_ahead": false,
      "rule": "always_on",
      "rule_label": "Always-on carry",
      "samples": {
        "full": {
          "ann_return_arithmetic": 0.11125012986190459,
          "ann_return_geometric": 0.11755418977192233,
          "ann_volatility": 0.013473221141464483,
          "annualized_cost_drag": 0.0046986386168663815,
          "annualized_turnover_units": 15.66212872288794,
          "avg_gross_exposure": 2.0,
          "downside_deviation_annualized": 0.010459428920534206,
          "end": "2026-09-30",
          "invested_fraction": 1.0,
          "max_drawdown": -0.024283209961711516,
          "max_drawdown_recomputed": -0.024283209961711516,
          "position_entries": 1,
          "position_exits": 0,
          "profit_factor": 6.262746915172541,
          "rebalance_days": 2464,
          "risk_free_rate_annual": 0.02,
          "sample": "full",
          "sessions": 2464,
          "sharpe_backtest_scale": 7.240598869983262,
          "sharpe_canonical": 8.257129360070175,
          "sortino_backtest_scale": 9.32691359280635,
          "sortino_canonical": 10.636348380693676,
          "start": "2020-01-02",
          "total_return": 1.1176103478729904
        },
        "post2022": {
          "ann_return_arithmetic": 0.0684443715127791,
          "ann_return_geometric": 0.07081663052281706,
          "ann_volatility": 0.00572994538618933,
          "annualized_cost_drag": 0.0037048933173954943,
          "annualized_turnover_units": 12.349644391318316,
          "avg_gross_exposure": 2.0,
          "downside_deviation_annualized": 0.002353162093355494,
          "end": "2026-09-30",
          "invested_fraction": 1.0,
          "max_drawdown": -0.005261919452998809,
          "max_drawdown_recomputed": -0.005261919452998809,
          "position_entries": 0,
          "position_exits": 0,
          "profit_factor": 7.5298339222220525,
          "rebalance_days": 1369,
          "risk_free_rate_annual": 0.02,
          "sample": "post2022",
          "sessions": 1369,
          "sharpe_backtest_scale": 8.868606434766107,
          "sharpe_canonical": 11.945030344922305,
          "sortino_backtest_scale": 21.59504042084709,
          "sortino_canonical": 29.086127005887967,
          "start": "2023-01-01",
          "total_return": 0.2925638507151913
        },
        "test_oos": {
          "ann_return_arithmetic": 0.03843162146159495,
          "ann_return_geometric": 0.03917143888543295,
          "ann_volatility": 0.0034370386705364644,
          "annualized_cost_drag": 0.0034857383900040637,
          "annualized_turnover_units": 11.619127966680214,
          "avg_gross_exposure": 2.0,
          "downside_deviation_annualized": 0.0018935214198159596,
          "end": "2026-09-30",
          "invested_fraction": 1.0,
          "max_drawdown": -0.005261919452999364,
          "max_drawdown_recomputed": -0.005261919452999364,
          "position_entries": 0,
          "position_exits": 0,
          "profit_factor": 4.398940072782397,
          "rebalance_days": 638,
          "risk_free_rate_annual": 0.02,
          "sample": "test_oos",
          "sessions": 638,
          "sharpe_backtest_scale": 5.577894438540201,
          "sharpe_canonical": 11.181608688620432,
          "sortino_backtest_scale": 10.124754166919493,
          "sortino_canonical": 20.29637534564056,
          "start": "2025-01-01",
          "total_return": 0.06946928073889302
        },
        "train": {
          "ann_return_arithmetic": 0.16476710080250076,
          "ann_return_geometric": 0.17886664956942577,
          "ann_volatility": 0.018801460575792583,
          "annualized_cost_drag": 0.005941047123693452,
          "annualized_turnover_units": 19.803490412311508,
          "avg_gross_exposure": 2.0,
          "downside_deviation_annualized": 0.014435001055015034,
          "end": "2022-12-31",
          "invested_fraction": 1.0,
          "max_drawdown": -0.024283209961711516,
          "max_drawdown_recomputed": -0.024283209961711516,
          "position_entries": 1,
          "position_exits": 0,
          "profit_factor": 5.780938855878701,
          "rebalance_days": 1095,
          "risk_free_rate_annual": 0.02,
          "sample": "train",
          "sessions": 1095,
          "sharpe_backtest_scale": 8.44969724181807,
          "sharpe_canonical": 8.76352664934144,
          "sortino_backtest_scale": 11.005655556514979,
          "sortino_canonical": 11.414415570496761,
          "start": "2020-01-02",
          "total_return": 0.6383023141961586
        },
        "val": {
          "ann_return_arithmetic": 0.09463880999794395,
          "ann_return_geometric": 0.09922238527712546,
          "ann_volatility": 0.006868715578436114,
          "annualized_cost_drag": 0.0038961667013568263,
          "annualized_turnover_units": 12.987222337856089,
          "avg_gross_exposure": 2.0,
          "downside_deviation_annualized": 0.0027963440013734193,
          "end": "2024-12-31",
          "invested_fraction": 1.0,
          "max_drawdown": -0.0013521862122445327,
          "max_drawdown_recomputed": -0.0013521862122445327,
          "position_entries": 0,
          "position_exits": 0,
          "profit_factor": 10.694987943647144,
          "rebalance_days": 731,
          "risk_free_rate_annual": 0.02,
          "sample": "val",
          "sessions": 731,
          "sharpe_backtest_scale": 11.53379905929414,
          "sharpe_canonical": 13.778239747625646,
          "sortino_backtest_scale": 28.330700814426095,
          "sortino_canonical": 33.8437652704611,
          "start": "2023-01-01",
          "total_return": 0.2086030650849171
        }
      },
      "symbol": "BTCUSDT",
      "turnover_convention": "drift",
      "yearly": {
        "2020": {
          "ann_return_geometric": 0.17183381816627974,
          "annualized_turnover_units": 19.88704614669639,
          "invested_fraction": 1.0,
          "max_drawdown": -0.024283209961711516,
          "sessions": 365,
          "sharpe_canonical": 7.468793721628344
        },
        "2021": {
          "ann_return_geometric": 0.3485961427145625,
          "annualized_turnover_units": 22.988831132971345,
          "invested_fraction": 1.0,
          "max_drawdown": -0.005002241894988435,
          "sessions": 365,
          "sharpe_canonical": 13.758675658147203
        },
        "2022": {
          "ann_return_geometric": 0.03668330431758804,
          "annualized_turnover_units": 16.534593957266786,
          "invested_fraction": 1.0,
          "max_drawdown": -0.0043491997875151345,
          "sessions": 365,
          "sharpe_canonical": 5.618936919874762
        },
        "2023": {
          "ann_return_geometric": 0.0765855961371471,
          "annualized_turnover_units": 11.267851374575738,
          "invested_fraction": 1.0,
          "max_drawdown": -0.0009261337163611882,
          "sessions": 365,
          "sharpe_canonical": 13.672186362276294
        },
        "2024": {
          "ann_return_geometric": 0.12227133895958153,
          "annualized_turnover_units": 14.701895566264087,
          "invested_fraction": 1.0,
          "max_drawdown": -0.0013521862122449768,
          "sessions": 366,
          "sharpe_canonical": 14.549219587339726
        },
        "2025": {
          "ann_return_geometric": 0.04898121208398898,
          "annualized_turnover_units": 11.421737518470467,
          "invested_fraction": 1.0,
          "max_drawdown": -0.0008680757385995941,
          "sessions": 365,
          "sharpe_canonical": 13.969172250547341
        },
        "2026": {
          "ann_return_geometric": 0.026198977813723046,
          "annualized_turnover_units": 11.883038272894707,
          "invested_fraction": 1.0,
          "max_drawdown": -0.00526191945299892,
          "sessions": 273,
          "sharpe_canonical": 7.723022195986593
        }
      }
    },
    "BTCUSDT_funding_positive_lagged": {
      "book": "BTCUSDT_funding_positive_lagged",
      "bootstrap": {
        "full": {
          "ann_return_arithmetic_ci_95": [
            0.03805652314463654,
            0.15257302182862972
          ],
          "ann_return_geometric_ci_95": [
            0.038740948015404134,
            0.16461166940039842
          ],
          "block_days": 126,
          "n_bootstrap": 2000,
          "seed": 20261019,
          "sharpe_ci_95": [
            3.7673207806104165,
            9.093812051811463
          ]
        },
        "post2022": {
          "ann_return_arithmetic_ci_95": [
            0.013073902793162515,
            0.08587608864867835
          ],
          "ann_return_geometric_ci_95": [
            0.013138351477259558,
            0.08962567568335493
          ],
          "block_days": 126,
          "n_bootstrap": 2000,
          "seed": 20261019,
          "sharpe_ci_95": [
            1.974404584643905,
            10.690025015093113
          ]
        },
        "test_oos": {
          "ann_return_arithmetic_ci_95": [
            -0.024011941347810803,
            0.036389677953632335
          ],
          "ann_return_geometric_ci_95": [
            -0.02374434213043082,
            0.03704700079531041
          ],
          "block_days": 63,
          "n_bootstrap": 2000,
          "seed": 20261019,
          "sharpe_ci_95": [
            -3.8809040247058584,
            7.540430412126397
          ]
        }
      },
      "cost_bps_per_unit": 3.0,
      "cost_sensitivity": {
        "1.5bp": {
          "ann_return_arithmetic": 0.10497227055371566,
          "ann_return_geometric": 0.11056217961438364,
          "annualized_cost_drag": 0.014138616084045012,
          "annualized_turnover_units": 94.25744056030008,
          "cost_bps_per_unit": 1.5,
          "max_drawdown": -0.014698382591120107,
          "sharpe_canonical": 7.783097654361737
        },
        "3.0bp": {
          "ann_return_arithmetic": 0.09083365446967066,
          "ann_return_geometric": 0.09496606726132817,
          "annualized_cost_drag": 0.028277232168090024,
          "annualized_turnover_units": 94.25744056030008,
          "cost_bps_per_unit": 3.0,
          "max_drawdown": -0.025662769071929104,
          "sharpe_canonical": 6.451764131795484
        },
        "4.5bp": {
          "ann_return_arithmetic": 0.07669503838562564,
          "ann_return_geometric": 0.07958492166533304,
          "annualized_cost_drag": 0.042415848252135034,
          "annualized_turnover_units": 94.25744056030008,
          "cost_bps_per_unit": 4.5,
          "max_drawdown": -0.04007119417627114,
          "sharpe_canonical": 5.15978422596343
        }
      },
      "entries_full_sample": 137,
      "exits_full_sample": 136,
      "leg_weight": 1.0,
      "look_ahead": false,
      "rule": "funding_positive_lagged",
      "rule_label": "Funding-positive only (previous-day signal, implementable)",
      "samples": {
        "full": {
          "ann_return_arithmetic": 0.09083365446967066,
          "ann_return_geometric": 0.09496606726132817,
          "ann_volatility": 0.014078886427671102,
          "annualized_cost_drag": 0.028277232168090024,
          "annualized_turnover_units": 94.25744056030008,
          "avg_gross_exposure": 1.7564935064935066,
          "downside_deviation_annualized": 0.010019484705020225,
          "end": "2026-09-30",
          "invested_fraction": 0.8782467532467533,
          "max_drawdown": -0.025662769071929104,
          "max_drawdown_recomputed": -0.025662769071929104,
          "position_entries": 137,
          "position_exits": 136,
          "profit_factor": 3.5724683426595507,
          "rebalance_days": 2300,
          "risk_free_rate_annual": 0.02,
          "sample": "full",
          "sessions": 2464,
          "sharpe_backtest_scale": 5.324715675949158,
          "sharpe_canonical": 6.451764131795484,
          "sortino_backtest_scale": 7.48202821486086,
          "sortino_canonical": 9.065701195607275,
          "start": "2020-01-02",
          "total_return": 0.8449365998955432
        },
        "post2022": {
          "ann_return_arithmetic": 0.0478753909635249,
          "ann_return_geometric": 0.04900995154069965,
          "ann_volatility": 0.007136427710894931,
          "annualized_cost_drag": 0.02474117564099871,
          "annualized_turnover_units": 82.47058546999571,
          "avg_gross_exposure": 1.7837837837837838,
          "downside_deviation_annualized": 0.005029948200981187,
          "end": "2026-09-30",
          "invested_fraction": 0.8918918918918919,
          "max_drawdown": -0.02566276907192988,
          "max_drawdown_recomputed": -0.02566276907192988,
          "position_entries": 67,
          "position_exits": 67,
          "profit_factor": 2.7357538040233274,
          "rebalance_days": 1288,
          "risk_free_rate_annual": 0.02,
          "sample": "post2022",
          "sessions": 1369,
          "sharpe_backtest_scale": 4.065052252461156,
          "sharpe_canonical": 6.708593277058666,
          "sortino_backtest_scale": 5.767445385429756,
          "sortino_canonical": 9.51806838769948,
          "start": "2023-01-01",
          "total_return": 0.1965690444184991
        },
        "test_oos": {
          "ann_return_arithmetic": 0.013229423929404377,
          "ann_return_geometric": 0.013301632627365167,
          "ann_volatility": 0.005525077933013873,
          "annualized_cost_drag": 0.030398613428460574,
          "annualized_turnover_units": 101.32871142820193,
          "avg_gross_exposure": 1.6990595611285266,
          "downside_deviation_annualized": 0.00513516009148698,
          "end": "2026-09-30",
          "invested_fraction": 0.8495297805642633,
          "max_drawdown": -0.02566276907192888,
          "max_drawdown_recomputed": -0.02566276907192888,
          "position_entries": 40,
          "position_exits": 40,
          "profit_factor": 1.4048311975536898,
          "rebalance_days": 582,
          "risk_free_rate_annual": 0.02,
          "sample": "test_oos",
          "sessions": 638,
          "sharpe_backtest_scale": -1.2123570841616966,
          "sharpe_canonical": 2.3944320948587707,
          "sortino_backtest_scale": -1.3044125700656,
          "sortino_canonical": 2.576243718542678,
          "start": "2025-01-01",
          "total_return": 0.023366054738425124
        },
        "train": {
          "ann_return_arithmetic": 0.14454129167507113,
          "ann_return_geometric": 0.15526396681551535,
          "ann_volatility": 0.019192049556311493,
          "annualized_cost_drag": 0.03269811014579597,
          "annualized_turnover_units": 108.99370048598657,
          "avg_gross_exposure": 1.7223744292237444,
          "downside_deviation_annualized": 0.013291062197839007,
          "end": "2022-12-31",
          "invested_fraction": 0.8611872146118722,
          "max_drawdown": -0.01899735262103741,
          "max_drawdown_recomputed": -0.01899735262103741,
          "position_entries": 70,
          "position_exits": 69,
          "profit_factor": 4.214049280642537,
          "rebalance_days": 1012,
          "risk_free_rate_annual": 0.02,
          "sample": "train",
          "sessions": 1095,
          "sharpe_backtest_scale": 7.047916712523937,
          "sharpe_canonical": 7.531310882194826,
          "sortino_backtest_scale": 10.177062209332519,
          "sortino_canonical": 10.875074506729199,
          "start": "2020-01-02",
          "total_return": 0.5418555314475288
        },
        "val": {
          "ann_return_arithmetic": 0.07811359474980246,
          "ann_return_geometric": 0.08120222359678464,
          "ann_volatility": 0.00796358294369561,
          "annualized_cost_drag": 0.01980349396056005,
          "annualized_turnover_units": 66.01164653520017,
          "avg_gross_exposure": 1.8577291381668946,
          "downside_deviation_annualized": 0.004899294489306789,
          "end": "2024-12-31",
          "invested_fraction": 0.9288645690834473,
          "max_drawdown": -0.010491344356507892,
          "max_drawdown_recomputed": -0.010491344356507892,
          "position_entries": 27,
          "position_exits": 27,
          "profit_factor": 4.376660131098841,
          "rebalance_days": 706,
          "risk_free_rate_annual": 0.02,
          "sample": "val",
          "sessions": 731,
          "sharpe_backtest_scale": 7.685262278235643,
          "sharpe_canonical": 9.808850526463253,
          "sortino_backtest_scale": 12.492048340912094,
          "sortino_canonical": 15.94384557211112,
          "start": "2023-01-01",
          "total_return": 0.16924832407533819
        }
      },
      "symbol": "BTCUSDT",
      "turnover_convention": "drift",
      "yearly": {
        "2020": {
          "ann_return_geometric": 0.162065382189712,
          "annualized_turnover_units": 92.83739394056414,
          "invested_fraction": 0.8602739726027397,
          "max_drawdown": -0.01899735262103741,
          "sessions": 365,
          "sharpe_canonical": 7.122828317848858
        },
        "2021": {
          "ann_return_geometric": 0.3319757132132326,
          "annualized_turnover_units": 72.82259326068561,
          "invested_fraction": 0.9205479452054794,
          "max_drawdown": -0.011246216804782772,
          "sessions": 365,
          "sharpe_canonical": 12.918760930583268
        },
        "2022": {
          "ann_return_geometric": -0.0038681799849341614,
          "annualized_turnover_units": 161.32111425670996,
          "invested_fraction": 0.8027397260273973,
          "max_drawdown": -0.01458579811257743,
          "sessions": 365,
          "sharpe_canonical": -0.5397358052016877
        },
        "2023": {
          "ann_return_geometric": 0.05305368803313382,
          "annualized_turnover_units": 78.5354610798126,
          "invested_fraction": 0.9232876712328767,
          "max_drawdown": -0.010484935270352214,
          "sessions": 365,
          "sharpe_canonical": 7.452051867356241
        },
        "2024": {
          "ann_return_geometric": 0.11002317291433417,
          "annualized_turnover_units": 53.522050063114,
          "invested_fraction": 0.9344262295081968,
          "max_drawdown": -0.010491344356507226,
          "sessions": 366,
          "sharpe_canonical": 12.060057764877355
        },
        "2025": {
          "ann_return_geometric": 0.02902081072731666,
          "annualized_turnover_units": 74.28704802033101,
          "invested_fraction": 0.9178082191780822,
          "max_drawdown": -0.010776567409182425,
          "sessions": 365,
          "sharpe_canonical": 5.578916082359584
        },
        "2026": {
          "ann_return_geometric": -0.00734035594317517,
          "annualized_turnover_units": 137.4833163508132,
          "invested_fraction": 0.7582417582417582,
          "max_drawdown": -0.025662769071929104,
          "sessions": 273,
          "sharpe_canonical": -1.256299261010042
        }
      }
    },
    "BTCUSDT_funding_positive_sameday": {
      "book": "BTCUSDT_funding_positive_sameday",
      "bootstrap": {
        "full": {
          "ann_return_arithmetic_ci_95": [
            0.04589836625306857,
            0.1586085353615672
          ],
          "ann_return_geometric_ci_95": [
            0.046934839509619436,
            0.1716721393161238
          ],
          "block_days": 126,
          "n_bootstrap": 2000,
          "seed": 20261019,
          "sharpe_ci_95": [
            5.04818385640684,
            9.628514455867187
          ]
        },
        "post2022": {
          "ann_return_arithmetic_ci_95": [
            0.017424664954513537,
            0.08802491661245032
          ],
          "ann_return_geometric_ci_95": [
            0.0175583893936956,
            0.09196998193264719
          ],
          "block_days": 126,
          "n_bootstrap": 2000,
          "seed": 20261019,
          "sharpe_ci_95": [
            2.6995950469190424,
            11.04414700295658
          ]
        },
        "test_oos": {
          "ann_return_arithmetic_ci_95": [
            -0.017648283436424227,
            0.038126497343177045
          ],
          "ann_return_geometric_ci_95": [
            -0.017512317086097195,
            0.03884994841144885
          ],
          "block_days": 63,
          "n_bootstrap": 2000,
          "seed": 20261019,
          "sharpe_ci_95": [
            -2.9489119162953426,
            8.11810407108541
          ]
        }
      },
      "cost_bps_per_unit": 3.0,
      "cost_sensitivity": {
        "1.5bp": {
          "ann_return_arithmetic": 0.11227885758054,
          "ann_return_geometric": 0.11871645234386285,
          "annualized_cost_drag": 0.014106768377818069,
          "annualized_turnover_units": 94.04512251878714,
          "cost_bps_per_unit": 1.5,
          "max_drawdown": -0.009923198982147441,
          "sharpe_canonical": 8.888956792130571
        },
        "3.0bp": {
          "ann_return_arithmetic": 0.09817208920272193,
          "ann_return_geometric": 0.10304153602679245,
          "annualized_cost_drag": 0.028213536755636138,
          "annualized_turnover_units": 94.04512251878714,
          "cost_bps_per_unit": 3.0,
          "max_drawdown": -0.022839405196975804,
          "sharpe_canonical": 7.413565761113842
        },
        "4.5bp": {
          "ann_return_arithmetic": 0.08406532082490387,
          "ann_return_geometric": 0.0875821759126465,
          "annualized_cost_drag": 0.04232030513345421,
          "annualized_turnover_units": 94.04512251878714,
          "cost_bps_per_unit": 4.5,
          "max_drawdown": -0.03723002509734952,
          "sharpe_canonical": 5.98093629779916
        }
      },
      "entries_full_sample": 137,
      "exits_full_sample": 136,
      "leg_weight": 1.0,
      "look_ahead": true,
      "rule": "funding_positive_sameday",
      "rule_label": "Funding-positive only (same-day signal, pre-registered)",
      "samples": {
        "full": {
          "ann_return_arithmetic": 0.09817208920272193,
          "ann_return_geometric": 0.10304153602679245,
          "ann_volatility": 0.013242222753005186,
          "annualized_cost_drag": 0.028213536755636138,
          "annualized_turnover_units": 94.04512251878714,
          "avg_gross_exposure": 1.7573051948051948,
          "downside_deviation_annualized": 0.00589876757003913,
          "end": "2026-09-30",
          "invested_fraction": 0.8786525974025974,
          "max_drawdown": -0.022839405196975804,
          "max_drawdown_recomputed": -0.022839405196975804,
          "position_entries": 137,
          "position_exits": 136,
          "profit_factor": 4.251368605461089,
          "rebalance_days": 2301,
          "risk_free_rate_annual": 0.02,
          "sample": "full",
          "sessions": 2464,
          "sharpe_backtest_scale": 6.270966557177648,
          "sharpe_canonical": 7.413565761113842,
          "sortino_backtest_scale": 14.077777271404099,
          "sortino_canonical": 16.642813610991407,
          "start": "2020-01-02",
          "total_return": 0.9387609843182081
        },
        "post2022": {
          "ann_return_arithmetic": 0.05104770474717205,
          "ann_return_geometric": 0.052343629245548584,
          "ann_volatility": 0.006994172856006488,
          "annualized_cost_drag": 0.02471855024801723,
          "annualized_turnover_units": 82.39516749339077,
          "avg_gross_exposure": 1.7837837837837838,
          "downside_deviation_annualized": 0.004878979506541928,
          "end": "2026-09-30",
          "invested_fraction": 0.8918918918918919,
          "max_drawdown": -0.022839405196974805,
          "max_drawdown_recomputed": -0.022839405196974805,
          "position_entries": 67,
          "position_exits": 67,
          "profit_factor": 2.9938709573489293,
          "rebalance_days": 1288,
          "risk_free_rate_annual": 0.02,
          "sample": "post2022",
          "sessions": 1369,
          "sharpe_backtest_scale": 4.624368014835717,
          "sharpe_canonical": 7.298604967038107,
          "sortino_backtest_scale": 6.629179155637151,
          "sortino_canonical": 10.462783186263701,
          "start": "2023-01-01",
          "total_return": 0.21089388864220848
        },
        "test_oos": {
          "ann_return_arithmetic": 0.016716075649283173,
          "ann_return_geometric": 0.016841474043362226,
          "ann_volatility": 0.005382390355268952,
          "annualized_cost_drag": 0.03034125553005664,
          "annualized_turnover_units": 101.13751843352213,
          "avg_gross_exposure": 1.6990595611285266,
          "downside_deviation_annualized": 0.004914974144620865,
          "end": "2026-09-30",
          "invested_fraction": 0.8495297805642633,
          "max_drawdown": -0.022839405196976137,
          "max_drawdown_recomputed": -0.022839405196976137,
          "position_entries": 40,
          "position_exits": 40,
          "profit_factor": 1.5446937123378475,
          "rebalance_days": 582,
          "risk_free_rate_annual": 0.02,
          "sample": "test_oos",
          "sessions": 638,
          "sharpe_backtest_scale": -0.5868258799820821,
          "sharpe_canonical": 3.105697384605225,
          "sortino_backtest_scale": -0.6426332801963132,
          "sortino_canonical": 3.4010505767518397,
          "start": "2025-01-01",
          "total_return": 0.029623120544644888
        },
        "train": {
          "ann_return_arithmetic": 0.1570883287640441,
          "ann_return_geometric": 0.16987482329683234,
          "ann_volatility": 0.017790163768518007,
          "annualized_cost_drag": 0.03258306783228482,
          "annualized_turnover_units": 108.61022610761606,
          "avg_gross_exposure": 1.724200913242009,
          "downside_deviation_annualized": 0.006773625463460127,
          "end": "2022-12-31",
          "invested_fraction": 0.8621004566210045,
          "max_drawdown": -0.007507608913492336,
          "max_drawdown_recomputed": -0.007507608913492336,
          "position_entries": 70,
          "position_exits": 69,
          "profit_factor": 5.371476684584547,
          "rebalance_days": 1013,
          "risk_free_rate_annual": 0.02,
          "sample": "train",
          "sessions": 1095,
          "sharpe_backtest_scale": 8.424589298163472,
          "sharpe_canonical": 8.830066479884362,
          "sortino_backtest_scale": 22.1262341865995,
          "sortino_canonical": 23.19117429970799,
          "start": "2020-01-02",
          "total_return": 0.6010989918300567
        },
        "val": {
          "ann_return_arithmetic": 0.08101156160688903,
          "ann_return_geometric": 0.08434062330111103,
          "ann_volatility": 0.00781709709443918,
          "annualized_cost_drag": 0.019811182300081314,
          "annualized_turnover_units": 66.03727433360439,
          "avg_gross_exposure": 1.8577291381668946,
          "downside_deviation_annualized": 0.00480785180014237,
          "end": "2024-12-31",
          "invested_fraction": 0.9288645690834473,
          "max_drawdown": -0.009265098618627232,
          "max_drawdown_recomputed": -0.009265098618627232,
          "position_entries": 27,
          "position_exits": 27,
          "profit_factor": 4.828014685513953,
          "rebalance_days": 706,
          "risk_free_rate_annual": 0.02,
          "sample": "val",
          "sessions": 731,
          "sharpe_backtest_scale": 8.230756574186698,
          "sharpe_canonical": 10.363381780753105,
          "sortino_backtest_scale": 13.38240569295538,
          "sortino_canonical": 16.849845830208437,
          "start": "2023-01-01",
          "total_return": 0.17605545609899753
        }
      },
      "symbol": "BTCUSDT",
      "turnover_convention": "drift",
      "yearly": {
        "2020": {
          "ann_return_geometric": 0.18495355372591105,
          "annualized_turnover_units": 92.49913695933655,
          "invested_fraction": 0.863013698630137,
          "max_drawdown": -0.006058876925114198,
          "sessions": 365,
          "sharpe_canonical": 9.615378067457755
        },
        "2021": {
          "ann_return_geometric": 0.3410389868030048,
          "annualized_turnover_units": 72.45193084520723,
          "invested_fraction": 0.9205479452054794,
          "max_drawdown": -0.007507608913492558,
          "sessions": 365,
          "sharpe_canonical": 13.427368103984074
        },
        "2022": {
          "ann_return_geometric": 0.0075705204687435135,
          "annualized_turnover_units": 160.87961051830433,
          "invested_fraction": 0.8027397260273973,
          "max_drawdown": -0.0061177470507298715,
          "sessions": 365,
          "sharpe_canonical": 1.1033913269779843
        },
        "2023": {
          "ann_return_geometric": 0.057144985926288916,
          "annualized_turnover_units": 78.40486292956477,
          "invested_fraction": 0.9232876712328767,
          "max_drawdown": -0.009185674845058944,
          "sessions": 365,
          "sharpe_canonical": 8.291968155591892
        },
        "2024": {
          "ann_return_geometric": 0.11215869749979723,
          "annualized_turnover_units": 53.70347696331606,
          "invested_fraction": 0.9344262295081968,
          "max_drawdown": -0.009265098618627676,
          "sessions": 366,
          "sharpe_canonical": 12.376520189431755
        },
        "2025": {
          "ann_return_geometric": 0.032136187114079506,
          "annualized_turnover_units": 74.40703197598064,
          "invested_fraction": 0.9178082191780822,
          "max_drawdown": -0.008850736137373083,
          "sessions": 365,
          "sharpe_canonical": 6.380541597929506
        },
        "2026": {
          "ann_return_geometric": -0.0032540101106427466,
          "annualized_turnover_units": 136.8760809133853,
          "invested_fraction": 0.7582417582417582,
          "max_drawdown": -0.022839405196975693,
          "sessions": 273,
          "sharpe_canonical": -0.5643817313941614
        }
      }
    },
    "ETHUSDT_always_on": {
      "book": "BTCUSDT_always_on",
      "bootstrap": {
        "full": {
          "ann_return_arithmetic_ci_95": [
            0.06497167032542431,
            0.2066012169974819
          ],
          "ann_return_geometric_ci_95": [
            0.0670826811930848,
            0.22911588156217072
          ],
          "block_days": 126,
          "n_bootstrap": 2000,
          "seed": 20261019,
          "sharpe_ci_95": [
            5.197240431651126,
            9.977681469736883
          ]
        },
        "post2022": {
          "ann_return_arithmetic_ci_95": [
            0.03943392006453595,
            0.10325830869829854
          ],
          "ann_return_geometric_ci_95": [
            0.040208057908493584,
            0.10872925369506728
          ],
          "block_days": 126,
          "n_bootstrap": 2000,
          "seed": 20261019,
          "sharpe_ci_95": [
            7.645878411187302,
            13.81409405359275
          ]
        },
        "test_oos": {
          "ann_return_arithmetic_ci_95": [
            0.01214146157550715,
            0.041234452257673734
          ],
          "ann_return_geometric_ci_95": [
            0.01220677880002996,
            0.042087003996878335
          ],
          "block_days": 63,
          "n_bootstrap": 2000,
          "seed": 20261019,
          "sharpe_ci_95": [
            2.706006990359816,
            11.156543859127199
          ]
        }
      },
      "cost_bps_per_unit": 3.0,
      "cost_sensitivity": {
        "1.5bp": {
          "ann_return_arithmetic": 0.13254865671410607,
          "ann_return_geometric": 0.14152345518857534,
          "annualized_cost_drag": 0.0031908595701727045,
          "annualized_turnover_units": 21.2723971344847,
          "cost_bps_per_unit": 1.5,
          "max_drawdown": -0.018242227377008646,
          "sharpe_canonical": 7.385285335958099
        },
        "3.0bp": {
          "ann_return_arithmetic": 0.1293577971439334,
          "ann_return_geometric": 0.13788810359464332,
          "annualized_cost_drag": 0.006381719140345409,
          "annualized_turnover_units": 21.2723971344847,
          "cost_bps_per_unit": 3.0,
          "max_drawdown": -0.01910783258033777,
          "sharpe_canonical": 7.20732786990488
        },
        "4.5bp": {
          "ann_return_arithmetic": 0.12616693757376068,
          "ann_return_geometric": 0.13426424628943323,
          "annualized_cost_drag": 0.009572578710518115,
          "annualized_turnover_units": 21.2723971344847,
          "cost_bps_per_unit": 4.5,
          "max_drawdown": -0.019987373179009227,
          "sharpe_canonical": 7.028389625237822
        }
      },
      "entries_full_sample": 1,
      "exits_full_sample": 0,
      "leg_weight": 1.0,
      "look_ahead": false,
      "rule": "always_on",
      "rule_label": "Always-on carry",
      "samples": {
        "full": {
          "ann_return_arithmetic": 0.1293577971439334,
          "ann_return_geometric": 0.13788810359464332,
          "ann_volatility": 0.017948093867643157,
          "annualized_cost_drag": 0.006381719140345409,
          "annualized_turnover_units": 21.2723971344847,
          "avg_gross_exposure": 2.0,
          "downside_deviation_annualized": 0.015346424876721856,
          "end": "2026-09-30",
          "invested_fraction": 1.0,
          "max_drawdown": -0.01910783258033777,
          "max_drawdown_recomputed": -0.01910783258033777,
          "position_entries": 1,
          "position_exits": 0,
          "profit_factor": 5.97633606373957,
          "rebalance_days": 2464,
          "risk_free_rate_annual": 0.02,
          "sample": "full",
          "sessions": 2464,
          "sharpe_backtest_scale": 6.56827986659754,
          "sharpe_canonical": 7.20732786990488,
          "sortino_backtest_scale": 7.681795893287255,
          "sortino_canonical": 8.429181270756363,
          "start": "2020-01-02",
          "total_return": 1.391720543943947
        },
        "post2022": {
          "ann_return_arithmetic": 0.06821872717972946,
          "ann_return_geometric": 0.0705719291700091,
          "ann_volatility": 0.00622261734856071,
          "annualized_cost_drag": 0.00495943904783338,
          "annualized_turnover_units": 16.531463492777934,
          "avg_gross_exposure": 2.0,
          "downside_deviation_annualized": 0.0038839564869855743,
          "end": "2026-09-30",
          "invested_fraction": 1.0,
          "max_drawdown": -0.00792716300651708,
          "max_drawdown_recomputed": -0.00792716300651708,
          "position_entries": 0,
          "position_exits": 0,
          "profit_factor": 6.341342020150919,
          "rebalance_days": 1369,
          "risk_free_rate_annual": 0.02,
          "sample": "post2022",
          "sessions": 1369,
          "sharpe_backtest_scale": 8.127115382035562,
          "sharpe_canonical": 10.963027831931274,
          "sortino_backtest_scale": 13.020724959063354,
          "sortino_canonical": 17.564235698396185,
          "start": "2023-01-01",
          "total_return": 0.29145634148558086
        },
        "test_oos": {
          "ann_return_arithmetic": 0.030621380526178688,
          "ann_return_geometric": 0.031084493567453908,
          "ann_volatility": 0.004232121564974176,
          "annualized_cost_drag": 0.0054545227521363435,
          "annualized_turnover_units": 18.181742507121147,
          "avg_gross_exposure": 2.0,
          "downside_deviation_annualized": 0.0037773852885606305,
          "end": "2026-09-30",
          "invested_fraction": 1.0,
          "max_drawdown": -0.007927163006516524,
          "max_drawdown_recomputed": -0.007927163006516524,
          "position_entries": 0,
          "position_exits": 0,
          "profit_factor": 2.916189427531608,
          "rebalance_days": 638,
          "risk_free_rate_annual": 0.02,
          "sample": "test_oos",
          "sessions": 638,
          "sharpe_backtest_scale": 2.619134019965597,
          "sharpe_canonical": 7.235468087591556,
          "sortino_backtest_scale": 2.934435521052618,
          "sortino_canonical": 8.106501769600246,
          "start": "2025-01-01",
          "total_return": 0.05496397675913367
        },
        "train": {
          "ann_return_arithmetic": 0.20579559329096095,
          "ann_return_geometric": 0.22803355848660023,
          "ann_volatility": 0.025455587794256582,
          "annualized_cost_drag": 0.008159893977467752,
          "annualized_turnover_units": 27.199646591559176,
          "avg_gross_exposure": 2.0,
          "downside_deviation_annualized": 0.02104738135167717,
          "end": "2022-12-31",
          "invested_fraction": 1.0,
          "max_drawdown": -0.01910783258033777,
          "max_drawdown_recomputed": -0.01910783258033777,
          "position_entries": 1,
          "position_exits": 0,
          "profit_factor": 5.839283397184105,
          "rebalance_days": 1095,
          "risk_free_rate_annual": 0.02,
          "sample": "train",
          "sessions": 1095,
          "sharpe_backtest_scale": 8.172412287943231,
          "sharpe_canonical": 8.084495826782424,
          "sortino_backtest_scale": 9.88405897202138,
          "sortino_canonical": 9.777729108070826,
          "start": "2020-01-02",
          "total_return": 0.8519561731314276
        },
        "val": {
          "ann_return_arithmetic": 0.1010328272686014,
          "ann_return_geometric": 0.10626956857151737,
          "ann_volatility": 0.007112959660880824,
          "annualized_cost_drag": 0.004527341368838455,
          "annualized_turnover_units": 15.091137896128187,
          "avg_gross_exposure": 2.0,
          "downside_deviation_annualized": 0.004052341340476993,
          "end": "2024-12-31",
          "invested_fraction": 1.0,
          "max_drawdown": -0.001273566865419462,
          "max_drawdown_recomputed": -0.001273566865419462,
          "position_entries": 0,
          "position_exits": 0,
          "profit_factor": 11.132147759351295,
          "rebalance_days": 731,
          "risk_free_rate_annual": 0.02,
          "sample": "val",
          "sessions": 731,
          "sharpe_backtest_scale": 12.128505247397156,
          "sharpe_canonical": 14.204048959289349,
          "sortino_backtest_scale": 21.288820788567318,
          "sortino_canonical": 24.931963716735922,
          "start": "2023-01-01",
          "total_return": 0.22417103326404964
        }
      },
      "symbol": "BTCUSDT",
      "turnover_convention": "drift",
      "yearly": {
        "2020": {
          "ann_return_geometric": 0.28821198950000326,
          "annualized_turnover_units": 27.319319554352184,
          "invested_fraction": 1.0,
          "max_drawdown": -0.01673732151551477,
          "sessions": 365,
          "sharpe_canonical": 8.790888460067016
        },
        "2021": {
          "ann_return_geometric": 0.4378162857734553,
          "annualized_turnover_units": 30.590171926727237,
          "invested_fraction": 1.0,
          "max_drawdown": -0.0040248828575828455,
          "sessions": 365,
          "sharpe_canonical": 12.759775145966275
        },
        "2022": {
          "ann_return_geometric": -0.00013821575267491948,
          "annualized_turnover_units": 23.689448293598122,
          "invested_fraction": 1.0,
          "max_drawdown": -0.019107832580336992,
          "sessions": 365,
          "sharpe_canonical": -0.007897090651010404
        },
        "2023": {
          "ann_return_geometric": 0.08029934807548367,
          "annualized_turnover_units": 12.558235129049283,
          "invested_fraction": 1.0,
          "max_drawdown": -0.0010000843083727284,
          "sessions": 365,
          "sharpe_canonical": 12.53285977139393
        },
        "2024": {
          "ann_return_geometric": 0.1327905821652593,
          "annualized_turnover_units": 17.61712016384348,
          "invested_fraction": 1.0,
          "max_drawdown": -0.001273566865419351,
          "sessions": 366,
          "sharpe_canonical": 16.07730366551592
        },
        "2025": {
          "ann_return_geometric": 0.043750153892321286,
          "annualized_turnover_units": 19.888605857677295,
          "invested_fraction": 1.0,
          "max_drawdown": -0.0023786143796198367,
          "sessions": 365,
          "sharpe_canonical": 9.964881502111666
        },
        "2026": {
          "ann_return_geometric": 0.014390338081614829,
          "annualized_turnover_units": 15.899672459674285,
          "invested_fraction": 1.0,
          "max_drawdown": -0.007927163006516413,
          "sessions": 273,
          "sharpe_canonical": 3.580673508071041
        }
      }
    },
    "ETHUSDT_funding_positive_lagged": {
      "book": "BTCUSDT_funding_positive_lagged",
      "bootstrap": {
        "full": {
          "ann_return_arithmetic_ci_95": [
            0.04104031142097309,
            0.18854345782082407
          ],
          "ann_return_geometric_ci_95": [
            0.041844687367146124,
            0.2071050235768964
          ],
          "block_days": 126,
          "n_bootstrap": 2000,
          "seed": 20261019,
          "sharpe_ci_95": [
            3.3014632417547283,
            8.852245951092208
          ]
        },
        "post2022": {
          "ann_return_arithmetic_ci_95": [
            0.008012618309955253,
            0.08944579379243062
          ],
          "ann_return_geometric_ci_95": [
            0.008024892152646424,
            0.09351996736123155
          ],
          "block_days": 126,
          "n_bootstrap": 2000,
          "seed": 20261019,
          "sharpe_ci_95": [
            1.2285724802819644,
            10.8820901708555
          ]
        },
        "test_oos": {
          "ann_return_arithmetic_ci_95": [
            -0.03648778130640822,
            0.01822549529052516
          ],
          "ann_return_geometric_ci_95": [
            -0.03585170695098715,
            0.01837756677178158
          ],
          "block_days": 63,
          "n_bootstrap": 2000,
          "seed": 20261019,
          "sharpe_ci_95": [
            -5.680966026691175,
            3.3989062071131935
          ]
        }
      },
      "cost_bps_per_unit": 3.0,
      "cost_sensitivity": {
        "1.5bp": {
          "ann_return_arithmetic": 0.1246805612650223,
          "ann_return_geometric": 0.13258429433958474,
          "annualized_cost_drag": 0.01494929625989752,
          "annualized_turnover_units": 99.66197506598347,
          "cost_bps_per_unit": 1.5,
          "max_drawdown": -0.018263444212353597,
          "sharpe_canonical": 7.025411082443364
        },
        "3.0bp": {
          "ann_return_arithmetic": 0.1097312650051248,
          "ann_return_geometric": 0.11577454756247829,
          "annualized_cost_drag": 0.02989859251979504,
          "annualized_turnover_units": 99.66197506598347,
          "cost_bps_per_unit": 3.0,
          "max_drawdown": -0.04194463793488845,
          "sharpe_canonical": 6.019405453191115
        },
        "4.5bp": {
          "ann_return_arithmetic": 0.09478196874522726,
          "ann_return_geometric": 0.09921010112683937,
          "annualized_cost_drag": 0.04484788877969256,
          "annualized_turnover_units": 99.66197506598347,
          "cost_bps_per_unit": 4.5,
          "max_drawdown": -0.07262623803835633,
          "sharpe_canonical": 5.022955832739539
        }
      },
      "entries_full_sample": 138,
      "exits_full_sample": 137,
      "leg_weight": 1.0,
      "look_ahead": false,
      "rule": "funding_positive_lagged",
      "rule_label": "Funding-positive only (previous-day signal, implementable)",
      "samples": {
        "full": {
          "ann_return_arithmetic": 0.1097312650051248,
          "ann_return_geometric": 0.11577454756247829,
          "ann_volatility": 0.018229585273567526,
          "annualized_cost_drag": 0.02989859251979504,
          "annualized_turnover_units": 99.66197506598347,
          "avg_gross_exposure": 1.760551948051948,
          "downside_deviation_annualized": 0.013676816637986595,
          "end": "2026-09-30",
          "invested_fraction": 0.880275974025974,
          "max_drawdown": -0.04194463793488845,
          "max_drawdown_recomputed": -0.04194463793488845,
          "position_entries": 138,
          "position_exits": 137,
          "profit_factor": 3.8160100166976685,
          "rebalance_days": 2306,
          "risk_free_rate_annual": 0.02,
          "sample": "full",
          "sessions": 2464,
          "sharpe_backtest_scale": 5.253797391723944,
          "sharpe_canonical": 6.019405453191115,
          "sortino_backtest_scale": 7.002692958277281,
          "sortino_canonical": 8.02315830573851,
          "start": "2020-01-02",
          "total_return": 1.0949498262324617
        },
        "post2022": {
          "ann_return_arithmetic": 0.047045392941694714,
          "ann_return_geometric": 0.048137478664466826,
          "ann_volatility": 0.007434140877915205,
          "annualized_cost_drag": 0.027689890658833947,
          "annualized_turnover_units": 92.2996355294465,
          "avg_gross_exposure": 1.7735573411249086,
          "downside_deviation_annualized": 0.005189824042132622,
          "end": "2026-09-30",
          "invested_fraction": 0.8867786705624543,
          "max_drawdown": -0.02855390379519762,
          "max_drawdown_recomputed": -0.02855390379519762,
          "position_entries": 73,
          "position_exits": 73,
          "profit_factor": 2.5945883506624505,
          "rebalance_days": 1287,
          "risk_free_rate_annual": 0.02,
          "sample": "post2022",
          "sessions": 1369,
          "sharpe_backtest_scale": 3.784899846067696,
          "sharpe_canonical": 6.328289134451794,
          "sortino_backtest_scale": 5.421663323464906,
          "sortino_canonical": 9.064930248071116,
          "start": "2023-01-01",
          "total_return": 0.19284063285477338
        },
        "test_oos": {
          "ann_return_arithmetic": -0.0026461226955815926,
          "ann_return_geometric": -0.0026605892411433185,
          "ann_volatility": 0.006004681368044835,
          "annualized_cost_drag": 0.042089327370280975,
          "annualized_turnover_units": 140.2977579009366,
          "avg_gross_exposure": 1.6206896551724137,
          "downside_deviation_annualized": 0.005177750595056256,
          "end": "2026-09-30",
          "invested_fraction": 0.8103448275862069,
          "max_drawdown": -0.028553903795197844,
          "max_drawdown_recomputed": -0.028553903795197844,
          "position_entries": 55,
          "position_exits": 55,
          "profit_factor": 0.9375541304551478,
          "rebalance_days": 572,
          "risk_free_rate_annual": 0.02,
          "sample": "test_oos",
          "sessions": 638,
          "sharpe_backtest_scale": -3.7738204331267893,
          "sharpe_canonical": -0.44067662102163935,
          "sortino_backtest_scale": -4.3765316279968705,
          "sortino_canonical": -0.5110564224758382,
          "start": "2025-01-01",
          "total_return": -0.0046459359193996574
        },
        "train": {
          "ann_return_arithmetic": 0.18810291692734926,
          "ann_return_geometric": 0.20650854066474889,
          "ann_volatility": 0.02547051656765773,
          "annualized_cost_drag": 0.03265997411582769,
          "annualized_turnover_units": 108.8665803860923,
          "avg_gross_exposure": 1.7442922374429224,
          "downside_deviation_annualized": 0.01875506571929408,
          "end": "2022-12-31",
          "invested_fraction": 0.8721461187214612,
          "max_drawdown": -0.04194463793488845,
          "max_drawdown_recomputed": -0.04194463793488845,
          "position_entries": 65,
          "position_exits": 64,
          "profit_factor": 4.7029004435609085,
          "rebalance_days": 1019,
          "risk_free_rate_annual": 0.02,
          "sample": "train",
          "sessions": 1095,
          "sharpe_backtest_scale": 7.322526819168483,
          "sharpe_canonical": 7.385123753877883,
          "sortino_backtest_scale": 9.944435463794731,
          "sortino_canonical": 10.029445897053847,
          "start": "2020-01-02",
          "total_return": 0.7562696713463721
        },
        "val": {
          "ann_return_arithmetic": 0.09041500576875666,
          "ann_return_geometric": 0.09458287682615985,
          "ann_volatility": 0.0078123188854789,
          "annualized_cost_drag": 0.01512239322804982,
          "annualized_turnover_units": 50.40797742683274,
          "avg_gross_exposure": 1.9069767441860466,
          "downside_deviation_annualized": 0.005091411330251628,
          "end": "2024-12-31",
          "invested_fraction": 0.9534883720930233,
          "max_drawdown": -0.006478716812333474,
          "max_drawdown_recomputed": -0.006478716812333474,
          "position_entries": 18,
          "position_exits": 18,
          "profit_factor": 5.949038863603939,
          "rebalance_days": 715,
          "risk_free_rate_annual": 0.02,
          "sample": "val",
          "sessions": 731,
          "sharpe_backtest_scale": 9.5468295546397,
          "sharpe_canonical": 11.573389040328987,
          "sortino_backtest_scale": 14.648762786658175,
          "sortino_canonical": 17.7583384849576,
          "start": "2023-01-01",
          "total_return": 0.1984083613066765
        }
      },
      "symbol": "BTCUSDT",
      "turnover_convention": "drift",
      "yearly": {
        "2020": {
          "ann_return_geometric": 0.2805575194485024,
          "annualized_turnover_units": 46.731605205314104,
          "invested_fraction": 0.9835616438356164,
          "max_drawdown": -0.01960148317027499,
          "sessions": 365,
          "sharpe_canonical": 8.539788424822476
        },
        "2021": {
          "ann_return_geometric": 0.4258186053568367,
          "annualized_turnover_units": 61.18860086496207,
          "invested_fraction": 0.9671232876712329,
          "max_drawdown": -0.005067818562473292,
          "sessions": 365,
          "sharpe_canonical": 12.374327504852673
        },
        "2022": {
          "ann_return_geometric": -0.0381046317536754,
          "annualized_turnover_units": 218.6795350880007,
          "invested_fraction": 0.6657534246575343,
          "max_drawdown": -0.04194463793488834,
          "sessions": 365,
          "sharpe_canonical": -5.225993753910589
        },
        "2023": {
          "ann_return_geometric": 0.0651664043960909,
          "annualized_turnover_units": 59.95236292072491,
          "invested_fraction": 0.936986301369863,
          "max_drawdown": -0.006478716812333474,
          "sessions": 365,
          "sharpe_canonical": 9.010226250375887
        },
        "2024": {
          "ann_return_geometric": 0.12472801816025259,
          "annualized_turnover_units": 40.88966948893479,
          "invested_fraction": 0.9699453551912568,
          "max_drawdown": -0.005993245791639734,
          "sessions": 366,
          "sharpe_canonical": 14.157153150688089
        },
        "2025": {
          "ann_return_geometric": 0.013002430818890742,
          "annualized_turnover_units": 121.63505364147403,
          "invested_fraction": 0.8958904109589041,
          "max_drawdown": -0.014791083220955015,
          "sessions": 365,
          "sharpe_canonical": 2.206757331025264
        },
        "2026": {
          "ann_return_geometric": -0.023224294148231017,
          "annualized_turnover_units": 165.249725134284,
          "invested_fraction": 0.6959706959706959,
          "max_drawdown": -0.028553903795197733,
          "sessions": 273,
          "sharpe_canonical": -3.8933424209298235
        }
      }
    },
    "ETHUSDT_funding_positive_sameday": {
      "book": "BTCUSDT_funding_positive_sameday",
      "bootstrap": {
        "full": {
          "ann_return_arithmetic_ci_95": [
            0.04807762888825562,
            0.19751487990942587
          ],
          "ann_return_geometric_ci_95": [
            0.04919900107130611,
            0.21802934361966006
          ],
          "block_days": 126,
          "n_bootstrap": 2000,
          "seed": 20261019,
          "sharpe_ci_95": [
            4.593726750364231,
            9.348946893315878
          ]
        },
        "post2022": {
          "ann_return_arithmetic_ci_95": [
            0.013626598899875662,
            0.09126956617444172
          ],
          "ann_return_geometric_ci_95": [
            0.013701711669967365,
            0.09551853466045547
          ],
          "block_days": 126,
          "n_bootstrap": 2000,
          "seed": 20261019,
          "sharpe_ci_95": [
            2.145066121536703,
            11.232642303148225
          ]
        },
        "test_oos": {
          "ann_return_arithmetic_ci_95": [
            -0.027269367979258663,
            0.02029086388100673
          ],
          "ann_return_geometric_ci_95": [
            -0.026919913398120318,
            0.020485497152657607
          ],
          "block_days": 63,
          "n_bootstrap": 2000,
          "seed": 20261019,
          "sharpe_ci_95": [
            -4.468635872113869,
            3.9820346145537253
          ]
        }
      },
      "cost_bps_per_unit": 3.0,
      "cost_sensitivity": {
        "1.5bp": {
          "ann_return_arithmetic": 0.1327616764869345,
          "ann_return_geometric": 0.1417991920973165,
          "annualized_cost_drag": 0.01492947837099347,
          "annualized_turnover_units": 99.52985580662315,
          "cost_bps_per_unit": 1.5,
          "max_drawdown": -0.00788967915549621,
          "sharpe_canonical": 8.148708620959775
        },
        "3.0bp": {
          "ann_return_arithmetic": 0.11783219811594103,
          "ann_return_geometric": 0.1248756427440827,
          "annualized_cost_drag": 0.02985895674198694,
          "annualized_turnover_units": 99.52985580662315,
          "cost_bps_per_unit": 3.0,
          "max_drawdown": -0.026403648650787148,
          "sharpe_canonical": 7.0135632061216
        },
        "4.5bp": {
          "ann_return_arithmetic": 0.10290271974494755,
          "ann_return_geometric": 0.10819870119345643,
          "annualized_cost_drag": 0.04478843511298042,
          "annualized_turnover_units": 99.52985580662315,
          "cost_bps_per_unit": 4.5,
          "max_drawdown": -0.054380428652991086,
          "sharpe_canonical": 5.887482774293801
        }
      },
      "entries_full_sample": 138,
      "exits_full_sample": 137,
      "leg_weight": 1.0,
      "look_ahead": true,
      "rule": "funding_positive_sameday",
      "rule_label": "Funding-positive only (same-day signal, pre-registered)",
      "samples": {
        "full": {
          "ann_return_arithmetic": 0.11783219811594103,
          "ann_return_geometric": 0.1248756427440827,
          "ann_volatility": 0.016800618266774064,
          "annualized_cost_drag": 0.02985895674198694,
          "annualized_turnover_units": 99.52985580662315,
          "avg_gross_exposure": 1.7613636363636365,
          "downside_deviation_annualized": 0.005758428120825902,
          "end": "2026-09-30",
          "invested_fraction": 0.8806818181818182,
          "max_drawdown": -0.026403648650787148,
          "max_drawdown_recomputed": -0.026403648650787148,
          "position_entries": 138,
          "position_exits": 137,
          "profit_factor": 4.577112299635201,
          "rebalance_days": 2307,
          "risk_free_rate_annual": 0.02,
          "sample": "full",
          "sessions": 2464,
          "sharpe_backtest_scale": 6.242368053293086,
          "sharpe_canonical": 7.0135632061216,
          "sortino_backtest_scale": 18.212546990868912,
          "sortino_canonical": 20.462562984816934,
          "start": "2020-01-02",
          "total_return": 1.2130461247773536
        },
        "post2022": {
          "ann_return_arithmetic": 0.05037426427795896,
          "ann_return_geometric": 0.05163346538279123,
          "ann_volatility": 0.00723628567813396,
          "annualized_cost_drag": 0.027664715333937977,
          "annualized_turnover_units": 92.21571777979327,
          "avg_gross_exposure": 1.7735573411249086,
          "downside_deviation_annualized": 0.005028932436300118,
          "end": "2026-09-30",
          "invested_fraction": 0.8867786705624543,
          "max_drawdown": -0.022406561162124805,
          "max_drawdown_recomputed": -0.022406561162124805,
          "position_entries": 73,
          "position_exits": 73,
          "profit_factor": 2.851816599344766,
          "rebalance_days": 1287,
          "risk_free_rate_annual": 0.02,
          "sample": "post2022",
          "sessions": 1369,
          "sharpe_backtest_scale": 4.371505878821058,
          "sharpe_canonical": 6.961342671997591,
          "sortino_backtest_scale": 6.290294368334082,
          "sortino_canonical": 10.016890247787913,
          "start": "2023-01-01",
          "total_return": 0.20783182261588085
        },
        "test_oos": {
          "ann_return_arithmetic": 0.0023674830719351125,
          "ann_return_geometric": 0.0023541934962125755,
          "ann_volatility": 0.005669410737044503,
          "annualized_cost_drag": 0.04204445147655621,
          "annualized_turnover_units": 140.1481715885207,
          "avg_gross_exposure": 1.6206896551724137,
          "downside_deviation_annualized": 0.00489058220012769,
          "end": "2026-09-30",
          "invested_fraction": 0.8103448275862069,
          "max_drawdown": -0.022406561162125693,
          "max_drawdown_recomputed": -0.022406561162125693,
          "position_entries": 55,
          "position_exits": 55,
          "profit_factor": 1.0611171375187953,
          "rebalance_days": 572,
          "risk_free_rate_annual": 0.02,
          "sample": "test_oos",
          "sessions": 638,
          "sharpe_backtest_scale": -3.1124586526229154,
          "sharpe_canonical": 0.41758891386467,
          "sortino_backtest_scale": -3.6081198069478733,
          "sortino_canonical": 0.48409023201231527,
          "start": "2025-01-01",
          "total_return": 0.004118623381426545
        },
        "train": {
          "ann_return_arithmetic": 0.20217001676817614,
          "ann_return_geometric": 0.22366160307387517,
          "ann_volatility": 0.023127660156807082,
          "annualized_cost_drag": 0.032602259470406146,
          "annualized_turnover_units": 108.67419823468715,
          "avg_gross_exposure": 1.7461187214611873,
          "downside_deviation_annualized": 0.006353739145349651,
          "end": "2022-12-31",
          "invested_fraction": 0.8730593607305936,
          "max_drawdown": -0.026403648650787148,
          "max_drawdown_recomputed": -0.026403648650787148,
          "position_entries": 65,
          "position_exits": 64,
          "profit_factor": 6.039840610166435,
          "rebalance_days": 1020,
          "risk_free_rate_annual": 0.02,
          "sample": "train",
          "sessions": 1095,
          "sharpe_backtest_scale": 8.80597525616668,
          "sharpe_canonical": 8.741481645676645,
          "sortino_backtest_scale": 32.05381876952512,
          "sortino_canonical": 31.819061523189202,
          "start": "2020-01-02",
          "total_return": 0.8322469099914924
        },
        "val": {
          "ann_return_arithmetic": 0.09227347961235462,
          "ann_return_geometric": 0.09661921625018,
          "ann_volatility": 0.0077295753959406915,
          "annualized_cost_drag": 0.015114412106864887,
          "annualized_turnover_units": 50.381373689549626,
          "avg_gross_exposure": 1.9069767441860466,
          "downside_deviation_annualized": 0.005096635436352339,
          "end": "2024-12-31",
          "invested_fraction": 0.9534883720930233,
          "max_drawdown": -0.005833685187965898,
          "max_drawdown_recomputed": -0.005833685187965898,
          "position_entries": 18,
          "position_exits": 18,
          "profit_factor": 6.384822811482599,
          "rebalance_days": 715,
          "risk_free_rate_annual": 0.02,
          "sample": "val",
          "sessions": 731,
          "sharpe_backtest_scale": 9.912474143200386,
          "sharpe_canonical": 11.937716483212453,
          "sortino_backtest_scale": 15.033293475080562,
          "sortino_canonical": 18.104783197598046,
          "start": "2023-01-01",
          "total_return": 0.20287762271397702
        }
      },
      "symbol": "BTCUSDT",
      "turnover_convention": "drift",
      "yearly": {
        "2020": {
          "ann_return_geometric": 0.3029990126339641,
          "annualized_turnover_units": 46.51013697676117,
          "invested_fraction": 0.9863013698630136,
          "max_drawdown": -0.002730194092474658,
          "sessions": 365,
          "sharpe_canonical": 11.41618050500259
        },
        "2021": {
          "ann_return_geometric": 0.4334415620401717,
          "annualized_turnover_units": 60.807539023851945,
          "invested_fraction": 0.9671232876712329,
          "max_drawdown": -0.004902085465202766,
          "sessions": 365,
          "sharpe_canonical": 12.712972570485427
        },
        "2022": {
          "ann_return_geometric": -0.01902052934507603,
          "annualized_turnover_units": 218.70491870344839,
          "invested_fraction": 0.6657534246575343,
          "max_drawdown": -0.02640364865078737,
          "sessions": 365,
          "sharpe_canonical": -2.729437440493366
        },
        "2023": {
          "ann_return_geometric": 0.06769330594745315,
          "annualized_turnover_units": 60.008802128898864,
          "invested_fraction": 0.936986301369863,
          "max_drawdown": -0.005833685187965898,
          "sessions": 365,
          "sharpe_canonical": 9.407001741424624
        },
        "2024": {
          "ann_return_geometric": 0.12624652585491103,
          "annualized_turnover_units": 40.78024969948823,
          "invested_fraction": 0.9699453551912568,
          "max_drawdown": -0.004647547062930579,
          "sessions": 366,
          "sharpe_canonical": 14.51122569517575
        },
        "2025": {
          "ann_return_geometric": 0.014867340316408795,
          "annualized_turnover_units": 121.77235495863125,
          "invested_fraction": 0.8958904109589041,
          "max_drawdown": -0.012975007497208035,
          "sessions": 365,
          "sharpe_canonical": 2.6559051106069522
        },
        "2026": {
          "ann_return_geometric": -0.014135136414585303,
          "annualized_turnover_units": 164.71657111199923,
          "invested_fraction": 0.6959706959706959,
          "max_drawdown": -0.02240656116212436,
          "sessions": 273,
          "sharpe_canonical": -2.4925759553956235
        }
      }
    }
  },
  "portfolio": {
    "always_on": {
      "book": "PORTFOLIO_always_on",
      "bootstrap": {
        "full": {
          "ann_return_arithmetic_ci_95": [
            0.06484968316494528,
            0.18702982063311846
          ],
          "ann_return_geometric_ci_95": [
            0.06693566342508912,
            0.20540781330443553
          ],
          "block_days": 126,
          "n_bootstrap": 2000,
          "seed": 20261019,
          "sharpe_ci_95": [
            6.210862433367539,
            11.203805769779244
          ]
        },
        "post2022": {
          "ann_return_arithmetic_ci_95": [
            0.04094708867388154,
            0.10122411234338136
          ],
          "ann_return_geometric_ci_95": [
            0.041787480354539455,
            0.10648360435147172
          ],
          "block_days": 126,
          "n_bootstrap": 2000,
          "seed": 20261019,
          "sharpe_ci_95": [
            9.713792854751494,
            15.007876620118067
          ]
        },
        "test_oos": {
          "ann_return_arithmetic_ci_95": [
            0.015857235946379836,
            0.04497280540862729
          ],
          "ann_return_geometric_ci_95": [
            0.015978289077080078,
            0.04599161185907442
          ],
          "block_days": 63,
          "n_bootstrap": 2000,
          "seed": 20261019,
          "sharpe_ci_95": [
            4.998758311446822,
            15.464261565020033
          ]
        }
      },
      "cost_bps_per_unit": 3.0,
      "cost_sensitivity": {
        "1.5bp": {
          "ann_return_arithmetic": 0.12307405294222194,
          "ann_return_geometric": 0.13082116715431757,
          "annualized_cost_drag": 0.002770089439302947,
          "annualized_turnover_units": 18.467262928686317,
          "cost_bps_per_unit": 1.5,
          "max_drawdown": -0.016923390394390725,
          "sharpe_canonical": 8.32121940242756
        },
        "3.0bp": {
          "ann_return_arithmetic": 0.120303963502919,
          "ann_return_geometric": 0.12769409977315704,
          "annualized_cost_drag": 0.005540178878605894,
          "annualized_turnover_units": 18.467262928686317,
          "cost_bps_per_unit": 3.0,
          "max_drawdown": -0.017213345266197444,
          "sharpe_canonical": 8.135176202397444
        },
        "4.5bp": {
          "ann_return_arithmetic": 0.11753387406361604,
          "ann_return_geometric": 0.1245756168672445,
          "annualized_cost_drag": 0.008310268317908842,
          "annualized_turnover_units": 18.467262928686317,
          "cost_bps_per_unit": 4.5,
          "max_drawdown": -0.017545537620434537,
          "sharpe_canonical": 7.9478084238578806
        }
      },
      "entries_full_sample": 2,
      "exits_full_sample": 0,
      "leg_weight": 0.5,
      "look_ahead": false,
      "rule": "always_on",
      "rule_label": "Always-on carry",
      "samples": {
        "full": {
          "ann_return_arithmetic": 0.120303963502919,
          "ann_return_geometric": 0.12769409977315704,
          "ann_volatility": 0.014788120196765415,
          "annualized_cost_drag": 0.005540178878605894,
          "annualized_turnover_units": 18.467262928686317,
          "avg_gross_exposure": 2.0,
          "downside_deviation_annualized": 0.01294182069423682,
          "end": "2026-09-30",
          "invested_fraction": 1.0,
          "max_drawdown": -0.017213345266197444,
          "max_drawdown_recomputed": -0.017213345266197444,
          "position_entries": 2,
          "position_exits": 0,
          "profit_factor": 7.7408631599442055,
          "rebalance_days": 2464,
          "risk_free_rate_annual": 0.02,
          "sample": "full",
          "sessions": 2464,
          "sharpe_backtest_scale": 7.282473927735103,
          "sharpe_canonical": 8.135176202397444,
          "sortino_backtest_scale": 8.321402553592383,
          "sortino_canonical": 9.295752610487957,
          "start": "2020-01-02",
          "total_return": 1.2507490605895417
        },
        "post2022": {
          "ann_return_arithmetic": 0.0683315493462543,
          "ann_return_geometric": 0.07069742761785203,
          "ann_volatility": 0.005466018688175015,
          "annualized_cost_drag": 0.004332166182614438,
          "annualized_turnover_units": 14.440553942048126,
          "avg_gross_exposure": 2.0,
          "downside_deviation_annualized": 0.0026760951902644304,
          "end": "2026-09-30",
          "invested_fraction": 1.0,
          "max_drawdown": -0.00653462754284051,
          "max_drawdown_recomputed": -0.00653462754284051,
          "position_entries": 0,
          "position_exits": 0,
          "profit_factor": 9.405992087800554,
          "rebalance_days": 1369,
          "risk_free_rate_annual": 0.02,
          "sample": "post2022",
          "sessions": 1369,
          "sharpe_backtest_scale": 9.27501907879111,
          "sharpe_canonical": 12.501155455995837,
          "sortino_backtest_scale": 18.944553169217613,
          "sortino_canonical": 25.534050356221563,
          "start": "2023-01-01",
          "total_return": 0.2920242558243793
        },
        "test_oos": {
          "ann_return_arithmetic": 0.034526500993886815,
          "ann_return_geometric": 0.03512280994305561,
          "ann_volatility": 0.003098280421602726,
          "annualized_cost_drag": 0.004470130571070204,
          "annualized_turnover_units": 14.900435236900682,
          "avg_gross_exposure": 2.0,
          "downside_deviation_annualized": 0.0022811608681107373,
          "end": "2026-09-30",
          "invested_fraction": 1.0,
          "max_drawdown": -0.006534627542839289,
          "max_drawdown_recomputed": -0.006534627542839289,
          "position_entries": 0,
          "position_exits": 0,
          "profit_factor": 4.581199010570518,
          "rebalance_days": 638,
          "risk_free_rate_annual": 0.02,
          "sample": "test_oos",
          "sessions": 638,
          "sharpe_backtest_scale": 4.881033310481513,
          "sharpe_canonical": 11.143762440982155,
          "sortino_backtest_scale": 6.629435983434328,
          "sortino_canonical": 15.135495911992276,
          "start": "2025-01-01",
          "total_return": 0.06219678518059002
        },
        "train": {
          "ann_return_arithmetic": 0.18528134704673088,
          "ann_return_geometric": 0.20323965609904593,
          "ann_volatility": 0.020836270155148686,
          "annualized_cost_drag": 0.007050470550580602,
          "annualized_turnover_units": 23.501568501935342,
          "avg_gross_exposure": 2.0,
          "downside_deviation_annualized": 0.01767487323956173,
          "end": "2022-12-31",
          "invested_fraction": 1.0,
          "max_drawdown": -0.017213345266197444,
          "max_drawdown_recomputed": -0.017213345266197444,
          "position_entries": 2,
          "position_exits": 0,
          "profit_factor": 7.176712413049229,
          "rebalance_days": 1095,
          "risk_free_rate_annual": 0.02,
          "sample": "train",
          "sessions": 1095,
          "sharpe_backtest_scale": 8.794263787838585,
          "sharpe_canonical": 8.892251140300534,
          "sortino_backtest_scale": 10.36724018415589,
          "sortino_canonical": 10.482753937494444,
          "start": "2020-01-02",
          "total_return": 0.742033131687178
        },
        "val": {
          "ann_return_arithmetic": 0.09783581863327269,
          "ann_return_geometric": 0.10274388375148735,
          "ann_volatility": 0.006518313555745014,
          "annualized_cost_drag": 0.00421175403509764,
          "annualized_turnover_units": 14.039180116992133,
          "avg_gross_exposure": 2.0,
          "downside_deviation_annualized": 0.0031681160135460518,
          "end": "2024-12-31",
          "invested_fraction": 1.0,
          "max_drawdown": -0.0010388388997484288,
          "max_drawdown_recomputed": -0.0010388388997484288,
          "position_entries": 0,
          "position_exits": 0,
          "profit_factor": 15.368281452012619,
          "rebalance_days": 731,
          "risk_free_rate_annual": 0.02,
          "sample": "val",
          "sessions": 731,
          "sharpe_backtest_scale": 12.694063125969105,
          "sharpe_canonical": 15.009375936977383,
          "sortino_backtest_scale": 26.117693732709192,
          "sortino_canonical": 30.881387618051807,
          "start": "2023-01-01",
          "total_return": 0.21636995503117928
        }
      },
      "symbol": "BTC+ETH",
      "turnover_convention": "drift",
      "yearly": {
        "2020": {
          "ann_return_geometric": 0.22869724182488205,
          "annualized_turnover_units": 23.60318285052429,
          "invested_fraction": 1.0,
          "max_drawdown": -0.017213345266197444,
          "sessions": 365,
          "sharpe_canonical": 8.679555195934164
        },
        "2021": {
          "ann_return_geometric": 0.39255579330219836,
          "annualized_turnover_units": 26.78950152984929,
          "invested_fraction": 1.0,
          "max_drawdown": -0.0020008062922928227,
          "sessions": 365,
          "sharpe_canonical": 14.094629974589662
        },
        "2022": {
          "ann_return_geometric": 0.01811989217737353,
          "annualized_turnover_units": 20.112021125432452,
          "invested_fraction": 1.0,
          "max_drawdown": -0.008698842484932134,
          "sessions": 365,
          "sharpe_canonical": 2.552491059304977
        },
        "2023": {
          "ann_return_geometric": 0.07844450320705443,
          "annualized_turnover_units": 11.91304325181251,
          "invested_fraction": 1.0,
          "max_drawdown": -0.0008549731106097802,
          "sessions": 365,
          "sharpe_canonical": 14.58271739783793
        },
        "2024": {
          "ann_return_geometric": 0.12752213025712256,
          "annualized_turnover_units": 16.159507865053786,
          "invested_fraction": 1.0,
          "max_drawdown": -0.0010388388997486508,
          "sessions": 366,
          "sharpe_canonical": 16.117653065929144
        },
        "2025": {
          "ann_return_geometric": 0.04636562973164415,
          "annualized_turnover_units": 15.655171688073883,
          "invested_fraction": 1.0,
          "max_drawdown": -0.0012097385316378606,
          "sessions": 365,
          "sharpe_canonical": 15.149602474520103
        },
        "2026": {
          "ann_return_geometric": 0.02027969607587976,
          "annualized_turnover_units": 13.891355366284497,
          "invested_fraction": 1.0,
          "max_drawdown": -0.006534627542840621,
          "sessions": 273,
          "sharpe_canonical": 6.516628648230736
        }
      }
    },
    "funding_positive_lagged": {
      "book": "PORTFOLIO_funding_positive_lagged",
      "bootstrap": {
        "full": {
          "ann_return_arithmetic_ci_95": [
            0.03993022307370233,
            0.17027236250017938
          ],
          "ann_return_geometric_ci_95": [
            0.04068907269194232,
            0.1853985534020296
          ],
          "block_days": 126,
          "n_bootstrap": 2000,
          "seed": 20261019,
          "sharpe_ci_95": [
            3.788361987328271,
            9.45943330300998
          ]
        },
        "post2022": {
          "ann_return_arithmetic_ci_95": [
            0.01095322431744497,
            0.08773254551328577
          ],
          "ann_return_geometric_ci_95": [
            0.011001309509669672,
            0.0916507339599457
          ],
          "block_days": 126,
          "n_bootstrap": 2000,
          "seed": 20261019,
          "sharpe_ci_95": [
            2.0053212382087318,
            11.610226380524905
          ]
        },
        "test_oos": {
          "ann_return_arithmetic_ci_95": [
            -0.029378778075852024,
            0.02643840900885079
          ],
          "ann_return_geometric_ci_95": [
            -0.028965129136515992,
            0.026781400578929585
          ],
          "block_days": 63,
          "n_bootstrap": 2000,
          "seed": 20261019,
          "sharpe_ci_95": [
            -5.761977251190548,
            6.449059812606579
          ]
        }
      },
      "cost_bps_per_unit": 3.0,
      "cost_sensitivity": {
        "1.5bp": {
          "ann_return_arithmetic": 0.11482641590936901,
          "ann_return_geometric": 0.12153610464291242,
          "annualized_cost_drag": 0.014543956171971269,
          "annualized_turnover_units": 96.9597078131418,
          "cost_bps_per_unit": 1.5,
          "max_drawdown": -0.014650405696223223,
          "sharpe_canonical": 7.768877513142397
        },
        "3.0bp": {
          "ann_return_arithmetic": 0.10028245973739773,
          "ann_return_geometric": 0.10534031886718953,
          "annualized_cost_drag": 0.029087912343942538,
          "annualized_turnover_units": 96.9597078131418,
          "cost_bps_per_unit": 3.0,
          "max_drawdown": -0.02659446105343266,
          "sharpe_canonical": 6.596559909105592
        },
        "4.5bp": {
          "ann_return_arithmetic": 0.08573850356542644,
          "ann_return_geometric": 0.08937565695693839,
          "annualized_cost_drag": 0.04363186851591381,
          "annualized_turnover_units": 96.9597078131418,
          "cost_bps_per_unit": 4.5,
          "max_drawdown": -0.05296299782247249,
          "sharpe_canonical": 5.4481938206471305
        }
      },
      "entries_full_sample": 275,
      "exits_full_sample": 273,
      "leg_weight": 0.5,
      "look_ahead": false,
      "rule": "funding_positive_lagged",
      "rule_label": "Funding-positive only (previous-day signal, implementable)",
      "samples": {
        "full": {
          "ann_return_arithmetic": 0.10028245973739773,
          "ann_return_geometric": 0.10534031886718953,
          "ann_volatility": 0.015202235880397656,
          "annualized_cost_drag": 0.029087912343942538,
          "annualized_turnover_units": 96.9597078131418,
          "avg_gross_exposure": 1.7585227272727273,
          "downside_deviation_annualized": 0.010780481822342773,
          "end": "2026-09-30",
          "invested_fraction": 0.9460227272727273,
          "max_drawdown": -0.02659446105343266,
          "max_drawdown_recomputed": -0.02659446105343266,
          "position_entries": 275,
          "position_exits": 273,
          "profit_factor": 4.280513628346025,
          "rebalance_days": 2413,
          "risk_free_rate_annual": 0.02,
          "sample": "full",
          "sessions": 2464,
          "sharpe_backtest_scale": 5.613668906244943,
          "sharpe_canonical": 6.596559909105592,
          "sortino_backtest_scale": 7.9161878173496785,
          "sortino_canonical": 9.302224278098613,
          "start": "2020-01-02",
          "total_return": 0.9662008141477516
        },
        "post2022": {
          "ann_return_arithmetic": 0.0474603919526098,
          "ann_return_geometric": 0.04857905751574387,
          "ann_volatility": 0.0065366397709032175,
          "annualized_cost_drag": 0.026215533149916335,
          "annualized_turnover_units": 87.38511049972112,
          "avg_gross_exposure": 1.7786705624543462,
          "downside_deviation_annualized": 0.0036399801629127546,
          "end": "2026-09-30",
          "invested_fraction": 0.9503287070854638,
          "max_drawdown": -0.02659446105343144,
          "max_drawdown_recomputed": -0.02659446105343144,
          "position_entries": 140,
          "position_exits": 140,
          "profit_factor": 2.9741533265760958,
          "rebalance_days": 1341,
          "risk_free_rate_annual": 0.02,
          "sample": "post2022",
          "sessions": 1369,
          "sharpe_backtest_scale": 4.3721328568477755,
          "sharpe_canonical": 7.260671172958309,
          "sortino_backtest_scale": 7.851432215738939,
          "sortino_canonical": 13.038640275069918,
          "start": "2023-01-01",
          "total_return": 0.19472660231199734
        },
        "test_oos": {
          "ann_return_arithmetic": 0.0052916506169113885,
          "ann_return_geometric": 0.005294594808492592,
          "ann_volatility": 0.004690567881355473,
          "annualized_cost_drag": 0.03624397039937078,
          "annualized_turnover_units": 120.81323466456928,
          "avg_gross_exposure": 1.6598746081504703,
          "downside_deviation_annualized": 0.0036061442898563116,
          "end": "2026-09-30",
          "invested_fraction": 0.9122257053291536,
          "max_drawdown": -0.026594461053432328,
          "max_drawdown_recomputed": -0.026594461053432328,
          "position_entries": 95,
          "position_exits": 95,
          "profit_factor": 1.1640578756789477,
          "rebalance_days": 613,
          "risk_free_rate_annual": 0.02,
          "sample": "test_oos",
          "sessions": 638,
          "sharpe_backtest_scale": -3.1351012422099016,
          "sharpe_canonical": 1.128147113688549,
          "sortino_backtest_scale": -4.077874873967772,
          "sortino_canonical": 1.4673984709364574,
          "start": "2025-01-01",
          "total_return": 0.009272978011505062
        },
        "train": {
          "ann_return_arithmetic": 0.1663221043012102,
          "ann_return_geometric": 0.18064621510461643,
          "ann_volatility": 0.02110344397777573,
          "annualized_cost_drag": 0.032679042130811825,
          "annualized_turnover_units": 108.93014043603944,
          "avg_gross_exposure": 1.7333333333333334,
          "downside_deviation_annualized": 0.015062157196207076,
          "end": "2022-12-31",
          "invested_fraction": 0.9406392694063926,
          "max_drawdown": -0.026049549193389976,
          "max_drawdown_recomputed": -0.026049549193389976,
          "position_entries": 135,
          "position_exits": 133,
          "profit_factor": 5.294296043320935,
          "rebalance_days": 1072,
          "risk_free_rate_annual": 0.02,
          "sample": "train",
          "sessions": 1095,
          "sharpe_backtest_scale": 7.612322200764706,
          "sharpe_canonical": 7.881277789367736,
          "sortino_backtest_scale": 10.665551621322214,
          "sortino_canonical": 11.042382716805871,
          "start": "2020-01-02",
          "total_return": 0.6457328482874825
        },
        "val": {
          "ann_return_arithmetic": 0.08426430025927956,
          "ann_return_geometric": 0.08787709972546165,
          "ann_volatility": 0.007273103182179638,
          "annualized_cost_drag": 0.01746294359430493,
          "annualized_turnover_units": 58.20981198101644,
          "avg_gross_exposure": 1.8823529411764706,
          "downside_deviation_annualized": 0.0036966050365012807,
          "end": "2024-12-31",
          "invested_fraction": 0.9835841313269493,
          "max_drawdown": -0.00800954354080008,
          "max_drawdown_recomputed": -0.00800954354080008,
          "position_entries": 45,
          "position_exits": 45,
          "profit_factor": 5.9943321860851855,
          "rebalance_days": 728,
          "risk_free_rate_annual": 0.02,
          "sample": "val",
          "sessions": 731,
          "sharpe_backtest_scale": 9.332618832051262,
          "sharpe_canonical": 11.585742447012395,
          "sortino_backtest_scale": 18.362010291936723,
          "sortino_canonical": 22.795050979812828,
          "start": "2023-01-01",
          "total_return": 0.18374971721315214
        }
      },
      "symbol": "BTC+ETH",
      "turnover_convention": "drift",
      "yearly": {
        "2020": {
          "ann_return_geometric": 0.21992326465674372,
          "annualized_turnover_units": 69.78449957293913,
          "invested_fraction": 0.989041095890411,
          "max_drawdown": -0.015887532500741264,
          "sessions": 365,
          "sharpe_canonical": 8.348266344169115
        },
        "2021": {
          "ann_return_geometric": 0.3781627009643407,
          "annualized_turnover_units": 67.00559706282385,
          "invested_fraction": 0.9753424657534246,
          "max_drawdown": -0.0062991446724360856,
          "sessions": 365,
          "sharpe_canonical": 13.468765585763142
        },
        "2022": {
          "ann_return_geometric": -0.02112703951444661,
          "annualized_turnover_units": 190.0003246723553,
          "invested_fraction": 0.8575342465753425,
          "max_drawdown": -0.026049549193389754,
          "sessions": 365,
          "sharpe_canonical": -3.5874870513366623
        },
        "2023": {
          "ann_return_geometric": 0.0590983063898618,
          "annualized_turnover_units": 69.24391200026875,
          "invested_fraction": 0.9808219178082191,
          "max_drawdown": -0.007667893240093315,
          "sessions": 365,
          "sharpe_canonical": 9.295567525489785
        },
        "2024": {
          "ann_return_geometric": 0.11735604516277554,
          "annualized_turnover_units": 47.20585977602439,
          "invested_fraction": 0.9863387978142076,
          "max_drawdown": -0.008009543540799968,
          "sessions": 366,
          "sharpe_canonical": 13.900836636986027
        },
        "2025": {
          "ann_return_geometric": 0.020986399042278725,
          "annualized_turnover_units": 97.96105083090252,
          "invested_fraction": 0.9808219178082191,
          "max_drawdown": -0.01231411848430497,
          "sessions": 365,
          "sharpe_canonical": 4.850847315842541
        },
        "2026": {
          "ann_return_geometric": -0.015309165410428816,
          "annualized_turnover_units": 151.3665207425486,
          "invested_fraction": 0.8205128205128205,
          "max_drawdown": -0.026594461053432328,
          "sessions": 273,
          "sharpe_canonical": -3.088572386974803
        }
      }
    },
    "funding_positive_sameday": {
      "book": "PORTFOLIO_funding_positive_sameday",
      "bootstrap": {
        "full": {
          "ann_return_arithmetic_ci_95": [
            0.04721296799458369,
            0.17840384377082708
          ],
          "ann_return_geometric_ci_95": [
            0.048296979125357874,
            0.19509278835781937
          ],
          "block_days": 126,
          "n_bootstrap": 2000,
          "seed": 20261019,
          "sharpe_ci_95": [
            5.355899344858051,
            10.08130487065041
          ]
        },
        "post2022": {
          "ann_return_arithmetic_ci_95": [
            0.015503149521698713,
            0.08990614815430176
          ],
          "ann_return_geometric_ci_95": [
            0.015613144330067857,
            0.0940312711053779
          ],
          "block_days": 126,
          "n_bootstrap": 2000,
          "seed": 20261019,
          "sharpe_ci_95": [
            2.9243938780624563,
            12.01631859969699
          ]
        },
        "test_oos": {
          "ann_return_arithmetic_ci_95": [
            -0.022119449914324615,
            0.028444423372064317
          ],
          "ann_return_geometric_ci_95": [
            -0.021887685262860303,
            0.028844619713153007
          ],
          "block_days": 63,
          "n_bootstrap": 2000,
          "seed": 20261019,
          "sharpe_ci_95": [
            -4.551618913362771,
            7.157864297644786
          ]
        }
      },
      "cost_bps_per_unit": 3.0,
      "cost_sensitivity": {
        "1.5bp": {
          "ann_return_arithmetic": 0.12252026703373727,
          "ann_return_geometric": 0.13021471307037658,
          "annualized_cost_drag": 0.01451812337440577,
          "annualized_turnover_units": 96.78748916270514,
          "cost_bps_per_unit": 1.5,
          "max_drawdown": -0.00879170053722722,
          "sharpe_canonical": 9.015569579113011
        },
        "3.0bp": {
          "ann_return_arithmetic": 0.10800214365933147,
          "ann_return_geometric": 0.11392306271560937,
          "annualized_cost_drag": 0.02903624674881154,
          "annualized_turnover_units": 96.78748916270514,
          "cost_bps_per_unit": 3.0,
          "max_drawdown": -0.022058153706212558,
          "sharpe_canonical": 7.700593065862711
        },
        "4.5bp": {
          "ann_return_arithmetic": 0.09348402028492571,
          "ann_return_geometric": 0.09786347794644734,
          "annualized_cost_drag": 0.04355437012321731,
          "annualized_turnover_units": 96.78748916270514,
          "cost_bps_per_unit": 4.5,
          "max_drawdown": -0.038584340247629245,
          "sharpe_canonical": 6.41112071815327
        }
      },
      "entries_full_sample": 275,
      "exits_full_sample": 273,
      "leg_weight": 0.5,
      "look_ahead": true,
      "rule": "funding_positive_sameday",
      "rule_label": "Funding-positive only (same-day signal, pre-registered)",
      "samples": {
        "full": {
          "ann_return_arithmetic": 0.10800214365933147,
          "ann_return_geometric": 0.11392306271560937,
          "ann_volatility": 0.014025172182920927,
          "annualized_cost_drag": 0.02903624674881154,
          "annualized_turnover_units": 96.78748916270514,
          "avg_gross_exposure": 1.7593344155844155,
          "downside_deviation_annualized": 0.004315540946656484,
          "end": "2026-09-30",
          "invested_fraction": 0.9464285714285714,
          "max_drawdown": -0.022058153706212558,
          "max_drawdown_recomputed": -0.022058153706212558,
          "position_entries": 275,
          "position_exits": 273,
          "profit_factor": 5.3304208588782895,
          "rebalance_days": 2414,
          "risk_free_rate_annual": 0.02,
          "sample": "full",
          "sessions": 2464,
          "sharpe_backtest_scale": 6.69674935114049,
          "sharpe_canonical": 7.700593065862711,
          "sortino_backtest_scale": 21.763914159678492,
          "sortino_canonical": 25.02632809984283,
          "start": "2020-01-02",
          "total_return": 1.0715940907798989
        },
        "post2022": {
          "ann_return_arithmetic": 0.0507109845125655,
          "ann_return_geometric": 0.051993645521325904,
          "ann_volatility": 0.006389679745334504,
          "annualized_cost_drag": 0.0261916327909776,
          "annualized_turnover_units": 87.305442636592,
          "avg_gross_exposure": 1.7786705624543462,
          "downside_deviation_annualized": 0.003457008054848606,
          "end": "2026-09-30",
          "invested_fraction": 0.9503287070854638,
          "max_drawdown": -0.022058153706213335,
          "max_drawdown_recomputed": -0.022058153706213335,
          "position_entries": 140,
          "position_exits": 140,
          "profit_factor": 3.3020541809843706,
          "rebalance_days": 1341,
          "risk_free_rate_annual": 0.02,
          "sample": "post2022",
          "sessions": 1369,
          "sharpe_backtest_scale": 5.007081230430432,
          "sharpe_canonical": 7.936389073269703,
          "sortino_backtest_scale": 9.254721138544472,
          "sortino_canonical": 14.669038575551223,
          "start": "2023-01-01",
          "total_return": 0.20938412734667144
        },
        "test_oos": {
          "ann_return_arithmetic": 0.009541779360609143,
          "ann_return_geometric": 0.009577212655276668,
          "ann_volatility": 0.0044783664731054265,
          "annualized_cost_drag": 0.03619285350330643,
          "annualized_turnover_units": 120.64284501102144,
          "avg_gross_exposure": 1.6598746081504703,
          "downside_deviation_annualized": 0.003159556476958663,
          "end": "2026-09-30",
          "invested_fraction": 0.9122257053291536,
          "max_drawdown": -0.022058153706213113,
          "max_drawdown_recomputed": -0.022058153706213113,
          "position_entries": 95,
          "position_exits": 95,
          "profit_factor": 1.319287182688835,
          "rebalance_days": 613,
          "risk_free_rate_annual": 0.02,
          "sample": "test_oos",
          "sessions": 638,
          "sharpe_backtest_scale": -2.3273636508572455,
          "sharpe_canonical": 2.1306383517096585,
          "sortino_backtest_scale": -3.2988134318004456,
          "sortino_canonical": 3.0199743002517563,
          "start": "2025-01-01",
          "total_return": 0.016800352664903873
        },
        "train": {
          "ann_return_arithmetic": 0.17962917276611012,
          "ann_return_geometric": 0.1965021032917953,
          "ann_volatility": 0.019143706052843948,
          "annualized_cost_drag": 0.03259266365134548,
          "annualized_turnover_units": 108.64221217115161,
          "avg_gross_exposure": 1.735159817351598,
          "downside_deviation_annualized": 0.005080660469959611,
          "end": "2022-12-31",
          "invested_fraction": 0.9415525114155251,
          "max_drawdown": -0.013464298117546125,
          "max_drawdown_recomputed": -0.013464298117546125,
          "position_entries": 135,
          "position_exits": 133,
          "profit_factor": 7.284983342536339,
          "rebalance_days": 1073,
          "risk_free_rate_annual": 0.02,
          "sample": "train",
          "sessions": 1095,
          "sharpe_backtest_scale": 9.219850263297086,
          "sharpe_canonical": 9.38319739502189,
          "sortino_backtest_scale": 34.739991844642674,
          "sortino_canonical": 35.35547668028643,
          "start": "2020-01-02",
          "total_return": 0.7129330904357776
        },
        "val": {
          "ann_return_arithmetic": 0.08664252060962183,
          "ann_return_geometric": 0.0904675935428374,
          "ann_volatility": 0.00717003894388852,
          "annualized_cost_drag": 0.017462797203473105,
          "annualized_turnover_units": 58.209324011577024,
          "avg_gross_exposure": 1.8823529411764706,
          "downside_deviation_annualized": 0.003833094571830268,
          "end": "2024-12-31",
          "invested_fraction": 0.9835841313269493,
          "max_drawdown": -0.006741817363101088,
          "max_drawdown_recomputed": -0.006741817363101088,
          "position_entries": 45,
          "position_exits": 45,
          "profit_factor": 6.710685570035927,
          "rebalance_days": 728,
          "risk_free_rate_annual": 0.02,
          "sample": "val",
          "sessions": 731,
          "sharpe_backtest_scale": 9.828062873061715,
          "sharpe_canonical": 12.08396792369904,
          "sortino_backtest_scale": 18.383995547803497,
          "sortino_canonical": 22.603804572515624,
          "start": "2023-01-01",
          "total_return": 0.18940175834619755
        }
      },
      "symbol": "BTC+ETH",
      "turnover_convention": "drift",
      "yearly": {
        "2020": {
          "ann_return_geometric": 0.24262202633029184,
          "annualized_turnover_units": 69.50463696804886,
          "invested_fraction": 0.9917808219178083,
          "max_drawdown": -0.0037690949091978565,
          "sessions": 365,
          "sharpe_canonical": 11.52373126519735
        },
        "2021": {
          "ann_return_geometric": 0.3865322552078756,
          "annualized_turnover_units": 66.62973493452958,
          "invested_fraction": 0.9753424657534246,
          "max_drawdown": -0.004476336216355348,
          "sessions": 365,
          "sharpe_canonical": 13.884644354154444
        },
        "2022": {
          "ann_return_geometric": -0.005805458175134226,
          "annualized_turnover_units": 189.79226461087634,
          "invested_fraction": 0.8575342465753425,
          "max_drawdown": -0.013464298117545792,
          "sessions": 365,
          "sharpe_canonical": -1.0320640257123035
        },
        "2023": {
          "ann_return_geometric": 0.06241152547792117,
          "annualized_turnover_units": 69.20683252923183,
          "invested_fraction": 0.9808219178082191,
          "max_drawdown": -0.006741817363101088,
          "sessions": 365,
          "sharpe_canonical": 10.02713352421894
        },
        "2024": {
          "ann_return_geometric": 0.11918485645877852,
          "annualized_turnover_units": 47.24186333140214,
          "invested_fraction": 0.9863387978142076,
          "max_drawdown": -0.00665704291551894,
          "sessions": 366,
          "sharpe_canonical": 14.224658640040106
        },
        "2025": {
          "ann_return_geometric": 0.023470792396115936,
          "annualized_turnover_units": 98.08969346730596,
          "invested_fraction": 0.9808219178082191,
          "max_drawdown": -0.010414698724264704,
          "sessions": 365,
          "sharpe_canonical": 5.581886892018942
        },
        "2026": {
          "ann_return_geometric": -0.008704249730655977,
          "annualized_turnover_units": 150.79632601269228,
          "invested_fraction": 0.8205128205128205,
          "max_drawdown": -0.02205815370621267,
          "sessions": 273,
          "sharpe_canonical": -1.8519076759185342
        }
      }
    }
  },
  "promotion_gates": {
    "always_on": {
      "gate_pass_note": "The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.",
      "min_pooled_oos_trades": 100,
      "net_oos_sharpe_canonical_365": 9.208538388105994,
      "net_oos_sharpe_min": 0.9,
      "pooled_oos_position_round_trips": 0,
      "pooled_oos_rebalance_days_repo_convention": 1276,
      "pooled_oos_settlement_observations": 3828,
      "promotion_gate_pass": false,
      "sharpe_criterion_pass": true,
      "trade_count_criterion_pass": false
    },
    "funding_positive_lagged": {
      "gate_pass_note": "The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.",
      "min_pooled_oos_trades": 100,
      "net_oos_sharpe_canonical_365": 0.9768777369185657,
      "net_oos_sharpe_min": 0.9,
      "pooled_oos_position_round_trips": 95,
      "pooled_oos_rebalance_days_repo_convention": 1154,
      "pooled_oos_settlement_observations": 3828,
      "promotion_gate_pass": false,
      "sharpe_criterion_pass": true,
      "trade_count_criterion_pass": false
    },
    "funding_positive_sameday": {
      "gate_pass_note": "The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.",
      "min_pooled_oos_trades": 100,
      "net_oos_sharpe_canonical_365": 1.7616431492349476,
      "net_oos_sharpe_min": 0.9,
      "pooled_oos_position_round_trips": 95,
      "pooled_oos_rebalance_days_repo_convention": 1154,
      "pooled_oos_settlement_observations": 3828,
      "promotion_gate_pass": false,
      "sharpe_criterion_pass": true,
      "trade_count_criterion_pass": false
    }
  },
  "reconciliation_with_cost_screen": {
    "crypto_annual_turnover_units": 18.170996694920085,
    "crypto_convention": {
      "charges_position_transitions": true,
      "periods_per_year": 365
    },
    "crypto_cost_drag_3bp": 0.005451299008476025,
    "crypto_gross_annualized_signal": 0.13395684247803485,
    "crypto_net_annualized_return_3bp": 0.12779436778666153,
    "same_gross_series": true,
    "same_turnover_series": true,
    "screen_annual_turnover_units": 12.545455252383181,
    "screen_break_even_cost_bps": 69.18529035508527,
    "screen_convention": {
      "charges_position_transitions": false,
      "periods_per_year": 252
    },
    "screen_cost_drag_3bp": 0.0037636365757149543,
    "screen_gross_annualized_signal": 0.09067168827979422,
    "screen_net_annualized_return_3bp": 0.08657600471768223,
    "source": "research/cost_admissibility_screen.py:build_cryptofunding_candidate"
  },
  "robustness": {
    "capacity": {
      "BTCUSDT": {
        "capacity_usdt": {
          "perp_drift_median": 2897148749.579035,
          "perp_drift_worst_day": 97314906.80315216,
          "perp_parity_median": 618958794155.4698,
          "perp_parity_worst_day": 20790757594.681038,
          "spot_drift_median": 406585254.2949264,
          "spot_drift_worst_day": 28793225.92772443,
          "spot_parity_median": 86864548724.44835,
          "spot_parity_worst_day": 6151503405.774345
        },
        "entry_capacity_usdt": {
          "perp_median": 121964902.1823626,
          "perp_worst_day": 4096787.6056957003,
          "spot_median": 17116529.06191896,
          "spot_worst_day": 1212144.5211606228
        },
        "mean_daily_turnover_units_per_unit_weight": {
          "drift": 0.04209825339485399,
          "parity": 0.00019704850037517604
        },
        "perp": {
          "days": 2465,
          "median_daily_quote_volume": 12196490218.23626,
          "min_daily_quote_volume": 409678760.56957
        },
        "spot": {
          "days": 2465,
          "median_daily_quote_volume": 1711652906.191896,
          "min_daily_quote_volume": 121214452.11606228
        }
      },
      "ETHUSDT": {
        "capacity_usdt": {
          "perp_drift_median": 1139410229.0308626,
          "perp_drift_worst_day": 7889467.2019995935,
          "perp_parity_median": 267889684213.73538,
          "perp_parity_worst_day": 1854913027.3790495,
          "spot_drift_median": 161309088.8003487,
          "spot_drift_worst_day": 3297841.864615048,
          "spot_parity_median": 37925796836.39151,
          "spot_parity_worst_day": 775364125.3949386
        },
        "entry_capacity_usdt": {
          "perp_median": 65480597.57196981,
          "perp_worst_day": 453398.62127690006,
          "spot_median": 9270248.1154842,
          "spot_worst_day": 189523.185320643
        },
        "mean_daily_turnover_units_per_unit_weight": {
          "drift": 0.05746885178279031,
          "parity": 0.0002444312022098104
        },
        "perp": {
          "days": 2465,
          "median_daily_quote_volume": 6548059757.19698,
          "min_daily_quote_volume": 45339862.12769
        },
        "spot": {
          "days": 2465,
          "median_daily_quote_volume": 927024811.54842,
          "min_daily_quote_volume": 18952318.5320643
        }
      },
      "participation_assumption": "1% of the daily quote volume of the traded leg; the capacity is the notional whose daily rebalance trade stays inside that budget. The one-time entry is bounded by the same 1% budget."
    },
    "convergence_sensitivity": {
      "always_on": {
        "gross_funding_only_ann": 0.13001434199988826,
        "gross_funding_only_max_drawdown": -0.008568902201327777,
        "gross_funding_only_sharpe": 10.00266750061503,
        "gross_with_convergence_ann": 0.12769409977315704,
        "note": "The basis-convergence term is a near zero-sum change of the price difference between the two legs; crediting it or not moves the annualized net return by well under one percentage point, so the result does not depend on that accounting."
      },
      "funding_positive_lagged": {
        "gross_funding_only_ann": 0.10447111501480433,
        "gross_funding_only_max_drawdown": -0.03038727102596306,
        "gross_funding_only_sharpe": 7.6919430528546195,
        "gross_with_convergence_ann": 0.10534031886718953,
        "note": "The basis-convergence term is a near zero-sum change of the price difference between the two legs; crediting it or not moves the annualized net return by well under one percentage point, so the result does not depend on that accounting."
      },
      "funding_positive_sameday": {
        "gross_funding_only_ann": 0.10903202122496713,
        "gross_funding_only_max_drawdown": -0.024274538555422054,
        "gross_funding_only_sharpe": 8.129422352810755,
        "gross_with_convergence_ann": 0.11392306271560937,
        "note": "The basis-convergence term is a near zero-sum change of the price difference between the two legs; crediting it or not moves the annualized net return by well under one percentage point, so the result does not depend on that accounting."
      }
    },
    "cost_sensitivity_portfolio": {
      "always_on": {
        "1.5bp": {
          "ann_return_arithmetic": 0.12307405294222194,
          "ann_return_geometric": 0.13082116715431757,
          "annualized_cost_drag": 0.002770089439302947,
          "annualized_turnover_units": 18.467262928686317,
          "cost_bps_per_unit": 1.5,
          "max_drawdown": -0.016923390394390725,
          "sharpe_canonical": 8.32121940242756
        },
        "3.0bp": {
          "ann_return_arithmetic": 0.120303963502919,
          "ann_return_geometric": 0.12769409977315704,
          "annualized_cost_drag": 0.005540178878605894,
          "annualized_turnover_units": 18.467262928686317,
          "cost_bps_per_unit": 3.0,
          "max_drawdown": -0.017213345266197444,
          "sharpe_canonical": 8.135176202397444
        },
        "4.5bp": {
          "ann_return_arithmetic": 0.11753387406361604,
          "ann_return_geometric": 0.1245756168672445,
          "annualized_cost_drag": 0.008310268317908842,
          "annualized_turnover_units": 18.467262928686317,
          "cost_bps_per_unit": 4.5,
          "max_drawdown": -0.017545537620434537,
          "sharpe_canonical": 7.9478084238578806
        }
      },
      "funding_positive_lagged": {
        "1.5bp": {
          "ann_return_arithmetic": 0.11482641590936901,
          "ann_return_geometric": 0.12153610464291242,
          "annualized_cost_drag": 0.014543956171971269,
          "annualized_turnover_units": 96.9597078131418,
          "cost_bps_per_unit": 1.5,
          "max_drawdown": -0.014650405696223223,
          "sharpe_canonical": 7.768877513142397
        },
        "3.0bp": {
          "ann_return_arithmetic": 0.10028245973739773,
          "ann_return_geometric": 0.10534031886718953,
          "annualized_cost_drag": 0.029087912343942538,
          "annualized_turnover_units": 96.9597078131418,
          "cost_bps_per_unit": 3.0,
          "max_drawdown": -0.02659446105343266,
          "sharpe_canonical": 6.596559909105592
        },
        "4.5bp": {
          "ann_return_arithmetic": 0.08573850356542644,
          "ann_return_geometric": 0.08937565695693839,
          "annualized_cost_drag": 0.04363186851591381,
          "annualized_turnover_units": 96.9597078131418,
          "cost_bps_per_unit": 4.5,
          "max_drawdown": -0.05296299782247249,
          "sharpe_canonical": 5.4481938206471305
        }
      },
      "funding_positive_sameday": {
        "1.5bp": {
          "ann_return_arithmetic": 0.12252026703373727,
          "ann_return_geometric": 0.13021471307037658,
          "annualized_cost_drag": 0.01451812337440577,
          "annualized_turnover_units": 96.78748916270514,
          "cost_bps_per_unit": 1.5,
          "max_drawdown": -0.00879170053722722,
          "sharpe_canonical": 9.015569579113011
        },
        "3.0bp": {
          "ann_return_arithmetic": 0.10800214365933147,
          "ann_return_geometric": 0.11392306271560937,
          "annualized_cost_drag": 0.02903624674881154,
          "annualized_turnover_units": 96.78748916270514,
          "cost_bps_per_unit": 3.0,
          "max_drawdown": -0.022058153706212558,
          "sharpe_canonical": 7.700593065862711
        },
        "4.5bp": {
          "ann_return_arithmetic": 0.09348402028492571,
          "ann_return_geometric": 0.09786347794644734,
          "annualized_cost_drag": 0.04355437012321731,
          "annualized_turnover_units": 96.78748916270514,
          "cost_bps_per_unit": 4.5,
          "max_drawdown": -0.038584340247629245,
          "sharpe_canonical": 6.41112071815327
        }
      }
    },
    "funding_rounding_and_settlement": {
      "late_entry": {
        "ann_return_geometric": 0.08212703056599291,
        "note": "Position established after the 00:00 UTC settlement of the day.",
        "settlements_captured": 2,
        "sharpe_canonical": 6.845089884467944
      },
      "published_rate_decimals": 8,
      "worst_case_rounding": {
        "ann_return_geometric": 0.12768862477315704,
        "annual_return_impact": 5.475000000000001e-06,
        "daily_return_impact": 1.5000000000000002e-08,
        "note": "The exchange rounds each funding payment to 1e-8 USDT of notional; the worst case (always against the trader) is 0.5e-8 per settlement, 3 settlements a day."
      }
    },
    "return_decomposition": {
      "BTCUSDT": {
        "basis_annualized": -0.0013609160991511049,
        "basis_annualized_volatility": 0.006567285916915722,
        "funding_annualized": 0.11730968457792205,
        "funding_annualized_volatility": 0.011050819796107978,
        "funding_positive_day_fraction": 0.8786525974025974,
        "gross_annualized": 0.11594876847877096,
        "gross_annualized_volatility": 0.013480661847230489
      },
      "ETHUSDT": {
        "basis_annualized": -0.002681953460039381,
        "basis_annualized_volatility": 0.009472447088827902,
        "funding_annualized": 0.13842146974431818,
        "funding_annualized_volatility": 0.014255627379724556,
        "funding_positive_day_fraction": 0.8806818181818182,
        "gross_annualized": 0.1357395162842788,
        "gross_annualized_volatility": 0.017949770466895307
      }
    },
    "turnover_convention_sensitivity": {
      "always_on": {
        "drift": {
          "ann_return_geometric": 0.12769409977315704,
          "annualized_cost_drag": 0.005540178878605894,
          "annualized_turnover_units": 18.467262928686317,
          "note": "Constant-notional rebalance of both legs every day (the cost screen's convention): w*(|spot_return| + |perp_return|) while the pair is held.",
          "sharpe_canonical": 8.135176202397444
        },
        "fixed_quantity": {
          "ann_return_geometric": 0.1338560283913044,
          "annualized_cost_drag": 8.887987012987013e-05,
          "annualized_turnover_units": 0.2962662337662338,
          "note": "Fixed coin quantity on both legs (no daily rebalancing at all): the pair is entered and exited only.",
          "sharpe_canonical": 8.497536395613542
        },
        "parity": {
          "ann_return_geometric": 0.13382863282240387,
          "annualized_cost_drag": 0.00011305088384639818,
          "annualized_turnover_units": 0.376836279487994,
          "note": "Equal-notional maintenance: only the basis drift is traded, w*|spot_return - perp_return| while the pair is held.",
          "sharpe_canonical": 8.49594634136537
        }
      },
      "funding_positive_lagged": {
        "drift": {
          "ann_return_geometric": 0.10534031886718953,
          "annualized_cost_drag": 0.029087912343942538,
          "annualized_turnover_units": 96.9597078131418,
          "note": "Constant-notional rebalance of both legs every day (the cost screen's convention): w*(|spot_return| + |perp_return|) while the pair is held.",
          "sharpe_canonical": 6.596559909105592
        },
        "fixed_quantity": {
          "ann_return_geometric": 0.11058421205587288,
          "annualized_cost_drag": 0.024353084415584415,
          "annualized_turnover_units": 81.17694805194806,
          "note": "Fixed coin quantity on both legs (no daily rebalancing at all): the pair is entered and exited only.",
          "sharpe_canonical": 6.890730051233235
        },
        "parity": {
          "ann_return_geometric": 0.11055994713453576,
          "annualized_cost_drag": 0.02437494231104837,
          "annualized_turnover_units": 81.24980770349458,
          "note": "Equal-notional maintenance: only the basis drift is traded, w*|spot_return - perp_return| while the pair is held.",
          "sharpe_canonical": 6.889376379713542
        }
      },
      "funding_positive_sameday": {
        "drift": {
          "ann_return_geometric": 0.11392306271560937,
          "annualized_cost_drag": 0.02903624674881154,
          "annualized_turnover_units": 96.78748916270514,
          "note": "Constant-notional rebalance of both legs every day (the cost screen's convention): w*(|spot_return| + |perp_return|) while the pair is held.",
          "sharpe_canonical": 7.700593065862711
        },
        "fixed_quantity": {
          "ann_return_geometric": 0.11914941148912739,
          "annualized_cost_drag": 0.024353084415584415,
          "annualized_turnover_units": 81.17694805194806,
          "note": "Fixed coin quantity on both legs (no daily rebalancing at all): the pair is entered and exited only.",
          "sharpe_canonical": 7.998590274902295
        },
        "parity": {
          "ann_return_geometric": 0.11912539196527172,
          "annualized_cost_drag": 0.02437456254894098,
          "annualized_turnover_units": 81.24854182980327,
          "note": "Equal-notional maintenance: only the basis drift is traded, w*|spot_return - perp_return| while the pair is held.",
          "sharpe_canonical": 7.997429313210894
        }
      }
    }
  }
}
```
