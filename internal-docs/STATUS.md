# NAQUUUU Workspace Status
<!-- verified-against: ADR-043 -->

- Updated: 2026-10-05
- Purpose: one-page digest for the WhatsApp relay and any agent that needs current context. Details live in `DECISION_LOG.md`, `HOSTS.md`, and the specs.

## Live today

- **Relay baseline (2026-09-28 and 2026-09-30):** the 09-28 owner message round-trip verified the then-current session, bridge, gateway, owner gate, and `opencode run`; the 09-30 bounded journal contained 27 occurrences of 503, 30 of 429, and 11 timeout matches, without identifying affected turns or proving a cause for duplicate replies or prolonged group typing. Do not run `hermes update` on the relay host. See `L-17` through `L-21`, `ASTRA_HANDOFF.md`, and the runbook.
- **Relay guard rollout (2026-10-05, partial acceptance):** 49 targeted regression tests and sanitization passed; the sanitizer scanned 11 changed/new Python files with zero findings. Patched-source stubs passed normal, queued, and crash group-silence and send/poll cases; synthetic leak and identity canaries passed. The gateway was restarted once and reported active, `NRestarts=0`, bridge `connected=true`, and no startup import errors. No real test message was sent, so phone/group end-to-end behavior, duplicate final replies, and typing cleanup are not declared verified. Receipt: `internal-docs/relay/2026-10-05-TEXT_ART_LOOP_FIX.md`. Follow-through deployed a single-invocation wrapper, uncertain-send replay stop, explicit paused typing, and a 15-second safety lease. Installed-source stubs passed; gateway active with zero restarts and bridge connected. Native dashboard integration and remaining acceptance are recorded in `relay/2026-10-05-HERMES_ACTIVITY_INTEGRATION.md`.
- **Hermes Dashboard (ADR-040; integration checked 2026-10-05):** Native Agents tab installed at `/agents`, with privacy-limited OpenCode counts and naquuuu light/dark themes. Eight viewport/mode checks passed; activity API rejects unauthenticated requests with 401. Gateway stayed active during dashboard restart. Authenticated owner-device navigation is unverified. Earlier network/access checks: owner-configured built-in auth; service enabled and active with the only 9119 listener on loopback. Tailscale Serve routes HTTPS to the loopback service; status required auth and unauthenticated `/api/config` returned 401. UFW had no 9119 rule and Funnel was not configured. Login from a tailnet device, off-tailnet reachability, and cloud firewall remain unverified.
- 7-agent opencode roster (naquuuubot + naquuuu-curator + 5 hidden subagents); personas in `.opencode/agent/`, AGY mirrors in `.agents/agents/`.
- **Cost-aware model routing (ADR-041, 2026-09-30):** use the configured lower-cost specialist model for routine implementation and deterministic checks; the orchestrator retains architecture, privacy/security, review, and integration decisions and escalates for uncertainty or risk. Cost does not relax the Tier 1/Hermes-state exclusion. Timing comparisons are not established; do not infer them from configuration.
- WhatsApp relay hosted on the VPS (M1, ADR-026): group intake is allowlisted; speaking may be per-group free-response, while tool execution remains owner-only through the fail-closed `scripts/wa_owner_gate.py` (`NAQUUUU_WA_OWNER_IDS`, host env only). A newly admitted group is mention-only until owner promotion. The gateway does not depend on the laptop; ADR-043 removes it from standby/failover duties as well.
- Assistant provider policy (ADR-028, owner-set 2026-09-25): Nous Portal is primary and Gemini fallback. Provider status and actual turn outcomes must be checked separately; the 09-30 error counts did not attribute failures. Image generation is paid and key-gated; do not use it for ordinary text art.
- Auto-sync (ADR-025): gate-protected auto-commit + node auto-pull. Last recorded laptop Scheduled Task state (2026-09-25) was `Disabled`; VPS and home-server timers were recorded active. GitHub stays canonical. Auto-sync stages and audits the staged snapshot, including new files, before publication. Current scheduler state has not been refreshed.
- **Relay standby decision (ADR-043, proposed 2026-10-02):** the employer-managed laptop is no longer an approved relay standby or failover dependency. `mipad-linux` is the proposed standby and intended sole holder of the rollback session after a verified transfer; this is not yet implemented. Hermes-on-standby setup, session transfer and laptop-copy deletion after verification, phone-to-VPS kill-switch check, Linux `host_check.py` support, and a two-way drill remain open. The laptop remains the workstation/co-writer; whether the hub `.env` stays there remains open.
- **M2 worker dispatch (ADR-029; last recorded state in September docs): BLOCKED.** Worker SSH authentication, authorization, heavy execution, archive verification, and the relay-skill switch remain unverified/blocked; the drain timer and isolated offline-queue test alone do not prove readiness. Queued jobs do not yet have verified completion feedback. Keep worker dispatch separate from the proposed standby role.
- Tailscale ACL hardening is drafted (`internal-docs/TAILSCALE_ACL.md`) to put personal devices behind `tag:personal` with default-deny; not applied. The tailnet currently mixes work machines with personal devices.
- Autonomy: shell execution is auto-approved with destructive deny-lists. Commits and pushes are gate-protected, but auto-sync **publishes whatever an agent left behind** - it is not a review gate (`L-04`; a bad model pin once went live this way). Treat a commit needing approval as a real requirement, not a formality.
- Remote access: Tailscale + RDP (the phone drives the desktop); SSH deferred (ADR-020).
- Gates: sanitization runs via `.githooks` and again inside auto-sync, which stages first and audits the staged snapshot (`verify_sanitization.py --staged`); auto-sync fails closed if the gate cannot run. Historical relay-host gate gaps remain documented in `L-04` and `internal-docs/relay/VPS_RELAY_RUNBOOK.md`.
- **Git/audit evidence (2026-10-05):** the recorded strict multi-repo audit failed on the preserved dirty/diverged hub, an existing dirty child repo, and stale `STATUS.md`/`LESSONS.md` digests. Those two digests are reconciled here; strict audit has not been rerun, and this worktree remains intentionally dirty. The separate sanitizer result passed across 11 changed/new Python files. No commit or push was made.

## Phase state

| Phase | State |
| :--- | :--- |
| 1 Agent architecture | Done (ADR-011, ADR-013, ADR-014) |
| 2 Hermes WhatsApp | Done; gateway runs as a login item |
| 3 Relay, autonomy, AGY parity | Done (ADR-015 through ADR-018, ADR-020) |
| 4 Hosting | M1 is the live VPS relay (ADR-026). M2 worker dispatch is blocked pending worker SSH trust and verified execution/archive/skill integration (ADR-029). ADR-043 proposes `mipad-linux` as relay standby and removes relay duties from the employer-managed laptop; owner-run migration and two-way drill remain pending. Tailscale ACL hardening is drafted, not applied. DigitalOcean Managed Agents remains gated (ADR-019 amendment). |

## Phase 4 Stage 0 (DigitalOcean gate)

- Gate 1 PASSED: deny-by-default is enforced platform-side (allowed call executed; forbidden read and write denied; `action_invoke` policy-denied; discovery filtered to the allowed tool).
- Pending owner actions: delete the superseded Allow-default session; revocation drill; Insights opt-out; card cap and threshold alerts; DO account 2FA; phone-only kill drill; console snapshot (zero triggers/schedules/KBs).
- Stage A stays blocked until the full gate set passes (HOSTS.md Section 9).

## Pending workspace items

- Spotify taste snapshot (ADR-021): live fetch succeeded 2026-09-28 with existing authorization; cache-only status tested with zero network. Setup remains documented in SPOTIFY_INTEGRATION.md.
- Model-backend placeholder: route personal model backends to the GCP project `naquuuu` (deferred; ROADMAP line 11).
- SSH path: deferred (ADR-020); fallbacks are the Win32-OpenSSH release or Tailscale built-in SSH.
- M2 worker dispatch (ADR-029): blocked until worker SSH trust, one-job execution, archive verification, and completion reporting are proven; do not treat a ready drain timer or offline-queue test as dispatch readiness.
- Relay standby migration (ADR-043, proposed): configure Hermes disabled on `mipad-linux`, verify transfer of the sole rollback session and remove the laptop copy only after verification, validate phone-to-VPS SSH and `hermes gateway stop`, add Linux `host_check.py` support, then perform the two-way drill. The laptop is not a relay standby.
- Tailscale ACL hardening (`internal-docs/TAILSCALE_ACL.md`): apply from the Tailscale admin console and test before trusting it.
- Group presence (Mode 2): owner-only chat policy hooks and 2026-10-05 group guards are deployed. The bridge caches bridge-sourced display names, refuses unresolved outbound identifiers, and handles owner-only group commands; admission does not itself promote free-response. The guard filters unaddressed idle group statuses; `NO_REPLY` is reserved for WhatsApp group idle status/routine bot acknowledgements, never direct substantive questions. User-requested text art/repetition is ordinary text, bounded to 3,600 characters/100 repeats; at most 128 request grants are retained for 10 minutes and replies use the exact inbound ID in `replyTo`. Targeted tests and synthetic canaries passed, but no real phone/group message was sent; the phone command matrix, proactive greeting, final-reply uniqueness, and full typing cleanup remain unverified. See `L-31` and the 2026-10-05 receipt.

## Next steps

1. Resolve owner-run ADR-043 migration requirements: disabled Hermes setup on `mipad-linux`, verified session transfer, phone-to-VPS kill-switch check, Linux readiness support, and a two-way drill.
2. Keep M2 worker dispatch blocked until worker trust, execution, archive verification, and completion feedback pass separately from standby readiness.
3. Apply and test the Tailscale ACL hardening (`internal-docs/TAILSCALE_ACL.md`) before trusting it.
4. Obtain a designated test target before live phone/group checks; then verify reply uniqueness, mention/free-response behavior, typing cleanup, and owner-only actions.
5. Stage 0 owner actions remain for DO. No model timing comparison or paid benchmark is recorded; follow ADR-041's cost-aware policy.

## Astra execution receipt

See `ASTRA_EXECUTION_REPORT.md` for earlier workstream evidence and remaining live checks. Runtime guards and an authenticated warm wrapper were deployed; provider/model pins were unchanged in that receipt. ADR-034 accepts authenticated reply-context commands and the sixty-second generic status exception. ADR-041 governs cost-aware agent routing; ADR-043 supersedes laptop standby assumptions, with migration still pending.
