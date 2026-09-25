#!/usr/bin/env bash
# NAQUUUU home-server onboarding (Ubuntu 24.04+).
#
# Safe to re-run: every step checks before it acts. No secrets in this file.
#
# Usage on the home-server laptop:
#   curl -fsSL https://raw.githubusercontent.com/naquuuu/naquuuu-personal-works/main/scripts/provision_home_server.sh -o ~/provision_home_server.sh
#   bash ~/provision_home_server.sh

set -u

REPO_URL="https://github.com/naquuuu/naquuuu-personal-works.git"
REPO_DIR="$HOME/naquuuu"
AUTOSYNC_BIN="$HOME/.local/bin/naquuuu-autosync"

say() { printf '\n=== %s ===\n' "$1"; }

say "1/7 base packages"
sudo apt-get update -y
sudo apt-get install -y git curl xz-utils python3 openssh-server tmux ufw

say "2/7 Tailscale"
if ! command -v tailscale >/dev/null 2>&1; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi
if ! tailscale status >/dev/null 2>&1; then
  echo "Opening Tailscale login (authenticate with the same account as your other devices)..."
  sudo tailscale up
else
  tailscale status | head -3
fi
sudo ufw allow OpenSSH >/dev/null 2>&1 || true
sudo ufw allow in on tailscale0 >/dev/null 2>&1 || true
sudo ufw --force enable >/dev/null 2>&1 || true

say "3/7 always-on (never suspend)"
sudo mkdir -p /etc/systemd/logind.conf.d
printf '[Login]\nHandleLidSwitch=ignore\nHandleLidSwitchExternalPower=ignore\nHandleLidSwitchDocked=ignore\nIdleAction=ignore\n' \
  | sudo tee /etc/systemd/logind.conf.d/99-naquuuu-nosleep.conf >/dev/null
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target >/dev/null 2>&1 || true
echo "sleep targets masked; lid-close rules apply from the next boot"

say "4/7 workspace clone"
if [ ! -d "$REPO_DIR/.git" ]; then
  git clone "$REPO_URL" "$REPO_DIR"
else
  git -C "$REPO_DIR" pull --ff-only || true
fi
git -C "$REPO_DIR" config core.hooksPath .githooks

say "5/7 opencode"
if ! command -v opencode >/dev/null 2>&1 && [ ! -x "$HOME/.opencode/bin/opencode" ]; then
  curl -fsSL https://opencode.ai/install | bash
fi
sudo ln -sf "$HOME/.opencode/bin/opencode" /usr/local/bin/opencode 2>/dev/null || true
/usr/local/bin/opencode --version 2>/dev/null || echo "opencode installed (open a new shell to pick up PATH)"

say "6/7 auto-sync timer (pull + gate + commit + push every 5 min)"
mkdir -p "$HOME/.local/bin" "$HOME/.config/systemd/user"
if [ -f "$REPO_DIR/scripts/node_autosync.sh" ]; then
  cp "$REPO_DIR/scripts/node_autosync.sh" "$AUTOSYNC_BIN"
  chmod +x "$AUTOSYNC_BIN"
fi
cat > "$HOME/.config/systemd/user/naquuuu-autosync.service" <<'UNIT'
[Unit]
Description=NAQUUUU workspace auto-sync (pull, gate, commit, push)

[Service]
Type=oneshot
ExecStart=%h/.local/bin/naquuuu-autosync
UNIT
cat > "$HOME/.config/systemd/user/naquuuu-autosync.timer" <<'UNIT'
[Unit]
Description=NAQUUUU workspace auto-sync timer

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
Persistent=true

[Install]
WantedBy=timers.target
UNIT
systemctl --user daemon-reload 2>/dev/null || true
systemctl --user enable --now naquuuu-autosync.timer 2>/dev/null || echo "timer enable needs a re-login, then re-run step 6"
sudo loginctl enable-linger "$(id -un)" 2>/dev/null || true
systemctl --user list-timers naquuuu-autosync.timer --no-pager 2>/dev/null | head -3

say "7/7 this machine"
echo "host: $(hostname)"
echo "OS:   $(. /etc/os-release && echo "$PRETTY_NAME")"
echo "CPU:  $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2 | xargs)"
echo "RAM:  $(free -h | awk '/^Mem:/{print $2}') total, $(free -h | awk '/^Mem:/{print $7}') available"
echo "DISK: $(df -h / | awk 'NR==2{print $4" free of "$2}')"

cat <<'DONE'

=== done ===

Two one-time manual steps remain:
  1. opencode auth login        # choose the same provider as the VPS (opencode-go)
  2. Reboot once so the lid/always-on rules apply:
     sudo reboot

This box is now: a synced workspace replica + auto-sync node + M2 worker candidate.
DONE
