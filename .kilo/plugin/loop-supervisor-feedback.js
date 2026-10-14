import { createHash } from "node:crypto";
import { appendFile, mkdir, readFile, rename, unlink, writeFile } from "node:fs/promises";
import { isAbsolute, relative, resolve, sep, basename } from "node:path";

const MAX_FEEDBACK_CHARS_PER_INJECTION = 9000;
const MAX_PROTOCOL_RECORD_CHARS = 12000;
const VALID_DISPOSITIONS = new Set([
  "accepted", "in_progress", "verified", "blocked", "rejected_with_reason", "superseded",
]);
const MAX_UNACKNOWLEDGED_REMINDERS = 1;
const REMINDER_EVERY_TOOL_BOUNDARIES = 8;

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

async function readProtocolRecord(protocolDir, filename, maximum = MAX_PROTOCOL_RECORD_CHARS) {
  if (!protocolDir) return null;
  const path = resolve(protocolDir, filename);
  if (!isInside(protocolDir, path)) return null;
  try {
    const raw = await readFile(path, "utf8");
    if (raw.length > maximum) return null;
    const value = JSON.parse(raw);
    return value && typeof value === "object" && !Array.isArray(value) ? value : null;
  } catch {
    return null;
  }
}

function dispositionAcknowledges(recommendation, disposition) {
  if (!recommendation || !disposition
      || recommendation.schema_version !== 1
      || disposition.schema_version !== 1
      || typeof recommendation.recommendation_id !== "string"
      || recommendation.recommendation_id.length === 0
      || disposition.recommendation_id !== recommendation.recommendation_id
      || !VALID_DISPOSITIONS.has(disposition.disposition)
      || typeof disposition.reason !== "string"
      || disposition.reason.trim().length < 8) {
    return false;
  }
  if (disposition.disposition === "verified"
      && (typeof disposition.verification !== "string" || !disposition.verification.trim())) {
    return false;
  }
  return true;
}

async function readProtocolState(protocolDir) {
  const recommendation = await readProtocolRecord(protocolDir, "current-supervisor-recommendation.json");
  if (!recommendation || typeof recommendation.report !== "string"
      || recommendation.report.length < 80 || recommendation.report.length > MAX_PROTOCOL_RECORD_CHARS) {
    return { recommendation: null, disposition: null, acknowledged: false };
  }
  const disposition = await readProtocolRecord(protocolDir, "worker-disposition.json", 6000);
  return { recommendation, disposition, acknowledged: dispositionAcknowledges(recommendation, disposition) };
}

function buildProtocolReminder(recommendation) {
  // One lightweight reminder; the already-delivered recommendation body is never repeated.
  return "## Supervisor → Worker\\n\\n"
    + "Recommendation ID: " + recommendation.recommendation_id + "\\n\\n"
    + "Please write a valid .kilo-runtime/worker-disposition.json for this recommendation. "
    + "Use schema_version=1, the exact recommendation_id, an allowed disposition, a concrete reason, "
    + "string evidence/verification fields, and an ISO-8601 UTC updated_at. "
    + "Do not repeat the recommendation text; acknowledge, verify, block, or reject it with evidence.\\n\\n---\\n\\n";
}

async function appendAgentDialogue(transcriptDir, roleMessage) {
  if (!transcriptDir || typeof roleMessage !== "string" || !roleMessage.trim()) return false;
  const destination = resolve(transcriptDir, "agent-dialogue.md");
  if (!isInside(transcriptDir, destination)) return false;
  try {
    let existing = "";
    try { existing = await readFile(destination, "utf8"); } catch (error) {
      if (!(error instanceof Error) || error.code !== "ENOENT") throw error;
    }
    if (existing.includes(roleMessage)) return true;
    await appendFile(destination, roleMessage, { encoding: "utf8", mode: 0o600 });
    return true;
  } catch {
    return false;
  }
}

function chooseChunkEnd(function chooseChunkEnd(journal, start) {
  let end = Math.min(start + MAX_FEEDBACK_CHARS_PER_INJECTION, journal.length);
  if (end < journal.length) {
    const nextEntry = journal.lastIndexOf("--- SUPERVISOR ADVICE ENTRY", end);
    if (nextEntry > start) end = nextEntry;
  }
  if (end <= start) end = Math.min(start + MAX_FEEDBACK_CHARS_PER_INJECTION, journal.length);
  return end;
}

async function saveWorkerDelivery(transcriptDir, injectionText, sequence) {
  if (!transcriptDir) return null;
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const filename = "worker-delivery-" + stamp + "-" + process.pid + "-" + sequence + ".md";
  const destination = resolve(transcriptDir, filename);
  if (!isInside(transcriptDir, destination)) return null;
  const tempPath = destination + "." + process.pid + ".tmp";
  try {
    await mkdir(transcriptDir, { recursive: true });
    await writeFile(tempPath, injectionText, { encoding: "utf8", mode: 0o600 });
    await rename(tempPath, destination);
    return destination;
  } catch {
    try { await unlink(tempPath); } catch {}
    return null;
  }
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
  let toolBoundaryCount = 0;
  let reminderRecommendationId = null;
  let reminderDeliveryCount = 0;
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

        const protocolState = await readProtocolState(safeProtocolDir);
        const recommendation = protocolState.recommendation;
        if (recommendation?.recommendation_id !== reminderRecommendationId) {
          reminderRecommendationId = recommendation?.recommendation_id ?? null;
          reminderDeliveryCount = 0;
          toolBoundaryCount = 0;
        }
        toolBoundaryCount += 1;

        let injectionText = "";
        let deliveryKind = "";
        let nextCursorOffset = lastInjectedOffset;
        let nextCursorDigest = lastInjectedPrefixDigest;
        if (lastInjectedOffset < journal.length) {
          const start = lastInjectedOffset;
          const end = chooseChunkEnd(journal, start);
          const pending = redactSensitiveText(journal.slice(start, end));
          if (pending.trim()) {
            const body = pending
              .replace(/^--- SUPERVISOR ADVICE ENTRY ---\\s*$/gm, "")
              .replace(/^--- END SUPERVISOR ADVICE ENTRY ---\\s*$/gm, "")
              .trim();
            if (body) {
              const recommendationId = recommendation?.recommendation_id ?? "(not assigned)";
              injectionText = "## Supervisor → Worker\\n\\n"
                + "Recommendation ID: " + recommendationId + "\\n\\n"
                + body + "\\n\\n---\\n\\n";
              deliveryKind = "journal";
              nextCursorOffset = end;
              nextCursorDigest = digest(journal.slice(0, end));
            }
            if (false) {
              nextCursorOffset = end;            nextCursorOffset = end;
            nextCursorDigest = digest(journal.slice(0, end));
          }
        }

        if (!injectionText && recommendation && !protocolState.acknowledged
            && toolBoundaryCount % REMINDER_EVERY_TOOL_BOUNDARIES === 0
            && reminderDeliveryCount < MAX_UNACKNOWLEDGED_REMINDERS) {
          injectionText = buildProtocolReminder(recommendation);
          deliveryKind = "recommendation-reminder";
          reminderDeliveryCount += 1;
        }
        if (!injectionText) return;

        const original = typeof output.output === "string"
          ? output.output
          : String(output.output ?? "");
        output.output = (original ? original + "\n\n" : "") + injectionText;

        injectionSequence += 1;
        const transcriptSaved = await appendAgentDialogue(safeTranscriptDir, injectionText);
        // Journal delivery advances the durable journal cursor. Reminder delivery never does.
        let cursorSaved = "unchanged";
        if (deliveryKind === "journal") {
          lastInjectedOffset = nextCursorOffset;
          lastInjectedPrefixDigest = nextCursorDigest;
          cursorSaved = (await writeCursor(safeCursorPath, lastInjectedOffset, lastInjectedPrefixDigest)) ? "yes" : "no";
        } else {
          cursorSaved = "not_required";
        }

        console.log("[loop-supervisor-feedback] DELIVERY_CONFIRMED sequence=" + injectionSequence
          + " direction=Supervisor→Worker"
          + " source=" + deliveryKind
          + " output_mutated=yes"
          + " dialogue_recorded=" + (transcriptSaved ? "yes" : "no")
          + " cursor_saved=" + cursorSaved);
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
