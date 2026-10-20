#!/usr/bin/env python3
"""Read-only refresh of the rolling 63d Sharpe and max-drawdown gate evidence.

Cycle 866 task: refresh the rolling 63d Sharpe and the max-DD evidence from
the committed record and quantify the gap to the promotion thresholds.

The script answers four questions, all from the committed record only
(``data/processed/paper_trading_state.yaml``) and the committed gate table
(``config/promotion_gates.yaml``):

1. What is the current value of every gate that the record is measured
   against, and does an independent recomputation reproduce the production
   values bit-for-bit?
2. How often did the rolling 63d Sharpe gate pass *on the record itself* --
   i.e. what is the empirical base rate of the gate, where does the current
   value sit in that distribution, and how long is the current failing run
   compared with the historical runs?
3. What is the evidence on the two drawdown gates (full-period max DD and
   rolling 63d max DD), including the worst value the record has ever
   produced and the headroom to the -15% threshold?
4. What is the exact gap to each promotion threshold, expressed in the units
   of the gate, and what would have to be true for the gate to clear it?

Everything is deterministic and read-only: the script opens the state file
and the raw cache for reading only, and re-hashes them at the end to prove
that nothing changed.

Usage::

    python research/rolling_63d_gate_refresh.py
"""

from __future__ import annotations

import hashlib
import math
import sys
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluation.sharpe import sharpe_ratio  # noqa: E402
from src.simulation.evaluation import GoNoGoConfig, evaluate_go_no_go  # noqa: E402
from src.simulation.paper_trading import (  # noqa: E402
    PaperTradingConfig,
    PaperTradingState,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = REPO_ROOT / "data" / "processed" / "paper_trading_state.yaml"
CONFIG_PATH = REPO_ROOT / "config" / "paper_trading_config.yaml"
GATES_PATH = REPO_ROOT / "config" / "promotion_gates.yaml"
RAW_DIR = REPO_ROOT / "data" / "raw"

WINDOW = 63
ANNUAL = 252
# The documented canonical full-period Sharpe of the committed record
# (acceptance criterion of Cycle 866) and the length of the reference sample
# it was computed on.
#
# The reference is asserted on the *reference sample* -- the first
# REFERENCE_SESSIONS sessions of the committed record -- and not on the whole
# record, so that an append-only extension of the record (which necessarily
# moves the full-period Sharpe) cannot invalidate the check, while any rewrite
# of the record's history still fails it.  The published Sharpe of the current
# record is checked against an independent re-derivation of the canonical
# formula and against the production gate value instead of against a frozen
# constant.
REFERENCE_SESSIONS = 449
CANONICAL_FULL_SHARPE_REFERENCE = 1.748401
# The recorded backtest baseline Sharpe, the PSR reference (see
# config/promotion_gates.yaml -> sharpe_convention.backtest_baseline_scale).
BACKTEST_BASELINE_SHARPE = 1.4178
# One-sided normal quantile for a 95% probability.
Z_95 = 1.6448536269514722


# ----------------------------------------------------------------------
# read-only helpers
# ----------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fingerprint() -> dict[str, str]:
    """SHA-256 of the state file and of every raw cache file."""
    out: dict[str, str] = {}
    for path in [STATE_PATH, *sorted(RAW_DIR.glob("*.parquet"))]:
        out[str(path.relative_to(REPO_ROOT))] = sha256_file(path)
    return out


def load_state() -> dict:
    with open(STATE_PATH) as fh:
        return yaml.safe_load(fh) or {}


def load_gate_table() -> dict:
    with open(GATES_PATH) as fh:
        return yaml.safe_load(fh) or {}


# ----------------------------------------------------------------------
# estimators (identical formulas to the production code)
# ----------------------------------------------------------------------
def window_max_drawdown(window: np.ndarray) -> float:
    """Peak-to-trough drawdown of a compounded window.

    Same formula as ``src.simulation.evaluation._compute_rolling_metrics``:
    the peak is the running maximum of the compounded window, so the drawdown
    is measured inside the window only.
    """
    cum = np.cumprod(1.0 + window)
    peak = np.maximum.accumulate(cum)
    return float((cum / peak - 1.0).min())


def full_max_drawdown(returns: np.ndarray) -> float:
    """Peak-to-trough drawdown over the whole record.

    Same formula as ``src.evaluation.utils.max_drawdown``.
    """
    cum = np.cumprod(1.0 + returns)
    running_max = np.maximum.accumulate(cum)
    return float(((cum / running_max) - 1.0).min())


def failing_runs(passes: np.ndarray) -> list[int]:
    """Lengths of the runs of consecutive failing windows."""
    runs: list[int] = []
    current = 0
    for ok in passes:
        if not ok:
            current += 1
        else:
            if current:
                runs.append(current)
            current = 0
    if current:
        runs.append(current)
    return runs


def recovery_lags(passes: np.ndarray) -> list[int]:
    """For every failing window, the number of windows until the next pass."""
    lags: list[int] = []
    n = len(passes)
    for i in range(n):
        if passes[i]:
            continue
        j = i
        while j < n and not passes[j]:
            j += 1
        if j < n:
            lags.append(j - i)
    return lags


# ----------------------------------------------------------------------
# main
# ----------------------------------------------------------------------
def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, bool(ok), detail))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))

    print("=== Rolling 63d gate evidence refresh (read-only, Cycle 866) ===")
    hashes_before = fingerprint()
    print(f"state file                 : {STATE_PATH.relative_to(REPO_ROOT)}")
    print(f"raw cache files fingerprinted: {len(hashes_before) - 1}")

    state = load_state()
    gates_table = load_gate_table()
    returns = np.asarray(state["cumulative_returns"], dtype=float)
    dates = [str(d) for d in state["cumulative_dates"]]
    n = len(returns)

    config = PaperTradingConfig.from_paper_config_yaml(CONFIG_PATH)
    go_no_go_config = GoNoGoConfig(
        min_days=config.go_no_go_min_days,
        target_sharpe=config.go_no_go_target_sharpe,
        max_dd_threshold=config.go_no_go_max_dd_threshold,
    )
    result = evaluate_go_no_go(
        PaperTradingState.from_yaml(STATE_PATH), config, go_no_go_config=go_no_go_config
    )
    production_gates = {g.name: g for g in result.gates}
    thresholds = {g["name"]: g for g in gates_table["gates"]}

    # ------------------------------------------------------------------
    print(f"\n--- 1. committed record and canonical Sharpe re-derivation ---")
    print(f"sessions                    : {n}")
    print(f"first / last session        : {dates[0]} -> {dates[-1]}")
    print(f"state last_run_date         : {state.get('last_run_date')}")
    print(f"sharpe convention           : {result.sharpe_convention}")

    canonical_full = sharpe_ratio(returns)
    print(f"canonical full-period Sharpe: {canonical_full:.6f}")
    # independent re-derivation of the published number from the committed
    # record, with the canonical formula written out (the production estimator
    # is imported, so this is a second, independent computation path)
    finite = returns[np.isfinite(returns)]
    indep_canonical = (
        float(np.mean(finite)) * ANNUAL
        / (float(np.std(finite, ddof=1)) * math.sqrt(ANNUAL))
    )
    check(
        "canonical full-period Sharpe re-derived independently from the committed record",
        abs(canonical_full - indep_canonical) < 1e-12,
        f"{canonical_full:.12f} vs {indep_canonical:.12f}",
    )
    check(
        "full-period Sharpe gate value == re-derived canonical Sharpe",
        abs(production_gates["full_period_sharpe"].value - canonical_full) < 1e-12,
        f"gate {production_gates['full_period_sharpe'].value:.12f}",
    )
    if n >= REFERENCE_SESSIONS:
        reference_sharpe = sharpe_ratio(returns[:REFERENCE_SESSIONS])
        check(
            f"canonical Sharpe of the {REFERENCE_SESSIONS}-session reference sample "
            f"== {CANONICAL_FULL_SHARPE_REFERENCE}",
            abs(reference_sharpe - CANONICAL_FULL_SHARPE_REFERENCE) < 5e-7,
            f"{reference_sharpe:.6f} vs {CANONICAL_FULL_SHARPE_REFERENCE} "
            f"(record: {n} sessions through {dates[-1]})",
        )
    else:
        check(
            f"record has at least the {REFERENCE_SESSIONS}-session reference sample",
            False,
            f"record has only {n} sessions",
        )

    # ------------------------------------------------------------------
    print(f"\n--- 2. production gate table (config/promotion_gates.yaml) ---")
    for gate in result.gates:
        print(
            f"  {gate.name:22s} value={gate.value:>12.6f} "
            f"threshold={gate.threshold:>8.3f} {gate.pass_fail}"
        )
    print(f"  decision: {result.decision}  failed_gates: {result.failed_gates}")

    # independent recomputation of the numeric gates
    trailing = returns[-WINDOW:] if n >= WINDOW else returns
    indep = {
        "full_period_sharpe": canonical_full,
        "rolling_63d_sharpe": sharpe_ratio(trailing),
        "max_drawdown": full_max_drawdown(returns),
        "rolling_63d_max_dd": window_max_drawdown(trailing),
    }
    print(f"\n--- 3. independent recomputation vs production gate values ---")
    for name, value in indep.items():
        prod = production_gates[name].value
        print(f"  {name:22s} independent {value:>12.6f}   production {prod:>12.6f}   diff {value - prod:+.3e}")
        check(
            f"{name} recomputation matches production",
            abs(value - prod) < 1e-12,
            f"diff {value - prod:+.3e}",
        )
    stored_flag = (state.get("drift_flags") or {}).get("low_rolling_sharpe", {}).get("value")
    check(
        "stored low_rolling_sharpe drift flag == recomputed rolling 63d Sharpe",
        stored_flag is not None and abs(float(stored_flag) - indep["rolling_63d_sharpe"]) < 1e-12,
        f"stored {stored_flag}",
    )

    # ------------------------------------------------------------------
    print(f"\n--- 4. rolling 63d Sharpe: empirical base rate on the record ---")
    roll_sharpe = np.array(
        [sharpe_ratio(returns[i - WINDOW + 1: i + 1]) for i in range(WINDOW - 1, n)]
    )
    roll_dd = np.array(
        [window_max_drawdown(returns[i - WINDOW + 1: i + 1]) for i in range(WINDOW - 1, n)]
    )
    window_ends = [dates[i] for i in range(WINDOW - 1, n)]
    target = thresholds["rolling_63d_sharpe"]["threshold"]
    passes = roll_sharpe >= target
    n_windows = len(roll_sharpe)
    n_pass = int(passes.sum())
    print(f"rolling windows on the record      : {n_windows}")
    print(f"gate threshold                     : {target}")
    print(f"windows passing the gate           : {n_pass} ({n_pass / n_windows:.4%})")
    print(f"windows failing the gate           : {n_windows - n_pass} ({1 - n_pass / n_windows:.4%})")
    print(f"rolling Sharpe min / median / max  : {roll_sharpe.min():.6f} / {np.median(roll_sharpe):.6f} / {roll_sharpe.max():.6f}")
    for pct in (5, 10, 25, 50, 75, 90, 95):
        print(f"  p{pct:<3d}                          : {np.percentile(roll_sharpe, pct):.6f}")
    current = roll_sharpe[-1]
    rank = float((roll_sharpe <= current).mean())
    print(f"current rolling 63d Sharpe         : {current:.6f} (window {dates[n - WINDOW]} -> {dates[-1]})")
    print(f"percentile rank of the current value: {rank:.4%} of the {n_windows} windows on the record")
    runs = failing_runs(passes)
    current_run = runs[-1] if runs else 0
    print(f"historical failing runs (lengths)  : {sorted(runs, reverse=True)}")
    print(f"current failing run                 : {current_run} windows "
          f"(since {window_ends[-current_run] if current_run else 'n/a'})")
    last_pass_idx = int(np.max(np.where(passes)[0])) if passes.any() else -1
    print(f"last passing window ended           : {window_ends[last_pass_idx]} "
          f"({n_windows - 1 - last_pass_idx} windows ago)")
    lags = recovery_lags(passes)
    print(f"recovery lag (failing window -> next pass): median {np.median(lags):.1f}, "
          f"mean {np.mean(lags):.2f}, p90 {np.percentile(lags, 90):.1f}, max {max(lags)}")

    # ------------------------------------------------------------------
    print(f"\n--- 5. max drawdown evidence ---")
    dd_threshold = thresholds["max_drawdown"]["threshold"]
    roll_dd_threshold = thresholds["rolling_63d_max_dd"]["threshold"]
    print(f"full-period max DD (gate)           : {indep['max_drawdown']:.6f} "
          f"(threshold {dd_threshold}, headroom {indep['max_drawdown'] - dd_threshold:+.6f})")
    print(f"rolling 63d max DD (gate, current)  : {indep['rolling_63d_max_dd']:.6f} "
          f"(threshold {roll_dd_threshold}, headroom {indep['rolling_63d_max_dd'] - roll_dd_threshold:+.6f})")
    print(f"worst rolling 63d max DD on record  : {roll_dd.min():.6f}")
    print(f"rolling windows breaching -15%      : {int((roll_dd <= roll_dd_threshold).sum())} of {n_windows}")
    print(f"worst single session on record      : {returns.min():.6%} "
          f"({dates[int(np.argmin(returns))]})")
    print(f"best single session on record       : {returns.max():.6%} "
          f"({dates[int(np.argmax(returns))]})")
    peak_nav = float(state["peak_nav"])
    current_nav = float(state["current_nav"])
    current_dd = current_nav / peak_nav - 1.0
    breach_nav = (1.0 + dd_threshold) * peak_nav
    sessions_to_breach = 0
    nav_ratio = current_nav / peak_nav
    while nav_ratio > (1.0 + dd_threshold):
        nav_ratio *= 1.0 + float(returns.min())
        sessions_to_breach += 1
        if sessions_to_breach > 1000:
            break
    print(f"running-peak NAV {peak_nav:.2f}, current NAV {current_nav:.2f}, "
          f"current drawdown {current_dd:+.6%}")
    print(f"NAV that would breach the -15% gate : {breach_nav:.2f} "
          f"({breach_nav / current_nav - 1.0:+.6%} from the current NAV)")
    print(f"consecutive worst-recorded sessions to breach the gate: {sessions_to_breach}")

    # ------------------------------------------------------------------
    print(f"\n--- 6. gap to each promotion threshold ---")
    mean_window = float(trailing.mean())
    std_window = float(trailing.std(ddof=1))
    required_mean = target * std_window / math.sqrt(ANNUAL)
    print(f"rolling 63d Sharpe gate: {current:.6f} vs {target} -> gap {target - current:+.6f} Sharpe units")
    print(f"  window mean {mean_window:+.6%}/session, dispersion {std_window:.6%}/session "
          f"({std_window * math.sqrt(ANNUAL):.4%} annualised)")
    print(f"  mean required for Sharpe {target} at the same dispersion: {required_mean:+.6%}/session "
          f"({required_mean * 1e4:+.4f} bp/day)")
    print(f"  mean shortfall: {(required_mean - mean_window) * 1e4:+.4f} bp/day "
          f"({(required_mean - mean_window) * ANNUAL * 100:+.4f} pp annualised)")
    print(f"  window cumulative net return: {trailing.sum():+.6%}; required "
          f"{required_mean * WINDOW:+.6%}; gap {(required_mean * WINDOW - trailing.sum()) * 100:+.4f} pp")
    # dispersion that would be needed at the observed mean (only if mean > 0)
    if mean_window > 0:
        required_std = mean_window * math.sqrt(ANNUAL) / target
        print(f"  dispersion that would be needed at the observed mean: {required_std:.6%} "
              f"(observed {std_window:.6%})")
    else:
        print("  dispersion cannot rescue the gate: the window mean is negative, so no "
              "dispersion makes the Sharpe reach the threshold")

    # counterfactual: how many of the worst sessions in the window would have
    # to be replaced for the gate to clear.  Two variants, both bounded by
    # committed data only.
    worst_replaced = np.sort(trailing)
    record_mean = float(returns.mean())
    record_best = np.sort(returns)[-WINDOW:]
    k_best = None
    k_avg = None
    for k in range(0, WINDOW + 1):
        cand = np.concatenate([worst_replaced[k:], record_best[:k]]) if k else worst_replaced
        if k_best is None and sharpe_ratio(cand) >= target:
            k_best = k
        cand_avg = np.concatenate([worst_replaced[k:], np.full(k, record_mean)]) if k else worst_replaced
        if k_avg is None and sharpe_ratio(cand_avg) >= target:
            k_avg = k
            break
    print(f"  counterfactual bound: replacing the {k_best} worst window sessions with the "
          f"{k_best} best sessions of the record gives Sharpe {sharpe_ratio(np.concatenate([worst_replaced[k_best:], record_best[:k_best]])):.6f}")
    print(f"  counterfactual bound: replacing the {k_avg} worst window sessions with "
          f"record-average sessions ({record_mean:+.6%}) gives Sharpe "
          f"{sharpe_ratio(np.concatenate([worst_replaced[k_avg:], np.full(k_avg, record_mean)])):.6f}")
    print("  (bounds only: they describe the composition of the window, not future returns)")

    print(f"\n  full-period max DD gate: {indep['max_drawdown']:.6f} vs {dd_threshold} -> "
          f"headroom {indep['max_drawdown'] - dd_threshold:+.6f} "
          f"({(dd_threshold - indep['max_drawdown']) * 100:.4f} pp of drawdown left)")
    print(f"  rolling 63d max DD gate: {indep['rolling_63d_max_dd']:.6f} vs {roll_dd_threshold} -> "
          f"headroom {indep['rolling_63d_max_dd'] - roll_dd_threshold:+.6f} "
          f"({(roll_dd_threshold - indep['rolling_63d_max_dd']) * 100:.4f} pp); "
          f"worst window on record {roll_dd.min():.6f}, {int((roll_dd <= roll_dd_threshold).sum())} breaches")

    # PSR interaction: the decision that would remain if the rolling gate cleared
    z95 = Z_95
    required_observed = BACKTEST_BASELINE_SHARPE
    required_observed_sharpe = required_observed + z95 * result.sharpe_se
    print(f"\n  PSR gate (for the decision interaction): psr {result.psr_normal:.6f} vs "
          f"{thresholds['psr']['threshold']}, se {result.sharpe_se:.6f}; an observed Sharpe of "
          f"{required_observed_sharpe:.6f} would be needed at the current SE")
    failing_now = set(result.failed_gates)
    hypothetical = sorted((failing_now - {"rolling_63d_sharpe"}))
    print(f"  if the rolling 63d Sharpe gate alone were met, the remaining failing gates would be "
          f"{hypothetical or ['<none>']} -> decision INCONCLUSIVE (grey-zone PSR only), not GO")

    # Counterfactual: the record truncated at the end of the last passing
    # rolling window (the 444-session record of 2026-10-09) is evaluated with
    # the production code, so the "rolling gate alone" statement above is a
    # computed gate table and not an inference from the decision mapping.
    paper_state = PaperTradingState.from_yaml(STATE_PATH)
    n_trunc = last_pass_idx + WINDOW
    paper_state.cumulative_returns = list(state["cumulative_returns"])[:n_trunc]
    paper_state.cumulative_dates = list(state["cumulative_dates"])[:n_trunc]
    paper_state.cumulative_pnl = list(state.get("cumulative_pnl") or [])[:n_trunc]
    paper_state.run_history = list(state.get("run_history") or [])[:n_trunc]
    trunc_result = evaluate_go_no_go(
        paper_state, config, go_no_go_config=go_no_go_config
    )
    print(f"\n  counterfactual: the record truncated at the last passing rolling window "
          f"({n_trunc} sessions, through {dates[n_trunc - 1]}) evaluated with the production code:")
    for gate in trunc_result.gates:
        print(
            f"    {gate.name:22s} value={gate.value:>12.6f} "
            f"threshold={gate.threshold:>8.3f} {gate.pass_fail}"
        )
    print(f"    decision: {trunc_result.decision}  failed_gates: {trunc_result.failed_gates}")
    check(
        f"counterfactual without the {current_run} failing windows: rolling gate passes, "
        "decision INCONCLUSIVE",
        trunc_result.failed_gates == ["psr"] and trunc_result.decision == "INCONCLUSIVE",
        f"failed_gates={trunc_result.failed_gates}, decision={trunc_result.decision}",
    )

    # ------------------------------------------------------------------
    print(f"\n--- 7. read-only proof ---")
    hashes_after = fingerprint()
    changed = [k for k, v in hashes_before.items() if hashes_after.get(k) != v]
    check("state file and raw cache byte-identical before/after", not changed, f"changed: {changed}")
    check("no failing gate is reported as passing", "rolling_63d_sharpe" in result.failed_gates
          and "psr" in result.failed_gates, f"failed_gates={result.failed_gates}")
    check("decision is NO-GO on the committed record", result.decision == "NO-GO", result.decision)

    failed = [c for c in checks if not c[1]]
    print(f"\nchecks passed: {len(checks) - len(failed)}/{len(checks)}")
    if failed:
        for name, _, detail in failed:
            print(f"  FAILED: {name} {detail}")
        print("OVERALL: FAIL")
        return 1
    print("OVERALL: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
