# VPS Relay Runbook (M1)

- Purpose: provision the always-on VPS relay so the WhatsApp front door survives the laptop being off.
- Status: M1 complete (2026-09-25): relay hosted on the VPS; verified from WhatsApp.
- Related: `internal-docs/HOSTS.md` §4.3, §5.2, §5.4; `internal-docs/DECISION_LOG.md` ADR-019 amendment, ADR-024 through ADR-029; `internal-docs/relay/README.md`; `internal-docs/relay/M2_DISPATCH_RUNBOOK.md` (M2, pending); `internal-docs/TAILSCALE_ACL.md` (drafted, pending).
- Scope: M1 = the relay survives the laptop being off (WhatsApp front door always on).
- Non-goals for M1: heavy dev-task execution on the VPS is M2; DO Managed Agents stays behind the Phase 4 gate set (`HOSTS.md` §9). M1 landed a repo-scoped ed25519 deploy key, so the VPS writes (scoped) under gate-protected auto-sync (ADR-025, ADR-026). M2 worker dispatch is authored and Proposed (ADR-029) - pending worker SSH trust and owner approval, not live; see `internal-docs/relay/M2_DISPATCH_RUNBOOK.md`.

## Target host

| Item | Value |
| :--- | :--- |
| Host | Tencent Cloud Lighthouse |
| Package | 2 vCPU / 2 GB RAM / 20 Mbps / 40 GB disk |
| Region | Singapore |
| Image | Ubuntu 24.04 LTS |
| Note | 2 GB is the M1 minimum (add swap); upgrade the package if M2 needs more |

## Step 0 — Purchase checklist

- [ ] Lighthouse "2vCPUs Linux" first-deal promo (2vCPUs2G 20M40G Starter).
- [ ] Region: Singapore.
- [ ] Image: **Ubuntu 24.04 LTS** (do NOT pick the app images: Hermes Agent, OpenCode, OpenClaw/Moltbot — their base layout is undocumented and versions are pinned old).
- [ ] 6-month term.
- [ ] Add an ed25519 SSH key at creation (no password login).
- [ ] Console firewall: allow TCP 22 only (restrict to owner IPs where possible); everything else via Tailscale.

## Step 1 — Base setup (default sudo user, e.g. `ubuntu`)

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl xz-utils git ufw unattended-upgrades
```

- Swap: create a 2 GB swap file — `sudo fallocate -l 2G /swapfile`, `sudo chmod 600 /swapfile`, `sudo mkswap /swapfile`, `sudo swapon /swapfile` — and persist it in `/etc/fstab`.
- Timezone: `sudo timedatectl set-timezone Asia/Jakarta`.
- UFW: `sudo ufw default deny incoming`; `sudo ufw default allow outgoing`; `sudo ufw allow OpenSSH`; `sudo ufw allow in on tailscale0`; `sudo ufw enable`.
- Enable unattended-upgrades.

## Step 2 — Tailscale

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

- Owner authenticates.
- Note the tailnet node name.
- Optional later: `sudo tailscale set --ssh` (phone SSH without keys).

## Step 3 — Hermes (per-user, lean)

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash -s -- --skip-browser --skip-computer-use
sudo loginctl enable-linger <user>
```

- `enable-linger` keeps the user service alive across logout and reboot.
- Provider keys: configure owner-side (`hermes model` / `~/.hermes/.env`); personal model routing stays on the personal GCP project per AGENTS.md Critical Rule 3; never in chat or the repo.
- WhatsApp values in `~/.hermes/.env`: mirror the laptop's WhatsApp-related lines only (WHATSAPP_ENABLED / WHATSAPP_MODE / WHATSAPP_ALLOWED_USERS / WHATSAPP_GROUP_POLICY / WHATSAPP_GROUP_ALLOWED_USERS / WHATSAPP_REQUIRE_MENTION), plus WHATSAPP_FREE_RESPONSE_CHATS for the groups promoted to free-response and NAQUUUU_WA_OWNER_IDS for the owner gate (Tier 1, host-only; see `Group presence (owner-run)`).
- The hub `.env` (`C:\personal\naquuuu\.env`) never goes to the VPS.
- Do not start the gateway yet.

### Relay persona and display

- The SOUL persona canonical in `internal-docs/relay/WHATSAPP_SOUL.md` is copied to `~/.hermes/SOUL.md` on the relay host (ADR-027); a persona change lands in both.
- WhatsApp display settings (`display.platforms.whatsapp`): `{tool_progress: off, show_reasoning: false, interim_assistant_messages: false, streaming: false}`.
- Curator-directed messages (`@curator`, "ask the curator", "curator:") route to `opencode run --agent naquuuu-curator`.
- Image generation runs through `scripts/gen_image.py` (Gemini API; configurable model with a 3-model fallback chain; no viable free tier; keyed by `GEMINI_IMAGE_KEY`, fallback `GOOGLE_API_KEY`); the bot delivers it with the `MEDIA:` directive; vision (reading images) needs a multimodal provider configured under `auxiliary.vision`.

## Step 4 — opencode + runtime clone

```bash
curl -fsSL https://opencode.ai/install | bash
git clone https://github.com/naquuuu/naquuuu-personal-works.git ~/naquuuu
```

- The repo is public; the clone started read-only, then the remote was switched to SSH with the repo-scoped deploy key (see Gotchas). opencode 1.18.32 with `opencode-go` auth.
- Owner-side provider auth for opencode.
- Smoke test (no writes, no commits): `cd ~/naquuuu && opencode run --agent naquuuubot "Reply with the current branch."`

Gate arming (relay host — this host pushes to a public remote):

1. `cd ~/naquuuu && git config core.hooksPath .githooks` — the same line `scripts/provision_home_server.sh` sets for the home server. The VPS path had no step for it.
2. `sudo apt install -y python3` — the Step 1 package list does not install it, and the sanitization gate cannot run on this host without an interpreter.
3. One-command form of both: `./scripts/enable_gates.sh` (add `--check` for a read-only status run). Re-run it after any re-clone; an unarmed host is a push-capable writer with no gate.

### Heavy jobs (M2, pending)

- M1 runs every job locally on the VPS. M2 (authored, Proposed - ADR-029) adds `scripts/dispatch_job.sh`: heavy jobs go to the home server (`mipad-linux`) over Tailscale using the dedicated relay-to-worker key (`NAQUUUU_WORKER_KEY`) and queue durably when the worker is offline; light work stays local. Queued output is archived under `done/` and summarized by `scripts/job_status.sh`; the relay skill is not yet wired to poll the queue (no automatic reply).
- NOT live: the relay skill does not dispatch until the worker SSH trust is authorized with `scripts/authorize_worker.sh` and the owner approves. Full steps: `internal-docs/relay/M2_DISPATCH_RUNBOOK.md`.

## Step 5 — Relay skill (Linux variant)

- Install to `~/.hermes/skills/relay/opencode-relay/SKILL.md` using the exact block in the Appendix.
- The Windows canonical copy stays in `internal-docs/relay/README.md`.

## Step 6 — WhatsApp session move

Only ONE bridge may run at a time — never laptop and VPS together.

1. Laptop: `hermes gateway stop`.
2. Keep a copy of `%LOCALAPPDATA%\hermes\whatsapp\session` as the rollback backup.
3. On the VPS, verify the bridge's expected session path (`~/.hermes/whatsapp/session`; if the installed version uses `platforms/whatsapp/...`, place it there — check the bridge process args).
4. Transfer over Tailscale (scp/WinSCP), owner-run; never through chat or the repo.
5. `hermes gateway install` and `hermes gateway start`.
6. Verify with `hermes gateway status` plus a phone "hello".
7. Fallback if the copied session is rejected: `hermes whatsapp` QR re-pair (owner-private scan).

## Step 6.5 — Deploy sync (after `git pull` / host-tool-gate migration)

When pulled code changes the owner-auth patches (e.g. the ADR-035 host-only guard), re-run the installer and reload the gateway. Always use the Hermes venv interpreter, never system `python3`.

1. `cd ~/naquuuu && git pull`.
2. `~/.hermes/hermes-agent/venv/bin/python scripts/install_wa_owner_auth.py --hermes-repo ~/.hermes/hermes-agent` (migrates the V2 executor block in place, writes timestamped backups, never restarts).
3. `~/.hermes/hermes-agent/venv/bin/python scripts/install_wa_owner_auth.py --hermes-repo ~/.hermes/hermes-agent --check` must print `owner-auth patches are fully installed on the pinned source`.
4. Mirror the persona before the restart so it loads with the new gate: `cp ~/naquuuu/internal-docs/relay/WHATSAPP_SOUL.md ~/.hermes/SOUL.md` (ADR-027 mirror rule).
5. Never restart blindly: confirm the gateway's `session_turn_leases` count is 0 (no in-flight turns); if not, wait and re-check. The exact read command is not yet recorded in this runbook; add it here after the next deploy.
6. `systemctl --user restart hermes-gateway.service`, then `systemctl --user status hermes-gateway.service`.

## Step 7 — Readiness + switch drill

1. `cd ~/naquuuu && python scripts/host_check.py` → expect READY.
2. Run the `HOSTS.md` §5.4 drill both directions; log results.

```mermaid
flowchart LR
  A["Laptop: gateway stop<br/>(tree committed + pushed)"] --> B["VPS: pull + host_check READY + gateway start"]
  B --> C["Phone: hello + repo-status question"]
  C --> D["Reverse drill: VPS to laptop and back"]
```

## Step 8 — Rollback

1. Stop the VPS gateway.
2. Restore the laptop session copy if needed.
3. Start the laptop gateway.
4. Verify with a phone "hello".

## Relay recovery (2026-09-28 outage)

This section is the recovery procedure for a lost or contested WhatsApp session on the relay host. It is written for the failure as observed, not for a hypothetical one.

**Incident as recorded (2026-09-28).** The WhatsApp session was quarantined as `session.dead-<timestamp>`; the replacement session was left unpaired; the Hermes gateway was stopped; the systemd unit still carried `Restart=always`. Two root causes, in order of importance:

1. **A second host was still running a bridge.** ADR-026 moved the relay to the VPS, but the laptop's Hermes gateway auto-start (a Startup-folder `Hermes_Gateway.vbs`) was never disarmed, so after any login a second host could run a bridge against the same WhatsApp account.
2. **`Restart=always` re-spawned the bridge immediately on failure.** Each re-pair attempt compounded the previous one and escalated a single logout into a provider rate limit.

**The order is the fix.** Perform the steps in the order written. The order was the defect; a correct step performed out of order reintroduces the fault.

0. **Stop retrying.** The repeated attempts are what caused the block, not the logout. Wait out the provider rate-limit window before touching anything else. No window length is recorded here; use what the provider itself reports.
1. **Disarm every OTHER host's bridge auto-start first.** On the Windows laptop that is the Startup-folder `Hermes_Gateway.vbs` entry. Then verify nothing else holds the session: no `hermes` process on any other host, and nothing listening on port 3000.
2. **Change `Restart=always` to `Restart=on-failure` on the relay host.** Use a systemd drop-in, non-interactive:

   ```bash
   mkdir -p ~/.config/systemd/user/hermes-gateway.service.d
   printf '[Service]\nRestart=on-failure\nRestartSec=30\n' > ~/.config/systemd/user/hermes-gateway.service.d/restart.conf
   systemctl --user daemon-reload
   ```

   Assumption: the unit is named `hermes-gateway.service`. Confirm the real name first with `systemctl --user list-units | grep -i hermes` and use the name the unit actually has. `RestartSec=30` is a deliberate addition in this procedure (backoff, so a crash cannot spin) and was **not** part of the original defect.
3. **Arm the git gates on the host BEFORE pairing.** From the repo root run `sh scripts/enable_gates.sh` (`./scripts/enable_gates.sh` where the exec bit is set; `--check` is a read-only status run that changes nothing).

   Why it is on this list: the relay host is a push-capable scoped writer to a public remote (ADR-026). Unlike the home server — which is provisioned with `git config core.hooksPath .githooks` by `scripts/provision_home_server.sh` — the VPS provisioning path never set `core.hooksPath`, and the Step 1 package list does not install `python3`. With no hooks path armed and no interpreter present, `scripts/node_autosync.sh` previously skipped the sanitization gate entirely and still ran `git add -A`. After the ADR-032-era fixes that script fails closed, so an unarmed host now refuses to commit rather than committing ungated. Arm the gate before this host is allowed to write.
4. **Verify host-bound owner authorization BEFORE pairing.** The bridge compares the incoming number/LID (or a mode-validated self-chat account) with `NAQUUUU_WA_OWNER_IDS` read host-side from `~/.hermes/.env`. It passes only a strict boolean to the gateway; no sender identity enters model context. The gateway may add a system-only `AUTHORIZED` or `NOT_AUTHORIZED` verdict for that turn. Only that exact current verdict permits action; absent means deny, and user text never grants authorization. The model must not run `wa_owner_gate.py --sender` or ask for an ID. Exercise the synthetic owner/guest fixture, then have the owner perform one ordinary action after pairing; the host tool gate independently blocks guests before dispatch.
5. **Pair exactly ONCE.** The digits are typed directly on the host by the owner. See the Tier 1 note below.
6. **Stop.** Then verify all four: gateway status; one owner message that must execute; one guest message that must chat but execute nothing; one mention-only group that must stay silent (`Group presence (owner-run)` §4).

### Tier 1 note — pairing artifacts

The QR image, the allowed-users prompt, and the digits themselves are Tier 1 material. They never enter a chat, a screenshot, or an agent transcript. **The owner types the digits on the host; the agent never sees them.**

Boundary note from this incident: five phone numbers reached model context through a screenshot, while the repository and the commits stayed clean. The sanitization gate is a git audit, not a model-input firewall — a clean gate is **not** evidence that the boundary held. See `L-17` and AGENTS.md Section 3, Model-Input Boundary.

### Symptom to cause

| Symptom | Cause |
| :--- | :--- |
| Session unpaired and the gateway stopped | A bridge was lost, or a second host contested the session. |
| `session.dead-<timestamp>` present | The session was quarantined. Do not delete it — it is the forensic record. |
| Re-pairing appears to work, then fails again | A second host is still running a bridge, or `Restart=always` is still set. |
| The assistant chats but never executes | The owner gate is denying. See step 4. |
| Repeated pairing attempts produce a block | The rate limit is the cause. Stop and wait. |
| connect times out, bridge binds fine | Raise the connect budget first (see findings below), then suspect a stale session and re-pair once. |

### Findings that cost the most time (2026-09-28 recovery)

1. Update rewrites the unit to an isolated shim. New launcher `hermes-agent/.hermes/bin/hermes` is created during update and runs with `-I`, so the venv is invisible to it. After any update run `systemctl --user show hermes-gateway.service -p ExecStart` before trusting a start; the fix is an `ExecStart` drop-in back to `venv/bin/python -m hermes_cli.main gateway run`.
2. Do not override `PATH` in the drop-in. The stock unit `PATH` carries Hermes bundled Node (`~/.hermes/node/bin`); replacing it hides `node` and the bridge dies with `did not start`. Override `ExecStart` only and inherit the rest.
3. A stray gateway turns every fresh start into a no-op. Any stray PID serving the host makes a new start exit 75 in under a second. Before starting check `ss -tln | grep 3000`, `pgrep -af bridge`, and `systemctl --user is-active hermes-gateway.service`; kill strays first.
4. Small-host timeouts: env first (see `L-19`). Bridge poll is `_poll_bridge_health` (`for attempt in range(15)` -> `range(90)`); connect is `_connect_adapter_with_timeout` (default `_PLATFORM_CONNECT_TIMEOUT_SECS_DEFAULT`, 30s) honoured via `HERMES_GATEWAY_PLATFORM_CONNECT_TIMEOUT` in `gateway/run_adapters.py:145-162`. Mandatory pre-launch: `echo ${HERMES_GATEWAY_PLATFORM_CONNECT_TIMEOUT:-UNSET}` — UNSET means silently on the default; a code patch is wiped by the next update.

## Group presence (owner-run)

Ground truth (verified on the relay host, Hermes v0.21.4): **no thread awareness or observation exists for WhatsApp** — upstream support is Telegram-only. The relay is stateless per turn; each turn sees only the chat text of the triggering message. Two per-chat decisions, kept separate:

- **Speaking** — a chat id in `WHATSAPP_FREE_RESPONSE_CHATS` is free-response: the whole group can message the bot with no @mention, and for that chat the sender allowlist (`WHATSAPP_ALLOWED_USERS`) is bypassed. Any other group is mention-only (`WHATSAPP_REQUIRE_MENTION=true`; an @mention, a reply, a slash command, or the bot name counts as addressed).
- **Acting** — owner-only. The bridge verifies configured owner identity and passes a strict boolean to the host tool gate, which runs before tool hooks or execution and fails closed. The model never receives sender identity or an ALLOW/DENY token and must not run `wa_owner_gate.py --sender`.

### Recorded on-host capability evidence (2026-09-27)

Read directly on the relay host over key-only SSH, and reproducible with `python3 scripts/wa_free_response.py --check` on that host:

```
hermes_version                     0.21.4
free_response_supported            true
awareness_supported_for_whatsapp   false
```

Sources on the host: `WHATSAPP_FREE_RESPONSE_CHATS` is read by `gateway/platforms/whatsapp_common.py::_whatsapp_free_response_chats`, and the group path bypasses the sender allowlist for listed chats (`_should_process_message`); `observe_unmentioned_group_messages` is bridged for Telegram only (`gateway/config_loader.py`), so no observation applies to WhatsApp on this version. No host file contents, secrets, or ids were read to produce this.

### 1. Promote an existing allowlisted group to free-response

1. Confirm the group is already allowlisted: `python3 scripts/wa_group_allow.py --list` (counts only, never chat ids).
2. Add it to free-response: `python3 scripts/wa_free_response.py --add <CHATID>`. The chat id is a placeholder here; take the real value from the gateway log on the host, never from chat, a repo, or model context. The script is idempotent and writes a timestamped backup before editing.
3. Confirm the new count: `python3 scripts/wa_free_response.py --list`.
4. Roll back: `python3 scripts/wa_free_response.py --remove <CHATID>` — the group returns to mention-only. Its group-allowlist entry is untouched; promotion and admission are independent.
5. Reload: `systemctl --user restart hermes-gateway.service` (fall back to `hermes gateway restart` if the service manager balks).

A new group is mention-only from the moment it is admitted; free-response is a separate, deliberate promotion.

### 2. Set the owner ids on the host

1. Owner-side only, on the relay host: set `NAQUUUU_WA_OWNER_IDS` in `~/.hermes/.env` as full international digits, comma-separated, no `+`.
2. Owner ids are Tier 1: they live only in the host env — never in the repo, never in `internal-docs/`, never in chat, never in model output (ADR-027 §2, ADR-028 §5, AGENTS.md Model-Input Boundary).
3. Never set the wildcard form. An empty or unreadable owner list must deny, not allow: an unset `NAQUUUU_WA_OWNER_IDS` locks the bot out of tool execution rather than opening it.
4. Reload: `systemctl --user restart hermes-gateway.service`.

### 3. "Add this group" from WhatsApp

Group admission from chat is handled by the host chat policy (host-side command-gate, ADR-034), not by the bot running a script. The model never runs `wa_owner_gate.py`, `wa_group_allow.py`, or `wa_free_response.py` from chat. Owner-side on the relay host, group admission and promotion scripts are host-shell-only: `python3 scripts/wa_group_allow.py --add-latest` (for admission) and `python3 scripts/wa_free_response.py --add <CHATID>` (for promotion); these scripts never run from a WhatsApp turn even when owner-AUTHORIZED, and the host tool gate blocks them. Free-response promotion is a separate deliberate step, host-run; the bot never promotes a group on a guest request.

### 4. Verify (four checks)

1. **Guest chat in a free-response group**: a non-owner member sends a plain message with no @mention → the bot replies in 1-3 sentences. No numbers, ids, or JIDs in the reply.
2. **Guest cannot execute**: the same guest asks for a tool, a status run, or an install → the bot replies conversationally and **nothing executes**; no skill runs and no files change.
3. **Owner can execute**: the owner sends the same request → the skill runs and the result comes back trimmed.
4. **Mention-only group holds**: in a group absent from `WHATSAPP_FREE_RESPONSE_CHATS`, an unaddressed message draws no reply, while an @mention, reply, slash command, or bot name gets one. The bot must not claim it read the room.

### Persona mirror

Any change to `internal-docs/relay/WHATSAPP_SOUL.md` lands in both the repo copy and `~/.hermes/SOUL.md` on the relay host (mirror rule, ADR-027). A group-presence change is a persona change and must land in both.

### Initiative post (OPTIONAL, off by default)

A bounded nudge: a Hermes cron job that calls `send_message`, capped to **at most one post per day**. The exact cron/`send_message` syntax is **TO BE CONFIRMED** against the installed Hermes version before it is presented as working - do not run unverified syntax. Keep it bounded: one line, no process narration. It is opt-in and stays off while the persona defaults to `NO_REPLY`, and it is never a response to an unaddressed message flood.

## Gotchas (as executed)

- Only one WhatsApp bridge at a time: after `hermes gateway stop`, an orphaned `bridge.js` can survive; verify port 3000 is free before starting another host.
- The WhatsApp env transfer must include `WHATSAPP_ENABLED`; a filtered copy missed it and the bridge stayed off.
- Run `npm install` in the bridge directory before the first VPS start.
- The deploy key makes the VPS a scoped writer: the clone remote was switched to SSH (`git@github.com:...`); a push was verified (`Everything up-to-date`). Scope is that one repository; revocable from the repo's Deploy keys page.

## Security notes

- No hub `.env` on the VPS.
- Tier 1 never in model context.
- SSH key-only; UFW enabled.
- Unattended upgrades on.
- Tailscale-only admin access.
- Kill switch from the phone: tailnet SSH → `hermes gateway stop`.

## Deferred

- M2: authored (ADR-029); dispatch + durable queue runbook in `internal-docs/relay/M2_DISPATCH_RUNBOOK.md`; pending worker SSH trust and owner approval. Heavy jobs on the worker may avoid the possible 4 GB VPS upgrade.
- Relay multi-turn parity.
- DO Stage A behind the Phase 4 gates.

## Appendix — Relay skill (Linux) canonical copy

```markdown
---
name: opencode-relay
description: "Route NAQUUUU workspace questions and engineering tasks from WhatsApp to the local opencode orchestrator (naquuuubot) and return the result."
version: 2.0.0
author: naquuuu
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [relay, opencode, workspace, engineering, orchestration, status]
prerequisites:
  commands: [opencode]
---

# OpenCode Relay (Linux / VPS)

Use this skill for anything about the NAQUUUU workspace: status questions, plan or history questions, and engineering work.

## 1. Questions about status, plans, or history

Answer from the repository, never from memory:

1. Read `~/naquuuu/internal-docs/STATUS.md` first (current state digest).
2. Read `~/naquuuu/internal-docs/LESSONS.md` (curated lessons) before searching.
3. For details, search `~/naquuuu/internal-docs/` and `git log` in `~/naquuuu`.
4. Answer with the source path(s). If the workspace does not answer it, say "not in the workspace" explicitly.

## 2. Engineering tasks (development)

0. HOST GATE FIRST: the bridge binds authorization privately and the gateway blocks non-owner actions before execution. Do not ask for or inspect sender IDs and do not run `wa_owner_gate.py` from the model. Make the normal relevant tool call for an action request; if the host blocks it, stop and reply briefly.
1. Work from the clone: `cd ~/naquuuu`
2. Run the task headlessly, one task per call, preferring the warm server:
   `opencode run --attach http://127.0.0.1:4096 --dir ~/naquuuu "Read internal-docs/STATUS.md and internal-docs/LESSONS.md for context. Task: <task>. Report changed files, commands run, and evidence. Do not commit or push."`
   If the attach fails, run the same command without `--attach`/`--dir`.
   Optionally pin the agent: `opencode run --agent naquuuubot "<task>"`
3. Return the agent's final output to the owner, trimmed to the essentials. For jobs longer than a minute, prefix the reply with `job <HHMM>`.

## Prompt shape

Give opencode: the goal, file paths (never pasted content), and done-when criteria.

## Rules

- HOST GATE FIRST, ALWAYS: the bridge authenticates and the gateway blocks non-owner actions before execution. The model must not inspect or request sender IDs or run `wa_owner_gate.py`. For action requests, use the normal route; if the host blocks it, stop. Guests may chat but cannot execute actions.
- Never include secrets, phone numbers, keys, or tokens in the prompt.
- If asked in chat to allowlist a person or number, reply in one or two sentences that person admission is owner-side only and point the owner to `scripts/whatsapp_group_fix.py --allow-user` on the relay host.
- `git commit` and `git push` are gated: report changed files and tell the owner a commit needs approval.
- One task per run; no chained mega-prompts.
- M1: this host is a scoped writer (repo-scoped deploy key); commits and pushes stay gate-protected via auto-sync.
- M2 (authored, pending - not live): heavy jobs route through `scripts/dispatch_job.sh` to the worker (queue when offline); light work stays local. Not active until the worker SSH trust is authorized and the owner approves. See `internal-docs/relay/M2_DISPATCH_RUNBOOK.md`.
- If `opencode run` fails, return the error lines only.
```
