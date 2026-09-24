# NAQUUUU Workspace Status

- Updated: 2026-09-23
- Purpose: one-page digest for the WhatsApp relay and any agent that needs current context. Details live in `DECISION_LOG.md`, `HOSTS.md`, and the specs.

## Live today

- 7-agent opencode roster (naquuuubot + naquuuu-curator + 5 hidden subagents); personas in `.opencode/agent/`, AGY mirrors in `.agents/agents/`.
- WhatsApp relay: the owner messages Hermes; engineering tasks route to opencode via `opencode run` (Hermes skill: `opencode-relay`).
- Autonomy: shell execution is auto-approved with destructive deny-lists; `git commit` and `git push` remain the human gate.
- Remote access: Tailscale + RDP (the phone drives the desktop); SSH deferred (ADR-020).
- Gates: sanitization runs on every commit via `.githooks`; `scripts/host_check.py` checks the Hermes gateway and bridge.

## Phase state

| Phase | State |
| :--- | :--- |
| 1 Agent architecture | Done (ADR-011, ADR-013, ADR-014) |
| 2 Hermes WhatsApp | Done; gateway runs as a login item |
| 3 Relay, autonomy, AGY parity | Done (ADR-015 through ADR-018, ADR-020) |
| 4 Hosting | In progress: decoupled topology approved. The relay moves to a plain VPS (flat cost); DigitalOcean Managed Agents is a gated sandboxed worker (ADR-019 amendment) |

## Phase 4 Stage 0 (DigitalOcean gate)

- Gate 1 PASSED: deny-by-default is enforced platform-side (allowed call executed; forbidden read and write denied; `action_invoke` policy-denied; discovery filtered to the allowed tool).
- Pending owner actions: delete the superseded Allow-default session; revocation drill; Insights opt-out; card cap and threshold alerts; DO account 2FA; phone-only kill drill; console snapshot (zero triggers/schedules/KBs).
- Stage A stays blocked until the full gate set passes (HOSTS.md Section 9).

## Pending workspace items

- Spotify taste snapshot (ADR-021): implementation in progress; owner one-time Spotify app setup pending.
- Model-backend placeholder: route personal model backends to the GCP project `naquuuu` (deferred; ROADMAP line 11).
- SSH path: deferred (ADR-020); fallbacks are the Win32-OpenSSH release or Tailscale built-in SSH.

## Next steps

1. Finish the Stage 0 owner actions.
2. Provision the plain VPS relay (decoupled track).
3. Decide Stage A after the gates pass.
