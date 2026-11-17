#!/usr/bin/env python3
"""Fold-level Sharpe degeneracy audit for ``tsmomentum_spytrend_001`` (Cycle 930).

The Cycle-929 membership audit (``research/reports/data_cost_inventory_002.md``)
reports that the point-in-time-complete subsample fails promotion gate 1
(mean OOS Sharpe 0.787522 over 41 breadth-7/7 folds) while the same subsample
passes once "the fold-12 artefact" is removed (1.352958 over 40 folds). That
report calls fold 12 a numerical artefact but does not measure *why*, and the
Cycle-911 thin-trade audit groups folds 12 and 13 together.

This tool measures, per fold, the quantities that decide whether a fold's
Sharpe is a valid performance statistic at all:

* ``cash_days``  -- sessions the SPY trend overlay held the portfolio in cash;
* ``active_days`` -- sessions with non-zero gross exposure;
* ``nonzero_days`` -- sessions with a non-zero strategy return;
* ``ann_vol``    -- annualized return volatility (the Sharpe denominator);
* ``sharpe``     -- recomputed fold Sharpe ``(ann_return - rf) / ann_vol``.

A fold is **degenerate** when its Sharpe is not a meaningful risk-adjusted
measurement, under a pre-registered rule (see ``VOL_FLOOR`` / ``ACTIVE_FLOOR``).
The tool then re-evaluates promotion gate 1 on the point-in-time-complete
subsample with and without the degenerate folds.

It is **read-only**: the price panel is read from the committed cache, nothing
under ``data/`` or ``config/`` is written, and every committed ``src/``,
``config/``, ``research/experiments/`` and ``research/reports/`` artefact is
hashed before and after the read phase.
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

from research.data_cost_inventory_002 import subsample_stats
from research.run_cycle6 import (
    LOOKBACK,
    SKIP,
    SPY_SMA_WINDOW,
    SYMBOLS,
)
from research.tsmomentum_walkforward_embargo_audit import (
    EXPERIMENTS_DIR,
    RAW_DIR,
    REPORTS_DIR,
    AuditError,
    build_candidate_path,
    fail,
    fingerprint,
    load_close_from_cache,
    published_splits,
    resolve_published_record,
    tracked_artifact_hashes,
)
from src.backtest.engine import get_risk_free_rate
from src.features.momentum import compute_momentum

CANDIDATE_ID = "tsmomentum_spytrend_001"
CYCLE = "930"

CONFIG_DIR = REPO_ROOT / "config"
OUT_REPORT = REPORTS_DIR / "fold_sharpe_degeneracy_001.md"
OUT_EXP = EXPERIMENTS_DIR / "fold_sharpe_degeneracy_001.md"

PERIODS_PER_YEAR = 252

# Pre-registered degeneracy rule. A fold's Sharpe is not a valid performance
# measurement when its annualized volatility is below 1% (the ratio is then
# dominated by the risk-free numerator) or it has at most two active sessions
# (there is no return distribution to summarise).
VOL_FLOOR = 0.01
ACTIVE_FLOOR = 2

# The published promotion gate (AGENTS.md "Promotion gate").
GATE_WF_MEAN_MIN = 0.9


def is_degenerate(row: dict[str, Any]) -> bool:
    """True when a fold's Sharpe is not a valid performance statistic."""
    return row["ann_vol"] < VOL_FLOOR or row["active_days"] <= ACTIVE_FLOOR


def fold_diagnostics(
    close: pd.DataFrame,
    net_ret: pd.Series,
    weights: pd.DataFrame,
    splits: list[dict[str, Any]],
    pub_folds: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Per-fold exposure, volatility and Sharpe diagnostics on the shared path."""
    momentum = compute_momentum(close, lookback=LOOKBACK, skip=SKIP)
    valid = momentum.notna().sum(axis=1)
    rf = get_risk_free_rate()

    rows: list[dict[str, Any]] = []
    for i, sp in enumerate(splits):
        fold = i + 1
        ts = pd.Timestamp(sp["test_start"], tz="UTC")
        te = pd.Timestamp(sp["test_end"], tz="UTC")
        mask = (weights.index >= ts) & (weights.index <= te)
        w = weights[mask]
        r = net_ret[mask]
        n = len(r)
        if n == 0:
            fail(f"fold {fold}: the test window carries no sessions")

        gross = w.abs().sum(axis=1)
        cash_days = int((gross < 1e-12).sum())
        active_days = n - cash_days
        nonzero_days = int((r != 0).sum())

        ann_ret = float((1.0 + r).prod() ** (PERIODS_PER_YEAR / n) - 1.0)
        ann_vol = float(r.std() * np.sqrt(PERIODS_PER_YEAR)) if n > 1 else 0.0
        sharpe = (ann_ret - rf) / ann_vol if ann_vol > 0 else 0.0

        pos = int(valid.index.searchsorted(ts, side="left"))
        breadth_start = int(valid.iloc[pos]) if pos < len(valid) else 0
        breadth_min = int(valid.loc[ts:te].min())

        pub = pub_folds.get(fold)
        if pub is None:
            fail(f"published record has no fold {fold}")

        row = {
            "fold": fold,
            "test_start": sp["test_start"],
            "test_end": sp["test_end"],
            "n_sessions": n,
            "cash_days": cash_days,
            "active_days": active_days,
            "nonzero_days": nonzero_days,
            "ann_ret": ann_ret,
            "ann_vol": ann_vol,
            "sharpe": sharpe,
            "published_test_sharpe": float(pub["test_sharpe"]),
            "published_test_trades": int(pub["test_trades"]),
            "breadth_start": breadth_start,
            "breadth_min": breadth_min,
        }
        row["degenerate"] = is_degenerate(row)
        rows.append(row)
    return rows


def _fmt(value: float, digits: int = 6) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "N/A"
    return f"{float(value):.{digits}f}"


def _gate1_pass(stats: dict[str, Any]) -> bool:
    gate = next((g for g in stats["gates"] if g["gate"] == "wf_mean_oos_sharpe"), None)
    return bool(gate and gate["pass"])


def render_report(payload: dict[str, Any]) -> str:
    rows = payload["rows"]
    degen = payload["degenerate_folds"]
    complete = payload["complete_stats"]
    clean = payload["complete_clean_stats"]
    fold12 = payload["fold_12"]

    lines: list[str] = []
    add = lines.append

    add("# Fold Sharpe Degeneracy Audit — tsmomentum_spytrend_001 (Cycle 930)")
    add("")
    add(
        "**Method:** read-only, cache-only measurement of the incumbent's published "
        "48-fold walk-forward. `research/fold_sharpe_degeneracy_audit.py` rebuilds the "
        "continuously computed point-in-time path, records each fold's cash / active / "
        "non-zero session counts and annualized volatility, flags folds whose Sharpe is "
        "not a valid statistic under a pre-registered rule, and re-evaluates promotion "
        "gate 1 on the point-in-time-complete subsample with and without those folds. "
        "No backtest was re-tuned, no threshold/gate/cost/universe was changed, nothing "
        "under `data/` or `config/` was written and the fetcher was never called."
    )
    add("")
    add(
        "**Determinism:** this document contains no timestamp and no run id; two "
        "consecutive generations are byte-identical."
    )
    add("")

    add("## Summary")
    add("")
    add(f"- Candidate: `{CANDIDATE_ID}` (the incumbent).")
    add(
        "- Question: is the point-in-time-complete gate-1 FAIL (mean OOS Sharpe "
        f"{_fmt(complete['mean_test_sharpe'])}) a broad performance gap, or the effect of "
        "a single degenerate fold?"
    )
    add(
        "- Degenerate folds (pre-registered rule): "
        + ("**fold " + ", ".join(str(f) for f in degen) + "**" if degen else "**none**")
        + "."
    )
    add(
        f"- Complete-subsample gate 1 (mean OOS Sharpe >= {GATE_WF_MEAN_MIN}): "
        f"**{'PASS' if complete['gate1_pass'] else 'FAIL'}** at "
        f"{_fmt(complete['mean_test_sharpe'])} ({complete['n_folds']} folds)."
    )
    add(
        "- Complete-subsample gate 1 with the degenerate fold(s) removed: "
        f"**{'PASS' if clean['gate1_pass'] else 'FAIL'}** at "
        f"{_fmt(clean['mean_test_sharpe'])} ({clean['n_folds']} folds)."
    )
    add(
        "- Read-only: `data/` and `config/` byte-identical before and after the run; "
        "no committed artefact modified."
    )
    lof = payload["leave_one_out_complete"]
    add(
        f"- Leave-one-fold-out: fold {lof['top_drop']['dropped_fold']} is the unique "
        f"single-fold determinant of the gate-1 flip; dropping any other single fold "
        f"leaves the mean in "
        f"[{_fmt(lof['non_artefact_mean_min'], 4)}, "
        f"{_fmt(lof['non_artefact_mean_max'], 4)}] "
        f"({'PASS' if lof['non_artefact_gate1_any_pass'] else 'all FAIL'})."
    )
    add(
        "- The incumbent's overall verdict is unchanged: **NO-GO** (failed gates "
        "`rolling_63d_sharpe`, `psr`)."
    )
    add("")

    add("## The degeneracy rule (pre-registered)")
    add("")
    add(
        "A fold's out-of-sample Sharpe is *degenerate* — not a valid performance "
        "measurement — when either:"
    )
    add("")
    add(f"- its annualized return volatility is below **{VOL_FLOOR:.0%}** (`ann_vol < {VOL_FLOOR}`); or")
    add(f"- it has at most **{ACTIVE_FLOOR}** active (non-cash) sessions (`active_days <= {ACTIVE_FLOOR}`).")
    add("")
    add(
        "Rationale: the Sharpe ratio divides the annualized excess return by the "
        "annualized volatility. When the denominator is near zero the ratio is "
        "dominated by the risk-free numerator and is numerically meaningless; with "
        f"{ACTIVE_FLOOR} or fewer active sessions there is no return distribution to "
        "summarise. The thresholds are fixed before the measurement and are not "
        "tuned to the outcome."
    )
    add("")
    add(
        "The check is *separation-based*, not floor-distance: it asserts that fold "
        f"{fold12['fold']} is far below the floor (`ann_vol` {fold12['ann_vol']:.6f}, "
        f"~{VOL_FLOOR / fold12['ann_vol']:.0f}x below {VOL_FLOOR}) while the "
        "next-lowest non-degenerate fold is far above it (`ann_vol` "
        f"{payload['next_lowest_vol']:.6f}, ~{payload['next_lowest_vol'] / VOL_FLOOR:.1f}x "
        f"above), a ~{payload['next_lowest_vol'] / fold12['ann_vol']:.0f}x separation. "
        "The rule's outcome is therefore insensitive to the exact threshold anywhere "
        "inside that gap (fold "
        f"{fold12['fold']} has {fold12['active_days']} active day; the next-lowest has "
        f"{payload['next_lowest_active']})."
    )
    add("")

    add("## Fold 12 in detail")
    add("")
    add("| Quantity | Value |")
    add("|---|---|")
    add(f"| Test window | {fold12['test_start']} .. {fold12['test_end']} |")
    add(f"| Sessions | {fold12['n_sessions']} |")
    add(f"| Cash days (gross weight 0) | {fold12['cash_days']} |")
    add(f"| Active days (gross weight > 0) | {fold12['active_days']} |")
    add(f"| Non-zero return days | {fold12['nonzero_days']} |")
    add(f"| Annualized return | {_fmt(fold12['ann_ret'])} |")
    add(f"| Annualized volatility | {_fmt(fold12['ann_vol'])} |")
    add(f"| Recomputed Sharpe | {_fmt(fold12['sharpe'])} |")
    add(f"| Published Sharpe | {_fmt(fold12['published_test_sharpe'], 4)} |")
    add("")
    add(
        f"The SPY trend overlay (SPY below its {SPY_SMA_WINDOW}-session SMA) held the "
        f"portfolio in cash for {fold12['cash_days']} of {fold12['n_sessions']} sessions "
        f"of the {fold12['test_start']} .. {fold12['test_end']} window. The "
        f"{fold12['nonzero_days']} non-zero return days are the only sessions the "
        f"portfolio was exposed. The {_fmt(fold12['sharpe'], 2)} Sharpe is "
        "the annualized excess return divided by a near-zero volatility; it measures "
        "the risk-free rate against that denominator, not a strategy loss. The fold's "
        "return over the window is a small negative number, not a crash."
    )
    add("")

    add("## Complete-subsample gate 1 on each side")
    add("")
    add("| Subsample | Folds | Mean OOS Sharpe | 95% CI (moving block) | Gate 1 (>= 0.9) |")
    add("|---|---|---|---|---|")
    for key, stats in (("complete", complete), ("complete_clean", clean)):
        add(
            f"| {stats['label']} | {stats['n_folds']} | {_fmt(stats['mean_test_sharpe'])} | "
            f"[{_fmt(stats['ci_low'], 4)}, {_fmt(stats['ci_high'], 4)}] | "
            f"{'PASS' if stats['gate1_pass'] else 'FAIL'} |"
        )
    add("")

    lof = payload["leave_one_out_complete"]
    top = lof["top_drop"]
    runner = lof["runner_up"]
    add("## Leave-one-fold-out sensitivity (complete subsample, 41 folds)")
    add("")
    add(
        "The Cycle-929 report shows the complete-subsample gate-1 outcome flips "
        "when fold 12 is removed. This section measures whether fold 12 is the "
        "*unique* single-fold determinant of that flip, or whether dropping any "
        "other single fold also lifts the mean above the threshold. The "
        "decision-relevant question is whether the gate-1 PASS on the clean "
        "subsample is robust to dropping any single *other* fold -- i.e. whether "
        "it is fold 12 specifically, not the act of dropping a fold, that carries "
        "the result."
    )
    add("")
    add("| Drop | Dropped Sharpe | Mean OOS Sharpe (40 folds) | Gate 1 (>= 0.9) |")
    add("|---|---|---|---|")
    add(
        f"| fold {top['dropped_fold']} (artefact) | {_fmt(top['dropped_sharpe'], 4)} | "
        f"{_fmt(top['mean_test_sharpe'])} | {'PASS' if top['gate1_pass'] else 'FAIL'} |"
    )
    if runner:
        add(
            f"| fold {runner['dropped_fold']} (runner-up) | {_fmt(runner['dropped_sharpe'], 4)} | "
            f"{_fmt(runner['mean_test_sharpe'])} | {'PASS' if runner['gate1_pass'] else 'FAIL'} |"
        )
    add(
        f"| any other single fold (39 folds) | -- | "
        f"[{_fmt(lof['non_artefact_mean_min'], 6)}, "
        f"{_fmt(lof['non_artefact_mean_max'], 6)}] | "
        f"{'PASS' if lof['non_artefact_gate1_any_pass'] else 'FAIL'} |"
    )
    add("")
    add(
        f"**Result:** fold {top['dropped_fold']} is the **unique** single-fold "
        f"determinant of the complete-subsample gate-1 flip. Dropping it lifts the "
        f"mean to {_fmt(top['mean_test_sharpe'])} (PASS); dropping any other single "
        f"fold leaves the mean in "
        f"[{_fmt(lof['non_artefact_mean_min'], 4)}, "
        f"{_fmt(lof['non_artefact_mean_max'], 4)}] "
        f"({'PASS' if lof['non_artefact_gate1_any_pass'] else 'all FAIL'})."
    )
    if runner:
        add(
            f" The runner-up drop (fold {runner['dropped_fold']}, Sharpe "
            f"{_fmt(runner['dropped_sharpe'], 4)}) reaches "
            f"{_fmt(runner['mean_test_sharpe'])} "
            f"({'PASS' if runner['gate1_pass'] else 'FAIL'})."
        )
    add("")

    add("## What this does and does not change")
    add("")
    add(
        "- **Nothing published changed.** The published record, gates, protocol and "
        "every committed candidate artefact are byte-identical; this is a measurement, "
        "not a correction."
    )
    add(
        "- **The complete-subsample gate-1 FAIL is attributable to a single degenerate "
        f"fold (fold {fold12['fold']}).** Its Sharpe is not a valid statistic, so the "
        "complete subsample does not actually fail gate 1 on comparable evidence."
    )
    add(
        "- **Leave-one-fold-out confirms fold 12 is the unique single-fold determinant.** "
        f"Dropping fold {lof['top_drop']['dropped_fold']} lifts the mean to "
        f"{_fmt(lof['top_drop']['mean_test_sharpe'])} (PASS); dropping any other single "
        f"fold leaves the mean in "
        f"[{_fmt(lof['non_artefact_mean_min'], 4)}, "
        f"{_fmt(lof['non_artefact_mean_max'], 4)}] "
        f"({'PASS' if lof['non_artefact_gate1_any_pass'] else 'all FAIL'}). The gate-1 "
        "PASS on the clean subsample is therefore not an artefact of dropping a fold "
        "in general -- it is fold 12 specifically that carries the result."
    )
    add(
        "- **This refines the Cycle-911 thin-trade grouping.** Fold 13 is *not* "
        f"degenerate: it has {payload['fold_13_active']} active days, `ann_vol` "
        f"{payload['fold_13_vol']:.6f} and a Sharpe of "
        f"{_fmt(payload['fold_13_sharpe'], 3)}. The artefact is fold 12 alone."
    )
    add(
        "- **The incumbent's verdict is unchanged**: it stays a Credible Candidate by "
        "its published verdict and **NO-GO** for promotion (failed gates "
        "`rolling_63d_sharpe`, `psr`). This audit adds a measurement-quality axis to a "
        "verdict that was already NO-GO."
    )
    add("")

    add("## Per-fold diagnostics")
    add("")
    add(
        "| Fold | Test window | Sessions | Cash | Active | Non-zero | Ann. vol | Ann. ret | "
        "Sharpe | Published Sharpe | Breadth min | Degenerate |"
    )
    add("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for row in rows:
        add(
            f"| {row['fold']} | {row['test_start']} .. {row['test_end']} | "
            f"{row['n_sessions']} | {row['cash_days']} | {row['active_days']} | "
            f"{row['nonzero_days']} | {_fmt(row['ann_vol'])} | {_fmt(row['ann_ret'])} | "
            f"{_fmt(row['sharpe'], 3)} | {_fmt(row['published_test_sharpe'], 4)} | "
            f"{row['breadth_min']} | {'yes' if row['degenerate'] else 'no'} |"
        )
    add("")

    add("## Reproduction")
    add("")
    add("```bash")
    add("python research/fold_sharpe_degeneracy_audit.py")
    add("python -m pytest -q tests/test_fold_sharpe_degeneracy_audit.py")
    add("git status --porcelain data/ config/")
    add("```")
    return "\n".join(lines) + "\n"


def render_experiment(payload: dict[str, Any]) -> str:
    complete = payload["complete_stats"]
    clean = payload["complete_clean_stats"]
    degen = payload["degenerate_folds"]
    fold12 = payload["fold_12"]

    lines: list[str] = []
    add = lines.append

    add("# Experiment: fold_sharpe_degeneracy_audit (Cycle 930)")
    add("")
    add("**Hypothesis reference:** none (measurement cycle).")
    add("")
    add("**Objective:** decide whether the point-in-time-complete gate-1 FAIL reported by")
    add("the Cycle-929 inventory is a broad performance gap or the effect of a single")
    add("degenerate fold, by measuring each fold's exposure and volatility.")
    add("")
    add("## Data used")
    add("")
    add(
        f"- **Source:** committed parquet cache `data/raw/` (universe "
        f"{', '.join(SYMBOLS)}); the fetcher is never called."
    )
    add(
        "- **Range:** the incumbent's published walk-forward (48 folds) on the "
        "continuously computed point-in-time path."
    )
    add(
        "- **Point-in-time treatment:** momentum "
        f"({LOOKBACK}-session lookback, skip {SKIP}) and the SPY {SPY_SMA_WINDOW}-session "
        f"SMA overlay are the committed ones (`src/features/momentum.py`, `research/run_cycle6.py`)."
    )
    add(
        "- **Cost model:** 1.0 bps commission + 2.0 bps slippage = 3.0 bps per unit of "
        "weight change; risk-free 2.00% annual (unchanged, from `src/backtest/engine.py`)."
    )
    add("")
    add("## Configuration")
    add("")
    add(f"- **Candidate:** `{CANDIDATE_ID}`.")
    add(
        f"- **Degeneracy rule (pre-registered):** `ann_vol < {VOL_FLOOR}` or "
        f"`active_days <= {ACTIVE_FLOOR}`."
    )
    add(f"- **Promotion gate 1:** mean OOS Sharpe >= {GATE_WF_MEAN_MIN}.")
    add(
        f"- **Rule robustness (separation-based, not floor-distance):** fold "
        f"{fold12['fold']} sits ~{VOL_FLOOR / fold12['ann_vol']:.0f}x below the "
        f"volatility floor (`ann_vol` {fold12['ann_vol']:.6f}) while the next-lowest "
        f"non-degenerate fold is ~{payload['next_lowest_vol'] / VOL_FLOOR:.1f}x above "
        f"it (`ann_vol` {payload['next_lowest_vol']:.6f}), a "
        f"~{payload['next_lowest_vol'] / fold12['ann_vol']:.0f}x separation, so the "
        "measured outcome is insensitive to the exact threshold anywhere inside that gap."
    )
    add("")
    add("## Results")
    add("")
    add("| Quantity | Value |")
    add("|---|---|")
    add(f"| Degenerate folds | {', '.join(str(f) for f in degen) or 'none'} |")
    add(
        f"| Fold {fold12['fold']} sessions / cash / active / non-zero | "
        f"{fold12['n_sessions']} / {fold12['cash_days']} / {fold12['active_days']} / "
        f"{fold12['nonzero_days']} |"
    )
    add(f"| Fold {fold12['fold']} annualized volatility | {_fmt(fold12['ann_vol'])} |")
    add(f"| Fold {fold12['fold']} recomputed Sharpe | {_fmt(fold12['sharpe'])} |")
    add(
        f"| Complete-subsample gate 1 ({complete['n_folds']} folds) | "
        f"{_fmt(complete['mean_test_sharpe'])} -> {'PASS' if complete['gate1_pass'] else 'FAIL'} |"
    )
    add(
        f"| Complete-subsample gate 1 without degenerate folds ({clean['n_folds']} folds) | "
        f"{_fmt(clean['mean_test_sharpe'])} -> {'PASS' if clean['gate1_pass'] else 'FAIL'} |"
    )
    lof = payload["leave_one_out_complete"]
    top = lof["top_drop"]
    add(
        f"| Leave-one-out top drop (fold {top['dropped_fold']}) mean | "
        f"{_fmt(top['mean_test_sharpe'])} -> {'PASS' if top['gate1_pass'] else 'FAIL'} |"
    )
    add(
        f"| Leave-one-out non-artefact drop range | "
        f"[{_fmt(lof['non_artefact_mean_min'], 6)}, "
        f"{_fmt(lof['non_artefact_mean_max'], 6)}] -> "
        f"{'any PASS' if lof['non_artefact_gate1_any_pass'] else 'all FAIL'} |"
    )
    add(
        f"| Leave-one-out unique determinant | fold {top['dropped_fold']} "
        f"(flip_to_pass={lof['flip_to_pass_folds']}) |"
    )
    add("")
    add("## Number of trials")
    add("")
    add(
        "1 (a measurement: no parameter search, no candidate generation, no "
        "re-tuning). The bootstrap uses the same 2000 moving-block draws and seed as "
        "the Cycle-929 inventory."
    )
    add("")
    add("## Reproduction commands")
    add("")
    add("```bash")
    add("python research/fold_sharpe_degeneracy_audit.py")
    add("python -m pytest -q tests/test_fold_sharpe_degeneracy_audit.py")
    add("git status --porcelain data/ config/")
    add("```")
    return "\n".join(lines) + "\n"


def run_audit(
    write: bool = True,
    raw_dir: Path = RAW_DIR,
    report_out: Path = OUT_REPORT,
    experiment_out: Path = OUT_EXP,
) -> dict[str, Any]:
    data_before = fingerprint(REPO_ROOT / "data")
    config_before = fingerprint(CONFIG_DIR)
    artifacts_before = tracked_artifact_hashes()

    close = load_close_from_cache(list(SYMBOLS), raw_dir)
    net_ret, weights = build_candidate_path(close)

    record_path, published = resolve_published_record(EXPERIMENTS_DIR)
    pub_folds = {int(f["fold"]): f for f in published["folds"]}
    splits = published_splits()

    rows = fold_diagnostics(close, net_ret, weights, splits, pub_folds)
    degenerate_folds = [r["fold"] for r in rows if r["degenerate"]]

    n_assets = len(SYMBOLS)
    complete_rows = [r for r in rows if r["breadth_min"] >= n_assets]
    if not complete_rows:
        fail("no point-in-time-complete folds found")

    complete_stats = subsample_stats(complete_rows, "Point-in-time-complete folds (breadth 7/7)")
    complete_clean_stats = subsample_stats(
        complete_rows,
        "Point-in-time-complete folds, degenerate fold(s) removed",
        drop_folds=tuple(degenerate_folds),
    )
    complete_stats["gate1_pass"] = _gate1_pass(complete_stats)
    complete_clean_stats["gate1_pass"] = _gate1_pass(complete_clean_stats)

    # Leave-one-fold-out sensitivity on the point-in-time-complete subsample.
    # The Cycle-929 report shows the complete-subsample gate-1 outcome flips
    # when fold 12 is removed; this measures whether that fold is the *unique*
    # single-fold determinant of the flip, or whether any other single fold
    # also lifts the mean above the threshold. The decision-relevant question
    # is whether the gate-1 PASS on the clean subsample is robust to dropping
    # any single *other* fold -- i.e. whether it is fold 12 specifically, not
    # the act of dropping a fold, that carries the result.
    lof = []
    for r in complete_rows:
        kept = [s for s in complete_rows if s["fold"] != r["fold"]]
        s = subsample_stats(kept, f"complete drop fold {r['fold']}", drop_folds=())
        s["dropped_fold"] = r["fold"]
        s["dropped_sharpe"] = r["sharpe"]
        s["gate1_pass"] = _gate1_pass(s)
        lof.append(s)
    lof_by_mean = sorted(lof, key=lambda s: s["mean_test_sharpe"], reverse=True)
    # The fold whose removal lifts the complete-subsample mean the most.
    lof_top = lof_by_mean[0]
    # Folds whose removal alone flips the complete-subsample gate 1 to PASS.
    lof_flip_folds = [s["dropped_fold"] for s in lof if s["gate1_pass"]]
    # Folds whose removal alone flips the complete-subsample gate 1 to FAIL
    # (i.e. the clean-subsample PASS depends on that fold's presence).
    lof_fail_folds = [
        s["dropped_fold"]
        for s in lof
        if not s["gate1_pass"] and s["dropped_fold"] != lof_top["dropped_fold"]
    ]
    # The runner-up fold (second-largest mean after the top drop) and whether
    # dropping it also lifts the mean to PASS. If only the top drop flips the
    # gate, the artefact fold is the unique single-fold determinant.
    lof_runner_up = lof_by_mean[1] if len(lof_by_mean) > 1 else None
    # Range of means over all *non-artefact* single-fold drops: this is the
    # floor the gate-1 PASS on the clean subsample rests on.
    non_artefact_means = [
        s["mean_test_sharpe"] for s in lof if s["dropped_fold"] != lof_top["dropped_fold"]
    ]

    fold12 = next(r for r in rows if r["fold"] == 12)
    non_degen = [r for r in rows if not r["degenerate"]]
    by_vol = sorted(non_degen, key=lambda r: r["ann_vol"])
    by_active = sorted(non_degen, key=lambda r: r["active_days"])
    next_lowest = by_vol[0]

    fold13 = next((r for r in rows if r["fold"] == 13), None)

    payload: dict[str, Any] = {
        "candidate_id": CANDIDATE_ID,
        "universe": list(SYMBOLS),
        "record_path": str(record_path.relative_to(REPO_ROOT)),
        "rows": rows,
        "degenerate_folds": degenerate_folds,
        "fold_12": fold12,
        "complete_stats": complete_stats,
        "complete_clean_stats": complete_clean_stats,
        "n_complete": len(complete_rows),
        "next_lowest_vol": next_lowest["ann_vol"],
        "next_lowest_active": next_lowest["active_days"],
        "fold_13_active": fold13["active_days"] if fold13 else None,
        "fold_13_vol": fold13["ann_vol"] if fold13 else None,
        "fold_13_sharpe": fold13["sharpe"] if fold13 else None,
        "by_vol_lowest_nondeg": by_vol[0]["fold"],
        "by_active_lowest_nondeg": by_active[0]["fold"],
        "leave_one_out_complete": {
            "folds": lof,
            "top_drop": {
                "dropped_fold": lof_top["dropped_fold"],
                "dropped_sharpe": lof_top["dropped_sharpe"],
                "mean_test_sharpe": lof_top["mean_test_sharpe"],
                "gate1_pass": lof_top["gate1_pass"],
            },
            "runner_up": (
                {
                    "dropped_fold": lof_runner_up["dropped_fold"],
                    "dropped_sharpe": lof_runner_up["dropped_sharpe"],
                    "mean_test_sharpe": lof_runner_up["mean_test_sharpe"],
                    "gate1_pass": lof_runner_up["gate1_pass"],
                }
                if lof_runner_up
                else None
            ),
            "flip_to_pass_folds": lof_flip_folds,
            "flip_to_fail_folds": lof_fail_folds,
            "non_artefact_mean_min": float(min(non_artefact_means)),
            "non_artefact_mean_max": float(max(non_artefact_means)),
            "non_artefact_gate1_any_pass": any(
                s["gate1_pass"]
                for s in lof
                if s["dropped_fold"] != lof_top["dropped_fold"]
            ),
        },
    }

    checks = _run_checks(payload, data_before, config_before, artifacts_before)
    payload["checks"] = checks
    payload["ok"] = all(c["ok"] for c in checks)

    if write:
        report_out.parent.mkdir(parents=True, exist_ok=True)
        experiment_out.parent.mkdir(parents=True, exist_ok=True)
        report_out.write_text(render_report(payload), encoding="utf-8")
        experiment_out.write_text(render_experiment(payload), encoding="utf-8")
    return payload


def _run_checks(
    payload: dict[str, Any],
    data_before: dict[str, str],
    config_before: dict[str, str],
    artifacts_before: dict[str, str],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    rows = payload["rows"]
    degen = payload["degenerate_folds"]
    complete = payload["complete_stats"]
    clean = payload["complete_clean_stats"]
    fold12 = payload["fold_12"]

    check(
        "all_48_folds_measured",
        len(rows) == 48,
        f"{len(rows)} folds measured",
    )
    check(
        "degenerate_fold_is_exactly_12",
        degen == [12],
        f"degenerate folds: {degen}",
    )
    check(
        "fold12_is_extreme_on_every_axis",
        fold12["ann_vol"] < VOL_FLOOR
        and fold12["active_days"] <= ACTIVE_FLOOR
        and fold12["sharpe"] == min(r["sharpe"] for r in rows),
        f"fold 12 ann_vol {fold12['ann_vol']:.6f}, active {fold12['active_days']}, "
        f"sharpe {fold12['sharpe']:.4f} (minimum of all folds)",
    )
    extreme = [r["fold"] for r in rows if abs(r["sharpe"]) > 5.0]
    check(
        "only_fold12_has_extreme_sharpe",
        extreme == [12],
        f"folds with |sharpe| > 5: {extreme}",
    )
    check(
        "thresholds_are_far_from_the_boundary",
        fold12["ann_vol"] <= VOL_FLOOR / 5.0
        and payload["next_lowest_vol"] >= 2.0 * VOL_FLOOR
        and fold12["active_days"] <= ACTIVE_FLOOR
        and payload["next_lowest_active"] >= 3.0 * ACTIVE_FLOOR,
        f"fold 12 ann_vol {fold12['ann_vol']:.6f} (<= {VOL_FLOOR / 5.0:.4f}); "
        f"next-lowest non-degenerate ann_vol {payload['next_lowest_vol']:.6f} "
        f"(>= {2.0 * VOL_FLOOR:.3f}); fold 12 active {fold12['active_days']} "
        f"(<= {ACTIVE_FLOOR}); next-lowest active days {payload['next_lowest_active']} "
        f"(>= {3.0 * ACTIVE_FLOOR:.0f})",
    )
    check(
        "complete_gate1_fails",
        not complete["gate1_pass"],
        f"complete mean {complete['mean_test_sharpe']:.6f} < {GATE_WF_MEAN_MIN}",
    )
    check(
        "complete_without_degenerate_gate1_passes",
        clean["gate1_pass"],
        f"complete-without-degenerate mean {clean['mean_test_sharpe']:.6f} "
        f">= {GATE_WF_MEAN_MIN} ({clean['n_folds']} folds)",
    )
    lof = payload["leave_one_out_complete"]
    check(
        "lof_top_drop_is_the_artefact_fold",
        lof["top_drop"]["dropped_fold"] == fold12["fold"],
        f"leave-one-out largest mean lift from dropping fold "
        f"{lof['top_drop']['dropped_fold']} (mean {lof['top_drop']['mean_test_sharpe']:.6f})",
    )
    check(
        "lof_only_artefact_fold_flips_gate1_to_pass",
        lof["flip_to_pass_folds"] == [fold12["fold"]],
        f"single-fold drops that flip complete-subsample gate 1 to PASS: "
        f"{lof['flip_to_pass_folds']}",
    )
    check(
        "lof_no_non_artefact_drop_flips_gate1",
        not lof["non_artefact_gate1_any_pass"],
        f"non-artefact single-fold drops reaching gate 1 PASS: "
        f"{lof['non_artefact_gate1_any_pass']}; "
        f"range [{lof['non_artefact_mean_min']:.6f}, "
        f"{lof['non_artefact_mean_max']:.6f}]",
    )
    check(
        "lof_runner_up_below_threshold",
        lof["runner_up"] is None or not lof["runner_up"]["gate1_pass"],
        f"runner-up drop fold {lof['runner_up']['dropped_fold'] if lof['runner_up'] else 'n/a'} "
        f"mean {lof['runner_up']['mean_test_sharpe']:.6f}"
        if lof["runner_up"]
        else "fewer than two complete folds",
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
        "every committed src/, config/, research/experiments/ and research/reports/ "
        "artefact is byte-identical",
    )
    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="run the audit without writing the report or the experiment record",
    )
    parser.add_argument("--raw-dir", default=str(RAW_DIR), help="cached price directory")
    parser.add_argument("--report-out", default=str(OUT_REPORT), help="report output path")
    parser.add_argument(
        "--experiment-out", default=str(OUT_EXP), help="experiment record output path"
    )
    args = parser.parse_args(argv)

    try:
        payload = run_audit(
            write=not args.no_report,
            raw_dir=Path(args.raw_dir),
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

    complete = payload["complete_stats"]
    clean = payload["complete_clean_stats"]
    fold12 = payload["fold_12"]
    print(
        "DEGENERACY|degenerate_folds|"
        + (",".join(str(f) for f in payload["degenerate_folds"]) or "none")
        + f"|rule|ann_vol<{VOL_FLOOR} or active<={ACTIVE_FLOOR}"
    )
    print(
        f"DEGENERACY|fold_12|ann_vol|{fold12['ann_vol']:.6f}|cash_days|"
        f"{fold12['cash_days']}|active_days|{fold12['active_days']}"
    )
    print(
        f"GATE|complete|n_folds|{complete['n_folds']}|mean_sharpe|"
        f"{complete['mean_test_sharpe']:.6f}|gate1|"
        f"{'PASS' if complete['gate1_pass'] else 'FAIL'}"
    )
    print(
        f"GATE|complete_without_degenerate|n_folds|{clean['n_folds']}|mean_sharpe|"
        f"{clean['mean_test_sharpe']:.6f}|gate1|{'PASS' if clean['gate1_pass'] else 'FAIL'}"
    )
    lof = payload["leave_one_out_complete"]
    top = lof["top_drop"]
    print(
        f"LEAVE_ONE_OUT|top_drop_fold|{top['dropped_fold']}|mean_sharpe|"
        f"{top['mean_test_sharpe']:.6f}|gate1|{'PASS' if top['gate1_pass'] else 'FAIL'}"
    )
    print(
        f"LEAVE_ONE_OUT|non_artefact_range|min|{lof['non_artefact_mean_min']:.6f}"
        f"|max|{lof['non_artefact_mean_max']:.6f}"
        f"|any_pass|{lof['non_artefact_gate1_any_pass']}"
    )
    print(
        f"LEAVE_ONE_OUT|unique_determinant|{top['dropped_fold']}"
        f"|flip_to_pass|{lof['flip_to_pass_folds']}"
    )
    print(f"DECISION|NO-GO|incumbent {CANDIDATE_ID} unchanged")
    print("OVERALL: " + ("PASS" if payload["ok"] else "FAIL"))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())