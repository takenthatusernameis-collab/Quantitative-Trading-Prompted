# Month-End Candidate Re-Audit (month_end_candidate_reaudit_001, Cycle 871)

## Summary

Two frozen candidates specify the month-end rebalance schedule
(`execution.rebalance_schedule: "monthly"`, `signal_lag_days: 1`) but were executed with a
**calendar** rule (`weights.index.is_month_end`) that rebalances one session earlier than the
configuration specifies and **never rebalances at all** in every month whose last calendar day was
a weekend or a market holiday. Cycle 870 put one correct implementation of the schedule into shared
code (`src/backtest/rebalance.py`); this cycle measures, read-only, what the defect did to the two
published results.

| Candidate | Published (legacy) test Sharpe | Config-faithful test Sharpe | Published WF mean OOS Sharpe | Config-faithful WF mean OOS Sharpe | Verdict |
|---|---|---|---|---|---|
| `csmomentum_001` | 0.4101 | 0.4878 | 0.6868 | 0.6975 | **verdict unchanged** |
| `macroregime_001` | 0.2950 (published artifact) / 0.3371 (cache-reproducible) | 0.1705 (cache-reproducible) | 0.4331 (published artifact) / 0.4628 (cache-reproducible) | 0.2838 (cache-reproducible) | **verdict unchanged** |

**Headline:** the schedule defect moved the *numbers* materially — the walk-forward mean OOS
Sharpe changes by +0.0107 for
`csmomentum_001` and by -0.1790
for `macroregime_001` (cache-reproducible paths) — but it did **not** move either candidate across
its own pre-registered gates: both were rejected before and both are rejected after. The published
rejections are robust to the defect.

No configuration, universe, cost model, gate threshold, Sharpe convention or committed artifact was
changed by this cycle; the tool is read-only and writes exactly this report.

## 1. Method

### 1.1 Data (read-only)

| Item | `csmomentum_001` | `macroregime_001` |
|---|---|---|
| Universe | SPY, QQQ, IWM, TLT, GLD, DBC, VNQ, EFA, EEM, XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY (18) | SPY, QQQ, IWM, TLT, GLD, EFA, EEM (7) + `^VIX` (input only) |
| Window | 1993-01-29 .. 2026-10-09 (8482 sessions) | 2004-11-18 .. 2026-10-09 (5507 sessions) |
| Source | committed raw cache `data/raw/*.parquet` (Yahoo Finance via yfinance), cache-only, no network | idem |
| Aligned-frame content hash | `abccaa7a9fb67e99` | `7393bf74d806c40b` |
| Costs | 3.0 bps round-trip (1 bps commission + 2 bps slippage) | idem |

The published windows (…1993-01-01/2026-10-09 and 2004-11-18/2026-10-09) are used, not the current
cache end, so that the numbers are comparable with the published records.

### 1.2 The two schedules

**Legacy (the defect).** `research/run_cycle13.py:_apply_monthly_schedule` and
`research/run_cycle19.py:_apply_monthly_schedule`:

```python
is_month_end = pd.Series(weights.index.is_month_end, index=weights.index)
return weights.where(is_month_end, axis=0).ffill().fillna(0.0)
```

`is_month_end` is a **calendar** predicate applied to a **trading** calendar. Two consequences:

1. the row that survives is the one of the month's last *calendar* day, and it was produced by the
   signal of the **previous** session, so the position is put on one session earlier than the
   frozen configuration specifies (`signal_lag_days: 1` from the month's last *session*);
2. a month whose last calendar day was a weekend or a market holiday has **no** such row, so the
   previous month's weights are carried through the whole month.

| Schedule statistic | `csmomentum_001` | `macroregime_001` |
|---|---|---|
| Calendar months in the sample | 406 | 264 |
| Months with a calendar rebalance | 284 | 187 |
| Months with **no** calendar rebalance | 122 (30.0%) | 77 (29.2%) |
| Shared-schedule month-end signals | 392 | 251 |

**Config-faithful.** `src/backtest/rebalance.py:build_month_end_weights` (the single shared
implementation since Cycle 870): the signal is formed on the **last session** of the calendar month
and the positions become effective on the **next** session and are held until the next month-end
signal. For `csmomentum_001` (no risk overlays) the config-faithful weight matrix *is*
`build_month_end_weights(mask)`; for `macroregime_001` the same schedule is applied to the same
daily pipeline by sampling it at each segment's effective date, so the **only** difference between
the two paths is the schedule rule.

### 1.3 Metrics and conventions

Both Sharpe conventions are reported and never mixed:

* **canonical** (`src/evaluation/sharpe.py:sharpe_ratio`, `arithmetic_annualized_rf0`) — the
  convention of the promotion gates since Cycle 861;
* **backtest scale** (`backtest_sharpe_ratio`, `cagr_annualized_rf2`) — the scale of the published
  backtest records, and therefore the scale on which the candidates' pre-registered walk-forward
  gate was evaluated. The gate table below uses the **backtest scale**, exactly as the original
  runs did.

The walk-forward design is the pre-registered one: 10y train / 12m
test / 6m step, 21d purge, 21d embargo, fixed
parameters. The fold windows are slices of one continuously computed point-in-time path (no
re-optimisation per fold).

## 2. `csmomentum_001` — deviation

### 2.1 Reproduction of the published numbers

| Published source | What the legacy path reproduces | Result |
|---|---|---|
| `research/experiments/csmomentum_baseline_wf_001.md` (test window, calendar path) | all 10 published test metrics | reproduced (tolerance = the last published decimal of each metric) |
| `research/experiments/csmomentum_baseline_wf_001.md` (walk-forward) | 48 folds, mean OOS Sharpe 0.6868, 79.2% positive, 313 pooled trades | reproduced (tolerance = the last published decimal of each metric) |
| `data/processed/weights_csmomentum_001.parquet` | the point-in-time weight matrix | bit-identical (max abs diff 0.000e+00) |
| `data/processed/simulation_csmomentum_001.parquet` | the daily net-return series | max abs diff 1.388e-17 (0 of 8482 sessions differ) |

**Important provenance finding.** `research/experiments/csmomentum_001_experiment_001.md` — the
record named for this candidate — was **not** produced by the calendar path. Its reproduction
command is `run_backtest(...)` without a rebalance schedule, i.e. the engine's **daily re-rank**
path, and the daily path reproduces that record's baseline block exactly:

| Metric | Published (`csmomentum_001_experiment_001.md`) | Daily re-rank path | Legacy calendar path |
|---|---|---|---|
| annualized_return | 0.0937 | 0.093693 (reproduced) | 0.091326 |
| annualized_volatility | 0.1639 | 0.163914 (reproduced) | 0.167990 |
| sharpe_ratio | 0.4496 | 0.449586 (reproduced) | 0.424585 |
| sortino_ratio | 0.5852 | 0.585207 (reproduced) | 0.539910 |
| max_drawdown | -0.4336 | -0.433621 (reproduced) | -0.426715 |
| annualized_turnover | 12.03 | 12.033506 (reproduced) | 1.860670 |
| trade_count | 1781 | 1781.000000 (reproduced) | 184.000000 |
| profit_factor | 1.1217 | 1.121709 (reproduced) | 1.119051 |
| avg_exposure | 0.968 | 0.967696 (reproduced) | 0.965103 |
| test sharpe_ratio | 0.5652 | 0.565215 (reproduced) | 0.410118 |
| test annualized_return | 0.1114 | 0.111406 (reproduced) | 0.090744 |
| test max_drawdown | -0.2756 | -0.275630 (reproduced) | -0.357143 |
| test trade_count | 533 | 533.000000 (reproduced) | 62.000000 |

The repository therefore holds **two contradictory published records for the same candidate** that
differ only in the rebalance schedule (full-sample Sharpe 0.4496 daily vs 0.4246 calendar; test
Sharpe 0.5652 vs 0.4101). The walk-forward block of the same record is *not* reproducible with the
repository's current fold generator (it reports 46 folds / mean OOS Sharpe
0.6619; the generator produces 48 folds /
0.6928 on the frozen configuration's own window), while the
frozen configuration `config/csmomentum_001.yaml` itself declares `folds_expected: 48`.

### 2.2 Legacy vs config-faithful

| Metric | Legacy (calendar) | Config-faithful | Delta |
|---|---|---|---|
| **full sample** | | | |
| sharpe_canonical | 0.6045 | 0.6051 | 0.0006 |
| sharpe_backtest_scale | 0.4246 | 0.4247 | 0.0001 |
| annualized_return | 0.0913 | 0.0905 | -0.0009 |
| annualized_volatility | 0.1680 | 0.1659 | -0.0021 |
| max_drawdown | -0.4267 | -0.4474 | -0.0206 |
| annualized_turnover | 1.86 | 2.16 | 0.29 |
| trade_days | 184 | 232 | 48 |
| avg_exposure | 0.9651 | 0.9677 | 0.0026 |
| profit_factor | 1.1191 | 1.1175 | -0.0015 |
| cost_drag_total | 0.0188 | 0.0218 | 0.0030 |
| sessions | 8482 | 8482 | 0 |
| **test sample** | | | |
| sharpe_canonical | 0.5904 | 0.6635 | 0.0732 |
| sharpe_backtest_scale | 0.4101 | 0.4878 | 0.0777 |
| annualized_return | 0.0907 | 0.0999 | 0.0091 |
| annualized_volatility | 0.1725 | 0.1638 | -0.0087 |
| max_drawdown | -0.3571 | -0.2940 | 0.0631 |
| annualized_turnover | 2.06 | 2.47 | 0.41 |
| trade_days | 62 | 77 | 15 |
| avg_exposure | 1.0000 | 1.0000 | 0.0000 |
| profit_factor | 1.1199 | 1.1303 | 0.0103 |
| cost_drag_total | 0.0054 | 0.0065 | 0.0011 |
| sessions | 2205 | 2205 | 0 |

### 2.3 Walk-forward (48 folds)

| Metric | Legacy (calendar) | Config-faithful | Delta |
|---|---|---|---|
| folds | 48 | 48 | 0 |
| mean OOS Sharpe (backtest scale) | 0.6868 | 0.6975 | 0.0107 |
| mean OOS Sharpe (canonical) | 0.8318 | 0.8404 | 0.0086 |
| median OOS Sharpe | 0.6432 | 0.6179 | -0.0253 |
| % positive folds | 0.7917 | 0.7917 | 0.0000 |
| pooled OOS trades | 313 | 400 | 87 |
| std OOS Sharpe | 0.7822 | 0.7784 | -0.0039 |

### 2.4 Gates

| Gate | Threshold | Legacy | Config-faithful | Status |
|---|---|---|---|---|
| 1. WF mean OOS Sharpe | >= 0.9 | 0.6868 | 0.6975 | FAIL in both |
| 2. Positive fold rate | >= 50% | 79.2% | 79.2% | PASS in both |
| 3. Pooled OOS trades | > 100 | 313 | 400 | PASS in both |

Pre-registered falsification condition (WF mean OOS Sharpe < 0.9 **or** positive fold rate < 50%):
**met in both paths**. Verdict: **Rejected/Failed** (legacy) and
**Rejected/Failed** (config-faithful) → **verdict unchanged**. The gate-1 margin is
0.2025 Sharpe
on the config-faithful path, so the verdict is not close to flipping.

## 3. `macroregime_001` — deviation

### 3.1 Reproduction of the published numbers and the VIX data gap

The committed legacy path (`data/processed/weights_macroregime_001.parquet`) reproduces the
published numbers exactly:

| Metric | Published | Observed | Abs. diff | Result |
|---|---|---|---|---|
| `total_return` | 0.5571 | 0.557123 | 2.269e-05 | MATCH |
| `annualized_return` | 0.0519 | 0.051913 | 1.283e-05 | MATCH |
| `annualized_volatility` | 0.1082 | 0.108167 | 3.330e-05 | MATCH |
| `sharpe_ratio` | 0.2950 | 0.295034 | 3.377e-05 | MATCH |
| `sortino_ratio` | 0.3289 | 0.328877 | 2.271e-05 | MATCH |
| `max_drawdown` | -0.1807 | -0.180660 | 4.004e-05 | MATCH |
| `annualized_turnover` | 3.13 | 3.125506 | 4.494e-03 | MATCH |
| `trade_count` | 58 | 58.000000 | 0.000e+00 | MATCH |
| `profit_factor` | 1.11 | 1.108529 | 1.471e-03 | MATCH |
| `avg_exposure` | 0.6758 | 0.675795 | 4.995e-06 | MATCH |

| Metric | Published | Observed | Abs. diff | Result |
|---|---|---|---|---|
| `n_folds` | 24 | 24.000000 | 0.000e+00 | MATCH |
| `mean_test_sharpe` | 0.4331 | 0.433114 | 1.362e-05 | MATCH |
| `std_test_sharpe` | 0.9609 | 0.960863 | 3.718e-05 | MATCH |
| `median_test_sharpe` | 0.4950 | 0.494990 | 1.036e-05 | MATCH |
| `pct_positive_sharpe` | 0.750 | 0.750000 | 0.000e+00 | MATCH |
| `total_test_trades` | 137 | 137.000000 | 0.000e+00 | MATCH |

**Data gap.** The committed `^VIX` cache starts
**2025-01-02**, i.e. **5063 of
5507 sessions** of the candidate's sample have no VIX observation
(444 of 5507 sessions are covered). The published
run had the full VIX history, so the VIX regime gate was active before 2025; the cache-reproducible
path cannot activate it and therefore differs from the published path by up to
0.125000 in weight (published test Sharpe
0.2950 vs cache-reproducible
0.3371; published WF mean OOS Sharpe
0.4331 vs cache-reproducible 0.4628).

**Consequence for this cycle.** The config-faithful path *with the published VIX gate* is **not
computable from the committed cache**. The deviation below is therefore measured on the
cache-reproducible paths (legacy and config-faithful share the identical, cache-limited VIX input,
so the schedule effect is measured like-for-like), and the missing input is quantified above
rather than hidden. The published record's own numbers are reproduced from the committed artifact,
so the *published* result is not in doubt; only the *config-faithful* counterpart is data-limited.

### 3.2 Legacy vs config-faithful (cache-reproducible paths)

| Metric | Legacy (calendar) | Config-faithful | Delta |
|---|---|---|---|
| **full sample** | | | |
| sharpe_canonical | 0.7547 | 0.7109 | -0.0438 |
| sharpe_backtest_scale | 0.5270 | 0.4806 | -0.0464 |
| annualized_return | 0.0718 | 0.0674 | -0.0045 |
| annualized_volatility | 0.0984 | 0.0986 | 0.0002 |
| max_drawdown | -0.1794 | -0.2227 | -0.0434 |
| annualized_turnover | 2.66 | 3.42 | 0.75 |
| trade_days | 127 | 180 | 53 |
| avg_exposure | 0.6391 | 0.6471 | 0.0080 |
| profit_factor | 1.1630 | 1.1522 | -0.0108 |
| cost_drag_total | 0.0175 | 0.0224 | 0.0049 |
| sessions | 5507 | 5507 | 0 |
| **test sample** | | | |
| sharpe_canonical | 0.5630 | 0.4010 | -0.1620 |
| sharpe_backtest_scale | 0.3371 | 0.1705 | -0.1666 |
| annualized_return | 0.0562 | 0.0387 | -0.0175 |
| annualized_volatility | 0.1075 | 0.1099 | 0.0024 |
| max_drawdown | -0.1794 | -0.2227 | -0.0434 |
| annualized_turnover | 3.11 | 4.03 | 0.92 |
| trade_days | 58 | 83 | 25 |
| avg_exposure | 0.6735 | 0.6851 | 0.0116 |
| profit_factor | 1.1174 | 1.0819 | -0.0355 |
| cost_drag_total | 0.0082 | 0.0106 | 0.0024 |
| sessions | 2205 | 2205 | 0 |

### 3.3 Walk-forward (24 folds)

| Metric | Legacy (calendar) | Config-faithful | Delta |
|---|---|---|---|
| folds | 24 | 24 | 0 |
| mean OOS Sharpe (backtest scale) | 0.4628 | 0.2838 | -0.1790 |
| mean OOS Sharpe (canonical) | 0.6605 | 0.4762 | -0.1844 |
| median OOS Sharpe | 0.5275 | 0.5022 | -0.0252 |
| % positive folds | 0.7500 | 0.6250 | -0.1250 |
| pooled OOS trades | 137 | 191 | 54 |
| std OOS Sharpe | 0.9693 | 1.1155 | 0.1462 |

### 3.4 Gates

| Gate | Threshold | Legacy (cache) | Config-faithful (cache) | Status |
|---|---|---|---|---|
| 1. WF mean OOS Sharpe | >= 0.9 | 0.4628 | 0.2838 | FAIL in both |
| 2. Positive fold rate | >= 50% | 75.0% | 62.5% | PASS in both |
| 3. Pooled OOS trades | > 100 | 137 | 191 | PASS in both |

Pre-registered falsification condition: **met in both paths**. Verdict:
**Rejected/Failed** (legacy) and **Rejected/Failed** (config-faithful) →
**verdict unchanged**. The gate-1 margin on the config-faithful path is
0.6162 Sharpe,
which is 3.4x
the measured schedule effect, so the verdict is not sensitive to the missing VIX history.

## 4. What the schedule defect actually did

| | `csmomentum_001` | `macroregime_001` |
|---|---|---|
| Months with no rebalance at all (legacy) | 122 of 406 (30.0%) | 77 of 264 (29.2%) |
| Test-period trade days (legacy → faithful) | 62 → 77 | 58 → 83 |
| Test-period annualized turnover (legacy → faithful) | 2.06x → 2.47x | 3.11x → 4.03x |
| Test-period Sharpe (legacy → faithful) | 0.4101 → 0.4878 | 0.3371 → 0.1705 |
| WF mean OOS Sharpe (legacy → faithful) | 0.6868 → 0.6975 | 0.4628 → 0.2838 |

The defect is a **timing** defect, not a cost defect in the sense of a wrong cost model: it made the
strategy hold a stale selection for a whole month in roughly a quarter to a third of all months and
re-entered one session early otherwise. For `csmomentum_001` the corrected schedule is slightly
*better* on the test window and on the walk-forward mean; for `macroregime_001` it is clearly
*worse* (the overlay's vol-target and drawdown state interact with the rebalance timing, and the
stale-selection months happened to be favourable). Neither change is large enough to move a
candidate across a 0.9 Sharpe gate from 0.29–0.70.

## 5. Falsification conditions for this report

This cycle's conclusions are wrong if any of the following holds:

1. the legacy path does not reproduce the committed `weights_csmomentum_001.parquet` /
   `weights_macroregime_001.parquet` artifacts or the published test-period metrics (it does, to the
   tolerances stated in §2.1 and §3.1);
2. a config-faithful path does not equal `src/backtest/rebalance.py:build_month_end_weights` (it is
   bit-identical for `csmomentum_001`);
3. a config-faithful segment is not the selection of its own signal date, or is effective on or
   before its signal date (checked for both candidates);
4. the calendar rule has no month without a rebalance (it has
   122 and
   77 such months);
5. a gate threshold, the cost model, the universe or the Sharpe convention differs from the frozen
   configuration (none does);
6. the raw cache or any committed artifact under `data/`, `config/` or `research/experiments/` is
   modified (none is).

## 6. Limitations

1. The `macroregime_001` config-faithful path is **not computable with the published VIX gate**:
   the committed `^VIX` cache starts 2025-01-02. The
   deviation is measured on cache-reproducible paths and the missing input is quantified; the
   published result itself is reproduced from the committed artifact.
2. `csmomentum_001` has **two** published records with different numbers; this report does not
   decide which one is authoritative, it identifies which code path produced each and measures the
   schedule's effect on both.
3. The walk-forward fold statistic is the **mean of overlapping 12-month Sharpe ratios**, not the
   Sharpe of the concatenated covered window, and the folds overlap by 6 months; the pooled trade
   count sums over folds and therefore counts the same session several times.
4. Costs are the repository's flat 3.0 bps round-trip model with no bid-ask spread,
   market impact, borrow or latency; sector ETFs can be wider than SPY.
5. The 9 sector ETFs, DBC and VNQ end 2026-10-08 while the core cache reaches 2026-10-16, so on
   the last session of the published window (2026-10-09) the sector ETFs carry their 2026-10-08
   close forward and their return on that session is zero. The committed published artifact was
   produced under the same cache layout, so the legacy path still reproduces it exactly
   (0 of 8482 sessions differ, max abs diff
   1.388e-17); a re-run on a freshly extended cache would move those last rows.
6. This is a measurement cycle: no parameter, universe, cost model, gate threshold or configuration
   was changed, and no candidate verdict was re-opened.

## 7. Checks

| Check | Result | Detail |
|---|---|---|
| `csmomentum_legacy_reproduces_committed_weights` | PASS | max abs(legacy weights - data/processed/weights_csmomentum_001.parquet) = 0.000e+00 (tolerance 1e-12) over 8482 sessions. |
| `csmomentum_legacy_net_returns_match_committed_simulation` | PASS | max abs(legacy net return - committed simulation) = 1.388e-17 (tolerance 1e-12); 0 of 8482 sessions differ. |
| `csmomentum_legacy_reproduces_published_calendar_record` | PASS | the legacy path reproduces the test-period metrics of research/experiments/csmomentum_baseline_wf_001.md exactly |
| `csmomentum_legacy_reproduces_published_walkforward` | PASS | the legacy path reproduces the walk-forward block of research/experiments/csmomentum_baseline_wf_001.md (folds 48, mean OOS Sharpe 0.6868, pooled trades 313). |
| `csmomentum_001_experiment_001_is_the_daily_rerank_path` | PASS | the daily re-rank path reproduces research/experiments/csmomentum_001_experiment_001.md (full sample Sharpe 0.4496, test Sharpe 0.5652, 1781 trade days); the legacy calendar path does NOT. |
| `csmomentum_001_experiment_001_walkforward_block_is_not_reproducible` | PASS | the walk-forward block of research/experiments/csmomentum_001_experiment_001.md reports 46 folds / mean OOS Sharpe 0.6619, which the repository's current fold generator does not reproduce: the daily re-rank path on the frozen config's own window (1993-01-01..2026-10-09) yields 48 folds / 0.6928. |
| `csmomentum_faithful_path_equals_shared_module` | PASS | the config-faithful path is bit-identical to src/backtest/rebalance.py:build_month_end_weights (max abs difference = 0.000e+00). |
| `csmomentum_faithful_path_is_point_in_time` | PASS | 392 month-end signals; each segment equals the equal-weight of the selection mask at its own signal date and becomes effective strictly after it. |
| `macroregime_legacy_reproduces_published_metrics` | PASS | the committed legacy weights artifact reproduces the test-period metrics of research/experiments/macroregime_baseline_wf_001.md exactly |
| `macroregime_legacy_reproduces_published_walkforward` | PASS | the committed legacy weights artifact reproduces the walk-forward block of research/experiments/macroregime_baseline_wf_001.md and of research/experiments/macroregime_001_experiment_002.md (folds 24, mean OOS Sharpe 0.4331, pooled trades 137). |
| `macroregime_001_experiment_002_restates_the_same_numbers` | PASS | the walk-forward numbers restated in research/experiments/macroregime_001_experiment_002.md (24 folds, mean OOS Sharpe 0.4331, 75.0% positive, 137 pooled trades) are reproduced by the committed legacy weights artifact. |
| `macroregime_vix_history_gap_is_quantified` | PASS | the committed ^VIX cache starts 2025-01-02, i.e. 5063 of 5507 sessions of the candidate's sample have no VIX observation; the cache-reproducible legacy path therefore differs from the published path by at most 0.125000 in weight (published test Sharpe 0.2950 vs cache-reproducible 0.3371). |
| `macroregime_faithful_path_is_point_in_time` | PASS | 251 month-end signals; every segment holds only the assets its own signal date selected and becomes effective strictly after it. |
| `schedule_defect_does_not_move_either_candidate_across_its_gates` | PASS | csmomentum_001: verdict unchanged (WF mean OOS Sharpe 0.6868 -> 0.6975, gate 0.9); macroregime_001: verdict unchanged (WF mean OOS Sharpe 0.4628 -> 0.2838). |
| `calendar_rule_actually_skips_months` | PASS | the calendar rule has no rebalance at all in 122 of 406 months (csmomentum_001) and in 77 of 264 months (macroregime_001). |
| `raw_cache_unchanged` | PASS | all 19 cached parquet files are SHA-256 byte-identical before and after the run. |
| `no_new_processed_artifacts` | PASS | data/processed contains the same 16 parquet files before and after the run; the tool writes no simulation artifact. |

## 8. Reproduction

```bash
python research/month_end_candidate_reaudit.py    # this report; OVERALL: PASS
python research/rebalance_schedule_audit.py        # Cycle 870 tool must still print OVERALL: PASS
python research/sectorrotation_long_sample_feasibility.py
python research/promotion_feasibility_backtest.py  # incumbent artifacts unchanged (NO-GO)
python -m pytest -q
git status --porcelain data/                        # empty
```

## 9. Provenance

- Data: committed raw cache `data/raw/*.parquet` (read-only; SHA-256 byte-identical before and after
  the run).
- Committed artifacts used as the reproduction reference: `data/processed/weights_csmomentum_001.parquet`,
  `data/processed/simulation_csmomentum_001.parquet`, `data/processed/weights_macroregime_001.parquet`
  (all read-only, all unchanged).
- Shared schedule implementation: `src/backtest/rebalance.py` (unchanged by this cycle).
- Gate thresholds, candidate configurations, cost model and Sharpe convention: unchanged.
