# Group Context Memory: Implementation Brief (ADR-048)

Status: approved 2026-10-13 ("build it next"). Implementation pending. Scope frozen by ADR-048 and `internal-docs/relay/CONTEXT_LIMITS.md`.

## Goal

Give the relay short, honest continuity in one opted-in free-response group: the bot can reference the last few messages of that group's conversation, held in process memory only, with a kill switch and counts-only diagnostics.

## In scope

1. **Capture** (relay guard layer): a per-chat rolling window fed from the events the adapter already receives, in `wa_chat_policy.py` or a sibling `wa_group_memory.py` helper. Bounds: last 10 messages or 10 minutes, whichever is smaller. Identifiers stripped via the existing `RAW_RE` scrubber; store display names only when already resolved in the name cache; drop empty/system bodies; skip status-like chatter.
2. **Injection**: a bounded, labelled block (for example `[recent group chatter, for context only]`) assembled at turn build time, capped in characters, for the opted-in chat only. The current message and any structured quote stay authoritative; the block never claims to be memory of a person.
3. **Toggle**: `NAQUUUU_GROUP_MEMORY` style flag, default off, consulted host-side (never from chat); restart clears all state; a `--check` probe prints counts only (window size per chat, never content).
4. **Tests**: stub tests for bounds, TTL eviction, per-chat scoping, default-off, identifier redaction, and injection formatting; no raw content in logs or diagnostics.
5. **Deploy**: overlay-first, anchored patch on the pinned checkout with backup + source stubs; single gateway restart; health verification.
6. **Live test**: in the designated group, a short scripted exchange where the second message depends on the first (for example the owner asks a follow-up that should be answerable only from the window), then `systemctl --user restart hermes-gateway.service` and confirm the window is gone (counts probe shows zero).

## Out of scope

- Mention-only groups, any cross-group memory, persistence of any kind, memory visible to guests as a transcript, model-input changes beyond the bounded block, any change to the owner gate, and any paid dependency.

## Done when

- 1. Stub matrix green (bounds, TTL, scope, default-off, redaction) and shown in the receipt.
- 2. On-host source stubs pass; gateway restarts once with zero startup errors.
- 3. Live test: the follow-up answer reflects the window in the opted-in group only, and the restart probe proves the window did not survive.
- 4. Sanitization, agent parity, relay eval, and strict audit (hub-clean) re-run with raw output.
- 5. Rollback: disable the flag; restore overlay + patched source from stamped backups if needed.

## Privacy gates (non-negotiable)

- In-memory only; no file, no log line, no export contains message text.
- Diagnostics are counts; the counts probe never prints chat identifiers.
- Window contents never enter agent-readable paths or commit content.
- The window is excluded from the final-reply/notice guard exceptions: outgoing text still passes every existing guard.
