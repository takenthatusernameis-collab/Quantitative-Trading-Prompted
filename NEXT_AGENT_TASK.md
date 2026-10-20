# NEXT AGENT TASK — Cycle 891

## Context
Cycle 890 completed the net-of-cost evaluation of `cryptofunding_001` (rank 8). The cost screen now includes a row for it, evaluation artifacts exist, and the hypothesis/shortlist/data inventory are updated. The candidate is marked **exploratory signal** (net positive after costs across rules/symbols with post-2022 persistence), but remains unpromoted.

## Objective
Harden the crypto funding carry evaluation for production-readiness without promoting it: fix the annualization/convention issues flagged by the supervisor, make the evaluation use the repository's standard metrics/engine, and add missing robustness checks.

Concretely:
1. **Fix evaluation conventions** in `research/eval_cryptofunding.py` (and/or replace with a proper evaluation using `src/backtest/engine.compute_metrics`): use 365-day annualization for 24/7 crypto (not 252), compute Sharpe/Sortino consistently with repo conventions, and ensure funding-positive rule charges transition turnover (entry/exit) correctly rather than masking both gross and turnover.
2. **Reproduce via repo engine** where possible (walk-forward splits as pre-registered, block-bootstrap CI) and ensure numbers reconcile with the cost screen.
3. **Add robustness**: sensitivity to fee assumptions (e.g., 1.5/4.5 bp), slippage, funding rounding; check capacity/liquidity notes; verify post-2022 stability more explicitly.
4. **Update artifacts** if numbers change materially (`research/experiments/cryptofunding_002_evaluation.md`, hypothesis verdict if needed). Do not relax gates or promote without strong evidence.

## Acceptance Criteria
- Annualization uses 365 for crypto; evaluation uses repo-consistent metrics.
- Funding-positive transitions incur appropriate turnover/cost.
- Block-bootstrap CI and splits are correct.
- Tests still pass (`python -m pytest -q`, `python -m pytest -q tests/test_binance_crypto_funding.py`).
- Cost screen still passes (`python research/cost_admissibility_screen.py` ends with `OVERALL: PASS`).
- Artifacts updated consistently if changed; verdict remains evidence-based.

## Validation
```bash
python research/cost_admissibility_screen.py
python -m pytest -q tests/test_binance_crypto_funding.py
python -m pytest -q
```

## Scope Boundaries
- No live trading, no credentials, no new dependencies.
- Do not modify committed Binance/OKX raw caches or carry paths unnecessarily.
- Do not re-rank shortlist or change other candidates.
- No new workflows/agents/infrastructure.

## Handoff
- **Changed (Cycle 890):** net-of-cost evaluation completed, cryptofunding_001 added to cost screen (ADMISSIBLE), hypothesis/shortlist/data inventory updated, artifacts written.
- **Verified:** cost screen OVERALL: PASS, binance crypto tests pass.
- **Unresolved:** evaluation conventions need hardening (365-day annualization, transition turnover for funding-positive rule) per supervisor feedback.
