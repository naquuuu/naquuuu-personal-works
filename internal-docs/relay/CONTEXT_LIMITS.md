# Relay Context Limits and the Memory Question

Status: documentation of current capability plus a bounded option proposal. No behaviour change.

## What the relay can do today (verified on the host, 2026-09-27, Hermes v0.21.4)

- **Stateless per turn.** There is no thread awareness or message observation for WhatsApp (`awareness_supported_for_whatsapp=false`; upstream support is Telegram-only). Each turn sees only the chat text of the triggering message.
- **One carrier for anything earlier:** an explicit structured quote. When the current message includes quoted text, that supplied quote is the only context beyond the current message. Nothing else carries, and quotes arrive only when a person quotes.
- **No room reading.** Unaddressed messages in mention-only groups are filtered before the model runs; the bot never sees the rest of the conversation and must never claim it did.
- **Owner-only session reuse is not memory.** `relay_run.py` can reuse a cached opencode session, but only when the host injects `NAQUUUU_RELAY_CONTEXT`; there is no global last-session reuse and no cross-turn memory for casual chat.
- **The failure this prevents:** invented context (replying as if it followed earlier messages). The persona states the limit plainly so the model answers from what it can see.

## What real cross-message memory would require

1. **Capture:** the bridge already sees group traffic; memory needs a host-side buffer of recent messages per chat, kept outside the model.
2. **Injection:** a bounded window (for example the last N messages or the last X minutes) assembled into the model context for each turn, with the current message last.
3. **Upstream gap:** WhatsApp has no observation hook in the pinned version, so this is a bridge-side or patch-level extension that must follow the pinned-checkout discipline (installer with anchors, backups, source stubs, no `hermes update`).
4. **A deletion and retention story:** in-memory only, dropped on restart and on a kill switch, with counts-only observability.

## The privacy surface it creates

- **Chat content at rest (even briefly):** other people's messages would live in a host buffer. That is Tier 2 content with real people in it; the buffer must never persist to disk and never enter logs.
- **Expanded model context:** group chatter enters the model every turn. The existing guards (notice suppression, drafting block, identity scrub) reduce leak shapes, but context that was never injected cannot leak.
- **Group consent:** free-response groups opted into the bot; a rolling buffer widens what the bot holds about people who never addressed it directly.
- **Boundary discipline:** the buffer must be excluded from agent-readable paths and from relay-run prompts, exactly like Hermes state.

## Bounded option (proposal only, owner decision)

If group conversations need continuity, the smallest honest version is:

1. Per-chat rolling window in memory: the last 10 messages or 10 minutes, whichever is smaller.
2. Enabled per free-response group, opt-in, off by default; one group to start.
3. Quotes and the current message always take precedence; the window is labelled as recent chatter, never as memory of the person.
4. A kill switch (`systemctl --user restart hermes-gateway.service` drops the window) plus counts-only diagnostics (window size, not content).
5. Never persisted, never logged, never visible to guests as a transcript.

Estimated shape: one bridge-side capture + one injection patch + stub tests, following the existing overlay installer pattern. Recommendation: defer until a real group workflow needs it; until then the stateless behaviour and the quote rule are the honest contract.
