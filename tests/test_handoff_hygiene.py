"""Regression guard for repository-root handoff hygiene.

Why this exists
---------------
Repeated corrective invocations whose only permitted work was read-only (a hard
clock gate blocked the mutating paper-trading extension) each wrote a new
``CORRECTIVE_HANDOFF_*.md`` file into the repository root. That accumulated 760
per-invocation handoffs at the top level, so every session's ``git status`` and
every reviewer's diff was dominated by handoff noise and no session could tell
substantive change from bookkeeping.

The one canonical current handoff (``CORRECTIVE_HANDOFF_CURRENT.md``) plus the
per-gate records (``CORRECTIVE_HANDOFF_POSTGATE_<YYYYMMDD>.md``) are load-bearing:
``tests/test_post_gate_handoff_consistency.py`` globs the latter at the root and
``scripts/post_gate_orchestrator.sh`` writes them there. Everything else is
historical and belongs in ``research/handoffs/archive/``.

This guard is read-only: it never writes, never touches ``data/raw``, and never
moves files. It fails closed so the root cannot silently re-accumulate
per-invocation handoffs.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_DIR = REPO_ROOT / "research" / "handoffs" / "archive"

_CANONICAL_CURRENT = "CORRECTIVE_HANDOFF_CURRENT.md"

# Root gate records: CORRECTIVE_HANDOFF_POSTGATE_<YYYYMMDD>.md, optionally with
# the ``_pregate_backup`` suffix used by the orchestrator's backup path.
_ROOT_POSTGATE_RE = re.compile(
    r"^CORRECTIVE_HANDOFF_POSTGATE_\d{8}(_pregate_backup)?\.md$"
)


def _root_handoffs() -> list[Path]:
    return sorted(REPO_ROOT.glob("CORRECTIVE_HANDOFF_*.md"))


def test_root_holds_only_canonical_handoffs() -> None:
    """Root may contain only the current handoff and per-gate records."""
    unexpected = [
        p.name
        for p in _root_handoffs()
        if p.name != _CANONICAL_CURRENT and not _ROOT_POSTGATE_RE.match(p.name)
    ]
    assert not unexpected, (
        "per-invocation handoffs must live in research/handoffs/archive/, "
        f"found at repository root: {unexpected[:5]}"
        + (f" (+{len(unexpected) - 5} more)" if len(unexpected) > 5 else "")
    )


def test_single_canonical_current_handoff() -> None:
    """Exactly one canonical current handoff exists at the root."""
    current = [p for p in _root_handoffs() if p.name == _CANONICAL_CURRENT]
    assert len(current) == 1, (
        f"expected exactly one {_CANONICAL_CURRENT}, found {len(current)}"
    )
    assert current[0].stat().st_size > 0, f"{_CANONICAL_CURRENT} is empty"


def test_gate_records_present_for_the_consistency_guard() -> None:
    """The post-gate handoff consistency guard depends on root gate records."""
    gate_records = [
        p for p in _root_handoffs() if p.name != _CANONICAL_CURRENT
    ]
    assert gate_records, (
        "no CORRECTIVE_HANDOFF_POSTGATE_<YYYYMMDD>.md at the repository root; "
        "tests/test_post_gate_handoff_consistency.py and "
        "scripts/post_gate_orchestrator.sh require them"
    )


def test_archive_preserves_historical_handoffs() -> None:
    """Archived history is kept, not deleted."""
    assert ARCHIVE_DIR.is_dir(), f"archive directory missing: {ARCHIVE_DIR}"
    archived = sorted(ARCHIVE_DIR.glob("CORRECTIVE_HANDOFF_*.md"))
    assert archived, (
        "archive is empty; historical handoffs must be moved, never deleted"
    )
    assert all(p.stat().st_size > 0 for p in archived), (
        "archive contains an empty handoff file"
    )
