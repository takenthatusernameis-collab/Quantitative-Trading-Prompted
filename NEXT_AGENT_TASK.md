# Cycle 943 — Freeze hypothesis + config for cryptofunding_001 carry candidate

## Context
Cycle 942 (this session) found the full Cycle 942 acceptance scope (hypothesis + frozen config + data inventory + evaluation script + tests + run + reports + handoff) exceeds one session. Data readiness is already established: committed Binance carry paths (`data/processed/crypto/{BTC,ETH}USDT_carry_path.parquet`, 2,464 daily rows each, 2020-01-02..2026-09-30) with SHA-verified provenance (`research/reports/binance_crypto_manifest.json`). Existing `research/eval_cryptofunding.py` (Cycle 892) contains the reference cost model and metric conventions. The four ETF shortlist candidates are closed; crypto carry is structurally distinct.

## Objective
Freeze a pre-registered hypothesis and config for `cryptofunding_001` (spot-long/perp-short funding carry, BTC+ETH, delta-neutral, daily rebalance) following AGENTS.md hypothesis-first requirements, with explicit cost model (3 bp/unit default unless justified). No evaluation run yet.

## Acceptance criteria
- `research/hypotheses/cryptofunding_001.md` with all required elements.
- `config/cryptofunding_001.yaml` frozen, including cost model.
- `git status --porcelain data/ config/` shows only the new config (expected).
- Validation: `python -m pytest tests/test_shortlist_gross_edge_001.py -q` still passes.

## Scope boundaries
- No evaluation script, tests, or runs this cycle.
- No data changes.
- Research/backtest only.

## Handoff notes
- Next cycle implements `research/cryptofunding_001_evaluation.py` + tests following `research/leadlag_001_evaluation.py` patterns (frozen-config assertion, cache-only, SHA checks, walk-forward purge/embargo, realized turnover/cost drag, benchmark-relative accounting) and runs it.
