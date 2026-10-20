#!/usr/bin/env python3
"""SMA-175 candidate validation audit for ``tsmomentum_spytrend_001`` (Cycle 914).

Cycle 913 found that the incumbent's published walk-forward PASS is not
phase-stable: the published 48-fold mean OOS Sharpe (0.9473) is the average of
two interleaved 24-fold sub-designs, and phase B alone fails gate-1
(0.5096 < 0.9).  The smallest reversible fix identified there was to change
the SPY trend-filter SMA window from 200 to 175 days, which makes both phases
pass gate-1.

This tool validates that mutation under the **full published protocol** --
48-fold walk-forward (gate-1 mean OOS Sharpe, gate-2 positive fold rate,
gate-3 pooled OOS trades) plus the published SMA-plateau check -- and compares
it with the SMA-200 incumbent.  Gates, thresholds and the cost model are
consumed as published and are never changed.

It is a **read-only validation**:

* the close panel is read from the committed parquet cache in ``data/raw/``
  (the fetcher is never called) and is capped at the candidate definition's
  ``END_DATE`` so that the published data range is reproduced exactly;
* nothing under ``data/`` or ``config/`` is written;
* ``research/run_cycle6.py`` (the committed candidate definition that produced
  the published record) is read, never modified;
* no promotion is performed -- this tool only measures and reports.

Reproduction anchor
-------------------
Before the mutation is measured, the harness is anchored on the incumbent:

* the published 48-fold design is re-derived from the committed cache and
  compared with the published record (aggregate statistics and every fold);
* the published SMA-plateau table (six pre-specified windows on the
  2018-01-01..END_DATE test period) is re-derived and compared cell by cell;
* the locally built candidate path is compared bit-for-bit with the committed
  path builders.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.tsmomentum_walkforward_embargo_audit import (  # noqa: E402
    CANDIDATE_ID,
    END_DATE,
    EXPERIMENTS_DIR,
    GATE_POOLED_TRADES_MIN,
    GATE_POSITIVE_FOLD_RATE_MIN,
    GATE_WF_MEAN_MIN,
    RAW_DIR,
    REPORTS_DIR,
    SYMBOLS,
    AuditError,
    _apply_overlay,
    _table_rows,
    build_anchor,
    build_candidate_path,
    decision_from_gates,
    evaluate_design,
    fail,
    fingerprint,
    gate_table,
    load_close_from_cache,
    published_splits,
    resolve_published_record,
    tracked_artifact_hashes,
)
from research.run_cycle6 import (  # noqa: E402  (committed candidate definition)
    COMMISSION_BPS,
    DD_THRESHOLD,
    LOOKBACK,
    SKIP,
    SLIPPAGE_BPS,
    SMA_WINDOWS,
    SPY_SMA_WINDOW,
    START_DATE,
    TOP_FRACTION,
    VAL_END,
    VOL_TARGET,
    VOL_TARGET_LOOKBACK,
    WF_EMBARGO_DAYS,
    WF_PURGE_DAYS,
    WF_STEP_MONTHS,
    WF_TEST_MONTHS,
    WF_TRAIN_YEARS,
)
from research.tsmomentum_phase_stability_fix_audit import (  # noqa: E402
    build_candidate_path_with_spy_sma,
)
from src.backtest.engine import get_cost_params, get_risk_free_rate  # noqa: E402
from src.features.momentum import build_weights  # noqa: E402

CYCLE = "914"

# The candidate mutation under validation: SPY trend-filter SMA window.
BASELINE_SMA_WINDOW = int(SPY_SMA_WINDOW)  # 200 (the published incumbent)
CANDIDATE_SMA_WINDOW = 175

# Published SMA-plateau rule (research/run_cycle6.py, "Plateau Verdict"):
# at least 2 of the 6 pre-specified windows must reach Sharpe >= 0.9, and the
# window that is the candidate's own baseline must be one of them.
PLATEAU_MIN_WINDOWS = 2
PLATEAU_SHARPE_MIN = 0.9

# Informational perturbation around the candidate window (not a gate).
PERTURBATION_WINDOWS = [165, 170, 175, 180, 185]

# Informational cost sensitivity (not a gate): round-trip cost levels.
COST_SENSITIVITY_BPS = [0.0, 3.0, 6.0, 10.0]

THIN_TRADE_MAX = 10  # folds at or below this trade count are "thin-trade" folds

OUT_REPORT = REPORTS_DIR / "tsmomentum_sma175_validation_001.md"
OUT_EXP = EXPERIMENTS_DIR / "tsmomentum_sma175_validation_001.md"


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _fmt(value: float, digits: int = 6) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "N/A"
    return f"{float(value):.{digits}f}"


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _design_summary(design: dict[str, Any]) -> dict[str, Any]:
    s = design.get("summary", {})
    return {
        "n_folds": int(s.get("n_folds", 0)),
        "mean_test_sharpe": float(s.get("mean_test_sharpe", float("nan"))),
        "std_test_sharpe": float(s.get("std_test_sharpe", float("nan"))),
        "median_test_sharpe": float(s.get("median_test_sharpe", float("nan"))),
        "min_test_sharpe": float(s.get("min_test_sharpe", float("nan"))),
        "max_test_sharpe": float(s.get("max_test_sharpe", float("nan"))),
        "pct_positive_sharpe": float(s.get("pct_positive_sharpe", float("nan"))),
        "mean_test_ann_return": float(s.get("mean_test_ann_return", float("nan"))),
        "mean_test_max_dd": float(s.get("mean_test_max_dd", float("nan"))),
        "mean_test_trades": float(s.get("mean_test_trades", float("nan"))),
        "total_test_trades": int(s.get("total_test_trades", 0)),
    }


def _build_path(
    close: pd.DataFrame,
    sma_window: int,
    commission_bps: float | None = None,
    slippage_bps: float | None = None,
) -> tuple[pd.Series, pd.DataFrame]:
    """The published candidate path with a configurable SPY SMA window.

    Mirrors the published protocol's ``_eval_candidate_period`` (candidate
    evaluated over the full history, then sliced per fold) and the committed
    overlay ``_apply_overlay``.  The cost arguments default to the committed
    published cost model; they are only overridden for the informational
    cost-sensitivity table.
    """
    weights = build_weights(close, lookback=LOOKBACK, skip=SKIP, top_fraction=TOP_FRACTION)
    common = close.index.intersection(weights.index)
    close_a = close.loc[common]
    weights_a = weights.loc[common]
    daily_ret = close_a.pct_change().fillna(0.0)

    spy = close_a["SPY"]
    spy_sma = spy.rolling(sma_window).mean()
    exposure = pd.Series(1.0, index=close_a.index)
    exposure[spy < spy_sma] = 0.0
    exposure[spy.isna() | spy_sma.isna()] = 0.0

    kwargs: dict[str, float] = {}
    if commission_bps is not None:
        kwargs["commission_bps"] = commission_bps
    if slippage_bps is not None:
        kwargs["slippage_bps"] = slippage_bps

    combined_weights, net_ret, _ = _apply_overlay(
        daily_ret, weights_a, exposure_factor=exposure, **kwargs
    )
    if len(net_ret) == 0:
        fail("candidate path is empty")
    return net_ret, combined_weights


def _build_plateau_path(
    close: pd.DataFrame, sma_window: int
) -> tuple[pd.Series, pd.DataFrame, dict[str, Any]]:
    """The published plateau path: overlay applied on the post-VAL_END slice.

    This is the published ``_eval_candidate`` semantics (the overlay is applied
    to the test-period slice, not to the full history), re-implemented against
    the committed cache so the fetcher is never called.
    """
    weights = build_weights(close, lookback=LOOKBACK, skip=SKIP, top_fraction=TOP_FRACTION)
    common = close.index.intersection(weights.index)
    close_a = close.loc[common]
    weights_a = weights.loc[common]
    daily_ret = close_a.pct_change().fillna(0.0)

    test_mask = weights_a.index > pd.Timestamp(VAL_END, tz="UTC")
    test_asset_ret = daily_ret[test_mask]
    test_weights = weights_a[test_mask]

    spy = close_a["SPY"]
    spy_sma = spy.rolling(sma_window).mean()
    exposure = pd.Series(1.0, index=close_a.index)
    exposure[spy < spy_sma] = 0.0
    exposure[spy.isna() | spy_sma.isna()] = 0.0
    test_exposure = exposure[test_mask]

    combined_weights, net_ret, metrics = _apply_overlay(
        test_asset_ret, test_weights, exposure_factor=test_exposure
    )
    if len(net_ret) == 0:
        fail("plateau path is empty")
    return net_ret, combined_weights, metrics


def _parse_published_plateau(text: str) -> dict[int, dict[str, Any]]:
    """The published SMA-plateau table of the published record."""
    out: dict[int, dict[str, Any]] = {}
    for cells in _table_rows(text, "SMA Window"):
        if len(cells) < 7:
            continue
        try:
            window = int(cells[0])
            out[window] = {
                "sma_window": window,
                "test_sharpe": float(cells[1]),
                "test_ann_return": float(cells[2]),
                "test_max_dd": float(cells[3]),
                "test_trades": int(cells[4]),
                "test_sortino": float(cells[5]),
                "test_profit_factor": float(cells[6]),
            }
        except ValueError:
            continue
    if not out:
        fail("published record carries no SMA-plateau table")
    return out


def _influence(folds: list[dict[str, Any]], mean: float) -> dict[str, Any]:
    """Fold leave-one-out influence summary for one design."""
    sharpes = [float(r["test_sharpe"]) for r in folds]
    trades = [int(r["test_trades"]) for r in folds]
    rows: list[dict[str, Any]] = []
    for i, r in enumerate(folds):
        loo = float(np.mean(sharpes[:i] + sharpes[i + 1 :])) if len(sharpes) > 1 else float("nan")
        rows.append(
            {
                "fold": r["fold"],
                "test_sharpe": sharpes[i],
                "test_trades": trades[i],
                "loo_mean": loo,
                "shift": loo - mean,
                "is_thin": trades[i] <= THIN_TRADE_MAX,
            }
        )
    ordered = sorted(sharpes)
    trimmed = float(np.mean(ordered[1:-1])) if len(ordered) > 2 else float("nan")
    thin = [r for r in rows if r["is_thin"]]
    return {
        "mean": mean,
        "median": float(np.median(sharpes)),
        "trimmed_mean_drop_min_max": trimmed,
        "most_influential_fold": max(rows, key=lambda r: abs(r["shift"])) if rows else None,
        "thin_trade_folds": [r["fold"] for r in thin],
        "thin_trade_fold_details": [
            {"fold": r["fold"], "test_sharpe": r["test_sharpe"], "test_trades": r["test_trades"],
             "loo_mean": r["loo_mean"]}
            for r in thin
        ],
        "both_thin_trade_folds_excluded_mean": (
            float(np.mean([s for s, t in zip(sharpes, trades) if t > THIN_TRADE_MAX]))
            if any(t <= THIN_TRADE_MAX for t in trades) else mean
        ),
        "rows": rows,
    }


def _phase_split(splits: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    phase_a = [s for i, s in enumerate(splits) if i % 2 == 0]
    phase_b = [s for i, s in enumerate(splits) if i % 2 == 1]
    return phase_a, phase_b


def _phases(
    net_ret: pd.Series,
    weights: pd.DataFrame,
    phase_a_splits: list[dict[str, Any]],
    phase_b_splits: list[dict[str, Any]],
    mean_all: float | None = None,
) -> dict[str, Any]:
    des_a = evaluate_design(net_ret, weights, phase_a_splits)
    des_b = evaluate_design(net_ret, weights, phase_b_splits)
    des_a["gates"] = gate_table(des_a["summary"])
    des_a["decision"] = decision_from_gates(des_a["gates"])
    des_b["gates"] = gate_table(des_b["summary"])
    des_b["decision"] = decision_from_gates(des_b["gates"])
    mean_a = float(des_a["summary"]["mean_test_sharpe"])
    mean_b = float(des_b["summary"]["mean_test_sharpe"])
    mean_avg = float((mean_a + mean_b) / 2.0)
    return {
        "phase_a": {
            "n_folds": int(des_a["summary"].get("n_folds", 0)),
            "mean_test_sharpe": mean_a,
            "median_test_sharpe": float(des_a["summary"].get("median_test_sharpe", float("nan"))),
            "pct_positive_sharpe": float(des_a["summary"].get("pct_positive_sharpe", float("nan"))),
            "pooled_oos_trades": int(des_a["summary"].get("total_test_trades", 0)),
            "gate_table": des_a["gates"],
            "decision": des_a["decision"],
            "independence": des_a["independence"],
        },
        "phase_b": {
            "n_folds": int(des_b["summary"].get("n_folds", 0)),
            "mean_test_sharpe": mean_b,
            "median_test_sharpe": float(des_b["summary"].get("median_test_sharpe", float("nan"))),
            "pct_positive_sharpe": float(des_b["summary"].get("pct_positive_sharpe", float("nan"))),
            "pooled_oos_trades": int(des_b["summary"].get("total_test_trades", 0)),
            "gate_table": des_b["gates"],
            "decision": des_b["decision"],
            "independence": des_b["independence"],
        },
        "gate1_phase_a": des_a["gates"][0]["status"],
        "gate1_phase_b": des_b["gates"][0]["status"],
        "gate1_outcome_changes_between_phases": bool(
            des_a["gates"][0]["status"] != des_b["gates"][0]["status"]
        ),
        "phase_mean_average": mean_avg,
        "phase_means_average_to_published_mean": (
            bool(abs(mean_avg - float(mean_all)) <= 1e-9) if mean_all is not None else None
        ),
    }


# ----------------------------------------------------------------------
# Audit
# ----------------------------------------------------------------------
def run_audit(
    experiments_dir: Path = EXPERIMENTS_DIR,
    raw_dir: Path = RAW_DIR,
) -> dict[str, Any]:
    """Run the whole validation and return the payload (no file writes)."""
    checks: list[dict[str, Any]] = []

    def record_check(name: str, ok: bool, observed: Any = "", expected: Any = "") -> None:
        checks.append(
            {"name": name, "pass": bool(ok), "observed": observed, "expected": expected}
        )

    # ------------------------------------------------------------------
    # Read-only baselines
    # ------------------------------------------------------------------
    data_before = fingerprint(REPO_ROOT / "data")
    config_before = fingerprint(REPO_ROOT / "config")
    artifacts_before = tracked_artifact_hashes()

    # ------------------------------------------------------------------
    # Data: committed cache only, capped at the protocol's END_DATE
    # ------------------------------------------------------------------
    panel = load_close_from_cache(list(SYMBOLS), raw_dir)
    raw_last = panel.index.max()
    end_ts = pd.Timestamp(END_DATE, tz="UTC")
    close = panel.loc[panel.index <= end_ts]
    if close.empty:
        fail("cached close panel is empty after the END_DATE cut")
    data_info = {
        "source": "committed parquet cache in data/raw/ (fetcher never called)",
        "symbols": list(SYMBOLS),
        "start_date": START_DATE,
        "end_date": END_DATE,
        "raw_cache_first_date": str(panel.index.min().date()),
        "raw_cache_last_date": str(raw_last.date()),
        "protocol_capped_last_date": str(close.index.max().date()),
        "sessions_raw": int(len(panel)),
        "sessions_used": int(len(close)),
        "sessions_dropped_after_end_date": int(len(panel) - len(close)),
        "end_date_cap_applied": bool(raw_last > end_ts),
        "note": (
            "the committed cache extends past the published protocol END_DATE; the panel is "
            "capped at END_DATE so the published data range (and the published plateau table) "
            "is reproduced exactly"
        ),
    }
    record_check(
        "cache_only_path_built",
        len(close) > 0 and len(close.columns) == len(SYMBOLS),
        f"{len(close)} sessions ({data_info['sessions_raw']} cached), {len(close.columns)} symbols, "
        f"last {data_info['protocol_capped_last_date']}",
        "non-empty cache-only panel capped at the published END_DATE",
    )

    # ------------------------------------------------------------------
    # Published record (resolved by content)
    # ------------------------------------------------------------------
    record_path, published = resolve_published_record(experiments_dir)
    published_text = record_path.read_text(encoding="utf-8")
    record_check(
        "published_record_resolved_by_content",
        True,
        _rel(record_path),
        "exactly one published walk-forward record carrying the published anchor",
    )

    splits = published_splits()
    phase_a_splits, phase_b_splits = _phase_split(splits)

    # ------------------------------------------------------------------
    # Anchor 1: the incumbent (SMA-200) on the published 48-fold design
    # ------------------------------------------------------------------
    net_ret_base, weights_base = build_candidate_path(close)
    base_design = evaluate_design(net_ret_base, weights_base, splits)
    base_design["gates"] = gate_table(base_design["summary"])
    base_design["decision"] = decision_from_gates(base_design["gates"])
    base_summary = _design_summary(base_design)
    anchor = build_anchor(published, base_design)
    record_check(
        "reproduces_published_walk_forward_aggregate",
        anchor["matches"],
        "; ".join(
            f"{r['metric']}={r['observed']} (published {r['published_text']})" for r in anchor["rows"]
        ),
        "published aggregate statistics",
    )
    record_check(
        "reproduces_published_walk_forward_fold_table",
        anchor["per_fold_match"],
        f"{anchor['per_fold_count']} folds compared",
        "every published fold reproduced",
    )

    # ------------------------------------------------------------------
    # Anchor 2: the published SMA-plateau table
    # ------------------------------------------------------------------
    published_plateau = _parse_published_plateau(published_text)
    plateau_rows: list[dict[str, Any]] = []
    plateau_all_match = True
    for window in SMA_WINDOWS:
        if window not in published_plateau:
            fail(f"published plateau table has no row for SMA window {window}")
        _, _, metrics = _build_plateau_path(close, window)
        observed = {
            "sma_window": window,
            "test_sharpe": float(metrics["sharpe_ratio"]),
            "test_ann_return": float(metrics["annualized_return"]),
            "test_max_dd": float(metrics["max_drawdown"]),
            "test_trades": int(metrics["trade_count"]),
            "test_sortino": float(metrics["sortino_ratio"]),
            "test_profit_factor": float(metrics["profit_factor"]),
        }
        pub = published_plateau[window]
        diffs = {
            "test_sharpe": abs(observed["test_sharpe"] - pub["test_sharpe"]),
            "test_ann_return": abs(observed["test_ann_return"] - pub["test_ann_return"]),
            "test_max_dd": abs(observed["test_max_dd"] - pub["test_max_dd"]),
            "test_sortino": abs(observed["test_sortino"] - pub["test_sortino"]),
            "test_profit_factor": abs(observed["test_profit_factor"] - pub["test_profit_factor"]),
        }
        match = (
            diffs["test_sharpe"] <= 1e-4
            and diffs["test_ann_return"] <= 1e-4
            and diffs["test_max_dd"] <= 1e-4
            and diffs["test_sortino"] <= 1e-4
            and diffs["test_profit_factor"] <= 0.005
            and observed["test_trades"] == pub["test_trades"]
        )
        plateau_all_match = plateau_all_match and match
        plateau_rows.append(
            {
                **observed,
                "published": pub,
                "abs_diffs": diffs,
                "match": bool(match),
            }
        )
    record_check(
        "reproduces_published_plateau_table",
        plateau_all_match,
        "; ".join(
            f"{r['sma_window']}: sharpe {r['test_sharpe']:.4f} vs published "
            f"{r['published']['test_sharpe']:.4f}, trades {r['test_trades']} vs "
            f"{r['published']['test_trades']}"
            for r in plateau_rows
        ),
        "every published plateau row reproduced (sharpe/return/dd/sortino/profit-factor/trades)",
    )

    # ------------------------------------------------------------------
    # Harness equivalence: the local path builder vs the committed builders
    # ------------------------------------------------------------------
    local_base_ret, local_base_w = _build_path(close, BASELINE_SMA_WINDOW)
    committed_base_ret, committed_base_w = build_candidate_path(close)
    base_ret_diff = float(np.max(np.abs(local_base_ret.to_numpy() - committed_base_ret.to_numpy())))
    base_w_diff = float(
        np.max(np.abs(local_base_w.to_numpy() - committed_base_w.to_numpy()))
    )

    local_cand_ret, local_cand_w = _build_path(close, CANDIDATE_SMA_WINDOW)
    committed_cand_ret, committed_cand_w = build_candidate_path_with_spy_sma(
        close, CANDIDATE_SMA_WINDOW
    )
    cand_ret_diff = float(np.max(np.abs(local_cand_ret.to_numpy() - committed_cand_ret.to_numpy())))
    cand_w_diff = float(
        np.max(np.abs(local_cand_w.to_numpy() - committed_cand_w.to_numpy()))
    )
    record_check(
        "harness_matches_committed_path_builders",
        base_ret_diff == 0.0 and base_w_diff == 0.0 and cand_ret_diff == 0.0 and cand_w_diff == 0.0,
        f"SMA-200 max|diff| ret={base_ret_diff} weights={base_w_diff}; "
        f"SMA-175 max|diff| ret={cand_ret_diff} weights={cand_w_diff}",
        "local path builder is bit-identical to the committed path builders",
    )

    # ------------------------------------------------------------------
    # The candidate (SMA-175) on the published 48-fold design
    # ------------------------------------------------------------------
    cand_design = evaluate_design(local_cand_ret, local_cand_w, splits)
    cand_design["gates"] = gate_table(cand_design["summary"])
    cand_design["decision"] = decision_from_gates(cand_design["gates"])
    cand_summary = _design_summary(cand_design)
    cand_gates = cand_design["gates"]
    record_check(
        "sma175_gate1_walkforward_mean_oos_sharpe",
        cand_gates[0]["status"] == "PASS",
        f"{cand_gates[0]['observed']:.6f} (margin {cand_gates[0]['margin']:+.6f})",
        f">= {GATE_WF_MEAN_MIN}",
    )
    record_check(
        "sma175_gate2_positive_fold_rate",
        cand_gates[1]["status"] == "PASS",
        f"{cand_gates[1]['observed']:.6f} (margin {cand_gates[1]['margin']:+.6f})",
        f">= {GATE_POSITIVE_FOLD_RATE_MIN}",
    )
    record_check(
        "sma175_gate3_pooled_oos_trades",
        cand_gates[2]["status"] == "PASS",
        f"{cand_gates[2]['observed']} (margin {cand_gates[2]['margin']:+.0f})",
        f"> {GATE_POOLED_TRADES_MIN}",
    )

    # ------------------------------------------------------------------
    # Phase decomposition (the reason the mutation exists)
    # ------------------------------------------------------------------
    phases_base = _phases(
        net_ret_base, weights_base, phase_a_splits, phase_b_splits, base_summary["mean_test_sharpe"]
    )
    phases_cand = _phases(
        local_cand_ret, local_cand_w, phase_a_splits, phase_b_splits, cand_summary["mean_test_sharpe"]
    )
    record_check(
        "sma175_phase_stable_gate1",
        phases_cand["gate1_phase_a"] == "PASS" and phases_cand["gate1_phase_b"] == "PASS",
        f"phase A {phases_cand['phase_a']['mean_test_sharpe']:.6f} "
        f"({phases_cand['gate1_phase_a']}, {phases_cand['phase_a']['pooled_oos_trades']} trades), "
        f"phase B {phases_cand['phase_b']['mean_test_sharpe']:.6f} "
        f"({phases_cand['gate1_phase_b']}, {phases_cand['phase_b']['pooled_oos_trades']} trades)",
        "both phases pass gate-1 (phase-stable outcome)",
    )
    record_check(
        "phase_means_average_to_published_mean",
        phases_cand["phase_means_average_to_published_mean"],
        f"({phases_cand['phase_a']['mean_test_sharpe']:.6f} + "
        f"{phases_cand['phase_b']['mean_test_sharpe']:.6f}) / 2 = "
        f"{phases_cand['phase_mean_average']:.6f}, published recomputed "
        f"{cand_summary['mean_test_sharpe']:.6f}",
        "published mean equals the average of the two phase means",
    )

    # ------------------------------------------------------------------
    # Fold comparison and influence
    # ------------------------------------------------------------------
    fold_rows: list[dict[str, Any]] = []
    for base_f, cand_f in zip(base_design["folds"], cand_design["folds"]):
        fold_rows.append(
            {
                "fold": base_f["fold"],
                "test_start": base_f["test_start"],
                "test_end": base_f["test_end"],
                "sharpe_sma200": float(base_f["test_sharpe"]),
                "sharpe_sma175": float(cand_f["test_sharpe"]),
                "trades_sma200": int(base_f["test_trades"]),
                "trades_sma175": int(cand_f["test_trades"]),
            }
        )
    influence_base = _influence(base_design["folds"], base_summary["mean_test_sharpe"])
    influence_cand = _influence(cand_design["folds"], cand_summary["mean_test_sharpe"])

    # ------------------------------------------------------------------
    # SMA-plateau gate for the candidate vs the incumbent
    # ------------------------------------------------------------------
    n_pass = sum(1 for r in plateau_rows if r["test_sharpe"] >= PLATEAU_SHARPE_MIN)
    passing_windows = [r["sma_window"] for r in plateau_rows if r["test_sharpe"] >= PLATEAU_SHARPE_MIN]
    plateau_gate = {
        "rule": (
            f">= {PLATEAU_MIN_WINDOWS} of {len(SMA_WINDOWS)} pre-specified windows reach "
            f"Sharpe >= {PLATEAU_SHARPE_MIN}, and the candidate's own baseline window is one of them"
        ),
        "windows": list(SMA_WINDOWS),
        "n_pass": int(n_pass),
        "passing_windows": passing_windows,
        "sma200": {
            "baseline_window": BASELINE_SMA_WINDOW,
            "baseline_window_passes": BASELINE_SMA_WINDOW in passing_windows,
            "gate": "PASS" if (n_pass >= PLATEAU_MIN_WINDOWS and BASELINE_SMA_WINDOW in passing_windows) else "FAIL",
        },
        "sma175": {
            "baseline_window": CANDIDATE_SMA_WINDOW,
            "baseline_window_passes": CANDIDATE_SMA_WINDOW in passing_windows,
            "gate": "PASS" if (n_pass >= PLATEAU_MIN_WINDOWS and CANDIDATE_SMA_WINDOW in passing_windows) else "FAIL",
        },
    }
    record_check(
        "sma175_plateau_gate_passes",
        plateau_gate["sma175"]["gate"] == "PASS",
        f"{n_pass}/{len(SMA_WINDOWS)} windows >= {PLATEAU_SHARPE_MIN} "
        f"({', '.join(str(w) for w in passing_windows)}); candidate baseline window "
        f"{CANDIDATE_SMA_WINDOW} passes: {plateau_gate['sma175']['baseline_window_passes']}",
        f">= {PLATEAU_MIN_WINDOWS} of {len(SMA_WINDOWS)} windows including the candidate baseline",
    )

    # ------------------------------------------------------------------
    # Cost model: the published one, unchanged
    # ------------------------------------------------------------------
    commission_bps, slippage_bps = get_cost_params()
    cost_model = {
        "commission_bps": commission_bps * 10000.0,
        "slippage_bps": slippage_bps * 10000.0,
        "round_trip_bps": (commission_bps + slippage_bps) * 10000.0,
        "published_commission_bps": COMMISSION_BPS * 10000.0,
        "published_slippage_bps": SLIPPAGE_BPS * 10000.0,
        "rf_annual": get_risk_free_rate(),
        "source": "config/settings.yaml via src.backtest.engine.get_cost_params (unchanged)",
        "note": "all reported metrics are net of the published round-trip cost",
    }
    record_check(
        "cost_model_unchanged",
        abs(commission_bps - COMMISSION_BPS) <= 1e-15 and abs(slippage_bps - SLIPPAGE_BPS) <= 1e-15,
        f"{cost_model['commission_bps']:.1f} bps commission + {cost_model['slippage_bps']:.1f} bps "
        f"slippage = {cost_model['round_trip_bps']:.1f} bps round-trip",
        "the committed published cost model is used unchanged",
    )

    # Informational: net-of-cost sensitivity of the candidate.
    cost_sensitivity: list[dict[str, Any]] = []
    for total_bps in COST_SENSITIVITY_BPS:
        half = total_bps / 2.0 * 1e-4
        ret, w = _build_path(
            close, CANDIDATE_SMA_WINDOW, commission_bps=half, slippage_bps=half
        )
        des = evaluate_design(ret, w, splits)
        s = _design_summary(des)
        cost_sensitivity.append(
            {
                "round_trip_bps": total_bps,
                "mean_test_sharpe": s["mean_test_sharpe"],
                "pct_positive_sharpe": s["pct_positive_sharpe"],
                "total_test_trades": s["total_test_trades"],
                "gate1": gate_table(s)[0]["status"],
            }
        )

    # Informational: perturbation around the candidate window.
    perturbation: list[dict[str, Any]] = []
    for window in PERTURBATION_WINDOWS:
        ret, w = _build_path(close, window)
        des = evaluate_design(ret, w, splits)
        gates = gate_table(des["summary"])
        ph = _phases(ret, w, phase_a_splits, phase_b_splits)
        perturbation.append(
            {
                "sma_window": window,
                "mean_test_sharpe": float(des["summary"]["mean_test_sharpe"]),
                "pct_positive_sharpe": float(des["summary"]["pct_positive_sharpe"]),
                "total_test_trades": int(des["summary"]["total_test_trades"]),
                "gate1": gates[0]["status"],
                "phase_a_mean": ph["phase_a"]["mean_test_sharpe"],
                "phase_b_mean": ph["phase_b"]["mean_test_sharpe"],
                "phase_stable_gate1": bool(
                    ph["gate1_phase_a"] == "PASS" and ph["gate1_phase_b"] == "PASS"
                ),
            }
        )

    # ------------------------------------------------------------------
    # Read-only verification
    # ------------------------------------------------------------------
    data_after = fingerprint(REPO_ROOT / "data")
    config_after = fingerprint(REPO_ROOT / "config")
    artifacts_after = tracked_artifact_hashes()
    record_check("data_unchanged", data_before == data_after)
    record_check("config_unchanged", config_before == config_after)
    record_check("committed_artifacts_unchanged", artifacts_before == artifacts_after)

    # ------------------------------------------------------------------
    # Verdict (measurement only -- no promotion is performed)
    # ------------------------------------------------------------------
    protocol_gates_met = all(g["status"] == "PASS" for g in cand_gates)
    phase_stable = (
        phases_cand["gate1_phase_a"] == "PASS" and phases_cand["gate1_phase_b"] == "PASS"
    )
    plateau_ok = plateau_gate["sma175"]["gate"] == "PASS"
    baseline_phase_stable = (
        phases_base["gate1_phase_a"] == "PASS" and phases_base["gate1_phase_b"] == "PASS"
    )
    caveat = (
        "The SMA window was selected on the same 48 folds that are used to evaluate it "
        "(Cycle 913 scanned 175/170/180/150/190 on the published design and kept the first "
        "phase-stable window). The SMA-175 numbers are therefore in-sample with respect to the "
        "parameter choice: they are not independent evidence, and the selection itself (the number "
        "of windows tried) must be charged against the multiple-testing budget before promotion."
    )
    if protocol_gates_met and phase_stable and plateau_ok:
        label = "Credible candidate for further validation (not promoted)"
        detail = (
            f"SMA-175 passes the published protocol on the published 48-fold design "
            f"(gate-1 {cand_gates[0]['observed']:.6f} >= {GATE_WF_MEAN_MIN}, gate-2 "
            f"{cand_gates[1]['observed']:.4f} >= {GATE_POSITIVE_FOLD_RATE_MIN}, gate-3 "
            f"{cand_gates[2]['observed']} > {GATE_POOLED_TRADES_MIN}), is phase-stable "
            f"(phase A {phases_cand['phase_a']['mean_test_sharpe']:.6f} / phase B "
            f"{phases_cand['phase_b']['mean_test_sharpe']:.6f}, both PASS) and passes the published "
            f"SMA-plateau rule ({n_pass}/{len(SMA_WINDOWS)} windows, candidate baseline included). "
            f"The incumbent SMA-200 is not phase-stable (phase B "
            f"{phases_base['phase_b']['mean_test_sharpe']:.6f} FAIL). Promotion is not performed by "
            f"this tool: the parameter choice is in-sample, so a selection-aware holdout is required "
            f"first. {caveat}"
        )
    else:
        label = "Rejected/Failed"
        detail = (
            f"SMA-175 does not satisfy the published protocol: gates met = {protocol_gates_met}, "
            f"phase-stable = {phase_stable}, plateau gate = {plateau_ok}. No promotion is performed."
        )
    verdict = {
        "label": label,
        "detail": detail,
        "protocol_gates_met": bool(protocol_gates_met),
        "phase_stable": bool(phase_stable),
        "plateau_ok": bool(plateau_ok),
        "baseline_phase_stable": bool(baseline_phase_stable),
        "promotion_performed": False,
        "selection_caveat": caveat,
    }

    payload: dict[str, Any] = {
        "cycle": CYCLE,
        "candidate": CANDIDATE_ID,
        "mutation": {
            "name": "spy_sma_175",
            "parameter": "SPY_SMA_WINDOW",
            "baseline_value": BASELINE_SMA_WINDOW,
            "candidate_value": CANDIDATE_SMA_WINDOW,
            "description": (
                f"change the SPY trend-filter SMA window from {BASELINE_SMA_WINDOW} to "
                f"{CANDIDATE_SMA_WINDOW} days (all other candidate parameters unchanged)"
            ),
        },
        "overall": "PASS" if all(c["pass"] for c in checks) else "FAIL",
        "checks": checks,
        "data": data_info,
        "published_record_path": _rel(record_path),
        "published_anchor": {
            "value": published["aggregate"].get("mean_test_sharpe", {}).get("value"),
            "matches": anchor["matches"],
            "per_fold_match": anchor["per_fold_match"],
            "per_fold_count": anchor["per_fold_count"],
            "rows": anchor["rows"],
        },
        "baseline_design_sma200": {
            "summary": base_summary,
            "gates": base_design["gates"],
            "decision": base_design["decision"],
            "independence": base_design["independence"],
        },
        "candidate_design_sma175": {
            "summary": cand_summary,
            "gates": cand_gates,
            "decision": cand_design["decision"],
            "independence": cand_design["independence"],
        },
        "phases": {
            "sma200": phases_base,
            "sma175": phases_cand,
            "phase_a_fold_numbers": [
                f["fold"] for f in base_design["folds"] if f["fold"] % 2 == 1
            ],
            "phase_b_fold_numbers": [
                f["fold"] for f in base_design["folds"] if f["fold"] % 2 == 0
            ],
        },
        "fold_comparison": fold_rows,
        "influence": {"sma200": influence_base, "sma175": influence_cand},
        "plateau": {
            "published_period": f"{VAL_END} -> {END_DATE} (post-VAL_END test period)",
            "rows": plateau_rows,
            "gate": plateau_gate,
        },
        "cost_model": cost_model,
        "cost_sensitivity": cost_sensitivity,
        "perturbation": perturbation,
        "verdict": verdict,
        "read_only": {
            "data_unchanged": data_before == data_after,
            "config_unchanged": config_before == config_after,
            "committed_artifacts_unchanged": artifacts_before == artifacts_after,
        },
        "point_in_time": (
            "signals use only data available at formation (weights shifted one day), the SPY SMA is "
            "computed point-in-time, the overlay/cost model are applied on the same continuously "
            "computed path for every fold and phase, and the panel is capped at the published END_DATE"
        ),
    }
    return payload


# ----------------------------------------------------------------------
# Report / experiment rendering
# ----------------------------------------------------------------------
def _gate_lines(gates: list[dict[str, Any]]) -> list[str]:
    if not gates:
        return ["- Gate table not formed (insufficient folds)."]
    return [
        "- {gate}: threshold {threshold}, observed {observed}, margin {margin}, status {status}".format(
            gate=g["gate"],
            threshold=g["threshold"],
            observed=_fmt(g["observed"], 6) if isinstance(g["observed"], float) else g["observed"],
            margin=_fmt(g["margin"], 6),
            status=g["status"],
        )
        for g in gates
    ]


def render_report(payload: dict[str, Any]) -> str:
    base = payload["baseline_design_sma200"]
    cand = payload["candidate_design_sma175"]
    phases = payload["phases"]
    plateau = payload["plateau"]
    infl = payload["influence"]
    data = payload["data"]
    verdict = payload["verdict"]
    lines: list[str] = []

    lines.append(
        f"# TSMomentum SPY-Trend SMA-175 Candidate Validation (tsmomentum_sma175_validation_001, Cycle {payload['cycle']})"
    )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Candidate: `{payload['candidate']}` (the incumbent)")
    lines.append(f"- Mutation under validation: {payload['mutation']['description']}")
    lines.append(
        f"- Published walk-forward record (resolved by content): `{payload['published_record_path']}`"
    )
    lines.append(
        f"- Published (SMA-200) 48-fold WF mean OOS Sharpe: {base['summary']['mean_test_sharpe']:.6f} "
        f"(gate-1 {base['gates'][0]['status']}, margin {base['gates'][0]['margin']:+.6f})"
    )
    lines.append(
        f"- Candidate (SMA-175) 48-fold WF mean OOS Sharpe: {cand['summary']['mean_test_sharpe']:.6f} "
        f"(gate-1 {cand['gates'][0]['status']}, margin {cand['gates'][0]['margin']:+.6f})"
    )
    lines.append(
        f"- Phase stability -- SMA-200: phase A {phases['sma200']['phase_a']['mean_test_sharpe']:.6f} "
        f"({phases['sma200']['gate1_phase_a']}), phase B {phases['sma200']['phase_b']['mean_test_sharpe']:.6f} "
        f"({phases['sma200']['gate1_phase_b']}); "
        f"SMA-175: phase A {phases['sma175']['phase_a']['mean_test_sharpe']:.6f} "
        f"({phases['sma175']['gate1_phase_a']}), phase B {phases['sma175']['phase_b']['mean_test_sharpe']:.6f} "
        f"({phases['sma175']['gate1_phase_b']})"
    )
    lines.append(
        f"- SMA-plateau rule: {plateau['gate']['n_pass']}/{len(plateau['gate']['windows'])} windows "
        f"reach Sharpe >= {PLATEAU_SHARPE_MIN}; gate for SMA-175: "
        f"**{plateau['gate']['sma175']['gate']}**, for SMA-200: "
        f"**{plateau['gate']['sma200']['gate']}**"
    )
    lines.append(
        f"- Verdict: **{verdict['label']}** (promotion performed: "
        f"{'yes' if verdict['promotion_performed'] else 'no'})"
    )
    lines.append(
        "- Read-only: `data/` and `config/` byte-identical before and after the run "
        f"(**{'yes' if payload['read_only']['data_unchanged'] and payload['read_only']['config_unchanged'] else 'NO'}**); "
        "no committed artifact modified "
        f"(**{'yes' if payload['read_only']['committed_artifacts_unchanged'] else 'NO'}**)."
    )
    lines.append(f"- Data source: {data['source']}.")
    lines.append("")

    lines.append("## 1. Data, protocol and the END_DATE cap")
    lines.append("")
    lines.append("| Item | Value |")
    lines.append("|---|---|")
    lines.append(f"| Source | {data['source']} |")
    lines.append(f"| Universe | {', '.join(data['symbols'])} |")
    lines.append(f"| Protocol date range | {data['start_date']} to {data['end_date']} |")
    lines.append(f"| Cached panel | {data['raw_cache_first_date']} to {data['raw_cache_last_date']} ({data['sessions_raw']} sessions) |")
    lines.append(f"| Panel used | {data['protocol_capped_last_date']} ({data['sessions_used']} sessions) |")
    lines.append(f"| Sessions dropped after END_DATE | {data['sessions_dropped_after_end_date']} |")
    lines.append(
        f"| Signal | TSMOM lookback {LOOKBACK}, skip {SKIP}, top_fraction {TOP_FRACTION} |"
    )
    lines.append(
        f"| Risk overlay | vol-target {VOL_TARGET} (lookback {VOL_TARGET_LOOKBACK}) + drawdown control {DD_THRESHOLD} |"
    )
    lines.append(
        f"| Regime filter | SPY {BASELINE_SMA_WINDOW}-day SMA (incumbent) vs {CANDIDATE_SMA_WINDOW}-day SMA (candidate) |"
    )
    lines.append(
        f"| Walk-forward | train {WF_TRAIN_YEARS}y / test {WF_TEST_MONTHS}m / step {WF_STEP_MONTHS}m, "
        f"purge {WF_PURGE_DAYS}d, embargo {WF_EMBARGO_DAYS}d |"
    )
    lines.append(
        f"| Cost model | {payload['cost_model']['commission_bps']:.1f} bps commission + "
        f"{payload['cost_model']['slippage_bps']:.1f} bps slippage = "
        f"{payload['cost_model']['round_trip_bps']:.1f} bps round-trip (unchanged); "
        f"risk-free {payload['cost_model']['rf_annual']} annual |"
    )
    lines.append(
        f"| Gates (pre-registered) | WF mean OOS Sharpe >= {GATE_WF_MEAN_MIN}, positive fold rate >= "
        f"{GATE_POSITIVE_FOLD_RATE_MIN}, pooled OOS trades > {GATE_POOLED_TRADES_MIN}, SMA plateau "
        f">= {PLATEAU_MIN_WINDOWS}/{len(SMA_WINDOWS)} windows |"
    )
    lines.append("")
    lines.append(f"- {data['note']}.")
    lines.append(f"- Point-in-time treatment: {payload['point_in_time']}.")
    lines.append(
        "- The committed cache now carries sessions past the published protocol's END_DATE, which "
        "shifts the (unbounded) plateau test period; capping the panel at END_DATE reproduces the "
        "published plateau table exactly, and leaves the walk-forward design unchanged "
        "(its fold windows are already bounded by END_DATE)."
    )
    lines.append("")

    lines.append("## 2. Anchor A -- the published 48-fold design (SMA-200, incumbent)")
    lines.append("")
    lines.append(
        "| Metric | Recomputed | Published | Match |"
    )
    lines.append("|---|---|---|---|")
    for row in payload["published_anchor"]["rows"]:
        lines.append(
            f"| {row['metric']} | {row['observed']} | {row['published_text']} | "
            f"{'YES' if row['match'] else 'NO'} |"
        )
    lines.append("")
    lines.append(
        f"- Per-fold reproduction: {payload['published_anchor']['per_fold_count']} folds compared, "
        f"all match: **{'YES' if payload['published_anchor']['per_fold_match'] else 'NO'}**."
    )
    lines.append("")

    lines.append("## 3. Anchor B -- the published SMA-plateau table")
    lines.append("")
    lines.append(
        "| SMA Window | Test Sharpe (recomputed) | Published | Ann. Return | Published | Max DD | Published | Trades | Published | Match |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in plateau["rows"]:
        p = r["published"]
        lines.append(
            f"| {r['sma_window']} | {r['test_sharpe']:.4f} | {p['test_sharpe']:.4f} | "
            f"{r['test_ann_return']:.4f} | {p['test_ann_return']:.4f} | {r['test_max_dd']:.4f} | "
            f"{p['test_max_dd']:.4f} | {r['test_trades']} | {p['test_trades']} | "
            f"{'YES' if r['match'] else 'NO'} |"
        )
    lines.append("")
    lines.append(f"- Plateau period: {plateau['published_period']}.")
    lines.append(
        f"- Rule: {plateau['gate']['rule']}. Windows at or above Sharpe {PLATEAU_SHARPE_MIN}: "
        f"**{plateau['gate']['n_pass']}/{len(plateau['gate']['windows'])}** "
        f"({', '.join(str(w) for w in plateau['gate']['passing_windows'])})."
    )
    lines.append(
        f"- Gate for the incumbent (baseline window {plateau['gate']['sma200']['baseline_window']}): "
        f"**{plateau['gate']['sma200']['gate']}**; for the candidate (baseline window "
        f"{plateau['gate']['sma175']['baseline_window']}): **{plateau['gate']['sma175']['gate']}**."
    )
    lines.append("")

    lines.append("## 4. The candidate (SMA-175) on the published 48-fold walk-forward")
    lines.append("")
    lines.append(
        "| Design | Folds | WF mean OOS Sharpe | Median | Positive fold rate | Pooled OOS trades | Gate 1 | Gate 2 | Gate 3 | Decision |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for label, d in (("SMA-200 (incumbent)", base), ("SMA-175 (candidate)", cand)):
        s = d["summary"]
        g = d["gates"]
        lines.append(
            f"| {label} | {s['n_folds']} | {s['mean_test_sharpe']:.6f} | "
            f"{s['median_test_sharpe']:.4f} | {s['pct_positive_sharpe']:.4f} | "
            f"{s['total_test_trades']} | {g[0]['status']} ({g[0]['margin']:+.4f}) | "
            f"{g[1]['status']} ({g[1]['margin']:+.4f}) | {g[2]['status']} ({g[2]['margin']:+.0f}) | "
            f"{d['decision']['label']} |"
        )
    lines.append("")
    lines.append("### 4.1 Candidate gate table (SMA-175)")
    lines.append("")
    lines.extend(_gate_lines(cand["gates"]))
    lines.append("")
    lines.append("### 4.2 Per-fold comparison")
    lines.append("")
    lines.append(
        "| Fold | Test Start | Test End | SMA-200 Test Sharpe | SMA-175 Test Sharpe | SMA-200 Trades | SMA-175 Trades |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for row in payload["fold_comparison"]:
        lines.append(
            f"| {row['fold']} | {row['test_start']} | {row['test_end']} | "
            f"{row['sharpe_sma200']:.4f} | {row['sharpe_sma175']:.4f} | "
            f"{row['trades_sma200']} | {row['trades_sma175']} |"
        )
    lines.append("")
    lines.append("### 4.3 Fold influence (leave-one-out)")
    lines.append("")
    for key, label in (("sma200", "SMA-200 (incumbent)"), ("sma175", "SMA-175 (candidate)")):
        inf = infl[key]
        mi = inf["most_influential_fold"]
        lines.append(f"- **{label}**: mean {inf['mean']:.6f}, median {inf['median']:.6f}, "
                     f"trimmed mean (min/max removed) {inf['trimmed_mean_drop_min_max']:.6f}; "
                     f"most influential fold {mi['fold']} (Sharpe {mi['test_sharpe']:.4f}, "
                     f"{mi['test_trades']} trades, LOO mean {mi['loo_mean']:.6f}, "
                     f"shift {mi['shift']:+.6f}); thin-trade folds (<= {THIN_TRADE_MAX} trades): "
                     f"{inf['thin_trade_folds'] or 'none'}.")
    lines.append("")

    lines.append("## 5. Phase decomposition (odd folds vs even folds)")
    lines.append("")
    lines.append(
        "| Phase | Design | Folds | WF mean OOS Sharpe | Median | Positive fold rate | Pooled OOS trades | Gate 1 | Decision |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for label, key in (("SMA-200 (incumbent)", "sma200"), ("SMA-175 (candidate)", "sma175")):
        ph = phases[key]
        for pname, pkey in (("Phase A (odd folds)", "phase_a"), ("Phase B (even folds)", "phase_b")):
            p = ph[pkey]
            lines.append(
                f"| {pname} | {label} | {p['n_folds']} | {p['mean_test_sharpe']:.6f} | "
                f"{p['median_test_sharpe']:.4f} | {p['pct_positive_sharpe']:.4f} | "
                f"{p['pooled_oos_trades']} | {p['gate_table'][0]['status']} "
                f"({p['gate_table'][0]['margin']:+.4f}) | {p['decision']['label']} |"
            )
    lines.append("")
    lines.append(
        f"- Phase A fold numbers: {', '.join(str(n) for n in phases['phase_a_fold_numbers'])}; "
        f"phase B fold numbers: {', '.join(str(n) for n in phases['phase_b_fold_numbers'])}."
    )
    lines.append(
        f"- Gate-1 outcome changes between phases -- SMA-200: "
        f"**{'YES' if phases['sma200']['gate1_outcome_changes_between_phases'] else 'NO'}**; "
        f"SMA-175: **{'YES' if phases['sma175']['gate1_outcome_changes_between_phases'] else 'NO'}**."
    )
    lines.append(
        f"- Phase means average to the published mean -- SMA-175: "
        f"**{'YES' if phases['sma175']['phase_means_average_to_published_mean'] else 'NO'}** "
        f"({phases['sma175']['phase_mean_average']:.6f} vs {cand['summary']['mean_test_sharpe']:.6f})."
    )
    lines.append("")

    lines.append("## 6. Cost model and net-of-cost sensitivity (informational)")
    lines.append("")
    lines.append(
        f"- The published cost model is used unchanged: "
        f"{payload['cost_model']['commission_bps']:.1f} bps commission + "
        f"{payload['cost_model']['slippage_bps']:.1f} bps slippage = "
        f"{payload['cost_model']['round_trip_bps']:.1f} bps round-trip. Every metric in this "
        f"report is net of that cost."
    )
    lines.append("")
    lines.append(
        "| Round-trip cost (bps) | WF mean OOS Sharpe | Positive fold rate | Pooled OOS trades | Gate 1 |"
    )
    lines.append("|---|---|---|---|---|")
    for row in payload["cost_sensitivity"]:
        lines.append(
            f"| {row['round_trip_bps']:.1f} | {row['mean_test_sharpe']:.6f} | "
            f"{row['pct_positive_sharpe']:.4f} | {row['total_test_trades']} | {row['gate1']} |"
        )
    lines.append("")
    lines.append(
        "- Informational only: the cost model itself is not changed and no gate depends on this table."
    )
    lines.append("")

    lines.append("## 7. Parameter perturbation around SMA-175 (informational)")
    lines.append("")
    lines.append(
        "| SMA window | WF mean OOS Sharpe | Positive fold rate | Pooled OOS trades | Gate 1 | Phase A mean | Phase B mean | Phase-stable gate-1 |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for row in payload["perturbation"]:
        lines.append(
            f"| {row['sma_window']} | {row['mean_test_sharpe']:.6f} | "
            f"{row['pct_positive_sharpe']:.4f} | {row['total_test_trades']} | {row['gate1']} | "
            f"{row['phase_a_mean']:.6f} | {row['phase_b_mean']:.6f} | "
            f"{'YES' if row['phase_stable_gate1'] else 'NO'} |"
        )
    lines.append("")
    lines.append(
        "- Informational only: this is a neighbourhood check around the candidate window, not a "
        "gate, and it is measured on the same folds that selected the window."
    )
    lines.append("")

    lines.append("## 8. Verdict and caveats")
    lines.append("")
    lines.append(f"- **{verdict['label']}**")
    lines.append(f"- {verdict['detail']}")
    lines.append(
        f"- Selection caveat: {verdict['selection_caveat']}"
    )
    lines.append(
        "- No promotion was performed: `research/run_cycle6.py` is unchanged and the committed "
        "candidate definition still uses SMA 200."
    )
    lines.append("")

    lines.append("## 9. Checks")
    lines.append("")
    for c in payload["checks"]:
        lines.append(
            f"- [{c['name']}]: {'PASS' if c['pass'] else 'FAIL'}"
            + (
                f" (observed: {c['observed']}, expected: {c['expected']})"
                if c.get("observed") or c.get("expected")
                else ""
            )
        )
    lines.append("")

    lines.append("## 10. Reproduction commands")
    lines.append("")
    lines.append("```bash")
    lines.append("python research/tsmomentum_sma175_validation_audit.py")
    lines.append("python -m pytest -q tests/test_tsmomentum_sma175_validation_audit.py")
    lines.append("python -m pytest -q")
    lines.append("git status --porcelain data/ config/")
    lines.append("git diff --stat src/ config/ research/run_cycle6.py research/experiments/ research/reports/")
    lines.append("```")
    lines.append("")

    lines.append("## 11. JSON payload")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(payload, indent=2, default=str, sort_keys=True))
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def render_experiment(payload: dict[str, Any]) -> str:
    base = payload["baseline_design_sma200"]
    cand = payload["candidate_design_sma175"]
    phases = payload["phases"]
    plateau = payload["plateau"]
    infl = payload["influence"]
    data = payload["data"]
    verdict = payload["verdict"]
    lines: list[str] = []

    lines.append(
        f"# Experiment: SMA-175 candidate validation for `{payload['candidate']}` "
        f"(tsmomentum_sma175_validation_001, Cycle {payload['cycle']})"
    )
    lines.append("")
    lines.append("## Hypothesis reference")
    lines.append("")
    lines.append("- Candidate hypothesis: `research/hypotheses/tsmomentum_004.md` (Cycle 5 promoted candidate)")
    lines.append(
        f"- Published walk-forward record: `{payload['published_record_path']}` (resolved by content)"
    )
    lines.append(
        "- Frozen candidate definition: `research/run_cycle6.py` (the script that produced the "
        "published record; read, never changed)"
    )
    lines.append(
        "- Prior evidence: `research/experiments/tsmomentum_phase_stability_fix_001.md` (Cycle 913, "
        "phase-instability diagnosis and the SMA-175 tweak), "
        "`research/experiments/tsmomentum_fold_phase_decision_001.md` (Cycle 912, downgrade to "
        "exploratory)"
    )
    lines.append(
        "- Pre-registered promotion gates: `AGENTS.md` and the published record's gate table (read, "
        "never changed)"
    )
    lines.append("")

    lines.append("## Objective")
    lines.append("")
    lines.append(
        "Validate the SMA-175 mutation (SPY trend-filter SMA window 200 -> 175) as a candidate "
        "under the full published protocol: the 48-fold walk-forward gates (gate-1 mean OOS "
        "Sharpe, gate-2 positive fold rate, gate-3 pooled OOS trades), the phase decomposition "
        "that motivated the mutation, and the published SMA-plateau check, all with the published "
        "cost model and thresholds unchanged. Measurement only: no promotion, no change to "
        "`research/run_cycle6.py`, no writes under `data/` or `config/`."
    )
    lines.append("")

    lines.append("## Data")
    lines.append("")
    lines.append(f"- Source: {data['source']}")
    lines.append(f"- Universe: {', '.join(data['symbols'])}")
    lines.append(
        f"- Date range: {data['start_date']} to {data['end_date']} (panel capped at END_DATE; "
        f"the committed cache extends to {data['raw_cache_last_date']}, "
        f"{data['sessions_dropped_after_end_date']} sessions dropped)"
    )
    lines.append(f"- Point-in-time treatment: {payload['point_in_time']}")
    lines.append(
        f"- Cost model: {payload['cost_model']['commission_bps']:.1f} bps commission + "
        f"{payload['cost_model']['slippage_bps']:.1f} bps slippage = "
        f"{payload['cost_model']['round_trip_bps']:.1f} bps round-trip; risk-free "
        f"{payload['cost_model']['rf_annual']} annual (unchanged)"
    )
    lines.append("")

    lines.append("## Configuration (consumed as-is, never inferred)")
    lines.append("")
    lines.append(f"- Signal: TSMOM lookback {LOOKBACK}, skip {SKIP}, top_fraction {TOP_FRACTION}")
    lines.append(
        f"- Risk overlay: vol-target {VOL_TARGET} (lookback {VOL_TARGET_LOOKBACK}) + drawdown "
        f"control {DD_THRESHOLD}"
    )
    lines.append(
        f"- Regime filter: SPY SMA {BASELINE_SMA_WINDOW}d (incumbent) vs {CANDIDATE_SMA_WINDOW}d "
        f"(candidate); all other parameters unchanged"
    )
    lines.append(
        f"- Walk-forward (published design): train {WF_TRAIN_YEARS}y / test {WF_TEST_MONTHS}m / step "
        f"{WF_STEP_MONTHS}m, purge {WF_PURGE_DAYS}d, embargo {WF_EMBARGO_DAYS}d"
    )
    lines.append(
        f"- Gates (pre-registered): WF mean OOS Sharpe >= {GATE_WF_MEAN_MIN}, positive fold rate >= "
        f"{GATE_POSITIVE_FOLD_RATE_MIN}, pooled OOS trades > {GATE_POOLED_TRADES_MIN}, SMA plateau "
        f">= {PLATEAU_MIN_WINDOWS} of {len(SMA_WINDOWS)} pre-specified windows "
        f"({', '.join(str(w) for w in SMA_WINDOWS)}) with Sharpe >= {PLATEAU_SHARPE_MIN} including "
        f"the candidate's own baseline window"
    )
    lines.append("")

    lines.append("## Splits")
    lines.append("")
    lines.append(
        f"- Published design: {base['summary']['n_folds']} folds, mean consecutive test-window "
        f"overlap {base['independence']['mean_consecutive_overlap_days']:.1f} days, "
        f"{base['independence']['max_disjoint_test_windows']} disjoint test windows (unchanged by "
        f"the mutation: the same splits are used for both designs)"
    )
    lines.append(
        "- Phase A = odd folds, phase B = even folds of the published 48-fold design "
        "(the interleaving of two disjoint 24-fold sub-designs)."
    )
    lines.append("")

    lines.append("## Results")
    lines.append("")
    lines.append("### Anchor")
    lines.append("")
    lines.append(
        f"- Published design recomputed (SMA-200): {base['summary']['n_folds']} folds, WF mean OOS "
        f"Sharpe {base['summary']['mean_test_sharpe']:.6f}, median "
        f"{base['summary']['median_test_sharpe']:.4f}, positive fold rate "
        f"{base['summary']['pct_positive_sharpe']:.4f}, pooled OOS trades "
        f"{base['summary']['total_test_trades']} -- published anchor reproduced: "
        f"**{'MATCH' if payload['published_anchor']['matches'] else 'MISMATCH'}** "
        f"({payload['published_anchor']['per_fold_count']} folds compared)."
    )
    lines.append(
        f"- Published SMA-plateau table reproduced from the committed cache: "
        f"**{'MATCH' if all(r['match'] for r in plateau['rows']) else 'MISMATCH'}** "
        f"({len(plateau['rows'])} windows)."
    )
    lines.append("")
    lines.append("### Gate table")
    lines.append("")
    lines.append("| Design | WF mean OOS Sharpe | Positive fold rate | Pooled OOS trades | Decision |")
    lines.append("|---|---|---|---|---|")
    for label, d in (("SMA-200 (incumbent)", base), ("SMA-175 (candidate)", cand)):
        g = d["gates"]
        lines.append(
            f"| {label} | {g[0]['status']} ({g[0]['observed']:.6f} vs {g[0]['threshold']}, margin "
            f"{g[0]['margin']:+.6f}) | {g[1]['status']} ({g[1]['observed']:.4f} vs {g[1]['threshold']}, "
            f"margin {g[1]['margin']:+.4f}) | {g[2]['status']} ({g[2]['observed']} vs "
            f"{g[2]['threshold']}, margin {g[2]['margin']:+.0f}) | {d['decision']['label']} |"
        )
    lines.append("")
    lines.append("### Phase decomposition")
    lines.append("")
    lines.append(
        "| Design | Phase A mean (gate 1) | Phase B mean (gate 1) | Gate-1 outcome changes between phases |"
    )
    lines.append("|---|---|---|---|")
    for label, key in (("SMA-200 (incumbent)", "sma200"), ("SMA-175 (candidate)", "sma175")):
        ph = phases[key]
        lines.append(
            f"| {label} | {ph['phase_a']['mean_test_sharpe']:.6f} ({ph['gate1_phase_a']}, "
            f"{ph['phase_a']['pooled_oos_trades']} trades) | {ph['phase_b']['mean_test_sharpe']:.6f} "
            f"({ph['gate1_phase_b']}, {ph['phase_b']['pooled_oos_trades']} trades) | "
            f"**{'YES' if ph['gate1_outcome_changes_between_phases'] else 'NO'}** |"
        )
    lines.append("")
    lines.append("### SMA-plateau check")
    lines.append("")
    lines.append(
        f"- Windows with Sharpe >= {PLATEAU_SHARPE_MIN}: **{plateau['gate']['n_pass']}/"
        f"{len(plateau['gate']['windows'])}** ({', '.join(str(w) for w in plateau['gate']['passing_windows'])})."
    )
    lines.append(
        f"- Gate for SMA-175 (baseline window {plateau['gate']['sma175']['baseline_window']}): "
        f"**{plateau['gate']['sma175']['gate']}**; for SMA-200 (baseline window "
        f"{plateau['gate']['sma200']['baseline_window']}): **{plateau['gate']['sma200']['gate']}**."
    )
    lines.append("")
    lines.append("### Fold influence")
    lines.append("")
    for key, label in (("sma200", "SMA-200 (incumbent)"), ("sma175", "SMA-175 (candidate)")):
        inf = infl[key]
        mi = inf["most_influential_fold"]
        lines.append(
            f"- {label}: mean {inf['mean']:.6f}, median {inf['median']:.6f}, trimmed mean "
            f"{inf['trimmed_mean_drop_min_max']:.6f}; most influential fold {mi['fold']} "
            f"(Sharpe {mi['test_sharpe']:.4f}, {mi['test_trades']} trades, LOO mean "
            f"{mi['loo_mean']:.6f}); thin-trade folds (<= {THIN_TRADE_MAX} trades): "
            f"{inf['thin_trade_folds'] or 'none'}."
        )
    lines.append("")
    lines.append("### Net-of-cost sensitivity (informational)")
    lines.append("")
    lines.append("| Round-trip cost (bps) | WF mean OOS Sharpe | Positive fold rate | Pooled OOS trades | Gate 1 |")
    lines.append("|---|---|---|---|---|")
    for row in payload["cost_sensitivity"]:
        lines.append(
            f"| {row['round_trip_bps']:.1f} | {row['mean_test_sharpe']:.6f} | "
            f"{row['pct_positive_sharpe']:.4f} | {row['total_test_trades']} | {row['gate1']} |"
        )
    lines.append("")
    lines.append("### Parameter perturbation around SMA-175 (informational)")
    lines.append("")
    lines.append("| SMA window | WF mean OOS Sharpe | Positive fold rate | Pooled OOS trades | Gate 1 | Phase A mean | Phase B mean | Phase-stable gate-1 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for row in payload["perturbation"]:
        lines.append(
            f"| {row['sma_window']} | {row['mean_test_sharpe']:.6f} | "
            f"{row['pct_positive_sharpe']:.4f} | {row['total_test_trades']} | {row['gate1']} | "
            f"{row['phase_a_mean']:.6f} | {row['phase_b_mean']:.6f} | "
            f"{'YES' if row['phase_stable_gate1'] else 'NO'} |"
        )
    lines.append("")

    lines.append("## Trial count")
    lines.append("")
    lines.append(
        "- Deterministic measurement: 1 incumbent path + 1 candidate path on the published 48-fold "
        "design, 2 phase decompositions, 6 published plateau windows, 4 informational cost levels, "
        "5 informational perturbation windows. No per-fold re-optimisation, no candidate "
        "selection inside this tool."
    )
    lines.append(
        "- Prior trial count to be charged against this result (from Cycle 913): 5 SPY SMA windows "
        "were tried on the same 48 folds (175, 170, 180, 150, 190) and the first phase-stable one "
        "was kept."
    )
    lines.append("")

    lines.append("## Decision")
    lines.append("")
    lines.append(f"- **{verdict['label']}**")
    lines.append(f"- {verdict['detail']}")
    lines.append("")

    lines.append("## Reproduction")
    lines.append("")
    lines.append("```bash")
    lines.append("python research/tsmomentum_sma175_validation_audit.py")
    lines.append("python -m pytest -q tests/test_tsmomentum_sma175_validation_audit.py")
    lines.append("python -m pytest -q")
    lines.append("git status --porcelain data/ config/")
    lines.append("git diff --stat src/ config/ research/run_cycle6.py research/experiments/ research/reports/")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


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

    cand = payload["candidate_design_sma175"]
    base = payload["baseline_design_sma200"]
    phases = payload["phases"]
    print("OVERALL: " + payload["overall"])
    print(f"report: {args.report_out}")
    print(f"experiment: {args.experiment_out}")
    print(
        f"incumbent SMA-{payload['mutation']['baseline_value']}: {base['summary']['n_folds']} folds, "
        f"WF mean OOS Sharpe {base['summary']['mean_test_sharpe']:.4f}, "
        f"phase A {phases['sma200']['phase_a']['mean_test_sharpe']:.4f} "
        f"({phases['sma200']['gate1_phase_a']}), phase B "
        f"{phases['sma200']['phase_b']['mean_test_sharpe']:.4f} "
        f"({phases['sma200']['gate1_phase_b']})"
    )
    print(
        f"candidate SMA-{payload['mutation']['candidate_value']}: {cand['summary']['n_folds']} folds, "
        f"WF mean OOS Sharpe {cand['summary']['mean_test_sharpe']:.4f}, "
        f"phase A {phases['sma175']['phase_a']['mean_test_sharpe']:.4f} "
        f"({phases['sma175']['gate1_phase_a']}), phase B "
        f"{phases['sma175']['phase_b']['mean_test_sharpe']:.4f} "
        f"({phases['sma175']['gate1_phase_b']})"
    )
    print(
        "candidate gates: "
        + ", ".join(f"{g['gate']}={g['status']}" for g in cand["gates"])
    )
    print(
        f"SMA-plateau: {payload['plateau']['gate']['n_pass']}/"
        f"{len(payload['plateau']['gate']['windows'])} windows >= {PLATEAU_SHARPE_MIN}, "
        f"gate SMA-175 {payload['plateau']['gate']['sma175']['gate']}"
    )
    print(f"verdict: {payload['verdict']['label']}")
    return 0 if payload["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
