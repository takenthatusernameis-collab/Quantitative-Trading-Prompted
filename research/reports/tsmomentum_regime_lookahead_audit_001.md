# Regime-filter same-session feedback: read-only audit (tsmomentum_regime_lookahead_audit_001)

*Generated: 2026-11-19T02:12:33Z*
*Candidate: `tsmomentum_spytrend_001` (incumbent). Nothing is promoted, re-fit or re-ranked.*
*Reproduction: `/tmp/kilo-venv/bin/python research/tsmomentum_regime_lookahead_audit_001.py`*

## 1. Finding

The SPY 200-session SMA regime filter decides session *t*'s exposure from
session *t*'s own close:

* `src/simulation/engine.py::_regime_exposure` builds `sma = spy.rolling(200).mean()`
  (window **includes** `t`) and sets `exposure[spy < sma] = 0.0`;
* `src/simulation/engine.py:450-452` multiplies that factor into
  `base_weights` for the **same** index row, and
  `_finalize` computes `gross_ret = (scheduled * asset_ret).sum(axis=1)` with
  `asset_ret = close.pct_change()`, i.e. the weight recorded at `t` earns
  `close[t] / close[t-1] - 1`;
* the research path is identical: `research/run_cycle6.py::_eval_candidate_period`
  and `_apply_overlay` (`weights.mul(ef, axis=0)`).

The momentum signal is correctly lagged one session
(`src/features/momentum.py::build_weights` ends with `weights.shift(1)`), so the
regime factor is the **only** same-session input on the execution path. The
practical meaning: on every session that closes below its own 200-session SMA,
the strategy is recorded as holding cash *for that session*, which it could not
have known before that session's return was realised.

Two committed documents assert the opposite, so this is a documentation/measurement
mismatch, not a design note:

* `research/reports/deployment_dossier_001.md:279` — "No lookahead bias: signals
  shifted 1 day, regime computed point-in-time";
* `research/reports/go_nogo_evaluation_001.md:75` — "weights shifted 1 day; SPY
  SMA computed point-in-time".

The live record inherits the same feedback: `src/simulation/paper_trading.py:288-296`
sets `daily_pnl = current_nav * latest["net_return"]`, and that `net_return` was
produced by the same-session gate.

## 2. Magnitude

The point-in-time variant is the committed rule shifted one session
(`exposure.shift(1).fillna(0.0)`): the exposure applied on session *t* is the one
that was knowable at the close of *t-1*. Nothing else changes — same universe,
same lookback/skip/top-fraction, same vol target, same drawdown control, same
3 bps round-trip cost, same fold design.

| Path | 48-fold mean OOS Sharpe | Folds improved by lagging | Folds worsened |
| --- | --- | --- | --- |
| Committed (session *t*'s own close) | 0.947307 | — | — |
| Point-in-time (`shift(1)`) | 0.153040 | 4 | 43 |

The committed path reproduces the published anchor exactly
(`research/experiments/tsmomentum_regime_filter_wf_001.md`: 48 folds,
mean OOS Sharpe **0.947307**, 6013 pooled OOS trades), so both columns are
computed by the same machinery on the same cache.

### Post-2017 test period (the period the live record is measured against)

| Exposure convention | Sharpe | Ann. return | Max drawdown | Trades | Avg daily turnover |
| --- | --- | --- | --- | --- | --- |
| Committed (same-session) | 1.333367 | 0.138454 | -0.077940 | 1218 | 0.052496 |
| Point-in-time (shift(1)) | 0.555815 | 0.069569 | -0.154646 | 1247 | 0.052496 |

### Committed live record

| Quantity | Value |
| --- | --- |
| Record sessions | 472 |
| Sessions recorded at zero exposure | 55 |
| Sessions recorded at full exposure | 411 |
| Mean base-portfolio return on the cash-out sessions | 0.00053990 |
| Median base-portfolio return on the cash-out sessions | 0.00113708 |
| Sum of base-portfolio returns on the cash-out sessions | 0.02969435 |
| Worst / best base-portfolio return on a cash-out session | -0.04991608 / 0.08283898 |
| Cash-out sessions with a negative base return | 25 of 55 |
| Mean base-portfolio return on full-exposure sessions | 0.00082150 |

"Base-portfolio return" is the equal-weight top-half momentum portfolio computed
from the committed cache — the return the ungated strategy would have earned on
that session. On the record's cash-out sessions that P&L was replaced by cash,
so the recorded return on those sessions is the return *after* using that
session's own close.

## 3. Interpretation and boundaries

* This is a **measurement defect of the same class** as the volatility-estimate
  same-session feedback that
  `research/reports/tsmomentum_same_session_vol_correction_001.md` already
  corrected behind the opt-in `lag_vol_estimate` switch. It was never audited
  for the regime factor.
* It is **not** a claim that the candidate has an edge after correction. The
  promotion decision is unchanged by this audit: `research/go_no_go_evaluation.py`
  reports **NO-GO** on the committed record, and this audit changes no state,
  no config, no threshold, no gate and no committed artifact.
* No production code is changed here. A correction would require an opt-in
  switch in `src/simulation/engine.py` plus `research/run_cycle6.py` (mirroring
  `lag_vol_estimate`), a default-path bit-identity proof, and a re-derivation of
  every published statistic — out of scope for a read-only audit and bounded as
  a follow-up task.
* Until that follow-up exists, the paper-trading record's returns and every
  published Sharpe statistic of this candidate are computed with one session of
  regime look-ahead, and the two committed documents quoted in section 1 are
  inaccurate on this point.

## 4. Verification

| Check | Observed |
| --- | --- |
| Committed-path anchor reproduces 0.947307 | 0.947307 |
| Fold comparison computed on both paths | 48 folds |
| `data/` byte-identical before/after | True |
| `config/` byte-identical before/after | True |
| Exposure sessions affected by the lag | 223 |
| Cash-out sessions in the loaded history | 2270 |
