"""Regression tests for the published sample definition of the long-sample artifact.

``research/promotion_feasibility_backtest.py`` publishes the sample it
actually computed.  ``src/backtest/engine.py:run_backtest`` does not slice the
price frame it loads, so the realized sample of the incumbent's long-sample
backtest is the **union calendar** of the raw cache (``data/raw/*.parquet``),
not the common inception date the artifact used to label it with.

These tests assert that:

* the published realized window equals the union index of the raw cache,
  computed independently here, so the artifact cannot describe a sample it did
  not compute,
* the published label is the common inception (max of the per-symbol first
  dates) and is published as a *label*, next to the realized window,
* the cache fingerprint is derived from the files on disk (a later append is
  therefore visible as a fingerprint change and not as a silent stale value),
* the reference-sample anchors are re-derived and pass, and
* the tool prints the realized window and reproduces the committed report
  byte-identically.

No window date or session count is pinned: both sides of every comparison are
recomputed from the raw cache, so the invariants survive the next data append.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import research.promotion_feasibility_backtest as pf  # noqa: E402

REPORT = ROOT / "research" / "reports" / "promotion_feasibility_backtest_001.md"
UNIVERSE = ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"]


def _frames() -> dict[str, pd.DataFrame]:
    return {
        symbol: pd.read_parquet(ROOT / "data" / "raw" / f"{symbol}.parquet")
        for symbol in UNIVERSE
    }


def _union_index() -> pd.DatetimeIndex:
    """The union calendar of the raw cache, computed independently of the tool."""
    frames = _frames()
    return pd.DatetimeIndex(sorted(set().union(*[df.index for df in frames.values()])))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _published_sample() -> dict:
    """The ``sample`` block the committed report publishes."""
    text = REPORT.read_text()
    marker = "## Sample definition"
    assert marker in text, "the report no longer publishes a sample definition"
    start = text.index("```json", text.index(marker)) + len("```json")
    end = text.index("```", start)
    return json.loads(text[start:end])


def test_published_realized_window_equals_independent_union_index():
    union = _union_index()
    sample = _published_sample()
    assert sample["realized_start_date"] == union.min().date().isoformat()
    assert sample["realized_end_date"] == union.max().date().isoformat()
    assert sample["realized_session_count"] == len(union)
    # the historical key names describe the same (realized) sample
    assert sample["start_date"] == sample["realized_start_date"]
    assert sample["end_date"] == sample["realized_end_date"]
    assert sample["session_count"] == sample["realized_session_count"]
    fingerprint = sample["union_index_fingerprint"]
    assert fingerprint["first_date"] == union.min().date().isoformat()
    assert fingerprint["last_date"] == union.max().date().isoformat()
    assert fingerprint["count"] == len(union)


def test_published_label_is_the_common_inception():
    frames = _frames()
    label_start = max(df.index.min() for df in frames.values()).date().isoformat()
    label_end = min(df.index.max() for df in frames.values()).date().isoformat()
    sample = _published_sample()
    assert sample["label_start_date"] == label_start
    assert sample["label_end_date"] == label_end
    # the label and the realized window are published side by side, not mixed
    assert "realized_start_date" in sample and "realized_end_date" in sample
    assert "realized_session_count" in sample


def test_cache_fingerprint_is_derived_from_the_raw_cache():
    frames = _frames()
    fingerprint = _published_sample()["cache_fingerprint"]["per_symbol"]
    assert set(fingerprint) == set(UNIVERSE)
    for symbol, df in frames.items():
        entry = fingerprint[symbol]
        assert entry["rows"] == len(df)
        assert entry["first_date"] == df.index.min().date().isoformat()
        assert entry["last_date"] == df.index.max().date().isoformat()
        assert entry["sha256"] == _sha256(ROOT / "data" / "raw" / f"{symbol}.parquet")


def test_reference_sample_checks_are_published_and_pass():
    checks = _published_sample()["reference_sample_checks"]
    names = {check["name"] for check in checks}
    assert names == {"incumbent_reference_sample", "paper_record_reference_sample"}
    for check in checks:
        assert check["pass"], check


def test_tool_publishes_the_realized_window_and_reproduces_the_report():
    before = REPORT.read_bytes()
    proc = subprocess.run(
        [sys.executable, "research/promotion_feasibility_backtest.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "OVERALL: PASS" in proc.stdout
    assert "decision=NO-GO" in proc.stdout

    union = _union_index()
    assert (
        f"realized {union.min().date().isoformat()}..{union.max().date().isoformat()} "
        f"({len(union)} sessions)" in proc.stdout
    )
    assert "realized window equals raw-cache union index: True" in proc.stdout
    assert "reference check [incumbent_reference_sample]: PASS" in proc.stdout
    assert "reference check [paper_record_reference_sample]: PASS" in proc.stdout

    assert REPORT.read_bytes() == before, (
        "the promotion report is not reproduced byte-identically: either the code "
        "changed the numbers, or the raw cache changed and the report has to be "
        "re-committed with the refreshed data"
    )


def test_sample_definition_helper_matches_the_raw_cache():
    """The tool's own cache scan agrees with the independent computation."""
    frames = _frames()
    per_symbol_stats, raw_hashes, union = pf.scan_raw_cache(UNIVERSE)
    assert set(per_symbol_stats) == set(UNIVERSE)
    assert set(raw_hashes) == set(UNIVERSE)
    assert union.equals(_union_index())
    for symbol, df in frames.items():
        assert per_symbol_stats[symbol]["row_count"] == len(df)
        assert raw_hashes[symbol] == _sha256(ROOT / "data" / "raw" / f"{symbol}.parquet")
