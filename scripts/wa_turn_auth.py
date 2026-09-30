"""Per-task owner authorization for WhatsApp tool execution.

This module carries only a boolean decision, never a sender identity or token.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar

_UNBOUND = object()
_NON_WHATSAPP = object()
_WA_ALLOWED: ContextVar[object] = ContextVar("_naquuuu_wa_allowed", default=_UNBOUND)
_GATEWAY_TURN: ContextVar[bool] = ContextVar("_naquuuu_gateway_turn", default=False)


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
