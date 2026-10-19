# Experiment: Sector Rotation Long-Sample Feasibility (sectorrotation_001, Cycle 869)

## Hypothesis reference

`research/hypotheses/sectorrotation_001.md` (v001, pre-registered 2026-10-12, code revision
47c531e). Frozen configuration: `config/sectorrotation_candidate_001.yaml` (unchanged by this
cycle).

## Objective

Run the long-sample feasibility backtest of the frozen `sectorrotation_001` candidate over its
whole available history (1998-12-22 .. 2026-10-08), in the pattern of
`research/promotion_feasibility_backtest.py`, and report net-of-cost Sharpe, PSR, trade count and
gate outcomes.

## Data used

- **Source**: committed raw cache `data/raw/{XLB,XLE,XLF,XLI,XLK,XLP,XLU,XLV,XLY}.parquet`
  (Yahoo Finance via yfinance, cached). No network access; no data written.
- **Date range**: 1998-12-22 .. 2026-10-08, 6,991 sessions of the 9-sector union calendar.
  The sector cache ends 6 sessions before the repository's core cache (2026-10-16).
- **Frequency**: daily, EOD `Close`.
- **Universe**: the 9 GICS sector ETFs; identical inception (1998-12-22), so cross-sectional
  breadth is constant at 9 and there is no survivorship or point-in-time breadth growth.
- **Point-in-time treatment**: momentum = `Close_{t-21} / Close_{t-273} - 1`, ranked across the
  9 assets, top 50% held equal-weight, month-end rebalance with a 1-day signal lag. The first
  date with a valid cross-section is 2000-01-24 (pre-registered value, reproduced); the first
  session with positions is 2000-02-01.
- **Missing data**: 0 NaN in every cached `Close` series, 0 duplicate dates, aligned frame
  6991 x 9.
- **Integrity**: aligned-frame content hash `5e2d48e6579a53cd...` reproduces the value frozen in
  the pre-registration; per-file SHA-256 of all 9 parquet files is byte-identical before and after
  the run (`git status --porcelain data/` empty).
- **Costs**: 1 bps commission + 2 bps slippage = 3 bps round-trip, charged on absolute weight
  change (`config/settings.yaml`, equal to the frozen candidate cost model).

## Configuration

- Signal: `lookback=252`, `skip=21`, `top_fraction=0.5` (the pre-registered baseline, the centre
  of the 18-configuration robustness grid).
- Rebalance: month-end, 1-day lag (frozen config). **The repository engine does not implement
  this**: `src/backtest/engine.py:run_backtest` accepts `rebalance_freq` and never uses it, so
  `build_weights` re-ranks every session. The config-faithful month-end path was implemented in
  the research script; the engine path is reported next to it as the deviation measurement
  (Sharpe 0.471379 vs 0.472367; annualized turnover 16.48x vs 3.00x; 1,088 vs 175 trade days).
- Risk overlay: none (pre-registered baseline).
- Trials: 1 configuration for the headline result, plus the 3-lookback plateau check required by
  the pre-registered falsification condition. The remaining 15 grid cells were **not** evaluated
  in this cycle.

## Splits

- Long sample (full): 1998-12-22 .. 2026-10-08; invested sample: 2000-02-01 .. 2026-10-08
  (6,712 sessions).
- Pre-registered chronological splits: train <= 2009-12-31, validation 2010-01-01 .. 2017-12-31,
  test 2018-01-01 .. 2026-10-08.
- Pre-registered walk-forward: 36 folds (10y train / 12m test / 6m step, 21d purge, 21d embargo),
  fixed parameters, generated with `src/evaluation/walkforward.py:generate_walkforward_splits`.

## Results

### Long sample (config-faithful month-end rebalance, invested sample)

| Metric | Value |
|---|---|
| Sessions | 6,712 |
| Sharpe (canonical `arithmetic_annualized_rf0`) | 0.472367 |
| Sharpe (backtest-baseline scale `cagr_annualized_rf2`) | 0.284499 |
| CAGR | 7.1200% |
| Annualized vol | 17.9965% |
| Max drawdown | -47.1578% |
| Rolling 63d Sharpe / max DD | 1.765163 / -3.3481% |
| Trade days / month-end rebalances | 175 / 321 |
| Annualized turnover | 2.9961x |
| Profit factor | 1.0922 |
| Cumulative cost drag | 2.394% |

### PSR and multiple testing (seed 20240101 for the PSR, 42 for the DSR)

| Target | PSR (normal) | PSR (empirical) | Sharpe SE |
|---|---|---|---|
| 0.0 | 0.996895 | 0.999 | 0.172618 |
| 0.9 (candidate's own promotion threshold) | 0.006618 | 0.008 | 0.172618 |
| 1.4178 (incumbent's recorded backtest baseline) | 2.16e-08 | 0.000 | 0.172618 |

Deflated Sharpe Ratio (N=18, the pre-registered configuration count): -4.1828, probability
1.44e-05, against the 0.9 target.

### Repository promotion-gate table (`config/promotion_gates.yaml`) on the long sample

`track_record_length` 6,712 PASS; `full_period_sharpe` 0.472367 FAIL; `rolling_63d_sharpe`
1.765163 PASS; `max_drawdown` -0.471578 FAIL; `rolling_63d_max_dd` -0.033481 PASS;
`regime_flips` NOT APPLICABLE (no paper-trading record, no regime filter); `psr` 0.006618 FAIL
(zone `below_grey`). **Decision: NO-GO** (failed: `full_period_sharpe`, `max_drawdown`, `psr`).
Under the incumbent's PSR target 1.4178 the decision is unchanged (NO-GO); under the conservative
reading (regime-flip gate counted as failed) it is NO-GO as well.

### Candidate's own pre-registered gates

| Gate | Value | Threshold | Verdict |
|---|---|---|---|
| Walk-forward mean OOS Sharpe | 0.847243 | >= 0.9 | **FAIL** |
| Positive fold rate | 0.916667 | >= 0.5 | PASS |
| Pooled OOS trades (sum over folds / distinct sessions) | 215 / 110 | > 100 | PASS |
| Parameter plateau (lookbacks within 10% of the baseline) | 2 of 3 (189, 252) | >= 2 of 3 | PASS |

### Pre-registered splits

| Split | Sessions | Sharpe (canonical) | CAGR | Max DD |
|---|---|---|---|---|
| Train (1998-12-22 .. 2009-12-31) | 2,774 | 0.147532 | 1.0080% | -47.1578% |
| Validation (2010 .. 2017) | 2,013 | 0.720430 | 10.2645% | -22.6371% |
| Test (2018-01-02 .. 2026-10-08) | 2,204 | 0.686168 | 11.3593% | -34.1320% |

### Benchmark (1/N equal weight over the same 9 sectors)

| Window | Strategy Sharpe | Benchmark Sharpe | Strategy CAGR | Benchmark CAGR | Excess CAGR |
|---|---|---|---|---|---|
| Invested sample (2000-02-01 .. 2026-10-08) | 0.472367 | 0.468824 | 7.1200% | 7.1044% | +0.0156 pp |
| Walk-forward window (2008-09-17 .. 2026-07-30) | 0.590049 | 0.568512 | 9.6429% | 9.3834% | +0.2595 pp |
| Test window (2018-01-02 .. 2026-10-08) | 0.686168 | 0.618723 | 11.3593% | 9.9616% | +1.3977 pp |

Max drawdown on the invested sample: strategy -47.1578% vs benchmark -53.9222%; on the test
window: strategy -34.1320% vs benchmark -37.4287%. The pre-registered C4 prior for the net
annualized excess over 1/N was 0-1.5%: the long-sample excess (+0.0156 pp) is far below it, the
test-window excess (+1.3977 pp) is at the top of it.

### Interpretation

1. The strategy is **not** promotable on the long sample: canonical Sharpe 0.472367 (gate 0.9),
   max drawdown -47.16% (gate -15%), PSR vs the 0.9 threshold 0.006618.
2. The edge over the 1/N benchmark is **economically negligible on the long sample**: +0.0035
   Sharpe and +0.0156 pp annualized, bought with 3.00x annualized turnover and a 47% drawdown;
   over the walk-forward window the excess is +0.0215 Sharpe. It is materially larger only on
   the 2018-2026 test window (+0.0674 Sharpe, +1.3977 pp annualized, drawdown -34.13% vs the
   benchmark's -37.43%), which is inside the pre-registered 0-1.5% excess-return band but is not
   the pre-registered evaluation statistic and is not a promotion gate.
3. The pre-registered walk-forward gate **fails** (0.847243 < 0.9), which by the pre-stated
   falsification condition rejects the hypothesis. The countervailing evidence is recorded too:
   91.7% positive folds, the plateau check passes, and the test-window Sharpe is 0.686168.
4. The walk-forward gate statistic and the long-sample statistic measure **different windows**:
   the 10-year burn-in puts the first fold test window at 2008-09-17, so the 2,448 invested
   sessions before it (Sharpe 0.182379, max DD -36.32%) are excluded from the folds. In
   addition, the gate statistic is the mean of 36 **overlapping** 12-month Sharpes, not the
   Sharpe of the concatenated covered window (0.590049). Neither adjustment can be used to
   rescue the gate: the pre-registered rule is applied as written.
5. The repository engine does not implement the frozen rebalance schedule; this is a *measurement
   defect in the shared engine*, not a candidate defect, and it is documented for the next cycle.

## Number of trials

1 headline configuration (the pre-registered baseline) + 2 companion paths (engine daily
re-rank, full sample incl. warmup) + 3 plateau lookbacks = 6 evaluated configurations, of which
the candidate-config equivalents are 4 distinct strategy configurations. The remaining 15 cells of
the pre-registered 18-configuration grid were not evaluated.

## Decision / label

**Rejected/failed** (pre-registered falsification condition met: walk-forward mean OOS Sharpe
0.847243 < 0.9). The candidate is not promotable; live deployment remains unsupported.

## Reproduction commands

```bash
python research/sectorrotation_long_sample_feasibility.py   # OVERALL: PASS (12/12 checks)
python -m pytest -q                                          # full suite
git status --porcelain data/                                 # empty: no market data touched
```

## Evidence artifacts

- `research/sectorrotation_long_sample_feasibility.py` (the tool)
- `research/reports/sectorrotation_long_sample_feasibility_001.md` (the report)
- `research/experiments/sectorrotation_long_sample_feasibility_001.md` (this record)
- `tests/test_sectorrotation_long_sample_feasibility.py` (7 regression tests)
