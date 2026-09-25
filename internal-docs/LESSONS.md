# Lessons (curated)

Short, append-only. Agents read this first together with `STATUS.md` — it exists so we do not re-read everything.

1. WhatsApp replies must read human (ADR-027): 1-3 sentences, no bullet menus, no preamble, no process/reasoning/tool chatter.
2. Never print phone numbers, IDs, or JIDs. WhatsApp mentions arrive as numeric IDs; use the name from the conversation, or say "dia/they", or ask for the name in one line.
3. Workspace/agent/project/state questions route through `opencode run`; never answer them from Hermes memory or bundled skills.
4. Auto-sync is gate-protected but publishes whatever an agent left behind: an agent edit changed the opencode model pin to an invalid value and it went live (fixed in `8522de0`). Validate config edits — `opencode.jsonc` must parse and use `provider/model` form.
5. Only one WhatsApp bridge at a time: `hermes gateway stop` can leave an orphaned `bridge.js`; check port 3000 before starting another host.
6. Moving a WhatsApp session: the env transfer must include `WHATSAPP_ENABLED`, and a fresh host needs `npm install` in the bridge directory before its first start.
7. Auto-sync commit labels stay neutral (`hub`, `vm-0-8-ubuntu`, `mipad-linux`); never use machine names that carry corporate identifiers.
8. Free-tier assistant models are slower and more verbose; measure candidates and keep the fastest, least robotic one.
9. Latency: `opencode serve` + `opencode run --attach --dir <repo>` removes cold start (measured ~7 s for a warm one-word run); fall back to a plain `opencode run` if the server is down.
