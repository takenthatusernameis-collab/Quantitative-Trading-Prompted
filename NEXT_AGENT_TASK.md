# NEXT AGENT TASK — Cycle 892

## Context
Cycle 891 hardened the net-of-cost evaluation of `cryptofunding_001` (shortlist rank 8, crypto
perpetual funding carry). Three defects of the Cycle 890 evaluation were corrected and the result
was re-recorded: the 24/7 series is now annualized at **365** periods/year instead of 252, the
funding-positive rule now pays for its **entry and exit** transitions, and the pre-registered
same-day funding signal was identified as a **look-ahead** and replaced by a previous-day signal
for the primary result.

Current measured state (equal-weight BTC/ETH portfolio, net of the repository's flat 3 bp/unit
cost model, 365-day annualization): always-on **+12.77%/yr**, canonical Sharpe **8.14**, max DD
-1.72%, turnover 18.5 units/yr; the implementable funding-positive rule **+10.53%/yr**, Sharpe
6.60, turnover 97.0 units/yr. The cost screen's crypto row is unchanged and ADMISSIBLE (break-even
69.19 bp/unit) and the screen still ends with `OVERALL: PASS`. The promotion gate is **FAIL**: the
Sharpe criterion passes with a wide margin, but the pooled out-of-sample count of independent
position round trips is 95 (funding-positive) and 0 (always-on), below the repository's 100. The
candidate stays an **exploratory signal**; nothing is promoted.

The remaining weakness is that **net capture feasibility is still measured with the repository's
flat cost model only**: 3 bp per unit of weight change, applied to turnover, with no charge for the
**capital** the book ties up in the spot leg and no venue-specific fee schedule.

## Objective
Measure the crypto carry under a **realistic execution and capital-cost model** instead of the
repository's flat turnover cost, and re-evaluate the promotion gates under it. Concretely:

1. **Capital charge.** The book is long spot / short perp, so the spot leg ties up cash that
   could earn the risk-free rate (`get_risk_free_rate()`) or a stablecoin yield. Charge the
   capital charge on the spot-leg notional (`weight * spot_notional`) and report a sensitivity
   (e.g. 0% / repo rf / 5% USDT-equivalent yield). State the convention explicitly: the
   repository's backtest-baseline Sharpe already subtracts the rf from the *ratio*, but the
   *return* series does not pay it.
2. **Venue fee schedule.** Replace the flat 3 bp/unit by a per-leg schedule (Binance VIP0 spot
   taker vs perp taker, with a maker alternative), applied to the leg weights actually traded, and
   report the break-even cost per unit under that schedule. Use the schedule published by the
   venue as a documented assumption (source and date in the record); no live fees are implied.
3. **Rebalancing convention.** Cycle 891 showed the turnover convention (daily constant-notional
   rebalance vs parity maintenance vs fixed coin quantity) moves the drag by two orders of
   magnitude. Fix the headline convention with an explicit argument (what an implementer would
   actually trade) and keep the others as sensitivity rows.
4. **Re-evaluate the gates** (canonical scale, 365-day) under the realistic model and report the
   break-even capital charge and break-even fee per unit.

## Acceptance Criteria
- `research/eval_cryptofunding.py` reports, per rule and per pre-registered sample, the net
  annualized return, canonical Sharpe and max drawdown under (a) the flat model, (b) the capital
  charge, and (c) the venue fee schedule; the capital-charge and fee rows are explicit and
  reproducible.
- The break-even cost per unit **and** the break-even capital charge are reported for every rule,
  and the promotion gate is re-evaluated under the realistic model (the gate decision must remain
  evidence-based and must not be relaxed).
- The record states which model is the headline and why; the cost-screen reconciliation section
  still reproduces the screen's crypto row exactly (same gross and turnover series, screen
  break-even 69.1853 bp) and states explicitly that the screen uses the flat model.
- `research/experiments/cryptofunding_002_evaluation.md`,
  `research/hypotheses/cryptofunding_001.md` and the rank-8 rows of
  `research/reports/opportunity_shortlist.md` are updated consistently with the new numbers
  (no re-ranking, no score change unless the evidence requires it and the change is justified).
- Tests still pass (`python -m pytest -q`, `python -m pytest -q tests/test_eval_cryptofunding.py`,
  `python -m pytest -q tests/test_binance_crypto_funding.py`); the cost screen still ends with
  `OVERALL: PASS`.

## Validation
```bash
python research/eval_cryptofunding.py
python -m pytest -q tests/test_eval_cryptofunding.py
python research/cost_admissibility_screen.py
python -m pytest -q
```

## Scope Boundaries
- No live trading, no credentials, no new dependencies, no scheduled jobs or infrastructure.
- Do not modify the committed Binance/OKX raw caches or the committed carry paths.
- Do not change the repository's flat cost model, the cost screen's shared machinery, the
  promotion-gate thresholds, or the other candidates' rows; the crypto candidate's numbers may
  change, the conventions may not.
- Do not re-rank the shortlist, do not promote the candidate, and do not add new trading rules
  beyond the three pre-registered ones (trial count stays at 3 rules x 2 symbols = 6
  configurations; the capital-charge and fee rows are sensitivity analyses of the same
  configurations).
- Keep the loop non-recursive: this task must not dispatch another workflow or agent session.

## Handoff
- **Changed (Cycle 891):** `research/eval_cryptofunding.py` rewritten as a documented, deterministic
  evaluation (365-day annualization, charged entry/exit transitions, previous-day funding signal
  for the implementable rule, repo metrics on the 365 scale, block-bootstrap CIs, cost / turnover
  convention / funding-rounding / convergence / capacity robustness, cost-screen reconciliation,
  honest trade counts, gate = FAIL); `src/backtest/engine.py` and
  `src/evaluation/statistics.py` gained a backward-compatible `periods_per_year` keyword
  (default 252, so every committed number is unchanged); `tests/test_eval_cryptofunding.py`
  added (21 invariants); `research/experiments/cryptofunding_002_evaluation.md`,
  `research/hypotheses/cryptofunding_001.md` and the rank-8 shortlist rows rewritten.
- **Verified:** `python -m pytest -q` -> 194 passed; `python -m pytest -q
  tests/test_eval_cryptofunding.py` -> 21 passed; `python research/cost_admissibility_screen.py`
  -> `OVERALL: PASS` (crypto row unchanged: gross +9.0672%/yr at 252, turnover 12.55/yr, drag
  +0.3764%, break-even 69.1853 bp, ADMISSIBLE); `python research/eval_cryptofunding.py` regenerates
  the committed record deterministically. The Cycle 890 always-on numbers reproduce exactly when
  the hardened evaluation is rendered at 252 without the entry cost (regression test).
- **Unresolved:** the net capture is still measured with the flat 3 bp/unit turnover cost, with no
  capital charge for the spot leg and no venue fee schedule - this is the next task above. Also
  unresolved and out of scope here: the candidate's price legs are Binance-only (an independent
  venue's funding history is still not cached, the OKX API returned only ~296 records in Cycle
  888), and the capacity estimate is an upper bound that ignores market impact.
- **Failed approaches to avoid repeating:** (i) re-litigating the Cycle 890 max-drawdown
  "inconsistency" - the always-on drawdowns reproduce exactly from the parquet and the small
  drawdowns belong to the funding-positive rows; (ii) treating the canonical and the backtest
  Sharpe/Sortino scales as a series mismatch - the sign difference on the low-return OOS window
  is the 2% risk-free rate in the engine's backtest-baseline numerator, and both formulas are now
  pinned by tests.
