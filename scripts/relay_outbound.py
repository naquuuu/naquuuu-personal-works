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
RE_ART_WORDS = re.compile(r"\b(?:ascii?|asci|text)\s*(?:text\s*)?art\b", re.IGNORECASE)
RE_REQUEST_VERB = re.compile(r"\b(?:draw|make|create|write|show|generate|give|provide|say|repeat|type|buat|bikin|berikan|beri|gambar|tulis|ucapkan|bilang)\b", re.IGNORECASE)
RE_EN_AFFECTION_REQUEST = re.compile(
    r"\b(?:say|write|repeat|type|tulis|ucapkan|bilang)\b\s*[\"'“”]?\s*(i\s+love\s+you|love\s+you|i\s+love\s+u|sayang(?:\s+you)?|aku\s+cinta\s+kamu|cinta\s+kamu)[\"'“”]?\s+(\d{1,3})\s+times?\b",
    re.IGNORECASE,
)
RE_COUNTED_WORD = re.compile(r"\b(?P<count>\d{1,6})\s+kata\s+(?P<phrase>sayang|cinta|kasih(?:\s+sayang)?)\b", re.IGNORECASE)
RE_LEADING_ID_AFFECTION = re.compile(r"^\s*(\d{1,6})\s+kata\s+(sayang|cinta|kasih(?:\s+sayang)?)\s+(?:deh|dong|ya)\b", re.IGNORECASE)
RE_FOLLOWUP = re.compile(r"^(?:do that|make that|draw that|write that|say that|repeat that|show that|create that|do it|the same|please|yes|ini|itu|lanjutkan|yang tadi|itu saja|iya)[.!? ]*$", re.IGNORECASE)
RE_REPEAT_ONLY = re.compile(r"^[\W_]*$", re.UNICODE)


def _without_bot_mention(text: str) -> str:
    """Remove only the known textual bot mention; preserve numeric/JID identifiers."""
    return re.sub(r"(?i)(?<!\w)@naquuuubot\b", " ", text)


def _direct_creative_allowance(text: str) -> dict | None:
    direct = _without_bot_mention(text).strip()
    count_word = RE_COUNTED_WORD.search(direct)
    leading_affection = RE_LEADING_ID_AFFECTION.search(direct)
    affection = RE_EN_AFFECTION_REQUEST.search(direct)
    phrase = None
    count = None
    if count_word:
        prefix = direct[:count_word.start()]
        if RE_REQUEST_VERB.search(prefix) or leading_affection:
            count, phrase = int(count_word.group("count")), " ".join(count_word.group("phrase").lower().split())
    elif affection:
        count, phrase = int(affection.group(2)), " ".join(affection.group(1).lower().split())

    if phrase and count and 3 <= count <= 100:
        if RE_ART_WORDS.search(direct):
            return {"kind": "art", "phrase": phrase, "max_chars": 3600, "max_lines": 100, "max_repeats": count}
        return {"kind": "phrase", "phrase": phrase, "max_repeats": count, "max_chars": 3600}
    if count_word or leading_affection:
        return None

    if RE_ART_WORDS.search(direct) and RE_REQUEST_VERB.search(direct):
        return {"kind": "art", "max_chars": 3600, "max_lines": 100, "max_repeats": 100}
    return None


def requested_creative_allowance(request: str, quoted_text: str = "") -> dict | None:
    """Recognize explicit bounded requests; quotes need a current-message referral."""
    allowance = _direct_creative_allowance(request)
    if allowance:
        return allowance
    current = _without_bot_mention(request).strip().strip(" \t\r\n.,!?;:").lower()
    if RE_FOLLOWUP.fullmatch(current):
        # Quoted text is a source request only when it independently matches the
        # explicit request grammar. An arbitrary quote cannot create permission.
        return _direct_creative_allowance(quoted_text)
    return None


def _repetition_within_allowance(text: str, allowance: dict | None) -> bool:
    if not isinstance(allowance, dict) or len(text) > int(allowance.get("max_chars", 0)):
        return False
    if allowance.get("kind") == "phrase":
        phrase = str(allowance.get("phrase") or "")
        if not phrase:
            return False
        pattern = re.compile(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", re.IGNORECASE)
        matches = list(pattern.finditer(text))
        if not 3 <= len(matches) <= int(allowance.get("max_repeats", 0)):
            return False
        residue = pattern.sub("", text)
        return bool(RE_REPEAT_ONLY.fullmatch(residue))
    if allowance.get("kind") == "art":
        phrase = str(allowance.get("phrase") or "")
        if phrase and _phrase_repetition_matches(text, phrase, int(allowance.get("max_repeats", 0))):
            return True
        return _looks_like_ascii_art(text, int(allowance.get("max_lines", 0)))
    return False


def _phrase_repetition_matches(text: str, phrase: str, max_repeats: int) -> bool:
    text = re.sub(r"(?is)^\s*```(?:text|txt)?\s*|\s*```\s*$", "", text).strip()
    pattern = re.compile(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", re.IGNORECASE)
    matches = list(pattern.finditer(text))
    return 3 <= len(matches) <= max_repeats and bool(RE_REPEAT_ONLY.fullmatch(pattern.sub("", text)))


def _looks_like_ascii_art(text: str, max_lines: int) -> bool:
    unwrapped = re.sub(r"(?m)^\s*```(?:text|txt)?\s*$|^\s*```\s*$", "", text).strip()
    lines = [line for line in unwrapped.splitlines() if line.strip()]
    if not 3 <= len(lines) <= max_lines:
        return False
    compact = "".join(c for c in unwrapped if not c.isspace())
    if not compact:
        return False
    symbol_count = sum(not c.isalnum() for c in compact)
    if symbol_count / len(compact) < 0.35:
        return False
    # Reject sentence-like lines even if they contain occasional drawing marks.
    words = re.findall(r"[A-Za-z]{3,}", unwrapped)
    if len(words) > 8:
        return False
    return True


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


def contains_leak_signature(text: str, *, repetition_allowance: dict | None = None) -> bool:
    """Checks whether text contains internal harness tokens, drafting, or repetition loops.

    Ordinary user conversations discussing WhatsApp rate limits, slang, or technical
    architecture will NOT trigger this check.
    """
    if contains_internal_drafting(text):
        return True

    if has_repetition_loop(text) and not _repetition_within_allowance(text, repetition_allowance):
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


def sanitize_outbound_text(text: str, *, repetition_allowance: dict | None = None) -> tuple[str, bool]:
    """Sanitizes a single outbound string.

    Returns:
        (clean_text, is_clean): tuple containing the text to send and a boolean flag.
    """
    if contains_leak_signature(text, repetition_allowance=repetition_allowance):
        digest = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]
        logger.warning("outbound_leak_blocked: hash=%s length=%d", digest, len(text))
        return SAFE_FALLBACK_REPLY, False
    return text, True


def sanitize_relay_events(events: list[dict], *, repetition_allowance: dict | None = None) -> tuple[str, bool]:
    """Extracts, collapses, and sanitizes text events from opencode execution JSON lines."""
    # Tool-step narration is not the final answer. Keep text after the last tool
    # event, then use the last assistant message identity when metadata exists.
    last_tool = max((i for i, event in enumerate(events)
                     if event.get('type') == 'tool_use'), default=-1)
    visible = [event for event in events[last_tool + 1:]
               if event.get('type') == 'text' and isinstance(event.get('part'), dict)]
    def message_id(event: dict):
        return event.get('part', {}).get('messageID') or event.get('messageID')
    final_message = next((message_id(event) for event in reversed(visible)
                          if message_id(event)), None)
    if final_message:
        visible = [event for event in visible if message_id(event) == final_message]
    raw_texts = [
        e.get("part", {}).get("text", "")
        for e in visible
        if isinstance(e.get('part', {}).get('text'), str)
    ]
    collapsed = collapse_adjacent_duplicate_texts(raw_texts)
    combined = "\n".join(collapsed).strip()

    if not combined:
        return "", True

    return sanitize_outbound_text(combined, repetition_allowance=repetition_allowance)
