#!/usr/bin/env python3
"""Read-only go/no-go evaluation for the current paper-trading record.

This script regenerates the go/no-go evaluation from the committed
paper-trading state and prints a comprehensive summary. It is designed
to be side-effect free: it does not modify any files under data/ or
research/ (only reads). A separate check (outside this script or by
comparing before/after hashes) confirms byte identity.
"""
from __future__ import annotations

import hashlib
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.simulation.paper_trading import PaperTradingConfig, PaperTradingState
from src.simulation.evaluation import evaluate_go_no_go, GoNoGoConfig
from src.evaluation.utils import annualize_return, max_drawdown, sharpe_ratio


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_sha256_set(paths: Iterable[Path]) -> dict[str, str]:
    res = {}
    for p in sorted(paths):
        try:
            res[str(p)] = sha256_file(p)
        except FileNotFoundError:
            res[str(p)] = "<missing>"
    return res


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    state_path = repo_root / "data" / "processed" / "paper_trading_state.yaml"
    config_path = repo_root / "config" / "paper_trading_config.yaml"
    raw_dir = repo_root / "data" / "raw"

    # Capture hashes before (read-only)
    paths_before = []
    paths_before.append(state_path)
    if raw_dir.exists():
        for p in raw_dir.rglob("*.parquet"):
            paths_before.append(p)
    for p in raw_dir.glob("*.parquet"):
        if p not in paths_before:
            paths_before.append(p)
    hashes_before = compute_sha256_set(paths_before)

    # Load state and evaluate
    state = PaperTradingState.from_yaml(state_path)
    config = PaperTradingConfig.from_paper_config_yaml(config_path)
    go_no_go_config = GoNoGoConfig(
        min_days=config.go_no_go_min_days,
        target_sharpe=config.go_no_go_target_sharpe,
        max_dd_threshold=config.go_no_go_max_dd_threshold,
    )
    result = evaluate_go_no_go(state, config, go_no_go_config=go_no_go_config)

    # Reproducibility self-check: the PSR bootstrap is seeded, so two
    # evaluations of the same state must agree exactly.
    repeat = evaluate_go_no_go(state, config, go_no_go_config=go_no_go_config)
    deterministic = (
        repeat.decision == result.decision
        and repeat.psr_normal == result.psr_normal
        and repeat.psr_empirical == result.psr_empirical
        and repeat.sharpe_se == result.sharpe_se
        and repeat.sharpe_ci_lower == result.sharpe_ci_lower
        and repeat.sharpe_ci_upper == result.sharpe_ci_upper
    )

    # Compute rolling 63d Sharpe (report-level gate) explicitly
    returns = state.cumulative_returns
    dates = state.cumulative_dates
    window = 63
    rolling_sharpe_63d = 0.0
    if len(returns) >= 2:
        arr = np.array(returns, dtype=float)
        recent = arr[-window:] if len(arr) >= window else arr
        if len(recent) >= 2 and np.std(recent) > 0:
            rolling_sharpe_63d = float(sharpe_ratio(pd.Series(recent)))

    # Output summary
    print("=== Go/No-Go Evaluation (read-only) ===")
    print(f"evaluation_date: {datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print(f"state_last_run_date: {state.last_run_date}")
    print(f"state_path: {state_path}")
    print(f"paper_days: {result.paper_days}")
    print(f"paper_sharpe: {result.paper_sharpe:.6f}")
    print(f"rolling_sharpe_63d (report-level gate): {rolling_sharpe_63d:.6f}")
    print(f"paper_ann_return: {result.paper_ann_return:.6f}")
    print(f"paper_volatility: {result.paper_volatility:.6f}")
    print(f"paper_sortino: {result.paper_sortino:.6f}")
    print(f"paper_profit_factor: {result.paper_profit_factor:.6f}")
    print(f"paper_max_dd: {result.paper_max_dd:.6f}")
    print(f"paper_total_return: {result.paper_total_return:.6f}")
    print(f"paper_trade_count: {result.paper_trade_count}")
    print(f"paper_annualized_turnover: {result.paper_annualized_turnover:.6f}")
    print(f"psr_normal: {result.psr_normal:.6f}")
    print(f"psr_empirical: {result.psr_empirical:.6f}")
    print(f"psr_seed: {go_no_go_config.psr_seed}")
    print(f"evaluation_deterministic: {deterministic}")
    print(f"sharpe_se: {result.sharpe_se:.6f}")
    print(f"sharpe_ci_lower: {result.sharpe_ci_lower:.6f}")
    print(f"sharpe_ci_upper: {result.sharpe_ci_upper:.6f}")
    print(f"regime_stable: {result.regime_stable}")
    print(f"regime_persistence_days: {result.regime_persistence_days}")
    print(f"vol_scale: [{result.vol_scale_min:.3f}, {result.vol_scale_max:.3f}]")
    print(f"dd_scale: [{result.dd_scale_min:.3f}, {result.dd_scale_max:.3f}]")
    print(f"turnover_median: {result.turnover_median:.6f}, p95: {result.turnover_p95:.6f}")
    print(f"drift_flags_count: {result.drift_flags_count}")
    if state.drift_flags:
        for k, v in state.drift_flags.items():
            try:
                print(f"  drift_flag.{k}: value={v.get('value')} threshold={v.get('threshold')} date={v.get('date')}")
            except Exception:
                print(f"  drift_flag.{k}: {v}")
    print(f"decision (evaluate_go_no_go): {result.decision}")
    print(f"rationale: {result.rationale}")
    print(f"conditions_for_reevaluation: {result.conditions_for_reevaluation}")
    print(f"candidate_id: {result.candidate_id}")

    # Verify hashes after (side-effect free)
    hashes_after = compute_sha256_set(paths_before)
    mismatches = []
    for k, v in hashes_before.items():
        if hashes_after.get(k) != v:
            mismatches.append(k)
    print(f"side_effect_free: {len(mismatches) == 0}")
    if mismatches:
        print("MISMATCHED_PATHS:")
        for m in mismatches:
            print(f"  {m}")
        return 1
    if not deterministic:
        print("NON-DETERMINISTIC EVALUATION: repeated evaluation disagrees")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
