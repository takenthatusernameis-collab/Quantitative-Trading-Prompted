#!/usr/bin/env python3
"""SMA-175 validation audit for the incumbent ``tsmomentum_spytrend_001``."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.run_cycle6 import (  # noqa: E402
    DD_THRESHOLD,
    END_DATE,
    LOOKBACK,
    SKIP,
    SPY_SMA_WINDOW,
    START_DATE,
    SYMBOLS,
    TOP_FRACTION,
    VOL_TARGET,
    VOL_TARGET_LOOKBACK,
    WF_EMBARGO_DAYS,
    WF_PURGE_DAYS,
    WF_STEP_MONTHS,
    WF_TEST_MONTHS,
    WF_TRAIN_YEARS,
    _apply_overlay,
)
from src.backtest.engine import get_cost_params, get_risk_free_rate  # noqa: E402
from src.evaluation.walkforward import evaluate_walkforward, summarize_walkforward  # noqa: E402
from src.features.momentum import build_weights  # noqa: E402

CANDIDATE_ID = "tsmomentum_spytrend_001"
CYCLE = "914"
SMA_NEW = 175
SMA_BASELINE = 200

REPORTS_DIR = REPO_ROOT / "research" / "reports"
EXPERIMENTS_DIR = REPO_ROOT / "research" / "experiments"
RAW_DIR = REPO_ROOT / "data" / "raw"
OUT_REPORT = REPORTS_DIR / "tsmomentum_sma175_validation_001.md"
OUT_EXP = EXPERIMENTS_DIR / "tsmomentum_sma175_validation_001.md"


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
                rel = path.relative_to(REPO_ROOT)
            except ValueError:
                continue
            out[str(rel)] = sha256_file(path)
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
        except OSError:
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


def load_close_from_cache(symbols: list[str], raw_dir: Path) -> pd.DataFrame:
    frames: dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        path = raw_dir / f"{symbol}.parquet"
        if not path.exists():
            fail(f"missing cached price: {path}")
        try:
            df = pd.read_parquet(path)
        except Exception as exc:  # noqa: BLE001
            fail(f"unreadable {path}: {exc}")
        idx = pd.to_datetime(df.index)
        if idx.tz is None:
            idx = idx.tz_localize("UTC", ambiguous="infer", nonexistent="shift_forward")
        else:
            idx = idx.tz_convert("UTC")
        df = df.copy()
        df.index = idx
        frames[symbol] = df.sort_index()

    all_index = pd.DatetimeIndex(sorted(set().union(*[f.index for f in frames.values()])))
    all_index = all_index[all_index.weekday < 5]
    if len(all_index) == 0:
        fail("empty calendar")

    out = pd.DataFrame(index=all_index)
    for symbol, df in frames.items():
        out[symbol] = df["Close"].reindex(all_index).ffill()
    out = out.ffill().dropna(how="all")
    missing = [c for c in symbols if c not in out.columns]
    if missing:
        fail(f"missing symbols: {missing}")
    return out


def _utc(ts: str) -> pd.Timestamp:
    return pd.Timestamp(ts, tz="UTC")


def _eval_candidate_period(
    close: pd.DataFrame,
    symbols: list[str],
    start_date: str,
    end_date: str,
    spy_sma_window: int,
) -> tuple[pd.Series, pd.DataFrame]:
    weights = build_weights(close, lookback=LOOKBACK, skip=SKIP, top_fraction=TOP_FRACTION)
    common = close.index.intersection(weights.index)
    close_a = close.loc[common]
    weights_a = weights.loc[common]
    daily_ret = close_a.pct_change().fillna(0.0)

    spy = close_a["SPY"]
    spy_sma = spy.rolling(spy_sma_window).mean()
    exposure = pd.Series(1.0, index=close_a.index)
    exposure[spy < spy_sma] = 0.0
    exposure[spy.isna() | spy_sma.isna()] = 0.0

    cw, net_ret, _ = _apply_overlay(daily_ret, weights_a, exposure_factor=exposure)
    mask = (cw.index >= start_date) & (cw.index <= end_date)
    return net_ret[mask], cw[mask]


def eval_candidate_test_period(close: pd.DataFrame, spy_sma_window: int) -> dict[str, Any]:
    weights = build_weights(close, lookback=LOOKBACK, skip=SKIP, top_fraction=TOP_FRACTION)
    common = close.index.intersection(weights.index)
    close_a = close.loc[common]
    weights_a = weights.loc[common]
    daily_ret = close_a.pct_change().fillna(0.0)

    test_mask = weights_a.index > _utc("2017-12-31")
    test_asset_ret = daily_ret[test_mask]
    test_weights = weights_a[test_mask]

    spy = close_a["SPY"]
    spy_sma = spy.rolling(spy_sma_window).mean()
    exposure = pd.Series(1.0, index=close_a.index)
    exposure[spy < spy_sma] = 0.0
    exposure[spy.isna() | spy_sma.isna()] = 0.0
    test_exposure = exposure[test_mask]

    cw, net_ret_test, metrics_test = _apply_overlay(test_asset_ret, test_weights, exposure_factor=test_exposure)
    return {
        "net_ret_test": net_ret_test,
        "combined_weights": cw,
        "test_metrics": metrics_test,
        "test_index": net_ret_test.index,
    }


def run_walkforward_for_sma(close: pd.DataFrame, spy_sma_window: int) -> dict[str, Any]:
    def config_fn(symbols: list[str], start: str, end: str) -> tuple[pd.Series, pd.DataFrame]:
        return _eval_candidate_period(close, symbols, start, end, spy_sma_window=spy_sma_window)

    wf_df = evaluate_walkforward(
        SYMBOLS,
        START_DATE,
        END_DATE,
        config_fn,
        train_years=WF_TRAIN_YEARS,
        test_months=WF_TEST_MONTHS,
        step_months=WF_STEP_MONTHS,
        purge_days=WF_PURGE_DAYS,
        embargo_days=WF_EMBARGO_DAYS,
    )
    summary = summarize_walkforward(wf_df)
    return {"wf_df": wf_df, "summary": summary}


def run_plateau_for_sma(close: pd.DataFrame) -> dict[str, Any]:
    sma_windows = [150, 175, 200, 226, 250, 277]
    results = []
    for w in sma_windows:
        r = eval_candidate_test_period(close, spy_sma_window=w)
        m = r["test_metrics"]
        results.append(
            {
                "sma_window": w,
                "test_sharpe": m["sharpe_ratio"],
                "test_ann_return": m["annualized_return"],
                "test_max_dd": m["max_drawdown"],
                "test_trades": m["trade_count"],
                "test_sortino": m["sortino_ratio"],
                "test_profit_factor": m["profit_factor"],
            }
        )
    plateau_df = pd.DataFrame(results)
    n_pass = int((plateau_df["test_sharpe"] >= 0.9).sum())
    is_robust = n_pass >= 2
    return {"plateau_df": plateau_df, "n_pass": n_pass, "is_robust": is_robust, "sma_windows": sma_windows}


def fmt(v: float, d: int = 6) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "N/A"
    return f"{float(v):.{d}f}"


def run_audit() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def record(name: str, ok: bool, observed: Any = "", expected: Any = "") -> None:
        checks.append({"name": name, "pass": bool(ok), "observed": observed, "expected": expected})

    data_before = fingerprint(REPO_ROOT / "data")
    config_before = fingerprint(REPO_ROOT / "config")
    artifacts_before = tracked_artifact_hashes()

    close = load_close_from_cache(list(SYMBOLS), RAW_DIR)
    record("cache_loaded", True, f"{len(close)} sessions")

    wf200 = run_walkforward_for_sma(close, spy_sma_window=SMA_BASELINE)
    wf175 = run_walkforward_for_sma(close, spy_sma_window=SMA_NEW)

    summary200 = wf200["summary"]
    summary175 = wf175["summary"]

    record("wf_sma200_folds", summary200.get("n_folds", 0) == 48, summary200.get("n_folds", 0), 48)
    record("wf_sma175_folds", summary175.get("n_folds", 0) == 48, summary175.get("n_folds", 0), 48)
    record("wf_sma200_mean_sharpe_exists", not np.isnan(summary200.get("mean_test_sharpe", np.nan)))
    record("wf_sma175_mean_sharpe_exists", not np.isnan(summary175.get("mean_test_sharpe", np.nan)))

    plateau = run_plateau_for_sma(close)
    record("plateau_windows", len(plateau["plateau_df"]) == 6, len(plateau["plateau_df"]), 6)

    data_after = fingerprint(REPO_ROOT / "data")
    config_after = fingerprint(REPO_ROOT / "config")
    artifacts_after = tracked_artifact_hashes()
    record("data_unchanged", data_before == data_after)
    record("config_unchanged", config_before == config_after)
    record("committed_artifacts_unchanged", artifacts_before == artifacts_after)

    commission_bps, slippage_bps = get_cost_params()
    payload = {
        "candidate_id": CANDIDATE_ID,
        "cycle": CYCLE,
        "sma_baseline": SMA_BASELINE,
        "sma_new": SMA_NEW,
        "run_cycle6_sma_still_baseline": SPY_SMA_WINDOW == SMA_BASELINE,
        "config": {
            "symbols": SYMBOLS,
            "start": START_DATE,
            "end": END_DATE,
            "lookback": LOOKBACK,
            "skip": SKIP,
            "top_fraction": TOP_FRACTION,
            "vol_target": VOL_TARGET,
            "dd_threshold": DD_THRESHOLD,
            "vol_target_lookback": VOL_TARGET_LOOKBACK,
            "wf_train_years": WF_TRAIN_YEARS,
            "wf_test_months": WF_TEST_MONTHS,
            "wf_step_months": WF_STEP_MONTHS,
            "wf_purge_days": WF_PURGE_DAYS,
            "wf_embargo_days": WF_EMBARGO_DAYS,
        },
        "costs": {
            "commission_bps": float(commission_bps * 10000.0),
            "slippage_bps": float(slippage_bps * 10000.0),
            "total_bps": float((commission_bps + slippage_bps) * 10000.0),
            "rf_annual": float(get_risk_free_rate()),
        },
        "walkforward_sma200": wf200,
        "walkforward_sma175": wf175,
        "plateau": plateau,
        "checks": checks,
        "read_only": {
            "data_unchanged": data_before == data_after,
            "config_unchanged": config_before == config_after,
            "committed_artifacts_unchanged": artifacts_before == artifacts_after,
        },
    }
    return payload


def render_report(payload: dict[str, Any]) -> str:
    wf200 = payload["walkforward_sma200"]["summary"]
    wf175 = payload["walkforward_sma175"]["summary"]
    p = payload["plateau"]
    lines = []
    lines.append(f"# TSMomentum SMA-175 Validation (tsmomentum_sma175_validation_001, Cycle {CYCLE})")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Candidate: `{payload['candidate_id']}`")
    lines.append(f"- Change validated: SPY SMA window {payload['sma_baseline']} -> {payload['sma_new']} days")
    lines.append(f"- run_cycle6.py still has SMA baseline: {payload['run_cycle6_sma_still_baseline']}")
    lines.append(f"- WF SMA-200 mean Sharpe: {fmt(wf200.get('mean_test_sharpe'), 4)} (folds {wf200.get('n_folds', 0)})")
    lines.append(f"- WF SMA-175 mean Sharpe: {fmt(wf175.get('mean_test_sharpe'), 4)} (folds {wf175.get('n_folds', 0)})")
    lines.append(f"- Plateau (6 windows): passes {p['n_pass']}/6 (robust={p['is_robust']})")
    lines.append(f"- Data/config unchanged: {payload['read_only']['data_unchanged'] and payload['read_only']['config_unchanged']}")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for c in payload["checks"]:
        lines.append(f"- [{c['name']}]: {'PASS' if c['pass'] else 'FAIL'}")
    lines.append("")
    return "\n".join(lines)


def render_experiment(payload: dict[str, Any]) -> str:
    wf200 = payload["walkforward_sma200"]["summary"]
    wf175 = payload["walkforward_sma175"]["summary"]
    lines = []
    lines.append(f"# Experiment: SMA-175 validation for {payload['candidate_id']} (Cycle {CYCLE})")
    lines.append("")
    lines.append("Read-only validation comparing SMA-200 vs SMA-175 under published protocol.")
    lines.append("")
    lines.append(f"- WF SMA-200 mean Sharpe: {fmt(wf200.get('mean_test_sharpe'), 4)} (folds {wf200.get('n_folds', 0)})")
    lines.append(f"- WF SMA-175 mean Sharpe: {fmt(wf175.get('mean_test_sharpe'), 4)} (folds {wf175.get('n_folds', 0)})")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    payload = run_audit()
    overall = all(c["pass"] for c in payload["checks"])
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(render_report(payload), encoding="utf-8")
    OUT_EXP.write_text(render_experiment(payload), encoding="utf-8")
    print("OVERALL: PASS" if overall else "OVERALL: FAIL")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
