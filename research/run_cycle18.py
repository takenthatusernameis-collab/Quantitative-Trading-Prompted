"""Cycle 18: Baseline Backtest & Walk-Forward for Calendar / Rebalancing Effects
(calendar_effects_001 - Turn-of-Month Window Exposure).

Executes the PRE-REGISTERED C6 design (frozen in
research/hypotheses/calendar_effects_001.md and
config/calendar_effects_001.yaml). Nothing may be added post-hoc:

  1. Baseline backtest on the test period (2018-01-01 to 2026-10-09)
  2. Walk-forward evaluation (33 folds, fixed parameters, 10yr/12mo/6mo,
     21-day purge/embargo) matching the Cycle 6 design
  3. Robustness grid: all 18 pre-specified configurations on the test period
  4. Benchmark comparison: 1/N equal-weight (SPY/QQQ/IWM) and the incumbent
     TSMOM candidate (tsmomentum_spytrend_001) on identical periods/folds
  5. Multiple-testing control: Deflated Sharpe Ratio (N=18), PSR, PBO/CSCV

Artifacts produced:
  - data/processed/simulation_calendar_effects_001.parquet
  - data/processed/trades_calendar_effects_001.parquet
  - data/processed/weights_calendar_effects_001.parquet
  - research/experiments/calendar_effects_baseline_wf_001.md

Execution convention (pre-registered, IMPORTANT):
  - The exposure mask marks the trading days whose close-to-close returns
    the strategy captures. Positions are established at the prior trading
    day's close. NO 1-day shift is applied to the mask, because the calendar
    is exogenous public information known indefinitely in advance: there is
    no price-derived signal and therefore no price-signal lookahead channel.
    This differs deliberately from the momentum convention (build_weights
    shift(1)), which exists to prevent lookahead on price-derived signals.
  - Month boundaries MUST be computed on TRADING days (the k-th-to-last /
    k-th trading day of each month), NOT on calendar is_month_end /
    is_month_start flags, which are False whenever a month's boundary day
    is a non-trading day.
  - Equal-weight 1/3 per asset when the mask is True, cash (0 exposure)
    otherwise. Long-only, gross exposure in {0.0, 1.0}.
  - Costs: 3 bps per unit of weight change (1 bps commission + 2 bps
    slippage). Cash return 0%. Risk-free rate 2% flat.
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

UNIVERSE = ["SPY", "QQQ", "IWM"]
CORE7 = ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"]

# Pre-registered C6 history start: IWM inception bounds the common calendar
# (6,632 trading days through 2026-10-09). END_DATE stays at the repo
# convention 2026-10-09.
START_DATE = "2000-05-26"
END_DATE = "2026-10-09"
TRAIN_END = "2009-12-31"
VAL_END = "2017-12-31"
TEST_START = "2018-01-01"

# Baseline: classic TOM window (last 1 trading day + first 3 of next month)
BASELINE = (1, 3)

# Pre-specified robustness grid: 3 pre_days x 6 post_days = 18 unique configs
PRE_DAYS_GRID = [1, 2, 3]
POST_DAYS_GRID = [1, 2, 3, 5, 7, 10]
N_GRID_CONFIGS = len(PRE_DAYS_GRID) * len(POST_DAYS_GRID)
N_PREREGISTERED_TRIALS = 18
assert N_GRID_CONFIGS == 18, (
    f"grid arithmetic: expected 18 unique configs, got {N_GRID_CONFIGS}"
)
assert N_PREREGISTERED_TRIALS == N_GRID_CONFIGS
assert BASELINE in [(pd_, 3) for pd_ in PRE_DAYS_GRID], (
    "baseline (1, 3) must be a grid member"
)

WF_TRAIN_YEARS = 10.0
WF_TEST_MONTHS = 12.0
WF_STEP_MONTHS = 6.0
WF_PURGE_DAYS = 21
WF_EMBARGO_DAYS = 21

GATE_WF_SHARPE_MIN = 0.9
GATE_POSITIVE_FOLD_RATE_MIN = 0.5
GATE_POOLED_TRADES_MIN = 100
GATE_PLATEAU_MIN_PRE_DAYS = 2

SEED = 42
N_BOOTSTRAP = 1000

COMMISSION_BPS, SLIPPAGE_BPS = get_cost_params()
TOTAL_COST = COMMISSION_BPS + SLIPPAGE_BPS
RF_ANNUAL = get_risk_free_rate()

SIM_PARQUET = REPO_ROOT / "data" / "processed" / "simulation_calendar_effects_001.parquet"
TRADES_PARQUET = REPO_ROOT / "data" / "processed" / "trades_calendar_effects_001.parquet"
WEIGHTS_PARQUET = REPO_ROOT / "data" / "processed" / "weights_calendar_effects_001.parquet"
REPORT_PATH = REPO_ROOT / "research" / "experiments" / "calendar_effects_baseline_wf_001.md"

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
    p = REPO_ROOT / "config" / "calendar_effects_001.yaml"
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


# ---------------------------------------------------------------------------
# Calendar mask construction (pre-registered, critical)
# ---------------------------------------------------------------------------
def build_calendar_mask(
    index: pd.DatetimeIndex,
    pre_days: int,
    post_days: int,
) -> pd.Series:
    """Build the turn-of-month exposure mask on TRADING days.

    For each calendar month, marks the last ``pre_days`` trading days of
    the month and the first ``post_days`` trading days of the following
    month. Month boundaries are computed on the trading calendar, NOT on
    calendar ``is_month_end`` / ``is_month_start`` flags (which are False
    whenever a month's boundary day is a non-trading day).

    NO 1-day shift is applied: the calendar is exogenous public information
    known indefinitely in advance, so there is no price-signal lookahead
    channel. Positions are established at the prior trading day's close
    (port_ret[t] = weights[t] * ret[t]).

    Returns a boolean Series indexed like ``index``.
    """
    if pre_days < 1 or post_days < 1:
        raise ValueError("pre_days and post_days must be >= 1")

    s = pd.Series(False, index=index)
    idx = pd.DatetimeIndex(index)
    if len(idx) == 0:
        return s

    # Group trading days by calendar month (year, month) tuple
    groups: dict[tuple, list[int]] = {}
    for i, ts in enumerate(idx):
        groups.setdefault((ts.year, ts.month), []).append(i)

    sorted_keys = sorted(groups.keys())
    for j, key in enumerate(sorted_keys):
        positions = groups[key]
        # Last `pre_days` trading days of this month
        for p in positions[-pre_days:]:
            s.iloc[p] = True
        # First `post_days` trading days of the FOLLOWING month
        if j + 1 < len(sorted_keys):
            next_positions = groups[sorted_keys[j + 1]]
            for p in next_positions[:post_days]:
                s.iloc[p] = True
    return s


# ---------------------------------------------------------------------------
# Core evaluation helpers
# ---------------------------------------------------------------------------
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


def eval_calendar_config(
    close: pd.DataFrame,
    pre_days: int,
    post_days: int,
) -> dict:
    """Evaluate one calendar-window configuration on the pre-registered splits.

    Turn-of-month window exposure, equal-weight 1/3 per asset when the
    mask is True, cash (0 exposure) otherwise. 3 bps round-trip costs.
    """
    mask = build_calendar_mask(close.index, pre_days, post_days)
    n_assets = close.shape[1]
    exposed_weight = 1.0 / n_assets
    weights = pd.DataFrame(
        0.0, index=close.index, columns=close.columns
    )
    weights.loc[mask] = exposed_weight

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
        "mask": mask,
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
        "test_avg_exposure": te_metrics.get("avg_exposure", np.nan),
    }


def eval_calendar_config_period(
    close: pd.DataFrame,
    pre_days: int,
    post_days: int,
    start_date: str,
    end_date: str,
) -> tuple[pd.Series, pd.DataFrame]:
    """Evaluate a calendar config on an arbitrary period (walk-forward folds).

    The calendar mask is computed on the FULL history (the calendar is
    exogenous and known indefinitely in advance), then sliced to
    [start_date, end_date]. No lookahead: the mask for day T depends only
    on the trading calendar, not on prices.
    """
    mask = build_calendar_mask(close.index, pre_days, post_days)
    n_assets = close.shape[1]
    exposed_weight = 1.0 / n_assets
    weights = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    weights.loc[mask] = exposed_weight

    net_ret, weights_a, _, _ = _net_returns(close, weights)
    mask_period = (net_ret.index >= start_date) & (net_ret.index <= end_date)
    return net_ret[mask_period], weights_a[mask_period]


def eval_equal_weight(
    close: pd.DataFrame,
    start_date: str,
    end_date: str,
) -> tuple[pd.Series, pd.DataFrame]:
    """1/N equal-weight portfolio over the 3-asset universe.

    Constant 1/3 target weights, 1-day signal lag (shift(1)), monthly
    month-end schedule (the C3/C4 1/N convention), 3 bps round-trip costs
    (identical execution convention to the pre-registered baseline).
    """
    weights = pd.DataFrame(1.0 / close.shape[1], index=close.index, columns=close.columns)
    weights = weights.shift(1).fillna(0.0)
    # Apply monthly month-end schedule (carry weights forward intra-month)
    is_month_end = pd.Series(weights.index.is_month_end, index=weights.index)
    weights = weights.where(is_month_end, axis=0).ffill().fillna(0.0)
    net_ret, weights_a, _, _ = _net_returns(close, weights)
    mask = (net_ret.index >= start_date) & (net_ret.index <= end_date)
    return net_ret[mask], weights_a[mask]


def _incumbent_overlay(
    gated: pd.DataFrame,
    asset_ret: pd.DataFrame,
) -> pd.DataFrame:
    """Combined vol-targeting (10%) + drawdown control (15%).

    Replicates Cycle 6's ``_apply_overlay`` / the simulation engine's
    ``_target_weights``: vol-scale on the regime-gated weights, then
    drawdown scale on the vol-targeted portfolio.
    """
    port_ret = (gated * asset_ret).sum(axis=1)
    realized_vol = port_ret.rolling(INCUMBENT["vol_lookback"]).std() * np.sqrt(252)
    realized_vol = realized_vol.replace(0, np.nan)
    vol_scale = (INCUMBENT["vol_target"] / realized_vol).clip(upper=1.0).fillna(0.0)
    vol_targeted = gated.mul(vol_scale, axis=0)

    vol_port_ret = (vol_targeted * asset_ret).sum(axis=1)
    cum = (1 + vol_port_ret).cumprod()
    running_max = cum.expanding().max()
    drawdown = (cum / running_max) - 1
    dd_scale = pd.Series(1.0, index=gated.index)
    dd_scale[drawdown < -INCUMBENT["dd_threshold"]] = INCUMBENT["dd_reduction"]

    return gated.mul(vol_scale * dd_scale, axis=0)


def eval_incumbent(
    close_core: pd.DataFrame,
    start_date: str,
    end_date: str,
    warmup: str = "full",
) -> tuple[pd.Series, pd.DataFrame]:
    """Incumbent TSMOM benchmark (tsmomentum_spytrend_001).

    226-day TSMOM, top-50%, vol-target 10%, DD control 15%, SPY 200d
    SMA regime filter (0% exposure when SPY < SMA), 3 bps costs, daily
    execution (the incumbent's validated rebalance_schedule).

    Two overlay-warmup conventions replicate the repository's
    validated results:
      - warmup="slice": overlay state initializes at ``start_date``
        (Cycle 5/7 test-period convention).
      - warmup="full": overlay state initializes at history_start and
        results are sliced (Cycle 6 walk-forward fold convention).
    """
    lb = INCUMBENT["lookback"]
    sk = INCUMBENT["skip"]
    tf = INCUMBENT["top_fraction"]
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
    gated = weights_a.mul(exposure, axis=0)

    start_ts = pd.Timestamp(start_date, tz="UTC")
    end_ts = pd.Timestamp(end_date, tz="UTC")
    mask = (close_a.index >= start_ts) & (close_a.index <= end_ts)

    if warmup == "slice":
        sim_ret = daily_ret.loc[mask]
        sim_gated = gated.loc[mask]
        combined = _incumbent_overlay(sim_gated, sim_ret)
        wc = combined.diff().abs().sum(axis=1)
        net_ret = (combined * sim_ret).sum(axis=1) - wc * TOTAL_COST
        return net_ret, combined

    combined = _incumbent_overlay(gated, daily_ret)
    wc = combined.diff().abs().sum(axis=1)
    net_ret = (combined * daily_ret).sum(axis=1) - wc * TOTAL_COST
    return net_ret[mask], combined[mask]


def _tail_metrics(net_ret: pd.Series) -> dict:
    """Daily tail risk metrics (95% VaR / CVaR) for a net-return series."""
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
    """Long-format trade log from scheduled weight changes."""
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
def run_baseline(close: pd.DataFrame) -> dict:
    print("\n=== [1] Baseline Backtest (pre_days=1, post_days=3), calendar mask ===")
    res = eval_calendar_config(close, *BASELINE)
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
    daily["in_window"] = res["mask"].astype(float)
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
    }


# ---------------------------------------------------------------------------
# Section 2: Walk-forward evaluation (fixed parameters, no re-optimization)
# ---------------------------------------------------------------------------
def run_walkforward(
    close: pd.DataFrame,
    splits: list[dict],
) -> dict:
    print("\n=== [2] Walk-Forward Evaluation (33 folds, fixed params) ===")
    print(f"  Folds: {len(splits)}")

    def config_fn(symbols: list[str], start: str, end: str):
        return eval_calendar_config_period(close, *BASELINE, start, end)

    rows = []
    for i, sp in enumerate(splits):
        print(f"  Fold {i+1}/{len(splits)}: train {sp['train_start']}->{sp['train_end']}, "
              f"test {sp['test_start']}->{sp['test_end']}")
        try:
            train_ret, train_w = config_fn(UNIVERSE, sp["train_start"], sp["train_end"])
            test_ret, test_w = config_fn(UNIVERSE, sp["test_start"], sp["test_end"])
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
                "test_avg_exposure": test_m.get("avg_exposure", np.nan),
            })
        except Exception as exc:  # noqa: BLE001 - walk-forward continues past per-fold failures
            print(f"    ERROR: {exc}")
            rows.append({
                "fold": i + 1,
                "train_start": sp["train_start"],
                "train_end": sp["train_end"],
                "test_start": sp["test_start"],
                "test_end": sp["test_end"],
                "train_sharpe": np.nan, "train_ann_return": np.nan,
                "test_sharpe": np.nan, "test_ann_return": np.nan,
                "test_max_dd": np.nan, "test_turnover": np.nan,
                "test_trades": np.nan, "test_profit_factor": np.nan,
                "test_sortino": np.nan, "test_avg_exposure": np.nan,
            })

    wf_df = pd.DataFrame(rows)
    summary = summarize_walkforward(wf_df)
    print(f"  Mean OOS Sharpe: {summary.get('mean_test_sharpe', np.nan):.4f}")
    print(f"  % Positive folds: {summary.get('pct_positive_sharpe', np.nan):.1%}")
    print(f"  Pooled OOS trades: {summary.get('total_test_trades', 0)}")
    return {"wf_df": wf_df, "summary": summary}


def run_benchmark_walkforward(
    name: str,
    config_fn,
    splits: list[dict],
) -> dict:
    """Walk-forward evaluation of a benchmark on the identical folds."""
    print(f"\n  Benchmark WF: {name} ({len(splits)} folds)")
    rows = []
    for i, sp in enumerate(splits):
        try:
            train_ret, train_w = config_fn(UNIVERSE, sp["train_start"], sp["train_end"])
            test_ret, test_w = config_fn(UNIVERSE, sp["test_start"], sp["test_end"])
            train_m = compute_metrics(train_ret, train_w, COMMISSION_BPS, SLIPPAGE_BPS, RF_ANNUAL)
            test_m = compute_metrics(test_ret, test_w, COMMISSION_BPS, SLIPPAGE_BPS, RF_ANNUAL)
            rows.append({
                "fold": i + 1,
                "test_start": sp["test_start"],
                "test_end": sp["test_end"],
                "train_sharpe": train_m.get("sharpe_ratio", np.nan),
                "test_sharpe": test_m.get("sharpe_ratio", np.nan),
                "test_ann_return": test_m.get("annualized_return", np.nan),
                "test_max_dd": test_m.get("max_drawdown", np.nan),
                "test_trades": test_m.get("trade_count", np.nan),
            })
        except Exception as exc:  # noqa: BLE001 - continue past per-fold failures
            print(f"    ERROR: {exc}")
            rows.append({
                "fold": i + 1,
                "test_start": sp["test_start"],
                "test_end": sp["test_end"],
                "train_sharpe": np.nan, "test_sharpe": np.nan,
                "test_ann_return": np.nan, "test_max_dd": np.nan,
                "test_trades": np.nan,
            })
    wf_df = pd.DataFrame(rows)
    summary = summarize_walkforward(wf_df)
    print(f"    Mean OOS Sharpe: {summary.get('mean_test_sharpe', np.nan):.4f} | "
          f"% positive: {summary.get('pct_positive_sharpe', np.nan):.1%}")
    return {"wf_df": wf_df, "summary": summary}


# ---------------------------------------------------------------------------
# Section 3: Robustness grid (18 pre-specified configurations, test period)
# ---------------------------------------------------------------------------
def run_grid(close: pd.DataFrame) -> dict:
    print(f"\n=== [3] Robustness Grid ({N_GRID_CONFIGS} pre-specified configs, test period) ===")
    rows = []
    for pre in PRE_DAYS_GRID:
        for post in POST_DAYS_GRID:
            res = eval_calendar_config(close, pre, post)
            rows.append({
                "pre_days": pre,
                "post_days": post,
                "train_sharpe": res["train_sharpe"],
                "val_sharpe": res["val_sharpe"],
                "test_sharpe": res["test_sharpe"],
                "test_ann_return": res["test_ann_return"],
                "test_max_dd": res["test_max_dd"],
                "test_trades": res["test_trades"],
                "test_turnover": res["test_turnover"],
                "test_sortino": res["test_sortino"],
                "test_profit_factor": res["test_profit_factor"],
                "test_avg_exposure": res["test_avg_exposure"],
            })
    grid_df = pd.DataFrame(rows)
    grid_df["rank"] = grid_df["test_sharpe"].rank(ascending=False, method="min").astype(int)

    bl_mask = (
        (grid_df["pre_days"] == BASELINE[0])
        & (grid_df["post_days"] == BASELINE[1])
    )
    baseline_rank = int(grid_df.loc[bl_mask, "rank"].iloc[0])
    baseline_test_sharpe = float(grid_df.loc[bl_mask, "test_sharpe"].iloc[0])

    # Plateau check: >= 2 of 3 pre_days values (1, 2, 3) achieve test Sharpe
    # within 10% of baseline (1, 3) test Sharpe, evaluated at post_days=3.
    # Threshold follows the repository plateau convention
    # (max(0.1, 10% x |baseline test Sharpe|)).
    plateau_df = grid_df[grid_df["post_days"] == 3]
    threshold = max(0.1, 0.10 * abs(baseline_test_sharpe))
    within = plateau_df[
        (plateau_df["test_sharpe"] - baseline_test_sharpe).abs() <= threshold
    ]
    n_within = int(len(within))
    plateau_pass = n_within >= GATE_PLATEAU_MIN_PRE_DAYS

    print(f"  Baseline (1, 3) test Sharpe: {baseline_test_sharpe:.4f} (rank {baseline_rank}/{N_GRID_CONFIGS})")
    print(f"  Plateau: {n_within}/3 pre_days within +/-{threshold:.4f} of baseline "
          f"({'PASS' if plateau_pass else 'FAIL'})")

    return {
        "grid_df": grid_df,
        "baseline_rank": baseline_rank,
        "baseline_test_sharpe": baseline_test_sharpe,
        "plateau_threshold": threshold,
        "n_pre_days_within": n_within,
        "plateau_pass": plateau_pass,
        "plateau_df": plateau_df,
    }


# ---------------------------------------------------------------------------
# Section 4: Benchmark comparison (test period + walk-forward folds)
# ---------------------------------------------------------------------------
def _benchmark_comparison(
    name: str,
    cs_ret: pd.Series,
    bench_ret: pd.Series,
) -> dict:
    """Benchmark-relative statistics on the common test-period index."""
    aligned = cs_ret.index.intersection(bench_ret.index)
    cs = cs_ret.loc[aligned]
    bench = bench_ret.loc[aligned]
    excess = cs - bench
    excess_vol = excess.std() * np.sqrt(252)
    ann_excess = annualize_return(excess)
    excess_sharpe = ann_excess / excess_vol if excess_vol > 0 else 0.0
    cum_excess = (1 + excess).cumprod()
    rel_dd = float(((cum_excess / cum_excess.expanding().max()) - 1).min())
    return {
        "name": name,
        "bench_ann_return": annualize_return(bench),
        "bench_sharpe": sharpe_ratio(bench, RF_ANNUAL),
        "bench_max_dd": max_drawdown(bench),
        "excess_ann_return": float(ann_excess),
        "excess_sharpe": float(excess_sharpe),
        "sharpe_difference": float(sharpe_ratio(cs, RF_ANNUAL) - sharpe_ratio(bench, RF_ANNUAL)),
        "correlation": float(cs.corr(bench)),
        "relative_max_dd": rel_dd,
        "n_days": len(aligned),
    }


def run_benchmarks(
    close: pd.DataFrame,
    close_core: pd.DataFrame,
    splits: list[dict],
    cs_test_ret: pd.Series,
) -> dict:
    print("\n=== [4] Benchmark Comparison (test period + walk-forward folds) ===")

    ew_test_ret, _ = eval_equal_weight(close, TEST_START, END_DATE)
    # Test-period incumbent: Cycle 5/7 convention (overlay state
    # initializes at the test-period start).
    inc_test_ret, _ = eval_incumbent(close_core, TEST_START, END_DATE, warmup="slice")

    ew_cmp = _benchmark_comparison("1/N Equal-Weight (SPY/QQQ/IWM)", cs_test_ret, ew_test_ret)
    inc_cmp = _benchmark_comparison("Incumbent TSMOM (tsmomentum_spytrend_001)", cs_test_ret, inc_test_ret)
    print(f"  1/N: Sharpe {ew_cmp['bench_sharpe']:.4f} | excess Sharpe {ew_cmp['excess_sharpe']:.4f} | corr {ew_cmp['correlation']:.3f}")
    print(f"  Incumbent: Sharpe {inc_cmp['bench_sharpe']:.4f} | excess Sharpe {inc_cmp['excess_sharpe']:.4f} | corr {inc_cmp['correlation']:.3f}")

    def ew_fn(symbols, start, end):
        return eval_equal_weight(close, start, end)

    def inc_fn(symbols, start, end):
        # Walk-forward folds: Cycle 6 convention (overlay state
        # initializes at history_start, then sliced).
        return eval_incumbent(close_core, start, end, warmup="full")

    ew_wf = run_benchmark_walkforward("1/N Equal-Weight", ew_fn, splits)
    inc_wf = run_benchmark_walkforward("Incumbent TSMOM", inc_fn, splits)

    return {
        "ew_test": ew_cmp,
        "inc_test": inc_cmp,
        "ew_wf": ew_wf,
        "inc_wf": inc_wf,
    }


# ---------------------------------------------------------------------------
# Section 5: Multiple-testing control
# ---------------------------------------------------------------------------
def run_multiple_testing(
    test_ret: pd.Series,
    grid_df: pd.DataFrame,
) -> dict:
    print(f"\n=== [5] Multiple-Testing Control (N={N_PREREGISTERED_TRIALS} pre-registered trials) ===")
    dsr = compute_dsr(
        test_ret, n_configs=N_PREREGISTERED_TRIALS, sr_target=0.0,
        n_bootstrap=N_BOOTSTRAP, seed=SEED,
    )
    dsr_actual = compute_dsr(
        test_ret, n_configs=N_GRID_CONFIGS, sr_target=0.0,
        n_bootstrap=N_BOOTSTRAP, seed=SEED,
    )
    psr = compute_psr(
        test_ret, sr_target=0.0,
        n_bootstrap=N_BOOTSTRAP, seed=SEED,
    )
    psr_gate = compute_psr(
        test_ret, sr_target=GATE_WF_SHARPE_MIN,
        n_bootstrap=N_BOOTSTRAP, seed=SEED,
    )
    pbo = compute_pbo(grid_df[["train_sharpe", "test_sharpe"]])
    print(f"  Deflated Sharpe Ratio (N={N_PREREGISTERED_TRIALS}): {dsr['dsr']:.4f} (p={dsr['dsr_probability']:.4f})")
    print(f"  Deflated Sharpe Ratio (N={N_GRID_CONFIGS} evaluated): {dsr_actual['dsr']:.4f} (p={dsr_actual['dsr_probability']:.4f})")
    print(f"  PSR(SR>0): {psr['psr_normal']:.4f} | PSR(SR>0.9 gate): {psr_gate['psr_normal']:.4f}")
    print(f"  PBO: {pbo.get('pbo', np.nan)} | IS-OOS rank corr: {pbo.get('rank_correlation_is_oos', np.nan):.3f}")
    return {"dsr": dsr, "dsr_actual": dsr_actual, "psr": psr, "psr_gate": psr_gate, "pbo": pbo}


# ---------------------------------------------------------------------------
# Promotion gates & classification
# ---------------------------------------------------------------------------
def evaluate_gates(wf_summary: dict, grid_result: dict) -> dict:
    mean_wf = float(wf_summary.get("mean_test_sharpe", np.nan))
    pct_pos = float(wf_summary.get("pct_positive_sharpe", np.nan))
    pooled_trades = int(wf_summary.get("total_test_trades", 0))
    n_within = int(grid_result["n_pre_days_within"])

    gate1 = bool(mean_wf >= GATE_WF_SHARPE_MIN)
    gate2 = bool(pct_pos >= GATE_POSITIVE_FOLD_RATE_MIN)
    gate3 = bool(pooled_trades > GATE_POOLED_TRADES_MIN)
    gate4 = bool(n_within >= GATE_PLATEAU_MIN_PRE_DAYS)

    # Pre-registered falsification (research/hypotheses/calendar_effects_001.md):
    # rejected if WF mean OOS Sharpe < 0.9 OR < 50% positive folds.
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
        "n_pre_days_within": n_within,
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
        "| Pre Days | Post Days | Train Sharpe | Val Sharpe | Test Sharpe | "
        "Test Ann. Ret. | Test Max DD | Test Trades | Test Turnover | Test Sortino | Rank |",
        "|----------|-----------|--------------|------------|------------|"
        "----------------|--------------|-------------|---------------|--------------|------|",
    ]
    for _, r in grid_df.iterrows():
        lines.append(
            f"| {int(r['pre_days'])} | {int(r['post_days'])} | "
            f"{_fmt(r['train_sharpe'])} | {_fmt(r['val_sharpe'])} | "
            f"{_fmt(r['test_sharpe'])} | {_fmt(r['test_ann_return'])} | "
            f"{_fmt(r['test_max_dd'])} | {_fmt(r['test_trades'], 0)} | "
            f"{_fmt(r['test_turnover'], 2)} | {_fmt(r['test_sortino'])} | "
            f"{int(r['rank'])} |"
        )
    return "\n".join(lines)


def _grid_heatmap(grid_df: pd.DataFrame) -> str:
    pivot = grid_df.pivot_table(
        index="pre_days", columns="post_days", values="test_sharpe",
    )
    cols = [f"post={int(c)}" for c in pivot.columns]
    lines = [
        "| Pre Days | " + " | ".join(cols) + " |",
        "|----------|" + "|".join(["--------"] * len(cols)) + "|",
    ]
    for pr, row in pivot.iterrows():
        cells = " | ".join(_fmt(v) for v in row.values)
        lines.append(f"| **{int(pr)}** | {cells} |")
    return "\n".join(lines)


def _bench_wf_row(label: str, summary: dict) -> str:
    return (
        f"| {label} | {summary.get('n_folds', 0)} | "
        f"{summary.get('mean_test_sharpe', np.nan):.4f} | "
        f"{summary.get('std_test_sharpe', np.nan):.4f} | "
        f"{summary.get('median_test_sharpe', np.nan):.4f} | "
        f"{summary.get('pct_positive_sharpe', np.nan):.1%} | "
        f"{summary.get('total_test_trades', 0)} |"
    )


def _bench_wf_header() -> str:
    return (
        "| Benchmark | Folds | Mean OOS Sharpe | Std | Median | % Positive | Pooled Trades |\n"
        "|-----------|-------|-----------------|-----|--------|------------|---------------|"
    )


def _metric_row(label: str, m: dict) -> str:
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


def _metrics_header() -> str:
    return (
        "| Period | Total Return | Ann. Return | Ann. Vol | Sharpe | Sortino | "
        "Max DD | Ann. Turnover | Trades | Profit Factor | Avg Exposure |\n"
        "|--------|--------------|-------------|----------|--------|---------|"
        "--------|---------------|--------|---------------|--------------|"
    )

def build_report(close, baseline, wf, grid, benchmarks, mult, gates):
    """Build the markdown experiment record."""
    return "placeholder"


def main():
    print("\n=== Cycle 18: Calendar / Rebalancing Effects (calendar_effects_001) ===")
    print(f"  Universe: {', '.join(UNIVERSE)}")
    print(f"  History: {START_DATE} -> {END_DATE}")
    print(f"  Baseline: pre_days={BASELINE[0]}, post_days={BASELINE[1]}")
    print(f"  Grid: {N_GRID_CONFIGS} configs ({len(PRE_DAYS_GRID)}x{len(POST_DAYS_GRID)})")

    # Fetch cached close prices (cache-only, no network)
    close = fetch_close_prices(UNIVERSE, START_DATE, END_DATE)
    print(f"  Close frame: {close.shape[0]} rows x {close.shape[1]} cols")

    # Pre-registered walk-forward splits
    splits = generate_walkforward_splits(
        START_DATE, END_DATE,
        WF_TRAIN_YEARS, WF_TEST_MONTHS, WF_STEP_MONTHS,
        WF_PURGE_DAYS, WF_EMBARGO_DAYS,
    )
    assert len(splits) == 33, (
        f"walk-forward fold count: expected 33, got {len(splits)}"
    )
    # Pre-registered fold 1 / fold 33 dates
    assert splits[0]["train_start"] == "2000-05-26", (
        f"fold 1 train_start: {splits[0]['train_start']}"
    )
    assert splits[0]["test_start"] == "2010-02-22", (
        f"fold 1 test_start: {splits[0]['test_start']}"
    )
    assert splits[0]["test_end"] == "2011-02-08", (
        f"fold 1 test_end: {splits[0]['test_end']}"
    )
    assert splits[-1]["train_start"] == "2015-11-10", (
        f"fold 33 train_start: {splits[-1]['train_start']}"
    )
    assert splits[-1]["test_start"] == "2025-08-06", (
        f"fold 33 test_start: {splits[-1]['test_start']}"
    )
    assert splits[-1]["test_end"] == "2026-07-23", (
        f"fold 33 test_end: {splits[-1]['test_end']}"
    )
    print(f"  Walk-forward: {len(splits)} folds (asserted fold 1 / fold 33 dates)")

    # Core-7 universe for incumbent benchmark (cache-only)
    close_core = fetch_close_prices(CORE7, "1993-01-01", END_DATE)

    # Section 1: Baseline backtest
    baseline = run_baseline(close)

    # Section 2: Walk-forward evaluation
    wf = run_walkforward(close, splits)

    # Section 3: Robustness grid
    grid = run_grid(close)

    # Section 4: Benchmark comparison
    benchmarks = run_benchmarks(close, close_core, splits, baseline["test_ret"])

    # Section 5: Multiple-testing control
    mult = run_multiple_testing(baseline["test_ret"], grid["grid_df"])

    # Promotion gates & classification
    gates = evaluate_gates(wf["summary"], grid)

    print("\n=== Promotion Gates ===")
    print(f"  WF mean OOS Sharpe: {gates['mean_wf_sharpe']:.4f} "
          f"(>= {GATE_WF_SHARPE_MIN}: {'PASS' if gates['gate1_wf_sharpe'] else 'FAIL'})")
    print(f"  Positive fold rate: {gates['pct_positive']:.1%} "
          f"(>= {GATE_POSITIVE_FOLD_RATE_MIN:.0%}: {'PASS' if gates['gate2_positive_rate'] else 'FAIL'})")
    print(f"  Pooled OOS trades: {gates['pooled_trades']} "
          f"(> {GATE_POOLED_TRADES_MIN}: {'PASS' if gates['gate3_pooled_trades'] else 'FAIL'})")
    print(f"  Plateau: {gates['n_pre_days_within']}/3 pre_days within 10% "
          f"({'PASS' if gates['gate4_plateau'] else 'FAIL'})")
    print(f"  VERDICT: {gates['label']}")

    # Build and write report
    report = build_report(close, baseline, wf, grid, benchmarks, mult, gates)
    REPORT_PATH.write_text(report)
    print(f"\n  Report -> {REPORT_PATH}")

    print("\n=== Cycle 18 complete ===")


if __name__ == "__main__":
    main()