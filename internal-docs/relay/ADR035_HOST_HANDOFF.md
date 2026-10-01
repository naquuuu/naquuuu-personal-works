# ADR-035 Host Handoff Prompt

Purpose: a self-contained prompt for a local agent (written for `gpt-6.1-sol`, works with any model) to finish the Hermes WhatsApp owner-auth / host-only-guard rollout on the relay host. Tier 2 only: it contains no identifiers, secrets, or host addresses. Paste everything inside the fence as the first message.

````text
[HUB] Finish the Hermes WhatsApp ADR-035 rollout on the relay host.

You are naquuuubot (see AGENTS.md in the hub). Work from the hub checkout on this machine. Read these first, in order:
- AGENTS.md (Sections 3 and 7.9)
- internal-docs/DECISION_LOG.md, ADR-035 (last entry)
- internal-docs/relay/VPS_RELAY_RUNBOOK.md "Step 6.5 — Deploy sync"
- internal-docs/relay/WHATSAPP_SOUL.md

Code state: branch `claude/hermes-whatsapp-owner-auth-modywq`, head 1e63b61 (on top of 5a5e838, based on origin/main 1f7e11f). Verify with `git fetch origin && git log --oneline -3 origin/claude/hermes-whatsapp-owner-auth-modywq`. It is NOT merged to main.

## Hard rules
1. Privacy: never print, store, or paste phone numbers, WhatsApp IDs/JIDs/LIDs, session tokens, API keys, message text, or private config contents. Report counts and booleans only. If a command's output could contain any of these, pipe it through `wc -l`, `grep -c`, or a yes/no test instead.
2. Never read the hub `.env` or Hermes state (`~/.hermes/.env`, `config.yaml`, sessions, state databases, logs) unless the owner authorizes it in this chat, naming what and until when. Reading code in the pinned checkout `~/.hermes/hermes-agent` (not its data) is allowed.
3. Never trust ownership from WhatsApp `fromMe`/`fromOwner` metadata. Ownership comes only from the bridge's strict flag (ADR-035 item 1).
4. On the VPS, always use `~/.hermes/hermes-agent/venv/bin/python` and `~/.hermes/hermes-agent/venv/bin/hermes`, never system `python3` or the PATH `hermes` (it is broken: "No module named 'dotenv'").
5. Never restart `hermes-gateway.service` blindly: confirm `session_turn_leases` = 0 first.
6. Never reset, clean, stash, rebase, or force-push. Stage only the files you changed. Run `python scripts/verify_sanitization.py` before every commit.
7. Ask the owner before each outward or persistent action (push, VPS write, config change, restart, merge). One question per action, with the exact command.

## VPS access
`ssh ubuntu@<tailscale-host>` over Tailscale only (the owner gives you the host name; never write it to a file). Workspace `~/naquuuu`, Hermes checkout `~/.hermes/hermes-agent` pinned at ecacf3d0c967222f34d15bc58852a85f2c33880c. Service: `systemctl --user <verb> hermes-gateway.service`. If the VPS is unreachable, say so and stop the VPS items.

## Tasks (in order; ask before each persistent step)
1. Local check. On the branch, run:
   `cd scripts && python -m unittest test_install_wa_owner_auth test_refresh_wa_prompt_snapshot test_sync_wa_owner_auth_prompt test_wa_owner_prompt_contract test_wa_owner_auth_runtime test_wa_chat_policy test_install_wa_chat_policy`
   Expect 49 tests OK, 1 skipped (runtime fixture). Then `python scripts/verify_sanitization.py`.
2. Branch on the VPS. Ask the owner: merge the branch to main first, or check out the branch in `~/naquuuu`? Auto-sync timers commit from that clone, so confirm the clone is clean before switching (`git status --short | wc -l` must be 0). Then `git pull`.
3. Deploy (runbook Step 6.5), with owner approval:
   a. `~/.hermes/hermes-agent/venv/bin/python scripts/install_wa_owner_auth.py --hermes-repo ~/.hermes/hermes-agent`
   b. Same command with `--check`. It must print `owner-auth patches are fully installed on the pinned source`. If it raises "Pinned source anchor mismatch" or "Partial ... patch", STOP and report; do not hand-edit Hermes files.
   c. `cp ~/naquuuu/internal-docs/relay/WHATSAPP_SOUL.md ~/.hermes/SOUL.md` (copying TO state is allowed; do not read the old file's contents, just compare with `cmp -s` and report same/different).
   d. Confirm `session_turn_leases` = 0. If you do not know how to read it, find where Hermes defines it with `grep -rn session_turn_leases ~/.hermes/hermes-agent --include=*.py | head` (source only), then ask the owner to authorize a count-only read. Record the exact read command in runbook Step 6.5 item 5, replacing "not yet recorded".
   e. `systemctl --user restart hermes-gateway.service`, then `systemctl --user is-active hermes-gateway.service`.
4. Live checks (the owner sends the messages; you report only pass/fail):
   - Owner asks for `pwd` in chat. Expect: the tool runs. 0 gate denials.
   - Owner asks the bot to run `whatsapp_group_fix.py --dry-run`. Expect: a one-sentence "host-shell job" reply, nothing executed.
   - Owner sends one photo asking what it shows. Expect: a normal description. If the reply says the action is host-only, the media-cache exemption in `scripts/wa_turn_auth.py` (`_HERMES_MEDIA_CACHE`) does not match where Hermes stores attachments. Find the real cache directory name from Hermes source (not state), add it to the exemption plus a test, rerun step 1, and ask before committing.
   - A guest message in an admitted group: chat reply only, no tool.
5. Item F: restore `approvals.destructive_slash_confirm` to `true`. The owner already approved this. Prefer `~/.hermes/hermes-agent/venv/bin/hermes config set approvals.destructive_slash_confirm true` run in the host shell; take a timestamped backup of `config.yaml` first (`cp` only, no reading). If `hermes config set` is not a valid subcommand on this pinned version (check `hermes config --help`), give the owner the one-line manual edit instead of editing state yourself. Verify with a count-only check (e.g. `grep -c 'destructive_slash_confirm: true'`). Restart per step 3d-3e only if Hermes requires it.
6. Item D: fix the PATH `hermes` launcher. Diagnose with `head -1 ~/.local/bin/hermes` (shebang only) and `ls -l ~/.local/bin/hermes`. Proposed fix (ask first): point it at the venv, e.g. `ln -sf ~/.hermes/hermes-agent/venv/bin/hermes ~/.local/bin/hermes`. Verify `hermes --version` works from a fresh login shell. Then `crontab -l | grep -c hermes` and `systemctl --user list-timers` to report how many jobs call `hermes`.
7. Item G: VPS drift of `scripts/wa_chat_policy.py`. Origin's copy is canonical. On the VPS: `git diff --stat -- scripts/wa_chat_policy.py`. If it differs, show the code diff (code is Tier 2; redact any literal digits or IDs) and ask the owner whether to keep or discard each hunk. Never discard without approval.
8. Item C (owner-only, no chat): new groups are added by JID by the owner from the host shell: `~/.hermes/hermes-agent/venv/bin/python scripts/whatsapp_group_fix.py --group <jid>`. You never type, see, or echo a JID. Just tell the owner the command and report the script's numbered status lines afterwards.

## Done when
Each task above has a four-block report:
### Result
### Files Changed
### Evidence   (commands run + counts/booleans only)
### Blockers
Nothing may claim success without a verified run. Log any new architectural decision as the next free ADR (read DECISION_LOG.md immediately before appending) and bump the `verified-against` stamps in STATUS.md and LESSONS.md in the same commit.
````
