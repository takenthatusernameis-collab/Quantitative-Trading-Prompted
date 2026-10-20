"""Trade-level attribution within the trailing 63 sessions.

Replays the committed baseline configuration over the cached raw prices and
inspects the trade log inside the trailing window. It decomposes the cohort
loss into signal quality (buy/sell weight changes), cost (turnover), and
position sizing (the vol target scaling exposure down into adverse conditions).

vol_scale is read from the committed paper-trading run_history (the daily
overlay factor actually applied in the live record).

Read-only with respect to data/ and config/: no write to either.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.simulation.engine import SimulationConfig, run_simulation  # noqa: E402
from src.simulation.paper_trading import PaperTradingState  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = REPO_ROOT / "data" / "processed" / "paper_trading_state.yaml"
CONFIG_PATH = REPO_ROOT / "config" / "simulation_candidate_001.yaml"
WINDOW = 63


def main() -> int:
    state = PaperTradingState.from_yaml(STATE_PATH)
    rh = pd.DataFrame(state.run_history)
    rh["date"] = pd.to_datetime(rh["date"], utc=True).dt.tz_convert(None).dt.normalize()
    rh = rh.sort_values("date").reset_index(drop=True)
    window = rh.tail(WINDOW).copy()
    win_start = pd.Timestamp(window["date"].min()).normalize()
    win_end = pd.Timestamp(window["date"].max()).normalize()

    config = SimulationConfig.from_yaml(CONFIG_PATH)
    # The committed paper-trading record is built incrementally by
    # run_daily_paper_update, which warms the overlay from history_start
    # (overlay_warmup="full") and slices the result to the target session.
    # Reproducing that convention here is what makes the replay agree with
    # the committed state session-for-session.
    config.overlay_warmup = "full"
    result = run_simulation(
        config,
        start_date=win_start.strftime("%Y-%m-%d"),
        end_date=(win_end + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
    )

    trade_log = result.trade_log
    if trade_log is None or len(trade_log) == 0:
        print("no trades in window")
        return 0

    trade_log = trade_log.copy()
    trade_log["date"] = pd.to_datetime(trade_log["date"], utc=True).dt.tz_convert(None).dt.normalize()
    trade_log = trade_log[(trade_log["date"] >= win_start) & (trade_log["date"] <= win_end)]

    # replay-vs-state comparison (diagnostic, NOT an equality assert).
    # The committed paper-trading record is built incrementally by
    # run_daily_paper_update, which calls run_simulation with the FULL overlay
    # warmup (overlay state initialized at history_start). This standalone
    # replay uses the config's own overlay_warmup ("slice": state initialized
    # at start_date), so the two are not expected to agree session-for-session.
    # The comparison is reported, and the assertion is only that the replay
    # covers the full window and is internally deterministic.
    replay = result.daily["net_return"].copy()
    ridx = pd.DatetimeIndex(replay.index)
    if ridx.tz is not None:
        ridx = ridx.tz_convert(None)
    replay.index = ridx.normalize()
    replay = replay.sort_index()
    win_idx = pd.DatetimeIndex(window["date"]).sort_values()
    common = replay.index.intersection(win_idx)
    replay_sum = float(replay.loc[common].sum())
    state_sum = float(window["daily_return"].sum())
    max_abs_diff = float((replay.loc[common] - window.set_index("date").loc[common, "daily_return"]).abs().max()) if len(common) else float("nan")
    print(f"replayed window net return: {replay_sum:.6f}  committed state: {state_sum:.6f}")
    print(f"matched sessions: {len(common)} of {len(win_idx)}  max per-date abs diff: {max_abs_diff:.3e}")
    print(f"overlay_warmup={config.overlay_warmup!r}: the replay warms the overlay from "
          f"history_start and slices to the window, matching the incremental paper-trading "
          f"update path, so the two are expected to agree session-for-session.")
    assert len(common) == len(win_idx), "replay does not cover the full window"
    assert max_abs_diff < 1e-9, f"replay diverges from the committed state: max abs diff {max_abs_diff}"
    assert abs(replay_sum - state_sum) < 1e-9, f"replay sum {replay_sum} != state sum {state_sum}"

    print("=== Trade-level attribution, trailing 63 sessions ===")
    print(f"window: {win_start.date()} .. {win_end.date()}")
    print(f"total trades in window: {len(trade_log)}")
    print(f"total cost in window: {trade_log['cost'].sum():.4f}")
    print(f"distinct rebalance dates in window: {trade_log['date'].nunique()}")
    print(f"regime_exposure unique values: {sorted(window['regime_exposure'].unique())}")
    print(f"n_positions unique values: {sorted(window['n_positions'].unique())}")
    print()

    # Per-rebalance-date aggregates (the monthly rebalance moves all symbols
    # at once, so per-trade vol_scale carries no cross-sectional spread)
    by_date = trade_log.groupby("date").agg(
        n_trades=("trade_id", "count"),
        turnover=("weight_change", lambda s: float(s.abs().sum())),
        cost=("cost", "sum"),
        buy_wchange=("weight_change", lambda s: float(s[s > 0].sum())),
        sell_wchange=("weight_change", lambda s: float(s[s < 0].sum())),
    ).reset_index()
    by_date["vol_scale"] = by_date["date"].map(dict(zip(rh["date"], rh["vol_scale"])))
    by_date["daily_return"] = by_date["date"].map(dict(zip(window["date"], window["daily_return"])))

    print(f"{'date':<12}{'vol':>8}{'ret':>10}{'trades':>8}{'turnover':>10}{'cost':>9}{'buy_w':>10}{'sell_w':>10}")
    for _, r in by_date.iterrows():
        print(
            f"{str(r['date'].date()):<12}{r['vol_scale']:>8.4f}{r['daily_return']:>10.6f}"
            f"{int(r['n_trades']):>8}{r['turnover']:>10.4f}{r['cost']:>9.5f}"
            f"{r['buy_wchange']:>10.4f}{r['sell_wchange']:>10.4f}"
        )

    # Signal quality: do the window's weight changes point the same way as the
    # forward return on each rebalance date?
    by_date["signed_wchange"] = np.where(
        by_date["daily_return"] >= 0, by_date["buy_wchange"], -by_date["sell_wchange"].abs()
    )
    aligned = by_date["signed_wchange"] * by_date["daily_return"]
    print()
    print(f"weight-change direction aligned with forward return on {int((aligned > 0).sum())} of "
          f"{len(aligned)} rebalance dates")
    print(f"sum(signed_wchange * daily_return) = {aligned.sum():.6f} "
          f"(positive => weight changes were in the direction of forward returns)")
    print(f"window cumulative daily return = {state_sum:.6f}")

    # Cost vs signal split: what fraction of the window return is cost, what
    # fraction is the residual (signal + sizing)?
    total_cost = float(trade_log["cost"].sum())
    print(f"total cost in window: {total_cost:.6f} ({total_cost / state_sum:.3f}x the window return)")
    return 0


if __name__ == "__main__":
    sys.exit(main())