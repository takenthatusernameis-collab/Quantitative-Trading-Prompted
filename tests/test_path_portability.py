"""Regression: verification scripts must not hard-code the absolute worktree path.

Cycle 1256: ``research/verify_gate_time_forward_bar.py`` and
``research/verify_monday_extension_path.py`` derived ``ROOT`` from a hard-coded
absolute path (``/home/runner/work/Quantitative-Trading-Prompted/...``) while
``research/verify_live_extension_path.py`` already used ``Path(__file__)``. If the
repository is ever checked out at a different path -- or if the scripts are run
from a copied worktree -- the hard-coded path would resolve to a directory that
does not exist and the scripts would fail silently at the first file read,
rather than at the assertion phase.

This test pins the contract that the three forward/backward verification
scripts all derive their root from ``__file__``, so the scripts are portable
across worktrees. It is a source-level scan, not a subprocess run, so it is
fast and deterministic.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Scripts that must derive their root from __file__ rather than a hard-coded path.
PORTABILITY_TARGETS = [
    "research/verify_gate_time_forward_bar.py",
    "research/verify_monday_extension_path.py",
    "research/verify_live_extension_path.py",
]

# A hard-coded absolute worktree path looks like a Path literal containing the
# repository's own name twice (the GitHub Actions worktree layout). Matching on
# the doubled name avoids false positives from absolute paths that name a
# different, unrelated location.
_HARDCODED_ROOT = re.compile(
    r'Path\(\s*["\']'
    r'(?P<p>[^"\']*Quantitative-Trading-Prompted/Quantitative-Trading-Prompted)'
    r'["\']\s*\)'
)


def _read(path: Path) -> str:
    return path.read_text()


def test_no_script_hardcodes_the_worktree_path() -> None:
    offenders: list[str] = []
    for rel in PORTABILITY_TARGETS:
        text = _read(ROOT / rel)
        for match in _HARDCODED_ROOT.finditer(text):
            offenders.append(f"{rel}: {match.group('p')}")
    assert not offenders, (
        "verification scripts must derive ROOT from Path(__file__), not a "
        f"hard-coded worktree path; offenders: {offenders}"
    )


def test_portable_scripts_derive_root_from_file() -> None:
    """Each target script's ROOT assignment must come from ``__file__``."""
    for rel in PORTABILITY_TARGETS:
        text = _read(ROOT / rel)
        assert (
            "Path(__file__).resolve().parent.parent" in text
        ), f"{rel} does not derive ROOT from Path(__file__)"


def test_verify_live_extension_path_is_the_portable_reference() -> None:
    """The already-portable script must remain portable (regression guard)."""
    text = _read(ROOT / "research" / "verify_live_extension_path.py")
    assert "Path(__file__).resolve().parent.parent" in text
    assert _HARDCODED_ROOT.search(text) is None