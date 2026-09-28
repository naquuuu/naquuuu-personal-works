"""Outbound text sanitization, drafting leak prevention, and repetition guard for WhatsApp relay.

Collapses adjacent duplicate text events, detects internal reasoning/drafts (<think>, Thought:),
suppresses degenerative repetition loop floods, and enforces signature combination matching
against internal harness prompts with fail-closed safe fallback replies.
"""
from __future__ import annotations

import hashlib
import logging
import re

logger = logging.getLogger(__name__)

SAFE_FALLBACK_REPLY = "Jawaban belum bisa ditampilkan. Silakan coba lagi."

# Marker regex patterns
RE_VERY_FIRST = re.compile(r"\bVERY\s+FIRST\s+TOOL\s+RESULT\b", re.IGNORECASE)
RE_SYSTEM_NOTE = re.compile(r"\bSystem\s+Note:?\b", re.IGNORECASE)
RE_WHATSAPP_ENV = re.compile(r"\bThis\s+conversation\s+is\s+happening\s+via\s+WhatsApp\b", re.IGNORECASE)
RE_STOP_SENDING = re.compile(
    r"\b(stop\s+sending\s+messages|do\s+not\s+send\s+(further\s+)?messages|stop\s+sending)\b",
    re.IGNORECASE,
)
RE_RATE_LIMIT_INSTRUCTION = re.compile(
    r"\b(after\s+a\s+rate\s+limit|if\s+you\s+(receive|hit)\s+a\s+rate\s+limit|provider\s+rate\s+limit)\b",
    re.IGNORECASE,
)
RE_DRAFT_PREFIXES = re.compile(
    r"(?:^|\n)\s*(?:Thought|Thinking Process|Internal Draft|Draft\s+\d+|Let me think)\s*:",
    re.IGNORECASE,
)


def normalize_for_inspection(text: str) -> str:
    """Collapses consecutive whitespace to single spaces for robust token matching."""
    return " ".join(text.split())


def collapse_adjacent_duplicate_texts(texts: list[str]) -> list[str]:
    """Collapses adjacent duplicate text chunks or events."""
    collapsed: list[str] = []
    for item in texts:
        stripped = item.strip()
        if not stripped:
            continue
        if not collapsed or collapsed[-1].strip() != stripped:
            collapsed.append(item)
    return collapsed


def contains_internal_drafting(text: str) -> bool:
    """Detects internal reasoning markup, thought tags, or candidate draft headers."""
    lowered = text.lower()
    if "<think" in lowered or "</think>" in lowered:
        return True
    if RE_DRAFT_PREFIXES.search(text):
        return True
    return False


def has_repetition_loop(text: str) -> bool:
    """Detects degenerate repetition loops that would trigger multipart flood splits."""
    # 1. Repeated sentences or distinct clauses >= 10 chars
    sentences = [s.strip() for s in re.split(r"[.!?\n]+", text) if len(s.strip()) >= 10]
    counts: dict[str, int] = {}
    for s in sentences:
        s_norm = " ".join(s.lower().split())
        counts[s_norm] = counts.get(s_norm, 0) + 1
        if counts[s_norm] >= 3:
            return True

    # 2. Repeated consecutive word n-grams (loops of 3 to 12 words)
    words = text.split()
    if len(words) >= 9:
        for span in range(3, min(12, len(words) // 3 + 1)):
            for i in range(len(words) - 3 * span + 1):
                c1 = " ".join(words[i : i + span]).lower()
                c2 = " ".join(words[i + span : i + 2 * span]).lower()
                c3 = " ".join(words[i + 2 * span : i + 3 * span]).lower()
                if c1 == c2 == c3:
                    return True

    return False


def contains_leak_signature(text: str) -> bool:
    """Checks whether text contains internal harness tokens, drafting, or repetition loops.

    Ordinary user conversations discussing WhatsApp rate limits, slang, or technical
    architecture will NOT trigger this check.
    """
    if contains_internal_drafting(text):
        return True

    if has_repetition_loop(text):
        return True

    normalized = normalize_for_inspection(text)

    # 1. Unambiguous internal harness directive
    if RE_VERY_FIRST.search(normalized):
        return True

    # 2. WhatsApp environment harness declaration
    if RE_WHATSAPP_ENV.search(normalized):
        return True

    # 3. System Note combination matching
    if RE_SYSTEM_NOTE.search(normalized):
        if (
            "whatsapp" in normalized.lower()
            or RE_STOP_SENDING.search(normalized)
            or RE_RATE_LIMIT_INSTRUCTION.search(normalized)
            or "tool result" in normalized.lower()
        ):
            return True

    # 4. Rate-limit instruction accompanied by message stopping directive
    if RE_STOP_SENDING.search(normalized) and RE_RATE_LIMIT_INSTRUCTION.search(normalized):
        return True

    return False


def sanitize_outbound_text(text: str) -> tuple[str, bool]:
    """Sanitizes a single outbound string.

    Returns:
        (clean_text, is_clean): tuple containing the text to send and a boolean flag.
    """
    if contains_leak_signature(text):
        digest = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]
        logger.warning("outbound_leak_blocked: hash=%s length=%d", digest, len(text))
        return SAFE_FALLBACK_REPLY, False
    return text, True


def sanitize_relay_events(events: list[dict]) -> tuple[str, bool]:
    """Extracts, collapses, and sanitizes text events from opencode execution JSON lines."""
    raw_texts = [
        e.get("part", {}).get("text", "")
        for e in events
        if e.get("type") == "text" and isinstance(e.get("part"), dict)
    ]
    collapsed = collapse_adjacent_duplicate_texts(raw_texts)
    combined = "\n".join(collapsed).strip()

    if not combined:
        return "", True

    return sanitize_outbound_text(combined)
