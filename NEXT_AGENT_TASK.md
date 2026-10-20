# Next agent task — Cycle 898 (draft)

## Context

Cycle 897 added the self-funded restatement fields to `fixed_coin_reconciled_capital_base`
(leverage path min/avg/max, funding gap min/avg/max, capital rate, self-funded net annualized)
in `research/eval_cryptofunding.py`. Tests pass (231), cost screen OVERALL: PASS.

## Objective

Update the experiment record `research/experiments/cryptofunding_002_evaluation.md` to state the
definitions (leverage, gross per unit capital employed, funding gap, self-funded restatement with
named capital rate) before numbers, report the new fields for all three rules plus constant-notional
comparison, and correct the "headline: fixed coin quantity" claim if the advantage does not survive
on a self-funded basis. Add a regression test pinning the new identities and rendered numbers.

## Acceptance criteria

1. Record states definitions before numbers and self-funded conclusion with numbers.
2. `python -m pytest -q` passes.
3. `python research/cost_admissibility_screen.py` OVERALL: PASS.
4. `python research/eval_cryptofunding.py` runs clean; `git status --porcelain data/ config/` empty.

## Scope boundaries

No new trials, rules, thresholds, symbols, cost models. No promotion/rejection. Trial count stays 6.

## Validation commands

```
python research/eval_cryptofunding.py
python -m pytest -q
python research/cost_admissibility_screen.py
```
