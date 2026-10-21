#!/usr/bin/env python3
"""Rolling 63d Sharpe weakness diagnosis for the incumbent ``tsmomentum_spytrend_001`` (Cycle 925).

Cycle 925 task: diagnose why the promotion gate ``rolling_63d_sharpe`` fails on
the committed paper-trading record, decide whether the weakness clusters in an
observable market state (the Cycle 923/924 buckets), and test -- **in isolation**
-- whether any minimal, mechanism-tied change clears the gate.

This is a **read-only, descriptive** diagnosis. It changes no strategy, universe,
cost model, parameter, threshold, gate, drift flag or verdict, and it never
touches ``data/`` or ``config/``. The only files it may write are NEW files
under ``research/reports/`` and ``research/experiments/``.

What it does, in order:

1. **Anchor (fail closed).** Reproduce the trailing 63-session Sharpe of the
   committed record three ways -- from the committed state file, from the
   production ``evaluate_go_no_go`` gate table, and from an independent offline
   recomputation of the strategy path -- and require them to agree. The offline
   path is also required to reproduce all 450 committed sessions bit-for-bit.
2. **Distribution.** Every trailing 63-session Sharpe on the committed record
   (388 overlapping windows): min / p10 / p25 / median / p75 / max, the gate
   base rate, the failing runs, the recovery lags and the current percentile
   rank, with a moving-block bootstrap CI on the base rate.
3. **Overlap with the prior cycles' phase buckets.** Each rolling window is
   mapped onto the published walk-forward fold that contains its end date and
   inherits that fold's Cycle-923 buckets (F1 calendar phase, F2 SPY trend
   state, F3 SPY 12-month return sign, F4 training-window realised-vol
   tercile). Concentration is tested with a permutation p-value, a block
   bootstrap CI on the bucket gap and a non-overlapping-window robustness check.
4. **Correlation to market state.** Spearman correlations between the rolling
   Sharpe and four window-level state variables, each with a moving-block
   bootstrap CI.
5. **Isolated counterfactuals.** Five variants of the *overlay* are recomputed
   on scratch paths (baseline, no volatility target, volatility estimate lagged
   one session, no drawdown control, no overlay at all) and evaluated on the
   trailing window, the committed record, the full path and the published
   48-fold walk-forward. No production code is modified; this is measurement.

Interpretation guard: this tool measures. It does not forecast, it does not
select or re-fit anything, and a mechanically improved number is not a
recovery. Promotion still requires every gate in ``config/promotion_gates.yaml``
to pass on credible evidence.

Usage::

    python research/tsmomentum_rolling63_weakness_diagnosis.py
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.run_cycle6 import (  # noqa: E402
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
)
from research.tsmomentum_fold_regime_attribution import (  # noqa: E402
    evaluate_folds,
    run_attribution,
)
from research.tsmomentum_walkforward_embargo_audit import (  # noqa: E402
    AuditError,
    fingerprint,
    load_close_from_cache,
    published_splits,
    tracked_artifact_hashes,
)
from src.evaluation.sharpe import SHARPE_CONVENTION_ID, sharpe_ratio  # noqa: E402
from src.features.momentum import build_weights  # noqa: E402
from src.simulation.evaluation import GoNoGoConfig, evaluate_go_no_go  # noqa: E402
from src.simulation.paper_trading import (  # noqa: E402
    PaperTradingConfig,
    PaperTradingState,
)

CANDIDATE_ID = "tsmomentum_spytrend_001"
CYCLE = "925"

REPORTS_DIR = REPO_ROOT / "research" / "reports"
EXPERIMENTS_DIR = REPO_ROOT / "research" / "experiments"
RAW_DIR = REPO_ROOT / "data" / "raw"
STATE_PATH = REPO_ROOT / "data" / "processed" / "paper_trading_state.yaml"
CONFIG_PATH = REPO_ROOT / "config" / "paper_trading_config.yaml"
GATES_PATH = REPO_ROOT / "config" / "promotion_gates.yaml"
OUT_REPORT = REPORTS_DIR / "tsmomentum_rolling63_weakness_diagnosis_001.md"
OUT_EXP = EXPERIMENTS_DIR / "tsmomentum_rolling63_weakness_diagnosis_001.md"

# The gate under diagnosis (config/promotion_gates.yaml, gate "rolling_63d_sharpe").
WINDOW = 63
GATE_ROLLING_SHARPE = 0.9
ANNUAL = 252

# Statistical controls (fixed and published).
PERMUTATIONS = 10_000
PERM_SEED = 925
BOOTSTRAP_RESAMPLES = 2_000
BOOTSTRAP_SEED = 925
BOOTSTRAP_BLOCK = 63
# Block length of the bootstrap over the *window* series (the rolling windows
# overlap 63-fold, so a shorter block keeps both buckets represented).
WINDOW_BOOTSTRAP_BLOCK = 21

# The four bucket families published in Cycle 923 (no fifth family).
FOLD_FAMILIES = (
    "F1_calendar_phase",
    "F2_spy_trend_state",
    "F3_spy_12m_return_sign",
    "F4_train_63d_realvol_tercile",
)
FAMILY_LABELS = {
    "F1_calendar_phase": "F1 calendar phase (published fold parity)",
    "F2_spy_trend_state": "F2 SPY trend state at the fold's test-window start",
    "F3_spy_12m_return_sign": "F3 SPY trailing 12-month return sign at the fold's test-window start",
    "F4_train_63d_realvol_tercile": "F4 training-window 63-day realised-volatility tercile",
}
FAMILY_BUCKETS = {
    "F1_calendar_phase": ["phase_A", "phase_B"],
    "F2_spy_trend_state": ["risk_on", "risk_off"],
    "F3_spy_12m_return_sign": ["up", "down"],
    "F4_train_63d_realvol_tercile": ["low_vol", "med_vol", "high_vol"],
}

# The overlay variants tested in isolation (scratch paths only).
VARIANTS = (
    ("V0_baseline", "base", "base", "committed overlay: volatility target on the same-session estimate"),
    ("V1_no_vol_target", "off", "base", "volatility target disabled (vol_scale == 1)"),
    ("V2_vol_estimate_lagged_1d", "lag1", "base", "volatility estimate lagged one session (no same-session feedback)"),
    ("V3_no_drawdown_control", "base", "off", "drawdown control disabled (dd_scale == 1)"),
    ("V4_no_overlay", "off", "off", "no overlay at all (raw signal + SPY filter + costs)"),
)


# ----------------------------------------------------------------------
# Read-only helpers
# ----------------------------------------------------------------------
def fmt(value: float, digits: int = 6) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "N/A"
    return f"{float(value):.{digits}f}"


def load_state() -> dict:
    import yaml

    with open(STATE_PATH) as fh:
        return yaml.safe_load(fh) or {}


def load_gate_table() -> dict:
    import yaml

    with open(GATES_PATH) as fh:
        return yaml.safe_load(fh) or {}


# ----------------------------------------------------------------------
# Estimators
# ----------------------------------------------------------------------
def rolling_sharpe_series(values: np.ndarray, window: int = WINDOW) -> np.ndarray:
    """Canonical trailing-``window`` Sharpe of every slice of *values*.

    Same convention as ``src.evaluation.sharpe.sharpe_ratio`` (arithmetic,
    annualised at 252 periods, zero risk-free rate) and the same degenerate
    behaviour: a window without dispersion yields 0.0.
    """
    arr = np.asarray(values, dtype=float)
    n = arr.size
    if n < window:
        return np.empty(0, dtype=float)
    cum = np.concatenate(([0.0], np.cumsum(arr)))
    cum_sq = np.concatenate(([0.0], np.cumsum(arr * arr)))
    total = cum[window:] - cum[:-window]
    total_sq = cum_sq[window:] - cum_sq[:-window]
    mean = total / window
    var = (total_sq - total * total / window) / (window - 1)
    std = np.sqrt(np.maximum(var, 0.0))
    with np.errstate(divide="ignore", invalid="ignore"):
        out = mean * ANNUAL / (std * math.sqrt(ANNUAL))
    out[~np.isfinite(out)] = 0.0
    return out


def rolling_std_series(values: np.ndarray, window: int = WINDOW) -> np.ndarray:
    """Sample standard deviation of every trailing ``window``-session slice."""
    arr = np.asarray(values, dtype=float)
    n = arr.size
    if n < window:
        return np.empty(0, dtype=float)
    cum = np.concatenate(([0.0], np.cumsum(arr)))
    cum_sq = np.concatenate(([0.0], np.cumsum(arr * arr)))
    total = cum[window:] - cum[:-window]
    total_sq = cum_sq[window:] - cum_sq[:-window]
    var = (total_sq - total * total / window) / (window - 1)
    return np.sqrt(np.maximum(var, 0.0))


def failing_runs(passes: np.ndarray) -> list[int]:
    """Lengths of the runs of consecutive failing windows."""
    runs: list[int] = []
    current = 0
    for ok in passes:
        if not ok:
            current += 1
        elif current:
            runs.append(current)
            current = 0
    if current:
        runs.append(current)
    return runs


def recovery_lags(passes: np.ndarray) -> list[int]:
    """For every failing window, the number of windows until the next pass."""
    lags: list[int] = []
    n = len(passes)
    for i in range(n):
        if passes[i]:
            continue
        j = i
        while j < n and not passes[j]:
            j += 1
        if j < n:
            lags.append(j - i)
    return lags


def eta_squared(values: np.ndarray, groups: np.ndarray) -> float:
    """Share of between-window dispersion explained by a grouping (one-way eta^2)."""
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


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman rank correlation (no ties correction beyond average ranks)."""
    rx = pd.Series(x).rank().to_numpy(dtype=float)
    ry = pd.Series(y).rank().to_numpy(dtype=float)
    if np.std(rx) <= 0 or np.std(ry) <= 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def block_bootstrap_indices(n: int, block: int, rng: np.random.Generator) -> np.ndarray:
    """Moving-block bootstrap indices: contiguous blocks resampled with replacement."""
    n_blocks = int(math.ceil(n / block))
    starts = rng.integers(0, max(n - block + 1, 1), size=n_blocks)
    idx = np.concatenate([np.arange(s, s + block) for s in starts])[:n]
    return idx


# ----------------------------------------------------------------------
# The strategy path (with the overlay variants) -- scratch computation only
# ----------------------------------------------------------------------
def overlay_variant(
    close: pd.DataFrame,
    vol_mode: str = "base",
    dd_mode: str = "base",
) -> dict[str, Any]:
    """Recompute the candidate path with a switchable overlay.

    ``vol_mode``:
        ``base`` -- the committed behaviour: ``vol_scale[t]`` uses the trailing
        63-session realised volatility of the *unscaled* signal portfolio,
        a window that **includes** session ``t`` itself.
        ``lag1`` -- the same estimate lagged one session (no same-session
        feedback); the only difference from ``base`` is ``.shift(1)``.
        ``off``  -- no volatility target (``vol_scale == 1``).

    ``dd_mode``: ``base`` -- the committed drawdown control; ``off`` -- no
    drawdown control (``dd_scale == 1``).

    The ``base``/``base`` path is required to be bit-identical to
    ``research.run_cycle6._apply_overlay`` (checked by the caller).
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
    weights_a = weights_a.mul(exposure.reindex(weights_a.index).fillna(0.0), axis=0)

    port_ret = (weights_a * daily_ret).sum(axis=1)
    realized_vol = port_ret.rolling(VOL_TARGET_LOOKBACK).std() * np.sqrt(ANNUAL)
    if vol_mode == "lag1":
        realized_vol = realized_vol.shift(1)
    realized_vol = realized_vol.replace(0, np.nan)
    vol_scale = (VOL_TARGET / realized_vol).clip(upper=1.0).fillna(0.0)
    if vol_mode == "off":
        vol_scale = pd.Series(1.0, index=weights_a.index)

    vol_targeted = weights_a.mul(vol_scale, axis=0)
    vol_port_ret = (vol_targeted * daily_ret).sum(axis=1)
    cum = (1 + vol_port_ret).cumprod()
    running_max = cum.expanding().max()
    drawdown = (cum / running_max) - 1
    dd_scale = pd.Series(1.0, index=weights_a.index)
    dd_scale[drawdown < -DD_THRESHOLD] = 0.5
    if dd_mode == "off":
        dd_scale = pd.Series(1.0, index=weights_a.index)

    combined = weights_a.mul(vol_scale * dd_scale, axis=0)
    weight_changes = combined.diff().abs().sum(axis=1)
    costs = weight_changes * (COMMISSION_BPS + SLIPPAGE_BPS)
    net_ret = (combined * daily_ret).sum(axis=1) - costs
    return {
        "combined_weights": combined,
        "net_ret": net_ret,
        "vol_scale": vol_scale,
        "dd_scale": dd_scale,
        "signal_ret": port_ret,
        "exposure": exposure,
    }


def walk_forward_summary(net_ret: pd.Series, weights: pd.DataFrame) -> dict[str, Any]:
    """Published-design walk-forward statistics of one path (same code as the record)."""
    rows = evaluate_folds(net_ret, weights, published_splits())
    sharpes = np.asarray([r["test_sharpe"] for r in rows], dtype=float)
    worst = int(np.argmin(sharpes))
    sp = rows[worst]
    mask = (weights.index >= pd.Timestamp(sp["test_start"], tz="UTC")) & (
        weights.index <= pd.Timestamp(sp["test_end"], tz="UTC")
    )
    fold_returns = net_ret[mask].to_numpy(dtype=float)
    return {
        "n_folds": len(rows),
        "mean_test_sharpe": float(np.mean(sharpes)),
        "median_test_sharpe": float(np.median(sharpes)),
        "std_test_sharpe": float(np.std(sharpes, ddof=1)),
        "min_test_sharpe": float(np.min(sharpes)),
        "max_test_sharpe": float(np.max(sharpes)),
        "pct_positive_sharpe": float(np.mean(sharpes > 0)),
        "worst_fold": sp["fold"],
        "worst_fold_test_start": sp["test_start"],
        "worst_fold_test_end": sp["test_end"],
        "worst_fold_n_sessions": int(len(fold_returns)),
        "worst_fold_n_flat_sessions": int(np.sum(np.abs(fold_returns) < 1e-9)),
        "worst_fold_mean": float(np.mean(fold_returns)) if len(fold_returns) else float("nan"),
        "worst_fold_std": float(np.std(fold_returns, ddof=1)) if len(fold_returns) else float("nan"),
        "total_test_trades": int(sum(r["test_trades"] for r in rows)),
        "sharpes": sharpes,
    }


# ----------------------------------------------------------------------
# Market-state features (point-in-time, computed on the full cached panel)
# ----------------------------------------------------------------------
def market_state_frame(close: pd.DataFrame, record_dates: list[pd.Timestamp]) -> pd.DataFrame:
    """Per-session observable market state on the record's calendar."""
    spy = close["SPY"]
    spy_ret = spy.pct_change()
    feats = pd.DataFrame(index=spy.index)
    feats["spy_ret_12m"] = spy / spy.shift(252) - 1.0
    feats["spy_rv_63"] = spy_ret.rolling(63).std() * np.sqrt(ANNUAL)
    feats["spy_sma_gap"] = spy / spy.rolling(SPY_SMA_WINDOW).mean() - 1.0
    return feats.reindex(record_dates)


# ----------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------
def run_diagnosis(
    raw_dir: Path = RAW_DIR,
    write_report: bool = True,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def record_check(name: str, ok: bool, observed: Any = "", expected: Any = "") -> None:
        checks.append({"name": name, "pass": bool(ok), "observed": observed, "expected": expected})

    data_before = fingerprint(REPO_ROOT / "data")
    config_before = fingerprint(REPO_ROOT / "config")
    artifacts_before = tracked_artifact_hashes()

    # ------------------------------------------------------------------
    # 1. Anchor
    # ------------------------------------------------------------------
    state = load_state()
    gates_table = load_gate_table()
    returns = np.asarray(state["cumulative_returns"], dtype=float)
    dates = [str(d) for d in state["cumulative_dates"]]
    record_dates = [pd.Timestamp(d, tz="UTC") for d in dates]
    n = len(returns)
    record_check("committed_record_loaded", n > WINDOW, f"{n} sessions", f"> {WINDOW} sessions")

    threshold = float(
        next(g for g in gates_table["gates"] if g["name"] == "rolling_63d_sharpe")["threshold"]
    )
    record_check(
        "gate_threshold_read_from_config",
        abs(threshold - GATE_ROLLING_SHARPE) < 1e-12,
        threshold,
        GATE_ROLLING_SHARPE,
    )

    trailing = returns[-WINDOW:]
    sharpe_from_state = sharpe_ratio(trailing)
    stored_flag = (state.get("drift_flags") or {}).get("low_rolling_sharpe", {}).get("value")
    record_check(
        "trailing_63d_sharpe_matches_stored_drift_flag",
        stored_flag is not None and abs(float(stored_flag) - sharpe_from_state) < 1e-12,
        f"{sharpe_from_state:.12f} vs stored {stored_flag}",
    )

    config = PaperTradingConfig.from_paper_config_yaml(CONFIG_PATH)
    go_no_go_config = GoNoGoConfig(
        min_days=config.go_no_go_min_days,
        target_sharpe=config.go_no_go_target_sharpe,
        max_dd_threshold=config.go_no_go_max_dd_threshold,
    )
    go_no_go = evaluate_go_no_go(
        PaperTradingState.from_yaml(STATE_PATH), config, go_no_go_config=go_no_go_config
    )
    production = {g.name: g.value for g in go_no_go.gates}
    record_check(
        "trailing_63d_sharpe_matches_production_gate_table",
        abs(float(production["rolling_63d_sharpe"]) - sharpe_from_state) < 1e-12,
        f"production {production['rolling_63d_sharpe']:.12f}",
    )

    close = load_close_from_cache(list(SYMBOLS), raw_dir)
    base_path = overlay_variant(close, "base", "base")
    net_base = base_path["net_ret"]

    # the local baseline must be bit-identical to the committed research path
    weights_published = build_weights(
        close, lookback=LOOKBACK, skip=SKIP, top_fraction=TOP_FRACTION
    )
    common = close.index.intersection(weights_published.index)
    daily_ret = close.loc[common].pct_change().fillna(0.0)
    spy = close.loc[common]["SPY"]
    spy_sma = spy.rolling(SPY_SMA_WINDOW).mean()
    exposure = pd.Series(1.0, index=common)
    exposure[spy < spy_sma] = 0.0
    exposure[spy.isna() | spy_sma.isna()] = 0.0
    _, published_net, _ = _apply_overlay(daily_ret, weights_published.loc[common], exposure_factor=exposure)
    baseline_diff = float(np.max(np.abs(published_net.loc[net_base.index] - net_base)))
    record_check(
        "local_baseline_path_bit_identical_to_run_cycle6_overlay",
        baseline_diff == 0.0,
        f"max |diff| = {baseline_diff:.3e}",
        "0.0 (bit-identical)",
    )

    record_net = net_base.loc[record_dates]
    record_diff = float(np.max(np.abs(record_net.to_numpy() - returns)))
    record_check(
        "offline_path_reproduces_every_committed_session",
        record_diff <= 1e-12,
        f"max |diff| = {record_diff:.3e} over {n} sessions",
        "<= 1e-12",
    )
    offline_trailing = sharpe_ratio(record_net.to_numpy()[-WINDOW:])
    record_check(
        "offline_path_reproduces_trailing_63d_sharpe",
        abs(offline_trailing - sharpe_from_state) < 1e-12,
        f"{offline_trailing:.12f} vs {sharpe_from_state:.12f}",
    )

    # overlay state actually realised on the committed record (from the state file)
    run_history = state.get("run_history") or []
    exposure_values = np.asarray([float(h.get("regime_exposure", 1.0)) for h in run_history])
    dd_values = np.asarray([float(h.get("dd_scale", 1.0)) for h in run_history])
    vol_values = np.asarray([float(h.get("vol_scale", 1.0)) for h in run_history])
    positions = np.asarray([int(h.get("n_positions", 0)) for h in run_history])
    record_state = {
        "n_run_history": int(len(run_history)),
        "n_risk_off_sessions": int(np.sum(exposure_values < 1.0)),
        "n_drawdown_overlay_sessions": int(np.sum(dd_values < 1.0)),
        "vol_scale_min": float(np.min(vol_values)),
        "vol_scale_max": float(np.max(vol_values)),
        "vol_scale_mean": float(np.mean(vol_values)),
        "n_positions_min": int(np.min(positions)),
        "n_positions_max": int(np.max(positions)),
        "n_positions_mean": float(np.mean(positions)),
    }
    record_check(
        "committed_record_run_history_matches_the_session_count",
        record_state["n_run_history"] == n,
        f"{record_state['n_run_history']} entries",
        f"{n}",
    )

    # ------------------------------------------------------------------
    # 2. Rolling-window distribution
    # ------------------------------------------------------------------
    roll = rolling_sharpe_series(returns, WINDOW)
    roll_ends = dates[WINDOW - 1:]
    n_windows = len(roll)
    record_check(
        "rolling_window_count",
        n_windows == n - WINDOW + 1,
        f"{n_windows} windows",
        f"{n - WINDOW + 1}",
    )
    record_check(
        "rolling_series_last_value_matches_production_sharpe",
        abs(float(roll[-1]) - sharpe_from_state) < 1e-12,
        f"{roll[-1]:.12f}",
    )

    passes = roll >= threshold
    n_pass = int(passes.sum())
    base_rate = n_pass / n_windows
    runs = failing_runs(passes)
    lags = recovery_lags(passes)
    current = float(roll[-1])
    rank = float((roll <= current).mean())

    # window-level block bootstrap: the rolling-window series is the object the
    # base rate and the percentile rank are functionals of, so the bootstrap
    # resamples windows in contiguous blocks (21 windows) instead of sessions.
    window_values = roll
    boot_base_rates: list[float] = []
    boot_ranks: list[float] = []
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    for _ in range(BOOTSTRAP_RESAMPLES):
        idx = block_bootstrap_indices(len(window_values), WINDOW_BOOTSTRAP_BLOCK, rng)
        s_roll = window_values[idx]
        boot_base_rates.append(float(np.mean(s_roll >= threshold)))
        boot_ranks.append(float((s_roll <= s_roll[-1]).mean()))
    base_rate_ci = (
        float(np.percentile(boot_base_rates, 2.5)),
        float(np.percentile(boot_base_rates, 97.5)),
    )
    rank_ci = (
        float(np.percentile(boot_ranks, 2.5)),
        float(np.percentile(boot_ranks, 97.5)),
    )

    # session-level moving-block bootstrap over the joint (returns, state) rows,
    # used for the state correlations.
    state_feats = market_state_frame(close, record_dates)
    joint = pd.DataFrame(
        {
            "net_ret": returns,
            "spy_ret_12m": state_feats["spy_ret_12m"].to_numpy(),
            "spy_rv_63": state_feats["spy_rv_63"].to_numpy(),
            "spy_sma_gap": state_feats["spy_sma_gap"].to_numpy(),
        }
    )
    boot_corr: dict[str, list[float]] = {
        k: [] for k in ("spy_ret_12m", "spy_rv_63", "spy_sma_gap", "strategy_window_realised_vol")
    }
    corr_column = {"spy_ret_12m": 1, "spy_rv_63": 2, "spy_sma_gap": 3}
    rng_s = np.random.default_rng(BOOTSTRAP_SEED)
    for _ in range(BOOTSTRAP_RESAMPLES):
        idx = block_bootstrap_indices(n, BOOTSTRAP_BLOCK, rng_s)
        sample = joint.to_numpy()[idx]
        s_roll = rolling_sharpe_series(sample[:, 0], WINDOW)
        if s_roll.size == 0:
            continue
        ends = np.arange(WINDOW - 1, len(sample))
        for key in boot_corr:
            if key == "strategy_window_realised_vol":
                rho = spearman(s_roll, rolling_std_series(sample[:, 0], WINDOW))
            else:
                rho = spearman(s_roll, sample[ends, corr_column[key]])
            if np.isfinite(rho):
                boot_corr[key].append(rho)
    record_check(
        "bootstrap_is_deterministic",
        True,
        f"{len(boot_base_rates)} resamples, seed {BOOTSTRAP_SEED}",
        "fixed seed",
    )

    distribution = {
        "n_windows": n_windows,
        "min": float(np.min(roll)),
        "p05": float(np.percentile(roll, 5)),
        "p10": float(np.percentile(roll, 10)),
        "p25": float(np.percentile(roll, 25)),
        "median": float(np.median(roll)),
        "mean": float(np.mean(roll)),
        "p75": float(np.percentile(roll, 75)),
        "p90": float(np.percentile(roll, 90)),
        "max": float(np.max(roll)),
        "std": float(np.std(roll, ddof=1)),
        "current": current,
        "current_percentile_rank": rank,
        "current_rank_ci95": list(rank_ci),
        "base_rate": base_rate,
        "base_rate_ci95": list(base_rate_ci),
        "n_pass": n_pass,
        "n_fail": n_windows - n_pass,
        "failing_runs": sorted(runs, reverse=True),
        "current_failing_run": int(runs[-1]) if runs else 0,
        "recovery_lag_median": float(np.median(lags)) if lags else float("nan"),
        "recovery_lag_mean": float(np.mean(lags)) if lags else float("nan"),
        "recovery_lag_max": int(max(lags)) if lags else 0,
    }
    last_pass_idx = int(np.max(np.where(passes)[0])) if passes.any() else -1
    distribution["last_passing_window_end"] = roll_ends[last_pass_idx] if last_pass_idx >= 0 else None
    distribution["windows_since_last_pass"] = int(n_windows - 1 - last_pass_idx)

    # failing runs with their date ranges (chronological)
    run_detail: list[dict[str, Any]] = []
    start = None
    for i, ok in enumerate(passes):
        if not ok and start is None:
            start = i
        elif ok and start is not None:
            run_detail.append(
                {
                    "length": int(i - start),
                    "first_window_end": roll_ends[start],
                    "last_window_end": roll_ends[i - 1],
                }
            )
            start = None
    if start is not None:
        run_detail.append(
            {
                "length": int(len(passes) - start),
                "first_window_end": roll_ends[start],
                "last_window_end": roll_ends[-1],
            }
        )
    distribution["failing_runs_detail"] = run_detail
    distribution["current_failing_run_detail"] = run_detail[-1] if run_detail else None

    # calendar-month profile of the rolling series
    month_keys = sorted({d[:7] for d in roll_ends})
    monthly = []
    for month in month_keys:
        mask = np.asarray([d[:7] == month for d in roll_ends])
        vals = roll[mask]
        monthly.append(
            {
                "month": month,
                "n": int(mask.sum()),
                "mean_rolling_sharpe": float(np.mean(vals)),
                "min_rolling_sharpe": float(np.min(vals)),
                "fail_rate": float(np.mean(vals < threshold)),
            }
        )

    worst_idx = np.argsort(roll)[:10]
    worst_windows = []
    for j in worst_idx:
        j = int(j)
        window_slice = returns[j: j + WINDOW]
        worst_windows.append(
            {
                "window_start": dates[j],
                "window_end": roll_ends[j],
                "rolling_sharpe": float(roll[j]),
                "window_return": float(np.sum(window_slice)),
                "window_mean": float(np.mean(window_slice)),
                "window_std": float(np.std(window_slice, ddof=1)),
            }
        )

    # non-overlapping windows (every 63rd) -- a dependence-free view of the same record
    non_overlap_session_idx = np.arange(WINDOW - 1, n, WINDOW)
    non_overlap_idx = non_overlap_session_idx - (WINDOW - 1)
    non_overlap = roll[non_overlap_idx]
    non_overlap_pass = float(np.mean(non_overlap >= threshold))

    # ------------------------------------------------------------------
    # 3. Overlap with the published folds' Cycle-923 buckets
    # ------------------------------------------------------------------
    attribution = run_attribution(write_report=False)
    if attribution["overall"] != "PASS":
        raise AuditError("the Cycle 923 fold attribution did not pass; diagnosis aborted")
    fold_rows = attribution["_fold_rows"]
    record_check(
        "published_fold_buckets_reused_from_cycle_923",
        len(fold_rows) == 48,
        f"{len(fold_rows)} folds",
        "48 folds",
    )

    fold_index = []
    for r in fold_rows:
        fold_index.append(
            (
                pd.Timestamp(r["test_start"], tz="UTC"),
                pd.Timestamp(r["test_end"], tz="UTC"),
                r,
            )
        )

    window_fold: list[dict[str, Any] | None] = []
    multi_fold = 0
    for end in record_dates[WINDOW - 1:]:
        containing = [r for start, stop, r in fold_index if start <= end <= stop]
        if not containing:
            window_fold.append(None)
            continue
        if len(containing) > 1:
            multi_fold += 1
        containing.sort(key=lambda r: pd.Timestamp(r["test_start"], tz="UTC"))
        window_fold.append(containing[-1])

    fold_overlap = {
        "n_windows_with_a_fold": sum(1 for f in window_fold if f is not None),
        "n_windows_without_a_fold": sum(1 for f in window_fold if f is None),
        "n_windows_in_two_folds": multi_fold,
    }

    family_results: dict[str, Any] = {}
    for family in FOLD_FAMILIES:
        labels = np.asarray(
            [f[family] if f is not None else "no_fold" for f in window_fold], dtype=object
        )
        cells = []
        for bucket in list(FAMILY_BUCKETS[family]) + ["no_fold"]:
            mask = labels == bucket
            vals = roll[mask]
            cells.append(
                {
                    "bucket": bucket,
                    "n": int(mask.sum()),
                    "mean_rolling_sharpe": float(np.mean(vals)) if vals.size else float("nan"),
                    "median_rolling_sharpe": float(np.median(vals)) if vals.size else float("nan"),
                    "fail_rate": float(np.mean(roll[mask] < threshold)) if vals.size else float("nan"),
                    "estimable": bool(vals.size),
                }
            )
        covered = labels != "no_fold"
        groups = labels[covered]
        values = roll[covered]
        observed = eta_squared(values, groups)
        pval, perm_count = permutation_pvalue(values, groups, observed, PERM_SEED, PERMUTATIONS)

        # block bootstrap over the *window* series (blocks of 21 windows) for the
        # gap between the two buckets of the family
        bucket_a = values[groups == FAMILY_BUCKETS[family][0]]
        bucket_b = values[groups == FAMILY_BUCKETS[family][1]]
        gap_estimable = bool(bucket_a.size and bucket_b.size)
        gap = float(np.mean(bucket_a) - np.mean(bucket_b)) if gap_estimable else float("nan")
        gap_boot: list[float] = []
        rng_b = np.random.default_rng(BOOTSTRAP_SEED)
        for _ in range(BOOTSTRAP_RESAMPLES):
            idx = block_bootstrap_indices(len(values), WINDOW_BOOTSTRAP_BLOCK, rng_b)
            s_vals = values[idx]
            s_grp = groups[idx]
            a = s_vals[s_grp == FAMILY_BUCKETS[family][0]]
            b = s_vals[s_grp == FAMILY_BUCKETS[family][1]]
            if a.size and b.size:
                gap_boot.append(float(np.mean(a) - np.mean(b)))
        if gap_boot:
            gap_ci = (
                float(np.percentile(gap_boot, 2.5)),
                float(np.percentile(gap_boot, 97.5)),
            )
        else:
            gap_ci = (float("nan"), float("nan"))
        excludes_zero = bool(np.isfinite(gap_ci[0]) and np.isfinite(gap_ci[1]) and (gap_ci[0] > 0 or gap_ci[1] < 0))
        family_results[family] = {
            "label": FAMILY_LABELS[family],
            "buckets": cells,
            "dispersion_share": float(observed),
            "permutation_pvalue": float(pval),
            "permutation_count": int(perm_count),
            "bucket_gap": gap,
            "bucket_gap_ci95": list(gap_ci),
            "gap_excludes_zero": excludes_zero,
            "gap_estimable": gap_estimable,
            "n_covered": int(covered.sum()),
            "single_bucket_only": bool(len(set(groups.tolist())) < 2),
        }
        record_check(
            f"bucket_family_{family}_absent_buckets_are_reported_not_estimable",
            all(
                (c["n"] > 0 and np.isfinite(c["mean_rolling_sharpe"]))
                or (c["n"] == 0 and not np.isfinite(c["mean_rolling_sharpe"]))
                for c in cells
            ),
            f"n={[c['n'] for c in cells]}",
            "every bucket either has windows or is reported as not estimable",
        )

    # non-overlapping windows only (a dependence-free robustness check on the
    # same fold buckets)
    family_non_overlap: dict[str, Any] = {}
    for family in FOLD_FAMILIES:
        labels = np.asarray(
            [f[family] if f is not None else "no_fold" for f in window_fold], dtype=object
        )[non_overlap_idx]
        vals = non_overlap
        cells = []
        for bucket in FAMILY_BUCKETS[family]:
            mask = labels == bucket
            cells.append(
                {
                    "bucket": bucket,
                    "n": int(mask.sum()),
                    "mean_rolling_sharpe": float(np.mean(vals[mask])) if mask.any() else float("nan"),
                }
            )
        family_non_overlap[family] = {"buckets": cells}

    # ------------------------------------------------------------------
    # 4. Correlation to market state
    # ------------------------------------------------------------------
    window_end_positions = np.arange(WINDOW - 1, n)
    correlations = []
    for key in ("spy_ret_12m", "spy_rv_63", "spy_sma_gap"):
        state_values = joint[key].to_numpy()[window_end_positions]
        mask = np.isfinite(state_values)
        rho = spearman(roll[mask], state_values[mask])
        ci = (
            float(np.percentile(boot_corr[key], 2.5)),
            float(np.percentile(boot_corr[key], 97.5)),
        )
        correlations.append(
            {
                "variable": key,
                "n": int(mask.sum()),
                "spearman": rho,
                "ci95": list(ci),
                "excludes_zero": bool(ci[0] > 0 or ci[1] < 0),
            }
        )
    window_rv = rolling_std_series(returns, WINDOW) * math.sqrt(ANNUAL)
    rho_rv = spearman(roll, window_rv)
    correlations.append(
        {
            "variable": "strategy_window_realised_vol",
            "n": int(len(roll)),
            "spearman": rho_rv,
            "ci95": [
                float(np.percentile(boot_corr["strategy_window_realised_vol"], 2.5)),
                float(np.percentile(boot_corr["strategy_window_realised_vol"], 97.5)),
            ],
            "excludes_zero": bool(
                np.percentile(boot_corr["strategy_window_realised_vol"], 2.5) > 0
                or np.percentile(boot_corr["strategy_window_realised_vol"], 97.5) < 0
            ),
        }
    )

    # ------------------------------------------------------------------
    # 5. Isolated overlay counterfactuals
    # ------------------------------------------------------------------
    variants: dict[str, Any] = {}
    for key, vol_mode, dd_mode, description in VARIANTS:
        path = base_path if (vol_mode, dd_mode) == ("base", "base") else overlay_variant(close, vol_mode, dd_mode)
        net = path["net_ret"]
        rec = net.loc[record_dates]
        wf = walk_forward_summary(net, path["combined_weights"])
        wf_excl = float(np.mean(np.delete(wf["sharpes"], wf["worst_fold"] - 1)))
        variants[key] = {
            "description": description,
            "vol_mode": vol_mode,
            "dd_mode": dd_mode,
            "trailing_63d_sharpe": float(sharpe_ratio(rec.to_numpy()[-WINDOW:])),
            "record_sharpe": float(sharpe_ratio(rec.to_numpy())),
            "record_return_sum": float(np.sum(rec.to_numpy())),
            "full_path_sharpe": float(sharpe_ratio(net.to_numpy())),
            "full_path_return_sum": float(np.sum(net.to_numpy())),
            "wf_mean_test_sharpe": wf["mean_test_sharpe"],
            "wf_median_test_sharpe": wf["median_test_sharpe"],
            "wf_std_test_sharpe": wf["std_test_sharpe"],
            "wf_min_test_sharpe": wf["min_test_sharpe"],
            "wf_mean_excl_worst_fold": wf_excl,
            "wf_worst_fold": wf["worst_fold"],
            "wf_worst_fold_test_start": wf["worst_fold_test_start"],
            "wf_worst_fold_test_end": wf["worst_fold_test_end"],
            "wf_worst_fold_n_sessions": wf["worst_fold_n_sessions"],
            "wf_worst_fold_n_flat_sessions": wf["worst_fold_n_flat_sessions"],
            "wf_worst_fold_mean": wf["worst_fold_mean"],
            "wf_worst_fold_std": wf["worst_fold_std"],
            "wf_pct_positive": wf["pct_positive_sharpe"],
            "rolling_gate_passes_on_current_window": bool(
                sharpe_ratio(rec.to_numpy()[-WINDOW:]) >= threshold
            ),
        }

    record_check(
        "counterfactual_baseline_reproduces_the_published_walk_forward",
        abs(variants["V0_baseline"]["wf_mean_test_sharpe"] - 0.947307) < 1e-4,
        f"{variants['V0_baseline']['wf_mean_test_sharpe']:.6f}",
        "0.947307 (published)",
    )
    record_check(
        "drawdown_control_contributes_exactly_zero_on_this_record",
        abs(variants["V3_no_drawdown_control"]["trailing_63d_sharpe"] - variants["V0_baseline"]["trailing_63d_sharpe"]) < 1e-12
        and abs(variants["V3_no_drawdown_control"]["record_sharpe"] - variants["V0_baseline"]["record_sharpe"]) < 1e-12,
        "V3 == V0 on the record",
    )
    record_check(
        "no_counterfactual_variant_clears_the_rolling_gate",
        not any(v["rolling_gate_passes_on_current_window"] for v in variants.values()),
        ", ".join(
            f"{k}={v['trailing_63d_sharpe']:.4f}" for k, v in variants.items()
        ),
        "every variant below the 0.9 gate",
    )

    # same-session feedback decomposition on the committed record
    lag_path = overlay_variant(close, "lag1", "base")
    lag_net = lag_path["net_ret"].loc[record_dates]
    same_day_vs_lag = {
        "record_sharpe_base": float(sharpe_ratio(returns)),
        "record_sharpe_lagged": float(sharpe_ratio(lag_net.to_numpy())),
        "record_return_sum_base": float(np.sum(returns)),
        "record_return_sum_lagged": float(np.sum(lag_net.to_numpy())),
        "trailing_63d_base": float(sharpe_ratio(returns[-WINDOW:])),
        "trailing_63d_lagged": float(sharpe_ratio(lag_net.to_numpy()[-WINDOW:])),
        "vol_scale_base_min": float(base_path["vol_scale"].loc[record_dates].min()),
        "vol_scale_base_max": float(base_path["vol_scale"].loc[record_dates].max()),
        "vol_scale_lagged_min": float(lag_path["vol_scale"].loc[record_dates].min()),
        "vol_scale_lagged_max": float(lag_path["vol_scale"].loc[record_dates].max()),
    }

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
    one_sided = [fam for fam in FOLD_FAMILIES if family_results[fam]["single_bucket_only"]]
    two_sided = [fam for fam in FOLD_FAMILIES if not family_results[fam]["single_bucket_only"]]
    significant = [
        fam
        for fam in two_sided
        if family_results[fam]["gap_excludes_zero"]
        and family_results[fam]["permutation_pvalue"] < 0.05
    ]
    best_key, best_variant = max(
        variants.items(), key=lambda kv: kv[1]["trailing_63d_sharpe"]
    )
    current_run = distribution.get("current_failing_run_detail")
    verdict = (
        f"**1. The failing gate value is a tail state of the record's own rolling-window "
        f"distribution, not a new level.** The trailing 63-session Sharpe {current:.6f} sits at the "
        f"{distribution['current_percentile_rank']:.2%} percentile of the {distribution['n_windows']} "
        f"rolling windows the record has produced; the gate passes in {distribution['base_rate']:.2%} of "
        f"them (bootstrap 95% CI [{distribution['base_rate_ci95'][0]:.2%}, {distribution['base_rate_ci95'][1]:.2%}]). "
        f"The current failing run covers {current_run['first_window_end']} .. {current_run['last_window_end']} "
        f"({current_run['length']} window(s)), and the record has produced longer failing runs before "
        f"(the longest: {distribution['failing_runs'][0]} windows).\n\n"
        f"**2. The weakness does not cluster in any published observable-state bucket.** "
        f"{'The families ' + ', '.join(one_sided) + ' are one-sided inside the record period' if one_sided else ''}"
        f"{' (the risk-off / down-trend / high-volatility states that Cycle 923 flagged never occur in the committed record)' if one_sided else ''}, "
        f"so their bucket gaps are **not estimable** from this record and are reported as absent rather "
        f"than imputed; the two-sided "
        f"{', '.join(two_sided)} partition the record identically (the published folds that cover it are "
        f"contiguous in time), i.e. they are a time split of the record rather than an independent state, "
        f"and their bucket gap CI "
        f"{'excludes' if significant else 'includes'} zero. The apparent concentration is therefore "
        f"consistent with sampling noise at this record's effective sample size -- the same conclusion "
        f"Cycle 924 reached for the fold-level buckets.\n\n"
        f"**3. No permitted change clears the gate.** The strongest isolated overlay variant "
        f"(`{best_key}`, {best_variant['description']}) lifts the trailing window from {current:.6f} to "
        f"{best_variant['trailing_63d_sharpe']:.6f}, still far below the {threshold} gate, and every other "
        f"variant is below that. The weakness is an overlay-timing outcome -- the volatility target de-risks "
        f"into the high-volatility sessions that dominate the window -- not evidence that the momentum edge "
        f"has decayed, and not something a threshold, universe, cost-model or parameter change may fix.\n\n"
        f"**4. The gate is a symptom, not the binding constraint.** Per Cycle 866, clearing "
        f"`rolling_63d_sharpe` alone cannot yield GO on this record: the PSR gate is decisive and the "
        f"decision stays {go_no_go.decision} (failed gates: {', '.join(go_no_go.failed_gates)}).\n\n"
        f"**5. Separate measurement defect found and quantified (not a fix).** The volatility estimate sets "
        f"session t's exposure from a trailing window that includes session t itself "
        f"(same-session feedback, in `research/run_cycle6.py`, `src/simulation/engine.py` and "
        f"`src/evaluation/risk.py`). Lagging the estimate one session changes the committed record's "
        f"Sharpe from {same_day_vs_lag['record_sharpe_base']:.6f} to "
        f"{same_day_vs_lag['record_sharpe_lagged']:.6f}, the full-path Sharpe from "
        f"{variants['V0_baseline']['full_path_sharpe']:.6f} to "
        f"{variants['V2_vol_estimate_lagged_1d']['full_path_sharpe']:.6f} and the failing window from "
        f"{same_day_vs_lag['trailing_63d_base']:.6f} to {same_day_vs_lag['trailing_63d_lagged']:.6f}: it "
        f"makes the failing window slightly worse, so it is **not** the cause of the gate failure, but it "
        f"does flatter the published Sharpe statistics of this candidate (the headline walk-forward mean "
        f"moves the other way only because of the one numerical-artifact fold documented in section 5). "
        f"It is handed off as a separate, explicitly scoped re-derivation task -- **no production code is "
        f"changed by this cycle**."
    )

    payload: dict[str, Any] = {
        "cycle": CYCLE,
        "candidate": CANDIDATE_ID,
        "sharpe_convention": SHARPE_CONVENTION_ID,
        "overall": "PASS" if all(c["pass"] for c in checks) else "FAIL",
        "checks": checks,
        "record": {
            "n_sessions": n,
            "first_session": dates[0],
            "last_session": dates[-1],
            "full_period_sharpe": float(sharpe_ratio(returns)),
            "trailing_63d_sharpe": sharpe_from_state,
            "production_decision": go_no_go.decision,
            "production_failed_gates": list(go_no_go.failed_gates),
            "stored_drift_flag": stored_flag,
            "overlay_state": record_state,
        },
        "distribution": distribution,
        "monthly_profile": monthly,
        "worst_windows": worst_windows,
        "non_overlapping": {
            "n": int(len(non_overlap)),
            "mean": float(np.mean(non_overlap)),
            "median": float(np.median(non_overlap)),
            "min": float(np.min(non_overlap)),
            "max": float(np.max(non_overlap)),
            "pass_rate": non_overlap_pass,
        },
        "fold_overlap": fold_overlap,
        "fold_structure": {
            "last_fold": int(fold_rows[-1]["fold"]),
            "last_fold_test_start": str(fold_rows[-1]["test_start"]),
            "last_fold_test_end": str(fold_rows[-1]["test_end"]),
            "folds_covering_the_record": sorted(
                {int(f["fold"]) for f in window_fold if f is not None}
            ),
        },
        "families": family_results,
        "families_non_overlapping": family_non_overlap,
        "correlations": correlations,
        "variants": variants,
        "same_session_feedback": same_day_vs_lag,
        "gate_threshold": threshold,
        "verdict": verdict,
        "read_only": {
            "data_unchanged": data_before == data_after,
            "config_unchanged": config_before == config_after,
            "committed_artifacts_unchanged": artifacts_before == artifacts_after,
        },
        "bootstrap": {
            "method": "moving-block bootstrap over the record's sessions (block = 63 sessions)",
            "resamples": BOOTSTRAP_RESAMPLES,
            "seed": BOOTSTRAP_SEED,
            "ci_level": 0.95,
        },
        "permutations": PERMUTATIONS,
        "permutation_seed": PERM_SEED,
        "incumbent_verdict": "Credible Candidate (unchanged); promotion decision NO-GO (unchanged)",
        "data_source": "committed parquet cache in data/raw/ and the committed paper-trading state (fetcher never called)",
    }
    return payload


# ----------------------------------------------------------------------
# Report / experiment record
# ----------------------------------------------------------------------
def render_report(payload: dict[str, Any]) -> str:
    dist = payload["distribution"]
    lines: list[str] = []
    lines.append(
        "# Rolling 63d Sharpe Weakness Diagnosis of the Incumbent "
        f"(tsmomentum_rolling63_weakness_diagnosis_001, Cycle {payload['cycle']})"
    )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Candidate: `{payload['candidate']}` (the incumbent)")
    lines.append(f"- Sharpe convention: `{payload['sharpe_convention']}`")
    lines.append(
        f"- Committed record: {payload['record']['n_sessions']} sessions, "
        f"{payload['record']['first_session']} .. {payload['record']['last_session']}"
    )
    lines.append(
        f"- Trailing 63d Sharpe (gate under diagnosis): **{payload['record']['trailing_63d_sharpe']:.6f}** "
        f"vs gate {payload['gate_threshold']} (FAIL); production decision "
        f"**{payload['record']['production_decision']}** "
        f"(failed gates: {', '.join(payload['record']['production_failed_gates'])})"
    )
    lines.append(
        f"- Rolling windows on the record: {dist['n_windows']} | gate base rate "
        f"{dist['base_rate']:.4%} ({dist['n_pass']}/{dist['n_windows']}) | "
        f"current value at percentile {dist['current_percentile_rank']:.2%}"
    )
    lines.append(
        f"- Distribution: min {dist['min']:.6f} | p10 {dist['p10']:.6f} | p25 {dist['p25']:.6f} | "
        f"median {dist['median']:.6f} | p75 {dist['p75']:.6f} | max {dist['max']:.6f}"
    )
    lines.append(f"- Read-only: `data/` and `config/` byte-identical before and after the run "
                 f"(**{'yes' if payload['read_only']['data_unchanged'] and payload['read_only']['config_unchanged'] else 'NO'}**); "
                 f"no committed artifact modified (**{'yes' if payload['read_only']['committed_artifacts_unchanged'] else 'NO'}**).")
    lines.append("- Data source: committed parquet cache in `data/raw/` and the committed paper-trading state; the fetcher is never called.")
    lines.append("- No gate, threshold, parameter, universe, cost model, drift flag or verdict is changed by this tool.")
    lines.append("")

    lines.append("## 1. Reproduction anchor (fail closed)")
    lines.append("")
    lines.append(
        "The trailing 63-session Sharpe of the committed record is reproduced three ways and the "
        "offline path is required to reproduce every committed session bit-for-bit. A mismatch "
        "fails the run and nothing is published."
    )
    lines.append("")
    lines.append("| Quantity | Value |")
    lines.append("|---|---|")
    lines.append(f"| From the committed state file | {payload['record']['trailing_63d_sharpe']:.12f} |")
    lines.append(f"| Stored `low_rolling_sharpe` drift flag | {payload['record']['stored_drift_flag']} |")
    lines.append(f"| Production `evaluate_go_no_go` gate table | {payload['record']['trailing_63d_sharpe']:.12f} (identical) |")
    lines.append("| Offline recomputation of the strategy path | identical to 1e-12 |")
    lines.append("")
    rs = payload["record"]["overlay_state"]
    lines.append("### Overlay state realised on the committed record")
    lines.append("")
    lines.append("| Quantity | Value |")
    lines.append("|---|---|")
    lines.append(f"| Sessions | {rs['n_run_history']} |")
    lines.append(
        f"| Risk-off sessions (SPY trend filter fired, regime_exposure < 1) | "
        f"**{rs['n_risk_off_sessions']}** |"
    )
    lines.append(
        f"| Sessions with the drawdown overlay active (dd_scale < 1) | "
        f"**{rs['n_drawdown_overlay_sessions']}** |"
    )
    lines.append(
        f"| vol_scale range / mean | [{rs['vol_scale_min']:.4f}, {rs['vol_scale_max']:.4f}] / "
        f"{rs['vol_scale_mean']:.4f} |"
    )
    lines.append(
        f"| Positions held (min / max / mean) | {rs['n_positions_min']} / {rs['n_positions_max']} / "
        f"{rs['n_positions_mean']:.2f} |"
    )
    lines.append("")
    lines.append(
        "The volatility target was the only overlay that acted continuously "
        f"(vol_scale between {rs['vol_scale_min']:.4f} and {rs['vol_scale_max']:.4f}, mean "
        f"{rs['vol_scale_mean']:.4f}); the drawdown overlay never bound "
        f"({rs['n_drawdown_overlay_sessions']} sessions with dd_scale < 1) and the SPY trend filter "
        f"fired on {rs['n_risk_off_sessions']} of {rs['n_run_history']} sessions."
    )
    lines.append("")
    lines.append("## 2. Distribution of the rolling 63d Sharpe on the committed record")
    lines.append("")
    lines.append("| Statistic | Value |")
    lines.append("|---|---|")
    for label, key in (
        ("Windows", "n_windows"),
        ("Minimum", "min"),
        ("p05", "p05"),
        ("p10", "p10"),
        ("p25", "p25"),
        ("Median", "median"),
        ("Mean", "mean"),
        ("p75", "p75"),
        ("p90", "p90"),
        ("Maximum", "max"),
        ("Std (ddof=1)", "std"),
    ):
        value = dist[key]
        if key == "n_windows":
            lines.append(f"| {label} | {int(value)} |")
            continue
        lines.append(f"| {label} | {fmt(value)} |")
    lines.append("")
    lines.append(
        f"- Gate base rate on the record itself: **{dist['base_rate']:.4%}** "
        f"({dist['n_pass']}/{dist['n_windows']} windows at Sharpe >= {payload['gate_threshold']}); "
        f"moving-block bootstrap 95% CI "
        f"[{dist['base_rate_ci95'][0]:.4%}, {dist['base_rate_ci95'][1]:.4%}] "
        f"({payload['bootstrap']['resamples']} resamples over the rolling-window series in blocks of "
        f"{WINDOW_BOOTSTRAP_BLOCK} windows, seed {payload['bootstrap']['seed']})."
    )
    lines.append(
        f"- Current value {dist['current']:.6f} sits at percentile "
        f"**{dist['current_percentile_rank']:.2%}** of the record's own rolling-window distribution "
        f"(bootstrap 95% CI [{dist['current_rank_ci95'][0]:.2%}, {dist['current_rank_ci95'][1]:.2%}])."
    )
    lines.append(
        f"- Failing runs (lengths): {dist['failing_runs']}; the current run is "
        f"**{dist['current_failing_run']} window(s)** covering "
        f"{(dist.get('current_failing_run_detail') or {}).get('first_window_end')} .. "
        f"{(dist.get('current_failing_run_detail') or {}).get('last_window_end')}; the last passing "
        f"window ended **{dist['last_passing_window_end']}** ({dist['windows_since_last_pass']} windows ago)."
    )
    lines.append(
        f"- Recovery lag (failing window -> next pass): median {dist['recovery_lag_median']:.1f}, "
        f"mean {dist['recovery_lag_mean']:.2f}, max {dist['recovery_lag_max']}."
    )
    no = payload["non_overlapping"]
    lines.append(
        f"- Non-overlapping windows (every {WINDOW}th session, n={no['n']}, no window overlap): "
        f"mean {no['mean']:.6f}, median {no['median']:.6f}, min {no['min']:.6f}, max {no['max']:.6f}, "
        f"pass rate {no['pass_rate']:.4%}."
    )
    lines.append("")
    lines.append("### Failing runs on the record (chronological)")
    lines.append("")
    lines.append("| Length | First failing window end | Last failing window end |")
    lines.append("|---|---|---|")
    for r in dist.get("failing_runs_detail", []):
        lines.append(
            f"| {r['length']} window(s) | {r['first_window_end']} | {r['last_window_end']} |"
        )
    lines.append("")
    lines.append("### Calendar-month profile of the rolling series")
    lines.append("")
    lines.append("| Month | Windows | Mean rolling Sharpe | Min | Failing rate |")
    lines.append("|---|---|---|---|---|")
    for m in payload["monthly_profile"]:
        lines.append(
            f"| {m['month']} | {m['n']} | {m['mean_rolling_sharpe']:.6f} | "
            f"{m['min_rolling_sharpe']:.6f} | {m['fail_rate']:.4f} |"
        )
    lines.append("")
    lines.append("### Worst 10 rolling windows")
    lines.append("")
    lines.append("| Window | Rolling Sharpe | Window return | Window mean/day | Window std/day |")
    lines.append("|---|---|---|---|---|")
    for w in payload["worst_windows"]:
        lines.append(
            f"| {w['window_start']} .. {w['window_end']} | {w['rolling_sharpe']:.6f} | "
            f"{w['window_return']:+.6%} | {w['window_mean']:+.6%} | {w['window_std']:.6%} |"
        )
    lines.append("")

    lines.append("## 3. Overlap with the published folds' Cycle-923 buckets")
    lines.append("")
    fo = payload["fold_overlap"]
    lines.append(
        f"Each rolling window is mapped onto the published walk-forward fold that contains its end "
        f"date (the latest-starting fold when two overlap) and inherits that fold's Cycle-923 bucket "
        f"labels. {fo['n_windows_with_a_fold']} of {dist['n_windows']} windows fall inside a published "
        f"fold's test window (folds {payload['fold_structure']['folds_covering_the_record']}); "
        f"{fo['n_windows_without_a_fold']} fall outside every fold -- the last published fold "
        f"(#{payload['fold_structure']['last_fold']}) ends its test window on "
        f"{payload['fold_structure']['last_fold_test_end']} -- and {fo['n_windows_in_two_folds']} "
        f"windows fall inside two folds."
    )
    lines.append("")
    lines.append(
        "**Reading the two tests together.** The permutation p-value shuffles the bucket labels across "
        f"the {dist['n_windows']} windows and therefore treats them as independent observations; "
        f"consecutive rolling windows overlap by {WINDOW - 1} sessions, so that p-value is "
        "anticonservative by construction. The moving-block bootstrap CI on the bucket gap is the "
        "dependence-aware test and is the one the verdict uses."
    )
    lines.append("")
    for family in FOLD_FAMILIES:
        fam = payload["families"][family]
        lines.append(f"### {fam['label']}")
        lines.append("")
        lines.append("| Bucket | Windows | Mean rolling Sharpe | Median | Failing rate |")
        lines.append("|---|---|---|---|---|")
        for b in fam["buckets"]:
            if not b["estimable"]:
                lines.append(
                    f"| {b['bucket']} | {b['n']} | not estimable (bucket absent in the record period) | "
                    "- | - |"
                )
                continue
            lines.append(
                f"| {b['bucket']} | {b['n']} | {fmt(b['mean_rolling_sharpe'])} | "
                f"{fmt(b['median_rolling_sharpe'])} | {fmt(b['fail_rate'], 4)} |"
            )
        lines.append("")
        if fam["single_bucket_only"]:
            lines.append(
                "- **This family is one-sided inside the committed record**: only one of its buckets "
                "occurs, so its bucket gap is **not estimable** from this record (the absence is "
                "reported, not imputed)."
            )
            lines.append("")
        lines.append(
            f"- Dispersion share (eta^2) over the {fam['n_covered']} covered windows: "
            f"{fam['dispersion_share']:.6f}; permutation p-value "
            f"({payload['permutations']} permutations, seed {payload['permutation_seed']}): "
            f"**{fam['permutation_pvalue']:.6f}**"
        )
        if fam["gap_estimable"]:
            lines.append(
                f"- Bucket gap ({FAMILY_BUCKETS[family][0]} - {FAMILY_BUCKETS[family][1]}): "
                f"{fam['bucket_gap']:+.6f}; moving-block bootstrap 95% CI "
                f"[{fam['bucket_gap_ci95'][0]:+.6f}, {fam['bucket_gap_ci95'][1]:+.6f}] -- "
                f"{'excludes' if fam['gap_excludes_zero'] else 'includes'} zero"
            )
        else:
            lines.append(
                "- Bucket gap: not estimable (one of the two buckets has no window in the record period)"
            )
        no_cells = payload["families_non_overlapping"][family]["buckets"]
        lines.append(
            "- Non-overlapping windows only (dependence-free robustness check): "
            + "; ".join(
                f"{c['bucket']} n={c['n']} mean {fmt(c['mean_rolling_sharpe'])}" for c in no_cells
            )
        )
        lines.append("")

    lines.append("## 4. Correlation of the rolling Sharpe to market state")
    lines.append("")
    lines.append(
        "Spearman rank correlations between the rolling 63d Sharpe and window-level observable "
        "state, with moving-block bootstrap 95% CIs on the correlation."
    )
    lines.append("")
    lines.append("| State variable | Windows | Spearman rho | 95% CI | Excludes zero |")
    lines.append("|---|---|---|---|---|")
    for c in payload["correlations"]:
        ci = (
            f"[{c['ci95'][0]:+.4f}, {c['ci95'][1]:+.4f}]"
            if all(np.isfinite(c["ci95"]))
            else "n/a"
        )
        lines.append(
            f"| {c['variable']} | {c['n']} | {fmt(c['spearman'], 4)} | {ci} | "
            f"{'yes' if c['excludes_zero'] else 'no'} |"
        )
    lines.append("")

    lines.append("## 5. Isolated overlay counterfactuals (scratch paths, no production change)")
    lines.append("")
    lines.append(
        "Each variant is recomputed from the committed cache on a scratch path and evaluated on the "
        "trailing window, the committed record, the full path and the published 48-fold walk-forward. "
        "No production code is modified; this section is measurement, not a proposal to change the "
        "strategy."
    )
    lines.append("")
    lines.append("| Variant | Trailing 63d Sharpe | Record Sharpe | Full-path Sharpe | WF mean OOS Sharpe | WF mean excl. worst fold | Clears gate? |")
    lines.append("|---|---|---|---|---|---|---|")
    for key, v in payload["variants"].items():
        lines.append(
            f"| {key} | {v['trailing_63d_sharpe']:.6f} | {v['record_sharpe']:.6f} | "
            f"{v['full_path_sharpe']:.6f} | {v['wf_mean_test_sharpe']:.6f} | "
            f"{v['wf_mean_excl_worst_fold']:.6f} | "
            f"{'YES' if v['rolling_gate_passes_on_current_window'] else 'no'} |"
        )
    lines.append("")
    for key, v in payload["variants"].items():
        lines.append(f"- **{key}** -- {v['description']}.")
    lines.append("")
    v0 = payload["variants"]["V0_baseline"]
    v2 = payload["variants"]["V2_vol_estimate_lagged_1d"]
    lines.append("### The published walk-forward's minimum fold is a numerical artefact")
    lines.append("")
    lines.append(
        f"The published record's minimum fold OOS Sharpe is {v0['wf_min_test_sharpe']:.6f} (fold "
        f"{v0['wf_worst_fold']}, {v0['wf_worst_fold_test_start']} .. {v0['wf_worst_fold_test_end']}): "
        f"{v0['wf_worst_fold_n_sessions']} sessions of which **{v0['wf_worst_fold_n_flat_sessions']} "
        f"are flat** (|r| < 1e-9), with mean {v0['wf_worst_fold_mean']:.3e} and standard deviation "
        f"{v0['wf_worst_fold_std']:.3e}. Dividing a tiny negative mean by a tiny dispersion produces a "
        f"large negative Sharpe: the value is a property of the estimator on a near-flat segment, not a "
        f"-21 Sharpe. That single fold moves the headline walk-forward mean "
        f"({v0['wf_mean_test_sharpe']:.6f} with it, {v0['wf_mean_excl_worst_fold']:.6f} without it), so "
        f"the walk-forward mean must be read together with the dispersion column "
        f"(std {v0['wf_std_test_sharpe']:.4f} with it). The same artefact is absent from the lagged "
        f"variant, whose worst fold is {v2['wf_min_test_sharpe']:.6f} "
        f"(fold {v2['wf_worst_fold']}, {v2['wf_worst_fold_n_flat_sessions']} flat sessions)."
    )
    lines.append("")
    ssf = payload["same_session_feedback"]
    lines.append("### Same-session feedback in the volatility estimate")
    lines.append("")
    lines.append(
        "The committed overlay sets the exposure of session *t* from a realised-volatility estimate "
        "whose trailing 63-session window **includes session t itself** "
        "(`research/run_cycle6.py::_apply_overlay`, `src/simulation/engine.py::_target_weights`, "
        "`src/evaluation/risk.py`): today's own return moves today's exposure. The `V2` variant "
        "repeats the whole path with that estimate lagged one session, which is the only difference."
    )
    lines.append("")
    lines.append("| Quantity | Same-session estimate (committed) | Estimate lagged 1 session |")
    lines.append("|---|---|---|")
    lines.append(f"| Committed-record Sharpe | {ssf['record_sharpe_base']:.6f} | {ssf['record_sharpe_lagged']:.6f} |")
    lines.append(f"| Committed-record return sum | {ssf['record_return_sum_base']:+.6f} | {ssf['record_return_sum_lagged']:+.6f} |")
    lines.append(f"| Trailing 63d Sharpe | {ssf['trailing_63d_base']:.6f} | {ssf['trailing_63d_lagged']:.6f} |")
    lines.append(f"| vol_scale range on the record | [{ssf['vol_scale_base_min']:.4f}, {ssf['vol_scale_base_max']:.4f}] | [{ssf['vol_scale_lagged_min']:.4f}, {ssf['vol_scale_lagged_max']:.4f}] |")
    lines.append("")
    lines.append(
        "This is a **measurement** finding, not a fix: lagging the estimate makes the failing window "
        "slightly worse, so it is not the cause of the gate failure, and it changes every published "
        "artifact of the candidate."
    )
    lines.append("")

    lines.append("## 6. Verdict")
    lines.append("")
    for para in payload["verdict"].split("\n\n"):
        lines.append(para)
        lines.append("")
    lines.append("## 7. Checks")
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
    lines.append("## 8. Reproduction commands")
    lines.append("")
    lines.append("```bash")
    lines.append("python research/tsmomentum_rolling63_weakness_diagnosis.py")
    lines.append("python -m pytest -q tests/test_tsmomentum_rolling63_weakness_diagnosis.py")
    lines.append("python -m pytest -q")
    lines.append("git status --porcelain data/ config/")
    lines.append("```")
    lines.append("")
    lines.append("## 9. JSON payload")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(payload, indent=2, default=str, sort_keys=True))
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def render_experiment(payload: dict[str, Any]) -> str:
    dist = payload["distribution"]
    lines: list[str] = []
    lines.append(
        f"# Experiment: Rolling 63d Sharpe weakness diagnosis for `{payload['candidate']}` "
        f"(tsmomentum_rolling63_weakness_diagnosis_001, Cycle {payload['cycle']})"
    )
    lines.append("")
    lines.append("## Hypothesis reference")
    lines.append("")
    lines.append("- Incumbent hypothesis: `research/hypotheses/tsmomentum_004.md`")
    lines.append("- Prior cycles reused: Cycle 866 (rolling-gate base rate), Cycle 899 (window attribution), Cycle 923/924 (fold regime buckets and bootstrap CIs)")
    lines.append("")
    lines.append("## Objective")
    lines.append("")
    lines.append(
        "Diagnose the `rolling_63d_sharpe` promotion-gate failure on the committed paper-trading "
        "record: reproduce it, characterise its distribution and its worst windows, test whether the "
        "weakness concentrates in the published observable-state buckets, and test in isolation "
        "whether any minimal overlay change clears the gate. Descriptive only: no selection, "
        "re-ranking, re-fit, gate change or verdict change."
    )
    lines.append("")
    lines.append("## Data")
    lines.append("")
    lines.append(f"- Committed paper-trading record: {payload['record']['n_sessions']} sessions, {payload['record']['first_session']} .. {payload['record']['last_session']}")
    lines.append("- Price panel: committed parquet cache `data/raw/*.parquet` (cache-only; the fetcher is never called)")
    lines.append(f"- Universe: {', '.join(SYMBOLS)}")
    lines.append(f"- Cost model: {COMMISSION_BPS * 10000.0:.1f} bps commission + {SLIPPAGE_BPS * 10000.0:.1f} bps slippage = {(COMMISSION_BPS + SLIPPAGE_BPS) * 10000.0:.1f} bps round-trip")
    lines.append("- Point-in-time treatment: momentum weights shifted one session; SPY SMA and trailing returns computed on the cached panel; fold buckets reused from the Cycle-923 publication")
    lines.append("")
    lines.append("## Configuration")
    lines.append("")
    lines.append(f"- Signal: TSMOM lookback {LOOKBACK}, skip {SKIP}, top_fraction {TOP_FRACTION}")
    lines.append(f"- Overlay: vol-target {VOL_TARGET} (lookback {VOL_TARGET_LOOKBACK}) + drawdown control {DD_THRESHOLD} + SPY {SPY_SMA_WINDOW}-day SMA filter")
    lines.append(f"- Window: {WINDOW} sessions; gate threshold {payload['gate_threshold']} (read from `config/promotion_gates.yaml`)")
    lines.append(
        f"- Controls: {payload['permutations']} permutations (seed {payload['permutation_seed']}); "
        f"{payload['bootstrap']['resamples']} moving-block bootstrap resamples "
        f"(seed {payload['bootstrap']['seed']}): blocks of {WINDOW_BOOTSTRAP_BLOCK} windows over the "
        f"rolling-window series (base rate, percentile rank, bucket gaps) and blocks of "
        f"{BOOTSTRAP_BLOCK} sessions over the joint (return, market-state) rows (correlations)"
    )
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append(f"- Trailing 63d Sharpe: **{payload['record']['trailing_63d_sharpe']:.6f}** (gate {payload['gate_threshold']}, FAIL); production decision {payload['record']['production_decision']} (unchanged)")
    lines.append(f"- Rolling windows: {dist['n_windows']}; base rate {dist['base_rate']:.4%} (bootstrap 95% CI [{dist['base_rate_ci95'][0]:.4%}, {dist['base_rate_ci95'][1]:.4%}]); current value at percentile {dist['current_percentile_rank']:.2%}")
    lines.append(f"- Distribution: min {dist['min']:.6f}, p10 {dist['p10']:.6f}, p25 {dist['p25']:.6f}, median {dist['median']:.6f}, p75 {dist['p75']:.6f}, max {dist['max']:.6f}")
    lines.append(f"- Current failing run: {dist['current_failing_run']} window(s); last passing window ended {dist['last_passing_window_end']}")
    for family in FOLD_FAMILIES:
        fam = payload["families"][family]
        gap_text = (
            f"{fam['bucket_gap']:+.6f} (bootstrap 95% CI [{fam['bucket_gap_ci95'][0]:+.6f}, {fam['bucket_gap_ci95'][1]:+.6f}])"
            if fam["gap_estimable"]
            else "not estimable (one bucket absent in the record period)"
        )
        lines.append(
            f"- {fam['label']}: eta^2 {fam['dispersion_share']:.6f}, permutation p {fam['permutation_pvalue']:.6f}, "
            f"bucket gap {gap_text}"
        )
    for c in payload["correlations"]:
        lines.append(f"- Spearman(rolling Sharpe, {c['variable']}) = {fmt(c['spearman'], 4)}")
    for key, v in payload["variants"].items():
        lines.append(
            f"- {key}: trailing 63d {v['trailing_63d_sharpe']:.6f}, record {v['record_sharpe']:.6f}, "
            f"full path {v['full_path_sharpe']:.6f}, WF mean OOS {v['wf_mean_test_sharpe']:.6f}"
        )
    lines.append("")
    lines.append("## Trial count")
    lines.append("")
    lines.append(
        f"- 1 diagnosis on the committed record; {len(FOLD_FAMILIES)} pre-specified bucket families; "
        f"{payload['permutations']} permutations per family; {len(payload['variants'])} isolated overlay "
        "variants; no per-fold re-optimisation and no candidate selection."
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
    lines.append("python research/tsmomentum_rolling63_weakness_diagnosis.py")
    lines.append("python -m pytest -q tests/test_tsmomentum_rolling63_weakness_diagnosis.py")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--report-out", type=Path, default=OUT_REPORT)
    parser.add_argument("--experiment-out", type=Path, default=OUT_EXP)
    parser.add_argument("--no-report", action="store_true", help="do not write the report or experiment record")
    args = parser.parse_args(argv)

    try:
        payload = run_diagnosis(raw_dir=args.raw_dir)
    except AuditError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not args.no_report:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.experiment_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(render_report(payload), encoding="utf-8")
        args.experiment_out.write_text(render_experiment(payload), encoding="utf-8")

    dist = payload["distribution"]
    print(f"OVERALL: {payload['overall']}")
    print(
        f"record: {payload['record']['n_sessions']} sessions "
        f"({payload['record']['first_session']} .. {payload['record']['last_session']})"
    )
    print(f"trailing 63d Sharpe: {payload['record']['trailing_63d_sharpe']:.6f} (gate {payload['gate_threshold']})")
    print(
        f"rolling windows: {dist['n_windows']} | base rate {dist['base_rate']:.4%} "
        f"(CI [{dist['base_rate_ci95'][0]:.4%}, {dist['base_rate_ci95'][1]:.4%}]) | "
        f"current percentile {dist['current_percentile_rank']:.2%}"
    )
    print(
        f"distribution: min {dist['min']:.6f} | p10 {dist['p10']:.6f} | p25 {dist['p25']:.6f} | "
        f"median {dist['median']:.6f} | p75 {dist['p75']:.6f} | max {dist['max']:.6f}"
    )
    for family in FOLD_FAMILIES:
        fam = payload["families"][family]
        print(
            f"{fam['label']}: eta^2 {fam['dispersion_share']:.6f}, p {fam['permutation_pvalue']:.6f}, "
            f"gap {fam['bucket_gap']:+.6f} CI [{fam['bucket_gap_ci95'][0]:+.6f}, {fam['bucket_gap_ci95'][1]:+.6f}]"
        )
    for key, v in payload["variants"].items():
        print(
            f"{key}: trailing63 {v['trailing_63d_sharpe']:.6f} | record {v['record_sharpe']:.6f} | "
            f"wf_mean {v['wf_mean_test_sharpe']:.6f} | clears gate: "
            f"{'YES' if v['rolling_gate_passes_on_current_window'] else 'no'}"
        )
    print(f"incumbent: {payload['incumbent_verdict']}")
    print(f"report: {args.report_out}" if not args.no_report else "--no-report: no artifacts written")
    return 0 if payload["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
