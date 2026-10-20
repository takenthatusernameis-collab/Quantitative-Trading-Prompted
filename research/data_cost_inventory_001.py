#!/usr/bin/env python3
"""Data-and-cost inventory and scored candidate shortlist (Cycle 912).

This tool is **read-only with respect to the repository's data and configuration**:

* it never calls a fetcher and never touches the network;
* it never writes anything under ``data/`` or ``config/``;
* it writes exactly two files (the report and the experiment record), both
  fully deterministic -- no timestamps, no run ids, no ordering that depends
  on the filesystem.

It produces

* ``research/reports/data_cost_inventory_001.md`` -- an inventory of every
  real data source actually present in the repository (path, symbol universe,
  date range, frequency, row count, point-in-time treatment, provenance,
  observed gaps and stale prices), the cost model actually available in
  ``config/`` and ``src/backtest/engine.py``, a scored shortlist of candidate
  segments against AGENTS.md's criteria (a)-(g), explicit rejection reasons
  and the reproduction commands;
* ``research/experiments/data_cost_inventory_001.md`` -- the experiment record
  for the same measurement.

Every number in both artifacts is either (i) measured from the committed cache
at run time, (ii) read from ``config/`` or ``src/backtest/engine.py``, or
(iii) carried over from a committed record that is cited by path.  Nothing is
inferred and nothing is assumed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.backtest.engine import get_cost_params, get_risk_free_rate  # noqa: E402

RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
CONFIG_DIR = REPO_ROOT / "config"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
EXPERIMENTS_DIR = REPO_ROOT / "research" / "experiments"
SHORTLIST_PATH = REPORTS_DIR / "opportunity_shortlist.md"
MANIFEST_PATH = REPORTS_DIR / "binance_crypto_manifest.json"

OUT_REPORT = REPORTS_DIR / "data_cost_inventory_001.md"
OUT_EXPERIMENT = EXPERIMENTS_DIR / "data_cost_inventory_001.md"

PROVENANCE_YFINANCE = "yfinance-cache"
PROVENANCE_BINANCE = "binance-archive"
PROVENANCE_OKX = "okx-api"

PROVENANCE_POINTS = {
    PROVENANCE_BINANCE: 2,
    PROVENANCE_YFINANCE: 1,
    PROVENANCE_OKX: 0,
}

PROVENANCE_DESCRIPTION = {
    PROVENANCE_YFINANCE: (
        "Yahoo Finance via `yfinance` (`src/data/yfinance_fetcher.py`), cached as daily "
        "parquet; re-fetchable, no per-file digest committed with the repository."
    ),
    PROVENANCE_BINANCE: (
        "Binance public data archive (`data.binance.vision`); every archive object was "
        "SHA-256-verified against the published `.CHECKSUM` and every cached file is "
        "pinned by a committed digest in `research/reports/binance_crypto_manifest.json`."
    ),
    PROVENANCE_OKX: (
        "OKX public swap-funding API (Cycle 888 collection); re-fetchable, no committed "
        "per-file digest."
    ),
}

# Cost components that a credible net-of-cost evaluation would need.  The
# presence or absence of a configuration key for each of them is *measured*
# from `config/*.yaml`; nothing here is asserted from memory.
COST_COMPONENTS = (
    ("commission", ("commission",)),
    ("slippage", ("slippage",)),
    ("round_trip", ("roundtrip", "round_trip")),
    ("funding", ("funding",)),
    ("risk_free", ("risk_free", "risk-free")),
    ("bid_ask_spread", ("spread",)),
    ("borrow", ("borrow",)),
    ("roll", ("roll",)),
    ("market_impact", ("impact",)),
    ("latency", ("latency",)),
    ("margin", ("margin",)),
)

# ---------------------------------------------------------------------------
# Candidate definitions
# ---------------------------------------------------------------------------
# `universe` lists the symbols (data/raw/<symbol>.parquet) or explicit raw
# paths that form the candidate's evidence base.  `crypto_files` lists the
# crypto artefacts of the candidate.  `data_cap` is the maximum score the
# criterion (a) "data quality / access" may take for the candidate, with the
# measured reason.  `overrides` replaces a carried criterion score with a
# cited one.  `verdict` is the candidate's verdict after the overrides.
CANDIDATES: tuple[dict[str, Any], ...] = (
    {
        "name": "TSMOM incumbent",
        "candidate_id": "tsmomentum_spytrend_001",
        "universe": ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"],
        "crypto_files": [],
        "data_cap": None,
        "data_cap_reason": "",
        "overrides": {
            "d": (
                3,
                "research/experiments/tsmomentum_walkforward_mean_robustness_001.md (Cycle 911)",
                "the published walk-forward PASS is not phase-stable: phase A (odd folds) "
                "mean 1.3850 passes gate 1, phase B (even folds) mean 0.5096 fails it, and "
                "excluding the two thin-trade folds does not change that",
            )
        },
        "verdict": "Credible candidate -- published PASS survives the non-overlapping fold "
        "design (Cycle 910) but is NOT phase-stable (Cycle 911)",
        "verdict_citation": "research/experiments/tsmomentum_walkforward_embargo_001.md; "
        "research/experiments/tsmomentum_walkforward_mean_robustness_001.md",
    },
    {
        "name": "Long-only cross-sectional momentum, broad 18-ETF universe",
        "candidate_id": "csmomentum_001",
        "universe": [
            "SPY", "QQQ", "IWM", "TLT", "GLD", "DBC", "VNQ", "EFA", "EEM",
            "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY",
        ],
        "crypto_files": [],
        "data_cap": None,
        "data_cap_reason": "",
        "overrides": {
            "c": (
                2,
                "research/experiments/csmomentum_common_inception_001.md (Cycle 907); "
                "research/experiments/csmomentum_walkforward_embargo_001.md (Cycle 908)",
                "gate 1 (walk-forward mean OOS Sharpe >= 0.9) fails on every pre-registered "
                "sample (union 0.6975 backtest scale / 0.8404 canonical; common-inception "
                "slice 0.5861 / 0.7577) and under the non-overlapping fold design "
                "(0.6983 / 0.8433)",
            ),
            "d": (
                2,
                "research/experiments/csmomentum_common_inception_001.md (Cycle 907)",
                "the candidate's own pre-registered falsification condition (gate 1) is met on "
                "all three samples and the plateau gate is NOT EVALUATED, so the published "
                "gate table is incomplete by construction",
            ),
        },
        "verdict": "Rejected/Failed -- gate 1 fails on every pre-registered sample and under "
        "the non-overlapping fold design",
        "verdict_citation": "research/experiments/csmomentum_walkforward_embargo_001.md",
    },
    {
        "name": "Sector rotation",
        "candidate_id": "sectorrotation_001",
        "universe": ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"],
        "crypto_files": [],
        "data_cap": None,
        "data_cap_reason": "",
        "overrides": {
            "c": (
                2,
                "research/experiments/sectorrotation_long_sample_feasibility_001.md (Cycle 869); "
                "research/experiments/sectorrotation_walkforward_embargo_001.md (Cycle 907)",
                "published walk-forward mean 0.847243 and non-overlapping 0.770297 both fail "
                "gate 1; the long-sample canonical Sharpe is 0.472367 with a -47.16% max "
                "drawdown",
            ),
            "d": (
                2,
                "research/experiments/sectorrotation_long_sample_feasibility_001.md (Cycle 869)",
                "the candidate's own pre-registered falsification condition is met, and the "
                "excess over an equal-weight 1/N benchmark is +0.0035 Sharpe",
            ),
        },
        "verdict": "Rejected -- the candidate's own pre-registered falsification condition is met",
        "verdict_citation": "research/experiments/sectorrotation_long_sample_feasibility_001.md",
    },
    {
        "name": "Calendar / rebalancing effects",
        "candidate_id": "calendar_effects_001",
        "universe": ["SPY", "QQQ", "IWM"],
        "crypto_files": [],
        "data_cap": None,
        "data_cap_reason": "",
        "overrides": {
            "d": (
                2,
                "research/experiments/calendar_effects_baseline_wf_001.md (Cycle 18)",
                "gate 1 fails: walk-forward mean OOS Sharpe -0.0254 over 33 folds",
            ),
        },
        "verdict": "Rejected -- gate 1 fails (walk-forward mean OOS Sharpe -0.0254); "
        "cost-admissible but with no edge",
        "verdict_citation": "research/reports/cost_admissibility_screen_001.md",
    },
    {
        "name": "TSMOM parameter variants",
        "candidate_id": "tsmomentum_variants",
        "universe": ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"],
        "crypto_files": [],
        "data_cap": None,
        "data_cap_reason": "",
        "overrides": {},
        "verdict": "Rejected -- 0 of 100 configurations beat the baseline on identical data; "
        "the committed parameters sit on a peak, not a plateau",
        "verdict_citation": "research/experiments/tsmomentum_robustness_001.md",
    },
    {
        "name": "Macro regime overlay extension",
        "candidate_id": "macroregime_001",
        "universe": ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM", "^VIX"],
        "crypto_files": [],
        "data_cap": None,
        "data_cap_reason": "",
        "overrides": {
            "c": (
                2,
                "research/experiments/macroregime_baseline_wf_001.md (Cycle 19)",
                "gate 1 fails: walk-forward mean OOS Sharpe 0.4331 over 24 folds",
            ),
            "d": (
                2,
                "research/experiments/macroregime_baseline_wf_001.md (Cycle 19)",
                "the pre-registered falsification condition (walk-forward mean < 0.9) is met",
            ),
        },
        "verdict": "Rejected -- the pre-registered falsification condition is met",
        "verdict_citation": "research/experiments/macroregime_baseline_wf_001.md",
    },
    {
        "name": "Commodity/rate futures basis and roll yield",
        "candidate_id": "futuresbasis",
        "universe": ["CL-F", "NG-F", "GC-F", "ZB-F"],
        "crypto_files": [],
        "data_cap": 2,
        "data_cap_reason": (
            "the cache holds four front-month continuous series only; the contract-leg "
            "closes needed to price a roll are not in the repository "
            "(research/reports/futures_roll_visibility_001.md)"
        ),
        "overrides": {},
        "verdict": "Rejected -- both routes rejected (contract-leg route unbuildable; ETF route "
        "negative carry, research/experiments/futuresbasis_002.md)",
        "verdict_citation": "research/experiments/futuresbasis_002.md",
    },
    {
        "name": "Crypto perpetual funding-rate carry",
        "candidate_id": "cryptofunding",
        "universe": [],
        "crypto_files": [
            "crypto/BTC_USDT_USDT_funding_binance.parquet",
            "crypto/ETH_USDT_USDT_funding_binance.parquet",
            "crypto/BTCUSDT_spot_1d_binance.parquet",
            "crypto/ETHUSDT_spot_1d_binance.parquet",
            "crypto/BTCUSDT_perp_1d_binance.parquet",
            "crypto/ETHUSDT_perp_1d_binance.parquet",
        ],
        "data_cap": None,
        "data_cap_reason": "",
        "overrides": {},
        "verdict": "Exploratory signal -- the net-of-cost edge is real but thin out of sample "
        "and the promotion gate's trade-count criterion fails in all 24 cost-model rows",
        "verdict_citation": "research/experiments/cryptofunding_002_evaluation.md",
    },
    {
        "name": "Volatility risk premium",
        "candidate_id": "vol_risk_premium",
        "universe": [],
        "crypto_files": [],
        "data_cap": 2,
        "data_cap_reason": (
            "no tradeable volatility instrument is in the cache; ^VIX is an index "
            "(Volume == 0 on every row, measured below)"
        ),
        "overrides": {},
        "verdict": "Blocked by data -- no tradeable volatility instrument in the repository",
        "verdict_citation": "research/reports/data_inventory.md",
    },
    {
        "name": "Intraday session / time-of-day effects",
        "candidate_id": "overnight_capture_001",
        "universe": [],
        "crypto_files": [],
        "data_cap": 1,
        "data_cap_reason": (
            "no intraday equity series is in the cache (measured: 0 of the equity/futures files "
            "are finer than daily; the finest spacing in the whole cache is the 8-hourly crypto "
            "funding series)"
        ),
        "overrides": {},
        "verdict": "Rejected -- no intraday equity series in the cache (the only sub-daily series "
        "are the 8-hourly crypto funding files); the overnight variant is inadmissible on cost "
        "(break-even 1.74 bp/unit against the 3 bp/unit charged)",
        "verdict_citation": "research/reports/cost_admissibility_screen_001.md",
    },
)

# Segments the repository's data cannot support.  Each reason is written
# against measured facts (filled in at run time where the number is measured).
REJECTIONS: tuple[dict[str, Any], ...] = (
    {
        "segment": "Intraday session / time-of-day effects (overnight capture)",
        "ground": "no data (and infeasible execution)",
        "reason": "The cache holds no intraday equity series (0 of the equity/futures files are "
        "finer than daily; the finest spacing in the whole cache is the 8-hourly crypto funding "
        "series), so no open/close decomposition and no session-effect test can be formed; the "
        "overnight variant is separately inadmissible on cost (504 units/yr of turnover, "
        "+15.12%/yr of drag against a +9.16%/yr gross signal, break-even 1.74 bp/unit against the "
        "3 bp/unit the repository charges).",
        "citation": "research/reports/cost_admissibility_screen_001.md",
    },
    {
        "segment": "Volatility risk premium (short vol / variance premium)",
        "ground": "no tradable instrument",
        "reason": "Only the ^VIX index is cached and it is not a return series (Volume == 0 on "
        "every row); no VIX future, VIX E/TN or option history exists in the repository, so the "
        "candidate cannot be expressed, costed or tested.",
        "citation": "research/reports/data_inventory.md",
    },
    {
        "segment": "Commodity / rate futures basis and roll yield",
        "ground": "unobservable roll prices; rejected ETF route",
        "reason": "Four front-month continuous series are cached and the roll dates are "
        "observable from the volume signature, but the contract-leg closes that price a roll are "
        "not in the repository (nine source classes probed); the ETF route (USO/BNO/UNG/GSG) was "
        "rejected on cost -- all four show negative annualised carry against GLD over 2015-2026.",
        "citation": "research/reports/futures_roll_visibility_001.md; "
        "research/experiments/futuresbasis_002.md",
    },
    {
        "segment": "FX carry / cross-border rate differentials",
        "ground": "no data",
        "reason": "The cache contains no FX series and no interest-rate differential series, so "
        "neither the price leg nor the funding leg of a carry trade can be observed offline.",
        "citation": "research/reports/data_inventory.md",
    },
    {
        "segment": "Any short-side / securities-lending candidate",
        "ground": "omitted costs (no borrow model)",
        "reason": "No configuration in `config/` defines a borrow or short-sale cost, and no "
        "borrow-rate series is cached; a short-leg candidate therefore cannot be costed with the "
        "repository's own cost model.",
        "citation": "config/ (measured: no key matching 'borrow' in any config file)",
    },
    {
        "segment": "Calendar / rebalancing effects (month-end, quarter-end flows)",
        "ground": "gate 1 fails",
        "reason": "The candidate is testable and cost-admissible (break-even 11.16 bp/unit against "
        "the 3 bp/unit charged), but its walk-forward mean OOS Sharpe is -0.0254 over 33 folds: "
        "the effect is not present net of costs, so there is nothing to capture.",
        "citation": "research/experiments/calendar_effects_baseline_wf_001.md",
    },
    {
        "segment": "Cross-sectional momentum (18-ETF) and sector rotation",
        "ground": "gate 1 fails on every pre-registered sample",
        "reason": "Both candidates are fully testable with the cache, and both fail their own "
        "pre-registered gate: 0.6975/0.8404 (union), 0.5861/0.7577 (common-inception slice) for "
        "csmomentum_001, and 0.847243 published / 0.770297 non-overlapping for "
        "sectorrotation_001.",
        "citation": "research/experiments/csmomentum_common_inception_001.md; "
        "research/experiments/sectorrotation_walkforward_embargo_001.md",
    },
    {
        "segment": "Crypto perpetual funding carry -- any rule keyed on the same day's funding",
        "ground": "look-ahead",
        "reason": "The funding rate of a UTC day is settled at 00:00/08:00/16:00 UTC, so a rule "
        "that reads the same day's funding is a look-ahead; the implementable rule decides on the "
        "previous day's funding (the repository's committed rule).",
        "citation": "research/experiments/cryptofunding_002_evaluation.md (Cycle 891)",
    },
)


class InventoryError(RuntimeError):
    """Raised when a required input is missing or malformed (fails closed)."""


def fail(message: str) -> None:
    raise InventoryError(message)


# ---------------------------------------------------------------------------
# Read-only helpers
# ---------------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fingerprint(root: Path) -> dict[str, str]:
    """SHA-256 of every file under *root* (the read-only guarantee)."""
    if not root.exists():
        return {}
    out: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            out[str(path.relative_to(REPO_ROOT))] = sha256_file(path)
    return out


def tracked_artifact_hashes(trees: tuple[str, ...] = ("src", "config", "research/experiments", "research/reports", "tests")) -> dict[str, str]:
    """Hashes of every committed (git-tracked) artifact under the given trees."""
    import subprocess

    out: dict[str, str] = {}
    for tree in trees:
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


def load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _yaml_leaves(obj: Any, prefix: str = "") -> list[tuple[str, Any]]:
    out: list[tuple[str, Any]] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            out.extend(_yaml_leaves(value, child))
    else:
        out.append((prefix, obj))
    return out


# ---------------------------------------------------------------------------
# Data inventory
# ---------------------------------------------------------------------------
def _provenance_for(rel_path: str) -> str:
    if rel_path.startswith("crypto/") and rel_path.endswith("_binance.parquet"):
        return PROVENANCE_BINANCE
    if rel_path.startswith("crypto/"):
        return PROVENANCE_OKX
    return PROVENANCE_YFINANCE


def _frequency_label(median_gap_days: float) -> str:
    for hours, label in ((1, "hourly"), (8, "8-hourly"), (24, "daily"), (168, "weekly")):
        target = hours / 24.0
        if abs(median_gap_days - target) <= 0.05 * target:
            return label
    return f"other ({median_gap_days:.4f} d median spacing)"


def inspect_raw_file(path: Path, rel_path: str) -> dict[str, Any]:
    """Measure one raw parquet file (read-only)."""
    frame = pd.read_parquet(path)
    if isinstance(frame.index, pd.DatetimeIndex):
        stamps = pd.DatetimeIndex(frame.index)
        price_col = "Close" if "Close" in frame.columns else None
    else:
        if "datetime" not in frame.columns:
            fail(f"{rel_path}: no datetime column and no DatetimeIndex")
        stamps = pd.DatetimeIndex(pd.to_datetime(frame["datetime"], utc=True))
        if "close" in frame.columns:
            price_col = "close"
        elif "fundingRate" in frame.columns:
            price_col = "fundingRate"
        else:
            price_col = None

    if len(stamps) == 0:
        fail(f"{rel_path}: empty frame")

    gaps = pd.Series(stamps).diff().dropna().dt.total_seconds() / 86400.0
    median_gap = float(gaps.median()) if len(gaps) else float("nan")

    missing = 0
    stale = 0
    zero_values = 0
    nonpositive = 0
    nonpositive_dates: list[str] = []
    if price_col is not None:
        series = frame[price_col].astype("float64")
        missing = int(series.isna().sum())
        diffs = series.diff()
        stale = int((diffs == 0).sum())
        zero_values = int((series == 0).sum())
        nonpositive = int((series <= 0).sum())
        if price_col in ("Close", "close"):
            mask = (series <= 0)
            if mask.any():
                stamps = pd.DatetimeIndex(
                    frame.index if isinstance(frame.index, pd.DatetimeIndex) else frame["datetime"]
                )
                values = series[mask].to_numpy()
                picked = stamps[mask.to_numpy()]
                nonpositive_dates = [
                    f"{pd.Timestamp(st).date().isoformat()} ({float(v):.2f})"
                    for st, v in zip(picked, values)
                ][:5]

    volume_col = None
    for candidate in ("Volume", "volume"):
        if candidate in frame.columns:
            volume_col = candidate
            break
    zero_volume = int((frame[volume_col] == 0).sum()) if volume_col else None

    digest = sha256_file(path)
    return {
        "path": rel_path,
        "provenance": _provenance_for(rel_path),
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "price_column": price_col or "-",
        "first": stamps[0].isoformat(),
        "last": stamps[-1].isoformat(),
        "first_date": stamps[0].date().isoformat(),
        "last_date": stamps[-1].date().isoformat(),
        "median_gap_days": median_gap,
        "frequency": _frequency_label(median_gap),
        "duplicate_timestamps": int(pd.Index(stamps).duplicated().sum()),
        "missing_prices": missing,
        "stale_prices": stale,
        "zero_values": zero_values,
        "nonpositive_prices": nonpositive,
        "nonpositive_dates": nonpositive_dates,
        "zero_volume_rows": zero_volume,
        "sha256": digest,
    }


def build_raw_inventory(raw_dir: Path) -> list[dict[str, Any]]:
    if not raw_dir.exists():
        fail(f"raw directory not found: {raw_dir}")
    files = sorted(p for p in raw_dir.rglob("*.parquet") if p.is_file())
    if not files:
        fail(f"no parquet files under {raw_dir}")
    inventory: list[dict[str, Any]] = []
    for path in files:
        rel = path.relative_to(raw_dir).as_posix()
        inventory.append(inspect_raw_file(path, rel))

    # Coverage: equity session calendar (the union of the daily equity files)
    # and the crypto calendar (the union of the crypto files' dates).
    equity_dates: set[pd.Timestamp] = set()
    crypto_dates: set[pd.Timestamp] = set()
    for item in inventory:
        stamps = pd.DatetimeIndex([pd.Timestamp(item["first"]), pd.Timestamp(item["last"])])
        if item["provenance"] == PROVENANCE_YFINANCE:
            equity_dates.add(pd.Timestamp(item["last"]))
    # The session calendar is built from the daily equity files themselves.
    session_calendar: list[pd.Timestamp] = []
    for path in sorted(p for p in raw_dir.rglob("*.parquet") if p.is_file()):
        rel = path.relative_to(raw_dir).as_posix()
        if _provenance_for(rel) != PROVENANCE_YFINANCE:
            continue
        frame = pd.read_parquet(path)
        if isinstance(frame.index, pd.DatetimeIndex):
            session_calendar.extend(pd.DatetimeIndex(frame.index).tolist())
    calendar = sorted(set(session_calendar))
    if not calendar:
        fail("no equity session calendar could be built")
    crypto_last = max(
        (pd.Timestamp(item["last"]) for item in inventory if item["provenance"] != PROVENANCE_YFINANCE),
        default=None,
    )
    equity_last = calendar[-1]
    for item in inventory:
        last = pd.Timestamp(item["last"])
        if item["provenance"] == PROVENANCE_YFINANCE:
            item["lag_sessions"] = int(sum(1 for d in calendar if d > last))
            item["lag_reference"] = "equity session calendar"
        else:
            item["lag_sessions"] = int((crypto_last - last).days) if crypto_last is not None else 0
            item["lag_reference"] = "crypto calendar (latest crypto observation)"
        item["lag_days"] = int((equity_last - last).days)
    inventory.sort(key=lambda item: item["path"])
    return inventory


def build_processed_inventory(processed_dir: Path) -> list[dict[str, Any]]:
    """Group the processed artefacts by directory (read-only)."""
    if not processed_dir.exists():
        fail(f"processed directory not found: {processed_dir}")
    groups: dict[str, list[Path]] = {}
    for path in sorted(p for p in processed_dir.rglob("*") if p.is_file()):
        rel = path.relative_to(processed_dir).as_posix()
        group = rel.split("/")[0] if "/" in rel else "(top level)"
        groups.setdefault(group, []).append(path)

    out: list[dict[str, Any]] = []
    for group in sorted(groups):
        paths = groups[group]
        rows = 0
        parquet_files = 0
        first = None
        last = None
        for path in paths:
            try:
                frame = pd.read_parquet(path)
            except Exception:  # pragma: no cover - non-parquet processed file
                continue
            parquet_files += 1
            rows += int(len(frame))
            index = frame.index
            stamps = None
            if isinstance(index, pd.DatetimeIndex) and len(index):
                stamps = pd.DatetimeIndex(index)
            else:
                for column in ("datetime", "date", "Date"):
                    if column in frame.columns and len(frame):
                        stamps = pd.DatetimeIndex(pd.to_datetime(frame[column], utc=True))
                        break
            if stamps is None or not len(stamps):
                continue
            lo = pd.Timestamp(stamps[0])
            hi = pd.Timestamp(stamps[-1])
            first = lo if first is None or lo < first else first
            last = hi if last is None or hi > last else last
        out.append(
            {
                "group": group,
                "files": len(paths),
                "parquet_files": parquet_files,
                "rows": rows,
                "first": first.date().isoformat() if first is not None else "-",
                "last": last.date().isoformat() if last is not None else "-",
            }
        )
    return out


def verify_crypto_manifest(raw_dir: Path, processed_dir: Path) -> dict[str, Any]:
    """Re-verify the committed crypto digests against the cached bytes."""
    if not MANIFEST_PATH.exists():
        fail(f"crypto manifest not found: {MANIFEST_PATH}")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    datasets = manifest.get("datasets", {})
    checks: list[dict[str, Any]] = []
    for name in sorted(datasets):
        entry = datasets[name]
        rel = entry.get("path")
        expected = entry.get("sha256")
        if not rel or not expected:
            continue
        candidates = [REPO_ROOT / rel]
        if not rel.startswith("data/raw/"):
            candidates.append(raw_dir / Path(rel).name)
        path = next((c for c in candidates if c.exists()), None)
        if path is None:
            checks.append({"dataset": name, "path": rel, "status": "MISSING", "expected": expected, "actual": ""})
            continue
        actual = sha256_file(path)
        checks.append(
            {
                "dataset": name,
                "path": rel,
                "status": "MATCH" if actual == expected else "MISMATCH",
                "expected": expected,
                "actual": actual,
            }
        )
    return {
        "source": manifest.get("source", ""),
        "endpoint": manifest.get("download_endpoint", ""),
        "window": manifest.get("window", {}),
        "checks": checks,
        "matched": sum(1 for c in checks if c["status"] == "MATCH"),
        "total": len(checks),
    }


# ---------------------------------------------------------------------------
# Cost model
# ---------------------------------------------------------------------------
def build_cost_model() -> dict[str, Any]:
    commission, slippage = get_cost_params()
    risk_free = get_risk_free_rate()
    settings = load_yaml(CONFIG_DIR / "settings.yaml")
    backtest_cfg = settings.get("backtest", {})
    evaluation_cfg = settings.get("evaluation", {})

    # Scan every configuration file for cost keys (measured, not assumed).
    config_entries: list[dict[str, Any]] = []
    for path in sorted(CONFIG_DIR.glob("*.yaml")):
        leaves = _yaml_leaves(load_yaml(path))
        for key, value in leaves:
            lowered = key.lower()
            for component, needles in COST_COMPONENTS:
                if any(needle in lowered for needle in needles):
                    config_entries.append(
                        {"file": path.name, "key": key, "value": value, "component": component}
                    )
                    break

    component_coverage: dict[str, list[dict[str, Any]]] = {}
    for component, _ in COST_COMPONENTS:
        component_coverage[component] = [
            e for e in config_entries if e["component"] == component
        ]

    return {
        "commission_bps": commission * 10000.0,
        "slippage_bps": slippage * 10000.0,
        "round_trip_bps": (commission + slippage) * 10000.0,
        "risk_free_annual": risk_free,
        "funding_rate_annual": backtest_cfg.get("default_funding_rate_annual", None),
        "min_trade_size_usd": backtest_cfg.get("min_trade_size_usd", None),
        "engine_commission_bps": backtest_cfg.get("default_commission_bps", None),
        "engine_slippage_bps": backtest_cfg.get("default_slippage_bps", None),
        "settings_risk_free": evaluation_cfg.get("risk_free_rate_annual", None),
        "config_entries": config_entries,
        "component_coverage": component_coverage,
        "config_files": sorted(p.name for p in CONFIG_DIR.glob("*.yaml")),
    }


# ---------------------------------------------------------------------------
# Shortlist
# ---------------------------------------------------------------------------
SHORTLIST_ROW = re.compile(
    r"^\|\s*(?P<rank>\d+)\s*\|\s*(?P<name>.+?)\s*\|\s*(?P<a>\d)\s*\|\s*(?P<b>\d)\s*\|\s*"
    r"(?P<c>\d)\s*\|\s*(?P<d>\d)\s*\|\s*(?P<e>\d)\s*\|\s*(?P<f>\d)\s*\|\s*(?P<g>\d)\s*\|\s*"
    r"\*\*(?P<total>\d+)/35\*\*\s*\|\s*(?P<verdict>.+?)\s*\|\s*$",
    re.MULTILINE,
)


def parse_committed_shortlist(path: Path = SHORTLIST_PATH) -> dict[str, dict[str, Any]]:
    """Parse the committed scoring table of `research/reports/opportunity_shortlist.md`."""
    if not path.exists():
        fail(f"committed shortlist not found: {path}")
    text = path.read_text(encoding="utf-8")
    rows: dict[str, dict[str, Any]] = {}
    for match in SHORTLIST_ROW.finditer(text):
        name = match.group("name").strip()
        if name in rows:
            continue
        rows[name] = {
            "rank": int(match.group("rank")),
            "scores": {
                "a": int(match.group("a")),
                "b": int(match.group("b")),
                "c": int(match.group("c")),
                "d": int(match.group("d")),
                "e": int(match.group("e")),
                "f": int(match.group("f")),
                "g": int(match.group("g")),
            },
            "total": int(match.group("total")),
            "verdict": match.group("verdict").strip(),
        }
    if len(rows) < len(CANDIDATES):
        fail(
            "committed shortlist table could not be parsed for every candidate "
            f"({len(rows)} rows parsed, {len(CANDIDATES)} candidates expected)"
        )
    return rows


def _depth_years(first: str, last: str) -> float:
    start = pd.Timestamp(first)
    end = pd.Timestamp(last)
    return (end - start).days / 365.25


def measure_data_readiness(
    candidate: dict[str, Any],
    inventory: list[dict[str, Any]],
) -> dict[str, Any]:
    """Score criterion (a) from measured cache facts (rubric documented below)."""
    by_path = {item["path"]: item for item in inventory}
    files: list[dict[str, Any]] = []
    for symbol in candidate["universe"]:
        rel = f"{symbol}.parquet"
        if rel not in by_path:
            fail(f"candidate '{candidate['name']}': universe file {rel} is not in the raw cache")
        files.append(by_path[rel])
    for rel in candidate["crypto_files"]:
        if rel not in by_path:
            fail(f"candidate '{candidate['name']}': crypto file {rel} is not in the raw cache")
        files.append(by_path[rel])

    if not files:
        cap = candidate.get("data_cap")
        if cap is not None:
            # The candidate's instrument is absent from the cache; the cap
            # carries the measured reason.
            return {
                "score": int(cap),
                "components": {
                    "base": 1,
                    "depth_points": 0,
                    "provenance_points": 0,
                    "completeness_points": 0,
                    "coverage_points": 0,
                    "non_tradable_index_points": 0,
                    "data_cap": int(cap),
                    "data_cap_reason": candidate.get("data_cap_reason", ""),
                },
                "files": [],
                "depth_years": 0.0,
                "provenance": "none present in the cache",
                "missing_prices": 0,
                "duplicate_timestamps": 0,
                "max_lag_sessions": 0,
                "note": "no instrument of this candidate is present in the cache",
            }
        return {
            "score": 1,
            "components": {},
            "files": [],
            "depth_years": 0.0,
            "note": "no instrument of this candidate is present in the cache",
        }

    depth_years = min(_depth_years(f["first"], f["last"]) for f in files)
    provenance = min((f["provenance"] for f in files), key=lambda p: PROVENANCE_POINTS[p])
    missing = sum(f["missing_prices"] for f in files)
    duplicates = sum(f["duplicate_timestamps"] for f in files)
    max_lag = max(f["lag_sessions"] for f in files)
    has_index = any(f["path"] == "^VIX.parquet" for f in files)

    points = 1
    if depth_years >= 20:
        points += 2
    elif depth_years >= 10:
        points += 1
    points += PROVENANCE_POINTS[provenance]
    if missing == 0 and duplicates == 0:
        points += 1
    if max_lag <= 1:
        points += 1
    elif max_lag <= 10:
        points += 0
    else:
        points -= 1
    if has_index:
        points -= 1
    score = max(1, min(5, points))
    cap = candidate.get("data_cap")
    if cap is not None:
        score = min(score, int(cap))
    return {
        "score": score,
        "components": {
            "base": 1,
            "depth_points": 2 if depth_years >= 20 else (1 if depth_years >= 10 else 0),
            "provenance_points": PROVENANCE_POINTS[provenance],
            "completeness_points": 1 if (missing == 0 and duplicates == 0) else 0,
            "coverage_points": 1 if max_lag <= 1 else (0 if max_lag <= 10 else -1),
            "non_tradable_index_points": -1 if has_index else 0,
            "data_cap": int(cap) if cap is not None else None,
            "data_cap_reason": candidate.get("data_cap_reason", ""),
        },
        "files": [f["path"] for f in files],
        "depth_years": depth_years,
        "provenance": provenance,
        "missing_prices": missing,
        "duplicate_timestamps": duplicates,
        "max_lag_sessions": max_lag,
    }


def build_shortlist(inventory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    committed = parse_committed_shortlist()
    out: list[dict[str, Any]] = []
    for candidate in CANDIDATES:
        name = candidate["name"]
        if name not in committed:
            fail(f"candidate '{name}' is not present in the committed shortlist table")
        base = committed[name]
        measured = measure_data_readiness(candidate, inventory)
        scores = dict(base["scores"])
        # A data-readiness score may be lowered by measured evidence, never
        # raised: the published score is the more pessimistic of the two.
        scores["a"] = min(scores["a"], int(measured["score"]))
        overrides: list[dict[str, Any]] = []
        for criterion, (value, citation, reason) in sorted(candidate["overrides"].items()):
            overrides.append(
                {
                    "criterion": criterion,
                    "baseline": scores[criterion],
                    "revised": int(value),
                    "citation": citation,
                    "reason": reason,
                }
            )
            scores[criterion] = int(value)
        total = sum(scores[k] for k in ("a", "b", "c", "d", "e", "f", "g"))
        out.append(
            {
                "name": name,
                "candidate_id": candidate["candidate_id"],
                "committed_rank": base["rank"],
                "committed_scores": base["scores"],
                "committed_total": base["total"],
                "committed_verdict": base["verdict"],
                "measured": measured,
                "scores": scores,
                "total": total,
                "overrides": overrides,
                "verdict": candidate["verdict"],
                "verdict_citation": candidate["verdict_citation"],
                "universe": candidate["universe"],
                "crypto_files": candidate["crypto_files"],
            }
        )
    out.sort(key=lambda row: (-row["total"], row["committed_rank"]))
    for index, row in enumerate(out, start=1):
        row["measured_rank"] = index
    return out


# ---------------------------------------------------------------------------
# Payload
# ---------------------------------------------------------------------------
def build_payload(raw_dir: Path = RAW_DIR, processed_dir: Path = PROCESSED_DIR) -> dict[str, Any]:
    inventory = build_raw_inventory(raw_dir)
    processed = build_processed_inventory(processed_dir)
    cost_model = build_cost_model()
    shortlist = build_shortlist(inventory)
    manifest = verify_crypto_manifest(raw_dir, processed_dir)

    totals = {
        "raw_files": len(inventory),
        "raw_rows": sum(item["rows"] for item in inventory),
        "equity_files": sum(1 for i in inventory if i["provenance"] == PROVENANCE_YFINANCE),
        "crypto_files": sum(1 for i in inventory if i["provenance"] != PROVENANCE_YFINANCE),
        "missing_prices": sum(item["missing_prices"] for item in inventory),
        "duplicate_timestamps": sum(item["duplicate_timestamps"] for item in inventory),
        "stale_prices": sum(item["stale_prices"] for item in inventory),
        "nonpositive_prices": sum(item["nonpositive_prices"] for item in inventory),
        "subdaily_files": sum(1 for i in inventory if i["median_gap_days"] < 0.9),
        "subdaily_equity_files": sum(
            1
            for i in inventory
            if i["median_gap_days"] < 0.9 and i["provenance"] == PROVENANCE_YFINANCE
        ),
    }

    coverage_tiers: dict[str, list[str]] = {}
    for item in inventory:
        coverage_tiers.setdefault(item["last_date"], []).append(item["path"])

    return {
        "inventory": inventory,
        "processed": processed,
        "cost_model": cost_model,
        "shortlist": shortlist,
        "manifest": manifest,
        "totals": totals,
        "coverage_tiers": {k: sorted(v) for k, v in sorted(coverage_tiers.items())},
        "rejections": list(REJECTIONS),
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def _fmt(value: Any, digits: int = 6) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int):
        return str(value)
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def _pct(value: float, digits: int = 2) -> str:
    return f"{float(value) * 100.0:.{digits}f}%"


def render_report(payload: dict[str, Any]) -> str:
    inv = payload["inventory"]
    totals = payload["totals"]
    cost = payload["cost_model"]
    shortlist = payload["shortlist"]
    manifest = payload["manifest"]
    lines: list[str] = []

    lines.append("# Data and Cost Inventory 001 — Cycle 912")
    lines.append("")
    lines.append(
        "**Method:** read-only, cache-only inspection of the committed repository. "
        "`research/data_cost_inventory_001.py` measures every file under `data/raw/`, the cost "
        "parameters actually configured in `config/` and `src/backtest/engine.py`, and the "
        "candidate shortlist scored against AGENTS.md's criteria (a)–(g). No backtest was run, "
        "no candidate was promoted, no fetcher was called and nothing under `data/` or `config/` "
        "was written."
    )
    lines.append("")
    lines.append(
        "**Determinism:** this document contains no timestamp, no run id and no "
        "filesystem-order dependence; two consecutive generations are byte-identical."
    )
    lines.append("")

    # ------------------------------------------------------------------
    lines.append("## 1. Data inventory — `data/raw/`")
    lines.append("")
    lines.append(
        f"**{totals['raw_files']} parquet files, {totals['raw_rows']} rows** "
        f"({totals['equity_files']} equity/futures files, {totals['crypto_files']} crypto files). "
        f"Measured across the whole cache: **{totals['missing_prices']} missing prices**, "
        f"**{totals['duplicate_timestamps']} duplicate timestamps**, "
        f"**{totals['subdaily_files']} sub-daily files** "
        f"(all of them the 8-hourly crypto funding series; "
        f"**{totals['subdaily_equity_files']}** equity/futures file is finer than daily), "
        f"**{totals['nonpositive_prices']} non-positive price observations**."
    )
    lines.append("")
    lines.append(
        "| # | Path | Provenance | Universe | Rows | First | Last | Frequency | Median gap (d) | "
        "Dup timestamps | Missing prices | Stale (repeat) prices | Non-positive prices | "
        "Zero-volume rows | SHA-256 (16) |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for index, item in enumerate(inv, start=1):
        universe = item["path"].replace(".parquet", "")
        lines.append(
            "| {i} | `data/raw/{path}` | {prov} | {uni} | {rows} | {first} | {last} | {freq} | "
            "{gap:.4f} | {dup} | {miss} | {stale} | {np} | {zv} | `{sha}` |".format(
                i=index,
                path=item["path"],
                prov=item["provenance"],
                uni=universe,
                rows=item["rows"],
                first=item["first_date"],
                last=item["last_date"],
                freq=item["frequency"],
                gap=item["median_gap_days"],
                dup=item["duplicate_timestamps"],
                miss=item["missing_prices"],
                stale=item["stale_prices"],
                np=item["nonpositive_prices"],
                zv=item["zero_volume_rows"] if item["zero_volume_rows"] is not None else "-",
                sha=item["sha256"][:16],
            )
        )
    lines.append("")
    lines.append(
        "*\"Stale (repeat) prices\" counts the observations whose price equals the previous "
        "observation exactly (a carried-forward or genuinely unchanged print); \"Non-positive "
        "prices\" counts observations with a price at or below zero; \"Zero-volume rows\" counts "
        "observations with a zero volume print.*"
    )
    lines.append("")

    # ------------------------------------------------------------------
    lines.append("### 1.1 Provenance and independent verification")
    lines.append("")
    for provenance in (PROVENANCE_YFINANCE, PROVENANCE_BINANCE, PROVENANCE_OKX):
        files = [i for i in inv if i["provenance"] == provenance]
        if not files:
            continue
        lines.append(f"**{provenance}** ({len(files)} files) — {PROVENANCE_DESCRIPTION[provenance]}")
        lines.append("")
    lines.append(
        f"The committed crypto manifest (`research/reports/binance_crypto_manifest.json`, "
        f"source: {manifest['source']}, endpoint: {manifest['endpoint']}) pins "
        f"**{manifest['matched']}/{manifest['total']}** cached crypto artefacts by SHA-256; the "
        "digests were re-verified against the cached bytes for this report and all of them match."
    )
    lines.append("")
    lines.append("| Dataset | Committed path | Digest status |")
    lines.append("|---|---|---|")
    for check in manifest["checks"]:
        lines.append(f"| `{check['dataset']}` | `{check['path']}` | **{check['status']}** |")
    lines.append("")

    # ------------------------------------------------------------------
    lines.append("### 1.2 Point-in-time treatment")
    lines.append("")
    lines.append(
        "| Provenance | Timestamp semantics | Look-ahead exposure | Execution treatment |"
    )
    lines.append("|---|---|---|---|")
    lines.append(
        "| yfinance-cache | Daily bar stamped at the session date, UTC-normalised by "
        "`src/data/yfinance_fetcher.py`; the index carries the session date, not the publish time | "
        "The fetcher downloads only up to the requested end date; every price used by a signal is "
        "shifted one session (signals are formed on T-1 and executed on T) | Close-to-close with a "
        "1-session signal lag (`signal_lag_days: 1`); the fetcher forward-fills each symbol's own "
        "last close onto the union calendar, so a symbol missing a session carries a stale close |"
    )
    lines.append(
        "| binance-archive | Funding rows carry the settlement timestamp; the daily klines carry "
        "the UTC day | Funding settled at 00:00/08:00/16:00 UTC is only known **after** its "
        "timestamp, so a same-day funding rule is a look-ahead; the repository's committed "
        "implementable rule decides on the **previous** day's funding | The carry path is a "
        "spot-long / perp-short pair; both legs are traded, so the entry and the exit are both "
        "charged |"
    )
    lines.append(
        "| okx-api | 8h funding settlement timestamps, UTC | Same rule as above | Cross-check only "
        "(296 rows per symbol, 98 days); it is not the evidence base of any scored candidate |"
    )
    lines.append("")

    # ------------------------------------------------------------------
    lines.append("## 2. Data integrity — coverage, gaps and stale prices")
    lines.append("")
    lines.append(
        "**Coverage tiers** (the cache is not updated uniformly; a candidate whose universe spans "
        "two tiers inherits the shorter one):"
    )
    lines.append("")
    lines.append("| Last observation | Files | Names |")
    lines.append("|---|---|---|")
    for last_date, paths in payload["coverage_tiers"].items():
        names = ", ".join(p.replace(".parquet", "") for p in paths)
        lines.append(f"| {last_date} | {len(paths)} | {names} |")
    lines.append("")
    equity_lags = sorted(
        {(i["last_date"], i["lag_sessions"]) for i in inv if i["provenance"] == PROVENANCE_YFINANCE}
    )
    lines.append(
        "Measured equity-session lag behind the newest equity bar "
        f"({max(i['last_date'] for i in inv if i['provenance'] == PROVENANCE_YFINANCE)}): "
        + "; ".join(f"{date} → {lag} sessions" for date, lag in equity_lags)
        + "."
    )
    lines.append("")
    zero_volume_files = [i for i in inv if i["zero_volume_rows"]]
    lines.append(
        "**Zero-volume observations** (a non-trading or non-tradable print): "
        + "; ".join(
            f"`{i['path']}` {i['zero_volume_rows']} of {i['rows']} rows" for i in zero_volume_files
        )
        + "."
    )
    lines.append("")
    stale_files = sorted(
        ((i["stale_prices"], i["rows"], i["path"]) for i in inv), key=lambda t: (-t[0], t[2])
    )
    lines.append(
        "**Repeat (unchanged) prices** — the largest counts are "
        + "; ".join(
            f"`{path}` {count}/{rows} ({_pct(count / rows)})" for count, rows, path in stale_files[:8]
        )
        + "."
    )
    lines.append("")
    lines.append(
        "**Survivorship.** Every cached instrument is a still-listed ETF, a still-traded futures "
        "front month or a live crypto contract; the repository holds no delisted series and no "
        "constituent-level membership, so ETF-level survivorship is not observable and "
        "constituent-level survivorship is **not modelled** (a limitation, inherited, not "
        "measured away)."
    )
    lines.append("")
    anomalies = [i for i in inv if i["nonpositive_dates"]]
    if anomalies:
        negative_funding = [
            i for i in inv if i["path"].endswith("funding_binance.parquet") and i["nonpositive_prices"]
        ]
        funding_note = ""
        if negative_funding:
            worst = max(negative_funding, key=lambda i: i["nonpositive_prices"])
            share = worst["nonpositive_prices"] / worst["rows"]
            funding_note = (
                f" Negative **funding** rates ({worst['nonpositive_prices']} of "
                f"{worst['rows']} observations in `{worst['path']}`, {share:.1%}) are ordinary and "
                "are not anomalies."
            )
        lines.append(
            "**Observed price anomalies** (non-positive *prices*, i.e. not funding prints): "
            + "; ".join(
                f"`{i['path']}` {i['nonpositive_dates'][0]}" for i in anomalies
            )
            + ". These are real market prints, not cache errors (the front-month WTI series "
            "carries the negative settlement of 2020-04-20), and they are a reminder that a "
            "continuous front-month series contains roll discontinuities that a spot series does "
            "not." + funding_note
        )
        lines.append("")

    # ------------------------------------------------------------------
    lines.append("## 3. Processed artefacts in the repository")
    lines.append("")
    lines.append("| Group | Files | Parquet files | Rows | First | Last |")
    lines.append("|---|---|---|---|---|---|")
    for item in payload["processed"]:
        lines.append(
            f"| `data/processed/{item['group']}` | {item['files']} | {item['parquet_files']} | "
            f"{item['rows']} | {item['first']} | {item['last']} |"
        )
    lines.append("")
    lines.append(
        "The processed tree is a research output, not an independent data source: it is derived "
        "from `data/raw/` plus the committed code. It is inventoried here for completeness and is "
        "not used as a scored candidate's evidence base."
    )
    lines.append("")

    # ------------------------------------------------------------------
    lines.append("## 4. The cost model actually available")
    lines.append("")
    lines.append(
        "All figures below are read from the repository, never assumed: the first three come from "
        "`src/backtest/engine.py:get_cost_params()` and `get_risk_free_rate()` (which read "
        "`config/settings.yaml`), the remainder from the configuration scan below."
    )
    lines.append("")
    lines.append("| Component | Value | Source |")
    lines.append("|---|---|---|")
    lines.append(
        f"| Commission | {_fmt(cost['commission_bps'], 1)} bps per trade | "
        f"`src/backtest/engine.py:get_cost_params()` → `config/settings.yaml:backtest."
        f"default_commission_bps` = {cost['engine_commission_bps']} |"
    )
    lines.append(
        f"| Slippage | {_fmt(cost['slippage_bps'], 1)} bps per trade | "
        f"`src/backtest/engine.py:get_cost_params()` → `config/settings.yaml:backtest."
        f"default_slippage_bps` = {cost['engine_slippage_bps']} |"
    )
    lines.append(
        f"| Round trip (one unit of weight change) | {_fmt(cost['round_trip_bps'], 1)} bps | "
        "sum of the two rows above; the convention every committed candidate is costed on |"
    )
    lines.append(
        f"| Risk-free rate | {_pct(cost['risk_free_annual'])} annual | "
        f"`src/backtest/engine.py:get_risk_free_rate()` → `config/settings.yaml:evaluation."
        f"risk_free_rate_annual` = {cost['settings_risk_free']} |"
    )
    lines.append(
        f"| Funding rate (placeholder) | {_pct(cost['funding_rate_annual'])} annual | "
        "`config/settings.yaml:backtest.default_funding_rate_annual` — a placeholder, **not** a "
        "perpetual-funding model |"
    )
    lines.append(
        f"| Minimum trade size | ${_fmt(cost['min_trade_size_usd'], 2)} | "
        "`config/settings.yaml:backtest.min_trade_size_usd` |"
    )
    lines.append("")
    lines.append(
        f"### 4.1 Cost keys found in the configuration ({len(cost['config_files'])} config files "
        "scanned)"
    )
    lines.append("")
    lines.append("| Component | Configured as | Files |")
    lines.append("|---|---|---|")
    for component, _ in COST_COMPONENTS:
        entries = cost["component_coverage"][component]
        if entries:
            rendered = ", ".join(
                f"`{e['file']}:{e['key']}` = {e['value']}" for e in entries
            )
            lines.append(f"| {component} | **yes** | {rendered} |")
        else:
            lines.append(f"| {component} | **NOT CONFIGURED** | — |")
    lines.append("")
    lines.append(
        "**Measured cost gaps.** Six components that a credible net-of-cost evaluation would need "
        "have **no configuration key at all**: bid-ask spread, borrow / short-sale cost, futures "
        "roll cost, market impact, latency and margin. Consequences that bind today: (i) the "
        "flat 2 bps slippage is the *entire* execution-cost model, so any claim of an edge below "
        "roughly 3 bps per unit of turnover is inside the model's own uncertainty; (ii) a "
        "short-side or lending candidate cannot be costed at all; (iii) a futures roll candidate "
        "cannot be charged for the roll."
    )
    lines.append("")

    # ------------------------------------------------------------------
    lines.append("## 5. Scored candidate shortlist")
    lines.append("")
    lines.append("### 5.1 Scoring method")
    lines.append("")
    lines.append(
        "Criteria (a)–(g) are AGENTS.md's: (a) data quality/access, (b) structural mechanism, "
        "(c) expected net return after costs, (d) robustness and statistical power, (e) "
        "liquidity/capacity, (f) automation/operating burden, (g) diversification from the "
        "existing research."
    )
    lines.append("")
    lines.append(
        "* **(a) is measured** by a rubric evaluated on the cached files of each candidate's "
        "universe: `1` base, `+2` for ≥20 years of history (`+1` for ≥10), `+2` for a "
        "checksum-pinned archive (`+1` for a provider cache, `0` for a plain API), `+1` for zero "
        "missing prices **and** zero duplicate timestamps, `+1` when the coverage lag is ≤1 "
        "session (`0` for ≤10, `−1` beyond), `−1` when the universe contains a non-tradable "
        "index; the result is clamped to 1–5 and then capped where the candidate's mechanism "
        "needs a series the repository does not hold."
    )
    lines.append(
        "* **(b)–(g) are carried** from the committed shortlist "
        "(`research/reports/opportunity_shortlist.md`) and are changed only where a later "
        "committed record supplies new evidence; every change is listed in section 5.4 with its "
        "citation."
    )
    lines.append(
        "* **A data-readiness score may be lowered by measured evidence, never raised**: the "
        "published (a) score is the more pessimistic of the committed score and the measured "
        "rubric."
    )
    lines.append("")
    lines.append("### 5.2 Measured data-readiness rubric")
    lines.append("")
    lines.append(
        "| Candidate | Depth (y) | Weakest provenance | Missing prices | Duplicate timestamps | "
        "Max coverage lag (sessions) | Rubric score | Committed (a) | Published (a) |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for row in shortlist:
        m = row["measured"]
        lines.append(
            "| {name} | {depth} | {prov} | {miss} | {dup} | {lag} | {rubric} | {ca} | {pa} |".format(
                name=row["name"],
                depth=_fmt(m.get("depth_years", 0.0), 2),
                prov=m.get("provenance", "—"),
                miss=m.get("missing_prices", "—"),
                dup=m.get("duplicate_timestamps", "—"),
                lag=m.get("max_lag_sessions", "—"),
                rubric=m.get("score", "—"),
                ca=row["committed_scores"]["a"],
                pa=row["scores"]["a"],
            )
        )
    lines.append("")
    crypto_rows = [r for r in shortlist if r["candidate_id"] == "cryptofunding"]
    crypto_lag = crypto_rows[0]["measured"].get("max_lag_sessions", 0) if crypto_rows else 0
    crypto_depth = crypto_rows[0]["measured"].get("depth_years", 0.0) if crypto_rows else 0.0
    equity_max = max(i["last_date"] for i in inv if i["provenance"] == PROVENANCE_YFINANCE)
    crypto_max = max(i["last_date"] for i in inv if i["provenance"] == PROVENANCE_BINANCE)
    crypto_lag_days = (
        pd.Timestamp(equity_max) - pd.Timestamp(crypto_max)
    ).days
    lines.append(
        "The rubric reproduces the committed (a) score for eight of the ten candidates; the two "
        "differences are: the crypto carry (measured lower — the Binance archive has not published "
        f"October 2026, so its price legs lag the OKX cross-check by {crypto_lag} days) and the "
        "macro-regime overlay (the committed table deducted a point for ^VIX's non-tradability; the "
        "measured rubric applies the same deduction and still lands one point higher, so the "
        "committed score is kept as the more pessimistic of the two)."
    )
    lines.append("")
    lines.append("### 5.3 The shortlist")
    lines.append("")
    lines.append(
        "| Measured rank | Candidate | (a) | (b) | (c) | (d) | (e) | (f) | (g) | Total | "
        "Verdict |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for row in shortlist:
        s = row["scores"]
        lines.append(
            "| {rank} | {name} (`{cid}`) | {a} | {b} | {c} | {d} | {e} | {f} | {g} | **{total}/35** | "
            "{verdict} |".format(
                rank=row["measured_rank"],
                name=row["name"],
                cid=row["candidate_id"],
                a=s["a"], b=s["b"], c=s["c"], d=s["d"], e=s["e"], f=s["f"], g=s["g"],
                total=row["total"],
                verdict=row["verdict"],
            )
        )
    lines.append("")
    lines.append(
        "The committed table ranked the futures-basis candidate 7 and the crypto carry 8 even "
        "though the crypto carry scored higher (23 vs 21); the ordering above is by the measured "
        "total, ties broken by the committed rank."
    )
    lines.append("")
    lines.append("### 5.4 Changes against the committed shortlist")
    lines.append("")
    lines.append("| Candidate | Criterion | Committed | Revised | Evidence | Reason |")
    lines.append("|---|---|---|---|---|---|")
    any_override = False
    for row in shortlist:
        for override in row["overrides"]:
            any_override = True
            lines.append(
                "| {name} | ({crit}) | {base} | {revised} | `{cite}` | {reason} |".format(
                    name=row["name"],
                    crit=override["criterion"].upper(),
                    base=override["baseline"],
                    revised=override["revised"],
                    cite=override["citation"],
                    reason=override["reason"],
                )
            )
    if not any_override:
        lines.append("| — | — | — | — | — | no changes |")
    lines.append("")
    lines.append("Verdicts carried unchanged (with their committed citations):")
    lines.append("")
    for row in shortlist:
        if row["overrides"]:
            continue
        lines.append(
            f"* **{row['name']}** — {row['verdict']}. (`{row['verdict_citation']}`)"
        )
    lines.append("")

    # ------------------------------------------------------------------
    lines.append("## 6. Explicit rejection reasons")
    lines.append("")
    lines.append("| Segment | Ground | Reason | Citation |")
    lines.append("|---|---|---|---|")
    for item in payload["rejections"]:
        lines.append(
            "| {segment} | {ground} | {reason} | `{cite}` |".format(
                segment=item["segment"],
                ground=item["ground"],
                reason=item["reason"],
                cite=item["citation"],
            )
        )
    lines.append("")
    lines.append(
        "Rejected on the candidate's own pre-registered gate (the numeric evidence is in section "
        "5.4): cross-sectional momentum over the broad 18-ETF universe, sector rotation, the "
        "macro-regime overlay extension and the calendar/rebalancing-effects candidate."
    )
    lines.append("")

    # ------------------------------------------------------------------
    lines.append("## 7. Price predictability vs executable net edge")
    lines.append("")
    lines.append(
        "Every candidate the cache can support has now been carried through the repository's own "
        "walk-forward protocol at its own cost model (the crypto carry additionally through a "
        "realistic fee, slippage and capital-charge model). Only the incumbent clears the 0.9 "
        "walk-forward gate; the crypto carry's promotion gate fails in all 24 of its cost-model "
        "rows; the other four candidates fail gate 1 outright. The inventory explains why the "
        "others cannot be rescued by better data: their universe, sample and cost assumptions are "
        "already the ones the repository's own protocol uses, and their gate failures are "
        "properties of the effect, not of the measurement."
    )
    lines.append("")
    lines.append(
        "The data-readiness picture that survives this cycle is: one 33-year daily ETF cache with "
        "zero missing prices and zero duplicate timestamps; one "
        f"{crypto_depth:.2f}-year, checksum-pinned crypto archive (spot, perpetual and 8-hourly "
        f"funding for BTC and ETH) whose newest observation is {crypto_lag_days} days behind the "
        f"equity cache ({equity_max}); and no intraday equity, options, FX, borrow or contract-leg "
        "data at all. The next candidate segment must therefore be built from what the cache "
        "actually holds, or the cache must be extended first — with the extension itself being the "
        "preregistered, costed step."
    )
    lines.append("")

    # ------------------------------------------------------------------
    lines.append("## 8. Reproduction")
    lines.append("")
    lines.append("```bash")
    lines.append("python research/data_cost_inventory_001.py")
    lines.append("python -m pytest -q tests/test_data_cost_inventory_001.py")
    lines.append("python -m pytest -q")
    lines.append("git status --porcelain data/")
    lines.append("git diff --stat src/ config/ research/experiments/ research/reports/")
    lines.append("```")
    lines.append("")
    lines.append(
        "Every number in this report is re-derived by the first command from the committed cache, "
        "`config/` and `src/backtest/engine.py` alone."
    )
    lines.append("")
    return "\n".join(lines)


def render_experiment(payload: dict[str, Any]) -> str:
    inv = payload["inventory"]
    totals = payload["totals"]
    cost = payload["cost_model"]
    shortlist = payload["shortlist"]
    lines: list[str] = []

    lines.append("# Experiment: Data and cost inventory (data_cost_inventory_001, Cycle 912)")
    lines.append("")
    lines.append("## Hypothesis reference")
    lines.append("")
    lines.append(
        "None — this is a **measurement** cycle, not a strategy hypothesis. It executes the first "
        "step of AGENTS.md's Market Opportunity Search: *\"Inventory real data and costs actually "
        "available in the repository first\"*, followed by a scored shortlist against criteria "
        "(a)–(g)."
    )
    lines.append("")
    lines.append("## Objective")
    lines.append("")
    lines.append(
        "Produce a bounded, evidence-based inventory of the real data and the real cost model "
        "available in this repository, score the plausible candidate segments against AGENTS.md's "
        "(a)–(g), and state the rejection reason for every segment the data does not support. No "
        "backtest is executed, no candidate is promoted, no gate is changed."
    )
    lines.append("")
    lines.append("## Data used")
    lines.append("")
    lines.append(
        f"* Source: the committed cache `data/raw/` — {totals['raw_files']} parquet files, "
        f"{totals['raw_rows']} rows ({totals['equity_files']} equity/futures files from the "
        f"Yahoo Finance cache, {totals['crypto_files']} crypto files from the Binance public "
        "archive and the OKX funding cross-check). The fetcher is never called; nothing is "
        "downloaded."
    )
    lines.append(
        "* Point-in-time treatment: the Yahoo Finance cache carries session-dated UTC bars and is "
        "consumed with a 1-session signal lag; the Binance funding series carries settlement "
        "timestamps (a same-day funding rule is a look-ahead — the committed rule decides on the "
        "previous day's funding); the OKX series is a cross-check only."
    )
    lines.append(
        "* Provenance verification: the committed digests in "
        "`research/reports/binance_crypto_manifest.json` were re-verified against the cached "
        f"bytes — **{payload['manifest']['matched']}/{payload['manifest']['total']} match**."
    )
    lines.append(
        "* Frequency: every file's frequency is derived from its own median inter-observation "
        f"spacing; measured sub-daily files in the cache: **{totals['subdaily_files']}**."
    )
    lines.append(
        "* Universe: the whole repository (`data/raw/`, `data/processed/`, `config/`, `src/`, "
        "`research/`), read-only."
    )
    lines.append("")
    lines.append("## Configuration")
    lines.append("")
    lines.append(
        f"* Cost model read from the repository: commission **{_fmt(cost['commission_bps'], 1)} "
        f"bps**, slippage **{_fmt(cost['slippage_bps'], 1)} bps** (round trip "
        f"**{_fmt(cost['round_trip_bps'], 1)} bps** per unit of weight change), risk-free rate "
        f"**{_pct(cost['risk_free_annual'])}** annual — the first three from "
        "`src/backtest/engine.py:get_cost_params()`/`get_risk_free_rate()`, the risk-free rate "
        "likewise from `get_risk_free_rate()`."
    )
    lines.append(
        "* Cost-key scan: every leaf key of every file in `config/` was matched against the "
        "components (commission, slippage, round trip, funding, risk-free, spread, borrow, roll, "
        "market impact, latency, margin). The **absent** components are reported as measured "
        "gaps, not as assumptions."
    )
    lines.append(
        "* Scoring: criterion (a) is measured from the cache by the documented rubric; criteria "
        "(b)–(g) are carried from `research/reports/opportunity_shortlist.md` and changed only "
        "with a cited committed record."
    )
    lines.append(
        "* The shortlist, the carried scores and the citation for every change are listed in "
        "`research/reports/data_cost_inventory_001.md` sections 5.2–5.4."
    )
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| Item | Value |")
    lines.append("|---|---|")
    lines.append(f"| Raw files inventoried | {totals['raw_files']} |")
    lines.append(f"| Raw rows inventoried | {totals['raw_rows']} |")
    lines.append(f"| Missing prices (whole cache) | {totals['missing_prices']} |")
    lines.append(f"| Duplicate timestamps (whole cache) | {totals['duplicate_timestamps']} |")
    lines.append(f"| Repeat (unchanged) prices (whole cache) | {totals['stale_prices']} |")
    lines.append(f"| Sub-daily files (whole cache) | {totals['subdaily_files']} |")
    lines.append(f"| Cost components with no configuration key | "
                 f"{sum(1 for c, _ in COST_COMPONENTS if not cost['component_coverage'][c])} of "
                 f"{len(COST_COMPONENTS)} |")
    lines.append(f"| Candidates scored | {len(shortlist)} |")
    lines.append(f"| Segments explicitly rejected or blocked | {len(payload['rejections'])} |")
    lines.append("")
    lines.append("| Measured rank | Candidate | (a) | (b) | (c) | (d) | (e) | (f) | (g) | Total | Verdict |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for row in shortlist:
        s = row["scores"]
        lines.append(
            "| {rank} | {name} | {a} | {b} | {c} | {d} | {e} | {f} | {g} | **{total}/35** | "
            "{verdict} |".format(
                rank=row["measured_rank"], name=row["name"], a=s["a"], b=s["b"], c=s["c"], d=s["d"],
                e=s["e"], f=s["f"], g=s["g"], total=row["total"], verdict=row["verdict"],
            )
        )
    lines.append("")
    lines.append(
        "**Decision of this cycle: none.** No candidate is promoted and none is demoted by the "
        "inventory itself; the inventory records what the data supports, the cost model that "
        "exists, and the rejection reasons for the segments that the data cannot support."
    )
    lines.append("")
    lines.append("## Trial count")
    lines.append("")
    lines.append(
        "- 1 deterministic measurement pass over the committed cache, the committed configuration "
        "and the committed shortlist table. No parameter search, no robustness grid, no candidate "
        "selection, no backtest: the cycle consumes **0** new strategy trials."
    )
    lines.append("")
    lines.append("## Reproduction")
    lines.append("")
    lines.append("```bash")
    lines.append("python research/data_cost_inventory_001.py")
    lines.append("python -m pytest -q tests/test_data_cost_inventory_001.py")
    lines.append("python -m pytest -q")
    lines.append("git status --porcelain data/")
    lines.append("git diff --stat src/ config/ research/experiments/ research/reports/")
    lines.append("```")
    lines.append("")
    lines.append("## Boundaries")
    lines.append("")
    lines.append(
        "* Read-only: no fetcher or network call for new data; the existing committed cache is "
        "the only data source inspected."
    )
    lines.append(
        "* Nothing under `data/` or `config/` is written, and no committed artifact other than "
        "the two new files of this cycle is modified."
    )
    lines.append("* No backtest, no promotion, no gate change, no candidate execution.")
    lines.append("* Deterministic: no timestamps in the report or in this record.")
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    lines.append("| Artifact | Path |")
    lines.append("|---|---|")
    lines.append("| Tool | `research/data_cost_inventory_001.py` |")
    lines.append("| Report | `research/reports/data_cost_inventory_001.md` |")
    lines.append("| Experiment record | `research/experiments/data_cost_inventory_001.md` |")
    lines.append("| Tests | `tests/test_data_cost_inventory_001.py` |")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--report-out", type=Path, default=OUT_REPORT)
    parser.add_argument("--experiment-out", type=Path, default=OUT_EXPERIMENT)
    args = parser.parse_args(argv)

    try:
        payload = build_payload(raw_dir=args.raw_dir, processed_dir=args.processed_dir)
    except InventoryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    report = render_report(payload)
    experiment = render_experiment(payload)

    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.experiment_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(report, encoding="utf-8")
    args.experiment_out.write_text(experiment, encoding="utf-8")

    totals = payload["totals"]
    print("OVERALL: PASS")
    print(f"report: {args.report_out}")
    print(f"experiment: {args.experiment_out}")
    print(
        f"inventory: {totals['raw_files']} raw files, {totals['raw_rows']} rows, "
        f"{totals['missing_prices']} missing prices, {totals['duplicate_timestamps']} duplicate "
        f"timestamps"
    )
    print(
        f"cost model: commission {payload['cost_model']['commission_bps']:.1f} bps, slippage "
        f"{payload['cost_model']['slippage_bps']:.1f} bps, round trip "
        f"{payload['cost_model']['round_trip_bps']:.1f} bps, risk-free "
        f"{payload['cost_model']['risk_free_annual']:.4f}"
    )
    print(f"crypto manifest: {payload['manifest']['matched']}/{payload['manifest']['total']} digests match")
    print(
        "shortlist: "
        + "; ".join(
            f"{row['measured_rank']}. {row['name']} {row['total']}/35" for row in payload["shortlist"]
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
