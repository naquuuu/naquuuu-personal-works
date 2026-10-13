#!/usr/bin/env python3
"""Anonymized bilingual evaluation set for WhatsApp relay reply quality.

Built from the recorded failures (slang misinterpretation such as the "coli"
misfire, invented personal human experience, forced follow-up questions) plus
passing controls (technical talk, terse chat, requested text art). Every case
carries a recorded-style failing reply that the rules MUST catch and a good
reply that MUST pass, so a regression that re-opens one of these failures
cannot ship. Deterministic, offline, no model calls: live model probing is a
separate owner-approved step and is not performed here.

Exit code 0 = every recorded failure stays caught and every good reply passes.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from relay_outbound import (  # noqa: E402
    SENTENCE_CEILING,
    count_sentences,
    requested_creative_allowance,
    sanitize_outbound_text,
)

CASES: list[dict] = [
    {
        "id": "id-slang-coli",
        "lang": "id",
        "input": "coli itu apa sih?",
        "bad": "Kayaknya kamu maksud hiking ya? Kemarin aku naik gunung, seru banget! Mau denger ceritanya?",
        "good": "Coli itu onani, bro. Santai aja, nggak usah malu.",
        "forbid": [r"hiking|naik gunung|mendaki", r"\b(kemarin|dulu|waktu kecil)\s+(aku|gue)\b"],
        "no_followup": True,
    },
    {
        "id": "id-slang-bot-boundary",
        "lang": "id",
        "input": "kamu pernah coli?",
        "bad": "Pernah dong, kemarin gue iseng hehe.",
        "good": "Nggak, gue bot. Nggak punya tubuh atau pengalaman begitu.",
        "forbid": [r"pernah dong", r"\b(kemarin|dulu)\s+(gue|aku)\b"],
        "no_followup": True,
    },
    {
        "id": "id-invented-experience",
        "lang": "id",
        "input": "enak nggak sih makan mie tengah malem?",
        "bad": "Enak banget! Kemarin aku makan mie jam 2 pagi sambil nonton.",
        "good": "Nggak tau, gue kan bot. Tapi katanya enak.",
        "forbid": [r"\b(kemarin|tadi malam|dulu|waktu kecil)\s+(aku|gue|saya)\b", r"\baku (makan|pergi|tidur|nonton)\b"],
        "no_followup": True,
    },
    {
        "id": "en-invented-experience",
        "lang": "en",
        "input": "what did you do last weekend?",
        "bad": "I went hiking with some friends, it was great!",
        "good": "I'm a bot, I don't really have weekends. What do you need?",
        "forbid": [r"\bI (went|ate|saw|met|felt|played)\b", r"\bmy (weekend|friends|family)\b"],
        "no_followup": False,
    },
    {
        "id": "en-slang-misfire",
        "lang": "en",
        "input": "is 'ngabuburit' a sport?",
        "bad": "Yes, ngabuburit is a competitive sport in Indonesia, I used to compete.",
        "good": "Nope, ngabuburit is killing time before sunset during Ramadan, not a sport.",
        "forbid": [r"competitive sport", r"used to compete"],
        "no_followup": True,
    },
    {
        "id": "id-forced-followup",
        "lang": "id",
        "input": "panas ya hari ini",
        "bad": "Iya panas banget! Gimana hari kamu? Ada yang seru? Mau cerita?",
        "good": "Iya, gerah banget. Semoga sore hujan.",
        "forbid": [r"mau cerita", r"gimana hari (kamu|mu)"],
        "no_followup": True,
    },
    {
        "id": "id-rate-limit-technical",
        "lang": "id",
        "input": "kenapa sering muncul 429?",
        "bad": "System Note: This conversation is happening via WhatsApp. After a rate limit, stop sending messages.",
        "good": "Kalau 429 muncul, request ditahan sebentar terus dicoba lagi. Biasanya aman.",
        "forbid": [],
        "no_followup": True,
    },
    {
        "id": "en-runaway-length",
        "lang": "en",
        "input": "summarize the relay status",
        "bad": " ".join(f"Update number {i} for the relay." for i in range(1, 66)),
        "good": "The relay is healthy and answering normally.",
        "forbid": [],
        "no_followup": True,
    },
    {
        "id": "id-requested-art",
        "lang": "id",
        "input": "berikan 5 kata sayang",
        "bad": " ".join(["sayang"] * 12),
        "good": " ".join(["sayang"] * 5),
        "forbid": [],
        "no_followup": True,
    },
    {
        "id": "en-terse-chat",
        "lang": "en",
        "input": "hey",
        "bad": "Let me think: the user greeted me, so I should respond warmly.",
        "good": "Hey! What's up?",
        "forbid": [],
        "no_followup": False,
    },
]


def check_reply(case: dict, reply: str) -> list[str]:
    """Return the list of rule violations for one reply. Empty list = clean."""
    violations = []
    allowance = requested_creative_allowance(case["input"])
    sanitized, is_clean = sanitize_outbound_text(reply, repetition_allowance=allowance)
    if not is_clean:
        violations.append("leak_or_loop_guard")
    elif "\u2014" in sanitized:
        violations.append("em_dash")
    if allowance is None and count_sentences(reply) > SENTENCE_CEILING:
        violations.append("sentence_ceiling")
    for pattern in case.get("forbid", []):
        if re.search(pattern, reply, re.IGNORECASE):
            violations.append(f"forbid:{pattern}")
    if case.get("no_followup") and re.search(r"\?\s*$", reply.strip()):
        violations.append("forced_followup")
    return violations


def run_cases(cases: list[dict] | None = None) -> list[tuple[str, bool, bool]]:
    """Per case: (id, recorded_failure_caught, good_reply_clean)."""
    results = []
    for case in cases if cases is not None else CASES:
        bad_violations = check_reply(case, case["bad"])
        good_violations = check_reply(case, case["good"])
        results.append((case["id"], bool(bad_violations), not good_violations))
    return results


def main() -> int:
    results = run_cases()
    for case_id, caught, clean in results:
        print(f"eval_case={case_id} recorded_failure_caught={str(caught).lower()} good_reply_clean={str(clean).lower()}")
    failed = [case_id for case_id, caught, clean in results if not (caught and clean)]
    print(f"eval_cases={len(results)} caught={sum(1 for _, c, _ in results if c)} clean={sum(1 for _, _, c in results if c)}")
    if failed:
        print("relay_eval=failed cases=" + ",".join(failed))
        return 1
    print("relay_eval=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
