set -Eeuo pipefail
cutoff_epoch=$(($(date +%s) + 355 * 60))
umask 077
# A silent Kilo invocation is a stall; this does not shorten the global workflow cutoff.
KILO_IDLE_TIMEOUT_SECONDS="${KILO_IDLE_TIMEOUT_SECONDS:-600}"
if ! [[ "$KILO_IDLE_TIMEOUT_SECONDS" =~ ^[1-9][0-9]*$ ]]; then
  echo "::error::KILO_IDLE_TIMEOUT_SECONDS must be a positive integer."
  exit 1
fi

# Session target is user-configurable; transient attempts and corrective retries have no numeric cap.
KILO_INPUT_SESSIONS="${KILO_INPUT_SESSIONS:-1000}"
if ! [[ "$KILO_INPUT_SESSIONS" =~ ^[1-9][0-9]*$ ]]; then
  echo "::error::KILO_INPUT_SESSIONS must be a positive whole number."
  exit 1
fi
SESSION_LIMIT_POLICY="$KILO_INPUT_SESSIONS"
echo "::notice::Configured worker session target: $SESSION_LIMIT_POLICY; transient retries and corrective attempts remain count-unbounded until the global 355-minute cutoff."
WORKFLOW_STARTED_EPOCH="$(date +%s)"
KILO_PROGRESS_STATE_FILE="$RUNNER_TEMP/kilo-progress-state-${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}.txt"
KILO_PROGRESS_LOG="$RUNNER_TEMP/kilo-progress-${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}.log"
: > "$KILO_PROGRESS_LOG"

write_progress() {
  local phase="${1:-unknown}" detail="${2:-}" now elapsed remaining head_sha tmp line
  now="$(date +%s)"
  elapsed=$((now - WORKFLOW_STARTED_EPOCH))
  remaining=$((cutoff_epoch - now))
  if [ "$remaining" -lt 0 ]; then remaining=0; fi
  detail="$(printf '%s' "$detail" | tr '\r\n' '  ' | cut -c1-160)"
  head_sha="$(git rev-parse --short HEAD 2>/dev/null || printf 'unknown')"
  tmp="${KILO_PROGRESS_STATE_FILE}.tmp.$$"
  if ! {
    printf 'updated_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'phase=%s\n' "$phase"
    printf 'detail=%s\n' "$detail"
    printf 'session=%s\n' "${agent_index:-0}"
    printf 'session_limit=%s\n' "$SESSION_LIMIT_POLICY"
    printf 'attempt=%s\n' "${session_attempt:-0}"
    printf 'completed=%s\n' "${sessions_completed:-0}"
    printf 'failed=%s\n' "${failed_sessions:-0}"
    printf 'checkpoints=%s\n' "${persisted_checkpoints:-0}"
    printf 'verified_checkpoint_sha=%s\n' "${last_verified_checkpoint_sha:-none}"
    printf 'head=%s\n' "$head_sha"
    printf 'elapsed_seconds=%s\n' "$elapsed"
    printf 'remaining_seconds=%s\n' "$remaining"
  } > "$tmp"; then
    rm -f "$tmp"
    return 0
  fi
  if ! mv -f "$tmp" "$KILO_PROGRESS_STATE_FILE"; then
    rm -f "$tmp"
    return 0
  fi
  line="[progress] $(date -u +%Y-%m-%dT%H:%M:%SZ) phase=${phase} session=${agent_index:-0}/${SESSION_LIMIT_POLICY} attempt=${session_attempt:-0} completed=${sessions_completed:-0} failed=${failed_sessions:-0} checkpoints=${persisted_checkpoints:-0} verified_sha=${last_verified_checkpoint_sha:-none} head=${head_sha} elapsed=${elapsed}s remaining=${remaining}s detail=${detail}"
  printf '%s\n' "$line" | tee -a "$KILO_PROGRESS_LOG" || true
}

progress_field() {
  local field="$1"
  if [ ! -f "$KILO_PROGRESS_STATE_FILE" ]; then printf 'unknown'; return 0; fi
  awk -F= -v field="$field" '$1 == field { sub(/^[^=]*=/, ""); print; exit }' "$KILO_PROGRESS_STATE_FILE"
}

record_intentional_noop() {
  python3 .github/scripts/kilo-terminal-outcome.py --intentional-noop --cutoff 0 --checkpoint-sha "$(git rev-parse HEAD 2>/dev/null || printf 'unknown')" --output "${GITHUB_OUTPUT:-}"
}

# Shared production checkpoint routine: CI calls it directly against a local bare Git remote.
source .github/scripts/kilo-persist-checkpoint.sh

write_progress "controller-configured" "event=${KILO_TRIGGER_EVENT:-unknown}; session_policy=${SESSION_LIMIT_POLICY}; hard_cutoff=355_minutes"

# While the one-shot marker awaits its independent validation gate,
# scheduled invocations must not consume it or start a duplicate run.
if [ "$KILO_TRIGGER_EVENT" = "schedule" ]; then
  DEFAULT_BRANCH="$KILO_DEFAULT_BRANCH"
  if [ -z "$DEFAULT_BRANCH" ] || ! git fetch origin "$DEFAULT_BRANCH"; then
    echo "::error::Could not verify the default branch; scheduled activation cannot safely continue."
    exit 1
  fi
  if git cat-file -e "origin/$DEFAULT_BRANCH:.kilo/TWO_AGENT_ONCE" 2>/dev/null; then
    echo "::notice::One-shot marker is awaiting validation/dispatch; this scheduled activation will not start Kilo."
    record_intentional_noop
    exit 0
  fi
fi
# Kilo uses only the repository-scoped GITHUB_TOKEN. Workflow definitions are maintainer-managed because this token cannot grant workflows permission.
export HOME="$RUNNER_TEMP/kilo-home"
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_DATA_HOME="$HOME/.local/share"
export XDG_CACHE_HOME="$HOME/.cache"
export TMPDIR="$RUNNER_TEMP/kilo-tmp"
mkdir -p "$XDG_CONFIG_HOME/kilo" "$XDG_DATA_HOME/kilo" "$XDG_CACHE_HOME/kilo" "$TMPDIR" "$RUNNER_TEMP/kilo"
HEARTBEAT_STATE_FILE="$RUNNER_TEMP/kilo-active-attempt"
: > "$HEARTBEAT_STATE_FILE"
for directory in "$HOME" "$XDG_CONFIG_HOME/kilo" "$XDG_DATA_HOME/kilo" "$XDG_CACHE_HOME/kilo" "$TMPDIR" "$RUNNER_TEMP/kilo"; do
  if ! ( : > "$directory/.kilo-write-test" ) 2>/dev/null; then
    echo "::error::Runtime directory is not writable: $directory."
    exit 1
  fi
  rm -f "$directory/.kilo-write-test"
done

# A durable marker authorizes a validation-gated one-time activation; the active run remains cutoff-bound.
one_shot_mode=0
if [ -f ".kilo/TWO_AGENT_ONCE" ]; then
  one_shot_mode=1
  echo "::notice::One-shot marker detected; authorizing a validation-gated activation."
fi
if [ "$one_shot_mode" -eq 1 ]; then
  SESSION_LIMIT_POLICY=2
fi
# A queued schedule may check out an older commit containing the sentinel.
# Require it to exist on the live default branch before spending the allowance.
if [ "$one_shot_mode" -eq 1 ]; then
  DEFAULT_BRANCH="$KILO_DEFAULT_BRANCH"
  if [ -z "$DEFAULT_BRANCH" ] || ! git fetch origin "$DEFAULT_BRANCH"; then
    echo "::error::Could not verify the one-shot marker on the remote branch."
    exit 1
  fi
  if ! git cat-file -e "origin/$DEFAULT_BRANCH:.kilo/TWO_AGENT_ONCE" 2>/dev/null; then
    echo "::notice::The one-shot marker is absent from origin/$DEFAULT_BRANCH; this is a stale/duplicate activation, exiting without invoking Kilo."
    record_intentional_noop
    exit 0
  fi
fi

if [ "$KILO_TRIGGER_EVENT" = "push" ] && [ "$one_shot_mode" -ne 1 ]; then
  echo "::notice::One-shot sentinel is absent; safe no-op."
  record_intentional_noop
  exit 0
fi

if [ "$one_shot_mode" -eq 0 ] && [ "${GITHUB_EVENT_NAME:-${KILO_TRIGGER_EVENT:-}}" = "schedule" ] && [ -f ".kilo/SKIP_NEXT_ROUTINE_KILO" ]; then
  echo "::notice::Consuming the one-time post-smoke skip; this activation will not start Kilo."
  git config user.name "kilo-autonomous"
  git config user.email "kilo-autonomous@users.noreply.github.com"
  DEFAULT_BRANCH="$KILO_DEFAULT_BRANCH"
  if [ -z "$DEFAULT_BRANCH" ]; then
    echo "::error::Default branch is unavailable; retaining the skip marker for recovery."
    exit 1
  fi
  if ! git rm -f -- .kilo/SKIP_NEXT_ROUTINE_KILO || ! git commit -m "chore(kilo): consume one-time post-run skip"; then
    echo "::error::Could not create the skip-marker consumption commit."
    exit 1
  fi
  delay=5
  while true; do
    remaining=$((cutoff_epoch - $(date +%s)))
    if [ "$remaining" -le 0 ]; then
      echo "::error::Could not verify skip-marker persistence before the cutoff."
      exit 1
    fi
    if git fetch origin "$DEFAULT_BRANCH" && git merge-base --is-ancestor "origin/$DEFAULT_BRANCH" HEAD && git push origin "HEAD:$DEFAULT_BRANCH"; then
      remote_sha="$(git ls-remote origin "refs/heads/$DEFAULT_BRANCH" 2>/dev/null | awk 'NR==1 {print $1}')"
      local_sha="$(git rev-parse HEAD)"
      if [ -n "$remote_sha" ] && [ "$remote_sha" = "$local_sha" ]; then
        echo "Verified one-time skip-marker removal at $remote_sha."
        break
      fi
    fi
    echo "::warning::Could not verify skip-marker removal; retrying without a fixed attempt limit."
    remaining=$((cutoff_epoch - $(date +%s)))
    if [ "$remaining" -le 0 ]; then exit 1; fi
    if [ "$delay" -gt "$remaining" ]; then delay="$remaining"; fi
    sleep "$delay"
    if [ "$delay" -lt 30 ]; then delay=$((delay * 2)); if [ "$delay" -gt 30 ]; then delay=30; fi; fi
  done
  record_intentional_noop
  exit 0
fi

cat > "$HOME/.config/kilo/kilo.json" <<'EOF'
{"$schema":"https://app.kilo.ai/config.json","permission":"allow"}
EOF

install_attempt=0
install_backoff=5
write_progress "kilo-cli-install" "installing pinned Kilo CLI"
until timeout --signal=TERM --kill-after=10s 180s npm install --no-audit --no-fund --prefix "$RUNNER_TEMP/kilo" @kilocode/cli@7.7.1; do
  install_attempt=$((install_attempt + 1))
  write_progress "kilo-cli-install-retry" "CLI installation retry=${install_attempt}"
  remaining=$((cutoff_epoch - $(date +%s)))
  if [ "$remaining" -le 0 ]; then
    echo "::error::Kilo installation did not recover before the 355-minute cutoff; no agent session was started."
    exit 1
  fi
  delay="$install_backoff"
  if [ "$remaining" -lt "$delay" ]; then delay="$remaining"; fi
  echo "::warning::Kilo CLI installation attempt $install_attempt failed; retrying in ${delay}s (no attempt-count cap)."
  sleep "$delay"
  if [ "$install_backoff" -lt 60 ]; then
    install_backoff=$((install_backoff * 2))
    if [ "$install_backoff" -gt 60 ]; then install_backoff=60; fi
  fi
done
export PATH="$RUNNER_TEMP/kilo/node_modules/.bin:$PATH"

git config user.name "kilo-autonomous"
git config user.email "kilo-autonomous@users.noreply.github.com"

# Capture runtime context alongside any future timeout process snapshots.
# Do not print environment variables, tokens, command-line arguments, or prompts.
echo "::group::Kilo runtime baseline diagnostics"
printf 'checked_out_commit=%s\n' "$(git rev-parse HEAD)"
printf 'runner_kernel=%s\n' "$(uname -srmo 2>&1)"
printf 'node_version=%s\n' "$(node --version 2>&1)"
printf 'npm_version=%s\n' "$(npm --version 2>&1)"
printf 'python_version=%s\n' "$(python3 --version 2>&1)"
printf 'kilo_cli_package=%s\n' "$(npm list --prefix "$RUNNER_TEMP/kilo" @kilocode/cli --depth=0 2>&1 | tail -n 1)"
echo "::endgroup::"

if [ "$one_shot_mode" -eq 1 ]; then
  echo "One-shot marker accepted; sequential Kilo sessions run up to the configured cap or global 355-minute cutoff."
else
  echo "Routine Kilo sessions continue without a count cap until the global 355-minute cutoff."
fi
command=$(cat <<'PROMPT'
Execute the task assigned by the previous agent and prepare a task for the next agent!

If no prior agent assignment or handoff exists, inspect the repository and select one bounded, high-value task that can be implemented and verified in this session. Do not wait passively for an assignment that does not exist. Do not count control-marker-only commits as project progress.

GENERAL RELIABILITY AND PROGRESS RULES

1. PRESERVE THE WORKING BASELINE
- Keep the existing project and workflow architecture stable.
- Prefer the smallest reversible change that solves a demonstrated problem.
- Do not introduce parallel execution, redesign orchestration, or weaken permissions and safety controls merely because a task failed.
- Prioritize useful, durable progress over infrastructure perfection.

2. CHANGE APPROACH AFTER REPEATED FAILURE
- Track consecutive failures caused by the same underlying problem and approach.
- After five consecutive failures, do not repeat that same approach unchanged a sixth time.
- Record the observed failures and evidence, then choose a materially different approach.
- Changing wording, waiting, or retrying an identical operation with unchanged assumptions is not a materially different approach.
- Do not make speculative changes merely to satisfy this rule. If no safe, evidence-based alternative is apparent, consult loop-supervisor once before handing off; if it still cannot identify a safe alternative, preserve the evidence and prepare a clear handoff.
- Distinguish a recurring deterministic blocker from unrelated transient errors.

MANDATORY LOOP-SUPERVISOR PROTOCOL

A. CONTINUOUS SUPERVISION FROM WORKER START
- The controller starts a separate read/write-restricted `loop-supervisor` review process immediately before the first worker invocation. It reviews the current task and the latest worker/repository evidence immediately, then on a 150-second cadence.
- New or materially changed supervisor feedback is injected into the next worker tool result by the `loop-supervisor-feedback` plugin. Read it, assess it against current evidence, and either take the smallest safe verified action or explicitly explain why it is unsuitable.
- FILE-BACKED TWO-WAY DIALOGUE (mandatory, lightweight, non-blocking): the controller owns `.kilo-runtime/current-supervisor-recommendation.json`; never edit or replace it. The `.kilo-runtime/` directory is deliberately outside `.kilo/` because Kilo validates JSON files under `.kilo/` as configuration. When advice arrives, read that file and write/replace `.kilo-runtime/worker-disposition.json` within the next two tool calls, before unrelated exploration when practical. Use a JSON object with `schema_version: 1`, `recommendation_id` copied exactly from the current recommendation, `disposition` (one of `accepted`, `in_progress`, `verified`, `blocked`, `rejected_with_reason`, `superseded`), `reason`, `evidence`, `verification`, and `updated_at`. Include a concrete reason of at least one sentence; `verified` requires the actual verification result. `reason`, `evidence`, and `verification` must be JSON strings; `updated_at` should be an ISO-8601 UTC timestamp. Example: `{\"schema_version\":1,\"recommendation_id\":\"<exact id>\",\"disposition\":\"in_progress\",\"reason\":\"I reviewed the supervisor recommendation and am incorporating the relevant parts into this task.\",\"evidence\":\"Read the current recommendation file.\",\"verification\":\"\",\"updated_at\":\"<UTC timestamp>\"}`. Update the worker-owned disposition file as work progresses. If advice is unsafe, stale, technically incorrect, or conflicts with higher-priority requirements, record `rejected_with_reason` or `superseded` and explain why; never obey blindly. These runtime files are ignored locally and must not be committed. If the protocol file cannot be written, continue work safely; the controller will expose the outstanding recommendation again at bounded intervals.
- A scheduled review is not a promise that the model can interrupt a tool call or active generation. Feedback arrives at the next tool-result boundary. The monitor still records its scheduled review and status; the controller heartbeat reports status every 30 seconds.
- Do not spawn an additional background startup review; the controller-managed continuous monitor is authoritative. You may still invoke a targeted foreground supervisor task for a failure loop, using a unique report path.
- If the plugin, monitor, or supervisor is unavailable, continue the assigned task using the best available evidence. No supervisor failure may terminate or restart the worker.

B. ESCALATE TO A FOREGROUND SUPERVISOR ON A FAILURE LOOP
Consult `loop-supervisor` using a foreground Task call and await its result when any one condition is observed:
- Five consecutive failed attempts without a verified successful outcome.
- An alternating normalized failure pattern such as A/B/A/B, even though neither individual error occurred five times.
- The same underlying failure recurs after an attempted correction.
- Three attempts using substantially the same approach produce no meaningful improvement.
Do not escalate every transient error: if a retry succeeds and the relevant outcome is verified, continue normally. Normalize away timestamps, request IDs, volatile temporary paths, and line numbers when they do not change the underlying failure.

C. SEND EVIDENCE, NOT JUST AN ERROR LABEL
- Supply the actual relevant error/output, current objective and acceptance criteria, approaches already tried, changes made, and results of verification. Redact tokens, credentials, secrets, and personal data.
- Request one evidence-supported diagnosis and one materially different, reversible next step, plus a focused verification check.
- Use the session-scoped escalation report path supplied below. Keep supervisor calls sequential: do not launch concurrent duplicate reviews for the same failure cluster.
- After receiving advice, either apply a materially different approach and verify it, or explain why the advice is unsupported/infeasible and choose another evidence-based approach. If a new approach fails, the worker may escalate again with updated evidence; do not repeatedly ask the same question without testing or updating evidence.
- Treat the supervisor's returned Task result as the primary communication channel. The written report is supplementary traceability, not proof that the worker received or acted on the advice.

D. BOUNDS AND FAILURE BEHAVIOR
- The supervisor may diagnose and write only its report; the worker remains responsible for code changes, commands, tests, and commits.
- The supervisor cannot run shell commands, use the network, delegate to other agents, change configuration, control workflows, or end the worker session.
- A supervisor error, timeout, unavailable capability, or inconclusive answer must not end this worker session or the GitHub Actions run. Continue safely using available evidence.
- Before handing off an unresolved task, consult the supervisor once for that unresolved failure cluster unless it is unavailable or unsafe to do so. Then preserve a precise, evidence-based handoff.

3. HANDLE ERRORS PROPORTIONATELY
- For transient network, provider, rate-limit, timeout, and service errors, preserve progress, use bounded backoff, and honor available retry instructions.
- Avoid amplifying service outages with unnecessary parallel requests.
- For reproducible errors, investigate and fix the root cause with the smallest verifiable change.
- Do not repeatedly retry an operation when its prerequisites are known to be missing.

4. INSPECT AND VERIFY
- Inspect relevant error messages, logs, configuration, dependencies, and project conventions before changing things.
- Reproduce the smallest failure when practical and verify prerequisites before relying on them.
- Never claim a test, deployment, log review, or other check passed without evidence.
- After a change, rerun the focused check; run broader checks when useful.
- Never delete user data, disable validation, or weaken safety controls simply to make an error disappear.

5. PRESERVE DURABLE PROGRESS
- Inspect repository status and diffs before checkpointing.
- Preserve useful partial work and avoid unrelated modifications.
- Exclude secrets, credentials, caches, generated runtime data, and environment directories as appropriate.
- Use available formatting and whitespace checks.
- Respect repository boundaries and collaboration conventions.
- Reconcile remote changes instead of blindly overwriting them. When committing or pushing is part of the task, verify persistence.

6. PRIORITIZE RESULTS OVER ACTIVITY
- An unsuccessful session can still produce useful findings if they are recorded durably.
- A successful process exit does not prove the task was completed correctly.
- Fix cheap, deterministic blockers; tolerate isolated recoverable failures.
- Do not turn every operational imperfection into an infrastructure project.
- Prefer accumulated, verified improvements over optimizing solely for successful session exits.

7. USE SAFEGUARDS PROPORTIONATELY
- Encode critical, repeatable invariants in executable checks when practical.
- Use agent instructions for judgment and decisions that cannot reliably be reduced to deterministic checks.
- Preserve existing automation, permissions, checkpoint controls, and safety policies unless the assigned task explicitly requires a change and the change is justified.
- Avoid elaborate machinery for hypothetical failures without evidence that its benefits justify the complexity.
- Do not treat a prompt instruction as an independently enforced guarantee.

8. END EVERY SESSION WITH A USEFUL HANDOFF
State:
- What changed.
- What was actually verified.
- What remains unresolved.
- Which approaches have already failed and why.
- One precise next task, with relevant evidence and constraints.

If blocked, preserve useful progress and leave an evidence-based handoff. The next session must inspect that evidence rather than blindly repeating failed attempts.

DEFAULT OPERATING PRINCIPLE
Make progress despite imperfection. Fix cheap, deterministic blockers. Tolerate isolated recoverable failures. Protect durable progress and critical invariants. Change approach when evidence shows the current one is not working.
PROMPT
)
DEFAULT_BRANCH="$KILO_DEFAULT_BRANCH"

if [ -z "$DEFAULT_BRANCH" ]; then
  echo "::error::GitHub did not provide the default branch; refusing to report a successful activation."
  exit 1
fi

echo "Repository default branch: $DEFAULT_BRANCH"
write_progress "runtime-ready" "Kilo CLI installed; supervisor and worker are being prepared"

# Continuous supervisor starts before the first Kilo worker invocation and keeps
# reviewing the active attempt throughout the controller's cutoff-bound session loop.
SUPERVISOR_FEEDBACK_FILE="$RUNNER_TEMP/kilo-supervisor-feedback-${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}.md"
SUPERVISOR_FEEDBACK_CURSOR_FILE="$RUNNER_TEMP/kilo-supervisor-feedback-cursor-${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}.json"
SUPERVISOR_ACTIVE_LOG_POINTER="$RUNNER_TEMP/kilo-supervisor-active-attempt"
SUPERVISOR_OBJECTIVE_FILE="$RUNNER_TEMP/kilo-supervisor-objective-${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}.txt"
SUPERVISOR_LOOP_LOG="$RUNNER_TEMP/kilo-supervisor-loop-${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}.log"
SUPERVISOR_TRANSCRIPT_DIR="$RUNNER_TEMP/kilo-supervisor-transcripts-${GITHUB_RUN_ID:-local}-attempt-${GITHUB_RUN_ATTEMPT:-1}"
DIALOGUE_PROTOCOL_DIR="$PWD/.kilo-runtime"
mkdir -p "$SUPERVISOR_TRANSCRIPT_DIR" "$DIALOGUE_PROTOCOL_DIR"
# This runner-local exclude prevents the worker's checkpoint sweep from committing
# controller-owned recommendation state or worker-owned disposition state.
for ignore_pattern in '/.kilo-runtime/' '/.kilo/supervisor-reports/'; do
  if ! grep -qxF "$ignore_pattern" .git/info/exclude 2>/dev/null; then
    printf '%s\n' "$ignore_pattern" >> .git/info/exclude
  fi
done
rm -f "$DIALOGUE_PROTOCOL_DIR/current-supervisor-recommendation.json" "$DIALOGUE_PROTOCOL_DIR/worker-disposition.json"
export KILO_SUPERVISOR_PROTOCOL_DIR="$DIALOGUE_PROTOCOL_DIR"
: > "$SUPERVISOR_ACTIVE_LOG_POINTER"
: > "$SUPERVISOR_FEEDBACK_FILE"
rm -f "$SUPERVISOR_FEEDBACK_CURSOR_FILE"
printf '%s\n' "$command" > "$SUPERVISOR_OBJECTIVE_FILE"
export KILO_SUPERVISOR_FEEDBACK_FILE="$SUPERVISOR_FEEDBACK_FILE"
export KILO_SUPERVISOR_FEEDBACK_CURSOR_FILE="$SUPERVISOR_FEEDBACK_CURSOR_FILE"
export KILO_SUPERVISOR_TRANSCRIPT_DIR="$SUPERVISOR_TRANSCRIPT_DIR"
supervisor_loop_pid=""
write_progress "supervisor-starting" "launching independent 150-second-cadence review process"
python3 .github/scripts/kilo-supervisor-loop.py \
  --repo-root "$PWD" \
  --runtime-root "$RUNNER_TEMP" \
  --active-log-pointer "$SUPERVISOR_ACTIVE_LOG_POINTER" \
  --objective-file "$SUPERVISOR_OBJECTIVE_FILE" \
  --feedback-file "$SUPERVISOR_FEEDBACK_FILE" \
  --transcript-dir "$SUPERVISOR_TRANSCRIPT_DIR" \
  --report-dir .kilo/supervisor-reports \
  --kilo "$RUNNER_TEMP/kilo/node_modules/.bin/kilo" \
  --model kilo/kilo-auto/free \
  --interval-seconds 150 \
  --review-timeout-seconds 120 \
  --run-id "${GITHUB_RUN_ID:-local}" \
  --run-attempt "${GITHUB_RUN_ATTEMPT:-1}" \
  > >(tee -a "$SUPERVISOR_LOOP_LOG") 2>&1 &
supervisor_loop_pid=$!
echo "[loop-supervisor] Started alongside the Kilo worker; immediate review plus a 150-second cadence (PID $supervisor_loop_pid)."
echo "[loop-supervisor] Only actual supervisor-to-worker and worker-to-supervisor messages are emitted as live dialogue and saved to agent-dialogue.jsonl; review prompts, repository snapshots, and CLI diagnostics are not published."
echo "::notice title=Live agent dialogue::Expand the 'Run bash .github/scripts/kilo-controller.sh' step logs and search for 'LIVE AGENT DIALOGUE BOX — SUPERVISOR → WORKER' or 'LIVE AGENT DIALOGUE BOX — WORKER → SUPERVISOR'. Only new messages actually crossing a role boundary are shown."
write_progress "supervisor-running" "review loop launched"

heartbeat() {
  while true; do
    stamp="$(date -u +%Y-%m-%dT%H:%M:%S)"
    now_epoch="$(date +%s)"
    elapsed=$((now_epoch - WORKFLOW_STARTED_EPOCH))
    remaining=$((cutoff_epoch - now_epoch))
    if [ "$remaining" -lt 0 ]; then remaining=0; fi
    phase="$(progress_field phase)"
    detail="$(progress_field detail)"
    current_session="$(progress_field session)"
    current_attempt="$(progress_field attempt)"
    completed="$(progress_field completed)"
    failed="$(progress_field failed)"
    checkpoints="$(progress_field checkpoints)"
    verified_sha="$(progress_field verified_checkpoint_sha)"
    state_head="$(progress_field head)"
    state_time="$(progress_field updated_utc)"
    dirty_paths="$(git status --porcelain --untracked-files=all 2>/dev/null | wc -l | tr -d ' ' || printf 'unknown')"
    printf '[heartbeat] %sZ elapsed=%ss remaining=%ss phase=%s last_phase_at=%s session=%s/%s attempt=%s completed=%s failed=%s verified_checkpoints=%s verified_sha=%s head=%s dirty_paths=%s idle_watchdog=%ss detail="%s"\n' \
      "$stamp" "$elapsed" "$remaining" "${phase:-unknown}" "${state_time:-unknown}" \
      "${current_session:-0}" "$SESSION_LIMIT_POLICY" "${current_attempt:-0}" \
      "${completed:-0}" "${failed:-0}" "${checkpoints:-0}" "${verified_sha:-none}" "${state_head:-unknown}" \
      "${dirty_paths:-unknown}" "$KILO_IDLE_TIMEOUT_SECONDS" "${detail:-unknown}"
    active_log=""
    if [ -f "$HEARTBEAT_STATE_FILE" ]; then IFS= read -r active_log < "$HEARTBEAT_STATE_FILE" || true; fi
    if [ -n "$active_log" ] && [ -f "$active_log" ]; then
      last_output_epoch="$(stat -c '%Y' "$active_log" 2>/dev/null || printf '%s' "$now_epoch")"
      silent_for=$((now_epoch - last_output_epoch))
      printf '[activity] worker_log=%s output_silence=%ss idle_watchdog_remaining=%ss\n' "$(basename "$active_log")" "$silent_for" "$((KILO_IDLE_TIMEOUT_SECONDS - silent_for))"
      python3 - "$active_log" <<'PY'
import re
import sys
from pathlib import Path
try:
    lines = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace").splitlines()[-3:]
except OSError:
    lines = []
for line in lines:
    line = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", line)
    line = re.sub(r"(?i)(authorization\s*:\s*bearer)\s+\S+", r"\1 [REDACTED]", line)
    line = re.sub(r"(?i)\bbearer\s+[A-Za-z0-9._~+/\-=]{8,}", "Bearer [REDACTED]", line)
    line = re.sub(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b", "[REDACTED_GITHUB_TOKEN]", line)
    line = re.sub(r"\bsk-[A-Za-z0-9_-]{20,}\b", "[REDACTED_API_KEY]", line)
    line = re.sub(r"(?i)\b(GITHUB_TOKEN|GH_TOKEN|KILO_API_KEY|API_KEY|ACCESS_TOKEN|SECRET_KEY|PASSWORD)\s*[:=]\s*\S+", r"\1=[REDACTED]", line)
    line = " ".join(line.split())[:220]
    if line: print(f"[worker-tail] {line}")
PY
    else
      printf '[activity] no active worker invocation; phase=%s\n' "${phase:-unknown}"
    fi
    if [ -f "$SUPERVISOR_LOOP_LOG" ]; then
      review_started="$(grep -Ec '\[loop-supervisor\].*review [0-9]+ started' "$SUPERVISOR_LOOP_LOG" || true)"
      review_completed="$(grep -Ec '\[loop-supervisor\].*review [0-9]+ completed with usable report' "$SUPERVISOR_LOOP_LOG" || true)"
      review_timeouts="$(grep -Ec '\[loop-supervisor\].*review [0-9]+ timed out;' "$SUPERVISOR_LOOP_LOG" || true)"
      review_failures="$(grep -Ec '\[loop-supervisor\].*review [0-9]+ (returned exit|returned without writing|wrote an empty report|report could not be sanitized|failed to launch or complete|feedback append failed)' "$SUPERVISOR_LOOP_LOG" || true)"
      supervisor_event="$(grep -E '\[loop-supervisor\].*(review [0-9]+ started|review [0-9]+ completed with usable report|issued a new supervisor recommendation|complete;|timed out|returned exit|feedback append failed|stopped;|unexpected monitor failure)' "$SUPERVISOR_LOOP_LOG" | tail -n 1 | cut -c1-220 || true)"
    else
      review_started=0
      review_completed=0
      review_timeouts=0
      review_failures=0
      supervisor_event="no supervisor log yet"
    fi
    dialogue_file="$SUPERVISOR_TRANSCRIPT_DIR/agent-dialogue.jsonl"
    dialogue_transcripts="$(grep -c '"direction":' "$dialogue_file" 2>/dev/null || true)"
    delivery_transcripts="$(grep -c '"direction":"supervisor_to_worker"' "$dialogue_file" 2>/dev/null || true)"
    worker_replies="$(grep -c '"direction":"worker_to_supervisor"' "$dialogue_file" 2>/dev/null || true)"
    dialogue_transcripts="${dialogue_transcripts:-0}"
    delivery_transcripts="${delivery_transcripts:-0}"
    worker_replies="${worker_replies:-0}"
    read -r journal_units cursor_offset advice_entries < <(python3 - "$SUPERVISOR_FEEDBACK_FILE" "$SUPERVISOR_FEEDBACK_CURSOR_FILE" <<'PY'
import json
import sys
from pathlib import Path
journal_path, cursor_path = map(Path, sys.argv[1:3])
try:
    journal = journal_path.read_text(encoding="utf-8", errors="replace")
except OSError:
    journal = ""
try:
    cursor = json.loads(cursor_path.read_text(encoding="utf-8"))
    offset = int(cursor.get("offset", 0))
except (OSError, ValueError, TypeError, json.JSONDecodeError):
    offset = 0
print(len(journal.encode("utf-16-le")) // 2, offset, journal.count("--- SUPERVISOR ADVICE ENTRY"))
PY
    )
    journal_units="${journal_units:-0}"
    cursor_offset="${cursor_offset:-0}"
    advice_entries="${advice_entries:-0}"
    pending_units=$((journal_units - cursor_offset))
    if [ "$pending_units" -lt 0 ]; then pending_units=0; fi
    latest_transcript="$(find "$SUPERVISOR_TRANSCRIPT_DIR" -maxdepth 1 -type f -printf '%f\n' 2>/dev/null | sort | tail -n 1)"
    printf '[supervisor-status] reviews_started=%s reviews_completed=%s review_timeouts=%s review_failures=%s advice_entries=%s delivery_transcripts=%s dialogue_transcripts=%s journal_units=%s injected_cursor_units=%s queued_not_yet_injected_units=%s latest_event="%s" latest_transcript="%s"\n' \
      "${review_started:-0}" "${review_completed:-0}" "${review_timeouts:-0}" "${review_failures:-0}" "${advice_entries:-0}" "$delivery_transcripts" "$dialogue_transcripts" "$journal_units" "$cursor_offset" "$pending_units" "${supervisor_event:-unknown}" "${latest_transcript:-none}"
    sleep 30
  done
}

heartbeat &
heartbeat_pid=$!
write_progress "worker-loop-ready" "30-second live status heartbeat active"
trap 'kill "$heartbeat_pid" 2>/dev/null || true; if [ -n "${supervisor_loop_pid:-}" ]; then kill -TERM "$supervisor_loop_pid" 2>/dev/null || true; wait "$supervisor_loop_pid" 2>/dev/null || true; fi; rm -f "$HEARTBEAT_STATE_FILE" "$SUPERVISOR_ACTIVE_LOG_POINTER" "$SUPERVISOR_FEEDBACK_FILE" "$SUPERVISOR_FEEDBACK_CURSOR_FILE" "$SUPERVISOR_OBJECTIVE_FILE"' EXIT

# Project changes exclude workflow definitions and control-only markers.
project_worktree_changes() {
  {
    git status --porcelain --untracked-files=all | awk '{ print substr($0, 4) }'
    # Also count substantive commits an agent made directly during this session.
    git diff --name-only "${WORKFLOW_BASE_SHA:-HEAD}" HEAD
  } | awk '{
    path = $0
    if (path != "" &&
        path !~ /^\.github\/workflows\// &&
        path != ".kilo/TWO_AGENT_ONCE" &&
        path != ".kilo/SKIP_NEXT_ROUTINE_KILO") print path
  }' | sort -u
}

failed_sessions=0
sessions_completed=0
persisted_checkpoints=0
last_verified_checkpoint_sha="none"
consecutive_failures=0
idle_timeout_retry_count=0
project_progress=0
provider_pressure_streak=0
hard_provider_block=0
correction_failure_block=0
no_progress_block=0
cutoff=0

agent_index=0
while true; do
  if [ "$agent_index" -ge "$SESSION_LIMIT_POLICY" ]; then
    echo "::notice::Configured session target reached ($SESSION_LIMIT_POLICY); transient retries and corrective invocations remained count-unbounded until the 355-minute cutoff."
    break
  fi
  remaining=$((cutoff_epoch - $(date +%s)))
  if [ "$remaining" -le 0 ]; then
    cutoff=1
    break
  fi
  agent_index=$((agent_index + 1))
  WORKFLOW_BASE_SHA="$(git rev-parse HEAD)"
  session_log="$RUNNER_TEMP/kilo-session-${agent_index}.log"
  : > "$session_log"
  provider_pressure=0
  hard_provider_block=0
  correction_failure_block=0
  no_progress_block=0
  transient_retry_backoff=15
  session_attempt=0
  echo "Starting sequential Kilo session ${agent_index}; remaining safety budget ${remaining}s."
  write_progress "session-start" "starting session ${agent_index}; configured target=${SESSION_LIMIT_POLICY}; retries/corrections remain cutoff-bounded"
  while true; do
    session_attempt=$((session_attempt + 1))
    attempt_log="$RUNNER_TEMP/kilo-session-${agent_index}-attempt-${session_attempt}.log"
    remaining_global=$((cutoff_epoch - $(date +%s)))
    if [ "$remaining_global" -le 0 ]; then rc=124; echo "::warning::355-minute workflow cutoff reached before attempt ${session_attempt}."; break; fi
    : > "$attempt_log"
    printf '%s\n' "$attempt_log" > "$HEARTBEAT_STATE_FILE"
    printf '%s\n' "$attempt_log" > "$SUPERVISOR_ACTIVE_LOG_POINTER"
    echo "Kilo invocation attempt ${session_attempt} for session ${agent_index}; transient upstream failures retry without an attempt-count cap."
    write_progress "invocation-start" "Kilo worker process invoked"
    SESSION_REPORT_PREFIX=".kilo/supervisor-reports/run-${GITHUB_RUN_ID:-local}-attempt-${GITHUB_RUN_ATTEMPT:-1}-session-${agent_index}-invocation-${session_attempt}"
    session_command="${command}

SESSION-SCOPED SUPERVISOR OUTPUT CONTEXT
- GitHub Actions run ID: ${GITHUB_RUN_ID:-local}
- Run attempt: ${GITHUB_RUN_ATTEMPT:-1}
- Worker session index: ${agent_index}; CLI invocation attempt: ${session_attempt}
- Startup review report path: ${SESSION_REPORT_PREFIX}-startup.md
- For each later supervisor escalation, use ${SESSION_REPORT_PREFIX}-escalation-NN.md, replacing NN with a unique, increasing two-digit number for this invocation.
- Reports are temporary diagnostics under .kilo/supervisor-reports/ and must not be treated as research outputs or project deliverables.
"
    set +e
    timeout --signal=TERM --kill-after=10s "${remaining_global}s" python3 .github/scripts/kilo-invoke-with-idle-timeout.py --idle-timeout-seconds "$KILO_IDLE_TIMEOUT_SECONDS" -- kilo run --model kilo/kilo-auto/free --auto "$session_command" 2>&1 | tee "$attempt_log" | tee -a "$session_log"
    rc=${PIPESTATUS[0]}
    set -e
    rm -f "$HEARTBEAT_STATE_FILE"
    write_progress "invocation-exit" "Kilo invocation returned exit_code=${rc}"
    if [ "$rc" -eq 0 ]; then break; fi
    # Normalize ANSI color/control sequences before classifying provider errors.
    normalized_attempt_log="$attempt_log.normalized"
    python - "$attempt_log" "$normalized_attempt_log" <<'PY'
import re
import sys
from pathlib import Path

source, target = map(Path, sys.argv[1:3])
text = source.read_text(encoding="utf-8", errors="replace")
text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
target.write_text(text, encoding="utf-8")
PY
    if grep -Eiq 'current[:= ]*402.*limit[:= ]*400|insufficient.{0,20}(quota|credit)|quota.{0,30}(exceed|exhaust|limit)|exceed.{0,20}quota|billing.{0,30}(limit|quota)|account.{0,30}(limit|quota)|credits?.{0,20}(exhaust|deplet|limit)' "$normalized_attempt_log"; then
      hard_provider_block=1
      echo "::error::Hard provider quota/capacity limit detected; ending retries for this session. A fresh session will start while workflow time remains."
      break
    fi
    # Our own silence watchdog is a stall signal, not a network error worth repeating five times in place.
    if grep -Fq 'Kilo invocation idle timeout' "$normalized_attempt_log"; then
      idle_timeout_retry_count=$((idle_timeout_retry_count + 1))
      echo "::warning::Kilo invocation remained silent for ${KILO_IDLE_TIMEOUT_SECONDS}s; ending this invocation and preserving progress before the next session."
      break
    fi
    if grep -Eiq 'Upstream idle timeout exceeded|upstream.{0,40}idle.{0,40}timeout|ECONNRESET|ECONNREFUSED|ETIMEDOUT|EAI_AGAIN|ENETUNREACH|EHOSTUNREACH|socket hang up|fetch failed|temporary failure in name resolution|gateway timeout|bad gateway|service unavailable|too many requests|rate[ _-]?limit|resource[_ -]?exhausted|temporarily unavailable|HTTP.{0,12}(429|500|502|503|504)|status.{0,12}(429|500|502|503|504)' "$normalized_attempt_log"; then
      idle_timeout_retry_count=$((idle_timeout_retry_count + 1))
      retry_delay="$transient_retry_backoff"
      remaining_global=$((cutoff_epoch - $(date +%s)))
      if [ "$remaining_global" -le "$retry_delay" ]; then echo "::warning::Transient upstream/network failure detected, but insufficient workflow time remains for another retry."; break; fi
      echo "::warning::Transient upstream/network failure in session ${agent_index}; retry #${idle_timeout_retry_count} after ${retry_delay}s (no attempt-count cap; cutoff remains authoritative)."
      write_progress "retry-cooldown" "sleeping ${retry_delay}s before provider/network retry"
      sleep "$retry_delay"
      if [ "$transient_retry_backoff" -lt 300 ]; then
        transient_retry_backoff=$((transient_retry_backoff * 2))
        if [ "$transient_retry_backoff" -gt 300 ]; then transient_retry_backoff=300; fi
      fi
      continue
    fi
    break
  done
  # Keep corrective invocations running while time remains. Count attempts for traceability,
  # not as a termination condition; only verified durable progress or the global cutoff ends this loop.
  correction_reason=""
  if [ "$rc" -ne 0 ] && [ "$rc" -ne 124 ] && [ "$rc" -ne 137 ] && [ "$hard_provider_block" -eq 0 ] && [ -f "$normalized_attempt_log" ] && ! grep -Eiq 'Upstream idle timeout exceeded|upstream.{0,40}idle.{0,40}timeout|ECONNRESET|ECONNREFUSED|ETIMEDOUT|EAI_AGAIN|ENETUNREACH|EHOSTUNREACH|socket hang up|fetch failed|temporary failure in name resolution|gateway timeout|bad gateway|service unavailable|too many requests|rate[ _-]?limit|resource[_ -]?exhausted|temporarily unavailable|HTTP.{0,12}(429|500|502|503|504)|status.{0,12}(429|500|502|503|504)' "$normalized_attempt_log"; then
    correction_reason="non-transient Kilo invocation failure"
  elif [ "$rc" -eq 0 ] && [ "$hard_provider_block" -eq 0 ]; then
    current_project_changes="$(project_worktree_changes)"
    if [ -z "$current_project_changes" ]; then
      correction_reason="successful invocation produced no durable project changes"
    fi
  fi
  correction_attempt=0
  previous_recovery_log=""
  while [ -n "$correction_reason" ] && [ "$hard_provider_block" -eq 0 ] && [ "$(date +%s)" -lt "$cutoff_epoch" ]; do
    remaining_recovery=$((cutoff_epoch - $(date +%s)))
    if [ "$remaining_recovery" -lt 60 ]; then
      rc=1
      correction_failure_block=1
      echo "::warning::Less than 60 seconds remain for a useful corrective invocation; retaining evidence for the cutoff handoff."
      break
    fi
    correction_attempt=$((correction_attempt + 1))
    prior_record="${previous_recovery_log:-$session_log}"
    recovery_command=$(cat <<RECOVERY_PROMPT
Corrective invocation ${correction_attempt} for the ongoing Kilo task. The previous invocation failed or made no durable project changes. This is not a one-pass allowance: keep trying materially different, evidence-supported corrections until verified durable project progress is produced or the global 355-minute cutoff is reached.
Latest observed blocker: ${correction_reason}
Inspect the current worktree and the latest diagnostic record at: ${prior_record}
If this is not the first corrective invocation, inspect its previous corrective log and choose an approach materially different from prior failed approaches. Do not simply repeat the same operation with unchanged assumptions. Do not invent changes merely to create activity. Identify the smallest justified correction, implement it when safe, and run the narrowest relevant verification. Record what changed, the exact verification commands and outputs, and unresolved blockers in a durable handoff. Emit exactly one final machine-readable line CORRECTIVE_VERIFICATION=PASS only if focused verification actually succeeded; otherwise emit CORRECTIVE_VERIFICATION=BLOCKED and explain the blocker. Preserve research pre-registrations and promotion gates, tests, security controls, workflow boundaries, user data, and all safety requirements. If no safe correction is supported, preserve useful evidence and explain the next distinct investigation needed.
RECOVERY_PROMPT
)
    recovery_log="$RUNNER_TEMP/kilo-session-${agent_index}-recovery-${correction_attempt}.log"
    echo "::warning::${correction_reason}; starting corrective attempt ${correction_attempt} (no attempt-count cap before cutoff)."
    write_progress "corrective-attempt-start" "attempt=${correction_attempt}; ${correction_reason}"
    : > "$recovery_log"
    printf '%s\n' "$recovery_log" > "$HEARTBEAT_STATE_FILE"
    printf '%s\n' "$recovery_log" > "$SUPERVISOR_ACTIVE_LOG_POINTER"
    set +e
    KILO_PRIOR_FAILURE_LOG="$prior_record" timeout --signal=TERM --kill-after=10s "${remaining_recovery}s" python3 .github/scripts/kilo-invoke-with-idle-timeout.py --idle-timeout-seconds "$KILO_IDLE_TIMEOUT_SECONDS" -- kilo run --model kilo/kilo-auto/free --auto "$recovery_command" 2>&1 | tee "$recovery_log" | tee -a "$session_log"
    recovery_rc=${PIPESTATUS[0]}
    set -e
    rm -f "$HEARTBEAT_STATE_FILE"
    write_progress "corrective-attempt-exit" "attempt=${correction_attempt}; exit_code=${recovery_rc}"
    mkdir -p "$RUNNER_TEMP/kilo-failure-logs"
    tail -n 2000 "$session_log" > "$RUNNER_TEMP/kilo-failure-logs/corrective-session-${agent_index}.log" || true
    previous_recovery_log="$recovery_log"
    if [ "$recovery_rc" -eq 0 ]; then
      if ! grep -Fxq 'CORRECTIVE_VERIFICATION=PASS' "$recovery_log"; then
        rc=1
        correction_failure_block=1
        correction_reason="corrective invocation did not provide verified-success evidence"
        echo "::error::Corrective invocation exited successfully but lacked the required successful-verification marker; another evidence-led attempt may try a different approach."
      elif ! git diff --check || ! git diff --cached --check; then
        rc=1
        correction_failure_block=1
        correction_reason="corrective invocation failed git diff checks"
        echo "::error::Corrective invocation failed git diff checks; retaining diagnostic evidence and trying a distinct correction."
      else
        corrected_project_changes="$(project_worktree_changes)"
        if [ -z "$corrected_project_changes" ]; then
          rc=1
          no_progress_block=1
          correction_reason="successful invocation produced no durable project changes"
          echo "::warning::Corrective invocation produced no durable project changes; evidence is retained and another corrective attempt will use it to choose a different approach."
        else
          rc=0
          correction_reason=""
          echo "::notice::Corrective invocation produced durable project changes, passed git diff checks, and reported focused verification success."
          break
        fi
      fi
    else
      rc="$recovery_rc"
      correction_failure_block=1
      correction_reason="corrective invocation exited with status ${recovery_rc}"
      echo "::warning::Corrective invocation ${correction_attempt} failed (exit ${recovery_rc}); the next attempt will inspect its output and change approach."
    fi
  done
  if [ "$rc" -ne 0 ]; then
    mkdir -p "$RUNNER_TEMP/kilo-failure-logs"
    tail -n 2000 "$session_log" > "$RUNNER_TEMP/kilo-failure-logs/session-${agent_index}.log" || true
    if grep -Eiq '(^|[^0-9])429([^0-9]|$)|rate[ _-]?limit|resource[_ -]?exhausted|quota.*(exceed|limit)|current[:= ]*402.*limit[:= ]*400' "$session_log"; then
      provider_pressure=1
      provider_pressure_streak=$((provider_pressure_streak + 1))
      echo "::warning::Provider quota/capacity failure detected; applying a longer cooldown."
    else
      provider_pressure_streak=0
    fi
  elif [ "$rc" -eq 0 ]; then
    provider_pressure_streak=0
  fi

  if [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ]; then
    if [ "$(date +%s)" -ge "$cutoff_epoch" ]; then
      cutoff=1
      echo "::warning::355-minute safety cutoff reached; saving the last possible checkpoint."
    else
      consecutive_failures=$((consecutive_failures + 1))
      failed_sessions=$((failed_sessions + 1))
      echo "::warning::Kilo invocation returned timeout status before the global cutoff or was terminated (failure streak: $consecutive_failures); continuing with a fresh session when time remains."
    fi
  elif [ "$rc" -ne 0 ]; then
    consecutive_failures=$((consecutive_failures + 1))
    failed_sessions=$((failed_sessions + 1))
    echo "::warning::Kilo session exited with status $rc (failure streak: $consecutive_failures; no failure-count cutoff)."
  else
    consecutive_failures=0
  fi

  # Keep Actions workflow definitions maintainer-managed. Restore tracked
  # workflow files to the revision at session start and remove agent-created
  # workflow files before creating the checkpoint commit.
  if ! git restore --source="$WORKFLOW_BASE_SHA" --staged --worktree -- .github/workflows; then
    echo "::warning::Could not fully restore workflow files; workflow paths remain excluded."
  fi
  git clean -fd -- .github/workflows || true

  # Consume the one-shot trigger after session two, if a smaller configured
  # cap ends the activation earlier, or at the global cutoff.
  if [ "$one_shot_mode" -eq 1 ] && { [ "$agent_index" -ge 2 ] || [ "$(date +%s)" -ge "$cutoff_epoch" ]; }; then
    mkdir -p .kilo
    if printf '%s\n' 'Skip one routine Kilo activation after the one-shot validation-gated activation.' > .kilo/SKIP_NEXT_ROUTINE_KILO; then
      rm -f -- .kilo/TWO_AGENT_ONCE || echo "::warning::Could not remove the one-shot marker; routine activations remain safely gated."
    else
      echo "::warning::Could not write the post-run skip marker; retaining the one-shot marker for recovery."
    fi
  fi

  stage_repository_changes() {
    git add -A -- . \
      ':(exclude).github/workflows/**' \
      ':(exclude)**/*.pyc' ':(exclude)**/*.pyo' \
      ':(exclude)**/*.sqlite' ':(exclude)**/*.sqlite3' ':(exclude)**/*.db' \
      ':(exclude)**/*.sqlite-wal' ':(exclude)**/*.sqlite-shm' \
      ':(exclude)**/*.sqlite3-wal' ':(exclude)**/*.sqlite3-shm' \
      ':(exclude)**/*.db-wal' ':(exclude)**/*.db-shm' \
      ':(exclude)**/*.tmp' ':(exclude)**/coverage.xml' ':(exclude)**/.coverage' \
      ':(exclude)**/kilo-session-*.log'
  }
  write_progress "checkpoint-staging" "staging project changes; workflow definitions excluded"
  checkpoint_ready=1
  if ! stage_repository_changes; then
    echo "::warning::Staging failed; preserving worktree and allowing the next session to retry."
    checkpoint_ready=0
  fi

  # Repair generated trailing whitespace and extra blank lines at EOF
  # before enforcing the staged-diff check.
  if ! git diff --cached --check; then
    echo "::warning::Normalizing trailing whitespace and blank lines at EOF in changed text files."
    if ! python - <<'PY'
import os
import re
import subprocess
from pathlib import Path

staged_paths = subprocess.check_output(
    ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"]
).split(b"\0")

for raw_path in staged_paths:
    if not raw_path:
        continue
    path = Path(os.fsdecode(raw_path))
    if path.is_symlink() or not path.is_file():
        continue

    content = path.read_bytes()
    if b"\0" in content:
        continue

    cleaned = re.sub(rb"[ \t]+(?=\r?$)", b"", content, flags=re.MULTILINE)
    # Collapse trailing empty/whitespace-only lines to a single final newline.
    cleaned = re.sub(rb"(?:[ \t]*\r?\n)+\Z", b"\n", cleaned)
    if cleaned != content:
        path.write_bytes(cleaned)
PY
    then
      echo "::warning::Whitespace normalizer failed; deferring checkpoint to a fresh session."
      checkpoint_ready=0
    else
    if ! stage_repository_changes; then
      echo "::warning::Restaging after whitespace repair failed; deferring this checkpoint."
      checkpoint_ready=0
    fi
    fi
  fi

  if [ "$checkpoint_ready" -eq 1 ] && ! git diff --cached --check; then
    echo "::warning::Whitespace check still fails after normalization; deferring this checkpoint and continuing with a fresh session."
    checkpoint_ready=0
  fi

  checkpoint_has_project_changes=0
  if [ "$checkpoint_ready" -eq 1 ] && ! git diff --cached --quiet; then
    while IFS= read -r -d '' changed_path; do
      case "$changed_path" in
        .kilo/TWO_AGENT_ONCE|.kilo/SKIP_NEXT_ROUTINE_KILO) ;;
        *) checkpoint_has_project_changes=1 ;;
      esac
    done < <(git diff --cached --name-only -z)
  fi
  committed_this_iteration=0
  if [ "$checkpoint_ready" -eq 1 ] && ! git diff --cached --quiet; then
    if git commit --allow-empty-message -m ""; then
      committed_this_iteration=1
      write_progress "checkpoint-committed" "local checkpoint created; remote verification pending"
    else
      echo "::warning::Checkpoint commit failed; retaining worktree for the next session."
      checkpoint_ready=0
    fi
  fi

  # Keep persistence logic independently testable; this is the exact production routine.
  persist_current_checkpoint

  if [ "$hard_provider_block" -eq 1 ]; then
    echo "::warning::This session hit a hard provider quota/capacity limit. The session is ending; a fresh session may retry while workflow time remains."
  elif [ "$provider_pressure_streak" -ge 3 ]; then
    echo "::warning::Provider rate-limit/capacity errors have recurred across sessions. Continuing with the existing session-level cooldown policy until the global cutoff."
  elif [ "$correction_failure_block" -eq 1 ]; then
    echo "::warning::Corrective attempts did not verify durable progress in this session; evidence and checkpoints are preserved, and later sessions may continue until cutoff."
  elif [ "$no_progress_block" -eq 1 ]; then
    echo "::warning::The corrective session produced no durable project progress. Preserving the evidence and starting another session while time remains."
  fi
  if [ "$consecutive_failures" -ge 5 ]; then
    echo "::warning::At least five consecutive sessions have failed; continuing with fresh sessions rather than ending the action."
  fi
  sessions_completed=$((sessions_completed + 1))
  write_progress "session-complete" "exit_code=${rc} persisted=${persisted} progress=${project_progress}"
  if [ "$cutoff" -eq 1 ]; then
    break
  fi
  if [ "$provider_pressure" -eq 1 ]; then
    case "$provider_pressure_streak" in
      1) backoff_seconds=300 ;;
      2) backoff_seconds=600 ;;
      *) backoff_seconds=900 ;;
    esac
    remaining=$((cutoff_epoch - $(date +%s)))
    if [ "$backoff_seconds" -gt "$remaining" ]; then backoff_seconds="$remaining"; fi
    if [ "$backoff_seconds" -gt 0 ]; then
      echo "Provider cooldown: waiting ${backoff_seconds}s; no fixed failure-count limit."
      write_progress "provider-cooldown" "waiting ${backoff_seconds}s due to provider pressure"
      sleep "$backoff_seconds"
    fi
  elif [ "$consecutive_failures" -gt 0 ]; then
    case "$consecutive_failures" in
      1) backoff_seconds=15 ;;
      2) backoff_seconds=30 ;;
      3) backoff_seconds=60 ;;
      *) backoff_seconds=120 ;;
    esac
    jitter_seconds=$((RANDOM % 8))
    backoff_seconds=$((backoff_seconds + jitter_seconds))
    echo "Waiting ${backoff_seconds}s before the next agent session to reduce transient provider/network contention."
    write_progress "session-cooldown" "waiting ${backoff_seconds}s before next session"
    sleep "$backoff_seconds"
  fi
done

if [ "$cutoff" -eq 1 ]; then
  echo "::warning::The 355-minute safety cutoff was reached; see checkpoint verification messages above."
fi
if [ "$cutoff" -eq 1 ]; then
  write_progress "controller-finished" "355-minute hard cutoff reached"
else
  write_progress "controller-finished" "controller loop finished before cutoff"
fi
# Publish only role-dialogue records; raw protocol state files remain runner-local.
read -r final_journal_units final_cursor_offset final_advice_entries < <(python3 - "$SUPERVISOR_FEEDBACK_FILE" "$SUPERVISOR_FEEDBACK_CURSOR_FILE" <<'PY'
import json
import sys
from pathlib import Path
journal_path, cursor_path = map(Path, sys.argv[1:3])
try:
    journal = journal_path.read_text(encoding="utf-8", errors="replace")
except OSError:
    journal = ""
try:
    cursor = json.loads(cursor_path.read_text(encoding="utf-8"))
    offset = int(cursor.get("offset", 0))
except (OSError, ValueError, TypeError, json.JSONDecodeError):
    offset = 0
print(len(journal.encode("utf-16-le")) // 2, offset, journal.count("--- SUPERVISOR ADVICE ENTRY"))
PY
)
final_pending_units=$((final_journal_units - final_cursor_offset))
if [ "$final_pending_units" -lt 0 ]; then final_pending_units=0; fi
final_review_count="$(grep -Ec '\[loop-supervisor\].*review [0-9]+ started' "$SUPERVISOR_LOOP_LOG" || true)"
final_completed_review_count="$(grep -Ec '\[loop-supervisor\].*review [0-9]+ completed with usable report' "$SUPERVISOR_LOOP_LOG" || true)"
final_timeout_count="$(grep -Ec '\[loop-supervisor\].*review [0-9]+ timed out;' "$SUPERVISOR_LOOP_LOG" || true)"
final_review_failure_count="$(grep -Ec '\[loop-supervisor\].*review [0-9]+ (returned exit|returned without writing|wrote an empty report|report could not be sanitized|failed to launch or complete|feedback append failed)' "$SUPERVISOR_LOOP_LOG" || true)"
dialogue_file="$SUPERVISOR_TRANSCRIPT_DIR/agent-dialogue.jsonl"
final_dialogue_count="$(grep -c '"direction":' "$dialogue_file" 2>/dev/null || true)"
final_delivery_count="$(grep -c '"direction":"supervisor_to_worker"' "$dialogue_file" 2>/dev/null || true)"
final_worker_reply_count="$(grep -c '"direction":"worker_to_supervisor"' "$dialogue_file" 2>/dev/null || true)"
final_delivery_count="${final_delivery_count:-0}"
final_dialogue_count="${final_dialogue_count:-0}"
final_worker_reply_count="${final_worker_reply_count:-0}"
printf 'project_progress=%s\n' "$project_progress" >> "$GITHUB_OUTPUT"
printf 'failed_sessions=%s\n' "$failed_sessions" >> "$GITHUB_OUTPUT"
printf 'idle_timeout_retries=%s\n' "$idle_timeout_retry_count" >> "$GITHUB_OUTPUT"
printf 'session_limit=%s\n' "$SESSION_LIMIT_POLICY" >> "$GITHUB_OUTPUT"
printf 'sessions_started=%s\n' "$agent_index" >> "$GITHUB_OUTPUT"
printf 'sessions_completed=%s\n' "$sessions_completed" >> "$GITHUB_OUTPUT"
printf 'persisted_checkpoints=%s\n' "$persisted_checkpoints" >> "$GITHUB_OUTPUT"
printf 'last_verified_checkpoint_sha=%s\n' "$last_verified_checkpoint_sha" >> "$GITHUB_OUTPUT"
printf 'supervisor_review_count=%s\n' "$final_review_count" >> "$GITHUB_OUTPUT"
printf 'supervisor_reviews_completed=%s\n' "$final_completed_review_count" >> "$GITHUB_OUTPUT"
printf 'supervisor_review_timeouts=%s\n' "$final_timeout_count" >> "$GITHUB_OUTPUT"
printf 'supervisor_review_failures=%s\n' "$final_review_failure_count" >> "$GITHUB_OUTPUT"
printf 'supervisor_delivery_transcripts=%s\n' "$final_delivery_count" >> "$GITHUB_OUTPUT"
printf 'supervisor_dialogue_transcripts=%s\n' "$final_dialogue_count" >> "$GITHUB_OUTPUT"
printf 'supervisor_worker_replies=%s\n' "$final_worker_reply_count" >> "$GITHUB_OUTPUT"
printf 'supervisor_advice_entries=%s\n' "$final_advice_entries" >> "$GITHUB_OUTPUT"
printf 'supervisor_pending_units=%s\n' "$final_pending_units" >> "$GITHUB_OUTPUT"
printf 'final_phase=%s\n' "$(progress_field phase)" >> "$GITHUB_OUTPUT"
printf 'final_phase_detail=%s\n' "$(progress_field detail)" >> "$GITHUB_OUTPUT"
if [ "$failed_sessions" -gt 0 ]; then
  echo "::warning::$failed_sessions Kilo session(s) failed during this activation. Session-level failures did not stop the action; upstream idle/network retries: $idle_timeout_retry_count."
fi
if [ "$project_progress" -ne 1 ]; then
  echo "::warning::No meaningful repository change was confirmed before the action ended. Review the preserved session logs and checkpoints."
fi
if [ "$cutoff" -eq 1 ]; then
  echo "Kilo controller reached the global 355-minute safety cutoff. Sessions started: $agent_index; failed sessions: $failed_sessions; upstream idle/network retries: $idle_timeout_retry_count."
else
  echo "Kilo controller finished at the configured session target or cutoff. Sessions started: $agent_index; failed sessions: $failed_sessions; upstream idle/network retries: $idle_timeout_retry_count."
fi

# A successful final echo is not evidence of a successful repository outcome.
# Recheck the worktree so unstaged substantive changes cannot be reported as durable progress.
terminal_status_file="${RUNNER_TEMP:-/tmp}/kilo-terminal-git-status-${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}.txt"
if ! git status --porcelain --untracked-files=all > "$terminal_status_file"; then
  printf '?? terminal-status-check-unavailable\n' > "$terminal_status_file"
fi
set +e
python3 .github/scripts/kilo-terminal-outcome.py \
  --project-progress "${project_progress:-0}" \
  --checkpoint-persisted "${persisted:-0}" \
  --git-status-file "$terminal_status_file" \
  --cutoff "$cutoff" \
  --checkpoint-sha "$(git rev-parse HEAD 2>/dev/null || printf 'unknown')" \
  --output "${GITHUB_OUTPUT:-}"
terminal_exit_code=$?
set -e
exit "$terminal_exit_code"
