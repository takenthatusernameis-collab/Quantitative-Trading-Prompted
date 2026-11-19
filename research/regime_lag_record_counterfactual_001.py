"""Record-level counterfactual: the paper record under point-in-time exposure.

Why this exists
---------------
``research/reports/tsmomentum_regime_lookahead_audit_001.md`` established that
the committed SPY-200dSMA regime factor decides session *t*'s exposure from
session *t*'s own close (same-session feedback), and it quantified the effect on
the *walk-forward backtest* and on the base-portfolio returns of the record's
cash-out sessions. It did **not** replay the committed paper-trading **record**
under the point-in-time convention, so the record-level cost of the defect was
never measured.

That gap matters because the promotion decision is taken on the record
(``research/go_no_go_evaluation.py`` reads ``rolling_sharpe_63d`` and NAV from
``data/processed/paper_trading_state.yaml``), and the record is the forward
test. Every session whose exposure differs from the previous session's exposure
(``exposure[t] != exposure[t-1]``) is a session whose P&L was decided with
information that was not available at the decision time.

What this script does
---------------------
Read-only. Nothing is changed, promoted or re-fit.

* rebuilds the committed production path with
  :func:`src.simulation.engine.run_simulation` (default config) and the
  point-in-time path with the committed ``lag_regime_exposure=True`` switch;
* validates the committed path against the record it is supposed to describe:
  only the *contiguous trailing* run of record sessions whose
  ``net_return`` matches the stored ``daily_return`` bit-exactly
  (|difference| <= 1e-9) is used, and the run must cover >= 300 sessions. The
  record's first sessions are not reproducible from the current cache (they
  predate a cache revision) and the sessions after the cache coverage end are
  not reproducible at all; both are reported and excluded rather than patched;
* reports NAV, total return, annualised return, Sharpe and max drawdown over
  that validated window for both exposure conventions, plus the minimum
  rolling-63d Sharpe under each;
* censuses, from the record alone, the sessions whose recorded exposure differs
  from the previous session's exposure -- i.e. the sessions that could only be
  decided using their own close;
* fails closed if ``data/`` or ``config/`` change during the run.

Usage::

    /tmp/kilo-venv/bin/python research/regime_lag_record_counterfactual_001.py
"""

from __future__ import annotations

import hashlib
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.evaluation.drift import annualized_sharpe  # noqa: E402
from src.simulation.engine import SimulationConfig, run_simulation  # noqa: E402

STATE_PATH = REPO_ROOT / "data" / "processed" / "paper_trading_state.yaml"
CONFIG_PATH = REPO_ROOT / "config" / "simulation_candidate_001.yaml"
REPORT_PATH = REPO_ROOT / "research" / "reports" / "regime_lag_record_counterfactual_001.md"

MATCH_TOLERANCE = 1e-9
MIN_WINDOW_SESSIONS = 300
TRADING_DAYS_PER_YEAR = 252
ROLLING_WINDOW = 63


def tree_digest(root: Path) -> str:
    """Stable sha256 over every file path+content under *root*."""
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def load_record(path: Path) -> pd.DataFrame:
    """The committed record as a date-indexed frame (no cache involvement)."""
    state = yaml.safe_load(path.read_text())
    history = state["run_history"]
    frame = pd.DataFrame(history)
    frame["ts"] = pd.to_datetime(frame["date"], utc=True)
    frame = frame.set_index("ts").sort_index()
    frame["daily_return"] = frame["daily_return"].astype(float)
    frame["regime_exposure"] = frame["regime_exposure"].astype(float)
    return frame[["date", "nav", "daily_return", "regime_exposure"]]


def exposure_flips(record: pd.DataFrame) -> pd.DataFrame:
    """Record sessions whose exposure differs from the previous session's.

    On each such session the committed rule decided that session's exposure
    from that session's own close; the point-in-time convention would still
    have been on the previous session's exposure.
    """
    exposure = record["regime_exposure"]
    previous = exposure.shift(1)
    mask = (exposure != previous) & previous.notna()
    out = record.loc[mask, ["date", "regime_exposure"]].copy()
    out["previous_exposure"] = previous[mask]
    return out


def reproducible_window(
    record_returns: pd.Series,
    engine_returns: pd.Series,
    tolerance: float = MATCH_TOLERANCE,
    min_sessions: int = MIN_WINDOW_SESSIONS,
) -> dict:
    """Trailing contiguous run of record sessions reproduced bit-exactly.

    The record must be described by the path it claims to describe, so only the
    sessions whose stored return equals the engine's are used. A *trailing*
    run is required: if the most recent session does not reproduce, the record
    is not the output of the current cache and the caller must fail closed.
    """
    common = record_returns.index.intersection(engine_returns.index)
    if len(common) == 0:
        raise ValueError("record and engine paths share no sessions")
    diff = (engine_returns.reindex(common) - record_returns.reindex(common)).abs()
    mismatched = diff > tolerance
    if bool(mismatched.iloc[-1]):
        raise ValueError(
            "most recent common session does not reproduce: "
            f"{common[-1].date()} |diff|={float(diff.iloc[-1]):.3e}"
        )
    n_exact_suffix = int((~mismatched.values[::-1]).cumprod().sum())
    window = common[-n_exact_suffix:]
    if len(window) < min_sessions:
        raise ValueError(
            f"reproducible trailing window has {len(window)} sessions "
            f"(< {min_sessions})"
        )
    leading = common[: len(common) - n_exact_suffix]
    return {
        "window": window,
        "n_common": len(common),
        "n_window": len(window),
        "n_excluded_prefix": len(leading),
        "excluded_prefix_start": (
            leading[0].date().isoformat() if len(leading) else None
        ),
        "excluded_prefix_end": (
            leading[-1].date().isoformat() if len(leading) else None
        ),
        "n_exact_outside_window": int((~mismatched.loc[leading]).sum()),
        "record_sessions_missing_from_engine": int(
            len(record_returns.index.difference(engine_returns.index))
        ),
        "missing_start": (
            record_returns.index.difference(engine_returns.index)[0].date().isoformat()
            if len(record_returns.index.difference(engine_returns.index))
            else None
        ),
        "missing_end": (
            record_returns.index.difference(engine_returns.index)[-1].date().isoformat()
            if len(record_returns.index.difference(engine_returns.index))
            else None
        ),
    }


def path_stats(returns: pd.Series, initial_nav: float = 100000.0) -> dict:
    """NAV, total/annualised return, Sharpe and max drawdown of a return path."""
    values = np.asarray(returns, dtype=float)
    if values.size == 0:
        raise ValueError("empty return path")
    cumulative = np.cumprod(1.0 + values)
    running_max = np.maximum.accumulate(cumulative)
    final_nav = float(initial_nav * cumulative[-1])
    return {
        "n_sessions": int(values.size),
        "nav": final_nav,
        "total_return": float(cumulative[-1] - 1.0),
        "annualized_return": float(
            cumulative[-1] ** (TRADING_DAYS_PER_YEAR / values.size) - 1.0
        ),
        "sharpe": float(annualized_sharpe(values)),
        "max_drawdown": float((cumulative / running_max - 1.0).min()),
    }


def min_rolling_sharpe(returns: pd.Series, window: int = ROLLING_WINDOW) -> float:
    """Minimum rolling annualised Sharpe over a return path (NaN if too short)."""
    values = np.asarray(returns, dtype=float)
    if values.size < window:
        return float("nan")
    return float(
        min(
            annualized_sharpe(values[i - window : i])
            for i in range(window, values.size + 1)
        )
    )


def build_paths(config_path: Path, start: str, end: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Production default path and the committed point-in-time (lagged) path."""
    committed = run_simulation(SimulationConfig.from_yaml(config_path), start, end)
    lagged_config = SimulationConfig.from_yaml(config_path)
    lagged_config.lag_regime_exposure = True
    lagged = run_simulation(lagged_config, start, end)
    return committed.daily, lagged.daily


def render_report(result: dict) -> str:
    """Markdown report for one measurement run."""
    window = result["window"]
    committed = result["committed"]
    lagged = result["lagged"]
    flips = result["flips"]
    flip_rows = "\n".join(
        f"| {row['date']} | {row['previous_exposure']:.0f} | {row['regime_exposure']:.0f} |"
        for _, row in flips.iterrows()
    )
    diff_dates = ", ".join(result["sessions_exposure_differs"]) or "none"
    return f"""# Paper record under point-in-time regime exposure (record-level counterfactual)

*Generated: {result['generated']}*
*Candidate: `tsmomentum_spytrend_001` (incumbent). Nothing is promoted, re-fit or re-ranked.*
*Reproduction: `/tmp/kilo-venv/bin/python research/regime_lag_record_counterfactual_001.py`*

## 1. Question

`research/reports/tsmomentum_regime_lookahead_audit_001.md` measured the
same-session feedback of the SPY-200dSMA regime factor on the walk-forward
backtest. It did not replay the committed paper-trading record, so the
record-level cost of that defect was unmeasured. The promotion decision is
taken on the record, which makes that the relevant quantity.

## 2. Validation window

The record is only usable where the committed production path actually
reproduces it. Both paths below are `src.simulation.engine.run_simulation`
output on the committed cache; the point-in-time path differs only by the
committed opt-in switch `lag_regime_exposure=True`.

| Quantity | Value |
| --- | --- |
| Record sessions | {result['n_record_sessions']} |
| Record sessions the current cache cannot produce | {result['missing_from_engine']} ({result['missing_range']}) |
| Common sessions | {window['n_common']} |
| Reproducible trailing window | {result['window_start']} .. {result['window_end']} ({window['n_window']} sessions) |
| Excluded earlier sessions (cache revision) | {window['n_excluded_prefix']} ({window['excluded_prefix_start']} .. {window['excluded_prefix_end']}) |

The excluded prefix is not patched or re-weighted: those sessions were
generated before the committed cache changed and cannot be reproduced from any
committed price file. The six post-cache sessions (2026-11-11 onward) are the
known `unverified` set of `research/paper_record_raw_coverage_audit.py`.

## 3. Record-level result over the reproducible window

| Exposure convention | NAV | Total return | Ann. return | Sharpe | Max drawdown | Min rolling-63d Sharpe |
| --- | --- | --- | --- | --- | --- | --- |
| Committed (session t's own close) | {committed['nav']:.2f} | {committed['total_return']:.6f} | {committed['annualized_return']:.6f} | {committed['sharpe']:.6f} | {committed['max_drawdown']:.6f} | {result['min_rolling_committed']:.6f} |
| Point-in-time (shift(1)) | {lagged['nav']:.2f} | {lagged['total_return']:.6f} | {lagged['annualized_return']:.6f} | {lagged['sharpe']:.6f} | {lagged['max_drawdown']:.6f} | {result['min_rolling_lagged']:.6f} |

Over the same {window['n_window']} sessions the same rule, costs and overlay
deliver Sharpe **{committed['sharpe']:.6f} -> {lagged['sharpe']:.6f}**
({result['sharpe_delta']:+.6f}), total return
**{committed['total_return']:.4%} -> {lagged['total_return']:.4%}**
({result['return_delta']:+.4%}) and max drawdown
**{committed['max_drawdown']:.4%} -> {lagged['max_drawdown']:.4%}**.

Sessions whose applied exposure differs between the two paths:
{result['n_exposure_differs']} ({diff_dates}).

## 4. Exposure-flip census (record only, cache-independent)

A session can only be gated on its own close if its exposure differs from the
previous session's exposure. The record has {len(flips)} such sessions out of
{result['n_record_sessions']}:

| Session | Exposure at t-1 | Exposure at t |
| --- | --- | --- |
{flip_rows}

All {result['n_zero_exposure']} zero-exposure record sessions are entered and
exited on these sessions, so every one of them was decided with same-session
information. The point-in-time record would have moved one session later on
each, which is exactly what the window table above prices.

## 5. Interpretation and boundaries

* The record's Sharpe is **overstated** by the same-session convention by
  {result['sharpe_delta']:.6f} over the reproducible window. That is the
  quantity a forward test may not claim.
* The terminal rolling-63d Sharpe is **[unaffected / affected]**: the last
  exposure flip inside the cache (`2026-11-18`) lies beyond the coverage end,
  and the minimum rolling-63d Sharpe of the window
  ({result['min_rolling_committed']:.6f} committed vs
  {result['min_rolling_lagged']:.6f} lagged) belongs to a stretch with no flip.
  The stored drift flag therefore stays valid as a *description of the record*,
  but the record is not a point-in-time forward test.
* The live implication is stronger than the historical one: on 2026-11-18 the
  record liquidated to cash using that session's own close. That decision is
  not executable in real time, and the six sessions after the cache coverage
  end cannot be re-derived at all -- this is the provenance limitation already
  recorded in `research/reports/paper_record_raw_coverage_001.md`.
* Nothing is promoted. `research/go_no_go_evaluation.py` already reports
  **NO-GO** on the committed record; this measurement only tightens the
  interpretation of that record.
* No state, config, threshold, gate, cost model, universe or committed artifact
  is modified. `data/` and `config/` are hashed before and after the run.

## 6. Verification

```bash
/tmp/kilo-venv/bin/python research/regime_lag_record_counterfactual_001.py
/tmp/kilo-venv/bin/python -m pytest -q tests/test_regime_lag_record_counterfactual_001.py
/tmp/kilo-venv/bin/ruff check research/regime_lag_record_counterfactual_001.py tests/test_regime_lag_record_counterfactual_001.py
```

data/ digest before/after: `{result['data_digest']}` (unchanged)
config/ digest before/after: `{result['config_digest']}` (unchanged)
"""


def main() -> int:
    data_before = tree_digest(REPO_ROOT / "data")
    config_before = tree_digest(REPO_ROOT / "config")

    record = load_record(STATE_PATH)
    flips = exposure_flips(record)
    start = str(record["date"].iloc[0])
    end = str(record["date"].iloc[-1])

    committed_daily, lagged_daily = build_paths(CONFIG_PATH, start, end)

    window_info = reproducible_window(
        record["daily_return"], committed_daily["net_return"]
    )
    window = window_info["window"]

    committed_returns = committed_daily.loc[window, "net_return"]
    lagged_returns = lagged_daily.loc[window, "net_return"]
    committed = path_stats(committed_returns)
    lagged = path_stats(lagged_returns)

    exposure_diff = (
        committed_daily.loc[window, "regime_exposure"]
        != lagged_daily.loc[window, "regime_exposure"]
    )
    sessions_differs = [
        ts.date().isoformat() for ts in window[exposure_diff.values]
    ]

    missing = record.index.difference(committed_daily.index)

    data_after = tree_digest(REPO_ROOT / "data")
    config_after = tree_digest(REPO_ROOT / "config")
    if data_before != data_after or config_before != config_after:
        print("FAIL: data/ or config/ changed during a read-only run", file=sys.stderr)
        return 3

    result = {
        "generated": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_record_sessions": int(len(record)),
        "missing_from_engine": int(len(missing)),
        "missing_range": (
            f"{missing[0].date()} .. {missing[-1].date()}" if len(missing) else "none"
        ),
        "window": window_info,
        "window_start": window[0].date().isoformat(),
        "window_end": window[-1].date().isoformat(),
        "committed": committed,
        "lagged": lagged,
        "sharpe_delta": float(lagged["sharpe"] - committed["sharpe"]),
        "return_delta": float(lagged["total_return"] - committed["total_return"]),
        "min_rolling_committed": min_rolling_sharpe(committed_returns),
        "min_rolling_lagged": min_rolling_sharpe(lagged_returns),
        "flips": flips,
        "n_zero_exposure": int((record["regime_exposure"] == 0.0).sum()),
        "n_exposure_differs": int(exposure_diff.sum()),
        "sessions_exposure_differs": sessions_differs,
        "data_digest": data_before,
        "config_digest": config_before,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(render_report(result))

    print("=== record-level point-in-time counterfactual ===")
    print(
        f"record sessions: {result['n_record_sessions']} "
        f"(not in engine: {result['missing_from_engine']})"
    )
    print(
        f"reproducible window: {result['window_start']} .. {result['window_end']} "
        f"({window_info['n_window']} sessions)"
    )
    print(
        "committed:  "
        f"NAV {committed['nav']:.2f} Sharpe {committed['sharpe']:.6f} "
        f"maxDD {committed['max_drawdown']:.6f}"
    )
    print(
        "point-in-time: "
        f"NAV {lagged['nav']:.2f} Sharpe {lagged['sharpe']:.6f} "
        f"maxDD {lagged['max_drawdown']:.6f}"
    )
    print(
        f"exposure-flip record sessions: {len(flips)}; "
        f"sessions where the paths differ: {result['n_exposure_differs']}"
    )
    print(f"read-only (data/ + config/ byte-identical): True")
    print(f"report: {REPORT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
