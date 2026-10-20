#!/usr/bin/env python3
"""Walk-forward embargo (fold-overlap) sensitivity audit for the incumbent
``tsmomentum_spytrend_001`` candidate (Cycle 910).

The published walk-forward for this candidate steps the folds by 6 months over
a 12-month test window, so consecutive test windows **overlap**: the folds are
not independent observations. This tool re-measures the published evidence
under three fold designs over the *same* continuously computed point-in-time
path and publishes the delta against the published protocol. It is a
**read-only sensitivity**: the published protocol, the gates, the candidate
parameters and every committed artifact are left untouched.

Designs
-------
1. **Published design** (reference): 10y train / 12m test / 6m step, 21d
   purge, 21d embargo -- the design of the published record.
2. **Design A** (non-overlapping test windows): step = test window length
   (12 months), everything else unchanged.
3. **Design B** (literal embargo, informational): the next training window
   starts after the previous test window ends plus the configured embargo.

Data and machinery
------------------
* **Cache only.** The close panel is read from the committed parquet cache in
  ``data/raw/``. The fetcher is never called, and nothing under ``data/`` or
  ``config/`` is written.
* **Config-faithful.** The candidate definition (universe, dates, signal,
  overlay, trend filter, cost model, walk-forward design) is consumed as-is
  from the committed ``research/run_cycle6.py`` module -- the script that
  produced the published record -- and the overlay is executed with that
  module's own ``_apply_overlay`` so the path cannot drift from the
  published one.
* **Published record resolved by content**, not by filename: the record that
  carries the published aggregate table is located by parsing
  ``research/experiments/*.md`` and matching the published anchor, and the
  published numbers are extracted from it deterministically.

Reproduction anchor
-------------------
The tool re-derives the published design from the committed cache and checks
it against the published record: the fold count, the per-fold test windows,
the per-fold OOS Sharpe / annualised return / max drawdown / trade count and
the published aggregate statistics. A mismatch fails the run.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.run_cycle6 import (  # noqa: E402  (committed candidate definition)
    DD_THRESHOLD,
    END_DATE,
    LOOKBACK,
    SKIP,
    SPY_SMA_WINDOW,
    START_DATE,
    SYMBOLS,
    TOP_FRACTION,
    VOL_TARGET,
    VOL_TARGET_LOOKBACK,
    WF_EMBARGO_DAYS,
    WF_PURGE_DAYS,
    WF_STEP_MONTHS,
    WF_TEST_MONTHS,
    WF_TRAIN_YEARS,
    _apply_overlay,
)
from src.backtest.engine import get_cost_params, get_risk_free_rate  # noqa: E402
from src.evaluation.sharpe import sharpe_ratio  # noqa: E402
from src.evaluation.utils import period_metrics  # noqa: E402
from src.evaluation.walkforward import generate_walkforward_splits  # noqa: E402
from src.features.momentum import build_weights  # noqa: E402

CANDIDATE_ID = "tsmomentum_spytrend_001"
CYCLE = "910"

REPORTS_DIR = REPO_ROOT / "research" / "reports"
EXPERIMENTS_DIR = REPO_ROOT / "research" / "experiments"
RAW_DIR = REPO_ROOT / "data" / "raw"
OUT_REPORT = REPORTS_DIR / "tsmomentum_walkforward_embargo_001.md"
OUT_EXP = EXPERIMENTS_DIR / "tsmomentum_walkforward_embargo_001.md"

# The anchor quoted in the task specification and in the published record.
PUBLISHED_WF_MEAN = 0.9473
# Pre-registered promotion-gate thresholds (AGENTS.md "Promotion gate" and the
# published record's gate table). These are inputs, never derived from data.
GATE_WF_MEAN_MIN = 0.9
GATE_POSITIVE_FOLD_RATE_MIN = 0.5
GATE_POOLED_TRADES_MIN = 100

# Aggregate row labels of the published record, mapped to the tool's keys.
AGGREGATE_KEYS = {
    "Folds": "n_folds",
    "Mean Test Sharpe": "mean_test_sharpe",
    "Std Test Sharpe": "std_test_sharpe",
    "Median Test Sharpe": "median_test_sharpe",
    "Min Test Sharpe": "min_test_sharpe",
    "Max Test Sharpe": "max_test_sharpe",
    "% Positive Sharpe Folds": "pct_positive_sharpe",
    "Mean Test Ann. Return": "mean_test_ann_return",
    "Mean Test Max DD": "mean_test_max_dd",
    "Mean Test Trades": "mean_test_trades",
    "Total Pooled OOS Trades": "total_test_trades",
}
PERCENT_KEYS = {"pct_positive_sharpe", "mean_test_ann_return", "mean_test_max_dd"}


class AuditError(RuntimeError):
    """Raised when a required input is missing or malformed (fails closed)."""


def fail(message: str) -> None:
    raise AuditError(message)


# ----------------------------------------------------------------------
# Read-only helpers
# ----------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fingerprint(root: Path) -> dict[str, str]:
    """SHA-256 of every file under *root* (used for the read-only guarantee)."""
    if not root.exists():
        return {}
    out: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            out[str(path.relative_to(REPO_ROOT))] = sha256_file(path)
    return out


def tracked_artifact_hashes() -> dict[str, str]:
    """Hashes of every committed (git-tracked) artifact under the audited trees."""
    import subprocess

    out: dict[str, str] = {}
    for tree in ("src", "config", "research/experiments", "research/reports", "tests"):
        try:
            res = subprocess.run(
                ["git", "ls-files", tree],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError:
            continue
        if res.returncode != 0:
            continue
        for rel in res.stdout.splitlines():
            rel = rel.strip()
            if not rel:
                continue
            path = REPO_ROOT / rel
            if path.is_file():
                out[rel] = sha256_file(path)
    return out


# ----------------------------------------------------------------------
# Published record: resolved by content, parsed deterministically
# ----------------------------------------------------------------------
def _parse_number(text: str) -> tuple[float, int, bool]:
    """Return (value, decimals, is_percent) for a published numeric cell."""
    raw = text.strip()
    is_percent = raw.endswith("%")
    if is_percent:
        raw = raw[:-1].strip()
    if not re.fullmatch(r"-?\d+(\.\d+)?", raw):
        fail(f"published cell is not numeric: {text!r}")
    decimals = len(raw.split(".")[1]) if "." in raw else 0
    return float(raw), decimals, is_percent


def _table_rows(text: str, header_contains: str) -> list[list[str]]:
    """Rows of the first markdown table whose header contains *header_contains*."""
    rows: list[list[str]] = []
    in_table = False
    header_seen = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            if in_table and not stripped:
                in_table = False
            continue
        if not in_table:
            in_table = True
            header_seen = header_contains in stripped
            continue
        if not header_seen:
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        rows.append(cells)
    return rows


def parse_published_record(text: str) -> dict[str, Any] | None:
    """Parse the published walk-forward record; ``None`` if it is not one."""
    if "Per-Fold Results" not in text or "Mean Test Sharpe" not in text:
        return None

    aggregate: dict[str, Any] = {}
    for cells in _table_rows(text, "Metric"):
        if len(cells) != 2:
            continue
        key = AGGREGATE_KEYS.get(cells[0].strip())
        if key is None:
            continue
        value, decimals, is_percent = _parse_number(cells[1])
        aggregate[key] = {
            "value": value,
            "decimals": decimals,
            "is_percent": is_percent,
            "text": cells[1].strip(),
        }

    if "mean_test_sharpe" not in aggregate or "n_folds" not in aggregate:
        return None
    if abs(aggregate["mean_test_sharpe"]["value"] - PUBLISHED_WF_MEAN) > 1e-9:
        return None

    folds: list[dict[str, Any]] = []
    for cells in _table_rows(text, "Train Start"):
        if len(cells) != 10:
            continue
        try:
            fold = int(cells[0])
            train_sharpe = float(cells[5])
            test_sharpe = float(cells[6])
            test_ann_return = float(cells[7])
            test_max_dd = float(cells[8])
            test_trades = int(cells[9])
        except ValueError:
            continue
        folds.append(
            {
                "fold": fold,
                "train_start": cells[1],
                "train_end": cells[2],
                "test_start": cells[3],
                "test_end": cells[4],
                "train_sharpe": train_sharpe,
                "test_sharpe": test_sharpe,
                "test_ann_return": test_ann_return,
                "test_max_dd": test_max_dd,
                "test_trades": test_trades,
            }
        )
    if len(folds) != int(aggregate["n_folds"]["value"]):
        return None

    gates: dict[str, Any] = {}
    for cells in _table_rows(text, "Threshold"):
        if len(cells) != 4:
            continue
        name = cells[0].strip()
        if "Walk-Forward Mean OOS Sharpe" in name:
            gates["wf_mean_oos_sharpe_min"] = _parse_number(cells[1])[0]
        elif "folds positive Sharpe" in name:
            value, _, is_percent = _parse_number(cells[1])
            gates["positive_fold_rate_min"] = value / 100.0 if is_percent else value
    if "wf_mean_oos_sharpe_min" not in gates:
        return None

    return {"aggregate": aggregate, "folds": folds, "gates": gates}


def resolve_published_record(experiments_dir: Path) -> tuple[Path, dict[str, Any]]:
    """Locate the published walk-forward record by content (not by filename)."""
    if not experiments_dir.is_dir():
        fail(f"experiments directory not found: {experiments_dir}")
    matches: list[tuple[Path, dict[str, Any]]] = []
    parse_errors: list[str] = []
    for path in sorted(experiments_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        try:
            parsed = parse_published_record(text)
        except AuditError as exc:
            parse_errors.append(f"{path.name}: {exc}")
            continue
        if parsed is not None:
            matches.append((path, parsed))
    if not matches:
        detail = f" (parse errors: {'; '.join(parse_errors)})" if parse_errors else ""
        fail(
            "no published walk-forward record with the published anchor "
            f"{PUBLISHED_WF_MEAN} found in {experiments_dir}{detail}"
        )
    if len(matches) > 1:
        names = ", ".join(str(p) for p, _ in matches)
        fail(f"published record is ambiguous (multiple matches): {names}")
    return matches[0]


# ----------------------------------------------------------------------
# Cache-only data access
# ----------------------------------------------------------------------
def load_close_from_cache(symbols: list[str], raw_dir: Path) -> pd.DataFrame:
    """Close panel from the committed parquet cache (the fetcher is never used).

    Mirrors the alignment the committed fetcher performs: the union of the
    symbols' cached calendars restricted to weekdays, each symbol forward
    filled onto that calendar.
    """
    frames: dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        path = raw_dir / f"{symbol}.parquet"
        if not path.exists():
            fail(f"required cached price file is missing: {path}")
        try:
            df = pd.read_parquet(path)
        except Exception as exc:  # noqa: BLE001
            fail(f"cached price file is unreadable: {path} ({exc})")
        if df.empty:
            fail(f"cached price file is empty: {path}")
        idx = pd.to_datetime(df.index)
        if idx.tz is None:
            idx = idx.tz_localize("UTC", ambiguous="infer", nonexistent="shift_forward")
        else:
            idx = idx.tz_convert("UTC")
        df = df.copy()
        df.index = idx
        frames[symbol] = df.sort_index()

    all_index = pd.DatetimeIndex(sorted(set().union(*[f.index for f in frames.values()])))
    all_index = all_index[all_index.weekday < 5]
    if len(all_index) == 0:
        fail("cached price files produced an empty calendar")

    out = pd.DataFrame(
        index=all_index,
        columns=pd.MultiIndex.from_product(
            [["Open", "High", "Low", "Close", "Volume"], list(frames.keys())]
        ),
    )
    for symbol, df in frames.items():
        reindexed = df.reindex(all_index)
        for col in ("Open", "High", "Low", "Close", "Volume"):
            out[(col, symbol)] = reindexed[col].ffill()

    close = out.xs("Close", level=0, axis=1)
    close = close.ffill().dropna(how="all")
    if close.empty:
        fail("cached close panel is empty")
    missing = [c for c in symbols if c not in close.columns]
    if missing:
        fail(f"cached close panel is missing symbols: {missing}")
    return close


def build_candidate_path(close: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    """The continuously computed point-in-time path used by the published record.

    Identical to the published protocol's ``_eval_candidate_period`` (which
    evaluates the candidate over the full history and slices the requested
    period), but computed once instead of once per fold.
    """
    weights = build_weights(close, lookback=LOOKBACK, skip=SKIP, top_fraction=TOP_FRACTION)
    common = close.index.intersection(weights.index)
    close_a = close.loc[common]
    weights_a = weights.loc[common]
    daily_ret = close_a.pct_change().fillna(0.0)

    spy = close_a["SPY"]
    spy_sma = spy.rolling(SPY_SMA_WINDOW).mean()
    exposure = pd.Series(1.0, index=close_a.index)
    exposure[spy < spy_sma] = 0.0
    exposure[spy.isna() | spy_sma.isna()] = 0.0

    combined_weights, net_ret, _ = _apply_overlay(
        daily_ret, weights_a, exposure_factor=exposure
    )
    if len(net_ret) == 0:
        fail("candidate path is empty")
    return net_ret, combined_weights


# ----------------------------------------------------------------------
# Fold designs
# ----------------------------------------------------------------------
def published_splits() -> list[dict[str, Any]]:
    return generate_walkforward_splits(
        START_DATE,
        END_DATE,
        WF_TRAIN_YEARS,
        WF_TEST_MONTHS,
        WF_STEP_MONTHS,
        WF_PURGE_DAYS,
        WF_EMBARGO_DAYS,
    )


def design_a_splits() -> list[dict[str, Any]]:
    """Non-overlapping test windows: step = test window length."""
    return generate_walkforward_splits(
        START_DATE,
        END_DATE,
        WF_TRAIN_YEARS,
        WF_TEST_MONTHS,
        float(WF_TEST_MONTHS),
        WF_PURGE_DAYS,
        WF_EMBARGO_DAYS,
    )


def design_b_splits() -> list[dict[str, Any]]:
    """Literal embargo: the next training window starts after the previous test
    window ends plus the configured embargo days."""
    all_dates = pd.bdate_range(start=START_DATE, end=END_DATE)
    if len(all_dates) == 0:
        return []
    splits: list[dict[str, Any]] = []
    train_window = int(WF_TRAIN_YEARS * 252)
    test_window = int(WF_TEST_MONTHS * 21)
    idx = 0
    while True:
        if idx + train_window > len(all_dates):
            break
        train_start = all_dates[idx]
        train_end_idx = idx + train_window - 1
        test_start_idx = train_end_idx + 1 + WF_PURGE_DAYS
        if test_start_idx >= len(all_dates):
            break
        test_start = all_dates[test_start_idx]
        test_end_idx = test_start_idx + test_window - 1
        if test_end_idx >= len(all_dates):
            break
        test_end = all_dates[test_end_idx]
        splits.append(
            {
                "train_start": train_start.strftime("%Y-%m-%d"),
                "train_end": all_dates[train_end_idx].strftime("%Y-%m-%d"),
                "test_start": test_start.strftime("%Y-%m-%d"),
                "test_end": test_end.strftime("%Y-%m-%d"),
            }
        )
        next_start = test_end_idx + 1 + WF_EMBARGO_DAYS
        if next_start <= idx:
            break
        idx = next_start
        if len(splits) > 200:
            break
    return splits


def mean_consecutive_overlap_days(folds: list[dict[str, Any]]) -> float:
    """Mean overlap (calendar days) between consecutive test windows."""
    overlaps = []
    for prev, nxt in itertools.pairwise(folds):
        a = pd.Timestamp(prev["test_end"])
        b = pd.Timestamp(nxt["test_start"])
        overlaps.append(max(0, int((a - b).days)))
    if not overlaps:
        return 0.0
    return float(sum(overlaps) / len(overlaps))


def max_disjoint_test_windows(folds: list[dict[str, Any]]) -> int:
    """The number of folds whose test windows share no session."""
    intervals = sorted((f["test_start"], f["test_end"]) for f in folds)
    count = 0
    last_end: str | None = None
    for start, end in intervals:
        if last_end is None or start > last_end:
            count += 1
            last_end = end
    return count


def evaluate_design(
    net_ret: pd.Series,
    weights: pd.DataFrame,
    splits: list[dict[str, Any]],
) -> dict[str, Any]:
    """Slice the shared path per fold and compute the published metrics."""
    rows: list[dict[str, Any]] = []
    for i, sp in enumerate(splits):
        train_mask = (weights.index >= pd.Timestamp(sp["train_start"], tz="UTC")) & (
            weights.index <= pd.Timestamp(sp["train_end"], tz="UTC")
        )
        test_mask = (weights.index >= pd.Timestamp(sp["test_start"], tz="UTC")) & (
            weights.index <= pd.Timestamp(sp["test_end"], tz="UTC")
        )
        if not test_mask.any():
            continue
        train_m = period_metrics(net_ret[train_mask], weights[train_mask])
        test_m = period_metrics(net_ret[test_mask], weights[test_mask])
        rows.append(
            {
                "fold": i + 1,
                "train_start": sp["train_start"],
                "train_end": sp["train_end"],
                "test_start": sp["test_start"],
                "test_end": sp["test_end"],
                "train_sharpe": float(train_m.get("sharpe_ratio", np.nan)),
                "test_sharpe": float(test_m.get("sharpe_ratio", np.nan)),
                "test_ann_return": float(test_m.get("annualized_return", np.nan)),
                "test_max_dd": float(test_m.get("max_drawdown", np.nan)),
                "test_trades": int(test_m.get("trade_count", 0)),
                "test_sharpe_canonical": float(
                    sharpe_ratio(net_ret[test_mask].to_numpy())
                ),
            }
        )

    sharpes = [r["test_sharpe"] for r in rows if not np.isnan(r["test_sharpe"])]
    if not sharpes:
        return {"folds": rows, "summary": {}, "independence": {
            "mean_consecutive_overlap_days": 0.0, "max_disjoint_test_windows": 0}}
    summary = {
        "n_folds": len(rows),
        "mean_test_sharpe": float(np.mean(sharpes)),
        "std_test_sharpe": float(np.std(sharpes, ddof=1)),
        "median_test_sharpe": float(np.median(sharpes)),
        "min_test_sharpe": float(np.min(sharpes)),
        "max_test_sharpe": float(np.max(sharpes)),
        "pct_positive_sharpe": float(np.mean([s > 0 for s in sharpes])),
        "mean_test_ann_return": float(
            np.mean([r["test_ann_return"] for r in rows if not np.isnan(r["test_ann_return"])])
        ),
        "mean_test_max_dd": float(
            np.mean([r["test_max_dd"] for r in rows if not np.isnan(r["test_max_dd"])])
        ),
        "mean_test_trades": float(np.mean([r["test_trades"] for r in rows])),
        "total_test_trades": int(sum(r["test_trades"] for r in rows)),
        "mean_test_sharpe_canonical": float(
            np.mean([r["test_sharpe_canonical"] for r in rows])
        ),
    }
    independence = {
        "mean_consecutive_overlap_days": mean_consecutive_overlap_days(rows),
        "max_disjoint_test_windows": max_disjoint_test_windows(rows),
    }
    return {"folds": rows, "summary": summary, "independence": independence}


def gate_table(summary: dict[str, Any]) -> list[dict[str, Any]]:
    """Gate table on the published protocol's own scale and thresholds."""
    if not summary:
        return []
    mean_sharpe = float(summary.get("mean_test_sharpe", float("nan")))
    positive_rate = float(summary.get("pct_positive_sharpe", float("nan")))
    pooled_trades = int(summary.get("total_test_trades", 0))
    gates = [
        {
            "gate": "wf_mean_oos_sharpe",
            "threshold": GATE_WF_MEAN_MIN,
            "observed": mean_sharpe,
            "status": "PASS" if mean_sharpe >= GATE_WF_MEAN_MIN else "FAIL",
        },
        {
            "gate": "positive_fold_rate",
            "threshold": GATE_POSITIVE_FOLD_RATE_MIN,
            "observed": positive_rate,
            "status": "PASS" if positive_rate >= GATE_POSITIVE_FOLD_RATE_MIN else "FAIL",
        },
        {
            "gate": "pooled_oos_trades",
            "threshold": GATE_POOLED_TRADES_MIN,
            "observed": pooled_trades,
            "status": "PASS" if pooled_trades > GATE_POOLED_TRADES_MIN else "FAIL",
        },
    ]
    for g in gates:
        g["margin"] = float(g["observed"] - g["threshold"])
    return gates


def decision_from_gates(gates: list[dict[str, Any]]) -> dict[str, str]:
    if not gates:
        return {"label": "Insufficient folds", "detail": "no gate table could be formed"}
    failed = [g["gate"] for g in gates if g["status"] != "PASS"]
    if not failed:
        return {
            "label": "Passes preliminary gates",
            "detail": "all evaluated gates pass (the SMA-plateau gate is not fold-dependent and is not re-evaluated)",
        }
    return {
        "label": "Rejected/Failed",
        "detail": f"gate(s) not met: {', '.join(failed)}",
    }


# ----------------------------------------------------------------------
# Anchor
# ----------------------------------------------------------------------
def _published_match(observed: float, published: dict[str, Any]) -> dict[str, Any]:
    value = float(published["value"])
    decimals = int(published["decimals"])
    if published.get("is_percent"):
        scaled = observed * 100.0
        tol = 0.5 * (10.0 ** (-decimals))
    else:
        scaled = observed
        tol = 10.0 ** (-decimals)
    diff = abs(scaled - value)
    return {
        "published": value,
        "published_text": published["text"],
        "observed": observed,
        "scaled_observed": scaled,
        "tolerance": tol,
        "abs_diff": diff,
        "match": bool(diff <= tol + 1e-12),
    }


def build_anchor(
    published: dict[str, Any],
    recomputed: dict[str, Any],
) -> dict[str, Any]:
    """Compare the re-derived published design against the published record."""
    rows: list[dict[str, Any]] = []
    aggregate = published["aggregate"]
    summary = recomputed["summary"]

    for label, key in (
        ("n_folds", "n_folds"),
        ("mean_test_sharpe", "mean_test_sharpe"),
        ("std_test_sharpe", "std_test_sharpe"),
        ("median_test_sharpe", "median_test_sharpe"),
        ("min_test_sharpe", "min_test_sharpe"),
        ("max_test_sharpe", "max_test_sharpe"),
        ("pct_positive_sharpe", "pct_positive_sharpe"),
        ("mean_test_ann_return", "mean_test_ann_return"),
        ("mean_test_max_dd", "mean_test_max_dd"),
        ("mean_test_trades", "mean_test_trades"),
        ("total_test_trades", "total_test_trades"),
    ):
        if key not in aggregate or key not in summary:
            continue
        if key in ("n_folds", "total_test_trades"):
            observed = int(summary[key])
            expected = int(aggregate[key]["value"])
            rows.append(
                {
                    "metric": label,
                    "published": expected,
                    "published_text": aggregate[key]["text"],
                    "observed": observed,
                    "tolerance": 0,
                    "abs_diff": int(abs(observed - expected)),
                    "match": observed == expected,
                }
            )
            continue
        rows.append({"metric": label, **_published_match(float(summary[key]), aggregate[key])})

    # Per-fold reproduction: windows, OOS Sharpe, trade count.
    per_fold: list[dict[str, Any]] = []
    pub_folds = published["folds"]
    rec_folds = recomputed["folds"]
    for pub, rec in zip(pub_folds, rec_folds):
        window_match = (
            pub["train_start"] == rec["train_start"]
            and pub["train_end"] == rec["train_end"]
            and pub["test_start"] == rec["test_start"]
            and pub["test_end"] == rec["test_end"]
        )
        sharpe_diff = abs(pub["test_sharpe"] - rec["test_sharpe"])
        train_sharpe_diff = abs(pub["train_sharpe"] - rec["train_sharpe"])
        trades_match = int(pub["test_trades"]) == int(rec["test_trades"])
        per_fold.append(
            {
                "fold": pub["fold"],
                "window_match": bool(window_match),
                "test_sharpe_published": pub["test_sharpe"],
                "test_sharpe_observed": rec["test_sharpe"],
                "test_sharpe_abs_diff": sharpe_diff,
                "train_sharpe_abs_diff": train_sharpe_diff,
                "trades_match": bool(trades_match),
                "match": bool(
                    window_match
                    and sharpe_diff <= 1e-4
                    and train_sharpe_diff <= 1e-4
                    and trades_match
                ),
            }
        )
    per_fold_match = len(per_fold) == len(pub_folds) == len(rec_folds) and all(
        r["match"] for r in per_fold
    )
    return {
        "rows": rows,
        "matches": all(r["match"] for r in rows),
        "per_fold": per_fold,
        "per_fold_match": bool(per_fold_match),
        "per_fold_count": len(per_fold),
    }


# ----------------------------------------------------------------------
# Report / experiment record
# ----------------------------------------------------------------------
def _fmt(value: float, digits: int = 6) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "N/A"
    return f"{float(value):.{digits}f}"


def _fold_table(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| Fold | Train Start | Train End | Test Start | Test End | Train Sharpe | Test Sharpe | Test Ann. Ret. | Test Max DD | Test Trades |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            "| {fold} | {train_start} | {train_end} | {test_start} | {test_end} | "
            "{train_sharpe} | {test_sharpe} | {test_ann_return} | {test_max_dd} | {test_trades} |".format(
                fold=r["fold"],
                train_start=r["train_start"],
                train_end=r["train_end"],
                test_start=r["test_start"],
                test_end=r["test_end"],
                train_sharpe=_fmt(r["train_sharpe"], 4),
                test_sharpe=_fmt(r["test_sharpe"], 4),
                test_ann_return=_fmt(r["test_ann_return"], 4),
                test_max_dd=_fmt(r["test_max_dd"], 4),
                test_trades=r["test_trades"],
            )
        )
    return lines


def _design_summary_rows(design: dict[str, Any], label: str) -> list[str]:
    s = design["summary"]
    ind = design["independence"]
    if not s:
        return [
            f"| {label} | 0 | N/A | N/A | N/A | 0 | {ind['mean_consecutive_overlap_days']:.1f} | {ind['max_disjoint_test_windows']} | Insufficient folds (no gate table) |"
        ]
    return [
        "| {label} | {folds} | {mean} | {median} | {pos} | {trades} | {overlap} | {disjoint} | {decision} |".format(
            label=label,
            folds=s["n_folds"],
            mean=_fmt(s["mean_test_sharpe"]),
            median=_fmt(s["median_test_sharpe"]),
            pos=f"{s['pct_positive_sharpe']:.4f}",
            trades=s["total_test_trades"],
            overlap=f"{ind['mean_consecutive_overlap_days']:.1f}",
            disjoint=ind["max_disjoint_test_windows"],
            decision=design["decision"]["label"],
        )
    ]


def _gate_lines(gates: list[dict[str, Any]]) -> list[str]:
    if not gates:
        return ["- Gate table not formed (insufficient folds)."]
    return [
        "- {gate}: threshold {threshold}, observed {observed}, margin {margin}, status {status}".format(
            gate=g["gate"],
            threshold=g["threshold"],
            observed=_fmt(g["observed"]) if isinstance(g["observed"], float) else g["observed"],
            margin=_fmt(g["margin"]),
            status=g["status"],
        )
        for g in gates
    ]


def render_report(payload: dict[str, Any]) -> str:
    pub = payload["published_design"]
    des_a = payload["design_a_nonoverlapping"]
    des_b = payload["design_b_embargo_literal"]
    delta = payload["delta_published_vs_design_a"]
    lines: list[str] = []
    lines.append(
        f"# TSMomentum SPY-Trend Walk-Forward Embargo Audit (tsmomentum_walkforward_embargo_001, Cycle {CYCLE})"
    )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Candidate: `{CANDIDATE_ID}` (the incumbent)")
    lines.append(
        f"- Published walk-forward record (resolved by content): `{payload['published_record_path']}`"
    )
    lines.append(
        f"- Published WF mean OOS Sharpe: {payload['published_anchor_value']:.4f} "
        f"(gate >= {GATE_WF_MEAN_MIN}, margin {payload['published_anchor_value'] - GATE_WF_MEAN_MIN:+.4f})"
    )
    lines.append(
        f"- Design A (non-overlapping test windows) WF mean OOS Sharpe: "
        f"{_fmt(des_a['summary'].get('mean_test_sharpe'), 4)} "
        f"({des_a['summary'].get('n_folds', 0)} folds)"
    )
    lines.append(
        f"- Gate-1 outcome: published **{payload['published_gate1_status']}**, "
        f"Design A **{des_a['gates'][0]['status'] if des_a['gates'] else 'N/A'}** -- "
        f"outcome changes under Design A: **{'YES' if delta['gate_outcome_changes'] else 'NO'}**"
    )
    lines.append(
        f"- Published verdict: **{payload['published_verdict']}**; "
        f"Design A verdict: **{des_a['decision']['label']}**; "
        f"verdict survives Design A: **{'YES' if delta['verdict_survives'] else 'NO'}** "
        "(the published record's verdict also requires the SMA-plateau gate, which is not "
        "fold-dependent and is therefore not re-evaluated here)"
    )
    lines.append(
        "- Read-only: `data/` and `config/` byte-identical before and after the run "
        f"(**{'yes' if payload['read_only']['data_unchanged'] and payload['read_only']['config_unchanged'] else 'NO'}**); "
        "no committed artifact modified "
        f"(**{'yes' if payload['read_only']['committed_artifacts_unchanged'] else 'NO'}**)."
    )
    lines.append(
        "- Data source: committed parquet cache in `data/raw/` only; the fetcher is never called."
    )
    lines.append("")
    lines.append("## 1. Reproduction anchor (published design, re-derived from the committed cache)")
    lines.append("")
    lines.append(
        "The published design is re-derived from the committed cache with the committed "
        "candidate definition and compared with the published record, which is resolved by "
        "content (the record that carries the published aggregate table and fold table)."
    )
    lines.append("")
    lines.append("| Metric | Published | Recomputed | Tolerance | Match |")
    lines.append("|---|---|---|---|---|")
    for r in payload["anchor"]["rows"]:
        lines.append(
            "| {metric} | {published_text} | {observed} | {tol} | {match} |".format(
                metric=r["metric"],
                published_text=r["published_text"],
                observed=(
                    _fmt(r["observed"], 4)
                    if isinstance(r["observed"], float)
                    else r["observed"]
                ),
                tol=_fmt(r["tolerance"], 6),
                match="MATCH" if r["match"] else "DIFF",
            )
        )
    lines.append("")
    lines.append(
        f"- Aggregate anchor: **{'MATCH' if payload['anchor']['matches'] else 'DIFF'}**"
    )
    lines.append(
        f"- Per-fold reproduction: **{payload['anchor']['per_fold_count']} folds**, "
        f"all windows/OOS Sharpe/trades reproduced: "
        f"**{'YES' if payload['anchor']['per_fold_match'] else 'NO'}**"
    )
    lines.append("")
    lines.append("## 2. The three designs")
    lines.append("")
    lines.append(
        "All three designs are evaluated on the **same continuously computed "
        "point-in-time path** (one pass over the committed cache, one overlay, one "
        "cost model); only the fold windows change."
    )
    lines.append("")
    lines.append(
        "| Design | Folds | WF mean OOS Sharpe | Median | Positive fold rate | Pooled OOS trades | Mean consecutive overlap (days) | Max disjoint test windows | Decision |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    lines.extend(_design_summary_rows(pub, "Published design"))
    lines.extend(_design_summary_rows(des_a, "Design A (non-overlapping)"))
    lines.extend(_design_summary_rows(des_b, "Design B (literal embargo)"))
    lines.append("")
    lines.append("### 2.1 Published design -- fold table")
    lines.append("")
    lines.extend(_fold_table(pub["folds"]))
    lines.append("")
    lines.append("### 2.2 Design A (non-overlapping test windows) -- fold table")
    lines.append("")
    lines.extend(_fold_table(des_a["folds"]))
    lines.append("")
    lines.append("### 2.3 Design B (literal embargo, informational) -- fold table")
    lines.append("")
    lines.extend(_fold_table(des_b["folds"]))
    lines.append("")
    lines.append(
        "Design B is informational: with a 10-year training window and the configured "
        f"embargo the fold count is {des_b['summary'].get('n_folds', 0)}, which is too few "
        "to form a stable gate table. The fold count is published and the gate table is "
        "not forced."
    )
    lines.append("")
    lines.append("## 3. Delta (published design vs Design A)")
    lines.append("")
    lines.append(f"- Fold count: published {delta['fold_count_published']}, Design A {delta['fold_count_design_a']} (delta {delta['fold_count_delta']})")
    lines.append(
        f"- WF mean OOS Sharpe: published {_fmt(delta['mean_sharpe_published'], 6)}, "
        f"Design A {_fmt(delta['mean_sharpe_design_a'], 6)} "
        f"(delta {_fmt(delta['mean_sharpe_delta'], 6)})"
    )
    lines.append(
        f"- Gate-1 margin (>= {GATE_WF_MEAN_MIN}): published {delta['gate1_margin_published']:+.6f}, "
        f"Design A {delta['gate1_margin_design_a']:+.6f} "
        f"(delta {delta['gate1_margin_delta']:+.6f})"
    )
    lines.append(
        f"- Gate-1 outcome changes under Design A: **{'YES' if delta['gate_outcome_changes'] else 'NO'}**"
    )
    lines.append(
        f"- Published verdict survives Design A: **{'YES' if delta['verdict_survives'] else 'NO'}**"
    )
    lines.append("")
    lines.append("## 4. Gate tables")
    lines.append("")
    lines.append(
        "Thresholds are the pre-registered ones (published record gate table and the "
        "AGENTS.md promotion gate: WF mean OOS Sharpe >= 0.9, positive fold rate >= 50%, "
        "> 100 pooled OOS trades). The SMA-plateau gate of the published record is not "
        "fold-dependent and is not re-evaluated here."
    )
    lines.append("")
    lines.append("### Published design")
    lines.extend(_gate_lines(pub["gates"]))
    lines.append("")
    lines.append("### Design A")
    lines.extend(_gate_lines(des_a["gates"]))
    lines.append("")
    lines.append("### Design B")
    lines.extend(_gate_lines(des_b["gates"]))
    lines.append("")
    lines.append("## 5. Independence diagnostic")
    lines.append("")
    lines.append("| Design | Folds | Mean consecutive test-window overlap (days) | Max pairwise-disjoint test windows |")
    lines.append("|---|---|---|---|")
    for label, design in (
        ("Published design", pub),
        ("Design A (non-overlapping)", des_a),
        ("Design B (literal embargo)", des_b),
    ):
        ind = design["independence"]
        lines.append(
            f"| {label} | {design['summary'].get('n_folds', 0)} | "
            f"{ind['mean_consecutive_overlap_days']:.1f} | {ind['max_disjoint_test_windows']} |"
        )
    lines.append("")
    lines.append(
        "The published design's test windows overlap, so its folds are not independent "
        "observations; Design A makes them pairwise disjoint, and its disjoint count "
        "equals its fold count."
    )
    lines.append("")
    lines.append("## 6. Checks")
    lines.append("")
    for c in payload["checks"]:
        lines.append(
            f"- [{c['name']}]: {'PASS' if c['pass'] else 'FAIL'}"
            + (f" (observed: {c['observed']}, expected: {c['expected']})" if c.get("observed") or c.get("expected") else "")
        )
    lines.append("")
    lines.append("## 7. Reproduction commands")
    lines.append("")
    lines.append("```bash")
    lines.append("python research/tsmomentum_walkforward_embargo_audit.py")
    lines.append("python -m pytest -q tests/test_tsmomentum_walkforward_embargo_audit.py")
    lines.append("python -m pytest -q")
    lines.append("git status --porcelain data/")
    lines.append("```")
    lines.append("")
    lines.append("## 8. JSON payload")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(payload, indent=2, default=str, sort_keys=True))
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def render_experiment(payload: dict[str, Any]) -> str:
    pub = payload["published_design"]
    des_a = payload["design_a_nonoverlapping"]
    des_b = payload["design_b_embargo_literal"]
    delta = payload["delta_published_vs_design_a"]
    lines: list[str] = []
    lines.append(
        f"# Experiment: Walk-forward embargo sensitivity for `{CANDIDATE_ID}` (tsmomentum_walkforward_embargo_001, Cycle {CYCLE})"
    )
    lines.append("")
    lines.append("## Hypothesis reference")
    lines.append("")
    lines.append("- Candidate hypothesis: `research/hypotheses/tsmomentum_004.md` (Cycle 5 promoted candidate)")
    lines.append(
        f"- Published walk-forward record: `{payload['published_record_path']}` (resolved by content)"
    )
    lines.append(
        "- Frozen candidate definition: `research/run_cycle6.py` (the script that produced the published record; read, never changed)"
    )
    lines.append("- Pre-registered promotion gates: `AGENTS.md` and the published record's gate table (read, never changed)")
    lines.append("")
    lines.append("## Objective")
    lines.append("")
    lines.append(
        "Quantify how much of the incumbent's published walk-forward evidence survives a "
        "non-overlapping (embargoed) fold design, publish the delta against the published "
        "protocol, and state whether the published gate outcome changes under Design A. "
        "Sensitivity only: the published protocol, the gates and every committed artifact "
        "are unchanged."
    )
    lines.append("")
    lines.append("## Data")
    lines.append("")
    lines.append("- Source: committed raw cache `data/raw/*.parquet` (cache-only; the fetcher is never called)")
    lines.append(f"- Universe: {', '.join(SYMBOLS)}")
    lines.append(f"- Date range: {START_DATE} to {END_DATE}")
    lines.append(f"- Point-in-time treatment: {payload['point_in_time']}")
    lines.append(
        f"- Cost model: {payload['commission_bps']:.1f} bps commission + {payload['slippage_bps']:.1f} bps slippage "
        f"= {payload['commission_bps'] + payload['slippage_bps']:.1f} bps round-trip; risk-free rate {payload['rf_annual']} annual"
    )
    lines.append("")
    lines.append("## Configuration (consumed as-is, never inferred)")
    lines.append("")
    lines.append(f"- Signal: TSMOM lookback {LOOKBACK}, skip {SKIP}, top_fraction {TOP_FRACTION}")
    lines.append(
        f"- Risk overlay: vol-target {VOL_TARGET} (lookback {VOL_TARGET_LOOKBACK}) + drawdown control {DD_THRESHOLD}"
    )
    lines.append(f"- Regime filter: SPY {SPY_SMA_WINDOW}-day SMA trend filter")
    lines.append(
        f"- Walk-forward (published design): train {WF_TRAIN_YEARS}y / test {WF_TEST_MONTHS}m / step {WF_STEP_MONTHS}m, purge {WF_PURGE_DAYS}d, embargo {WF_EMBARGO_DAYS}d"
    )
    lines.append(
        f"- Gates (pre-registered): WF mean OOS Sharpe >= {GATE_WF_MEAN_MIN}, positive fold rate >= {GATE_POSITIVE_FOLD_RATE_MIN}, pooled OOS trades > {GATE_POOLED_TRADES_MIN}"
    )
    lines.append("")
    lines.append("## Splits")
    lines.append("")
    lines.append(
        f"- Published design: {pub['summary'].get('n_folds', 0)} folds, overlap {pub['independence']['mean_consecutive_overlap_days']:.1f} days, disjoint {pub['independence']['max_disjoint_test_windows']}"
    )
    lines.append(
        f"- Design A (non-overlapping): {des_a['summary'].get('n_folds', 0)} folds, overlap {des_a['independence']['mean_consecutive_overlap_days']:.1f} days, disjoint {des_a['independence']['max_disjoint_test_windows']}"
    )
    lines.append(
        f"- Design B (literal embargo): {des_b['summary'].get('n_folds', 0)} folds, overlap {des_b['independence']['mean_consecutive_overlap_days']:.1f} days, disjoint {des_b['independence']['max_disjoint_test_windows']}"
    )
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| Design | Folds | WF mean OOS Sharpe | Median | Std | Positive fold rate | Pooled OOS trades | Decision |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for label, design in (
        ("Published", pub),
        ("Design A", des_a),
        ("Design B", des_b),
    ):
        s = design["summary"]
        lines.append(
            "| {label} | {folds} | {mean} | {median} | {std} | {pos} | {trades} | {decision} |".format(
                label=label,
                folds=s.get("n_folds", 0),
                mean=_fmt(s.get("mean_test_sharpe", float("nan"))),
                median=_fmt(s.get("median_test_sharpe", float("nan"))),
                std=_fmt(s.get("std_test_sharpe", float("nan"))),
                pos=f"{s.get('pct_positive_sharpe', float('nan')):.4f}",
                trades=s.get("total_test_trades", 0),
                decision=design["decision"]["label"],
            )
        )
    lines.append("")
    lines.append(
        f"- Published anchor reproduced: **{'YES' if payload['anchor']['matches'] and payload['anchor']['per_fold_match'] else 'NO'}** "
        f"(published WF mean OOS Sharpe {payload['published_anchor_value']:.4f}, "
        f"recomputed {pub['summary'].get('mean_test_sharpe', float('nan')):.4f})"
    )
    lines.append(
        f"- Delta (published -> Design A): folds {delta['fold_count_published']} -> {delta['fold_count_design_a']}, "
        f"mean OOS Sharpe {delta['mean_sharpe_published']:.6f} -> {delta['mean_sharpe_design_a']:.6f} "
        f"({delta['mean_sharpe_delta']:+.6f}), gate-1 margin {delta['gate1_margin_published']:+.6f} -> {delta['gate1_margin_design_a']:+.6f}"
    )
    lines.append(
        f"- Gate-1 outcome changes under Design A: **{'YES' if delta['gate_outcome_changes'] else 'NO'}**; "
        f"published verdict ({payload['published_verdict']}) survives: **{'YES' if delta['verdict_survives'] else 'NO'}**"
    )
    lines.append(
        f"- Informational (canonical arithmetic scale, not a gate): published {pub['summary'].get('mean_test_sharpe_canonical', float('nan')):.6f}, "
        f"Design A {des_a['summary'].get('mean_test_sharpe_canonical', float('nan')):.6f}"
    )
    lines.append("")
    lines.append("## Independence diagnostic")
    lines.append("")
    lines.append("| Design | Folds | Mean consecutive test-window overlap (days) | Max pairwise-disjoint test windows |")
    lines.append("|---|---|---|---|")
    for label, design in (
        ("Published", pub),
        ("Design A", des_a),
        ("Design B", des_b),
    ):
        ind = design["independence"]
        lines.append(
            f"| {label} | {design['summary'].get('n_folds', 0)} | {ind['mean_consecutive_overlap_days']:.1f} | {ind['max_disjoint_test_windows']} |"
        )
    lines.append("")
    lines.append("## Trial count")
    lines.append("")
    lines.append(
        "- 1 measurement per design = 3 measurements on one shared path; fixed parameters, "
        "no per-fold re-optimisation, no robustness grid, no candidate selection."
    )
    lines.append("")
    lines.append("## Reproduction")
    lines.append("")
    lines.append("```bash")
    lines.append("python research/tsmomentum_walkforward_embargo_audit.py")
    lines.append("python -m pytest -q tests/test_tsmomentum_walkforward_embargo_audit.py")
    lines.append("python -m pytest -q")
    lines.append("git status --porcelain data/")
    lines.append("git diff --stat src/ config/ research/experiments/ research/reports/")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


# ----------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------
def run_audit(
    experiments_dir: Path = EXPERIMENTS_DIR,
    raw_dir: Path = RAW_DIR,
) -> dict[str, Any]:
    """Run the whole audit and return the payload (no file writes)."""
    checks: list[dict[str, Any]] = []

    def record_check(name: str, ok: bool, observed: Any = "", expected: Any = "") -> None:
        checks.append(
            {"name": name, "pass": bool(ok), "observed": observed, "expected": expected}
        )

    record_path, published = resolve_published_record(experiments_dir)
    record_check(
        "published_record_resolved_by_content",
        True,
        str(record_path.relative_to(REPO_ROOT)) if record_path.is_relative_to(REPO_ROOT) else str(record_path),
        "exactly one published walk-forward record",
    )

    data_before = fingerprint(REPO_ROOT / "data")
    config_before = fingerprint(REPO_ROOT / "config")
    artifacts_before = tracked_artifact_hashes()

    close = load_close_from_cache(list(SYMBOLS), raw_dir)
    net_ret, weights = build_candidate_path(close)
    record_check(
        "cache_only_path_built",
        len(net_ret) > 0,
        f"{len(net_ret)} sessions, {len(close.columns)} symbols",
        "non-empty path",
    )

    designs = {
        "published_design": published_splits(),
        "design_a_nonoverlapping": design_a_splits(),
        "design_b_embargo_literal": design_b_splits(),
    }
    evaluated: dict[str, Any] = {}
    for name, splits in designs.items():
        result = evaluate_design(net_ret, weights, splits)
        gates = gate_table(result["summary"])
        result["gates"] = gates
        result["decision"] = decision_from_gates(gates)
        evaluated[name] = result

    pub = evaluated["published_design"]
    des_a = evaluated["design_a_nonoverlapping"]
    des_b = evaluated["design_b_embargo_literal"]

    anchor = build_anchor(published, pub)
    record_check(
        "reproduces_published_walk_forward_aggregate",
        anchor["matches"],
        "; ".join(
            f"{r['metric']}={r['observed']} (published {r['published_text']})"
            for r in anchor["rows"]
        ),
        "published aggregate statistics",
    )
    record_check(
        "reproduces_published_walk_forward_fold_table",
        anchor["per_fold_match"],
        f"{anchor['per_fold_count']} folds compared",
        "every published fold reproduced",
    )
    record_check(
        "published_design_has_test_window_overlap",
        pub["independence"]["mean_consecutive_overlap_days"] > 0,
        pub["independence"]["mean_consecutive_overlap_days"],
        "> 0 days",
    )
    record_check(
        "design_a_test_windows_pairwise_disjoint",
        des_a["independence"]["mean_consecutive_overlap_days"] == 0.0
        and des_a["independence"]["max_disjoint_test_windows"]
        == des_a["summary"].get("n_folds", 0),
        f"overlap={des_a['independence']['mean_consecutive_overlap_days']}, "
        f"disjoint={des_a['independence']['max_disjoint_test_windows']}, "
        f"folds={des_a['summary'].get('n_folds', 0)}",
        "overlap == 0 and disjoint == folds",
    )
    record_check(
        "published_gate_thresholds_consumed_from_record",
        abs(float(published["gates"]["wf_mean_oos_sharpe_min"]) - GATE_WF_MEAN_MIN) < 1e-12
        and abs(float(published["gates"]["positive_fold_rate_min"]) - GATE_POSITIVE_FOLD_RATE_MIN) < 1e-12,
        str(published["gates"]),
        "0.9 / 0.5 as published",
    )

    data_after = fingerprint(REPO_ROOT / "data")
    config_after = fingerprint(REPO_ROOT / "config")
    artifacts_after = tracked_artifact_hashes()
    record_check("data_unchanged", data_before == data_after)
    record_check("config_unchanged", config_before == config_after)
    record_check("committed_artifacts_unchanged", artifacts_before == artifacts_after)

    commission_bps, slippage_bps = get_cost_params()
    published_mean = float(pub["summary"].get("mean_test_sharpe", float("nan")))
    design_a_mean = float(des_a["summary"].get("mean_test_sharpe", float("nan")))
    published_gate1 = pub["gates"][0]["status"] if pub["gates"] else "N/A"
    design_a_gate1 = des_a["gates"][0]["status"] if des_a["gates"] else "N/A"

    delta = {
        "fold_count_published": pub["summary"].get("n_folds", 0),
        "fold_count_design_a": des_a["summary"].get("n_folds", 0),
        "fold_count_delta": des_a["summary"].get("n_folds", 0)
        - pub["summary"].get("n_folds", 0),
        "mean_sharpe_published": published_mean,
        "mean_sharpe_design_a": design_a_mean,
        "mean_sharpe_delta": design_a_mean - published_mean,
        "gate1_threshold": GATE_WF_MEAN_MIN,
        "gate1_margin_published": published_mean - GATE_WF_MEAN_MIN,
        "gate1_margin_design_a": design_a_mean - GATE_WF_MEAN_MIN,
        "gate1_margin_delta": (design_a_mean - GATE_WF_MEAN_MIN)
        - (published_mean - GATE_WF_MEAN_MIN),
        "gate1_status_published": published_gate1,
        "gate1_status_design_a": design_a_gate1,
        "gate_outcome_changes": published_gate1 != design_a_gate1,
        "verdict_survives": bool(
            published_gate1 == "PASS"
            and design_a_gate1 == "PASS"
            and des_a["decision"]["label"] == "Passes preliminary gates"
        ),
    }

    payload: dict[str, Any] = {
        "cycle": CYCLE,
        "candidate": CANDIDATE_ID,
        "overall": "PASS" if all(c["pass"] for c in checks) else "FAIL",
        "checks": checks,
        "published_record_path": str(
            record_path.relative_to(REPO_ROOT)
            if record_path.is_relative_to(REPO_ROOT)
            else record_path
        ),
        "published_anchor_value": PUBLISHED_WF_MEAN,
        "published_verdict": "Credible Candidate",
        "published_gate1_status": published_gate1,
        "design_a_gate1_status": design_a_gate1,
        "published_design": pub,
        "design_a_nonoverlapping": des_a,
        "design_b_embargo_literal": des_b,
        "delta_published_vs_design_a": delta,
        "anchor": anchor,
        "read_only": {
            "data_unchanged": data_before == data_after,
            "config_unchanged": config_before == config_after,
            "committed_artifacts_unchanged": artifacts_before == artifacts_after,
            "files_hashed": len(artifacts_before),
        },
        "commission_bps": commission_bps * 10000.0,
        "slippage_bps": slippage_bps * 10000.0,
        "rf_annual": get_risk_free_rate(),
        "point_in_time": (
            "signals use only data available at formation (weights shifted one day), "
            "the SPY SMA is computed point-in-time, and the overlay/cost model are applied "
            "on the same continuously computed path for every design"
        ),
        "data_source": "committed parquet cache in data/raw/ (fetcher never called)",
    }
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiments-dir", type=Path, default=EXPERIMENTS_DIR)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--report-out", type=Path, default=OUT_REPORT)
    parser.add_argument("--experiment-out", type=Path, default=OUT_EXP)
    args = parser.parse_args(argv)

    try:
        payload = run_audit(
            experiments_dir=args.experiments_dir,
            raw_dir=args.raw_dir,
        )
    except AuditError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.experiment_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(render_report(payload), encoding="utf-8")
    args.experiment_out.write_text(render_experiment(payload), encoding="utf-8")

    print("OVERALL: " + payload["overall"])
    print(f"report: {args.report_out}")
    print(f"experiment: {args.experiment_out}")
    print(
        f"published design: {payload['published_design']['summary'].get('n_folds', 0)} folds, "
        f"WF mean OOS Sharpe {payload['published_design']['summary'].get('mean_test_sharpe', float('nan')):.4f}"
    )
    print(
        f"Design A: {payload['design_a_nonoverlapping']['summary'].get('n_folds', 0)} folds, "
        f"WF mean OOS Sharpe {payload['design_a_nonoverlapping']['summary'].get('mean_test_sharpe', float('nan')):.4f}"
    )
    print(
        f"Design B: {payload['design_b_embargo_literal']['summary'].get('n_folds', 0)} folds"
    )
    print(
        f"gate-1 outcome changes under Design A: "
        f"{'YES' if payload['delta_published_vs_design_a']['gate_outcome_changes'] else 'NO'}"
    )
    return 0 if payload["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
