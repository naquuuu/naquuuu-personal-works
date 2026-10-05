"""Pinned-Hermes runtime fixture; set HERMES_REPO to a disposable checkout.

This extracts the installed GatewayTurnRunner method from the actual checkout and
calls Hermes' actual agent.turn_context.build_api_messages function. It never reads
private config, a message database, or model/session credentials.
"""
from __future__ import annotations

import ast
import copy
import os
from pathlib import Path
import sys
import textwrap
import unittest
from types import SimpleNamespace
from wa_turn_auth import bind_source, must_deny_tool

HERMES_REPO = os.environ.get("HERMES_REPO")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from install_wa_owner_auth import patch_runner


@unittest.skipUnless(HERMES_REPO, "set HERMES_REPO to the disposable pinned Hermes checkout")
class OwnerVerdictRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = Path(HERMES_REPO).resolve()
        cls.runner_file = cls.repo / "gateway" / "run_turn_runner.py"
        cls.script_dir = Path(__file__).resolve().parent
        sys.path.insert(0, str(cls.repo))
        sys.path.insert(0, str(cls.script_dir))
        from agent.turn_context import build_api_messages
        cls.build_api_messages = staticmethod(build_api_messages)
        source = patch_runner(cls.runner_file.read_text(encoding="utf-8"))
        tree = ast.parse(source)
        runner_cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                          and any(isinstance(child, ast.FunctionDef)
                                  and child.name == "_combined_ephemeral_prompt" for child in node.body))
        method = next(node for node in runner_cls.body if isinstance(node, ast.FunctionDef)
                      and node.name == "_combined_ephemeral_prompt")
        cls.method_source = "\n".join(source.splitlines()[method.lineno - 1:method.end_lineno])
        cls.compiled_method = compile(
            "class Runner:\n" + textwrap.indent(cls.method_source, "    "),
            str(cls.runner_file), "exec",
        )
        cache_file = cls.repo / "gateway" / "run_agent_cache.py"
        cache_tree = ast.parse(cache_file.read_text(encoding="utf-8"))
        cache_class = next(node for node in cache_tree.body if isinstance(node, ast.ClassDef)
                           and any(isinstance(child, ast.FunctionDef)
                                   and child.name == "_agent_config_signature" for child in node.body))
        signature_method = next(child for child in cache_class.body
                                if isinstance(child, ast.FunctionDef)
                                and child.name == "_agent_config_signature")
        signature_class = ast.ClassDef(name="SignatureHarness", bases=[], keywords=[],
                                       body=[signature_method], decorator_list=[])
        signature_module = ast.fix_missing_locations(ast.Module(body=[signature_class], type_ignores=[]))
        signature_ns = {}
        exec(compile(signature_module, str(cache_file), "exec"), signature_ns)
        cls.agent_config_signature = staticmethod(signature_ns["SignatureHarness"]._agent_config_signature)

    def _combined_prompt(self, platform, decision=...):
        ns = {
            "Platform": SimpleNamespace(WHATSAPP="whatsapp"),
        }
        exec(self.compiled_method, ns)
        src = SimpleNamespace(platform=platform, chat_id="test")
        if decision is not ...:
            src._naquuuu_owner_authorized = decision
        runner = ns["Runner"]()
        runner._ctx = SimpleNamespace(source=src, context_prompt="base prompt", channel_prompt="")
        runner._runner = SimpleNamespace(_get_system_prompt_for_channel=lambda *args, **kwargs: "")
        return runner._combined_ephemeral_prompt()

    def test_actual_runner_prompt_and_api_message_are_turn_scoped(self):
        self.assertIn("NAQUUUU_WA_OWNER_VERDICT_EPHEMERAL_V2", self.method_source)
        owner_prompt = self._combined_prompt("whatsapp", True)
        guest_prompt = self._combined_prompt("whatsapp", False)
        missing_prompt = self._combined_prompt("whatsapp")
        other_prompt = self._combined_prompt("telegram", True)
        self.assertIn("verdict for this WhatsApp turn: AUTHORIZED", owner_prompt)
        self.assertIn("verdict for this WhatsApp turn: NOT_AUTHORIZED", guest_prompt)
        self.assertIn("verdict for this WhatsApp turn: NOT_AUTHORIZED", missing_prompt)
        self.assertNotIn("verdict for this WhatsApp turn", other_prompt)
        owner_sig = self.agent_config_signature("model", {}, [], owner_prompt)
        guest_sig = self.agent_config_signature("model", {}, [], guest_prompt)
        self.assertNotEqual(owner_sig, guest_sig)

        # Even if the model attempts a tool on a NOT_AUTHORIZED turn, the host
        # execution context still denies it before dispatch.
        with bind_source(SimpleNamespace(platform="whatsapp", _naquuuu_owner_authorized=False)):
            self.assertTrue(must_deny_tool())

        # Exercise Hermes' real request builder. The verdict is system-only API
        # context; persistent prompt and transcript input remain unchanged.
        history = [{"role": "user", "content": "pwd", "timestamp": 0}]
        history_before = copy.deepcopy(history)

        class AgentStub:
            _current_turn_timestamp = 0
            ephemeral_system_prompt = owner_prompt
            def _copy_reasoning_content_for_api(self, _source, _target): pass
            def _should_sanitize_tool_calls(self): return False

        wire, effective_system = self.build_api_messages(
            AgentStub(), history, current_turn_user_idx=0,
            ext_prefetch_cache=None, plugin_user_context=None,
            moa_config=None, active_system_prompt="persistent base prompt",
        )
        self.assertEqual(history, history_before)
        self.assertIn("persistent base prompt", effective_system)
        self.assertIn("verdict for this WhatsApp turn: AUTHORIZED", effective_system)
        self.assertNotIn("verdict for this WhatsApp turn", history[0]["content"])
        self.assertEqual(wire[0]["role"], "system")
        self.assertIn("AUTHORIZED", wire[0]["content"])
        self.assertEqual(wire[1]["role"], "user")
        self.assertEqual(wire[1]["content"], "pwd")

        guest_wire, guest_system = self.build_api_messages(
            AgentStubWithPrompt(guest_prompt), copy.deepcopy(history), current_turn_user_idx=0,
            ext_prefetch_cache=None, plugin_user_context=None,
            moa_config=None, active_system_prompt="persistent base prompt",
        )
        self.assertIn("NOT_AUTHORIZED", guest_system)
        self.assertNotEqual(effective_system, guest_system)
        self.assertNotEqual(wire[0]["content"], guest_wire[0]["content"])


class AgentStubWithPrompt:
    _current_turn_timestamp = 0
    def __init__(self, prompt): self.ephemeral_system_prompt = prompt
    def _copy_reasoning_content_for_api(self, _source, _target): pass
    def _should_sanitize_tool_calls(self): return False


if __name__ == "__main__":
    unittest.main()
