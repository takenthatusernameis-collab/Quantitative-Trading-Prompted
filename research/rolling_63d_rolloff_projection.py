#!/usr/bin/env python3
"""Read-only projection of rolling 63d Sharpe as window rolls forward.

From Cycle 863 objective: project canonical rolling 63d Sharpe for next 63 sessions
under (a) flat: 0.00% net of cost each session; (b) record-average: committed record
mean daily net return each session. For every projected window report: window mean,
window dispersion (std, ddof=1), canonical Sharpe, gate verdict (>= 0.9), and mean
daily net return required for that window to reach Sharpe 0.9 at its own dispersion.

The projection is read-only and uses only the committed record in
data/processed/paper_trading_state.yaml.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import NamedTuple

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluation.sharpe import sharpe_ratio

STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "paper_trading_state.yaml"
WINDOW = 63
ANNUAL = 252
TARGET_SHARPE = 0.9


class WindowStats(NamedTuple):
    start_idx: int  # index in extended series (0-based relative to original start)
    end_idx: int
    start_date: str | None
    end_date: str | None
    mean_daily: float
    std_daily: float
    sharpe_canonical: float
    passes_gate: bool
    mean_required: float  # mean daily needed for Sharpe >= TARGET_SHARPE at this std


def load_committed_rets() -> tuple[np.ndarray, list[str]]:
    with open(STATE_PATH) as f:
        state = yaml.safe_load(f)
    rets = np.array(state.get("cumulative_returns", []), dtype=float)
    # Try to reconstruct dates if available
    dates: list[str] = []
    # cumulative_returns don't store dates; but we can infer from last_run_date and count
    last_run = state.get("last_run_date")
    if last_run:
        # rough: dates are business days ending at last_run going back n-1 days?
        # But we don't have exact calendar; use string markers for reporting
        # We'll construct approximate date strings by index offset conceptually
        pass
    return rets, dates


def required_mean_to_reach_sharpe(target_sharpe: float, std_window: float) -> float:
    if std_window <= 0 or not np.isfinite(std_window):
        return float("inf")
    # canonical: sharpe = mean * sqrt(ANNUAL) / std (ddof=1), with rf=0
    return target_sharpe * std_window / np.sqrt(ANNUAL)


def compute_window(rets_window: np.ndarray) -> WindowStats:
    if len(rets_window) < WINDOW:
        # pad not expected
        pass
    rw = rets_window[-WINDOW:] if len(rets_window) >= WINDOW else rets_window
    mean_daily = float(rw.mean()) if len(rw) > 0 else 0.0
    std_daily = float(rw.std(ddof=1)) if len(rw) > 1 else 0.0
    sharpe_canonical = sharpe_ratio(rw) if len(rw) > 0 else 0.0
    mean_required = required_mean_to_reach_sharpe(TARGET_SHARPE, std_daily)
    passes_gate = sharpe_canonical >= TARGET_SHARPE
    return WindowStats(
        start_idx=-1,
        end_idx=-1,
        start_date=None,
        end_date=None,
        mean_daily=mean_daily,
        std_daily=std_daily,
        sharpe_canonical=sharpe_canonical,
        passes_gate=passes_gate,
        mean_required=mean_required,
    )


def project_path(rets_base: np.ndarray, future_mean: float, horizon: int) -> list[WindowStats]:
    # Extend series
    extended = list(rets_base)
    results: list[WindowStats] = []
    for i in range(horizon):
        # append next session with future_mean
        extended.append(float(future_mean))
        # compute rolling 63 on last 63 of extended
        window_rets = np.array(extended[-WINDOW:])
        mean_daily = float(window_rets.mean())
        std_daily = float(window_rets.std(ddof=1)) if len(window_rets) > 1 else 0.0
        sharpe_canonical = sharpe_ratio(window_rets)
        mean_required = required_mean_to_reach_sharpe(TARGET_SHARPE, std_daily)
        passes_gate = sharpe_canonical >= TARGET_SHARPE
        # track indices (relative to original)
        start_idx = len(extended) - WINDOW  # index in extended
        end_idx = len(extended) - 1
        results.append(
            WindowStats(
                start_idx=start_idx,
                end_idx=end_idx,
                start_date=None,
                end_date=None,
                mean_daily=mean_daily,
                std_daily=std_daily,
                sharpe_canonical=sharpe_canonical,
                passes_gate=passes_gate,
                mean_required=mean_required,
            )
        )
    return results

def main():
    rets, dates = load_committed_rets()
    n = len(rets)
    mean_rec = float(rets.mean()) if n > 0 else 0.0

    print("=== Read-only rolling 63d roll-off projection ===")
    print(f"Committed record: {n} sessions")
    print(f"Record mean daily net return: {mean_rec:.8f} ({mean_rec * 252:.6f} annualized)")
    print(f"Canonical trailing 63d Sharpe (last window): {sharpe_ratio(rets[-WINDOW:]) if n >= WINDOW else float('nan'):.6f}")
    print()

    # Show current window composition info
    if n >= WINDOW:
        last_window = rets[-WINDOW:]
        print(f"Last window (sessions {n - WINDOW}..{n - 1}, 63 sessions total):")
        print(f"  mean={last_window.mean():.6f}, std={last_window.std(ddof=1):.6f}, sharpe={sharpe_ratio(last_window):.6f}")
        print()

    # Projection (a): flat 0.00%
    print("--- Assumption (a): FLAT --- every future session earns exactly 0.00% net of cost")
    flat_path = project_path(rets, future_mean=0.0, horizon=WINDOW)
    first_reach_flat = None
    for i, ws in enumerate(flat_path):
        if ws.passes_gate and first_reach_flat is None:
            first_reach_flat = i + 1  # session number in horizon
        if i < 10 or i % 10 == 9 or i == len(flat_path) - 1:
            # print summary lines
            pass  # we'll format nicely
    # print key points
    for i, ws in enumerate(flat_path):
        if i == 0 or i == 9 or i == 19 or i == 29 or i == 39 or i == 49 or i == 59 or i == len(flat_path) - 1:
            print(f"  +{i+1:2d} sess (end idx {ws.end_idx}): mean={ws.mean_daily:.6f}, std={ws.std_daily:.6f}, sharpe={ws.sharpe_canonical:.6f}, gate>={TARGET_SHARPE}? {ws.passes_gate} (req_mean={ws.mean_required:.6f})")
    if first_reach_flat is None:
        print(f"  First time >= {TARGET_SHARPE} under flat: NEVER within {WINDOW} sessions")
    else:
        print(f"  First time >= {TARGET_SHARPE} under flat: at +{first_reach_flat} sessions")
    print()

    # Projection (b): record average
    print(f"--- Assumption (b): RECORD-AVERAGE --- every future session earns {mean_rec:.6f}% net of cost")
    avg_path = project_path(rets, future_mean=mean_rec, horizon=WINDOW)
    first_reach_avg = None
    for i, ws in enumerate(avg_path):
        if ws.passes_gate and first_reach_avg is None:
            first_reach_avg = i + 1
    for i, ws in enumerate(avg_path):
        if i == 0 or i == 9 or i == 19 or i == 29 or i == 39 or i == 49 or i == 59 or i == len(avg_path) - 1:
            print(f"  +{i+1:2d} sess (end idx {ws.end_idx}): mean={ws.mean_daily:.6f}, std={ws.std_daily:.6f}, sharpe={ws.sharpe_canonical:.6f}, gate>={TARGET_SHARPE}? {ws.passes_gate} (req_mean={ws.mean_required:.6f})")
    if first_reach_avg is None:
        print(f"  First time >= {TARGET_SHARPE} under record-average: NEVER within {WINDOW} sessions")
    else:
        print(f"  First time >= {TARGET_SHARPE} under record-average: at +{first_reach_avg} sessions")
    print()

    # PSR note
    print("--- PSR note (from Cycle 862 numbers) ---")
    print("  At current SE 0.690150, observed Sharpe needed for PSR>=0.95: 2.552996")
    print(f"  Current observed Sharpe (full period): {sharpe_ratio(rets):.6f}; gap is numerator-driven")
    print("  Trailing window change was not the cause of PSR shortfall (see attribution)")
    print()
    print("=== End of projection ===")


if __name__ == "__main__":
    main()
