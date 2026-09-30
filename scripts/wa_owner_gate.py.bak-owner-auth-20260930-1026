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

How the persona must use it:
    Before `opencode run`, before any skill install, and before any other tool
    execution, the model calls this gate with the current sender id and obeys
    the verdict verbatim:
        exit 0 = ALLOW  -> the owner asked; proceed with the tool call
        exit 3 = DENY   -> a guest; reply in chat only, run nothing
    There is no third answer, and no path that treats a DENY as negotiable.

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
    They are read only from the host environment variable
    NAQUUUU_WA_OWNER_IDS (comma-separated) and never live in this repository,
    in code, in docs, or in any prompt (AGENTS.md Model-Input Boundary). No
    real phone number, sender id, or owner id is written anywhere in this
    file, including comments and examples. This script never prints the sender
    id, the owner ids, or the owner list - only the verdict and a reason
    category.

Usage:
    python3 scripts/wa_owner_gate.py --sender <sender-id>
    python3 scripts/wa_owner_gate.py --sender <sender-id> --json
    python3 scripts/wa_owner_gate.py --hermes-home <path>   # accepted, inert

`--hermes-home` is accepted for interface symmetry with the other relay
helpers; the owner list comes from the process environment only, so it does
not affect the verdict.

Exit codes: 0 = ALLOW (the sender is an owner); 3 = DENY (malformed sender,
sender is not an owner, or no owner list configured); 2 = argparse usage error
(e.g. a missing --sender). No usage error can produce ALLOW.
"""

from __future__ import annotations

import argparse
import io
import json
import os
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


def owner_digits() -> set[str] | None:
    """Digit form of the configured owners; None when unusable (fail closed)."""
    raw = os.environ.get(OWNER_ENV)
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


def evaluate(sender: str) -> tuple[bool, str]:
    """(allow, reason). Shape check first, so a non-id is never compared."""
    if not is_sender_id(sender):
        return False, DENY_BAD_SENDER
    owners = owner_digits()
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
        help="accepted for interface symmetry; the owner list comes from the host env only",
    )
    parser.add_argument(
        "--json", action="store_true", help="print the verdict as JSON (no identifiers)"
    )
    args = parser.parse_args()

    # The verdict below reads the host environment only; --hermes-home is
    # accepted for interface parity and deliberately has no effect on it.
    allow, reason = evaluate(args.sender)
    return emit(allow, reason, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
