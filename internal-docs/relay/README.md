# Thin Relay (Phase 3B) - WhatsApp to opencode

## What it is
A Hermes local skill that routes workspace engineering tasks from WhatsApp to the opencode orchestrator (naquuuubot) and returns the result to the chat.

Flow: WhatsApp -> Hermes (skill: opencode-relay) -> `opencode run "<task>"` -> naquuuubot -> reply.

## Install path
The live skill is installed at:
`%LOCALAPPDATA%\hermes\skills\relay\opencode-relay\SKILL.md`

This repository keeps the canonical copy below; re-copy it to the install path after edits.

## Skill content

```markdown
---
name: opencode-relay
description: "Route NAQUUUU workspace engineering tasks from WhatsApp to the opencode orchestrator (naquuuubot) and return its result."
version: 1.0.0
author: naquuuu
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [relay, opencode, workspace, engineering, orchestration]
prerequisites:
  commands: [opencode]
---

# OpenCode Relay

Route engineering work in the NAQUUUU workspace to the opencode orchestrator instead of doing it in this chat. Use this whenever the owner asks for work that touches the workspace: inspect repos, run gates, build or fix code, write files, or prepare briefs.

## How

1. Work from the hub:
   `cd /c/personal/naquuuu`
2. Run the task headlessly, one task per call:
   `opencode run "<task>"`
   Optionally pin the agent: `opencode run --agent naquuuubot "<task>"`
3. Return the agent's final output to the owner, trimmed to the essentials. For jobs longer than a minute, prefix the reply with `job <HHMM>`.

## Prompt shape

Give opencode: the goal, file paths (never pasted content), and done-when criteria.

## Rules

- Never include secrets, phone numbers, keys, or tokens in the prompt.
- `git commit` and `git push` are gated: if the task needs a commit, report the changed files and tell the owner a commit needs approval.
- One task per run; no chained mega-prompts.
- For AGY authoring work, write a brief to `internal-docs/briefs/` and tell the owner to run it in AGY. AGY stays human-operated; never invoke the `agy` CLI.
- If `opencode run` fails, return the error lines only.
```

## Evidence (2026-09-23)
- CLI validation: `opencode run "<task>"` from Git Bash executed in the hub and returned branch + dirty count (exit 0).
- WhatsApp end-to-end: owner asked Hermes to "Ask opencode to report the hub's branch and latest commit" -> reply reported branch `main`, latest commit `9a97df7`, message `fix: registry-safe AGY tool list (code_search removed)`.

## Deferred
- Job IDs are informal (`job <HHMM>`); a durable queue and per-job approvals were superseded by ADR-016 (autonomous execution) and can be revisited if needed.
- New Hermes skills may require a gateway restart to be discovered.
