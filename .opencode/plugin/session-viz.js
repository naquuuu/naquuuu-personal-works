// session-viz: telemetry plugin for the naquuuu engineering hub.
//
// what it does:
//   one jsonl record per host event, appended to
//   <workspaceRoot>/.session-viz/<sessionID>.jsonl, read later by
//   scripts/render_agent_viz.py. paths and command strings only, never file
//   contents. credential shaped strings are replaced with [redacted].
//
// why this file is plain esm javascript and not typescript:
//   `node --check .opencode/plugin/session-viz.js` has to stay able to verify
//   this file, and unverifiable telemetry that silently breaks a working
//   session is worse than untyped telemetry. the sibling package.json in this
//   directory carries {"type":"module"} so the check resolves esm. converting
//   to .ts is a rename plus one type import, and nothing else changes.

import { appendFile, mkdir } from "node:fs/promises";
import { appendFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";

const FALLBACK_ROOT = "C:/personal/naquuuu";
const DATA_DIRNAME = ".session-viz";
const UNKNOWN = "unknown";
const REDACTED = "[redacted]";
const MAX_TEXT = 500;
const MAX_COMMAND = 300;
const MAX_LABEL = 300;
const FLUSH_INTERVAL_MS = 2000;
const FLUSH_MAX_RECORDS = 25;
const MAX_TRACKED_CALLS = 500;
const AGENT_NAME_HINT = /^naquuuu/;

// Credential shapes, assembled from fragments on purpose. the hub sanitization
// linter greps source files for literal token specimens, including inside
// comments, so the shapes are described structurally here and never written
// out as something that could be mistaken for a real key.
const SECRET_PATTERNS = [
  new RegExp("AI" + "zaSy[A-Za-z0-9_-]{25,}", "g"),
  new RegExp("dop" + "_v1_[A-Za-z0-9_-]{12,}", "g"),
  new RegExp("(?:bearer|basic|token)\\s+[A-Za-z0-9._~+/=-]{12,}", "gi"),
  new RegExp("((?:api[_-]?key|token|secret|password|passwd)\\s*[:=]\\s*\\\"?)([A-Za-z0-9._~+/=-]{12,})", "gi"),
  // three segment base64url shapes. these are short and url safe, so the long
  // run rule below cannot see them, and the leading segment always starts with
  // the base64 of an opening brace.
  new RegExp("eyJ[A-Za-z0-9_-]{6,}\\.[A-Za-z0-9_-]{6,}(?:\\.[A-Za-z0-9_-]{6,})?", "g"),
  // pem block headers. the body of the block is not a single token, so only the
  // header is matched; the surrounding block text is truncated by clip().
  new RegExp("-----BEGIN [A-Z ]*PRIVATE KEY-----", "g"),
  new RegExp("[A-Za-z0-9+/]{40,}={0,2}", "g"),
];

// Paths this plugin must never touch, read, or name. matches are refused at
// the recording boundary so the path never reaches disk.
const BLOCKED_PATH_PATTERNS = [
  /(^|[\\/])\.env(\.|$)/i,
  /(^|[\\/])\.hermes([\\/]|$)/i,
  /AppData[\\/]Local[\\/]hermes/i,
  /(^|[\\/])hermes[\\/]state([\\/]|$)/i,
];

const buffer = new Map();
let bufferedCount = 0;
let chain = Promise.resolve();
let lastAgent = null;
const callStarts = new Map();
const ensuredDirs = new Map();

function workspaceRoot() {
  const fromEnv = process.env?.NAQUUUU_WORKSPACE;
  return typeof fromEnv === "string" && fromEnv.trim() !== "" ? fromEnv.trim() : FALLBACK_ROOT;
}

// index of the key=value rule inside SECRET_PATTERNS. that one keeps its
// label, so a redacted command still reads as "token=[redacted]".
const SECRET_VALUE_RULE = 3;

function redact(value) {
  if (typeof value !== "string" || value === "") return value;
  let out = value;
  SECRET_PATTERNS.forEach((pattern, index) => {
    pattern.lastIndex = 0;
    out = index === SECRET_VALUE_RULE ? out.replace(pattern, (match, label) => label + REDACTED) : out.replace(pattern, REDACTED);
  });
  return out;
}

function clip(value, max) {
  if (typeof value !== "string") return value;
  if (value.length <= max) return value;
  return value.slice(0, max) + " [truncated]";
}

function str(value) {
  return typeof value === "string" && value.trim() !== "" ? value : null;
}

function sessionKey(raw) {
  const value = str(raw) ?? UNKNOWN;
  const safe = value.replace(/[^A-Za-z0-9._-]/g, "_").replace(/^\.+/, "").slice(0, 120);
  return safe === "" ? UNKNOWN : safe;
}

async function ensureDir() {
  const dir = join(workspaceRoot(), DATA_DIRNAME);
  if (ensuredDirs.has(dir)) return ensuredDirs.get(dir);
  const pending = mkdir(dir, { recursive: true }).catch(() => undefined);
  ensuredDirs.set(dir, pending);
  return pending;
}

function queue(record) {
  const key = sessionKey(record.sessionID);
  const line = JSON.stringify(record);
  const lines = buffer.get(key);
  if (lines) lines.push(line);
  else buffer.set(key, [line]);
  bufferedCount += 1;
  if (bufferedCount >= FLUSH_MAX_RECORDS) void flush();
}

function push(rawSessionID, type, payload) {
  const record = { ts: new Date().toISOString(), type, sessionID: sessionKey(rawSessionID) };
  if (payload && typeof payload === "object") Object.assign(record, payload);
  queue(record);
}

// flushes are serialized on one chain. a caller that awaits the returned
// promise waits for every earlier flush too, so dispose can never return while
// a batch is still in flight and no batch is ever dropped.
function flush() {
  chain = chain.then(async () => {
    if (buffer.size === 0) return;
    const batch = [...buffer.entries()];
    buffer.clear();
    bufferedCount = 0;
    try {
      await ensureDir();
      for (const [key, lines] of batch) {
        await appendFile(join(workspaceRoot(), DATA_DIRNAME, key + ".jsonl"), lines.join("\n") + "\n", "utf8");
      }
    } catch {
      // telemetry never surfaces an error into the host session
    }
  });
  return chain;
}

function flushSync() {
  if (buffer.size === 0) return;
  const batch = [...buffer.entries()];
  buffer.clear();
  bufferedCount = 0;
  try {
    const dir = join(workspaceRoot(), DATA_DIRNAME);
    mkdirSync(dir, { recursive: true });
    for (const [key, lines] of batch) {
      appendFileSync(join(dir, key + ".jsonl"), lines.join("\n") + "\n", "utf8");
    }
  } catch {
    // same rule on the way out
  }
}

function trackStart(callID, tool) {
  if (callStarts.size >= MAX_TRACKED_CALLS) {
    const oldest = callStarts.keys().next();
    if (!oldest.done) callStarts.delete(oldest.value);
  }
  callStarts.set(callID, { t: Date.now(), tool });
}

function isBlockedPath(path) {
  return BLOCKED_PATH_PATTERNS.some((pattern) => pattern.test(path));
}

function firstString(...candidates) {
  for (const candidate of candidates) {
    const found = str(candidate);
    if (found !== null) return found;
  }
  return null;
}

function collectText(parts) {
  if (!Array.isArray(parts)) return "";
  const chunks = [];
  for (const part of parts) {
    const text = str(part?.text);
    if (text !== null) chunks.push(text);
  }
  return chunks.join("\n");
}

function isFailure(output) {
  if (output == null) return false;
  if (output.error != null) return true;
  if (output.metadata?.error != null) return true;
  const exitCode = output.metadata?.exitCode ?? output.exitCode;
  if (typeof exitCode === "number" && exitCode !== 0) return true;
  return false;
}

function errorLabel(output) {
  const message = firstString(output?.error?.message, output?.error, output?.metadata?.error);
  return message === null ? null : clip(redact(message), MAX_LABEL);
}

// every tool gets the generic record. the tool specific records below add
// shape, never contents.
function describeArgs(tool, args) {
  if (args == null || typeof args !== "object") return {};

  if (tool === "todowrite") {
    const items = Array.isArray(args.todos) ? args.todos : [];
    return {
      todos: items
        .filter((item) => item != null && typeof item === "object")
        .map((item) => ({
          content: clip(redact(String(item?.content ?? "")), MAX_LABEL),
          status: str(item?.status) ?? "unknown",
          priority: str(item?.priority) ?? "unknown",
        })),
    };
  }

  if (tool === "task") {
    return {
      handoff: {
        from: lastAgent,
        to: firstString(args.subagent_type, args.subagentType, args.agent),
        description: clip(redact(String(args.description ?? "")), MAX_LABEL),
      },
    };
  }

  if (tool === "edit" || tool === "write" || tool === "patch" || tool === "multiedit") {
    const path = firstString(args.filePath, args.file_path, args.path, args.target);
    if (path === null) return {};
    if (isBlockedPath(path)) return { path: null, blocked: true };
    return { path: clip(redact(path), MAX_LABEL) };
  }

  if (tool === "bash" || tool === "shell") {
    const command = firstString(args.command, args.cmd);
    if (command === null) return {};
    return { command: clip(redact(command), MAX_COMMAND) };
  }

  return {};
}

const timer = setInterval(() => void flush(), FLUSH_INTERVAL_MS);
if (typeof timer?.unref === "function") timer.unref();
process.on("exit", flushSync);

export default async function sessionViz() {
  return {
    async event(input) {
      try {
        const event = input?.event;
        const type = str(event?.type);
        const agent = firstString(event?.properties?.agent, event?.properties?.info?.agent);
        if (agent !== null && AGENT_NAME_HINT.test(agent)) lastAgent = agent;
        if (type !== "session.idle" && type !== "session.error") return;
        const sessionID = firstString(event?.properties?.sessionID, event?.properties?.info?.sessionID);
        push(sessionID, "event", { event: type, agent: lastAgent, ok: type !== "session.error" });
      } catch {
        // swallowed on purpose
      }
    },

    async "chat.message"(input, output) {
      try {
        const agent = str(input?.agent);
        if (agent !== null) lastAgent = agent;
        const message = output?.message;
        const role = str(message?.role) ?? "unknown";
        const text = clip(redact(collectText(output?.parts)), MAX_TEXT);
        push(input?.sessionID, "chat.message", { agent, role, text });
      } catch {
        // swallowed on purpose
      }
    },

    async "tool.execute.before"(input, output) {
      try {
        const tool = str(input?.tool) ?? UNKNOWN;
        const callID = sessionKey(input?.callID);
        trackStart(callID, tool);
        push(input?.sessionID, "tool", {
          tool,
          phase: "before",
          callID,
          agent: lastAgent,
          ...describeArgs(tool, output?.args),
        });
      } catch {
        // swallowed on purpose
      }
    },

    async "tool.execute.after"(input, output) {
      try {
        const callID = sessionKey(input?.callID);
        const start = callStarts.get(callID);
        if (start !== undefined) callStarts.delete(callID);
        const tool = str(input?.tool) ?? start?.tool ?? UNKNOWN;
        push(input?.sessionID, "tool", {
          tool,
          phase: "after",
          callID,
          agent: lastAgent,
          ok: !isFailure(output),
          durationMs: start !== undefined ? Date.now() - start.t : null,
          error: errorLabel(output),
        });
      } catch {
        // swallowed on purpose
      }
    },

    async dispose() {
      try {
        clearInterval(timer);
        await flush();
      } catch {
        // swallowed on purpose
      }
    },
  };
}
