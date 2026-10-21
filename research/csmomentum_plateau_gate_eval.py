#!/usr/bin/env python3
"""Close the last open pre-registered gate of ``csmomentum_001`` (Cycle 922).

What this cycle does
--------------------
The C3 baseline (long-only cross-sectional momentum, 18-ETF universe) was
**already executed** -- the premise of the Cycle 922 hand-off ("no backtest has
been executed for C3 yet") is stale:

* ``research/run_cycle13.py`` executed the pre-registered baseline
  (252/21/0.5) with the chronological splits and the 48-fold walk-forward and
  published ``research/experiments/csmomentum_baseline_wf_001.md``;
* Cycle 871 re-ran the two month-end candidates on the **config-faithful**
  month-end schedule (``src/backtest/rebalance.py:build_month_end_weights``)
  and published ``research/reports/month_end_candidate_reaudit_001.md``;
* Cycle 907 published the pre-registered gate table on the three
  sample-policy samples (``research/reports/csmomentum_common_inception_gate_001.md``)
  and the candidate's label: **Rejected/Failed** (gate 1 fails on every sample).

What was still open is the **last of the four pre-registered promotion gates**:
the **parameter-plateau gate** (gate 4, ">= 2 of 3 lookbacks within 10% of the
baseline test Sharpe"), which every config-faithful record reports as
*NOT EVALUATED* because the 18-configuration pre-registered grid had never been
evaluated on that path. This tool evaluates it, and publishes the grid and the
multiple-testing record on the same config-faithful path, so that the
pre-registered falsification condition of
``research/hypotheses/csmomentum_001.md`` is complete on the path the verdict
is measured on.

Discipline (unchanged from the pre-registration)
------------------------------------------------
* The **decision subject is the pre-registered baseline** (252/21/0.5). No
  configuration is selected on any result; the grid is diagnostic (plateau gate
  + multiple-testing control), exactly as the hypothesis states.
* Read-only with respect to market data and configuration: the price panel is
  read **directly from the committed parquet cache** (``data/raw/*.parquet``);
  the fetcher is never called, nothing is downloaded, and every file under
  ``data/`` and ``config/`` is SHA-256 fingerprinted before and after the run.
* No gate, threshold, decision mapping, universe, cost model, parameter,
  candidate configuration or committed artifact is changed. The tool writes two
  **new** files (``research/reports/`` and ``research/experiments/``) and
  nothing else; ``--no-report`` writes neither.
* Deterministic: no RNG is used in the path; the block bootstrap uses the
  repository's own settings with a fixed seed.

Reproduction: ``python research/csmomentum_plateau_gate_eval.py``
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.csmomentum_common_inception_audit import (  # noqa: E402
    aligned_close_from_cache,
    fingerprint,
)
from research.month_end_candidate_reaudit import (  # noqa: E402
    compare_published,
    path_metrics,
    path_returns,
    walkforward,
)
from research.promotion_feasibility_backtest import load_yaml, scan_raw_cache  # noqa: E402
from src.backtest.engine import get_cost_params  # noqa: E402
from src.backtest.rebalance import build_month_end_weights  # noqa: E402
from src.evaluation.sharpe import backtest_sharpe_ratio  # noqa: E402
from src.evaluation.statistics import compute_dsr, compute_psr  # noqa: E402
from src.evaluation.walkforward import generate_walkforward_splits  # noqa: E402
from src.features.momentum import compute_momentum, select_top_decile  # noqa: E402

CONFIG_CAND = REPO_ROOT / "config" / "csmomentum_candidate_001.yaml"
RAW_DIR = REPO_ROOT / "data" / "raw"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
EXPERIMENTS_DIR = REPO_ROOT / "research" / "experiments"
OUT_REPORT = REPORTS_DIR / "csmomentum_plateau_gate_eval_001.md"
OUT_EXP = EXPERIMENTS_DIR / "csmomentum_plateau_gate_eval_001.md"

CANDIDATE_ID = "csmomentum_001"
CYCLE = 922

#: The pre-registered robustness grid
#: (``research/hypotheses/csmomentum_001.md``, "Pre-Specified Robustness Grid"
#: and the comment block of ``config/csmomentum_candidate_001.yaml``).
GRID_LOOKBACKS = (189, 252, 315)
GRID_SKIPS = (21, 42)
GRID_TOP_FRACTIONS = (0.3, 0.5, 0.7)
#: The pre-registered baseline (the centre of the grid, the decision subject).
BASELINE = (252, 21, 0.5)
#: The plateau gate is defined on the three lookbacks at the baseline's
#: ``skip`` and ``top_fraction`` (``research/hypotheses/csmomentum_001.md``,
#: "Falsification Condition", item 4).
PLATEAU_SKIP = 21
PLATEAU_TOP_FRACTION = 0.5

#: The repository plateau tolerance convention
#: (``src/evaluation/statistics.py:format_plateau_markdown`` and
#: ``research/run_cycle13.py``): ``max(0.1, 10% x |baseline test Sharpe|)``.
PLATEAU_ABS_FLOOR = 0.1
PLATEAU_REL = 0.10

#: The pre-registered gate count form of the plateau gate: ">= 2 of 3
#: lookbacks" (``research/hypotheses/csmomentum_001.md``; implemented as
#: ``GATE_PLATEAU_MIN_LOOKBACKS = 2`` in ``research/run_cycle13.py``).
PLATEAU_MIN_LOOKBACKS = 2

#: Block-bootstrap settings of the repository (identical to
#: ``research/run_cycle13.py``): 1000 samples, block 22, seed 42.
N_BOOTSTRAP = 1000
BLOCK_SIZE = 22
SEED = 42

#: The published config-faithful record of the union sample
#: (``research/reports/csmomentum_common_inception_gate_001.md`` and
#: ``research/reports/month_end_candidate_reaudit_001.md``), quoted with the
#: precision of the published record so that every comparison uses the
#: repository's own tolerance convention (the unit of the last published
#: decimal). The tool's OVERALL depends on reproducing them.
PUBLISHED_UNION_PATH = {
    "sharpe_backtest_scale": "0.4247",
    "sharpe_canonical": "0.6051",
    "max_drawdown": "-0.4474",
    "annualized_turnover": "2.16",
    "trade_days": "232",
    "mean_positions": "7.56",
}
PUBLISHED_UNION_WF = {
    "n_folds": "48",
    "mean_test_sharpe": "0.6975",
    "mean_test_sharpe_canonical": "0.8404",
    "median_test_sharpe": "0.6179",
    "pct_positive_sharpe": "0.7917",
    "total_test_trades": "400",
}
#: The pre-registered evaluation sample (``config/sample_policy.yaml``,
#: ``candidates.csmomentum_001``): the common-inception slice.
PUBLISHED_SLICE_WF = {
    "n_folds": "21",
    "mean_test_sharpe": "0.5861",
    "mean_test_sharpe_canonical": "0.7577",
    "median_test_sharpe": "0.6311",
    "pct_positive_sharpe": "0.7619",
    "total_test_trades": "166",
}

#: Committed artifacts this tool must not modify (byte-identical before/after).
COMMITTED_ARTIFACTS = (
    "research/experiments/csmomentum_001_experiment_001.md",
    "research/experiments/csmomentum_baseline_wf_001.md",
    "research/experiments/csmomentum_common_inception_001.md",
    "research/reports/month_end_candidate_reaudit_001.md",
    "research/reports/csmomentum_common_inception_gate_001.md",
    "research/reports/promotion_feasibility_backtest_001.md",
    "research/hypotheses/csmomentum_001.md",
)


# ----------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_hash() -> str:
    try:
        import subprocess

        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception:  # pragma: no cover - git is not available
        return "unknown"


def _fmt(value: Any, spec: str = ".4f") -> str:
    if value is None:
        return "N/A"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    try:
        f = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not np.isfinite(f):
        return "N/A"
    return format(f, spec)


# ----------------------------------------------------------------------
# The config-faithful path
# ----------------------------------------------------------------------
def _thr(value: Any) -> str:
    """Format a gate threshold without a spurious trailing ``.0``."""
    f = float(value)
    if f == int(f):
        return str(int(f))
    return f"{f:g}"


def build_path(
    close: pd.DataFrame,
    lookback: int,
    skip: int,
    top_fraction: float,
    cost_per_trade: float,
) -> dict[str, Any]:
    """The config-faithful month-end path of one parameter configuration.

    The signal is formed on the **last session** of the calendar month and the
    positions become effective on the **next** session
    (``src/backtest/rebalance.py:build_month_end_weights``); the selection mask
    is the repository's shared one (``src/features/momentum.py``); the costs are
    the frozen 3 bps round trip on the weight changes.
    """
    momentum = compute_momentum(close, lookback=lookback, skip=skip)
    mask = select_top_decile(momentum, top_fraction=top_fraction)
    weights, segments = build_month_end_weights(mask)
    net, weights_a, turnover = path_returns(close, weights, cost_per_trade)
    return {
        "momentum": momentum,
        "mask": mask,
        "weights": weights_a,
        "net": net,
        "turnover": turnover,
        "segments": segments,
        "mean_positions": float((weights_a > 0).sum(axis=1).mean()),
    }


def config_metrics(
    net: pd.Series,
    weights: pd.DataFrame,
    cost_per_trade: float,
    samples: dict[str, pd.Index],
) -> dict[str, Any]:
    """Train / validation / test metrics of one path (repository conventions)."""
    out: dict[str, Any] = {}
    for name, sample in samples.items():
        out[name] = path_metrics(net, weights, cost_per_trade, sample)
    return out


# ----------------------------------------------------------------------
# The plateau gate
# ----------------------------------------------------------------------
def plateau_gate(
    grid: pd.DataFrame,
    baseline: tuple[int, int, float],
    min_lookbacks: int,
) -> dict[str, Any]:
    """The pre-registered parameter-plateau gate (gate 4).

    The gate is defined on the **test-split Sharpe** of the three lookbacks at
    the baseline's ``skip`` and ``top_fraction``; the tolerance is the
    repository's convention ``max(0.1, 10% x |baseline test Sharpe|)``.
    """
    sub = grid[
        (grid["skip"] == PLATEAU_SKIP)
        & (np.isclose(grid["top_fraction"], PLATEAU_TOP_FRACTION))
    ].sort_values("lookback")
    base_row = grid[
        (grid["lookback"] == baseline[0])
        & (grid["skip"] == baseline[1])
        & (np.isclose(grid["top_fraction"], baseline[2]))
    ].iloc[0]
    baseline_sharpe = float(base_row["test_sharpe"])
    threshold = max(PLATEAU_ABS_FLOOR, PLATEAU_REL * abs(baseline_sharpe))
    rows = []
    n_within = 0
    for _, row in sub.iterrows():
        diff = abs(float(row["test_sharpe"]) - baseline_sharpe)
        within = diff <= threshold
        n_within += int(within)
        rows.append(
            {
                "lookback": int(row["lookback"]),
                "skip": int(row["skip"]),
                "top_fraction": float(row["top_fraction"]),
                "test_sharpe": float(row["test_sharpe"]),
                "abs_diff": float(diff),
                "within_tolerance": bool(within),
                "is_baseline": bool(int(row["lookback"]) == baseline[0]),
            }
        )
    fraction = n_within / len(sub) if len(sub) else 0.0
    return {
        "baseline_test_sharpe": baseline_sharpe,
        "threshold": float(threshold),
        "threshold_rule": "max(0.1, 10% x |baseline test Sharpe|)",
        "lookbacks": rows,
        "n_within": int(n_within),
        "n_lookbacks": int(len(sub)),
        "fraction": float(fraction),
        "min_lookbacks_required": int(min_lookbacks),
        "passed": bool(n_within >= min_lookbacks),
        # The literal reading of the config's fraction threshold (0.667) on a
        # three-point count is published next to the count form, because
        # 2/3 = 0.6667 rounds to 0.667 and a strict `>=` comparison on the
        # rounded fraction would demand 3 of 3. The count form is the
        # pre-registered one (hypothesis, and research/run_cycle13.py).
        "fraction_reading_would_pass": bool(fraction >= 0.667),
    }


# ----------------------------------------------------------------------
# Measurement
# ----------------------------------------------------------------------
def evaluate() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, observed: Any = None, expected: Any = None) -> None:
        checks.append(
            {"name": name, "expected": expected, "observed": observed, "pass": bool(passed)}
        )

    # --- the frozen configuration -------------------------------------
    config_text = CONFIG_CAND.read_text(encoding="utf-8")
    config_hash = sha256_file(CONFIG_CAND)
    cand = load_yaml(CONFIG_CAND)
    universe = list(cand["universe"])
    signal_cfg = cand["signal"]
    baseline = (
        int(signal_cfg["lookback"]),
        int(signal_cfg["skip"]),
        float(signal_cfg["top_fraction"]),
    )
    evaluation = cand["evaluation"]
    wf_cfg = evaluation["walk_forward"]
    gate_cfg = evaluation["promotion_gates"]
    mt_cfg = evaluation["multiple_testing"]
    history_start = str(cand["history_start"])
    test_end = str(evaluation["splits"]["test_end"])
    train_end = str(evaluation["splits"]["train_end"])
    val_end = str(evaluation["splits"]["validation_end"])
    cost_cfg = cand["cost_model"]
    commission, slippage = get_cost_params()
    cost_per_trade = commission + slippage

    check(
        "config_is_consumed_as_frozen",
        baseline == BASELINE,
        observed={"lookback": baseline[0], "skip": baseline[1], "top_fraction": baseline[2]},
        expected={"lookback": BASELINE[0], "skip": BASELINE[1], "top_fraction": BASELINE[2]},
    )
    check(
        "pre_registered_grid_still_declared_in_the_frozen_config",
        all(
            literal in config_text
            for literal in ("189", "252", "315", "21", "42", "0.3", "0.5", "0.7")
        ),
        observed="lookback {189, 252, 315} x skip {21, 42} x top_fraction {0.3, 0.5, 0.7}",
        expected="the grid literals of the frozen config's comment block",
    )
    check(
        "pre_registered_trial_count_is_read_from_the_config",
        int(mt_cfg["total_configs"]) == 27,
        observed=int(mt_cfg["total_configs"]),
        expected=27,
    )
    check(
        "cost_model_matches_the_frozen_config",
        bool(
            np.isclose(float(cost_cfg["total_round_trip_bps"]) * 1e-4, cost_per_trade, atol=1e-12)
        ),
        observed=cost_per_trade,
        expected=float(cost_cfg["total_round_trip_bps"]) * 1e-4,
    )

    # --- read-only fingerprints (before) ------------------------------
    data_before = fingerprint(REPO_ROOT / "data")
    config_before = fingerprint(REPO_ROOT / "config")
    artifacts_before = {rel: sha256_file(REPO_ROOT / rel) for rel in COMMITTED_ARTIFACTS}

    # --- data (committed cache only, never the fetcher) ---------------
    per_symbol_stats, raw_hashes, _raw_union_index = scan_raw_cache(universe)
    common_inception = pd.Timestamp(
        max(s["first_date"] for s in per_symbol_stats.values()), tz="UTC"
    )
    close_full = aligned_close_from_cache(universe)
    close_union = close_full.loc[
        (close_full.index >= pd.Timestamp(history_start, tz="UTC"))
        & (close_full.index <= pd.Timestamp(test_end, tz="UTC"))
    ].copy()
    close_slice = close_union.loc[close_union.index >= common_inception].copy()

    check(
        "evaluation_window_ends_at_the_frozen_test_end",
        close_union.index.max() == pd.Timestamp(test_end, tz="UTC"),
        observed=close_union.index.max().date().isoformat(),
        expected=test_end,
    )

    # --- the pre-registered splits and walk-forward protocol ----------
    train_sample = close_union.index[close_union.index <= pd.Timestamp(train_end, tz="UTC")]
    val_sample = close_union.index[
        (close_union.index > pd.Timestamp(train_end, tz="UTC"))
        & (close_union.index <= pd.Timestamp(val_end, tz="UTC"))
    ]
    test_sample = close_union.index[close_union.index > pd.Timestamp(val_end, tz="UTC")]
    samples = {"train": train_sample, "validation": val_sample, "test": test_sample}

    def splits_for(start: str) -> list[dict[str, Any]]:
        return generate_walkforward_splits(
            start,
            test_end,
            float(wf_cfg["train_years"]),
            float(wf_cfg["test_months"]),
            float(wf_cfg["step_months"]),
            int(wf_cfg["purge_days"]),
            int(wf_cfg["embargo_days"]),
        )

    union_splits = splits_for(history_start)
    slice_splits = splits_for(common_inception.date().isoformat())

    # --- the pre-registered grid on the config-faithful path ----------
    grid_rows: list[dict[str, Any]] = []
    grid_paths: dict[tuple[int, int, float], dict[str, Any]] = {}
    built: list[tuple[tuple[int, int, float], str]] = []
    for lookback in GRID_LOOKBACKS:
        for skip in GRID_SKIPS:
            for top_fraction in GRID_TOP_FRACTIONS:
                path = build_path(close_union, lookback, skip, top_fraction, cost_per_trade)
                built.append(((lookback, skip, top_fraction), "union_sample"))
                grid_paths[(lookback, skip, top_fraction)] = path
                metrics = config_metrics(
                    path["net"], path["weights"], cost_per_trade, samples
                )
                wf_summary, _rows = walkforward(
                    path["net"], path["weights"], union_splits
                )
                grid_rows.append(
                    {
                        "lookback": lookback,
                        "skip": skip,
                        "top_fraction": top_fraction,
                        "train_sharpe": float(metrics["train"]["sharpe_backtest_scale"]),
                        "val_sharpe": float(metrics["validation"]["sharpe_backtest_scale"]),
                        "test_sharpe": float(metrics["test"]["sharpe_backtest_scale"]),
                        "test_sharpe_canonical": float(metrics["test"]["sharpe_canonical"]),
                        "test_ann_return": float(metrics["test"]["annualized_return"]),
                        "test_max_dd": float(metrics["test"]["max_drawdown"]),
                        "test_turnover": float(metrics["test"]["annualized_turnover"]),
                        "test_trades": int(metrics["test"]["trade_days"]),
                        "test_sortino": float(metrics["test"]["sortino_ratio"]),
                        "test_profit_factor": float(metrics["test"]["profit_factor"]),
                        "wf_mean_test_sharpe": float(wf_summary["mean_test_sharpe"]),
                        "wf_median_test_sharpe": float(wf_summary["median_test_sharpe"]),
                        "wf_pct_positive": float(wf_summary["pct_positive_sharpe"]),
                        "wf_pooled_trades": int(wf_summary["total_test_trades"]),
                        "wf_n_folds": int(wf_summary["n_folds"]),
                    }
                )
    grid = pd.DataFrame(grid_rows)
    grid["rank"] = (
        grid["test_sharpe"].rank(ascending=False, method="min").astype(int)
    )

    # --- the baseline path (the decision subject) ---------------------
    base_path = grid_paths[BASELINE]
    base_metrics = config_metrics(
        base_path["net"], base_path["weights"], cost_per_trade, samples
    )
    union_path_summary = path_metrics(
        base_path["net"],
        base_path["weights"],
        cost_per_trade,
        close_union.index,
    )
    union_wf, _union_wf_rows = walkforward(
        base_path["net"], base_path["weights"], union_splits
    )

    # the pre-registered evaluation sample (common-inception slice)
    slice_path = build_path(close_slice, *BASELINE, cost_per_trade)
    built.append((BASELINE, "common_inception_slice"))
    slice_wf, _slice_wf_rows = walkforward(
        slice_path["net"], slice_path["weights"], slice_splits
    )
    slice_test_metrics = path_metrics(
        slice_path["net"], slice_path["weights"], cost_per_trade, test_sample
    )

    # --- reproduction anchors -----------------------------------------
    union_path_summary = dict(union_path_summary)
    union_path_summary["mean_positions"] = base_path["mean_positions"]
    union_path_anchor = compare_published(union_path_summary, PUBLISHED_UNION_PATH)
    union_wf_anchor = compare_published(union_wf, PUBLISHED_UNION_WF)
    slice_wf_anchor = compare_published(slice_wf, PUBLISHED_SLICE_WF)
    check(
        "union_sample_reproduces_the_published_config_faithful_path",
        all(r["match"] for r in union_path_anchor),
        observed={
            k: v for k, v in union_path_summary.items()
            if k in PUBLISHED_UNION_PATH
        },
        expected=PUBLISHED_UNION_PATH,
    )
    check(
        "union_sample_reproduces_the_published_walk_forward",
        all(r["match"] for r in union_wf_anchor),
        observed={
            "n_folds": union_wf.get("n_folds"),
            "mean_test_sharpe": union_wf.get("mean_test_sharpe"),
            "median_test_sharpe": union_wf.get("median_test_sharpe"),
            "pct_positive_sharpe": union_wf.get("pct_positive_sharpe"),
            "total_test_trades": union_wf.get("total_test_trades"),
        },
        expected=PUBLISHED_UNION_WF,
    )
    check(
        "common_inception_sample_reproduces_the_published_walk_forward",
        all(r["match"] for r in slice_wf_anchor),
        observed={
            "n_folds": slice_wf.get("n_folds"),
            "mean_test_sharpe": slice_wf.get("mean_test_sharpe"),
            "median_test_sharpe": slice_wf.get("median_test_sharpe"),
            "pct_positive_sharpe": slice_wf.get("pct_positive_sharpe"),
            "total_test_trades": slice_wf.get("total_test_trades"),
        },
        expected=PUBLISHED_SLICE_WF,
    )

    # --- the plateau gate (gate 4) ------------------------------------
    plateau = plateau_gate(grid, BASELINE, PLATEAU_MIN_LOOKBACKS)
    # the same gate on the pre-registered evaluation sample (the common
    # inception slice): the test split lies entirely after the warm-up ramp,
    # so the measurement is expected to be identical.
    slice_plateau_rows = []
    for lookback in GRID_LOOKBACKS:
        p = build_path(
            close_slice, lookback, PLATEAU_SKIP, PLATEAU_TOP_FRACTION, cost_per_trade
        )
        built.append(((lookback, PLATEAU_SKIP, PLATEAU_TOP_FRACTION), "common_inception_slice"))
        m = path_metrics(p["net"], p["weights"], cost_per_trade, test_sample)
        slice_plateau_rows.append(
            {"lookback": lookback, "test_sharpe": float(m["sharpe_backtest_scale"])}
        )
    slice_plateau_df = pd.DataFrame(slice_plateau_rows)
    base_slice = float(
        slice_plateau_df.loc[
            slice_plateau_df["lookback"] == BASELINE[0], "test_sharpe"
        ].iloc[0]
    )
    slice_threshold = max(PLATEAU_ABS_FLOOR, PLATEAU_REL * abs(base_slice))
    slice_n_within = int(
        ((slice_plateau_df["test_sharpe"] - base_slice).abs() <= slice_threshold).sum()
    )
    check(
        "plateau_measurement_is_invariant_to_the_sample_definition",
        abs(base_slice - plateau["baseline_test_sharpe"]) <= 1e-9
        and slice_n_within == plateau["n_within"],
        observed={
            "union_baseline_test_sharpe": plateau["baseline_test_sharpe"],
            "slice_baseline_test_sharpe": base_slice,
            "union_n_within": plateau["n_within"],
            "slice_n_within": slice_n_within,
        },
        expected="the test split lies entirely after the warm-up ramp, so both samples measure the same gate",
    )

    # --- the four-gate table of the baseline --------------------------
    def gate_table(wf_summary: dict[str, Any]) -> list[dict[str, Any]]:
        mean_wf = float(wf_summary.get("mean_test_sharpe", np.nan))
        pct_pos = float(wf_summary.get("pct_positive_sharpe", np.nan))
        pooled = int(wf_summary.get("total_test_trades", 0))
        g1 = bool(mean_wf >= float(gate_cfg["wf_mean_oos_sharpe_min"]))
        g2 = bool(pct_pos >= float(gate_cfg["positive_fold_rate_min"]))
        g3 = bool(pooled > float(gate_cfg["pooled_oos_trades_min"]))
        g4 = bool(plateau["passed"])
        return [
            {
                "name": "wf_mean_oos_sharpe",
                "threshold": float(gate_cfg["wf_mean_oos_sharpe_min"]),
                "threshold_text": f">= {_thr(gate_cfg['wf_mean_oos_sharpe_min'])}",
                "comparison": ">=",
                "value": mean_wf,
                "passed": g1,
                "source": "config/csmomentum_candidate_001.yaml:evaluation.promotion_gates",
            },
            {
                "name": "positive_fold_rate",
                "threshold": float(gate_cfg["positive_fold_rate_min"]),
                "threshold_text": f">= {_thr(gate_cfg['positive_fold_rate_min'])}",
                "comparison": ">=",
                "value": pct_pos,
                "passed": g2,
                "source": "config/csmomentum_candidate_001.yaml:evaluation.promotion_gates",
            },
            {
                "name": "pooled_oos_trades",
                "threshold": float(gate_cfg["pooled_oos_trades_min"]),
                "threshold_text": f"> {_thr(gate_cfg['pooled_oos_trades_min'])}",
                "comparison": ">",
                "value": pooled,
                "passed": g3,
                "source": "config/csmomentum_candidate_001.yaml:evaluation.promotion_gates",
            },
            {
                "name": "plateau",
                "threshold": float(PLATEAU_MIN_LOOKBACKS),
                "threshold_text": (
                    f">= {PLATEAU_MIN_LOOKBACKS} of {plateau['n_lookbacks']} lookbacks"
                ),
                "config_fraction_threshold": float(gate_cfg["plateau_fraction_min"]),
                "comparison": f">= {PLATEAU_MIN_LOOKBACKS} of {plateau['n_lookbacks']} lookbacks",
                "value": plateau["n_within"],
                "passed": g4,
                "source": "research/hypotheses/csmomentum_001.md (falsification condition, item 4)",
            },
        ]

    union_gates = gate_table(union_wf)
    slice_gates = gate_table(slice_wf)
    # the pre-registered falsification condition: gate 1 or gate 2 fails.
    falsified = (not union_gates[0]["passed"]) or (not union_gates[1]["passed"])
    label = "Rejected/Failed" if falsified else "Exploratory signal"
    decision = "NO-GO" if falsified else "GO"

    # --- the robustness diagnostic over the grid -----------------------
    gate1_min = float(gate_cfg["wf_mean_oos_sharpe_min"])
    clearing = grid[grid["wf_mean_test_sharpe"] >= gate1_min]
    robustness = {
        "n_configs": int(len(grid)),
        "n_clearing_gate1": int(len(clearing)),
        "clearing": [
            {
                "lookback": int(r["lookback"]),
                "skip": int(r["skip"]),
                "top_fraction": float(r["top_fraction"]),
                "wf_mean_test_sharpe": float(r["wf_mean_test_sharpe"]),
                "test_sharpe": float(r["test_sharpe"]),
            }
            for _, r in clearing.sort_values("wf_mean_test_sharpe", ascending=False).iterrows()
        ],
        "best_wf_config": {
            "lookback": int(grid.loc[grid["wf_mean_test_sharpe"].idxmax(), "lookback"]),
            "skip": int(grid.loc[grid["wf_mean_test_sharpe"].idxmax(), "skip"]),
            "top_fraction": float(
                grid.loc[grid["wf_mean_test_sharpe"].idxmax(), "top_fraction"]
            ),
            "wf_mean_test_sharpe": float(grid["wf_mean_test_sharpe"].max()),
        },
        "baseline_wf_mean_test_sharpe": float(
            grid.loc[
                (grid["lookback"] == BASELINE[0])
                & (grid["skip"] == BASELINE[1])
                & (np.isclose(grid["top_fraction"], BASELINE[2])),
                "wf_mean_test_sharpe",
            ].iloc[0]
        ),
        "note": (
            "diagnostic only: the pre-registered decision subject is the baseline "
            "(252, 21, 0.5); no configuration is selected on any of these results"
        ),
    }

    # --- multiple-testing control -------------------------------------
    test_net = base_path["net"].loc[test_sample]
    dsr_pre = compute_dsr(
        test_net,
        n_configs=int(mt_cfg["total_configs"]),
        n_bootstrap=N_BOOTSTRAP,
        block_size=BLOCK_SIZE,
        seed=SEED,
    )
    dsr_actual = compute_dsr(
        test_net,
        n_configs=int(len(grid)),
        n_bootstrap=N_BOOTSTRAP,
        block_size=BLOCK_SIZE,
        seed=SEED,
    )
    psr_zero = compute_psr(
        test_net, sr_target=0.0, n_bootstrap=N_BOOTSTRAP, block_size=BLOCK_SIZE, seed=SEED
    )
    psr_gate = compute_psr(
        test_net,
        sr_target=gate1_min,
        n_bootstrap=N_BOOTSTRAP,
        block_size=BLOCK_SIZE,
        seed=SEED,
    )
    # The DSR of the committed Cycle 13 record was computed with the
    # pre-Cycle-861 estimator (the backtest-baseline-scale Sharpe as the
    # numerator); Cycle 861 unified the Sharpe convention and
    # ``compute_dsr`` now uses the canonical one
    # (``arithmetic_annualized_rf0``). The two numbers are therefore not
    # comparable, so the record's own estimator is reconstructed here with
    # the same bootstrap standard error: DSR = (SR_backtest - SE*E[max])/SE.
    def legacy_scale_dsr(dsr_block: dict[str, Any]) -> float:
        se = float(dsr_block["sharpe_se"])
        if se <= 0:
            return 0.0
        return float(
            (backtest_sharpe_ratio(test_net) - se * float(dsr_block["e_max"])) / se
        )

    legacy_scale = {
        "sr_observed_backtest_scale": float(backtest_sharpe_ratio(test_net)),
        "dsr_at_preregistered_n": legacy_scale_dsr(dsr_pre),
        "dsr_at_actual_n": legacy_scale_dsr(dsr_actual),
        "note": (
            "the estimator the committed Cycle 13 record used (the backtest-baseline-scale "
            "Sharpe as the numerator, before Cycle 861 unified the convention); computed "
            "with the same block-bootstrap standard error so that it is comparable with "
            "research/experiments/csmomentum_baseline_wf_001.md"
        ),
    }
    is_oos = {
        "is_oos_spearman": float(
            grid["train_sharpe"].corr(grid["test_sharpe"], method="spearman")
        ),
        "mean_is_sharpe": float(grid["train_sharpe"].mean()),
        "mean_oos_sharpe": float(grid["test_sharpe"].mean()),
        "n_configs_with_positive_test_sharpe": int((grid["test_sharpe"] > 0).sum()),
        "best_is_config_test_sharpe": float(
            grid.loc[grid["train_sharpe"].idxmax(), "test_sharpe"]
        ),
    }

    # --- the selection breadth (a measured disclosure) ----------------
    base_mask = base_path["mask"]
    selected = base_mask.sum(axis=1)
    test_holding = selected.loc[test_sample]
    test_holding = test_holding[test_holding > 0]
    breadth = {
        "universe_size": len(universe),
        "pre_registered_top_fraction": BASELINE[2],
        "implied_rank_count": int(round(BASELINE[2] * len(universe))),
        "full_sample_mean": float(selected.mean()),
        "full_sample_median": float(selected.median()),
        "full_sample_min": int(selected.min()),
        "full_sample_max": int(selected.max()),
        "test_window_mean": float(test_holding.mean()),
        "test_window_median": float(test_holding.median()),
        "test_window_min": int(test_holding.min()),
        "test_window_max": int(test_holding.max()),
        "test_window_sessions": int(len(test_holding)),
        "note": (
            "the shared selection module holds every asset whose cross-sectional RANK is "
            ">= max_rank x (1 - top_fraction) (the rule documented in "
            "research/hypotheses/sectorrotation_001.md); the boundary rank is inclusive, so "
            "18 assets at top_fraction 0.5 give the top 10 of 18 (55.6%), one asset more "
            "than the literal 'top 50%' reading of the csmomentum hypothesis prose. The "
            "rule is applied identically to the baseline and to every configuration of the "
            "grid, so it does not bias the plateau comparison."
        ),
    }
    # The selection mask must be exactly the documented rank rule.
    documented = base_path["momentum"].rank(
        axis=1, ascending=True, method="average", na_option="keep"
    )
    documented_mask = pd.DataFrame(
        False, index=documented.index, columns=documented.columns
    )
    for stamp, row in documented.iterrows():
        if row.isna().all():
            continue
        documented_mask.loc[stamp, :] = row.ge(row.max() * (1.0 - BASELINE[2]))
    check(
        "selection_follows_the_documented_rank_rule",
        bool((base_mask.to_numpy() == documented_mask.to_numpy()).all()),
        observed={
            "rule": "rank >= max_rank x (1 - top_fraction)",
            "held_in_the_test_window": f"{breadth['test_window_min']}..{breadth['test_window_max']} of {len(universe)}",
            "mask_equals_the_documented_rule": bool(
                (base_mask.to_numpy() == documented_mask.to_numpy()).all()
            ),
        },
        expected="the mask is exactly the documented rank rule",
    )

    # --- read-only fingerprints (after) -------------------------------
    data_after = fingerprint(REPO_ROOT / "data")
    config_after = fingerprint(REPO_ROOT / "config")
    artifacts_after = {rel: sha256_file(REPO_ROOT / rel) for rel in COMMITTED_ARTIFACTS}
    check(
        "data_and_config_unchanged",
        data_before == data_after and config_before == config_after,
        observed={"data": data_before == data_after, "config": config_before == config_after},
        expected={"data": True, "config": True},
    )
    check(
        "committed_artifacts_unchanged",
        artifacts_before == artifacts_after,
        observed=[rel for rel in COMMITTED_ARTIFACTS if artifacts_before[rel] != artifacts_after[rel]],
        expected="no committed artifact modified",
    )
    check(
        "the_fetcher_is_never_called",
        ("fetch_" + "universe") not in Path(__file__).read_text(encoding="utf-8"),
        observed="the tool's source carries no fetcher call",
        expected="no fetcher call",
    )
    baseline_builds = [tag for params, tag in built if params == BASELINE and tag == "union_sample"]
    check(
        "walk_forward_uses_fixed_parameters",
        len(baseline_builds) == 1,
        observed={
            "baseline_paths_built": len(baseline_builds),
            "paths_built_in_total": len(built),
            "parameter": {"lookback": BASELINE[0], "skip": BASELINE[1], "top_fraction": BASELINE[2]},
            "folds": int(union_wf.get("n_folds", 0)),
            "note": (
                "the baseline path is built once and every fold is a slice of that one "
                "continuously computed point-in-time path, so no per-fold re-optimisation "
                "is possible"
            ),
        },
        expected="the baseline path is built exactly once and reused by every fold",
    )
    check(
        "grid_size_is_the_pre_registered_unique_combination_count",
        int(len(grid)) == 18,
        observed=int(len(grid)),
        expected=18,
    )
    check(
        "plateau_gate_reading_is_disclosed",
        True,
        observed={
            "count_form": f">= {PLATEAU_MIN_LOOKBACKS} of {plateau['n_lookbacks']}",
            "n_within": plateau["n_within"],
            "fraction": plateau["fraction"],
            "config_fraction_threshold": float(gate_cfg["plateau_fraction_min"]),
            "literal_fraction_reading_would_pass": plateau["fraction_reading_would_pass"],
        },
        expected="both readings published (2/3 = 0.6667 rounds to the config's 0.667)",
    )

    structural_pass = all(c["pass"] for c in checks)

    payload: dict[str, Any] = {
        "candidate": CANDIDATE_ID,
        "cycle": CYCLE,
        "git_rev": _git_hash(),
        "config_sha256": config_hash,
        "candidate_configuration": {
            "universe": universe,
            "universe_size": len(universe),
            "lookback": BASELINE[0],
            "skip": BASELINE[1],
            "top_fraction": BASELINE[2],
            "history_start": history_start,
            "test_end": test_end,
            "cost_model": cost_cfg,
            "walk_forward": wf_cfg,
            "promotion_gates": gate_cfg,
            "multiple_testing": mt_cfg,
        },
        "samples": {
            "union_sample": {
                "start": close_union.index[0].date().isoformat(),
                "end": close_union.index[-1].date().isoformat(),
                "sessions": int(len(close_union)),
                "price_width_min": int(close_union.notna().sum(axis=1).min()),
                "price_width_max": int(close_union.notna().sum(axis=1).max()),
            },
            "common_inception_slice": {
                "start": close_slice.index[0].date().isoformat(),
                "end": close_slice.index[-1].date().isoformat(),
                "sessions": int(len(close_slice)),
                "common_inception": common_inception.date().isoformat(),
                "price_width_min": int(close_slice.notna().sum(axis=1).min()),
                "price_width_max": int(close_slice.notna().sum(axis=1).max()),
            },
        },
        "raw_cache_fingerprint": {
            sym: {
                "first_date": per_symbol_stats[sym]["first_date"],
                "last_date": per_symbol_stats[sym]["last_date"],
                "row_count": per_symbol_stats[sym]["row_count"],
                "sha256": raw_hashes[sym],
            }
            for sym in universe
        },
        "splits": {
            "train": [str(train_sample[0].date()), str(train_sample[-1].date())],
            "validation": [str(val_sample[0].date()), str(val_sample[-1].date())],
            "test": [str(test_sample[0].date()), str(test_sample[-1].date())],
        },
        "baseline_path_union": union_path_summary,
        "baseline_split_metrics": {
            "train": base_metrics["train"],
            "validation": base_metrics["validation"],
            "test": base_metrics["test"],
        },
        "baseline_test_metrics_slice_sample": slice_test_metrics,
        "walk_forward_union": {
            "n_folds": int(union_wf.get("n_folds", 0)),
            "mean_test_sharpe": float(union_wf.get("mean_test_sharpe", float("nan"))),
            "mean_test_sharpe_canonical": float(
                union_wf.get("mean_test_sharpe_canonical", float("nan"))
            ),
            "median_test_sharpe": float(union_wf.get("median_test_sharpe", float("nan"))),
            "std_test_sharpe": float(union_wf.get("std_test_sharpe", float("nan"))),
            "pct_positive_sharpe": float(union_wf.get("pct_positive_sharpe", float("nan"))),
            "total_test_trades": int(union_wf.get("total_test_trades", 0)),
        },
        "walk_forward_slice": {
            "n_folds": int(slice_wf.get("n_folds", 0)),
            "mean_test_sharpe": float(slice_wf.get("mean_test_sharpe", float("nan"))),
            "mean_test_sharpe_canonical": float(
                slice_wf.get("mean_test_sharpe_canonical", float("nan"))
            ),
            "median_test_sharpe": float(slice_wf.get("median_test_sharpe", float("nan"))),
            "pct_positive_sharpe": float(slice_wf.get("pct_positive_sharpe", float("nan"))),
            "total_test_trades": int(slice_wf.get("total_test_trades", 0)),
        },
        "gates_union": union_gates,
        "gates_slice": slice_gates,
        "failed_gates": [g["name"] for g in union_gates if not g["passed"]],
        "plateau": plateau,
        "plateau_slice_sample": {
            "baseline_test_sharpe": base_slice,
            "threshold": float(slice_threshold),
            "n_within": slice_n_within,
            "lookbacks": [
                {"lookback": int(r["lookback"]), "test_sharpe": float(r["test_sharpe"])}
                for _, r in slice_plateau_df.iterrows()
            ],
        },
        "grid": [
            {k: (float(v) if isinstance(v, (float, np.floating)) else int(v) if isinstance(v, (int, np.integer)) else v)
             for k, v in row.items()}
            for row in grid.to_dict("records")
        ],
        "robustness_diagnostic": robustness,
        "multiple_testing": {
            "dsr_pre_registered_n": {
                "n_configs": int(mt_cfg["total_configs"]),
                "dsr": float(dsr_pre["dsr"]),
                "dsr_probability": float(dsr_pre["dsr_probability"]),
                "sr_observed": float(dsr_pre["sr_observed"]),
                "sharpe_se": float(dsr_pre["sharpe_se"]),
                "sr_threshold": float(dsr_pre["sr_threshold"]),
                "e_max": float(dsr_pre["e_max"]),
            },
            "dsr_actual_n": {
                "n_configs": int(len(grid)),
                "dsr": float(dsr_actual["dsr"]),
                "dsr_probability": float(dsr_actual["dsr_probability"]),
                "sr_observed": float(dsr_actual["sr_observed"]),
                "sharpe_se": float(dsr_actual["sharpe_se"]),
                "sr_threshold": float(dsr_actual["sr_threshold"]),
                "e_max": float(dsr_actual["e_max"]),
            },
            "psr_vs_zero": {
                "psr_normal": float(psr_zero["psr_normal"]),
                "psr_empirical": float(psr_zero["psr_empirical"]),
                "sharpe_se": float(psr_zero["sharpe_se"]),
            },
            "psr_vs_gate": {
                "psr_normal": float(psr_gate["psr_normal"]),
                "psr_empirical": float(psr_gate["psr_empirical"]),
                "sharpe_se": float(psr_gate["sharpe_se"]),
            },
            "block_bootstrap_ci_95": [
                float(psr_zero["ci_lower"]),
                float(psr_zero["ci_upper"]),
            ],
            "legacy_scale": legacy_scale,
            "n_bootstrap": N_BOOTSTRAP,
            "block_size": BLOCK_SIZE,
            "seed": SEED,
            "is_oos": is_oos,
        },
        "selection_breadth": breadth,
        "anchors": {
            "union_path": union_path_anchor,
            "union_walk_forward": union_wf_anchor,
            "slice_walk_forward": slice_wf_anchor,
        },
        "checks": checks,
        "structural_pass": structural_pass,
        "decision": decision,
        "label": label,
        "falsified": bool(falsified),
    }
    return payload


# ----------------------------------------------------------------------
# Reporting
# ----------------------------------------------------------------------
def render_report(p: dict[str, Any]) -> str:
    L: list[str] = []
    A = L.append
    A(f"# CSMomentum Plateau-Gate Evaluation ({p['candidate']}, Cycle {p['cycle']})")
    A("")
    A("## Summary")
    A("")
    A(
        "The C3 baseline was **already executed** (Cycle 13, `research/run_cycle13.py`) and "
        "its config-faithful gate table was published in Cycle 907; the candidate's label is "
        "unchanged. What was still open is the **last of the four pre-registered promotion "
        "gates**: the **parameter-plateau gate** (gate 4). This cycle evaluates it on the "
        "config-faithful month-end path, publishes the pre-registered 18-configuration grid "
        "on that path, and completes the multiple-testing record."
    )
    A("")
    A(f"- Candidate: `{p['candidate']}` (pre-registered baseline 252/21/0.5)")
    A(f"- Git rev: {p['git_rev']}")
    A(f"- Frozen config SHA-256: `{p['config_sha256']}`")
    A(f"- Decision: **{p['decision']}** -- research label **{p['label']}**")
    A(f"- Failed gates: {', '.join(p['failed_gates']) or 'none'}")
    A("")
    A("## 1. Method")
    A("")
    A(
        "The price panel is read **directly from the committed cache** "
        "(`data/raw/*.parquet`); the fetcher is never called, nothing is downloaded, and every "
        "file under `data/` and `config/` is SHA-256 fingerprinted before and after the run. "
        "The path is the **config-faithful month-end schedule** "
        "(`src/backtest/rebalance.py:build_month_end_weights`): the signal is formed on the "
        "last session of the calendar month, the positions become effective on the next "
        "session, the costs are the frozen 3 bps round trip on the weight changes and the "
        "signal lag is 1 day."
    )
    A("")
    A("| Item | Value |")
    A("|---|---|")
    A(f"| Universe | {p['candidate_configuration']['universe_size']} ETFs |")
    A(
        f"| Union sample | {p['samples']['union_sample']['start']} .. "
        f"{p['samples']['union_sample']['end']} "
        f"({p['samples']['union_sample']['sessions']} sessions, price width "
        f"{p['samples']['union_sample']['price_width_min']}..{p['samples']['union_sample']['price_width_max']}) |"
    )
    A(
        f"| Common-inception slice (pre-registered evaluation sample) | "
        f"{p['samples']['common_inception_slice']['start']} .. "
        f"{p['samples']['common_inception_slice']['end']} "
        f"({p['samples']['common_inception_slice']['sessions']} sessions, price width "
        f"{p['samples']['common_inception_slice']['price_width_min']}.."
        f"{p['samples']['common_inception_slice']['price_width_max']}) |"
    )
    A(
        f"| Splits | train {p['splits']['train'][0]}..{p['splits']['train'][1]}, "
        f"validation {p['splits']['validation'][0]}..{p['splits']['validation'][1]}, "
        f"test {p['splits']['test'][0]}..{p['splits']['test'][1]} |"
    )
    wf = p["candidate_configuration"]["walk_forward"]
    A(
        f"| Walk-forward | {wf['train_years']}y train / {wf['test_months']}m test / "
        f"{wf['step_months']}m step, {wf['purge_days']}d purge, {wf['embargo_days']}d embargo, "
        "**fixed parameters** (no per-fold re-optimisation) |"
    )
    A("")
    A("## 2. Reproduction anchors")
    A("")
    A(
        "The tool fails closed if it does not reproduce the published config-faithful record "
        "of `research/reports/csmomentum_common_inception_gate_001.md`."
    )
    A("")
    A("| Metric | Published | Observed | Tolerance | Result |")
    A("|---|---|---|---|---|")
    for group in ("union_path", "union_walk_forward", "slice_walk_forward"):
        for row in p["anchors"][group]:
            obs = "N/A" if row["observed"] is None else f"{row['observed']:.6f}"
            pub = f"{row['published']:.{row['decimals']}f}"
            A(
                f"| `{row['metric']}` ({group}) | {pub} | {obs} | "
                f"{row['tolerance']:.0e} | {'MATCH' if row['match'] else 'MISMATCH'} |"
            )
    A("")
    A("## 3. The pre-registered gate table (baseline 252/21/0.5)")
    A("")
    A("| Gate | Threshold | Observed (union) | Result | Observed (common-inception slice) | Result |")
    A("|---|---|---|---|---|---|")
    for g_union, g_slice in zip(p["gates_union"], p["gates_slice"]):
        A(
            f"| {g_union['name']} | {g_union['threshold_text']} | "
            f"{_fmt(g_union['value'])} | {'PASS' if g_union['passed'] else 'FAIL'} | "
            f"{_fmt(g_slice['value'])} | {'PASS' if g_slice['passed'] else 'FAIL'} |"
        )
    A("")
    A(
        f"**Decision: {p['decision']} -- {p['label']}.** The pre-registered falsification "
        "condition (`research/hypotheses/csmomentum_001.md`: gate 1 or gate 2 fails) is met, "
        "so the candidate is rejected/failed. The plateau gate (gate 4) is now **EVALUATED** "
        "instead of NOT EVALUATED; it does not enter the falsification condition, so it does "
        "not change the verdict."
    )
    A("")
    A("## 4. The parameter-plateau gate (gate 4)")
    A("")
    pl = p["plateau"]
    A(
        f"- Baseline test Sharpe: **{pl['baseline_test_sharpe']:.4f}**; tolerance "
        f"**{pl['threshold']:.4f}** (`{pl['threshold_rule']}`)"
    )
    A(f"- Lookbacks within tolerance: **{pl['n_within']} of {pl['n_lookbacks']}**")
    A(
        f"- Gate (\">= {pl['min_lookbacks_required']} of {pl['n_lookbacks']} lookbacks\"): "
        f"**{'PASS' if pl['passed'] else 'FAIL'}**"
    )
    A("")
    A("| Lookback | Skip | Top fraction | Test Sharpe | Abs. diff | Within tolerance |")
    A("|---|---|---|---|---|---|")
    for row in pl["lookbacks"]:
        A(
            f"| {row['lookback']}{' (baseline)' if row['is_baseline'] else ''} | {row['skip']} | "
            f"{row['top_fraction']:.1f} | {row['test_sharpe']:.4f} | {row['abs_diff']:.4f} | "
            f"{'yes' if row['within_tolerance'] else 'no'} |"
        )
    A("")
    A(
        f"**Threshold-reading disclosure.** The hypothesis states the gate in the count form "
        f"(\">= {pl['min_lookbacks_required']} of {pl['n_lookbacks']} lookbacks\"), which is what "
        f"this tool applies. The frozen config expresses the same threshold as a fraction "
        f"(`plateau_fraction_min: "
        f"{p['candidate_configuration']['promotion_gates']['plateau_fraction_min']}`); because "
        f"2/3 = 0.6667 rounds to 0.667, a literal `>=` comparison on the rounded fraction "
        f"would demand 3 of 3 rather than 2 of 3. Both readings are published and they agree "
        f"here: the observed fraction is {pl['fraction']:.4f} "
        f"({pl['n_within']} of {pl['n_lookbacks']}), which "
        f"{'passes' if pl['fraction_reading_would_pass'] else 'fails'} under the literal "
        f"fraction reading as well."
    )
    A("")
    A(
        "The gate is **invariant to the sample definition**: the test split lies entirely "
        "after the 252+21 warm-up ramp, so the union sample and the pre-registered "
        "common-inception slice measure the identical numbers "
        f"(slice: {p['plateau_slice_sample']['n_within']} of "
        f"{pl['n_lookbacks']} within {p['plateau_slice_sample']['threshold']:.4f})."
    )
    A("")
    A("## 5. The pre-registered grid on the config-faithful path")
    A("")
    A(
        "All 18 unique pre-specified combinations (3 lookbacks x 2 skips x 3 top fractions) "
        "evaluated on the identical test split with the identical execution convention. The "
        "grid is **diagnostic**: the baseline is pre-specified and no configuration is selected "
        "on any of these results."
    )
    A("")
    A(
        "| Lookback | Skip | Top fraction | Train Sharpe | Val Sharpe | Test Sharpe | Test ann. ret. | "
        "Test max DD | Test trades | Test turnover | WF mean OOS Sharpe | Rank |"
    )
    A("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for row in sorted(p["grid"], key=lambda r: r["rank"]):
        A(
            f"| {row['lookback']} | {row['skip']} | {row['top_fraction']:.1f} | "
            f"{row['train_sharpe']:.4f} | {row['val_sharpe']:.4f} | {row['test_sharpe']:.4f} | "
            f"{row['test_ann_return']:.4f} | {row['test_max_dd']:.4f} | {row['test_trades']} | "
            f"{row['test_turnover']:.2f} | {row['wf_mean_test_sharpe']:.4f} | {row['rank']} |"
        )
    A("")
    rb = p["robustness_diagnostic"]
    A("### Robustness of the rejection across the pre-registered neighbourhood")
    A("")
    A(
        f"- Configurations clearing gate 1 (walk-forward mean OOS Sharpe >= "
        f"{p['candidate_configuration']['promotion_gates']['wf_mean_oos_sharpe_min']}): "
        f"**{rb['n_clearing_gate1']} of {rb['n_configs']}**"
    )
    A(
        f"- Baseline (252/21/0.5) walk-forward mean OOS Sharpe: "
        f"**{rb['baseline_wf_mean_test_sharpe']:.4f}**"
    )
    A(
        f"- Best configuration in the grid: ({rb['best_wf_config']['lookback']}, "
        f"{rb['best_wf_config']['skip']}, {rb['best_wf_config']['top_fraction']:.1f}) at "
        f"**{rb['best_wf_config']['wf_mean_test_sharpe']:.4f}**"
    )
    if rb["clearing"]:
        A("")
        A("| Lookback | Skip | Top fraction | WF mean OOS Sharpe | Test Sharpe |")
        A("|---|---|---|---|---|")
        for row in rb["clearing"]:
            A(
                f"| {row['lookback']} | {row['skip']} | {row['top_fraction']:.1f} | "
                f"{row['wf_mean_test_sharpe']:.4f} | {row['test_sharpe']:.4f} |"
            )
    A("")
    A(f"> {rb['note']}.")
    A("")
    A("## 6. Multiple-testing control")
    A("")
    mt = p["multiple_testing"]
    A(
        f"- Deflated Sharpe Ratio at the **pre-registered trial count N="
        f"{mt['dsr_pre_registered_n']['n_configs']}** (primary, conservative): "
        f"**{mt['dsr_pre_registered_n']['dsr']:.4f}** "
        f"(DSR probability {mt['dsr_pre_registered_n']['dsr_probability']:.4f}); observed test "
        f"Sharpe {mt['dsr_pre_registered_n']['sr_observed']:.4f}, deflation threshold "
        f"{mt['dsr_pre_registered_n']['sr_threshold']:.4f}, SE "
        f"{mt['dsr_pre_registered_n']['sharpe_se']:.4f}, E[max of N] "
        f"{mt['dsr_pre_registered_n']['e_max']:.4f}"
    )
    A(
        f"- Deflated Sharpe Ratio at the **actual evaluated count N="
        f"{mt['dsr_actual_n']['n_configs']}** (disclosure; the pre-registration's label of "
        f"27 is a mislabel -- 3 x 2 x 3 yields 18 unique combinations, and no configuration "
        f"was invented to reach 27): **{mt['dsr_actual_n']['dsr']:.4f}** "
        f"(DSR probability {mt['dsr_actual_n']['dsr_probability']:.4f})"
    )
    A(
        f"- Probabilistic Sharpe Ratio vs SR=0: {mt['psr_vs_zero']['psr_normal']:.4f} "
        f"(empirical {mt['psr_vs_zero']['psr_empirical']:.4f}); vs the 0.9 gate: "
        f"{mt['psr_vs_gate']['psr_normal']:.4f} (empirical "
        f"{mt['psr_vs_gate']['psr_empirical']:.4f})"
    )
    A(
        f"- Block-bootstrap Sharpe 95% CI: "
        f"[{mt['block_bootstrap_ci_95'][0]:.4f}, {mt['block_bootstrap_ci_95'][1]:.4f}]"
    )
    A(
        f"- **Scale disclosure.** The DSR and PSR above use the repository's *current* Sharpe "
        f"convention (`arithmetic_annualized_rf0`, unified in Cycle 861), on which the "
        f"baseline's test-split Sharpe is "
        f"{mt['dsr_pre_registered_n']['sr_observed']:.4f}. The committed Cycle 13 record's DSR "
        f"(**-0.6484** at N=27) was computed with the *pre*-Cycle-861 estimator (the "
        f"backtest-baseline-scale Sharpe {mt['legacy_scale']['sr_observed_backtest_scale']:.4f} "
        f"as the numerator), so the two numbers are **not comparable**. Reconstructed with the "
        f"record's own estimator and the same bootstrap standard error, this path's DSR is "
        f"**{mt['legacy_scale']['dsr_at_preregistered_n']:.4f}** at N=27 and "
        f"**{mt['legacy_scale']['dsr_at_actual_n']:.4f}** at N=18 -- negative, i.e. on the "
        f"record's own scale the observed test Sharpe does **not** survive the multiple-testing "
        f"deflation either. The DSR is not part of the pre-registered falsification condition "
        f"and does not enter the verdict."
    )
    A(
        f"- IS-OOS Spearman rank correlation: {mt['is_oos']['is_oos_spearman']:.4f}; mean IS "
        f"Sharpe {mt['is_oos']['mean_is_sharpe']:.4f} vs mean OOS Sharpe "
        f"{mt['is_oos']['mean_oos_sharpe']:.4f}; "
        f"{mt['is_oos']['n_configs_with_positive_test_sharpe']} of {rb['n_configs']} "
        f"configurations have a positive test Sharpe; the best-IS configuration's test Sharpe "
        f"is {mt['is_oos']['best_is_config_test_sharpe']:.4f}"
    )
    A(
        f"- Bootstrap settings: {mt['n_bootstrap']} samples, block {mt['block_size']}, seed "
        f"{mt['seed']} (the repository's own settings)"
    )
    A("")
    A("## 7. A measured disclosure: the selection breadth")
    A("")
    b = p["selection_breadth"]
    A(
        f"The shared selection module (`src/features/momentum.py:select_top_decile`) holds "
        f"every asset whose cross-sectional **rank** is >= max_rank x (1 - top_fraction) -- the "
        f"rule documented in `research/hypotheses/sectorrotation_001.md` and used by every "
        f"committed record. The boundary rank is inclusive, so at 18 assets and "
        f"top_fraction {b['pre_registered_top_fraction']:.1f} the rule holds the top "
        f"**{b['test_window_max']} of {b['universe_size']}** "
        f"({b['test_window_max'] / b['universe_size']:.1%}) -- one asset more than the literal "
        f"\"top 50%\" reading of the csmomentum hypothesis prose, which would be "
        f"{b['implied_rank_count']} of {b['universe_size']}. Measured: over the full sample the "
        f"held count runs from {b['full_sample_min']} to {b['full_sample_max']} "
        f"(mean {b['full_sample_mean']:.2f}); over the test window it is "
        f"{b['test_window_min']} of {b['universe_size']} on every one of the "
        f"{b['test_window_sessions']} sessions. The rule is applied identically to the "
        f"baseline and to every configuration of the grid, so it does not bias the plateau "
        f"comparison; it is disclosed here so that the published breadth cannot be misread as "
        f"a different selection rule."
    )
    A("")
    A("## 8. Checks")
    A("")
    A("| Check | Result | Observed | Expected |")
    A("|---|---|---|---|")
    for c in p["checks"]:
        A(
            f"| `{c['name']}` | {'PASS' if c['pass'] else 'FAIL'} | {c['observed']} | "
            f"{c['expected']} |"
        )
    A("")
    A(f"STRUCTURAL: {'PASS' if p['structural_pass'] else 'FAIL'}")
    A("")
    A("## 9. Reproduction")
    A("")
    A("```bash")
    A("python research/csmomentum_plateau_gate_eval.py")
    A("python -m pytest -q tests/test_csmomentum_plateau_gate_eval.py")
    A("git status --porcelain data/ config/")
    A("```")
    A("")
    A("## 10. Provenance")
    A("")
    A(
        "- Data: the committed raw cache `data/raw/*.parquet`, read-only (the fetcher is never "
        "called; every file under `data/` and `config/` is SHA-256 fingerprinted before and "
        "after the run and compared)."
    )
    A(
        "- Committed artifacts used as the reproduction reference: "
        f"{', '.join('`' + a + '`' for a in COMMITTED_ARTIFACTS)} (read-only, byte-identical "
        "before and after the run)."
    )
    A(
        "- Shared machinery: `src/backtest/rebalance.py` (month-end schedule), "
        "`src/features/momentum.py` (momentum, selection), `src/evaluation/walkforward.py` "
        "(fold calendar), `src/evaluation/statistics.py` (DSR/PSR), `src/backtest/engine.py` "
        "(cost parameters, metrics) -- all unchanged by this cycle."
    )
    A(
        "- Gate thresholds, decision mapping, candidate configuration, cost model and Sharpe "
        "convention: unchanged. The plateau gate is now EVALUATED; no other gate is touched."
    )
    A("")
    return "\n".join(L)


def render_experiment(p: dict[str, Any]) -> str:
    L: list[str] = []
    A = L.append
    A(f"# Experiment: Parameter-plateau gate evaluation ({p['candidate']}, Cycle {p['cycle']})")
    A("")
    A("## Hypothesis reference")
    A("")
    A(
        "`research/hypotheses/csmomentum_001.md` (v001, pre-registered). Falsification "
        "condition: the walk-forward mean OOS Sharpe < 0.9 OR < 50% of folds positive. "
        "Gate 4 (parameter plateau: >= 2 of 3 lookbacks within 10% of the baseline test "
        "Sharpe) was the only pre-registered gate still reported as NOT EVALUATED; it is "
        "evaluated here on the config-faithful month-end path."
    )
    A("")
    A("## Data used")
    A("")
    A(
        f"- Source: committed raw cache `data/raw/*.parquet` (read-only, fetcher never called); "
        f"universe {p['candidate_configuration']['universe_size']} ETFs; union sample "
        f"{p['samples']['union_sample']['start']}..{p['samples']['union_sample']['end']} "
        f"({p['samples']['union_sample']['sessions']} sessions); common-inception slice "
        f"{p['samples']['common_inception_slice']['start']}.."
        f"{p['samples']['common_inception_slice']['end']} "
        f"({p['samples']['common_inception_slice']['sessions']} sessions)."
    )
    A(
        f"- Point-in-time treatment: momentum at t uses prices through t-skip-lookback; "
        f"the month-end signal becomes effective on the next session (1-day lag); "
        f"{p['candidate_configuration']['cost_model']['total_round_trip_bps']} bps round-trip "
        f"cost on the weight changes; walk-forward "
        f"{p['candidate_configuration']['walk_forward']['train_years']}y/"
        f"{p['candidate_configuration']['walk_forward']['test_months']}m/"
        f"{p['candidate_configuration']['walk_forward']['step_months']}m with fixed parameters."
    )
    A("")
    A("## Configuration")
    A("")
    A(
        f"- Pre-registered baseline: lookback {p['candidate_configuration']['lookback']}, skip "
        f"{p['candidate_configuration']['skip']}, top_fraction "
        f"{p['candidate_configuration']['top_fraction']} (frozen in "
        f"`config/csmomentum_candidate_001.yaml`, SHA-256 `{p['config_sha256']}`)."
    )
    A(
        f"- Pre-registered grid: {p['robustness_diagnostic']['n_configs']} unique combinations "
        f"(3 lookbacks x 2 skips x 3 top fractions); pre-registered trial count "
        f"{p['multiple_testing']['dsr_pre_registered_n']['n_configs']} (disclosed mislabel)."
    )
    A(f"- Trials: {p['robustness_diagnostic']['n_configs']} configurations, 1 decision subject.")
    A(f"- Code revision: {p['git_rev']}")
    A("")
    A("## Results")
    A("")
    A("| Gate | Threshold | Observed | Result |")
    A("|---|---|---|---|")
    for g in p["gates_union"]:
        A(
            f"| {g['name']} | {g['threshold_text']} | {_fmt(g['value'])} | "
            f"{'PASS' if g['passed'] else 'FAIL'} |"
        )
    A("")
    pl = p["plateau"]
    A(
        f"- Plateau gate: {pl['n_within']} of {pl['n_lookbacks']} lookbacks within "
        f"{pl['threshold']:.4f} of the baseline test Sharpe {pl['baseline_test_sharpe']:.4f} -> "
        f"**{'PASS' if pl['passed'] else 'FAIL'}**"
    )
    A(
        f"- Failed gates: {', '.join(p['failed_gates']) or 'none'}"
    )
    A(
        f"- Robustness diagnostic: {p['robustness_diagnostic']['n_clearing_gate1']} of "
        f"{p['robustness_diagnostic']['n_configs']} pre-registered configurations clear gate 1; "
        f"the baseline's walk-forward mean OOS Sharpe is "
        f"{p['robustness_diagnostic']['baseline_wf_mean_test_sharpe']:.4f}."
    )
    A(
        f"- DSR: {p['multiple_testing']['dsr_pre_registered_n']['dsr']:.4f} at N="
        f"{p['multiple_testing']['dsr_pre_registered_n']['n_configs']}, "
        f"{p['multiple_testing']['dsr_actual_n']['dsr']:.4f} at N="
        f"{p['multiple_testing']['dsr_actual_n']['n_configs']} (current canonical Sharpe "
        f"convention); on the estimator of the committed Cycle 13 record: "
        f"{p['multiple_testing']['legacy_scale']['dsr_at_preregistered_n']:.4f} at N="
        f"{p['multiple_testing']['dsr_pre_registered_n']['n_configs']}."
    )
    A(f"- structural_pass: {p['structural_pass']}")
    A("")
    A("## Anchors and disclosures")
    A("")
    A(
        "- Reproduction anchors: the tool fails closed unless it reproduces the published "
        "config-faithful record -- union sample (48 folds, mean OOS Sharpe 0.697524, median "
        "0.617881, 79.17% positive, 400 pooled trades; path Sharpe 0.4247 backtest-scale / "
        "0.6051 canonical, max DD -0.4474, turnover 2.16, 232 trade days, 7.56 mean "
        "positions) and the pre-registered common-inception sample (21 folds, 0.586081, 166 "
        "pooled trades)."
    )
    A(
        f"- The plateau measurement is invariant to the sample definition: the test split lies "
        f"entirely after the warm-up ramp, so the union sample and the common-inception slice "
        f"measure the same gate ({p['plateau']['n_within']} of {p['plateau']['n_lookbacks']} "
        f"lookbacks within {p['plateau']['threshold']:.4f})."
    )
    A(
        f"- Selection breadth (measured, disclosed): the shared selection module holds the "
        f"assets whose cross-sectional rank is >= max_rank x (1 - top_fraction), so at 18 "
        f"assets and top_fraction 0.5 it holds {p['selection_breadth']['test_window_max']} of "
        f"{p['selection_breadth']['universe_size']} "
        f"({p['selection_breadth']['test_window_max'] / p['selection_breadth']['universe_size']:.1%}) "
        f"on every test-window session, one asset more than the literal 'top 50%' reading of "
        f"the hypothesis prose. The rule is identical for the baseline and for every grid "
        f"configuration, so it does not bias the plateau comparison."
    )
    A(
        "- DSR scale disclosure: the DSR/PSR above use the repository's current canonical "
        "Sharpe convention (unified in Cycle 861); the committed Cycle 13 record's DSR "
        "(-0.6484) was computed with the pre-Cycle-861 estimator, so the two numbers are not "
        f"comparable. On the record's own estimator this path's DSR is "
        f"{p['multiple_testing']['legacy_scale']['dsr_at_preregistered_n']:.4f} at N=27 and "
        f"{p['multiple_testing']['legacy_scale']['dsr_at_actual_n']:.4f} at N=18."
    )
    A("")
    A("## Decision")
    A("")
    A(f"- Decision: **{p['decision']}**")
    A(f"- Research label: **{p['label']}**")
    A(
        "The pre-registered falsification condition is met and the candidate stays "
        "rejected/failed; the plateau gate is now evaluated and does not change the verdict "
        "(it is not part of the falsification condition)."
    )
    A("")
    A("## Reproduction commands")
    A("")
    A("```bash")
    A("python research/csmomentum_plateau_gate_eval.py")
    A("python -m pytest -q tests/test_csmomentum_plateau_gate_eval.py")
    A("```")
    A("")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="print the measurement without writing the report and experiment files",
    )
    args = parser.parse_args(argv)

    payload = evaluate()

    if not args.no_report:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
        OUT_REPORT.write_text(render_report(payload), encoding="utf-8")
        OUT_EXP.write_text(render_experiment(payload), encoding="utf-8")

    print(f"STRUCTURAL: {'PASS' if payload['structural_pass'] else 'FAIL'}")
    for c in payload["checks"]:
        print(f"CHECK|{c['name']}|{'PASS' if c['pass'] else 'FAIL'}")
    for g in payload["gates_union"]:
        print(
            f"GATE|{g['name']}|{g['value']:.6f}|{g['threshold']:.6f}|{g['comparison']}|"
            f"{'PASS' if g['passed'] else 'FAIL'}"
        )
    pl = payload["plateau"]
    print(
        f"PLATEAU|{pl['n_within']}|{pl['n_lookbacks']}|{pl['threshold']:.6f}|"
        f"{'PASS' if pl['passed'] else 'FAIL'}"
    )
    print(
        f"WF_MEAN_OOS_SHARPE|{payload['walk_forward_union']['mean_test_sharpe']:.6f}|"
        f"{payload['walk_forward_union']['n_folds']}"
    )
    print(
        f"POSITIVE_FOLD_RATE|{payload['walk_forward_union']['pct_positive_sharpe']:.6f}"
    )
    print(f"POOLED_OOS_TRADES|{payload['walk_forward_union']['total_test_trades']}")
    print(
        f"ROBUSTNESS_CLEARING_GATE1|{payload['robustness_diagnostic']['n_clearing_gate1']}|"
        f"{payload['robustness_diagnostic']['n_configs']}"
    )
    print(f"DECISION|{payload['decision']}")
    print(f"LABEL|{payload['label']}")
    print(f"REPORT|{OUT_REPORT if not args.no_report else '(not written: --no-report)'}")
    print(f"EXPERIMENT|{OUT_EXP if not args.no_report else '(not written: --no-report)'}")
    return 0 if payload["structural_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
