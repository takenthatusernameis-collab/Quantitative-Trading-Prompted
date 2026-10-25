# Experiment: `leadlag_001` evaluation (leadlag_001_evaluation)

**Cycle 939.** Execution of the **frozen** pre-registration
(`research/hypotheses/leadlag_001.md` + `config/leadlag_candidate_001.yaml`, freeze commit
**ace2643**). The frozen values are re-asserted by the tool before the run; a
post-freeze edit of the config fails closed. No threshold, gate, cost model, universe or
Sharpe convention was changed after the result was known; nothing under `data/` or
`config/` was written; the fetcher was never called; no other candidate was executed,
re-tuned or re-ranked.

## Hypothesis reference

`research/hypotheses/leadlag_001.md` (frozen at `ace2643`).

## Data used

- **Source**: the committed parquet cache
  `data/raw/{CL-F,GC-F,NG-F,ZB-F,USO,BNO,UNG,GSG,GLD,TLT}.parquet` (the fetcher is never called).
- **Date range**: 2015-01-02 .. 2026-10-15
- **Frequency**: daily, session hours
- **Universe**: CL-F, GC-F, NG-F, ZB-F, USO, BNO, UNG, GSG, GLD, TLT; the **complete cross-section** of the ten
  instruments is the panel: 2960 sessions out of a 6102-session
  union calendar (calendar churn 51.49%, because the futures and the ETF legs
  have different trading calendars).
- **Point-in-time treatment**: the futures signal at session `t` uses only closes up to
  and including `t`; the weights formed at `t` become effective at `t+1` (one-session lag)
  and are held until the next rebalance.

## Configuration (frozen)

| Item | Value |
|---|---|
| Signal | sign of the futures leg's trailing 5-session return; long the ETF leg when positive, cash otherwise |
| Pairs | CL-F/USO, CL-F/BNO, GC-F/GLD, NG-F/UNG, ZB-F/TLT (five pre-registered; components of the one configuration, not a grid) |
| Construction | long-only; 0.2 of the book per pair (equal weight), cash otherwise; gross exposure <= 1.0 |
| Rebalance | every 5 sessions, anchored on the panel's first session; 52 rebalances/yr |
| Signal lag | 1 session |
| Cost model | 1.0 bp commission + 2.0 bp slippage = **3.0 bp per unit of weight change**; 2.00% annual risk-free |
| Benchmark | cash (the rule is a directional tilt on the ETF leg only; the cash return is 0) |
| Walk-forward | 10-year train, 12-month test, 6-month step, 21-day purge, 21-day embargo |
| Trials | **5** (the five pre-registered pairs, deflated through the DSR) |
| Data-quality rules | a futures signal whose trailing window contains a detected roll date or a non-positive close is **unusable**: the pair stays flat |

## Number of trials

**5.** The five pre-registered pairs are the five components of one
configuration, deflated through the Deflated Sharpe Ratio; the Cycle-934 shortlist's
measured effective-bet count on this panel is **2.96**, so the
deflation is not generous. No parameter search, no variant, no grid.

## Results

### Walk-forward folds (3 folds)

| Fold | Test start | Test end | Sessions | Sharpe (canonical) | Excess over cash (Sharpe) | Trades | Max drawdown |
|---|---|---|---|---|---|---|---|
| 1 | 2024-09-30 | 2025-09-16 | 241 | -0.629718 | -0.629718 | 47 | -12.9966% |
| 2 | 2025-03-25 | 2026-03-11 | 242 | -0.176571 | -0.176571 | 45 | -12.9966% |
| 3 | 2025-09-17 | 2026-09-03 | 243 | 1.027363 | 1.027363 | 40 | -10.3860% |

### Gate statistics

| Statistic | Value | Gate | Outcome |
|---|---|---|---|
| Walk-forward mean OOS Sharpe (canonical) | 0.073691 | >= 0.9 | FAIL |
| Walk-forward median OOS Sharpe | -0.176571 | - | - |
| Walk-forward std of OOS Sharpe | 0.856418 | - | - |
| Positive-fold rate | 0.3333 | >= 0.5 | FAIL |
| Pooled OOS trades | 132 | > 100 | PASS |
| Pooled out-of-sample sessions | 484 | - | - |
| Net excess over cash (annualized) | 3.3555%/yr | - | - |
| Net excess over the 2.00% risk-free hurdle (annualized) | 1.3555%/yr | > 0 | PASS |
| Net excess 95% CI (moving block, 2000 draws, block 22, seed 20240101) | [-13.5760%, 21.6097%]/yr | excludes zero | FAIL |
| Fold-Sharpe 95% CI (moving block, block 2) | [-0.478669, 1.027363] | - | - |
| Deflated Sharpe Ratio (N = 5) | -0.590604 (probability 0.277393) | > 0 | FAIL |
| Absolute out-of-sample Sharpe | 0.267807 | - | - |

### Cost model, turnover and the hurdle

| Quantity | Value |
|---|---|
| Measured gross scale (frozen, shortlist Cycle 934) | 30.1518%/yr |
| Required capture (frozen, shortlist Cycle 934) | 5.1738% of the gross scale |
| Realized turnover | 25.5124 units/yr (shortlist proxy: 52.00 units/yr) |
| Realized cost drag | 0.7654%/yr (shortlist proxy: 1.5600%/yr) |

### Data quality: the detected roll windows and the CL-F defect

| Futures leg | Detected rolls | First roll | Last roll | Roll-affected signal sessions | Unusable signal sessions (all rules) | Share of the leg's sessions |
|---|---|---|---|---|---|---|
| CL-F | 127 | 2015-02-27 | 2026-09-23 | 762 | 769 | 25.94% |
| GC-F | 72 | 2015-02-24 | 2026-07-07 | 432 | 437 | 14.74% |
| NG-F | 125 | 2015-04-09 | 2026-08-28 | 750 | 755 | 25.46% |
| ZB-F | 62 | 2015-04-15 | 2026-10-14 | 368 | 373 | 12.58% |

- **Two counts are published on purpose.** The frozen config's
  `data_quality.unusable_signal_sessions` block records the **roll-affected**
  count (the roll rule alone: CL-F 762, GC-F 432, NG-F 750, ZB-F 368), which the
  evaluator reproduces exactly. The **unusable** column adds the non-positive close and
  the missing-history sessions (the first five sessions of every futures leg), i.e. the
  sessions on which the pair is flat for one reason or another.
- **CL-F non-positive close**: 1 session(s)
  (2020-04-20), close value
  -37.63.
  The affected signal sessions are excluded (the pair stays flat); no return is computed
  that spans the defective close.
- **Roll detection is ex-post**: the committed detector classifies a session using up to
  eight forward sessions, so the roll-affected sessions are a *backtest cleaning*, not a
  tradable point-in-time signal. A live rule would have to detect the roll with the same lag.
- **Net excess with the roll windows kept** (the same rule without the roll exclusion):
  4.1456%/yr, walk-forward mean OOS Sharpe
  0.061885; **cleaned**: 3.3555%/yr,
  walk-forward mean OOS Sharpe 0.073691.

### Per-pair attribution (out of sample)

| Pair | Net excess (annualized) | Sharpe | Trades | Share of OOS sessions long |
|---|---|---|---|---|
| CL-F/USO | 0.3343% | 0.069293 | 54 | 35.12% |
| CL-F/BNO | 0.9651% | 0.202878 | 54 | 35.12% |
| GC-F/GLD | 3.5534% | 0.918335 | 52 | 55.58% |
| NG-F/UNG | -0.5751% | -0.092239 | 44 | 32.85% |
| ZB-F/TLT | -0.9223% | -0.590778 | 41 | 42.36% |

- **Without the two CL-F pairs** the net excess over cash is
  2.0560%/yr (Sharpe 0.271402);
  the two CL-F pairs alone contribute 1.2994%/yr.

## Falsification condition (pre-registered) and outcome

| # | Condition | Observed | Requirement | Outcome |
|---|---|---|---|---|
| i | walk-forward mean OOS Sharpe (net, canonical) >= 0.9 | 0.073691 | 0.9 | **FIRED** |
| ii | net excess over cash bootstrap 95% CI excludes zero after the deflation for the five pairs (DSR > 0) | CI [-13.5760%, 21.6097%]/yr, DSR -0.590604 | CI excludes zero and DSR > 0 | **FIRED** |
| iii | the excess does not disappear once the detected roll windows are excluded | net excess with the roll windows 4.1456%/yr, cleaned 3.3555%/yr | the excess does not disappear when the roll windows are excluded | not fired |
| iv | the excess is not carried by the CL-F window | full book 3.3555%/yr, without the CL-F pairs 2.0560%/yr | the excess survives without the CL-F pairs | not fired |

**Rejected/Failed**

## Decision

The candidate is **falsified**: condition(s) i, ii fired. It is labelled **Rejected/Failed**; it is not promoted, not simulated and not paper-traded, and its configuration is retired as written (no variant is opened).

**No other candidate's verdict changes.** The incumbent `tsmomentum_spytrend_001` stays a
**Credible Candidate** and **NO-GO** for promotion; every closed line keeps its committed
status.

## Reproduction commands

```bash
python research/leadlag_001_evaluation.py
python -m pytest -q tests/test_leadlag_001_evaluation.py
git status --porcelain data/
git diff --name-only HEAD -- config/settings.yaml
```
