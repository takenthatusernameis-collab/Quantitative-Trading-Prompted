#!/usr/bin/env python3
"""Classify Kilo controller terminal state without confusing a shell exit with durable progress."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable

CONTROL_ONLY_PATHS = {".kilo/TWO_AGENT_ONCE", ".kilo/SKIP_NEXT_ROUTINE_KILO"}
CONTROL_ONLY_PREFIXES = (".kilo-runtime/", ".kilo/supervisor-reports/")
IGNORED_SUFFIXES = (
    ".pyc", ".pyo", ".sqlite", ".sqlite3", ".db",
    ".sqlite-wal", ".sqlite-shm", ".sqlite3-wal", ".sqlite3-shm",
    ".db-wal", ".db-shm", ".tmp",
)
IGNORED_EXACT_PATHS = {".coverage", "coverage.xml"}


def _status_path(line: str) -> str:
    """Return the path from a Git porcelain-v1 record."""
    if len(line) < 4:
        return ""
    path = line[3:].strip()
    if " -> " in path:
        path = path.rsplit(" -> ", 1)[1].strip()
    if len(path) >= 2 and path[0] == path[-1] == '"':
        path = path[1:-1]
    return path


def _ignored_generated_path(path: str) -> bool:
    if not path:
        return True
    if path in CONTROL_ONLY_PATHS or path.startswith(CONTROL_ONLY_PREFIXES):
        return True
    if path in IGNORED_EXACT_PATHS or path.endswith(IGNORED_SUFFIXES):
        return True
    basename = path.rsplit("/", 1)[-1]
    return basename.startswith("kilo-session-") and basename.endswith(".log")


def project_worktree_is_dirty(status_lines: Iterable[str]) -> bool:
    """Return True if substantive changes remain outside the committed checkpoint."""
    return any(
        bool(line.strip()) and not _ignored_generated_path(_status_path(line))
        for line in status_lines
    )


def classify_outcome(
    *,
    project_progress: bool,
    checkpoint_persisted: bool,
    dirty_project_worktree: bool,
    intentional_noop: bool = False,
) -> tuple[str, int]:
    if intentional_noop:
        return "intentional_noop", 0
    if not checkpoint_persisted or dirty_project_worktree:
        return "persistence_failure", 1
    if project_progress:
        return "verified_progress", 0
    return "no_progress_failure", 1


def emit_github_outputs(output_path: str, status: str, cutoff: bool, checkpoint_sha: str) -> None:
    if not output_path:
        return
    with Path(output_path).open("a", encoding="utf-8") as handle:
        handle.write(f"terminal_status={status}\n")
        handle.write(f"cutoff_reached={'true' if cutoff else 'false'}\n")
        handle.write(f"terminal_checkpoint_sha={checkpoint_sha}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-progress", choices=("0", "1"), default="0")
    parser.add_argument("--checkpoint-persisted", choices=("0", "1"), default="0")
    parser.add_argument("--git-status-file")
    parser.add_argument("--cutoff", choices=("0", "1"), default="0")
    parser.add_argument("--intentional-noop", action="store_true")
    parser.add_argument("--checkpoint-sha", default="unknown", help="Full Git SHA for the terminal local HEAD")
    parser.add_argument("--output", default="")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64}|unknown)", args.checkpoint_sha):
        parser.error("--checkpoint-sha must be a full lowercase Git SHA or unknown")

    dirty = False
    if args.git_status_file:
        try:
            status_text = Path(args.git_status_file).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(f"Unable to read final Git status ({type(exc).__name__}); failing closed.", file=sys.stderr)
            dirty = True
        else:
            dirty = project_worktree_is_dirty(status_text.splitlines())

    status, rc = classify_outcome(
        project_progress=args.project_progress == "1",
        checkpoint_persisted=args.checkpoint_persisted == "1",
        dirty_project_worktree=dirty,
        intentional_noop=args.intentional_noop,
    )
    try:
        emit_github_outputs(args.output, status, args.cutoff == "1", args.checkpoint_sha)
    except OSError as exc:
        print(f"Unable to emit GitHub terminal outputs ({type(exc).__name__}).", file=sys.stderr)
        return 1

    if status == "verified_progress":
        print("Kilo terminal outcome: verified_progress; meaningful progress and remote checkpoint are verified.")
    elif status == "intentional_noop":
        print("Kilo terminal outcome: intentional_noop; no worker progress was expected.")
    elif status == "persistence_failure":
        print("::error::Kilo terminal outcome: persistence_failure; substantive worktree changes or checkpoint persistence remain unverified.")
    else:
        print("::error::Kilo terminal outcome: no_progress_failure; no meaningful durable project progress was confirmed.")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
