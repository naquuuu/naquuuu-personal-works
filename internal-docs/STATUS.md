# NAQUUUU Workspace Status

- Updated: 2026-09-25
- Purpose: one-page digest for the WhatsApp relay and any agent that needs current context. Details live in `DECISION_LOG.md`, `HOSTS.md`, and the specs.

## Live today

- 7-agent opencode roster (naquuuubot + naquuuu-curator + 5 hidden subagents); personas in `.opencode/agent/`, AGY mirrors in `.agents/agents/`.
- WhatsApp relay hosted on the VPS (M1 complete, ADR-026): the owner messages Hermes; engineering tasks route to opencode via `opencode run` (Hermes skill: `opencode-relay`); group intake is per-group allowlist and mention-only (ADR-024). The relay survives the laptop being off.
- Auto-sync (ADR-025): gate-protected auto-commit + node auto-pull on the laptop (Scheduled Task, 10 min), the VPS (systemd user timer, 5 min), and the home server (systemd user timer, 5 min); GitHub stays canonical.
- Home server (`mipad-linux`) onboarded as a synced replica and M2 worker candidate; owner follow-ups pending (`opencode auth login`, reboot).
- Autonomy: shell execution is auto-approved with destructive deny-lists; commits and pushes are gate-protected by auto-sync and remain reviewable.
- Remote access: Tailscale + RDP (the phone drives the desktop); SSH deferred (ADR-020).
- Gates: sanitization runs via `.githooks` and again inside auto-sync; `scripts/host_check.py` checks the Hermes gateway and bridge.

## Phase state

| Phase | State |
| :--- | :--- |
| 1 Agent architecture | Done (ADR-011, ADR-013, ADR-014) |
| 2 Hermes WhatsApp | Done; gateway runs as a login item |
| 3 Relay, autonomy, AGY parity | Done (ADR-015 through ADR-018, ADR-020) |
| 4 Hosting | M1 done (relay hosted on the VPS, ADR-026); M2 (worker dispatch + queue) next. DigitalOcean Managed Agents is a gated sandboxed worker (ADR-019 amendment) |

## Phase 4 Stage 0 (DigitalOcean gate)

- Gate 1 PASSED: deny-by-default is enforced platform-side (allowed call executed; forbidden read and write denied; `action_invoke` policy-denied; discovery filtered to the allowed tool).
- Pending owner actions: delete the superseded Allow-default session; revocation drill; Insights opt-out; card cap and threshold alerts; DO account 2FA; phone-only kill drill; console snapshot (zero triggers/schedules/KBs).
- Stage A stays blocked until the full gate set passes (HOSTS.md Section 9).

## Pending workspace items

- Spotify taste snapshot (ADR-021): implementation in progress; owner one-time Spotify app setup pending.
- Model-backend placeholder: route personal model backends to the GCP project `naquuuu` (deferred; ROADMAP line 11).
- SSH path: deferred (ADR-020); fallbacks are the Win32-OpenSSH release or Tailscale built-in SSH.

## Next steps

1. M2 worker dispatch (VPS → home server) + queue.
2. Optional assistant model upgrade off the free tier.
3. Stage 0 owner actions remain for DO.
