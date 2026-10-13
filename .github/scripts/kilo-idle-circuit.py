#!/usr/bin/env python3
"""Persistent circuit breaker for repeated silent Kilo sessions.

Two silent stalls without intervening verified project progress open a
repository-persisted cooldown. The first later/manual invocation is probe-only.
Repeated probe failures exponentially back off, capped at six hours.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_STATE = {
    "consecutive_idle_stalls": 0,
    "cooldown_level": 0,
    "retry_after_epoch": 0,
    "last_stall_utc": None,
    "last_run_id": None,
    "reason": None,
}


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return dict(DEFAULT_STATE)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read idle circuit state at {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"idle circuit state at {path} is not a JSON object")
    result = dict(DEFAULT_STATE)
    result.update(raw)
    for key in ("consecutive_idle_stalls", "cooldown_level", "retry_after_epoch"):
        value = result[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"invalid {key} in idle circuit state at {path}")
    return result


def cooldown_seconds(level: int) -> int:
    return min(1800 * (2 ** max(0, level - 1)), 21600)


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="decide whether this activation may launch Kilo")
    check.add_argument("--state-file", required=True, type=Path)
    check.add_argument("--event", required=True)
    check.add_argument("--now", type=int, default=None, help=argparse.SUPPRESS)

    for name in ("record-stall", "defer-probe"):
        item = subparsers.add_parser(name)
        item.add_argument("--state-file", required=True, type=Path)
        item.add_argument("--count", type=int, required=True)
        item.add_argument("--level", type=int, required=True)
        item.add_argument("--run-id", default="unknown")
        item.add_argument("--now", type=int, default=None, help=argparse.SUPPRESS)

    clear = subparsers.add_parser("clear", help="clear the breaker after verified project progress")
    clear.add_argument("--state-file", required=True, type=Path)

    args = parser.parse_args()
    now = getattr(args, "now", None)
    now = int(time.time()) if now is None else now
    try:
        if args.command == "check":
            state = load_state(args.state_file)
            count = state["consecutive_idle_stalls"]
            level = state["cooldown_level"]
            retry_after = state["retry_after_epoch"]
            if count == 0:
                mode = "normal"
            elif args.event != "workflow_dispatch" and retry_after > now:
                mode = "skip"
            else:
                mode = "probe"
            print(f"{mode}\t{count}\t{level}\t{retry_after}")
            return 0

        if args.command == "clear":
            try:
                args.state_file.unlink()
            except FileNotFoundError:
                pass
            return 0

        state = load_state(args.state_file)
        previous_count = max(args.count, state["consecutive_idle_stalls"])
        previous_level = max(args.level, state["cooldown_level"])
        if args.command == "record-stall":
            count = previous_count + 1
            level = previous_level
            retry_after = 0
            if count >= 2:
                level = max(1, previous_level + 1)
                retry_after = now + cooldown_seconds(level)
            reason = "repeated Kilo idle-output timeout without verified project progress"
        else:
            count = max(2, previous_count)
            level = max(1, previous_level + 1)
            retry_after = now + cooldown_seconds(level)
            reason = "recovery probe failed without verified project progress"

        state.update({
            "consecutive_idle_stalls": count,
            "cooldown_level": level,
            "retry_after_epoch": retry_after,
            "last_stall_utc": datetime.fromtimestamp(now, timezone.utc).isoformat(),
            "last_run_id": str(args.run_id),
            "reason": reason,
        })
        save_state(args.state_file, state)
        print(f"{count}\t{level}\t{retry_after}")
        return 0
    except (OSError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
