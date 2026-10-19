#!/usr/bin/env python3
"""Read-only audit of the repository's Sharpe conventions (Cycle 861).

Prints, for the committed paper-trading record and for the 444-session
record that ends 2026-10-09:

* the value of every Sharpe scale in use, so that the numbers quoted in the
  monitoring artifacts can be reproduced from the committed state alone,
* the Probabilistic Sharpe Ratio under a scale-consistent pairing
  (canonical numerator *and* canonical bootstrap) and under the historical,
  mixed pairing, and
* the promotion-gate table and the decision for both records.

The script is read-only: it opens the state file and never writes to it, to
the raw cache or to the network. The promotion evaluation is imported from
the repository, so the gate table it prints is the one that
``config/promotion_gates.yaml`` defines.

Usage::

    python research/sharpe_convention_audit.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from arch.bootstrap import MovingBlockBootstrap
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluation.sharpe import (  # noqa: E402
    SHARPE_CONVENTION_FORMULA,
    SHARPE_CONVENTION_ID,
    backtest_sharpe_ratio,
    sharpe_ratio,
)
from src.simulation.evaluation import GoNoGoConfig, evaluate_go_no_go  # noqa: E402
from src.simulation.paper_trading import (  # noqa: E402
    PaperTradingConfig,
    PaperTradingState,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = REPO_ROOT / "data" / "processed" / "paper_trading_state.yaml"
CONFIG_PATH = REPO_ROOT / "config" / "paper_trading_config.yaml"

BOOTSTRAP_SAMPLES = 1000
BLOCK_SIZE = 22
PSR_SEED = 20240101
BACKTEST_TARGET = 1.4178


def legacy_safe_sharpe(sample: np.ndarray) -> float | None:
    """The pre-Cycle-861 bootstrap estimator (arithmetic, 2% risk-free rate).

    Kept here only to reproduce the historical PSR numbers; the production
    code no longer contains it.
    """
    sample = np.asarray(sample, dtype=float)
    if len(sample) < 2:
        return None
    std = sample.std(ddof=1)
    if std == 0 or np.isnan(std) or std < 1e-12:
        return None
    log_ret = np.log(np.clip(1.0 + sample, 1e-10, None))
    geor_growth = math.exp(log_ret.mean() * 252 / len(sample))
    if not np.isfinite(geor_growth):
        return None
    ann_vol = std * math.sqrt(252)
    if ann_vol < 1e-12:
        return None
    rf_daily = 0.02 / 252.0
    sharpe = float((sample.mean() - rf_daily) * 252 / ann_vol)
    if not np.isfinite(sharpe):
        return None
    return sharpe


def legacy_bootstrap_sharpe(
    returns: np.ndarray,
    n_samples: int = BOOTSTRAP_SAMPLES,
    block_size: int = BLOCK_SIZE,
    seed: int = PSR_SEED,
) -> np.ndarray:
    """The pre-Cycle-861 moving-block bootstrap (same seed, same block size)."""
    arr = np.asarray(returns, dtype=float)
    effective_block = min(block_size, max(1, len(arr) // 10))
    mbb = MovingBlockBootstrap(effective_block, arr, seed=seed)
    results: list[float] = []
    for posdata, _ in mbb.bootstrap(n_samples):
        value = legacy_safe_sharpe(posdata[0])
        if value is not None:
            results.append(value)
    if len(results) < n_samples * 0.5:
        results.extend([legacy_safe_sharpe(arr)] * (n_samples - len(results)))
    return np.array(results)


def legacy_mixed_psr(returns: np.ndarray) -> dict:
    """PSR as computed before Cycle 861: geometric numerator, mixed bootstrap."""
    sharpes = legacy_bootstrap_sharpe(returns)
    se = float(np.std(sharpes, ddof=1))
    ann_return = float((1.0 + returns).prod() ** (252 / len(returns)) - 1.0)
    ann_vol = float(np.std(returns, ddof=1)) * math.sqrt(252)
    sr_obs = (ann_return - 0.02) / ann_vol if ann_vol > 0 else 0.0
    z = (sr_obs - BACKTEST_TARGET) / se if se > 0 else 0.0
    return {
        "sharpe_observed": sr_obs,
        "sharpe_se": se,
        "psr_normal": float(stats.norm.cdf(z)),
        "psr_empirical": float((sharpes > BACKTEST_TARGET).mean()),
    }


def canonical_psr(returns: np.ndarray) -> dict:
    """PSR with the canonical estimator on both sides (Cycle 861)."""
    from src.evaluation.statistics import block_bootstrap_sharpe

    sharpes = block_bootstrap_sharpe(
        pd.Series(returns),
        BOOTSTRAP_SAMPLES,
        BLOCK_SIZE,
        seed=PSR_SEED,
    )
    se = float(np.std(sharpes, ddof=1))
    sr_obs = sharpe_ratio(returns)
    z = (sr_obs - BACKTEST_TARGET) / se if se > 0 else 0.0
    return {
        "sharpe_observed": sr_obs,
        "sharpe_se": se,
        "psr_normal": float(stats.norm.cdf(z)),
        "psr_empirical": float((sharpes > BACKTEST_TARGET).mean()),
        "bootstrap_mean": float(np.mean(sharpes)),
        "ci_lower": float(np.percentile(sharpes, 2.5)),
        "ci_upper": float(np.percentile(sharpes, 97.5)),
    }


def load_state() -> dict:
    with open(STATE_PATH) as fh:
        return yaml.safe_load(fh) or {}


def truncated_state(state: dict, n_sessions: int) -> PaperTradingState:
    paper_state = PaperTradingState.from_yaml(STATE_PATH)
    paper_state.cumulative_returns = list(state["cumulative_returns"])[:n_sessions]
    paper_state.cumulative_dates = list(state["cumulative_dates"])[:n_sessions]
    paper_state.cumulative_pnl = list(state.get("cumulative_pnl") or [])[:n_sessions]
    paper_state.run_history = list(state.get("run_history") or [])[:n_sessions]
    return paper_state


def report_record(
    label: str,
    returns: np.ndarray,
    dates: list[str],
    state: dict,
    is_current: bool = False,
) -> dict:
    print(f"\n=== {label} ({len(returns)} sessions, last {dates[-1]}) ===")

    canonical_full = sharpe_ratio(returns)
    backtest_scale_full = backtest_sharpe_ratio(returns)
    canonical_roll = sharpe_ratio(returns[-63:])
    backtest_scale_roll = backtest_sharpe_ratio(returns[-63:])

    print("Sharpe values by scale")
    print(f"  full period, canonical          : {canonical_full:.6f}")
    print(f"  full period, backtest-baseline  : {backtest_scale_full:.6f}")
    print(f"  trailing 63d, canonical         : {canonical_roll:.6f}")
    print(f"  trailing 63d, backtest-baseline : {backtest_scale_roll:.6f}")
    print(f"  scale offset (canonical - base) : {canonical_full - backtest_scale_full:+.6f}")

    stored = (state.get("drift_flags") or {}).get("low_rolling_sharpe") or {}
    stored_value = stored.get("value")
    if stored_value is not None and is_current:
        print(
            "  stored low_rolling_sharpe flag  : "
            f"{stored_value} (equals canonical trailing 63d: "
            f"{abs(float(stored_value) - canonical_roll) <= 1e-12})"
        )

    canonical = canonical_psr(returns)
    legacy = legacy_mixed_psr(returns)
    print("Probabilistic Sharpe Ratio (target 1.4178)")
    print(
        f"  canonical pairing : psr {canonical['psr_normal']:.6f} "
        f"(observed {canonical['sharpe_observed']:.6f}, se {canonical['sharpe_se']:.6f}, "
        f"empirical {canonical['psr_empirical']:.3f}, "
        f"CI [{canonical['ci_lower']:.6f}, {canonical['ci_upper']:.6f}])"
    )
    print(
        f"  pre-Cycle-861 mix : psr {legacy['psr_normal']:.6f} "
        f"(observed {legacy['sharpe_observed']:.6f}, se {legacy['sharpe_se']:.6f}, "
        f"empirical {legacy['psr_empirical']:.3f})"
    )
    offset = canonical["sharpe_observed"] - legacy["sharpe_observed"]
    scale_consistent_target = BACKTEST_TARGET + offset
    z = (
        (canonical["sharpe_observed"] - scale_consistent_target)
        / canonical["sharpe_se"]
        if canonical["sharpe_se"] > 0
        else 0.0
    )
    print(
        f"  scale-consistent sensitivity: if the target carried the same "
        f"{offset:+.6f} offset -> target {scale_consistent_target:.6f}, "
        f"psr {float(stats.norm.cdf(z)):.6f}"
    )
    return {
        "canonical": canonical,
        "legacy": legacy,
        "canonical_full": canonical_full,
        "canonical_roll": canonical_roll,
        "backtest_scale_roll": backtest_scale_roll,
    }


def report_gates(label: str, paper_state: PaperTradingState, config: PaperTradingConfig) -> None:
    go_no_go_config = GoNoGoConfig(
        min_days=config.go_no_go_min_days,
        target_sharpe=config.go_no_go_target_sharpe,
        max_dd_threshold=config.go_no_go_max_dd_threshold,
    )
    result = evaluate_go_no_go(
        paper_state, config, go_no_go_config=go_no_go_config
    )
    print(f"\n--- promotion gates: {label} ---")
    for gate in result.gates:
        print(
            f"  {gate.name:22s} value={gate.value:>12.6f} "
            f"threshold={gate.threshold:>8.3f} {gate.pass_fail}"
        )
    print(f"  psr_zone={result.psr_zone} failed_gates={result.failed_gates}")
    print(f"  decision: {result.decision}")
    print(f"  sharpe_convention: {result.sharpe_convention}")


def main() -> int:
    state = load_state()
    returns = np.asarray(state["cumulative_returns"], dtype=float)
    dates = [str(d) for d in state["cumulative_dates"]]
    config = PaperTradingConfig.from_paper_config_yaml(CONFIG_PATH)

    print("=== Sharpe convention audit (read-only) ===")
    print(f"canonical convention id : {SHARPE_CONVENTION_ID}")
    print(f"canonical formula       : {SHARPE_CONVENTION_FORMULA}")
    print("backtest-baseline scale : cagr_annualized_rf2 (recorded baseline 1.4178)")
    print(f"state file              : {STATE_PATH}")
    print(f"state last_run_date     : {state.get('last_run_date')}")

    report_record(
        f"committed record through {dates[-1]}",
        returns,
        dates,
        state,
        is_current=True,
    )
    report_gates("committed record", PaperTradingState.from_yaml(STATE_PATH), config)

    # The 444-session record that the validation artifacts describe.
    n_444 = sum(1 for d in dates if d <= "2026-10-09")
    report_record(
        f"444-session record through {dates[n_444 - 1]}",
        returns[:n_444],
        dates[:n_444],
        state,
    )
    report_gates("444-session record", truncated_state(state, n_444), config)

    return 0


if __name__ == "__main__":
    sys.exit(main())
