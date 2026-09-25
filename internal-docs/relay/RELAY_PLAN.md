# Relay Optimization & Media Plan

- Scope: relay prompt-to-reply latency, context reuse, and image capabilities on the relay host.
- Status: plan; partially implementable today. Items marked "verify" need a host check before implementation.
- Related: `internal-docs/DECISION_LOG.md` ADR-025 (auto-sync), ADR-026 (relay hosted on the VPS), ADR-027 (WhatsApp relay UX); `internal-docs/relay/README.md`, `internal-docs/relay/VPS_RELAY_RUNBOOK.md`.

## 1. Latency (prompt to reply), free-first

- opencode cold start dominates per-message time: keep an `opencode serve` instance running on the relay host and use `opencode run --attach http://127.0.0.1:<port>`. The CLI supports `--attach` and `--port`; manage the server via a systemd user service.
- Reuse opencode sessions for follow-ups in one topic (`--continue` / `--session <id>`) instead of re-reading the workspace each time.
- Shrink the assistant prompt: prune the relay host's bundled Hermes skill packs to just `relay`; keep the SOUL persona short.
- Route status/history questions to a direct read of `internal-docs/STATUS.md` (already the relay skill's design); reserve `opencode run` for engineering tasks.
- Choose the fastest available model on the current (free) plan: measure two or three candidates and keep the fastest.
- Keep light work on the relay host; dispatch only heavy jobs to the home server (extra hop).
- Provider prompt caching helps where the provider supports it; free routes usually do not (verify).

## 2. Context cache and lessons

- Digests read first: `internal-docs/STATUS.md` (state) and a new short, curated `internal-docs/LESSONS.md` (append-only; to be created).
- Seed the relay host's `~/.hermes/memories/MEMORY.md` with the standing invariants (UX rules, routing, host layout) so they ride in the system prompt each turn.
- Hermes per-chat sessions already keep conversation context between messages.
- Retrieval stance: the workspace corpus is small; ripgrep is faster and free; do NOT add a vector database yet.
  - Next step if needed: SQLite FTS5 over `internal-docs/`.
  - Only if semantic search is genuinely required: a local embedding/vector index (`sqlite-vec` plus a local embedding model) hosted on the home server to keep the relay host lean.

## 3. Media (images)

- Read: incoming WhatsApp images already reach the agent; enable vision with a free multimodal model via `auxiliary.vision` (e.g. a Google AI Studio key).
- Generate: prefer the Nous Tool Gateway image tool if the subscription includes it; otherwise a small free-API script (e.g. Pollinations) invoked by the relay, delivered as a WhatsApp image via the `MEDIA:` directive.
- Edit: basic edits with ImageMagick on the relay host (crop/resize/rotate/annotate/format; free, fast); AI edits require a paid provider or the home server later.
- Current state: the relay host has the `vision` tool present but `image_gen` "not configured" (verify provider options before enabling).
