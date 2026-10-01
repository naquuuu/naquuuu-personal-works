"""Per-task owner authorization for WhatsApp tool execution.

This module carries only a boolean decision, never a sender identity or token.
"""
from __future__ import annotations

import json
import re
from contextlib import contextmanager
from contextvars import ContextVar

_UNBOUND = object()
_NON_WHATSAPP = object()
_WA_ALLOWED: ContextVar[object] = ContextVar("_naquuuu_wa_allowed", default=_UNBOUND)
_GATEWAY_TURN: ContextVar[bool] = ContextVar("_naquuuu_gateway_turn", default=False)

# Tripwire for obvious host-admin actions; obfuscated commands can evade it. The
# owner's host shell is the only admin path. It never carries identities.
# Every gap is length-bounded so a large argument cannot cause quadratic backtracking.
_HOST_ONLY_MAX_DEPTH = 8
# Hermes home spellings; the media caches directly under it stay usable for vision/audio flows.
_HERMES_HOME = r"(?:\.hermes|\$HERMES_HOME|\$\{HERMES_HOME\}|%LOCALAPPDATA%[/\\]hermes)"
_HERMES_TOKEN_END = r"[^\s\"';&|]"
_HERMES_MEDIA_CACHE = (
    r"[/\\](?:image_cache|audio_cache|document_cache|video_cache|cache)"
    r"(?:[/\\](?:(?!\.\.)" + _HERMES_TOKEN_END + r")*)?(?!" + _HERMES_TOKEN_END + r")"
)
_HOST_ONLY_RE = re.compile(
    r"whatsapp_group_fix|wa_free_response|wa_group_allow|wa_owner_gate|wa_chat_policy"
    r"|install_wa_owner_auth|install_wa_chat_policy|install_relay_guards"
    r"|sync_wa_owner_auth_prompt|refresh_wa_prompt_snapshot|enable_gates|swap_action_gateway_session"
    r"|(?<!process)\.env(?![A-Za-z0-9_])(?!\.(?:example|sample|template)(?![A-Za-z0-9_]))"
    r"|" + _HERMES_HOME + r"(?![\w.])(?!" + _HERMES_MEDIA_CACHE + r")"
    r"|\bhermes[^;&|]{0,200}?\bgateway\s+(?:start|stop|restart|install|uninstall|run|--replace)\b"
    r"|\bhermes[^;&|]{0,200}?\bconfig\s+(?:set|edit)\b"
    r"|\bsystemctl\b[^;&|]{0,200}?\bhermes"
    r"|\bservice\s+hermes"
    r"|\b(?:pkill|killall|pgrep)\b[^;&|]{0,200}?\bhermes"
    r"|\bprintenv\b"
    r"|/proc/[^\s\"'/]{1,32}/environ(?![\w])",
    re.IGNORECASE,
)


@contextmanager
def bind_source(source):
    raw_platform = getattr(source, "platform", None)
    platform = getattr(raw_platform, "value", raw_platform)
    if not isinstance(platform, str) or not platform.strip():
        decision = _UNBOUND
    elif platform.strip().lower() == "whatsapp":
        decision = True if getattr(source, "_naquuuu_owner_authorized", None) is True else False
    else:
        decision = _NON_WHATSAPP
    token = _WA_ALLOWED.set(decision)
    gateway_token = _GATEWAY_TURN.set(True)
    try:
        yield
    finally:
        _GATEWAY_TURN.reset(gateway_token)
        _WA_ALLOWED.reset(token)


def must_deny_tool() -> bool:
    """Deny unbound or guest turns; allow owner WhatsApp and explicitly bound non-WA."""
    if not _GATEWAY_TURN.get():
        return False  # Direct CLI/non-gateway agents have no WhatsApp sender scope.
    decision = _WA_ALLOWED.get()
    return decision is _UNBOUND or decision is False


def _references_host_only(value, depth=0) -> bool:
    if depth > _HOST_ONLY_MAX_DEPTH:
        return True  # Unbounded nesting is treated as hostile.
    if isinstance(value, (bytes, bytearray)):
        value = bytes(value).decode("utf-8", errors="replace")
    if isinstance(value, str):
        if _HOST_ONLY_RE.search(value):
            return True
        if value.lstrip()[:1] in ("{", "["):
            try:
                parsed = json.loads(value)
            except ValueError:
                return False
            return _references_host_only(parsed, depth + 1)  # Catches JSON escapes.
        return False
    if isinstance(value, dict):
        return any(_references_host_only(key, depth + 1) or _references_host_only(item, depth + 1)
                   for key, item in value.items())
    if isinstance(value, (list, tuple, set, frozenset)):
        return any(_references_host_only(item, depth + 1) for item in value)
    return False  # Non-string scalars cannot name a host action.


def must_deny_host_only(function_args) -> bool:
    """Deny host-admin actions on any bound WhatsApp turn, even owner-authorized ones."""
    if not _GATEWAY_TURN.get():
        return False
    decision = _WA_ALLOWED.get()
    if decision is not True and decision is not False:
        return False  # Unbound or non-WhatsApp turns are handled by must_deny_tool.
    return _references_host_only(function_args)
