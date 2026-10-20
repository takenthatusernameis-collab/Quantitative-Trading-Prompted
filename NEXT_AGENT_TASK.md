# NEXT_AGENT_TASK.md

## Cycle 912 — Data readiness and cost inventory: real data and costs actually available in the repository (opportunity shortlist)

### Context

The walk-forward fold-sensitivity sequence is complete:
- Cycle 908: `csmomentum_001` under non-overlapping folds — Rejected/Failed survives (gate 1 still fails).
- Cycle 909: `sectorrotation_001` under non-overlapping folds — Rejected/Failed survives.
- Cycle 910: `tsmomentum_spytrend_001` (incumbent, the only published walk-forward PASS) under non-overlapping folds — PASS survives, margin grows (+0.0473 -> +0.4850).
- Cycle 911 (this cycle): the incumbent's published walk-forward mean (0.9473) decomposes into phase A (odd folds, mean 1.3850, gate 1 PASS) and phase B (even folds, mean 0.5096, gate 1 FAIL); the two thin-trade folds (12: 2 trades, -21.8299; 13: 8 trades, -0.2665) do not by themselves change gate 1 (both excluded -> mean 1.4689, PASS). Published PASS is **NOT phase-stable**.

The incumbent sensitivity work is concluded: no further TSMOM/regime/universe variations on `tsmomentum_spytrend_001` (per its own guidance, the next cycle must explore a different structural mechanism). Per AGENTS.md's strategic priority order, the next step is **data readiness and integrity**: inventory the real historical observations, timestamps, point-in-time universe membership, history depth, and independently checkable provenance actually available in the repository, then score plausible candidate segments against AGENTS.md criteria (a) data quality/access, (b) plausible structural explanation, (c) expected return after costs, (d) robustness/statistical power, (e) liquidity/capacity, (f) automation burden, (g) diversification from existing research — rejecting anything explained by bad data, stale prices, survivorship/lookahead bias, omitted costs, extreme turnover, or illiquidity.

Existing research scaffolding to reuse (read-only, no new dependencies): `research/collect_binance_crypto_funding.py`, `research/eval_cryptofunding.py`, `research/gate_false_negative_rate.py`, `research/drift_persistence_report.py`, `config/`, `data/raw/` (the committed parquet cache and any crypto funding data present), `requirements.txt` cost parameters (`get_cost_params` in `src/backtest/engine.py`).

### Objective

Produce a bounded, evidence-based data-and-cost inventory plus a scored candidate-segment shortlist for the next research cycle. No backtest is executed, no candidate is promoted, nothing under `data/` or `config/` is changed, and no committed artifact is modified.

### Acceptance criteria

1. **New document** `research/reports/data_cost_inventory_001.md` (deterministic, no timestamps) containing:
   - An inventory of every real data source actually present in the repository: for each, the path, symbol universe, date range (first/last), frequency, row count, point-in-time treatment (timestamp semantics, look-ahead exposure), provenance (how to independently verify), and any gaps/stale prices observed.
   - The cost model actually available/credible: fees, bid-ask spread assumptions, slippage, funding, borrow, roll — sourced from `config/` and `src/backtest/engine.py` (`get_cost_params`, `get_risk_free_rate`), not invented.
   - A scored shortlist of plausible candidate segments (e.g., crypto perpetual funding/carry, basis compensation, market-session effects, documented rebalancing flows, and any others the data supports), each scored against criteria (a)-(g) above with the data actually observed.
   - Explicit rejection reasons for any segment the data does not support (bad data, stale prices, survivorship/lookahead bias, omitted costs, extreme turnover, illiquidity, infeasible execution).
   - Reproduction commands: how to re-derive the inventory from the repository.
2. **New experiment record** `research/experiments/data_cost_inventory_001.md` referencing the report, data used, configuration, and reproduction commands.
3. **No modifications** to any committed artifact; nothing under `data/` or `config/` written; fetcher/network not used for new data (read-only inspection of existing cache only).
4. **Tests** `tests/test_data_cost_inventory_001.py` checking:
   - both artifacts exist,
   - the report's inventory covers every file under `data/raw/` (parquet files and any crypto funding files),
   - cost figures in the report match `get_cost_params()`/`get_risk_free_rate()` from `src/backtest/engine.py`,
   - `data/` and `config/` byte-identical before and after the report generation,
   - committed artifacts byte-identical before and after,
   - determinism: two consecutive generations produce identical files.
5. **Verification commands** (must all pass):
   ```
   python research/data_cost_inventory_001.py   # if a generator script is used; otherwise the report is produced directly and verified by tests
   python -m pytest -q tests/test_data_cost_inventory_001.py
   git status --porcelain data/
   git diff --stat src/ config/ research/experiments/ research/reports/
   ```

### Scope boundaries
- Data readiness and integrity only; no backtest, no candidate execution, no promotion, no gate changes.
- Read-only: no fetcher/network calls for new data; inspect the existing committed cache only.
- Do not change `src/`, `config/`, `data/`, or any committed artifact.
- Keep deterministic: no timestamps in the report or experiment record.
- One narrow task: inventory + scored shortlist + rejections; nothing broader.

### Notes
- The tooling pattern to follow: read-only audit tools such as `research/tsmomentum_walkforward_embargo_audit.py` (cache-only, fingerprint read-only checks, `tracked_artifact_hashes`) and `research/csmomentum_common_inception_audit.py` (cache fingerprint per symbol).
- Operational note: the worker image ships without the repository's Python dependencies — install from `requirements.txt` (`python3 -m pip install -r requirements.txt`) before running tools or tests. The full suite takes ~10 minutes; run it in the background and poll, since the invocation watchdog terminates a worker whose child is silent for 600 s. Running the suite re-stamps `research/reports/sectorrotation_long_sample_feasibility_001.md` with the current commit hash (pre-existing side effect); revert that one-line stamp so `git diff --stat src/ config/ research/experiments/ research/reports/` stays empty.
