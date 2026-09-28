"""Reapply guarded hotfixes to the pinned relay checkout; never update it."""
from __future__ import annotations
import ast
import datetime
import os
import pathlib
import shutil
import subprocess
import sysconfig

def replace_once(text, old, new):
    if new in text:
        return text
    if text.count(old) != 1:
        raise RuntimeError('source contract changed; no mutation')
    return text.replace(old, new, 1)

def main():
    root = pathlib.Path.home() / '.hermes/hermes-agent'
    rev = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    if not rev.startswith('ecacf3d0c9'):
        raise RuntimeError('unexpected checkout; no mutation')
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    aux = root / 'agent/auxiliary_client.py'
    vision = root / 'tools/vision_tools.py'
    source = aux.read_text()
    new = '''        from relay_runtime import retry_primary
        return await retry_primary(
            lambda: _primary(provider=request_provider, base_url=req.base_info),
            retries=min(2, _transient_retry_count()))
'''
    if 'from relay_runtime import retry_primary' not in source:
        start = source.index('        try:\n            return await _primary(provider=request_provider, base_url=req.base_info)', source.index('async def _async_call_llm_impl('))
        end = source.index('    except Exception as first_err:', start)
        source = source[:start] + new + source[end:]
    v = replace_once(vision.read_text(),
        '        analysis, scale_note = await stage(user_prompt, debug_call_data, temp_paths)',
        '        from relay_runtime import vision_budget\n        analysis, scale_note = await vision_budget(lambda: stage(user_prompt, debug_call_data, temp_paths))')
    v = replace_once(v,
        '        return finish({"success": False, "error": error_msg, "analysis": analysis})',
        '        return finish({"success": False, "error": "vision_unavailable", "analysis": "Gambarnya belum bisa dibaca sekarang. Coba lagi nanti.", "retryable": False})')
    for p, text in [(aux, source), (vision, v)]:
        ast.parse(text)
    for p, text in [(aux, source), (vision, v)]:
        if p.read_text() != text:
            shutil.copy2(p, str(p) + '.bak-' + stamp)
            p.write_text(text)
    helper = pathlib.Path(sysconfig.get_paths()['purelib']) / 'relay_runtime.py'
    if helper.exists():
        shutil.copy2(helper, str(helper) + '.bak-' + stamp)
    shutil.copy2(pathlib.Path(__file__).with_name('relay_runtime.py'), helper)
    import yaml
    config = pathlib.Path.home() / '.hermes/config.yaml'
    data = yaml.safe_load(config.read_text())
    wa = data.setdefault('display', {}).setdefault('platforms', {}).setdefault('whatsapp', {})
    wa.update(long_running_notifications='generic', busy_ack_detail=False,
              tool_progress='off', show_reasoning=False, interim_assistant_messages=False, streaming=False)
    data.setdefault('auxiliary', {})['transient_retries'] = 2
    data['auxiliary'].setdefault('vision', {})['timeout'] = 12
    shutil.copy2(config, str(config) + '.bak-' + stamp)
    config.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    drop = pathlib.Path.home() / '.config/systemd/user/hermes-gateway.service.d/latency.conf'
    if drop.exists():
        shutil.copy2(drop, str(drop) + '.bak-' + stamp)
    workspace = os.environ.get('NAQUUUU_WORKSPACE', str(pathlib.Path.home() / 'naquuuu'))
    drop.write_text('[Service]\nEnvironment="HERMES_AGENT_NOTIFY_INTERVAL=60"\n'
                    f'Environment="NAQUUUU_WORKSPACE={workspace}"\n')
    print('guard_install=ok; notify_interval=60; vision_budget=45; retries=2')

if __name__ == '__main__':
    main()
