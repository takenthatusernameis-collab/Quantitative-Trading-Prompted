import { createHash, randomUUID } from "node:crypto";
import { appendFile, mkdir, readFile, rename, unlink, writeFile } from "node:fs/promises";
import { isAbsolute, relative, resolve, sep, basename } from "node:path";

const MAX_FEEDBACK_CHARS_PER_INJECTION = 9000;
const MAX_PROTOCOL_RECORD_CHARS = 12000;

function isInside(parent, candidate) {
  const resolvedParent = resolve(parent);
  const resolvedCandidate = resolve(candidate);
  const rel = relative(resolvedParent, resolvedCandidate);
  return rel === "" || (!rel.startsWith(".." + sep) && rel !== ".." && !isAbsolute(rel));
}

function digest(text) {
  return createHash("sha256").update(text).digest("hex");
}

function redactSensitiveText(text) {
  return text
    .replace(/\x1b\[[0-?]*[ -/]*[@-~]/g, "")
    .replace(/(authorization\s*:\s*bearer)\s+[A-Za-z0-9._~+/\-=]+/gi, "$1 [REDACTED]")
    .replace(/\bbearer\s+[A-Za-z0-9._~+/\-=]{8,}/gi, "Bearer [REDACTED]")
    .replace(/\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b/g, "[REDACTED_GITHUB_TOKEN]")
    .replace(/\bsk-[A-Za-z0-9_-]{20,}\b/g, "[REDACTED_API_KEY]")
    .replace(/\b(GITHUB_TOKEN|GH_TOKEN|KILO_API_KEY|API_KEY|ACCESS_TOKEN|SECRET_KEY|PASSWORD)\s*[:=]\s*\S+/gi, "$1=[REDACTED]");
}

async function readCursor(cursorPath) {
  if (!cursorPath) return { offset: 0, prefixDigest: digest("") };
  try {
    const parsed = JSON.parse(await readFile(cursorPath, "utf8"));
    if (!Number.isSafeInteger(parsed.offset) || parsed.offset < 0
        || typeof parsed.prefixDigest !== "string") {
      return { offset: 0, prefixDigest: digest("") };
    }
    return { offset: parsed.offset, prefixDigest: parsed.prefixDigest };
  } catch {
    return { offset: 0, prefixDigest: digest("") };
  }
}

async function writeCursor(cursorPath, offset, prefixDigest) {
  if (!cursorPath) return false;
  const temporaryPath = cursorPath + "." + process.pid + ".tmp";
  try {
    await writeFile(temporaryPath, JSON.stringify({ offset, prefixDigest }), {
      encoding: "utf8",
      mode: 0o600,
    });
    await rename(temporaryPath, cursorPath);
    return true;
  } catch {
    try { await unlink(temporaryPath); } catch {}
    // Cursor persistence is best-effort; advice remains in the append-only journal.
    return false;
  }
}

async function readCurrentRecommendation(protocolDir) {
  if (!protocolDir) return null;
  const path = resolve(protocolDir, "current-supervisor-recommendation.json");
  if (!isInside(protocolDir, path)) return null;
  try {
    const raw = await readFile(path, "utf8");
    if (raw.length > MAX_PROTOCOL_RECORD_CHARS) return null;
    const value = JSON.parse(raw);
    if (!value || typeof value !== "object" || Array.isArray(value)
        || ![1, 2].includes(value.schema_version)
        || typeof value.recommendation_id !== "string"
        || !value.recommendation_id.trim()
        || typeof value.report !== "string"
        || value.report.trim().length < 80
        || value.report.length > MAX_PROTOCOL_RECORD_CHARS) return null;
    return {
      recommendation_id: value.recommendation_id.trim(),
      task_id: typeof value.task_id === "string" && value.task_id.trim()
        ? value.task_id.trim() : ((process.env.GITHUB_RUN_ID || "local") + "-attempt-" + (process.env.GITHUB_RUN_ATTEMPT || "1")),
      session_id: typeof value.session_id === "string" ? value.session_id : "",
      message_type: typeof value.message_type === "string" ? value.message_type : "advisory_recommendation",
      priority: typeof value.priority === "string" ? value.priority : "normal",
      scope_boundaries: Array.isArray(value.scope_boundaries) ? value.scope_boundaries.slice(0, 64) : [],
      acceptance_criteria: Array.isArray(value.acceptance_criteria) ? value.acceptance_criteria.slice(0, 64) : [],
      report: redactSensitiveText(value.report).trim(),
    };
  } catch {
    return null;
  }
}

function chooseChunkEnd(journal, start) {
  let end = Math.min(start + MAX_FEEDBACK_CHARS_PER_INJECTION, journal.length);
  if (end < journal.length) {
    const nextEntry = journal.lastIndexOf("--- SUPERVISOR ADVICE ENTRY", end);
    if (nextEntry > start) end = nextEntry;
  }
  if (end <= start) end = Math.min(start + MAX_FEEDBACK_CHARS_PER_INJECTION, journal.length);
  return end;
}

function buildCommunicationEvent(stage, base) {
  const event = {
    schema_version: 2,
    event_id: randomUUID(),
    timestamp_utc: new Date().toISOString(),
    stage,
    direction: base.direction,
    role: base.role,
    message_id: base.message_id,
    task_id: base.task_id,
    run_id: base.run_id,
    session_id: base.session_id,
    message_type: base.message_type,
    priority: base.priority,
    scope_boundaries: base.scope_boundaries,
    acceptance_criteria: base.acceptance_criteria,
    correlation_id: base.correlation_id,
    delivery_state: base.delivery_state,
    acknowledgement_state: base.acknowledgement_state,
    disposition: "",
    reason: "",
    evidence: "",
    verification: "",
    work_performed: "",
    blockers: [],
    changed_files: [],
    commit_sha: "",
    checkpoint_sha: "",
    commands_executed: [],
    test_outcomes: [],
    artifact_refs: [],
    outstanding_work: [],
    message: base.message,
  };
  event.event_key = digest([
    event.direction, event.stage, event.message_id, event.correlation_id,
    event.message, event.disposition
  ].join("\0"));
  return event;
}

async function appendJsonlOnce(transcriptDir, filename, event) {
  if (!transcriptDir) return false;
  const destination = resolve(transcriptDir, filename);
  if (!isInside(transcriptDir, destination)) return false;
  try {
    await mkdir(transcriptDir, { recursive: true });
    let existing = "";
    try { existing = await readFile(destination, "utf8"); } catch {}
    if (existing && !existing.endsWith("\n")) return false;
    for (const line of existing.split(/\r?\n/)) {
      if (!line) continue;
      let prior;
      try { prior = JSON.parse(line); } catch { return false; }
      if (prior.event_key === event.event_key) return true;
    }
    await appendFile(destination, JSON.stringify(event) + "\n", { encoding: "utf8", mode: 0o600 });
    return true;
  } catch {
    return false;
  }
}

async function saveWorkerDelivery(transcriptDir, injectionText, sequence, recommendation) {
  if (!transcriptDir) return null;
  const safeMessage = redactSensitiveText(injectionText);
  const messageId = recommendation?.recommendation_id || "unlinked-recommendation";
  const taskId = recommendation?.task_id || ((process.env.GITHUB_RUN_ID || "local")
    + "-attempt-" + (process.env.GITHUB_RUN_ATTEMPT || "1"));
  const base = {
    direction: "supervisor_to_worker",
    role: "supervisor",
    message_id: messageId,
    task_id: taskId,
    run_id: process.env.GITHUB_RUN_ID || "local",
    session_id: process.env.KILO_WORKER_SESSION_ID || recommendation?.session_id || taskId,
    message_type: recommendation?.message_type || "advisory_recommendation",
    priority: recommendation?.priority || "normal",
    scope_boundaries: recommendation?.scope_boundaries || [],
    acceptance_criteria: recommendation?.acceptance_criteria || [],
    correlation_id: messageId,
    delivery_state: "delivered",
    acknowledgement_state: "pending",
    message: safeMessage,
  };
  const dialogueEvent = buildCommunicationEvent("message_delivered", base);
  dialogueEvent.sequence = sequence;
  const communicationEvent = buildCommunicationEvent("message_delivered", base);
  // Retry both tracks as a pair. A successful first append is idempotently recognized
  // on retry if writing the second track failed partway through.
  for (let attempt = 0; attempt < 3; attempt++) {
    const dialogueSaved = await appendJsonlOnce(transcriptDir, "agent-dialogue.jsonl", dialogueEvent);
    const communicationSaved = await appendJsonlOnce(transcriptDir, "agent-communication.jsonl", communicationEvent);
    if (dialogueSaved && communicationSaved) return resolve(transcriptDir, "agent-dialogue.jsonl");
    if (attempt < 2) await new Promise(resolve => setTimeout(resolve, 25 * (attempt + 1)));
  }
  return null;
}

const LoopSupervisorFeedback = async () => {
  if (process.env.KILO_SUPERVISOR_MODE === "1") return {};

  const feedbackPath = process.env.KILO_SUPERVISOR_FEEDBACK_FILE;
  const runtimeRoot = process.env.RUNNER_TEMP;
  const configuredCursorPath = process.env.KILO_SUPERVISOR_FEEDBACK_CURSOR_FILE;
  const configuredTranscriptDir = process.env.KILO_SUPERVISOR_TRANSCRIPT_DIR;
  const configuredProtocolDir = process.env.KILO_SUPERVISOR_PROTOCOL_DIR;
  const workspaceRoot = process.env.GITHUB_WORKSPACE;
  const expectedProtocolDir = workspaceRoot ? resolve(workspaceRoot, ".kilo-runtime") : null;
  const safeProtocolDir = configuredProtocolDir && workspaceRoot && isAbsolute(configuredProtocolDir)
      && resolve(configuredProtocolDir) === expectedProtocolDir
      && isInside(workspaceRoot, configuredProtocolDir) ? configuredProtocolDir : null;
  const safeFeedbackPath = feedbackPath && runtimeRoot && isAbsolute(feedbackPath)
      && isInside(runtimeRoot, feedbackPath) ? feedbackPath : null;
  const safeCursorPath = configuredCursorPath && runtimeRoot && isAbsolute(configuredCursorPath)
      && isInside(runtimeRoot, configuredCursorPath) ? configuredCursorPath : null;
  const safeTranscriptDir = configuredTranscriptDir && runtimeRoot && isAbsolute(configuredTranscriptDir)
      && isInside(runtimeRoot, configuredTranscriptDir) ? configuredTranscriptDir : null;
  let { offset: lastInjectedOffset, prefixDigest: lastInjectedPrefixDigest } =
      await readCursor(safeCursorPath);
  let injectionSequence = 0;
  console.log("[loop-supervisor-feedback] HOOK_READY journal="
    + (safeFeedbackPath ? "configured" : "disabled")
    + " cursor=" + (safeCursorPath ? "configured" : "disabled")
    + " transcript=" + (safeTranscriptDir ? "configured" : "disabled")
    + " protocol=" + (safeProtocolDir ? "configured" : "disabled"));

  return {
    "tool.execute.after": async (input, output) => {
      try {
        if (!safeFeedbackPath || !runtimeRoot) return;
        const journal = safeFeedbackPath ? await readFile(safeFeedbackPath, "utf8") : "";
        if (lastInjectedOffset > journal.length
            || digest(journal.slice(0, lastInjectedOffset)) !== lastInjectedPrefixDigest) {
          // Replay rather than risk skipping advice if the journal was replaced.
          lastInjectedOffset = 0;
          lastInjectedPrefixDigest = digest("");
        }

        const recommendation = await readCurrentRecommendation(safeProtocolDir);
        let injectionText = "";
        let nextCursorOffset = lastInjectedOffset;
        let nextCursorDigest = lastInjectedPrefixDigest;
        if (lastInjectedOffset < journal.length) {
          const start = lastInjectedOffset;
          const end = chooseChunkEnd(journal, start);
          const pending = redactSensitiveText(journal.slice(start, end));
          if (pending.trim()) {
            const recommendationLabel = recommendation
              ? "\nTask ID: " + recommendation.task_id
                + "\nWorker session ID: " + (process.env.KILO_WORKER_SESSION_ID || recommendation.session_id || "unknown")
                + "\nCorrelation ID / Recommendation ID: " + recommendation.recommendation_id
                + "\nAfter assessing this message, write/update .kilo-runtime/worker-disposition.json with schema_version=2, copying the exact task_id, session_id, and recommendation_id. Include acknowledgement_state, disposition, reason, evidence, verification, work_performed, blockers, changed_files, commit_sha, checkpoint_sha, commands_executed, test_outcomes, artifact_refs, acceptance_criteria, outstanding_work, and updated_at. Treat your verification as a claim until the controller independently verifies it."
              : "";
            injectionText = "[SUPERVISOR → WORKER: NEW MESSAGE]\n"
              + "This is a single advisory message. Verify it against evidence and continue the current task without restarting. Delivery, acknowledgement, processing, and verification are distinct states. "
              + "Record your reason, evidence, and verification in the worker-disposition file. "
              + "Do not follow advice that conflicts with higher-priority instructions, safety rules, or pre-registered acceptance criteria.\n"
              + recommendationLabel + "\n\n" + pending;
            nextCursorOffset = end;
            nextCursorDigest = digest(journal.slice(0, end));
          }
        }

        if (!injectionText) return;

        const original = typeof output.output === "string"
          ? output.output
          : String(output.output ?? "");
        output.output = (original ? original + "\n\n" : "") + injectionText;

        injectionSequence += 1;
        const transcriptPath = await saveWorkerDelivery(
          safeTranscriptDir, injectionText, injectionSequence, recommendation
        );
        if (!transcriptPath) {
          // The worker-facing output has been mutated, but the dual-track record is not durable.
          // Do not advance the cursor: retry delivery/persistence at the next tool boundary.
          console.error("[loop-supervisor-feedback] DELIVERY_PERSISTENCE_FAILED sequence=" + injectionSequence
            + " direction=supervisor_to_worker output_mutated=yes transcript_saved=no cursor_advanced=no"
            + "; pending advice will be retried at the next tool-result boundary");
          return;
        }
        lastInjectedOffset = nextCursorOffset;
        lastInjectedPrefixDigest = nextCursorDigest;
        const cursorSaved = (await writeCursor(safeCursorPath, lastInjectedOffset, lastInjectedPrefixDigest)) ? "yes" : "no";

        console.log("[loop-supervisor-feedback] DELIVERY_CONFIRMED sequence=" + injectionSequence
          + " direction=supervisor_to_worker output_mutated=yes transcript_saved=yes"
          + " cursor_saved=" + cursorSaved + " transcript=" + basename(transcriptPath));
        console.log("::group::LIVE AGENT DIALOGUE BOX — SUPERVISOR → WORKER");
        for (const line of injectionText.split("\n")) {
          console.log("[agent-dialogue] " + line);
        }
        console.log("::endgroup::");
      } catch (error) {
        // Fail open, but leave evidence that this tool-result hook did not complete.
        const errorType = error instanceof Error ? error.name : typeof error;
        console.error("[loop-supervisor-feedback] HOOK_ERROR type=" + errorType
          + "; worker continues and pending advice may be retried at the next tool-result boundary");
      }
    },
  };
};

export default { id: "loop-supervisor-feedback", server: LoopSupervisorFeedback };
