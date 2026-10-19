# Next Agent Task: Cycle 867 — promotion-criteria feasibility on the frozen candidate's long-sample backtest

## Context

- Committed paper record: 449 daily sessions, 2025-01-02 → 2026-10-16, 7-ETF universe (SPY, QQQ, IWM, TLT, GLD, EFA, EEM), net-of-cost. Decision **NO-GO**; failed gates `rolling_63d_sharpe` (-0.211884) and `psr` (0.684041).
- Cycle 866 (read-only, `research/reports/rolling_63d_gate_refresh_001.md`) established, from the committed record alone:
  - the rolling 63d Sharpe gate passes in **287 of 387** windows on this record (74.16%); the current value sits at the 8.53 percentile; the current failing run is 5 windows; historical recovery lag median 9, max 36 windows;
  - the drawdown gates are **not** binding: worst rolling 63d max DD on record -4.98574%, 0 breaches in 387 windows, 10.0143 pp of headroom;
  - the rolling gate is a **symptom**: the 444-session record truncated at the last passing window evaluates to `rolling_63d_sharpe` 0.935578 PASS, `psr` 0.762425 FAIL → **INCONCLUSIVE**. Clearing the rolling gate alone can never yield "GO";
  - the **PSR gate is the decisive constraint**: it needs an observed Sharpe of 2.552996 at the current SE 0.690150, and Cycle 865 showed 252–504 further sessions at the record mean to get there — far beyond a practical research cadence.
- The paper record is 449 sessions long; the committed raw cache reaches much deeper (EFA from 2001-08-27, EEM from 2003-04-14, DBC from 2006-02-06; the 7-ETF universe therefore supports a multi-thousand-session sample from ~2004). The repository's own promotion machinery can therefore be tested on a **long sample of the same frozen candidate** instead of on a short prospective record.
- The PSR target 1.4178 is the recorded backtest baseline, but the backtest *return series* is not stored in the repository (`config/promotion_gates.yaml`, `sharpe_convention.backtest_baseline_scale` note), so the baseline has never been re-derived against the current code and the current gate table.

## Objective

Read-only feasibility test of the **promotion criteria themselves** on the frozen candidate's long-sample backtest:

1. Re-run the frozen candidate `tsmomentum_spytrend_001` (`config/simulation_candidate_001.yaml`) over the longest feasible window supported by the committed raw cache, using the repository's own engine and cost model, with no network access.
2. Evaluate the **same** gate table (`config/promotion_gates.yaml`, canonical convention `arithmetic_annualized_rf0`) on that long-sample net-of-cost series, and report the full gate table, the PSR, the bootstrap SE and the sample length.
3. Answer the decision-relevant question: **is the PSR gate attainable for this strategy family at all?** i.e. does a long sample of the same strategy clear the observed-Sharpe-vs-1.4178 comparison, or is the criterion unattainable for this return series (low Sharpe-to-dispersion ratio) regardless of sample length?
4. State the consequence for the research loop in one sentence: if the long sample also fails, the incumbent is not promotable in principle and the next cycle must move to a different candidate family; if it passes, the paper record's shortfall is a sample-length/slow-start effect that is worth continuing to collect.

## Acceptance Criteria

1. Report `research/reports/promotion_feasibility_backtest_001.md` containing: the exact sample definition (start/end dates, session count, warm-up handling, universe, cost model, data source and SHA-256 of the raw files used), the full gate table with the canonical Sharpe/PSR/SE/DD values, the recorded-baseline comparison, the answer to acceptance criterion 4 below, and explicit falsification conditions.
2. Script `research/promotion_feasibility_backtest.py` — deterministic, re-runnable, and **read-only with respect to `data/`**: it must not write into `data/raw` or `data/processed`; any intermediate series goes in memory or to a scratch directory outside the repository. It must print its own `OVERALL: PASS/FAIL` summary and the sample it used.
3. **Baseline tie-back (the correctness check):** either the long-sample backtest Sharpe on the recorded backtest-baseline scale (`backtest_sharpe_ratio`, CAGR − 2% rf) **reproduces the recorded baseline 1.4178 within a stated tolerance**, or the deviation is **quantified and explained** (window, warm-up convention `overlay_warmup`, cost model, rebalance convention) — with the number the deviation comes from. Silently accepting a different sample is not acceptable.
4. **Explicit answer, with numbers:** the report states whether the long-sample PSR reaches the 0.95 gate and what observed Sharpe / SE / sample length would be required if it does not; and it states the consequence for the incumbent (`not promotable in principle` vs `short prospective record`).
5. **Verification:** `python research/promotion_feasibility_backtest.py` exits 0 with `OVERALL: PASS`; `python research/rolling_63d_gate_refresh.py` still exits 0 with `OVERALL: PASS`; `python -m pytest -q` passes; `git status --porcelain data/` is empty before and after.

## Scope & Constraints

- Read-only with respect to `data/`, `config/`, `src/` and every threshold: no change to the gate table, the Sharpe convention, the strategy parameters, the cost model, the universe or the promotion rules.
- No network access for the backtest: the run must use the committed raw cache only. If the repository's fetch path would reach the network, it must be bypassed or the run must be reported as blocked.
- No new dependencies, no infrastructure, no workflow/agent changes, no live trading.
- The loop stays non-recursive: this task must not dispatch the workflow or start further agent sessions.
- No fabricated numbers: if the backtest cannot be re-run (engine error, missing history, runtime), record the exact blocker and stop short of any feasibility claim; a documented blocker is an acceptable outcome, a fabricated table is not.
- Deterministic: same inputs → same outputs; report the reproduction command.

## Validation Commands

```bash
python research/promotion_feasibility_backtest.py
python research/rolling_63d_gate_refresh.py
python research/sharpe_convention_audit.py
python -m pytest -q
git status --porcelain data/
```

## Evidence Artifacts

- `research/reports/promotion_feasibility_backtest_001.md` (new)
- `research/promotion_feasibility_backtest.py` (new)
- `research/reports/rolling_63d_gate_refresh_001.md` (Cycle 866, unchanged)
- `data/processed/paper_trading_state.yaml`, `data/raw/*.parquet` (read-only; must be byte-identical afterwards)

## Handoff

- Changed: `research/rolling_63d_gate_refresh.py` (new read-only tool), `research/reports/rolling_63d_gate_refresh_001.md` (new), `tests/test_rolling_63d_gate_refresh.py` (6 new tests), `README.md` (Cycle 866 entry), `NEXT_AGENT_TASK.md` (this file).
- Verified: `python research/rolling_63d_gate_refresh.py` → OVERALL: PASS (11/11), exit 0, state + 19 raw parquet files SHA-256 byte-identical before/after; canonical full-period Sharpe re-derived as 1.748401; the four numeric gates recompute to 0.000e+00 against the production values; `python research/sharpe_convention_audit.py` → gate table reproduced (449-session NO-GO, 444-session INCONCLUSIVE); `python research/go_no_go_evaluation.py` → side_effect_free True, evaluation_deterministic True, NO-GO; `python -m pytest -q` → 67 passed in 73.37s; `git status --porcelain data/` empty.
- Unresolved: the PSR gate remains the decisive constraint for the incumbent (needs observed Sharpe 2.552996 at SE 0.690150, i.e. 252–504 further sessions at the record mean); whether the criterion is attainable for this strategy family at all is untested and is the subject of Cycle 867.
- Failed approaches: none new this cycle. The rolling-window forward projection (Cycle 863/864) and the PSR continuation-horizon grid (Cycle 865) were left unchanged; Cycle 866 deliberately produced record-history evidence (base rate, headroom, computed counterfactual) rather than another projection.
- Next task: Cycle 867 as specified above.
