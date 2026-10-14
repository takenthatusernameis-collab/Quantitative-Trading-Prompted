import { createHash } from "node:crypto";
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
        || value.schema_version !== 1
        || typeof value.recommendation_id !== "string"
        || !value.recommendation_id.trim()
        || typeof value.report !== "string"
        || value.report.trim().length < 80
        || value.report.length > MAX_PROTOCOL_RECORD_CHARS) return null;
    return {
      recommendation_id: value.recommendation_id.trim(),
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

async function saveWorkerDelivery(transcriptDir, injectionText, sequence, recommendationId) {
  if (!transcriptDir) return null;
  const destination = resolve(transcriptDir, "agent-dialogue.jsonl");
  if (!isInside(transcriptDir, destination)) return null;
  const safeMessage = redactSensitiveText(injectionText).trim();
  const messageId = recommendationId || "unlinked-recommendation";
  const eventKey = digest("supervisor_to_worker\0" + messageId + "\0" + safeMessage);
  try {
    await mkdir(transcriptDir, { recursive: true });
    let existing = "";
    try { existing = await readFile(destination, "utf8"); } catch {}
    for (const line of existing.split(/\r?\n/).slice(-2000)) {
      try {
        if (line && JSON.parse(line).event_key === eventKey) return destination;
      } catch {}
    }
    const event = {
      schema_version: 1,
      timestamp_utc: new Date().toISOString(),
      direction: "supervisor_to_worker",
      role: "supervisor",
      message_id: messageId,
      event_key: eventKey,
      message: safeMessage,
      sequence,
    };
    await appendFile(destination, JSON.stringify(event) + "\n", { encoding: "utf8", mode: 0o600 });
    return destination;
  } catch {
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
              ? "\nRecommendation ID: " + recommendation.recommendation_id
                + "\nAfter assessing this message, write one reply to .kilo-runtime/worker-disposition.json using the same ID; do not repeat the recommendation text."
              : "";
            injectionText = "[SUPERVISOR → WORKER: NEW MESSAGE]\n"
              + "This is a single advisory message. Verify it against evidence and continue the current task without restarting. "
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
          safeTranscriptDir, injectionText, injectionSequence, recommendation?.recommendation_id
        );
        lastInjectedOffset = nextCursorOffset;
        lastInjectedPrefixDigest = nextCursorDigest;
        const cursorSaved = (await writeCursor(safeCursorPath, lastInjectedOffset, lastInjectedPrefixDigest)) ? "yes" : "no";

        console.log("[loop-supervisor-feedback] DELIVERY_CONFIRMED sequence=" + injectionSequence
          + " direction=supervisor_to_worker output_mutated=yes transcript_saved=" + (transcriptPath ? "yes" : "no")
          + " cursor_saved=" + cursorSaved + " transcript=" + (transcriptPath ? basename(transcriptPath) : "unavailable"));
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
