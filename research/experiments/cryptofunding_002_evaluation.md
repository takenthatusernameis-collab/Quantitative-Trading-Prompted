# Experiment: cryptofunding_002_evaluation — realistic execution and capital-cost model (Cycle 892)

Hypothesis: `research/hypotheses/cryptofunding_001.md`

This record supersedes the Cycle 891 evaluation (`research/experiments/cryptofunding_002_evaluation.md`, previous revision), which measured the net capture of the carry with the repository's flat 3 bp/unit turnover cost alone: no charge for the capital the book ties up in the spot leg and no venue-specific fee schedule. Cycle 892 measures the same three pre-registered rules under a realistic execution and capital-cost model and re-evaluates the promotion gates under it. The Cycle 891 numbers (flat model, 365-day annualization, charged entry/exit transitions, previous-day funding signal) are unchanged and are reported below as the flat-model rows.

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
* **Trial count:** 6 candidate configurations (3 rules x 2 symbols); the BTC/ETH portfolio is an equal-weight combination of the two symbol books, not an additional configuration. The robustness rows and the cost-model rows (capital charge, venue fee schedule, turnover convention) are sensitivity analyses of the same configurations, not new trials.

## Cost models (Cycle 892)

The repository's flat model charges one number per unit of weight change and nothing for the capital the book ties up. Cycle 892 measures the same three pre-registered rules under a realistic execution and capital-cost model:

| Model | Trading cost | Capital charge | Source |
|---|---|---|---|
| `flat_3bp` | 3.0 bp per unit of weight change (both legs) | 0.00%/yr on the spot leg's notional | src/backtest/engine.py:get_cost_params (config/settings.yaml) |
| `flat_3bp_capital_rf` | 3.0 bp per unit of weight change (both legs) | 2.00%/yr on the spot leg's notional | src/backtest/engine.py:get_cost_params + get_risk_free_rate |
| `venue_taker` | spot 10.0 bp / perp 5.0 bp per unit of leg turnover | 0.00%/yr on the spot leg's notional | Binance published VIP 0 fee schedule (accessed 2026-10-20) |
| `venue_taker_slippage` | spot 12.0 bp / perp 7.0 bp per unit of leg turnover | 0.00%/yr on the spot leg's notional | Binance VIP 0 published spot taker 10 bp and USDⓈ-M perp taker 5 bp (accessed 2026-10-20) + the repository's 2 bp/unit slippage assumption |
| `venue_maker_slippage` | spot 12.0 bp / perp 4.0 bp per unit of leg turnover | 0.00%/yr on the spot leg's notional | Binance published VIP 0 fee schedule, maker (spot 10 bp, perp 2 bp, accessed 2026-10-20) + the repository's 2 bp/unit slippage assumption |
| `realistic_rf` **(headline)** | spot 12.0 bp / perp 7.0 bp per unit of leg turnover | 2.00%/yr on the spot leg's notional | Binance VIP 0 published spot taker 10 bp and USDⓈ-M perp taker 5 bp (accessed 2026-10-20) + the repository's 2 bp/unit slippage assumption + get_risk_free_rate() |
| `realistic_no_capital_charge` | spot 12.0 bp / perp 7.0 bp per unit of leg turnover | 0.00%/yr on the spot leg's notional | Binance VIP 0 published spot taker 10 bp and USDⓈ-M perp taker 5 bp (accessed 2026-10-20) + the repository's 2 bp/unit slippage assumption |
| `realistic_usdt_5pct` | spot 12.0 bp / perp 7.0 bp per unit of leg turnover | 5.00%/yr on the spot leg's notional | Binance VIP 0 published spot taker 10 bp and USDⓈ-M perp taker 5 bp (accessed 2026-10-20) + the repository's 2 bp/unit slippage assumption + 5% USDT-equivalent yield assumption |

### The venue fee schedule

**Binance VIP 0 (standard, published schedule)** (published schedule, accessed 2026-10-20):

| Leg | Maker | Taker |
|---|---|---|
| Spot | 10.0 bp | 10.0 bp |
| USDⓈ-M perp | 2.0 bp | 5.0 bp |

* Binance, 'VIP Program: Updates to Spot and Margin Trading Fees for VIP 3 - VIP 9 Users' (2024-10-07): Normal User maker 0.1000% / taker 0.1000% on spot.
* Binance futures fee explainer (support FAQ 360033544231): a Regular User's maker fee is 0.02% and taker fee 0.05% on USDⓈ-M futures.
* config/settings.yaml: default_slippage_bps (the repository's own slippage assumption).

The published fees are applied to the **leg weights that are actually traded**, and the repository's own slippage assumption (2.0 bp per unit of weight change) is added on top, because a fee schedule does not model execution slippage. Published schedule used as a documented assumption; no live fees are implied (the account-specific table is only visible after login). The BNB fee discount is not claimed.

### The capital charge

The charge is applied to the spot leg's notional (the cash the delta-neutral book ties up; the short perp leg is self-financing because its own proceeds are posted as its margin). The repository's backtest-baseline Sharpe/Sortino already subtract the 2% risk-free rate from the ratio's numerator while the return series does not pay it, so the backtest-scale metrics of a capital-charge row are computed with a zero risk-free rate (no double counting). The canonical gate convention (arithmetic_annualized_rf0) is unaffected either way.

| Sensitivity | Annual rate on the spot leg's notional |
|---|---|
| `none` | 0.00% |
| `repo_rf` | 2.00% |
| `usdt_5pct` | 5.00% |

The 0% row is the row in which the capital is free; the `repo_rf` row is the repository's own risk-free rate and is the **headline**; the `usdt_5pct` row is the opportunity cost of the locked cash at a stablecoin-equivalent lending yield (a documented assumption, not a quoted rate).

### Which model is the headline, and why

**Headline: `realistic_rf` under the `drift` turnover convention.** It is the conservative end of both cost axes at once: the *taker* fee schedule (the more expensive of the two published rates on the perp leg), the repository's slippage assumption on top of it, and the repository's risk-free rate as the charge for the capital the spot leg ties up. The cheaper corners - the maker schedule, no capital charge, a 5% yield - are reported as rows, and the flat model is reported unchanged so that the cost-model effect is isolated.

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

## Results under the cost models (portfolio, equal weight BTC/ETH)

Every pre-registered rule under every cost model, on every pre-registered sample. The rules and the symbols are the same as in the flat-model table above; only the cost model changes.

| Rule | Cost model | Sample | Ann. net (geo) | Sharpe (canonical) | Max DD | Turnover/yr | Fee drag/yr | Capital drag/yr |
|---|---|---|---|---|---|---|---|---|
| `always_on` | `flat_3bp` | full | +12.7694% | 8.135 | -1.7213% | 18.47 | +0.5540% | +0.0000% |
| `always_on` | `flat_3bp` | train | +20.3240% | 8.892 | -1.7213% | 23.50 | +0.7050% | +0.0000% |
| `always_on` | `flat_3bp` | val | +10.2744% | 15.009 | -0.1039% | 14.04 | +0.4212% | +0.0000% |
| `always_on` | `flat_3bp` | test_oos | +3.5123% | 11.144 | -0.6535% | 14.90 | +0.4470% | +0.0000% |
| `always_on` | `flat_3bp` | post2022 | +7.0697% | 12.501 | -0.6535% | 14.44 | +0.4332% | +0.0000% |
| `always_on` | `flat_3bp_capital_rf` | full | +10.5371% | 6.783 | -1.8354% | 18.47 | +0.5540% | +2.0000% |
| `always_on` | `flat_3bp_capital_rf` | train | +17.9425% | 7.932 | -1.8354% | 23.50 | +0.7050% | +2.0000% |
| `always_on` | `flat_3bp_capital_rf` | val | +8.0913% | 11.941 | -0.2204% | 14.04 | +0.4212% | +2.0000% |
| `always_on` | `flat_3bp_capital_rf` | test_oos | +1.4627% | 4.689 | -1.1856% | 14.90 | +0.4470% | +2.0000% |
| `always_on` | `flat_3bp_capital_rf` | post2022 | +4.9500% | 8.842 | -1.1856% | 14.44 | +0.4332% | +2.0000% |
| `always_on` | `venue_taker` | full | +11.8370% | 7.570 | -1.8206% | 18.47 | +1.3846% | +0.0000% |
| `always_on` | `venue_taker` | train | +19.0597% | 8.371 | -1.8206% | 23.50 | +1.7618% | +0.0000% |
| `always_on` | `venue_taker` | val | +9.5803% | 13.988 | -0.1161% | 14.04 | +1.0527% | +0.0000% |
| `always_on` | `venue_taker` | test_oos | +2.8207% | 8.815 | -0.8590% | 14.90 | +1.1174% | +0.0000% |
| `always_on` | `venue_taker` | post2022 | +6.3765% | 11.243 | -0.8590% | 14.44 | +1.0829% | +0.0000% |
| `always_on` | `venue_taker_slippage` | full | +11.4248% | 7.315 | -1.8649% | 18.47 | +1.7539% | +0.0000% |
| `always_on` | `venue_taker_slippage` | train | +18.5016% | 8.137 | -1.8649% | 23.50 | +2.2318% | +0.0000% |
| `always_on` | `venue_taker_slippage` | val | +9.2732% | 13.526 | -0.1267% | 14.04 | +1.3335% | +0.0000% |
| `always_on` | `venue_taker_slippage` | test_oos | +2.5147% | 7.778 | -0.9502% | 14.90 | +1.4154% | +0.0000% |
| `always_on` | `venue_taker_slippage` | post2022 | +6.0698% | 10.676 | -0.9502% | 14.44 | +1.3717% | +0.0000% |
| `always_on` | `venue_maker_slippage` | full | +11.7341% | 7.507 | -1.8315% | 18.47 | +1.4766% | +0.0000% |
| `always_on` | `venue_maker_slippage` | train | +18.9205% | 8.313 | -1.8315% | 23.50 | +1.8788% | +0.0000% |
| `always_on` | `venue_maker_slippage` | val | +9.5036% | 13.873 | -0.1174% | 14.04 | +1.1227% | +0.0000% |
| `always_on` | `venue_maker_slippage` | test_oos | +2.7442% | 8.556 | -0.8818% | 14.90 | +1.1918% | +0.0000% |
| `always_on` | `venue_maker_slippage` | post2022 | +6.2999% | 11.101 | -0.8818% | 14.44 | +1.1549% | +0.0000% |
| `always_on` | `realistic_rf` | full | +9.2190% | 5.964 | -2.1235% | 18.47 | +1.7539% | +2.0000% |
| `always_on` | `realistic_rf` | train | +16.1561% | 7.180 | -2.1235% | 23.50 | +2.2318% | +2.0000% |
| `always_on` | `realistic_rf` | val | +7.1099% | 10.477 | -0.3670% | 14.04 | +1.3335% | +2.0000% |
| `always_on` | `realistic_rf` | test_oos | +0.4849% | 1.516 | -1.5131% | 14.90 | +1.4154% | +2.0000% |
| `always_on` | `realistic_rf` | post2022 | +3.9697% | 7.054 | -1.5131% | 14.44 | +1.3717% | +2.0000% |
| `always_on` | `realistic_no_capital_charge` | full | +11.4248% | 7.315 | -1.8649% | 18.47 | +1.7539% | +0.0000% |
| `always_on` | `realistic_no_capital_charge` | train | +18.5016% | 8.137 | -1.8649% | 23.50 | +2.2318% | +0.0000% |
| `always_on` | `realistic_no_capital_charge` | val | +9.2732% | 13.526 | -0.1267% | 14.04 | +1.3335% | +0.0000% |
| `always_on` | `realistic_no_capital_charge` | test_oos | +2.5147% | 7.778 | -0.9502% | 14.90 | +1.4154% | +0.0000% |
| `always_on` | `realistic_no_capital_charge` | post2022 | +6.0698% | 10.676 | -0.9502% | 14.44 | +1.3717% | +0.0000% |
| `always_on` | `realistic_usdt_5pct` | full | +5.9917% | 3.938 | -4.6018% | 18.47 | +1.7539% | +5.0000% |
| `always_on` | `realistic_usdt_5pct` | train | +12.7244% | 5.744 | -4.6018% | 23.50 | +2.2318% | +5.0000% |
| `always_on` | `realistic_usdt_5pct` | val | +3.9447% | 5.902 | -0.7809% | 14.04 | +1.3335% | +5.0000% |
| `always_on` | `realistic_usdt_5pct` | test_oos | -2.4850% | -7.877 | -4.5436% | 14.90 | +1.4154% | +5.0000% |
| `always_on` | `realistic_usdt_5pct` | post2022 | +0.8972% | 1.620 | -4.5436% | 14.44 | +1.3717% | +5.0000% |
| `funding_positive_sameday` | `flat_3bp` | full | +11.3923% | 7.701 | -2.2058% | 96.79 | +2.9036% | +0.0000% |
| `funding_positive_sameday` | `flat_3bp` | train | +19.6502% | 9.383 | -1.3464% | 108.64 | +3.2593% | +0.0000% |
| `funding_positive_sameday` | `flat_3bp` | val | +9.0468% | 12.084 | -0.6742% | 58.21 | +1.7463% | +0.0000% |
| `funding_positive_sameday` | `flat_3bp` | test_oos | +0.9577% | 2.131 | -2.2058% | 120.64 | +3.6193% | +0.0000% |
| `funding_positive_sameday` | `flat_3bp` | post2022 | +5.1994% | 7.936 | -2.2058% | 87.31 | +2.6192% | +0.0000% |
| `funding_positive_sameday` | `flat_3bp_capital_rf` | full | +9.4503% | 6.484 | -2.6445% | 96.79 | +2.9036% | +1.7593% |
| `funding_positive_sameday` | `flat_3bp_capital_rf` | train | +17.5932% | 8.518 | -2.4353% | 108.64 | +3.2593% | +1.7352% |
| `funding_positive_sameday` | `flat_3bp_capital_rf` | val | +7.0138% | 9.554 | -0.8999% | 58.21 | +1.7463% | +1.8824% |
| `funding_positive_sameday` | `flat_3bp_capital_rf` | test_oos | -0.7041% | -1.635 | -2.6445% | 120.64 | +3.6193% | +1.6599% |
| `funding_positive_sameday` | `flat_3bp_capital_rf` | post2022 | +3.3450% | 5.246 | -2.6445% | 87.31 | +2.6192% | +1.7787% |
| `funding_positive_sameday` | `venue_taker` | full | +6.6432% | 4.027 | -9.1045% | 96.79 | +7.2587% | +0.0000% |
| `funding_positive_sameday` | `venue_taker` | train | +13.9401% | 6.206 | -9.1045% | 108.64 | +8.1475% | +0.0000% |
| `funding_positive_sameday` | `venue_taker` | val | +6.2265% | 6.573 | -2.1989% | 58.21 | +4.3655% | +0.0000% |
| `funding_positive_sameday` | `venue_taker` | test_oos | -4.3800% | -5.075 | -8.9275% | 120.64 | +9.0481% | +0.0000% |
| `funding_positive_sameday` | `venue_taker` | post2022 | +1.1446% | 1.212 | -8.9275% | 87.31 | +6.5477% | +0.0000% |
| `funding_positive_sameday` | `venue_taker_slippage` | full | +4.5970% | 2.631 | -14.8601% | 96.79 | +9.1944% | +0.0000% |
| `funding_positive_sameday` | `venue_taker_slippage` | train | +11.4892% | 4.923 | -12.4660% | 108.64 | +10.3203% | +0.0000% |
| `funding_positive_sameday` | `venue_taker_slippage` | val | +4.9961% | 4.740 | -2.8858% | 58.21 | +5.5296% | +0.0000% |
| `funding_positive_sameday` | `venue_taker_slippage` | test_oos | -6.6617% | -6.357 | -12.5118% | 120.64 | +11.4610% | +0.0000% |
| `funding_positive_sameday` | `venue_taker_slippage` | post2022 | -0.6078% | -0.549 | -12.5118% | 87.31 | +8.2938% | +0.0000% |
| `funding_positive_sameday` | `venue_maker_slippage` | full | +6.1282% | 3.663 | -10.0095% | 96.79 | +7.7423% | +0.0000% |
| `funding_positive_sameday` | `venue_maker_slippage` | train | +13.3229% | 5.877 | -9.9507% | 108.64 | +8.6903% | +0.0000% |
| `funding_positive_sameday` | `venue_maker_slippage` | val | +5.9177% | 6.080 | -2.3710% | 58.21 | +4.6564% | +0.0000% |
| `funding_positive_sameday` | `venue_maker_slippage` | test_oos | -4.9555% | -5.449 | -9.8369% | 120.64 | +9.6513% | +0.0000% |
| `funding_positive_sameday` | `venue_maker_slippage` | post2022 | +0.7038% | 0.720 | -9.8369% | 87.31 | +6.9841% | +0.0000% |
| `funding_positive_sameday` | `realistic_rf` | full | +2.7733% | 1.615 | -21.1033% | 96.79 | +9.1944% | +1.7593% |
| `funding_positive_sameday` | `realistic_rf` | train | +9.5722% | 4.162 | -13.6502% | 108.64 | +10.3203% | +1.7352% |
| `funding_positive_sameday` | `realistic_rf` | val | +3.0385% | 2.940 | -3.6067% | 58.21 | +5.5296% | +1.8824% |
| `funding_positive_sameday` | `realistic_rf` | test_oos | -8.1984% | -8.001 | -14.4549% | 120.64 | +11.4610% | +1.6599% |
| `funding_positive_sameday` | `realistic_rf` | post2022 | -2.3599% | -2.196 | -14.4549% | 87.31 | +8.2938% | +1.7787% |
| `funding_positive_sameday` | `realistic_no_capital_charge` | full | +4.5970% | 2.631 | -14.8601% | 96.79 | +9.1944% | +0.0000% |
| `funding_positive_sameday` | `realistic_no_capital_charge` | train | +11.4892% | 4.923 | -12.4660% | 108.64 | +10.3203% | +0.0000% |
| `funding_positive_sameday` | `realistic_no_capital_charge` | val | +4.9961% | 4.740 | -2.8858% | 58.21 | +5.5296% | +0.0000% |
| `funding_positive_sameday` | `realistic_no_capital_charge` | test_oos | -6.6617% | -6.357 | -12.5118% | 120.64 | +11.4610% | +0.0000% |
| `funding_positive_sameday` | `realistic_no_capital_charge` | post2022 | -0.6078% | -0.549 | -12.5118% | 87.31 | +8.2938% | +0.0000% |
| `funding_positive_sameday` | `realistic_usdt_5pct` | full | +0.0969% | 0.066 | -30.0153% | 96.79 | +9.1944% | +4.3983% |
| `funding_positive_sameday` | `realistic_usdt_5pct` | train | +6.7581% | 3.004 | -15.4101% | 108.64 | +10.3203% | +4.3379% |
| `funding_positive_sameday` | `realistic_usdt_5pct` | val | +0.1701% | 0.174 | -5.2127% | 58.21 | +5.5296% | +4.7059% |
| `funding_positive_sameday` | `realistic_usdt_5pct` | test_oos | -10.4563% | -10.539 | -17.7598% | 120.64 | +11.4610% | +4.1497% |
| `funding_positive_sameday` | `realistic_usdt_5pct` | post2022 | -4.9306% | -4.739 | -18.8548% | 87.31 | +8.2938% | +4.4467% |
| `funding_positive_lagged` | `flat_3bp` | full | +10.5340% | 6.597 | -2.6594% | 96.96 | +2.9088% | +0.0000% |
| `funding_positive_lagged` | `flat_3bp` | train | +18.0646% | 7.881 | -2.6050% | 108.93 | +3.2679% | +0.0000% |
| `funding_positive_lagged` | `flat_3bp` | val | +8.7877% | 11.586 | -0.8010% | 58.21 | +1.7463% | +0.0000% |
| `funding_positive_lagged` | `flat_3bp` | test_oos | +0.5295% | 1.128 | -2.6594% | 120.81 | +3.6244% | +0.0000% |
| `funding_positive_lagged` | `flat_3bp` | post2022 | +4.8579% | 7.261 | -2.6594% | 87.39 | +2.6216% | +0.0000% |
| `funding_positive_lagged` | `flat_3bp_capital_rf` | full | +8.6079% | 5.466 | -3.8833% | 96.96 | +2.9088% | +1.7585% |
| `funding_positive_lagged` | `flat_3bp_capital_rf` | train | +16.0369% | 7.086 | -3.8833% | 108.93 | +3.2679% | +1.7333% |
| `funding_positive_lagged` | `flat_3bp_capital_rf` | val | +6.7596% | 9.087 | -1.0188% | 58.21 | +1.7463% | +1.8824% |
| `funding_positive_lagged` | `flat_3bp_capital_rf` | test_oos | -1.1254% | -2.489 | -3.2078% | 120.81 | +3.6244% | +1.6599% |
| `funding_positive_lagged` | `flat_3bp_capital_rf` | post2022 | +3.0096% | 4.617 | -3.2078% | 87.39 | +2.6216% | +1.7787% |
| `funding_positive_lagged` | `venue_taker` | full | +5.8132% | 3.313 | -10.5445% | 96.96 | +7.2715% | +0.0000% |
| `funding_positive_lagged` | `venue_taker` | train | +12.4154% | 5.118 | -10.4945% | 108.93 | +8.1690% | +0.0000% |
| `funding_positive_lagged` | `venue_taker` | val | +5.9741% | 6.235 | -2.3253% | 58.21 | +4.3655% | +0.0000% |
| `funding_positive_lagged` | `venue_taker` | test_oos | -4.7930% | -5.456 | -9.5845% | 120.81 | +9.0609% | +0.0000% |
| `funding_positive_lagged` | `venue_taker` | post2022 | +0.8126% | 0.849 | -9.5845% | 87.39 | +6.5537% | +0.0000% |
| `funding_positive_lagged` | `venue_taker_slippage` | full | +3.7793% | 2.048 | -17.1892% | 96.96 | +9.2107% | +0.0000% |
| `funding_positive_lagged` | `venue_taker_slippage` | train | +9.9908% | 3.990 | -13.8252% | 108.93 | +10.3476% | +0.0000% |
| `funding_positive_lagged` | `venue_taker_slippage` | val | +4.7465% | 4.457 | -3.0131% | 58.21 | +5.5297% | +0.0000% |
| `funding_positive_lagged` | `venue_taker_slippage` | test_oos | -7.0681% | -6.655 | -13.1477% | 120.81 | +11.4771% | +0.0000% |
| `funding_positive_lagged` | `venue_taker_slippage` | post2022 | -0.9356% | -0.838 | -13.1477% | 87.39 | +8.3014% | +0.0000% |
| `funding_positive_lagged` | `venue_maker_slippage` | full | +5.3013% | 2.984 | -11.6847% | 96.96 | +7.7560% | +0.0000% |
| `funding_positive_lagged` | `venue_maker_slippage` | train | +11.8049% | 4.829 | -11.3389% | 108.93 | +8.7131% | +0.0000% |
| `funding_positive_lagged` | `venue_maker_slippage` | val | +5.6660% | 5.757 | -2.4977% | 58.21 | +4.6564% | +0.0000% |
| `funding_positive_lagged` | `venue_maker_slippage` | test_oos | -5.3668% | -5.805 | -10.4886% | 120.81 | +9.6649% | +0.0000% |
| `funding_positive_lagged` | `venue_maker_slippage` | post2022 | +0.3728% | 0.378 | -10.4886% | 87.39 | +6.9905% | +0.0000% |
| `funding_positive_lagged` | `realistic_rf` | full | +1.9706% | 1.088 | -23.2602% | 96.96 | +9.2107% | +1.7585% |
| `funding_positive_lagged` | `realistic_rf` | train | +8.1015% | 3.280 | -14.9929% | 108.93 | +10.3476% | +1.7333% |
| `funding_positive_lagged` | `realistic_rf` | val | +2.7936% | 2.675 | -3.8952% | 58.21 | +5.5297% | +1.8824% |
| `funding_positive_lagged` | `realistic_rf` | test_oos | -8.5981% | -8.272 | -15.0756% | 120.81 | +11.4771% | +1.6599% |
| `funding_positive_lagged` | `realistic_rf` | post2022 | -2.6820% | -2.464 | -15.0795% | 87.39 | +8.3014% | +1.7787% |
| `funding_positive_lagged` | `realistic_no_capital_charge` | full | +3.7793% | 2.048 | -17.1892% | 96.96 | +9.2107% | +0.0000% |
| `funding_positive_lagged` | `realistic_no_capital_charge` | train | +9.9908% | 3.990 | -13.8252% | 108.93 | +10.3476% | +0.0000% |
| `funding_positive_lagged` | `realistic_no_capital_charge` | val | +4.7465% | 4.457 | -3.0131% | 58.21 | +5.5297% | +0.0000% |
| `funding_positive_lagged` | `realistic_no_capital_charge` | test_oos | -7.0681% | -6.655 | -13.1477% | 120.81 | +11.4771% | +0.0000% |
| `funding_positive_lagged` | `realistic_no_capital_charge` | post2022 | -0.9356% | -0.838 | -13.1477% | 87.39 | +8.3014% | +0.0000% |
| `funding_positive_lagged` | `realistic_usdt_5pct` | full | -0.6837% | -0.373 | -31.9522% | 96.96 | +9.2107% | +4.3963% |
| `funding_positive_lagged` | `realistic_usdt_5pct` | train | +5.3279% | 2.204 | -16.7256% | 108.93 | +10.3476% | +4.3333% |
| `funding_positive_lagged` | `realistic_usdt_5pct` | val | -0.0680% | -0.062 | -5.4964% | 58.21 | +5.5297% | +4.7059% |
| `funding_positive_lagged` | `realistic_usdt_5pct` | test_oos | -10.8462% | -10.766 | -18.3847% | 120.81 | +11.4771% | +4.1497% |
| `funding_positive_lagged` | `realistic_usdt_5pct` | post2022 | -5.2442% | -4.974 | -19.6015% | 87.39 | +8.3014% | +4.4467% |

The venue model charges the spot leg and the perp leg separately, so the two legs' turnovers are reported as well (the fee drag is the weighted average of the two published rates over the turnover that is actually traded):

| Rule | Cost model | Spot turnover/yr | Perp turnover/yr | Spot notional (mean share of equity) | Fee drag/yr |
|---|---|---|---|---|---|
| `always_on` | `flat_3bp` | 9.22 | 9.24 | 1.000 | +0.5540% |
| `always_on` | `flat_3bp_capital_rf` | 9.22 | 9.24 | 1.000 | +0.5540% |
| `always_on` | `venue_taker` | 9.22 | 9.24 | 1.000 | +1.3846% |
| `always_on` | `venue_taker_slippage` | 9.22 | 9.24 | 1.000 | +1.7539% |
| `always_on` | `venue_maker_slippage` | 9.22 | 9.24 | 1.000 | +1.4766% |
| `always_on` | `realistic_rf` | 9.22 | 9.24 | 1.000 | +1.7539% |
| `always_on` | `realistic_no_capital_charge` | 9.22 | 9.24 | 1.000 | +1.7539% |
| `always_on` | `realistic_usdt_5pct` | 9.22 | 9.24 | 1.000 | +1.7539% |
| `funding_positive_sameday` | `flat_3bp` | 48.39 | 48.40 | 0.880 | +2.9036% |
| `funding_positive_sameday` | `flat_3bp_capital_rf` | 48.39 | 48.40 | 0.880 | +2.9036% |
| `funding_positive_sameday` | `venue_taker` | 48.39 | 48.40 | 0.880 | +7.2587% |
| `funding_positive_sameday` | `venue_taker_slippage` | 48.39 | 48.40 | 0.880 | +9.1944% |
| `funding_positive_sameday` | `venue_maker_slippage` | 48.39 | 48.40 | 0.880 | +7.7423% |
| `funding_positive_sameday` | `realistic_rf` | 48.39 | 48.40 | 0.880 | +9.1944% |
| `funding_positive_sameday` | `realistic_no_capital_charge` | 48.39 | 48.40 | 0.880 | +9.1944% |
| `funding_positive_sameday` | `realistic_usdt_5pct` | 48.39 | 48.40 | 0.880 | +9.1944% |
| `funding_positive_lagged` | `flat_3bp` | 48.47 | 48.49 | 0.879 | +2.9088% |
| `funding_positive_lagged` | `flat_3bp_capital_rf` | 48.47 | 48.49 | 0.879 | +2.9088% |
| `funding_positive_lagged` | `venue_taker` | 48.47 | 48.49 | 0.879 | +7.2715% |
| `funding_positive_lagged` | `venue_taker_slippage` | 48.47 | 48.49 | 0.879 | +9.2107% |
| `funding_positive_lagged` | `venue_maker_slippage` | 48.47 | 48.49 | 0.879 | +7.7560% |
| `funding_positive_lagged` | `realistic_rf` | 48.47 | 48.49 | 0.879 | +9.2107% |
| `funding_positive_lagged` | `realistic_no_capital_charge` | 48.47 | 48.49 | 0.879 | +9.2107% |
| `funding_positive_lagged` | `realistic_usdt_5pct` | 48.47 | 48.49 | 0.879 | +9.2107% |

### Break-evens

The three break-evens of every rule (portfolio), on the full sample and on the out-of-sample window:

| Rule | Sample | Break-even flat cost/unit | Break-even capital charge (annual, on the spot leg) | Break-even multiple of the venue schedule |
|---|---|---|---|---|
| `always_on` | full | 68.0677 bp | +10.82% | 6.03x |
| `always_on` | test_oos | 26.1668 bp | +2.48% | 1.34x |
| `funding_positive_sameday` | full | 14.1376 bp | +5.11% | 1.30x |
| `funding_positive_sameday` | test_oos | 3.7898 bp | -8.31% | 0.25x |
| `funding_positive_lagged` | full | 13.3208 bp | +4.22% | 1.21x |
| `funding_positive_lagged` | test_oos | 3.4369 bp | -8.83% | 0.22x |

* The **break-even flat cost per unit** is the cost screen's own measure, computed on the same series: the flat cost at which the net annualized return is exactly zero.
* The **break-even capital charge** holds the venue fees (taker + repository slippage) fixed and solves for the annual rate on the spot leg's notional at which the net annualized return is zero. A negative value means the book is already unprofitable before the capital is charged.
* The **break-even multiple of the venue schedule** holds the capital charge (at the repository's risk-free rate) fixed and solves for the multiple of the published fee schedule at which the net annualized return is zero.

### The turnover convention: the headline and the bound

The pre-registered gross path is the **constant-notional** construction: the book resets the spot and the perp notionals to `w * equity` every day. The only turnover convention that is internally consistent with that gross path is therefore the daily constant-notional rebalance (`drift`), and that is the headline: the other two conventions do not describe the same book traded less often, they describe a *different* book (a fixed-coin book is paid its funding on a notional that scales with the coin's price, so its return on equity is a different quantity). The fixed-coin construction is measured with its own self-consistent gross path in the next section; it is a sensitivity of the same six configurations, not a replacement of the pre-registered headline.

What an implementer would actually trade is a constant-notional target rebalanced on a *threshold* rather than every day, so the headline's daily cadence **over**-states the trading cost. The two other conventions bound the other end. The rows below are the headline cost model under each convention, and they bound how much the trading-frequency question can move the answer:

| Rule | Convention | Consistent with the pre-registered gross path | Ann. net | Sharpe | Turnover/yr | Fee drag/yr |
|---|---|---|---|---|---|---|
| `always_on` | `drift` | yes | +9.2190% | 5.964 | 18.47 | +1.7539% |
| `always_on` | `parity` | no (cost-only bound) | +11.1090% | 7.117 | 0.38 | +0.0378% |
| `always_on` | `fixed_quantity` | no (cost-only bound) | +11.1197% | 7.123 | 0.30 | +0.0281% |
| `funding_positive_sameday` | `drift` | yes | +2.7733% | 1.615 | 96.79 | +9.1944% |
| `funding_positive_sameday` | `parity` | no (cost-only bound) | +4.2989% | 2.454 | 81.25 | +7.7204% |
| `funding_positive_sameday` | `fixed_quantity` | no (cost-only bound) | +4.3079% | 2.458 | 81.18 | +7.7118% |
| `funding_positive_lagged` | `drift` | yes | +1.9706% | 1.088 | 96.96 | +9.2107% |
| `funding_positive_lagged` | `parity` | no (cost-only bound) | +3.5011% | 1.898 | 81.25 | +7.7206% |
| `funding_positive_lagged` | `fixed_quantity` | no (cost-only bound) | +3.5102% | 1.903 | 81.18 | +7.7118% |

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

**The screen uses the repository's flat 3 bp/unit cost model.** It does not use the venue fee schedule and it does not charge the capital the spot leg ties up, so the screen's crypto row is the flat-model row of this record and not its headline. The screen is left untouched (the shared machinery and the other candidates' rows are unchanged) and it still ends with `OVERALL: PASS`.

**The screen's ADMISSIBLE verdict is therefore a statement about the flat 3 bp/unit model only.** It does not describe the headline model of this record, in which the traded cost per unit is several times the flat cost and the capital charge is not in the screen at all. The question the screen answers for the headline is answered here instead, by the break-evens: under the headline model the always-on book still nets a positive return, its break-even multiple of the published fee schedule is 6.03x on the full sample, and its break-even capital charge is +10.82% per year on the spot leg's notional.

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

* `drift`: Constant-notional rebalance of both legs every day (the cost screen's convention): w*(|spot_return| + |perp_return|) while the pair is held, of which the spot leg trades w*|spot_return| and the perp leg w*|perp_return|.
* `parity`: Equal-notional maintenance: only the basis drift is traded, w*|spot_return - perp_return| while the pair is held. The adjustment is executed on the spot leg (the perp leg keeps its drifted notional), which is the conservative choice under a per-leg fee schedule.
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

### Under the repository's flat model (Cycle 891, unchanged)

| Rule | Net OOS Sharpe (canonical, 365) | Sharpe criterion | Pooled OOS round trips | Repo rebalance-day count | Settlement observations | Trade-count criterion | Gate |
|---|---|---|---|---|---|---|---|
| `always_on` | 9.209 | PASS | 0 | 1276 | 3828 | FAIL | **FAIL** |
| `funding_positive_sameday` | 1.762 | PASS | 95 | 1154 | 3828 | FAIL | **FAIL** |
| `funding_positive_lagged` | 0.977 | PASS | 95 | 1154 | 3828 | FAIL | **FAIL** |

The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.

### Under every cost model (the gate is re-evaluated, never relaxed)

The gates are the repository's own thresholds, unchanged: a net out-of-sample Sharpe (canonical, 365) of at least 0.9 and more than 100 pooled out-of-sample independent trades. Only the cost model changes between the rows. The trade count is a property of the position path, not of the cost model, so it does not move between the rows.

| Rule | Cost model | Net OOS Sharpe (canonical, 365) | Sharpe criterion | Pooled OOS round trips | Trade-count criterion | Gate |
|---|---|---|---|---|---|---|
| `always_on` | `flat_3bp` | 9.209 | PASS | 0 | FAIL | **FAIL** |
| `always_on` | `flat_3bp_capital_rf` | 3.936 | PASS | 0 | FAIL | **FAIL** |
| `always_on` | `venue_taker` | 7.388 | PASS | 0 | FAIL | **FAIL** |
| `always_on` | `venue_taker_slippage` | 6.577 | PASS | 0 | FAIL | **FAIL** |
| `always_on` | `venue_maker_slippage` | 7.185 | PASS | 0 | FAIL | **FAIL** |
| `always_on` | `realistic_rf` | 1.412 | PASS | 0 | FAIL | **FAIL** |
| `always_on` | `realistic_no_capital_charge` | 6.577 | PASS | 0 | FAIL | **FAIL** |
| `always_on` | `realistic_usdt_5pct` | -6.336 | FAIL | 0 | FAIL | **FAIL** |
| `funding_positive_sameday` | `flat_3bp` | 1.762 | PASS | 95 | FAIL | **FAIL** |
| `funding_positive_sameday` | `flat_3bp_capital_rf` | -1.286 | FAIL | 95 | FAIL | **FAIL** |
| `funding_positive_sameday` | `venue_taker` | -3.953 | FAIL | 95 | FAIL | **FAIL** |
| `funding_positive_sameday` | `venue_taker_slippage` | -4.941 | FAIL | 95 | FAIL | **FAIL** |
| `funding_positive_sameday` | `venue_maker_slippage` | -4.242 | FAIL | 95 | FAIL | **FAIL** |
| `funding_positive_sameday` | `realistic_rf` | -6.220 | FAIL | 95 | FAIL | **FAIL** |
| `funding_positive_sameday` | `realistic_no_capital_charge` | -4.941 | FAIL | 95 | FAIL | **FAIL** |
| `funding_positive_sameday` | `realistic_usdt_5pct` | -8.183 | FAIL | 95 | FAIL | **FAIL** |
| `funding_positive_lagged` | `flat_3bp` | 0.977 | PASS | 95 | FAIL | **FAIL** |
| `funding_positive_lagged` | `flat_3bp_capital_rf` | -1.961 | FAIL | 95 | FAIL | **FAIL** |
| `funding_positive_lagged` | `venue_taker` | -4.269 | FAIL | 95 | FAIL | **FAIL** |
| `funding_positive_lagged` | `venue_taker_slippage` | -5.194 | FAIL | 95 | FAIL | **FAIL** |
| `funding_positive_lagged` | `venue_maker_slippage` | -4.540 | FAIL | 95 | FAIL | **FAIL** |
| `funding_positive_lagged` | `realistic_rf` | -6.459 | FAIL | 95 | FAIL | **FAIL** |
| `funding_positive_lagged` | `realistic_no_capital_charge` | -5.194 | FAIL | 95 | FAIL | **FAIL** |
| `funding_positive_lagged` | `realistic_usdt_5pct` | -8.398 | FAIL | 95 | FAIL | **FAIL** |

**Which criterion fails:** the trade-count criterion fails in all 24 of the 24 rows (the pooled out-of-sample round trips are a property of the position path, not of the cost model); the Sharpe criterion passes in 9 and fails in 15 of them. The gate is therefore **FAIL** under every cost model, and the gate is never relaxed: the thresholds are the repository's own and are applied unchanged.

## The implementable construction: fixed coin quantity (Cycle 893)

The pre-registered gross path resets both legs to constant notional every day. This section measures the **fixed coin quantity** construction: ``q`` coins are held long spot and short perp from entry to exit, the book is marked to market, and ``q`` is re-sized from then-current equity at each entry. It has no daily rebalance turnover - entry and exit only - so it is what an implementer would actually run, and its gross path is self-consistent with its trading. It is a sensitivity of the same six configurations (3 rules x 2 symbols) under the Cycle 892 headline cost model, not a new trial.

### Accounting conventions

* Entry: at the entry day's close, ``q = weight * equity / spot_close``, so the spot notional is ``weight`` of then-current equity.
* While held: the daily price P&L is the change of the basis level, ``q * ((S_t - P_t) - (S_{t-1} - P_{t-1}))``; funding is paid on the coin's perp notional ``q * funding_cashflow_t * P_{t-1}``, the previous day's perp close as the notional proxy.
* Equity compounds on price P&L plus funding; each entry re-sizes ``q`` from then-current equity.
* Entry and exit days carry no same-day P&L; entry and exit are charged as turnover costs (each leg trades ``weight`` per transition).
* Costs: the Cycle 892 headline model - venue taker plus repository slippage on the legs actually traded, plus the capital charge on the marked-to-market spot notional - applied to entry/exit turnover only.

### Results (net of the Cycle 892 headline cost model, 365-day annualization)

| Rule | Sample | Sessions | Ann. net (geo) | Sharpe (canonical) | Max DD | Turnover/yr | Entries | Exits |
|---|---|---|---|---|---|---|---|---|
| `always_on` | full | 2464 | +54.1139% | 6.740 | -2.7412% | 0.30 | 2 | 0 |
| `always_on` | train | 1095 | +110.3057% | 8.174 | -2.7412% | 0.67 | 2 | 0 |
| `always_on` | val | 731 | +31.7806% | 11.273 | -0.4487% | 0.00 | 0 | 0 |
| `always_on` | test_oos | 638 | +8.1501% | 7.143 | -2.6197% | 0.00 | 0 | 0 |
| `always_on` | post2022 | 1369 | +20.1861% | 9.165 | -2.6197% | 0.00 | 0 | 0 |
| `funding_positive_sameday` | full | 2464 | +16.9965% | 4.164 | -14.3245% | 81.18 | 275 | 273 |
| `funding_positive_sameday` | train | 1095 | +40.0138% | 6.348 | -13.1184% | 89.33 | 135 | 133 |
| `funding_positive_sameday` | val | 731 | +9.0606% | 6.070 | -3.0815% | 44.94 | 45 | 45 |
| `funding_positive_sameday` | test_oos | 638 | -6.8343% | -6.287 | -12.9955% | 108.70 | 95 | 95 |
| `funding_positive_sameday` | post2022 | 1369 | +1.3411% | 0.986 | -12.9955% | 74.65 | 140 | 140 |
| `funding_positive_lagged` | full | 2464 | +16.0201% | 3.913 | -15.5975% | 81.18 | 275 | 273 |
| `funding_positive_lagged` | train | 1095 | +37.7882% | 5.986 | -14.1699% | 89.33 | 135 | 133 |
| `funding_positive_lagged` | val | 731 | +8.9643% | 5.922 | -3.3205% | 44.94 | 45 | 45 |
| `funding_positive_lagged` | test_oos | 638 | -7.1925% | -6.663 | -13.5099% | 108.70 | 95 | 95 |
| `funding_positive_lagged` | post2022 | 1369 | +1.1117% | 0.812 | -13.5099% | 74.65 | 140 | 140 |

### Break-evens (portfolio, headline cost model)

| Rule | Sample | Break-even flat cost/unit | Break-even capital charge (annual, spot notional) | Break-even venue fee multiple |
|---|---|---|---|---|
| `always_on` | full | none | +15.97% | none |
| `always_on` | test_oos | none | +4.37% | none |
| `funding_positive_sameday` | full | 31.7025 bp | +15.22% | 3.03x |
| `funding_positive_sameday` | test_oos | 4.6907 bp | -5.67% | 0.32x |
| `funding_positive_lagged` | full | 30.6544 bp | +14.60% | 2.92x |
| `funding_positive_lagged` | test_oos | 4.3106 bp | -6.21% | 0.28x |

### Promotion gate (fixed coin quantity)

| Rule | Cost model | Net OOS Sharpe (canonical, 365) | Sharpe criterion | Pooled OOS round trips | Trade-count criterion | Gate |
|---|---|---|---|---|---|---|
| `always_on` | `realistic_rf` | 5.645 | PASS | 0 | FAIL | **FAIL** |
| `funding_positive_sameday` | `realistic_rf` | -4.943 | FAIL | 95 | FAIL | **FAIL** |
| `funding_positive_lagged` | `realistic_rf` | -5.224 | FAIL | 95 | FAIL | **FAIL** |

### Headline: constant notional versus fixed coin quantity

On the full sample under the headline model, the constant-notional book nets +9.2190%/yr (Sharpe 5.964, turnover 18.47/yr) versus +54.1139%/yr for the fixed-coin book (Sharpe 6.740, turnover 0.30/yr); for the implementable funding-positive rule the figures are +1.9706%/yr (Sharpe 1.088) versus +16.0201%/yr (Sharpe 3.913).

**Headline: fixed coin quantity.** The implementable construction nets more than the constant-notional book on the same committed path on both rules, so the Cycle 892 constant-notional headline was **conservative**: it under-states the implementable book by +44.8949%/yr (always-on) and +14.0495%/yr (funding-positive).

Neither construction passes the promotion gate: the trade-count criterion fails because neither book opens independent out-of-sample positions in sufficient number, and the gate is never relaxed.

## The threshold-rebalanced constant notional (Cycle 894)

The pre-registered book resets both legs to constant notional every day. This section measures the **threshold-rebalanced** version of that same construction: the legs are reset to `weight * equity` only on the days where the cumulative price drift of either leg since the last rebalance exceeds a pre-registered threshold of **2%**; between those days the notional floats with the price and nothing is traded. It answers one question: how much of the daily-rebalanced answer is an artefact of rebalancing every day? It is a sensitivity of the same six configurations (3 rules x 2 symbols) under the Cycle 892 headline cost model, not a new trial.

### Accounting conventions

* Equal **notional** on the two legs at every rebalance (the pre-registered book's convention); between rebalances each leg keeps its own coin quantity, so the two notionals drift apart by the basis move.
* The daily P&L of a held leg is `notional_spot * spot_return - notional_perp * perp_return + funding_cashflow * notional_perp`, with the notionals in effect from the previous close; the equity compounds on it.
* The book has **one** equity for all the symbols it holds: the equal-weight BTC/ETH book is one book with a shared equity, not two books added up.
* A position transition is charged on both legs with the target notional `weight` per leg, exactly as the pre-registered book charges it, and the entry day's carry is earned.
* The turnover of a rebalance is the cumulative price drift of the leg since the last rebalance, `weight * |P_t / P_k - 1|` per leg - the same linearized convention the pre-registered `drift` turnover uses. **With a threshold of 0 the book rebalances every day and reproduces the pre-registered book exactly** (gross, turnover, leg weights and capital base), which is the regression guard of this section.
* The capital charge is applied to the marked-to-market spot notional (the notional actually tied up), the same convention the fixed-coin construction uses.

### Results (net of the Cycle 892 headline cost model, 365-day annualization, equal-weight BTC/ETH portfolio)

| Rule | Sample | Sessions | Ann. net (geo) | Sharpe (canonical) | Max DD | Turnover/yr | Entries | Exits |
|---|---|---|---|---|---|---|---|---|
| `always_on` | full | 2464 | +9.5081% | 6.144 | -2.0218% | 15.64 | 2 | 0 |
| `always_on` | train | 1095 | +16.4489% | 7.303 | -2.0218% | 20.81 | 2 | 0 |
| `always_on` | val | 731 | +7.4133% | 10.857 | -0.3313% | 10.97 | 0 | 0 |
| `always_on` | test_oos | 638 | +0.7511% | 2.331 | -1.4142% | 12.11 | 0 | 0 |
| `always_on` | post2022 | 1369 | +4.2554% | 7.515 | -1.4142% | 11.50 | 0 | 0 |
| `funding_positive_sameday` | full | 2464 | +3.0150% | 1.753 | -20.2566% | 94.25 | 275 | 273 |
| `funding_positive_sameday` | train | 1095 | +9.8043% | 4.258 | -13.5028% | 106.32 | 135 | 133 |
| `funding_positive_sameday` | val | 731 | +3.3111% | 3.190 | -3.4547% | 55.35 | 45 | 45 |
| `funding_positive_sameday` | test_oos | 638 | -7.9766% | -7.757 | -14.1684% | 118.13 | 95 | 95 |
| `funding_positive_sameday` | post2022 | 1369 | -2.1120% | -1.957 | -14.1684% | 84.60 | 140 | 140 |
| `funding_positive_lagged` | full | 2464 | +2.2113% | 1.218 | -22.4251% | 94.42 | 275 | 273 |
| `funding_positive_lagged` | train | 1095 | +8.3275% | 3.368 | -14.8486% | 106.65 | 135 | 133 |
| `funding_positive_lagged` | val | 731 | +3.0753% | 2.932 | -3.7286% | 55.26 | 45 | 45 |
| `funding_positive_lagged` | test_oos | 638 | -8.3799% | -8.040 | -14.7938% | 118.30 | 95 | 95 |
| `funding_positive_lagged` | post2022 | 1369 | -2.4313% | -2.226 | -14.7938% | 84.64 | 140 | 140 |

### Sensitivity: the rebalancing frequency (portfolio, headline model)

| Threshold | Rule | Ann. net (geo) | Sharpe (canonical) | Max DD | Turnover/yr | Rebalances (BTC, ETH) |
|---|---|---|---|---|---|---|
| 1% | `always_on` | +9.3298% | 6.033 | -2.0704% | 17.42 | 1523, 1730 |
| 1% | `funding_positive_sameday` | +2.8693% | 1.670 | -20.7657% | 95.83 | 1319, 1515 |
| 1% | `funding_positive_lagged` | +2.0630% | 1.138 | -22.9413% | 96.03 | 1339, 1514 |
| 2% | `always_on` | +9.5081% | 6.144 | -2.0218% | 15.64 | 952, 1259 |
| 2% | `funding_positive_sameday` | +3.0150% | 1.753 | -20.2566% | 94.25 | 816, 1097 |
| 2% | `funding_positive_lagged` | +2.2113% | 1.218 | -22.4251% | 94.42 | 831, 1086 |
| 5% | `always_on` | +10.0285% | 6.446 | -1.9883% | 10.78 | 361, 536 |
| 5% | `funding_positive_sameday` | +3.4449% | 1.991 | -18.8949% | 89.98 | 300, 465 |
| 5% | `funding_positive_lagged` | +2.6406% | 1.446 | -21.1154% | 90.14 | 304, 466 |
| 10% | `always_on` | +10.4650% | 6.651 | -1.8683% | 7.57 | 143, 229 |
| 10% | `funding_positive_sameday` | +3.8538% | 2.204 | -17.8822% | 86.83 | 118, 172 |
| 10% | `funding_positive_lagged` | +3.0582% | 1.656 | -20.1162% | 86.93 | 113, 179 |

The grid is a sensitivity of the same construction, reported next to the pre-registered threshold and never used to select one: the headline of this section is the pre-registered 2% row.

### Break-evens (portfolio, headline cost model)

| Rule | Sample | Break-even flat cost/unit | Break-even capital charge (annual, spot notional) | Break-even venue fee multiple |
|---|---|---|---|---|
| `always_on` | full | 80.3329 bp | +11.09% | 7.11x |
| `always_on` | test_oos | 32.1990 bp | +2.75% | 1.65x |
| `funding_positive_sameday` | full | 14.5103 bp | +5.38% | 1.33x |
| `funding_positive_sameday` | test_oos | 3.8726 bp | -8.01% | 0.26x |
| `funding_positive_lagged` | full | 13.6722 bp | +4.49% | 1.24x |
| `funding_positive_lagged` | test_oos | 3.5102 bp | -8.54% | 0.22x |

### Promotion gate (threshold-rebalanced constant notional)

| Rule | Cost model | Net OOS Sharpe (canonical, 365) | Sharpe criterion | Pooled OOS round trips | Trade-count criterion | Gate |
|---|---|---|---|---|---|---|
| `always_on` | `realistic_rf` | 2.088 | PASS | 0 | FAIL | **FAIL** |
| `funding_positive_sameday` | `realistic_rf` | -6.031 | FAIL | 95 | FAIL | **FAIL** |
| `funding_positive_lagged` | `realistic_rf` | -6.276 | FAIL | 95 | FAIL | **FAIL** |

The gate is re-evaluated for this construction on the same thresholds as every other row and is never relaxed: it **fails** in every row, on the same trade-count criterion as the other constructions (the pooled out-of-sample round trips are a property of the position path, not of the rebalancing frequency).

### The three constructions on the same committed path

The three constructions are compared below on the **per-symbol** basis (one symbol at a time, `weight = 1`, each book measured against its own equity), because that is the only comparison in which all three use the same accounting. The portfolio rows follow below with their accounting stated.

| Rule | Symbol | Daily drift (ann. net) | Threshold 2% (ann. net) | Fixed coin (ann. net) | Threshold minus daily drift |
|---|---|---|---|---|---|
| `always_on` | BTCUSDT | +8.4342% | +8.7401% | +26.5145% | +0.3059% |
| `always_on` | ETHUSDT | +10.0058% | +10.2779% | +42.9265% | +0.2721% |
| `funding_positive_sameday` | BTCUSDT | +1.9504% | +2.2074% | +9.8350% | +0.2571% |
| `funding_positive_sameday` | ETHUSDT | +3.5947% | +3.8208% | +18.8218% | +0.2262% |
| `funding_positive_lagged` | BTCUSDT | +1.1906% | +1.4419% | +9.1115% | +0.2513% |
| `funding_positive_lagged` | ETHUSDT | +2.7483% | +2.9783% | +17.7718% | +0.2300% |

| Rule | Construction | Portfolio ann. net | Sharpe | Turnover/yr | Accounting |
|---|---|---|---|---|---|
| `always_on` | daily drift (pre-registered) | +9.2190% | 5.964 | 18.47 | one shared equity |
| `always_on` | threshold 2% | +9.5081% | 6.144 | 15.64 | one shared equity |
| `always_on` | fixed coin (Cycle 893) | +54.1139% | 6.740 | 0.30 | sum of the two symbols' separately compounded returns |
| `funding_positive_sameday` | daily drift (pre-registered) | +2.7733% | 1.615 | 96.79 | one shared equity |
| `funding_positive_sameday` | threshold 2% | +3.0150% | 1.753 | 94.25 | one shared equity |
| `funding_positive_sameday` | fixed coin (Cycle 893) | +16.9965% | 4.164 | 81.18 | sum of the two symbols' separately compounded returns |
| `funding_positive_lagged` | daily drift (pre-registered) | +1.9706% | 1.088 | 96.96 | one shared equity |
| `funding_positive_lagged` | threshold 2% | +2.2113% | 1.218 | 94.42 | one shared equity |
| `funding_positive_lagged` | fixed coin (Cycle 893) | +16.0201% | 3.913 | 81.18 | sum of the two symbols' separately compounded returns |

**Which convention nets more.** On the consistent per-symbol basis the threshold-rebalanced constant notional nets **more** than the daily-rebalanced one on every rule and symbol. The mechanism is measured, not assumed: on the always-on rule the *gross* path barely moves (the gross annualized return of the portfolio is +13.3957%/yr for the daily-rebalanced book and +13.3901%/yr for the threshold-rebalanced one - the funding is earned on a notional that is larger after a price rise and smaller after a fall, and the two effects very nearly cancel), so almost the whole difference is the trading cost that the fewer rebalances avoid: the annualized fee drag falls from +1.7539%/yr to +1.4853%/yr under the headline model. The fixed-coin construction nets more than both, but it is **a different book, not a different rebalancing frequency**: it holds one coin quantity on both legs for the whole holding stretch, so its perp notional scales with the coin's price while its equity compounds only on the carry, and its return on equity is a different quantity from the constant-notional book's. The threshold construction does **not** converge to it as the threshold grows: at an unbounded threshold it holds equal *notional* on the two legs, whose coin quantities drift apart, and it accumulates a directional exposure to the spot's relative performance since the last rebalance.

**A portfolio-accounting caveat on the Cycle 893 fixed-coin portfolio.** The fixed-coin portfolio row above is the committed Cycle 893 number: it adds the two symbols' returns, each measured against its own equity, so each symbol's capital is counted twice. The capital-consistent account of the same construction (the capital split once at the entry, never rebalanced) is materially lower. The diagnostic below reports both, gross, so that the difference is visible and reproducible; reconciling the committed Cycle 893 portfolio number is a separate, bounded task and this section does not change it.

| Rule | Committed (sum of sub-book returns) | Capital-consistent equal-weight split | Ratio |
|---|---|---|---|
| `always_on` | +94.8821%/yr (gross) | +41.5961%/yr (gross) | 2.28x |
| `funding_positive_sameday` | +59.2260%/yr (gross) | +26.9350%/yr (gross) | 2.20x |
| `funding_positive_lagged` | +56.7270%/yr (gross) | +25.8991%/yr (gross) | 2.19x |

## The capital-consistent fixed-coin portfolio (Cycle 895 reconciliation)

The committed Cycle 893 fixed-coin portfolio adds the two symbols' **separately compounded** returns: each symbol's return is measured against its own equity and the two are added, so each symbol's capital is counted twice. This section reconciles that portfolio under a single stated convention: the capital is split **once** (half per symbol at the entry, never rebalanced), the two symbols' P&L is added against their **combined** equity, and the turnover and the capital-charge base are expressed as fractions of that combined equity. It is one book with a shared equity, not two sub-books added up. The three pre-registered rules are re-measured under the Cycle 892 headline cost model; no new trials, no change to the gate, the cost screen or the flat model.

* **Convention:** capital split once (0.5 of combined equity per symbol at entry, never rebalanced); the marked-to-market spot notionals of the two legs sum to the combined equity, so the capital base is never double-counted; turnover is entry/exit only, charged on both legs with the target notional per leg; the capital charge is the marked-to-market spot notional (fraction of combined equity) times the annual rate, divided across 365 days.

### Results (net of the Cycle 892 headline cost model, 365-day annualization)

| Rule | Sample | Sessions | Ann. net (geo) | Sharpe (canonical) | Max DD | Turnover/yr | Entries | Exits |
|---|---|---|---|---|---|---|---|---|
| `always_on` | full | 2464 | +25.4188% | 6.626 | -1.8769% | 0.30 | 2 | 0 |
| `always_on` | train | 1095 | +47.8401% | 8.060 | -1.8769% | 0.67 | 2 | 0 |
| `always_on` | val | 731 | +15.7663% | 11.305 | -0.1922% | 0.00 | 0 | 0 |
| `always_on` | test_oos | 638 | +3.6618% | 6.296 | -1.3004% | 0.00 | 0 | 0 |
| `always_on` | post2022 | 1369 | +9.9587% | 8.930 | -1.3004% | 0.00 | 0 | 0 |
| `funding_positive_lagged` | full | 2464 | +3.7769% | 1.738 | -23.8607% | 81.18 | 275 | 273 |
| `funding_positive_lagged` | train | 1095 | +12.8458% | 4.127 | -14.7899% | 89.33 | 135 | 133 |
| `funding_positive_lagged` | val | 731 | +2.1833% | 2.209 | -4.2567% | 44.94 | 45 | 45 |
| `funding_positive_lagged` | test_oos | 638 | -8.5139% | -8.480 | -14.8740% | 108.70 | 95 | 95 |
| `funding_positive_lagged` | post2022 | 1369 | -2.9493% | -2.839 | -15.2196% | 74.65 | 140 | 140 |
| `funding_positive_sameday` | full | 2464 | +4.2217% | 1.951 | -23.0761% | 81.18 | 275 | 273 |
| `funding_positive_sameday` | train | 1095 | +13.7758% | 4.449 | -14.2696% | 89.33 | 135 | 133 |
| `funding_positive_sameday` | val | 731 | +2.2281% | 2.275 | -4.1301% | 44.94 | 45 | 45 |
| `funding_positive_sameday` | test_oos | 638 | -8.3376% | -8.269 | -14.6037% | 108.70 | 95 | 95 |
| `funding_positive_sameday` | post2022 | 1369 | -2.8394% | -2.742 | -14.8431% | 74.65 | 140 | 140 |

### Break-evens (portfolio, headline cost model)

| Rule | Sample | Break-even flat cost/unit | Break-even capital charge (annual, on combined spot notionals) | Break-even venue fee multiple |
|---|---|---|---|---|
| `always_on` | full | none | +16.20% | none |
| `always_on` | test_oos | none | +4.30% | none |
| `funding_positive_lagged` | full | 15.5152 bp | +8.26% | 1.48x |
| `funding_positive_lagged` | test_oos | 2.1559 bp | -17.57% | 0.14x |
| `funding_positive_sameday` | full | 16.0505 bp | +8.94% | 1.54x |
| `funding_positive_sameday` | test_oos | 2.3458 bp | -16.86% | 0.16x |

### Promotion gate (capital-consistent fixed coin, re-evaluated, never relaxed)

| Rule | Net OOS Sharpe (canonical, 365) | Sharpe criterion | Pooled OOS round trips | Trade-count criterion | Gate |
|---|---|---|---|---|---|
| `always_on` | 5.645 | PASS | 0 | FAIL | **FAIL** |
| `funding_positive_lagged` | -5.224 | FAIL | 95 | FAIL | **FAIL** |
| `funding_positive_sameday` | -4.943 | FAIL | 95 | FAIL | **FAIL** |

The gate is evaluated on the per-symbol fixed-coin books (the positions and trades are identical to the committed Cycle 893 portfolio - only the capital aggregation changes), so the trade counts are unchanged: 0 pooled out-of-sample round trips for always-on and 95 for the funding-positive rules, against the repository's 100. The promotion gate **fails** for every rule and is never relaxed.

### Whether the Cycle 893 headline survives the reconciliation

The committed Cycle 893 headline states that the constant-notional headline was **conservative by +44.89 pp/yr (always-on) and +14.05 pp/yr (funding-positive)** because the fixed-coin book nets more on the same committed path. Those figures are computed on the committed portfolio rows, whose accounting counts each symbol's capital twice. On the capital-consistent account the comparison changes:

* `always_on`: committed fixed-coin portfolio +54.1139%/yr versus constant-notional +9.2190%/yr - the Cycle 893 headline claims a +44.8949%/yr advantage. The reconciled capital-consistent fixed-coin portfolio nets +25.4188%/yr, a +16.1998%/yr advantage over constant-notional and 15.9107%/yr over the threshold-rebalanced book (+9.5081%/yr).
* `funding_positive_lagged`: committed fixed-coin portfolio +16.0201%/yr versus constant-notional +1.9706%/yr - the Cycle 893 headline claims a +14.0495%/yr advantage. The reconciled capital-consistent fixed-coin portfolio nets +3.7769%/yr, a +1.8064%/yr advantage over constant-notional and 1.5657%/yr over the threshold-rebalanced book (+2.2113%/yr).
* `funding_positive_sameday`: committed fixed-coin portfolio +16.9965%/yr versus constant-notional +2.7733%/yr - the Cycle 893 headline claims a +14.2232%/yr advantage. The reconciled capital-consistent fixed-coin portfolio nets +4.2217%/yr, a +1.4484%/yr advantage over constant-notional and 1.2067%/yr over the threshold-rebalanced book (+3.0150%/yr).

**The Cycle 893 headline does not survive the reconciliation.** The always-on fixed-coin book still nets more than the constant-notional book, but the margin shrinks from the committed +44.89 pp/yr to +16.20 pp/yr on the capital-consistent account, and the funding-positive margin shrinks from +14.05 pp/yr to +1.81 pp/yr. The constant-notional headline remains conservative versus the implementable fixed-coin construction, but by a much smaller margin than the committed double-counted capital suggested. The per-symbol rows are unaffected by the reconciliation (each symbol's book is standalone), and on that basis the fixed-coin construction still nets more than both the daily-drift and the threshold-rebalanced books.

### The three constructions on the committed path (portfolio basis)

| Rule | Construction | Portfolio ann. net | Sharpe | Turnover/yr | Accounting |
|---|---|---|---|---|---|
| `always_on` | daily drift (pre-registered) | +9.2190% | 5.964 | 18.47 | one shared equity |
| `always_on` | threshold 2% | +9.5081% | 6.144 | 15.64 | one shared equity |
| `always_on` | fixed coin (Cycle 893, committed) | +54.1139% | 6.740 | 0.30 | sum of separately compounded sub-book returns (capital counted twice) |
| `always_on` | fixed coin (Cycle 895, reconciled) | +25.4188% | 6.626 | 0.30 | capital split once, P&L added against combined equity |
| `funding_positive_lagged` | daily drift (pre-registered) | +1.9706% | 1.088 | 96.96 | one shared equity |
| `funding_positive_lagged` | threshold 2% | +2.2113% | 1.218 | 94.42 | one shared equity |
| `funding_positive_lagged` | fixed coin (Cycle 893, committed) | +16.0201% | 3.913 | 81.18 | sum of separately compounded sub-book returns (capital counted twice) |
| `funding_positive_lagged` | fixed coin (Cycle 895, reconciled) | +3.7769% | 1.738 | 81.18 | capital split once, P&L added against combined equity |
| `funding_positive_sameday` | daily drift (pre-registered) | +2.7733% | 1.615 | 96.79 | one shared equity |
| `funding_positive_sameday` | threshold 2% | +3.0150% | 1.753 | 94.25 | one shared equity |
| `funding_positive_sameday` | fixed coin (Cycle 893, committed) | +16.9965% | 4.164 | 81.18 | sum of separately compounded sub-book returns (capital counted twice) |
| `funding_positive_sameday` | fixed coin (Cycle 895, reconciled) | +4.2217% | 1.951 | 81.18 | capital split once, P&L added against combined equity |

## Verdict

**Exploratory signal — not promoted.** Under the **realistic** cost model of this cycle (the published Binance VIP0 taker schedule plus the repository's slippage assumption, plus the repository's risk-free rate as the charge for the capital the spot leg ties up) the always-on BTC/ETH carry still nets +9.2190%/yr with a canonical Sharpe of 5.964 on the full sample, and the implementable funding-positive rule nets +1.9706%/yr with a canonical Sharpe of 1.088. The carry survives the realistic cost model, but the candidate is **not** promoted, for four measured reasons:

1. **The trade-count criterion of the promotion gate is not met** under any cost model: the pooled out-of-sample independent round trips are 95 (funding-positive) and 0 (always-on, which opens its position before the out-of-sample window), against the repository's 100.
2. **The realistic cost model removes most of the out-of-sample edge.** The always-on book's out-of-sample net return falls from +3.5123%/yr (flat model) to +0.4849%/yr and its out-of-sample canonical Sharpe from 11.144 to 1.516; the implementable funding-positive rule's out-of-sample Sharpe is **negative** under the headline model. The carry is a low-volatility, low-return stream whose out-of-sample margin does not survive a realistic fee schedule and a realistic charge for the capital.
3. The pre-registered funding-positive rule is contaminated by a look-ahead (the same day's aggregate funding). The implementable variant, which also pays for its entries and exits, is materially weaker than the Cycle 890 record reported.
4. The edge is venue-specific (Binance only), regime-dependent (2021 is the best year by a wide margin) and structurally exposed to the funding-positive regime that produced it: a long period of negative funding removes the return *and* adds trading costs.

**What the realistic model changed.** The venue fee schedule is 3x (spot) and 2x (perp) the repository's flat 3 bp per unit, and the capital charge adds 2%/yr on the spot leg's notional; together they take the always-on book from +12.7694%/yr to +9.2190%/yr. The break-even columns show how much room is left: the always-on book's break-even multiple of the published fee schedule is 6.03x and its break-even capital charge is +10.82%/yr.

The Sharpe criterion is met on the full sample, so the candidate deserves one more validation cycle (an independent venue's price and funding history, the borrow/financing side of the spot leg, and threshold-rebalanced refinements of the fixed-quantity construction measured here) before it is either promoted or rejected.

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
  "cost_model_evaluation": {
    "break_evens": {
      "always_on": {
        "full": {
          "break_even_capital_charge_annual": {
            "bracketed": true,
            "fee_model": "venue_taker_slippage",
            "note": "The annual rate charged on the spot leg's notional at which the net annualized return is exactly zero, with the trading fees held at the stated model.",
            "reason": "",
            "sample": "full",
            "solution_annual_rate": 0.108195333275944
          },
          "break_even_flat_cost_bps": {
            "bracketed": true,
            "note": "The flat cost per unit (both legs, one number) at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "full",
            "solution_bps": 68.06774032438625
          },
          "break_even_venue_fee_multiplier": {
            "bracketed": true,
            "cost_model": "realistic_rf",
            "note": "The multiple of the published fee schedule at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "full",
            "solution_multiplier": 6.027192874535103
          }
        },
        "test_oos": {
          "break_even_capital_charge_annual": {
            "bracketed": true,
            "fee_model": "venue_taker_slippage",
            "note": "The annual rate charged on the spot leg's notional at which the net annualized return is exactly zero, with the trading fees held at the stated model.",
            "reason": "",
            "sample": "test_oos",
            "solution_annual_rate": 0.024837287608534098
          },
          "break_even_flat_cost_bps": {
            "bracketed": true,
            "note": "The flat cost per unit (both legs, one number) at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "test_oos",
            "solution_bps": 26.166763003402593
          },
          "break_even_venue_fee_multiplier": {
            "bracketed": true,
            "cost_model": "realistic_rf",
            "note": "The multiple of the published fee schedule at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "test_oos",
            "solution_multiplier": 1.3417378217127407
          }
        }
      },
      "funding_positive_lagged": {
        "full": {
          "break_even_capital_charge_annual": {
            "bracketed": true,
            "fee_model": "venue_taker_slippage",
            "note": "The annual rate charged on the spot leg's notional at which the net annualized return is exactly zero, with the trading fees held at the stated model.",
            "reason": "",
            "sample": "full",
            "solution_annual_rate": 0.0421965210698545
          },
          "break_even_flat_cost_bps": {
            "bracketed": true,
            "note": "The flat cost per unit (both legs, one number) at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "full",
            "solution_bps": 13.320842811390321
          },
          "break_even_venue_fee_multiplier": {
            "bracketed": true,
            "cost_model": "realistic_rf",
            "note": "The multiple of the published fee schedule at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "full",
            "solution_multiplier": 1.2116223584598629
          }
        },
        "test_oos": {
          "break_even_capital_charge_annual": {
            "bracketed": true,
            "fee_model": "venue_taker_slippage",
            "note": "The annual rate charged on the spot leg's notional at which the net annualized return is exactly zero, with the trading fees held at the stated model.",
            "reason": "",
            "sample": "test_oos",
            "solution_annual_rate": -0.08832536498084664
          },
          "break_even_flat_cost_bps": {
            "bracketed": true,
            "note": "The flat cost per unit (both legs, one number) at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "test_oos",
            "solution_bps": 3.4369360656455683
          },
          "break_even_venue_fee_multiplier": {
            "bracketed": true,
            "cost_model": "realistic_rf",
            "note": "The multiple of the published fee schedule at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "test_oos",
            "solution_multiplier": 0.2172129421524005
          }
        }
      },
      "funding_positive_sameday": {
        "full": {
          "break_even_capital_charge_annual": {
            "bracketed": true,
            "fee_model": "venue_taker_slippage",
            "note": "The annual rate charged on the spot leg's notional at which the net annualized return is exactly zero, with the trading fees held at the stated model.",
            "reason": "",
            "sample": "full",
            "solution_annual_rate": 0.051101692486554384
          },
          "break_even_flat_cost_bps": {
            "bracketed": true,
            "note": "The flat cost per unit (both legs, one number) at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "full",
            "solution_bps": 14.137637722069485
          },
          "break_even_venue_fee_multiplier": {
            "bracketed": true,
            "cost_model": "realistic_rf",
            "note": "The multiple of the published fee schedule at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "full",
            "solution_multiplier": 1.2971819527592743
          }
        },
        "test_oos": {
          "break_even_capital_charge_annual": {
            "bracketed": true,
            "fee_model": "venue_taker_slippage",
            "note": "The annual rate charged on the spot leg's notional at which the net annualized return is exactly zero, with the trading fees held at the stated model.",
            "reason": "",
            "sample": "test_oos",
            "solution_annual_rate": -0.08306832192465663
          },
          "break_even_flat_cost_bps": {
            "bracketed": true,
            "note": "The flat cost per unit (both legs, one number) at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "test_oos",
            "solution_bps": 3.7897931116276595
          },
          "break_even_venue_fee_multiplier": {
            "bracketed": true,
            "cost_model": "realistic_rf",
            "note": "The multiple of the published fee schedule at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "test_oos",
            "solution_multiplier": 0.25415542659175117
          }
        }
      }
    },
    "fixed_coin_portfolio_accounting": {
      "always_on": {
        "capital_consistent_equal_weight_split": {
          "ann_return_geometric_gross": 0.4159606720667117,
          "note": "The capital-consistent account of the same construction: the capital is split once (half per symbol at the entry, never rebalanced) and the two books' P&L is added against their combined equity."
        },
        "committed_sum_of_sub_book_returns": {
          "ann_return_geometric_gross": 0.9488208771553963,
          "note": "The Cycle 893 accounting: the two symbols' returns are measured against their own equities and added, so each symbol's capital is counted twice."
        },
        "per_symbol_ann_return_geometric_gross": {
          "BTCUSDT": 0.31150098103423285,
          "ETHUSDT": 0.4889376511233192
        },
        "ratio_committed_over_capital_consistent": 2.2810350614185575
      },
      "funding_positive_lagged": {
        "capital_consistent_equal_weight_split": {
          "ann_return_geometric_gross": 0.25899123723809403,
          "note": "The capital-consistent account of the same construction: the capital is split once (half per symbol at the entry, never rebalanced) and the two books' P&L is added against their combined equity."
        },
        "committed_sum_of_sub_book_returns": {
          "ann_return_geometric_gross": 0.5672701463509091,
          "note": "The Cycle 893 accounting: the two symbols' returns are measured against their own equities and added, so each symbol's capital is counted twice."
        },
        "per_symbol_ann_return_geometric_gross": {
          "BTCUSDT": 0.20404743256060032,
          "ETHUSDT": 0.3028535662808234
        },
        "ratio_committed_over_capital_consistent": 2.1903063300532066
      },
      "funding_positive_sameday": {
        "capital_consistent_equal_weight_split": {
          "ann_return_geometric_gross": 0.2693496457949027,
          "note": "The capital-consistent account of the same construction: the capital is split once (half per symbol at the entry, never rebalanced) and the two books' P&L is added against their combined equity."
        },
        "committed_sum_of_sub_book_returns": {
          "ann_return_geometric_gross": 0.5922603833103977,
          "note": "The Cycle 893 accounting: the two symbols' returns are measured against their own equities and added, so each symbol's capital is counted twice."
        },
        "per_symbol_ann_return_geometric_gross": {
          "BTCUSDT": 0.21230573307268386,
          "ETHUSDT": 0.31461352863332315
        },
        "ratio_committed_over_capital_consistent": 2.198853395787929
      }
    },
    "fixed_coin_reconciled": {
      "always_on": {
        "realistic_rf": {
          "samples": {
            "full": {
              "ann_return_arithmetic": 0.22714231164388024,
              "ann_return_geometric": 0.2541880503489118,
              "ann_volatility": 0.034281071064699783,
              "annualized_capital_charge_drag": 0.03191186647421866,
              "annualized_cost_drag": 0.032193319396296584,
              "annualized_fee_drag": 0.000281452922077922,
              "annualized_turnover_perp_units": 0.1481331168831169,
              "annualized_turnover_spot_units": 0.1481331168831169,
              "annualized_turnover_units": 0.2962662337662338,
              "avg_gross_exposure": 3.1911200000297946,
              "avg_spot_notional_fraction": 1.5955933237109332,
              "downside_deviation_annualized": 0.010683031999529082,
              "end": "2026-09-30",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 1.0,
              "max_drawdown": -0.018768510503488045,
              "max_drawdown_recomputed": -0.018768510503488045,
              "position_entries": 2,
              "position_exits": 0,
              "profit_factor": 8.375090340021645,
              "rebalance_days": 1,
              "risk_free_rate_annual": 0.02,
              "sample": "full",
              "sessions": 2464,
              "sharpe_backtest_scale": 7.414822304389918,
              "sharpe_canonical": 6.625881414708052,
              "sortino_backtest_scale": 23.793624353097194,
              "sortino_canonical": 21.26197053925261,
              "start": "2020-01-02",
              "total_return": 3.6133384508409723
            },
            "post2022": {
              "ann_return_arithmetic": 0.09500325858613701,
              "ann_return_geometric": 0.09958676623533469,
              "ann_volatility": 0.010638670307837222,
              "annualized_capital_charge_drag": 0.030773962342276744,
              "annualized_cost_drag": 0.030773962342276744,
              "annualized_fee_drag": 0.0,
              "annualized_turnover_perp_units": 0.0,
              "annualized_turnover_spot_units": 0.0,
              "annualized_turnover_units": 0.0,
              "avg_gross_exposure": 3.0770034483004953,
              "avg_spot_notional_fraction": 1.538698117113837,
              "downside_deviation_annualized": 0.004269478194492408,
              "end": "2026-09-30",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 1.0,
              "max_drawdown": -0.013003848396829665,
              "max_drawdown_recomputed": -0.013003848396829665,
              "position_entries": 0,
              "position_exits": 0,
              "profit_factor": 6.662177321720742,
              "rebalance_days": 0,
              "risk_free_rate_annual": 0.02,
              "sample": "post2022",
              "sessions": 1369,
              "sharpe_backtest_scale": 9.360828313475585,
              "sharpe_canonical": 8.929993677513501,
              "sortino_backtest_scale": 23.32527810161926,
              "sortino_canonical": 22.251725915520648,
              "start": "2023-01-01",
              "total_return": 0.42770631601058273
            },
            "test_oos": {
              "ann_return_arithmetic": 0.03598151863025642,
              "ann_return_geometric": 0.03661794900980575,
              "ann_volatility": 0.0057152141330611824,
              "annualized_capital_charge_drag": 0.031214431505747656,
              "annualized_cost_drag": 0.031214431505747656,
              "annualized_fee_drag": 0.0,
              "annualized_turnover_perp_units": 0.0,
              "annualized_turnover_spot_units": 0.0,
              "annualized_turnover_units": 0.0,
              "avg_gross_exposure": 3.1207349985444357,
              "avg_spot_notional_fraction": 1.5607215752873826,
              "downside_deviation_annualized": 0.004254254037135083,
              "end": "2026-09-30",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 1.0,
              "max_drawdown": -0.013003848396828555,
              "max_drawdown_recomputed": -0.013003848396828555,
              "position_entries": 0,
              "position_exits": 0,
              "profit_factor": 2.7621350648825036,
              "rebalance_days": 0,
              "risk_free_rate_annual": 0.02,
              "sample": "test_oos",
              "sessions": 638,
              "sharpe_backtest_scale": 6.407100094111863,
              "sharpe_canonical": 6.2957428702647755,
              "sortino_backtest_scale": 8.60737245358887,
              "sortino_canonical": 8.457773869678746,
              "start": "2025-01-01",
              "total_return": 0.06488000966412777
            },
            "train": {
              "ann_return_arithmetic": 0.3923462966996341,
              "ann_return_geometric": 0.4784006521628157,
              "ann_volatility": 0.048678127016810305,
              "annualized_capital_charge_drag": 0.03333450643460998,
              "annualized_cost_drag": 0.03396783976794331,
              "annualized_fee_drag": 0.0006333333333333333,
              "annualized_turnover_perp_units": 0.3333333333333333,
              "annualized_turnover_spot_units": 0.3333333333333333,
              "annualized_turnover_units": 0.6666666666666666,
              "avg_gross_exposure": 3.333791743698663,
              "avg_spot_notional_fraction": 1.6667253217304991,
              "downside_deviation_annualized": 0.014447470421426786,
              "end": "2022-12-31",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 1.0,
              "max_drawdown": -0.018768510503488045,
              "max_drawdown_recomputed": -0.018768510503488045,
              "position_entries": 2,
              "position_exits": 0,
              "profit_factor": 9.118608755910936,
              "rebalance_days": 1,
              "risk_free_rate_annual": 0.02,
              "sample": "train",
              "sessions": 1095,
              "sharpe_backtest_scale": 9.827836062747583,
              "sharpe_canonical": 8.060012180915319,
              "sortino_backtest_scale": 33.11310826103566,
              "sortino_canonical": 27.156746839069648,
              "start": "2020-01-02",
              "total_return": 2.23129371853726
            },
            "val": {
              "ann_return_arithmetic": 0.14651607676924483,
              "ann_return_geometric": 0.15766260421657474,
              "ann_volatility": 0.012960518234016788,
              "annualized_capital_charge_drag": 0.030389530979356847,
              "annualized_cost_drag": 0.030389530979356847,
              "annualized_fee_drag": 0.0,
              "annualized_turnover_perp_units": 0.0,
              "annualized_turnover_spot_units": 0.0,
              "annualized_turnover_units": 0.0,
              "avg_gross_exposure": 3.038835556295524,
              "avg_spot_notional_fraction": 1.5194765489678423,
              "downside_deviation_annualized": 0.004300216409327743,
              "end": "2024-12-31",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 1.0,
              "max_drawdown": -0.0019223493664495273,
              "max_drawdown_recomputed": -0.0019223493664495273,
              "position_entries": 0,
              "position_exits": 0,
              "profit_factor": 11.772406163916248,
              "rebalance_days": 0,
              "risk_free_rate_annual": 0.02,
              "sample": "val",
              "sessions": 731,
              "sharpe_backtest_scale": 12.164837961707892,
              "sharpe_canonical": 11.304800789885995,
              "sortino_backtest_scale": 36.66387670038734,
              "sortino_canonical": 34.07179146878095,
              "start": "2023-01-01",
              "total_return": 0.34072036572542785
            }
          }
        }
      },
      "funding_positive_lagged": {
        "realistic_rf": {
          "samples": {
            "full": {
              "ann_return_arithmetic": 0.03730527152483237,
              "ann_return_geometric": 0.03776948202648511,
              "ann_volatility": 0.02146489983474084,
              "annualized_capital_charge_drag": 0.011841442662196448,
              "annualized_cost_drag": 0.0889595433115471,
              "annualized_fee_drag": 0.07711810064935065,
              "annualized_turnover_perp_units": 40.58847402597403,
              "annualized_turnover_spot_units": 40.58847402597403,
              "annualized_turnover_units": 81.17694805194806,
              "avg_gross_exposure": 1.1841883909579503,
              "avg_spot_notional_fraction": 0.5920721331098223,
              "downside_deviation_annualized": 0.011988987479538513,
              "end": "2026-09-30",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 0.9460227272727273,
              "max_drawdown": -0.2386074667032918,
              "max_drawdown_recomputed": -0.2386074667032918,
              "position_entries": 275,
              "position_exits": 273,
              "profit_factor": 1.4464191442497074,
              "rebalance_days": 463,
              "risk_free_rate_annual": 0.02,
              "sample": "full",
              "sessions": 2464,
              "sharpe_backtest_scale": 1.7595927452386888,
              "sharpe_canonical": 1.7379662524422295,
              "sortino_backtest_scale": 3.150347941470947,
              "sortino_canonical": 3.111628199503996,
              "start": "2020-01-02",
              "total_return": 0.2843756700695095
            },
            "post2022": {
              "ann_return_arithmetic": -0.029880156349475377,
              "ann_return_geometric": -0.029493091307487673,
              "ann_volatility": 0.010524863235882476,
              "annualized_capital_charge_drag": 0.011042296957815832,
              "annualized_cost_drag": 0.08196267679711457,
              "annualized_fee_drag": 0.07092037983929873,
              "annualized_turnover_perp_units": 37.326515704894085,
              "annualized_turnover_spot_units": 37.326515704894085,
              "annualized_turnover_units": 74.65303140978817,
              "avg_gross_exposure": 1.1041160795116711,
              "avg_spot_notional_fraction": 0.5521148478907916,
              "downside_deviation_annualized": 0.011427241084331675,
              "end": "2026-09-30",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 0.9503287070854638,
              "max_drawdown": -0.15219629919066802,
              "max_drawdown_recomputed": -0.15219629919066802,
              "position_entries": 140,
              "position_exits": 140,
              "profit_factor": 0.597461953101643,
              "rebalance_days": 238,
              "risk_free_rate_annual": 0.02,
              "sample": "post2022",
              "sessions": 1369,
              "sharpe_backtest_scale": -2.8022303612399173,
              "sharpe_canonical": -2.8390066150793096,
              "sortino_backtest_scale": -2.580945924727778,
              "sortino_canonical": -2.614818058791566,
              "start": "2023-01-01",
              "total_return": -0.10620903049608366
            },
            "test_oos": {
              "ann_return_arithmetic": -0.0889175815027289,
              "ann_return_geometric": -0.08513920085303983,
              "ann_volatility": 0.010485339624129026,
              "annualized_capital_charge_drag": 0.009092374104834492,
              "annualized_cost_drag": 0.11235648068790657,
              "annualized_fee_drag": 0.10326410658307209,
              "annualized_turnover_perp_units": 54.34952978056426,
              "annualized_turnover_spot_units": 54.34952978056426,
              "annualized_turnover_units": 108.69905956112852,
              "avg_gross_exposure": 0.9090353800745775,
              "avg_spot_notional_fraction": 0.4546187052417246,
              "downside_deviation_annualized": 0.011553691936432051,
              "end": "2026-09-30",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 0.9122257053291536,
              "max_drawdown": -0.14873996698333813,
              "max_drawdown_recomputed": -0.14873996698333813,
              "position_entries": 95,
              "position_exits": 95,
              "profit_factor": 0.15850802842853956,
              "rebalance_days": 161,
              "risk_free_rate_annual": 0.02,
              "sample": "test_oos",
              "sessions": 638,
              "sharpe_backtest_scale": -8.119832442729484,
              "sharpe_canonical": -8.480181347498785,
              "sortino_backtest_scale": -7.369003892562853,
              "sortino_canonical": -7.69603188244501,
              "start": "2025-01-01",
              "total_return": -0.14404547809236978
            },
            "train": {
              "ann_return_arithmetic": 0.12130239550650114,
              "ann_return_geometric": 0.1284579207516916,
              "ann_volatility": 0.029393216794172373,
              "annualized_capital_charge_drag": 0.012840557246029382,
              "annualized_cost_drag": 0.09770722391269603,
              "annualized_fee_drag": 0.08486666666666665,
              "annualized_turnover_perp_units": 44.666666666666664,
              "annualized_turnover_spot_units": 44.666666666666664,
              "annualized_turnover_units": 89.33333333333333,
              "avg_gross_exposure": 1.284297061615444,
              "avg_spot_notional_fraction": 0.642027862301469,
              "downside_deviation_annualized": 0.012540882325345924,
              "end": "2022-12-31",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 0.9406392694063926,
              "max_drawdown": -0.14789926773120066,
              "max_drawdown_recomputed": -0.14789926773120066,
              "position_entries": 135,
              "position_exits": 133,
              "profit_factor": 2.273677433920928,
              "rebalance_days": 225,
              "risk_free_rate_annual": 0.02,
              "sample": "train",
              "sessions": 1095,
              "sharpe_backtest_scale": 4.370325359460494,
              "sharpe_canonical": 4.1268839799307395,
              "sortino_backtest_scale": 10.243132613729255,
              "sortino_canonical": 9.672556711686964,
              "start": "2020-01-02",
              "total_return": 0.4369978148049307
            },
            "val": {
              "ann_return_arithmetic": 0.021646351513418958,
              "ann_return_geometric": 0.021832677214858043,
              "ann_volatility": 0.009798957644950645,
              "annualized_capital_charge_drag": 0.01274414481034948,
              "annualized_cost_drag": 0.055435663278201736,
              "annualized_fee_drag": 0.042691518467852255,
              "annualized_turnover_perp_units": 22.46922024623803,
              "annualized_turnover_spot_units": 22.46922024623803,
              "annualized_turnover_units": 44.93844049247606,
              "avg_gross_exposure": 1.2743780305935664,
              "avg_spot_notional_fraction": 0.637207240517474,
              "downside_deviation_annualized": 0.010991176287392235,
              "end": "2024-12-31",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 0.9835841313269493,
              "max_drawdown": -0.042567256341840554,
              "max_drawdown_recomputed": -0.042567256341840554,
              "position_entries": 45,
              "position_exits": 45,
              "profit_factor": 1.4626105011342705,
              "rebalance_days": 77,
              "risk_free_rate_annual": 0.02,
              "sample": "val",
              "sessions": 731,
              "sharpe_backtest_scale": 2.2280611883355075,
              "sharpe_canonical": 2.209046339186211,
              "sortino_backtest_scale": 1.9863822255222932,
              "sortino_canonical": 1.9694299270087285,
              "start": "2023-01-01",
              "total_return": 0.0442038059591785
            }
          }
        }
      },
      "funding_positive_sameday": {
        "realistic_rf": {
          "samples": {
            "full": {
              "ann_return_arithmetic": 0.0415786591005969,
              "ann_return_geometric": 0.042216607880321444,
              "ann_volatility": 0.02131647514397219,
              "annualized_capital_charge_drag": 0.011919725050155242,
              "annualized_cost_drag": 0.0890378256995059,
              "annualized_fee_drag": 0.07711810064935065,
              "annualized_turnover_perp_units": 40.58847402597403,
              "annualized_turnover_spot_units": 40.58847402597403,
              "annualized_turnover_units": 81.17694805194806,
              "avg_gross_exposure": 1.192016507329034,
              "avg_spot_notional_fraction": 0.5959862525077622,
              "downside_deviation_annualized": 0.011314172568223705,
              "end": "2026-09-30",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 0.9464285714285714,
              "max_drawdown": -0.23076121846186326,
              "max_drawdown_recomputed": -0.23076121846186326,
              "position_entries": 275,
              "position_exits": 273,
              "profit_factor": 1.5148262742388996,
              "rebalance_days": 463,
              "risk_free_rate_annual": 0.02,
              "sample": "full",
              "sessions": 2464,
              "sharpe_backtest_scale": 1.9804685153239012,
              "sharpe_canonical": 1.9505410167381447,
              "sortino_backtest_scale": 3.7313031620967525,
              "sortino_canonical": 3.674918236387183,
              "start": "2020-01-02",
              "total_return": 0.3219917005930377
            },
            "post2022": {
              "ann_return_arithmetic": -0.028749308520724177,
              "ann_return_geometric": -0.02839447508917159,
              "ann_volatility": 0.01048449813105832,
              "annualized_capital_charge_drag": 0.011079807681507028,
              "annualized_cost_drag": 0.08200018752080576,
              "annualized_fee_drag": 0.07092037983929873,
              "annualized_turnover_perp_units": 37.326515704894085,
              "annualized_turnover_spot_units": 37.326515704894085,
              "annualized_turnover_units": 74.65303140978817,
              "avg_gross_exposure": 1.1078655172802891,
              "avg_spot_notional_fraction": 0.5539903840753514,
              "downside_deviation_annualized": 0.011420890175134854,
              "end": "2026-09-30",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 0.9503287070854638,
              "max_drawdown": -0.14843132160660655,
              "max_drawdown_recomputed": -0.14843132160660655,
              "position_entries": 140,
              "position_exits": 140,
              "profit_factor": 0.6088100002168069,
              "rebalance_days": 238,
              "risk_free_rate_annual": 0.02,
              "sample": "post2022",
              "sessions": 1369,
              "sharpe_backtest_scale": -2.7082340741764632,
              "sharpe_canonical": -2.7420776999864063,
              "sortino_backtest_scale": -2.48618756101788,
              "sortino_canonical": -2.5172563679244657,
              "start": "2023-01-01",
              "total_return": -0.10240827449202405
            },
            "test_oos": {
              "ann_return_arithmetic": -0.08699260349383724,
              "ann_return_geometric": -0.08337633040944503,
              "ann_volatility": 0.010520495319822682,
              "annualized_capital_charge_drag": 0.009233208298161594,
              "annualized_cost_drag": 0.11249731488123367,
              "annualized_fee_drag": 0.10326410658307207,
              "annualized_turnover_perp_units": 54.34952978056426,
              "annualized_turnover_spot_units": 54.34952978056426,
              "annualized_turnover_units": 108.69905956112852,
              "avg_gross_exposure": 0.9231169429292186,
              "avg_spot_notional_fraction": 0.4616604149080797,
              "downside_deviation_annualized": 0.011406847641730092,
              "end": "2026-09-30",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 0.9122257053291536,
              "max_drawdown": -0.14603687858586556,
              "max_drawdown_recomputed": -0.14603687858586556,
              "position_entries": 95,
              "position_exits": 95,
              "profit_factor": 0.1700295387099687,
              "rebalance_days": 161,
              "risk_free_rate_annual": 0.02,
              "sample": "test_oos",
              "sessions": 638,
              "sharpe_backtest_scale": -7.925133548830884,
              "sharpe_canonical": -8.268869558824484,
              "sortino_backtest_scale": -7.3093227005528085,
              "sortino_canonical": -7.626349209363416,
              "start": "2025-01-01",
              "total_return": -0.14116040593546897
            },
            "train": {
              "ann_return_arithmetic": 0.12950467524086046,
              "ann_return_geometric": 0.1377581700100241,
              "ann_volatility": 0.029109998395456943,
              "annualized_capital_charge_drag": 0.01296981352292183,
              "annualized_cost_drag": 0.09783648018958849,
              "annualized_fee_drag": 0.08486666666666666,
              "annualized_turnover_perp_units": 44.666666666666664,
              "annualized_turnover_spot_units": 44.666666666666664,
              "annualized_turnover_units": 89.33333333333333,
              "avg_gross_exposure": 1.2972244574447709,
              "avg_spot_notional_fraction": 0.6484906761460913,
              "downside_deviation_annualized": 0.011195643881126234,
              "end": "2022-12-31",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 0.9415525114155251,
              "max_drawdown": -0.14269592319148927,
              "max_drawdown_recomputed": -0.14269592319148927,
              "position_entries": 135,
              "position_exits": 133,
              "profit_factor": 2.441304890878061,
              "rebalance_days": 225,
              "risk_free_rate_annual": 0.02,
              "sample": "train",
              "sessions": 1095,
              "sharpe_backtest_scale": 4.732331762392792,
              "sharpe_canonical": 4.448803929205012,
              "sortino_backtest_scale": 12.304622357831395,
              "sortino_canonical": 11.567416453749583,
              "start": "2020-01-02",
              "total_return": 0.47282073020991633
            },
            "val": {
              "ann_return_arithmetic": 0.022084100771815003,
              "ann_return_geometric": 0.022280981387545085,
              "ann_volatility": 0.00970585439803809,
              "annualized_capital_charge_drag": 0.012691477184344765,
              "annualized_cost_drag": 0.05538299565219702,
              "annualized_fee_drag": 0.042691518467852255,
              "annualized_turnover_perp_units": 22.46922024623803,
              "annualized_turnover_spot_units": 22.46922024623803,
              "annualized_turnover_units": 44.93844049247606,
              "avg_gross_exposure": 1.2691098270422354,
              "avg_spot_notional_fraction": 0.6345738592172382,
              "downside_deviation_annualized": 0.010988045080681755,
              "end": "2024-12-31",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 0.9835841313269493,
              "max_drawdown": -0.04130057678265109,
              "max_drawdown_recomputed": -0.04130057678265109,
              "position_entries": 45,
              "position_exits": 45,
              "profit_factor": 1.4784803548689038,
              "rebalance_days": 77,
              "risk_free_rate_annual": 0.02,
              "sample": "val",
              "sessions": 731,
              "sharpe_backtest_scale": 2.295622876029223,
              "sharpe_canonical": 2.2753381481056434,
              "sortino_backtest_scale": 2.0277475405263496,
              "sortino_canonical": 2.009829829570083,
              "start": "2023-01-01",
              "total_return": 0.04512150081489219
            }
          }
        }
      }
    },
    "fixed_coin_reconciled_break_evens": {
      "always_on": {
        "full": {
          "break_even_capital_charge_annual": {
            "bracketed": true,
            "fee_model": "venue_taker_slippage",
            "note": "The annual rate charged on the spot leg's notional at which the net annualized return is exactly zero, with the trading fees held at the stated model.",
            "reason": "",
            "sample": "full",
            "solution_annual_rate": 0.16202792571857572
          },
          "break_even_flat_cost_bps": {
            "bracketed": false,
            "note": "The flat cost per unit (both legs, one number) at which the net annualized return is exactly zero.",
            "reason": "objective does not change sign inside the bracket",
            "sample": "full",
            "solution_bps": null
          },
          "break_even_venue_fee_multiplier": {
            "bracketed": false,
            "cost_model": "realistic_rf",
            "note": "The multiple of the published fee schedule at which the net annualized return is exactly zero.",
            "reason": "objective does not change sign inside the bracket",
            "sample": "full",
            "solution_multiplier": null
          }
        },
        "test_oos": {
          "break_even_capital_charge_annual": {
            "bracketed": true,
            "fee_model": "venue_taker_slippage",
            "note": "The annual rate charged on the spot leg's notional at which the net annualized return is exactly zero, with the trading fees held at the stated model.",
            "reason": "",
            "sample": "test_oos",
            "solution_annual_rate": 0.04304452193900943
          },
          "break_even_flat_cost_bps": {
            "bracketed": false,
            "note": "The flat cost per unit (both legs, one number) at which the net annualized return is exactly zero.",
            "reason": "objective does not change sign inside the bracket",
            "sample": "test_oos",
            "solution_bps": null
          },
          "break_even_venue_fee_multiplier": {
            "bracketed": false,
            "cost_model": "realistic_rf",
            "note": "The multiple of the published fee schedule at which the net annualized return is exactly zero.",
            "reason": "objective does not change sign inside the bracket",
            "sample": "test_oos",
            "solution_multiplier": null
          }
        }
      },
      "funding_positive_lagged": {
        "full": {
          "break_even_capital_charge_annual": {
            "bracketed": true,
            "fee_model": "venue_taker_slippage",
            "note": "The annual rate charged on the spot leg's notional at which the net annualized return is exactly zero, with the trading fees held at the stated model.",
            "reason": "",
            "sample": "full",
            "solution_annual_rate": 0.08264607796445489
          },
          "break_even_flat_cost_bps": {
            "bracketed": true,
            "note": "The flat cost per unit (both legs, one number) at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "full",
            "solution_bps": 15.515155004595726
          },
          "break_even_venue_fee_multiplier": {
            "bracketed": true,
            "cost_model": "realistic_rf",
            "note": "The multiple of the published fee schedule at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "full",
            "solution_multiplier": 1.479997054047999
          }
        },
        "test_oos": {
          "break_even_capital_charge_annual": {
            "bracketed": true,
            "fee_model": "venue_taker_slippage",
            "note": "The annual rate charged on the spot leg's notional at which the net annualized return is exactly zero, with the trading fees held at the stated model.",
            "reason": "",
            "sample": "test_oos",
            "solution_annual_rate": -0.1757345604710281
          },
          "break_even_flat_cost_bps": {
            "bracketed": true,
            "note": "The flat cost per unit (both legs, one number) at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "test_oos",
            "solution_bps": 2.155852836676786
          },
          "break_even_venue_fee_multiplier": {
            "bracketed": true,
            "cost_model": "realistic_rf",
            "note": "The multiple of the published fee schedule at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "test_oos",
            "solution_multiplier": 0.1389047047268832
          }
        }
      },
      "funding_positive_sameday": {
        "full": {
          "break_even_capital_charge_annual": {
            "bracketed": true,
            "fee_model": "venue_taker_slippage",
            "note": "The annual rate charged on the spot leg's notional at which the net annualized return is exactly zero, with the trading fees held at the stated model.",
            "reason": "",
            "sample": "full",
            "solution_annual_rate": 0.0894132605753839
          },
          "break_even_flat_cost_bps": {
            "bracketed": true,
            "note": "The flat cost per unit (both legs, one number) at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "full",
            "solution_bps": 16.050490968791564
          },
          "break_even_venue_fee_multiplier": {
            "bracketed": true,
            "cost_model": "realistic_rf",
            "note": "The multiple of the published fee schedule at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "full",
            "solution_multiplier": 1.5353462640632642
          }
        },
        "test_oos": {
          "break_even_capital_charge_annual": {
            "bracketed": true,
            "fee_model": "venue_taker_slippage",
            "note": "The annual rate charged on the spot leg's notional at which the net annualized return is exactly zero, with the trading fees held at the stated model.",
            "reason": "",
            "sample": "test_oos",
            "solution_annual_rate": -0.16858028015121818
          },
          "break_even_flat_cost_bps": {
            "bracketed": true,
            "note": "The flat cost per unit (both legs, one number) at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "test_oos",
            "solution_bps": 2.345842036174872
          },
          "break_even_venue_fee_multiplier": {
            "bracketed": true,
            "cost_model": "realistic_rf",
            "note": "The multiple of the published fee schedule at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "test_oos",
            "solution_multiplier": 0.1575424768816447
          }
        }
      }
    },
    "gates": {
      "always_on": {
        "flat_3bp": {
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
        "flat_3bp_capital_rf": {
          "gate_pass_note": "The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.",
          "min_pooled_oos_trades": 100,
          "net_oos_sharpe_canonical_365": 3.9361759261455935,
          "net_oos_sharpe_min": 0.9,
          "pooled_oos_position_round_trips": 0,
          "pooled_oos_rebalance_days_repo_convention": 1276,
          "pooled_oos_settlement_observations": 3828,
          "promotion_gate_pass": false,
          "sharpe_criterion_pass": true,
          "trade_count_criterion_pass": false
        },
        "realistic_no_capital_charge": {
          "gate_pass_note": "The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.",
          "min_pooled_oos_trades": 100,
          "net_oos_sharpe_canonical_365": 6.576697948284435,
          "net_oos_sharpe_min": 0.9,
          "pooled_oos_position_round_trips": 0,
          "pooled_oos_rebalance_days_repo_convention": 1276,
          "pooled_oos_settlement_observations": 3828,
          "promotion_gate_pass": false,
          "sharpe_criterion_pass": true,
          "trade_count_criterion_pass": false
        },
        "realistic_rf": {
          "gate_pass_note": "The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.",
          "min_pooled_oos_trades": 100,
          "net_oos_sharpe_canonical_365": 1.4116469529792166,
          "net_oos_sharpe_min": 0.9,
          "pooled_oos_position_round_trips": 0,
          "pooled_oos_rebalance_days_repo_convention": 1276,
          "pooled_oos_settlement_observations": 3828,
          "promotion_gate_pass": false,
          "sharpe_criterion_pass": true,
          "trade_count_criterion_pass": false
        },
        "realistic_usdt_5pct": {
          "gate_pass_note": "The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.",
          "min_pooled_oos_trades": 100,
          "net_oos_sharpe_canonical_365": -6.335929539978615,
          "net_oos_sharpe_min": 0.9,
          "pooled_oos_position_round_trips": 0,
          "pooled_oos_rebalance_days_repo_convention": 1276,
          "pooled_oos_settlement_observations": 3828,
          "promotion_gate_pass": false,
          "sharpe_criterion_pass": false,
          "trade_count_criterion_pass": false
        },
        "venue_maker_slippage": {
          "gate_pass_note": "The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.",
          "min_pooled_oos_trades": 100,
          "net_oos_sharpe_canonical_365": 7.185325829493877,
          "net_oos_sharpe_min": 0.9,
          "pooled_oos_position_round_trips": 0,
          "pooled_oos_rebalance_days_repo_convention": 1276,
          "pooled_oos_settlement_observations": 3828,
          "promotion_gate_pass": false,
          "sharpe_criterion_pass": true,
          "trade_count_criterion_pass": false
        },
        "venue_taker": {
          "gate_pass_note": "The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.",
          "min_pooled_oos_trades": 100,
          "net_oos_sharpe_canonical_365": 7.388335607515721,
          "net_oos_sharpe_min": 0.9,
          "pooled_oos_position_round_trips": 0,
          "pooled_oos_rebalance_days_repo_convention": 1276,
          "pooled_oos_settlement_observations": 3828,
          "promotion_gate_pass": false,
          "sharpe_criterion_pass": true,
          "trade_count_criterion_pass": false
        },
        "venue_taker_slippage": {
          "gate_pass_note": "The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.",
          "min_pooled_oos_trades": 100,
          "net_oos_sharpe_canonical_365": 6.576697948284435,
          "net_oos_sharpe_min": 0.9,
          "pooled_oos_position_round_trips": 0,
          "pooled_oos_rebalance_days_repo_convention": 1276,
          "pooled_oos_settlement_observations": 3828,
          "promotion_gate_pass": false,
          "sharpe_criterion_pass": true,
          "trade_count_criterion_pass": false
        }
      },
      "funding_positive_lagged": {
        "flat_3bp": {
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
        "flat_3bp_capital_rf": {
          "gate_pass_note": "The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.",
          "min_pooled_oos_trades": 100,
          "net_oos_sharpe_canonical_365": -1.9612867792302175,
          "net_oos_sharpe_min": 0.9,
          "pooled_oos_position_round_trips": 95,
          "pooled_oos_rebalance_days_repo_convention": 1154,
          "pooled_oos_settlement_observations": 3828,
          "promotion_gate_pass": false,
          "sharpe_criterion_pass": false,
          "trade_count_criterion_pass": false
        },
        "realistic_no_capital_charge": {
          "gate_pass_note": "The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.",
          "min_pooled_oos_trades": 100,
          "net_oos_sharpe_canonical_365": -5.1939090306461235,
          "net_oos_sharpe_min": 0.9,
          "pooled_oos_position_round_trips": 95,
          "pooled_oos_rebalance_days_repo_convention": 1154,
          "pooled_oos_settlement_observations": 3828,
          "promotion_gate_pass": false,
          "sharpe_criterion_pass": false,
          "trade_count_criterion_pass": false
        },
        "realistic_rf": {
          "gate_pass_note": "The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.",
          "min_pooled_oos_trades": 100,
          "net_oos_sharpe_canonical_365": -6.45925537793317,
          "net_oos_sharpe_min": 0.9,
          "pooled_oos_position_round_trips": 95,
          "pooled_oos_rebalance_days_repo_convention": 1154,
          "pooled_oos_settlement_observations": 3828,
          "promotion_gate_pass": false,
          "sharpe_criterion_pass": false,
          "trade_count_criterion_pass": false
        },
        "realistic_usdt_5pct": {
          "gate_pass_note": "The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.",
          "min_pooled_oos_trades": 100,
          "net_oos_sharpe_canonical_365": -8.397861016566758,
          "net_oos_sharpe_min": 0.9,
          "pooled_oos_position_round_trips": 95,
          "pooled_oos_rebalance_days_repo_convention": 1154,
          "pooled_oos_settlement_observations": 3828,
          "promotion_gate_pass": false,
          "sharpe_criterion_pass": false,
          "trade_count_criterion_pass": false
        },
        "venue_maker_slippage": {
          "gate_pass_note": "The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.",
          "min_pooled_oos_trades": 100,
          "net_oos_sharpe_canonical_365": -4.5395524598257655,
          "net_oos_sharpe_min": 0.9,
          "pooled_oos_position_round_trips": 95,
          "pooled_oos_rebalance_days_repo_convention": 1154,
          "pooled_oos_settlement_observations": 3828,
          "promotion_gate_pass": false,
          "sharpe_criterion_pass": false,
          "trade_count_criterion_pass": false
        },
        "venue_taker": {
          "gate_pass_note": "The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.",
          "min_pooled_oos_trades": 100,
          "net_oos_sharpe_canonical_365": -4.269411757535707,
          "net_oos_sharpe_min": 0.9,
          "pooled_oos_position_round_trips": 95,
          "pooled_oos_rebalance_days_repo_convention": 1154,
          "pooled_oos_settlement_observations": 3828,
          "promotion_gate_pass": false,
          "sharpe_criterion_pass": false,
          "trade_count_criterion_pass": false
        },
        "venue_taker_slippage": {
          "gate_pass_note": "The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.",
          "min_pooled_oos_trades": 100,
          "net_oos_sharpe_canonical_365": -5.1939090306461235,
          "net_oos_sharpe_min": 0.9,
          "pooled_oos_position_round_trips": 95,
          "pooled_oos_rebalance_days_repo_convention": 1154,
          "pooled_oos_settlement_observations": 3828,
          "promotion_gate_pass": false,
          "sharpe_criterion_pass": false,
          "trade_count_criterion_pass": false
        }
      },
      "funding_positive_sameday": {
        "flat_3bp": {
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
        },
        "flat_3bp_capital_rf": {
          "gate_pass_note": "The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.",
          "min_pooled_oos_trades": 100,
          "net_oos_sharpe_canonical_365": -1.2856474528917414,
          "net_oos_sharpe_min": 0.9,
          "pooled_oos_position_round_trips": 95,
          "pooled_oos_rebalance_days_repo_convention": 1154,
          "pooled_oos_settlement_observations": 3828,
          "promotion_gate_pass": false,
          "sharpe_criterion_pass": false,
          "trade_count_criterion_pass": false
        },
        "realistic_no_capital_charge": {
          "gate_pass_note": "The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.",
          "min_pooled_oos_trades": 100,
          "net_oos_sharpe_canonical_365": -4.940762700978757,
          "net_oos_sharpe_min": 0.9,
          "pooled_oos_position_round_trips": 95,
          "pooled_oos_rebalance_days_repo_convention": 1154,
          "pooled_oos_settlement_observations": 3828,
          "promotion_gate_pass": false,
          "sharpe_criterion_pass": false,
          "trade_count_criterion_pass": false
        },
        "realistic_rf": {
          "gate_pass_note": "The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.",
          "min_pooled_oos_trades": 100,
          "net_oos_sharpe_canonical_365": -6.220178769039983,
          "net_oos_sharpe_min": 0.9,
          "pooled_oos_position_round_trips": 95,
          "pooled_oos_rebalance_days_repo_convention": 1154,
          "pooled_oos_settlement_observations": 3828,
          "promotion_gate_pass": false,
          "sharpe_criterion_pass": false,
          "trade_count_criterion_pass": false
        },
        "realistic_usdt_5pct": {
          "gate_pass_note": "The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.",
          "min_pooled_oos_trades": 100,
          "net_oos_sharpe_canonical_365": -8.182918085107076,
          "net_oos_sharpe_min": 0.9,
          "pooled_oos_position_round_trips": 95,
          "pooled_oos_rebalance_days_repo_convention": 1154,
          "pooled_oos_settlement_observations": 3828,
          "promotion_gate_pass": false,
          "sharpe_criterion_pass": false,
          "trade_count_criterion_pass": false
        },
        "venue_maker_slippage": {
          "gate_pass_note": "The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.",
          "min_pooled_oos_trades": 100,
          "net_oos_sharpe_canonical_365": -4.241941489765794,
          "net_oos_sharpe_min": 0.9,
          "pooled_oos_position_round_trips": 95,
          "pooled_oos_rebalance_days_repo_convention": 1154,
          "pooled_oos_settlement_observations": 3828,
          "promotion_gate_pass": false,
          "sharpe_criterion_pass": false,
          "trade_count_criterion_pass": false
        },
        "venue_taker": {
          "gate_pass_note": "The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.",
          "min_pooled_oos_trades": 100,
          "net_oos_sharpe_canonical_365": -3.952913539397108,
          "net_oos_sharpe_min": 0.9,
          "pooled_oos_position_round_trips": 95,
          "pooled_oos_rebalance_days_repo_convention": 1154,
          "pooled_oos_settlement_observations": 3828,
          "promotion_gate_pass": false,
          "sharpe_criterion_pass": false,
          "trade_count_criterion_pass": false
        },
        "venue_taker_slippage": {
          "gate_pass_note": "The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.",
          "min_pooled_oos_trades": 100,
          "net_oos_sharpe_canonical_365": -4.940762700978757,
          "net_oos_sharpe_min": 0.9,
          "pooled_oos_position_round_trips": 95,
          "pooled_oos_rebalance_days_repo_convention": 1154,
          "pooled_oos_settlement_observations": 3828,
          "promotion_gate_pass": false,
          "sharpe_criterion_pass": false,
          "trade_count_criterion_pass": false
        }
      }
    },
    "headline_cost_model": "realistic_rf",
    "headline_turnover_convention": "drift",
    "per_symbol": {
      "always_on": {
        "realistic_rf": {
          "BTCUSDT": {
            "full": {
              "ann_return_arithmetic": 0.08107319095086563,
              "ann_return_geometric": 0.08434195149957624,
              "ann_volatility": 0.013489443394123432,
              "annualized_capital_charge_drag": 0.02,
              "annualized_cost_drag": 0.034875577527905356,
              "annualized_fee_drag": 0.014875577527905356,
              "annualized_turnover_perp_units": 7.837953879120338,
              "annualized_turnover_spot_units": 7.8241748437676,
              "annualized_turnover_units": 15.66212872288794,
              "avg_spot_notional_fraction": 1.0,
              "invested_fraction": 1.0,
              "max_drawdown": -0.028592995793232823,
              "position_entries": 1,
              "position_exits": 0,
              "rebalance_days": 2464,
              "sessions": 2464,
              "sharpe_backtest_scale": 6.252441189405868,
              "sharpe_canonical": 6.010121291304318
            },
            "post2022": {
              "ann_return_arithmetic": 0.0404187519256596,
              "ann_return_geometric": 0.04122712832146247,
              "ann_volatility": 0.0057597580930329375,
              "annualized_capital_charge_drag": 0.02,
              "annualized_cost_drag": 0.031730512904515014,
              "annualized_fee_drag": 0.011730512904515013,
              "annualized_turnover_perp_units": 6.178120730133934,
              "annualized_turnover_spot_units": 6.171523661184383,
              "annualized_turnover_units": 12.349644391318316,
              "avg_spot_notional_fraction": 1.0,
              "invested_fraction": 1.0,
              "max_drawdown": -0.013217948163700366,
              "position_entries": 0,
              "position_exits": 0,
              "rebalance_days": 1369,
              "sessions": 1369,
              "sharpe_backtest_scale": 7.157788166716798,
              "sharpe_canonical": 7.0174391481042475
            },
            "test_oos": {
              "ann_return_arithmetic": 0.010880114750584247,
              "ann_return_geometric": 0.0109331386312852,
              "ann_volatility": 0.0035095960610079806,
              "annualized_capital_charge_drag": 0.02,
              "annualized_cost_drag": 0.031037245101014767,
              "annualized_fee_drag": 0.011037245101014767,
              "annualized_turnover_perp_units": 5.811416918002974,
              "annualized_turnover_spot_units": 5.8077110486772385,
              "annualized_turnover_units": 11.619127966680214,
              "avg_spot_notional_fraction": 1.0,
              "invested_fraction": 1.0,
              "max_drawdown": -0.013217948163700921,
              "position_entries": 0,
              "position_exits": 0,
              "rebalance_days": 638,
              "sessions": 638,
              "sharpe_backtest_scale": 3.1152128168690516,
              "sharpe_canonical": 3.1001045594573076
            },
            "train": {
              "ann_return_arithmetic": 0.13190052156776705,
              "ann_return_geometric": 0.14076520255193836,
              "ann_volatility": 0.018853023668962722,
              "annualized_capital_charge_drag": 0.02,
              "annualized_cost_drag": 0.03880762635842716,
              "annualized_fee_drag": 0.018807626358427164,
              "annualized_turnover_perp_units": 9.913124272693297,
              "annualized_turnover_spot_units": 9.890366139618214,
              "annualized_turnover_units": 19.803490412311508,
              "avg_spot_notional_fraction": 1.0,
              "invested_fraction": 1.0,
              "max_drawdown": -0.028592995793232823,
              "position_entries": 1,
              "position_exits": 0,
              "rebalance_days": 1095,
              "sessions": 1095,
              "sharpe_backtest_scale": 7.466452332719272,
              "sharpe_canonical": 6.996252902653048
            },
            "val": {
              "ann_return_arithmetic": 0.06619939558872125,
              "ann_return_geometric": 0.06840799906404738,
              "ann_volatility": 0.0068926013984201865,
              "annualized_capital_charge_drag": 0.02,
              "annualized_cost_drag": 0.03233558111057952,
              "annualized_fee_drag": 0.012335581110579523,
              "annualized_turnover_perp_units": 6.498171389695564,
              "annualized_turnover_spot_units": 6.489050948160524,
              "annualized_turnover_units": 12.987222337856089,
              "avg_spot_notional_fraction": 1.0,
              "invested_fraction": 1.0,
              "max_drawdown": -0.004624420745970137,
              "position_entries": 0,
              "position_exits": 0,
              "rebalance_days": 731,
              "sessions": 731,
              "sharpe_backtest_scale": 9.924844787880346,
              "sharpe_canonical": 9.604413741942835
            }
          },
          "ETHUSDT": {
            "full": {
              "ann_return_arithmetic": 0.09553657991595053,
              "ann_return_geometric": 0.1000576659597261,
              "ann_volatility": 0.017978613926166724,
              "annualized_capital_charge_drag": 0.02,
              "annualized_cost_drag": 0.04020293636832828,
              "annualized_fee_drag": 0.02020293636832828,
              "annualized_turnover_perp_units": 10.647880386106714,
              "annualized_turnover_spot_units": 10.624516748377983,
              "annualized_turnover_units": 21.2723971344847,
              "avg_spot_notional_fraction": 1.0,
              "invested_fraction": 1.0,
              "max_drawdown": -0.039772359016844616,
              "position_entries": 1,
              "position_exits": 0,
              "rebalance_days": 2464,
              "sessions": 2464,
              "sharpe_backtest_scale": 5.5653715225565055,
              "sharpe_canonical": 5.313901300083159
            },
            "post2022": {
              "ann_return_arithmetic": 0.03747531253290634,
              "ann_return_geometric": 0.0381637711892584,
              "ann_volatility": 0.006303021881323162,
              "annualized_capital_charge_drag": 0.02,
              "annualized_cost_drag": 0.03570285369465649,
              "annualized_fee_drag": 0.01570285369465649,
              "annualized_turnover_perp_units": 8.269804993354063,
              "annualized_turnover_spot_units": 8.261658499423875,
              "annualized_turnover_units": 16.531463492777934,
              "avg_spot_notional_fraction": 1.0,
              "invested_fraction": 1.0,
              "max_drawdown": -0.017746285109485394,
              "position_entries": 0,
              "position_exits": 0,
              "rebalance_days": 1369,
              "sessions": 1369,
              "sharpe_backtest_scale": 6.054837172998496,
              "sharpe_canonical": 5.945610413308502
            },
            "test_oos": {
              "ann_return_arithmetic": -0.0011953544684568534,
              "ann_return_geometric": -0.0012039423485151746,
              "ann_volatility": 0.0043183109224577375,
              "annualized_capital_charge_drag": 0.02,
              "annualized_cost_drag": 0.03727125774677188,
              "annualized_fee_drag": 0.017271257746771886,
              "annualized_turnover_perp_units": 9.093666523546988,
              "annualized_turnover_spot_units": 9.08807598357416,
              "annualized_turnover_units": 18.181742507121147,
              "avg_spot_notional_fraction": 1.0,
              "invested_fraction": 1.0,
              "max_drawdown": -0.017746285109486726,
              "position_entries": 0,
              "position_exits": 0,
              "rebalance_days": 638,
              "sessions": 638,
              "sharpe_backtest_scale": -0.27879936626470586,
              "sharpe_canonical": -0.2768106534988744
            },
            "train": {
              "ann_return_arithmetic": 0.16812642014187518,
              "ann_return_geometric": 0.1826552717521619,
              "ann_volatility": 0.025534810038977795,
              "annualized_capital_charge_drag": 0.02,
              "annualized_cost_drag": 0.04582906712655355,
              "annualized_fee_drag": 0.025829067126553553,
              "annualized_turnover_perp_units": 13.621017566634913,
              "annualized_turnover_spot_units": 13.578629024924265,
              "annualized_turnover_units": 27.199646591559176,
              "avg_spot_notional_fraction": 1.0,
              "invested_fraction": 1.0,
              "max_drawdown": -0.039772359016844616,
              "position_entries": 1,
              "position_exits": 0,
              "rebalance_days": 1095,
              "sessions": 1095,
              "sharpe_backtest_scale": 7.15318702090779,
              "sharpe_canonical": 6.58420485154334
            },
            "val": {
              "ann_return_arithmetic": 0.07122618195406874,
              "ann_return_geometric": 0.07378903784464774,
              "ann_volatility": 0.007174353988253047,
              "annualized_capital_charge_drag": 0.02,
              "annualized_cost_drag": 0.03433398668337111,
              "annualized_fee_drag": 0.014333986683371103,
              "annualized_turnover_perp_units": 7.550757583965434,
              "annualized_turnover_spot_units": 7.540380312162751,
              "annualized_turnover_units": 15.091137896128187,
              "avg_spot_notional_fraction": 1.0,
              "invested_fraction": 1.0,
              "max_drawdown": -0.0030865796564878423,
              "position_entries": 0,
              "position_exits": 0,
              "rebalance_days": 731,
              "sessions": 731,
              "sharpe_backtest_scale": 10.285112494513998,
              "sharpe_canonical": 9.927887872649046
            }
          }
        }
      },
      "funding_positive_lagged": {
        "realistic_rf": {
          "BTCUSDT": {
            "full": {
              "ann_return_arithmetic": 0.012004962137140937,
              "ann_return_geometric": 0.011905859253431794,
              "ann_volatility": 0.018399054458607705,
              "annualized_capital_charge_drag": 0.017564935064935065,
              "annualized_cost_drag": 0.10710592450061972,
              "annualized_fee_drag": 0.08954098943568466,
              "annualized_turnover_perp_units": 47.135878473350886,
              "annualized_turnover_spot_units": 47.121562086949204,
              "annualized_turnover_units": 94.25744056030008,
              "avg_spot_notional_fraction": 0.8782467532467533,
              "invested_fraction": 0.8782467532467533,
              "max_drawdown": -0.20199522085517363,
              "position_entries": 137,
              "position_exits": 136,
              "rebalance_days": 2300,
              "sessions": 2464,
              "sharpe_backtest_scale": 0.6470908209014962,
              "sharpe_canonical": 0.6524771239820211
            },
            "post2022": {
              "ann_return_arithmetic": -0.023566517877662913,
              "ann_return_geometric": -0.02337395892507943,
              "ann_volatility": 0.012974441180806552,
              "annualized_capital_charge_drag": 0.017837837837837836,
              "annualized_cost_drag": 0.09618308448218651,
              "annualized_fee_drag": 0.07834524664434868,
              "annualized_turnover_perp_units": 41.23891183929234,
              "annualized_turnover_spot_units": 41.231673630703376,
              "annualized_turnover_units": 82.47058546999571,
              "avg_spot_notional_fraction": 0.8918918918918919,
              "invested_fraction": 0.8918918918918919,
              "max_drawdown": -0.13503606472619722,
              "position_entries": 67,
              "position_exits": 67,
              "rebalance_days": 1288,
              "sessions": 1369,
              "sharpe_backtest_scale": -1.8015387791542938,
              "sharpe_canonical": -1.8163801854160402
            },
            "test_oos": {
              "ann_return_arithmetic": -0.06962360647642289,
              "ann_return_geometric": -0.06734046476145428,
              "ann_volatility": 0.013025559642200786,
              "annualized_capital_charge_drag": 0.016990595611285266,
              "annualized_cost_drag": 0.11325164383428785,
              "annualized_fee_drag": 0.09626104822300258,
              "annualized_turnover_perp_units": 50.66681098167943,
              "annualized_turnover_spot_units": 50.66190044652249,
              "annualized_turnover_units": 101.32871142820193,
              "avg_spot_notional_fraction": 0.8495297805642633,
              "invested_fraction": 0.8495297805642633,
              "max_drawdown": -0.12741509301780973,
              "position_entries": 40,
              "position_exits": 40,
              "rebalance_days": 582,
              "sessions": 638,
              "sharpe_backtest_scale": -5.169871131162891,
              "sharpe_canonical": -5.345152791044251
            },
            "train": {
              "ann_return_arithmetic": 0.056477433498114876,
              "ann_return_geometric": 0.05781176326603532,
              "ann_volatility": 0.023278468943058142,
              "annualized_capital_charge_drag": 0.017223744292237445,
              "annualized_cost_drag": 0.1207619683227522,
              "annualized_fee_drag": 0.10353822403051476,
              "annualized_turnover_perp_units": 54.508433105338234,
              "annualized_turnover_spot_units": 54.48526738064833,
              "annualized_turnover_units": 108.99370048598657,
              "avg_spot_notional_fraction": 0.8611872146118722,
              "invested_fraction": 0.8611872146118722,
              "max_drawdown": -0.1219083084153948,
              "position_entries": 70,
              "position_exits": 69,
              "rebalance_days": 1012,
              "sessions": 1095,
              "sharpe_backtest_scale": 2.4834864959310536,
              "sharpe_canonical": 2.4261661553543443
            },
            "val": {
              "ann_return_arithmetic": 0.01663105055736974,
              "ann_return_geometric": 0.01668952501807408,
              "ann_volatility": 0.012565615641849019,
              "annualized_capital_charge_drag": 0.018577291381668946,
              "annualized_cost_drag": 0.08128603815299276,
              "annualized_fee_drag": 0.06270874677132382,
              "annualized_turnover_perp_units": 33.01045814183276,
              "annualized_turnover_spot_units": 33.001188393367414,
              "annualized_turnover_units": 66.01164653520017,
              "avg_spot_notional_fraction": 0.9288645690834473,
              "invested_fraction": 0.9288645690834473,
              "max_drawdown": -0.04612269891127019,
              "position_entries": 27,
              "position_exits": 27,
              "rebalance_days": 706,
              "sessions": 731,
              "sharpe_backtest_scale": 1.3281899983070176,
              "sharpe_canonical": 1.3235364689956803
            }
          },
          "ETHUSDT": {
            "full": {
              "ann_return_arithmetic": 0.0273511456916221,
              "ann_return_geometric": 0.02748275010914525,
              "ann_volatility": 0.021832911866479985,
              "annualized_capital_charge_drag": 0.01760551948051948,
              "annualized_cost_drag": 0.11227871183329771,
              "annualized_fee_drag": 0.09467319235277824,
              "annualized_turnover_perp_units": 49.84235545280386,
              "annualized_turnover_spot_units": 49.81961961317965,
              "annualized_turnover_units": 99.66197506598347,
              "avg_spot_notional_fraction": 0.880275974025974,
              "invested_fraction": 0.880275974025974,
              "max_drawdown": -0.26866771744760154,
              "position_entries": 138,
              "position_exits": 137,
              "rebalance_days": 2306,
              "sessions": 2464,
              "sharpe_backtest_scale": 1.258776212592121,
              "sharpe_canonical": 1.252748412987195
            },
            "post2022": {
              "ann_return_arithmetic": -0.030682957397706063,
              "ann_return_geometric": -0.03030566868152962,
              "ann_volatility": 0.013425013658518309,
              "annualized_capital_charge_drag": 0.017735573411249088,
              "annualized_cost_drag": 0.10541824099823471,
              "annualized_fee_drag": 0.08768266758698563,
              "annualized_turnover_perp_units": 46.153790096700355,
              "annualized_turnover_spot_units": 46.14584543274615,
              "annualized_turnover_units": 92.2996355294465,
              "avg_spot_notional_fraction": 0.8867786705624543,
              "invested_fraction": 0.8867786705624543,
              "max_drawdown": -0.18051319115388575,
              "position_entries": 73,
              "position_exits": 73,
              "rebalance_days": 1287,
              "sessions": 1369,
              "sharpe_backtest_scale": -2.257403191712983,
              "sharpe_canonical": -2.2855066056664612
            },
            "test_oos": {
              "ann_return_arithmetic": -0.11004531406984262,
              "ann_return_geometric": -0.10431586637509993,
              "ann_volatility": 0.014530583999990257,
              "annualized_capital_charge_drag": 0.016206896551724137,
              "annualized_cost_drag": 0.149488518744542,
              "annualized_fee_drag": 0.13328162219281786,
              "annualized_turnover_perp_units": 70.1513745766121,
              "annualized_turnover_spot_units": 70.1463833243245,
              "annualized_turnover_units": 140.2977579009366,
              "avg_spot_notional_fraction": 0.8103448275862069,
              "invested_fraction": 0.8103448275862069,
              "max_drawdown": -0.18051319115388453,
              "position_entries": 55,
              "position_exits": 55,
              "rebalance_days": 572,
              "sessions": 638,
              "sharpe_backtest_scale": -7.179055320499842,
              "sharpe_canonical": -7.5733579648220894
            },
            "train": {
              "ann_return_arithmetic": 0.09990702434850814,
              "ann_return_geometric": 0.10459960206961005,
              "ann_volatility": 0.02866741582363882,
              "annualized_capital_charge_drag": 0.017442922374429223,
              "annualized_cost_drag": 0.12085586669466877,
              "annualized_fee_drag": 0.10341294432023955,
              "annualized_turnover_perp_units": 54.45390428614238,
              "annualized_turnover_spot_units": 54.41267609994991,
              "annualized_turnover_units": 108.8665803860923,
              "avg_spot_notional_fraction": 0.8721461187214612,
              "invested_fraction": 0.8721461187214612,
              "max_drawdown": -0.1786749341524867,
              "position_entries": 65,
              "position_exits": 64,
              "rebalance_days": 1019,
              "sessions": 1095,
              "sharpe_backtest_scale": 3.6487279744049492,
              "sharpe_canonical": 3.4850376805197056
            },
            "val": {
              "ann_return_arithmetic": 0.03858268358290013,
              "ann_return_geometric": 0.03926951239979837,
              "ann_volatility": 0.011192178078344429,
              "annualized_capital_charge_drag": 0.019069767441860466,
              "annualized_cost_drag": 0.06695471541390634,
              "annualized_fee_drag": 0.04788494797204587,
              "annualized_turnover_perp_units": 25.209249880306807,
              "annualized_turnover_spot_units": 25.19872754652592,
              "annualized_turnover_units": 50.40797742683274,
              "avg_spot_notional_fraction": 0.9534883720930233,
              "invested_fraction": 0.9534883720930233,
              "max_drawdown": -0.03211888443830502,
              "position_entries": 18,
              "position_exits": 18,
              "rebalance_days": 715,
              "sessions": 731,
              "sharpe_backtest_scale": 3.5086568606141406,
              "sharpe_canonical": 3.4472900013584633
            }
          }
        }
      },
      "funding_positive_sameday": {
        "realistic_rf": {
          "BTCUSDT": {
            "full": {
              "ann_return_arithmetic": 0.019472839869940046,
              "ann_return_geometric": 0.019503597087483282,
              "ann_volatility": 0.017696857252172443,
              "annualized_capital_charge_drag": 0.01757305194805195,
              "annualized_cost_drag": 0.10691278608841803,
              "annualized_fee_drag": 0.08933973414036608,
              "annualized_turnover_perp_units": 47.02882576435699,
              "annualized_turnover_spot_units": 47.01629675443016,
              "annualized_turnover_units": 94.04512251878714,
              "avg_spot_notional_fraction": 0.8786525974025974,
              "invested_fraction": 0.8786525974025974,
              "max_drawdown": -0.18288596645345234,
              "position_entries": 137,
              "position_exits": 136,
              "rebalance_days": 2301,
              "sessions": 2464,
              "sharpe_backtest_scale": 1.1020938243195155,
              "sharpe_canonical": 1.1003558198193404
            },
            "post2022": {
              "ann_return_arithmetic": -0.02034528917572779,
              "ann_return_geometric": -0.020220803465188397,
              "ann_volatility": 0.012819742656840572,
              "annualized_capital_charge_drag": 0.017837837837837836,
              "annualized_cost_drag": 0.09611154417091707,
              "annualized_fee_drag": 0.07827370633307923,
              "annualized_turnover_perp_units": 41.20098931797935,
              "annualized_turnover_spot_units": 41.194178175411416,
              "annualized_turnover_units": 82.39516749339077,
              "avg_spot_notional_fraction": 0.8918918918918919,
              "invested_fraction": 0.8918918918918919,
              "max_drawdown": -0.12809631447319458,
              "position_entries": 67,
              "position_exits": 67,
              "rebalance_days": 1288,
              "sessions": 1369,
              "sharpe_backtest_scale": -1.5773174241059078,
              "sharpe_canonical": -1.587027892862702
            },
            "test_oos": {
              "ann_return_arithmetic": -0.0660127854775205,
              "ann_return_geometric": -0.06396444900471099,
              "ann_volatility": 0.012891009976227195,
              "annualized_capital_charge_drag": 0.016990595611285266,
              "annualized_cost_drag": 0.11307011665686033,
              "annualized_fee_drag": 0.09607952104557506,
              "annualized_turnover_perp_units": 50.57100214930303,
              "annualized_turnover_spot_units": 50.56651628421912,
              "annualized_turnover_units": 101.13751843352213,
              "avg_spot_notional_fraction": 0.8495297805642633,
              "invested_fraction": 0.8495297805642633,
              "max_drawdown": -0.12200375145078046,
              "position_entries": 40,
              "position_exits": 40,
              "rebalance_days": 582,
              "sessions": 638,
              "sharpe_backtest_scale": -4.961942401927411,
              "sharpe_canonical": -5.120838910159654
            },
            "train": {
              "ann_return_arithmetic": 0.06925459207406726,
              "ann_return_geometric": 0.0714413149291604,
              "ann_volatility": 0.022075839519812315,
              "annualized_capital_charge_drag": 0.01724200913242009,
              "annualized_cost_drag": 0.12041680452226168,
              "annualized_fee_drag": 0.10317479538984159,
              "annualized_turnover_perp_units": 54.31495187859533,
              "annualized_turnover_spot_units": 54.29527422902072,
              "annualized_turnover_units": 108.61022610761606,
              "avg_spot_notional_fraction": 0.8621004566210045,
              "invested_fraction": 0.8621004566210045,
              "max_drawdown": -0.11156770328011723,
              "position_entries": 70,
              "position_exits": 69,
              "rebalance_days": 1013,
              "sessions": 1095,
              "sharpe_backtest_scale": 3.236176584135985,
              "sharpe_canonical": 3.1371215582498513
            },
            "val": {
              "ann_return_arithmetic": 0.019512252056206204,
              "ann_return_geometric": 0.019625071020336282,
              "ann_volatility": 0.012394354004128716,
              "annualized_capital_charge_drag": 0.018577291381668946,
              "annualized_cost_drag": 0.08131049185076415,
              "annualized_fee_drag": 0.06273320046909521,
              "annualized_turnover_perp_units": 33.02305746246018,
              "annualized_turnover_spot_units": 33.01421687114423,
              "annualized_turnover_units": 66.03727433360439,
              "avg_spot_notional_fraction": 0.9288645690834473,
              "invested_fraction": 0.9288645690834473,
              "max_drawdown": -0.04262343283508918,
              "position_entries": 27,
              "position_exits": 27,
              "rebalance_days": 706,
              "sessions": 731,
              "sharpe_backtest_scale": 1.5833879695383013,
              "sharpe_canonical": 1.5742855214322928
            }
          },
          "ETHUSDT": {
            "full": {
              "ann_return_arithmetic": 0.035529192475817324,
              "ann_return_geometric": 0.03594661829820822,
              "ann_volatility": 0.020600558265959492,
              "annualized_capital_charge_drag": 0.017613636363636366,
              "annualized_cost_drag": 0.11216196238211062,
              "annualized_fee_drag": 0.09454832601847427,
              "annualized_turnover_perp_units": 49.77500189894696,
              "annualized_turnover_spot_units": 49.75485390767618,
              "annualized_turnover_units": 99.52985580662315,
              "avg_spot_notional_fraction": 0.8806818181818182,
              "invested_fraction": 0.8806818181818182,
              "max_drawdown": -0.2446467695491107,
              "position_entries": 138,
              "position_exits": 137,
              "rebalance_days": 2307,
              "sessions": 2464,
              "sharpe_backtest_scale": 1.7449341825656572,
              "sharpe_canonical": 1.7246713422580402
            },
            "post2022": {
              "ann_return_arithmetic": -0.02729966063531996,
              "ann_return_geometric": -0.027016995234139585,
              "ann_volatility": 0.013264040789120683,
              "annualized_capital_charge_drag": 0.017735573411249088,
              "annualized_cost_drag": 0.10533864024721692,
              "annualized_fee_drag": 0.08760306683596783,
              "annualized_turnover_perp_units": 46.1115889995682,
              "annualized_turnover_spot_units": 46.10412878022507,
              "annualized_turnover_units": 92.21571777979327,
              "avg_spot_notional_fraction": 0.8867786705624543,
              "invested_fraction": 0.8867786705624543,
              "max_drawdown": -0.17316809260814048,
              "position_entries": 73,
              "position_exits": 73,
              "rebalance_days": 1287,
              "sessions": 1369,
              "sharpe_backtest_scale": -2.0368600838666926,
              "sharpe_canonical": -2.058170739169579
            },
            "test_oos": {
              "ann_return_arithmetic": -0.10493463836276845,
              "ann_return_geometric": -0.09972271653007736,
              "ann_volatility": 0.014336275880560663,
              "annualized_capital_charge_drag": 0.016206896551724137,
              "annualized_cost_drag": 0.14934657291125977,
              "annualized_fee_drag": 0.13313967635953564,
              "annualized_turnover_perp_units": 70.07625909337838,
              "annualized_turnover_spot_units": 70.07191249514231,
              "annualized_turnover_units": 140.1481715885207,
              "avg_spot_notional_fraction": 0.8103448275862069,
              "invested_fraction": 0.8103448275862069,
              "max_drawdown": -0.17316809260814103,
              "position_entries": 55,
              "position_exits": 55,
              "rebalance_days": 572,
              "sessions": 638,
              "sharpe_backtest_scale": -6.955970808660066,
              "sharpe_canonical": -7.319518627920312
            },
            "train": {
              "ann_return_arithmetic": 0.11407960335175059,
              "ann_return_geometric": 0.1204274690264937,
              "ann_volatility": 0.026551670107501982,
              "annualized_capital_charge_drag": 0.017461187214611873,
              "annualized_cost_drag": 0.12069267288683168,
              "annualized_fee_drag": 0.1032314856722198,
              "annualized_turnover_perp_units": 54.355104418809546,
              "annualized_turnover_spot_units": 54.31909381587761,
              "annualized_turnover_units": 108.67419823468715,
              "avg_spot_notional_fraction": 0.8730593607305936,
              "invested_fraction": 0.8730593607305936,
              "max_drawdown": -0.1623923275518082,
              "position_entries": 65,
              "position_exits": 64,
              "rebalance_days": 1020,
              "sessions": 1095,
              "sharpe_backtest_scale": 4.535589231822664,
              "sharpe_canonical": 4.29651328484675
            },
            "val": {
              "ann_return_arithmetic": 0.04045836370135875,
              "ann_return_geometric": 0.04122147764544648,
              "ann_volatility": 0.011105154375709253,
              "annualized_capital_charge_drag": 0.019069767441860466,
              "annualized_cost_drag": 0.06692952801786076,
              "annualized_fee_drag": 0.04785976057600028,
              "annualized_turnover_perp_units": 25.19577570291855,
              "annualized_turnover_spot_units": 25.185597986631084,
              "annualized_turnover_units": 50.381373689549626,
              "avg_spot_notional_fraction": 0.9534883720930233,
              "invested_fraction": 0.9534883720930233,
              "max_drawdown": -0.03006632704175982,
              "position_entries": 18,
              "position_exits": 18,
              "rebalance_days": 715,
              "sessions": 731,
              "sharpe_backtest_scale": 3.7119229729585625,
              "sharpe_canonical": 3.643205878331142
            }
          }
        }
      }
    },
    "portfolio": {
      "always_on": {
        "flat_3bp": {
          "samples": {
            "full": {
              "ann_return_geometric": 0.12769409977315704,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.005540178878605894,
              "max_drawdown": -0.017213345266197444,
              "sharpe_canonical": 8.135176202397444
            },
            "post2022": {
              "ann_return_geometric": 0.07069742761785203,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.004332166182614438,
              "max_drawdown": -0.00653462754284051,
              "sharpe_canonical": 12.501155455995837
            },
            "test_oos": {
              "ann_return_geometric": 0.03512280994305561,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.004470130571070204,
              "max_drawdown": -0.006534627542839289,
              "sharpe_canonical": 11.143762440982155
            },
            "train": {
              "ann_return_geometric": 0.20323965609904593,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.007050470550580602,
              "max_drawdown": -0.017213345266197444,
              "sharpe_canonical": 8.892251140300534
            },
            "val": {
              "ann_return_geometric": 0.10274388375148735,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.00421175403509764,
              "max_drawdown": -0.0010388388997484288,
              "sharpe_canonical": 15.009375936977383
            }
          }
        },
        "flat_3bp_capital_rf": {
          "samples": {
            "full": {
              "ann_return_geometric": 0.10537092614398569,
              "annualized_capital_charge_drag": 0.02,
              "annualized_fee_drag": 0.005540178878605894,
              "max_drawdown": -0.018353683481735383,
              "sharpe_canonical": 6.782739264241195
            },
            "post2022": {
              "ann_return_geometric": 0.04949955026448816,
              "annualized_capital_charge_drag": 0.02,
              "annualized_fee_drag": 0.004332166182614438,
              "max_drawdown": -0.011855603057085662,
              "sharpe_canonical": 8.842185163181565
            },
            "test_oos": {
              "ann_return_geometric": 0.014627367961192572,
              "annualized_capital_charge_drag": 0.02,
              "annualized_fee_drag": 0.004470130571070204,
              "max_drawdown": -0.011855603057084996,
              "sharpe_canonical": 4.6885688243714
            },
            "train": {
              "ann_return_geometric": 0.17942520881940238,
              "annualized_capital_charge_drag": 0.02,
              "annualized_fee_drag": 0.007050470550580602,
              "max_drawdown": -0.018353683481735383,
              "sharpe_canonical": 7.932386449975524
            },
            "val": {
              "ann_return_geometric": 0.08091329042197182,
              "annualized_capital_charge_drag": 0.02,
              "annualized_fee_drag": 0.00421175403509764,
              "max_drawdown": -0.0022035071439726606,
              "sharpe_canonical": 11.941097642452457
            }
          }
        },
        "realistic_no_capital_charge": {
          "samples": {
            "full": {
              "ann_return_geometric": 0.11424754929139191,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.017539256948116817,
              "max_drawdown": -0.01864871064496043,
              "sharpe_canonical": 7.315299579271961
            },
            "post2022": {
              "ann_return_geometric": 0.06069786043334191,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.01371668329958575,
              "max_drawdown": -0.009502266490638789,
              "sharpe_canonical": 10.67573720148079
            },
            "test_oos": {
              "ann_return_geometric": 0.025147436593969452,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.014154251423893326,
              "max_drawdown": -0.009502266490637457,
              "sharpe_canonical": 7.778252149337728
            },
            "train": {
              "ann_return_geometric": 0.18501559164056447,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.022318346742490353,
              "max_drawdown": -0.01864871064496043,
              "sharpe_canonical": 8.136830581493964
            },
            "val": {
              "ann_return_geometric": 0.0927315266187494,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.013334783896975313,
              "max_drawdown": -0.0012671923759368653,
              "sharpe_canonical": 13.525931264329946
            }
          }
        },
        "realistic_rf": {
          "samples": {
            "samples": {
              "full": {
                "ann_return_arithmetic": 0.08830488543340807,
                "ann_return_geometric": 0.09218983799950076,
                "ann_volatility": 0.01480525633431227,
                "annualized_capital_charge_drag": 0.02,
                "annualized_cost_drag": 0.037539256948116814,
                "annualized_fee_drag": 0.017539256948116817,
                "annualized_turnover_perp_units": 9.242917132613526,
                "annualized_turnover_spot_units": 9.224345796072793,
                "annualized_turnover_units": 18.467262928686317,
                "avg_spot_notional_fraction": 1.0,
                "invested_fraction": 1.0,
                "max_drawdown": -0.021235065443034107,
                "position_entries": 2,
                "position_exits": 0,
                "rebalance_days": 2464,
                "sessions": 2464,
                "sharpe_backtest_scale": 6.226831600736559,
                "sharpe_canonical": 5.964428000395712
              },
              "post2022": {
                "ann_return_arithmetic": 0.03894703222928297,
                "ann_return_geometric": 0.039697421958073464,
                "ann_volatility": 0.005521588918571981,
                "annualized_capital_charge_drag": 0.02,
                "annualized_cost_drag": 0.03371668329958575,
                "annualized_fee_drag": 0.01371668329958575,
                "annualized_turnover_perp_units": 7.223962861743997,
                "annualized_turnover_spot_units": 7.216591080304129,
                "annualized_turnover_units": 14.440553942048126,
                "avg_spot_notional_fraction": 1.0,
                "invested_fraction": 1.0,
                "max_drawdown": -0.0151306136188738,
                "position_entries": 0,
                "position_exits": 0,
                "rebalance_days": 1369,
                "sessions": 1369,
                "sharpe_backtest_scale": 7.18949247100782,
                "sharpe_canonical": 7.053591421535168
              },
              "test_oos": {
                "ann_return_arithmetic": 0.004842380141063697,
                "ann_return_geometric": 0.0048489739185648695,
                "ann_volatility": 0.0031938255104238143,
                "annualized_capital_charge_drag": 0.02,
                "annualized_cost_drag": 0.03415425142389333,
                "annualized_fee_drag": 0.014154251423893326,
                "annualized_turnover_perp_units": 7.45254172077498,
                "annualized_turnover_spot_units": 7.447893516125698,
                "annualized_turnover_units": 14.900435236900682,
                "avg_spot_notional_fraction": 1.0,
                "invested_fraction": 1.0,
                "max_drawdown": -0.015130613618873912,
                "position_entries": 0,
                "position_exits": 0,
                "rebalance_days": 638,
                "sessions": 638,
                "sharpe_backtest_scale": 1.5182338242145923,
                "sharpe_canonical": 1.5161692851595774
              },
              "train": {
                "ann_return_arithmetic": 0.1500134708548211,
                "ann_return_geometric": 0.16156086292679173,
                "ann_volatility": 0.02089431126186798,
                "annualized_capital_charge_drag": 0.02,
                "annualized_cost_drag": 0.042318346742490354,
                "annualized_fee_drag": 0.022318346742490353,
                "annualized_turnover_perp_units": 11.767070919664105,
                "annualized_turnover_spot_units": 11.734497582271237,
                "annualized_turnover_units": 23.501568501935342,
                "avg_spot_notional_fraction": 1.0,
                "invested_fraction": 1.0,
                "max_drawdown": -0.021235065443034107,
                "position_entries": 2,
                "position_exits": 0,
                "rebalance_days": 1095,
                "sessions": 1095,
                "sharpe_backtest_scale": 7.732289468743558,
                "sharpe_canonical": 7.179632244140777
              },
              "val": {
                "ann_return_arithmetic": 0.068712788771395,
                "ann_return_geometric": 0.07109860882257468,
                "ann_volatility": 0.006558719472820691,
                "annualized_capital_charge_drag": 0.02,
                "annualized_cost_drag": 0.03333478389697531,
                "annualized_fee_drag": 0.013334783896975313,
                "annualized_turnover_perp_units": 7.024464486830499,
                "annualized_turnover_spot_units": 7.014715630161637,
                "annualized_turnover_units": 14.039180116992133,
                "avg_spot_notional_fraction": 1.0,
                "invested_fraction": 1.0,
                "max_drawdown": -0.003669875554275226,
                "position_entries": 0,
                "position_exits": 0,
                "rebalance_days": 731,
                "sessions": 731,
                "sharpe_backtest_scale": 10.840318619695058,
                "sharpe_canonical": 10.476555531325976
              }
            }
          }
        },
        "realistic_usdt_5pct": {
          "samples": {
            "full": {
              "ann_return_geometric": 0.059917115741551674,
              "annualized_capital_charge_drag": 0.05000000000000001,
              "annualized_fee_drag": 0.017539256948116817,
              "max_drawdown": -0.04601755693071141,
              "sharpe_canonical": 3.9381206320813384
            },
            "post2022": {
              "ann_return_geometric": 0.008971702614989363,
              "annualized_capital_charge_drag": 0.05000000000000001,
              "annualized_fee_drag": 0.01371668329958575,
              "max_drawdown": -0.045436310464386453,
              "sharpe_canonical": 1.620372751616737
            },
            "test_oos": {
              "ann_return_geometric": -0.02484961635243288,
              "annualized_capital_charge_drag": 0.05000000000000001,
              "annualized_fee_drag": 0.014154251423893326,
              "max_drawdown": -0.04543631046438934,
              "sharpe_canonical": -7.87695501110765
            },
            "train": {
              "ann_return_geometric": 0.12724401529566842,
              "annualized_capital_charge_drag": 0.05000000000000001,
              "annualized_fee_drag": 0.022318346742490353,
              "max_drawdown": -0.04601755693071141,
              "sharpe_canonical": 5.743834738110996
            },
            "val": {
              "ann_return_geometric": 0.03944744545299761,
              "annualized_capital_charge_drag": 0.05000000000000001,
              "annualized_fee_drag": 0.013334783896975313,
              "max_drawdown": -0.007808681066037493,
              "sharpe_canonical": 5.902491931820023
            }
          }
        },
        "venue_maker_slippage": {
          "samples": {
            "full": {
              "ann_return_geometric": 0.11734071459324547,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.01476638180833276,
              "max_drawdown": -0.01831481849251093,
              "sharpe_canonical": 7.506699097866459
            },
            "post2022": {
              "ann_return_geometric": 0.06299880374323208,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.011549494441062555,
              "max_drawdown": -0.008818021889281491,
              "sharpe_canonical": 11.101395549473322
            },
            "test_oos": {
              "ann_return_geometric": 0.0274419176622287,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.011918488907660832,
              "max_drawdown": -0.008818021889282046,
              "sharpe_canonical": 8.555531099002714
            },
            "train": {
              "ann_return_geometric": 0.18920473125495962,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.018788225466591126,
              "max_drawdown": -0.01831481849251093,
              "sharpe_canonical": 8.31318143390346
            },
            "val": {
              "ann_return_geometric": 0.09503623121838323,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.011227444550926162,
              "max_drawdown": -0.0011741225244538134,
              "sharpe_canonical": 13.87304022276938
            }
          }
        },
        "venue_taker": {
          "samples": {
            "full": {
              "ann_return_geometric": 0.11836950636866139,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.013845804362379558,
              "max_drawdown": -0.018206217220493315,
              "sharpe_canonical": 7.569913808297439
            },
            "post2022": {
              "ann_return_geometric": 0.06376531927293794,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.010828572511176127,
              "max_drawdown": -0.00859000723598402,
              "sharpe_canonical": 11.242523944056046
            },
            "test_oos": {
              "ann_return_geometric": 0.02820692345152298,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.01117416437651319,
              "max_drawdown": -0.008590007235984465,
              "sharpe_canonical": 8.815091066399285
            },
            "train": {
              "ann_return_geometric": 0.19059661206450929,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.01761803304210329,
              "max_drawdown": -0.018206217220493315,
              "sharpe_canonical": 8.37131251689669
            },
            "val": {
              "ann_return_geometric": 0.09580340350409156,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.010526947873576886,
              "max_drawdown": -0.0011607142546706806,
              "sharpe_canonical": 13.987763867713884
            }
          }
        },
        "venue_taker_slippage": {
          "samples": {
            "full": {
              "ann_return_geometric": 0.11424754929139191,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.017539256948116817,
              "max_drawdown": -0.01864871064496043,
              "sharpe_canonical": 7.315299579271961
            },
            "post2022": {
              "ann_return_geometric": 0.06069786043334191,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.01371668329958575,
              "max_drawdown": -0.009502266490638789,
              "sharpe_canonical": 10.67573720148079
            },
            "test_oos": {
              "ann_return_geometric": 0.025147436593969452,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.014154251423893326,
              "max_drawdown": -0.009502266490637457,
              "sharpe_canonical": 7.778252149337728
            },
            "train": {
              "ann_return_geometric": 0.18501559164056447,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.022318346742490353,
              "max_drawdown": -0.01864871064496043,
              "sharpe_canonical": 8.136830581493964
            },
            "val": {
              "ann_return_geometric": 0.0927315266187494,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.013334783896975313,
              "max_drawdown": -0.0012671923759368653,
              "sharpe_canonical": 13.525931264329946
            }
          }
        }
      },
      "funding_positive_lagged": {
        "flat_3bp": {
          "samples": {
            "full": {
              "ann_return_geometric": 0.10534031886718953,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.029087912343942538,
              "max_drawdown": -0.02659446105343266,
              "sharpe_canonical": 6.596559909105592
            },
            "post2022": {
              "ann_return_geometric": 0.04857905751574387,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.026215533149916335,
              "max_drawdown": -0.02659446105343144,
              "sharpe_canonical": 7.260671172958309
            },
            "test_oos": {
              "ann_return_geometric": 0.005294594808492592,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.03624397039937078,
              "max_drawdown": -0.026594461053432328,
              "sharpe_canonical": 1.128147113688549
            },
            "train": {
              "ann_return_geometric": 0.18064621510461643,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.032679042130811825,
              "max_drawdown": -0.026049549193389976,
              "sharpe_canonical": 7.881277789367736
            },
            "val": {
              "ann_return_geometric": 0.08787709972546165,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.01746294359430493,
              "max_drawdown": -0.00800954354080008,
              "sharpe_canonical": 11.585742447012395
            }
          }
        },
        "flat_3bp_capital_rf": {
          "samples": {
            "full": {
              "ann_return_geometric": 0.08607853222483319,
              "annualized_capital_charge_drag": 0.017585227272727273,
              "annualized_fee_drag": 0.029087912343942538,
              "max_drawdown": -0.038833431917071004,
              "sharpe_canonical": 5.465818644295653
            },
            "post2022": {
              "ann_return_geometric": 0.030095845752937223,
              "annualized_capital_charge_drag": 0.017786705624543462,
              "annualized_fee_drag": 0.026215533149916335,
              "max_drawdown": -0.03207825281432286,
              "sharpe_canonical": 4.617185197779982
            },
            "test_oos": {
              "ann_return_geometric": -0.011253772566930054,
              "annualized_capital_charge_drag": 0.016598746081504703,
              "annualized_fee_drag": 0.03624397039937078,
              "max_drawdown": -0.032078252814322306,
              "sharpe_canonical": -2.4889524728309937
            },
            "train": {
              "ann_return_geometric": 0.1603686019306918,
              "annualized_capital_charge_drag": 0.017333333333333333,
              "annualized_fee_drag": 0.032679042130811825,
              "max_drawdown": -0.038833431917071004,
              "sharpe_canonical": 7.0864243030437555
            },
            "val": {
              "ann_return_geometric": 0.06759561024557414,
              "annualized_capital_charge_drag": 0.018823529411764708,
              "annualized_fee_drag": 0.01746294359430493,
              "max_drawdown": -0.010187569224678006,
              "sharpe_canonical": 9.087059569378575
            }
          }
        },
        "realistic_no_capital_charge": {
          "samples": {
            "full": {
              "ann_return_geometric": 0.03779264686226158,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.09210709089423148,
              "max_drawdown": -0.1718916383596557,
              "sharpe_canonical": 2.0483459546916043
            },
            "post2022": {
              "ann_return_geometric": -0.009356128615761405,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.08301395711566717,
              "max_drawdown": -0.13147692392172883,
              "sharpe_canonical": -0.8383352130884232
            },
            "test_oos": {
              "ann_return_geometric": -0.07068133226379414,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.11477133520791022,
              "max_drawdown": -0.13147692392172816,
              "sharpe_canonical": -6.655047927057315
            },
            "train": {
              "ann_return_geometric": 0.09990832629060376,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.10347558417537717,
              "max_drawdown": -0.1382524033434831,
              "sharpe_canonical": 3.9900164525478914
            },
            "val": {
              "ann_return_geometric": 0.04746530518682479,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.055296847371684846,
              "max_drawdown": -0.03013053534637944,
              "sharpe_canonical": 4.456896818689791
            }
          }
        },
        "realistic_rf": {
          "samples": {
            "samples": {
              "full": {
                "ann_return_arithmetic": 0.01967805391438151,
                "ann_return_geometric": 0.01970566667269469,
                "ann_volatility": 0.018087521756042613,
                "annualized_capital_charge_drag": 0.017585227272727273,
                "annualized_cost_drag": 0.10969231816695876,
                "annualized_fee_drag": 0.09210709089423148,
                "annualized_turnover_perp_units": 48.48911696307737,
                "annualized_turnover_spot_units": 48.470590850064426,
                "annualized_turnover_units": 96.9597078131418,
                "avg_spot_notional_fraction": 0.8792613636363636,
                "invested_fraction": 0.9460227272727273,
                "max_drawdown": -0.23260191941836283,
                "position_entries": 275,
                "position_exits": 273,
                "rebalance_days": 2413,
                "sessions": 2464,
                "sharpe_backtest_scale": 1.0894619472184734,
                "sharpe_canonical": 1.0879353280007824
              },
              "post2022": {
                "ann_return_arithmetic": -0.027124737637684488,
                "ann_return_geometric": -0.02682008320756213,
                "ann_volatility": 0.011006252489510952,
                "annualized_capital_charge_drag": 0.017786705624543462,
                "annualized_cost_drag": 0.10080066274021063,
                "annualized_fee_drag": 0.08301395711566717,
                "annualized_turnover_perp_units": 43.696350967996345,
                "annualized_turnover_spot_units": 43.68875953172476,
                "annualized_turnover_units": 87.38511049972112,
                "avg_spot_notional_fraction": 0.8893352812271731,
                "invested_fraction": 0.9503287070854638,
                "max_drawdown": -0.15079485126556458,
                "position_entries": 140,
                "position_exits": 140,
                "rebalance_days": 1341,
                "sessions": 1369,
                "sharpe_backtest_scale": -2.43680428312197,
                "sharpe_canonical": -2.4644844067982796
              },
              "test_oos": {
                "ann_return_arithmetic": -0.08983446027313276,
                "ann_return_geometric": -0.08598148551658547,
                "ann_volatility": 0.010859414035587262,
                "annualized_capital_charge_drag": 0.016598746081504703,
                "annualized_cost_drag": 0.1313700812894149,
                "annualized_fee_drag": 0.11477133520791022,
                "annualized_turnover_perp_units": 60.40909277914575,
                "annualized_turnover_spot_units": 60.404141885423506,
                "annualized_turnover_units": 120.81323466456928,
                "avg_spot_notional_fraction": 0.8299373040752351,
                "invested_fraction": 0.9122257053291536,
                "max_drawdown": -0.15075570536760852,
                "position_entries": 95,
                "position_exits": 95,
                "rebalance_days": 613,
                "sessions": 638,
                "sharpe_backtest_scale": -7.9176910683041015,
                "sharpe_canonical": -8.2724961014229
              },
              "train": {
                "ann_return_arithmetic": 0.07819222892331151,
                "ann_return_geometric": 0.08101465546364373,
                "ann_volatility": 0.023836497661991928,
                "annualized_capital_charge_drag": 0.017333333333333333,
                "annualized_cost_drag": 0.1208089175087105,
                "annualized_fee_drag": 0.10347558417537717,
                "annualized_turnover_perp_units": 54.4811686957403,
                "annualized_turnover_spot_units": 54.448971740299115,
                "annualized_turnover_units": 108.93014043603944,
                "avg_spot_notional_fraction": 0.8666666666666667,
                "invested_fraction": 0.9406392694063926,
                "max_drawdown": -0.14992899786170033,
                "position_entries": 135,
                "position_exits": 133,
                "rebalance_days": 1072,
                "sessions": 1095,
                "sharpe_backtest_scale": 3.3987650624036196,
                "sharpe_canonical": 3.2803572920862267
              },
              "val": {
                "ann_return_arithmetic": 0.02760686707013493,
                "ann_return_geometric": 0.02793573700907359,
                "ann_volatility": 0.010318469628023148,
                "annualized_capital_charge_drag": 0.018823529411764708,
                "annualized_cost_drag": 0.07412037678344956,
                "annualized_fee_drag": 0.055296847371684846,
                "annualized_turnover_perp_units": 29.109854011069775,
                "annualized_turnover_spot_units": 29.09995796994666,
                "annualized_turnover_units": 58.20981198101644,
                "avg_spot_notional_fraction": 0.9411764705882353,
                "invested_fraction": 0.9835841313269493,
                "max_drawdown": -0.03895184624452375,
                "position_entries": 45,
                "position_exits": 45,
                "rebalance_days": 728,
                "sessions": 731,
                "sharpe_backtest_scale": 2.7073527389376664,
                "sharpe_canonical": 2.6754807704390133
              }
            }
          }
        },
        "realistic_usdt_5pct": {
          "samples": {
            "full": {
              "ann_return_geometric": -0.00683720173412572,
              "annualized_capital_charge_drag": 0.043963068181818186,
              "annualized_fee_drag": 0.09210709089423148,
              "max_drawdown": -0.3195219106202398,
              "sharpe_canonical": -0.37349323773311277
            },
            "post2022": {
              "ann_return_geometric": -0.05244213044917867,
              "annualized_capital_charge_drag": 0.04446676406135866,
              "annualized_fee_drag": 0.08301395711566717,
              "max_drawdown": -0.1960149053981839,
              "sharpe_canonical": -4.973943395018612
            },
            "test_oos": {
              "ann_return_geometric": -0.10846214837399304,
              "annualized_capital_charge_drag": 0.04149686520376176,
              "annualized_fee_drag": 0.11477133520791022,
              "max_drawdown": -0.1838473195891931,
              "sharpe_canonical": -10.765584797126213
            },
            "train": {
              "ann_return_geometric": 0.05327913270026707,
              "annualized_capital_charge_drag": 0.04333333333333334,
              "annualized_fee_drag": 0.10347558417537717,
              "max_drawdown": -0.16725551372255865,
              "sharpe_canonical": 2.2035535041671515
            },
            "val": {
              "ann_return_geometric": -0.0006799035751945404,
              "annualized_capital_charge_drag": 0.047058823529411764,
              "annualized_fee_drag": 0.055296847371684846,
              "max_drawdown": -0.05496412563341524,
              "sharpe_canonical": -0.06176312398801381
            }
          }
        },
        "venue_maker_slippage": {
          "samples": {
            "full": {
              "ann_return_geometric": 0.053013179008492006,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.07756035580530826,
              "max_drawdown": -0.11684682162951487,
              "sharpe_canonical": 2.984267058739648
            },
            "post2022": {
              "ann_return_geometric": 0.003728177734629634,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.06990505182526827,
              "max_drawdown": -0.1048861223446893,
              "sharpe_canonical": 0.3784834945547191
            },
            "test_oos": {
              "ann_return_geometric": -0.05366834382480157,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.0966486073741665,
              "max_drawdown": -0.10488612234468986,
              "sharpe_canonical": -5.804827180647245
            },
            "train": {
              "ann_return_geometric": 0.1180485751103495,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.08713123356665507,
              "max_drawdown": -0.11338907353747985,
              "sharpe_canonical": 4.829123786293636
            },
            "val": {
              "ann_return_geometric": 0.056660378914673126,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.046563891168363916,
              "max_drawdown": -0.02497675264091892,
              "sharpe_canonical": 5.757112786789561
            }
          }
        },
        "venue_taker": {
          "samples": {
            "full": {
              "ann_return_geometric": 0.05813161682901424,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.07271514933160311,
              "max_drawdown": -0.10544542724560146,
              "sharpe_canonical": 3.3130521291981143
            },
            "post2022": {
              "ann_return_geometric": 0.008125861834893833,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.06553693501572293,
              "max_drawdown": -0.09584546476538214,
              "sharpe_canonical": 0.8494766335946426
            },
            "test_oos": {
              "ann_return_geometric": -0.04793006203435135,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.09060868827499638,
              "max_drawdown": -0.09584546476538192,
              "sharpe_canonical": -5.455884417406628
            },
            "train": {
              "ann_return_geometric": 0.12415361266382674,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.08168955608816927,
              "max_drawdown": -0.10494547461049208,
              "sharpe_canonical": 5.117846972160528
            },
            "val": {
              "ann_return_geometric": 0.05974088475643047,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.04365488497548156,
              "max_drawdown": -0.02325324148310426,
              "sharpe_canonical": 6.234754879251051
            }
          }
        },
        "venue_taker_slippage": {
          "samples": {
            "full": {
              "ann_return_geometric": 0.03779264686226158,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.09210709089423148,
              "max_drawdown": -0.1718916383596557,
              "sharpe_canonical": 2.0483459546916043
            },
            "post2022": {
              "ann_return_geometric": -0.009356128615761405,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.08301395711566717,
              "max_drawdown": -0.13147692392172883,
              "sharpe_canonical": -0.8383352130884232
            },
            "test_oos": {
              "ann_return_geometric": -0.07068133226379414,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.11477133520791022,
              "max_drawdown": -0.13147692392172816,
              "sharpe_canonical": -6.655047927057315
            },
            "train": {
              "ann_return_geometric": 0.09990832629060376,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.10347558417537717,
              "max_drawdown": -0.1382524033434831,
              "sharpe_canonical": 3.9900164525478914
            },
            "val": {
              "ann_return_geometric": 0.04746530518682479,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.055296847371684846,
              "max_drawdown": -0.03013053534637944,
              "sharpe_canonical": 4.456896818689791
            }
          }
        }
      },
      "funding_positive_sameday": {
        "flat_3bp": {
          "samples": {
            "full": {
              "ann_return_geometric": 0.11392306271560937,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.02903624674881154,
              "max_drawdown": -0.022058153706212558,
              "sharpe_canonical": 7.700593065862711
            },
            "post2022": {
              "ann_return_geometric": 0.051993645521325904,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.0261916327909776,
              "max_drawdown": -0.022058153706213335,
              "sharpe_canonical": 7.936389073269703
            },
            "test_oos": {
              "ann_return_geometric": 0.009577212655276668,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.03619285350330643,
              "max_drawdown": -0.022058153706213113,
              "sharpe_canonical": 2.1306383517096585
            },
            "train": {
              "ann_return_geometric": 0.1965021032917953,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.03259266365134548,
              "max_drawdown": -0.013464298117546125,
              "sharpe_canonical": 9.38319739502189
            },
            "val": {
              "ann_return_geometric": 0.0904675935428374,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.017462797203473105,
              "max_drawdown": -0.006741817363101088,
              "sharpe_canonical": 12.08396792369904
            }
          }
        },
        "flat_3bp_capital_rf": {
          "samples": {
            "full": {
              "ann_return_geometric": 0.0945033020081183,
              "annualized_capital_charge_drag": 0.017593344155844157,
              "annualized_fee_drag": 0.02903624674881154,
              "max_drawdown": -0.026444918159319153,
              "sharpe_canonical": 6.484351173028158
            },
            "post2022": {
              "ann_return_geometric": 0.033450419638031414,
              "annualized_capital_charge_drag": 0.017786705624543462,
              "annualized_fee_drag": 0.0261916327909776,
              "max_drawdown": -0.026444918159318376,
              "sharpe_canonical": 5.246394602598087
            },
            "test_oos": {
              "ann_return_geometric": -0.007041425565567749,
              "annualized_capital_charge_drag": 0.016598746081504703,
              "annualized_fee_drag": 0.03619285350330643,
              "max_drawdown": -0.026444918159318598,
              "sharpe_canonical": -1.635266697100663
            },
            "train": {
              "ann_return_geometric": 0.1759315838538993,
              "annualized_capital_charge_drag": 0.017351598173515982,
              "annualized_fee_drag": 0.03259266365134548,
              "max_drawdown": -0.024352730677198342,
              "sharpe_canonical": 8.518319218702237
            },
            "val": {
              "ann_return_geometric": 0.07013793466818186,
              "annualized_capital_charge_drag": 0.018823529411764708,
              "annualized_fee_drag": 0.017462797203473105,
              "max_drawdown": -0.008998783387997089,
              "sharpe_canonical": 9.554429793565854
            }
          }
        },
        "realistic_no_capital_charge": {
          "samples": {
            "full": {
              "ann_return_geometric": 0.04597022763201575,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.09194403007942017,
              "max_drawdown": -0.14860121932028014,
              "sharpe_canonical": 2.630825368819771
            },
            "post2022": {
              "ann_return_geometric": -0.006077603274039278,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.08293838658452352,
              "max_drawdown": -0.12511798612843217,
              "sharpe_canonical": -0.5494117312351042
            },
            "test_oos": {
              "ann_return_geometric": -0.06661742586470665,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.11460959870255535,
              "max_drawdown": -0.12511798612843228,
              "sharpe_canonical": -6.357325893699512
            },
            "train": {
              "ann_return_geometric": 0.11489236535522407,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.10320314053103072,
              "max_drawdown": -0.12466011890076589,
              "sharpe_canonical": 4.923051749006123
            },
            "val": {
              "ann_return_geometric": 0.049960583271813075,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.055296480522547736,
              "max_drawdown": -0.02885840227569436,
              "sharpe_canonical": 4.739835902663224
            }
          }
        },
        "realistic_rf": {
          "samples": {
            "samples": {
              "full": {
                "ann_return_arithmetic": 0.027501016172878694,
                "ann_return_geometric": 0.027732835648205834,
                "ann_volatility": 0.017026455724279358,
                "annualized_capital_charge_drag": 0.017593344155844157,
                "annualized_cost_drag": 0.10953737423526433,
                "annualized_fee_drag": 0.09194403007942017,
                "annualized_turnover_perp_units": 48.40191383165196,
                "annualized_turnover_spot_units": 48.38557533105317,
                "annualized_turnover_units": 96.78748916270514,
                "avg_spot_notional_fraction": 0.8796672077922078,
                "invested_fraction": 0.9464285714285714,
                "max_drawdown": -0.2110329827390569,
                "position_entries": 275,
                "position_exits": 273,
                "rebalance_days": 2414,
                "sessions": 2464,
                "sharpe_backtest_scale": 1.628808490580891,
                "sharpe_canonical": 1.6151932391697257
              },
              "post2022": {
                "ann_return_arithmetic": -0.023822474905523874,
                "ann_return_geometric": -0.02359918607305833,
                "ann_volatility": 0.010850419206127573,
                "annualized_capital_charge_drag": 0.017786705624543462,
                "annualized_cost_drag": 0.10072509220906697,
                "annualized_fee_drag": 0.08293838658452352,
                "annualized_turnover_perp_units": 43.65628915877378,
                "annualized_turnover_spot_units": 43.649153477818246,
                "annualized_turnover_units": 87.305442636592,
                "avg_spot_notional_fraction": 0.8893352812271731,
                "invested_fraction": 0.9503287070854638,
                "max_drawdown": -0.1445490365503087,
                "position_entries": 140,
                "position_exits": 140,
                "rebalance_days": 1341,
                "sessions": 1369,
                "sharpe_backtest_scale": -2.1749561583511103,
                "sharpe_canonical": -2.1955349791527476
              },
              "test_oos": {
                "ann_return_arithmetic": -0.08547371192014448,
                "ann_return_geometric": -0.081984271450389,
                "ann_volatility": 0.010683163478067005,
                "annualized_capital_charge_drag": 0.016598746081504703,
                "annualized_cost_drag": 0.13120834478406007,
                "annualized_fee_drag": 0.11460959870255535,
                "annualized_turnover_perp_units": 60.3236306213407,
                "annualized_turnover_spot_units": 60.31921438968072,
                "annualized_turnover_units": 120.64284501102144,
                "avg_spot_notional_fraction": 0.8299373040752351,
                "invested_fraction": 0.9122257053291536,
                "max_drawdown": -0.14454903655030993,
                "position_entries": 95,
                "position_exits": 95,
                "rebalance_days": 613,
                "sessions": 638,
                "sharpe_backtest_scale": -7.674156781248012,
                "sharpe_canonical": -8.000786667322437
              },
              "train": {
                "ann_return_arithmetic": 0.09166709771290892,
                "ann_return_geometric": 0.09572214007387903,
                "ann_volatility": 0.02202574143250209,
                "annualized_capital_charge_drag": 0.017351598173515982,
                "annualized_cost_drag": 0.1205547387045467,
                "annualized_fee_drag": 0.10320314053103072,
                "annualized_turnover_perp_units": 54.335028148702435,
                "annualized_turnover_spot_units": 54.307184022449164,
                "annualized_turnover_units": 108.64221217115161,
                "avg_spot_notional_fraction": 0.867579908675799,
                "invested_fraction": 0.9415525114155251,
                "max_drawdown": -0.13650221556154096,
                "position_entries": 135,
                "position_exits": 133,
                "rebalance_days": 1073,
                "sessions": 1095,
                "sharpe_backtest_scale": 4.345921356028792,
                "sharpe_canonical": 4.161816663190333
              },
              "val": {
                "ann_return_arithmetic": 0.029985307878782477,
                "ann_return_geometric": 0.030384613996349064,
                "ann_volatility": 0.01019762379220389,
                "annualized_capital_charge_drag": 0.018823529411764708,
                "annualized_cost_drag": 0.07412000993431245,
                "annualized_fee_drag": 0.055296480522547736,
                "annualized_turnover_perp_units": 29.109416582689363,
                "annualized_turnover_spot_units": 29.099907428887658,
                "annualized_turnover_units": 58.209324011577024,
                "avg_spot_notional_fraction": 0.9411764705882353,
                "invested_fraction": 0.9835841313269493,
                "max_drawdown": -0.036067329337652665,
                "position_entries": 45,
                "position_exits": 45,
                "rebalance_days": 728,
                "sessions": 731,
                "sharpe_backtest_scale": 2.9795778522029983,
                "sharpe_canonical": 2.9404210715937884
              }
            }
          }
        },
        "realistic_usdt_5pct": {
          "samples": {
            "full": {
              "ann_return_geometric": 0.0009694925535974619,
              "annualized_capital_charge_drag": 0.04398336038961039,
              "annualized_fee_drag": 0.09194403007942017,
              "max_drawdown": -0.30015256975826676,
              "sharpe_canonical": 0.06588632708806845
            },
            "post2022": {
              "ann_return_geometric": -0.04930578742239311,
              "annualized_capital_charge_drag": 0.04446676406135866,
              "annualized_fee_drag": 0.08293838658452352,
              "max_drawdown": -0.18854768762822316,
              "sharpe_canonical": -4.738855788095243
            },
            "test_oos": {
              "ann_return_geometric": -0.10456293258026561,
              "annualized_capital_charge_drag": 0.04149686520376176,
              "annualized_fee_drag": 0.11460959870255535,
              "max_drawdown": -0.1775978062156892,
              "sharpe_canonical": -10.539133303504597
            },
            "train": {
              "ann_return_geometric": 0.06758125545840121,
              "annualized_capital_charge_drag": 0.04337899543378996,
              "annualized_fee_drag": 0.10320314053103072,
              "max_drawdown": -0.15410130139175648,
              "sharpe_canonical": 3.0036006481289883
            },
            "val": {
              "ann_return_geometric": 0.0017009801044576278,
              "annualized_capital_charge_drag": 0.047058823529411764,
              "annualized_fee_drag": 0.055296480522547736,
              "max_drawdown": -0.052127439752180926,
              "sharpe_canonical": 0.17408188058196242
            }
          }
        },
        "venue_maker_slippage": {
          "samples": {
            "full": {
              "ann_return_geometric": 0.06128225869822934,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.07742345592992458,
              "max_drawdown": -0.10009537029282123,
              "sharpe_canonical": 3.662734791086345
            },
            "post2022": {
              "ann_return_geometric": 0.0070376061247392485,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.06984149983689139,
              "max_drawdown": -0.09836893298312988,
              "sharpe_canonical": 0.7198075652901373
            },
            "test_oos": {
              "ann_return_geometric": -0.049554815272422115,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.09651250951615313,
              "max_drawdown": -0.0983689329831311,
              "sharpe_canonical": -5.449238071221437
            },
            "train": {
              "ann_return_geometric": 0.13322885847520638,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.08690263208641999,
              "max_drawdown": -0.09950666432060629,
              "sharpe_canonical": 5.876526753182781
            },
            "val": {
              "ann_return_geometric": 0.0591772352510187,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.04656365554774093,
              "max_drawdown": -0.023710423137023984,
              "sharpe_canonical": 6.080203023813844
            }
          }
        },
        "venue_taker": {
          "samples": {
            "full": {
              "ann_return_geometric": 0.06643183801746932,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.07258653224687917,
              "max_drawdown": -0.0910445600101033,
              "sharpe_canonical": 4.027133368475372
            },
            "post2022": {
              "ann_return_geometric": 0.011445731831047468,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.06547729805720513,
              "max_drawdown": -0.08927452943562697,
              "sharpe_canonical": 1.211886543738044
            },
            "test_oos": {
              "ann_return_geometric": -0.04379979565284686,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.09048102970035106,
              "max_drawdown": -0.08927452943562775,
              "sharpe_canonical": -5.075379702870726
            },
            "train": {
              "ann_return_geometric": 0.13940073860191649,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.08147469809680039,
              "max_drawdown": -0.0910445600101033,
              "sharpe_canonical": 6.2061522849007735
            },
            "val": {
              "ann_return_geometric": 0.062265052521319975,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.04365461572023234,
              "max_drawdown": -0.02198887396225091,
              "sharpe_canonical": 6.572782998334156
            }
          }
        },
        "venue_taker_slippage": {
          "samples": {
            "full": {
              "ann_return_geometric": 0.04597022763201575,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.09194403007942017,
              "max_drawdown": -0.14860121932028014,
              "sharpe_canonical": 2.630825368819771
            },
            "post2022": {
              "ann_return_geometric": -0.006077603274039278,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.08293838658452352,
              "max_drawdown": -0.12511798612843217,
              "sharpe_canonical": -0.5494117312351042
            },
            "test_oos": {
              "ann_return_geometric": -0.06661742586470665,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.11460959870255535,
              "max_drawdown": -0.12511798612843228,
              "sharpe_canonical": -6.357325893699512
            },
            "train": {
              "ann_return_geometric": 0.11489236535522407,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.10320314053103072,
              "max_drawdown": -0.12466011890076589,
              "sharpe_canonical": 4.923051749006123
            },
            "val": {
              "ann_return_geometric": 0.049960583271813075,
              "annualized_capital_charge_drag": 0.0,
              "annualized_fee_drag": 0.055296480522547736,
              "max_drawdown": -0.02885840227569436,
              "sharpe_canonical": 4.739835902663224
            }
          }
        }
      }
    },
    "threshold": {
      "always_on": {
        "realistic_rf": {
          "samples": {
            "full": {
              "ann_return_arithmetic": 0.09094897420666076,
              "ann_return_geometric": 0.09508081836800408,
              "ann_volatility": 0.014803898604688557,
              "annualized_capital_charge_drag": 0.019993434396718808,
              "annualized_cost_drag": 0.034846121222069794,
              "annualized_fee_drag": 0.014852686825350988,
              "annualized_turnover_perp_units": 7.8283682642652925,
              "annualized_turnover_spot_units": 7.810690866971069,
              "annualized_turnover_units": 15.639059131236364,
              "avg_gross_exposure": 1.9993411474425407,
              "avg_spot_notional_fraction": 0.9996717198359404,
              "downside_deviation_annualized": 0.010995854944627858,
              "end": "2026-09-30",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 1.0,
              "max_drawdown": -0.02021845815949086,
              "max_drawdown_recomputed": -0.02021845815949086,
              "position_entries": 2,
              "position_exits": 0,
              "profit_factor": 4.427123922070466,
              "rebalance_days": 1461,
              "risk_free_rate_annual": 0.02,
              "sample": "full",
              "sessions": 2464,
              "sharpe_backtest_scale": 6.422687759958782,
              "sharpe_canonical": 6.143582622070663,
              "sortino_backtest_scale": 8.646969139444389,
              "sortino_canonical": 8.271205346437828,
              "start": "2020-01-02",
              "total_return": 0.8462422186397718
            },
            "post2022": {
              "ann_return_arithmetic": 0.04169130691808301,
              "ann_return_geometric": 0.042554088490691866,
              "ann_volatility": 0.005547885057728993,
              "annualized_capital_charge_drag": 0.019996533350350315,
              "annualized_cost_drag": 0.030919045793288254,
              "annualized_fee_drag": 0.010922512442937937,
              "annualized_turnover_perp_units": 5.753515423003867,
              "annualized_turnover_spot_units": 5.745876372362692,
              "annualized_turnover_units": 11.499391795366558,
              "avg_gross_exposure": 1.999650699140327,
              "avg_spot_notional_fraction": 0.9998266675175157,
              "downside_deviation_annualized": 0.00277707366285603,
              "end": "2026-09-30",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 1.0,
              "max_drawdown": -0.014141968485220202,
              "max_drawdown_recomputed": -0.014141968485220202,
              "position_entries": 0,
              "position_exits": 0,
              "profit_factor": 3.6464628582416587,
              "rebalance_days": 709,
              "risk_free_rate_annual": 0.02,
              "sample": "post2022",
              "sessions": 1369,
              "sharpe_backtest_scale": 7.6703262680988615,
              "sharpe_canonical": 7.514810866530317,
              "sortino_backtest_scale": 15.323356041959613,
              "sortino_canonical": 15.012675924197975,
              "start": "2023-01-01",
              "total_return": 0.1691820263033046
            },
            "test_oos": {
              "ann_return_arithmetic": 0.007488283320053992,
              "ann_return_geometric": 0.007511121496622142,
              "ann_volatility": 0.0032127696227180966,
              "annualized_capital_charge_drag": 0.020001775120690846,
              "annualized_cost_drag": 0.03150177386647969,
              "annualized_fee_drag": 0.011499998745788843,
              "annualized_turnover_perp_units": 6.055183624695692,
              "annualized_turnover_spot_units": 6.051141840418216,
              "annualized_turnover_units": 12.106325465113907,
              "avg_gross_exposure": 2.0001830053259892,
              "avg_spot_notional_fraction": 1.0000887560345422,
              "downside_deviation_annualized": 0.002382815560560173,
              "end": "2026-09-30",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 1.0,
              "max_drawdown": -0.01414196848521998,
              "max_drawdown_recomputed": -0.01414196848521998,
              "position_entries": 0,
              "position_exits": 0,
              "profit_factor": 1.384592778060914,
              "rebalance_days": 345,
              "risk_free_rate_annual": 0.02,
              "sample": "test_oos",
              "sessions": 638,
              "sharpe_backtest_scale": 2.3378960768022683,
              "sharpe_canonical": 2.330787513397455,
              "sortino_backtest_scale": 3.1522043170040246,
              "sortino_canonical": 3.1426197830828255,
              "start": "2025-01-01",
              "total_return": 0.013165884422614127
            },
            "train": {
              "ann_return_arithmetic": 0.1525323043601429,
              "ann_return_geometric": 0.16448933619915596,
              "ann_volatility": 0.020885257172329294,
              "annualized_capital_charge_drag": 0.019989559997155768,
              "annualized_cost_drag": 0.03975586210061038,
              "annualized_fee_drag": 0.01976630210345461,
              "annualized_turnover_perp_units": 10.422408026536427,
              "annualized_turnover_spot_units": 10.392180404065927,
              "annualized_turnover_units": 20.814588430602356,
              "avg_gross_exposure": 1.9989541371464041,
              "avg_spot_notional_fraction": 0.9994779998577883,
              "downside_deviation_annualized": 0.01610687733821312,
              "end": "2022-12-31",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 1.0,
              "max_drawdown": -0.02021845815949086,
              "max_drawdown_recomputed": -0.02021845815949086,
              "position_entries": 2,
              "position_exits": 0,
              "profit_factor": 4.811312335756677,
              "rebalance_days": 752,
              "risk_free_rate_annual": 0.02,
              "sample": "train",
              "sessions": 1095,
              "sharpe_backtest_scale": 7.875858786028574,
              "sharpe_canonical": 7.303348151356819,
              "sortino_backtest_scale": 10.212366602489086,
              "sortino_canonical": 9.470010924977013,
              "start": "2020-01-02",
              "total_return": 0.5790887792529524
            },
            "val": {
              "ann_return_arithmetic": 0.07154291985316169,
              "ann_return_geometric": 0.07413344872362937,
              "ann_volatility": 0.006589859469846397,
              "annualized_capital_charge_drag": 0.019991958453664603,
              "annualized_cost_drag": 0.030410454123389302,
              "annualized_fee_drag": 0.010418495669724697,
              "annualized_turnover_perp_units": 5.4902263495710555,
              "annualized_turnover_spot_units": 5.479447687520798,
              "annualized_turnover_units": 10.969674037091856,
              "avg_gross_exposure": 1.9991861145350565,
              "avg_spot_notional_fraction": 0.9995979226832302,
              "downside_deviation_annualized": 0.003294908586317056,
              "end": "2024-12-31",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 1.0,
              "max_drawdown": -0.003313478705102346,
              "max_drawdown_recomputed": -0.003313478705102346,
              "position_entries": 0,
              "position_exits": 0,
              "profit_factor": 6.719128346757657,
              "rebalance_days": 364,
              "risk_free_rate_annual": 0.02,
              "sample": "val",
              "sessions": 731,
              "sharpe_backtest_scale": 11.249625134321317,
              "sharpe_canonical": 10.856516771036588,
              "sortino_backtest_scale": 22.49939468168778,
              "sortino_canonical": 21.713172908730098,
              "start": "2023-01-01",
              "total_return": 0.15398874387642913
            }
          }
        }
      },
      "funding_positive_lagged": {
        "realistic_rf": {
          "samples": {
            "full": {
              "ann_return_arithmetic": 0.022036140772611724,
              "ann_return_geometric": 0.022112784738469005,
              "ann_volatility": 0.01809496589316271,
              "annualized_capital_charge_drag": 0.017578565398642627,
              "annualized_cost_drag": 0.10727210855387799,
              "annualized_fee_drag": 0.08969354315523537,
              "annualized_turnover_perp_units": 47.21800733753206,
              "annualized_turnover_spot_units": 47.20078168246911,
              "annualized_turnover_units": 94.41878902000117,
              "avg_gross_exposure": 1.7578519368945849,
              "avg_spot_notional_fraction": 0.8789282699321314,
              "downside_deviation_annualized": 0.014078063641682115,
              "end": "2026-09-30",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 0.9460227272727273,
              "max_drawdown": -0.2242512336305026,
              "max_drawdown_recomputed": -0.2242512336305026,
              "position_entries": 275,
              "position_exits": 273,
              "profit_factor": 1.2438487373426608,
              "rebalance_days": 1608,
              "risk_free_rate_annual": 0.02,
              "sample": "full",
              "sessions": 2464,
              "sharpe_backtest_scale": 1.2220406973424829,
              "sharpe_canonical": 1.2178050460398053,
              "sortino_backtest_scale": 1.5707262945592753,
              "sortino_canonical": 1.5652820823573674,
              "start": "2020-01-02",
              "total_return": 0.1591070429608159
            },
            "post2022": {
              "ann_return_arithmetic": -0.024551676930398728,
              "ann_return_geometric": -0.024312904106721378,
              "ann_volatility": 0.011031816821142073,
              "annualized_capital_charge_drag": 0.017783611024923186,
              "annualized_cost_drag": 0.09818812162327609,
              "annualized_fee_drag": 0.0804045105983529,
              "annualized_turnover_perp_units": 42.32280094364869,
              "annualized_turnover_spot_units": 42.31545828149901,
              "annualized_turnover_units": 84.6382592251477,
              "avg_gross_exposure": 1.7783573713125627,
              "avg_spot_notional_fraction": 0.8891805512461592,
              "downside_deviation_annualized": 0.011153538991458845,
              "end": "2026-09-30",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 0.9503287070854638,
              "max_drawdown": -0.14793781691882157,
              "max_drawdown_recomputed": -0.14793781691882157,
              "position_entries": 140,
              "position_exits": 140,
              "profit_factor": 0.6912014719864323,
              "rebalance_days": 801,
              "risk_free_rate_annual": 0.02,
              "sample": "post2022",
              "sessions": 1369,
              "sharpe_backtest_scale": -2.2038893956366814,
              "sharpe_canonical": -2.2255334119894323,
              "sortino_backtest_scale": -2.179837639455935,
              "sortino_canonical": -2.2012454476735956,
              "start": "2023-01-01",
              "total_return": -0.0881838440441276
            },
            "test_oos": {
              "ann_return_arithmetic": -0.08744952857136225,
              "ann_return_geometric": -0.08379865595546365,
              "ann_volatility": 0.010877021953306433,
              "annualized_capital_charge_drag": 0.01660341096055766,
              "annualized_cost_drag": 0.12898832023219053,
              "annualized_fee_drag": 0.11238490927163289,
              "annualized_turnover_perp_units": 59.15256166225327,
              "annualized_turnover_spot_units": 59.148430090046354,
              "annualized_turnover_units": 118.30099175229961,
              "avg_gross_exposure": 1.660344828132477,
              "avg_spot_notional_fraction": 0.8301705480278829,
              "downside_deviation_annualized": 0.011481527372375759,
              "end": "2026-09-30",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 0.9122257053291536,
              "max_drawdown": -0.14793781691882224,
              "max_drawdown_recomputed": -0.14793781691882224,
              "position_entries": 95,
              "position_exits": 95,
              "profit_factor": 0.21464103799893522,
              "rebalance_days": 399,
              "risk_free_rate_annual": 0.02,
              "sample": "test_oos",
              "sessions": 638,
              "sharpe_backtest_scale": -7.704191120988798,
              "sharpe_canonical": -8.039841139125315,
              "sortino_backtest_scale": -7.298563443491058,
              "sortino_canonical": -7.6165414003857554,
              "start": "2025-01-01",
              "total_return": -0.14185195232246017
            },
            "train": {
              "ann_return_arithmetic": 0.08028154938943487,
              "ann_return_geometric": 0.08327508324129096,
              "ann_volatility": 0.023837688926875125,
              "annualized_capital_charge_drag": 0.017322211551722005,
              "annualized_cost_drag": 0.11862916618674924,
              "annualized_fee_drag": 0.10130695463502723,
              "annualized_turnover_perp_units": 53.33813295691683,
              "annualized_turnover_spot_units": 53.30855130432123,
              "annualized_turnover_units": 106.64668426123804,
              "avg_gross_exposure": 1.732215462266081,
              "avg_spot_notional_fraction": 0.8661105775861002,
              "downside_deviation_annualized": 0.016840651368623307,
              "end": "2022-12-31",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 0.9406392694063926,
              "max_drawdown": -0.14848646914278774,
              "max_drawdown_recomputed": -0.14848646914278774,
              "position_entries": 135,
              "position_exits": 133,
              "profit_factor": 1.7723333096031446,
              "rebalance_days": 807,
              "risk_free_rate_annual": 0.02,
              "sample": "train",
              "sessions": 1095,
              "sharpe_backtest_scale": 3.4934210064048967,
              "sharpe_canonical": 3.3678411374402875,
              "sortino_backtest_scale": 4.9448849345842465,
              "sortino_canonical": 4.767128517309704,
              "start": "2020-01-02",
              "total_return": 0.27120695919859505
            },
            "val": {
              "ann_return_arithmetic": 0.030344122449812938,
              "ann_return_geometric": 0.030752773857952276,
              "ann_volatility": 0.010348268012894743,
              "annualized_capital_charge_drag": 0.018813662517488446,
              "annualized_cost_drag": 0.07130641613423716,
              "annualized_fee_drag": 0.05249275361674872,
              "annualized_turnover_perp_units": 27.63417257364907,
              "annualized_turnover_spot_units": 27.62402734599532,
              "annualized_turnover_units": 55.25819991964438,
              "avg_gross_exposure": 1.881356006810366,
              "avg_spot_notional_fraction": 0.9406831258744223,
              "downside_deviation_annualized": 0.010461849931782353,
              "end": "2024-12-31",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 0.9835841313269493,
              "max_drawdown": -0.037285843849416245,
              "max_drawdown_recomputed": -0.037285843849416245,
              "position_entries": 45,
              "position_exits": 45,
              "profit_factor": 1.5867502170264813,
              "rebalance_days": 402,
              "risk_free_rate_annual": 0.02,
              "sample": "val",
              "sessions": 731,
              "sharpe_backtest_scale": 2.9717798011833416,
              "sharpe_canonical": 2.932289965045533,
              "sortino_backtest_scale": 2.93951586559539,
              "sortino_canonical": 2.9004547616028846,
              "start": "2023-01-01",
              "total_return": 0.0625394515824822
            }
          }
        }
      },
      "funding_positive_sameday": {
        "realistic_rf": {
          "samples": {
            "full": {
              "ann_return_arithmetic": 0.02985044916235852,
              "ann_return_geometric": 0.030149964936691642,
              "ann_volatility": 0.017032743021582683,
              "annualized_capital_charge_drag": 0.01758662691492275,
              "annualized_cost_drag": 0.10712325002232348,
              "annualized_fee_drag": 0.08953662310740074,
              "annualized_turnover_perp_units": 47.13440085609277,
              "annualized_turnover_spot_units": 47.118785423446504,
              "annualized_turnover_units": 94.25318627953926,
              "avg_gross_exposure": 1.7586542446621019,
              "avg_spot_notional_fraction": 0.8793313457461375,
              "downside_deviation_annualized": 0.011060296746410934,
              "end": "2026-09-30",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 0.9464285714285714,
              "max_drawdown": -0.2025660299852129,
              "max_drawdown_recomputed": -0.2025660299852129,
              "position_entries": 275,
              "position_exits": 273,
              "profit_factor": 1.3559293274396982,
              "rebalance_days": 1602,
              "risk_free_rate_annual": 0.02,
              "sample": "full",
              "sessions": 2464,
              "sharpe_backtest_scale": 1.7701179955857813,
              "sharpe_canonical": 1.752533289825024,
              "sortino_backtest_scale": 2.7259634734913694,
              "sortino_canonical": 2.6988832078167335,
              "start": "2020-01-02",
              "total_return": 0.2220441250654983
            },
            "post2022": {
              "ann_return_arithmetic": -0.02128692093467517,
              "ann_return_geometric": -0.021120467611472238,
              "ann_volatility": 0.010878072855575831,
              "annualized_capital_charge_drag": 0.01778247667991911,
              "annualized_cost_drag": 0.09815506003288856,
              "annualized_fee_drag": 0.08037258335296944,
              "annualized_turnover_perp_units": 42.30580321852921,
              "annualized_turnover_spot_units": 42.2987675833325,
              "annualized_turnover_units": 84.60457080186171,
              "avg_gross_exposure": 1.7782402480868034,
              "avg_spot_notional_fraction": 0.8891238339959554,
              "downside_deviation_annualized": 0.01103472127733255,
              "end": "2026-09-30",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 0.9503287070854638,
              "max_drawdown": -0.14168397060056526,
              "max_drawdown_recomputed": -0.14168397060056526,
              "position_entries": 140,
              "position_exits": 140,
              "profit_factor": 0.7235980158287485,
              "rebalance_days": 799,
              "risk_free_rate_annual": 0.02,
              "sample": "post2022",
              "sessions": 1369,
              "sharpe_backtest_scale": -1.941563353351362,
              "sharpe_canonical": -1.956865082381207,
              "sortino_backtest_scale": -1.9140010047066398,
              "sortino_canonical": -1.929085511058863,
              "start": "2023-01-01",
              "total_return": -0.07694340497778163
            },
            "test_oos": {
              "ann_return_arithmetic": -0.0830609098311003,
              "ann_return_geometric": -0.07976633138141509,
              "ann_volatility": 0.010707356434780584,
              "annualized_capital_charge_drag": 0.016600900566492334,
              "annualized_cost_drag": 0.12882139279078608,
              "annualized_fee_drag": 0.11222049222429376,
              "annualized_turnover_perp_units": 59.065549839670204,
              "annualized_turnover_spot_units": 59.06217278043719,
              "annualized_turnover_units": 118.1277226201074,
              "avg_gross_exposure": 1.660088835437577,
              "avg_spot_notional_fraction": 0.8300450283246166,
              "downside_deviation_annualized": 0.011267316254599192,
              "end": "2026-09-30",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 0.9122257053291536,
              "max_drawdown": -0.14168397060056492,
              "max_drawdown_recomputed": -0.14168397060056492,
              "position_entries": 95,
              "position_exits": 95,
              "profit_factor": 0.23171192540870073,
              "rebalance_days": 397,
              "risk_free_rate_annual": 0.02,
              "sample": "test_oos",
              "sessions": 638,
              "sharpe_backtest_scale": -7.449675544778824,
              "sharpe_canonical": -7.757368528546831,
              "sortino_backtest_scale": -7.079443727236765,
              "sortino_canonical": -7.371845074215945,
              "start": "2025-01-01",
              "total_return": -0.13523940875154028
            },
            "train": {
              "ann_return_arithmetic": 0.09378383698230291,
              "ann_return_geometric": 0.09804343397009774,
              "ann_volatility": 0.02202296870776184,
              "annualized_capital_charge_drag": 0.017341769994119086,
              "annualized_cost_drag": 0.11833553504107823,
              "annualized_fee_drag": 0.10099376504695914,
              "annualized_turnover_perp_units": 53.17125032259916,
              "annualized_turnover_spot_units": 53.14490818428312,
              "annualized_turnover_units": 106.31615850688227,
              "avg_gross_exposure": 1.7341672686909455,
              "avg_spot_notional_fraction": 0.8670884997059543,
              "downside_deviation_annualized": 0.01101856486830241,
              "end": "2022-12-31",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 0.9415525114155251,
              "max_drawdown": -0.13502823364097682,
              "max_drawdown_recomputed": -0.13502823364097682,
              "position_entries": 135,
              "position_exits": 133,
              "profit_factor": 2.01461833729012,
              "rebalance_days": 803,
              "risk_free_rate_annual": 0.02,
              "sample": "train",
              "sessions": 1095,
              "sharpe_backtest_scale": 4.45187182850344,
              "sharpe_canonical": 4.258455716247259,
              "sortino_backtest_scale": 8.89802212374713,
              "sortino_canonical": 8.51143847708289,
              "start": "2020-01-02",
              "total_return": 0.32391029071850186
            },
            "val": {
              "ann_return_arithmetic": 0.0326279968709599,
              "ann_return_geometric": 0.03311065497865706,
              "ann_volatility": 0.010227318191732457,
              "annualized_capital_charge_drag": 0.018813729156480375,
              "annualized_cost_drag": 0.07139018958208329,
              "annualized_fee_drag": 0.05257646042560292,
              "annualized_turnover_perp_units": 27.678281543716704,
              "annualized_turnover_spot_units": 27.668052787501026,
              "annualized_turnover_units": 55.34633433121773,
              "avg_gross_exposure": 1.881360085665745,
              "avg_spot_notional_fraction": 0.9406864578240186,
              "downside_deviation_annualized": 0.010418845685959742,
              "end": "2024-12-31",
              "engine_risk_free_rate_annual": 0.0,
              "invested_fraction": 0.9835841313269493,
              "max_drawdown": -0.03454721858788257,
              "max_drawdown_recomputed": -0.03454721858788257,
              "position_entries": 45,
              "position_exits": 45,
              "profit_factor": 1.6542172998153581,
              "rebalance_days": 402,
              "risk_free_rate_annual": 0.02,
              "sample": "val",
              "sessions": 731,
              "sharpe_backtest_scale": 3.2374718726775313,
              "sharpe_canonical": 3.1902788452730126,
              "sortino_backtest_scale": 3.177958094079118,
              "sortino_canonical": 3.131632606376811,
              "start": "2023-01-01",
              "total_return": 0.06741288208982388
            }
          }
        }
      }
    },
    "threshold_break_evens": {
      "always_on": {
        "full": {
          "break_even_capital_charge_annual": {
            "bracketed": true,
            "fee_model": "venue_taker_slippage",
            "note": "The annual rate charged on the spot leg's notional at which the net annualized return is exactly zero, with the trading fees held at the stated model.",
            "reason": "",
            "sample": "full",
            "solution_annual_rate": 0.11086923768743873
          },
          "break_even_flat_cost_bps": {
            "bracketed": true,
            "note": "The flat cost per unit (both legs, one number) at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "full",
            "solution_bps": 80.33294132083029
          },
          "break_even_venue_fee_multiplier": {
            "bracketed": true,
            "cost_model": "realistic_rf",
            "note": "The multiple of the published fee schedule at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "full",
            "solution_multiplier": 7.113578089411021
          }
        },
        "test_oos": {
          "break_even_capital_charge_annual": {
            "bracketed": true,
            "fee_model": "venue_taker_slippage",
            "note": "The annual rate charged on the spot leg's notional at which the net annualized return is exactly zero, with the trading fees held at the stated model.",
            "reason": "",
            "sample": "test_oos",
            "solution_annual_rate": 0.02748246630653739
          },
          "break_even_flat_cost_bps": {
            "bracketed": true,
            "note": "The flat cost per unit (both legs, one number) at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "test_oos",
            "solution_bps": 32.19900298126959
          },
          "break_even_venue_fee_multiplier": {
            "bracketed": true,
            "cost_model": "realistic_rf",
            "note": "The multiple of the published fee schedule at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "test_oos",
            "solution_multiplier": 1.650651768068201
          }
        }
      },
      "funding_positive_lagged": {
        "full": {
          "break_even_capital_charge_annual": {
            "bracketed": true,
            "fee_model": "venue_taker_slippage",
            "note": "The annual rate charged on the spot leg's notional at which the net annualized return is exactly zero, with the trading fees held at the stated model.",
            "reason": "",
            "sample": "full",
            "solution_annual_rate": 0.044887963216751814
          },
          "break_even_flat_cost_bps": {
            "bracketed": true,
            "note": "The flat cost per unit (both legs, one number) at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "full",
            "solution_bps": 13.672181465790345
          },
          "break_even_venue_fee_multiplier": {
            "bracketed": true,
            "cost_model": "realistic_rf",
            "note": "The multiple of the published fee schedule at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "full",
            "solution_multiplier": 1.2435629596438957
          }
        },
        "test_oos": {
          "break_even_capital_charge_annual": {
            "bracketed": true,
            "fee_model": "venue_taker_slippage",
            "note": "The annual rate charged on the spot leg's notional at which the net annualized return is exactly zero, with the trading fees held at the stated model.",
            "reason": "",
            "sample": "test_oos",
            "solution_annual_rate": -0.08542207768186927
          },
          "break_even_flat_cost_bps": {
            "bracketed": true,
            "note": "The flat cost per unit (both legs, one number) at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "test_oos",
            "solution_bps": 3.510159239431232
          },
          "break_even_venue_fee_multiplier": {
            "bracketed": true,
            "cost_model": "realistic_rf",
            "note": "The multiple of the published fee schedule at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "test_oos",
            "solution_multiplier": 0.22181077401910443
          }
        }
      },
      "funding_positive_sameday": {
        "full": {
          "break_even_capital_charge_annual": {
            "bracketed": true,
            "fee_model": "venue_taker_slippage",
            "note": "The annual rate charged on the spot leg's notional at which the net annualized return is exactly zero, with the trading fees held at the stated model.",
            "reason": "",
            "sample": "full",
            "solution_annual_rate": 0.053785568568855524
          },
          "break_even_flat_cost_bps": {
            "bracketed": true,
            "note": "The flat cost per unit (both legs, one number) at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "full",
            "solution_bps": 14.510295600939571
          },
          "break_even_venue_fee_multiplier": {
            "bracketed": true,
            "cost_model": "realistic_rf",
            "note": "The multiple of the published fee schedule at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "full",
            "solution_multiplier": 1.3313629980984842
          }
        },
        "test_oos": {
          "break_even_capital_charge_annual": {
            "bracketed": true,
            "fee_model": "venue_taker_slippage",
            "note": "The annual rate charged on the spot leg's notional at which the net annualized return is exactly zero, with the trading fees held at the stated model.",
            "reason": "",
            "sample": "test_oos",
            "solution_annual_rate": -0.08014816464856267
          },
          "break_even_flat_cost_bps": {
            "bracketed": true,
            "note": "The flat cost per unit (both legs, one number) at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "test_oos",
            "solution_bps": 3.872632248658192
          },
          "break_even_venue_fee_multiplier": {
            "bracketed": true,
            "cost_model": "realistic_rf",
            "note": "The multiple of the published fee schedule at which the net annualized return is exactly zero.",
            "reason": "",
            "sample": "test_oos",
            "solution_multiplier": 0.2597755807073554
          }
        }
      }
    },
    "threshold_gates": {
      "always_on": {
        "realistic_rf": {
          "gate_pass_note": "The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.",
          "min_pooled_oos_trades": 100,
          "net_oos_sharpe_canonical_365": 2.08821960910283,
          "net_oos_sharpe_min": 0.9,
          "pooled_oos_position_round_trips": 0,
          "pooled_oos_rebalance_days_repo_convention": 508,
          "pooled_oos_settlement_observations": 3828,
          "promotion_gate_pass": false,
          "sharpe_criterion_pass": true,
          "trade_count_criterion_pass": false
        }
      },
      "funding_positive_lagged": {
        "realistic_rf": {
          "gate_pass_note": "The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.",
          "min_pooled_oos_trades": 100,
          "net_oos_sharpe_canonical_365": -6.276213708599346,
          "net_oos_sharpe_min": 0.9,
          "pooled_oos_position_round_trips": 95,
          "pooled_oos_rebalance_days_repo_convention": 555,
          "pooled_oos_settlement_observations": 3828,
          "promotion_gate_pass": false,
          "sharpe_criterion_pass": false,
          "trade_count_criterion_pass": false
        }
      },
      "funding_positive_sameday": {
        "realistic_rf": {
          "gate_pass_note": "The Sharpe criterion is met by a wide margin. The trade-count criterion is not met on independent position round trips; the repository's rebalance-day count is reported next to it because for a continuously held carry position it counts daily rebalances of one position, not independent trades. The always-on book reports 0 round trips in the out-of-sample window because it opens its position once, before that window, and never closes it: its independent observations are the daily funding settlements (3,828 eight-hour settlements in the window), not new positions. That is a counting convention, stated here so that '0 trades' is not read as a defect in the construction.",
          "min_pooled_oos_trades": 100,
          "net_oos_sharpe_canonical_365": -6.030517343233685,
          "net_oos_sharpe_min": 0.9,
          "pooled_oos_position_round_trips": 95,
          "pooled_oos_rebalance_days_repo_convention": 550,
          "pooled_oos_settlement_observations": 3828,
          "promotion_gate_pass": false,
          "sharpe_criterion_pass": false,
          "trade_count_criterion_pass": false
        }
      }
    },
    "threshold_per_symbol": {
      "always_on": {
        "realistic_rf": {
          "BTCUSDT": {
            "full": {
              "ann_return_arithmetic": 0.083890651201164,
              "ann_return_geometric": 0.08740065798595409,
              "ann_volatility": 0.013489470921175972,
              "annualized_capital_charge_drag": 0.019991010211424458,
              "annualized_cost_drag": 0.03198389722224117,
              "annualized_fee_drag": 0.011992887010816711,
              "annualized_turnover_perp_units": 6.320125748934355,
              "annualized_turnover_spot_units": 6.307332488802219,
              "annualized_turnover_units": 12.627458237736576,
              "avg_spot_notional_fraction": 0.9995505105712229,
              "invested_fraction": 1.0,
              "max_drawdown": -0.02831855537350303,
              "position_entries": 1,
              "position_exits": 0,
              "rebalance_days": 952,
              "sessions": 2464,
              "sharpe_backtest_scale": 6.479176129046784,
              "sharpe_canonical": 6.218972685538853
            },
            "post2022": {
              "ann_return_arithmetic": 0.043365001742735144,
              "ann_return_geometric": 0.04429887440051461,
              "ann_volatility": 0.005782989780277704,
              "annualized_capital_charge_drag": 0.01999414376685661,
              "annualized_cost_drag": 0.028759352159442433,
              "annualized_fee_drag": 0.008765208392585823,
              "annualized_turnover_perp_units": 4.6166354645501215,
              "annualized_turnover_spot_units": 4.61130297283395,
              "annualized_turnover_units": 9.22793843738407,
              "avg_spot_notional_fraction": 0.9997071883428305,
              "invested_fraction": 1.0,
              "max_drawdown": -0.012390737191051882,
              "position_entries": 0,
              "position_exits": 0,
              "rebalance_days": 447,
              "sessions": 1369,
              "sharpe_backtest_scale": 7.660202781542412,
              "sharpe_canonical": 7.498716648372275
            },
            "test_oos": {
              "ann_return_arithmetic": 0.013816652967273432,
              "ann_return_geometric": 0.013905954912033058,
              "ann_volatility": 0.0035348223727764603,
              "annualized_capital_charge_drag": 0.019994419507034327,
              "annualized_cost_drag": 0.028096353039631924,
              "annualized_fee_drag": 0.008101933532597597,
              "annualized_turnover_perp_units": 4.265362464931862,
              "annualized_turnover_spot_units": 4.2634831726210765,
              "annualized_turnover_units": 8.528845637552939,
              "avg_spot_notional_fraction": 0.9997209753517162,
              "invested_fraction": 1.0,
              "max_drawdown": -0.012390737191051437,
              "position_entries": 0,
              "position_exits": 0,
              "rebalance_days": 207,
              "sessions": 638,
              "sharpe_backtest_scale": 3.933989730044198,
              "sharpe_canonical": 3.9087262414323267
            },
            "train": {
              "ann_return_arithmetic": 0.13455696545558327,
              "ann_return_geometric": 0.14379864738279924,
              "ann_volatility": 0.01884631296784794,
              "annualized_capital_charge_drag": 0.019987092551710647,
              "annualized_cost_drag": 0.0360153147482425,
              "annualized_fee_drag": 0.016028222196531855,
              "annualized_turnover_perp_units": 8.449877529137108,
              "annualized_turnover_spot_units": 8.427756605113235,
              "annualized_turnover_units": 16.87763413425034,
              "avg_spot_notional_fraction": 0.9993546275855324,
              "invested_fraction": 1.0,
              "max_drawdown": -0.02831855537350303,
              "position_entries": 1,
              "position_exits": 0,
              "rebalance_days": 505,
              "sessions": 1095,
              "sharpe_backtest_scale": 7.630067887980085,
              "sharpe_canonical": 7.139697068871732
            },
            "val": {
              "ann_return_arithmetic": 0.06915412146741994,
              "ann_return_geometric": 0.07156874914754807,
              "ann_volatility": 0.006917574362210798,
              "annualized_capital_charge_drag": 0.019993903107166627,
              "annualized_cost_drag": 0.02933800255402398,
              "annualized_fee_drag": 0.009344099446857355,
              "annualized_turnover_perp_units": 4.923218465584935,
              "annualized_turnover_spot_units": 4.914872100789918,
              "annualized_turnover_units": 9.838090566374854,
              "avg_spot_notional_fraction": 0.9996951553583313,
              "invested_fraction": 1.0,
              "max_drawdown": -0.004178537483762623,
              "position_entries": 0,
              "position_exits": 0,
              "rebalance_days": 240,
              "sessions": 731,
              "sharpe_backtest_scale": 10.345931304838956,
              "sharpe_canonical": 9.99687431553954
            }
          },
          "ETHUSDT": {
            "full": {
              "ann_return_arithmetic": 0.09800798319882083,
              "ann_return_geometric": 0.10277897117369261,
              "ann_volatility": 0.017979746840479094,
              "annualized_capital_charge_drag": 0.019996054297677437,
              "annualized_cost_drag": 0.03770854093756271,
              "annualized_fee_drag": 0.017712486639885266,
              "annualized_turnover_perp_units": 9.33661077959623,
              "annualized_turnover_spot_units": 9.314049245139921,
              "annualized_turnover_units": 18.650660024736148,
              "avg_spot_notional_fraction": 0.9998027148838718,
              "invested_fraction": 1.0,
              "max_drawdown": -0.03801679395152069,
              "position_entries": 1,
              "position_exits": 0,
              "rebalance_days": 1259,
              "sessions": 2464,
              "sharpe_backtest_scale": 5.716374767986107,
              "sharpe_canonical": 5.451021311277222
            },
            "post2022": {
              "ann_return_arithmetic": 0.040018358390731715,
              "ann_return_geometric": 0.04080675392984423,
              "ann_volatility": 0.00633261751217138,
              "annualized_capital_charge_drag": 0.019998919156938938,
              "annualized_cost_drag": 0.03307873565022899,
              "annualized_fee_drag": 0.01307981649329005,
              "annualized_turnover_perp_units": 6.890395381457609,
              "annualized_turnover_spot_units": 6.880449771891436,
              "annualized_turnover_units": 13.770845153349047,
              "avg_spot_notional_fraction": 0.9999459578469468,
              "invested_fraction": 1.0,
              "max_drawdown": -0.016801406243607153,
              "position_entries": 0,
              "position_exits": 0,
              "rebalance_days": 599,
              "sessions": 1369,
              "sharpe_backtest_scale": 6.443899991024733,
              "sharpe_canonical": 6.31940241358583
            },
            "test_oos": {
              "ann_return_arithmetic": 0.0011602391071410484,
              "ann_return_geometric": 0.0011515212267501074,
              "ann_volatility": 0.004333891920836537,
              "annualized_capital_charge_drag": 0.02000895040892647,
              "annualized_cost_drag": 0.03490701436790656,
              "annualized_fee_drag": 0.014898063958980091,
              "annualized_turnover_perp_units": 7.845004784459519,
              "annualized_turnover_spot_units": 7.838800508215358,
              "annualized_turnover_units": 15.68380529267488,
              "avg_spot_notional_fraction": 1.0004475204463235,
              "invested_fraction": 1.0,
              "max_drawdown": -0.01680140624360782,
              "position_entries": 0,
              "position_exits": 0,
              "rebalance_days": 301,
              "sessions": 638,
              "sharpe_backtest_scale": 0.26570141752123766,
              "sharpe_canonical": 0.2677129767733333
            },
            "train": {
              "ann_return_arithmetic": 0.17050825384929932,
              "ann_return_geometric": 0.1854743961764329,
              "ann_volatility": 0.025528704638079897,
              "annualized_capital_charge_drag": 0.01999247256952311,
              "annualized_cost_drag": 0.043496854579900476,
              "annualized_fee_drag": 0.023504382010377366,
              "annualized_turnover_perp_units": 12.394938523935744,
              "annualized_turnover_spot_units": 12.356604203018618,
              "annualized_turnover_units": 24.751542726954366,
              "avg_spot_notional_fraction": 0.9996236284761555,
              "invested_fraction": 1.0,
              "max_drawdown": -0.03801679395152069,
              "position_entries": 1,
              "position_exits": 0,
              "rebalance_days": 660,
              "sessions": 1095,
              "sharpe_backtest_scale": 7.265327356240786,
              "sharpe_canonical": 6.679079736578591
            },
            "val": {
              "ann_return_arithmetic": 0.0739328318557534,
              "ann_return_geometric": 0.07669848827836034,
              "ann_volatility": 0.007210363397536823,
              "annualized_capital_charge_drag": 0.019990164110744616,
              "annualized_cost_drag": 0.03148305600333665,
              "annualized_fee_drag": 0.011492891892592038,
              "annualized_turnover_perp_units": 6.0572342335571765,
              "annualized_turnover_spot_units": 6.044023274251679,
              "annualized_turnover_units": 12.101257507808857,
              "avg_spot_notional_fraction": 0.9995082055372307,
              "invested_fraction": 1.0,
              "max_drawdown": -0.002815979665345081,
              "position_entries": 0,
              "position_exits": 0,
              "rebalance_days": 298,
              "sessions": 731,
              "sharpe_backtest_scale": 10.637256966072167,
              "sharpe_canonical": 10.253690109573403
            }
          }
        }
      },
      "funding_positive_lagged": {
        "realistic_rf": {
          "BTCUSDT": {
            "full": {
              "ann_return_arithmetic": 0.014485905769294349,
              "ann_return_geometric": 0.014419214201801589,
              "ann_volatility": 0.018407277866295136,
              "annualized_capital_charge_drag": 0.017556344588601353,
              "annualized_cost_drag": 0.10453935926395563,
              "annualized_fee_drag": 0.08698301467535428,
              "annualized_turnover_perp_units": 45.78848016114529,
              "annualized_turnover_spot_units": 45.775898802127166,
              "annualized_turnover_units": 91.56437896327245,
              "avg_spot_notional_fraction": 0.8778172294300676,
              "invested_fraction": 0.8782467532467533,
              "max_drawdown": -0.19287832561318896,
              "position_entries": 137,
              "position_exits": 136,
              "rebalance_days": 1051,
              "sessions": 2464,
              "sharpe_backtest_scale": 0.783343105185806,
              "sharpe_canonical": 0.7869662138267026
            },
            "post2022": {
              "ann_return_arithmetic": -0.02084042824109522,
              "ann_return_geometric": -0.020708112085839447,
              "ann_volatility": 0.012999529837688914,
              "annualized_capital_charge_drag": 0.017833605022330952,
              "annualized_cost_drag": 0.09344383066990714,
              "annualized_fee_drag": 0.07561022564757618,
              "annualized_turnover_perp_units": 39.79821738447909,
              "annualized_turnover_spot_units": 39.79289456536737,
              "annualized_turnover_units": 79.59111194984646,
              "avg_spot_notional_fraction": 0.8916802511165477,
              "invested_fraction": 0.8918918918918919,
              "max_drawdown": -0.1305340135624592,
              "position_entries": 67,
              "position_exits": 67,
              "rebalance_days": 505,
              "sessions": 1369,
              "sharpe_backtest_scale": -1.5929893114904363,
              "sharpe_canonical": -1.6031678453995748
            },
            "test_oos": {
              "ann_return_arithmetic": -0.06695525023534717,
              "ann_return_geometric": -0.0648482940045908,
              "ann_volatility": 0.013049234668569972,
              "annualized_capital_charge_drag": 0.01699092581077814,
              "annualized_cost_drag": 0.11058695179408896,
              "annualized_fee_drag": 0.09359602598331082,
              "annualized_turnover_perp_units": 49.262500434123915,
              "annualized_turnover_spot_units": 49.26022973285341,
              "annualized_turnover_units": 98.52273016697734,
              "avg_spot_notional_fraction": 0.8495462905389068,
              "invested_fraction": 0.8495297805642633,
              "max_drawdown": -0.12427635426886252,
              "position_entries": 40,
              "position_exits": 40,
              "rebalance_days": 232,
              "sessions": 638,
              "sharpe_backtest_scale": -4.969509373663317,
              "sharpe_canonical": -5.130971427513197
            },
            "train": {
              "ann_return_arithmetic": 0.05865188865534304,
              "ann_return_geometric": 0.060114068682538546,
              "ann_volatility": 0.023278482938901432,
              "annualized_capital_charge_drag": 0.017209705744970466,
              "annualized_cost_drag": 0.1184113032322227,
              "annualized_fee_drag": 0.10120159748725223,
              "annualized_turnover_perp_units": 53.2776762718814,
              "annualized_turnover_spot_units": 53.256020080779386,
              "annualized_turnover_units": 106.53369635266078,
              "avg_spot_notional_fraction": 0.8604852872485231,
              "invested_fraction": 0.8611872146118722,
              "max_drawdown": -0.12028846906802448,
              "position_entries": 70,
              "position_exits": 69,
              "rebalance_days": 546,
              "sessions": 1095,
              "sharpe_backtest_scale": 2.582387728629857,
              "sharpe_canonical": 2.5195752149865385
            },
            "val": {
              "ann_return_arithmetic": 0.019407528574681452,
              "ann_return_geometric": 0.019515789413935947,
              "ann_volatility": 0.012591796361755735,
              "annualized_capital_charge_drag": 0.018569076071538473,
              "annualized_cost_drag": 0.07848170853963629,
              "annualized_fee_drag": 0.05991263246809781,
              "annualized_turnover_perp_units": 31.538008648947752,
              "annualized_turnover_spot_units": 31.530022011528654,
              "annualized_turnover_units": 63.0680306604764,
              "avg_spot_notional_fraction": 0.9284538035769236,
              "invested_fraction": 0.9288645690834473,
              "max_drawdown": -0.044489445734977706,
              "position_entries": 27,
              "position_exits": 27,
              "rebalance_days": 273,
              "sessions": 731,
              "sharpe_backtest_scale": 1.549881276130705,
              "sharpe_canonical": 1.5412835482018046
            }
          },
          "ETHUSDT": {
            "full": {
              "ann_return_arithmetic": 0.02958748099623222,
              "ann_return_geometric": 0.029782727421494792,
              "ann_volatility": 0.021842369327265274,
              "annualized_capital_charge_drag": 0.017600672683049066,
              "annualized_cost_drag": 0.11000474431816548,
              "annualized_fee_drag": 0.09240407163511641,
              "annualized_turnover_perp_units": 48.64753451391881,
              "annualized_turnover_spot_units": 48.62566456281106,
              "annualized_turnover_units": 97.27319907672985,
              "avg_spot_notional_fraction": 0.8800336341524533,
              "invested_fraction": 0.880275974025974,
              "max_drawdown": -0.2609213597371439,
              "position_entries": 138,
              "position_exits": 137,
              "rebalance_days": 1301,
              "sessions": 2464,
              "sharpe_backtest_scale": 1.363530072001748,
              "sharpe_canonical": 1.3545911871061955
            },
            "post2022": {
              "ann_return_arithmetic": -0.028262503028403982,
              "ann_return_geometric": -0.027955873977727586,
              "ann_volatility": 0.01345105007515842,
              "annualized_capital_charge_drag": 0.01773337708029581,
              "annualized_cost_drag": 0.1029321726294254,
              "annualized_fee_drag": 0.0851987955491296,
              "annualized_turnover_perp_units": 44.84738450281828,
              "annualized_turnover_spot_units": 44.83802199763066,
              "annualized_turnover_units": 89.68540650044895,
              "avg_spot_notional_fraction": 0.8866688540147905,
              "invested_fraction": 0.8867786705624543,
              "max_drawdown": -0.17783805969290567,
              "position_entries": 73,
              "position_exits": 73,
              "rebalance_days": 634,
              "sessions": 1369,
              "sharpe_backtest_scale": -2.0783413801541686,
              "sharpe_canonical": -2.1011372993547583
            },
            "test_oos": {
              "ann_return_arithmetic": -0.10794366934352959,
              "ann_return_geometric": -0.10243109820754126,
              "ann_volatility": 0.014544810276252007,
              "annualized_capital_charge_drag": 0.01621542949751794,
              "annualized_cost_drag": 0.1473892220574729,
              "annualized_fee_drag": 0.13117379255995495,
              "annualized_turnover_perp_units": 69.04262289038259,
              "annualized_turnover_spot_units": 69.0366304472393,
              "annualized_turnover_units": 138.07925333762188,
              "avg_spot_notional_fraction": 0.810771474875897,
              "invested_fraction": 0.8103448275862069,
              "max_drawdown": -0.17783805969290412,
              "position_entries": 55,
              "position_exits": 55,
              "rebalance_days": 323,
              "sessions": 638,
              "sharpe_backtest_scale": -7.042449936578775,
              "sharpe_canonical": -7.421455989685494
            },
            "train": {
              "ann_return_arithmetic": 0.10191316878593722,
              "ann_return_geometric": 0.10681708187070194,
              "ann_volatility": 0.028671244560507823,
              "annualized_capital_charge_drag": 0.017434761888683047,
              "annualized_cost_drag": 0.11884707367148528,
              "annualized_fee_drag": 0.10141231178280223,
              "annualized_turnover_perp_units": 53.398589641952235,
              "annualized_turnover_spot_units": 53.36108252786306,
              "annualized_turnover_units": 106.75967216981529,
              "avg_spot_notional_fraction": 0.8717380944341523,
              "invested_fraction": 0.8721461187214612,
              "max_drawdown": -0.17750152886285042,
              "position_entries": 65,
              "position_exits": 64,
              "rebalance_days": 667,
              "sessions": 1095,
              "sharpe_backtest_scale": 3.725582321523402,
              "sharpe_canonical": 3.554542899972813
            },
            "val": {
              "ann_return_arithmetic": 0.0412813876816509,
              "ann_return_geometric": 0.04207729815778816,
              "ann_volatility": 0.01122443152209227,
              "annualized_capital_charge_drag": 0.019058206844744893,
              "annualized_cost_drag": 0.06413108161014454,
              "annualized_fee_drag": 0.045072874765399645,
              "annualized_turnover_perp_units": 23.730336498350386,
              "annualized_turnover_spot_units": 23.71803268046198,
              "annualized_turnover_units": 47.448369178812364,
              "avg_spot_notional_fraction": 0.9529103422372446,
              "invested_fraction": 0.9534883720930233,
              "max_drawdown": -0.030409764986512378,
              "position_entries": 18,
              "position_exits": 18,
              "rebalance_days": 311,
              "sessions": 731,
              "sharpe_backtest_scale": 3.7487242070986246,
              "sharpe_canonical": 3.6778154510898484
            }
          }
        }
      },
      "funding_positive_sameday": {
        "realistic_rf": {
          "BTCUSDT": {
            "full": {
              "ann_return_arithmetic": 0.021991546537334296,
              "ann_return_geometric": 0.02207436534158025,
              "ann_volatility": 0.017705383580881553,
              "annualized_capital_charge_drag": 0.017564997151026305,
              "annualized_cost_drag": 0.10430184648620151,
              "annualized_fee_drag": 0.08673684933517521,
              "annualized_turnover_perp_units": 45.65833809148404,
              "annualized_turnover_spot_units": 45.646677225946995,
              "annualized_turnover_units": 91.30501531743103,
              "avg_spot_notional_fraction": 0.8782498575513152,
              "invested_fraction": 0.8786525974025974,
              "max_drawdown": -0.1736046434685795,
              "position_entries": 137,
              "position_exits": 136,
              "rebalance_days": 1041,
              "sessions": 2464,
              "sharpe_backtest_scale": 1.2467600738916702,
              "sharpe_canonical": 1.2420824681302576
            },
            "post2022": {
              "ann_return_arithmetic": -0.017602410363423377,
              "ann_return_geometric": -0.017529929535975985,
              "ann_volatility": 0.012849234464363288,
              "annualized_capital_charge_drag": 0.01783258858709572,
              "annualized_cost_drag": 0.0933552254054289,
              "annualized_fee_drag": 0.07552263681833318,
              "annualized_turnover_perp_units": 39.7519842521284,
              "annualized_turnover_spot_units": 39.746873201536076,
              "annualized_turnover_units": 79.49885745366448,
              "avg_spot_notional_fraction": 0.891629429354786,
              "invested_fraction": 0.8918918918918919,
              "max_drawdown": -0.123471673190514,
              "position_entries": 67,
              "position_exits": 67,
              "rebalance_days": 501,
              "sessions": 1369,
              "sharpe_backtest_scale": -1.3642781275876297,
              "sharpe_canonical": -1.3699189949597999
            },
            "test_oos": {
              "ann_return_arithmetic": -0.06324780103935086,
              "ann_return_geometric": -0.06137260349814333,
              "ann_volatility": 0.012917472388556872,
              "annualized_capital_charge_drag": 0.01698970594405159,
              "annualized_cost_drag": 0.1103118461274684,
              "annualized_fee_drag": 0.09332214018341681,
              "annualized_turnover_perp_units": 49.11822164968358,
              "annualized_turnover_spot_units": 49.11615419053192,
              "annualized_turnover_units": 98.2343758402155,
              "avg_spot_notional_fraction": 0.8494852972025796,
              "invested_fraction": 0.8495297805642633,
              "max_drawdown": -0.11877053064192578,
              "position_entries": 40,
              "position_exits": 40,
              "rebalance_days": 230,
              "sessions": 638,
              "sharpe_backtest_scale": -4.7511309993208215,
              "sharpe_canonical": -4.896298527828078
            },
            "train": {
              "ann_return_arithmetic": 0.07149303237946879,
              "ann_return_geometric": 0.07384196749111505,
              "ann_volatility": 0.02207290148493341,
              "annualized_capital_charge_drag": 0.017230446762004362,
              "annualized_cost_drag": 0.11798762206572452,
              "annualized_fee_drag": 0.10075717530372016,
              "annualized_turnover_perp_units": 53.04262887329031,
              "annualized_turnover_spot_units": 53.022779243680795,
              "annualized_turnover_units": 106.0654081169711,
              "avg_spot_notional_fraction": 0.861522338100218,
              "invested_fraction": 0.8621004566210045,
              "max_drawdown": -0.10996812617654894,
              "position_entries": 70,
              "position_exits": 69,
              "rebalance_days": 540,
              "sessions": 1095,
              "sharpe_backtest_scale": 3.345367510543112,
              "sharpe_canonical": 3.2389503676382887
            },
            "val": {
              "ann_return_arithmetic": 0.02223583758629172,
              "ann_return_geometric": 0.022405309253184846,
              "ann_volatility": 0.012427862160522716,
              "annualized_capital_charge_drag": 0.018568237186633554,
              "annualized_cost_drag": 0.07855587653995529,
              "annualized_fee_drag": 0.059987639353321735,
              "annualized_turnover_perp_units": 31.577347508434556,
              "annualized_turnover_spot_units": 31.5695800811813,
              "annualized_turnover_units": 63.14692758961585,
              "avg_spot_notional_fraction": 0.9284118593316776,
              "invested_fraction": 0.9288645690834473,
              "max_drawdown": -0.04109467096876884,
              "position_entries": 27,
              "position_exits": 27,
              "rebalance_days": 271,
              "sessions": 731,
              "sharpe_backtest_scale": 1.8028289148841412,
              "sharpe_canonical": 1.7891924853273784
            }
          },
          "ETHUSDT": {
            "full": {
              "ann_return_arithmetic": 0.037710498720807395,
              "ann_return_geometric": 0.038208321968052905,
              "ann_volatility": 0.020612464325299694,
              "annualized_capital_charge_drag": 0.017608218511388146,
              "annualized_cost_drag": 0.10994461539101441,
              "annualized_fee_drag": 0.09233639687962626,
              "annualized_turnover_perp_units": 48.61046362070149,
              "annualized_turnover_spot_units": 48.59089362094603,
              "annualized_turnover_units": 97.20135724164751,
              "avg_spot_notional_fraction": 0.8804109255694073,
              "invested_fraction": 0.8806818181818182,
              "max_drawdown": -0.23684686326119042,
              "position_entries": 138,
              "position_exits": 137,
              "rebalance_days": 1299,
              "sessions": 2464,
              "sharpe_backtest_scale": 1.8536513327596689,
              "sharpe_canonical": 1.8294997689588048
            },
            "post2022": {
              "ann_return_arithmetic": -0.024970903515997022,
              "ann_return_geometric": -0.024748719363592908,
              "ann_volatility": 0.013292561809172064,
              "annualized_capital_charge_drag": 0.017732135965737337,
              "annualized_cost_drag": 0.10295466585334305,
              "annualized_fee_drag": 0.08522252988760572,
              "annualized_turnover_perp_units": 44.85962218493003,
              "annualized_turnover_spot_units": 44.8506619651289,
              "annualized_turnover_units": 89.71028415005895,
              "avg_spot_notional_fraction": 0.8866067982868668,
              "invested_fraction": 0.8867786705624543,
              "max_drawdown": -0.17051455041721242,
              "position_entries": 73,
              "position_exits": 73,
              "rebalance_days": 636,
              "sessions": 1369,
              "sharpe_backtest_scale": -1.8618472284639613,
              "sharpe_canonical": -1.8785621518620081
            },
            "test_oos": {
              "ann_return_arithmetic": -0.1028739340227951,
              "ann_return_geometric": -0.0978653538551898,
              "ann_volatility": 0.01435837018209651,
              "annualized_capital_charge_drag": 0.016211652374566586,
              "annualized_cost_drag": 0.1473304966397373,
              "annualized_fee_drag": 0.1311188442651707,
              "annualized_turnover_perp_units": 69.01287802965683,
              "annualized_turnover_spot_units": 69.00819137034246,
              "annualized_turnover_units": 138.0210693999993,
              "avg_spot_notional_fraction": 0.8105826187283293,
              "invested_fraction": 0.8103448275862069,
              "max_drawdown": -0.17051455041721342,
              "position_entries": 55,
              "position_exits": 55,
              "rebalance_days": 320,
              "sessions": 638,
              "sharpe_backtest_scale": -6.815909648103262,
              "sharpe_canonical": -7.1647361586392915
            },
            "train": {
              "ann_return_arithmetic": 0.11607656233924142,
              "ann_return_geometric": 0.12266628132464596,
              "ann_volatility": 0.02655732571313686,
              "annualized_capital_charge_drag": 0.017453293401795404,
              "annualized_cost_drag": 0.11868364819199351,
              "annualized_fee_drag": 0.1012303547901981,
              "annualized_turnover_perp_units": 53.29987177190799,
              "annualized_turnover_spot_units": 53.26703712488543,
              "annualized_turnover_units": 106.56690889679341,
              "avg_spot_notional_fraction": 0.8726646700897702,
              "invested_fraction": 0.8730593607305936,
              "max_drawdown": -0.16114816629875994,
              "position_entries": 65,
              "position_exits": 64,
              "rebalance_days": 663,
              "sessions": 1095,
              "sharpe_backtest_scale": 4.61892445985131,
              "sharpe_canonical": 4.370792586311616
            },
            "val": {
              "ann_return_arithmetic": 0.04302107112605108,
              "ann_return_geometric": 0.043892586614066254,
              "ann_volatility": 0.011135693117167292,
              "annualized_capital_charge_drag": 0.019059179100028637,
              "annualized_cost_drag": 0.06422446059791274,
              "annualized_fee_drag": 0.04516528149788411,
              "annualized_turnover_perp_units": 23.77921557899886,
              "annualized_turnover_spot_units": 23.766525493820765,
              "annualized_turnover_units": 47.545741072819624,
              "avg_spot_notional_fraction": 0.9529589550014319,
              "invested_fraction": 0.9534883720930233,
              "max_drawdown": -0.028547998824633325,
              "position_entries": 18,
              "position_exits": 18,
              "rebalance_days": 316,
              "sessions": 731,
              "sharpe_backtest_scale": 3.941612448568598,
              "sharpe_canonical": 3.863349202729719
            }
          }
        }
      }
    },
    "threshold_rebalance": {
      "convention": "threshold_rebalanced",
      "pre_registered_threshold": 0.02,
      "sensitivity_grid": [
        0.01,
        0.02,
        0.05,
        0.1
      ]
    },
    "threshold_sensitivity": {
      "0.0100": {
        "always_on": {
          "rebalances": {
            "BTCUSDT": 1523,
            "ETHUSDT": 1730
          },
          "samples": {
            "full": {
              "ann_return_arithmetic": 0.08931905982818414,
              "ann_return_geometric": 0.09329780287057354,
              "ann_volatility": 0.0148051835274728,
              "annualized_capital_charge_drag": 0.019996414122780398,
              "annualized_cost_drag": 0.036543879535529344,
              "annualized_fee_drag": 0.016547465412748943,
              "annualized_turnover_perp_units": 8.720412525505944,
              "annualized_turnover_spot_units": 8.702647204078987,
              "annualized_turnover_units": 17.42305972958493,
              "avg_spot_notional_fraction": 0.9998207061390199,
              "invested_fraction": 1.0,
              "max_drawdown": -0.02070384389201685,
              "position_entries": 2,
              "position_exits": 0,
              "rebalance_days": 1973,
              "sessions": 2464,
              "sharpe_backtest_scale": 6.301698502922861,
              "sharpe_canonical": 6.032958636577647
            }
          }
        },
        "funding_positive_lagged": {
          "rebalances": {
            "BTCUSDT": 1339,
            "ETHUSDT": 1514
          },
          "samples": {
            "full": {
              "ann_return_arithmetic": 0.02058393924842673,
              "ann_return_geometric": 0.020629689189469058,
              "ann_volatility": 0.01809197419581653,
              "annualized_capital_charge_drag": 0.01758203962739495,
              "annualized_cost_drag": 0.10881064526806973,
              "annualized_fee_drag": 0.09122860564067478,
              "annualized_turnover_perp_units": 48.025894766455785,
              "annualized_turnover_spot_units": 48.008732753463114,
              "annualized_turnover_units": 96.0346275199189,
              "avg_spot_notional_fraction": 0.8791019813697474,
              "invested_fraction": 0.9460227272727273,
              "max_drawdown": -0.22941346971444587,
              "position_entries": 275,
              "position_exits": 273,
              "rebalance_days": 2019,
              "sessions": 2464,
              "sharpe_backtest_scale": 1.140267444900476,
              "sharpe_canonical": 1.1377387025671541
            }
          }
        },
        "funding_positive_sameday": {
          "rebalances": {
            "BTCUSDT": 1319,
            "ETHUSDT": 1515
          },
          "samples": {
            "full": {
              "ann_return_arithmetic": 0.028435412957784213,
              "ann_return_geometric": 0.028693468717587267,
              "ann_volatility": 0.017029487695791,
              "annualized_capital_charge_drag": 0.017589363937481575,
              "annualized_cost_drag": 0.10862266622000723,
              "annualized_fee_drag": 0.09103330228252565,
              "annualized_turnover_perp_units": 47.921912794149414,
              "annualized_turnover_spot_units": 47.90663610551756,
              "annualized_turnover_units": 95.828548899667,
              "avg_spot_notional_fraction": 0.8794681968740787,
              "invested_fraction": 0.9464285714285714,
              "max_drawdown": -0.20765661991560835,
              "position_entries": 275,
              "position_exits": 273,
              "rebalance_days": 2009,
              "sessions": 2464,
              "sharpe_backtest_scale": 1.684928474077299,
              "sharpe_canonical": 1.6697750082530254
            }
          }
        }
      },
      "0.0200": {
        "always_on": {
          "rebalances": {
            "BTCUSDT": 952,
            "ETHUSDT": 1259
          },
          "samples": {
            "full": {
              "ann_return_arithmetic": 0.09094897420666076,
              "ann_return_geometric": 0.09508081836800408,
              "ann_volatility": 0.014803898604688557,
              "annualized_capital_charge_drag": 0.019993434396718808,
              "annualized_cost_drag": 0.034846121222069794,
              "annualized_fee_drag": 0.014852686825350988,
              "annualized_turnover_perp_units": 7.8283682642652925,
              "annualized_turnover_spot_units": 7.810690866971069,
              "annualized_turnover_units": 15.639059131236364,
              "avg_spot_notional_fraction": 0.9996717198359404,
              "invested_fraction": 1.0,
              "max_drawdown": -0.02021845815949086,
              "position_entries": 2,
              "position_exits": 0,
              "rebalance_days": 1461,
              "sessions": 2464,
              "sharpe_backtest_scale": 6.422687759958782,
              "sharpe_canonical": 6.143582622070663
            }
          }
        },
        "funding_positive_lagged": {
          "rebalances": {
            "BTCUSDT": 831,
            "ETHUSDT": 1086
          },
          "samples": {
            "full": {
              "ann_return_arithmetic": 0.022036140772611724,
              "ann_return_geometric": 0.022112784738469005,
              "ann_volatility": 0.01809496589316271,
              "annualized_capital_charge_drag": 0.017578565398642627,
              "annualized_cost_drag": 0.10727210855387799,
              "annualized_fee_drag": 0.08969354315523537,
              "annualized_turnover_perp_units": 47.21800733753206,
              "annualized_turnover_spot_units": 47.20078168246911,
              "annualized_turnover_units": 94.41878902000117,
              "avg_spot_notional_fraction": 0.8789282699321314,
              "invested_fraction": 0.9460227272727273,
              "max_drawdown": -0.2242512336305026,
              "position_entries": 275,
              "position_exits": 273,
              "rebalance_days": 1608,
              "sessions": 2464,
              "sharpe_backtest_scale": 1.2220406973424829,
              "sharpe_canonical": 1.2178050460398053
            }
          }
        },
        "funding_positive_sameday": {
          "rebalances": {
            "BTCUSDT": 816,
            "ETHUSDT": 1097
          },
          "samples": {
            "full": {
              "ann_return_arithmetic": 0.02985044916235852,
              "ann_return_geometric": 0.030149964936691642,
              "ann_volatility": 0.017032743021582683,
              "annualized_capital_charge_drag": 0.01758662691492275,
              "annualized_cost_drag": 0.10712325002232348,
              "annualized_fee_drag": 0.08953662310740074,
              "annualized_turnover_perp_units": 47.13440085609277,
              "annualized_turnover_spot_units": 47.118785423446504,
              "annualized_turnover_units": 94.25318627953926,
              "avg_spot_notional_fraction": 0.8793313457461375,
              "invested_fraction": 0.9464285714285714,
              "max_drawdown": -0.2025660299852129,
              "position_entries": 275,
              "position_exits": 273,
              "rebalance_days": 1602,
              "sessions": 2464,
              "sharpe_backtest_scale": 1.7701179955857813,
              "sharpe_canonical": 1.752533289825024
            }
          }
        }
      },
      "0.0500": {
        "always_on": {
          "rebalances": {
            "BTCUSDT": 361,
            "ETHUSDT": 536
          },
          "samples": {
            "full": {
              "ann_return_arithmetic": 0.09569168411744315,
              "ann_return_geometric": 0.1002847916505265,
              "ann_volatility": 0.01484580549894753,
              "annualized_capital_charge_drag": 0.019958103769336214,
              "annualized_cost_drag": 0.030200502904256098,
              "annualized_fee_drag": 0.010242399134919884,
              "annualized_turnover_perp_units": 5.39866966593175,
              "annualized_turnover_spot_units": 5.386108640639716,
              "annualized_turnover_units": 10.784778306571466,
              "avg_spot_notional_fraction": 0.9979051884668108,
              "invested_fraction": 1.0,
              "max_drawdown": -0.019882671820922404,
              "position_entries": 2,
              "position_exits": 0,
              "rebalance_days": 683,
              "sessions": 2464,
              "sharpe_backtest_scale": 6.755092652778998,
              "sharpe_canonical": 6.445705093214852
            }
          }
        },
        "funding_positive_lagged": {
          "rebalances": {
            "BTCUSDT": 304,
            "ETHUSDT": 466
          },
          "samples": {
            "full": {
              "ann_return_arithmetic": 0.026228936412675177,
              "ann_return_geometric": 0.026406113614960702,
              "ann_volatility": 0.018143308982323796,
              "annualized_capital_charge_drag": 0.01755861879915983,
              "annualized_cost_drag": 0.10319183652934652,
              "annualized_fee_drag": 0.08563321773018669,
              "annualized_turnover_perp_units": 45.078112500368334,
              "annualized_turnover_spot_units": 45.065449149940704,
              "annualized_turnover_units": 90.14356165030904,
              "avg_spot_notional_fraction": 0.8779309399579915,
              "invested_fraction": 0.9460227272727273,
              "max_drawdown": -0.21115376601145208,
              "position_entries": 275,
              "position_exits": 273,
              "rebalance_days": 1001,
              "sessions": 2464,
              "sharpe_backtest_scale": 1.455418834606575,
              "sharpe_canonical": 1.4456534052431584
            }
          }
        },
        "funding_positive_sameday": {
          "rebalances": {
            "BTCUSDT": 300,
            "ETHUSDT": 465
          },
          "samples": {
            "full": {
              "ann_return_arithmetic": 0.03401656293553276,
              "ann_return_geometric": 0.03444932644757248,
              "ann_volatility": 0.017086084505829168,
              "annualized_capital_charge_drag": 0.01755675396911238,
              "annualized_cost_drag": 0.1030383489421692,
              "annualized_fee_drag": 0.08548159497305682,
              "annualized_turnover_perp_units": 44.99719332110821,
              "annualized_turnover_spot_units": 44.98629970690091,
              "annualized_turnover_units": 89.98349302800914,
              "avg_spot_notional_fraction": 0.877837698455619,
              "invested_fraction": 0.9464285714285714,
              "max_drawdown": -0.1889485070055127,
              "position_entries": 275,
              "position_exits": 273,
              "rebalance_days": 1010,
              "sessions": 2464,
              "sharpe_backtest_scale": 2.016221237570234,
              "sharpe_canonical": 1.9908928183006185
            }
          }
        }
      },
      "0.1000": {
        "always_on": {
          "rebalances": {
            "BTCUSDT": 143,
            "ETHUSDT": 229
          },
          "samples": {
            "full": {
              "ann_return_arithmetic": 0.09965430199366655,
              "ann_return_geometric": 0.10465002711165083,
              "ann_volatility": 0.014983182465689172,
              "annualized_capital_charge_drag": 0.019930116758920213,
              "annualized_cost_drag": 0.02712348624552935,
              "annualized_fee_drag": 0.0071933694866091365,
              "annualized_turnover_perp_units": 3.791339397467751,
              "annualized_turnover_spot_units": 3.782859923651427,
              "annualized_turnover_units": 7.574199321119178,
              "avg_spot_notional_fraction": 0.9965058379460106,
              "invested_fraction": 1.0,
              "max_drawdown": -0.01868317888429505,
              "position_entries": 2,
              "position_exits": 0,
              "rebalance_days": 314,
              "sessions": 2464,
              "sharpe_backtest_scale": 6.984499277860013,
              "sharpe_canonical": 6.651077114082439
            }
          }
        },
        "funding_positive_lagged": {
          "rebalances": {
            "BTCUSDT": 113,
            "ETHUSDT": 179
          },
          "samples": {
            "full": {
              "ann_return_arithmetic": 0.030291754194544683,
              "ann_return_geometric": 0.03058155779579641,
              "ann_volatility": 0.01829393528939264,
              "annualized_capital_charge_drag": 0.017562640433305406,
              "annualized_cost_drag": 0.10014428545175866,
              "annualized_fee_drag": 0.08258164501845325,
              "annualized_turnover_perp_units": 43.4693068174439,
              "annualized_turnover_spot_units": 43.46094187186877,
              "annualized_turnover_units": 86.93024868931268,
              "avg_spot_notional_fraction": 0.8781320216652704,
              "invested_fraction": 0.9460227272727273,
              "max_drawdown": -0.2011619924170419,
              "position_entries": 275,
              "position_exits": 273,
              "rebalance_days": 699,
              "sessions": 2464,
              "sharpe_backtest_scale": 1.6716773789797155,
              "sharpe_canonical": 1.6558358666606157
            }
          }
        },
        "funding_positive_sameday": {
          "rebalances": {
            "BTCUSDT": 118,
            "ETHUSDT": 172
          },
          "samples": {
            "full": {
              "ann_return_arithmetic": 0.03796416234181325,
              "ann_return_geometric": 0.038538091694774845,
              "ann_volatility": 0.017226654397067078,
              "annualized_capital_charge_drag": 0.017557491607944318,
              "annualized_cost_drag": 0.10004681766848496,
              "annualized_fee_drag": 0.08248932606054064,
              "annualized_turnover_perp_units": 43.419416425904664,
              "annualized_turnover_spot_units": 43.413112135339496,
              "annualized_turnover_units": 86.83252856124417,
              "avg_spot_notional_fraction": 0.877874580397216,
              "invested_fraction": 0.9464285714285714,
              "max_drawdown": -0.1788219017689171,
              "position_entries": 275,
              "position_exits": 273,
              "rebalance_days": 697,
              "sessions": 2464,
              "sharpe_backtest_scale": 2.237119919311561,
              "sharpe_canonical": 2.203803563173406
            }
          }
        }
      }
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
    "cost_models": {
      "capital_charge_convention": "The charge is applied to the spot leg's notional (the cash the delta-neutral book ties up; the short perp leg is self-financing because its own proceeds are posted as its margin). The repository's backtest-baseline Sharpe/Sortino already subtract the 2% risk-free rate from the ratio's numerator while the return series does not pay it, so the backtest-scale metrics of a capital-charge row are computed with a zero risk-free rate (no double counting). The canonical gate convention (arithmetic_annualized_rf0) is unaffected either way.",
      "capital_charge_grid": {
        "none": 0.0,
        "repo_rf": 0.02,
        "usdt_5pct": 0.05
      },
      "headline": "realistic_rf",
      "headline_turnover_convention": "drift",
      "models": {
        "flat_3bp": {
          "capital_rate_annual": 0.0,
          "flat_bps_per_unit": 3.0,
          "kind": "flat",
          "label": "Repository flat model (3 bp per unit of weight change)",
          "note": "The repository-wide convention (1 bp commission + 2 bp slippage per unit of weight change) and the convention the cost screen uses. No capital charge.",
          "perp_bps_per_unit": 0.0,
          "source": "src/backtest/engine.py:get_cost_params (config/settings.yaml)",
          "spot_bps_per_unit": 0.0
        },
        "flat_3bp_capital_rf": {
          "capital_rate_annual": 0.02,
          "flat_bps_per_unit": 3.0,
          "kind": "flat",
          "label": "Flat model + capital charge at the repository risk-free rate",
          "note": "Isolates the capital charge: the same flat trading cost, plus the cost of the capital the spot leg ties up.",
          "perp_bps_per_unit": 0.0,
          "source": "src/backtest/engine.py:get_cost_params + get_risk_free_rate",
          "spot_bps_per_unit": 0.0
        },
        "realistic_no_capital_charge": {
          "capital_rate_annual": 0.0,
          "flat_bps_per_unit": 0.0,
          "kind": "venue",
          "label": "Venue taker + slippage, no capital charge",
          "note": "The capital-charge sensitivity row 'none' (0%): the book is charged only what it trades.",
          "perp_bps_per_unit": 7.0,
          "source": "Binance VIP 0 published spot taker 10 bp and USD\u24c8-M perp taker 5 bp (accessed 2026-10-20) + the repository's 2 bp/unit slippage assumption",
          "spot_bps_per_unit": 12.0
        },
        "realistic_rf": {
          "capital_rate_annual": 0.02,
          "flat_bps_per_unit": 0.0,
          "kind": "venue",
          "label": "HEADLINE: venue taker + slippage + capital charge at the repository rf",
          "note": "The realistic model of this evaluation: the conservative end of both the fee schedule (taker) and the capital charge (the repository's risk-free rate).",
          "perp_bps_per_unit": 7.0,
          "source": "Binance VIP 0 published spot taker 10 bp and USD\u24c8-M perp taker 5 bp (accessed 2026-10-20) + the repository's 2 bp/unit slippage assumption + get_risk_free_rate()",
          "spot_bps_per_unit": 12.0
        },
        "realistic_usdt_5pct": {
          "capital_rate_annual": 0.05,
          "flat_bps_per_unit": 0.0,
          "kind": "venue",
          "label": "Venue taker + slippage + capital charge at a 5% USDT-equivalent yield",
          "note": "The capital-charge sensitivity row 'usdt_5pct': the cash the spot leg ties up could have earned a stablecoin lending yield instead.",
          "perp_bps_per_unit": 7.0,
          "source": "Binance VIP 0 published spot taker 10 bp and USD\u24c8-M perp taker 5 bp (accessed 2026-10-20) + the repository's 2 bp/unit slippage assumption + 5% USDT-equivalent yield assumption",
          "spot_bps_per_unit": 12.0
        },
        "venue_maker_slippage": {
          "capital_rate_annual": 0.0,
          "flat_bps_per_unit": 0.0,
          "kind": "venue",
          "label": "Binance VIP 0 venue fees, maker + repository slippage (spot 12 bp, perp 4 bp)",
          "note": "The maker alternative: at VIP 0 the spot fee is the same for maker and taker, so only the perp leg gets cheaper.",
          "perp_bps_per_unit": 4.0,
          "source": "Binance published VIP 0 fee schedule, maker (spot 10 bp, perp 2 bp, accessed 2026-10-20) + the repository's 2 bp/unit slippage assumption",
          "spot_bps_per_unit": 12.0
        },
        "venue_taker": {
          "capital_rate_annual": 0.0,
          "flat_bps_per_unit": 0.0,
          "kind": "venue",
          "label": "Binance VIP 0 venue fees, taker (spot 10 bp, perp 5 bp)",
          "note": "The published fee schedule alone: no slippage, no capital charge.",
          "perp_bps_per_unit": 5.0,
          "source": "Binance published VIP 0 fee schedule (accessed 2026-10-20)",
          "spot_bps_per_unit": 10.0
        },
        "venue_taker_slippage": {
          "capital_rate_annual": 0.0,
          "flat_bps_per_unit": 0.0,
          "kind": "venue",
          "label": "Binance VIP 0 venue fees, taker + repository slippage (spot 12 bp, perp 7 bp)",
          "note": "The published fee schedule plus the repository's slippage assumption, which a fee schedule does not model.",
          "perp_bps_per_unit": 7.0,
          "source": "Binance VIP 0 published spot taker 10 bp and USD\u24c8-M perp taker 5 bp (accessed 2026-10-20) + the repository's 2 bp/unit slippage assumption",
          "spot_bps_per_unit": 12.0
        }
      },
      "venue_fee_schedule": {
        "accessed": "2026-10-20",
        "note": "Published schedule used as a documented assumption; no live fees are implied (the account-specific table is only visible after login). The BNB fee discount is not claimed.",
        "perp_maker_bps": 2.0,
        "perp_taker_bps": 5.0,
        "repository_slippage_bps_per_unit": 2.0,
        "sources": [
          "Binance, 'VIP Program: Updates to Spot and Margin Trading Fees for VIP 3 - VIP 9 Users' (2024-10-07): Normal User maker 0.1000% / taker 0.1000% on spot.",
          "Binance futures fee explainer (support FAQ 360033544231): a Regular User's maker fee is 0.02% and taker fee 0.05% on USD\u24c8-M futures.",
          "config/settings.yaml: default_slippage_bps (the repository's own slippage assumption)."
        ],
        "spot_maker_bps": 10.0,
        "spot_taker_bps": 10.0,
        "tier": "VIP 0 (standard, published schedule)",
        "venue": "Binance"
      }
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
    "generated_at": "2026-10-20T07:22:32.620606+00:00",
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
    "trial_count": "6 candidate configurations (3 rules x 2 symbols); the BTC/ETH portfolio is an equal-weight combination of the two symbol books, not an additional configuration. The robustness rows and the cost-model rows (capital charge, venue fee schedule, turnover convention) are sensitivity analyses of the same configurations, not new trials."
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
      "cost_model": "flat_3bp",
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.0046986386168663815,
          "annualized_fee_drag": 0.0046986386168663815,
          "annualized_turnover_perp_units": 7.837953879120338,
          "annualized_turnover_spot_units": 7.8241748437676,
          "annualized_turnover_units": 15.66212872288794,
          "avg_gross_exposure": 2.0,
          "avg_spot_notional_fraction": 1.0,
          "downside_deviation_annualized": 0.010459428920534206,
          "end": "2026-09-30",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.0037048933173954943,
          "annualized_fee_drag": 0.0037048933173954943,
          "annualized_turnover_perp_units": 6.178120730133934,
          "annualized_turnover_spot_units": 6.171523661184383,
          "annualized_turnover_units": 12.349644391318316,
          "avg_gross_exposure": 2.0,
          "avg_spot_notional_fraction": 1.0,
          "downside_deviation_annualized": 0.002353162093355494,
          "end": "2026-09-30",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.0034857383900040637,
          "annualized_fee_drag": 0.0034857383900040637,
          "annualized_turnover_perp_units": 5.811416918002974,
          "annualized_turnover_spot_units": 5.8077110486772385,
          "annualized_turnover_units": 11.619127966680214,
          "avg_gross_exposure": 2.0,
          "avg_spot_notional_fraction": 1.0,
          "downside_deviation_annualized": 0.0018935214198159596,
          "end": "2026-09-30",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.005941047123693452,
          "annualized_fee_drag": 0.005941047123693452,
          "annualized_turnover_perp_units": 9.913124272693297,
          "annualized_turnover_spot_units": 9.890366139618214,
          "annualized_turnover_units": 19.803490412311508,
          "avg_gross_exposure": 2.0,
          "avg_spot_notional_fraction": 1.0,
          "downside_deviation_annualized": 0.014435001055015034,
          "end": "2022-12-31",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.0038961667013568263,
          "annualized_fee_drag": 0.0038961667013568263,
          "annualized_turnover_perp_units": 6.498171389695564,
          "annualized_turnover_spot_units": 6.489050948160524,
          "annualized_turnover_units": 12.987222337856089,
          "avg_gross_exposure": 2.0,
          "avg_spot_notional_fraction": 1.0,
          "downside_deviation_annualized": 0.0027963440013734193,
          "end": "2024-12-31",
          "engine_risk_free_rate_annual": 0.02,
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
      "cost_model": "flat_3bp",
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.028277232168090024,
          "annualized_fee_drag": 0.028277232168090024,
          "annualized_turnover_perp_units": 47.135878473350886,
          "annualized_turnover_spot_units": 47.121562086949204,
          "annualized_turnover_units": 94.25744056030008,
          "avg_gross_exposure": 1.7564935064935066,
          "avg_spot_notional_fraction": 0.8782467532467533,
          "downside_deviation_annualized": 0.010019484705020225,
          "end": "2026-09-30",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.02474117564099871,
          "annualized_fee_drag": 0.02474117564099871,
          "annualized_turnover_perp_units": 41.23891183929234,
          "annualized_turnover_spot_units": 41.231673630703376,
          "annualized_turnover_units": 82.47058546999571,
          "avg_gross_exposure": 1.7837837837837838,
          "avg_spot_notional_fraction": 0.8918918918918919,
          "downside_deviation_annualized": 0.005029948200981187,
          "end": "2026-09-30",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.030398613428460574,
          "annualized_fee_drag": 0.030398613428460574,
          "annualized_turnover_perp_units": 50.66681098167943,
          "annualized_turnover_spot_units": 50.66190044652249,
          "annualized_turnover_units": 101.32871142820193,
          "avg_gross_exposure": 1.6990595611285266,
          "avg_spot_notional_fraction": 0.8495297805642633,
          "downside_deviation_annualized": 0.00513516009148698,
          "end": "2026-09-30",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.03269811014579597,
          "annualized_fee_drag": 0.03269811014579597,
          "annualized_turnover_perp_units": 54.508433105338234,
          "annualized_turnover_spot_units": 54.48526738064833,
          "annualized_turnover_units": 108.99370048598657,
          "avg_gross_exposure": 1.7223744292237444,
          "avg_spot_notional_fraction": 0.8611872146118722,
          "downside_deviation_annualized": 0.013291062197839007,
          "end": "2022-12-31",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.01980349396056005,
          "annualized_fee_drag": 0.01980349396056005,
          "annualized_turnover_perp_units": 33.01045814183276,
          "annualized_turnover_spot_units": 33.001188393367414,
          "annualized_turnover_units": 66.01164653520017,
          "avg_gross_exposure": 1.8577291381668946,
          "avg_spot_notional_fraction": 0.9288645690834473,
          "downside_deviation_annualized": 0.004899294489306789,
          "end": "2024-12-31",
          "engine_risk_free_rate_annual": 0.02,
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
      "cost_model": "flat_3bp",
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.028213536755636138,
          "annualized_fee_drag": 0.028213536755636138,
          "annualized_turnover_perp_units": 47.02882576435699,
          "annualized_turnover_spot_units": 47.01629675443016,
          "annualized_turnover_units": 94.04512251878714,
          "avg_gross_exposure": 1.7573051948051948,
          "avg_spot_notional_fraction": 0.8786525974025974,
          "downside_deviation_annualized": 0.00589876757003913,
          "end": "2026-09-30",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.02471855024801723,
          "annualized_fee_drag": 0.02471855024801723,
          "annualized_turnover_perp_units": 41.20098931797935,
          "annualized_turnover_spot_units": 41.194178175411416,
          "annualized_turnover_units": 82.39516749339077,
          "avg_gross_exposure": 1.7837837837837838,
          "avg_spot_notional_fraction": 0.8918918918918919,
          "downside_deviation_annualized": 0.004878979506541928,
          "end": "2026-09-30",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.03034125553005664,
          "annualized_fee_drag": 0.03034125553005664,
          "annualized_turnover_perp_units": 50.57100214930303,
          "annualized_turnover_spot_units": 50.56651628421912,
          "annualized_turnover_units": 101.13751843352213,
          "avg_gross_exposure": 1.6990595611285266,
          "avg_spot_notional_fraction": 0.8495297805642633,
          "downside_deviation_annualized": 0.004914974144620865,
          "end": "2026-09-30",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.03258306783228482,
          "annualized_fee_drag": 0.03258306783228482,
          "annualized_turnover_perp_units": 54.31495187859533,
          "annualized_turnover_spot_units": 54.29527422902072,
          "annualized_turnover_units": 108.61022610761606,
          "avg_gross_exposure": 1.724200913242009,
          "avg_spot_notional_fraction": 0.8621004566210045,
          "downside_deviation_annualized": 0.006773625463460127,
          "end": "2022-12-31",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.019811182300081314,
          "annualized_fee_drag": 0.019811182300081314,
          "annualized_turnover_perp_units": 33.02305746246018,
          "annualized_turnover_spot_units": 33.01421687114423,
          "annualized_turnover_units": 66.03727433360439,
          "avg_gross_exposure": 1.8577291381668946,
          "avg_spot_notional_fraction": 0.9288645690834473,
          "downside_deviation_annualized": 0.00480785180014237,
          "end": "2024-12-31",
          "engine_risk_free_rate_annual": 0.02,
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
      "cost_model": "flat_3bp",
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.006381719140345409,
          "annualized_fee_drag": 0.006381719140345409,
          "annualized_turnover_perp_units": 10.647880386106714,
          "annualized_turnover_spot_units": 10.624516748377983,
          "annualized_turnover_units": 21.2723971344847,
          "avg_gross_exposure": 2.0,
          "avg_spot_notional_fraction": 1.0,
          "downside_deviation_annualized": 0.015346424876721856,
          "end": "2026-09-30",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.00495943904783338,
          "annualized_fee_drag": 0.00495943904783338,
          "annualized_turnover_perp_units": 8.269804993354063,
          "annualized_turnover_spot_units": 8.261658499423875,
          "annualized_turnover_units": 16.531463492777934,
          "avg_gross_exposure": 2.0,
          "avg_spot_notional_fraction": 1.0,
          "downside_deviation_annualized": 0.0038839564869855743,
          "end": "2026-09-30",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.0054545227521363435,
          "annualized_fee_drag": 0.0054545227521363435,
          "annualized_turnover_perp_units": 9.093666523546988,
          "annualized_turnover_spot_units": 9.08807598357416,
          "annualized_turnover_units": 18.181742507121147,
          "avg_gross_exposure": 2.0,
          "avg_spot_notional_fraction": 1.0,
          "downside_deviation_annualized": 0.0037773852885606305,
          "end": "2026-09-30",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.008159893977467752,
          "annualized_fee_drag": 0.008159893977467752,
          "annualized_turnover_perp_units": 13.621017566634913,
          "annualized_turnover_spot_units": 13.578629024924265,
          "annualized_turnover_units": 27.199646591559176,
          "avg_gross_exposure": 2.0,
          "avg_spot_notional_fraction": 1.0,
          "downside_deviation_annualized": 0.02104738135167717,
          "end": "2022-12-31",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.004527341368838455,
          "annualized_fee_drag": 0.004527341368838455,
          "annualized_turnover_perp_units": 7.550757583965434,
          "annualized_turnover_spot_units": 7.540380312162751,
          "annualized_turnover_units": 15.091137896128187,
          "avg_gross_exposure": 2.0,
          "avg_spot_notional_fraction": 1.0,
          "downside_deviation_annualized": 0.004052341340476993,
          "end": "2024-12-31",
          "engine_risk_free_rate_annual": 0.02,
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
      "cost_model": "flat_3bp",
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.02989859251979504,
          "annualized_fee_drag": 0.02989859251979504,
          "annualized_turnover_perp_units": 49.84235545280386,
          "annualized_turnover_spot_units": 49.81961961317965,
          "annualized_turnover_units": 99.66197506598347,
          "avg_gross_exposure": 1.760551948051948,
          "avg_spot_notional_fraction": 0.880275974025974,
          "downside_deviation_annualized": 0.013676816637986595,
          "end": "2026-09-30",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.027689890658833947,
          "annualized_fee_drag": 0.027689890658833947,
          "annualized_turnover_perp_units": 46.153790096700355,
          "annualized_turnover_spot_units": 46.14584543274615,
          "annualized_turnover_units": 92.2996355294465,
          "avg_gross_exposure": 1.7735573411249086,
          "avg_spot_notional_fraction": 0.8867786705624543,
          "downside_deviation_annualized": 0.005189824042132622,
          "end": "2026-09-30",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.042089327370280975,
          "annualized_fee_drag": 0.042089327370280975,
          "annualized_turnover_perp_units": 70.1513745766121,
          "annualized_turnover_spot_units": 70.1463833243245,
          "annualized_turnover_units": 140.2977579009366,
          "avg_gross_exposure": 1.6206896551724137,
          "avg_spot_notional_fraction": 0.8103448275862069,
          "downside_deviation_annualized": 0.005177750595056256,
          "end": "2026-09-30",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.03265997411582769,
          "annualized_fee_drag": 0.03265997411582769,
          "annualized_turnover_perp_units": 54.45390428614238,
          "annualized_turnover_spot_units": 54.41267609994991,
          "annualized_turnover_units": 108.8665803860923,
          "avg_gross_exposure": 1.7442922374429224,
          "avg_spot_notional_fraction": 0.8721461187214612,
          "downside_deviation_annualized": 0.01875506571929408,
          "end": "2022-12-31",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.01512239322804982,
          "annualized_fee_drag": 0.01512239322804982,
          "annualized_turnover_perp_units": 25.209249880306807,
          "annualized_turnover_spot_units": 25.19872754652592,
          "annualized_turnover_units": 50.40797742683274,
          "avg_gross_exposure": 1.9069767441860466,
          "avg_spot_notional_fraction": 0.9534883720930233,
          "downside_deviation_annualized": 0.005091411330251628,
          "end": "2024-12-31",
          "engine_risk_free_rate_annual": 0.02,
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
      "cost_model": "flat_3bp",
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.02985895674198694,
          "annualized_fee_drag": 0.02985895674198694,
          "annualized_turnover_perp_units": 49.77500189894696,
          "annualized_turnover_spot_units": 49.75485390767618,
          "annualized_turnover_units": 99.52985580662315,
          "avg_gross_exposure": 1.7613636363636365,
          "avg_spot_notional_fraction": 0.8806818181818182,
          "downside_deviation_annualized": 0.005758428120825902,
          "end": "2026-09-30",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.027664715333937977,
          "annualized_fee_drag": 0.027664715333937977,
          "annualized_turnover_perp_units": 46.1115889995682,
          "annualized_turnover_spot_units": 46.10412878022507,
          "annualized_turnover_units": 92.21571777979327,
          "avg_gross_exposure": 1.7735573411249086,
          "avg_spot_notional_fraction": 0.8867786705624543,
          "downside_deviation_annualized": 0.005028932436300118,
          "end": "2026-09-30",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.04204445147655621,
          "annualized_fee_drag": 0.04204445147655621,
          "annualized_turnover_perp_units": 70.07625909337838,
          "annualized_turnover_spot_units": 70.07191249514231,
          "annualized_turnover_units": 140.1481715885207,
          "avg_gross_exposure": 1.6206896551724137,
          "avg_spot_notional_fraction": 0.8103448275862069,
          "downside_deviation_annualized": 0.00489058220012769,
          "end": "2026-09-30",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.032602259470406146,
          "annualized_fee_drag": 0.032602259470406146,
          "annualized_turnover_perp_units": 54.355104418809546,
          "annualized_turnover_spot_units": 54.31909381587761,
          "annualized_turnover_units": 108.67419823468715,
          "avg_gross_exposure": 1.7461187214611873,
          "avg_spot_notional_fraction": 0.8730593607305936,
          "downside_deviation_annualized": 0.006353739145349651,
          "end": "2022-12-31",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.015114412106864887,
          "annualized_fee_drag": 0.015114412106864887,
          "annualized_turnover_perp_units": 25.19577570291855,
          "annualized_turnover_spot_units": 25.185597986631084,
          "annualized_turnover_units": 50.381373689549626,
          "avg_gross_exposure": 1.9069767441860466,
          "avg_spot_notional_fraction": 0.9534883720930233,
          "downside_deviation_annualized": 0.005096635436352339,
          "end": "2024-12-31",
          "engine_risk_free_rate_annual": 0.02,
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
      "cost_model": "flat_3bp",
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.005540178878605894,
          "annualized_fee_drag": 0.005540178878605894,
          "annualized_turnover_perp_units": 9.242917132613526,
          "annualized_turnover_spot_units": 9.224345796072793,
          "annualized_turnover_units": 18.467262928686317,
          "avg_gross_exposure": 2.0,
          "avg_spot_notional_fraction": 1.0,
          "downside_deviation_annualized": 0.01294182069423682,
          "end": "2026-09-30",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.004332166182614438,
          "annualized_fee_drag": 0.004332166182614438,
          "annualized_turnover_perp_units": 7.223962861743997,
          "annualized_turnover_spot_units": 7.216591080304129,
          "annualized_turnover_units": 14.440553942048126,
          "avg_gross_exposure": 2.0,
          "avg_spot_notional_fraction": 1.0,
          "downside_deviation_annualized": 0.0026760951902644304,
          "end": "2026-09-30",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.004470130571070204,
          "annualized_fee_drag": 0.004470130571070204,
          "annualized_turnover_perp_units": 7.45254172077498,
          "annualized_turnover_spot_units": 7.447893516125698,
          "annualized_turnover_units": 14.900435236900682,
          "avg_gross_exposure": 2.0,
          "avg_spot_notional_fraction": 1.0,
          "downside_deviation_annualized": 0.0022811608681107373,
          "end": "2026-09-30",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.007050470550580602,
          "annualized_fee_drag": 0.007050470550580602,
          "annualized_turnover_perp_units": 11.767070919664105,
          "annualized_turnover_spot_units": 11.734497582271237,
          "annualized_turnover_units": 23.501568501935342,
          "avg_gross_exposure": 2.0,
          "avg_spot_notional_fraction": 1.0,
          "downside_deviation_annualized": 0.01767487323956173,
          "end": "2022-12-31",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.00421175403509764,
          "annualized_fee_drag": 0.00421175403509764,
          "annualized_turnover_perp_units": 7.024464486830499,
          "annualized_turnover_spot_units": 7.014715630161637,
          "annualized_turnover_units": 14.039180116992133,
          "avg_gross_exposure": 2.0,
          "avg_spot_notional_fraction": 1.0,
          "downside_deviation_annualized": 0.0031681160135460518,
          "end": "2024-12-31",
          "engine_risk_free_rate_annual": 0.02,
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
      "cost_model": "flat_3bp",
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.029087912343942538,
          "annualized_fee_drag": 0.029087912343942538,
          "annualized_turnover_perp_units": 48.48911696307737,
          "annualized_turnover_spot_units": 48.470590850064426,
          "annualized_turnover_units": 96.9597078131418,
          "avg_gross_exposure": 1.7585227272727273,
          "avg_spot_notional_fraction": 0.8792613636363636,
          "downside_deviation_annualized": 0.010780481822342773,
          "end": "2026-09-30",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.026215533149916335,
          "annualized_fee_drag": 0.026215533149916335,
          "annualized_turnover_perp_units": 43.696350967996345,
          "annualized_turnover_spot_units": 43.68875953172476,
          "annualized_turnover_units": 87.38511049972112,
          "avg_gross_exposure": 1.7786705624543462,
          "avg_spot_notional_fraction": 0.8893352812271731,
          "downside_deviation_annualized": 0.0036399801629127546,
          "end": "2026-09-30",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.03624397039937078,
          "annualized_fee_drag": 0.03624397039937078,
          "annualized_turnover_perp_units": 60.40909277914575,
          "annualized_turnover_spot_units": 60.404141885423506,
          "annualized_turnover_units": 120.81323466456928,
          "avg_gross_exposure": 1.6598746081504703,
          "avg_spot_notional_fraction": 0.8299373040752351,
          "downside_deviation_annualized": 0.0036061442898563116,
          "end": "2026-09-30",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.032679042130811825,
          "annualized_fee_drag": 0.032679042130811825,
          "annualized_turnover_perp_units": 54.4811686957403,
          "annualized_turnover_spot_units": 54.448971740299115,
          "annualized_turnover_units": 108.93014043603944,
          "avg_gross_exposure": 1.7333333333333334,
          "avg_spot_notional_fraction": 0.8666666666666667,
          "downside_deviation_annualized": 0.015062157196207076,
          "end": "2022-12-31",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.01746294359430493,
          "annualized_fee_drag": 0.01746294359430493,
          "annualized_turnover_perp_units": 29.109854011069775,
          "annualized_turnover_spot_units": 29.09995796994666,
          "annualized_turnover_units": 58.20981198101644,
          "avg_gross_exposure": 1.8823529411764706,
          "avg_spot_notional_fraction": 0.9411764705882353,
          "downside_deviation_annualized": 0.0036966050365012807,
          "end": "2024-12-31",
          "engine_risk_free_rate_annual": 0.02,
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
      "cost_model": "flat_3bp",
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.02903624674881154,
          "annualized_fee_drag": 0.02903624674881154,
          "annualized_turnover_perp_units": 48.40191383165196,
          "annualized_turnover_spot_units": 48.38557533105317,
          "annualized_turnover_units": 96.78748916270514,
          "avg_gross_exposure": 1.7593344155844155,
          "avg_spot_notional_fraction": 0.8796672077922078,
          "downside_deviation_annualized": 0.004315540946656484,
          "end": "2026-09-30",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.0261916327909776,
          "annualized_fee_drag": 0.0261916327909776,
          "annualized_turnover_perp_units": 43.65628915877378,
          "annualized_turnover_spot_units": 43.649153477818246,
          "annualized_turnover_units": 87.305442636592,
          "avg_gross_exposure": 1.7786705624543462,
          "avg_spot_notional_fraction": 0.8893352812271731,
          "downside_deviation_annualized": 0.003457008054848606,
          "end": "2026-09-30",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.03619285350330643,
          "annualized_fee_drag": 0.03619285350330643,
          "annualized_turnover_perp_units": 60.3236306213407,
          "annualized_turnover_spot_units": 60.31921438968072,
          "annualized_turnover_units": 120.64284501102144,
          "avg_gross_exposure": 1.6598746081504703,
          "avg_spot_notional_fraction": 0.8299373040752351,
          "downside_deviation_annualized": 0.003159556476958663,
          "end": "2026-09-30",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.03259266365134548,
          "annualized_fee_drag": 0.03259266365134548,
          "annualized_turnover_perp_units": 54.335028148702435,
          "annualized_turnover_spot_units": 54.307184022449164,
          "annualized_turnover_units": 108.64221217115161,
          "avg_gross_exposure": 1.735159817351598,
          "avg_spot_notional_fraction": 0.867579908675799,
          "downside_deviation_annualized": 0.005080660469959611,
          "end": "2022-12-31",
          "engine_risk_free_rate_annual": 0.02,
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
          "annualized_capital_charge_drag": 0.0,
          "annualized_cost_drag": 0.017462797203473105,
          "annualized_fee_drag": 0.017462797203473105,
          "annualized_turnover_perp_units": 29.109416582689363,
          "annualized_turnover_spot_units": 29.099907428887658,
          "annualized_turnover_units": 58.209324011577024,
          "avg_gross_exposure": 1.8823529411764706,
          "avg_spot_notional_fraction": 0.9411764705882353,
          "downside_deviation_annualized": 0.003833094571830268,
          "end": "2024-12-31",
          "engine_risk_free_rate_annual": 0.02,
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
          "note": "Constant-notional rebalance of both legs every day (the cost screen's convention): w*(|spot_return| + |perp_return|) while the pair is held, of which the spot leg trades w*|spot_return| and the perp leg w*|perp_return|.",
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
          "note": "Equal-notional maintenance: only the basis drift is traded, w*|spot_return - perp_return| while the pair is held. The adjustment is executed on the spot leg (the perp leg keeps its drifted notional), which is the conservative choice under a per-leg fee schedule.",
          "sharpe_canonical": 8.49594634136537
        }
      },
      "funding_positive_lagged": {
        "drift": {
          "ann_return_geometric": 0.10534031886718953,
          "annualized_cost_drag": 0.029087912343942538,
          "annualized_turnover_units": 96.9597078131418,
          "note": "Constant-notional rebalance of both legs every day (the cost screen's convention): w*(|spot_return| + |perp_return|) while the pair is held, of which the spot leg trades w*|spot_return| and the perp leg w*|perp_return|.",
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
          "note": "Equal-notional maintenance: only the basis drift is traded, w*|spot_return - perp_return| while the pair is held. The adjustment is executed on the spot leg (the perp leg keeps its drifted notional), which is the conservative choice under a per-leg fee schedule.",
          "sharpe_canonical": 6.889376379713542
        }
      },
      "funding_positive_sameday": {
        "drift": {
          "ann_return_geometric": 0.11392306271560937,
          "annualized_cost_drag": 0.02903624674881154,
          "annualized_turnover_units": 96.78748916270514,
          "note": "Constant-notional rebalance of both legs every day (the cost screen's convention): w*(|spot_return| + |perp_return|) while the pair is held, of which the spot leg trades w*|spot_return| and the perp leg w*|perp_return|.",
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
          "note": "Equal-notional maintenance: only the basis drift is traded, w*|spot_return - perp_return| while the pair is held. The adjustment is executed on the spot leg (the perp leg keeps its drifted notional), which is the conservative choice under a per-leg fee schedule.",
          "sharpe_canonical": 7.997429313210894
        }
      }
    }
  },
  "turnover_convention_bounds": {
    "always_on": {
      "drift": {
        "ann_return_geometric": 0.09218983799950076,
        "annualized_capital_charge_drag": 0.02,
        "annualized_fee_drag": 0.017539256948116817,
        "annualized_turnover_units": 18.467262928686317,
        "consistent_with_pre_registered_gross_path": true,
        "max_drawdown": -0.021235065443034107,
        "note": "Constant-notional rebalance of both legs every day (the cost screen's convention): w*(|spot_return| + |perp_return|) while the pair is held, of which the spot leg trades w*|spot_return| and the perp leg w*|perp_return|.",
        "sharpe_canonical": 5.964428000395712
      },
      "fixed_quantity": {
        "ann_return_geometric": 0.11119691666287435,
        "annualized_capital_charge_drag": 0.02,
        "annualized_fee_drag": 0.000281452922077922,
        "annualized_turnover_units": 0.2962662337662338,
        "consistent_with_pre_registered_gross_path": false,
        "max_drawdown": -0.017680580415810554,
        "note": "Fixed coin quantity on both legs (no daily rebalancing at all): the pair is entered and exited only.",
        "sharpe_canonical": 7.12295353639318
      },
      "parity": {
        "ann_return_geometric": 0.11108952219462687,
        "annualized_capital_charge_drag": 0.02,
        "annualized_fee_drag": 0.0003781369769440342,
        "annualized_turnover_units": 0.376836279487994,
        "consistent_with_pre_registered_gross_path": false,
        "max_drawdown": -0.017701513687370163,
        "note": "Equal-notional maintenance: only the basis drift is traded, w*|spot_return - perp_return| while the pair is held. The adjustment is executed on the spot leg (the perp leg keeps its drifted notional), which is the conservative choice under a per-leg fee schedule.",
        "sharpe_canonical": 7.116572948610952
      }
    },
    "funding_positive_lagged": {
      "drift": {
        "ann_return_geometric": 0.01970566667269469,
        "annualized_capital_charge_drag": 0.017585227272727273,
        "annualized_fee_drag": 0.09210709089423148,
        "annualized_turnover_units": 96.9597078131418,
        "consistent_with_pre_registered_gross_path": true,
        "max_drawdown": -0.23260191941836283,
        "note": "Constant-notional rebalance of both legs every day (the cost screen's convention): w*(|spot_return| + |perp_return|) while the pair is held, of which the spot leg trades w*|spot_return| and the perp leg w*|perp_return|.",
        "sharpe_canonical": 1.0879353280007824
      },
      "fixed_quantity": {
        "ann_return_geometric": 0.03510162728456834,
        "annualized_capital_charge_drag": 0.017585227272727273,
        "annualized_fee_drag": 0.07711810064935065,
        "annualized_turnover_units": 81.17694805194806,
        "consistent_with_pre_registered_gross_path": false,
        "max_drawdown": -0.18863627118438275,
        "note": "Fixed coin quantity on both legs (no daily rebalancing at all): the pair is entered and exited only.",
        "sharpe_canonical": 1.903193033436771
      },
      "parity": {
        "ann_return_geometric": 0.03501115629720708,
        "annualized_capital_charge_drag": 0.017585227272727273,
        "annualized_fee_drag": 0.07720553223120646,
        "annualized_turnover_units": 81.24980770349458,
        "consistent_with_pre_registered_gross_path": false,
        "max_drawdown": -0.18882876746103183,
        "note": "Equal-notional maintenance: only the basis drift is traded, w*|spot_return - perp_return| while the pair is held. The adjustment is executed on the spot leg (the perp leg keeps its drifted notional), which is the conservative choice under a per-leg fee schedule.",
        "sharpe_canonical": 1.8984905237108414
      }
    },
    "funding_positive_sameday": {
      "drift": {
        "ann_return_geometric": 0.027732835648205834,
        "annualized_capital_charge_drag": 0.017593344155844157,
        "annualized_fee_drag": 0.09194403007942017,
        "annualized_turnover_units": 96.78748916270514,
        "consistent_with_pre_registered_gross_path": true,
        "max_drawdown": -0.2110329827390569,
        "note": "Constant-notional rebalance of both legs every day (the cost screen's convention): w*(|spot_return| + |perp_return|) while the pair is held, of which the spot leg trades w*|spot_return| and the perp leg w*|perp_return|.",
        "sharpe_canonical": 1.6151932391697257
      },
      "fixed_quantity": {
        "ann_return_geometric": 0.04307855123918802,
        "annualized_capital_charge_drag": 0.017593344155844157,
        "annualized_fee_drag": 0.07711810064935065,
        "annualized_turnover_units": 81.17694805194806,
        "consistent_with_pre_registered_gross_path": false,
        "max_drawdown": -0.16619481966808947,
        "note": "Fixed coin quantity on both legs (no daily rebalancing at all): the pair is entered and exited only.",
        "sharpe_canonical": 2.4581986249648535
      },
      "parity": {
        "ann_return_geometric": 0.04298899520532218,
        "annualized_capital_charge_drag": 0.017593344155844157,
        "annualized_fee_drag": 0.07720401318277689,
        "annualized_turnover_units": 81.24854182980327,
        "consistent_with_pre_registered_gross_path": false,
        "max_drawdown": -0.16639186480941914,
        "note": "Equal-notional maintenance: only the basis drift is traded, w*|spot_return - perp_return| while the pair is held. The adjustment is executed on the spot leg (the perp leg keeps its drifted notional), which is the conservative choice under a per-leg fee schedule.",
        "sharpe_canonical": 2.453554179903174
      }
    }
  }
}
```
