# NAQUUUU Workspace Status

- Updated: 2026-09-27
- Purpose: one-page digest for the WhatsApp relay and any agent that needs current context. Details live in `DECISION_LOG.md`, `HOSTS.md`, and the specs.

## Live today

- 7-agent opencode roster (naquuuubot + naquuuu-curator + 5 hidden subagents); personas in `.opencode/agent/`, AGY mirrors in `.agents/agents/`.
- WhatsApp relay hosted on the VPS (M1 complete, ADR-026): the owner messages Hermes; engineering tasks route to opencode via `opencode run` (Hermes skill: `opencode-relay`); group intake is per-group allowlist and mention-only (ADR-024). The relay survives the laptop being off.
- Assistant provider policy (ADR-028, owner-set 2026-09-25): Nous Portal is primary for the Hermes relay assistant, Gemini is the fallback. Image generation is paid and key-gated via `scripts/gen_image.py` (configurable model, 3-model fallback chain; `GEMINI_IMAGE_KEY`, fallback `GOOGLE_API_KEY`); there is no viable free image tier. Group intake is an owner-driven command (`scripts/wa_group_allow.py`, allowlist + mention gate; `open`/allow-all refused).
- Auto-sync (ADR-025): gate-protected auto-commit + node auto-pull on the laptop (Scheduled Task, 10 min), the VPS (systemd user timer, 5 min), and the home server (systemd user timer, 5 min); GitHub stays canonical.
- Home server (`mipad-linux`) onboarded as a synced replica and M2 worker candidate; owner follow-ups pending (`opencode auth login`, reboot).
- M2 worker dispatch (ADR-029) is authored and **Proposed - NOT live**: the relay host will dispatch heavy jobs to `mipad-linux` over Tailscale with the dedicated relay-to-worker key (`NAQUUUU_WORKER_KEY`) and queue them durably when the worker is offline; light work stays on the relay host. Queued output is archived under `done/` and summarized by `scripts/job_status.sh` (`--prune` bounds retention); the relay skill is not yet wired to poll it, so a queued job produces no automatic reply. Pending worker SSH trust (`scripts/authorize_worker.sh`, owner-run) and owner approval. Heavy jobs currently run on the relay host.
- Tailscale ACL hardening is drafted (`internal-docs/TAILSCALE_ACL.md`) to put personal devices behind `tag:personal` with default-deny; not applied. The tailnet currently mixes work machines with personal devices.
- Autonomy: shell execution is auto-approved with destructive deny-lists; commits and pushes are gate-protected by auto-sync and remain reviewable.
- Remote access: Tailscale + RDP (the phone drives the desktop); SSH deferred (ADR-020).
- Gates: sanitization runs via `.githooks` and again inside auto-sync; `scripts/host_check.py` checks the Hermes gateway and bridge.

## Phase state

| Phase | State |
| :--- | :--- |
| 1 Agent architecture | Done (ADR-011, ADR-013, ADR-014) |
| 2 Hermes WhatsApp | Done; gateway runs as a login item |
| 3 Relay, autonomy, AGY parity | Done (ADR-015 through ADR-018, ADR-020) |
| 4 Hosting | M1 done (relay hosted on the VPS, ADR-026). M2 (worker dispatch + durable queue, ADR-029) authored and Proposed - pending worker SSH trust and owner approval; heavy jobs still run on the relay host. Tailscale ACL hardening drafted, not applied. DigitalOcean Managed Agents is a gated sandboxed worker (ADR-019 amendment) |

## Phase 4 Stage 0 (DigitalOcean gate)

- Gate 1 PASSED: deny-by-default is enforced platform-side (allowed call executed; forbidden read and write denied; `action_invoke` policy-denied; discovery filtered to the allowed tool).
- Pending owner actions: delete the superseded Allow-default session; revocation drill; Insights opt-out; card cap and threshold alerts; DO account 2FA; phone-only kill drill; console snapshot (zero triggers/schedules/KBs).
- Stage A stays blocked until the full gate set passes (HOSTS.md Section 9).

## Pending workspace items

- Spotify taste snapshot (ADR-021): implementation in progress; owner one-time Spotify app setup pending.
- Model-backend placeholder: route personal model backends to the GCP project `naquuuu` (deferred; ROADMAP line 11).
- SSH path: deferred (ADR-020); fallbacks are the Win32-OpenSSH release or Tailscale built-in SSH.
- M2 activation (ADR-029): owner approval plus the owner-run `scripts/authorize_worker.sh` on the worker; the M2 scripts are authored (dedicated relay-to-worker key, `job_status.sh`) and the relay skill is not switched to dispatch until both land.
- Home server (`mipad-linux`): `opencode auth login` and a reboot remain; it is also the M2 worker.
- Tailscale ACL hardening (`internal-docs/TAILSCALE_ACL.md`): apply from the Tailscale admin console and test before trusting it.
- Group presence (Mode 2) is authored against the verified Hermes v0.21.4 behaviour and **pending owner rollout on the relay host**: free-response is per group via `WHATSAPP_FREE_RESPONSE_CHATS` (group-wide chat, no @mention, sender allowlist bypassed for that chat — a deliberate owner decision; a new group is mention-only until promoted), and tool execution is owner-only through `scripts/wa_owner_gate.py` (`NAQUUUU_WA_OWNER_IDS`, host env only) with guests chat-only. There is **no thread awareness or observation for WhatsApp** on this version, so the relay is stateless per turn, and silence is `NO_REPLY`. Owner-run, not yet on the host: `scripts/wa_free_response.py` and `scripts/wa_owner_gate.py`.

## Next steps

1. M2: owner approval + worker key authorization (`scripts/authorize_worker.sh`, using the dedicated `~/.ssh/id_ed25519_worker.pub`); then switch the relay skill to dispatch and verify (ADR-029).
2. Apply the Tailscale ACL hardening (`internal-docs/TAILSCALE_ACL.md`) and test it before trusting it.
3. Home-server follow-ups: `opencode auth login` + reboot.
4. Optional: raise the assistant model above the free tier (ADR-027 capability bar).
5. Stage 0 owner actions remain for DO.
