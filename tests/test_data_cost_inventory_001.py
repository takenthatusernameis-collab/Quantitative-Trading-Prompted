"""Tests for the data-and-cost inventory (Cycle 912).

The inventory is read-only: it measures the committed cache, the committed cost
configuration and the committed shortlist table, and writes two deterministic
artifacts.  These tests pin the artefacts' existence, the coverage of the
inventory, the agreement of the published cost figures with
``src/backtest/engine.py``, the read-only guarantee on ``data/`` and
``config/``, the immutability of every committed artifact, and determinism.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import pytest  # noqa: E402

from research.data_cost_inventory_001 import (  # noqa: E402
    COST_COMPONENTS,
    build_payload,
    fingerprint,
    parse_committed_shortlist,
    tracked_artifact_hashes,
)
from src.backtest.engine import get_cost_params, get_risk_free_rate  # noqa: E402

TOOL = "research/data_cost_inventory_001.py"
REPORT = REPO / "research" / "reports" / "data_cost_inventory_001.md"
EXPERIMENT = REPO / "research" / "experiments" / "data_cost_inventory_001.md"
RAW_DIR = REPO / "data" / "raw"


def _run_tool(*extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, TOOL, *extra],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def payload() -> dict:
    return build_payload()


@pytest.fixture(scope="module")
def report_text() -> str:
    return REPORT.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def experiment_text() -> str:
    return EXPERIMENT.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Artefacts
# ---------------------------------------------------------------------------
def test_tool_runs_and_passes():
    result = _run_tool()
    assert result.returncode == 0, result.stderr
    assert "OVERALL: PASS" in result.stdout


def test_artifacts_exist():
    assert REPORT.exists()
    assert EXPERIMENT.exists()
    assert REPORT.stat().st_size > 0
    assert EXPERIMENT.stat().st_size > 0


def test_artifacts_contain_no_timestamp():
    """The artefacts are deterministic, so they must not carry a run time."""
    import re

    for path in (REPORT, EXPERIMENT):
        text = path.read_text(encoding="utf-8")
        stamps = re.findall(r"20\d\d-\d\d-\d\d[ T]\d\d:\d\d", text)
        assert not stamps, f"{path.name} carries a timestamp: {stamps[:3]}"


# ---------------------------------------------------------------------------
# Inventory coverage
# ---------------------------------------------------------------------------
def test_report_inventory_covers_every_raw_file(report_text: str):
    raw_files = sorted(p for p in RAW_DIR.rglob("*") if p.is_file())
    assert raw_files, "the raw cache is empty"
    for path in raw_files:
        rel = path.relative_to(RAW_DIR).as_posix()
        assert f"data/raw/{rel}" in report_text, f"{rel} is missing from the report"


def test_report_inventory_lists_measured_facts(report_text: str, payload: dict):
    for item in payload["inventory"]:
        row = f"| `data/raw/{item['path']}` |"
        assert row in report_text, f"no inventory row for {item['path']}"
        assert item["sha256"][:16] in report_text
        assert str(item["rows"]) in report_text
        assert item["first_date"] in report_text
        assert item["last_date"] in report_text


def test_crypto_funding_files_are_inventoried(report_text: str):
    funding = sorted(p.name for p in (RAW_DIR / "crypto").glob("*funding*.parquet"))
    assert len(funding) == 4
    for name in funding:
        assert f"data/raw/crypto/{name}" in report_text


def test_measured_cache_integrity(payload: dict):
    totals = payload["totals"]
    assert totals["raw_files"] == 35
    assert totals["missing_prices"] == 0
    assert totals["duplicate_timestamps"] == 0
    # The only sub-daily series in the cache are the 8-hourly crypto funding files.
    assert totals["subdaily_files"] == 4
    assert totals["subdaily_equity_files"] == 0


def test_crypto_manifest_digests_match(payload: dict):
    manifest = payload["manifest"]
    assert manifest["total"] == 8
    assert manifest["matched"] == manifest["total"]
    assert all(check["status"] == "MATCH" for check in manifest["checks"])


# ---------------------------------------------------------------------------
# Cost model
# ---------------------------------------------------------------------------
def test_cost_figures_match_the_engine(report_text: str):
    commission, slippage = get_cost_params()
    risk_free = get_risk_free_rate()
    assert f"{commission * 10000:.1f} bps per trade" in report_text
    assert f"{slippage * 10000:.1f} bps per trade" in report_text
    assert f"{(commission + slippage) * 10000:.1f} bps" in report_text
    assert f"{risk_free * 100:.2f}% annual" in report_text


def test_unconfigured_cost_components_are_reported(payload: dict, report_text: str):
    coverage = payload["cost_model"]["component_coverage"]
    for component in ("bid_ask_spread", "roll", "market_impact", "latency", "margin"):
        assert coverage[component] == [], f"{component} unexpectedly has a config key"
        assert "NOT CONFIGURED" in report_text
    # Borrow is priced, but only by one candidate's own pre-registered
    # assumption (Cycle 936, pairs_001); it is not part of the shared cost
    # model, and the report must say where the price comes from.
    borrow = coverage["borrow"]
    assert borrow, "the pairs candidate's explicit borrow assumption must be measured"
    assert {entry["file"] for entry in borrow} == {"pairs_candidate_001.yaml"}
    assert all(entry["value"] == 25.0 for entry in borrow)
    assert "borrow" in report_text
    for component, _ in COST_COMPONENTS:
        assert component in payload["cost_model"]["component_coverage"]


def test_a_rule_parameter_is_not_counted_as_a_cost(payload: dict):
    coverage = payload["cost_model"]["component_coverage"]
    # `data_quality.roll_window_sessions_per_event` and `roll_detector` name
    # the roll *rule* of the leadlag candidate; they are not a price and must
    # not close the futures-roll cost gap.
    assert coverage["roll"] == []
    assert coverage["market_impact"] == []


# ---------------------------------------------------------------------------
# Shortlist
# ---------------------------------------------------------------------------
def test_shortlist_is_internally_consistent(payload: dict):
    rows = payload["shortlist"]
    assert len(rows) == 10
    for row in rows:
        scores = row["scores"]
        assert set(scores) == {"a", "b", "c", "d", "e", "f", "g"}
        assert row["total"] == sum(scores.values())
        assert row["total"] <= 35
        assert row["verdict"]
        assert row["verdict_citation"]
        for override in row["overrides"]:
            assert override["citation"]
            assert override["reason"]
            assert 1 <= override["revised"] <= 5


def test_shortlist_is_scored_against_the_committed_table(payload: dict):
    committed = parse_committed_shortlist()
    assert len(committed) == 10
    for row in payload["shortlist"]:
        base = committed[row["name"]]
        assert row["committed_rank"] == base["rank"]
        assert row["committed_total"] == base["total"]
        # Criterion (a) may only be lowered by measured evidence.
        assert row["scores"]["a"] <= base["scores"]["a"]


def test_every_rejected_segment_has_a_reason(payload: dict, report_text: str):
    rejections = payload["rejections"]
    assert len(rejections) >= 6
    for item in rejections:
        assert item["segment"]
        assert item["ground"]
        assert len(item["reason"]) > 40
        assert item["citation"]
        assert item["segment"] in report_text


def test_report_records_the_shortlist_table(report_text: str, payload: dict):
    for row in payload["shortlist"]:
        assert row["name"] in report_text
        assert f"**{row['total']}/35**" in report_text


def test_experiment_record_references_the_report(experiment_text: str):
    assert "data_cost_inventory_001" in experiment_text
    assert "research/data_cost_inventory_001.py" in experiment_text
    assert "python -m pytest -q tests/test_data_cost_inventory_001.py" in experiment_text


# ---------------------------------------------------------------------------
# Read-only guarantee and determinism
# ---------------------------------------------------------------------------
def test_data_and_config_are_byte_identical_before_and_after():
    before_data = fingerprint(REPO / "data")
    before_config = fingerprint(REPO / "config")
    result = _run_tool()
    assert result.returncode == 0, result.stderr
    assert fingerprint(REPO / "data") == before_data
    assert fingerprint(REPO / "config") == before_config


def test_committed_artifacts_are_byte_identical_before_and_after():
    before = tracked_artifact_hashes()
    assert before, "no committed artifacts were found"
    result = _run_tool()
    assert result.returncode == 0, result.stderr
    after = tracked_artifact_hashes()
    assert after == before
    if "research/reports/data_cost_inventory_001.md" in before:
        assert _sha256(REPORT) == before["research/reports/data_cost_inventory_001.md"]


def test_two_consecutive_generations_are_identical(tmp_path: Path):
    first_report = tmp_path / "report_1.md"
    first_experiment = tmp_path / "experiment_1.md"
    second_report = tmp_path / "report_2.md"
    second_experiment = tmp_path / "experiment_2.md"

    result = _run_tool(
        "--report-out", str(first_report),
        "--experiment-out", str(first_experiment),
    )
    assert result.returncode == 0, result.stderr
    result = _run_tool(
        "--report-out", str(second_report),
        "--experiment-out", str(second_experiment),
    )
    assert result.returncode == 0, result.stderr

    assert first_report.read_bytes() == second_report.read_bytes()
    assert first_experiment.read_bytes() == second_experiment.read_bytes()
    # The committed artefacts are the same bytes as a fresh generation.
    assert first_report.read_bytes() == REPORT.read_bytes()
    assert first_experiment.read_bytes() == EXPERIMENT.read_bytes()


# ---------------------------------------------------------------------------
# Fail-closed behaviour
# ---------------------------------------------------------------------------
def test_fails_closed_on_an_empty_raw_cache(tmp_path: Path):
    empty_raw = tmp_path / "raw"
    empty_raw.mkdir()
    result = _run_tool(
        "--raw-dir", str(empty_raw),
        "--report-out", str(tmp_path / "report.md"),
        "--experiment-out", str(tmp_path / "experiment.md"),
    )
    assert result.returncode != 0
    assert "ERROR" in result.stderr
    assert not (tmp_path / "report.md").exists()
    assert not (tmp_path / "experiment.md").exists()


def test_fails_closed_on_a_missing_raw_cache(tmp_path: Path):
    result = _run_tool(
        "--raw-dir", str(tmp_path / "does-not-exist"),
        "--report-out", str(tmp_path / "report.md"),
        "--experiment-out", str(tmp_path / "experiment.md"),
    )
    assert result.returncode != 0
    assert "ERROR" in result.stderr
    assert not (tmp_path / "report.md").exists()
    assert not (tmp_path / "experiment.md").exists()
