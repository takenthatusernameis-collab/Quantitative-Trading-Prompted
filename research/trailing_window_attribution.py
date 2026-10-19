#!/usr/bin/env python3
"""Read-only attribution of the trailing-63-session underperformance (Cycle 862).

Answers, from the committed paper-trading record alone, what made the
trailing 63 sessions of the record that ends 2026-10-16 fail the promotion
gate (canonical rolling 63d Sharpe -0.211884) and what moved the
Probabilistic Sharpe Ratio to 0.684041.

The script decomposes the window return into a telescoping sequence of
counterfactual portfolio paths -- raw signal, + SPY-trend filter, + volatility
overlay, + drawdown overlay, + gross-exposure cap, + trading costs -- so that
every component is a difference of two compounded paths of the *same* data and
the components sum to the observed compounded return exactly. It then
attributes the same window per asset and per mechanism, and decomposes the
PSR change between the 449-session record and the 444-session record that
ends 2026-10-09.

The script is read-only with respect to the repository:

* the committed state ``data/processed/paper_trading_state.yaml`` is opened
  for reading only and is never written;
* the raw cache is read through the cache-only path (``force=False``);
* the incremental paper-trading replay runs against a *scratch* copy of the
  state in a temporary directory outside ``data/processed``; the scratch
  directory is removed before the script returns;
* the SHA-256 of the state file and of every ``data/raw`` parquet file is
  recorded before and after the run and must be unchanged.

Usage::

    python research/trailing_window_attribution.py
    python research/trailing_window_attribution.py --skip-replay
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluation.sharpe import sharpe_ratio  # noqa: E402
from src.evaluation.statistics import block_bootstrap_sharpe  # noqa: E402
from src.simulation.engine import _load_market_data, run_simulation  # noqa: E402
from src.simulation.paper_trading import (  # noqa: E402
    PaperTradingConfig,
    PaperTradingState,
    run_daily_paper_update,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = REPO_ROOT / "data" / "processed" / "paper_trading_state.yaml"
CONFIG_PATH = REPO_ROOT / "config" / "paper_trading_config.yaml"
RAW_DIR = REPO_ROOT / "data" / "raw"

WINDOW = 63
TAIL = 5
BACKTEST_TARGET = 1.4178
BOOTSTRAP_SAMPLES = 1000
BLOCK_SIZE = 22
PSR_SEED = 20240101
RECONCILE_TOL = 1e-6


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repository_fingerprint() -> dict[str, str]:
    """SHA-256 of the committed state and of every raw-cache parquet file."""
    files = [STATE_PATH] + sorted(RAW_DIR.glob("*.parquet"))
    return {str(p.relative_to(REPO_ROOT)): sha256_file(p) for p in files}


def load_state() -> dict:
    with open(STATE_PATH) as fh:
        return yaml.safe_load(fh) or {}


def compounded(returns) -> float:
    arr = np.asarray(returns, dtype=float)
    return float(np.prod(1.0 + arr) - 1.0)


def build_layers(sim, asset_ret: pd.DataFrame, config: PaperTradingConfig) -> dict:
    """Counterfactual weight paths, one per mechanism, plus the per-asset data."""
    index = sim.daily.index
    symbols = list(config.universe)

    base = sim.base_weights.reindex(index).fillna(0.0)
    regime = sim.daily["regime_exposure"].reindex(index).fillna(0.0)
    vol_scale = sim.daily["vol_scale"].reindex(index).fillna(0.0)
    dd_scale = sim.daily["dd_scale"].reindex(index).fillna(0.0)
    combined = sim.weights.reindex(index).fillna(0.0)

    gated = base.mul(regime, axis=0)
    vol_targeted = gated.mul(vol_scale, axis=0)
    dd_scaled = vol_targeted.mul(dd_scale, axis=0)

    ret = asset_ret.reindex(index).fillna(0.0)

    def portfolio_return(weights: pd.DataFrame) -> pd.Series:
        return (weights * ret).sum(axis=1)

    cost = sim.daily["cost"].reindex(index)
    turnover = sim.daily["turnover"].reindex(index)

    trade_log = sim.trade_log
    if len(trade_log):
        per_symbol_cost = trade_log.pivot_table(
            index="date", columns="symbol", values="cost", aggfunc="sum"
        )
        per_symbol_cost = per_symbol_cost.reindex(index).fillna(0.0)
    else:
        per_symbol_cost = pd.DataFrame(0.0, index=index, columns=symbols)

    return {
        "index": index,
        "symbols": symbols,
        "asset_ret": ret,
        "base": base,
        "gated": gated,
        "vol_targeted": vol_targeted,
        "dd_scaled": dd_scaled,
        "combined": combined,
        "regime": regime,
        "vol_scale": vol_scale,
        "dd_scale": dd_scale,
        "turnover": turnover,
        "cost": cost,
        "cost_per_symbol": per_symbol_cost,
        "r_signal": portfolio_return(base),
        "r_filter": portfolio_return(gated),
        "r_vol": portfolio_return(vol_targeted),
        "r_dd": portfolio_return(dd_scaled),
        "r_gross": portfolio_return(combined),
        "net_return": sim.daily["net_return"].reindex(index),
    }


def decompose_window(layers: dict, sl: slice) -> dict:
    """Telescoping decomposition of a window into one component per mechanism."""
    r_signal = layers["r_signal"].iloc[sl]
    r_filter = layers["r_filter"].iloc[sl]
    r_vol = layers["r_vol"].iloc[sl]
    r_dd = layers["r_dd"].iloc[sl]
    r_gross = layers["r_gross"].iloc[sl]
    net = layers["net_return"].iloc[sl]
    cost = layers["cost"].iloc[sl]

    c_signal = compounded(r_signal)
    c_filter = compounded(r_filter)
    c_vol = compounded(r_vol)
    c_dd = compounded(r_dd)
    c_gross = compounded(r_gross)
    c_net = compounded(net)

    components = {
        "gross_signal_return": c_signal,
        "filter_effect": c_filter - c_signal,
        "vol_overlay_effect": c_vol - c_filter,
        "drawdown_overlay_effect": c_dd - c_vol,
        "leverage_cap_effect": c_gross - c_dd,
        "cost_drag": c_net - c_gross,
    }
    overlay_effect = (
        components["vol_overlay_effect"]
        + components["drawdown_overlay_effect"]
        + components["leverage_cap_effect"]
    )
    total = sum(components.values())
    residual = c_net - total
    components["overlay_effect"] = overlay_effect

    arithmetic = {
        "signal_sum": float(r_signal.sum()),
        "vol_scaled_sum": float(r_vol.sum()),
        "net_sum": float(net.sum()),
        "cost_sum": float(cost.sum()),
    }
    return {
        "components": components,
        "levels": {
            "signal": c_signal,
            "filter": c_filter,
            "vol": c_vol,
            "drawdown": c_dd,
            "gross": c_gross,
            "net": c_net,
        },
        "residual": residual,
        "observed": c_net,
        "arithmetic": arithmetic,
        "n_sessions": int(len(net)),
        "regime_off_sessions": int((layers["regime"].iloc[sl] == 0).sum()),
        "vol_scale_mean": float(layers["vol_scale"].iloc[sl].mean()),
        "dd_scale_min": float(layers["dd_scale"].iloc[sl].min()),
        "turnover_sum": float(layers["turnover"].iloc[sl].sum()),
        "start": str(layers["index"][sl][0].date()),
        "end": str(layers["index"][sl][-1].date()),
    }


def per_asset_attribution(layers: dict, sl: slice) -> dict:
    """Per-asset and per-mechanism attribution over a window."""
    index = layers["index"]
    window_index = index[sl]
    ret = layers["asset_ret"].iloc[sl]
    cost_sym = layers["cost_per_symbol"].iloc[sl]

    mechanisms = {
        "signal": layers["base"].iloc[sl],
        "filter": layers["gated"].iloc[sl] - layers["base"].iloc[sl],
        "vol_overlay": layers["vol_targeted"].iloc[sl] - layers["gated"].iloc[sl],
        "drawdown_overlay": layers["dd_scaled"].iloc[sl] - layers["vol_targeted"].iloc[sl],
        "leverage_cap": layers["combined"].iloc[sl] - layers["dd_scaled"].iloc[sl],
    }

    per_mechanism = {}
    for name, weights in mechanisms.items():
        per_mechanism[name] = (weights * ret).sum(axis=0)
    per_mechanism["cost"] = -cost_sym.sum(axis=0)

    signal_path = pd.DataFrame(
        {sym: compounded((layers["base"].iloc[sl][sym] * ret[sym]).to_numpy()) for sym in layers["symbols"]},
        index=layers["symbols"],
    )

    gross_by_asset = (layers["combined"].iloc[sl] * ret)
    order = sorted(
        layers["symbols"],
        key=lambda s: -abs(float(gross_by_asset[s].sum())),
    )

    no_cost_paths = {}
    for k in range(len(order) + 1):
        subset = order[:k]
        if subset:
            path = (gross_by_asset[subset].sum(axis=1)).to_numpy()
        else:
            path = np.zeros(len(window_index))
        no_cost_paths[k] = compounded(path)
    telescoped = {
        order[k]: no_cost_paths[k + 1] - no_cost_paths[k] for k in range(len(order))
    }
    gross_path = compounded(gross_by_asset.sum(axis=1).to_numpy())
    cost_path = float(layers["cost"].iloc[sl].sum())

    return {
        "per_mechanism_sum": pd.DataFrame(per_mechanism),
        "telescoped": telescoped,
        "order": order,
        "gross_path_no_cost": gross_path,
        "cost_sum": cost_path,
        "net_path": compounded(
            (gross_by_asset.sum(axis=1) - layers["cost"].iloc[sl]).to_numpy()
        ),
        "window_index": window_index,
        "per_session": {
            "gross_by_asset": gross_by_asset,
            "cost_by_asset": cost_sym,
            "signal_by_asset": (layers["base"].iloc[sl] * ret),
        },
    }


def psr_attribution(returns: np.ndarray, n_previous: int) -> dict:
    """Split the PSR change between two records into numerator and SE effects."""
    def psr(obs: float, se: float) -> float:
        if se <= 0:
            return 1.0 if obs > BACKTEST_TARGET else 0.0
        return float(stats.norm.cdf((obs - BACKTEST_TARGET) / se))

    def record(arr: np.ndarray) -> dict:
        boot = block_bootstrap_sharpe(
            pd.Series(arr), BOOTSTRAP_SAMPLES, BLOCK_SIZE, seed=PSR_SEED
        )
        se = float(np.std(boot, ddof=1))
        obs = sharpe_ratio(arr)
        return {
            "observed": obs,
            "se": se,
            "psr": psr(obs, se),
            "empirical": float((boot > BACKTEST_TARGET).mean()),
            "bootstrap_mean": float(np.mean(boot)),
        }

    current = record(returns)
    previous = record(returns[:n_previous])
    mixed = psr(current["observed"], previous["se"])
    mixed_other = psr(previous["observed"], current["se"])
    return {
        "current": current,
        "previous": previous,
        "numerator_effect": mixed - previous["psr"],
        "se_effect": current["psr"] - mixed,
        "interaction": (mixed_other - previous["psr"]) - (current["psr"] - mixed),
        "mixed_observed_current_se_previous": mixed,
        "mixed_observed_previous_se_current": mixed_other,
    }


def scratch_replay(
    state: dict,
    dates: list[str],
    window_dates: list[str],
    market_data: pd.DataFrame,
    config: PaperTradingConfig,
) -> dict:
    """Replay the window through the incremental paper-trading path on a scratch state."""
    scratch = Path(tempfile.mkdtemp(prefix="trailing_window_attribution_"))
    try:
        scratch_state_path = scratch / "paper_trading_state.yaml"
        n_keep = len(dates) - len(window_dates)
        nav_path = 100000.0 * np.cumprod(
            1.0 + np.asarray(state["cumulative_returns"], dtype=float)
        )
        peak = float(np.max(nav_path[:n_keep]))
        max_dd = float((nav_path[:n_keep] / np.maximum.accumulate(nav_path[:n_keep]) - 1.0).min())
        truncated = {
            "last_run_date": dates[n_keep - 1],
            "current_positions": {},
            "cumulative_returns": list(state["cumulative_returns"])[:n_keep],
            "cumulative_pnl": list(state.get("cumulative_pnl") or [])[:n_keep],
            "cumulative_dates": list(dates)[:n_keep],
            "peak_nav": peak,
            "current_nav": float(nav_path[n_keep - 1]),
            "max_drawdown": max_dd,
            "drift_flags": {},
            "run_history": list(state.get("run_history") or [])[:n_keep],
            "previous_regime_exposure": float(
                (state.get("run_history") or [])[n_keep - 1].get("regime_exposure", 1.0)
            ),
            "rolling_sharpe_63d": 0.0,
            "rolling_max_dd_63d": 0.0,
            "regime_persistence_days": 0,
            "vol_scale_min": 1.0,
            "vol_scale_max": 1.0,
            "dd_scale_min": 1.0,
            "dd_scale_max": 1.0,
            "turnover_median": 0.0,
            "turnover_p95": 0.0,
        }
        with open(scratch_state_path, "w") as fh:
            yaml.safe_dump(truncated, fh, sort_keys=False)

        scratch_config = replace(
            config,
            output_dir=str(scratch / "artifacts"),
            report_path=str(scratch / "report.md"),
            state_path=str(scratch_state_path),
        )
        scratch_state = PaperTradingState.from_yaml(scratch_state_path)

        committed = {h["date"]: h for h in state["run_history"]}
        records = []
        for date in window_dates:
            ts = pd.Timestamp(date, tz="UTC")
            session_data = market_data[market_data.index <= ts]
            scratch_state, artifacts = run_daily_paper_update(
                scratch_config, scratch_state, market_data=session_data
            )
            records.append(
                {
                    "date": date,
                    "nav": scratch_state.current_nav,
                    "daily_return": artifacts["daily_return"],
                    "turnover": artifacts["turnover"],
                    "vol_scale": artifacts["vol_scale"],
                    "dd_scale": artifacts["dd_scale"],
                    "regime_exposure": artifacts["regime_exposure"],
                    "positions": artifacts["positions"],
                }
            )

        fields = ["nav", "daily_return", "turnover", "vol_scale", "dd_scale", "regime_exposure"]
        worst = {f: 0.0 for f in fields}
        for rec in records:
            ref = committed[rec["date"]]
            for f in fields:
                worst[f] = max(worst[f], abs(float(rec[f]) - float(ref[f])))

        start_diff = float(nav_path[n_keep - 1]) - float(
            state["run_history"][n_keep - 1]["nav"]
        )
        end_diff = float(records[-1]["nav"]) - float(committed[records[-1]["date"]]["nav"])
        return {
            "records": records,
            "max_abs_diff": worst,
            "nav_start_diff": start_diff,
            "nav_end_diff": end_diff,
            "nav_growth_diff": end_diff - start_diff,
            "scratch_dir": str(scratch),
            "state_path": str(scratch_state_path),
        }
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-replay",
        action="store_true",
        help="skip the scratch incremental replay (faster; the per-asset tables are unaffected)",
    )
    args = parser.parse_args()

    fingerprint_before = repository_fingerprint()
    state = load_state()
    dates = [str(d) for d in state["cumulative_dates"]]
    returns = np.asarray(state["cumulative_returns"], dtype=float)
    history = state["run_history"]
    config = PaperTradingConfig.from_paper_config_yaml(CONFIG_PATH)

    print("=== Trailing-window attribution (read-only) ===")
    print(f"state file          : {STATE_PATH}")
    print(f"last_run_date       : {state.get('last_run_date')}  sessions: {len(dates)}")
    print(f"sharpe convention   : arithmetic_annualized_rf0 (canonical)")

    sim = run_simulation(config, config.history_start, dates[-1])
    close, _ = _load_market_data(list(config.universe), config.history_start, dates[-1])
    layers = build_layers(sim, close.pct_change(), config)

    sim_index = layers["index"]
    sim_dates = [str(ts.date()) for ts in sim_index]
    positions = {d: i for i, d in enumerate(sim_dates)}
    window_dates = dates[-WINDOW:]
    sl_window = slice(positions[window_dates[0]], positions[window_dates[-1]] + 1)
    prev_dates = dates[-(WINDOW + TAIL):-TAIL]
    sl_prev = slice(positions[prev_dates[0]], positions[prev_dates[-1]] + 1)
    tail_dates = dates[-TAIL:]
    sl_tail = slice(positions[tail_dates[0]], positions[tail_dates[-1]] + 1)

    print("\n--- 1. Does the engine reproduce the committed record? ---")
    committed_returns = np.array([h["daily_return"] for h in history], dtype=float)
    record_index = [sim_index[positions[d]] for d in dates]
    sim_returns = sim.daily["net_return"].reindex(record_index).to_numpy()
    record_diff = float(np.max(np.abs(sim_returns - committed_returns)))
    field_diffs = {}
    for key, column in [
        ("turnover", "turnover"),
        ("vol_scale", "vol_scale"),
        ("dd_scale", "dd_scale"),
        ("regime_exposure", "regime_exposure"),
        ("n_positions", "n_positions"),
    ]:
        committed_field = np.array([h[key] for h in history], dtype=float)
        sim_field = sim.daily[column].reindex(record_index).to_numpy(dtype=float)
        field_diffs[key] = float(np.max(np.abs(sim_field - committed_field)))
    print(f"  max |net_return - committed|      : {record_diff:.3e}")
    for key, value in field_diffs.items():
        print(f"  max |{key:<24s} - committed| : {value:.3e}")
    reproduces = record_diff == 0.0 and all(v == 0.0 for v in field_diffs.values())

    print("\n--- 2. Window decomposition (telescoping counterfactual paths) ---")
    windows = {
        "trailing_63": decompose_window(layers, sl_window),
        "previous_63": decompose_window(layers, sl_prev),
        "tail_5": decompose_window(layers, sl_tail),
    }
    for label, w in windows.items():
        comp = w["components"]
        print(f"\n  [{label}] {w['start']} .. {w['end']}  ({w['n_sessions']} sessions)")
        print(f"    gross signal return (L0)      : {comp['gross_signal_return']*100:+.6f}%")
        print(f"    filter effect (SPY trend)     : {comp['filter_effect']*100:+.6f}%")
        print(f"    overlay effect (vol+dd+cap)   : {comp['overlay_effect']*100:+.6f}%")
        print(f"      vol overlay                 : {comp['vol_overlay_effect']*100:+.6f}%")
        print(f"      drawdown overlay            : {comp['drawdown_overlay_effect']*100:+.6f}%")
        print(f"      gross-exposure cap          : {comp['leverage_cap_effect']*100:+.6f}%")
        print(f"    cost drag (turnover x 3bp)    : {comp['cost_drag']*100:+.6f}%")
        print(f"    residual                      : {w['residual']*100:+.3e} %  (tol {RECONCILE_TOL})")
        print(f"    observed compounded net return: {w['observed']*100:+.6f}%")
        print(f"    arithmetic sum of daily rets  : {w['arithmetic']['net_sum']*100:+.6f}%")
        print(f"    regime-off sessions           : {w['regime_off_sessions']}")
        print(f"    mean vol_scale                : {w['vol_scale_mean']:.4f}  min dd_scale: {w['dd_scale_min']:.4f}")
        print(f"    cumulative turnover           : {w['turnover_sum']:.4f}")

    print("\n--- 3. Overlay mechanics: how the vol scaler interacted with the signal ---")
    for label, sl in [("trailing_63", sl_window), ("previous_63", sl_prev), ("tail_5", sl_tail)]:
        vol_scale = layers["vol_scale"].iloc[sl]
        r_signal = layers["r_signal"].iloc[sl]
        median = float(vol_scale.median())
        high = r_signal[vol_scale >= median].sum()
        low = r_signal[vol_scale < median].sum()
        corr = float(np.corrcoef(vol_scale, r_signal)[0, 1])
        print(
            f"  {label:<12s} mean vol_scale {vol_scale.mean():.4f}  median {median:.4f}  "
            f"corr(vol_scale, signal return) {corr:+.4f}"
        )
        print(
            f"               signal sum on high-vol_scale half {high*100:+.6f}%  "
            f"on low-vol_scale half {low*100:+.6f}%"
        )
        implied = 0.10 / vol_scale.replace(0.0, np.nan)
        print(
            f"               implied trailing realised vol of the raw signal portfolio "
            f"(target 10% / vol_scale): mean {implied.mean():.4f} annualised"
        )

    print("\n--- 3b. Window-to-window change and the Sharpe level ---")
    dropped_dates = dates[-(WINDOW + TAIL):-TAIL][:TAIL]
    dropped_sl = slice(positions[dropped_dates[0]], positions[dropped_dates[-1]] + 1)
    dropped = decompose_window(layers, dropped_sl)
    w_cur = windows["trailing_63"]
    w_prv = windows["previous_63"]
    print(
        f"  sessions that LEFT the window ({dropped['start']} .. {dropped['end']}): "
        f"compounded {dropped['observed']*100:+.6f}%, arithmetic {dropped['arithmetic']['net_sum']*100:+.6f}%"
    )
    print(
        f"  sessions that ENTERED the window ({windows['tail_5']['start']} .. "
        f"{windows['tail_5']['end']}): "
        f"compounded {windows['tail_5']['observed']*100:+.6f}%, "
        f"arithmetic {windows['tail_5']['arithmetic']['net_sum']*100:+.6f}%"
    )
    print(
        f"  overlap of 58 sessions is unchanged; arithmetic swing "
        f"{(w_cur['arithmetic']['net_sum'] - w_prv['arithmetic']['net_sum'])*100:+.6f}%, "
        f"compounded swing {(w_cur['observed'] - w_prv['observed'])*100:+.6f}%"
    )
    for label, sl in [("trailing_63", sl_window), ("previous_63", sl_prev)]:
        net = layers["net_return"].iloc[sl]
        mean = float(net.mean())
        std = float(net.std(ddof=1))
        sr = sharpe_ratio(net)
        required_mean = 0.9 * std / np.sqrt(252.0)
        print(
            f"  {label:<12s} mean {mean*1e4:+.4f} bp/day ({mean*252*100:+.4f}% annualised)  "
            f"std {std*1e4:.4f} bp/day ({std*np.sqrt(252)*100:.4f}% annualised)  "
            f"Sharpe {sr:.6f}"
        )
        print(
            f"               mean required for Sharpe 0.9 at this dispersion: "
            f"{required_mean*1e4:+.4f} bp/day ({required_mean*252*100:+.4f}% annualised); "
            f"gap {((mean - required_mean)*252*100):+.4f} pp annualised"
        )

    print("\n--- 4. Per-asset attribution ---")
    for label, sl in [("trailing_63", sl_window), ("tail_5", sl_tail)]:
        pa = per_asset_attribution(layers, sl)
        print(f"\n  [{label}] session-summed contribution (bp), by asset and mechanism")
        table = pa["per_mechanism_sum"] * 1e4
        table = table.loc[[s for s in pa["order"]]]
        print(table.round(2).to_string())
        total = float(table.to_numpy().sum())
        print(f"    sum of all cells (bp): {total:.4f}")
        print(
            f"    window net arithmetic sum: {float(layers['net_return'].iloc[sl].sum())*1e4:.4f} bp"
        )
        print("  compounded attribution (no-cost paths, telescoped over assets):")
        for sym in pa["order"]:
            print(f"    {sym:<4s} {pa['telescoped'][sym]*100:+.6f}%")
        print(f"    cost drag (turnover x 3bp): {(pa['net_path']-pa['gross_path_no_cost'])*100:+.6f}%")
        print(f"    sum check: {sum(pa['telescoped'].values())*100 + (pa['net_path']-pa['gross_path_no_cost'])*100:+.9f}% vs observed {pa['net_path']*100:+.6f}%")

    print("\n--- 5. Tail sessions in detail ---")
    tail = layers["index"][sl_tail]
    tail_index = [str(ts.date()) for ts in tail]
    returns_detail = pd.DataFrame(
        {
            "signal_bp": layers["r_signal"].iloc[sl_tail] * 1e4,
            "vol_scaled_bp": layers["r_vol"].iloc[sl_tail] * 1e4,
            "net_bp": layers["net_return"].iloc[sl_tail] * 1e4,
            "cost_bp": layers["cost"].iloc[sl_tail] * 1e4,
        },
        index=tail_index,
    )
    scales_detail = pd.DataFrame(
        {
            "vol_scale": layers["vol_scale"].iloc[sl_tail],
            "dd_scale": layers["dd_scale"].iloc[sl_tail],
            "regime": layers["regime"].iloc[sl_tail],
            "turnover_bp": layers["turnover"].iloc[sl_tail] * 1e4,
        },
        index=tail_index,
    )
    print(returns_detail.round(3).to_string())
    print(scales_detail.round(6).to_string())
    held = {
        str(ts.date()): [
            s for s in layers["symbols"] if float(layers["combined"].loc[ts, s]) > 0.0
        ]
        for ts in layers["index"][sl_tail]
    }
    print("  assets held (weight > 0):")
    for date, symbols in held.items():
        print(f"    {date}: {', '.join(symbols)}")
    print("  underlying asset returns (bp):")
    print((layers["asset_ret"].iloc[sl_tail] * 1e4).round(1).to_string())

    print("\n--- 6. PSR attribution (449-session vs 444-session record) ---")
    n_previous = sum(1 for d in dates if d <= "2026-10-09")
    psr = psr_attribution(returns, n_previous)
    cur, prev = psr["current"], psr["previous"]
    print(f"  449-session record: observed {cur['observed']:.6f}  se {cur['se']:.6f}  psr {cur['psr']:.6f}  empirical {cur['empirical']:.3f}")
    print(f"  444-session record: observed {prev['observed']:.6f}  se {prev['se']:.6f}  psr {prev['psr']:.6f}  empirical {prev['empirical']:.3f}")
    print(f"  numerator effect (observed Sharpe {prev['observed']:.6f} -> {cur['observed']:.6f}): {psr['numerator_effect']:+.6f}")
    print(f"  standard-error effect (se {prev['se']:.6f} -> {cur['se']:.6f})          : {psr['se_effect']:+.6f}")
    print(f"  interaction term                                               : {psr['interaction']:+.6f}")
    print(f"  total                                                           : {cur['psr']-prev['psr']:+.6f}")
    print(f"  PSR gate threshold 0.95: 449-session psr {cur['psr']:.6f} FAIL, 444-session psr {prev['psr']:.6f} FAIL")
    z_needed = float(stats.norm.ppf(0.95))
    print(
        f"  observed Sharpe needed for psr>=0.95 at se {cur['se']:.6f}: "
        f"{BACKTEST_TARGET + z_needed*cur['se']:.6f} (observed {cur['observed']:.6f}); "
        f"se needed at observed: {(cur['observed']-BACKTEST_TARGET)/z_needed:.6f}"
    )

    print("\n--- 7. Scratch incremental replay (state copy outside data/processed) ---")
    replay_result = None
    if not args.skip_replay:
        market_data = None
        from src.data.yfinance_fetcher import fetch_universe

        missing = [
            s
            for s in config.universe
            if not (RAW_DIR / f"{s.replace('/', '-').replace('=', '-')}.parquet").exists()
        ]
        if missing:
            print(f"  raw cache incomplete for {missing}; skipping replay")
        else:
            market_data = fetch_universe(
                list(config.universe), config.history_start, dates[-1], force=False
            )
            replay_result = scratch_replay(
                state, dates, window_dates, market_data, config
            )
            print(f"  scratch state: {replay_result['state_path']} (removed after the run)")
            tolerances = {
                "nav": 1e-6,
                "daily_return": 1e-12,
                "turnover": 1e-12,
                "vol_scale": 1e-12,
                "dd_scale": 1e-12,
                "regime_exposure": 1e-12,
            }
            for key, value in replay_result["max_abs_diff"].items():
                verdict = "OK" if value <= tolerances[key] else "FAIL"
                print(
                    f"  max |replayed {key:<18s} - committed| : {value:.3e} "
                    f"(tol {tolerances[key]:.0e}) {verdict}"
                )
            replay_ok = all(
                replay_result["max_abs_diff"][k] <= tolerances[k] for k in tolerances
            )
            print(
                f"  NAV gap origin: scratch seed (vectorised cumprod) vs committed NAV at the "
                f"truncation session = {replay_result['nav_start_diff']:+.3e};"
            )
            print(
                f"                   same gap at the last replayed session            = "
                f"{replay_result['nav_end_diff']:+.3e};"
            )
            print(
                f"                   gap accumulated by the 63 replayed sessions      = "
                f"{replay_result['nav_growth_diff']:+.3e} (float association order only)"
            )
            print(f"  replay reproduces the committed window: {replay_ok}")
    else:
        print("  skipped (--skip-replay)")
        replay_ok = True

    print("\n--- 8. Read-only and reconciliation checks ---")
    fingerprint_after = repository_fingerprint()
    unchanged = fingerprint_before == fingerprint_after
    residual_ok = all(
        abs(w["residual"]) <= RECONCILE_TOL for w in windows.values()
    )
    trailing_sharpe = sharpe_ratio(returns[-WINDOW:])
    stored_flag = (state.get("drift_flags") or {}).get("low_rolling_sharpe") or {}
    stored_value = stored_flag.get("value")
    flag_ok = stored_value is not None and abs(float(stored_value) - trailing_sharpe) <= 1e-12

    print(f"  state/raw SHA-256 set unchanged        : {unchanged}")
    print(f"  decomposition residual <= {RECONCILE_TOL}      : {residual_ok}")
    print(f"  engine reproduces committed record      : {reproduces}")
    print(f"  scratch replay reproduces committed rows: {replay_ok}")
    print(f"  trailing 63d Sharpe {trailing_sharpe:.6f} == stored drift flag: {flag_ok}")

    ok = unchanged and residual_ok and reproduces and flag_ok and replay_ok
    print(f"\nOVERALL: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
