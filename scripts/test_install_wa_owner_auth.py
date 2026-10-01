"""Synthetic fixtures for the WhatsApp host authorization installer."""
import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
import contextvars
from unittest import mock
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

from install_wa_owner_auth import (HOST_ONLY_MARK, MARK, PROMPT_OWNER_MARK, PROMPT_OWNER_MARK_V1,
                                   _EXECUTOR_ANCHOR, _EXECUTOR_V2, _render_runner_block_v1, patch_adapter, patch_bridge,
                                   patch_executor, patch_gateway, patch_runner,
                                   require_pinned_checkout, require_tool_context_propagation)
import wa_turn_auth
from wa_turn_auth import bind_source, must_deny_host_only, must_deny_tool
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
        self.assertLess(patched.index('must_deny_tool()'), patched.index('must_deny_host_only('))
        self.assertLess(patched.index('must_deny_host_only('), patched.index('from agent import relay_tools'))
        self.assertLess(patched.index('must_deny_host_only('), patched.index('apply_tool_request_middleware'))
        self.assertIn('host-only action', patched)
        self.assertNotIn('from wa_turn_auth import', patched)  # attribute access keeps stale modules fail-closed


EXECUTOR_SOURCE = (
    "def run_tool(function_args, middleware_trace=None):\n"
    + _EXECUTOR_ANCHOR + "\n    return 'dispatched'\n"
)


class _Source:
    def __init__(self, platform, authorized=None):
        self.platform = platform
        if authorized is not None:
            self._naquuuu_owner_authorized = authorized


def _nested(depth, leaf):
    value = leaf
    for _ in range(depth):
        value = [value]
    return value


class HostOnlyTripwirePerformanceTests(unittest.TestCase):
    def test_large_arguments_scan_in_linear_time(self):
        import time
        owner = SimpleNamespace(platform="whatsapp", _naquuuu_owner_authorized=True)
        payloads = ["hermes " * 28000, "/proc/" * 30000, "hermes foo\n" * 18000,
                    "systemctl " * 20000, "pkill " * 30000, "x" * 200000]
        with bind_source(owner):
            for payload in payloads:
                started = time.perf_counter()
                must_deny_host_only({"content": payload})
                self.assertLess(time.perf_counter() - started, 1.0, payload[:12])


class HostOnlyTripwireTests(unittest.TestCase):
    OWNER = _Source("whatsapp", True)
    GUEST = _Source("whatsapp", False)
    DENIED = [
        {"command": "python3 scripts/whatsapp_group_fix.py --allow-user 15550001111"},
        "python3 scripts/wa_free_response.py --add-latest",
        "python3 scripts/wa_group_allow.py --add",
        "python3 scripts/wa_owner_gate.py",
        "python3 scripts/install_wa_owner_auth.py --hermes-repo x",
        "python3 scripts/install_wa_chat_policy.py",
        {"path": "/home/u/.hermes/.env", "content": "X=1"},
        "cat ~/naquuuu/.env",
        "cat .env.local",
        "ls ~/.hermes",
        "ls '~/.hermes'",
        "type %USERPROFILE%\\.hermes\\config.yaml",
        "systemctl --user restart hermes-gateway.service",
        "hermes gateway restart",
        "HERMES  GATEWAY   stop",
        "hermes config set approvals.destructive_slash_confirm false",
        "pkill -f hermes",
        "killall hermes",
        json.dumps({"command": "hermes gateway install"}),
        json.dumps({"command": "cat \u002eenv"}),
        {"outer": [{"inner": ("ok", "cat ~/.env")}]},
        [["nested", ["deeper", {"k": "pkill hermes"}]]],
        {"cat ~/.env": "value"},
        _nested(12, "pwd"),
        # Round 2: terminators, home spellings, cache-exemption boundaries.
        "ls ~/.hermes,", "ls ~/.hermes;", "echo (~/.hermes)", "ls ~/.hermes",
        "cat /home/u/.hermes/config.yaml", "cat /home/u/.hermes/logs/agent.log",
        "cat /home/u/.hermes/SOUL.md", "ls /home/u/.hermes/hermes-agent/",
        "cat /home/u/.hermes/.env",
        "cat /home/u/.hermes/cache_evil/x", "cat /home/u/.hermes/image_cache/../config.yaml",
        "cat /home/u/.hermes/image_cache/..\\.env",
        "cat $HERMES_HOME/config.yaml", "cat ${HERMES_HOME}/logs/x", "ls $HERMES_HOME",
        "cat $hermes_home/SOUL.md",
        "type %LOCALAPPDATA%\\hermes\\config.yaml", "dir %localappdata%/hermes/logs",
        "cat /home/u/.hermes/image_cache/a.jpg /home/u/.hermes/.env",
        "cat .env", "cat .env.local", "cat config/.env.production",
        "hermes -p synthetic gateway restart", "hermes gateway --replace",
        "hermes gateway run --replace", "python3 -m hermes_cli.main gateway restart",
        "python3 -m hermes_cli.main -p x gateway stop",
        "hermes\ngateway restart", "echo ok; hermes config edit", "hermes config set a b",
        "hermes -p x config edit",
        "systemctl --user stop hermes-gateway", "systemctl\n  restart hermes-gateway",
        "service hermes-gateway restart", "pgrep -fa hermes", "killall -9 hermes",
        "python3 scripts/wa_chat_policy.py", "python3 scripts/install_relay_guards.py",
        "python3 scripts/sync_wa_owner_auth_prompt.py --apply",
        "python3 scripts/refresh_wa_prompt_snapshot.py", "bash scripts/enable_gates.sh",
        "python3 scripts/swap_action_gateway_session.py",
        "printenv", "printenv HOME", "cat /proc/self/environ", "tr '\\0' '\\n' < /proc/1234/environ",
        {"cmd": {"cat ~/.env", "x"}}, frozenset(["hermes gateway restart"]),
        b"cat ~/.env", bytearray(b"pkill hermes"), [b"hermes config set a b"],
        b"\xff\xfe hermes gateway stop",
    ]
    ALLOWED = [
        "pwd",
        'opencode run --agent naquuuubot "status"',
        'python3 "$NAQUUUU_WORKSPACE/scripts/relay_run.py" --status',
        "import os; print(os.environ.get('HOME'))",
        {"path": "notes/environment.md"},
        {"count": 3, "flag": True, "none": None, "items": ["a", 1, 2.5]},
        "hermes --version",
        # Round 2: false-positive cuts and media caches.
        "const k = process.env.NODE_ENV;", "cat .env.example", "cat .env.sample", "cat .env.template",
        'python3 "$NAQUUUU_WORKSPACE/scripts/relay_run.py" --file /home/u/.hermes/image_cache/img_1.jpg',
        "python3 relay_run.py --file /home/u/.hermes/audio_cache/a.ogg",
        "python3 relay_run.py --file /home/u/.hermes/document_cache/doc_1.pdf",
        "python3 relay_run.py --file /home/u/.hermes/video_cache/v.mp4",
        "python3 relay_run.py --file /home/u/.hermes/cache/x/y.png",
        "python3 relay_run.py --file $HERMES_HOME/image_cache/img_1.jpg",
        "python3 relay_run.py --file ${HERMES_HOME}/image_cache/img_1.jpg",
        "python3 relay_run.py --file %LOCALAPPDATA%\\hermes\\image_cache\\img_1.jpg",
        {"file": "/home/u/.hermes/image_cache/img_1.jpg"},
        'relay_run.py --file "/home/u/.hermes/image_cache/img_1.jpg"',
        "hermes gateway status", "hermes -p synthetic gateway status", "hermes\ngateway status",
        "hermes config show", "echo hi; echo hermes", "systemctl status ssh; echo hermes",
        "service ssh restart", "printenvironment notes", "cat /proc/cpuinfo", b"pwd", {"a", "pwd"},
    ]

    def test_owner_whatsapp_turn_denies_host_only_actions(self):
        with bind_source(self.OWNER):
            self.assertFalse(must_deny_tool())
            for args in self.DENIED:
                with self.subTest(args=args):
                    self.assertTrue(must_deny_host_only(args))

    def test_owner_whatsapp_turn_allows_ordinary_actions(self):
        with bind_source(self.OWNER):
            for args in self.ALLOWED:
                with self.subTest(args=args):
                    self.assertFalse(must_deny_host_only(args))

    def test_guest_whatsapp_turn_is_denied_by_both_gates(self):
        with bind_source(self.GUEST):
            self.assertTrue(must_deny_tool())
            for args in self.DENIED:
                with self.subTest(args=args):
                    self.assertTrue(must_deny_host_only(args))

    def test_non_whatsapp_and_unbound_turns_are_not_tripped(self):
        with bind_source(_Source("telegram")):
            for args in self.DENIED:
                with self.subTest(args=args):
                    self.assertFalse(must_deny_host_only(args))
        for args in self.DENIED:
            with self.subTest(args=args):
                self.assertFalse(must_deny_host_only(args))  # no binding at all

    def test_owner_turn_deny_and_allow_lists_hold_together(self):
        """Every DENIED entry denies and every ALLOWED entry passes, in one owner turn."""
        with bind_source(self.OWNER):
            for args in self.DENIED:
                self.assertTrue(must_deny_host_only(args), args)
            for args in self.ALLOWED:
                self.assertFalse(must_deny_host_only(args), args)

    def test_executor_v2_to_v3_migration_is_equivalent_and_idempotent(self):
        fresh = patch_executor(EXECUTOR_SOURCE)
        v2 = EXECUTOR_SOURCE.replace(_EXECUTOR_ANCHOR, _EXECUTOR_V2)
        self.assertIn(MARK, v2)
        self.assertNotIn(HOST_ONLY_MARK, v2)
        self.assertEqual(patch_executor(v2), fresh)
        self.assertEqual(patch_executor(fresh), fresh)
        self.assertEqual(fresh.count(MARK), 1)
        self.assertEqual(fresh.count(HOST_ONLY_MARK), 1)
        compile(fresh, "<executor-fixture>", "exec")

    def test_executor_mixed_or_partial_markers_raise(self):
        fresh = patch_executor(EXECUTOR_SOURCE)
        v2 = EXECUTOR_SOURCE.replace(_EXECUTOR_ANCHOR, _EXECUTOR_V2)
        for bad in (
            fresh + "\n# " + HOST_ONLY_MARK,
            fresh + "\n# " + MARK,
            fresh.replace("must_deny_host_only(function_args)", "False"),
            v2 + "\n# " + HOST_ONLY_MARK,
            v2 + "\n# " + MARK,
            v2.replace("must_deny_tool()", "False"),
            EXECUTOR_SOURCE + "\n# " + HOST_ONLY_MARK,
        ):
            with self.subTest(bad=bad[-60:]):
                with self.assertRaisesRegex(ValueError, "Partial owner-auth executor patch"):
                    patch_executor(bad)

    @staticmethod
    def _patched_run_tool():
        namespace = {"_ManagedToolResult": lambda **kwargs: kwargs}
        exec(compile(patch_executor(EXECUTOR_SOURCE), "<executor-fixture>", "exec"), namespace)
        return namespace["run_tool"]

    @staticmethod
    def _isolated(auth_module):
        """Fake agent package, chosen wa_turn_auth, and no workspace path; restored on exit."""
        agent = types.ModuleType("agent")
        agent.relay_tools = object()
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.dict(os.environ))
        os.environ.pop("NAQUUUU_WORKSPACE", None)
        stack.enter_context(mock.patch.dict(sys.modules, {"wa_turn_auth": auth_module, "agent": agent}))
        return stack

    def test_patched_executor_blocks_host_only_before_dispatch(self):
        run_tool = self._patched_run_tool()
        with self._isolated(wa_turn_auth):
            with bind_source(self.OWNER):
                blocked = run_tool({"command": "hermes gateway restart"})
                allowed = run_tool({"command": "pwd"})
            with bind_source(self.GUEST):
                guest = run_tool({"command": "pwd"})
        self.assertTrue(blocked["blocked"])
        self.assertFalse(blocked["dispatched"])
        self.assertIn("host-only action", blocked["result"])
        self.assertEqual(allowed, "dispatched")
        self.assertIn("Only the owner can run WhatsApp tools.", guest["result"])

    def test_stale_wa_turn_auth_without_host_only_check_fails_closed(self):
        stale = types.ModuleType("wa_turn_auth")
        stale.must_deny_tool = lambda: False
        run_tool = self._patched_run_tool()
        before = sys.modules["wa_turn_auth"]
        with self._isolated(stale):
            result = run_tool({"command": "pwd"})
        self.assertIs(sys.modules["wa_turn_auth"], before)
        self.assertTrue(result["blocked"])
        self.assertFalse(result["dispatched"])
        self.assertIn("WhatsApp tool authorization unavailable.", result["result"])


if __name__ == "__main__":
    unittest.main()
