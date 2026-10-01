# Thin Relay (Phase 3B) - WhatsApp to opencode

## What it is
A Hermes local skill that routes workspace engineering tasks from WhatsApp to the opencode orchestrator (naquuuubot) and returns the result to the chat.

The v2 skill also answers questions: for status, plan, or history questions it reads `internal-docs/STATUS.md` and searches the workspace docs before answering, so replies come from the repository rather than the agent's memory.

Flow: WhatsApp -> Hermes (skill: opencode-relay) -> `opencode run "<task>"` -> naquuuubot -> reply.

## Install path
The live skill is installed at:
`%LOCALAPPDATA%\hermes\skills\relay\opencode-relay\SKILL.md`

This repository keeps the canonical copy below; re-copy it to the install path after edits.

## VPS relay (Linux, live)
Live host: Tencent Cloud Lighthouse 2 vCPU / 2 GB / 40 GB, Singapore, Ubuntu 24.04 LTS. The VPS is the live relay host (M1 complete 2026-09-25, ADR-026): Hermes gateway (systemd user service, linger enabled) + WhatsApp bridge (bot mode) + opencode 1.18.32 (`opencode-go` auth) + workspace clone at `~/naquuuu`. The WhatsApp session was copied from the laptop; a repo-scoped ed25519 deploy key makes the VPS a scoped writer. The laptop's gateway is stopped and its session copy is retained as rollback. The canonical Linux skill copy, the full provisioning steps, and the as-executed gotchas live in `internal-docs/relay/VPS_RELAY_RUNBOOK.md`; the Windows skill below remains canonical for the laptop.

The WhatsApp persona is canonical at `internal-docs/relay/WHATSAPP_SOUL.md` (mirrored to `~/.hermes/SOUL.md` on the host; ADR-027). VPS Linux relay skill source: `internal-docs/relay/OPENCODE_RELAY_SKILL.md`; it reuses the existing authenticated loopback `opencode serve` instance.

M2 is approved and partially staged: the drain timer is installed and enabled, but worker SSH trust and real worker execution have not passed. The relay skill remains local for both light and heavy jobs until the dedicated key authenticates and archive verification succeeds. Offline jobs are retained and summarized, with no automatic WhatsApp reply. Runbook: `internal-docs/relay/M2_DISPATCH_RUNBOOK.md`.

- Optimization and media plan (latency, context reuse, images): `internal-docs/relay/RELAY_PLAN.md`.
- Heavy jobs route through dispatch (M2, authored, pending - not live): `internal-docs/relay/M2_DISPATCH_RUNBOOK.md`.

## Skill content

```markdown
---
name: opencode-relay
description: "Route NAQUUUU workspace questions and engineering tasks from WhatsApp to the local opencode orchestrator (naquuuubot) and return the result."
version: 2.0.0
author: naquuuu
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [relay, opencode, workspace, engineering, orchestration, status]
prerequisites:
  commands: [opencode]
---

# OpenCode Relay

Use this skill for anything about the NAQUUUU workspace: status questions, plan or history questions, and engineering work.

## 1. Questions about status, plans, or history

Answer from the repository, never from memory:

1. Read `C:\personal\naquuuu\internal-docs\STATUS.md` first (current state digest).
2. For details, search `internal-docs\` (DECISION_LOG.md, HOSTS.md, specs/, research/) and `git log` in `C:\personal\naquuuu`.
3. Answer with the source path(s). If the workspace does not answer it, say "not in the workspace" explicitly.

## 2. Engineering tasks (development)

0. OWNER GATE: the Hermes host authenticates bridge-provided sender identity before any tool middleware or dispatch. Never pass a sender ID from model context or run `wa_owner_gate.py --sender` from chat. Missing identity/config denies tools; guests remain chat-only.
1. Work from the hub: `cd /c/personal/naquuuu`
2. Run the task headlessly, one task per call:
   `opencode run "Read internal-docs/STATUS.md for context. Task: <task>. Report changed files, commands run, and evidence. Do not commit or push."`
   Optionally pin the agent: `opencode run --agent naquuuubot "<task>"`
3. Return the agent's final output to the owner, trimmed to the essentials. For jobs longer than a minute, prefix the reply with `job <HHMM>`.

## Prompt shape

Give opencode: the goal, file paths (never pasted content), and done-when criteria.

## Rules

- OWNER GATE: host code enforces owner authorization before tools, including tool hooks and background execution. Do not provide sender IDs or invoke a model-supplied identity check. Any unknown identity or configuration error is denied.
- HOST-ONLY ACTIONS: person/group admission/promotion scripts (`wa_owner_gate.py`, `wa_group_allow.py`, `whatsapp_group_fix.py`, `wa_free_response.py`, `install_wa_owner_auth.py`, `install_wa_chat_policy.py`), `.env` edits, `.hermes/` state changes, and Hermes service control are host-shell-only (even when owner-AUTHORIZED); never run them from a WhatsApp turn and never pass them to opencode run either. The host tool gate blocks obvious forms in Hermes tool arguments (best-effort tripwire, ADR-035); it cannot see what a child `opencode run` does, so this rule still binds the agent.
- Never include secrets, phone numbers, keys, or tokens in the prompt.
- The relay runs opencode with the config default model `opencode-go/deepseek-v4.1-flash` (from `opencode.jsonc`); or pass `--model opencode-go/deepseek-v4.1-flash` explicitly.
- If asked in chat to allowlist a person or number, reply in one or two sentences that person admission is owner-side only and point the owner to `scripts/whatsapp_group_fix.py --allow-user` on the relay host.
- `git commit` and `git push` are gated: report changed files and tell the owner a commit needs approval.
- One task per run; no chained mega-prompts.
- M2 heavy jobs (authored, pending - not live): this skill does not dispatch yet; once the worker SSH trust is authorized on the relay host, heavy dev work routes through `scripts/dispatch_job.sh` (queue when the worker is offline). A queued job is not auto-replied: its output is archived under `done/` and summarized by `naquuuu-job-status`. See `internal-docs/relay/M2_DISPATCH_RUNBOOK.md`.
- For AGY authoring work, write a brief to `internal-docs/briefs/` and tell the owner to run it in AGY. AGY stays human-operated; never invoke the `agy` CLI.
- If `opencode run` fails, return the error lines only.
```

## Evidence
- CLI validation: `opencode run "<task>"` from Git Bash executed in the hub and returned branch + dirty count (exit 0).
- WhatsApp end-to-end: owner asked Hermes to "Ask opencode to report the hub's branch and latest commit" -> reply reported branch `main`, latest commit `9a97df7`, message `fix: registry-safe AGY tool list (code_search removed)`.
- v2.0.0 (2026-09-23): adds repository-grounded question answering (`internal-docs/STATUS.md` plus docs and `git log` search) so WhatsApp answers come from the repository, not from the agent's memory; development tasks now carry a STATUS.md context header.
- 2026-09-24: group replies verified live in a private test group; `scripts/host_check.py` READY (5 PASS / 1 WARN / 0 FAIL, the WARN being the dirty hub tree during edits).

## Group chats (bot mode)
Hermes defaults to `WHATSAPP_GROUP_POLICY=pairing`, which forwards nothing from groups. The relay uses a per-group allowlist:

- Policy: `WHATSAPP_GROUP_POLICY=allowlist` with `WHATSAPP_GROUP_ALLOWED_USERS=<group JID>@g.us`.
- Mention gate: `WHATSAPP_REQUIRE_MENTION=true` (replies only to @mentions, replies to the bot, or `/commands`).
- `open` is refused by the installed Hermes v0.21.4 unless `WHATSAPP_ALLOW_ALL_USERS` is enabled (safe-mode rail); allow-all is intentionally not used.
- Sender gating stays on `WHATSAPP_ALLOWED_USERS` (owner plus one guest; values live only in the host env).
- Helper: `scripts/whatsapp_group_fix.py` applies the policy idempotently with a timestamped `.env` backup and falls back to `hermes gateway start` when `hermes gateway restart` reports a service-manager failure on this VBS-only Windows install.
- On the relay host, group intake is managed as a command, not a config edit (ADR-028): `scripts/wa_group_allow.py --list | --add-latest | --add <JID> | --remove <JID>` edits the allowlist with a timestamped backup and never prints JID values, only counts.
- Ops note: a stale WhatsApp bridge process from a previous run can hold port 3000 and must be cleared before restart.

### Two gates (group vs person)
Group admission and person admission are independent: allowlisting a group does not put its members on the person allowlist. Free-response (below) is a separate, per-chat speaking permission, not a person admission.

- Group gate: `WHATSAPP_GROUP_POLICY=allowlist` + `WHATSAPP_GROUP_ALLOWED_USERS`, managed by `scripts/wa_group_allow.py`.
- Person gate: `WHATSAPP_ALLOWED_USERS` (owner-side only). A non-allowlisted member is silently dropped even inside an allowlisted group, except in a free-response group where the sender allowlist is bypassed for that chat (see `Group presence (Mode 2)`).
- No chat command: person admission never runs from WhatsApp; phone numbers are Tier 1 and must not enter model context (AGENTS.md Model-Input Boundary; ADR-027 §2, ADR-028 §5). The relay never prints numbers, IDs, or JIDs.
- Owner-side add on the relay host, one number per invocation, full international digits with no `+`: `python3 scripts/whatsapp_group_fix.py --allow-user <digits>` (backs up `~/.hermes/.env`, appends to `WHATSAPP_ALLOWED_USERS`, restarts).
- Verify: `python3 scripts/whatsapp_group_fix.py --dry-run`; `python3 scripts/wa_group_allow.py --list`; `hermes gateway status`.
- Fallback: edit `WHATSAPP_ALLOWED_USERS` in `~/.hermes/.env`, then `systemctl --user restart hermes-gateway.service`.
- Never `WHATSAPP_ALLOWED_USERS=*` or `WHATSAPP_ALLOW_ALL_USERS` (rejected as unsafe, ADR-024): add named people, never the whole room. Allowlist membership grants speaking, not operating; the host-side tool gate grants execution only to a verified owner.

## Group presence (Mode 2)

Group behaviour is decided per chat, and two decisions stay separate: who may **speak** to the bot, and who may make it **act**.

**Speaking — free-response per group.** A chat id listed in `WHATSAPP_FREE_RESPONSE_CHATS` is free-response: anyone in that group can message the bot with no @mention, and for that chat the per-sender allowlist (`WHATSAPP_ALLOWED_USERS`) is bypassed. That bypass is deliberate and owner-set: a guest who was never allowlisted as a person can still hold a conversation in that group. Every other group stays mention-only — the bot answers only on an @mention, a reply to it, a slash command, or its name (`mention_patterns`), under `WHATSAPP_REQUIRE_MENTION=true`. A newly allowlisted group is mention-only until the owner promotes it.

**Acting — owner-only.** A speaker is not an operator. The Hermes host binds a trusted owner decision to each WhatsApp turn and blocks tool middleware/dispatch for guests and unknown senders. The model never supplies sender IDs or performs authorization. Missing identity/configuration denies execution; guests can still chat.

**Silence.** The gateway accepts `NO_REPLY`, so when nothing is worth saying the assistant emits `NO_REPLY` and sends no message.

**No thread awareness.** On the installed Hermes v0.21.4 there is no observation or thread awareness for WhatsApp (upstream support is Telegram-only), so the relay is stateless per turn: no stored group chatter, no message-history context, nothing carried between turns. Each turn sees only the chat text of the triggering message. Never promise a group member that the bot read the room.

- Promotion is host-side and owner-run: `scripts/wa_free_response.py` edits `WHATSAPP_FREE_RESPONSE_CHATS` idempotently, with a timestamped backup, and prints counts only — never chat ids.
- Group admission stays a separate owner-run command: `scripts/wa_group_allow.py --list | --add-latest | --add <CHATID> | --remove <CHATID>` manages `WHATSAPP_GROUP_ALLOWED_USERS`.
- Model pin: the relay runs opencode with the config default model `opencode-go/deepseek-v4.1-flash` (from `opencode.jsonc`); pass `--model opencode-go/deepseek-v4.1-flash` only to override explicitly.
- Persona/display change: the `WHATSAPP_SOUL.md` group-presence text lands on both the repo copy and `~/.hermes/SOUL.md` on the relay host (mirror rule, ADR-027).
- Safety note: free-response is scoped to the listed chats and is **not** `WHATSAPP_ALLOW_ALL_USERS`; allow-all stays refused and unused (ADR-024). Free-response widens who may speak, never who may execute — Hermes enforces the execution boundary before tool middleware.

## Deferred
- Job IDs are informal (`job <HHMM>`); per-job approvals were superseded by ADR-016 (autonomous execution). A durable queue returns with M2 worker dispatch (ADR-029, authored and pending), not a per-job approval gate.
- New Hermes skills may require a gateway restart to be discovered.
