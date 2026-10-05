#!/usr/bin/env python3
r"""
wa_owner_gate.py - the execution gate for the WhatsApp relay: "may THIS sender
cause tool execution (opencode run, skill install, any tool)?"

Why this gate exists:
    Free response (WHATSAPP_FREE_RESPONSE_CHATS) lets a message from any
    member of a promoted group - including guests - reach the agent without a
    mention. That is the intended "the whole group can chat" behavior, but it
    also means a guest's plain text arrives in the agent's context. Chatting
    is harmless; running `opencode run`, installing a skill, or executing any
    other tool on the relay host is not. This gate is therefore the ONLY
    reliable boundary between "a guest can talk" and "a guest can act".

Host integration:
    The gateway uses this evaluator with a bridge-provided sender identity.
    A model must never supply a sender identity or invoke this CLI as a gate.

Fail-closed by design:
    - No owner list configured (variable absent, empty, or a wildcard such as
      `*`) -> DENY, exit 3, reason `no-owner-config`. A broken configuration can
      never widen access.
    - A --sender value that is not a bare sender id -> DENY, exit 3, reason
      `bad-sender-format`. The shape check happens BEFORE any comparison, so a
      malformed sender is never normalized into something comparable: message
      text, a chat id, or any other string that merely CONTAINS an owner id can
      never be compared against the owner list, and therefore can never ALLOW.
    - Owner-list entries that are not bare sender ids are dropped too; if
      nothing usable survives, the verdict is DENY (`no-owner-config`).

Strict sender-id shape:
    A sender id is exactly:

        [ + ] DIGITS [ @s.whatsapp.net | @lid ]

    enforced as ^\+?[0-9]+(@(s\.whatsapp\.net|lid))?$ against the value after
    stripping surrounding whitespace. Nothing else is accepted - no interior
    spaces, no prefixes or labels, no other domains, no free text. Comparison
    after that shape check is by digits only, so an owner matches whether it
    arrives as bare digits, with a leading `+`, or with an
    `@s.whatsapp.net` / `@lid` suffix.

Owner ids are Tier 1:
    They are read only from the host's private <hermes-home>/.env file,
    variable NAQUUUU_WA_OWNER_IDS (comma-separated), and never live in this repository,
    in code, in docs, or in any prompt (AGENTS.md Model-Input Boundary). No
    real phone number, sender id, or owner id is written anywhere in this
    file, including comments and examples. This script never prints the sender
    id, the owner ids, or the owner list - only the verdict and a reason
    category.

Usage:
    python3 scripts/wa_owner_gate.py --sender <sender-id>
    python3 scripts/wa_owner_gate.py --sender <sender-id> --json
    python3 scripts/wa_owner_gate.py --hermes-home <path>

`--hermes-home` selects the private configuration directory. Otherwise
HERMES_HOME or ~/.hermes is used. Missing or unreadable configuration denies.

Exit codes: 0 = ALLOW (the sender is an owner); 3 = DENY (malformed sender,
sender is not an owner, or no owner list configured); 2 = argparse usage error
(e.g. a missing --sender). No usage error can produce ALLOW.
"""

from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path
import re
import sys

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

OWNER_ENV = "NAQUUUU_WA_OWNER_IDS"
WILDCARD_TOKENS = ("*", "all", "any", "everyone", "open")
# A sender id is [+]digits[@s.whatsapp.net|@lid] and nothing else.
SENDER_ID_RE = re.compile(r"^\+?[0-9]+(@(s\.whatsapp\.net|lid))?$")
DIGITS_RE = re.compile(r"\D+")

ALLOW = "owner"
DENY_NOT_OWNER = "not-owner"
DENY_NO_CONFIG = "no-owner-config"
DENY_BAD_SENDER = "bad-sender-format"


def is_sender_id(raw: str) -> bool:
    """True only for a bare sender id; anything else is not an id at all."""
    return SENDER_ID_RE.fullmatch((raw or "").strip()) is not None


def digits_only(raw: str) -> str:
    """Digits of an already-validated id, so +, @s.whatsapp.net and @lid do not matter."""
    return DIGITS_RE.sub("", (raw or "").strip())


def owner_value(hermes_home: str | Path | None = None) -> str | None:
    """Read the single private configuration source used by bridge and helper."""
    try:
        fallback_home = os.environ.get("USERPROFILE") if os.name == "nt" else None
        fallback_home = fallback_home or Path.home()
        home = Path(hermes_home) if hermes_home is not None else Path(
            os.environ.get("HERMES_HOME") or (Path(fallback_home) / ".hermes")
        )
        for line in (home / ".env").read_text(encoding="utf-8").splitlines():
            match = re.match(r"^\s*(?:export\s+)?" + OWNER_ENV + r"\s*=\s*(.*)$", line)
            if match:
                return match.group(1).strip().strip("\"'")
    except (OSError, UnicodeError, RuntimeError, ValueError):
        return None
    return None


def owner_digits(hermes_home: str | Path | None = None) -> set[str] | None:
    """Digit form of the configured owners; None when unusable (fail closed)."""
    raw = owner_value(hermes_home)
    if raw is None:
        return None
    entries = [part.strip() for part in raw.split(",") if part.strip()]
    if not entries:
        return None
    for entry in entries:
        if entry.lower() in WILDCARD_TOKENS:
            return None
    owners = {digits_only(entry) for entry in entries if is_sender_id(entry)}
    owners.discard("")
    return owners or None


def evaluate(sender: str, hermes_home: str | Path | None = None) -> tuple[bool, str]:
    """(allow, reason). Shape check first, so a non-id is never compared."""
    if not is_sender_id(sender):
        return False, DENY_BAD_SENDER
    owners = owner_digits(hermes_home)
    if owners is None:
        return False, DENY_NO_CONFIG
    if digits_only(sender) in owners:
        return True, ALLOW
    return False, DENY_NOT_OWNER


def emit(allow: bool, reason: str, as_json: bool) -> int:
    if allow:
        if as_json:
            print(json.dumps({"allow": True, "reason": reason}))
        else:
            print("ALLOW")
        return 0
    if as_json:
        print(json.dumps({"allow": False, "reason": reason}))
    else:
        print(f"DENY ({reason})")
    return 3


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Decide whether the current WhatsApp sender may run tools."
    )
    parser.add_argument(
        "--sender",
        metavar="ID",
        required=True,
        help="current sender id: [+]digits[@s.whatsapp.net|@lid]; anything else denies",
    )
    parser.add_argument(
        "--hermes-home",
        default=None,
        help="Hermes home whose private .env contains NAQUUUU_WA_OWNER_IDS",
    )
    parser.add_argument(
        "--json", action="store_true", help="print the verdict as JSON (no identifiers)"
    )
    args = parser.parse_args()

    allow, reason = evaluate(args.sender, args.hermes_home)
    return emit(allow, reason, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
