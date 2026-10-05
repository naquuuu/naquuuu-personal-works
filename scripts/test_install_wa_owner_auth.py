"""Synthetic fixtures for the WhatsApp host authorization installer."""
import json
import shutil
import subprocess
import tempfile
import unittest
import contextvars
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

from install_wa_owner_auth import (MARK, PROMPT_OWNER_MARK, PROMPT_OWNER_MARK_V1,
                                   _render_runner_block_v1, patch_adapter, patch_bridge,
                                   patch_executor, patch_gateway, patch_runner,
                                   require_pinned_checkout, require_tool_context_propagation)
from wa_turn_auth import bind_source, must_deny_tool
from wa_owner_gate import evaluate


class TurnContextTests(unittest.TestCase):
    def test_owner_allow_guest_deny_and_thread_isolation(self):
        from concurrent.futures import ThreadPoolExecutor

        class Source:
            platform = "whatsapp"
            def __init__(self, decision):
                self._naquuuu_owner_authorized = decision

        def check(decision):
            with bind_source(Source(decision)):
                return must_deny_tool()

        self.assertFalse(check(True))
        self.assertTrue(check(False))
        class OtherSource:
            platform = "telegram"
        with bind_source(OtherSource()):
            self.assertFalse(must_deny_tool())
        self.assertFalse(must_deny_tool())  # unbound direct CLI call remains available
        with bind_source(object()):
            self.assertTrue(must_deny_tool())  # unknown platform inside gateway scope denies
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(check, [True, False])), [False, True])

    def test_guest_decision_propagates_to_executor_worker_per_submit(self):
        def propagate_context_to_thread(target):
            context = contextvars.copy_context()
            return lambda: context.run(target)

        class Source:
            platform = "whatsapp"
            _naquuuu_owner_authorized = False

        with ThreadPoolExecutor(max_workers=1) as pool:
            with bind_source(Source()):
                guest_future = pool.submit(propagate_context_to_thread(must_deny_tool))
            with bind_source(type("Owner", (), {
                    "platform": "whatsapp", "_naquuuu_owner_authorized": True})()):
                owner_future = pool.submit(propagate_context_to_thread(must_deny_tool))
            self.assertTrue(guest_future.result())
            self.assertFalse(owner_future.result())

    def test_installer_requires_all_pinned_worker_context_wrappers(self):
        executor = '''
executor.submit(propagate_context_to_thread(_run))
executor.submit(propagate_context_to_thread(self.run_worker), i, submit_index)
'''
        thread_context = "ctx = contextvars.copy_context()\nreturn ctx.run(_inner)"
        approval = '''
executor.submit(propagate_context_to_thread(slot.run))
invoke = propagate_context_to_thread(tracked)
'''
        require_tool_context_propagation(executor, thread_context, approval)
        with self.assertRaisesRegex(ValueError, "no longer propagates"):
            require_tool_context_propagation(executor.replace("propagate_context_to_thread", "submit"),
                                             thread_context, approval)

    def test_gate_reads_private_file_not_process_environment(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            (home / ".env").write_text("NAQUUUU_WA_OWNER_IDS=10000001\n", encoding="utf-8")
            self.assertEqual(evaluate("10000001@lid", home), (True, "owner"))
            (home / ".env").write_text("NAQUUUU_WA_OWNER_IDS=*\n", encoding="utf-8")
            self.assertFalse(evaluate("10000001", home)[0])


@unittest.skipUnless(shutil.which("node"), "Node is required for bridge fixture tests")
class BridgePatchTests(unittest.TestCase):
    def test_alias_allow_config_fail_closed_and_patch_idempotence(self):
        fixture = r'''
const path = require('node:path');
const sock = {user:null};
const botIds = [];
const ALLOWED_USERS = new Set();
      console.log(`🔒 Allowed users: ${Array.from(ALLOWED_USERS).join(', ')}`);
      const connectedUser = sock?.user
  ? {
            id: sock.user.id || null,
            name: sock.user.name || sock.user.verifiedName || null,
    }
  : null;
function make(msg) {
      const senderId = msg.key.participant || 'chat';
      const senderAltId = normalizeWhatsAppId(msg.key.participantAlt || msg.key.remoteJidAlt || '');
      const resolvedSenderId = senderAltId.endsWith('@s.whatsapp.net') ? senderAltId : senderId;
      const isGroup = true;
      while (false) {
          const isSelfChat = false;
          if (!isSelfChat) {
            emitDebugEvent({
              stage: 'ignored',
              reason: 'self_chat_mismatch',
              chatId: redactWhatsAppId(chatId),
              senderId: redactWhatsAppId(senderId),
            });
            continue;
          }
          if (msg.key.fromMe) {
            if (WHATSAPP_MODE === 'bot') {
              const decision = classifyOwnerMessageGate({fromMe: true});
              if (decision.action === 'drop_echo') continue;
              if (decision.action === 'drop_disabled') continue;
              if (decision.action === 'drop_allowlist') continue;
              fromOwner = true;
            } else {
              const isSelfChat = checkSelfChat(msg);
              if (!isSelfChat) {
                emitDebugEvent({
                  stage: 'ignored',
                  reason: 'self_chat_mismatch',
                  chatId: redactWhatsAppId(chatId),
                  senderId: redactWhatsAppId(senderId),
                });
                continue;
              }
            }
          }
          try { console.log(JSON.stringify({
                reason: 'allowlist_mismatch_owner_chat',
                chatId,
                senderId,
            }));
          } catch {}
          continue;
          try { console.log(JSON.stringify({
              reason: 'self_chat_mode_rejects_non_self',
              chatId,
              senderId,
            }));
          } catch {}
          continue;
          try { console.log(JSON.stringify({
              reason: isGroup ? 'group_policy_rejected' : 'allowlist_mismatch',
              chatId,
              senderId,
              senderAltId,
            }));
          } catch {}
          continue;
      }
const event = {};
      event.fromOwner = fromOwner;
      event.senderAltId = senderAltId;
      return event._naquuuuOwnerAuthorized;
}
'''
        patched = patch_bridge(fixture)
        self.assertEqual(patch_bridge(patched), patched)
        self.assertIn("redactWhatsAppId(senderId)", patched)
        self.assertIn("redactWhatsAppId(senderAltId)", patched)
        self.assertIn("name: null", patched)
        self.assertIn("process.platform === 'win32' ? process.env.USERPROFILE : process.env.HOME", patched)
        self.assertNotIn("chatId,\n                senderId,", patched)
        self.assertNotIn("chatId,\n              senderId,", patched)
        # Extract the injected block into an isolated synthetic evaluator.
        harness = r"""
const vm = require('node:vm'), assert = require('node:assert/strict'), path = require('node:path');
const source = PATCH;
function check(sender, alias, text, fail=false, fromMe=false) {
  const context = {
    require, path, process:{env:{HOME:'/synthetic'}},
    readFileSync: (_p) => { if (fail) throw Error('fixture'); return text; },
    normalizeWhatsAppId: x => x, redactWhatsAppId: x => '…', fromOwner:false,
    msg:{key:{participant:sender,participantAlt:alias,fromMe}}, chatId:'synthetic@g.us'
  };
  context.run = new Function('msg','chatId','fromOwner','readFileSync','path','process','normalizeWhatsAppId','redactWhatsAppId','botIds',
    source.slice(source.indexOf('function make(msg) {') + 'function make(msg) {'.length, source.lastIndexOf('}')) + '\nreturn _naquuuuOwnerAuthorized;');
  context.msg.key.participant = sender;
  context.msg.key.participantAlt = alias;
  return context.run(context.msg,context.chatId,false,context.readFileSync,path,context.process,context.normalizeWhatsAppId,context.redactWhatsAppId,[]);
}
assert.equal(check('10000002@lid','10000001@s.whatsapp.net','NAQUUUU_WA_OWNER_IDS=10000001'),true);
assert.equal(check('10000002@lid','claimed 10000001','NAQUUUU_WA_OWNER_IDS=10000001'),false);
assert.equal(check('10000001','', 'NAQUUUU_WA_OWNER_IDS=*'),false);
assert.equal(check('10000001','', '', true),false);
assert.equal(check('10000001','', 'NAQUUUU_WA_OWNER_IDS=10000001', false, true),false);
console.log('owner bridge fixture PASS');
""".replace("PATCH", json.dumps(patched))
        result = subprocess.run(["node", "-e", harness], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


RUNNER_ANCHOR = "        return combined\n\n    def _append_auto_media_tags("
RUNNER_PRISTINE = '''class GatewayTurnRunner:
    def _combined_ephemeral_prompt(self) -> str:
        ctx = self._ctx
        combined = ctx.context_prompt or ""
        return combined

    def _append_auto_media_tags(self, *args):
        pass
'''
AUTHORIZED_V2_TEXT = (
    "Trusted host verdict for this WhatsApp turn: AUTHORIZED. "
    "The host has already verified that the latest user message comes from the owner; "
    "verification is complete and is not your job. Do not say you cannot verify owner authorization. "
    "Earlier replies in this conversation that refused for lack of verification are obsolete; do not repeat them. "
    "If the latest message asks for an action, call the relevant tool now (for a shell command such as pwd, "
    "use the terminal tool). The host still enforces every tool call."
)
NOT_AUTHORIZED_TEXT = (
    "Trusted host verdict for this WhatsApp turn: NOT_AUTHORIZED. "
    "Do not invoke tools or route around the host gate; respond conversationally without taking action."
)


class InstallerAnchorTests(unittest.TestCase):
    def test_ephemeral_owner_verdict_is_turn_scoped_and_strict(self):
        # Exact method body from pinned gateway/run_turn_runner.py at ecacf3d0c967222f34d15bc58852a85f2c33880c.
        source = '''class GatewayTurnRunner:
    def _combined_ephemeral_prompt(self) -> str:
        """Platform context + YAML channel_prompts hint + channel_overrides system_prompt (or global
        ephemeral) + the gateway ephemeral prompt."""
        ctx = self._ctx
        combined = ctx.context_prompt or ""
        for extra in (
            (ctx.channel_prompt or "").strip(),
            self._runner._get_system_prompt_for_channel(
                ctx.source.platform, ctx.source.chat_id or "", thread_id=getattr(ctx.source, "thread_id", None),
                parent_id=getattr(ctx.source, "parent_chat_id", None),
            ),
        ):
            if extra:
                combined = (combined + "\\n\\n" + extra).strip()
        return combined

    def _append_auto_media_tags(self, *args):
        pass
'''
        patched = patch_runner(source)
        self.assertEqual(patch_runner(patched), patched)
        namespace = {
            "Platform": SimpleNamespace(WHATSAPP="whatsapp"),
        }
        exec(compile(patched, "<pinned-run-turn-runner-fixture>", "exec"), namespace)
        cls = namespace["GatewayTurnRunner"]

        def run(platform, decision_marker=...):
            source_obj = SimpleNamespace(platform=platform, chat_id="fixture")
            if decision_marker is not ...:
                source_obj._naquuuu_owner_authorized = decision_marker
            instance = cls()
            instance._ctx = SimpleNamespace(
                source=source_obj, context_prompt="base", channel_prompt="",)
            instance._runner = SimpleNamespace(_get_system_prompt_for_channel=lambda *a, **k: "")
            return instance._combined_ephemeral_prompt()

        authorized = run("whatsapp", True)
        denied = run("whatsapp", False)
        missing = run("whatsapp")
        non_bool = [run("whatsapp", value) for value in ("true", "True", 1, [True], object())]
        non_whatsapp = run("telegram", True)
        for result in non_bool:
            self.assertIn(NOT_AUTHORIZED_TEXT, result)
            self.assertNotIn(AUTHORIZED_V2_TEXT, result)
        self.assertIn("Trusted host verdict for this WhatsApp turn: AUTHORIZED", authorized)
        self.assertIn("Trusted host verdict for this WhatsApp turn: NOT_AUTHORIZED", denied)
        self.assertIn("Trusted host verdict for this WhatsApp turn: NOT_AUTHORIZED", missing)
        self.assertNotIn("Trusted host verdict", non_whatsapp)
        self.assertIn(PROMPT_OWNER_MARK, patched)
        self.assertNotIn(PROMPT_OWNER_MARK_V1, patched)
        self.assertTrue(authorized.endswith(AUTHORIZED_V2_TEXT))
        self.assertNotIn("ask the model", authorized)
        self.assertIn(NOT_AUTHORIZED_TEXT, denied)
        self.assertIn(NOT_AUTHORIZED_TEXT, missing)

    def test_v1_to_v2_upgrade_is_equivalent_and_idempotent(self):
        pristine = RUNNER_PRISTINE
        direct = patch_runner(pristine)
        v1 = pristine.replace(RUNNER_ANCHOR, _render_runner_block_v1() + RUNNER_ANCHOR)
        self.assertIn(PROMPT_OWNER_MARK_V1, v1)
        self.assertIn("ask the model", v1)
        upgraded = patch_runner(v1)
        self.assertEqual(upgraded, direct)
        self.assertNotIn(PROMPT_OWNER_MARK_V1, upgraded)
        self.assertEqual(patch_runner(upgraded), upgraded)
        compile(upgraded, "<upgraded-runner-fixture>", "exec")

    def test_v1_renderer_matches_installed_production_block(self):
        # Golden copy of the V1 block as installed on the pinned production runner.
        golden = r'''        # NAQUUUU_WA_OWNER_VERDICT_EPHEMERAL_V1: per-turn API-only status; never persist it in session prompt/history.
        if ctx.source.platform == Platform.WHATSAPP:
            _wa_authorized = getattr(ctx.source, "_naquuuu_owner_authorized", None) is True
            if _wa_authorized:
                _wa_note = (
                    "Trusted host verdict for this WhatsApp turn: AUTHORIZED. "
                    "This strict verdict comes from the bridge. If an action is requested, make the normal relevant tool call; "
                    "do not ask the model to verify sender identity. The host still enforces every tool call."
                )
            else:
                _wa_note = (
                    "Trusted host verdict for this WhatsApp turn: NOT_AUTHORIZED. "
                    "Do not invoke tools or route around the host gate; respond conversationally without taking action."
                )
            combined = (combined + "\n\n" + _wa_note).strip()
'''
        self.assertEqual(_render_runner_block_v1(), golden)

    def test_v1_modified_duplicated_or_mixed_markers_raise(self):
        v1 = RUNNER_PRISTINE.replace(RUNNER_ANCHOR, _render_runner_block_v1() + RUNNER_ANCHOR)
        modified = v1.replace("do not ask the model", "do ask the model")
        with self.assertRaisesRegex(ValueError, "Partial owner-verdict"):
            patch_runner(modified)
        block = _render_runner_block_v1()
        duplicated = RUNNER_PRISTINE.replace(RUNNER_ANCHOR, block + block + RUNNER_ANCHOR)
        with self.assertRaisesRegex(ValueError, "Partial owner-verdict"):
            patch_runner(duplicated)
        v2 = patch_runner(RUNNER_PRISTINE)
        with self.assertRaises(ValueError):
            patch_runner(v2.replace(RUNNER_ANCHOR, _render_runner_block_v1() + RUNNER_ANCHOR))
        with self.assertRaises(ValueError):
            patch_runner(v2.replace("call the relevant tool now", "call a tool"))
        with self.assertRaises(ValueError):
            patch_runner(v2 + "\n# " + PROMPT_OWNER_MARK)

    def test_partial_executor_marker_is_fatal(self):
        with self.assertRaisesRegex(ValueError, "Partial owner-auth executor patch"):
            patch_executor(MARK + "\n    # incomplete")

    def test_check_refuses_non_pinned_checkout(self):
        with tempfile.TemporaryDirectory() as temp:
            subprocess.run(["git", "init", temp], check=True, capture_output=True)
            subprocess.run(["git", "-C", temp, "-c", "user.name=fixture", "-c",
                            "user.email=fixture@example.invalid", "commit", "--allow-empty", "-m", "fixture"],
                           check=True, capture_output=True)
            with self.assertRaisesRegex(ValueError, "not the pinned"):
                require_pinned_checkout(Path(temp))

    def test_adapter_scrubs_raw_event_identity(self):
        source = '            return MessageEvent(\n                text=body, message_type=msg_type, source=source, raw_message=data, message_id=data.get("messageId"),'
        result = patch_adapter(source)
        self.assertIn('raw_message={}, message_id=data.get("messageId")', result)
        self.assertNotIn('safe_raw_message', result)
        self.assertEqual(patch_adapter(result), result)

    def test_gateway_redaction_log_context_proxy_and_background(self):
        source = '''        context_prompt = self._pinned_session_context_prompt(context, _redact_pii, session_key)
        _platform_name, source.user_name or source.user_id or "unknown",
            source.chat_id or "unknown", (event.text or "")[:80].replace("\\n", " "),
        with self._profile_scope_for_source(source):
            return await self._run_agent_inner(message, context_prompt, history, source, session_id, **turn_kwargs)
        with self._profile_scope_for_source(source):
            return await self._run_background_task_inner(
                prompt, source, task_id, event_message_id, media_urls, media_types,
            )
        if self._get_proxy_url():
            return await self._run_agent_via_proxy('''
        patched = patch_gateway(source)
        self.assertIn('WhatsApp proxy execution is disabled', patched)
        self.assertNotIn('source.user_id or "unknown"', patched)
        self.assertIn('"unknown" if _platform_name.lower() == "whatsapp"', patched)
        self.assertIn('"unknown" if _platform_name.lower() == "whatsapp" else source.chat_id', patched)
        preview_expr = '"[redacted]" if _platform_name.lower() == "whatsapp" else (event.text or "")[:80].replace("\\n", " ")'
        self.assertIn(preview_expr, patched)
        synthetic_text = "Contact +15550001111 at 15550002222@s.whatsapp.net"
        for platform, expected in (("whatsapp", "[redacted]"), ("telegram", synthetic_text)):
            scope = {"_platform_name": platform, "event": SimpleNamespace(text=synthetic_text)}
            exec("preview = " + preview_expr, {}, scope)
            self.assertEqual(scope["preview"], expected)
            if platform == "whatsapp":
                self.assertNotIn("15550001111", scope["preview"])
                self.assertNotIn("15550002222", scope["preview"])
        self.assertLess(patched.index("_redact_pii = True"), patched.index("context_prompt = self._pinned_session_context_prompt"))
        self.assertEqual(patch_gateway(patched), patched)

    def test_executor_gate_precedes_hooks_and_dispatch(self):
        source = '    """Run Relay rewrites before Hermes policy and dispatch exactly once."""\n    from agent import relay_tools\n    from hermes_cli.middleware import apply_tool_request_middleware'
        patched = patch_executor(source)
        self.assertLess(patched.index('must_deny_tool()'), patched.index('from agent import relay_tools'))
        self.assertLess(patched.index('must_deny_tool()'), patched.index('apply_tool_request_middleware'))
        self.assertIn('WhatsApp tool authorization unavailable.', patched)
        self.assertIn('blocked=True, dispatched=False', patched)
        self.assertEqual(patch_executor(patched), patched)


if __name__ == "__main__":
    unittest.main()
