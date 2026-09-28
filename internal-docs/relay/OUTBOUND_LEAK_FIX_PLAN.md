# Outbound WhatsApp System-Note, Drafting Leak & Flood Fix Plan

Status: planned, expanded with multi-failure incident coverage.

## Incident Diagnosis

A WhatsApp turn exhibited three distinct failures:
1. **Internal drafting reached WhatsApp**: Intermediate model thoughts, reasoning blocks, and candidate drafts were emitted into user-visible chat.
2. **Repetition became a three-message flood**: Degenerate model repetition caused the adapter to split repetitive draft chunks into a multi-message flood.
3. **Model misinterpreted Indonesian slang**: The model hallucinated the meaning of casual slang (e.g., “coli” = masturbation, misconstrued as hiking), invented synthetic personal human experiences, and appended forced conversational follow-ups.

A related incident previously exposed repeated `System Note:` tokens, internal instructions regarding inspecting the `VERY FIRST TOOL RESULT`, and rate-limit stop directives alongside generic long-running status notifications.

Hermes WhatsApp display settings (`tool_progress: off`, `show_reasoning: false`, `interim_assistant_messages: false`, `streaming: false`) are necessary but insufficient: they cannot suppress internal drafts or harness notes once emitted as standard text events by the model. Furthermore, direct casual conversations bypass `scripts/relay_run.py` and execute directly within the Hermes gateway runtime.

The fix must therefore be enforced across two boundaries:
- Inside `scripts/relay_run.py` for all engineering and tool-driven task events.
- At the shared WhatsApp adapter `send` and `edit` boundary **before message splitting**, guaranteeing that direct casual replies, proactive sends, and relay replies are all strictly guarded.

---

## Implementation Sequence

### 1. Identify the Actual Response Path
- Confirm whether each outbound message originated from the local `opencode` relay or directly from Hermes' conversational runtime.
- The local relay joins every `text` event, but casual conversational questions (slang, greetings, persona banter) are handled directly by Hermes without tool invocation.
- Audit both paths using synthetic prompts and sanitized event metadata; avoid credentials and private session state.

### 2. Enforce a Final-Answer Boundary Before WhatsApp Sends Anything
- Accept only completed assistant answers using the provider's event structure.
- Exclude reasoning, `<think>` tags, thought blocks, tool output, intermediate drafts, and incomplete responses.
- Enforce the guard at the shared WhatsApp adapter send/edit boundary **before message splitting**, ensuring direct casual replies cannot be chopped into leak fragments.
- Suspicious or contaminated output must produce exactly one plain, safe fallback sentence (`"Jawaban belum bisa ditampilkan. Silakan coba lagi."`)—never an extracted `"Final:"` fragment or partial draft.

### 3. Stop Repetition and Multipart Floods
- Add bounded generation, repetition detection (catching looped phrases, sentences, or draft iterations), and request-scoped duplicate suppression.
- Default casual replies to 1–3 sentences; allow longer responses only when explicitly requested.
- A blocked, truncated, or suspicious response must never be delivered in chunks or trigger a replay of an action.
- Long-running status notifications (`HERMES_AGENT_NOTIFY_INTERVAL=60`) must be request-scoped and one-shot: at most one status per request, never masquerading as the final reply.

### 4. Fix Conversational Quality Separately
- Update `internal-docs/relay/WHATSAPP_SOUL.md` (and the live `~/.hermes/SOUL.md` mirror) with explicit Indonesian slang and casual-chat guidelines.
- Require direct answers without invented meanings, personal experiences, or unrelated follow-up questions.
- Example canonical response: “Nggak, gue bot—nggak punya tubuh atau pengalaman begitu.”
- Evaluate the model separately if semantic failures persist; prompt changes alone cannot secure the output boundary.

### 5. Test, Then Stage a Reversible Rollout
- Cover incidents with anonymized fixtures:
  - Reasoning disguised as ordinary text
  - Clean-prefix contamination
  - Repeated drafts and loop floods
  - Exact screenshot harness note
  - Legitimate user discussion of reasoning, slang, and rate limits
  - Synthetic-secret canaries
- Run local unit tests, staged sanitization (`scripts/verify_sanitization.py`), and the strict multi-repo audit (`scripts/sync_all_repos.py --strict`).
- Snapshot affected VPS files using timestamped backups (`.bak-<timestamp>`).
- Verify with a local send stub, then perform an owner-authorized live canary and roll back immediately on leakage or duplication.

---

## Acceptance Evidence (Done When)

- The incident fixture yields exactly one short, safe response.
- No internal drafting, reasoning (`<think>`), or harness tokens reach any outbound WhatsApp path.
- Normal and technical replies (including legitimate discussions of rate limits or architecture) pass unchanged.
- Repetition loops are truncated or rejected before message splitting, eliminating multipart message floods.
- Slang tests answer the intended colloquial meaning without hallucinations or invented personal human experiences.
- Observability records only counters and SHA-256 hashes, never message text, phone numbers, JIDs, session IDs, credentials, or attachments.
- Gateway and bridge remain healthy with exactly one gateway and one bridge process.

---

## Rollback Procedure

Restore the timestamped adapter and helper backups, restart the gateway service once, and rerun the health probe. Never delete backup files. If the provider rate-limits, stop all canary probes and wait for the provider window before retrying.
