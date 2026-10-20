#!/usr/bin/env python3
"""Promotion-criteria feasibility test on the frozen candidate's long-sample backtest."""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.backtest.engine import run_backtest
from src.evaluation.sharpe import backtest_sharpe_ratio, sharpe_ratio
from src.evaluation.statistics import compute_psr
from src.evaluation.utils import max_drawdown

CONFIG_CAND = REPO_ROOT / "config" / "simulation_candidate_001.yaml"
CONFIG_GATES = REPO_ROOT / "config" / "promotion_gates.yaml"
RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
PAPER_STATE_PATH = PROCESSED_DIR / "paper_trading_state.yaml"
REPORTS_DIR = REPO_ROOT / "research" / "reports"

PSR_TARGET_BACKTEST_SCALE = 1.4178

# Reference-sample anchors (Cycle 901/902).  They are defined by a *date
# boundary*, not by the length of the current record, so an append-only
# extension of the raw cache or of the paper record cannot invalidate them.
# Every run re-derives them and fails loudly if one of them moved.
REF_INCUMBENT_END = "2026-10-16"
REF_INCUMBENT_SESSIONS = 8487
REF_INCUMBENT_SHARPE = 0.5646255767978904
REF_INCUMBENT_MAX_DD = -0.6224126346564325
REF_INCUMBENT_PSR = 2.2219753177036448e-08
REF_PAPER_SESSIONS = 449
REF_PAPER_SHARPE = 1.748401


@dataclass
class SampleDef:
    label_start_date: str
    label_end_date: str
    realized_start_date: str
    realized_end_date: str
    realized_session_count: int
    start_date: str
    end_date: str
    session_count: int
    universe: list[str]
    lookback: int
    skip: int
    top_fraction: float
    rebalance_freq: str
    cost_model: dict[str, float]
    overlay_warmup: str | None = None
    data_source: str = "committed raw cache (data/raw/*.parquet)"
    sha256_raw_files: dict[str, str] | None = None
    per_symbol_stats: dict[str, Any] | None = None
    union_index_fingerprint: dict[str, Any] | None = None
    cache_fingerprint: dict[str, Any] | None = None
    reference_sample_anchors: dict[str, Any] | None = None
    reference_sample_checks: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def load_yaml(p: Path) -> Any:
    with open(p, "r") as f:
        return yaml.safe_load(f)


def scan_raw_cache(universe: list[str]) -> tuple[dict[str, dict[str, Any]], dict[str, str], pd.DatetimeIndex]:
    """Read every raw parquet once: per-symbol stats, SHA-256 and the union index."""
    per_symbol_stats: dict[str, dict[str, Any]] = {}
    raw_hashes: dict[str, str] = {}
    indexes: list[pd.DatetimeIndex] = []
    for sym in universe:
        path = RAW_DIR / f"{sym}.parquet"
        if not path.exists():
            raise FileNotFoundError(f"missing {path}")
        df = pd.read_parquet(path)
        index = pd.DatetimeIndex(df.index)
        indexes.append(index)
        digest = sha256_file(path)
        raw_hashes[sym] = digest
        per_symbol_stats[sym] = {
            "first_date": index.min().date().isoformat(),
            "last_date": index.max().date().isoformat(),
            "row_count": int(len(index)),
        }
    union_index = pd.DatetimeIndex(sorted(set().union(*indexes)))
    return per_symbol_stats, raw_hashes, union_index


def rolling_window(series: pd.Series, window: int) -> tuple[float, float]:
    if len(series) < window:
        raise RuntimeError(f"Series too short: {len(series)}")
    tail = series.iloc[-window:]
    r63 = sharpe_ratio(tail)
    cum = (1.0 + tail).cumprod()
    dd = (cum / cum.expanding().max()) - 1.0
    return r63, float(dd.min())


def count_regime_flips(path: Path) -> int:
    try:
        st = load_yaml(path)
    except Exception:
        return 0
    flips = 0
    prev = None
    for rec in (st.get("run_history") or []):
        exp = rec.get("regime_exposure")
        if exp is not None:
            if prev is not None and exp != prev:
                flips += 1
            prev = exp
    return flips


def reference_sample_checks(net_ret: pd.Series) -> list[dict[str, Any]]:
    """Re-derive the Cycle 901/902 reference-sample anchors and check them."""
    checks: list[dict[str, Any]] = []

    reference = net_ret.loc[: REF_INCUMBENT_END]
    ref_sharpe = sharpe_ratio(reference)
    ref_mdd = max_drawdown(reference)
    ref_psr = float(
        compute_psr(reference, sr_target=PSR_TARGET_BACKTEST_SCALE, seed=20240101)["psr_normal"]
    )
    checks.append(
        {
            "name": "incumbent_reference_sample",
            "definition": f"realized net returns truncated at {REF_INCUMBENT_END}",
            "expected": {
                "sessions": REF_INCUMBENT_SESSIONS,
                "sharpe": REF_INCUMBENT_SHARPE,
                "max_drawdown": REF_INCUMBENT_MAX_DD,
                "psr": REF_INCUMBENT_PSR,
            },
            "observed": {
                "sessions": int(len(reference)),
                "sharpe": ref_sharpe,
                "max_drawdown": ref_mdd,
                "psr": ref_psr,
            },
            "pass": bool(
                len(reference) == REF_INCUMBENT_SESSIONS
                and abs(ref_sharpe - REF_INCUMBENT_SHARPE) <= 1e-12
                and abs(ref_mdd - REF_INCUMBENT_MAX_DD) <= 1e-12
                and abs(ref_psr - REF_INCUMBENT_PSR) <= 1e-18
            ),
        }
    )

    state = load_yaml(PAPER_STATE_PATH) or {}
    paper_returns = [float(r) for r in (state.get("cumulative_returns") or [])]
    if len(paper_returns) < REF_PAPER_SESSIONS:
        raise RuntimeError(
            f"paper record has {len(paper_returns)} sessions, "
            f"fewer than the {REF_PAPER_SESSIONS}-session reference sample"
        )
    paper_sharpe = sharpe_ratio(paper_returns[:REF_PAPER_SESSIONS])
    checks.append(
        {
            "name": "paper_record_reference_sample",
            "definition": f"first {REF_PAPER_SESSIONS} sessions of the committed paper record",
            "expected": {
                "sessions": REF_PAPER_SESSIONS,
                "sharpe": REF_PAPER_SHARPE,
            },
            "observed": {
                "sessions": REF_PAPER_SESSIONS,
                "sharpe": paper_sharpe,
            },
            "pass": bool(abs(paper_sharpe - REF_PAPER_SHARPE) <= 1e-6),
        }
    )
    return checks


def main() -> int:
    cand = load_yaml(CONFIG_CAND)
    gates = load_yaml(CONFIG_GATES)
    universe = list(cand["universe"])
    cost_model = cand.get("cost_model", {})
    overlay_warmup = cand.get("overlay_warmup")

    try:
        per_symbol_stats, raw_hashes, union_index = scan_raw_cache(universe)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    start_label = max(pd.Timestamp(s["first_date"]) for s in per_symbol_stats.values()).date()
    end_label = min(pd.Timestamp(s["last_date"]) for s in per_symbol_stats.values()).date()
    start = start_label
    end = end_label

    union_fingerprint = {
        "first_date": union_index.min().date().isoformat(),
        "last_date": union_index.max().date().isoformat(),
        "count": int(len(union_index)),
    }

    net_ret, weights, metrics = run_backtest(
        symbols=universe,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        lookback=cand["signal"]["lookback"],
        skip=cand["signal"]["skip"],
        top_fraction=cand["signal"]["top_fraction"],
        rebalance_freq=cand["signal"]["rebalance_freq"],
    )

    if net_ret.empty:
        print("ERROR: empty returns", file=sys.stderr)
        return 1

    paper_sharpe = sharpe_ratio(net_ret)
    paper_mdd = max_drawdown(net_ret)
    paper_days = len(net_ret)
    rolling_sharpe_63d, rolling_mdd_63d = rolling_window(net_ret, 63)
    psr_res = compute_psr(net_ret, sr_target=PSR_TARGET_BACKTEST_SCALE, seed=20240101)
    psr_normal = float(psr_res["psr_normal"])
    sharpe_obs_canon = float(psr_res["sharpe_observed"])
    sharpe_se = float(psr_res["sharpe_se"])
    sharpe_backtest_scale = backtest_sharpe_ratio(net_ret)
    regime_flips = count_regime_flips(PROCESSED_DIR / "paper_trading_state.yaml")

    realized_index = pd.DatetimeIndex(net_ret.index)
    realized_start = realized_index.min().date().isoformat()
    realized_end = realized_index.max().date().isoformat()
    realized_count = int(len(realized_index))
    realized_equals_union = bool(
        realized_count == union_fingerprint["count"]
        and realized_start == union_fingerprint["first_date"]
        and realized_end == union_fingerprint["last_date"]
        and realized_index.equals(union_index)
    )

    try:
        ref_checks = reference_sample_checks(net_ret)
    except (OSError, RuntimeError) as exc:
        print(f"ERROR: reference-sample check failed: {exc}", file=sys.stderr)
        return 1
    ref_checks_pass = all(bool(c["pass"]) for c in ref_checks)

    cache_fingerprint = {
        "per_symbol": {
            sym: {
                "rows": stats["row_count"],
                "first_date": stats["first_date"],
                "last_date": stats["last_date"],
                "sha256": raw_hashes[sym],
            }
            for sym, stats in per_symbol_stats.items()
        },
        "note": (
            "derived from the raw cache at run time; a later append to the cache "
            "changes these values and is therefore visible as a fingerprint change"
        ),
    }

    sample = SampleDef(
        label_start_date=start_label.isoformat(),
        label_end_date=end_label.isoformat(),
        realized_start_date=realized_start,
        realized_end_date=realized_end,
        realized_session_count=realized_count,
        start_date=realized_start,
        end_date=realized_end,
        session_count=realized_count,
        universe=universe,
        lookback=cand["signal"]["lookback"],
        skip=cand["signal"]["skip"],
        top_fraction=cand["signal"]["top_fraction"],
        rebalance_freq=cand["signal"]["rebalance_freq"],
        cost_model={k: float(v) for k, v in cost_model.items()},
        overlay_warmup=overlay_warmup,
        sha256_raw_files=raw_hashes,
        per_symbol_stats=per_symbol_stats,
        union_index_fingerprint=union_fingerprint,
        cache_fingerprint=cache_fingerprint,
        reference_sample_anchors={
            "incumbent_reference_end": REF_INCUMBENT_END,
            "incumbent_reference_sessions": REF_INCUMBENT_SESSIONS,
            "incumbent_reference_sharpe": REF_INCUMBENT_SHARPE,
            "incumbent_reference_max_drawdown": REF_INCUMBENT_MAX_DD,
            "incumbent_reference_psr": REF_INCUMBENT_PSR,
            "paper_record_reference_sessions": REF_PAPER_SESSIONS,
            "paper_record_reference_sharpe": REF_PAPER_SHARPE,
        },
        reference_sample_checks=ref_checks,
    )

    def check(thr, comp, val):
        if comp == "gte":
            return val >= thr
        if comp == "gt":
            return val > thr
        if comp == "lte":
            return val <= thr
        if comp == "lt":
            return val < thr
        return val == thr

    gate_results = {}
    failed = []
    for g in gates["gates"]:
        name = g["name"]
        thr = float(g["threshold"])
        comp = g["comparison"]
        if name == "track_record_length":
            val = float(paper_days)
        elif name == "full_period_sharpe":
            val = paper_sharpe
        elif name == "rolling_63d_sharpe":
            val = rolling_sharpe_63d
        elif name == "max_drawdown":
            val = paper_mdd
        elif name == "rolling_63d_max_dd":
            val = rolling_mdd_63d
        elif name == "regime_flips":
            val = float(regime_flips)
        elif name == "psr":
            val = psr_normal
        else:
            continue
        ok = check(thr, comp, val)
        gate_results[name] = {"value": val, "threshold": thr, "comparison": comp, "pass": ok}
        if not ok:
            failed.append(name)

    pgz = gates.get("psr_grey_zone", {})
    if "lower" in pgz and "upper" in pgz:
        if psr_normal < float(pgz["lower"]):
            psr_zone = "below_grey"
        elif psr_normal < float(pgz["upper"]):
            psr_zone = "grey_zone"
        else:
            psr_zone = "above_grey"
    else:
        psr_zone = "unknown"

    dm = gates.get("decision_mapping", {})
    if paper_days < 126:
        decision = dm.get("insufficient_track_record", "INCONCLUSIVE")
    elif all(gr["pass"] for gr in gate_results.values()):
        decision = dm.get("all_gates_pass", "GO")
    elif failed == ["psr"] and psr_zone == "grey_zone":
        decision = dm.get("psr_grey_zone_and_only_psr_gate_fails", "INCONCLUSIVE")
    else:
        decision = dm.get("any_other_gate_fails", "NO-GO")

    required_sr = None
    if psr_normal < 0.95 and sharpe_se > 0:
        required_sr = PSR_TARGET_BACKTEST_SCALE + 1.6448536269514722 * sharpe_se
    elif psr_normal < 0.95:
        required_sr = PSR_TARGET_BACKTEST_SCALE

    report = {
        "sample": sample.to_dict(),
        "canonical": {
            "paper_sharpe": paper_sharpe,
            "paper_max_dd": paper_mdd,
            "rolling_sharpe_63d": rolling_sharpe_63d,
            "rolling_63d_max_dd": rolling_mdd_63d,
            "regime_flips": regime_flips,
            "paper_days": paper_days,
            "sharpe_observed_canonical": sharpe_obs_canon,
            "sharpe_se": sharpe_se,
        },
        "backtest_baseline_scale": {
            "sharpe_backtest_scale": sharpe_backtest_scale,
            "psr_target_backtest_scale": PSR_TARGET_BACKTEST_SCALE,
            "baseline_tieback": {
                "recorded_baseline": 1.4178,
                "tolerance": "window/warmup/costs explain deviation (must be quantified)",
                "within_tolerance": abs(sharpe_backtest_scale - 1.4178) < 0.1,
                "delta": sharpe_backtest_scale - 1.4178,
            },
        },
        "psr": {
            "psr_normal": psr_normal,
            "psr_empirical": float(psr_res["psr_empirical"]),
            "psr_zone": psr_zone,
            "sharpe_ci_lower": float(psr_res.get("sharpe_ci_lower", float("nan"))),
            "sharpe_ci_upper": float(psr_res.get("sharpe_ci_upper", float("nan"))),
        },
        "gates": gate_results,
        "decision": decision,
        "failed_gates": failed,
        "attainability": {
            "psr_reaches_095": psr_normal >= 0.95,
            "required_observed_sharpe_for_psr095": required_sr if required_sr is not None else sharpe_obs_canon,
            "sharpe_se_at_this_sample": sharpe_se,
            "sample_length": paper_days,
            "note": "PSR>=0.95 when (sr_obs - sr_t)/se >= 1.64485 at same SE.",
        },
        "consequence": "not promotable in principle" if (psr_normal < 0.95) else "short prospective record; long sample passes PSR gate",
        "reproduction": {
            "command": "python research/promotion_feasibility_backtest.py",
            "deterministic": True,
            "no_network": True,
            "read_only_data": True,
        },
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_md = REPORTS_DIR / "promotion_feasibility_backtest_001.md"
    with open(out_md, "w") as f:
        f.write("# Promotion Criteria Feasibility (Cycle 867)\n\n")
        f.write(
            "`label_*` is the common inception of the universe (the max of the per-symbol first\n"
            "dates); `realized_*` (and the historical `start_date` / `end_date` /\n"
            "`session_count` keys) is the sample the backtest actually computed. The engine\n"
            "does not slice the price frame to the common inception, so the realized sample\n"
            "is the union calendar of the raw cache -- the two windows are published side by\n"
            "side instead of one being labelled as the other.\n\n"
        )
        f.write("## Sample definition\n\n```json\n")
        json.dump(report["sample"], f, indent=2)
        f.write("\n```\n\n")
        f.write("## Canonical metrics (arithmetic_annualized_rf0)\n\n```json\n")
        json.dump(report["canonical"], f, indent=2)
        f.write("\n```\n\n")
        f.write("## Backtest-baseline scale (cagr_annualized_rf2)\n\n```json\n")
        json.dump(report["backtest_baseline_scale"], f, indent=2)
        f.write("\n```\n\n")
        f.write("## PSR vs backtest baseline 1.4178\n\n```json\n")
        json.dump(report["psr"], f, indent=2)
        f.write("\n```\n\n")
        f.write("## Gate evaluation (same table as config/promotion_gates.yaml)\n\n```json\n")
        json.dump(report["gates"], f, indent=2)
        f.write("\n```\n\n")
        f.write("## Reference-sample integrity (Cycle 901/902 anchors)\n\n```json\n")
        json.dump(report["sample"]["reference_sample_checks"], f, indent=2)
        f.write("\n```\n\n")
        f.write("## Decision\n\n")
        f.write(f"- decision: {report['decision']}\n")
        f.write(f"- failed_gates: {report['failed_gates']}\n")
        f.write(f"- psr_zone: {report['psr']['psr_zone']}\n\n")
        f.write("## Attainability (explicit answer)\n\n```json\n")
        json.dump(report["attainability"], f, indent=2)
        f.write("\n```\n\n")
        f.write("## Consequence for research loop\n\n")
        f.write(f"{report['consequence']}\n\n")
        f.write("## Falsification conditions\n\n")
        f.write("- backtest reads from network (cache bypass) -> false claim; must be read-only.\n")
        f.write("- long-sample uses different universe/window than stated -> reject.\n")
        f.write("- canonical vs backtest-baseline scales mixed -> reject.\n")
        f.write("- gate thresholds changed from config/promotion_gates.yaml -> reject.\n")
        f.write("- published realized window differs from the raw-cache union index -> reject.\n")
        f.write("- a reference-sample anchor no longer reproduces -> reject.\n\n")
        f.write("## Reproduction\n\n```json\n")
        json.dump(report["reproduction"], f, indent=2)
        f.write("\n```\n")

    overall = "PASS" if (ref_checks_pass and realized_equals_union) else "FAIL"
    print(f"OVERALL: {overall}")
    print(
        f"SAMPLE: realized {realized_start}..{realized_end} ({realized_count} sessions), "
        f"label {start_label.isoformat()}..{end_label.isoformat()}, universe={universe}"
    )
    print(f"sharpe_canon={paper_sharpe:.6f} sharpe_backtest={sharpe_backtest_scale:.6f} delta={sharpe_backtest_scale-1.4178:.6f}")
    print(f"rolling63={rolling_sharpe_63d:.6f} psr={psr_normal:.6f} failed={failed} decision={decision}")
    print(f"attainable_psr095={report['attainability']['psr_reaches_095']} req_sr_obs={required_sr:.6f} se={sharpe_se:.6f}")
    print(
        f"realized window equals raw-cache union index: {realized_equals_union} "
        f"({union_fingerprint['first_date']}..{union_fingerprint['last_date']}, "
        f"{union_fingerprint['count']} sessions)"
    )
    for c in ref_checks:
        print(f"reference check [{c['name']}]: {'PASS' if c['pass'] else 'FAIL'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
