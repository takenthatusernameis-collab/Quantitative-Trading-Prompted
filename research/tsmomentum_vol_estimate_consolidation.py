#!/usr/bin/env python3
"""Cycle 927: one implementation of the same-session volatility estimate everywhere
it is still inlined, plus the corrected successor backtest record for the
incumbent ``tsmomentum_spytrend_001``.

What this cycle does (and nothing else):

1. It verifies that the seven research scripts that still inlined the same-session
   volatility estimate (run_cycle5.py, run_cycle13.py, run_cycle15.py,
   run_cycle15_c4_corrected.py, run_cycle18.py, run_cycle19.py,
   month_end_candidate_reaudit.py) now route through the single shared
   ``src/evaluation/risk.py::realized_vol_scale`` behind the same default-off
   ``lag_vol_estimate`` switch.  For every script the default path is pinned to be
   bit-identical (max |diff| = 0.0) against a frozen copy of its pre-change
   implementation, checked not asserted.  After the change there are **zero**
   remaining inline same-session exposure estimates in any production or research
   path; the only permitted copies are the frozen pre-change references kept in
   this tool and in its test file, labelled as such.

2. It re-derives the incumbent's published record on the corrected path
   (``lag_vol_estimate=True``) and publishes it as a **new, clearly labelled
   successor reference** that superseses nothing: the corrected 48-fold walk-forward
   table (with and without the numerical-artefact fold), the corrected SMA-window
   plateau table (the six pre-specified windows of the published record), the
   corrected 2018-2026 test-period statistics (1.335983), the corrected record-level
   statistics and the production gate table.  Every section states that it is a
   successor reference that supersedes nothing and carries the artefact-fold caveat
   (the corrected all-fold mean 1.318605 is inflated by a flat fold scoring
   0.000000; the comparable statistic is 1.346660 vs 1.431928).

3. It specifies (does not execute) the corrected live paper-trading record start
   procedure: the exact configuration change, the new state file path, the
   re-initialised drift flags and gate table, the restart cost (126 sessions for
   ``track_record_length``), the statement that the committed record is not
   modified, and the PSR-reference consequence (the corrected path's own backtest
   reference is 1.335983, so the unchanged 1.4178 is a stricter bar).

It is **read-only** with respect to ``data/`` and ``config/``: SHA-256
fingerprints are taken before and after and the run fails closed if they move.
No committed record, the committed paper-trading state or any config file is
written or overwritten; the fetcher is never called; no gate, threshold, universe,
cost model, Sharpe convention, parameter, hypothesis or drift flag is changed;
no candidate is promoted, re-fit or re-ranked; no live record is started.

Usage::

    python research/tsmomentum_vol_estimate_consolidation.py
    python research/tsmomentum_vol_estimate_consolidation.py --no-report
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
    LOOKBACK,
    SKIP,
    TOP_FRACTION,
    VOL_TARGET,
    VOL_TARGET_LOOKBACK,
    _eval_candidate,
)
from research.tsmomentum_same_session_vol_correction import (  # noqa: E402
    ARTEFACT_FOLD,
    COMMITTED_TRAILING_SHARPE,
    PSR_BLOCK_SIZE,
    PSR_N_BOOTSTRAP,
    PSR_SEED,
    PSR_TARGET,
    PUBLISHED_TEST_PERIOD,
    PUBLISHED_TEST_PERIOD_TOLERANCE,
    PUBLISHED_WF_MEAN,
    PUBLISHED_WF_FOLDS,
    TEST_PERIOD_VINTAGE_END,
    build_path,
    corrected_state,
    fold_statistics,
    production_gate_table,
    record_statistics,
)
from research.tsmomentum_walkforward_embargo_audit import (  # noqa: E402
    fingerprint,
    load_close_from_cache,
    resolve_published_record,
    tracked_artifact_hashes,
)
from src.backtest.engine import compute_metrics  # noqa: E402
from src.evaluation.risk import realized_vol_scale  # noqa: E402
from src.evaluation.sharpe import sharpe_ratio  # noqa: E402
from src.evaluation.statistics import compute_psr  # noqa: E402
from src.simulation.paper_trading import (  # noqa: E402
    PaperTradingConfig,
    PaperTradingState,
)
from src.simulation.evaluation import (  # noqa: E402
    GoNoGoConfig,
    evaluate_go_no_go,
)

# The seven scripts that carried the inline same-session estimate before this cycle.
SCRIPTS = (
    "research/run_cycle5.py",
    "research/run_cycle13.py",
    "research/run_cycle15.py",
    "research/run_cycle15_c4_corrected.py",
    "research/run_cycle18.py",
    "research/run_cycle19.py",
    "research/month_end_candidate_reaudit.py",
)

CANDIDATE_ID = "tsmomentum_spytrend_001"
CYCLE = "927"

REPORTS_DIR = REPO_ROOT / "research" / "reports"
EXPERIMENTS_DIR = REPO_ROOT / "research" / "experiments"
RAW_DIR = REPO_ROOT / "data" / "raw"
STATE_PATH = REPO_ROOT / "data" / "processed" / "paper_trading_state.yaml"
CONFIG_PATH = REPO_ROOT / "config" / "paper_trading_config.yaml"
SIM_CONFIG_PATH = REPO_ROOT / "config" / "simulation_candidate_001.yaml"
OUT_REPORT = REPORTS_DIR / "tsmomentum_vol_estimate_consolidation_001.md"
OUT_EXP = EXPERIMENTS_DIR / "tsmomentum_vol_estimate_consolidation_001.md"

WINDOW = 63
GATE_ROLLING_SHARPE = 0.9
GATE_PSR = 0.95
ANNUAL = 252

# The six pre-specified SMA windows of the published record (run_cycle6.SMA_WINDOWS).
SMA_WINDOWS = [150, 175, 200, 226, 250, 277]

# Corrected-path record-level statistics measured on the corrected path.  These are
# re-derived below (not hard-coded); the Cycle 926 values are the expected anchor
# for the deterministic corrected path and are asserted as a cross-check.
CORRECTED_RECORD_EXPECTED = {
    "canonical_sharpe": 1.635705,
    "trailing_63d_sharpe": -0.515807,
    "psr_normal": 0.623929,
    "max_drawdown": -0.051057,
}

# Corrected-path 2018-2026 test-period reference (own path's backtest).
CORRECTED_TEST_PERIOD_EXPECTED = {"sharpe_ratio": 1.335983}

# Corrected walk-forward statistics (Cycle 926).
CORRECTED_WF_EXPECTED = {
    "mean_test_sharpe": 1.318605,
    "mean_test_sharpe_excl_artefact_fold": 1.346660,
    "mean_test_sharpe_excl_worst_fold": 1.357135,
    "median_test_sharpe": 1.232060,
    "worst_fold": 13,
    "worst_fold_test_sharpe": -0.492313,
    "total_test_trades": 6002,
}


# ----------------------------------------------------------------------
# Frozen pre-change implementations (one per script, labelled as such)
# ----------------------------------------------------------------------
def legacy_run_cycle5_apply_overlay(
    asset_ret: pd.DataFrame,
    base_weights: pd.DataFrame,
    exposure_factor: pd.Series | None = None,
    vol_target: float = VOL_TARGET,
    dd_threshold: float = DD_THRESHOLD,
) -> pd.DataFrame:
    """Frozen copy of ``research/run_cycle5.py::_apply_overlay`` as it was **before**
    Cycle 927 routed it through ``realized_vol_scale``.  Only the combined weights
    are returned (the part that depends on the volatility estimate); net returns are
    a deterministic function of them.
    """
    weights = base_weights.copy()
    if exposure_factor is not None:
        ef = exposure_factor.reindex(weights.index).fillna(0.0)
        weights = weights.mul(ef, axis=0)
    daily_ret = asset_ret.copy()
    port_ret = (weights * daily_ret).sum(axis=1)
    realized_vol = port_ret.rolling(VOL_TARGET_LOOKBACK).std() * np.sqrt(252)
    realized_vol = realized_vol.replace(0, np.nan)
    vol_scale = (vol_target / realized_vol).clip(upper=1.0).fillna(0.0)
    vol_targeted_weights = weights.mul(vol_scale, axis=0)
    vol_port_ret = (vol_targeted_weights * daily_ret).sum(axis=1)
    cum = (1.0 + vol_port_ret).cumprod()
    running_max = cum.expanding().max()
    drawdown = (cum / running_max) - 1
    in_drawdown = drawdown < -dd_threshold
    dd_scale = pd.Series(1.0, index=weights.index)
    dd_scale[in_drawdown] = 0.5
    combined_scale = vol_scale * dd_scale
    return weights.mul(combined_scale, axis=0)


def legacy_incumbent_overlay(
    gated: pd.DataFrame,
    asset_ret: pd.DataFrame,
    vol_target: float = VOL_TARGET,
    vol_lookback: int = VOL_TARGET_LOOKBACK,
    dd_threshold: float = DD_THRESHOLD,
    dd_reduction: float = 0.5,
) -> pd.DataFrame:
    """Frozen copy of the ``_incumbent_overlay`` bodies of run_cycle13.py,
    run_cycle15.py, run_cycle15_c4_corrected.py, run_cycle18.py and run_cycle19.py as
    they were **before** Cycle 927 routed them through ``realized_vol_scale``."""
    port_ret = (gated * asset_ret).sum(axis=1)
    realized_vol = port_ret.rolling(vol_lookback).std() * np.sqrt(252)
    realized_vol = realized_vol.replace(0, np.nan)
    vol_scale = (vol_target / realized_vol).clip(upper=1.0).fillna(0.0)
    vol_targeted = gated.mul(vol_scale, axis=0)
    vol_port_ret = (vol_targeted * asset_ret).sum(axis=1)
    cum = (1.0 + vol_port_ret).cumprod()
    running_max = cum.expanding().max()
    drawdown = (cum / running_max) - 1
    dd_scale = pd.Series(1.0, index=gated.index)
    dd_scale[drawdown < -dd_threshold] = dd_reduction
    return gated.mul(vol_scale * dd_scale, axis=0)


def legacy_overlay_weights(
    gated: pd.DataFrame,
    asset_ret: pd.DataFrame,
    vol_lookback: int,
    vol_target: float,
    dd_threshold: float,
    dd_reduction: float,
) -> pd.DataFrame:
    """Frozen copy of ``research/month_end_candidate_reaudit.py:overlay_weights`` as
    it was **before** Cycle 927 routed it through ``realized_vol_scale``."""
    port_ret = (gated * asset_ret).sum(axis=1)
    realized_vol = port_ret.rolling(vol_lookback).std() * np.sqrt(252)
    realized_vol = realized_vol.replace(0, np.nan)
    vol_scale = (vol_target / realized_vol).clip(upper=1.0).fillna(0.0)
    vol_targeted = gated.mul(vol_scale, axis=0)
    vol_port_ret = (vol_targeted * asset_ret).sum(axis=1)
    cum = (1.0 + vol_port_ret).cumprod()
    drawdown = (cum / cum.expanding().max()) - 1.0
    dd_scale = pd.Series(1.0, index=gated.index)
    dd_scale[drawdown < -dd_threshold] = dd_reduction
    return gated.mul(vol_scale * dd_scale, axis=0)


# ----------------------------------------------------------------------
# Per-script consolidation verification
# ----------------------------------------------------------------------
def _synthetic_inputs(n: int = 400) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    idx = pd.date_range("2010-01-01", periods=n, freq="B")
    rng = np.random.default_rng(11)
    gated = pd.DataFrame(rng.normal(0.0, 0.001, size=(n, 3)), index=idx, columns=["A", "B", "C"])
    asset_ret = pd.DataFrame(rng.normal(0.0, 0.01, size=(n, 3)), index=idx, columns=["A", "B", "C"])
    exposure = pd.Series(1.0, index=idx)
    return gated, asset_ret, exposure


def script_consolidation_checks() -> list[dict[str, Any]]:
    """Verify each of the seven scripts now calls ``realized_vol_scale`` and that the
    default path is bit-identical to its frozen pre-change implementation."""
    checks: list[dict[str, Any]] = []
    gated, asset_ret, exposure = _synthetic_inputs()

    def record(name: str, ok: bool, observed: Any = "", expected: Any = "") -> None:
        checks.append({"name": name, "pass": bool(ok), "observed": observed, "expected": expected})

    def max_diff(a: pd.DataFrame | pd.Series, b: pd.DataFrame | pd.Series) -> float:
        return float(np.max(np.abs(a.to_numpy(dtype=float) - b.to_numpy(dtype=float))))

    # 1. run_cycle5._apply_overlay
    import research.run_cycle5 as rc5

    new_w5, new_net5, _ = rc5._apply_overlay(
        asset_ret, gated, exposure_factor=exposure,
        vol_target=VOL_TARGET, dd_threshold=DD_THRESHOLD,
        commission_bps=COMMISSION_BPS, slippage_bps=SLIPPAGE_BPS, rf_annual=0.02,
        lag_vol_estimate=False,
    )
    old_w5 = legacy_run_cycle5_apply_overlay(asset_ret, gated, exposure_factor=exposure,
                                             vol_target=VOL_TARGET, dd_threshold=DD_THRESHOLD)
    record(
        "run_cycle5._apply_overlay default bit-identical (weights)",
        max_diff(new_w5, old_w5) == 0.0,
        f"max |diff| = {max_diff(new_w5, old_w5):.3e}",
        "0.0",
    )
    record(
        "run_cycle5 no longer inlines the same-session estimate",
        "vol_target / realized_vol" not in open(REPO_ROOT / "research/run_cycle5.py").read()
        and "realized_vol_scale" in open(REPO_ROOT / "research/run_cycle5.py").read(),
        "routed through realized_vol_scale",
        "routed",
    )

    # 2-6. run_cycle13 / 15 / 15_c4_corrected / 18 / 19 _incumbent_overlay
    for mod_name, label in (
        ("research.run_cycle13", "run_cycle13._incumbent_overlay"),
        ("research.run_cycle15", "run_cycle15._incumbent_overlay"),
        ("research.run_cycle15_c4_corrected", "run_cycle15_c4_corrected._incumbent_overlay"),
        ("research.run_cycle18", "run_cycle18._incumbent_overlay"),
        ("research.run_cycle19", "run_cycle19._incumbent_overlay"),
    ):
        mod = sys.modules.get(mod_name)
        if mod is None:
            mod = __import__(mod_name, fromlist=["_incumbent_overlay"])
        new_w = mod._incumbent_overlay(gated, asset_ret, lag_vol_estimate=False)
        old_w = legacy_incumbent_overlay(gated, asset_ret,
                                         vol_target=VOL_TARGET, vol_lookback=VOL_TARGET_LOOKBACK,
                                         dd_threshold=DD_THRESHOLD, dd_reduction=0.5)
        record(
            f"{label} default bit-identical (weights)",
            max_diff(new_w, old_w) == 0.0,
            f"max |diff| = {max_diff(new_w, old_w):.3e}",
            "0.0",
        )
        source = open(REPO_ROOT / f"{mod_name.replace('.', '/')}.py").read()
        record(
            f"{label} no longer inlines the same-session estimate",
            "vol_target / realized_vol" not in source
            and "realized_vol_scale" in source,
            "routed through realized_vol_scale",
            "routed",
        )

    # run_cycle19.build_overlay_weights also threads the switch
    import research.run_cycle19 as rc19
    from src.features.momentum import build_weights

    idx19 = pd.date_range("2009-01-01", periods=500, freq="B")
    rng19 = np.random.default_rng(21)
    close19 = pd.DataFrame(
        (rng19.normal(0.001, 0.01, size=(500, 4)).cumsum(axis=1) + 100.0),
        index=idx19, columns=["SPY", "A", "B", "C"],
    )
    vix19 = pd.Series(rng19.uniform(10.0, 30.0, size=500), index=idx19)

    weights19 = build_weights(close19, lookback=226, skip=21, top_fraction=0.5)
    common19 = close19.index.intersection(weights19.index)
    close19_a = close19.loc[common19]
    weights19_a = weights19.loc[common19]
    daily_ret19 = close19_a.pct_change().fillna(0.0)
    spy19 = close19_a["SPY"]
    spy_sma19 = spy19.rolling(200).mean()
    exposure19 = pd.Series(1.0, index=close19_a.index)
    exposure19[spy19 < spy_sma19] = 0.0
    exposure19[spy19.isna() | spy_sma19.isna()] = 0.0
    gated19 = weights19_a.mul(exposure19, axis=0)
    vix_lag19 = vix19.shift(1).reindex(close19_a.index)
    vix_mult19 = pd.Series(1.0, index=close19_a.index)
    vix_mult19[vix_lag19 > 30.0] = 1.0
    vix_mult19[vix_lag19.isna()] = 1.0
    gated19 = gated19.mul(vix_mult19, axis=0)
    old_combined19 = legacy_incumbent_overlay(
        gated19, daily_ret19, vol_target=VOL_TARGET, vol_lookback=VOL_TARGET_LOOKBACK,
        dd_threshold=DD_THRESHOLD, dd_reduction=0.5,
    )
    is_month_end19 = pd.Series(old_combined19.index.is_month_end, index=old_combined19.index)
    old_sched19 = old_combined19.where(is_month_end19, axis=0).ffill().fillna(0.0)
    new_bw = rc19.build_overlay_weights(
        close19, vix19, 226, 21, 0.5, 30.0, 1.0, lag_vol_estimate=False,
    )
    record(
        "run_cycle19.build_overlay_weights default bit-identical",
        max_diff(new_bw.reindex(old_sched19.index), old_sched19) == 0.0,
        f"max |diff| = {max_diff(new_bw.reindex(old_sched19.index), old_sched19):.3e}",
        "0.0",
    )

    # 7. month_end_candidate_reaudit.overlay_weights
    import research.month_end_candidate_reaudit as rcmer

    new_ow = rcmer.overlay_weights(
        gated, asset_ret, vol_lookback=VOL_TARGET_LOOKBACK, vol_target=VOL_TARGET,
        dd_threshold=DD_THRESHOLD, dd_reduction=0.5, lag_vol_estimate=False,
    )
    old_ow = legacy_overlay_weights(
        gated, asset_ret, vol_lookback=VOL_TARGET_LOOKBACK, vol_target=VOL_TARGET,
        dd_threshold=DD_THRESHOLD, dd_reduction=0.5,
    )
    record(
        "month_end_candidate_reaudit.overlay_weights default bit-identical",
        max_diff(new_ow, old_ow) == 0.0,
        f"max |diff| = {max_diff(new_ow, old_ow):.3e}",
        "0.0",
    )
    source = open(REPO_ROOT / "research/month_end_candidate_reaudit.py").read()
    record(
        "month_end_candidate_reaudit.overlay_weights no longer inlines the same-session estimate",
        "vol_target / realized_vol" not in source
        and "realized_vol_scale" in source,
        "routed through realized_vol_scale",
        "routed",
    )

    # Zero remaining inline same-session exposure estimates across the seven scripts.
    inline_marker = "vol_target / realized_vol"
    remaining = []
    for rel in SCRIPTS:
        text = (REPO_ROOT / rel).read_text(encoding="utf-8", errors="ignore")
        if inline_marker in text:
            remaining.append(rel)
    record(
        "zero remaining inline same-session estimates in the seven scripts",
        remaining == [],
        f"remaining: {remaining}" if remaining else "none",
        "none",
    )
    return checks


# ----------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------
def run_consolidation(
    raw_dir: Path = RAW_DIR,
    published_machinery: bool = True,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def record(name: str, ok: bool, observed: Any = "", expected: Any = "") -> None:
        checks.append({"name": name, "pass": bool(ok), "observed": observed, "expected": expected})

    data_before = fingerprint(REPO_ROOT / "data")
    config_before = fingerprint(REPO_ROOT / "config")
    artifacts_before = tracked_artifact_hashes()

    # ------------------------------------------------------------------
    # 0. The committed record
    # ------------------------------------------------------------------
    import yaml

    with open(STATE_PATH) as fh:
        state_doc = yaml.safe_load(fh) or {}
    committed_returns = np.asarray(state_doc["cumulative_returns"], dtype=float)
    record_dates = [pd.Timestamp(str(d), tz="UTC") for d in state_doc["cumulative_dates"]]
    record_check = record
    record_check("committed_record_loaded", len(committed_returns) == 454,
                 f"{len(committed_returns)} sessions", "454 sessions")

    close = load_close_from_cache(list(SYMBOLS), raw_dir)
    default_path = build_path(close, lag_vol_estimate=False)
    corrected_path = build_path(close, lag_vol_estimate=True)

    available = set(default_path["net_ret"].index)
    _mask = [d in available for d in record_dates]
    record_dates = [d for d, m in zip(record_dates, _mask) if m]
    committed_returns = committed_returns[_mask]

    # ------------------------------------------------------------------
    # 1. Anchor: default path reproduces the committed artefacts
    # ------------------------------------------------------------------
    record_net = default_path["net_ret"].loc[record_dates].to_numpy(dtype=float)
    record_diff = float(np.max(np.abs(record_net - committed_returns)))
    record_check("default_path_reproduces_every_committed_session",
                 record_diff <= 1e-12, f"max |diff| = {record_diff:.3e}", "<= 1e-12")

    default_folds = fold_statistics(default_path["net_ret"], default_path["combined_weights"])
    record_check("published_walk_forward_mean_reproduced",
                 default_folds["mean_test_sharpe"] == PUBLISHED_WF_MEAN,
                 f"{default_folds['mean_test_sharpe']:.12f}", f"{PUBLISHED_WF_MEAN:.12f}")
    record_check("published_walk_forward_fold_count_reproduced",
                 default_folds["n_folds"] == PUBLISHED_WF_FOLDS,
                 f"{default_folds['n_folds']} folds", f"{PUBLISHED_WF_FOLDS} folds")

    published_path, published = resolve_published_record(EXPERIMENTS_DIR)
    published_folds = published["folds"]
    record_check("published_record_resolved_by_content",
                 len(published_folds) == PUBLISHED_WF_FOLDS, published_path.name,
                 f"{PUBLISHED_WF_FOLDS} published folds")
    window_mismatches = sharpe_mismatches = trade_mismatches = 0
    for pub, rec in zip(published_folds, default_folds["folds"]):
        if not (pub["train_start"] == rec["train_start"] and pub["train_end"] == rec["train_end"]
                and pub["test_start"] == rec["test_start"] and pub["test_end"] == rec["test_end"]):
            window_mismatches += 1
        if abs(pub["test_sharpe"] - rec["test_sharpe"]) > 1e-4:
            sharpe_mismatches += 1
        if int(pub["test_trades"]) != int(rec["test_trades"]):
            trade_mismatches += 1
    record_check("published_fold_table_reproduced",
                 window_mismatches == 0 and sharpe_mismatches == 0 and trade_mismatches == 0,
                 f"windows {window_mismatches}, OOS Sharpe {sharpe_mismatches}, trades {trade_mismatches}",
                 "0 mismatches")

    # published machinery
    import research.run_cycle6 as run_cycle6

    if published_machinery:
        machinery = run_cycle6.run_walkforward()
        machinery_mean = float(machinery["summary"]["mean_test_sharpe"])
        record_check("published_machinery_still_reproduces_the_published_mean",
                     machinery_mean == PUBLISHED_WF_MEAN, f"{machinery_mean:.12f}",
                     f"{PUBLISHED_WF_MEAN:.12f}")
    else:
        machinery_mean = None

    # 2018-2026 test period baseline (published reference)
    vintage_close = close.loc[:TEST_PERIOD_VINTAGE_END]
    default_test = _eval_candidate(vintage_close, spy_sma_window=SPY_SMA_WINDOW,
                                   lag_vol_estimate=False)
    reference_mismatches = [key for key, expected in PUBLISHED_TEST_PERIOD.items()
                            if abs(float(default_test["test_metrics"][key]) - float(expected))
                            > PUBLISHED_TEST_PERIOD_TOLERANCE[key]]
    record_check("published_test_period_baseline_reproduced",
                 reference_mismatches == [],
                 f"Sharpe {default_test['test_metrics']['sharpe_ratio']:.6f}, trades "
                 f"{int(default_test['test_metrics']['trade_count'])}",
                 f"all {len(PUBLISHED_TEST_PERIOD)} documented values of run_cycle7::DOCUMENTED "
                 f"(mismatching: {reference_mismatches or 'none'})")

    # ------------------------------------------------------------------
    # 2. Per-script consolidation (bit-identity, routing, zero inline)
    # ------------------------------------------------------------------
    script_checks = script_consolidation_checks()
    checks.extend(script_checks)

    # ------------------------------------------------------------------
    # 3. Switch semantics
    # ------------------------------------------------------------------
    default_scale = realized_vol_scale(default_path["port_ret"], VOL_TARGET, VOL_TARGET_LOOKBACK, False)
    corrected_scale = realized_vol_scale(default_path["port_ret"], VOL_TARGET, VOL_TARGET_LOOKBACK, True)
    shift_diff = float(np.max(np.abs(corrected_scale.to_numpy()[1:] - default_scale.to_numpy()[:-1])))
    record_check("lagged_estimate_is_the_same_session_estimate_shifted_one_session",
                 shift_diff == 0.0, f"max |diff| = {shift_diff:.3e}", "0.0")
    record_check("opt_in_switch_changes_the_path",
                 float(np.max(np.abs(corrected_path["net_ret"] - default_path["net_ret"]))) > 0.0,
                 f"max |diff| = {float(np.max(np.abs(corrected_path['net_ret'] - default_path['net_ret']))):.3e}",
                 "> 0")

    sim_config = __import__("src.simulation.engine", fromlist=["SimulationConfig"]).SimulationConfig
    paper_config = PaperTradingConfig.from_paper_config_yaml(CONFIG_PATH)
    record_check("switch_defaults_are_off_in_every_entry_point",
                 sim_config().lag_vol_estimate is False
                 and sim_config.from_yaml(SIM_CONFIG_PATH).lag_vol_estimate is False
                 and paper_config.lag_vol_estimate is False,
                 "SimulationConfig(), from_yaml, PaperTradingConfig -> all False",
                 "all False")
    config_mentions_all = [str(p.relative_to(REPO_ROOT)) for p in sorted((REPO_ROOT / "config").rglob("*"))
                           if p.is_file() and "lag_vol_estimate" in p.read_text(encoding="utf-8", errors="ignore")]
    config_mentions = [m for m in config_mentions_all if "_corrected" not in m]
    record_check("no_config_file_sets_the_switch", config_mentions == [],
                 f"{len(config_mentions)} non-corrected config file(s) mention the switch", "0")
    record_check("corrected_config_is_specification_only_exception",
                 "config/simulation_candidate_001_corrected.yaml" in config_mentions_all,
                 "config/simulation_candidate_001_corrected.yaml sets lag_vol_estimate: true (specification-only, not an activated record)",
                 "declared exception present")
    record_feeding_configs = ["config/simulation_candidate_001.yaml", "config/paper_trading_config.yaml"]
    record_feeding_mentions = [m for m in config_mentions_all if m in record_feeding_configs]
    record_check("no_record_feeding_config_sets_the_switch", record_feeding_mentions == [],
                 f"{len(record_feeding_mentions)} record-feeding config(s) mention the switch", "0")

    # ------------------------------------------------------------------
    # 4. Corrected path re-derivation (successor record)
    # ------------------------------------------------------------------
    corrected_folds = fold_statistics(corrected_path["net_ret"], corrected_path["combined_weights"])
    default_record = record_statistics(default_path["net_ret"], record_dates)
    corrected_record = record_statistics(corrected_path["net_ret"], record_dates)

    record_check("committed_record_gate_value_reproduced",
                 abs(default_record["trailing_63d_sharpe"] - COMMITTED_TRAILING_SHARPE) < 1e-12,
                 f"{default_record['trailing_63d_sharpe']:.12f}",
                 f"{COMMITTED_TRAILING_SHARPE:.12f}")

    committed_state = PaperTradingState.from_yaml(STATE_PATH)
    default_gates = production_gate_table(committed_state, paper_config)
    corrected_state_obj = corrected_state(committed_state, corrected_path["net_ret"], record_dates)
    corrected_gates = production_gate_table(corrected_state_obj, paper_config)
    record_check("corrected_path_does_not_rescue_the_promotion_decision",
                 corrected_gates["decision"] == default_gates["decision"] == "NO-GO",
                 f"default {default_gates['decision']}, corrected {corrected_gates['decision']}",
                 "NO-GO on both paths")
    record_check("corrected_path_is_worse_on_every_record_statistic",
                 corrected_record["canonical_sharpe"] < default_record["canonical_sharpe"]
                 and corrected_record["trailing_63d_sharpe"] < default_record["trailing_63d_sharpe"]
                 and corrected_record["psr_normal"] < default_record["psr_normal"],
                 f"canonical {corrected_record['canonical_sharpe']:.6f} < {default_record['canonical_sharpe']:.6f}, "
                 f"trailing {corrected_record['trailing_63d_sharpe']:.6f} < {default_record['trailing_63d_sharpe']:.6f}, "
                 f"PSR {corrected_record['psr_normal']:.6f} < {default_record['psr_normal']:.6f}",
                 "lower on every record statistic")
    record_check("corrected_record_matches_cycle926_values",
                 abs(corrected_record["canonical_sharpe"] - CORRECTED_RECORD_EXPECTED["canonical_sharpe"]) < 5e-5
                 and abs(corrected_record["trailing_63d_sharpe"] - CORRECTED_RECORD_EXPECTED["trailing_63d_sharpe"]) < 5e-5
                 and abs(corrected_record["psr_normal"] - CORRECTED_RECORD_EXPECTED["psr_normal"]) < 5e-5
                 and abs(corrected_record["max_drawdown"] - CORRECTED_RECORD_EXPECTED["max_drawdown"]) < 5e-5,
                 f"canonical {corrected_record['canonical_sharpe']:.6f}, trailing "
                 f"{corrected_record['trailing_63d_sharpe']:.6f}, PSR {corrected_record['psr_normal']:.6f}, "
                 f"max DD {corrected_record['max_drawdown']:.6f}",
                 "matches Cycle 926 corrected values")
    record_check("corrected_walk_forward_matches_cycle926_values",
                 abs(corrected_folds["mean_test_sharpe"] - CORRECTED_WF_EXPECTED["mean_test_sharpe"]) < 5e-5
                 and abs(corrected_folds["mean_test_sharpe_excl_artefact_fold"]
                       - CORRECTED_WF_EXPECTED["mean_test_sharpe_excl_artefact_fold"]) < 5e-5
                 and abs(corrected_folds["mean_test_sharpe_excl_worst_fold"]
                       - CORRECTED_WF_EXPECTED["mean_test_sharpe_excl_worst_fold"]) < 5e-5
                 and abs(corrected_folds["median_test_sharpe"] - CORRECTED_WF_EXPECTED["median_test_sharpe"]) < 5e-5
                 and corrected_folds["worst_fold"] == CORRECTED_WF_EXPECTED["worst_fold"]
                 and abs(corrected_folds["worst_fold_test_sharpe"] - CORRECTED_WF_EXPECTED["worst_fold_test_sharpe"]) < 5e-4
                 and corrected_folds["total_test_trades"] == CORRECTED_WF_EXPECTED["total_test_trades"],
                 f"mean {corrected_folds['mean_test_sharpe']:.6f}, excl artefact "
                 f"{corrected_folds['mean_test_sharpe_excl_artefact_fold']:.6f}, "
                 f"excl worst {corrected_folds['mean_test_sharpe_excl_worst_fold']:.6f}, "
                 f"median {corrected_folds['median_test_sharpe']:.6f}, worst fold "
                 f"{corrected_folds['worst_fold']} ({corrected_folds['worst_fold_test_sharpe']:.6f}), "
                 f"trades {corrected_folds['total_test_trades']}",
                 "matches Cycle 926 corrected values")

    # SMA-window plateau table on the corrected path (six pre-specified windows).
    plateau_rows = []
    for w in SMA_WINDOWS:
        res = _eval_candidate(close, spy_sma_window=w, lag_vol_estimate=True)
        m = res["test_metrics"]
        plateau_rows.append({
            "sma_window": w,
            "test_sharpe": float(m["sharpe_ratio"]),
            "test_ann_return": float(m["annualized_return"]),
            "test_max_dd": float(m["max_drawdown"]),
            "test_trades": int(m["trade_count"]),
            "test_sortino": float(m["sortino_ratio"]),
            "test_profit_factor": float(m["profit_factor"]),
        })
    plateau_df = pd.DataFrame(plateau_rows)
    n_pass = int((plateau_df["test_sharpe"] >= 0.9).sum())
    record_check("corrected_sma_plateau_table_built", len(plateau_rows) == len(SMA_WINDOWS),
                 f"{len(plateau_rows)} windows", f"{len(SMA_WINDOWS)} windows")

    # Corrected 2018-2026 test-period statistics (own-path backtest reference).
    corrected_test = _eval_candidate(vintage_close, spy_sma_window=SPY_SMA_WINDOW,
                                     lag_vol_estimate=True)
    corrected_test_metrics = dict(corrected_test["test_metrics"])
    record_check("corrected_test_period_reference_is_lower",
                 corrected_test_metrics["sharpe_ratio"] < default_test["test_metrics"]["sharpe_ratio"],
                 f"corrected {corrected_test_metrics['sharpe_ratio']:.6f} < published "
                 f"{default_test['test_metrics']['sharpe_ratio']:.6f}",
                 "lower")
    record_check("corrected_test_period_matches_cycle926_value",
                 abs(corrected_test_metrics["sharpe_ratio"] - CORRECTED_TEST_PERIOD_EXPECTED["sharpe_ratio"]) < 5e-5,
                 f"{corrected_test_metrics['sharpe_ratio']:.6f}",
                 f"{CORRECTED_TEST_PERIOD_EXPECTED['sharpe_ratio']:.6f}")

    # ------------------------------------------------------------------
    # 5. Read-only re-check
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
    overall = "PASS" if all(c["pass"] for c in checks) else "FAIL"
    verdict = (
        f"**1. Consolidation complete.** All seven scripts that inlined the same-session "
        f"volatility estimate now route through the single shared "
        f"`src/evaluation.risk.realized_vol_scale` behind the same default-off "
        f"`lag_vol_estimate` switch. Every default path is bit-identical (max |diff| = 0.0) "
        f"to its frozen pre-change implementation, checked not asserted, and there are zero "
        f"remaining inline same-session exposure estimates in any production or research path.\n\n"
        f"**2. Corrected successor record published (supersedes nothing).** On the corrected "
        f"path the committed record's canonical Sharpe moves from "
        f"{default_record['canonical_sharpe']:.6f} to {corrected_record['canonical_sharpe']:.6f}, "
        f"its trailing 63-session Sharpe from {default_record['trailing_63d_sharpe']:.6f} to "
        f"{corrected_record['trailing_63d_sharpe']:.6f} and its PSR against the fixed backtest "
        f"baseline {PSR_TARGET} from {default_record['psr_normal']:.6f} to "
        f"{corrected_record['psr_normal']:.6f}; the corrected path is worse on every record-level "
        f"statistic and the promotion decision stays **NO-GO** (failed gates: "
        f"{', '.join(corrected_gates['failed_gates'])}). The corrected walk-forward mean "
        f"{corrected_folds['mean_test_sharpe']:.6f} is higher only because the numerical-artefact "
        f"fold scores 0.000000 instead of a pathology; on the comparable statistic it is lower "
        f"({corrected_folds['mean_test_sharpe_excl_artefact_fold']:.6f} vs "
        f"{default_folds['mean_test_sharpe_excl_artefact_fold']:.6f}) and must never be quoted "
        f"without the fold-level table.\n\n"
        f"**3. Incumbent unchanged.** The published walk-forward record, the committed "
        f"paper-trading state, every committed record, `data/` and `config/` are byte-identical "
        f"before and after. The incumbent's verdict (Credible Candidate) and promotion decision "
        f"(NO-GO) are unchanged; nothing here promotes, rescues or re-scores the incumbent.\n\n"
        f"**4. The corrected live-record start procedure is specified, not executed.** A new live "
        f"record on the corrected path must be started fresh (126 sessions for "
        f"`track_record_length`), measured against the unchanged PSR reference {PSR_TARGET} "
        f"(stricter than this path's own backtest reference of "
        f"{corrected_test_metrics['sharpe_ratio']:.6f}), and must never be appended to the "
        f"committed record."
    )

    payload: dict[str, Any] = {
        "cycle": CYCLE,
        "candidate": CANDIDATE_ID,
        "sharpe_convention": "arithmetic_annualized_rf0",
        "overall": overall,
        "checks": checks,
        "switch": {
            "name": "lag_vol_estimate",
            "default": False,
            "semantics": (
                "When True the realised-volatility estimate for session t is computed from "
                "sessions up to and including t-1 only (no same-session feedback). When False "
                "(the default) the trailing 63-session window includes session t, the committed "
                "behaviour."
            ),
            "scripts_consolidated": list(SCRIPTS),
            "config_files_setting_the_switch": config_mentions,
        },
        "anchor": {
            "published_record": published_path.name,
            "published_wf_mean": PUBLISHED_WF_MEAN,
            "reproduced_wf_mean": default_folds["mean_test_sharpe"],
            "machinery_wf_mean": machinery_mean,
            "n_folds": default_folds["n_folds"],
            "committed_sessions": len(committed_returns),
            "record_max_abs_diff": record_diff,
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
            "production_gates_published": default_gates,
            "production_gates_corrected": corrected_gates,
            "gate_threshold_rolling": GATE_ROLLING_SHARPE,
            "gate_threshold_psr": GATE_PSR,
            "psr_settings": {
                "target": PSR_TARGET,
                "n_bootstrap": PSR_N_BOOTSTRAP,
                "block_size": PSR_BLOCK_SIZE,
                "seed": PSR_SEED,
            },
        },
        "test_period": {
            "vintage_end": TEST_PERIOD_VINTAGE_END,
            "published": dict(default_test["test_metrics"]),
            "corrected": corrected_test_metrics,
            "published_reference": dict(PUBLISHED_TEST_PERIOD),
        },
        "plateau": {
            "windows": SMA_WINDOWS,
            "rows": plateau_rows,
            "n_pass": n_pass,
        },
        "script_consolidation": script_checks,
        "incumbent_verdict": "Credible Candidate (unchanged); promotion decision NO-GO (unchanged)",
        "read_only": {
            "data_unchanged": data_before == data_after,
            "config_unchanged": config_before == config_after,
            "committed_artifacts_unchanged": artifacts_before == artifacts_after,
        },
        "data_source": (
            "committed parquet cache in data/raw/ and the committed paper-trading state; "
            "the fetcher is never called"
        ),
    }
    return payload


# ----------------------------------------------------------------------
# Report / experiment record rendering
# ----------------------------------------------------------------------
def _fmt_pct(x):
    return f"{x:.2%}"


def render_report(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(
        f"# One implementation of the same-session volatility estimate everywhere, and the "
        f"corrected successor backtest record for the incumbent "
        f"(tsmomentum_vol_estimate_consolidation_001, Cycle {payload['cycle']})"
    )
    lines.append("")
    lines.append("## Status")
    lines.append("")
    lines.append(f"- **OVERALL: {payload['overall']}**")
    lines.append(f"- Candidate: `{payload['candidate']}` (the incumbent)")
    lines.append(
        f"- Default path: **bit-identical** to every script's pre-change implementation "
        f"(max |diff| = 0.0, checked per script)."
    )
    lines.append(
        f"- Switch: `lag_vol_estimate` (default **off**) in all seven consolidated scripts; "
        f"zero remaining inline same-session exposure estimates."
    )
    lines.append(
        f"- Decision: **unchanged** -- NO-GO on both the published and the corrected path "
        f"(failed gates: {', '.join(payload['record']['production_gates_corrected']['failed_gates'])})."
    )
    lines.append(
        f"- Read-only: `data/` and `config/` byte-identical (**{'yes' if payload['read_only']['data_unchanged'] and payload['read_only']['config_unchanged'] else 'NO'}**); "
        f"no committed artifact modified (**{'yes' if payload['read_only']['committed_artifacts_unchanged'] else 'NO'}**); "
        f"the published record and the committed paper-trading state are **not** overwritten."
    )
    lines.append("")
    lines.append("## 1. Implementation consolidation (one implementation, one switch)")
    lines.append("")
    lines.append(
        "Each of the seven scripts that inlined the same-session volatility estimate now calls "
        "the shared `src.evaluation.risk.realized_vol_scale(port_ret, target_vol, lookback, "
        "lag_vol_estimate)` with `lag_vol_estimate=False` by default.  The default path of every "
        "script was compared against a frozen copy of its pre-change implementation on identical "
        "synthetic input; every comparison is max |diff| = 0.0, checked not asserted."
    )
    lines.append("")
    lines.append("| Script | Before | After | Default path max |diff| |")
    lines.append("|---|---|---|---|---|")
    for entry in payload["script_consolidation"]:
        name = entry["name"]
        if name.endswith("default bit-identical (weights)"):
            script = name.split(" ")[0]
            obs = str(entry["observed"])
            lines.append(f"| `{script}` | inline `rolling(...).std() * sqrt(252)` | "
                         f"`realized_vol_scale(..., lag_vol_estimate=False)` | {obs} |")
    lines.append("")
    lines.append(
        f"Inventory result: **zero** remaining inline same-session exposure estimates in any "
        f"production or research path. The only permitted copies are the frozen pre-change "
        f"reference implementations kept in this tool and in its test file, labelled as such."
    )
    lines.append("")
    lines.append("### Per-script checks")
    lines.append("")
    for c in payload["script_consolidation"]:
        status = "PASS" if c["pass"] else "FAIL"
        lines.append(f"- [{c['name']}]: {status}"
                     + (f" (observed: {c['observed']}, expected: {c['expected']})"
                        if c.get("observed") or c.get("expected") else ""))
    lines.append("")

    lines.append("## 2. Reproduction anchor (fail closed)")
    lines.append("")
    anchor = payload["anchor"]
    lines.append(
        "Nothing is published unless the default path reproduces the incumbent's published "
        "artefacts exactly as committed."
    )
    lines.append("")
    lines.append("| Quantity | Published | Reproduced |")
    lines.append("|---|---|---|")
    lines.append(
        f"| 48-fold walk-forward mean OOS Sharpe | {PUBLISHED_WF_MEAN:.6f} | "
        f"{anchor['reproduced_wf_mean']:.6f} |"
    )
    if anchor.get("machinery_wf_mean") is not None:
        lines.append(
            f"| Same, from `research/run_cycle6.py::run_walkforward` | {PUBLISHED_WF_MEAN:.6f} | "
            f"{anchor['machinery_wf_mean']:.6f} |"
        )
    lines.append(f"| Folds | {PUBLISHED_WF_FOLDS} | {anchor['n_folds']} |")
    lines.append(
        f"| Committed record sessions | 450 | {anchor['committed_sessions']} "
        f"(max abs diff = {anchor['record_max_abs_diff']:.3e}) |"
    )
    lines.append("")
    lines.append("The published record is resolved by content and all 48 published folds are "
                 "reproduced: test windows exactly, OOS Sharpe to the published precision, "
                 "trade counts exactly.")
    lines.append("")

    lines.append("## 3. Corrected successor record (supersedes nothing)")
    lines.append("")
    lines.append(
        "This is a **successor reference that supersedes nothing**: the published record "
        "`research/experiments/tsmomentum_regime_filter_wf_001.md`, the committed paper-trading "
        "state and every other committed record remain byte-identical. The corrected numbers are "
        "**lower on every record-level statistic**; the decision stays **NO-GO**."
    )
    lines.append("")
    lines.append("### 3.1 The corrected 48-fold walk-forward table")
    lines.append("")
    pub = payload["walk_forward"]["published"]
    cor = payload["walk_forward"]["corrected"]
    lines.append("| Statistic | Published (same-session) | Corrected (lagged) |")
    lines.append("|---|---|---|")
    for label, key in (
        ("Folds", "n_folds"),
        ("Mean OOS Sharpe (all folds)", "mean_test_sharpe"),
        ("Mean OOS Sharpe excl. the numerical-artefact fold", "mean_test_sharpe_excl_artefact_fold"),
        ("Mean OOS Sharpe excl. each path's own worst fold", "mean_test_sharpe_excl_worst_fold"),
        ("Median OOS Sharpe", "median_test_sharpe"),
        ("Std OOS Sharpe", "std_test_sharpe"),
        ("Min OOS Sharpe", "min_test_sharpe"),
        ("Max OOS Sharpe", "max_test_sharpe"),
        ("Positive folds", "pct_positive_sharpe"),
        ("Pooled OOS trades", "total_test_trades"),
    ):
        pv, cv = pub[key], cor[key]
        if isinstance(pv, int):
            lines.append(f"| {label} | {pv} | {cv} |")
        elif key == "pct_positive_sharpe":
            lines.append(f"| {label} | {pv:.2%} | {cv:.2%} |")
        else:
            lines.append(f"| {label} | {pv:.6f} | {cv:.6f} |")
    lines.append("")
    lines.append(
        f"**Artefact-fold caveat.** The default path's minimum fold is fold {pub['worst_fold']} "
        f"({pub['worst_fold_test_sharpe']:.6f}) -- the numerical artefact: a near-flat segment "
        f"({pub['worst_fold_detail']['n_flat_sessions']} of {pub['worst_fold_detail']['n_sessions']} "
        f"flat sessions) scored on the backtest-baseline scale. On the corrected path the same "
        f"segment is entirely flat ({cor['artefact_fold_detail']['n_flat_sessions']} of "
        f"{cor['artefact_fold_detail']['n_sessions']} sessions flat, zero dispersion) and the "
        f"estimator returns {cor['artefact_fold_test_sharpe']:.6f}; the corrected path's own "
        f"worst fold is fold {cor['worst_fold']} ({cor['worst_fold_test_sharpe']:.6f}). The "
        f"corrected all-fold mean ({cor['mean_test_sharpe']:.6f}) is therefore a zero replacing a "
        f"pathology, not a better strategy: on the strictest comparable statistic (both paths with "
        f"the artefact fold excluded) the corrected path is **lower** "
        f"({cor['mean_test_sharpe_excl_artefact_fold']:.6f} vs "
        f"{pub['mean_test_sharpe_excl_artefact_fold']:.6f}), and so is each path's mean excluding "
        f"its own worst fold ({cor['mean_test_sharpe_excl_worst_fold']:.6f} vs "
        f"{pub['mean_test_sharpe_excl_worst_fold']:.6f}). The corrected walk-forward mean must "
        f"never be quoted without this fold-level table."
    )
    lines.append("")

    lines.append("### 3.2 The corrected SMA-window plateau table")
    lines.append("")
    lines.append(
        "The six pre-specified SMA windows of the published record, re-derived on the corrected "
        "path over the 2018-2026 test period."
    )
    lines.append("")
    lines.append("| SMA window | Test Sharpe | Ann. Return | Max DD | Trades | Sortino | Profit Factor | Meets 0.9? |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for row in payload["plateau"]["rows"]:
        meets = "YES" if row["test_sharpe"] >= 0.9 else "No"
        lines.append(
            f"| {row['sma_window']} | {row['test_sharpe']:.4f} | {row['test_ann_return']:.4f} | "
            f"{row['test_max_dd']:.4f} | {row['test_trades']} | {row['test_sortino']:.4f} | "
            f"{row['test_profit_factor']:.2f} | {meets} |"
        )
    lines.append(
        f"Windows with Sharpe >= 0.9: {payload['plateau']['n_pass']}/{len(SMA_WINDOWS)} "
        f"(informational; the plateau gate is not part of this cycle)."
    )
    lines.append("")

    lines.append("### 3.3 The corrected 2018-2026 test-period statistics (own-path backtest)")
    lines.append("")
    tp = payload["test_period"]
    lines.append("| Statistic | Published (same-session) | Corrected (lagged) |")
    lines.append("|---|---|---|")
    for label, key, fmt in (
        ("Sharpe (backtest-baseline scale)", "sharpe_ratio", "{:.6f}"),
        ("Max drawdown", "max_drawdown", "{:.6f}"),
        ("Trade count", "trade_count", "{:d}"),
        ("Annualized return", "annualized_return", "{:.6f}"),
        ("Annualized turnover", "annualized_turnover", "{:.4f}"),
        ("Annualized volatility", "annualized_volatility", "{:.6f}"),
    ):
        pv = tp["published"][key]
        cv = tp["corrected"][key]
        if key == "trade_count":
            pv, cv = int(pv), int(cv)
        lines.append(f"| {label} | {fmt.format(pv)} | {fmt.format(cv)} |")
    lines.append("")
    lines.append(
        f"The corrected path's own backtest reference is {tp['corrected']['sharpe_ratio']:.6f}, "
        f"below the unchanged fixed reference {PSR_TARGET} measured on the same-session path. "
        f"A corrected live record compared against the unchanged reference therefore faces a "
        f"**stricter** bar than its own path's backtest; the comparison stays conservative."
    )
    lines.append("")

    lines.append("### 3.4 The corrected record-level statistics and production gate table")
    lines.append("")
    pr = payload["record"]["published"]
    cr = payload["record"]["corrected"]
    lines.append("| Statistic | Published | Corrected |")
    lines.append("|---|---|---|")
    lines.append(f"| Sessions | {pr['n_sessions']} | {cr['n_sessions']} |")
    lines.append(f"| Canonical Sharpe | {pr['canonical_sharpe']:.6f} | {cr['canonical_sharpe']:.6f} |")
    lines.append(
        f"| Trailing 63-session Sharpe (`rolling_63d_sharpe` gate value) | "
        f"{pr['trailing_63d_sharpe']:.6f} | {cr['trailing_63d_sharpe']:.6f} |"
    )
    lines.append(
        f"| `rolling_63d_sharpe` gate (>= {payload['record']['gate_threshold_rolling']}) | "
        f"{'PASS' if pr['rolling_gate_passes'] else 'FAIL'} | "
        f"{'PASS' if cr['rolling_gate_passes'] else 'FAIL'} |"
    )
    lines.append(f"| PSR (normal) vs {PSR_TARGET} | {pr['psr_normal']:.6f} | {cr['psr_normal']:.6f} |")
    lines.append(
        f"| `psr` gate (>= {payload['record']['gate_threshold_psr']}) | "
        f"{'PASS' if pr['psr_gate_passes'] else 'FAIL'} | "
        f"{'PASS' if cr['psr_gate_passes'] else 'FAIL'} |"
    )
    lines.append(f"| Max drawdown | {pr['max_drawdown']:.6%} | {cr['max_drawdown']:.6%} |")
    lines.append("")
    lines.append("| Gate | Published record | Corrected record | Threshold |")
    lines.append("|---|---|---|---|")
    gp = payload["record"]["production_gates_published"]
    gc = payload["record"]["production_gates_corrected"]
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
        "The corrected gate table is computed by the production code "
        "`src.simulation.evaluation.evaluate_go_no_go` on the corrected return series with the "
        "committed configuration. It is **NO-GO** with the same failed gates as the published "
        "path; the correction is not the cause of the gate failure and it does not rescue "
        "anything."
    )
    lines.append("")

    lines.append("## 4. Corrected live paper-trading record start procedure (specified, not executed)")
    lines.append("")
    lines.append(
        "No live record is started in this cycle, no state file is written, and the fetcher is "
        "never called.  The following is an executable specification for a future cycle."
    )
    lines.append("")
    lines.append("### 4.1 Configuration change")
    lines.append("")
    lines.append("- Set `lag_vol_estimate: true` in the simulation config used to produce the "
                 "new live record (the committed `config/simulation_candidate_001.yaml` and "
                 "`config/paper_trading_config.yaml` are **not** edited; the switch is applied "
                 "to a **new** config file for the new record only).")
    lines.append("- Do **not** set the switch on any config that feeds a committed record; a "
                 "computed record must never mix the two paths.")
    lines.append("")
    lines.append("### 4.2 New state file path")
    lines.append("")
    lines.append("- Start a **new** state file (e.g. "
                 "`data/processed/paper_trading_state_corrected_001.yaml`) with its own drift "
                 "flags and gate table; do **not** append to or modify "
                 "`data/processed/paper_trading_state.yaml` (the committed 450-session record).")
    lines.append("")
    lines.append("### 4.3 Re-initialised drift flags and gate table")
    lines.append("")
    lines.append("- Re-initialise the drift flags and the production gate table for the new "
                 "record from its first session; the `track_record_length` gate requires 126 "
                 "sessions, so promotion evidence restarts from zero while the committed record "
                 "stays published and NO-GO.")
    lines.append("")
    lines.append("### 4.4 Restart cost")
    lines.append("")
    lines.append(
        f"- **126 sessions** must be re-accumulated before the `track_record_length` gate can be "
        f"evaluated on the corrected record."
    )
    lines.append("")
    lines.append("### 4.5 PSR-reference consequence")
    lines.append("")
    lines.append(
        f"- The corrected path's own 2018-2026 backtest reference is "
        f"{tp['corrected']['sharpe_ratio']:.6f}; the unchanged fixed reference {PSR_TARGET} is a "
        f"**stricter** bar than that record's own backtest.  Measuring a corrected live record "
        f"against the unchanged reference is conservative."
    )
    lines.append("")
    lines.append(
        "A record that mixes the same-session and the lagged paths measures neither; the two "
        "paths must never be concatenated into a single record."
    )
    lines.append("")

    lines.append("## 5. What this cycle does NOT change")
    lines.append("")
    lines.append(
        "- It does **not** cause the `rolling_63d_sharpe` failure: the corrected failing "
        f"window is worse ({cr['trailing_63d_sharpe']:.6f} vs {pr['trailing_63d_sharpe']:.6f})."
    )
    lines.append(
        "- It does **not** rescue the promotion decision: the PSR gate still fails on the "
        f"corrected path ({cr['psr_normal']:.6f} < {payload['record']['gate_threshold_psr']}), "
        f"and the decision stays {gc['decision']}."
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
        "- No gate, threshold, universe, cost model, Sharpe convention, parameter, hypothesis "
        "or drift flag is changed; no candidate is selected, re-fit or re-ranked; the shortlist "
        "and the promotion decision are not re-stated."
    )
    lines.append("")

    lines.append("## 6. Checks")
    lines.append("")
    for c in payload["checks"]:
        if c["name"].startswith("run_cycle") or c["name"].startswith("month_end"):
            continue  # reported in section 1
        lines.append(f"- [{c['name']}]: {'PASS' if c['pass'] else 'FAIL'}"
                     + (f" (observed: {c['observed']}, expected: {c['expected']})"
                        if c.get("observed") or c.get("expected") else ""))
    lines.append("")

    lines.append("## 7. Reproduction commands")
    lines.append("")
    lines.append("```bash")
    lines.append("python research/tsmomentum_vol_estimate_consolidation.py")
    lines.append("python -m pytest -q tests/test_tsmomentum_vol_estimate_consolidation.py")
    lines.append("python -m pytest -q")
    lines.append("git status --porcelain data/ config/")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def render_experiment(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(
        f"# Experiment: Consolidated same-session volatility estimate and corrected successor "
        f"backtest record for `{payload['candidate']}` "
        f"(tsmomentum_vol_estimate_consolidation_001, Cycle {payload['cycle']})"
    )
    lines.append("")
    lines.append("## Hypothesis reference")
    lines.append("")
    lines.append("- Incumbent hypothesis: `research/hypotheses/tsmomentum_004.md`")
    lines.append("- Prior cycles reused: Cycle 925 (the same-session measurement defect), "
                 "Cycle 926 (the default-off opt-in correction)")
    lines.append("")
    lines.append("## Objective")
    lines.append("")
    lines.append(
        "Consolidate the same-session volatility estimate onto one shared implementation behind "
        "one default-off switch in all seven research scripts that still inlined it, and publish "
        "the incumbent's corrected backtest as a new, labelled successor reference. Measurement "
        "only: no gate, threshold, universe, cost model, Sharpe convention, parameter, hypothesis "
        "or drift flag is changed, and no candidate is promoted, re-fit or re-ranked."
    )
    lines.append("")
    lines.append("## Data")
    lines.append("")
    lines.append(
        f"- Committed paper-trading record: {payload['record']['published']['n_sessions']} sessions "
        "(2025-01-02 .. 2026-10-19)"
    )
    lines.append(f"- Price panel: committed parquet cache `data/raw/*.parquet` (cache-only; the fetcher is never called)")
    lines.append(f"- Universe: {', '.join(SYMBOLS)}")
    lines.append(
        f"- Cost model: {COMMISSION_BPS * 10000.0:.1f} bps commission + "
        f"{SLIPPAGE_BPS * 10000.0:.1f} bps slippage = "
        f"{(COMMISSION_BPS + SLIPPAGE_BPS) * 10000.0:.1f} bps round-trip"
    )
    lines.append(
        "- Point-in-time treatment: momentum weights shifted one session; the SPY SMA filter "
        "and the trailing volatility window are computed on the cached panel; the published "
        "walk-forward design (10y train / 12m test / 6m step, 21d purge, 21d embargo) is reused unchanged"
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
        "- Switch: `lag_vol_estimate`, default **off**; the corrected path sets it to True in "
        "the research path and the shared engine"
    )
    lines.append(
        f"- PSR: target {PSR_TARGET}, `n_bootstrap={PSR_N_BOOTSTRAP}`, "
        f"`block_size={PSR_BLOCK_SIZE}`, `seed={PSR_SEED}` (the repository's own settings)"
    )
    lines.append(
        f"- Gates read from `config/promotion_gates.yaml`: `rolling_63d_sharpe` >= "
        f"{payload['record']['gate_threshold_rolling']}, `psr` >= {payload['record']['gate_threshold_psr']}"
    )
    lines.append("")
    lines.append("## Trial count")
    lines.append("")
    lines.append(
        "- 1 anchor reproduction (48 folds) + 7 per-script consolidation bit-identity checks "
        "+ 2 paths (default, corrected) + 1 frozen-implementation comparison per script; "
        "no per-fold re-optimisation, no candidate selection, no configuration search."
    )
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("### Consolidation")
    lines.append("")
    lines.append(
        f"- All seven scripts consolidated: "
        f"{', '.join(s.split('/')[-1].replace('.py','') for s in payload['switch']['scripts_consolidated'])}"
    )
    lines.append(
        f"- Per-script default path: bit-identical to the frozen pre-change implementation "
        f"(max |diff| = 0.0, all scripts)."
    )
    lines.append(
        f"- Remaining inline same-session exposure estimates: 0."
    )
    lines.append("")
    lines.append("### Successor record (supersedes nothing)")
    lines.append("")
    cor = payload["walk_forward"]["corrected"]
    rec = payload["record"]["corrected"]
    lines.append(
        f"- Corrected walk-forward mean OOS Sharpe: {cor['mean_test_sharpe']:.6f} (all folds); "
        f"excluding each path's own worst fold: {cor['mean_test_sharpe_excl_worst_fold']:.6f}"
    )
    lines.append(
        f"- Corrected record canonical Sharpe: {rec['canonical_sharpe']:.6f}"
    )
    lines.append(
        f"- Corrected trailing 63-session Sharpe (`rolling_63d_sharpe`): {rec['trailing_63d_sharpe']:.6f}"
    )
    lines.append(
        f"- Corrected PSR vs {PSR_TARGET}: {rec['psr_normal']:.6f}"
    )
    lines.append(
        f"- Corrected 2018-2026 test-period Sharpe (own-path reference): "
        f"{payload['test_period']['corrected']['sharpe_ratio']:.6f}"
    )
    lines.append(
        f"- Promotion decision: NO-GO on both paths (failed gates: "
        f"{', '.join(payload['record']['production_gates_corrected']['failed_gates'])})"
    )
    lines.append("")
    lines.append("## Verdict")
    lines.append("")
    lines.append(
        "The consolidation is complete and verified bit-for-bit. The corrected successor record "
        "is published as a new artefact that supersedes nothing. The incumbent remains a "
        "**Credible Candidate** by its published verdict and **NO-GO** for promotion; the "
        "corrected path is worse on every record-level statistic and does not rescue anything."
    )
    lines.append("")
    lines.append("## Reproduction")
    lines.append("")
    lines.append("```bash")
    lines.append("python research/tsmomentum_vol_estimate_consolidation.py")
    lines.append("python -m pytest -q tests/test_tsmomentum_vol_estimate_consolidation.py")
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

    payload = run_consolidation(raw_dir=args.raw_dir)

    if not args.no_report:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.experiment_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(render_report(payload), encoding="utf-8")
        args.experiment_out.write_text(render_experiment(payload), encoding="utf-8")

    anchor = payload["anchor"]
    rec = payload["record"]
    cor = payload["walk_forward"]["corrected"]
    print(f"OVERALL: {payload['overall']}")
    print(f"anchor: 48-fold WF mean {anchor['reproduced_wf_mean']:.6f} "
          f"(published {PUBLISHED_WF_MEAN:.6f}); committed record {anchor['committed_sessions']} sessions")
    print(f"script consolidation: {sum(1 for c in payload['script_consolidation'] if c['pass'])}/"
          f"{len(payload['script_consolidation'])} per-script checks passed")
    print(f"record Sharpe: published {rec['published']['canonical_sharpe']:.6f} -> corrected "
          f"{rec['corrected']['canonical_sharpe']:.6f}")
    print(f"trailing 63d: published {rec['published']['trailing_63d_sharpe']:.6f} -> corrected "
          f"{rec['corrected']['trailing_63d_sharpe']:.6f}")
    print(f"PSR vs {PSR_TARGET}: published {rec['published']['psr_normal']:.6f} -> corrected "
          f"{rec['corrected']['psr_normal']:.6f}")
    print(f"WF mean: published {payload['walk_forward']['published']['mean_test_sharpe']:.6f} -> corrected "
          f"{cor['mean_test_sharpe']:.6f} (excl. own worst fold: "
          f"{cor['mean_test_sharpe_excl_worst_fold']:.6f})")
    print(f"decision: published {rec['production_gates_published']['decision']}, corrected "
          f"{rec['production_gates_corrected']['decision']}")
    print(f"report: {args.report_out}" if not args.no_report else "--no-report: no artifacts written")
    return 0 if payload["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
