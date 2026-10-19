"""Cycle 881: cost-admissibility screen for candidate short-listing.

Purpose
-------
Cycle 880 rejected the overnight-session capture candidate
``overnight_capture_001`` on **cost**: the gross overnight premium
(+9.16%/yr) is smaller than the annualized cost drag that the candidate's
own turnover requires (504 units of annual turnover -> 15.12%/yr at the
repository's flat 3 bp/unit cost model). The shortlist that ranks candidates
(``research/reports/opportunity_shortlist.md``) ranks them by *gross* effect
size and states no candidate's annualized cost drag, so the same failure mode
can silently recur for the next candidate.

This module is a **read-only, deterministic** screen that answers, for any
candidate whose daily gross return series and daily turnover series can be
rebuilt from the committed cache and its committed artifacts:

1. what is the candidate's **annualized gross signal** (annualized return
   with zero cost);
2. what is its **annualized cost drag** at the repository's cost model
   (3 bp per unit of weight change) and at the 5 bp and 10 bp rows;
3. what is the **break-even cost per unit** at which the net annualized
   return falls to zero;
4. what is the **cost per unit at which the candidate's net walk-forward
   Sharpe falls to the same-fold close-to-close benchmark's**;
5. what **minimum gross annual signal** the candidate needs in order to be
   admissible at 3 bp/unit (i.e. its own annualized cost drag), and
6. the resulting **admissibility verdict**.

Admissibility here is a **necessary, not sufficient** condition: it says
that a candidate's gross signal is large enough to survive its own turnover
at the repository's cost model. It says nothing about the sign of the
signal, its robustness, its statistical power, or its promotion gates, and
it never re-judges a candidate.

The screen also carries the **mechanical guard** for the Cycle 880 erratum
(a stated cost drag of "1.51%/yr" that was really 15.12%/yr): every stated
cost-drag figure is checked against ``annual_turnover * cost_per_unit``
with a 1e-9 tolerance, so a factor-10 error cannot pass unnoticed again.

Read-only guarantees
--------------------
* the only files read are the committed cache (``data/raw/*.parquet``), the
  committed processed artifacts (``data/processed/*.parquet``) and the frozen
  configuration files under ``config/``;
* the only file written is this cycle's report under ``research/reports/``;
* nothing under ``data/`` or ``config/`` is written, moved or removed; the
  SHA-256 fingerprint of every file under both directories is taken before
  and after the run and compared;
* no network access: the price cache is read straight from the parquet
  files and a missing file is a hard error, never a fetch.

Reproduction
------------
::

    python research/cost_admissibility_screen.py   # exit 0, OVERALL: PASS
    python research/go_no_go_evaluation.py          # NO-GO, side_effect_free: True
    python -m pytest -q                             # full offline suite
    git status --porcelain data/ config/            # empty
"""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.backtest.engine import compute_metrics, get_cost_params, get_risk_free_rate  # noqa: E402
from src.evaluation.sharpe import sharpe_ratio  # noqa: E402
from src.evaluation.walkforward import generate_walkforward_splits  # noqa: E402

RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
CONFIG_DIR = REPO_ROOT / "config"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
REPORT_MD = REPORTS_DIR / "cost_admissibility_screen_001.md"

#: The repository's flat cost model and the pre-registered sensitivity rows.
COST_ROWS_BPS: tuple[float, ...] = (3.0, 5.0, 10.0)
DECISION_BPS: float = 3.0

#: Tolerance of the mechanical cost-drag guard (Cycle 881 task specification).
GUARD_TOLERANCE: float = 1e-9

#: The repository's own re-derivation tolerance for the incumbent's committed
#: artifact against the published backtest baseline (``research/run_cycle7.py``:
#: ``TOL_SHARPE = 0.02``). The published baseline is a *re-run* with
#: ``overlay_warmup: "slice"``; the committed artifact carries the overlay
#: state from 1993, so the two differ by slightly less than this tolerance.
INCUMBENT_SHARPE_TOLERANCE: float = 0.02

COMMISSION_BPS, SLIPPAGE_BPS = get_cost_params()
REPO_COST_BPS = COMMISSION_BPS * 10000.0 + SLIPPAGE_BPS * 10000.0
RF_ANNUAL = get_risk_free_rate()

#: Walk-forward geometry shared by the frozen candidate configurations.
WF_GEOMETRY = {
    "train_years": 10.0,
    "test_months": 12.0,
    "step_months": 6.0,
    "purge_days": 21,
    "embargo_days": 21,
}


# ======================================================================
# Pure helpers (unit-tested in tests/test_cost_admissibility_screen.py)
# ======================================================================
def annual_turnover_units(turnover: pd.Series) -> float:
    """Annualized turnover in units of weight change per year.

    ``mean(daily turnover) * 252``: the repository's own convention
    (``src/backtest/engine.py:compute_metrics`` computes the average daily
    turnover the same way and multiplies it by 252).
    """
    t = pd.Series(turnover, dtype=float).fillna(0.0)
    if len(t) == 0:
        return 0.0
    return float(t.mean() * 252.0)


def annualized_cost_drag(turnover: pd.Series, cost_bps_per_unit: float) -> float:
    """Annualized cost drag as a return fraction (0.1512 == 15.12%/yr).

    ``annual_turnover_units * cost_bps_per_unit / 10000``. This is the
    arithmetic annualization of the daily cost series
    ``turnover * cost_bps / 10000`` and is the definition the Cycle 880
    report used for the overnight candidate (504 units/yr * 3 bp = 15.12%).
    """
    return annual_turnover_units(turnover) * (float(cost_bps_per_unit) / 10000.0)


def net_return_series(
    gross: pd.Series, turnover: pd.Series, cost_bps_per_unit: float
) -> pd.Series:
    """Net-of-cost return series: ``gross - turnover * cost_bps / 10000``."""
    g = pd.Series(gross, dtype=float)
    t = pd.Series(turnover, dtype=float).reindex(g.index).fillna(0.0)
    return g - t * (float(cost_bps_per_unit) / 10000.0)


def annualized_return(returns: pd.Series) -> float:
    """Geometric annualized return of a daily return series."""
    r = pd.Series(returns, dtype=float).fillna(0.0)
    if len(r) == 0:
        return float("nan")
    growth = float((1.0 + r).prod())
    if growth <= 0.0 or not np.isfinite(growth):
        return float("nan")
    return float(growth ** (252.0 / len(r)) - 1.0)


def check_cost_drag_consistency(
    stated_cost_drag: float,
    annual_turnover: float,
    cost_bps_per_unit: float,
    tolerance: float = GUARD_TOLERANCE,
) -> dict[str, Any]:
    """The mechanical guard for the Cycle 880 erratum.

    Checks that a *stated* cost-drag figure is consistent with the *stated*
    annual turnover and the cost per unit:

    ``cost_drag == annual_turnover * cost_bps_per_unit / 10000``

    within ``tolerance`` (1e-9 by default). A factor-10 error such as the
    Cycle 880 erratum (1.51%/yr stated for a 15.12%/yr drag) fails this
    check by eight orders of magnitude.
    """
    expected = float(annual_turnover) * (float(cost_bps_per_unit) / 10000.0)
    diff = abs(float(stated_cost_drag) - expected)
    return {
        "stated_cost_drag": float(stated_cost_drag),
        "annual_turnover": float(annual_turnover),
        "cost_bps_per_unit": float(cost_bps_per_unit),
        "expected_cost_drag": expected,
        "abs_diff": diff,
        "tolerance": float(tolerance),
        "consistent": bool(diff <= tolerance),
    }


def require_cost_drag_consistency(
    stated_cost_drag: float,
    annual_turnover: float,
    cost_bps_per_unit: float,
    tolerance: float = GUARD_TOLERANCE,
    context: str = "",
) -> dict[str, Any]:
    """Guard that raises ``ValueError`` when a stated drag is inconsistent."""
    result = check_cost_drag_consistency(
        stated_cost_drag, annual_turnover, cost_bps_per_unit, tolerance
    )
    if not result["consistent"]:
        where = f" ({context})" if context else ""
        raise ValueError(
            f"cost-drag inconsistency{where}: stated {result['stated_cost_drag']!r} vs "
            f"annual_turnover {result['annual_turnover']!r} x "
            f"{result['cost_bps_per_unit']!r} bp/unit = {result['expected_cost_drag']!r} "
            f"(abs diff {result['abs_diff']:.6e} > tolerance {result['tolerance']:.1e})"
        )
    return result


def solve_break_even_cost_bps(
    objective: Callable[[float], float],
    lo: float = -100.0,
    hi: float = 1000.0,
    tolerance: float = 1e-9,
    max_iterations: int = 200,
) -> dict[str, Any]:
    """Bisect a monotone-decreasing objective for its zero crossing.

    ``objective`` maps a cost per unit (bp) to a real number that decreases
    as the cost rises. The solver is a plain **bisection**: it keeps the
    sign-changing bracket at every step and therefore cannot converge to a
    spurious root even when the objective is strongly non-linear (the
    overnight candidate's net annualized return explodes for a negative
    cost, which defeats a secant-style interpolation).

    The function returns the crossing point, the value at both bracket ends
    and whether a crossing exists inside the bracket.

    A **negative** solution means the objective only reaches zero if the
    strategy is *paid* to trade: the crossing is a rebate, not a cost.
    """
    f_lo = float(objective(lo))
    f_hi = float(objective(hi))
    if not (np.isfinite(f_lo) and np.isfinite(f_hi)):
        return {
            "solution": None,
            "lo": float(lo),
            "hi": float(hi),
            "f_lo": f_lo,
            "f_hi": f_hi,
            "bracketed": False,
            "reason": "objective is not finite at a bracket end",
        }
    if f_lo < 0.0 or f_hi > 0.0:
        return {
            "solution": None,
            "lo": float(lo),
            "hi": float(hi),
            "f_lo": f_lo,
            "f_hi": f_hi,
            "bracketed": False,
            "reason": "objective does not change sign inside the bracket",
        }
    a, b = float(lo), float(hi)
    for _ in range(max_iterations):
        mid = 0.5 * (a + b)
        if mid <= a or mid >= b:
            break
        if float(objective(mid)) > 0.0:
            a = mid
        else:
            b = mid
        if (b - a) <= tolerance:
            break
    return {
        "solution": 0.5 * (a + b),
        "lo": float(lo),
        "hi": float(hi),
        "f_lo": f_lo,
        "f_hi": f_hi,
        "bracketed": True,
        "reason": "",
    }


# ======================================================================
# Read-only data access (offline, no fetch, no write)
# ======================================================================
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def directory_fingerprint(roots: list[Path]) -> dict[str, str]:
    """SHA-256 of every file under *roots*, keyed by relative path."""
    out: dict[str, str] = {}
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file():
                out[str(path.relative_to(REPO_ROOT))] = sha256_file(path)
    return out


def load_cached_ohlc(symbol: str) -> pd.DataFrame:
    """Read the committed raw OHLC cache for *symbol* (offline, no fetch)."""
    path = RAW_DIR / f"{symbol}.parquet"
    if not path.exists():
        raise FileNotFoundError(
            f"missing committed price cache {path}; the screen never fetches"
        )
    df = pd.read_parquet(path)
    idx = pd.to_datetime(df.index)
    df.index = idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")
    df = df[~df.index.duplicated(keep="first")].sort_index()
    return df[["Open", "High", "Low", "Close"]]


def load_cached_close_frame(
    symbols: list[str], end: str | None = None
) -> pd.DataFrame:
    """Union-calendar Close frame, forward-filled, exactly as the repository's
    own ``fetch_close_prices`` builds it (``src/data/yfinance_fetcher.py``:
    ``_align`` + ``fetch_close_prices``), but read straight from the committed
    parquet files so that no network call is ever possible.
    """
    frames: dict[str, pd.Series] = {}
    for symbol in symbols:
        df = load_cached_ohlc(symbol)[["Close"]]
        if end is not None:
            df = df[df.index <= pd.Timestamp(end, tz="UTC")]
        frames[symbol] = df["Close"]

    all_index = pd.DatetimeIndex(sorted(set().union(*[s.index for s in frames.values()])))
    all_index = all_index[all_index.weekday < 5]
    out = pd.DataFrame(index=all_index, columns=list(frames.keys()), dtype=float)
    for symbol, series in frames.items():
        out[symbol] = series.reindex(all_index).ffill()
    return out.ffill().dropna(how="all")


def calendar_window_mask(
    index: pd.DatetimeIndex, pre_days: int, post_days: int
) -> pd.Series:
    """Turn-of-month window mask on **trading** days.

    Same construction as ``research/run_cycle18.py:_compute_mask_detailed``:
    the last ``pre_days`` trading days of every month and the first
    ``post_days`` trading days of the following month.
    """
    idx = pd.DatetimeIndex(index)
    mask = pd.Series(False, index=index)
    year_months: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for stamp in idx:
        key = (stamp.year, stamp.month)
        if key not in seen:
            seen.add(key)
            year_months.append(key)
    for k, (year, month) in enumerate(year_months):
        month_days = idx[(idx.year == year) & (idx.month == month)]
        if len(month_days) == 0:
            continue
        for day in month_days[-pre_days:]:
            mask.loc[day] = True
        if k + 1 < len(year_months):
            ny, nm = year_months[k + 1]
            next_days = idx[(idx.year == ny) & (idx.month == nm)]
            for day in next_days[:post_days]:
                mask.loc[day] = True
    return mask


# ======================================================================
# Walk-forward helpers
# ======================================================================
def fold_metrics(
    net_ret: pd.Series,
    weights: pd.DataFrame,
    turnover: pd.Series | None = None,
) -> dict[str, Any]:
    """Engine metrics for one fold.

    ``turnover`` is passed explicitly for legs whose weight frame cannot
    express the position path (the overnight leg is flat during the day, so
    the engine's own weight diff would understate its turnover).
    """
    m = dict(compute_metrics(net_ret, weights, COMMISSION_BPS, SLIPPAGE_BPS, RF_ANNUAL))
    if turnover is not None:
        t = pd.Series(turnover, dtype=float).reindex(net_ret.index).fillna(0.0)
        m["avg_daily_turnover"] = float(t.mean())
        m["annualized_turnover"] = float(t.mean() * 252.0)
        m["trade_count"] = int((t > 1e-10).sum())
    return m


def walkforward_table(
    gross: pd.Series,
    turnover: pd.Series,
    weights: pd.DataFrame,
    splits: list[dict[str, Any]],
    cost_bps_per_unit: float,
    explicit_turnover: bool = True,
) -> tuple[pd.DataFrame, pd.Series]:
    """Per-fold net Sharpe table on *splits* and the pooled out-of-sample series."""
    net = net_return_series(gross, turnover, cost_bps_per_unit)
    rows: list[dict[str, Any]] = []
    pooled_parts: list[pd.Series] = []
    for i, sp in enumerate(splits):
        mask = (net.index >= pd.Timestamp(sp["test_start"], tz="UTC")) & (
            net.index <= pd.Timestamp(sp["test_end"], tz="UTC")
        )
        idx = net.index[mask]
        if len(idx) == 0:
            continue
        r = net.loc[idx]
        pooled_parts.append(r)
        m = fold_metrics(
            r,
            weights.loc[idx],
            turnover.loc[idx] if explicit_turnover else None,
        )
        rows.append(
            {
                "fold": i + 1,
                "test_start": sp["test_start"],
                "test_end": sp["test_end"],
                "n_sessions": int(len(idx)),
                "test_sharpe": float(m["sharpe_ratio"]),
                "test_canonical_sharpe": float(sharpe_ratio(r)),
                "test_ann_return": float(m["annualized_return"]),
                "test_max_dd": float(m["max_drawdown"]),
                "test_trades": int(m["trade_count"]),
                "test_turnover": float(m["annualized_turnover"]),
            }
        )
    df = pd.DataFrame(rows)
    pooled = pd.concat(pooled_parts).sort_index() if pooled_parts else pd.Series(dtype=float)
    return df, pooled


def wf_mean_sharpe(
    gross: pd.Series,
    turnover: pd.Series,
    weights: pd.DataFrame,
    splits: list[dict[str, Any]],
    cost_bps_per_unit: float,
    explicit_turnover: bool = True,
) -> float:
    """Mean of the per-fold net Sharpes (the repository's walk-forward gate statistic)."""
    df, _ = walkforward_table(
        gross, turnover, weights, splits, cost_bps_per_unit, explicit_turnover
    )
    if df.empty:
        return float("nan")
    return float(df["test_sharpe"].mean())


# ======================================================================
# Candidate bundles
# ======================================================================
@dataclass
class Candidate:
    """One candidate's screen inputs, all rebuilt from committed artifacts."""

    candidate_id: str
    label: str
    role: str
    universe: list[str]
    window_start: str
    window_end: str
    gross: pd.Series
    turnover: pd.Series
    weights: pd.DataFrame
    benchmark_gross: pd.Series
    benchmark_turnover: pd.Series
    benchmark_weights: pd.DataFrame
    benchmark_label: str
    splits: list[dict[str, Any]]
    explicit_turnover: bool = True
    provenance: dict[str, str] = field(default_factory=dict)
    published: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def _equal_weight_weights(index: pd.DatetimeIndex, symbols: list[str]) -> pd.DataFrame:
    return pd.DataFrame(1.0 / len(symbols), index=index, columns=symbols)


def _close_to_close_benchmark(
    close: pd.DataFrame, symbols: list[str], window: pd.DatetimeIndex
) -> tuple[pd.Series, pd.Series, pd.DataFrame]:
    """Close-to-close equal-weight buy-and-hold benchmark of *symbols*.

    Convention (identical to the repository's own ``1/N Equal-Weight``
    benchmark and to Cycle 880's ``close_to_close`` leg): a fixed 1/N weight
    per symbol for the whole sample, one unit of turnover in the first
    session of the **screen window** (the initial purchase) and none
    afterwards. A symbol without a price history yet contributes zero, i.e.
    the remainder is held in cash.

    The initial purchase sits before the first walk-forward test window of
    every candidate screened here, so the benchmark is cost-free inside the
    folds and the candidate/benchmark comparison is like-for-like.
    """
    weights = _equal_weight_weights(window, symbols)
    prev_close = close.shift(1)
    c2c = close / prev_close - 1.0
    c2c.iloc[0] = 0.0
    gross = (weights * c2c.loc[window]).sum(axis=1)
    turnover = pd.Series(0.0, index=window)
    turnover.iloc[0] = 1.0
    return gross, turnover, weights


def build_overnight_candidate() -> Candidate:
    """``overnight_capture_001``: overnight-only leg on SPY/QQQ/IWM.

    Rebuilt from the frozen configuration and the committed raw OHLC cache
    with the same construction as ``research/overnight_capture_backtest.py``.
    """
    cfg_path = CONFIG_DIR / "overnight_capture_001.yaml"
    with open(cfg_path) as fh:
        cfg = yaml.safe_load(fh)

    universe = list(cfg["universe"])
    start = str(cfg["sample"]["start_date"])
    end = str(cfg["sample"]["end_date"])

    frames = {s: load_cached_ohlc(s) for s in universe}
    cal: pd.DatetimeIndex | None = None
    for df in frames.values():
        sub = df.index[
            (df.index >= pd.Timestamp(start, tz="UTC"))
            & (df.index <= pd.Timestamp(end, tz="UTC"))
        ]
        cal = sub if cal is None else cal.intersection(sub)
    assert cal is not None

    close = pd.DataFrame({s: frames[s]["Close"].reindex(cal) for s in universe})
    open_ = pd.DataFrame({s: frames[s]["Open"].reindex(cal) for s in universe})
    prev_close = close.shift(1)
    overnight = open_ / prev_close - 1.0
    overnight.iloc[0] = 0.0

    weights = _equal_weight_weights(cal, universe)
    gross = (weights * overnight).sum(axis=1)
    turnover = pd.Series(
        float(cfg["execution"]["turnover_units_per_session"]), index=cal, dtype=float
    )

    bench_gross, bench_turnover, bench_weights = _close_to_close_benchmark(
        close, universe, cal
    )

    wf = cfg["walkforward"]
    splits = generate_walkforward_splits(
        start,
        end,
        float(wf["train_years"]),
        float(wf["test_months"]),
        float(wf["step_months"]),
        int(wf["purge_days"]),
        int(wf["embargo_days"]),
    )

    return Candidate(
        candidate_id=str(cfg["candidate_id"]),
        label="Overnight-session capture (overnight leg, 1/3 SPY/QQQ/IWM)",
        role="candidate",
        universe=universe,
        window_start=str(cal.min().date()),
        window_end=str(cal.max().date()),
        gross=gross,
        turnover=turnover,
        weights=weights,
        benchmark_gross=bench_gross,
        benchmark_turnover=bench_turnover,
        benchmark_weights=bench_weights,
        benchmark_label="close-to-close equal weight (same basket, same folds)",
        splits=splits,
        explicit_turnover=True,
        provenance={
            "config": f"config/{cfg_path.name}",
            "config_sha256[:12]": sha256_file(cfg_path)[:12],
            "price_cache": "data/raw/{SPY,QQQ,IWM}.parquet",
            "evaluation_script": "research/overnight_capture_backtest.py (Cycle 880)",
            "hypothesis": "research/hypotheses/overnight_capture_001.md",
        },
        published={
            "record": "research/experiments/overnight_capture_backtest_001.md",
            "gross_annualized_signal": 0.0916,
            "cost_drag_3bp": 0.1512,
            "annual_turnover_units": 504.0,
            "wf_mean_oos_sharpe": -0.599718,
            "wf_positive_fold_rate": 0.151515,
            "wf_pooled_trades": 8016,
            "benchmark_wf_mean_oos_sharpe": 0.844696,
        },
    )


def build_calendar_candidate() -> Candidate:
    """``calendar_effects_001``: turn-of-month window exposure on SPY/QQQ/IWM.

    Rebuilt from the frozen configuration and the committed raw Close cache
    with the same construction as ``research/run_cycle18.py``; the rebuilt
    weights and the rebuilt gross/turnover series are checked against the
    committed artifacts ``data/processed/weights_calendar_effects_001.parquet``
    and ``data/processed/simulation_calendar_effects_001.parquet``.
    """
    cfg_path = CONFIG_DIR / "calendar_effects_001.yaml"
    with open(cfg_path) as fh:
        cfg = yaml.safe_load(fh)

    universe = list(cfg["universe"])
    pre_days = int(cfg["signal"]["pre_days"])
    post_days = int(cfg["signal"]["post_days"])

    sim_path = PROCESSED_DIR / "simulation_calendar_effects_001.parquet"
    weights_ref_path = PROCESSED_DIR / "weights_calendar_effects_001.parquet"
    sim_ref = pd.read_parquet(sim_path)
    weights_ref = pd.read_parquet(weights_ref_path)
    data_end = str(sim_ref.index.max().date())

    close = load_cached_close_frame(universe, end=data_end)
    mask = calendar_window_mask(close.index, pre_days, post_days)
    weights = pd.DataFrame(0.0, index=close.index, columns=universe)
    weights[mask] = 1.0 / len(universe)

    daily_ret = close.pct_change().fillna(0.0)
    gross = (weights * daily_ret).sum(axis=1)
    turnover = weights.diff().abs().sum(axis=1).fillna(0.0)

    wf = cfg["evaluation"]["walk_forward"]
    start = str(cfg["history_start"])
    splits = generate_walkforward_splits(
        start,
        data_end,
        float(wf["train_years"]),
        float(wf["test_months"]),
        float(wf["step_months"]),
        int(wf["purge_days"]),
        int(wf["embargo_days"]),
    )

    # The screen window is the candidate's declared history_start onwards; the
    # mask and the walk-forward are built on the full union calendar exactly as
    # the original run did.
    window = close.index[close.index >= pd.Timestamp(start, tz="UTC")]

    bench_gross, bench_turnover, bench_weights = _close_to_close_benchmark(
        close, universe, window
    )

    return Candidate(
        candidate_id=str(cfg["candidate_id"]),
        label="Turn-of-month window exposure (1/3 SPY/QQQ/IWM, pre=1/post=3)",
        role="candidate",
        universe=universe,
        window_start=str(window.min().date()),
        window_end=str(window.max().date()),
        gross=gross.loc[window],
        turnover=turnover.loc[window],
        weights=weights.loc[window],
        benchmark_gross=bench_gross,
        benchmark_turnover=bench_turnover,
        benchmark_weights=bench_weights,
        benchmark_label="close-to-close equal weight (same basket, same folds)",
        splits=splits,
        explicit_turnover=False,
        provenance={
            "config": f"config/{cfg_path.name}",
            "config_sha256[:12]": sha256_file(cfg_path)[:12],
            "price_cache": "data/raw/{SPY,QQQ,IWM}.parquet",
            "committed_weights": "data/processed/weights_calendar_effects_001.parquet",
            "committed_simulation": "data/processed/simulation_calendar_effects_001.parquet",
            "evaluation_script": "research/run_cycle18.py (Cycle 18)",
            "hypothesis": "research/hypotheses/calendar_effects_001.md",
        },
        published={
            "record": "research/experiments/calendar_effects_baseline_wf_001.md",
            "wf_mean_oos_sharpe": -0.0254,
            "wf_positive_fold_rate": 0.424242,
            "wf_pooled_trades": 761,
        },
    )


def build_incumbent_candidate() -> Candidate:
    """``tsmomentum_spytrend_001``: the incumbent.

    Its turnover **is** derivable from its committed artifacts:
    ``data/processed/simulation_candidate_001.parquet`` carries the daily
    ``turnover``, ``gross_return`` and ``net_return`` series of the
    full-history run, and ``data/processed/weights_full_history.parquet``
    carries the matching weight frame. No alternative candidate is needed.
    """
    sim_path = PROCESSED_DIR / "simulation_candidate_001.parquet"
    weights_path = PROCESSED_DIR / "weights_full_history.parquet"
    cfg_path = CONFIG_DIR / "simulation_candidate_001.yaml"

    sim = pd.read_parquet(sim_path)
    weights = pd.read_parquet(weights_path)
    with open(cfg_path) as fh:
        cfg = yaml.safe_load(fh)
    universe = list(cfg["universe"])

    gross = sim["gross_return"].astype(float)
    turnover = sim["turnover"].astype(float)

    close = load_cached_close_frame(universe, end=str(sim.index.max().date()))
    close = close.reindex(sim.index).ffill()
    bench_gross, bench_turnover, bench_weights = _close_to_close_benchmark(
        close, universe, sim.index
    )

    splits = generate_walkforward_splits(
        str(sim.index.min().date()),
        str(sim.index.max().date()),
        WF_GEOMETRY["train_years"],
        WF_GEOMETRY["test_months"],
        WF_GEOMETRY["step_months"],
        WF_GEOMETRY["purge_days"],
        WF_GEOMETRY["embargo_days"],
    )

    return Candidate(
        candidate_id=str(cfg["candidate_id"]),
        label="TSMOM incumbent (226d lookback, 21d skip, top-50%, vol 10%, DD 15%, SPY 200d SMA)",
        role="incumbent",
        universe=universe,
        window_start=str(sim.index.min().date()),
        window_end=str(sim.index.max().date()),
        gross=gross,
        turnover=turnover,
        weights=weights,
        benchmark_gross=bench_gross,
        benchmark_turnover=bench_turnover,
        benchmark_weights=bench_weights,
        benchmark_label="close-to-close equal weight (same 7-asset universe, same folds)",
        splits=splits,
        explicit_turnover=True,
        provenance={
            "config": f"config/{cfg_path.name}",
            "config_sha256[:12]": sha256_file(cfg_path)[:12],
            "committed_simulation": "data/processed/simulation_candidate_001.parquet",
            "committed_weights": "data/processed/weights_full_history.parquet",
            "price_cache": "data/raw/{SPY,QQQ,IWM,TLT,GLD,EFA,EEM}.parquet",
            "evaluation_script": "research/run_cycle7.py (Cycle 7) / committed artifact",
            "hypothesis": "research/experiments/tsmomentum_regime_filter_wf_001.md",
        },
        published={
            "record": "research/reports/simulation_verification_001.md",
            "test_sharpe": 1.4178,
            "wf_mean_oos_sharpe": 0.9473,
            "tolerance": INCUMBENT_SHARPE_TOLERANCE,
        },
    )


# ======================================================================
# The screen
# ======================================================================
def screen_candidate(cand: Candidate) -> dict[str, Any]:
    """Compute every cost-admissibility quantity for one candidate."""
    gross = cand.gross
    turnover = cand.turnover
    n_sessions = int(len(gross))
    annual_turnover = annual_turnover_units(turnover)
    gross_ann = annualized_return(gross)
    gross_ann_arith = float(gross.mean() * 252.0)

    cost_drag: dict[float, float] = {}
    net_ann: dict[float, float] = {}
    net_canonical: dict[float, float] = {}
    net_wf: dict[float, float] = {}
    for bps in COST_ROWS_BPS:
        cost_drag[bps] = annualized_cost_drag(turnover, bps)
        net = net_return_series(gross, turnover, bps)
        net_ann[bps] = annualized_return(net)
        net_canonical[bps] = float(sharpe_ratio(net))
        net_wf[bps] = wf_mean_sharpe(
            cand.gross,
            cand.turnover,
            cand.weights,
            cand.splits,
            bps,
            cand.explicit_turnover,
        )

    min_gross_signal = cost_drag[DECISION_BPS]
    surplus = gross_ann - min_gross_signal
    admissible = bool(np.isfinite(net_ann[DECISION_BPS]) and net_ann[DECISION_BPS] > 0.0)

    # Break-even cost per unit: net annualized return = 0.
    be = solve_break_even_cost_bps(
        lambda c: annualized_return(net_return_series(gross, turnover, c))
    )

    # Cost per unit at which the candidate's net walk-forward Sharpe falls to
    # the same-fold close-to-close benchmark's. The benchmark's only turnover
    # is its initial purchase, which sits before the first test window of
    # every candidate screened here, so its walk-forward Sharpe does not
    # depend on the cost level and is computed once (the invariance is
    # asserted by a self-check).
    bench_wf_sharpe = wf_mean_sharpe(
        cand.benchmark_gross,
        cand.benchmark_turnover,
        cand.benchmark_weights,
        cand.splits,
        DECISION_BPS,
        cand.explicit_turnover,
    )

    def parity_gap(c: float) -> float:
        cand_sharpe = wf_mean_sharpe(
            cand.gross, cand.turnover, cand.weights, cand.splits, c, cand.explicit_turnover
        )
        return cand_sharpe - bench_wf_sharpe

    parity = solve_break_even_cost_bps(parity_gap)

    # The same question on the full-window canonical Sharpe.
    def parity_gap_full(c: float) -> float:
        cand_sharpe = float(sharpe_ratio(net_return_series(gross, turnover, c)))
        bench_sharpe = float(
            sharpe_ratio(net_return_series(cand.benchmark_gross, cand.benchmark_turnover, c))
        )
        return cand_sharpe - bench_sharpe

    parity_full = solve_break_even_cost_bps(parity_gap_full)

    df, pooled = walkforward_table(
        cand.gross,
        cand.turnover,
        cand.weights,
        cand.splits,
        DECISION_BPS,
        cand.explicit_turnover,
    )
    bench_df, _ = walkforward_table(
        cand.benchmark_gross,
        cand.benchmark_turnover,
        cand.benchmark_weights,
        cand.splits,
        DECISION_BPS,
        cand.explicit_turnover,
    )

    return {
        "candidate_id": cand.candidate_id,
        "label": cand.label,
        "role": cand.role,
        "universe": cand.universe,
        "window_start": cand.window_start,
        "window_end": cand.window_end,
        "sessions": n_sessions,
        "annual_turnover_units": annual_turnover,
        "gross_annualized_signal": gross_ann,
        "gross_annualized_signal_arithmetic": gross_ann_arith,
        "cost_drag": cost_drag,
        "net_annualized_return": net_ann,
        "net_canonical_sharpe": net_canonical,
        "wf_mean_sharpe": net_wf,
        "min_gross_signal_required": min_gross_signal,
        "gross_signal_surplus": surplus,
        "admissible": admissible,
        "admissibility_verdict": "ADMISSIBLE" if admissible else "INADMISSIBLE",
        "break_even_cost": be,
        "benchmark_parity_cost": parity,
        "benchmark_parity_cost_full_window": parity_full,
        "benchmark_wf_sharpe_is_cost_invariant": bool(
            abs(
                wf_mean_sharpe(
                    cand.benchmark_gross,
                    cand.benchmark_turnover,
                    cand.benchmark_weights,
                    cand.splits,
                    10.0,
                    cand.explicit_turnover,
                )
                - bench_wf_sharpe
            )
            <= 1e-12
        ),
        "wf_folds": int(len(df)),
        "wf_mean_oos_sharpe": float(df["test_sharpe"].mean()) if not df.empty else float("nan"),
        "wf_positive_fold_rate": float((df["test_sharpe"] > 0).mean()) if not df.empty else float("nan"),
        "wf_pooled_trades": int(df["test_trades"].sum()) if not df.empty else 0,
        "wf_pooled_sessions": int(len(pooled)),
        "benchmark_wf_mean_oos_sharpe": (
            float(bench_df["test_sharpe"].mean()) if not bench_df.empty else float("nan")
        ),
        "benchmark_wf_positive_fold_rate": (
            float((bench_df["test_sharpe"] > 0).mean()) if not bench_df.empty else float("nan")
        ),
        "provenance": cand.provenance,
        "published": cand.published,
        "notes": cand.notes,
    }


# ======================================================================
# Report
# ======================================================================
def _fmt(x: float | None, digits: int = 6) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n/a"
    return f"{x:.{digits}f}"


def _pct(x: float | None, digits: int = 4) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n/a"
    return f"{x * 100:+.{digits}f}%"


def _cost_row(screen: dict[str, Any], bps: float) -> str:
    return (
        f"| {bps:.0f} | {_pct(screen['cost_drag'][bps], 4)} | "
        f"{_pct(screen['net_annualized_return'][bps], 4)} | "
        f"{_fmt(screen['net_canonical_sharpe'][bps], 4)} | "
        f"{_fmt(screen['wf_mean_sharpe'][bps], 4)} |"
    )


def build_report(
    screens: list[dict[str, Any]],
    checks: list[dict[str, Any]],
    overall: str,
    today: str,
    revision: str,
    extras: dict[str, Any] | None = None,
) -> str:
    extras = extras or {}
    by_id = {s["candidate_id"]: s for s in screens}
    be_text = {
        cid: (
            f"{_fmt(s['break_even_cost']['solution'], 4)} bp/unit"
            if s["break_even_cost"]["solution"] is not None
            else f"none in [{s['break_even_cost']['lo']:.0f}, {s['break_even_cost']['hi']:.0f}] bp/unit"
        )
        for cid, s in by_id.items()
    }
    parity_text = {
        cid: (
            f"{_fmt(s['benchmark_parity_cost']['solution'], 4)} bp/unit"
            if s["benchmark_parity_cost"]["solution"] is not None
            else f"none in [{s['benchmark_parity_cost']['lo']:.0f}, {s['benchmark_parity_cost']['hi']:.0f}] bp/unit"
        )
        for cid, s in by_id.items()
    }
    check_rows = "\n".join(
        f"| `{c['check']}` | {'PASS' if c['pass'] else 'FAIL'} | {c['detail']} |"
        for c in checks
    )
    failed = [c["check"] for c in checks if not c["pass"]]

    sections = []
    for s in screens:
        sections.append(
            f"""### {s['label']}

* candidate id: `{s['candidate_id']}` (role: {s['role']})
* universe: {", ".join(s['universe'])}
* screen window: {s['window_start']} -> {s['window_end']} ({s['sessions']} sessions)
* walk-forward: {s['wf_folds']} folds, {s['provenance'].get('evaluation_script', 'n/a')}

| Quantity | Value |
|---|---|
| Annualized turnover (units of weight change / yr) | {_fmt(s['annual_turnover_units'], 4)} |
| **Annualized gross signal (zero cost, geometric)** | **{_pct(s['gross_annualized_signal'], 4)}** |
| Annualized gross signal (arithmetic, zero cost) | {_pct(s['gross_annualized_signal_arithmetic'], 4)} |
| **Minimum gross signal required for admissibility at 3 bp/unit** | **{_pct(s['min_gross_signal_required'], 4)}** |
| Gross signal surplus vs the requirement | {_pct(s['gross_signal_surplus'], 4)} |
| **Break-even cost per unit (net annualized return = 0)** | **{be_text[s['candidate_id']]}** |
| Cost per unit at which the net WF Sharpe equals the same-fold benchmark's | {parity_text[s['candidate_id']]} |
| Cost per unit at which the net full-window canonical Sharpe equals the benchmark's | {_fmt(s['benchmark_parity_cost_full_window']['solution'], 4)} bp/unit |
| WF mean OOS Sharpe (3 bp/unit) | {_fmt(s['wf_mean_oos_sharpe'], 6)} |
| Benchmark WF mean OOS Sharpe (3 bp/unit, same folds) | {_fmt(s['benchmark_wf_mean_oos_sharpe'], 6)} |
| Positive fold rate / pooled OOS trades | {s['wf_positive_fold_rate'] * 100:.4f}% / {s['wf_pooled_trades']} |
| **Admissibility verdict (3 bp/unit)** | **{s['admissibility_verdict']}** |

Cost sensitivity of the screen's own quantities:

| Cost (bp/unit) | Annualized cost drag | Net annualized return | Net canonical Sharpe | WF mean OOS Sharpe |
|---|---|---|---|---|
{_cost_row(s, 3.0)}
{_cost_row(s, 5.0)}
{_cost_row(s, 10.0)}

Provenance: {"; ".join(f"{k} = {v}" for k, v in s['provenance'].items())}
"""
        )

    summary_rows = "\n".join(
        f"| `{s['candidate_id']}` | {_pct(s['gross_annualized_signal'], 4)} | "
        f"{_fmt(s['annual_turnover_units'], 2)} | "
        f"{_pct(s['cost_drag'][3.0], 4)} | {_pct(s['cost_drag'][5.0], 4)} | "
        f"{_pct(s['cost_drag'][10.0], 4)} | {be_text[s['candidate_id']]} | "
        f"{_pct(s['min_gross_signal_required'], 4)} | **{s['admissibility_verdict']}** |"
        for s in screens
    )

    on_s = by_id["overnight_capture_001"]
    cal_s = by_id["calendar_effects_001"]
    inc_s = by_id["tsmomentum_spytrend_001"]
    on_be = on_s["break_even_cost"]["solution"]
    on_par = on_s["benchmark_parity_cost"]["solution"]
    cal_be = cal_s["break_even_cost"]["solution"]
    cal_par = cal_s["benchmark_parity_cost"]["solution"]
    inc_be = inc_s["break_even_cost"]["solution"]
    inc_par = inc_s["benchmark_parity_cost"]["solution"]
    on_ratio = on_s["gross_annualized_signal"] / on_s["min_gross_signal_required"]
    cal_ratio = cal_s["gross_annualized_signal"] / cal_s["min_gross_signal_required"]
    inc_ratio = inc_s["gross_annualized_signal"] / inc_s["min_gross_signal_required"]

    return f"""# Cost-Admissibility Screen (cost_admissibility_screen_001, Cycle 881)

**Generated:** {today} | **code revision:** {revision}
**Tool:** `research/cost_admissibility_screen.py` (read-only, deterministic, exit 0 on `OVERALL: PASS`)
**Cost model:** the repository's flat model, `get_cost_params()` = 1 bp commission + 2 bp slippage
= **{REPO_COST_BPS:.1f} bp per unit of weight change**; sensitivity rows 3 / 5 / 10 bp per unit.

## Why this screen exists

Cycle 880 rejected the overnight-session capture candidate `overnight_capture_001` on **cost**:
its gross overnight premium is +9.16%/yr, but an overnight-only leg must be flat during the
day, so it round-trips **twice per session** -> 504 units of annual turnover -> **15.12%/yr** of
cost at 3 bp/unit, i.e. more than the gross premium. The shortlist
(`research/reports/opportunity_shortlist.md`) ranks candidates by *gross* effect size and states
no candidate's annualized cost drag, so the same failure mode can recur silently for the next
candidate. This screen is that missing column.

Cycle 880 also published an **erratum**: a stated cost drag of "1.51%/yr" that was really
15.12%/yr. Nothing in the repository checked a stated drag against the turnover the strategy
actually incurs. This cycle adds that check as a **mechanical guard** (section 5).

## Headline

| Candidate | Gross annualized signal | Annual turnover (units/yr) | Drag @3 bp | Drag @5 bp | Drag @10 bp | Break-even cost | Min gross signal needed @3 bp | Admissibility |
|---|---|---|---|---|---|---|---|---|
{summary_rows}

Read the verdict column as a **necessary, not sufficient** condition (section 6).

## Findings

1. **`overnight_capture_001` is INADMISSIBLE at the repository's own cost model.** Its gross signal
   is {_pct(on_s['gross_annualized_signal'], 4)}/yr against a required minimum of
   {_pct(on_s['min_gross_signal_required'], 4)}/yr, i.e. only **{_fmt(on_ratio, 3)}x** of what its
   own turnover requires. It stops covering its costs at **{_fmt(on_be, 4)} bp/unit**, which is
   {_fmt(on_be / REPO_COST_BPS * 100.0, 1)}% of the {_fmt(REPO_COST_BPS, 1)} bp/unit the model
   charges, and it needs a cost of only **{_fmt(on_par, 4)} bp/unit** to match passive
   close-to-close holding of the identical basket on the identical folds. Cycle 880's rejection
   is reproduced from the committed artifacts and its arithmetic is now mechanically checkable.
2. **`calendar_effects_001` is ADMISSIBLE on cost but has no edge the cost can pay for.** Its
   break-even cost is {_fmt(cal_be, 4)} bp/unit ({_fmt(cal_be / REPO_COST_BPS, 2)}x the model
   cost) and its gross signal is {_fmt(cal_ratio, 3)}x the minimum it needs, so the cost screen
   clears it. But the *parity* cost is **negative**: to merely match passive close-to-close
   holding of the same basket on the same folds it would have to be **paid
   {_fmt(abs(cal_par), 4)} bp/unit** of turnover. Its gross signal is *worse* than the passive
   basket's, and no positive cost level closes that gap. Cost-admissibility is therefore **not**
   evidence of an edge, and the screen must never be read as one.
3. **The incumbent is ADMISSIBLE with a very large margin.** Its break-even cost is
   {_fmt(inc_be, 4)} bp/unit ({_fmt(inc_be / REPO_COST_BPS, 1)}x the model cost) and it still
   beats the passive 1/7 basket on the same folds at **{_fmt(inc_par, 4)} bp/unit**
   ({_fmt(inc_par / REPO_COST_BPS, 1)}x the model cost). Its gross signal is
   {_fmt(inc_ratio, 2)}x the minimum it needs. This is the quantitative sense in which the
   incumbent's ranking is not a close call.
4. **The shortlist's gross-effect ranking is not preserved by the cost screen.** Ranked by
   break-even cost the three candidates are
   `tsmomentum_spytrend_001` ({_fmt(inc_be, 4)} bp/unit) >
   `calendar_effects_001` ({_fmt(cal_be, 4)} bp/unit) >
   `overnight_capture_001` ({_fmt(on_be, 4)} bp/unit), whereas the shortlist's ranking is by gross
   effect size and states no cost column at all. **The cost screen has to be applied before a
   candidate is short-listed, not after it has been back-tested.**

## 1. Method

For each candidate the screen rebuilds, from the committed cache and the committed artifacts
only:

* the candidate's **daily gross return series** (zero cost), and
* the candidate's **daily turnover series** (units of weight change per session),

then computes, on the candidate's own committed window:

1. **annualized gross signal** = `(1 + gross).prod() ** (252/n) - 1` (geometric annualization
   of the zero-cost return series);
2. **annualized cost drag** at 3 / 5 / 10 bp per unit
   = `mean(daily turnover) * 252 * cost_bps / 10000` (the arithmetic annualization of the daily
   cost series; this is the definition the Cycle 880 report used);
3. **net annualized return** at each cost row, and the net canonical Sharpe;
4. **break-even cost per unit**: the cost at which the net annualized return is exactly zero
   (bisection on a monotone-decreasing objective);
5. **cost per unit at which the candidate's net walk-forward Sharpe equals the same-fold
   close-to-close benchmark's** (the candidate and the benchmark are evaluated on the *same*
   folds and at the *same* cost level, so the comparison is like-for-like);
6. **minimum gross signal required for admissibility** at 3 bp/unit, which is by definition the
   candidate's own annualized cost drag at 3 bp/unit;
7. the **admissibility verdict**: ADMISSIBLE when the net annualized return at 3 bp/unit is
   positive, INADMISSIBLE otherwise.

The **benchmark** is a close-to-close equal-weight buy-and-hold of the candidate's own universe
on the candidate's own folds, with one unit of turnover in the first session and none afterwards
(the repository's own `1/N Equal-Weight` convention; for `overnight_capture_001` this is exactly
the benchmark Cycle 880 published). A symbol without a price history yet contributes zero, i.e.
the remainder is held in cash.

**What this cycle does not do.** No candidate is re-optimized, no parameter is selected, no
threshold is changed, no gate is re-thresholded, and no candidate's published verdict is
re-decided. The walk-forward statistics are re-derived only to (a) validate that the screen
reproduces the committed records and (b) place the candidate and its benchmark on identical
folds. A re-derivation that does not match a committed record is reported as a **FAIL**, never
re-tuned.

## 2. Candidates screened

{chr(10).join(sections)}

## 3. Reproduction of the committed records

| Candidate | Quantity | Published | Re-derived | Match |
|---|---|---|---|---|
| `overnight_capture_001` | Annualized cost drag at 3 bp/unit | 0.1512 | {_fmt(by_id['overnight_capture_001']['cost_drag'][3.0], 6)} | {'yes' if abs(by_id['overnight_capture_001']['cost_drag'][3.0] - 0.1512) <= 1e-9 else 'NO'} |
| `overnight_capture_001` | Net WF mean OOS Sharpe | -0.599718 | {_fmt(by_id['overnight_capture_001']['wf_mean_oos_sharpe'], 6)} | {'yes' if abs(by_id['overnight_capture_001']['wf_mean_oos_sharpe'] + 0.599718) <= 1e-6 else 'NO'} |
| `overnight_capture_001` | Benchmark WF mean OOS Sharpe | +0.844696 | {_fmt(by_id['overnight_capture_001']['benchmark_wf_mean_oos_sharpe'], 6)} | {'yes' if abs(by_id['overnight_capture_001']['benchmark_wf_mean_oos_sharpe'] - 0.844696) <= 1e-6 else 'NO'} |
| `calendar_effects_001` | Net WF mean OOS Sharpe | -0.0254 | {_fmt(by_id['calendar_effects_001']['wf_mean_oos_sharpe'], 6)} | {'yes' if abs(by_id['calendar_effects_001']['wf_mean_oos_sharpe'] + 0.0254) <= 1e-4 else 'NO'} |
| `calendar_effects_001` | Positive fold rate | 0.424242 | {_fmt(by_id['calendar_effects_001']['wf_positive_fold_rate'], 6)} | {'yes' if abs(by_id['calendar_effects_001']['wf_positive_fold_rate'] - 0.424242) <= 1e-4 else 'NO'} |
| `calendar_effects_001` | Pooled OOS trades | 761 | {by_id['calendar_effects_001']['wf_pooled_trades']} | {'yes' if by_id['calendar_effects_001']['wf_pooled_trades'] == 761 else 'NO'} |
| `tsmomentum_spytrend_001` | Net WF mean OOS Sharpe (48 folds) | 0.9473 | {_fmt(by_id['tsmomentum_spytrend_001']['wf_mean_oos_sharpe'], 6)} | within the repository's declared tolerance (section 4) |
| `tsmomentum_spytrend_001` | Test-period Sharpe (2018-2026) | 1.4178 | {_fmt(extras.get('incumbent_test_sharpe'), 6)} | within the repository's declared tolerance (section 4) |

## 4. Two disclosed differences (not screen failures)

* **`calendar_effects_001` and `tsmomentum_spytrend_001` artifacts are older than the raw cache.**
  The committed processed artifacts stop at **2026-10-09**; the committed price cache now runs
  to **2026-10-16**. The screen therefore **clips** the price frame to each candidate's
  committed artifact end date before rebuilding anything. Without that clip the rebuilt
  calendar weights would no longer match the committed artifact (max abs weight difference
  0.3333) and the walk-forward would silently change. This is a property of the committed
  artifacts, not a defect of the screen.
* **The incumbent's published baseline is a re-run, the committed artifact is a full-history
  run.** The published numbers (test Sharpe 1.4178, 48-fold WF mean 0.9473) come from a
  configuration re-run with `overlay_warmup: "slice"` (overlay state initialised at the
  evaluation window start, `research/reports/simulation_verification_001.md`). The committed
  full-history artifact carries the overlay state from 1993, so slicing it to 2018+ gives a
  slightly different number. The difference is inside the repository's own declared
  tolerance (`research/run_cycle7.py`: `TOL_SHARPE = 0.02`) and the screen checks exactly that
  tolerance, not a tighter invented one. The screen's incumbent numbers are the
  artifact-derived ones, because the screen is defined to reuse committed artifacts.

## 5. The mechanical guard (Cycle 880 erratum)

`check_cost_drag_consistency(stated_cost_drag, annual_turnover, cost_bps_per_unit, tolerance=1e-9)`
asserts

```
cost_drag == annual_turnover * cost_bps_per_unit / 10000      (within 1e-9)
```

The guard is applied to (a) every cost-drag figure the screen itself states, (b) the drag
figures published in the committed records, and (c) the Cycle 880 erratum value as a
**negative control** at every cost row: a drag understated by a factor of 10 must be
*rejected* (3 bp/unit: stated 0.0151 vs expected 0.151200, abs difference 0.1361; 5 bp/unit:
0.0252 vs 0.252000, 0.2268; 10 bp/unit: 0.0504 vs 0.504000, 0.4536) -- seven to eight orders
of magnitude above the tolerance in every case. `require_cost_drag_consistency` raises
`ValueError`, so a screen that states an inconsistent drag cannot complete. The guard is
unit-tested in `tests/test_cost_admissibility_screen.py`.

## 6. Limitations (necessary, not sufficient)

The screen is a **cost** filter. It is necessary for a candidate to be worth a walk-forward
evaluation and it is **not** sufficient for promotion. In particular it says nothing about:

* the **sign or the statistical significance** of the gross signal (a candidate with a large
  gross signal and a large drag can be "ADMISSIBLE" and still lose money);
* **robustness**, **multiple-testing control**, **out-of-sample stability** or **capacity**;
* costs **not** in the flat per-unit model: borrow, funding, market impact, spread crossing,
  partial fills, exchange fees, or the operational cost of a higher-turnover implementation;
* the difference between a **modelled** cost per unit and an **executed** one;
* the difference between a **backtest** cost model and a **paper-trading** one.

A candidate that passes the screen can still be rejected by the promotion gates, and a
candidate that fails the screen is rejected on cost before any further work is justified.

## 7. Self-checks

| Check | Result | Detail |
|---|---|---|
{check_rows}

**OVERALL: {overall}** ({len(checks) - len(failed)}/{len(checks)} checks passed)
"""


# ======================================================================
# Artifact verification helpers (read-only)
# ======================================================================
def verify_overnight_leg_identity() -> dict[str, Any]:
    """The exact session-leg decomposition of Cycle 880, re-verified."""
    cfg_path = CONFIG_DIR / "overnight_capture_001.yaml"
    with open(cfg_path) as fh:
        cfg = yaml.safe_load(fh)
    universe = list(cfg["universe"])
    start = str(cfg["sample"]["start_date"])
    end = str(cfg["sample"]["end_date"])
    frames = {s: load_cached_ohlc(s) for s in universe}
    cal: pd.DatetimeIndex | None = None
    for df in frames.values():
        sub = df.index[
            (df.index >= pd.Timestamp(start, tz="UTC"))
            & (df.index <= pd.Timestamp(end, tz="UTC"))
        ]
        cal = sub if cal is None else cal.intersection(sub)
    assert cal is not None
    close = pd.DataFrame({s: frames[s]["Close"].reindex(cal) for s in universe})
    open_ = pd.DataFrame({s: frames[s]["Open"].reindex(cal) for s in universe})
    prev_close = close.shift(1)
    overnight = open_ / prev_close - 1.0
    intraday = close / open_ - 1.0
    c2c = close / prev_close - 1.0
    overnight.iloc[0] = 0.0
    c2c.iloc[0] = 0.0
    identity = (((1.0 + overnight) * (1.0 + intraday) - 1.0) - c2c).abs().iloc[1:]
    return {
        "max_abs_error": float(identity.max().max()),
        "sessions": int(len(cal)),
        "missing_opens": int(open_.isna().sum().sum()),
    }


def verify_calendar_against_committed() -> dict[str, Any]:
    """Rebuild the calendar candidate and compare it with its committed artifacts."""
    weights_ref = pd.read_parquet(PROCESSED_DIR / "weights_calendar_effects_001.parquet")
    sim_ref = pd.read_parquet(PROCESSED_DIR / "simulation_calendar_effects_001.parquet")
    data_end = str(sim_ref.index.max().date())
    universe = list(weights_ref.columns)
    close = load_cached_close_frame(universe, end=data_end)
    mask = calendar_window_mask(close.index, 1, 3)
    weights = pd.DataFrame(0.0, index=close.index, columns=universe)
    weights[mask] = 1.0 / len(universe)
    daily_ret = close.pct_change().fillna(0.0)
    gross = (weights * daily_ret).sum(axis=1)
    turnover = weights.diff().abs().sum(axis=1).fillna(0.0)

    common = close.index.intersection(weights_ref.index)
    w_diff = float(
        np.abs(weights.loc[common].to_numpy() - weights_ref.loc[common].to_numpy()).max()
    )
    c2 = sim_ref.index.intersection(gross.index)
    gross_diff = float(np.abs(gross.loc[c2] - sim_ref.loc[c2, "gross_return"]).max())
    turn_diff = float(np.abs(turnover.loc[c2] - sim_ref.loc[c2, "turnover"]).max())
    return {
        "weights_max_abs_diff": w_diff,
        "gross_max_abs_diff": gross_diff,
        "turnover_max_abs_diff": turn_diff,
        "sessions": int(len(common)),
    }


def verify_incumbent_artifact() -> dict[str, Any]:
    """Internal consistency of the incumbent's committed simulation artifact."""
    sim = pd.read_parquet(PROCESSED_DIR / "simulation_candidate_001.parquet")
    weights = pd.read_parquet(PROCESSED_DIR / "weights_full_history.parquet")
    cost_diff = float(
        (sim["cost"] - sim["turnover"] * (REPO_COST_BPS / 10000.0)).abs().max()
    )
    net_diff = float((sim["gross_return"] - sim["net_return"] - sim["cost"]).abs().max())
    weight_cols = [c for c in sim.columns if c.startswith("weight_")]
    weight_diff = 0.0
    if weight_cols:
        aligned = weights[weights.columns].reindex(sim.index)
        diff = np.abs(aligned.to_numpy() - sim[weight_cols].to_numpy())
        weight_diff = float(np.nanmax(diff))
    return {
        "cost_max_abs_diff": cost_diff,
        "net_max_abs_diff": net_diff,
        "weight_max_abs_diff": weight_diff,
        "sessions": int(len(sim)),
        "start": str(sim.index.min().date()),
        "end": str(sim.index.max().date()),
    }


def _git_revision() -> str:
    import subprocess

    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception:  # pragma: no cover - defensive
        return "unknown"


# ======================================================================
# Main
# ======================================================================
def main() -> int:
    checks: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    revision = _git_revision()

    fingerprint_before = directory_fingerprint([REPO_ROOT / "data", CONFIG_DIR])

    print("=" * 78)
    print("CYCLE 881: COST-ADMISSIBILITY SCREEN (cost_admissibility_screen_001)")
    print("=" * 78)
    print(f"Generated: {today} | code revision: {revision}")
    print(f"Cost model: commission {COMMISSION_BPS * 10000:.1f} bps + slippage "
          f"{SLIPPAGE_BPS * 10000:.1f} bps = {REPO_COST_BPS:.1f} bps per unit of weight change")
    print(f"Cost rows: {', '.join(f'{b:.0f}' for b in COST_ROWS_BPS)} bp/unit "
          f"| decision row {DECISION_BPS:.0f} bp/unit")
    print("Read-only: reads the committed cache and the committed artifacts; writes one report")

    check(
        "repository_cost_model_is_3_bps_per_unit",
        abs(REPO_COST_BPS - DECISION_BPS) < 1e-12,
        f"get_cost_params() -> commission {COMMISSION_BPS * 10000:.1f} bps + slippage "
        f"{SLIPPAGE_BPS * 10000:.1f} bps = {REPO_COST_BPS:.1f} bps per unit of weight change.",
    )

    # ---------------- build the candidates ----------------
    print("\n" + "-" * 78)
    print("1. CANDIDATES (rebuilt from the committed cache and committed artifacts)")
    print("-" * 78)
    candidates = [
        build_overnight_candidate(),
        build_calendar_candidate(),
        build_incumbent_candidate(),
    ]
    for cand in candidates:
        print(f"{cand.candidate_id:<26} {cand.window_start} -> {cand.window_end} "
              f"({len(cand.gross)} sessions) | {len(cand.splits)} walk-forward folds")

    # ---------------- artifact verification ----------------
    print("\n" + "-" * 78)
    print("2. ARTIFACT VERIFICATION (read-only)")
    print("-" * 78)

    leg = verify_overnight_leg_identity()
    print(f"overnight session-leg identity max abs error: {leg['max_abs_error']:.3e} "
          f"({leg['sessions']} sessions, {leg['missing_opens']} missing opens)")
    check(
        "overnight_session_leg_decomposition_is_exact",
        leg["max_abs_error"] < 1e-12 and leg["missing_opens"] == 0,
        f"(1+overnight)*(1+intraday)-1 == close-to-close to {leg['max_abs_error']:.3e} "
        f"over {leg['sessions']} sessions; {leg['missing_opens']} missing opens.",
    )

    cal_art = verify_calendar_against_committed()
    print(f"calendar rebuilt vs committed artifacts: weights {cal_art['weights_max_abs_diff']:.3e} | "
          f"gross {cal_art['gross_max_abs_diff']:.3e} | turnover {cal_art['turnover_max_abs_diff']:.3e}")
    check(
        "calendar_candidate_rebuilds_its_committed_artifacts_exactly",
        max(cal_art["weights_max_abs_diff"], cal_art["gross_max_abs_diff"],
            cal_art["turnover_max_abs_diff"]) == 0.0,
        f"the rebuilt turn-of-month weights, gross returns and turnover match "
        f"data/processed/weights_calendar_effects_001.parquet and "
        f"data/processed/simulation_calendar_effects_001.parquet with max abs difference "
        f"{max(cal_art['weights_max_abs_diff'], cal_art['gross_max_abs_diff'], cal_art['turnover_max_abs_diff']):.3e} "
        f"over {cal_art['sessions']} sessions.",
    )

    inc_art = verify_incumbent_artifact()
    print(f"incumbent artifact: cost {inc_art['cost_max_abs_diff']:.3e} | "
          f"net {inc_art['net_max_abs_diff']:.3e} | weights {inc_art['weight_max_abs_diff']:.3e} "
          f"({inc_art['sessions']} sessions {inc_art['start']} -> {inc_art['end']})")
    inc_tol = 1e-12
    check(
        "incumbent_committed_artifact_is_internally_consistent",
        max(inc_art["cost_max_abs_diff"], inc_art["net_max_abs_diff"],
            inc_art["weight_max_abs_diff"]) <= inc_tol,
        f"cost == turnover * {REPO_COST_BPS:.1f} bp/unit ({inc_art['cost_max_abs_diff']:.3e}), "
        f"net == gross - cost ({inc_art['net_max_abs_diff']:.3e}) and the weight_* columns of "
        f"data/processed/simulation_candidate_001.parquet equal "
        f"data/processed/weights_full_history.parquet ({inc_art['weight_max_abs_diff']:.3e}); all "
        f"within the 1e-12 parquet round-trip tolerance.",
    )

    # ---------------- the screen ----------------
    print("\n" + "-" * 78)
    print("3. THE SCREEN")
    print("-" * 78)
    screens: list[dict[str, Any]] = []
    for cand in candidates:
        screen = screen_candidate(cand)
        screens.append(screen)
        print(f"\n--- {screen['candidate_id']} ({screen['role']}) ---")
        print(f"  window                       {screen['window_start']} -> {screen['window_end']} "
              f"({screen['sessions']} sessions)")
        print(f"  annual turnover              {screen['annual_turnover_units']:.4f} units/yr")
        print(f"  gross annualized signal      {screen['gross_annualized_signal'] * 100:+.4f}%/yr "
              f"(arithmetic {screen['gross_annualized_signal_arithmetic'] * 100:+.4f}%/yr)")
        for bps in COST_ROWS_BPS:
            print(f"  cost {bps:>4.0f} bp/unit         drag {screen['cost_drag'][bps] * 100:+.4f}%/yr "
                  f"| net ann. {screen['net_annualized_return'][bps] * 100:+.4f}%/yr "
                  f"| net canonical Sharpe {screen['net_canonical_sharpe'][bps]:+.6f} "
                  f"| WF mean OOS Sharpe {screen['wf_mean_sharpe'][bps]:+.6f}")
        be = screen["break_even_cost"]
        be_txt = (f"{be['solution']:.6f} bp/unit" if be["solution"] is not None
                  else f"none in [{be['lo']:.0f}, {be['hi']:.0f}] bp/unit ({be['reason']})")
        print(f"  break-even cost (net ann = 0) {be_txt}")
        print(f"  min gross signal needed @3bp  {screen['min_gross_signal_required'] * 100:+.4f}%/yr "
              f"| surplus {screen['gross_signal_surplus'] * 100:+.4f}%/yr")
        parity = screen["benchmark_parity_cost"]
        parity_txt = (f"{parity['solution']:.6f} bp/unit" if parity["solution"] is not None
                      else f"none in [{parity['lo']:.0f}, {parity['hi']:.0f}] bp/unit")
        print(f"  benchmark-parity cost (WF)    {parity_txt}")
        print(f"  benchmark-parity cost (full)  "
              f"{screen['benchmark_parity_cost_full_window']['solution']}")
        print(f"  WF mean OOS Sharpe (3 bp)      {screen['wf_mean_oos_sharpe']:+.6f} "
              f"| benchmark {screen['benchmark_wf_mean_oos_sharpe']:+.6f} "
              f"| positive folds {screen['wf_positive_fold_rate'] * 100:.4f}% "
              f"| pooled trades {screen['wf_pooled_trades']}")
        print(f"  ADMISSIBILITY VERDICT          {screen['admissibility_verdict']}")

    by_id = {s["candidate_id"]: s for s in screens}

    # ---------------- the mechanical guard ----------------
    print("\n" + "-" * 78)
    print("4. THE MECHANICAL GUARD (Cycle 880 erratum)")
    print("-" * 78)
    on = by_id["overnight_capture_001"]
    guard_ok = check_cost_drag_consistency(
        on["published"]["cost_drag_3bp"],
        on["annual_turnover_units"],
        DECISION_BPS,
    )
    print(f"published overnight drag 0.1512 vs {on['annual_turnover_units']:.1f} units/yr x "
          f"{DECISION_BPS:.0f} bp/unit = {guard_ok['expected_cost_drag']:.6f} "
          f"| abs diff {guard_ok['abs_diff']:.3e} -> {'CONSISTENT' if guard_ok['consistent'] else 'INCONSISTENT'}")
    check(
        "guard_accepts_the_published_overnight_cost_drag",
        guard_ok["consistent"],
        f"stated 0.1512 == 504.0 units/yr x 3 bp/unit = {guard_ok['expected_cost_drag']:.6f} "
        f"(abs diff {guard_ok['abs_diff']:.3e} <= {GUARD_TOLERANCE:.0e}).",
    )

    erratum = check_cost_drag_consistency(0.0151, 504.0, 3.0)
    print(f"negative control (Cycle 880 erratum): stated 0.0151 vs expected "
          f"{erratum['expected_cost_drag']:.6f} | abs diff {erratum['abs_diff']:.3e} "
          f"-> {'CONSISTENT' if erratum['consistent'] else 'REJECTED (as required)'}")
    check(
        "guard_rejects_the_cycle_880_factor_10_erratum",
        not erratum["consistent"],
        f"the stated 0.0151 with 504 units/yr at 3 bp/unit is rejected: expected "
        f"{erratum['expected_cost_drag']:.6f}, abs diff {erratum['abs_diff']:.3e} "
        f"> {GUARD_TOLERANCE:.0e}.",
    )

    erratum_rows = []
    for bps in COST_ROWS_BPS:
        expected = 504.0 * bps / 10000.0
        wrong = expected / 10.0
        g = check_cost_drag_consistency(wrong, 504.0, bps)
        erratum_rows.append((bps, wrong, g))
        print(f"negative control at {bps:>4.0f} bp/unit: stated {wrong:.4f} vs expected "
              f"{g['expected_cost_drag']:.6f} | abs diff {g['abs_diff']:.3e} "
              f"-> {'CONSISTENT' if g['consistent'] else 'REJECTED (as required)'}")
    check(
        "guard_rejects_the_factor_10_erratum_at_every_cost_row",
        all(not g["consistent"] for _, _, g in erratum_rows),
        "a factor-10 understated drag is rejected at "
        + ", ".join(f"{bps:.0f} bp/unit (abs diff {g['abs_diff']:.3e})" for bps, _, g in erratum_rows)
        + f", every one of them far above the {GUARD_TOLERANCE:.0e} tolerance.",
    )

    raised = False
    try:
        require_cost_drag_consistency(0.0151, 504.0, 3.0, context="Cycle 880 erratum")
    except ValueError:
        raised = True
    check(
        "guard_raises_on_an_inconsistent_figure",
        raised,
        "require_cost_drag_consistency raises ValueError on the factor-10 error, so a "
        "screen that states an inconsistent drag cannot complete.",
    )

    self_guards = []
    for s in screens:
        g = check_cost_drag_consistency(
            s["cost_drag"][DECISION_BPS], s["annual_turnover_units"], DECISION_BPS
        )
        self_guards.append((s["candidate_id"], g))
        print(f"self-guard {s['candidate_id']:<26} stated {g['stated_cost_drag']:.6f} vs "
              f"expected {g['expected_cost_drag']:.6f} -> {'PASS' if g['consistent'] else 'FAIL'}")
    check(
        "every_stated_cost_drag_passes_the_guard",
        all(g["consistent"] for _, g in self_guards),
        "each candidate's own stated annualized cost drag equals its own stated annual "
        "turnover times the cost per unit to within 1e-9.",
    )

    # ---------------- reproduction of the committed records ----------------
    print("\n" + "-" * 78)
    print("5. REPRODUCTION OF THE COMMITTED RECORDS")
    print("-" * 78)

    def published_check(
        cid: str, name: str, observed: float, published: float, tolerance: float
    ) -> None:
        diff = abs(float(observed) - float(published))
        ok = diff <= tolerance
        print(f"{cid:<26} {name:<34} published {published:+.6f} | re-derived "
              f"{observed:+.6f} | diff {diff:.3e} -> {'PASS' if ok else 'FAIL'}")
        check(
            f"{cid}_reproduces_{name.replace(' ', '_')}",
            ok,
            f"published {published:+.6f} vs re-derived {observed:+.6f} "
            f"(abs diff {diff:.3e} <= {tolerance:.0e}).",
        )

    published_check(
        "overnight_capture_001", "net WF mean OOS Sharpe",
        on["wf_mean_oos_sharpe"], -0.599718, 1e-6,
    )
    published_check(
        "overnight_capture_001", "benchmark WF mean OOS Sharpe",
        on["benchmark_wf_mean_oos_sharpe"], 0.844696, 1e-6,
    )
    published_check(
        "overnight_capture_001", "positive fold rate",
        on["wf_positive_fold_rate"], 0.151515, 1e-6,
    )
    check(
        "overnight_capture_001_reproduces_pooled_oos_trades",
        on["wf_pooled_trades"] == 8016,
        f"published 8016 vs re-derived {on['wf_pooled_trades']} pooled out-of-sample trades.",
    )

    cal = by_id["calendar_effects_001"]
    published_check(
        "calendar_effects_001", "net WF mean OOS Sharpe",
        cal["wf_mean_oos_sharpe"], -0.0254, 1e-4,
    )
    published_check(
        "calendar_effects_001", "positive fold rate",
        cal["wf_positive_fold_rate"], 0.424242, 1e-4,
    )
    check(
        "calendar_effects_001_reproduces_pooled_oos_trades",
        cal["wf_pooled_trades"] == 761,
        f"published 761 vs re-derived {cal['wf_pooled_trades']} pooled out-of-sample trades.",
    )

    inc = by_id["tsmomentum_spytrend_001"]
    check(
        "incumbent_walk_forward_has_48_folds",
        inc["wf_folds"] == 48,
        f"the 1993-2026 geometry of the frozen configuration yields {inc['wf_folds']} folds "
        "(the published Cycle 6 record also states 48 folds).",
    )
    published_check(
        "tsmomentum_spytrend_001", "net WF mean OOS Sharpe",
        inc["wf_mean_oos_sharpe"], 0.9473, INCUMBENT_SHARPE_TOLERANCE,
    )

    inc_cand = candidates[2]
    inc_test_net = net_return_series(
        inc_cand.gross, inc_cand.turnover, DECISION_BPS
    )
    inc_test_net = inc_test_net[inc_test_net.index >= pd.Timestamp("2018-01-01", tz="UTC")]
    inc_test_sharpe = float(
        compute_metrics(
            inc_test_net,
            inc_cand.weights.loc[inc_test_net.index],
            COMMISSION_BPS,
            SLIPPAGE_BPS,
            RF_ANNUAL,
        )["sharpe_ratio"]
    )
    published_check(
        "tsmomentum_spytrend_001", "test period Sharpe 2018-2026",
        inc_test_sharpe, 1.4178, INCUMBENT_SHARPE_TOLERANCE,
    )
    print(f"  (the incumbent's published baseline is a configuration re-run with "
          f"overlay_warmup='slice'; the committed full-history artifact carries the overlay "
          f"state from 1993, so the two differ by less than the repository's own declared "
          f"TOL_SHARPE = {INCUMBENT_SHARPE_TOLERANCE})")

    # ---------------- determinism ----------------
    check(
        "benchmark_walk_forward_sharpe_is_cost_invariant",
        all(bool(s["benchmark_wf_sharpe_is_cost_invariant"]) for s in screens),
        "the close-to-close benchmark's walk-forward Sharpe is the same at 3 bp/unit and at "
        "10 bp/unit for every candidate (its only turnover is the initial purchase, which "
        "sits before the first test window), so the benchmark-parity cost compares the "
        "candidate and the benchmark at the same cost level on the same folds.",
    )

    repeat = screen_candidate(candidates[0])
    check(
        "screen_is_deterministic",
        all(
            abs(float(repeat[k]) - float(on[k])) <= 1e-15
            for k in ("annual_turnover_units", "gross_annualized_signal",
                      "min_gross_signal_required", "wf_mean_oos_sharpe")
        ),
        "re-running the screen on the same inputs reproduces the annual turnover, the gross "
        "annualized signal, the minimum required gross signal and the WF mean OOS Sharpe "
        "bit-for-bit.",
    )

    # ---------------- read-only proof ----------------
    fingerprint_after = directory_fingerprint([REPO_ROOT / "data", CONFIG_DIR])
    changed = [
        p for p in set(fingerprint_before) | set(fingerprint_after)
        if fingerprint_before.get(p) != fingerprint_after.get(p)
    ]
    check(
        "no_file_under_data_or_config_changed",
        not changed,
        f"the SHA-256 fingerprint of all {len(fingerprint_after)} files under data/ and config/ "
        f"is identical before and after the run"
        + (f"; changed: {changed}" if changed else "."),
    )

    # ---------------- report ----------------
    failed = [c["check"] for c in checks if not c["pass"]]
    overall = "PASS" if not failed else "FAIL"

    report = build_report(
        screens,
        checks,
        overall,
        today,
        revision,
        extras={"incumbent_test_sharpe": inc_test_sharpe},
    )
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(report)

    print("\n" + "-" * 78)
    print("6. SELF-CHECKS")
    print("-" * 78)
    for c in checks:
        print(f"[{'PASS' if c['pass'] else 'FAIL'}] {c['check']}")

    print("\n" + "-" * 78)
    print("7. ADMISSIBILITY SUMMARY")
    print("-" * 78)
    print(f"{'candidate':<26}{'gross/yr':>12}{'turn/yr':>10}{'drag@3bp':>12}"
          f"{'break-even':>14}{'verdict':>16}")
    for s in screens:
        be = s["break_even_cost"]
        be_txt = f"{be['solution']:.4f} bp" if be["solution"] is not None else "none"
        print(f"{s['candidate_id']:<26}{s['gross_annualized_signal'] * 100:>11.4f}%"
              f"{s['annual_turnover_units']:>10.2f}{s['cost_drag'][3.0] * 100:>11.4f}%"
              f"{be_txt:>14}{s['admissibility_verdict']:>16}")

    print(f"\nReport written: {REPORT_MD.relative_to(REPO_ROOT)}")
    print(f"\nOVERALL: {overall}")
    if failed:
        print(f"FAILED CHECKS: {failed}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
