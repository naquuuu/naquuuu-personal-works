#!/usr/bin/env python3
r"""
wa_free_response.py - owner-run promotion of an ALREADY allowlisted WhatsApp
group to free response, i.e. the whole group can chat with the bot and no
@mention is required.

What this does:
    WHATSAPP_FREE_RESPONSE_CHATS is a comma-separated list of group chat ids
    in <hermes-home>/.env. While a chat id sits in that list, the gateway
    processes group messages in that chat WITHOUT requiring a mention AND
    WITHOUT the per-sender group allowlist check (that reader lives in
    gateway/platforms/whatsapp_common.py::_whatsapp_free_response_chats).

Why this is deliberately owner-only:
    Free response bypasses the per-sender group check. Every member of the
    promoted group, including guests, can therefore reach the agent on every
    message. Promotion is a per-group, on-purpose decision; this script never
    adds a group on its own. A new group starts mention-only and stays
    mention-only until the owner promotes it here with --add.

Ordering matters:
    1. the group must first be allowlisted (scripts/wa_group_allow.py), and
    2. only then may it be promoted here.
    A chat id that is not in the allowlist is still accepted by this tool
    (it is a different key), so the owner keeps full control of the sequence.

Awareness (v0.21.4):
    Thread-awareness / observation (observe_unmentioned_group_messages,
    observe_allowed_chats, history_backfill) is NOT available for WhatsApp on
    Hermes v0.21.4 - that upstream path is Telegram-only. This script
    therefore writes no awareness keys and claims no awareness: the bot does
    not silently track ambient group chatter. Use --check to confirm what the
    installed build actually supports.

Unchanged by this tool (left exactly as the owner configured them):
    WHATSAPP_GROUP_POLICY, WHATSAPP_REQUIRE_MENTION, WHATSAPP_GROUP_ALLOWED_USERS,
    WHATSAPP_ALLOWED_USERS, WHATSAPP_ALLOW_ALL_USERS, and DM gating.

Safety:
    - Group ids are validated as digits@g.us; wildcards and open values are
      refused, and the tool refuses to run at all if the install is already in
      an allow-all posture.
    - The .env is backed up (<name>.bak-YYYYmmdd-HHMMSS) before any write.
    - Only the targeted key is rewritten; every other line is preserved.
    - No value, number, or chat id is ever echoed - status markers and counts
      only. --list prints a count, never the ids.
    - --dry-run writes nothing. The gateway is restarted immediately (no
      delayed/scheduled restart); the restart is skipped when nothing changed.
    - --check never prints file contents, .env values, or absolute paths.

Usage:
    python3 scripts/wa_free_response.py --list
    python3 scripts/wa_free_response.py --check
    python3 scripts/wa_free_response.py --dry-run --add <group-id>@g.us
    python3 scripts/wa_free_response.py --add <group-id>@g.us
    python3 scripts/wa_free_response.py --remove <group-id>@g.us
    python3 scripts/wa_free_response.py --add <group-id>@g.us --no-restart
    python3 scripts/wa_free_response.py --list --hermes-home <path>

The <group-id> is passed on your own command line and written only to the
local Hermes .env; it is never echoed back and never enters this repository.
Do not paste phone numbers, sender ids, or chat ids into chats, code, or
files (Tier 1 - see AGENTS.md Model-Input Boundary).

Exit codes: 0 = ok; 1 = fatal (bad input, missing/unwritable .env, or the
install is in an open posture); 2 = applied but the gateway restart needs
attention.
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

KEY = "WHATSAPP_FREE_RESPONSE_CHATS"
ALLOW_ALL_USERS_KEY = "WHATSAPP_ALLOW_ALL_USERS"
GROUP_POLICY_KEY = "WHATSAPP_GROUP_POLICY"
GROUP_ALLOWED_KEY = "WHATSAPP_GROUP_ALLOWED_USERS"
JID_RE = re.compile(r"^[0-9]{5,25}@g\.us$")
KEY_RE = re.compile(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")
WILDCARD_TOKENS = ("*", "all", "any", "open", "true", "1", "yes", "on")
OPEN_POLICIES = ("open", "all", "any", "everyone")
TRUTHY = ("true", "1", "yes", "on", "enabled")
BOM_UTF8 = b"\xef\xbb\xbf"
MAX_READ_BYTES = 4 * 1024 * 1024
MAX_SCAN_FILES = 400
FREE_RESPONSE_TOKENS = ("_whatsapp_free_response_chats", "free_response_chats")
AWARENESS_TOKENS = (
    "observe_unmentioned_group_messages",
    "observe_allowed_chats",
    "history_backfill",
)
WHATSAPP_LOCATIONS = (
    ("plugins", "platforms", "whatsapp"),
    ("gateway", "platforms", "whatsapp_common.py"),
)


# --------------------------------------------------------------------------- #
# host paths
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# .env read / write
# --------------------------------------------------------------------------- #
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


def raw_values(text: str, key: str) -> list[str]:
    """Every raw right-hand side assigned to `key` (comments/blank lines skipped)."""
    found: list[str] = []
    for line in text.splitlines():
        match = KEY_RE.match(line.strip())
        if match and match.group(1).upper() == key:
            found.append(match.group(2).strip().strip('"').strip("'"))
    return found


def split_entries(raw: str) -> list[str]:
    """Split one comma list, trim quotes/spaces, drop empties, keep order."""
    out: list[str] = []
    for part in raw.split(","):
        entry = part.strip().strip('"').strip("'")
        if entry and entry not in out:
            out.append(entry)
    return out


def free_response_entries(text: str) -> list[str]:
    """Union of every WHATSAPP_FREE_RESPONSE_CHATS occurrence, in order."""
    entries: list[str] = []
    for raw in raw_values(text, KEY):
        for entry in split_entries(raw):
            if entry not in entries:
                entries.append(entry)
    return entries


def render(text: str, key: str, entries: list[str]) -> str:
    """Collapse every `key` line into one canonical line; keep other lines."""
    out: list[str] = []
    seen = False
    for line in text.splitlines():
        match = KEY_RE.match(line.strip())
        if match and match.group(1).upper() == key:
            if seen:
                continue
            seen = True
            out.append(f"{key}={','.join(entries)}")
            continue
        out.append(line)
    if not seen:
        out.append(f"{key}={','.join(entries)}")
    return "\n".join(out) + "\n"


def backup_and_write(path: str, new_text: str, had_bom: bool, newline: str) -> str:
    """Back up the original, then write the new text (UTF-8, BOM preserved)."""
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = f"{path}.bak-{stamp}"
    shutil.copy2(path, backup)
    body = new_text.replace("\n", newline) if newline != "\n" else new_text
    data = body.encode("utf-8")
    if had_bom:
        data = BOM_UTF8 + data
    with open(path, "wb") as fh:
        fh.write(data)
    return backup


# --------------------------------------------------------------------------- #
# safety rails
# --------------------------------------------------------------------------- #
def is_open_posture(text: str) -> str | None:
    """Refuse to act when the install is already allow-all / open."""
    for raw in raw_values(text, ALLOW_ALL_USERS_KEY):
        if raw.strip().lower() in TRUTHY:
            return "WHATSAPP_ALLOW_ALL_USERS is enabled (open posture)"
    for raw in raw_values(text, GROUP_POLICY_KEY):
        if raw.strip().lower() in OPEN_POLICIES:
            return "WHATSAPP_GROUP_POLICY is an open policy"
    return None


def rejected_token(raw: str) -> str | None:
    """Return the offending token when `raw` is a wildcard / open value."""
    for entry in split_entries(raw):
        if entry.lower() in WILDCARD_TOKENS:
            return entry.lower()
    return None


# --------------------------------------------------------------------------- #
# --check probe (booleans only, never file contents)
# --------------------------------------------------------------------------- #
def candidate_roots(home: str) -> list[str]:
    """Install roots to probe, nearest first (absolute paths never printed)."""
    roots: list[str] = [
        os.path.join(home, "hermes-agent"),
        home,
    ]
    exe = find_hermes_bin(home)
    if exe:
        current = os.path.dirname(os.path.abspath(exe))
        for _ in range(4):
            roots.append(current)
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent
    unique: list[str] = []
    for root in roots:
        norm = os.path.normpath(root)
        if norm not in unique and os.path.isdir(norm):
            unique.append(norm)
    return unique


def locate_install(home: str) -> str | None:
    """First root that contains a known WhatsApp source location."""
    for root in candidate_roots(home):
        for parts in WHATSAPP_LOCATIONS:
            if os.path.exists(os.path.join(root, *parts)):
                return root
    return None


def whatsapp_files(root: str) -> list[str]:
    """Only the WhatsApp plugin dir and whatsapp_common.py; nothing else."""
    files: list[str] = []
    for parts in WHATSAPP_LOCATIONS:
        target = os.path.join(root, *parts)
        if os.path.isfile(target):
            files.append(target)
        elif os.path.isdir(target):
            for dirpath, dirnames, filenames in os.walk(target):
                dirnames[:] = [d for d in dirnames if d != "__pycache__"]
                for name in sorted(filenames):
                    if not name.endswith(".py"):
                        continue
                    files.append(os.path.join(dirpath, name))
                    if len(files) >= MAX_SCAN_FILES:
                        return files
    return files


def probe_tokens(root: str) -> tuple[bool, bool, int]:
    """(free_response_supported, awareness_supported_for_whatsapp, files scanned)."""
    free_response = False
    awareness = False
    files = whatsapp_files(root)
    for path in files:
        try:
            with open(path, "rb") as fh:
                blob = fh.read(MAX_READ_BYTES)
        except OSError:
            continue
        text = blob.decode("utf-8", errors="replace")
        if any(token in text for token in FREE_RESPONSE_TOKENS):
            free_response = True
        if any(token in text for token in AWARENESS_TOKENS):
            awareness = True
    return free_response, awareness, len(files)


def detect_version(home: str, root: str | None) -> str:
    """Best-effort Hermes version, else 'unknown'. Never prints file contents."""
    exe = find_hermes_bin(home)
    if exe:
        try:
            result = subprocess.run(
                [exe, "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            match = re.search(r"(\d+\.\d+(?:\.\d+)?(?:[-.][0-9A-Za-z.]+)?)", result.stdout or "")
            if match:
                return match.group(1)
        except Exception:
            pass
    if root:
        for parts in (
            ("pyproject.toml",),
            ("hermes-agent", "pyproject.toml"),
            ("hermes", "pyproject.toml"),
        ):
            candidate = os.path.join(root, *parts)
            if not os.path.isfile(candidate):
                continue
            try:
                with open(candidate, "rb") as fh:
                    text = fh.read(MAX_READ_BYTES).decode("utf-8", errors="replace")
            except OSError:
                continue
            match = re.search(
                r"(?m)^\s*(?:version|__version__)\s*[=:]\s*[\"']([^\"']+)[\"']", text
            )
            if match:
                return match.group(1)
    return "unknown"


def run_check(home: str) -> int:
    print("=" * 74)
    print("  WHATSAPP FREE RESPONSE - support probe (booleans only)")
    print("=" * 74)
    print(f"  hermes home:      {home}")
    print("  scope:            plugins/platforms/whatsapp/ + gateway/platforms/whatsapp_common.py")
    root = locate_install(home)
    if root is None:
        print("  install_probe:    not found (no WhatsApp source in the usual locations)")
        print("-" * 74)
        print(f"  {'free_response_supported':<34} unknown")
        print(f"  {'awareness_supported_for_whatsapp':<34} unknown")
        print(f"  {'hermes_version':<34} {detect_version(home, None)}")
        print("-" * 74)
        print("  Note: install Hermes on this host, then rerun --check.")
        return 0
    free_response, awareness, scanned = probe_tokens(root)
    print(f"  install_probe:    found ({scanned} WhatsApp source file(s) inspected)")
    print(f"  {'hermes_version':<34} {detect_version(home, root)}")
    print("-" * 74)
    print(f"  {'free_response_supported':<34} {str(free_response).lower()}")
    print(f"  {'awareness_supported_for_whatsapp':<34} {str(awareness).lower()}")
    print("-" * 74)
    if not free_response:
        print("  WARN  this build has no free-response reader; --add would have no effect.")
        print("        Update with: hermes update --backup")
    if awareness:
        print("  WARN  awareness tokens found in the WhatsApp paths (unexpected on v0.21.4).")
    else:
        print("  OK    awareness is unavailable for WhatsApp (expected on v0.21.4):")
        print("        the bot does not observe ambient group chatter.")
    return 0


# --------------------------------------------------------------------------- #
# gateway restart (same contract as scripts/whatsapp_group_fix.py)
# --------------------------------------------------------------------------- #
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


def restart_gateway(home: str) -> int:
    """restart, else start; 0 when clean, 2 when the owner must finish by hand."""
    print("  Restarting gateway: hermes gateway restart")
    restart = run_gateway(home, "restart")
    if restart is None:
        print("  WARN  hermes binary not found or restart failed to run.")
        print("        Run manually: hermes gateway start")
        return 2
    code, output = restart
    for line in output[-4:]:
        print(f"    | {line}")
    if code == 0:
        print("  PASS  gateway restart command completed")
        return 0
    print("  WARN  restart path failed; falling back to: hermes gateway start")
    start = run_gateway(home, "start")
    if start is None:
        print("  WARN  gateway start could not run. Run manually: hermes gateway start")
        return 2
    code, output = start
    for line in output[-4:]:
        print(f"    | {line}")
    if code != 0:
        print(f"  WARN  gateway start exited {code}. Check: hermes gateway status")
        return 2
    print("  PASS  gateway started (start fallback)")
    return 0


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Promote an allowlisted WhatsApp group to free response (no @mention)."
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--add", metavar="CHATID", help="promote one group to free response")
    action.add_argument("--remove", metavar="CHATID", help="return one group to mention-only")
    action.add_argument("--list", action="store_true", help="print how many groups are promoted")
    action.add_argument("--check", action="store_true", help="probe the installed Hermes build")
    parser.add_argument(
        "--dry-run", action="store_true", help="preview changes; write nothing, restart nothing"
    )
    parser.add_argument(
        "--no-restart", action="store_true", help="write the change but do not restart the gateway"
    )
    parser.add_argument(
        "--hermes-home",
        default=None,
        help=r"override the Hermes home (default: %LOCALAPPDATA%\hermes or ~/.hermes)",
    )
    args = parser.parse_args()

    home = (
        os.path.abspath(os.path.expanduser(args.hermes_home))
        if args.hermes_home
        else hermes_home()
    )
    if args.check:
        return run_check(home)

    env_path = os.path.join(home, ".env")
    if not os.path.isfile(env_path):
        print("FAIL  .env not found in the resolved Hermes home.")
        print("      Check the Hermes install, or pass --hermes-home.")
        return 1
    parsed = read_env(env_path)
    if parsed is None:
        print("FAIL  .env unreadable in the resolved Hermes home.")
        return 1
    text, had_bom, newline = parsed

    if args.list:
        entries = free_response_entries(text)
        print(f"{len(entries)} free-response chat(s)")
        return 0

    target = (args.add or args.remove or "").strip()
    token = rejected_token(target)
    if token is not None:
        print(f"FAIL  refusing a wildcard/open value ('{token}').")
        print("      Free response is promoted per group id only.")
        return 1
    if not JID_RE.match(target):
        print("FAIL  chat id must be digits@g.us (5-25 digits).")
        return 1

    entries = free_response_entries(text)
    existing = rejected_token(",".join(entries))
    if existing is not None:
        print("FAIL  the existing list already holds a wildcard/open value.")
        print("      Fix that by hand before promoting groups one at a time.")
        return 1
    rail = is_open_posture(text)
    if rail is not None:
        print(f"FAIL  refusing to run: {rail}.")
        print("      Restore the owner-configured allowlist policy first.")
        return 1

    removing = args.remove is not None
    if removing:
        if target not in entries:
            status = "not present"
            new_entries = entries
        else:
            status = "removed"
            new_entries = [entry for entry in entries if entry != target]
    elif target in entries:
        status = "already present"
        new_entries = entries
    else:
        status = "added"
        new_entries = entries + [target]

    changed = new_entries != entries
    mode = "DRY RUN (no writes, no restart)" if args.dry_run else (
        "APPLY (no restart)" if args.no_restart else "APPLY + RESTART"
    )

    print("=" * 74)
    print("  WHATSAPP FREE RESPONSE - group-wide chat, no @mention")
    print("=" * 74)
    print(f"  hermes home: {home}")
    print(f"  mode:        {mode}")
    print("-" * 74)
    print(f"  {KEY:<28}: {status}")
    print(f"  free-response chats: {len(new_entries)}")
    print("-" * 74)

    if args.dry_run:
        if changed:
            print("DRY RUN: nothing written. Re-run without --dry-run to apply.")
        else:
            print("DRY RUN: no change needed; nothing written.")
        return 0

    if not changed:
        print("No .env change needed. Gateway restart skipped (nothing applied).")
        return 0

    try:
        backup = backup_and_write(env_path, render(text, KEY, new_entries), had_bom, newline)
    except OSError as exc:
        print(f"FAIL  could not write .env ({exc.__class__.__name__}); nothing changed.")
        return 1
    print(f"PASS  .env updated; backup: {os.path.basename(backup)}")

    if args.no_restart:
        print("Skipped restart (--no-restart). Apply later with: hermes gateway restart")
        return 0

    code = restart_gateway(home)
    print("-" * 74)
    print("  Every member of a promoted group can now reach the agent without a mention.")
    print("  Keep a tool gate in front of tool execution (scripts/wa_owner_gate.py).")
    if code != 0:
        print("  Config applied, but the gateway restart needs attention.")
        return 2
    print("Done. Test in the group: send a plain message with no @mention.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
