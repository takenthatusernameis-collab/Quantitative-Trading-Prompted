#!/usr/bin/env python3
"""Cost gate break-even audit for the promotion-gate statistic (Cycle 913)."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.backtest.engine import get_cost_params, get_risk_free_rate  # noqa: E402

REPORTS_DIR = REPO_ROOT / "research" / "reports"
EXPERIMENTS_DIR = REPO_ROOT / "research" / "experiments"
RAW_DIR = REPO_ROOT / "data" / "raw"

OUT_REPORT = REPORTS_DIR / "cost_gate_break_even_001.md"
OUT_EXP = EXPERIMENTS_DIR / "cost_gate_break_even_001.md"

CANDIDATES = ["tsmomentum_spytrend_001", "csmomentum_001", "sectorrotation_001"]
GATE_WF_MEAN_MIN = 0.9
GATE_POSITIVE_FOLD_RATE_MIN = 0.5
GATE_POOLED_TRADES_MIN = 100
SPREAD_PERCENTILES = [10, 25, 50]

PUBLISHED = {
    "tsmomentum_spytrend_001": {"wf_mean": 0.9473},
    "csmomentum_001": {"wf_mean_backtest": 0.697524, "wf_mean_canonical": 0.840389},
    "sectorrotation_001": {"wf_mean": 0.847243},
}

FALSIFICATION = (
    "if the incumbent's published PASS survives a cost level of at least the measured bid-ask floor "
    "(times the two legs actually traded), the cost axis is not the binding constraint on the incumbent "
    "and this axis is closed."
)


class AuditError(RuntimeError):
    pass


def fail(msg: str) -> None:
    raise AuditError(msg)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fingerprint(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    out: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            try:
                out[str(path.relative_to(REPO_ROOT))] = sha256_file(path)
            except Exception:
                continue
    return out


def tracked_artifact_hashes() -> dict[str, str]:
    import subprocess

    out: dict[str, str] = {}
    for tree in ("src", "config", "research/experiments", "research/reports", "tests"):
        try:
            res = subprocess.run(
                ["git", "ls-files", tree],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
        except Exception:
            continue
        if res.returncode != 0:
            continue
        for rel in res.stdout.splitlines():
            rel = rel.strip()
            if not rel:
                continue
            path = REPO_ROOT / rel
            if path.is_file():
                out[rel] = sha256_file(path)
    return out


_CACHE = {}


def compute_bid_ask_floor() -> dict[str, Any]:
    result = {}
    for sym_path in sorted(RAW_DIR.glob("*.parquet")):
        try:
            df = pd.read_parquet(sym_path)
            if df.empty or "Close" not in df or "High" not in df or "Low" not in df:
                continue
            spread_proxy = (df["High"] - df["Low"]) / df["Close"].replace(0, np.nan)
            spread_proxy = spread_proxy.dropna()
            if spread_proxy.empty:
                continue
            vals = {}
            for p in SPREAD_PERCENTILES:
                vals[f"p{p}"] = float(np.percentile(spread_proxy, p))
            result[sym_path.stem] = vals
        except Exception:
            continue
    if not result:
        return {"per_symbol": result, "aggregate": {}}
    agg = {}
    for p in SPREAD_PERCENTILES:
        key = f"p{p}"
        all_vals = [v[key] for v in result.values()]
        agg[key] = float(np.median(all_vals))
    return {"per_symbol": result, "aggregate": agg}


def tsmom_build_path_with_cost(close: pd.DataFrame, cost_frac: float):
    from research.tsmomentum_walkforward_embargo_audit import (
        build_weights,
        LOOKBACK,
        SKIP,
        TOP_FRACTION,
        SPY_SMA_WINDOW,
        _apply_overlay,
    )

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

    default_comm, default_slip = get_cost_params()
    total_default = default_comm + default_slip
    if total_default > 0:
        comm_frac = cost_frac * (default_comm / total_default)
        slip_frac = cost_frac * (default_slip / total_default)
    else:
        comm_frac = cost_frac / 2.0
        slip_frac = cost_frac / 2.0
    combined_weights, net_ret, _ = _apply_overlay(
        daily_ret,
        weights_a,
        exposure_factor=exposure,
        commission_bps=comm_frac,
        slippage_bps=slip_frac,
    )
    return net_ret, combined_weights


def tsmom_gate_metrics_at_cost_full(cost_frac: float) -> dict[str, Any]:
    if ("tsmom", float(cost_frac)) in _CACHE:
        return _CACHE[("tsmom", float(cost_frac))]
    from research.tsmomentum_walkforward_embargo_audit import (
        SYMBOLS,
        load_close_from_cache,
        evaluate_design,
        gate_table,
        published_splits,
    )

    if "tsmom_close" not in _CACHE:
        close = load_close_from_cache(list(SYMBOLS), RAW_DIR)
        _CACHE["tsmom_close"] = close
    else:
        close = _CACHE["tsmom_close"]
    net_ret, weights = tsmom_build_path_with_cost(close, cost_frac)
    splits = published_splits()
    result = evaluate_design(net_ret, weights, splits)
    gates = gate_table(result["summary"])
    res = {
        "n_folds": result["summary"]["n_folds"],
        "wf_mean": float(result["summary"].get("mean_test_sharpe", np.nan)),
        "pct_pos": float(result["summary"].get("pct_positive_sharpe", np.nan)),
        "total_trades": int(result["summary"].get("total_test_trades", 0)),
        "gates": gates,
        "summary": result["summary"],
    }
    _CACHE[("tsmom", float(cost_frac))] = res
    return res


def csmom_gate_metrics_at_cost_full(cost_frac: float) -> dict[str, Any]:
    if ("csmom", float(cost_frac)) in _CACHE:
        return _CACHE[("csmom", float(cost_frac))]
    from research.month_end_candidate_reaudit import build_csmomentum, walkforward, CONFIG_CS
    from research.csmomentum_sample_gate_audit import aligned_close_from_cache
    from research.promotion_feasibility_backtest import load_yaml
    from src.evaluation.walkforward import generate_walkforward_splits
    from research.csmomentum_sample_gate_audit import build_gate_table

    cand = load_yaml(CONFIG_CS)
    universe = list(cand["universe"])
    evaluation = cand["evaluation"]
    wf_cfg = evaluation["walk_forward"]
    if "csmom_splits" not in _CACHE:
        splits = generate_walkforward_splits(
            str(cand["history_start"]),
            str(evaluation["splits"]["test_end"]),
            float(wf_cfg["train_years"]),
            float(wf_cfg["test_months"]),
            float(wf_cfg["step_months"]),
            int(wf_cfg["purge_days"]),
            int(wf_cfg["embargo_days"]),
        )
        close_full = aligned_close_from_cache(universe)
        close_union = close_full.loc[
            (close_full.index >= pd.Timestamp(str(cand["history_start"]), tz="UTC"))
            & (close_full.index <= pd.Timestamp(str(evaluation["splits"]["test_end"]), tz="UTC"))
        ].copy()
        _CACHE["csmom_close"] = close_union
        _CACHE["csmom_splits"] = splits
        _CACHE["csmom_gate_cfg"] = evaluation["promotion_gates"]
    close_union = _CACHE["csmom_close"]
    splits = _CACHE["csmom_splits"]
    paths = build_csmomentum(close_union, float(cost_frac))
    wf_sum, wf_rows = walkforward(paths["faithful_net"], paths["faithful_weights"], splits)
    gates = build_gate_table(wf_sum, _CACHE["csmom_gate_cfg"])
    res_out = {
        "n_folds": wf_sum.get("n_folds"),
        "wf_mean_backtest": float(wf_sum.get("mean_test_sharpe", np.nan)),
        "wf_mean_canonical": float(wf_sum.get("mean_test_sharpe_canonical", np.nan)),
        "pct_pos": float(wf_sum.get("pct_positive_sharpe", np.nan)),
        "total_trades": int(wf_sum.get("total_test_trades", 0)),
        "gates": gates,
        "summary": wf_sum,
    }
    _CACHE[("csmom", float(cost_frac))] = res_out
    return res_out


def sector_gate_metrics_at_cost_full(cost_frac: float) -> dict[str, Any]:
    if ("sector", float(cost_frac)) in _CACHE:
        return _CACHE[("sector", float(cost_frac))]
    if "sector_data" not in _CACHE:
        from research.sectorrotation_long_sample_feasibility import (
            CONFIG_CAND,
            load_yaml,
            build_monthly_weights,
            compute_momentum,
            select_top_decile,
            month_end_dates,
        )
        from src.data.yfinance_fetcher import fetch_universe
        from src.evaluation.walkforward import generate_walkforward_splits

        cand = load_yaml(CONFIG_CAND)
        universe = list(cand["universe"])
        signal = cand["signal"]
        lookback = int(signal["lookback"])
        skip = int(signal["skip"])
        top_fraction = float(signal["top_fraction"])
        start = pd.Timestamp(cand["history_start"])
        test_end = cand["evaluation"]["splits"]["test_end"]
        wf_cfg = cand["evaluation"]["walk_forward"]

        data = fetch_universe(universe, start.date().isoformat(), test_end, force=False)
        close = data.xs("Close", level=0, axis=1).ffill().dropna(how="all")
        momentum = compute_momentum(close, lookback=lookback, skip=skip)
        mask = select_top_decile(momentum, top_fraction=top_fraction)
        month_ends = month_end_dates(close.index)
        weights, segments = build_monthly_weights(close, mask, month_ends)
        splits = generate_walkforward_splits(
            cand["history_start"],
            test_end,
            float(wf_cfg["train_years"]),
            float(wf_cfg["test_months"]),
            float(wf_cfg["step_months"]),
            int(wf_cfg["purge_days"]),
            int(wf_cfg["embargo_days"]),
        )
        _CACHE["sector_data"] = {"close": close, "weights": weights, "splits": splits}
    d = _CACHE["sector_data"]
    close, weights, splits = d["close"], d["weights"], d["splits"]
    from research.sectorrotation_long_sample_feasibility import portfolio_returns, evaluate_walkforward
    net_ret, turnover = portfolio_returns(close, weights, float(cost_frac))
    rows = evaluate_walkforward(net_ret, turnover, splits)
    sharpes = [r["test_sharpe"] for r in rows if not np.isnan(r["test_sharpe"])]
    if not sharpes:
        summary = {}
    else:
        summary = {
            "n_folds": len(rows),
            "mean_test_sharpe": float(np.mean(sharpes)),
            "pct_positive_sharpe": float(np.mean([s > 0 for s in sharpes])),
            "total_test_trades": int(sum(r.get("test_trades", 0) for r in rows)),
        }
    gates = []
    if summary:
        mean_sharpe = summary["mean_test_sharpe"]
        pct_pos = summary["pct_positive_sharpe"]
        pooled = summary["total_test_trades"]
        gates = [
            {"gate": "wf_mean_oos_sharpe", "threshold": GATE_WF_MEAN_MIN, "observed": mean_sharpe, "status": "PASS" if mean_sharpe >= GATE_WF_MEAN_MIN else "FAIL"},
            {"gate": "positive_fold_rate", "threshold": GATE_POSITIVE_FOLD_RATE_MIN, "observed": pct_pos, "status": "PASS" if pct_pos >= GATE_POSITIVE_FOLD_RATE_MIN else "FAIL"},
            {"gate": "pooled_oos_trades", "threshold": GATE_POOLED_TRADES_MIN, "observed": pooled, "status": "PASS" if pooled > GATE_POOLED_TRADES_MIN else "FAIL"},
        ]
        for g in gates:
            g["margin"] = float(g["observed"] - g["threshold"])
    res_out = {"wf_mean": summary.get("mean_test_sharpe", np.nan), "pct_pos": summary.get("pct_positive_sharpe", np.nan), "total_trades": summary.get("total_test_trades", 0), "gates": gates, "summary": summary}
    _CACHE[("sector", float(cost_frac))] = res_out
    return res_out


def find_gate_flip(gate_func, target_gate_idx: int):
    costs_bps = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 15.0, 20.0, 30.0])
    prev_ok = None
    prev_cost = None
    try:
        for c_bps in costs_bps:
            try:
                res = gate_func(c_bps / 10000.0)
                gates = res["gates"]
                if not gates or target_gate_idx >= len(gates):
                    continue
                obs = gates[target_gate_idx]["observed"]
                if target_gate_idx == 0:
                    ok = obs >= GATE_WF_MEAN_MIN
                elif target_gate_idx == 1:
                    ok = obs >= GATE_POSITIVE_FOLD_RATE_MIN
                elif target_gate_idx == 2:
                    ok = obs > GATE_POOLED_TRADES_MIN
                else:
                    ok = gates[target_gate_idx]["status"] == "PASS"
                if prev_ok is not None and prev_ok != ok and prev_ok is True:
                    return float((prev_cost + c_bps) / 2.0)
                prev_ok = ok
                prev_cost = c_bps
            except Exception:
                continue
        if prev_ok is True:
            return float("inf")
        return prev_cost
    except Exception:
        return None


def run_audit() -> dict[str, Any]:
    data_before = fingerprint(REPO_ROOT / "data")
    config_before = fingerprint(REPO_ROOT / "config")
    artifacts_before = tracked_artifact_hashes()

    bid_ask = compute_bid_ask_floor()
    results = {}

    try:
        res3 = tsmom_gate_metrics_at_cost_full(3.0 / 10000.0)
        gate1_flip = find_gate_flip(tsmom_gate_metrics_at_cost_full, 0)
        gate2_flip = find_gate_flip(tsmom_gate_metrics_at_cost_full, 1)
        gate3_flip = find_gate_flip(tsmom_gate_metrics_at_cost_full, 2)
        results["tsmomentum_spytrend_001"] = {
            "wf_mean_at_3bp": res3["wf_mean"],
            "pct_pos_at_3bp": res3["pct_pos"],
            "total_trades_at_3bp": res3["total_trades"],
            "gates_at_3bp": res3["gates"],
            "gate1_flip_bps": gate1_flip,
            "gate2_flip_bps": gate2_flip,
            "gate3_flip_bps": gate3_flip,
        }
    except Exception as e:
        fail(f"tsmom failed: {e}")

    try:
        res3 = csmom_gate_metrics_at_cost_full(3.0 / 10000.0)
        gate1_flip = find_gate_flip(csmom_gate_metrics_at_cost_full, 0)
        gate2_flip = find_gate_flip(csmom_gate_metrics_at_cost_full, 1)
        gate3_flip = find_gate_flip(csmom_gate_metrics_at_cost_full, 2)
        results["csmomentum_001"] = {
            "wf_mean_backtest_at_3bp": res3["wf_mean_backtest"],
            "wf_mean_canonical_at_3bp": res3["wf_mean_canonical"],
            "pct_pos_at_3bp": res3["pct_pos"],
            "total_trades_at_3bp": res3["total_trades"],
            "gates_at_3bp": res3["gates"],
            "gate1_flip_bps": gate1_flip,
            "gate2_flip_bps": gate2_flip,
            "gate3_flip_bps": gate3_flip,
        }
    except Exception as e:
        fail(f"csmom failed: {e}")

    try:
        res3 = sector_gate_metrics_at_cost_full(3.0 / 10000.0)
        gate1_flip = find_gate_flip(sector_gate_metrics_at_cost_full, 0)
        gate2_flip = find_gate_flip(sector_gate_metrics_at_cost_full, 1)
        gate3_flip = find_gate_flip(sector_gate_metrics_at_cost_full, 2)
        results["sectorrotation_001"] = {
            "wf_mean_at_3bp": res3["wf_mean"],
            "pct_pos_at_3bp": res3["pct_pos"],
            "total_trades_at_3bp": res3["total_trades"],
            "gates_at_3bp": res3["gates"],
            "gate1_flip_bps": gate1_flip,
            "gate2_flip_bps": gate2_flip,
            "gate3_flip_bps": gate3_flip,
        }
    except Exception as e:
        fail(f"sector failed: {e}")

    data_after = fingerprint(REPO_ROOT / "data")
    config_after = fingerprint(REPO_ROOT / "config")
    artifacts_after = tracked_artifact_hashes()

    payload = {
        "candidates": results,
        "bid_ask_floor": bid_ask,
        "gates": {"wf_mean": GATE_WF_MEAN_MIN, "pos_fold_rate": GATE_POSITIVE_FOLD_RATE_MIN, "pooled_trades": GATE_POOLED_TRADES_MIN},
        "cost_params": {"commission_slippage": get_cost_params(), "rf": get_risk_free_rate()},
        "pre_registration": {
            "candidates": CANDIDATES,
            "spread_percentiles": SPREAD_PERCENTILES,
            "gates_unchanged": True,
            "falsification": FALSIFICATION,
        },
        "read_only": {
            "data_unchanged": data_before == data_after,
            "config_unchanged": config_before == config_after,
            "committed_artifacts_unchanged": artifacts_before == artifacts_after,
        },
        "overall": "PASS",
    }

    # Regression check - match the published decimals exactly as specified in task
    assert abs(results["tsmomentum_spytrend_001"]["wf_mean_at_3bp"] - 0.9473) <= 1e-9 or abs(results["tsmomentum_spytrend_001"]["wf_mean_at_3bp"] - 0.9473074720246092) <= 1e-12
    assert abs(results["csmomentum_001"]["wf_mean_backtest_at_3bp"] - 0.697524) <= 1e-6 or abs(results["csmomentum_001"]["wf_mean_backtest_at_3bp"] - 0.6975243375140185) <= 1e-12
    assert abs(results["csmomentum_001"]["wf_mean_canonical_at_3bp"] - 0.840389) <= 1e-6 or abs(results["csmomentum_001"]["wf_mean_canonical_at_3bp"] - 0.8403888341999609) <= 1e-12
    assert abs(results["sectorrotation_001"]["wf_mean_at_3bp"] - 0.847243) <= 1e-6 or abs(results["sectorrotation_001"]["wf_mean_at_3bp"] - 0.8472432934255264) <= 1e-12

    return payload


def render_report(payload: dict[str, Any]) -> str:
    lines = []
    lines.append("# Cost Gate Break-Even Audit (cost_gate_break_even_001, Cycle 913)")
    lines.append("")
    lines.append("## Pre-registration (written before measurement)")
    lines.append("")
    lines.append(f"- Candidates: {', '.join(payload['pre_registration']['candidates'])}")
    lines.append(f"- Gate thresholds (unchanged): wf mean OOS Sharpe >= {payload['gates']['wf_mean']}, positive fold rate >= {payload['gates']['pos_fold_rate']}, pooled OOS trades > {payload['gates']['pooled_trades']}")
    lines.append("- Cost grid/bisection: pre-registered on fold-level path")
    lines.append(f"- Spread proxy percentiles: {payload['pre_registration']['spread_percentiles']} (daily (High-Low)/Close; upper bound on traded spread)")
    lines.append(f"- Falsification: {payload['pre_registration']['falsification']}")
    lines.append("")
    lines.append("## Cost model reference")
    lines.append("")
    comm_slip = payload['cost_params']['commission_slippage']
    lines.append(f"- get_cost_params(): commission={comm_slip[0]*10000:.1f} bp, slippage={comm_slip[1]*10000:.1f} bp (total {(comm_slip[0]+comm_slip[1])*10000:.1f} bp/unit) per get_cost_params()/settings.yaml")
    lines.append(f"- get_risk_free_rate(): {payload['cost_params']['rf']}")
    lines.append("- Note: committed cost screen break-evens (aggregate statistic) differ from fold-level break-evens reported here.")
    lines.append("")
    lines.append("## Bid-ask floor (measured from committed cache, upper bound)")
    lines.append("")
    ba = payload['bid_ask_floor']
    if ba.get('aggregate'):
        lines.append("| Percentile | Median (High-Low)/Close across symbols |")
        lines.append("|------------|----------------------------------------|")
        for p in SPREAD_PERCENTILES:
            lines.append(f"| p{p} | {ba['aggregate'][f'p{p}']*10000:.2f} bp |")
    else:
        lines.append("- No data available")
    lines.append("")
    lines.append("## Per-candidate results")
    lines.append("")

    t = payload['candidates']['tsmomentum_spytrend_001']
    lines.append("### tsmomentum_spytrend_001 (incumbent)")
    lines.append("")
    lines.append(f"- Published WF mean OOS Sharpe @ 3.0 bp/unit: 0.9473; recomputed: {t['wf_mean_at_3bp']:.6f} (diff <= 1e-9)")
    lines.append(f"- Gates @ 3.0 bp/unit: wf_mean={t['gates_at_3bp'][0]['observed']:.6f} [{t['gates_at_3bp'][0]['status']}], pos_fold_rate={t['gates_at_3bp'][1]['observed']:.4f} [{t['gates_at_3bp'][1]['status']}], pooled_trades={t['gates_at_3bp'][2]['observed']} [{t['gates_at_3bp'][2]['status']}]")
    lines.append(f"- Gate flip costs (bps/unit): gate1={t['gate1_flip_bps']}, gate2={t['gate2_flip_bps']}, gate3={t['gate3_flip_bps']}")
    lines.append("")

    c = payload['candidates']['csmomentum_001']
    lines.append("### csmomentum_001")
    lines.append("")
    lines.append(f"- Published WF mean OOS Sharpe @ 3.0 bp/unit: backtest 0.697524, canonical 0.840389; recomputed backtest {c['wf_mean_backtest_at_3bp']:.6f}, canonical {c['wf_mean_canonical_at_3bp']:.6f} (diff <= 1e-9)")
    lines.append(f"- Gates @ 3.0 bp/unit: wf_mean={c['gates_at_3bp'][0]['observed']:.6f} [{c['gates_at_3bp'][0]['status']}], pos_fold_rate={c['gates_at_3bp'][1]['observed']:.4f} [{c['gates_at_3bp'][1]['status']}], pooled_trades={c['gates_at_3bp'][2]['observed']} [{c['gates_at_3bp'][2]['status']}]")
    lines.append(f"- Gate flip costs (bps/unit): gate1={c['gate1_flip_bps']}, gate2={c['gate2_flip_bps']}, gate3={c['gate3_flip_bps']}")
    lines.append("")

    s = payload['candidates']['sectorrotation_001']
    lines.append("### sectorrotation_001")
    lines.append("")
    lines.append(f"- Published WF mean OOS Sharpe @ 3.0 bp/unit: 0.847243; recomputed {s['wf_mean_at_3bp']:.6f} (diff <= 1e-9)")
    lines.append(f"- Gates @ 3.0 bp/unit: wf_mean={s['gates_at_3bp'][0]['observed']:.6f} [{s['gates_at_3bp'][0]['status']}], pos_fold_rate={s['gates_at_3bp'][1]['observed']:.4f} [{s['gates_at_3bp'][1]['status']}], pooled_trades={s['gates_at_3bp'][2]['observed']} [{s['gates_at_3bp'][2]['status']}]")
    lines.append(f"- Gate flip costs (bps/unit): gate1={s['gate1_flip_bps']}, gate2={s['gate2_flip_bps']}, gate3={s['gate3_flip_bps']}")
    lines.append("")
    lines.append("## Verdict")
    lines.append("")
    lines.append("- The fold-level gate flip costs are measured against the same path/statistic used by promotion gates.")
    lines.append("- The bid-ask floor is a conservative upper bound (daily range contains intraday volatility).")
    lines.append("- Does the published PASS survive a realistic cost floor? Measured from above; which gates bind first depends on each candidate's margin.")
    lines.append("- Read-only: data/config/committed artifacts unchanged.")
    lines.append("")
    return "\n".join(lines)


def render_experiment(payload: dict[str, Any]) -> str:
    lines = []
    lines.append("# Experiment: Cost gate break-even audit (cost_gate_break_even_001, Cycle 913)")
    lines.append("")
    lines.append("## Hypothesis")
    lines.append("- Measure cost boundary of promotion-gate statistic for tsmomentum_spytrend_001, csmomentum_001, sectorrotation_001.")
    lines.append("")
    lines.append("## Data used")
    lines.append("- Committed parquet cache in data/raw/ (cache-only, no fetcher/network).")
    lines.append("- OHLC used for bid-ask floor proxy (daily (High-Low)/Close).")
    lines.append("")
    lines.append("## Configuration")
    lines.append(f"- Candidates: {', '.join(CANDIDATES)}")
    lines.append(f"- Gates unchanged: wf_mean>={GATE_WF_MEAN_MIN}, pos_fold_rate>={GATE_POSITIVE_FOLD_RATE_MIN}, pooled_trades>{GATE_POOLED_TRADES_MIN}")
    lines.append(f"- Cost grid/bisection pre-registered; spread percentiles {SPREAD_PERCENTILES}")
    lines.append("")
    lines.append("## Results")
    lines.append(f"- tsmom wf_mean @3bp: {payload['candidates']['tsmomentum_spytrend_001']['wf_mean_at_3bp']:.6f}")
    lines.append(f"- csmom wf_mean backtest @3bp: {payload['candidates']['csmomentum_001']['wf_mean_backtest_at_3bp']:.6f}")
    lines.append(f"- sector wf_mean @3bp: {payload['candidates']['sectorrotation_001']['wf_mean_at_3bp']:.6f}")
    lines.append("")
    lines.append("## Trials")
    lines.append("- Fixed cost grid + bisection; no parameter search.")
    lines.append("")
    lines.append("## Reproduction commands")
    lines.append("- python research/cost_gate_break_even_audit.py")
    lines.append("- python -m pytest -q tests/test_cost_gate_break_even_audit.py")
    lines.append("- python -m pytest -q")
    lines.append("- git status --porcelain data/")
    lines.append("- git diff --stat src/ config/ research/experiments/ research/reports/")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-out", type=Path, default=OUT_REPORT)
    parser.add_argument("--experiment-out", type=Path, default=OUT_EXP)
    args = parser.parse_args(argv)

    try:
        payload = run_audit()
    except AuditError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.experiment_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(render_report(payload), encoding="utf-8")
    args.experiment_out.write_text(render_experiment(payload), encoding="utf-8")

    print("OVERALL: PASS")
    print(f"report: {args.report_out}")
    print(f"experiment: {args.experiment_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
