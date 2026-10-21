#!/usr/bin/env python3
"""Like-for-like mechanism comparison on the point-in-time-complete window.

Cycle 931.

What this tool does
-------------------
Cycle 929 measured the incumbent's *point-in-time universe membership*: the
published 48-fold walk-forward mixes **7 folds measured on an incomplete
cross-section** (fewer than seven members carry a valid momentum) with **41
folds measured on the complete one**. Cycle 930 then executed the
pre-registered ``riskparity_001`` evaluation on a point-in-time-complete
window and rejected the candidate. Three numbers are now available for three
*different* measurement windows, so they cannot be compared:

| Path | Where it was measured |
|---|---|
| Incumbent ``tsmomentum_spytrend_001`` | published 48 folds (membership-heterogeneous), 0.947307 |
| Incumbent, complete subsample | the 41 complete published folds, 0.787522 |
| ``riskparity_001`` (rejected) | its own 22 folds, 0.778089 |
| 1/N equal weight | its own 22 folds, 0.773084 |

This tool puts the three mechanisms **side by side on one window, under one
walk-forward design and one cost model**:

1. the **window** is the point-in-time-complete one: the union of the 41
   published folds whose cross-section is complete (7 of 7 members carry a
   valid momentum throughout the test window), i.e. 2006-02-15 .. 2026-05-28;
2. the **design** is the published one -- 10-year rolling train, 12-month
   test, 6-month step, 21-day purge and 21-day embargo -- and every path is
   measured on **exactly the same 41 test windows**;
3. the **cost model** is the repository's committed one: 1.0 bp commission +
   2.0 bp slippage = 3.0 bp per unit of weight change, applied identically to
   all three paths.

The three paths are:

* the **incumbent** ``tsmomentum_spytrend_001`` (momentum selection + SPY
  200-session trend overlay + volatility targeting + drawdown control), the
  published path, recomputed from the committed cache;
* the **``riskparity_001`` baseline** (lagged 63-session inverse-volatility
  weights, cap 0.30) -- the pre-registered reference configuration of the
  Cycle-930 grid; no parameter is searched here;
* the **1/N equal-weight** benchmark over the same seven ETFs.

For every path the tool reports the walk-forward mean OOS Sharpe on both
repository scales (backtest and canonical), the positive-fold rate, the
pooled out-of-sample trades, the pre-registered gate outcomes, the excess
over 1/N and a moving-block bootstrap 95% CI on that excess (fold level,
seed 20240101 -- the seed of both Cycle 929 and Cycle 930 -- at both draw
counts used by those cycles).

Reproduction anchor
-------------------
The published 48-fold walk-forward is reproduced first (48 folds, mean
0.947307, positive-fold rate 91.67%, 6013 pooled out-of-sample trades) and
the Cycle-929 complete-cross-section figure (0.787522) is reproduced on the
41 complete folds. A mismatch fails the run; it is reported, never
silently adjusted.

The tool is **read-only**: the price panel is read from the committed parquet
cache (the fetcher is never called), nothing under ``data/`` or ``config/`` is
written, the SHA-256 of every file under those two trees and of every
committed artefact is compared before and after the run, and no committed
record, gate, protocol or shortlist row is modified.

Reproduction
------------
```bash
python research/mechanism_comparison_001.py
python -m pytest -q tests/test_mechanism_comparison_001.py
git status --porcelain data/ config/
```
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.data_cost_inventory_002 import (  # noqa: E402
    fingerprint,
    moving_block_bootstrap_mean,
    tracked_artifact_hashes,
)
from research.month_end_candidate_reaudit import path_returns  # noqa: E402
from research.riskparity_001_eval import (  # noqa: E402
    BASELINE as RISKPARITY_BASELINE,
    build_weights as build_riskparity_weights,
)
from research.run_cycle6 import (  # noqa: E402
    LOOKBACK,
    SKIP,
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
from src.backtest.engine import (  # noqa: E402
    compute_metrics,
    get_cost_params,
    get_risk_free_rate,
)
from src.evaluation.sharpe import sharpe_ratio  # noqa: E402
from src.features.momentum import compute_momentum  # noqa: E402

CANDIDATE_ID = "tsmomentum_spytrend_001"
CYCLE = "931"

RAW_DIR = REPO_ROOT / "data" / "raw"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
EXPERIMENTS_DIR = REPO_ROOT / "research" / "experiments"

OUT_REPORT = REPORTS_DIR / "mechanism_comparison_001.md"
OUT_EXP = EXPERIMENTS_DIR / "mechanism_comparison_001.md"

SELF_OUTPUTS = {
    str(OUT_REPORT.relative_to(REPO_ROOT)),
    str(OUT_EXP.relative_to(REPO_ROOT)),
}

UNIVERSE = list(SYMBOLS)

# Pre-registered promotion gates (AGENTS.md "Promotion gate"; the same
# thresholds every published record and config/promotion_gates.yaml uses).
GATE_WF_MEAN_MIN = 0.9
GATE_POSITIVE_FOLD_MIN = 0.5
GATE_POOLED_TRADES_MIN = 100

# The published anchor the incumbent's 48-fold walk-forward must reproduce.
PUBLISHED_WF_MEAN = 0.947307
PUBLISHED_POSITIVE_RATE = 0.9166666666666666
PUBLISHED_POOLED_TRADES = 6013

# The Cycle-929 complete-cross-section figure that must be reproduced.
CYCLE929_COMPLETE_MEAN = 0.787522
CYCLE929_TOLERANCE = 1e-6
# The published per-fold table carries four decimals, so a recomputed fold
# Sharpe may differ from the published one by up to half a unit in the last
# published place.
PUBLISHED_FOLD_TOLERANCE = 5e-5

# The Cycle-930 baseline figure, re-derived on the Cycle-930 design as a
# cross-check that the panel and the cost model are unchanged.
CYCLE930_BASELINE_MEAN = 0.778089

# Bootstrap settings. The seed is the one both Cycle 929 and Cycle 930 used;
# the draw counts are the ones those two cycles used (2000 and 1000).
BOOTSTRAP_SEED = 20240101
BOOTSTRAP_DRAWS = (2000, 1000)

# The riskparity baseline of the pre-registered Cycle-930 grid.
RISKPARITY_LOOKBACK, RISKPARITY_CAP = RISKPARITY_BASELINE


class ComparisonError(RuntimeError):
    """Raised when a required input is missing or malformed (fails closed)."""


def fail(message: str) -> None:
    raise ComparisonError(message)


# ----------------------------------------------------------------------
# Path construction
# ----------------------------------------------------------------------
def equal_weight_path(
    close: pd.DataFrame, cost: float
) -> tuple[pd.Series, pd.DataFrame]:
    """The 1/N equal-weight benchmark over the seven universe members."""
    weights = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    weights[:] = 1.0 / len(close.columns)
    net_ret, weights_a, _ = path_returns(close, weights, cost)
    return net_ret, weights_a


def riskparity_path(
    close: pd.DataFrame, lookback: int, cap: float, cost: float
) -> tuple[pd.Series, pd.DataFrame]:
    """The ``riskparity_001`` baseline: lagged inverse-volatility weights.

    The weights are formed on the **full** price panel (the trailing
    volatility window of the first rebalance inside the measured window
    reaches back before it) and are then costed over the whole panel.
    """
    weights, _ = build_riskparity_weights(close, lookback, cap)
    net_ret, weights_a, _ = path_returns(close, weights, cost)
    return net_ret, weights_a


# ----------------------------------------------------------------------
# Fold selection
# ----------------------------------------------------------------------
def breadth_by_fold(
    valid: pd.Series, splits: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """The effective cross-section of every published fold's test window."""
    out: list[dict[str, Any]] = []
    for i, sp in enumerate(splits):
        ts = pd.Timestamp(sp["test_start"], tz="UTC")
        te = pd.Timestamp(sp["test_end"], tz="UTC")
        window = valid.loc[ts:te]
        if window.empty:
            fail(f"fold {i + 1}: the test window carries no session")
        pos = int(valid.index.searchsorted(ts, side="left"))
        if pos >= len(valid):
            fail(f"fold {i + 1}: the test window starts after the end of the panel")
        out.append(
            {
                "fold": i + 1,
                "test_start": sp["test_start"],
                "test_end": sp["test_end"],
                "breadth_start": int(valid.iloc[pos]),
                "breadth_min": int(window.min()),
                "breadth_mean": float(window.mean()),
            }
        )
    return out


# ----------------------------------------------------------------------
# Statistics
# ----------------------------------------------------------------------
def aggregate(rows: list[dict[str, Any]], label: str) -> dict[str, Any]:
    """Aggregate the gate statistics over a set of folds (one path)."""
    sharpes = [float(r["test_sharpe"]) for r in rows]
    canonical = [float(r["test_sharpe_canonical"]) for r in rows]
    pooled = int(sum(int(r["test_trades"]) for r in rows))
    mean_sharpe = float(np.mean(sharpes))
    positive_rate = float(np.mean([s > 0 for s in sharpes]))
    gates = {
        "wf_mean_oos_sharpe": {
            "value": mean_sharpe,
            "threshold": GATE_WF_MEAN_MIN,
            "comparison": ">=",
            "passed": bool(mean_sharpe >= GATE_WF_MEAN_MIN),
        },
        "positive_fold_rate": {
            "value": positive_rate,
            "threshold": GATE_POSITIVE_FOLD_MIN,
            "comparison": ">=",
            "passed": bool(positive_rate >= GATE_POSITIVE_FOLD_MIN),
        },
        "pooled_oos_trades": {
            "value": pooled,
            "threshold": GATE_POOLED_TRADES_MIN,
            "comparison": ">",
            "passed": bool(pooled > GATE_POOLED_TRADES_MIN),
        },
    }
    return {
        "label": label,
        "n_folds": len(rows),
        "folds": [int(r["fold"]) for r in rows],
        "mean_test_sharpe": mean_sharpe,
        "median_test_sharpe": float(np.median(sharpes)),
        "min_test_sharpe": float(np.min(sharpes)),
        "max_test_sharpe": float(np.max(sharpes)),
        "mean_test_sharpe_canonical": float(np.mean(canonical)),
        "median_test_sharpe_canonical": float(np.median(canonical)),
        "pct_positive_sharpe": positive_rate,
        "total_test_trades": pooled,
        "gates": gates,
        "gates_passed": all(g["passed"] for g in gates.values()),
        "failed_gates": [name for name, g in gates.items() if not g["passed"]],
    }


def excess_bootstrap(
    path_sharpes: list[float], bench_sharpes: list[float], n_folds: int
) -> dict[str, Any]:
    """Paired moving-block bootstrap CI on the per-fold excess over 1/N.

    The bootstrap is run on the **paired per-fold differences** (the same
    fold for both paths), so the equity beta a long-only seven-asset book
    earns anyway cancels out and only the mechanism's own contribution is
    resampled. The block size follows the Cycle-929 rule
    (``max(2, n_folds // 8)``); the seed is the Cycle-929/Cycle-930 seed and
    the draw counts are the ones those two cycles used.
    """
    if len(path_sharpes) != len(bench_sharpes):
        fail("the paired excess needs the same folds for both paths")
    diffs = [float(a) - float(b) for a, b in zip(path_sharpes, bench_sharpes)]
    block = max(2, n_folds // 8)
    out: dict[str, Any] = {
        "excess": float(np.mean(diffs)),
        "fold_diffs": diffs,
        "block": block,
        "seed": BOOTSTRAP_SEED,
        "ci": {},
    }
    for draws in BOOTSTRAP_DRAWS:
        boot = moving_block_bootstrap_mean(diffs, block, draws, BOOTSTRAP_SEED)
        out["ci"][str(draws)] = {
            "draws": draws,
            "ci_low": float(boot["ci_low"]),
            "ci_high": float(boot["ci_high"]),
            "mean": float(boot["mean"]),
        }
    primary = out["ci"][str(BOOTSTRAP_DRAWS[0])]
    out["primary_draws"] = BOOTSTRAP_DRAWS[0]
    out["ci_low"] = primary["ci_low"]
    out["ci_high"] = primary["ci_high"]
    out["excludes_zero"] = bool(primary["ci_low"] > 0.0 or primary["ci_high"] < 0.0)
    out["positive"] = bool(primary["ci_low"] > 0.0)
    return out


def pooled_oos_returns(
    net_ret: pd.Series, fold_rows: list[dict[str, Any]]
) -> pd.Series:
    """The out-of-sample returns of the measured folds, concatenated."""
    parts = []
    for r in fold_rows:
        sel = (
            (net_ret.index >= pd.Timestamp(r["test_start"], tz="UTC"))
            & (net_ret.index <= pd.Timestamp(r["test_end"], tz="UTC"))
        )
        parts.append(net_ret[sel])
    if not parts:
        return pd.Series(dtype=float)
    return pd.concat(parts)


def correlation(a: pd.Series, b: pd.Series) -> float:
    joined = pd.concat([a, b], axis=1).dropna()
    if len(joined) < 3:
        return float("nan")
    return float(joined.iloc[:, 0].corr(joined.iloc[:, 1]))


# ----------------------------------------------------------------------
# The comparison
# ----------------------------------------------------------------------
def run_comparison() -> dict[str, Any]:
    data_before = fingerprint(REPO_ROOT / "data")
    config_before = fingerprint(REPO_ROOT / "config")
    artifacts_before = tracked_artifact_hashes()

    commission, slippage = get_cost_params()
    cost = commission + slippage
    rf = get_risk_free_rate()

    close = load_close_from_cache(UNIVERSE, RAW_DIR)
    if close.empty:
        fail("the committed cache produced an empty close panel")

    # --- the published design and the point-in-time-complete folds ----
    splits = published_splits()
    if len(splits) < 5:
        fail("the published walk-forward design produced too few folds")
    momentum = compute_momentum(close, lookback=LOOKBACK, skip=SKIP)
    valid = momentum.notna().sum(axis=1)
    breadth = breadth_by_fold(valid, splits)
    n_assets = len(UNIVERSE)
    complete_rows = [b for b in breadth if b["breadth_min"] >= n_assets]
    incomplete_rows = [b for b in breadth if b["breadth_min"] < n_assets]
    if not complete_rows:
        fail("no published fold is measured on a complete cross-section")
    complete_folds = {b["fold"] for b in complete_rows}

    # --- the three paths ----------------------------------------------
    incumbent_net, incumbent_w = build_candidate_path(close)
    riskparity_net, riskparity_w = riskparity_path(
        close, RISKPARITY_LOOKBACK, RISKPARITY_CAP, cost
    )
    bench_net, bench_w = equal_weight_path(close, cost)

    paths = {
        "incumbent": {
            "label": "Incumbent `tsmomentum_spytrend_001`",
            "net_ret": incumbent_net,
            "weights": incumbent_w,
        },
        "riskparity_001": {
            "label": "`riskparity_001` baseline (L = 63, cap = 0.30)",
            "net_ret": riskparity_net,
            "weights": riskparity_w,
        },
        "one_over_n": {
            "label": "1/N equal weight (7 ETFs)",
            "net_ret": bench_net,
            "weights": bench_w,
        },
    }

    designs: dict[str, dict[str, Any]] = {}
    for key, spec in paths.items():
        design = evaluate_design(spec["net_ret"], spec["weights"], splits)
        rows = [r for r in design["folds"] if int(r["fold"]) in complete_folds]
        if len(rows) != len(complete_rows):
            fail(
                f"{key}: the design produced {len(rows)} folds on the complete "
                f"cross-section, expected {len(complete_rows)}"
            )
        designs[key] = {
            "rows": rows,
            "all_rows": design["folds"],
            "summary": design["summary"],
        }

    # --- the published anchor (48 folds) ------------------------------
    record_path, published = resolve_published_record(EXPERIMENTS_DIR)
    pub_folds = {int(f["fold"]): f for f in published["folds"]}
    incumbent_rows_all = designs["incumbent"]["rows"]
    incumbent_summary_all = designs["incumbent"]["summary"]

    max_fold_gap = 0.0
    for row in designs["incumbent"]["all_rows"]:
        pub = pub_folds.get(int(row["fold"]))
        if pub is None:
            fail(f"the published record has no fold {row['fold']}")
        max_fold_gap = max(
            max_fold_gap, abs(float(row["test_sharpe"]) - float(pub["test_sharpe"]))
        )

    # The Cycle-929 figure is the mean of the **published** per-fold Sharpes
    # of the 41 complete folds (the published table carries four decimals).
    published_complete = [
        float(pub_folds[f]["test_sharpe"]) for f in sorted(complete_folds)
    ]
    cycle929_mean = float(np.mean(published_complete))
    recomputed_complete_mean = float(
        np.mean([float(r["test_sharpe"]) for r in incumbent_rows_all])
    )

    # --- aggregates on the one window ---------------------------------
    aggregates = {
        key: aggregate(designs[key]["rows"], paths[key]["label"])
        for key in paths
    }
    bench_agg = aggregates["one_over_n"]
    bench_sharpes = [float(r["test_sharpe"]) for r in designs["one_over_n"]["rows"]]

    pooled = {key: pooled_oos_returns(spec["net_ret"], designs[key]["rows"])
              for key, spec in paths.items()}

    window_start = min(r["test_start"] for r in designs["incumbent"]["rows"])
    window_end = max(r["test_end"] for r in designs["incumbent"]["rows"])

    # The union of the measured test windows: the one window all three paths
    # are measured on.
    union = pd.Series(False, index=close.index)
    for r in designs["incumbent"]["rows"]:
        union |= (close.index >= pd.Timestamp(r["test_start"], tz="UTC")) & (
            close.index <= pd.Timestamp(r["test_end"], tz="UTC")
        )

    window_metrics = {}
    for key, spec in paths.items():
        r = spec["net_ret"][union.values]
        ann_return = (1.0 + r).prod() ** (252 / len(r)) - 1.0
        ann_vol = float(r.std(ddof=1)) * np.sqrt(252)
        window_metrics[key] = {
            "sessions": int(len(r)),
            "sharpe_canonical": float(sharpe_ratio(r.to_numpy())),
            "sharpe_backtest_cagr_scale": float(
                (ann_return - rf) / ann_vol if ann_vol > 0 else 0.0
            ),
        }

    # --- excess over 1/N (paired, fold level) -------------------------
    excess = {}
    for key in ("incumbent", "riskparity_001"):
        sharpes = [float(r["test_sharpe"]) for r in designs[key]["rows"]]
        excess[key] = excess_bootstrap(sharpes, bench_sharpes, len(sharpes))
        canonical_path = [
            float(r["test_sharpe_canonical"]) for r in designs[key]["rows"]
        ]
        canonical_bench = [
            float(r["test_sharpe_canonical"]) for r in designs["one_over_n"]["rows"]
        ]
        excess[key]["canonical_excess"] = float(
            np.mean(canonical_path) - np.mean(canonical_bench)
        )

    # --- the Cycle-930 cross-check ------------------------------------
    cycle930 = _cycle930_cross_check(close, cost)

    # --- decision (pre-specified rule) ---------------------------------
    supported = [k for k in ("incumbent", "riskparity_001") if excess[k]["positive"]]
    if supported and any(
        aggregates[k]["mean_test_sharpe"] >= GATE_WF_MEAN_MIN for k in supported
    ):
        decision = "CREDIBLE_CANDIDATE"
        label = "Credible candidate"
    elif supported:
        decision = "EXPLORATORY_SIGNAL"
        label = "Exploratory signal"
    else:
        decision = "REJECTED"
        label = "Rejected"
    label_detail = {
        "CREDIBLE_CANDIDATE": (
            "at least one mechanism's excess over 1/N is statistically supported "
            "and its walk-forward mean OOS Sharpe clears the 0.9 gate on the "
            "point-in-time-complete window"
        ),
        "EXPLORATORY_SIGNAL": (
            "at least one mechanism's excess over 1/N is statistically supported, "
            "but no mechanism clears the 0.9 walk-forward gate on the "
            "point-in-time-complete window"
        ),
        "REJECTED": (
            "no mechanism's excess over 1/N is statistically supported on the "
            "point-in-time-complete window"
        ),
    }[decision]

    payload = {
        "cycle": CYCLE,
        "candidate_id": CANDIDATE_ID,
        "universe": UNIVERSE,
        "cost_per_unit": cost,
        "commission_bps": commission * 10000.0,
        "slippage_bps": slippage * 10000.0,
        "risk_free_annual": rf,
        "record_path": str(record_path.relative_to(REPO_ROOT)),
        "n_published_folds": len(splits),
        "n_complete_folds": len(complete_rows),
        "n_incomplete_folds": len(incomplete_rows),
        "complete_folds": sorted(complete_folds),
        "incomplete_folds": [b["fold"] for b in incomplete_rows],
        "window_start": window_start,
        "window_end": window_end,
        "breadth": breadth,
        "aggregates": aggregates,
        "window_metrics": window_metrics,
        "excess": excess,
        "cycle930_cross_check": cycle930,
        "published_anchor": {
            "n_folds": int(incumbent_summary_all["n_folds"]),
            "mean_test_sharpe": float(incumbent_summary_all["mean_test_sharpe"]),
            "pct_positive_sharpe": float(incumbent_summary_all["pct_positive_sharpe"]),
            "total_test_trades": int(incumbent_summary_all["total_test_trades"]),
            "max_fold_gap": float(max_fold_gap),
        },
        "cycle929_anchor": {
            "published_convention_mean": cycle929_mean,
            "recomputed_full_precision_mean": recomputed_complete_mean,
            "target": CYCLE929_COMPLETE_MEAN,
            "abs_gap_published_convention": abs(
                cycle929_mean - CYCLE929_COMPLETE_MEAN
            ),
            "abs_gap_recomputed": abs(
                recomputed_complete_mean - CYCLE929_COMPLETE_MEAN
            ),
        },
        "correlations": {
            key: correlation(pooled[key], pooled["one_over_n"])
            for key in ("incumbent", "riskparity_001")
        },
        "correlation_incumbent_riskparity": correlation(
            pooled["incumbent"], pooled["riskparity_001"]
        ),
        "decision": decision,
        "label": label,
        "label_detail": label_detail,
        "fold_rows": {
            key: [
                {
                    "fold": int(r["fold"]),
                    "test_start": r["test_start"],
                    "test_end": r["test_end"],
                    "test_sharpe": float(r["test_sharpe"]),
                    "test_sharpe_canonical": float(r["test_sharpe_canonical"]),
                    "test_trades": int(r["test_trades"]),
                }
                for r in designs[key]["rows"]
            ]
            for key in paths
        },
    }

    # --- read-only guarantees -----------------------------------------
    data_after = fingerprint(REPO_ROOT / "data")
    config_after = fingerprint(REPO_ROOT / "config")
    artifacts_after = tracked_artifact_hashes()
    if data_before != data_after:
        fail("data/ changed during the run")
    if config_before != config_after:
        fail("config/ changed during the run")
    changed = {
        key
        for key in set(artifacts_before) | set(artifacts_after)
        if artifacts_before.get(key) != artifacts_after.get(key)
    }
    changed -= SELF_OUTPUTS
    if changed:
        fail(f"committed artefacts changed during the run: {sorted(changed)}")

    anchor = payload["published_anchor"]
    payload["checks"] = [
        {"name": "data_unchanged", "pass": True},
        {"name": "config_unchanged", "pass": True},
        {"name": "committed_artifacts_unchanged", "pass": True},
        {
            "name": "published_anchor_reproduced",
            "pass": bool(
                anchor["n_folds"] == 48
                and abs(anchor["mean_test_sharpe"] - PUBLISHED_WF_MEAN) <= 1e-6
                and abs(anchor["pct_positive_sharpe"] - PUBLISHED_POSITIVE_RATE) <= 1e-6
                and anchor["total_test_trades"] == PUBLISHED_POOLED_TRADES
            ),
        },
        {
            "name": "incumbent_fold_sharpes_match_published_record",
            "pass": bool(anchor["max_fold_gap"] <= PUBLISHED_FOLD_TOLERANCE),
        },
        {
            "name": "incumbent_reproduces_cycle929_complete_mean",
            "pass": bool(
                payload["cycle929_anchor"]["abs_gap_published_convention"]
                <= CYCLE929_TOLERANCE
            ),
        },
        {
            "name": "all_paths_measured_on_identical_folds",
            "pass": bool(
                aggregates["incumbent"]["folds"]
                == aggregates["riskparity_001"]["folds"]
                == aggregates["one_over_n"]["folds"]
                and len(aggregates["incumbent"]["folds"]) == len(complete_rows)
            ),
        },
        {
            "name": "measured_window_is_point_in_time_complete",
            "pass": bool(
                all(b["breadth_min"] >= n_assets for b in complete_rows)
            ),
        },
        {
            "name": "cost_model_is_three_bp_per_unit",
            "pass": bool(abs(cost * 10000.0 - 3.0) <= 1e-9),
        },
        {
            "name": "cycle930_riskparity_baseline_reproduced",
            "pass": bool(
                abs(cycle930["mean_test_sharpe"] - CYCLE930_BASELINE_MEAN) <= 1e-6
            ),
        },
    ]
    payload["structural_pass"] = all(c["pass"] for c in payload["checks"])
    return payload


def _cycle930_cross_check(close: pd.DataFrame, cost: float) -> dict[str, Any]:
    """Re-derive the Cycle-930 baseline on the Cycle-930 design.

    The comparison window is *not* the Cycle-930 window, so the candidate's
    published figure is re-derived on its own design as a cross-check that
    the panel, the cost model and the candidate construction are unchanged
    by this cycle. The construction follows Cycle 930 exactly: the weights
    are formed on the full panel and sliced to the evaluation window, and the
    cost is charged on the sliced weight frame.
    """
    from research.month_end_candidate_reaudit import walkforward  # noqa: E402
    from research.riskparity_001_eval import (  # noqa: E402  (local import)
        EVAL_START,
        WF_EMBARGO_DAYS,
        WF_PURGE_DAYS,
        WF_STEP_MONTHS,
        WF_TEST_MONTHS,
        WF_TRAIN_YEARS,
    )
    from src.evaluation.walkforward import generate_walkforward_splits  # noqa: E402

    window = close.loc[close.index >= pd.Timestamp(EVAL_START, tz="UTC")]
    splits = generate_walkforward_splits(
        EVAL_START,
        str(window.index[-1].date()),
        WF_TRAIN_YEARS,
        WF_TEST_MONTHS,
        WF_STEP_MONTHS,
        WF_PURGE_DAYS,
        WF_EMBARGO_DAYS,
    )
    weights_full, _ = build_riskparity_weights(
        close, RISKPARITY_LOOKBACK, RISKPARITY_CAP
    )
    weights = weights_full.loc[window.index]
    net_ret, weights_a, _ = path_returns(window, weights, cost)
    summary, _ = walkforward(net_ret, weights_a, splits)
    return {
        "n_folds": int(summary["n_folds"]),
        "mean_test_sharpe": float(summary["mean_test_sharpe"]),
        "target": CYCLE930_BASELINE_MEAN,
    }


# ----------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------
def fmt(value: float, digits: int = 6) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "n/a"
    return f"{value:.{digits}f}"


def _gate_row(name: str, gate: dict[str, Any]) -> str:
    return (
        f"{fmt(float(gate['value']))} {gate['comparison']} "
        f"{fmt(float(gate['threshold']))} -> "
        f"{'PASS' if gate['passed'] else 'FAIL'}"
    )


def render_report(payload: dict[str, Any]) -> str:
    agg = payload["aggregates"]
    exc = payload["excess"]
    anchor = payload["published_anchor"]
    c929 = payload["cycle929_anchor"]
    lines: list[str] = []
    A = lines.append

    A("# Like-for-like mechanism comparison on the point-in-time-complete window")
    A("")
    A(f"**Cycle {payload['cycle']} — measurement of three mechanisms on one "
      "window, under one walk-forward design and one cost model.**")
    A("")
    A("## Status")
    A("")
    A(f"- **Decision label: {payload['label']}** — {payload['label_detail']}.")
    A(f"- The label applies to the **incremental-value comparison only**. The "
      "incumbent's published verdict is unchanged (a Credible Candidate by its "
      "published verdict and NO-GO for promotion) and `riskparity_001` remains "
      "**rejected**.")
    A(f"- Window: **{payload['window_start']} .. {payload['window_end']}** "
      f"({payload['n_complete_folds']} walk-forward folds, the point-in-time-"
      "complete folds of the published design).")
    A(f"- Cost model: {payload['commission_bps']:.1f} bp commission + "
      f"{payload['slippage_bps']:.1f} bp slippage = "
      f"**{payload['cost_per_unit'] * 10000.0:.1f} bp per unit of weight "
      "change**, applied identically to all three paths.")
    A(f"- Universe: {', '.join(payload['universe'])}.")
    A("")

    A("## 1. What was compared and why it was not comparable before")
    A("")
    A("Cycle 929 measured the incumbent's point-in-time universe membership: the "
      "published 48-fold walk-forward mixes **7 folds measured on an incomplete "
      "cross-section** with **41 measured on the complete one**. Cycle 930 "
      "evaluated `riskparity_001` on its own 22-fold design. The three numbers "
      "therefore came from three different windows and could not be compared:")
    A("")
    A("| Path | Where it was measured | Walk-forward mean OOS Sharpe |")
    A("|---|---|---|")
    A("| Incumbent, published record | 48 folds, membership-heterogeneous | "
      f"{fmt(anchor['mean_test_sharpe'])} |")
    A("| Incumbent, complete subsample | the 41 complete published folds | "
      f"{fmt(c929['published_convention_mean'])} |")
    A("| `riskparity_001` (rejected) | its own 22 folds | "
      f"{fmt(payload['cycle930_cross_check']['mean_test_sharpe'])} |")
    A("| 1/N equal weight | its own 22 folds | 0.773084 |")
    A("")
    A("This cycle re-measures **all three paths on the same 41 folds** with the "
      "same cost model. No candidate is proposed, no parameter is searched and "
      "no committed artefact is modified.")
    A("")

    A("## 2. The window and the design")
    A("")
    A("| Item | Value |")
    A("|---|---|")
    A(f"| Design | the published one: 10-year rolling train, 12-month test, "
      "6-month step, 21-day purge, 21-day embargo |")
    A(f"| Published folds | {payload['n_published_folds']} |")
    A(f"| Point-in-time-complete folds (measured) | "
      f"{payload['n_complete_folds']} |")
    A(f"| Membership-incomplete folds (excluded) | "
      f"{payload['n_incomplete_folds']} |")
    A(f"| Measured window | {payload['window_start']} .. {payload['window_end']} |")
    A(f"| Excluded folds | {', '.join(str(f) for f in payload['incomplete_folds'])} |")
    A("")
    A("A fold is *point-in-time complete* when all seven members carry a valid "
      "momentum (226-session lookback skipping 21) on **every** session of its "
      "test window. The 41 measured folds are folds "
      f"{payload['complete_folds'][0]}..{payload['complete_folds'][-1]} of the "
      "published design; the seven excluded folds are the ones before the last "
      "member (GLD) has a valid momentum.")
    A("")

    A("## 3. The three paths on the same folds")
    A("")
    A("| Path | WF mean OOS Sharpe (backtest) | WF mean OOS Sharpe (canonical) "
      "| Median fold | Worst fold | Positive folds | Pooled OOS trades | "
      "Window Sharpe (backtest) |")
    A("|---|---|---|---|---|---|---|---|---|")
    for key in ("incumbent", "riskparity_001", "one_over_n"):
        a = agg[key]
        w = payload["window_metrics"][key]
        A(f"| {a['label']} | {fmt(a['mean_test_sharpe'])} | "
          f"{fmt(a['mean_test_sharpe_canonical'])} | "
          f"{fmt(a['median_test_sharpe'])} | {fmt(a['min_test_sharpe'])} | "
          f"{fmt(a['pct_positive_sharpe'])} | {a['total_test_trades']} | "
          f"{fmt(w['sharpe_backtest_cagr_scale'])} |")
    A("")
    A("The *window Sharpe* is a single Sharpe over the union of the 41 test "
      "windows; the *walk-forward mean* is the mean of the per-fold Sharpes. "
      "The two are not interchangeable and are never compared with each other.")
    A("")

    A("### 3.1 The pre-registered gates on the one window")
    A("")
    A("| Path | Gate 1: WF mean OOS Sharpe >= 0.9 | Gate 2: positive folds >= 0.5 "
      "| Gate 3: pooled OOS trades > 100 | All gates |")
    A("|---|---|---|---|---|")
    for key in ("incumbent", "riskparity_001", "one_over_n"):
        g = agg[key]["gates"]
        A(f"| {agg[key]['label']} | {_gate_row('g1', g['wf_mean_oos_sharpe'])} | "
          f"{_gate_row('g2', g['positive_fold_rate'])} | "
          f"{_gate_row('g3', g['pooled_oos_trades'])} | "
          f"{'PASS' if agg[key]['gates_passed'] else 'FAIL'} |")
    A("")
    A("Gate 3 is a *strategy* gate (a live book must trade). The 1/N benchmark "
      "holds constant weights, so it books no trade inside the measured folds "
      "and fails gate 3 by construction; that is a property of the benchmark, "
      "not a result.")
    A("")

    A("## 4. Incremental value over 1/N")
    A("")
    A("The excess is the **paired per-fold difference** of the walk-forward "
      "Sharpe against 1/N on the same fold, so the equity beta a long-only "
      "seven-asset book earns anyway cancels. The CI is a moving-block "
      "bootstrap over the 41 fold-level differences (block "
      f"{exc['incumbent']['block']}, seed {exc['incumbent']['seed']}, draw "
      f"counts {', '.join(str(d) for d in BOOTSTRAP_DRAWS)} — the seed and the "
      "draw counts of Cycle 929 and Cycle 930).")
    A("")
    A("| Path | Excess over 1/N (same folds) | 95% CI (2000 draws) | "
      "95% CI (1000 draws) | Canonical-scale excess | Correlation with 1/N |")
    A("|---|---|---|---|---|---|")
    for key in ("incumbent", "riskparity_001"):
        e = exc[key]
        A(f"| {agg[key]['label']} | {fmt(e['excess'])} | "
          f"[{fmt(e['ci']['2000']['ci_low'])}, {fmt(e['ci']['2000']['ci_high'])}] | "
          f"[{fmt(e['ci']['1000']['ci_low'])}, {fmt(e['ci']['1000']['ci_high'])}] | "
          f"{fmt(e['canonical_excess'])} | "
          f"{fmt(payload['correlations'][key])} |")
    A("")
    A(f"Correlation between the two mechanisms' pooled out-of-sample returns: "
      f"{fmt(payload['correlation_incumbent_riskparity'])}.")
    A("")

    A("## 5. The per-fold table")
    A("")
    A("| Fold | Test window | Incumbent Sharpe | `riskparity_001` Sharpe | "
      "1/N Sharpe | Incumbent excess |")
    A("|---|---|---|---|---|---|")
    for i, r in enumerate(payload["fold_rows"]["incumbent"]):
        rp = payload["fold_rows"]["riskparity_001"][i]
        bn = payload["fold_rows"]["one_over_n"][i]
        A(f"| {r['fold']} | {r['test_start']} .. {r['test_end']} | "
          f"{fmt(r['test_sharpe'])} | {fmt(rp['test_sharpe'])} | "
          f"{fmt(bn['test_sharpe'])} | "
          f"{fmt(r['test_sharpe'] - bn['test_sharpe'])} |")
    A("")

    A("## 6. Which published statistic survives the homogeneous window")
    A("")
    A("| Published statistic | Where it comes from | On the homogeneous window |")
    A("|---|---|---|")
    A(f"| 0.947307 (incumbent walk-forward headline) | the published 48-fold "
      f"record, membership-heterogeneous | **does not survive**: the same path "
      f"on the 41 complete folds is {fmt(c929['published_convention_mean'])} "
      f"(published convention) / {fmt(c929['recomputed_full_precision_mean'])} "
      "(recomputed at full precision), below the 0.9 gate |")
    A("| 0.4716 (1/N reference) | the Cycle-7 benchmark record: a **single** "
      "1/N Sharpe over the incumbent's 2018-01-01..2026-10-09 test window at "
      "0 bp cost | **not a walk-forward statistic**, so it cannot survive or "
      "fail a walk-forward comparison; the like-for-like 1/N reference for the "
      "headline is the 1/N walk-forward mean on the same folds, "
      f"{fmt(agg['one_over_n']['mean_test_sharpe'])}, and the 1/N window Sharpe "
      f"on the homogeneous window is "
      f"{fmt(payload['window_metrics']['one_over_n']['sharpe_backtest_cagr_scale'])} |")
    A("")
    A("**Implication for the incumbent's published verdict: none.** The verdict "
      "stays a Credible Candidate by its published verdict and NO-GO for "
      "promotion (it failed the `rolling_63d_sharpe` and `psr` gates in the "
      "committed record). This cycle does not change, and does not re-open, "
      "that verdict: it measures the *incremental value over equal weight* of "
      "two mechanisms on one homogeneous window, and it states the result. "
      "The published headline (0.947307) is a membership-heterogeneous "
      "statistic and the published 1/N reference (0.4716) is a different "
      "statistic on a different window; the pair was never like-for-like and "
      "is not used as one here.")
    A("")

    A("## 7. The reproduction anchors")
    A("")
    A("| Anchor | Required | Observed | Outcome |")
    A("|---|---|---|---|")
    A(f"| Published 48-fold walk-forward | 48 folds, mean "
      f"{PUBLISHED_WF_MEAN:.6f}, positive {PUBLISHED_POSITIVE_RATE:.6f}, "
      f"{PUBLISHED_POOLED_TRADES} pooled trades | {anchor['n_folds']} folds, "
      f"mean {fmt(anchor['mean_test_sharpe'])}, positive "
      f"{fmt(anchor['pct_positive_sharpe'])}, {anchor['total_test_trades']} "
      f"pooled trades | "
      f"{'PASS' if any(c['name'] == 'published_anchor_reproduced' and c['pass'] for c in payload['checks']) else 'FAIL'} |")
    A(f"| Per-fold Sharpes vs the published table | <= {PUBLISHED_FOLD_TOLERANCE:g} "
      f"(the published table carries four decimals) | max |Δ| = "
      f"{anchor['max_fold_gap']:.3e} | "
      f"{'PASS' if any(c['name'] == 'incumbent_fold_sharpes_match_published_record' and c['pass'] for c in payload['checks']) else 'FAIL'} |")
    A(f"| Cycle-929 complete-cross-section figure | {CYCLE929_COMPLETE_MEAN:.6f} "
      f"± {CYCLE929_TOLERANCE:g} | {fmt(c929['published_convention_mean'])} "
      f"(|Δ| = {c929['abs_gap_published_convention']:.3e}) | "
      f"{'PASS' if any(c['name'] == 'incumbent_reproduces_cycle929_complete_mean' and c['pass'] for c in payload['checks']) else 'FAIL'} |")
    A(f"| Cycle-930 `riskparity_001` baseline on its own design | "
      f"{CYCLE930_BASELINE_MEAN:.6f} | "
      f"{fmt(payload['cycle930_cross_check']['mean_test_sharpe'])} | "
      f"{'PASS' if any(c['name'] == 'cycle930_riskparity_baseline_reproduced' and c['pass'] for c in payload['checks']) else 'FAIL'} |")
    A("")
    A("The Cycle-929 figure is the mean of the **published** per-fold Sharpes "
      "of the 41 complete folds; the full-precision recomputation is "
      f"{fmt(c929['recomputed_full_precision_mean'])} "
      f"(|Δ| = {c929['abs_gap_recomputed']:.3e} against the published figure). "
      "The difference is the four-decimal rounding of the published fold table "
      "(max per-fold |Δ| = "
      f"{anchor['max_fold_gap']:.3e}) — the same residual Cycle 929 documented "
      "for the phase decomposition — and it changes no gate outcome: both "
      "values are below the 0.9 threshold.")
    A("")

    A("## 8. What this does and does not change")
    A("")
    A("- **Nothing published changed.** The published record, the published "
      "gates, the published protocol, the committed shortlist and every "
      "committed candidate artefact are byte-identical after the run; the "
      "fetcher was never called and `data/` and `config/` are byte-identical.")
    A("- **No new candidate and no new edge is claimed.** The cycle measures "
      "two already-published mechanisms against a benchmark on one window; it "
      "proposes nothing and re-tunes nothing.")
    A("- **The incumbent's verdict is unchanged** (Credible Candidate by its "
      "published verdict, NO-GO for promotion) and `riskparity_001` remains "
      "rejected.")
    A("- **The comparison is an association, not a mechanism.** The 41 folds "
      "overlap (a 12-month test window on a 6-month step), so the pooled "
      "out-of-sample trade count is not 41 independent samples; the bootstrap "
      "CI is a moving-block interval on that serial structure, not an "
      "independent-sample interval.")
    A("")

    A("## 9. Reproduction")
    A("")
    A("```bash")
    A("python research/mechanism_comparison_001.py")
    A("python -m pytest -q tests/test_mechanism_comparison_001.py")
    A("python -m pytest -q tests/test_riskparity_001_evaluation.py")
    A("git status --porcelain data/ config/")
    A("```")
    A("")
    A("Every number in this report is re-derived by the first command from the "
      "committed cache, `config/`, `src/` and the committed published record.")
    A("")
    return "\n".join(lines)


def render_experiment(payload: dict[str, Any]) -> str:
    agg = payload["aggregates"]
    exc = payload["excess"]
    c929 = payload["cycle929_anchor"]
    lines: list[str] = []
    A = lines.append

    A(f"# Experiment: Like-for-like mechanism comparison "
      f"(mechanism_comparison_001)")
    A("")
    A(f"**Cycle {payload['cycle']}.**")
    A("")
    A("## Hypothesis reference")
    A("")
    A("This is a **measurement cycle**, not a candidate cycle. It has no new")
    A("hypothesis of its own: it re-measures the incumbent")
    A("`tsmomentum_spytrend_001`, the rejected `riskparity_001` candidate and")
    A("the 1/N benchmark on **one** point-in-time-complete window under **one**")
    A("walk-forward design and **one** cost model, and states each mechanism's")
    A("incremental value over 1/N. The inputs are the committed records:")
    A("")
    A("- `research/experiments/tsmomentum_regime_filter_wf_001.md` (the "
      "published 48-fold walk-forward record and the 0.947307 headline);")
    A("- `research/hypotheses/riskparity_001.md` and "
      "`research/experiments/riskparity_001_evaluation.md` (the pre-registered "
      "candidate and its Cycle-930 rejection);")
    A("- `research/experiments/tsmomentum_benchmark_001.md` (the 0.4716 1/N "
      "reference);")
    A("- `research/reports/data_cost_inventory_002.md` (the Cycle-929 "
      "point-in-time membership audit and the 0.787522 complete-cross-section "
      "figure).")
    A("")
    A("## Data used")
    A("")
    A(f"- **Source**: the committed parquet cache `data/raw/` (the fetcher is "
      "never called).")
    A(f"- **Universe**: {', '.join(payload['universe'])}.")
    A(f"- **Window**: {payload['window_start']} .. {payload['window_end']} "
      f"({payload['n_complete_folds']} folds; the panel itself starts "
      "1993-01-29 and ends 2026-10-19).")
    A("- **Frequency**: daily, weekdays, forward-filled onto the union "
      "calendar.")
    A("")
    A("## Point-in-time treatment")
    A("")
    A("- The incumbent's momentum selection uses only data available at "
      "formation (226-session lookback skipping the most recent 21 sessions); "
      "the SPY trend overlay uses a 200-session moving average.")
    A("- The `riskparity_001` weights use a **lagged** volatility estimate "
      "(the trailing window ends at t-1), so no same-session feedback is "
      "possible.")
    A("- A fold is *point-in-time complete* only when all seven members carry "
      "a valid momentum on **every** session of its test window; the "
      f"{payload['n_incomplete_folds']} folds that fail this test are excluded "
      "and the remaining folds are the measurement window for all three paths.")
    A("- No constituent-level membership exists in the repository and none is "
      "modelled; the asset-level membership is measured, as in Cycle 929.")
    A("")
    A("## Configuration")
    A("")
    A("| Item | Value |")
    A("|---|---|")
    A("| Walk-forward design | 10-year rolling train, 12-month test, 6-month "
      "step, 21-day purge, 21-day embargo (the published design) |")
    A(f"| Folds | {payload['n_complete_folds']} |")
    A(f"| Cost model | {payload['commission_bps']:.1f} bp commission + "
      f"{payload['slippage_bps']:.1f} bp slippage = "
      f"{payload['cost_per_unit'] * 10000.0:.1f} bp per unit of weight change |")
    A(f"| Risk-free rate | {payload['risk_free_annual']:.2f} annual |")
    A(f"| Incumbent | momentum selection (lookback {LOOKBACK}, skip {SKIP}, "
      f"top fraction {TOP_FRACTION}) + SPY 200-session trend overlay |")
    A(f"| `riskparity_001` | pre-registered baseline: lagged {RISKPARITY_LOOKBACK}"
      f"-session inverse volatility, cap {RISKPARITY_CAP} |")
    A("| 1/N benchmark | equal weight over the seven ETFs, constant weights |")
    A(f"| Bootstrap | moving block, block {exc['incumbent']['block']}, seed "
      f"{exc['incumbent']['seed']}, draws "
      f"{', '.join(str(d) for d in BOOTSTRAP_DRAWS)} |")
    A("")
    A("## Number of trials")
    A("")
    A("**1** — this cycle searches nothing. The `riskparity_001` path is the "
      "pre-registered baseline of the Cycle-930 grid (9 configurations, "
      "declared N = 9, already evaluated and rejected); the incumbent is the "
      "published path; the benchmark is the benchmark.")
    A("")
    A("## Results")
    A("")
    A("| Path | WF mean OOS Sharpe (backtest) | WF mean OOS Sharpe (canonical) "
      "| Positive folds | Pooled OOS trades | Gate 1 | Gate 2 | Gate 3 | "
      "Excess over 1/N | 95% CI (2000 draws) |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for key in ("incumbent", "riskparity_001", "one_over_n"):
        a = agg[key]
        g = a["gates"]
        if key in exc:
            e = exc[key]
            excess_cell = fmt(e["excess"])
            ci_cell = (
                f"[{fmt(e['ci']['2000']['ci_low'])}, "
                f"{fmt(e['ci']['2000']['ci_high'])}]"
            )
        else:
            excess_cell = "-"
            ci_cell = "-"
        A(f"| {a['label']} | {fmt(a['mean_test_sharpe'])} | "
          f"{fmt(a['mean_test_sharpe_canonical'])} | "
          f"{fmt(a['pct_positive_sharpe'])} | {a['total_test_trades']} | "
          f"{_gate_row('g1', g['wf_mean_oos_sharpe'])} | "
          f"{_gate_row('g2', g['positive_fold_rate'])} | "
          f"{_gate_row('g3', g['pooled_oos_trades'])} | {excess_cell} | "
          f"{ci_cell} |")
    A("")
    A("## Decision")
    A("")
    A(f"**{payload['label']}** — {payload['label_detail']}.")
    A("")
    A("The label applies to the incremental-value comparison only. The "
      "incumbent's published verdict is unchanged (a Credible Candidate by its "
      "published verdict and NO-GO for promotion) and `riskparity_001` remains "
      "rejected.")
    A("")
    A("## Reproduction commands")
    A("")
    A("```bash")
    A("python research/mechanism_comparison_001.py")
    A("python -m pytest -q tests/test_mechanism_comparison_001.py")
    A("git status --porcelain data/ config/")
    A("```")
    A("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="print the measurement without writing the report and experiment files",
    )
    args = parser.parse_args(argv)

    payload = run_comparison()

    if not args.no_report:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
        OUT_REPORT.write_text(render_report(payload), encoding="utf-8")
        OUT_EXP.write_text(render_experiment(payload), encoding="utf-8")

    agg = payload["aggregates"]
    exc = payload["excess"]
    c929 = payload["cycle929_anchor"]
    print(f"STRUCTURAL: {'PASS' if payload['structural_pass'] else 'FAIL'}")
    for check in payload["checks"]:
        print(f"CHECK|{check['name']}|{'PASS' if check['pass'] else 'FAIL'}")
    for key in ("incumbent", "riskparity_001", "one_over_n"):
        a = agg[key]
        print(f"PATH|{key}|WF_MEAN_OOS_SHARPE|{a['mean_test_sharpe']:.6f}|"
              f"CANONICAL|{a['mean_test_sharpe_canonical']:.6f}|"
              f"POSITIVE_FOLDS|{a['pct_positive_sharpe']:.6f}|"
              f"POOLED_TRADES|{a['total_test_trades']}")
    for key in ("incumbent", "riskparity_001"):
        e = exc[key]
        print(f"EXCESS|{key}|{e['excess']:.6f}|CI2000|"
              f"{e['ci']['2000']['ci_low']:.6f}|{e['ci']['2000']['ci_high']:.6f}|"
              f"CI1000|{e['ci']['1000']['ci_low']:.6f}|"
              f"{e['ci']['1000']['ci_high']:.6f}|"
              f"EXCLUDES_ZERO|{e['excludes_zero']}")
    print(f"CYCLE929_ANCHOR|{c929['published_convention_mean']:.6f}|"
          f"RECOMPUTED|{c929['recomputed_full_precision_mean']:.6f}|"
          f"TARGET|{c929['target']:.6f}")
    print(f"PUBLISHED_ANCHOR|{payload['published_anchor']['mean_test_sharpe']:.6f}|"
          f"{payload['published_anchor']['total_test_trades']}")
    print(f"CYCLE930_CROSSCHECK|"
          f"{payload['cycle930_cross_check']['mean_test_sharpe']:.6f}")
    print(f"WINDOW|{payload['window_start']}..{payload['window_end']}|"
          f"FOLDS|{payload['n_complete_folds']}")
    print(f"DECISION|{payload['decision']}")
    print(f"LABEL|{payload['label']}")
    print(
        f"REPORT|{OUT_REPORT if not args.no_report else '(not written: --no-report)'}"
    )
    print(
        f"EXPERIMENT|{OUT_EXP if not args.no_report else '(not written: --no-report)'}"
    )
    return 0 if payload["structural_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
