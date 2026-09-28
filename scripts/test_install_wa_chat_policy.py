"""Exercise the generated bridge intake hook with synthetic host state."""
import json
import shutil
import subprocess
import unittest

from install_wa_chat_policy import bridge_patch


@unittest.skipUnless(shutil.which('node'), 'Node is required for bridge hook tests')
class BridgeHookTests(unittest.TestCase):
    def test_intake_alias_and_fail_closed_matrix(self):
        fixture = """
const ALLOWED_USERS = parseAllowedUsers(process.env.WHATSAPP_ALLOWED_USERS || '');
const GROUP_ALLOWED_USERS = parseAllowedUsers(process.env.WHATSAPP_GROUP_ALLOWED_USERS || '');
        const intakeAllowed = isGroup
          ? matchesInboundWhatsAppGroup({chatId, groupPolicy: WHATSAPP_GROUP_POLICY,
              groupAllowedUsers: GROUP_ALLOWED_USERS, sessionDir: SESSION_DIR})
          : WHATSAPP_DM_POLICY === 'pairing'
            || matchesAllowedSender(senderId, senderAltId, ALLOWED_USERS, SESSION_DIR);
"""
        patched = bridge_patch(fixture)
        self.assertEqual(bridge_patch(patched), patched)
        harness = r"""
const vm = require('node:vm');
const assert = require('node:assert/strict');
const patch = PATCH;
function allowed({ sender = '10000002@lid', alias = '', group = false, broken = false,
                   owners = '10000001', people = '', groups = '' } = {}) {
  const context = {
    process: {env: {HOME: '/synthetic'}}, path: require('node:path'), SESSION_DIR: '/synthetic/session',
    senderId: sender, senderAltId: alias, isGroup: group, chatId: '10000000001@g.us',
    WHATSAPP_GROUP_POLICY: 'allowlist', WHATSAPP_DM_POLICY: 'allowlist',
    readFileSync: () => {
      if (broken) throw new Error('synthetic read failure');
      return `NAQUUUU_WA_OWNER_IDS=${owners}\nWHATSAPP_ALLOWED_USERS=${people}\nWHATSAPP_GROUP_ALLOWED_USERS=${groups}`;
    },
    parseAllowedUsers: raw => new Set(raw.split(',').filter(Boolean)),
    matchesInboundWhatsAppGroup: ({chatId, groupAllowedUsers}) => groupAllowedUsers.has(chatId),
    matchesAllowedSender: (id, alt, list) => list.has(id) || list.has(alt),
  };
  return vm.runInNewContext(patch + '\nintakeAllowed', context);
}
assert.equal(allowed(), false);
assert.equal(allowed({broken: true}), false);
assert.equal(allowed({group: true, broken: true}), false);
assert.equal(allowed({group: true, alias: '10000001@s.whatsapp.net'}), true);
assert.equal(allowed({group: true, alias: 'claimed 10000001'}), false);
assert.equal(allowed({group: true, alias: '10000001@s.whatsapp.net', owners: '*'}), false);
assert.equal(allowed({people: '10000002@lid'}), true);
assert.equal(allowed({group: true, groups: '10000000001@g.us'}), true);
console.log('bridge intake matrix PASS');
""".replace('PATCH', json.dumps(patched))
        result = subprocess.run(['node', '-e', harness], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
