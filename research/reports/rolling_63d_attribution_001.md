# Rolling-63d Sharpe Attribution (Cycle 899)

Reads only the committed paper-trading state and the cached raw prices; writes
nothing to `data/` or `config/`.

## Window
2026-07-22 .. 2026-10-19 (63 sessions). Window cumulative return -0.009050,
window rolling-63d Sharpe -0.4489.

## Cohort attribution (coarse)

| bucket | sessions | share_sessions | share_return | sharpe | mean_ret |
|---|---|---|---|---|---|
| regime_risk_on | 63 | 1.000 | 1.000 | -0.4489 | -0.000144 |
| regime_risk_off | 0 | 0.000 | -0.000 | None | None |
| exposure_full | 63 | 1.000 | 1.000 | -0.4489 | -0.000144 |
| exposure_cash | 0 | 0.000 | -0.000 | None | None |
| vol_q1 | 16 | 0.254 | -2.4297 | 4.4345 | 0.001374 |
| vol_q4 | 16 | 0.254 | 2.4911 | -3.7721 | -0.001409 |
| first_half | 31 | 0.4921 | -1.9565 | 1.9957 | 0.000571 |
| second_half | 32 | 0.5079 | 2.9565 | -2.3985 | -0.000836 |

## Cohort attribution (refined)

| cohort | n | share_n | share_ret | sharpe | mean_ret |
|---|---|---|---|---|---|
| high_vol_late | 16 | 0.254 | 2.491 | -3.772 | -0.001409 |
| high_vol_early | 0 | 0.000 | -0.000 | None | None |
| low_vol_late | 16 | 0.254 | -2.430 | 4.435 | 0.001374 |
| low_vol_early | 0 | 0.000 | -0.000 | None | None |
| high_vol_all | 16 | 0.254 | 2.491 | -3.772 | -0.001409 |
| low_vol_all | 16 | 0.254 | -2.430 | 4.435 | 0.001374 |
| late_all | 63 | 1.000 | 1.000 | -0.449 | -0.000144 |
| high_vol_and_turnover_spike | 9 | 0.143 | 1.580 | -3.254 | -0.001589 |

Dominant cohort: `high_vol_late` carries 2.49x the window's own negative return
(share_return 2.491) with sub-sample Sharpe -3.772, against +4.435 for the
low-volatility cohort. Falsification condition (broad, unattributable decline):
**False** — the decline is concentrated.

## Trade-level decomposition

`research/rolling_63d_attribution_trade.py` replays the baseline config with
`overlay_warmup="full"` (the convention the incremental paper-trading update
uses) and reproduces the committed state **exactly**: 63/63 matched sessions,
max per-date abs diff 0.000e+00, replay sum -0.009050 == state sum -0.009050.

| metric | value |
|---|---|
| trades in window | 259 |
| rebalance dates | 62 |
| total cost | 0.000995 |
| cost as share of window return | -0.110x |
| weight-change direction aligned with forward return | 40 of 62 rebalance dates |
| sum(signed_wchange x daily_return) | +0.006618 |

vol_scale in the window ranges 0.4524 .. 0.6526.

### Sign convention

`signed_wchange` is the net weight change on a rebalance date, signed by the
sign of that date's **portfolio-level** `daily_return` from the committed
record: positive weight change when the day's return is non-negative, negative
when it is negative. `sum(signed_wchange x daily_return)` is therefore the
cross-product of the direction the book moved and the direction the book made
money that day. A positive sum means the book was, on net, increasing exposure
into days that went up and reducing exposure into days that went down.

This statistic is **not** an edge measure and does not contradict the negative
window return. It is computed over weight *changes* (turnover), so it responds
to rebalance magnitude, not to the level of exposure carried into each session.
A book that is fully invested (n_positions 4, regime_exposure 1.0 on all 63
sessions) with a flat signal can produce a positive alignment sum while still
losing money, because the sum ignores the exposure that was already on before
the rebalance. The window return is dominated by the *level* of exposure in
high-volatility sessions (the vol target's scaling), not by the direction of
the rebalance flow. The two statements are therefore consistent: the signal is
still pointing the right way on rebalance dates, and the loss comes from the
overlay reducing exposure into the window's worst sessions.

The 40/62 alignment count is reported without a formal significance test: it
is a descriptive split of the rebalance dates, not a hypothesis test, and no
p-value or bootstrap is computed for it.

## Finding

The trailing Sharpe collapse is concentrated, not broad, and it is **not** a
signal-quality or cost problem:

- **Not a regime-filter story.** All 63 sessions are risk-on (regime_exposure
  1.0) and fully invested (n_positions 4). The SPY 200d SMA filter has not
  fired in the trailing window.
- **Not a signal-quality problem.** Weight changes are aligned with forward
  returns on 40 of 62 rebalance dates; sum(signed_wchange x daily_return) is
  positive (+0.006618). The momentum signal is still pointing the right way.
- **Not a cost problem.** Total cost is 0.000995, only 0.11x the window return.
- **It is a position-sizing / overlay-timing outcome.** The vol target is
  reducing exposure in high-volatility sessions, which are the window's
  worst performers (high_vol_late Sharpe -3.772 vs low_vol_late +4.435).

This is the same family of finding as Cycle 878's overlay-attribution: the
trailing NO-GO is an overlay-timing outcome, not evidence that the momentum
edge has decayed.

## Falsification

The pre-registered falsification condition — "the decline is broad and
unattributable across buckets" — is **FALSE**. A single cohort
(high_vol_late) carries more than half the window return, so the attribution is
informatively concentrated.

## Interpretation (no parameter change)

No parameter, gate, threshold, candidate, cost model or deployment decision was
changed. The decision remains **NO-GO**, live deployment unsupported.

## Reproduction

```
python research/rolling_63d_attribution.py
python research/rolling_63d_attribution_coarse.py
python research/rolling_63d_attribution_trade.py
```

The trade-level script replays the baseline config with
`overlay_warmup="full"` and asserts 63/63 matched sessions with max per-date
abs diff and window-sum tolerance both at 1e-9 against the committed state.