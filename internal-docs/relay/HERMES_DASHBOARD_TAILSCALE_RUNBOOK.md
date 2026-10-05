# Hermes Dashboard on Tailscale

Purpose: make Hermes Dashboard available to authorized tailnet devices while its backend listens only on `127.0.0.1:9119`. Do not open a public port, configure Funnel, add a public reverse proxy, or rewrite `Host` / `Origin` headers.

## Preflight snapshot — 2026-09-30

Read-only checks from the owner's existing SSH access found:

- Hermes CLI reports `Hermes Agent v0.21.4`, build string `upstream 952c941e`; the previously recorded checkout revision is `ecacf3d0c9`. Treat this version/build/checkout mismatch as a deployment-drift item; do not update Hermes to reconcile it.
- Gateway is active; no dashboard systemd unit or dashboard process is running.
- Nothing listens on port 9119. Caddy and Nginx are absent/inactive. UFW is active with no rule mentioning 9119.
- Tailscale is installed and connected. The previous Serve configuration is empty; no Funnel configuration was reported.
- This check did not inspect the cloud provider firewall. A loopback-only listener and no Funnel remain required regardless.

Before changes, confirm these facts from the live host again. Do not print env-file values or raw service logs.

## Current rollout — 2026-09-30

- Owner configured Basic Auth through the interactive script; `.env` is mode 0600 and the previous file was backed up on the VPS.
- `hermes-dashboard.service` is enabled and active. Local checks confirm a loopback listener, `/api/status` reports `auth_required: true`, and unauthenticated `/api/config` returns 401.
- Tailscale Serve is active at `https://hermes-vps.tail317e88.ts.net/` and proxies to `http://127.0.0.1:9119`. HTTPS checks from the VPS over the tailnet returned `auth_required: true` and unauthenticated `/api/config` returned 401.
- UFW has no 9119 rule. Serve status reports the route as tailnet-only; Funnel has no route. Owner-device login and off-tailnet reachability checks remain.

## Auth setup script

Run on the VPS as the Hermes user with Hermes' venv Python:

```bash
~/.hermes/hermes-agent/venv/bin/python ~/naquuuu/scripts/configure_hermes_dashboard_auth.py
```

The script prompts for a username and prompts twice for the password without echoing it. It requires at least 12 characters, imports `hermes_bootstrap` before the Hermes Basic Auth helper, creates the hash and a random 32-byte hex signing secret, updates only the three dashboard auth keys in `~/.hermes/.env`, saves a mode-0600 backup, and enforces mode 0600 on the updated file. It never prints credential values. Do not put a password in a command, chat, shell history, or this repository.

## Service and Tailscale Serve

The verified gateway launcher is the Hermes venv Python running `-m hermes_cli.main gateway run`. Dashboard service uses the same interpreter and shared Hermes environment, while omitting gateway-only settings:

```ini
[Unit]
Description=Hermes Agent Dashboard
After=network.target

[Service]
Type=simple
WorkingDirectory=%h/.hermes/hermes-agent
Environment=HERMES_HOME=%h/.hermes
Environment=HERMES_AGENT_NOTIFY_INTERVAL=60
Environment=NAQUUUU_WORKSPACE=%h/naquuuu
EnvironmentFile=%h/.hermes/.env
ExecStart=%h/.hermes/hermes-agent/venv/bin/python -m hermes_cli.main dashboard --host 127.0.0.1 --port 9119 --no-open
Restart=always
RestartSec=5
RestartPreventExitStatus=78

[Install]
WantedBy=default.target
```

Install the checked-in `internal-docs/relay/hermes-dashboard.service` as `~/.config/systemd/user/hermes-dashboard.service`, then run `systemctl --user daemon-reload`, `enable --now hermes-dashboard.service`, and verify the only 9119 listener is `127.0.0.1:9119`. Check for an existing dashboard process before starting; stop it only after the new service is healthy. Enable user linger only if it is not already enabled.

Use the Tailscale hostname `hermes-vps` and set the exact HTTPS MagicDNS name shown by `tailscale status`:

```bash
hermes config set dashboard.public_url https://hermes-vps.<tailnet>.ts.net
sudo tailscale serve --bg 9119
tailscale serve status
```

Tailscale was already installed and connected at preflight, so do not rerun its installer or `tailscale up` without a concrete need. `tailscale set --hostname=hermes-vps` is sufficient for renaming an already connected node. If Serve asks for tailnet HTTPS/Serve enablement, provide its approval link to the owner and continue once enabled. Keep Funnel disabled. Tailscale Serve preserves incoming Host and Origin; do not add header rewriting.

## Acceptance checks

- `systemctl --user is-active hermes-dashboard.service` is `active`; gateway remains active.
- `ss -ltn` shows port 9119 only on `127.0.0.1`; no firewall rule opens 9119; Caddy/Nginx remain absent or inactive; `tailscale serve status` shows the HTTPS tailnet route and no Funnel exposure.
- From an authenticated tailnet device, `/api/status` reports `auth_required: true`; unauthenticated `/api/config` returns 401; authenticated dashboard access works.
- From a device outside the tailnet, the dashboard URL and VPS public address cannot reach the dashboard.
- Never include the password, password hash, signing secret, `.env` contents, session cookie, or authenticated config response in logs or handoff.

## Read-only relay health summary

From the hub, run `python scripts/relay_vps_status.py`. It uses strict, batch SSH and prints only service/port state, aggregate provider error counts from a bounded recent journal window, firewall rule presence, and queue counts. It never returns raw journal lines or chat content. If the relay Tailscale address changes, set `NAQUUUU_RELAY_SSH_TARGET` to the verified SSH target; do not disable host-key checking.

Hermes references: [Web Dashboard](https://hermes-agent.nousresearch.com/docs/user-guide/features/web-dashboard), [CLI commands](https://hermes-agent.nousresearch.com/docs/reference/cli-commands/). Tailscale references: [Serve](https://tailscale.com/docs/features/tailscale-serve), [Serve CLI](https://tailscale.com/docs/reference/tailscale-cli/serve), [Serve vs Funnel](https://tailscale.com/docs/reference/tailscale-cli/funnel).
