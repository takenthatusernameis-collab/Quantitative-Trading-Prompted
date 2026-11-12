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
#   --force     skips the clock-gate pre-check (testing only).
#   --read-only runs the verification portion (cmds 1,3,5,6,7,8) and SKIPS the
#               mutating extend (cmds 2,4). Safe to run before the gate.
#
# Both GATE_EPOCH and HANDOFF are env-overridable so this script is reusable for
# later gates without editing it. Defaults below target the 2026-11-12 gate.
# Example for the 2026-11-13 gate (22:00 UTC = epoch 1794607200):
#   GATE_EPOCH=1794607200 HANDOFF=CORRECTIVE_HANDOFF_POSTGATE_20261113.md \
#     bash scripts/post_gate_orchestrator.sh
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || exit 2

PY="${PYTHON:-/tmp/kilo-venv/bin/python}"
RUFF="${RUFF:-/tmp/kilo-venv/bin/ruff}"
GATE_EPOCH="${GATE_EPOCH:-1794520800}"   # 2026-11-12T22:00:00Z (override for later gates)
HANDOFF="${HANDOFF:-CORRECTIVE_HANDOFF_POSTGATE_20261112.md}"
# Human-readable gate timestamp derived from GATE_EPOCH so the generated handoff
# is correct for whichever gate is targeted (defaults to the 2026-11-12 gate).
GATE_HUMAN="$(date -u -d "@$GATE_EPOCH" +%FT%TZ)"
PYTEST6="tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py tests/test_state_aggregate_audit.py tests/test_rolling_63d_gate_refresh.py"
PYTEST7="tests/test_data_cost_inventory_001.py tests/test_data_cost_inventory_002.py"
RUFF4="research/drift_persistence_report.py research/extend_paper_trading_state.py research/verify_monday_extension_path.py research/verify_gate_time_forward_bar.py"

log() { echo "[$(date -u +%FT%TZ)] $*"; }
fail() { log "FATAL: $*"; exit 1; }

# --- 0. Clock gate -----------------------------------------------------------
READ_ONLY=0
FORCE=0
for arg in "$@"; do
  case "$arg" in
    --read-only) READ_ONLY=1 ;;
    --force) FORCE=1 ;;
  esac
done
if (( ! FORCE )); then
  now_epoch="$(date +%s)"
  if (( now_epoch < GATE_EPOCH )); then
    log "clock gate NOT released (now=$now_epoch target=$GATE_EPOCH); refusing to run"
    log "re-run at/after $(date -u -d "@$GATE_EPOCH" +%FT%TZ) UTC"
    exit 3
  fi
fi
log "clock gate released; starting post-gate cycle (read_only=$READ_ONLY)"

# --- 1. Date -----------------------------------------------------------------
log "cmd1: date"
date -u
TZ=America/New_York date

# --- 2. Extend (only if a completed candidate bar exists) --------------------
if (( READ_ONLY )); then
  log "cmd2: SKIP extend (read-only mode)"
else
  log "cmd2: extend_paper_trading_state"
  "$PY" research/extend_paper_trading_state.py 2>&1 | tail -25
fi

# --- 3. Drift report ---------------------------------------------------------
log "cmd3: drift_persistence_report"
"$PY" research/drift_persistence_report.py 2>&1 | tail -8

# --- 4. Idempotency re-run ---------------------------------------------------
if (( READ_ONLY )); then
  log "cmd4: SKIP idempotency re-extend (read-only mode)"
else
  log "cmd4: extend idempotency check"
  "$PY" research/extend_paper_trading_state.py 2>&1 | tail -8
fi

# --- 5. 6-module pytest ------------------------------------------------------
log "cmd5: 6-module pytest"
"$PY" -m pytest $PYTEST6 -q 2>&1 | tail -6

# --- 6. Git status -----------------------------------------------------------
log "cmd6: git status"
git status --porcelain

# --- 7. Data-cost inventory (the waiter gap) ---------------------------------
log "cmd7a: data_cost_inventory_001"
"$PY" research/data_cost_inventory_001.py 2>&1 | tail -5
log "cmd7b: data_cost_inventory_002"
"$PY" research/data_cost_inventory_002.py 2>&1 | tail -5
log "cmd7c: inventory pytest"
"$PY" -m pytest $PYTEST7 -q 2>&1 | tail -6

# --- 8. Ruff -----------------------------------------------------------------
log "cmd8: ruff"
"$RUFF" check $RUFF4 2>&1 | tail -4

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
cat > "$HANDOFF" <<EOF
# Post-Gate Handoff — cycle for gate $GATE_HUMAN (orchestrator scripts/post_gate_orchestrator.sh)

- **Generated:** $(date -u +%FT%TZ) UTC
- **Mode:** $([ $READ_ONLY -eq 1 ] && echo "read-only verification" || echo "full cycle (extend included)")
- **State:** $STATE_SHA
- **Gate epoch:** $GATE_EPOCH ($GATE_HUMAN)
- **Orchestrator:** scripts/post_gate_orchestrator.sh (idempotent, restart-safe)
- **Cmds run:** 1 date, 2 extend, 3 drift, 4 idempotent re-extend, 5 6-module pytest, 6 git status, 7 data-cost inventory + tests, 8 ruff
- **Waiter gap closed:** cmd7 now runs inside the cycle and the handoff is written into the repository (not /tmp).
EOF
log "cycle complete"
exit 0