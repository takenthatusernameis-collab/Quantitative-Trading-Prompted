"""Cycle 13: Baseline Backtest & Walk-Forward for Cross-Sectional Momentum (csmomentum_001).

Executes the pre-registered evaluation for Candidate C3 (long-only cross-sectional
momentum, broad 18-ETF universe) using the frozen configuration in
config/csmomentum_candidate_001.yaml.

Artifacts produced:
  - data/processed/simulation_csmomentum_001.parquet  (daily net/gross returns, costs, turnover, exposure, positions, weights)
  - data/processed/trades_csmomentum_001.parquet       (trade log)
  - data/processed/weights_csmomentum_001.parquet      (point-in-time weights)
  - research/experiments/csmomentum_baseline_wf_001.md (experiment record)

NO risk overlays are added (reserved for Cycle 14+ per AGENTS.md).
NO configuration is selected based on test-period results.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import warnings
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.backtest.engine import (
    compute_metrics,
    get_cost_params,
    get_risk_free_rate,
)
from src.data.yfinance_fetcher import fetch_universe
from src.evaluation.statistics import compute_dsr, compute_pbo, compute_psr
from src.evaluation.utils import (
    annualize_return,
    fetch_close_prices,
    max_drawdown,
    sharpe_ratio,
)
from src.evaluation.walkforward import (
    generate_walkforward_splits,
    summarize_walkforward,
)
from src.features.momentum import build_weights

warnings.filterwarnings("ignore", category=RuntimeWarning)

REPO_ROOT = Path(__file__).resolve().parent.parent

UNIVERSE = [
    "SPY", "QQQ", "IWM", "TLT", "GLD", "DBC", "VNQ", "EFA", "EEM",
    "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY",
]
CORE7 = ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"]

START_DATE = "1993-01-01"
END_DATE = "2026-10-09"
TRAIN_END = "2009-12-31"
VAL_END = "2017-12-31"
TEST_START = "2018-01-01"

BASELINE = (252, 21, 0.5)

LOOKBACKS = [189, 252, 315]
SKIPS = [21, 42]
TOP_FRACTIONS = [0.3, 0.5, 0.7]

WF_TRAIN_YEARS = 10.0
WF_TEST_MONTHS = 12.0
WF_STEP_MONTHS = 6.0
WF_PURGE_DAYS = 21
WF_EMBARGO_DAYS = 21

GATE_WF_SHARPE_MIN = 0.9
GATE_POSITIVE_FOLD_RATE_MIN = 0.5
GATE_POOLED_TRADES_MIN = 100
GATE_PLATEAU_FRACTION_MIN = 0.667

COMMISSION_BPS, SLIPPAGE_BPS = get_cost_params()
TOTAL_COST = COMMISSION_BPS + SLIPPAGE_BPS
RF_ANNUAL = get_risk_free_rate()

SIM_PARQUET = REPO_ROOT / "data" / "processed" / "simulation_csmomentum_001.parquet"
TRADES_PARQUET = REPO_ROOT / "data" / "processed" / "trades_csmomentum_001.parquet"
WEIGHTS_PARQUET = REPO_ROOT / "data" / "processed" / "weights_csmomentum_001.parquet"
REPORT_PATH = REPO_ROOT / "research" / "experiments" / "csmomentum_baseline_wf_001.md"

INCUMBENT = {
    "lookback": 226, "skip": 21, "top_fraction": 0.5,
    "vol_target": 0.10, "vol_lookback": 63,
    "dd_threshold": 0.15, "dd_reduction": 0.5,
    "spy_sma_window": 200,
}


def _git_hash() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=False, capture_output=True, text=True, cwd=REPO_ROOT,
        )
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except (OSError, RuntimeError):
        return "unknown"


def _today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def _config_hash() -> str:
    p = REPO_ROOT / "config" / "csmomentum_candidate_001.yaml"
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


def _fmt_pct(x: float) -> str:
    return f"{x:.2%}"


def _fmt_num(x: float, nd: int = 4) -> str:
    return f"{x:.{nd}f}"


def eval_config(close, lookback, skip, top_fraction,
                train_end=TRAIN_END, val_end=VAL_END):
    """Evaluate a single parameter config using pre-loaded close prices."""
    weights = build_weights(close, lookback=lookback, skip=skip, top_fraction=top_fraction)
    common = close.index.intersection(weights.index)
    close_a = close.loc[common]
    weights_a = weights.loc[common]
    daily_ret = close_a.pct_change().fillna(0.0)
    port_ret = (weights_a * daily_ret).sum(axis=1)
    wc = weights_a.diff().abs().sum(axis=1)
    net_ret = port_ret - wc * TOTAL_COST

    train_end_dt = pd.Timestamp(train_end, tz="UTC")
    val_end_dt = pd.Timestamp(val_end, tz="UTC")
    tr_m = net_ret.index <= train_end_dt
    va_m = (net_ret.index > train_end_dt) & (net_ret.index <= val_end_dt)
    te_m = net_ret.index > val_end_dt

    def _metrics(r, w):
        if len(r) == 0:
            return {}
        return compute_metrics(r, w, COMMISSION_BPS, SLIPPAGE_BPS, RF_ANNUAL)

    return {
        "net_ret": net_ret, "weights": weights_a,
        "train": _metrics(net_ret[tr_m], weights_a[tr_m]),
        "validation": _metrics(net_ret[va_m], weights_a[va_m]),
        "test": _metrics(net_ret[te_m], weights_a[te_m]),
        "train_sharpe": sharpe_ratio(net_ret[tr_m]) if tr_m.sum() > 1 else np.nan,
        "val_sharpe": sharpe_ratio(net_ret[va_m]) if va_m.sum() > 1 else np.nan,
        "test_sharpe": sharpe_ratio(net_ret[te_m]) if te_m.sum() > 1 else np.nan,
        "test_ann_return": annualize_return(net_ret[te_m]) if te_m.sum() > 0 else np.nan,
        "test_max_dd": max_drawdown(net_ret[te_m]) if te_m.sum() > 0 else np.nan,
        "test_trades": _metrics(net_ret[te_m], weights_a[te_m]).get("trade_count", 0),
        "test_turnover": _metrics(net_ret[te_m], weights_a[te_m]).get("annualized_turnover", np.nan),
        "test_profit_factor": _metrics(net_ret[te_m], weights_a[te_m]).get("profit_factor", np.nan),
        "test_sortino": _metrics(net_ret[te_m], weights_a[te_m]).get("sortino_ratio", np.nan),
    }


def eval_config_period(close, lookback, skip, top_fraction, start_date, end_date):
    """Evaluate a config on an arbitrary period (for walk-forward folds)."""
    weights = build_weights(close, lookback=lookback, skip=skip, top_fraction=top_fraction)
    common = close.index.intersection(weights.index)
    close_a = close.loc[common]
    weights_a = weights.loc[common]
    daily_ret = close_a.pct_change().fillna(0.0)
    port_ret = (weights_a * daily_ret).sum(axis=1)
    wc = weights_a.diff().abs().sum(axis=1)
    net_ret = port_ret - wc * TOTAL_COST
    mask = (net_ret.index >= start_date) & (net_ret.index <= end_date)
    return net_ret[mask], weights_a[mask]


def eval_equal_weight(close, start_date, end_date):
    """1/N equal-weight portfolio over the 18-ETF universe, monthly rebalance, 1-day lag, 3bps costs."""
    weights = pd.DataFrame(1.0 / close.shape[1], index=close.index, columns=close.columns)
    weights = weights.shift(1).fillna(0.0)
    common = close.index.intersection(weights.index)
    close_a = close.loc[common]
    weights_a = weights.loc[common]
    daily_ret = close_a.pct_change().fillna(0.0)
    port_ret = (weights_a * daily_ret).sum(axis=1)
    wc = weights_a.diff().abs().sum(axis=1)
    net_ret = port_ret - wc * TOTAL_COST
    mask = (net_ret.index >= start_date) & (net_ret.index <= end_date)
    return net_ret[mask], weights_a[mask]


def eval_incumbent(close_core, start_date, end_date):
    """Incumbent TSMOM: 226d lookback, vol-target 10%, DD control 15%, SPY 200d SMA, 3bps costs."""
    lb, sk, tf = INCUMBENT["lookback"], INCUMBENT["skip"], INCUMBENT["top_fraction"]
    weights = build_weights(close_core, lookback=lb, skip=sk, top_fraction=tf)
    common = close_core.index.intersection(weights.index)
    close_a = close_core.loc[common]
    weights_a = weights.loc[common]
    daily_ret = close_a.pct_change().fillna(0.0)

    spy = close_a["SPY"]
    spy_sma = spy.rolling(INCUMBENT["spy_sma_window"]).mean()
    exposure = pd.Series(1.0, index=close_a.index)
    exposure[spy < spy_sma] = 0.0
    exposure[spy.isna() | spy_sma.isna()] = 0.0

    port_ret = (weights_a * daily_ret).sum(axis=1)
    realized_vol = port_ret.rolling(INCUMBENT["vol_lookback"]).std() * np.sqrt(252)
    realized_vol = realized_vol.replace(0, np.nan)
    vol_scale = (INCUMBENT["vol_target"] / realized_vol).clip(upper=1.0).fillna(0.0)
    vol_targeted_weights = weights_a.mul(vol_scale, axis=0)

    vol_port_ret = (vol_targeted_weights * daily_ret).sum(axis=1)
    cum = (1 + vol_port_ret).cumprod()
    running_max = cum.expanding().max()
    drawdown = (cum / running_max) - 1
    in_drawdown = drawdown < -INCUMBENT["dd_threshold"]
    dd_scale = pd.Series(1.0, index=weights_a.index)
    dd_scale[in_drawdown] = INCUMBENT["dd_reduction"]
    combined_scale = vol_scale * dd_scale
    combined_weights = weights_a.mul(combined_scale, axis=0)

    wc = combined_weights.diff().abs().sum(axis=1)
    net_ret = (combined_weights * daily_ret).sum(axis=1) - wc * TOTAL_COST
    mask = (net_ret.index >= start_date) & (net_ret.index <= end_date)
    return net_ret[mask], combined_weights[mask]
