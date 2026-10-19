#!/usr/bin/env python3
"""Long-sample feasibility backtest for the frozen sectorrotation_001 candidate (Cycle 869).

Read-only with respect to market data: the script reads the committed raw cache
(``data/raw/*.parquet``), writes exactly one report under ``research/reports/``
and touches nothing else.

It reuses the pattern of ``research/promotion_feasibility_backtest.py`` (sample
definition -> canonical metrics -> PSR -> gate table -> decision), but applies it
to the pre-registered ``sectorrotation_001`` candidate:

* the frozen configuration is ``config/sectorrotation_candidate_001.yaml``
  (9 GICS sector ETFs, lookback 252, skip 21, top_fraction 0.5, month-end
  rebalancing with a 1-day signal lag, 3 bps round-trip);
* the repository engine (``src/backtest/engine.py``) accepts a
  ``rebalance_freq`` argument that it never uses -- it re-ranks the universe
  every day -- so the config-faithful month-end rebalance is implemented here
  and the engine path is reported next to it as the deviation measurement;
* the incumbent's paper-trading gate table (``config/promotion_gates.yaml``)
  has one gate (``regime_flips``) that a candidate without a paper-trading
  record cannot satisfy, so it is reported as NOT APPLICABLE and the decision
  is given under three explicit readings instead of a single hidden one;
* the candidate's own pre-registered falsification condition
  (``research/hypotheses/sectorrotation_001.md``) is walk-forward based, so the
  36 pre-registered folds are evaluated as well.

Everything is deterministic: the only stochastic component is the seeded
moving-block bootstrap of the PSR (seed 20240101 for the gate PSR, seed 42 for
the Deflated Sharpe Ratio, as documented in the respective configs).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.backtest.engine import get_cost_params, run_backtest
from src.data.yfinance_fetcher import fetch_universe
from src.evaluation.sharpe import backtest_sharpe_ratio, sharpe_ratio
from src.evaluation.statistics import compute_dsr, compute_psr
from src.evaluation.utils import max_drawdown
from src.evaluation.walkforward import generate_walkforward_splits
from src.features.momentum import compute_momentum, select_top_decile

CONFIG_CAND = REPO_ROOT / "config" / "sectorrotation_candidate_001.yaml"
CONFIG_GATES = REPO_ROOT / "config" / "promotion_gates.yaml"
RAW_DIR = REPO_ROOT / "data" / "raw"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
REPORT_MD = REPORTS_DIR / "sectorrotation_long_sample_feasibility_001.md"

# The incumbent's recorded backtest baseline, kept so this report can be
# compared like-for-like with research/reports/promotion_feasibility_backtest_001.md.
PSR_TARGET_COMPARABLE = 1.4178
# The candidate's own promotion threshold (canonical scale). This is the PSR
# that answers the promotion question for a candidate with no recorded backtest
# baseline: P(true Sharpe > the gate threshold).
PSR_TARGET_CANDIDATE = 0.9
PSR_SEED = 20240101
PSR_N_BOOTSTRAP = 1000
PSR_BLOCK_SIZE = 22
DSR_N_CONFIGS = 18
DSR_SEED = 42
WF_EXPECTED_FOLDS = 36
# Pre-registered in research/hypotheses/sectorrotation_001.md (data integrity
# verified at freeze time, 2026-10-12).
ALIGNED_FRAME_HASH_PREFIX = "5e2d48e6579a53cd"
PRE_REGISTERED_FIRST_SIGNAL = "2000-01-24"


# ----------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def load_yaml(path: Path) -> Any:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def content_hash(frame: pd.DataFrame) -> str:
    """Content hash of a frame: sha256 over the pandas row hashes."""
    return hashlib.sha256(pd.util.hash_pandas_object(frame).values.tobytes()).hexdigest()


def clean(returns: pd.Series) -> pd.Series:
    s = pd.Series(returns).astype(float)
    return s.replace([np.inf, -np.inf], np.nan).dropna()


def git_revision() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:  # noqa: BLE001 - provenance only, never fails the run
        pass
    return "unknown"


def month_end_dates(index: pd.DatetimeIndex) -> list[pd.Timestamp]:
    """Last trading date of every calendar month present in *index*."""
    last: dict[str, pd.Timestamp] = {}
    for d, key in zip(index, index.strftime("%Y-%m")):
        last[key] = d
    return [last[k] for k in sorted(last)]


# ----------------------------------------------------------------------
# Strategy construction
# ----------------------------------------------------------------------
def build_monthly_weights(
    close: pd.DataFrame,
    mask: pd.DataFrame,
    month_ends: list[pd.Timestamp],
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Month-end rebalanced, 1-day-lagged, equal-weight top-``top_fraction`` weights.

    The signal is formed on the last trading day of a month and the resulting
    positions are effective from the next trading day, which is the frozen
    configuration's ``rebalance_schedule: month-end`` + ``signal_lag_days: 1``.
    Months whose signal is not yet defined carry no positions (point-in-time,
    no back-fill).
    """
    idx = close.index
    weights = pd.DataFrame(0.0, index=idx, columns=close.columns)
    segments: list[dict[str, Any]] = []

    for d in month_ends[:-1]:
        sel = mask.loc[d]
        n_selected = int(sel.sum())
        if n_selected == 0:
            continue
        eff_pos = int(idx.searchsorted(d, side="right"))
        if eff_pos >= len(idx):
            break
        eff = idx[eff_pos]
        segments.append(
            {
                "signal_date": d,
                "effective_date": eff,
                "n_selected": n_selected,
                "weights": sel.astype(float).to_numpy() / n_selected,
            }
        )

    for j, seg in enumerate(segments):
        start = int(idx.get_loc(seg["effective_date"]))
        end = int(idx.get_loc(segments[j + 1]["effective_date"])) if j + 1 < len(segments) else len(idx)
        weights.iloc[start:end, :] = seg["weights"]

    return weights, segments


def portfolio_returns(
    close: pd.DataFrame,
    weights: pd.DataFrame,
    cost_per_trade: float,
) -> tuple[pd.Series, pd.Series]:
    """Net-of-cost portfolio returns and the per-session turnover series."""
    daily_ret = close.pct_change().fillna(0.0)
    port_ret = (weights * daily_ret).sum(axis=1)
    turnover = weights.diff().abs().sum(axis=1).fillna(0.0)
    return port_ret - turnover * cost_per_trade, turnover


def compute_stats(
    net_ret: pd.Series,
    weights: pd.DataFrame,
    turnover: pd.Series,
    sample: pd.Index,
    cost_per_trade: float,
) -> dict[str, Any]:
    """Metrics for one sample of a strategy path (all series are pre-sliced)."""
    r = clean(net_ret.loc[sample])
    w = weights.loc[r.index]
    t = turnover.loc[r.index]
    n = len(r)
    if n < 2:
        return {"sessions": int(n)}

    cum = (1.0 + r).cumprod()
    dd = (cum / cum.expanding().max()) - 1.0
    tail = r.iloc[-63:]
    tail_cum = (1.0 + tail).cumprod()
    tail_dd = (tail_cum / tail_cum.expanding().max()) - 1.0
    gross = r + t * cost_per_trade
    gross_profit = float(gross[gross > 0].sum())
    gross_loss = float(-gross[gross < 0].sum())
    trade_mask = t > 1e-10

    return {
        "sessions": int(n),
        "start_date": r.index[0].date().isoformat(),
        "end_date": r.index[-1].date().isoformat(),
        "sharpe_canonical": float(sharpe_ratio(r)),
        "sharpe_backtest_scale": float(backtest_sharpe_ratio(r)),
        "cagr": float((1.0 + r).prod() ** (252.0 / n) - 1.0),
        "annualized_vol": float(r.std(ddof=1) * np.sqrt(252)),
        "total_return": float(cum.iloc[-1] - 1.0),
        "max_drawdown": float(max_drawdown(r)),
        "rolling_63d_sharpe": float(sharpe_ratio(tail)),
        "rolling_63d_max_dd": float(tail_dd.min()),
        "trade_days": int(trade_mask.sum()),
        "turnover_total": float(t.sum()),
        "annualized_turnover": float(t.sum()) * 252.0 / n,
        "avg_exposure": float(w.abs().sum(axis=1).mean()),
        "profit_factor": float(gross_profit / gross_loss) if gross_loss > 0 else float("inf"),
        "best_day": float(r.max()),
        "worst_day": float(r.min()),
        "cost_drag_total": float((t * cost_per_trade).sum()),
    }


# ----------------------------------------------------------------------
# Gates and decision
# ----------------------------------------------------------------------
def _compare(threshold: float, comparison: str, value: float) -> bool:
    if comparison == "gte":
        return value >= threshold
    if comparison == "gt":
        return value > threshold
    if comparison == "lte":
        return value <= threshold
    if comparison == "lt":
        return value < threshold
    return value == threshold


def evaluate_gates(
    gates_cfg: dict[str, Any],
    values: dict[str, float],
    psr_value: float,
    regime_flips_applicable: bool,
) -> tuple[dict[str, Any], list[str], str, str]:
    """Evaluate the repository gate table; returns (gates, failed, decision, zone)."""
    failed: list[str] = []
    gate_results: dict[str, Any] = {}

    for g in gates_cfg["gates"]:
        name = g["name"]
        thr = float(g["threshold"])
        comp = g["comparison"]
        if name == "regime_flips" and not regime_flips_applicable:
            gate_results[name] = {
                "value": None,
                "threshold": thr,
                "comparison": comp,
                "pass": None,
                "status": "not_applicable",
                "note": (
                    "The candidate has no paper-trading record and no regime filter "
                    "(frozen config: risk_overlay.none = true), so this gate cannot be "
                    "satisfied or violated by a long-sample backtest."
                ),
            }
            continue
        if name == "psr":
            val = float(psr_value)
        else:
            val = float(values[name])
        ok = _compare(thr, comp, val)
        gate_results[name] = {
            "value": val,
            "threshold": thr,
            "comparison": comp,
            "pass": bool(ok),
            "status": "evaluated",
        }
        if not ok:
            failed.append(name)

    pgz = gates_cfg.get("psr_grey_zone", {})
    if "lower" in pgz and "upper" in pgz:
        if psr_value < float(pgz["lower"]):
            zone = "below_grey"
        elif psr_value < float(pgz["upper"]):
            zone = "grey_zone"
        else:
            zone = "above_grey"
    else:
        zone = "unknown"

    dm = gates_cfg.get("decision_mapping", {})
    sessions = int(values.get("track_record_length", 0))
    applicable = [g for g in gate_results.values() if g.get("status") != "not_applicable"]
    if sessions < 126:
        decision = dm.get("insufficient_track_record", "INCONCLUSIVE")
    elif all(g["pass"] for g in applicable):
        decision = dm.get("all_gates_pass", "GO")
    elif failed == ["psr"] and zone == "grey_zone":
        decision = dm.get("psr_grey_zone_and_only_psr_gate_fails", "INCONCLUSIVE")
    else:
        decision = dm.get("any_other_gate_fails", "NO-GO")

    return gate_results, failed, decision, zone


# ----------------------------------------------------------------------
# Walk-forward
# ----------------------------------------------------------------------
def evaluate_walkforward(
    net_ret: pd.Series,
    turnover: pd.Series,
    splits: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Per-fold out-of-sample metrics of a fixed-parameter strategy path.

    The parameters are fixed across folds (pre-registered design) and the
    weights are the ones of the full-history path, i.e. the fold windows are
    sliced from a continuously computed, point-in-time strategy rather than
    re-fitted per fold.
    """
    rows: list[dict[str, Any]] = []
    for i, sp in enumerate(splits):
        ts = pd.Timestamp(sp["test_start"], tz="UTC")
        te = pd.Timestamp(sp["test_end"], tz="UTC")
        sel = (net_ret.index >= ts) & (net_ret.index <= te)
        r = clean(net_ret[sel])
        if len(r) < 2:
            continue
        t = turnover.loc[r.index]
        cum = (1.0 + r).cumprod()
        dd = (cum / cum.expanding().max()) - 1.0
        rows.append(
            {
                "fold": i + 1,
                "train_start": sp["train_start"],
                "train_end": sp["train_end"],
                "test_start": sp["test_start"],
                "test_end": sp["test_end"],
                "test_sessions": int(len(r)),
                "test_sharpe": float(sharpe_ratio(r)),
                "test_cagr": float((1.0 + r).prod() ** (252.0 / len(r)) - 1.0),
                "test_max_dd": float(dd.min()),
                "test_trades": int((t > 1e-10).sum()),
                "test_positive": bool(sharpe_ratio(r) > 0),
            }
        )
    return rows


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main() -> int:
    cand = load_yaml(CONFIG_CAND)
    gates_cfg = load_yaml(CONFIG_GATES)

    universe = list(cand["universe"])
    signal = cand["signal"]
    cost_model = {k: float(v) for k, v in cand.get("cost_model", {}).items()}
    lookback = int(signal["lookback"])
    skip = int(signal["skip"])
    top_fraction = float(signal["top_fraction"])
    splits_cfg = cand["evaluation"]["splits"]
    train_end = pd.Timestamp(splits_cfg["train_end"], tz="UTC")
    val_end = pd.Timestamp(splits_cfg["validation_end"], tz="UTC")

    checks: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    # --- data integrity: every symbol must be cached (no network) ---
    missing = [s for s in universe if not (RAW_DIR / f"{s}.parquet").exists()]
    if missing:
        print(f"ERROR: missing cached raw files for {missing}", file=sys.stderr)
        return 1
    hashes_before = {s: sha256_file(RAW_DIR / f"{s}.parquet") for s in universe}

    # --- sample definition from the committed cache ---
    per_symbol = {}
    for s in universe:
        df = pd.read_parquet(RAW_DIR / f"{s}.parquet")
        per_symbol[s] = {
            "rows": int(len(df)),
            "first": df.index.min().date().isoformat(),
            "last": df.index.max().date().isoformat(),
            "close_nan": int(df["Close"].isna().sum()),
            "duplicate_dates": int(df.index.duplicated().sum()),
        }
    start = max(pd.Timestamp(v["first"]) for v in per_symbol.values())
    end = min(pd.Timestamp(v["last"]) for v in per_symbol.values())

    check(
        "raw_cache_present",
        True,
        f"{len(universe)}/{len(universe)} sector parquet files present in data/raw (no network fetch possible).",
    )

    # --- aligned price frame (cache only) ---
    data = fetch_universe(universe, start.date().isoformat(), end.date().isoformat(), force=False)
    close = data.xs("Close", level=0, axis=1)
    close = close.ffill().dropna(how="all")
    aligned_hash = content_hash(close)

    check(
        "aligned_frame_shape",
        close.shape == (6991, 9),
        f"aligned Close frame is {close.shape[0]} x {close.shape[1]} (expected 6991 x 9).",
    )
    check(
        "aligned_frame_no_missing",
        bool(close.isna().sum().sum() == 0),
        f"aligned Close frame has {int(close.isna().sum().sum())} missing values.",
    )
    check(
        "aligned_frame_matches_preregistered_hash",
        aligned_hash.startswith(ALIGNED_FRAME_HASH_PREFIX),
        f"aligned-frame content hash {aligned_hash[:16]} (pre-registered {ALIGNED_FRAME_HASH_PREFIX}).",
    )
    check(
        "sample_matches_preregistered_window",
        start.date().isoformat() == cand.get("history_start")
        and end.date().isoformat() == per_symbol[universe[0]]["last"],
        f"sample {start.date().isoformat()}..{end.date().isoformat()} matches the frozen history_start "
        f"{cand.get('history_start')} and the cached last session.",
    )

    # --- cost model ---
    commission_bps, slippage_bps = get_cost_params()
    cost_per_trade = commission_bps + slippage_bps
    check(
        "cost_model_matches_frozen_config",
        abs(commission_bps * 10000 - cost_model["commission_bps"]) < 1e-9
        and abs(slippage_bps * 10000 - cost_model["slippage_bps"]) < 1e-9
        and abs(cost_per_trade * 10000 - cost_model["total_round_trip_bps"]) < 1e-9,
        f"engine cost model {commission_bps*10000:.1f}+{slippage_bps*10000:.1f} bps "
        f"= {cost_per_trade*10000:.1f} bps round-trip equals the frozen config.",
    )

    # --- signal and weights (config-faithful, month-end rebalance) ---
    momentum = compute_momentum(close, lookback=lookback, skip=skip)
    mask = select_top_decile(momentum, top_fraction=top_fraction)
    month_ends = month_end_dates(close.index)
    weights, segments = build_monthly_weights(close, mask, month_ends)
    net_ret, turnover = portfolio_returns(close, weights, cost_per_trade)

    first_signal = momentum.dropna(how="all").index.min()
    invested = weights.sum(axis=1) > 0
    first_invested = invested[invested].index.min()
    check(
        "warmup_matches_preregistered_signal_date",
        first_signal.date().isoformat() == PRE_REGISTERED_FIRST_SIGNAL,
        f"first date with a valid momentum cross-section is {first_signal.date().isoformat()} "
        f"(pre-registered {PRE_REGISTERED_FIRST_SIGNAL}).",
    )
    check(
        "no_positions_before_warmup",
        bool((~invested.loc[invested.index < first_invested]).all()),
        f"no position is held before {first_invested.date().isoformat()} "
        f"({int((~invested).sum())} pre-warmup sessions carry zero exposure).",
    )

    # point-in-time check of the monthly construction: every segment's weights
    # must equal the equal-weight of the mask at its own signal date, and the
    # effective date must be strictly after the signal date.
    pit_ok = True
    pit_detail = []
    for seg in segments:
        expected = mask.loc[seg["signal_date"]].astype(float).to_numpy() / seg["n_selected"]
        actual = weights.loc[seg["effective_date"]].to_numpy()
        if not np.allclose(expected, actual, atol=1e-12):
            pit_ok = False
            pit_detail.append(f"segment at {seg['signal_date'].date()} mismatch")
        if not seg["effective_date"] > seg["signal_date"]:
            pit_ok = False
            pit_detail.append(f"segment at {seg['signal_date'].date()} not lagged")
    check(
        "monthly_weights_point_in_time",
        pit_ok and len(segments) > 0,
        f"{len(segments)} rebalances; each segment equals the equal-weight of the mask at its own "
        f"signal date and becomes effective strictly after it"
        + ("" if pit_ok else f"; problems: {pit_detail[:3]}"),
    )

    # --- engine path (the pattern used by the incumbent feasibility script) ---
    engine_net, engine_weights, engine_metrics = run_backtest(
        symbols=universe,
        start_date=start.date().isoformat(),
        end_date=end.date().isoformat(),
        lookback=lookback,
        skip=skip,
        top_fraction=top_fraction,
        rebalance_freq=cand["signal"].get("rebalance_freq", "monthly"),
    )
    engine_turnover = engine_weights.diff().abs().sum(axis=1).fillna(0.0)
    engine_invested = engine_weights.sum(axis=1) > 0
    engine_first_invested = engine_invested[engine_invested].index.min()

    # --- samples ---
    full_index = close.index
    invested_index = close.index[invested]
    engine_invested_index = close.index[engine_invested]

    monthly_invested = compute_stats(net_ret, weights, turnover, invested_index, cost_per_trade)
    monthly_full = compute_stats(net_ret, weights, turnover, full_index, cost_per_trade)
    engine_invested_stats = compute_stats(
        engine_net, engine_weights, engine_turnover, engine_invested_index, cost_per_trade
    )
    engine_full_stats = compute_stats(
        engine_net, engine_weights, engine_turnover, full_index, cost_per_trade
    )

    # --- benchmark: 1/N equal weight over the same universe (engine convention:
    # constant exogenous weights, zero observed turnover, zero cost drag) ---
    daily_ret = close.pct_change().fillna(0.0)
    bench_net = daily_ret.mean(axis=1)
    bench_turnover = pd.Series(0.0, index=close.index)
    bench_weights = pd.DataFrame(1.0 / len(universe), index=close.index, columns=close.columns)
    bench_invested = compute_stats(
        bench_net, bench_weights, bench_turnover, invested_index, cost_per_trade
    )
    bench_test = compute_stats(
        bench_net,
        bench_weights,
        bench_turnover,
        close.index[close.index > val_end],
        cost_per_trade,
    )
    check(
        "benchmark_exposure_is_unit",
        abs(bench_invested["avg_exposure"] - 1.0) < 1e-9,
        f"1/N benchmark gross exposure is {bench_invested['avg_exposure']:.6f} on the invested sample.",
    )

    # --- PSR under three targets ---
    psr_candidate = compute_psr(
        net_ret.loc[invested_index],
        sr_target=PSR_TARGET_CANDIDATE,
        n_bootstrap=PSR_N_BOOTSTRAP,
        block_size=PSR_BLOCK_SIZE,
        seed=PSR_SEED,
    )
    psr_comparable = compute_psr(
        net_ret.loc[invested_index],
        sr_target=PSR_TARGET_COMPARABLE,
        n_bootstrap=PSR_N_BOOTSTRAP,
        block_size=PSR_BLOCK_SIZE,
        seed=PSR_SEED,
    )
    psr_zero = compute_psr(
        net_ret.loc[invested_index],
        sr_target=0.0,
        n_bootstrap=PSR_N_BOOTSTRAP,
        block_size=PSR_BLOCK_SIZE,
        seed=PSR_SEED,
    )
    dsr = compute_dsr(
        net_ret.loc[invested_index],
        n_configs=DSR_N_CONFIGS,
        sr_target=PSR_TARGET_CANDIDATE,
        n_bootstrap=PSR_N_BOOTSTRAP,
        block_size=PSR_BLOCK_SIZE,
        seed=DSR_SEED,
    )

    # --- repository promotion-gate table on the long sample ---
    gate_values = {
        "track_record_length": float(monthly_invested["sessions"]),
        "full_period_sharpe": float(monthly_invested["sharpe_canonical"]),
        "rolling_63d_sharpe": float(monthly_invested["rolling_63d_sharpe"]),
        "max_drawdown": float(monthly_invested["max_drawdown"]),
        "rolling_63d_max_dd": float(monthly_invested["rolling_63d_max_dd"]),
    }
    gates_primary, failed_primary, decision_primary, zone_primary = evaluate_gates(
        gates_cfg, gate_values, float(psr_candidate["psr_normal"]), regime_flips_applicable=False
    )
    gates_comparable, failed_comparable, decision_comparable, zone_comparable = evaluate_gates(
        gates_cfg, gate_values, float(psr_comparable["psr_normal"]), regime_flips_applicable=False
    )
    # conservative reading: the regime-flip gate cannot be satisfied and is
    # counted as failed.
    gates_conservative = json.loads(json.dumps(gates_primary))
    gates_conservative["regime_flips"] = {
        "value": None,
        "threshold": float(next(g["threshold"] for g in gates_cfg["gates"] if g["name"] == "regime_flips")),
        "comparison": "gte",
        "pass": False,
        "status": "not_applicable_counted_as_failed",
    }
    failed_conservative = sorted(failed_primary + ["regime_flips"])
    decision_conservative = (
        gates_cfg["decision_mapping"]["psr_grey_zone_and_only_psr_gate_fails"]
        if failed_conservative == ["psr"] and zone_primary == "grey_zone"
        else gates_cfg["decision_mapping"]["any_other_gate_fails"]
    )

    # --- pre-registered chronological splits ---
    split_stats = {        "train": compute_stats(
            net_ret, weights, turnover, close.index[close.index <= train_end], cost_per_trade
        ),
        "validation": compute_stats(
            net_ret,
            weights,
            turnover,
            close.index[(close.index > train_end) & (close.index <= val_end)],
            cost_per_trade,
        ),
        "test": compute_stats(
            net_ret, weights, turnover, close.index[close.index > val_end], cost_per_trade
        ),
    }

    # --- pre-registered walk-forward (36 folds) ---
    wf_cfg = cand["evaluation"]["walk_forward"]
    wf_splits = generate_walkforward_splits(
        start_date=cand["history_start"],
        end_date=end.date().isoformat(),
        train_years=float(wf_cfg["train_years"]),
        test_months=float(wf_cfg["test_months"]),
        step_months=float(wf_cfg["step_months"]),
        purge_days=int(wf_cfg["purge_days"]),
        embargo_days=int(wf_cfg["embargo_days"]),
    )
    check(
        "walkforward_fold_count",
        len(wf_splits) == WF_EXPECTED_FOLDS,
        f"generated {len(wf_splits)} walk-forward folds (pre-registered {WF_EXPECTED_FOLDS}).",
    )
    wf_rows = evaluate_walkforward(net_ret, turnover, wf_splits)
    wf_sharpes = [r["test_sharpe"] for r in wf_rows]
    wf_mean_sharpe = float(np.mean(wf_sharpes)) if wf_sharpes else float("nan")
    wf_positive_rate = float(np.mean([r["test_positive"] for r in wf_rows])) if wf_rows else float("nan")
    wf_pooled_trades = int(sum(r["test_trades"] for r in wf_rows))
    traded_sessions: set[pd.Timestamp] = set()
    for r in wf_rows:
        ts = pd.Timestamp(r["test_start"], tz="UTC")
        te = pd.Timestamp(r["test_end"], tz="UTC")
        sel = (net_ret.index >= ts) & (net_ret.index <= te)
        t = turnover.loc[clean(net_ret[sel]).index]
        traded_sessions.update(t[t > 1e-10].index.tolist())
    wf_unique_trades = len(traded_sessions)

    # The pre-registered design burns in 10 years before the first fold test
    # window, so the fold windows start in 2008 and exclude the first ~8.6
    # years of the candidate's live history. That difference is quantified
    # here, because it is the reason the walk-forward gate and the long-sample
    # gate disagree.
    wf_first_start = pd.Timestamp(wf_splits[0]["test_start"], tz="UTC")
    wf_last_end = pd.Timestamp(wf_splits[-1]["test_end"], tz="UTC")
    wf_window = close.index[(close.index >= wf_first_start) & (close.index <= wf_last_end)]
    pre_wf_window = close.index[close.index < wf_first_start]
    stats_wf_window = compute_stats(net_ret, weights, turnover, wf_window, cost_per_trade)
    stats_pre_wf = compute_stats(net_ret, weights, turnover, pre_wf_window, cost_per_trade)
    bench_wf_window = compute_stats(
        bench_net, bench_weights, bench_turnover, wf_window, cost_per_trade
    )

    wf_gates = {
        "wf_mean_oos_sharpe": {
            "value": wf_mean_sharpe,
            "threshold": float(cand["evaluation"]["promotion_gates"]["wf_mean_oos_sharpe_min"]),
            "comparison": "gte",
            "pass": bool(wf_mean_sharpe >= float(cand["evaluation"]["promotion_gates"]["wf_mean_oos_sharpe_min"])),
            "status": "evaluated",
        },
        "positive_fold_rate": {
            "value": wf_positive_rate,
            "threshold": float(cand["evaluation"]["promotion_gates"]["positive_fold_rate_min"]),
            "comparison": "gte",
            "pass": bool(wf_positive_rate >= float(cand["evaluation"]["promotion_gates"]["positive_fold_rate_min"])),
            "status": "evaluated",
        },
        "pooled_oos_trades": {
            "value": float(wf_pooled_trades),
            "threshold": float(cand["evaluation"]["promotion_gates"]["pooled_oos_trades_min"]),
            "comparison": "gt",
            "pass": bool(wf_pooled_trades > float(cand["evaluation"]["promotion_gates"]["pooled_oos_trades_min"])),
            "status": "evaluated",
        },
    }
    wf_failed = [k for k, g in wf_gates.items() if not g["pass"]]

    # --- parameter plateau: 3 lookbacks at skip=21, top_fraction=0.5 ---
    plateau_rows = []
    test_mask = close.index > val_end
    for lb in (189, 252, 315):
        mom_lb = compute_momentum(close, lookback=lb, skip=skip)
        mask_lb = select_top_decile(mom_lb, top_fraction=top_fraction)
        w_lb, _ = build_monthly_weights(close, mask_lb, month_ends)
        net_lb, turn_lb = portfolio_returns(close, w_lb, cost_per_trade)
        st = compute_stats(net_lb, w_lb, turn_lb, close.index[test_mask], cost_per_trade)
        plateau_rows.append(
            {
                "lookback": lb,
                "skip": skip,
                "top_fraction": top_fraction,
                "test_sessions": st["sessions"],
                "test_sharpe_canonical": st["sharpe_canonical"],
                "test_sharpe_backtest_scale": st["sharpe_backtest_scale"],
                "test_cagr": st["cagr"],
                "test_max_dd": st["max_drawdown"],
            }
        )
    baseline_plateau = next(p for p in plateau_rows if p["lookback"] == lookback)
    plateau_threshold = max(0.1, 0.10 * abs(baseline_plateau["test_sharpe_canonical"]))
    within = [
        p["lookback"]
        for p in plateau_rows
        if abs(p["test_sharpe_canonical"] - baseline_plateau["test_sharpe_canonical"]) <= plateau_threshold
    ]
    plateau_required = int(round(float(cand["evaluation"]["promotion_gates"]["plateau_fraction_min"]) * 3))
    plateau_gate = {
        "value": float(len(within)),
        "threshold": float(plateau_required),
        "comparison": "gte",
        "pass": bool(len(within) >= plateau_required),
        "status": "evaluated",
        "lookbacks_within_threshold": within,
        "threshold_used": float(plateau_threshold),
    }

    # --- final integrity check: the raw cache must be untouched ---
    hashes_after = {s: sha256_file(RAW_DIR / f"{s}.parquet") for s in universe}
    check(
        "raw_cache_unchanged",
        hashes_before == hashes_after,
        f"all {len(universe)} sector parquet files are SHA-256 byte-identical before and after the run.",
    )

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------
    sample_def = {
        "candidate_id": cand["candidate_id"],
        "start_date": start.date().isoformat(),
        "end_date": end.date().isoformat(),
        "session_count": int(len(close.index)),
        "universe": universe,
        "lookback": lookback,
        "skip": skip,
        "top_fraction": top_fraction,
        "rebalance_freq": cand["signal"].get("rebalance_freq", "monthly"),
        "signal_lag_days": int(cand["execution"]["signal_lag_days"]),
        "cost_model": cost_model,
        "data_source": "committed raw cache (data/raw/*.parquet), no network",
        "aligned_frame_rows": int(close.shape[0]),
        "aligned_frame_hash": aligned_hash,
        "pre_registered_aligned_frame_hash": ALIGNED_FRAME_HASH_PREFIX,
        "sha256_raw_files": hashes_before,
        "per_symbol": per_symbol,
    }

    psr_table = {
        "target_0.0": {
            "sr_target": 0.0,
            "psr_normal": float(psr_zero["psr_normal"]),
            "psr_empirical": float(psr_zero["psr_empirical"]),
            "sharpe_observed": float(psr_zero["sharpe_observed"]),
            "sharpe_se": float(psr_zero["sharpe_se"]),
        },
        "target_0.9_candidate_gate": {
            "sr_target": PSR_TARGET_CANDIDATE,
            "psr_normal": float(psr_candidate["psr_normal"]),
            "psr_empirical": float(psr_candidate["psr_empirical"]),
            "sharpe_observed": float(psr_candidate["sharpe_observed"]),
            "sharpe_se": float(psr_candidate["sharpe_se"]),
            "sharpe_ci_lower": float(np.percentile(psr_candidate["bootstrap_sharpes"], 2.5)),
            "sharpe_ci_upper": float(np.percentile(psr_candidate["bootstrap_sharpes"], 97.5)),
        },
        "target_1.4178_incumbent_baseline": {
            "sr_target": PSR_TARGET_COMPARABLE,
            "psr_normal": float(psr_comparable["psr_normal"]),
            "psr_empirical": float(psr_comparable["psr_empirical"]),
            "sharpe_observed": float(psr_comparable["sharpe_observed"]),
            "sharpe_se": float(psr_comparable["sharpe_se"]),
        },
    }

    wf_summary = {
        "n_folds": len(wf_rows),
        "mean_test_sharpe": wf_mean_sharpe,
        "median_test_sharpe": float(np.median(wf_sharpes)) if wf_sharpes else float("nan"),
        "min_test_sharpe": float(np.min(wf_sharpes)) if wf_sharpes else float("nan"),
        "max_test_sharpe": float(np.max(wf_sharpes)) if wf_sharpes else float("nan"),
        "positive_fold_rate": wf_positive_rate,
        "pooled_oos_trades_sum_over_folds": wf_pooled_trades,
        "unique_traded_sessions_across_folds": wf_unique_trades,
        "mean_test_cagr": float(np.mean([r["test_cagr"] for r in wf_rows])),
        "worst_test_max_dd": float(np.min([r["test_max_dd"] for r in wf_rows])),
        "folds": wf_rows,
    }

    dsr_summary = {
        "dsr": float(dsr["dsr"]),
        "dsr_probability": float(dsr["dsr_probability"]),
        "n_configs": int(dsr["n_configs"]),
        "sr_observed": float(dsr["sr_observed"]),
        "sharpe_se": float(dsr["sharpe_se"]),
        "sr_threshold": float(dsr["sr_threshold"]),
        "e_max": float(dsr["e_max"]),
        "sr_target": float(dsr["sr_target"]),
        "seed": DSR_SEED,
    }

    variants = {
        "monthly_rebalance_invested_sample": monthly_invested,
        "monthly_rebalance_full_sample": monthly_full,
        "engine_daily_rerank_invested_sample": engine_invested_stats,
        "engine_daily_rerank_full_sample": engine_full_stats,
        "benchmark_1_over_9_equal_weight": bench_invested,
    }

    decisions = {
        "primary_candidate_target_0.9": {
            "decision": decision_primary,
            "failed_gates": failed_primary,
            "psr_zone": zone_primary,
            "regime_flips_treatment": "not_applicable_excluded",
            "psr_target": PSR_TARGET_CANDIDATE,
        },
        "comparable_incumbent_target_1.4178": {
            "decision": decision_comparable,
            "failed_gates": failed_comparable,
            "psr_zone": zone_comparable,
            "regime_flips_treatment": "not_applicable_excluded",
            "psr_target": PSR_TARGET_COMPARABLE,
        },
        "conservative_regime_flips_counted_as_failed": {
            "decision": decision_conservative,
            "failed_gates": failed_conservative,
            "psr_zone": zone_primary,
            "regime_flips_treatment": "not_applicable_counted_as_failed",
            "psr_target": PSR_TARGET_CANDIDATE,
        },
    }

    # Pre-registered falsification condition of the hypothesis.
    falsified = wf_failed or not plateau_gate["pass"]
    if falsified:
        label = "rejected/failed (pre-registered falsification condition met)"
    elif wf_mean_sharpe >= 0.9 and wf_positive_rate >= 0.5 and wf_pooled_trades > 100:
        label = "credible candidate for further validation"
    else:
        label = "exploratory signal"

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    def jdump(obj: Any) -> str:
        return json.dumps(obj, indent=2, default=str)

    with open(REPORT_MD, "w") as f:
        f.write("# Sector Rotation Long-Sample Feasibility (Cycle 869)\n\n")
        f.write(
            "Candidate `sectorrotation_001` (frozen config `config/sectorrotation_candidate_001.yaml`) "
            "evaluated on its own long sample, in the pattern of "
            "`research/promotion_feasibility_backtest.py`.\n\n"
        )
        f.write(f"- code revision: `{git_revision()}`\n")
        f.write(f"- report generator: `research/sectorrotation_long_sample_feasibility.py`\n")
        f.write(f"- raw cache SHA-256 identical before/after: {hashes_before == hashes_after}\n\n")

        f.write("## Verdict\n\n")
        f.write(
            f"- long-sample net-of-cost Sharpe (canonical `arithmetic_annualized_rf0`, "
            f"config-faithful month-end rebalance, invested sample): "
            f"**{monthly_invested['sharpe_canonical']:.6f}** "
            f"(backtest-baseline scale {monthly_invested['sharpe_backtest_scale']:.6f})\n"
        )
        f.write(
            f"- PSR vs the candidate's own promotion threshold 0.9: "
            f"**{psr_candidate['psr_normal']:.6f}** "
            f"(PSR vs the incumbent baseline 1.4178: {psr_comparable['psr_normal']:.6f})\n"
        )
        f.write(
            f"- trade days (invested sample): **{monthly_invested['trade_days']}** across "
            f"{len(segments)} month-end rebalances; pooled out-of-sample trades over the "
            f"{len(wf_rows)} pre-registered folds: **{wf_pooled_trades}** "
            f"({wf_unique_trades} unique sessions)\n"
        )
        f.write(
            f"- repository promotion-gate table on the long sample: "
            f"**{decision_primary}** (failed: {failed_primary}; PSR zone {zone_primary})\n"
        )
        f.write(
            f"- candidate's own pre-registered gates: walk-forward mean OOS Sharpe "
            f"{wf_mean_sharpe:.6f} (>= 0.9 required), positive fold rate {wf_positive_rate:.4f} "
            f"(>= 0.5), pooled OOS trades {wf_pooled_trades} (> 100), plateau {plateau_gate['value']:.0f}/3 "
            f"lookbacks within 10% -> failed gates {wf_failed}\n"
        )
        f.write(
            f"- excess over the 1/N equal-weight benchmark on the invested sample: "
            f"{monthly_invested['sharpe_canonical'] - bench_invested['sharpe_canonical']:+.6f} Sharpe, "
            f"{(monthly_invested['cagr'] - bench_invested['cagr']) * 100:+.4f} pp annualized, at "
            f"{monthly_invested['annualized_turnover']:.4f}x annualized turnover\n"
        )
        f.write(
            f"- the 36 pre-registered fold windows cover "
            f"{stats_wf_window['start_date']}..{stats_wf_window['end_date']} and exclude the "
            f"{stats_pre_wf['sessions']} sessions before "
            f"{stats_pre_wf['end_date']} (max drawdown there {stats_pre_wf['max_drawdown']:.6f}); the "
            f"fold windows and the long sample therefore measure different periods\n"
        )
        f.write(f"- label: **{label}**\n\n")

        f.write("## 1. Sample definition and data integrity\n\n```json\n")
        f.write(jdump(sample_def))
        f.write("\n```\n\n")
        f.write(
            f"- The aligned Close frame reproduces the pre-registered content hash "
            f"`{ALIGNED_FRAME_HASH_PREFIX}` recorded in "
            "`research/hypotheses/sectorrotation_001.md` (freeze time 2026-10-12): the cached data "
            "has not changed since pre-registration.\n"
        )
        f.write(
            f"- The cache ends {end.date().isoformat()} for the 9 sector ETFs, i.e. "
            f"{len(close.index)} sessions of the 9-sector union calendar. The core cache "
            "(SPY/QQQ/.../EEM) reaches 2026-10-16; the sector universe is 6 sessions behind. "
            "No data was fetched or written (`data/` is byte-identical, see the checks).\n"
        )
        f.write(
            f"- The first date with a valid 9-asset momentum cross-section is "
            f"{first_signal.date().isoformat()} (pre-registered {PRE_REGISTERED_FIRST_SIGNAL}); "
            f"the first session with positions is {first_invested.date().isoformat()}. "
            f"The invested sample therefore has {monthly_invested['sessions']} sessions and the "
            f"full aligned sample {monthly_full['sessions']}.\n\n"
        )

        f.write("## 2. Execution path: the engine does not implement the frozen rebalance schedule\n\n")
        f.write(
            "`src/backtest/engine.py:run_backtest` accepts a `rebalance_freq` argument and never uses "
            "it: `build_weights` re-ranks the universe **every session**, so positions can change "
            "between month-ends. The frozen configuration specifies month-end rebalancing with a "
            "1-day signal lag, so the config-faithful path is implemented in this script "
            "(`build_monthly_weights`) and the engine path is reported next to it as a deviation "
            "measurement, using exactly the code path of "
            "`research/promotion_feasibility_backtest.py`.\n\n"
        )
        f.write(
            f"- config-faithful (month-end rebalance): {len(segments)} rebalances, "
            f"{monthly_invested['trade_days']} trade days, annualized turnover "
            f"{monthly_invested['annualized_turnover']:.4f}\n"
        )
        f.write(
            f"- engine default (daily re-rank): {engine_invested_stats['trade_days']} trade days, "
            f"annualized turnover {engine_invested_stats['annualized_turnover']:.4f}, "
            f"Sharpe {engine_invested_stats['sharpe_canonical']:.6f}\n\n"
        )

        f.write("## 3. Long-sample results (primary: config-faithful month-end rebalance)\n\n")
        f.write("```json\n")
        f.write(jdump(monthly_invested))
        f.write("\n```\n\n")
        f.write("### Variant comparison\n\n```json\n")
        f.write(jdump(variants))
        f.write("\n```\n\n")
        f.write(
            "The full-sample rows keep the pre-warmup sessions (zero exposure, zero return); the "
            "invested-sample rows start at the first session with a position. The gate evaluation "
            "uses the invested sample of the config-faithful path.\n\n"
        )

        f.write("## 4. Pre-registered chronological splits\n\n```json\n")
        f.write(jdump(split_stats))
        f.write("\n```\n\n")

        f.write("## 5. Pre-registered walk-forward (36 folds, fixed parameters)\n\n")
        f.write(
            f"Splits are generated with `src/evaluation/walkforward.py:generate_walkforward_splits` "
            f"({wf_cfg['train_years']}y train / {wf_cfg['test_months']}m test / {wf_cfg['step_months']}m "
            f"step, purge {wf_cfg['purge_days']}d, embargo {wf_cfg['embargo_days']}d) from "
            f"{cand['history_start']}; {len(wf_splits)} folds were generated "
            f"(pre-registered: {WF_EXPECTED_FOLDS}). Parameters are fixed across folds, so the "
            "fold test windows are slices of one continuously computed point-in-time strategy path "
            "rather than re-fitted per fold.\n\n"
        )
        f.write("```json\n")
        f.write(jdump({k: v for k, v in wf_summary.items() if k != "folds"}))
        f.write("\n```\n\n")
        f.write("### Candidate's own pre-registered gates\n\n```json\n")
        f.write(jdump(wf_gates))
        f.write("\n```\n\n")
        f.write(
            "Falsification condition (pre-registered): WF mean OOS Sharpe < 0.9 OR positive fold rate "
            "< 50% OR pooled OOS trades < 100 OR the parameter plateau check fails.\n\n"
        )

        f.write("### What the walk-forward windows cover (and what they exclude)\n\n")
        f.write(
            f"The pre-registered design burns in 10 years before the first fold test window, so the "
            f"36 fold test windows cover **{stats_wf_window['start_date']} .. {stats_wf_window['end_date']}** "
            f"and **exclude** the first {stats_pre_wf['sessions']} invested sessions "
            f"({stats_pre_wf['start_date']} .. {stats_pre_wf['end_date']}). That is why the walk-forward "
            f"mean OOS Sharpe ({wf_mean_sharpe:.6f}) is far above the full-sample Sharpe "
            f"({monthly_invested['sharpe_canonical']:.6f}): the two numbers measure different windows, "
            f"and the excluded window is where the strategy lost money.\n\n"
        )
        f.write(
            f"Two further properties of the pre-registered design must be kept in mind when reading "
            f"the gate value. (1) The gate statistic is the **mean of 36 overlapping 12-month "
            f"Sharpes**; it is not the Sharpe of the concatenated covered window, which is "
            f"{stats_wf_window['sharpe_canonical']:.6f} over the same "
            f"{stats_wf_window['sessions']} sessions -- equal-weighting the folds gives every year "
            f"the same weight and therefore a higher value than the compounded path. (2) The folds "
            f"overlap by 6 months, so they are not independent observations: the pooled trade count "
            f"is {wf_pooled_trades} summed over folds but only {wf_unique_trades} distinct traded "
            f"sessions.\n\n"
        )
        f.write("```json\n")
        f.write(
            jdump(
                {
                    "walkforward_covered_window": stats_wf_window,
                    "pre_walkforward_window_excluded_from_the_folds": stats_pre_wf,
                    "benchmark_1_over_9_same_window": bench_wf_window,
                }
            )
        )
        f.write("\n```\n\n")

        f.write("### Parameter plateau (lookback 189 / 252 / 315 at skip 21, top_fraction 0.5, test window)\n\n")
        f.write("```json\n")
        f.write(jdump({"rows": plateau_rows, "gate": plateau_gate}))
        f.write("\n```\n\n")

        f.write("## 6. PSR and multiple-testing control\n\n```json\n")
        f.write(jdump(psr_table))
        f.write("\n```\n\n")
        f.write("```json\n")
        f.write(jdump(dsr_summary))
        f.write("\n```\n\n")
        f.write(
            "The PSR seed is 20240101 (as in `config/promotion_gates.yaml`), the DSR seed is 42 "
            "(as in the frozen candidate config); N=18 is the pre-registered configuration count. "
            "Three PSR targets are reported because the candidate has no recorded backtest baseline "
            "of its own: 0.0 (is the edge positive at all), 0.9 (the candidate's own promotion "
            "threshold -- the decision-relevant reading) and 1.4178 (the incumbent's recorded "
            "baseline -- kept for like-for-like comparison with "
            "`research/reports/promotion_feasibility_backtest_001.md`).\n\n"
        )

        f.write("## 7. Repository promotion-gate table applied to the long sample\n\n")
        f.write("```json\n")
        f.write(jdump(gates_primary))
        f.write("\n```\n\n")
        f.write(
            "`regime_flips` is reported as NOT APPLICABLE: it counts risk-on/risk-off transitions in "
            "a paper-trading state, and this candidate has no paper-trading record and no regime "
            "filter (frozen config: `risk_overlay.none = true`). The decision is therefore given "
            "under three explicit readings.\n\n"
        )
        f.write("```json\n")
        f.write(jdump(decisions))
        f.write("\n```\n\n")
        f.write("### Same table with the incumbent's PSR target (1.4178)\n\n```json\n")
        f.write(jdump(gates_comparable))
        f.write("\n```\n\n")

        f.write("## 8. Benchmark: 1/N equal weight over the same 9 sectors\n\n```json\n")
        f.write(jdump({"invested_sample": bench_invested, "test_window": bench_test}))
        f.write("\n```\n\n")
        f.write(
            f"The benchmark is evaluated in the engine's exogenous-weight convention (constant 1/9 "
            f"weights, zero observed turnover, zero cost drag), which is the convention documented in "
            f"the hypothesis.\n\n"
        )
        f.write(
            f"- invested sample: strategy CAGR {monthly_invested['cagr']:+.6f} vs benchmark "
            f"{bench_invested['cagr']:+.6f} (excess {monthly_invested['cagr'] - bench_invested['cagr']:+.6f}), "
            f"Sharpe {monthly_invested['sharpe_canonical']:.6f} vs {bench_invested['sharpe_canonical']:.6f} "
            f"(excess {monthly_invested['sharpe_canonical'] - bench_invested['sharpe_canonical']:+.6f})\n"
        )
        f.write(
            f"- test window (2018-01-01 .. 2026-10-08): strategy CAGR {split_stats['test']['cagr']:+.6f} "
            f"vs benchmark {bench_test['cagr']:+.6f} (excess "
            f"{split_stats['test']['cagr'] - bench_test['cagr']:+.6f}), Sharpe "
            f"{split_stats['test']['sharpe_canonical']:.6f} vs {bench_test['sharpe_canonical']:.6f} "
            f"(excess {split_stats['test']['sharpe_canonical'] - bench_test['sharpe_canonical']:+.6f})\n"
        )
        f.write(
            f"- max drawdown: strategy {monthly_invested['max_drawdown']:.6f} vs benchmark "
            f"{bench_invested['max_drawdown']:.6f}\n"
        )
        f.write(
            f"- the strategy buys its long-sample Sharpe with turnover "
            f"({monthly_invested['annualized_turnover']:.4f}x annualized) and "
            f"{monthly_invested['trade_days']} trade days; the benchmark needs none.\n\n"
        )

        f.write("## 9. Falsification conditions for this report\n\n")
        f.write("- the raw cache is modified, or the aligned-frame hash stops matching "
                f"`{ALIGNED_FRAME_HASH_PREFIX}` -> the data is not the pre-registered data -> reject.\n")
        f.write("- the sample window differs from 1998-12-22..2026-10-08 -> reject.\n")
        f.write("- canonical and backtest-baseline Sharpe conventions are mixed in one statement -> reject.\n")
        f.write("- the walk-forward fold count is not 36 -> reject.\n")
        f.write("- the month-end weights are not derived from the mask at the preceding month-end -> "
                "the path is not point-in-time -> reject.\n")
        f.write("- a gate threshold is changed from `config/promotion_gates.yaml` or from the frozen "
                "candidate config -> reject.\n\n")

        f.write("## 10. Limitations and caveats\n\n")
        f.write(
            "1. The long sample is a single path of one pre-registered configuration; it is a "
            "feasibility screen, not an independent out-of-sample record.\n"
        )
        f.write(
            "2. The engine's `rebalance_freq` argument is inert, so the repository's own backtest "
            "path for this candidate does not implement the frozen month-end schedule; the "
            "config-faithful path lives in this research script, not in `src/`.\n"
        )
        f.write(
            "3. The PSR target 1.4178 belongs to the incumbent's backtest baseline and is not the "
            "candidate's own baseline; it is reported for comparability only.\n"
        )
        f.write(
            "4. The `regime_flips` gate cannot be evaluated without a paper-trading record, so the "
            "gate table is reported under three explicit readings instead of one.\n"
        )
        f.write(
            "5. Costs are the repository's flat 3 bps round-trip model (1 bps commission + 2 bps "
            "slippage) with no bid-ask spread, market-impact, borrow or latency model; sector ETFs "
            "can be wider than SPY.\n"
        )
        f.write(
            "6. The sector-ETF cache ends 2026-10-08 while the core cache reaches 2026-10-16, so the "
            "candidate is evaluated 6 sessions behind the rest of the repository.\n"
        )
        f.write(
            "7. The 18-configuration robustness grid is not evaluated here (only the 3-lookback "
            "plateau check required by the pre-registered falsification condition).\n\n"
        )

        f.write("## 11. Reproduction\n\n")
        f.write("```json\n")
        f.write(
            jdump(
                {
                    "command": "python research/sectorrotation_long_sample_feasibility.py",
                    "deterministic": True,
                    "no_network": True,
                    "read_only_data": True,
                    "psr_seed": PSR_SEED,
                    "dsr_seed": DSR_SEED,
                    "n_bootstrap": PSR_N_BOOTSTRAP,
                    "block_size": PSR_BLOCK_SIZE,
                }
            )
        )
        f.write("\n```\n\n")

        f.write("## Appendix A: walk-forward folds\n\n")
        f.write("| Fold | Test start | Test end | Sessions | Test Sharpe | Test CAGR | Test max DD | Trades | Positive |\n")
        f.write("|---|---|---|---|---|---|---|---|---|\n")
        for r in wf_rows:
            f.write(
                f"| {r['fold']} | {r['test_start']} | {r['test_end']} | {r['test_sessions']} | "
                f"{r['test_sharpe']:.6f} | {r['test_cagr']:.6f} | {r['test_max_dd']:.6f} | "
                f"{r['test_trades']} | {r['test_positive']} |\n"
            )
        f.write("\n")

        f.write("## Appendix B: internal checks\n\n")
        f.write("| Check | Pass | Detail |\n|---|---|---|\n")
        for c in checks:
            f.write(f"| {c['check']} | {c['pass']} | {c['detail']} |\n")
        f.write("\n")

    n_pass = sum(1 for c in checks if c["pass"])
    overall = "PASS" if n_pass == len(checks) else "FAIL"
    print(f"OVERALL: {overall} ({n_pass}/{len(checks)} checks)")
    print(
        f"SAMPLE: {start.date().isoformat()}..{end.date().isoformat()} "
        f"({len(close.index)} sessions), universe={len(universe)} sector ETFs"
    )
    print(
        f"monthly_invested sharpe_canon={monthly_invested['sharpe_canonical']:.6f} "
        f"backtest={monthly_invested['sharpe_backtest_scale']:.6f} "
        f"psr0.9={psr_candidate['psr_normal']:.6f} psr1.4178={psr_comparable['psr_normal']:.6f}"
    )
    print(
        f"engine_daily sharpe_canon={engine_invested_stats['sharpe_canonical']:.6f} "
        f"trade_days={engine_invested_stats['trade_days']}"
    )
    print(
        f"wf folds={len(wf_rows)} mean_oos_sharpe={wf_mean_sharpe:.6f} "
        f"positive_rate={wf_positive_rate:.4f} pooled_trades={wf_pooled_trades} "
        f"unique_trades={wf_unique_trades}"
    )
    print(
        f"gates primary: decision={decision_primary} failed={failed_primary} zone={zone_primary}; "
        f"wf_failed={wf_failed} plateau_pass={plateau_gate['pass']}"
    )
    print(f"label: {label}")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
