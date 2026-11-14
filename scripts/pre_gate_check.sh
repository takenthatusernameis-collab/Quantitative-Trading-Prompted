#!/usr/bin/env bash
# Pre-gate cheap-path checker (durable, read-only, side-effect free).
#
# Why this exists
# ---------------
# NEXT_AGENT_TASK.md's "cheap pre-gate path" tells a session to (1) check the
# gate epoch, (2) hash the state file, (3) confirm `data/raw` is clean, and then
# STOP without re-running the full read-only orchestrator cycle. That path was
# prose-only and unenforced, so several pre-gate sessions ignored it and each
# rewrote the handoff's timestamp/epoch header — producing commits that carry no
# project progress (e.g. 5be09e6 / b5403fc / 6799001, which differ only in the
# "Context — verified baseline" timestamp lines).
#
# This script makes the cheap path a single deterministic, side-effect-free call.
# It NEVER writes a file, never touches `data/raw`, and never runs the extend.
#
# Exit codes
# ----------
#   0  Pre-gate cheap path applies: now < GATE_EPOCH, state hash matches
#      STATE_SHA256, and `data/raw` is clean. The session should STOP (no cycle).
#   3  Check failed: a precondition is unmet (gate already reached, hash drift,
#      or dirty `data/raw`). The caller must inspect and act; do not blindly stop.
#   2  Usage / environment error (missing state file, bad args).
#
# Usage:
#   GATE_EPOCH=1794866400 \
#   STATE_SHA256=c438cd71785459e2612e2dda3425d670de920a62de532c0dff2da6fe332b6365 \
#     bash scripts/pre_gate_check.sh
#
# Both GATE_EPOCH and STATE_SHA256 are required so this cannot silently "pass"
# against the wrong gate or a stale hash. STATE_SHA256 is the committed baseline
# the caller expects; drift means the state advanced (or was corrupted) and the
# cheap path must NOT be taken.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || exit 2

STATE_FILE="${STATE_FILE:-data/processed/paper_trading_state.yaml}"

GATE_EPOCH="${GATE_EPOCH:-}"
STATE_SHA256="${STATE_SHA256:-}"

if [[ -z "$GATE_EPOCH" || -z "$STATE_SHA256" ]]; then
  echo "usage: GATE_EPOCH=<epoch> STATE_SHA256=<sha256> [STATE_FILE=path] bash scripts/pre_gate_check.sh" >&2
  exit 2
fi
if ! [[ "$GATE_EPOCH" =~ ^[0-9]+$ ]]; then
  echo "FATAL: GATE_EPOCH must be a non-negative integer, got '$GATE_EPOCH'" >&2
  exit 2
fi
if ! [[ "$STATE_SHA256" =~ ^[0-9a-fA-F]{64}$ ]]; then
  echo "FATAL: STATE_SHA256 must be a 64-char hex sha256, got '$STATE_SHA256'" >&2
  exit 2
fi
if [[ ! -f "$STATE_FILE" ]]; then
  echo "FATAL: state file not found: $STATE_FILE" >&2
  exit 2
fi

now_epoch="$(date -u +%s)"
gate_human="$(date -u -d "@$GATE_EPOCH" +%FT%TZ 2>/dev/null || echo "$GATE_EPOCH")"

# 1. Gate epoch check: the cheap path only applies strictly before the gate.
if (( now_epoch >= GATE_EPOCH )); then
  echo "CHECK FAILED: now ($now_epoch, $(date -u +%FT%TZ)) >= gate $GATE_EPOCH ($gate_human);" >&2
  echo "  the gate is released — the full gate cycle is the correct next step, not the cheap path." >&2
  exit 3
fi

# 2. State hash check: a mismatch means the state advanced or was corrupted.
actual_sha="$(sha256sum "$STATE_FILE" | awk '{print $1}')"
if [[ "$actual_sha" != "$STATE_SHA256" ]]; then
  echo "CHECK FAILED: state hash $actual_sha != expected $STATE_SHA256;" >&2
  echo "  state advanced or was corrupted — do NOT take the cheap path; inspect the diff." >&2
  exit 3
fi

# 3. data/raw must be untouched.
raw_dirty="$(git status --porcelain -- data/raw)"
if [[ -n "$raw_dirty" ]]; then
  echo "CHECK FAILED: data/raw has uncommitted changes:" >&2
  printf '%s\n' "$raw_dirty" >&2
  echo "  raw data must stay untouched; do NOT take the cheap path." >&2
  exit 3
fi

remaining=$(( GATE_EPOCH - now_epoch ))
echo "PRE-GATE OK: now=$now_epoch ($(date -u +%FT%TZ)) < gate $GATE_EPOCH ($gate_human); T-${remaining}s remaining." >&2
echo "  state sha256 matches ($actual_sha); data/raw clean. STOP — do not re-run the cycle." >&2
exit 0