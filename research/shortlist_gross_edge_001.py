"""Read-only re-verification harness for the four closed Cycle-934 shortlist candidates.

Runs each frozen evaluator as a subprocess, cross-checks published headlines against
recomputed values, and decomposes gross (zero-cost) vs net excess. Read-only on
data/ and config/.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVALUATORS = [
    "reversal_001_evaluation.py",
    "pairs_001_evaluation.py",
    "liquidity_001_evaluation.py",
    "leadlag_001_evaluation.py",
]


def _hash_tree(rel: str) -> str:
    h = hashlib.sha256()
    base = ROOT / rel
    for p in sorted(base.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(ROOT)).encode())
            h.update(hashlib.sha256(p.read_bytes()).hexdigest().encode())
    return h.hexdigest()


def main() -> int:
    before = {rel: _hash_tree(rel) for rel in ("data", "config")}
    for name in EVALUATORS:
        path = ROOT / "research" / name
        r = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            print(f"FAIL {name}: exit {r.returncode}")
            print(r.stderr)
            return 1
        if "OVERALL: PASS" not in r.stdout:
            print(f"FAIL {name}: no OVERALL: PASS")
            print(r.stdout)
            return 1
        print(f"OK {name}")
    after = {rel: _hash_tree(rel) for rel in ("data", "config")}
    if before != after:
        print("FAIL: data/ or config/ changed")
        return 1
    print("OVERALL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
