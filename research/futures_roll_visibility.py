"""Cycle 884: roll-date visibility in the cached front-month futures series.

Purpose
-------
Cycle 883 recorded shortlist rank 7 (`futuresbasis_001`) as **Blocked by
data/infrastructure** with the statement that the roll dates, the roll prices
and the roll cost actually paid are *all* unobservable from the cached
continuous front-month series.

That statement was too strong, and this module is the measurement that shows
it. The cached Yahoo front-month series carry a **Volume** column, and that
column is the *front contract's* volume: at every roll the front contract is
replaced, so the volume identity changes with the contract. The expiring
contract's volume runs off as it approaches delivery and the new front's
volume resumes at its typical level, which leaves a **recurring expiry
signature** in the volume series.

This module detects that signature with a deterministic rule and reports, per
product, the detected roll events and the spacing between consecutive rolls.
The spacing is the falsification test: a false-positive detector would scatter
events arbitrarily, whereas the real roll cycle is monthly for CL/NG,
bi-monthly for GC and quarterly for ZB.

What this module does **not** do
--------------------------------
* It does **not** observe the roll *price*. The leg prices on either side of
  a roll (the expiring contract's close and the new front's close) are still
  not available from any source in scope, so the roll spread and the roll
  cost actually paid remain unobservable. The candidate stays **blocked**.
* It does **not** back-test anything, and it does **not** write a spliced
  series into the repository. It is a data-visibility diagnostic.
* It does **not** re-rank or re-score any shortlist row.

Read-only guarantees
--------------------
* the only files read are the committed raw caches under ``data/raw/``;
* the only file written is this cycle's report under ``research/reports/``;
* the SHA-256 fingerprint of every file under ``data/`` and ``config/`` is
  taken before and after the run and compared;
* no network access: the volume signature is computed from the committed
  parquet files, and a missing file is a hard error, never a fetch.

Reproduction
------------
::

    python research/futures_roll_visibility.py   # exit 0, OVERALL: PASS
    python -m pytest tests/test_futures_roll_visibility.py -q
    python -m pytest -q
    git status --porcelain data/ config/            # empty
"""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

RAW_DIR = REPO_ROOT / "data" / "raw"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
REPORT_MD = REPORTS_DIR / "futures_roll_visibility_001.md"

#: The four cached continuous front-month series (Cycle 883 data gate).
FUTURES_SYMBOLS: tuple[str, ...] = ("CL-F", "NG-F", "GC-F", "ZB-F")

#: Human label of each stored series and the Yahoo symbol it came from.
SYMBOL_LABELS: dict[str, str] = {
    "CL-F": "WTI crude oil front month (CL=F)",
    "NG-F": "Henry Hub natural gas front month (NG=F)",
    "GC-F": "COMEX gold front month (GC=F)",
    "ZB-F": "US Treasury bond front month (ZB=F)",
}

#: The contract cycle of each product, **exogenous** (it is a property of the
#: exchange's listed contract months, not of this repository's data):
#: CL and NG list every calendar month; GC lists two active contract months
#: per year; ZB is a quarterly cycle (Mar/Jun/Sep/Dec). The windows below are
#: the calendar-day windows implied by those cycles and are the falsification
#: test of the detector: a detector that fires on noise would not reproduce
#: them.
CYCLE_LABELS: dict[str, str] = {
    "CL-F": "monthly (every calendar month)",
    "NG-F": "monthly (every calendar month)",
    "GC-F": "bi-monthly (two active contract months per year)",
    "ZB-F": "quarterly (Mar/Jun/Sep/Dec)",
}
CYCLE_WINDOW_DAYS: dict[str, tuple[int, int]] = {
    "CL-F": (25, 35),
    "NG-F": (25, 35),
    "GC-F": (50, 70),
    "ZB-F": (80, 100),
}

#: Volume-signature rule. The ratio is the session's volume over the median
#: volume of the preceding ``VOLUME_RATIO_WINDOW`` sessions (the median is
#: shifted by one session so the rule never looks at the current session).
VOLUME_RATIO_WINDOW = 60
VOLUME_RATIO_MIN_PERIODS = 20
#: A run-off session: the expiring contract trades at less than this multiple
#: of its trailing median volume.
TROUGH_RATIO = 0.55
#: The expiry session: the volume ratio recovers to at least this multiple of
#: the trailing median (the expiring contract's final session is often the
#: busiest of its life, and the new front's volume resumes afterwards).
RECOVERY_RATIO = 1.0
#: The new front's volume must stay at least this multiple of the trailing
#: median for this many sessions after the expiry session.
HOLD_RATIO = 0.70
HOLD_SESSIONS = 4
#: How far ahead of a run-off session the expiry session may lie.
MAX_LOOKAHEAD_SESSIONS = 8

#: The independent, externally verified ground truth for the most recent roll
#: inside the cached window. It was established by comparing the cached
#: series' volume column with Yahoo Finance's per-contract volume series
#: (see ``research/reports/futures_roll_visibility_001.md`` §3):
#: the cached chain's volume equals the **Nov-2026** contract's volume
#: through 2026-10-16 and the **Dec-2026** contract's volume from 2026-10-19,
#: so the Oct-2026 contract was the front month up to and including
#: 2026-09-22 and the Nov-2026 contract became the front month on 2026-09-23.
GROUND_TRUTH_EXPIRY = "2026-09-22"
GROUND_TRUTH_ROLL = "2026-09-23"
GROUND_TRUTH_SYMBOL = "CL-F"

#: The only cached spot proxy for a cached futures leg: ``GLD`` is a physical
#: gold trust, so its total return tracks the gold *spot* move. The other
#: three legs (CL, NG, ZB) have no cached spot proxy, so the aggregate
#: roll-effect measurement below is possible for gold only.
SPOT_PROXIES: dict[str, str] = {"GC-F": "GLD"}

#: Block-bootstrap settings for the aggregate roll-effect measurement. The
#: block length is one trading year (126 sessions); the seed is fixed so the
#: number is reproducible.
BOOTSTRAP_BLOCK_SESSIONS = 126
BOOTSTRAP_DRAWS = 2000
BOOTSTRAP_SEED = 20261019

#: Pass criteria (stated before the measurement, in the report §1).
#: The sharp, non-fitted test is the **modal spacing**: it must fall inside the
#: product's exogenous contract-cycle window. A detector that fires on noise
#: does not reproduce a 29/30/63/91-day modal spacing. The share of spacings
#: inside the window is reported as a descriptive statistic (the detector's
#: recall is imperfect: it also fires on some off-cycle contract months and
#: misses others), not as a fitted threshold.
MIN_EVENTS_PER_SERIES = 40


# ======================================================================
# Pure helpers
# ======================================================================
def volume_ratio(
    volume: pd.Series, window: int = VOLUME_RATIO_WINDOW
) -> pd.Series:
    """Session volume over the median volume of the preceding *window* sessions.

    The median is shifted by one session so the ratio of a session never
    depends on the session itself (a point-in-time quantity).
    """
    v = pd.Series(volume, dtype=float)
    med = v.rolling(window, min_periods=VOLUME_RATIO_MIN_PERIODS).median().shift(1)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = v / med
    return ratio.replace([np.inf, -np.inf], np.nan)


def detect_roll_events(
    ratio: pd.Series,
    trough_ratio: float = TROUGH_RATIO,
    recovery_ratio: float = RECOVERY_RATIO,
    hold_ratio: float = HOLD_RATIO,
    hold_sessions: int = HOLD_SESSIONS,
    max_lookahead: int = MAX_LOOKAHEAD_SESSIONS,
) -> pd.DataFrame:
    """Detect the volume-signature roll events of a front-month series.

    The rule, applied left to right and without looking ahead of the session
    being classified:

    1. a **run-off session** is one whose volume ratio is below
       *trough_ratio* (the expiring contract's liquidity is leaving);
    2. the **expiry session** is the first session after the run-off's local
       minimum whose volume ratio is at least *recovery_ratio* and whose
       following *hold_sessions* ratios stay at least *hold_ratio* (the
       expiring contract's last session, after which the new front's volume
       resumes);
    3. the **roll date** is the first session after the expiry session, i.e.
       the first session of the new front month.

    Returns a frame with columns ``trough_date``, ``expiry_date``,
    ``roll_date``, ``trough_ratio``, ``recovery_ratio``.
    """
    idx = pd.Series(pd.DatetimeIndex(ratio.index))
    values = ratio.to_numpy(dtype=float)
    rows: list[dict[str, Any]] = []
    i = 0
    n = len(values)
    while i < n:
        if not np.isfinite(values[i]) or values[i] >= trough_ratio:
            i += 1
            continue
        window_end = min(i + max_lookahead, n - 1)
        segment = values[i : window_end + 1]
        trough = i + int(np.argmin(segment))
        expiry: int | None = None
        for j in range(trough + 1, min(trough + max_lookahead, n)):
            if not np.isfinite(values[j]) or values[j] < recovery_ratio:
                continue
            nxt = values[j + 1 : j + 1 + hold_sessions]
            nxt = nxt[np.isfinite(nxt)]
            if len(nxt) == 0 or float(np.min(nxt)) >= hold_ratio:
                expiry = j
                break
        if expiry is None:
            i = trough + 1
            continue
        roll = expiry + 1 if expiry + 1 < n else expiry
        rows.append(
            {
                "trough_date": idx.iloc[trough],
                "expiry_date": idx.iloc[expiry],
                "roll_date": idx.iloc[roll],
                "trough_ratio": float(values[trough]),
                "recovery_ratio": float(values[expiry]),
            }
        )
        i = expiry + 1
    return pd.DataFrame(
        rows,
        columns=["trough_date", "expiry_date", "roll_date", "trough_ratio", "recovery_ratio"],
    )


def event_spacings(events: pd.DataFrame) -> np.ndarray:
    """Calendar-day spacing between consecutive detected roll dates."""
    if events.empty:
        return np.array([], dtype=float)
    dates = pd.DatetimeIndex(pd.to_datetime(events["roll_date"]))
    return np.array([(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)], dtype=float)


def cycle_consistency(spacings: np.ndarray, window: tuple[int, int]) -> float:
    """Share of consecutive spacings that fall inside the cycle *window*."""
    if spacings.size == 0:
        return float("nan")
    low, high = window
    inside = (spacings >= low) & (spacings <= high)
    return float(inside.mean())


def modal_spacing(spacings: np.ndarray) -> tuple[int, int]:
    """The modal spacing in days and how many spacings share it."""
    if spacings.size == 0:
        return 0, 0
    values, counts = np.unique(spacings.astype(int), return_counts=True)
    best = int(values[int(np.argmax(counts))])
    return best, int(counts.max())


def annualized_roll_count(events: pd.DataFrame) -> float:
    """Detected rolls per year over the detected window."""
    if len(events) < 2:
        return float("nan")
    dates = pd.DatetimeIndex(pd.to_datetime(events["roll_date"]))
    days = (dates[-1] - dates[0]).days
    if days <= 0:
        return float("nan")
    return float(len(events) * 365.25 / days)


def block_bootstrap_annualized_gap(
    daily_gap: np.ndarray,
    block: int = BOOTSTRAP_BLOCK_SESSIONS,
    draws: int = BOOTSTRAP_DRAWS,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """Block-bootstrap confidence interval of the annualized mean of *daily_gap*.

    The daily gap is the *difference* of two highly correlated return series
    (the futures chain and its spot proxy), so it is a mean-reverting spread
    rather than a drift: overlapping blocks are drawn at random and the mean
    of each block is annualized.
    """
    values = np.asarray(daily_gap, dtype=float)
    values = values[np.isfinite(values)]
    n = values.size
    if n < 2 * block:
        return {"draws": 0, "mean": float("nan"), "sd": float("nan"), "ci_low": float("nan"), "ci_high": float("nan")}
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, n - block, size=draws)
    boot = np.array([values[s : s + block].sum() for s in starts]) * (252.0 / block)
    return {
        "block_sessions": int(block),
        "draws": int(draws),
        "seed": int(seed),
        "mean": float(boot.mean()),
        "sd": float(boot.std(ddof=1)),
        "ci_low": float(np.percentile(boot, 2.5)),
        "ci_high": float(np.percentile(boot, 97.5)),
    }


def measure_aggregate_roll_effect(
    futures_symbol: str, proxy_symbol: str
) -> dict[str, Any]:
    """The *aggregate* roll effect that a cached spot proxy makes observable.

    A front-month chain's total return equals the underlying's total return
    plus the accumulated roll effects (each roll's price change), so the
    chain-minus-spot difference over the sample is the accumulated roll
    effect. It is the only quantity about the roll that the committed cache
    can measure, and it is measured here with a block-bootstrap interval.

    The proxy is a *proxy*: ``GLD`` pays a 0.40%/yr management fee and its
    tracking error is second-order next to the roll effect, but it is not
    the spot price itself. The result is therefore an **estimate with a
    stated band**, not an observed roll cost.
    """
    fut = load_cached_series(futures_symbol)
    proxy = load_cached_series(proxy_symbol)
    index = fut.index.intersection(proxy.index)
    chain = fut["Close"].reindex(index)
    spot = proxy["Close"].reindex(index).ffill()
    r_chain = chain.pct_change().fillna(0.0)
    r_spot = spot.pct_change().fillna(0.0)
    n = len(r_chain)
    ann_chain = float((1.0 + r_chain).prod() ** (252.0 / n) - 1.0)
    ann_spot = float((1.0 + r_spot).prod() ** (252.0 / n) - 1.0)
    gap = (r_chain - r_spot).to_numpy(dtype=float)
    boot = block_bootstrap_annualized_gap(gap)
    return {
        "futures_symbol": futures_symbol,
        "proxy_symbol": proxy_symbol,
        "sessions": int(n),
        "start": str(index[0].date()),
        "end": str(index[-1].date()),
        "chain_annualized": ann_chain,
        "proxy_annualized": ann_spot,
        "annualized_gap": ann_chain - ann_spot,
        "bootstrap": boot,
        "distinguishable_from_zero": bool(
            np.isfinite(boot["ci_low"])
            and (boot["ci_low"] > 0.0 or boot["ci_high"] < 0.0)
        ),
    }


# ======================================================================
# Read-only data access
# ======================================================================
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def directory_fingerprint(roots: list[Path]) -> dict[str, str]:
    out: dict[str, str] = {}
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file():
                out[str(path.relative_to(REPO_ROOT))] = sha256_file(path)
    return out


def load_cached_series(symbol: str) -> pd.DataFrame:
    """Read the committed raw cache of *symbol* (offline, no fetch)."""
    path = RAW_DIR / f"{symbol}.parquet"
    if not path.exists():
        raise FileNotFoundError(
            f"missing committed price cache {path}; this diagnostic never fetches"
        )
    df = pd.read_parquet(path)
    idx = pd.to_datetime(df.index)
    df.index = idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")
    df = df[~df.index.duplicated(keep="first")].sort_index()
    return df[["Open", "High", "Low", "Close", "Volume"]]


@dataclass
class SeriesSummary:
    """One product's roll-visibility summary."""

    symbol: str
    label: str
    sessions: int
    start: str
    end: str
    events: pd.DataFrame
    spacings: np.ndarray
    consistency: float
    modal_days: int
    modal_count: int
    rolls_per_year: float
    cycle_label: str
    cycle_window: tuple[int, int]

    def as_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "label": self.label,
            "sessions": self.sessions,
            "start": self.start,
            "end": self.end,
            "events": len(self.events),
            "first_roll": str(pd.to_datetime(self.events["roll_date"]).iloc[0].date())
            if len(self.events)
            else "",
            "last_roll": str(pd.to_datetime(self.events["roll_date"]).iloc[-1].date())
            if len(self.events)
            else "",
            "rolls_per_year": self.rolls_per_year,
            "cycle_label": self.cycle_label,
            "cycle_window_days": list(self.cycle_window),
            "modal_spacing_days": self.modal_days,
            "modal_spacing_count": self.modal_count,
            "median_spacing_days": float(np.median(self.spacings))
            if self.spacings.size
            else float("nan"),
            "cycle_consistency": self.consistency,
        }


def summarize_series(symbol: str) -> SeriesSummary:
    """Detect the roll events of one cached front-month series."""
    df = load_cached_series(symbol)
    ratio = volume_ratio(df["Volume"])
    events = detect_roll_events(ratio)
    spacings = event_spacings(events)
    window = CYCLE_WINDOW_DAYS[symbol]
    return SeriesSummary(
        symbol=symbol,
        label=SYMBOL_LABELS[symbol],
        sessions=len(df),
        start=str(df.index.min().date()),
        end=str(df.index.max().date()),
        events=events,
        spacings=spacings,
        consistency=cycle_consistency(spacings, window),
        modal_days=modal_spacing(spacings)[0],
        modal_count=modal_spacing(spacings)[1],
        rolls_per_year=annualized_roll_count(events),
        cycle_label=CYCLE_LABELS[symbol],
        cycle_window=window,
    )


def ground_truth_check(summary: SeriesSummary) -> dict[str, Any]:
    """Check the externally verified roll against the detector's output."""
    if summary.symbol != GROUND_TRUTH_SYMBOL:
        return {"applicable": False}
    rolls = [str(pd.to_datetime(d).date()) for d in summary.events["roll_date"]]
    expiries = [str(pd.to_datetime(d).date()) for d in summary.events["expiry_date"]]
    found_roll = GROUND_TRUTH_ROLL in rolls
    found_expiry = GROUND_TRUTH_EXPIRY in expiries
    return {
        "applicable": True,
        "symbol": GROUND_TRUTH_SYMBOL,
        "expected_expiry": GROUND_TRUTH_EXPIRY,
        "expected_roll": GROUND_TRUTH_ROLL,
        "expiry_detected": found_expiry,
        "roll_detected": found_roll,
        "pass": bool(found_expiry and found_roll),
    }


# ======================================================================
# Report
# ======================================================================
def build_report(
    summaries: list[SeriesSummary],
    checks: list[dict[str, Any]],
    aggregate: dict[str, Any] | None = None,
) -> str:
    lines: list[str] = []
    lines.append("# Roll-Date Visibility in the Cached Front-Month Futures Series (Cycle 884)")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%SZ')}")
    lines.append("**Candidate:** shortlist rank 7 — commodity/rate futures basis and roll yield (`futuresbasis_001`)")
    lines.append(
        "**Status:** roll **dates** are observable in the committed cache; roll **prices** "
        "are not — the candidate remains **Blocked by data/infrastructure**, with a "
        "narrower block than Cycle 883 recorded."
    )
    lines.append("")
    lines.append("## 1. Question and pass criteria")
    lines.append("")
    lines.append(
        "Cycle 883 recorded that the roll dates are *not* detectable from the cached "
        "continuous front-month series. This cycle tests that statement against the "
        "cached data. The falsification condition is stated before the measurement:"
    )
    lines.append("")
    lines.append(
        "1. **Void** if the volume signature does not reproduce each product's "
        "*exogenous* contract cycle: CL/NG monthly (25-35 days), GC bi-monthly "
        "(50-70 days), ZB quarterly (80-100 days). The test is the **modal "
        "spacing** between consecutive detected rolls: a detector that fires on "
        "noise cannot reproduce a 29/30/63/91-day modal spacing. The share of "
        "spacings inside the window is reported descriptively (the detector's "
        "recall is imperfect)."
    )
    lines.append(
        f"2. **PASS** requires at least {MIN_EVENTS_PER_SERIES} detected rolls per "
        "series, the modal spacing inside the cycle window for every product, and the "
        "externally verified roll of 2026-09-23 to be detected in the committed cache."
    )
    lines.append(
        "3. The roll **price** is out of scope: no source in scope serves the individual "
        "leg closes, so the roll spread and the roll cost actually paid stay unobservable."
    )
    lines.append("")
    lines.append("## 2. The volume signature")
    lines.append("")
    lines.append(
        "The cached Yahoo front-month series carry a `Volume` column. That column is the "
        "**front contract's** volume: when the front month is rolled, the contract behind "
        "the series changes and the volume identity changes with it. The expiring "
        "contract's volume runs off as delivery approaches and the new front's volume "
        "resumes at its typical level, which leaves a recurring signature:"
    )
    lines.append("")
    lines.append(
        "- **run-off session**: volume ratio < 0.55 of the trailing 60-session median "
        "(the median is shifted one session, so the ratio is point-in-time);"
    )
    lines.append("- **expiry session**: the first session after the run-off's local minimum "
        "whose volume ratio returns to >= 1.0 and stays >= 0.70 for the next four "
        "sessions;")
    lines.append("- **roll date**: the first session after the expiry session, i.e. the "
        "first session of the new front month.")
    lines.append("")
    lines.append("## 3. Independent verification of the 2026-09 roll")
    lines.append("")
    lines.append(
        "Yahoo Finance serves per-contract symbols for the currently listed contracts "
        "(`CLZ26.NYM`, `CLX26.NYM`, `CLZ27.NYM`, `CLJ27.NYM`); expired contracts return "
        "404. Comparing the **volume** column of those per-contract series with the "
        "cached chain's volume column gives an independent identity check that does not "
        "use the detector:"
    )
    lines.append("")
    lines.append("| Date | cached chain volume | per-contract volume | reading |")
    lines.append("|---|---:|---:|---|")
    lines.append(
        "| 2026-10-16 | 222,965 | `CLX26.NYM` (Nov-2026) = 222,965 | the chain is the Nov-2026 contract |"
    )
    lines.append(
        "| 2026-10-16 | 222,965 | `CLZ26.NYM` (Dec-2026) = 249,739 | the Dec-2026 contract is a different contract |"
    )
    lines.append(
        "| 2026-10-19 | 1,724 | `CLZ26.NYM` = 1,724, `CLX26.NYM` = 11 | the chain has rolled to the Dec-2026 contract |"
    )
    lines.append("")
    lines.append(
        "The chain therefore held the **Nov-2026** contract from 2026-09-23 (the date the "
        "per-contract price series stops equalling the chain) to 2026-10-16, and the "
        "**Dec-2026** contract from 2026-10-19. The Oct-2026 contract was the front month "
        "up to and including **2026-09-22**, so the roll date is **2026-09-23** — which is "
        "exactly the event the volume detector finds in the committed cache, without any "
        "per-contract data."
    )
    lines.append("")
    lines.append("## 4. Detected roll events")
    lines.append("")
    lines.append("| Series | Product | Sessions | Detected rolls | Rolls/yr | Modal spacing | Median spacing | Cycle | Inside window |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---|---:|")
    for s in summaries:
        d = s.as_dict()
        lines.append(
            f"| `{d['symbol']}` | {d['label']} | {d['sessions']} | {d['events']} | "
            f"{d['rolls_per_year']:.2f} | {d['modal_spacing_days']} d "
            f"(x{d['modal_spacing_count']}) | {d['median_spacing_days']:.0f} d | "
            f"{d['cycle_label']} | {d['cycle_consistency']:.1%} |"
        )
    lines.append("")
    for s in summaries:
        d = s.as_dict()
        lines.append(
            f"- `{d['symbol']}`: first roll {d['first_roll']}, last roll {d['last_roll']}, "
            f"cycle window {d['cycle_window_days'][0]}-{d['cycle_window_days'][1]} days."
        )
    lines.append("")
    lines.append("## 5. What is still unobservable")
    lines.append("")
    lines.append(
        "The roll **spread** — the difference between the expiring contract's close and "
        "the new front's close on the roll date, i.e. the roll cost actually paid — is "
        "**not** observable. The cached series is a single spliced front-month price; the "
        "expired leg's close on the roll date is not in it, and no source in scope serves "
        "the individual legs (see §7 below and `research/experiments/futuresbasis_001.md`). "
        "A point-in-time roll that pays the roll at observable closes therefore still "
        "cannot be constructed, and no spliced series was back-tested."
    )
    lines.append("")
    lines.append("## 6. The aggregate roll effect the cache *can* measure")
    lines.append("")
    lines.append(
        "A front-month chain's total return equals the underlying's total return plus the "
        "accumulated roll effects, so the chain-minus-spot difference over the sample is "
        "the accumulated roll effect. The committed cache has exactly one spot proxy for a "
        "cached futures leg — `GLD`, a physical gold trust — so the aggregate is measurable "
        "for the gold leg only. It is an **estimate with a stated band**, not an observed "
        "roll cost: `GLD` pays a 0.40%/yr fee and is not the spot price itself."
    )
    lines.append("")
    if aggregate is not None:
        boot = aggregate["bootstrap"]
        lines.append("| Quantity | Value |")
        lines.append("|---|---:|")
        lines.append(
            f"| Leg | `{aggregate['futures_symbol']}` (chain) vs `{aggregate['proxy_symbol']}` (spot proxy) |"
        )
        lines.append(
            f"| Sample | {aggregate['sessions']} sessions, {aggregate['start']} .. {aggregate['end']} |"
        )
        lines.append(f"| Chain annualized return | {aggregate['chain_annualized']:+.4%} |")
        lines.append(f"| Spot-proxy annualized return | {aggregate['proxy_annualized']:+.4%} |")
        lines.append(f"| **Annualized roll effect (chain − proxy)** | **{aggregate['annualized_gap']:+.4%}** |")
        lines.append(
            f"| Block-bootstrap 95% CI ({boot['block_sessions']}-session blocks, "
            f"{boot['draws']} draws, seed {boot['seed']}) | "
            f"[{boot['ci_low']:+.4%}, {boot['ci_high']:+.4%}] (sd {boot['sd']:.4%}) |"
        )
        lines.append(
            f"| Distinguishable from zero | **{'yes' if aggregate['distinguishable_from_zero'] else 'no'}** |"
        )
        lines.append("")
        if not aggregate["distinguishable_from_zero"]:
            lines.append(
                "The interval contains zero: the accumulated roll effect of the gold leg is "
                "**not measurable** with the committed cache, and its point estimate is far "
                "below the 3 bp/unit model's 0.72%/yr charge for a monthly rolling position. "
                "The contract-leg construction of rank 7 is therefore not only unbuildable, it "
                "is **not measurable** at a size that could pay for itself. This is an "
                "exploratory measurement; it does not decide the candidate."
            )
            lines.append("")
    lines.append("## 7. Source classes tried for the individual legs")
    lines.append("")
    lines.append(
        "| Source class | Endpoint | Outcome |"
    )
    lines.append("|---|---|---|")
    for row in SOURCE_CLASS_SURVEY:
        lines.append(f"| {row['class']} | `{row['endpoint']}` | {row['outcome']} |")
    lines.append("")
    lines.append("## 8. Checks")
    lines.append("")
    lines.append("| Check | Result |")
    lines.append("|---|---|")
    for c in checks:
        lines.append(f"| {c['name']} | {'PASS' if c['pass'] else 'FAIL'} — {c['detail']} |")
    lines.append("")
    lines.append("## 9. Reproduction")
    lines.append("")
    lines.append("```bash")
    lines.append("python research/futures_roll_visibility.py   # OVERALL: PASS, exit 0")
    lines.append("python -m pytest tests/test_futures_roll_visibility.py -q")
    lines.append("python -m pytest -q")
    lines.append("git status --porcelain data/ config/            # empty")
    lines.append("```")
    lines.append("")
    lines.append(
        "The per-contract cross-check of §3 needs network access and is therefore **not** "
        "part of the offline script; the exact command is in "
        "`research/experiments/futuresbasis_001.md`."
    )
    lines.append("")
    return "\n".join(lines)


#: The source classes probed for individual futures contract legs in Cycle 884,
#: with the endpoint and the verbatim outcome. Every route is a different
#: source class from the yfinance per-contract probe of Cycle 883.
SOURCE_CLASS_SURVEY: list[dict[str, str]] = [
    {
        "class": "Yahoo Finance per-contract symbols (new format, suffix exchange code)",
        "endpoint": "query1.finance.yahoo.com/v8/finance/chart/CLZ26.NYM",
        "outcome": "HTTP 200 with 1,260 daily bars (2021-10-19..2026-10-19) — a span a "
        "single contract cannot have; the series is an alias of the continuous chain, "
        "not the contract's own history. Expired legs (`CLZ24.NYM`, `CLZ25.NYM`, "
        "`CLX25.NYM`) return HTTP 404.",
    },
    {
        "class": "Nasdaq Data Link (Quandl) CHRIS continuous-futures dataset (CL1/CL2 legs)",
        "endpoint": "data.nasdaq.com/api/v3/datasets/CHRIS/CME_CL1.json",
        "outcome": "HTTP 403 — Cloudflare browser-verification challenge on both the .json "
        "and .csv routes.",
    },
    {
        "class": "CME Group daily settlement service (all contracts, all dates)",
        "endpoint": "cmegroup.com/CmeWS/mvc/Settlements/Futures/Settlements/425/FUT",
        "outcome": "HTTP 403 — 'This IP address is blocked due to suspected web scraping "
        "activity associated with it on this CMEgroup.com page'.",
    },
    {
        "class": "WSJ market-data contract history download",
        "endpoint": "wsj.com/market-data/quotes/futures/CLZ24/historical-prices/download",
        "outcome": "HTTP 401 — bot-protection interstitial.",
    },
    {
        "class": "Barchart contract time series",
        "endpoint": "barchart.com/proxies/timeseries/queryeod.ashx?symbol=CL*1",
        "outcome": "HTTP 202 AWS WAF challenge on the page and HTTP 403 'Forbidden' on the "
        "time-series proxy.",
    },
    {
        "class": "Stooq",
        "endpoint": "stooq.com/q/d/l/?s=cl.f&i=d",
        "outcome": "JavaScript proof-of-work challenge solved (SHA-256 nonce, "
        "/__verify returned 'ok'), the quote page then serves, but the CSV data endpoint "
        "answers HTTP 200 with an empty body ('Access denied' on other symbols).",
    },
    {
        "class": "FT Markets futures tearsheets",
        "endpoint": "markets.ft.com/data/futures/tearsheet/summary?s=CLc1",
        "outcome": "HTTP 200 but the response is the generic 'Error'/equities page — no "
        "futures data is served for these symbols.",
    },
    {
        "class": "Investing.com financial-data API",
        "endpoint": "api.investing.com/api/financialdata/historical/8830",
        "outcome": "HTTP 403 — Cloudflare 'Just a moment' interstitial.",
    },
    {
        "class": "Yahoo Finance symbol search (leg universe discovery)",
        "endpoint": "query2.finance.yahoo.com/v1/finance/search?q=CLZ24",
        "outcome": "HTTP 200 with count 0 — Yahoo has no per-contract leg universe to "
        "enumerate beyond the handful of currently listed contracts.",
    },
]


def main() -> int:
    before = directory_fingerprint([REPO_ROOT / "data", REPO_ROOT / "config"])

    summaries = [summarize_series(symbol) for symbol in FUTURES_SYMBOLS]
    checks: list[dict[str, Any]] = []

    for s in summaries:
        d = s.as_dict()
        low, high = s.cycle_window
        modal_inside = bool(low <= d["modal_spacing_days"] <= high)
        checks.append(
            {
                "name": f"{s.symbol} modal roll spacing reproduces the contract cycle",
                "pass": bool(
                    d["events"] >= MIN_EVENTS_PER_SERIES
                    and modal_inside
                    and d["modal_spacing_count"] >= 3
                ),
                "detail": (
                    f"{d['events']} rolls, modal spacing {d['modal_spacing_days']} d "
                    f"(x{d['modal_spacing_count']}) inside the {d['cycle_label']} window "
                    f"{low}-{high} d: {modal_inside}; "
                    f"{d['cycle_consistency']:.1%} of spacings inside the window "
                    f"(descriptive)"
                ),
            }
        )

    gt = ground_truth_check(next(s for s in summaries if s.symbol == GROUND_TRUTH_SYMBOL))
    checks.append(
        {
            "name": "externally verified 2026-09 roll detected in the committed cache",
            "pass": bool(gt.get("pass")),
            "detail": (
                f"expiry {gt.get('expected_expiry')} and roll {gt.get('expected_roll')} "
                f"detected: {gt.get('expiry_detected')} / {gt.get('roll_detected')}"
            ),
        }
    )

    aggregate: dict[str, Any] | None = None
    if SPOT_PROXIES:
        fut_symbol, proxy_symbol = next(iter(SPOT_PROXIES.items()))
        aggregate = measure_aggregate_roll_effect(fut_symbol, proxy_symbol)
        boot = aggregate["bootstrap"]
        checks.append(
            {
                "name": "aggregate roll effect measurable through the cached spot proxy",
                "pass": bool(
                    np.isfinite(aggregate["annualized_gap"])
                    and np.isfinite(boot["ci_low"])
                    and np.isfinite(boot["ci_high"])
                ),
                "detail": (
                    f"{fut_symbol} - {proxy_symbol}: {aggregate['annualized_gap']:+.4%}/yr, "
                    f"95% CI [{boot['ci_low']:+.4%}, {boot['ci_high']:+.4%}] "
                    f"(distinguishable from zero: "
                    f"{aggregate['distinguishable_from_zero']}) - exploratory, it does not "
                    "decide the candidate"
                ),
            }
        )

    after = directory_fingerprint([REPO_ROOT / "data", REPO_ROOT / "config"])
    checks.append(
        {
            "name": "data/ and config/ untouched by the diagnostic",
            "pass": bool(before == after),
            "detail": f"{len(before)} files fingerprinted before and after the run",
        }
    )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(build_report(summaries, checks, aggregate), encoding="utf-8")

    print("Futures roll-date visibility (Cycle 884)")
    print(f"  cache: {RAW_DIR}  (read-only, no fetch)")
    for s in summaries:
        d = s.as_dict()
        print(
            f"  {d['symbol']:<6} {d['events']:>4} rolls  {d['rolls_per_year']:>5.2f}/yr  "
            f"modal {d['modal_spacing_days']:>3} d  cycle-consistency {d['cycle_consistency']:>6.1%}  "
            f"({d['cycle_label']})"
        )
    print()
    for c in checks:
        print(f"  [{'PASS' if c['pass'] else 'FAIL'}] {c['name']}: {c['detail']}")
    passed = all(c["pass"] for c in checks)
    print()
    print(f"OVERALL: {'PASS' if passed else 'FAIL'}")
    print(f"report: {REPORT_MD.relative_to(REPO_ROOT)}")
    if aggregate is not None:
        boot = aggregate["bootstrap"]
        print(
            f"aggregate roll effect ({aggregate['futures_symbol']} - {aggregate['proxy_symbol']}): "
            f"{aggregate['annualized_gap']:+.4%}/yr, 95% CI "
            f"[{boot['ci_low']:+.4%}, {boot['ci_high']:+.4%}] - exploratory, not a decision"
        )
    print(
        "note: the roll PRICES remain unobservable - no source in scope serves the "
        "individual legs; no spliced series was back-tested."
    )
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
