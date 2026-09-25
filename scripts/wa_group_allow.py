#!/usr/bin/env python3
"""Manage the WhatsApp group allowlist from the relay host (owner-driven).

Usage:
    python3 scripts/wa_group_allow.py --list
    python3 scripts/wa_group_allow.py --add-latest
    python3 scripts/wa_group_allow.py --add 120363000000000000@g.us
    python3 scripts/wa_group_allow.py --remove 120363000000000000@g.us

Edits WHATSAPP_GROUP_ALLOWED_USERS in ~/.hermes/.env (timestamped backup before
any write) and schedules a gateway restart ~20 s later so the current reply can
finish. Never prints JID values; only counts. Stdlib only.
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys

ENV_PATH = os.path.join(os.path.expanduser("~"), ".hermes", ".env")
BRIDGE_LOG = os.path.join(os.path.expanduser("~"), ".hermes", "whatsapp", "bridge.log")
KEY = "WHATSAPP_GROUP_ALLOWED_USERS"
JID_RE = re.compile(r"([0-9]{5,25}@g\.us)")
KEY_RE = re.compile(rf"^(?:export\s+)?{KEY}\s*=\s*(.*)$", re.IGNORECASE)


def read_env() -> str:
    with open(ENV_PATH, encoding="utf-8", errors="replace") as handle:
        return handle.read()


def parse(text: str) -> tuple[list[str], list[str]]:
    """Return (entries, lines) with a single canonical allowlist line."""
    entries: list[str] = []
    lines: list[str] = []
    seen_key = False
    for line in text.splitlines():
        match = KEY_RE.match(line.strip())
        if match:
            if seen_key:
                continue
            seen_key = True
            entries = [part.strip() for part in match.group(1).split(",") if part.strip()]
            lines.append(f"{KEY}={','.join(entries)}")
            continue
        lines.append(line)
    if not seen_key:
        lines.append(f"{KEY}=")
    return entries, lines


def write_env(entries: list[str], lines: list[str]) -> str:
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = f"{ENV_PATH}.bak-{stamp}"
    shutil.copy2(ENV_PATH, backup)
    rebuilt = [f"{KEY}={','.join(entries)}" if KEY_RE.match(line.strip()) else line for line in lines]
    with open(ENV_PATH, "w", encoding="utf-8") as handle:
        handle.write("\n".join(rebuilt) + "\n")
    return backup


def latest_group_jid() -> str | None:
    try:
        with open(BRIDGE_LOG, encoding="utf-8", errors="replace") as handle:
            matches = JID_RE.findall(handle.read())
    except OSError:
        return None
    return matches[-1] if matches else None


def schedule_restart(delay: int = 20) -> None:
    subprocess.Popen(
        ["bash", "-lc", f"sleep {delay}; systemctl --user restart hermes-gateway.service"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage the WhatsApp group allowlist.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="show how many groups are allowlisted")
    group.add_argument("--add-latest", action="store_true", help="allowlist the most recent group seen in the bridge log")
    group.add_argument("--add", metavar="JID", help="allowlist a specific group JID")
    group.add_argument("--remove", metavar="JID", help="remove a specific group JID")
    args = parser.parse_args()

    if not os.path.isfile(ENV_PATH):
        print("no hermes env file", file=sys.stderr)
        return 1

    entries, lines = parse(read_env())

    if args.list:
        print(f"{len(entries)} group(s) allowlisted")
        return 0

    target = args.add
    if args.add_latest:
        target = latest_group_jid()
        if not target:
            print("no group found in the bridge log yet", file=sys.stderr)
            return 1

    if not target or not JID_RE.fullmatch(target.strip()):
        print("invalid group id", file=sys.stderr)
        return 1

    target = target.strip()
    if args.remove:
        if target not in entries:
            print("that group was not allowlisted")
            return 0
        entries = [entry for entry in entries if entry != target]
        write_env(entries, lines)
        schedule_restart()
        print(f"removed; {len(entries)} group(s) allowlisted")
        return 0

    if target in entries:
        print(f"already allowlisted; {len(entries)} group(s)")
        return 0

    entries.append(target)
    write_env(entries, lines)
    schedule_restart()
    print(f"allowlisted; {len(entries)} group(s) - gateway restarting in ~20s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
