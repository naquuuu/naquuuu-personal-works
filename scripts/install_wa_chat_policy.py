"""Install reviewable relay policy hooks on the pinned Hermes checkout.

No service restart. Timestamped backups retained. Run after copying wa_chat_policy.py
and wa_owner_gate.py into the workspace scripts directory on the relay host.
"""
from __future__ import annotations
import argparse
import datetime as dt
from pathlib import Path
import py_compile
import shutil

MARKER = '# NAQUUUU_CHAT_POLICY_V1'


def one(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError('Pinned source mismatch; no patch written.')
    return text.replace(old, new, 1)


def adapter_patch(text: str) -> str:
    if MARKER in text:
        return text
    # Defer import until runtime to preserve future imports and plugin loading.
    text += '''\n\n# NAQUUUU_CHAT_POLICY_V1
from pathlib import Path as _PolicyPath
import sys as _policy_sys
_policy_root = os.environ.get("NAQUUUU_WORKSPACE")
if not _policy_root:
    raise RuntimeError("NAQUUUU_WORKSPACE is required for relay policy")
_policy_sys.path.insert(0, str(_PolicyPath(_policy_root) / "scripts"))
from wa_chat_policy import host_policy as _wa_policy
'''
    text = one(text, '                            event = await self._build_message_event(msg_data)', '''                            policy = _wa_policy()
                            policy.observe(msg_data)
                            answer = policy.intercept(msg_data)
                            if answer is not None:
                                self._allow_from = self._coerce_allow_list(os.environ.get("WHATSAPP_ALLOWED_USERS", ""))
                                self._group_allow_from = self._coerce_allow_list(os.environ.get("WHATSAPP_GROUP_ALLOWED_USERS", ""))
                                await self.send(str(msg_data.get("chatId") or ""), answer)
                                continue
                            event = await self._build_message_event(msg_data)''')
    text = one(text, '            async with self._bridge_req("post", path, timeout, json=payload) as resp:', '            payload = _wa_policy().outbound(payload)\n            if not payload:\n                return\n            async with self._bridge_req("post", path, timeout, json=payload) as resp:')
    text = one(text, '            async with self._bridge_req("post", "edit", 15, json={"chatId": to_whatsapp_jid(chat_id), "messageId": message_id, "message": content}) as resp:', '            content = _wa_policy().scrub(content)\n            async with self._bridge_req("post", "edit", 15, json={"chatId": to_whatsapp_jid(chat_id), "messageId": message_id, "message": content}) as resp:')
    text = one(text, '                url = f"http://localhost:{bridge_port}/{path}"', '                payload = _wa_policy().outbound(payload, proactive=True)\n                if not payload:\n                    return\n                url = f"http://localhost:{bridge_port}/{path}"')
    return text


def bridge_patch(text: str) -> str:
    marker = '// NAQUUUU_CHAT_POLICY_V1'
    if marker in text:
        return text
    text = one(text, "const ALLOWED_USERS = parseAllowedUsers(process.env.WHATSAPP_ALLOWED_USERS || '');", "let ALLOWED_USERS = parseAllowedUsers(process.env.WHATSAPP_ALLOWED_USERS || '');")
    text = one(text, "const GROUP_ALLOWED_USERS = parseAllowedUsers(process.env.WHATSAPP_GROUP_ALLOWED_USERS || '');", "let GROUP_ALLOWED_USERS = parseAllowedUsers(process.env.WHATSAPP_GROUP_ALLOWED_USERS || '');")
    anchor = '        const intakeAllowed = isGroup'
    text = one(text, anchor, r'''        // NAQUUUU_CHAT_POLICY_V1
        // Refresh host-only lists after authenticated Python command mutations.
        let policyOwners = [];
        try {
          const home = process.env.HERMES_HOME || path.dirname(SESSION_DIR);
          const envFile = process.env.HERMES_HOME
            ? path.join(home, '.env')
            : path.join(process.env.HOME, '.hermes', '.env');
          const envText = readFileSync(envFile, 'utf8');
          const values = {};
          for (const line of envText.split(/\r?\n/)) {
            const m = line.match(/^\s*(?:export\s+)?(WHATSAPP_ALLOWED_USERS|WHATSAPP_GROUP_ALLOWED_USERS|NAQUUUU_WA_OWNER_IDS)\s*=\s*(.*)$/);
            if (m) values[m[1]] = m[2].trim().replace(/^['"]|['"]$/g, '');
          }
          ALLOWED_USERS = parseAllowedUsers(values.WHATSAPP_ALLOWED_USERS || '');
          GROUP_ALLOWED_USERS = parseAllowedUsers(values.WHATSAPP_GROUP_ALLOWED_USERS || '');
          const candidates = (values.NAQUUUU_WA_OWNER_IDS || '').split(',').map(x => x.trim());
          if (!candidates.some(x => ['*', 'all', 'any', 'everyone', 'open'].includes(x.toLowerCase())))
            policyOwners = candidates.filter(x => /^\+?[0-9]+(@(s\.whatsapp\.net|lid))?$/.test(x)).map(x => x.replace(/\D/g, ''));
        } catch {
          ALLOWED_USERS = parseAllowedUsers('');
          GROUP_ALLOWED_USERS = parseAllowedUsers('');
        }
        // Owners may reach Python command interception even from a removed group.
        // Python still runs wa_owner_gate before parsing and normal message gates afterwards.
        const policyOwner = [senderId, senderAltId].some(identity =>
          typeof identity === 'string'
          && /^\+?[0-9]+(@(s\.whatsapp\.net|lid))?$/.test(identity)
          && policyOwners.includes(identity.replace(/\D/g, '')));
        const intakeAllowed = policyOwner || (isGroup''')
    text = one(text, '            || matchesAllowedSender(senderId, senderAltId, ALLOWED_USERS, SESSION_DIR);', '            || matchesAllowedSender(senderId, senderAltId, ALLOWED_USERS, SESSION_DIR));')
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--hermes-repo', type=Path, required=True)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    adapter = args.hermes_repo / 'plugins/platforms/whatsapp/adapter.py'
    bridge = args.hermes_repo / 'scripts/whatsapp-bridge/bridge.js'
    proposals = [(adapter, adapter_patch(adapter.read_text(encoding='utf-8'))),
                 (bridge, bridge_patch(bridge.read_text(encoding='utf-8')))]
    compile(proposals[0][1], '<adapter>', 'exec')
    if args.check:
        print('policy patches match pinned source')
        return
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    for file, content in proposals:
        if content != file.read_text(encoding='utf-8'):
            shutil.copy2(file, file.with_name(file.name + '.bak-' + stamp))
            file.write_text(content, encoding='utf-8')
    print('policy hooks installed; restart gateway once after all deployment changes')

if __name__ == '__main__':
    main()
