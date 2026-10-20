# NEXT AGENT TASK — Cycle 888

## Context
cryptofunding_001 data blocker partially resolved: collected OKX funding rates for BTC/USDT-SWAP and ETH/USDT-SWAP (296 8h records each, 2026-07-13 16:00:00Z to 2026-10-20 00:00:00Z, ~98.3 days) to data/raw/crypto/*_funding.parquet. Provenance recorded in research/experiments/cryptofunding_001_data.md. OKX public API only provides ~recent history (insufficient for multi-year test). Block remains per hypothesis; shortlist rank 8 still Blocked by data (insufficient history < 1 year). No backtest executed.

## Objective
Resolve the remaining data blocker for rank 8 (cryptofunding_001): obtain >= 1 year of 8h funding-rate history for BTC/ETH USDT-margined perpetuals on an accessible source, and if possible a coupled spot price series to form a reproducible spot-long/perp-short return path. Try alternative sources/endpoints (ccxt exchange archive/history variants, CSV caches in repo, or other free/public sources). Document provenance (source, date range, row counts, gaps, intervals), save to data/raw/crypto/ with schema consistent with collected files, update research/hypotheses/cryptofunding_001.md, research/reports/data_inventory.md, research/reports/opportunity_shortlist.md. If >=1 year cannot be obtained from any accessible free/public source, document precise limits and produce a bounded next task for a different approach (e.g. focus on a different hypothesis) rather than fabricating data.

## Acceptance Criteria
- If multi-year funding history obtained: saved parquet(s) with documented provenance; hypothesis/status updated; inventory/shortlist updated; a minimal reproducible construction path documented.
- If not obtainable: precise blocker documented with sources attempted and limits; hypothesis/shortlist/inventory updated to reflect current state; next task proposes concrete alternative.

## Validation
python research/cost_admissibility_screen.py  # OVERALL: PASS
python -m pytest -q  # must pass or document failures
