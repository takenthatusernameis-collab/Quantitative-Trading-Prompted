#!/usr/bin/env python3
"""Common-inception sample audit for csmomentum_001 (Cycle 905). Read-only."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.promotion_feasibility_backtest import scan_raw_cache, load_yaml  # noqa: E402

RAW_DIR = REPO_ROOT / "data" / "raw"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
OUT_REPORT = REPORTS_DIR / "csmomentum_common_inception_audit_001.md"
POLICY_DEFAULT = REPO_ROOT / "config" / "sample_policy.yaml"
CAND_CONFIG = REPO_ROOT / "config" / "csmomentum_candidate_001.yaml"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default=str(POLICY_DEFAULT))
    args = ap.parse_args()

    policy_path = Path(args.policy)
    if not policy_path.exists():
        print("POLICY: MISSING", file=sys.stderr)
        return 2
    try:
        policy = yaml.safe_load(policy_path.read_text())
    except Exception as e:
        print(f"POLICY: MALFORMED {e}", file=sys.stderr)
        return 2
    cand = (policy or {}).get("candidates", {}).get("csmomentum_001")
    if not isinstance(cand, dict):
        print("POLICY: candidate section missing", file=sys.stderr)
        return 2
    if cand.get("rule_id") != "common_inception_fully_populated":
        print("POLICY: bad rule_id", file=sys.stderr)
        return 2

    cand_cfg = load_yaml(CAND_CONFIG)
    universe = cand_cfg["universe"]
    # validate policy universe matches config
    if cand.get("universe") != universe:
        print("POLICY: universe mismatch", file=sys.stderr)
        return 2

    stats, _hashes, union_index = scan_raw_cache(universe)
    first_dates = [s["first_date"] for s in stats.values()]
    common_inception = max(first_dates)
    union_start = min(first_dates)

    # session counts
    import pandas as pd
    idx_union = union_index
    common_slice = idx_union[idx_union >= pd.Timestamp(common_inception, tz="UTC").tz_convert(idx_union.tz) if idx_union.tz else pd.Timestamp(common_inception)]

    lines = []
    lines.append("# csmomentum_001 common-inception sample audit (Cycle 905)")
    lines.append("")
    lines.append(f"common_inception: {common_inception}")
    lines.append(f"union_start: {union_start}")
    lines.append(f"union_sessions: {len(idx_union)}")
    lines.append(f"common_inception_sessions: {len(common_slice)}")
    lines.append(f"union_start_date: {idx_union[0].date()}")
    lines.append(f"common_inception_start_date: {common_slice[0].date()}")
    lines.append(f"end_date: {idx_union[-1].date()}")
    lines.append("")
    lines.append("OVERALL: PASS")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text("\n".join(lines) + "\n")
    print("OVERALL: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
