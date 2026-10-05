#!/usr/bin/env python3
"""Print a redacted, read-only health summary for the Hermes relay VPS."""
from __future__ import annotations

import os
import base64
import re
import shutil
import subprocess
import sys


REMOTE_CHECKS = r'''set +e
systemctl --user is-active hermes-gateway.service >/dev/null 2>&1 && echo gateway=active || echo gateway=inactive
systemctl --user show hermes-gateway.service -p NRestarts --value 2>/dev/null | awk '{print "gateway_restarts=" $1}'
if ss -ltnH 'sport = :3000' 2>/dev/null | grep -q .; then echo bridge_port=up; else echo bridge_port=down; fi
ss -ltnH 'sport = :9119' 2>/dev/null | awk 'BEGIN{n=0;bad=0} {n++; if ($4 !~ /^127[.]0[.]0[.]1:/) bad=1} END {if(n==0) print "dashboard_port=down"; else if(bad) print "dashboard_port=nonloopback"; else print "dashboard_port=loopback"}'
sudo -n ufw status 2>/dev/null | awk 'BEGIN{s="unknown";r="no"} /^Status:/ {s=tolower($2)} tolower($0) ~ /9119/ {r="yes"} END {print "ufw=" s; print "ufw_rule_9119=" r}'
if command -v tailscale >/dev/null 2>&1; then tailscale serve status --json 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); s=json.dumps(d).lower(); print("tailscale_serve=" + ("configured" if "9119" in s else "no_dashboard_route"))' 2>/dev/null || echo tailscale_serve=unknown; else echo tailscale_serve=unavailable; fi
journalctl --user -u hermes-gateway.service --since '24 hours ago' -n 500 --no-pager -o cat 2>/dev/null | python3 -c 'import re,sys; s=sys.stdin.read(); print("provider_503_recent="+str(len(re.findall(r"\b503\b",s)))); print("provider_429_recent="+str(len(re.findall(r"\b429\b",s)))); print("provider_timeout_recent="+str(len(re.findall(r"timeout|timed out",s,re.I))))'
for q in pending done failed; do d="$HOME/.naquuuu/queue/$q"; n=0; [ ! -d "$d" ] || n=$(find "$d" -maxdepth 1 -type f 2>/dev/null | wc -l); echo "queue_$q=$n"; done
'''


def main() -> int:
    ssh = shutil.which("ssh")
    if not ssh:
        print("RELAY_SSH=unavailable")
        return 1
    # The default Tailscale IP already has a verified SSH host key on the setup laptop.
    # Override this when the relay host's tailnet address changes.
    target = os.environ.get("NAQUUUU_RELAY_SSH_TARGET", "ubuntu@100.87.52.117")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.@-]*", target):
        print("RELAY_SSH=invalid_target")
        return 2
    try:
        result = subprocess.run(
            [
                ssh,
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=8",
                target,
                "printf %s " + base64.b64encode(REMOTE_CHECKS.encode("utf-8")).decode("ascii") + " | base64 -d | bash",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=25,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        print("RELAY_SSH=unavailable")
        return 1
    if result.returncode != 0:
        print("RELAY_SSH=unavailable")
        return 1

    allowed = re.compile(
        r"^(?:gateway=(?:active|inactive)|gateway_restarts=\d+|"
        r"bridge_port=(?:up|down)|dashboard_port=(?:down|loopback|nonloopback)|"
        r"ufw=(?:active|inactive|unknown)|ufw_rule_9119=(?:yes|no)|"
        r"tailscale_serve=(?:configured|no_dashboard_route|unknown|unavailable)|"
        r"provider_(?:503|429|timeout)_recent=\d+|queue_(?:pending|done|failed)=\d+)$"
    )
    print("RELAY_SSH=ok")
    for line in result.stdout.splitlines():
        line = line.strip()
        if allowed.fullmatch(line):
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
