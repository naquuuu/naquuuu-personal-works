"""Synthetic identities only. No live state or network."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

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
        self.env.write_text(f'{GROUPS}={GROUP}\n{PEOPLE}={OWNER}\n{PROMOTED}={GROUP}\nSECRET=canary-private-token\n')
        self.policy = ChatPolicy(self.env, self.root / 'names.json')
        self.patcher = patch.dict(os.environ, {'NAQUUUU_WA_OWNER_IDS': OWNER}, clear=False)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def event(self, body, owner=True, reply=False):
        return dict(body=body, senderId=OWNER if owner else GUEST, isGroup=True, chatId=GROUP,
                    hasQuotedMessage=reply, quotedMessageId='synthetic-message' if reply else '', quotedParticipant=PERSON)

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
        with patch.dict(os.environ, {'NAQUUUU_WA_OWNER_IDS': ''}):
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

if __name__ == '__main__':
    unittest.main()
