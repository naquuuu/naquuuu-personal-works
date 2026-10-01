"""Install host-side WhatsApp owner enforcement into the pinned Hermes checkout.

The installer is local/reviewable and never restarts or deploys Hermes. It refuses
any source drift or partial marker set before writing a file.
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
import shutil
import subprocess

MARK = "NAQUUUU_WA_OWNER_AUTH_V2"
BRIDGE_OWNER_MARK = "NAQUUUU_WA_OWNER_AUTH_FROMME_V1"
HOST_ONLY_MARK = "NAQUUUU_WA_HOST_ONLY_GUARD_V1"
PROMPT_OWNER_MARK_V1 = "NAQUUUU_WA_OWNER_VERDICT_EPHEMERAL_V1"
PROMPT_OWNER_MARK = "NAQUUUU_WA_OWNER_VERDICT_EPHEMERAL_V2"
PINNED_COMMIT = "ecacf3d0c967222f34d15bc58852a85f2c33880c"


def replace_once(text: str, anchor: str, replacement: str) -> str:
    if text.count(anchor) != 1:
        raise ValueError(f"Pinned source anchor mismatch: {anchor[:80]!r}")
    return text.replace(anchor, replacement, 1)


def require_pinned_checkout(repo: Path) -> None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError("Hermes checkout commit could not be verified") from exc
    if result.stdout.strip() != PINNED_COMMIT:
        raise ValueError("Hermes checkout is not the pinned owner-auth source commit")


def require_tool_context_propagation(executor: str, thread_context: str, approval_batch: str) -> None:
    """Require the pinned host's per-submit ContextVar propagation on every tool path."""
    if (executor.count("propagate_context_to_thread(") < 2
            or "executor.submit(propagate_context_to_thread(_run))" not in executor
            or "executor.submit(propagate_context_to_thread(self.run_worker), i, submit_index)" not in executor
            or "ctx = contextvars.copy_context()" not in thread_context
            or "return ctx.run(_inner)" not in thread_context
            or "executor.submit(propagate_context_to_thread(slot.run))" not in approval_batch
            or "invoke = propagate_context_to_thread(tracked)" not in approval_batch):
        raise ValueError("Pinned tool executor no longer propagates per-turn context to every worker")


def patch_adapter(text: str) -> str:
    if MARK in text:
        if text.count(MARK) == 1 and all(fragment in text for fragment in (
            "source._naquuuu_owner_authorized = data.get(\"_naquuuuOwnerAuthorized\") is True",
            "raw_message={}, message_id=data.get(\"messageId\")",
        )):
            return text
        raise ValueError("Partial owner-auth adapter patch detected")
    # Set trusted, host-internal state and do not retain the raw bridge payload.
    return replace_once(text,
        "            return MessageEvent(\n                text=body, message_type=msg_type, source=source, raw_message=data, message_id=data.get(\"messageId\"),",
        f'''            # {MARK}: only bridge-computed strict bool is trusted.
            source._naquuuu_owner_authorized = data.get("_naquuuuOwnerAuthorized") is True
            return MessageEvent(
                text=body, message_type=msg_type, source=source, raw_message={{}}, message_id=data.get("messageId"),''')


def patch_bridge(text: str) -> str:
    if BRIDGE_OWNER_MARK in text:
        if text.count(BRIDGE_OWNER_MARK) == 2 and text.count("NAQUUUU_CHAT_POLICY_V1") <= 1 and all(fragment in text for fragment in (
            "const _naquuuuSessionOwnerAuthorized = botIds.some(_naquuuuOwnerIdentityMatches)",
            "_naquuuuOwnerAuthorized = _naquuuuSessionOwnerAuthorized; // " + BRIDGE_OWNER_MARK,
            "let _naquuuuOwnerAuthorized = !msg.key.fromMe && [senderId, senderAltId].some(_naquuuuOwnerIdentityMatches)",
            "const _naquuuuOwnerIdentityMatches = (identity) =>",
            "let _naquuuuSelfChatVerified = false;",
            "_naquuuuSelfChatVerified = true;",
            "_naquuuuOwnerAuthorized = _naquuuuSelfChatVerified && _naquuuuSessionOwnerAuthorized;",
            "event._naquuuuOwnerAuthorized = _naquuuuOwnerAuthorized",
            "Allowed users configured: ${ALLOWED_USERS.size}",
        )):
            return text
        raise ValueError("Partial fromMe owner-auth bridge patch detected")
    if MARK in text:
        # Migrate the installed V2 bridge gate without losing adjacent chat-policy edits.
        if text.count(MARK) != 2 or text.count("NAQUUUU_CHAT_POLICY_V1") != 1 or not all(fragment in text for fragment in (
            "const _naquuuuOwnerAuthorized = !msg.key.fromMe && [senderId, senderAltId].some(identity =>",
            "event.senderAltId = senderAltId",
            "event._naquuuuOwnerAuthorized = _naquuuuOwnerAuthorized",
            "if (!isSelfChat) {",
            "fromOwner = true;",
            "reason: 'allowlist_mismatch_owner_chat',\n                chatId: redactWhatsAppId(chatId),",
            "reason: 'self_chat_mode_rejects_non_self',\n              chatId: redactWhatsAppId(chatId),",
            "senderAltId: redactWhatsAppId(senderAltId),",
            "id: sock.user.id ? redactWhatsAppId(sock.user.id) : null",
            "Allowed users configured: ${ALLOWED_USERS.size}",
        )):
            raise ValueError("Partial owner-auth bridge patch detected")
        text = replace_once(text,
            "      const _naquuuuOwnerAuthorized = !msg.key.fromMe && [senderId, senderAltId].some(identity =>\n        typeof identity === 'string' && /^\\+?[0-9]+(@(s\\.whatsapp\\.net|lid))?$/.test(identity)\n        && _naquuuuOwnerIds.includes(identity.replace(/\\D/g, '')));",
            """      const _naquuuuOwnerIdentityMatches = (identity) =>
        typeof identity === 'string' && /^\\+?[0-9]+(@(s\\.whatsapp\\.net|lid))?$/.test(identity)
        && _naquuuuOwnerIds.includes(identity.replace(/\\D/g, ''));
      const _naquuuuSessionOwnerAuthorized = botIds.some(_naquuuuOwnerIdentityMatches);
      let _naquuuuSelfChatVerified = false;
      let _naquuuuOwnerAuthorized = !msg.key.fromMe && [senderId, senderAltId].some(_naquuuuOwnerIdentityMatches);""")
        text = replace_once(text, "          fromOwner = true;",
            "          fromOwner = true;\n          _naquuuuOwnerAuthorized = _naquuuuSessionOwnerAuthorized; // " + BRIDGE_OWNER_MARK)
        text = replace_once(text,
            "          if (!isSelfChat) {\n            emitDebugEvent({\n              stage: 'ignored',\n              reason: 'self_chat_mismatch',\n              chatId: redactWhatsAppId(chatId),\n              senderId: redactWhatsAppId(senderId),\n            });\n            continue;\n          }",
            "          if (!isSelfChat) {\n            emitDebugEvent({\n              stage: 'ignored',\n              reason: 'self_chat_mismatch',\n              chatId: redactWhatsAppId(chatId),\n              senderId: redactWhatsAppId(senderId),\n            });\n            continue;\n          }\n          _naquuuuSelfChatVerified = true;\n          _naquuuuOwnerAuthorized = _naquuuuSelfChatVerified && _naquuuuSessionOwnerAuthorized; // " + BRIDGE_OWNER_MARK)
        return text
    # Exact identity acquisition site; fromOwner is intentionally not consulted.
    text = replace_once(text,
        "      const senderAltId = normalizeWhatsAppId(msg.key.participantAlt || msg.key.remoteJidAlt || '');\n      const resolvedSenderId = senderAltId.endsWith('@s.whatsapp.net') ? senderAltId : senderId;",
        f'''      const senderAltId = normalizeWhatsAppId(msg.key.participantAlt || msg.key.remoteJidAlt || '');
      const resolvedSenderId = senderAltId.endsWith('@s.whatsapp.net') ? senderAltId : senderId;
      // {MARK}: file/environment failure and wildcard config always deny.
      let _naquuuuOwnerIds = [];
      try {{
        const homeRoot = process.platform === 'win32' ? process.env.USERPROFILE : process.env.HOME;
        const home = process.env.HERMES_HOME || (homeRoot ? path.join(homeRoot, '.hermes') : null);
        if (!home) throw new Error('Hermes home unavailable');
        const envText = readFileSync(path.join(home, '.env'), 'utf8');
        const ownerLine = envText.split(/\\r?\\n/).find(line => /^\\s*(?:export\\s+)?NAQUUUU_WA_OWNER_IDS\\s*=/.test(line));
        const ownerValue = ownerLine ? ownerLine.replace(/^\\s*(?:export\\s+)?NAQUUUU_WA_OWNER_IDS\\s*=\\s*/, '').trim().replace(/^['\"]|['\"]$/g, '') : '';
        const entries = ownerValue.split(',').map(value => value.trim()).filter(Boolean);
        if (entries.length && !entries.some(value => ['*', 'all', 'any', 'everyone', 'open'].includes(value.toLowerCase())))
          _naquuuuOwnerIds = entries.filter(value => /^\\+?[0-9]+(@(s\\.whatsapp\\.net|lid))?$/.test(value)).map(value => value.replace(/\\D/g, ''));
      }} catch {{ _naquuuuOwnerIds = []; }}
      const _naquuuuOwnerIdentityMatches = (identity) =>
        typeof identity === 'string' && /^\\+?[0-9]+(@(s\\.whatsapp\\.net|lid))?$/.test(identity)
        && _naquuuuOwnerIds.includes(identity.replace(/\\D/g, ''));
      const _naquuuuSessionOwnerAuthorized = botIds.some(_naquuuuOwnerIdentityMatches);
      let _naquuuuSelfChatVerified = false;
      let _naquuuuOwnerAuthorized = !msg.key.fromMe && [senderId, senderAltId].some(_naquuuuOwnerIdentityMatches);''')
    # Remove raw user/chat identity from every inbound rejection log path.
    text = replace_once(text,
        "reason: 'allowlist_mismatch_owner_chat',\n                chatId,\n                senderId,",
        "reason: 'allowlist_mismatch_owner_chat',\n                chatId: redactWhatsAppId(chatId),\n                senderId: redactWhatsAppId(senderId),")
    text = replace_once(text,
        "reason: 'self_chat_mode_rejects_non_self',\n              chatId,\n              senderId,",
        "reason: 'self_chat_mode_rejects_non_self',\n              chatId: redactWhatsAppId(chatId),\n              senderId: redactWhatsAppId(senderId),")
    text = replace_once(text,
        "reason: isGroup ? 'group_policy_rejected' : 'allowlist_mismatch',\n              chatId,\n              senderId,\n              senderAltId,",
        "reason: isGroup ? 'group_policy_rejected' : 'allowlist_mismatch',\n              chatId: redactWhatsAppId(chatId),\n              senderId: redactWhatsAppId(senderId),\n              senderAltId: redactWhatsAppId(senderAltId),")
    text = replace_once(text, "      event.fromOwner = fromOwner;", f'''      event.fromOwner = fromOwner;
      event.senderAltId = senderAltId;
      event._naquuuuOwnerAuthorized = _naquuuuOwnerAuthorized; // {MARK}'''.replace('+', ''))
    text = replace_once(text, "          fromOwner = true;",
        "          fromOwner = true;\n          _naquuuuOwnerAuthorized = _naquuuuSessionOwnerAuthorized; // " + BRIDGE_OWNER_MARK)
    text = replace_once(text,
        "          if (!isSelfChat) {\n            emitDebugEvent({\n              stage: 'ignored',\n              reason: 'self_chat_mismatch',\n              chatId: redactWhatsAppId(chatId),\n              senderId: redactWhatsAppId(senderId),\n            });\n            continue;\n          }",
        "          if (!isSelfChat) {\n            emitDebugEvent({\n              stage: 'ignored',\n              reason: 'self_chat_mismatch',\n              chatId: redactWhatsAppId(chatId),\n              senderId: redactWhatsAppId(senderId),\n            });\n            continue;\n          }\n          _naquuuuSelfChatVerified = true;\n          _naquuuuOwnerAuthorized = _naquuuuSelfChatVerified && _naquuuuSessionOwnerAuthorized; // " + BRIDGE_OWNER_MARK)
    text = replace_once(text, "            id: sock.user.id || null,\n            name: sock.user.name || sock.user.verifiedName || null,",
        "            id: sock.user.id ? redactWhatsAppId(sock.user.id) : null,\n            name: null,")
    text = replace_once(text, "      console.log(`🔒 Allowed users: ${Array.from(ALLOWED_USERS).join(', ')}`);",
        "      console.log(`🔒 Allowed users configured: ${ALLOWED_USERS.size}`);")
    return text


def patch_gateway(text: str) -> str:
    if MARK in text:
        if (text.count("with bind_source(source)") == 2
                and text.count(MARK) == 4
                and "WhatsApp proxy execution is disabled" in text
                and "_platform_name, \"unknown\" if _platform_name.lower() == \"whatsapp\" else source.user_name or \"unknown\"," in text
                and '"unknown" if _platform_name.lower() == "whatsapp" else source.chat_id or "unknown",' in text
                and '"[redacted]" if _platform_name.lower() == "whatsapp" else (event.text or "")[:80].replace("\\n", " ")' in text
                and "_redact_pii = True" in text):
            return text
        raise ValueError("Partial owner-auth gateway patch detected")
    text = replace_once(text,
        "        context_prompt = self._pinned_session_context_prompt(context, _redact_pii, session_key)",
        f'''        # {MARK}: WhatsApp identifiers never enter the model context, regardless of optional config.
        if str(getattr(getattr(source, "platform", None), "value", source.platform)).lower() == "whatsapp":
            _redact_pii = True
        context_prompt = self._pinned_session_context_prompt(context, _redact_pii, session_key)''')
    text = replace_once(text, "_platform_name, source.user_name or source.user_id or \"unknown\",",
        "_platform_name, \"unknown\" if _platform_name.lower() == \"whatsapp\" else source.user_name or \"unknown\",")
    text = replace_once(text,
        "            source.chat_id or \"unknown\", (event.text or \"\")[:80].replace(\"\\n\", \" \"),",
        "            \"unknown\" if _platform_name.lower() == \"whatsapp\" else source.chat_id or \"unknown\", \"[redacted]\" if _platform_name.lower() == \"whatsapp\" else (event.text or \"\")[:80].replace(\"\\n\", \" \"),")
    text = replace_once(text,
        "        with self._profile_scope_for_source(source):\n            return await self._run_agent_inner(message, context_prompt, history, source, session_id, **turn_kwargs)",
        f'''        with self._profile_scope_for_source(source):
            # {MARK}: task-local binding follows this source through child tasks.
            import os as _wa_os, sys as _wa_sys
            _wa_root = _wa_os.environ.get("NAQUUUU_WORKSPACE")
            if not _wa_root:
                raise RuntimeError("WhatsApp owner authorization workspace is unavailable")
            _wa_sys.path.insert(0, _wa_os.path.join(_wa_root, "scripts"))
            from wa_turn_auth import bind_source
            with bind_source(source):
                return await self._run_agent_inner(message, context_prompt, history, source, session_id, **turn_kwargs)''')
    text = replace_once(text,
        "        with self._profile_scope_for_source(source):\n            return await self._run_background_task_inner(\n                prompt, source, task_id, event_message_id, media_urls, media_types,\n            )",
        f'''        with self._profile_scope_for_source(source):
            # {MARK}: background task inherits only the host decision.
            import os as _wa_os, sys as _wa_sys
            _wa_root = _wa_os.environ.get("NAQUUUU_WORKSPACE")
            if not _wa_root:
                raise RuntimeError("WhatsApp owner authorization workspace is unavailable")
            _wa_sys.path.insert(0, _wa_os.path.join(_wa_root, "scripts"))
            from wa_turn_auth import bind_source
            with bind_source(source):
                return await self._run_background_task_inner(
                    prompt, source, task_id, event_message_id, media_urls, media_types,
                )''')
    text = replace_once(text, "        if self._get_proxy_url():\n            return await self._run_agent_via_proxy(",
        f'''        # {MARK}: proxy execution has no equivalent remote owner enforcement.
        if str(getattr(getattr(source, "platform", None), "value", source.platform)).lower() == "whatsapp" and self._get_proxy_url():
            raise RuntimeError("WhatsApp proxy execution is disabled without remote owner enforcement")
        if self._get_proxy_url():
            return await self._run_agent_via_proxy(''')
    return text


_RUNNER_ANCHOR = "        return combined\n\n    def _append_auto_media_tags("
_WA_AUTHORIZED_LINES_V1 = (
    "Trusted host verdict for this WhatsApp turn: AUTHORIZED. ",
    "This strict verdict comes from the bridge. If an action is requested, make the normal relevant tool call; ",
    "do not ask the model to verify sender identity. The host still enforces every tool call.",
)
_WA_AUTHORIZED_LINES_V2 = (
    "Trusted host verdict for this WhatsApp turn: AUTHORIZED. ",
    "The host has already verified that the latest user message comes from the owner; "
    "verification is complete and is not your job. Do not say you cannot verify owner authorization. ",
    "Earlier replies in this conversation that refused for lack of verification are obsolete; do not repeat them. ",
    "If the latest message asks for an action, call the relevant tool now (for a shell command such as pwd, "
    "use the terminal tool). The host still enforces every tool call.",
)


def _render_runner_block(mark: str, authorized_lines: tuple) -> str:
    """Render the per-turn verdict block (ends just before the return statement)."""
    authorized = "".join(f'                    "{line}"\n' for line in authorized_lines)
    return f'''        # {mark}: per-turn API-only status; never persist it in session prompt/history.
        if ctx.source.platform == Platform.WHATSAPP:
            _wa_authorized = getattr(ctx.source, "_naquuuu_owner_authorized", None) is True
            if _wa_authorized:
                _wa_note = (
{authorized}                )
            else:
                _wa_note = (
                    "Trusted host verdict for this WhatsApp turn: NOT_AUTHORIZED. "
                    "Do not invoke tools or route around the host gate; respond conversationally without taking action."
                )
            combined = (combined + "\\n\\n" + _wa_note).strip()
'''


def _render_runner_block_v1() -> str:
    """V1 block exactly as installed in production."""
    return _render_runner_block(PROMPT_OWNER_MARK_V1, _WA_AUTHORIZED_LINES_V1)


def _render_runner_block_v2() -> str:
    return _render_runner_block(PROMPT_OWNER_MARK, _WA_AUTHORIZED_LINES_V2)


def patch_runner(text: str) -> str:
    """Expose only the strict bridge verdict in the API-time ephemeral system prompt (V2; upgrades V1)."""
    v2 = _render_runner_block_v2()
    v1 = _render_runner_block_v1()
    has_v1 = PROMPT_OWNER_MARK_V1 in text
    has_v2 = PROMPT_OWNER_MARK in text
    if has_v2 and not has_v1:
        if text.count(PROMPT_OWNER_MARK) == 1 and text.count(v2) == 1:
            return text
        raise ValueError("Partial owner-verdict ephemeral prompt patch detected")
    if has_v1 and not has_v2:
        if text.count(PROMPT_OWNER_MARK_V1) == 1 and text.count(v1) == 1:
            return text.replace(v1, v2, 1)
        raise ValueError("Partial owner-verdict ephemeral prompt patch detected")
    if has_v1 and has_v2:
        raise ValueError("Conflicting owner-verdict ephemeral prompt patch markers detected")
    return replace_once(text, _RUNNER_ANCHOR, v2 + _RUNNER_ANCHOR)


_EXECUTOR_ANCHOR = "    \"\"\"Run Relay rewrites before Hermes policy and dispatch exactly once.\"\"\"\n    from agent import relay_tools"
_EXECUTOR_V2 = f'''    \"\"\"Run Relay rewrites before Hermes policy and dispatch exactly once.\"\"\"
    # {MARK}: this is before relay hooks, middleware, plugin pre-hooks and dispatch.
    try:
        import os as _wa_os, sys as _wa_sys
        _wa_root = _wa_os.environ.get("NAQUUUU_WORKSPACE")
        if _wa_root:
            _wa_sys.path.insert(0, _wa_os.path.join(_wa_root, "scripts"))
        from wa_turn_auth import must_deny_tool
        if must_deny_tool():
            return _ManagedToolResult(
                result='{{"error":"Only the owner can run WhatsApp tools."}}',
                args=function_args, middleware_trace=middleware_trace or [], blocked=True, dispatched=False,
            )
    except ImportError:
        # A direct CLI has no gateway sender scope and may not have workspace
        # scripts on sys.path. WhatsApp gateway turns cannot reach here unless
        # the earlier gateway binding import succeeded.
        pass
    except Exception:
        # A broken gate disables this tool execution; it never falls through.
        return _ManagedToolResult(
            result='{{"error":"WhatsApp tool authorization unavailable."}}',
            args=function_args, middleware_trace=middleware_trace or [], blocked=True, dispatched=False,
        )
    from agent import relay_tools'''
# Attribute access (not `from ... import`) so a stale wa_turn_auth without the
# host-only check raises AttributeError and hits the fail-closed Exception branch.
_EXECUTOR_V3 = _EXECUTOR_V2.replace(
    "        from wa_turn_auth import must_deny_tool\n        if must_deny_tool():",
    "        import wa_turn_auth as _wa_turn_auth\n        if _wa_turn_auth.must_deny_tool():",
).replace(
    "            )\n    except ImportError:",
    f'''            )
        # {HOST_ONLY_MARK}: host-admin actions stay in the owner's host shell, never WhatsApp.
        if _wa_turn_auth.must_deny_host_only(function_args):
            return _ManagedToolResult(
                result='{{"error":"That is a host-only action; run it from the host shell."}}',
                args=function_args, middleware_trace=middleware_trace or [], blocked=True, dispatched=False,
            )
    except ImportError:''', 1)
if HOST_ONLY_MARK not in _EXECUTOR_V3 or _EXECUTOR_V3 == _EXECUTOR_V2:
    raise RuntimeError("Executor V3 template failed to build")


def patch_executor(text: str) -> str:
    """Install the executor gate (V3: owner gate plus host-only tripwire; upgrades V2)."""
    has_mark = MARK in text
    has_host_only = HOST_ONLY_MARK in text
    if has_host_only:
        if (text.count(_EXECUTOR_V3) == 1 and text.count(MARK) == 1
                and text.count(HOST_ONLY_MARK) == 1 and _EXECUTOR_ANCHOR not in text):
            return text
        raise ValueError("Partial owner-auth executor patch detected")
    if has_mark:
        if text.count(_EXECUTOR_V2) == 1 and text.count(MARK) == 1:
            return text.replace(_EXECUTOR_V2, _EXECUTOR_V3, 1)
        raise ValueError("Partial owner-auth executor patch detected")
    return replace_once(text, _EXECUTOR_ANCHOR, _EXECUTOR_V3)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--hermes-repo', type=Path, required=True)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    repo = args.hermes_repo.resolve()
    require_pinned_checkout(repo)
    require_tool_context_propagation(
        (repo / 'agent/tool_executor.py').read_text(encoding='utf-8'),
        (repo / 'tools/thread_context.py').read_text(encoding='utf-8'),
        (repo / 'agent/terminal_approval_batch.py').read_text(encoding='utf-8'),
    )
    files = [
        (repo / 'plugins/platforms/whatsapp/adapter.py', patch_adapter),
        (repo / 'scripts/whatsapp-bridge/bridge.js', patch_bridge),
        (repo / 'gateway/run_turn.py', patch_gateway),
        (repo / 'gateway/run_turn_runner.py', patch_runner),
        (repo / 'agent/tool_executor.py', patch_executor),
    ]
    originals = [(path, path.read_text(encoding='utf-8')) for path, _patch in files]
    proposals = [(path, patch(original)) for (path, patch), (_same_path, original) in zip(files, originals)]
    compile(proposals[0][1], '<adapter>', 'exec')
    compile(proposals[2][1], '<run_turn>', 'exec')
    compile(proposals[3][1], '<run_turn_runner>', 'exec')
    compile(proposals[4][1], '<tool_executor>', 'exec')
    if args.check:
        if any(proposed != original for (_path, proposed), (_same_path, original) in zip(proposals, originals)):
            raise ValueError('Owner-auth patches are not fully installed')
        print('owner-auth patches are fully installed on the pinned source')
        return
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    for path, content in proposals:
        original = path.read_text(encoding='utf-8')
        if original != content:
            shutil.copy2(path, path.with_name(path.name + '.bak-' + stamp))
            path.write_text(content, encoding='utf-8')
    print('owner-auth patches installed locally; no service restart performed')


if __name__ == '__main__':
    main()
