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

The WhatsApp persona is canonical at `internal-docs/relay/WHATSAPP_SOUL.md` (mirrored to `~/.hermes/SOUL.md` on the host; ADR-027).

- Optimization and media plan (latency, context reuse, images): `internal-docs/relay/RELAY_PLAN.md`.

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

1. Work from the hub: `cd /c/personal/naquuuu`
2. Run the task headlessly, one task per call:
   `opencode run "Read internal-docs/STATUS.md for context. Task: <task>. Report changed files, commands run, and evidence. Do not commit or push."`
   Optionally pin the agent: `opencode run --agent naquuuubot "<task>"`
3. Return the agent's final output to the owner, trimmed to the essentials. For jobs longer than a minute, prefix the reply with `job <HHMM>`.

## Prompt shape

Give opencode: the goal, file paths (never pasted content), and done-when criteria.

## Rules

- Never include secrets, phone numbers, keys, or tokens in the prompt.
- `git commit` and `git push` are gated: report changed files and tell the owner a commit needs approval.
- One task per run; no chained mega-prompts.
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
- Ops note: a stale WhatsApp bridge process from a previous run can hold port 3000 and must be cleared before restart.

## Deferred
- Job IDs are informal (`job <HHMM>`); a durable queue and per-job approvals were superseded by ADR-016 (autonomous execution) and can be revisited if needed.
- New Hermes skills may require a gateway restart to be discovered.
