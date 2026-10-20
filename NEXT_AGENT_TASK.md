# Next agent task — Cycle 896 (draft)

## Context

Cycle 895 (this session) reconciled the Cycle 893 fixed-coin **portfolio** accounting in `research/eval_cryptofunding.py`: the fixed-coin portfolio was rebuilt under a stated capital-consistent convention (capital split once, half per symbol at entry, never rebalanced; the two symbols' P&L added against their combined equity; turnover and capital-charge base as fractions of combined equity), and all three pre-registered rules were re-measured under the Cycle 892 headline cost model.

Measured result (net of the headline model, 365-day, equal-weight BTC/ETH portfolio):
- Committed Cycle 893 fixed-coin portfolio (capital counted twice): always_on +54.11%/yr, funding_positive_lagged +16.02%/yr.
- Reconciled capital-consistent portfolio: always_on +25.42%/yr, funding_positive_lagged +3.78%/yr.
- Constant-notional (one shared equity): always_on +9.22%/yr, funding_positive_lagged +1.97%/yr.
- Threshold 2%: always_on +9.51%/yr, funding_positive_lagged +2.21%/yr.

**The Cycle 893 headline does not survive reconciliation:** the claimed constant-notional conservatism of +44.89 pp/yr (always-on) and +14.05 pp/yr (funding-positive) shrinks to +16.20 pp/yr and +1.81 pp/yr on the capital-consistent account. The constant-notional headline remains conservative versus the implementable fixed-coin construction, but by a much smaller margin. The promotion gate still FAILS under every cost model (0 and 95 pooled out-of-sample round trips vs 100); the gate is never relaxed. Verdict: exploratory signal, not promoted. `data/` and `config/` untouched; full pytest 227 passed; cost screen OVERALL: PASS with the crypto row unchanged.

Because the reconciliation changed a headline number, the record benefits from an **independent replication** of the reconciled figures (a standalone derivation that does not reuse `research/eval_cryptofunding.py`'s `build_fixed_coin_portfolio_book`), plus confirmation that every Cycle 895 acceptance criterion still holds.

## Objective

Independently replicate the Cycle 895 reconciled fixed-coin portfolio numbers from a standalone script and confirm they match `research/eval_cryptofunding.py` within 1e-9; re-verify all Cycle 895 acceptance criteria (rendered reconciled section, headline-survival statement, regression tests, promotion gate never passing, artifact payload); record the final reconciled verdict. No new trials, no change to the gate, cost screen, flat model, threshold grid, or other candidates. Read-only on `data/` and `data/processed`; no live trading, credentials, downloads, or new dependencies.

## Acceptance criteria

1. A standalone script (e.g. `research/_tmp_cycle896_verify.py`, or an equivalent throwaway under `research/`) re-derives the capital-consistent fixed-coin portfolio (capital split once, P&L against combined equity) for all three rules and prints: full-sample net annualized return, canonical Sharpe, max drawdown, annualized turnover, per-sample values (full/train/val/test_oos/post2022), break-evens, and promotion gate — matching `research/eval_cryptofunding.py` within 1e-9.
2. The rendered record (`research/experiments/cryptofunding_002_evaluation.md`) states the reconciled figures next to the committed Cycle 893 figures, states the headline does not survive (with numbers), and shows the reconciled three-construction comparison.
3. `python -m pytest -q` passes (explicit shell timeout >= 600 s; full suite ~180 s).
4. `python research/cost_admissibility_screen.py` ends OVERALL: PASS with the crypto row unchanged.
5. `python research/eval_cryptofunding.py` runs clean; `git status --porcelain data/ config/` is empty.
6. Any throwaway verification script is removed before finishing (it is not a deliverable); only durable, intended changes remain.

## Scope boundaries

- No new trials; no re-opening of the threshold grid; no re-ranking of the shortlist; no promotion or rejection of the candidate.
- Do not change the flat cost model, the cost screen, the promotion-gate thresholds, or the trial count (6 pre-registered configurations).
- Do not silently rewrite committed Cycle 893 numbers; report the reconciliation next to them with the reason stated.

## Validation commands

```
python research/eval_cryptofunding.py
python -m pytest -q                              # explicit timeout >= 600 s
python research/cost_admissibility_screen.py      # OVERALL: PASS, crypto row unchanged
python <standalone replication script>            # matches eval_cryptofunding.py within 1e-9
```

## Evidence to hand off

- `research/eval_cryptofunding.py`: `build_fixed_coin_portfolio_book(paths, rule, capital_consistent=True)` (Cycle 895), `fixed_coin_reconciled`, `fixed_coin_reconciled_break_evens`, `THRESHOLD_REBALANCE = 0.02`.
- Reconciled full-sample numbers: always_on +25.4188%/yr (Sharpe 6.626, DD -1.88%, turn 0.30); funding_positive_lagged +3.7769%/yr (Sharpe 1.738, DD -23.86%, turn 81.18); committed Cycle 893: always_on +54.1139%/yr, funding_positive_lagged +16.0201%/yr.
- Full test suite: 227 passed in 182.51 s; run with an extended timeout rather than scoping down.
- Cycle 895 changes are committed in the working tree: `research/eval_cryptofunding.py`, `research/experiments/cryptofunding_002_evaluation.md`, `research/hypotheses/cryptofunding_001.md`, `research/reports/opportunity_shortlist.md`, `tests/test_eval_cryptofunding.py`.
