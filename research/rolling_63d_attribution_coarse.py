"""Coarse rolling-63d Sharpe attribution by point-in-time bucket.

Reads only the committed paper-trading state; writes nothing. Reports, for the
last 63 sessions, each bucket's session share, return share, and sub-sample
rolling-63d Sharpe. The falsification condition is that no single bucket carries
a disproportionate share of the decline.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluation.sharpe import sharpe_ratio  # noqa: E402
from src.evaluation.drift import sharpe_persistence  # noqa: E402
from src.simulation.paper_trading import PaperTradingState  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = REPO_ROOT / "data" / "processed" / "paper_trading_state.yaml"
WINDOW = 63


def _sharpe(returns: pd.Series) -> float:
    if len(returns) < 2 or returns.std(ddof=1) == 0:
        return float("nan")
    return float(sharpe_ratio(list(returns)))


def _bucket_report(name: str, mask: pd.Series, window_returns: pd.Series) -> dict:
    sub = window_returns[mask]
    share_sessions = float(mask.mean())
    share_return = float(sub.sum() / window_returns.sum()) if window_returns.sum() != 0 else float("nan")
    return {
        "bucket": name,
        "sessions": int(mask.sum()),
        "share_sessions": round(share_sessions, 4),
        "share_return": None if np.isnan(share_return) else round(share_return, 4),
        "sharpe": None if len(sub) < 2 or np.isnan(_sharpe(sub)) else round(_sharpe(sub), 4),
        "mean_daily_ret": None if len(sub) == 0 else round(float(sub.mean()), 6),
    }


def main() -> int:
    state = PaperTradingState.from_yaml(STATE_PATH)
    rh = pd.DataFrame(state.run_history)
    rh["date"] = pd.to_datetime(rh["date"])
    rh = rh.sort_values("date").reset_index(drop=True)

    persistence = sharpe_persistence(rh["date"], rh["daily_return"])
    series = persistence["series"]
    tail = {d.strftime("%Y-%m-%d"): round(v, 4) for d, v in series[-10:] if v is not None}

    window = rh.tail(WINDOW).copy()
    ret = window["daily_return"].astype(float)
    vol_q = pd.qcut(window["vol_scale"], 4, labels=["q1", "q2", "q3", "q4"], duplicates="drop")

    buckets = {
        "regime_risk_on": window["regime_exposure"] > 0.5,
        "regime_risk_off": window["regime_exposure"] <= 0.5,
        "exposure_full": window["n_positions"] >= 4,
        "exposure_cash": window["n_positions"] <= 0,
        "vol_q1": vol_q == "q1",
        "vol_q4": vol_q == "q4",
        "first_half": window.index < window.index[len(window) // 2],
        "second_half": window.index >= window.index[len(window) // 2],
    }

    rows = [_bucket_report(name, mask, ret) for name, mask in buckets.items()]

    print("=== Rolling-63d Sharpe attribution, coarse buckets (last 63 sessions) ===")
    print(f"window: {window['date'].min().date()} .. {window['date'].max().date()} ({len(window)} sessions)")
    print(f"window cumulative return: {ret.sum():.6f}")
    print(f"window rolling-63d Sharpe: {_sharpe(ret):.4f}")
    print(f"tail series: {tail}")
    print()
    print(f"{'bucket':<18}{'sessions':>9}{'share_sessions':>14}{'share_return':>13}{'sharpe':>10}{'mean_ret':>12}")
    for r in rows:
        print(
            f"{r['bucket']:<18}{r['sessions']:>9}{r['share_sessions']:>14}"
            f"{str(r['share_return']):>13}{str(r['sharpe']):>10}{str(r['mean_daily_ret']):>12}"
        )

    shares = [r["share_return"] for r in rows if r["share_return"] is not None]
    top = max(shares, key=lambda x: abs(x)) if shares else None
    concentrated = top is not None and abs(top) > 0.5
    print()
    print(f"largest |share_return| bucket: {top}")
    print(f"concentrated (single bucket > 50% of window return): {concentrated}")
    print(f"falsification (broad, unattributable decline): {not concentrated}")
    return 0


if __name__ == "__main__":
    sys.exit(main())