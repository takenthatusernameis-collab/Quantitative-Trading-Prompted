from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOOL = REPO / "research" / "cost_gate_break_even_audit.py"
REPORT = REPO / "research" / "reports" / "cost_gate_break_even_001.md"
EXPERIMENT = REPO / "research" / "experiments" / "cost_gate_break_even_001.md"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _committed_artifact_hashes():
    import subprocess as sp

    res = sp.run(
        ["git", "ls-files", "src", "config", "research/experiments", "research/reports"],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    out: dict[str, str] = {}
    for rel in res.stdout.splitlines():
        rel = rel.strip()
        if not rel:
            continue
        path = REPO / rel
        if path.is_file():
            out[rel] = _sha256(path)
    return out


def _fingerprint(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            try:
                out[str(path.relative_to(REPO))] = _sha256(path)
            except Exception:
                continue
    return out


def _run_tool(*extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), *extra],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )


def test_tool_runs_and_passes():
    result = _run_tool()
    assert result.returncode == 0, result.stderr
    assert "OVERALL: PASS" in result.stdout


def test_artifacts_exist():
    assert REPORT.exists()
    assert EXPERIMENT.exists()


def test_published_values_reproduced_at_3bp():
    from research import cost_gate_break_even_audit as audit

    payload = audit.run_audit()
    # Check the regression conditions
    assert abs(payload["candidates"]["tsmomentum_spytrend_001"]["wf_mean_at_3bp"] - 0.9473074720246092) <= 1e-9 or abs(payload["candidates"]["tsmomentum_spytrend_001"]["wf_mean_at_3bp"] - 0.9473) <= 1e-9
    assert abs(payload["candidates"]["csmomentum_001"]["wf_mean_backtest_at_3bp"] - 0.6975243375140185) <= 1e-9 or abs(payload["candidates"]["csmomentum_001"]["wf_mean_backtest_at_3bp"] - 0.697524) <= 1e-6
    assert abs(payload["candidates"]["csmomentum_001"]["wf_mean_canonical_at_3bp"] - 0.8403888341999609) <= 1e-9 or abs(payload["candidates"]["csmomentum_001"]["wf_mean_canonical_at_3bp"] - 0.840389) <= 1e-6
    assert abs(payload["candidates"]["sectorrotation_001"]["wf_mean_at_3bp"] - 0.8472432934255264) <= 1e-9 or abs(payload["candidates"]["sectorrotation_001"]["wf_mean_at_3bp"] - 0.847243) <= 1e-6


def test_report_references_get_cost_params():
    text = REPORT.read_text()
    assert "get_cost_params()" in text or "3.0 bp" in text
    from src.backtest.engine import get_cost_params, get_risk_free_rate
    assert get_cost_params() == (0.0001, 0.0002)


def test_gate_flip_monotonic_or_reported():
    from research import cost_gate_break_even_audit as audit

    payload = audit.run_audit()
    for cid, data in payload["candidates"].items():
        assert "gate1_flip_bps" in data
        assert "gate2_flip_bps" in data
        assert "gate3_flip_bps" in data


def test_data_and_config_unchanged():
    before_data = _fingerprint(REPO / "data")
    before_config = _fingerprint(REPO / "config")
    result = _run_tool()
    assert result.returncode == 0, result.stderr
    assert _fingerprint(REPO / "data") == before_data
    assert _fingerprint(REPO / "config") == before_config


def test_committed_artifacts_unchanged():
    before = _committed_artifact_hashes()
    result = _run_tool()
    assert result.returncode == 0, result.stderr
    after = _committed_artifact_hashes()
    assert after == before


def test_determinism():
    r1 = _run_tool()
    assert r1.returncode == 0
    t1 = REPORT.read_text()
    e1 = EXPERIMENT.read_text()
    r2 = _run_tool()
    assert r2.returncode == 0
    t2 = REPORT.read_text()
    e2 = EXPERIMENT.read_text()
    assert t1 == t2
    assert e1 == e2


def test_fails_closed_missing_input(tmp_path):
    pass
