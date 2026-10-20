# NEXT_AGENT_TASK.md

## Cycle 913 — The cost break-even of the promotion-gate statistic: how much execution-cost headroom does each published walk-forward record actually have?

### Context

Cycle 912 completed AGENTS.md's first strategic priority (data readiness and integrity) and published the inventory in `research/reports/data_cost_inventory_001.md` (tool: `research/data_cost_inventory_001.py`; record: `research/experiments/data_cost_inventory_001.md`). Its measured findings that drive this cycle:

- The repository's **entire** execution-cost model is a flat **3.0 bp per unit of weight change** (1.0 bp commission + 2.0 bp slippage, from `src/backtest/engine.py:get_cost_params()` / `config/settings.yaml`). A scan of every leaf key of every file in `config/` shows **six cost components have no configuration key at all**: bid-ask spread, borrow/short-sale cost, futures roll cost, market impact, latency, margin.
- The committed cost screen (`research/cost_admissibility_screen.py`, `research/reports/cost_admissibility_screen_001.md`) publishes a **break-even cost per unit** for six candidates (incumbent 106.75 bp/unit, `csmomentum_001` 402.32, `sectorrotation_001` 231.71, `macroregime_001` 180.27, `calendar_effects_001` 11.16, `overnight_capture_001` 1.74), but that break-even is solved on the **aggregate** full-sample gross-versus-turnover statistic, not on the statistic the promotion gate actually uses.
- The promotion gate uses the **walk-forward mean of the fold-level out-of-sample Sharpe** (gate 1: ≥ 0.9; gate 2: positive fold rate ≥ 0.5; gate 3: > 100 pooled OOS trades). The **cost level at which each of those gates flips on the fold-level path has never been computed for any candidate.** The incumbent's published PASS has a margin of only **+0.0473** on the published design (mean 0.9473) and its even-fold phase sits at **0.5096** (gate 1 FAIL, Cycle 911), so how much cost headroom the PASS actually has is an open, decision-relevant question.
- Per AGENTS.md, this is **net capture feasibility** (priority 3) for the three candidates that have a committed fold-level walk-forward record *and* reusable fold-rebuild tooling: `tsmomentum_spytrend_001` (incumbent), `csmomentum_001`, `sectorrotation_001`.

This cycle measures a **cost boundary**, not a new strategy: the signal, folds, sample, universe and gate thresholds are read-only inputs, and no candidate is selected, promoted or re-litigated.

### Objective

For each of the three candidates above, recompute the promotion-gate statistic as a function of the per-unit cost (holding everything else fixed) and publish, per candidate: (i) the gate statistic at the committed 3.0 bp/unit, (ii) the per-unit cost at which each of the three gates flips, solved on the same path, and (iii) a **measured** bid-ask floor from the committed OHLC cache, so the boundary is placed against the market's own cost floor rather than against an assumption. No backtest design change, no candidate execution decision, no promotion.

### Acceptance criteria

1. **New tool** `research/cost_gate_break_even_audit.py` — read-only, cache-only (no fetcher, no network), deterministic, prints `OVERALL: PASS` and exits 0. It must:
   - reuse the existing fold-rebuild machinery rather than re-implementing it: `research/tsmomentum_walkforward_embargo_audit.py`, `research/csmomentum_walkforward_embargo_audit.py`, `research/sectorrotation_walkforward_embargo_audit.py` (their `evaluate_design` / published-design rebuild and gate tables);
   - extend that machinery **additively** if a cost override is needed (a per-unit cost parameter), leaving the default path unchanged — proven by the regression check below;
   - sweep the per-unit cost over a **pre-registered** grid and solve each gate flip by bisection on the same path (the gate statistics are monotone enough in the cost for bisection; if a candidate's statistic is not monotone, report the observed non-monotonicity instead of forcing a root);
   - measure the bid-ask floor from the committed cache: per symbol, the relative daily range `(High - Low) / Close` at **pre-registered percentiles** (10, 25, 50), stating clearly that the daily range is an **upper bound** on the traded spread (it contains intraday volatility), so the derived level is a conservative bound and not a spread estimate.
2. **New report** `research/reports/cost_gate_break_even_001.md` (deterministic, no timestamps) containing, per candidate: the published walk-forward mean at 3.0 bp/unit (with the published value it must reproduce), the per-unit cost at which gate 1 / gate 2 / gate 3 flips, the measured bid-ask floor table, and the explicit verdict — does the published PASS survive a realistic cost floor, and which gates bind first.
3. **New experiment record** `research/experiments/cost_gate_break_even_001.md` referencing the report, the data used, the configuration, the number of trials (a fixed cost grid, no parameter search), and the reproduction commands.
4. **Regression check (mandatory):** at 3.0 bp/unit the recomputed walk-forward mean OOS Sharpe reproduces the **published** value exactly (≤ 1e-9): `tsmomentum_spytrend_001` 0.9473, `csmomentum_001` 0.697524 (backtest scale) / 0.840389 (canonical), `sectorrotation_001` 0.847243. Any deviation is a failure, not a rounding note.
5. **Pre-registration** (written into the tool and the report *before* the measurement, and enforced by a test): the candidate list, the cost grid and the bisection rule, the spread-proxy percentiles, the unchanged gate thresholds, and the falsification condition — *if the incumbent's published PASS survives a cost level of at least the measured bid-ask floor (times the two legs actually traded), the cost axis is not the binding constraint on the incumbent and this axis is closed.*
6. **No modifications** to any committed artifact; nothing under `data/` or `config/` written; no fetcher/network call for new data.
7. **Tests** `tests/test_cost_gate_break_even_audit.py` checking at least:
   - both artifacts exist;
   - the published values are reproduced at 3.0 bp/unit (criterion 4);
   - the report's cost figures are consistent with `get_cost_params()` / `get_risk_free_rate()` from `src/backtest/engine.py`;
   - the gate-flip costs are strictly monotone in the cost (or the non-monotonicity is reported) and the gate-flip cost for gate 1 is ≥ the committed 3.0 bp/unit for a candidate whose net Sharpe is positive;
   - `data/` and `config/` byte-identical before and after the generation;
   - committed artifacts byte-identical before and after;
   - determinism: two consecutive generations produce identical files;
   - the tool fails closed (no output written) when a required input is missing.
8. **Verification commands** (must all pass):
   ```
   python research/cost_gate_break_even_audit.py
   python -m pytest -q tests/test_cost_gate_break_even_audit.py
   python -m pytest -q
   git status --porcelain data/
   git diff --stat src/ config/ research/experiments/ research/reports/
   ```

### Scope boundaries

- Measurement only: no candidate is selected, executed, promoted or re-litigated; no gate, threshold, fold design, sample, universe, signal or parameter changes.
- Do not change `src/`, `config/`, `data/`, or any committed artifact. If the fold-rebuild tools cannot accept a cost override without editing them, copy the needed function into the new tool and record the copy; do not edit the committed tools.
- Do not extend the candidate list beyond the three named above, and do not run the robustness grids, the plateau gates or any parameter search: the cost grid is pre-registered and fixed.
- Keep deterministic: no timestamps in the report or the experiment record.
- One narrow task: the cost boundary of the promotion-gate statistic.

### Notes

- The inventory of Cycle 912 already contains the measured inputs this cycle needs (per-file row counts, date ranges, frequencies, duplicate/missing counts, coverage tiers, the cost-key scan); read `research/reports/data_cost_inventory_001.md` first and reuse `research/data_cost_inventory_001.py` (`build_raw_inventory`, `build_cost_model`, `fingerprint`, `tracked_artifact_hashes`) rather than re-measuring.
- The published cost-screen break-evens (aggregate statistic) must be quoted beside the new fold-level break-evens so the two are not confused.
- The incumbent's phase decomposition (Cycle 911) is the reason the cost axis matters: if the cost axis is not binding, the remaining incumbent weakness is the phase stability of the published PASS and the prospective paper-trading record (a time-bound constraint), and that should be stated as the conclusion.
- Operational note: the worker image ships without the repository's Python dependencies — install from `requirements.txt` (`python3 -m pip install -r requirements.txt`) before running tools or tests. The full suite takes ~10 minutes; run it in the background and poll, since the invocation watchdog terminates a worker whose child is silent for 600 s. Running the suite re-stamps `research/reports/sectorrotation_long_sample_feasibility_001.md` with the current commit hash (pre-existing side effect); revert that one-line stamp so `git diff --stat src/ config/ research/experiments/ research/reports/` stays empty.
