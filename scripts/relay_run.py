"""Authenticated warm opencode relay, safe output, optional trusted context reuse."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).parent.resolve()))
from relay_outbound import sanitize_relay_events


def server_env() -> dict:
    env = os.environ.copy()
    try:
        pid = subprocess.check_output(['systemctl', '--user', 'show', 'opencode-serve.service', '-p', 'MainPID', '--value'], text=True).strip()
        for entry in Path('/proc', pid, 'environ').read_bytes().split(b'\0'):
            if entry.startswith((b'OPENCODE_SERVER_PASSWORD=', b'OPENCODE_SERVER_USERNAME=')):
                key, value = entry.decode().split('=', 1)
                env[key] = value
    except (OSError, subprocess.SubprocessError):
        pass
    return env


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('task', nargs='?')
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--file', action='append', default=[])
    args = parser.parse_args()
    root = Path(os.environ['NAQUUUU_WORKSPACE'])
    if args.status:
        print((root / 'internal-docs/STATUS.md').read_text(encoding='utf-8'))
        return 0
    if not args.task:
        parser.error('task required')
    binary = str(Path.home() / '.opencode/bin/opencode')
    env = server_env()
    cache = Path.home() / '.local/state/naquuuu/relay-sessions'
    # Only a host-injected context enables reuse. Never use a global last session.
    context = env.get('NAQUUUU_RELAY_CONTEXT')
    path = cache / (hashlib.sha256(context.encode()).hexdigest() + '.json') if context else None
    session = None
    if path and path.exists():
        session = json.loads(path.read_text()).get('session')
    base = [binary, 'run', '--format', 'json']
    files = [item for f in args.file for item in ['--file', str(Path(f).resolve(strict=True))]]
    attempts = [base + ['--attach', 'http://127.0.0.1:4096', '--dir', str(root)] + (['--session', session] if session else []) + files + [args.task], base + files + [args.task]]
    for index, command in enumerate(attempts):
        try:
            result = subprocess.run(command, cwd=root, env=env, text=True, capture_output=True, timeout=120)
        except subprocess.TimeoutExpired:
            print('Belum selesai dalam batas waktu. Coba tugas yang lebih kecil.')
            return 1  # Never rerun a task whose side effects are uncertain.
        events = []
        for line in result.stdout.splitlines():
            try:
                events.append(json.loads(line))
            except ValueError:
                pass
        if result.returncode == 0 and not any(e.get('type') == 'error' for e in events):
            reply, is_clean = sanitize_relay_events(events)
            if path and events and is_clean:
                cache.mkdir(parents=True, exist_ok=True, mode=0o700)
                sid = next((e.get('sessionID') for e in events if e.get('sessionID')), None)
                if sid:
                    fd, temp = tempfile.mkstemp(dir=cache)
                    with os.fdopen(fd, 'w') as out:
                        json.dump({'session': sid}, out)
                    os.replace(temp, path)
            print(reply or 'Selesai.')
            return 0
        # Fall back only if the server rejected before any execution event.
        if events or index:
            break
    print('Tugasnya belum bisa dijalankan sekarang.')
    return 1

if __name__ == '__main__':
    raise SystemExit(main())
