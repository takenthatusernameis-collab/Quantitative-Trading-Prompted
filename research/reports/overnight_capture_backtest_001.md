# Cycle 880 - Overnight-Session Capture Candidate (`overnight_capture_001`)

**Generated:** 2026-10-19 | **Code revision at run:** 8b04295 | **Script:** `research/overnight_capture_backtest.py`
**Hypothesis (pre-registered before execution):** `research/hypotheses/overnight_capture_001.md`
**Frozen config:** `config/overnight_capture_001.yaml` (sha256[:12] = bb44adfbc500)
**Decision label:** **Rejected/Failed** (see section 9)

Reproduction: `python research/overnight_capture_backtest.py` (exit 0, `OVERALL: PASS`)

---

## 1. Data-integrity pre-check

The committed cache in `data/raw/` was read directly (no network, no writes).

```
sym      rows        start          end  nanO  nanC  dup  ohlc_v
SPY      8487   1993-01-29   2026-10-16     0     0    0       0
QQQ      6945   1999-03-10   2026-10-16     0     0    0       0
IWM      6637   2000-05-26   2026-10-16     0     0    0       0
```

- **Raw vs. adjusted:** the fetcher calls yfinance with `auto_adjust=False`
  (`src/data/yfinance_fetcher.py`), and an independent fresh download over
  2024-01-01..2024-02-01 shows the cached `Close` matches the **raw** series
  (max abs diff 0.000000 over all 21 sessions for SPY/QQQ/IWM) and differs from
  the adjusted series (SPY cached 472.65 vs adjusted 457.67). The exploratory
  diagnostic's caveat #5 (which asserts the opposite) is **wrong for the
  committed cache** and is corrected here.
- **Ex-dividend implication (conservative):** the overnight leg does not receive
  dividends; on raw prices the overnight return on an ex-dividend date is biased
  *downward*. The measured overnight gross return is therefore a **lower bound**
  and the cost disadvantage below is not an artefact of dividend treatment.
- **Open/Close alignment:** 0 sessions with a missing Open on the common
  calendar; 0 OHLC violations; 0 duplicate dates.
- **Session-leg identity:** `(1+overnight)*(1+intraday) - 1 == close-to-close`
  holds to 2.220e-16 (per asset, per session).

## 2. Walk-forward design (asserted)

`generate_walkforward_splits(train=10y, test=12m, step=6m, purge=21d, embargo=21d)`
over 2000-05-26 -> 2026-10-16.

- folds: **33** (asserted in the script)
- first fold: train 2000-05-26 -> 2010-01-21 | test 2010-02-22 -> 2011-02-08
- last fold: train 2015-11-10 -> 2025-07-07 | test 2025-08-06 -> 2026-07-23

The strategy has no fitted parameter, so the train window only bounds each fold;
the per-fold statistic is the test-period net Sharpe.

## 3. Full-sample net metrics (3 bp/unit decision configuration)

```
leg                  ann_ret   sharpe  canon_sh  sortino    maxDD  ann_turn   cost/yr  trades
overnight            -0.0616  -0.6679   -0.4590  -0.8195  -0.8558     504.0    0.1512    6637
intraday             -0.1507  -0.9567   -0.8259  -1.2908  -0.9871     504.0    0.1512    6637
close_to_close        0.0782   0.2691    0.4564   0.3564  -0.5966       0.0    0.0000       1
```

- gross overnight annualized return, **before** any cost:
  0.0916
- annualized cost drag at 3 bp/unit: **15.12%/yr** (504 units of turnover x 3 bp).
  The pre-registration stated "~1.51%/yr"; that figure is an arithmetic error
  by a factor of 10 and is disclosed as an erratum in
  `research/hypotheses/overnight_capture_001.md` (section "Erratum"). The
  decision configuration (3 bp/unit), the gates and the falsification
  conditions are unchanged.
- The **gross** overnight effect is real and large (+9.16%/yr for the basket);
  the net result is negative because an overnight-only leg must round-trip
  **twice per session** (sell at the open, buy back at the close), i.e. 504
  units of annual turnover, and the repository's flat 3 bp/unit cost model
  charges 15.12%/yr for it.

## 4. Per-fold walk-forward table (net of 3 bp/unit)

```
fold  test_start    test_end    n   sharpe    canon   ann_ret    maxDD trades sharpe_c2c
   1  2010-02-22  2011-02-08  245  -0.2575  -0.0296   -0.0103  -0.1037    245     1.2545
   2  2010-08-17  2011-08-03  244  -0.3533  -0.0964   -0.0136  -0.0930    244     1.4031
   3  2011-02-09  2012-01-26  243  -0.8508  -0.6868   -0.1106  -0.2044    243    -0.0600
   4  2011-08-04  2012-07-20  243  -0.8826  -0.7210   -0.1137  -0.1319    243     0.2413
   5  2012-01-27  2013-01-14  242  -1.0900  -0.8540   -0.0762  -0.1122    242     0.6571
   6  2012-07-23  2013-07-09  241  -0.4284  -0.1329   -0.0132  -0.0716    241     1.5143
   7  2013-01-15  2014-01-01  243  -0.6030  -0.2788   -0.0211  -0.0563    243     2.4308
   8  2013-07-10  2014-06-26  244  -0.4404  -0.0881   -0.0074  -0.0478    244     1.6266
   9  2014-01-02  2014-12-19  245  -1.0724  -0.7769   -0.0558  -0.0961    245     0.7172
  10  2014-06-27  2015-06-15  243  -1.7032  -1.4627   -0.1009  -0.0978    243     0.6507
  11  2014-12-22  2015-12-08  243  -1.2895  -1.1253   -0.1217  -0.1559    243     0.0274
  12  2015-06-16  2016-06-01  243  -1.6790  -1.6267   -0.1936  -0.2211    243    -0.2073
  13  2015-12-09  2016-11-24  243  -2.0008  -1.9253   -0.1755  -0.1910    243     0.4403
  14  2016-06-02  2017-05-19  244  -1.0315  -0.7228   -0.0503  -0.0582    244     1.5100
  15  2016-11-25  2017-11-13  244  -0.8153  -0.3746   -0.0188  -0.0390    244     1.9736
  16  2017-05-22  2018-05-08  243   0.1834   0.5124    0.0321  -0.0449    243     1.1094
  17  2017-11-14  2018-10-31  243  -0.1215   0.1728    0.0105  -0.0659    243     0.2655
  18  2018-05-09  2019-04-25  242  -0.8036  -0.5452   -0.0499  -0.0853    242     0.3550
  19  2018-11-01  2019-10-18  242  -0.8025  -0.5687   -0.0591  -0.1233    242     0.3649
  20  2019-04-26  2020-04-13  243  -1.1372  -1.0814   -0.2372  -0.3037    243    -0.3210
  21  2019-10-21  2020-10-06  243  -0.1631   0.0428   -0.0208  -0.2948    243     0.5086
  22  2020-04-14  2021-03-31  244   2.8580   2.5412    0.4551  -0.0429    244     2.8361
  23  2020-10-07  2021-09-23  243   1.4355   1.5547    0.1701  -0.0543    243     2.3134
  24  2021-04-01  2022-03-18  244  -0.9104  -0.6904   -0.0727  -0.1102    244     0.1961
  25  2021-09-24  2022-09-12  243  -1.7596  -1.7291   -0.2048  -0.2411    243    -0.6266
  26  2022-03-21  2023-03-07  242  -2.0364  -2.1510   -0.2776  -0.2748    242    -0.5426
  27  2022-09-13  2023-08-30  243  -1.4139  -1.3035   -0.1583  -0.1483    243     0.4109
  28  2023-03-08  2024-02-22  242  -0.6094  -0.3438   -0.0333  -0.0756    242     1.7266
  29  2023-08-31  2024-08-16  242   0.1371   0.3740    0.0345  -0.0715    242     1.2844
  30  2024-02-23  2025-02-10  242   1.1973   1.3367    0.1537  -0.0715    242     1.1032
  31  2024-08-19  2025-08-05  241  -0.3707  -0.1607   -0.0312  -0.2049    241     0.4749
  32  2025-02-11  2026-01-28  242  -0.7165  -0.5213   -0.0747  -0.1746    242     0.7483
  33  2025-08-06  2026-07-23  242  -0.2594  -0.0191   -0.0077  -0.1095    242     1.4884
```

**Pooled OOS:** 8016 | pooled net annualized return: -0.051924

## 5. Pooled out-of-sample statistics

- pooled canonical Sharpe (arithmetic, rf 0): -0.389216
- pooled backtest-scale Sharpe (CAGR, rf 2%): -0.605673
- DSR (N = 3, sr_target 0): -2.446673 -> **REJECTED**
- PSR vs the 0.9 gate: 0.000000 (normal approx 0.000000), bootstrap SE of the Sharpe 0.210405
- block-bootstrap 95% CI: [-0.788295, 0.034214] (n = 1000, block = 22, seed = 42)

## 6. Cost-sensitivity row (3 / 5 / 10 bp per unit; N = 3, never a selection grid)

```
3.0 bp/unit | WF mean OOS Sharpe   -0.5997 | pooled ann. return   -0.0519 | pooled canonical Sharpe   -0.3892
5.0 bp/unit | WF mean OOS Sharpe   -1.5469 | pooled ann. return   -0.1429 | pooled canonical Sharpe   -1.2380
10.0 bp/unit | WF mean OOS Sharpe  -3.5375 | pooled ann. return   -0.3340 | pooled canonical Sharpe  -3.3601
```

## 7. Benchmarks on identical folds

| leg | WF mean OOS Sharpe (net) |
|---|---|
| overnight (candidate) | -0.599718 |
| close-to-close equal weight | 0.844696 |
| intraday only | -0.957874 |

overnight minus close-to-close: -1.444414
The candidate **loses** to passive close-to-close holding of the identical
basket on identical folds, so the overnight leg is not an edge: the gross
overnight premium is consumed by the cost of the two daily round trips.

## 8. Rolling-63 gate-statistic dispersion (Cycle 879 carry-over)

Any rolling-63 statistic quoted for this candidate is reported next to its own
dispersion, per the Cycle 879 finding that the gate statistic fails in 39.16%
of the incumbent's own windows (an ordinary failure, not a structural break).

- rolling-63 canonical Sharpe windows on the candidate's own pooled OOS series: **7954**
- current trailing-63 pooled value: 0.168597
- windows below the 0.9 gate: **69.1979%** (false-negative rate on this candidate's own history)
- percentile of the current window: 58.5366%
- rolling median -0.334035, p10 -3.588319, p90 3.073308

The candidate's rolling window is itself deep inside the failing region: this
is not a marginal, gate-noise-limited result.

## 9. Gates and pre-registered falsification verdicts

| # | Pre-registered falsification condition | Observed | Verdict |
|---|---|---|---|
| F1 | WF mean OOS Sharpe >= 0.9 | -0.599718 | **FAIL** |
| F2 | positive fold rate >= 50% | 15.1515% | **FAIL** |
| F3 | pooled OOS trades > 100 | 8016 | PASS |
| F4 | net WF Sharpe > same-fold close-to-close | -0.599718 | **FAIL** |
| F5 | edge survives the 10 bp/unit cost row | -3.537547 | **FAIL** |
| - | DSR at N = 3 does not reject | -2.446673 | **REJECTED** |
| - | block-bootstrap 95% CI lower bound > 0 | -0.788295 | **FAIL** |

**DECISION: Rejected/Failed.** The candidate fails four of the five
pre-registered falsification conditions and is rejected by the DSR.

## 10. Interpretation and what this cycle establishes

1. The **gross** overnight effect is real in this data: +9.16%/yr annualized
   for the 1/3 SPY/QQQ/IWM basket over 6,637 sessions, and it dominates the
   intraday leg (which is ~0 gross). This **confirms the exploratory
   diagnostic's mechanism observation** and extends it to a cost-aware,
   walk-forward evaluation.
2. The effect is **not capturable** by the pre-registered strategy. An
   overnight-only leg must be flat during the day, so it round-trips twice per
   session: 504 units of annual turnover at the repository's flat 3 bp/unit
   model = 15.12%/yr of cost drag against a +9.16%/yr gross premium. Net WF
   mean OOS Sharpe -0.599718; 15.2% of folds positive.
3. The mechanism is **not equity beta**: the overnight leg underperforms the
   identical close-to-close basket on identical folds by
   -1.444414 Sharpe units. The negative Sharpe is a cost result, not a market-direction result.
4. **Structural consequence for the research program:** any candidate that is
   flat for part of the session must be evaluated against its own turnover
   cost *before* being short-listed, because the gross signal size (9%/yr) is
   smaller than the cost of the daily round trip (15%/yr). A session-timing
   candidate that can avoid the second daily round trip (e.g. a position held
   continuously with only the *exposure* timed rather than the position) would
   have a different cost structure and is a **different** hypothesis; it is not
   tested here and must not be inferred from this result.
5. The candidate is **rejected**, so no promotion, no deployment and no change
   to the incumbent is implied. The incumbent remains **NO-GO**.

## 11. Reproduction

```
python research/overnight_capture_backtest.py     # OVERALL: PASS, DECISION: Rejected/Failed
python research/go_no_go_evaluation.py             # NO-GO, side_effect_free: True
python -m pytest -q                                # 95 existing + 8 new tests
git status --porcelain data/ config/               # empty
```

No file under `data/` or `config/` was modified; `config/overnight_capture_001.yaml`
is a NEW candidate config. No live trading, no credentials, no scheduled jobs,
no new dependencies, no change to the shared engine in `src/`.
