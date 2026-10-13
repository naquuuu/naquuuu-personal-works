# Codex takeover prompt: relay send-stall recovery + hardening (2026-10-14)

Paste the block below into Codex. Scope: recover the WhatsApp relay outbound path and land the hardening rails. Everything else (group memory, tuning) is already shipped and recorded.

---

## TAKEOVER PROMPT (for Codex)

Goal: restore WhatsApp relay sending and land the send-failure hardening, provable with raw output.

Context, current state (2026-10-14, ~00:45 WIB, last pushed commit 84321f0):
- The relay gateway is active on the VPS (`hermes-gateway.service`, started 00:38:47 WIB) and the bridge reports connected. Receives, polling, and typing all work: `POST /typing` answers instantly.
- Outbound sends hang at the WhatsApp layer. Direct probe of the bridge on the relay host: `curl -s -X POST http://127.0.0.1:3000/send -H 'Content-Type: application/json' -d '{"chatId":"0@g.us","message":"probe"}'` returns `{"error":"sendMessage timed out after 60s"}` for a dead jid while typing stays instant. So `sock.sendMessage` stalls for every outbound message, and because Baileys serializes sends, one hung send wedges the rest until the socket is recreated.
- Contributing history: roughly seven gateway restarts in one hour during the deploy night produced connection churn ("connection closed / stream errored" in `~/.hermes/whatsapp/bridge.log`); sends failed at 00:35:20, 00:36:20, 00:41:56, 00:43:24, 00:43:32. All guards behaved per design (delivery uncertain, no replay, no duplicate fallbacks); the burst breaker never tripped.
- Read first: `internal-docs/relay/2026-10-14-GROUP_MEMORY_AND_TUNING.md` (receipt incl. both incidents), `L-36` and `L-37` in `internal-docs/LESSONS.md`, `internal-docs/relay/VPS_RELAY_RUNBOOK.md` ("Relay recovery (2026-09-28 outage)" section).

Step 0, recovery (follow the 2026-09-28 playbook, in order):
1. Stop all testing traffic and restarts. Prefer pausing the relay for the quiet window (`systemctl --user stop hermes-gateway.service`), or at minimum zero sends.
2. Wait out the provider window (hours, not minutes). No probes that send during the wait; typing-level checks only.
3. Restart ONCE (`systemctl --user start hermes-gateway.service`; or restart if already running), confirm active, bridge `connected`, zero startup errors.
4. Verify with exactly ONE controlled send to a designated target the owner names; confirm it lands before resuming normal operation. If it times out again: stop, wait longer, do not loop.

Hardening to land (owner-approved direction; keep each item minimal and tested):
1. Single bounded retry for transient send failures (bridge 503 or `sendMessage timed out`): at most one retry after a short delay, inside the existing final-reply claim so a delivered message can never duplicate. No partial replay.
2. Keep the real bridge error type in counts-only logs (error class string + counter, never message content or identifiers). Today the delivery patch discards the bridge's error body, which is why diagnosis needed a direct probe.
3. Owner decision to surface: when a send finally fails, stay silent (current) or send one plain "gagal terkirim, coba lagi" line. Ask the owner; default stays silent unless approved.
4. Optional if the owner agrees: a send-stall detector (N consecutive timeouts for a chat pauses that chat quietly and logs counts only), mirroring the `reply_burst` breaker pattern in `wa_chat_policy.py`.

Environment and boundaries:
- Relay host: `ubuntu@100.87.52.117` (Tailscale). Runtime overlay wins imports from `~/.local/share/naquuuu/relay-guards/`; staged tests in `~/.local/share/naquuuu/relay-verify/`. Hermes checkout is pinned: never run `hermes update`.
- The VPS clone auto-syncs from the hub; write only to the overlay and to `internal-docs/relay/`, never the clone. Commits and pushes need owner approval.
- Tier 1 boundary: no phone numbers, JIDs, chat ids, message bodies, env contents, or session state in model context. Diagnose with counts-only greps and the bridge debug JSON (`event/stage/reason/fromMe` fields only); say so when evidence is a probe rather than a live reply.
- Restart discipline per `L-36`: at most two gateway restarts per hour while the relay is in use; batch deploys.
- Run before any push: `python scripts/verify_sanitization.py`, `python scripts/sync_all_repos.py --strict` (hub clean), `python scripts/wa_eval.py`, `python scripts/verify_agent_sync.py`.

Done when, all provable with raw output:
1. After the quiet window and one restart, one designated live send lands and a second controlled message gets exactly one normal reply.
2. The retry and error-logging changes have stub tests; the duplicate-safety claim still passes; host source stubs pass (`verify_wa_group_guard_source.py --hermes-repo ~/.hermes/hermes-agent`).
3. A receipt under `internal-docs/relay/` records the incident, the probe evidence, the recovery timeline, and the rollback (overlay backups under `~/.local/share/naquuuu/relay-guard-backups/`).

Evidence: four-block handoff (Result, Files Changed, Evidence, Blockers) with raw gate output, numbers only for anything relay-side.
