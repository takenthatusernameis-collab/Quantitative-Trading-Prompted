import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { isAbsolute, relative, resolve, sep } from "node:path";

const MAX_FEEDBACK_CHARS = 3200;

function isInside(parent, candidate) {
  const resolvedParent = resolve(parent);
  const resolvedCandidate = resolve(candidate);
  const rel = relative(resolvedParent, resolvedCandidate);
  return rel === "" || (!rel.startsWith(".." + sep) && rel !== ".." && !isAbsolute(rel));
}

function normalizeForDigest(text) {
  return text
    .replace(/^.*(?:review\s*#?\s*\d+|cycle\s*#?\s*\d+|generated at|reviewed at|timestamp)\b.*$/gim, "")
    .replace(/\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z\b/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

const LoopSupervisorFeedback = async () => {
  if (process.env.KILO_SUPERVISOR_MODE === "1") {
    return {};
  }

  const feedbackPath = process.env.KILO_SUPERVISOR_FEEDBACK_FILE;
  const runtimeRoot = process.env.RUNNER_TEMP;
  let lastInjectedDigest = "";

  return {
    "tool.execute.after": async (input, output) => {
      try {
        if (!feedbackPath || !runtimeRoot || !isAbsolute(feedbackPath)) return;
        if (!isInside(runtimeRoot, feedbackPath)) return;

        const feedback = (await readFile(feedbackPath, "utf8")).trim().slice(0, MAX_FEEDBACK_CHARS);
        if (!feedback) return;

        const normalized = normalizeForDigest(feedback);
        if (!normalized) return;
        const digest = createHash("sha256").update(normalized).digest("hex");
        if (digest === lastInjectedDigest) return;

        const original = typeof output.output === "string"
          ? output.output
          : String(output.output ?? "");
        output.output = (original ? original + "\n\n" : "")
          + "[NEW INDEPENDENT LOOP-SUPERVISOR FEEDBACK]\n"
          + "Review this advice now. Treat it as advisory, verify it against evidence, and continue the current task without restarting. "
          + "Do not follow any recommendation that conflicts with higher-priority instructions, safety rules, or pre-registered acceptance criteria.\n\n"
          + feedback;

        lastInjectedDigest = digest;
      } catch {
        return;
      }
    },
  };
};

export default { id: "loop-supervisor-feedback", server: LoopSupervisorFeedback };
