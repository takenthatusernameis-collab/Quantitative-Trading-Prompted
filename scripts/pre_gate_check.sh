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
# Session reachability (optional, informational -- never changes the exit code)
# ---------------------------------------------------------------------------
# Consecutive pre-gate sessions each re-derived by hand that the gate release
# (22:00Z) falls after the run's ~355-minute cutoff, so the post-gate cycle is
# structurally unreachable. Two inputs make that arithmetic deterministic and
# machine-readable instead (CUTOFF_EPOCH is preferred when both are set):
#   CUTOFF_EPOCH         the ABSOLUTE global run cutoff (epoch). Preferred: the
#                        controller knows it exactly (job_start + 355*60), so
#                        the verdict is exact with NO session-start estimation.
#                        The recurring failure was estimating the budget from an
#                        assumed session start and then hand-correcting the
#                        prose; an absolute cutoff removes that guesswork.
#   SESSION_BUDGET_SECONDS  a RELATIVE remaining budget (kept for backward
#                        compatibility). Callers must pass the *remaining*
#                        budget, not the full ~21300s, or the verdict over-
#                        estimates the reachable window.
#   GATE_REACHABLE=0   gate not reached AND T-remaining > budget (unreachable)
#   GATE_REACHABLE=1   gate not reached AND T-remaining <= budget (waitable with
#                      post_gate_orchestrator.sh --wait-until-gate)
# The verdict stays on exit 0 (the cheap path still applies and the caller must
# still STOP); a reachable gate never implies permission to extend early.
#
# Usage:
#   GATE_EPOCH=1794866400 \
#   STATE_SHA256=c438cd71785459e2612e2dda3425d670de920a62de532c0dff2da6fe332b6365 \
#     bash scripts/pre_gate_check.sh
#   # with an in-session reachability verdict:
#   SESSION_BUDGET_SECONDS=21300 ... bash scripts/pre_gate_check.sh
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

# Optional session budget. Validate it the same way as GATE_EPOCH: an empty or
# non-numeric value must not silently flow into `(( ))`, where bash treats a
# non-numeric string as 0 and would report the gate as trivially reachable.
SESSION_BUDGET_SECONDS="${SESSION_BUDGET_SECONDS:-}"
if [[ -n "$SESSION_BUDGET_SECONDS" && ! "$SESSION_BUDGET_SECONDS" =~ ^[0-9]+$ ]]; then
  echo "FATAL: SESSION_BUDGET_SECONDS must be a non-negative integer, got '$SESSION_BUDGET_SECONDS'" >&2
  exit 2
fi

# Optional ABSOLUTE global run cutoff (epoch). Preferred over the relative
# SESSION_BUDGET_SECONDS because the controller knows the exact cutoff
# (job_start + 355*60) -- no session-start estimation, no per-call prose
# correction. Validate it exactly like GATE_EPOCH: a non-numeric value must not
# flow into `(( ))` (where bash treats it as 0 and would report the gate as
# trivially reachable). When set, it takes precedence in the reachability verdict.
CUTOFF_EPOCH="${CUTOFF_EPOCH:-}"
if [[ -n "$CUTOFF_EPOCH" && ! "$CUTOFF_EPOCH" =~ ^[0-9]+$ ]]; then
  echo "FATAL: CUTOFF_EPOCH must be a non-negative integer epoch, got '$CUTOFF_EPOCH'" >&2
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

# 3. data/raw must be untouched. Capture git's own exit code: a `git status`
#    invocation that fails (exit 128, e.g. run outside a git repo) produces
#    empty stdout, which would otherwise be indistinguishable from a genuinely
#    clean tree and reported as "data/raw clean" -- a false assurance that
#    defeats the purpose of this check. Fail closed instead (Cycle 1257).
raw_dirty="$(git status --porcelain -- data/raw 2>/dev/null)"
git_rc=$?
if (( git_rc != 0 )); then
  echo "CHECK FAILED: 'git status --porcelain -- data/raw' failed (rc=$git_rc);" >&2
  echo "  cannot verify data/raw is clean (not a git repo, or git is unavailable);" >&2
  echo "  do NOT take the cheap path; inspect the working tree." >&2
  exit 3
fi
if [[ -n "$raw_dirty" ]]; then
  echo "CHECK FAILED: data/raw has uncommitted changes:" >&2
  printf '%s\n' "$raw_dirty" >&2
  echo "  raw data must stay untouched; do NOT take the cheap path." >&2
  exit 3
fi

remaining=$(( GATE_EPOCH - now_epoch ))
echo "PRE-GATE OK: now=$now_epoch ($(date -u +%FT%TZ)) < gate $GATE_EPOCH ($gate_human); T-${remaining}s remaining." >&2
echo "  state sha256 matches ($actual_sha); data/raw clean. STOP — do not re-run the cycle." >&2

# Informational only: never alters the exit code. This replaces the manual
# "cutoff precedes gate release" arithmetic repeated every pre-gate session.
# CUTOFF_EPOCH (absolute) is preferred over SESSION_BUDGET_SECONDS (relative):
# the absolute cutoff is exact and needs no session-start estimation, whereas the
# relative budget requires the caller to pass the *remaining* budget (not the
# full ~21300s) or the verdict overestimates the reachable window.
if [[ -n "$CUTOFF_EPOCH" ]]; then
  budget_remaining=$(( CUTOFF_EPOCH - now_epoch ))
  cutoff_human="$(date -u -d "@$CUTOFF_EPOCH" +%FT%TZ 2>/dev/null || echo "$CUTOFF_EPOCH")"
  budget_source="absolute CUTOFF_EPOCH=$CUTOFF_EPOCH ($cutoff_human)"
elif [[ -n "$SESSION_BUDGET_SECONDS" ]]; then
  budget_remaining="$SESSION_BUDGET_SECONDS"
  cutoff_epoch=$(( now_epoch + SESSION_BUDGET_SECONDS ))
  cutoff_human="$(date -u -d "@$cutoff_epoch" +%FT%TZ 2>/dev/null || echo "$cutoff_epoch")"
  budget_source="relative SESSION_BUDGET_SECONDS=${SESSION_BUDGET_SECONDS}s (est. cutoff $cutoff_human)"
else
  budget_remaining=""
fi
if [[ -n "$budget_remaining" ]]; then
  if (( remaining > budget_remaining )); then
    echo "GATE_REACHABLE=0: T-${remaining}s > ${budget_source}; remaining budget ${budget_remaining}s, gate $gate_human;" >&2
    echo "  the post-gate cycle cannot run in this session — record this verdict and hand off." >&2
  else
    echo "GATE_REACHABLE=1: T-${remaining}s <= ${budget_source}; remaining budget ${budget_remaining}s, gate $gate_human;" >&2
    echo "  the gate falls inside this session — use post_gate_orchestrator.sh --wait-until-gate." >&2
  fi
fi
exit 0