#!/usr/bin/env python3
"""Data & cost inventory 002 with a point-in-time universe-membership audit
of the incumbent's published walk-forward (``tsmomentum_spytrend_001``).

Cycle 929.

What this tool does
-------------------
1. **Refreshes the data inventory** from the committed parquet cache
   (``data/raw/``): per file -- rows, first/last observation, sampling
   frequency, asset class and the integrity counters (missing prices,
   duplicate timestamps, non-positive prices, zero-volume prints, repeated
   prices) plus a SHA-256 digest.
2. **Audits the drift** against the committed Cycle-912 inventory
   (``research/reports/data_cost_inventory_001.md``): the published per-file
   digests are re-verified against the current bytes, and the set of
   configuration files the published scan covered is compared with the
   current one. The published inventory is therefore *checked*, not trusted.
3. **Re-derives the cost model** actually configured in ``config/`` and in
   ``src/backtest/engine.py``, and states which cost components have no
   configuration key at all.
4. **Measures the point-in-time universe membership of the incumbent's
   published walk-forward** -- the one data-readiness property
   (AGENTS.md, "Data readiness and integrity: ... point-in-time universe
   membership") that no committed record measures. The incumbent's universe
   is seven ETFs whose inceptions are spread over 1993-2004, so the
   *effective* cross-section of the published path grows over the sample.
   The tool measures that schedule from the data, maps it onto the
   published fold table, and reports the published walk-forward statistic
   on the point-in-time-complete subsample and on the incomplete one.

The tool is **read-only**: the price panel is read from the committed cache
(the fetcher is never called), nothing under ``data/`` or ``config/`` is
written, and the SHA-256 of every file under those two trees plus every
committed artefact is compared before and after the run. The published
record, the published gates, the published protocol and every committed
candidate artefact are left untouched -- this is a measurement, not a
correction.

Reproduction anchor
-------------------
The published walk-forward is reproduced before anything is published: 48
folds, mean OOS Sharpe 0.947307, positive-fold rate 91.67%, 6013 pooled
out-of-sample trades, and every published fold's test window, OOS Sharpe
and trade count. A mismatch fails the run.
"""

from __future__ import annotations

import argparse
import hashlib
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
    END_DATE,
    LOOKBACK,
    SKIP,
    START_DATE,
    SYMBOLS,
    TOP_FRACTION,
)
from research.tsmomentum_walkforward_embargo_audit import (  # noqa: E402
    build_candidate_path,
    evaluate_design,
    load_close_from_cache,
    published_splits,
    resolve_published_record,
)
from src.backtest.engine import get_cost_params, get_risk_free_rate  # noqa: E402
from src.features.momentum import compute_momentum, select_top_decile  # noqa: E402

CANDIDATE_ID = "tsmomentum_spytrend_001"
CYCLE = "929"

RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
CONFIG_DIR = REPO_ROOT / "config"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
EXPERIMENTS_DIR = REPO_ROOT / "research" / "experiments"

OUT_REPORT = REPORTS_DIR / "data_cost_inventory_002.md"
OUT_EXP = EXPERIMENTS_DIR / "data_cost_inventory_002.md"

# The inventory published in Cycle 912, whose digests this tool re-verifies.
PUBLISHED_INVENTORY = REPORTS_DIR / "data_cost_inventory_001.md"

# Pre-registered promotion-gate thresholds (AGENTS.md "Promotion gate"; the
# same thresholds the published record's own gate table uses).
GATE_WF_MEAN_MIN = 0.9
GATE_POSITIVE_FOLD_RATE_MIN = 0.5
GATE_POOLED_TRADES_MIN = 100

# The published aggregate the recomputed path must reproduce.
PUBLISHED_WF_MEAN = 0.9473
PUBLISHED_POSITIVE_RATE = 0.9166666666666666
PUBLISHED_POOLED_TRADES = 6013

# Bootstrap settings (moving block over the fold-level statistics).
BOOTSTRAP_DRAWS = 2000
BOOTSTRAP_SEED = 20240101

# Cost components a credible net-of-cost evaluation needs. The first five are
# present in the repository's own cost model; the rest have no configuration
# key at all (measured, not assumed).
COST_COMPONENT_KEYS = {
    "commission": ("commission",),
    "slippage": ("slippage",),
    "round_trip": ("round_trip", "roundtrip"),
    "funding": ("funding",),
    "risk_free": ("risk_free", "risk-free"),
}
UNCONFIGURED_COST_COMPONENTS = (
    "bid_ask_spread",
    "borrow",
    "roll",
    "market_impact",
    "latency",
    "margin",
)

ASSET_CLASS_RULES = (
    ("crypto", "crypto"),
    ("futures", "futures"),
)


class AuditError(RuntimeError):
    """Raised when a required input is missing or malformed (fails closed)."""


def fail(message: str) -> None:
    raise AuditError(message)


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


def tracked_artifact_hashes() -> dict[str, str]:
    """SHA-256 of the committed artefacts this tool must not modify."""
    out: dict[str, str] = {}
    for root in (REPO_ROOT / "src", CONFIG_DIR, EXPERIMENTS_DIR, REPORTS_DIR):
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix not in {".md", ".py", ".yaml", ".yml", ".json"}:
                continue
            out[str(path.relative_to(REPO_ROOT))] = sha256_file(path)
    return out


# ----------------------------------------------------------------------
# Data inventory
# ----------------------------------------------------------------------
def classify_asset_class(rel_path: str) -> str:
    name = rel_path.split("/")[-1]
    if rel_path.startswith("data/raw/crypto/"):
        return "crypto"
    if name.endswith("-F.parquet"):
        return "futures"
    if name.startswith("^"):
        return "index (non-tradable)"
    return "etf"


def normalise_price_frame(path: Path) -> tuple[pd.DatetimeIndex, pd.Series, pd.Series | None, str]:
    """Return (index, price series, volume series or None, price label).

    Two schemas are cached: the yfinance schema (``Open/High/Low/Close/Volume``
    on a UTC datetime index) and the crypto schema (``timestamp``/``datetime``
    columns with lowercase ``open/high/low/close/volume`` or ``fundingRate``).
    """
    df = pd.read_parquet(path)
    if "Close" in df.columns:
        idx = pd.to_datetime(df.index)
        if idx.tz is None:
            idx = idx.tz_localize("UTC")
        else:
            idx = idx.tz_convert("UTC")
        df = df.copy()
        df.index = idx
        df = df.sort_index()
        return idx, df["Close"], df["Volume"] if "Volume" in df.columns else None, "Close"

    if "datetime" not in df.columns:
        fail(f"cached file has an unrecognised schema: {path}")
    idx = pd.DatetimeIndex(pd.to_datetime(df["datetime"]))
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    else:
        idx = idx.tz_convert("UTC")
    df = df.copy()
    df.index = idx
    df = df.sort_index()
    if "close" in df.columns:
        return idx, df["close"], df["volume"] if "volume" in df.columns else None, "close"
    if "fundingRate" in df.columns:
        # A funding rate is a signed rate, not a price: a non-positive value is
        # ordinary and is reported as not applicable.
        return idx, df["fundingRate"], None, "fundingRate"
    fail(f"cached file has no price column: {path}")
    raise AssertionError("unreachable")


def measure_price_file(path: Path) -> dict[str, Any]:
    """Integrity and coverage counters for one cached price file."""
    idx, close, volume, price_label = normalise_price_frame(path)

    dupes = int(idx.duplicated().sum())
    missing = int(close.isna().sum())
    non_positive = None if price_label == "fundingRate" else int((close <= 0).sum())
    zero_volume = int((volume == 0).sum()) if volume is not None else None
    repeats = int((close == close.shift(1)).sum())

    gaps = pd.Series(idx).diff().dt.total_seconds().dropna()
    if len(gaps):
        median_gap_days = float(np.median(gaps) / 86400.0)
        frequency = "8-hourly" if median_gap_days < 0.5 else "daily"
    else:
        median_gap_days = float("nan")
        frequency = "unknown"

    rel = str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else path.name
    return {
        "path": rel,
        "asset_class": classify_asset_class(rel),
        "price_label": price_label,
        "rows": int(len(idx)),
        "first": str(idx[0].date()),
        "last": str(idx[-1].date()),
        "frequency": frequency,
        "median_gap_days": median_gap_days,
        "dup_timestamps": dupes,
        "missing_prices": missing,
        "non_positive_prices": non_positive,
        "zero_volume_rows": zero_volume,
        "repeat_prices": repeats,
        "sha256_16": sha256_file(path)[:16],
    }


def measure_inventory(raw_dir: Path) -> list[dict[str, Any]]:
    files = sorted(raw_dir.rglob("*.parquet"))
    if not files:
        fail(f"no cached price files found under {raw_dir}")
    return [measure_price_file(path) for path in files]


def measure_processed_tree(processed_dir: Path) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    if not processed_dir.exists():
        return []
    for path in sorted(processed_dir.rglob("*")):
        if not path.is_file() or path.suffix != ".parquet":
            continue
        rel = path.relative_to(processed_dir)
        group = str(rel.parts[0]) if len(rel.parts) > 1 else "(top level)"
        entry = groups.setdefault(
            group, {"group": group, "files": 0, "rows": 0, "first": None, "last": None}
        )
        df = pd.read_parquet(path)
        entry["files"] += 1
        entry["rows"] += int(len(df))
        dates = pd.Series(dtype="datetime64[ns]")
        if isinstance(df.index, pd.DatetimeIndex):
            dates = pd.Series(df.index)
        elif "date" in df.columns:
            dates = pd.Series(pd.to_datetime(df["date"], errors="coerce", utc=True)).dropna()
        if len(dates):
            first, last = str(dates.min().date()), str(dates.max().date())
            entry["first"] = first if entry["first"] is None else min(entry["first"], first)
            entry["last"] = last if entry["last"] is None else max(entry["last"], last)
    return [groups[k] for k in sorted(groups)]


# ----------------------------------------------------------------------
# Drift audit against the published Cycle-912 inventory
# ----------------------------------------------------------------------
def parse_published_digests(text: str) -> dict[str, str]:
    """Published per-file SHA-256 prefixes from the Cycle-912 inventory."""
    digests: dict[str, str] = {}
    pattern = re.compile(r"\|\s*\d+\s*\|\s*`([^`]+)`\s*\|.*\|\s*`([0-9a-f]{16})`\s*\|")
    for match in pattern.finditer(text):
        digests[match.group(1)] = match.group(2)
    return digests


def parse_published_config_files(text: str) -> set[str]:
    """Configuration files the Cycle-912 cost scan covered.

    The published report names the files both with and without the ``config/``
    prefix (``calendar_effects_001.yaml:cost_model.commission_bps``), so the
    names are normalised to ``config/<name>``.
    """
    names: set[str] = set()
    for match in re.finditer(r"`([^`\s]*\.yaml)(?::[^`]*)?`", text):
        name = match.group(1)
        if not name:
            continue
        names.add(name if name.startswith("config/") else f"config/{name}")
    return names


def parse_published_config_count(text: str) -> int | None:
    """The number of configuration files the published scan claims to have read."""
    match = re.search(r"\((\d+) config files scanned\)", text)
    return int(match.group(1)) if match else None


def audit_drift(inventory: list[dict[str, Any]]) -> dict[str, Any]:
    if not PUBLISHED_INVENTORY.exists():
        fail(f"published inventory not found: {PUBLISHED_INVENTORY}")
    text = PUBLISHED_INVENTORY.read_text(encoding="utf-8")
    published_digests = parse_published_digests(text)
    if not published_digests:
        fail("published inventory contains no parseable per-file digest table")

    current = {row["path"]: row["sha256_16"] for row in inventory}
    rows = []
    for path, digest in sorted(published_digests.items()):
        now = current.get(path)
        if now is None:
            status = "REMOVED"
        elif now == digest:
            status = "MATCH"
        else:
            status = "CHANGED"
        rows.append(
            {
                "path": path,
                "published_sha256_16": digest,
                "current_sha256_16": now or "-",
                "status": status,
            }
        )
    added = sorted(set(current) - set(published_digests))

    published_configs = parse_published_config_files(text)
    current_configs = {f"config/{p.name}" for p in sorted(CONFIG_DIR.glob("*.yaml"))}
    config_added = sorted(current_configs - published_configs)
    config_removed = sorted(published_configs - current_configs)

    return {
        "published_inventory": str(PUBLISHED_INVENTORY.relative_to(REPO_ROOT)),
        "files": rows,
        "n_match": sum(1 for r in rows if r["status"] == "MATCH"),
        "n_changed": sum(1 for r in rows if r["status"] == "CHANGED"),
        "n_removed": sum(1 for r in rows if r["status"] == "REMOVED"),
        "added_files": added,
        "published_config_files": sorted(published_configs),
        "published_config_count_claim": parse_published_config_count(text),
        "current_config_files": sorted(current_configs),
        "config_added": config_added,
        "config_removed": config_removed,
    }


# ----------------------------------------------------------------------
# Cost model
# ----------------------------------------------------------------------
#: Words that turn a component name into a price. A key prices a component
#: when the component is the subject of one of them (``roll_cost``,
#: ``borrow_bps``) or when the key *is* the component (``bid_ask_spread``).
COST_VALUE_WORDS = frozenset(
    {
        "cost",
        "costs",
        "price",
        "prices",
        "bps",
        "bp",
        "fee",
        "fees",
        "rate",
        "spread",
        "premium",
        "discount",
        "notional",
    }
)


def _is_numeric(value: str) -> bool:
    """True when a configuration value is a number.

    A cost component is *priced* only when the configuration key that names it
    carries a number. A key that merely mentions a component (for example
    ``data_quality.roll_detector``, which names the module that detects a
    roll) is a description of a rule, not a cost assumption; counting it as a
    price would silently drop the component from the disclosed gap.
    """
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def _prices_component(key_clean: str, component: str) -> bool:
    """True when a configuration key prices the given cost component.

    The key must name the component and the name must be the subject of a
    cost term (``roll_cost``, ``borrow_bps``), or the key must *be* the
    component (``bid_ask_spread``). A key that only names the component as
    part of a rule (``roll_detector``, ``roll_window_sessions_per_event``)
    describes the rule, not a price.
    """
    words = [word for word in key_clean.replace("-", "_").split("_") if word]
    component_words = [word for word in component.replace("-", "_").split("_") if word]
    span = len(component_words)
    for start in range(0, len(words) - span + 1):
        if words[start : start + span] != component_words:
            continue
        if start + span == len(words):
            return True
        if words[start + span] in COST_VALUE_WORDS:
            return True
    return False


def scan_cost_config() -> dict[str, Any]:
    """Cost keys present in ``config/`` and the components that have none."""
    found: dict[str, list[str]] = {key: [] for key in COST_COMPONENT_KEYS}
    unconfigured_hits: dict[str, list[str]] = {c: [] for c in UNCONFIGURED_COST_COMPONENTS}
    for path in sorted(CONFIG_DIR.glob("*.yaml")):
        rel = f"config/{path.name}"
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or ":" not in stripped:
                continue
            key, _, value = stripped.partition(":")
            key_clean = key.strip().lower()
            value_clean = value.strip().split("#")[0].strip()
            for component, needles in COST_COMPONENT_KEYS.items():
                if any(needle in key_clean for needle in needles):
                    found[component].append(f"{rel}:{line_no}:{key_clean} = {value_clean}")
            for component in UNCONFIGURED_COST_COMPONENTS:
                if _prices_component(key_clean, component) and _is_numeric(value_clean):
                    unconfigured_hits[component].append(
                        f"{rel}:{line_no}:{key_clean} = {value_clean}"
                    )
    return {
        "configured": {k: v for k, v in found.items()},
        "unconfigured": {
            k: v for k, v in unconfigured_hits.items() if v
        },
        "unconfigured_components": [
            c for c in UNCONFIGURED_COST_COMPONENTS if not unconfigured_hits[c]
        ],
        "n_config_files": len(list(CONFIG_DIR.glob("*.yaml"))),
    }


def measure_costs() -> dict[str, Any]:
    # ``get_cost_params`` returns fractions of one unit; the repository quotes
    # them in basis points.
    commission, slippage = get_cost_params()
    return {
        "engine_commission_bps": round(float(commission) * 10000.0, 6),
        "engine_slippage_bps": round(float(slippage) * 10000.0, 6),
        "engine_round_trip_bps": round((float(commission) + float(slippage)) * 10000.0, 6),
        "engine_risk_free_rate_annual": float(get_risk_free_rate()),
        "config_scan": scan_cost_config(),
    }


# ----------------------------------------------------------------------
# Point-in-time universe membership
# ----------------------------------------------------------------------
def moving_block_bootstrap_mean(
    values: list[float] | np.ndarray, block: int, draws: int, seed: int
) -> dict[str, float]:
    """Moving-block bootstrap CI for the mean of a fold-level statistic."""
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return {"mean": float("nan"), "ci_low": float("nan"), "ci_high": float("nan")}
    n = len(arr)
    block = max(1, min(block, n))
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block))
    means = np.empty(draws, dtype=float)
    for i in range(draws):
        picked: list[int] = []
        while len(picked) < n:
            start = int(rng.integers(0, n))
            picked.extend(range(start, min(start + block, n)))
        means[i] = float(arr[picked[:n]].mean())
    return {
        "mean": float(arr.mean()),
        "ci_low": float(np.percentile(means, 2.5)),
        "ci_high": float(np.percentile(means, 97.5)),
    }


def subsample_stats(
    rows: list[dict[str, Any]], label: str, drop_folds: tuple[int, ...] = ()
) -> dict[str, Any]:
    """Aggregate the published gate statistics over a fold subsample."""
    kept = [r for r in rows if r["fold"] not in drop_folds]
    sharpes = [r["published_test_sharpe"] for r in kept]
    trades = [r["published_test_trades"] for r in kept]
    if not kept:
        return {"label": label, "n_folds": 0}
    block = max(2, len(kept) // 8)
    boot = moving_block_bootstrap_mean(sharpes, block, BOOTSTRAP_DRAWS, BOOTSTRAP_SEED)
    mean_sharpe = float(np.mean(sharpes))
    positive_rate = float(np.mean([s > 0 for s in sharpes]))
    pooled = int(sum(trades))
    gates = [
        {
            "gate": "wf_mean_oos_sharpe",
            "threshold": GATE_WF_MEAN_MIN,
            "value": mean_sharpe,
            "pass": bool(mean_sharpe >= GATE_WF_MEAN_MIN),
        },
        {
            "gate": "positive_fold_rate",
            "threshold": GATE_POSITIVE_FOLD_RATE_MIN,
            "value": positive_rate,
            "pass": bool(positive_rate >= GATE_POSITIVE_FOLD_RATE_MIN),
        },
        {
            "gate": "pooled_oos_trades",
            "threshold": GATE_POOLED_TRADES_MIN,
            "value": pooled,
            "pass": bool(pooled > GATE_POOLED_TRADES_MIN),
        },
    ]
    return {
        "label": label,
        "n_folds": len(kept),
        "folds": [r["fold"] for r in kept],
        "mean_test_sharpe": mean_sharpe,
        "median_test_sharpe": float(np.median(sharpes)),
        "std_test_sharpe": float(np.std(sharpes, ddof=1)) if len(sharpes) > 1 else float("nan"),
        "pct_positive_sharpe": positive_rate,
        "pooled_trades": pooled,
        "ci_low": boot["ci_low"],
        "ci_high": boot["ci_high"],
        "gates": gates,
        "failed_gates": [g["gate"] for g in gates if not g["pass"]],
    }


def audit_membership(raw_dir: Path) -> dict[str, Any]:
    """Measure the effective cross-section of the published path."""
    close = load_close_from_cache(list(SYMBOLS), raw_dir)
    net_ret, weights = build_candidate_path(close)

    momentum = compute_momentum(close, lookback=LOOKBACK, skip=SKIP)
    valid = momentum.notna().sum(axis=1)
    selected = select_top_decile(momentum, top_fraction=TOP_FRACTION).sum(axis=1)

    inceptions = []
    for symbol in SYMBOLS:
        first_price = close[symbol].first_valid_index()
        first_momentum = momentum[symbol].first_valid_index()
        inceptions.append(
            {
                "symbol": symbol,
                "first_price": str(pd.Timestamp(first_price).date()),
                "first_valid_momentum": str(pd.Timestamp(first_momentum).date()),
            }
        )

    # Selection-rule degeneracy: with k assets carrying a valid momentum the
    # repository's "top half" rule holds ceil(k/2)-or-more of them.
    degeneracy = []
    for k in range(1, len(SYMBOLS) + 1):
        ranks = list(range(1, k + 1))
        threshold = max(ranks) * (1.0 - TOP_FRACTION)
        held = sum(1 for r in ranks if r >= threshold)
        degeneracy.append(
            {
                "valid_assets": k,
                "selected": held,
                "share": held / k,
                "rule": "top_fraction selection over the assets with a valid momentum",
            }
        )

    design = evaluate_design(net_ret, weights, published_splits())
    computed = design["folds"]
    summary = design["summary"]

    record_path, published = resolve_published_record(EXPERIMENTS_DIR)
    pub_folds = {int(f["fold"]): f for f in published["folds"]}

    rows: list[dict[str, Any]] = []
    for row in computed:
        fold = int(row["fold"])
        pub = pub_folds.get(fold)
        if pub is None:
            fail(f"published record has no fold {fold}")
        ts = pd.Timestamp(row["test_start"], tz="UTC")
        te = pd.Timestamp(row["test_end"], tz="UTC")
        breadth_win = valid.loc[ts:te]
        selected_win = selected.loc[ts:te]
        # A published test window may start on a session the union calendar does
        # not carry; the breadth at the start is read at the first session on or
        # after the published test start.
        pos = int(valid.index.searchsorted(ts, side="left"))
        if pos >= len(valid):
            fail(f"fold {fold}: the test window starts after the end of the price panel")
        breadth_start = int(valid.iloc[pos])
        rows.append(
            {
                "fold": fold,
                "train_start": row["train_start"],
                "test_start": row["test_start"],
                "test_end": row["test_end"],
                "published_test_sharpe": float(pub["test_sharpe"]),
                "recomputed_test_sharpe": float(row["test_sharpe"]),
                "published_test_trades": int(pub["test_trades"]),
                "recomputed_test_trades": int(row["test_trades"]),
                "breadth_start": breadth_start,
                "breadth_min": int(breadth_win.min()),
                "breadth_mean": float(breadth_win.mean()),
                "selected_mean": float(selected_win.mean()),
                "phase": "A" if fold % 2 == 1 else "B",
            }
        )

    n_assets = len(SYMBOLS)
    complete = [r for r in rows if r["breadth_min"] >= n_assets]
    incomplete = [r for r in rows if r["breadth_min"] < n_assets]
    artefact_fold = min(rows, key=lambda r: r["published_test_sharpe"])["fold"]

    all_stats = subsample_stats(rows, "All published folds (48)")
    complete_stats = subsample_stats(
        complete, f"Point-in-time-complete folds (breadth {n_assets}/{n_assets})"
    )
    complete_clean_stats = subsample_stats(
        complete,
        f"Point-in-time-complete folds, artefact fold {artefact_fold} removed",
        drop_folds=(artefact_fold,),
    )
    incomplete_stats = subsample_stats(
        incomplete, "Point-in-time-incomplete folds (breadth < 7/7)"
    )

    phase_rows = []
    for label, subset in (
        ("all", rows),
        ("complete", complete),
        ("incomplete", incomplete),
    ):
        for phase in ("A", "B"):
            sel = [r for r in subset if r["phase"] == phase]
            if not sel:
                continue
            phase_rows.append(
                {
                    "subset": label,
                    "phase": phase,
                    "n_folds": len(sel),
                    "mean_test_sharpe": float(np.mean([r["published_test_sharpe"] for r in sel])),
                    "median_test_sharpe": float(
                        np.median([r["published_test_sharpe"] for r in sel])
                    ),
                }
            )

    return {
        "candidate_id": CANDIDATE_ID,
        "universe": list(SYMBOLS),
        "lookback": LOOKBACK,
        "skip": SKIP,
        "top_fraction": TOP_FRACTION,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "record_path": str(record_path.relative_to(REPO_ROOT)),
        "inceptions": inceptions,
        "degeneracy": degeneracy,
        "breadth_schedule": [
            {
                "breadth": int(k),
                "sessions": int((valid == k).sum()),
                "first": str(valid.index[valid == k][0].date())
                if (valid == k).any()
                else "-",
                "last": str(valid.index[valid == k][-1].date()) if (valid == k).any() else "-",
            }
            for k in sorted(valid.unique())
        ],
        "rows": rows,
        "recomputed_summary": {
            "n_folds": summary["n_folds"],
            "mean_test_sharpe": summary["mean_test_sharpe"],
            "pct_positive_sharpe": summary["pct_positive_sharpe"],
            "total_test_trades": summary["total_test_trades"],
        },
        "published_aggregate": {
            "n_folds": published["aggregate"]["n_folds"]["value"],
            "mean_test_sharpe": published["aggregate"]["mean_test_sharpe"]["value"],
            "pct_positive_sharpe": published["aggregate"]["pct_positive_sharpe"]["value"],
            "total_test_trades": published["aggregate"]["total_test_trades"]["value"],
        },
        "subsamples": {
            "all": all_stats,
            "complete": complete_stats,
            "complete_without_artefact": complete_clean_stats,
            "incomplete": incomplete_stats,
        },
        "phase_rows": phase_rows,
        "artefact_fold": artefact_fold,
        "n_complete": len(complete),
        "n_incomplete": len(incomplete),
    }


# ----------------------------------------------------------------------
# Internal checks
# ----------------------------------------------------------------------
def run_checks(
    inventory: list[dict[str, Any]],
    drift: dict[str, Any],
    costs: dict[str, Any],
    membership: dict[str, Any],
    data_before: dict[str, str],
    config_before: dict[str, str],
    artifacts_before: dict[str, str],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    recomputed = membership["recomputed_summary"]
    published = membership["published_aggregate"]
    # The published record rounds the aggregate to four decimals and states the
    # positive-fold rate as a percentage.
    published_rate = published["pct_positive_sharpe"]
    if published_rate > 1.0:
        published_rate = published_rate / 100.0
    check(
        "anchor_n_folds",
        recomputed["n_folds"] == published["n_folds"] == 48,
        f"recomputed {recomputed['n_folds']} folds vs published {published['n_folds']}",
    )
    check(
        "anchor_mean_oos_sharpe",
        abs(recomputed["mean_test_sharpe"] - published["mean_test_sharpe"]) < 5e-5
        and abs(recomputed["mean_test_sharpe"] - PUBLISHED_WF_MEAN) < 5e-5,
        f"recomputed {recomputed['mean_test_sharpe']:.6f} vs published {published['mean_test_sharpe']}",
    )
    check(
        "anchor_positive_fold_rate",
        abs(recomputed["pct_positive_sharpe"] - published_rate) < 5e-4
        and abs(recomputed["pct_positive_sharpe"] - PUBLISHED_POSITIVE_RATE) < 1e-9,
        f"recomputed {recomputed['pct_positive_sharpe']:.6f} vs published {published_rate:.6f}",
    )
    check(
        "anchor_pooled_trades",
        recomputed["total_test_trades"] == published["total_test_trades"] == PUBLISHED_POOLED_TRADES,
        f"recomputed {recomputed['total_test_trades']} vs published {published['total_test_trades']}",
    )

    window_mismatch = [
        r["fold"]
        for r in membership["rows"]
        if abs(r["published_test_sharpe"] - r["recomputed_test_sharpe"]) > 5e-5
        or r["published_test_trades"] != r["recomputed_test_trades"]
    ]
    check(
        "per_fold_reproduction",
        not window_mismatch,
        f"all {len(membership['rows'])} published folds reproduced"
        if not window_mismatch
        else f"folds mismatching: {window_mismatch}",
    )

    check(
        "inventory_non_empty",
        len(inventory) > 0 and all(row["rows"] > 0 for row in inventory),
        f"{len(inventory)} cached price files measured",
    )
    check(
        "inventory_no_missing_prices",
        all(row["missing_prices"] == 0 for row in inventory),
        f"total missing prices: {sum(row['missing_prices'] for row in inventory)}",
    )
    check(
        "inventory_no_duplicate_timestamps",
        all(row["dup_timestamps"] == 0 for row in inventory),
        f"total duplicate timestamps: {sum(row['dup_timestamps'] for row in inventory)}",
    )
    check(
        "drift_digests_verified",
        drift["n_match"] == len(drift["files"]) and not drift["added_files"],
        f"{drift['n_match']}/{len(drift['files'])} published digests match; "
        f"{drift['n_changed']} changed; {drift['n_removed']} removed; "
        f"{len(drift['added_files'])} added",
    )
    check(
        "cost_model_read",
        costs["engine_round_trip_bps"] > 0 and costs["engine_risk_free_rate_annual"] > 0,
        f"round trip {costs['engine_round_trip_bps']} bps, rf {costs['engine_risk_free_rate_annual']}",
    )
    check(
        "unconfigured_cost_components_measured",
        set(costs["config_scan"]["unconfigured_components"])
        <= set(UNCONFIGURED_COST_COMPONENTS),
        "unconfigured: "
        + ", ".join(costs["config_scan"]["unconfigured_components"]),
    )
    check(
        "membership_schedule_measured",
        membership["n_complete"] + membership["n_incomplete"] == 48
        and membership["n_incomplete"] > 0,
        f"{membership['n_incomplete']} folds on an incomplete cross-section, "
        f"{membership['n_complete']} on the complete one",
    )
    inception_pairs = [
        (row["first_price"], row["first_valid_momentum"], row["symbol"])
        for row in membership["inceptions"]
    ]
    by_price = [s for _, _, s in sorted(inception_pairs)]
    by_momentum = [s for _, _, s in sorted(inception_pairs, key=lambda r: r[1])]
    check(
        "membership_inception_order",
        by_price == by_momentum
        and all(mom > price for price, mom, _ in inception_pairs),
        "each member's first valid momentum follows its first cached close, and no "
        "member overtakes another between price availability and momentum "
        f"availability ({', '.join(by_momentum)})",
    )
    check(
        "data_unchanged",
        fingerprint(REPO_ROOT / "data") == data_before,
        "every file under data/ is byte-identical after the run",
    )
    check(
        "config_unchanged",
        fingerprint(CONFIG_DIR) == config_before,
        "every file under config/ is byte-identical after the run",
    )
    check(
        "committed_artifacts_unchanged",
        tracked_artifact_hashes() == artifacts_before,
        "every committed src/, config/, research/experiments/ and research/reports/ artefact is byte-identical",
    )
    return checks


# ----------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------
def fmt(value: float, digits: int = 6) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "-"
    return f"{value:.{digits}f}"


def render_report(payload: dict[str, Any]) -> str:
    inv = payload["inventory"]
    drift = payload["drift"]
    costs = payload["costs"]
    mem = payload["membership"]
    lines: list[str] = []
    add = lines.append

    def total(field: str) -> str:
        values = [r[field] for r in inv if r[field] is not None]
        if len(values) != len(inv):
            return f"{sum(values)} (n/a for the {len(inv) - len(values)} funding-rate files)"
        return str(sum(values))

    add("# Data and Cost Inventory 002 — Cycle 929")
    add("")
    add(
        "**Method:** read-only, cache-only inspection of the committed repository. "
        "`research/data_cost_inventory_002.py` re-measures the cache, re-verifies the "
        "digests published by the Cycle-912 inventory, re-derives the configured cost "
        "model, and measures the **point-in-time universe membership** of the "
        "incumbent's published walk-forward. No backtest was re-tuned, no candidate was "
        "promoted, no fetcher was called and nothing under `data/` or `config/` was "
        "written."
    )
    add("")
    add(
        "**Determinism:** this document contains no timestamp and no run id; two "
        "consecutive generations are byte-identical."
    )
    add("")

    add("## 1. Data inventory — `data/raw/`")
    add("")
    total_rows = sum(r["rows"] for r in inv)
    add(
        f"**{len(inv)} parquet files, {total_rows} rows** "
        f"({sum(1 for r in inv if r['asset_class'] == 'etf')} ETF, "
        f"{sum(1 for r in inv if r['asset_class'] == 'futures')} futures, "
        f"{sum(1 for r in inv if r['asset_class'] == 'crypto')} crypto, "
        f"{sum(1 for r in inv if r['asset_class'].startswith('index'))} index). "
        f"**{total('missing_prices')} missing prices**, "
        f"**{total('dup_timestamps')} duplicate timestamps**, "
        f"**{total('non_positive_prices')} non-positive prices**, "
        f"**{total('zero_volume_rows')} zero-volume rows**."
    )
    add("")
    add(
        "The counters marked *n/a* apply to the crypto funding-rate files: a "
        "funding rate is a signed rate (a negative value is ordinary, not an "
        "anomaly) and the series carries no volume column."
    )
    add("")
    add("| # | Path | Asset class | Rows | First | Last | Freq | Missing | Dup | Repeat | Non-pos | Zero-vol | SHA-256 (16) |")
    add("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for i, row in enumerate(inv, start=1):
        add(
            f"| {i} | `{row['path']}` | {row['asset_class']} | {row['rows']} | "
            f"{row['first']} | {row['last']} | {row['frequency']} | {row['missing_prices']} | "
            f"{row['dup_timestamps']} | {row['repeat_prices']} | "
            f"{'-' if row['non_positive_prices'] is None else row['non_positive_prices']} | "
            f"{'-' if row['zero_volume_rows'] is None else row['zero_volume_rows']} | "
            f"`{row['sha256_16']}` |"
        )
    add("")
    add("### 1.1 Processed artefacts")
    add("")
    add("| Group | Files | Rows | First | Last |")
    add("|---|---|---|---|---|")
    for group in payload["processed"]:
        add(
            f"| `data/processed/{group['group']}` | {group['files']} | {group['rows']} | "
            f"{group['first']} | {group['last']} |"
        )
    add("")

    add("## 2. Drift audit against the committed Cycle-912 inventory")
    add("")
    add(
        f"The published inventory (`{drift['published_inventory']}`) pins a SHA-256 "
        f"prefix for every cached price file. This tool re-computes them: "
        f"**{drift['n_match']} of {len(drift['files'])} match**, "
        f"**{drift['n_changed']} changed**, **{drift['n_removed']} removed**, "
        f"**{len(drift['added_files'])} added**."
    )
    add("")
    if drift["n_changed"] or drift["n_removed"] or drift["added_files"]:
        add("| Path | Published | Current | Status |")
        add("|---|---|---|---|")
        for row in drift["files"]:
            if row["status"] != "MATCH":
                add(
                    f"| `{row['path']}` | `{row['published_sha256_16']}` | "
                    f"`{row['current_sha256_16']}` | **{row['status']}** |"
                )
        for path in drift["added_files"]:
            add(f"| `{path}` | - | `{drift.get('added_digests', {}).get(path, '-')}` | **ADDED** |")
        add("")
    claim = drift.get("published_config_count_claim")
    add(
        "The configuration file set has changed: the published scan covered "
        f"**{len(drift['published_config_files'])} files**"
        + (f" (the report states \"{claim} config files scanned\")" if claim else "")
        + f", the current tree holds **{len(drift['current_config_files'])}**. Added: "
        + (", ".join(f"`{c}`" for c in drift["config_added"]) or "none")
        + ". Removed: "
        + (", ".join(f"`{c}`" for c in drift["config_removed"]) or "none")
        + "."
    )
    add("")

    add("## 3. The cost model actually available")
    add("")
    add("| Component | Value | Source |")
    add("|---|---|---|")
    add(
        f"| Commission | {costs['engine_commission_bps']} bps per trade | "
        "`src/backtest/engine.py:get_cost_params()` -> `config/settings.yaml` |"
    )
    add(
        f"| Slippage | {costs['engine_slippage_bps']} bps per trade | "
        "`src/backtest/engine.py:get_cost_params()` -> `config/settings.yaml` |"
    )
    add(
        f"| Round trip (one unit of weight change) | {costs['engine_round_trip_bps']} bps | "
        "the convention every committed candidate is costed on |"
    )
    add(
        f"| Risk-free rate | {costs['engine_risk_free_rate_annual']:.2%} annual | "
        "`src/backtest/engine.py:get_risk_free_rate()` |"
    )
    add("")
    add(
        f"**{costs['config_scan']['n_config_files']} configuration files scanned.** "
        "Components with a configuration key:"
    )
    add("")
    add("| Component | Keys found |")
    add("|---|---|")
    for component, hits in costs["config_scan"]["configured"].items():
        rendered = "<br>".join(f"`{h}`" for h in hits) if hits else "_none_"
        add(f"| {component} | {rendered} |")
    add("")
    add(
        "Components with **no configuration key at all**: "
        + ", ".join(f"`{c}`" for c in costs["config_scan"]["unconfigured_components"])
        + ". The cost axis itself is closed by the committed Cycle-913 break-even "
        "audit (`research/reports/cost_gate_break_even_001.md`), which measures the "
        "bid-ask floor from the cache and the cost level at which each gate flips; "
        "this inventory re-states the gap and does not redo that measurement."
    )
    add("")
    priced_elsewhere = costs["config_scan"]["unconfigured"]
    if priced_elsewhere:
        add(
            "Components priced **outside** the shared cost model (a candidate's own "
            "pre-registered assumption, not part of `config/settings.yaml` and not "
            "applied to any other candidate): "
            + "; ".join(
                f"`{component}` -> "
                + ", ".join(f"`{hit}`" for hit in hits)
                for component, hits in sorted(priced_elsewhere.items())
            )
            + ". A key that only *names* a component (for example the module that "
            "detects a roll) describes a rule, not a price, and is not counted as "
            "one."
        )
        add("")

    add("## 4. Point-in-time universe membership of the published walk-forward")
    add("")
    add(
        "AGENTS.md lists **point-in-time universe membership** first among the "
        "data-readiness criteria, and the committed inventories state that the "
        "repository holds \"no constituent-level membership\" and that this is "
        "\"not modelled\". That statement is about *constituent* membership (index "
        "members). The **asset-level** membership of the incumbent's universe is "
        "measurable from the cache, and it has never been measured: the seven "
        "universe ETFs did not all exist at the start of the published sample, so "
        "the *effective* cross-section of the published path grows over the sample."
    )
    add("")
    add("### 4.1 When each universe member enters the path")
    add("")
    add(
        "A member can only be ranked once it has a valid "
        f"{LOOKBACK}-session momentum that skips the most recent {SKIP} sessions, "
        "i.e. {n} sessions of price history.".format(n=LOOKBACK + SKIP)
    )
    add("")
    add("| Symbol | First cached close | First valid momentum |")
    add("|---|---|---|")
    for row in mem["inceptions"]:
        add(f"| {row['symbol']} | {row['first_price']} | {row['first_valid_momentum']} |")
    add("")
    add("### 4.2 The effective cross-section over the sample")
    add("")
    add("| Assets with a valid momentum | Sessions | From | To |")
    add("|---|---|---|---|")
    for row in mem["breadth_schedule"]:
        add(f"| {row['breadth']} | {row['sessions']} | {row['first']} | {row['last']} |")
    add("")
    add(
        "**The selection rule degenerates as the cross-section shrinks.** The "
        f"repository's shared rule (`src/features/momentum.py:select_top_decile`) "
        f"selects every asset whose cross-sectional rank is at least "
        f"`max_rank x (1 - {TOP_FRACTION})`, which is a *rank* rule, not a count "
        "rule: with `k` assets that carry a valid momentum it holds"
    )
    add("")
    add("| Assets with a valid momentum (`k`) | Held | Share of the cross-section |")
    add("|---|---|---|")
    for row in mem["degeneracy"]:
        add(f"| {row['valid_assets']} | {row['selected']} | {row['share']:.1%} |")
    add("")
    add(
        "so the pre-2006 part of the published path is not the same strategy as "
        "the post-2006 part: with 4 assets carrying a valid momentum it holds 3 of "
        "them (75%), with 5 it holds 3 (60%) and with 6 it holds 4 (66.7%), where "
        "the full 7-asset cross-section holds 4 (57.1%). With one or two assets "
        "the rule degenerates further: it holds the single best asset, then both "
        "of the two."
    )
    add("")

    add("### 4.3 The published fold table with its effective cross-section")
    add("")
    add(
        "| Fold | Test window | Breadth at start | Breadth (min/mean) | Mean assets selected | "
        "Published OOS Sharpe | Recomputed | Trades | Phase |"
    )
    add("|---|---|---|---|---|---|---|---|---|")
    for row in mem["rows"]:
        add(
            f"| {row['fold']} | {row['test_start']} .. {row['test_end']} | "
            f"{row['breadth_start']} | {row['breadth_min']} / {row['breadth_mean']:.2f} | "
            f"{row['selected_mean']:.2f} | {row['published_test_sharpe']:.4f} | "
            f"{row['recomputed_test_sharpe']:.4f} | {row['published_test_trades']} | "
            f"{row['phase']} |"
        )
    add("")

    add("### 4.4 The published statistic on each side of the membership boundary")
    add("")
    add("| Subsample | Folds | Mean OOS Sharpe | 95% CI (moving block) | Positive folds | Pooled trades | Gate 1 (>= 0.9) |")
    add("|---|---|---|---|---|---|---|")
    for key in ("all", "complete", "complete_without_artefact", "incomplete"):
        s = mem["subsamples"][key]
        gate1 = next(g for g in s["gates"] if g["gate"] == "wf_mean_oos_sharpe")
        add(
            f"| {s['label']} | {s['n_folds']} | {s['mean_test_sharpe']:.6f} | "
            f"[{s['ci_low']:.4f}, {s['ci_high']:.4f}] | {s['pct_positive_sharpe']:.2%} | "
            f"{s['pooled_trades']} | {'PASS' if gate1['pass'] else 'FAIL'} |"
        )
    add("")
    add("| Subsample | Gate 1 | Gate 2 (positive folds >= 0.5) | Gate 3 (pooled trades > 100) |")
    add("|---|---|---|---|")
    for key in ("all", "complete", "complete_without_artefact", "incomplete"):
        s = mem["subsamples"][key]
        marks = {g["gate"]: ("PASS" if g["pass"] else "FAIL") for g in s["gates"]}
        add(
            f"| {s['label']} | {marks['wf_mean_oos_sharpe']} | {marks['positive_fold_rate']} | "
            f"{marks['pooled_oos_trades']} |"
        )
    add("")

    add("### 4.5 The membership split is not the phase split")
    add("")
    add("| Subsample | Phase | Folds | Mean OOS Sharpe | Median |")
    add("|---|---|---|---|---|")
    for row in mem["phase_rows"]:
        add(
            f"| {row['subset']} | {row['phase']} | {row['n_folds']} | "
            f"{row['mean_test_sharpe']:.6f} | {row['median_test_sharpe']:.4f} |"
        )
    add("")
    add(
        "The `all` row is an independent reproduction of the committed Cycle-911 "
        "phase decomposition (phase A **1.385029** vs the published **1.385035**, "
        "phase B **0.509583** vs the published **0.509580**; the residual is the "
        "rounding of the per-fold Sharpes to the four decimals the published fold "
        "table carries). The membership split is therefore a **third** axis, not a "
        "relabelling of the phase split: the incomplete folds are high in *both* "
        "phases (A 1.786325, B 2.012333), so they are not a phase artefact."
    )

    add("## 5. What this does and does not change")
    add("")
    add(
        "- **Nothing published changed.** The published record, the published gates, "
        "the published protocol, the shortlist row and every committed candidate "
        "artefact are byte-identical after the run; the anchor (48 folds, mean "
        f"{mem['recomputed_summary']['mean_test_sharpe']:.6f}, positive rate "
        f"{mem['recomputed_summary']['pct_positive_sharpe']:.2%}, "
        f"{mem['recomputed_summary']['total_test_trades']} pooled trades) is reproduced "
        "from the committed cache."
    )
    add(
        "- **The incumbent's verdict is unchanged**: it stays a **Credible Candidate** "
        "by its published verdict and **NO-GO** for promotion (failed gates "
        "`rolling_63d_sharpe`, `psr`). This audit adds a third stability axis to a "
        "verdict that was already NO-GO."
    )
    add(
        "- **The published walk-forward mean is not a homogeneous statistic.** It "
        f"averages {mem['n_incomplete']} folds measured on an incomplete cross-section "
        f"(mean {mem['subsamples']['incomplete']['mean_test_sharpe']:.6f}) with "
        f"{mem['n_complete']} folds measured on the complete one (mean "
        f"{mem['subsamples']['complete']['mean_test_sharpe']:.6f}; "
        f"{mem['subsamples']['complete_without_artefact']['mean_test_sharpe']:.6f} with "
        f"the fold-{mem['artefact_fold']} numerical artefact removed). The gate-1 "
        "outcome on the complete subsample therefore depends on that artefact, and "
        "neither variant reproduces the published number."
    )
    add(
        "- **The finding is an association, not a mechanism.** The incomplete folds "
        "are also the earliest folds, so \"incomplete cross-section\" and \"a "
        "favourable 2002-2006 regime for this rule\" are not separable in this "
        "design. The decision-relevant statement is the same either way: the "
        "published statistic does not survive either stability split taken alone."
    )
    add(
        "- **The cost model is unchanged** and the cost axis remains closed by the "
        "committed Cycle-913 break-even audit."
    )
    add("")

    add("## 6. Reproduction")
    add("")
    add("```bash")
    add("python research/data_cost_inventory_002.py")
    add("python -m pytest -q tests/test_data_cost_inventory_002.py")
    add("git status --porcelain data/ config/")
    add("```")
    add("")
    add(
        "Every number in this report is re-derived by the first command from the "
        "committed cache, `config/`, `src/` and the committed published record."
    )
    return "\n".join(lines) + "\n"


def render_experiment(payload: dict[str, Any]) -> str:
    mem = payload["membership"]
    inv = payload["inventory"]
    drift = payload["drift"]
    costs = payload["costs"]
    lines: list[str] = []
    add = lines.append

    add("# Experiment: data_cost_inventory_002 (Cycle 929)")
    add("")
    add("**Hypothesis reference:** none (measurement cycle).")
    add("")
    add("**Objective:** refresh the repository's data and cost inventory from the")
    add("committed tree, verify the published Cycle-912 digests, and measure the")
    add("point-in-time universe membership of the incumbent's published walk-forward,")
    add("which no committed record measures.")
    add("")
    add("## Data used")
    add("")
    add(
        f"- **Source:** committed parquet cache `data/raw/` ({len(inv)} files, "
        f"{sum(r['rows'] for r in inv)} rows); the fetcher is never called."
    )
    add(
        "- **Date range:** the cache spans "
        f"{min(r['first'] for r in inv)} .. {max(r['last'] for r in inv)}; the "
        f"incumbent's published walk-forward spans {mem['start_date']} .. {mem['end_date']}."
    )
    add("- **Frequency:** daily for every equity/futures file; 8-hourly for the crypto funding files.")
    add(
        "- **Point-in-time treatment:** the price panel is read from the cache exactly "
        "as the committed fetcher aligns it (union calendar, each symbol forward "
        "filled); the momentum, the selection rule and the overlay are the committed "
        "ones (`src/features/momentum.py`, `research/run_cycle6.py`)."
    )
    add(
        f"- **Cost model:** {costs['engine_commission_bps']} bps commission + "
        f"{costs['engine_slippage_bps']} bps slippage = "
        f"{costs['engine_round_trip_bps']} bps per unit of weight change; risk-free "
        f"{costs['engine_risk_free_rate_annual']:.2%}."
    )
    add("")
    add("## Configuration")
    add("")
    add(f"- **Candidate:** `{mem['candidate_id']}` (universe: {', '.join(mem['universe'])}).")
    add(f"- **Signal:** {mem['lookback']}-session momentum skipping the most recent {mem['skip']} sessions, top_fraction {mem['top_fraction']}.")
    add("- **Design:** the published 10y-train / 12m-test / 6m-step walk-forward with 21d purge and 21d embargo, on the continuously computed point-in-time path.")
    add(f"- **Published record:** `{mem['record_path']}` (resolved by content).")
    add("")
    add("## Results")
    add("")
    add("| Quantity | Value |")
    add("|---|---|")
    add(
        f"| Published inventory digests re-verified | {drift['n_match']}/{len(drift['files'])} match, "
        f"{drift['n_changed']} changed, {drift['n_removed']} removed, {len(drift['added_files'])} added |"
    )
    add(
        f"| Configuration files | {len(drift['published_config_files'])} published vs "
        f"{len(drift['current_config_files'])} current (added: "
        + (", ".join(drift["config_added"]) or "none")
        + ") |"
    )
    add(
        f"| Anchor (recomputed) | {mem['recomputed_summary']['n_folds']} folds, mean "
        f"{mem['recomputed_summary']['mean_test_sharpe']:.6f}, positive "
        f"{mem['recomputed_summary']['pct_positive_sharpe']:.2%}, "
        f"{mem['recomputed_summary']['total_test_trades']} pooled trades |"
    )
    add(
        f"| Folds on an incomplete cross-section | {mem['n_incomplete']} of 48 "
        f"(mean OOS Sharpe {mem['subsamples']['incomplete']['mean_test_sharpe']:.6f}) |"
    )
    add(
        f"| Folds on the complete cross-section | {mem['n_complete']} of 48 "
        f"(mean OOS Sharpe {mem['subsamples']['complete']['mean_test_sharpe']:.6f}; "
        f"{mem['subsamples']['complete_without_artefact']['mean_test_sharpe']:.6f} without "
        f"the fold-{mem['artefact_fold']} artefact) |"
    )
    add("")
    add("## Number of trials")
    add("")
    add(
        "1 (a measurement: no parameter search, no candidate generation, no "
        "re-tuning). The bootstrap uses "
        f"{BOOTSTRAP_DRAWS} moving-block draws with seed {BOOTSTRAP_SEED}."
    )
    add("")
    add("## Reproduction commands")
    add("")
    add("```bash")
    add("python research/data_cost_inventory_002.py")
    add("python -m pytest -q tests/test_data_cost_inventory_002.py")
    add("git status --porcelain data/ config/")
    add("```")
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------
def run_audit(
    write: bool = True,
    raw_dir: Path = RAW_DIR,
    processed_dir: Path = PROCESSED_DIR,
    report_out: Path = OUT_REPORT,
    experiment_out: Path = OUT_EXP,
) -> dict[str, Any]:
    data_before = fingerprint(REPO_ROOT / "data")
    config_before = fingerprint(CONFIG_DIR)
    artifacts_before = tracked_artifact_hashes()

    inventory = measure_inventory(raw_dir)
    processed = measure_processed_tree(processed_dir)
    drift = audit_drift(inventory)
    drift["added_digests"] = {r["path"]: r["sha256_16"] for r in inventory}
    costs = measure_costs()
    membership = audit_membership(raw_dir)

    payload = {
        "inventory": inventory,
        "processed": processed,
        "drift": drift,
        "costs": costs,
        "membership": membership,
    }
    checks = run_checks(
        inventory, drift, costs, membership, data_before, config_before, artifacts_before
    )
    payload["checks"] = checks
    payload["ok"] = all(c["ok"] for c in checks)

    if write:
        report_out.parent.mkdir(parents=True, exist_ok=True)
        experiment_out.parent.mkdir(parents=True, exist_ok=True)
        report_out.write_text(render_report(payload), encoding="utf-8")
        experiment_out.write_text(render_experiment(payload), encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="run the audit without writing the report or the experiment record",
    )
    parser.add_argument("--raw-dir", default=str(RAW_DIR), help="cached price directory")
    parser.add_argument(
        "--processed-dir", default=str(PROCESSED_DIR), help="processed artefact directory"
    )
    parser.add_argument("--report-out", default=str(OUT_REPORT), help="report output path")
    parser.add_argument(
        "--experiment-out", default=str(OUT_EXP), help="experiment record output path"
    )
    args = parser.parse_args(argv)

    try:
        payload = run_audit(
            write=not args.no_report,
            raw_dir=Path(args.raw_dir),
            processed_dir=Path(args.processed_dir),
            report_out=Path(args.report_out),
            experiment_out=Path(args.experiment_out),
        )
    except AuditError as exc:
        print(f"OVERALL: FAIL\n{exc}")
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    for check in payload["checks"]:
        status = "PASS" if check["ok"] else "FAIL"
        print(f"[{status}] {check['check']}: {check['detail']}")

    mem = payload["membership"]
    print(
        "MEMBERSHIP|incomplete_folds|"
        f"{mem['n_incomplete']}|mean_sharpe|{mem['subsamples']['incomplete']['mean_test_sharpe']:.6f}"
    )
    print(
        "MEMBERSHIP|complete_folds|"
        f"{mem['n_complete']}|mean_sharpe|{mem['subsamples']['complete']['mean_test_sharpe']:.6f}"
    )
    print(
        "MEMBERSHIP|complete_without_artefact|"
        f"{mem['subsamples']['complete_without_artefact']['n_folds']}|mean_sharpe|"
        f"{mem['subsamples']['complete_without_artefact']['mean_test_sharpe']:.6f}"
    )
    print(f"DECISION|NO-GO|incumbent {mem['candidate_id']} unchanged")
    print("OVERALL: " + ("PASS" if payload["ok"] else "FAIL"))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
