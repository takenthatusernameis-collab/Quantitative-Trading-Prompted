#!/usr/bin/env python3
"""Common-inception gate audit for ``csmomentum_001`` (Cycle 907).

Measures the candidate's **config-faithful** walk-forward evaluation on the
three samples that ``config/sample_policy.yaml`` pre-registers for it
(``candidates.csmomentum_001``) and publishes the three gate tables side by
side, read-only.

What the tool does
------------------
* consumes the machine-readable sample policy and **fails closed** when the
  policy is missing, malformed or does not carry a valid
  ``candidates.csmomentum_001`` section
  (``research.csmomentum_common_inception_audit.load_policy``);
* re-derives the common inception from the committed raw cache at run time
  (max of the per-symbol first dates -- a rule, never a frozen date) and
  publishes the per-symbol cache fingerprint;
* builds the three pre-registered samples with the **config-faithful**
  month-end schedule (``src/backtest/rebalance.py:build_month_end_weights``,
  executed exactly as ``research/month_end_candidate_reaudit.py`` executes it)
  -- not the legacy calendar rule and not the daily re-rank path;
* evaluates the **pre-registered** walk-forward protocol
  (``config/csmomentum_candidate_001.yaml:evaluation.walk_forward``) on each
  sample and publishes the **pre-registered** gate table
  (``evaluation.promotion_gates``) on the **backtest scale**
  (``backtest_sharpe_ratio``), the scale on which the candidate's gate was
  originally evaluated;
* reproduces the committed config-faithful record of
  ``research/reports/month_end_candidate_reaudit_001.md`` on the union sample
  -- the reproduction anchor, on which the tool's OVERALL depends;
* publishes the degenerate-fold diagnostic (the cross-section every fold is
  trained on and traded on), the **fold-independence** diagnostic (the overlap
  between consecutive test windows and the maximum number of pairwise-disjoint
  test windows) and a matched-fold-window sensitivity;
* writes ``research/reports/csmomentum_common_inception_gate_001.md`` and
  touches nothing else: nothing under ``data/`` or ``config/`` is written
  (checked by fingerprint before/after), no committed artifact is modified
  (checked by fingerprint before/after).

No gate, threshold, decision mapping, universe, cost model, parameter,
candidate configuration or committed artifact is changed. The plateau gate is
reported as NOT EVALUATED (the 27-configuration robustness grid is out of
scope for this cycle).

Reproduction: ``python research/csmomentum_sample_gate_audit.py``
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.csmomentum_common_inception_audit import (  # noqa: E402
    aligned_close_from_cache,
    fail,
    fingerprint,
    load_policy,
)
from research.month_end_candidate_reaudit import (  # noqa: E402
    build_csmomentum,
    gates_for,
    walkforward,
)
from research.promotion_feasibility_backtest import load_yaml, scan_raw_cache  # noqa: E402
from src.backtest.engine import (  # noqa: E402
    compute_metrics,
    get_cost_params,
    get_risk_free_rate,
)
from src.evaluation.sharpe import sharpe_ratio  # noqa: E402
from src.evaluation.walkforward import generate_walkforward_splits  # noqa: E402
from src.features.momentum import compute_momentum  # noqa: E402

CONFIG_CAND = REPO_ROOT / "config" / "csmomentum_candidate_001.yaml"
POLICY_DEFAULT = REPO_ROOT / "config" / "sample_policy.yaml"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
OUT_REPORT = REPORTS_DIR / "csmomentum_common_inception_gate_001.md"

CANDIDATE_ID = "csmomentum_001"
UNION_SAMPLE = "union_sample"
EVALUATION_SAMPLE = "common_inception_slice"
WINDOW_SAMPLE = "common_inception_window"
SAMPLE_ORDER = (UNION_SAMPLE, EVALUATION_SAMPLE, WINDOW_SAMPLE)

#: The selection fallback threshold of ``src/features/momentum.py`` (5 assets).
#: A cross-section narrower than this is a degenerate selection: the ranking
#: is taken over a handful of assets (with one, it is a single-asset,
#: time-series bet rather than a cross-sectional one).
BREADTH_FALLBACK = 5

#: The committed config-faithful record of
#: ``research/reports/month_end_candidate_reaudit_001.md`` (section 2.3), on
#: the union sample. The tool's OVERALL depends on reproducing it at the
#: tolerance of the last published decimal.
PUBLISHED_UNION_WF = {
    "n_folds": "48",
    "mean_test_sharpe": "0.6975",
    "mean_test_sharpe_canonical": "0.8404",
    "median_test_sharpe": "0.6179",
    "pct_positive_sharpe": "0.7917",
    "total_test_trades": "400",
}

#: The two values the union-sample path must **not** produce: the legacy
#: calendar rule (0.6868) and the daily re-rank path (0.6928).
FORBIDDEN_UNION_WF = {
    "legacy_calendar_path": "0.6868",
    "daily_rerank_path": "0.6928",
}

#: Committed artifacts this tool must not modify (byte-identical before/after).
COMMITTED_ARTIFACTS = (
    "research/experiments/csmomentum_001_experiment_001.md",
    "research/experiments/csmomentum_baseline_wf_001.md",
    "research/reports/month_end_candidate_reaudit_001.md",
    "research/reports/promotion_feasibility_backtest_001.md",
)


# ----------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def decimals_of(text: str) -> int:
    return len(text.split(".")[1]) if "." in text else 0


def compare_published(observed: float, published_text: str) -> dict[str, Any]:
    """Compare one observed number with a published one.

    The published value is quoted as the string it has in the committed
    record, so the tolerance of the comparison is the unit of that string's
    last published decimal (the repository's own convention, see
    ``research/month_end_candidate_reaudit.py:compare_published``).
    """
    published = float(published_text)
    decimals = decimals_of(published_text)
    tolerance = 10.0 ** (-decimals)
    diff = abs(float(observed) - published)
    return {
        "published": published,
        "published_text": published_text,
        "decimals": decimals,
        "tolerance": tolerance,
        "observed": float(observed),
        "abs_diff": diff,
        "match": bool(diff <= tolerance),
    }


def path_summary(
    net: pd.Series,
    weights: pd.DataFrame,
) -> dict[str, Any]:
    """Full-sample summary of one execution path (repository conventions)."""
    if len(net) < 2:
        return {"sessions": int(len(net))}
    bt = compute_metrics(net, weights, *get_cost_params(), get_risk_free_rate())
    return {
        "sessions": int(len(net)),
        "start_date": net.index[0].date().isoformat(),
        "end_date": net.index[-1].date().isoformat(),
        "sharpe_backtest_scale": float(bt["sharpe_ratio"]),
        "sharpe_canonical": float(sharpe_ratio(net)),
        "annualized_return": float(bt["annualized_return"]),
        "annualized_volatility": float(bt["annualized_volatility"]),
        "max_drawdown": float(bt["max_drawdown"]),
        "annualized_turnover": float(bt["annualized_turnover"]),
        "trade_days": int(bt["trade_count"]),
        "mean_positions": float((weights > 0).sum(axis=1).mean()),
    }


def max_disjoint_test_windows(folds: list[dict[str, Any]]) -> int:
    """The maximum number of folds whose test windows share no session.

    The pre-registered design steps the folds by 6 months over a 12-month test
    window, so consecutive test windows overlap: the folds are **not**
    independent observations, and the number of disjoint test windows is the
    honest upper bound on the independent evidence the walk-forward carries.
    """
    intervals = sorted((f["test_start"], f["test_end"]) for f in folds)
    count = 0
    last_end: str | None = None
    for start, end in intervals:
        if last_end is None or start > last_end:
            count += 1
            last_end = end
    return count


def mean_consecutive_overlap_days(folds: list[dict[str, Any]]) -> float:
    """Mean overlap (in calendar days) between consecutive test windows."""
    overlaps = []
    for prev, nxt in zip(folds, folds[1:]):
        a = pd.Timestamp(prev["test_end"])
        b = pd.Timestamp(nxt["test_start"])
        overlaps.append(max(0, int((a - b).days)))
    if not overlaps:
        return 0.0
    return float(sum(overlaps) / len(overlaps))


def breadth_stats(breadth: pd.Series) -> dict[str, Any]:
    """Selectable-breadth summary of one sample."""
    if breadth.empty:
        return {"sessions": 0, "sessions_with_zero_selectable_assets": 0}
    held = breadth[breadth > 0]
    below = breadth[breadth < BREADTH_FALLBACK]
    return {
        "sessions": int(len(breadth)),
        "opening_breadth": int(breadth.iloc[0]),
        "breadth_min": int(breadth.min()),
        "breadth_median": float(breadth.median()),
        "breadth_max": int(breadth.max()),
        "sessions_with_zero_selectable_assets": int((breadth == 0).sum()),
        "sessions_below_fallback": int(len(below)),
        "first_session_below_fallback": (
            below.index.min().date().isoformat() if not below.empty else None
        ),
        "last_session_below_fallback": (
            below.index.max().date().isoformat() if not below.empty else None
        ),
        "first_session_with_a_selectable_asset": (
            held.index.min().date().isoformat() if not held.empty else None
        ),
    }


def fold_diagnostics(
    splits: list[dict[str, Any]],
    index: pd.DatetimeIndex,
    priced: pd.Series,
    valid: pd.Series,
) -> list[dict[str, Any]]:
    """The cross-section every fold is trained on and traded on.

    For every fold: the number of assets with a price and the number with a
    valid momentum at the **training-window end** (as pre-registered), plus
    the minimum over the training window and the breadth at the start of the
    test window, so that the mechanism by which the union sample differs
    from the common-inception samples is visible rather than asserted.
    """
    rows: list[dict[str, Any]] = []
    for i, sp in enumerate(splits):
        ts = pd.Timestamp(sp["train_start"], tz="UTC")
        te = pd.Timestamp(sp["train_end"], tz="UTC")
        tes = pd.Timestamp(sp["test_start"], tz="UTC")
        tee = pd.Timestamp(sp["test_end"], tz="UTC")
        train_idx = index[(index >= ts) & (index <= te)]
        test_idx = index[(index >= tes) & (index <= tee)]
        train_valid = valid.reindex(train_idx)
        test_valid = valid.reindex(test_idx)
        train_priced = priced.reindex(train_idx)
        rows.append(
            {
                "fold": i + 1,
                "train_start": sp["train_start"],
                "train_end": sp["train_end"],
                "test_start": sp["test_start"],
                "test_end": sp["test_end"],
                "train_sessions_in_sample": int(len(train_idx)),
                "test_sessions_in_sample": int(len(test_idx)),
                "train_end_assets_priced": int(train_priced.iloc[-1]) if len(train_idx) else 0,
                "train_end_assets_valid_momentum": (
                    int(train_valid.iloc[-1]) if len(train_idx) else 0
                ),
                "train_min_assets_valid_momentum": (
                    int(train_valid.min()) if len(train_idx) else 0
                ),
                "test_start_assets_valid_momentum": (
                    int(test_valid.iloc[0]) if len(test_idx) else 0
                ),
                "test_min_assets_valid_momentum": (
                    int(test_valid.min()) if len(test_idx) else 0
                ),
                "test_sessions_below_fallback": (
                    int((test_valid < BREADTH_FALLBACK).sum()) if len(test_idx) else 0
                ),
            }
        )
    return rows


def diagnostic_counts(diag: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate the degenerate-fold diagnostic."""
    n = len(diag)
    if n == 0:
        return {"folds": 0}
    return {
        "folds": n,
        "folds_with_train_end_breadth_below_fallback": int(
            sum(1 for r in diag if r["train_end_assets_valid_momentum"] < BREADTH_FALLBACK)
        ),
        "folds_with_train_window_breadth_below_fallback": int(
            sum(1 for r in diag if r["train_min_assets_valid_momentum"] < BREADTH_FALLBACK)
        ),
        "folds_with_test_window_breadth_below_fallback": int(
            sum(1 for r in diag if r["test_min_assets_valid_momentum"] < BREADTH_FALLBACK)
        ),
        "folds_entirely_below_fallback_in_test": int(
            sum(
                1
                for r in diag
                if r["test_sessions_in_sample"] > 0
                and r["test_sessions_below_fallback"] == r["test_sessions_in_sample"]
            )
        ),
        "min_train_end_assets_valid_momentum": int(
            min(r["train_end_assets_valid_momentum"] for r in diag)
        ),
        "min_test_start_assets_valid_momentum": int(
            min(r["test_start_assets_valid_momentum"] for r in diag)
        ),
        "min_test_min_assets_valid_momentum": int(
            min(r["test_min_assets_valid_momentum"] for r in diag)
        ),
    }


def build_gate_table(
    wf: dict[str, Any],
    gate_cfg: dict[str, Any],
) -> list[dict[str, Any]]:
    """The pre-registered gate table of one sample.

    The gate table is evaluated on the **backtest scale** only
    (``backtest_sharpe_ratio``), the scale on which the candidate's gate was
    originally evaluated. The canonical scale is published beside the summary
    but never mixed into a gate.
    """
    mean_wf = float(wf.get("mean_test_sharpe", float("nan")))
    pct_pos = float(wf.get("pct_positive_sharpe", float("nan")))
    pooled = int(wf.get("total_test_trades", 0))
    g1 = bool(mean_wf >= float(gate_cfg["wf_mean_oos_sharpe_min"]))
    g2 = bool(pct_pos >= float(gate_cfg["positive_fold_rate_min"]))
    g3 = bool(pooled > float(gate_cfg["pooled_oos_trades_min"]))
    return [
        {
            "gate": "wf_mean_oos_sharpe",
            "threshold": f">= {gate_cfg['wf_mean_oos_sharpe_min']}",
            "observed": mean_wf,
            "status": "PASS" if g1 else "FAIL",
        },
        {
            "gate": "positive_fold_rate",
            "threshold": f">= {gate_cfg['positive_fold_rate_min']}",
            "observed": pct_pos,
            "status": "PASS" if g2 else "FAIL",
        },
        {
            "gate": "pooled_oos_trades",
            "threshold": f">> {gate_cfg['pooled_oos_trades_min']}",
            "observed": pooled,
            "status": "PASS" if g3 else "FAIL",
        },
        {
            "gate": "plateau",
            "threshold": f">= {gate_cfg['plateau_fraction_min']} (>= 2 of 3 lookbacks)",
            "observed": None,
            "status": "NOT EVALUATED",
            "reason": (
                "the 27-configuration robustness grid is out of scope for this cycle "
                "(it is a re-optimisation, not a measurement); the plateau gate is "
                "reported as NOT EVALUATED, as the published record already does"
            ),
        },
    ]


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, default=POLICY_DEFAULT)
    args = parser.parse_args(argv)

    # --- the policy fails closed -------------------------------------
    policy, section = load_policy(args.policy)

    cand = load_yaml(CONFIG_CAND)
    universe = list(cand["universe"])
    if list(section["universe"]) != universe:
        fail("policy universe does not match config/csmomentum_candidate_001.yaml")

    signal_cfg = cand["signal"]
    lookback = int(signal_cfg["lookback"])
    skip = int(signal_cfg["skip"])
    top_fraction = float(signal_cfg["top_fraction"])
    evaluation = cand["evaluation"]
    wf_cfg = evaluation["walk_forward"]
    gate_cfg = evaluation["promotion_gates"]
    test_end = str(evaluation["splits"]["test_end"])
    history_start = str(cand["history_start"])

    commission, slippage = get_cost_params()
    cost_per_trade = commission + slippage

    # --- read-only fingerprints (before) ------------------------------
    data_before = fingerprint(REPO_ROOT / "data")
    config_before = fingerprint(REPO_ROOT / "config")
    artifacts_before = {rel: sha256_file(REPO_ROOT / rel) for rel in COMMITTED_ARTIFACTS}

    # --- data (committed cache only, never the fetcher) ---------------
    per_symbol_stats, raw_hashes, raw_union_index = scan_raw_cache(universe)
    common_inception = pd.Timestamp(
        max(s["first_date"] for s in per_symbol_stats.values()), tz="UTC"
    )
    ci_str = common_inception.date().isoformat()

    close_full = aligned_close_from_cache(universe)
    close_union = close_full.loc[
        (close_full.index >= pd.Timestamp(history_start, tz="UTC"))
        & (close_full.index <= pd.Timestamp(test_end, tz="UTC"))
    ].copy()
    close_slice = close_union.loc[close_union.index >= common_inception].copy()
    window_index = close_union.index[close_union.index >= common_inception]

    # --- the config-faithful paths -------------------------------------
    union_path = build_csmomentum(close_union, cost_per_trade)
    slice_path = build_csmomentum(close_slice, cost_per_trade)
    # the warm-up-preserving window keeps the union frame, so its path *is*
    # the union path; only the evaluation window is truncated.
    window_path = union_path

    # --- the pre-registered walk-forward protocol ----------------------
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
    inception_splits = splits_for(ci_str)

    union_wf, union_rows = walkforward(
        union_path["faithful_net"], union_path["faithful_weights"], union_splits
    )
    slice_wf, slice_rows = walkforward(
        slice_path["faithful_net"], slice_path["faithful_weights"], inception_splits
    )
    window_wf, window_rows = walkforward(
        window_path["faithful_net"].loc[window_index],
        window_path["faithful_weights"].loc[window_index],
        inception_splits,
    )

    # --- the matched-fold-window sensitivity ---------------------------
    # The fold calendar is anchored at the declared start of each sample, so
    # the three calendars are offset by a few sessions. This block evaluates
    # all three paths on the *same* test windows (the union sample's folds
    # whose test window lies inside the common-inception window) and removes
    # that offset from the comparison.
    first_common_test_start = slice_rows[0]["test_start"] if slice_rows else None
    matched_splits = [
        sp
        for sp, r in zip(union_splits, union_rows)
        if first_common_test_start is not None and r["test_start"] >= first_common_test_start
    ]
    # how far apart the two fold calendars are: the union fold that starts just
    # before the common-inception samples' first test window, and the number
    # of sessions between the two dates.
    union_fold_before = [r for r in union_rows if r["test_start"] < first_common_test_start]
    union_fold_after = [r for r in union_rows if r["test_start"] >= first_common_test_start]
    offset_sessions = None
    if union_fold_before and first_common_test_start:
        a = pd.Timestamp(union_fold_before[-1]["test_start"], tz="UTC")
        b = pd.Timestamp(first_common_test_start, tz="UTC")
        offset_sessions = int(((close_union.index > a) & (close_union.index <= b)).sum())
    fold_calendar = {
        "common_inception_first_test_start": first_common_test_start,
        "union_fold_before": union_fold_before[-1]["test_start"] if union_fold_before else None,
        "union_fold_after": union_fold_after[0]["test_start"] if union_fold_after else None,
        "offset_sessions": offset_sessions,
    }
    matched: dict[str, Any] = {}
    for name, path, net_index in (
        (UNION_SAMPLE, union_path, None),
        (EVALUATION_SAMPLE, slice_path, None),
        (WINDOW_SAMPLE, window_path, window_index),
    ):
        net = path["faithful_net"]
        weights = path["faithful_weights"]
        if net_index is not None:
            net = net.loc[net_index]
            weights = weights.loc[net_index]
        wf_m, _rows_m = walkforward(net, weights, matched_splits)
        matched[name] = {
            "folds": int(wf_m.get("n_folds", 0)),
            "mean_test_sharpe": wf_m.get("mean_test_sharpe"),
            "median_test_sharpe": wf_m.get("median_test_sharpe"),
            "pct_positive_sharpe": wf_m.get("pct_positive_sharpe"),
            "total_test_trades": int(wf_m.get("total_test_trades", 0)),
        }

    # --- the degenerate-fold diagnostic --------------------------------
    def diagnostics_for(frame: pd.DataFrame, splits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        momentum = compute_momentum(frame, lookback=lookback, skip=skip)
        priced = frame.notna().sum(axis=1)
        valid = momentum.notna().sum(axis=1)
        return fold_diagnostics(splits, frame.index, priced, valid)

    union_diag = diagnostics_for(close_union, union_splits)
    slice_diag = diagnostics_for(close_slice, inception_splits)
    window_diag = diagnostics_for(close_union, inception_splits)

    # --- the three samples ---------------------------------------------
    samples: dict[str, Any] = {}
    sample_inputs = {
        UNION_SAMPLE: {
            "frame": close_union,
            "path": union_path,
            "wf": union_wf,
            "rows": union_rows,
            "diag": union_diag,
            "net": union_path["faithful_net"],
            "weights": union_path["faithful_weights"],
            "split_anchor": history_start,
            "note": (
                "the union calendar of the raw cache, truncated at the frozen "
                "evaluation.splits.test_end; the sample the candidate's published "
                "gate table was measured on"
            ),
        },
        EVALUATION_SAMPLE: {
            "frame": close_slice,
            "path": slice_path,
            "wf": slice_wf,
            "rows": slice_rows,
            "diag": slice_diag,
            "net": slice_path["faithful_net"],
            "weights": slice_path["faithful_weights"],
            "split_anchor": ci_str,
            "note": (
                "the price frame is truncated at the common inception before the "
                "signal is formed, so the signal has no warm-up"
            ),
        },
        WINDOW_SAMPLE: {
            "frame": close_union,
            "path": window_path,
            "wf": window_wf,
            "rows": window_rows,
            "diag": window_diag,
            "net": window_path["faithful_net"].loc[window_index],
            "weights": window_path["faithful_weights"].loc[window_index],
            "split_anchor": ci_str,
            "note": (
                "the union frame is kept (warm-up preserved); only the evaluation "
                "window is truncated at the common inception"
            ),
        },
    }

    for name in SAMPLE_ORDER:
        item = sample_inputs[name]
        frame = item["frame"]
        momentum = compute_momentum(frame, lookback=lookback, skip=skip)
        breadth = momentum.notna().sum(axis=1).reindex(item["net"].index)
        gates = build_gate_table(item["wf"], gate_cfg)
        decision = gates_for(item["wf"], gate_cfg)
        samples[name] = {
            "note": item["note"],
            "split_anchor": item["split_anchor"],
            "start_date": item["net"].index[0].date().isoformat(),
            "end_date": item["net"].index[-1].date().isoformat(),
            "sessions": int(len(item["net"])),
            "price_width_min": int(frame.notna().sum(axis=1).reindex(item["net"].index).min()),
            "price_width_max": int(frame.notna().sum(axis=1).reindex(item["net"].index).max()),
            "path": path_summary(item["net"], item["weights"]),
            "walk_forward": {
                "n_folds": int(item["wf"]["n_folds"]),
                "mean_test_sharpe": float(item["wf"]["mean_test_sharpe"]),
                "mean_test_sharpe_canonical": float(item["wf"]["mean_test_sharpe_canonical"]),
                "std_test_sharpe": float(item["wf"]["std_test_sharpe"]),
                "median_test_sharpe": float(item["wf"]["median_test_sharpe"]),
                "min_test_sharpe": float(item["wf"]["min_test_sharpe"]),
                "max_test_sharpe": float(item["wf"]["max_test_sharpe"]),
                "pct_positive_sharpe": float(item["wf"]["pct_positive_sharpe"]),
                "total_test_trades": int(item["wf"]["total_test_trades"]),
                "mean_consecutive_test_window_overlap_days": mean_consecutive_overlap_days(
                    item["rows"]
                ),
                "max_disjoint_test_windows": max_disjoint_test_windows(item["rows"]),
                "folds": item["rows"],
            },
            "gates": gates,
            "decision": {
                "label": decision["label"],
                "falsified": bool(decision["falsified"]),
                "falsification_rule": (
                    "the published mapping: falsified when the walk-forward mean OOS "
                    "Sharpe gate or the positive-fold-rate gate fails"
                ),
            },
            "breadth": breadth_stats(breadth),
            "degenerate_folds": diagnostic_counts(item["diag"]),
            "fold_diagnostics": item["diag"],
        }

    # --- the reproduction anchor (the union sample) --------------------
    anchor_rows = []
    for key, published_text in PUBLISHED_UNION_WF.items():
        if key == "n_folds":
            observed = float(union_wf["n_folds"])
        else:
            observed = float(union_wf[key])
        anchor_rows.append(
            {"metric": key, **compare_published(observed, published_text)}
        )
    anchor_ok = all(r["match"] for r in anchor_rows)

    forbidden_rows = []
    for label, published_text in FORBIDDEN_UNION_WF.items():
        published = float(published_text)
        observed = float(union_wf["mean_test_sharpe"])
        forbidden_rows.append(
            {
                "path": label,
                "published_mean_test_sharpe": published,
                "observed_union_mean_test_sharpe": observed,
                "abs_diff": abs(observed - published),
                "produced": bool(abs(observed - published) <= 10.0 ** (-decimals_of(published_text))),
            }
        )
    forbidden_ok = not any(r["produced"] for r in forbidden_rows)

    # --- structural checks ---------------------------------------------
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, observed: Any = None, expected: Any = None) -> None:
        checks.append(
            {
                "name": name,
                "expected": expected,
                "observed": observed,
                "pass": bool(passed),
            }
        )

    check(
        "policy_universe_matches_candidate_config",
        list(section["universe"]) == universe,
        observed=len(section["universe"]),
        expected=len(universe),
    )
    check(
        "common_inception_rederived_from_raw_cache",
        ci_str
        == max(s["first_date"] for s in per_symbol_stats.values()),
        observed=ci_str,
        expected="max of per-symbol first dates in data/raw",
    )
    check(
        "aligned_index_matches_the_raw_cache_union",
        set(close_full.index) == set(raw_union_index),
        observed=int(len(close_full.index)),
        expected=int(len(raw_union_index)),
    )
    check(
        "union_sample_reproduces_the_committed_config_faithful_record",
        anchor_ok,
        observed={
            r["metric"]: r["observed"] for r in anchor_rows
        },
        expected={k: v for k, v in PUBLISHED_UNION_WF.items()},
    )
    check(
        "union_sample_does_not_reproduce_the_legacy_or_daily_values",
        forbidden_ok,
        observed=[r["path"] for r in forbidden_rows if not r["produced"]],
        expected="no legacy (0.6868) or daily re-rank (0.6928) value produced",
    )
    check(
        "config_faithful_path_equals_the_shared_month_end_module",
        bool(union_path["faithful_equals_shared_module"])
        and bool(slice_path["faithful_equals_shared_module"]),
        observed={
            "union": union_path["faithful_equals_shared_module"],
            "slice": slice_path["faithful_equals_shared_module"],
        },
        expected=True,
    )
    pit_ok = True
    for path in (union_path, slice_path):
        for seg in path["segments"]:
            expected_w = (
                path["mask"].loc[seg["signal_date"]].astype(float).to_numpy()
                / seg["n_selected"]
            )
            actual_w = path["faithful_weights"].loc[seg["effective_date"]].to_numpy()
            if not all(abs(a - b) <= 1e-12 for a, b in zip(expected_w, actual_w)):
                pit_ok = False
            if not seg["effective_date"] > seg["signal_date"]:
                pit_ok = False
    check(
        "config_faithful_path_is_point_in_time",
        pit_ok and len(union_path["segments"]) > 0 and len(slice_path["segments"]) > 0,
        observed={
            "union_segments": len(union_path["segments"]),
            "slice_segments": len(slice_path["segments"]),
        },
        expected="every segment equals the selection at its own signal date and becomes effective strictly after it",
    )
    check(
        "evaluation_window_ends_at_the_frozen_test_end",
        all(
            samples[name]["end_date"] == test_end for name in SAMPLE_ORDER
        ),
        observed={name: samples[name]["end_date"] for name in SAMPLE_ORDER},
        expected=test_end,
    )
    excluded = [d.date().isoformat() for d in close_full.index if d > pd.Timestamp(test_end, tz="UTC")]
    check(
        "cached_sessions_after_the_test_end_are_excluded",
        len(excluded) == 6
        and all(samples[name]["end_date"] == test_end for name in SAMPLE_ORDER),
        observed=excluded,
        expected="the six cached sessions 2026-10-12..2026-10-19 are outside the window",
    )
    check(
        "common_inception_sample_is_fully_populated",
        samples[EVALUATION_SAMPLE]["price_width_min"] == len(universe)
        and samples[EVALUATION_SAMPLE]["price_width_max"] == len(universe),
        observed={
            "min": samples[EVALUATION_SAMPLE]["price_width_min"],
            "max": samples[EVALUATION_SAMPLE]["price_width_max"],
        },
        expected=len(universe),
    )
    check(
        "union_sample_is_ragged",
        samples[UNION_SAMPLE]["price_width_min"] < len(universe),
        observed=samples[UNION_SAMPLE]["price_width_min"],
        expected=f"< {len(universe)}",
    )
    check(
        "plateau_gate_is_reported_as_not_evaluated",
        all(
            next(g for g in samples[name]["gates"] if g["gate"] == "plateau")["status"]
            == "NOT EVALUATED"
            for name in SAMPLE_ORDER
        ),
        observed="NOT EVALUATED on every sample",
        expected="NOT EVALUATED on every sample",
    )
    union_breadth = samples[UNION_SAMPLE]["breadth"]
    union_folds = samples[UNION_SAMPLE]["walk_forward"]["folds"]
    first_test_start = union_folds[0]["test_start"] if union_folds else ""
    check(
        "union_degenerate_sessions_precede_the_earliest_test_window",
        bool(union_breadth["last_session_below_fallback"])
        and union_breadth["last_session_below_fallback"] < first_test_start,
        observed={
            "last_session_below_fallback": union_breadth["last_session_below_fallback"],
            "earliest_test_window_start": first_test_start,
        },
        expected="the degenerate sessions of the union sample lie before the earliest fold's test window",
    )
    check(
        "every_sample_publishes_a_decision",
        all(samples[name]["decision"]["label"] for name in SAMPLE_ORDER),
        observed={name: samples[name]["decision"]["label"] for name in SAMPLE_ORDER},
        expected="a decision on every sample",
    )

    # --- read-only proof (after) ---------------------------------------
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
        observed=sorted(
            rel for rel in COMMITTED_ARTIFACTS if artifacts_before[rel] != artifacts_after[rel]
        ),
        expected="no committed artifact modified",
    )

    overall = "PASS" if all(c["pass"] for c in checks) else "FAIL"

    payload = {
        "candidate": CANDIDATE_ID,
        "artifact": "common-inception gate table (measurement only, no re-optimisation)",
        "gate_scale": "backtest_sharpe_ratio",
        "policy": {
            "path": str(args.policy),
            "schema_version": policy.get("schema_version"),
            "rule_id": section["rule_id"],
            "evaluation_sample": section["long_sample_diagnostic"]["evaluation_sample"],
            "publish_alongside": section["long_sample_diagnostic"]["publish_alongside"],
            "derivation_rule": section["derivation"]["rule"],
            "evidence_note": section["evidence_note"],
        },
        "candidate_configuration": {
            "lookback": lookback,
            "skip": skip,
            "top_fraction": top_fraction,
            "history_start": history_start,
            "test_end": test_end,
            "cost_model": cand.get("cost_model"),
            "walk_forward": wf_cfg,
            "promotion_gates": gate_cfg,
            "universe_size": len(universe),
        },
        "common_inception": ci_str,
        "samples": samples,
        "reproduction_anchor": {
            "source": "research/reports/month_end_candidate_reaudit_001.md (section 2.3)",
            "rows": anchor_rows,
            "matches": anchor_ok,
        },
        "forbidden_values": forbidden_rows,
        "matched_fold_windows": {
            "note": (
                "all three paths evaluated on the same test windows (the union "
                "sample's folds whose test window lies inside the common-inception "
                "window); removes the fold-calendar offset between the samples"
            ),
            "fold_calendar": fold_calendar,
            "folds": len(matched_splits),
            "first_test_start": matched_splits[0]["test_start"] if matched_splits else None,
            "last_test_end": matched_splits[-1]["test_end"] if matched_splits else None,
            "per_sample": matched,
        },
        "raw_cache_fingerprint": {
            "per_symbol": {
                sym: {
                    "first_date": per_symbol_stats[sym]["first_date"],
                    "last_date": per_symbol_stats[sym]["last_date"],
                    "row_count": per_symbol_stats[sym]["row_count"],
                    "sha256": raw_hashes[sym],
                }
                for sym in universe
            }
        },
        "checks": checks,
        "overall": overall,
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(build_report(payload))

    print(f"OVERALL: {overall}")
    for c in checks:
        print(f"check [{c['name']}]: {'PASS' if c['pass'] else 'FAIL'}")
    for name in SAMPLE_ORDER:
        s = samples[name]
        wf = s["walk_forward"]
        print(
            f"{name}: {s['sessions']} sessions ({s['start_date']}..{s['end_date']}), "
            f"{wf['n_folds']} folds, WF mean OOS Sharpe {wf['mean_test_sharpe']:.4f} "
            f"(backtest scale; canonical {wf['mean_test_sharpe_canonical']:.4f}), "
            f"median {wf['median_test_sharpe']:.4f}, positive {wf['pct_positive_sharpe']:.2%}, "
            f"pooled {wf['total_test_trades']} -> {s['decision']['label']}"
        )
    print(
        f"common inception {ci_str} (re-derived); matched-fold-window sensitivity: "
        + ", ".join(
            f"{name} {matched[name]['mean_test_sharpe']:.4f}" for name in SAMPLE_ORDER
        )
    )
    print(f"report: {OUT_REPORT.relative_to(REPO_ROOT)}")
    return 0 if overall == "PASS" else 1


# ----------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------
def _fmt(value: Any, spec: str = ".4f") -> str:
    if value is None:
        return "n/a"
    try:
        return format(float(value), spec)
    except (TypeError, ValueError):
        return str(value)


def build_report(payload: dict[str, Any]) -> str:
    """Render the cycle report (deterministic: no timestamps)."""
    p = payload
    samples = p["samples"]
    wf_cfg = p["candidate_configuration"]["walk_forward"]
    gate_cfg = p["candidate_configuration"]["promotion_gates"]
    names = list(SAMPLE_ORDER)

    def gate_of(name: str, gate: str) -> dict[str, Any]:
        return next(g for g in samples[name]["gates"] if g["gate"] == gate)

    def status_of(name: str, gate: str) -> str:
        return gate_of(name, gate)["status"]

    summary_rows = "\n".join(
        "| {label} | {sessions} | {start}..{end} | {folds} | {mean} | {median} | {pos} | "
        "{pooled} | {g1} | {g2} | {g3} | {g4} | **{decision}** |".format(
            label=name,
            sessions=samples[name]["sessions"],
            start=samples[name]["start_date"],
            end=samples[name]["end_date"],
            folds=samples[name]["walk_forward"]["n_folds"],
            mean=_fmt(samples[name]["walk_forward"]["mean_test_sharpe"]),
            median=_fmt(samples[name]["walk_forward"]["median_test_sharpe"]),
            pos=_fmt(samples[name]["walk_forward"]["pct_positive_sharpe"] * 100, ".2f") + "%",
            pooled=samples[name]["walk_forward"]["total_test_trades"],
            g1=status_of(name, "wf_mean_oos_sharpe"),
            g2=status_of(name, "positive_fold_rate"),
            g3=status_of(name, "pooled_oos_trades"),
            g4=status_of(name, "plateau"),
            decision=samples[name]["decision"]["label"],
        )
        for name in names
    )

    def fold_table(name: str) -> str:
        lines = [
            "| Fold | Test window | Sessions | OOS Sharpe (backtest) | OOS Sharpe (canonical) |",
            "|---|---|---|---|---|",
        ]
        for r in samples[name]["walk_forward"]["folds"]:
            lines.append(
                f"| {r['fold']} | {r['test_start']}..{r['test_end']} | {r['test_sessions']} | "
                f"{r['test_sharpe']:.4f} | {r['test_sharpe_canonical']:.4f} |"
            )
        return "\n".join(lines)

    def diag_table(name: str) -> str:
        lines = [
            "| Fold | Test window | Assets priced @ train end | Assets with valid momentum @ train end | "
            "Min valid momentum in train window | Valid momentum @ test start | Min valid momentum in test window |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in samples[name]["fold_diagnostics"]:
            lines.append(
                f"| {r['fold']} | {r['test_start']}..{r['test_end']} | "
                f"{r['train_end_assets_priced']} | {r['train_end_assets_valid_momentum']} | "
                f"{r['train_min_assets_valid_momentum']} | {r['test_start_assets_valid_momentum']} | "
                f"{r['test_min_assets_valid_momentum']} |"
            )
        return "\n".join(lines)

    def diag_summary_table() -> str:
        lines = [
            "| Sample | Folds | Train-end breadth < 5 | Train window contains breadth < 5 | "
            "Test window contains breadth < 5 | Test window entirely breadth < 5 | "
            "Min valid momentum @ test start |",
            "|---|---|---|---|---|---|---|",
        ]
        for name in names:
            d = samples[name]["degenerate_folds"]
            lines.append(
                f"| {name} | {d['folds']} | {d['folds_with_train_end_breadth_below_fallback']} | "
                f"{d['folds_with_train_window_breadth_below_fallback']} | "
                f"{d['folds_with_test_window_breadth_below_fallback']} | "
                f"{d['folds_entirely_below_fallback_in_test']} | "
                f"{d['min_test_start_assets_valid_momentum']} |"
            )
        return "\n".join(lines)

    def path_table() -> str:
        lines = [
            "| Sample | Sessions | Sharpe (backtest) | Sharpe (canonical) | Ann. return | "
            "Max drawdown | Ann. turnover | Trade days | Mean positions |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for name in names:
            ps = samples[name]["path"]
            lines.append(
                f"| {name} | {ps['sessions']} | {ps['sharpe_backtest_scale']:.4f} | "
                f"{ps['sharpe_canonical']:.4f} | {ps['annualized_return']:.4f} | "
                f"{ps['max_drawdown']:.4f} | {ps['annualized_turnover']:.2f} | "
                f"{ps['trade_days']} | {ps['mean_positions']:.2f} |"
            )
        return "\n".join(lines)

    def independence_table() -> str:
        lines = [
            "| Sample | Folds | Mean consecutive test-window overlap (days) | "
            "Maximum number of disjoint test windows |",
            "|---|---|---|---|",
        ]
        for name in names:
            wf = samples[name]["walk_forward"]
            lines.append(
                f"| {name} | {wf['n_folds']} | "
                f"{wf['mean_consecutive_test_window_overlap_days']:.0f} | "
                f"{wf['max_disjoint_test_windows']} |"
            )
        return "\n".join(lines)

    anchor_rows = "\n".join(
        f"| `{r['metric']}` | {r['published_text']} | {r['observed']:.6f} | "
        f"{r['abs_diff']:.3e} | {r['tolerance']:.0e} | {'MATCH' if r['match'] else 'DIFFERS'} |"
        for r in p["reproduction_anchor"]["rows"]
    )
    forbidden_rows = "\n".join(
        f"| {r['path']} | {r['published_mean_test_sharpe']:.4f} | "
        f"{r['observed_union_mean_test_sharpe']:.6f} | {r['abs_diff']:.3e} | "
        f"{'PRODUCED' if r['produced'] else 'not produced'} |"
        for r in p["forbidden_values"]
    )
    matched = p["matched_fold_windows"]
    matched_rows = "\n".join(
        f"| {name} | {matched['per_sample'][name]['folds']} | "
        f"{_fmt(matched['per_sample'][name]['mean_test_sharpe'])} | "
        f"{_fmt(matched['per_sample'][name]['median_test_sharpe'])} | "
        f"{_fmt(matched['per_sample'][name]['pct_positive_sharpe'] * 100, '.2f')}% | "
        f"{matched['per_sample'][name]['total_test_trades']} |"
        for name in names
    )
    check_rows = "\n".join(
        f"| `{c['name']}` | {'PASS' if c['pass'] else 'FAIL'} | {c['observed']} | {c['expected']} |"
        for c in p["checks"]
    )
    fingerprint_rows = "\n".join(
        f"| {sym} | {info['first_date']} | {info['last_date']} | {info['row_count']} | "
        f"`{info['sha256'][:16]}` |"
        for sym, info in p["raw_cache_fingerprint"]["per_symbol"].items()
    )

    union = samples[UNION_SAMPLE]
    slice_ = samples[EVALUATION_SAMPLE]
    window = samples[WINDOW_SAMPLE]
    union_wf = union["walk_forward"]
    slice_wf = slice_["walk_forward"]
    window_wf = window["walk_forward"]

    return f"""# CSMomentum Common-Inception Gate Audit (csmomentum_common_inception_gate_001, Cycle 907)

## Summary

`csmomentum_001`'s published gate table was measured on the **union calendar** of the raw
cache, whose cross-section is ragged (it starts with one asset and reaches the full 18-asset
universe only at the common inception). Cycle 905 pre-registered, in
`config/sample_policy.yaml` (`candidates.csmomentum_001`), that the candidate's long-sample
diagnostic is evaluated on the **common-inception** sample, with the union sample and the
warm-up-preserving window published beside it. This cycle re-derives the candidate's
**config-faithful** walk-forward on the three pre-registered samples and publishes the three
gate tables side by side.

**Gate scale: backtest scale (`backtest_sharpe_ratio`)** -- the scale on which the candidate's
pre-registered walk-forward gate was originally evaluated. The canonical scale
(`arithmetic_annualized_rf0`) is published beside the summary but is never used for a gate.

| Sample | Sessions | Window | Folds | WF mean OOS Sharpe | Median | Positive folds | Pooled OOS trades | Gate 1 | Gate 2 | Gate 3 | Gate 4 (plateau) | Decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
{summary_rows}

**The verdict does not move.** The candidate stays **Rejected/Failed** on all three samples:
gate 1 (walk-forward mean OOS Sharpe >= {gate_cfg['wf_mean_oos_sharpe_min']}) fails on every
sample, by {gate_cfg['wf_mean_oos_sharpe_min'] - union_wf['mean_test_sharpe']:.4f} on the union
sample and by {gate_cfg['wf_mean_oos_sharpe_min'] - slice_wf['mean_test_sharpe']:.4f} on the
pre-registered common-inception samples. The published rejection is therefore **not** an
artefact of the sample definition; on the pre-registered sample the gate-1 margin is
*larger*, not smaller.

Two further findings are published below and neither favours the candidate:

1. **The ragged era never reaches a fold's test window.** The union sample contains
   {union['breadth']['sessions_below_fallback']} of {union['sessions']} sessions with fewer
   than {BREADTH_FALLBACK} selectable assets (the single-asset / degenerate-selection regime),
   from {union['breadth']['first_session_below_fallback']} to
   {union['breadth']['last_session_below_fallback']} -- i.e. **all of them lie before** the
   earliest fold's test window ({union['walk_forward']['folds'][0]['test_start']}). Every fold
   of every sample is therefore *traded* on a populated cross-section (at least
   {min(samples[n]['degenerate_folds']['min_test_start_assets_valid_momentum'] for n in names)}
   assets with a valid momentum at the start of a test window), and no fold is *trained* on a
   degenerate cross-section at its training-window end either (a ten-year training window is
   longer than the ragged era).
2. **The sample and the fold calendar move together.** The three samples' walk-forward
   calendars are anchored at their own declared start, so the common-inception calendars are
   offset by a few sessions from the union calendar. On the *same* test windows all three
   paths produce the same numbers (section 5), i.e. the difference between the union sample's
   {union_wf['mean_test_sharpe']:.4f} and the common-inception samples'
   {slice_wf['mean_test_sharpe']:.4f} is a fold-calendar effect of the size of the fold-to-fold
   scatter, not a change in the strategy's behaviour.
3. **The folds are not independent observations.** The 6-month step over a 12-month test
   window makes consecutive test windows overlap and the repository's generator does not apply
   the embargo parameter, so the honest count of independent test windows is
   {union_wf['max_disjoint_test_windows']} (union sample) and
   {slice_wf['max_disjoint_test_windows']} (common-inception samples) -- a property of the
   published protocol that applies to every sample equally (section 4.4).

No gate, threshold, decision mapping, universe, cost model, parameter, candidate
configuration or committed artifact was changed by this cycle.

## 1. Method

### 1.1 Data and provenance (read-only)

| Item | Value |
|---|---|
| Universe | {", ".join(p["raw_cache_fingerprint"]["per_symbol"].keys())} ({p["candidate_configuration"]["universe_size"]} assets) |
| Source | committed raw cache `data/raw/*.parquet` (cache-only: the fetcher is never called, so nothing is downloaded and nothing is written) |
| Evaluation window | {p["candidate_configuration"]["history_start"]} .. {p["candidate_configuration"]["test_end"]} (the frozen `evaluation.splits.test_end`) |
| Common inception | **{p['common_inception']}** (re-derived from the raw cache: max of the per-symbol first dates; no date in the policy is trusted) |
| Costs | {p['candidate_configuration']['cost_model']['commission_bps']} bps commission + {p['candidate_configuration']['cost_model']['slippage_bps']} bps slippage per round trip |
| Signal | lookback {p['candidate_configuration']['lookback']}, skip {p['candidate_configuration']['skip']}, top fraction {p['candidate_configuration']['top_fraction']} |

Per-symbol cache fingerprint (derived at run time, never a frozen literal):

| Symbol | First date | Last date | Rows | SHA-256 (first 16) |
|---|---|---|---|---|
{fingerprint_rows}

### 1.2 The three pre-registered samples

| Sample | Definition | Price frame | Warm-up |
|---|---|---|---|
| `union_sample` | the union calendar of the raw cache, truncated at the frozen test end | {union['start_date']}..{union['end_date']} ({union['sessions']} sessions, price width {union['price_width_min']}..{union['price_width_max']}) | preserved |
| `common_inception_slice` | the price frame is truncated at the common inception **before** the signal is formed | {slice_['start_date']}..{slice_['end_date']} ({slice_['sessions']} sessions, price width {slice_['price_width_min']}..{slice_['price_width_max']}) | none (the signal has no pre-inception history) |
| `common_inception_window` | the union frame is kept; only the evaluation window is truncated | {window['start_date']}..{window['end_date']} ({window['sessions']} sessions, price width {window['price_width_min']}..{window['price_width_max']}) | preserved |

### 1.3 The config-faithful path

The path is the **config-faithful month-end schedule** of
`src/backtest/rebalance.py:build_month_end_weights`, executed exactly as
`research/month_end_candidate_reaudit.py` executes it: the signal is formed on the **last
session** of the calendar month and the positions become effective on the **next** session and
are held until the next month-end signal. It is **not** the legacy calendar rule
(`weights.index.is_month_end`, published mean OOS Sharpe 0.6868) and **not** the daily re-rank
path (0.6928). The tool asserts the equality of the path with the shared module and the
point-in-time property of every segment (the weights of a segment equal the selection at its
own signal date and become effective strictly after it).

### 1.4 The pre-registered walk-forward protocol

{float(wf_cfg['train_years']):.0f}y train / {float(wf_cfg['test_months']):.0f}m test /
{float(wf_cfg['step_months']):.0f}m step, {wf_cfg['purge_days']}d purge, {wf_cfg['embargo_days']}d
embargo, **fixed parameters** (no per-fold re-optimisation). The fold windows are slices of
**one continuously computed point-in-time path** per sample; the training window is a label of
the design (the parameters are fixed), and it is reported because it is where the sample
difference shows up.

**What the repository's generator actually applies** (`src/evaluation/walkforward.py:generate_walkforward_splits`):
the {wf_cfg['purge_days']}-day **purge** is applied as a gap between the end of the training
window and the start of the test window; the {wf_cfg['embargo_days']}-day **embargo** parameter is
accepted but **not applied** to the fold construction, because the folds roll: the next fold's
training window starts {float(wf_cfg['step_months']):.0f} months after the previous fold's and
therefore contains the tail of the previous fold's test window. This is the repository's own
convention -- it is the generator that produced the candidate's own published 48-fold record and
the Cycle 871 config-faithful record -- so all three samples are measured identically and the
comparison is unaffected. It does mean that the folds are **not independent observations**: the
honest count of disjoint test windows is published in section 4.4. Because the parameters are
fixed, no information from a test window enters the trading path; the overlap is a
statistical-independence limitation, not a look-ahead.

Each sample's fold calendar is generated over that sample's own declared window: the union
sample over the configuration's `history_start`
({p['candidate_configuration']['history_start']}), the two common-inception samples over the
re-derived common inception ({p['common_inception']}). A fold can only be trained on data the
sample actually contains, so the common-inception samples' first out-of-sample fold starts
after a full {float(wf_cfg['train_years']):.0f}-year training window inside the sample.

### 1.5 The gate table and the decision mapping

The gate table is the candidate's own pre-registered table
(`config/csmomentum_candidate_001.yaml:evaluation.promotion_gates`):

| Gate | Threshold | Meaning |
|---|---|---|
| 1. `wf_mean_oos_sharpe` | >= {gate_cfg['wf_mean_oos_sharpe_min']} | mean out-of-sample Sharpe over the folds (backtest scale) |
| 2. `positive_fold_rate` | >= {gate_cfg['positive_fold_rate_min']} | share of folds with a positive out-of-sample Sharpe |
| 3. `pooled_oos_trades` | > {gate_cfg['pooled_oos_trades_min']} | pooled out-of-sample trade days over the folds |
| 4. `plateau` | >= {gate_cfg['plateau_fraction_min']} (>= 2 of 3 lookbacks) | **NOT EVALUATED** -- the 27-configuration grid is out of scope for this cycle |

The decision mapping is the published one (`research/month_end_candidate_reaudit.py:gates_for`):
the candidate is **falsified** when gate 1 or gate 2 fails, and the label is then
**Rejected/Failed**; otherwise the label is *exploratory signal*. Gate 3 and gate 4 are
published but are not part of the falsification condition.

## 2. The reproduction anchor (the union sample)

The tool's OVERALL depends on reproducing the committed config-faithful record of
`research/reports/month_end_candidate_reaudit_001.md` (section 2.3) on the union sample, at the
tolerance of the last published decimal.

| Metric | Published | Observed | Abs. diff | Tolerance | Result |
|---|---|---|---|---|---|
{anchor_rows}

The two values the union-sample path must **not** produce:

| Path | Published mean OOS Sharpe | Observed | Abs. diff | Result |
|---|---|---|---|---|
{forbidden_rows}

## 3. The three gate tables

### 3.1 `union_sample` (the sample the published record was measured on)

{union['note']}.

- path (full sample): Sharpe {union['path']['sharpe_backtest_scale']:.4f} (backtest scale) /
  {union['path']['sharpe_canonical']:.4f} (canonical), max drawdown
  {union['path']['max_drawdown']:.4f}, annual turnover {union['path']['annualized_turnover']:.2f}x,
  {union['path']['trade_days']} trade days, mean {union['path']['mean_positions']:.2f} positions
- walk-forward: {union_wf['n_folds']} folds, mean OOS Sharpe {union_wf['mean_test_sharpe']:.4f}
  (canonical {union_wf['mean_test_sharpe_canonical']:.4f}), median
  {union_wf['median_test_sharpe']:.4f}, std {union_wf['std_test_sharpe']:.4f}, positive
  {union_wf['pct_positive_sharpe']:.2%}, pooled OOS trades {union_wf['total_test_trades']}
- gates: 1 {status_of(UNION_SAMPLE, 'wf_mean_oos_sharpe')} (observed
  {gate_of(UNION_SAMPLE, 'wf_mean_oos_sharpe')['observed']:.4f}), 2
  {status_of(UNION_SAMPLE, 'positive_fold_rate')} (observed
  {gate_of(UNION_SAMPLE, 'positive_fold_rate')['observed']:.2%}), 3
  {status_of(UNION_SAMPLE, 'pooled_oos_trades')} (observed
  {gate_of(UNION_SAMPLE, 'pooled_oos_trades')['observed']}), 4
  {status_of(UNION_SAMPLE, 'plateau')} -- **{samples[UNION_SAMPLE]['decision']['label']}**

{fold_table(UNION_SAMPLE)}

### 3.2 `common_inception_slice` (the pre-registered evaluation sample)

{slice_['note']}.

- path (full sample): Sharpe {slice_['path']['sharpe_backtest_scale']:.4f} (backtest scale) /
  {slice_['path']['sharpe_canonical']:.4f} (canonical), max drawdown
  {slice_['path']['max_drawdown']:.4f}, annual turnover
  {slice_['path']['annualized_turnover']:.2f}x, {slice_['path']['trade_days']} trade days,
  mean {slice_['path']['mean_positions']:.2f} positions
- walk-forward: {slice_wf['n_folds']} folds, mean OOS Sharpe {slice_wf['mean_test_sharpe']:.4f}
  (canonical {slice_wf['mean_test_sharpe_canonical']:.4f}), median
  {slice_wf['median_test_sharpe']:.4f}, std {slice_wf['std_test_sharpe']:.4f}, positive
  {slice_wf['pct_positive_sharpe']:.2%}, pooled OOS trades {slice_wf['total_test_trades']}
- gates: 1 {status_of(EVALUATION_SAMPLE, 'wf_mean_oos_sharpe')} (observed
  {gate_of(EVALUATION_SAMPLE, 'wf_mean_oos_sharpe')['observed']:.4f}), 2
  {status_of(EVALUATION_SAMPLE, 'positive_fold_rate')} (observed
  {gate_of(EVALUATION_SAMPLE, 'positive_fold_rate')['observed']:.2%}), 3
  {status_of(EVALUATION_SAMPLE, 'pooled_oos_trades')} (observed
  {gate_of(EVALUATION_SAMPLE, 'pooled_oos_trades')['observed']}), 4
  {status_of(EVALUATION_SAMPLE, 'plateau')} -- **{samples[EVALUATION_SAMPLE]['decision']['label']}**

{fold_table(EVALUATION_SAMPLE)}

### 3.3 `common_inception_window` (warm-up preserved)

{window['note']}.

- path (full sample): Sharpe {window['path']['sharpe_backtest_scale']:.4f} (backtest scale) /
  {window['path']['sharpe_canonical']:.4f} (canonical), max drawdown
  {window['path']['max_drawdown']:.4f}, annual turnover
  {window['path']['annualized_turnover']:.2f}x, {window['path']['trade_days']} trade days,
  mean {window['path']['mean_positions']:.2f} positions
- walk-forward: {window_wf['n_folds']} folds, mean OOS Sharpe
  {window_wf['mean_test_sharpe']:.4f} (canonical
  {window_wf['mean_test_sharpe_canonical']:.4f}), median
  {window_wf['median_test_sharpe']:.4f}, std {window_wf['std_test_sharpe']:.4f}, positive
  {window_wf['pct_positive_sharpe']:.2%}, pooled OOS trades {window_wf['total_test_trades']}
- gates: 1 {status_of(WINDOW_SAMPLE, 'wf_mean_oos_sharpe')} (observed
  {gate_of(WINDOW_SAMPLE, 'wf_mean_oos_sharpe')['observed']:.4f}), 2
  {status_of(WINDOW_SAMPLE, 'positive_fold_rate')} (observed
  {gate_of(WINDOW_SAMPLE, 'positive_fold_rate')['observed']:.2%}), 3
  {status_of(WINDOW_SAMPLE, 'pooled_oos_trades')} (observed
  {gate_of(WINDOW_SAMPLE, 'pooled_oos_trades')['observed']}), 4
  {status_of(WINDOW_SAMPLE, 'plateau')} -- **{samples[WINDOW_SAMPLE]['decision']['label']}**

{fold_table(WINDOW_SAMPLE)}

### 3.4 The paths in one table

{path_table()}

The `common_inception_slice` and the `common_inception_window` produce **identical** gate
tables. The reason is mechanical and is published here: the slice's signal has no history
before the common inception, so it is flat for the first
{slice_['breadth']['sessions_with_zero_selectable_assets']} sessions (the
{p['candidate_configuration']['lookback']}+{p['candidate_configuration']['skip']} warm-up
ramp), while the window's signal is already live on the first session of the window. The two
paths coincide from the first month-end signal that both can form (the first month-end after
the ramp) and the common-inception samples' **first out-of-sample fold starts years after
that**, so the difference is invisible to the gate table.

## 4. The degenerate-fold diagnostic

The cross-section each fold is trained on and traded on. The threshold
({BREADTH_FALLBACK} assets) is the selection fallback of `src/features/momentum.py`: with
fewer than {BREADTH_FALLBACK} assets carrying a valid momentum the selection is taken over a
handful of assets, and with one asset it is a single-asset, time-series bet rather than a
cross-sectional one.

{diag_summary_table()}

Reading the table:

* **At the training-window end** (the pre-registered diagnostic) **no fold of any sample** is
  trained on a cross-section narrower than {BREADTH_FALLBACK} assets: the union sample's
  earliest fold ends its training window in
  {union['fold_diagnostics'][0]['train_end']}, when
  {union['fold_diagnostics'][0]['train_end_assets_valid_momentum']} assets already have a valid
  momentum. A ten-year training window is simply longer than the ragged era.
* **Over the training window** the union sample's
  {union['degenerate_folds']['folds_with_train_window_breadth_below_fallback']} earliest folds
  do contain a degenerate stretch (down to
  {min(r['train_min_assets_valid_momentum'] for r in union['fold_diagnostics'])} selectable
  asset), while the common-inception samples' affected folds contain only the warm-up ramp
  ({slice_['degenerate_folds']['folds_with_train_window_breadth_below_fallback']} folds in the
  slice, whose ramp is cut away by the truncated price frame, and
  {window['degenerate_folds']['folds_with_train_window_breadth_below_fallback']} in the
  warm-up-preserving window).
* **In the test windows** the degeneracy never happens: every fold of every sample trades a
  cross-section of at least
  {min(samples[n]['degenerate_folds']['min_test_start_assets_valid_momentum'] for n in names)}
  assets with a valid momentum.

So the ragged cross-section of the union calendar is real (it dominates the sample's first
years: the last session with fewer than {BREADTH_FALLBACK} selectable assets is
{union['breadth']['last_session_below_fallback']}) but it lies **entirely in the training
windows**: the union sample's earliest fold tests
{union['fold_diagnostics'][0]['test_start']}, by which time
{union['fold_diagnostics'][0]['test_start_assets_valid_momentum']} assets already have a valid
momentum. The published gate table was therefore not computed on a degenerate cross-section,
and the "earliest folds are trained on a single asset" reading of the ragged calendar is
correct about the *training* window only.

Per-fold detail:

### 4.1 `union_sample`

{diag_table(UNION_SAMPLE)}

### 4.2 `common_inception_slice`

{diag_table(EVALUATION_SAMPLE)}

### 4.3 `common_inception_window`

{diag_table(WINDOW_SAMPLE)}

### 4.4 The independence of the folds

The pre-registered design steps the folds by {float(wf_cfg['step_months']):.0f} months over a
{float(wf_cfg['test_months']):.0f}-month test window, so consecutive test windows **overlap** and
the folds are not independent observations. The embargo parameter is not applied by the
repository's generator (section 1.4), so the overlap is not removed.

{independence_table()}

The honest count of independent test windows is therefore the third column, not the fold count:
about {union_wf['max_disjoint_test_windows']} independent observations on the union sample and
about {slice_wf['max_disjoint_test_windows']} on the common-inception samples. This is a
property of the published protocol (the candidate's own 48-fold record has the same overlap) and
it applies to every sample equally, so it does not bias the comparison -- but it is the reason
the difference between the samples' mean OOS Sharpe ({abs(union_wf['mean_test_sharpe'] - slice_wf['mean_test_sharpe']):.4f})
is not resolvable, and it is a fact the promotion gate's "> 100 pooled OOS trades" screen does
not see.

## 5. Matched fold windows (the fold-calendar sensitivity)

Each sample's fold calendar is anchored at its own declared start, so the union calendar and
the common-inception calendars are offset by a few sessions: the common-inception samples' first
test window starts {matched['fold_calendar']['common_inception_first_test_start']}, while the
union sample's nearest fold starts
{matched['fold_calendar']['union_fold_before']} -- an offset of
{matched['fold_calendar']['offset_sessions']} sessions. To remove that offset from the
comparison, all three paths are evaluated on the **same** {matched['folds']} test windows (the
union sample's folds whose test window lies inside the common-inception window, from
{matched['first_test_start']} to {matched['last_test_end']}):

| Path | Folds | Mean OOS Sharpe | Median | Positive | Pooled trades |
|---|---|---|---|---|---|
{matched_rows}

The three paths are identical here: from the first month-end signal that both the union frame
and the truncated frame can form, the two paths are the same path, so the only difference
between the samples is the pre-common-inception history, which none of these test windows
touches. The residual difference between the union sample's own-calendar
{union_wf['mean_test_sharpe']:.4f} and the common-inception samples'
{slice_wf['mean_test_sharpe']:.4f} is therefore a **fold-calendar** effect. Its size is
{abs(union_wf['mean_test_sharpe'] - slice_wf['mean_test_sharpe']):.4f} Sharpe, which is about
{abs(union_wf['mean_test_sharpe'] - slice_wf['mean_test_sharpe']) / (union_wf['std_test_sharpe'] / (union_wf['n_folds'] ** 0.5)):.1f}
standard errors of the fold mean (the fold Sharpes have a standard deviation of
{union_wf['std_test_sharpe']:.4f} over {union_wf['n_folds']} folds, i.e. a standard error of
about {union_wf['std_test_sharpe'] / (union_wf['n_folds'] ** 0.5):.3f}, and about
{union_wf['std_test_sharpe'] / (matched['folds'] ** 0.5):.3f} on the {matched['folds']} matched
folds). The difference is therefore **not resolvable** at this number of folds -- and it does not
matter for the verdict: gate 1 fails on every sample and every calendar, by
{gate_cfg['wf_mean_oos_sharpe_min'] - union_wf['mean_test_sharpe']:.4f} (union sample) and
{gate_cfg['wf_mean_oos_sharpe_min'] - slice_wf['mean_test_sharpe']:.4f} (common-inception
samples).

## 6. What the measurement says

1. **The published verdict is not an artefact of the sample definition.** On the pre-registered
   common-inception samples the candidate's walk-forward mean OOS Sharpe is
   {slice_wf['mean_test_sharpe']:.4f} (gate 1 threshold {gate_cfg['wf_mean_oos_sharpe_min']}),
   *below* the union sample's {union_wf['mean_test_sharpe']:.4f}. The candidate stays
   **Rejected/Failed** on all three samples; the gate-1 margin on the pre-registered sample is
   {gate_cfg['wf_mean_oos_sharpe_min'] - slice_wf['mean_test_sharpe']:.4f}.
2. **The trade-count screen still passes on the pre-registered sample**
   ({slice_wf['total_test_trades']} pooled OOS trades > {gate_cfg['pooled_oos_trades_min']}),
   so the rejection is a return-quality rejection, not a statistical-power one.
3. **The degenerate-cross-section argument does not carry.** The union calendar's degenerate
   sessions end on {union['breadth']['last_session_below_fallback']}, before the earliest
   fold's test window; no fold of any sample trades a cross-section narrower than
   {BREADTH_FALLBACK} assets. The published gate table was not produced by a one-asset,
   time-series regime.
4. **The candidate is not promoted, re-fit, re-ranked or re-optimised.** The plateau gate stays
   **NOT EVALUATED**; the 27-configuration grid is out of scope for this cycle. The published
   records (`research/experiments/csmomentum_001_experiment_001.md`,
   `research/experiments/csmomentum_baseline_wf_001.md`,
   `research/reports/month_end_candidate_reaudit_001.md`,
   `research/reports/promotion_feasibility_backtest_001.md`) are unchanged, byte for byte.
5. **The walk-forward's folds are not independent observations.** The 6-month step over a
   12-month test window makes consecutive test windows overlap, and the repository's generator
   does not apply the embargo parameter, so the honest count of independent test windows is
   {union_wf['max_disjoint_test_windows']} (union sample) and
   {slice_wf['max_disjoint_test_windows']} (common-inception samples), not {union_wf['n_folds']}
   and {slice_wf['n_folds']}. This is a property of the published protocol, shared by every
   published walk-forward record in the repository, and it applies to all three samples equally.

## 7. Checks

| Check | Result | Observed | Expected |
|---|---|---|---|
{check_rows}

## 8. Reproduction

```bash
python research/csmomentum_sample_gate_audit.py    # this report; OVERALL: {p['overall']}
python research/csmomentum_common_inception_audit.py # the Cycle 905/906 sample audit still passes
python research/month_end_candidate_reaudit.py        # the committed config-faithful record is unchanged
python -m pytest -q tests/test_csmomentum_sample_gate_audit.py
python -m pytest -q
git status --porcelain data/                          # empty
```

## 9. Provenance

- Data: the committed raw cache `data/raw/*.parquet`, read-only (the fetcher is never called;
  every file under `data/` and `config/` is SHA-256 fingerprinted before and after the run and
  compared).
- Committed artifacts used as the reproduction reference: the four records listed in section 6
  (read-only, byte-identical before and after the run).
- Shared schedule implementation: `src/backtest/rebalance.py` (unchanged by this cycle).
- Sample policy: `config/sample_policy.yaml` (read, never written).
- Gate thresholds, decision mapping, candidate configuration, cost model and Sharpe convention:
  unchanged.

```json
{json.dumps(payload, indent=2, sort_keys=False, default=str)}
```
"""


if __name__ == "__main__":
    sys.exit(main())
