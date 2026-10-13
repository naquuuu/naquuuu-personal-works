# Group memory and relay tuning receipt

**Date:** 2026-10-14
**Related:** ADR-048, ADR-047 implementation correction (2026-10-14), `L-35`, brief `2026-10-13-group-context-memory.md`

## Scope

Bounded group context memory shipped and live-tested, plus the relay tuning fixes that live feedback forced the same night.

## Context memory (ADR-048)

- **Implementation**: `scripts/wa_group_memory.py` (rolling window: last 10 messages or 10 minutes per chat, in-memory only, identifiers redacted on write, idle statuses skipped, counts-only journal diagnostics), wired into `wa_chat_policy.py` (`observe` records, `inject_group_context` prepends the labelled block before the owner prefix so prefixes stay at position 0). Adapter patch via `install_wa_group_memory.py` (`NAQUUUU_GROUP_MEMORY_V1`) with anchored installer, backup, and idempotent re-apply.
- **Opt-in (host-side only)**: `NAQUUUU_GROUP_MEMORY=on` and `NAQUUUU_GROUP_MEMORY_CHATS=<jid>` in `~/.hermes/.env`, written by `wa_group_memory.py --enable-latest` (latest group from the bridge log, id never printed; timestamped env backup). `--disable` is the kill switch. `--check` prints config counts only.
- **Deviation from the brief**: the brief described a probe printing per-chat window sizes; cross-process state is not readable by design, so runtime diagnostics are counts-only journal lines (`group_memory_diag window=N block=N`, no identifiers, no content) and the probe prints configuration counts only.
- **Live proof**: inside one window, a fresh code (KIWI-771) given in message 1 was answered from context in the follow-up, and the reply named it as coming from earlier in the chat; after a gateway restart the same question was met with no knowledge of the code. Diag lines: `recorded window=3` then `inject window=3 block=1` before the successful answer; post-restart `inject window=1 block=0`.
- **Upstream note**: in the mention-only test group, a message without a recognized mention entity is dropped by `_should_process_message` before dispatch (captured by memory, never answered). A reply-to-bot always passes; no config change was made.

## Tuning fixes (same night, from live feedback)

1. **Sentence ceiling corrected**: the ~20-sentence cap counted newlines and blocked genuine replies of 470 to 2270 characters with fallback spam (five `reason=ceiling` blocks observed). It now counts sentence enders only, with a runaway cap of 60; long replies ride WhatsApp's natural bubble split. After the fix: zero new ceiling blocks, and the previously blocked warm reply shipped.
2. **Em dash rule enforced**: `normalize_em_dashes` at the outbound sanitization boundary (comma substitution, punctuation tidy) so no em dash can ship in any reply, language, or quote. Persona files (`.opencode/agent/naquuuubot.md`, `naquuuu-curator.md`, `naquuuu-verifier.md` and their `.agents/` mirrors, `CLAUDE.md`) normalized; zero remaining.
3. **Warmth persona**: curator-reviewed basa-basi rule for the people around the owner (guest-first, one warm line, graceful feedback handling), the length/bubble wording aligned with the guard, and a guest-header carve on the 1 to 3 sentence rule.
4. **Bot-to-bot**: now allowed in any language, with an explicit no-endless-loop rule and a deterministic breaker: more than 20 replies by the bot to one chat inside 5 minutes pauses that chat quietly for 10 minutes (`reply_burst` / `reply_burst_suppressed` counts-only logs).

## Post-deploy incident (2026-10-14, 00:35 to 00:39)

Two replies failed to deliver at 00:35:20 and 00:36:20 with "Delivery uncertain; automatic replay stopped"; the bridge log shows 12 connection churn events ("connection closed / stream errored") in that stretch, with no session conflict and no rate-limit indicator. Cause: reconnection churn from the night's deploy restarts (roughly seven gateway restarts in one hour). The no-replay guard kept the failure from duplicating, so the user saw silence. A final restart at 00:38:47 re-established the connection; from 00:39 onward: zero send failures, bridge connected, owner-verified reply. Operational rule for the next session: batch deploys into one restart; do not restart more than twice in an hour while the relay is in use. Recorded as `L-36`.

## Verification

- Local: 128 tests OK, relay eval 10/10, sanitization passes, agent parity OK, digest freshness OK.
- Host: 76 staged tests OK; source stubs pass including `group_memory_injection_source=pass`; adapter compiles; one restart per stage, zero startup errors, bridge connected.
- Live (owner-verified): warm reply to the resent adjust request; no code knowledge after restart; no new fallback spam; no burst events.

## Rollback

1. Memory off: `python3 wa_group_memory.py --disable` + `systemctl --user restart hermes-gateway.service`.
2. Overlay restore from `~/.local/share/naquuuu/relay-guard-backups/20261013-163441-memory/overlay/` (previous `wa_chat_policy.py`, `verify_wa_group_guard_source.py`).
3. Adapter: restore the timestamped `adapter.py.bak-*` files created by `install_wa_group_memory.py`; restart once; confirm health.
4. Persona: `verify_soul_mirror.py --apply` after reverting `WHATSAPP_SOUL.md`; backups `SOUL.md.bak-20261013-160452` and later stamps on the host.
