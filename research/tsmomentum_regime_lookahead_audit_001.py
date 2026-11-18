"""Same-session feedback in the SPY-SMA regime filter: read-only audit.

Why this exists
---------------
The repository already found, documented and made opt-in a *deliberate*
correction for same-session feedback in the volatility estimate
(``lag_vol_estimate``; see
``research/reports/tsmomentum_same_session_vol_correction_001.md``).  The
regime filter has the same class of feedback and was never audited.

In ``src/simulation/engine.py``::

    def _regime_exposure(close, config):
        spy = close["SPY"]
        sma = spy.rolling(config.regime_window).mean()
        exposure = pd.Series(config.exposure_above, index=close.index)
        exposure[spy < sma] = config.exposure_below
        ...

and in ``research/run_cycle6.py``::

    exposure = pd.Series(1.0, index=close_a.index)
    exposure[spy < spy_sma] = 0.0
    ...
    weights = weights.mul(ef, axis=0)              # _apply_overlay

the exposure for session *t* is formed from session *t*'s own close (and an SMA
whose window includes session *t*), and it gates the position that earns
session *t*'s close-to-close return ``close[t] / close[t-1] - 1``.  The momentum
signal itself is correctly lagged one session (``build_weights`` shifts by 1),
so the regime factor is the only same-session input on the execution path.

That is one session of look-ahead: on every session that closes below its own
200-session SMA the strategy holds cash *for that session*, which it cannot
know before that session's return is realised.  Two committed documents assert
the opposite ("No lookahead bias: signals shifted 1 day, regime computed
point-in-time", ``research/reports/deployment_dossier_001.md``;
"weights shifted 1 day; SPY SMA computed point-in-time",
``research/reports/go_nogo_evaluation_001.md``).

What this script does
---------------------
Nothing is changed and nothing is promoted.  It quantifies the defect against
the committed cache and the committed paper-trading record:

* reproduces the published 48-fold walk-forward anchor (**0.947307**) on the
  committed (same-session) exposure path and fails closed if it does not;
* re-runs the same 48 folds with the regime exposure lagged one session
  (``exposure.shift(1)``, the point-in-time version);
* compares the post-2017 test period both ways (Sharpe, max drawdown,
  annualised return, trades);
* measures how much of the committed live record's return came from sessions
  whose exposure was set to cash using that session's own close.

Every write is confined to ``research/reports/``.  ``data/`` and ``config/``
are hashed before and after the run and the run fails if they differ.

Usage::

    /tmp/kilo-venv/bin/python research/tsmomentum_regime_lookahead_audit_001.py
"""

from __future__ import annotations

import hashlib
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import research.run_cycle6 as rc

REPORT_DIR = REPO_ROOT / "research" / "reports"
REPORT_PATH = REPORT_DIR / "tsmomentum_regime_lookahead_audit_001.md"
ANCHOR_WF_SHARPE = 0.947307
ANCHOR_TOLERANCE = 5e-7


def tree_digest(root: Path) -> str:
    """Stable sha256 over every file path+content under *root*."""
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def exposure_committed(close: pd.DataFrame, window: int = rc.SPY_SMA_WINDOW) -> pd.Series:
    """The committed regime exposure: session t's own close decides session t."""
    spy = close["SPY"]
    sma = spy.rolling(window).mean()
    exposure = pd.Series(1.0, index=close.index)
    exposure[spy < sma] = 0.0
    exposure[spy.isna() | sma.isna()] = 0.0
    return exposure


def exposure_point_in_time(
    close: pd.DataFrame, window: int = rc.SPY_SMA_WINDOW
) -> pd.Series:
    """The same rule, known only after session t-1 has closed."""
    return exposure_committed(close, window).shift(1).fillna(0.0)


def _period_returns(
    close: pd.DataFrame,
    start: str,
    end: str,
    exposure: pd.Series,
) -> tuple[pd.Series, pd.DataFrame]:
    """Mirror of ``run_cycle6._eval_candidate_period`` with a supplied exposure."""
    weights = rc.build_weights(
        close, lookback=rc.LOOKBACK, skip=rc.SKIP, top_fraction=rc.TOP_FRACTION
    )
    common = close.index.intersection(weights.index)
    close_a = close.loc[common]
    weights_a = weights.loc[common]
    daily_ret = close_a.pct_change().fillna(0.0)

    cw, net_ret, _ = rc._apply_overlay(
        daily_ret,
        weights_a,
        exposure_factor=exposure.reindex(close_a.index),
    )
    mask = (cw.index >= start) & (cw.index <= end)
    return net_ret[mask], cw[mask]


def walkforward(close: pd.DataFrame, exposure: pd.Series) -> dict:
    """48-fold walk-forward with a fixed exposure series (no re-optimisation)."""

    def config_fn(
        symbols: list[str], start: str, end: str
    ) -> tuple[pd.Series, pd.DataFrame]:
        return _period_returns(close, start, end, exposure)

    wf = rc.evaluate_walkforward(
        rc.SYMBOLS,
        rc.START_DATE,
        rc.END_DATE,
        config_fn,
        train_years=rc.WF_TRAIN_YEARS,
        test_months=rc.WF_TEST_MONTHS,
        step_months=rc.WF_STEP_MONTHS,
        purge_days=rc.WF_PURGE_DAYS,
        embargo_days=rc.WF_EMBARGO_DAYS,
    )
    return {"wf_df": wf, "summary": rc.summarize_walkforward(wf)}


def test_period_metrics(close: pd.DataFrame, exposure: pd.Series) -> dict:
    """Post-2017 test period metrics for one exposure convention."""
    weights = rc.build_weights(
        close, lookback=rc.LOOKBACK, skip=rc.SKIP, top_fraction=rc.TOP_FRACTION
    )
    common = close.index.intersection(weights.index)
    close_a = close.loc[common]
    daily_ret = close_a.pct_change().fillna(0.0)
    test_mask = close_a.index > rc._utc(rc.VAL_END)
    _, net_ret, metrics = rc._apply_overlay(
        daily_ret[test_mask],
        weights.loc[common][test_mask],
        exposure_factor=exposure.reindex(close_a.index)[test_mask],
    )
    return {"net_ret": net_ret, "metrics": metrics}


def live_record_off_days(close: pd.DataFrame) -> dict:
    """Same-day base-portfolio return on the record's own cash-out sessions."""
    state_path = REPO_ROOT / "data" / "processed" / "paper_trading_state.yaml"
    import yaml

    state = yaml.safe_load(state_path.read_text())
    history = state["run_history"]
    dates = [row["date"] for row in history]
    exposure = [float(row["regime_exposure"]) for row in history]

    weights = rc.build_weights(
        close, lookback=rc.LOOKBACK, skip=rc.SKIP, top_fraction=rc.TOP_FRACTION
    )
    common = close.index.intersection(weights.index)
    base_ret = (weights.loc[common] * close.loc[common].pct_change().fillna(0.0)).sum(
        axis=1
    )

    off = [d for d, e in zip(dates, exposure) if e == 0.0]
    ts_off = [pd.Timestamp(d, tz="UTC") for d in off if pd.Timestamp(d, tz="UTC") in base_ret.index]
    series = base_ret.reindex(ts_off).dropna()
    on = [d for d, e in zip(dates, exposure) if e > 0.0]
    ts_on = [pd.Timestamp(d, tz="UTC") for d in on if pd.Timestamp(d, tz="UTC") in base_ret.index]
    on_series = base_ret.reindex(ts_on).dropna()

    return {
        "n_record_sessions": len(history),
        "n_off_days": len(series),
        "n_on_days": len(on_series),
        "off_mean": float(series.mean()) if len(series) else 0.0,
        "off_median": float(series.median()) if len(series) else 0.0,
        "off_sum": float(series.sum()) if len(series) else 0.0,
        "on_mean": float(on_series.mean()) if len(on_series) else 0.0,
        "off_worst": float(series.min()) if len(series) else 0.0,
        "off_best": float(series.max()) if len(series) else 0.0,
        "n_off_negative": int((series < 0).sum()),
        "last_run_date": state["last_run_date"],
        "record_sharpe": float(state["rolling_sharpe_63d"]),
        "record_nav": float(state["current_nav"]),
    }


def fmt(value: float, digits: int = 6) -> str:
    return f"{value:.{digits}f}"


def main() -> int:
    data_digest_before = tree_digest(REPO_ROOT / "data")
    config_digest_before = tree_digest(REPO_ROOT / "config")

    close = rc._load_close(rc.SYMBOLS)
    committed = exposure_committed(close)
    pit = exposure_point_in_time(close)

    flipped = int((committed != pit).sum())
    below = int((committed == 0.0).sum())

    print("=== regime-filter same-session feedback audit ===")
    print(f"sessions loaded:      {len(close)} ({close.index[0].date()} -> {close.index[-1].date()})")
    print(f"cash-out sessions:    {below}")
    print(f"sessions affected by the one-session lag: {flipped}")

    # --- anchor: the published walk-forward record must reproduce ---
    default_wf = walkforward(close, committed)
    anchor = float(default_wf["summary"]["mean_test_sharpe"])
    print(f"anchor 48-fold mean OOS Sharpe: {anchor:.6f} (published {ANCHOR_WF_SHARPE})")
    if abs(anchor - ANCHOR_WF_SHARPE) > ANCHOR_TOLERANCE:
        print(
            f"FAIL: committed exposure path does not reproduce the published "
            f"anchor ({anchor:.6f} != {ANCHOR_WF_SHARPE})",
            file=sys.stderr,
        )
        return 2

    lagged_wf = walkforward(close, pit)
    lagged_anchor = float(lagged_wf["summary"]["mean_test_sharpe"])
    print(f"point-in-time 48-fold mean OOS Sharpe: {lagged_anchor:.6f}")

    committed_test = test_period_metrics(close, committed)
    lagged_test = test_period_metrics(close, pit)
    record = live_record_off_days(close)

    fold_cmp = default_wf["wf_df"][["test_sharpe"]].copy()
    fold_cmp["pit_sharpe"] = lagged_wf["wf_df"]["test_sharpe"].to_numpy()
    fold_cmp["delta"] = fold_cmp["pit_sharpe"] - fold_cmp["test_sharpe"]
    worse = int((fold_cmp["delta"] < 0).sum())
    better = int((fold_cmp["delta"] > 0).sum())

    data_digest_after = tree_digest(REPO_ROOT / "data")
    config_digest_after = tree_digest(REPO_ROOT / "config")
    read_only = (
        data_digest_before == data_digest_after
        and config_digest_before == config_digest_after
    )
    print(f"read-only (data/ + config/ byte-identical): {read_only}")
    if not read_only:
        print("FAIL: data/ or config/ changed during a read-only audit", file=sys.stderr)
        return 3

    def metrics_row(label: str, metrics: dict) -> str:
        return (
            f"| {label} | {fmt(metrics['sharpe_ratio'])} | "
            f"{fmt(metrics['annualized_return'])} | "
            f"{fmt(metrics['max_drawdown'])} | "
            f"{int(metrics['trade_count'])} | "
            f"{fmt(metrics['avg_daily_turnover'])} |"
        )

    m_committed = committed_test["metrics"]
    m_lagged = lagged_test["metrics"]

    report = f"""# Regime-filter same-session feedback: read-only audit (tsmomentum_regime_lookahead_audit_001)

*Generated: {datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}*
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
| Committed (session *t*'s own close) | {fmt(anchor)} | — | — |
| Point-in-time (`shift(1)`) | {fmt(lagged_anchor)} | {better} | {worse} |

The committed path reproduces the published anchor exactly
(`research/experiments/tsmomentum_regime_filter_wf_001.md`: 48 folds,
mean OOS Sharpe **0.947307**, 6013 pooled OOS trades), so both columns are
computed by the same machinery on the same cache.

### Post-2017 test period (the period the live record is measured against)

| Exposure convention | Sharpe | Ann. return | Max drawdown | Trades | Avg daily turnover |
| --- | --- | --- | --- | --- | --- |
{metrics_row("Committed (same-session)", m_committed)}
{metrics_row("Point-in-time (shift(1))", m_lagged)}

### Committed live record

| Quantity | Value |
| --- | --- |
| Record sessions | {record['n_record_sessions']} |
| Sessions recorded at zero exposure | {record['n_off_days']} |
| Sessions recorded at full exposure | {record['n_on_days']} |
| Mean base-portfolio return on the cash-out sessions | {fmt(record['off_mean'], 8)} |
| Median base-portfolio return on the cash-out sessions | {fmt(record['off_median'], 8)} |
| Sum of base-portfolio returns on the cash-out sessions | {fmt(record['off_sum'], 8)} |
| Worst / best base-portfolio return on a cash-out session | {fmt(record['off_worst'], 8)} / {fmt(record['off_best'], 8)} |
| Cash-out sessions with a negative base return | {record['n_off_negative']} of {record['n_off_days']} |
| Mean base-portfolio return on full-exposure sessions | {fmt(record['on_mean'], 8)} |

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
| Committed-path anchor reproduces 0.947307 | {fmt(anchor)} |
| Fold comparison computed on both paths | {len(fold_cmp)} folds |
| `data/` byte-identical before/after | {data_digest_before == data_digest_after} |
| `config/` byte-identical before/after | {config_digest_before == config_digest_after} |
| Exposure sessions affected by the lag | {flipped} |
| Cash-out sessions in the loaded history | {below} |
"""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report)
    print(f"report written -> {REPORT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
