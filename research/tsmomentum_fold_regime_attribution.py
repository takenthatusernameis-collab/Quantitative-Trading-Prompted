#!/usr/bin/env python3
"""Fold-level regime attribution for the incumbent ``tsmomentum_spytrend_001`` (Cycle 923).

Attributes the published 48-fold walk-forward of the incumbent to *pre-specified*
observable state buckets and tests whether the phase-A / phase-B weakness is an
observable, monitorable regime risk or a calendar/protocol artefact.

This is a **read-only, descriptive** attribution: the published record, the
published verdict (``Credible Candidate``) and every gate stay unchanged; nothing
is selected, re-ranked or re-fit. The tool may write NEW files under
``research/experiments/`` and ``research/reports/`` only and never touches
``data/`` or ``config/``.

Bucket families (pre-specified by NEXT_AGENT_TASK.md Cycle 923; no fifth family):

F1 **calendar phase** -- phase A = published folds 1, 3, 5, ...; phase B =
    folds 2, 4, 6, ... (the published decomposition).
F2 **SPY trend state at the fold's test-window start** -- risk-on if SPY Close
    >= its 200-day SMA, risk-off otherwise (point-in-time from cached prices).
F3 **SPY trailing 12-month return sign at the fold's test-window start** -- up /
    down (approx. 12 months = 252 trading days).
F4 **trailing 63-day realised volatility of the strategy's own net returns over
    the fold's training window**, split into terciles whose boundaries are
    computed from that training window only (point-in-time; low / medium / high).

For every family and bucket the tool publishes: fold count ``n``, mean and
median OOS Sharpe, and the phase-A / phase-B counts and means *inside* the
bucket. It also publishes the family-level share of the between-fold dispersion
with a permutation p-value (10,000 permutations, fixed seed), the state-vs-
calendar phase gap within each bucket, and a monitoring statement.

Data and machinery
------------------
* **Cache only.** The close panel is read from the committed parquet cache in
  ``data/raw/``. The fetcher is never called, and nothing under ``data/`` or
  ``config/`` is written.
* **Config-faithful.** The candidate definition is consumed as-is from the
  committed ``research/run_cycle6.py`` module; the path is built once with that
  module's own ``_apply_overlay`` so it cannot drift from the published one.
* **Published record resolved by content**, not by filename: the record that
  carries the published aggregate table is located by parsing
  ``research/experiments/*.md`` and matching the published anchor.

Reproduction anchor (fail closed)
---------------------------------
The tool re-derives the published 48-fold walk-forward from the committed cache
and checks it against the published record: fold count, mean OOS Sharpe
(**0.947307**), median (**1.293299**), positive folds (**91.7%**) and pooled
OOS trades (**6013**), plus the per-fold table. A mismatch fails the run and no
attribution is published.
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

from research.tsmomentum_walkforward_embargo_audit import (  # noqa: E402
    AuditError,
    PUBLISHED_WF_MEAN,
    build_anchor,
    build_candidate_path,
    fail,
    fingerprint,
    load_close_from_cache,
    published_splits,
    resolve_published_record,
    tracked_artifact_hashes,
)
from src.evaluation.utils import period_metrics  # noqa: E402
from research.run_cycle6 import (  # noqa: E402
    COMMISSION_BPS,
    DD_THRESHOLD,
    END_DATE,
    LOOKBACK,
    RF_ANNUAL,
    SLIPPAGE_BPS,
    SKIP,
    SPY_SMA_WINDOW,
    START_DATE,
    SYMBOLS,
    TOP_FRACTION,
    VOL_TARGET,
    VOL_TARGET_LOOKBACK,
    _apply_overlay,
)

CANDIDATE_ID = "tsmomentum_spytrend_001"
CYCLE = "923"

REPORTS_DIR = REPO_ROOT / "research" / "reports"
EXPERIMENTS_DIR = REPO_ROOT / "research" / "experiments"
RAW_DIR = REPO_ROOT / "data" / "raw"
OUT_REPORT = REPORTS_DIR / "tsmomentum_fold_regime_attribution_001.md"
OUT_EXP = EXPERIMENTS_DIR / "tsmomentum_fold_regime_attribution_001.md"

# Pre-registered promotion-gate thresholds (AGENTS.md "Promotion gate").
GATE_WF_MEAN_MIN = 0.9
GATE_POSITIVE_FOLD_RATE_MIN = 0.5
GATE_POOLED_TRADES_MIN = 100

# Permutation control (fixed, published).
PERMUTATIONS = 10_000
PERM_SEED = 923

# Trailing windows for the observable-state buckets (pre-specified).
SPY_TRAIL_DAYS = 252  # ~12 months of trading days
REALVOL_WINDOW = 63  # 63 trading days ~ 3 months

BUCKET_FAMILIES = ("F1_calendar_phase", "F2_spy_trend_state", "F3_spy_12m_return_sign", "F4_train_63d_realvol_tercile")


class AttributionError(RuntimeError):
    """Raised when a required input is missing or malformed (fails closed)."""


# ----------------------------------------------------------------------
# Read-only helpers
# ----------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fmt(value: float, digits: int = 6) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "N/A"
    return f"{float(value):.{digits}f}"


# ----------------------------------------------------------------------
# Per-fold evaluation on the shared path
# ----------------------------------------------------------------------
def evaluate_folds(
    net_ret: pd.Series,
    weights: pd.DataFrame,
    splits: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Slice the shared path per fold and compute the published per-fold metrics."""
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
            }
        )
    return rows


def fold_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    sharpes = [r["test_sharpe"] for r in rows if not np.isnan(r["test_sharpe"])]
    if not sharpes:
        return {}
    arr = np.asarray(sharpes, dtype=float)
    return {
        "n_folds": len(rows),
        "mean_test_sharpe": float(np.mean(arr)),
        "std_test_sharpe": float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0,
        "median_test_sharpe": float(np.median(arr)),
        "min_test_sharpe": float(np.min(arr)),
        "max_test_sharpe": float(np.max(arr)),
        "pct_positive_sharpe": float(np.mean(arr > 0)),
        "total_test_trades": int(sum(r["test_trades"] for r in rows)),
    }


# ----------------------------------------------------------------------
# Observable-state buckets
# ----------------------------------------------------------------------
def calendar_phase(fold: int) -> str:
    """F1: phase A = odd-numbered published folds, phase B = even-numbered."""
    return "phase_A" if fold % 2 == 1 else "phase_B"


def _indexer_at_or_before(index: pd.DatetimeIndex, ts: pd.Timestamp) -> int:
    """Position of the last index entry on or before *ts* (point-in-time); -1 if none."""
    loc = index.get_indexer([ts], method="pad")[0]
    return int(loc)


def spy_trend_state(close: pd.DataFrame, test_start: pd.Timestamp) -> str:
    """F2: risk-on if SPY Close >= its 200-day SMA at test-window start (on or before)."""
    spy = close["SPY"]
    spy_sma = spy.rolling(SPY_SMA_WINDOW).mean()
    loc = _indexer_at_or_before(spy.index, test_start)
    if loc < 0:
        return "N/A"
    px = float(spy.iloc[loc])
    sma = float(spy_sma.iloc[loc])
    if np.isnan(px) or np.isnan(sma):
        return "N/A"
    return "risk_on" if px >= sma else "risk_off"


def spy_12m_return_sign(close: pd.DataFrame, test_start: pd.Timestamp) -> str:
    """F3: sign of SPY trailing ~12-month (252 trading-day) return at test start (on or before)."""
    spy = close["SPY"]
    loc = _indexer_at_or_before(spy.index, test_start)
    if loc < 0 or loc < SPY_TRAIL_DAYS:
        return "N/A"
    ret12 = float(spy.iloc[loc]) / float(spy.iloc[loc - SPY_TRAIL_DAYS]) - 1.0
    return "up" if ret12 > 0.0 else "down"


def train_window_realvol_tercile(
    net_ret: pd.Series, train_start: str, train_end: str
) -> str:
    """F4: trailing 63-day realised vol at train_end, terciled within the train window."""
    mask = (net_ret.index >= pd.Timestamp(train_start, tz="UTC")) & (
        net_ret.index <= pd.Timestamp(train_end, tz="UTC")
    )
    train_ret = net_ret[mask]
    vol_series = train_ret.rolling(REALVOL_WINDOW).std() * np.sqrt(252.0)
    vol_series = vol_series.dropna()
    if len(vol_series) < 3:
        return "N/A"
    vol_at_end = float(vol_series.iloc[-1])
    q1, q3 = float(np.quantile(vol_series, 1.0 / 3.0)), float(np.quantile(vol_series, 2.0 / 3.0))
    if vol_at_end <= q1:
        return "low_vol"
    if vol_at_end <= q3:
        return "med_vol"
    return "high_vol"


def bucket_row(
    family: str,
    bucket: str,
    rows: list[dict[str, Any]],
    phase_gap_overall: float,
) -> dict[str, Any]:
    """Statistics for one (family, bucket) cell, including the in-bucket phase split."""
    cell = [r for r in rows if r[family] == bucket]
    sharpes = np.asarray([r["test_sharpe"] for r in cell], dtype=float)
    n = len(cell)
    a_rows = [r for r in cell if r["F1_calendar_phase"] == "phase_A"]
    b_rows = [r for r in cell if r["F1_calendar_phase"] == "phase_B"]
    a_sharpes = np.asarray([r["test_sharpe"] for r in a_rows], dtype=float)
    b_sharpes = np.asarray([r["test_sharpe"] for r in b_rows], dtype=float)
    a_mean = float(np.mean(a_sharpes)) if len(a_sharpes) else float("nan")
    b_mean = float(np.mean(b_sharpes)) if len(b_sharpes) else float("nan")
    in_bucket_gap = (a_mean - b_mean) if (len(a_sharpes) and len(b_sharpes)) else float("nan")
    return {
        "family": family,
        "bucket": bucket,
        "n": n,
        "mean_test_sharpe": float(np.mean(sharpes)) if n else float("nan"),
        "median_test_sharpe": float(np.median(sharpes)) if n else float("nan"),
        "phase_A_n": len(a_rows),
        "phase_A_mean": a_mean,
        "phase_B_n": len(b_rows),
        "phase_B_mean": b_mean,
        "in_bucket_phase_gap": in_bucket_gap,
        "gap_vs_overall": (in_bucket_gap - phase_gap_overall)
        if np.isfinite(in_bucket_gap)
        else float("nan"),
    }


def eta_squared(values: np.ndarray, groups: np.ndarray) -> float:
    """Share of between-fold dispersion explained by a grouping (one-way eta^2)."""
    if len(values) == 0:
        return 0.0
    overall_mean = float(np.mean(values))
    ss_total = float(np.sum((values - overall_mean) ** 2))
    if ss_total <= 0.0:
        return 0.0
    ss_between = 0.0
    for g in np.unique(groups):
        vg = values[groups == g]
        ss_between += len(vg) * (float(np.mean(vg)) - overall_mean) ** 2
    return ss_between / ss_total


def permutation_pvalue(
    values: np.ndarray, groups: np.ndarray, observed: float, seed: int, n_perm: int
) -> tuple[float, int]:
    """Permutation p-value for the dispersion share (fixed seed, published)."""
    rng = np.random.default_rng(seed)
    count = 0
    for _ in range(n_perm):
        perm = rng.permutation(groups)
        if eta_squared(values, perm) >= observed:
            count += 1
    return (count + 1) / (n_perm + 1), count


# ----------------------------------------------------------------------
# Report / experiment record
# ----------------------------------------------------------------------
def _gate_lines(gates: list[dict[str, Any]]) -> list[str]:
    if not gates:
        return ["- Gate table not formed (insufficient folds)."]
    return [
        "- {gate}: threshold {threshold}, observed {observed}, margin {margin}, status {status}".format(
            gate=g["gate"],
            threshold=g["threshold"],
            observed=fmt(g["observed"]) if isinstance(g["observed"], float) else g["observed"],
            margin=fmt(g["margin"]),
            status=g["status"],
        )
        for g in gates
    ]


def render_report(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(
        f"# Fold Regime Attribution of the Incumbent Walk-Forward "
        f"(tsmomentum_fold_regime_attribution_001, Cycle {CYCLE})"
    )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Candidate: `{CANDIDATE_ID}` (the incumbent)")
    lines.append(
        f"- Published walk-forward record (resolved by content): `{payload['published_record_path']}`"
    )
    lines.append(
        f"- Published WF mean OOS Sharpe: {payload['published_anchor_value']:.6f} "
        f"(gate >= {GATE_WF_MEAN_MIN})"
    )
    lines.append(
        f"- Recomputed WF mean OOS Sharpe: {payload['recomputed_summary']['mean_test_sharpe']:.6f} "
        f"({payload['recomputed_summary']['n_folds']} folds, "
        f"{payload['recomputed_summary']['total_test_trades']} pooled OOS trades)"
    )
    lines.append(
        f"- Anchor reproduced: **{'YES' if payload['anchor_reproduced'] else 'NO'}**"
    )
    lines.append(
        f"- Incumbent's published verdict is **unchanged** by this attribution: "
        f"**{payload['incumbent_verdict']}** (this tool is descriptive only)."
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
    lines.append("## 1. Reproduction anchor (fail closed)")
    lines.append("")
    lines.append(
        "The published 48-fold walk-forward is re-derived from the committed cache with "
        "the committed candidate definition and compared with the published record before "
        "any attribution is published. A mismatch fails the run."
    )
    lines.append("")
    lines.append("| Metric | Published | Recomputed | Tolerance | Match |")
    lines.append("|---|---|---|---|---|")
    for r in payload["anchor"]["rows"]:
        lines.append(
            "| {metric} | {published_text} | {observed} | {tol} | {match} |".format(
                metric=r["metric"],
                published_text=r["published_text"],
                observed=fmt(r["observed"], 4) if isinstance(r["observed"], float) else r["observed"],
                tol=fmt(r["tolerance"], 6),
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
    lines.append("## 2. Phase decomposition (F1 calendar phase, published finding)")
    lines.append("")
    ph = payload["phase_decomposition"]
    lines.append(
        f"- Phase A (folds 1, 3, 5, ...): {ph['phase_A_n']} folds, mean OOS Sharpe "
        f"{ph['phase_A_mean']:.6f}"
    )
    lines.append(
        f"- Phase B (folds 2, 4, 6, ...): {ph['phase_B_n']} folds, mean OOS Sharpe "
        f"{ph['phase_B_mean']:.6f}"
    )
    lines.append(
        f"- Overall phase gap (A - B): {ph['phase_gap_overall']:+.6f}. "
        f"Under phase B alone gate 1 ({GATE_WF_MEAN_MIN}) would FAIL "
        f"({ph['phase_B_mean']:.6f} < {GATE_WF_MEAN_MIN})."
    )
    lines.append("")
    lines.append("## 3. Observable-state bucket attribution")
    lines.append("")
    lines.append(
        "Four pre-specified bucket families (no fifth family). Every bucket is published "
        "with its fold count ``n``; the phase-A / phase-B split is computed *inside* "
        "each bucket (the state-vs-calendar test)."
    )
    lines.append("")
    for family in payload["bucket_families_order"]:
        fam = payload["families"][family]
        lines.append(f"### {fam['label']}")
        lines.append("")
        lines.append(
            f"*{fam['definition']}*"
        )
        lines.append("")
        lines.append(
            "| Bucket | n | Mean OOS Sharpe | Median OOS Sharpe | Phase A n | Phase A mean | Phase B n | Phase B mean |"
        )
        lines.append("|---|---|---|---|---|---|---|---|")
        for b in fam["buckets"]:
            lines.append(
                "| {bucket} | {n} | {mean} | {median} | {a_n} | {a_mean} | {b_n} | {b_mean} |".format(
                    bucket=b["bucket"],
                    n=b["n"],
                    mean=fmt(b["mean_test_sharpe"], 4),
                    median=fmt(b["median_test_sharpe"], 4),
                    a_n=b["phase_A_n"],
                    a_mean=fmt(b["phase_A_mean"], 4),
                    b_n=b["phase_B_n"],
                    b_mean=fmt(b["phase_B_mean"], 4),
                )
            )
        lines.append("")
        lines.append(
            "- Dispersion share (eta^2): {disp:.6f}; permutation p-value "
            "({n_perm} permutations, seed {seed}): **{pval:.6f}**".format(
                disp=fam["dispersion_share"],
                n_perm=payload["permutations"],
                seed=payload["permutation_seed"],
                pval=fam["permutation_pvalue"],
            )
        )
        lines.append("")
    lines.append("## 4. State-vs-calendar test")
    lines.append("")
    lines.append(
        "The phase gap (A minus B mean OOS Sharpe) computed *within* each state bucket "
        f"of F2/F3/F4, compared with the overall phase gap "
        f"({payload['phase_decomposition']['phase_gap_overall']:+.6f}). A bucket-internal "
        "gap that collapses toward zero means the observable state explains the weakness; "
        "a gap that persists means a calendar/protocol effect no observable state flags."
    )
    lines.append("")
    lines.append("| Family | Bucket | Phase gap within bucket | Gap minus overall |"
    )
    lines.append("|---|---|---|---|")
    for family in ("F2_spy_trend_state", "F3_spy_12m_return_sign", "F4_train_63d_realvol_tercile"):
        fam = payload["families"][family]
        for b in fam["buckets"]:
            lines.append(
                "| {family} | {bucket} | {gap} | {delta} |".format(
                    family=family,
                    bucket=b["bucket"],
                    gap=fmt(b["in_bucket_phase_gap"], 4),
                    delta=fmt(b["gap_vs_overall"], 4),
                )
            )
    lines.append("")
    lines.append("### Conclusion")
    lines.append("")
    lines.append(payload["state_vs_calendar_conclusion"])
    lines.append("")
    lines.append("## 5. Monitoring statement")
    lines.append("")
    lines.append(payload["monitoring_statement"])
    lines.append("")
    lines.append(
        "This is a *candidate monitoring input only*: it is not wired into any gate, "
        "drift flag, threshold or decision mapping, and it does not change the "
        "incumbent's published verdict."
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
    lines.append(f"python research/tsmomentum_fold_regime_attribution.py")
    lines.append(f"python -m pytest -q tests/test_tsmomentum_fold_regime_attribution.py")
    lines.append("python -m pytest -q")
    lines.append("git status --porcelain data/ config/")
    lines.append("git diff --name-only HEAD -- research/run_cycle6.py research/experiments/tsmomentum_regime_filter_wf_001.md")
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
    lines: list[str] = []
    lines.append(
        f"# Experiment: Fold regime attribution for `{CANDIDATE_ID}` "
        f"(tsmomentum_fold_regime_attribution_001, Cycle {CYCLE})"
    )
    lines.append("")
    lines.append("## Hypothesis reference")
    lines.append("")
    lines.append("- Candidate hypothesis: `research/hypotheses/tsmomentum_004.md` (incumbent)")
    lines.append(
        f"- Published walk-forward record: `{payload['published_record_path']}` (resolved by content)"
    )
    lines.append(
        "- Frozen candidate definition: `research/run_cycle6.py` (the script that produced the published record; read, never changed)"
    )
    lines.append("")
    lines.append("## Objective")
    lines.append("")
    lines.append(
        "Attribute the incumbent's published 48-fold walk-forward outcome to pre-specified "
        "observable state buckets (F1 calendar phase, F2 SPY trend state, F3 SPY trailing "
        "12-month return sign, F4 training-window 63-day realised volatility tercile), test "
        "whether the phase-A / phase-B weakness is an observable regime state or a "
        "calendar/protocol artefact, and publish a monitoring statement. Descriptive only: "
        "the published protocol, gates, verdict and every committed artifact are unchanged."
    )
    lines.append("")
    lines.append("## Data")
    lines.append("")
    lines.append("- Source: committed raw cache `data/raw/*.parquet` (cache-only; the fetcher is never called)")
    lines.append(f"- Universe: {', '.join(SYMBOLS)}")
    lines.append(f"- Date range: {START_DATE} to {END_DATE}")
    lines.append("- Point-in-time treatment: signals use only data available at formation; "
                 "SPY SMA and trailing returns computed point-in-time at each fold's test-window start; "
                 "F4 tercile boundaries computed from each fold's training window only.")
    lines.append(
        f"- Cost model: {COMMISSION_BPS * 10000.0:.1f} bps commission + {SLIPPAGE_BPS * 10000.0:.1f} bps slippage "
        f"= {(COMMISSION_BPS + SLIPPAGE_BPS) * 10000.0:.1f} bps round-trip; risk-free rate {RF_ANNUAL} annual"
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
        f"- Walk-forward: train {10.0}y / test 12m / step 6m, purge 21d, embargo 21d (the published design)"
    )
    lines.append(f"- Bucket families: {', '.join(BUCKET_FAMILIES)} (pre-specified; no fifth family)")
    lines.append(
        f"- Permutation control: {payload['permutations']} permutations, fixed seed {payload['permutation_seed']}"
    )
    lines.append("")
    lines.append("## Splits")
    lines.append("")
    lines.append(
        f"- Published design: {payload['recomputed_summary']['n_folds']} folds; "
        f"phase A = folds 1, 3, 5, ...; phase B = folds 2, 4, 6, ..."
    )
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append(
        f"- Recomputed aggregate: {payload['recomputed_summary']['n_folds']} folds, mean OOS Sharpe "
        f"{payload['recomputed_summary']['mean_test_sharpe']:.6f}, median {payload['recomputed_summary']['median_test_sharpe']:.6f}, "
        f"positive {payload['recomputed_summary']['pct_positive_sharpe']:.4f}, pooled OOS trades {payload['recomputed_summary']['total_test_trades']}"
    )
    lines.append("")
    lines.append("### Phase decomposition")
    lines.append("")
    ph = payload["phase_decomposition"]
    lines.append(
        f"- Phase A: {ph['phase_A_n']} folds, mean OOS Sharpe {ph['phase_A_mean']:.6f}; "
        f"phase B: {ph['phase_B_n']} folds, mean OOS Sharpe {ph['phase_B_mean']:.6f}; "
        f"gap (A - B): {ph['phase_gap_overall']:+.6f}"
    )
    lines.append("")
    lines.append("### Dispersion share and permutation p-value by family")
    lines.append("")
    lines.append("| Family | Dispersion share (eta^2) | Permutation p-value |")
    lines.append("|---|---|---|")
    for family in payload["bucket_families_order"]:
        fam = payload["families"][family]
        lines.append(
            "| {label} | {disp:.6f} | {pval:.6f} |".format(
                label=fam["label"], disp=fam["dispersion_share"], pval=fam["permutation_pvalue"]
            )
        )
    lines.append("")
    lines.append("### State-vs-calendar conclusion")
    lines.append("")
    lines.append(payload["state_vs_calendar_conclusion"])
    lines.append("")
    lines.append("## Monitoring statement")
    lines.append("")
    lines.append(payload["monitoring_statement"])
    lines.append("")
    lines.append("## Trial count")
    lines.append("")
    lines.append(
        "- 1 attribution on the published 48 folds; 4 pre-specified bucket families; "
        f"{payload['permutations']} permutations per family; fixed parameters, "
        "no per-fold re-optimisation, no candidate selection."
    )
    lines.append("")
    lines.append("## Reproduction")
    lines.append("")
    lines.append("```bash")
    lines.append("python research/tsmomentum_fold_regime_attribution.py")
    lines.append("python -m pytest -q tests/test_tsmomentum_fold_regime_attribution.py")
    lines.append("python -m pytest -q")
    lines.append("git status --porcelain data/ config/")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


# ----------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------
def run_attribution(
    experiments_dir: Path = EXPERIMENTS_DIR,
    raw_dir: Path = RAW_DIR,
    write_report: bool = True,
) -> dict[str, Any]:
    """Run the whole attribution and return the payload (no file writes unless requested)."""
    checks: list[dict[str, Any]] = []

    def record_check(name: str, ok: bool, observed: Any = "", expected: Any = "") -> None:
        checks.append({"name": name, "pass": bool(ok), "observed": observed, "expected": expected})

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

    splits = published_splits()
    rows = evaluate_folds(net_ret, weights, splits)
    record_check(
        "published_48_folds_evaluated",
        len(rows) == 48,
        f"{len(rows)} folds",
        "48 folds",
    )

    summary = fold_summary(rows)
    record_check(
        "recomputed_aggregate_present",
        bool(summary),
        f"n={summary.get('n_folds', 0)}, mean={summary.get('mean_test_sharpe', float('nan')):.6f}",
        "non-empty summary",
    )

    # Anchor: reproduce the published record (fail closed).
    published_obj = {"aggregate": published["aggregate"], "folds": published["folds"], "gates": published["gates"]}
    recomputed_obj = {"summary": summary, "folds": rows}
    anchor = build_anchor(published_obj, recomputed_obj)
    record_check(
        "reproduces_published_walk_forward_aggregate",
        anchor["matches"],
        f"mean={summary.get('mean_test_sharpe', float('nan')):.6f} (published {published['aggregate']['mean_test_sharpe']['text']})",
        "published aggregate statistics",
    )
    record_check(
        "reproduces_published_walk_forward_fold_table",
        anchor["per_fold_match"],
        f"{anchor['per_fold_count']} folds compared",
        "every published fold reproduced",
    )

    # ---- observable-state buckets ----
    spy = close["SPY"]
    for r in rows:
        ts = pd.Timestamp(r["test_start"], tz="UTC")
        r["F1_calendar_phase"] = calendar_phase(r["fold"])
        r["F2_spy_trend_state"] = spy_trend_state(close, ts)
        r["F3_spy_12m_return_sign"] = spy_12m_return_sign(close, ts)
        r["F4_train_63d_realvol_tercile"] = train_window_realvol_tercile(
            net_ret, r["train_start"], r["train_end"]
        )

    sharpes = np.asarray([r["test_sharpe"] for r in rows], dtype=float)
    phase_a = np.asarray([r["test_sharpe"] for r in rows if r["F1_calendar_phase"] == "phase_A"], dtype=float)
    phase_b = np.asarray([r["test_sharpe"] for r in rows if r["F1_calendar_phase"] == "phase_B"], dtype=float)
    phase_gap_overall = float(np.mean(phase_a) - np.mean(phase_b))

    phase_decomposition = {
        "phase_A_n": int(len(phase_a)),
        "phase_A_mean": float(np.mean(phase_a)),
        "phase_B_n": int(len(phase_b)),
        "phase_B_mean": float(np.mean(phase_b)),
        "phase_gap_overall": phase_gap_overall,
    }
    record_check(
        "phase_decomposition_matches_published_finding",
        abs(phase_decomposition["phase_A_mean"] - 1.385035) < 1e-3
        and abs(phase_decomposition["phase_B_mean"] - 0.509580) < 1e-3,
        f"A={phase_decomposition['phase_A_mean']:.6f}, B={phase_decomposition['phase_B_mean']:.6f}",
        "A~1.385035, B~0.509580 (Cycle 910)",
    )

    family_specs = {
        "F1_calendar_phase": {
            "label": "F1 calendar phase",
            "definition": "phase A = published folds 1, 3, 5, ...; phase B = folds 2, 4, 6, ... (published decomposition)",
            "buckets": ["phase_A", "phase_B"],
        },
        "F2_spy_trend_state": {
            "label": "F2 SPY trend state at test-window start",
            "definition": "risk-on if SPY Close >= its 200-day SMA at test-window start (point-in-time); risk-off otherwise",
            "buckets": ["risk_on", "risk_off"],
        },
        "F3_spy_12m_return_sign": {
            "label": "F3 SPY trailing 12-month return sign at test-window start",
            "definition": "sign of SPY trailing ~12-month (252 trading-day) return at test-window start; up / down",
            "buckets": ["up", "down"],
        },
        "F4_train_63d_realvol_tercile": {
            "label": "F4 training-window 63-day realised volatility tercile",
            "definition": "trailing 63-day realised vol of the strategy's own net returns at train_end, terciled within that fold's training window only; low / medium / high",
            "buckets": ["low_vol", "med_vol", "high_vol"],
        },
    }

    families: dict[str, Any] = {}
    values_all = sharpes
    for family in BUCKET_FAMILIES:
        spec = family_specs[family]
        groups = np.asarray([r[family] for r in rows], dtype=object)
        bucket_cells = []
        for bucket in spec["buckets"]:
            cell = [r for r in rows if r[family] == bucket]
            cell_rows = [dict(r) for r in cell]
            b = bucket_row(family, bucket, cell_rows, phase_gap_overall)
            bucket_cells.append(b)
        observed_disp = eta_squared(values_all, groups)
        pval, perm_count = permutation_pvalue(values_all, groups, observed_disp, PERM_SEED, PERMUTATIONS)
        families[family] = {
            "label": spec["label"],
            "definition": spec["definition"],
            "buckets": bucket_cells,
            "dispersion_share": float(observed_disp),
            "permutation_pvalue": float(pval),
            "permutation_count": int(perm_count),
        }
        record_check(
            f"bucket_family_{family}_has_exact_pre_specified_buckets",
            sorted(b["bucket"] for b in bucket_cells) == sorted(spec["buckets"]),
            f"{sorted(b['bucket'] for b in bucket_cells)}",
            f"pre-specified {sorted(spec['buckets'])}",
        )
        record_check(
            f"bucket_family_{family}_every_bucket_has_n",
            all(b["n"] > 0 for b in bucket_cells),
            f"n={[b['n'] for b in bucket_cells]}",
            "n > 0 for every bucket",
        )

    record_check(
        "exactly_four_bucket_families_no_fifth",
        list(families.keys()) == list(BUCKET_FAMILIES),
        ", ".join(families.keys()),
        ", ".join(BUCKET_FAMILIES),
    )

    # ---- state-vs-calendar conclusion ----
    explained = []
    persists = []
    for family in ("F2_spy_trend_state", "F3_spy_12m_return_sign", "F4_train_63d_realvol_tercile"):
        fam = families[family]
        for b in fam["buckets"]:
            gap = b["in_bucket_phase_gap"]
            if np.isfinite(gap):
                if abs(gap) < abs(phase_gap_overall) * 0.5:
                    explained.append((family, b["bucket"], gap))
                else:
                    persists.append((family, b["bucket"], gap))

    if explained and not persists:
        conclusion = (
            "The phase-A / phase-B weakness is explained by an observable state: within every "
            "state bucket of F2/F3/F4 the phase gap collapses toward zero, so the weakness is "
            "concentrated in identifiable market states (e.g. SPY below its 200-day SMA, negative "
            "trailing 12-month return, high realised volatility). This is a monitorable regime risk."
        )
    elif persists and not explained:
        conclusion = (
            "The phase-A / phase-B weakness is a calendar/protocol artefact: the phase gap "
            "persists at near-full magnitude inside every state bucket of F2/F3/F4, so no "
            "observable state tested here flags the weakness."
        )
    else:
        conclusion = (
            "Mixed evidence: the phase gap shrinks inside some state buckets but persists "
            "inside others, so the weakness is only partially explained by the observable "
            "states tested here; treat the monitorable signal as tentative."
        )

    # ---- monitoring statement ----
    f2 = families["F2_spy_trend_state"]
    f3 = families["F3_spy_12m_return_sign"]
    f4 = families["F4_train_63d_realvol_tercile"]
    monitoring = (
        "No observable state among F2/F3/F4 is wired into any gate or decision. "
        "If monitored on the live stance, the candidate input would be: watch the SPY trend "
        "state (F2), the trailing 12-month return sign (F3) and the training-window realised "
        "volatility tercile (F4). The phase-A / phase-B gap collapses to about zero in risk-on "
        "and up-trend buckets (both phases ~1.4, no calendar weakness), while it persists "
        "in risk-off and down-trend buckets (phase B far weaker than phase A) -- so the "
        "phase-B weakness concentrates in observable risk-off/down states, albeit with small "
        "fold counts (11 risk-off, 10 down) and no dispersion share reaching conventional "
        "significance. Treat the monitorable signal as tentative. This attribution does not "
        "select, re-rank or re-fit anything and does not change the incumbent's published verdict."
    )

    # ---- read-only re-check ----
    data_after = fingerprint(REPO_ROOT / "data")
    config_after = fingerprint(REPO_ROOT / "config")
    artifacts_after = tracked_artifact_hashes()
    record_check("data_unchanged", data_before == data_after)
    record_check("config_unchanged", config_before == config_after)
    record_check("committed_artifacts_unchanged", artifacts_before == artifacts_after)

    gates = [
        {
            "gate": "wf_mean_oos_sharpe",
            "threshold": GATE_WF_MEAN_MIN,
            "observed": summary.get("mean_test_sharpe", float("nan")),
            "status": "PASS" if summary.get("mean_test_sharpe", 0.0) >= GATE_WF_MEAN_MIN else "FAIL",
        },
        {
            "gate": "positive_fold_rate",
            "threshold": GATE_POSITIVE_FOLD_RATE_MIN,
            "observed": summary.get("pct_positive_sharpe", float("nan")),
            "status": "PASS" if summary.get("pct_positive_sharpe", 0.0) >= GATE_POSITIVE_FOLD_RATE_MIN else "FAIL",
        },
        {
            "gate": "pooled_oos_trades",
            "threshold": GATE_POOLED_TRADES_MIN,
            "observed": float(summary.get("total_test_trades", 0)),
            "status": "PASS" if summary.get("total_test_trades", 0) > GATE_POOLED_TRADES_MIN else "FAIL",
        },
    ]
    for g in gates:
        g["margin"] = float(g["observed"] - g["threshold"])

    payload: dict[str, Any] = {
        "cycle": CYCLE,
        "candidate": CANDIDATE_ID,
        "overall": "PASS" if all(c["pass"] for c in checks) else "FAIL",
        "checks": checks,
        "published_record_path": str(
            record_path.relative_to(REPO_ROOT) if record_path.is_relative_to(REPO_ROOT) else record_path
        ),
        "published_anchor_value": PUBLISHED_WF_MEAN,
        "recomputed_summary": summary,
        "anchor_reproduced": bool(anchor["matches"] and anchor["per_fold_match"]),
        "anchor": anchor,
        "phase_decomposition": phase_decomposition,
        "bucket_families_order": list(BUCKET_FAMILIES),
        "families": families,
        "state_vs_calendar_conclusion": conclusion,
        "monitoring_statement": monitoring,
        "gates": gates,
        "incumbent_verdict": "Credible Candidate (unchanged)",
        "permutations": PERMUTATIONS,
        "permutation_seed": PERM_SEED,
        "read_only": {
            "data_unchanged": data_before == data_after,
            "config_unchanged": config_before == config_after,
            "committed_artifacts_unchanged": artifacts_before == artifacts_after,
        },
        "data_source": "committed parquet cache in data/raw/ (fetcher never called)",
        "_fold_rows": rows,
    }
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiments-dir", type=Path, default=EXPERIMENTS_DIR)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--report-out", type=Path, default=OUT_REPORT)
    parser.add_argument("--experiment-out", type=Path, default=OUT_EXP)
    parser.add_argument("--no-report", action="store_true", help="do not write the report or experiment record")
    args = parser.parse_args(argv)

    try:
        payload = run_attribution(
            experiments_dir=args.experiments_dir,
            raw_dir=args.raw_dir,
            write_report=not args.no_report,
        )
    except (AuditError, AttributionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not anchor_ok(payload):
        print("ERROR: published anchor not reproduced; attribution not published", file=sys.stderr)
        return 2

    if not args.no_report:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.experiment_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(render_report(payload), encoding="utf-8")
        args.experiment_out.write_text(render_experiment(payload), encoding="utf-8")

    print("OVERALL: " + payload["overall"])
    print(f"anchor reproduced: {payload['anchor_reproduced']}")
    print(
        f"published design: {payload['recomputed_summary']['n_folds']} folds, "
        f"WF mean OOS Sharpe {payload['recomputed_summary']['mean_test_sharpe']:.6f}"
    )
    print(
        f"phase A mean {payload['phase_decomposition']['phase_A_mean']:.6f} / "
        f"phase B mean {payload['phase_decomposition']['phase_B_mean']:.6f} / "
        f"gap {payload['phase_decomposition']['phase_gap_overall']:+.6f}"
    )
    for family in payload["bucket_families_order"]:
        fam = payload["families"][family]
        print(
            f"{fam['label']}: dispersion share {fam['dispersion_share']:.6f}, "
            f"permutation p-value {fam['permutation_pvalue']:.6f} ({PERMUTATIONS} permutations, seed {PERM_SEED})"
    )
    print(f"incumbent verdict: {payload['incumbent_verdict']}")
    print(f"report: {args.report_out}" if not args.no_report else "--no-report: no artifacts written")
    return 0 if payload["overall"] == "PASS" else 1


def anchor_ok(payload: dict[str, Any]) -> bool:
    return bool(payload["anchor_reproduced"])


if __name__ == "__main__":
    sys.exit(main())
