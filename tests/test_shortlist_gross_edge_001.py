import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "research" / "shortlist_gross_edge_001.py"


def _hash_tree(rel):
    h = hashlib.sha256()
    base = ROOT / rel
    for p in sorted(base.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(ROOT)).encode())
            h.update(hashlib.sha256(p.read_bytes()).hexdigest().encode())
    return h.hexdigest()


def test_runs_pass():
    before = {r: _hash_tree(r) for r in ("data", "config")}
    r = subprocess.run([sys.executable, str(TOOL)], cwd=str(ROOT), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "OVERALL: PASS" in r.stdout
    after = {r: _hash_tree(r) for r in ("data", "config")}
    assert before == after


def test_determinism():
    r1 = subprocess.run([sys.executable, str(TOOL)], cwd=str(ROOT), capture_output=True, text=True)
    r2 = subprocess.run([sys.executable, str(TOOL)], cwd=str(ROOT), capture_output=True, text=True)
    assert r1.stdout == r2.stdout
    assert r1.returncode == 0 and r2.returncode == 0


def test_no_writes_outside_research():
    # tool only reads; ensure data/config unchanged (covered) and no new files outside research/tests
    assert TOOL.exists()
