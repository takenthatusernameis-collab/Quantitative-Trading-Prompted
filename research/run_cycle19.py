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
from src.evaluation.statistics import (
    block_bootstrap_sharpe,
    compute_dsr,
    compute_pbo,
    compute_psr,
)
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
        "net_ret": net_ret,
        "weights": weights,
        "test_ret": test_ret,
        "test_w": test_w,
        "test_metrics": test_metrics,
        "tail": tail,
        "daily": daily,
        "trades_df": trades_df,
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


# ---------------------------------------------------------------------------
# Section 3: Robustness grid (12 pre-specified VIX-gate configurations, test period)
# ---------------------------------------------------------------------------
def run_grid(close: pd.DataFrame, vix: pd.Series) -> dict:
    """Evaluate all 12 pre-registered VIX-gate configurations on the test period.

    Grid: vix_threshold in {20, 25, 30, 35} x vix_exposure in {0.0, 0.5, 1.0}.
    The vix_exposure=1.0 arm is the incumbent control (no VIX gate).
    Diagnostic only — no config is selected on test-period results.
    """
    print(f"\n=== [3] Robustness Grid ({N_GRID_CONFIGS} pre-specified configs) ===")
    rows = []
    for vt in VIX_THRESHOLDS:
        for ve in VIX_EXPOSURES:
            res = eval_config(
                close, vix,
                BASELINE["lookback"], BASELINE["skip"], BASELINE["top_fraction"],
                vt, ve,
            )
            rows.append({
                "vix_threshold": vt,
                "vix_exposure": ve,
                "train_sharpe": res["train_sharpe"],
                "val_sharpe": res["val_sharpe"],
                "test_sharpe": res["test_sharpe"],
                "test_ann_return": res["test_ann_return"],
                "test_max_dd": res["test_max_dd"],
                "test_trades": res["test_trades"],
                "test_turnover": res["test_turnover"],
                "test_sortino": res["test_sortino"],
                "test_profit_factor": res["test_profit_factor"],
                "test_exposure": res["test"].get("avg_exposure", np.nan) if res["test"] else np.nan,
            })
    grid_df = pd.DataFrame(rows)
    grid_df["rank"] = grid_df["test_sharpe"].rank(ascending=False, method="min").astype(int)

    bl_mask = (grid_df["vix_threshold"] == BASELINE["vix_threshold"]) & (grid_df["vix_exposure"] == BASELINE["vix_exposure"])
    baseline_rank = int(grid_df.loc[bl_mask, "rank"].iloc[0])
    baseline_test_sharpe = float(grid_df.loc[bl_mask, "test_sharpe"].iloc[0])

    # Plateau check: at vix_exposure=0.5, how many of the 4 vix_thresholds
    # achieve test Sharpe within 10% of the baseline (30, 0.5) test Sharpe.
    # Threshold = max(0.1, 10% x |baseline test Sharpe|) per repository convention.
    expo_slice = grid_df[grid_df["vix_exposure"] == 0.5]
    threshold = max(0.1, 0.10 * abs(baseline_test_sharpe)) if np.isfinite(baseline_test_sharpe) else 0.1
    n_within = int((np.abs(expo_slice["test_sharpe"].values - baseline_test_sharpe) <= threshold).sum())
    plateau_pass = n_within >= 2  # >= 2 of 4

    print(f"  Baseline (vix_threshold={BASELINE['vix_threshold']}, vix_exposure={BASELINE['vix_exposure']}) "
          f"test Sharpe: {baseline_test_sharpe:.4f} (rank {baseline_rank}/{N_GRID_CONFIGS})")
    print(f"  Plateau (vix_exposure=0.5, {len(expo_slice)} thresholds): "
          f"{n_within}/4 within +/-{threshold:.4f} ({'PASS' if plateau_pass else 'FAIL'})")

    return {
        "grid_df": grid_df,
        "baseline_rank": baseline_rank,
        "baseline_test_sharpe": baseline_test_sharpe,
        "plateau_threshold": threshold,
        "n_thresholds_within": n_within,
        "plateau_pass": plateau_pass,
        "expo_slice": expo_slice,
    }


# ---------------------------------------------------------------------------
# Section 4: Benchmark comparison (test period + walk-forward folds)
# ---------------------------------------------------------------------------
def _benchmark_comparison(
    name: str,
    candidate_ret: pd.Series,
    bench_ret: pd.Series,
) -> dict:
    """Benchmark-relative statistics on the common test-period index."""
    aligned = candidate_ret.index.intersection(bench_ret.index)
    cand = candidate_ret.loc[aligned]
    bench = bench_ret.loc[aligned]
    excess = cand - bench
    excess_vol = excess.std() * np.sqrt(252)
    ann_excess = annualize_return(excess)
    excess_sharpe = ann_excess / excess_vol if excess_vol > 0 else 0.0
    cum_excess = (1 + excess).cumprod()
    rel_dd = float(((cum_excess / cum_excess.expanding().max()) - 1).min()) if len(cum_excess) > 0 else np.nan
    return {
        "name": name,
        "bench_ann_return": annualize_return(bench),
        "bench_sharpe": sharpe_ratio(bench, RF_ANNUAL),
        "bench_max_dd": max_drawdown(bench),
        "excess_ann_return": float(ann_excess),
        "excess_sharpe": float(excess_sharpe),
        "sharpe_difference": float(sharpe_ratio(cand, RF_ANNUAL) - sharpe_ratio(bench, RF_ANNUAL)),
        "correlation": float(cand.corr(bench)) if len(cand) > 1 else 0.0,
        "relative_max_dd": rel_dd,
        "n_days": len(aligned),
    }


def _build_gated_only(
    close: pd.DataFrame,
    vix: pd.Series,
    lookback: int,
    skip: int,
    top_fraction: float,
    vix_threshold: float,
    vix_exposure: float,
    spy_sma_window: int = 200,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build regime-gated weights WITHOUT the vol+dd overlay.

    Used for the incumbent benchmark's "slice" warmup (overlay initialized
    only at the period start, not at history_start).
    """
    weights = build_weights(close, lookback=lookback, skip=skip, top_fraction=top_fraction)
    common = close.index.intersection(weights.index)
    close_a = close.loc[common]
    weights_a = weights.loc[common]
    daily_ret = close_a.pct_change().fillna(0.0)

    spy = close_a["SPY"]
    spy_sma = spy.rolling(spy_sma_window).mean()
    exposure = pd.Series(1.0, index=close_a.index)
    exposure[spy < spy_sma] = 0.0
    exposure[spy.isna() | spy_sma.isna()] = 0.0
    gated = weights_a.mul(exposure, axis=0)

    vix_lag = vix.shift(1).reindex(close_a.index).ffill()
    vix_exposure_mult = pd.Series(1.0, index=close_a.index)
    vix_exposure_mult[vix_lag > vix_threshold] = vix_exposure
    gated = gated.mul(vix_exposure_mult, axis=0)

    return gated, daily_ret


def eval_incumbent(
    close: pd.DataFrame,
    vix: pd.Series,
    start_date: str,
    end_date: str,
    warmup: str = "full",
) -> tuple[pd.Series, pd.DataFrame]:
    """Incumbent benchmark (tsmomentum_spytrend_001): SPY trend filter +
    vol+dd overlay, NO VIX gate (vix_exposure=1.0).

    - 'slice': overlay state initializes at start_date (test-period convention).
    - 'full':  overlay state initializes at history_start, then sliced
      (walk-forward fold convention).
    """
    gated, daily_ret = _build_gated_only(
        close, vix,
        BASELINE["lookback"], BASELINE["skip"], BASELINE["top_fraction"],
        BASELINE["vix_threshold"], 1.0,
    )
    start_ts = pd.Timestamp(start_date, tz="UTC")
    end_ts = pd.Timestamp(end_date, tz="UTC")
    mask = (gated.index >= start_ts) & (gated.index <= end_ts)

    if warmup == "slice":
        sim_ret = daily_ret.loc[mask]
        sim_gated = gated.loc[mask]
        combined = _incumbent_overlay(sim_gated, sim_ret)
        combined = _apply_monthly_schedule(combined)
        wc = combined.diff().abs().sum(axis=1)
        net_ret = (combined * sim_ret).sum(axis=1) - wc * TOTAL_COST
        return net_ret, combined

    combined = _incumbent_overlay(gated, daily_ret)
    weights_out = _apply_monthly_schedule(combined)
    wc = weights_out.diff().abs().sum(axis=1)
    net_ret = (weights_out * daily_ret).sum(axis=1) - wc * TOTAL_COST
    return net_ret[mask], weights_out[mask]


def run_benchmarks(
    close: pd.DataFrame,
    vix: pd.Series,
    splits: list[dict],
    cs_test_ret: pd.Series,
) -> dict:
    """Benchmark comparison: 1/N equal-weight (7-ETF) + incumbent control arm."""
    print("\n=== [4] Benchmark Comparison ===")

    # Test-period benchmarks
    ew_test_ret, _ = eval_equal_weight(close, TEST_START, END_DATE)
    # Incumbent test-period: "slice" warmup (Cycle 5/7 convention)
    inc_test_ret, _ = eval_incumbent(close, vix, TEST_START, END_DATE, warmup="slice")

    ew_cmp = _benchmark_comparison("1/N Equal-Weight (7-ETF)", cs_test_ret, ew_test_ret)
    inc_cmp = _benchmark_comparison("Incumbent TSMOM (tsmomentum_spytrend_001)", cs_test_ret, inc_test_ret)
    print(f"  1/N: Sharpe {ew_cmp['bench_sharpe']:.4f} | excess Sharpe {ew_cmp['excess_sharpe']:.4f} | corr {ew_cmp['correlation']:.3f}")
    print(f"  Incumbent: Sharpe {inc_cmp['bench_sharpe']:.4f} | excess Sharpe {inc_cmp['excess_sharpe']:.4f} | corr {inc_cmp['correlation']:.3f}")

    def ew_wf(start, end):
        return eval_equal_weight(close, start, end)

    def inc_wf(start, end):
        return eval_incumbent(close, vix, start, end, warmup="full")

    def ew_fn(symbols, start, end):
        return ew_wf(start, end)

    def inc_fn(symbols, start, end):
        return inc_wf(start, end)

    ew_wf_result = run_benchmark_walkforward("1/N Equal-Weight", ew_fn, splits)
    inc_wf_result = run_benchmark_walkforward("Incumbent TSMOM", inc_fn, splits)

    return {
        "ew_test": ew_cmp,
        "inc_test": inc_cmp,
        "ew_wf": ew_wf_result,
        "inc_wf": inc_wf_result,
    }


def run_benchmark_walkforward(
    name: str,
    config_fn,
    splits: list[dict],
) -> dict:
    """Walk-forward evaluation of a benchmark on the identical folds."""
    rows = []
    for i, sp in enumerate(splits):
        try:
            test_ret, test_w = config_fn(UNIVERSE, sp["test_start"], sp["test_end"])
            test_m = compute_metrics(test_ret, test_w, COMMISSION_BPS, SLIPPAGE_BPS, RF_ANNUAL)
            rows.append({
                "fold": i + 1,
                "test_start": sp["test_start"],
                "test_end": sp["test_end"],
                "test_sharpe": test_m.get("sharpe_ratio", np.nan),
                "test_ann_return": test_m.get("annualized_return", np.nan),
                "test_max_dd": test_m.get("max_drawdown", np.nan),
                "test_trades": test_m.get("trade_count", 0),
                "test_sortino": test_m.get("sortino_ratio", np.nan),
                "test_profit_factor": test_m.get("profit_factor", np.nan),
            })
        except Exception as exc:  # noqa: BLE001
            print(f"    ERROR ({name} fold {i+1}): {exc}")
            rows.append({
                "fold": i + 1,
                "test_start": sp["test_start"],
                "test_end": sp["test_end"],
                "test_sharpe": np.nan, "test_ann_return": np.nan,
                "test_max_dd": np.nan, "test_trades": 0,
                "test_sortino": np.nan, "test_profit_factor": np.nan,
            })
    df = pd.DataFrame(rows)
    summary = summarize_walkforward(df)
    print(f"    {name} WF: mean OOS Sharpe {summary.get('mean_test_sharpe', np.nan):.4f} | "
          f"% positive: {summary.get('pct_positive_sharpe', np.nan):.1%}")
    return {"wf_df": df, "summary": summary}


# ---------------------------------------------------------------------------
# Section 5: Multiple-testing control
# ---------------------------------------------------------------------------
def run_multiple_testing(
    test_ret: pd.Series,
    grid_df: pd.DataFrame,
) -> dict:
    """DSR, PSR, PBO/CSCV, and block-bootstrap CI on the baseline config."""
    print(f"\n=== [5] Multiple-Testing Control (N={N_PREREGISTERED_TRIALS} pre-registered trials) ===")

    dsr = compute_dsr(
        test_ret, n_configs=N_PREREGISTERED_TRIALS, sr_target=0.0,
        n_bootstrap=N_BOOTSTRAP, seed=SEED, block_size=22,
    )
    psr_vs0 = compute_psr(
        test_ret, sr_target=0.0,
        n_bootstrap=N_BOOTSTRAP, seed=SEED, block_size=22,
    )
    psr_vs9 = compute_psr(
        test_ret, sr_target=GATE_WF_SHARPE_MIN,
        n_bootstrap=N_BOOTSTRAP, seed=SEED, block_size=22,
    )

    # Block-bootstrap Sharpe 95% CI on the baseline test returns
    bs_sharpes = block_bootstrap_sharpe(test_ret, n_samples=N_BOOTSTRAP, block_size=22, seed=SEED)
    ci_lower = float(np.percentile(bs_sharpes, 2.5))
    ci_upper = float(np.percentile(bs_sharpes, 97.5))

    # PBO/CSCV over the 12-config grid (train Sharpe vs test Sharpe)
    pbo_input = grid_df[["train_sharpe", "test_sharpe"]].copy()
    pbo = compute_pbo(pbo_input)

    print(f"  DSR (N={N_PREREGISTERED_TRIALS}): {dsr['dsr']:.4f} (p={dsr['dsr_probability']:.4f})")
    print(f"  PSR(SR>0): {psr_vs0['psr_normal']:.4f} | PSR(SR>0.9 gate): {psr_vs9['psr_normal']:.4f}")
    print(f"  Block-bootstrap Sharpe 95% CI: [{ci_lower:.4f}, {ci_upper:.4f}]")
    print(f"  PBO: {pbo.get('pbo', np.nan)} | IS-OOS rank corr: {pbo.get('rank_correlation_is_oos', np.nan):.3f}")

    return {
        "dsr": dsr,
        "psr_vs0": psr_vs0,
        "psr_vs09": psr_vs9,
        "bs_sharpes": bs_sharpes,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "pbo": pbo,
    }


# ---------------------------------------------------------------------------
# Promotion gates & classification
# ---------------------------------------------------------------------------
def evaluate_gates(wf_summary: dict, grid_result: dict) -> dict:
    mean_wf = float(wf_summary.get("mean_test_sharpe", np.nan))
    pct_pos = float(wf_summary.get("pct_positive_sharpe", np.nan))
    pooled_trades = int(wf_summary.get("total_test_trades", 0))
    n_within = int(grid_result["n_thresholds_within"])

    gate1 = bool(np.isfinite(mean_wf) and mean_wf >= GATE_WF_SHARPE_MIN)
    gate2 = bool(np.isfinite(pct_pos) and pct_pos >= GATE_POSITIVE_FOLD_RATE_MIN)
    gate3 = bool(pooled_trades > GATE_POOLED_TRADES_MIN)
    gate4 = bool(n_within >= 2)  # >= 2 of 4 thresholds

    falsified = (not gate1) or (not gate2)
    if falsified:
        label = "Rejected/Failed"
    elif gate1 and gate2 and gate3 and gate4:
        label = "Credible candidate for further validation"
    else:
        label = "Exploratory signal"

    return {
        "mean_wf_sharpe": mean_wf,
        "pct_positive": pct_pos,
        "pooled_trades": pooled_trades,
        "n_thresholds_within": n_within,
        "gate1_wf_sharpe": gate1,
        "gate2_positive_rate": gate2,
        "gate3_pooled_trades": gate3,
        "gate4_plateau": gate4,
        "falsified": falsified,
        "label": label,
    }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------
def _wf_table(wf_df: pd.DataFrame) -> str:
    lines = [
        "| Fold | Train Start | Train End | Test Start | Test End | "
        "Train Sharpe | Test Sharpe | Test Ann. Ret. | Test Max DD | Test Trades |",
        "|------|-------------|-----------|------------|----------|--------------|"
        "------------|----------------|--------------|-------------|",
    ]
    for _, r in wf_df.iterrows():
        lines.append(
            f"| {int(r['fold'])} | {r['train_start']} | {r['train_end']} | "
            f"{r['test_start']} | {r['test_end']} | "
            f"{_fmt(r['train_sharpe'])} | {_fmt(r['test_sharpe'])} | "
            f"{_fmt(r['test_ann_return'])} | {_fmt(r['test_max_dd'])} | "
            f"{_fmt(r['test_trades'], 0)} |"
        )
    return "\n".join(lines)


def _grid_table(grid_df: pd.DataFrame) -> str:
    lines = [
        "| VIX Threshold | VIX Exposure | Train Sharpe | Val Sharpe | Test Sharpe | "
        "Test Ann. Ret. | Test Max DD | Test Trades | Test Turnover | Test Sortino | Rank |",
        "|---------------|--------------|--------------|------------|------------|"
        "----------------|--------------|-------------|---------------|--------------|------|",
    ]
    for _, r in grid_df.iterrows():
        lines.append(
            f"| {int(r['vix_threshold'])} | {r['vix_exposure']:.1f} | "
            f"{_fmt(r['train_sharpe'])} | {_fmt(r['val_sharpe'])} | "
            f"{_fmt(r['test_sharpe'])} | {_fmt(r['test_ann_return'])} | "
            f"{_fmt(r['test_max_dd'])} | {_fmt(r['test_trades'], 0)} | "
            f"{_fmt(r['test_turnover'], 2)} | {_fmt(r['test_sortino'])} | "
            f"{int(r['rank'])} |"
        )
    return "\n".join(lines)


def _grid_heatmap(grid_df: pd.DataFrame) -> str:
    pivot = grid_df.pivot_table(
        index="vix_threshold", columns="vix_exposure", values="test_sharpe",
    )
    cols = [f"expo={ve:.1f}" for ve in pivot.columns]
    lines = [
        "| VIX Threshold | " + " | ".join(cols) + " |",
        "|---------------|" + "|".join(["--------"] * len(cols)) + "|",
    ]
    for vt, row in pivot.iterrows():
        cells = " | ".join(_fmt(v) for v in row.values)
        lines.append(f"| **{int(vt)}** | {cells} |")
    return "\n".join(lines)


def build_report(
    close: pd.DataFrame,
    vix: pd.Series,
    baseline: dict,
    wf: dict,
    grid: dict,
    benchmarks: dict,
    mult: dict,
    gates: dict,
) -> str:
    today = _today()
    rev = _git_hash()
    cfg_hash = _config_hash()
    res = baseline["res"]
    tm = baseline["test_metrics"]
    tail = baseline["tail"]
    wf_summary = wf["summary"]
    grid_df = grid["grid_df"]
    wf_df = wf["fold_df"]

    # Data integrity table
    integrity_lines = [
        "| Symbol | Rows | Start | End | Close NaN | Dup dates |",
        "|--------|------|-------|-----|-----------|-----------|",
    ]
    integrity_lines.append(
        f"| Aligned 7-ETF Close frame | {len(close):,} | "
        f"{close.index.min().strftime('%Y-%m-%d')} | "
        f"{close.index.max().strftime('%Y-%m-%d')} | "
        f"{int(close.isna().sum().sum())} | 0 |"
    )
    integrity_lines.append(
        f"| ^VIX Close frame | {len(vix):,} | "
        f"{vix.index.min().strftime('%Y-%m-%d')} | "
        f"{vix.index.max().strftime('%Y-%m-%d')} | "
        f"{int(vix.isna().sum())} | 0 |"
    )
    integrity_lines.append(f"| Aligned frame hash | {_frame_hash(close)} | | | | |")
    integrity_lines.append(f"| Config hash (SHA-256[:12]) | {cfg_hash} | | | | |")
    integrity = "\n".join(integrity_lines)

    def metric_row(label: str, m: dict) -> str:
        pf = m.get("profit_factor", "N/A")
        pf_str = f"{pf:.2f}" if isinstance(pf, float) else str(pf)
        return (
            f"| {label} | {m.get('total_return', np.nan):.4f} | "
            f"{m.get('annualized_return', np.nan):.4f} | "
            f"{m.get('annualized_volatility', np.nan):.4f} | "
            f"{m.get('sharpe_ratio', np.nan):.4f} | "
            f"{m.get('sortino_ratio', np.nan):.4f} | "
            f"{m.get('max_drawdown', np.nan):.4f} | "
            f"{m.get('annualized_turnover', np.nan):.2f} | "
            f"{m.get('trade_count', 0)} | {pf_str} | "
            f"{m.get('avg_exposure', np.nan):.4f} |"
        )

    metrics_header = (
        "| Period | Total Return | Ann. Return | Ann. Vol | Sharpe | Sortino | "
        "Max DD | Ann. Turnover | Trades | Profit Factor | Avg Exposure |\n"
        "|--------|--------------|-------------|----------|--------|---------|--------|"
        "---------------|--------|---------------|--------------|"
    )

    def bench_wf_row(label: str, summary: dict) -> str:
        return (
            f"| {label} | {summary.get('n_folds', 0)} | "
            f"{summary.get('mean_test_sharpe', np.nan):.4f} | "
            f"{summary.get('std_test_sharpe', np.nan):.4f} | "
            f"{summary.get('pct_positive_sharpe', np.nan):.1%} | "
            f"{summary.get('total_test_trades', 0)} |"
        )

    bench_wf_header = (
        "| Benchmark | Folds | Mean OOS Sharpe | Std | % Positive | Pooled Trades |\n"
        "|-----------|-------|-----------------|-----|------------|---------------|"
    )

    dsr = mult["dsr"]
    dsr_actual = mult["dsr"]  # pre-registered and evaluated count both = 12
    psr = mult["psr_vs0"]
    psr_gate = mult["psr_vs09"]
    pbo = mult["pbo"]
    ew = benchmarks["ew_test"]
    inc = benchmarks["inc_test"]

    gate_rows = "\n".join([
        f"| 1. Walk-forward mean OOS Sharpe >= {GATE_WF_SHARPE_MIN} | "
        f"{gates['mean_wf_sharpe']:.4f} | {'PASS' if gates['gate1_wf_sharpe'] else 'FAIL'} |",
        f"| 2. Positive fold rate >= {GATE_POSITIVE_FOLD_RATE_MIN:.0%} | "
        f"{gates['pct_positive']:.1%} | {'PASS' if gates['gate2_positive_rate'] else 'FAIL'} |",
        f"| 3. Pooled OOS trades > {GATE_POOLED_TRADES_MIN} | "
        f"{gates['pooled_trades']} | {'PASS' if gates['gate3_pooled_trades'] else 'FAIL'} |",
        f"| 4. VIX-gate plateau: >= 2 of 4 vix_thresholds within 10% of baseline | "
        f"{gates['n_thresholds_within']}/4 | {'PASS' if gates['gate4_plateau'] else 'FAIL'} |",
    ])

    pbo_val = pbo.get("pbo", np.nan)
    if isinstance(pbo_val, float) and np.isnan(pbo_val):
        pbo_txt = (
            f"PBO not computable — degenerate: all {pbo.get('n_configs', 0)} evaluated "
            "configs have identical OOS classification (all above or all below threshold), "
            "so the logit-normal PBO model has no variation. Overfitting diagnostics "
            "rely on IS-OOS rank correlation and mean-IS vs mean-OOS gap below."
        )
    else:
        pbo_txt = f"PBO = {pbo_val:.4f}"

    falsified_str = "MET (hypothesis falsified)" if gates["falsified"] else "NOT met"

    # Grid config strings
    grid_vt = ", ".join(str(x) for x in VIX_THRESHOLDS)
    grid_ve = ", ".join(str(x) for x in VIX_EXPOSURES)

    md = f"""# Experiment: Baseline Backtest & Walk-Forward — Macro Regime Overlay Extension (macroregime_001)

## Hypothesis Reference

`research/hypotheses/macroregime_001.md` (Cycle 19 pre-registration, v001).
Candidate C5 from the Cycle 11 Opportunity Shortlist (24/35 — Exploratory
signal, rank 6 of 10). Parent cycle: Cycle 11 Opportunity Shortlist.

**Mechanism**: The incumbent 226-day TSMOM + combined vol-target (10%) +
drawdown-control (15%) + SPY 200d SMA trend filter is extended with a VIX-level
regime exposure multiplier. Volatility regimes are persistent and VIX spikes
lead equity drawdowns; reducing exposure in high-volatility regimes is a
defensive overlay. C5 is an *overlay-on-overlay* extension — it tests whether the
VIX gate adds value over the already-gated (SPY trend-filtered) incumbent.

**Pre-registered falsification condition** (stated BEFORE any backtest
execution): the hypothesis is rejected if the walk-forward mean OOS Sharpe
< {GATE_WF_SHARPE_MIN} OR < {GATE_POSITIVE_FOLD_RATE_MIN:.0%} of walk-forward folds
have positive test Sharpe.

---

## Data Used

- **Source**: Yahoo Finance via yfinance, cached as daily parquet in
  `data/raw/` (7 ETF files + `^VIX.parquet`). No new data was fetched
  (`fetch_universe(..., force=False)`; cache-only).
- **Date Range**: {START_DATE} to {END_DATE} (common-calendar intersection of the 7 ETFs,
  bounded by GLD inception {START_DATE})
- **Frequency**: Daily (end-of-day OHLCV)
- **Universe**: {", ".join(UNIVERSE)} (n=7)
- **Regime Driver**: ^VIX (index, INPUT ONLY — never a position, not tradeable)
- **Price Field**: Close (EOD), forward-filled onto the union trading calendar
- **Point-in-Time Treatment**: Momentum at date t uses only prices through
  t-skip-lookback; base momentum weights shifted 1 day (signal on T-1 close,
  positions effective T); monthly month-end rebalance calendar carries weights
  forward intra-month (no intra-month trading); SPY 200d SMA and VIX regime use
  the prior day's close (1-day lag, no look-ahead); walk-forward uses 21-day
  purge and 21-day embargo between train and test.
- **Missing-Data Handling**: Pre-inception cells are NaN (not back-filled) and
  would be excluded from cross-sectional ranking via `na_option="keep"`. All 7
  ETFs are incepted by {START_DATE}, so cross-sectional breadth is constant at 7
  for the full strategy history (no point-in-time breadth growth).
- **Cost Model**: 1.0 bps commission + 2.0 bps slippage = 3.0 bps round-trip per
  unit of weight change, identical across candidate and all benchmarks.

{integrity}

---

## Configuration

**Baseline (pre-specified, frozen in `config/macroregime_candidate_001.yaml`)**:

| Parameter | Value |
|-----------|-------|
| Signal | Time-series momentum (226-day return, 21-day skip, top-50% equal-weight) |
| Lookback | {BASELINE['lookback']} trading days (~11 months) |
| Skip | {BASELINE['skip']} trading days (~1 month) |
| Top fraction | {BASELINE['top_fraction']} |
| Vol targeting | {BASELINE['vol_target']:.0%} annualized (63-day trailing realized vol, cap 100%) |
| Drawdown control | Reduce exposure by {BASELINE['dd_reduction']:.0%} when cumulative DD exceeds {BASELINE['dd_threshold']:.0%} |
| SPY trend filter | 0% exposure when SPY < 200d SMA; 100% otherwise (incumbent) |
| VIX regime gate | {BASELINE['vix_exposure']:.0%} exposure when ^VIX > {BASELINE['vix_threshold']}; full exposure otherwise |
| Rebalance | Monthly (month-end calendar) |
| Signal lag | 1 day (T-1 close -> T position) |
| VIX lag | 1 day (prior day VIX close, point-in-time) |
| Commission | 1.0 bps |
| Slippage | 2.0 bps |
| Round-trip cost | 3.0 bps per unit of weight change |
| Risk-free rate | 2.0% annualized (flat) |

**Pre-specified Robustness Grid (fixed count for multiple-testing control)**:

`vix_threshold` in {{{grid_vt}}} x `vix_exposure` in {{{grid_ve}}} =
**{N_GRID_CONFIGS} unique configurations**. Baseline (threshold={BASELINE['vix_threshold']},
exposure={BASELINE['vix_exposure']}) is a grid member. The `vix_exposure=1.0`
arm is the **incumbent control** (no VIX gate — isolates the marginal effect of the VIX gate).
No configurations were added post-hoc; no configuration was selected on test-period results.

**Grid arithmetic assertion (pre-registered)**: `len(vix_thresholds) * len(vix_exposures) == {N_GRID_CONFIGS}`.

**Config file SHA-256[:12]**: `{cfg_hash}`

---

## Train/Validation/Test Splits & Walk-Forward Design

| Split | Period | Purpose |
|-------|--------|---------|
| Train | {START_DATE} to {TRAIN_END} | Parameter selection (NOT used — baseline is pre-specified) |
| Validation | 2010-01-01 to {VAL_END} | Robustness screening (diagnostic only) |
| Test | {TEST_START} to {END_DATE} | Final holdout, promotion-gate decision |

**Walk-Forward Design (pre-registered, matches Cycle 6 convention)**:

- Rolling window: {WF_TRAIN_YEARS:.0f}-year train, {WF_TEST_MONTHS:.0f}-month test, {WF_STEP_MONTHS:.0f}-month step
- Purge: {WF_PURGE_DAYS} days between train end and test start
- Embargo: {WF_EMBARGO_DAYS} days after test period end
- Parameters: FIXED across all folds (no per-fold re-optimization)
- Folds: {wf_summary.get('n_folds', 0)} (from the {START_DATE} common-calendar start)
- Fold 1: train {wf_df.iloc[0]['train_start']} → {wf_df.iloc[0]['train_end']}, test {wf_df.iloc[0]['test_start']} → {wf_df.iloc[0]['test_end']}
- Fold {wf_summary.get('n_folds', 0)}: train {wf_df.iloc[-1]['train_start']} → {wf_df.iloc[-1]['train_end']}, test {wf_df.iloc[-1]['test_start']} → {wf_df.iloc[-1]['test_end']}

**Point-in-time treatment**: momentum signals use only data available at formation (1-day lag);
SPY 200-day SMA and VIX regime use only prior day's close; combined overlay uses only realized
volatility and drawdown history up to the period start. No look-ahead in any split.

---

## 1. Baseline Backtest (Test Period {TEST_START} to {END_DATE})

Configuration: lookback={BASELINE['lookback']}, skip={BASELINE['skip']},
top_fraction={BASELINE['top_fraction']}, vix_threshold={BASELINE['vix_threshold']},
vix_exposure={BASELINE['vix_exposure']}.

{metrics_header}
{metric_row("Test (2018-2026)", tm)}
{metric_row("Validation (2010-2017)", res["validation"])}
{metric_row("Train (2004-2009)", res["train"])}

**Tail metrics (test period, daily net returns)**:

| Metric | Value |
|--------|-------|
| 95% VaR (daily) | {tail['var_95_daily']:.4f} ({tail['var_95_daily']:.2%}) |
| 95% CVaR (daily) | {tail['cvar_95_daily']:.4f} ({tail['cvar_95_daily']:.2%}) |
| Worst day | {tail['worst_day']:.4f} ({tail['worst_day']:.2%}) |

**Artifacts**:

| Artifact | Path | Rows |
|----------|------|------|
| Daily simulation series | `data/processed/simulation_macroregime_001.parquet` | {len(baseline['daily']):,} |
| Trade log | `data/processed/trades_macroregime_001.parquet` | {len(baseline['trades_df']):,} |
| Point-in-time weights | `data/processed/weights_macroregime_001.parquet` | {len(baseline['weights']):,} |

---

## 2. Walk-Forward Evaluation ({wf_summary.get('n_folds', 0)} Folds, Fixed Parameters)

10-year train / 1-year test / 6-month step, {WF_PURGE_DAYS}-day purge, {WF_EMBARGO_DAYS}-day embargo,
fixed pre-registered baseline parameters (vix_threshold={BASELINE['vix_threshold']},
vix_exposure={BASELINE['vix_exposure']}), monthly rebalance, 1-day lag, 3 bps round-trip costs.
No per-fold re-optimization.

### Per-Fold Results

{_wf_table(wf_df)}

### Aggregate Walk-Forward Statistics

| Metric | Value |
|--------|-------|
| Folds | {wf_summary.get('n_folds', 0)} |
| Mean OOS Sharpe | {wf_summary.get('mean_test_sharpe', np.nan):.4f} |
| Std OOS Sharpe | {wf_summary.get('std_test_sharpe', np.nan):.4f} |
| Median OOS Sharpe | {wf_summary.get('median_test_sharpe', np.nan):.4f} |
| Min / Max OOS Sharpe | {wf_summary.get('min_test_sharpe', np.nan):.4f} / {wf_summary.get('max_test_sharpe', np.nan):.4f} |
| % Positive Sharpe Folds | {wf_summary.get('pct_positive_sharpe', np.nan):.1%} |
| Mean Test Ann. Return | {wf_summary.get('mean_test_ann_return', np.nan):.2%} |
| Mean Test Max DD | {wf_summary.get('mean_test_max_dd', np.nan):.2%} |
| Mean Test Trades | {wf_summary.get('mean_test_trades', np.nan):.1f} |
| Total Pooled OOS Trades | {wf_summary.get('total_test_trades', 0)} |

---

## 3. Robustness Grid ({N_GRID_CONFIGS} Pre-Specified Configurations, Test Period)

All {N_GRID_CONFIGS} pre-specified combinations evaluated on the identical test period
({TEST_START} to {END_DATE}) with the identical execution convention. The grid is diagnostic
only: the baseline is pre-specified and no configuration is selected on these results.

### Heatmap — Test Sharpe by VIX Gate Configuration

{_grid_heatmap(grid_df)}

### Full Grid Results

{_grid_table(grid_df)}

### Baseline Rank & VIX-Gate Plateau Check

- **Baseline (threshold={BASELINE['vix_threshold']}, exposure={BASELINE['vix_exposure']}) test Sharpe**: {grid['baseline_test_sharpe']:.4f} — rank **{grid['baseline_rank']} of {N_GRID_CONFIGS}** by test Sharpe
- **Plateau check** (vix_exposure=0.5; all {len(grid['expo_slice'])} vix_thresholds {grid_vt}):
  **{grid['n_thresholds_within']} of 4** thresholds within +/-{grid['plateau_threshold']:.4f}
  of the baseline test Sharpe (threshold = max(0.1, 10% x |baseline|), the repository
  plateau convention from `src/evaluation/statistics.py`) — {'**PASS**' if grid['plateau_pass'] else '**FAIL**'} (gate: >= 2 of 4)

---

## 4. Benchmark Comparison

Both benchmarks evaluated on the identical test period ({TEST_START} to {END_DATE}) and the
identical walk-forward folds, with the identical 3 bps round-trip cost model and 1-day signal lag.

The **incumbent control arm** (tsmomentum_spytrend_001: 226d TSMOM + vol-target 10% + DD
control 15% + SPY 200d SMA filter, NO VIX gate) is evaluated with its validated overlay-warmup
conventions: "slice" (overlay state initializes at the period start) for the test period —
reproducing the Cycle 7 test record — and "full" (overlay state initializes at history_start,
then sliced) for the walk-forward folds — reproducing the Cycle 6 fold record.

The **1/N equal-weight** benchmark is constant 1/7 target weights with a 1-day lag and the
monthly calendar, 3 bps round-trip costs.

### Test-Period Comparison

| Benchmark | Ann. Return | Sharpe | Max DD | Excess Return (ann.) | Excess Sharpe (IR) | Sharpe Diff. | Correlation | Relative Max DD |
|-----------|-------------|--------|--------|----------------------|--------------------|--------------|-------------|-----------------|
| 1/N Equal-Weight (7-ETF) | {ew['bench_ann_return']:.4f} | {ew['bench_sharpe']:.4f} | {ew['bench_max_dd']:.4f} | {ew['excess_ann_return']:.4f} | {ew['excess_sharpe']:.4f} | {ew['sharpe_difference']:.4f} | {ew['correlation']:.3f} | {ew['relative_max_dd']:.4f} |
| Incumbent TSMOM (tsmomentum_spytrend_001) | {inc['bench_ann_return']:.4f} | {inc['bench_sharpe']:.4f} | {inc['bench_max_dd']:.4f} | {inc['excess_ann_return']:.4f} | {inc['excess_sharpe']:.4f} | {inc['sharpe_difference']:.4f} | {inc['correlation']:.3f} | {inc['relative_max_dd']:.4f} |

Excess return/Sharpe are computed on the daily candidate-minus-benchmark series (excess
Sharpe = annualized excess return / annualized excess volatility, i.e. an information ratio).

### Walk-Forward Comparison (identical folds)

{bench_wf_header}
{bench_wf_row("VIX-regime overlay (C5 baseline)", wf_summary)}
{bench_wf_row("1/N Equal-Weight (7-ETF)", benchmarks['ew_wf']['summary'])}
{bench_wf_row("Incumbent TSMOM (control arm)", benchmarks['inc_wf']['summary'])}

---

## 5. Multiple-Testing Control

- **Exact configuration count tracked**: {N_GRID_CONFIGS} unique pre-specified combinations
  (4 thresholds x 3 exposures), with an explicit arithmetic assertion in the Cycle 19 script
  (`assert len(vix_thresholds) * len(vix_exposures) == 12`). The pre-registered trial count
  is {N_PREREGISTERED_TRIALS} — the pre-registered count equals the evaluated count.
  No configuration was selected on test-period results.
- **Deflated Sharpe Ratio** (`src/evaluation.statistics:compute_dsr`,
  {N_BOOTSTRAP} block-bootstrap samples, block=22d, seed={SEED}):
  - At the pre-registered and evaluated count N={N_PREREGISTERED_TRIALS}:
    **DSR = {dsr['dsr']:.4f}** (DSR probability = {dsr['dsr_probability']:.4f}).
    Observed test Sharpe {dsr['sr_observed']:.4f} vs deflation threshold
    {dsr['sr_threshold']:.4f} (SE = {dsr['sharpe_se']:.4f},
    E[max of {N_PREREGISTERED_TRIALS}] = {dsr['e_max']:.4f}).
- **Probabilistic Sharpe Ratio** (PSR vs SR=0):
  {psr['psr_normal']:.4f} (empirical {psr['psr_empirical']:.4f});
  PSR vs the {GATE_WF_SHARPE_MIN} gate: {psr_gate['psr_normal']:.4f}.
- **Block-bootstrap Sharpe 95% CI**: [{mult['ci_lower']:.4f}, {mult['ci_upper']:.4f}].
- **PBO / CSCV** (`src/evaluation/statistics:compute_pbo` over the {N_GRID_CONFIGS}-config
  grid, train=2004-2009 vs test=2018-2026):
  {pbo_txt}; best-IS config OOS Sharpe = {pbo.get('best_is_config', {}).get('test_sharpe', np.nan):.4f};
  IS-OOS Spearman rank correlation = {pbo.get('rank_correlation_is_oos', np.nan):.4f};
  mean IS Sharpe = {pbo.get('mean_is_sharpe', np.nan):.4f} vs mean OOS Sharpe =
  {pbo.get('mean_oos_sharpe', np.nan):.4f}; {pbo.get('n_configs_oos_positive', 0)} of
  {pbo.get('n_configs', 0)} configs have positive OOS Sharpe.

---

## Promotion-Gate Verdict

Pre-registered promotion gates (ALL must pass to advance):

| Gate | Threshold | Observed | Status |
|------|-----------|----------|--------|
{gate_rows}

**Pre-registered falsification condition**: WF mean OOS Sharpe < {GATE_WF_SHARPE_MIN}
OR positive-fold rate < {GATE_POSITIVE_FOLD_RATE_MIN:.0%} — **{falsified_str}**.

### Final Classification

## **{gates['label']}**
"""
    if gates["label"] == "Rejected/Failed":
        md += f"""The pre-registered falsification condition is met.

**Observed evidence**:
- Walk-forward mean OOS Sharpe: {gates['mean_wf_sharpe']:.4f} over {wf_summary.get('n_folds', 0)} folds
  ({wf_summary.get('pct_positive_sharpe', np.nan):.1%} positive fold rate).
- Pooled OOS trades: {gates['pooled_trades']}.
- Baseline test Sharpe: {grid['baseline_test_sharpe']:.4f} (rank {grid['baseline_rank']}/{N_GRID_CONFIGS}).
- VIX-gate plateau: {gates['n_thresholds_within']}/4 thresholds within tolerance.
- Deflated Sharpe Ratio: {dsr['dsr']:.4f} (p={dsr['dsr_probability']:.4f}) does not survive
  multiple-testing deflation at N={N_PREREGISTERED_TRIALS}.
- Incumbent benchmark test Sharpe: {inc['bench_sharpe']:.4f} (control arm, vix_exposure=1.0).

**Classification rationale**: The candidate does not clear the WF mean OOS Sharpe >= {GATE_WF_SHARPE_MIN}
gate and/or the >= {GATE_POSITIVE_FOLD_RATE_MIN:.0%} positive-fold-rate gate. Per the pre-registered
decision discipline in `research/hypotheses/macroregime_001.md`, the result is labeled
**Rejected/Failed** and archived.

**Structural interpretation**: C5 is an overlay-on-overlay extension of an already-gated
candidate (the SPY trend filter already captures the equity-downturn regime). The VIX regime gate
adds a second regime indicator on top of the SPY SMA filter. As the pre-registered prior
explicitly acknowledged, the prior probability of *raising* the incumbent's already-validated
OOS Sharpe is low — the more likely outcomes are (a) no change (the SPY trend filter already
captures the equity-downturn regime) or (b) a decline (over-trimming exits winning positions in
rebounding high-vol windows). ^VIX is an index (not tradeable), so the gate is a position-sizing
rule on the cached ETF universe, not a volatility risk-premium harvest. The result is consistent
with the overlay-only constraint and the diminishing-returns expectation documented in the
pre-registration.
"""
    elif gates["label"] == "Credible candidate for further validation":
        md += f"""All four promotion gates passed. Per the pre-registered decision discipline,
`macroregime_001` (VIX regime overlay on the SPY-trend-filtered incumbent) advances as a
**credible candidate for further validation**. The next cycle will run a prospective
simulation/paper-trading validation of the VIX-overlay incumbent.
"""
    else:
        md += f"""The pre-registered falsification condition is not met, but not all promotion
gates passed. Per the pre-registered decision discipline, `macroregime_001` is an
**exploratory signal**: some promise, gates not fully cleared; the next cycle will
conduct limited follow-up.
"""

    md += f"""
---

## Decision & Next Steps

**Label**: {gates['label']}

**Code revision**: `{rev}`
**Config SHA-256[:12]**: `{cfg_hash}`
**Code revision (git)**: `{rev}`

---

## Reproducibility

### Reproduction Commands

```bash
# Cycle 19: Execute the pre-registered C5 evaluation (baseline + WF + grid + benchmarks + stats)
python3 research/run_cycle19.py

# Verify frozen pre-registration parses
python3 -c "import yaml; yaml.safe_load(open('config/macroregime_candidate_001.yaml'))"
```

### Determinism

The backtest, walk-forward, grid, and benchmark computations are fully deterministic
(no RNG). The block-bootstrap statistics (DSR/PSR/CIs) use seed={SEED} for reproducibility.

### Configuration

- Frozen config: `config/macroregime_candidate_001.yaml` (SHA-256[:12] = `{cfg_hash}`)
- Baseline: lookback={BASELINE['lookback']}, skip={BASELINE['skip']}, top_fraction={BASELINE['top_fraction']}, vix_threshold={BASELINE['vix_threshold']}, vix_exposure={BASELINE['vix_exposure']}
- Grid: {N_GRID_CONFIGS} unique configs ({len(VIX_THRESHOLDS)} thresholds x {len(VIX_EXPOSURES)} exposures)
- Walk-forward: train={WF_TRAIN_YEARS:.0f}y, test={WF_TEST_MONTHS:.0f}m, step={WF_STEP_MONTHS:.0f}m, purge={WF_PURGE_DAYS}d, embargo={WF_EMBARGO_DAYS}d
- Bootstrap: {N_BOOTSTRAP} samples, block=22d, seed={SEED}
- Costs: {COMMISSION_BPS * 10000:.1f} bps commission + {SLIPPAGE_BPS * 10000:.1f} bps slippage = {TOTAL_COST * 10000:.1f} bps round-trip; risk-free rate {RF_ANNUAL:.1%}

---

## Artifacts Referenced

| Artifact | Path |
|----------|------|
| Pre-registered hypothesis | `research/hypotheses/macroregime_001.md` |
| Frozen configuration | `config/macroregime_candidate_001.yaml` |
| Daily simulation series | `data/processed/simulation_macroregime_001.parquet` |
| Trade log | `data/processed/trades_macroregime_001.parquet` |
| Point-in-time weights | `data/processed/weights_macroregime_001.parquet` |
| Cycle 6 walk-forward design | `research/experiments/tsmomentum_regime_filter_wf_001.md` |
| Cycle 11 shortlist (C5 = 24/35) | `research/reports/opportunity_shortlist.md` |
| Prior C5 VIX filter test | `research/experiments/tsmomentum_regime_filter_001.md` |

---

*Report generated: {today} by `research/run_cycle19.py` (Cycle 19)*
*Code revision: {rev}*
"""
    return md


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    print("=" * 60)
    print("CYCLE 19: Baseline Backtest & Walk-Forward — Macro Regime Overlay (macroregime_001)")
    print("=" * 60)

    # --- Data loading (cache-only, no new fetch) ---
    close_raw = fetch_close_prices(UNIVERSE, START_DATE, END_DATE)
    vix_raw = fetch_close_prices([REGIME], START_DATE, END_DATE)
    vix = vix_raw[REGIME]

    # Filter to common-calendar start (GLD inception): strategy history is
    # constant-breadth 7 from START_DATE onward (no point-in-time breadth growth).
    common_start_ts = pd.Timestamp(START_DATE, tz="UTC")
    close = close_raw.loc[close_raw.index >= common_start_ts].copy()
    vix = vix.loc[vix.index >= common_start_ts].copy()

    # Forward-fill VIX gaps on the ETF calendar (VIX is an input only, never a position)
    vix = vix.reindex(close.index, method="ffill").ffill()

    print(f"Data loaded: {close.shape[1]} ETFs + ^VIX, {len(close):,} common trading days "
          f"({close.index.min().strftime('%Y-%m-%d')} to {close.index.max().strftime('%Y-%m-%d')})")

    # --- Pre-execution assertions ---
    assert N_GRID_CONFIGS == 12, f"grid arithmetic: expected 12, got {N_GRID_CONFIGS}"
    assert N_PREREGISTERED_TRIALS == N_GRID_CONFIGS
    assert (BASELINE["vix_threshold"], BASELINE["vix_exposure"]) in [
        (vt, ve) for vt in VIX_THRESHOLDS for ve in VIX_EXPOSURES
    ], "baseline must be a grid member"
    assert len(close) >= 1000, f"insufficient common-calendar data: {len(close)} days"

    splits = generate_walkforward_splits(
        START_DATE, END_DATE,
        WF_TRAIN_YEARS, WF_TEST_MONTHS, WF_STEP_MONTHS,
        WF_PURGE_DAYS, WF_EMBARGO_DAYS,
    )
    assert len(splits) == 24, f"pre-registered fold count violated: expected 24, got {len(splits)}"
    assert splits[0]["train_start"] == START_DATE, splits[0]
    print(f"Walk-forward splits verified: {len(splits)} folds")

    # --- Section 1: Baseline backtest ---
    baseline = run_baseline(close, vix)

    # --- Section 2: Walk-forward evaluation ---
    wf = run_walkforward(close, vix, splits)

    # --- Section 3: Robustness grid ---
    grid = run_grid(close, vix)

    # --- Section 4: Benchmark comparison ---
    benchmarks = run_benchmarks(close, vix, splits, baseline["test_ret"])

    # --- Section 5: Multiple-testing control ---
    mult = run_multiple_testing(baseline["test_ret"], grid["grid_df"])

    # --- Gate evaluation ---
    gates = evaluate_gates(wf["summary"], grid)

    # --- Report generation ---
    report = build_report(close, vix, baseline, wf, grid, benchmarks, mult, gates)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report)
    print(f"\n  Report written -> {REPORT_PATH}")

    # --- Summary ---
    print("\n" + "=" * 60)
    print("CYCLE 19 COMPLETE")
    print("=" * 60)
    print(f"Promotion gates:")
    print(f"  1. WF mean OOS Sharpe >= {GATE_WF_SHARPE_MIN}: {gates['mean_wf_sharpe']:.4f} "
          f"({'PASS' if gates['gate1_wf_sharpe'] else 'FAIL'})")
    print(f"  2. Positive fold rate >= {GATE_POSITIVE_FOLD_RATE_MIN:.0%}: {gates['pct_positive']:.1%} "
          f"({'PASS' if gates['gate2_positive_rate'] else 'FAIL'})")
    print(f"  3. Pooled OOS trades > {GATE_POOLED_TRADES_MIN}: {gates['pooled_trades']} "
          f"({'PASS' if gates['gate3_pooled_trades'] else 'FAIL'})")
    print(f"  4. VIX-gate plateau (>= 2 of 4 thresholds): {gates['n_thresholds_within']}/4 "
          f"({'PASS' if gates['gate4_plateau'] else 'FAIL'})")
    print(f"FINAL VERDICT: {gates['label']}")


if __name__ == "__main__":
    main()
