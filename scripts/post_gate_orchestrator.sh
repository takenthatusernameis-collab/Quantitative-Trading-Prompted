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
#   --force     skips the clock-gate pre-check (testing only). The handoff then
#               records "Gate state: NOT released" so a forced pre-gate run can
#               never be mistaken for post-gate evidence.
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
# HANDOFF defaults to the date of GATE_EPOCH (not a hard-coded filename), so a
# partial override of GATE_EPOCH alone cannot overwrite a different gate's record.
# Example for the 2026-11-13 gate (22:00 UTC = epoch 1794607200):
#   GATE_EPOCH=1794607200 bash scripts/post_gate_orchestrator.sh --wait-until-gate
#   # writes CORRECTIVE_HANDOFF_POSTGATE_20261113.md; override HANDOFF only for
#   # a custom filename, which must name the same gate date as GATE_EPOCH.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || exit 2

PY="${PYTHON:-/tmp/kilo-venv/bin/python}"
RUFF="${RUFF:-/tmp/kilo-venv/bin/ruff}"
GATE_EPOCH="${GATE_EPOCH:-1794520800}"   # 2026-11-12T22:00:00Z (override for later gates)
WAIT_UNTIL_GATE=0
MAX_WAIT_SECONDS=""
# Validate the clock-gate variable itself before anything derives a date or
# filename from it. A typo'd/empty/non-numeric GATE_EPOCH (e.g.
# GATE_EPOCH=17948_66400 or a quoted blank) previously flowed into `date -d "@"`
# and the `(( now_epoch < GATE_EPOCH ))` arithmetic: GNU date prints a bogus
# human date and arithmetic silently evaluates a non-numeric string as 0, so the
# gate would appear permanently open. Fail closed as a usage error (mirrors the
# GATE_EPOCH guard in scripts/pre_gate_check.sh).
if ! [[ "$GATE_EPOCH" =~ ^[0-9]+$ ]]; then
  echo "FATAL: GATE_EPOCH must be a non-negative integer epoch, got '$GATE_EPOCH'" >&2
  exit 2
fi

# Human-readable gate timestamp derived from GATE_EPOCH so the generated handoff
# is correct for whichever gate is targeted (defaults to the 2026-11-12 gate).
GATE_HUMAN="$(date -u -d "@$GATE_EPOCH" +%FT%TZ)"
GATE_DATE="$(date -u -d "@$GATE_EPOCH" +%Y%m%d)"
# Default the durable handoff to the gate being run. Previously this was the
# hard-coded 2026-11-12 filename, so overriding only GATE_EPOCH (the natural
# partial invocation) silently overwrote the 2026-11-12 record with 2026-11-13
# content -- the same durable-evidence hazard class as an ignored flag.
HANDOFF="${HANDOFF:-CORRECTIVE_HANDOFF_POSTGATE_${GATE_DATE}.md}"
PYTEST6="tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py tests/test_state_aggregate_audit.py tests/test_rolling_63d_gate_refresh.py"
PYTEST7="tests/test_data_cost_inventory_001.py tests/test_data_cost_inventory_002.py"
# cmd8 lints every script the cycle EXECUTES, including cmd4b's
# paper_trading_record_status_audit.py. That script runs in the real post-gate
# cycle (it regenerates the record-status artifacts after the extend) but was
# absent from this list, so a latent defect in it would fail the cycle with
# Status: FAILED and no lint evidence -- the exact gap cmd8 exists to close for
# the other four extension scripts. It now passes ruff (EXE001 cleared by making
# the file executable) and is pinned here so it cannot silently drop out again.
RUFF4="research/drift_persistence_report.py research/drift_invariant_check.py research/extend_paper_trading_state.py research/verify_monday_extension_path.py research/verify_gate_time_forward_bar.py research/paper_trading_record_status_audit.py research/paper_record_raw_coverage_audit.py research/paper_trading_artifact_reconciliation_audit.py"

log() { echo "[$(date -u +%FT%TZ)] $*"; }
fail() { log "FATAL: $*"; exit 1; }

# Fail closed when an explicit HANDOFF names a different gate date than
# GATE_EPOCH. Writing one gate's cycle into another gate's durable record is the
# mis-invocation hazard this script exists to prevent; the date must match.
if [[ "$(basename "$HANDOFF")" =~ (20[0-9]{6}) ]]; then
  HANDOFF_DATE="${BASH_REMATCH[1]}"
  if [[ "$HANDOFF_DATE" != "$GATE_DATE" ]]; then
    log "FATAL: HANDOFF '$HANDOFF' names gate date $HANDOFF_DATE but GATE_EPOCH is $GATE_HUMAN ($GATE_DATE); refusing to write another gate's durable record"
    exit 2
  fi
fi

# --- Step-failure tracking (self-evidencing) ---------------------------------
# The orchestrator must not claim "cycle complete" (or exit 0) when any sub-check
# fails. Each verification step records its exit status here; the handoff and the
# process exit code reflect the aggregate result.
FAILED=0
# The durable handoff must record what ACTUALLY ran, not the nominal cycle: in
# read-only mode cmds 2/4 are skipped, and a handoff that still claims "2 extend"
# would misrepresent the cycle to whoever reads it after the gate.
CMDS_RUN=""
CMDS_SKIPPED=""
mark_run() { CMDS_RUN="${CMDS_RUN:+$CMDS_RUN, }$1"; }
mark_skipped() { CMDS_SKIPPED="${CMDS_SKIPPED:+$CMDS_SKIPPED, }$1"; }
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
      case "$1" in
        ''|*[!0-9]*) log "FATAL: --max-wait-seconds requires a positive integer, got '$1'"; exit 2 ;;
      esac
      # 0 is not a usable wait budget: it silently degrades to "do not wait" and
      # exits 3 exactly like the no-wait path, which is indistinguishable from a
      # mis-invocation in the durable record. Require strictly positive.
      if (( $1 == 0 )); then log "FATAL: --max-wait-seconds requires a positive integer, got '$1'"; exit 2; fi
      MAX_WAIT_SECONDS="$1"; shift ;;
    -h|--help)
      log "usage: post_gate_orchestrator.sh [--read-only] [--force] [--wait-until-gate] [--max-wait-seconds N]"
      exit 0 ;;
    *)
      # A silently-ignored flag is a durable-evidence hazard for the gate-active
      # run: e.g. a typo'd --wait-until-gate would exit 3 before the gate and the
      # operator would see only "gate NOT released", never "unknown flag". Fail
      # closed with a usage error so mis-invocation is visible.
      log "FATAL: unknown argument '$1' (see --help)"; exit 2 ;;
  esac
done
now_epoch="$(date +%s)"
# --- Preflight: the interpreters must exist before any step runs ---------------
# ``/tmp/kilo-venv`` is ephemeral (recreated per job; see NEXT_AGENT_TASK.md
# "Runtime note"). If the run that is active at/after the gate is a fresh
# container without it, PYTHON/RUFF point at missing paths and EVERY step fails
# with an opaque ``No such file or directory`` (rc=127) -- and in the real
# (non-read-only) cycle that is the mutating extend (cmd2), which would abort
# mid-cycle after the script already logged "starting post-gate cycle". Detect
# the missing prerequisites up front and fail closed with an actionable message,
# before the clock wait or any step, so the operator re-creates the venv instead
# of reading a mid-cycle failure. Uses the same PY/RUFF the cycle invokes, so a
# pass here guarantees every later step can execute its interpreter.
# ``command -v`` resolves a PATH command, an explicit path, or a shell builtin
# (the test suite uses ``true``/``false`` as no-op interpreters), so it validates
# exactly what a later step can execute without rejecting a bare command name.
for _prog in "$PY" "$RUFF"; do
  if ! command -v "$_prog" >/dev/null 2>&1; then
    log "FATAL: required interpreter '$_prog' is missing or not executable; the gate cycle cannot run."
    log "       /tmp/kilo-venv is ephemeral -- recreate it, then re-run:"
    log "       python3 -m venv /tmp/kilo-venv && /tmp/kilo-venv/bin/python -m pip install --no-cache-dir numpy pandas scipy statsmodels arch yfinance pyarrow pyyaml pytest ruff"
    exit 2
  fi
done
if (( ! FORCE )); then
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
# The durable record must be unambiguous about WHICH side of the gate produced
# it. A `--force --read-only` run before the gate writes the same handoff file
# as the post-gate cycle, so "Status: OK" alone reads like post-gate evidence to
# the next session. Record the gate state explicitly instead.
now_epoch="$(date +%s)"
if (( now_epoch < GATE_EPOCH )); then
  PRE_GATE=1
  GATE_STATE="NOT released — pre-gate verification run only (T-$(( GATE_EPOCH - now_epoch ))s remaining; mutating extend withheld)"
else
  PRE_GATE=0
  GATE_STATE="released (gate epoch reached)"
fi
# The mutating extend (cmd2) and its idempotency re-run (cmd4) must NEVER run
# before the gate is released, whatever the flags. --force overrides only the
# exit-3 refusal so a pre-gate verification cycle can run; it does NOT
# re-enable the mutating extend, which would advance the paper-trading state
# before the target session is complete (NEXT_AGENT_TASK.md scope boundary:
# "Do not run a mutating extend before the target session gate").
#
# A --force FULL run before the gate previously ran the extend (cmd2 + cmd4)
# and then wrote a handoff claiming "full cycle (extend included)" /
# "Cmds skipped: none" while its OWN "Gate state" line said "NOT released ...
# mutating extend withheld" -- a self-contradictory durable record that is
# worse than either honest label, and exactly the class of false-evidence
# hazard this orchestrator exists to prevent (cf. Cycle 1258/1259/1260, where
# a handoff that reads "OK" but does not match what ran was the recurring
# defect). The extend is now gated on the clock, not on --read-only.
EXTEND_DISABLED=0
if (( READ_ONLY || PRE_GATE )); then
  EXTEND_DISABLED=1
fi
# The Mode line must describe what ACTUALLY ran. A pre-gate full run is NOT a
# "full cycle (extend included)"; claiming so would misrepresent the cycle to
# whoever reads the handoff after the gate (the acceptance criteria's expected
# "Mode: full cycle (extend included)" is produced only by the real post-gate
# run, i.e. the else branch here).
# Gate state takes precedence for the Mode label: a pre-gate run (whether
# --read-only or not) is "pre-gate verification"; a post-gate --read-only run
# is "read-only verification"; a post-gate full run is "full cycle (extend included)".
if (( PRE_GATE )); then
  MODE="pre-gate verification (extend withheld — gate not released)"
elif (( READ_ONLY )); then
  MODE="read-only verification"
else
  MODE="full cycle (extend included)"
fi
log "gate state: $GATE_STATE"
log "starting post-gate cycle (read_only=$READ_ONLY, extend_disabled=$EXTEND_DISABLED)"

# --- 1. Date -----------------------------------------------------------------
log "cmd1: date"
mark_run "1 date"
date -u
TZ=America/New_York date
record_rc $? "cmd1 date"

# --- 1b. Pre-extend session anchor (for the cmd8c digest guard) --------------
# research/paper_record_raw_coverage_audit.py documents (``--extend-before``)
# that a session appended by this cycle MUST carry a valid
# ``provider_digest_YYYYMMDD.json``, and fails closed (exit 1) when it does not.
# That contract was dead in the real cycle: cmd8c was invoked with no argument,
# so ``require_digest_for`` stayed None and a silently failed digest write would
# still read "Status: OK". Capture the pre-extension ``last_run_date`` here,
# before cmd2 mutates the state, and hand it to cmd8c.
#
# A plain text read (not an interpreter call) keeps this pre-step out of the
# python step sequence, so the cycle's ordering contract (extend is still the
# first python action) and its exit-code accounting are unchanged.
STATE_FILE_PATH="data/processed/paper_trading_state.yaml"
EXTEND_BEFORE=""
if [[ -f "$STATE_FILE_PATH" ]]; then
  EXTEND_BEFORE="$(sed -n "s/^last_run_date:[[:space:]]*['\"]\{0,1\}\(20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]\)['\"]\{0,1\}[[:space:]]*\$/\1/p" "$STATE_FILE_PATH" | head -1)"
fi
# Only a real YYYY-MM-DD session date is passed on (mirrors the State-line
# last_run anchoring); a missing state or a malformed value must not turn into a
# bogus argument that fails the audit.
if [[ "$EXTEND_BEFORE" =~ ^20[0-9]{2}-[0-9]{2}-[0-9]{2}$ ]]; then
  log "pre-extend last_run anchor: $EXTEND_BEFORE (cmd8c digest requirement active)"
else
  EXTEND_BEFORE=""
  log "pre-extend last_run anchor unavailable; cmd8c digest requirement not armed"
fi

# --- 2. Extend (only if a completed candidate bar exists) --------------------
if (( EXTEND_DISABLED )); then
  log "cmd2: SKIP extend (gate not released: $MODE)"
  mark_skipped "2 extend (gate not released)"
else
  log "cmd2: extend_paper_trading_state"
  mark_run "2 extend"
  "$PY" research/extend_paper_trading_state.py 2>&1 | tail -25
  record_rc $? "cmd2 extend"
fi

# --- 3. Drift report ---------------------------------------------------------
log "cmd3: drift_persistence_report"
mark_run "3 drift"
"$PY" research/drift_persistence_report.py 2>&1 | tail -8
record_rc $? "cmd3 drift"

# --- 4. Idempotency re-run ---------------------------------------------------
if (( EXTEND_DISABLED )); then
  log "cmd4: SKIP idempotency re-extend (gate not released: $MODE)"
  mark_skipped "4 idempotent re-extend (gate not released)"
else
  log "cmd4: extend idempotency check"
  mark_run "4 idempotent re-extend"
  "$PY" research/extend_paper_trading_state.py 2>&1 | tail -8
  record_rc $? "cmd4 idempotency re-extend"
fi

# --- 4b. Regenerate record-status artifacts (post-extend only) ---------------
# research/{reports,experiments}/paper_trading_record_status_001.md are derived
# snapshots (session count + last_run_date) of the paper-trading state. They were
# NOT regenerated by any step, so after cmd2 appends a session they go stale
# (e.g. 470/2026-11-16 while the state is 471/2026-11-17) and
# tests/test_paper_trading_record_status_audit.py -- which asserts the artifacts
# equal the state-derived output -- fails. That is the exact drift class that
# produced the 469/2026-11-13 staleness. Regenerate them here, after the extend
# has written the new state, so the durable human-readable record tracks it.
# Gated on EXTEND_DISABLED so --read-only and pre-gate runs stay side-effect free
# (their contract: they must never write a file).
if (( EXTEND_DISABLED )); then
  log "cmd4b: SKIP record-status regen (gate not released: $MODE)"
  mark_skipped "4b record-status regen (gate not released)"
else
  log "cmd4b: regenerate record-status artifacts"
  mark_run "4b record-status regen"
  "$PY" research/paper_trading_record_status_audit.py > /tmp/cmd4b.out 2>&1
  cmd4b_rc=$?
  tail -3 /tmp/cmd4b.out
  record_rc $cmd4b_rc "cmd4b record-status regen"
fi

# --- 5. 6-module pytest ------------------------------------------------------
log "cmd5: 6-module pytest"
mark_run "5 6-module pytest"
"$PY" -m pytest $PYTEST6 -q > /tmp/cmd5.out 2>&1
cmd5_rc=$?
tail -6 /tmp/cmd5.out
record_rc $cmd5_rc "cmd5 6-module pytest"

# --- 6. Git status -----------------------------------------------------------
log "cmd6: git status"
mark_run "6 git status"
git status --porcelain
record_rc $? "cmd6 git status"

# --- 7. Data-cost inventory (the waiter gap) ---------------------------------
# cmd7a/cmd7b/cmd7c are piped through `tail` to keep the log short, but
# `set -uo pipefail` makes the PIPELINE's exit code the LAST command's (tail),
# which always succeeds -- so a failing inventory script (rc=1, e.g. the
# data_cost_inventory_002 NO-GO gate) is silently recorded as PASSED and the
# handoff's "Status: OK" reads as passing evidence for a cycle whose own
# inventory step failed. That is the recurring false-evidence defect class this
# orchestrator exists to prevent (cf. the Cycle-1258/1259/1260 fingerprint
# guards). Capture the pre-pipe exit code and record THAT instead.
mark_run "7 data-cost inventory + tests"
log "cmd7a: data_cost_inventory_001"
"$PY" research/data_cost_inventory_001.py > /tmp/cmd7a.out 2>&1
cmd7a_rc=$?
tail -5 /tmp/cmd7a.out
record_rc $cmd7a_rc "cmd7a inventory 001"
log "cmd7b: data_cost_inventory_002"
"$PY" research/data_cost_inventory_002.py > /tmp/cmd7b.out 2>&1
cmd7b_rc=$?
tail -5 /tmp/cmd7b.out
record_rc $cmd7b_rc "cmd7b inventory 002"
log "cmd7c: inventory pytest"
"$PY" -m pytest $PYTEST7 -q > /tmp/cmd7c.out 2>&1
cmd7c_rc=$?
tail -6 /tmp/cmd7c.out
record_rc $cmd7c_rc "cmd7c inventory pytest"

# --- 8. Ruff -----------------------------------------------------------------
log "cmd8: ruff"
mark_run "8 ruff"
"$RUFF" check $RUFF4 > /tmp/cmd8.out 2>&1
cmd8_rc=$?
tail -4 /tmp/cmd8.out
record_rc $cmd8_rc "cmd8 ruff"

# --- 8b. Drift invariant check (read-only) -----------------------------------
# research/drift_invariant_check.py encodes the three falsification conditions
# from research/reports/drift_decision_20261118.md §7. Read-only: never writes
# state or artifacts. Runs in every mode (pre-gate, read-only, post-gate).
log "cmd8b: drift_invariant_check"
mark_run "8b drift invariant"
"$PY" research/drift_invariant_check.py > /tmp/cmd8b.out 2>&1
cmd8b_rc=$?
tail -6 /tmp/cmd8b.out
record_rc $cmd8b_rc "cmd8b drift invariant check"

# --- 8c. Paper-record vs committed raw-cache coverage audit (read-only) --------
# research/paper_record_raw_coverage_audit.py quantifies the reproducibility gap
# between the committed paper-trading record and the committed raw cache (the
# extension path never writes data/raw, so the six most recent sessions rest on
# the state file alone). It is the provenance check the research contract ranks
# first, and it was the ONLY cycle step that existed as a script with no
# orchestrator wiring: its exit code was never recorded, so a coverage/regression
# defect (malformed provider digest, non-reproducing stored Sharpe) would have
# surfaced only as a printed FAIL line in /tmp/cmd8c.out while the handoff still
# read "Status: OK" -- the recurring false-evidence class this orchestrator
# exists to prevent (cf. cmd8b's identical gap, closed in Cycle 1271).
log "cmd8c: paper_record_raw_coverage_audit"
mark_run "8c coverage audit"
COVERAGE_ARGS=()
if [[ -n "$EXTEND_BEFORE" ]]; then
  COVERAGE_ARGS=(--extend-before "$EXTEND_BEFORE")
fi
"$PY" research/paper_record_raw_coverage_audit.py ${COVERAGE_ARGS[@]+"${COVERAGE_ARGS[@]}"} > /tmp/cmd8c.out 2>&1
cmd8c_rc=$?
tail -6 /tmp/cmd8c.out
record_rc $cmd8c_rc "cmd8c coverage audit"

# --- 8d. Record <-> per-session artifact reconciliation (read-only) -----------
# research/paper_trading_artifact_reconciliation_audit.py is the only check that
# compares every run_history row with its four committed per-session parquet
# artifacts across the WHOLE record. audit_state_aggregates.py re-derives
# state-level fields from run_history only; drift_invariant_check.py checks the
# latest session's regime exposure; the coverage audit compares against
# data/raw. A dropped, duplicated, corrupted or wrongly reconstructed artifact
# (the 2026-11-02 repair defect it attests) would therefore pass every other
# step while the handoff read "Status: OK". Read-only: it writes only its own
# report and never the state, the artifacts or data/raw. A nonzero exit means an
# unattested mismatch -- record it as a step failure, do not hush it.
log "cmd8d: paper_trading_artifact_reconciliation_audit"
mark_run "8d artifact reconciliation"
"$PY" research/paper_trading_artifact_reconciliation_audit.py > /tmp/cmd8d.out 2>&1
cmd8d_rc=$?
tail -6 /tmp/cmd8d.out
record_rc $cmd8d_rc "cmd8d artifact reconciliation"

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
# The State line is the evidence anchor for the whole cycle (hash + last_run +
# nav + run count): without it the handoff cannot prove which state the cycle
# ran against. A silent failure here (python error, missing yaml, missing
# dependency) produced an empty "- **State:** " while the script still reported
# "Status: OK" and exited 0 -- a false-assurance record that reads as a passing
# cycle. Fail the cycle instead (Cycle 1258).
record_rc $? "9 state fingerprint (State line)"
mark_run "9 state fingerprint"
# Evidence-integrity gap (Cycle 1259): the Cycle-1258 guard only caught the
# *empty* fingerprint (python error -> empty output -> rc!=0). A python that
# exits 0 but loads a state whose ``current_nav``/``last_run_date`` key is
# absent prints ``nav=None`` / ``last_run=None`` -- a syntactically present but
# semantically empty fingerprint that passed ``record_rc`` and yielded
# "Status: OK" with no verifiable NAV. Fail the cycle on a *malformed
# non-empty* fingerprint (missing/None nav, missing/None last_run, non-hex
# hash, non-integer run count). An empty fingerprint is left to record_rc's
# exit-code check so the 11 silent-success stubs (PYTHON=true, no output, exit
# 0) keep passing -- they are legitimately "no state to fingerprint" in tests,
# not a malformed production record.
# last_run is anchored to the YYYY-MM-DD session date, not a free string: the
# free `[^[:space:]]+` alternative accepted the literal token "None" (a state
# whose last_run_date key is absent prints last_run=None), which is exactly the
# semantically-empty fingerprint this guard exists to reject (Cycle 1260).
# nav allows an optional leading minus (nav=-?[0-9]+...): current_nav is a float
# and a paper account can legitimately fall below zero. The prior
# `[0-9]+...`-only pattern rejected a valid negative NAV as "malformed" and
# failed an otherwise-successful post-gate cycle with Status: FAILED, destroying
# the very success evidence this orchestrator exists to leave behind
# (test_negative_nav_fingerprint_is_not_malformed).
if [[ -n "$STATE_SHA" ]] \
   && ! [[ "$STATE_SHA" =~ ^[0-9a-fA-F]{64}\ last_run=20[0-9]{2}-[0-9]{2}-[0-9]{2}\ nav=-?[0-9]+\.?[0-9]*\ runs=[0-9]+$ ]]; then
  log "STEP FAILED (rc=1): 9 state fingerprint malformed (got: '$STATE_SHA')"
  FAILED=1
fi
if (( FAILED )); then
  STATUS="FAILED — one or more verification steps failed (see STEP FAILED lines above)"
else
  STATUS="OK — all verification steps passed"
fi
# A handoff that could not be written is NOT a successful cycle: the whole point
# of this script is to leave durable evidence in the repo (not /tmp, which is lost
# on runner teardown). Silently exiting 0 after a failed write would let a
# teardown kill erase the only record of the gate check.
if ! cat > "$HANDOFF" <<EOF
# Post-Gate Handoff — cycle for gate $GATE_HUMAN (orchestrator scripts/post_gate_orchestrator.sh)

- **Generated:** $(date -u +%FT%TZ) UTC
- **Status:** $STATUS
- **Mode:** $MODE
- **Gate state:** $GATE_STATE
- **State:** $STATE_SHA
- **Gate epoch:** $GATE_EPOCH ($GATE_HUMAN)
- **Orchestrator:** scripts/post_gate_orchestrator.sh (idempotent, restart-safe)
- **Cmds run:** ${CMDS_RUN:-none}
- **Cmds skipped:** ${CMDS_SKIPPED:-none}
- **Waiter gap closed:** cmd7 now runs inside the cycle and the handoff is written into the repository (not /tmp).
EOF
then
  log "FATAL: could not write durable handoff to '$HANDOFF' (path unwritable?); refusing to report success"
  exit 1
fi
if (( FAILED )); then
  log "cycle complete WITH FAILURES; see handoff $HANDOFF"
  exit 1
fi
log "cycle complete"
exit 0