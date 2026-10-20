#!/usr/bin/env python3
"""Common-inception sample audit (Cycle 903).

The incumbent's published long-sample evidence is computed on the **union
calendar** of the raw cache (1993-01-29..2026-10-19, 8,488 sessions),
because ``src/backtest/engine.py:run_backtest`` does not slice the price
frame it loads, while the frozen configuration describes a **seven-asset
universe** whose first fully populated date is 2004-11-18.  The published
numbers are therefore the numbers of a 1-to-7-asset strategy.

This tool measures the incumbent's canonical metrics and its **full promotion
gate table** on that common-inception sample and publishes them next to the
union-sample numbers, so that it is known whether the published NO-GO
verdict is an artefact of the sample definition.

Two common-inception variants are published:

``common_inception_slice``
    The aligned price frame is truncated to 2004-11-18 *before* the signal,
    cost model, universe, lookback / skip / top_fraction and rebalance
    semantics are applied -- the literal reading of "the sample the frozen
    configuration describes".  The first 248 sessions are held flat (no
    asset has a 226+21-session momentum history yet), which is published
    with the result.

``common_inception_window``
    The union path restricted to the sessions from 2004-11-18 onwards: the
    signals are still formed with the pre-inception history (warm-up), so
    this variant isolates the *window* effect from the *warm-up* effect.

Read-only and decision-neutral:

* nothing under ``data/`` or ``config/`` is written (checked by fingerprint),
* the committed long-sample artifact is read, never regenerated or edited
  (checked byte-for-byte before and after the run),
* no gate, threshold, decision mapping, candidate configuration, universe,
  cost model or Sharpe convention is changed,
* the incumbent's published decision (NO-GO) is not changed here; the choice
  of the sample on which the *long-sample diagnostic's* gate table is evaluated
  is left to an explicitly recorded decision, and the evidence for that
  decision is published here.  (The promotion decision itself is made on the
  paper record, which the long-sample diagnostic's sample does not affect.)
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.promotion_feasibility_backtest import (  # noqa: E402
    PSR_TARGET_BACKTEST_SCALE,
    count_regime_flips,
    load_yaml,
    rolling_window,
    scan_raw_cache,
)
from src.backtest import engine  # noqa: E402
from src.backtest.engine import run_backtest  # noqa: E402
from src.data.yfinance_fetcher import fetch_universe  # noqa: E402
from src.evaluation.sharpe import backtest_sharpe_ratio, sharpe_ratio  # noqa: E402
from src.evaluation.statistics import compute_psr  # noqa: E402
from src.evaluation.utils import max_drawdown  # noqa: E402
from src.features.momentum import compute_momentum  # noqa: E402
from src.simulation.evaluation import (  # noqa: E402
    classify_psr,
    evaluate_promotion_gates,
    map_decision,
)

CONFIG_CAND = REPO_ROOT / "config" / "simulation_candidate_001.yaml"
CONFIG_GATES = REPO_ROOT / "config" / "promotion_gates.yaml"
RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
COMMITTED_REPORT = REPORTS_DIR / "promotion_feasibility_backtest_001.md"
OUT_REPORT = REPORTS_DIR / "common_inception_sample_audit_001.md"

PSR_SEED = 20240101
ROLLING_WINDOW = 63
MOMENTUM_BREADTH_FALLBACK = 5  # select_top_decile's single-asset fallback threshold


# ----------------------------------------------------------------------
# Read-only helpers
# ----------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fingerprint_tree(root: Path) -> dict[str, str]:
    """SHA-256 of every file under *root* (relative path -> digest)."""
    out: dict[str, str] = {}
    if not root.exists():
        return out
    for path in sorted(root.rglob("*")):
        if path.is_file():
            out[str(path.relative_to(REPO_ROOT))] = sha256_file(path)
    return out


def parse_json_block(text: str, header: str) -> Any:
    """Parse the first ```json block that follows *header*."""
    if header not in text:
        raise KeyError(f"header not found in artifact: {header}")
    start = text.index("```json", text.index(header)) + len("```json")
    end = text.index("```", start)
    return json.loads(text[start:end])


def parse_decision_bullets(text: str) -> dict[str, Any]:
    """Parse the ``- decision:`` / ``- failed_gates:`` / ``- psr_zone:`` bullets."""
    section = text[text.index("## Decision"):]
    section = section[: section.index("##", 3)]
    out: dict[str, Any] = {}
    for key in ("decision", "failed_gates", "psr_zone"):
        match = re.search(rf"^- {key}:\s*(.+)$", section, flags=re.MULTILINE)
        if match is None:
            raise KeyError(f"decision bullet not found: {key}")
        value = match.group(1).strip()
        if key == "failed_gates":
            out[key] = ast.literal_eval(value)
        else:
            out[key] = value
    return out


# ----------------------------------------------------------------------
# Sample construction
# ----------------------------------------------------------------------
def aligned_close(universe: list[str], start_date: str, end_date: str) -> pd.DataFrame:
    """The aligned, forward-filled Close frame the engine works on."""
    data = fetch_universe(universe, start_date, end_date, force=False)
    if data.empty:
        raise RuntimeError("No data fetched")
    close = data.xs("Close", level=0, axis=1)
    return close.ffill().dropna(how="all")


def width_series(close: pd.DataFrame, index: pd.DatetimeIndex) -> pd.Series:
    """Number of assets with a price on each session of *index*."""
    return close.reindex(index).notna().sum(axis=1)


def width_changes(width: pd.Series) -> list[dict[str, Any]]:
    """The sessions on which the cross-section width changes.

    The first observation is the sample's *opening* width, not a change, so it
    is not listed here; it is published separately as ``opening_width``.
    """
    changes: list[dict[str, Any]] = []
    previous: int | None = None
    for stamp, value in width.items():
        count = int(value)
        if previous is None:
            previous = count
            continue
        if count != previous:
            changes.append({"date": stamp.date().isoformat(), "assets_with_price": count})
            previous = count
    return changes


def sliced_fetch_factory(start: pd.Timestamp):
    """A ``fetch_universe`` replacement that truncates the aligned frame."""

    def sliced_fetch(symbols, start_date, end_date, force=False, raw_dir=None):
        data = fetch_universe(symbols, start_date, end_date, force=force, raw_dir=raw_dir)
        if data.empty:
            raise RuntimeError("No data fetched")
        return data.loc[data.index >= start]

    return sliced_fetch


def sample_metrics(net_ret: pd.Series) -> dict[str, Any]:
    """Canonical metrics of one sample (same definitions as the long-sample artifact)."""
    if net_ret.empty:
        raise RuntimeError("empty return series")
    rolling_sharpe_63d, rolling_mdd_63d = rolling_window(net_ret, ROLLING_WINDOW)
    psr_res = compute_psr(net_ret, sr_target=PSR_TARGET_BACKTEST_SCALE, seed=PSR_SEED)
    return {
        "sessions": int(len(net_ret)),
        "start_date": net_ret.index.min().date().isoformat(),
        "end_date": net_ret.index.max().date().isoformat(),
        "paper_sharpe": sharpe_ratio(net_ret),
        "paper_max_dd": max_drawdown(net_ret),
        "rolling_sharpe_63d": rolling_sharpe_63d,
        "rolling_63d_max_dd": rolling_mdd_63d,
        "paper_days": int(len(net_ret)),
        "sharpe_observed_canonical": float(psr_res["sharpe_observed"]),
        "sharpe_se": float(psr_res["sharpe_se"]),
        "sharpe_backtest_scale": backtest_sharpe_ratio(net_ret),
        "psr_normal": float(psr_res["psr_normal"]),
        "psr_empirical": float(psr_res["psr_empirical"]),
        "psr_ci_lower": float(psr_res["ci_lower"]),
        "psr_ci_upper": float(psr_res["ci_upper"]),
        "zero_return_sessions": int((net_ret == 0.0).sum()),
    }


def evaluate_gates(gates: dict, metrics: dict, regime_flips: int) -> dict[str, Any]:
    """The repository's own promotion-gate machinery on one sample.

    ``src/simulation/evaluation.py`` is the production implementation of the
    gate table defined by ``config/promotion_gates.yaml``; it is used here
    unchanged, so the common-inception table cannot drift from the table the
    paper record is judged by.
    """
    metric_values = {
        "paper_days": float(metrics["paper_days"]),
        "paper_sharpe": float(metrics["paper_sharpe"]),
        "paper_max_dd": float(metrics["paper_max_dd"]),
        "rolling_sharpe_63d": float(metrics["rolling_sharpe_63d"]),
        "rolling_max_dd_63d": float(metrics["rolling_63d_max_dd"]),
        "regime_flips": float(regime_flips),
        "psr_normal": float(metrics["psr_normal"]),
    }
    evaluations = evaluate_promotion_gates(metric_values, gates["gates"])
    table: dict[str, Any] = {}
    failed: list[str] = []
    for evaluation in evaluations:
        table[evaluation.name] = {
            "value": evaluation.value,
            "threshold": evaluation.threshold,
            "comparison": evaluation.comparison,
            "pass": bool(evaluation.passed),
        }
        if not evaluation.passed:
            failed.append(evaluation.name)
    zone = classify_psr(metrics["psr_normal"], gates["psr_grey_zone"])
    decision, rationale, conditions = map_decision(
        evaluations,
        metrics["psr_normal"],
        gates["psr_grey_zone"],
        gates["decision_mapping"],
    )
    return {
        "gates": table,
        "failed_gates": failed,
        "psr_zone": zone,
        "decision": decision,
        "rationale": rationale,
        "conditions_for_reevaluation": conditions,
    }


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main() -> int:
    cand = load_yaml(CONFIG_CAND)
    gates = load_yaml(CONFIG_GATES)
    universe = list(cand["universe"])
    lookback = int(cand["signal"]["lookback"])
    skip = int(cand["signal"]["skip"])
    top_fraction = float(cand["signal"]["top_fraction"])
    rebalance_freq = cand["signal"]["rebalance_freq"]

    data_fingerprint_before = fingerprint_tree(REPO_ROOT / "data")
    config_fingerprint_before = fingerprint_tree(REPO_ROOT / "config")
    committed_before = COMMITTED_REPORT.read_bytes() if COMMITTED_REPORT.exists() else b""

    # -- the raw cache, scanned independently of the engine --------------
    per_symbol_stats, raw_hashes, union_index = scan_raw_cache(universe)
    union_start = union_index.min().date().isoformat()
    union_end = union_index.max().date().isoformat()
    common_inception = pd.Timestamp(
        max(stats["first_date"] for stats in per_symbol_stats.values()), tz="UTC"
    )
    common_inception_str = common_inception.date().isoformat()

    close = aligned_close(universe, union_start, union_end)
    union_width = width_series(close, union_index)
    momentum = compute_momentum(close, lookback=lookback, skip=skip)
    momentum_breadth = momentum.notna().sum(axis=1)

    # -- the three sample paths -----------------------------------------
    union_net, union_weights, _ = run_backtest(
        symbols=universe,
        start_date=union_start,
        end_date=union_end,
        lookback=lookback,
        skip=skip,
        top_fraction=top_fraction,
        rebalance_freq=rebalance_freq,
    )
    with patch.object(
        engine, "fetch_universe", sliced_fetch_factory(common_inception)
    ):
        slice_net, slice_weights, _ = run_backtest(
            symbols=universe,
            start_date=common_inception_str,
            end_date=union_end,
            lookback=lookback,
            skip=skip,
            top_fraction=top_fraction,
            rebalance_freq=rebalance_freq,
        )
    window_net = union_net.loc[common_inception:]

    realized_index = pd.DatetimeIndex(union_net.index)
    union_realized = {
        "start_date": realized_index.min().date().isoformat(),
        "end_date": realized_index.max().date().isoformat(),
        "sessions": int(len(realized_index)),
        "equals_raw_cache_union": bool(
            len(realized_index) == len(union_index)
            and realized_index.equals(union_index)
        ),
    }

    regime_flips = count_regime_flips(PROCESSED_DIR / "paper_trading_state.yaml")

    # -- where the union sample's numbers come from ---------------------
    pre_net = union_net.loc[union_net.index < common_inception]
    union_cum = (1.0 + union_net).cumprod()
    union_dd = union_cum / union_cum.expanding().max() - 1.0
    trough = union_dd.idxmin()
    peak = union_cum.loc[:trough].idxmax()
    era = {
        "before_common_inception": {
            "sessions": int(len(pre_net)),
            "start_date": pre_net.index.min().date().isoformat(),
            "end_date": pre_net.index.max().date().isoformat(),
            "sharpe": sharpe_ratio(pre_net),
            "max_drawdown": max_drawdown(pre_net),
        },
        "from_common_inception": {
            "sessions": int(len(window_net)),
            "start_date": window_net.index.min().date().isoformat(),
            "end_date": window_net.index.max().date().isoformat(),
            "sharpe": sharpe_ratio(window_net),
            "max_drawdown": max_drawdown(window_net),
        },
        "union_max_drawdown": {
            "value": float(union_dd.min()),
            "peak_date": peak.date().isoformat(),
            "trough_date": trough.date().isoformat(),
            "is_pre_common_inception": bool(trough < common_inception),
            "note": (
                "the union sample's maximum drawdown is a peak-to-trough episode "
                "that opens before the common inception; the common-inception "
                "sample cannot contain it"
            ),
        },
    }

    samples: dict[str, dict[str, Any]] = {}
    for name, series, definition in (
        (
            "union_sample",
            union_net,
            "the union calendar of the raw cache (the sample the committed "
            "long-sample artifact computes)",
        ),
        (
            "common_inception_slice",
            slice_net,
            "the aligned price frame truncated to the common inception "
            f"{common_inception_str} before the signal, cost model, universe, "
            "lookback/skip/top_fraction and rebalance semantics are applied",
        ),
        (
            "common_inception_window",
            window_net,
            "the union path restricted to the sessions from the common "
            f"inception {common_inception_str} onwards (warm-up preserved)",
        ),
    ):
        metrics = sample_metrics(series)
        evaluation = evaluate_gates(gates, metrics, regime_flips)
        positions = (union_weights if name != "common_inception_slice" else slice_weights)
        position_counts = (positions > 0).sum(axis=1)
        position_counts = position_counts.reindex(series.index).fillna(0).astype(int)
        samples[name] = {
            "label": name,
            "definition": definition,
            "metrics": metrics,
            "gates": evaluation["gates"],
            "failed_gates": evaluation["failed_gates"],
            "psr_zone": evaluation["psr_zone"],
            "decision": evaluation["decision"],
            "rationale": evaluation["rationale"],
            "conditions_for_reevaluation": evaluation["conditions_for_reevaluation"],
            "positions": {
                "mean_positions_held": float(position_counts.mean()),
                "median_positions_held": float(position_counts.median()),
                "sessions_with_one_position": int((position_counts == 1).sum()),
                "sessions_with_no_position": int((position_counts == 0).sum()),
            },
        }

    # -- cross-section width per sample ---------------------------------
    for name, series in (
        ("union_sample", union_net),
        ("common_inception_slice", slice_net),
        ("common_inception_window", window_net),
    ):
        width = union_width.reindex(series.index)
        breadth = momentum_breadth.reindex(series.index)
        samples[name]["cross_section"] = {
            "sessions": int(len(series)),
            "opening_date": series.index.min().date().isoformat(),
            "opening_width": int(width.iloc[0]),
            "price_width_min": int(width.min()),
            "price_width_median": float(width.median()),
            "price_width_max": int(width.max()),
            "price_width_change_dates": width_changes(width),
            "momentum_breadth_min": int(breadth.min()),
            "momentum_breadth_median": float(breadth.median()),
            "momentum_breadth_max": int(breadth.max()),
            "momentum_breadth_change_dates": width_changes(breadth),
            "sessions_with_fewer_than_five_selectable_assets": int(
                (breadth < MOMENTUM_BREADTH_FALLBACK).sum()
            ),
        }

    # -- the warm-up ramp of the sliced sample ---------------------------
    slice_nonzero = slice_net[slice_net != 0.0]
    first_position_date = None
    slice_position_counts = (slice_weights > 0).sum(axis=1)
    held = slice_position_counts[slice_position_counts > 0]
    if not held.empty:
        first_position_date = held.index.min().date().isoformat()
    differing = slice_net.index[~np.isclose(slice_net.values, window_net.values)]
    warmup = {
        "flat_sessions_before_the_first_signal": int((slice_net == 0.0).sum()),
        "first_non_zero_return_date": (
            slice_nonzero.index.min().date().isoformat() if not slice_nonzero.empty else None
        ),
        "first_session_with_a_position": first_position_date,
        "sessions_differing_from_the_warmup_variant": int(len(differing)),
        "first_differing_session": (
            differing.min().date().isoformat() if len(differing) else None
        ),
        "last_differing_session": (
            differing.max().date().isoformat() if len(differing) else None
        ),
        "note": (
            "the sliced sample has no momentum history for 226+21 sessions, so "
            "it is held flat (zero position, zero return, zero cost) until the "
            "first signal; the warm-up variant forms the same signals from the "
            "pre-inception history and therefore differs only in that ramp"
        ),
    }

    # -- the union sample against the committed artifact -----------------
    committed_text = COMMITTED_REPORT.read_text()
    committed_sample = parse_json_block(committed_text, "## Sample definition")
    committed_canonical = parse_json_block(
        committed_text, "## Canonical metrics (arithmetic_annualized_rf0)"
    )
    committed_psr = parse_json_block(committed_text, "## PSR vs backtest baseline 1.4178")
    committed_gates = parse_json_block(
        committed_text, "## Gate evaluation (same table as config/promotion_gates.yaml)"
    )
    committed_decision = parse_decision_bullets(committed_text)

    union_metrics = samples["union_sample"]["metrics"]
    union_canonical = {
        "paper_sharpe": union_metrics["paper_sharpe"],
        "paper_max_dd": union_metrics["paper_max_dd"],
        "rolling_sharpe_63d": union_metrics["rolling_sharpe_63d"],
        "rolling_63d_max_dd": union_metrics["rolling_63d_max_dd"],
        "regime_flips": regime_flips,
        "paper_days": union_metrics["paper_days"],
        "sharpe_observed_canonical": union_metrics["sharpe_observed_canonical"],
        "sharpe_se": union_metrics["sharpe_se"],
    }
    union_psr = {
        "psr_normal": union_metrics["psr_normal"],
        "psr_empirical": union_metrics["psr_empirical"],
    }

    equality_checks = [
        {
            "name": "union_sample_window",
            "expected": {
                "start_date": committed_sample["realized_start_date"],
                "end_date": committed_sample["realized_end_date"],
                "sessions": committed_sample["realized_session_count"],
            },
            "observed": {
                "start_date": union_realized["start_date"],
                "end_date": union_realized["end_date"],
                "sessions": union_realized["sessions"],
            },
            "pass": bool(
                union_realized["start_date"] == committed_sample["realized_start_date"]
                and union_realized["end_date"] == committed_sample["realized_end_date"]
                and union_realized["sessions"] == committed_sample["realized_session_count"]
            ),
        },
        {
            "name": "union_sample_canonical_metrics",
            "expected": committed_canonical,
            "observed": union_canonical,
            "pass": bool(union_canonical == committed_canonical),
        },
        {
            "name": "union_sample_psr",
            "expected": {
                "psr_normal": committed_psr["psr_normal"],
                "psr_empirical": committed_psr["psr_empirical"],
            },
            "observed": union_psr,
            "pass": bool(union_psr == {
                "psr_normal": committed_psr["psr_normal"],
                "psr_empirical": committed_psr["psr_empirical"],
            }),
        },
        {
            "name": "union_sample_gate_table",
            "expected": committed_gates,
            "observed": samples["union_sample"]["gates"],
            "pass": bool(samples["union_sample"]["gates"] == committed_gates),
        },
        {
            "name": "union_sample_decision",
            "expected": {
                "decision": committed_decision["decision"],
                "failed_gates": committed_decision["failed_gates"],
            },
            "observed": {
                "decision": samples["union_sample"]["decision"],
                "failed_gates": samples["union_sample"]["failed_gates"],
            },
            "pass": bool(
                samples["union_sample"]["decision"] == committed_decision["decision"]
                and samples["union_sample"]["failed_gates"]
                == committed_decision["failed_gates"]
            ),
        },
    ]

    # -- read-only and structural checks --------------------------------
    data_fingerprint_after = fingerprint_tree(REPO_ROOT / "data")
    config_fingerprint_after = fingerprint_tree(REPO_ROOT / "config")
    committed_after = COMMITTED_REPORT.read_bytes() if COMMITTED_REPORT.exists() else b""

    structural_checks = [
        {
            "name": "data_and_config_unchanged",
            "expected": "identical SHA-256 fingerprint of every file under data/ and config/",
            "observed": {
                "data_files": len(data_fingerprint_after),
                "config_files": len(config_fingerprint_after),
                "data_unchanged": data_fingerprint_after == data_fingerprint_before,
                "config_unchanged": config_fingerprint_after == config_fingerprint_before,
            },
            "pass": bool(
                data_fingerprint_after == data_fingerprint_before
                and config_fingerprint_after == config_fingerprint_before
            ),
        },
        {
            "name": "committed_artifact_untouched",
            "expected": "byte-identical research/reports/promotion_feasibility_backtest_001.md",
            "observed": {"unchanged": committed_after == committed_before},
            "pass": bool(committed_after == committed_before),
        },
        {
            "name": "union_sample_equals_raw_cache_union_index",
            "expected": {
                "first_date": union_index.min().date().isoformat(),
                "last_date": union_index.max().date().isoformat(),
                "count": int(len(union_index)),
            },
            "observed": union_realized,
            "pass": bool(union_realized["equals_raw_cache_union"]),
        },
        {
            "name": "common_inception_sample_is_fully_populated",
            "expected": {
                "price_width_min": 7,
                "price_width_max": 7,
                "momentum_breadth_min": 6,
                "start_date": common_inception_str,
                "end_date": union_end,
            },
            "observed": {
                "price_width_min": samples["common_inception_slice"]["cross_section"][
                    "price_width_min"
                ],
                "price_width_max": samples["common_inception_slice"]["cross_section"][
                    "price_width_max"
                ],
                "momentum_breadth_min": samples["common_inception_slice"]["cross_section"][
                    "momentum_breadth_min"
                ],
                "start_date": samples["common_inception_slice"]["metrics"]["start_date"],
                "end_date": samples["common_inception_slice"]["metrics"]["end_date"],
            },
            "pass": bool(
                samples["common_inception_slice"]["cross_section"]["price_width_min"] == 7
                and samples["common_inception_slice"]["cross_section"]["price_width_max"] == 7
                and samples["common_inception_slice"]["cross_section"]["momentum_breadth_min"]
                >= MOMENTUM_BREADTH_FALLBACK
                and samples["common_inception_slice"]["metrics"]["start_date"]
                == common_inception_str
                and samples["common_inception_slice"]["metrics"]["end_date"] == union_end
            ),
        },
        {
            "name": "common_inception_sample_sessions_are_a_subset_of_the_union_sample",
            "expected": "every common-inception session exists in the union sample",
            "observed": {
                "slice_sessions": int(len(slice_net)),
                "window_sessions": int(len(window_net)),
                "subset": bool(
                    set(slice_net.index).issubset(set(union_net.index))
                    and set(window_net.index).issubset(set(union_net.index))
                ),
            },
            "pass": bool(
                set(slice_net.index).issubset(set(union_net.index))
                and set(window_net.index).issubset(set(union_net.index))
            ),
        },
    ]

    checks = equality_checks + structural_checks
    overall = "PASS" if all(bool(c["pass"]) for c in checks) else "FAIL"

    # -- the sensitivity verdict -----------------------------------------
    union_sample = samples["union_sample"]
    slice_sample = samples["common_inception_slice"]
    window_sample = samples["common_inception_window"]
    gate_names = list(union_sample["gates"].keys())
    sensitivity = {
        "gates_that_disagree": [
            name
            for name in gate_names
            if union_sample["gates"][name]["pass"]
            != slice_sample["gates"][name]["pass"]
        ],
        "decision_union": union_sample["decision"],
        "decision_common_inception_slice": slice_sample["decision"],
        "decision_common_inception_window": window_sample["decision"],
        "decision_agrees": bool(
            union_sample["decision"] == slice_sample["decision"]
            and union_sample["decision"] == window_sample["decision"]
        ),
        "failed_gates_union": union_sample["failed_gates"],
        "failed_gates_common_inception_slice": slice_sample["failed_gates"],
        "failed_gates_common_inception_window": window_sample["failed_gates"],
        "metric_deltas_common_inception_slice_minus_union": {
            "paper_sharpe": slice_sample["metrics"]["paper_sharpe"]
            - union_sample["metrics"]["paper_sharpe"],
            "paper_max_dd": slice_sample["metrics"]["paper_max_dd"]
            - union_sample["metrics"]["paper_max_dd"],
            "psr_normal": slice_sample["metrics"]["psr_normal"]
            - union_sample["metrics"]["psr_normal"],
        },
        "metric_deltas_common_inception_window_minus_union": {
            "paper_sharpe": window_sample["metrics"]["paper_sharpe"]
            - union_sample["metrics"]["paper_sharpe"],
            "paper_max_dd": window_sample["metrics"]["paper_max_dd"]
            - union_sample["metrics"]["paper_max_dd"],
            "psr_normal": window_sample["metrics"]["psr_normal"]
            - union_sample["metrics"]["psr_normal"],
        },
    }

    # -- the published artifact ------------------------------------------
    report = {
        "question": (
            "Are the incumbent's published long-sample numbers and its NO-GO "
            "verdict an artefact of the sample definition (the union calendar "
            "of the raw cache) rather than of the strategy?"
        ),
        "status": "measurement, not a decision",
        "candidate": {
            "candidate_id": cand["candidate_id"],
            "universe": universe,
            "lookback": lookback,
            "skip": skip,
            "top_fraction": top_fraction,
            "rebalance_freq": rebalance_freq,
            "cost_model": {k: float(v) for k, v in cand.get("cost_model", {}).items()},
        },
        "data": {
            "source": "committed raw cache (data/raw/*.parquet)",
            "universe": universe,
            "union_start_date": union_start,
            "union_end_date": union_end,
            "union_sessions": int(len(union_index)),
            "common_inception": common_inception_str,
            "per_symbol_stats": per_symbol_stats,
            "sha256_raw_files": raw_hashes,
            "point_in_time_treatment": (
                "signals use only data up to the formation session, positions are "
                "effective on the next session (build_weights shifts by one day); "
                "no forward-looking data is used"
            ),
            "missing_data_handling": (
                "the engine forward-fills each symbol on the union calendar; the "
                "cross-section width published here counts the assets that have a "
                "price on each session"
            ),
        },
        "samples": {
            name: {
                key: value
                for key, value in sample.items()
                if key not in ("metrics",)
            }
            for name, sample in samples.items()
        },
        "sample_metrics": {
            name: sample["metrics"] for name, sample in samples.items()
        },
        "union_realized_window": union_realized,
        "era_decomposition": era,
        "warmup_ramp": warmup,
        "committed_artifact_equality_checks": equality_checks,
        "structural_checks": structural_checks,
        "sample_definition_sensitivity": sensitivity,
        "verdict": {
            "measurement": (
                "the sample definition changes the published numbers materially "
                "and does not change the verdict"
                if sensitivity["decision_agrees"]
                else "the sample definition changes the verdict"
            ),
            "incumbent_published_decision": union_sample["decision"],
            "incumbent_published_decision_changed": False,
            "deferred_decision": (
                "which sample the long-sample diagnostic's gate table is evaluated on "
                "is not decided here; the evidence above is the input to that decision. "
                "The promotion decision itself is made on the paper record, which the "
                "sample definition of the long-sample diagnostic does not affect."
            ),
            "live_deployment": "unsupported (unchanged)",
        },
        "reproduction": {
            "command": "python research/common_inception_sample_audit.py",
            "deterministic": True,
            "no_network": True,
            "read_only_data": True,
            "test": "python -m pytest -q tests/test_common_inception_sample_audit.py",
        },
        "method": {
            "measurement": (
                "one deterministic measurement of the frozen candidate on three "
                "samples; no parameter search, no re-fit, no re-selection"
            ),
            "trials": 1,
            "engine": (
                "src/backtest/engine.py:run_backtest, unchanged; the price frame "
                "is truncated in front of it for the slice variant and the engine's "
                "window semantics are untouched"
            ),
            "gate_table": (
                "src/simulation/evaluation.py:evaluate_promotion_gates + "
                "map_decision on config/promotion_gates.yaml, unchanged"
            ),
            "psr": (
                "src/evaluation/statistics.py:compute_psr, seed 20240101, target "
                "1.4178 (the recorded backtest baseline)"
            ),
            "sharpe_convention": "arithmetic_annualized_rf0 (src/evaluation/sharpe.py)",
            "cost_model": "config/settings.yaml (1 bps commission + 2 bps slippage)",
            "splits": (
                "none: a long-sample diagnostic has no train/validation/test split; "
                "the three samples are published side by side instead"
            ),
            "rolling_window": (
                "the trailing 63 sessions of each sample's own net-return series "
                "(sharpe_ratio over the last 63 sessions, drawdown over the same "
                "window).  All three samples end on the same session, so their "
                "trailing 63-session windows are the same 63 sessions and their "
                "rolling-63d values are identical by construction -- not because a "
                "shared series was evaluated"
            ),
        },
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_REPORT, "w") as fh:
        fh.write("# Common-Inception Sample Audit (Cycle 903)\n\n")
        fh.write(
            "The incumbent's published long-sample evidence is computed on the **union\n"
            "calendar** of the raw cache, because `src/backtest/engine.py:run_backtest`\n"
            "does not slice the price frame it loads, while the frozen configuration\n"
            "describes a **seven-asset universe** whose first fully populated date is\n"
            f"{common_inception_str}.  This artifact publishes the incumbent's canonical\n"
            "metrics and its **full promotion gate table** on that common-inception\n"
            "sample next to the union-sample numbers.\n\n"
            "**This is a measurement, not a decision.**  No gate, threshold, decision\n"
            "mapping, candidate configuration, universe, cost model or Sharpe\n"
            "convention was changed, the committed long-sample artifact was not\n"
            "regenerated or edited, and the incumbent's published decision (NO-GO) is\n"
            "not changed by this cycle.  The choice of the sample on which the\n"
            "long-sample diagnostic's gate table is evaluated is left to an explicitly\n"
            "recorded decision; the evidence needed for it is published below.\n\n"
        )
        fh.write("## Question\n\n")
        fh.write(f"{report['question']}\n\n")
        fh.write("## Samples\n\n```json\n")
        json.dump(report["samples"], fh, indent=2)
        fh.write("\n```\n\n")
        fh.write("## Canonical metrics per sample (arithmetic_annualized_rf0)\n\n```json\n")
        json.dump(report["sample_metrics"], fh, indent=2)
        fh.write("\n```\n\n")
        fh.write("## Where the union sample's numbers come from\n\n```json\n")
        json.dump(report["era_decomposition"], fh, indent=2)
        fh.write("\n```\n\n")
        fh.write("## Warm-up ramp of the sliced sample\n\n```json\n")
        json.dump(report["warmup_ramp"], fh, indent=2)
        fh.write("\n```\n\n")
        fh.write("## Gate tables (config/promotion_gates.yaml, unchanged)\n\n```json\n")
        json.dump(
            {name: sample["gates"] for name, sample in samples.items()},
            fh,
            indent=2,
        )
        fh.write("\n```\n\n")
        fh.write("## Decisions and rationales\n\n```json\n")
        json.dump(
            {
                name: {
                    "decision": sample["decision"],
                    "failed_gates": sample["failed_gates"],
                    "psr_zone": sample["psr_zone"],
                    "rationale": sample["rationale"],
                    "conditions_for_reevaluation": sample["conditions_for_reevaluation"],
                }
                for name, sample in samples.items()
            },
            fh,
            indent=2,
        )
        fh.write("\n```\n\n")
        fh.write("## Sample-definition sensitivity\n\n```json\n")
        json.dump(report["sample_definition_sensitivity"], fh, indent=2)
        fh.write("\n```\n\n")
        fh.write("## Union sample vs the committed artifact (exact equality)\n\n```json\n")
        json.dump(report["committed_artifact_equality_checks"], fh, indent=2)
        fh.write("\n```\n\n")
        fh.write("## Structural checks (read-only, window, cross-section)\n\n```json\n")
        json.dump(report["structural_checks"], fh, indent=2)
        fh.write("\n```\n\n")
        fh.write("## Verdict\n\n")
        fh.write(f"- {report['verdict']['measurement']}\n")
        fh.write(
            f"- incumbent published decision: {report['verdict']['incumbent_published_decision']} "
            "(unchanged by this cycle)\n"
        )
        fh.write(f"- deferred decision: {report['verdict']['deferred_decision']}\n")
        fh.write(f"- live deployment: {report['verdict']['live_deployment']}\n\n")
        fh.write("## Data used\n\n```json\n")
        json.dump(report["data"], fh, indent=2)
        fh.write("\n```\n\n")
        fh.write("## Reproduction\n\n```json\n")
        json.dump(report["reproduction"], fh, indent=2)
        fh.write("\n```\n\n")
        fh.write("## Method\n\n```json\n")
        json.dump(report["method"], fh, indent=2)
        fh.write("\n```\n\n")
        fh.write("## Falsification conditions\n\n")
        fh.write("- a gate, a threshold, the decision mapping or the Sharpe convention changed -> reject.\n")
        fh.write("- the union-sample numbers differ from the committed artifact -> reject.\n")
        fh.write("- the committed artifact is regenerated or edited by this tool -> reject.\n")
        fh.write("- a file under data/ or config/ changed during the run -> reject.\n")
        fh.write("- the common-inception sample does not have seven assets with a price -> reject.\n")
        fh.write("- two runs of the tool disagree -> reject.\n\n")

    print(f"OVERALL: {overall}")
    print(
        f"SAMPLES: union {union_start}..{union_end} ({len(union_index)} sessions), "
        f"common inception {common_inception_str}"
    )
    for name, sample in samples.items():
        metrics = sample["metrics"]
        print(
            f"sample [{name}]: sessions={metrics['sessions']} "
            f"sharpe={metrics['paper_sharpe']:.10f} max_dd={metrics['paper_max_dd']:.10f} "
            f"rolling63={metrics['rolling_sharpe_63d']:.10f} "
            f"rolling63_dd={metrics['rolling_63d_max_dd']:.10f} "
            f"psr={metrics['psr_normal']:.6e} failed={sample['failed_gates']} "
            f"decision={sample['decision']}"
        )
        cross = sample["cross_section"]
        print(
            f"cross-section [{name}]: price width min/median/max "
            f"{cross['price_width_min']}/{cross['price_width_median']}/{cross['price_width_max']}, "
            f"momentum breadth min/median/max "
            f"{cross['momentum_breadth_min']}/{cross['momentum_breadth_median']}/{cross['momentum_breadth_max']}, "
            f"sessions with <5 selectable assets {cross['sessions_with_fewer_than_five_selectable_assets']}"
        )
    print(
        f"warm-up ramp: flat sessions {warmup['flat_sessions_before_the_first_signal']}, "
        f"first position {warmup['first_session_with_a_position']}, "
        f"differing sessions {warmup['sessions_differing_from_the_warmup_variant']}"
    )
    for check in checks:
        print(f"check [{check['name']}]: {'PASS' if check['pass'] else 'FAIL'}")
    print(
        f"sensitivity: gates that disagree {sensitivity['gates_that_disagree']}, "
        f"decision agrees {sensitivity['decision_agrees']}"
    )
    print(f"report: {OUT_REPORT.relative_to(REPO_ROOT)}")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
