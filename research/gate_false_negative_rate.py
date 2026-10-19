#!/usr/bin/env python3
"""Empirical null distribution of the promotion gate's rolling-63-day Sharpe.

Read-only diagnostic (Cycle 879, pre-registered in
``research/hypotheses/promotion_gate_false_negative_001.md``).

The promotion gate in ``config/promotion_gates.yaml`` tests the incumbent's
trailing 63-session Sharpe against 0.9. This script measures the distribution
of that same statistic over the incumbent's own long-sample history, for the
executed path and for the raw-signal path, so that a trailing-window NO-GO
can be read against the statistic's own dispersion instead of against an
assumption.

The script writes exactly one report and one JSON sidecar under
``research/reports/`` and never touches ``data/``, ``config/`` or the
paper-trading state.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import research.long_sample_overlay_attribution as tool
from src.evaluation.drift import rolling_sharpe_series
from src.evaluation.sharpe import sharpe_ratio
from src.simulation.engine import SimulationConfig

CONFIG_CAND = REPO_ROOT / "config" / "simulation_candidate_001.yaml"
CONFIG_GATES = REPO_ROOT / "config" / "promotion_gates.yaml"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
REPORT_PATH = REPORTS_DIR / "gate_false_negative_rate_001.md"
JSON_PATH = REPORTS_DIR / "gate_false_negative_rate_001.json"

WINDOW = 63
GATE_THRESHOLD = 0.9
DRIFT_THRESHOLD = 0.5
INFORMATIVE_FAIL_RATE = 0.10
EXTREME_PERCENTILE = 1.0
TRAILING_GATE_VALUE = -0.21188351222842883
CROSS_CHECK_TOL = 1e-9


def rolling_sharpe_values(returns: np.ndarray, window: int = WINDOW) -> np.ndarray:
    """Rolling-window canonical Sharpe for every complete window."""
    arr = np.asarray(returns, dtype=float)
    cumulative = np.concatenate([[0.0], np.cumsum(arr)])
    squares = np.concatenate([[0.0], np.cumsum(arr * arr)])
    total = cumulative[window:] - cumulative[:-window]
    total_sq = squares[window:] - squares[:-window]
    variance = (total_sq - total * total / window) / (window - 1)
    safe = np.where(variance > 0.0, variance, 1.0)
    sharpe = (total / window) * 252 / (np.sqrt(safe) * np.sqrt(252))
    sharpe = np.where(variance > 0.0, sharpe, 0.0)
    return np.where(np.isfinite(sharpe), sharpe, 0.0)


def zero_dispersion_windows(returns: np.ndarray, window: int = WINDOW) -> int:
    """Number of complete windows whose returns have no dispersion."""
    arr = np.asarray(returns, dtype=float)
    cumulative = np.concatenate([[0.0], np.cumsum(arr)])
    squares = np.concatenate([[0.0], np.cumsum(arr * arr)])
    total = cumulative[window:] - cumulative[:-window]
    total_sq = squares[window:] - squares[:-window]
    variance = (total_sq - total * total / window) / (window - 1)
    return int(np.sum(variance <= 0.0))


def distribution(values: np.ndarray) -> dict:
    arr = np.asarray(values, dtype=float)
    return {
        "count": int(arr.size),
        "mean": float(np.mean(arr)),
        "sd": float(np.std(arr, ddof=1)),
        "min": float(np.min(arr)),
        "p01": float(np.percentile(arr, 1)),
        "p05": float(np.percentile(arr, 5)),
        "p25": float(np.percentile(arr, 25)),
        "median": float(np.median(arr)),
        "p75": float(np.percentile(arr, 75)),
        "p95": float(np.percentile(arr, 95)),
        "p99": float(np.percentile(arr, 99)),
        "max": float(np.max(arr)),
    }


def failure_rate(values: np.ndarray, threshold: float) -> dict:
    """Share of windows strictly below ``threshold`` with a dependence-aware error."""
    arr = np.asarray(values, dtype=float)
    failures = int(np.sum(arr < threshold))
    rate = failures / arr.size if arr.size else float("nan")
    n_eff = arr.size / WINDOW if arr.size else float("nan")
    stderr = float(np.sqrt(rate * (1.0 - rate) / n_eff)) if n_eff > 0 else float("nan")
    return {
        "threshold": threshold,
        "failures": failures,
        "rate": rate,
        "stderr_independent_window_approx": stderr,
        "effective_independent_windows": n_eff,
    }


def percentile_rank(values: np.ndarray, target: float) -> float:
    arr = np.asarray(values, dtype=float)
    return 100.0 * float(np.mean(arr <= target))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-report", action="store_true", help="print the measurement without writing files"
    )
    args = parser.parse_args()

    fingerprint_before = tool.fingerprint(tool.read_only_targets())

    config = SimulationConfig.from_yaml(CONFIG_CAND)
    gates = tool.yaml.safe_load(CONFIG_GATES.read_text()) or {}
    end_date = "2026-10-16"

    print("=== Promotion-gate false-negative rate (read-only) ===")
    print(f"config        : {CONFIG_CAND.name} (candidate {config.candidate_id})")
    print(f"gate table    : {CONFIG_GATES.name}")
    print(f"window        : {WINDOW} sessions")

    sim, layers = tool.long_sample_layers(config, end_date)
    net_paths = tool.layer_net_paths(layers, config)
    index = layers["index"]
    dates = [str(ts.date()) for ts in index]

    paths = {
        "executed": net_paths["combined"],
        "raw_signal": net_paths["base"],
    }

    print("\n--- 1. Rolling-63 canonical Sharpe distribution ---")
    results: dict[str, dict] = {}
    for label, path in paths.items():
        returns = path.to_numpy(dtype=float)
        drift_series = rolling_sharpe_series(dates, list(returns), window=WINDOW)
        drift_values = np.array(
            [v for _, v in drift_series if v is not None], dtype=float
        )[-(len(returns) - WINDOW + 1) :]
        values = rolling_sharpe_values(returns)
        mismatch = float(np.max(np.abs(drift_values - values)))
        stats = distribution(values)
        results[label] = {
            "stats": stats,
            "values": values,
            "drift_estimator_mismatch": mismatch,
            "zero_dispersion_windows": zero_dispersion_windows(returns),
            "failure_0_9": failure_rate(values, GATE_THRESHOLD),
            "failure_0_5": failure_rate(values, DRIFT_THRESHOLD),
            "failure_0_0": failure_rate(values, 0.0),
        }
        res = results[label]
        print(f"\n  [{label}] {stats['count']} complete windows")
        print(
            f"    mean {stats['mean']:+.4f}  sd {stats['sd']:.4f}  median {stats['median']:+.4f}  "
            f"min {stats['min']:+.4f}  max {stats['max']:+.4f}"
        )
        print(
            f"    p01 {stats['p01']:+.4f}  p05 {stats['p05']:+.4f}  p25 {stats['p25']:+.4f}  "
            f"p75 {stats['p75']:+.4f}  p95 {stats['p95']:+.4f}  p99 {stats['p99']:+.4f}"
        )
        print(f"    zero-dispersion windows: {res['zero_dispersion_windows']}")
        print(f"    drift-estimator cross-check (max |diff|): {mismatch:.3e}")
        for key, label_text in [
            ("failure_0_9", "fails >= 0.9 gate"),
            ("failure_0_5", "fails 0.5 drift threshold"),
            ("failure_0_0", "negative"),
        ]:
            payload = res[key]
            print(
                f"    {label_text:<26s}: {payload['rate']*100:6.2f}% "
                f"(+/- {payload['stderr_independent_window_approx']*100:.2f} pp, "
                f"n_eff {payload['effective_independent_windows']:.0f})"
            )

    executed = results["executed"]
    raw = results["raw_signal"]
    trailing_value = float(executed["values"][-1])
    trailing_rank = percentile_rank(executed["values"], trailing_value)
    raw_trailing_value = float(raw["values"][-1])

    print("\n--- 2. Current trailing window ---")
    print(f"  executed path trailing value : {trailing_value!r}")
    print(f"  live gate value (committed)  : {TRAILING_GATE_VALUE!r}")
    print(f"  cross-check difference       : {abs(trailing_value - TRAILING_GATE_VALUE):.3e}")
    print(f"  percentile rank              : {trailing_rank:.2f}%")
    print(f"  raw-signal trailing value    : {raw_trailing_value:+.6f}")
    trailing_reproduced = abs(trailing_value - TRAILING_GATE_VALUE) <= 1e-12

    print("\n--- 3. Pre-registered conditions ---")
    g1 = executed["failure_0_9"]["rate"] >= INFORMATIVE_FAIL_RATE
    g2 = trailing_rank < EXTREME_PERCENTILE
    overlay_causes_failures = executed["failure_0_9"]["rate"] > raw["failure_0_9"]["rate"]
    g3 = overlay_causes_failures
    print(f"  G1 gate failure rate >= 10%      : {g1} ({executed['failure_0_9']['rate']*100:.2f}%)")
    print(f"  G2 current window in extreme tail : {g2} (rank {trailing_rank:.2f}%)")
    print(
        f"  G3 overlay causes gate failures   : {g3} "
        f"(raw {raw['failure_0_9']['rate']*100:.2f}% vs executed {executed['failure_0_9']['rate']*100:.2f}%)"
    )
    print(
        "     G3 wording note: the pre-registration's condition sentence and its falsification"
    )
    print(
        "     clause are mutually inconsistent. The measured event is 'the raw-signal path fails"
    )
    print(
        "     in more windows than the executed path', which under the hypothesis's own prior"
    )
    print(
        "     table and falsification clause means the overlay *reduces* gate failures. G3 is"
    )
    print(
        "     therefore reported as the proposition it names: 'the overlay causes gate failures'"
    )
    print("     is FALSE, and the decision rule is applied on that reading.")
    if g1 and not g2 and not g3:
        decision = (
            "The rolling-63-day gate fails on a large fraction of the strategy's own history, "
            "the current window is an ordinary failure rather than an extreme one, and the "
            "overlay does not cause gate failures (it reduces them). A trailing-window NO-GO "
            "is therefore weak evidence about the edge and must be reported together with "
            "this false-negative rate."
        )
    elif g1 and g3:
        decision = (
            "The rolling-63-day gate has a high false-negative rate and the overlay causes "
            "gate failures; the trailing NO-GO is a genuine signal-level problem and must not "
            "be softened by the gate's noisiness."
        )
    elif not g1:
        decision = (
            "The rolling-63-day gate fails rarely on the strategy's own history, so the "
            "current trailing NO-GO is informative evidence and is not softened."
        )
    else:
        decision = (
            "The rolling-63-day gate has a high false-negative rate; the current window is an "
            "extreme drawdown of the statistic, and the overlay's role in gate failures is "
            "mixed. Report the false-negative rate alongside the gate decision."
        )
    print(f"  decision: {decision}")

    fingerprint_after = tool.fingerprint(tool.read_only_targets())
    read_only_ok = fingerprint_before == fingerprint_after
    print(f"\n  read-only (data/, config/, state unchanged): {read_only_ok}")

    overall_pass = (
        trailing_reproduced
        and read_only_ok
        and executed["drift_estimator_mismatch"] <= CROSS_CHECK_TOL
        and raw["drift_estimator_mismatch"] <= CROSS_CHECK_TOL
    )
    print(f"OVERALL: {'PASS' if overall_pass else 'FAIL'}")

    if not args.no_report:
        write_report(
            {
                "config": config,
                "gates": gates,
                "results": results,
                "trailing_value": trailing_value,
                "trailing_rank": trailing_rank,
                "trailing_reproduced": trailing_reproduced,
                "raw_trailing_value": raw_trailing_value,
                "g1": g1,
                "g2": g2,
                "g3": g3,
                "decision": decision,
                "read_only_ok": read_only_ok,
                "overall_pass": overall_pass,
                "sample_start": dates[0],
                "sample_end": dates[-1],
                "n_sessions": len(dates),
            }
        )
        print(f"report written: {REPORT_PATH.relative_to(REPO_ROOT)}")
    return 0 if overall_pass else 1


def write_report(ctx: dict) -> None:
    """Write the deterministic report from the measured numbers."""
    executed = ctx["results"]["executed"]
    raw = ctx["results"]["raw_signal"]
    lines: list[str] = []
    lines.append("# Empirical Null Distribution of the Promotion Gate's Rolling-63-Day Sharpe")
    lines.append("")
    lines.append("Cycle 879 — measurement-only, pre-registered in")
    lines.append("`research/hypotheses/promotion_gate_false_negative_001.md` before execution")
    lines.append("(with a disclosed Cycle 878 feasibility probe; see the hypothesis file).")
    lines.append("No gate, threshold, configuration, state, candidate or deployment decision")
    lines.append("was changed; the incumbent's decision (**NO-GO**) is unchanged.")
    lines.append("")
    lines.append("## 0. Sample and integrity")
    lines.append("")
    lines.append("| Item | Value |")
    lines.append("|---|---|")
    lines.append(f"| Sample | {ctx['sample_start']} .. {ctx['sample_end']} ({ctx['n_sessions']} sessions) |")
    lines.append(f"| Paths | executed (L4) and raw signal (L0), each net of its own 3 bp turnover cost |")
    lines.append(f"| Statistic | rolling-{WINDOW}-session canonical Sharpe (`arithmetic_annualized_rf0`) |")
    lines.append(f"| Estimator | `src/evaluation/drift.py:rolling_sharpe_series` (the live drift-flag estimator) |")
    lines.append(f"| Cross-check vs vectorised recomputation | executed {executed['drift_estimator_mismatch']:.3e}, raw {raw['drift_estimator_mismatch']:.3e} (tol {CROSS_CHECK_TOL:.0e}; the vectorised path accumulates in a different order, so the difference is floating-point noise) |")
    lines.append(f"| Trailing window reproduces the live gate value | {ctx['trailing_reproduced']} (diff {abs(ctx['trailing_value'] - TRAILING_GATE_VALUE):.3e}) |")
    lines.append(f"| Read-only (data/, config/, state) | {ctx['read_only_ok']} |")
    lines.append("")

    lines.append("## 1. Distribution of the gate statistic")
    lines.append("")
    lines.append("| Statistic | Executed path (L4) | Raw signal (L0) |")
    lines.append("|---|---|---|")
    for key, label in [
        ("count", "windows"),
        ("mean", "mean"),
        ("sd", "standard deviation"),
        ("min", "minimum"),
        ("p01", "p01"),
        ("p05", "p05"),
        ("p25", "p25"),
        ("median", "median"),
        ("p75", "p75"),
        ("p95", "p95"),
        ("p99", "p99"),
        ("max", "maximum"),
    ]:
        if key == "count":
            lines.append(
                f"| {label} | {int(executed['stats'][key])} | {int(raw['stats'][key])} |"
            )
            continue
        lines.append(
            f"| {label} | {executed['stats'][key]:.6f} | {raw['stats'][key]:.6f} |"
        )
    lines.append(
        f"| zero-dispersion windows | {executed['zero_dispersion_windows']} | "
        f"{raw['zero_dispersion_windows']} |"
    )
    lines.append("")
    lines.append("### Failure rates")
    lines.append("")
    lines.append(
        "| Threshold | Executed path | Raw signal | Independent-window SE (executed) |"
    )
    lines.append("|---|---|---|---|")
    for key, label in [
        ("failure_0_9", "rolling Sharpe < 0.9 (promotion gate)"),
        ("failure_0_5", "rolling Sharpe < 0.5 (drift threshold)"),
        ("failure_0_0", "rolling Sharpe < 0"),
    ]:
        lines.append(
            f"| {label} | {executed[key]['rate']*100:.2f}% | {raw[key]['rate']*100:.2f}% | "
            f"+/- {executed[key]['stderr_independent_window_approx']*100:.2f} pp |"
        )
    lines.append("")
    lines.append(
        f"**Dependence.** Consecutive windows share up to {WINDOW - 1} of their {WINDOW} sessions, "
        f"so the effective number of independent windows is approximately "
        f"{executed['failure_0_9']['effective_independent_windows']:.0f}, not "
        f"{executed['stats']['count']}. The standard errors above use the independent-window "
        "approximation and are therefore **optimistic**; the failure rates themselves are not "
        "affected."
    )
    lines.append("")
    lines.append(
        f"**Zero-dispersion windows** are scored 0.0 by the repository's canonical convention "
        f"(`src/evaluation/sharpe.py:sharpe_ratio`), which mechanically fails the 0.9 gate. "
        f"There are {executed['zero_dispersion_windows']} such windows on the executed path "
        f"({executed['zero_dispersion_windows'] / executed['stats']['count'] * 100:.2f}% of all "
        f"windows) and {raw['zero_dispersion_windows']} on the raw-signal path. They are the "
        "cash periods created by the SPY-trend filter, and they are part of the strategy's "
        "behaviour, not a modelling artefact of this cycle."
    )
    lines.append("")

    lines.append("## 2. The current trailing window")
    lines.append("")
    lines.append("| Item | Value |")
    lines.append("|---|---|")
    lines.append(f"| Executed path trailing value | {ctx['trailing_value']:+.12f} |")
    lines.append(f"| Live gate value (committed record) | {TRAILING_GATE_VALUE:+.12f} |")
    lines.append(f"| Percentile rank in the distribution | {ctx['trailing_rank']:.2f}% |")
    lines.append(f"| Raw-signal trailing value | {ctx['raw_trailing_value']:+.6f} |")
    lines.append("")

    lines.append("## 3. Pre-registered conditions")
    lines.append("")
    lines.append("| Condition | Statement | Verdict |")
    lines.append("|---|---|---|")
    lines.append(
        f"| G1 | executed path fails the >= 0.9 gate in >= {INFORMATIVE_FAIL_RATE*100:.0f}% of windows | "
        f"**{'PASS' if ctx['g1'] else 'FAIL'}** |"
    )
    lines.append(
        f"| G2 | current trailing value is below the {EXTREME_PERCENTILE:.0f}"
        f"{'st' if int(EXTREME_PERCENTILE) == 1 else 'th'} percentile | "
        f"**{'PASS' if ctx['g2'] else 'FAIL'}** |"
    )
    lines.append(
        f"| G3 | the overlay causes gate failures (executed path fails in more windows than the "
        f"raw-signal path) | **{'PASS' if ctx['g3'] else 'FAIL'}** |"
    )
    lines.append("")
    lines.append(f"- G1 detail: executed failure rate {executed['failure_0_9']['rate']*100:.2f}% "
                 f"(+/- {executed['failure_0_9']['stderr_independent_window_approx']*100:.2f} pp).")
    lines.append(f"- G2 detail: trailing rank {ctx['trailing_rank']:.2f}% of "
                 f"{executed['stats']['count']} windows; the p01 of the distribution is "
                 f"{executed['stats']['p01']:+.6f}.")
    lines.append(f"- G3 detail: raw-signal failure rate {raw['failure_0_9']['rate']*100:.2f}% vs "
                 f"executed {executed['failure_0_9']['rate']*100:.2f}% "
                 f"(difference {abs(raw['failure_0_9']['rate'] - executed['failure_0_9']['rate'])*100:.2f} pp).")
    lines.append("")
    lines.append("### 3.1 Wording defect in the pre-registered G3 (disclosed, not silently fixed)")
    lines.append("")
    lines.append(
        "The G3 condition sentence in the pre-registration (\"the raw-signal path fails the"
    )
    lines.append(
        "gate in materially more windows than the executed path -> the overlay causes gate"
    )
    lines.append(
        "failures\") contradicts its own falsification clause (\"falsified if the executed path"
    )
    lines.append(
        "fails *less* often: the overlay then **helps** the gate\"), which is also what the"
    )
    lines.append(
        "hypothesis's prior table states. The two clauses describe the same event with opposite"
    )
    lines.append(
        "labels. The measured event is that the raw-signal path fails in **more** windows"
    )
    lines.append(
        f"({raw['failure_0_9']['rate']*100:.2f}%) than the executed path"
    )
    lines.append(
        f"({executed['failure_0_9']['rate']*100:.2f}%), i.e. the overlay **reduces** gate"
    )
    lines.append(
        "failures by "
        f"{abs(raw['failure_0_9']['rate'] - executed['failure_0_9']['rate'])*100:.2f} pp. G3 is"
    )
    lines.append(
        "therefore reported as the proposition it names — *the overlay causes gate failures* —"
    )
    lines.append(
        f"which is **{'PASS' if ctx['g3'] else 'FAIL'}** — and the decision rule is applied on"
    )
    lines.append(
        "that reading, which is the reading stated in the hypothesis's prior table and in its"
    )
    lines.append("falsification clause. The wording defect is recorded here rather than repaired")
    lines.append("in the pre-registered file, so the audit trail shows what was actually")
    lines.append("written before execution.")
    lines.append("")
    lines.append(f"**Decision (pre-registered rule):** {ctx['decision']}")
    lines.append("")
    lines.append("## 4. What this measurement does and does not establish")
    lines.append("")
    lines.append("It establishes the sampling distribution of the gate statistic **for this")
    lines.append("strategy on this history**, and therefore the false-negative rate of a")
    lines.append("single trailing-window gate read.")
    lines.append("")
    lines.append("It does not establish that the gate should be changed: the gate table in")
    lines.append("`config/promotion_gates.yaml` is the incumbent's frozen contract, and a")
    lines.append("criterion is not relaxed because it failed. The measured rate is a reason to")
    lines.append("**report the gate's informativeness alongside every gate decision**, not to")
    lines.append("ignore the gate.")
    lines.append("")
    lines.append("## 5. Reproduction")
    lines.append("")
    lines.append("```bash")
    lines.append("python research/gate_false_negative_rate.py")
    lines.append("python research/long_sample_overlay_attribution.py")
    lines.append("python research/go_no_go_evaluation.py")
    lines.append("python -m pytest -q")
    lines.append("git status --porcelain data/ config/")
    lines.append("```")
    lines.append("")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines))

    payload = {
        "sample": {
            "start": ctx["sample_start"],
            "end": ctx["sample_end"],
            "sessions": ctx["n_sessions"],
        },
        "paths": {
            label: {
                "stats": payload["stats"],
                "zero_dispersion_windows": payload["zero_dispersion_windows"],
                "failure_0_9": payload["failure_0_9"],
                "failure_0_5": payload["failure_0_5"],
                "failure_0_0": payload["failure_0_0"],
            }
            for label, payload in {
                "executed": executed,
                "raw_signal": raw,
            }.items()
        },
        "trailing": {
            "executed_value": ctx["trailing_value"],
            "raw_signal_value": ctx["raw_trailing_value"],
            "percentile_rank": ctx["trailing_rank"],
        },
        "conditions": {"g1": ctx["g1"], "g2": ctx["g2"], "g3": ctx["g3"]},
        "decision": ctx["decision"],
    }
    JSON_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    sys.exit(main())
