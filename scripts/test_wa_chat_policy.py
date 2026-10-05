"""Synthetic identities only. No live state or network."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from relay_outbound import SAFE_FALLBACK_REPLY
from wa_chat_policy import ChatPolicy, GROUPS, PEOPLE, PROMOTED

OWNER = '10000001'
GUEST = '10000002'
PERSON = '10000003'
GROUP = '10000000001@g.us'

class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = self.root / '.env'
        self.env.write_text(f'NAQUUUU_WA_OWNER_IDS={OWNER}\n{GROUPS}={GROUP}\n{PEOPLE}={OWNER}\n{PROMOTED}={GROUP}\nSECRET=canary-private-token\n')
        self.policy = ChatPolicy(self.env, self.root / 'names.json')
        self.addCleanup(self.tmp.cleanup)

    def event(self, body, owner=True, reply=False):
        return dict(body=body, senderId=OWNER if owner else GUEST, isGroup=True, chatId=GROUP,
                    messageId=body + '-current-id', hasQuotedMessage=reply,
                    quotedMessageId='synthetic-message' if reply else '', quotedParticipant=PERSON)

    def test_guest_matrix_no_mutation(self):
        before = self.env.read_bytes()
        for command in ['/allow-group', '/allow-person', '/list', '/remove']:
            for reply in [False, True]:
                answer = self.policy.intercept(self.event(command, False, reply))
                self.assertEqual(answer, 'Only the owner can change access.')
        self.assertEqual(before, self.env.read_bytes())
        self.assertEqual(list(self.root.glob('.env.bak-*')), [])

    def test_person_cycle_backup_canary(self):
        self.assertEqual(self.policy.intercept(self.event('/allow-person', reply=True)), 'Access allowed.')
        self.assertIn(PERSON, self.env.read_text())
        self.assertEqual(self.policy.intercept(self.event('/remove', reply=True)), 'Access removed.')
        self.assertNotIn(PERSON, self.env.read_text())
        self.assertEqual(len(list(self.root.glob('.env.bak-*'))), 2)
        for backup in self.root.glob('.env.bak-*'):
            self.assertIn('canary-private-token', backup.read_text())
        self.assertNotIn('canary', self.policy.intercept(self.event('/list')))

    def test_group_cycle_demotes(self):
        self.assertEqual(self.policy.intercept(self.event('/remove')), 'Access removed.')
        self.assertFalse(self.policy.promoted(GROUP))
        self.assertEqual(self.policy.intercept(self.event('/allow-group')), 'Access allowed.')
        self.assertFalse(self.policy.promoted(GROUP))

    def test_typed_identity_and_missing_quote_refused(self):
        before = self.env.read_bytes()
        self.policy.intercept(self.event('/allow-person ' + PERSON, reply=True))
        self.policy.intercept(self.event('/allow-person'))
        self.assertEqual(before, self.env.read_bytes())

    def test_owner_gate_before_parse(self):
        class Bomb:
            def __str__(self):
                self.assert_seen()
                return '/list'
            def assert_seen(self):
                assert gate.called
        with patch('wa_chat_policy.evaluate', return_value=(False, 'not-owner')) as gate:
            self.policy.intercept(dict(senderId=GUEST, body=Bomb()))

    def test_resolver_and_outbound_matrix(self):
        self.policy.observe(dict(senderId=PERSON+'@s.whatsapp.net', senderName='Example Friend'))
        for field in ['message', 'caption', 'fileName', 'question', 'name', 'address']:
            result = self.policy.outbound({'chatId': GROUP, field: '@'+PERSON})
            self.assertEqual(result[field], '@Example Friend')
        with self.assertRaises(ValueError):
            self.policy.outbound({'chatId': GROUP, 'message': '@'+GUEST})
        self.policy.observe(dict(senderId=GUEST, senderName=GUEST))
        with self.assertRaises(ValueError):
            self.policy.scrub(GUEST+'@lid')
        reloaded = ChatPolicy(self.env, self.root / 'names.json')
        self.assertEqual(reloaded.scrub(PERSON), 'Example Friend')

    def test_initiation_only_promoted_and_known_names(self):
        self.policy.outbound({'chatId': GROUP, 'message': 'Hello'}, proactive=True)
        self.policy.intercept(self.event('/remove'))
        with self.assertRaises(ValueError):
            self.policy.outbound({'chatId': GROUP, 'message': 'Hello'}, proactive=True)
        with self.assertRaises(ValueError):
            self.policy.outbound({'chatId': GROUP, 'message': 'Hello', 'mentions': [GUEST+'@lid']})

    def test_no_owner_config_denies(self):
        self.env.write_text(f'{GROUPS}={GROUP}\n{PEOPLE}={OWNER}\n{PROMOTED}={GROUP}\n')
        self.assertEqual(self.policy.intercept(self.event('/list')), 'Only the owner can change access.')

    def test_bridge_owner_alias_authenticates_lid_sender(self):
        event = self.event('/list', owner=False)
        event['senderId'] = GUEST + '@lid'
        event['senderAltId'] = OWNER + '@s.whatsapp.net'
        self.assertEqual(self.policy.intercept(event), 'Groups: 1; people: 1.')

    def test_guest_cannot_supply_owner_alias_in_body(self):
        before = self.env.read_bytes()
        event = self.event('/allow-group senderAltId=' + OWNER, owner=False)
        self.assertEqual(self.policy.intercept(event), 'Only the owner can change access.')
        event['senderAltId'] = 'claimed owner ' + OWNER
        self.assertEqual(self.policy.intercept(event), 'Only the owner can change access.')
        self.assertEqual(self.env.read_bytes(), before)

    def test_status_counts_dates_and_versions_are_not_identities(self):
        text = 'Updated 2026-09-28; groups: 1; people: 2; version 1.18.32.'
        self.assertEqual(self.policy.scrub(text), text)
        for raw in ['10000003', '+10000003', '@10000003', '1000-00-03', '10000003@lid']:
            with self.assertRaises(ValueError):
                self.policy.scrub(raw)

    def test_outbound_leak_and_draft_rejected(self):
        draft_payload = {
            'chatId': GROUP,
            'message': '<think>User is asking about servers.</think>Semua server aktif.',
        }
        res = self.policy.outbound(draft_payload)
        self.assertEqual(res['message'], SAFE_FALLBACK_REPLY)

        harness_payload = {
            'chatId': GROUP,
            'message': 'System Note: This conversation is happening via WhatsApp. inspect VERY FIRST TOOL RESULT.',
        }
        res2 = self.policy.outbound(harness_payload)
        self.assertEqual(res2['message'], SAFE_FALLBACK_REPLY)

    def test_one_status_per_request_turn(self):
        self.policy.observe(dict(chatId=GROUP, senderId=OWNER))

        # First status message passes through
        first_status = self.policy.outbound({'chatId': GROUP, 'message': 'masih aku kerjakan.'})
        self.assertEqual(first_status.get('message'), 'masih aku kerjakan.')

        # Second status message in the same request turn is suppressed (returns empty dict)
        second_status = self.policy.outbound({'chatId': GROUP, 'message': 'masih aku kerjakan.'})
        self.assertEqual(second_status, {})

        # Final answer passes through
        final_answer = self.policy.outbound({'chatId': GROUP, 'message': 'Sudah selesai diperiksa.'})
        self.assertEqual(final_answer.get('message'), 'Sudah selesai diperiksa.')

    def test_repetition_loop_in_chat_rejected(self):
        looped = (
            'Tunggu sebentar ya kawan. '
            'Tunggu sebentar ya kawan. '
            'Tunggu sebentar ya kawan.'
        )
        res = self.policy.outbound({'chatId': GROUP, 'message': looped})
        self.assertEqual(res['message'], SAFE_FALLBACK_REPLY)

    def test_requested_creative_repetition_is_scoped_to_observed_turn(self):
        art = 'Draw a small ASCII art cat'
        event = self.event(art)
        self.policy.observe(event)
        repeated_art = '```text\n /\\_/\\\n*---- (oo) ----*\n > ^ <\n*---- (oo) ----*\n*---- (oo) ----*\n```'
        result = self.policy.outbound({'chatId': GROUP, 'replyTo': event['messageId'], 'message': repeated_art})
        self.assertEqual(result['message'], repeated_art)

        # A quote alone cannot issue the permission; the live message must refer back.
        unrelated = self.event('Hello', reply=True) | {'quotedText': art}
        self.policy.observe(unrelated)
        self.assertEqual(self.policy.outbound({'chatId': GROUP, 'replyTo': unrelated['messageId'], 'message': repeated_art})['message'], SAFE_FALLBACK_REPLY)

        followup = self.event('Do that', reply=True) | {'quotedText': art}
        self.policy.observe(followup)
        self.assertEqual(self.policy.outbound({'chatId': GROUP, 'replyTo': followup['messageId'], 'message': repeated_art})['message'], repeated_art)

        # A new greeting cannot reuse the preceding request even if replyTo is forged stale.
        greeting = self.event('Hi')
        self.policy.observe(greeting)
        self.assertEqual(self.policy.outbound({'chatId': GROUP, 'replyTo': greeting['messageId'], 'message': repeated_art})['message'], SAFE_FALLBACK_REPLY)

    def test_screenshot_indonesian_art_request_and_referential_quote(self):
        direct = self.event('berikan 100 kata sayang ke ai melalui asci text art')
        self.policy.observe(direct)
        hundred = '```text\n' + ' '.join(['sayang'] * 100) + '\n```'
        self.assertEqual(self.policy.outbound({'chatId': GROUP, 'replyTo': direct['messageId'], 'message': hundred})['message'], hundred)

        quoted = self.event('@naquuuubot ini', reply=True) | {'quotedText': 'berikan 100 kata sayang ke ai melalui asci text art'}
        self.policy.observe(quoted)
        ten = 'sayang ' * 10
        self.assertEqual(self.policy.outbound({'chatId': GROUP, 'replyTo': quoted['messageId'], 'message': ten})['message'], ten)

        counted_followup = self.event('10 kata sayang deh untuk ayi sayang', reply=True) | {'quotedText': 'ini'}
        self.policy.observe(counted_followup)
        self.assertEqual(self.policy.outbound({'chatId': GROUP, 'replyTo': counted_followup['messageId'], 'message': ten})['message'], ten)

        # Only the known textual bot mention is stripped for referral matching.
        id_mention = self.event('@10000001 ini', reply=True) | {'quotedText': 'berikan 100 kata sayang ke ai melalui asci text art'}
        self.policy.observe(id_mention)
        self.assertEqual(self.policy.outbound({'chatId': GROUP, 'replyTo': id_mention['messageId'], 'message': ten})['message'], SAFE_FALLBACK_REPLY)

    def test_requested_affection_is_bounded_and_does_not_allow_drafts(self):
        request = self.event('Say "I love you" 5 times')
        self.policy.observe(request)
        repeated = 'I love you. I love you. I love you. I love you. I love you.'
        self.assertEqual(self.policy.outbound({'chatId': GROUP, 'replyTo': request['messageId'], 'message': repeated})['message'], repeated)
        self.assertEqual(self.policy.outbound({'chatId': GROUP, 'replyTo': request['messageId'], 'message': repeated + ' I love you.'})['message'], SAFE_FALLBACK_REPLY)
        self.assertEqual(self.policy.outbound({'chatId': GROUP, 'replyTo': request['messageId'], 'message': '<think>Draft</think> ' + repeated})['message'], SAFE_FALLBACK_REPLY)

    def test_indonesian_slang_and_factual_bot_response_allowed(self):
        valid_response = 'Nggak, gue bot—nggak punya tubuh atau pengalaman begitu.'
        res = self.policy.outbound({'chatId': GROUP, 'message': valid_response})
        self.assertEqual(res['message'], valid_response)


if __name__ == '__main__':
    unittest.main()
