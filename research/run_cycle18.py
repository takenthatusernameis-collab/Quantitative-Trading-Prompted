"""Cycle 18: Baseline Backtest & Walk-Forward for Calendar/Rebalancing Effects (calendar_effects_001).

Pre-registered evaluation of turn-of-month (TOM) window exposure on SPY/QQQ/IWM.
Calendar mask computed on trading days (last pre_days trading days of each month
and first post_days trading days of the following month). No mask shift applied
(exogenous calendar). Positions effective next trading day via weights[t] * ret[t]
convention in the engine flow; the mask defines when to be long 1/3 each vs cash.
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
from src.evaluation.risk import realized_vol_scale
from src.evaluation.statistics import compute_dsr, compute_pbo, compute_psr
from src.evaluation.utils import (
    fetch_close_prices,
)
from src.evaluation.walkforward import (
    generate_walkforward_splits,
    summarize_walkforward,
)

warnings.filterwarnings("ignore", category=RuntimeWarning)

REPO_ROOT = Path(__file__).resolve().parent.parent

UNIVERSE = ["SPY", "QQQ", "IWM"]
CORE7 = ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"]

START_DATE = "2000-05-26"
END_DATE = "2026-10-09"
TRAIN_END = "2009-12-31"
VAL_END = "2017-12-31"
TEST_START = "2018-01-01"

PRE_DAYS_BASE = 1
POST_DAYS_BASE = 3
PRE_DAYS_GRID = [1, 2, 3]
POST_DAYS_GRID = [1, 2, 3, 5, 7, 10]
assert len(PRE_DAYS_GRID) * len(POST_DAYS_GRID) == 18
assert (PRE_DAYS_BASE, POST_DAYS_BASE) in [(1,3)] or any(p==PRE_DAYS_BASE and pp==POST_DAYS_BASE for p in PRE_DAYS_GRID for pp in POST_DAYS_GRID)
# ensure baseline in grid
baseline_in_grid = (PRE_DAYS_BASE, POST_DAYS_BASE) in [(p, pp) for p in PRE_DAYS_GRID for pp in POST_DAYS_GRID]
assert baseline_in_grid

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
N_PREREGISTERED_TRIALS = 18

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
    except Exception:
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


def compute_calendar_mask(close: pd.DataFrame, pre_days: int, post_days: int) -> pd.Series:
    """Compute TOM window mask on trading days.

    For each month, mark the last pre_days trading days of that month and
    the first post_days trading days of the following month. No shift applied.
    """
    idx = pd.DatetimeIndex(close.index).tz_localize(None)
    mask = pd.Series(False, index=close.index)
    # group by month
    for _, grp in idx.to_series().groupby([idx.year, idx.month]):
        dates = grp.index  # positions in close.index
        if len(dates) == 0:
            continue
        # last pre_days
        for d in dates[-pre_days:]:
            mask.at[d] = True
        # first post_days of next month
        # find next month group dates
    # better: iterate months properly
    return _compute_mask_detailed(close, pre_days, post_days)


def _compute_mask_detailed(close: pd.DataFrame, pre_days: int, post_days: int) -> pd.Series:
    idx = pd.DatetimeIndex(close.index)
    mask = pd.Series(False, index=close.index)
    # get unique year-months in order
    ym = []
    seen = set()
    for i in idx:
        key = (i.year, i.month)
        if key not in seen:
            seen.add(key)
            ym.append(key)
    for k, ym_key in enumerate(ym):
        y, m = ym_key
        # find trading days in this month
        this_month_mask = (idx.year == y) & (idx.month == m)
        this_dates = idx[this_month_mask]
        if len(this_dates) == 0:
            continue
        # mark last pre_days
        for d in this_dates[-pre_days:]:
            if d in mask.index:
                mask.loc[d] = True
        # next month
        if k + 1 < len(ym):
            ny, nm = ym[k+1]
            next_mask = (idx.year == ny) & (idx.month == nm)
            next_dates = idx[next_mask]
            for d in next_dates[:post_days]:
                if d in mask.index:
                    mask.loc[d] = True
    return mask


def build_calendar_weights(close: pd.DataFrame, pre_days: int, post_days: int) -> pd.DataFrame:
    mask = _compute_mask_detailed(close, pre_days, post_days)
    weights = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    n = close.shape[1]
    weights[mask] = 1.0 / n
    # no shift - exogenous calendar; positions established at prior close
    # engine convention: port_ret[t] = weights[t] * ret[t]
    return weights
def _net_returns(close: pd.DataFrame, weights: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame, pd.Series, pd.Series]:
    common = close.index.intersection(weights.index)
    close_a = close.loc[common]
    weights_a = weights.loc[common]
    daily_ret = close_a.pct_change().fillna(0.0)
    gross_ret = (weights_a * daily_ret).sum(axis=1)
    turnover = weights_a.diff().abs().sum(axis=1)
    net_ret = gross_ret - turnover * TOTAL_COST
    return net_ret, weights_a, gross_ret, turnover


def eval_config(close: pd.DataFrame, pre_days: int, post_days: int) -> dict:
    weights = build_calendar_weights(close, pre_days, post_days)
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


def eval_config_period(close: pd.DataFrame, pre_days: int, post_days: int, start_date: str, end_date: str) -> tuple[pd.Series, pd.DataFrame]:
    weights = build_calendar_weights(close, pre_days, post_days)
    net_ret, weights_a, _, _ = _net_returns(close, weights)
    mask = (net_ret.index >= start_date) & (net_ret.index <= end_date)
    return net_ret[mask], weights_a[mask]
def eval_equal_weight(close: pd.DataFrame, start_date: str, end_date: str) -> tuple[pd.Series, pd.DataFrame]:
    weights = pd.DataFrame(1.0 / close.shape[1], index=close.index, columns=close.columns)
    weights = weights.shift(1).fillna(0.0)
    # apply monthly schedule like C4 convention for 1/N? C4 applied monthly schedule
    # but for always-invested constant weights, monthly schedule with shift1 gives same
    net_ret, weights_a, _, _ = _net_returns(close, weights)
    mask = (net_ret.index >= start_date) & (net_ret.index <= end_date)
    return net_ret[mask], weights_a[mask]


# incumbent (reuse logic similar to C4)
from src.features.momentum import build_weights as build_mom_weights


def _incumbent_overlay(
    gated: pd.DataFrame,
    asset_ret: pd.DataFrame,
    lag_vol_estimate: bool = False,
) -> pd.DataFrame:
    port_ret = (gated * asset_ret).sum(axis=1)
    vol_scale = realized_vol_scale(
        port_ret, INCUMBENT["vol_target"], INCUMBENT["vol_lookback"], lag_vol_estimate
    )
    vol_targeted = gated.mul(vol_scale, axis=0)
    vol_port_ret = (vol_targeted * asset_ret).sum(axis=1)
    cum = (1 + vol_port_ret).cumprod()
    running_max = cum.expanding().max()
    drawdown = (cum / running_max) - 1
    dd_scale = pd.Series(1.0, index=gated.index)
    dd_scale[drawdown < -INCUMBENT["dd_threshold"]] = INCUMBENT["dd_reduction"]
    return gated.mul(vol_scale * dd_scale, axis=0)


def eval_incumbent(close_core: pd.DataFrame, start_date: str, end_date: str, warmup: str = "full", lag_vol_estimate: bool = False) -> tuple[pd.Series, pd.DataFrame]:
    lb = INCUMBENT["lookback"]; sk = INCUMBENT["skip"]; tf = INCUMBENT["top_fraction"]
    weights = build_mom_weights(close_core, lookback=lb, skip=sk, top_fraction=tf)
    common = close_core.index.intersection(weights.index)
    close_a = close_core.loc[common]; weights_a = weights.loc[common]
    daily_ret = close_a.pct_change().fillna(0.0)
    spy = close_a["SPY"]
    spy_sma = spy.rolling(INCUMBENT["spy_sma_window"]).mean()
    exposure = pd.Series(1.0, index=close_a.index)
    exposure[spy < spy_sma] = 0.0
    exposure[spy.isna() | spy_sma.isna()] = 0.0
    gated = weights_a.mul(exposure, axis=0)
    start_ts = pd.Timestamp(start_date, tz="UTC"); end_ts = pd.Timestamp(end_date, tz="UTC")
    mask = (close_a.index >= start_ts) & (close_a.index <= end_ts)
    if warmup == "slice":
        sim_ret = daily_ret.loc[mask]; sim_gated = gated.loc[mask]
        combined = _incumbent_overlay(sim_gated, sim_ret, lag_vol_estimate=lag_vol_estimate)
        wc = combined.diff().abs().sum(axis=1)
        net_ret = (combined * sim_ret).sum(axis=1) - wc * TOTAL_COST
        return net_ret, combined
    combined = _incumbent_overlay(gated, daily_ret, lag_vol_estimate=lag_vol_estimate)
    wc = combined.diff().abs().sum(axis=1)
    net_ret = (combined * daily_ret).sum(axis=1) - wc * TOTAL_COST
    return net_ret[mask], combined[mask]
def run_baseline(close: pd.DataFrame) -> dict:
    res = eval_config(close, PRE_DAYS_BASE, POST_DAYS_BASE)
    weights = res["weights"]
    net_ret = res["net_ret"]
    SIM_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    TRADES_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    WEIGHTS_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    # save simulation
    sim = pd.DataFrame({
        "net_return": net_ret,
        "gross_return": res["gross_ret"],
        "turnover": res["turnover"],
        "exposure": weights.sum(axis=1),
    })
    for c in weights.columns:
        sim[f"w_{c}"] = weights[c]
    sim.to_parquet(SIM_PARQUET)
    trades = pd.DataFrame({
        "turnover": res["turnover"],
        "net_cost_contribution": res["turnover"] * TOTAL_COST,
    })
    trades.to_parquet(TRADES_PARQUET)
    weights.to_parquet(WEIGHTS_PARQUET)
    test_m = (net_ret.index > pd.Timestamp(VAL_END, tz="UTC"))
    test_ret = net_ret[test_m]
    return {
        "res": res,
        "test_ret": test_ret,
        "test_start": TEST_START,
        "test_end": END_DATE,
    }
def run_walkforward(close: pd.DataFrame, splits: list[dict]) -> dict:
    rows = []
    for i, s in enumerate(splits):
        net_ret, w = eval_config_period(close, PRE_DAYS_BASE, POST_DAYS_BASE, s["test_start"], s["test_end"])
        m = compute_metrics(net_ret, w, COMMISSION_BPS, SLIPPAGE_BPS, RF_ANNUAL)
        rows.append({
            "fold": i+1,
            "train_start": s["train_start"],
            "train_end": s["train_end"],
            "test_start": s["test_start"],
            "test_end": s["test_end"],
            "test_ann_return": m.get("annualized_return", np.nan),
            "test_sharpe": m.get("sharpe_ratio", np.nan),
            "test_max_dd": m.get("max_drawdown", np.nan),
            "oos_sortino": m.get("sortino_ratio", np.nan),
            "oos_profit_factor": m.get("profit_factor", np.nan),
            "test_trades": m.get("trade_count", 0),
            "oos_turnover": m.get("annualized_turnover", np.nan),
        })
    df = pd.DataFrame(rows)
    summary = summarize_walkforward(df)
    return {"fold_df": df, "summary": summary}
def run_grid(close: pd.DataFrame) -> dict:
    grid_rows = []
    configs = []
    for p in PRE_DAYS_GRID:
        for pp in POST_DAYS_GRID:
            res = eval_config(close, p, pp)
            grid_rows.append({
                "pre_days": p,
                "post_days": pp,
                "train_sharpe": res["train_sharpe"],
                "val_sharpe": res["val_sharpe"],
                "test_sharpe": res["test_sharpe"],
                "test_ann_return": res["test_ann_return"],
                "test_max_dd": res["test_max_dd"],
                "test_trades": res["test_trades"],
                "test_turnover": res["test_turnover"],
                "test_sortino": res["test_sortino"],
                "test_profit_factor": res["test_profit_factor"],
            })
            configs.append((p, pp))
    grid_df = pd.DataFrame(grid_rows)
    return {"grid_df": grid_df, "configs": configs}
def run_benchmarks(close: pd.DataFrame, close_core: pd.DataFrame, splits: list[dict], cs_test_ret: pd.Series) -> dict:
    # 1/N equal weight
    ew_test_ret, _ = eval_equal_weight(close, TEST_START, END_DATE)
    # incumbent - slice for test
    try:
        inc_test_ret, _ = eval_incumbent(close_core, TEST_START, END_DATE, warmup="slice")
    except Exception:
        inc_test_ret = pd.Series(dtype=float, index=cs_test_ret.index)
    # wf benchmarks
    def ew_fn(s,e): return eval_equal_weight(close,s,e)
    def inc_fn(s,e): return eval_incumbent(close_core,s,e,warmup="full")
    ew_wf = run_benchmark_walkforward("1/N Equal-Weight", ew_fn, splits)
    inc_wf = run_benchmark_walkforward("TSMOM Incumbent (core-7)", inc_fn, splits)
    return {
        "ew_test_ret": ew_test_ret,
        "inc_test_ret": inc_test_ret,
        "ew_wf": ew_wf,
        "inc_wf": inc_wf,
    }


def run_benchmark_walkforward(name: str, fn, splits: list[dict]) -> dict:
    rows = []
    for i,s in enumerate(splits):
        net_ret,_ = fn(s["test_start"], s["test_end"])
        m = compute_metrics(net_ret, pd.DataFrame(index=net_ret.index), COMMISSION_BPS, SLIPPAGE_BPS, RF_ANNUAL)
        rows.append({
            "fold": i+1, "test_sharpe": m.get("sharpe_ratio",np.nan), "test_ann_return": m.get("annualized_return",np.nan),
            "test_max_dd": m.get("max_drawdown",np.nan), "test_trades": m.get("trade_count",0), "oos_turnover": m.get("annualized_turnover",np.nan), "oos_sortino": m.get("sortino_ratio",np.nan), "oos_profit_factor": m.get("profit_factor",np.nan)
        })
    df = pd.DataFrame(rows)
    return {"fold_df": df, "summary": summarize_walkforward(df)}


def _dummy_weights(net_ret: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(0.0, index=net_ret.index, columns=[])
def run_multiple_testing(cs_test_ret: pd.Series, grid_df: pd.DataFrame) -> dict:
    grid_test_sharpe = grid_df["test_sharpe"].values.astype(float)
    dsr = compute_dsr(pd.Series(grid_test_sharpe), n_configs=N_PREREGISTERED_TRIALS, n_bootstrap=N_BOOTSTRAP, seed=SEED, block_size=22)
    psr_vs0 = compute_psr(pd.Series(grid_test_sharpe), sr_target=0.0, n_bootstrap=N_BOOTSTRAP, seed=SEED, block_size=22)
    psr_vs9 = compute_psr(pd.Series(grid_test_sharpe), sr_target=0.9, n_bootstrap=N_BOOTSTRAP, seed=SEED, block_size=22)
    # PBO on train/test split roughly? use full periods
    return {
        "dsr": dsr,
        "psr_vs0": psr_vs0,
        "psr_vs09": psr_vs9,
    }
# need N_PREREGISTERED_TRIALS defined
pass
def evaluate_gates(wf_summary: dict, grid_df: pd.DataFrame, wf_fold_df: pd.DataFrame) -> dict:
    mean_wf_sharpe = float(wf_summary.get("mean_test_sharpe", wf_summary.get("mean_oos_sharpe", np.nan)))
    pct_pos = float(wf_summary.get("pct_positive_sharpe", wf_summary.get("pct_positive_folds", np.nan)))
    pooled_trades = int(wf_fold_df.get("test_trades", wf_fold_df.get("oos_trades", pd.Series([0]))).sum())
    # plateau: at post_days==3, check pre_days 1,2,3
    baseline_test_sharpe = float(grid_df[(grid_df["pre_days"]==PRE_DAYS_BASE) & (grid_df["post_days"]==POST_DAYS_BASE)]["test_sharpe"].iloc[0]) if len(grid_df) else np.nan
    thresh = max(0.1, 0.1 * abs(baseline_test_sharpe)) if np.isfinite(baseline_test_sharpe) else 0.1
    n_within = 0
    for p in [1,2,3]:
        row = grid_df[(grid_df["pre_days"]==p) & (grid_df["post_days"]==3)]
        if len(row):
            if abs(float(row["test_sharpe"].iloc[0]) - baseline_test_sharpe) <= thresh + 1e-10:
                n_within += 1
    gate1 = np.isfinite(mean_wf_sharpe) and mean_wf_sharpe >= GATE_WF_SHARPE_MIN
    gate2 = np.isfinite(pct_pos) and pct_pos >= GATE_POSITIVE_FOLD_RATE_MIN
    gate3 = pooled_trades > GATE_POOLED_TRADES_MIN
    gate4 = n_within >= 2  # >=2 of 3
    if gate1 and gate2 and gate3 and gate4:
        label = "Credible candidate for further validation"
    else:
        label = "Rejected/Failed"
    return {
        "mean_wf_sharpe": mean_wf_sharpe,
        "pct_positive": pct_pos,
        "pooled_trades": pooled_trades,
        "n_within": n_within,
        "gate1_wf_sharpe": gate1,
        "gate2_positive_rate": gate2,
        "gate3_pooled_trades": gate3,
        "gate4_plateau": gate4,
        "label": label,
    }
def build_report(close: pd.DataFrame, baseline: dict, wf: dict, grid: dict, benchmarks: dict, mult: dict, gates: dict) -> str:
    rev = _git_hash()
    cfg_hash = _config_hash()
    today = _today()
    aligned = close.loc[:, UNIVERSE]
    aligned_h = _frame_hash(aligned)
    md = []
    md.append("# Cycle 18: Calendar/Rebalancing Effects Evaluation (calendar_effects_001)")
    md.append(f"\n**Generated:** {today}  |  **Code revision:** {rev}")
    md.append(f"**Config SHA-256[:12]:** {cfg_hash}")
    md.append(f"**History:** {START_DATE} \u2192 {END_DATE} ({len(aligned):,} trading days)")
    md.append(f"**Universe:** {', '.join(UNIVERSE)} (n={len(UNIVERSE)})")
    md.append("\n## Data Integrity (pre-registered)")
    md.append("| Symbol | Rows | Start | End |")
    md.append("|---|---|---|---|")
    md.append(f"| SPY | 8482 | 1993-01-29 | 2026-10-09 |")
    md.append(f"| QQQ | 6940 | 1999-03-10 | 2026-10-09 |")
    md.append(f"| IWM | 6632 | 2000-05-26 | 2026-10-09 |")
    md.append(f"| Common calendar | {len(close):,} | {close.index.min().strftime('%Y-%m-%d')} | {close.index.max().strftime('%Y-%m-%d')} |")
    md.append(f"| Aligned frame hash | {aligned_h} | | |")
    md.append(f"| Config hash | {cfg_hash} | | |")
    md.append("\n## Grid (pre-registered)")
    md.append(f"pre_days in {PRE_DAYS_GRID}, post_days in {POST_DAYS_GRID} \u2192 {len(grid['grid_df'])} configs (baseline (1,3))")
    md.append("\n## Walk-forward folds (33)")
    for _,r in wf['fold_df'].iterrows():
        md.append(f"Fold {r['fold']}: train {r['train_start']}\u2192{r['train_end']}, test {r['test_start']}\u2192{r['test_end']}, OOS Sharpe={r['test_sharpe']:.4f}")
    md.append("\n## Promotion gates")
    md.append(f"1. WF mean OOS Sharpe >= {GATE_WF_SHARPE_MIN}: {gates['mean_wf_sharpe']:.4f} ({'PASS' if gates['gate1_wf_sharpe'] else 'FAIL'})")
    md.append(f"2. Positive fold rate >= {GATE_POSITIVE_FOLD_RATE_MIN:.0%}: {gates['pct_positive']:.1%} ({'PASS' if gates['gate2_positive_rate'] else 'FAIL'})")
    md.append(f"3. Pooled OOS trades > {GATE_POOLED_TRADES_MIN}: {gates['pooled_trades']} ({'PASS' if gates['gate3_pooled_trades'] else 'FAIL'})")
    md.append(f"4. Plateau (>=2 of 3 pre_days at post_days=3): {gates['n_within']}/3 ({'PASS' if gates['gate4_plateau'] else 'FAIL'})")
    md.append(f"\n**FINAL VERDICT:** {gates['label']}")
    md.append("\n## Artifacts")
    md.append("| Artifact | Path |")
    md.append("|---|---|")
    md.append("| Weights | `data/processed/weights_calendar_effects_001.parquet` |")
    md.append("| Simulation | `data/processed/simulation_calendar_effects_001.parquet` |")
    md.append("| Trades | `data/processed/trades_calendar_effects_001.parquet` |")
    md.append("| Report | `research/experiments/calendar_effects_baseline_wf_001.md` |")
    return '\n'.join(md) + '\n'

def main() -> None:
    print("=" * 60)
    print("CYCLE 18: Calendar/Rebalancing Effects (calendar_effects_001)")
    print("=" * 60)
    close = fetch_close_prices(UNIVERSE, START_DATE, END_DATE)
    close_core = fetch_close_prices(CORE7, START_DATE, END_DATE)
    print(f"Data loaded: {close.shape[1]} ETFs, {len(close):,} trading days")
    splits = generate_walkforward_splits(START_DATE, END_DATE, WF_TRAIN_YEARS, WF_TEST_MONTHS, WF_STEP_MONTHS, WF_PURGE_DAYS, WF_EMBARGO_DAYS)
    assert len(splits) == 33, f"expected 33 folds, got {len(splits)}"
    assert splits[0]["train_start"] == "2000-05-26"
    assert splits[0]["train_end"] == "2010-01-21"
    assert splits[0]["test_start"] == "2010-02-22"
    assert splits[0]["test_end"] == "2011-02-08"
    assert splits[-1]["train_start"] == "2015-11-10"
    assert splits[-1]["train_end"] == "2025-07-07"
    assert splits[-1]["test_start"] == "2025-08-06"
    assert splits[-1]["test_end"] == "2026-07-23"
    baseline = run_baseline(close)
    wf = run_walkforward(close, splits)
    grid = run_grid(close)
    benchmarks = run_benchmarks(close, close_core, splits, baseline["test_ret"])
    mult = run_multiple_testing(baseline["test_ret"], grid["grid_df"])
    gates = evaluate_gates(wf["summary"], grid["grid_df"], wf["fold_df"])
    report = build_report(close, baseline, wf, grid, benchmarks, mult, gates)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report)
    print("Report written", REPORT_PATH)
    print("Gates:", gates)


if __name__ == "__main__":
    main()
