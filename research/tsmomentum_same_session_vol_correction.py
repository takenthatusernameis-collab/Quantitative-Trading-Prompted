#!/usr/bin/env python3
"""Same-session volatility estimate: opt-in correction and side-by-side re-derivation
for the incumbent ``tsmomentum_spytrend_001`` (Cycle 926).

Cycle 925 found and quantified a **measurement defect**: the committed
volatility target sets session *t*'s exposure from a realised-volatility
estimate whose trailing 63-session window **includes session t itself**
(same-session feedback).  It is present in the published research path
(``research/run_cycle6.py::_apply_overlay``), in the shared simulation /
live paper-trading path (``src/simulation/engine.py::_target_weights``) and in
both overlay helpers of ``src/evaluation/risk.py``.

This cycle does two things and nothing else:

1. It makes the corrected estimate (volatility computed from sessions up to
   and including *t-1*) reachable through an explicit **opt-in, default-off**
   switch (``lag_vol_estimate``) that is available in all three code paths.
   The default path is **bit-identical** to the pre-change implementation.
2. It **re-derives** the incumbent's published record on the corrected path
   and publishes the result **side by side** with the published values, in
   **new** artifacts only.

What it is **not**: a fix, a promotion, a recovery or a new edge.  The
incumbent's published verdict (**Credible Candidate**) and its promotion
decision (**NO-GO**) are unchanged, the published walk-forward record and the
committed paper-trading state are **not** overwritten, and no gate, threshold,
universe, cost model, Sharpe convention, hypothesis or drift flag is touched.
``data/`` and ``config/`` are read-only and the fetcher is never called.

Usage::

    python research/tsmomentum_same_session_vol_correction.py
    python research/tsmomentum_same_session_vol_correction.py --no-report
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

from research.run_cycle6 import (  # noqa: E402  (committed candidate definition)
    COMMISSION_BPS,
    DD_THRESHOLD,
    SLIPPAGE_BPS,
    SPY_SMA_WINDOW,
    SYMBOLS,
    TOP_FRACTION,
    LOOKBACK,
    SKIP,
    VOL_TARGET,
    VOL_TARGET_LOOKBACK,
    _apply_overlay,
    _eval_candidate,
)
from research.tsmomentum_walkforward_embargo_audit import (  # noqa: E402
    evaluate_design,
    fingerprint,
    load_close_from_cache,
    published_splits,
    resolve_published_record,
    tracked_artifact_hashes,
)
from src.backtest.engine import compute_metrics  # noqa: E402
from src.evaluation.risk import (  # noqa: E402
    combined_risk_overlay,
    realized_vol_scale,
    volatility_target_overlay,
)
from src.evaluation.sharpe import SHARPE_CONVENTION_ID, sharpe_ratio  # noqa: E402
from src.evaluation.statistics import compute_psr  # noqa: E402
from src.features.momentum import build_weights  # noqa: E402
from src.simulation.engine import SimulationConfig, _target_weights  # noqa: E402
from src.simulation.evaluation import GoNoGoConfig, evaluate_go_no_go  # noqa: E402
from src.simulation.paper_trading import (  # noqa: E402
    PaperTradingConfig,
    PaperTradingState,
)

CANDIDATE_ID = "tsmomentum_spytrend_001"
CYCLE = "926"

REPORTS_DIR = REPO_ROOT / "research" / "reports"
EXPERIMENTS_DIR = REPO_ROOT / "research" / "experiments"
RAW_DIR = REPO_ROOT / "data" / "raw"
STATE_PATH = REPO_ROOT / "data" / "processed" / "paper_trading_state.yaml"
CONFIG_PATH = REPO_ROOT / "config" / "paper_trading_config.yaml"
SIM_CONFIG_PATH = REPO_ROOT / "config" / "simulation_candidate_001.yaml"
GATES_PATH = REPO_ROOT / "config" / "promotion_gates.yaml"
OUT_REPORT = REPORTS_DIR / "tsmomentum_same_session_vol_correction_001.md"
OUT_EXP = EXPERIMENTS_DIR / "tsmomentum_same_session_vol_correction_001.md"

# The published walk-forward aggregate (research/experiments/tsmomentum_regime_filter_wf_001.md)
# re-derived from the committed cache.  This is the anchor of the default path.
PUBLISHED_WF_MEAN = 0.9473074720246092
PUBLISHED_WF_FOLDS = 48
# The published numerical-artefact fold (Cycle 925 section 5): a near-flat segment.
ARTEFACT_FOLD = 12

# The gate under measurement (config/promotion_gates.yaml).
WINDOW = 63
GATE_ROLLING_SHARPE = 0.9
GATE_PSR = 0.95
ANNUAL = 252

# The repository's own PSR settings (config/promotion_gates.yaml, gate "psr").
PSR_TARGET = 1.4178
PSR_N_BOOTSTRAP = 1000
PSR_BLOCK_SIZE = 22
PSR_SEED = 20240101

# The committed record's trailing 63-session Sharpe (Cycle 925 anchor).
COMMITTED_TRAILING_SHARPE = -0.1429350026091491

# The published backtest baseline of the incumbent on the 2018-2026 test period
# (research/run_cycle7.py::DOCUMENTED), the fixed PSR reference 1.4178.  The
# measurement is taken on the **Cycle 7 data vintage** (panel truncated at
# 2026-10-09); the committed cache now extends 8 sessions further, which moves
# the test-period numbers and would make the anchor irreproducible.
TEST_PERIOD_VINTAGE_END = "2026-10-09"
PUBLISHED_TEST_PERIOD = {
    "sharpe_ratio": 1.4178,
    "max_drawdown": -0.0779,
    "trade_count": 1196,
    "annualized_return": 0.1446,
    "annualized_turnover": 13.32,
    "sortino_ratio": 1.7477,
    "profit_factor": 1.35,
    "annualized_volatility": 0.0879,
}
# The published values are rounded in the source document (4 decimals, except
# the two 2-decimal ones), so the anchor tolerance follows the published
# precision.  The trade count must match exactly.
PUBLISHED_TEST_PERIOD_TOLERANCE = {
    "sharpe_ratio": 1e-3,
    "max_drawdown": 1e-3,
    "trade_count": 0.0,
    "annualized_return": 1e-3,
    "annualized_turnover": 5e-3,
    "sortino_ratio": 1e-3,
    "profit_factor": 5e-3,
    "annualized_volatility": 1e-3,
}

# The numeric markers of the affected published statistics, used to build the
# committed-artefact blast-radius inventory (measured, not hand-listed).
BLAST_RADIUS_MARKERS = (
    ("0.9473", "published 48-fold walk-forward mean OOS Sharpe"),
    ("1.771084", "committed record's canonical Sharpe"),
    ("0.448918", "committed record's trailing 63-session Sharpe (drift flag)"),
    ("1.486941", "full-path Sharpe of the committed record's path"),
)


# ----------------------------------------------------------------------
# Frozen pre-change implementations (the bit-identity reference)
# ----------------------------------------------------------------------
def legacy_apply_overlay(
    asset_ret: pd.DataFrame,
    base_weights: pd.DataFrame,
    exposure_factor: pd.Series | None = None,
) -> tuple[pd.DataFrame, pd.Series, dict]:
    """Frozen copy of ``research/run_cycle6.py::_apply_overlay`` as it was
    **before** the opt-in switch was added."""
    weights = base_weights.copy()
    if exposure_factor is not None:
        ef = exposure_factor.reindex(weights.index).fillna(0.0)
        weights = weights.mul(ef, axis=0)

    daily_ret = asset_ret.copy()

    port_ret = (weights * daily_ret).sum(axis=1)
    realized_vol = port_ret.rolling(VOL_TARGET_LOOKBACK).std() * np.sqrt(252)
    realized_vol = realized_vol.replace(0, np.nan)
    vol_scale = (VOL_TARGET / realized_vol).clip(upper=1.0).fillna(0.0)
    vol_targeted_weights = weights.mul(vol_scale, axis=0)

    vol_port_ret = (vol_targeted_weights * daily_ret).sum(axis=1)
    cum = (1 + vol_port_ret).cumprod()
    running_max = cum.expanding().max()
    drawdown = (cum / running_max) - 1
    in_drawdown = drawdown < -DD_THRESHOLD
    dd_scale = pd.Series(1.0, index=weights.index)
    dd_scale[in_drawdown] = 0.5

    combined_scale = vol_scale * dd_scale
    combined_weights = weights.mul(combined_scale, axis=0)

    weight_changes = combined_weights.diff().abs().sum(axis=1)
    cost_per_trade = COMMISSION_BPS + SLIPPAGE_BPS
    costs = weight_changes * cost_per_trade

    net_ret = (combined_weights * daily_ret).sum(axis=1) - costs
    metrics = compute_metrics(
        net_ret, combined_weights, COMMISSION_BPS, SLIPPAGE_BPS, 0.02
    )
    return combined_weights, net_ret, metrics


def legacy_target_weights(
    weights: pd.DataFrame,
    asset_ret: pd.DataFrame,
    config: SimulationConfig,
) -> dict:
    """Frozen copy of ``src/simulation/engine.py::_target_weights`` as it was
    **before** the opt-in switch was added."""
    port_ret = (weights * asset_ret).sum(axis=1)
    realized_vol = port_ret.rolling(config.vol_lookback).std() * np.sqrt(252)
    realized_vol = realized_vol.replace(0, np.nan)
    vol_scale = (config.vol_target / realized_vol).clip(upper=1.0).fillna(0.0)

    vol_targeted = weights.mul(vol_scale, axis=0)
    vol_port_ret = (vol_targeted * asset_ret).sum(axis=1)
    cum = (1 + vol_port_ret).cumprod()
    running_max = cum.expanding().max()
    drawdown = (cum / running_max) - 1.0
    in_drawdown = drawdown < -config.dd_threshold
    dd_scale = pd.Series(1.0, index=weights.index)
    dd_scale[in_drawdown] = config.dd_reduction

    combined = weights.mul(vol_scale * dd_scale, axis=0)

    gross = combined.abs().sum(axis=1)
    leverage_scale = (config.max_leverage / gross).clip(upper=1.0)
    combined = combined.mul(leverage_scale, axis=0)

    return {
        "combined_weights": combined,
        "vol_scale": vol_scale,
        "dd_scale": dd_scale,
        "overlay_drawdown": drawdown,
    }


def legacy_volatility_target_overlay(
    returns: pd.Series,
    weights: pd.DataFrame,
    target_vol: float = 0.15,
    vol_lookback: int = 63,
) -> tuple[pd.Series, dict]:
    """Frozen copy of ``src/evaluation/risk.py::volatility_target_overlay`` as
    it was **before** the opt-in switch was added."""
    daily_ret = returns.copy()
    port_ret = (weights * daily_ret).sum(axis=1)
    realized_vol = port_ret.rolling(vol_lookback).std() * np.sqrt(252)
    realized_vol = realized_vol.replace(0, np.nan)
    scale = target_vol / realized_vol
    scale = scale.clip(upper=1.0).fillna(0.0)
    scaled_weights = weights.mul(scale, axis=0)
    weight_changes = scaled_weights.diff().abs().sum(axis=1)
    cost_per_trade = 1.0 / 10000.0 + 2.0 / 10000.0
    costs = weight_changes * cost_per_trade
    net_ret = (scaled_weights * daily_ret).sum(axis=1) - costs
    metrics = compute_metrics(
        net_ret, scaled_weights, 1.0 / 10000.0, 2.0 / 10000.0, 0.02
    )
    return net_ret, metrics


def legacy_combined_risk_overlay(
    returns: pd.Series,
    weights: pd.DataFrame,
    target_vol: float = 0.15,
    vol_lookback: int = 63,
) -> tuple[pd.Series, dict]:
    """Frozen copy of ``src/evaluation/risk.py::combined_risk_overlay`` as it
    was **before** the opt-in switch was added."""
    daily_ret = returns.copy()
    port_ret = (weights * daily_ret).sum(axis=1)
    realized_vol = port_ret.rolling(vol_lookback).std() * np.sqrt(252)
    realized_vol = realized_vol.replace(0, np.nan)
    vol_scale = (target_vol / realized_vol).clip(upper=1.0).fillna(0.0)
    vol_targeted_weights = weights.mul(vol_scale, axis=0)
    vol_port_ret = (vol_targeted_weights * daily_ret).sum(axis=1)
    cum = (1 + vol_port_ret).cumprod()
    running_max = cum.expanding().max()
    drawdown = (cum / running_max) - 1
    in_drawdown = drawdown < -0.15
    dd_scale = pd.Series(1.0, index=weights.index)
    dd_scale[in_drawdown] = 0.5
    combined_scale = vol_scale * dd_scale
    combined_weights = weights.mul(combined_scale, axis=0)
    weight_changes = combined_weights.diff().abs().sum(axis=1)
    cost_per_trade = 1.0 / 10000.0 + 2.0 / 10000.0
    costs = weight_changes * cost_per_trade
    net_ret = (combined_weights * daily_ret).sum(axis=1) - costs
    metrics = compute_metrics(
        net_ret, combined_weights, 1.0 / 10000.0, 2.0 / 10000.0, 0.02
    )
    return net_ret, metrics


# ----------------------------------------------------------------------
# Path construction (the published research path, with the opt-in switch)
# ----------------------------------------------------------------------
def build_path(close: pd.DataFrame, lag_vol_estimate: bool = False) -> dict[str, Any]:
    """The published research path over the full history, with the switch.

    Uses ``research/run_cycle6.py::_apply_overlay`` -- the function that
    produced the published record -- with the opt-in switch forwarded.
    """
    weights = build_weights(close, lookback=LOOKBACK, skip=SKIP, top_fraction=TOP_FRACTION)
    common = close.index.intersection(weights.index)
    close_a = close.loc[common]
    weights_a = weights.loc[common]
    daily_ret = close_a.pct_change().fillna(0.0)

    spy = close_a["SPY"]
    spy_sma = spy.rolling(SPY_SMA_WINDOW).mean()
    exposure = pd.Series(1.0, index=close_a.index)
    exposure[spy < spy_sma] = 0.0
    exposure[spy.isna() | spy_sma.isna()] = 0.0

    combined, net_ret, metrics = _apply_overlay(
        daily_ret, weights_a, exposure_factor=exposure,
        lag_vol_estimate=lag_vol_estimate,
    )

    gated = weights_a.mul(exposure.reindex(weights_a.index).fillna(0.0), axis=0)
    port_ret = (gated * daily_ret).sum(axis=1)
    vol_scale = realized_vol_scale(
        port_ret, VOL_TARGET, VOL_TARGET_LOOKBACK, lag_vol_estimate
    )
    return {
        "net_ret": net_ret,
        "combined_weights": combined,
        "exposure": exposure,
        "base_weights": weights_a,
        "gated_weights": gated,
        "daily_ret": daily_ret,
        "asset_ret": close_a.pct_change(),
        "port_ret": port_ret,
        "vol_scale": vol_scale,
        "metrics": metrics,
    }


# ----------------------------------------------------------------------
# Statistics
# ----------------------------------------------------------------------
def fold_segment_detail(
    net_ret: pd.Series,
    weights: pd.DataFrame,
    row: dict[str, Any],
) -> dict[str, Any]:
    """The raw content of one fold's test window (why a fold Sharpe is what it is)."""
    mask = (weights.index >= pd.Timestamp(row["test_start"], tz="UTC")) & (
        weights.index <= pd.Timestamp(row["test_end"], tz="UTC")
    )
    values = net_ret[mask].to_numpy(dtype=float)
    return {
        "fold": int(row["fold"]),
        "test_start": str(row["test_start"]),
        "test_end": str(row["test_end"]),
        "n_sessions": int(len(values)),
        "n_flat_sessions": int(np.sum(np.abs(values) < 1e-9)),
        "mean_daily_return": float(np.mean(values)) if len(values) else float("nan"),
        "std_daily_return": float(np.std(values, ddof=1)) if len(values) > 1 else float("nan"),
    }


def fold_statistics(net_ret: pd.Series, weights: pd.DataFrame) -> dict[str, Any]:
    """The published-design walk-forward statistics of one path."""
    design = evaluate_design(net_ret, weights, published_splits())
    rows = design["folds"]
    sharpes = np.asarray([r["test_sharpe"] for r in rows], dtype=float)
    worst = int(np.argmin(sharpes))
    artefact = ARTEFACT_FOLD - 1
    without_artefact = np.delete(sharpes, artefact)
    without_worst = np.delete(sharpes, worst)
    return {
        "n_folds": len(rows),
        "mean_test_sharpe": float(np.mean(sharpes)),
        "median_test_sharpe": float(np.median(sharpes)),
        "std_test_sharpe": float(np.std(sharpes, ddof=1)),
        "min_test_sharpe": float(np.min(sharpes)),
        "max_test_sharpe": float(np.max(sharpes)),
        "pct_positive_sharpe": float(np.mean(sharpes > 0)),
        "mean_test_sharpe_excl_artefact_fold": float(np.mean(without_artefact)),
        "mean_test_sharpe_excl_worst_fold": float(np.mean(without_worst)),
        "worst_fold": int(rows[worst]["fold"]),
        "worst_fold_test_sharpe": float(sharpes[worst]),
        "worst_fold_test_start": str(rows[worst]["test_start"]),
        "worst_fold_test_end": str(rows[worst]["test_end"]),
        "worst_fold_detail": fold_segment_detail(net_ret, weights, rows[worst]),
        "artefact_fold": ARTEFACT_FOLD,
        "artefact_fold_test_sharpe": float(sharpes[artefact]),
        "artefact_fold_test_start": str(rows[artefact]["test_start"]),
        "artefact_fold_test_end": str(rows[artefact]["test_end"]),
        "artefact_fold_detail": fold_segment_detail(net_ret, weights, rows[artefact]),
        "total_test_trades": int(sum(r["test_trades"] for r in rows)),
        "sharpes": sharpes,
        "folds": rows,
    }


def record_statistics(net_ret: pd.Series, record_dates: list[pd.Timestamp]) -> dict[str, Any]:
    """The record's gate-relevant statistics on one path."""
    rec = net_ret.loc[record_dates].to_numpy(dtype=float)
    trailing = float(sharpe_ratio(rec[-WINDOW:]))
    psr = compute_psr(
        pd.Series(rec),
        sr_target=PSR_TARGET,
        n_bootstrap=PSR_N_BOOTSTRAP,
        block_size=PSR_BLOCK_SIZE,
        seed=PSR_SEED,
    )
    return {
        "n_sessions": int(len(rec)),
        "canonical_sharpe": float(sharpe_ratio(rec)),
        "trailing_63d_sharpe": trailing,
        "rolling_gate_value": trailing,
        "rolling_gate_passes": bool(trailing >= GATE_ROLLING_SHARPE),
        "psr_normal": float(psr["psr_normal"]),
        "psr_empirical": float(psr["psr_empirical"]),
        "psr_sharpe_se": float(psr["sharpe_se"]),
        "psr_ci_lower": float(psr["ci_lower"]),
        "psr_ci_upper": float(psr["ci_upper"]),
        "psr_target": PSR_TARGET,
        "psr_gate_passes": bool(psr["psr_normal"] >= GATE_PSR),
        "return_sum": float(np.sum(rec)),
        "max_drawdown": float((np.cumprod(1.0 + rec) / np.maximum.accumulate(np.cumprod(1.0 + rec)) - 1.0).min()),
    }


def production_gate_table(
    state: PaperTradingState,
    config: PaperTradingConfig,
) -> dict[str, Any]:
    """The production promotion-gate table of a (possibly corrected) record."""
    go_no_go_config = GoNoGoConfig(
        min_days=config.go_no_go_min_days,
        target_sharpe=config.go_no_go_target_sharpe,
        max_dd_threshold=config.go_no_go_max_dd_threshold,
    )
    result = evaluate_go_no_go(
        state, config, go_no_go_config=go_no_go_config
    )
    return {
        "decision": result.decision,
        "failed_gates": list(result.failed_gates),
        "gates": {g.name: float(g.value) for g in result.gates},
        "psr_normal": float(result.psr_normal),
    }


def corrected_state(
    committed: PaperTradingState,
    net_ret: pd.Series,
    record_dates: list[pd.Timestamp],
) -> PaperTradingState:
    """The committed state with the corrected return series substituted.

    Only the return series and the dates change; every other field is carried
    over unchanged, because the promotion gates consume only the returns, the
    dates, the run-history turnover and the run-history regime exposure.
    """
    rec = net_ret.loc[record_dates]
    state = PaperTradingState(
        last_run_date=committed.last_run_date,
        current_positions=dict(committed.current_positions),
        cumulative_returns=[float(x) for x in rec.to_numpy()],
        cumulative_pnl=list(committed.cumulative_pnl),
        cumulative_dates=[str(d.date()) for d in record_dates],
        peak_nav=committed.peak_nav,
        current_nav=committed.current_nav,
        max_drawdown=committed.max_drawdown,
        drift_flags=dict(committed.drift_flags),
        run_history=[dict(h) for h in committed.run_history],
        previous_regime_exposure=committed.previous_regime_exposure,
    )
    for history, value in zip(state.run_history, state.cumulative_returns):
        history["daily_return"] = value
    return state


# ----------------------------------------------------------------------
# Blast radius
# ----------------------------------------------------------------------
CODE_PATH_INVENTORY = (
    (
        "src/evaluation/risk.py::volatility_target_overlay",
        "shared code",
        "volatility-target overlay helper",
        "opt-in switch added (lag_vol_estimate, default off)",
    ),
    (
        "src/evaluation/risk.py::combined_risk_overlay",
        "shared code",
        "combined volatility + drawdown overlay helper",
        "opt-in switch added (lag_vol_estimate, default off)",
    ),
    (
        "src/simulation/engine.py::_target_weights",
        "shared code",
        "simulation engine / live paper-trading path",
        "opt-in switch added (SimulationConfig.lag_vol_estimate, default off)",
    ),
    (
        "research/run_cycle6.py::_apply_overlay",
        "research script",
        "published research path of the incumbent (the published walk-forward record)",
        "opt-in switch added (lag_vol_estimate, default off)",
    ),
    (
        "research/run_cycle5.py",
        "research script",
        "Cycle 5 candidate path of the incumbent",
        "not changed (same-session estimate still used)",
    ),
    (
        "research/run_cycle13.py",
        "research script",
        "csmomentum_001 candidate path",
        "not changed (same-session estimate still used)",
    ),
    (
        "research/run_cycle15.py, research/run_cycle15_c4_corrected.py",
        "research script",
        "csmomentum_001 candidate paths",
        "not changed (same-session estimate still used)",
    ),
    (
        "research/run_cycle18.py, research/run_cycle19.py",
        "research script",
        "csmomentum_001 / macroregime_001 candidate paths",
        "not changed (same-session estimate still used)",
    ),
    (
        "research/run_cycle3.py, research/run_cycle4.py",
        "research script",
        "consumers of the shared overlay helpers (no inline estimate of their own)",
        "already routed through src/evaluation/risk.py (they inherit the switch)",
    ),
    (
        "research/month_end_candidate_reaudit.py",
        "research script",
        "config-faithful month-end re-audit of csmomentum_001",
        "not changed (same-session estimate still used)",
    ),
    (
        "research/tsmomentum_rolling63_weakness_diagnosis.py::overlay_variant",
        "research script",
        "Cycle 925 diagnosis (already carried a scratch lag-1 variant)",
        "not changed (measurement only, scratch paths)",
    ),
    (
        "research/trailing_window_attribution.py",
        "research script",
        "consumes the simulation engine's vol_scale (indirect dependency)",
        "not changed (inherits the engine's default)",
    ),
)


def artifact_inventory() -> list[dict[str, Any]]:
    """The committed artefacts that quote the affected published statistics.

    Measured by searching the committed tree for the published numeric
    markers, so the inventory cannot drift from the repository's content.
    """
    import subprocess

    try:
        res = subprocess.run(
            ["git", "ls-files", "research", "data", "config", "src", "README.md"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return []
    files = [rel.strip() for rel in res.stdout.splitlines() if rel.strip()]
    text_suffixes = (".md", ".py", ".yaml", ".yml", ".json", ".txt")
    out: list[dict[str, Any]] = []
    for marker, description in BLAST_RADIUS_MARKERS:
        hits: list[str] = []
        for rel in files:
            path = REPO_ROOT / rel
            if not path.is_file() or not rel.endswith(text_suffixes):
                continue
            if path.stat().st_size > 4_000_000:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if marker in text:
                hits.append(rel)
        out.append(
            {
                "marker": marker,
                "description": description,
                "n_files": len(hits),
                "files": sorted(hits),
            }
        )
    return out


# ----------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------
def run_correction(
    raw_dir: Path = RAW_DIR,
    published_machinery: bool = True,
) -> dict[str, Any]:
    """Measure the correction.

    ``published_machinery`` runs the published walk-forward machinery
    (``research/run_cycle6.py::run_walkforward``) as the primary anchor.  It is
    on by default; the flag exists so a test can exercise the rest of the
    measurement without paying for the 96 per-fold path recomputations.
    """
    checks: list[dict[str, Any]] = []

    def record_check(name: str, ok: bool, observed: Any = "", expected: Any = "") -> None:
        checks.append({"name": name, "pass": bool(ok), "observed": observed, "expected": expected})

    data_before = fingerprint(REPO_ROOT / "data")
    config_before = fingerprint(REPO_ROOT / "config")
    artifacts_before = tracked_artifact_hashes()

    # ------------------------------------------------------------------
    # 1. The committed record
    # ------------------------------------------------------------------
    import yaml

    with open(STATE_PATH) as fh:
        state_doc = yaml.safe_load(fh) or {}
    committed_returns = np.asarray(state_doc["cumulative_returns"], dtype=float)
    record_dates = [pd.Timestamp(str(d), tz="UTC") for d in state_doc["cumulative_dates"]]
    n_sessions = len(committed_returns)
    record_check(
        "committed_record_loaded",
        n_sessions == 453,
        f"{n_sessions} sessions",
        "453 sessions",
    )

    close = load_close_from_cache(list(SYMBOLS), raw_dir)
    default_path = build_path(close, lag_vol_estimate=False)
    corrected_path = build_path(close, lag_vol_estimate=True)

    # ------------------------------------------------------------------
    # 2. Anchor: the default path reproduces the committed artefacts
    # ------------------------------------------------------------------
    record_net = default_path["net_ret"].loc[record_dates].to_numpy(dtype=float)
    record_diff = float(np.max(np.abs(record_net - committed_returns)))
    record_check(
        "default_path_reproduces_every_committed_session",
        record_diff <= 1e-12,
        f"max |diff| = {record_diff:.3e} over {n_sessions} sessions",
        "<= 1e-12",
    )

    legacy_weights, legacy_net, _ = legacy_apply_overlay(
        default_path["daily_ret"],
        default_path["base_weights"],
        exposure_factor=default_path["exposure"],
    )
    legacy_net_diff = float(np.max(np.abs(legacy_net - default_path["net_ret"])))
    legacy_weight_diff = float(np.max(np.abs(legacy_weights - default_path["combined_weights"])))
    record_check(
        "default_research_path_is_bit_identical_to_the_pre_change_implementation",
        legacy_net_diff == 0.0 and legacy_weight_diff == 0.0,
        f"net max |diff| = {legacy_net_diff:.3e}, weights max |diff| = {legacy_weight_diff:.3e}",
        "0.0 (bit-identical)",
    )

    sim_config = SimulationConfig.from_yaml(SIM_CONFIG_PATH)
    gated = default_path["gated_weights"]
    asset_ret = default_path["asset_ret"]
    new_targets = _target_weights(gated, asset_ret, sim_config)
    old_targets = legacy_target_weights(gated, asset_ret, sim_config)
    engine_diff = float(
        np.max(np.abs(new_targets["combined_weights"] - old_targets["combined_weights"]))
    )
    engine_vol_diff = float(np.max(np.abs(new_targets["vol_scale"] - old_targets["vol_scale"])))
    record_check(
        "default_simulation_path_is_bit_identical_to_the_pre_change_implementation",
        engine_diff == 0.0 and engine_vol_diff == 0.0,
        f"weights max |diff| = {engine_diff:.3e}, vol_scale max |diff| = {engine_vol_diff:.3e}",
        "0.0 (bit-identical)",
    )

    asset_returns = default_path["daily_ret"].sum(axis=1)
    risk_new, _ = volatility_target_overlay(asset_returns, gated)
    risk_old, _ = legacy_volatility_target_overlay(asset_returns, gated)
    risk_vol_diff = float(np.max(np.abs(risk_new - risk_old)))
    comb_new, _ = combined_risk_overlay(asset_returns, gated)
    comb_old, _ = legacy_combined_risk_overlay(asset_returns, gated)
    comb_diff = float(np.max(np.abs(comb_new - comb_old)))
    record_check(
        "default_risk_overlay_helpers_are_bit_identical_to_the_pre_change_implementation",
        risk_vol_diff == 0.0 and comb_diff == 0.0,
        f"vol-target max |diff| = {risk_vol_diff:.3e}, combined max |diff| = {comb_diff:.3e}",
        "0.0 (bit-identical)",
    )

    # published walk-forward: the published design, re-derived from the cache
    default_folds = fold_statistics(default_path["net_ret"], default_path["combined_weights"])
    record_check(
        "published_walk_forward_mean_reproduced",
        default_folds["mean_test_sharpe"] == PUBLISHED_WF_MEAN,
        f"{default_folds['mean_test_sharpe']:.12f}",
        f"{PUBLISHED_WF_MEAN:.12f} (published)",
    )
    record_check(
        "published_walk_forward_fold_count_reproduced",
        default_folds["n_folds"] == PUBLISHED_WF_FOLDS,
        f"{default_folds['n_folds']} folds",
        f"{PUBLISHED_WF_FOLDS} folds",
    )

    published_path, published = resolve_published_record(EXPERIMENTS_DIR)
    published_folds = published["folds"]
    record_check(
        "published_record_resolved_by_content",
        len(published_folds) == PUBLISHED_WF_FOLDS,
        published_path.name,
        f"{PUBLISHED_WF_FOLDS} published folds",
    )
    window_mismatches = 0
    sharpe_mismatches = 0
    trade_mismatches = 0
    for pub, rec in zip(published_folds, default_folds["folds"]):
        if not (
            pub["train_start"] == rec["train_start"]
            and pub["train_end"] == rec["train_end"]
            and pub["test_start"] == rec["test_start"]
            and pub["test_end"] == rec["test_end"]
        ):
            window_mismatches += 1
        if abs(pub["test_sharpe"] - rec["test_sharpe"]) > 1e-4:
            sharpe_mismatches += 1
        if int(pub["test_trades"]) != int(rec["test_trades"]):
            trade_mismatches += 1
    record_check(
        "published_fold_table_reproduced",
        window_mismatches == 0 and sharpe_mismatches == 0 and trade_mismatches == 0,
        f"windows {window_mismatches}, OOS Sharpe {sharpe_mismatches}, trades {trade_mismatches} mismatching",
        "0 mismatches (published precision: 1e-4)",
    )

    # the published machinery itself (the code that produced the record)
    import research.run_cycle6 as run_cycle6

    if published_machinery:
        machinery = run_cycle6.run_walkforward()
        machinery_summary = machinery["summary"]
        machinery_mean = float(machinery_summary["mean_test_sharpe"])
        record_check(
            "published_machinery_still_reproduces_the_published_mean",
            machinery_mean == PUBLISHED_WF_MEAN,
            f"{machinery_mean:.12f}",
            f"{PUBLISHED_WF_MEAN:.12f} (published)",
        )
        machinery_sharpes = machinery["wf_df"]["test_sharpe"].to_numpy(dtype=float)
        record_check(
            "continuous_path_and_published_machinery_agree_fold_by_fold",
            bool(np.array_equal(machinery_sharpes, default_folds["sharpes"])),
            f"max |diff| = {float(np.max(np.abs(machinery_sharpes - default_folds['sharpes']))):.3e}",
            "0.0 (the re-derivation shortcut used for the corrected path is exact)",
        )
    else:
        machinery_mean = None

    # ------------------------------------------------------------------
    # 3. Switch semantics
    # ------------------------------------------------------------------
    default_scale = realized_vol_scale(
        default_path["port_ret"], VOL_TARGET, VOL_TARGET_LOOKBACK, False
    )
    corrected_scale = realized_vol_scale(
        default_path["port_ret"], VOL_TARGET, VOL_TARGET_LOOKBACK, True
    )
    shift_diff = float(
        np.max(np.abs(corrected_scale.to_numpy()[1:] - default_scale.to_numpy()[:-1]))
    )
    record_check(
        "lagged_estimate_is_the_same_session_estimate_shifted_one_session",
        shift_diff == 0.0,
        f"max |diff| = {shift_diff:.3e}",
        "0.0 (exact shift)",
    )
    legacy_scale = default_path["port_ret"].rolling(VOL_TARGET_LOOKBACK).std() * np.sqrt(ANNUAL)
    legacy_scale = legacy_scale.replace(0, np.nan)
    legacy_scale = (VOL_TARGET / legacy_scale).clip(upper=1.0).fillna(0.0)
    record_check(
        "default_scale_is_the_committed_same_session_estimate",
        float(np.max(np.abs(default_scale.to_numpy() - legacy_scale.to_numpy()))) == 0.0,
        f"max |diff| = {float(np.max(np.abs(default_scale.to_numpy() - legacy_scale.to_numpy()))):.3e}",
        "0.0 (bit-identical)",
    )
    record_check(
        "opt_in_switch_changes_the_path",
        float(np.max(np.abs(corrected_path["net_ret"] - default_path["net_ret"]))) > 0.0,
        f"max |diff| = {float(np.max(np.abs(corrected_path['net_ret'] - default_path['net_ret']))):.3e}",
        "> 0 (the corrected path is a different path)",
    )
    paper_config = PaperTradingConfig.from_paper_config_yaml(CONFIG_PATH)
    record_check(
        "switch_defaults_are_off_in_every_entry_point",
        SimulationConfig().lag_vol_estimate is False
        and sim_config.lag_vol_estimate is False
        and paper_config.lag_vol_estimate is False,
        "SimulationConfig(), SimulationConfig.from_yaml, PaperTradingConfig.from_paper_config_yaml -> all False",
        "all False (default off)",
    )
    config_mentions_all = [
        str(p.relative_to(REPO_ROOT))
        for p in sorted((REPO_ROOT / "config").rglob("*"))
        if p.is_file() and "lag_vol_estimate" in p.read_text(encoding="utf-8", errors="ignore")
    ]
    config_mentions = [m for m in config_mentions_all if "_corrected" not in m]
    record_check(
        "no_config_file_sets_the_switch",
        config_mentions == [],
        f"{len(config_mentions)} non-corrected config file(s) mention the switch",
        "0",
    )
    record_check(
        "corrected_config_is_specification_only_exception",
        "config/simulation_candidate_001_corrected.yaml" in config_mentions_all,
        "config/simulation_candidate_001_corrected.yaml sets lag_vol_estimate: true (specification-only, not an activated record)",
        "declared exception present",
    )
    record_feeding_configs = ["config/simulation_candidate_001.yaml", "config/paper_trading_config.yaml"]
    record_feeding_mentions = [m for m in config_mentions_all if m in record_feeding_configs]
    record_check(
        "no_record_feeding_config_sets_the_switch",
        record_feeding_mentions == [],
        f"{len(record_feeding_mentions)} record-feeding config(s) mention the switch",
        "0",
    )

    # ------------------------------------------------------------------
    # 4. Re-derivation on the corrected path
    # ------------------------------------------------------------------
    corrected_folds = fold_statistics(
        corrected_path["net_ret"], corrected_path["combined_weights"]
    )
    default_record = record_statistics(default_path["net_ret"], record_dates)
    corrected_record = record_statistics(corrected_path["net_ret"], record_dates)

    record_check(
        "committed_record_gate_value_reproduced",
        abs(default_record["trailing_63d_sharpe"] - COMMITTED_TRAILING_SHARPE) < 1e-12,
        f"{default_record['trailing_63d_sharpe']:.12f}",
        f"{COMMITTED_TRAILING_SHARPE:.12f} (committed drift flag)",
    )

    committed_state = PaperTradingState.from_yaml(STATE_PATH)
    default_gates = production_gate_table(committed_state, paper_config)
    corrected_state_obj = corrected_state(committed_state, corrected_path["net_ret"], record_dates)
    corrected_gates = production_gate_table(corrected_state_obj, paper_config)
    record_check(
        "corrected_path_does_not_rescue_the_promotion_decision",
        corrected_gates["decision"] == default_gates["decision"] == "NO-GO",
        f"default {default_gates['decision']}, corrected {corrected_gates['decision']}",
        "NO-GO on both paths (the decision is unchanged)",
    )
    record_check(
        "corrected_path_does_not_clear_the_rolling_gate",
        not corrected_record["rolling_gate_passes"],
        f"corrected trailing 63d Sharpe {corrected_record['trailing_63d_sharpe']:.6f}",
        f"< {GATE_ROLLING_SHARPE} (the corrected window is worse)",
    )
    record_check(
        "corrected_path_does_not_clear_the_psr_gate",
        not corrected_record["psr_gate_passes"],
        f"corrected PSR {corrected_record['psr_normal']:.6f}",
        f"< {GATE_PSR}",
    )
    record_check(
        "published_numerical_artefact_fold_is_absent_on_the_corrected_path",
        abs(corrected_folds["artefact_fold_test_sharpe"]) < 1.0
        and abs(default_folds["artefact_fold_test_sharpe"]) > 1.0,
        f"fold {ARTEFACT_FOLD}: default {default_folds['artefact_fold_test_sharpe']:.6f}, "
        f"corrected {corrected_folds['artefact_fold_test_sharpe']:.6f}",
        "the artefact disappears when the estimate is lagged",
    )

    # ------------------------------------------------------------------
    # 4b. The 2018-2026 test period: the published PSR reference
    # ------------------------------------------------------------------
    vintage_close = close.loc[:TEST_PERIOD_VINTAGE_END]
    default_test = _eval_candidate(
        vintage_close, spy_sma_window=SPY_SMA_WINDOW, lag_vol_estimate=False
    )
    corrected_test = _eval_candidate(
        vintage_close, spy_sma_window=SPY_SMA_WINDOW, lag_vol_estimate=True
    )
    test_period = {
        "published": dict(default_test["test_metrics"]),
        "corrected": dict(corrected_test["test_metrics"]),
        "published_reference": dict(PUBLISHED_TEST_PERIOD),
        "vintage_end": TEST_PERIOD_VINTAGE_END,
    }
    reference_mismatches = [
        key
        for key, expected in PUBLISHED_TEST_PERIOD.items()
        if abs(float(default_test["test_metrics"][key]) - float(expected))
        > PUBLISHED_TEST_PERIOD_TOLERANCE[key]
    ]
    record_check(
        "published_test_period_baseline_reproduced",
        reference_mismatches == [],
        f"Sharpe {default_test['test_metrics']['sharpe_ratio']:.6f}, max DD "
        f"{default_test['test_metrics']['max_drawdown']:.6f}, trades "
        f"{int(default_test['test_metrics']['trade_count'])}",
        f"the {len(PUBLISHED_TEST_PERIOD)} documented values of "
        f"research/run_cycle7.py::DOCUMENTED on the {TEST_PERIOD_VINTAGE_END} vintage "
        f"(mismatching: {reference_mismatches or 'none'})",
    )

    # ------------------------------------------------------------------
    # 5. Blast radius
    # ------------------------------------------------------------------
    inventory = artifact_inventory()
    distinct_affected = len({rel for item in inventory for rel in item["files"]})

    # ------------------------------------------------------------------
    # 6. Read-only re-check
    # ------------------------------------------------------------------
    data_after = fingerprint(REPO_ROOT / "data")
    config_after = fingerprint(REPO_ROOT / "config")
    artifacts_after = tracked_artifact_hashes()
    record_check("data_unchanged", data_before == data_after)
    record_check("config_unchanged", config_before == config_after)
    record_check("committed_artifacts_unchanged", artifacts_before == artifacts_after)

    # ------------------------------------------------------------------
    # Verdict
    # ------------------------------------------------------------------
    verdict = (
        f"**1. The defect is real, quantified and now correctable, but it is not a "
        f"cause of the gate failure and it does not rescue anything.** The same-session "
        f"volatility estimate (session *t*'s own return moves session *t*'s exposure) is "
        f"present in the published research path, in the shared simulation / live "
        f"paper-trading path and in both overlay helpers of `src/evaluation/risk.py`. With "
        f"the estimate lagged one session the committed record's canonical Sharpe moves from "
        f"{default_record['canonical_sharpe']:.6f} to {corrected_record['canonical_sharpe']:.6f}, "
        f"its trailing 63-session Sharpe from {default_record['trailing_63d_sharpe']:.6f} to "
        f"{corrected_record['trailing_63d_sharpe']:.6f} and its PSR against the fixed "
        f"backtest baseline {PSR_TARGET} from {default_record['psr_normal']:.6f} to "
        f"{corrected_record['psr_normal']:.6f}. The corrected path is **worse on every "
        f"record-level statistic** and the promotion decision stays "
        f"**{corrected_gates['decision']}** (failed gates: "
        f"{', '.join(corrected_gates['failed_gates'])}).\n\n"
        f"**2. The corrected 48-fold walk-forward mean looks better only because a "
        f"numerical artefact disappears.** On the default path the published mean OOS Sharpe is "
        f"{default_folds['mean_test_sharpe']:.6f} and it contains one pathological fold "
        f"(fold {default_folds['worst_fold']}, {default_folds['worst_fold_test_sharpe']:.6f}: "
        f"{default_folds['worst_fold_detail']['n_flat_sessions']} of "
        f"{default_folds['worst_fold_detail']['n_sessions']} flat sessions, so the backtest-scale "
        f"estimator divides a near-zero numerator by a near-zero dispersion, Cycle 925 "
        f"section 5). Excluding that fold the default path's mean is "
        f"{default_folds['mean_test_sharpe_excl_worst_fold']:.6f}. On the corrected path the "
        f"same segment is entirely flat, so the estimator returns "
        f"{corrected_folds['artefact_fold_test_sharpe']:.6f} instead of a pathology, the mean "
        f"over all 48 folds is {corrected_folds['mean_test_sharpe']:.6f}, and the strictest "
        f"comparable statistic - both paths with fold {ARTEFACT_FOLD} excluded - is "
        f"**lower** on the corrected path ({corrected_folds['mean_test_sharpe_excl_artefact_fold']:.6f} "
        f"vs {default_folds['mean_test_sharpe_excl_artefact_fold']:.6f}); excluding each path's "
        f"own worst fold it is also lower "
        f"({corrected_folds['mean_test_sharpe_excl_worst_fold']:.6f} vs "
        f"{default_folds['mean_test_sharpe_excl_worst_fold']:.6f}). The corrected path is not a "
        f"recovery, and the higher headline mean must never be quoted without the fold-level "
        f"table.\n\n"
        f"**3. The default path is unchanged, bit-for-bit.** The opt-in switch "
        f"(`lag_vol_estimate`, default off) is available in all three code paths; every "
        f"default-path comparison in this report is a max |diff| of exactly 0.0 against a "
        f"frozen copy of the pre-change implementation (research path, simulation path and "
        f"both risk-overlay helpers). No gate, threshold, universe, cost model, Sharpe "
        f"convention, parameter, hypothesis or drift flag was changed, the published "
        f"walk-forward record and the committed paper-trading state were **not** overwritten, "
        f"and `data/` and `config/` are byte-identical before and after the run.\n\n"
        f"**4. Decision recommendation: adopt only for new live paper-trading records.** "
        f"The defect is a genuine point-in-time error in the **live** path (the exposure for "
        f"session *t* is set with information that is only fully observable after session "
        f"*t*'s close, at the price the trade is executed at), so a **new** live record must "
        f"not be produced with it. But the published backtest artefacts are frozen, are "
        f"quoted by {distinct_affected} committed files, and the correction "
        f"**lowers** every record-level statistic of the only credible candidate in the "
        f"repository while leaving the decision NO-GO: adopting it everywhere would invalidate "
        f"a large body of published evidence in exchange for no decision-relevant gain. The "
        f"published record therefore stays as it is, and a clearly labelled successor record "
        f"is the right vehicle for the corrected backtest (plan in section 7, not executed "
        f"here). Two consequences must be stated. (i) A corrected live record is measured on a "
        f"different path from the published backtest baseline {PSR_TARGET}, so its PSR "
        f"comparison against that unchanged reference is **conservative**: the corrected "
        f"path's own 2018-2026 test-period Sharpe is "
        f"{test_period['corrected']['sharpe_ratio']:.6f} against the published "
        f"{test_period['published']['sharpe_ratio']:.6f}. (ii) A corrected live record must be "
        f"**started fresh** rather than appended to the committed one, because a record that "
        f"mixes the two paths measures neither; the `track_record_length` gate needs 126 "
        f"sessions, so the promotion evidence would restart from zero while the committed "
        f"record stays published and NO-GO.\n\n"
        f"**5. The incumbent's published verdict is unchanged.** It remains a **Credible "
        f"Candidate** by its published verdict and **NO-GO** for promotion, live deployment "
        f"remains unsupported, and this cycle publishes a measurement and a plan - not an "
        f"edge, not a recovery and not a promotion."
    )

    payload: dict[str, Any] = {
        "cycle": CYCLE,
        "candidate": CANDIDATE_ID,
        "sharpe_convention": SHARPE_CONVENTION_ID,
        "overall": "PASS" if all(c["pass"] for c in checks) else "FAIL",
        "checks": checks,
        "switch": {
            "name": "lag_vol_estimate",
            "default": False,
            "semantics": (
                "When True the realised-volatility estimate for session t is computed from "
                "sessions up to and including t-1 only (no same-session feedback). When "
                "False (the default) the trailing 63-session window includes session t, "
                "which is the committed behaviour."
            ),
            "entry_points": [
                "src/evaluation/risk.py::realized_vol_scale",
                "src/evaluation/risk.py::volatility_target_overlay",
                "src/evaluation/risk.py::combined_risk_overlay",
                "src/evaluation/risk.py::run_risk_overlays",
                "src/evaluation/risk.py::run_combined_risk_overlays",
                "src/simulation/engine.py::SimulationConfig.lag_vol_estimate",
                "src/simulation/engine.py::_target_weights",
                "src/simulation/paper_trading.py::PaperTradingConfig.from_paper_config_yaml",
                "research/run_cycle6.py::_apply_overlay",
                "research/run_cycle6.py::_eval_candidate",
                "research/run_cycle6.py::_eval_candidate_period",
                "research/run_cycle6.py::run_walkforward",
            ],
            "config_files_setting_the_switch": config_mentions,
        },
        "anchor": {
            "published_record": published_path.name,
            "published_wf_mean": PUBLISHED_WF_MEAN,
            "reproduced_wf_mean": default_folds["mean_test_sharpe"],
            "machinery_wf_mean": machinery_mean,
            "published_machinery_run": bool(published_machinery),
            "n_folds": default_folds["n_folds"],
            "committed_sessions": n_sessions,
            "record_max_abs_diff": record_diff,
            "research_path_max_abs_diff": legacy_net_diff,
            "research_weights_max_abs_diff": legacy_weight_diff,
            "simulation_path_max_abs_diff": engine_diff,
            "risk_overlay_max_abs_diff": max(risk_vol_diff, comb_diff),
            "lagged_shift_max_abs_diff": shift_diff,
        },
        "walk_forward": {
            "published": {
                k: v for k, v in default_folds.items() if k not in ("sharpes", "folds")
            },
            "corrected": {
                k: v for k, v in corrected_folds.items() if k not in ("sharpes", "folds")
            },
            "published_folds": default_folds["folds"],
            "corrected_folds": corrected_folds["folds"],
        },
        "record": {
            "published": default_record,
            "corrected": corrected_record,
            "test_period_2018_2026": test_period,
            "gate_threshold_rolling": GATE_ROLLING_SHARPE,
            "gate_threshold_psr": GATE_PSR,
            "psr_settings": {
                "target": PSR_TARGET,
                "n_bootstrap": PSR_N_BOOTSTRAP,
                "block_size": PSR_BLOCK_SIZE,
                "seed": PSR_SEED,
            },
            "production_gates_published": default_gates,
            "production_gates_corrected": corrected_gates,
        },
        "blast_radius": {
            "code_paths": [
                {"path": p, "kind": k, "role": r, "state": s}
                for p, k, r, s in CODE_PATH_INVENTORY
            ],
            "committed_artifacts": inventory,
            "n_distinct_affected_files": distinct_affected,
        },
        "decision": {
            "recommendation": "adopt_only_for_new_live_paper_trading_records",
            "reason": (
                "The same-session estimate is a point-in-time error in the live path, so a "
                "new live record must not be produced with it; but the published backtest "
                "artefacts are frozen, are quoted by many committed files, and the "
                "correction lowers every record-level statistic of the incumbent while "
                "leaving the promotion decision NO-GO, so adopting it everywhere would "
                "invalidate published evidence for no decision-relevant gain."
            ),
            "re_derivation_plan": [
                "0. The seven research scripts that still inline the same-session estimate "
                "(run_cycle5.py, run_cycle13.py, run_cycle15.py, run_cycle15_c4_corrected.py, "
                "run_cycle18.py, run_cycle19.py, month_end_candidate_reaudit.py) must route "
                "through the shared src/evaluation/risk.py::realized_vol_scale and accept the "
                "same default-off switch, so that a future adoption cannot be partial: one "
                "implementation, not two.",
                "1. src/simulation/engine.py: keep the switch default-off until the live "
                "record is restarted, then set lag_vol_estimate: true in the (new) "
                "simulation config for records started from that point on; never rewrite a "
                "committed record.",
                "2. research/experiments/tsmomentum_regime_filter_wf_001.md: publish a "
                "labelled successor record (new file) with the corrected 48-fold table; do "
                "not overwrite the published one.",
                "3. The SMA-window plateau table of the same published record: re-derive on "
                "the corrected path in the same successor record.",
                "4. data/processed/paper_trading_state.yaml: keep the committed 453-session "
                "record as published; if a corrected record is started, publish it as a new "
                "state file with its own drift flags and gate table.",
                "5. research/reports/paper_trading_validation_002.md, go_no_go_evaluation_002.md "
                "and deployment_dossier_001.md: add dated addenda with the corrected gate "
                "values; do not rewrite the published values.",
                "6. research/reports/opportunity_shortlist.md and the README cycle log: "
                "re-state the incumbent's score with the corrected statistics only after "
                "the successor record exists.",
                "7. A corrected live record must be started fresh, not appended to the "
                "committed one: a record that mixes the two paths measures neither. The "
                "track_record_length gate needs 126 sessions, and the corrected path's own "
                "2018-2026 backtest reference is 1.335983, so the unchanged PSR reference "
                "1.4178 is a stricter bar than that record's own backtest.",
            ],
        },
        "verdict": verdict,
        "read_only": {
            "data_unchanged": data_before == data_after,
            "config_unchanged": config_before == config_after,
            "committed_artifacts_unchanged": artifacts_before == artifacts_after,
        },
        "incumbent_verdict": "Credible Candidate (unchanged); promotion decision NO-GO (unchanged)",
        "data_source": "committed parquet cache in data/raw/ and the committed paper-trading state (fetcher never called)",
    }
    return payload


# ----------------------------------------------------------------------
# Report / experiment record
# ----------------------------------------------------------------------
def render_report(payload: dict[str, Any]) -> str:
    anchor = payload["anchor"]
    wf = payload["walk_forward"]
    rec = payload["record"]
    lines: list[str] = []

    lines.append(
        "# Same-session volatility estimate: opt-in correction and side-by-side "
        f"re-derivation for the incumbent (tsmomentum_same_session_vol_correction_001, "
        f"Cycle {payload['cycle']})"
    )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Candidate: `{payload['candidate']}` (the incumbent)")
    lines.append(f"- Sharpe convention: `{payload['sharpe_convention']}`")
    lines.append(
        f"- Anchor: the published 48-fold walk-forward mean OOS Sharpe "
        f"**{anchor['reproduced_wf_mean']:.6f}** is reproduced from the committed cache "
        f"(published: {anchor['published_wf_mean']:.6f}), and the committed record's "
        f"{anchor['committed_sessions']} sessions are reproduced with max |diff| = "
        f"{anchor['record_max_abs_diff']:.3e}."
    )
    lines.append(
        f"- Default path: **bit-identical** to the pre-change implementation (max |diff| = "
        f"{anchor['research_path_max_abs_diff']:.1e} research path, "
        f"{anchor['simulation_path_max_abs_diff']:.1e} simulation path, "
        f"{anchor['risk_overlay_max_abs_diff']:.1e} risk overlays)."
    )
    lines.append(
        f"- Switch: `lag_vol_estimate` (default **off**), available in the shared risk "
        f"helpers, the simulation engine and the published research path."
    )
    lines.append(
        f"- Record on the corrected path: canonical Sharpe "
        f"{rec['published']['canonical_sharpe']:.6f} -> {rec['corrected']['canonical_sharpe']:.6f}, "
        f"trailing 63-session Sharpe {rec['published']['trailing_63d_sharpe']:.6f} -> "
        f"{rec['corrected']['trailing_63d_sharpe']:.6f}, PSR vs {PSR_TARGET} "
        f"{rec['published']['psr_normal']:.6f} -> {rec['corrected']['psr_normal']:.6f}."
    )
    lines.append(
        f"- Decision: **unchanged** -- {rec['production_gates_published']['decision']} on the "
        f"published path and {rec['production_gates_corrected']['decision']} on the corrected "
        f"path (failed gates: {', '.join(rec['production_gates_corrected']['failed_gates'])})."
    )
    lines.append(
        f"- Read-only: `data/` and `config/` byte-identical before and after the run "
        f"(**{'yes' if payload['read_only']['data_unchanged'] and payload['read_only']['config_unchanged'] else 'NO'}**); "
        f"no committed artifact modified (**{'yes' if payload['read_only']['committed_artifacts_unchanged'] else 'NO'}**); "
        f"the published walk-forward record and the committed paper-trading state are **not** overwritten."
    )
    lines.append("- Data source: committed parquet cache in `data/raw/` and the committed paper-trading state; the fetcher is never called.")
    lines.append(
        "- No gate, threshold, universe, cost model, Sharpe convention, parameter, hypothesis "
        "or drift flag is changed by this tool, and no candidate is promoted, re-fit or re-ranked."
    )
    lines.append("")

    lines.append("## 1. The defect and the switch")
    lines.append("")
    lines.append(
        "The committed volatility target sets the exposure of session *t* from a "
        "realised-volatility estimate whose trailing 63-session window **includes session t "
        "itself**: today's own return moves today's exposure. The switch "
        "`lag_vol_estimate` (default **off**) computes the estimate from sessions up to and "
        "including *t-1* only."
    )
    lines.append("")
    lines.append("| Entry point | Switch | Default |")
    lines.append("|---|---|---|")
    for entry in payload["switch"]["entry_points"]:
        lines.append(f"| `{entry}` | `lag_vol_estimate` | `False` |")
    lines.append("")
    lines.append(
        f"Semantics: {payload['switch']['semantics']} The lagged scale is exactly the "
        f"same-session scale shifted one session (max |diff| = "
        f"{anchor['lagged_shift_max_abs_diff']:.1e}), and the default scale is bit-identical to "
        f"the committed inline computation. No config file sets the switch "
        f"({len(payload['switch']['config_files_setting_the_switch'])} file(s) mention it), and "
        f"the default value is a code default, not a config-file edit."
    )
    lines.append("")

    lines.append("## 2. Reproduction anchor (fail closed)")
    lines.append("")
    lines.append(
        "Nothing is published unless the default path reproduces the incumbent's published "
        "artefacts. A mismatch fails the run."
    )
    lines.append("")
    lines.append("| Quantity | Published | Reproduced |")
    lines.append("|---|---|---|")
    lines.append(
        f"| 48-fold walk-forward mean OOS Sharpe | {anchor['published_wf_mean']:.6f} | "
        f"{anchor['reproduced_wf_mean']:.6f} |"
    )
    if anchor.get("published_machinery_run", True):
        lines.append(
            f"| Same, from the published machinery (`research/run_cycle6.py::run_walkforward`) | "
            f"{anchor['published_wf_mean']:.6f} | {anchor['machinery_wf_mean']:.6f} |"
        )
    else:
        lines.append(
            f"| Same, from the published machinery (`research/run_cycle6.py::run_walkforward`) | "
            f"{anchor['published_wf_mean']:.6f} | not run (skipped) |"
        )
    lines.append(f"| Folds | {anchor['n_folds']} | {anchor['n_folds']} |")
    lines.append(
        f"| Committed record sessions | {anchor['committed_sessions']} | "
        f"{anchor['committed_sessions']} (max abs diff = {anchor['record_max_abs_diff']:.3e}) |"
    )
    lines.append("")
    lines.append(
        "The published record is resolved **by content** (the committed file that carries the "
        "published aggregate and fold tables), and all 48 published folds are reproduced: "
        "test windows exactly, OOS Sharpe to the published precision and trade counts exactly."
    )
    lines.append("")

    lines.append("## 3. Default-path bit-identity")
    lines.append("")
    lines.append(
        "Each default-path result is compared with a **frozen copy of the pre-change "
        "implementation** (kept in the tool and in the test file), so the guarantee is "
        "checked, not asserted."
    )
    lines.append("")
    lines.append("| Code path | max abs diff | Required |")
    lines.append("|---|---|---|")
    lines.append(
        f"| `research/run_cycle6.py::_apply_overlay` (net returns) | "
        f"{anchor['research_path_max_abs_diff']:.1e} | 0.0 |"
    )
    lines.append(
        f"| `research/run_cycle6.py::_apply_overlay` (combined weights) | "
        f"{anchor['research_weights_max_abs_diff']:.1e} | 0.0 |"
    )
    lines.append(
        f"| `src/simulation/engine.py::_target_weights` (weights + vol_scale) | "
        f"{anchor['simulation_path_max_abs_diff']:.1e} | 0.0 |"
    )
    lines.append(
        f"| `src/evaluation/risk.py` (both overlay helpers) | "
        f"{anchor['risk_overlay_max_abs_diff']:.1e} | 0.0 |"
    )
    lines.append("")

    lines.append("## 4. Side-by-side re-derivation")
    lines.append("")
    lines.append("### 4.1 The published walk-forward record")
    lines.append("")
    lines.append("| Statistic | Published (default path) | Corrected path |")
    lines.append("|---|---|---|")
    pub = wf["published"]
    cor = wf["corrected"]
    for label, key in (
        ("Folds", "n_folds"),
        ("Mean OOS Sharpe (all folds)", "mean_test_sharpe"),
        ("Mean OOS Sharpe excl. the numerical-artefact fold", "mean_test_sharpe_excl_artefact_fold"),
        ("Mean OOS Sharpe excl. that path's own worst fold", "mean_test_sharpe_excl_worst_fold"),
        ("Median OOS Sharpe", "median_test_sharpe"),
        ("Std OOS Sharpe", "std_test_sharpe"),
        ("Min OOS Sharpe", "min_test_sharpe"),
        ("Max OOS Sharpe", "max_test_sharpe"),
        ("Positive folds", "pct_positive_sharpe"),
        ("Pooled OOS trades", "total_test_trades"),
    ):
        pv = pub[key]
        cv = cor[key]
        if isinstance(pv, int):
            lines.append(f"| {label} | {pv} | {cv} |")
        elif key == "pct_positive_sharpe":
            lines.append(f"| {label} | {pv:.2%} | {cv:.2%} |")
        else:
            lines.append(f"| {label} | {pv:.6f} | {cv:.6f} |")
    lines.append("")
    pub_detail = pub["artefact_fold_detail"]
    cor_detail = cor["artefact_fold_detail"]
    lines.append(
        f"The default path's minimum fold is fold {pub['worst_fold']} "
        f"({pub['worst_fold_test_start']} .. {pub['worst_fold_test_end']}, OOS Sharpe "
        f"{pub['worst_fold_test_sharpe']:.6f}) -- the numerical artefact documented in Cycle "
        f"925 section 5. The published per-fold Sharpe is computed on the **backtest-baseline "
        f"scale** (`(CAGR - 2%) / annualised volatility`, "
        f"`src/backtest/engine.py::compute_metrics`), and on this fold that estimator divides a "
        f"near-zero numerator by a near-zero denominator: **{pub_detail['n_flat_sessions']} of "
        f"{pub_detail['n_sessions']} sessions are flat**, the segment's mean daily return is "
        f"{pub_detail['mean_daily_return']:.3e} and its dispersion "
        f"{pub_detail['std_daily_return']:.3e}. On the corrected path the same segment is "
        f"**{cor_detail['n_flat_sessions']} of {cor_detail['n_sessions']} sessions flat** (zero "
        f"dispersion), which the estimator returns as "
        f"{cor['artefact_fold_test_sharpe']:.6f} and the corrected path's own worst fold is fold "
        f"{cor['worst_fold']} ({cor['worst_fold_test_sharpe']:.6f}). **The corrected path's "
        f"higher all-fold mean is therefore a zero replacing a pathology, not a better "
        f"strategy**: on the strictest comparable statistic (both paths with the same fold "
        f"{ARTEFACT_FOLD} excluded) the corrected path is **lower** "
        f"({cor['mean_test_sharpe_excl_artefact_fold']:.6f} vs "
        f"{pub['mean_test_sharpe_excl_artefact_fold']:.6f}), and so is each path's mean "
        f"excluding its own worst fold ({cor['mean_test_sharpe_excl_worst_fold']:.6f} vs "
        f"{pub['mean_test_sharpe_excl_worst_fold']:.6f})."
    )
    lines.append("")
    lines.append("### 4.2 The committed paper-trading record")
    lines.append("")
    lines.append("| Statistic | Published (default path) | Corrected path |")
    lines.append("|---|---|---|")
    pr = rec["published"]
    cr = rec["corrected"]
    lines.append(f"| Sessions | {pr['n_sessions']} | {cr['n_sessions']} |")
    lines.append(
        f"| Canonical Sharpe | {pr['canonical_sharpe']:.6f} | {cr['canonical_sharpe']:.6f} |"
    )
    lines.append(
        f"| Trailing 63-session Sharpe (`rolling_63d_sharpe` gate value) | "
        f"{pr['trailing_63d_sharpe']:.6f} | {cr['trailing_63d_sharpe']:.6f} |"
    )
    lines.append(
        f"| `rolling_63d_sharpe` gate (>= {rec['gate_threshold_rolling']}) | "
        f"**{'PASS' if pr['rolling_gate_passes'] else 'FAIL'}** | "
        f"**{'PASS' if cr['rolling_gate_passes'] else 'FAIL'}** |"
    )
    lines.append(
        f"| PSR (normal) vs {PSR_TARGET} | {pr['psr_normal']:.6f} | {cr['psr_normal']:.6f} |"
    )
    lines.append(
        f"| PSR (empirical) vs {PSR_TARGET} | {pr['psr_empirical']:.6f} | "
        f"{cr['psr_empirical']:.6f} |"
    )
    lines.append(
        f"| PSR Sharpe SE | {pr['psr_sharpe_se']:.6f} | {cr['psr_sharpe_se']:.6f} |"
    )
    lines.append(f"| Max drawdown | {pr['max_drawdown']:.6%} | {cr['max_drawdown']:.6%} |")
    lines.append(
        f"| `psr` gate (>= {rec['gate_threshold_psr']}) | "
        f"**{'PASS' if pr['psr_gate_passes'] else 'FAIL'}** | "
        f"**{'PASS' if cr['psr_gate_passes'] else 'FAIL'}** |"
    )
    lines.append("")
    lines.append(
        f"PSR settings (the repository's own): `n_bootstrap={rec['psr_settings']['n_bootstrap']}`, "
        f"`block_size={rec['psr_settings']['block_size']}`, `seed={rec['psr_settings']['seed']}`, "
        f"target {rec['psr_settings']['target']}."
    )
    lines.append("")
    lines.append("### 4.3 The production promotion-gate table")
    lines.append("")
    lines.append("| Gate | Published record | Corrected record | Threshold |")
    lines.append("|---|---|---|---|")
    gp = rec["production_gates_published"]
    gc = rec["production_gates_corrected"]
    thresholds = {
        "track_record_length": ">= 126",
        "full_period_sharpe": ">= 0.9",
        "rolling_63d_sharpe": ">= 0.9",
        "max_drawdown": ">= -0.15",
        "rolling_63d_max_dd": ">= -0.15",
        "regime_flips": ">= 1",
        "psr": ">= 0.95",
    }
    for name, value in gp["gates"].items():
        lines.append(
            f"| `{name}` | {value:.6f} | {gc['gates'].get(name, float('nan')):.6f} | "
            f"{thresholds.get(name, '')} |"
        )
    lines.append(
        f"| **decision** | **{gp['decision']}** | **{gc['decision']}** | failed gates: "
        f"{', '.join(gc['failed_gates'])} |"
    )
    lines.append("")
    lines.append(
        "The corrected record's gate table is computed by the production code "
        "(`src/simulation/evaluation.py::evaluate_go_no_go`) on the corrected return series "
        "with the committed configuration; only the return series and the dates are "
        "substituted, because the promotion gates consume only the returns, the dates, the "
        "run-history turnover and the run-history regime exposure."
    )
    lines.append("")
    lines.append("### 4.4 The PSR reference a corrected live record would face")
    lines.append("")
    test_period = rec["test_period_2018_2026"]
    lines.append(
        "The `psr` gate compares the live record's Sharpe with a **fixed backtest-baseline "
        f"Sharpe of {PSR_TARGET}**, which was measured on the **2018-2026 test period of the "
        "same-session path** (`research/run_cycle7.py::DOCUMENTED`). A live record produced on "
        "the corrected path would be measured against a reference computed on a different "
        f"path, so the corrected equivalent of that reference is measured here, on the "
        f"published **Cycle 7 data vintage** (panel truncated at {test_period['vintage_end']}; "
        f"the committed cache now extends 8 sessions further, which is why the published "
        f"vintage is the reproducible one)."
    )
    lines.append("")
    lines.append("| Test-period statistic (2018-2026) | Published (same-session) | Corrected |")
    lines.append("|---|---|---|")
    for label, key, fmt in (
        ("Sharpe (the backtest-baseline scale)", "sharpe_ratio", "{:.6f}"),
        ("Max drawdown", "max_drawdown", "{:.6f}"),
        ("Trade count", "trade_count", "{:d}"),
        ("Annualized return", "annualized_return", "{:.6f}"),
        ("Annualized turnover", "annualized_turnover", "{:.4f}"),
        ("Annualized volatility", "annualized_volatility", "{:.6f}"),
    ):
        pub_value = test_period["published"][key]
        cor_value = test_period["corrected"][key]
        if key == "trade_count":
            pub_value = int(pub_value)
            cor_value = int(cor_value)
        lines.append(
            f"| {label} | {fmt.format(pub_value)} | {fmt.format(cor_value)} |"
        )
    lines.append("")
    lines.append(
        f"The published test-period reference **{test_period['published']['sharpe_ratio']:.6f}** "
        f"is reproduced together with all {len(PUBLISHED_TEST_PERIOD)} documented values of "
        f"`research/run_cycle7.py::DOCUMENTED` (max DD "
        f"{test_period['published']['max_drawdown']:.6f}, "
        f"{int(test_period['published']['trade_count'])} trades, annualized return "
        f"{test_period['published']['annualized_return']:.6f}). The corrected path's "
        f"test-period Sharpe is **{test_period['corrected']['sharpe_ratio']:.6f}**, i.e. "
        f"{test_period['corrected']['sharpe_ratio'] - test_period['published']['sharpe_ratio']:+.6f} "
        f"against the same-session path. A live record on the corrected path compared against "
        f"the *unchanged* reference {PSR_TARGET} would therefore face a **stricter** bar than "
        f"its own path's backtest -- the comparison stays conservative -- while compared "
        f"against its own path's reference it would face the honest one. The fixed reference "
        f"{PSR_TARGET} is **not** restated by this cycle: changing a gate target is a "
        f"promotion decision and is out of scope here."
    )
    lines.append("")

    lines.append("## 5. Blast radius")
    lines.append("")
    lines.append("### 5.1 Code paths that use the same-session estimate")
    lines.append("")
    lines.append("| Path | Kind | Role | State after this cycle |")
    lines.append("|---|---|---|---|")
    for entry in payload["blast_radius"]["code_paths"]:
        lines.append(
            f"| `{entry['path']}` | {entry['kind']} | {entry['role']} | {entry['state']} |"
        )
    lines.append("")
    lines.append("### 5.2 Committed artefacts that quote the affected statistics")
    lines.append("")
    lines.append(
        "Measured by searching the committed tree for the published numeric markers, so the "
        f"inventory cannot drift from the repository's content: "
        f"{payload['blast_radius']['n_distinct_affected_files']} distinct committed files quote "
        f"at least one of them."
    )
    lines.append("")
    lines.append("| Marker | Statistic | Committed files quoting it |")
    lines.append("|---|---|---|")
    for item in payload["blast_radius"]["committed_artifacts"]:
        lines.append(
            f"| `{item['marker']}` | {item['description']} | {item['n_files']} |"
        )
    lines.append("")
    for item in payload["blast_radius"]["committed_artifacts"]:
        if not item["files"]:
            continue
        lines.append(f"- `{item['marker']}` ({item['description']}):")
        for rel in item["files"]:
            lines.append(f"  - `{rel}`")
    lines.append("")

    lines.append("## 6. Decision recommendation")
    lines.append("")
    decision = payload["decision"]
    lines.append(f"**Recommendation: {decision['recommendation']}.**")
    lines.append("")
    lines.append(decision["reason"])
    lines.append("")
    lines.append("### Re-derivation plan (a plan, not an execution)")
    lines.append("")
    for step in decision["re_derivation_plan"]:
        lines.append(f"{step}")
    lines.append("")

    lines.append("## 7. What this cycle does NOT change")
    lines.append("")
    lines.append(
        "- It does **not** cause the `rolling_63d_sharpe` failure: the corrected failing "
        f"window is *worse* ({rec['corrected']['trailing_63d_sharpe']:.6f} vs "
        f"{rec['published']['trailing_63d_sharpe']:.6f})."
    )
    lines.append(
        "- It does **not** rescue the promotion decision: the PSR gate still fails on the "
        f"corrected path ({rec['corrected']['psr_normal']:.6f} < {rec['gate_threshold_psr']}), "
        f"and the decision stays {rec['production_gates_corrected']['decision']}."
    )
    lines.append(
        "- It does **not** change the incumbent's published verdict: the candidate remains a "
        "**Credible Candidate** by its published verdict and **NO-GO** for promotion."
    )
    lines.append(
        "- The corrected walk-forward mean is **not** an edge, a recovery or a promotion: on "
        "the comparable statistic it is lower than the published path."
    )
    lines.append(
        "- The published walk-forward record, the committed paper-trading state, the gate "
        "table, the thresholds, the universe, the cost model, the Sharpe convention and the "
        "hypotheses are **untouched**."
    )
    lines.append("")

    lines.append("## 8. Checks")
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

    lines.append("## 9. Reproduction commands")
    lines.append("")
    lines.append("```bash")
    lines.append("python research/tsmomentum_same_session_vol_correction.py")
    lines.append("python -m pytest -q tests/test_tsmomentum_same_session_vol_correction.py")
    lines.append("python -m pytest -q")
    lines.append("git status --porcelain data/ config/")
    lines.append("```")
    lines.append("")
    lines.append("## 10. JSON payload")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(payload, indent=2, default=str, sort_keys=True))
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def render_experiment(payload: dict[str, Any]) -> str:
    anchor = payload["anchor"]
    wf = payload["walk_forward"]
    rec = payload["record"]
    lines: list[str] = []
    lines.append(
        f"# Experiment: Same-session volatility estimate -- opt-in correction and "
        f"side-by-side re-derivation for `{payload['candidate']}` "
        f"(tsmomentum_same_session_vol_correction_001, Cycle {payload['cycle']})"
    )
    lines.append("")
    lines.append("## Hypothesis reference")
    lines.append("")
    lines.append("- Incumbent hypothesis: `research/hypotheses/tsmomentum_004.md`")
    lines.append(
        "- Prior cycles reused: Cycle 866 (rolling-gate base rate), Cycle 910 (fold design), "
        "Cycle 921 (PSR target), Cycle 925 (the rolling-63d diagnosis and the discovery of "
        "the same-session measurement defect)"
    )
    lines.append("")
    lines.append("## Objective")
    lines.append("")
    lines.append(
        "Make the same-session volatility estimate correctable behind a default-off, opt-in "
        "switch, and re-derive the incumbent's published record on the corrected path in a "
        "new artifact. Measurement and remediation planning only: no gate, threshold, "
        "universe, cost model, Sharpe convention, parameter, hypothesis or drift flag is "
        "changed, and no candidate is promoted, re-fit or re-ranked."
    )
    lines.append("")
    lines.append("## Data")
    lines.append("")
    lines.append(
        f"- Committed paper-trading record: {rec['published']['n_sessions']} sessions "
        "(2025-01-02 .. 2026-10-19)"
    )
    lines.append(
        "- Price panel: committed parquet cache `data/raw/*.parquet` (cache-only; the fetcher "
        "is never called)"
    )
    lines.append(f"- Universe: {', '.join(SYMBOLS)}")
    lines.append(
        f"- Cost model: {COMMISSION_BPS * 10000.0:.1f} bps commission + "
        f"{SLIPPAGE_BPS * 10000.0:.1f} bps slippage = "
        f"{(COMMISSION_BPS + SLIPPAGE_BPS) * 10000.0:.1f} bps round-trip"
    )
    lines.append(
        "- Point-in-time treatment: momentum weights shifted one session; the SPY SMA filter "
        "and the trailing volatility window are computed on the cached panel; the published "
        "walk-forward design (10y train / 12m test / 6m step, 21d purge, 21d embargo) is "
        "reused unchanged"
    )
    lines.append("")
    lines.append("## Configuration")
    lines.append("")
    lines.append(f"- Signal: TSMOM lookback {LOOKBACK}, skip {SKIP}, top_fraction {TOP_FRACTION}")
    lines.append(
        f"- Overlay: vol-target {VOL_TARGET} (lookback {VOL_TARGET_LOOKBACK}) + drawdown "
        f"control {DD_THRESHOLD} + SPY {SPY_SMA_WINDOW}-day SMA filter"
    )
    lines.append(
        f"- Switch: `lag_vol_estimate`, default **off**; the corrected path sets it to True "
        f"in the research path (`research/run_cycle6.py::_apply_overlay`) and in the shared "
        f"engine (`src/simulation/engine.py::SimulationConfig.lag_vol_estimate`)"
    )
    lines.append(
        f"- PSR: target {PSR_TARGET}, `n_bootstrap={PSR_N_BOOTSTRAP}`, "
        f"`block_size={PSR_BLOCK_SIZE}`, `seed={PSR_SEED}` (the repository's own settings)"
    )
    lines.append(
        f"- Gates read from `config/promotion_gates.yaml`: `rolling_63d_sharpe` >= "
        f"{rec['gate_threshold_rolling']}, `psr` >= {rec['gate_threshold_psr']}"
    )
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("### Anchor (fail closed)")
    lines.append("")
    lines.append(
        f"- Published 48-fold walk-forward mean OOS Sharpe reproduced: "
        f"**{anchor['reproduced_wf_mean']:.6f}** (published {anchor['published_wf_mean']:.6f}); "
        f"the published machinery reproduces **{anchor['machinery_wf_mean']:.6f}**"
    )
    lines.append(
        f"- Committed record's {anchor['committed_sessions']} sessions reproduced with max "
        f"|diff| = {anchor['record_max_abs_diff']:.3e}"
    )
    lines.append(
        f"- Default path bit-identical to the pre-change implementation: research path "
        f"{anchor['research_path_max_abs_diff']:.1e}, simulation path "
        f"{anchor['simulation_path_max_abs_diff']:.1e}, risk overlays "
        f"{anchor['risk_overlay_max_abs_diff']:.1e}"
    )
    lines.append("")
    lines.append("### Side by side")
    lines.append("")
    lines.append(
        f"- Walk-forward mean OOS Sharpe: {wf['published']['mean_test_sharpe']:.6f} -> "
        f"{wf['corrected']['mean_test_sharpe']:.6f} (all folds); excluding each path's own "
        f"worst fold: {wf['published']['mean_test_sharpe_excl_worst_fold']:.6f} -> "
        f"{wf['corrected']['mean_test_sharpe_excl_worst_fold']:.6f}"
    )
    lines.append(
        f"- Record canonical Sharpe: {rec['published']['canonical_sharpe']:.6f} -> "
        f"{rec['corrected']['canonical_sharpe']:.6f}"
    )
    lines.append(
        f"- Trailing 63-session Sharpe (`rolling_63d_sharpe`): "
        f"{rec['published']['trailing_63d_sharpe']:.6f} -> "
        f"{rec['corrected']['trailing_63d_sharpe']:.6f}"
    )
    lines.append(
        f"- PSR vs {PSR_TARGET}: {rec['published']['psr_normal']:.6f} -> "
        f"{rec['corrected']['psr_normal']:.6f}"
    )
    lines.append(
        f"- Promotion decision: {rec['production_gates_published']['decision']} -> "
        f"{rec['production_gates_corrected']['decision']} (failed gates: "
        f"{', '.join(rec['production_gates_corrected']['failed_gates'])})"
    )
    lines.append("")
    lines.append("## Trial count")
    lines.append("")
    lines.append(
        "- 1 anchor reproduction (published machinery, 48 folds) + 2 paths (default, "
        "corrected) + 1 frozen-implementation bit-identity comparison per code path; no "
        "per-fold re-optimisation, no candidate selection, no configuration search."
    )
    lines.append("")
    lines.append("## Verdict")
    lines.append("")
    for para in payload["verdict"].split("\n\n"):
        lines.append(para)
        lines.append("")
    lines.append("## Reproduction")
    lines.append("")
    lines.append("```bash")
    lines.append("python research/tsmomentum_same_session_vol_correction.py")
    lines.append("python -m pytest -q tests/test_tsmomentum_same_session_vol_correction.py")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--report-out", type=Path, default=OUT_REPORT)
    parser.add_argument("--experiment-out", type=Path, default=OUT_EXP)
    parser.add_argument(
        "--no-report", action="store_true", help="do not write the report or experiment record"
    )
    args = parser.parse_args(argv)

    payload = run_correction(raw_dir=args.raw_dir)

    if not args.no_report:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.experiment_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(render_report(payload), encoding="utf-8")
        args.experiment_out.write_text(render_experiment(payload), encoding="utf-8")

    anchor = payload["anchor"]
    rec = payload["record"]
    wf = payload["walk_forward"]
    print(f"OVERALL: {payload['overall']}")
    print(
        f"anchor: 48-fold WF mean {anchor['reproduced_wf_mean']:.6f} "
        f"(published {anchor['published_wf_mean']:.6f}); committed record "
        f"{anchor['committed_sessions']} sessions, max |diff| = "
        f"{anchor['record_max_abs_diff']:.3e}"
    )
    print(
        f"bit-identity: research {anchor['research_path_max_abs_diff']:.1e}, simulation "
        f"{anchor['simulation_path_max_abs_diff']:.1e}, risk overlays "
        f"{anchor['risk_overlay_max_abs_diff']:.1e}"
    )
    print(
        f"record Sharpe: published {rec['published']['canonical_sharpe']:.6f} -> corrected "
        f"{rec['corrected']['canonical_sharpe']:.6f}"
    )
    print(
        f"trailing 63d: published {rec['published']['trailing_63d_sharpe']:.6f} -> corrected "
        f"{rec['corrected']['trailing_63d_sharpe']:.6f}"
    )
    print(
        f"PSR vs {PSR_TARGET}: published {rec['published']['psr_normal']:.6f} -> corrected "
        f"{rec['corrected']['psr_normal']:.6f}"
    )
    print(
        f"WF mean: published {wf['published']['mean_test_sharpe']:.6f} -> corrected "
        f"{wf['corrected']['mean_test_sharpe']:.6f} (excl. own worst fold: "
        f"{wf['published']['mean_test_sharpe_excl_worst_fold']:.6f} -> "
        f"{wf['corrected']['mean_test_sharpe_excl_worst_fold']:.6f})"
    )
    print(
        f"decision: published {rec['production_gates_published']['decision']}, corrected "
        f"{rec['production_gates_corrected']['decision']}"
    )
    print(f"recommendation: {payload['decision']['recommendation']}")
    print(f"incumbent: {payload['incumbent_verdict']}")
    print(f"report: {args.report_out}" if not args.no_report else "--no-report: no artifacts written")
    return 0 if payload["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
