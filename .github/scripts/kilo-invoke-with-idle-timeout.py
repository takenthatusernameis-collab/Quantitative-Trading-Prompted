#!/usr/bin/env python3
"""Run a command and terminate it if it stops producing output.

The caller owns the overall workflow cutoff. This watchdog only bounds an
individual silent/stalled invocation and forwards child output unchanged.
"""

from __future__ import annotations

import argparse
import os
import selectors
import signal
import subprocess
import sys
import time
from typing import Sequence

_requested_signal: int | None = None


def _handle_signal(signum: int, _frame: object) -> None:
    global _requested_signal
    _requested_signal = signum


def _signal_process_group(process: subprocess.Popen[bytes], signum: int) -> None:
    try:
        os.killpg(process.pid, signum)
    except ProcessLookupError:
        pass
    except OSError as exc:
        print(f"[idle-watchdog] Unable to signal child process group: {exc}", file=sys.stderr, flush=True)


def _terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    _signal_process_group(process, signal.SIGTERM)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass
    # Also terminate descendants that may have inherited the output pipe.
    _signal_process_group(process, signal.SIGKILL)
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        print("[idle-watchdog] Child process did not exit after SIGKILL.", file=sys.stderr, flush=True)


def _parse_args(argv: Sequence[str]) -> tuple[int, list[str]]:
    try:
        divider = list(argv).index("--")
    except ValueError as exc:
        raise SystemExit(
            "usage: kilo-invoke-with-idle-timeout.py "
            "--idle-timeout-seconds N -- COMMAND [ARGS...]"
        ) from exc

    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--idle-timeout-seconds", type=int, default=900)
    options = parser.parse_args(list(argv[:divider]))
    command = list(argv[divider + 1 :])
    if options.idle_timeout_seconds < 1:
        parser.error("--idle-timeout-seconds must be at least 1")
    if not command:
        parser.error("a command is required after --")
    return options.idle_timeout_seconds, command


def main(argv: Sequence[str] | None = None) -> int:
    global _requested_signal
    idle_timeout, command = _parse_args(sys.argv[1:] if argv is None else argv)
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            start_new_session=True,
        )
    except OSError as exc:
        print(f"[idle-watchdog] Could not start child command: {exc}", file=sys.stderr, flush=True)
        return 127

    assert process.stdout is not None
    last_output = time.monotonic()
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)

    try:
        while True:
            if _requested_signal is not None:
                print(
                    f"[idle-watchdog] Received signal {_requested_signal}; terminating Kilo invocation.",
                    flush=True,
                )
                _terminate_process_group(process)
                return 128 + _requested_signal

            idle_for = time.monotonic() - last_output
            remaining_idle = idle_timeout - idle_for
            if remaining_idle <= 0:
                print(
                    f"[idle-watchdog] Kilo invocation idle timeout: no child output for "
                    f"{idle_timeout} seconds; terminating this invocation while preserving "
                    "the overall workflow cutoff.",
                    flush=True,
                )
                _terminate_process_group(process)
                return 124

            if not selector.get_map():
                if process.poll() is not None:
                    return process.wait()
                time.sleep(min(1.0, remaining_idle))
                continue

            events = selector.select(timeout=min(1.0, remaining_idle))
            for key, _mask in events:
                try:
                    chunk = os.read(key.fileobj.fileno(), 65536)
                except OSError as exc:
                    print(f"[idle-watchdog] Error reading child output: {exc}", file=sys.stderr, flush=True)
                    chunk = b""
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                try:
                    sys.stdout.buffer.write(chunk)
                    sys.stdout.buffer.flush()
                except BrokenPipeError:
                    _terminate_process_group(process)
                    return 141
                last_output = time.monotonic()

            if process.poll() is not None and not selector.get_map():
                return process.wait()
    finally:
        selector.close()
        if process.poll() is None:
            _terminate_process_group(process)
        process.stdout.close()


if __name__ == "__main__":
    raise SystemExit(main())
