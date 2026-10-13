# Next Agent Task: Cycle 18 — Execute the Frozen C6 Calendar-Effects Evaluation

## Current research state — read first

Cycle 17 has completed the corrected, cache-only C4 evaluation. Do **not** repeat or tune C4.

- C3 (broad 18-ETF cross-sectional momentum): Rejected/Failed on its valid pre-registered test.
- C4 (9 GICS sector ETFs): Rejected/Failed on its first valid execution. Mean OOS walk-forward Sharpe = **0.6944** vs the frozen 0.90 gate; 83.3% positive folds, 158 pooled OOS trades, and 3/3 lookbacks on the plateau check.
- C4's corrected full run: [GitHub Actions run #38418474184](https://github.com/takenthatusernameis-collab/Quantitative-Trading-Prompted/actions/runs/38418474184). The [validated output bundle](https://github.com/takenthatusernameis-collab/Quantitative-Trading-Prompted/actions/runs/38418474184/artifacts/11825760496) includes the full report and generated parquet files.
- The C4 canonical report and cross-momentum consolidation were updated. The defective pre-correction report remains preserved at `research/experiments/sectorrotation_baseline_wf_001_pre-correction.md`.
- Do not optimize C3/C4 against their holdout. Their hypotheses/configs and historical scripts remain unchanged.

## Objective

Execute **Cycle 18 — C6 calendar/rebalancing effects** using the already frozen pre-registration. C6 is an independent, deterministic calendar-timing hypothesis: turn-of-month (TOM) exposure in SPY/QQQ/IWM. Implement, test, run, validate, report the result honestly, and prepare the next task based on the pre-registered decision discipline.

Frozen specification:
- Hypothesis: `research/hypotheses/calendar_effects_001.md`
- Config: `config/calendar_effects_001.yaml`
- Required runner to create: `research/run_cycle18.py`
- Required experiment record: `research/experiments/calendar_effects_baseline_wf_001.md`
- Required strategy-specific artifacts: `data/processed/simulation_calendar_effects_001.parquet`, `data/processed/trades_calendar_effects_001.parquet`, and `data/processed/weights_calendar_effects_001.parquet`.

## Part 1 — validate the frozen design before backtesting

Run these checks first; do not change the pre-registration to make them pass:

```bash
python3 -c "import yaml; yaml.safe_load(open('config/calendar_effects_001.yaml'))"
python3 - <<'PY'
import sys
sys.path.insert(0, '.')
from src.evaluation.walkforward import generate_walkforward_splits

pre_days, post_days = [1, 2, 3], [1, 2, 3, 5, 7, 10]
assert len(pre_days) * len(post_days) == 18
splits = generate_walkforward_splits(
    "2000-05-26", "2026-10-09", 10, 12, 6, 21, 21
)
assert len(splits) == 33, f"expected 33 folds, got {len(splits)}"
expected_first = {
    "train_start": "2000-05-26",
    "train_end": "2010-01-21",
    "test_start": "2010-02-22",
    "test_end": "2011-02-08",
}
expected_last = {
    "train_start": "2015-11-10",
    "train_end": "2025-07-07",
    "test_start": "2025-08-06",
    "test_end": "2026-07-23",
}
for key, value in expected_first.items():
    assert splits[0][key] == value, (key, splits[0][key], value)
for key, value in expected_last.items():
    assert splits[-1][key] == value, (key, splits[-1][key], value)
print("C6 pre-registration checks: PASS (18 configurations, 33 folds)")
PY
```

If any check fails, stop and investigate the mismatch. Do not edit `research/hypotheses/calendar_effects_001.md` or `config/calendar_effects_001.yaml`.

## Part 2 — implement a deterministic, cache-only runner

Create `research/run_cycle18.py`. Read the C6 hypothesis and config line-by-line before coding. Follow established runner/report discipline in the C3/C4 research code, but do not call the network-capable shared data fetcher.

### Data and execution invariants

- Candidate inputs are the tracked caches `data/raw/SPY.parquet`, `data/raw/QQQ.parquet`, and `data/raw/IWM.parquet`; the incumbent TSMOM context benchmark uses its own CORE7 inputs (`SPY, QQQ, IWM, TLT, GLD, EFA, EEM`). Read parquet files locally only.
- Enforce cache preflight **before** evaluation: all expected files exist, are tracked/non-empty/readable, contain `Close`, have unique timestamps, and cover the frozen expected dates. Fail closed on missing/inadequate inputs; no downloads, fallback data, or cache healing.
- C6 candidate history starts on the common calendar, **2000-05-26 through 2026-10-09**. Respect each symbol's pre-inception NaNs. The three-asset candidate calendar has 6,632 trading days.
- Universe: exactly SPY, QQQ, IWM. Exposure is equal-weight 1/3 per ETF during TOM windows and 0 otherwise.
- Baseline is `pre_days=1`, `post_days=3`. The fixed grid is `pre_days=[1,2,3]`, `post_days=[1,2,3,5,7,10]` — exactly 18 combinations. Do not add configurations or select a winner based on test-period performance.
- Build monthly boundary windows on **trading-day positions**, not calendar `is_month_end`/`is_month_start` flags. For each boundary, mark the last `pre_days` trading days of that month and the first `post_days` trading days of the following month. Construct the calendar mask on the full common history and then slice it into train/test folds; do not reset window boundaries within folds.
- The exposure mask is deliberately **not shifted by one day**: the calendar is exogenous and known in advance; it marks the close-to-close returns captured by positions entered at the prior close. Document this convention exactly as the frozen hypothesis specifies.
- Costs are 1 bp commission + 2 bps slippage = 3 bps per unit of absolute weight change; apply them at window boundaries. Cash return is 0%; use the repository's 2% annualized risk-free rate for reported risk-adjusted metrics. No overlay, leverage, borrowing, or added funding assumptions.
- Keep C6 training/validation/test periods and all 33 walk-forward splits exactly as frozen. Fixed parameters across folds; no per-fold re-optimization and no portfolio/cash state carryover from a previous fold.

### Evaluation and diagnostics required

1. Baseline test-period report with annualized return, Sharpe, Sortino, drawdown, trade count, turnover, exposure and tail metrics.
2. Walk-forward baseline with all 33 train/test fold rows and a 33-fold summary. Validate fold/date integrity and fail closed on any missing/non-finite required train/OOS metric.
3. Full 18-configuration grid, baseline rank, and pre-registered plateau check across `pre_days=1,2,3` at `post_days=3`. Use the repository plateau convention: tolerance `max(0.1, 0.10 * abs(baseline test Sharpe))`; at least 2/3 pre-day values must lie within that tolerance of baseline.
4. Benchmarks on the same declared test range and folds: always-invested 1/N basket over SPY/QQQ/IWM using the frozen C3/C4-style convention, and the incumbent TSMOM candidate on CORE7 using its established “slice” test-period and “full” walk-forward warmup conventions. Clearly state that the incumbent is context and its historical 48-fold results are not directly comparable to C6's 33-fold test design.
5. Multiple-testing diagnostics at the true frozen count **N=18**: DSR, PSR vs SR=0 and vs the 0.9 gate, bootstrap Sharpe interval (1,000 samples, 22-day blocks, seed 42), and PBO/CSCV where computable. Report degeneracy explicitly; do not fabricate a missing statistic.
6. Promotion gates, exactly as frozen: mean OOS walk-forward Sharpe >= 0.9; positive-fold rate >= 50%; pooled OOS trades > 100; and >= 2/3 `pre_days` values within the plateau tolerance at `post_days=3`. The research conclusion follows the observed metrics, even if rejected.

### Artifact/report validation

- Write the markdown report with source commit, config SHA-256 prefix, input-cache integrity counts and hashes, execution conventions, metrics, all grid/fold results, limitations, promotion-gate decision, and reproduction commands.
- Persist the three C6-specific parquet outputs above. Re-read each saved artifact and check schemas, expected dates/rows/columns, finite values, and agreement with in-memory calculations; verify report provenance and the exact frozen config hash before finalizing the report.
- Do not overwrite C3/C4 artifacts or their reports.
- Add focused tests (e.g. trading-day mask across weekends/market holidays, baseline mask and grid arithmetic, cache-missing fail-closed behavior, cost boundary behavior, fold/date/finite-metric checks). Reuse installed dependencies; add no dependency just for convenience.

## Part 3 — isolated Actions execution (must not invoke Kilo)

Create `.github/workflows/cycle18-c6-full-backtest.yml` as a dedicated non-Kilo `workflow_dispatch`/pilot-branch push workflow. It should:
- checkout the exact triggering revision and verify `git rev-parse HEAD == github.sha`;
- have read-only repository permissions unless strictly needed otherwise;
- perform the cache-only preflight before running the script;
- run the C6 script and its output/report contract;
- publish report, three C6 parquet outputs, cache manifest, hashes and provenance as a named Actions artifact;
- always upload useful diagnostics when preflight or evaluation fails;
- never call `main.yml`, `gh workflow run main.yml`, Kilo, or any agent-dispatch endpoint; never download market data; never commit generated outputs automatically to the repository.
Validate workflow/YAML/shell syntax and add the workflow path to the existing workflow syntax validation where appropriate.

## Acceptance criteria

- Frozen C6 config/hypothesis are unchanged and the pre-registration checks pass.
- Cache-only runner completes against current tracked data or fails closed before computation if data validation fails.
- Exactly 18 grid configurations and 33 chronological folds; all required metrics finite; persisted artifacts/report pass their own assertions.
- Full report and all required outputs are published in the dedicated C6 Actions artifact; execution provenance identifies the precise code SHA.
- Research result follows the unchanged promotion rules. No threshold weakening, post-hoc tuning, downloaded replacement data, or selective reporting.
- Update `research/reports/cross_momentum_consolidation.md` only if needed to reference the final C4 rejection and current C6 status; do not rewrite its root-cause history.
- Update `NEXT_AGENT_TASK.md` after completion according to the observed C6 decision and the frozen shortlist/decision tree; the subsequent task must not assume a passing result.

## Scope boundaries

- Do not modify `research/hypotheses/calendar_effects_001.md` or `config/calendar_effects_001.yaml`.
- Do not modify historical `research/run_cycle13.py`, `research/run_cycle15.py`, frozen C3/C4 configs, or C3/C4 artifacts.
- Do not reopen C3/C4 for holdout-driven optimization; C4 is conclusively rejected on the first valid execution.
- No new data fetches, overlays, leverage, or extra configurations.
- Keep the validated `.github/workflows/cycle15-c4-full-backtest.yml` isolated from Kilo; do not change its behavior to dispatch agents.
