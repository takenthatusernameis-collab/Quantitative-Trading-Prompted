#!/usr/bin/env python3
"""Run a command with an idle timeout and capture non-secret process diagnostics.

The caller owns the workflow-wide cutoff. Child output resets the idle timer.
While output is silent, lightweight process/system snapshots are retained in
memory and emitted only when the watchdog fires (or receives a termination
signal), so diagnostic messages cannot accidentally reset the idle timer.
Command lines and environment variables are intentionally not collected.
"""

from __future__ import annotations

import argparse
import io
import os
import selectors
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
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
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    # Also terminate descendants that may have inherited the output pipe.
    _signal_process_group(process, signal.SIGKILL)
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        print("[idle-watchdog] Child process did not exit after SIGKILL.", file=sys.stderr, flush=True)


def _run_diagnostic_command(args: list[str], timeout: float = 2.0) -> str:
    try:
        result = subprocess.run(
            args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=timeout,
            check=False,
        )
        output = result.stdout.strip()
        if result.returncode != 0:
            return f"(exit {result.returncode})\n{output}"
        return output or "(no output)"
    except FileNotFoundError:
        return f"(unavailable: {args[0]} not installed)"
    except subprocess.TimeoutExpired:
        return f"(diagnostic command timed out after {timeout:.1f}s)"
    except OSError as exc:
        return f"(diagnostic command failed: {exc})"


def _capture_snapshot(history: io.StringIO, pgid: int, label: str) -> None:
    """Append a bounded, secret-conscious snapshot without writing to stdout."""
    now = datetime.now(timezone.utc).isoformat()
    history.write(f"\n--- snapshot={label} utc={now} kilo_pgid={pgid} ---\n")

    for path, title in (("/proc/loadavg", "loadavg"), ("/proc/uptime", "uptime")):
        try:
            history.write(f"{title}: {open(path, encoding='utf-8').read().strip()}\n")
        except OSError as exc:
            history.write(f"{title}: unavailable ({exc})\n")

    try:
        with open("/proc/meminfo", encoding="utf-8") as handle:
            wanted = ("MemTotal:", "MemAvailable:", "SwapTotal:", "SwapFree:")
            for line in handle:
                if line.startswith(wanted):
                    history.write(f"memory: {line.strip()}\n")
    except OSError as exc:
        history.write(f"memory: unavailable ({exc})\n")

    ps_output = _run_diagnostic_command([
        "ps", "-eo",
        "pid=,ppid=,pgid=,stat=,etime=,time=,%cpu=,%mem=,wchan:24=,comm=",
    ])
    members: list[tuple[int, str]] = []
    for line in ps_output.splitlines():
        columns = line.split(None, 9)
        if len(columns) >= 3 and columns[2] == str(pgid):
            try:
                members.append((int(columns[0]), line))
            except ValueError:
                continue

    history.write("process_group_members: pid ppid pgid stat elapsed cpu_time cpu_pct mem_pct wait_channel command_name\n")
    if members:
        for pid, line in members:
            history.write(f"  {line}\n")
        # Capture selected /proc fields only. Avoid command lines and environment
        # variables, which can accidentally contain prompt material or secrets.
        selected = (
            "Name:", "State:", "Pid:", "PPid:", "Threads:", "VmRSS:",
            "voluntary_ctxt_switches:", "nonvoluntary_ctxt_switches:",
        )
        for pid, _line in members:
            status_path = f"/proc/{pid}/status"
            history.write(f"proc_status pid={pid}: ")
            try:
                values = []
                with open(status_path, encoding="utf-8") as handle:
                    for row in handle:
                        if row.startswith(selected):
                            values.append(row.strip())
                history.write(" | ".join(values) if values else "(selected fields unavailable)")
            except OSError as exc:
                history.write(f"(unavailable: {exc})")
            try:
                fd_count = len(os.listdir(f"/proc/{pid}/fd"))
                history.write(f" | open_fd_count={fd_count}")
            except OSError as exc:
                history.write(f" | open_fd_count=unavailable ({exc})")
            history.write("\n")
    else:
        history.write("  (no processes currently found in the Kilo process group)\n")
        history.write(f"  ps_diagnostic: {ps_output[:1200]}\n")

    # Show TCP connection state only for sockets attributed to this process
    # group. This helps distinguish a sleeping process with an open request
    # from a process doing CPU work. No environment variables or argv are read.
    ss_path = shutil.which("ss")
    if ss_path and members:
        socket_output = _run_diagnostic_command([ss_path, "-tpn"], timeout=2.0)
        member_ids = [pid for pid, _line in members]
        socket_lines = [
            line for line in socket_output.splitlines()
            if any(f"pid={pid}," in line for pid in member_ids)
        ]
        history.write("process_group_tcp_sockets:\n")
        if socket_lines:
            for line in socket_lines[:40]:
                history.write(f"  {line}\n")
        else:
            history.write("  (no TCP sockets attributed to this process group, or socket ownership unavailable)\n")
    else:
        history.write("process_group_tcp_sockets: unavailable (ss missing or process group empty)\n")


def _emit_diagnostics(history: io.StringIO) -> None:
    print("\n=== KILO_IDLE_DIAGNOSTICS_BEGIN ===", flush=True)
    print(
        "The following samples were collected while child output was silent. "
        "Only process names, process states, selected counters, system load/memory, "
        "and process-attributed TCP socket summaries are included; argv and environment are omitted.",
        flush=True,
    )
    payload = history.getvalue().strip()
    print(payload if payload else "(no process snapshots were collected)", flush=True)
    print("=== KILO_IDLE_DIAGNOSTICS_END ===\n", flush=True)


def _parse_args(argv: Sequence[str]) -> tuple[int, int, list[str]]:
    try:
        divider = list(argv).index("--")
    except ValueError as exc:
        raise SystemExit(
            "usage: kilo-invoke-with-idle-timeout.py "
            "--idle-timeout-seconds N [--diagnostic-sample-interval-seconds N] -- COMMAND [ARGS...]"
        ) from exc

    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--idle-timeout-seconds", type=int, default=900)
    parser.add_argument("--diagnostic-sample-interval-seconds", type=int, default=60)
    options = parser.parse_args(list(argv[:divider]))
    command = list(argv[divider + 1 :])
    if options.idle_timeout_seconds < 1:
        parser.error("--idle-timeout-seconds must be at least 1")
    if options.diagnostic_sample_interval_seconds < 1:
        parser.error("--diagnostic-sample-interval-seconds must be at least 1")
    if not command:
        parser.error("a command is required after --")
    return options.idle_timeout_seconds, options.diagnostic_sample_interval_seconds, command


def main(argv: Sequence[str] | None = None) -> int:
    global _requested_signal
    idle_timeout, sample_interval, command = _parse_args(sys.argv[1:] if argv is None else argv)
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
    last_snapshot = last_output
    history = io.StringIO()
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    _capture_snapshot(history, process.pid, "started")

    try:
        while True:
            now = time.monotonic()
            if _requested_signal is not None:
                print(
                    f"[idle-watchdog] Received signal {_requested_signal}; collecting diagnostics before termination.",
                    flush=True,
                )
                _capture_snapshot(history, process.pid, "termination-signal")
                _emit_diagnostics(history)
                _terminate_process_group(process)
                return 128 + _requested_signal

            idle_for = now - last_output
            remaining_idle = idle_timeout - idle_for
            if remaining_idle <= 0:
                print(
                    f"[idle-watchdog] Kilo invocation idle timeout: no child output for "
                    f"{idle_timeout} seconds; collecting diagnostics before terminating this invocation.",
                    flush=True,
                )
                _capture_snapshot(history, process.pid, "idle-timeout")
                _emit_diagnostics(history)
                _terminate_process_group(process)
                print(
                    "[idle-watchdog] Child process group termination attempted; "
                    "the controller can now preserve the session log and checkpoint.",
                    flush=True,
                )
                return 124

            remaining_sample = sample_interval - (now - last_snapshot)
            select_timeout = min(1.0, remaining_idle, max(0.0, remaining_sample))
            if not selector.get_map():
                if process.poll() is not None:
                    return process.wait()
                time.sleep(max(0.01, select_timeout))
                events = []
            else:
                events = selector.select(timeout=select_timeout)

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
                    _capture_snapshot(history, process.pid, "parent-pipe-closed")
                    _terminate_process_group(process)
                    return 141
                last_output = time.monotonic()

            if process.poll() is not None and not selector.get_map():
                return process.wait()

            now = time.monotonic()
            if now - last_snapshot >= sample_interval:
                _capture_snapshot(history, process.pid, "silent-period")
                last_snapshot = now
    finally:
        selector.close()
        if process.poll() is None:
            _terminate_process_group(process)
        process.stdout.close()


if __name__ == "__main__":
    raise SystemExit(main())
