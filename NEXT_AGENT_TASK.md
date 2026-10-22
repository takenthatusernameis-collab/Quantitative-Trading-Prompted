# Cycle 947 — New evidence-based market-opportunity search (data-first, shortlist from actual repo)

## Context

Cycle 946 backfilled `README.md` with Cycles 936–945 and confirmed:
- The Cycle-934 shortlist is **fully exhausted**: `reversal_001`, `pairs_001`, `liquidity_001`, `leadlag_001` are all **Rejected/Failed**.
- `cryptofunding_001` remains an **exploratory signal (not promoted)** and fails the trade-count gate under every cost model (<100 pooled OOS round trips).
- The incumbent `tsmomentum_spytrend_001` stays **Credible Candidate / NO-GO** (with canonical Sharpe convention and enforced promotion gates).
- `sectorrotation_001` remains **Rejected/Failed** on its own pre-registered falsification condition.

The repository now has a correct month-end rebalance path (`src/backtest/rebalance.py`) and enforced promotion gates (`config/promotion_gates.yaml`). A data/cost inventory (Cycle 912) exists, but no systematic market-opportunity search from first principles has been executed against the actual cached data and the real 3 bp/unit cost model.

## Objective

Conduct a new, bounded, evidence-based search for plausible trading opportunities using **only the data already cached in `data/raw/`** and the **actual cost model** implemented in `src/backtest/engine.py` (1.0 bp commission + 2.0 bp slippage = 3.0 bp per unit weight change; RF 2.00%/yr). Produce a short, scored shortlist with explicit rejection reasons for non-viable segments, and prepare **at most one** concrete candidate for pre-registration (or zero if nothing meets minimum bar). Do **not** re-score closed candidates.

## Acceptance criteria

- Read-only inventory of **all files under `data/raw/`** (counts, date ranges, frequencies, asset classes, gaps). Distinguish sub-daily from daily; note missing/duplicate timestamps.
- Build a scored shortlist against AGENTS.md criteria (a)-(g) using only measured facts. For each rejected segment, state an explicit, evidence-based reason (no data / unobservable prices / insufficient history / omitted costs make it infeasible / look-ahead / gate failures / illiquidity / etc.).
- If any segment appears plausible on paper, do **not** tune freely — pre-register a hypothesis in `research/hypotheses/` with: mechanism, expected direction/magnitude, horizon/universe, features/data sources, entry/exit, benchmark, confounders, falsification conditions, and a **concrete cost model** (must cover bid-ask/borrow/roll/impact/latency if relevant; if not measurable from cached data, mark as **blocked**).
- Run only the smallest necessary read-only checks to score; **no full grid search, no parameter sweep across multiple candidates**.
- Produce `research/reports/market_opportunity_search_001.md` and `research/experiments/market_opportunity_search_001.md` with all numbers re-derived.
- If pre-registering a candidate, write `research/hypotheses/<name>.md` and a minimal config in `config/` (or explicitly say "no candidate pre-registered"). Do **not** run a full walk-forward evaluation this cycle.
- `git status --porcelain data/ config/` empty. No changes to `src/`, closed experiment records, or promotion gates/thresholds.
- `python -m pytest -q` passes (or only pre-existing failures unchanged; report count).

## Scope boundaries

- **Data-first**: use only `data/raw/`. Do not call external fetchers/networks. Do not download data.
- **Cost-realistic**: use the actual model in code; do not assume free trading. If a plausible mechanism requires costs not present/measurable in cache, reject or block.
- **No re-opening**: do not re-evaluate `reversal_001`, `pairs_001`, `liquidity_001`, `leadlag_001`, `sectorrotation_001`, or `cryptofunding_001`.
- **Narrow**: at most one pre-registered candidate. Prefer "reject/block with evidence" over expanding scope.
- **Deterministic**: no randomness in inventory/scoring unless seeded and recorded.

## Validation commands

- `python -m pytest -q`
- `git status --porcelain data/ config/`
- `git diff --stat` (expect only new reports/experiments/hypotheses/config if pre-registered)

## Handoff notes

- Start from `data/raw/` inventory (file list + date ranges). Cross-check against Cycle 912 inventory but verify by direct inspection.
- Score segments: equities (sectors/indexes), rates/commodities/futures, crypto spot/perps/funding (note sub-daily), volatility, etc. Be explicit about capacity/liquidity and automation feasibility.
- If nothing clears a high bar, the correct output is a **rejection list with evidence**, not a weak candidate.
- Next task should flow from concrete evidence (either a pre-registered candidate ready for bounded evaluation, or a specific blocked question that needs new data to answer).
