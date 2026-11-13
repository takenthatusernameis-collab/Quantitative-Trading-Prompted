#!/usr/bin/env bash
# Post-gate orchestrator (Cycle 1242) -- closes the gate-waiter gap.
#
# The detached waiter (gate_wait_and_run.sh) runs cmds 1,3,2,3,4,5,6,8 but:
#   * does NOT run cmd7 (data-cost inventory 001/002 + its tests);
#   * writes NO durable handoff;
#   * logs only to /tmp, which is lost on runner teardown.
#
# This script is the durable, restart-safe, gate-guarded replacement. It:
#   * refuses to run before the gate release (22:00 UTC 2026-11-12);
#   * runs the full cycle 1-8 in order;
#   * writes a durable handoff into the repository (not /tmp);
#   * is idempotent: re-running after a completed cycle is a verified no-op.
#
# Usage: scripts/post_gate_orchestrator.sh [--force] [--read-only]
#                                        [--wait-until-gate [--max-wait-seconds N]]
#   --force     skips the clock-gate pre-check (testing only).
#   --read-only runs the verification portion (cmds 1,3,5,6,7,8) and SKIPS the
#               mutating extend (cmds 2,4). Safe to run before the gate.
#   --wait-until-gate
#               instead of exiting 3 before the gate, block (60s heartbeat) until
#               GATE_EPOCH is reached, then run the cycle. The run's own 355-minute
#               cutoff bounds the wait. Use this from the session whose run is
#               active across the gate (see NEXT_AGENT_TASK.md "Note").
#   --max-wait-seconds N
#               cap the --wait-until-gate wait at N seconds; if the gate is still
#               not released afterwards, exit 3 (default: wait until run cutoff).
#
# Both GATE_EPOCH and HANDOFF are env-overridable so this script is reusable for
# later gates without editing it. Defaults below target the 2026-11-12 gate.
# Example for the 2026-11-13 gate (22:00 UTC = epoch 1794607200):
#   GATE_EPOCH=1794607200 HANDOFF=CORRECTIVE_HANDOFF_POSTGATE_20261113.md \
#     bash scripts/post_gate_orchestrator.sh --wait-until-gate
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || exit 2

PY="${PYTHON:-/tmp/kilo-venv/bin/python}"
RUFF="${RUFF:-/tmp/kilo-venv/bin/ruff}"
GATE_EPOCH="${GATE_EPOCH:-1794520800}"   # 2026-11-12T22:00:00Z (override for later gates)
HANDOFF="${HANDOFF:-CORRECTIVE_HANDOFF_POSTGATE_20261112.md}"
WAIT_UNTIL_GATE=0
MAX_WAIT_SECONDS=""
# Human-readable gate timestamp derived from GATE_EPOCH so the generated handoff
# is correct for whichever gate is targeted (defaults to the 2026-11-12 gate).
GATE_HUMAN="$(date -u -d "@$GATE_EPOCH" +%FT%TZ)"
PYTEST6="tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py tests/test_state_aggregate_audit.py tests/test_rolling_63d_gate_refresh.py"
PYTEST7="tests/test_data_cost_inventory_001.py tests/test_data_cost_inventory_002.py"
RUFF4="research/drift_persistence_report.py research/extend_paper_trading_state.py research/verify_monday_extension_path.py research/verify_gate_time_forward_bar.py"

log() { echo "[$(date -u +%FT%TZ)] $*"; }
fail() { log "FATAL: $*"; exit 1; }

# --- Step-failure tracking (self-evidencing) ---------------------------------
# The orchestrator must not claim "cycle complete" (or exit 0) when any sub-check
# fails. Each verification step records its exit status here; the handoff and the
# process exit code reflect the aggregate result.
FAILED=0
record_rc() {
  local rc="$1" label="$2"
  if (( rc != 0 )); then
    log "STEP FAILED (rc=$rc): $label"
    FAILED=1
  fi
}

# --- 0. Clock gate -----------------------------------------------------------
READ_ONLY=0
FORCE=0
while (( $# > 0 )); do
  case "$1" in
    --read-only) READ_ONLY=1; shift ;;
    --force) FORCE=1; shift ;;
    --wait-until-gate) WAIT_UNTIL_GATE=1; shift ;;
    --max-wait-seconds)
      shift
      if (( $# == 0 )); then log "FATAL: --max-wait-seconds requires a value"; exit 2; fi
      MAX_WAIT_SECONDS="$1"; shift ;;
    *) shift ;;
  esac
done
if (( ! FORCE )); then
  now_epoch="$(date +%s)"
  if (( now_epoch < GATE_EPOCH )); then
    if (( WAIT_UNTIL_GATE )); then
      wait_seconds=$(( GATE_EPOCH - now_epoch ))
      if [ -n "$MAX_WAIT_SECONDS" ] && (( wait_seconds > MAX_WAIT_SECONDS )); then
        wait_seconds="$MAX_WAIT_SECONDS"
      fi
      log "clock gate NOT released (now=$now_epoch target=$GATE_EPOCH); waiting up to ${wait_seconds}s for release"
      wait_deadline=$(( now_epoch + wait_seconds ))
      while :; do
        now_epoch="$(date +%s)"
        (( now_epoch >= GATE_EPOCH )) && break
        (( now_epoch >= wait_deadline )) && break
        sleep_for=$(( wait_deadline - now_epoch ))
        (( sleep_for > 60 )) && sleep_for=60
        (( sleep_for < 1 )) && sleep_for=1
        sleep "$sleep_for"
        log "still waiting for gate: $(date -u +%FT%TZ) target $(date -u -d "@$GATE_EPOCH" +%FT%TZ)"
      done
      now_epoch="$(date +%s)"
      if (( now_epoch < GATE_EPOCH )); then
        log "wait budget exhausted before gate release (now=$now_epoch target=$GATE_EPOCH); refusing to run"
        exit 3
      fi
      log "clock gate released after wait"
    else
      log "clock gate NOT released (now=$now_epoch target=$GATE_EPOCH); refusing to run"
      log "re-run at/after $(date -u -d "@$GATE_EPOCH" +%FT%TZ) UTC"
      exit 3
    fi
  fi
fi
log "clock gate released; starting post-gate cycle (read_only=$READ_ONLY)"

# --- 1. Date -----------------------------------------------------------------
log "cmd1: date"
date -u
TZ=America/New_York date
record_rc $? "cmd1 date"

# --- 2. Extend (only if a completed candidate bar exists) --------------------
if (( READ_ONLY )); then
  log "cmd2: SKIP extend (read-only mode)"
else
  log "cmd2: extend_paper_trading_state"
  "$PY" research/extend_paper_trading_state.py 2>&1 | tail -25
  record_rc $? "cmd2 extend"
fi

# --- 3. Drift report ---------------------------------------------------------
log "cmd3: drift_persistence_report"
"$PY" research/drift_persistence_report.py 2>&1 | tail -8
record_rc $? "cmd3 drift"

# --- 4. Idempotency re-run ---------------------------------------------------
if (( READ_ONLY )); then
  log "cmd4: SKIP idempotency re-extend (read-only mode)"
else
  log "cmd4: extend idempotency check"
  "$PY" research/extend_paper_trading_state.py 2>&1 | tail -8
  record_rc $? "cmd4 idempotency re-extend"
fi

# --- 5. 6-module pytest ------------------------------------------------------
log "cmd5: 6-module pytest"
"$PY" -m pytest $PYTEST6 -q 2>&1 | tail -6
record_rc $? "cmd5 6-module pytest"

# --- 6. Git status -----------------------------------------------------------
log "cmd6: git status"
git status --porcelain
record_rc $? "cmd6 git status"

# --- 7. Data-cost inventory (the waiter gap) ---------------------------------
log "cmd7a: data_cost_inventory_001"
"$PY" research/data_cost_inventory_001.py 2>&1 | tail -5
record_rc $? "cmd7a inventory 001"
log "cmd7b: data_cost_inventory_002"
"$PY" research/data_cost_inventory_002.py 2>&1 | tail -5
record_rc $? "cmd7b inventory 002"
log "cmd7c: inventory pytest"
"$PY" -m pytest $PYTEST7 -q 2>&1 | tail -6
record_rc $? "cmd7c inventory pytest"

# --- 8. Ruff -----------------------------------------------------------------
log "cmd8: ruff"
"$RUFF" check $RUFF4 2>&1 | tail -4
record_rc $? "cmd8 ruff"

# --- 9. Durable handoff ------------------------------------------------------
log "writing durable handoff: $HANDOFF"
STATE_SHA="$("$PY" - <<'PY'
import hashlib, yaml
from pathlib import Path
p = Path("data/processed/paper_trading_state.yaml")
h = hashlib.sha256(p.read_bytes()).hexdigest()
s = yaml.safe_load(p.read_text()) or {}
print(f"{h} last_run={s.get('last_run_date')} nav={s.get('current_nav')} runs={len(s.get('run_history') or [])}")
PY
)"
if (( FAILED )); then
  log "cycle complete WITH FAILURES; see handoff $HANDOFF"
  STATUS="FAILED — one or more verification steps failed (see STEP FAILED lines above)"
else
  log "cycle complete"
  STATUS="OK — all verification steps passed"
fi
cat > "$HANDOFF" <<EOF
# Post-Gate Handoff — cycle for gate $GATE_HUMAN (orchestrator scripts/post_gate_orchestrator.sh)

- **Generated:** $(date -u +%FT%TZ) UTC
- **Status:** $STATUS
- **Mode:** $([ $READ_ONLY -eq 1 ] && echo "read-only verification" || echo "full cycle (extend included)")
- **State:** $STATE_SHA
- **Gate epoch:** $GATE_EPOCH ($GATE_HUMAN)
- **Orchestrator:** scripts/post_gate_orchestrator.sh (idempotent, restart-safe)
- **Cmds run:** 1 date, 2 extend, 3 drift, 4 idempotent re-extend, 5 6-module pytest, 6 git status, 7 data-cost inventory + tests, 8 ruff
- **Waiter gap closed:** cmd7 now runs inside the cycle and the handoff is written into the repository (not /tmp).
EOF
if (( FAILED )); then
  exit 1
fi
exit 0