#!/usr/bin/env python3
"""Correct the stored ``rolling_max_dd_63d`` to the trailing-63-session window.

Cycle 1140: ``src/simulation/paper_trading.run_daily_paper_update`` computed
``rolling_max_dd`` over the *full* history (``cumprod(1+r)`` over every session)
and stored it under a field whose name, docstring and the promotion gate
(``config/promotion_gates.yaml`` "rolling_63d_max_dd") all describe a
*trailing 63-session* drawdown. Its sibling ``rolling_sharpe_63d`` already used
the trailing 63 sessions, so the two aggregates were measured on different
windows.

This script rewrites ONLY that one field in the canonical state, using the
trailing-63 definition, and asserts that the rest of the state is preserved.
It is safe to re-run: it is idempotent when the field already holds the
corrected value.

Usage::

    python research/correct_rolling_max_dd_field.py [--dry-run]

The script is read-only with respect to ``data/raw`` and the network. It opens
the canonical state, rewrites it atomically (the same ``tempfile + os.replace``
pattern as ``PaperTradingState.to_yaml``), and records a before/after SHA-256.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = REPO_ROOT / "data" / "processed" / "paper_trading_state.yaml"
WINDOW = 63


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def trailing_63_max_dd(returns: list[float]) -> float:
    recent = np.asarray(returns[-WINDOW:], dtype=float)
    cum = np.cumprod(1.0 + recent)
    peak = np.maximum.accumulate(cum)
    return float((cum / peak - 1.0).min())


def full_history_max_dd(returns: list[float]) -> float:
    arr = np.asarray(returns, dtype=float)
    cum = np.cumprod(1.0 + arr)
    peak = np.maximum.accumulate(cum)
    return float((cum / peak - 1.0).min())


def _atomic_write(path: Path, payload: str) -> None:
    """Write ``payload`` to ``path`` atomically (tempfile + os.replace)."""
    fd, tmp_path = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    before_sha = sha256_file(STATE_PATH)
    with open(STATE_PATH) as fh:
        doc = yaml.safe_load(fh) or {}

    returns = [float(r) for r in (doc.get("cumulative_returns") or [])]
    if len(returns) < 2:
        print("state has no return history; nothing to correct")
        return 1

    stored = float(doc.get("rolling_max_dd_63d", 0.0))
    corrected = trailing_63_max_dd(returns)
    full = full_history_max_dd(returns)

    print(f"return sessions:           {len(returns)}")
    print(f"stored rolling_max_dd_63d: {stored:.12f}")
    print(f"full-history max dd:       {full:.12f}  (the old, wrong value)")
    print(f"trailing-63 max dd:       {corrected:.12f}  (corrected value)")
    print(f"stored == full-history:    {abs(stored - full) <= 1e-12}")
    print(f"stored == trailing-63:     {abs(stored - corrected) <= 1e-12}")

    if abs(stored - corrected) <= 1e-12:
        print("field already holds the corrected value; no rewrite needed")
        return 0

    if args.dry_run:
        print("DRY RUN: no state file written")
        return 0

    # Rewrite ONLY the one field; rebuild the document from the parsed mapping so
    # every other key, ordering and value is preserved except for the corrected
    # field.
    doc["rolling_max_dd_63d"] = corrected
    payload = yaml.safe_dump(doc, sort_keys=False)
    _atomic_write(STATE_PATH, payload)

    after_sha = sha256_file(STATE_PATH)
    print(f"state sha256 before: {before_sha}")
    print(f"state sha256 after:  {after_sha}")
    print("rewrote rolling_max_dd_63d only")
    return 0


if __name__ == "__main__":
    sys.exit(main())