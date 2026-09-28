"""Unit tests for outbound WhatsApp text sanitization, drafting leak prevention, and repetition guard."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import unittest
from unittest.mock import patch

from relay_outbound import (
    SAFE_FALLBACK_REPLY,
    collapse_adjacent_duplicate_texts,
    contains_internal_drafting,
    contains_leak_signature,
    has_repetition_loop,
    sanitize_outbound_text,
    sanitize_relay_events,
)


class OutboundSanitizationTests(unittest.TestCase):
    def test_clean_text_passes_unchanged(self):
        sample = "Tugas selesai. Hasil perubahan telah disimpan ke file tujuan."
        sanitized, is_clean = sanitize_outbound_text(sample)
        self.assertTrue(is_clean)
        self.assertEqual(sanitized, sample)

    def test_collapse_adjacent_duplicate_texts(self):
        chunks = [
            "Halo!",
            "Halo!",
            "   Halo!   ",
            "Ada yang bisa dibantu?",
            "Ada yang bisa dibantu?",
            "",
            "   ",
            "Selesai.",
        ]
        collapsed = collapse_adjacent_duplicate_texts(chunks)
        self.assertEqual(collapsed, ["Halo!", "Ada yang bisa dibantu?", "Selesai."])

    def test_exact_screenshot_note_rejected(self):
        screenshot_payload = (
            "System Note: This conversation is happening via WhatsApp. "
            "Please ensure you review the VERY FIRST TOOL RESULT before answering. "
            "If you hit a rate limit, stop sending messages immediately."
        )
        self.assertTrue(contains_leak_signature(screenshot_payload))
        sanitized, is_clean = sanitize_outbound_text(screenshot_payload)
        self.assertFalse(is_clean)
        self.assertEqual(sanitized, SAFE_FALLBACK_REPLY)
        self.assertNotIn("System Note", sanitized)
        self.assertNotIn("VERY FIRST TOOL RESULT", sanitized)
        self.assertNotIn("WhatsApp", sanitized)

    def test_think_tags_rejected(self):
        closed_think = "<think>The user is asking a casual question. Let me reply in Indonesian.</think>Nggak, gue bot."
        self.assertTrue(contains_internal_drafting(closed_think))
        sanitized, is_clean = sanitize_outbound_text(closed_think)
        self.assertFalse(is_clean)
        self.assertEqual(sanitized, SAFE_FALLBACK_REPLY)

        unclosed_think = "<think>\nLet me ponder this task further..."
        self.assertTrue(contains_internal_drafting(unclosed_think))
        sanitized, is_clean = sanitize_outbound_text(unclosed_think)
        self.assertFalse(is_clean)
        self.assertEqual(sanitized, SAFE_FALLBACK_REPLY)

    def test_draft_prefixes_rejected(self):
        draft_payload = "Thought: I should check whether 'coli' means hiking or not.\nDraft 1: Mungkin maksudnya naik gunung."
        self.assertTrue(contains_internal_drafting(draft_payload))
        sanitized, is_clean = sanitize_outbound_text(draft_payload)
        self.assertFalse(is_clean)
        self.assertEqual(sanitized, SAFE_FALLBACK_REPLY)

    def test_repetition_loop_flood_rejected(self):
        # Repetition of sentences (3 or more times)
        looped_sentences = (
            "Saya akan memeriksa status sistem sekarang. "
            "Saya akan memeriksa status sistem sekarang. "
            "Saya akan memeriksa status sistem sekarang."
        )
        self.assertTrue(has_repetition_loop(looped_sentences))
        sanitized, is_clean = sanitize_outbound_text(looped_sentences)
        self.assertFalse(is_clean)
        self.assertEqual(sanitized, SAFE_FALLBACK_REPLY)

        # Repetition of word n-grams
        looped_ngrams = "coba cek lagi nanti ya coba cek lagi nanti ya coba cek lagi nanti ya"
        self.assertTrue(has_repetition_loop(looped_ngrams))
        sanitized, is_clean = sanitize_outbound_text(looped_ngrams)
        self.assertFalse(is_clean)
        self.assertEqual(sanitized, SAFE_FALLBACK_REPLY)

    def test_repeated_notes_rejected(self):
        payload = (
            "System Note: This conversation is happening via WhatsApp.\n\n"
            "System Note: This conversation is happening via WhatsApp.\n\n"
            "System Note: inspect VERY FIRST TOOL RESULT."
        )
        self.assertTrue(contains_leak_signature(payload))
        sanitized, is_clean = sanitize_outbound_text(payload)
        self.assertFalse(is_clean)
        self.assertEqual(sanitized, SAFE_FALLBACK_REPLY)

    def test_contaminated_text_after_clean_prefix_rejected(self):
        payload = (
            "Berikut ringkasan perubahan yang sudah dibuat:\n"
            "1. Menambahkan guard pada adapter.\n"
            "System Note: This conversation is happening via WhatsApp."
        )
        self.assertTrue(contains_leak_signature(payload))
        sanitized, is_clean = sanitize_outbound_text(payload)
        self.assertFalse(is_clean)
        self.assertEqual(sanitized, SAFE_FALLBACK_REPLY)

    def test_ordinary_rate_limit_discussion_passes(self):
        discussion = (
            "Untuk menangani rate limit pada integrasi WhatsApp, terapkan backoff eksponensial "
            "dan antrean pesan. Jangan mengirim pesan secara bersamaan dalam volume tinggi."
        )
        self.assertFalse(contains_leak_signature(discussion))
        sanitized, is_clean = sanitize_outbound_text(discussion)
        self.assertTrue(is_clean)
        self.assertEqual(sanitized, discussion)

    def test_casual_slang_discussion_passes(self):
        # Legitimate persona answer explaining slang or clarifying bot nature
        clean_slang_reply = "Nggak, gue bot—nggak punya tubuh atau pengalaman begitu."
        self.assertFalse(contains_leak_signature(clean_slang_reply))
        sanitized, is_clean = sanitize_outbound_text(clean_slang_reply)
        self.assertTrue(is_clean)
        self.assertEqual(sanitized, clean_slang_reply)

    def test_observability_hashes_without_raw_text(self):
        dirty = "System Note: inspect VERY FIRST TOOL RESULT and stop sending messages after a rate limit."
        with patch("relay_outbound.logger.warning") as mock_log:
            sanitized, is_clean = sanitize_outbound_text(dirty)
            self.assertFalse(is_clean)
            self.assertTrue(mock_log.called)
            args = mock_log.call_args[0]
            fmt = args[0]
            params = args[1:]
            self.assertIn("outbound_leak_blocked", fmt)
            for p in params:
                self.assertNotIn("System Note", str(p))
                self.assertNotIn("VERY FIRST", str(p))

    def test_sanitize_relay_events(self):
        clean_events = [
            {"type": "text", "part": {"text": "Baris satu"}},
            {"type": "text", "part": {"text": "Baris satu"}},
            {"type": "text", "part": {"text": "Baris dua"}},
        ]
        result, is_clean = sanitize_relay_events(clean_events)
        self.assertTrue(is_clean)
        self.assertEqual(result, "Baris satu\nBaris dua")

        dirty_events = [
            {"type": "text", "part": {"text": "Jawaban awal."}},
            {"type": "text", "part": {"text": "System Note: This conversation is happening via WhatsApp."}},
        ]
        result, is_clean = sanitize_relay_events(dirty_events)
        self.assertFalse(is_clean)
        self.assertEqual(result, SAFE_FALLBACK_REPLY)


if __name__ == "__main__":
    unittest.main()
