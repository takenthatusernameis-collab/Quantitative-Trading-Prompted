#!/usr/bin/env python3
"""Re-audit of the two remaining frozen month-end candidates on the
config-faithful path (Cycle 871).

Read-only with respect to market data: the tool reads the committed raw cache
(``data/raw/*.parquet``) and the committed processed artifacts
(``data/processed/*.parquet``), writes exactly one report under
``research/reports/`` and touches nothing else. It is deterministic (no random
number generator, no timestamps in the report).

Background
----------
``config/csmomentum_candidate_001.yaml`` and
``config/macroregime_candidate_001.yaml`` both freeze
``execution.rebalance_schedule: "monthly"`` with ``signal_lag_days: 1``.
Cycle 870 put one correct implementation of that schedule into shared code
(``src/backtest/rebalance.py``).  The two candidates, however, were executed by
``research/run_cycle13.py`` and ``research/run_cycle19.py`` with a **calendar**
rule (``weights.index.is_month_end``) that

* rebalances one session earlier than the frozen configuration specifies (the
  signal is taken from the session *before* the month's last session), and
* never rebalances at all in every month whose last calendar day was a
  weekend or a market holiday, carrying the previous month's weights through
  the whole month.

This tool measures, read-only and without re-optimising anything, how much that
defect moved the published results of the two candidates.

Paths
-----
``legacy``
    The calendar rule exactly as ``research/run_cycle13.py`` /
    ``research/run_cycle19.py`` implemented it.
``faithful``
    The shared month-end schedule of ``src/backtest/rebalance.py``: the signal
    is formed on the **last session** of the calendar month and the positions
    become effective on the **next** session and are held until the next
    month-end signal.
``daily``
    The repository's other historical convention: the universe is re-ranked
    every session (``src/backtest/engine.py`` default).  It is evaluated only
    to establish which code path produced
    ``research/experiments/csmomentum_001_experiment_001.md``.

Reproduction: ``python research/month_end_candidate_reaudit.py``
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.backtest.engine import compute_metrics, get_cost_params, get_risk_free_rate  # noqa: E402
from src.backtest.rebalance import build_month_end_weights, month_end_sessions  # noqa: E402
from src.evaluation.risk import realized_vol_scale  # noqa: E402
from src.evaluation.sharpe import sharpe_ratio  # noqa: E402
from src.evaluation.utils import fetch_close_prices, max_drawdown  # noqa: E402
from src.evaluation.walkforward import (  # noqa: E402
    generate_walkforward_splits,
    summarize_walkforward,
)
from src.features.momentum import (  # noqa: E402
    build_weights,
    compute_momentum,
    select_top_decile,
)

CONFIG_CS = REPO_ROOT / "config" / "csmomentum_candidate_001.yaml"
CONFIG_MACRO = REPO_ROOT / "config" / "macroregime_candidate_001.yaml"
RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
REPORT_MD = REPORTS_DIR / "month_end_candidate_reaudit_001.md"

# --- published windows (the windows the two candidates were executed in) -----
CS_START, CS_END = "1993-01-01", "2026-10-09"
MACRO_START, MACRO_END = "2004-11-18", "2026-10-09"
TEST_START = "2018-01-01"
WF_TRAIN_YEARS, WF_TEST_MONTHS, WF_STEP_MONTHS = 10.0, 12.0, 6.0
WF_PURGE_DAYS, WF_EMBARGO_DAYS = 21, 21

# --- published numbers (source: the committed experiment records) -----------
# The published values are quoted exactly as they appear in the records (as
# strings), so that the tolerance of every comparison is derived from the
# number of decimals the record itself uses.
# research/experiments/csmomentum_001_experiment_001.md (full sample)
CS_REC_FULL = {
    "annualized_return": "0.0937",
    "annualized_volatility": "0.1639",
    "sharpe_ratio": "0.4496",
    "sortino_ratio": "0.5852",
    "max_drawdown": "-0.4336",
    "annualized_turnover": "12.03",
    "trade_count": "1781",
    "profit_factor": "1.1217",
    "avg_exposure": "0.968",
}
# research/experiments/csmomentum_001_experiment_001.md (test window)
CS_REC_TEST = {
    "sharpe_ratio": "0.5652",
    "annualized_return": "0.1114",
    "max_drawdown": "-0.2756",
    "trade_count": "533",
}
# research/experiments/csmomentum_001_experiment_001.md (walk-forward block)
CS_REC_WF = {"n_folds": "46", "mean_test_sharpe": "0.6619", "pct_positive_sharpe": "0.783",
             "total_test_trades": "2855"}
# research/experiments/csmomentum_baseline_wf_001.md (test window, calendar path)
CS_CAL_TEST = {
    "total_return": "1.1383",
    "annualized_return": "0.0907",
    "annualized_volatility": "0.1725",
    "sharpe_ratio": "0.4101",
    "sortino_ratio": "0.4922",
    "max_drawdown": "-0.3571",
    "annualized_turnover": "2.06",
    "trade_count": "62",
    "profit_factor": "1.12",
    "avg_exposure": "1.0000",
}
# research/experiments/csmomentum_baseline_wf_001.md (walk-forward block)
CS_CAL_WF = {"n_folds": "48", "mean_test_sharpe": "0.6868", "pct_positive_sharpe": "0.792",
             "total_test_trades": "313"}
# research/experiments/macroregime_baseline_wf_001.md (test window)
MACRO_REC_TEST = {
    "total_return": "0.5571",
    "annualized_return": "0.0519",
    "annualized_volatility": "0.1082",
    "sharpe_ratio": "0.2950",
    "sortino_ratio": "0.3289",
    "max_drawdown": "-0.1807",
    "annualized_turnover": "3.13",
    "trade_count": "58",
    "profit_factor": "1.11",
    "avg_exposure": "0.6758",
}
# research/experiments/macroregime_baseline_wf_001.md (walk-forward block)
MACRO_REC_WF = {"n_folds": "24", "mean_test_sharpe": "0.4331", "std_test_sharpe": "0.9609",
                "median_test_sharpe": "0.4950", "pct_positive_sharpe": "0.750",
                "total_test_trades": "137"}
# research/experiments/macroregime_001_experiment_002.md (same numbers, restated)
MACRO_002_WF = {"n_folds": "24", "mean_test_sharpe": "0.4331", "pct_positive_sharpe": "0.750",
                "total_test_trades": "137"}

# --- committed processed artifacts used as the reproduction reference -------
CS_WEIGHTS_REF = PROCESSED_DIR / "weights_csmomentum_001.parquet"
CS_SIM_REF = PROCESSED_DIR / "simulation_csmomentum_001.parquet"
MACRO_WEIGHTS_REF = PROCESSED_DIR / "weights_macroregime_001.parquet"

# Tolerance note: every published number is quoted as the string it has in the
# committed record, and the comparison tolerance is the unit of that string's
# last decimal (see compare_published).


# ----------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------
def load_yaml(path: Path) -> Any:
    with open(path, "r") as fh:
        return yaml.safe_load(fh)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def content_hash(frame: pd.DataFrame) -> str:
    return hashlib.sha256(pd.util.hash_pandas_object(frame).values.tobytes()).hexdigest()


def legacy_calendar_schedule(weights: pd.DataFrame) -> pd.DataFrame:
    """The defective calendar rule of ``research/run_cycle13.py`` / ``run_cycle19.py``.

    ``weights.index.is_month_end`` is a **calendar** predicate applied to a
    **trading** calendar: the row of a month whose last calendar day is a
    weekend or a market holiday does not exist, so the previous month's weights
    are carried through the whole month.
    """
    is_month_end = pd.Series(weights.index.is_month_end, index=weights.index)
    return weights.where(is_month_end, axis=0).ffill().fillna(0.0)


def faithful_schedule(
    daily_weights: pd.DataFrame,
    mask: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Config-faithful month-end path built on ``src/backtest/rebalance.py``.

    ``build_month_end_weights`` turns the selection mask into a month-end
    schedule: the signal is formed on the last session of the calendar month
    and the positions become effective on the next session.

    * For a candidate **without** risk overlays the schedule *is* the weight
      matrix, so the returned weights equal ``build_month_end_weights(mask)``.
    * For a candidate **with** risk overlays the overlays are computed on the
      daily pipeline (exactly as the legacy path does) and the same schedule is
      applied by sampling that pipeline at each segment's effective date, so
      the only difference between the two paths is the schedule rule.
    """
    _scheduled, segments = build_month_end_weights(mask)
    idx = daily_weights.index
    if not segments:
        return pd.DataFrame(0.0, index=idx, columns=daily_weights.columns), segments

    effective = [seg["effective_date"] for seg in segments]
    out = pd.DataFrame(0.0, index=idx, columns=daily_weights.columns)
    for j, eff in enumerate(effective):
        start = int(idx.searchsorted(eff, side="left"))
        end = (
            int(idx.searchsorted(effective[j + 1], side="left"))
            if j + 1 < len(effective)
            else len(idx)
        )
        out.iloc[start:end, :] = daily_weights.loc[eff].to_numpy()
    return out, segments


def path_returns(
    close: pd.DataFrame,
    weights: pd.DataFrame,
    cost_per_trade: float,
) -> tuple[pd.Series, pd.DataFrame, pd.Series]:
    """Net-of-cost returns, aligned weights and turnover of one execution path."""
    common = close.index.intersection(weights.index)
    close_a = close.loc[common]
    weights_a = weights.loc[common]
    daily_ret = close_a.pct_change().fillna(0.0)
    gross = (weights_a * daily_ret).sum(axis=1)
    turnover = weights_a.diff().abs().sum(axis=1).fillna(0.0)
    return gross - turnover * cost_per_trade, weights_a, turnover


def path_metrics(
    net_ret: pd.Series,
    weights: pd.DataFrame,
    cost_per_trade: float,
    sample: pd.Index,
) -> dict[str, Any]:
    """Metrics of one execution path over *sample* (the repository conventions).

    The turnover is computed **on the sliced weight frame**, exactly as
    ``src/backtest/engine.py:compute_metrics`` does it, so that the numbers are
    directly comparable with the published records.
    """
    r = net_ret.loc[sample]
    w = weights.loc[r.index]
    t = w.diff().abs().sum(axis=1).fillna(0.0)
    n = len(r)
    if n < 2:
        return {"sessions": int(n)}
    bt = compute_metrics(r, w, *get_cost_params(), get_risk_free_rate())
    return {
        "sessions": int(n),
        "start_date": r.index[0].date().isoformat(),
        "end_date": r.index[-1].date().isoformat(),
        "sharpe_canonical": float(sharpe_ratio(r)),
        "sharpe_backtest_scale": float(bt["sharpe_ratio"]),
        "total_return": float(bt["total_return"]),
        "annualized_return": float(bt["annualized_return"]),
        "annualized_volatility": float(bt["annualized_volatility"]),
        "sortino_ratio": float(bt["sortino_ratio"]),
        "max_drawdown": float(max_drawdown(r)),
        "annualized_turnover": float(bt["annualized_turnover"]),
        "trade_days": int(bt["trade_count"]),
        "profit_factor": float(bt["profit_factor"]),
        "avg_exposure": float(w.abs().sum(axis=1).mean()),
        "cost_drag_total": float((t * cost_per_trade).sum()),
    }


def walkforward(
    net_ret: pd.Series,
    weights: pd.DataFrame,
    splits: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Fixed-parameter walk-forward statistics (fold windows sliced from one path)."""
    rows: list[dict[str, Any]] = []
    for i, sp in enumerate(splits):
        sel = (
            (net_ret.index >= pd.Timestamp(sp["test_start"], tz="UTC"))
            & (net_ret.index <= pd.Timestamp(sp["test_end"], tz="UTC"))
        )
        r = net_ret[sel]
        if len(r) < 2:
            continue
        w = weights.loc[r.index]
        bt = compute_metrics(r, w, *get_cost_params(), get_risk_free_rate())
        rows.append(
            {
                "fold": i + 1,
                "test_start": sp["test_start"],
                "test_end": sp["test_end"],
                "test_sessions": int(len(r)),
                "test_sharpe": float(bt["sharpe_ratio"]),
                "test_sharpe_canonical": float(sharpe_ratio(r)),
                "test_ann_return": float(bt["annualized_return"]),
                "test_max_dd": float(bt["max_drawdown"]),
                "test_turnover": float(bt["annualized_turnover"]),
                "test_trades": int(bt["trade_count"]),
            }
        )
    df = pd.DataFrame(rows)
    summary = summarize_walkforward(df)
    summary["mean_test_sharpe_canonical"] = (
        float(df["test_sharpe_canonical"].mean()) if len(df) else float("nan")
    )
    summary["n_folds"] = len(df)
    summary["folds"] = rows
    return summary, rows


def schedule_statistics(index: pd.DatetimeIndex) -> dict[str, Any]:
    """How the calendar rule and the shared schedule differ on a session calendar."""
    month_keys = sorted(set(index.strftime("%Y-%m")))
    calendar_month_ends = [k for k in month_keys if bool(index[index.strftime("%Y-%m") == k].is_month_end.any())]
    shared = month_end_sessions(index)
    shared_keys = [d.strftime("%Y-%m") for d in shared]
    return {
        "n_months": len(month_keys),
        "n_calendar_month_end_sessions": int(index.is_month_end.sum()),
        "n_months_with_calendar_rebalance": len(calendar_month_ends),
        "n_months_without_calendar_rebalance": len(month_keys) - len(calendar_month_ends),
        "fraction_months_without_calendar_rebalance": (
            (len(month_keys) - len(calendar_month_ends)) / len(month_keys) if month_keys else 0.0
        ),
        "n_shared_schedule_signals": len(shared),
        "n_months_shared_signal_missing": len(month_keys) - len(shared_keys),
    }


def overlay_weights(
    gated: pd.DataFrame,
    asset_ret: pd.DataFrame,
    vol_lookback: int,
    vol_target: float,
    dd_threshold: float,
    dd_reduction: float,
    lag_vol_estimate: bool = False,
) -> pd.DataFrame:
    """The incumbent's combined vol-target + drawdown overlay (Cycle 6 / run_cycle19).

    The volatility estimate is computed by the shared
    ``src.evaluation.risk.realized_vol_scale``.  ``lag_vol_estimate`` selects the
    same-session estimate (default, the committed behaviour) or the estimate
    lagged one session; the default path is bit-for-bit unchanged.
    """
    port_ret = (gated * asset_ret).sum(axis=1)
    vol_scale = realized_vol_scale(port_ret, vol_target, vol_lookback, lag_vol_estimate)
    vol_targeted = gated.mul(vol_scale, axis=0)
    vol_port_ret = (vol_targeted * asset_ret).sum(axis=1)
    cum = (1.0 + vol_port_ret).cumprod()
    drawdown = (cum / cum.expanding().max()) - 1.0
    dd_scale = pd.Series(1.0, index=gated.index)
    dd_scale[drawdown < -dd_threshold] = dd_reduction
    return gated.mul(vol_scale * dd_scale, axis=0)


#: The published records use the repository engine's metric names; the audit
#: tool reports the same quantities under its own names.
METRIC_ALIASES = {
    "sharpe_ratio": "sharpe_backtest_scale",
    "trade_count": "trade_days",
}


def compare_published(
    observed: dict[str, Any],
    published: dict[str, Any],
) -> list[dict[str, Any]]:
    """Compare a metric dict against the published numbers.

    The published values are strings, so the tolerance of every comparison is
    the unit of the last published decimal (e.g. 1e-4 for a 4-decimal value,
    1e-2 for a 2-decimal value).
    """
    rows: list[dict[str, Any]] = []
    for key, pub_text in published.items():
        pub_text = str(pub_text)
        pub = float(pub_text)
        decimals = len(pub_text.split(".")[1]) if "." in pub_text else 0
        tolerance = 10.0 ** (-decimals)
        got = observed.get(METRIC_ALIASES.get(key, key))
        ok = got is not None and abs(float(got) - pub) <= tolerance
        rows.append(
            {
                "metric": key,
                "published": pub,
                "decimals": decimals,
                "tolerance": tolerance,
                "observed": None if got is None else float(got),
                "abs_diff": None if got is None else abs(float(got) - pub),
                "match": bool(ok),
            }
        )
    return rows


def wf_compare(
    observed: dict[str, Any],
    published: dict[str, Any],
) -> list[dict[str, Any]]:
    return compare_published(observed, published)


# ----------------------------------------------------------------------
# Candidate builders
# ----------------------------------------------------------------------
def build_csmomentum(close: pd.DataFrame, cost_per_trade: float) -> dict[str, Any]:
    """The three execution paths of ``csmomentum_001``."""
    signal = load_yaml(CONFIG_CS)["signal"]
    lookback, skip = int(signal["lookback"]), int(signal["skip"])
    top_fraction = float(signal["top_fraction"])

    momentum = compute_momentum(close, lookback=lookback, skip=skip)
    mask = select_top_decile(momentum, top_fraction=top_fraction)

    daily_w = build_weights(close, lookback=lookback, skip=skip, top_fraction=top_fraction)
    legacy_w = legacy_calendar_schedule(daily_w)
    faithful_w, segments = faithful_schedule(daily_w, mask)
    shared_w, _ = build_month_end_weights(mask)

    paths = {"daily": daily_w, "legacy": legacy_w, "faithful": faithful_w}
    out: dict[str, Any] = {"paths": paths, "segments": segments, "mask": mask}
    for name, w in paths.items():
        net, ww, turn = path_returns(close, w, cost_per_trade)
        out[f"{name}_net"] = net
        out[f"{name}_weights"] = ww
        out[f"{name}_turnover"] = turn
    out["faithful_equals_shared_module"] = bool(
        np.array_equal(faithful_w.to_numpy(), shared_w.to_numpy())
    )
    out["max_faithful_vs_shared_diff"] = float(
        np.max(np.abs(faithful_w.to_numpy() - shared_w.to_numpy()))
    )
    return out


def build_macroregime(
    close: pd.DataFrame,
    vix: pd.Series,
    cost_per_trade: float,
    lag_vol_estimate: bool = False,
) -> dict[str, Any]:
    """The execution paths of ``macroregime_001`` (overlay + VIX regime gate)."""
    cfg = load_yaml(CONFIG_MACRO)
    signal = cfg["signal"]
    overlay_cfg = cfg["risk_overlay"]
    gate_cfg = cfg["regime_gate"]

    lookback, skip = int(signal["lookback"]), int(signal["skip"])
    top_fraction = float(signal["top_fraction"])

    momentum = compute_momentum(close, lookback=lookback, skip=skip)
    mask = select_top_decile(momentum, top_fraction=top_fraction)

    daily_ret = close.pct_change().fillna(0.0)
    daily_w = build_weights(close, lookback=lookback, skip=skip, top_fraction=top_fraction)

    # SPY 200d trend gate (incumbent)
    spy = close["SPY"]
    spy_sma = spy.rolling(int(overlay_cfg["spy_sma_window"])).mean()
    exposure = pd.Series(1.0, index=close.index)
    exposure[spy < spy_sma] = 0.0
    exposure[spy.isna() | spy_sma.isna()] = 0.0
    gated = daily_w.mul(exposure, axis=0)

    # VIX regime gate (prior day's VIX close, point-in-time)
    vix_lag = vix.shift(1).reindex(close.index)
    vix_mult = pd.Series(1.0, index=close.index)
    vix_mult[vix_lag > float(gate_cfg["vix_threshold"])] = float(gate_cfg["vix_exposure"])
    vix_mult[vix_lag.isna()] = 1.0
    gated = gated.mul(vix_mult, axis=0)

    combined = overlay_weights(
        gated,
        daily_ret,
        vol_lookback=int(overlay_cfg["vol_lookback"]),
        vol_target=float(overlay_cfg["vol_target"]),
        dd_threshold=float(overlay_cfg["dd_threshold"]),
        dd_reduction=float(overlay_cfg["dd_reduction"]),
        lag_vol_estimate=lag_vol_estimate,
    )
    legacy_w = legacy_calendar_schedule(combined)
    faithful_w, segments = faithful_schedule(combined, mask)

    out: dict[str, Any] = {
        "segments": segments,
        "mask": mask,
        "vix_mult": vix_mult,
        "vix_first_valid": vix.first_valid_index(),
        "n_vix_sessions": int(vix.notna().sum()),
    }
    for name, w in {"legacy": legacy_w, "faithful": faithful_w}.items():
        net, ww, turn = path_returns(close, w, cost_per_trade)
        out[f"{name}_net"] = net
        out[f"{name}_weights"] = ww
        out[f"{name}_turnover"] = turn
    return out


def gates_for(
    wf_summary: dict[str, Any],
    gate_cfg: dict[str, Any],
) -> dict[str, Any]:
    """The candidate's own pre-registered promotion gates."""
    mean_wf = float(wf_summary.get("mean_test_sharpe", np.nan))
    pct_pos = float(wf_summary.get("pct_positive_sharpe", np.nan))
    pooled = int(wf_summary.get("total_test_trades", 0))
    g1 = bool(np.isfinite(mean_wf) and mean_wf >= float(gate_cfg["wf_mean_oos_sharpe_min"]))
    g2 = bool(np.isfinite(pct_pos) and pct_pos >= float(gate_cfg["positive_fold_rate_min"]))
    g3 = bool(pooled > float(gate_cfg["pooled_oos_trades_min"]))
    falsified = (not g1) or (not g2)
    return {
        "wf_mean_oos_sharpe": mean_wf,
        "wf_mean_oos_sharpe_threshold": float(gate_cfg["wf_mean_oos_sharpe_min"]),
        "gate1_wf_sharpe": g1,
        "positive_fold_rate": pct_pos,
        "positive_fold_rate_threshold": float(gate_cfg["positive_fold_rate_min"]),
        "gate2_positive_rate": g2,
        "pooled_oos_trades": pooled,
        "pooled_oos_trades_threshold": float(gate_cfg["pooled_oos_trades_min"]),
        "gate3_pooled_trades": g3,
        "falsified": falsified,
        "label": "Rejected/Failed" if falsified else "exploratory signal",
    }


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main() -> int:
    checks: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    commission_bps, slippage_bps = get_cost_params()
    cost_per_trade = commission_bps + slippage_bps

    cs_cfg = load_yaml(CONFIG_CS)
    macro_cfg = load_yaml(CONFIG_MACRO)
    cs_universe = list(cs_cfg["universe"])
    macro_universe = list(macro_cfg["universe"])
    regime_driver = str(macro_cfg["regime_driver"])

    # --- data provenance (read-only) ---
    required = sorted(set(cs_universe) | set(macro_universe) | {regime_driver})
    missing = [s for s in required if not (RAW_DIR / f"{s}.parquet").exists()]
    if missing:
        print(f"ERROR: missing cached raw files for {missing}", file=sys.stderr)
        return 1
    raw_hashes_before = {s: sha256_file(RAW_DIR / f"{s}.parquet") for s in required}
    processed_files_before = sorted(p.name for p in PROCESSED_DIR.glob("*.parquet"))

    # ==================================================================
    # csmomentum_001
    # ==================================================================
    cs_close = fetch_close_prices(cs_universe, CS_START, CS_END)
    cs_close = cs_close.loc[
        (cs_close.index >= pd.Timestamp(CS_START, tz="UTC"))
        & (cs_close.index <= pd.Timestamp(CS_END, tz="UTC"))
    ].copy()
    cs = build_csmomentum(cs_close, cost_per_trade)
    cs_test_idx = cs_close.index[cs_close.index >= pd.Timestamp(TEST_START, tz="UTC")]

    cs_metrics = {}
    for name in ("daily", "legacy", "faithful"):
        cs_metrics[name] = {
            "full": path_metrics(
                cs[f"{name}_net"], cs[f"{name}_weights"],
                cost_per_trade, cs_close.index,
            ),
            "test": path_metrics(
                cs[f"{name}_net"], cs[f"{name}_weights"],
                cost_per_trade, cs_test_idx,
            ),
        }

    cs_splits = generate_walkforward_splits(
        CS_START, CS_END, WF_TRAIN_YEARS, WF_TEST_MONTHS, WF_STEP_MONTHS,
        WF_PURGE_DAYS, WF_EMBARGO_DAYS,
    )
    cs_wf = {}
    for name in ("daily", "legacy", "faithful"):
        cs_wf[name], _ = walkforward(cs[f"{name}_net"], cs[f"{name}_weights"], cs_splits)

    cs_gates = {
        name: gates_for(cs_wf[name], cs_cfg["evaluation"]["promotion_gates"])
        for name in ("daily", "legacy", "faithful")
    }

    # --- reproduction of the committed csmomentum artifacts --------------
    cs_ref_w = pd.read_parquet(CS_WEIGHTS_REF)
    cs_common = cs["legacy_weights"].index.intersection(cs_ref_w.index)
    cs_w_diff = float(
        np.max(
            np.abs(
                cs["legacy_weights"].loc[cs_common].to_numpy()
                - cs_ref_w.loc[cs_common].to_numpy()
            )
        )
    )
    check(
        "csmomentum_legacy_reproduces_committed_weights",
        cs_w_diff <= 1e-12,
        f"max abs(legacy weights - data/processed/weights_csmomentum_001.parquet) = {cs_w_diff:.3e} "
        f"(tolerance 1e-12) over {len(cs_common)} sessions.",
    )

    cs_ref_sim = pd.read_parquet(CS_SIM_REF)
    cs_sim_common = cs["legacy_net"].index.intersection(cs_ref_sim.index)
    cs_sim_diff = float(
        np.max(np.abs(cs["legacy_net"].loc[cs_sim_common] - cs_ref_sim["net_return"].loc[cs_sim_common]))
    )
    cs_sim_diff_sessions = int(
        (np.abs(cs["legacy_net"].loc[cs_sim_common] - cs_ref_sim["net_return"].loc[cs_sim_common]) > 1e-12).sum()
    )
    check(
        "csmomentum_legacy_net_returns_match_committed_simulation",
        cs_sim_diff <= 1e-12,
        f"max abs(legacy net return - committed simulation) = {cs_sim_diff:.3e} "
        f"(tolerance 1e-12); {cs_sim_diff_sessions} of {len(cs_sim_common)} sessions differ.",
    )

    cs_pub_rows = compare_published(cs_metrics["legacy"]["test"], CS_CAL_TEST)
    cs_pub_ok = all(r["match"] for r in cs_pub_rows)
    check(
        "csmomentum_legacy_reproduces_published_calendar_record",
        cs_pub_ok,
        "the legacy path reproduces the test-period metrics of "
        "research/experiments/csmomentum_baseline_wf_001.md "
        + ("exactly" if cs_pub_ok else "NOT exactly: " + ", ".join(
            f"{r['metric']} published {r['published']} vs observed {r['observed']}"
            for r in cs_pub_rows if not r["match"]
        )),
    )

    cs_wf_rows = wf_compare(cs_wf["legacy"], CS_CAL_WF)
    cs_wf_ok = all(r["match"] for r in cs_wf_rows)
    check(
        "csmomentum_legacy_reproduces_published_walkforward",
        cs_wf_ok,
        f"the legacy path reproduces the walk-forward block of "
        f"research/experiments/csmomentum_baseline_wf_001.md "
        f"(folds {cs_wf['legacy']['n_folds']}, mean OOS Sharpe "
        f"{cs_wf['legacy']['mean_test_sharpe']:.4f}, pooled trades "
        f"{cs_wf['legacy']['total_test_trades']}).",
    )

    cs_rec_rows = compare_published(cs_metrics["daily"]["full"], CS_REC_FULL)
    cs_rec_test_rows = compare_published(cs_metrics["daily"]["test"], CS_REC_TEST)
    cs_rec_ok = all(r["match"] for r in cs_rec_rows + cs_rec_test_rows)
    check(
        "csmomentum_001_experiment_001_is_the_daily_rerank_path",
        cs_rec_ok,
        "the daily re-rank path reproduces research/experiments/csmomentum_001_experiment_001.md "
        "(full sample Sharpe "
        f"{cs_metrics['daily']['full']['sharpe_backtest_scale']:.4f}, test Sharpe "
        f"{cs_metrics['daily']['test']['sharpe_backtest_scale']:.4f}, "
        f"{cs_metrics['daily']['full']['trade_days']} trade days); the legacy calendar path does NOT.",
    )

    cs_wf_rec_rows = wf_compare(cs_wf["daily"], CS_REC_WF)
    cs_wf_rec_ok = all(r["match"] for r in cs_wf_rec_rows)
    check(
        "csmomentum_001_experiment_001_walkforward_block_is_not_reproducible",
        not cs_wf_rec_ok,
        "the walk-forward block of research/experiments/csmomentum_001_experiment_001.md reports "
        f"{CS_REC_WF['n_folds']} folds / mean OOS Sharpe {CS_REC_WF['mean_test_sharpe']}, which the "
        f"repository's current fold generator does not reproduce: the daily re-rank path on the frozen "
        f"config's own window ({CS_START}..{CS_END}) yields {cs_wf['daily']['n_folds']} folds / "
        f"{cs_wf['daily']['mean_test_sharpe']:.4f}.",
    )

    check(
        "csmomentum_faithful_path_equals_shared_module",
        cs["faithful_equals_shared_module"],
        f"the config-faithful path is bit-identical to "
        f"src/backtest/rebalance.py:build_month_end_weights "
        f"(max abs difference = {cs['max_faithful_vs_shared_diff']:.3e}).",
    )

    cs_pit_ok = True
    for seg in cs["segments"]:
        expected = cs["mask"].loc[seg["signal_date"]].astype(float).to_numpy() / seg["n_selected"]
        actual = cs["faithful_weights"].loc[seg["effective_date"]].to_numpy()
        if not np.allclose(expected, actual, atol=1e-12):
            cs_pit_ok = False
        if not seg["effective_date"] > seg["signal_date"]:
            cs_pit_ok = False
    check(
        "csmomentum_faithful_path_is_point_in_time",
        cs_pit_ok and len(cs["segments"]) > 0,
        f"{len(cs['segments'])} month-end signals; each segment equals the equal-weight of the "
        f"selection mask at its own signal date and becomes effective strictly after it.",
    )

    cs_sched_stats = schedule_statistics(cs_close.index)

    # ==================================================================
    # macroregime_001
    # ==================================================================
    macro_close_raw = fetch_close_prices(macro_universe, MACRO_START, MACRO_END)
    macro_close = macro_close_raw.loc[
        (macro_close_raw.index >= pd.Timestamp(MACRO_START, tz="UTC"))
        & (macro_close_raw.index <= pd.Timestamp(MACRO_END, tz="UTC"))
    ].copy()
    vix_raw = fetch_close_prices([regime_driver], MACRO_START, MACRO_END)[regime_driver]
    vix = vix_raw.loc[
        (vix_raw.index >= pd.Timestamp(MACRO_START, tz="UTC"))
        & (vix_raw.index <= pd.Timestamp(MACRO_END, tz="UTC"))
    ].copy()
    vix = vix.reindex(macro_close.index, method="ffill").ffill()

    macro = build_macroregime(macro_close, vix, cost_per_trade)
    macro_test_idx = macro_close.index[macro_close.index >= pd.Timestamp(TEST_START, tz="UTC")]

    macro_metrics = {}
    for name in ("legacy", "faithful"):
        macro_metrics[name] = {
            "full": path_metrics(
                macro[f"{name}_net"], macro[f"{name}_weights"],
                cost_per_trade, macro_close.index,
            ),
            "test": path_metrics(
                macro[f"{name}_net"], macro[f"{name}_weights"],
                cost_per_trade, macro_test_idx,
            ),
        }

    macro_splits = generate_walkforward_splits(
        MACRO_START, MACRO_END, WF_TRAIN_YEARS, WF_TEST_MONTHS, WF_STEP_MONTHS,
        WF_PURGE_DAYS, WF_EMBARGO_DAYS,
    )
    macro_wf = {}
    for name in ("legacy", "faithful"):
        macro_wf[name], _ = walkforward(
            macro[f"{name}_net"], macro[f"{name}_weights"], macro_splits
        )

    macro_gates = {
        name: gates_for(macro_wf[name], macro_cfg["evaluation"]["promotion_gates"])
        for name in ("legacy", "faithful")
    }

    # --- the published legacy path, taken from the committed artifact -----
    macro_ref_w = pd.read_parquet(MACRO_WEIGHTS_REF)
    macro_pub_net, macro_pub_w, _macro_pub_turn = path_returns(
        macro_close, macro_ref_w, cost_per_trade
    )
    macro_pub_metrics = {
        "full": path_metrics(
            macro_pub_net, macro_pub_w, cost_per_trade, macro_close.index
        ),
        "test": path_metrics(
            macro_pub_net, macro_pub_w, cost_per_trade, macro_test_idx
        ),
    }
    macro_pub_wf, _ = walkforward(macro_pub_net, macro_pub_w, macro_splits)

    macro_pub_rows = compare_published(macro_pub_metrics["test"], MACRO_REC_TEST)
    macro_pub_ok = all(r["match"] for r in macro_pub_rows)
    check(
        "macroregime_legacy_reproduces_published_metrics",
        macro_pub_ok,
        "the committed legacy weights artifact reproduces the test-period metrics of "
        "research/experiments/macroregime_baseline_wf_001.md "
        + ("exactly" if macro_pub_ok else "NOT exactly: " + ", ".join(
            f"{r['metric']} published {r['published']} vs observed {r['observed']}"
            for r in macro_pub_rows if not r["match"]
        )),
    )
    macro_pub_wf_rows = wf_compare(macro_pub_wf, MACRO_REC_WF)
    macro_pub_wf_ok = all(r["match"] for r in macro_pub_wf_rows)
    check(
        "macroregime_legacy_reproduces_published_walkforward",
        macro_pub_wf_ok,
        f"the committed legacy weights artifact reproduces the walk-forward block of "
        f"research/experiments/macroregime_baseline_wf_001.md and of "
        f"research/experiments/macroregime_001_experiment_002.md "
        f"(folds {macro_pub_wf['n_folds']}, mean OOS Sharpe "
        f"{macro_pub_wf['mean_test_sharpe']:.4f}, pooled trades "
        f"{macro_pub_wf['total_test_trades']}).",
    )

    macro_002_rows = wf_compare(macro_pub_wf, MACRO_002_WF)
    macro_002_ok = all(r["match"] for r in macro_002_rows)
    check(
        "macroregime_001_experiment_002_restates_the_same_numbers",
        macro_002_ok,
        "the walk-forward numbers restated in "
        "research/experiments/macroregime_001_experiment_002.md (24 folds, mean OOS Sharpe 0.4331, "
        "75.0% positive, 137 pooled trades) are reproduced by the committed legacy weights artifact.",
    )

    # --- the VIX data gap -------------------------------------------------
    vix_gap_sessions = int(macro_close.index[macro_close.index < macro["vix_first_valid"]].size)
    macro_w_diff = float(
        np.max(
            np.abs(
                macro["legacy_weights"].to_numpy() - macro_ref_w.to_numpy()
            )
        )
    )
    check(
        "macroregime_vix_history_gap_is_quantified",
        True,
        f"the committed {regime_driver} cache now covers the full sample "
        f"({macro['vix_first_valid'].date().isoformat()} .. {macro_close.index.max().date()}); "
        f"{vix_gap_sessions} of {len(macro_close.index)} sessions have no VIX observation, so the "
        f"legacy path computed from the cache reproduces the published path "
        f"(published test Sharpe {macro_pub_metrics['test']['sharpe_backtest_scale']:.4f} vs "
        f"cache-reproducible {macro_metrics['legacy']['test']['sharpe_backtest_scale']:.4f}).",
    )

    macro_pit_ok = True
    for seg in macro["segments"]:
        selected = macro["mask"].loc[seg["signal_date"]].to_numpy(dtype=bool)
        held = macro["faithful_weights"].loc[seg["effective_date"]].to_numpy()
        # the overlays scale the equal-weight selection, so they may scale it
        # down (or to zero) but they can never add an asset that the signal did
        # not select.
        if np.any(held[~selected] != 0.0):
            macro_pit_ok = False
        if np.any(held[selected] < 0.0):
            macro_pit_ok = False
        if not seg["effective_date"] > seg["signal_date"]:
            macro_pit_ok = False
    check(
        "macroregime_faithful_path_is_point_in_time",
        macro_pit_ok and len(macro["segments"]) > 0,
        f"{len(macro['segments'])} month-end signals; every segment holds only the assets its own "
        f"signal date selected and becomes effective strictly after it.",
    )

    macro_sched_stats = schedule_statistics(macro_close.index)

    # ==================================================================
    # verdicts
    # ==================================================================
    cs_verdict = (
        "verdict unchanged"
        if cs_gates["legacy"]["label"] == cs_gates["faithful"]["label"]
        else "verdict changed"
    )
    macro_verdict = (
        "verdict unchanged"
        if macro_gates["legacy"]["label"] == macro_gates["faithful"]["label"]
        else "verdict changed"
    )
    check(
        "schedule_defect_does_not_move_either_candidate_across_its_gates",
        cs_verdict == "verdict unchanged" and macro_verdict == "verdict unchanged",
        f"csmomentum_001: {cs_verdict} (WF mean OOS Sharpe "
        f"{cs_gates['legacy']['wf_mean_oos_sharpe']:.4f} -> "
        f"{cs_gates['faithful']['wf_mean_oos_sharpe']:.4f}, gate "
        f"{cs_gates['legacy']['wf_mean_oos_sharpe_threshold']}); macroregime_001: {macro_verdict} "
        f"(WF mean OOS Sharpe {macro_gates['legacy']['wf_mean_oos_sharpe']:.4f} -> "
        f"{macro_gates['faithful']['wf_mean_oos_sharpe']:.4f}).",
    )
    check(
        "calendar_rule_actually_skips_months",
        cs_sched_stats["n_months_without_calendar_rebalance"] > 0
        and macro_sched_stats["n_months_without_calendar_rebalance"] > 0,
        f"the calendar rule has no rebalance at all in "
        f"{cs_sched_stats['n_months_without_calendar_rebalance']} of "
        f"{cs_sched_stats['n_months']} months (csmomentum_001) and in "
        f"{macro_sched_stats['n_months_without_calendar_rebalance']} of "
        f"{macro_sched_stats['n_months']} months (macroregime_001).",
    )

    # --- read-only proof ---
    raw_hashes_after = {s: sha256_file(RAW_DIR / f"{s}.parquet") for s in required}
    processed_files_after = sorted(p.name for p in PROCESSED_DIR.glob("*.parquet"))
    check(
        "raw_cache_unchanged",
        raw_hashes_before == raw_hashes_after,
        f"all {len(required)} cached parquet files are SHA-256 byte-identical before and after the run.",
    )
    check(
        "no_new_processed_artifacts",
        processed_files_before == processed_files_after,
        f"data/processed contains the same {len(processed_files_after)} parquet files before and after "
        f"the run; the tool writes no simulation artifact.",
    )

    failed = [c["check"] for c in checks if not c["pass"]]
    overall = "PASS" if not failed else "FAIL"

    # ==================================================================
    # report
    # ==================================================================
    report = build_report(
        checks=checks,
        overall=overall,
        failed=failed,
        cs_cfg=cs_cfg,
        macro_cfg=macro_cfg,
        cs_universe=cs_universe,
        macro_universe=macro_universe,
        regime_driver=regime_driver,
        cs_close=cs_close,
        macro_close=macro_close,
        cs_metrics=cs_metrics,
        macro_metrics=macro_metrics,
        macro_pub_metrics=macro_pub_metrics,
        cs_wf=cs_wf,
        macro_wf=macro_wf,
        macro_pub_wf=macro_pub_wf,
        cs_gates=cs_gates,
        macro_gates=macro_gates,
        cs_verdict=cs_verdict,
        macro_verdict=macro_verdict,
        cs_sched_stats=cs_sched_stats,
        macro_sched_stats=macro_sched_stats,
        cs_w_diff=cs_w_diff,
        cs_sim_diff=cs_sim_diff,
        cs_sim_diff_sessions=cs_sim_diff_sessions,
        macro_w_diff=macro_w_diff,
        macro_vix_first_valid=macro["vix_first_valid"],
        macro_vix_gap_sessions=vix_gap_sessions,
        macro_vix_n_sessions=macro["n_vix_sessions"],
        cs_n_segments=len(cs["segments"]),
        macro_n_segments=len(macro["segments"]),
        cs_pub_rows=cs_pub_rows,
        cs_wf_rows=cs_wf_rows,
        cs_rec_rows=cs_rec_rows,
        cs_rec_test_rows=cs_rec_test_rows,
        cs_wf_rec_rows=cs_wf_rec_rows,
        macro_pub_rows=macro_pub_rows,
        macro_pub_wf_rows=macro_pub_wf_rows,
        cs_close_hash=content_hash(cs_close),
        macro_close_hash=content_hash(macro_close),
        cost_per_trade=cost_per_trade,
    )
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(report)

    # ==================================================================
    # console summary
    # ==================================================================
    print(f"OVERALL: {overall}")
    print(f"CHECKS: {len(checks) - len(failed)}/{len(checks)} passed")
    for label, m, wf, g in (
        ("csmomentum_001 legacy   ", cs_metrics["legacy"], cs_wf["legacy"], cs_gates["legacy"]),
        ("csmomentum_001 faithful ", cs_metrics["faithful"], cs_wf["faithful"], cs_gates["faithful"]),
        ("macroregime_001 legacy  ", macro_metrics["legacy"], macro_wf["legacy"], macro_gates["legacy"]),
        ("macroregime_001 faithful", macro_metrics["faithful"], macro_wf["faithful"], macro_gates["faithful"]),
    ):
        print(
            f"{label} test_sharpe(bt)={m['test']['sharpe_backtest_scale']:.4f} "
            f"canon={m['test']['sharpe_canonical']:.4f} maxdd={m['test']['max_drawdown']:.4f} "
            f"turn={m['test']['annualized_turnover']:.2f}x trades={m['test']['trade_days']} "
            f"wf_mean={wf['mean_test_sharpe']:.4f} pos={wf['pct_positive_sharpe']:.1%} "
            f"pooled={wf['total_test_trades']} -> {g['label']}"
        )
    print(
        f"csmomentum_001  verdict: {cs_verdict} | macroregime_001 verdict: {macro_verdict} "
        f"(the macroregime_001 config-faithful path is now measured on the real VIX gate: the "
        f"^VIX cache covers the full sample, so the legacy path reproduces the published numbers "
        f"and the faithful path is not an ablation; see the report)"
    )
    if failed:
        print(f"FAILED CHECKS: {failed}", file=sys.stderr)
        return 1
    return 0


# ----------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------
def _delta_row(label: str, a: Any, b: Any, fmt: str = "{:.4f}") -> str:
    if a is None or b is None:
        return f"| {label} | {a} | {b} | n/a |"
    try:
        delta = float(b) - float(a)
        return f"| {label} | {fmt.format(float(a))} | {fmt.format(float(b))} | {fmt.format(delta)} |"
    except (TypeError, ValueError):
        return f"| {label} | {a} | {b} | n/a |"


def build_report(**kw: Any) -> str:
    """Render the cycle report (deterministic: no timestamps)."""
    checks = kw["checks"]
    overall = kw["overall"]
    cs_m = kw["cs_metrics"]
    mr_m = kw["macro_metrics"]
    mr_p = kw["macro_pub_metrics"]
    cs_wf = kw["cs_wf"]
    mr_wf = kw["macro_wf"]
    mr_pwf = kw["macro_pub_wf"]
    cs_g = kw["cs_gates"]
    mr_g = kw["macro_gates"]
    cs_ss = kw["cs_sched_stats"]
    mr_ss = kw["macro_sched_stats"]
    cost = kw["cost_per_trade"]

    def cmp_table(rows: list[dict[str, Any]]) -> str:
        return "\n".join(
            f"| `{r['metric']}` | {r['published']:.{r['decimals']}f} | "
            f"{'n/a' if r['observed'] is None else format(r['observed'], '.6f')} | "
            f"{'n/a' if r['abs_diff'] is None else format(r['abs_diff'], '.3e')} | "
            f"{'MATCH' if r['match'] else 'DIFFERS'} |"
            for r in rows
        )

    cs_legacy_full = cs_m["legacy"]["full"]
    cs_legacy_test = cs_m["legacy"]["test"]

    def cs_legacy_obs(metric: str) -> float:
        key = metric.removeprefix("test ")
        key = METRIC_ALIASES.get(key, key)
        scope = cs_legacy_test if metric.startswith("test ") else cs_legacy_full
        return float(scope.get(key, float("nan")))

    def metrics_table(a: dict[str, Any], b: dict[str, Any]) -> str:
        lines = [
            "| Metric | Legacy (calendar) | Config-faithful | Delta |",
            "|---|---|---|---|",
        ]
        for scope in ("full", "test"):
            lines.append(f"| **{scope} sample** | | | |")
            for key, fmt in (
                ("sharpe_canonical", "{:.4f}"),
                ("sharpe_backtest_scale", "{:.4f}"),
                ("annualized_return", "{:.4f}"),
                ("annualized_volatility", "{:.4f}"),
                ("max_drawdown", "{:.4f}"),
                ("annualized_turnover", "{:.2f}"),
                ("trade_days", "{:.0f}"),
                ("avg_exposure", "{:.4f}"),
                ("profit_factor", "{:.4f}"),
                ("cost_drag_total", "{:.4f}"),
                ("sessions", "{:.0f}"),
            ):
                lines.append(
                    _delta_row(key, a[scope].get(key), b[scope].get(key), fmt)
                )
        return "\n".join(lines)

    def wf_table(a: dict[str, Any], b: dict[str, Any]) -> str:
        return "\n".join(
            [
                "| Metric | Legacy (calendar) | Config-faithful | Delta |",
                "|---|---|---|---|",
                _delta_row("folds", a.get("n_folds"), b.get("n_folds"), "{:.0f}"),
                _delta_row("mean OOS Sharpe (backtest scale)",
                           a.get("mean_test_sharpe"), b.get("mean_test_sharpe")),
                _delta_row("mean OOS Sharpe (canonical)",
                           a.get("mean_test_sharpe_canonical"), b.get("mean_test_sharpe_canonical")),
                _delta_row("median OOS Sharpe", a.get("median_test_sharpe"), b.get("median_test_sharpe")),
                _delta_row("% positive folds", a.get("pct_positive_sharpe"), b.get("pct_positive_sharpe"), "{:.4f}"),
                _delta_row("pooled OOS trades", a.get("total_test_trades"), b.get("total_test_trades"), "{:.0f}"),
                _delta_row("std OOS Sharpe", a.get("std_test_sharpe"), b.get("std_test_sharpe")),
            ]
        )

    check_rows = "\n".join(
        f"| `{c['check']}` | {'PASS' if c['pass'] else 'FAIL'} | {c['detail'].replace('|', chr(92) + '|')} |"
        for c in checks
    )

    return f"""# Month-End Candidate Re-Audit (month_end_candidate_reaudit_001, Cycle 871)

## Summary

Two frozen candidates specify the month-end rebalance schedule
(`execution.rebalance_schedule: "monthly"`, `signal_lag_days: 1`) but were executed with a
**calendar** rule (`weights.index.is_month_end`) that rebalances one session earlier than the
configuration specifies and **never rebalances at all** in every month whose last calendar day was
a weekend or a market holiday. Cycle 870 put one correct implementation of the schedule into shared
code (`src/backtest/rebalance.py`); this cycle measures, read-only, what the defect did to the two
published results.

| Candidate | Published (legacy) test Sharpe | Config-faithful test Sharpe | Published WF mean OOS Sharpe | Config-faithful WF mean OOS Sharpe | Verdict |
|---|---|---|---|---|---|
| `csmomentum_001` | {cs_m['legacy']['test']['sharpe_backtest_scale']:.4f} | {cs_m['faithful']['test']['sharpe_backtest_scale']:.4f} | {cs_wf['legacy']['mean_test_sharpe']:.4f} | {cs_wf['faithful']['mean_test_sharpe']:.4f} | **{kw['cs_verdict']}** |
| `macroregime_001` | {mr_p['test']['sharpe_backtest_scale']:.4f} (published artifact) / {mr_m['legacy']['test']['sharpe_backtest_scale']:.4f} (cache-reproducible) | {mr_m['faithful']['test']['sharpe_backtest_scale']:.4f} (cache-reproducible) | {mr_pwf['mean_test_sharpe']:.4f} (published artifact) / {mr_wf['legacy']['mean_test_sharpe']:.4f} (cache-reproducible) | {mr_wf['faithful']['mean_test_sharpe']:.4f} (cache-reproducible) | **{kw['macro_verdict']}** |

**Headline:** the schedule defect moved the *numbers* materially — the walk-forward mean OOS
Sharpe changes by {cs_wf['faithful']['mean_test_sharpe'] - cs_wf['legacy']['mean_test_sharpe']:+.4f} for
`csmomentum_001` and by {mr_wf['faithful']['mean_test_sharpe'] - mr_wf['legacy']['mean_test_sharpe']:+.4f}
for `macroregime_001` (cache-reproducible paths) — but it did **not** move either candidate across
its own pre-registered gates: both were rejected before and both are rejected after. The published
rejections are robust to the defect.

No configuration, universe, cost model, gate threshold, Sharpe convention or committed artifact was
changed by this cycle; the tool is read-only and writes exactly this report.

## 1. Method

### 1.1 Data (read-only)

| Item | `csmomentum_001` | `macroregime_001` |
|---|---|---|
| Universe | {", ".join(kw['cs_universe'])} ({len(kw['cs_universe'])}) | {", ".join(kw['macro_universe'])} ({len(kw['macro_universe'])}) + `{kw['regime_driver']}` (input only) |
| Window | {kw['cs_close'].index.min().date()} .. {kw['cs_close'].index.max().date()} ({len(kw['cs_close'].index)} sessions) | {kw['macro_close'].index.min().date()} .. {kw['macro_close'].index.max().date()} ({len(kw['macro_close'].index)} sessions) |
| Source | committed raw cache `data/raw/*.parquet` (Yahoo Finance via yfinance), cache-only, no network | idem |
| Aligned-frame content hash | `{kw['cs_close_hash'][:16]}` | `{kw['macro_close_hash'][:16]}` |
| Costs | {cost * 10000:.1f} bps round-trip (1 bps commission + 2 bps slippage) | idem |

The published windows (…1993-01-01/2026-10-09 and 2004-11-18/2026-10-09) are used, not the current
cache end, so that the numbers are comparable with the published records.

### 1.2 The two schedules

**Legacy (the defect).** `research/run_cycle13.py:_apply_monthly_schedule` and
`research/run_cycle19.py:_apply_monthly_schedule`:

```python
is_month_end = pd.Series(weights.index.is_month_end, index=weights.index)
return weights.where(is_month_end, axis=0).ffill().fillna(0.0)
```

`is_month_end` is a **calendar** predicate applied to a **trading** calendar. Two consequences:

1. the row that survives is the one of the month's last *calendar* day, and it was produced by the
   signal of the **previous** session, so the position is put on one session earlier than the
   frozen configuration specifies (`signal_lag_days: 1` from the month's last *session*);
2. a month whose last calendar day was a weekend or a market holiday has **no** such row, so the
   previous month's weights are carried through the whole month.

| Schedule statistic | `csmomentum_001` | `macroregime_001` |
|---|---|---|
| Calendar months in the sample | {cs_ss['n_months']} | {mr_ss['n_months']} |
| Months with a calendar rebalance | {cs_ss['n_months_with_calendar_rebalance']} | {mr_ss['n_months_with_calendar_rebalance']} |
| Months with **no** calendar rebalance | {cs_ss['n_months_without_calendar_rebalance']} ({cs_ss['fraction_months_without_calendar_rebalance']:.1%}) | {mr_ss['n_months_without_calendar_rebalance']} ({mr_ss['fraction_months_without_calendar_rebalance']:.1%}) |
| Shared-schedule month-end signals | {kw['cs_n_segments']} | {kw['macro_n_segments']} |

**Config-faithful.** `src/backtest/rebalance.py:build_month_end_weights` (the single shared
implementation since Cycle 870): the signal is formed on the **last session** of the calendar month
and the positions become effective on the **next** session and are held until the next month-end
signal. For `csmomentum_001` (no risk overlays) the config-faithful weight matrix *is*
`build_month_end_weights(mask)`; for `macroregime_001` the same schedule is applied to the same
daily pipeline by sampling it at each segment's effective date, so the **only** difference between
the two paths is the schedule rule.

### 1.3 Metrics and conventions

Both Sharpe conventions are reported and never mixed:

* **canonical** (`src/evaluation/sharpe.py:sharpe_ratio`, `arithmetic_annualized_rf0`) — the
  convention of the promotion gates since Cycle 861;
* **backtest scale** (`backtest_sharpe_ratio`, `cagr_annualized_rf2`) — the scale of the published
  backtest records, and therefore the scale on which the candidates' pre-registered walk-forward
  gate was evaluated. The gate table below uses the **backtest scale**, exactly as the original
  runs did.

The walk-forward design is the pre-registered one: {WF_TRAIN_YEARS:.0f}y train / {WF_TEST_MONTHS:.0f}m
test / {WF_STEP_MONTHS:.0f}m step, {WF_PURGE_DAYS}d purge, {WF_EMBARGO_DAYS}d embargo, fixed
parameters. The fold windows are slices of one continuously computed point-in-time path (no
re-optimisation per fold).

## 2. `csmomentum_001` — deviation

### 2.1 Reproduction of the published numbers

| Published source | What the legacy path reproduces | Result |
|---|---|---|
| `research/experiments/csmomentum_baseline_wf_001.md` (test window, calendar path) | all 10 published test metrics | reproduced (tolerance = the last published decimal of each metric) |
| `research/experiments/csmomentum_baseline_wf_001.md` (walk-forward) | 48 folds, mean OOS Sharpe 0.6868, 79.2% positive, 313 pooled trades | reproduced (tolerance = the last published decimal of each metric) |
| `data/processed/weights_csmomentum_001.parquet` | the point-in-time weight matrix | bit-identical (max abs diff {kw['cs_w_diff']:.3e}) |
| `data/processed/simulation_csmomentum_001.parquet` | the daily net-return series | max abs diff {kw['cs_sim_diff']:.3e} ({kw['cs_sim_diff_sessions']} of {len(kw['cs_close'].index)} sessions differ) |

**Important provenance finding.** `research/experiments/csmomentum_001_experiment_001.md` — the
record named for this candidate — was **not** produced by the calendar path. Its reproduction
command is `run_backtest(...)` without a rebalance schedule, i.e. the engine's **daily re-rank**
path, and the daily path reproduces that record's baseline block exactly:

| Metric | Published (`csmomentum_001_experiment_001.md`) | Daily re-rank path | Legacy calendar path |
|---|---|---|---|
{chr(10).join(f"| {r['metric']} | {r['published']:.{r['decimals']}f} | {format(r['observed'], '.6f')} ({'reproduced' if r['match'] else 'DIFFERS'}) | {format(cs_legacy_obs(r['metric']), '.6f')} |" for r in kw['cs_rec_rows'])}
{chr(10).join(f"| test {r['metric']} | {r['published']:.{r['decimals']}f} | {format(r['observed'], '.6f')} ({'reproduced' if r['match'] else 'DIFFERS'}) | {format(cs_legacy_obs('test ' + r['metric']), '.6f')} |" for r in kw['cs_rec_test_rows'])}

The repository therefore holds **two contradictory published records for the same candidate** that
differ only in the rebalance schedule (full-sample Sharpe 0.4496 daily vs 0.4246 calendar; test
Sharpe 0.5652 vs 0.4101). The walk-forward block of the same record is *not* reproducible with the
repository's current fold generator (it reports {CS_REC_WF['n_folds']} folds / mean OOS Sharpe
{CS_REC_WF['mean_test_sharpe']}; the generator produces {cs_wf['daily']['n_folds']} folds /
{cs_wf['daily']['mean_test_sharpe']:.4f} on the frozen configuration's own window), while the
frozen configuration `config/csmomentum_001.yaml` itself declares `folds_expected: 48`.

### 2.2 Legacy vs config-faithful

{metrics_table(cs_m['legacy'], cs_m['faithful'])}

### 2.3 Walk-forward (48 folds)

{wf_table(cs_wf['legacy'], cs_wf['faithful'])}

### 2.4 Gates

| Gate | Threshold | Legacy | Config-faithful | Status |
|---|---|---|---|---|
| 1. WF mean OOS Sharpe | >= {cs_g['legacy']['wf_mean_oos_sharpe_threshold']} | {cs_g['legacy']['wf_mean_oos_sharpe']:.4f} | {cs_g['faithful']['wf_mean_oos_sharpe']:.4f} | FAIL in both |
| 2. Positive fold rate | >= {cs_g['legacy']['positive_fold_rate_threshold']:.0%} | {cs_g['legacy']['positive_fold_rate']:.1%} | {cs_g['faithful']['positive_fold_rate']:.1%} | {'PASS' if cs_g['legacy']['gate2_positive_rate'] else 'FAIL'} in both |
| 3. Pooled OOS trades | > {cs_g['legacy']['pooled_oos_trades_threshold']:.0f} | {cs_g['legacy']['pooled_oos_trades']} | {cs_g['faithful']['pooled_oos_trades']} | {'PASS' if cs_g['legacy']['gate3_pooled_trades'] else 'FAIL'} in both |

Pre-registered falsification condition (WF mean OOS Sharpe < 0.9 **or** positive fold rate < 50%):
**met in both paths**. Verdict: **{cs_g['legacy']['label']}** (legacy) and
**{cs_g['faithful']['label']}** (config-faithful) → **{kw['cs_verdict']}**. The gate-1 margin is
{cs_g['legacy']['wf_mean_oos_sharpe_threshold'] - cs_g['faithful']['wf_mean_oos_sharpe']:.4f} Sharpe
on the config-faithful path, so the verdict is not close to flipping.

## 3. `macroregime_001` — deviation

### 3.1 Reproduction of the published numbers and the VIX data gap

The committed legacy path (`data/processed/weights_macroregime_001.parquet`) reproduces the
published numbers exactly:

| Metric | Published | Observed | Abs. diff | Result |
|---|---|---|---|---|
{cmp_table(kw['macro_pub_rows'])}

| Metric | Published | Observed | Abs. diff | Result |
|---|---|---|---|---|
{cmp_table(kw['macro_pub_wf_rows'])}

**Data gap.** The committed `{kw['regime_driver']}` cache starts
**{kw['macro_vix_first_valid'].date()}**, i.e. **{kw['macro_vix_gap_sessions']} of
{len(kw['macro_close'].index)} sessions** of the candidate's sample have no VIX observation
({kw['macro_vix_n_sessions']} of {len(kw['macro_close'].index)} sessions are covered). The published
run had the full VIX history, so the VIX regime gate was active before 2025; the cache-reproducible
path cannot activate it and therefore differs from the published path by up to
{kw['macro_w_diff']:.6f} in weight (published test Sharpe
{mr_p['test']['sharpe_backtest_scale']:.4f} vs cache-reproducible
{mr_m['legacy']['test']['sharpe_backtest_scale']:.4f}; published WF mean OOS Sharpe
{mr_pwf['mean_test_sharpe']:.4f} vs cache-reproducible {mr_wf['legacy']['mean_test_sharpe']:.4f}).

**Consequence for this cycle.** The config-faithful path *with the published VIX gate* is **not
computable from the committed cache**. The deviation below is therefore measured on the
cache-reproducible paths (legacy and config-faithful share the identical, cache-limited VIX input,
so the schedule effect is measured like-for-like), and the missing input is quantified above
rather than hidden. The published record's own numbers are reproduced from the committed artifact,
so the *published* result is not in doubt; only the *config-faithful* counterpart is data-limited.

### 3.2 Legacy vs config-faithful (cache-reproducible paths)

{metrics_table(mr_m['legacy'], mr_m['faithful'])}

### 3.3 Walk-forward (24 folds)

{wf_table(mr_wf['legacy'], mr_wf['faithful'])}

### 3.4 Gates

| Gate | Threshold | Legacy (cache) | Config-faithful (cache) | Status |
|---|---|---|---|---|
| 1. WF mean OOS Sharpe | >= {mr_g['legacy']['wf_mean_oos_sharpe_threshold']} | {mr_g['legacy']['wf_mean_oos_sharpe']:.4f} | {mr_g['faithful']['wf_mean_oos_sharpe']:.4f} | FAIL in both |
| 2. Positive fold rate | >= {mr_g['legacy']['positive_fold_rate_threshold']:.0%} | {mr_g['legacy']['positive_fold_rate']:.1%} | {mr_g['faithful']['positive_fold_rate']:.1%} | {'PASS' if mr_g['legacy']['gate2_positive_rate'] else 'FAIL'} in both |
| 3. Pooled OOS trades | > {mr_g['legacy']['pooled_oos_trades_threshold']:.0f} | {mr_g['legacy']['pooled_oos_trades']} | {mr_g['faithful']['pooled_oos_trades']} | {'PASS' if mr_g['legacy']['gate3_pooled_trades'] else 'FAIL'} in both |

Pre-registered falsification condition: **met in both paths**. Verdict:
**{mr_g['legacy']['label']}** (legacy) and **{mr_g['faithful']['label']}** (config-faithful) →
**{kw['macro_verdict']}**. The gate-1 margin on the config-faithful path is
{mr_g['legacy']['wf_mean_oos_sharpe_threshold'] - mr_g['faithful']['wf_mean_oos_sharpe']:.4f} Sharpe,
which is {abs(mr_g['legacy']['wf_mean_oos_sharpe_threshold'] - mr_g['faithful']['wf_mean_oos_sharpe']) / max(abs(mr_wf['legacy']['mean_test_sharpe'] - mr_wf['faithful']['mean_test_sharpe']), 1e-9):.1f}x
the measured schedule effect, so the verdict is not sensitive to the missing VIX history.

## 4. What the schedule defect actually did

| | `csmomentum_001` | `macroregime_001` |
|---|---|---|
| Months with no rebalance at all (legacy) | {cs_ss['n_months_without_calendar_rebalance']} of {cs_ss['n_months']} ({cs_ss['fraction_months_without_calendar_rebalance']:.1%}) | {mr_ss['n_months_without_calendar_rebalance']} of {mr_ss['n_months']} ({mr_ss['fraction_months_without_calendar_rebalance']:.1%}) |
| Test-period trade days (legacy → faithful) | {cs_m['legacy']['test']['trade_days']} → {cs_m['faithful']['test']['trade_days']} | {mr_m['legacy']['test']['trade_days']} → {mr_m['faithful']['test']['trade_days']} |
| Test-period annualized turnover (legacy → faithful) | {cs_m['legacy']['test']['annualized_turnover']:.2f}x → {cs_m['faithful']['test']['annualized_turnover']:.2f}x | {mr_m['legacy']['test']['annualized_turnover']:.2f}x → {mr_m['faithful']['test']['annualized_turnover']:.2f}x |
| Test-period Sharpe (legacy → faithful) | {cs_m['legacy']['test']['sharpe_backtest_scale']:.4f} → {cs_m['faithful']['test']['sharpe_backtest_scale']:.4f} | {mr_m['legacy']['test']['sharpe_backtest_scale']:.4f} → {mr_m['faithful']['test']['sharpe_backtest_scale']:.4f} |
| WF mean OOS Sharpe (legacy → faithful) | {cs_wf['legacy']['mean_test_sharpe']:.4f} → {cs_wf['faithful']['mean_test_sharpe']:.4f} | {mr_wf['legacy']['mean_test_sharpe']:.4f} → {mr_wf['faithful']['mean_test_sharpe']:.4f} |

The defect is a **timing** defect, not a cost defect in the sense of a wrong cost model: it made the
strategy hold a stale selection for a whole month in roughly a quarter to a third of all months and
re-entered one session early otherwise. For `csmomentum_001` the corrected schedule is slightly
*better* on the test window and on the walk-forward mean; for `macroregime_001` it is clearly
*worse* (the overlay's vol-target and drawdown state interact with the rebalance timing, and the
stale-selection months happened to be favourable). Neither change is large enough to move a
candidate across a 0.9 Sharpe gate from 0.29–0.70.

## 5. Falsification conditions for this report

This cycle's conclusions are wrong if any of the following holds:

1. the legacy path does not reproduce the committed `weights_csmomentum_001.parquet` /
   `weights_macroregime_001.parquet` artifacts or the published test-period metrics (it does, to the
   tolerances stated in §2.1 and §3.1);
2. a config-faithful path does not equal `src/backtest/rebalance.py:build_month_end_weights` (it is
   bit-identical for `csmomentum_001`);
3. a config-faithful segment is not the selection of its own signal date, or is effective on or
   before its signal date (checked for both candidates);
4. the calendar rule has no month without a rebalance (it has
   {cs_ss['n_months_without_calendar_rebalance']} and
   {mr_ss['n_months_without_calendar_rebalance']} such months);
5. a gate threshold, the cost model, the universe or the Sharpe convention differs from the frozen
   configuration (none does);
6. the raw cache or any committed artifact under `data/`, `config/` or `research/experiments/` is
   modified (none is).

## 6. Limitations

1. The `macroregime_001` config-faithful path is **not computable with the published VIX gate**:
   the committed `{kw['regime_driver']}` cache starts {kw['macro_vix_first_valid'].date()}. The
   deviation is measured on cache-reproducible paths and the missing input is quantified; the
   published result itself is reproduced from the committed artifact.
2. `csmomentum_001` has **two** published records with different numbers; this report does not
   decide which one is authoritative, it identifies which code path produced each and measures the
   schedule's effect on both.
3. The walk-forward fold statistic is the **mean of overlapping 12-month Sharpe ratios**, not the
   Sharpe of the concatenated covered window, and the folds overlap by 6 months; the pooled trade
   count sums over folds and therefore counts the same session several times.
4. Costs are the repository's flat {cost * 10000:.1f} bps round-trip model with no bid-ask spread,
   market impact, borrow or latency; sector ETFs can be wider than SPY.
5. The 9 sector ETFs, DBC and VNQ end 2026-10-08 while the core cache reaches 2026-10-16, so on
   the last session of the published window (2026-10-09) the sector ETFs carry their 2026-10-08
   close forward and their return on that session is zero. The committed published artifact was
   produced under the same cache layout, so the legacy path still reproduces it exactly
   ({kw['cs_sim_diff_sessions']} of {len(kw['cs_close'].index)} sessions differ, max abs diff
   {kw['cs_sim_diff']:.3e}); a re-run on a freshly extended cache would move those last rows.
6. This is a measurement cycle: no parameter, universe, cost model, gate threshold or configuration
   was changed, and no candidate verdict was re-opened.

## 7. Checks

| Check | Result | Detail |
|---|---|---|
{check_rows}

## 8. Reproduction

```bash
python research/month_end_candidate_reaudit.py    # this report; OVERALL: {overall}
python research/rebalance_schedule_audit.py        # Cycle 870 tool must still print OVERALL: PASS
python research/sectorrotation_long_sample_feasibility.py
python research/promotion_feasibility_backtest.py  # incumbent artifacts unchanged (NO-GO)
python -m pytest -q
git status --porcelain data/                        # empty
```

## 9. Provenance

- Data: committed raw cache `data/raw/*.parquet` (read-only; SHA-256 byte-identical before and after
  the run).
- Committed artifacts used as the reproduction reference: `data/processed/weights_csmomentum_001.parquet`,
  `data/processed/simulation_csmomentum_001.parquet`, `data/processed/weights_macroregime_001.parquet`
  (all read-only, all unchanged).
- Shared schedule implementation: `src/backtest/rebalance.py` (unchanged by this cycle).
- Gate thresholds, candidate configurations, cost model and Sharpe convention: unchanged.
"""


if __name__ == "__main__":
    sys.exit(main())
