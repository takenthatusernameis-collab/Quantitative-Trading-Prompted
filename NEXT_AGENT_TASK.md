# Cycle 944 — Implement cryptofunding_001 evaluation script and tests (cache-only)

## Context
Cycle 943 froze `research/hypotheses/cryptofunding_001.md` (pre-registered) and `config/cryptofunding_001.yaml` (frozen, cost model with 3 bp/unit default plus slippage/capital charge). Committed Binance carry paths exist: `data/processed/crypto/{BTC,ETH}USDT_carry_path.parquet` (2,464 daily rows each, 2020-01-02..2026-09-30), SHA-verified via `research/reports/binance_crypto_manifest.json`. Prior evaluations (Cycles 891-896) established it is an exploratory signal (not promoted) under realistic costs; this cycle implements a reproducible evaluation following repository patterns.

## Objective
Implement `research/cryptofunding_001_evaluation.py` and `tests/test_eval_cryptofunding_001.py` following `research/leadlag_001_evaluation.py` patterns (frozen-config assertion, cache-only, SHA checks, walk-forward with purge/embargo, realized turnover/cost drag, benchmark-relative accounting), run the evaluation, persist experiment/report outputs, and update hypothesis status if warranted. No new data fetch.

## Acceptance criteria
- `research/cryptofunding_001_evaluation.py` exists and reads only cached data; asserts frozen config values.
- `tests/test_eval_cryptofunding_001.py` exists and passes.
- Evaluation run produces:
  - `research/experiments/cryptofunding_001_evaluation.md`
  - `research/reports/cryptofunding_001_evaluation.md`
- `python research/cryptofunding_001_evaluation.py` prints `OVERALL: PASS` (or equivalent deterministic pass marker).
- `python -m pytest tests/test_eval_cryptofunding_001.py -q` passes.
- `git status --porcelain data/ config/` unchanged by evaluation (cache-only).
- Handoff updates `research/hypotheses/cryptofunding_001.md` Status/Verdict with evidence links and measured metrics (or explicitly states no change) without relaxing gates.

## Scope boundaries
- Cache-only; no network fetches.
- No changes to promotion gates or cost model assumptions without explicit justification and evidence.
- Research/backtest only.

## Validation commands
- `python research/cryptofunding_001_evaluation.py`
- `python -m pytest tests/test_eval_cryptofunding_001.py -q`
- `python -m pytest tests/test_shortlist_gross_edge_001.py -q`

## Handoff notes
- Follow patterns from `research/leadlag_001_evaluation.py`: load frozen config, verify SHA/checksums against manifest where applicable, enforce cache-only, compute realized turnover and cost drag per unit weight change, use walk-forward with purge/embargo, report benchmark-relative results, and write experiment+report with reproduction commands.
- Preserve prior Cycle 891-896 findings; do not rewrite reconciled numbers. If metrics differ due to construction details, explain reconciliation explicitly.
- Keep work bounded and restart-safe.
