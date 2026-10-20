#!/usr/bin/env python3
"""Common-inception sample-definition audit for csmomentum_001 (Cycle 905).

Read-only measurement: re-derives the candidate's common inception from the raw
cache and reports union vs common-inception slice/window raggedness. Does not
execute any backtest, change config, or write under data/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.promotion_feasibility_backtest import load_yaml, scan_raw_cache  # noqa: E402

CONFIG_CAND = REPO_ROOT / "config" / "csmomentum_candidate_001.yaml"
POLICY_DEFAULT = REPO_ROOT / "config" / "sample_policy.yaml"
RAW_DIR = REPO_ROOT / "data" / "raw"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
OUT_REPORT = REPORTS_DIR / "csmomentum_common_inception_audit_001.md"


def load_policy(path: Path) -> dict:
    import yaml

    if not path.exists():
        raise SystemExit(f"ERROR: policy file missing: {path}")
    try:
        policy = yaml.safe_load(path.read_text())
    except Exception as e:
        raise SystemExit(f"ERROR: failed to load policy: {e}")
    if not isinstance(policy, dict):
        raise SystemExit("ERROR: policy is not a dict")
    if policy.get("schema_version") != 1:
        raise SystemExit("ERROR: bad schema_version")
    cand_section = (policy.get("candidates") or {}).get("csmomentum_001")
    if not isinstance(cand_section, dict):
        raise SystemExit("ERROR: missing candidates.csmomentum_001 section")
    if cand_section.get("rule_id") != "common_inception_fully_populated":
        raise SystemExit("ERROR: bad rule_id")
    return policy, cand_section


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, default=POLICY_DEFAULT)
    args = parser.parse_args(argv)

    policy, cand_section = load_policy(args.policy)

    cand = load_yaml(CONFIG_CAND)
    universe = list(cand["universe"])
    expected_universe = list(cand_section.get("universe", []))
    if expected_universe and expected_universe != universe:
        raise SystemExit("ERROR: policy universe mismatch")

    per_symbol_stats, raw_hashes, union_index = scan_raw_cache(universe)
    common_inception = pd.Timestamp(
        max(s["first_date"] for s in per_symbol_stats.values()), tz="UTC"
    )
    ci_str = common_inception.date().isoformat()
    union_start = union_index.min().date().isoformat()
    union_end = union_index.max().date().isoformat()

    # raggedness: price width changes on union index
    # build aligned close
    from src.data.yfinance_fetcher import fetch_universe

    data = fetch_universe(universe, union_start, union_end, force=False)
    close = data.xs("Close", level=0, axis=1).ffill()
    width = close.reindex(union_index).notna().sum(axis=1)

    def width_changes(series):
        changes = []
        prev = None
        for stamp, v in series.items():
            c = int(v)
            if prev is None:
                prev = c
                continue
            if c != prev:
                changes.append({"date": stamp.date().isoformat(), "assets_with_price": c})
                prev = c
        return changes

    ci_mask = union_index >= common_inception
    ci_index = union_index[ci_mask]

    sessions_with_lt_n = int((width.reindex(ci_index) < len(universe)).sum()) if False else 0

    # structural checks
    checks = []
    checks.append(("common_inception_rederived", True))
    checks.append(("ci_after_union_start", common_inception >= union_index.min()))
    checks.append(("ci_index_nonempty", len(ci_index) > 0))
    # fully populated on common-inception slice
    ci_width = width.reindex(ci_index)
    fully_populated = bool((ci_width == len(universe)).all())
    checks.append(("common_inception_fully_populated", fully_populated))

    overall = "PASS" if all(c[1] for c in checks) else "FAIL"

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "candidate": "csmomentum_001",
        "universe_size": len(universe),
        "common_inception": ci_str,
        "union": {
            "start": union_start,
            "end": union_end,
            "sessions": int(len(union_index)),
            "price_width_min": int(width.min()),
            "price_width_max": int(width.max()),
            "price_width_changes": width_changes(width),
        },
        "common_inception_slice": {
            "start": ci_str,
            "end": union_end,
            "sessions": int(len(ci_index)),
            "price_width_min": int(ci_width.min()) if len(ci_width) else 0,
            "price_width_max": int(ci_width.max()) if len(ci_width) else 0,
            "fully_populated": fully_populated,
        },
        "common_inception_window": {
            "start": ci_str,
            "end": union_end,
            "sessions": int(len(ci_index)),
            "note": "warm-up preserved variant; same window as slice",
        },
        "raggedness": {
            "union_price_width_changes": width_changes(width),
            "sessions_with_fewer_than_N_assets_union": int((width < len(universe)).sum()),
        },
        "checks": [{"name": n, "pass": bool(p)} for n, p in checks],
        "overall": overall,
    }
    with open(OUT_REPORT, "w") as fh:
        fh.write("# CSMomentum Common-Inception Audit (Cycle 905)\n\n")
        fh.write("```json\n")
        json.dump(report, fh, indent=2)
        fh.write("\n```\n")

    print(f"OVERALL: {overall}")
    for n, p in checks:
        print(f"check [{n}]: {'PASS' if p else 'FAIL'}")
    print(f"report: {OUT_REPORT.relative_to(REPO_ROOT)}")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
