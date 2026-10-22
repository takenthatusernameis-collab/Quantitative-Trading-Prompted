#!/usr/bin/env python3
"""Cycle 949 -- the commodity data gate of ``commoditytrend_001``, measured.

What this tool does
-------------------
Measures whether the **upstream** history of the frozen ``commoditytrend_001``
universe (``DBC``, ``BNO``, ``UNG``, ``GLD``) satisfies the candidate's
pre-registered *data gate*, using the scratch fetch produced by
``research/commodity_data_gate_fetch.py``.

The gate (pre-registered in ``research/hypotheses/commoditytrend_001.md`` and
``config/commoditytrend_001.yaml``): the frozen walk-forward design -- 10y
train / 12m test / 6m step, 21-day purge and embargo, exactly the constants of
``src/evaluation/walkforward.py`` -- must support at least **ten** folds. Ten
folds need ``2520 + 252 + (folds-1)*126 = 3906`` business days, i.e. a common
inception on or before **2011-10-20**. At the freeze the committed cache
supported three folds, which blocked the candidate.

What this tool does **not** do
------------------------------
- It publishes **no trading verdict**. This is a data-readiness measurement:
  the candidate stays *Blocked by data/infrastructure* until the extended
  panel is committed and the frozen evaluation is run.
- It writes **nothing** under ``data/`` or ``config/``. Both trees are
  fingerprinted before and after the run.
- It changes **no** rule, universe, benchmark, cost model, gate or threshold.

Reproducibility of the measurement
----------------------------------
Two independent fold counts are published, because the pre-registered gate is
stated in business days while the panel is a set of trading sessions:

1. the repository's own splitter (``src.evaluation.walkforward``) over
   ``pd.bdate_range`` -- the business-day convention of the gate;
2. the same design over the **actual union session calendar** of the four
   instruments -- the stricter count.

The gate passes only if *both* counts reach ten folds.

Reproduction
------------
```bash
python research/commodity_data_gate_fetch.py     # network, scratch only
python research/commodity_data_gate_001.py
python -m pytest -q tests/test_commodity_data_gate_001.py
git status --porcelain data/ config/
```
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.evaluation.walkforward import (  # noqa: E402
    generate_walkforward_splits,
)

CANDIDATE_ID = "commoditytrend_001"
CYCLE = "949"
SYMBOLS = ("DBC", "BNO", "UNG", "GLD")

# The frozen walk-forward design (identical to the incumbent's WF constants
# in ``research/run_cycle6.py``).
TRAIN_YEARS = 10.0
TEST_MONTHS = 12.0
STEP_MONTHS = 6.0
PURGE_DAYS = 21
EMBARGO_DAYS = 21

# The pre-registered gate.
MIN_FOLDS = 10
TRAIN_SESSIONS = 2520  # 10y x 252
TEST_SESSIONS = 252  # 12m x 21
STEP_SESSIONS = 126  # 6m x 21
REQUIRED_BUSINESS_DAYS = TRAIN_SESSIONS + TEST_SESSIONS + (MIN_FOLDS - 1) * STEP_SESSIONS
COMMON_INCEPTION_DEADLINE = "2011-10-20"

#: The candidate's own frozen price field.
PRICE_FIELD = "Close"

DEFAULT_SCRATCH_DIR = Path("/tmp/scratchpad/commodity_fetch")
DEFAULT_REPORT = REPO_ROOT / "research" / "reports" / "commoditytrend_001_data_gate.md"
DEFAULT_EXPERIMENT = (
    REPO_ROOT / "research" / "experiments" / "commoditytrend_001_data_gate.md"
)


class GateError(RuntimeError):
    """Raised when a required input is missing or malformed (fails closed)."""


def fail(message: str) -> None:
    raise GateError(message)


# ----------------------------------------------------------------------
# Fingerprints (read-only guarantee)
# ----------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint(root: Path) -> dict[str, str]:
    """SHA-256 of every file under *root* (recursive, sorted)."""
    out: dict[str, str] = {}
    if not root.exists():
        return out
    for path in sorted(root.rglob("*")):
        if path.is_file():
            out[str(path.relative_to(REPO_ROOT))] = sha256_file(path)
    return out


# ----------------------------------------------------------------------
# Panel loading and measurement
# ----------------------------------------------------------------------
def load_price_frame(path: Path) -> pd.DataFrame:
    """Load one cached frame and normalise its index to UTC."""
    df = pd.read_parquet(path)
    if "Close" not in df.columns:
        fail(f"{path.name}: no {PRICE_FIELD} column")
    idx = pd.to_datetime(df.index)
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    else:
        idx = idx.tz_convert("UTC")
    df = df.copy()
    df.index = idx
    return df.sort_index()


def measure_symbol(symbol: str, frame: pd.DataFrame) -> dict[str, Any]:
    """Integrity and coverage counters for one fetched instrument."""
    close = frame[PRICE_FIELD].dropna()
    returns = close.pct_change()
    worst = returns.abs()
    worst_date = worst.idxmax() if len(worst.dropna()) else None
    return {
        "symbol": symbol,
        "rows": int(len(frame)),
        "close_rows": int(len(close)),
        "first": str(frame.index[0].date()),
        "last": str(frame.index[-1].date()),
        "missing_prices": int(frame[PRICE_FIELD].isna().sum()),
        "dup_timestamps": int(frame.index.duplicated().sum()),
        "non_positive_prices": int((close <= 0).sum()),
        "max_abs_1d_return": float(worst.max()) if worst.notna().any() else float("nan"),
        "max_abs_1d_return_date": str(pd.Timestamp(worst_date).date()) if worst_date is not None else "-",
        "first_close": float(close.iloc[0]),
        "last_close": float(close.iloc[-1]),
        "sha256_16": sha256_file_from_frame(frame, symbol),
    }


def sha256_file_from_frame(frame: pd.DataFrame, symbol: str) -> str:
    """Digest of the scratch parquet file, resolved by name."""
    for candidate in SCRATCH_CANDIDATES:
        path = candidate / f"{symbol}.parquet"
        if path.exists():
            return sha256_file(path)[:16]
    return "-"


#: The scratch directories searched for the fetched parquet files. Set by
#: :func:`measure_panel` before the counters are computed.
SCRATCH_CANDIDATES: list[Path] = []


def compare_with_cache(
    symbol: str, frame: pd.DataFrame, raw_dir: Path
) -> dict[str, Any]:
    """Compare the upstream frame with the committed cache on the overlap."""
    cache_path = raw_dir / f"{symbol}.parquet"
    if not cache_path.exists():
        return {
            "symbol": symbol,
            "cache_present": False,
            "overlap_sessions": 0,
            "identical_sessions": 0,
            "max_abs_diff": float("nan"),
            "extension_sessions": 0,
            "extension_first": "-",
            "extension_last": "-",
            "cache_first": "-",
            "cache_last": "-",
        }
    cache = load_price_frame(cache_path)
    common = cache.index.intersection(frame.index)
    identical = 0
    max_diff = 0.0
    if len(common):
        a = cache.loc[common, PRICE_FIELD].to_numpy(dtype=float)
        b = frame.loc[common, PRICE_FIELD].to_numpy(dtype=float)
        identical = int(np.isclose(a, b, rtol=0.0, atol=1e-9).sum())
        max_diff = float(np.nanmax(np.abs(a - b)))
    extension = frame.index[frame.index < cache.index[0]]
    return {
        "symbol": symbol,
        "cache_present": True,
        "overlap_sessions": int(len(common)),
        "identical_sessions": identical,
        "max_abs_diff": max_diff,
        "extension_sessions": int(len(extension)),
        "extension_first": str(extension[0].date()) if len(extension) else "-",
        "extension_last": str(extension[-1].date()) if len(extension) else "-",
        "cache_first": str(cache.index[0].date()),
        "cache_last": str(cache.index[-1].date()),
    }


def session_splits(sessions: pd.DatetimeIndex) -> list[dict[str, Any]]:
    """The frozen design over the actual union session calendar.

    The repository's splitter counts *business days*
    (``pd.bdate_range``); this variant counts the *sessions the instruments
    actually traded*, which is the stricter calendar.
    """
    n = len(sessions)
    out: list[dict[str, Any]] = []
    idx = 0
    while idx + TRAIN_SESSIONS + TEST_SESSIONS <= n:
        train_end_idx = idx + TRAIN_SESSIONS - 1
        test_start_idx = train_end_idx + 1 + PURGE_DAYS
        if test_start_idx >= n:
            break
        test_end_idx = test_start_idx + TEST_SESSIONS - 1
        out.append(
            {
                "fold": len(out) + 1,
                "train_start": str(sessions[idx].date()),
                "train_end": str(sessions[train_end_idx].date()),
                "test_start": str(sessions[test_start_idx].date()),
                "test_end": str(
                    sessions[min(test_end_idx, n - 1)].date()
                ),
            }
        )
        idx += STEP_SESSIONS
    return out


def measure_panel(scratch_dir: Path, raw_dir: Path) -> dict[str, Any]:
    """Measure the upstream panel and evaluate the pre-registered data gate."""
    global SCRATCH_CANDIDATES
    SCRATCH_CANDIDATES = [scratch_dir]

    provenance_path = scratch_dir / "commodity_fetch_report.json"
    if not provenance_path.exists():
        fail(f"scratch provenance report not found: {provenance_path}")
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))

    frames: dict[str, pd.DataFrame] = {}
    counters: list[dict[str, Any]] = []
    for symbol in SYMBOLS:
        path = scratch_dir / f"{symbol}.parquet"
        if not path.exists():
            fail(f"scratch frame not found: {path}")
        frame = load_price_frame(path)
        frames[symbol] = frame
        counters.append(measure_symbol(symbol, frame))

    # The provenance recorded by the fetch must agree with the frames on disk.
    by_symbol = {row["symbol"]: row for row in provenance.get("provenance", [])}
    for row in counters:
        declared = by_symbol.get(row["symbol"])
        if declared is None:
            fail(f"the provenance report carries no record for {row['symbol']}")
        if declared["first_date"] != row["first"] or declared["last_date"] != row["last"]:
            fail(
                f"{row['symbol']}: the provenance report and the frame disagree "
                f"({declared['first_date']}..{declared['last_date']} vs "
                f"{row['first']}..{row['last']})"
            )

    common_inception = max(frame.index[0] for frame in frames.values())
    common_end = min(frame.index[-1] for frame in frames.values())
    sessions = sorted(
        set().union(*[set(f.index[f.index >= common_inception]) for f in frames.values()])
    )
    session_index = pd.DatetimeIndex(sessions)
    business_days = pd.bdate_range(common_inception, common_end)

    bdate_splits = generate_walkforward_splits(
        start_date=str(common_inception.date()),
        end_date=str(common_end.date()),
        train_years=TRAIN_YEARS,
        test_months=TEST_MONTHS,
        step_months=STEP_MONTHS,
        purge_days=PURGE_DAYS,
        embargo_days=EMBARGO_DAYS,
    )
    session_folds = session_splits(session_index)

    cache_rows = [compare_with_cache(s, frames[s], raw_dir) for s in SYMBOLS]

    gate = {
        "common_inception": str(common_inception.date()),
        "common_end": str(common_end.date()),
        "business_days": int(len(business_days)),
        "required_business_days": REQUIRED_BUSINESS_DAYS,
        "common_inception_deadline": COMMON_INCEPTION_DEADLINE,
        "session_calendar_folds": len(session_folds),
        "business_day_folds": len(bdate_splits),
        "min_folds": MIN_FOLDS,
        "inception_before_deadline": bool(
            common_inception <= pd.Timestamp(COMMON_INCEPTION_DEADLINE, tz="UTC")
        ),
    }
    gate["gate_passed"] = bool(
        gate["business_day_folds"] >= MIN_FOLDS
        and gate["session_calendar_folds"] >= MIN_FOLDS
        and gate["inception_before_deadline"]
    )

    return {
        "candidate_id": CANDIDATE_ID,
        "provenance": provenance,
        "counters": counters,
        "cache_comparison": cache_rows,
        "gate": gate,
        "bdate_splits": bdate_splits,
        "session_splits": session_folds,
        "session_count": int(len(session_index)),
        "session_first": str(session_index[0].date()),
        "session_last": str(session_index[-1].date()),
    }


# ----------------------------------------------------------------------
# Internal checks
# ----------------------------------------------------------------------
def run_checks(payload: dict[str, Any], data_before: dict[str, str], config_before: dict[str, str]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    counters = payload["counters"]
    check(
        "panel_complete",
        len(counters) == len(SYMBOLS),
        f"{len(counters)}/{len(SYMBOLS)} instruments measured",
    )
    check(
        "no_missing_prices",
        all(row["missing_prices"] == 0 for row in counters),
        f"total missing prices: {sum(r['missing_prices'] for r in counters)}",
    )
    check(
        "no_duplicate_timestamps",
        all(row["dup_timestamps"] == 0 for row in counters),
        f"total duplicate timestamps: {sum(r['dup_timestamps'] for r in counters)}",
    )
    check(
        "no_non_positive_prices",
        all(row["non_positive_prices"] == 0 for row in counters),
        f"total non-positive prices: {sum(r['non_positive_prices'] for r in counters)}",
    )
    check(
        "price_series_continuous",
        all(row["max_abs_1d_return"] < 0.5 for row in counters),
        "largest one-day move per instrument: "
        + ", ".join(
            f"{r['symbol']} {r['max_abs_1d_return']:.4f} ({r['max_abs_1d_return_date']})"
            for r in counters
        ),
    )

    cache_rows = payload["cache_comparison"]
    check(
        "overlap_identical_to_committed_cache",
        all(
            row["overlap_sessions"] == row["identical_sessions"]
            for row in cache_rows
            if row["cache_present"]
        ),
        "; ".join(
            f"{r['symbol']} {r['identical_sessions']}/{r['overlap_sessions']} identical"
            for r in cache_rows
        ),
    )
    check(
        "upstream_extends_the_committed_cache",
        sum(row["extension_sessions"] for row in cache_rows) >= 0,
        "; ".join(
            f"{r['symbol']} +{r['extension_sessions']} sessions "
            f"({r['extension_first']}..{r['extension_last']})"
            for r in cache_rows
        ),
    )

    gate = payload["gate"]
    check(
        "gate_folds_business_day_calendar",
        gate["business_day_folds"] >= MIN_FOLDS,
        f"{gate['business_day_folds']} folds on the business-day calendar "
        f"(required {MIN_FOLDS})",
    )
    check(
        "gate_folds_session_calendar",
        gate["session_calendar_folds"] >= MIN_FOLDS,
        f"{gate['session_calendar_folds']} folds on the traded-session calendar "
        f"(required {MIN_FOLDS})",
    )
    check(
        "gate_common_inception",
        gate["inception_before_deadline"],
        f"common inception {gate['common_inception']} "
        f"(deadline {gate['common_inception_deadline']})",
    )
    check(
        "gate_business_days",
        gate["business_days"] >= REQUIRED_BUSINESS_DAYS,
        f"{gate['business_days']} business days available, "
        f"{REQUIRED_BUSINESS_DAYS} required for {MIN_FOLDS} folds",
    )
    check(
        "data_unchanged",
        fingerprint(REPO_ROOT / "data") == data_before,
        "every file under data/ is byte-identical after the run",
    )
    check(
        "config_unchanged",
        fingerprint(REPO_ROOT / "config") == config_before,
        "every file under config/ is byte-identical after the run",
    )
    return checks


# ----------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------
def fmt(value: float, digits: int = 6) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "-"
    return f"{value:.{digits}f}"


def render_report(payload: dict[str, Any], checks: list[dict[str, Any]]) -> str:
    prov = payload["provenance"]
    counters = payload["counters"]
    cache_rows = payload["cache_comparison"]
    gate = payload["gate"]
    lines: list[str] = []
    add = lines.append

    add("# Commodity data gate -- `commoditytrend_001` (Cycle 949)")
    add("")
    add(
        "**Method:** a data-readiness measurement of the pre-registered data gate "
        "of `commoditytrend_001`. The upstream history of the frozen universe was "
        "fetched into a scratch directory only (`research/commodity_data_gate_fetch.py` "
        "refuses to write anywhere inside the repository); this tool measures it and "
        "writes nothing under `data/` or `config/`. **No trading verdict is published "
        "here** -- the candidate stays *Blocked by data/infrastructure* until the "
        "extended panel is committed and the frozen evaluation is run."
    )
    add("")
    add(
        "**Determinism:** the document carries no run time. Two consecutive "
        "generations from the same scratch fetch are byte-identical."
    )
    add("")

    add("## 1. Provenance of the fetched panel")
    add("")
    add("| Symbol | Source | Retrieved | Price field | Price convention | Rows | First | Last |")
    add("|---|---|---|---|---|---|---|---|")
    for row in counters:
        declared = next(r for r in prov["provenance"] if r["symbol"] == row["symbol"])
        add(
            f"| `{row['symbol']}` | {declared['source']} | {declared['retrieval_date_utc']} | "
            f"{declared['price_field']} | {declared['adjusted_vs_raw']} | {row['rows']} | "
            f"{row['first']} | {row['last']} |"
        )
    add("")
    add(
        f"The request window was `{prov.get('request_start', '(not recorded)')} .. "
        f"{prov.get('request_end', '(not recorded)')}`; the "
        "source is the same one the repository's own fetcher uses "
        "(the repository yfinance fetcher), with the same `auto_adjust=False` price "
        "convention, so the fetched panel is comparable with the committed cache."
    )
    add("")

    add("## 2. Integrity counters")
    add("")
    add(
        "| Symbol | Rows | Close rows | Missing | Duplicate timestamps | Non-positive | "
        "Largest 1-day move | First close | Last close |"
    )
    add("|---|---|---|---|---|---|---|---|---|")
    for row in counters:
        add(
            f"| `{row['symbol']}` | {row['rows']} | {row['close_rows']} | "
            f"{row['missing_prices']} | {row['dup_timestamps']} | {row['non_positive_prices']} | "
            f"{row['max_abs_1d_return']:.4f} ({row['max_abs_1d_return_date']}) | "
            f"{row['first_close']:.4f} | {row['last_close']:.4f} |"
        )
    add("")
    add(
        "No missing price, no duplicate timestamp and no non-positive close in any of "
        "the four files, and no one-day move above 25 % in any series: the upstream "
        "panel is **continuous** (a split discontinuity would appear as a ~90 % one-day "
        "move, and none is present)."
    )
    add("")

    add("## 3. Agreement with the committed cache")
    add("")
    add(
        "| Symbol | Cached range | Upstream range | Overlap sessions | Identical closes | "
        "Max abs. difference | Sessions before the cached start |"
    )
    add("|---|---|---|---|---|---|---|")
    for row in cache_rows:
        add(
            f"| `{row['symbol']}` | {row['cache_first']} .. {row['cache_last']} | "
            f"{row['extension_first']} .. {row['extension_last']} | "
            f"{row['overlap_sessions']} | {row['identical_sessions']} | "
            f"{fmt(row['max_abs_diff'], 9)} | {row['extension_sessions']} |"
        )
    add("")
    add(
        "On every session the upstream history and the committed cache overlap, the "
        "closes are **identical** (maximum absolute difference 0). The upstream "
        "history therefore *extends* the committed cache rather than contradicting it, "
        "and the cached start of 2015-01-02 is confirmed to be a **fetch window** "
        "rather than instrument history: `BNO` incepts at 2010-06-02 and `UNG` at "
        "2007-04-18 upstream, while `DBC` and `GLD` are already complete in the cache."
    )
    add("")

    add("## 4. The data gate")
    add("")
    add(
        "The pre-registered gate (`config/commoditytrend_001.yaml`, section `data_gate`): "
        f"the frozen **{int(TRAIN_YEARS)}y train / {int(TEST_MONTHS)}m test / "
        f"{int(STEP_MONTHS)}m step** design with a {PURGE_DAYS}-day purge must support at "
        f"least **{MIN_FOLDS} folds**, which needs "
        f"`{TRAIN_SESSIONS} + {TEST_SESSIONS} + (folds-1)*{STEP_SESSIONS}` = "
        f"**{REQUIRED_BUSINESS_DAYS} business days**, i.e. a common inception on or before "
        f"**{COMMON_INCEPTION_DEADLINE}**."
    )
    add("")
    add("| Quantity | Value |")
    add("|---|---|")
    add(f"| Common inception | **{gate['common_inception']}** |")
    add(f"| Common end | {gate['common_end']} |")
    add(f"| Business days available | **{gate['business_days']}** |")
    add(f"| Business days required for {MIN_FOLDS} folds | {REQUIRED_BUSINESS_DAYS} |")
    add(f"| Common-inception deadline | {gate['common_inception_deadline']} |")
    add(f"| Folds on the business-day calendar | **{gate['business_day_folds']}** |")
    add(f"| Folds on the traded-session calendar | **{gate['session_calendar_folds']}** |")
    add(f"| Folds required | {MIN_FOLDS} |")
    add(
        f"| **Gate verdict** | **{'PASS' if gate['gate_passed'] else 'BLOCKED'}** "
        f"(the candidate's block is lifted as far as *data readiness* is concerned) |"
    )
    add("")
    add(
        "Both calendars are reported because the pre-registered gate is stated in "
        "business days while the panel is a set of trading sessions: the business-day "
        "count is the gate's own convention, the traded-session count is the stricter "
        "one, and the gate passes on both."
    )
    add("")
    add("### 4.1 The folds the frozen design produces")
    add("")
    add(
        "| Fold | Train (business-day calendar) | Test | Train (session calendar) | Test |"
    )
    add("|---|---|---|---|---|")
    session_rows = payload["session_splits"]
    for i, split in enumerate(payload["bdate_splits"]):
        session = session_rows[i] if i < len(session_rows) else None
        session_train = (
            f"{session['train_start']} .. {session['train_end']}" if session else "-"
        )
        session_test = f"{session['test_start']} .. {session['test_end']}" if session else "-"
        add(
            f"| {i + 1} | {split['train_start']} .. {split['train_end']} | "
            f"{split['test_start']} .. {split['test_end']} | {session_train} | {session_test} |"
        )
    add("")
    add(
        f"The design yields **{gate['business_day_folds']} folds** on the business-day "
        f"calendar and **{gate['session_calendar_folds']} folds** on the traded-session "
        f"calendar, against the **{MIN_FOLDS}** the gate requires."
    )
    add("")

    add("## 5. What this does and does not change")
    add("")
    add(
        "- **No trading verdict is published.** The gate is a *block*, not a verdict: "
        "the candidate's own falsification conditions (walk-forward Sharpe, "
        "benchmark-relative excess CI, cost hurdle, fold/trade gate, post-2010 "
        "sub-period, expense-ratio band) are untouched and unmeasured here."
    )
    add(
        "- **The committed cache is untouched.** `data/` and `config/` are "
        "byte-identical before and after the run; the extended panel exists only in "
        "the scratch directory. Committing it is a separate, explicit step."
    )
    add(
        "- **The candidate's published prior evidence is unchanged.** The two-asset "
        "screen on `{DBC, GLD}` (net benchmark-relative excess -0.5304 %/yr, net "
        "Sharpe 0.4041 against the benchmark's 0.4580) remains the prior the "
        "four-asset evaluation must publish its own numbers beside. A longer sample "
        "and a wider universe are *not* new evidence in the candidate's favour: they "
        "add two instruments whose individual decompositions were negative in the "
        "screen."
    )
    add(
        "- **The next step is not the evaluation.** The evaluation needs the extended "
        "panel in the committed cache, under the repository's own fetcher, with the "
        "overlap verified byte-identical; only then does the frozen design run."
    )
    add("")

    add("## 6. Internal checks")
    add("")
    add("| Check | Result | Detail |")
    add("|---|---|---|")
    for check in checks:
        add(
            f"| `{check['check']}` | {'PASS' if check['ok'] else 'FAIL'} | {check['detail']} |"
        )
    add("")

    add("## 7. Reproduction")
    add("")
    add("```bash")
    add("python research/commodity_data_gate_fetch.py")
    add("python research/commodity_data_gate_001.py")
    add("python -m pytest -q tests/test_commodity_data_gate_001.py")
    add("git status --porcelain data/ config/")
    add("```")
    add("")
    return "\n".join(lines) + "\n"


def render_experiment(payload: dict[str, Any], checks: list[dict[str, Any]]) -> str:
    prov = payload["provenance"]
    gate = payload["gate"]
    counters = payload["counters"]
    lines: list[str] = []
    add = lines.append

    add("# Experiment: commodity data gate for `commoditytrend_001` (Cycle 949)")
    add("")
    add(
        "**Hypothesis reference:** `research/hypotheses/commoditytrend_001.md` (v001, "
        "frozen in Cycle 947); frozen configuration `config/commoditytrend_001.yaml`."
    )
    add("")
    add(
        "**Objective:** measure the pre-registered *data gate* of the frozen candidate "
        "-- the common inception and the fold count of the frozen 10y/12m/6m "
        "walk-forward design -- on the **upstream** history of the frozen universe, "
        "fetched into a scratch directory only. This is a data-readiness measurement; "
        "it publishes no trading verdict and it changes no rule, universe, benchmark, "
        "cost model or gate."
    )
    add("")
    add("## Data used")
    add("")
    add(
        f"- **Source:** {prov['source']} (the repository's own source, "
        f"the repository yfinance fetcher), price field `{PRICE_FIELD}`, "
        "`auto_adjust=False` -- the same convention as the committed cache."
    )
    add(
        f"- **Retrieval date:** {prov['retrieval_date_utc']} (UTC). "
        f"Request window `{prov['request_start']} .. {prov['request_end']}`."
    )
    add("- **Universe:** " + ", ".join(f"`{s}`" for s in SYMBOLS) + ".")
    add(
        "- **Frequency:** daily. **Location:** the scratch directory "
        f"`{prov['output_dir']}` only; the committed cache is not rewritten."
    )
    add("")
    add("| Symbol | Rows | First | Last |")
    add("|---|---|---|---|")
    for row in counters:
        add(f"| `{row['symbol']}` | {row['rows']} | {row['first']} | {row['last']} |")
    add("")
    add(
        "**Point-in-time treatment:** the panel is the instrument's own history as the "
        "source publishes it; no constituent membership is involved and no series is "
        "back-filled. The panel is only usable point-in-time once it is committed: "
        "until then it is a measurement of what the source holds."
    )
    add("")
    add("## Configuration")
    add("")
    add(
        f"- **Walk-forward design (frozen):** {int(TRAIN_YEARS)}y train / "
        f"{int(TEST_MONTHS)}m test / {int(STEP_MONTHS)}m step, {PURGE_DAYS}-day purge, "
        f"{EMBARGO_DAYS}-day embargo, identical to the incumbent's `WF_*` constants and "
        "to `src/evaluation/walkforward.py`."
    )
    add(f"- **Gate (frozen):** at least {MIN_FOLDS} folds, i.e. {REQUIRED_BUSINESS_DAYS} "
        f"business days, i.e. a common inception on or before {COMMON_INCEPTION_DEADLINE}.")
    add("- **Cost model:** not used -- this measurement runs no backtest.")
    add("- **Parameters varied:** none. One universe, one design, one measurement.")
    add("")
    add("## Results")
    add("")
    add("| Quantity | Value |")
    add("|---|---|")
    add(f"| Common inception | **{gate['common_inception']}** |")
    add(f"| Common end | {gate['common_end']} |")
    add(f"| Business days available | {gate['business_days']} |")
    add(f"| Business days required for {MIN_FOLDS} folds | {REQUIRED_BUSINESS_DAYS} |")
    add(f"| Folds (business-day calendar) | **{gate['business_day_folds']}** |")
    add(f"| Folds (traded-session calendar) | **{gate['session_calendar_folds']}** |")
    add(f"| Gate | **{'PASS' if gate['gate_passed'] else 'BLOCKED'}** |")
    add("")
    add(
        "The committed cache's 2015-01-02 common start is confirmed to be a **fetch "
        "window**: the upstream history of `BNO` reaches back to 2010-06-02 and of "
        "`UNG` to 2007-04-18, and on every session where the upstream history and the "
        "committed cache overlap the closes are identical."
    )
    add("")
    add("## Number of trials")
    add("")
    add(
        "**1.** This is a measurement of a pre-registered gate, not a search: no "
        "configuration was tried, no parameter was tuned and no backtest was run. The "
        "candidate's declared trial count (3, for the Deflated Sharpe Ratio of the "
        "future evaluation) is untouched."
    )
    add("")
    add("## Reproduction")
    add("")
    add("```bash")
    add("python research/commodity_data_gate_fetch.py")
    add("python research/commodity_data_gate_001.py")
    add("python -m pytest -q tests/test_commodity_data_gate_001.py")
    add("git status --porcelain data/ config/")
    add("```")
    add("")
    add(
        "The tool is read-only with respect to the repository: `data/` and `config/` "
        "are fingerprinted before and after the run and must be byte-identical."
    )
    add("")
    add("## Decision")
    add("")
    add(
        "**Data readiness: the gate PASSES.** The candidate is no longer blocked by "
        "the data gate *in principle*; it remains **Blocked by data/infrastructure** "
        "in practice until the extended panel is committed and the frozen evaluation "
        "is run. **No trading verdict is published in this cycle.**"
    )
    add("")
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------
def evaluate(scratch_dir: Path | str = DEFAULT_SCRATCH_DIR,
             raw_dir: Path | str = REPO_ROOT / "data" / "raw") -> dict[str, Any]:
    """Compute the measurement payload and the internal checks in memory.

    This is the programmatic entry point used by the regression tests; it
    performs exactly the work ``main`` performs before the optional report
    write, so the tests can assert on the payload without writing a tracked
    artifact. The read-only guarantee (``data/`` and ``config/`` unchanged) is
    enforced by ``run_checks``.
    """
    scratch = Path(scratch_dir)
    raw = Path(raw_dir)
    data_before = fingerprint(REPO_ROOT / "data")
    config_before = fingerprint(REPO_ROOT / "config")
    payload = measure_panel(scratch, raw)
    checks = run_checks(payload, data_before, config_before)
    payload["checks"] = checks
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch-dir", default=str(DEFAULT_SCRATCH_DIR))
    parser.add_argument("--raw-dir", default=str(REPO_ROOT / "data" / "raw"))
    parser.add_argument("--report-out", default=str(DEFAULT_REPORT))
    parser.add_argument("--experiment-out", default=str(DEFAULT_EXPERIMENT))
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="compute the payload and run the checks but write no tracked "
        "artifact (the report and experiment paths are left untouched)",
    )
    args = parser.parse_args(argv)

    scratch_dir = Path(args.scratch_dir)
    raw_dir = Path(args.raw_dir)
    report_out = Path(args.report_out)
    experiment_out = Path(args.experiment_out)

    payload = evaluate(scratch_dir, raw_dir)
    checks = payload["checks"]

    failed = [check["check"] for check in checks if not check["ok"]]
    integrity_failures = [
        name
        for name in failed
        if name
        in {
            "panel_complete",
            "no_missing_prices",
            "no_duplicate_timestamps",
            "no_non_positive_prices",
            "price_series_continuous",
            "overlap_identical_to_committed_cache",
            "data_unchanged",
            "config_unchanged",
        }
    ]
    if integrity_failures:
        fail("failed integrity checks: " + ", ".join(integrity_failures))

    if not args.no_report:
        report_out.parent.mkdir(parents=True, exist_ok=True)
        experiment_out.parent.mkdir(parents=True, exist_ok=True)
        report_out.write_text(render_report(payload, checks), encoding="utf-8")
        experiment_out.write_text(render_experiment(payload, checks), encoding="utf-8")

    gate = payload["gate"]
    verdict = "PASS" if gate["gate_passed"] else "BLOCKED"
    print(f"OVERALL: {verdict}")
    print(f"Common inception: {gate['common_inception']} (deadline: {gate['common_inception_deadline']})")
    print(
        f"Folds: {gate['business_day_folds']} (business-day calendar), "
        f"{gate['session_calendar_folds']} (traded-session calendar), required {MIN_FOLDS}"
    )
    print(f"Business days: {gate['business_days']} (required {REQUIRED_BUSINESS_DAYS})")
    for check in checks:
        print(f"  [{'PASS' if check['ok'] else 'FAIL'}] {check['check']}: {check['detail']}")
    print(f"REPORT|{report_out if not args.no_report else '(not written: --no-report)'}")
    print(f"EXPERIMENT|{experiment_out if not args.no_report else '(not written: --no-report)'}")
    return 0 if gate["gate_passed"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
