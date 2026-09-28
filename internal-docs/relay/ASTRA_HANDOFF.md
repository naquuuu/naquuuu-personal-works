# Astra Handoff — WhatsApp relay, one-shot fix

Date: 2026-09-28. Read this file first, then act. Everything below was verified on the live
host (VM-0-8-ubuntu, Ubuntu 24.04, 2 vCPU / 2 GB) during a full-day recovery. Do not re-derive it.

## Goal

One thing: get the gateway's WhatsApp adapter to complete a connect, then confirm a message
round-trip. Everything else is already fixed and verified.

## Verified state

- Code: `~/.hermes/hermes-agent` at `ecacf3d0c9` (Hermes Agent v0.21.4). Detached HEAD.
  Reverted from `952c941e` after an update broke the env. Do NOT update, pull, fetch,
  or checkout.
- Env: `~/.hermes/hermes-agent/venv/` rebuilt. `venv/bin/python -c "import yaml"` returns OK.
- Service: `hermes-gateway.service`, two drop-ins in
  `~/.config/systemd/user/hermes-gateway.service.d/`:
  - `restart.conf`: `Restart=on-failure`, `RestartSec=30`, `StartLimitIntervalSec=300`,
    `StartLimitBurst=5`
  - `override.conf`: `ExecStart` ONLY (`venv/bin/python -m hermes_cli.main gateway run`).
    PATH is inherited so bundled Node stays visible. A previous revision hid Node and
    broke the bridge — do not re-add a PATH line.
- Session: freshly paired. Creds at `~/.hermes/whatsapp/session/`. (An earlier `no creds`
  check read the wrong directory — `~/.hermes/platforms/whatsapp/session/` — ignore it.)
- Bridge: binds `127.0.0.1:3000`, reports "WhatsApp connected!", queues messages.
  Verified multiple times in `~/.hermes/whatsapp/bridge.log`.
- Allowlist: `WHATSAPP_ALLOWED_USERS` and `NAQUUUU_WA_OWNER_IDS` set in `~/.hermes/.env`.
  Timestamped `.env.bak-*` files beside it. Grep counts, never values.
- Hotfixes (lost on any update — do not update):
  1. `adapter.py:423` — `for attempt in range(15)` became `range(90)`. Backup at
     `adapter.py.bak`. The failure string still says "15s" — message text only, ignore it.
  2. Env override `HERMES_GATEWAY_PLATFORM_CONNECT_TIMEOUT` (read by
     `_platform_connect_timeout_secs`, `gateway/run_adapters.py:145-162`). If visible,
     it wins over the 30s default.

## The single unproven step

No connect attempt has ever run with the 180 visible. Every shell tested printed UNSET for
`${HERMES_GATEWAY_PLATFORM_CONNECT_TIMEOUT:-UNSET}`, so every timeout seen so far was the
30-second default.

Prove it sticks, then launch:

```bash
export HERMES_GATEWAY_PLATFORM_CONNECT_TIMEOUT=180
# confirm: the echo below must print 180, not UNSET
echo "${HERMES_GATEWAY_PLATFORM_CONNECT_TIMEOUT:-UNSET}"
~/.hermes/hermes-agent/venv/bin/hermes gateway run
```

Then the owner sends a test message while watching the terminal. Outcomes:

- Connects and replies: done.
- Times out "after 180s": the session is stale — re-pair with
  `~/.hermes/hermes-agent/venv/bin/hermes whatsapp` (answer Y to clear, N to
  allowed-users, scan, restart the service).
- Times out "after 30s": the variable still isn't reaching the process — debug that,
  not the relay.

To make it permanent once proven, append to `override.conf`:

```ini
Environment="HERMES_GATEWAY_PLATFORM_CONNECT_TIMEOUT=180"
```

then `daemon-reload` and restart.

## What was tried and ruled out

- `hermes pm repair`, `hermes update`, `uv sync` (parent and `pm/`) — all fail on
  `uv.lock ... --locked was provided`. The `pm/uv.lock` is already correct (uv proved it);
  the failure is inside the wrapper.
- `hermes pm install` — does not exist in v0.21.4. Dead end.
- bare `hermes` — resolves to `.hermes/bin/hermes`, an isolated-mode (`-I`) shim with no
  packages. Always use the full `venv/bin/hermes` path.
- A duplicate gateway held the host lock for hours; every fresh start was a 767ms no-op
  (exit 75) until it was killed. Always clear strays first:
  `ss -tln | grep 3000`, `pgrep -af bridge`, `systemctl --user is-active`.

## Rules

- Tier 1 NEVER enters context: no phone numbers, JIDs, QR images, API keys, session IDs.
  `bridge.log` prints the allowed number in its header — redact before reading.
- Never: `hermes update`, `hermes gateway install`, bare `hermes`, systemctl edits beyond
  start/stop/reset, or a second gateway on the same host.
- One gateway per host. Clear strays before starting (commands above).
- On success, record the outcome against `L-18`/`L-19` in `internal-docs/LESSONS.md`
  (check IDs for collisions first — two writers shared that file today).

## Freshness

Verified against ADR-033. Related: ADR-026 (M1 relay), ADR-031 (group presence),
ADR-033 (read contract this file follows).
