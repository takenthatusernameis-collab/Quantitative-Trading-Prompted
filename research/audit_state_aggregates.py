"""Independent recomputation of the stored aggregate fields in the canonical
paper-trading state, derived solely from ``run_history``.

Prior cycles verified the drift flag (``low_rolling_sharpe``) and the
extension clock gate. This audit covers the *other* stored aggregates
(``rolling_sharpe_63d``, ``rolling_max_dd_63d``, ``regime_persistence_days``,
``vol_scale_min/max``, ``dd_scale_min/max``, ``turnover_median/p95``,
``peak_nav``, ``max_drawdown``) against the per-session record, using the exact
update formulas in ``src/simulation/paper_trading.run_daily_paper_update``.

It is read-only: it opens the committed state, recomputes, and reports
mismatches. It writes nothing.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.evaluation.sharpe import sharpe_ratio  # noqa: E402

STATE_PATH = ROOT / "data" / "processed" / "paper_trading_state.yaml"

# Defaults mirrored from src/simulation/paper_trading.py
DEFAULT_SHARPE_THRESHOLD = 0.5
DEFAULT_MIN_PERIODS = 20


def _nav_series(rh: list[dict]) -> np.ndarray:
    return np.array([float(r["nav"]) for r in rh], dtype=float)


def _returns_from_nav(nav: np.ndarray) -> np.ndarray:
    out = np.empty_like(nav)
    out[0] = nav[0] / 100000.0 - 1.0
    out[1:] = nav[1:] / nav[:-1] - 1.0
    return out


def audit(state: dict | None = None) -> dict:
    if state is None:
        with open(STATE_PATH) as fh:
            state = yaml.safe_load(fh) or {}

    rh = state["run_history"]
    dates = [str(r["date"]) for r in rh]
    nav = _nav_series(rh)
    rets = _returns_from_nav(nav)

    # --- rolling 63d sharpe (last 63 returns, canonical convention) ---
    recent = rets[-63:]
    rolling_sharpe = float(sharpe_ratio(recent))

    # --- rolling max dd: min(cum/peak - 1) over the full NAV product series ---
    cum = np.cumprod(1.0 + rets)
    peak = np.maximum.accumulate(cum)
    rolling_max_dd = float((cum / peak - 1.0).min())

    # --- regime persistence: consecutive trailing identical regime_exposure ---
    regimes = [float(r["regime_exposure"]) for r in rh]
    regime_persistence = 0
    for v in reversed(regimes):
        if regime_persistence == 0:
            last = v
            regime_persistence = 1
        elif v == last:
            regime_persistence += 1
        else:
            break

    # --- vol_scale / dd_scale running min/max ---
    vol_scales = [float(r["vol_scale"]) for r in rh]
    dd_scales = [float(r["dd_scale"]) for r in rh]
    vol_scale_min = min(vol_scales)
    vol_scale_max = max(vol_scales)
    dd_scale_min = min(dd_scales)
    dd_scale_max = max(dd_scales)

    # --- turnover distribution over run_history ---
    turnovers = [float(r["turnover"]) for r in rh]
    turnover_median = float(np.median(turnovers))
    turnover_p95 = float(np.percentile(turnovers, 95))

    # --- peak nav and running max drawdown over the NAV series ---
    peak_nav = float(nav.max())
    running_peak = np.maximum.accumulate(nav)
    dd_series = nav / running_peak - 1.0
    max_drawdown = float(dd_series.min())

    recomputed = {
        "rolling_sharpe_63d": rolling_sharpe,
        "rolling_max_dd_63d": rolling_max_dd,
        "regime_persistence_days": int(regime_persistence),
        "vol_scale_min": float(vol_scale_min),
        "vol_scale_max": float(vol_scale_max),
        "dd_scale_min": float(dd_scale_min),
        "dd_scale_max": float(dd_scale_max),
        "turnover_median": turnover_median,
        "turnover_p95": turnover_p95,
        "peak_nav": peak_nav,
        "max_drawdown": max_drawdown,
    }

    stored = {
        "rolling_sharpe_63d": float(state["rolling_sharpe_63d"]),
        "rolling_max_dd_63d": float(state["rolling_max_dd_63d"]),
        "regime_persistence_days": int(state["regime_persistence_days"]),
        "vol_scale_min": float(state["vol_scale_min"]),
        "vol_scale_max": float(state["vol_scale_max"]),
        "dd_scale_min": float(state["dd_scale_min"]),
        "dd_scale_max": float(state["dd_scale_max"]),
        "turnover_median": float(state["turnover_median"]),
        "turnover_p95": float(state["turnover_p95"]),
        "peak_nav": float(state["peak_nav"]),
        "max_drawdown": float(state["max_drawdown"]),
    }

    mismatches = {}
    for k in recomputed:
        r, s = recomputed[k], stored[k]
        tol = 1e-6 if isinstance(r, float) else 0
        if isinstance(r, float):
            ok = abs(r - s) <= max(tol, abs(s) * 1e-9)
        else:
            ok = r == s
        if not ok:
            diff = (r - s) if isinstance(r, float) else None
            mismatches[k] = {"recomputed": r, "stored": s, "diff": diff}

    return {
        "sessions": len(rh),
        "date_range": f"{dates[0]} -> {dates[-1]}",
        "recomputed": recomputed,
        "stored": stored,
        "mismatches": mismatches,
        "all_match": len(mismatches) == 0,
    }


def main() -> int:
    result = audit()
    print(f"state sessions: {result['sessions']}  date_range: {result['date_range']}")
    print(f"aggregate fields audited: {len(result['recomputed'])}")
    print(f"all_match: {result['all_match']}")
    if result["mismatches"]:
        print("MISMATCHES:")
        for k, v in result["mismatches"].items():
            print(f"  {k}: recomputed={v['recomputed']} stored={v['stored']} diff={v['diff']}")
        return 1
    print("OK: every stored aggregate matches its recomputation from run_history")
    return 0


if __name__ == "__main__":
    sys.exit(main())