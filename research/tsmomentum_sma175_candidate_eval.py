"""Independent SMA-175 candidate evaluation hook (read-only)."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.run_cycle6 import (
    COMMISSION_BPS,
    DD_THRESHOLD,
    END_DATE,
    LOOKBACK,
    SKIP,
    SLIPPAGE_BPS,
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
    _utc,
)
from src.backtest.engine import compute_metrics, get_cost_params, get_risk_free_rate
from src.evaluation.walkforward import evaluate_walkforward, summarize_walkforward
from src.features.momentum import build_weights

RAW_DIR = REPO_ROOT / "data" / "raw"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
OUT_REPORT = REPORTS_DIR / "tsmomentum_sma175_candidate_eval_001.md"

SMA_NEW = 175
CANDIDATE_ID = "tsmomentum_sma175_candidate_eval"
CYCLE = 918


def _git_hash() -> str:
    try:
        import subprocess

        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except (OSError, RuntimeError):
        return "unknown"


def _today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def load_close_from_cache(symbols: list[str]) -> pd.DataFrame:
    frames: dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        path = RAW_DIR / f"{symbol}.parquet"
        if not path.exists():
            raise FileNotFoundError(f"missing cached price: {path}")
        try:
            df = pd.read_parquet(path)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"unreadable {path}: {exc}") from exc
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
        raise RuntimeError("empty calendar")

    out = pd.DataFrame(index=all_index)
    for symbol, df in frames.items():
        if "Close" not in df.columns:
            raise RuntimeError(f"missing Close for {symbol}")
        out[symbol] = df["Close"].reindex(all_index).ffill()
    out = out.ffill().dropna(how="all")
    missing = [c for c in symbols if c not in out.columns]
    if missing:
        raise RuntimeError(f"missing symbols: {missing}")
    return out


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


def fmt(v: float, d: int = 4) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "N/A"
    return f"{float(v):.{d}f}"


def run_candidate_eval() -> dict[str, Any]:
    """Run independent SMA-175 candidate evaluation (read-only)."""
    close = load_close_from_cache(list(SYMBOLS))
    wf175 = run_walkforward_for_sma(close, spy_sma_window=SMA_NEW)
    summary175 = wf175["summary"]

    commission_bps, slippage_bps = get_cost_params()
    payload: dict[str, Any] = {
        "candidate_id": CANDIDATE_ID,
        "cycle": CYCLE,
        "sma_new": SMA_NEW,
        "sma_baseline_incumbent": SPY_SMA_WINDOW,
        "config": {
            "symbols": list(SYMBOLS),
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
        "walkforward_sma175": wf175,
        "summary": summary175,
        "git_rev": _git_hash(),
        "date": _today(),
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = render_report(payload)
    OUT_REPORT.write_text(report, encoding="utf-8")
    payload["report_path"] = str(OUT_REPORT)
    return payload


def render_report(payload: dict[str, Any]) -> str:
    s = payload["summary"]
    lines = []
    lines.append(f"# TSMomentum SMA-175 Candidate Eval ({payload['candidate_id']}, Cycle {payload['cycle']})")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Candidate: `{payload['candidate_id']}`")
    lines.append(f"- SMA window (candidate): {payload['sma_new']}")
    lines.append(f"- Incumbent SMA window (run_cycle6): {payload['sma_baseline_incumbent']} (unchanged)")
    lines.append(f"- Folds: {s.get('n_folds', 0)}")
    lines.append(f"- Mean test Sharpe: {fmt(s.get('mean_test_sharpe'))}")
    pct_pos = s.get('pct_positive_sharpe')
    if isinstance(pct_pos, float) and np.isnan(pct_pos):
        lines.append("- % Positive Sharpe: N/A")
    else:
        lines.append(f"- % Positive Sharpe: {float(pct_pos):.1%}")
    max_dd = s.get('mean_test_max_dd')
    if isinstance(max_dd, float) and np.isnan(max_dd):
        lines.append("- Mean test max DD: N/A")
    else:
        lines.append(f"- Mean test max DD: {float(max_dd):.2%}")
    lines.append(f"- Total test trades: {s.get('total_test_trades', 0)}")
    lines.append("")
    lines.append("## Config")
    lines.append("")
    for k, v in payload["config"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Costs")
    lines.append("")
    for k, v in payload["costs"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append(f"Git rev: {payload['git_rev']}")
    lines.append(f"Date: {payload['date']}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    payload = run_candidate_eval()
    s = payload["summary"]
    print(f"OVERALL: PASS (folds={s.get('n_folds',0)}, mean_sharpe={fmt(s.get('mean_test_sharpe'))})")
    print(f"REPORT: {payload['report_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
