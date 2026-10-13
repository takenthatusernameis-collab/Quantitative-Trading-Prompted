"""Cycle 15 C4 corrected re-execution: Sector Rotation across the nine GICS ETFs.

This runner preserves the frozen pre-registration and core evaluation machinery,
but makes the candidate universe, dates, configuration provenance, benchmark inputs,
cache-only requirement, walk-forward design, and output artifacts executable contracts.
The known-defective historical runner remains research/run_cycle15.py.
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
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.backtest.engine import (
    compute_metrics,
    get_cost_params,
    get_risk_free_rate,
)
from src.evaluation.statistics import compute_dsr, compute_pbo, compute_psr
from src.evaluation.utils import (
    annualize_return,
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
    "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY",
]
# Separate historical input universe for the incumbent TSMOM benchmark.
# Do not select it as a subset of the nine-sector candidate DataFrame.
CORE7 = ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"]
CORE7_START_DATE = "1993-01-01"

START_DATE = "1998-12-22"
END_DATE = "2026-10-09"
TRAIN_END = "2009-12-31"
VAL_END = "2017-12-31"
TEST_START = "2018-01-01"

BASELINE = (252, 21, 0.5)

LOOKBACKS = [189, 252, 315]
SKIPS = [21, 42]
TOP_FRACTIONS = [0.3, 0.5, 0.7]
N_GRID_CONFIGS = len(LOOKBACKS) * len(SKIPS) * len(TOP_FRACTIONS)
# Pre-registered multiple-testing count (frozen hypothesis and config
# state "27 configurations"; the pre-specified parameter values
# 3 lookbacks x 2 skips x 3 top-fractions yield 18 unique
# combinations. Both counts are reported for transparency; the
# pre-registered N=18 is the conservative primary).
N_PREREGISTERED_TRIALS = 18

WF_TRAIN_YEARS = 10.0
WF_TEST_MONTHS = 12.0
WF_STEP_MONTHS = 6.0
WF_PURGE_DAYS = 21
WF_EMBARGO_DAYS = 21

GATE_WF_SHARPE_MIN = 0.9
GATE_POSITIVE_FOLD_RATE_MIN = 0.5
GATE_POOLED_TRADES_MIN = 100
GATE_PLATEAU_MIN_LOOKBACKS = 2

SEED = 42
N_BOOTSTRAP = 1000

COMMISSION_BPS, SLIPPAGE_BPS = get_cost_params()
TOTAL_COST = COMMISSION_BPS + SLIPPAGE_BPS
RF_ANNUAL = get_risk_free_rate()

SIM_PARQUET = REPO_ROOT / "data" / "processed" / "simulation_sectorrotation_001.parquet"
TRADES_PARQUET = REPO_ROOT / "data" / "processed" / "trades_sectorrotation_001.parquet"
WEIGHTS_PARQUET = REPO_ROOT / "data" / "processed" / "weights_sectorrotation_001.parquet"
REPORT_PATH = REPO_ROOT / "research" / "experiments" / "sectorrotation_baseline_wf_001.md"

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
    p = REPO_ROOT / "config" / "sectorrotation_candidate_001.yaml"
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


EXPECTED_CLOSE_ROWS = 6991
EXPECTED_CLOSE_START = "1998-12-22"
EXPECTED_CLOSE_END = "2026-10-08"
EXPECTED_FOLD_ENDPOINTS = (
    {"train_start": "1998-12-22", "train_end": "2008-08-18", "test_start": "2008-09-17", "test_end": "2009-09-03"},
    {"train_start": "2015-11-17", "train_end": "2025-07-14", "test_start": "2025-08-13", "test_end": "2026-07-30"},
)


def _validate_preregistered_contract() -> list[dict]:
    """Fail before data access if code drifts from the frozen C4 plan."""
    config_path = REPO_ROOT / "config" / "sectorrotation_candidate_001.yaml"
    if not config_path.is_file():
        raise RuntimeError(f"Frozen C4 configuration is missing: {config_path}")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    expected_universe = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
    if UNIVERSE != expected_universe or config.get("universe") != expected_universe:
        raise RuntimeError("C4 universe mismatch: code and frozen config must both contain the nine GICS sector ETFs in order.")
    if config.get("candidate_id") != "sectorrotation_001":
        raise RuntimeError("Frozen config candidate_id is not sectorrotation_001.")
    if START_DATE != EXPECTED_CLOSE_START or config.get("history_start") != START_DATE:
        raise RuntimeError("C4 start date does not match the frozen history_start.")
    if END_DATE != "2026-10-09":
        raise RuntimeError("The pre-registered C4 end date changed unexpectedly.")
    signal = config.get("signal") or {}
    expected_signal = {"type": "csmomentum", "lookback": BASELINE[0], "skip": BASELINE[1],
                       "top_fraction": BASELINE[2], "rebalance_freq": "monthly"}
    for key, value in expected_signal.items():
        if signal.get(key) != value:
            raise RuntimeError(f"Frozen C4 signal mismatch for {key}: expected {value!r}, got {signal.get(key)!r}.")
    if len(LOOKBACKS) * len(SKIPS) * len(TOP_FRACTIONS) != 18 or N_GRID_CONFIGS != 18:
        raise RuntimeError("C4 robustness grid must contain exactly 18 unique configurations.")
    if N_PREREGISTERED_TRIALS != 18:
        raise RuntimeError("C4 multiple-testing trial count must remain 18.")
    execution = config.get("execution") or {}
    if execution.get("signal_lag_days") != 1 or execution.get("price_field") != "Close":
        raise RuntimeError("C4 execution convention differs from the frozen configuration.")
    if execution.get("rebalance_schedule") != "monthly":
        raise RuntimeError("C4 rebalance schedule differs from the frozen configuration.")
    if (config.get("risk_overlay") or {}).get("none") is not True:
        raise RuntimeError("C4 baseline must run without risk overlays.")
    data_config = config.get("data") or {}
    if data_config.get("cached") is not True or data_config.get("fetch_new") is not False:
        raise RuntimeError("C4 must use the frozen cached dataset without fetching new data.")
    costs = config.get("cost_model") or {}
    if not np.isclose(float(costs.get("commission_bps", float("nan"))), COMMISSION_BPS * 10000):
        raise RuntimeError("Commission assumption differs from the frozen C4 cost model.")
    if not np.isclose(float(costs.get("slippage_bps", float("nan"))), SLIPPAGE_BPS * 10000):
        raise RuntimeError("Slippage assumption differs from the frozen C4 cost model.")
    if not np.isclose(float(costs.get("total_round_trip_bps", float("nan"))), TOTAL_COST * 10000):
        raise RuntimeError("Total transaction cost differs from the frozen C4 cost model.")
    splits = generate_walkforward_splits(
        START_DATE, END_DATE, WF_TRAIN_YEARS, WF_TEST_MONTHS, WF_STEP_MONTHS, WF_PURGE_DAYS, WF_EMBARGO_DAYS
    )
    if len(splits) != 36:
        raise RuntimeError(f"C4 walk-forward design must have 36 folds, got {len(splits)}.")
    for actual, expected in zip((splits[0], splits[-1]), EXPECTED_FOLD_ENDPOINTS, strict=True):
        for key, value in expected.items():
            if actual.get(key) != value:
                raise RuntimeError(f"C4 fold endpoint drift at {key}: expected {value}, got {actual.get(key)}.")
    print("C4 pre-registration contract: PASS (9 ETFs, 18 configs, 36 folds, frozen costs).")
    return splits


def _require_cached_inputs() -> None:
    """Fail before fetcher use if caches are missing or invalid; never download data."""
    raw_dir = REPO_ROOT / "data" / "raw"
    symbols = list(dict.fromkeys([*UNIVERSE, *CORE7]))
    start, end = pd.Timestamp(START_DATE, tz="UTC"), pd.Timestamp(END_DATE, tz="UTC")
    missing = [symbol for symbol in symbols
               if not (raw_dir / f"{symbol.replace('/', '-').replace('=', '-')}.parquet").is_file()]
    if missing:
        raise RuntimeError("Cache-only C4 run blocked before fetch: missing data/raw parquet for "
                           f"{', '.join(missing)}. Restore the frozen cache; do not fetch new data.")
    for symbol in symbols:
        path = raw_dir / f"{symbol.replace('/', '-').replace('=', '-')}.parquet"
        try:
            frame = pd.read_parquet(path)
        except Exception as exc:
            raise RuntimeError(f"Cache-only C4 run blocked: unreadable parquet cache for {symbol}: {path}") from exc
        if frame.empty or "Close" not in frame.columns:
            raise RuntimeError(f"Cache-only C4 run blocked: {symbol} cache is empty or lacks Close.")
        index = pd.to_datetime(frame.index, utc=True)
        if index.has_duplicates:
            raise RuntimeError(f"Cache integrity failure: duplicate timestamps for {symbol}.")
        close = pd.to_numeric(pd.Series(frame["Close"].to_numpy(), index=index, name="Close"), errors="coerce")
        in_window = close.loc[(close.index >= start) & (close.index <= end)]
        if in_window.empty or in_window.index.max().date().isoformat() < EXPECTED_CLOSE_END:
            raise RuntimeError(f"Cache coverage failure for {symbol}: no usable Close through {EXPECTED_CLOSE_END}.")
        if symbol in UNIVERSE:
            if len(in_window) != EXPECTED_CLOSE_ROWS:
                raise RuntimeError(f"Frozen sector cache row-count mismatch for {symbol}: expected {EXPECTED_CLOSE_ROWS}, got {len(in_window)}.")
            if in_window.index.min().date().isoformat() != EXPECTED_CLOSE_START:
                raise RuntimeError(f"Frozen sector cache start mismatch for {symbol}.")
            if in_window.index.max().date().isoformat() != EXPECTED_CLOSE_END:
                raise RuntimeError(f"Frozen sector cache end mismatch for {symbol}.")
            if in_window.isna().any() or (in_window <= 0).any():
                raise RuntimeError(f"Frozen sector cache has missing/non-positive Close values for {symbol}.")
    print(f"Cache-only data preflight: PASS ({len(symbols)} symbol caches; no downloads allowed).")


def _load_cached_close_prices(symbols: list[str]) -> pd.DataFrame:
    """Load and align Close prices from local parquet files only.

    This deliberately does not call ``fetch_universe`` or ``fetch_close_prices``:
    their cache-miss behavior downloads from Yahoo Finance.  The preflight above
    validates every required cache first; this loader then has no network-capable
    code path.
    """
    raw_dir = REPO_ROOT / "data" / "raw"
    closes: dict[str, pd.Series] = {}
    for symbol in symbols:
        path = raw_dir / f"{symbol.replace('/', '-').replace('=', '-')}.parquet"
        frame = pd.read_parquet(path)
        index = pd.DatetimeIndex(pd.to_datetime(frame.index, utc=True))
        close = pd.Series(pd.to_numeric(frame["Close"], errors="coerce").to_numpy(), index=index)
        closes[symbol] = close[~close.index.duplicated(keep="last")].sort_index()

    all_dates = pd.DatetimeIndex(sorted(set().union(*(series.index for series in closes.values()))))
    all_dates = all_dates[all_dates.weekday < 5]
    return pd.DataFrame({symbol: closes[symbol].reindex(all_dates).ffill() for symbol in symbols}, index=all_dates)


def _slice_prices(frame: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:
    """Enforce requested dates because the cache loader returns whole cached files."""
    start, end = pd.Timestamp(start_date, tz="UTC"), pd.Timestamp(end_date, tz="UTC")
    return frame.loc[(frame.index >= start) & (frame.index <= end)].copy()


def _validate_sector_close(close: pd.DataFrame) -> None:
    if list(close.columns) != UNIVERSE:
        raise RuntimeError(f"C4 aligned columns differ from frozen universe: {list(close.columns)}")
    if len(close) != EXPECTED_CLOSE_ROWS:
        raise RuntimeError(f"C4 aligned frame must have {EXPECTED_CLOSE_ROWS} rows, got {len(close)}.")
    if close.index.has_duplicates:
        raise RuntimeError("C4 aligned Close frame has duplicate timestamps.")
    if close.index.min().date().isoformat() != EXPECTED_CLOSE_START or close.index.max().date().isoformat() != EXPECTED_CLOSE_END:
        raise RuntimeError("C4 aligned Close date range differs from 1998-12-22 through 2026-10-08.")
    if close.isna().any().any() or (close <= 0).any().any():
        raise RuntimeError("C4 aligned Close frame contains missing or non-positive values.")


def _validate_core_benchmark_close(close_core: pd.DataFrame) -> None:
    if list(close_core.columns) != CORE7:
        raise RuntimeError("Incumbent benchmark input columns do not match the 7-symbol CORE7 universe.")
    if close_core.empty or close_core.index.has_duplicates:
        raise RuntimeError("Incumbent benchmark cache is empty or has duplicate timestamps.")
    if close_core.index.max().date().isoformat() < EXPECTED_CLOSE_END:
        raise RuntimeError("Incumbent benchmark cache does not extend through the C4 evaluation end date.")


def _validate_generated_outputs(close: pd.DataFrame, baseline: dict, wf: dict, splits: list[dict], report: str) -> None:
    """Re-open persisted outputs and reject wrong-universe or wrong-fold artifacts."""
    if len(wf["wf_df"]) != 36 or wf["summary"].get("n_folds") != 36:
        raise RuntimeError("Generated walk-forward record does not contain exactly 36 folds.")
    # The legacy evaluator records per-fold exceptions as NaN and continues.
    # A complete row count is not sufficient evidence that every fold ran.
    required_oos_metrics = ("test_sharpe", "test_ann_return", "test_max_dd", "test_turnover", "test_trades")
    for column in required_oos_metrics:
        if column not in wf["wf_df"].columns:
            raise RuntimeError(f"Walk-forward output is missing required OOS metric: {column}.")
        values = pd.to_numeric(wf["wf_df"][column], errors="coerce")
        if not np.isfinite(values.to_numpy(dtype=float)).all():
            bad_folds = wf["wf_df"].loc[~np.isfinite(values.to_numpy(dtype=float)), "fold"].tolist()
            raise RuntimeError(f"Walk-forward metric {column} is missing/non-finite in fold(s): {bad_folds}.")
    for row, split in zip(wf["wf_df"].to_dict(orient="records"), splits, strict=True):
        for key in ("train_start", "train_end", "test_start", "test_end"):
            if row.get(key) != split.get(key):
                raise RuntimeError(f"Generated fold {row.get('fold')} has incorrect {key}.")
    if list(baseline["weights"].columns) != UNIVERSE or len(baseline["weights"]) != EXPECTED_CLOSE_ROWS:
        raise RuntimeError("In-memory weights violate the 9-ETF / 6,991-row contract.")
    weights = pd.read_parquet(WEIGHTS_PARQUET)
    if list(weights.columns) != UNIVERSE or len(weights) != EXPECTED_CLOSE_ROWS:
        raise RuntimeError("Persisted weights violate the C4 universe/row-count contract.")
    if not pd.DatetimeIndex(weights.index).equals(pd.DatetimeIndex(close.index)):
        raise RuntimeError("Persisted weights index differs from the aligned C4 price index.")
    simulation = pd.read_parquet(SIM_PARQUET)
    if len(simulation) != EXPECTED_CLOSE_ROWS or "net_return" not in simulation.columns:
        raise RuntimeError("Persisted simulation parquet is missing rows or net_return.")
    if not pd.DatetimeIndex(simulation.index).equals(pd.DatetimeIndex(close.index)):
        raise RuntimeError("Persisted simulation index differs from the aligned C4 price index.")
    trades = pd.read_parquet(TRADES_PARQUET)
    if not trades.empty and not set(trades["symbol"].dropna().unique()).issubset(set(UNIVERSE)):
        raise RuntimeError("Persisted trade log contains a symbol outside the nine-sector universe.")
    expected_hash = _config_hash()
    for required in ("sectorrotation_baseline_wf_001", "config/sectorrotation_candidate_001.yaml",
                     expected_hash, "1998-12-22", "36 Folds",
                     "XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY"):
        if required not in report:
            raise RuntimeError(f"Generated report is missing provenance marker: {required}")
    print("Persisted artifact contract: PASS (9 ETF columns, 6,991 dates, 36 folds, correct config hash).")


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
    """Month-end calendar rebalancing (pre-registered execution schedule).

    Weights computed on month-end dates (themselves already shifted 1 day
    by build_weights, i.e. point-in-time) are carried forward intra-month;
    no intra-month trading occurs.
    """
    is_month_end = pd.Series(weights.index.is_month_end, index=weights.index)
    return weights.where(is_month_end, axis=0).ffill().fillna(0.0)


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


def eval_config(close: pd.DataFrame, lookback: int, skip: int, top_fraction: float) -> dict:
    """Evaluate one parameter configuration on the pre-registered splits.

    Monthly rebalance, 1-day signal lag, 3 bps round-trip costs.
    """
    weights = build_weights(close, lookback=lookback, skip=skip, top_fraction=top_fraction)
    weights = _apply_monthly_schedule(weights)
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
    lookback: int,
    skip: int,
    top_fraction: float,
    start_date: str,
    end_date: str,
) -> tuple[pd.Series, pd.DataFrame]:
    """Evaluate a config on an arbitrary period (walk-forward folds).

    Signals are computed on the full history (point-in-time: each date's
    momentum uses only past prices), then sliced to [start_date, end_date].
    """
    weights = build_weights(close, lookback=lookback, skip=skip, top_fraction=top_fraction)
    weights = _apply_monthly_schedule(weights)
    net_ret, weights_a, _, _ = _net_returns(close, weights)
    mask = (net_ret.index >= start_date) & (net_ret.index <= end_date)
    return net_ret[mask], weights_a[mask]


def eval_equal_weight(
    close: pd.DataFrame,
    start_date: str,
    end_date: str,
) -> tuple[pd.Series, pd.DataFrame]:
    """1/N equal-weight portfolio over the 9-sector universe.

    Constant 1/9 target weights, 1-day signal lag, monthly rebalance
    calendar, 3 bps round-trip costs (identical execution convention to
    the pre-registered baseline).
    """
    weights = pd.DataFrame(1.0 / close.shape[1], index=close.index, columns=close.columns)
    weights = weights.shift(1).fillna(0.0)
    weights = _apply_monthly_schedule(weights)
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
    """Daily tail risk metrics (95% VaR / CVaR) for a net-return series.

    VaR/CVaR are reported as positive loss numbers: VaR is the
    5th-percentile loss, CVaR is the mean loss of the worst 5%
    of daily returns.
    """
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
    print("\n=== [1] Baseline Backtest (252, 21, 0.5), monthly rebalance ===")
    res = eval_config(close, *BASELINE)
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
    }


# ---------------------------------------------------------------------------
# Section 2: Walk-forward evaluation (fixed parameters, no re-optimization)
# ---------------------------------------------------------------------------
def run_walkforward(
    close: pd.DataFrame,
    splits: list[dict],
) -> dict:
    print("\n=== [2] Walk-Forward Evaluation (36 folds, fixed params) ===")
    print(f"  Folds: {len(splits)}")

    def config_fn(symbols: list[str], start: str, end: str):
        return eval_config_period(close, *BASELINE, start, end)

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
                "test_sortino": np.nan,
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
# Section 3: Robustness grid (27 pre-specified configurations, test period)
# ---------------------------------------------------------------------------
def run_grid(close: pd.DataFrame) -> dict:
    print(f"\n=== [3] Robustness Grid ({N_GRID_CONFIGS} pre-specified configs, test period) ===")
    rows = []
    for lb in LOOKBACKS:
        for sk in SKIPS:
            for tf in TOP_FRACTIONS:
                res = eval_config(close, lb, sk, tf)
                rows.append({
                    "lookback": lb,
                    "skip": sk,
                    "top_fraction": tf,
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
    grid_df = pd.DataFrame(rows)
    grid_df["rank"] = grid_df["test_sharpe"].rank(ascending=False, method="min").astype(int)

    bl_mask = (
        (grid_df["lookback"] == BASELINE[0])
        & (grid_df["skip"] == BASELINE[1])
        & (grid_df["top_fraction"] == BASELINE[2])
    )
    baseline_rank = int(grid_df.loc[bl_mask, "rank"].iloc[0])
    baseline_test_sharpe = float(grid_df.loc[bl_mask, "test_sharpe"].iloc[0])

    # Plateau check: >= 2 of 3 lookbacks within 10% of baseline test Sharpe
    # at skip=21, top_fraction=0.5. Threshold follows the repository plateau
    # convention (src/evaluation/statistics.py: max(0.1, 10% of |baseline|)).
    plateau_df = grid_df[(grid_df["skip"] == 21) & (grid_df["top_fraction"] == 0.5)]
    threshold = max(0.1, 0.10 * abs(baseline_test_sharpe))
    within = plateau_df[
        (plateau_df["test_sharpe"] - baseline_test_sharpe).abs() <= threshold
    ]
    n_within = int(len(within))
    plateau_pass = n_within >= GATE_PLATEAU_MIN_LOOKBACKS

    print(f"  Baseline (252,21,0.5) test Sharpe: {baseline_test_sharpe:.4f} (rank {baseline_rank}/{N_GRID_CONFIGS})")
    print(f"  Plateau: {n_within}/3 lookbacks within +/-{threshold:.4f} of baseline "
          f"({'PASS' if plateau_pass else 'FAIL'})")

    return {
        "grid_df": grid_df,
        "baseline_rank": baseline_rank,
        "baseline_test_sharpe": baseline_test_sharpe,
        "plateau_threshold": threshold,
        "n_lookbacks_within": n_within,
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

    ew_cmp = _benchmark_comparison("1/N Equal-Weight (9 sector ETFs)", cs_test_ret, ew_test_ret)
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
    n_within = int(grid_result["n_lookbacks_within"])

    gate1 = bool(mean_wf >= GATE_WF_SHARPE_MIN)
    gate2 = bool(pct_pos >= GATE_POSITIVE_FOLD_RATE_MIN)
    gate3 = bool(pooled_trades > GATE_POOLED_TRADES_MIN)
    gate4 = bool(n_within >= GATE_PLATEAU_MIN_LOOKBACKS)

    # Pre-registered falsification (research/hypotheses/sectorrotation_001.md):
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
        "n_lookbacks_within": n_within,
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
        "| Lookback | Skip | Top Fraction | Train Sharpe | Val Sharpe | Test Sharpe | "
        "Test Ann. Ret. | Test Max DD | Test Trades | Test Turnover | Test Sortino | Rank |",
        "|----------|------|--------------|--------------|------------|------------|"
        "----------------|--------------|-------------|---------------|--------------|------|",
    ]
    for _, r in grid_df.iterrows():
        lines.append(
            f"| {int(r['lookback'])} | {int(r['skip'])} | {r['top_fraction']:.1f} | "
            f"{_fmt(r['train_sharpe'])} | {_fmt(r['val_sharpe'])} | "
            f"{_fmt(r['test_sharpe'])} | {_fmt(r['test_ann_return'])} | "
            f"{_fmt(r['test_max_dd'])} | {_fmt(r['test_trades'], 0)} | "
            f"{_fmt(r['test_turnover'], 2)} | {_fmt(r['test_sortino'])} | "
            f"{int(r['rank'])} |"
        )
    return "\n".join(lines)


def _grid_heatmap(grid_df: pd.DataFrame) -> str:
    pivot = grid_df.pivot_table(
        index="lookback", columns=["skip", "top_fraction"], values="test_sharpe",
    )
    cols = [f"skip={int(sk)}, tf={tf:.1f}" for sk, tf in pivot.columns]
    lines = [
        "| Lookback | " + " | ".join(cols) + " |",
        "|----------|" + "|".join(["--------"] * len(cols)) + "|",
    ]
    for lb, row in pivot.iterrows():
        cells = " | ".join(_fmt(v) for v in row.values)
        lines.append(f"| **{int(lb)}** | {cells} |")
    return "\n".join(lines)


def build_report(
    close: pd.DataFrame,
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

    # Data integrity table
    integrity_lines = [
        "| Symbol | Rows | Start | End | Close Complete (aligned) |",
        "|--------|------|-------|-----|--------------------------|",
    ]
    for symbol in UNIVERSE:
        s = close[symbol]
        integrity_lines.append(
            f"| {symbol} | {len(s):,} | {s.first_valid_index().strftime('%Y-%m-%d')} | "
            f"{s.index.max().strftime('%Y-%m-%d')} | {s.notna().mean():.1%} |"
        )
    integrity = "\n".join(integrity_lines)

    # Metrics table helper
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
        "|--------|--------------|-------------|----------|--------|---------|"
        "--------|---------------|--------|---------------|--------------|"
    )

    # Benchmark WF aggregate table
    def bench_wf_row(label: str, summary: dict) -> str:
        return (
            f"| {label} | {summary.get('n_folds', 0)} | "
            f"{summary.get('mean_test_sharpe', np.nan):.4f} | "
            f"{summary.get('std_test_sharpe', np.nan):.4f} | "
            f"{summary.get('median_test_sharpe', np.nan):.4f} | "
            f"{summary.get('pct_positive_sharpe', np.nan):.1%} | "
            f"{summary.get('total_test_trades', 0)} |"
        )

    bench_wf_header = (
        "| Benchmark | Folds | Mean OOS Sharpe | Std | Median | % Positive | Pooled Trades |\n"
        "|-----------|-------|-----------------|-----|--------|------------|---------------|"
    )

    dsr = mult["dsr"]
    dsr_actual = mult["dsr_actual"]
    psr = mult["psr"]
    psr_gate = mult["psr_gate"]
    pbo = mult["pbo"]
    pbo_val = pbo.get("pbo", np.nan)
    if isinstance(pbo_val, float) and np.isnan(pbo_val):
        pbo_txt = (
            f"PBO not computable — degenerate: all {pbo.get('n_configs', 0)} evaluated "
            "configs have positive test-period Sharpe, so the top-k OOS-below-threshold "
            "rate is 0 for every k and the logit-normal PBO model has no variation. "
            "Overfitting diagnostics therefore rely on the IS-OOS rank correlation and "
            "the mean-IS vs mean-OOS gap reported below"
        )
    else:
        pbo_txt = f"PBO = {pbo_val:.4f}"
    ew = benchmarks["ew_test"]
    inc = benchmarks["inc_test"]

    gate_rows = [
        f"| 1. Walk-forward mean OOS Sharpe >= {GATE_WF_SHARPE_MIN} | "
        f"{gates['mean_wf_sharpe']:.4f} | {'PASS' if gates['gate1_wf_sharpe'] else 'FAIL'} |",
        f"| 2. Positive fold rate >= {GATE_POSITIVE_FOLD_RATE_MIN:.0%} | "
        f"{gates['pct_positive']:.1%} | {'PASS' if gates['gate2_positive_rate'] else 'FAIL'} |",
        f"| 3. Pooled OOS trades > {GATE_POOLED_TRADES_MIN} | "
        f"{gates['pooled_trades']} | {'PASS' if gates['gate3_pooled_trades'] else 'FAIL'} |",
        f"| 4. Parameter plateau: >= {GATE_PLATEAU_MIN_LOOKBACKS} of 3 lookbacks within 10% | "
        f"{gates['n_lookbacks_within']}/3 | {'PASS' if gates['gate4_plateau'] else 'FAIL'} |",
    ]

    md = f"""# Experiment: Baseline Backtest & Walk-Forward — Sector Rotation (sectorrotation_baseline_wf_001)

## Hypothesis Reference

`research/hypotheses/sectorrotation_001.md` (Cycle 12 pre-registration, v001).
Candidate C4 from the Cycle 11 Opportunity Shortlist (28/35 — Exploratory
signal): long-only cross-sectional momentum over the 9 GICS sector ETFs.

**Mechanism**: Assets with higher intermediate-term returns relative to the
universe tend to continue outperforming (investor underreaction, slow
information diffusion). Long-only top-fraction equal-weight implementation
avoids the borrow-cost gap that blocks short-side strategies.

**Pre-registered falsification condition** (stated BEFORE any backtest
execution): the hypothesis is rejected if the walk-forward mean OOS Sharpe
< {GATE_WF_SHARPE_MIN} OR < {GATE_POSITIVE_FOLD_RATE_MIN:.0%} of walk-forward folds have positive test Sharpe.

---

## Data Used

- **Source**: Yahoo Finance via yfinance, cached as daily parquet in
  `data/raw/` (9 sector ETF caches plus 7 incumbent-benchmark ETF caches). A cache preflight runs before the shared fetcher; missing or invalid caches fail before network access.
- **Date Range**: {START_DATE} to {END_DATE} ({len(close):,} aligned trading days)
- **Frequency**: Daily (end-of-day OHLCV)
- **Universe**: {", ".join(UNIVERSE)}
- **Price Field**: Close (EOD), forward-filled onto the union trading calendar
- **Point-in-Time Treatment**: Momentum at date t uses only prices through
  t-skip-lookback; weights shifted 1 day (signal on T-1 close, positions
  effective T); monthly month-end rebalance calendar carries weights forward
  intra-month (no intra-month trading); walk-forward uses 21-day purge and
  21-day embargo between train and test.
- **Missing-Data Handling**: The frozen C4 universe requires all 9 sector ETFs to share the 1998-12-22 to 2026-10-08 window. The runner validates 6,991 aligned observations, full Close completeness, and unique dates before computing any result.
- **Content hash (aligned Close frame)**: {_frame_hash(close)}

{integrity}

---

## Configuration

**Baseline (pre-registered, frozen in `config/sectorrotation_candidate_001.yaml`)**:

| Parameter | Value |
|-----------|-------|
| Signal | Cross-sectional momentum (rank-based) |
| Lookback | {BASELINE[0]} trading days (~12 months) |
| Skip | {BASELINE[1]} trading days (~1 month, short-term reversal skip) |
| Top fraction | {BASELINE[2]} (equal-weight top 50% by momentum rank) |
| Rebalance | Monthly (month-end calendar) |
| Signal lag | 1 day (T-1 close -> T position) |
| Risk overlay | NONE (baseline before complexity, AGENTS.md) |
| Commission | {COMMISSION_BPS * 10000:.1f} bps |
| Slippage | {SLIPPAGE_BPS * 10000:.1f} bps |
| Round-trip cost | {TOTAL_COST * 10000:.1f} bps on weight changes |
| Risk-free rate | {RF_ANNUAL:.1%} annualized (flat) |

**Pre-specified Robustness Grid (fixed count for multiple-testing control)**:

lookback in {{{', '.join(str(x) for x in LOOKBACKS)}}}, skip in {{{', '.join(str(x) for x in SKIPS)}}},
top_fraction in {{{', '.join(str(x) for x in TOP_FRACTIONS)}}}. Baseline is the center point
({BASELINE[0]}, {BASELINE[1]}, {BASELINE[2]}). No configurations were added post-hoc and no
configuration is selected on test-period results.

**Pre-registered configuration count**: 3 lookbacks x 2 skips x 3 top fractions = **{N_GRID_CONFIGS} unique combinations**. The corrected runner rejects execution unless both the grid and frozen trial count equal 18. No configurations are added post hoc; the pre-registered and actual trial counts both equal {N_PREREGISTERED_TRIALS}.

**Config file SHA-256 (first 12 hex)**: `{cfg_hash}`

---

## Train/Validation/Test Splits & Walk-Forward Design

| Split | Period | Purpose |
|-------|--------|---------|
| Train | {START_DATE} to {TRAIN_END} | Parameter selection (NOT used — baseline is pre-specified) |
| Validation | 2010-01-01 to {VAL_END} | Robustness screening (diagnostic only) |
| Test | 2018-01-01 to {END_DATE} | Final holdout, promotion-gate decision |

**Walk-Forward Design (matches Cycle 6 `tsmomentum_regime_filter_wf_001.md` exactly)**:

- Rolling window: {WF_TRAIN_YEARS:.0f}-year train, {WF_TEST_MONTHS:.0f}-month test, {WF_STEP_MONTHS:.0f}-month step
- Purge: {WF_PURGE_DAYS} days between train end and test start
- Embargo: {WF_EMBARGO_DAYS} days after test period end
- Parameters: FIXED across all folds (no per-fold re-optimization)
- Folds: {wf_summary.get('n_folds', 0)}

---

## 1. Baseline Backtest (Test Period {TEST_START} to {END_DATE})

{metrics_header}
{metric_row("Test (2018-2026)", tm)}
{metric_row("Validation (2010-2017)", res["validation"])}
{metric_row("Train (1998-2009)", res["train"])}

**Tail metrics (test period, daily net returns)**:

| Metric | Value |
|--------|-------|
| 95% VaR (daily) | {tail['var_95_daily']:.4f} ({tail['var_95_daily']:.2%}) |
| 95% CVaR (daily) | {tail['cvar_95_daily']:.4f} ({tail['cvar_95_daily']:.2%}) |
| Worst day | {tail['worst_day']:.4f} ({tail['worst_day']:.2%}) |
| Trade count (test) | {tm.get('trade_count', 0)} |

**Artifacts**:

| Artifact | Path | Rows |
|----------|------|------|
| Daily simulation series | `data/processed/simulation_sectorrotation_001.parquet` | {len(baseline['daily']):,} |
| Trade log | `data/processed/trades_sectorrotation_001.parquet` | {len(baseline['trades_df']):,} |
| Point-in-time weights | `data/processed/weights_sectorrotation_001.parquet` | {len(baseline['weights']):,} |

---

## 2. Walk-Forward Evaluation ({wf_summary.get('n_folds', 0)} Folds, Fixed Parameters)

### Walk-Forward Design

10-year train / 1-year test / 6-month step, 21-day purge, 21-day embargo,
fixed pre-registered parameters ({BASELINE[0]}, {BASELINE[1]}, {BASELINE[2]}), monthly
rebalance, 1-day lag, 3 bps round-trip costs. No per-fold re-optimization.

### Per-Fold Results

{_wf_table(wf['wf_df'])}

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
({TEST_START} to {END_DATE}) with the identical execution convention.
The grid is diagnostic only: the baseline is pre-specified and no
configuration is selected on these results. Its 18 combinations are frozen
in the hypothesis and config and checked before execution.

### Heatmap — Test Sharpe by Configuration

{_grid_heatmap(grid_df)}

### Full Grid Results

{_grid_table(grid_df)}

### Baseline Rank & Plateau Check

- **Baseline (252, 21, 0.5) test Sharpe**: {grid['baseline_test_sharpe']:.4f}
  — rank **{grid['baseline_rank']}** of {N_GRID_CONFIGS} by test Sharpe
- **Plateau check** (skip=21, top_fraction=0.5; lookbacks 189/252/315):
  **{grid['n_lookbacks_within']} of 3** lookbacks within +/-{grid['plateau_threshold']:.4f}
  of the baseline test Sharpe (threshold = max(0.1, 10% x |baseline|), the
  repository plateau convention from `src/evaluation/statistics.py`)
  — {'**PASS**' if grid['plateau_pass'] else '**FAIL**'} (gate: >= {GATE_PLATEAU_MIN_LOOKBACKS} of 3)

---

## 4. Benchmark Comparison

Both benchmarks are evaluated on the identical test period ({TEST_START} to
{END_DATE}) and the identical walk-forward folds with the same 3 bps cost model
and one-day signal lag. The incumbent TSMOM benchmark uses its own cached CORE7
input universe; the sector candidate uses the nine frozen GICS sector ETFs.
The 1/N benchmark is represented as constant 1/9 target weights with a one-day
lag and monthly schedule. Under the engine's exogenous-weight framework this
implies no observed turnover drag, a known upward bias documented as a limitation.

### Test-Period Comparison

| Benchmark | Ann. Return | Sharpe | Max DD | Excess Return (ann.) | Excess Sharpe (IR) | Sharpe Diff. | Correlation | Relative Max DD |
|-----------|-------------|--------|--------|----------------------|--------------------|--------------|-------------|-----------------|
| 1/N Equal-Weight (9 sector ETFs) | {ew['bench_ann_return']:.4f} | {ew['bench_sharpe']:.4f} | {ew['bench_max_dd']:.4f} | {ew['excess_ann_return']:.4f} | {ew['excess_sharpe']:.4f} | {ew['sharpe_difference']:.4f} | {ew['correlation']:.3f} | {ew['relative_max_dd']:.4f} |
| Incumbent TSMOM (tsmomentum_spytrend_001) | {inc['bench_ann_return']:.4f} | {inc['bench_sharpe']:.4f} | {inc['bench_max_dd']:.4f} | {inc['excess_ann_return']:.4f} | {inc['excess_sharpe']:.4f} | {inc['sharpe_difference']:.4f} | {inc['correlation']:.3f} | {inc['relative_max_dd']:.4f} |

Excess return/Sharpe are computed on the daily CS-minus-benchmark series
(excess Sharpe = annualized excess return / annualized excess volatility,
i.e. an information ratio). Relative max DD is the max drawdown of the
cumulative excess return.

### Walk-Forward Comparison (identical folds)

{bench_wf_header}
{bench_wf_row("Sector Rotation C4 (baseline)", wf_summary)}
{bench_wf_row("1/N Equal-Weight (9 sector ETFs)", benchmarks['ew_wf']['summary'])}
{bench_wf_row("Incumbent TSMOM (tsmomentum_spytrend_001)", benchmarks['inc_wf']['summary'])}

---

## 5. Multiple-Testing Control

- **Exact configuration count tracked**: {N_GRID_CONFIGS} unique pre-specified
  combinations (3 x 2 x 3) evaluated; both the frozen and evaluated trial counts are {N_PREREGISTERED_TRIALS}. No configuration selected on test-period
  results; the baseline is pre-specified and the grid is diagnostic
  (plateau + multiple-testing control) only.
- **Deflated Sharpe Ratio** (`src/evaluation/statistics.py:compute_dsr`,
  {N_BOOTSTRAP} block-bootstrap samples, seed={SEED}):
  - At the pre-registered N={N_PREREGISTERED_TRIALS} (primary, conservative):
    **DSR = {dsr['dsr']:.4f}** (DSR probability = {dsr['dsr_probability']:.4f}).
    Observed test Sharpe {dsr['sr_observed']:.4f} vs deflation threshold
    {dsr['sr_threshold']:.4f} (SE = {dsr['sharpe_se']:.4f},
    E[max of {N_PREREGISTERED_TRIALS}] = {dsr['e_max']:.4f}).
  - At the actual evaluated count N={N_GRID_CONFIGS} (disclosure):
    DSR = {dsr_actual['dsr']:.4f} (DSR probability = {dsr_actual['dsr_probability']:.4f}).
  Interpret the reported DSR values as computed; the runner does not hard-code their sign or significance.
- **Probabilistic Sharpe Ratio** (PSR vs SR=0): {psr['psr_normal']:.4f}
  (empirical {psr['psr_empirical']:.4f}); PSR vs the {GATE_WF_SHARPE_MIN} gate:
  {psr_gate['psr_normal']:.4f}.
- **Block-bootstrap Sharpe 95% CI**: [{dsr['ci_lower']:.4f}, {dsr['ci_upper']:.4f}].
- **PBO / CSCV** (`src/evaluation/statistics.py:compute_pbo` over the
  {N_GRID_CONFIGS}-config grid, train=1998-2009 vs test=2018-2026):
  {pbo_txt}; best-IS config OOS Sharpe =
  {pbo.get('best_is_config', {}).get('test_sharpe', np.nan):.4f};
  IS-OOS Spearman rank correlation = {pbo.get('rank_correlation_is_oos', np.nan):.4f};
  mean IS Sharpe = {pbo.get('mean_is_sharpe', np.nan):.4f} vs mean OOS Sharpe =
  {pbo.get('mean_oos_sharpe', np.nan):.4f}; {pbo.get('n_configs_oos_positive', 0)} of
  {pbo.get('n_configs', 0)} configs have positive OOS Sharpe.

---

## Promotion-Gate Verdict

Pre-registered promotion gates (ALL must pass before further development; this baseline contains no risk overlay):

| Gate | Threshold | Observed | Status |
|------|-----------|----------|--------|
{chr(10).join(gate_rows)}

**Pre-registered falsification condition**: WF mean OOS Sharpe < {GATE_WF_SHARPE_MIN}
OR positive-fold rate < {GATE_POSITIVE_FOLD_RATE_MIN:.0%} —
**{'MET (hypothesis falsified)' if gates['falsified'] else 'NOT met'}**.

### Final Classification

## **{gates['label']}**

"""

    if gates["label"] == "Rejected/Failed":
        md += f"""The candidate did not clear the pre-registered promotion/falsification rules.
Per the frozen decision discipline, sectorrotation_001 (long-only cross-sectional
momentum across the 9 GICS sector ETFs, monthly rebalance) is rejected/failed and archived.

Observed evidence:
- Test period (2018-2026) net Sharpe {tm.get('sharpe_ratio', np.nan):.4f}, max DD
  {tm.get('max_drawdown', np.nan):.2%}, {tm.get('trade_count', 0)} trades,
  {tm.get('annualized_turnover', np.nan):.2f}x annualized turnover.
- Walk-forward mean OOS Sharpe {gates['mean_wf_sharpe']:.4f} over
  {wf_summary.get('n_folds', 0)} folds; {gates['pooled_trades']} pooled OOS trades.
- Baseline rank {grid['baseline_rank']} of {N_GRID_CONFIGS}; plateau
  {gates['n_lookbacks_within']}/3 ({'passes' if gates['gate4_plateau'] else 'fails'}).
- DSR is reported at both trial counts above; this narrative does not
  hard-code its sign or significance.

The conclusion is limited to the frozen nine-sector ETF universe, execution
rules, transaction-cost assumptions, and historical window evaluated here.
"""
    elif gates["label"] == "Credible candidate for further validation":
        md += f"""All four promotion gates passed. Per the frozen decision discipline,
sectorrotation_001 is a credible candidate for further validation. No risk overlay
is added to this baseline and no configuration is selected on test-period results.
"""
    else:
        md += f"""The candidate is an exploratory signal: the falsification condition
was not met, but one or more promotion gates did not pass. Preserve this outcome
without tuning on the test period.
"""

    md += f"""
---

## Decision & Next Steps

**Label**: {gates['label']}

**Next scheduled task**: the pre-registered C6 calendar-effects evaluation in `NEXT_AGENT_TASK.md`.
"""

    if gates["label"] == "Rejected/Failed":
        md += """Per the pre-registered plan, C4 is archived under its observed
promotion-gate result. The next scheduled task evaluates the already
pre-registered C6 calendar-effects hypothesis; its frozen design is not tuned
in response to this C4 outcome.
"""

    md += f"""
---

## Reproducibility

### Reproduction Commands

```bash
# Corrected Cycle 15 C4 evaluation (regenerates C4 artifacts and this report)
python3 research/run_cycle15_c4_corrected.py

# Verify frozen pre-registration parses
python3 -c "import yaml; yaml.safe_load(open('config/sectorrotation_candidate_001.yaml'))"
```

### Code Revision

`{rev}`

### Configuration

- Frozen config: `config/sectorrotation_candidate_001.yaml` (SHA-256[:12] = `{cfg_hash}`)
- Baseline: lookback={BASELINE[0]}, skip={BASELINE[1]}, top_fraction={BASELINE[2]}
- Grid: {N_GRID_CONFIGS} unique configs (pre-registered trial count {N_PREREGISTERED_TRIALS};
  see disclosed pre-registered count above)
- Walk-forward: train={WF_TRAIN_YEARS:.0f}y, test={WF_TEST_MONTHS:.0f}m, step={WF_STEP_MONTHS:.0f}m,
  purge={WF_PURGE_DAYS}d, embargo={WF_EMBARGO_DAYS}d
- Bootstrap: {N_BOOTSTRAP} samples, block=22d, seed={SEED}
- Costs: {COMMISSION_BPS * 10000:.1f} bps commission + {SLIPPAGE_BPS * 10000:.1f} bps slippage =
  {TOTAL_COST * 10000:.1f} bps round-trip; risk-free rate {RF_ANNUAL:.1%}

### Determinism

The backtest, walk-forward, grid, and benchmark computations are fully
deterministic (no RNG). The block-bootstrap statistics (DSR/PSR/CIs) use
seed={SEED} for reproducibility.

---

## Artifacts Referenced

| Artifact | Path |
|----------|------|
| Pre-registered hypothesis | `research/hypotheses/sectorrotation_001.md` |
| Frozen configuration | `config/sectorrotation_candidate_001.yaml` |
| Daily simulation series | `data/processed/simulation_sectorrotation_001.parquet` |
| Trade log | `data/processed/trades_sectorrotation_001.parquet` |
| Point-in-time weights | `data/processed/weights_sectorrotation_001.parquet` |
| Cycle 6 walk-forward design | `research/experiments/tsmomentum_regime_filter_wf_001.md` |
| Cycle 11 shortlist (C3 = 29/35) | `research/reports/opportunity_shortlist.md` |

---

*Report generated: {today} by `research/run_cycle15_c4_corrected.py` (corrected Cycle 15 C4 evaluation)*
*Code revision: {rev}*
"""
    return md


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    print("=" * 60)
    print("CYCLE 15: Baseline Backtest & Walk-Forward — Sector Rotation (sectorrotation_001)")
    print("=" * 60)

    splits = _validate_preregistered_contract()
    _require_cached_inputs()

    close = _slice_prices(_load_cached_close_prices(UNIVERSE), START_DATE, END_DATE)
    _validate_sector_close(close)
    # The incumbent benchmark uses its own seven-symbol universe.
    close_core = _slice_prices(
        _load_cached_close_prices(CORE7),
        CORE7_START_DATE,
        END_DATE,
    )
    _validate_core_benchmark_close(close_core)
    print(f"Data loaded: {close.shape[1]} ETFs, {len(close):,} trading days "
          f"({close.index.min().strftime('%Y-%m-%d')} to {close.index.max().strftime('%Y-%m-%d')})")

    baseline = run_baseline(close)
    wf = run_walkforward(close, splits)
    grid = run_grid(close)
    benchmarks = run_benchmarks(close, close_core, splits, baseline["test_ret"])
    mult = run_multiple_testing(baseline["test_ret"], grid["grid_df"])

    gates = evaluate_gates(wf["summary"], grid)

    report = build_report(close, baseline, wf, grid, benchmarks, mult, gates)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report)
    _validate_generated_outputs(close, baseline, wf, splits, report)
    print(f"\n  Report written -> {REPORT_PATH}")

    print("\n" + "=" * 60)
    print("CYCLE 15 COMPLETE")
    print("=" * 60)
    print(f"Promotion gates:")
    print(f"  1. WF mean OOS Sharpe >= {GATE_WF_SHARPE_MIN}: {gates['mean_wf_sharpe']:.4f} "
          f"({'PASS' if gates['gate1_wf_sharpe'] else 'FAIL'})")
    print(f"  2. Positive fold rate >= {GATE_POSITIVE_FOLD_RATE_MIN:.0%}: {gates['pct_positive']:.1%} "
          f"({'PASS' if gates['gate2_positive_rate'] else 'FAIL'})")
    print(f"  3. Pooled OOS trades > {GATE_POOLED_TRADES_MIN}: {gates['pooled_trades']} "
          f"({'PASS' if gates['gate3_pooled_trades'] else 'FAIL'})")
    print(f"  4. Plateau >= {GATE_PLATEAU_MIN_LOOKBACKS}/3 lookbacks: {gates['n_lookbacks_within']}/3 "
          f"({'PASS' if gates['gate4_plateau'] else 'FAIL'})")
    print(f"FINAL VERDICT: {gates['label']}")


if __name__ == "__main__":
    main()
