#!/usr/bin/env python3
"""Independent-sample significance of the riskparity_001 excess over 1/N.

Cycle 932.

What this tool does
-------------------
Cycle 931 put riskparity_001's excess over 1/N (+0.039267, moving-block bootstrap
95% CI [0.006458, 0.079121]) on the same 41 point-in-time-complete folds as the
incumbent. The 41 folds overlap (a 12-month test window on a 6-month step), so
the CI is on a serially dependent fold set, not on independent samples.

This cycle recomputes that excess on a **non-overlapping annual subset** of the
same point-in-time-complete window: it keeps every fold whose test window is
disjoint from every other kept fold, preferring the earliest disjoint fold in
each calendar year, so the kept folds share no session. It then reports a
moving-block bootstrap 95% CI on the paired per-fold excess over 1/N (same
seed 20240101 as Cycle 931) and states whether the significance survives.

No parameter search, no new candidate, no new hypothesis. The incumbent's
published verdict is unchanged.

Reproduction anchor
------------------
The Cycle-931 like-for-like comparison is reproduced first on the same 41
folds (incumbent 0.787524, riskparity_001 0.642829, 1/N 0.603562, excess
+0.039267, CI [0.006458, 0.079121] at 2000 draws). A mismatch fails the run.

The tool is **read-only**: the price panel is read from the committed parquet
cache (the fetcher is never called), nothing under ``data/`` or ``config/`` is
written, the SHA-256 of every file under those two trees and of every
committed artefact is compared before and after the run, and no committed
record, gate, protocol or shortlist row is modified.

Reproduction
-----------
```bash
python research/riskparity_annual_subset_001.py
python -m pytest -q tests/test_riskparity_annual_subset_001.py
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

CANDIDATE_ID = "riskparity_001"
CYCLE = "932"

RAW_DIR = REPO_ROOT / "data" / "raw"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
EXPERIMENTS_DIR = REPO_ROOT / "research" / "experiments"

OUT_REPORT = REPORTS_DIR / "riskparity_annual_subset_001.md"
OUT_EXP = EXPERIMENTS_DIR / "riskparity_annual_subset_001.md"

SELF_OUTPUTS = {
    str(OUT_REPORT.relative_to(REPO_ROOT)),
    str(OUT_EXP.relative_to(REPO_ROOT)),
}

UNIVERSE = list(SYMBOLS)

# The Cycle-931 baseline the run must reproduce before it publishes anything.
C931_RISKPARITY_MEAN = 0.642829
C931_ONE_OVER_N_MEAN = 0.603562
C931_EXCESS = 0.039267
C931_CI_LOW = 0.006458
C931_CI_HIGH = 0.079121
C931_DRAWS = 2000
C931_TOLERANCE = 1e-6

# Bootstrap settings: the seed is the Cycle-931 seed; the draw counts are the
# ones Cycle 931 used (2000 and 1000) and the block is the Cycle-931 rule
# (max(2, n_folds // 8)).
BOOTSTRAP_SEED = 20240101
BOOTSTRAP_DRAWS = (2000, 1000)

RISKPARITY_LOOKBACK, RISKPARITY_CAP = RISKPARITY_BASELINE


class AnnualSubsetError(RuntimeError):
    """Raised when a required input is missing or malformed (fails closed)."""


def fail(message: str) -> None:
    raise AnnualSubsetError(message)


# ----------------------------------------------------------------------
# Path construction (identical to Cycle 931)
# ----------------------------------------------------------------------
def equal_weight_path(close: pd.DataFrame, cost: float) -> tuple[pd.Series, pd.DataFrame]:
    """The 1/N equal-weight benchmark over the seven universe members."""
    weights = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    weights[:] = 1.0 / len(close.columns)
    net_ret, weights_a, _ = path_returns(close, weights, cost)
    return net_ret, weights_a


def riskparity_path(
    close: pd.DataFrame, lookback: int, cap: float, cost: float
) -> tuple[pd.Series, pd.DataFrame]:
    """The ``riskparity_001`` baseline: lagged inverse-volatility weights."""
    weights, _ = build_riskparity_weights(close, lookback, cap)
    net_ret, weights_a, _ = path_returns(close, weights, cost)
    return net_ret, weights_a


# ----------------------------------------------------------------------
# Non-overlapping annual subset selection
# ----------------------------------------------------------------------
def disjoint_annual_subset(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Select a maximal non-overlapping subset of folds, one per calendar year.

    The published 41 folds overlap: a 12-month test window on a 6-month step
    means consecutive test windows share roughly six months. This function
    keeps, for each calendar year that the measured window touches, the
    earliest fold whose test window is disjoint from every fold already kept,
    and stops when no further disjoint fold exists. The result is a set of
    folds that share no session, so the per-fold excess over 1/N measured on
    them is a set of (weakly) independent observations rather than a
    serially dependent one.

    The selection rule is deterministic and pre-specified: it depends only on
    the published fold table (test_start / test_end), not on any outcome.
    """
    ordered = sorted(rows, key=lambda r: (pd.Timestamp(r["test_start"]), int(r["fold"])))
    kept: list[dict[str, Any]] = []
    last_end: pd.Timestamp | None = None
    for row in ordered:
        start = pd.Timestamp(row["test_start"], tz="UTC")
        end = pd.Timestamp(row["test_end"], tz="UTC")
        if last_end is not None and start <= last_end:
            continue
        kept.append(row)
        last_end = end
    years = sorted({pd.Timestamp(r["test_start"], tz="UTC").year for r in kept})
    return kept, {
        "n_kept": len(kept),
        "folds": [int(r["fold"]) for r in kept],
        "years": years,
        "test_windows": [
            {"fold": int(r["fold"]), "start": r["test_start"], "end": r["test_end"]}
            for r in kept
        ],
    }


# ----------------------------------------------------------------------
# Statistics
# ----------------------------------------------------------------------
def aggregate(rows: list[dict[str, Any]], label: str) -> dict[str, Any]:
    """Aggregate the walk-forward statistics over a set of folds (one path)."""
    sharpes = [float(r["test_sharpe"]) for r in rows]
    canonical = [float(r["test_sharpe_canonical"]) for r in rows]
    pooled = int(sum(int(r["test_trades"]) for r in rows))
    mean_sharpe = float(np.mean(sharpes))
    positive_rate = float(np.mean([s > 0 for s in sharpes]))
    return {
        "label": label,
        "n_folds": len(rows),
        "folds": [int(r["fold"]) for r in rows],
        "mean_test_sharpe": mean_sharpe,
        "median_test_sharpe": float(np.median(sharpes)),
        "min_test_sharpe": float(np.min(sharpes)),
        "max_test_sharpe": float(np.max(sharpes)),
        "mean_test_sharpe_canonical": float(np.mean(canonical)),
        "pct_positive_sharpe": positive_rate,
        "total_test_trades": pooled,
        "sharpe_std": float(np.std(sharpes, ddof=1)) if len(sharpes) > 1 else float("nan"),
    }


def excess_bootstrap(
    path_sharpes: list[float],
    bench_sharpes: list[float],
    n_folds: int,
) -> dict[str, Any]:
    """Paired moving-block bootstrap CI on the per-fold excess over 1/N.

    The bootstrap is run on the paired per-fold differences, so the equity
    beta a long-only seven-asset book earns anyway cancels out. The block
    size follows the Cycle-931 rule (``max(2, n_folds // 8)``); the seed is
    the Cycle-931 seed and the draw counts are the ones Cycle 931 used.
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
        "n_obs": len(diffs),
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

# appended
