#!/usr/bin/env python3
r"""
WhatsApp Group Fix - enable group intake on the local Hermes gateway.

Applies the agreed policy to the Hermes .env:

    WHATSAPP_GROUP_POLICY=allowlist  admit only the groups listed in
                                     WHATSAPP_GROUP_ALLOWED_USERS
                                     (senders still pass the normal
                                     allowlist / pairing check)
    WHATSAPP_REQUIRE_MENTION=true    reply only to @mentions, replies to
                                     the bot, or /commands

Note: the gateway refuses WHATSAPP_GROUP_POLICY=open unless
WHATSAPP_ALLOW_ALL_USERS is enabled (safe-mode rail), so `open` is not
used here; allowlist one group at a time with --group.

then restarts the gateway to load the change.

Why: Hermes defaults to WHATSAPP_GROUP_POLICY=pairing, which forwards
nothing from groups, so the bot stays silent in group chats while DMs
work normally. DM behavior is unaffected by this change.

Safety:
  - The .env is backed up (<name>.bak-YYYYmmdd-HHMMSS) before any write.
  - Existing keys are updated in place; re-running is idempotent.
  - File contents are never echoed; only key status markers are shown.
  - Path resolution mirrors scripts/host_check.py.

Usage:
  python scripts/whatsapp_group_fix.py --dry-run     # preview only
  python scripts/whatsapp_group_fix.py               # apply + restart
  python scripts/whatsapp_group_fix.py --no-restart  # apply only
  python scripts/whatsapp_group_fix.py --allow-user 62XXXXXXXXXX
                                                     # also append one number
                                                     # to WHATSAPP_ALLOWED_USERS
  python scripts/whatsapp_group_fix.py --group 1203630XXXXXXXXXX@g.us
                                                     # allowlist one group JID

The --allow-user value is passed on your command line and written only to
the local Hermes .env; it is never echoed back and never enters this
repository. Do not paste phone numbers into chats or files (Tier 1).

Exit codes: 0 = success (applied or previewed); 1 = fatal (no .env or
unwritable); 2 = config applied, but the gateway restart needs attention.
"""

from __future__ import annotations

import argparse
import datetime
import io
import os
import re
import shutil
import subprocess
import sys

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

TARGETS: tuple[tuple[str, str], ...] = (
    ("WHATSAPP_GROUP_POLICY", "allowlist"),
    ("WHATSAPP_REQUIRE_MENTION", "true"),
)
TARGET_MAP = dict(TARGETS)
ALLOWED_KEY = "WHATSAPP_ALLOWED_USERS"
ALLOW_ALL_KEY = "WHATSAPP_ALLOW_ALL_USERS"
GROUP_KEY = "WHATSAPP_GROUP_ALLOWED_USERS"
GROUP_JID_RE = re.compile(r"^[0-9]{5,20}@g\.us$")
KEY_RE = re.compile(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")
EXPORT_RE = re.compile(r"^export\s+", re.IGNORECASE)
BOM_UTF8 = b"\xef\xbb\xbf"


def hermes_home() -> str:
    """Resolve the native Hermes install root for this host."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(
            os.path.expanduser("~"), "AppData", "Local"
        )
        return os.path.join(base, "hermes")
    return os.path.join(os.path.expanduser("~"), ".hermes")


def find_hermes_bin(home: str) -> str | None:
    """Locate the hermes executable: install bin dir first, then PATH."""
    for candidate in (
        os.path.join(home, "bin", "hermes.exe"),
        os.path.join(home, "bin", "hermes"),
    ):
        if os.path.isfile(candidate):
            return candidate
    return shutil.which("hermes")


def read_env(path: str) -> tuple[str, bool, str] | None:
    """Return (text, had_bom, newline) or None when the file is unreadable."""
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError:
        return None
    had_bom = raw.startswith(BOM_UTF8)
    text = raw.decode("utf-8-sig", errors="replace")
    newline = "\r\n" if "\r\n" in text else "\n"
    return text, had_bom, newline


def plan_changes(text: str, newline: str) -> tuple[str, dict[str, str]]:
    """Return (new_text, key -> status). Status: added | updated | already set."""
    status: dict[str, str] = {}
    out_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        match = KEY_RE.match(stripped)
        key = match.group(1).upper() if match else None
        target_value = TARGET_MAP.get(key) if key else None
        if target_value is None:
            out_lines.append(line)
            continue
        wanted = f"{key}={target_value}"
        canonical = f"export {wanted}" if EXPORT_RE.match(stripped) else wanted
        if stripped.upper() == canonical.upper():
            status.setdefault(key, "already set")
            out_lines.append(line)
        else:
            status[key] = "updated"
            out_lines.append(canonical)
    for key, value in TARGETS:
        if key not in status:
            status[key] = "added"
            out_lines.append(f"{key}={value}")
    return newline.join(out_lines) + newline, status


def normalize_number(raw: str) -> str | None:
    """Digits only, country code, no leading 0; None when invalid."""
    digits = re.sub(r"\D", "", raw)
    if not digits or digits.startswith("0") or not (7 <= len(digits) <= 15):
        return None
    return digits


def update_allowed_users(text: str, newline: str, number: str) -> tuple[str, str]:
    """Ensure `number` is in WHATSAPP_ALLOWED_USERS. Values are never echoed."""
    lines = text.splitlines()
    for line in lines:
        match = KEY_RE.match(line.strip())
        if match and match.group(1).upper() == ALLOW_ALL_KEY:
            value = line.split("=", 1)[1].strip().strip('"').strip("'").lower()
            if value in ("true", "1", "yes", "on"):
                return text, "skipped (WHATSAPP_ALLOW_ALL_USERS is set)"
    found: list[int] = []
    for index, line in enumerate(lines):
        match = KEY_RE.match(line.strip())
        if match and match.group(1).upper() == ALLOWED_KEY:
            found.append(index)
            entries = [e.strip() for e in line.split("=", 1)[1].split(",") if e.strip()]
            if any(e == "*" for e in entries):
                return text, "skipped (WHATSAPP_ALLOWED_USERS is *)"
            if number in {re.sub(r"\D", "", e) for e in entries}:
                return text, "already present"
    if not found:
        lines.append(f"{ALLOWED_KEY}={number}")
        return newline.join(lines) + newline, "created (1 entry)"
    last = found[-1]
    stripped = lines[last].strip()
    prefix = "export " if EXPORT_RE.match(stripped) else ""
    value = stripped.split("=", 1)[1].strip().strip('"').strip("'")
    merged = f"{value},{number}" if value else number
    lines[last] = f"{prefix}{ALLOWED_KEY}={merged}"
    count = len([e for e in merged.split(",") if e.strip()])
    return newline.join(lines) + newline, f"appended (now {count} entries)"


def update_group_list(text: str, newline: str, jid: str) -> tuple[str, str]:
    """Ensure `jid` is in WHATSAPP_GROUP_ALLOWED_USERS. Values are never echoed."""
    lines = text.splitlines()
    found: list[int] = []
    for index, line in enumerate(lines):
        match = KEY_RE.match(line.strip())
        if match and match.group(1).upper() == GROUP_KEY:
            found.append(index)
            entries = [e.strip() for e in line.split("=", 1)[1].split(",") if e.strip()]
            if jid in entries:
                return text, "already present"
    if not found:
        lines.append(f"{GROUP_KEY}={jid}")
        return newline.join(lines) + newline, "created (1 group)"
    last = found[-1]
    stripped = lines[last].strip()
    prefix = "export " if EXPORT_RE.match(stripped) else ""
    value = stripped.split("=", 1)[1].strip().strip('"').strip("'")
    merged = f"{value},{jid}" if value else jid
    lines[last] = f"{prefix}{GROUP_KEY}={merged}"
    count = len([e for e in merged.split(",") if e.strip()])
    return newline.join(lines) + newline, f"appended (now {count} group(s))"


def backup_and_write(path: str, new_text: str, had_bom: bool) -> str:
    """Back up the original, then write the new text (UTF-8, BOM preserved)."""
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = f"{path}.bak-{stamp}"
    shutil.copy2(path, backup)
    data = new_text.encode("utf-8")
    if had_bom:
        data = BOM_UTF8 + data
    with open(path, "wb") as fh:
        fh.write(data)
    return backup


def run_gateway(home: str, subcommand: str) -> tuple[int, list[str]] | None:
    """Run `hermes gateway <subcommand>`; None when the binary cannot run."""
    exe = find_hermes_bin(home)
    if not exe:
        return None
    try:
        result = subprocess.run(
            [exe, "gateway", subcommand],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
    except Exception:
        return None
    output = [
        line for line in f"{result.stdout}\n{result.stderr}".splitlines() if line.strip()
    ]
    return result.returncode, output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Enable WhatsApp group intake on the local Hermes gateway"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="preview changes; write nothing, restart nothing",
    )
    parser.add_argument(
        "--no-restart",
        action="store_true",
        help="write changes but do not restart the gateway",
    )
    parser.add_argument(
        "--hermes-home",
        default=None,
        help=r"override the Hermes home (default: %LOCALAPPDATA%\hermes or ~/.hermes)",
    )
    parser.add_argument(
        "--allow-user",
        default=None,
        help="also append one number (full international digits, no +) to WHATSAPP_ALLOWED_USERS",
    )
    parser.add_argument(
        "--group",
        default=None,
        help="allowlist one group JID (e.g. 1234567890@g.us); sets WHATSAPP_GROUP_POLICY=allowlist",
    )
    args = parser.parse_args()

    home = (
        os.path.abspath(os.path.expanduser(args.hermes_home))
        if args.hermes_home
        else hermes_home()
    )
    env_path = os.path.join(home, ".env")
    if args.dry_run:
        mode = "DRY RUN (no writes, no restart)"
    elif args.no_restart:
        mode = "APPLY (no restart)"
    else:
        mode = "APPLY + RESTART"

    print("=" * 74)
    print("  WHATSAPP GROUP FIX - Hermes group intake + gateway restart")
    print("=" * 74)
    print(f"  hermes home: {home}")
    print(f"  .env:        {env_path}")
    print(f"  mode:        {mode}")
    print("-" * 74)

    if not os.path.isfile(env_path):
        print(f"FAIL  .env not found at {env_path}")
        print("      Check the Hermes install (Phase 2) before rerunning.")
        return 1

    parsed = read_env(env_path)
    if parsed is None:
        print(f"FAIL  .env unreadable at {env_path}")
        return 1
    text, had_bom, newline = parsed

    allow_number: str | None = None
    if args.allow_user:
        allow_number = normalize_number(args.allow_user)
        if allow_number is None:
            print("FAIL  --allow-user needs full international digits (country code, no leading 0)")
            return 1

    new_text, status = plan_changes(text, newline)
    allow_status: str | None = None
    if allow_number:
        new_text, allow_status = update_allowed_users(new_text, newline, allow_number)
    group_status: str | None = None
    if args.group:
        jid = args.group.strip()
        if not GROUP_JID_RE.match(jid):
            print("FAIL  --group needs a full group JID (digits + @g.us)")
            return 1
        new_text, group_status = update_group_list(new_text, newline, jid)
    changed = any(value != "already set" for value in status.values())
    if allow_status and allow_status.startswith(("appended", "created")):
        changed = True
    if group_status and group_status.startswith(("appended", "created")):
        changed = True

    for key, _ in TARGETS:
        state = status.get(key, "already set")
        detail = f"  ({key}={TARGET_MAP[key]})" if state in ("added", "updated") else ""
        print(f"{key:<28}: {state}{detail}")
    if allow_status:
        print(f"{ALLOWED_KEY:<28}: {allow_status}")
    if group_status:
        print(f"{GROUP_KEY:<28}: {group_status}")
    print("-" * 74)

    if args.dry_run:
        if changed:
            print("DRY RUN: nothing written. Re-run without --dry-run to apply.")
        else:
            print("No changes needed: policy already set. Re-run without --dry-run to restart.")
        return 0

    if changed:
        try:
            backup = backup_and_write(env_path, new_text, had_bom)
        except OSError as exc:
            print(f"FAIL  could not write .env ({exc.__class__.__name__}); nothing changed.")
            return 1
        print(f"PASS  .env updated; backup: {backup}")
    else:
        print("No .env changes needed (policy already set).")

    if args.no_restart:
        print("Skipped restart (--no-restart). Apply with: hermes gateway restart")
        return 0

    print("Restarting gateway: hermes gateway restart")
    restart = run_gateway(home, "restart")
    if restart is None:
        print("WARN  hermes binary not found or restart failed to run.")
        print("      Run manually: hermes gateway start")
        return 2
    code, output = restart
    for line in output[-4:]:
        print(f"    | {line}")
    if code != 0:
        print("WARN  restart path failed; falling back to: hermes gateway start")
        start = run_gateway(home, "start")
        if start is None:
            print("WARN  gateway start could not run. Run manually: hermes gateway start")
            return 2
        code, output = start
        for line in output[-4:]:
            print(f"    | {line}")
        if code != 0:
            print(f"WARN  gateway start exited {code}. Check: hermes gateway status")
            return 2
        print("PASS  gateway started (start fallback)")
    else:
        print("PASS  gateway restart command completed")

    probe = run_gateway(home, "status")
    if probe is not None:
        for line in probe[1][-3:]:
            print(f"    | {line}")

    print("-" * 74)
    if allow_status and allow_status.startswith(("appended", "created")):
        print("NOTE  allowlisted users can trigger the relay -> opencode run on this host.")
    if not group_status:
        print("Tip   without --group no group is allowlisted (groups stay silent).")
    print("Done. Test in the group: @mention the bot and expect a reply.")
    print("If it stays silent, update Hermes: hermes update --backup (then retest).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
