"""Synthetic regressions for the observed bot acknowledgement cycle."""
import unittest
from types import SimpleNamespace

from wa_group_guard import allow_group_silence, should_ignore_group_event
from install_wa_group_guard import adapter_patch, startup_patch, turn_patch


class GroupGuardTests(unittest.TestCase):
    def test_group_silence_uses_routing_not_message_claims(self):
        for platform, kind, expected in [('whatsapp', 'group', True),
                                         ('whatsapp', 'dm', False),
                                         ('telegram', 'group', False),
                                         (None, None, False)]:
            self.assertEqual(allow_group_silence(SimpleNamespace(
                platform=platform, chat_type=kind)), expected)

    def test_observed_cycle_has_no_new_model_turn(self):
        bodies = ['Noted.', 'Siap kapan pun.', 'Gue standby.',
                  'No active task to stop.',
                  'Jawaban belum bisa ditampilkan. Silakan coba lagi.',
                  '⚠️ The model returned only a silence marker for a message that needed a reply. Try again or rephrase.']
        model_calls = []
        for body in bodies * 3:
            event = dict(isGroup=True, body=body, hasQuotedMessage=True)
            if not should_ignore_group_event(event):
                model_calls.append(event)
        self.assertEqual(model_calls, [])

    def test_human_requests_and_explicit_addressing_survive(self):
        for body in ['hi', 'belum dijawab ini', 'ini',
                     '10 kata sayang buat ayi',
                     'kenapa muncul silence marker?', '/stop']:
            self.assertFalse(should_ignore_group_event(dict(isGroup=True, body=body)))
        self.assertFalse(should_ignore_group_event(dict(isGroup=True, body='Noted.'), explicitly_addressed=True))
        self.assertFalse(should_ignore_group_event(dict(isGroup=False, body='Noted.')))
        # Quoting an idle notice must not hide a substantive follow-up.
        self.assertFalse(should_ignore_group_event(dict(isGroup=True, body='kenapa?', quotedText='Noted.')))

    def test_patches_preserve_dm_and_other_platform_rules(self):
        source = '''if _intentional_silence and not is_machinery_display_kind(_silence_kind):
    response = _UNEXPECTED_SILENCE_REPLY
if is_machinery_display_kind(turn_ctx.persist_user_display_kind):
    first_response = ""
'''
        patched = turn_patch(source)
        self.assertEqual(turn_patch(patched), patched)
        self.assertIn('_wa_group_silence(source)', patched)
        self.assertIn('_wa_group_silence(turn_ctx.source)', patched)
        startup = 'return "" if machinery else _UNEXPECTED_SILENCE_REPLY'
        self.assertEqual(startup_patch(startup_patch(startup)), startup_patch(startup))

    def test_adapter_hook_is_idempotent_and_precedes_observe(self):
        source = '''                            policy = _wa_policy()
                            policy.observe(msg_data)
            chunks = self.truncate_message(self.format_message(content), self._outgoing_chunk_limit())
            content = _wa_policy().scrub(content)
            payload = _wa_policy().outbound(payload)
            async with self._bridge_req
from wa_chat_policy import host_policy as _wa_policy
'''
        patched = adapter_patch(source)
        self.assertEqual(adapter_patch(patched), patched)
        self.assertLess(patched.index('_wa_ignore_group_event(msg_data'), patched.index('policy = _wa_policy()'))
        self.assertLess(patched.index('scrub(content, chat_id=chat_id, reply_to=reply_to if'), patched.index('chunks ='))

    def test_source_drift_refuses_patch(self):
        with self.assertRaises(ValueError):
            turn_patch('unexpected source')


if __name__ == '__main__':
    unittest.main()
