# Hypothesis: cryptofunding_001 — Crypto perpetual funding-rate carry (spot long + perp short)

## Mechanism
Perpetual swaps pay funding to anchor price to spot; persistently positive funding can be harvested via spot-long/perp-short. Mechanical feature of perpetual swaps driven by leveraged long demand.

## Expected direction and magnitude
Positive carry from funding payments. Measured gross carry over 2020-01-01..2026-09-30: +11.59%/yr (BTC) and +13.57%/yr (ETH), but strongly regime-dependent (+37.3%/yr ETH in 2021 vs +1.9%/yr in 2026 YTD) and **before** all costs. Net-of-cost magnitude remains unproven.

## Holding horizon
Continuous (funding every 8h); position held while funding positive.

## Asset universe
BTC/USDT, ETH/USDT USDT-margined perpetuals. Binance (primary: prices and funding) and OKX
(funding only, independent cross-check). BTC and ETH are perpetual contracts, so there is no
point-in-time membership set to reconstruct.

## Features and data sources
Binance public archive (data.binance.vision), every archive file SHA256-verified against the
published .CHECKSUM before parsing:
- 8h funding rates: data/raw/crypto/{BTC,ETH}_USDT_USDT_funding_binance.parquet — 7,395 records
  per symbol, 2020-01-01T00:00:00Z..2026-09-30T16:00:00Z (2,464.7 days), 0 missing 8h periods,
  0 duplicate timestamps.
- Daily spot and perp legs: data/raw/crypto/{BTC,ETH}USDT_{spot,perp}_1d_binance.parquet — 2,465
  daily rows each, 2020-01-01..2026-09-30.
- Coupled return path: data/processed/crypto/{BTC,ETH}USDT_carry_path.parquet (daily
  funding cashflow, spot/perp returns, basis convergence).
- OKX 8h funding (data/raw/crypto/{BTC,ETH}_USDT_USDT_funding.parquet, 296 records per symbol,
  2026-07-13..2026-10-20) retained as an independent cross-check: on the 238 overlapping 8h
  settlements the same funding sign occurs in 91.2% of periods, median absolute difference 0.213 bp.
Provenance: research/experiments/cryptofunding_002_data.md; machine-readable manifest:
research/reports/binance_crypto_manifest.json.

## Entry/exit rules
Enter spot-long/perp-short when funding positive; exit when funding turns negative or risk limits hit.

## Benchmark
Hold spot only / risk-free.

## Known confounders
Funding rates volatile and can turn negative (negative in ~14% of periods over the full span);
the 2020-2021 bull regime dominates the mean; single venue for the price legs; live Binance/Bybit
APIs are geo-blocked from this environment (the archive is reachable instead); funding settlement
timing is not observable inside the 8h window.

## Falsification condition
No durable positive net carry after fees over multi-year history; <100 independent funding periods;
gross carry concentrated in a single regime (2020-2021) with no carry in the post-2022 sample.

## Cost model assumptions
Fees, borrow, margin, slippage per exchange schedule; capacity limited by Binance spot/perp
liquidity. **Applied in Cycle 891** (repository flat model: 3 bp per unit of weight change) and
**extended in Cycle 892** (venue fee schedule + capital charge): Binance VIP 0 published fees
(spot maker/taker 0.1000%, USDⓈ-M perp maker 0.02% / taker 0.05%, accessed 2026-10-20) applied
to the leg weights actually traded, plus the repository's 2 bp/unit slippage assumption, plus a
capital charge on the spot leg's notional (0% / the repository's 2% risk-free rate / a 5%
USDT-equivalent yield). The headline model is the conservative corner: taker fees + the
repository's slippage + the repository's risk-free rate as the capital charge.

## Status
Pre-registered (Cycle 886). **Data blocker resolved (Cycle 889):** 2,464.7 days of 8h funding
history per symbol plus coupled daily spot/perp legs are cached and checksum-verified, and a
reproducible spot-long/perp-short return path is committed
(data/processed/crypto/*_carry_path.parquet). **Net-of-cost evaluated (Cycle 891, hardened):** the
candidate is an **exploratory signal** — net positive after the repository's cost model on every
rule, symbol and sample, with a large Sharpe margin, but **not promoted**: the promotion gate's
trade-count criterion is not met on independent position round trips, the pre-registered
funding-positive rule is contaminated by a look-ahead, and the capacity of the trade is small.
**Realistic cost model measured (Cycle 892):** the same three rules under the published Binance
VIP0 fee schedule (plus the repository's slippage) and a capital charge on the spot leg. The
always-on book still nets +9.22%/yr (canonical Sharpe 5.96) on the full sample, but its
out-of-sample Sharpe falls from 11.14 to 1.52 and the implementable funding-positive rule's
out-of-sample Sharpe turns **negative**; the gate is FAIL under every cost model. **Cycle 944 evaluation (implemented):** produced a reproducible evaluation script and tests following repository patterns. **Corrected in Cycle 945:** the Cycle 944 generator applied 0.02 bp/unit of trading cost and no capital charge instead of the frozen 5.0 bp/unit and 2.00%/yr, and evaluated the gate at the module's flat-3 bp default, so its published headline (13.77%) was the **gross** return of the headline rule's portfolio and its per-rule OOS Sharpes (always_on 9.209, funding_positive_sameday 1.762, funding_positive_lagged 0.977) were the Cycle 891 flat-3 bp rows. The corrected figures under the frozen config are portfolio net ann headline **+6.52%** (gross +13.80%) with per-rule OOS Sharpe always_on **3.154**, funding_positive_sameday **-3.956**, funding_positive_lagged **-4.378** (all gate_pass=False; 0 / 95 / 95 pooled OOS independent round trips). Verdict unchanged: **exploratory signal, not promoted**. Evidence: `research/experiments/cryptofunding_002_data.md`
(data), `research/experiments/cryptofunding_002_evaluation.md` (net-of-cost evaluation and the
realistic cost model), `research/reports/cost_admissibility_screen_001.md` (cost screen),
`research/reports/opportunity_shortlist.md` (rank 8); Cycle 888 data note:
`research/experiments/cryptofunding_001_data.md`; Cycle 944: `research/cryptofunding_001_evaluation.py`,
`tests/test_eval_cryptofunding_001.py`, `research/experiments/cryptofunding_001_evaluation.md`,
`research/reports/cryptofunding_001_evaluation.md`; Cycle 945 correction of record:
`research/experiments/cryptofunding_001_evaluation_erratum_001.md`.

## Pre-registration (Cycle 890 evaluation)

### Rule set (fixed, no post-hoc selection)
1. **Always-on**: spot-long + perp-short carry every day (hold constant notional, rebalance daily to maintain constant notional due to drift). Entry/exit: always in.
2. **Funding-positive only**: same construction but only when funding is positive (`funding_cashflow > 0`); zero position otherwise. This is the rule named in the hypothesis.

**Trial count:** 2 rules × 2 symbols = 4 configurations. Reported explicitly; no other variants tested in this cycle.

**Cycle 891 amendment (defect fixes, not new trials).** The rule set above is unchanged in
substance, but three defects in its *evaluation* were corrected, and the corrections are recorded
here so the pre-registration stays auditable:
1. **Annualization.** The series is 24/7, so every annualized quantity is computed at **365**
   periods/year. The 252 rendering is retained only to reconcile with the cost screen.
2. **Transition turnover.** The Cycle 890 evaluation masked the turnover of rule 2 with the
   position mask and therefore never charged an entry or an exit. Rule 2 now charges
   `|position change| * 2 * w` on top of the daily rebalance, exactly like rule 1's opening
   trade.
3. **Signal timing.** Rule 2's decision variable was the *same day's* aggregate funding, which is
   not knowable before the day starts. The implementable variant (decision on the **previous**
   day's aggregate funding) is evaluated alongside the pre-registered one, which is retained for
   reconciliation and labelled as look-ahead contaminated. The always-on rule is unaffected.

**Trial count after the amendment:** 3 rules (always-on, funding-positive same-day [contaminated],
funding-positive previous-day [implementable]) × 2 symbols = **6 configurations**; the BTC/ETH
portfolio is an equal-weight combination of the two symbol books, not an additional
configuration, and the robustness rows are sensitivity analyses of the same configurations.

### Cost model (all numbers and sources)
All costs are applied per the repository's flat cost model used by `research/cost_admissibility_screen.py`: **3 bp per unit of weight change** (commission + slippage as per `get_cost_params()`; repository default 1 bp commission + 2 bp slippage = 3 bp/unit).

Sources and assumptions:
- **Binance spot taker fee** on long leg: included in the 3 bp/unit turnover model (repository convention).
- **Binance USDT-margined perp maker/taker fee** on short leg: included in the 3 bp/unit turnover model (repository convention).
- **Slippage per leg**: included in the 3 bp/unit turnover model (repository convention).
- **Margin/financing cost on perp**: included implicitly in funding mechanics; funding cashflow is already separated in the path (`funding_cashflow`); no separate margin interest modeled beyond what funding represents.
- **Funding rounding**: assumed negligible / captured in observed funding rates from exchange data.
- **Positioning**: held constant-notional (one entry + daily drift rebalance). **Annual turnover in weight-change units** computed as `mean(daily |Δw|) * 252` where daily turnover is sum of absolute weight changes across legs; for constant-notional spot-long/perp-short with daily drift, daily turnover ≈ |spot_return| + |perp_return| per day (two legs rebalancing), annualized as reported.

### Chronological splits
- **Full sample:** 2020-01-02 to 2026-09-30 (2,464 days) - all data, reported in full.
- **Train/validation/test split (chronological, no post-hoc window exclusion):**
  - Train: 2020-01-02 to 2022-12-31
  - Validation: 2023-01-01 to 2024-12-31
  - Test (out-of-sample): 2025-01-01 to 2026-09-30
- **Post-2022 sub-sample** (required by falsification condition): 2023-01-01 to 2026-09-30 (separately reported).

### Benchmarks
- **Primary:** hold spot only (buy-and-hold spot)
- **Secondary:** risk-free rate (from `get_risk_free_rate()`)

### Promotion gates (from AGENTS.md)
- Net out-of-sample Sharpe >= 0.9
- Pooled out-of-sample trades > 100 (or equivalently sufficient independent observations)

### Falsification condition
No durable positive net carry after fees over multi-year history; < 100 independent funding periods; gross carry concentrated in a single regime (2020-2021) with no carry in the post-2022 sample. As stated in hypothesis.


## Cycle 891 Verdict (hardened net-of-cost evaluation, supersedes Cycle 890)
- **What was fixed.** (i) The annualization of a 24/7 crypto series is **365** periods/year, not
  252 (Cycle 890 annualized at 252 and understated the annual return, the annual volatility and
  the annual turnover by the same factor). (ii) The funding-positive rule now pays for its
  **position transitions**: an entry (long spot + short perp) and an exit each change the leg
  weights by `2 * w` and are charged, which Cycle 890 omitted. (iii) The implementable funding-
  positive rule decides with the **previous** day's aggregate funding; the pre-registered same-day
  rule is a look-ahead (the day's funding is only known after its 00:00/08:00/16:00 UTC
  settlements) and is reported only for reconciliation.
- **Headline (net of 3 bp/unit, 365-day annualization, equal-weight BTC/ETH portfolio).**
  Always-on: +12.77%/yr, canonical Sharpe 8.14, max drawdown -1.72%, turnover 18.5 units/yr.
  Funding-positive (implementable, previous-day signal): +10.53%/yr, canonical Sharpe 6.60, max
  drawdown -2.66%, turnover 97.0 units/yr (the entry/exit charges dominate). Out-of-sample
  (2025-01-01..2026-09-30): always-on +3.51%/yr, Sharpe 11.14; funding-positive +0.53%/yr,
  Sharpe 1.13. The block-bootstrap 95% CI of the OOS Sharpe of the implementable funding-positive
  rule spans zero ([-3.88, +7.54] for ETH), so the OOS window alone does not establish the edge.
- **Corrections to the Cycle 890 record.** Cycle 890 reported `promotion_gate_pass: true` on a
  trade count that counted daily rebalances of one continuously held position (2,335 "trades")
  rather than independent round trips. On the honest count the pooled out-of-sample round trips
  are 95 (funding-positive) and 0 (always-on, the position is opened before the window), i.e.
  **below the repository's 100-trade criterion**; the gate is therefore **FAIL** and the
  candidate is **not promoted**. The Cycle 890 funding-positive numbers were also inflated by the
  look-ahead and by the missing transition costs.
- **Reconciliation.** The cost screen's crypto row and this evaluation are the **same series**
  (identical gross and turnover), rendered at 252 (screen) and 365 (crypto). The screen's
  cost drag (+0.376%/yr) understates the crypto drag (+0.545%/yr) by 365/252; the break-even cost
  per unit (69.19 bp) and the ADMISSIBLE verdict are invariant. The screen still reports
  **OVERALL: PASS**.
- **Mechanism check.** The edge is the **funding payment**: the basis-convergence term is a near
  zero-sum change of the price difference and contributes nothing to the annualized return (the
  funding-only gross return is within 0.2 pp/yr of the credited one). The low daily volatility
  that produces the large Sharpe is the same term, so the strategy is exposed to the funding
  regime itself: the implementable funding-positive rule is **negative** in 2022 (-2.11%/yr) and
  in 2026 YTD (-1.53%/yr).
- **Capacity.** At a 1% participation budget the one-time entry of an always-on book is bounded
  by the spot leg at ~$17.1m (BTC) and ~$9.3m (ETH) on a median day, and at ~$1.2m / ~$0.19m on
  the worst observed day. The candidate's capacity is therefore **small**, and the flat cost model
  does not capture the market impact of a larger book.
- **Verdict: exploratory signal (not promoted).** The Sharpe criterion is met with a very large
  margin on the canonical scale (the gate's convention), but the trade-count criterion is not,
  the pre-registered rule was contaminated, the edge is venue-specific and regime-dependent,
  and the capacity is small. One more validation cycle is warranted before either promotion or
  rejection.
- **Evidence:** `research/experiments/cryptofunding_002_evaluation.md`,
  `research/reports/cost_admissibility_screen_001.md`,
  `research/reports/opportunity_shortlist.md`,
  `tests/test_eval_cryptofunding.py` (21 invariants over the committed carry paths).

## Cycle 892 amendment (cost model, not new trials)

The rule set, the symbols, the splits and the annualization of the Cycle 890/891 pre-registration
are **unchanged**. Cycle 892 replaces the *cost model* of the evaluation with a realistic
execution and capital-cost model and re-evaluates the promotion gate under it. The cost models
are **sensitivity analyses of the same six configurations** (3 rules x 2 symbols), not new
trials; the BTC/ETH portfolio remains an equal-weight combination of the two symbol books.

1. **Venue fee schedule.** The repository's flat 3 bp/unit is replaced by a per-leg schedule:
   Binance VIP 0 published fees (spot maker/taker 0.1000%, USDⓈ-M perp maker 0.02% / taker
   0.05%, sources and access date 2026-10-20 in the record), applied to the leg weights that are
   actually traded, plus the repository's own 2 bp/unit slippage assumption (a published fee
   schedule does not model execution slippage). A maker alternative is reported.
2. **Capital charge.** The capital the spot leg ties up is charged at an annual rate: 0%, the
   repository's 2% risk-free rate, or a 5% USDT-equivalent yield. The charge is applied to the
   *return series*; the repository's backtest-baseline Sharpe/Sortino (which subtract the risk-free
   rate from the ratio's numerator while the return series does not pay it) are therefore computed
   with a zero risk-free rate on those rows, to avoid charging it twice. The canonical gate
   convention is a zero-risk-free-rate convention and is unaffected.
3. **Turnover convention.** The headline is the daily constant-notional rebalance (`drift`),
   because it is the only convention that is internally consistent with the pre-registered
   constant-notional gross path; `parity` and `fixed_quantity` are reported as cost-only bounds
   and are explicitly **not** a valid headline, because a fixed-coin book is paid its funding on a
   notional that scales with the coin's price, so its return on equity is a different quantity.
4. **Break-evens.** Per rule: the break-even flat cost per unit, the break-even capital charge on
   the spot leg, and the break-even multiple of the published fee schedule.
5. **Gate.** Re-evaluated under every cost model with the repository's own thresholds, unchanged.

## Cycle 892 Verdict (realistic execution and capital-cost model)

- **Headline (venue taker + repository slippage + the repository's risk-free rate as the capital
  charge, equal-weight BTC/ETH portfolio, 365-day annualization).** Always-on: **+9.22%/yr**,
  canonical Sharpe **5.96**, max drawdown -2.12%, turnover 18.5 units/yr, fee drag +1.75%/yr,
  capital charge +2.00%/yr (the flat-model row was +12.77%/yr, Sharpe 8.14). Implementable
  funding-positive rule (previous-day signal): **+1.97%/yr**, canonical Sharpe **1.09** (flat
  model: +10.53%/yr, Sharpe 6.60).
- **Out-of-sample (2025-01-01..2026-09-30).** The always-on book's canonical Sharpe falls from
  11.14 (flat model) to **1.52** and its net return from +3.51%/yr to **+0.48%/yr**; the
  implementable funding-positive rule's out-of-sample Sharpe is **negative** (-6.46 on the pooled
  per-symbol books). The out-of-sample margin of the edge does not survive a realistic fee
  schedule and a realistic charge for the capital.
- **Break-evens.** Always-on: the capital charge could rise to **+10.82%/yr** on the spot leg
  (full sample) and the published fee schedule could be **6.03x** higher before the edge vanishes;
  out of sample the headroom falls to +2.48%/yr and 1.34x. The implementable funding-positive
  rule: +4.22%/yr and 1.21x on the full sample, and **negative** headroom out of sample (it needs
  a rebate to break even).
- **Gate.** FAIL under **every** cost model: the trade-count criterion (95 and 0 pooled
  out-of-sample round trips against the repository's 100) fails in all 24 rows, and the Sharpe
  criterion fails in 15 of them. The gate is not relaxed.
- **Verdict: exploratory signal (not promoted), unchanged.** The carry is large enough to survive
  a realistic cost model on the full sample, but not out of sample, and it is small-capacity,
  venue-specific and regime-dependent. Evidence:
  `research/experiments/cryptofunding_002_evaluation.md` (sections "Cost models (Cycle 892)",
  "Results under the cost models", "Break-evens", "Promotion gates"),
  `tests/test_eval_cryptofunding.py` (39 invariants over the committed carry paths).

## Cycle 893 amendment (implementable construction with a self-consistent gross path)

The rule set, the symbols, the splits and the 365-day annualization are **unchanged**. Cycle 893
adds the fixed coin quantity construction and measures the same three pre-registered rules under
it, under the Cycle 892 headline cost model (Binance VIP 0 taker plus the repository's slippage
on the legs actually traded, plus the capital charge on the marked-to-market spot notional).

**Construction.** Hold ``q`` coins long spot and short perp from entry to exit; ``q`` is set at
each entry from then-current marked-to-market equity (``q = weight * equity / spot_close``), so
the spot notional is ``weight`` of equity at entry. While held the daily price P&L is the change
of the basis level ``q * ((S_t - P_t) - (S_{t-1} - P_{t-1}))`` and funding is paid on the coin's
perp notional ``q * funding_cashflow_t * P_{t-1}`` (the previous day's perp close as the notional
proxy). Equity compounds on price P&L plus funding. Entry and exit days carry no same-day P&L;
entry and exit are charged as turnover (each leg trades ``weight`` per transition). There is no
daily rebalancing turnover.

**Results (net of the headline cost model, 365-day annualization, equal-weight BTC/ETH
portfolio; the fixed-coin book is a sensitivity of the same six configurations, not new trials).**
Always-on: **+54.11%/yr**, canonical Sharpe **6.740**, max drawdown -2.74%, turnover 0.30 units/yr
(2 entries, 0 exits). Implementable funding-positive rule (previous-day signal): **+16.02%/yr**,
canonical Sharpe **3.913**, max drawdown -15.60%, turnover 81.18 units/yr (275 entries, 273 exits).
Out of sample (2025-01-01..2026-09-30): always-on Sharpe **5.645** with 0 round trips; funding-positive
Sharpe **-5.224** with 95 round trips.

**Headline: fixed coin quantity.** On the same committed path the fixed-coin book nets more than
the constant-notional book on both rules, so the Cycle 892 constant-notional headline was
**conservative**: it under-states the implementable book by **+44.89 pp/yr** (always-on: +54.11%
vs +9.22%/yr) and **+14.05 pp/yr** (funding-positive: +16.02% vs +1.97%/yr). The reason is
mechanical and stated in the record: the fixed-coin book earns funding on a perp notional that
scales with the coin's price, so its return on equity is a different quantity from the
constant-notional book (which resets notional daily). This is not an error; both constructions
are derived from the same committed carry path with their accounting stated.

**Gate.** FAIL under the headline model: the trade-count criterion (0 and 95 pooled out-of-sample
independent round trips against the repository's 100) fails, and the Sharpe criterion fails for
the funding-positive rule out of sample. The gate is never relaxed.

**Verdict: exploratory signal (not promoted), unchanged.** The carry survives a realistic cost
model on the full sample under both constructions, but the implementable rule's edge does not
survive out of sample, the trade-count criterion fails, the candidate is venue-specific and
regime-dependent, and capacity remains small. Evidence:
`research/experiments/cryptofunding_002_evaluation.md` (section "The implementable construction:
fixed coin quantity"),
`tests/test_eval_cryptofunding.py` (fixed-coin invariants: funding reconciliation with the
committed carry path, notional fraction vs the constant-notional funding-only component, turnover
consistent with claimed trades).

## Cycle 894 amendment (threshold-rebalanced constant notional)

The rule set, the symbols, the splits and the 365-day annualization are **unchanged**. Cycle 894
adds the **threshold-rebalanced** version of the pre-registered constant-notional construction and
measures the same three pre-registered rules under it, under the Cycle 892 headline cost model
(Binance VIP 0 taker plus the repository's slippage on the legs actually traded, plus the capital
charge on the marked-to-market spot notional). It is a sensitivity of the same six configurations
(the rebalancing frequency of one construction), not a new trial.

**Construction.** The legs are reset to ``weight * equity`` only on the days where the cumulative
price drift of either leg since the last rebalance exceeds a pre-registered threshold of **2%**;
between two rebalances the notional floats with the price and nothing is traded. The two legs
carry **equal notional** at every rebalance (the pre-registered book's convention) and each leg
keeps its own coin quantity between rebalances. The daily P&L of a held leg is
``notional_spot * spot_return - notional_perp * perp_return + funding_cashflow * notional_perp``
with the notionals in effect from the previous close; the equity compounds on it, and the book has
**one** equity for all the symbols it holds (the equal-weight BTC/ETH book is one book with a
shared equity, not two books added up). A position transition is charged on both legs with the
target notional ``weight`` per leg, exactly as the pre-registered book charges it, and the entry
day's carry is earned. The turnover of a rebalance is the cumulative price drift of the leg since
the last rebalance, ``weight * |P_t / P_k - 1|`` per leg - the same linearized convention the
pre-registered ``drift`` turnover uses - so **a threshold of 0 reproduces the pre-registered book
exactly** (gross, both leg turnovers, leg weights and capital base), which is the regression guard
of the cycle.

**Results (net of the headline cost model, 365-day annualization, equal-weight BTC/ETH
portfolio).** Always-on: **+9.51%/yr**, canonical Sharpe **6.144**, max drawdown -2.02%, turnover
15.64 units/yr (2 entries, 0 exits). Implementable funding-positive rule (previous-day signal):
**+2.21%/yr**, canonical Sharpe **1.218**, max drawdown -22.43%, turnover 94.42 units/yr (275
entries, 273 exits). Out of sample (2025-01-01..2026-09-30): always-on Sharpe **2.088** with 0
round trips; funding-positive Sharpe **-6.276** with 95 round trips.

**Headline: the threshold-rebalanced constant notional nets more than the daily-rebalanced one, and
the reason is the trading cost, not the carry.** On the consistent per-symbol basis it nets more on
every rule and symbol (always-on: BTC **+8.74%/yr** vs **+8.43%/yr**, ETH **+10.28%/yr** vs
**+10.01%/yr**), but the *gross* path barely moves (the portfolio's gross annualized return is
+13.3957%/yr daily-rebalanced and +13.3901%/yr threshold-rebalanced): the annualized fee drag falls
from +1.75%/yr to +1.49%/yr because there are fewer trades. The threshold is a sensitivity of the
construction, not a new configuration: the pre-registered 2% is the headline and the 1%/5%/10% rows
are reported next to it, never used to select one.

**The threshold construction is not the fixed-coin construction.** It holds equal *notional* on the
two legs, so as the threshold grows the two coin quantities drift apart and the book accumulates a
directional exposure to the spot's relative performance since the last rebalance; the fixed-coin
construction holds one coin quantity on both legs, so its perp notional scales with the coin's
price while its equity compounds only on the carry. They are different books with different return
quantities, and the threshold construction does not converge to the fixed-coin one.

**Cycle 895 reconciliation of the fixed-coin portfolio accounting.** The committed Cycle 893
fixed-coin portfolio adds the two symbols' separately compounded returns, so each symbol's capital
is counted twice; the capital-consistent account of the same construction splits the capital once
(half per symbol at the entry, never rebalanced) and adds the two symbols' P&L against their
combined equity. Re-measured under the Cycle 892 headline cost model (365-day, equal-weight
BTC/ETH portfolio):

| Rule | Committed portfolio (capital counted twice) | Reconciled portfolio (capital split once) | Constant-notional (one shared equity) |
| always_on | +54.11%/yr net | +25.42%/yr net | +9.22%/yr net |
| funding_positive_lagged | +16.02%/yr net | +3.78%/yr net | +1.97%/yr net |

The committed Cycle 893 headline ("the constant-notional headline was conservative by +44.89
pp/yr always-on and +14.05 pp/yr funding-positive") **does not survive the reconciliation**: on
the capital-consistent account the margin shrinks to +16.20 pp/yr (always-on) and +1.81 pp/yr
(funding-positive). The constant-notional headline remains conservative versus the implementable
fixed-coin construction, but by a much smaller margin than the committed double-counted capital
suggested. The per-symbol rows are unaffected (each symbol's book is standalone, weight = 1), and
on that basis the fixed-coin construction still nets more than both the daily-drift and the
threshold-rebalanced books. The gross diagnostic (committed +94.88%/yr vs capital-consistent
+41.60%/yr always-on, ratio 2.28x) and the committed Cycle 893 number are reported next to the
reconciled figures and are not rewritten. The promotion gate is re-evaluated under the headline
model and still **FAIL** (0 and 95 pooled out-of-sample round trips against the repository's 100;
the gate is never relaxed).


**Cycle 896: independent replication and the reconciled construction's capital base.** Every
reconciled figure above was re-derived from the committed carry paths by a standalone script that
does **not** reuse `build_fixed_coin_portfolio_book`: the capital-consistent portfolio was rebuilt
from the per-symbol primitives (position path, spot and perp closes, funding cash flow), the net
series and the five pre-registered samples' metrics were recomputed under the headline cost model,
the three break-evens were re-solved with an independent bisection and the promotion gate was
re-evaluated on independently built per-symbol books. All of them agree with the evaluation to
within **1e-9** (the largest deviation observed was 1.3e-15, i.e. floating-point noise). The
replication is kept as an executable regression guard in `tests/test_eval_cryptofunding.py`
(`test_reconciled_portfolio_metrics_match_independent_reconstruction`).

The same cycle corrected the record's statement of the reconciled construction's **capital base**.
The two symbols' marked-to-market spot notionals do **not** sum to the combined equity: at a
simultaneous entry they are 0.5 of it (0.25 per symbol at the pre-registered leg weight of 0.5),
and marked to market they drift **above** it, because the fixed coin quantity drifts with the coin's
price while the equity compounds only on the carry. Measured over the full sample: always-on
**1.60x** on average, **3.90x** peak, 1.44x at the last session; the funding-positive rules average
0.59x-0.60x (they are flat on the days they are out of the market) and peak at 2.47x while a
position is held. Two consequences, both already priced in the numbers above and stated here so
that the comparison is not misread: the capital charge is levied on the marked-to-market notional,
so the drift raises it (at the headline's 2%/yr the always-on book pays about 3.2%/yr of capital
drag against the constant-notional book's 2.0%/yr), and the constant-notional book holds a constant
spot notional by construction, so the two books are compared on the same *equity* but not on the
same *capital*. The reconciled headline is therefore a return on the **stated** combined equity,
not on the capital the spot leg ties up. This is a property of the fixed-coin construction, not of
the accounting convention: the committed Cycle 893 book drifts the same way, with the capital
counted twice. No number, gate, trial, cost model or ranking changed in this cycle.

**The advantage is the leverage, not a better carry.** The same trade measured on the capital it
actually employs - the gross P&L per unit of the marked-to-market spot notional - is **+13.89%/yr**
for `always_on`, against the constant-notional book's **+13.40%/yr** on its constant spot notional,
while the fixed-coin book's gross on the *stated* equity is **+29.52%/yr**. The two constructions
therefore earn the **same gross return per unit of capital**; what the fixed-coin book reports on the
stated equity is the return of a notional that grows with the price while the equity does not - an
implicit leverage of up to 3.90x that needs margin the stated equity does not provide. The *cost* of
that leverage is not priced in the numbers above (the capital charge is levied on the spot notional,
which is the cost of the capital employed, but the return is still measured on the stated equity);
pricing the margin and the funding of the gap, and stating what the fixed-coin construction is worth
on a self-funded basis, is the next cycle's pre-registered question. This cycle measures the capital
base, reports it, and stops there.

**Gate.** FAIL under the headline model: the trade-count criterion (0 and 95 pooled out-of-sample
independent round trips against the repository's 100) fails, and the gate is never relaxed.

**Verdict: exploratory signal (not promoted), unchanged.** The rebalancing frequency of the
constant-notional construction moves the net result by a few tenths of a percentage point per year
and does not change the gate, the out-of-sample failure of the implementable rule, or the
candidate's status. Evidence:
`research/experiments/cryptofunding_002_evaluation.md` (section "The threshold-rebalanced constant
notional"),
`tests/test_eval_cryptofunding.py` (threshold invariants: exact reproduction of the daily-drift book
at a threshold of 0, the cumulative-turnover inequality, the transition charge, the gate).

## Cycle 945 reconciliation (metric deltas and explanations)

Cycle 944 published a frozen-configuration evaluation of this candidate. Cycle 945
compared every published figure with the prior cycles' record and found that the
Cycle 944 numbers did not follow from the specification the same record claimed to
implement. The correction is of record in
`research/experiments/cryptofunding_001_evaluation_erratum_001.md`; this section is
the reconciliation the task asked for: every metric delta, and why it exists.

### Deltas against the Cycle 944 publication

Equal-weight BTC/ETH portfolio, 365-day annualization, 2020-01-02..2026-09-30, OOS
window 2025-01-01..2026-09-30.

| Metric | Cycle 944 (as published) | Cycle 945 (corrected) | Delta | Explanation |
|---|---|---|---|---|
| Portfolio net ann, headline rule `funding_positive_lagged` | +13.7746% | **+6.5212%** | **-7.2534 pp** | The Cycle 944 generator called `net_series(book, cost_bps)` with `CAPITAL_CHARGE_RATES["repo_rf"]` (the **annual** capital-charge rate 0.02) in the **basis-points** argument, so it charged 0.02 bp/unit instead of the frozen 5.0 bp/unit and charged no capital charge at all. The published figure was the **gross** return of the same portfolio (+13.7966%/yr). |
| Portfolio gross ann (no cost) | not published | +13.7966% | - | Published here so that the net line can be read against it. Unchanged by the correction: the gross path was never in dispute. |
| Annualized fee drag of the headline rule | not published | 4.8480%/yr | - | 96.9597 turnover units/yr x 5.0 bp/unit, the frozen cost model's trading cost. |
| Annualized capital-charge drag of the headline rule | 0 (not applied) | 1.7585%/yr | +1.7585 pp | 2.00%/yr charged on the spot leg, whose average notional is 87.93% of the book's equity. |
| Mean per-symbol OOS Sharpe, `always_on` | 9.209 | **3.154** | **-6.055** | The Cycle 944 gate was evaluated with the module's default flat model (3 bp/unit, no capital charge), i.e. the Cycle 891 row, instead of the frozen configuration's cost model. |
| Mean per-symbol OOS Sharpe, `funding_positive_sameday` | 1.762 | **-3.956** | **-5.718** | Same cause. The look-ahead-contaminated rule's OOS edge does not survive the frozen cost model. |
| Mean per-symbol OOS Sharpe, `funding_positive_lagged` | 0.977 | **-4.378** | **-5.355** | Same cause. The implementable rule's OOS Sharpe is negative under the frozen cost model, as it already was under the Cycle 892 realistic model (-6.46) and the Cycle 894 threshold-rebalanced book (-6.28). |
| Pooled OOS independent round trips | 0 / 95 / 95 | 0 / 95 / 95 | 0 | A property of the **position path**, not of the cost model: the count is unchanged by any cost convention. |
| Promotion gate | FAIL (3 of 3 rules) | FAIL (3 of 3 rules) | 0 | The trade-count criterion (95 against the repository's 100) fails under every cost model; the Sharpe criterion is met only by `always_on` under the frozen configuration. |
| Verdict | exploratory signal, not promoted | **exploratory signal, not promoted** | 0 | The verdict is driven by the gate and by the capacity/regime findings, none of which changed. |

### Reconciliation against the prior cycles (891-896)

Every figure the prior cycles published is reproduced under **its own** cost model
(the flat-3 bp and the venue rows by the corrected generator's reconciliation table,
the threshold-rebalanced rows by the same committed evaluation module), so the prior
record is consistent and is **not** rewritten by this cycle; the Cycle 944 record was
the only outlier.

| Prior-cycle figure | Prior cycle's cost model | Reproduced | Matches |
|---|---|---|---|
| `always_on` +12.77%/yr, OOS Sharpe 11.14 | flat 3 bp/unit (Cycle 891) | +12.7694%, 11.144 | yes |
| `funding_positive_lagged` +10.53%/yr, OOS Sharpe 1.13 | flat 3 bp/unit (Cycle 891) | +10.5340%, 1.128 | yes |
| `always_on` +9.22%/yr, OOS Sharpe 1.52 | venue taker + slippage + rf (Cycle 892) | +9.2190%, 1.516 | yes |
| `funding_positive_lagged` +1.97%/yr, per-symbol OOS Sharpe -6.46 | venue taker + slippage + rf (Cycle 892) | +1.9706%, -6.459 | yes |
| `always_on` +9.51%/yr, OOS Sharpe 2.088 (threshold-rebalanced) | venue taker + slippage + rf (Cycle 894) | +9.5081%, 2.088 | yes |
| `funding_positive_lagged` +2.21%/yr, OOS Sharpe -6.276 (threshold-rebalanced) | venue taker + slippage + rf (Cycle 894) | +2.2113%, -6.276 | yes |

**Sharpe conventions.** The promotion gate's "net OOS Sharpe" is the **mean of the
per-symbol** canonical (arithmetic, zero risk-free) out-of-sample Sharpes, because the
gate is applied to the per-symbol books; the "OOS Sharpe" in the reconciliation table
of `research/reports/cryptofunding_001_evaluation.md` is the **portfolio-level**
canonical out-of-sample Sharpe of the equal-weight BTC/ETH book. The prior record
uses both conventions and labels each of them: 11.14 and 1.13 (Cycle 891) and 1.52
(Cycle 892) are portfolio-level, while -6.46 (Cycle 892) and 2.088 / -6.276 (Cycle
894) are per-symbol means. The Cycle 944/945 "sharpe_oos" line is the per-symbol mean,
i.e. the gate statistic. All of them are reproduced under their own cost model; none
is compared across conventions silently.

The corrected frozen-configuration headline (+6.52%/yr) sits **between** the Cycle 891
flat-model headline (+10.53%/yr) and the Cycle 892 realistic-model headline
(+1.97%/yr), which is the expected ordering for a 5 bp/unit model with a 2%/yr capital
charge between a 3 bp/unit model with no capital charge and a 12 bp/7 bp venue
schedule with the same capital charge.

### Finalized status

**Verdict: exploratory signal (not promoted) — unchanged by this cycle.** The
candidate's edge is the funding payment, it is large on the full sample and negative
out of sample under every cost model that charges a realistic fee schedule or the
capital the spot leg ties up, it fails the trade-count criterion (95 pooled
out-of-sample independent round trips against the repository's 100) under every cost
model, it is venue-specific and regime-dependent, and its capacity is small. The
Cycle 944 record's more favourable figures are withdrawn and replaced by the
corrected ones above; the frozen specification, the data, the trial count, the gates
and the cost model are unchanged.

The open question the record names is unchanged as well: the fixed-coin construction's
advantage is **leverage**, not a better carry (Cycle 896 measured the same gross
return per unit of capital for the fixed-coin and the constant-notional books), and
the margin and funding cost of that leverage gap are still unpriced. That is the
next bounded step, not a promotion.
