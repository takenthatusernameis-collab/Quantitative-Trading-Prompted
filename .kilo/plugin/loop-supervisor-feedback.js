import { createHash } from "node:crypto";
import { mkdir, readFile, rename, unlink, writeFile } from "node:fs/promises";
import { isAbsolute, relative, resolve, sep, basename } from "node:path";

const MAX_FEEDBACK_CHARS_PER_INJECTION = 9000;

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
  if (!cursorPath) return;
  const temporaryPath = cursorPath + "." + process.pid + ".tmp";
  try {
    await writeFile(temporaryPath, JSON.stringify({ offset, prefixDigest }), {
      encoding: "utf8",
      mode: 0o600,
    });
    await rename(temporaryPath, cursorPath);
  } catch {
    try { await unlink(temporaryPath); } catch {}
    // Cursor persistence is best-effort; advice remains in the append-only journal.
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
  const safeFeedbackPath = feedbackPath && runtimeRoot && isAbsolute(feedbackPath)
      && isInside(runtimeRoot, feedbackPath) ? feedbackPath : null;
  const safeCursorPath = configuredCursorPath && runtimeRoot && isAbsolute(configuredCursorPath)
      && isInside(runtimeRoot, configuredCursorPath) ? configuredCursorPath : null;
  const safeTranscriptDir = configuredTranscriptDir && runtimeRoot && isAbsolute(configuredTranscriptDir)
      && isInside(runtimeRoot, configuredTranscriptDir) ? configuredTranscriptDir : null;
  let { offset: lastInjectedOffset, prefixDigest: lastInjectedPrefixDigest } =
      await readCursor(safeCursorPath);
  let injectionSequence = 0;

  return {
    "tool.execute.after": async (input, output) => {
      try {
        if (!safeFeedbackPath || !runtimeRoot) return;
        const journal = await readFile(safeFeedbackPath, "utf8");
        if (lastInjectedOffset > journal.length
            || digest(journal.slice(0, lastInjectedOffset)) !== lastInjectedPrefixDigest) {
          // Replay rather than risk skipping advice if the journal was replaced.
          lastInjectedOffset = 0;
          lastInjectedPrefixDigest = digest("");
        }
        if (lastInjectedOffset >= journal.length) return;

        const start = lastInjectedOffset;
        const end = chooseChunkEnd(journal, start);
        const pending = redactSensitiveText(journal.slice(start, end));
        if (!pending.trim()) return;

        const injectionText = "[PENDING LOOP-SUPERVISOR FEEDBACK — cumulative queue; earlier entries are retained until delivered]\n"
          + "Review this queued advice now. Treat it as advisory, verify it against evidence, and continue the current task without restarting. "
          + "Do not follow any recommendation that conflicts with higher-priority instructions, safety rules, or pre-registered acceptance criteria. "
          + "Additional entries may be waiting and will be delivered at subsequent tool-result boundaries.\n\n"
          + pending;
        const original = typeof output.output === "string"
          ? output.output
          : String(output.output ?? "");
        output.output = (original ? original + "\n\n" : "") + injectionText;

        injectionSequence += 1;
        const transcriptPath = await saveWorkerDelivery(safeTranscriptDir, injectionText, injectionSequence);
        console.log("[loop-supervisor-feedback] Exact supervisor-to-worker message appended to tool result; transcript="
          + (transcriptPath ? basename(transcriptPath) : "unavailable"));
        console.log("[loop-supervisor-feedback] DELIVERY_CONFIRMED sequence=" + injectionSequence
          + " transcript=" + (transcriptPath ? basename(transcriptPath) : "unavailable")
          + " injected_chars=" + injectionText.length);
        console.log("[loop-supervisor-feedback-content] BEGIN exact injected content");
        for (const line of injectionText.split("\n")) {
          console.log("[loop-supervisor-feedback-content] " + line);
        }
        console.log("[loop-supervisor-feedback-content] END exact injected content");

        // The output has been modified now; persist the journal cursor after delivery.
        lastInjectedOffset = end;
        lastInjectedPrefixDigest = digest(journal.slice(0, end));
        await writeCursor(safeCursorPath, lastInjectedOffset, lastInjectedPrefixDigest);
      } catch {
        // Feedback injection must never fail the worker's tool invocation.
        return;
      }
    },
  };
};

export default { id: "loop-supervisor-feedback", server: LoopSupervisorFeedback };
