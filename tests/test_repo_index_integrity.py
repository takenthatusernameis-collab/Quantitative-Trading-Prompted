"""Regression guard for repository index (git) integrity.

A tracked path that is not a valid filesystem path (e.g. an XML tool-call
injection artifact such as ``</rfl:parameter>home/...``) is a repository
corruption defect: it cannot be checked out cleanly, it breaks ``git status`` /
``git restore`` / ``git rm`` for that path, and it silently poisons any
downstream consumer that enumerates tracked files. It was discovered in
HEAD ``d6ad7d5`` (2026-11-15) as a single phantom entry alongside the
canonical ``research/hypotheses/futuresbasis_001.md`` (introduced by commit
``6e2b8b4``).

This guard is read-only and test-only: it never writes, never touches
``data/raw``, and never modifies the index. It fails closed if any tracked
path is not a valid, non-empty relative path composed of ordinary
filesystem characters.

Design notes:
- Ordinary dotfiles (``.gitignore``, ``.gitkeep``, ``.kilo/...``) are valid
  and MUST NOT be flagged. Only ``..`` parent-directory segments and absolute
  / trailing-slash paths are rejected as malformed.
- The index is intentionally NOT compared against ``git ls-tree HEAD``: doing
  so would fail on *any* legitimate staged change during normal development.
  Path validity and uniqueness are the properties that matter here.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Characters that can never appear in a portable repository-relative path.
# This rejects the XML/HTML tag delimiters (``<`` ``>``), quotes, shell and
# regex metacharacters, and all C0 control characters. Ordinary dotfiles
# (``..`` is handled separately, single-dot-prefixed names are fine) pass.
_INVALID_PATH_CHARS = re.compile(r"[\x00-\x1f<>\"'`$\\|&;(){}\[\]]")

# A path is malformed if it is absolute, has a trailing slash, contains an
# empty (``//``) segment, is exactly ``.``, or contains a ``..`` segment.
_INVALID_NAME = re.compile(r"^/|/$|//|^\.$|(^|/)\.\.(/|$)")


def _tracked_paths() -> list[str]:
    """Return tracked paths, NUL-delimited to survive any exotic bytes."""
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "-z"],
        capture_output=True,
        check=True,
    ).stdout
    return [p.decode("utf-8", "surrogateescape") for p in out.split(b"\x00") if p]


def test_no_phantom_tracked_paths() -> None:
    """Every tracked path must be a valid relative path; fail closed otherwise."""
    bad = []
    for p in _tracked_paths():
        if not p or _INVALID_NAME.search(p) or _INVALID_PATH_CHARS.search(p):
            bad.append(repr(p))
    assert not bad, (
        "repository index contains tracked path(s) that are not valid "
        f"filesystem paths: {bad[:10]}"
    )


def test_dotfiles_are_not_flagged() -> None:
    """Ordinary dotfiles must be accepted (guards the guard against false positives)."""
    for good in (
        ".gitignore",
        ".kilo/supervisor-reports/.gitkeep",
        "research/hypotheses/futuresbasis_001.md",
        "src/data/yfinance_fetcher.py",
    ):
        assert not _INVALID_NAME.search(good), f"valid path flagged: {good!r}"
        assert not _INVALID_PATH_CHARS.search(good), f"valid path flagged: {good!r}"
    for bad in ("../escape.md", "/etc/passwd", "a//b", ".", "a/<b>.md"):
        assert _INVALID_NAME.search(bad) or _INVALID_PATH_CHARS.search(bad), (
            f"malformed path NOT flagged: {bad!r}"
        )


def test_canonical_hypothesis_file_present_and_unique() -> None:
    """``research/hypotheses/futuresbasis_001.md`` must be tracked exactly once.

    The defect this guards against was a *duplicate* phantom entry for this
    file: the canonical path was present and correct, but a second, malformed
    entry shadowed it in the index. A single canonical tracking is required.

    The legitimate ``research/experiments/futuresbasis_001.md`` experiment
    record shares the filename, so any *other* path ending in this filename is
    only accepted under a real ``research/`` subdir; a malformed shadow (e.g.
    the ``</rfl:parameter>...`` phantom) is rejected.
    """
    canonical = "research/hypotheses/futuresbasis_001.md"
    paths = _tracked_paths()
    assert paths.count(canonical) == 1, (
        f"expected exactly one tracked {canonical!r}, got {paths.count(canonical)}"
    )
    assert canonical in paths
    assert (REPO_ROOT / "research" / "hypotheses" / "futuresbasis_001.md").is_file()
    for p in paths:
        if p.endswith("futuresbasis_001.md") and p != canonical:
            assert p.startswith(("research/hypotheses/", "research/experiments/")), (
                f"unexpected tracked shadow of futuresbasis_001.md: {p!r}"
            )