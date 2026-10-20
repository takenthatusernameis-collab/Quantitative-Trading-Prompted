# Next agent task — Cycle 897 (draft)

## Context

Cycle 896 independently replicated the Cycle 895 reconciled fixed-coin portfolio and, in doing so,
measured the capital base the reconciled construction actually ties up. The replication matched
`research/eval_cryptofunding.py` within 1e-9 (largest observed deviation 1.3e-15) and is kept as an
executable guard in `tests/test_eval_cryptofunding.py`
(`test_reconciled_portfolio_metrics_match_independent_reconstruction`).

The measurement produced one substantive finding, now committed in the record
(`research/experiments/cryptofunding_002_evaluation.md`, section "The capital base the reconciled
book ties up"):

* The reconciled construction's marked-to-market spot notional is **not** the combined equity. It is
  0.5x of it at a simultaneous entry and it drifts **above** it: always_on averages **1.60x** over the
  full sample, peaks at **3.90x** and ends at 1.44x; the funding-positive rules average 0.59-0.60x
  (flat on the days they are out of the market) and peak at 2.47x. The record's previous statement
  that the two legs' spot notionals "sum to the combined equity" was wrong and has been corrected.
* Measured on the capital it actually employs (gross P&L per unit of the marked-to-market spot
  notional), the fixed-coin book earns **+13.89%/yr** (always_on) against the constant-notional
  book's **+13.40%/yr** on its constant spot notional, while the fixed-coin book's gross on the
  *stated* equity is **+29.52%/yr**. The two constructions earn the **same gross return per unit of
  capital**: the fixed-coin book's headline advantage (the +16.20 pp/yr over constant-notional that
  the Cycle 893/895 record reports) is the return of a notional that grows with the price while the
  equity does not - an implicit leverage of up to 3.90x that needs margin the stated equity does
  not provide.
* The **cost** of that leverage is not priced anywhere in the committed numbers: the capital charge is
  levied on the spot notional (the capital employed), but the return is still measured on the stated
  equity. No number, gate, trial, cost model or ranking changed in Cycle 896; the candidate's verdict
  is unchanged (exploratory signal, not promoted; gate FAIL under every cost model, 0 and 95 pooled
  out-of-sample round trips vs 100).

## Objective

Price the leverage and state what the fixed-coin construction is worth on a **self-funded** basis:
(i) decompose the reconciled fixed-coin portfolio's gross P&L into the part that a constant-capital
book of the same trade would earn and the part that the notional's drift adds; (ii) re-state the
reconciled headline net of the capital that the drift actually requires (the margin and the funding
of the gap between the capital employed and the stated equity); (iii) state plainly whether the
fixed-coin construction's advantage over the constant-notional book survives on a self-funded basis,
and correct the record's "headline: fixed coin quantity" claim if it does not.

The definitions must be written down **before** the numbers are computed (falsifiable), and the
measurement must be deterministic and offline on the committed carry paths.

## Acceptance criteria

1. The record states, before the numbers, the definitions used: (a) the leverage path
   `L_t = marked-to-market spot notional / combined equity`; (b) the "gross per unit of capital
   employed" series `gross_t / L_t` (zero on the sessions the book is flat); (c) the **funding gap**
   `G_t = max(0, capital employed - stated equity)`; (d) the self-funded restatement, which must be
   a *re-accounting of the same book* (no new positions, rules, thresholds or symbols) whose cost
   side includes the funding of the gap at the stated capital rate, and the rate used must be named.
2. For all three pre-registered rules the record reports: the leverage path (min/avg/max per
   pre-registered sample), the funding gap (min/avg/max), the gross per unit of capital employed,
   the self-funded net return per sample, and the same three numbers for the constant-notional book,
   so the comparison is on one capital base.
3. A regression test in `tests/test_eval_cryptofunding.py` pins the identities the restatement relies
   on (gross per unit of capital employed = gross / leverage; the gap is zero where the capital
   employed is below the equity; the constant-notional book's spot notional is 0.5x the equity per
   invested symbol) and the rendered numbers.
4. The record states the conclusion with numbers - including the case where the advantage does **not**
   survive - and the "headline: fixed coin quantity" claim is corrected if the measurement contradicts
   it. The candidate's promotion status is not changed by this cycle: the gate stays FAIL and is never
   relaxed.
5. `python -m pytest -q` passes (explicit shell timeout >= 600 s; full suite ~185 s).
6. `python research/cost_admissibility_screen.py` ends OVERALL: PASS with the crypto row unchanged.
7. `python research/eval_cryptofunding.py` runs clean; `git status --porcelain data/ config/` is
   empty.

## Scope boundaries

- No new trials, rules, thresholds, symbols or cost models; the trial count stays 6 pre-registered
  configurations and the threshold grid stays closed.
- No change to the flat cost model, the cost screen, the promotion-gate thresholds or the ranking of
  the shortlist; no promotion or rejection of the candidate.
- Do not silently rewrite the committed Cycle 893 numbers or the Cycle 895 reconciled numbers; report
  the restatement next to them with the reason stated.
- The restatement is a diagnostic next to the committed headline, not a replacement of it, until the
  measurement above is in place.

## Validation commands

```
python research/eval_cryptofunding.py
python -m pytest -q                              # explicit timeout >= 600 s
python research/cost_admissibility_screen.py      # OVERALL: PASS, crypto row unchanged
```

## Evidence to hand off

- `research/eval_cryptofunding.py`: `build_fixed_coin_portfolio_book(paths, rule,
  capital_consistent=True)`, `fixed_coin_reconciled`, `fixed_coin_reconciled_break_evens`,
  `fixed_coin_reconciled_capital_base` (the Cycle 896 payload: min/avg/max/last spot-notional
  fraction, the constant-notional book's fraction, and the three annualizations).
- Cycle 896 measurements (committed, reproducible from `research/eval_cryptofunding.py`):
  capital base always_on 0.36x min / 1.60x average / 3.90x max / 1.44x last; funding-positive
  0.00x / 0.59-0.60x / 2.47x / 0.60-0.62x; gross on the stated equity +29.52%/yr (always_on) vs
  gross per unit of capital employed +13.89%/yr vs constant-notional gross +13.40%/yr.
- Reconciled full-sample net numbers (unchanged by Cycle 896): always_on +25.4188%/yr (Sharpe 6.626,
  DD -1.88%, turnover 0.30); funding_positive_lagged +3.7769%/yr (Sharpe 1.738, DD -23.86%, turnover
  81.18); committed Cycle 893 portfolio: always_on +54.1139%/yr, funding_positive_lagged +16.0201%/yr.
- Full test suite after Cycle 896: 230 passed (58 in `tests/test_eval_cryptofunding.py`) in ~184 s.
- Cycle 896 changes: `research/eval_cryptofunding.py`,
  `research/experiments/cryptofunding_002_evaluation.md`, `research/hypotheses/cryptofunding_001.md`,
  `research/reports/opportunity_shortlist.md`, `tests/test_eval_cryptofunding.py`.
