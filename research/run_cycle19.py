"""Cycle 19: Baseline Backtest & Walk-Forward for Macro Regime Overlay Extension (macroregime_001).

Pre-registered evaluation of the C5 candidate: the incumbent 226-day TSMOM +
combined vol-target (10%) + drawdown-control (15%) + SPY 200d SMA trend filter,
with an additional VIX-level regime exposure multiplier on top.

Baseline config (pre-specified):
  lookback=226, skip=21, top_fraction=0.5, vol_target=0.10, vol_lookback=63,
  dd_threshold=0.15, dd_reduction=0.5, spy_sma_window=200,
  vix_threshold=30, vix_exposure=0.5 (50% exposure when VIX > 30).

Robustness grid (pre-registered, 12 configs):
  vix_threshold in {20, 25, 30, 35} x vix_exposure in {0.0, 0.5, 1.0}
  The vix_exposure=1.0 arm is the incumbent CONTROL (no VIX gate).

Artifacts produced:
  - data/processed/simulation_macroregime_001.parquet
  - data/processed/trades_macroregime_001.parquet
  - data/processed/weights_macroregime_001.parquet
  - research/experiments/macroregime_baseline_wf_001.md
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
from src.evaluation.statistics import compute_dsr, compute_pbo, compute_psr
from src.evaluation.utils import fetch_close_prices
from src.evaluation.walkforward import (
    generate_walkforward_splits,
    summarize_walkforward,
)
from src.features.momentum import build_weights

warnings.filterwarnings("ignore", category=RuntimeWarning)

REPO_ROOT = Path(__file__).resolve().parent.parent

UNIVERSE = ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"]
REGIME = "^VIX"

START_DATE = "2004-11-18"
END_DATE = "2026-10-09"
TRAIN_END = "2009-12-31"
VAL_END = "2017-12-31"
TEST_START = "2018-01-01"

BASELINE = {
    "lookback": 226, "skip": 21, "top_fraction": 0.5,
    "vol_target": 0.10, "vol_lookback": 63,
    "dd_threshold": 0.15, "dd_reduction": 0.5,
    "spy_sma_window": 200,
    "vix_threshold": 30, "vix_exposure": 0.5,
}

VIX_THRESHOLDS = [20, 25, 30, 35]
VIX_EXPOSURES = [0.0, 0.5, 1.0]
N_GRID_CONFIGS = len(VIX_THRESHOLDS) * len(VIX_EXPOSURES)
N_PREREGISTERED_TRIALS = 12
assert N_GRID_CONFIGS == 12, (
    f"grid arithmetic: expected 12 unique configs (4 thresholds x 3 exposures), got {N_GRID_CONFIGS}"
)
assert N_PREREGISTERED_TRIALS == N_GRID_CONFIGS

WF_TRAIN_YEARS = 10.0
WF_TEST_MONTHS = 12.0
WF_STEP_MONTHS = 6.0
WF_PURGE_DAYS = 21
WF_EMBARGO_DAYS = 21

GATE_WF_SHARPE_MIN = 0.9
GATE_POSITIVE_FOLD_RATE_MIN = 0.5
GATE_POOLED_TRADES_MIN = 100

SEED = 42
N_BOOTSTRAP = 1000

COMMISSION_BPS, SLIPPAGE_BPS = get_cost_params()
TOTAL_COST = COMMISSION_BPS + SLIPPAGE_BPS
RF_ANNUAL = get_risk_free_rate()

SIM_PARQUET = REPO_ROOT / "data" / "processed" / "simulation_macroregime_001.parquet"
TRADES_PARQUET = REPO_ROOT / "data" / "processed" / "trades_macroregime_001.parquet"
WEIGHTS_PARQUET = REPO_ROOT / "data" / "processed" / "weights_macroregime_001.parquet"
REPORT_PATH = REPO_ROOT / "research" / "experiments" / "macroregime_baseline_wf_001.md"


def _git_hash() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=False, capture_output=True, text=True, cwd=REPO_ROOT,
        )
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def _config_hash() -> str:
    p = REPO_ROOT / "config" / "macroregime_candidate_001.yaml"
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


def _frame_hash(df: pd.DataFrame) -> str:
    return hashlib.sha256(
        pd.util.hash_pandas_object(df, index=True).values.tobytes()
    ).hexdigest()[:16]


def _fmt(x, nd: int = 4) -> str:
    if x is None:
        return "N/A"
    if isinstance(x, str):
        return x
    if isinstance(x, float) and not np.isfinite(x):
        return "N/A"
    return f"{x:.{nd}f}"


def _apply_monthly_schedule(weights: pd.DataFrame) -> pd.DataFrame:
    """Month-end calendar rebalancing (pre-registered execution schedule)."""
    is_month_end = pd.Series(weights.index.is_month_end, index=weights.index)
    return weights.where(is_month_end, axis=0).ffill().fillna(0.0)


def _net_returns(
    close: pd.DataFrame,
    weights: pd.DataFrame,
) -> tuple[pd.Series, pd.DataFrame, pd.Series, pd.Series]:
    """Return (net_ret, weights, gross_ret, turnover) for scheduled weights."""
    common = close.index.intersection(weights.index)
    close_a = close.loc[common]
    weights_a = weights.loc[common]
    daily_ret = close_a.pct_change().fillna(0.0)
    gross_ret = (weights_a * daily_ret).sum(axis=1)
    turnover = weights_a.diff().abs().sum(axis=1)
    net_ret = gross_ret - turnover * TOTAL_COST
    return net_ret, weights_a, gross_ret, turnover


def _incumbent_overlay(
    gated: pd.DataFrame,
    asset_ret: pd.DataFrame,
) -> pd.DataFrame:
    """Combined vol-targeting (10%) + drawdown control (15%).

    Replicates Cycle 6's overlay: vol-scale on the regime-gated weights,
    then drawdown scale on the vol-targeted portfolio.
    """
    port_ret = (gated * asset_ret).sum(axis=1)
    realized_vol = port_ret.rolling(BASELINE["vol_lookback"]).std() * np.sqrt(252)
    realized_vol = realized_vol.replace(0, np.nan)
    vol_scale = (BASELINE["vol_target"] / realized_vol).clip(upper=1.0).fillna(0.0)
    vol_targeted = gated.mul(vol_scale, axis=0)

    vol_port_ret = (vol_targeted * asset_ret).sum(axis=1)
    cum = (1 + vol_port_ret).cumprod()
    running_max = cum.expanding().max()
    drawdown = (cum / running_max) - 1
    dd_scale = pd.Series(1.0, index=gated.index)
    dd_scale[drawdown < -BASELINE["dd_threshold"]] = BASELINE["dd_reduction"]

    return gated.mul(vol_scale * dd_scale, axis=0)


def build_overlay_weights(
    close: pd.DataFrame,
    vix: pd.Series,
    lookback: int,
    skip: int,
    top_fraction: float,
    vix_threshold: float,
    vix_exposure: float,
    spy_sma_window: int = 200,
) -> pd.DataFrame:
    """Compute regime-gated weights for one configuration.

    Pipeline: base momentum weights -> SPY trend gate -> VIX regime gate ->
    vol+dd overlay -> monthly schedule.
    """
    weights = build_weights(close, lookback=lookback, skip=skip, top_fraction=top_fraction)
    common = close.index.intersection(weights.index)
    close_a = close.loc[common]
    weights_a = weights.loc[common]
    daily_ret = close_a.pct_change().fillna(0.0)

    # SPY trend gate (incumbent): 0% exposure when SPY < 200-day SMA
    spy = close_a["SPY"]
    spy_sma = spy.rolling(spy_sma_window).mean()
    exposure = pd.Series(1.0, index=close_a.index)
    exposure[spy < spy_sma] = 0.0
    exposure[spy.isna() | spy_sma.isna()] = 0.0
    gated = weights_a.mul(exposure, axis=0)

    # VIX regime gate (C5 extension): use PRIOR day's VIX close (point-in-time)
    vix_lag = vix.shift(1).reindex(close_a.index)
    vix_exposure_mult = pd.Series(1.0, index=close_a.index)
    vix_exposure_mult[vix_lag > vix_threshold] = vix_exposure
    vix_exposure_mult[vix_lag.isna()] = 1.0
    gated = gated.mul(vix_exposure_mult, axis=0)

    # Combined vol+dd overlay
    combined = _incumbent_overlay(gated, daily_ret)
    weights_out = _apply_monthly_schedule(combined)
    return weights_out


def eval_config(
    close: pd.DataFrame,
    vix: pd.Series,
    lookback: int,
    skip: int,
    top_fraction: float,
    vix_threshold: float,
    vix_exposure: float,
) -> dict:
    """Evaluate one VIX-gate configuration on the pre-registered splits."""
    weights = build_overlay_weights(
        close, vix, lookback, skip, top_fraction,
        vix_threshold, vix_exposure,
    )
    net_ret, weights_a, gross_ret, turnover = _net_returns(close, weights)

    train_end_dt = pd.Timestamp(TRAIN_END, tz="UTC")
    val_end_dt = pd.Timestamp(VAL_END, tz="UTC")
    tr_m = net_ret.index <= train_end_dt
    va_m = (net_ret.index > train_end_dt) & (net_ret.index <= val_end_dt)
    te_m = net_ret.index > val_end_dt

    def _metrics(r: pd.Series, w: pd.DataFrame) -> dict:
        if len(r) == 0:
            return {}
        return compute_metrics(r, w, COMMISSION_BPS, SLIPPAGE_BPS, RF_ANNUAL)

    tr_metrics = _metrics(net_ret[tr_m], weights_a[tr_m])
    va_metrics = _metrics(net_ret[va_m], weights_a[va_m])
    te_metrics = _metrics(net_ret[te_m], weights_a[te_m])

    return {
        "net_ret": net_ret,
        "weights": weights_a,
        "gross_ret": gross_ret,
        "turnover": turnover,
        "train": tr_metrics,
        "validation": va_metrics,
        "test": te_metrics,
        "train_sharpe": tr_metrics.get("sharpe_ratio", np.nan),
        "val_sharpe": va_metrics.get("sharpe_ratio", np.nan),
        "test_sharpe": te_metrics.get("sharpe_ratio", np.nan),
        "test_ann_return": te_metrics.get("annualized_return", np.nan),
        "test_max_dd": te_metrics.get("max_drawdown", np.nan),
        "test_trades": te_metrics.get("trade_count", 0),
        "test_turnover": te_metrics.get("annualized_turnover", np.nan),
        "test_sortino": te_metrics.get("sortino_ratio", np.nan),
        "test_profit_factor": te_metrics.get("profit_factor", np.nan),
    }


def eval_config_period(
    close: pd.DataFrame,
    vix: pd.Series,
    vix_threshold: float,
    vix_exposure: float,
    start_date: str,
    end_date: str,
) -> tuple[pd.Series, pd.DataFrame]:
    """Evaluate the baseline config on an arbitrary period (WF folds)."""
    weights = build_overlay_weights(
        close, vix, BASELINE["lookback"], BASELINE["skip"],
        BASELINE["top_fraction"], vix_threshold, vix_exposure,
    )
    net_ret, weights_a, _, _ = _net_returns(close, weights)
    mask = (net_ret.index >= start_date) & (net_ret.index <= end_date)
    return net_ret[mask], weights_a[mask]


def eval_equal_weight(
    close: pd.DataFrame,
    start_date: str,
    end_date: str,
) -> tuple[pd.Series, pd.DataFrame]:
    """1/N equal-weight portfolio over the 7-ETF universe."""
    weights = pd.DataFrame(1.0 / close.shape[1], index=close.index, columns=close.columns)
    weights = weights.shift(1).fillna(0.0)
    weights = _apply_monthly_schedule(weights)
    net_ret, weights_a, _, _ = _net_returns(close, weights)
    mask = (net_ret.index >= start_date) & (net_ret.index <= end_date)
    return net_ret[mask], weights_a[mask]


def _tail_metrics(net_ret: pd.Series) -> dict:
    clean = net_ret.dropna()
    if clean.empty:
        return {"var_95_daily": np.nan, "cvar_95_daily": np.nan, "worst_day": np.nan}
    var_95 = float(np.percentile(clean, 5))
    tail = clean[clean <= var_95]
    cvar_95 = float(-tail.mean()) if len(tail) > 0 else 0.0
    return {
        "var_95_daily": float(-var_95),
        "cvar_95_daily": cvar_95,
        "worst_day": float(clean.min()),
    }


def _build_trade_log(weights: pd.DataFrame, close: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "trade_id", "date", "symbol", "side",
        "weight_before", "weight_after", "weight_change", "price", "cost",
    ]
    changes = weights.diff()
    stacked = changes.stack()
    nonzero = stacked[stacked.abs() > 0]
    if nonzero.empty:
        return pd.DataFrame(columns=columns)

    before = weights.shift(1).stack().reindex(nonzero.index)
    after = weights.stack().reindex(nonzero.index)
    prices = close.stack().reindex(nonzero.index)

    trade_log = pd.DataFrame(
        {
            "weight_before": before.to_numpy(),
            "weight_after": after.to_numpy(),
            "weight_change": nonzero.to_numpy(),
            "price": prices.to_numpy(),
        },
        index=nonzero.index,
    )
    trade_log["side"] = np.where(
        trade_log["weight_change"] > 0, "buy", "sell"
    )
    trade_log["cost"] = trade_log["weight_change"].abs() * TOTAL_COST
    trade_log = trade_log.reset_index()
    trade_log.columns = ["date", "symbol"] + list(trade_log.columns[2:])
    trade_log.insert(0, "trade_id", np.arange(1, len(trade_log) + 1))
    return trade_log[columns]


# ---------------------------------------------------------------------------
# Section 1: Baseline backtest (test period)
# ---------------------------------------------------------------------------
def run_baseline(close: pd.DataFrame, vix: pd.Series) -> dict:
    print("\n=== [1] Baseline Backtest (226, 21, 0.5; VIX gate 30/0.5) ===")
    res = eval_config(
        close, vix,
        BASELINE["lookback"], BASELINE["skip"], BASELINE["top_fraction"],
        BASELINE["vix_threshold"], BASELINE["vix_exposure"],
    )
    net_ret = res["net_ret"]
    weights = res["weights"]

    test_mask = net_ret.index >= pd.Timestamp(TEST_START, tz="UTC")
    test_ret = net_ret[test_mask]
    test_w = weights[test_mask]

    daily = pd.DataFrame(index=weights.index)
    daily["net_return"] = net_ret
    daily["gross_return"] = res["gross_ret"]
    daily["cost"] = res["turnover"] * TOTAL_COST
    daily["turnover"] = res["turnover"]
    daily["exposure"] = weights.abs().sum(axis=1)
    daily["n_long"] = (weights > 0).sum(axis=1)
    cum_net = (1 + net_ret).cumprod()
    daily["drawdown"] = (cum_net / cum_net.expanding().max()) - 1.0
    for symbol in weights.columns:
        daily[f"weight_{symbol}"] = weights[symbol].to_numpy()

    SIM_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    daily.to_parquet(SIM_PARQUET)
    print(f"  Daily series -> {SIM_PARQUET} ({len(daily):,} rows)")

    trades_df = _build_trade_log(weights, close.loc[weights.index])
    trades_df.to_parquet(TRADES_PARQUET)
    print(f"  Trade log -> {TRADES_PARQUET} ({len(trades_df):,} trades)")

    weights.to_parquet(WEIGHTS_PARQUET)
    print(f"  Weights -> {WEIGHTS_PARQUET} ({len(weights):,} rows)")

    test_metrics = compute_metrics(
        test_ret, test_w, COMMISSION_BPS, SLIPPAGE_BPS, RF_ANNUAL
    )
    tail = _tail_metrics(test_ret)
    print(f"  Test Sharpe: {test_metrics.get('sharpe_ratio', np.nan):.4f} | "
          f"AnnRet: {test_metrics.get('annualized_return', np.nan):.2%} | "
          f"MaxDD: {test_metrics.get('max_drawdown', np.nan):.2%} | "
          f"Trades: {test_metrics.get('trade_count', 0)}")

    return {
        "res": res,
        "test_ret": test_ret,
        "test_start": TEST_START,
        "test_end": END_DATE,
    }


# ---------------------------------------------------------------------------
# Section 2: Walk-forward evaluation (fixed parameters, no re-optimization)
# ---------------------------------------------------------------------------
def run_walkforward(close: pd.DataFrame, vix: pd.Series, splits: list[dict]) -> dict:
    print("\n=== [2] Walk-Forward Evaluation (baseline VIX gate, fixed params) ===")
    print(f"  Folds: {len(splits)}")

    rows = []
    for i, sp in enumerate(splits):
        print(f"  Fold {i+1}/{len(splits)}: train {sp['train_start']}->{sp['train_end']}, "
              f"test {sp['test_start']}->{sp['test_end']}")
        try:
            train_ret, train_w = eval_config_period(
                close, vix,
                BASELINE["vix_threshold"], BASELINE["vix_exposure"],
                sp["train_start"], sp["train_end"],
            )
            test_ret, test_w = eval_config_period(
                close, vix,
                BASELINE["vix_threshold"], BASELINE["vix_exposure"],
                sp["test_start"], sp["test_end"],
            )
            train_m = compute_metrics(train_ret, train_w, COMMISSION_BPS, SLIPPAGE_BPS, RF_ANNUAL)
            test_m = compute_metrics(test_ret, test_w, COMMISSION_BPS, SLIPPAGE_BPS, RF_ANNUAL)
            rows.append({
                "fold": i + 1,
                "train_start": sp["train_start"],
                "train_end": sp["train_end"],
                "test_start": sp["test_start"],
                "test_end": sp["test_end"],
                "train_sharpe": train_m.get("sharpe_ratio", np.nan),
                "train_ann_return": train_m.get("annualized_return", np.nan),
                "test_sharpe": test_m.get("sharpe_ratio", np.nan),
                "test_ann_return": test_m.get("annualized_return", np.nan),
                "test_max_dd": test_m.get("max_drawdown", np.nan),
                "test_turnover": test_m.get("annualized_turnover", np.nan),
                "test_trades": test_m.get("trade_count", np.nan),
                "test_profit_factor": test_m.get("profit_factor", np.nan),
                "test_sortino": test_m.get("sortino_ratio", np.nan),
            })
        except Exception as exc:  # noqa: BLE001 - walk-forward continues past per-fold failures
            print(f"    ERROR: {exc}")
            rows.append({
                "fold": i + 1,
                "train_start": sp["train_start"],
                "train_end": sp["train_end"],
                "test_start": sp["test_start"],
                "test_end": sp["test_end"],
                "train_sharpe": np.nan,
                "train_ann_return": np.nan,
                "test_sharpe": np.nan,
                "test_ann_return": np.nan,
                "test_max_dd": np.nan,
                "test_turnover": np.nan,
                "test_trades": np.nan,
                "test_profit_factor": np.nan,
                "test_sortino": np.nan,
            })

    df = pd.DataFrame(rows)
    summary = summarize_walkforward(df)
    return {"fold_df": df, "summary": summary}
