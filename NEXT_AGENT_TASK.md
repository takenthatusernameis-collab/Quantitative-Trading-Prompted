# NEXT AGENT TASK — Cycle 893

## Context
Cycle 892 measured the crypto funding carry (`cryptofunding_001`, shortlist rank 8) under a
realistic execution and capital-cost model instead of the repository's flat turnover cost, and
re-evaluated the promotion gates under it.

Measured state after Cycle 892 (equal-weight BTC/ETH portfolio, 365-day annualization, the
headline model = Binance VIP0 taker fees applied to the traded leg weights + the repository's
2 bp/unit slippage + the repository's 2% risk-free rate as the charge for the capital the spot
leg ties up):

| Rule | Flat model (Cycle 891) | Headline realistic model | OOS Sharpe (flat -> headline) |
|---|---|---|---|
| always-on | +12.77%/yr, Sharpe 8.14 | **+9.22%/yr, Sharpe 5.96** | 11.14 -> **1.52** |
| funding-positive (previous-day signal, implementable) | +10.53%/yr, Sharpe 6.60 | **+1.97%/yr, Sharpe 1.09** | 0.98 -> **-6.46** (pooled per-symbol) |

The gate is **FAIL under every one of the 24 cost-model rows**: the trade-count criterion fails in
all of them (95 and 0 pooled out-of-sample round trips against the repository's 100) and the
Sharpe criterion fails in 15 of them. The candidate stays an **exploratory signal**; nothing is
promoted. Break-evens per rule (always-on, full sample): the capital charge could rise to
+10.82%/yr and the published fee schedule could be 6.03x higher before the edge vanishes; out of
sample the headroom falls to +2.48%/yr and 1.34x. The cost screen is untouched and still ends
with `OVERALL: PASS` (crypto row: gross +9.0672%/yr at 252, turnover 12.55/yr, drag +0.3764%,
break-even 69.1853 bp, ADMISSIBLE); the screen uses the flat 3 bp/unit model and is explicitly
not this candidate's headline.

The weakness this cycle left open is **the gross path is the pre-registered constant-notional
construction**: the book resets the spot and perp notionals to `w * equity` every day. That is the
only turnover convention internally consistent with it, so it is the headline - but an
implementer would not rebalance a delta-neutral carry pair every day, and a **fixed-coin** book is
paid its funding on a notional that scales with the coin's price, so its return on equity is a
*different quantity* (the record states this explicitly and defers the measurement). The Cycle 892
cost-only bounds (parity +0.038%/yr and fixed-quantity +0.028%/yr of fee drag versus the drift
convention's +1.754%/yr) therefore bound only the *trading cost*; they say nothing about the
*gross* path of the book an implementer would actually run.

## Objective
Build the **implementable construction with a self-consistent gross path** and measure the same
three pre-registered rules under it, so that the headline convention is chosen on evidence and
the record can state whether the constant-notional headline is conservative or optimistic.

Concretely, for the committed carry path's price levels (`spot_close`, `perp_close`) and its
funding cashflow:

1. **Fixed coin quantity (no daily trading).** Hold `q` coins long spot and `q` coins short perp
   from the entry to the exit, where `q` is set at the entry from the book's then-current equity.
   The equity path must be marked to market: the price P&L is the change of the *basis level*
   (`q * (S_t - P_t)`), the funding is paid on the coin's perp notional
   (`q * funding_cashflow_t * P_{t-1}`, the daily close as the notional proxy - state the
   approximation), and the entry/exit are charged. The masked rule re-sizes `q` at each entry
   from the then-current equity.
2. **Threshold-rebalanced constant notional (optional, if 1 is complete).** The same
   constant-notional target, rebalanced only when the notional drifts beyond a stated threshold
   (e.g. 2%), which is what an implementer actually does. Report the threshold as a sensitivity.
3. **Cost model.** Apply the Cycle 892 headline cost model to the new constructions: the venue
   fee schedule on the leg weights actually traded (the entry and the exit), the repository's
   slippage, and the capital charge on the spot leg's notional.
4. **Report.** Per rule and per pre-registered sample: net annualized return, canonical Sharpe,
   max drawdown, the turnover, the break-evens and the promotion gate; then state, with numbers,
   whether the constant-notional headline is conservative or optimistic relative to the
   implementable construction, and what the headline should be.

## Acceptance Criteria
- The new constructions' gross paths are derived from the **committed** carry path only (no new
  data, no new downloads) and their accounting is stated in the record: the equity path, the
  funding notional, the basis P&L, the entry/exit, and the approximation used for the funding
  notional.
- `research/eval_cryptofunding.py` reports, per rule and per pre-registered sample, the net
  annualized return, canonical Sharpe and max drawdown of the implementable construction under the
  Cycle 892 headline cost model, with the break-evens (flat cost per unit, capital charge, fee
  multiple) and the promotion gate re-evaluated (never relaxed).
- A regression test pins the reconciliation between the new path and the committed carry path
  (e.g. the funding dollars accrued over a holding stretch equal the sum of
  `funding_cashflow * perp notional per coin`, and the new path reproduces the constant-notional
  path's *funding-only* component when the notional is held constant), plus a test that the
  implementable construction's turnover is consistent with the trades it claims to make.
- The record states explicitly which construction is the **headline** and why, and whether the
  Cycle 892 constant-notional headline was conservative or optimistic, with the numbers.
- `research/experiments/cryptofunding_002_evaluation.md`,
  `research/hypotheses/cryptofunding_001.md` and the rank-8 row of
  `research/reports/opportunity_shortlist.md` are updated consistently with the new numbers (no
  re-ranking; no promotion; the candidate's verdict may change only if the evidence requires it).
- Tests pass (`python -m pytest -q`, `python -m pytest -q tests/test_eval_cryptofunding.py`,
  `python -m pytest -q tests/test_binance_crypto_funding.py`); the cost screen still ends with
  `OVERALL: PASS` and its crypto row is unchanged.

## Validation
```bash
python research/eval_cryptofunding.py
python -m pytest -q tests/test_eval_cryptofunding.py
python research/cost_admissibility_screen.py
python -m pytest -q
```

## Scope Boundaries
- No live trading, no credentials, no new dependencies, no scheduled jobs or infrastructure, no
  new data downloads.
- Do not modify the committed Binance/OKX raw caches or the committed carry paths
  (`data/processed/crypto/*_carry_path.parquet`); the new constructions are derived from them.
- Do not change the repository's flat cost model, the cost screen's shared machinery, the
  promotion-gate thresholds, or the other candidates' rows; the crypto candidate's numbers may
  change, the conventions may not.
- Do not re-rank the shortlist, do not promote the candidate, and do not add new trading rules
  beyond the three pre-registered ones. The new constructions are **sensitivity analyses of the
  same six configurations** (3 rules x 2 symbols); the trial count does not grow, and the
  pre-registered rule set is unchanged.
- Keep the loop non-recursive: this task must not dispatch another workflow or agent session.

## Handoff
- **Changed (Cycle 892):** `research/eval_cryptofunding.py` gained a per-leg turnover
  decomposition (the spot and the perp leg are charged at their own published rates), a
  `CostModel` machinery with eight models (the flat model, the flat model + capital charge, the
  venue taker schedule, the venue taker + slippage, the venue maker + slippage, and the three
  capital-charge sensitivities 0% / repo rf / 5% USDT-equivalent yield), a capital charge on the
  spot leg's notional, three break-evens per rule (flat cost per unit, capital charge, multiple of
  the published fee schedule), the gate re-evaluated under every model, and the new record
  sections ("Cost models (Cycle 892)", "Results under the cost models", "Break-evens", "The
  turnover convention: the headline and the bound"). The Binance VIP0 schedule is documented with
  its two sources and the access date 2026-10-20. The Cycle 891 flat-model numbers are unchanged
  (regression-tested). `tests/test_eval_cryptofunding.py` grew from 21 to 39 invariants.
  `research/experiments/cryptofunding_002_evaluation.md`,
  `research/hypotheses/cryptofunding_001.md` and the rank-8 shortlist row were updated.
- **Verified:** `python -m pytest -q` -> 212 passed; `python -m pytest -q
  tests/test_eval_cryptofunding.py` -> 39 passed; `python research/cost_admissibility_screen.py`
  -> `OVERALL: PASS` with the crypto row unchanged (gross +9.0672%/yr at 252, turnover 12.55/yr,
  drag +0.3764%, break-even 69.1853 bp, ADMISSIBLE, gate headroom 34.4890 bp);
  `python research/eval_cryptofunding.py` regenerates the record deterministically (two
  consecutive runs differ in the `generated_at` line only).
- **Unresolved:** the gross path of the implementable construction (this task above). Also
  unresolved and out of scope: the candidate's price legs are Binance-only (an independent
  venue's funding history is still not cached - the OKX API returned only ~296 records in Cycle
  888), the capacity estimate ignores market impact, and the promotion gate's trade-count
  criterion is structurally unreachable for a continuously held carry book (0 pooled out-of-sample
  round trips; the independent observations are the 3,828 funding settlements).
- **Failed approaches to avoid repeating:** (i) re-litigating the Cycle 890 max-drawdown
  "inconsistency" - the always-on drawdowns reproduce exactly from the parquet and the small
  drawdowns belong to the funding-positive rows; (ii) treating the canonical and the backtest
  Sharpe/Sortino scales as a series mismatch - the sign difference on the low-return OOS window
  is the 2% risk-free rate in the engine's backtest-baseline numerator, and both formulas are
  pinned by tests; (iii) reporting a turnover-convention row as if it were a book - the Cycle 892
  `parity` and `fixed_quantity` rows are **cost-only bounds** on the constant-notional gross
  path and are not a valid headline on their own.
