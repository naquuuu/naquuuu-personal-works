#!/usr/bin/env bash
# NAQUUUU M2 drain installer - runs ON the relay host.
#
# Usage:
#   bash scripts/install_dispatch_drain.sh
#
# Idempotent: copies drain_queue.sh to ~/.local/bin/naquuuu-drain, installs
# job_status.sh to ~/.local/bin/naquuuu-job-status, writes a commented default
# ~/.config/naquuuu/dispatch.env (only when missing), and installs (then
# enables) a systemd USER service + timer that runs the drain every 5 minutes.
# Safe to re-run.

set -u

REPO="${NAQUUUU_WORKSPACE:-${NAQUUUU_REPO:-$HOME/naquuuu}}"
BIN="$HOME/.local/bin/naquuuu-drain"
STATUS_BIN="$HOME/.local/bin/naquuuu-job-status"
UNIT_DIR="$HOME/.config/systemd/user"
SERVICE="$UNIT_DIR/naquuuu-drain.service"
TIMER="$UNIT_DIR/naquuuu-drain.timer"
ENV_DIR="$HOME/.config/naquuuu"
ENV_FILE="$ENV_DIR/dispatch.env"

if [ ! -f "$REPO/scripts/drain_queue.sh" ]; then
  echo "install_dispatch_drain: no scripts/drain_queue.sh under $REPO" >&2
  exit 1
fi

mkdir -p "$HOME/.local/bin" "$UNIT_DIR" "$ENV_DIR"
cp "$REPO/scripts/drain_queue.sh" "$BIN"
chmod +x "$BIN"

if [ -f "$REPO/scripts/job_status.sh" ]; then
  cp "$REPO/scripts/job_status.sh" "$STATUS_BIN"
  chmod +x "$STATUS_BIN"
else
  echo "install_dispatch_drain: no scripts/job_status.sh under $REPO" >&2
fi

# Commented default tunables; never overwrite an existing file.
if [ ! -f "$ENV_FILE" ]; then
  cat > "$ENV_FILE" <<'ENV'
# NAQUUUU dispatch/drain tunables. All optional; uncomment a line to override.
# Loaded by the systemd user service via EnvironmentFile and read by the scripts.
#
# NAQUUUU_WORKER_KEY=$HOME/.ssh/id_ed25519_worker
# NAQUUUU_WORKER_HOST=mipad-linux
# NAQUUUU_WORKER_USER=ubuntu
# NAQUUUU_WORKER_REPO=$HOME/naquuuu
# NAQUUUU_QUEUE_DIR=$HOME/.naquuuu/queue
# NAQUUUU_JOB_TIMEOUT=1800
# NAQUUUU_WORKER_REACH_TIMEOUT=5
# NAQUUUU_MAX_ATTEMPTS=3
# NAQUUUU_DRAIN_BATCH=1
# NAQUUUU_QUEUE_KEEP=50
# NAQUUUU_OPENCODE=opencode
ENV
  chmod 600 "$ENV_FILE"
fi

cat > "$SERVICE" <<'UNIT'
[Unit]
Description=NAQUUUU durable job queue drain (VPS to worker)

[Service]
Type=oneshot
TimeoutStartSec=1900
TimeoutStopSec=1900
EnvironmentFile=-%h/.config/naquuuu/dispatch.env
ExecStart=%h/.local/bin/naquuuu-drain
UNIT

cat > "$TIMER" <<'UNIT'
[Unit]
Description=NAQUUUU durable job queue drain timer

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
Persistent=true

[Install]
WantedBy=timers.target
UNIT

systemctl --user daemon-reload 2>/dev/null || true
systemctl --user enable --now naquuuu-drain.timer 2>/dev/null \
  || echo "timer enable needs a re-login; then re-run this script"
sudo loginctl enable-linger "$(id -un)" 2>/dev/null || true
systemctl --user list-timers naquuuu-drain.timer --no-pager 2>/dev/null | head -3 || true

echo "installed $BIN, $STATUS_BIN and enabled naquuuu-drain.timer"
