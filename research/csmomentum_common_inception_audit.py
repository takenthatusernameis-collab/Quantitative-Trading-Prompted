#!/usr/bin/env python3
"""Common-inception sample-definition audit for csmomentum_001 (Cycle 905).

Read-only measurement of the *sample* on which the candidate's long-sample
diagnostic is to be evaluated. The tool:

* consumes the machine-readable sample policy (``config/sample_policy.yaml``,
  section ``candidates.csmomentum_001``) and **fails closed** when the policy
  is missing, malformed or does not carry the pre-registered control,
* re-derives the common inception from the raw cache at measurement time (a
  rule, never a frozen date) and refuses to trust any date in the policy,
* measures the union sample next to the two pre-registered samples
  (``common_inception_slice`` and the warm-up preserving
  ``common_inception_window``): sessions, start/end, price width and the
  *selectable breadth* (how many assets have a valid momentum on a session),
  i.e. the raggedness that a naive union sample hides,
* writes ``research/reports/csmomentum_common_inception_audit_001.md`` and
  exits non-zero when any structural check fails.

Nothing under ``data/`` or ``config/`` is written (checked by fingerprint), no
backtest is executed, no gate, threshold, decision mapping, candidate
configuration, universe, cost model or Sharpe convention is touched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.promotion_feasibility_backtest import load_yaml, scan_raw_cache  # noqa: E402
from src.features.momentum import compute_momentum  # noqa: E402

CONFIG_CAND = REPO_ROOT / "config" / "csmomentum_candidate_001.yaml"
POLICY_DEFAULT = REPO_ROOT / "config" / "sample_policy.yaml"
RAW_DIR = REPO_ROOT / "data" / "raw"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
OUT_REPORT = REPORTS_DIR / "csmomentum_common_inception_audit_001.md"

CANDIDATE_ID = "csmomentum_001"
RULE_ID = "common_inception_fully_populated"
EVALUATION_SAMPLE = "common_inception_slice"
WINDOW_SAMPLE = "common_inception_window"
UNION_SAMPLE = "union_sample"
# src/features/momentum.py:select_top_decile falls back to the single best
# asset below this many selectable assets.
MOMENTUM_BREADTH_FALLBACK = 5
# Keys that would turn the policy's *rule* into a frozen date.
FROZEN_DATE_KEYS = ("common_inception", "inception_date", "start_date", "sample_start")


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


# ----------------------------------------------------------------------
# Policy
# ----------------------------------------------------------------------
def load_policy(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load and validate the policy; fail closed on anything malformed."""
    import yaml

    if not path.exists():
        fail(f"policy file missing: {path}")
    try:
        policy = yaml.safe_load(path.read_text())
    except Exception as exc:  # pragma: no cover - yaml parse failure
        fail(f"failed to load policy: {exc}")
    if not isinstance(policy, dict):
        fail("policy is not a mapping")
    if policy.get("schema_version") != 1:
        fail("bad schema_version")
    candidates = policy.get("candidates")
    if not isinstance(candidates, dict):
        fail("missing candidates section")
    section = candidates.get(CANDIDATE_ID)
    if not isinstance(section, dict):
        fail(f"missing candidates.{CANDIDATE_ID} section")

    if section.get("rule_id") != RULE_ID:
        fail(f"bad rule_id (expected {RULE_ID})")
    universe = section.get("universe")
    if not isinstance(universe, list) or not universe:
        fail("candidate universe must be a non-empty list")
    if not all(isinstance(sym, str) and sym for sym in universe):
        fail("candidate universe must contain symbol names")
    derivation = section.get("derivation")
    if not isinstance(derivation, dict) or not str(derivation.get("rule", "")).strip():
        fail("candidate derivation.rule must be a non-empty string")
    diag = section.get("long_sample_diagnostic")
    if not isinstance(diag, dict):
        fail("candidate long_sample_diagnostic must be a mapping")
    if diag.get("evaluation_sample") != EVALUATION_SAMPLE:
        fail(f"candidate evaluation_sample must be {EVALUATION_SAMPLE}")
    publish = diag.get("publish_alongside")
    if not isinstance(publish, list):
        fail("candidate publish_alongside must be a list")
    for required in (WINDOW_SAMPLE, UNION_SAMPLE):
        if required not in publish:
            fail(f"candidate publish_alongside must contain {required}")
    warm_up = section.get("warm_up_convention")
    if not isinstance(warm_up, dict):
        fail("candidate warm_up_convention must be a mapping")
    if warm_up.get("slice") != EVALUATION_SAMPLE:
        fail(f"candidate warm_up_convention.slice must be {EVALUATION_SAMPLE}")
    if warm_up.get("window_preserving") != WINDOW_SAMPLE:
        fail(f"candidate warm_up_convention.window_preserving must be {WINDOW_SAMPLE}")
    if not str(section.get("evidence_note", "")).strip():
        fail("candidate evidence_note must be a non-empty string")
    revisit = section.get("conditions_for_revisit")
    if not isinstance(revisit, list) or not revisit:
        fail("candidate conditions_for_revisit must be a non-empty list")
    for key in FROZEN_DATE_KEYS:
        if key in section:
            fail(f"candidate section carries a frozen date key ({key}); the rule is re-derived")
    return policy, section


# ----------------------------------------------------------------------
# Raw cache (read only)
# ----------------------------------------------------------------------
def load_symbol_frame(path: Path) -> pd.DataFrame:
    """Read one cached parquet exactly as ``YFinanceFetcher._load_cached`` does."""
    df = pd.read_parquet(path)
    if df.empty:
        fail(f"empty raw cache file: {path}")
    index = pd.to_datetime(df.index)
    if index.tz is None:
        index = index.tz_localize("UTC", ambiguous="infer", nonexistent="shift_forward")
    else:
        index = index.tz_convert("UTC")
    df = df.copy()
    df.index = index
    return df.sort_index()


def aligned_close_from_cache(universe: list[str]) -> pd.DataFrame:
    """The aligned, forward-filled Close frame the engine works on.

    Built straight from the cached parquet files (the same files the fetcher
    would read with ``force=False``) so the audit can never download or write.
    """
    frames: dict[str, pd.DataFrame] = {}
    for symbol in universe:
        path = RAW_DIR / f"{symbol}.parquet"
        if not path.exists():
            fail(f"missing raw cache file: {path}")
        frames[symbol] = load_symbol_frame(path)
    all_index = pd.DatetimeIndex(sorted(set().union(*[f.index for f in frames.values()])))
    all_index = all_index[all_index.weekday < 5]
    close = pd.DataFrame(index=all_index, columns=list(frames.keys()), dtype=float)
    for symbol, frame in frames.items():
        close[symbol] = frame["Close"].reindex(all_index).ffill()
    return close


def width_series(close: pd.DataFrame, index: pd.DatetimeIndex) -> pd.Series:
    """Number of assets with a price on each session of *index*."""
    return close.reindex(index).notna().sum(axis=1)


def width_changes(width: pd.Series) -> list[dict[str, Any]]:
    """The sessions on which the cross-section width changes."""
    changes: list[dict[str, Any]] = []
    previous: int | None = None
    for stamp, value in width.items():
        count = int(value)
        if previous is None:
            previous = count
            continue
        if count != previous:
            changes.append({"date": stamp.date().isoformat(), "assets_with_price": count})
            previous = count
    return changes


def breadth_stats(breadth: pd.Series) -> dict[str, Any]:
    """Selectable-breadth summary of one sample."""
    if breadth.empty:
        return {
            "sessions": 0,
            "breadth_min": 0,
            "breadth_median": 0.0,
            "breadth_max": 0,
            "sessions_with_zero_selectable_assets": 0,
            "sessions_with_fewer_than_five_selectable_assets": 0,
            "first_session_with_a_selectable_asset": None,
            "flat_sessions_before_the_first_signal": 0,
        }
    flat = breadth[breadth == 0]
    held = breadth[breadth > 0]
    return {
        "sessions": int(len(breadth)),
        "opening_breadth": int(breadth.iloc[0]),
        "breadth_min": int(breadth.min()),
        "breadth_median": float(breadth.median()),
        "breadth_max": int(breadth.max()),
        "sessions_with_zero_selectable_assets": int(len(flat)),
        "sessions_with_fewer_than_five_selectable_assets": int(
            (breadth < MOMENTUM_BREADTH_FALLBACK).sum()
        ),
        "first_session_with_a_selectable_asset": (
            held.index.min().date().isoformat() if not held.empty else None
        ),
        "flat_sessions_before_the_first_signal": int(len(flat)),
    }


def fingerprint(root: Path) -> dict[str, str]:
    """SHA-256 of every file under *root* (used for the read-only guarantee)."""
    out: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            out[str(path.relative_to(REPO_ROOT))] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    return out


# ----------------------------------------------------------------------
# Measurement
# ----------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, default=POLICY_DEFAULT)
    args = parser.parse_args(argv)

    policy, section = load_policy(args.policy)

    cand = load_yaml(CONFIG_CAND)
    universe = list(cand["universe"])
    policy_universe = list(section["universe"])
    universe_matches = policy_universe == universe
    if not universe_matches:
        fail("policy universe does not match config/csmomentum_candidate_001.yaml")

    signal_cfg = cand.get("signal", {})
    lookback = int(signal_cfg["lookback"])
    skip = int(signal_cfg["skip"])
    top_fraction = float(signal_cfg["top_fraction"])
    n_assets = len(universe)

    data_before = fingerprint(REPO_ROOT / "data")
    config_before = fingerprint(REPO_ROOT / "config")

    per_symbol_stats, raw_hashes, raw_union_index = scan_raw_cache(universe)
    close = aligned_close_from_cache(universe)
    union_index = close.index
    common_inception = pd.Timestamp(
        max(s["first_date"] for s in per_symbol_stats.values()), tz="UTC"
    )
    ci_str = common_inception.date().isoformat()
    union_start = union_index.min().date().isoformat()
    union_end = union_index.max().date().isoformat()

    union_width = width_series(close, union_index)
    ci_index = union_index[union_index >= common_inception]
    ci_width = union_width.reindex(ci_index)

    # -- the two pre-registered samples --------------------------------
    # slice: the price frame is truncated at the common inception, so the
    # signal has no pre-inception history to warm up with.
    slice_momentum = compute_momentum(
        close.loc[ci_index], lookback=lookback, skip=skip
    )
    slice_breadth = slice_momentum.notna().sum(axis=1)
    # window: the union frame is kept (warm-up preserved) and only the
    # evaluation window is truncated.
    union_breadth = compute_momentum(close, lookback=lookback, skip=skip).notna().sum(axis=1)
    window_breadth = union_breadth.reindex(ci_index)

    slice_stats = breadth_stats(slice_breadth)
    window_stats = breadth_stats(window_breadth)

    samples: dict[str, Any] = {
        UNION_SAMPLE: {
            "start": union_start,
            "end": union_end,
            "sessions": int(len(union_index)),
            "price_width_min": int(union_width.min()),
            "price_width_median": float(union_width.median()),
            "price_width_max": int(union_width.max()),
            "price_width_changes": width_changes(union_width),
            "momentum_breadth": breadth_stats(union_breadth),
        },
        EVALUATION_SAMPLE: {
            "start": ci_str,
            "end": union_end,
            "sessions": int(len(ci_index)),
            "price_width_min": int(ci_width.min()) if len(ci_width) else 0,
            "price_width_median": float(ci_width.median()) if len(ci_width) else 0.0,
            "price_width_max": int(ci_width.max()) if len(ci_width) else 0,
            "price_width_changes": width_changes(ci_width),
            "fully_populated": bool(len(ci_width) and (ci_width == n_assets).all()),
            "momentum_breadth": slice_stats,
        },
        WINDOW_SAMPLE: {
            "start": ci_str,
            "end": union_end,
            "sessions": int(len(ci_index)),
            "note": "warm-up preserved: the union price frame is kept, only the evaluation window is truncated",
            "price_width_min": int(ci_width.min()) if len(ci_width) else 0,
            "price_width_max": int(ci_width.max()) if len(ci_width) else 0,
            "momentum_breadth": window_stats,
        },
    }

    # -- structural checks ---------------------------------------------
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, observed: Any = None, expected: Any = None) -> None:
        checks.append(
            {
                "name": name,
                "expected": expected,
                "observed": observed,
                "pass": bool(passed),
            }
        )

    check(
        "policy_universe_matches_candidate_config",
        universe_matches,
        observed=len(policy_universe),
        expected=len(universe),
    )
    check(
        "common_inception_rederived_from_raw_cache",
        common_inception
        == pd.Timestamp(
            max(s["first_date"] for s in per_symbol_stats.values()), tz="UTC"
        ),
        observed=ci_str,
        expected="max of per-symbol first dates in data/raw",
    )
    check(
        "union_sample_is_ragged",
        bool(union_width.min() < n_assets),
        observed=int(union_width.min()),
        expected=f"< {n_assets}",
    )
    check(
        "common_inception_after_union_start",
        common_inception >= union_index.min(),
        observed=ci_str,
        expected=f">= {union_start}",
    )
    check(
        "common_inception_sample_is_nonempty",
        len(ci_index) > 0,
        observed=int(len(ci_index)),
        expected="> 0 sessions",
    )
    check(
        "common_inception_fully_populated",
        bool(len(ci_width) and (ci_width == n_assets).all()),
        observed=int(ci_width.min()) if len(ci_width) else 0,
        expected=n_assets,
    )
    check(
        "aligned_index_matches_raw_cache_union",
        set(union_index) == set(raw_union_index),
        observed=int(len(union_index)),
        expected=int(len(raw_union_index)),
    )
    check(
        "slice_warmup_ramp_matches_lookback_plus_skip",
        slice_stats["flat_sessions_before_the_first_signal"] == lookback + skip,
        observed=slice_stats["flat_sessions_before_the_first_signal"],
        expected=lookback + skip,
    )
    check(
        "window_variant_preserves_warmup",
        window_stats["opening_breadth"] > slice_stats["opening_breadth"],
        observed={
            "slice_opening_breadth": slice_stats["opening_breadth"],
            "window_opening_breadth": window_stats["opening_breadth"],
        },
        expected="window opening breadth > slice opening breadth (warm-up preserved)",
    )
    check(
        "common_inception_sample_is_a_subset_of_the_union_sample",
        set(ci_index).issubset(set(union_index)),
        observed=int(len(ci_index)),
        expected=f"subset of {len(union_index)} union sessions",
    )
    check(
        "common_inception_sample_ends_with_the_union_sample",
        bool(len(ci_index)) and ci_index.max() == union_index.max(),
        observed=ci_index.max().date().isoformat() if len(ci_index) else None,
        expected=union_end,
    )

    data_after = fingerprint(REPO_ROOT / "data")
    config_after = fingerprint(REPO_ROOT / "config")
    check(
        "data_and_config_unchanged",
        data_before == data_after and config_before == config_after,
        observed={"data": data_before == data_after, "config": config_before == config_after},
        expected={"data": True, "config": True},
    )

    overall = "PASS" if all(c["pass"] for c in checks) else "FAIL"

    report = {
        "candidate": CANDIDATE_ID,
        "artifact": "common-inception sample-definition audit (measurement only, no backtest)",
        "policy": {
            "path": str(args.policy.relative_to(REPO_ROOT))
            if args.policy.is_absolute() and REPO_ROOT in args.policy.parents
            else str(args.policy),
            "rule_id": section["rule_id"],
            "evaluation_sample": section["long_sample_diagnostic"]["evaluation_sample"],
            "publish_alongside": section["long_sample_diagnostic"]["publish_alongside"],
            "derivation_rule": section["derivation"]["rule"],
            "evidence_note": section["evidence_note"],
            "conditions_for_revisit": section["conditions_for_revisit"],
        },
        "candidate_configuration": {
            "signal_type": signal_cfg.get("type"),
            "lookback": lookback,
            "skip": skip,
            "top_fraction": top_fraction,
            "rebalance_freq": signal_cfg.get("rebalance_freq"),
            "cost_model": cand.get("cost_model"),
            "execution": cand.get("execution"),
            "universe_size": n_assets,
        },
        "common_inception": ci_str,
        "samples": samples,
        "raggedness": {
            "union_price_width_changes": width_changes(union_width),
            "sessions_with_fewer_than_N_assets_union": int((union_width < n_assets).sum()),
            "sessions_with_fewer_than_N_assets_common_inception": int(
                (ci_width < n_assets).sum()
            ),
            "selectable_breadth_threshold": MOMENTUM_BREADTH_FALLBACK,
        },
        "raw_cache_fingerprint": {
            "per_symbol": {
                sym: {
                    "first_date": per_symbol_stats[sym]["first_date"],
                    "last_date": per_symbol_stats[sym]["last_date"],
                    "row_count": per_symbol_stats[sym]["row_count"],
                    "sha256": raw_hashes[sym],
                }
                for sym in universe
            },
        },
        "checks": checks,
        "overall": overall,
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_REPORT, "w") as fh:
        fh.write(f"# CSMomentum Common-Inception Audit (Cycle 905)\n\n")
        fh.write(
            "Read-only sample measurement for `csmomentum_001`. The common inception is\n"
            "re-derived from the raw cache on every run; no date in the policy is trusted.\n"
            "No backtest is executed here and no gate, threshold, universe, cost model or\n"
            "Sharpe convention is changed.\n\n"
        )
        fh.write(
            f"- common inception: **{ci_str}** (re-derived; max of per-symbol first dates)\n"
            f"- union sample: {union_start} .. {union_end}, {len(union_index)} sessions, "
            f"price width {int(union_width.min())}..{int(union_width.max())} of {n_assets}\n"
            f"- common-inception slice: {ci_str} .. {union_end}, {len(ci_index)} sessions, "
            f"price width {int(ci_width.min()) if len(ci_width) else 0}.."
            f"{int(ci_width.max()) if len(ci_width) else 0} of {n_assets}\n"
            f"- slice warm-up ramp: {slice_stats['flat_sessions_before_the_first_signal']} flat "
            f"sessions before the first selectable asset "
            f"({slice_stats['first_session_with_a_selectable_asset']}), "
            f"first selectable asset in the warm-up-preserving window: "
            f"{window_stats['first_session_with_a_selectable_asset']}\n\n"
        )
        fh.write("```json\n")
        json.dump(report, fh, indent=2, sort_keys=False)
        fh.write("\n```\n")

    print(f"OVERALL: {overall}")
    for c in checks:
        print(f"check [{c['name']}]: {'PASS' if c['pass'] else 'FAIL'}")
    print(
        f"common inception {ci_str} (re-derived); union {union_start}..{union_end} "
        f"({len(union_index)} sessions, width {int(union_width.min())}.."
        f"{int(union_width.max())} of {n_assets})"
    )
    print(
        f"common-inception slice {ci_str}..{union_end} ({len(ci_index)} sessions, "
        f"fully populated={samples[EVALUATION_SAMPLE]['fully_populated']}, "
        f"flat sessions before the first signal "
        f"{slice_stats['flat_sessions_before_the_first_signal']}, "
        f"breadth max {slice_stats['breadth_max']})"
    )
    print(
        f"common-inception window (warm-up preserved) {ci_str}..{union_end} "
        f"({len(ci_index)} sessions, flat sessions before the first signal "
        f"{window_stats['flat_sessions_before_the_first_signal']}, "
        f"breadth max {window_stats['breadth_max']})"
    )
    print(f"report: {OUT_REPORT.relative_to(REPO_ROOT)}")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
