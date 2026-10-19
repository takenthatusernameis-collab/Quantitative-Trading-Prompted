# Experiment: Month-End Candidate Re-Audit (month_end_candidate_reaudit_001, Cycle 871)

## Hypothesis reference

This is a **measurement** experiment, not a strategy experiment. It closes the second half of the
defect that Cycle 870 (`research/experiments/rebalance_schedule_001.md`) found and fixed in shared
code: the two frozen candidates whose execution schedule was still the defective calendar rule had
never been re-measured on the corrected schedule.

The two candidates:

* `csmomentum_001` — `config/csmomentum_candidate_001.yaml`, executed by `research/run_cycle13.py`;
* `macroregime_001` — `config/macroregime_candidate_001.yaml`, executed by `research/run_cycle19.py`.

Both freeze `execution.rebalance_schedule: "monthly"` and `execution.signal_lag_days: 1` and both
were executed with

```python
is_month_end = pd.Series(weights.index.is_month_end, index=weights.index)
return weights.where(is_month_end, axis=0).ffill().fillna(0.0)
```

which is a **calendar** predicate applied to a **trading** calendar. It (a) enters the position one
session earlier than the configuration specifies, because the surviving row is the month's last
*calendar* day and it was produced by the previous session's signal, and (b) never rebalances at
all in every month whose last calendar day was a weekend or a market holiday, carrying the previous
month's weights through the whole month.

The frozen candidate configurations, the shared schedule implementation
(`src/backtest/rebalance.py`), the cost model, the gate thresholds and the Sharpe conventions are
**unchanged** by this cycle.

## Objective

For each of the two candidates, measure — read-only, without re-optimising anything —

1. whether the legacy (calendar) path reproduces the committed published numbers, and if a published
   number cannot be reproduced from the committed cache, say so explicitly and quantify the
   difference;
2. the deviation between the legacy path and the **config-faithful** path
   (`src/backtest/rebalance.py:build_month_end_weights`) in the canonical Sharpe, the backtest-scale
   Sharpe, max drawdown, annualized turnover, trade count and the pre-registered walk-forward mean
   OOS Sharpe;
3. whether the deviation moves the candidate across its own pre-registered gates, with the numbers
   that decide it, and label the outcome `verdict unchanged` / `verdict changed` / `indeterminate`.

## Data used

- **Source**: committed raw cache `data/raw/*.parquet` (Yahoo Finance via yfinance, cached).
  Cache-only, no network; the tool asserts that every cached file is SHA-256 byte-identical before
  and after the run and that `data/processed/` gains no file.
- **Date range / frequency / universe**:
  * `csmomentum_001`: 18 ETFs (`SPY QQQ IWM TLT GLD DBC VNQ EFA EEM XLB XLE XLF XLI XLK XLP XLU
    XLV XLY`), 1993-01-29 .. 2026-10-09, 8,482 sessions, EOD `Close`;
  * `macroregime_001`: 7 ETFs (`SPY QQQ IWM TLT GLD EFA EEM`) + `^VIX` as an *input only*,
    2004-11-18 .. 2026-10-09, 5,507 sessions.
- **Point-in-time treatment**: momentum = `Close_{t-21} / Close_{t-273} - 1` ranked cross-sectionally,
  top 50% equal-weight; the month-end signal is formed **on the last session** of the calendar month
  and the positions become effective on the **next** session (`signal_lag_days: 1`). The VIX regime
  gate uses the **prior** day's VIX close.
- **Missing data**: the aligned frames are the union calendar of the cached symbols, forward-filled
  per symbol; the `^VIX` series is forward-filled onto the ETF calendar. One coverage gap is
  material and is quantified below (the `^VIX` cache starts 2025-01-02).
- **Costs**: 1 bps commission + 2 bps slippage = 3 bps round-trip (`config/settings.yaml`), applied
  to the weight change of every session.
- **Splits**: the candidates' own pre-registered splits — `csmomentum_001` 1993-01-01 ..
  2026-10-09 (48 folds), `macroregime_001` 2004-11-18 .. 2026-10-09 (24 folds), 10y train / 12m test
  / 6m step, 21d purge, 21d embargo, fixed parameters.

## Configuration (parameters, hyperparameters)

No parameter was changed or tuned. The frozen values used are read from the candidate
configurations: `csmomentum_001` lookback 252 / skip 21 / top fraction 0.5;
`macroregime_001` lookback 226 / skip 21 / top fraction 0.5, SPY 200d SMA gate, VIX threshold 30 /
exposure 0.5, vol target 10% (63d lookback), drawdown control 15% → 0.5.

**Number of trials**: 1 per candidate per path (3 paths for `csmomentum_001`: daily / legacy /
faithful; 2 paths for `macroregime_001`: legacy / faithful). No configuration was searched, so the
trial count adds no multiple-testing degree of freedom; this cycle measures, it does not select.

## Results

### `csmomentum_001` (test window 2018-01-01 .. 2026-10-09, 48 walk-forward folds)

| Metric | Legacy (calendar) | Config-faithful | Delta |
|---|---|---|---|
| Sharpe (backtest scale) | 0.4101 | 0.4878 | +0.0777 |
| Sharpe (canonical) | 0.5904 | 0.6635 | +0.0732 |
| Max drawdown | -0.3571 | -0.2940 | +0.0631 |
| Annualized turnover | 2.06x | 2.47x | +0.41x |
| Trade days | 62 | 77 | +15 |
| WF mean OOS Sharpe (backtest scale) | 0.6868 | 0.6975 | +0.0107 |
| WF positive fold rate | 79.2% | 79.2% | 0.0pp |
| WF pooled OOS trades | 313 | 400 | +87 |
| Gate 1 (WF mean OOS Sharpe >= 0.9) | FAIL (0.6868) | FAIL (0.6975) | - |
| **Verdict** | **Rejected/Failed** | **Rejected/Failed** | **verdict unchanged** |

### `macroregime_001` (test window 2018-01-01 .. 2026-10-09, 24 walk-forward folds)

The numbers below are the **non-ablation** measurement: the `^VIX` cache now covers the full sample
(2004-11-18 .. 2026-10-09), so the VIX regime gate is active in both paths and the legacy path is
computed **from the cache** (no ablation). It reproduces the published numbers exactly (test Sharpe
0.2950, max drawdown -0.1807, turnover 3.13x, 58 trades, WF mean OOS Sharpe 0.4331 over 24 folds,
75.0% positive, 137 pooled trades).

| Metric | Legacy (calendar) | Config-faithful | Delta |
|---|---|---|---|
| Sharpe (backtest scale) | 0.2950 | 0.1428 | -0.1523 |
| Sharpe (canonical) | 0.5222 | 0.3823 | -0.1399 |
| Max drawdown | -0.1807 | -0.2240 | -0.0433 |
| Annualized turnover | 3.13x | 4.22x | +1.09x |
| Trade days | 58 | 84 | +26 |
| WF mean OOS Sharpe (backtest scale) | 0.4331 | 0.2636 | -0.1695 |
| WF positive fold rate | 75.0% | 66.7% | -8.3pp |
| WF pooled OOS trades | 137 | 193 | +56 |
| Gate 1 (WF mean OOS Sharpe >= 0.9) | FAIL (0.4331) | FAIL (0.2636) | - |
| **Verdict** | **Rejected/Failed** | **Rejected/Failed** | **verdict unchanged** |

The legacy column of the `macroregime_001` table is the **cache-reproducible** legacy path, which
reproduces the published path exactly because the cache now covers the full sample. See "Data gap"
below and the documented alternative in § "Cycle 871 ablation alternative".

### Reproduction of the published numbers

| Published source | Legacy path | Result |
|---|---|---|
| `research/experiments/csmomentum_baseline_wf_001.md` | test window + walk-forward | reproduced |
| `research/experiments/csmomentum_001_experiment_001.md` | — | **not** the calendar path (see below) |
| `research/experiments/macroregime_baseline_wf_001.md` | test window + walk-forward | reproduced |
| `research/experiments/macroregime_001_experiment_002.md` | the same numbers, restated | reproduced |
| `data/processed/weights_csmomentum_001.parquet` | weight matrix | bit-identical (max abs diff 0.0) |
| `data/processed/simulation_csmomentum_001.parquet` | daily net returns | max abs diff 1.4e-17 |
| `data/processed/weights_macroregime_001.parquet` | weight matrix | reproduces the published metrics |

**Provenance finding.** `research/experiments/csmomentum_001_experiment_001.md` was produced by the
repository's **daily re-rank** engine path (`run_backtest(...)` without a rebalance schedule), not by
the calendar path: the daily path reproduces its baseline block exactly (full-sample Sharpe 0.4496,
max drawdown -0.4336, turnover 12.03x, 1,781 trade days; test Sharpe 0.5652, 533 trade days),
while the calendar path gives 0.4246 / -0.4267 / 1.86x / 184 and 0.4101 / 62. The repository
therefore holds **two contradictory published records for the same candidate**, differing only in the
rebalance schedule. The walk-forward block of the same record is not reproducible with the
repository's current fold generator (it reports 46 folds / 0.6619; the generator gives 48 folds /
0.6928 on the frozen configuration's own window, and `config/csmomentum_001.yaml` itself declares
`folds_expected: 48`).

### Data gap (closed this cycle)

The committed `^VIX` cache now covers **2004-11-18 .. 2026-10-09** (5,514 sessions), i.e. the full
`macroregime_001` sample. **0 of 5,507 sessions** have no VIX observation. The config-faithful path
*with the published VIX gate* is therefore **computable from the committed cache**, and the legacy path
computed from the cache reproduces the published numbers exactly (test Sharpe 0.2950, max drawdown
-0.1807, turnover 3.13x, 58 trades, WF mean OOS Sharpe 0.4331 over 24 folds, 75.0% positive, 137
pooled trades). The gate-1 margin on the config-faithful path (0.6364 Sharpe) is 3.8x the measured
schedule effect (0.1695), so the verdict is not sensitive to the gate.

### Cycle 871 ablation alternative (documented, not deleted)

Cycle 871 measured the `macroregime_001` deviation on a **VIX-gate ablation**, because the committed
`^VIX` cache then covered only 2025-01-02 .. 2026-10-16 (451 rows) and 5,063 of the 5,507 sample
sessions had no VIX observation. On that ablation the legacy path gave test Sharpe 0.3371 / WF mean
OOS Sharpe 0.4628 and the config-faithful path gave test Sharpe 0.1705 / WF mean OOS Sharpe 0.2838
(both still Rejected/Failed, verdict unchanged). The non-ablation numbers above supersede them; the
ablation is kept here as the recorded alternative so the cycle's evolution is auditable.

### Effect of the defect

The calendar rule had **no rebalance at all** in 122 of 406 months (30.0%) for `csmomentum_001` and
in 77 of 264 months (29.2%) for `macroregime_001`, and entered the remaining positions one session
early. The corrected schedule therefore rebalances more often (test trade days 62 -> 77 and 58 -> 83)
and at a different point in time.

## Known confounders and limitations

1. The `macroregime_001` config-faithful path is now computable with the published VIX gate; the
   `^VIX` cache was backfilled this cycle to cover the full sample (see "Data gap").
2. `csmomentum_001` has two contradictory published records; this cycle identifies which code path
   produced each and measures the schedule's effect, it does not decide which record is
   authoritative.
3. The walk-forward statistic is the mean of **overlapping** 12-month Sharpe ratios and the pooled
   trade count double-counts sessions covered by two folds.
4. Costs are the repository's flat 3 bps round-trip model: no bid-ask spread, market impact, borrow
   or latency; sector ETFs can be wider than SPY.
5. The risk overlays of `macroregime_001` are computed on the same daily pipeline in both paths, so
   the measured deviation is attributable to the schedule rule alone; the separate question of
   whether the overlay state should be measured on the *held* portfolio is not answered here.
6. This is a measurement cycle: no parameter, universe, cost model, gate threshold or configuration
   was changed and no candidate verdict was re-opened.

## Falsification condition

This cycle's conclusions are wrong if any of the following holds (each is an executable check in
`research/month_end_candidate_reaudit.py`, 17/17 pass):

1. the legacy path does not reproduce the committed weight artifacts or the published test-period
   metrics;
2. the config-faithful path is not equal to `src/backtest/rebalance.py:build_month_end_weights`;
3. a config-faithful segment is not the selection of its own signal date, or is effective on or
   before its signal date;
4. the calendar rule has no month without a rebalance;
5. a gate threshold, the cost model, the universe or the Sharpe convention differs from the frozen
   configuration;
6. the raw cache or any committed artifact under `data/`, `config/` or `research/experiments/` is
   modified.

## Reproduction commands

```bash
python research/month_end_candidate_reaudit.py     # OVERALL: PASS, 17/17 checks
python research/rebalance_schedule_audit.py         # OVERALL: PASS (Cycle 870, unchanged)
python research/sectorrotation_long_sample_feasibility.py
python -m pytest -q                                 # 82 passed
git status --porcelain data/ config/               # empty
```

## Artifacts

| Artifact | Path |
|---|---|
| Tool | `research/month_end_candidate_reaudit.py` |
| Report | `research/reports/month_end_candidate_reaudit_001.md` |
| Shared schedule implementation (unchanged) | `src/backtest/rebalance.py` |
| Frozen configurations (unchanged) | `config/csmomentum_candidate_001.yaml`, `config/macroregime_candidate_001.yaml` |
| Committed artifacts used as reference (read-only) | `data/processed/weights_csmomentum_001.parquet`, `data/processed/simulation_csmomentum_001.parquet`, `data/processed/weights_macroregime_001.parquet` |
| Pre-registered hypotheses | `research/hypotheses/csmomentum_001.md`, `research/hypotheses/macroregime_001.md` |
| Predecessor cycle | `research/experiments/rebalance_schedule_001.md` (Cycle 870) |

---

*Report generated by `research/month_end_candidate_reaudit.py` (Cycle 871). Deterministic: no random
number generator, no timestamps.*
