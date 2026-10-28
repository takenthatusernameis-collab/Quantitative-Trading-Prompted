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

from research.month_end_candidate_reaudit import (  # noqa: E402
    build_csmomentum as build_csmomentum_path,
)
from research.month_end_candidate_reaudit import (  # noqa: E402
    build_macroregime as build_macroregime_path,
)
from research.sectorrotation_long_sample_feasibility import (  # noqa: E402
    build_monthly_weights as build_sectorrotation_weights,
)
from research.sectorrotation_long_sample_feasibility import (  # noqa: E402
    month_end_dates as sectorrotation_month_end_dates,
)
from src.backtest.engine import compute_metrics, get_cost_params, get_risk_free_rate  # noqa: E402
from src.evaluation.sharpe import sharpe_ratio  # noqa: E402
from src.evaluation.walkforward import generate_walkforward_splits  # noqa: E402
from src.features.momentum import compute_momentum, select_top_decile  # noqa: E402

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

#: The repository's own promotion threshold for the walk-forward mean OOS
#: Sharpe (``AGENTS.md`` and ``config/promotion_gates.yaml`` /
#: ``wf_mean_oos_sharpe_min`` in every frozen candidate configuration).
PROMOTION_WF_SHARPE_MIN: float = 0.9

#: The committed samples of the three month-end candidates, exactly as the
#: records that published their numbers state them:
#:   * ``csmomentum_001``  -- research/experiments/month_end_candidate_reaudit_001.md
#:   * ``macroregime_001``  -- research/experiments/month_end_candidate_reaudit_001.md
#:   * ``sectorrotation_001`` -- research/reports/sectorrotation_long_sample_feasibility_001.md
CS_SAMPLE = ("1993-01-01", "2026-10-09")
MACRO_SAMPLE = ("2004-11-18", "2026-10-09")
SECTOR_SAMPLE = ("1998-12-22", "2026-10-08")

#: The published test window of the two re-audited candidates.
TEST_START = "2018-01-01"


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


def gross_and_turnover(
    close: pd.DataFrame, weights: pd.DataFrame
) -> tuple[pd.Series, pd.Series]:
    """Daily gross return and daily turnover of a weight path.

    The same arithmetic as the repository's own research tools
    (``research/month_end_candidate_reaudit.py:path_returns`` and
    ``research/sectorrotation_long_sample_feasibility.py:portfolio_returns``):
    the close-to-close return of every asset, forward-filled to zero where a
    price history does not exist yet, weighted by the position, and the sum
    of the absolute weight changes.
    """
    common = close.index.intersection(weights.index)
    c = close.loc[common]
    w = weights.loc[common]
    daily_ret = c.pct_change().fillna(0.0)
    gross = (w * daily_ret).sum(axis=1)
    turnover = w.diff().abs().sum(axis=1).fillna(0.0)
    return gross, turnover


def invested_window(weights: pd.DataFrame) -> pd.DatetimeIndex:
    """The sessions from the first non-zero position to the end of the path.

    A candidate that cannot be invested before its signal warm-up is flat
    before it, and a flat period carries neither signal nor turnover, so the
    cost screen measures the candidate over the sessions it is actually
    invested. This is the same convention the committed records use
    ("invested sample" in
    ``research/reports/sectorrotation_long_sample_feasibility_001.md``).
    """
    invested = weights.sum(axis=1) > 0.0
    if not bool(invested.any()):
        return weights.index
    first = invested[invested].index.min()
    return weights.index[weights.index >= first]


def published_tolerance(published_text: str) -> float:
    """The comparison tolerance of a published number, in the repo's convention.

    The committed records quote their numbers as decimal strings, so the
    tolerance of a comparison is the unit of that string's last decimal
    (``research/month_end_candidate_reaudit.py:compare_published``): a
    4-decimal number is compared with a 1e-4 tolerance, a 2-decimal number
    with 1e-2. Counts are compared exactly (tolerance 0).
    """
    text = str(published_text)
    if "." not in text:
        return 0.0
    decimals = len(text.split(".")[1])
    return 10.0 ** (-decimals)


def sample_metrics(
    net_full: pd.Series,
    weights: pd.DataFrame,
    sample: pd.Index,
) -> dict[str, Any]:
    """The metrics of one sample of a path, in the committed records' convention.

    The return series is the **full path** sliced to *sample* (so the cost of
    the first session of the sample is not lost) while the weight frame is
    sliced as well, which is what ``research/month_end_candidate_reaudit.py:
    path_metrics`` does; the per-fold turnover and trade count therefore
    follow that record's convention.
    """
    r = net_full.loc[sample]
    w = weights.loc[r.index]
    if len(r) < 2:
        return {"sessions": len(r)}
    bt = compute_metrics(r, w, COMMISSION_BPS, SLIPPAGE_BPS, RF_ANNUAL)
    return {
        "sessions": len(r),
        "start": str(r.index[0].date()),
        "end": str(r.index[-1].date()),
        "sharpe_backtest_scale": float(bt["sharpe_ratio"]),
        "sharpe_canonical": float(sharpe_ratio(r)),
        "max_drawdown": float(bt["max_drawdown"]),
        "annualized_turnover": float(bt["annualized_turnover"]),
        "annualized_return": float(bt["annualized_return"]),
        "trade_days": int(bt["trade_count"]),
    }


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
    tolerance: float = 1e-6,
    max_iterations: int = 40,
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


def wf_mean_canonical_sharpe(
    gross: pd.Series,
    turnover: pd.Series,
    weights: pd.DataFrame,
    splits: list[dict[str, Any]],
    cost_bps_per_unit: float,
    explicit_turnover: bool = True,
) -> float:
    """Mean of the per-fold **canonical** Sharpes.

    The canonical scale (``arithmetic_annualized_rf0``, the single gate
    convention declared in ``config/promotion_gates.yaml`` and established in
    ``src/evaluation/sharpe.py``) is the scale the repository's promotion
    gates are expressed in, so it is the scale the **gate headroom** is
    measured on. The backtest-baseline scale is kept as well because the
    candidate records quote their walk-forward means on that scale.
    """
    df, _ = walkforward_table(
        gross, turnover, weights, splits, cost_bps_per_unit, explicit_turnover
    )
    if df.empty:
        return float("nan")
    return float(df["test_canonical_sharpe"].mean())


def wf_summary(
    gross: pd.Series,
    turnover: pd.Series,
    weights: pd.DataFrame,
    splits: list[dict[str, Any]],
    explicit_turnover: bool,
) -> dict[str, Any]:
    """The walk-forward summary of a path at the model's cost (3 bp/unit).

    Both Sharpe scales and both positive-fold rates are reported, because the
    committed candidate records quote their walk-forward statistics on
    different scales (the Cycle 871 record on the backtest-baseline scale,
    the Cycle 869 record on the canonical scale) and a reproduction check
    must compare like with like.
    """
    df, _ = walkforward_table(
        gross, turnover, weights, splits, DECISION_BPS, explicit_turnover
    )
    if df.empty:
        return {"folds": 0}
    return {
        "folds": len(df),
        "mean_sharpe_backtest": float(df["test_sharpe"].mean()),
        "mean_sharpe_canonical": float(df["test_canonical_sharpe"].mean()),
        "positive_fold_rate_backtest": float((df["test_sharpe"] > 0).mean()),
        "positive_fold_rate_canonical": float((df["test_canonical_sharpe"] > 0).mean()),
        "pooled_trades": int(df["test_trades"].sum()),
    }


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
    #: Reproduction of the candidate's own committed published record: one
    #: entry per published quantity, with the published value quoted exactly
    #: as the record states it, the value the screen re-derives from the
    #: committed cache and the comparison tolerance.
    verification: list[dict[str, Any]] = field(default_factory=list)


def _equal_weight_weights(index: pd.DatetimeIndex, symbols: list[str]) -> pd.DataFrame:
    return pd.DataFrame(1.0 / len(symbols), index=index, columns=symbols)


def _close_to_close_benchmark(
    close: pd.DataFrame,
    symbols: list[str],
    window: pd.DatetimeIndex,
    missing_as_cash: bool = False,
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

    ``missing_as_cash`` makes the "contributes zero" rule of the docstring
    true for a universe with **staggered inceptions**: without it a symbol
    that has no price yet contributes a NaN to the whole benchmark return
    and silently removes every fold that overlaps the gap. The three
    candidates screened in Cycle 881 keep the default (``False``) so that
    their published numbers do not move; the three month-end candidates
    added in Cycle 882 (18-ETF, 9-sector and 7-ETF universes with
    staggered inceptions) use ``True``.
    """
    weights = _equal_weight_weights(window, symbols)
    prev_close = close.shift(1)
    c2c = close / prev_close - 1.0
    c2c.iloc[0] = 0.0
    if missing_as_cash:
        c2c = c2c.fillna(0.0)
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
# The three month-end candidates (Cycle 882)
# ======================================================================
def _verification_entry(
    quantity: str,
    published_text: str,
    observed: float,
    source: str,
    tolerance: float | None = None,
) -> dict[str, Any]:
    """One row of the reproduction of a committed published record."""
    tol = published_tolerance(published_text) if tolerance is None else float(tolerance)
    return {
        "quantity": quantity,
        "published_text": str(published_text),
        "published": float(published_text),
        "observed": float(observed),
        "tolerance": float(tol),
        "source": source,
        "match": bool(abs(float(observed) - float(published_text)) <= tol),
        "abs_diff": abs(float(observed) - float(published_text)),
    }


def _month_end_candidate_splits(
    start: str, end: str, wf_cfg: dict[str, Any]
) -> list[dict[str, Any]]:
    """The candidate's own pre-registered walk-forward splits."""
    return generate_walkforward_splits(
        start,
        end,
        float(wf_cfg["train_years"]),
        float(wf_cfg["test_months"]),
        float(wf_cfg["step_months"]),
        int(wf_cfg["purge_days"]),
        int(wf_cfg["embargo_days"]),
    )


def build_csmomentum_candidate() -> Candidate:
    """``csmomentum_001``: long-only cross-sectional momentum, 18 ETFs.

    The construction is the **config-faithful month-end path** of Cycle 871
    (``research/month_end_candidate_reaudit.py:build_csmomentum`` ->
    ``faithful_schedule`` -> ``src/backtest/rebalance.py:build_month_end_weights``):
    the signal is formed on the last session of the calendar month and the
    positions become effective on the next session. The defective calendar
    rule and the daily re-rank path are not used.
    """
    cfg_path = CONFIG_DIR / "csmomentum_candidate_001.yaml"
    with open(cfg_path) as fh:
        cfg = yaml.safe_load(fh)
    universe = list(cfg["universe"])
    start, end = CS_SAMPLE

    close = load_cached_close_frame(universe, end=end)
    close = close.loc[
        (close.index >= pd.Timestamp(start, tz="UTC"))
        & (close.index <= pd.Timestamp(end, tz="UTC"))
    ].copy()

    path = build_csmomentum_path(close, REPO_COST_BPS / 10000.0)
    weights = path["faithful_weights"]
    gross, turnover = gross_and_turnover(close, weights)
    net_full = gross - turnover * (REPO_COST_BPS / 10000.0)

    window = invested_window(weights)
    gross = gross.loc[window]
    turnover = turnover.loc[window]
    net_full = net_full.loc[window]

    bench_gross, bench_turnover, bench_weights = _close_to_close_benchmark(
        close, universe, window, missing_as_cash=True
    )

    splits = _month_end_candidate_splits(start, end, cfg["evaluation"]["walk_forward"])

    test_idx = window[window >= pd.Timestamp(TEST_START, tz="UTC")]
    test = sample_metrics(net_full, weights, test_idx)

    source = "research/experiments/month_end_candidate_reaudit_001.md (config-faithful column)"
    verification = [
        _verification_entry(
            "Test-window Sharpe (backtest scale)", "0.4878",
            test["sharpe_backtest_scale"], source,
        ),
        _verification_entry(
            "Test-window Sharpe (canonical)", "0.6635",
            test["sharpe_canonical"], source,
        ),
        _verification_entry(
            "Test-window max drawdown", "-0.2940", test["max_drawdown"], source,
        ),
        _verification_entry(
            "Test-window annualized turnover", "2.47",
            test["annualized_turnover"], source,
        ),
        _verification_entry(
            "Test-window trade days", "77", test["trade_days"], source,
        ),
    ]
    wf = wf_summary(gross, turnover, weights.loc[window], splits, False)
    verification += [
        _verification_entry(
            "Walk-forward mean OOS Sharpe (backtest scale)", "0.6975",
            wf["mean_sharpe_backtest"], source,
        ),
        _verification_entry(
            "Walk-forward positive fold rate", "0.792",
            wf["positive_fold_rate_backtest"], source,
        ),
        _verification_entry(
            "Walk-forward pooled OOS trades", "400", wf["pooled_trades"], source,
        ),
        _verification_entry(
            "Walk-forward fold count", "48", wf["folds"], source,
        ),
    ]

    return Candidate(
        candidate_id=str(cfg["candidate_id"]),
        label="Long-only cross-sectional momentum, 18-ETF universe (month-end, top 50%)",
        role="candidate",
        universe=universe,
        window_start=str(window.min().date()),
        window_end=str(window.max().date()),
        gross=gross,
        turnover=turnover,
        weights=weights.loc[window],
        benchmark_gross=bench_gross,
        benchmark_turnover=bench_turnover,
        benchmark_weights=bench_weights,
        benchmark_label="close-to-close equal weight (same 18-ETF basket, same folds)",
        splits=splits,
        explicit_turnover=False,
        provenance={
            "config": f"config/{cfg_path.name}",
            "config_sha256[:12]": sha256_file(cfg_path)[:12],
            "price_cache": "data/raw/*.parquet (18 ETFs, cache only, no fetch)",
            "evaluation_script": "research/month_end_candidate_reaudit.py (Cycle 871)",
            "schedule": "src/backtest/rebalance.py:build_month_end_weights (Cycle 870)",
            "hypothesis": "research/hypotheses/csmomentum_001.md",
            "screen_window": "invested sample (first non-zero position .. 2026-10-09)",
        },
        published={
            "record": source,
            "test_sharpe_backtest_scale": 0.4878,
            "test_sharpe_canonical": 0.6635,
            "test_annualized_turnover": 2.47,
            "test_trade_days": 77,
            "wf_mean_oos_sharpe": 0.6975,
            "wf_positive_fold_rate": 0.792,
            "wf_pooled_trades": 400,
            "wf_folds": 48,
        },
        notes=[
            (
                "The trade-count and per-fold turnover convention of the Cycle 871 "
                "record (the weight frame is sliced per fold) is preserved, so the "
                "screen's pooled out-of-sample trade count is directly comparable "
                "with the published 400."
            ),
        ],
        verification=verification,
    )


def build_sectorrotation_candidate() -> Candidate:
    """``sectorrotation_001``: cross-sectional momentum over 9 GICS sectors.

    The construction is the **config-faithful month-end path** of Cycle 869
    (``research/sectorrotation_long_sample_feasibility.py:build_monthly_weights``
    -> ``src/backtest/rebalance.py:build_month_end_weights``).
    """
    cfg_path = CONFIG_DIR / "sectorrotation_candidate_001.yaml"
    with open(cfg_path) as fh:
        cfg = yaml.safe_load(fh)
    universe = list(cfg["universe"])
    start, end = SECTOR_SAMPLE

    close = load_cached_close_frame(universe, end=end)
    close = close.loc[
        (close.index >= pd.Timestamp(start, tz="UTC"))
        & (close.index <= pd.Timestamp(end, tz="UTC"))
    ].copy()

    signal = cfg["signal"]
    momentum = compute_momentum(
        close, lookback=int(signal["lookback"]), skip=int(signal["skip"])
    )
    mask = select_top_decile(momentum, top_fraction=float(signal["top_fraction"]))
    month_ends = sectorrotation_month_end_dates(close.index)
    weights, _segments = build_sectorrotation_weights(close, mask, month_ends)

    gross, turnover = gross_and_turnover(close, weights)
    net_full = gross - turnover * (REPO_COST_BPS / 10000.0)

    window = invested_window(weights)
    gross = gross.loc[window]
    turnover = turnover.loc[window]
    net_full = net_full.loc[window]

    bench_gross, bench_turnover, bench_weights = _close_to_close_benchmark(
        close, universe, window, missing_as_cash=True
    )

    splits = _month_end_candidate_splits(start, end, cfg["evaluation"]["walk_forward"])

    source = "research/reports/sectorrotation_long_sample_feasibility_001.md"
    verification = [
        _verification_entry(
            "Canonical Sharpe (invested sample)", "0.472367",
            float(sharpe_ratio(net_full)), source,
        ),
        _verification_entry(
            "Annualized turnover (invested sample)", "2.9961",
            annual_turnover_units(turnover), source,
        ),
        _verification_entry(
            "Trade days (invested sample)", "175",
            int((turnover > 1e-10).sum()), source,
        ),
    ]
    wf = wf_summary(gross, turnover, weights.loc[window], splits, True)
    verification += [
        _verification_entry(
            "Walk-forward mean OOS Sharpe (canonical)", "0.847243",
            wf["mean_sharpe_canonical"], source,
        ),
        _verification_entry(
            "Walk-forward positive fold rate", "0.9167",
            wf["positive_fold_rate_canonical"], source,
        ),
        _verification_entry(
            "Walk-forward pooled OOS trades", "215", wf["pooled_trades"], source,
        ),
        _verification_entry(
            "Walk-forward fold count", "36", wf["folds"], source,
        ),
    ]

    return Candidate(
        candidate_id=str(cfg["candidate_id"]),
        label="Sector rotation, 9 GICS sector ETFs (month-end, top 50%)",
        role="candidate",
        universe=universe,
        window_start=str(window.min().date()),
        window_end=str(window.max().date()),
        gross=gross,
        turnover=turnover,
        weights=weights.loc[window],
        benchmark_gross=bench_gross,
        benchmark_turnover=bench_turnover,
        benchmark_weights=bench_weights,
        benchmark_label="close-to-close equal weight (same 9-sector basket, same folds)",
        splits=splits,
        explicit_turnover=True,
        provenance={
            "config": f"config/{cfg_path.name}",
            "config_sha256[:12]": sha256_file(cfg_path)[:12],
            "price_cache": "data/raw/*.parquet (9 sector ETFs, cache only, no fetch)",
            "evaluation_script": "research/sectorrotation_long_sample_feasibility.py (Cycle 869)",
            "schedule": "src/backtest/rebalance.py:build_month_end_weights (Cycle 870)",
            "hypothesis": "research/hypotheses/sectorrotation_001.md",
            "screen_window": "invested sample (2000-02-01 .. 2026-10-08), the record's own sample",
        },
        published={
            "record": source,
            "canonical_sharpe": 0.472367,
            "annualized_turnover": 2.9961,
            "trade_days": 175,
            "wf_mean_oos_sharpe_canonical": 0.847243,
            "wf_positive_fold_rate": 0.9167,
            "wf_pooled_trades": 215,
            "wf_folds": 36,
        },
        notes=[
            (
                "The trade-count convention of the Cycle 869 record (counted from "
                "the turnover series) is preserved, so the screen's pooled "
                "out-of-sample trade count is directly comparable with the "
                "published 215."
            ),
        ],
        verification=verification,
    )


def build_macroregime_candidate() -> Candidate:
    """``macroregime_001``: the incumbent's overlays plus a VIX regime gate.

    The construction is the **config-faithful month-end path** of Cycle 871
    (``research/month_end_candidate_reaudit.py:build_macroregime`` ->
    ``faithful_schedule`` -> ``src/backtest/rebalance.py:build_month_end_weights``):
    the risk overlays are computed on the daily pipeline and the month-end
    schedule is applied to that pipeline, so the only difference from the
    defective calendar path is the schedule rule itself.
    """
    cfg_path = CONFIG_DIR / "macroregime_candidate_001.yaml"
    with open(cfg_path) as fh:
        cfg = yaml.safe_load(fh)
    universe = list(cfg["universe"])
    regime_driver = str(cfg["regime_driver"])
    start, end = MACRO_SAMPLE

    close = load_cached_close_frame(universe, end=end)
    close = close.loc[
        (close.index >= pd.Timestamp(start, tz="UTC"))
        & (close.index <= pd.Timestamp(end, tz="UTC"))
    ].copy()

    vix = load_cached_close_frame([regime_driver], end=end)[regime_driver]
    vix = vix.loc[
        (vix.index >= pd.Timestamp(start, tz="UTC"))
        & (vix.index <= pd.Timestamp(end, tz="UTC"))
    ].copy()
    vix = vix.reindex(close.index, method="ffill").ffill()

    path = build_macroregime_path(close, vix, REPO_COST_BPS / 10000.0)
    weights = path["faithful_weights"]
    gross, turnover = gross_and_turnover(close, weights)
    net_full = gross - turnover * (REPO_COST_BPS / 10000.0)

    window = invested_window(weights)
    gross = gross.loc[window]
    turnover = turnover.loc[window]
    net_full = net_full.loc[window]

    bench_gross, bench_turnover, bench_weights = _close_to_close_benchmark(
        close, universe, window, missing_as_cash=True
    )

    splits = _month_end_candidate_splits(start, end, cfg["evaluation"]["walk_forward"])

    test_idx = window[window >= pd.Timestamp(TEST_START, tz="UTC")]
    test = sample_metrics(net_full, weights, test_idx)

    source = "research/experiments/month_end_candidate_reaudit_001.md (config-faithful column)"
    verification = [
        _verification_entry(
            "Test-window Sharpe (backtest scale)", "0.1428",
            test["sharpe_backtest_scale"], source,
        ),
        _verification_entry(
            "Test-window Sharpe (canonical)", "0.3823",
            test["sharpe_canonical"], source,
        ),
        _verification_entry(
            "Test-window max drawdown", "-0.2240", test["max_drawdown"], source,
        ),
        _verification_entry(
            "Test-window annualized turnover", "4.22",
            test["annualized_turnover"], source,
        ),
        _verification_entry(
            "Test-window trade days", "84", test["trade_days"], source,
        ),
    ]
    wf = wf_summary(gross, turnover, weights.loc[window], splits, False)
    verification += [
        _verification_entry(
            "Walk-forward mean OOS Sharpe (backtest scale)", "0.2636",
            wf["mean_sharpe_backtest"], source,
        ),
        _verification_entry(
            "Walk-forward positive fold rate", "0.667",
            wf["positive_fold_rate_backtest"], source,
        ),
        _verification_entry(
            "Walk-forward pooled OOS trades", "193", wf["pooled_trades"], source,
        ),
        _verification_entry(
            "Walk-forward fold count", "24", wf["folds"], source,
        ),
    ]

    return Candidate(
        candidate_id=str(cfg["candidate_id"]),
        label="Macro regime overlay (TSMOM + SPY 200d SMA + VIX gate, month-end)",
        role="candidate",
        universe=universe,
        window_start=str(window.min().date()),
        window_end=str(window.max().date()),
        gross=gross,
        turnover=turnover,
        weights=weights.loc[window],
        benchmark_gross=bench_gross,
        benchmark_turnover=bench_turnover,
        benchmark_weights=bench_weights,
        benchmark_label="close-to-close equal weight (same 7-ETF basket, same folds)",
        splits=splits,
        explicit_turnover=False,
        provenance={
            "config": f"config/{cfg_path.name}",
            "config_sha256[:12]": sha256_file(cfg_path)[:12],
            "price_cache": "data/raw/*.parquet (7 ETFs + ^VIX as an input only, cache only)",
            "evaluation_script": "research/month_end_candidate_reaudit.py (Cycle 871)",
            "schedule": "src/backtest/rebalance.py:build_month_end_weights (Cycle 870)",
            "hypothesis": "research/hypotheses/macroregime_001.md",
            "screen_window": "invested sample (first non-zero position .. 2026-10-09)",
        },
        published={
            "record": source,
            "test_sharpe_backtest_scale": 0.1428,
            "test_sharpe_canonical": 0.3823,
            "test_annualized_turnover": 4.22,
            "test_trade_days": 84,
            "wf_mean_oos_sharpe": 0.2636,
            "wf_positive_fold_rate": 0.667,
            "wf_pooled_trades": 193,
            "wf_folds": 24,
        },
        notes=[
            (
                "The trade-count and per-fold turnover convention of the Cycle 871 "
                "record (the weight frame is sliced per fold) is preserved, so the "
                "screen's pooled out-of-sample trade count is directly comparable "
                "with the published 193."
            ),
            (
                "The record states the test-window trade days as 84 in its table "
                "and as 83 in its prose; the screen compares against the table's "
                "84 and reports the value it derives."
            ),
        ],
        verification=verification,
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

    _wf_cache = {}
    _wf_canon_cache = {}
    _net_cache = {}
    _sr_cache = {}

    def _get_net(c: float):
        key = (id(gross), id(turnover), float(c))
        if key not in _net_cache:
            _net_cache[key] = net_return_series(gross, turnover, c)
        return _net_cache[key]

    def _get_wf(c: float):
        key = (id(gross), id(turnover), id(cand.weights), id(tuple(cand.splits)), float(c), bool(cand.explicit_turnover))
        if key not in _wf_cache:
            _wf_cache[key] = wf_mean_sharpe(
                cand.gross,
                cand.turnover,
                cand.weights,
                cand.splits,
                c,
                cand.explicit_turnover,
            )
        return _wf_cache[key]

    def _get_wf_canon(c: float):
        key = (id(gross), id(turnover), id(cand.weights), id(tuple(cand.splits)), float(c), bool(cand.explicit_turnover))
        if key not in _wf_canon_cache:
            _wf_canon_cache[key] = wf_mean_canonical_sharpe(
                cand.gross,
                cand.turnover,
                cand.weights,
                cand.splits,
                c,
                cand.explicit_turnover,
            )
        return _wf_canon_cache[key]

    def _get_sr(s):
        key = id(s)
        if key not in _sr_cache:
            _sr_cache[key] = float(sharpe_ratio(s))
        return _sr_cache[key]

    cost_drag: dict[float, float] = {}
    net_ann: dict[float, float] = {}
    net_canonical: dict[float, float] = {}
    net_wf: dict[float, float] = {}
    net_wf_canonical: dict[float, float] = {}
    for bps in COST_ROWS_BPS:
        cost_drag[bps] = annualized_cost_drag(turnover, bps)
        net = _get_net(bps)
        net_ann[bps] = annualized_return(net)
        net_canonical[bps] = _get_sr(net)
        net_wf[bps] = _get_wf(bps)
        net_wf_canonical[bps] = _get_wf_canon(bps)

    min_gross_signal = cost_drag[DECISION_BPS]
    surplus = gross_ann - min_gross_signal
    admissible = bool(np.isfinite(net_ann[DECISION_BPS]) and net_ann[DECISION_BPS] > 0.0)

    # Break-even cost per unit: net annualized return = 0.
    be = solve_break_even_cost_bps(
        lambda c: annualized_return(_get_net(c))
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
        cand_sharpe = _get_wf(c)
        return cand_sharpe - bench_wf_sharpe

    parity = solve_break_even_cost_bps(parity_gap)

    # The same question on the full-window canonical Sharpe.
    def parity_gap_full(c: float) -> float:
        cand_sharpe = _get_sr(_get_net(c))
        bench_sharpe = _get_sr(net_return_series(cand.benchmark_gross, cand.benchmark_turnover, c))
        return cand_sharpe - bench_sharpe

    parity_full = solve_break_even_cost_bps(parity_gap_full)

    # Gate headroom: the cost per unit at which the candidate's net
    # walk-forward mean OOS Sharpe falls to the repository's own promotion
    # threshold (0.9). The gate is measured on the **canonical** scale
    # (``arithmetic_annualized_rf0``, the single gate convention declared in
    # ``config/promotion_gates.yaml``); the backtest-baseline scale, on
    # which the candidate records quote their walk-forward means, is
    # published next to it.
    def gate_gap(c: float) -> float:
        return _get_wf_canon(c) - PROMOTION_WF_SHARPE_MIN

    def gate_gap_backtest(c: float) -> float:
        return _get_wf(c) - PROMOTION_WF_SHARPE_MIN

    gate_headroom = solve_break_even_cost_bps(gate_gap)
    gate_headroom_backtest = solve_break_even_cost_bps(gate_gap_backtest)

    # The candidate's walk-forward mean OOS Sharpe before any cost is charged:
    # a candidate that is already below the gate at zero cost has no cost
    # headroom at all, and a negative gate headroom means it would have to be
    # *paid* to trade to reach the gate.
    wf_sharpe_at_zero_cost = _get_wf_canon(0.0)
    wf_sharpe_at_zero_cost_backtest = _get_wf(0.0)

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
        "wf_mean_canonical_sharpe": net_wf_canonical,
        "min_gross_signal_required": min_gross_signal,
        "gross_signal_surplus": surplus,
        "admissible": admissible,
        "admissibility_verdict": "ADMISSIBLE" if admissible else "INADMISSIBLE",
        "break_even_cost": be,
        "benchmark_parity_cost": parity,
        "benchmark_parity_cost_full_window": parity_full,
        "gate_headroom": gate_headroom,
        "gate_headroom_backtest_scale": gate_headroom_backtest,
        "wf_sharpe_at_zero_cost": wf_sharpe_at_zero_cost,
        "wf_sharpe_at_zero_cost_backtest_scale": wf_sharpe_at_zero_cost_backtest,
        "promotion_threshold": PROMOTION_WF_SHARPE_MIN,
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
        "verification": cand.verification,
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
        f"{_fmt(screen['wf_mean_sharpe'][bps], 4)} | "
        f"{_fmt(screen['wf_mean_canonical_sharpe'][bps], 4)} |"
    )


def _gate_text(solution: float | None) -> str:
    """The gate-headroom cell of a candidate block."""
    if solution is None:
        return "none (no cost level in [-100, 1000] bp/unit reaches the gate)"
    if solution < 0.0:
        return (
            f"{_fmt(solution, 4)} bp/unit (negative: the candidate would have to be "
            "**paid** to trade to reach the gate)"
        )
    return f"{_fmt(solution, 4)} bp/unit"


def _gate_headroom_text(screen: dict[str, Any], key: str = "gate_headroom") -> str:
    return _gate_text(screen[key]["solution"])


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

    verification_rows = "\n".join(
        f"| `{s['candidate_id']}` | {e['quantity']} | {e['published_text']} | "
        f"{_fmt(e['observed'], 6)} | {e['tolerance']:.0e} | "
        f"{'yes' if e['match'] else '**NO**'} |"
        for s in screens
        for e in s.get("verification", [])
    )

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
| WF mean OOS Sharpe, canonical scale (3 bp/unit) | {_fmt(s['wf_mean_canonical_sharpe'][3.0], 6)} |
| Benchmark WF mean OOS Sharpe (3 bp/unit, same folds) | {_fmt(s['benchmark_wf_mean_oos_sharpe'], 6)} |
| Positive fold rate / pooled OOS trades | {s['wf_positive_fold_rate'] * 100:.4f}% / {s['wf_pooled_trades']} |
| **Admissibility verdict (3 bp/unit)** | **{s['admissibility_verdict']}** |
| WF mean OOS Sharpe at **zero** cost (canonical scale) | {_fmt(s['wf_sharpe_at_zero_cost'], 6)} |
| Promotion threshold (walk-forward mean OOS Sharpe) | {_fmt(s['promotion_threshold'], 2)} |
| **Gate headroom: cost per unit at which the net WF mean OOS Sharpe falls to {_fmt(s['promotion_threshold'], 2)} (canonical scale, {s['wf_folds']} folds)** | **{_gate_headroom_text(s)}** |
| Gate headroom, backtest-baseline scale (the scale of the candidate records) | {_gate_headroom_text(s, 'gate_headroom_backtest_scale')} |

Cost sensitivity of the screen's own quantities:

| Cost (bp/unit) | Annualized cost drag | Net annualized return | Net canonical Sharpe | WF mean OOS Sharpe | WF mean OOS Sharpe (canonical) |
|---|---|---|---|---|---|
{_cost_row(s, 3.0)}
{_cost_row(s, 5.0)}
{_cost_row(s, 10.0)}

Provenance: {"; ".join(f"{k} = {v}" for k, v in s['provenance'].items())}

Notes: {" ".join(s['notes']) if s['notes'] else "none."}
"""
        )

    summary_rows = "\n".join(
        f"| `{s['candidate_id']}` | {_pct(s['gross_annualized_signal'], 4)} | "
        f"{_fmt(s['annual_turnover_units'], 2)} | "
        f"{_pct(s['cost_drag'][3.0], 4)} | {_pct(s['cost_drag'][5.0], 4)} | "
        f"{_pct(s['cost_drag'][10.0], 4)} | {be_text[s['candidate_id']]} | "
        f"{_pct(s['min_gross_signal_required'], 4)} | **{s['admissibility_verdict']}** | "
        f"{_gate_headroom_text(s)} |"
        for s in screens
    )

    on_s = by_id["overnight_capture_001"]
    cal_s = by_id["calendar_effects_001"]
    inc_s = by_id["tsmomentum_spytrend_001"]
    cs_s = by_id["csmomentum_001"]
    sec_s = by_id["sectorrotation_001"]
    mac_s = by_id["macroregime_001"]
    on_be = on_s["break_even_cost"]["solution"]
    on_par = on_s["benchmark_parity_cost"]["solution"]
    cal_be = cal_s["break_even_cost"]["solution"]
    cal_par = cal_s["benchmark_parity_cost"]["solution"]
    inc_be = inc_s["break_even_cost"]["solution"]
    inc_par = inc_s["benchmark_parity_cost"]["solution"]
    on_ratio = on_s["gross_annualized_signal"] / on_s["min_gross_signal_required"]
    cal_ratio = cal_s["gross_annualized_signal"] / cal_s["min_gross_signal_required"]
    inc_ratio = inc_s["gross_annualized_signal"] / inc_s["min_gross_signal_required"]
    cs_ratio = cs_s["gross_annualized_signal"] / cs_s["min_gross_signal_required"]
    sec_ratio = sec_s["gross_annualized_signal"] / sec_s["min_gross_signal_required"]
    mac_ratio = mac_s["gross_annualized_signal"] / mac_s["min_gross_signal_required"]
    cs_gh = cs_s["gate_headroom"]["solution"]
    sec_gh = sec_s["gate_headroom"]["solution"]
    on_gh = on_s["gate_headroom"]["solution"]
    inc_gh = inc_s["gate_headroom"]["solution"]
    cs_par = cs_s["benchmark_parity_cost"]["solution"]
    sec_par = sec_s["benchmark_parity_cost"]["solution"]
    mac_par = mac_s["benchmark_parity_cost"]["solution"]

    return f"""# Cost-Admissibility Screen (cost_admissibility_screen_001, Cycle 881; extended in Cycle 882)

**Generated:** {today} | **code revision:** {revision}
**Tool:** `research/cost_admissibility_screen.py` (read-only, deterministic, exit 0 on `OVERALL: PASS`)
**Cost model:** the repository's flat model, `get_cost_params()` = 1 bp commission + 2 bp slippage
= **{REPO_COST_BPS:.1f} bp per unit of weight change**; sensitivity rows 3 / 5 / 10 bp per unit.

## What changed in Cycle 882

The tool was **extended, not duplicated**. Three candidates were added
(`csmomentum_001`, `sectorrotation_001`, `macroregime_001`), one decision number was added (the
**gate headroom**) and the shortlist's cost column was completed for every row.

* **No number that Cycle 881 published has changed.** The three Cycle 881 blocks carry the same
  values to the same precision; the only additions inside them are the new gate-headroom lines
  and the new canonical-scale column of the cost-sensitivity table, plus the two new
  "reproduction of the committed records" tables.
* The three new candidates are built on the repository's **already-validated config-faithful
  month-end construction** (`src/backtest/rebalance.py`, Cycle 870) through the existing research
  tools `research/month_end_candidate_reaudit.py` (Cycle 871) and
  `research/sectorrotation_long_sample_feasibility.py` (Cycle 869). The defective calendar rule
  and the daily re-rank path are not used, and no parameter, universe, cost model, gate or
  threshold is changed.

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

| Candidate | Gross annualized signal | Annual turnover (units/yr) | Drag @3 bp | Drag @5 bp | Drag @10 bp | Break-even cost | Min gross signal needed @3 bp | Admissibility | Gate headroom (WF Sharpe = 0.9) |
|---|---|---|---|---|---|---|---|---|---|
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
   break-even cost the three candidates screened in Cycle 881 are
   `tsmomentum_spytrend_001` ({_fmt(inc_be, 4)} bp/unit) >
   `calendar_effects_001` ({_fmt(cal_be, 4)} bp/unit) >
   `overnight_capture_001` ({_fmt(on_be, 4)} bp/unit), whereas the shortlist's ranking is by gross
   effect size and states no cost column at all. **The cost screen has to be applied before a
   candidate is short-listed, not after it has been back-tested.**
5. **The three remaining shortlist candidates are all ADMISSIBLE on cost, and the shortlist's
   cost column is now complete.** `csmomentum_001` ({_fmt(cs_s['annual_turnover_units'], 4)}
   units of annual turnover, {_pct(cs_s['cost_drag'][3.0], 4)}/yr of drag at 3 bp/unit,
   {_fmt(cs_s['break_even_cost']['solution'], 2)} bp/unit break-even),
   `sectorrotation_001` ({_fmt(sec_s['annual_turnover_units'], 4)} units,
   {_pct(sec_s['cost_drag'][3.0], 4)}/yr, {_fmt(sec_s['break_even_cost']['solution'], 2)} bp/unit) and
   `macroregime_001` ({_fmt(mac_s['annual_turnover_units'], 4)} units,
   {_pct(mac_s['cost_drag'][3.0], 4)}/yr, {_fmt(mac_s['break_even_cost']['solution'], 2)} bp/unit)
   each carry a gross signal that is {_fmt(cs_ratio, 1)}x, {_fmt(sec_ratio, 1)}x and
   {_fmt(mac_ratio, 1)}x what their own turnover requires. All three re-derive their committed
   published records exactly (section 3.2), so the cost column is measured, not estimated.
6. **Their headroom is survival, not edge.** The **gate headroom** - the cost per unit at which
   the candidate's net walk-forward mean OOS Sharpe falls to the repository's own 0.9 promotion
   threshold - is **negative for all three**: `csmomentum_001` {_fmt(cs_gh, 4)} bp/unit,
   `sectorrotation_001` {_fmt(sec_gh, 4)} bp/unit and `macroregime_001` *no crossing at all*
   (its canonical walk-forward mean OOS Sharpe is only
   {_fmt(mac_s['wf_sharpe_at_zero_cost'], 4)} before any cost is charged, against the 0.90 gate).
   A negative gate headroom means the candidate would have to be **paid** to trade to reach the
   gate; no cost level, and no rebate, promotes it. Their **benchmark-parity costs are negative
   as well** ({_fmt(cs_par, 4)}, {_fmt(sec_par, 4)} and {_fmt(mac_par, 4)} bp/unit): at *zero* cost
   they already fail to match passive close-to-close holding of the same basket on the same folds.
   The overnight candidate is the mirror image: its gate headroom is positive
   ({_fmt(on_gh, 4)} bp/unit) but far below the {_fmt(REPO_COST_BPS, 1)} bp/unit the model
   charges, so it cannot be promoted at the model's cost either. Only the incumbent has real
   headroom ({_fmt(inc_gh, 4)} bp/unit, {_fmt(inc_gh / REPO_COST_BPS, 1)}x the model cost).
7. **Answer to this cycle's objective question: none of the remaining candidates is worth a
   promotion-gate test, and the headroom they have is only survival.** `csmomentum_001`,
   `sectorrotation_001` and `macroregime_001` survive their own costs with a very large margin,
   but every one of them is *below* the repository's 0.9 walk-forward gate before a single basis
   point is charged, and every one of them is *behind* the passive basket on the same folds at
   zero cost. Their cost headroom is a statement about how little they trade, not about an
   edge. Consequently the shortlist's remaining rows support **no further candidate evaluation**:
   the three candidates stay **Rejected/Failed** on their own pre-registered gates
   (`research/experiments/month_end_candidate_reaudit_001.md` and
   `research/reports/sectorrotation_long_sample_feasibility_001.md`), and the cost screen adds no
   candidate. The incumbent's headroom is likewise only *survival*; its edge is established by its
   own walk-forward record, not by this screen.

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
   positive, INADMISSIBLE otherwise;
8. the **gate headroom**: the cost per unit at which the candidate's net walk-forward mean OOS
   Sharpe falls to the repository's own promotion threshold of
   {_fmt(PROMOTION_WF_SHARPE_MIN, 2)} (`AGENTS.md`, `config/promotion_gates.yaml`,
   `wf_mean_oos_sharpe_min` in every frozen candidate configuration). It is measured on the
   **canonical** scale (`arithmetic_annualized_rf0`), the single gate convention the repository
   declares, and the backtest-baseline scale is published next to it because the candidate
   records quote their walk-forward means on that scale. The screen also publishes the
   candidate's walk-forward mean OOS Sharpe **at zero cost**, because a candidate that is
   already below the gate before a basis point is charged has no headroom at all, and a
   **negative** headroom means the candidate would have to be *paid* to trade to reach the gate.

The **benchmark** is a close-to-close equal-weight buy-and-hold of the candidate's own universe
on the candidate's own folds, with one unit of turnover in the first session and none afterwards
(the repository's own `1/N Equal-Weight` convention; for `overnight_capture_001` this is exactly
the benchmark Cycle 880 published). A symbol without a price history yet contributes zero, i.e.
the remainder is held in cash. The three candidates with a staggered-inception universe
(`csmomentum_001`: 18 ETFs, `sectorrotation_001`: 9 sector ETFs, `macroregime_001`: 7 ETFs) use
that cash rule explicitly, because otherwise a symbol without a price yet contributes a NaN to
the whole benchmark return and silently removes every fold that overlaps the gap. The three
candidates of Cycle 881 keep their original benchmark, so their published numbers do not move.

**What this cycle does not do.** No candidate is re-optimized, no parameter is selected, no
threshold is changed, no gate is re-thresholded, and no candidate's published verdict is
re-decided. The walk-forward statistics are re-derived only to (a) validate that the screen
reproduces the committed records and (b) place the candidate and its benchmark on identical
folds. A re-derivation that does not match a committed record is reported as a **FAIL**, never
re-tuned.

## 2. Candidates screened

{chr(10).join(sections)}

## 3. Reproduction of the committed records

### 3.1 The three candidates screened in Cycle 881

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

### 3.2 The three month-end candidates added in Cycle 882

**Tolerance rule.** The committed records quote their numbers as decimal strings, so the
tolerance of every comparison is the unit of that string's last decimal - the repository's own
rule (`research/month_end_candidate_reaudit.py:compare_published`). A 4-decimal published
number is therefore compared with 1e-4, a 2-decimal one with 1e-2, a 6-decimal one with 1e-6,
and a **count** (folds, trade days, pooled trades) with **0** (exact match), because a count is
an integer and no rounding is implied.

| Candidate | Quantity | Published | Re-derived | Tolerance | Match |
|---|---|---|---|---|---|
{verification_rows}

A mismatch here would be a **FAIL** and would be reported, never re-tuned: the screen measures
costs, it does not re-judge a candidate.

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
* **The screen window of the three month-end candidates is their *invested* sample.** A candidate
  that cannot be invested before its signal warm-up is flat before it, and a flat period carries
  neither signal nor turnover, so the screen measures it from the first session with a non-zero
  position to the end of the committed cache. This is the sample the committed records use
  ("invested sample" in `research/reports/sectorrotation_long_sample_feasibility_001.md`); the
  walk-forward folds are still the candidate's own pre-registered splits, generated from the
  candidate's own sample start, so the fold count and the fold windows are unchanged
  (48 / 36 / 24 folds for `csmomentum_001` / `sectorrotation_001` / `macroregime_001`).
* **The trade-count conventions of the two records differ and both are kept.** The Cycle 871
  record counts a fold's trades from the **sliced weight frame** (the first session of a fold
  contributes no trade), the Cycle 869 record counts them from the **turnover series** (the
  first session of a fold does). The screen keeps each candidate's own convention so that its
  pooled out-of-sample trade count is directly comparable with the number it is checked against
  (`csmomentum_001` 400, `macroregime_001` 193, `sectorrotation_001` 215). The convention only
  affects the trade-count and per-fold turnover columns, never a Sharpe.
* **`macroregime_001`'s record states its test-window trade days twice.** The table of
  `research/experiments/month_end_candidate_reaudit_001.md` says 84 and its prose says 83. The
  screen compares against the table's 84 and reports the value it derives (84), so the
  discrepancy inside the record is visible rather than silently resolved.

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
* the difference between a **backtest** cost model and a **paper-trading** one;
* the **statistical significance** of the walk-forward means the gate headroom is measured on.
  The gate headroom says at which cost the *point estimate* of the walk-forward mean OOS Sharpe
  reaches 0.9; it says nothing about the confidence interval of that estimate, about the
  positive-fold rate, about the pooled trade count (the second promotion gate, > 100 pooled
  out-of-sample trades) or about any other gate of `config/promotion_gates.yaml`;
* the **monotonicity** of the Sharpe in the cost. The break-evens and the gate headroom are
  bisections on a bracket that keeps its sign change, so a reported crossing is a genuine
  crossing; if the objective were not monotone in the cost, the reported value would be *a*
  crossing and not necessarily the outermost one.

A candidate that passes the screen can still be rejected by the promotion gates, and a
candidate that fails the screen is rejected on cost before any further work is justified. The
screen's verdict is **necessary, never sufficient**, and the Cycle 882 addition of the gate
headroom does not change that: it measures how much cost a candidate can afford, not whether it
has an edge.

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
    print("CYCLE 882: COST-ADMISSIBILITY SCREEN (cost_admissibility_screen_001)")
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
        build_csmomentum_candidate(),
        build_sectorrotation_candidate(),
        build_macroregime_candidate(),
        build_cryptofunding_candidate(),
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
                  f"| WF mean OOS Sharpe {screen['wf_mean_sharpe'][bps]:+.6f} "
                  f"| WF mean OOS Sharpe (canonical) {screen['wf_mean_canonical_sharpe'][bps]:+.6f}")
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
        gh = screen["gate_headroom"]
        gh_txt = (f"{gh['solution']:.6f} bp/unit" if gh["solution"] is not None
                  else f"none in [{gh['lo']:.0f}, {gh['hi']:.0f}] bp/unit ({gh['reason']})")
        ghb = screen["gate_headroom_backtest_scale"]
        ghb_txt = (f"{ghb['solution']:.6f} bp/unit" if ghb["solution"] is not None
                   else f"none in [{ghb['lo']:.0f}, {ghb['hi']:.0f}] bp/unit")
        print(f"  WF mean OOS Sharpe at 0 cost   {screen['wf_sharpe_at_zero_cost']:+.6f} "
              f"(canonical) | {screen['wf_sharpe_at_zero_cost_backtest_scale']:+.6f} (backtest scale)")
        print(f"  GATE HEADROOM (WF Sharpe = 0.9) {gh_txt} | backtest scale {ghb_txt}")
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

    # --- the three month-end candidates added in Cycle 882 -----------------
    for cid in ("csmomentum_001", "sectorrotation_001", "macroregime_001"):
        s = by_id[cid]
        for entry in s["verification"]:
            ok = bool(entry["match"])
            print(f"{cid:<26} {entry['quantity']:<44} published {entry['published']:+.6f} "
                  f"| re-derived {entry['observed']:+.6f} | diff {entry['abs_diff']:.3e} "
                  f"-> {'PASS' if ok else 'FAIL'}")
            check(
                f"{cid}_reproduces_{entry['quantity'].replace(' ', '_').replace('-', '_')}",
                ok,
                f"published {entry['published']:+.6f} vs re-derived {entry['observed']:+.6f} "
                f"(abs diff {entry['abs_diff']:.3e} <= {entry['tolerance']:.0e}); "
                f"source: {entry['source']}.",
            )
        check(
            f"{cid}_reproduces_its_committed_published_record",
            all(bool(e["match"]) for e in s["verification"]),
            f"all {len(s['verification'])} published quantities of {cid} are reproduced from the "
            f"committed cache within the tolerance of the record's own last decimal.",
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
          f"{'break-even':>14}{'verdict':>16}{'gate headroom':>18}")
    for s in screens:
        be = s["break_even_cost"]
        be_txt = f"{be['solution']:.4f} bp" if be["solution"] is not None else "none"
        gh = s["gate_headroom"]
        gh_txt = f"{gh['solution']:.4f} bp" if gh["solution"] is not None else "none"
        print(f"{s['candidate_id']:<26}{s['gross_annualized_signal'] * 100:>11.4f}%"
              f"{s['annual_turnover_units']:>10.2f}{s['cost_drag'][3.0] * 100:>11.4f}%"
              f"{be_txt:>14}{s['admissibility_verdict']:>16}{gh_txt:>18}")

    print(f"\nReport written: {REPORT_MD.relative_to(REPO_ROOT)}")
    print(f"\nOVERALL: {overall}")
    if failed:
        print(f"FAILED CHECKS: {failed}", file=sys.stderr)
        return 1
    return 0

def build_cryptofunding_candidate() -> Candidate:
    """cryptofunding_001: spot-long + perp-short carry (Binance)."""
    REPO = Path(__file__).resolve().parent.parent
    PROC = REPO / "data" / "processed" / "crypto"
    dfs = []
    for s in ["BTC", "ETH"]:
        df = pd.read_parquet(PROC / f"{s}USDT_carry_path.parquet")
        df = df[["gross_carry", "spot_return", "perp_return", "funding_cashflow"]].copy()
        dfs.append(df)
    common = dfs[0].index
    for d in dfs[1:]:
        common = common.intersection(d.index)
    btc = dfs[0].loc[common].rename(columns=lambda x: f"BTC_{x}")
    eth = dfs[1].loc[common].rename(columns=lambda x: f"ETH_{x}")
    df = pd.concat([btc, eth], axis=1)
    cal = df.index
    weights = pd.DataFrame(0.5, index=cal, columns=["BTC", "ETH"])
    gross_btc = df["BTC_gross_carry"].astype(float)
    gross_eth = df["ETH_gross_carry"].astype(float)
    gross = (weights["BTC"] * gross_btc + weights["ETH"] * gross_eth).astype(float)
    turnover = (weights["BTC"] * (df["BTC_spot_return"].abs() + df["BTC_perp_return"].abs()) +
                weights["ETH"] * (df["ETH_spot_return"].abs() + df["ETH_perp_return"].abs())).astype(float)
    bench_gross = (0.5 * df["BTC_spot_return"].astype(float) + 0.5 * df["ETH_spot_return"].astype(float))
    bench_turnover = pd.Series(0.0, index=cal)
    bench_turnover.iloc[0] = 1.0
    bench_weights = weights.copy()
    # use simple splits
    splits = generate_walkforward_splits(
        str(cal.min().date()),
        str(cal.max().date()),
        2.0, 6.0, 3.0, 0, 0,
    )
    return Candidate(
        candidate_id="cryptofunding_001",
        label="Crypto perpetual funding-rate carry (spot long + perp short, equal weight BTC/ETH)",
        role="candidate",
        universe=["BTC", "ETH"],
        window_start=str(cal.min().date()),
        window_end=str(cal.max().date()),
        gross=gross,
        turnover=turnover,
        weights=weights,
        benchmark_gross=bench_gross,
        benchmark_turnover=bench_turnover,
        benchmark_weights=bench_weights,
        benchmark_label="close-to-close equal weight spot (BTC/ETH)",
        splits=splits,
        explicit_turnover=True,
        provenance={
            "data": "data/processed/crypto/*_carry_path.parquet (checksum-verified, 2020-01-02..2026-09-30)",
            "hypothesis": "research/hypotheses/cryptofunding_001.md",
            "evaluation_script": "research/eval_cryptofunding.py",
        },
        published={},
        notes=["Crypto carry strategy using funding rates; net-of-cost evaluated in Cycle 890."],
        verification=[],
    )


if __name__ == "__main__":
    sys.exit(main())
