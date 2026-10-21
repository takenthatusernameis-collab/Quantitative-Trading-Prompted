# Experiment: bootstrap seed audit (bootstrap_seed_audit)

**Cycle 940.** Deterministic, read-only audit of the seed of every bootstrap call site in `research/` and `src/`.

## Hypothesis reference

None (measurement cycle). The audit was triggered by the Cycle-940 finding that the Cycle-938 `liquidity_001` record published an unreproducible Deflated Sharpe Ratio.

## Method

- every `.py` file under `research/` and `src/` is parsed with `ast`;
- every call to `compute_dsr`, `compute_psr` and `block_bootstrap_sharpe` (the bootstrap entry points whose `seed` defaults to `None`) is located;
- a call is **seeded** when it supplies a `seed` keyword (or the seed's positional slot) whose value is not the literal `None`;
- the audit **fails closed** when a candidate evaluator (`research/*_evaluation.py`) holds an unseeded call.

## Result

| Quantity | Value |
|---|---|
| Bootstrap call sites scanned | 55 |
| Unseeded call sites | 4 |
| Candidate evaluators with an unseeded call | 0 |

- `repository_parses`: PASS -- every python file under research/ and src/ parses
- `candidate_evaluators_seed_every_bootstrap`: PASS -- no unseeded bootstrap call in a candidate evaluator
- `bootstrap_call_sites_found`: PASS -- 55 bootstrap call sites scanned

## Reproduction commands

```bash
python research/bootstrap_seed_audit.py
python -m pytest -q tests/test_bootstrap_seed_audit.py
```
